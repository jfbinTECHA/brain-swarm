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

# New annotation triggers
INCIDENT_EVENT = Counter("cortex_incident_event_total", "Annotated incident events", ["event", "actor", "severity"])

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

    # Record detailed incident event
    severity = incident.get("commonLabels", {}).get("severity", "info")
    INCIDENT_EVENT.labels(event="created", actor="system", severity=severity).inc()

def mark_incident_resolved(severity: str = "info"):
    """Increment resolved incident counter"""
    INCIDENT_RESOLVED.inc()
    INCIDENT_EVENT.labels(event="resolved", actor="system", severity=severity).inc()

def record_ai_triage_action(incident_id: str = None, severity: str = "info"):
    """Increment AI triage action counter and record event stream"""
    AI_TRIAGE_ACTIONS.inc()
    INCIDENT_EVENT.labels(event="triaged", actor="kilo", severity=severity).inc()

    # Record to Redis stream for event sourcing
    if incident_id:
        event_data = {
            "actor": "kilo",
            "action": "triage",
            "incident": incident_id,
            "timestamp": str(time.time()),
            "severity": severity
        }
        r.xadd("kilo:events", event_data)

def record_incident_event(event: str, actor: str = "system", severity: str = "info"):
    """Record annotated incident events for detailed tracking"""
    INCIDENT_EVENT.labels(event=event, actor=actor, severity=severity).inc()