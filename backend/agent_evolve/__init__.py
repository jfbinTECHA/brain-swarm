"""
Agent Evolution Engine for Brain-Swarm
Implements evolutionary algorithms for agent adaptation and learning.
"""

from .genome import AgentGenome
from .evolution import EvolutionaryAlgorithm, NoveltySearch, EvolutionConfig
from .fitness import FitnessEvaluator, TaskBasedFitnessEvaluator, get_fitness_function

__all__ = [
    "AgentGenome",
    "EvolutionaryAlgorithm",
    "NoveltySearch",
    "EvolutionConfig",
    "FitnessEvaluator",
    "TaskBasedFitnessEvaluator",
    "get_fitness_function"
]