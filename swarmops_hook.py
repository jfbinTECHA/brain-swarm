#!/usr/bin/env python3
"""
SwarmOps Alert Webhook Handler
Receives Alertmanager webhooks and creates tickets in Jira, GitHub Issues, or ServiceNow
"""

import os
import json
import time
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
import httpx
import asyncio
from enum import Enum

from schemas.incident import AlertGroup

app = FastAPI(title="SwarmOps Alert Webhook Handler", version="1.0.0")

class TicketSystem(Enum):
    JIRA = "jira"
    GITHUB = "github"
    SERVICENOW = "servicenow"

class TicketCreator:
    def __init__(self, system: TicketSystem, config: Dict[str, Any]):
        self.system = system
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)

    async def create_ticket(self, alert_group: AlertGroup) -> Dict[str, Any]:
        """Create a ticket in the configured system"""
        if self.system == TicketSystem.JIRA:
            return await self._create_jira_ticket(alert_group)
        elif self.system == TicketSystem.GITHUB:
            return await self._create_github_issue(alert_group)
        elif self.system == TicketSystem.SERVICENOW:
            return await self._create_servicenow_ticket(alert_group)
        else:
            raise ValueError(f"Unsupported ticket system: {self.system}")

    async def close_ticket(self, ticket_system: str, ticket_id: str, resolution_reason: str = "Alert resolved") -> bool:
        """Close a ticket when alert is resolved"""
        try:
            # Trigger GitHub Actions workflow to close the incident
            github_token = os.getenv("GITHUB_TOKEN")
            github_owner = os.getenv("GITHUB_OWNER")
            github_repo = os.getenv("GITHUB_REPO")

            if github_token and github_owner and github_repo:
                # Calculate resolution time (would be passed from Alertmanager)
                resolution_time = time.time()

                payload = {
                    "event_type": "alert_resolved",
                    "client_payload": {
                        "ticket_system": ticket_system,
                        "ticket_id": ticket_id,
                        "resolution_reason": resolution_reason,
                        "alert_name": "Alert Resolution",  # Would be passed from webhook
                        "resolution_time": resolution_time
                    }
                }

                headers = {
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github.v3+json"
                }

                url = f"https://api.github.com/repos/{github_owner}/{github_repo}/dispatches"
                response = await self.client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                print(f"✅ GitHub Actions workflow triggered to close {ticket_system} ticket {ticket_id}")
                return True
            else:
                print("⚠️  GitHub credentials not configured for incident closure")
                return False

        except Exception as e:
            print(f"❌ Failed to trigger incident closure: {str(e)}")
            return False

    async def _create_jira_ticket(self, alert_group: AlertGroup) -> Dict[str, Any]:
        """Create a Jira ticket"""
        url = f"{self.config['base_url']}/rest/api/3/issue"

        # Format alert data for Jira
        summary = self._generate_summary(alert_group)
        description = self._generate_description(alert_group)

        payload = {
            "fields": {
                "project": {"key": self.config["project_key"]},
                "summary": summary,
                "description": description,
                "issuetype": {"name": self.config.get("issue_type", "Bug")},
                "priority": {"name": self._map_severity_to_priority(alert_group.commonLabels.get("severity", "warning"))},
                "labels": ["alertmanager", "brain-swarm", alert_group.commonLabels.get("service", "unknown")]
            }
        }

        auth = (self.config["username"], self.config["api_token"])

        response = await self.client.post(url, json=payload, auth=auth)
        response.raise_for_status()

        result = response.json()
        return {
            "system": "jira",
            "ticket_id": result["key"],
            "url": f"{self.config['base_url']}/browse/{result['key']}",
            "created": True
        }

    async def _create_github_issue(self, alert_group: AlertGroup) -> Dict[str, Any]:
        """Create a GitHub issue"""
        url = f"https://api.github.com/repos/{self.config['owner']}/{self.config['repo']}/issues"

        headers = {
            "Authorization": f"token {self.config['token']}",
            "Accept": "application/vnd.github.v3+json"
        }

        title = self._generate_summary(alert_group)
        body = self._generate_description(alert_group)

        # Add GitHub-specific formatting
        body += f"\n\n---\n**Alertmanager URL:** {alert_group.externalURL}"
        body += f"\n**Status:** {alert_group.status}"

        payload = {
            "title": title,
            "body": body,
            "labels": ["alert", "brain-swarm", f"severity-{alert_group.commonLabels.get('severity', 'unknown')}"]
        }

        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()
        return {
            "system": "github",
            "ticket_id": result["number"],
            "url": result["html_url"],
            "created": True
        }

    async def _create_servicenow_ticket(self, alert_group: AlertGroup) -> Dict[str, Any]:
        """Create a ServiceNow incident"""
        url = f"{self.config['instance_url']}/api/now/table/incident"

        headers = {
            "Authorization": f"Bearer {self.config['access_token']}",
            "Content-Type": "application/json"
        }

        payload = {
            "short_description": self._generate_summary(alert_group),
            "description": self._generate_description(alert_group),
            "urgency": self._map_severity_to_urgency(alert_group.commonLabels.get("severity", "warning")),
            "impact": "3",  # Medium impact by default
            "category": "Software",
            "subcategory": "Application",
            "assignment_group": self.config.get("assignment_group", ""),
            "work_notes": f"Alert received from Alertmanager\nExternal URL: {alert_group.externalURL}"
        }

        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()
        return {
            "system": "servicenow",
            "ticket_id": result["result"]["number"],
            "url": f"{self.config['instance_url']}/nav_to.do?uri=incident.do?sys_id={result['result']['sys_id']}",
            "created": True
        }

    def _generate_summary(self, alert_group: AlertGroup) -> str:
        """Generate a ticket summary from alert data"""
        alert_name = alert_group.commonLabels.get("alertname", "Unknown Alert")
        service = alert_group.commonLabels.get("service", "unknown")
        severity = alert_group.commonLabels.get("severity", "unknown")

        return f"[{severity.upper()}] {alert_name} - {service}"

    def _generate_description(self, alert_group: AlertGroup) -> str:
        """Generate a detailed ticket description"""
        description = []

        # Basic alert information
        description.append(f"**Alert Status:** {alert_group.status}")
        description.append(f"**Alert Name:** {alert_group.commonLabels.get('alertname', 'N/A')}")
        description.append(f"**Service:** {alert_group.commonLabels.get('service', 'N/A')}")
        description.append(f"**Severity:** {alert_group.commonLabels.get('severity', 'N/A')}")
        description.append(f"**Instance:** {alert_group.commonLabels.get('instance', 'N/A')}")

        # Summary and description from annotations
        if "summary" in alert_group.commonAnnotations:
            description.append(f"**Summary:** {alert_group.commonAnnotations['summary']}")
        if "description" in alert_group.commonAnnotations:
            description.append(f"**Description:** {alert_group.commonAnnotations['description']}")

        # Individual alert details
        if alert_group.alerts:
            description.append("\n**Alert Details:**")
            for i, alert in enumerate(alert_group.alerts, 1):
                description.append(f"\n**Alert {i}:**")
                description.append(f"- Labels: {', '.join(f'{k}={v}' for k, v in alert.get('labels', {}).items())}")
                if "annotations" in alert:
                    for k, v in alert["annotations"].items():
                        description.append(f"- {k}: {v}")
                if "value" in alert:
                    description.append(f"- Value: {alert['value']}")

        # External URL
        description.append(f"\n**Alertmanager URL:** {alert_group.externalURL}")

        return "\n".join(description)

    def _map_severity_to_priority(self, severity: str) -> str:
        """Map alert severity to Jira priority"""
        mapping = {
            "critical": "Highest",
            "warning": "High",
            "info": "Medium"
        }
        return mapping.get(severity.lower(), "Medium")

    def _map_severity_to_urgency(self, severity: str) -> str:
        """Map alert severity to ServiceNow urgency"""
        mapping = {
            "critical": "1",  # High
            "warning": "2",   # Medium
            "info": "3"       # Low
        }
        return mapping.get(severity.lower(), "2")

