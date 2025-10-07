from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
import os

app = FastAPI(title="Brain Swarm API")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# Example "/gpt/meta" and "/gpt/supervise" stubs if routers not yet wired
@app.get("/gpt/meta")
def gpt_meta():
    return {"meta": "Brain Swarm meta endpoint ready"}


@app.get("/gpt/supervise")
def gpt_supervise():
    return {"supervise": "Brain Swarm supervise endpoint ready"}


@app.on_event("startup")
async def _startup():
    # Prometheus metrics at /metrics
    Instrumentator().instrument(app).expose(app)