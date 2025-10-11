#!/usr/bin/env python3
"""
Evolution Script for Agent Evolution
Handles mutation and selection loop for evolving agent populations.
"""

import argparse
import json
import random
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
import asyncio

from .genome import AgentGenome
from .evolution import EvolutionaryAlgorithm, EvolutionConfig, NoveltySearch
from .fitness import get_performance_measure, comprehensive_agent_fitness


class EvolutionManager:
    """Manages the evolution process with persistence and monitoring."""

    def __init__(self, population_file: Optional[str] = None):
        self.population: List[AgentGenome] = []
        self.generation = 0
        self.population_file = population_file or "population.json"
        self.stats_history: List[Dict[str, Any]] = []

        # Load existing population if available
        self.load_population()

    def initialize_population(self, size: int, num_weights: int, mutation_rate: float = 0.05):
        """Initialize a new random population."""
        self.population = [
            AgentGenome.random(num_weights, mutation_rate)
            for _ in range(size)
        ]
        self.generation = 0
        print(f"🧬 Initialized population of {size} genomes with {num_weights} weights each")

    def load_population(self):
        """Load population from file if it exists."""
        if Path(self.population_file).exists():
            try:
                with open(self.population_file, 'r') as f:
                    data = json.load(f)

                self.population = [AgentGenome.from_dict(g) for g in data.get("population", [])]
                self.generation = data.get("generation", 0)
                self.stats_history = data.get("stats_history", [])

                print(f"📁 Loaded population of {len(self.population)} genomes (generation {self.generation})")

            except Exception as e:
                print(f"⚠️  Failed to load population: {e}")
                self.population = []
                self.generation = 0
        else:
            print("📁 No existing population found, starting fresh")

    def save_population(self):
        """Save current population to file."""
        data = {
            "population": [g.to_dict() for g in self.population],
            "generation": self.generation,
            "stats_history": self.stats_history,
            "timestamp": time.time()
        }

        Path(self.population_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.population_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        print(f"💾 Saved population (generation {self.generation}) to {self.population_file}")

    def evaluate_population(self, fitness_function_name: str = "sphere",
                          task_results: List[Dict[str, Any]] = None,
                          metrics: Dict[str, Any] = None) -> Dict[str, Any]:
        """Evaluate entire population fitness."""
        if fitness_function_name == "comprehensive":
            # Use comprehensive fitness evaluation
            for genome in self.population:
                genome.fitness_score = comprehensive_agent_fitness(
                    genome=genome,
                    task_results=task_results,
                    metrics=metrics,
                    evolution_history=self.stats_history[-10:] if self.stats_history else None,
                    population=self.population
                )
        else:
            # Use simple fitness function
            fitness_func = get_performance_measure(fitness_function_name)
            for genome in self.population:
                genome.fitness_score = fitness_func(genome, task_results or [])

        # Calculate statistics
        fitness_scores = [g.fitness_score for g in self.population]
        stats = {
            "generation": self.generation,
            "population_size": len(self.population),
            "best_fitness": max(fitness_scores),
            "avg_fitness": sum(fitness_scores) / len(fitness_scores),
            "worst_fitness": min(fitness_scores),
            "fitness_std": (sum((x - sum(fitness_scores)/len(fitness_scores))**2
                              for x in fitness_scores) / len(fitness_scores))**0.5,
            "evaluation_time": time.time()
        }

        self.stats_history.append(stats)
        return stats

    def select_elites(self, elite_size: int) -> List[AgentGenome]:
        """Select elite individuals."""
        return sorted(self.population, key=lambda g: g.fitness_score, reverse=True)[:elite_size]

    def tournament_selection(self, tournament_size: int, num_selections: int) -> List[AgentGenome]:
        """Perform tournament selection."""
        selections = []
        for _ in range(num_selections):
            # Select random tournament participants
            tournament = random.sample(self.population, min(tournament_size, len(self.population)))
            # Winner is the one with highest fitness
            winner = max(tournament, key=lambda g: g.fitness_score)
            selections.append(winner)
        return selections

    def mutate_population(self, population: List[AgentGenome], mutation_rate: float) -> List[AgentGenome]:
        """Apply mutation to a population."""
        mutated = []
        for genome in population:
            if random.random() < mutation_rate:
                mutated_genome = genome.mutate()
                mutated.append(mutated_genome)
            else:
                mutated.append(genome.copy())
        return mutated

    def evolve_generation(self, config: EvolutionConfig, fitness_function_name: str = "sphere",
                         task_results: List[Dict[str, Any]] = None,
                         metrics: Dict[str, Any] = None) -> bool:
        """Evolve one generation. Returns True if evolution should continue."""

        # Evaluate current population
        stats = self.evaluate_population(fitness_function_name, task_results, metrics)

        print(f"📊 Generation {self.generation}: Best={stats['best_fitness']:.4f}, "
              f"Avg={stats['avg_fitness']:.4f}, Std={stats['fitness_std']:.4f}")

        # Check termination conditions
        if config.fitness_threshold and stats['best_fitness'] >= config.fitness_threshold:
            print(f"🎯 Fitness threshold reached: {stats['best_fitness']:.4f} >= {config.fitness_threshold}")
            return False

        if self.generation >= config.max_generations:
            print(f"🏁 Maximum generations reached: {self.generation}")
            return False

        # Selection and reproduction
        elites = self.select_elites(config.elite_size)
        parents = self.tournament_selection(config.tournament_size,
                                          config.population_size - config.elite_size)

        # Crossover
        offspring = []
        for i in range(0, len(parents) - 1, 2):
            parent1 = parents[i]
            parent2 = parents[i + 1]

            if random.random() < config.crossover_rate:
                child1, child2 = parent1.crossover(parent2)
                offspring.extend([child1, child2])
            else:
                offspring.extend([parent1.copy(), parent2.copy()])

        # Handle odd number of parents
        if len(parents) % 2 == 1:
            offspring.append(parents[-1].copy())

        # Mutation
        offspring = self.mutate_population(offspring, config.mutation_rate)

        # Create new population
        self.population = elites + offspring[:config.population_size - config.elite_size]
        self.generation += 1

        # Auto-save every 10 generations
        if self.generation % 10 == 0:
            self.save_population()

        return True

    def get_best_genome(self) -> AgentGenome:
        """Get the best genome in current population."""
        return max(self.population, key=lambda g: g.fitness_score)

    def get_population_diversity(self) -> float:
        """Calculate population diversity."""
        if len(self.population) < 2:
            return 0.0

        distances = []
        for i, g1 in enumerate(self.population):
            for g2 in self.population[i+1:]:
                distances.append(g1.distance(g2))

        return sum(distances) / len(distances) if distances else 0.0


def run_evolution_loop(
    population_size: int = 50,
    num_weights: int = 10,
    generations: int = 100,
    fitness_function: str = "sphere",
    mutation_rate: float = 0.05,
    crossover_rate: float = 0.8,
    elite_size: int = 5,
    tournament_size: int = 3,
    fitness_threshold: Optional[float] = None,
    population_file: str = "population.json",
    save_interval: int = 10,
    verbose: bool = True
):
    """Run the main evolution loop."""

    print("🚀 Starting Agent Evolution Loop")
    print(f"   Population: {population_size}")
    print(f"   Generations: {generations}")
    print(f"   Fitness: {fitness_function}")
    print("-" * 50)

    # Initialize evolution manager
    manager = EvolutionManager(population_file)

    # Initialize population if empty
    if not manager.population:
        manager.initialize_population(population_size, num_weights, mutation_rate)

    # Configure evolution
    config = EvolutionConfig(
        population_size=population_size,
        elite_size=elite_size,
        tournament_size=tournament_size,
        mutation_rate=mutation_rate,
        crossover_rate=crossover_rate,
        max_generations=generations,
        fitness_threshold=fitness_threshold
    )

    start_time = time.time()

    try:
        while manager.evolve_generation(config, fitness_function):
            # Optional: Add custom evaluation data here
            task_results = None  # Could load from agent dispatch system
            metrics = None       # Could load from monitoring system

            if manager.generation % save_interval == 0:
                manager.save_population()

        # Final save
        manager.save_population()

        total_time = time.time() - start_time
        best_genome = manager.get_best_genome()

        print("-" * 50)
        print("✅ Evolution completed!")
        print(f"   Final generation: {manager.generation}")
        print(f"   Best fitness: {best_genome.fitness_score:.4f}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Generations per second: {manager.generation/total_time:.2f}")

        return {
            "success": True,
            "final_generation": manager.generation,
            "best_genome": best_genome.to_dict(),
            "total_time": total_time,
            "population_diversity": manager.get_population_diversity()
        }

    except KeyboardInterrupt:
        print("\n⏹️  Evolution interrupted by user")
        manager.save_population()
        return {"success": False, "reason": "interrupted", "final_generation": manager.generation}

    except Exception as e:
        print(f"\n❌ Evolution failed: {e}")
        manager.save_population()
        return {"success": False, "reason": str(e), "final_generation": manager.generation}


def main():
    """Command-line interface for evolution script."""
    parser = argparse.ArgumentParser(description="Run agent evolution with mutation and selection")
    parser.add_argument("--population", "-p", type=int, default=50,
                       help="Population size (default: 50)")
    parser.add_argument("--weights", "-w", type=int, default=10,
                       help="Number of weights per genome (default: 10)")
    parser.add_argument("--generations", "-g", type=int, default=100,
                       help="Maximum generations (default: 100)")
    parser.add_argument("--fitness", "-f", type=str, default="sphere",
                       choices=["sphere", "rastrigin", "rosenbrock", "task_completion",
                               "execution_efficiency", "comprehensive"],
                       help="Fitness function (default: sphere)")
    parser.add_argument("--mutation", "-m", type=float, default=0.05,
                       help="Mutation rate (default: 0.05)")
    parser.add_argument("--crossover", "-c", type=float, default=0.8,
                       help="Crossover rate (default: 0.8)")
    parser.add_argument("--elite", "-e", type=int, default=5,
                       help="Elite size (default: 5)")
    parser.add_argument("--tournament", "-t", type=int, default=3,
                       help="Tournament size (default: 3)")
    parser.add_argument("--threshold", type=float,
                       help="Fitness threshold to stop evolution")
    parser.add_argument("--population-file", default="population.json",
                       help="Population save file (default: population.json)")
    parser.add_argument("--save-interval", type=int, default=10,
                       help="Save population every N generations (default: 10)")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Suppress progress output")

    args = parser.parse_args()

    try:
        result = run_evolution_loop(
            population_size=args.population,
            num_weights=args.weights,
            generations=args.generations,
            fitness_function=args.fitness,
            mutation_rate=args.mutation,
            crossover_rate=args.crossover,
            elite_size=args.elite,
            tournament_size=args.tournament,
            fitness_threshold=args.threshold,
            population_file=args.population_file,
            save_interval=args.save_interval,
            verbose=not args.quiet
        )

        if result["success"]:
            print("🎉 Evolution completed successfully!")
        else:
            print(f"⚠️  Evolution ended: {result.get('reason', 'unknown')}")

        exit(0 if result["success"] else 1)

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()