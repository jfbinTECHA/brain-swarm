from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

@app.get("/ping")
def ping():
    return {"redis": True, "duckdb_path": "/data/cortex.duckdb"}

Instrumentator().instrument(app).expose(app)
