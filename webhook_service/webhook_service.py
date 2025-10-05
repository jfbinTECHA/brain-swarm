"""
Main webhook service implementation for handling external webhooks.
"""

import asyncio
import json
import hmac
import hashlib
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from ..core.base import logger
from ..observability.metrics import prometheus_metrics
from ..observability.tracing import tracing_manager, get_correlation_id
from ..message_queue import message_queue


class WebhookSource(Enum):
    GITHUB = "github"
    JIRA = "jira"
    SERVICENOW = "servicenow"
    PROMETHEUS = "prometheus"
    CUSTOM = "custom"


@dataclass
class WebhookEvent:
    source: WebhookSource
    event_type: str
    payload: Dict[str, Any]
    headers: Dict[str, str]
    raw_body: bytes
    correlation_id: str
    timestamp: float


@dataclass
class ProcessedIncident:
    title: str
    description: str
    severity: str
    source: str
    external_id: str
    metadata: Dict[str, Any]
    tags: list[str]


class WebhookProcessor:
    """Base class for webhook processors"""

    def __init__(self, source: WebhookSource):
        self.source = source

    def validate_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Validate webhook signature"""
        raise NotImplementedError

    def process_event(self, event: WebhookEvent) -> Optional[ProcessedIncident]:
        """Process webhook event and return incident if applicable"""
        raise NotImplementedError


class GitHubWebhookProcessor(WebhookProcessor):
    """GitHub webhook processor"""

    def __init__(self):
        super().__init__(WebhookSource.GITHUB)

    def validate_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Validate GitHub webhook signature (HMAC-SHA256)"""
        if not signature.startswith('sha256='):
            return False

        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected_signature}", signature)

    def process_event(self, event: WebhookEvent) -> Optional[ProcessedIncident]:
        """Process GitHub webhook events"""
        event_type = event.headers.get('X-GitHub-Event', '')

        if event_type == 'issues':
            return self._process_issue_event(event.payload)
        elif event_type == 'pull_request':
            return self._process_pr_event(event.payload)
        elif event_type == 'workflow_run':
            return self._process_workflow_event(event.payload)

        return None

    def _process_issue_event(self, payload: Dict[str, Any]) -> Optional[ProcessedIncident]:
        """Process GitHub issue events"""
        action = payload.get('action')
        issue = payload.get('issue', {})

        if action in ['opened', 'reopened'] and issue.get('labels', []):
            # Check for critical labels
            labels = [label['name'] for label in issue.get('labels', [])]
            if any(label.lower() in ['bug', 'critical', 'security'] for label in labels):
                return ProcessedIncident(
                    title=f"GitHub Issue: {issue.get('title', 'Unknown')}",
                    description=f"Issue #{issue.get('number')}: {issue.get('body', '')[:500]}...",
                    severity=self._map_github_severity(labels),
                    source="github",
                    external_id=str(issue.get('number')),
                    metadata={
                        'repository': payload.get('repository', {}).get('full_name'),
                        'url': issue.get('html_url'),
                        'assignee': issue.get('assignee', {}).get('login') if issue.get('assignee') else None,
                        'labels': labels
                    },
                    tags=['github', 'issue'] + labels
                )

        return None

    def _process_pr_event(self, payload: Dict[str, Any]) -> Optional[ProcessedIncident]:
        """Process GitHub PR events"""
        action = payload.get('action')
        pr = payload.get('pull_request', {})

        if action == 'opened' and pr.get('requested_reviewers'):
            return ProcessedIncident(
                title=f"GitHub PR Review: {pr.get('title', 'Unknown')}",
                description=f"PR #{pr.get('number')} needs review: {pr.get('body', '')[:500]}...",
                severity="medium",
                source="github",
                external_id=str(pr.get('number')),
                metadata={
                    'repository': payload.get('repository', {}).get('full_name'),
                    'url': pr.get('html_url'),
                    'author': pr.get('user', {}).get('login'),
                    'reviewers': [r['login'] for r in pr.get('requested_reviewers', [])]
                },
                tags=['github', 'pull-request', 'review-needed']
            )

        return None

    def _process_workflow_event(self, payload: Dict[str, Any]) -> Optional[ProcessedIncident]:
        """Process GitHub workflow events"""
        workflow_run = payload.get('workflow_run', {})

        if workflow_run.get('conclusion') == 'failure':
            return ProcessedIncident(
                title=f"GitHub CI Failure: {workflow_run.get('name', 'Unknown')}",
                description=f"Workflow {workflow_run.get('name')} failed in {workflow_run.get('head_repository', {}).get('full_name')}",
                severity="high",
                source="github",
                external_id=str(workflow_run.get('id')),
                metadata={
                    'repository': workflow_run.get('head_repository', {}).get('full_name'),
                    'url': workflow_run.get('html_url'),
                    'branch': workflow_run.get('head_branch'),
                    'commit': workflow_run.get('head_sha')
                },
                tags=['github', 'ci', 'failure']
            )

        return None

    def _map_github_severity(self, labels: list[str]) -> str:
        """Map GitHub labels to severity levels"""
        label_str = ' '.join(labels).lower()
        if 'critical' in label_str or 'security' in label_str:
            return 'critical'
        elif 'high' in label_str or 'bug' in label_str:
            return 'high'
        elif 'medium' in label_str:
            return 'medium'
        else:
            return 'low'


