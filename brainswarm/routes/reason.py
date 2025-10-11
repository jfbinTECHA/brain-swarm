from __future__ import annotations
from typing import Dict, Any
from fastapi import APIRouter, Query
import redis

from brainswarm.reasoning.concept_graph import (
    ingest_concepts_from_readings,
    top_concepts,
    related,
)

router = APIRouter()
_r = redis.from_url("redis://localhost:6379", decode_responses=True)

def _latest_metrics() -> Dict[str, float]:
    """
    Read last ~100 sensor_stream entries and take newest value per metric.
    """
    metrics: Dict[str, float] = {}
    try:
        # newest-first
        for _id, data in _r.xrevrange("sensor_stream", count=100):
            m = data.get("metric")
            if m and m not in metrics:
                metrics[m] = float(data.get("value", 0.0))
    except Exception:
        pass
    return metrics

@router.post("/reason/ingest")
def reason_ingest_from_sensors():
    """
    Map current sensor metrics -> concepts and update concept graph.
    """
    m = _latest_metrics()
    res = ingest_concepts_from_readings(m)
    return {"mapped": res, "metrics": m}

@router.get("/reason/top")
def reason_top(k: int = 10):
    """
    Return top activated concepts (attention).
    """
    return {"top": top_concepts(k)}

@router.get("/reason/infer")
def reason_infer(seed: str = Query(..., description="Seed concept"), k: int = 10):
    """
    Return up to k concepts related to 'seed' by edge weight.
    """
    return {"seed": seed, "related": related(seed, k)}