# Global ticket creators
ticket_creators: Dict[str, TicketCreator] = {}

def get_ticket_creator(system_name: str) -> Optional[TicketCreator]:
    """Get a ticket creator by name"""
    return ticket_creators.get(system_name)

@app.on_event("startup")
async def startup_event():
    """Initialize ticket creators on startup"""
    global ticket_creators

    # Jira configuration
    if os.getenv("JIRA_ENABLED", "false").lower() == "true":
        jira_config = {
            "base_url": os.getenv("JIRA_BASE_URL"),
            "username": os.getenv("JIRA_USERNAME"),
            "api_token": os.getenv("JIRA_API_TOKEN"),
            "project_key": os.getenv("JIRA_PROJECT_KEY", "ALERT"),
            "issue_type": os.getenv("JIRA_ISSUE_TYPE", "Bug")
        }
        if all(jira_config.values()):
            ticket_creators["jira"] = TicketCreator(TicketSystem.JIRA, jira_config)
            print("✅ Jira ticket creator initialized")

    # GitHub configuration
    if os.getenv("GITHUB_ENABLED", "false").lower() == "true":
        github_config = {
            "owner": os.getenv("GITHUB_OWNER"),
            "repo": os.getenv("GITHUB_REPO"),
            "token": os.getenv("GITHUB_TOKEN")
        }
        if all(github_config.values()):
            ticket_creators["github"] = TicketCreator(TicketSystem.GITHUB, github_config)
            print("✅ GitHub ticket creator initialized")

    # ServiceNow configuration
    if os.getenv("SERVICENOW_ENABLED", "false").lower() == "true":
        servicenow_config = {
            "instance_url": os.getenv("SERVICENOW_INSTANCE_URL"),
            "access_token": os.getenv("SERVICENOW_ACCESS_TOKEN"),
            "assignment_group": os.getenv("SERVICENOW_ASSIGNMENT_GROUP", "")
        }
        if servicenow_config["instance_url"] and servicenow_config["access_token"]:
            ticket_creators["servicenow"] = TicketCreator(TicketSystem.SERVICENOW, servicenow_config)
            print("✅ ServiceNow ticket creator initialized")

    if not ticket_creators:
        print("⚠️  No ticket systems configured. Set *_ENABLED=true and required environment variables.")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    for creator in ticket_creators.values():
        await creator.client.aclose()

