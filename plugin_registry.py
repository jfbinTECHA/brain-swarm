"""
Plugin Registry System for Dynamic Agent Registration and Management

This system allows agents to be registered as plugins with metadata,
enabling dynamic loading, instantiation, and capability discovery.
Similar to FastAPI's dependency_overrides but for agents.
"""

from typing import Dict, List, Any, Optional, Type, Callable
from abc import ABC, abstractmethod
import importlib
import inspect
from dataclasses import dataclass
from core.base import BaseAgent, AgentRole
from security.auth import verify_api_key


@dataclass
class AgentMetadata:
    """Metadata for registered agents"""
    name: str
    version: str
    description: str
    capabilities: List[str]
    dependencies: List[str]
    author: str
    tags: List[str]
    config_schema: Optional[Dict[str, Any]] = None
    agent_class: Optional[Type[BaseAgent]] = None


class AgentPlugin(ABC):
    """Base class for agent plugins"""

    @property
    @abstractmethod
    def metadata(self) -> AgentMetadata:
        """Return plugin metadata"""
        pass

    @abstractmethod
    def create_agent(self, agent_id: str, swarm_id: Optional[str] = None, **kwargs) -> BaseAgent:
        """Create an instance of the agent"""
        pass


class ClassBasedAgentPlugin(AgentPlugin):
    """Plugin wrapper for class-based agents"""

    def __init__(self, agent_class: Type[BaseAgent], metadata: AgentMetadata):
        self._agent_class = agent_class
        self._metadata = metadata
        self._metadata.agent_class = agent_class

    @property
    def metadata(self) -> AgentMetadata:
        return self._metadata

    def create_agent(self, agent_id: str, swarm_id: Optional[str] = None, **kwargs) -> BaseAgent:
        """Create agent instance with provided kwargs"""
        return self._agent_class(agent_id=agent_id, swarm_id=swarm_id, **kwargs)


class AgentRegistry:
    """Registry for managing agent plugins"""

    def __init__(self):
        self._plugins: Dict[str, AgentPlugin] = {}
        self._capabilities_index: Dict[str, List[str]] = {}  # capability -> list of agent names
        self._tags_index: Dict[str, List[str]] = {}  # tag -> list of agent names

    def register(self, plugin: AgentPlugin) -> None:
        """Register an agent plugin"""
        name = plugin.metadata.name
        if name in self._plugins:
            raise ValueError(f"Agent plugin '{name}' is already registered")

        self._plugins[name] = plugin

        # Update capability index
        for capability in plugin.metadata.capabilities:
            if capability not in self._capabilities_index:
                self._capabilities_index[capability] = []
            self._capabilities_index[capability].append(name)

        # Update tag index
        for tag in plugin.metadata.tags:
            if tag not in self._tags_index:
                self._tags_index[tag] = []
            self._tags_index[tag].append(name)

    def register_class(self, agent_class: Type[BaseAgent], metadata: AgentMetadata) -> None:
        """Register an agent class directly"""
        plugin = ClassBasedAgentPlugin(agent_class, metadata)
        self.register(plugin)

    def unregister(self, name: str) -> None:
        """Unregister an agent plugin"""
        if name not in self._plugins:
            raise ValueError(f"Agent plugin '{name}' is not registered")

        plugin = self._plugins[name]

        # Remove from capability index
        for capability in plugin.metadata.capabilities:
            if capability in self._capabilities_index:
                self._capabilities_index[capability].remove(name)
                if not self._capabilities_index[capability]:
                    del self._capabilities_index[capability]

        # Remove from tag index
        for tag in plugin.metadata.tags:
            if tag in self._tags_index:
                self._tags_index[tag].remove(name)
                if not self._tags_index[tag]:
                    del self._tags_index[tag]

        del self._plugins[name]

    def get_plugin(self, name: str) -> Optional[AgentPlugin]:
        """Get a plugin by name"""
        return self._plugins.get(name)

    def list_plugins(self) -> List[str]:
        """List all registered plugin names"""
        return list(self._plugins.keys())

    def find_by_capability(self, capability: str) -> List[str]:
        """Find agents that have a specific capability"""
        return self._capabilities_index.get(capability, [])

    def find_by_tag(self, tag: str) -> List[str]:
        """Find agents that have a specific tag"""
        return self._tags_index.get(tag, [])

    def search(self, query: str) -> List[str]:
        """Search for agents by name, description, or capabilities"""
        query_lower = query.lower()
        results = []

        for name, plugin in self._plugins.items():
            if (query_lower in name.lower() or
                query_lower in plugin.metadata.description.lower() or
                any(query_lower in cap.lower() for cap in plugin.metadata.capabilities)):
                results.append(name)

        return results

    def get_metadata(self, name: str) -> Optional[AgentMetadata]:
        """Get metadata for a plugin"""
        plugin = self.get_plugin(name)
        return plugin.metadata if plugin else None

    def create_agent(self, name: str, agent_id: str, swarm_id: Optional[str] = None, api_key: Optional[str] = None, **kwargs) -> Optional[BaseAgent]:
        """Create an agent instance with API key verification"""
        plugin = self.get_plugin(name)
        if not plugin:
            return None

        # Verify API key if required
        if api_key and not verify_api_key(api_key):
            raise ValueError(f"Invalid API key for agent {name}")

        return plugin.create_agent(agent_id, swarm_id, **kwargs)

    def get_capabilities(self) -> Dict[str, List[str]]:
        """Get all available capabilities and their agents"""
        return dict(self._capabilities_index)

    def get_tags(self) -> Dict[str, List[str]]:
        """Get all available tags and their agents"""
        return dict(self._tags_index)

    def validate_dependencies(self, name: str) -> List[str]:
        """Validate that all dependencies for an agent are available"""
        plugin = self.get_plugin(name)
        if not plugin:
            return [f"Agent '{name}' not found"]

        missing_deps = []
        for dep in plugin.metadata.dependencies:
            if dep not in self._plugins:
                missing_deps.append(dep)

        return missing_deps


