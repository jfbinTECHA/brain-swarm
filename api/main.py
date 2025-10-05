"""
Main FastAPI application for Brain Swarm

Provides REST API endpoints for task management, monitoring, and swarm coordination.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time
import os
import json
import asyncio

from ..config import settings
from ..coordination.coordinator import SwarmCoordinator
from ..core.base import logger
from ..observability.metrics import prometheus_metrics
from ..observability.health import health_checker, HealthStatus
from ..observability.tracing import tracing_manager, get_correlation_id
from ..observability.governance import governance_monitor
from ..observability.alerting import alert_manager
from ..security.auth import (
    get_current_user, require_api_key, authenticate_agent, authenticate_user,
    get_current_user_with_permissions, require_role, refresh_access_token,
    UserRole, Permission, SecurityAuditLogger
)
from ..plugin_registry import agent_registry
from ..message_queue import message_queue
from ..cortex.api.routes import router as cortex_router
from ..config import settings

# Conditional imports for scalability
if settings.scalability.enabled:
    if settings.scalability.message_queue_mode in ["cluster", "partitioned"]:
        from ..scalability.scalable_message_queue import initialize_scalable_message_queue, QueueMode, scalable_message_queue
    if settings.scalability.async_agents_enabled:
        from ..scalability.async_agents import initialize_async_agents
    if settings.scalability.multi_cluster_enabled:
        from ..scalability.multi_cluster_federation import initialize_multi_cluster_federation
    if settings.scalability.auto_scaling_enabled:
        from ..coordination.auto_scaling import initialize_auto_scaling
        from ..coordination.scalable_cloud_ops import start_scalable_cloud_ops

# Prometheus monitoring
from prometheus_fastapi_instrumentator import Instrumentator

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

# Add Prometheus monitoring
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Startup event to initialize services
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Initialize message queue (scalable or basic)
        if settings.scalability.enabled and settings.scalability.message_queue_mode in ["cluster", "partitioned"]:
            # Use scalable message queue
            queue_mode = QueueMode.CLUSTER if settings.scalability.message_queue_mode == "cluster" else QueueMode.PARTITIONED
            await initialize_scalable_message_queue(
                redis_urls=settings.scalability.redis_urls,
                mode=queue_mode,
                partitions=settings.scalability.partitions
            )
            # Replace global message_queue reference
            import api.main
            api.main.message_queue = scalable_message_queue
            logger.log("INFO", "API", f"Scalable message queue initialized (mode: {queue_mode.value})")
        else:
            # Use basic message queue
            await message_queue.connect()
            await message_queue.start_listening()
            logger.log("INFO", "API", "Basic message queue initialized")

        # Initialize async agents if enabled
        if settings.scalability.enabled and settings.scalability.async_agents_enabled:
            # Use all available agent types from registry
            from ..plugin_registry import agent_registry
            available_agent_types = list(agent_registry._plugins.keys())

            await initialize_async_agents(
                min_agents=settings.scalability.agent_pool_min,
                max_agents=settings.scalability.agent_pool_max,
                agent_types=available_agent_types
            )
            logger.log("INFO", "API", "Async agents initialized")

        # Initialize multi-cluster federation if enabled
        if settings.scalability.enabled and settings.scalability.multi_cluster_enabled:
            await initialize_multi_cluster_federation(
                local_cluster_id=settings.scalability.cluster_id,
                local_node_id=settings.node.node_name
            )
            logger.log("INFO", "API", "Multi-cluster federation initialized")

        # Initialize auto-scaling if enabled
        if settings.scalability.enabled and settings.scalability.auto_scaling_enabled:
            # Initialize auto-scaling coordinator
            auto_scaler = initialize_auto_scaling()
            logger.log("INFO", "API", "Auto-scaling coordinator initialized")

            # Start scalable cloud operations
            scalable_ops = start_scalable_cloud_ops()
            logger.log("INFO", "API", "Scalable cloud operations started")

        # Initialize scheduled summarizer job
        try:
            from ..cortex.scheduled_summarizer import scheduled_summarizer
            if scheduled_summarizer:
                await scheduled_summarizer.start()
                logger.log("INFO", "API", "Scheduled summarizer job started")
        except Exception as e:
            logger.log("WARNING", "API", f"Failed to start scheduled summarizer: {e}")

    except Exception as e:
        logger.log("ERROR", "API", f"Failed to initialize services: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        # Shutdown scalable components if they were initialized
        if settings.scalability.enabled:
            if settings.scalability.multi_cluster_enabled:
                from ..scalability.multi_cluster_federation import shutdown_multi_cluster_federation
                await shutdown_multi_cluster_federation()
                logger.log("INFO", "API", "Multi-cluster federation shutdown")

            if settings.scalability.async_agents_enabled:
                from ..scalability.async_agents import shutdown_async_agents
                await shutdown_async_agents()
                logger.log("INFO", "API", "Async agents shutdown")

            if settings.scalability.message_queue_mode in ["cluster", "partitioned"]:
                from ..scalability.scalable_message_queue import shutdown_scalable_message_queue
                await shutdown_scalable_message_queue()
                logger.log("INFO", "API", "Scalable message queue shutdown")
            else:
                await message_queue.stop_listening()
                await message_queue.disconnect()
                logger.log("INFO", "API", "Basic message queue shutdown")

            if settings.scalability.auto_scaling_enabled:
                from ..coordination.scalable_cloud_ops import stop_scalable_cloud_ops
                stop_scalable_cloud_ops()
                logger.log("INFO", "API", "Scalable cloud operations stopped")
        else:
            # Basic shutdown
            await message_queue.stop_listening()
            await message_queue.disconnect()
            logger.log("INFO", "API", "Message queue shutdown")

    except Exception as e:
        logger.log("ERROR", "API", f"Error during shutdown: {e}")

# Global coordinator instance
coordinator = None

async def get_swarm_graph_data(coord) -> Dict[str, Any]:
    """Generate graph visualization data for swarm view"""
    graph_data = {
        "nodes": [],
        "edges": [],
        "metadata": {
            "node_types": ["agent", "task", "coordinator"],
            "edge_types": ["assigned_to", "communicates_with", "depends_on"],
            "timestamp": time.time()
        }
    }

    # Add coordinator node
    graph_data["nodes"].append({
        "id": f"coordinator_{coord.swarm_id}",
        "label": f"Coordinator\n{coord.swarm_id}",
        "type": "coordinator",
        "size": 20,
        "color": "#3b82f6",
        "position": {"x": 0, "y": 0}
    })

    # Add agent nodes
    agent_nodes = []
    for i, agent_id in enumerate(coord.registered_agents):
        load = coord.agent_loads.get(agent_id, 0)
        status = "active" if load < coord.max_agent_load else "busy"

        # Position agents in a circle around coordinator
        angle = (2 * 3.14159 * i) / max(1, len(coord.registered_agents))
        radius = 100
        x = radius * 3.14159 * 0.5  # cos(angle) approximation
        y = radius * 3.14159 * 0.5  # sin(angle) approximation

        agent_node = {
            "id": agent_id,
            "label": f"{agent_id}\nLoad: {load}",
            "type": "agent",
            "size": 15 + min(load * 2, 10),  # Size based on load
            "color": "#22c55e" if status == "active" else "#eab308",
            "position": {"x": x, "y": y},
            "properties": {
                "load": load,
                "status": status,
                "max_load": coord.max_agent_load
            }
        }
        agent_nodes.append(agent_node)

        # Connect agent to coordinator
        graph_data["edges"].append({
            "id": f"coord_to_{agent_id}",
            "from": f"coordinator_{coord.swarm_id}",
            "to": agent_id,
            "type": "manages",
            "color": "#6b7280",
            "width": 2
        })

    graph_data["nodes"].extend(agent_nodes)

    # Add task nodes
    task_nodes = []
    for task_id, task_info in coord.delegation_system.active_tasks.items():
        assigned_agent = task_info["task"].assigned_agent

        # Position task near its assigned agent
        agent_index = list(coord.registered_agents.keys()).index(assigned_agent) if assigned_agent in coord.registered_agents else 0
        base_x = agent_nodes[agent_index]["position"]["x"] if agent_index < len(agent_nodes) else 0
        base_y = agent_nodes[agent_index]["position"]["y"] if agent_index < len(agent_nodes) else 0

        task_node = {
            "id": task_id,
            "label": task_info["task"].description[:20] + "..." if len(task_info["task"].description) > 20 else task_info["task"].description,
            "type": "task",
            "size": 10,
            "color": "#f59e0b",
            "position": {"x": base_x + 30, "y": base_y + 30},
            "properties": {
                "status": task_info["status"],
                "priority": task_info.get("priority", 1),
                "assigned_agent": assigned_agent
            }
        }
        task_nodes.append(task_node)

        # Connect task to assigned agent
        if assigned_agent:
            graph_data["edges"].append({
                "id": f"{task_id}_to_{assigned_agent}",
                "from": task_id,
                "to": assigned_agent,
                "type": "assigned_to",
                "color": "#22c55e",
                "width": 3
            })

    graph_data["nodes"].extend(task_nodes)

    # Add communication edges between agents (simplified)
    # In a real implementation, this would track actual message passing
    for i, agent1 in enumerate(coord.registered_agents):
        for j, agent2 in enumerate(coord.registered_agents):
            if i < j:  # Avoid duplicate edges
                # Add occasional communication edges for visualization
                if (hash(f"{agent1}_{agent2}") % 10) < 3:  # 30% chance
                    graph_data["edges"].append({
                        "id": f"comm_{agent1}_{agent2}",
                        "from": agent1,
                        "to": agent2,
                        "type": "communicates_with",
                        "color": "#a855f7",
                        "width": 1,
                        "style": "dashed"
                    })

    return graph_data

def create_app():
    """Factory function to create FastAPI app for testing"""
    return app

def get_coordinator() -> SwarmCoordinator:
    """Get or create the global coordinator instance"""
    global coordinator
    if coordinator is None:
        swarm_id = settings.node.swarm_id
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

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    role: str

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
async def create_task(
    task: TaskRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user_with_permissions([Permission.TASK_CREATE]))
):
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

    # Add scalable agents if enabled
    if settings.scalability.enabled and settings.scalability.async_agents_enabled:
        from ..scalability.async_agents import agent_pool
        if agent_pool:
            pool_metrics = agent_pool.get_pool_metrics()
            for agent_id in agent_pool.agents.keys():
                agent = agent_pool.agents[agent_id]
                agents.append({
                    "agent_id": agent_id,
                    "type": "async",
                    "current_load": agent.load_metrics.current_load,
                    "status": agent.state.value,
                    "utilization": agent.load_metrics.utilization
                })

    return {"agents": agents, "total": len(agents)}

@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get system metrics"""
    coord = get_coordinator()

    # Base metrics
    agent_metrics = {
        agent_id: {
            "load": coord.agent_loads.get(agent_id, 0),
            "performance": 0.8,  # Placeholder
            "status": "active"
        }
        for agent_id in coord.registered_agents
    }

    system_metrics = {
        "total_agents": len(coord.registered_agents),
        "active_tasks": len(coord.delegation_system.active_tasks),
        "system_load": sum(coord.agent_loads.values()) / max(len(coord.registered_agents), 1)
    }

    # Add scalable metrics if enabled
    if settings.scalability.enabled:
        if settings.scalability.async_agents_enabled:
            from ..scalability.async_agents import agent_pool
            if agent_pool:
                pool_metrics = agent_pool.get_pool_metrics()
                system_metrics.update({
                    "async_agents_total": pool_metrics["total_agents"],
                    "async_agents_active": pool_metrics["active_agents"],
                    "async_agents_avg_utilization": pool_metrics["avg_utilization"]
                })

        if settings.scalability.message_queue_mode in ["cluster", "partitioned"]:
            from ..scalability.scalable_message_queue import scalable_message_queue
            if scalable_message_queue:
                queue_metrics = scalable_message_queue.get_metrics()
                system_metrics.update({
                    "message_queue_mode": queue_metrics["mode"],
                    "messages_processed": queue_metrics["messages_processed"],
                    "messages_failed": queue_metrics["messages_failed"],
                    "queue_success_rate": queue_metrics["success_rate"]
                })

    return MetricsResponse(
        agent_metrics=agent_metrics,
        system_metrics=system_metrics,
        task_metrics={
            "completed_tasks": 0,  # Would track this in a real implementation
            "failed_tasks": 0,
            "average_completion_time": 0.0
        },
        timestamp=time.time()
    )

