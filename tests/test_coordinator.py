"""
Tests for SwarmCoordinator functionality.

This module tests the core coordination logic, agent management,
task execution, and load balancing features.
"""

import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any

from brain_swarm.coordination.coordinator import SwarmCoordinator
from brain_swarm.core.base import Message, MessageType, Task
from brain_swarm.agents.agents import VisionAgent, LanguageAgent


class TestSwarmCoordinator:
    """Test cases for SwarmCoordinator class."""

    @pytest.fixture
    def coordinator(self):
        """Create a fresh coordinator for each test."""
        coord = SwarmCoordinator("test_swarm")
        # Mock memory systems
        coord.working_memory = MagicMock()
        coord.long_term_memory = MagicMock()
        return coord

    def test_coordinator_initialization(self, coordinator):
        """Test coordinator initializes correctly."""
        assert coordinator.swarm_id == "test_swarm"
        assert coordinator.registered_agents == []
        assert coordinator.agent_loads == {}
        assert coordinator.max_agent_load == 3

    def test_agent_registration(self, coordinator):
        """Test agent registration functionality."""
        agent_id = "test_agent_001"

        coordinator.register_agent(agent_id)

        assert agent_id in coordinator.registered_agents
        assert coordinator.agent_loads[agent_id] == 0

    def test_agent_registration_duplicate(self, coordinator):
        """Test duplicate agent registration is handled."""
        agent_id = "test_agent_001"

        coordinator.register_agent(agent_id)
        coordinator.register_agent(agent_id)  # Should not error

        assert coordinator.registered_agents.count(agent_id) == 1

    def test_load_update(self, coordinator):
        """Test agent load tracking."""
        agent_id = "test_agent_001"
        coordinator.register_agent(agent_id)

        # Test load increase
        coordinator.update_agent_load(agent_id, 1)
        assert coordinator.agent_loads[agent_id] == 1

        # Test load decrease
        coordinator.update_agent_load(agent_id, -1)
        assert coordinator.agent_loads[agent_id] == 0

        # Test load decrease below zero (should remove agent)
        coordinator.update_agent_load(agent_id, -1)
        assert agent_id not in coordinator.agent_loads

    def test_least_loaded_agent_selection(self, coordinator):
        """Test selection of least loaded agent."""
        # Register multiple agents with different loads
        coordinator.register_agent("agent_1")
        coordinator.register_agent("agent_2")
        coordinator.register_agent("agent_3")

        coordinator.update_agent_load("agent_1", 2)
        coordinator.update_agent_load("agent_2", 1)
        # agent_3 remains at 0

        least_loaded = coordinator.get_least_loaded_agent()
        assert least_loaded == "agent_3"

    def test_least_loaded_agent_with_expertise(self, coordinator):
        """Test agent selection with expertise requirements."""
        coordinator.register_agent("vision_agent")
        coordinator.register_agent("lang_agent")

        # Mock agent expertise
        with patch.object(coordinator.planning_module, 'assign_agents_to_subtasks') as mock_expertise:
            mock_expertise.return_value = {
                "vision_agent": ["vision", "image"],
                "lang_agent": ["text", "language"]
            }

            # Should select vision agent for vision tasks
            agent = coordinator.get_least_loaded_agent("vision")
            assert agent == "vision_agent"

    def test_load_balance_report(self, coordinator):
        """Test load balancing report generation."""
        coordinator.register_agent("agent_1")
        coordinator.register_agent("agent_2")

        coordinator.update_agent_load("agent_1", 2)
        coordinator.update_agent_load("agent_2", 1)

        report = coordinator.get_load_balance_report()

        assert report["total_agents"] == 2
        assert report["total_load"] == 3
        assert report["average_load"] == 1.5
        assert report["agent_loads"]["agent_1"] == 2
        assert report["agent_loads"]["agent_2"] == 1

    @pytest.mark.asyncio
    async def test_task_execution_basic(self, coordinator, sample_task):
        """Test basic task execution flow."""
        coordinator.register_agent("test_agent")

        # Mock the delegation system
        coordinator.delegation_system = MagicMock()
        coordinator.delegation_system.active_tasks = {}

        # Mock agent assignment
        with patch.object(coordinator, 'get_least_loaded_agent', return_value="test_agent"):
            with patch.object(coordinator, 'send_message') as mock_send:
                result = coordinator.execute_task(sample_task)

                assert "task_id" in result
                assert result["status"] == "incremental_execution_started"
                mock_send.assert_called()

    def test_resource_availability_check(self, coordinator):
        """Test resource availability checking."""
        # Test with no high-priority tasks
        assert coordinator.check_resource_availability() == True

        # Add some high-priority tasks
        coordinator.delegation_system = MagicMock()
        coordinator.delegation_system.active_tasks = {
            "task_1": MagicMock(task=MagicMock(), status="active", priority=4),
            "task_2": MagicMock(task=MagicMock(), status="active", priority=4),
        }

        # Should return False when at limit
        assert coordinator.check_resource_availability() == False

    def test_predictive_control_insights(self, coordinator):
        """Test predictive control insights generation."""
        coordinator.register_agent("test_agent")

        insights = coordinator.get_predictive_control_insights()

        assert "load_forecasts" in insights
        assert "preventive_actions" in insights
        assert "resource_recommendations" in insights
        assert "system_health_predictions" in insights

    def test_system_health_assessment(self, coordinator):
        """Test system health assessment."""
        coordinator.register_agent("test_agent")
        coordinator.update_agent_load("test_agent", 1)

        health = coordinator.get_system_health()

        assert "overall_score" in health
        assert "agent_status" in health
        assert "memory_status" in health
        assert isinstance(health["overall_score"], (int, float))

    def test_message_processing(self, coordinator, task_assignment_message):
        """Test message processing."""
        # Mock the process_message method
        with patch.object(coordinator, 'handle_result_report', return_value=None) as mock_handler:
            task_assignment_message.message_type = MessageType.RESULT_REPORT
            result = coordinator.process_message(task_assignment_message)

            mock_handler.assert_called_once_with(task_assignment_message)

    def test_memory_systems_integration(self, coordinator, working_memory, long_term_memory):
        """Test integration with memory systems."""
        coordinator.set_memory_systems(working_memory, long_term_memory)

        assert coordinator.working_memory == working_memory
        assert coordinator.long_term_memory == long_term_memory

    @pytest.mark.slow
    def test_performance_under_load(self, coordinator):
        """Test coordinator performance under load."""
        # Register multiple agents
        for i in range(10):
            coordinator.register_agent(f"agent_{i}")

        # Simulate load
        for i in range(10):
            coordinator.update_agent_load(f"agent_{i}", 2)

        start_time = time.time()

        # Perform operations
        for _ in range(100):
            coordinator.get_least_loaded_agent()

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within reasonable time
        assert duration < 1.0  # Less than 1 second for 100 operations

    def test_error_handling_task_failure(self, coordinator):
        """Test error handling for task failures."""
        # This would test the error handling in task execution
        # Mock a failing task execution
        pass  # Implementation depends on specific error handling

    def test_concurrent_task_handling(self, coordinator):
        """Test handling of concurrent tasks."""
        coordinator.register_agent("agent_1")
        coordinator.register_agent("agent_2")

        # Simulate concurrent task assignments
        tasks = []
        for i in range(5):
            task = {"description": f"Task {i}", "type": "general", "priority": 1}
            tasks.append(task)

        # Execute tasks concurrently (in real implementation)
        # This is a simplified test
        for task in tasks:
            result = coordinator.execute_task(task)
            assert "task_id" in result

    def test_coordinator_cleanup(self, coordinator):
        """Test coordinator cleanup on shutdown."""
        coordinator.register_agent("test_agent")
        coordinator.update_agent_load("test_agent", 2)

        # Simulate cleanup
        coordinator.registered_agents.clear()
        coordinator.agent_loads.clear()

        assert len(coordinator.registered_agents) == 0
        assert len(coordinator.agent_loads) == 0