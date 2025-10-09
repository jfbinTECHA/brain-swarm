from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response
import os
from .routers import health
from .routes import dashboard as dashboard_routes

app = FastAPI(title="BrainSwarm API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(dashboard_routes.router, prefix="/dashboard", tags=["dashboard"])

@app.get("/")
def root():
    return {"message": "BrainSwarm API online"}

@app.get("/metrics")
def metrics():
    # Basic single-process export. If you use Gunicorn workers,
    # switch to multiprocess mode per prometheus_client docs.
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
