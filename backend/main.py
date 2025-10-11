from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import time
import uuid
from prometheus_fastapi_instrumentator import Instrumentator

# Import federation bridge
try:
    from bridge import (
        register_peer,
        broadcast_heartbeat,
        sync_summary,
        get_peer_list,
        initialize_federation,
        shutdown_federation
    )
    federation_available = True
except ImportError:
    federation_available = False
    print("Warning: Federation bridge not available")

# Import agent evolution engine
try:
    from backend.agent_evolve import (
        AgentGenome,
        EvolutionaryAlgorithm,
        EvolutionConfig,
        FitnessEvaluator,
        get_fitness_function
    )
    evolution_available = True
except ImportError:
    evolution_available = False
    print("Warning: Agent evolution engine not available")

app = FastAPI(title="Brain-Swarm API", version="0.2.0")

# Agent registry
agent_registry: Dict[str, Dict[str, Any]] = {}

# Task queue (in-memory for now)
task_queue: List[Dict[str, Any]] = []

class AgentRegistration(BaseModel):
    name: str
    capabilities: List[str]
    metadata: Optional[Dict[str, Any]] = {}

class TaskDispatch(BaseModel):
    agent_type: str
    task: str
    parameters: Optional[Dict[str, Any]] = {}
    priority: Optional[int] = 1

class TaskResult(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None

@app.get("/ping")
def ping():
    return {"redis": True, "duckdb_path": "/data/cortex.duckdb", "agents_registered": len(agent_registry)}

@app.post("/agent/register")
def register_agent(registration: AgentRegistration):
    """Register an agent with the swarm"""
    agent_id = str(uuid.uuid4())
    agent_registry[agent_id] = {
        "id": agent_id,
        "name": registration.name,
        "capabilities": registration.capabilities,
        "metadata": registration.metadata,
        "registered_at": time.time(),
        "status": "active"
    }
    return {"agent_id": agent_id, "status": "registered"}

@app.get("/agent/list")
def list_agents():
    """List all registered agents"""
    return {"agents": list(agent_registry.values())}

@app.post("/agent/dispatch")
def dispatch_task(dispatch: TaskDispatch):
    """Dispatch a task to an available agent"""
    # Find available agent with matching capabilities
    available_agents = [
        agent for agent in agent_registry.values()
        if agent["status"] == "active" and dispatch.agent_type in agent["capabilities"]
    ]

    if not available_agents:
        raise HTTPException(status_code=404, detail="No available agents for this task type")

    # Select agent (simple round-robin for now)
    selected_agent = available_agents[0]

    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "agent_id": selected_agent["id"],
        "task": dispatch.task,
        "parameters": dispatch.parameters,
        "priority": dispatch.priority,
        "status": "queued",
        "created_at": time.time()
    }

    task_queue.append(task)

    # In a real implementation, this would notify the agent via Redis pub/sub or similar
    # For now, we'll simulate immediate processing

    return {"task_id": task_id, "agent_id": selected_agent["id"], "status": "dispatched"}

