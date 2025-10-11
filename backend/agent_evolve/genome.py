"""
Agent Genome for Evolutionary Algorithms
Represents the genetic material of an agent that can evolve through mutation and crossover.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import random
import copy
from datetime import datetime


@dataclass
class AgentGenome:
    """Represents the genetic material of an agent"""
    weights: List[float]
    mutation_rate: float = 0.05
    generation: int = 0
    fitness_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    parent_ids: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate genome after initialization"""
        if not self.weights:
            raise ValueError("Genome must have at least one weight")

    @classmethod
    def random(cls, num_weights: int, mutation_rate: float = 0.05) -> 'AgentGenome':
        """Create a random genome with specified number of weights"""
        weights = [random.uniform(-1.0, 1.0) for _ in range(num_weights)]
        return cls(weights=weights, mutation_rate=mutation_rate)

    def mutate(self) -> 'AgentGenome':
        """Create a mutated copy of this genome"""
        new_weights = []
        for weight in self.weights:
            if random.random() < self.mutation_rate:
                # Gaussian mutation
                mutation = random.gauss(0, 0.1)
                new_weight = weight + mutation
                # Clamp to reasonable range
                new_weight = max(-2.0, min(2.0, new_weight))
            else:
                new_weight = weight
            new_weights.append(new_weight)

        return AgentGenome(
            weights=new_weights,
            mutation_rate=self.mutation_rate,
            generation=self.generation + 1,
            parent_ids=[f"gen_{self.generation}_id_{id(self)}"]
        )

    def crossover(self, other: 'AgentGenome') -> tuple['AgentGenome', 'AgentGenome']:
        """Perform crossover with another genome to create two offspring"""
        if len(self.weights) != len(other.weights):
            raise ValueError("Genomes must have same number of weights for crossover")

        # Single-point crossover
        crossover_point = random.randint(1, len(self.weights) - 1)

        child1_weights = self.weights[:crossover_point] + other.weights[crossover_point:]
        child2_weights = other.weights[:crossover_point] + self.weights[crossover_point:]

        child1 = AgentGenome(
            weights=child1_weights,
            mutation_rate=self.mutation_rate,
            generation=max(self.generation, other.generation) + 1,
            parent_ids=[f"gen_{self.generation}_id_{id(self)}", f"gen_{other.generation}_id_{id(other)}"]
        )

        child2 = AgentGenome(
            weights=child2_weights,
            mutation_rate=self.mutation_rate,
            generation=max(self.generation, other.generation) + 1,
            parent_ids=[f"gen_{self.generation}_id_{id(self)}", f"gen_{other.generation}_id_{id(other)}"]
        )

        return child1, child2

    def distance(self, other: 'AgentGenome') -> float:
        """Calculate genetic distance to another genome"""
        if len(self.weights) != len(other.weights):
            return float('inf')

        return sum((a - b) ** 2 for a, b in zip(self.weights, other.weights)) ** 0.5

    def copy(self) -> 'AgentGenome':
        """Create a deep copy of this genome"""
        return AgentGenome(
            weights=self.weights.copy(),
            mutation_rate=self.mutation_rate,
            generation=self.generation,
            fitness_score=self.fitness_score,
            parent_ids=self.parent_ids.copy()
        )

    def to_dict(self) -> dict:
        """Serialize genome to dictionary"""
        return {
            "weights": self.weights,
            "mutation_rate": self.mutation_rate,
            "generation": self.generation,
            "fitness_score": self.fitness_score,
            "created_at": self.created_at.isoformat(),
            "parent_ids": self.parent_ids
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AgentGenome':
        """Deserialize genome from dictionary"""
        return cls(
            weights=data["weights"],
            mutation_rate=data.get("mutation_rate", 0.05),
            generation=data.get("generation", 0),
            fitness_score=data.get("fitness_score", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            parent_ids=data.get("parent_ids", [])
        )

    def __str__(self) -> str:
        return f"AgentGenome(gen={self.generation}, fitness={self.fitness_score:.3f}, weights={len(self.weights)})"

    def __repr__(self) -> str:
        return self.__str__()