class JiraWebhookProcessor(WebhookProcessor):
    """Jira webhook processor"""

    def __init__(self):
        super().__init__(WebhookSource.JIRA)

    def validate_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Validate Jira webhook signature"""
        # Jira doesn't use HMAC by default, but we can implement basic validation
        return True  # Implement proper validation based on Jira setup

    def process_event(self, event: WebhookEvent) -> Optional[ProcessedIncident]:
        """Process Jira webhook events"""
        webhook_event = event.payload.get('webhookEvent', '')

        if webhook_event == 'jira:issue_created':
            return self._process_issue_created(event.payload)
        elif webhook_event == 'jira:issue_updated':
            return self._process_issue_updated(event.payload)

        return None

    def _process_issue_created(self, payload: Dict[str, Any]) -> Optional[ProcessedIncident]:
        """Process Jira issue creation"""
        issue = payload.get('issue', {})

        # Check priority and issue type
        priority = issue.get('fields', {}).get('priority', {}).get('name', '').lower()
        issue_type = issue.get('fields', {}).get('issuetype', {}).get('name', '').lower()

        if priority in ['highest', 'critical'] or issue_type in ['bug', 'incident']:
            return ProcessedIncident(
                title=f"Jira Issue: {issue.get('fields', {}).get('summary', 'Unknown')}",
                description=f"Issue {issue.get('key')}: {issue.get('fields', {}).get('description', '')[:500]}...",
                severity=self._map_jira_severity(priority),
                source="jira",
                external_id=issue.get('key'),
                metadata={
                    'project': issue.get('fields', {}).get('project', {}).get('key'),
                    'url': f"{payload.get('baseUrl', '')}/browse/{issue.get('key')}",
                    'assignee': issue.get('fields', {}).get('assignee', {}).get('displayName') if issue.get('fields', {}).get('assignee') else None,
                    'priority': priority,
                    'issue_type': issue_type
                },
                tags=['jira', issue_type, priority]
            )

        return None

    def _process_issue_updated(self, payload: Dict[str, Any]) -> Optional[ProcessedIncident]:
        """Process Jira issue updates"""
        issue = payload.get('issue', {})
        changelog = payload.get('changelog', {})

        # Check for status changes to blocked or critical
        for item in changelog.get('items', []):
            if item.get('field') == 'status' and item.get('toString').lower() in ['blocked', 'critical']:
                return ProcessedIncident(
                    title=f"Jira Status Change: {issue.get('fields', {}).get('summary', 'Unknown')}",
                    description=f"Issue {issue.get('key')} status changed to {item.get('toString')}",
                    severity="high",
                    source="jira",
                    external_id=issue.get('key'),
                    metadata={
                        'project': issue.get('fields', {}).get('project', {}).get('key'),
                        'url': f"{payload.get('baseUrl', '')}/browse/{issue.get('key')}",
                        'old_status': item.get('fromString'),
                        'new_status': item.get('toString')
                    },
                    tags=['jira', 'status-change']
                )

        return None

    def _map_jira_severity(self, priority: str) -> str:
        """Map Jira priority to severity levels"""
        priority_map = {
            'highest': 'critical',
            'high': 'high',
            'medium': 'medium',
            'low': 'low',
            'lowest': 'low'
        }
        return priority_map.get(priority, 'medium')


class ServiceNowWebhookProcessor(WebhookProcessor):
    """ServiceNow webhook processor"""

    def __init__(self):
        super().__init__(WebhookSource.SERVICENOW)

    def validate_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Validate ServiceNow webhook signature"""
        # Implement ServiceNow signature validation if needed
        return True

    def process_event(self, event: WebhookEvent) -> Optional[ProcessedIncident]:
        """Process ServiceNow webhook events"""
        # ServiceNow typically sends incident data
        incident = event.payload.get('incident', event.payload)

        if incident and incident.get('state') in ['1', '2', 1, 2]:  # New or Active incidents
            return ProcessedIncident(
                title=f"ServiceNow Incident: {incident.get('short_description', 'Unknown')}",
                description=f"Incident {incident.get('number')}: {incident.get('description', '')[:500]}...",
                severity=self._map_servicenow_priority(incident.get('priority')),
                source="servicenow",
                external_id=incident.get('number'),
                metadata={
                    'assignment_group': incident.get('assignment_group', {}).get('display_value'),
                    'caller': incident.get('caller_id', {}).get('display_value'),
                    'category': incident.get('category'),
                    'subcategory': incident.get('subcategory'),
                    'impact': incident.get('impact'),
                    'urgency': incident.get('urgency')
                },
                tags=['servicenow', 'incident', f"priority-{incident.get('priority')}"]
            )

        return None

    def _map_servicenow_priority(self, priority: str) -> str:
        """Map ServiceNow priority to severity levels"""
        try:
            prio_num = int(priority)
            if prio_num == 1:
                return 'critical'
            elif prio_num == 2:
                return 'high'
            elif prio_num == 3:
                return 'medium'
            else:
                return 'low'
        except (ValueError, TypeError):
            return 'medium'


