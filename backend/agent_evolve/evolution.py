"""
Evolutionary Algorithms for Agent Evolution
Implements genetic algorithms, selection, and population management.
"""

import random
import heapq
from typing import List, Callable, Optional, Tuple
from dataclasses import dataclass
from .genome import AgentGenome


@dataclass
class EvolutionConfig:
    """Configuration for evolutionary algorithms"""
    population_size: int = 50
    elite_size: int = 5
    tournament_size: int = 3
    mutation_rate: float = 0.05
    crossover_rate: float = 0.8
    max_generations: int = 100
    fitness_threshold: Optional[float] = None


class EvolutionaryAlgorithm:
    """Genetic algorithm for evolving agent genomes"""

    def __init__(self, config: EvolutionConfig):
        self.config = config
        self.population: List[AgentGenome] = []
        self.generation = 0
        self.best_fitness_history: List[float] = []
        self.avg_fitness_history: List[float] = []

    def initialize_population(self, genome_factory: Callable[[], AgentGenome]):
        """Initialize population with random genomes"""
        self.population = [genome_factory() for _ in range(self.config.population_size)]
        self.generation = 0

    def evaluate_population(self, fitness_function: Callable[[AgentGenome], float]):
        """Evaluate fitness of all genomes in population"""
        for genome in self.population:
            genome.fitness_score = fitness_function(genome)

    def select_parents_tournament(self) -> List[AgentGenome]:
        """Tournament selection for parent selection"""
        parents = []
        for _ in range(self.config.population_size - self.config.elite_size):
            # Select tournament participants
            tournament = random.sample(self.population, self.config.tournament_size)
            # Select winner (highest fitness)
            winner = max(tournament, key=lambda g: g.fitness_score)
            parents.append(winner)
        return parents

    def select_elites(self) -> List[AgentGenome]:
        """Select elite individuals that survive to next generation"""
        # Sort by fitness (descending)
        sorted_population = sorted(self.population, key=lambda g: g.fitness_score, reverse=True)
        return sorted_population[:self.config.elite_size]

    def crossover_population(self, parents: List[AgentGenome]) -> List[AgentGenome]:
        """Create offspring through crossover"""
        offspring = []

        # Shuffle parents for random pairing
        random.shuffle(parents)

        # Create pairs and perform crossover
        for i in range(0, len(parents) - 1, 2):
            parent1 = parents[i]
            parent2 = parents[i + 1]

            if random.random() < self.config.crossover_rate:
                child1, child2 = parent1.crossover(parent2)
                offspring.extend([child1, child2])
            else:
                # No crossover, copy parents
                offspring.extend([parent1.copy(), parent2.copy()])

        # If odd number, add last parent
        if len(parents) % 2 == 1:
            offspring.append(parents[-1].copy())

        return offspring

    def mutate_population(self, population: List[AgentGenome]) -> List[AgentGenome]:
        """Apply mutation to population"""
        mutated = []
        for genome in population:
            if random.random() < self.config.mutation_rate:
                mutated_genome = genome.mutate()
                mutated.append(mutated_genome)
            else:
                mutated.append(genome)
        return mutated

    def evolve_generation(self, fitness_function: Callable[[AgentGenome], float]) -> bool:
        """Evolve one generation. Returns True if evolution should continue."""
        # Evaluate current population
        self.evaluate_population(fitness_function)

        # Track statistics
        fitness_scores = [g.fitness_score for g in self.population]
        self.best_fitness_history.append(max(fitness_scores))
        self.avg_fitness_history.append(sum(fitness_scores) / len(fitness_scores))

        # Check termination conditions
        if self.config.fitness_threshold and max(fitness_scores) >= self.config.fitness_threshold:
            return False  # Stop evolution

        if self.generation >= self.config.max_generations:
            return False  # Stop evolution

        # Select elites
        elites = self.select_elites()

        # Select parents for reproduction
        parents = self.select_parents_tournament()

        # Create offspring
        offspring = self.crossover_population(parents)

        # Apply mutation
        offspring = self.mutate_population(offspring)

        # Create new population: elites + offspring
        self.population = elites + offspring[:self.config.population_size - self.config.elite_size]

        self.generation += 1
        return True  # Continue evolution

    def get_best_genome(self) -> AgentGenome:
        """Get the best genome in current population"""
        return max(self.population, key=lambda g: g.fitness_score)

    def get_population_stats(self) -> dict:
        """Get statistics about current population"""
        if not self.population:
            return {}

        fitness_scores = [g.fitness_score for g in self.population]
        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "best_fitness": max(fitness_scores),
            "avg_fitness": sum(fitness_scores) / len(fitness_scores),
            "worst_fitness": min(fitness_scores),
            "fitness_std": (sum((x - sum(fitness_scores)/len(fitness_scores))**2 for x in fitness_scores) / len(fitness_scores))**0.5
        }


