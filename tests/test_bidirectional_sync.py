"""
Tests for SwarmOps Bi-Directional Ticket Synchronization Service.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from swarmops_bidirectional_sync import (
    BiDirectionalSyncManager,
    SyncDirection,
    SyncStatus,
    SyncRecord,
    TicketSystem
)


class TestSyncRecord:
    """Test SyncRecord data structure"""

    def test_sync_record_creation(self):
        """Test creating a sync record"""
        record = SyncRecord(
            sync_id="test_sync_123",
            incident_id="incident_456",
            ticket_system="github",
            ticket_id="789",
            direction=SyncDirection.INCIDENT_TO_TICKET,
            status=SyncStatus.PENDING,
            created_at=1234567890.0,
            updated_at=1234567891.0
        )

        assert record.sync_id == "test_sync_123"
        assert record.incident_id == "incident_456"
        assert record.ticket_system == "github"
        assert record.ticket_id == "789"
        assert record.direction == SyncDirection.INCIDENT_TO_TICKET
        assert record.status == SyncStatus.PENDING

    def test_sync_record_to_dict(self):
        """Test converting sync record to dictionary"""
        record = SyncRecord(
            sync_id="test_sync_123",
            incident_id="incident_456",
            ticket_system="github",
            ticket_id="789",
            direction=SyncDirection.INCIDENT_TO_TICKET,
            status=SyncStatus.COMPLETED,
            created_at=1234567890.0,
            updated_at=1234567891.0,
            retry_count=2,
            error_message="Test error"
        )

        data = record.to_dict()

        assert data["sync_id"] == "test_sync_123"
        assert data["incident_id"] == "incident_456"
        assert data["direction"] == "incident_to_ticket"
        assert data["status"] == "completed"
        assert data["retry_count"] == 2
        assert data["error_message"] == "Test error"


class TestBiDirectionalSyncManager:
    """Test BiDirectionalSyncManager functionality"""

    @pytest.fixture
    def sync_manager(self):
        """Create a sync manager instance for testing"""
        manager = BiDirectionalSyncManager()

        # Mock Redis client
        manager.redis = Mock()

        # Set up minimal config for testing
        manager.ticket_configs = {
            "github": {
                "token": "test_token",
                "owner": "testorg",
                "repo": "testrepo"
            }
        }

        return manager

    def test_initialization(self, sync_manager):
        """Test sync manager initialization"""
        assert sync_manager.max_retries == 3
        assert sync_manager.retry_delay == 60
        assert sync_manager.poll_interval == 300
        assert sync_manager.conflict_resolution == "ticket_wins"
        assert isinstance(sync_manager.ticket_configs, dict)

    @pytest.mark.asyncio
    async def test_sync_incident_to_ticket_success(self, sync_manager):
        """Test successful incident to ticket synchronization"""
        incident_data = {
            "id": "incident_123",
            "title": "Test Incident",
            "severity": "high",
            "description": "Test description"
        }

        # Mock the GitHub API call
        with patch.object(sync_manager, '_create_github_issue', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = "123"

            ticket_id = await sync_manager.sync_incident_to_ticket(
                "incident_123", "github", incident_data
            )

            assert ticket_id == "123"
            mock_create.assert_called_once_with(incident_data)

    @pytest.mark.asyncio
    async def test_sync_incident_to_ticket_failure_with_retry(self, sync_manager):
        """Test incident to ticket sync with failure and retry"""
        incident_data = {
            "id": "incident_123",
            "title": "Test Incident",
            "severity": "high"
        }

        # Mock the GitHub API call to fail
        with patch.object(sync_manager, '_create_github_issue', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")

            with pytest.raises(Exception):
                await sync_manager.sync_incident_to_ticket(
                    "incident_123", "github", incident_data
                )

            # Should have been called once (initial attempt)
            assert mock_create.call_count == 1

    @pytest.mark.asyncio
    async def test_sync_ticket_to_incident_success(self, sync_manager):
        """Test successful ticket to incident synchronization"""
        ticket_data = {
            "id": "123",
            "title": "Test Ticket",
            "status": "open"
        }

        # Mock the incident creation
        with patch.object(sync_manager, '_create_incident_from_ticket', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = "incident_456"

            incident_id = await sync_manager.sync_ticket_to_incident(
                "github", "123", ticket_data
            )

            assert incident_id == "incident_456"
            mock_create.assert_called_once_with(ticket_data)

    def test_store_sync_record(self, sync_manager):
        """Test storing sync record in Redis"""
        record = SyncRecord(
            sync_id="test_sync_123",
            incident_id="incident_456",
            ticket_system="github",
            ticket_id="789",
            direction=SyncDirection.INCIDENT_TO_TICKET,
            status=SyncStatus.PENDING,
            created_at=1234567890.0,
            updated_at=1234567890.0
        )

        sync_manager._store_sync_record(record)

        # Verify Redis calls
        assert sync_manager.redis.hset.called
        assert sync_manager.redis.set.called

    def test_find_sync_by_ticket(self, sync_manager):
        """Test finding sync record by ticket information"""
        # Mock Redis responses
        sync_manager.redis.get.return_value = "test_sync_123"
        sync_manager.redis.hgetall.return_value = {
            "sync_id": "test_sync_123",
            "incident_id": "incident_456",
            "ticket_system": "github",
            "ticket_id": "789",
            "direction": "incident_to_ticket",
            "status": "completed",
            "created_at": "1234567890.0",
            "updated_at": "1234567891.0",
            "retry_count": "0"
        }

        record = sync_manager._find_sync_by_ticket("github", "789")

        assert record is not None
        assert record.sync_id == "test_sync_123"
        assert record.incident_id == "incident_456"

    def test_find_sync_by_ticket_not_found(self, sync_manager):
        """Test finding sync record when not found"""
        sync_manager.redis.get.return_value = None

        record = sync_manager._find_sync_by_ticket("github", "999")

        assert record is None

    @pytest.mark.asyncio
    async def test_handle_webhook_update_github(self, sync_manager):
        """Test handling GitHub webhook updates"""
        webhook_data = {
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "state": "closed",
                "updated_at": "2023-10-05T12:00:00Z"
            }
        }

        # Mock finding existing sync record
        mock_record = SyncRecord(
            sync_id="test_sync_123",
            incident_id="incident_456",
            ticket_system="github",
            ticket_id="123",
            direction=SyncDirection.TICKET_TO_INCIDENT,
            status=SyncStatus.COMPLETED,
            created_at=1234567890.0,
            updated_at=1234567890.0
        )

        with patch.object(sync_manager, '_find_sync_by_ticket') as mock_find:
            mock_find.return_value = mock_record

            with patch.object(sync_manager, '_handle_ticket_status_update', new_callable=AsyncMock) as mock_handle:
                await sync_manager.handle_webhook_update("github", webhook_data)

                mock_find.assert_called_once_with("github", "123")
                mock_handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_webhook_update_new_ticket(self, sync_manager):
        """Test handling webhook for new ticket (no existing sync)"""
        webhook_data = {
            "issue": {
                "number": 456,
                "title": "New Issue",
                "state": "open"
            }
        }

        # Mock no existing sync record
        with patch.object(sync_manager, '_find_sync_by_ticket') as mock_find:
            mock_find.return_value = None

            with patch.object(sync_manager, 'sync_ticket_to_incident', new_callable=AsyncMock) as mock_sync:
                mock_sync.return_value = "incident_789"

                await sync_manager.handle_webhook_update("github", webhook_data)

                mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_ticket_updates(self, sync_manager):
        """Test polling ticket systems for updates"""
        # Mock the polling methods
        with patch.object(sync_manager, '_poll_github_updates', new_callable=AsyncMock) as mock_github:
            with patch.object(sync_manager, '_poll_jira_updates', new_callable=AsyncMock) as mock_jira:
                with patch.object(sync_manager, '_poll_servicenow_updates', new_callable=AsyncMock) as mock_snow:

                    await sync_manager.poll_ticket_updates()

                    mock_github.assert_called_once()
                    # Jira and ServiceNow not called since not in ticket_configs

    def test_get_sync_status(self, sync_manager):
        """Test getting synchronization status"""
        # Mock Redis keys and data
        sync_manager.redis.keys.return_value = ["sync_record:incident_123:github"]
        sync_manager.redis.hgetall.return_value = {
            "sync_id": "sync_123",
            "incident_id": "incident_123",
            "ticket_system": "github",
            "ticket_id": "456",
            "direction": "incident_to_ticket",
            "status": "completed",
            "created_at": "1234567890.0",
            "updated_at": "1234567891.0",
            "retry_count": "0"
        }

        records = sync_manager.get_sync_status()

        assert len(records) == 1
        assert records[0]["sync_id"] == "sync_123"
        assert records[0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_resolve_conflicts(self, sync_manager):
        """Test conflict resolution"""
        conflicts = [
            {
                "sync_id": "conflict_123",
                "incident_id": "incident_456",
                "ticket_system": "github"
            }
        ]

        with patch.object(sync_manager, '_find_conflicting_syncs') as mock_find:
            mock_find.return_value = conflicts

            with patch.object(sync_manager, '_resolve_single_conflict', new_callable=AsyncMock) as mock_resolve:
                await sync_manager.resolve_conflicts()

                mock_resolve.assert_called_once_with(conflicts[0])

    def test_parse_webhook_data_github(self, sync_manager):
        """Test parsing GitHub webhook data"""
        webhook_data = {
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "state": "closed",
                "updated_at": "2023-10-05T12:00:00Z"
            }
        }

        result = sync_manager._parse_webhook_data("github", webhook_data)

        assert result is not None
        assert result["id"] == "123"
        assert result["title"] == "Test Issue"
        assert result["status"] == "closed"

    def test_parse_webhook_data_jira(self, sync_manager):
        """Test parsing Jira webhook data"""
        webhook_data = {
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "summary": "Test Issue",
                    "status": {"name": "In Progress"},
                    "updated": "2023-10-05T12:00:00.000+0000"
                }
            }
        }

        result = sync_manager._parse_webhook_data("jira", webhook_data)

        assert result is not None
        assert result["id"] == "PROJ-123"
        assert result["title"] == "Test Issue"
        assert result["status"] == "In Progress"

    def test_parse_webhook_data_servicenow(self, sync_manager):
        """Test parsing ServiceNow webhook data"""
        webhook_data = {
            "number": "INC001234",
            "short_description": "Test Incident",
            "state": "2",
            "sys_updated_on": "2023-10-05 12:00:00"
        }

        result = sync_manager._parse_webhook_data("servicenow", webhook_data)

        assert result is not None
        assert result["id"] == "INC001234"
        assert result["title"] == "Test Incident"
        assert result["status"] == "2"

    def test_format_incident_title(self, sync_manager):
        """Test formatting incident title"""
        incident = {
            "title": "Test Incident",
            "severity": "critical"
        }

        title = sync_manager._format_incident_title(incident)

        assert title == "[CRITICAL] Test Incident"

    def test_get_incident_labels_github(self, sync_manager):
        """Test getting incident labels for GitHub"""
        incident = {
            "severity": "high",
            "status": "active"
        }

        labels = sync_manager._get_incident_labels(incident, "github")

        assert "brain-swarm" in labels
        assert "incident" in labels
        assert "severity-high" in labels
        assert "status-active" in labels

    def test_map_severity_to_priority(self, sync_manager):
        """Test mapping severity to Jira priority"""
        assert sync_manager._map_severity_to_priority("critical") == "Highest"
        assert sync_manager._map_severity_to_priority("high") == "High"
        assert sync_manager._map_severity_to_priority("medium") == "Medium"
        assert sync_manager._map_severity_to_priority("unknown") == "Medium"

    def test_map_severity_to_urgency(self, sync_manager):
        """Test mapping severity to ServiceNow urgency"""
        assert sync_manager._map_severity_to_urgency("critical") == "1"
        assert sync_manager._map_severity_to_urgency("high") == "2"
        assert sync_manager._map_severity_to_urgency("medium") == "2"
        assert sync_manager._map_severity_to_urgency("unknown") == "2"


class TestGitHubIntegration:
    """Test GitHub-specific integration"""

    @pytest.fixture
    def sync_manager(self):
        manager = BiDirectionalSyncManager()
        manager.http_client = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_create_github_issue(self, sync_manager):
        """Test creating GitHub issue"""
        incident_data = {
            "id": "incident_123",
            "title": "Test Incident",
            "severity": "high",
            "description": "Test description"
        }

        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {"number": 456}
        sync_manager.http_client.post.return_value = mock_response

        ticket_id = await sync_manager._create_github_issue(incident_data)

        assert ticket_id == "456"

        # Verify API call
        call_args = sync_manager.http_client.post.call_args
        assert "repos/testorg/testrepo/issues" in call_args[0][0]
        payload = call_args[0][1]["json"]
        assert "[HIGH]" in payload["title"]
        assert "Test description" in payload["body"]

    @pytest.mark.asyncio
    async def test_poll_github_updates(self, sync_manager):
        """Test polling GitHub for updates"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "number": 123,
                "title": "Test Issue",
                "state": "closed",
                "updated_at": "2023-10-05T12:00:00Z"
            }
        ]
        sync_manager.http_client.get.return_value = mock_response

        with patch.object(sync_manager, 'handle_webhook_update', new_callable=AsyncMock) as mock_handle:
            await sync_manager._poll_github_updates()

            mock_handle.assert_called_once()


