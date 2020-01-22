import uuid, os, socket
from pydantic import BaseModel

REDIS_URL = os.environ.get('REDIS_URL')
GATEWAY_SERVICE = os.environ.get('GATEWAY_SERVICE')

MANAGE_PRESTO_SERVICE = (os.environ.get('MANAGE_PRESTO_SERVICE') == 'true')
MY_POD_NAME = os.environ.get('MY_POD_NAME') if os.environ.get('MY_POD_NAME') else socket.gethostname()
MY_POD_UID = os.environ.get('MY_POD_UID')
POD_PRESTO_SVC_MAP = "pod-presto-map:"

PRESTO_SVC =  os.environ.get('PRESTO_SVC') if os.environ.get('PRESTO_SVC') else 'presto-' + str(uuid.uuid4())[:12]
PRESTO_PORT = 8080

NUM_THREADS = 1

RESULTS_TIME_TO_LIVE_SECS = 600
POD_PRESTO_SVC_MAP = "pod-presto-map:"

STREAM_NAME = "tasks"
STREAM_CONSUMER_GROUP = STREAM_NAME + '-cg'
STREAM_CONSUMER_NAME  = PRESTO_SVC

RETRYABLE_ERROR_MESSAGES = ['Presto server is still initializing',      # Presto coordinator is restarting.
                            ]

class Stats(BaseModel):
    state : str = 'QUEUED'
    queued : bool = True
    scheduled : bool = False
    nodes : int = 0
    totalSplits : int = 0
    queuedSplits: int = 0
    runningSplits: int = 0
    completedSplits: int = 0
    cpuTimeMillis: int = 0
    wallTimeMillis: int = 0
    queuedTimeMillis : int = 0
    elapsedTimeMillis : int = 0
    processedRows : int = 0
    processedBytes : int = 0
    peakMemoryBytes : int = 0
    spilledBytes: int = 0

class QueryResult(BaseModel):
    id : str
    infoUri : str = None
    nextUri : str = None
    stats : Stats = Stats()
    error: str = None
    warnings = []

def getQueuedMessage(taskId: str):
    nextUri = 'http://' + GATEWAY_SERVICE + '/v1/statement/queued/' + taskId + '/zzz/0'
    infoUri = 'http://' + GATEWAY_SERVICE + '/ui/query.html?' + taskId
    return QueryResult(id=taskId, nextUri=nextUri, infoUri=infoUri)

def getExecutingMessage(taskId: str, page: int):
    nextUri = 'http://' + GATEWAY_SERVICE + '/v1/statement/executing/' + taskId + '/zzz/' + page
    infoUri = 'http://' + GATEWAY_SERVICE + '/ui/query.html?' + taskId
    qr = QueryResult(id=taskId, nextUri=nextUri, infoUri=infoUri);
    qr.stats.state = "RUNNING"; qr.stats.queued = False; qr.stats.scheduled = True
    return qr;

def getErrorMessage(taskId: str, error: str):
    return QueryResult(id=taskId, error=error)