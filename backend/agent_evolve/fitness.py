#!/usr/bin/env python3
"""
Performance Measurement Definitions for Agent Evolution
Defines how agent performance is measured and evaluated.
"""

from typing import Dict, Any, List, Callable
from .genome import AgentGenome


def task_completion_rate(genome: AgentGenome, task_results: List[Dict[str, Any]]) -> float:
    """
    Measure task completion performance.

    Args:
        genome: The agent genome being evaluated
        task_results: List of task execution results

    Returns:
        Completion rate (0.0 to 1.0)
    """
    if not task_results:
        return 0.0

    completed_tasks = sum(1 for result in task_results if result.get("success", False))
    return completed_tasks / len(task_results)


def execution_efficiency(genome: AgentGenome, task_results: List[Dict[str, Any]]) -> float:
    """
    Measure execution efficiency (speed vs quality tradeoff).

    Args:
        genome: The agent genome being evaluated
        task_results: List of task execution results

    Returns:
        Efficiency score (higher is better)
    """
    if not task_results:
        return 0.0

    total_score = 0.0
    for result in task_results:
        execution_time = result.get("execution_time", 1.0)
        success = result.get("success", False)
        quality = result.get("quality_score", 0.5)

        # Efficiency = quality / time (with minimum time to avoid division by zero)
        time_penalty = max(execution_time, 0.1)
        efficiency = (quality / time_penalty) if success else 0.0
        total_score += efficiency

    return total_score / len(task_results)


def resource_utilization(genome: AgentGenome, metrics: Dict[str, Any]) -> float:
    """
    Measure resource utilization efficiency.

    Args:
        genome: The agent genome being evaluated
        metrics: System resource metrics

    Returns:
        Resource efficiency score (0.0 to 1.0, higher is better)
    """
    cpu_usage = metrics.get("cpu_percent", 50.0) / 100.0
    memory_usage = metrics.get("memory_percent", 50.0) / 100.0
    network_usage = metrics.get("network_utilization", 0.5)

    # Lower resource usage is better (more efficient)
    # Convert to efficiency score where 1.0 = optimal resource usage
    efficiency = 1.0 - (cpu_usage * 0.4 + memory_usage * 0.4 + network_usage * 0.2)
    return max(0.0, min(1.0, efficiency))


def learning_adaptability(genome: AgentGenome, evolution_history: List[Dict[str, Any]]) -> float:
    """
    Measure how well the agent adapts and improves over generations.

    Args:
        genome: The agent genome being evaluated
        evolution_history: History of fitness scores across generations

    Returns:
        Adaptability score (0.0 to 1.0)
    """
    if len(evolution_history) < 2:
        return 0.5  # Neutral score for insufficient history

    fitness_scores = [gen.get("fitness_score", 0) for gen in evolution_history]

    # Calculate improvement trend
    improvements = []
    for i in range(1, len(fitness_scores)):
        improvement = fitness_scores[i] - fitness_scores[i-1]
        improvements.append(improvement)

    # Positive improvements indicate learning
    positive_improvements = sum(1 for imp in improvements if imp > 0)
    adaptability = positive_improvements / len(improvements) if improvements else 0.5

    return adaptability


def behavioral_diversity(genome: AgentGenome, population: List[AgentGenome]) -> float:
    """
    Measure behavioral diversity compared to population.

    Args:
        genome: The agent genome being evaluated
        population: Other genomes in the population

    Returns:
        Diversity score (0.0 to 1.0, higher = more diverse)
    """
    if not population:
        return 0.5

    distances = [genome.distance(other) for other in population if other != genome]

    if not distances:
        return 0.5

    avg_distance = sum(distances) / len(distances)

    # Normalize to 0-1 scale (assuming max reasonable distance is 10)
    diversity = min(1.0, avg_distance / 10.0)
    return diversity


def robustness_score(genome: AgentGenome, stress_test_results: List[Dict[str, Any]]) -> float:
    """
    Measure agent robustness under stress conditions.

    Args:
        genome: The agent genome being evaluated
        stress_test_results: Results from stress testing scenarios

    Returns:
        Robustness score (0.0 to 1.0)
    """
    if not stress_test_results:
        return 0.5

    total_tests = len(stress_test_results)
    passed_tests = sum(1 for result in stress_test_results if result.get("passed", False))

    # Bonus for handling extreme conditions
    extreme_conditions = [r for r in stress_test_results if r.get("extreme_condition", False)]
    extreme_passed = sum(1 for r in extreme_conditions if r.get("passed", False))

    base_score = passed_tests / total_tests if total_tests > 0 else 0.0
    extreme_bonus = (extreme_passed / len(extreme_conditions)) * 0.2 if extreme_conditions else 0.0

    return min(1.0, base_score + extreme_bonus)


