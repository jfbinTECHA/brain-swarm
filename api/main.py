"""
Main FastAPI application for Brain Swarm

Provides REST API endpoints for task management, monitoring, and swarm coordination.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time
import os

from ..coordination.coordinator import SwarmCoordinator
from ..core.base import logger

# Create FastAPI app
app = FastAPI(
    title="Brain Swarm API",
    description="Multi-Agent Swarm Intelligence System API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global coordinator instance
coordinator = None

def create_app():
    """Factory function to create FastAPI app for testing"""
    return app

def get_coordinator() -> SwarmCoordinator:
    """Get or create the global coordinator instance"""
    global coordinator
    if coordinator is None:
        swarm_id = os.getenv("BRAIN_SWARM_NODE_NAME", "api_swarm")
        coordinator = SwarmCoordinator(swarm_id)
        logger.log("INFO", "API", f"Initialized SwarmCoordinator: {swarm_id}")
    return coordinator

# Pydantic models for API
class TaskRequest(BaseModel):
    description: str
    type: Optional[str] = "general"
    priority: Optional[int] = 3
    resource_requirements: Optional[str] = "medium"

class TaskResponse(BaseModel):
    task_id: str
    status: str
    strategy: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    swarm_id: str
    agent_count: int
    active_tasks: int
    timestamp: float

class MetricsResponse(BaseModel):
    agent_metrics: Dict[str, Any]
    system_metrics: Dict[str, Any]
    task_metrics: Dict[str, Any]
    timestamp: float

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    coord = get_coordinator()
    return HealthResponse(
        status="healthy",
        swarm_id=coord.swarm_id,
        agent_count=len(coord.registered_agents),
        active_tasks=len(coord.delegation_system.active_tasks),
        timestamp=time.time()
    )

@app.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskRequest, background_tasks: BackgroundTasks):
    """Create and execute a new task"""
    try:
        coord = get_coordinator()

        task_data = {
            "description": task.description,
            "type": task.type,
            "priority": task.priority,
            "resource_requirements": task.resource_requirements,
            "task_id": f"task_{int(time.time())}_{hash(task.description) % 1000}"
        }

        # Execute task in background
        background_tasks.add_task(coord.execute_task, task_data)

        return TaskResponse(
            task_id=task_data["task_id"],
            status="accepted",
            strategy=None  # Will be populated when task completes
        )

    except Exception as e:
        logger.log("ERROR", "API", f"Failed to create task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}")

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a specific task"""
    coord = get_coordinator()

    # Check if task exists in active tasks
    if task_id in coord.delegation_system.active_tasks:
        task_info = coord.delegation_system.active_tasks[task_id]
        return {
            "task_id": task_id,
            "status": task_info["status"],
            "assigned_agent": task_info["task"].assigned_agent,
            "created_at": task_info["assigned_at"],
            "priority": task_info.get("priority", 1)
        }

    # Check working memory for completed tasks
    if coord.working_memory:
        result = coord.working_memory.retrieve(f"task_result_{task_id}")
        if result:
            return {
                "task_id": task_id,
                "status": "completed",
                "result": result
            }

    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

@app.get("/agents")
async def list_agents():
    """List all registered agents"""
    coord = get_coordinator()
    agents = []
    for agent_id in coord.registered_agents:
        load = coord.agent_loads.get(agent_id, 0)
        agents.append({
            "agent_id": agent_id,
            "current_load": load,
            "status": "active" if load < coord.max_agent_load else "busy"
        })

    return {"agents": agents, "total": len(agents)}

@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get system metrics"""
    coord = get_coordinator()

    return MetricsResponse(
        agent_metrics={
            agent_id: {
                "load": coord.agent_loads.get(agent_id, 0),
                "performance": 0.8,  # Placeholder
                "status": "active"
            }
            for agent_id in coord.registered_agents
        },
        system_metrics={
            "total_agents": len(coord.registered_agents),
            "active_tasks": len(coord.delegation_system.active_tasks),
            "system_load": sum(coord.agent_loads.values()) / max(len(coord.registered_agents), 1)
        },
        task_metrics={
            "completed_tasks": 0,  # Would track this in a real implementation
            "failed_tasks": 0,
            "average_completion_time": 0.0
        },
        timestamp=time.time()
    )

@app.get("/dashboard/{dashboard_type}")
async def get_dashboard(dashboard_type: str):
    """Get dashboard data"""
    coord = get_coordinator()

    if dashboard_type == "performance":
        return coord.get_performance_dashboard()
    elif dashboard_type == "learning":
        return coord.get_learning_insights_dashboard()
    elif dashboard_type == "operational":
        return coord.get_operational_oversight_dashboard()
    elif dashboard_type == "federation":
        return coord.get_federation_dashboard()
    elif dashboard_type == "predictive":
        return coord.get_predictive_control_dashboard()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown dashboard type: {dashboard_type}")

@app.post("/agents/register")
async def register_agent(agent_id: str, agent_type: str = "generic"):
    """Register a new agent"""
    coord = get_coordinator()
    coord.register_agent(agent_id)

    logger.log("INFO", "API", f"Registered agent: {agent_id} ({agent_type})")

    return {
        "status": "registered",
        "agent_id": agent_id,
        "agent_type": agent_type,
        "coordinator": coord.swarm_id
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Brain Swarm API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.log("ERROR", "API", f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)