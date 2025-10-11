#!/usr/bin/env python3
"""
Training Script for Agent Evolution
Runs one complete evolution cycle with configurable parameters.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Optional

from .genome import AgentGenome
from .evolution import EvolutionaryAlgorithm, EvolutionConfig
from .fitness import get_fitness_function, FitnessEvaluator


def run_evolution_cycle(
    population_size: int = 50,
    num_weights: int = 10,
    fitness_function_name: str = "sphere",
    generations: int = 10,
    mutation_rate: float = 0.05,
    crossover_rate: float = 0.8,
    elite_size: int = 5,
    output_file: Optional[str] = None,
    verbose: bool = True
) -> dict:
    """
    Run a single evolution cycle and return results.

    Args:
        population_size: Number of genomes in population
        num_weights: Number of weights per genome
        fitness_function_name: Name of fitness function to use
        generations: Number of generations to evolve
        mutation_rate: Probability of mutation per gene
        crossover_rate: Probability of crossover
        elite_size: Number of elite individuals to preserve
        output_file: Optional file to save results
        verbose: Whether to print progress

    Returns:
        Dictionary containing evolution results
    """
    if verbose:
        print(f"🚀 Starting evolution cycle:")
        print(f"   Population: {population_size}")
        print(f"   Weights per genome: {num_weights}")
        print(f"   Fitness function: {fitness_function_name}")
        print(f"   Generations: {generations}")
        print("-" * 50)

    # Get fitness function
    fitness_function = get_fitness_function(fitness_function_name)
    if not fitness_function:
        raise ValueError(f"Unknown fitness function: {fitness_function_name}")

    # Configure evolution
    config = EvolutionConfig(
        population_size=population_size,
        elite_size=elite_size,
        mutation_rate=mutation_rate,
        crossover_rate=crossover_rate,
        max_generations=generations
    )

    # Create evolutionary algorithm
    ea = EvolutionaryAlgorithm(config)

    # Initialize population
    def genome_factory():
        return AgentGenome.random(num_weights, mutation_rate)

    ea.initialize_population(genome_factory)

    # Track timing
    start_time = time.time()

    # Evolution loop
    generation = 0
    while ea.evolve_generation(fitness_function):
        generation += 1
        if verbose and generation % max(1, generations // 10) == 0:
            stats = ea.get_population_stats()
            print(f"Generation {generation}: Best={stats['best_fitness']:.4f}, Avg={stats['avg_fitness']:.4f}")

    total_time = time.time() - start_time

    # Get final results
    final_stats = ea.get_population_stats()
    best_genome = ea.get_best_genome()

    results = {
        "config": {
            "population_size": population_size,
            "num_weights": num_weights,
            "fitness_function": fitness_function_name,
            "generations": generations,
            "mutation_rate": mutation_rate,
            "crossover_rate": crossover_rate,
            "elite_size": elite_size
        },
        "final_stats": final_stats,
        "best_genome": best_genome.to_dict(),
        "evolution_history": {
            "best_fitness": ea.best_fitness_history,
            "avg_fitness": ea.avg_fitness_history
        },
        "timing": {
            "total_seconds": total_time,
            "seconds_per_generation": total_time / generations
        }
    }

    if verbose:
        print("-" * 50)
        print("✅ Evolution cycle completed!")
        print(f"   Best fitness: {final_stats['best_fitness']:.4f}")
        print(f"   Average fitness: {final_stats['avg_fitness']:.4f}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Generations per second: {generations/total_time:.2f}")

    # Save results if requested
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        if verbose:
            print(f"💾 Results saved to: {output_path}")

    return results


def main():
    """Command-line interface for training script."""
    parser = argparse.ArgumentParser(description="Run agent evolution training cycle")
    parser.add_argument("--population", "-p", type=int, default=50,
                       help="Population size (default: 50)")
    parser.add_argument("--weights", "-w", type=int, default=10,
                       help="Number of weights per genome (default: 10)")
    parser.add_argument("--fitness", "-f", type=str, default="sphere",
                       choices=["sphere", "rastrigin", "rosenbrock", "simple_sum", "quadratic"],
                       help="Fitness function to use (default: sphere)")
    parser.add_argument("--generations", "-g", type=int, default=10,
                       help="Number of generations (default: 10)")
    parser.add_argument("--mutation", "-m", type=float, default=0.05,
                       help="Mutation rate (default: 0.05)")
    parser.add_argument("--crossover", "-c", type=float, default=0.8,
                       help="Crossover rate (default: 0.8)")
    parser.add_argument("--elite", "-e", type=int, default=5,
                       help="Elite size (default: 5)")
    parser.add_argument("--output", "-o", type=str,
                       help="Output file for results (JSON)")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Suppress progress output")

    args = parser.parse_args()

    try:
        results = run_evolution_cycle(
            population_size=args.population,
            num_weights=args.weights,
            fitness_function_name=args.fitness,
            generations=args.generations,
            mutation_rate=args.mutation,
            crossover_rate=args.crossover,
            elite_size=args.elite,
            output_file=args.output,
            verbose=not args.quiet
        )

        # Exit with success
        exit(0)

    except Exception as e:
        print(f"❌ Error during evolution: {e}")
        exit(1)


if __name__ == "__main__":
    main()