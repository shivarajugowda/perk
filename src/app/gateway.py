from fastapi import FastAPI, Header, HTTPException
from starlette.requests import Request
from starlette.responses import Response
from app import config, taskqueue

app = FastAPI()

@app.on_event("startup")
async def startup():
    print("Init")

@app.on_event("shutdown")
async def shutdown():
    print("Shutdown")

@app.get("/ping")
async def ping():
    return {"ping": "pong!"}

@app.post("/v1/statement")
async def query(request: Request):
    body = await request.body()
    sql: str = bytes.decode(body)
    headers = {key: val for key, val in request.headers.items() if key.startswith("x-presto")}

    taskId = taskqueue.addTask(headers, sql)
    return config.getQueuedMessage(taskId)

@app.get("/v1/statement/{state}/{taskId}/{token}/{page}")
async def status(state : str, taskId : str, token : str, page : str):
    state, error = taskqueue.getStatus(taskId)
    if not  state:
        raise HTTPException(status_code=404, detail='Unknown Query ID : ' + taskId)
    elif state == taskqueue.STATE_ERROR:
        return config.getErrorMessage(taskId, error)
    elif state == taskqueue.STATE_DONE:
        headers, data = taskqueue.getResults(taskId, page)
        return Response(headers=headers, content=data, media_type="application/json")
    else:
        return config.getExecutingMessage(taskId, page)

@app.delete("/v1/query/{taskId}")
async def delete(taskId : str):
    print("Delete query : " + taskId)