class NoveltySearch:
    """Novelty search algorithm for exploring behavioral diversity"""

    def __init__(self, config: EvolutionConfig, novelty_metric: Callable[[AgentGenome, List[AgentGenome]], float]):
        self.config = config
        self.novelty_metric = novelty_metric
        self.archive: List[AgentGenome] = []
        self.population: List[AgentGenome] = []
        self.generation = 0

    def initialize_population(self, genome_factory: Callable[[], AgentGenome]):
        """Initialize population"""
        self.population = [genome_factory() for _ in range(self.config.population_size)]

    def calculate_novelty(self, genome: AgentGenome, k: int = 15) -> float:
        """Calculate novelty score for a genome"""
        # Get k nearest neighbors from population and archive
        neighbors = self.population + self.archive
        if genome in neighbors:
            neighbors.remove(genome)

        # Calculate distances to all neighbors
        distances = [(self.novelty_metric(genome, neighbor), neighbor) for neighbor in neighbors]

        # Get k smallest distances
        smallest_distances = heapq.nsmallest(k, distances, key=lambda x: x[0])

        # Novelty is average of k smallest distances
        if smallest_distances:
            return sum(d[0] for d in smallest_distances) / len(smallest_distances)
        else:
            return 0.0

    def update_archive(self, threshold: float = 0.5):
        """Update novelty archive with novel individuals"""
        for genome in self.population:
            novelty = self.calculate_novelty(genome)
            if novelty > threshold and genome not in self.archive:
                self.archive.append(genome)

    def evolve_generation(self, fitness_function: Optional[Callable[[AgentGenome], float]] = None) -> bool:
        """Evolve one generation using novelty search"""
        # Calculate novelty scores
        for genome in self.population:
            genome.fitness_score = self.calculate_novelty(genome)

        # Update archive
        self.update_archive()

        # Selection and reproduction (similar to genetic algorithm but using novelty)
        elites = sorted(self.population, key=lambda g: g.fitness_score, reverse=True)[:self.config.elite_size]

        # Create offspring through mutation only (novelty search often uses mutation)
        offspring = []
        for _ in range(self.config.population_size - self.config.elite_size):
            parent = random.choice(self.population)
            child = parent.mutate()
            offspring.append(child)

        self.population = elites + offspring
        self.generation += 1

        return self.generation < self.config.max_generations


# Utility functions for common evolutionary operations

def roulette_wheel_selection(population: List[AgentGenome], num_selections: int) -> List[AgentGenome]:
    """Roulette wheel selection based on fitness"""
    if not population:
        return []

    # Ensure all fitness scores are non-negative
    min_fitness = min(g.fitness_score for g in population)
    if min_fitness < 0:
        for g in population:
            g.fitness_score -= min_fitness

    total_fitness = sum(g.fitness_score for g in population)
    if total_fitness == 0:
        return random.sample(population, min(num_selections, len(population)))

    selections = []
    for _ in range(num_selections):
        pick = random.uniform(0, total_fitness)
        current_sum = 0
        for genome in population:
            current_sum += genome.fitness_score
            if current_sum >= pick:
                selections.append(genome)
                break

    return selections


def rank_selection(population: List[AgentGenome], num_selections: int) -> List[AgentGenome]:
    """Rank-based selection"""
    if not population:
        return []

    # Sort by fitness
    sorted_pop = sorted(population, key=lambda g: g.fitness_score, reverse=True)

    # Assign ranks (higher fitness = higher rank)
    ranks = list(range(1, len(sorted_pop) + 1))

    # Selection probability proportional to rank
    total_rank = sum(ranks)
    selections = []

    for _ in range(num_selections):
        pick = random.uniform(0, total_rank)
        current_sum = 0
        for i, genome in enumerate(sorted_pop):
            current_sum += ranks[i]
            if current_sum >= pick:
                selections.append(genome)
                break

    return selections