@app.get("/scalability/status")
async def get_scalability_status():
    """Get comprehensive scalability status"""
    if not settings.scalability.enabled:
        return {"enabled": False, "message": "Scalability features are not enabled"}

    status = {
        "enabled": True,
        "config": {
            "message_queue_mode": settings.scalability.message_queue_mode,
            "async_agents_enabled": settings.scalability.async_agents_enabled,
            "multi_cluster_enabled": settings.scalability.multi_cluster_enabled,
            "auto_scaling_enabled": settings.scalability.auto_scaling_enabled
        },
        "components": {}
    }

    # Async agents status
    if settings.scalability.async_agents_enabled:
        from ..scalability.async_agents import agent_pool, load_balancer
        if agent_pool:
            status["components"]["async_agents"] = {
                "pool_metrics": agent_pool.get_pool_metrics(),
                "load_balancer": load_balancer.get_routing_metrics()
            }

    # Message queue status
    if settings.scalability.message_queue_mode in ["cluster", "partitioned"]:
        from ..scalability.scalable_message_queue import scalable_message_queue
        if scalable_message_queue:
            status["components"]["message_queue"] = scalable_message_queue.get_metrics()

    # Multi-cluster status
    if settings.scalability.multi_cluster_enabled:
        from ..scalability.multi_cluster_federation import multi_cluster_federation
        if multi_cluster_federation:
            status["components"]["multi_cluster"] = multi_cluster_federation.get_multi_cluster_metrics()

    # Auto-scaling status
    if settings.scalability.auto_scaling_enabled:
        from ..coordination.auto_scaling import auto_scaler
        status["components"]["auto_scaling"] = auto_scaler.get_scaling_status()

        from ..coordination.scalable_cloud_ops import scalable_cloud_ops
        status["components"]["cloud_ops"] = scalable_cloud_ops.get_scaling_status()

    return status

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

