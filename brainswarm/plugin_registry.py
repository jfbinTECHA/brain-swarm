# brainswarm.plugin_registry
# Temporary stub for plugin and agent registry integration

from typing import Dict, Any

# In a full version, this would dynamically discover and register agent classes.
agent_registry: Dict[str, Any] = {
    "default_agent": {
        "name": "Default Swarm Agent",
        "version": "0.1.0",
        "capabilities": ["observe", "act", "learn"],
        "status": "stubbed",
    }
}

def register_plugin(name: str, plugin_obj: Any):
    """Register a plugin or extension."""
    agent_registry[name] = plugin_obj

def get_registered_plugins():
    """Return all registered plugins."""
    return list(agent_registry.keys())

def get_plugin_info(name: str) -> Dict[str, Any]:
    """Return metadata for a given plugin."""
    return agent_registry.get(name, {"error": "not found"})
