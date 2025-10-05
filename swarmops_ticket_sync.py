#!/usr/bin/env python3
"""
SwarmOps Ticket Synchronization Service
Polls external ticket systems for closed tickets and marks incidents as resolved
"""

import asyncio, os, httpx, redis, time
from prometheus_client import Counter, Gauge

# Import metrics from cortex
from cortex.incident_broadcast import INCIDENT_EVENT

# Redis client
r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)

# Ticket system credentials
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "jfbinTECHA/brain-swarm-incidents")
JIRA_URL     = os.getenv("JIRA_URL")
JIRA_USER    = os.getenv("JIRA_USER")
JIRA_TOKEN   = os.getenv("JIRA_TOKEN")

# Prometheus metrics
TICKETS_CHECKED = Counter("cortex_ticket_sync_checked_total", "Tickets polled")
TICKETS_RESOLVED = Counter("cortex_ticket_sync_resolved_total", "Tickets closed")
INCIDENT_TICKET = Gauge("cortex_incident_ticket_status", "Ticket status by incident", ["incident_id", "issue_url"])

async def poll_github():
    """Poll GitHub for recently closed issues"""
    if not GITHUB_TOKEN:
        return

    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/issues?state=closed&sort=updated&direction=desc&per_page=50",
                headers={"Authorization": f"token {GITHUB_TOKEN}"}
            )
            res.raise_for_status()

            for issue in res.json():
                # Only process issues updated in the last 10 minutes
                updated_at = issue.get("updated_at")
                if updated_at:
                    updated_time = time.strptime(updated_at, "%Y-%m-%dT%H:%M:%SZ")
                    if time.time() - time.mktime(updated_time) < 600:  # 10 minutes
                        issue_url = issue["html_url"]
                        incident_id = issue["title"].split("]")[1].strip() if "]" in issue["title"] else issue["title"]
                        await mark_resolved(incident_id, issue_url, "github")
        except Exception as e:
            print(f"❌ GitHub polling error: {e}")

async def poll_jira():
    """Poll Jira for recently closed issues"""
    if not all([JIRA_URL, JIRA_USER, JIRA_TOKEN]):
        return

    async with httpx.AsyncClient(auth=(JIRA_USER, JIRA_TOKEN)) as client:
        try:
            jql = 'status = "Done" AND updated >= -10m'
            res = await client.get(f"{JIRA_URL}/rest/api/3/search?jql={jql}")
            res.raise_for_status()

            for issue in res.json().get("issues", []):
                key = issue["key"]
                url = f"{JIRA_URL}/browse/{key}"
                await mark_resolved(key, url, "jira")
        except Exception as e:
            print(f"❌ Jira polling error: {e}")

async def mark_resolved(incident_id: str, issue_url: str, system: str):
    """Mark incident as resolved and emit events"""
    TICKETS_CHECKED.inc()

    # Emit Redis event
    r.xadd("cortex:incidents", {
        "event": "resolved",
        "actor": f"ticket-sync-{system}",
        "issue_url": issue_url,
        "incident_id": incident_id,
        "timestamp": str(time.time())
    })

    # Emit Prometheus metrics
    INCIDENT_EVENT.labels(event="resolved", actor=f"ticket-sync-{system}", severity="info").inc()
    INCIDENT_TICKET.labels(incident_id=incident_id, issue_url=issue_url).set(0)  # 0 = resolved
    TICKETS_RESOLVED.inc()

    print(f"✅ Ticket resolved: {incident_id} ({system}) - {issue_url}")

async def sync_loop():
    """Main synchronization loop"""
    print("🔄 Starting ticket synchronization service...")

    while True:
        try:
            await asyncio.gather(
                poll_github(),
                poll_jira()
            )
        except Exception as e:
            print(f"❌ Sync loop error: {e}")

        await asyncio.sleep(60)  # Poll every minute

if __name__ == "__main__":
    asyncio.run(sync_loop())