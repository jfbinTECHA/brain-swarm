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
