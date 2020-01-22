import redis, gzip, json, socket, traceback, sys
from app import config
from tenacity import retry, retry_if_exception_type, wait_random_exponential, stop_after_delay
from fastapi import HTTPException
from redis.sentinel import Sentinel

# Redis Streams based TaskQueue.
# IMPORTANT : All functions should be idempotent(and atomic if possible) since they are retried for resiliency.
print("Redis URL : " + config.REDIS_URL)
_redis = redis.from_url(config.REDIS_URL)
STATE = "state"
STATE_QUEUED = "QUEUED"
STATE_RUNNING = "RUNNING"
STATE_DONE = "DONE"
STATE_ERROR = "ERROR"

@retry(retry=retry_if_exception_type(redis.exceptions.ConnectionError), wait= wait_random_exponential(multiplier=0.5,max=2), stop=stop_after_delay(60))
def initWorker():
    try :
        with _redis.pipeline() as pipe:
            pipe.hset(config.POD_PRESTO_SVC_MAP, config.MY_POD_NAME, config.PRESTO_SVC);
            pipe.xgroup_create(config.STREAM_NAME, config.STREAM_CONSUMER_GROUP, mkstream=True)
            pipe.execute()
    except Exception as ex :
        if not "BUSYGROUP Consumer Group name already exists" in str(ex):
            print("Exception : " + str(ex))
            sys.exit(1)

@retry(retry=retry_if_exception_type(redis.exceptions.ConnectionError), wait= wait_random_exponential(multiplier=0.5,max=2), stop=stop_after_delay(60))
def shutdownWorker():
    with _redis.pipeline() as pipe:
        pipe.hdel(config.POD_PRESTO_SVC_MAP, config.POD_NAME);
        pipe.xgroup_delconsumer(config.STREAM_NAME, config.STREAM_CONSUMER_GROUP, config.STREAM_CONSUMER_NAME)
        pipe.execute()

@retry(retry=retry_if_exception_type(redis.exceptions.ConnectionError), wait= wait_random_exponential(multiplier=0.5,max=2), stop=stop_after_delay(60))
def getTask():
    while True:
        resp = _redis.xreadgroup(config.STREAM_CONSUMER_GROUP, config.STREAM_CONSUMER_NAME, {config.STREAM_NAME: ">"}, count=1, block=2000)
        #TODO : Claim PENDING TASKS > idleTime.
        if resp:
            for stream_key, message_list in resp:
                taskId, data = message_list[0]
                sql = data[b'sql'].decode()
                headers = json.loads(data[b'headers'].decode())
                return taskId.decode(), headers, sql

@retry(retry=retry_if_exception_type(redis.exceptions.ConnectionError), wait= wait_random_exponential(multiplier=0.5,max=2), stop=stop_after_delay(60))
def ackTask(taskId: str, error: str = None):
    with _redis.pipeline() as pipe:
        if error :
            pipe.hset(taskId, STATE, STATE_ERROR)
            pipe.hset(taskId, STATE_ERROR, error)
        else :
            pipe.hset(taskId, STATE, STATE_DONE)
        pipe.xack(config.STREAM_NAME, config.STREAM_CONSUMER_GROUP, taskId)
        pipe.xdel(config.STREAM_NAME, taskId)
        pipe.execute()

@retry(retry=retry_if_exception_type(redis.exceptions.ConnectionError), wait= wait_random_exponential(multiplier=0.5,max=2), stop=stop_after_delay(60))
def writeTaskResults(taskId: str, page: str, headers: {}, data: {}):
    with _redis.pipeline() as pipe:
        #TODO: ADD XCLAIM
        pipe.hset(taskId , page, gzip.compress(json.dumps(data).encode()))
        if headers:
            pipe.hset(taskId, str(page) + "_headers", json.dumps(headers))
        pipe.execute()


####################################################################################################
# The  following calls are from the Gatewa to get the status. So don't retry the calls but return 503 so that the client can retry the http request.

# /v1/statement doesn't retry on HTTP 503 so need to wait. The Presto client might throw a SocketTimeoutException if it waits more than 10 seconds.
@retry(retry=retry_if_exception_type(redis.exceptions.ConnectionError), wait= wait_random_exponential(multiplier=0.5,max=2), stop=stop_after_delay(60))
def addTask(headers: {}, query : str):
    # TODO : RATE LIMIT. Need to put this in LUA for atomicity.
    taskId = _redis.xadd(config.STREAM_NAME, {'headers':json.dumps(headers), 'sql': query, })
    with _redis.pipeline() as pipe:
        pipe.hset(taskId, STATE, STATE_QUEUED)
        pipe.expire(taskId, config.RESULTS_TIME_TO_LIVE_SECS)
        pipe.execute()
    return taskId.decode()

def getStatus(taskId: str):
    try:
        with _redis.pipeline() as pipe:
            pipe.hget(taskId, STATE)
            pipe.hget(taskId, STATE_ERROR)
            state, error = pipe.execute()
        return state.decode(), error
    except redis.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail='Redis service not available, please try again.')

def getResults(taskId: str, page: str):
    try:
        with _redis.pipeline() as pipe:
            pipe.hget(taskId, page + "_headers")
            pipe.hget(taskId, page)
            headers, data = pipe.execute()
        headers = json.loads(headers.decode()) if headers else {}
        headers['Content-Encoding'] = "gzip"
        return headers, data
    except redis.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail='Redis service not available, please try again.')

####################################################################################################