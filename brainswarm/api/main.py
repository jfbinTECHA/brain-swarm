from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time
import os
import json
import asyncio
import redis

from brainswarm.config import settings
from brainswarm.coordination.coordinator import SwarmCoordinator
from brainswarm.core.base import logger
from brainswarm.observability.metrics import prometheus_metrics
from brainswarm.observability.health import health_checker, HealthStatus
from brainswarm.observability.tracing import tracing_manager, get_correlation_id
from brainswarm.observability.governance import governance_monitor
from brainswarm.observability.alerting import alert_manager
from brainswarm.security.auth import (
    get_current_user, require_api_key, authenticate_agent, authenticate_user,
    get_current_user_with_permissions, require_role, refresh_access_token,
    UserRole, Permission, SecurityAuditLogger
)
from brainswarm.plugin_registry import agent_registry
from brainswarm.message_queue import message_queue
from brainswarm.cortex.incident_broadcast import broadcast_to_kilo
from brainswarm.dashboard.mission_control import (
    mission_control, get_mission_control_dashboard, create_mission_control_html
)
from brainswarm.webhook_service.api import router as webhook_router
from brainswarm.schemas.incident import AlertGroup

# 🧠 Newly added routers
from brainswarm.cortex.api import router as cortex_router
from brainswarm.memory.api import router as memory_router

import psutil
import shlex
import subprocess
import socket
import datetime


app = FastAPI(
    title="Brain Swarm Federation",
    description="Multi-Agent Swarm Intelligence System",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Routers ---
app.include_router(webhook_router)
app.include_router(cortex_router)   # 🧠 Cortex subsystem
app.include_router(memory_router)   # 💾 Memory subsystem


@app.get("/")
async def root():
    """Root endpoint for Brain Swarm Federation API."""
    return {"status": "ok", "system": "Brain Swarm Federation", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Lightweight system health probe for Brain Swarm API."""
    return {
        "status": "ok",
        "service": "brainswarm-api",
        "hostname": socket.gethostname(),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "details": {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "memory_percent": psutil.virtual_memory().percent,
            "active_pids": len(psutil.pids()),
        },
    }