@app.post("/auth/login", response_model=TokenResponse)
async def login_user(request: LoginRequest, request_obj: Request):
    """Login with username/password to get JWT tokens"""
    client_ip = request_obj.client.host if request_obj.client else "unknown"
    user_agent = request_obj.headers.get("user-agent", "unknown")

    tokens = authenticate_user(request.username, request.password)
    if not tokens:
        SecurityAuditLogger.log_auth_event(
            "login_failed",
            request.username,
            {"ip_address": client_ip, "user_agent": user_agent, "reason": "invalid_credentials"}
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")

    SecurityAuditLogger.log_auth_event(
        "login_successful",
        request.username,
        {"ip_address": client_ip, "user_agent": user_agent, "role": tokens["role"]}
    )

    return TokenResponse(**tokens)


@app.post("/auth/agent-login", response_model=TokenResponse)
async def login_agent(api_key: str, agent_id: str, request_obj: Request):
    """Login with API key to get JWT tokens (for agents)"""
    client_ip = request_obj.client.host if request_obj.client else "unknown"
    user_agent = request_obj.headers.get("user-agent", "unknown")

    tokens = authenticate_agent(api_key, agent_id)
    if not tokens:
        SecurityAuditLogger.log_auth_event(
            "agent_login_failed",
            agent_id,
            {"ip_address": client_ip, "user_agent": user_agent, "reason": "invalid_api_key"}
        )
        raise HTTPException(status_code=401, detail="Invalid API key")

    SecurityAuditLogger.log_auth_event(
        "agent_login_successful",
        agent_id,
        {"ip_address": client_ip, "user_agent": user_agent, "role": tokens["role"]}
    )

    return TokenResponse(**tokens)


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, request_obj: Request):
    """Refresh access token using refresh token"""
    client_ip = request_obj.client.host if request_obj.client else "unknown"

    new_access_token = refresh_access_token(request.refresh_token)
    if not new_access_token:
        SecurityAuditLogger.log_auth_event(
            "token_refresh_failed",
            "unknown",
            {"ip_address": client_ip, "reason": "invalid_refresh_token"}
        )
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Extract user info from new token for logging (simplified)
    SecurityAuditLogger.log_auth_event(
        "token_refresh_successful",
        "unknown",  # Would need to decode token to get user ID
        {"ip_address": client_ip}
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=request.refresh_token,  # Return same refresh token
        token_type="bearer",
        role="unknown"  # Would need to decode to get role
    )


