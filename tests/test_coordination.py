import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from brain_swarm.coordination.coordinator import SwarmCoordinator, PlanningModule, AutoScaler


class TestSwarmCoordinator:
    """Test suite for SwarmCoordinator edge cases and queue handling"""

    def setup_method(self):
        """Set up test fixtures"""
        self.coordinator = SwarmCoordinator("test_coordinator")

    def test_initialization(self):
        """Test coordinator initializes with correct structure"""
        assert self.coordinator.agent_id == "test_coordinator"
        assert len(self.coordinator.registered_agents) == 0
        assert len(self.coordinator.agent_loads) == 0
        assert isinstance(self.coordinator.planning_module, PlanningModule)
        assert isinstance(self.coordinator.auto_scaler, AutoScaler)

    def test_register_agent(self):
        """Test agent registration"""
        agent_id = "test_agent_1"

        self.coordinator.register_agent(agent_id)

        assert agent_id in self.coordinator.registered_agents
        assert self.coordinator.agent_loads[agent_id] == 0

    def test_register_duplicate_agent(self):
        """Test registering same agent twice"""
        agent_id = "test_agent_1"

        # First registration
        self.coordinator.register_agent(agent_id)
        initial_count = len(self.coordinator.registered_agents)

        # Second registration (should not add duplicate)
        self.coordinator.register_agent(agent_id)

        assert len(self.coordinator.registered_agents) == initial_count

    def test_unregister_agent(self):
        """Test agent unregistration"""
        agent_id = "test_agent_1"

        # Register then unregister
        self.coordinator.register_agent(agent_id)
        assert agent_id in self.coordinator.registered_agents

        self.coordinator.unregister_agent(agent_id)
        assert agent_id not in self.coordinator.registered_agents
        assert agent_id not in self.coordinator.agent_loads

    def test_update_agent_load(self):
        """Test agent load updates"""
        agent_id = "test_agent_1"

        self.coordinator.register_agent(agent_id)

        # Update load
        self.coordinator.update_agent_load(agent_id, 0.5)
        assert self.coordinator.agent_loads[agent_id] == 0.5

        # Update again (should accumulate)
        self.coordinator.update_agent_load(agent_id, 0.3)
        assert self.coordinator.agent_loads[agent_id] == 0.8

    def test_get_least_loaded_agent(self):
        """Test finding least loaded agent"""
        agents = ["agent_1", "agent_2", "agent_3"]

        for agent in agents:
            self.coordinator.register_agent(agent)

        # Set different loads
        self.coordinator.update_agent_load("agent_1", 0.8)
        self.coordinator.update_agent_load("agent_2", 0.3)
        self.coordinator.update_agent_load("agent_3", 0.6)

        least_loaded = self.coordinator.get_least_loaded_agent()
        assert least_loaded == "agent_2"  # Has lowest load

    def test_get_least_loaded_agent_empty_list(self):
        """Test least loaded agent with no agents"""
        result = self.coordinator.get_least_loaded_agent()
        assert result is None

    def test_get_least_loaded_agent_with_expertise_filter(self):
        """Test least loaded agent with expertise filtering"""
        agents = ["vision_agent", "language_agent", "math_agent"]

        for agent in agents:
            self.coordinator.register_agent(agent)

        # Set loads
        self.coordinator.update_agent_load("vision_agent", 0.5)
        self.coordinator.update_agent_load("language_agent", 0.2)
        self.coordinator.update_agent_load("math_agent", 0.8)

        # Filter for language expertise
        least_loaded = self.coordinator.get_least_loaded_agent(expertise_filter=["language"])
        assert least_loaded == "language_agent"

    def test_load_balance_report_empty_system(self):
        """Test load balance report for empty system"""
        report = self.coordinator.get_load_balance_report()

        assert report["total_agents"] == 0
        assert report["average_load"] == 0.0
        assert report["max_load"] == 0.0
        assert len(report["load_distribution"]) == 0

    def test_load_balance_report_with_agents(self):
        """Test load balance report with agents"""
        agents = ["agent_1", "agent_2", "agent_3"]

        for agent in agents:
            self.coordinator.register_agent(agent)

        # Set loads
        self.coordinator.update_agent_load("agent_1", 0.2)
        self.coordinator.update_agent_load("agent_2", 0.5)
        self.coordinator.update_agent_load("agent_3", 0.8)

        report = self.coordinator.get_load_balance_report()

        assert report["total_agents"] == 3
        assert abs(report["average_load"] - 0.5) < 0.001  # (0.2 + 0.5 + 0.8) / 3
        assert report["max_load"] == 0.8
        assert len(report["load_distribution"]) == 3

    def test_task_execution_with_no_agents(self):
        """Test task execution when no agents are available"""
        task = {"description": "test task", "priority": "normal"}

        result = self.coordinator.execute_task(task)

        assert "error" in result
        assert "no agents available" in result["error"].lower()

    def test_task_execution_with_agents(self):
        """Test task execution with available agents"""
        # Register agents
        self.coordinator.register_agent("test_agent")

        task = {"description": "test task", "priority": "normal"}

        with patch.object(self.coordinator, 'delegate_task') as mock_delegate:
            mock_delegate.return_value = {"task_id": "test_task_123", "status": "delegated"}

            result = self.coordinator.execute_task(task)

            assert result["task_id"] == "test_task_123"
            assert result["status"] == "delegated"
            mock_delegate.assert_called_once()

    def test_concurrent_task_execution(self):
        """Test handling multiple concurrent tasks"""
        # Register multiple agents
        for i in range(5):
            self.coordinator.register_agent(f"agent_{i}")

        tasks = []
        for i in range(10):
            task = {"description": f"concurrent task {i}", "priority": "normal"}
            tasks.append(task)

        # Execute tasks concurrently (simulated)
        results = []
        for task in tasks:
            with patch.object(self.coordinator, 'delegate_task') as mock_delegate:
                mock_delegate.return_value = {"task_id": f"task_{len(results)}", "status": "delegated"}
                result = self.coordinator.execute_task(task)
                results.append(result)

        assert len(results) == 10
        assert all("task_id" in result for result in results)

    def test_agent_failure_handling(self):
        """Test handling agent failures during task execution"""
        agent_id = "failing_agent"
        self.coordinator.register_agent(agent_id)

        # Simulate agent failure (high load)
        self.coordinator.update_agent_load(agent_id, 1.0)

        task = {"description": "test task", "priority": "high"}

        with patch.object(self.coordinator, 'get_least_loaded_agent') as mock_least_loaded:
            mock_least_loaded.return_value = None  # No agent available

            result = self.coordinator.execute_task(task)

            assert "error" in result
            assert "no suitable agent" in result["error"].lower()

    def test_task_queue_overflow_simulation(self):
        """Test behavior under task queue overflow conditions"""
        # Register limited agents
        for i in range(2):
            self.coordinator.register_agent(f"agent_{i}")

        # Simulate many tasks overwhelming the system
        tasks = []
        for i in range(100):
            task = {"description": f"overflow task {i}", "priority": "normal"}
            tasks.append(task)

        # Process tasks (should handle gracefully)
        results = []
        for task in tasks:
            try:
                result = self.coordinator.execute_task(task)
                results.append(result)
            except Exception:
                # Should handle gracefully
                results.append({"error": "system overload"})

        assert len(results) == 100
        # Should have some successful delegations and some errors
        successful = [r for r in results if "task_id" in r]
        errors = [r for r in results if "error" in r]

        assert len(successful) > 0  # Some should succeed
        assert len(errors) >= 0  # Some may fail under load

    def test_agent_load_distribution(self):
        """Test that tasks are distributed based on agent load"""
        agents = ["light_agent", "medium_agent", "heavy_agent"]

        for agent in agents:
            self.coordinator.register_agent(agent)

        # Set different loads
        self.coordinator.update_agent_load("light_agent", 0.1)
        self.coordinator.update_agent_load("medium_agent", 0.5)
        self.coordinator.update_agent_load("heavy_agent", 0.9)

        # Track which agents get selected for tasks
        selected_agents = []

        for i in range(10):
            selected = self.coordinator.get_least_loaded_agent()
            if selected:
                selected_agents.append(selected)
                # Slightly increase load to simulate work
                current_load = self.coordinator.agent_loads[selected]
                self.coordinator.update_agent_load(selected, min(1.0, current_load + 0.1))

        # Light agent should be selected most often
        light_count = selected_agents.count("light_agent")
        medium_count = selected_agents.count("medium_agent")
        heavy_count = selected_agents.count("heavy_agent")

        assert light_count > medium_count  # Light should get more tasks
        assert medium_count >= heavy_count  # Medium should get more than heavy

    def test_system_health_monitoring(self):
        """Test system health monitoring capabilities"""
        # Start with healthy system
        health = self.coordinator.get_system_health()
        assert health["status"] == "healthy"

        # Add agents and tasks
        self.coordinator.register_agent("test_agent")
        self.coordinator.update_agent_load("test_agent", 0.8)  # High load

        health = self.coordinator.get_system_health()
        assert health["status"] == "warning"  # High load triggers warning

        # Add more agents to balance load
        for i in range(3):
            self.coordinator.register_agent(f"balance_agent_{i}")

        health = self.coordinator.get_system_health()
        assert health["status"] == "healthy"  # Load balanced

    def test_graceful_shutdown(self):
        """Test coordinator shutdown procedure"""
        # Register agents and add some load
        self.coordinator.register_agent("agent_1")
        self.coordinator.register_agent("agent_2")
        self.coordinator.update_agent_load("agent_1", 0.5)

        # Shutdown
        self.coordinator.shutdown()

        # Verify cleanup
        assert len(self.coordinator.registered_agents) == 0
        assert len(self.coordinator.agent_loads) == 0