@app.post("/webhook")
async def alertmanager_webhook(alert_group: AlertGroup, background_tasks: BackgroundTasks, request: Request):
    """Handle Alertmanager webhook and create/close tickets"""
    print(f"📨 Received alert group: {alert_group.groupKey} ({len(alert_group.alerts)} alerts)")

    # Send alert to AI for processing
    background_tasks.add_task(send_alert_to_ai, alert_group)

    # Handle resolved alerts - close tickets
    if alert_group.status == "resolved":
        return await handle_resolved_alerts(alert_group, background_tasks)

    # Only process firing alerts
    if alert_group.status != "firing":
        return {"status": "ignored", "reason": "not firing status"}

    # Process each alert in the group
    for alert in alert_group.alerts:
        background_tasks.add_task(process_individual_alert, alert, alert_group)

    return {
        "status": "accepted",
        "alerts_count": len(alert_group.alerts)
    }

async def handle_resolved_alerts(alert_group: AlertGroup, background_tasks: BackgroundTasks):
    """Handle resolved alerts by closing corresponding tickets"""
    print(f"🔄 Processing resolved alerts for: {alert_group.groupKey}")

    # Extract ticket information from alert annotations (would be stored when ticket was created)
    # In a real implementation, you'd have a database mapping alerts to tickets
    # For now, we'll use a simple approach with alert fingerprints

    resolved_alerts = []

    for alert in alert_group.alerts:
        alert_name = alert.get("labels", {}).get("alertname", "Unknown")
        ticket_system = os.getenv("DEFAULT_TICKET_SYSTEM", "jira")
        ticket_id = f"auto-{hash(alert_name) % 10000:04d}"  # Simplified - would be stored in DB

        # Close ticket in background
        background_tasks.add_task(close_ticket_background, ticket_system, ticket_id, alert_name)

        resolved_alerts.append({
            "alert_name": alert_name,
            "ticket_system": ticket_system,
            "ticket_id": ticket_id
        })

    return {
        "status": "resolved_processed",
        "resolved_alerts": resolved_alerts,
        "alerts_count": len(alert_group.alerts)
    }

