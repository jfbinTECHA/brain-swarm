"""
Incident broadcasting to Kilo Code AI
Handles Redis pub/sub communication for real-time incident notifications
"""

import redis, os, json, time, asyncio
from prometheus_client import Counter

# Prometheus metrics for incident tracking
INCIDENT_CREATED = Counter("cortex_incidents_created_total", "New incidents")
INCIDENT_RESOLVED = Counter("cortex_incidents_resolved_total", "Resolved incidents")
AI_TRIAGE_ACTIONS = Counter("cortex_ai_triage_actions_total", "Kilo triage actions")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

async def broadcast_to_kilo(incident):
    msg = {
        "type": "incident_created",
        "timestamp": time.time(),
        "incident": incident,
    }
    # Run synchronous Redis publish in thread pool
    await asyncio.to_thread(r.publish, "cortex:incidents", json.dumps(msg))

    # Increment Prometheus metrics
    INCIDENT_CREATED.inc()

def mark_incident_resolved():
    """Increment resolved incident counter"""
    INCIDENT_RESOLVED.inc()

def record_ai_triage_action():
    """Increment AI triage action counter"""
    AI_TRIAGE_ACTIONS.inc()