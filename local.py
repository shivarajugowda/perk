import subprocess, os
import pathlib, shutil

# This file is only used for debugging/testing in the local env and is not used in K8S deployment.
# Assumes Redis and Presto are setup in the local env.
if __name__ == '__main__':
    shutil.rmtree('logs', ignore_errors=True)
    pathlib.Path('logs').mkdir(exist_ok=True)

    os.environ["REDIS_SENTINEL"] = "1"
    os.environ["REDIS_PORT"] = "26379"
    os.environ["REDIS_MASTER_SET"] = "1"
    os.environ["GATEWAY_SERVICE"] = "localhost:8000"

    # Start Gateway.
    cmd = ['uvicorn', 'app.gateway:app', '--log-level', 'error', '--workers', '2']
    with open("logs/gateway.log", "wb") as out:
        subprocess.Popen(cmd, stdout=out, stderr=out)

    # Start Worker.
    #src.app..start(argv=['celery', 'worker', '-O', 'fair', '-l', 'error',  '--logfile', 'logs/worker.log'])