@app.post("/auth/logout")
async def logout(current_user: Dict = Depends(get_current_user)):
    """Logout and invalidate tokens"""
    user_id = current_user.get("sub", "unknown")

    SecurityAuditLogger.log_auth_event(
        "logout",
        user_id,
        {"token_id": current_user.get("jti")}
    )

    # In a production system, you would add the token to a blacklist
    # For now, we just log the logout

    return {"message": "Successfully logged out"}

@app.post("/agents/register")
async def register_agent(
    agent_id: str,
    agent_type: str = "generic",
    api_key: str = None,
    current_user: Dict = Depends(get_current_user_with_permissions([Permission.AGENT_REGISTER]))
):
    """Register a new agent with authentication"""
    # Verify API key
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # Authenticate and get JWT tokens
    tokens = authenticate_agent(api_key, agent_id)
    if not tokens:
        SecurityAuditLogger.log_auth_event(
            "agent_registration_failed",
            agent_id,
            {"reason": "invalid_api_key", "registered_by": current_user.get("sub")}
        )
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Create agent using registry
    agent = agent_registry.create_agent(agent_type, agent_id, settings.node.swarm_id, api_key=api_key)
    if not agent:
        SecurityAuditLogger.log_auth_event(
            "agent_registration_failed",
            agent_id,
            {"reason": "unknown_agent_type", "agent_type": agent_type, "registered_by": current_user.get("sub")}
        )
        raise HTTPException(status_code=400, detail=f"Unknown agent type: {agent_type}")

    # Register with coordinator
    coord = get_coordinator()
    coord.register_agent(agent_id)

    SecurityAuditLogger.log_auth_event(
        "agent_registered",
        agent_id,
        {"agent_type": agent_type, "registered_by": current_user.get("sub"), "role": tokens["role"]}
    )

    logger.log("INFO", "API", f"Registered agent: {agent_id} ({agent_type})")

    return {
        "status": "registered",
        "agent_id": agent_id,
        "agent_type": agent_type,
        "coordinator": coord.swarm_id,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "role": tokens["role"]
    }

