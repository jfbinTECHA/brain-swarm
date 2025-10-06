"""
Ticket Sync Worker
------------------
Polls GitHub, Jira, and ServiceNow APIs for closed tickets
and updates Cortex + Prometheus metrics accordingly.
"""

import asyncio, os, httpx, redis
from prometheus_client import Counter
from .webhook_service import INCIDENT_EVENTS

r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)

TICKETS_CHECKED = Counter("cortex_ticket_sync_checked_total", "Tickets polled")
TICKETS_RESOLVED = Counter("cortex_ticket_sync_resolved_total", "Tickets closed")


async def mark_resolved(ticket_id: str, issue_url: str):
    TICKETS_RESOLVED.inc()
    INCIDENT_EVENTS.labels(event="resolved", actor="ticket-sync", severity="info").inc()
    r.xadd("cortex:incidents", {"event": "resolved", "actor": "ticket-sync", "id": ticket_id, "issue_url": issue_url})


async def poll_github():
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")
    async with httpx.AsyncClient() as client:
        res = await client.get(f"https://api.github.com/repos/{repo}/issues?state=closed",
                               headers={"Authorization": f"token {token}"})
        for issue in res.json():
            await mark_resolved(issue["number"], issue["html_url"])


async def main():
    while True:
        try:
            await poll_github()
        except Exception as e:
            print("Ticket sync error:", e)
        await asyncio.sleep(600)