async def create_ticket_background(creator: TicketCreator, alert_group: AlertGroup, request: Request):
    """Create ticket in background task"""
    try:
        # Generate a unique key for this alert group to prevent duplicates
        alert_key = hashlib.md5(f"{alert_group.groupKey}:{alert_group.status}".encode()).hexdigest()

        # Check if we've already processed this alert (simple in-memory cache)
        # In production, you'd want to use Redis or a database for this
        if hasattr(create_ticket_background, '_processed_alerts'):
            if alert_key in create_ticket_background._processed_alerts:
                print(f"⚠️  Alert {alert_key} already processed, skipping")
                return
        else:
            create_ticket_background._processed_alerts = set()

        create_ticket_background._processed_alerts.add(alert_key)

        # Keep only recent alerts (prevent memory leak)
        if len(create_ticket_background._processed_alerts) > 1000:
            create_ticket_background._processed_alerts.clear()

        # Create the ticket
        result = await creator.create_ticket(alert_group)

        print(f"✅ Ticket created: {result['system']} #{result['ticket_id']} - {result['url']}")

    except Exception as e:
        print(f"❌ Failed to create ticket: {str(e)}")
        # In production, you'd want to retry or send to a dead letter queue

async def close_ticket_background(ticket_system: str, ticket_id: str, alert_name: str):
    """Close ticket in background task when alert is resolved"""
    try:
        # Get the appropriate ticket creator
        creator = get_ticket_creator(ticket_system)
        if not creator:
            print(f"⚠️  Ticket system '{ticket_system}' not configured for closure")
            return

        # Close the ticket
        resolution_reason = f"Alert '{alert_name}' has been resolved by the monitoring system"
        success = await creator.close_ticket(ticket_system, ticket_id, resolution_reason)

        if success:
            print(f"✅ Ticket closed: {ticket_system} #{ticket_id}")
        else:
            print(f"⚠️  Ticket closure may have failed: {ticket_system} #{ticket_id}")

    except Exception as e:
        print(f"❌ Failed to close ticket {ticket_system} #{ticket_id}: {str(e)}")

async def process_individual_alert(alert: dict, alert_group: AlertGroup):
    """Process individual alert: create ticket and emit events"""
    try:
        # Extract alert details
        severity = alert.get('labels', {}).get('severity', 'info')
        alertname = alert.get('labels', {}).get('alertname', 'Unknown Alert')

        # Create ticket title and description
        title = f"[{severity.upper()}] {alertname}"
        desc = f"**Summary:** {alert.get('annotations', {}).get('summary', 'N/A')}\n"
        desc += f"**Description:** {alert.get('annotations', {}).get('description', 'N/A')}\n"
        desc += f"**Alertmanager URL:** {alert_group.externalURL}"

        issue_url = None

        # Try to create ticket based on available systems
        if os.getenv("GITHUB_ENABLED", "false").lower() == "true":
            issue_url = await create_github_issue(title, desc)
        elif os.getenv("JIRA_ENABLED", "false").lower() == "true":
            issue_url = await create_jira_issue(title, desc)
        elif os.getenv("SERVICENOW_ENABLED", "false").lower() == "true":
            issue_url = await create_servicenow_issue(title, desc)

        # Import metrics and Redis client
        from cortex.incident_broadcast import INCIDENT_EVENT, redis_client

        # Emit Prometheus metric with issue URL
        labels = {
            "event": "created",
            "actor": "system",
            "severity": severity
        }
        if issue_url:
            labels["issue_url"] = issue_url

        INCIDENT_EVENT.labels(**labels).inc()

        # Emit Redis stream event
        event_data = {
            "event": "created",
            "actor": "system",
            "severity": severity,
            "alertname": alertname,
            "issue_url": issue_url or "",
            "timestamp": str(time.time())
        }
        redis_client.xadd("cortex:incidents", event_data)

        print(f"✅ Alert processed: {title} - Ticket: {issue_url}")

    except Exception as e:
        print(f"❌ Failed to process alert: {str(e)}")

