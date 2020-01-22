from starlette.testclient import TestClient
import time
from app.gateway import app

client = TestClient(app)

def test_ping():
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"ping": "pong!"}

def sanity():
    NUMJOBS = 2
    start = time.perf_counter()
    for i in range(NUMJOBS):
        id = taskqueue.addTask({'X-Presto-User':'joe'}, "SELECT " + str(i))
        while taskqueue.getStatus(id)[0] != taskqueue.STATE_DONE:
            time.sleep(0.001)
    totalTime = time.perf_counter() - start
    print("Time taken " + str(totalTime) +  " per query (ms) : " + str((totalTime)/NUMJOBS))