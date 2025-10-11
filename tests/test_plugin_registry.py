"""
Tests for the Plugin Registry system
"""

import pytest
from unittest.mock import MagicMock
from ..plugin_registry import AgentRegistry, AgentMetadata, ClassBasedAgentPlugin
from ..core.base import BaseAgent, AgentRole


class MockAgent(BaseAgent):
    """Mock agent for testing"""

    def __init__(self, agent_id: str, swarm_id: str = None):
        super().__init__(agent_id, AgentRole.DEFAULT_MODE_NETWORK, swarm_id)
        self.test_called = False

    def execute_task(self, task):
        self.test_called = True
        return "mock_result"


class TestAgentRegistry:
    """Test cases for AgentRegistry"""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test"""
        return AgentRegistry()

    @pytest.fixture
    def mock_plugin(self):
        """Create a mock plugin"""
        metadata = AgentMetadata(
            name="test_agent",
            version="1.0.0",
            description="Test agent",
            capabilities=["test"],
            dependencies=[],
            author="Test Author",
            tags=["test"]
        )
        return ClassBasedAgentPlugin(MockAgent, metadata)

    def test_register_plugin(self, registry, mock_plugin):
        """Test registering a plugin"""
        registry.register(mock_plugin)

        assert "test_agent" in registry.list_plugins()
        assert registry.get_plugin("test_agent") == mock_plugin

    def test_register_duplicate_plugin(self, registry, mock_plugin):
        """Test that registering duplicate plugins raises error"""
        registry.register(mock_plugin)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(mock_plugin)

    def test_unregister_plugin(self, registry, mock_plugin):
        """Test unregistering a plugin"""
        registry.register(mock_plugin)
        assert "test_agent" in registry.list_plugins()

        registry.unregister("test_agent")
        assert "test_agent" not in registry.list_plugins()

    def test_unregister_nonexistent_plugin(self, registry):
        """Test unregistering non-existent plugin raises error"""
        with pytest.raises(ValueError, match="not registered"):
            registry.unregister("nonexistent")

    def test_find_by_capability(self, registry, mock_plugin):
        """Test finding agents by capability"""
        registry.register(mock_plugin)

        results = registry.find_by_capability("test")
        assert "test_agent" in results

        results = registry.find_by_capability("nonexistent")
        assert results == []

    def test_find_by_tag(self, registry, mock_plugin):
        """Test finding agents by tag"""
        registry.register(mock_plugin)

        results = registry.find_by_tag("test")
        assert "test_agent" in results

        results = registry.find_by_tag("nonexistent")
        assert results == []

    def test_search(self, registry, mock_plugin):
        """Test searching agents"""
        registry.register(mock_plugin)

        # Search by name
        results = registry.search("test_agent")
        assert "test_agent" in results

        # Search by description
        results = registry.search("Test agent")
        assert "test_agent" in results

        # Search by capability
        results = registry.search("test")
        assert "test_agent" in results

        # Search non-existent
        results = registry.search("nonexistent")
        assert results == []

    def test_create_agent(self, registry, mock_plugin):
        """Test creating an agent instance"""
        registry.register(mock_plugin)

        agent = registry.create_agent("test_agent", "test_id", "swarm_1")
        assert isinstance(agent, MockAgent)
        assert agent.agent_id == "test_id"
        assert agent.swarm_id == "swarm_1"

    def test_create_agent_with_invalid_api_key(self, registry, mock_plugin):
        """Test creating agent with invalid API key"""
        registry.register(mock_plugin)

        with pytest.raises(ValueError, match="Invalid API key"):
            registry.create_agent("test_agent", "test_id", "swarm_1", api_key="invalid")

    def test_create_nonexistent_agent(self, registry):
        """Test creating non-existent agent returns None"""
        agent = registry.create_agent("nonexistent", "test_id")
        assert agent is None

    def test_get_metadata(self, registry, mock_plugin):
        """Test getting plugin metadata"""
        registry.register(mock_plugin)

        metadata = registry.get_metadata("test_agent")
        assert metadata == mock_plugin.metadata

        metadata = registry.get_metadata("nonexistent")
        assert metadata is None

    def test_get_capabilities_and_tags(self, registry, mock_plugin):
        """Test getting capabilities and tags index"""
        registry.register(mock_plugin)

        capabilities = registry.get_capabilities()
        assert "test" in capabilities
        assert "test_agent" in capabilities["test"]

        tags = registry.get_tags()
        assert "test" in tags
        assert "test_agent" in tags["test"]

    def test_validate_dependencies(self, registry, mock_plugin):
        """Test dependency validation"""
        registry.register(mock_plugin)

        # No dependencies, should pass
        missing = registry.validate_dependencies("test_agent")
        assert missing == []

        # Create plugin with dependency
        dep_metadata = AgentMetadata(
            name="dependent_agent",
            version="1.0.0",
            description="Dependent agent",
            capabilities=["dep"],
            dependencies=["test_agent"],
            author="Test",
            tags=["dep"]
        )
        dep_plugin = ClassBasedAgentPlugin(MockAgent, dep_metadata)
        registry.register(dep_plugin)

        # Should validate successfully
        missing = registry.validate_dependencies("dependent_agent")
        assert missing == []

        # Unregister dependency
        registry.unregister("test_agent")

        # Should now have missing dependency
        missing = registry.validate_dependencies("dependent_agent")
        assert "test_agent" in missing


class TestAgentMetadata:
    """Test cases for AgentMetadata"""

    def test_metadata_creation(self):
        """Test creating metadata"""
        metadata = AgentMetadata(
            name="test",
            version="1.0.0",
            description="Test agent",
            capabilities=["cap1", "cap2"],
            dependencies=["dep1"],
            author="Author",
            tags=["tag1"]
        )

        assert metadata.name == "test"
        assert metadata.version == "1.0.0"
        assert metadata.capabilities == ["cap1", "cap2"]
        assert metadata.dependencies == ["dep1"]
        assert metadata.author == "Author"
        assert metadata.tags == ["tag1"]