@app.get("/agent/tasks/{task_id}")
def get_task_status(task_id: str):
    """Get the status of a dispatched task"""
    task = next((t for t in task_queue if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task

@app.post("/agent/tasks/{task_id}/complete")
def complete_task(task_id: str, result: TaskResult):
    """Mark a task as completed"""
    task = next((t for t in task_queue if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.update({
        "status": result.status,
        "result": result.result,
        "error": result.error,
        "completed_at": time.time()
    })

    return {"status": "updated"}

# Supervisor orchestration endpoint
@app.post("/supervisor/orchestrate")
def orchestrate_workflow(workflow: Dict[str, Any]):
    """Orchestrate a multi-agent workflow"""
    # Simple supervisor logic - in a real implementation this would be more sophisticated
    tasks = workflow.get("tasks", [])
    results = []

    for task_spec in tasks:
        # Dispatch each task
        dispatch = TaskDispatch(**task_spec)
        result = dispatch_task(dispatch)
        results.append(result)

    return {"workflow_id": str(uuid.uuid4()), "tasks_dispatched": results}

# Federation endpoints
@app.post("/federation/register-peer")
async def api_register_peer(node_id: str, address: str):
    """Register a peer node in the federation"""
    if not federation_available:
        raise HTTPException(status_code=503, detail="Federation not available")

    success = await register_peer(node_id, address)
    if success:
        return {"status": "registered", "node_id": node_id, "address": address}
    else:
        raise HTTPException(status_code=500, detail="Failed to register peer")

@app.post("/federation/heartbeat")
async def api_broadcast_heartbeat():
    """Broadcast heartbeat to federation"""
    if not federation_available:
        raise HTTPException(status_code=503, detail="Federation not available")

    await broadcast_heartbeat()
    return {"status": "heartbeat_sent"}

@app.post("/federation/sync-summary/{peer_id}")
async def api_sync_summary(peer_id: str):
    """Sync cortex summary with a peer node"""
    if not federation_available:
        raise HTTPException(status_code=503, detail="Federation not available")

    summary = await sync_summary(peer_id)
    if summary:
        return summary
    else:
        raise HTTPException(status_code=404, detail="Peer not found or sync failed")

@app.get("/federation/peers")
async def api_get_peers():
    """Get list of all known federation peers"""
    if not federation_available:
        raise HTTPException(status_code=503, detail="Federation not available")

    peers = await get_peer_list()
    return {"peers": peers}

# Evolution endpoints
@app.post("/evolution/genome/random")
def create_random_genome(num_weights: int = 10, mutation_rate: float = 0.05):
    """Create a random agent genome"""
    if not evolution_available:
        raise HTTPException(status_code=503, detail="Evolution engine not available")

    genome = AgentGenome.random(num_weights, mutation_rate)
    return {"genome": genome.to_dict()}

@app.post("/evolution/genome/mutate")
def mutate_genome(genome_data: dict):
    """Mutate an existing genome"""
    if not evolution_available:
        raise HTTPException(status_code=503, detail="Evolution engine not available")

    genome = AgentGenome.from_dict(genome_data)
    mutated = genome.mutate()
    return {"original": genome.to_dict(), "mutated": mutated.to_dict()}

@app.post("/evolution/genome/crossover")
def crossover_genomes(genome1_data: dict, genome2_data: dict):
    """Perform crossover between two genomes"""
    if not evolution_available:
        raise HTTPException(status_code=503, detail="Evolution engine not available")

    genome1 = AgentGenome.from_dict(genome1_data)
    genome2 = AgentGenome.from_dict(genome2_data)
    child1, child2 = genome1.crossover(genome2)
    return {"parent1": genome1.to_dict(), "parent2": genome2.to_dict(),
            "child1": child1.to_dict(), "child2": child2.to_dict()}

@app.post("/evolution/evaluate")
def evaluate_genome(genome_data: dict, fitness_function: str = "sphere"):
    """Evaluate genome fitness"""
    if not evolution_available:
        raise HTTPException(status_code=503, detail="Evolution engine not available")

    genome = AgentGenome.from_dict(genome_data)
    fitness_func = get_fitness_function(fitness_function)

    if not fitness_func:
        raise HTTPException(status_code=400, detail=f"Unknown fitness function: {fitness_function}")

    evaluator = FitnessEvaluator()
    result = evaluator.evaluate_sync(genome, fitness_func)

    return {
        "genome": genome.to_dict(),
        "fitness_function": fitness_function,
        "result": {
            "score": result.score,
            "metrics": result.metrics,
            "duration": result.duration,
            "success": result.success,
            "error_message": result.error_message
        }
    }

@app.post("/evolution/evolve")
def evolve_population(population_size: int = 20, generations: int = 10,
                     fitness_function: str = "sphere", num_weights: int = 5):
    """Run evolutionary algorithm"""
    if not evolution_available:
        raise HTTPException(status_code=503, detail="Evolution engine not available")

    fitness_func = get_fitness_function(fitness_function)
    if not fitness_func:
        raise HTTPException(status_code=400, detail=f"Unknown fitness function: {fitness_function}")

    # Configure evolution
    config = EvolutionConfig(
        population_size=population_size,
        max_generations=generations
    )

    # Create algorithm
    ea = EvolutionaryAlgorithm(config)

    # Initialize population
    def genome_factory():
        return AgentGenome.random(num_weights)

    ea.initialize_population(genome_factory)

    # Evolve
    evolution_history = []
    while ea.evolve_generation(fitness_func):
        stats = ea.get_population_stats()
        evolution_history.append(stats)

    # Get final results
    best_genome = ea.get_best_genome()

    return {
        "generations_run": len(evolution_history),
        "final_stats": ea.get_population_stats(),
        "best_genome": best_genome.to_dict(),
        "evolution_history": evolution_history
    }

@app.post("/agent/evolve")
async def trigger_agent_evolution(
    population_size: int = 50,
    generations: int = 25,
    fitness_measure: str = "comprehensive",
    num_weights: int = 10,
    mutation_rate: float = 0.05,
    elite_size: int = 5
):
    """
    Trigger agent evolution process via API

    This endpoint runs a complete evolutionary optimization cycle for agent genomes,
    evaluating them against the specified fitness measures and returning the best evolved agent.
    """
    if not evolution_available:
        raise HTTPException(status_code=503, detail="Evolution engine not available")

    try:
        # Import the evolution manager
        from backend.agent_evolve.evolve import EvolutionManager

        # Create temporary evolution manager (in production, you'd want persistent storage)
        manager = EvolutionManager(population_file=None)  # Don't save to disk for API calls

        # Initialize population
        manager.initialize_population(population_size, num_weights, mutation_rate)

        # Configure evolution
        from backend.agent_evolve.evolution import EvolutionConfig
        config = EvolutionConfig(
            population_size=population_size,
            elite_size=elite_size,
            mutation_rate=mutation_rate,
            crossover_rate=0.8,
            max_generations=generations
        )

        # Run evolution
        evolution_results = []
        generation = 0

        while manager.evolve_generation(config, fitness_measure) and generation < generations:
            generation += 1
            stats = manager.get_population_stats()
            evolution_results.append({
                "generation": generation,
                "stats": stats,
                "timestamp": time.time()
            })

        # Get final results
        best_genome = manager.get_best_genome()
        final_stats = manager.get_population_stats()

        return {
            "success": True,
            "evolution_summary": {
                "generations_completed": generation,
                "population_size": population_size,
                "fitness_measure": fitness_measure,
                "final_best_fitness": final_stats["best_fitness"],
                "final_avg_fitness": final_stats["avg_fitness"]
            },
            "best_agent_genome": best_genome.to_dict(),
            "evolution_progress": evolution_results[-5:] if evolution_results else [],  # Last 5 generations
            "diversity_score": manager.get_population_diversity()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evolution failed: {str(e)}")

# Federation initialization
federation_bridge = None

@app.on_event("startup")
async def startup_event():
    """Initialize federation bridge on startup"""
    global federation_bridge
    if federation_available:
        try:
            # Get node ID from environment or generate one
            import os
            node_id = os.getenv("NODE__NODE_NAME", f"brain_swarm_{uuid.uuid4().hex[:8]}")
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

            await initialize_federation(node_id, redis_url)
            print(f"✅ Federation bridge initialized for node: {node_id}")
        except Exception as e:
            print(f"⚠️  Federation initialization failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown federation bridge on shutdown"""
    if federation_available:
        try:
            await shutdown_federation()
            print("✅ Federation bridge shutdown")
        except Exception as e:
            print(f"⚠️  Federation shutdown failed: {e}")

Instrumentator().instrument(app).expose(app)
