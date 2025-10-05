"""
Pytest configuration and shared fixtures for Brain Swarm tests.

This module provides common test fixtures, utilities, and configuration
for the Brain Swarm testing suite.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any, List, Optional
import time

from brain_swarm.core.base import BaseAgent, AgentRole, Message, MessageType, Task
from brain_swarm.coordination.coordinator import SwarmCoordinator
from brain_swarm.agents.agents import VisionAgent, LanguageAgent, MathReasoningAgent
from brain_swarm.memory.memory import WorkingMemory, LongTermMemory
from brain_swarm.api.main import create_app


# Test Configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# Agent Fixtures
@pytest.fixture
def base_agent():
    """Create a basic agent for testing."""
    return BaseAgent("test_agent", AgentRole.DEFAULT_MODE_NETWORK, "test_swarm")


@pytest.fixture
def vision_agent():
    """Create a vision agent for testing."""
    return VisionAgent("vision_test", "test_swarm")


@pytest.fixture
def language_agent():
    """Create a language agent for testing."""
    return LanguageAgent("lang_test", "test_swarm")


@pytest.fixture
def math_agent():
    """Create a math reasoning agent for testing."""
    return MathReasoningAgent("math_test", "test_swarm")


# Coordinator Fixtures
@pytest.fixture
def swarm_coordinator():
    """Create a swarm coordinator for testing."""
    coordinator = SwarmCoordinator("test_swarm")

    # Mock memory systems to avoid dependencies
    coordinator.working_memory = MagicMock(spec=WorkingMemory)
    coordinator.long_term_memory = MagicMock(spec=LongTermMemory)

    return coordinator


@pytest.fixture
def coordinator_with_agents(swarm_coordinator, vision_agent, language_agent):
    """Create a coordinator with registered agents."""
    swarm_coordinator.register_agent("vision_test")
    swarm_coordinator.register_agent("lang_test")
    return swarm_coordinator


# Memory Fixtures
@pytest.fixture
def working_memory():
    """Create a working memory instance for testing."""
    return WorkingMemory(max_size=100)


@pytest.fixture
def long_term_memory():
    """Create a long-term memory instance for testing."""
    return LongTermMemory(max_size=1000)


# Task Fixtures
@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return {
        "description": "Analyze this image and provide a detailed description",
        "type": "vision_analysis",
        "priority": 2,
        "metadata": {"format": "jpg", "size": "2MB"}
    }


@pytest.fixture
def complex_task():
    """Create a complex multi-step task for testing."""
    return {
        "description": "Process this dataset: extract text from images, analyze sentiment, generate summary report",
        "type": "multi_modal_analysis",
        "priority": 4,
        "metadata": {
            "steps": ["vision", "nlp", "summarization"],
            "estimated_time": 300
        }
    }


# Message Fixtures
@pytest.fixture
def task_assignment_message():
    """Create a task assignment message."""
    return Message(
        sender="coordinator",
        receiver="vision_test",
        message_type=MessageType.TASK_ASSIGNMENT,
        content={
            "task": Task("task_123", "Test task", {}, "vision_test")
        },
        timestamp=time.time()
    )


@pytest.fixture
def result_report_message():
    """Create a result report message."""
    return Message(
        sender="vision_test",
        receiver="coordinator",
        message_type=MessageType.RESULT_REPORT,
        content={
            "task_id": "task_123",
            "result": "Analysis complete",
            "success": True
        },
        timestamp=time.time()
    )


# API Fixtures
@pytest.fixture
def test_app():
    """Create a test FastAPI application."""
    app = create_app()
    return app


@pytest.fixture
def test_client(test_app):
    """Create a test client for API testing."""
    from fastapi.testclient import TestClient
    return TestClient(test_app)


# Mock Fixtures
@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls."""
    with patch('openai.Completion.create') as mock_completion:
        mock_completion.return_value = {
            'choices': [{'text': 'Mock response from OpenAI'}]
        }
        yield mock_completion


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    mock_ws = AsyncMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.receive_json = AsyncMock()
    mock_ws.close = AsyncMock()
    return mock_ws


# Test Data Fixtures
@pytest.fixture
def test_image_data():
    """Create test image data."""
    return b"mock_image_data_jpeg_format"


@pytest.fixture
def test_text_data():
    """Create test text data."""
    return "This is a sample text for testing language processing capabilities."


@pytest.fixture
def test_math_problem():
    """Create a test math problem."""
    return "Solve for x: 2x + 3 = 7"


# Performance Testing Fixtures
@pytest.fixture
def performance_metrics():
    """Create performance metrics for testing."""
    return {
        "execution_time": 1.5,
        "memory_usage": 50.2,
        "cpu_usage": 15.3,
        "success_rate": 0.95
    }


# Configuration Fixtures
@pytest.fixture
def test_config():
    """Create test configuration."""
    return {
        "BRAIN_SWARM_MODE": "test",
        "LOG_LEVEL": "DEBUG",
        "MAX_AGENT_LOAD": 2,
        "WORKING_MEMORY_SIZE": 50,
        "LONG_TERM_MEMORY_SIZE": 200
    }


# Utility Functions
def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
    """Wait for a condition to become true."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    return False


def assert_eventually_true(condition_func, timeout=5.0, message="Condition not met"):
    """Assert that a condition becomes true within a timeout."""
    assert wait_for_condition(condition_func, timeout), message


# Test Markers
pytestmark = [
    pytest.mark.asyncio
]


# Cleanup
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up after each test."""
    yield
    # Add any cleanup logic here
    pass