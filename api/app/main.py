from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
import os

app = FastAPI(title="Brain Swarm API")

@app.on_event("startup")
async def _startup():
    # Prometheus metrics at /metrics
    Instrumentator().instrument(app).expose(app)

# Include admin router for control operations
from app.routes import admin
app.include_router(admin.router, prefix="/admin", tags=["admin"])


@app.get("/healthz")
def healthz():
    import os, redis, psycopg2
    status = {"status": "ok"}
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        conn.close()
        status["db"] = "ok"
    except Exception:
        status["db"] = "error"
    try:
        r = redis.Redis.from_url(os.getenv("REDIS_URL"))
        r.ping()
        status["redis"] = "ok"
    except Exception:
        status["redis"] = "error"
    return status


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