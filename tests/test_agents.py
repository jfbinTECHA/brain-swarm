"""
Tests for agent functionality.

This module tests individual agent capabilities, behavior profiles,
task execution, and inter-agent communication.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import time

from brain_swarm.agents.agents import VisionAgent, LanguageAgent, MathReasoningAgent, SimulationAgent
from brain_swarm.agents.agent_profiles import AgentBehaviorProfile
from brain_swarm.core.base import Message, MessageType, Task


class TestVisionAgent:
    """Test cases for VisionAgent."""

    @pytest.fixture
    def vision_agent(self):
        """Create a vision agent for testing."""
        return VisionAgent("vision_test", "test_swarm")

    def test_vision_agent_initialization(self, vision_agent):
        """Test vision agent initializes correctly."""
        assert vision_agent.agent_id == "vision_test"
        assert vision_agent.swarm_id == "test_swarm"
        assert hasattr(vision_agent, 'vision_capabilities')
        assert 'image_analysis' in vision_agent.vision_capabilities

    def test_behavior_profile_integration(self, vision_agent):
        """Test behavior profile affects agent decisions."""
        profile = vision_agent.behavior_profile

        # Test profile adaptation
        assert hasattr(profile, 'current_profile')
        assert hasattr(profile, 'get_decision_weight')

    @patch('brain_swarm.agents.agents.PIL_AVAILABLE', False)
    def test_image_analysis_without_pil(self, vision_agent):
        """Test image analysis fallback when PIL not available."""
        result = vision_agent.analyze_image("test.jpg")

        assert isinstance(result, str)
        assert "PIL not available" in result

    @patch('brain_swarm.agents.agents.PIL_AVAILABLE', True)
    @patch('PIL.Image.open')
    def test_image_analysis_with_pil(self, mock_image_open, vision_agent):
        """Test image analysis with PIL available."""
        # Mock PIL Image
        mock_img = MagicMock()
        mock_img.size = (800, 600)
        mock_img.mode = 'RGB'
        mock_img.getcolors.return_value = [(100, (255, 0, 0)), (50, (0, 255, 0))]
        mock_image_open.return_value = mock_img

        result = vision_agent.analyze_image("/path/to/test.jpg")

        assert isinstance(result, str)
        assert "800x600" in result
        assert "RGB" in result

    def test_task_execution(self, vision_agent, sample_task):
        """Test task execution for vision agent."""
        result = vision_agent.execute_task(sample_task)

        assert result is not None
        assert isinstance(result, str)

    def test_message_processing(self, vision_agent, task_assignment_message):
        """Test message processing."""
        # Mock task execution
        with patch.object(vision_agent, 'execute_task', return_value="Task completed") as mock_execute:
            result = vision_agent.process_message(task_assignment_message)

            assert result is not None
            mock_execute.assert_called_once()

    def test_knowledge_sharing(self, vision_agent):
        """Test knowledge sharing between agents."""
        knowledge = {
            "vision_technique": "edge_detection",
            "learned_from": "other_agent",
            "timestamp": time.time()
        }

        # Test receiving knowledge
        message = Message(
            sender="other_agent",
            receiver="vision_test",
            message_type=MessageType.SHARE_KNOWLEDGE,
            content=knowledge,
            timestamp=time.time()
        )

        result = vision_agent.process_message(message)
        assert result is None  # Knowledge sharing doesn't return messages

        # Check knowledge was stored
        assert "edge_detection" in vision_agent.vision_capabilities

    def test_performance_tracking(self, vision_agent):
        """Test performance history tracking."""
        initial_history_length = len(vision_agent.performance_history)

        # Execute a task
        task = {"description": "Test task", "type": "vision_analysis"}
        vision_agent.execute_task(task)

        # Check performance was recorded
        assert len(vision_agent.performance_history) > initial_history_length

        # Check performance data structure
        latest_performance = vision_agent.performance_history[-1]
        assert "task_type" in latest_performance
        assert "success" in latest_performance
        assert "quality" in latest_performance
        assert "execution_time" in latest_performance


class TestLanguageAgent:
    """Test cases for LanguageAgent."""

    @pytest.fixture
    def language_agent(self):
        """Create a language agent for testing."""
        return LanguageAgent("lang_test", "test_swarm")

    def test_language_agent_initialization(self, language_agent):
        """Test language agent initializes correctly."""
        assert language_agent.agent_id == "lang_test"
        assert hasattr(language_agent, 'language_capabilities')
        assert 'text_processing' in language_agent.language_capabilities

    def test_text_processing(self, language_agent, test_text_data):
        """Test basic text processing."""
        result = language_agent.process_text(test_text_data)

        assert isinstance(result, dict)
        assert "processed_text" in result or isinstance(result, str)

    def test_summarization(self, language_agent):
        """Test text summarization."""
        long_text = "This is a very long text that needs to be summarized. " * 10
        result = language_agent.summarize_text(long_text)

        assert isinstance(result, str)
        assert len(result) < len(long_text)

    def test_sentiment_analysis(self, language_agent):
        """Test sentiment analysis."""
        positive_text = "I love this amazing product!"
        negative_text = "This is terrible and awful."

        result_pos = language_agent.analyze_sentiment(positive_text)
        result_neg = language_agent.analyze_sentiment(negative_text)

        assert isinstance(result_pos, str)
        assert isinstance(result_neg, str)

    @patch('brain_swarm.agents.agents.requests.get')
    def test_api_integration(self, mock_get, language_agent):
        """Test external API integration."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "AbstractText": "Test abstract from API",
            "Answer": "Test answer"
        }
        mock_get.return_value = mock_response

        result = language_agent.query_knowledge_api("test query")

        assert "Test abstract from API" in result
        mock_get.assert_called_once()