@app.websocket("/ws/swarm-view")
async def swarm_view_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time swarm view updates"""
    await websocket.accept()

    # Subscribe to message queue for real-time updates
    async def message_callback(message):
        """Callback for incoming messages"""
        try:
            # Send message data to WebSocket client
            await websocket.send_json({
                "type": "message",
                "data": {
                    "sender": message.sender,
                    "receiver": message.receiver,
                    "message_type": message.message_type.value,
                    "timestamp": message.timestamp,
                    "content": message.content
                }
            })
        except Exception as e:
            logger.log("ERROR", "WebSocket", f"Error sending message: {e}")

    # Subscribe to all messages
    await message_queue.subscribe("swarm_view", message_callback)

    # Send initial swarm state
    coord = get_coordinator()
    await websocket.send_json({
        "type": "swarm_state",
        "data": {
            "swarm_id": coord.swarm_id,
            "agent_count": len(coord.registered_agents),
            "active_tasks": len(coord.delegation_system.active_tasks),
            "agents": list(coord.registered_agents.keys()),
            "timestamp": time.time()
        }
    })

    # Send initial graph visualization data
    graph_data = await get_swarm_graph_data(coord)
    await websocket.send_json({
        "type": "graph_visualization",
        "data": graph_data
    })

    # Send periodic system metrics and graph updates
    async def send_metrics():
        graph_update_counter = 0
        while True:
            try:
                coord = get_coordinator()
                metrics_data = {
                    "type": "metrics",
                    "data": {
                        "agent_count": len(coord.registered_agents),
                        "active_tasks": len(coord.delegation_system.active_tasks),
                        "system_load": sum(coord.agent_loads.values()) / max(len(coord.registered_agents), 1),
                        "timestamp": time.time()
                    }
                }
                await websocket.send_json(metrics_data)

                # Send graph updates every 30 seconds (6 * 5 seconds)
                graph_update_counter += 1
                if graph_update_counter >= 6:
                    graph_data = await get_swarm_graph_data(coord)
                    await websocket.send_json({
                        "type": "graph_update",
                        "data": graph_data
                    })
                    graph_update_counter = 0

                await asyncio.sleep(5)  # Send every 5 seconds
            except Exception as e:
                logger.log("ERROR", "WebSocket", f"Error sending metrics: {e}")
                break

    # Start metrics task
    metrics_task = asyncio.create_task(send_metrics())

    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            # Handle client messages if needed
            logger.log("DEBUG", "WebSocket", f"Received: {data}")

    except WebSocketDisconnect:
        logger.log("INFO", "WebSocket", "Client disconnected")
    finally:
        # Cleanup
        metrics_task.cancel()
        try:
            await metrics_task
        except asyncio.CancelledError:
            pass

@app.get("/")
async def root():
    """Root endpoint"""
    response = {
        "message": "Brain Swarm API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "websocket": "/ws/swarm-view",
        "observability": {
            "health": "/health",
            "metrics": "/metrics",
            "alerts": "/monitoring/alerts",
            "compliance": "/monitoring/compliance",
            "traces": "/monitoring/traces",
            "dashboard": "/monitoring/dashboard"
        }
    }

    # Add scalability endpoints if enabled
    if settings.scalability.enabled:
        response["scalability"] = {
            "status": "/scalability/status",
            "enabled_features": []
        }
        if settings.scalability.async_agents_enabled:
            response["scalability"]["enabled_features"].append("async_agents")
        if settings.scalability.message_queue_mode in ["cluster", "partitioned"]:
            response["scalability"]["enabled_features"].append("scalable_message_queue")
        if settings.scalability.multi_cluster_enabled:
            response["scalability"]["enabled_features"].append("multi_cluster_federation")
        if settings.scalability.auto_scaling_enabled:
            response["scalability"]["enabled_features"].append("auto_scaling")

    return response


# Enhanced health check with observability integration
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint with observability"""
    correlation_id = get_correlation_id()

    with tracing_manager.trace_context("health_check", tags={"endpoint": "/health"}):
        # Run health checks
        health_results = health_checker.get_overall_health()

        # Add correlation ID to response
        health_results["correlation_id"] = correlation_id

        # Set HTTP status based on health
        status_code = 200
        if health_results["status"] == "critical":
            status_code = 503  # Service Unavailable
        elif health_results["status"] == "unhealthy":
            status_code = 503
        elif health_results["status"] == "degraded":
            status_code = 200  # Still operational but degraded

        prometheus_metrics.record_api_request("/health", "GET", status_code, 0.001)

        return JSONResponse(
            content=health_results,
            status_code=status_code
        )


