"""
Agent implementations and behaviors.

This module contains all agent types and their specialized capabilities,
including vision processing, language understanding, mathematical reasoning,
and simulation capabilities.
"""

from .agents import (
    VisionAgent, LanguageAgent, MathReasoningAgent, SimulationAgent,
    ImaginationSimulation
)
from .agent_profiles import AgentBehaviorProfile, apply_behavior_modifier, get_behavior_description

__all__ = [
    # Agent types
    'VisionAgent', 'LanguageAgent', 'MathReasoningAgent', 'SimulationAgent',
    'ImaginationSimulation',

    # Behavior profiles
    'AgentBehaviorProfile', 'apply_behavior_modifier', 'get_behavior_description'
]