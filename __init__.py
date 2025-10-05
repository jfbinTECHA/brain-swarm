"""
Brain Swarm - Multi-Agent Swarm Intelligence System

A comprehensive framework for coordinating intelligent agents in distributed swarms,
featuring predictive analytics, self-tuning capabilities, and real-time monitoring.

Package Structure:
├── core/           # Base classes, types, and utilities
├── agents/         # Agent implementations and behaviors
├── coordination/   # Swarm coordination and task delegation
├── memory/         # Working and long-term memory systems
├── analytics/      # Predictive analytics and optimization
├── security/       # Governance, policies, and authentication
├── federation/     # Cross-swarm coordination and resource sharing
├── dashboard/      # Real-time monitoring and visualization
└── utils/          # Utility functions and helpers
"""

__version__ = "1.0.0"
__author__ = "Brain Swarm Team"
__description__ = "Multi-Agent Swarm Intelligence System"

# Core imports for easy access
from .core.base import BaseAgent, AgentRole, Message, MessageType, Task, logger, metrics
from .coordination.coordinator import SwarmCoordinator
from .agents.agents import VisionAgent, LanguageAgent, MathReasoningAgent, SimulationAgent
from .memory.memory import WorkingMemory, LongTermMemory
from .dashboard.dashboard import BrainSwarmDashboard

__all__ = [
    # Core classes
    'BaseAgent', 'SwarmCoordinator', 'BrainSwarmDashboard',

    # Agent types
    'VisionAgent', 'LanguageAgent', 'MathReasoningAgent', 'SimulationAgent',

    # Memory systems
    'WorkingMemory', 'LongTermMemory',

    # Base types
    'AgentRole', 'Message', 'MessageType', 'Task', 'logger', 'metrics'
]