class TestMathReasoningAgent:
    """Test cases for MathReasoningAgent."""

    @pytest.fixture
    def math_agent(self):
        """Create a math reasoning agent for testing."""
        return MathReasoningAgent("math_test", "test_swarm")

    def test_math_agent_initialization(self, math_agent):
        """Test math agent initializes correctly."""
        assert math_agent.agent_id == "math_test"
        assert hasattr(math_agent, 'math_capabilities')

    def test_calculation(self, math_agent, test_math_problem):
        """Test mathematical calculations."""
        result = math_agent.solve_equation(test_math_problem)

        assert isinstance(result, str)
        # Should contain the solution x = 2
        assert "x = 2" in result or "x=2" in result

    def test_logical_reasoning(self, math_agent):
        """Test logical reasoning capabilities."""
        premise = "All humans are mortal. Socrates is human."
        result = math_agent.logical_reasoning(premise)

        assert isinstance(result, str)
        assert len(result) > 0

    @patch('brain_swarm.agents.agents.sympy')
    def test_symbolic_math(self, mock_sympy, math_agent):
        """Test symbolic mathematics with sympy."""
        # Mock sympy availability
        mock_sympy.__bool__ = lambda: True
        mock_sympy.__nonzero__ = lambda: True

        # This would test advanced symbolic math
        # Implementation depends on sympy integration
        pass


class TestSimulationAgent:
    """Test cases for SimulationAgent."""

    @pytest.fixture
    def simulation_agent(self):
        """Create a simulation agent for testing."""
        return SimulationAgent("sim_test", "test_swarm")

    def test_simulation_agent_initialization(self, simulation_agent):
        """Test simulation agent initializes correctly."""
        assert simulation_agent.agent_id == "sim_test"
        assert hasattr(simulation_agent, 'simulation_capabilities')

    def test_scenario_simulation(self, simulation_agent):
        """Test scenario simulation."""
        scenario = "A startup launching a new product"
        result = simulation_agent.simulate_scenario(scenario)

        assert isinstance(result, dict)
        assert "scenario" in result
        assert "simulation_steps" in result

    def test_outcome_prediction(self, simulation_agent):
        """Test outcome prediction."""
        conditions = "Good market conditions with strong competition"
        result = simulation_agent.predict_outcome(conditions)

        assert isinstance(result, str)
        assert len(result) > 0