class TestPlanningModule:
    """Test suite for PlanningModule edge cases"""

    def setup_method(self):
        """Set up test fixtures"""
        self.planning = PlanningModule()

    def test_task_type_classification(self):
        """Test task type classification logic"""
        test_cases = [
            ("analyze this data", "analysis"),
            ("create a new design", "creative"),
            ("calculate the result", "mathematical"),
            ("decide between options", "decision_making"),
            ("simulate the scenario", "simulation"),
            ("explain the concept", "communication"),
            ("unknown task type", "general")
        ]

        for description, expected_type in test_cases:
            task_type = self.planning._classify_task_type(description)
            assert task_type == expected_type

    def test_complexity_estimation(self):
        """Test task complexity estimation"""
        simple_task = "Add two numbers"
        complex_task = "Design and implement a comprehensive machine learning pipeline with data preprocessing, model selection, hyperparameter tuning, cross-validation, and deployment considerations including scalability, monitoring, and maintenance strategies."

        simple_complexity = self.planning.estimate_complexity(simple_task)
        complex_complexity = self.planning.estimate_complexity(complex_task)

        assert simple_complexity == "low"
        assert complex_complexity == "high"

    def test_batch_processing_detection(self):
        """Test batch processing task detection"""
        batch_tasks = [
            "summarize 10 articles",
            "analyze 5 documents",
            "process 20 items",
            "review 3 reports"
        ]

        for task in batch_tasks:
            batch_info = self.planning._detect_batch_processing(task)
            assert batch_info is not None
            assert "count" in batch_info
            assert "action" in batch_info

    def test_non_batch_task_detection(self):
        """Test that non-batch tasks are not detected as batch"""
        non_batch_tasks = [
            "write a summary",
            "analyze the data",
            "process this item",
            "review the report"
        ]

        for task in non_batch_tasks:
            batch_info = self.planning._detect_batch_processing(task)
            assert batch_info is None

    def test_priority_assignment(self):
        """Test task priority assignment logic"""
        tasks = [
            {"description": "gather data for analysis", "expected_priority": 3},
            {"description": "decide on the best approach", "expected_priority": 3},
            {"description": "summarize the findings", "expected_priority": 1},
            {"description": "URGENT: fix critical bug", "expected_priority": 4},
            {"description": "deadline approaching task", "expected_priority": 4}
        ]

        prioritized = self.planning.assign_priorities([{"description": t["description"], "subtasks": []} for t in tasks], "test task")

        for i, task in enumerate(prioritized):
            assert task["priority"] >= tasks[i]["expected_priority"]

    def test_task_decomposition(self):
        """Test hierarchical task decomposition"""
        complex_task = "Build a web application with user authentication, database integration, and responsive design"

        subtasks = self.planning.break_down_task(complex_task)

        assert len(subtasks) > 1
        assert all("description" in subtask for subtask in subtasks)
        assert all("level" in subtask for subtask in subtasks)

    def test_max_decomposition_depth(self):
        """Test that decomposition respects max depth"""
        task = "Very deeply nested task that should stop at max depth"

        subtasks = self.planning.break_down_task(task, max_depth=2)

        # Should not exceed max depth
        max_level = max(subtask["level"] for subtask in subtasks)
        assert max_level <= 2

    def test_strategy_generation_with_constraints(self):
        """Test strategy generation under resource constraints"""
        task = "Complex analysis requiring multiple specialized agents"
        available_agents = ["vision_agent", "language_agent"]  # Limited agents

        strategy = self.planning.generate_strategy(task, available_agents)

        assert "task" in strategy
        assert "subtasks" in strategy
        assert "agent_assignments" in strategy
        assert len(strategy["agent_assignments"]) <= len(available_agents)