class WebhookService:
    """Main webhook service"""

    def __init__(self):
        self.processors: Dict[WebhookSource, WebhookProcessor] = {}
        self._register_processors()

    def _register_processors(self):
        """Register webhook processors"""
        self.processors[WebhookSource.GITHUB] = GitHubWebhookProcessor()
        self.processors[WebhookSource.JIRA] = JiraWebhookProcessor()
        self.processors[WebhookSource.SERVICENOW] = ServiceNowWebhookProcessor()

    async def process_webhook(
        self,
        source: str,
        headers: Dict[str, str],
        body: bytes,
        secret: Optional[str] = None
    ) -> Optional[ProcessedIncident]:
        """Process incoming webhook"""

        correlation_id = get_correlation_id()

        with tracing_manager.trace_context("webhook_processing", tags={"source": source}):
            try:
                # Parse source
                try:
                    webhook_source = WebhookSource(source.lower())
                except ValueError:
                    logger.log("WARNING", "WebhookService", f"Unknown webhook source: {source}")
                    return None

                # Get processor
                processor = self.processors.get(webhook_source)
                if not processor:
                    logger.log("WARNING", "WebhookService", f"No processor for source: {source}")
                    return None

                # Parse payload
                try:
                    payload = json.loads(body.decode('utf-8'))
                except json.JSONDecodeError as e:
                    logger.log("ERROR", "WebhookService", f"Invalid JSON payload: {e}")
                    prometheus_metrics.record_webhook_error(source, "invalid_json")
                    return None

                # Create webhook event
                event = WebhookEvent(
                    source=webhook_source,
                    event_type=headers.get('X-GitHub-Event', headers.get('X-Jira-Event', 'unknown')),
                    payload=payload,
                    headers=headers,
                    raw_body=body,
                    correlation_id=correlation_id,
                    timestamp=time.time()
                )

                # Validate signature if secret provided
                if secret and hasattr(processor, 'validate_signature'):
                    signature = headers.get('X-Hub-Signature-256', headers.get('X-Jira-Signature', ''))
                    if not processor.validate_signature(body, signature, secret):
                        logger.log("WARNING", "WebhookService", f"Invalid signature for {source}")
                        prometheus_metrics.record_webhook_error(source, "invalid_signature")
                        return None

                # Process event
                incident = processor.process_event(event)

                if incident:
                    # Record metrics
                    prometheus_metrics.record_webhook_processed(source, incident.severity)

                    # Log successful processing
                    logger.log("INFO", "WebhookService", f"Processed {source} webhook: {incident.title}")

                    # Publish to message queue for further processing
                    await message_queue.publish("webhook.incidents", {
                        "incident": incident.__dict__,
                        "correlation_id": correlation_id,
                        "timestamp": time.time()
                    })

                return incident

            except Exception as e:
                logger.log("ERROR", "WebhookService", f"Error processing webhook: {e}")
                prometheus_metrics.record_webhook_error(source, "processing_error")
                return None


# Global webhook service instance
webhook_service = WebhookService()