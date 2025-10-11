"""
Fitness Evaluation System for Agent Evolution
Defines fitness functions and evaluation mechanisms for evolved agents.
"""

import time
import asyncio
from typing import Callable, Dict, Any, List, Optional, Awaitable
from dataclasses import dataclass
from .genome import AgentGenome


@dataclass
class FitnessResult:
    """Result of a fitness evaluation"""
    score: float
    metrics: Dict[str, Any]
    duration: float
    success: bool
    error_message: Optional[str] = None


class FitnessEvaluator:
    """Evaluates fitness of agent genomes"""

    def __init__(self):
        self.evaluation_cache: Dict[str, FitnessResult] = {}
        self.max_cache_size = 1000

    def evaluate_sync(self, genome: AgentGenome, fitness_function: Callable[[AgentGenome], float]) -> FitnessResult:
        """Synchronously evaluate genome fitness"""
        start_time = time.time()

        try:
            score = fitness_function(genome)
            duration = time.time() - start_time

            result = FitnessResult(
                score=score,
                metrics={"raw_score": score},
                duration=duration,
                success=True
            )

        except Exception as e:
            duration = time.time() - start_time
            result = FitnessResult(
                score=float('-inf'),
                metrics={},
                duration=duration,
                success=False,
                error_message=str(e)
            )

        return result

    async def evaluate_async(self, genome: AgentGenome, fitness_function: Callable[[AgentGenome], Awaitable[float]]) -> FitnessResult:
        """Asynchronously evaluate genome fitness"""
        start_time = time.time()

        try:
            score = await fitness_function(genome)
            duration = time.time() - start_time

            result = FitnessResult(
                score=score,
                metrics={"raw_score": score},
                duration=duration,
                success=True
            )

        except Exception as e:
            duration = time.time() - start_time
            result = FitnessResult(
                score=float('-inf'),
                metrics={},
                duration=duration,
                success=False,
                error_message=str(e)
            )

        return result

    def get_cached_result(self, genome_id: str) -> Optional[FitnessResult]:
        """Get cached fitness result for genome"""
        return self.evaluation_cache.get(genome_id)

    def cache_result(self, genome_id: str, result: FitnessResult):
        """Cache fitness result for genome"""
        if len(self.evaluation_cache) >= self.max_cache_size:
            # Simple cache eviction - remove oldest
            oldest_key = next(iter(self.evaluation_cache))
            del self.evaluation_cache[oldest_key]

        self.evaluation_cache[genome_id] = result


# Common fitness functions

def simple_weighted_sum_fitness(genome: AgentGenome) -> float:
    """Simple fitness based on weighted sum of genome weights"""
    return sum(genome.weights)


def quadratic_fitness(genome: AgentGenome) -> float:
    """Fitness based on quadratic function of weights"""
    return sum(w ** 2 for w in genome.weights)


def target_vector_fitness(target: List[float]):
    """Create fitness function that measures distance to target vector"""
    def fitness(genome: AgentGenome) -> float:
        if len(genome.weights) != len(target):
            return float('-inf')

        # Negative distance (higher fitness = closer to target)
        distance = sum((a - b) ** 2 for a, b in zip(genome.weights, target))
        return -distance

    return fitness


def agent_task_performance_fitness(task_metrics: Dict[str, float]):
    """Create fitness function based on agent task performance metrics"""
    def fitness(genome: AgentGenome) -> float:
        # This would integrate with the agent dispatch system
        # For now, return a placeholder based on genome properties
        base_score = sum(abs(w) for w in genome.weights)  # Encourage diverse weights

        # Factor in task metrics (would be calculated from actual task execution)
        task_completion = task_metrics.get("completion_rate", 0.5)
        efficiency = task_metrics.get("efficiency", 0.5)

        return base_score * (task_completion + efficiency) / 2

    return fitness


def multi_objective_fitness(weights: List[float]):
    """Create multi-objective fitness function"""
    def fitness(genome: AgentGenome) -> float:
        if len(genome.weights) != len(weights):
            return float('-inf')

        # Weighted sum of multiple objectives
        objectives = [
            sum(genome.weights),  # Objective 1: sum
            sum(w ** 2 for w in genome.weights),  # Objective 2: quadratic
            max(genome.weights) - min(genome.weights),  # Objective 3: range
        ]

        return sum(w * obj for w, obj in zip(weights, objectives))

    return fitness


class TaskBasedFitnessEvaluator:
    """Evaluates fitness by running agents on actual tasks"""

    def __init__(self):
        self.task_results: Dict[str, Dict[str, Any]] = {}

    async def evaluate_on_task(self, genome: AgentGenome, task_definition: Dict[str, Any]) -> FitnessResult:
        """Evaluate genome by dispatching it to perform a task"""
        start_time = time.time()

        try:
            # This would integrate with the agent dispatch system
            # For now, simulate task execution based on genome

            # Simulate task execution time based on genome complexity
            execution_time = abs(sum(genome.weights)) * 0.1 + 0.5

            # Simulate success rate based on genome "quality"
            quality_score = sum(1 for w in genome.weights if -0.5 <= w <= 0.5) / len(genome.weights)
            success_rate = min(1.0, quality_score + 0.3)

            # Calculate fitness based on simulated performance
            fitness_score = success_rate * (1.0 / execution_time) * 100

            metrics = {
                "execution_time": execution_time,
                "success_rate": success_rate,
                "quality_score": quality_score,
                "task_type": task_definition.get("type", "unknown")
            }

            result = FitnessResult(
                score=fitness_score,
                metrics=metrics,
                duration=time.time() - start_time,
                success=True
            )

        except Exception as e:
            result = FitnessResult(
                score=float('-inf'),
                metrics={},
                duration=time.time() - start_time,
                success=False,
                error_message=str(e)
            )

        return result

    def get_task_statistics(self) -> Dict[str, Any]:
        """Get statistics about task evaluations"""
        if not self.task_results:
            return {}

        scores = [r["score"] for r in self.task_results.values()]
        return {
            "total_evaluations": len(self.task_results),
            "avg_score": sum(scores) / len(scores),
            "max_score": max(scores),
            "min_score": min(scores)
        }


# Benchmark fitness functions for testing evolution algorithms

def sphere_fitness(genome: AgentGenome) -> float:
    """Sphere function: f(x) = sum(x_i^2), minimum at x_i = 0"""
    return -sum(w ** 2 for w in genome.weights)  # Negative for maximization


def rastrigin_fitness(genome: AgentGenome) -> float:
    """Rastrigin function: multimodal optimization benchmark"""
    A = 10
    n = len(genome.weights)
    return -(A * n + sum(w ** 2 - A * (2 * 3.14159 * w) ** 2 for w in genome.weights))


def rosenbrock_fitness(genome: AgentGenome) -> float:
    """Rosenbrock function: classic optimization benchmark"""
    if len(genome.weights) < 2:
        return -float('inf')

    score = 0
    for i in range(len(genome.weights) - 1):
        x_i = genome.weights[i]
        x_next = genome.weights[i + 1]
        score += 100 * (x_next - x_i ** 2) ** 2 + (1 - x_i) ** 2

    return -score  # Negative for maximization


# Registry of available fitness functions
FITNESS_FUNCTIONS = {
    "simple_sum": simple_weighted_sum_fitness,
    "quadratic": quadratic_fitness,
    "sphere": sphere_fitness,
    "rastrigin": rastrigin_fitness,
    "rosenbrock": rosenbrock_fitness,
}


def get_fitness_function(name: str) -> Optional[Callable[[AgentGenome], float]]:
    """Get fitness function by name"""
    return FITNESS_FUNCTIONS.get(name)