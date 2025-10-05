"""
Tests for REST API endpoints.

This module tests the FastAPI endpoints for task management,
agent monitoring, metrics collection, and federation.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from brain_swarm.api.main import create_app
from brain_swarm.coordination.coordinator import SwarmCoordinator


class TestHealthEndpoints:
    """Test health check and system status endpoints."""

    def test_health_check(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_system_status(self, test_client):
        """Test system status endpoint."""
        response = test_client.get("/status")

        assert response.status_code == 200
        data = response.get_json()
        assert "version" in data
        assert "uptime" in data
        assert "agents" in data


class TestAgentEndpoints:
    """Test agent management endpoints."""

    def test_list_agents(self, test_client):
        """Test listing registered agents."""
        response = test_client.get("/agents")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_register_agent(self, test_client):
        """Test agent registration endpoint."""
        agent_data = {
            "agent_id": "test_agent_001",
            "agent_type": "VisionAgent",
            "capabilities": ["vision", "analysis"]
        }

        response = test_client.post("/agents/register", json=agent_data)

        assert response.status_code == 201
        data = response.get_json()
        assert "agent_id" in data
        assert data["agent_id"] == "test_agent_001"

    def test_agent_status(self, test_client):
        """Test individual agent status."""
        # First register an agent
        test_client.post("/agents/register", json={
            "agent_id": "test_agent_001",
            "agent_type": "VisionAgent"
        })

        response = test_client.get("/agents/test_agent_001")

        assert response.status_code == 200
        data = response.get_json()
        assert "agent_id" in data
        assert "status" in data

    def test_agent_not_found(self, test_client):
        """Test requesting non-existent agent."""
        response = test_client.get("/agents/non_existent_agent")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data


class TestTaskEndpoints:
    """Test task management endpoints."""

    def test_submit_task(self, test_client):
        """Test task submission."""
        task_data = {
            "description": "Analyze this image for objects",
            "type": "vision_analysis",
            "priority": 2,
            "metadata": {"format": "jpg"}
        }

        response = test_client.post("/tasks", json=task_data)

        assert response.status_code == 202  # Accepted
        data = response.get_json()
        assert "task_id" in data
        assert "status" in data
        assert data["status"] == "accepted"

    def test_get_task_status(self, test_client):
        """Test getting task status."""
        # Submit a task first
        task_response = test_client.post("/tasks", json={
            "description": "Test task",
            "type": "general"
        })
        task_data = task_response.get_json()
        task_id = task_data["task_id"]

        # Get task status
        response = test_client.get(f"/tasks/{task_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "task_id" in data
        assert "status" in data

    def test_list_tasks(self, test_client):
        """Test listing all tasks."""
        # Submit a few tasks
        for i in range(3):
            test_client.post("/tasks", json={
                "description": f"Task {i}",
                "type": "general"
            })

        response = test_client.get("/tasks")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_cancel_task(self, test_client):
        """Test task cancellation."""
        # Submit a task
        task_response = test_client.post("/tasks", json={
            "description": "Task to cancel",
            "type": "general"
        })
        task_data = task_response.get_json()
        task_id = task_data["task_id"]

        # Cancel the task
        response = test_client.delete(f"/tasks/{task_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data
        assert "cancelled" in data["status"].lower()

    def test_task_not_found(self, test_client):
        """Test requesting non-existent task."""
        response = test_client.get("/tasks/non_existent_task")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data


class TestMetricsEndpoints:
    """Test metrics and analytics endpoints."""

    def test_system_metrics(self, test_client):
        """Test system metrics endpoint."""
        response = test_client.get("/metrics")

        assert response.status_code == 200
        data = response.get_json()
        assert "system_load" in data
        assert "active_tasks" in data
        assert "total_agents" in data

    def test_performance_metrics(self, test_client):
        """Test performance metrics endpoint."""
        response = test_client.get("/metrics/performance")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)

    def test_agent_metrics(self, test_client):
        """Test agent-specific metrics."""
        # Register an agent first
        test_client.post("/agents/register", json={
            "agent_id": "test_agent_001",
            "agent_type": "VisionAgent"
        })

        response = test_client.get("/metrics/agents/test_agent_001")

        assert response.status_code == 200
        data = response.get_json()
        assert "agent_id" in data
        assert "performance" in data


class TestDashboardEndpoints:
    """Test dashboard data endpoints."""

    def test_dashboard_overview(self, test_client):
        """Test dashboard overview data."""
        response = test_client.get("/dashboard/overview")

        assert response.status_code == 200
        data = response.get_json()
        assert "system_health" in data
        assert "active_tasks" in data
        assert "recent_activity" in data

    def test_dashboard_performance(self, test_client):
        """Test performance dashboard data."""
        response = test_client.get("/dashboard/performance")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)

    def test_dashboard_learning(self, test_client):
        """Test learning insights dashboard."""
        response = test_client.get("/dashboard/learning")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)

    def test_dashboard_operational(self, test_client):
        """Test operational dashboard data."""
        response = test_client.get("/dashboard/operational")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)


class TestFederationEndpoints:
    """Test federation-related endpoints."""

    def test_federation_status(self, test_client):
        """Test federation status endpoint."""
        response = test_client.get("/federation/status")

        assert response.status_code == 200
        data = response.get_json()
        assert "federation_enabled" in data
        assert "connected_nodes" in data

    def test_list_federation_nodes(self, test_client):
        """Test listing federation nodes."""
        response = test_client.get("/federation/nodes")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_join_federation(self, test_client):
        """Test joining a federation."""
        join_data = {
            "node_url": "http://remote-node:8000",
            "node_name": "remote_node_001"
        }

        response = test_client.post("/federation/join", json=join_data)

        # This might return different status codes based on implementation
        assert response.status_code in [200, 202, 400]  # Success or validation error


class TestWebSocketEndpoints:
    """Test WebSocket communication endpoints."""

    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test WebSocket connection establishment."""
        # This would require a test WebSocket client
        # Implementation depends on WebSocket test utilities
        pass

    @pytest.mark.asyncio
    async def test_realtime_updates(self):
        """Test real-time data streaming via WebSocket."""
        # Test that agents send updates through WebSocket
        pass