# Global registry instance
agent_registry = AgentRegistry()


def register_agent_class(
    agent_class: Type[BaseAgent],
    name: str,
    version: str = "1.0.0",
    description: str = "",
    capabilities: Optional[List[str]] = None,
    dependencies: Optional[List[str]] = None,
    author: str = "Unknown",
    tags: Optional[List[str]] = None,
    config_schema: Optional[Dict[str, Any]] = None
) -> None:
    """Decorator to register an agent class with the registry"""

    def decorator(cls: Type[BaseAgent]) -> Type[BaseAgent]:
        metadata = AgentMetadata(
            name=name,
            version=version,
            description=description or cls.__doc__ or f"{name} agent",
            capabilities=capabilities or [],
            dependencies=dependencies or [],
            author=author,
            tags=tags or [],
            config_schema=config_schema
        )
        agent_registry.register_class(cls, metadata)
        return cls

    # If called as @register_agent_class, apply to the class
    if inspect.isclass(agent_class):
        return decorator(agent_class)
    # If called as @register_agent_class(...), return decorator
    else:
        # This is the decorator factory case
        return decorator


def load_plugin_from_module(module_path: str, plugin_name: str) -> None:
    """Load a plugin from a Python module"""
    try:
        module = importlib.import_module(module_path)
        plugin = getattr(module, plugin_name)
        if isinstance(plugin, AgentPlugin):
            agent_registry.register(plugin)
        else:
            raise ValueError(f"Plugin '{plugin_name}' in module '{module_path}' is not an AgentPlugin")
    except Exception as e:
        raise ImportError(f"Failed to load plugin '{plugin_name}' from '{module_path}': {e}")


def discover_plugins_in_package(package_name: str) -> None:
    """Discover and load all plugins in a package"""
    try:
        package = importlib.import_module(package_name)
        package_path = package.__path__[0]

        # This would require more complex plugin discovery logic
        # For now, just try to import known plugin modules
        potential_plugins = [
            f"{package_name}.vision_plugin",
            f"{package_name}.language_plugin",
            f"{package_name}.math_plugin",
            f"{package_name}.simulation_plugin"
        ]

        for plugin_module in potential_plugins:
            try:
                load_plugin_from_module(plugin_module, "plugin")
            except ImportError:
                continue  # Plugin not found, skip

    except Exception as e:
        raise ImportError(f"Failed to discover plugins in package '{package_name}': {e}")


# Auto-register built-in agents
def _register_builtin_agents():
    """Register the built-in agents that come with the system"""
    from agents.agents import VisionAgent, LanguageAgent, MathReasoningAgent, SimulationAgent

    # Vision Agent
    agent_registry.register_class(
        VisionAgent,
        AgentMetadata(
            name="vision_agent",
            version="1.0.0",
            description="Processes images and visual reasoning tasks",
            capabilities=["image_analysis", "object_detection", "scene_description"],
            dependencies=[],
            author="Brain Swarm Team",
            tags=["vision", "image", "analysis"],
            agent_class=VisionAgent
        )
    )

    # Language Agent
    agent_registry.register_class(
        LanguageAgent,
        AgentMetadata(
            name="language_agent",
            version="1.0.0",
            description="Handles NLP, summarization, and dialogue",
            capabilities=["summarization", "sentiment_analysis", "dialogue_generation"],
            dependencies=[],
            author="Brain Swarm Team",
            tags=["language", "nlp", "text"],
            agent_class=LanguageAgent
        )
    )

    # Math Reasoning Agent
    agent_registry.register_class(
        MathReasoningAgent,
        AgentMetadata(
            name="math_agent",
            version="1.0.0",
            description="Performs calculations and logical reasoning",
            capabilities=["calculation", "logical_reasoning", "problem_solving"],
            dependencies=[],
            author="Brain Swarm Team",
            tags=["math", "logic", "calculation"],
            agent_class=MathReasoningAgent
        )
    )

    # Simulation Agent
    agent_registry.register_class(
        SimulationAgent,
        AgentMetadata(
            name="simulation_agent",
            version="1.0.0",
            description="Runs scenario simulations and sandbox tests",
            capabilities=["scenario_simulation", "sandbox_testing", "outcome_prediction"],
            dependencies=[],
            author="Brain Swarm Team",
            tags=["simulation", "testing", "prediction"],
            agent_class=SimulationAgent
        )
    )


# Initialize built-in agents
_register_builtin_agents()