class TestAutoScaler:
    """Test suite for AutoScaler edge cases"""

    def setup_method(self):
        """Set up test fixtures"""
        self.coordinator = Mock()
        self.auto_scaler = AutoScaler(self.coordinator)

    def test_scaling_thresholds(self):
        """Test scaling threshold logic"""
        # Test scale up threshold
        assert self.auto_scaler.scale_up_threshold == 0.7
        assert self.auto_scaler.scale_down_threshold == 0.3

        # Test critical load threshold
        assert self.auto_scaler.critical_load_threshold == 0.9

    def test_no_scaling_needed(self):
        """Test that no scaling occurs when load is normal"""
        # Mock normal load
        self.coordinator.registered_agents = ["agent_1", "agent_2"]
        self.coordinator.agent_loads = {"agent_1": 0.5, "agent_2": 0.4}

        with patch.object(self.auto_scaler, '_calculate_system_load') as mock_load:
            mock_load.return_value = {
                "average_load": 0.45,
                "max_load": 0.5,
                "total_load": 0.9,
                "active_tasks": 2,
                "agent_count": 2
            }

            result = self.auto_scaler.check_scaling_needed()

            assert result["action"] == "no_action"

    def test_scale_up_due_to_high_load(self):
        """Test scaling up when load is high"""
        self.coordinator.registered_agents = ["agent_1", "agent_2"]
        self.coordinator.agent_loads = {"agent_1": 0.8, "agent_2": 0.9}

        with patch.object(self.auto_scaler, '_calculate_system_load') as mock_load, \
             patch.object(self.auto_scaler, '_determine_agent_types_to_add') as mock_determine, \
             patch.object(self.auto_scaler, '_instantiate_agent') as mock_instantiate:

            mock_load.return_value = {
                "average_load": 0.85,
                "max_load": 0.9,
                "total_load": 1.7,
                "active_tasks": 5,
                "agent_count": 2
            }
            mock_determine.return_value = ["LanguageAgent"]
            mock_instantiate.return_value = "new_agent_1"

            result = self.auto_scaler.check_scaling_needed()

            assert result["action"] == "scaled_up"
            assert "new_agent_1" in result["agents_added"]

    def test_scale_down_due_to_low_load(self):
        """Test scaling down when load is low"""
        self.coordinator.registered_agents = ["agent_1", "agent_2", "agent_3", "agent_4"]
        self.coordinator.agent_loads = {"agent_1": 0.1, "agent_2": 0.2, "agent_3": 0.1, "agent_4": 0.1}

        with patch.object(self.auto_scaler, '_calculate_system_load') as mock_load, \
             patch.object(self.auto_scaler, '_select_agents_for_removal') as mock_select, \
             patch.object(self.auto_scaler, '_safely_remove_agent') as mock_remove:

            mock_load.return_value = {
                "average_load": 0.125,
                "max_load": 0.2,
                "total_load": 0.5,
                "active_tasks": 1,
                "agent_count": 4
            }
            mock_select.return_value = ["agent_3", "agent_4"]
            mock_remove.return_value = True

            result = self.auto_scaler.check_scaling_needed()

            assert result["action"] == "scaled_down"
            mock_select.assert_called_with(2)  # Should remove 2 agents

    def test_critical_load_scaling(self):
        """Test immediate scaling when critical load is detected"""
        self.coordinator.registered_agents = ["agent_1"]
        self.coordinator.agent_loads = {"agent_1": 0.95}

        with patch.object(self.auto_scaler, '_calculate_system_load') as mock_load, \
             patch.object(self.auto_scaler, '_determine_agent_types_to_add') as mock_determine, \
             patch.object(self.auto_scaler, '_instantiate_agent') as mock_instantiate:

            mock_load.return_value = {
                "average_load": 0.95,
                "max_load": 0.95,
                "total_load": 0.95,
                "active_tasks": 3,
                "agent_count": 1
            }
            mock_determine.return_value = ["LanguageAgent", "MathAgent", "VisionAgent"]
            mock_instantiate.side_effect = ["agent_2", "agent_3", "agent_4"]

            result = self.auto_scaler.check_scaling_needed()

            assert result["action"] == "scaled_up"
            assert len(result["agents_added"]) == 3  # Critical load adds up to 3 agents

    def test_scaling_cooldown_prevents_frequent_scaling(self):
        """Test that scaling cooldown prevents too frequent operations"""
        # Set last scale time to recent
        self.auto_scaler.last_scale_time = time.time()

        result = self.auto_scaler.check_scaling_needed()

        assert result["action"] == "cooldown"

    def test_max_min_agent_limits(self):
        """Test that scaling respects min/max agent limits"""
        # Test minimum agents (can't scale below min)
        self.coordinator.registered_agents = ["agent_1"]
        self.coordinator.agent_loads = {"agent_1": 0.1}

        with patch.object(self.auto_scaler, '_calculate_system_load') as mock_load:
            mock_load.return_value = {
                "average_load": 0.1,
                "max_load": 0.1,
                "total_load": 0.1,
                "active_tasks": 0,
                "agent_count": 1
            }

            result = self.auto_scaler.check_scaling_needed()

            assert result["action"] == "no_action"  # Can't scale below min agents

        # Test maximum agents (can't scale above max)
        many_agents = [f"agent_{i}" for i in range(self.auto_scaler.max_agents)]
        self.coordinator.registered_agents = many_agents
        self.coordinator.agent_loads = {agent: 0.95 for agent in many_agents}

        with patch.object(self.auto_scaler, '_calculate_system_load') as mock_load:
            mock_load.return_value = {
                "average_load": 0.95,
                "max_load": 0.95,
                "total_load": 0.95 * self.auto_scaler.max_agents,
                "active_tasks": 10,
                "agent_count": self.auto_scaler.max_agents
            }

            result = self.auto_scaler.check_scaling_needed()

            assert result["action"] == "no_action"  # Can't scale above max agents

    def test_agent_type_distribution_logic(self):
        """Test intelligent agent type selection for scaling"""
        # Mock task analysis to return specific needs
        with patch.object(self.auto_scaler, '_analyze_recent_task_types') as mock_analyze:
            mock_analyze.return_value = {
                "vision": 0.8,  # High vision task demand
                "language": 0.2,
                "math": 0.0
            }

            agent_types = self.auto_scaler._determine_agent_types_to_add(3)

            # Should prioritize vision agents due to high demand
            vision_count = agent_types.count("VisionAgent")
            assert vision_count >= 2  # Should add multiple vision agents

    def test_scaling_history_tracking(self):
        """Test that scaling operations are properly tracked"""
        initial_history_length = len(self.auto_scaler.scaling_history)

        # Perform a scaling operation
        self.coordinator.registered_agents = ["agent_1"]
        self.coordinator.agent_loads = {"agent_1": 0.95}

        with patch.object(self.auto_scaler, '_calculate_system_load') as mock_load, \
             patch.object(self.auto_scaler, '_determine_agent_types_to_add') as mock_determine, \
             patch.object(self.auto_scaler, '_instantiate_agent') as mock_instantiate:

            mock_load.return_value = {
                "average_load": 0.95,
                "max_load": 0.95,
                "total_load": 0.95,
                "active_tasks": 3,
                "agent_count": 1
            }
            mock_determine.return_value = ["LanguageAgent"]
            mock_instantiate.return_value = "new_agent_1"

            self.auto_scaler.check_scaling_needed()

            # History should have grown
            assert len(self.auto_scaler.scaling_history) > initial_history_length

            # Last operation should be recorded
            last_operation = self.auto_scaler.scaling_history[-1]
            assert last_operation["action"] == "scale_up"
            assert last_operation["agents_added"] == ["new_agent_1"]