async def create_github_issue(title: str, description: str) -> str:
    """Create GitHub issue and return URL"""
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        github_owner = os.getenv("GITHUB_OWNER")
        github_repo = os.getenv("GITHUB_REPO")

        if not all([github_token, github_owner, github_repo]):
            return None

        url = f"https://api.github.com/repos/{github_owner}/{github_repo}/issues"
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        payload = {
            "title": title,
            "body": description,
            "labels": ["alert", "brain-swarm", f"severity-{title.split(']')[0].strip('[').lower()}"]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            result = response.json()
            return result.get("html_url")

    except Exception as e:
        print(f"❌ Failed to create GitHub issue: {str(e)}")
        return None

async def create_jira_issue(title: str, description: str) -> str:
    """Create Jira issue and return URL"""
    try:
        jira_url = os.getenv("JIRA_BASE_URL")
        jira_username = os.getenv("JIRA_USERNAME")
        jira_token = os.getenv("JIRA_API_TOKEN")
        jira_project = os.getenv("JIRA_PROJECT_KEY", "ALERT")

        if not all([jira_url, jira_username, jira_token]):
            return None

        url = f"{jira_url}/rest/api/3/issue"
        auth = (jira_username, jira_token)

        payload = {
            "fields": {
                "project": {"key": jira_project},
                "summary": title,
                "description": description,
                "issuetype": {"name": "Bug"},
                "priority": {"name": "High" if "CRITICAL" in title else "Medium"}
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, auth=auth)
            response.raise_for_status()

            result = response.json()
            issue_key = result.get("key")
            return f"{jira_url}/browse/{issue_key}"

    except Exception as e:
        print(f"❌ Failed to create Jira issue: {str(e)}")
        return None

async def create_servicenow_issue(title: str, description: str) -> str:
    """Create ServiceNow incident and return URL"""
    try:
        sn_url = os.getenv("SERVICENOW_INSTANCE_URL")
        sn_token = os.getenv("SERVICENOW_ACCESS_TOKEN")

        if not all([sn_url, sn_token]):
            return None

        url = f"{sn_url}/api/now/table/incident"
        headers = {
            "Authorization": f"Bearer {sn_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "short_description": title,
            "description": description,
            "urgency": "1" if "CRITICAL" in title else "2",
            "impact": "2",
            "category": "Software",
            "subcategory": "Application"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            result = response.json()
            sys_id = result.get("result", {}).get("sys_id")
            return f"{sn_url}/nav_to.do?uri=incident.do?sys_id={sys_id}"

    except Exception as e:
        print(f"❌ Failed to create ServiceNow incident: {str(e)}")
        return None

async def send_alert_to_ai(alert_group: AlertGroup):
    """Send alert to AI orchestration endpoint for processing"""
    try:
        # Get API endpoint from environment
        api_base_url = os.getenv("BRAIN_SWARM_API_URL", "http://brain-swarm-api.brainswarm.svc.cluster.local:8000")
        api_url = f"{api_base_url}/alerts"

        # Prepare alert data using the shared schema
        alert_data = alert_group.dict()

        # Get auth token if available
        headers = {"Content-Type": "application/json"}
        auth_token = os.getenv("BRAIN_SWARM_API_TOKEN")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        # Send to AI endpoint
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_url, json=alert_data, headers=headers)
            response.raise_for_status()

            result = response.json()
            print(f"🤖 Alert sent to AI: {alert_group.groupKey} - Task: {result.get('task_id', 'unknown')}")

    except Exception as e:
        print(f"❌ Failed to send alert to AI: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "configured_systems": list(ticket_creators.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/systems")
async def list_systems():
    """List configured ticket systems"""
    return {
        "systems": list(ticket_creators.keys()),
        "total": len(ticket_creators)
    }

@app.post("/gh-webhook")
async def github_webhook(request: Request):
    """Handle GitHub webhook for issue closures"""
    try:
        payload = await request.json()
        event_type = request.headers.get("X-GitHub-Event")

        if event_type == "issues" and payload.get("action") == "closed":
            issue = payload.get("issue", {})
            issue_url = issue.get("html_url")
            issue_title = issue.get("title", "")

            # Extract incident ID from title (format: [CRITICAL] alertname)
            incident_id = issue_title.split("]")[1].strip() if "]" in issue_title else issue_title

            await mark_resolved_webhook(incident_id, issue_url, "github")
            return {"status": "processed", "incident_id": incident_id}

        return {"status": "ignored", "reason": "not issue closure"}

    except Exception as e:
        print(f"❌ GitHub webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/jira-webhook")
async def jira_webhook(request: Request):
    """Handle Jira webhook for issue transitions"""
    try:
        payload = await request.json()

        # Check if this is a status change to "Done"
        changelog = payload.get("changelog", {})
        items = changelog.get("items", [])

        for item in items:
            if item.get("field") == "status" and item.get("toString") == "Done":
                issue = payload.get("issue", {})
                issue_key = issue.get("key")
                issue_url = f"{os.getenv('JIRA_BASE_URL', 'https://jira.example.com')}/browse/{issue_key}"

                await mark_resolved_webhook(issue_key, issue_url, "jira")
                return {"status": "processed", "incident_id": issue_key}

        return {"status": "ignored", "reason": "not status change to done"}

    except Exception as e:
        print(f"❌ Jira webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/servicenow-webhook")
async def servicenow_webhook(request: Request):
    """Handle ServiceNow webhook for incident updates"""
    try:
        payload = await request.json()
        inc = payload.get("result") or payload
        sys_id = inc.get("sys_id")
        number = inc.get("number")
        state = inc.get("state")

        if not all([sys_id, number]):
            return {"status": "ignored", "reason": "missing required fields"}

        servicenow_url = os.getenv("SERVICENOW_INSTANCE_URL", "https://instance.servicenow.com")
        url = f"{servicenow_url}/nav_to.do?uri=incident.do?sys_id={sys_id}"

        # Check if incident is resolved/closed
        if state in ("7", "Resolved", "Closed") or str(state).lower() in ("resolved", "closed"):
            await mark_resolved_webhook(number, url, "servicenow")
            return {"status": "processed", "incident_id": number}

        return {"status": "ignored", "reason": "not resolution event"}

    except Exception as e:
        print(f"❌ ServiceNow webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

async def mark_resolved_webhook(incident_id: str, issue_url: str, system: str):
    """Mark incident as resolved from webhook"""
    from cortex.incident_broadcast import INCIDENT_EVENT, redis_client

    # Emit Redis event
    redis_client.xadd("cortex:incidents", {
        "event": "resolved",
        "actor": f"webhook-{system}",
        "issue_url": issue_url,
        "incident_id": incident_id,
        "timestamp": str(time.time())
    })

    # Emit Prometheus metrics
    INCIDENT_EVENT.labels(event="resolved", actor=f"webhook-{system}", severity="info").inc()

    print(f"✅ Webhook resolution: {incident_id} ({system}) - {issue_url}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)