def cooperation_index(genome: AgentGenome, interaction_history: List[Dict[str, Any]]) -> float:
    """
    Measure cooperative behavior in multi-agent scenarios.

    Args:
        genome: The agent genome being evaluated
        interaction_history: History of interactions with other agents

    Returns:
        Cooperation score (0.0 to 1.0)
    """
    if not interaction_history:
        return 0.5

    cooperative_actions = sum(1 for interaction in interaction_history
                            if interaction.get("cooperative", False))
    total_interactions = len(interaction_history)

    cooperation_rate = cooperative_actions / total_interactions

    # Factor in mutual benefit
    mutual_benefits = sum(1 for interaction in interaction_history
                         if interaction.get("mutual_benefit", False))
    mutual_bonus = (mutual_benefits / total_interactions) * 0.3

    return min(1.0, cooperation_rate + mutual_bonus)


# Registry of performance measures
PERFORMANCE_MEASURES = {
    "task_completion": task_completion_rate,
    "execution_efficiency": execution_efficiency,
    "resource_utilization": resource_utilization,
    "learning_adaptability": learning_adaptability,
    "behavioral_diversity": behavioral_diversity,
    "robustness": robustness_score,
    "cooperation": cooperation_index,
}


def get_performance_measure(name: str) -> Callable:
    """
    Get a performance measurement function by name.

    Args:
        name: Name of the performance measure

    Returns:
        Performance measurement function

    Raises:
        ValueError: If performance measure not found
    """
    if name not in PERFORMANCE_MEASURES:
        available = list(PERFORMANCE_MEASURES.keys())
        raise ValueError(f"Unknown performance measure: {name}. Available: {available}")

    return PERFORMANCE_MEASURES[name]


def composite_fitness_score(
    genome: AgentGenome,
    measures: Dict[str, float],
    weights: Dict[str, float]
) -> float:
    """
    Calculate composite fitness score from multiple performance measures.

    Args:
        genome: The agent genome being evaluated
        measures: Dictionary of measure_name -> measure_value
        weights: Dictionary of measure_name -> weight

    Returns:
        Weighted composite fitness score
    """
    total_score = 0.0
    total_weight = 0.0

    for measure_name, weight in weights.items():
        if measure_name in measures:
            total_score += measures[measure_name] * weight
            total_weight += weight

    return total_score / total_weight if total_weight > 0 else 0.0


# Example fitness function combining multiple measures
def comprehensive_agent_fitness(
    genome: AgentGenome,
    task_results: List[Dict[str, Any]] = None,
    metrics: Dict[str, Any] = None,
    evolution_history: List[Dict[str, Any]] = None,
    population: List[AgentGenome] = None,
    stress_results: List[Dict[str, Any]] = None,
    interactions: List[Dict[str, Any]] = None
) -> float:
    """
    Comprehensive fitness function combining multiple performance aspects.

    Args:
        genome: Agent genome to evaluate
        task_results: Task execution results
        metrics: System resource metrics
        evolution_history: Evolution history for adaptability
        population: Population for diversity calculation
        stress_results: Stress test results
        interactions: Multi-agent interaction history

    Returns:
        Comprehensive fitness score
    """
    measures = {}
    weights = {}

    # Task performance (most important)
    if task_results:
        measures["task_completion"] = task_completion_rate(genome, task_results)
        measures["execution_efficiency"] = execution_efficiency(genome, task_results)
        weights["task_completion"] = 0.4
        weights["execution_efficiency"] = 0.3

    # Resource efficiency
    if metrics:
        measures["resource_utilization"] = resource_utilization(genome, metrics)
        weights["resource_utilization"] = 0.1

    # Learning and adaptation
    if evolution_history:
        measures["learning_adaptability"] = learning_adaptability(genome, evolution_history)
        weights["learning_adaptability"] = 0.1

    # Diversity and robustness
    if population:
        measures["behavioral_diversity"] = behavioral_diversity(genome, population)
        weights["behavioral_diversity"] = 0.05

    if stress_results:
        measures["robustness"] = robustness_score(genome, stress_results)
        weights["robustness"] = 0.05

    # Cooperation (if applicable)
    if interactions:
        measures["cooperation"] = cooperation_index(genome, interactions)
        weights["cooperation"] = 0.1

    return composite_fitness_score(genome, measures, weights)