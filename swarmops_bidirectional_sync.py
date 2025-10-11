#!/usr/bin/env python3
"""
SwarmOps Bi-Directional Ticket Synchronization Service
Handles real-time and periodic synchronization between Brain Swarm incidents and external ticket systems.
Supports conflict resolution, retry mechanisms, and comprehensive monitoring.
"""

import asyncio
import os
import json
import time
import hashlib
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import httpx
import redis
from dataclasses import dataclass, asdict

from schemas.incident import AlertGroup
from cortex.incident_broadcast import INCIDENT_EVENT, redis_client


class SyncDirection(Enum):
    """Direction of synchronization"""
    INCIDENT_TO_TICKET = "incident_to_ticket"
    TICKET_TO_INCIDENT = "ticket_to_incident"


class SyncStatus(Enum):
    """Status of synchronization operations"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


@dataclass
class SyncRecord:
    """Record of a synchronization operation"""
    sync_id: str
    incident_id: str
    ticket_system: str
    ticket_id: str
    direction: SyncDirection
    status: SyncStatus
    created_at: float
    updated_at: float
    retry_count: int = 0
    error_message: Optional[str] = None
    last_ticket_status: Optional[str] = None
    last_incident_status: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['direction'] = self.direction.value
        data['status'] = self.status.value
        return data


class TicketSystem(Enum):
    """Supported ticket systems"""
    JIRA = "jira"
    GITHUB = "github"
    SERVICENOW = "servicenow"


class BiDirectionalSyncManager:
    """Manages bi-directional synchronization between incidents and tickets"""

    def __init__(self):
        self.redis = redis_client
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Configuration
        self.max_retries = int(os.getenv("SYNC_MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("SYNC_RETRY_DELAY", "60"))  # seconds
        self.poll_interval = int(os.getenv("SYNC_POLL_INTERVAL", "300"))  # 5 minutes
        self.conflict_resolution = os.getenv("SYNC_CONFLICT_RESOLUTION", "ticket_wins")  # or "incident_wins"

        # Ticket system configurations
        self.ticket_configs = self._load_ticket_configs()

        # Sync state tracking
        self.active_syncs: Set[str] = set()
        self.last_poll_times: Dict[str, float] = {}

    def _load_ticket_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load configuration for each ticket system"""
        configs = {}

        # GitHub
        if os.getenv("GITHUB_ENABLED", "false").lower() == "true":
            configs["github"] = {
                "token": os.getenv("GITHUB_TOKEN"),
                "owner": os.getenv("GITHUB_OWNER"),
                "repo": os.getenv("GITHUB_REPO"),
                "webhook_secret": os.getenv("GITHUB_WEBHOOK_SECRET")
            }

        # Jira
        if os.getenv("JIRA_ENABLED", "false").lower() == "true":
            configs["jira"] = {
                "url": os.getenv("JIRA_BASE_URL"),
                "username": os.getenv("JIRA_USERNAME"),
                "token": os.getenv("JIRA_API_TOKEN"),
                "project": os.getenv("JIRA_PROJECT_KEY", "ALERT")
            }

        # ServiceNow
        if os.getenv("SERVICENOW_ENABLED", "false").lower() == "true":
            configs["servicenow"] = {
                "url": os.getenv("SERVICENOW_INSTANCE_URL"),
                "token": os.getenv("SERVICENOW_ACCESS_TOKEN"),
                "assignment_group": os.getenv("SERVICENOW_ASSIGNMENT_GROUP")
            }

        return configs

    async def sync_incident_to_ticket(self, incident_id: str, ticket_system: str,
                                    incident_data: Dict[str, Any]) -> str:
        """Create or update ticket from incident data"""
        sync_id = f"sync_{incident_id}_{ticket_system}_{int(time.time())}"

        # Create sync record
        sync_record = SyncRecord(
            sync_id=sync_id,
            incident_id=incident_id,
            ticket_system=ticket_system,
            ticket_id="",  # Will be filled when ticket is created
            direction=SyncDirection.INCIDENT_TO_TICKET,
            status=SyncStatus.IN_PROGRESS,
            created_at=time.time(),
            updated_at=time.time()
        )

        # Store sync record
        self._store_sync_record(sync_record)

        try:
            # Create ticket based on system
            if ticket_system == "github":
                ticket_id = await self._create_github_issue(incident_data)
            elif ticket_system == "jira":
                ticket_id = await self._create_jira_issue(incident_data)
            elif ticket_system == "servicenow":
                ticket_id = await self._create_servicenow_incident(incident_data)
            else:
                raise ValueError(f"Unsupported ticket system: {ticket_system}")

            # Update sync record with success
            sync_record.ticket_id = ticket_id
            sync_record.status = SyncStatus.COMPLETED
            sync_record.updated_at = time.time()
            self._store_sync_record(sync_record)

            # Emit success event
            await self._emit_sync_event("completed", sync_record)

            return ticket_id

        except Exception as e:
            # Update sync record with failure
            sync_record.status = SyncStatus.FAILED
            sync_record.error_message = str(e)
            sync_record.retry_count += 1
            sync_record.updated_at = time.time()
            self._store_sync_record(sync_record)

            # Emit failure event
            await self._emit_sync_event("failed", sync_record)

            # Schedule retry if under max retries
            if sync_record.retry_count < self.max_retries:
                asyncio.create_task(self._retry_sync(sync_record, self.retry_delay))

            raise

    async def sync_ticket_to_incident(self, ticket_system: str, ticket_id: str,
                                    ticket_data: Dict[str, Any]) -> str:
        """Create or update incident from ticket data"""
        incident_id = f"ticket_{ticket_system}_{ticket_id}"

        sync_id = f"sync_{incident_id}_{int(time.time())}"

        # Create sync record
        sync_record = SyncRecord(
            sync_id=sync_id,
            incident_id=incident_id,
            ticket_system=ticket_system,
            ticket_id=ticket_id,
            direction=SyncDirection.TICKET_TO_INCIDENT,
            status=SyncStatus.IN_PROGRESS,
            created_at=time.time(),
            updated_at=time.time(),
            last_ticket_status=ticket_data.get("status")
        )

        # Store sync record
        self._store_sync_record(sync_record)

        try:
            # Check if incident already exists
            existing_incident = await self._get_incident_by_ticket(ticket_system, ticket_id)

            if existing_incident:
                # Update existing incident
                await self._update_incident_from_ticket(existing_incident, ticket_data)
                incident_id = existing_incident["id"]
            else:
                # Create new incident
                incident_id = await self._create_incident_from_ticket(ticket_data)

            # Update sync record with success
            sync_record.incident_id = incident_id
            sync_record.status = SyncStatus.COMPLETED
            sync_record.updated_at = time.time()
            self._store_sync_record(sync_record)

            # Emit success event
            await self._emit_sync_event("completed", sync_record)

            return incident_id

        except Exception as e:
            # Update sync record with failure
            sync_record.status = SyncStatus.FAILED
            sync_record.error_message = str(e)
            sync_record.retry_count += 1
            sync_record.updated_at = time.time()
            self._store_sync_record(sync_record)

            # Emit failure event
            await self._emit_sync_event("failed", sync_record)

            raise

    async def poll_ticket_updates(self):
        """Poll ticket systems for updates"""
        print("🔄 Polling ticket systems for updates...")

        tasks = []
        for system, config in self.ticket_configs.items():
            if system == "github":
                tasks.append(self._poll_github_updates())
            elif system == "jira":
                tasks.append(self._poll_jira_updates())
            elif system == "servicenow":
                tasks.append(self._poll_servicenow_updates())

        await asyncio.gather(*tasks, return_exceptions=True)
        print("✅ Ticket polling completed")

    async def handle_webhook_update(self, ticket_system: str, webhook_data: Dict[str, Any]):
        """Handle real-time webhook updates from ticket systems"""
        print(f"🎣 Processing webhook from {ticket_system}")

        try:
            # Extract ticket information from webhook
            ticket_info = self._parse_webhook_data(ticket_system, webhook_data)

            if ticket_info:
                # Find corresponding sync record
                sync_record = self._find_sync_by_ticket(ticket_system, ticket_info["id"])

                if sync_record:
                    # Handle status update
                    await self._handle_ticket_status_update(sync_record, ticket_info)
                else:
                    # New ticket, create incident
                    await self.sync_ticket_to_incident(ticket_system, ticket_info["id"], ticket_info)

        except Exception as e:
            print(f"❌ Webhook processing error: {e}")

    async def resolve_conflicts(self):
        """Resolve synchronization conflicts based on configured strategy"""
        print("🔧 Resolving sync conflicts...")

        # Find conflicting sync records
        conflicts = self._find_conflicting_syncs()

        for conflict in conflicts:
            try:
                await self._resolve_single_conflict(conflict)
            except Exception as e:
                print(f"❌ Conflict resolution failed for {conflict['sync_id']}: {e}")

    async def get_sync_status(self, incident_id: Optional[str] = None,
                            ticket_system: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get synchronization status"""
        # Query Redis for sync records
        pattern = "sync_record:*"
        if incident_id:
            pattern = f"sync_record:{incident_id}:*"
        elif ticket_system:
            # This would require a secondary index in Redis
            pass

        keys = self.redis.keys(pattern)
        records = []

        for key in keys:
            data = self.redis.hgetall(key)
            if data:
                # Convert string values back to appropriate types
                record = SyncRecord(
                    sync_id=data.get("sync_id", ""),
                    incident_id=data.get("incident_id", ""),
                    ticket_system=data.get("ticket_system", ""),
                    ticket_id=data.get("ticket_id", ""),
                    direction=SyncDirection(data.get("direction", "incident_to_ticket")),
                    status=SyncStatus(data.get("status", "pending")),
                    created_at=float(data.get("created_at", 0)),
                    updated_at=float(data.get("updated_at", 0)),
                    retry_count=int(data.get("retry_count", 0)),
                    error_message=data.get("error_message"),
                    last_ticket_status=data.get("last_ticket_status"),
                    last_incident_status=data.get("last_incident_status")
                )
                records.append(record.to_dict())

        return records

    # Private methods for ticket system operations

    async def _create_github_issue(self, incident_data: Dict[str, Any]) -> str:
        """Create GitHub issue from incident data"""
        config = self.ticket_configs["github"]
        url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/issues"

        headers = {
            "Authorization": f"token {config['token']}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Format incident data for GitHub
        title = self._format_incident_title(incident_data)
        body = self._format_incident_body(incident_data, "github")

        payload = {
            "title": title,
            "body": body,
            "labels": self._get_incident_labels(incident_data, "github")
        }

        response = await self.http_client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()
        return str(result["number"])

    async def _create_jira_issue(self, incident_data: Dict[str, Any]) -> str:
        """Create Jira issue from incident data"""
        config = self.ticket_configs["jira"]
        url = f"{config['url']}/rest/api/3/issue"

        # Format incident data for Jira
        payload = {
            "fields": {
                "project": {"key": config["project"]},
                "summary": self._format_incident_title(incident_data),
                "description": self._format_incident_body(incident_data, "jira"),
                "issuetype": {"name": "Bug"},
                "priority": {"name": self._map_severity_to_priority(incident_data.get("severity", "medium"))},
                "labels": self._get_incident_labels(incident_data, "jira")
            }
        }

        auth = (config["username"], config["token"])
        response = await self.http_client.post(url, json=payload, auth=auth)
        response.raise_for_status()

        result = response.json()
        return result["key"]

    async def _create_servicenow_incident(self, incident_data: Dict[str, Any]) -> str:
        """Create ServiceNow incident from incident data"""
        config = self.ticket_configs["servicenow"]
        url = f"{config['url']}/api/now/table/incident"

        headers = {
            "Authorization": f"Bearer {config['token']}",
            "Content-Type": "application/json"
        }

        payload = {
            "short_description": self._format_incident_title(incident_data),
            "description": self._format_incident_body(incident_data, "servicenow"),
            "urgency": self._map_severity_to_urgency(incident_data.get("severity", "medium")),
            "impact": "3",
            "category": "Software",
            "subcategory": "Application",
            "assignment_group": config.get("assignment_group", "")
        }

        response = await self.http_client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()
        return result["result"]["number"]

    async def _poll_github_updates(self):
        """Poll GitHub for recent issue updates"""
        config = self.ticket_configs["github"]
        last_poll = self.last_poll_times.get("github", time.time() - 3600)  # 1 hour ago

        url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/issues"
        params = {
            "state": "all",
            "sort": "updated",
            "direction": "desc",
            "per_page": 50,
            "since": datetime.fromtimestamp(last_poll).isoformat()
        }

        headers = {"Authorization": f"token {config['token']}"}

        response = await self.http_client.get(url, params=params, headers=headers)
        response.raise_for_status()

        issues = response.json()
        for issue in issues:
            # Process issue updates
            ticket_data = {
                "id": str(issue["number"]),
                "title": issue["title"],
                "status": "closed" if issue["state"] == "closed" else "open",
                "updated_at": issue["updated_at"],
                "url": issue["html_url"]
            }

            await self.handle_webhook_update("github", {"issue": ticket_data})

        self.last_poll_times["github"] = time.time()

    async def _poll_jira_updates(self):
        """Poll Jira for recent issue updates"""
        config = self.ticket_configs["jira"]

        # JQL to find recently updated issues
        jql = f'project = {config["project"]} AND updated >= -15m'
        url = f"{config['url']}/rest/api/3/search"
        params = {"jql": jql, "maxResults": 50}

        auth = (config["username"], config["token"])
        response = await self.http_client.get(url, params=params, auth=auth)
        response.raise_for_status()

        result = response.json()
        for issue in result.get("issues", []):
            ticket_data = {
                "id": issue["key"],
                "title": issue["fields"]["summary"],
                "status": issue["fields"]["status"]["name"],
                "updated_at": issue["fields"]["updated"],
                "url": f"{config['url']}/browse/{issue['key']}"
            }

            await self.handle_webhook_update("jira", {"issue": ticket_data})

    async def _poll_servicenow_updates(self):
        """Poll ServiceNow for recent incident updates"""
        config = self.ticket_configs["servicenow"]

        url = f"{config['url']}/api/now/table/incident"
        params = {
            "sysparm_query": "sys_updated_onONLast 15 minutes@javascript:gs.beginningOfLast15Minutes()",
            "sysparm_limit": 50
        }

        headers = {"Authorization": f"Bearer {config['token']}"}
        response = await self.http_client.get(url, params=params, headers=headers)
        response.raise_for_status()

        result = response.json()
        for incident in result.get("result", []):
            ticket_data = {
                "id": incident["number"],
                "title": incident["short_description"],
                "status": incident["state"],
                "updated_at": incident["sys_updated_on"],
                "url": f"{config['url']}/nav_to.do?uri=incident.do?sys_id={incident['sys_id']}"
            }

            await self.handle_webhook_update("servicenow", {"incident": ticket_data})

    # Helper methods

    def _store_sync_record(self, record: SyncRecord):
        """Store sync record in Redis"""
        key = f"sync_record:{record.incident_id}:{record.ticket_system}"
        self.redis.hset(key, record.to_dict())

        # Also store by ticket for reverse lookup
        ticket_key = f"ticket_sync:{record.ticket_system}:{record.ticket_id}"
        self.redis.set(ticket_key, record.sync_id)

    def _find_sync_by_ticket(self, ticket_system: str, ticket_id: str) -> Optional[SyncRecord]:
        """Find sync record by ticket information"""
        ticket_key = f"ticket_sync:{ticket_system}:{ticket_id}"
        sync_id = self.redis.get(ticket_key)

        if sync_id:
            # Find the sync record
            pattern = f"sync_record:*:*"
            for key in self.redis.keys(pattern):
                data = self.redis.hgetall(key)
                if data.get("sync_id") == sync_id:
                    return SyncRecord(
                        sync_id=data.get("sync_id", ""),
                        incident_id=data.get("incident_id", ""),
                        ticket_system=data.get("ticket_system", ""),
                        ticket_id=data.get("ticket_id", ""),
                        direction=SyncDirection(data.get("direction", "incident_to_ticket")),
                        status=SyncStatus(data.get("status", "pending")),
                        created_at=float(data.get("created_at", 0)),
                        updated_at=float(data.get("updated_at", 0)),
                        retry_count=int(data.get("retry_count", 0)),
                        error_message=data.get("error_message"),
                        last_ticket_status=data.get("last_ticket_status"),
                        last_incident_status=data.get("last_incident_status")
                    )

        return None

    def _find_conflicting_syncs(self) -> List[Dict[str, Any]]:
        """Find sync records with conflicts"""
        conflicts = []
        # Implementation would check for records with different statuses
        # between incident and ticket systems
        return conflicts

    async def _retry_sync(self, record: SyncRecord, delay: int):
        """Retry a failed sync operation"""
        await asyncio.sleep(delay)

        try:
            if record.direction == SyncDirection.INCIDENT_TO_TICKET:
                # Retry incident to ticket sync
                incident_data = await self._get_incident_data(record.incident_id)
                await self.sync_incident_to_ticket(record.incident_id, record.ticket_system, incident_data)
            else:
                # Retry ticket to incident sync
                ticket_data = await self._get_ticket_data(record.ticket_system, record.ticket_id)
                await self.sync_ticket_to_incident(record.ticket_system, record.ticket_id, ticket_data)
        except Exception as e:
            print(f"❌ Retry failed for {record.sync_id}: {e}")

    async def _emit_sync_event(self, event_type: str, record: SyncRecord):
        """Emit synchronization event"""
        event_data = {
            "event": f"sync_{event_type}",
            "sync_id": record.sync_id,
            "incident_id": record.incident_id,
            "ticket_system": record.ticket_system,
            "ticket_id": record.ticket_id,
            "direction": record.direction.value,
            "status": record.status.value,
            "timestamp": time.time()
        }

        if record.error_message:
            event_data["error"] = record.error_message

        self.redis.xadd("cortex:sync_events", event_data)

        # Emit Prometheus metric
        INCIDENT_EVENT.labels(
            event=f"sync_{event_type}",
            actor="sync_manager",
            severity="info"
        ).inc()

    # Placeholder methods (would be implemented based on actual data storage)
    async def _get_incident_data(self, incident_id: str) -> Dict[str, Any]:
        """Get incident data (placeholder)"""
        return {"id": incident_id, "severity": "high", "title": f"Incident {incident_id}"}

    async def _get_ticket_data(self, system: str, ticket_id: str) -> Dict[str, Any]:
        """Get ticket data (placeholder)"""
        return {"id": ticket_id, "status": "open", "title": f"Ticket {ticket_id}"}

    async def _get_incident_by_ticket(self, system: str, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Find incident by ticket (placeholder)"""
        return None

    async def _create_incident_from_ticket(self, ticket_data: Dict[str, Any]) -> str:
        """Create incident from ticket (placeholder)"""
        return f"incident_from_ticket_{ticket_data['id']}"

    async def _update_incident_from_ticket(self, incident: Dict[str, Any], ticket_data: Dict[str, Any]):
        """Update incident from ticket (placeholder)"""
        pass

    async def _handle_ticket_status_update(self, sync_record: SyncRecord, ticket_info: Dict[str, Any]):
        """Handle ticket status update (placeholder)"""
        pass

    def _parse_webhook_data(self, system: str, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse webhook data to extract ticket information"""
        if system == "github" and "issue" in webhook_data:
            issue = webhook_data["issue"]
            return {
                "id": str(issue["number"]),
                "title": issue["title"],
                "status": "closed" if issue.get("state") == "closed" else "open",
                "updated_at": issue.get("updated_at"),
                "url": issue.get("html_url")
            }
        elif system == "jira" and "issue" in webhook_data:
            issue = webhook_data["issue"]
            return {
                "id": issue["key"],
                "title": issue["fields"]["summary"],
                "status": issue["fields"]["status"]["name"],
                "updated_at": issue["fields"]["updated"],
                "url": f"{self.ticket_configs['jira']['url']}/browse/{issue['key']}"
            }
        elif system == "servicenow" and "incident" in webhook_data:
            inc = webhook_data["incident"]
            return {
                "id": inc["number"],
                "title": inc["short_description"],
                "status": inc["state"],
                "updated_at": inc["sys_updated_on"],
                "url": f"{self.ticket_configs['servicenow']['url']}/nav_to.do?uri=incident.do?sys_id={inc['sys_id']}"
            }

        return None

    def _format_incident_title(self, incident: Dict[str, Any]) -> str:
        """Format incident data into ticket title"""
        severity = incident.get("severity", "unknown").upper()
        title = incident.get("title", incident.get("id", "Unknown Incident"))
        return f"[{severity}] {title}"

    def _format_incident_body(self, incident: Dict[str, Any], system: str) -> str:
        """Format incident data into ticket body"""
        body = f"**Incident ID:** {incident.get('id', 'N/A')}\n"
        body += f"**Severity:** {incident.get('severity', 'N/A')}\n"
        body += f"**Status:** {incident.get('status', 'N/A')}\n"
        body += f"**Description:** {incident.get('description', 'N/A')}\n"

        if incident.get("url"):
            body += f"**Incident URL:** {incident['url']}\n"

        body += f"**Created:** {datetime.now().isoformat()}\n"
        body += f"**Source:** Brain Swarm Incident Management\n"

        return body

    def _get_incident_labels(self, incident: Dict[str, Any], system: str) -> List[str]:
        """Get appropriate labels for the incident"""
        labels = ["brain-swarm", "incident"]

        severity = incident.get("severity", "unknown")
        if severity:
            labels.append(f"severity-{severity}")

        status = incident.get("status", "unknown")
        if status:
            labels.append(f"status-{status}")

        return labels

    def _map_severity_to_priority(self, severity: str) -> str:
        """Map severity to Jira priority"""
        mapping = {
            "critical": "Highest",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
            "info": "Lowest"
        }
        return mapping.get(severity.lower(), "Medium")

    def _map_severity_to_urgency(self, severity: str) -> str:
        """Map severity to ServiceNow urgency"""
        mapping = {
            "critical": "1",
            "high": "2",
            "medium": "2",
            "low": "3",
            "info": "3"
        }
        return mapping.get(severity.lower(), "2")


# Global sync manager instance
sync_manager = BiDirectionalSyncManager()


async def run_sync_service():
    """Run the bi-directional sync service"""
    print("🔄 Starting Brain Swarm Bi-Directional Sync Service")

    while True:
        try:
            # Poll for updates
            await sync_manager.poll_ticket_updates()

            # Resolve conflicts
            await sync_manager.resolve_conflicts()

            # Clean up old sync records (older than 30 days)
            # Implementation would go here

        except Exception as e:
            print(f"❌ Sync service error: {e}")

        await asyncio.sleep(sync_manager.poll_interval)


async def handle_webhook_endpoint(ticket_system: str, webhook_data: Dict[str, Any]):
    """Handle webhook from ticket system"""
    await sync_manager.handle_webhook_update(ticket_system, webhook_data)


if __name__ == "__main__":
    # Run sync service
    asyncio.run(run_sync_service())