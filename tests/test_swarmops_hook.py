"""
Tests for SwarmOps Alert Webhook Handler with bi-directional sync integration.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from swarmops_hook import (
    app,
    TicketCreator,
    TicketSystem,
    get_ticket_creator,
    create_github_issue,
    create_jira_issue,
    create_servicenow_issue,
    handle_resolved_alerts,
    process_individual_alert
)


class TestTicketCreator:
    """Test TicketCreator class"""

    @pytest.fixture
    def ticket_creator(self):
        """Create a ticket creator instance"""
        config = {
            "base_url": "https://api.github.com",
            "owner": "testorg",
            "repo": "testrepo",
            "token": "test_token"
        }
        return TicketCreator(TicketSystem.GITHUB, config)

    def test_initialization(self, ticket_creator):
        """Test ticket creator initialization"""
        assert ticket_creator.system == TicketSystem.GITHUB
        assert ticket_creator.config["owner"] == "testorg"
        assert isinstance(ticket_creator.client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_create_ticket_github(self, ticket_creator):
        """Test creating GitHub ticket"""
        alert_group = Mock()
        alert_group.commonLabels = {
            "alertname": "Test Alert",
            "service": "test-service",
            "severity": "critical"
        }
        alert_group.commonAnnotations = {
            "summary": "Test Summary",
            "description": "Test Description"
        }
        alert_group.externalURL = "http://prometheus:9090/alert"

        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {"number": 123, "html_url": "https://github.com/test/issue/123"}
        ticket_creator.client.post = AsyncMock(return_value=mock_response)

        result = await ticket_creator.create_ticket(alert_group)

        assert result["system"] == "github"
        assert result["ticket_id"] == "123"
        assert result["created"] is True

    @pytest.mark.asyncio
    async def test_close_ticket_success(self, ticket_creator):
        """Test closing ticket successfully"""
        # Mock GitHub API for repository dispatch
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        ticket_creator.client.post = AsyncMock(return_value=mock_response)

        with patch.dict('os.environ', {
            'GITHUB_TOKEN': 'test_token',
            'GITHUB_OWNER': 'testorg',
            'GITHUB_REPO': 'testrepo'
        }):
            success = await ticket_creator.close_ticket("github", "123", "Alert resolved")

            assert success is True
            ticket_creator.client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_ticket_no_github_config(self, ticket_creator):
        """Test closing ticket without GitHub configuration"""
        with patch.dict('os.environ', {}, clear=True):
            success = await ticket_creator.close_ticket("github", "123", "Alert resolved")

            assert success is False


class TestWebhookEndpoints:
    """Test webhook endpoint handlers"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "configured_systems" in data
        assert "timestamp" in data

    def test_systems_endpoint(self, client):
        """Test systems endpoint"""
        response = client.get("/systems")
        assert response.status_code == 200

        data = response.json()
        assert "systems" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_alertmanager_webhook_firing(self):
        """Test Alertmanager webhook with firing alerts"""
        from fastapi.testclient import TestClient
        client = TestClient(app)

        alert_group = {
            "receiver": "brain-swarm",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "HighCPUUsage",
                        "service": "web-server",
                        "severity": "critical",
                        "instance": "web-01:9100"
                    },
                    "annotations": {
                        "description": "CPU usage is above 90% for 5 minutes",
                        "summary": "High CPU usage detected"
                    },
                    "startsAt": "2023-10-05T21:45:00Z",
                    "endsAt": "0001-01-01T00:00:00Z",
                    "generatorURL": "http://prometheus:9090/graph?g0.expr=cpu_usage_percent%7Binstance%3D%22web-01%3A9100%22%7D+%3E+90&g0.tab=1",
                    "fingerprint": "abcd1234"
                }
            ],
            "groupLabels": {
                "alertname": "HighCPUUsage",
                "service": "web-server"
            },
            "commonLabels": {
                "alertname": "HighCPUUsage",
                "service": "web-server",
                "severity": "critical",
                "instance": "web-01:9100"
            },
            "commonAnnotations": {
                "description": "CPU usage is above 90% for 5 minutes",
                "summary": "High CPU usage detected"
            },
            "externalURL": "http://alertmanager:9093",
            "version": "4",
            "groupKey": "{}:{alertname=\"HighCPUUsage\", service=\"web-server\"}",
            "truncatedAlerts": 0
        }

        # Mock the AI processing
        with patch('swarmops_hook.send_alert_to_ai', new_callable=AsyncMock) as mock_ai:
            with patch('swarmops_hook.process_individual_alert', new_callable=AsyncMock) as mock_process:
                response = client.post("/webhook", json=alert_group)

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "accepted"
                assert data["alerts_count"] == 1

                mock_ai.assert_called_once()
                mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_alertmanager_webhook_resolved(self):
        """Test Alertmanager webhook with resolved alerts"""
        from fastapi.testclient import TestClient
        client = TestClient(app)

        alert_group = {
            "receiver": "brain-swarm",
            "status": "resolved",
            "alerts": [
                {
                    "status": "resolved",
                    "labels": {
                        "alertname": "HighCPUUsage",
                        "service": "web-server",
                        "severity": "critical"
                    },
                    "annotations": {
                        "description": "CPU usage has returned to normal",
                        "summary": "High CPU usage resolved"
                    }
                }
            ],
            "groupLabels": {"alertname": "HighCPUUsage"},
            "commonLabels": {"alertname": "HighCPUUsage", "severity": "critical"},
            "commonAnnotations": {"summary": "High CPU usage resolved"},
            "externalURL": "http://alertmanager:9093",
            "version": "4",
            "groupKey": "{}:{alertname=\"HighCPUUsage\"}"
        }

        with patch('swarmops_hook.handle_resolved_alerts', new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = {"status": "resolved_processed", "alerts_count": 1}

            response = client.post("/webhook", json=alert_group)

            assert response.status_code == 200
            mock_handle.assert_called_once()

    def test_github_webhook_issue_closed(self, client):
        """Test GitHub webhook for issue closure"""
        headers = {
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": "sha256=test"
        }

        payload = {
            "action": "closed",
            "issue": {
                "number": 123,
                "title": "[CRITICAL] High CPU Usage",
                "html_url": "https://github.com/test/repo/issues/123",
                "state": "closed"
            },
            "repository": {
                "full_name": "test/repo"
            }
        }

        with patch('swarmops_hook.mark_resolved_webhook', new_callable=AsyncMock) as mock_mark:
            response = client.post("/gh-webhook", json=payload, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert data["incident_id"] == "High CPU Usage"

            mock_mark.assert_called_once_with("High CPU Usage", "https://github.com/test/repo/issues/123", "github")

    def test_jira_webhook_issue_transition(self, client):
        """Test Jira webhook for issue status change"""
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "summary": "Critical System Outage",
                    "status": {"name": "Done"}
                }
            },
            "changelog": {
                "items": [
                    {
                        "field": "status",
                        "fromString": "In Progress",
                        "toString": "Done"
                    }
                ]
            }
        }

        with patch('swarmops_hook.mark_resolved_webhook', new_callable=AsyncMock) as mock_mark:
            response = client.post("/jira-webhook", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert data["incident_id"] == "PROJ-123"

            mock_mark.assert_called_once_with("PROJ-123", "https://jira.example.com/browse/PROJ-123", "jira")

    def test_servicenow_webhook_incident_resolved(self, client):
        """Test ServiceNow webhook for incident resolution"""
        payload = {
            "number": "INC001234",
            "short_description": "Database Server Down",
            "state": "7",  # Resolved
            "sys_updated_on": "2023-10-05 12:00:00",
            "sys_id": "sys123"
        }

        with patch('swarmops_hook.mark_resolved_webhook', new_callable=AsyncMock) as mock_mark:
            response = client.post("/servicenow-webhook", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert data["incident_id"] == "INC001234"

            mock_mark.assert_called_once()


class TestTicketCreationFunctions:
    """Test individual ticket creation functions"""

    @pytest.mark.asyncio
    async def test_create_github_issue_success(self):
        """Test successful GitHub issue creation"""
        with patch.dict('os.environ', {
            'GITHUB_TOKEN': 'test_token',
            'GITHUB_OWNER': 'testorg',
            'GITHUB_REPO': 'testrepo'
        }):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = Mock()
                mock_response.json.return_value = {"html_url": "https://github.com/test/issue/123"}
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client

                url = await create_github_issue("Test Title", "Test Description")

                assert url == "https://github.com/test/issue/123"
                mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_github_issue_no_config(self):
        """Test GitHub issue creation without configuration"""
        with patch.dict('os.environ', {}, clear=True):
            url = await create_github_issue("Test Title", "Test Description")

            assert url is None

    @pytest.mark.asyncio
    async def test_create_jira_issue_success(self):
        """Test successful Jira issue creation"""
        with patch.dict('os.environ', {
            'JIRA_BASE_URL': 'https://company.atlassian.net',
            'JIRA_USERNAME': 'testuser',
            'JIRA_API_TOKEN': 'test_token',
            'JIRA_PROJECT_KEY': 'PROJ'
        }):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = Mock()
                mock_response.json.return_value = {"key": "PROJ-123"}
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client

                url = await create_jira_issue("Test Title", "Test Description")

                assert url == "https://company.atlassian.net/browse/PROJ-123"
                mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_servicenow_issue_success(self):
        """Test successful ServiceNow incident creation"""
        with patch.dict('os.environ', {
            'SERVICENOW_INSTANCE_URL': 'https://company.servicenow.com',
            'SERVICENOW_ACCESS_TOKEN': 'test_token'
        }):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = Mock()
                mock_response.json.return_value = {
                    "result": {
                        "sys_id": "sys123",
                        "number": "INC001234"
                    }
                }
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client

                url = await create_servicenow_issue("Test Title", "Test Description")

                assert url == "https://company.servicenow.com/nav_to.do?uri=incident.do?sys_id=sys123"
                mock_client.post.assert_called_once()


class TestAlertProcessing:
    """Test alert processing functions"""

    @pytest.mark.asyncio
    async def test_process_individual_alert_github(self):
        """Test processing individual alert with GitHub"""
        alert = {
            "labels": {
                "alertname": "TestAlert",
                "severity": "critical"
            },
            "annotations": {
                "summary": "Test Summary",
                "description": "Test Description"
            }
        }

        alert_group = Mock()
        alert_group.externalURL = "http://prometheus:9090"

        with patch.dict('os.environ', {'GITHUB_ENABLED': 'true'}):
            with patch('swarmops_hook.create_github_issue', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = "https://github.com/test/issue/123"

                with patch('swarmops_hook.IncidentEvent') as mock_event:
                    with patch('swarmops_hook.redis_client') as mock_redis:
                        await process_individual_alert(alert, alert_group)

                        mock_create.assert_called_once()
                        mock_event.assert_called()
                        mock_redis.xadd.assert_called()

    @pytest.mark.asyncio
    async def test_handle_resolved_alerts(self):
        """Test handling resolved alerts"""
        alert_group = Mock()
        alert_group.alerts = [
            {
                "labels": {"alertname": "TestAlert"}
            }
        ]

        background_tasks = Mock()

        with patch('swarmops_hook.close_ticket_background', new_callable=AsyncMock) as mock_close:
            result = await handle_resolved_alerts(alert_group, background_tasks)

            assert result["status"] == "resolved_processed"
            assert result["alerts_count"] == 1
            mock_close.assert_called_once()


class TestStartupAndConfiguration:
    """Test startup and configuration functions"""

    def test_get_ticket_creator_exists(self):
        """Test getting existing ticket creator"""
        # Mock the global ticket_creators dict
        import swarmops_hook
        original_creators = swarmops_hook.ticket_creators
        swarmops_hook.ticket_creators = {"github": Mock()}

        try:
            creator = get_ticket_creator("github")
            assert creator is not None
        finally:
            swarmops_hook.ticket_creators = original_creators

    def test_get_ticket_creator_not_exists(self):
        """Test getting non-existent ticket creator"""
        import swarmops_hook
        original_creators = swarmops_hook.ticket_creators
        swarmops_hook.ticket_creators = {}

        try:
            creator = get_ticket_creator("nonexistent")
            assert creator is None
        finally:
            swarmops_hook.ticket_creators = original_creators


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_webhook_invalid_json(self):
        """Test webhook with invalid JSON"""
        from fastapi.testclient import TestClient
        client = TestClient(app)

        response = client.post("/webhook", data="invalid json")

        assert response.status_code == 422  # Validation error

    def test_github_webhook_invalid_event(self, client):
        """Test GitHub webhook with invalid event"""
        headers = {"X-GitHub-Event": "push"}  # Not an issue event
        payload = {"test": "data"}

        response = client.post("/gh-webhook", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    def test_jira_webhook_no_status_change(self, client):
        """Test Jira webhook without status change"""
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "PROJ-123"},
            "changelog": {
                "items": [
                    {
                        "field": "assignee",
                        "fromString": "user1",
                        "toString": "user2"
                    }
                ]
            }
        }

        response = client.post("/jira-webhook", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"