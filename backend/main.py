from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import time
import uuid
from prometheus_fastapi_instrumentator import Instrumentator

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

Instrumentator().instrument(app).expose(app)