class TestErrorHandling:
    """Test error handling in API endpoints."""

    def test_invalid_json(self, test_client):
        """Test handling of invalid JSON."""
        response = test_client.post("/tasks",
                                  data="invalid json",
                                  headers={"Content-Type": "application/json"})

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_missing_required_fields(self, test_client):
        """Test validation of required fields."""
        # Missing description
        response = test_client.post("/tasks", json={
            "type": "general"
        })

        assert response.status_code == 422  # Validation error
        data = response.get_json()
        assert "detail" in data

    def test_unauthorized_access(self, test_client):
        """Test unauthorized access handling."""
        # This would test JWT authentication
        # Implementation depends on auth setup
        pass

    def test_rate_limiting(self, test_client):
        """Test rate limiting on endpoints."""
        # Send multiple requests quickly
        for _ in range(10):
            response = test_client.get("/health")

        # Should still work or return rate limit error
        # Implementation depends on rate limiting setup
        pass


class TestIntegrationScenarios:
    """Test complete integration scenarios."""

    def test_complete_task_workflow(self, test_client):
        """Test complete task submission to completion workflow."""
        # 1. Register an agent
        test_client.post("/agents/register", json={
            "agent_id": "integration_test_agent",
            "agent_type": "LanguageAgent"
        })

        # 2. Submit a task
        task_response = test_client.post("/tasks", json={
            "description": "Summarize this text",
            "type": "text_summarization",
            "priority": 1
        })
        assert task_response.status_code == 202
        task_data = task_response.get_json()
        task_id = task_data["task_id"]

        # 3. Check task status
        status_response = test_client.get(f"/tasks/{task_id}")
        assert status_response.status_code == 200

        # 4. Wait for completion (in real scenario)
        # This would check status until completed

        # 5. Verify completion
        # final_status = test_client.get(f"/tasks/{task_id}")
        # assert final_status.get_json()["status"] == "completed"

    def test_concurrent_task_handling(self, test_client):
        """Test handling multiple concurrent tasks."""
        # Submit multiple tasks
        task_ids = []
        for i in range(5):
            response = test_client.post("/tasks", json={
                "description": f"Concurrent task {i}",
                "type": "general",
                "priority": 1
            })
            task_ids.append(response.get_json()["task_id"])

        # Check all tasks are accepted
        for task_id in task_ids:
            response = test_client.get(f"/tasks/{task_id}")
            assert response.status_code == 200

    def test_system_under_load(self, test_client):
        """Test system behavior under load."""
        # Submit many tasks quickly
        for i in range(20):
            test_client.post("/tasks", json={
                "description": f"Load test task {i}",
                "type": "general"
            })

        # Check system metrics still work
        metrics_response = test_client.get("/metrics")
        assert metrics_response.status_code == 200

        # Check system health
        health_response = test_client.get("/health")
        assert health_response.status_code == 200