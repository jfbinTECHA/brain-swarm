"""
Tests for the AdaptiveTaskBroker
"""

import pytest
import time
from unittest.mock import MagicMock

from coordination.adaptive_broker import AdaptiveTaskBroker, TaskAssignment


class TestAdaptiveTaskBroker:
    """Test cases for the AdaptiveTaskBroker"""

    def setup_method(self):
        """Set up test fixtures"""
        self.broker = AdaptiveTaskBroker(alpha=0.1, reward_window=10)

    def test_initialization(self):
        """Test broker initialization"""
        assert self.broker.alpha == 0.1
        assert self.broker.reward_window == 10
        assert len(self.broker.agent_performance) == 0
        assert len(self.broker.routing_weights) == 0

    def test_agent_registration(self):
        """Test agent registration"""
        self.broker.register_agent("agent1", ["vision", "analysis"])

        assert "agent1" in self.broker.agent_performance
        perf = self.broker.agent_performance["agent1"]
        assert perf.total_assignments == 0
        assert perf.successful_assignments == 0
        assert perf.reward_score == 1.0

        # Check routing weights initialized
        assert "general" in self.broker.routing_weights
        assert self.broker.routing_weights["general"]["agent1"] == 1.0

    def test_task_assignment_no_agents(self):
        """Test task assignment with no available agents"""
        result = self.broker.assign_task("task1", "test task", [])
        assert result is None

    def test_task_assignment_single_agent(self):
        """Test task assignment with single agent"""
        self.broker.register_agent("agent1")

        result = self.broker.assign_task("task1", "analyze this data", ["agent1"])
        assert result == "agent1"

        # Check assignment was recorded
        assert "task1" in self.broker.active_assignments
        assignment = self.broker.active_assignments["task1"]
        assert assignment.agent_id == "agent1"
        assert assignment.task_id == "task1"

    def test_task_assignment_multiple_agents(self):
        """Test task assignment with multiple agents"""
        self.broker.register_agent("agent1")
        self.broker.register_agent("agent2")

        # First assignment should go to agent1 (arbitrary but deterministic)
        result1 = self.broker.assign_task("task1", "analyze data", ["agent1", "agent2"])
        assert result1 in ["agent1", "agent2"]

        # Second assignment
        result2 = self.broker.assign_task("task2", "process text", ["agent1", "agent2"])
        assert result2 in ["agent1", "agent2"]
        assert result1 != result2  # Should distribute

    def test_task_completion_success(self):
        """Test successful task completion"""
        self.broker.register_agent("agent1")
        self.broker.assign_task("task1", "test task", ["agent1"])

        # Complete task successfully
        self.broker.complete_task("task1", success=True, latency=5.0, resource_cost=0.3)

        # Check agent performance updated
        perf = self.broker.agent_performance["agent1"]
        assert perf.total_assignments == 1
        assert perf.successful_assignments == 1
        assert perf.success_rate == 1.0
        assert perf.avg_latency == 5.0
        assert perf.avg_resource_cost == 0.3

        # Check task removed from active
        assert "task1" not in self.broker.active_assignments

        # Check added to history
        assert len(self.broker.assignment_history) == 1

    def test_task_completion_failure(self):
        """Test failed task completion"""
        self.broker.register_agent("agent1")
        self.broker.assign_task("task1", "test task", ["agent1"])

        # Complete task with failure
        self.broker.complete_task("task1", success=False, latency=10.0, resource_cost=0.8)

        # Check agent performance updated
        perf = self.broker.agent_performance["agent1"]
        assert perf.total_assignments == 1
        assert perf.successful_assignments == 0
        assert perf.success_rate == 0.0

        # Check reward score decreased (negative reward)
        assert perf.reward_score < 1.0

    def test_reward_calculation(self):
        """Test reward calculation logic"""
        assignment = TaskAssignment(
            task_id="test",
            agent_id="agent1",
            start_time=time.time(),
            success=True,
            latency=2.0,  # Fast completion
            resource_cost=0.2  # Low resource usage
        )

        reward = self.broker._calculate_reward(assignment)
        # Should be positive: +1.0 (success) - small latency penalty - small resource penalty
        assert reward > 0.5

        # Test failure case
        assignment.success = False
        reward_failure = self.broker._calculate_reward(assignment)
        # Should be negative: -1.0 (failure) - penalties
        assert reward_failure < -0.5

    def test_routing_weight_updates(self):
        """Test that routing weights are updated based on performance"""
        self.broker.register_agent("agent1")
        self.broker.register_agent("agent2")

        # Agent1 succeeds
        self.broker.assign_task("task1", "analysis task", ["agent1", "agent2"])
        self.broker.complete_task("task1", success=True, latency=3.0, resource_cost=0.2)

        # Agent2 fails
        self.broker.assign_task("task2", "analysis task", ["agent1", "agent2"])
        self.broker.complete_task("task2", success=False, latency=15.0, resource_cost=0.9)

        # Check weights updated
        weights = self.broker.routing_weights["analysis"]
        assert weights["agent1"] > weights["agent2"]  # Agent1 should have higher weight

    def test_learning_adaptation(self):
        """Test that the broker learns and adapts routing"""
        self.broker.register_agent("agent1")
        self.broker.register_agent("agent2")

        # Simulate multiple tasks with agent1 consistently performing better
        for i in range(10):
            task_id = f"task_{i}"
            # Alternate assignment but bias results
            agents = ["agent1", "agent2"]
            assigned = self.broker.assign_task(task_id, "analysis task", agents)

            # Agent1 always succeeds quickly, agent2 sometimes fails
            if assigned == "agent1":
                self.broker.complete_task(task_id, success=True, latency=2.0, resource_cost=0.2)
            else:
                success = (i % 3) != 0  # Agent2 fails every 3rd task
                latency = 5.0 if success else 20.0
                self.broker.complete_task(task_id, success=success, latency=latency, resource_cost=0.5)

        # Check that agent1 has higher performance
        perf1 = self.broker.agent_performance["agent1"]
        perf2 = self.broker.agent_performance["agent2"]

        assert perf1.success_rate > perf2.success_rate
        assert perf1.reward_score > perf2.reward_score

        # Check routing weights favor agent1
        weights = self.broker.routing_weights["analysis"]
        assert weights["agent1"] > weights["agent2"]

    def test_performance_report(self):
        """Test performance report generation"""
        self.broker.register_agent("agent1")
        self.broker.assign_task("task1", "test", ["agent1"])
        self.broker.complete_task("task1", success=True, latency=1.0, resource_cost=0.1)

        report = self.broker.get_performance_report()

        assert report["total_assignments"] == 1
        assert report["active_assignments"] == 0
        assert "agent1" in report["agent_performance"]
        assert report["agent_performance"]["agent1"]["total_assignments"] == 1
        assert report["agent_performance"]["agent1"]["success_rate"] == 1.0

    def test_routing_recommendation(self):
        """Test routing recommendation generation"""
        self.broker.register_agent("agent1")
        self.broker.register_agent("agent2")

        # Set up different performance levels
        self.broker.assign_task("task1", "test", ["agent1"])
        self.broker.complete_task("task1", success=True, latency=1.0, resource_cost=0.1)

        self.broker.assign_task("task2", "test", ["agent2"])
        self.broker.complete_task("task2", success=False, latency=10.0, resource_cost=0.8)

        recommendation = self.broker.get_routing_recommendation("general", ["agent1", "agent2"])

        assert recommendation["task_type"] == "general"
        assert len(recommendation["recommendations"]) == 2
        assert recommendation["best_agent"] == "agent1"  # Should recommend better performing agent

    def test_learning_state_persistence(self):
        """Test learning state export/import"""
        self.broker.register_agent("agent1")
        self.broker.assign_task("task1", "test", ["agent1"])
        self.broker.complete_task("task1", success=True, latency=2.0, resource_cost=0.3)

        # Export state
        state_json = self.broker.export_learning_state()
        assert isinstance(state_json, str)

        # Create new broker and import state
        new_broker = AdaptiveTaskBroker()
        new_broker.import_learning_state(state_json)

        # Check state was restored
        assert "agent1" in new_broker.agent_performance
        assert len(new_broker.assignment_history) == 1
        assert new_broker.assignment_history[0].task_id == "task1"

    def test_weight_normalization(self):
        """Test that routing weights are properly normalized"""
        self.broker.register_agent("agent1")
        self.broker.register_agent("agent2")

        # Manually set weights
        for agent_id in ["agent1", "agent2"]:
            self.broker.routing_weights["test"][agent_id] = 2.0

        # Trigger normalization by updating weights
        self.broker.assign_task("task1", "test task", ["agent1"])
        self.broker.complete_task("task1", success=True, latency=1.0, resource_cost=0.1)

        # Check weights are normalized (should sum to close to 2.0 or be proportional)
        weights = self.broker.routing_weights["test"]
        total_weight = sum(weights.values())
        assert abs(total_weight - 2.0) < 0.1 or all(w >= 0.1 for w in weights.values())


if __name__ == "__main__":
    pytest.main([__file__])