@app.get("/health/{check_name}")
async def specific_health_check(check_name: str):
    """Get specific health check result"""
    correlation_id = get_correlation_id()

    with tracing_manager.trace_context("specific_health_check",
                                     tags={"endpoint": f"/health/{check_name}", "check_name": check_name}):
        result = health_checker.run_check(check_name)

        if not result:
            raise HTTPException(status_code=404, detail=f"Health check '{check_name}' not found")

        response_data = result.to_dict()
        response_data["correlation_id"] = correlation_id

        status_code = 200
        if result.status == HealthStatus.CRITICAL:
            status_code = 503
        elif result.status == HealthStatus.UNHEALTHY:
            status_code = 503

        prometheus_metrics.record_api_request(f"/health/{check_name}", "GET", status_code, 0.001)

        return JSONResponse(content=response_data, status_code=status_code)


@app.get("/monitoring/alerts")
async def get_alerts():
    """Get active alerts and dashboard data"""
    correlation_id = get_correlation_id()

    with tracing_manager.trace_context("alerts_endpoint", tags={"endpoint": "/monitoring/alerts"}):
        dashboard_data = alert_manager.get_dashboard_data()

        # Add active alerts details
        active_alerts = alert_manager.get_active_alerts()
        dashboard_data["active_alerts_detail"] = [alert.to_dict() for alert in active_alerts]
        dashboard_data["correlation_id"] = correlation_id

        prometheus_metrics.record_api_request("/monitoring/alerts", "GET", 200, 0.001)

        return dashboard_data


