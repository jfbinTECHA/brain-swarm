"""
BrainSwarm Cognitive Cycle — minimal safe implementation
Perception → Attention → Understanding → Learning.
Runs every 15 seconds, storing the current focus in Redis for the UI HUD.
"""
from __future__ import annotations
import time, json, redis
from brainswarm.reasoning import concept_graph as cg
from brainswarm.planning import planner
# from brainswarm.logging import timeline  # commented out due to DB lock issues

r = redis.from_url("redis://localhost:6379", decode_responses=True)

def latest_metrics(limit:int=50):
    """Fetch latest system metrics from Redis sensor stream."""
    metrics = {}
    try:
        for _id, data in r.xrevrange("sensor_stream", count=limit):
            m = data.get("metric")
            if m and m not in metrics:
                metrics[m] = float(data.get("value", 0.0))
    except Exception:
        pass
    return metrics


def cognitive_step() -> dict:
    """One cognitive heartbeat cycle."""
    readings = latest_metrics()
    if readings:
        cg.ingest_concepts_from_readings(readings)

    top = cg.top_concepts(1)
    if top:
        focus, conf = top[0]
        related = cg.related(focus, 5)
    else:
        focus, conf, related = "None", 0.0, []

    result = {
        "focus": focus,
        "confidence": conf,
        "related": related,
        "timestamp": time.time(),
    }
    r.set("current_focus", json.dumps(result))

    # Plan actions based on focus
    plan_result = planner.plan_and_emit(result)
    actions = plan_result.get("actions", [])

    # Log to timeline
    # timeline.log_cycle(result, actions)  # commented out

    return result