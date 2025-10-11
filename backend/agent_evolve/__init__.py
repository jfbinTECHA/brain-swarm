"""
Agent Evolution Engine for Brain-Swarm
Implements evolutionary algorithms for agent adaptation and learning.
"""

from .genome import AgentGenome
from .evolution import EvolutionaryAlgorithm, NoveltySearch, EvolutionConfig
from .fitness_evaluator import FitnessEvaluator, TaskBasedFitnessEvaluator, get_fitness_function

# Import performance measures
from .fitness import (
    PERFORMANCE_MEASURES,
    get_performance_measure,
    composite_fitness_score,
    comprehensive_agent_fitness
)

__all__ = [
    "AgentGenome",
    "EvolutionaryAlgorithm",
    "NoveltySearch",
    "EvolutionConfig",
    "FitnessEvaluator",
    "TaskBasedFitnessEvaluator",
    "get_fitness_function",
    "PERFORMANCE_MEASURES",
    "get_performance_measure",
    "composite_fitness_score",
    "comprehensive_agent_fitness"
]