class TestJiraIntegration:
    """Test Jira-specific integration"""

    @pytest.fixture
    def sync_manager(self):
        manager = BiDirectionalSyncManager()
        manager.http_client = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_create_jira_issue(self, sync_manager):
        """Test creating Jira issue"""
        incident_data = {
            "id": "incident_123",
            "title": "Test Incident",
            "severity": "critical",
            "description": "Test description"
        }

        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {"key": "PROJ-456"}
        sync_manager.http_client.post.return_value = mock_response

        ticket_id = await sync_manager._create_jira_issue(incident_data)

        assert ticket_id == "PROJ-456"

        # Verify API call includes auth
        call_kwargs = sync_manager.http_client.post.call_args[1]
        assert "auth" in call_kwargs


class TestServiceNowIntegration:
    """Test ServiceNow-specific integration"""

    @pytest.fixture
    def sync_manager(self):
        manager = BiDirectionalSyncManager()
        manager.http_client = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_create_servicenow_incident(self, sync_manager):
        """Test creating ServiceNow incident"""
        incident_data = {
            "id": "incident_123",
            "title": "Test Incident",
            "severity": "high",
            "description": "Test description"
        }

        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "number": "INC001234",
                "sys_id": "sys123"
            }
        }
        sync_manager.http_client.post.return_value = mock_response

        ticket_id = await sync_manager._create_servicenow_incident(incident_data)

        assert ticket_id == "INC001234"

        # Verify API call includes authorization header
        call_kwargs = sync_manager.http_client.post.call_args[1]
        assert "Authorization" in call_kwargs["headers"]


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.fixture
    def sync_manager(self):
        manager = BiDirectionalSyncManager()
        manager.redis = Mock()
        return manager

    @pytest.mark.asyncio
    async def test_sync_with_invalid_ticket_system(self, sync_manager):
        """Test sync with invalid ticket system"""
        incident_data = {"id": "test"}

        with pytest.raises(ValueError, match="Unsupported ticket system"):
            await sync_manager.sync_incident_to_ticket(
                "incident_123", "invalid_system", incident_data
            )

    def test_parse_webhook_invalid_data(self, sync_manager):
        """Test parsing invalid webhook data"""
        result = sync_manager._parse_webhook_data("unknown", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_webhook_processing_error(self, sync_manager):
        """Test webhook processing with errors"""
        with patch.object(sync_manager, '_parse_webhook_data') as mock_parse:
            mock_parse.side_effect = Exception("Parse error")

            # Should not raise exception
            await sync_manager.handle_webhook_update("github", {"invalid": "data"})

    def test_sync_record_enum_values(self):
        """Test enum values in sync records"""
        record = SyncRecord(
            sync_id="test",
            incident_id="incident_123",
            ticket_system="github",
            ticket_id="456",
            direction=SyncDirection.TICKET_TO_INCIDENT,
            status=SyncStatus.CONFLICT,
            created_at=1234567890.0,
            updated_at=1234567890.0
        )

        data = record.to_dict()
        assert data["direction"] == "ticket_to_incident"
        assert data["status"] == "conflict"