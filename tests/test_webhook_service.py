"""
Tests for webhook service.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock

from webhook_service.webhook_service import (
    WebhookService,
    GitHubWebhookProcessor,
    JiraWebhookProcessor,
    ServiceNowWebhookProcessor,
    WebhookEvent,
    WebhookSource,
    ProcessedIncident
)


class TestGitHubWebhookProcessor:
    """Test GitHub webhook processor"""

    def setup_method(self):
        self.processor = GitHubWebhookProcessor()

    def test_validate_signature_valid(self):
        """Test valid signature validation"""
        payload = b'{"test": "data"}'
        secret = "test_secret"
        signature = "sha256=" + "f7e7b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8"

        # Mock the expected signature
        with patch('hmac.new') as mock_hmac:
            mock_hash = Mock()
            mock_hash.hexdigest.return_value = "f7e7b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8b6e8"
            mock_hmac.return_value = mock_hash

            assert self.processor.validate_signature(payload, signature, secret)

    def test_validate_signature_invalid_prefix(self):
        """Test invalid signature prefix"""
        payload = b'{"test": "data"}'
        signature = "invalid_prefix"
        secret = "test_secret"

        assert not self.processor.validate_signature(payload, signature, secret)

    def test_process_issue_event_critical(self):
        """Test processing critical GitHub issue"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Critical Security Issue",
                "body": "This is a critical security vulnerability",
                "html_url": "https://github.com/test/repo/issues/123",
                "labels": [
                    {"name": "security"},
                    {"name": "critical"}
                ]
            },
            "repository": {
                "full_name": "test/repo"
            }
        }

        event = WebhookEvent(
            source=WebhookSource.GITHUB,
            event_type="issues",
            payload=payload,
            headers={"X-GitHub-Event": "issues"},
            raw_body=json.dumps(payload).encode(),
            correlation_id="test-123",
            timestamp=1234567890
        )

        result = self.processor.process_event(event)

        assert result is not None
        assert result.title == "GitHub Issue: Critical Security Issue"
        assert result.severity == "critical"
        assert result.source == "github"
        assert result.external_id == "123"
        assert "security" in result.tags
        assert "critical" in result.tags

    def test_process_issue_event_non_critical(self):
        """Test processing non-critical GitHub issue"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 124,
                "title": "Minor Enhancement",
                "body": "This is a minor enhancement request",
                "html_url": "https://github.com/test/repo/issues/124",
                "labels": [
                    {"name": "enhancement"}
                ]
            },
            "repository": {
                "full_name": "test/repo"
            }
        }

        event = WebhookEvent(
            source=WebhookSource.GITHUB,
            event_type="issues",
            payload=payload,
            headers={"X-GitHub-Event": "issues"},
            raw_body=json.dumps(payload).encode(),
            correlation_id="test-124",
            timestamp=1234567890
        )

        result = self.processor.process_event(event)

        assert result is None  # Should not create incident for non-critical issues


class TestJiraWebhookProcessor:
    """Test Jira webhook processor"""

    def setup_method(self):
        self.processor = JiraWebhookProcessor()

    def test_process_issue_created_critical(self):
        """Test processing critical Jira issue"""
        payload = {
            "webhookEvent": "jira:issue_created",
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "summary": "Critical System Outage",
                    "description": "The main database is down",
                    "priority": {"name": "Highest"},
                    "issuetype": {"name": "Incident"},
                    "project": {"key": "PROJ"},
                    "assignee": {"displayName": "John Doe"}
                }
            },
            "baseUrl": "https://company.atlassian.net"
        }

        event = WebhookEvent(
            source=WebhookSource.JIRA,
            event_type="issue_created",
            payload=payload,
            headers={},
            raw_body=json.dumps(payload).encode(),
            correlation_id="test-jira-123",
            timestamp=1234567890
        )

        result = self.processor.process_event(event)

        assert result is not None
        assert result.title == "Jira Issue: Critical System Outage"
        assert result.severity == "critical"
        assert result.source == "jira"
        assert result.external_id == "PROJ-123"
        assert "highest" in result.tags


class TestServiceNowWebhookProcessor:
    """Test ServiceNow webhook processor"""

    def setup_method(self):
        self.processor = ServiceNowWebhookProcessor()

    def test_process_incident_critical(self):
        """Test processing critical ServiceNow incident"""
        payload = {
            "number": "INC0012345",
            "short_description": "Database Server Down",
            "description": "The primary database server is unresponsive",
            "state": "1",  # New
            "priority": "1",  # Critical
            "assignment_group": {"display_value": "Database Team"},
            "caller_id": {"display_value": "Jane Smith"},
            "category": "Database",
            "subcategory": "Performance",
            "impact": "1",
            "urgency": "1"
        }

        event = WebhookEvent(
            source=WebhookSource.SERVICENOW,
            event_type="incident",
            payload=payload,
            headers={},
            raw_body=json.dumps(payload).encode(),
            correlation_id="test-snow-123",
            timestamp=1234567890
        )

        result = self.processor.process_event(event)

        assert result is not None
        assert result.title == "ServiceNow Incident: Database Server Down"
        assert result.severity == "critical"
        assert result.source == "servicenow"
        assert result.external_id == "INC0012345"
        assert result.metadata["assignment_group"] == "Database Team"


class TestWebhookService:
    """Test main webhook service"""

    def setup_method(self):
        self.service = WebhookService()

    @pytest.mark.asyncio
    async def test_process_github_webhook(self):
        """Test processing GitHub webhook through service"""
        headers = {
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": "sha256=test"
        }

        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Critical Bug",
                "body": "This is critical",
                "html_url": "https://github.com/test/repo/issues/123",
                "labels": [{"name": "bug"}, {"name": "critical"}]
            },
            "repository": {"full_name": "test/repo"}
        }

        body = json.dumps(payload).encode()

        # Mock the processor to skip signature validation
        with patch.object(self.service.processors[WebhookSource.GITHUB], 'validate_signature', return_value=True):
            result = await self.service.process_webhook("github", headers, body)

        assert result is not None
        assert result.severity == "critical"
        assert result.source == "github"

    @pytest.mark.asyncio
    async def test_process_unknown_source(self):
        """Test processing webhook from unknown source"""
        headers = {}
        body = b'{"test": "data"}'

        result = await self.service.process_webhook("unknown", headers, body)

        assert result is None

    @pytest.mark.asyncio
    async def test_process_invalid_json(self):
        """Test processing invalid JSON payload"""
        headers = {"X-GitHub-Event": "issues"}
        body = b'invalid json'

        result = await self.service.process_webhook("github", headers, body)

        assert result is None