@app.get("/monitoring/compliance")
async def get_compliance_report(start_time: Optional[float] = None, end_time: Optional[float] = None):
    """Get compliance monitoring report"""
    correlation_id = get_correlation_id()

    with tracing_manager.trace_context("compliance_endpoint",
                                     tags={"endpoint": "/monitoring/compliance"}):
        report = governance_monitor.get_compliance_report(start_time, end_time)
        report["correlation_id"] = correlation_id

        prometheus_metrics.record_api_request("/monitoring/compliance", "GET", 200, 0.001)

        return report


@app.get("/monitoring/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get distributed trace information"""
    correlation_id = get_correlation_id()

    with tracing_manager.trace_context("trace_endpoint",
                                     tags={"endpoint": f"/monitoring/traces/{trace_id}", "trace_id": trace_id}):
        trace_tree = tracing_manager.get_trace_tree(trace_id)

        if "error" in trace_tree:
            raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

        trace_tree["correlation_id"] = correlation_id

        prometheus_metrics.record_api_request(f"/monitoring/traces/{trace_id}", "GET", 200, 0.001)

        return trace_tree


@app.get("/monitoring/dashboard")
async def get_monitoring_dashboard():
    """Comprehensive monitoring dashboard data"""
    correlation_id = get_correlation_id()

    with tracing_manager.trace_context("dashboard_endpoint", tags={"endpoint": "/monitoring/dashboard"}):
        # Gather data from all observability components
        dashboard = {
            "correlation_id": correlation_id,
            "timestamp": time.time(),
            "health": health_checker.get_overall_health(),
            "alerts": alert_manager.get_dashboard_data(),
            "compliance": governance_monitor.get_compliance_report(),
            "metrics_summary": prometheus_metrics.get_metrics_json(),
            "active_traces": len(tracing_manager.get_active_spans()),
            "system_status": "operational"  # Could be more sophisticated
        }

        prometheus_metrics.record_api_request("/monitoring/dashboard", "GET", 200, 0.001)

        return dashboard


@app.post("/monitoring/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, acknowledged_by: str = "api_user"):
    """Acknowledge an alert"""
    correlation_id = get_correlation_id()

    with tracing_manager.trace_context("acknowledge_alert",
                                     tags={"endpoint": f"/monitoring/alerts/{alert_id}/acknowledge",
                                           "alert_id": alert_id}):
        alert_manager.acknowledge_alert(alert_id, acknowledged_by)

        prometheus_metrics.record_api_request(f"/monitoring/alerts/{alert_id}/acknowledge", "POST", 200, 0.001)

        return {"status": "acknowledged", "alert_id": alert_id, "correlation_id": correlation_id}


@app.post("/monitoring/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, resolved_by: str = "api_user"):
    """Resolve an alert"""
    correlation_id = get_correlation_id()

    with tracing_manager.trace_context("resolve_alert",
                                     tags={"endpoint": f"/monitoring/alerts/{alert_id}/resolve",
                                           "alert_id": alert_id}):
        alert_manager.resolve_alert(alert_id, resolved_by)

        prometheus_metrics.record_api_request(f"/monitoring/alerts/{alert_id}/resolve", "POST", 200, 0.001)

        return {"status": "resolved", "alert_id": alert_id, "correlation_id": correlation_id}

# Include cortex router
app.include_router(cortex_router)

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
    uvicorn.run(app, host=settings.node.host, port=settings.node.port)