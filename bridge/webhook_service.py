"""
BrainSwarmOps Webhook Bridge Service
------------------------------------
Handles webhook intake from GitHub, Jira, and ServiceNow.
Performs signature validation, rate limiting (via ingress),
and emits structured events into Redis Streams + Prometheus metrics.
"""

from fastapi import FastAPI, Request, HTTPException
from prometheus_client import Counter, generate_latest
import redis, os, json, hmac, hashlib, httpx

app = FastAPI(title="SwarmOps Webhook Bridge", version="1.0")

r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)

INCIDENT_EVENTS = Counter("cortex_incident_event_total", "Incident event stream", ["event", "actor", "severity"])
WEBHOOK_REQUESTS = Counter("webhook_requests_total", "Webhook POSTs received", ["source"])
WEBHOOK_ERRORS = Counter("webhook_errors_total", "Webhook errors encountered", ["source"])

SECRET = os.getenv("WEBHOOK_SECRET", "default_secret")


def verify_signature(sig_header: str, body: bytes) -> bool:
    digest = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={digest}", sig_header or "")


@app.post("/gh-webhook")
async def github_hook(request: Request):
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(sig, body):
        WEBHOOK_ERRORS.labels(source="github").inc()
        raise HTTPException(status_code=403, detail="Invalid signature")

    data = await request.json()
    WEBHOOK_REQUESTS.labels(source="github").inc()

    action = data.get("action", "")
    issue = data.get("issue", {})
    title = issue.get("title", "unknown")
    severity = "critical" if "CRITICAL" in title.upper() else "info"

    r.xadd("cortex:incidents", {"source": "github", "action": action, "title": title, "severity": severity})
    INCIDENT_EVENTS.labels(event=action, actor="bridge", severity=severity).inc()

    return {"status": "accepted", "ticket_system": "github", "alerts_count": 1}


@app.get("/metrics")
def metrics():
    return generate_latest()