class TestAgentBehaviorProfiles:
    """Test cases for agent behavior profiles."""

    def test_behavior_profile_creation(self):
        """Test behavior profile creation."""
        profile = AgentBehaviorProfile("balanced")

        assert profile.current_profile == "balanced"
        assert hasattr(profile, 'decision_weights')

    def test_profile_adaptation(self):
        """Test profile adaptation based on performance."""
        profile = AgentBehaviorProfile("aggressive")

        # Simulate good performance feedback
        feedback = {
            "task_success": True,
            "task_quality": 0.9,
            "task_time": 1.0
        }

        initial_profile = profile.current_profile
        profile.adapt_profile(feedback)

        # Profile should remain stable or improve
        assert profile.current_profile in ["aggressive", "balanced", "conservative"]

    def test_decision_weight_calculation(self):
        """Test decision weight calculations."""
        profile = AgentBehaviorProfile("creative")

        creative_weight = profile.get_decision_weight("creative")
        precise_weight = profile.get_decision_weight("precise")

        assert isinstance(creative_weight, (int, float))
        assert isinstance(precise_weight, (int, float))
        assert creative_weight >= precise_weight  # Creative profile favors creativity


class TestAgentCommunication:
    """Test cases for inter-agent communication."""

    @pytest.fixture
    def agent_pair(self):
        """Create a pair of agents for communication testing."""
        agent1 = VisionAgent("agent1", "test_swarm")
        agent2 = LanguageAgent("agent2", "test_swarm")
        return agent1, agent2

    def test_knowledge_sharing_workflow(self, agent_pair):
        """Test knowledge sharing between agents."""
        agent1, agent2 = agent_pair

        # Agent1 shares knowledge with Agent2
        knowledge = {
            "technique": "image_captioning",
            "accuracy": 0.85,
            "timestamp": time.time()
        }

        # Simulate knowledge sharing
        message = Message(
            sender="agent1",
            receiver="agent2",
            message_type=MessageType.SHARE_KNOWLEDGE,
            content=knowledge,
            timestamp=time.time()
        )

        result = agent2.process_message(message)

        # Agent2 should process the knowledge
        assert result is None

    def test_task_collaboration(self, agent_pair):
        """Test collaborative task execution."""
        agent1, agent2 = agent_pair

        # Complex task requiring both agents
        complex_task = {
            "description": "Analyze diagram, extract text, generate summary",
            "type": "multi_modal_analysis",
            "requires_collaboration": True
        }

        # Each agent handles their part
        result1 = agent1.execute_task({
            "description": "Extract text from diagram",
            "type": "vision_analysis"
        })

        result2 = agent2.execute_task({
            "description": "Summarize extracted text",
            "type": "text_summarization",
            "context": result1
        })

        assert result1 is not None
        assert result2 is not None


class TestAgentPerformance:
    """Test cases for agent performance monitoring."""

    def test_performance_metrics_collection(self, vision_agent):
        """Test performance metrics are collected."""
        initial_count = len(vision_agent.performance_history)

        # Execute multiple tasks
        for i in range(3):
            task = {"description": f"Task {i}", "type": "vision_analysis"}
            vision_agent.execute_task(task)

        # Check metrics were collected
        assert len(vision_agent.performance_history) == initial_count + 3

        # Verify metric structure
        for metric in vision_agent.performance_history:
            assert "task_type" in metric
            assert "success" in metric
            assert "quality" in metric
            assert "execution_time" in metric
            assert "timestamp" in metric

    def test_performance_based_adaptation(self, vision_agent):
        """Test agents adapt based on performance."""
        # Simulate poor performance
        for _ in range(5):
            task = {"description": "Failing task", "type": "vision_analysis"}
            # Mock poor performance
            with patch.object(vision_agent, 'analyze_image', return_value="Failed analysis"):
                vision_agent.execute_task(task)

        # Check if profile adapted
        # This depends on the adaptation logic implementation
        assert len(vision_agent.performance_history) >= 5