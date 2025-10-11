from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response
import os
from .routers import health
from .routes import dashboard as dashboard_routes
from .routes import reason as reason_routes
from . import ui_embed
from . import ui_embed

from fastapi_utils.tasks import repeat_every
from .memory.edge_tracker import decay_edges
import redis
from .reasoning.concept_graph import ingest_concepts_from_readings
from .cycles import cognitive

_r = redis.from_url("redis://localhost:6379", decode_responses=True)

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
app.include_router(reason_routes.router, tags=["reason"])
app.include_router(ui_embed.router, tags=["ui"])
app.include_router(ui_embed.router, tags=["ui"])
from . import ui_timeline; app.include_router(ui_timeline.router)
from .routes import ops_status; app.include_router(ops_status.router)
from . import ui_maintenance; app.include_router(ui_maintenance.router)
from .routes import reflection_api as refl_routes; app.include_router(refl_routes.router)
from . import ui_reflection; app.include_router(ui_reflection.router)
import json

# Phase 8 Federation Bridge
from .federation import bridge; bridge.start_background_bridge()
from .routes import federation_api as fed_routes; app.include_router(fed_routes.router)
from . import ui_federation; app.include_router(ui_federation.router)
from . import ui_maintenance; app.include_router(ui_maintenance.router)


# Periodic adaptive-memory decay
@app.on_event("startup")
@repeat_every(seconds=60)  # every minute
def periodic_decay_task() -> None:
    decay_edges()


# Background cognitive loop — runs every 15s
@app.on_event("startup")
@repeat_every(seconds=15)
def periodic_cognitive_cycle() -> None:
    try:
        result = cognitive.cognitive_step()
        _r.set("current_focus", json.dumps(result))
    except Exception as e:
        _r.set("cog_error", str(e))

# Phase 9 — periodic reflection (every 5 min)
from brainswarm.reflection.engine import store_reflection
@app.on_event("startup")
@repeat_every(seconds=300)
def periodic_reflection() -> None:
    try:
        store_reflection(limit=200)
    except Exception as e:
        _r.set("reflection_error", str(e))

def _latest_metrics():
    """Helper used by periodic concept ingestion."""
    metrics = {}
    try:
        for _id, data in _r.xrevrange("sensor_stream", count=50):
            m = data.get("metric")
            if m and m not in metrics:
                metrics[m] = float(data.get("value", 0))
    except Exception:
        pass
    return metrics

# Periodic concept ingestion (maps sensors -> concepts -> graph)
@app.on_event("startup")
@repeat_every(seconds=10)  # gentle cadence
def periodic_concept_ingest() -> None:
    readings = _latest_metrics()
    if readings:
        ingest_concepts_from_readings(readings)

@app.get("/")
def root():
    return {"message": "BrainSwarm API online"}

@app.get("/metrics")
def metrics():
    # Basic single-process export. If you use Gunicorn workers,
    # switch to multiprocess mode per prometheus_client docs.
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
