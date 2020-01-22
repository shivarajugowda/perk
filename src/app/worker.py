import multiprocessing, time, signal, sys, json, subprocess, traceback
from http import client as httpclient
from urllib.parse import urlparse
from app import config, taskqueue
from tenacity import retry, stop_after_delay, wait_random_exponential, before_log

def start_presto_service():
    try:
        start = time.perf_counter()
        cmd = ['helm', 'install', config.PRESTO_SVC, './charts/presto', '--set', 'server.workers=0',
               '--set', 'owner.name=' + config.MY_POD_NAME, '--set', 'owner.uid=' + config.MY_POD_UID, '--wait']
        subprocess.Popen(cmd, stdout=subprocess.PIPE).wait()
        print("Presto Service initialization Time Taken : " + str(time.perf_counter() - start))
    except Exception as e:
        print("Failed to connect to Presto Service in " + str(time.perf_counter() - start)
              + " seconds with exception : " + str(e))
        shutdown_presto_service()
        sys.exit(1)

def shutdown_presto_service():
    cmd = ['helm', 'uninstall', config.PRESTO_SVC]
    subprocess.Popen(cmd, stdout=subprocess.PIPE).wait()

class Worker():

    def __init__(self, numrunners=1):
        print("Init ")
        taskqueue.initWorker()
        if config.MANAGE_PRESTO_SERVICE:
            start_presto_service()
        self.pool = multiprocessing.Pool(config.NUM_THREADS, self.runner)

    def shutdown(self):
        print("Shutdown ")
        self.pool.terminate()
        taskqueue.shutdownWorker()
        if config.MANAGE_PRESTO_SERVICE:
            shutdown_presto_service()

    def runner(self):

        @retry(wait=wait_random_exponential(multiplier=0.5, max=5), stop=stop_after_delay(60))
        def runQuery(taskId, headers, sql):
            conn = httpclient.HTTPConnection(host=config.PRESTO_SVC, port=config.PRESTO_PORT)
            conn.request('POST', '/v1/statement', headers=headers, body=sql)
            response = conn.getresponse()
            json_response = json.loads(response.read())
            nexturi = json_response.get('nextUri', None)
            page = storeResults(taskId, 0, response.getheaders(), json_response)
            while nexturi:
                conn.request('GET', nexturi)
                response = conn.getresponse()
                json_response = json.loads(response.read())
                nexturi = json_response.get('nextUri', None)
                page = storeResults(taskId, page, response.getheaders(), json_response)
            conn.close()

        def storeResults(taskId: str, page, headers, json_response):
            # Based on thee tests so far, I think we can ignore the QUEUED responses.
            if 'QUEUED' == json_response['stats']['state']:
                return page

            # Check for retryable errors.
            if 'error' in json_response and 'message' in json_response['error']:
                errmsg = json_response['error']['message']
                if any(pattern in errmsg for pattern in config.RETRYABLE_ERROR_MESSAGES):
                    raise RuntimeError(errmsg)  # Raise error, the query will be retried.

            if 'nextUri' in json_response:  # Switch the URI to point to the stored results.  # Tested on Presto 317
                parsed = urlparse(json_response['nextUri'])
                parsed = parsed._replace(netloc=config.GATEWAY_SERVICE,
                                         path=parsed.path.replace(json_response['id'], taskId))
                json_response['nextUri'] = parsed.geturl()

            json_response['id'] = taskId

            prestoHeaders = {key: val for key, val in headers if key.startswith("X-Presto")}
            taskqueue.writeTaskResults(taskId, page, prestoHeaders, json_response)
            return page + 1

        while True :
            taskId, headers, sql = taskqueue.getTask()
            try :
                runQuery(taskId, headers, sql)
                taskqueue.ackTask(taskId)
            except Exception as ex :
                print("Encountered Exception : " + str(ex) ) #TODO : Integrate with Sentry.
                traceback.print_exc()
                taskqueue.ackTask(taskId, str(ex))


def startWorker(numThreads:int =1):
    worker = Worker(config.NUM_THREADS)
    def signal_handler(signum, frame):
        worker.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def monitor():
    while True:
        time.sleep(10)

if __name__ == '__main__':
    startWorker(config.NUM_THREADS)
    monitor()
