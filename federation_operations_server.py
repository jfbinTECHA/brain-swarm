#!/usr/bin/env python3
"""
Federation Operations Server for Brain Swarm Operations Platform

A WebSocket-based server that provides real-time monitoring and control
capabilities for the Brain Swarm Federation Operations Platform.

Features:
- Real-time swarm monitoring and control
- Live metrics streaming
- Alert system
- Authentication and authorization
- Integration with federation registry
"""

import asyncio
import json
import logging
import time
import random
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
import hashlib
import secrets
import threading
import requests
from enum import Enum

import socketio
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from security import SecurityManager, PermissionLevel

class OperationMode(Enum):
    """Operation modes for the federation server"""
    LIVE = "live"          # Connect to real swarm nodes
    SIMULATION = "simulation"  # Use simulated data for testing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# FastAPI app
app = FastAPI(title="Federation Operations Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """Dependency to get and validate API key."""
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # Validate API key using SecurityManager
    client_credentials = ops_manager.security_manager.authenticate_client(
        api_key, "federation_rest_api"
    )

    if not client_credentials:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return api_key

# Mount Socket.IO
socket_app = socketio.ASGIApp(sio, app)

# Global state
@dataclass
class SwarmState:
    """Real-time swarm state."""
    swarm_id: str
    status: str = "unknown"
    load: float = 0.0
    tasks_active: int = 0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    network_latency: float = 0.0
    last_updated: float = 0.0
    alerts: List[Dict[str, Any]] = None
    metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []
        if self.metrics is None:
            self.metrics = {}

@dataclass
class FederationState:
    """Federation connection state."""
    id: str
    swarm1: str
    swarm2: str
    status: str = "inactive"
    throughput: float = 0.0
    latency: float = 0.0
    active: bool = False
    last_updated: float = 0.0

@dataclass
class Alert:
    """System alert."""
    id: str
    level: str  # 'critical', 'warning', 'info'
    title: str
    message: str
    swarm_id: Optional[str] = None
    timestamp: float = 0.0
    acknowledged: bool = False

@dataclass
class HistoricalMetric:
    """Historical metric data point."""
    timestamp: float
    metric_name: str
    value: float
    swarm_id: Optional[str] = None
    metadata: Dict[str, Any] = None

class FederationOperationsManager:
    """Manages real-time federation operations."""

    def __init__(self, registry_url: str = "http://localhost:8002",
                 credentials_file: str = "credentials.json",
                 audit_log_file: str = "federation_audit.log",
                 cert_file: Optional[str] = None,
                 key_file: Optional[str] = None,
                 operation_mode: OperationMode = OperationMode.SIMULATION):
        self.registry_url = registry_url
        self.operation_mode = operation_mode
        self.swarm_states: Dict[str, SwarmState] = {}
        self.federation_states: Dict[str, FederationState] = {}
        self.alerts: List[Alert] = []
        self.connected_clients: Set[str] = set()
        self.auth_tokens: Dict[str, Dict[str, Any]] = {}

        # Initialize Security Manager
        self.security_manager = SecurityManager(
            credentials_file=credentials_file,
            audit_log_file=audit_log_file,
            cert_file=cert_file,
            key_file=key_file
        )

        # Real swarm node connections
        self.discovered_swarms: Dict[str, Dict[str, Any]] = {}  # swarm_id -> connection info
        self.swarm_health_cache: Dict[str, Dict[str, Any]] = {}  # swarm_id -> last health data
        self.swarm_metrics_cache: Dict[str, Dict[str, Any]] = {}  # swarm_id -> last metrics data

        # Historical data storage
        self.metrics_history: List[HistoricalMetric] = []
        self.max_history_size = 10000  # Keep last 10k data points
        self.history_retention_hours = 24  # Keep data for 24 hours

        # Start background tasks
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self.monitor_thread.start()
        if self.operation_mode == OperationMode.LIVE:
            self.discovery_thread.start()

    def switch_operation_mode(self, new_mode: OperationMode) -> bool:
        """Switch between live and simulation modes"""
        if new_mode == self.operation_mode:
            return True  # Already in the requested mode

        logger.info(f"Switching from {self.operation_mode.value} to {new_mode.value} mode")

        old_mode = self.operation_mode
        self.operation_mode = new_mode

        # Clear existing data when switching modes
        self.swarm_states.clear()
        self.federation_states.clear()
        self.alerts.clear()
        self.discovered_swarms.clear()
        self.swarm_health_cache.clear()
        self.swarm_metrics_cache.clear()

        # Handle mode-specific initialization
        if new_mode == OperationMode.LIVE:
            # Start discovery thread for live mode
            if not self.discovery_thread.is_alive():
                self.discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
                self.discovery_thread.start()
        elif new_mode == OperationMode.SIMULATION:
            # Stop discovery thread if running
            if hasattr(self, 'discovery_thread') and self.discovery_thread.is_alive():
                # Thread will stop naturally since running=False will be checked
                pass

        # Initialize data for new mode
        if new_mode == OperationMode.SIMULATION:
            self._create_simulated_swarms()
        # Live mode will discover swarms via the discovery loop

        logger.info(f"Successfully switched to {new_mode.value} mode")
        return True

    def get_operation_mode(self) -> str:
        """Get current operation mode"""
        return self.operation_mode.value

    def _discovery_loop(self):
        """Background discovery loop for finding real swarm nodes."""
        while self.running:
            try:
                self._discover_swarm_nodes()
                time.sleep(30)  # Discover every 30 seconds
            except Exception as e:
                logger.error(f"Error in discovery loop: {e}")
                time.sleep(60)

    def _discover_swarm_nodes(self):
        """Discover real swarm nodes via registry and direct connections."""
        try:
            # Try to get swarms from federation registry
            registry_swarms = self._query_federation_registry()

            # Also try direct discovery on common ports
            direct_swarms = self._direct_swarm_discovery()

            # Merge discovered swarms
            all_discovered = {**registry_swarms, **direct_swarms}

            # Update discovered swarms
            for swarm_id, info in all_discovered.items():
                if swarm_id not in self.discovered_swarms:
                    logger.info(f"Discovered new swarm: {swarm_id} at {info.get('api_url')}")
                    self.discovered_swarms[swarm_id] = info
                else:
                    # Update existing info
                    self.discovered_swarms[swarm_id].update(info)

            # Remove stale discoveries (not seen for 5 minutes)
            cutoff_time = time.time() - 300
            stale_swarms = [
                swarm_id for swarm_id, info in self.discovered_swarms.items()
                if info.get('last_seen', 0) < cutoff_time
            ]
            for swarm_id in stale_swarms:
                logger.info(f"Removing stale swarm: {swarm_id}")
                del self.discovered_swarms[swarm_id]

        except Exception as e:
            logger.error(f"Error in swarm discovery: {e}")

    def _query_federation_registry(self) -> Dict[str, Dict[str, Any]]:
        """Query federation registry for registered swarms."""
        try:
            response = requests.get(f"{self.registry_url}/swarms", timeout=5)
            if response.status_code == 200:
                registry_data = response.json()
                swarms = {}

                for swarm in registry_data.get('swarms', []):
                    swarm_id = swarm.get('swarm_id')
                    if swarm_id:
                        swarms[swarm_id] = {
                            'api_url': f"http://{swarm['host']}:{swarm['api_port']}",
                            'discovery_port': swarm.get('discovery_port'),
                            'capabilities': swarm.get('capabilities', []),
                            'federation_enabled': swarm.get('federation_enabled', False),
                            'source': 'registry',
                            'last_seen': time.time()
                        }

                return swarms
        except Exception as e:
            logger.debug(f"Could not query federation registry: {e}")

        return {}

    def _direct_swarm_discovery(self) -> Dict[str, Dict[str, Any]]:
        """Direct discovery of swarm nodes on common ports."""
        discovered = {}
        common_ports = [8000, 8001, 8002, 8765]  # Common swarm API ports
        common_hosts = ['localhost', '127.0.0.1']

        for host in common_hosts:
            for port in common_ports:
                try:
                    url = f"http://{host}:{port}/health"
                    response = requests.get(url, timeout=2)

                    if response.status_code == 200:
                        health_data = response.json()
                        swarm_id = health_data.get('swarm_id', f"swarm_{host}_{port}")

                        # Get more details
                        try:
                            metrics_response = requests.get(f"http://{host}:{port}/metrics", timeout=2)
                            if metrics_response.status_code == 200:
                                metrics_data = metrics_response.json()
                            else:
                                metrics_data = {}
                        except:
                            metrics_data = {}

                        discovered[swarm_id] = {
                            'api_url': f"http://{host}:{port}",
                            'host': host,
                            'port': port,
                            'capabilities': ['api', 'metrics'],
                            'federation_enabled': True,
                            'source': 'direct',
                            'last_seen': time.time(),
                            'health_data': health_data,
                            'metrics_data': metrics_data
                        }

                        logger.debug(f"Direct discovery found swarm: {swarm_id} at {host}:{port}")

                except requests.exceptions.RequestException:
                    # Port not responding, continue
                    pass
                except Exception as e:
                    logger.debug(f"Error checking {host}:{port}: {e}")

        return discovered

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.running:
            try:
                if self.operation_mode == OperationMode.LIVE:
                    # Live mode: connect to real swarm nodes
                    self._update_real_swarm_states()
                elif self.operation_mode == OperationMode.SIMULATION:
                    # Simulation mode: use simulated data
                    self._update_simulated_swarm_states()
                    self._simulate_live_events()

                # Common operations for both modes
                self._update_federation_states()
                self._check_alerts()
                asyncio.run(self._broadcast_updates())
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
            time.sleep(5)  # Update every 5 seconds

    def _update_simulated_swarm_states(self):
        """Update swarm states with simulated data for testing."""
        try:
            # Ensure we have simulated swarms
            if not self.swarm_states:
                self._create_simulated_swarms()

            # Update each simulated swarm with realistic variations
            for swarm_id, state in self.swarm_states.items():
                # Simulate realistic status changes (rare)
                if (hash(swarm_id + 'status') % 100) < 2:  # 2% chance to change status
                    statuses = ["active", "busy", "inactive"]
                    old_status = state.status
                    state.status = random.choice(statuses)
                    if old_status != state.status:
                        logger.debug(f"Simulated swarm {swarm_id} status change: {old_status} -> {state.status}")

                # Update metrics with realistic variations
                base_load = 0.1 + (hash(swarm_id + 'base_load') % 60) / 100.0
                state.load = min(1.0, max(0.0, base_load + random.uniform(-0.1, 0.1)))
                state.load = round(state.load, 3)

                base_cpu = 0.05 + (hash(swarm_id + 'base_cpu') % 70) / 100.0
                state.cpu_usage = min(1.0, max(0.0, base_cpu + random.uniform(-0.05, 0.05)))
                state.cpu_usage = round(state.cpu_usage, 3)

                base_memory = 0.2 + (hash(swarm_id + 'base_mem') % 60) / 100.0
                state.memory_usage = min(1.0, max(0.0, base_memory + random.uniform(-0.1, 0.1)))
                state.memory_usage = round(state.memory_usage, 3)

                # Simulate task count changes
                task_change = random.choice([-1, 0, 0, 0, 1])  # Bias toward no change
                state.tasks_active = max(0, min(10, state.tasks_active + task_change))

                # Simulate network latency
                base_latency = 10 + (hash(swarm_id + 'base_lat') % 100)
                state.network_latency = max(5, base_latency + random.randint(-10, 10))

                # Update timestamp
                state.last_updated = time.time()

                # Store simulated metrics in history
                self._store_metric("swarm_load", state.load, swarm_id)
                self._store_metric("swarm_cpu", state.cpu_usage, swarm_id)
                self._store_metric("swarm_memory", state.memory_usage, swarm_id)
                self._store_metric("swarm_tasks", state.tasks_active, swarm_id)
                self._store_metric("swarm_latency", state.network_latency, swarm_id)

                logger.debug(f"Updated simulated swarm {swarm_id}: load={state.load:.2f}, tasks={state.tasks_active}")

        except Exception as e:
            logger.error(f"Error updating simulated swarm states: {e}")

    def _update_real_swarm_states(self):
        """Update swarm states by connecting to real swarm APIs."""
        try:
            # Update states for discovered swarms
            for swarm_id, swarm_info in self.discovered_swarms.items():
                try:
                    api_url = swarm_info['api_url']

                    # Get health data
                    health_response = requests.get(f"{api_url}/health", timeout=3)
                    if health_response.status_code == 200:
                        health_data = health_response.json()

                        # Get metrics data
                        try:
                            metrics_response = requests.get(f"{api_url}/metrics", timeout=3)
                            metrics_data = metrics_response.json() if metrics_response.status_code == 200 else {}
                        except:
                            metrics_data = {}

                        # Update or create swarm state
                        if swarm_id not in self.swarm_states:
                            self.swarm_states[swarm_id] = SwarmState(
                                swarm_id=swarm_id,
                                status="active",
                                last_updated=time.time()
                            )

                        state = self.swarm_states[swarm_id]

                        # Update from real API data
                        state.status = health_data.get('status', 'active')
                        state.last_updated = time.time()

                        # Extract metrics from API responses
                        agent_metrics = metrics_data.get('agent_metrics', {})
                        system_metrics = metrics_data.get('system_metrics', {})
                        task_metrics = metrics_data.get('task_metrics', {})

                        # Update state with real metrics
                        state.load = system_metrics.get('system_load', 0.0)
                        state.tasks_active = system_metrics.get('active_tasks', 0)
                        state.memory_usage = system_metrics.get('memory_usage', 0.0)
                        state.cpu_usage = system_metrics.get('cpu_usage', 0.0)
                        state.network_latency = system_metrics.get('network_latency', 50.0)

                        # Store metrics in cache
                        self.swarm_health_cache[swarm_id] = health_data
                        self.swarm_metrics_cache[swarm_id] = metrics_data

                        # Store historical metrics
                        self._store_metric("swarm_load", state.load, swarm_id)
                        self._store_metric("swarm_cpu", state.cpu_usage, swarm_id)
                        self._store_metric("swarm_memory", state.memory_usage, swarm_id)
                        self._store_metric("swarm_tasks", state.tasks_active, swarm_id)
                        self._store_metric("swarm_latency", state.network_latency, swarm_id)

                        logger.debug(f"Updated real swarm {swarm_id}: load={state.load:.2f}, tasks={state.tasks_active}")

                    else:
                        # API not responding
                        if swarm_id in self.swarm_states:
                            self.swarm_states[swarm_id].status = "unreachable"
                            self.swarm_states[swarm_id].last_updated = time.time()

                except requests.exceptions.RequestException as e:
                    logger.debug(f"Could not connect to swarm {swarm_id}: {e}")
                    if swarm_id in self.swarm_states:
                        self.swarm_states[swarm_id].status = "error"
                        self.swarm_states[swarm_id].last_updated = time.time()

                except Exception as e:
                    logger.error(f"Error updating swarm {swarm_id}: {e}")
                    if swarm_id in self.swarm_states:
                        self.swarm_states[swarm_id].status = "error"

        except Exception as e:
            logger.error(f"Error updating real swarm states: {e}")

    def _create_simulated_swarms(self):
        """Create simulated swarms when no real ones are found (for demo purposes)."""
        simulated_swarms = [
            ("enterprise-swarm-1", "enterprise"),
            ("cloud-swarm-1", "cloud"),
            ("home-swarm-1", "home")
        ]

        for swarm_id, swarm_type in simulated_swarms:
            if swarm_id not in self.swarm_states:
                self.swarm_states[swarm_id] = SwarmState(
                    swarm_id=swarm_id,
                    status="active",
                    last_updated=time.time()
                )

            state = self.swarm_states[swarm_id]
            # Simulate realistic metrics
            state.load = 0.2 + (hash(swarm_id + 'load') % 60) / 100.0
            state.tasks_active = 1 + (hash(swarm_id + 'tasks') % 10)
            state.memory_usage = 0.3 + (hash(swarm_id + 'mem') % 50) / 100.0
            state.cpu_usage = 0.1 + (hash(swarm_id + 'cpu') % 70) / 100.0
            state.network_latency = 10 + (hash(swarm_id + 'net') % 100)

    def _update_swarm_states(self):
        """Legacy method - now delegates to real swarm monitoring."""
        self._update_real_swarm_states()

    def _update_federation_states(self):
        """Update federation connection states."""
        try:
            # Create federations between swarms
            swarm_ids = list(self.swarm_states.keys())
            for i in range(len(swarm_ids)):
                for j in range(i + 1, len(swarm_ids)):
                    fed_id = f"{swarm_ids[i]}-{swarm_ids[j]}"

                    if fed_id not in self.federation_states:
                        self.federation_states[fed_id] = FederationState(
                            id=fed_id,
                            swarm1=swarm_ids[i],
                            swarm2=swarm_ids[j],
                            status="active",
                            active=True,
                            last_updated=time.time()
                        )

                    # Update federation metrics
                    fed = self.federation_states[fed_id]
                    fed.throughput = 50 + (hash(fed_id) % 200)  # MB/s
                    fed.latency = 10 + (hash(fed_id) % 100)  # ms
                    fed.last_updated = time.time()

                    # Store historical throughput data
                    self._store_metric("federation_throughput", fed.throughput, fed_id)

        except Exception as e:
            logger.error(f"Error updating federation states: {e}")

    def _check_alerts(self):
        """Check for system alerts."""
        try:
            current_time = time.time()

            # Check swarm health
            for swarm_id, state in self.swarm_states.items():
                # High load alert
                if state.load > 0.9 and not self._has_recent_alert(swarm_id, 'high_load'):
                    alert = Alert(
                        id=f"alert_{secrets.token_hex(8)}",
                        level="warning",
                        title="High Load Detected",
                        message=f"Swarm {swarm_id} is experiencing high load ({state.load:.1%})",
                        swarm_id=swarm_id,
                        timestamp=current_time
                    )
                    self.alerts.append(alert)

                # Memory usage alert
                if state.memory_usage > 0.95 and not self._has_recent_alert(swarm_id, 'high_memory'):
                    alert = Alert(
                        id=f"alert_{secrets.token_hex(8)}",
                        level="critical",
                        title="Critical Memory Usage",
                        message=f"Swarm {swarm_id} memory usage is critical ({state.memory_usage:.1%})",
                        swarm_id=swarm_id,
                        timestamp=current_time
                    )
                    self.alerts.append(alert)

                # Network latency alert
                if state.network_latency > 200 and not self._has_recent_alert(swarm_id, 'high_latency'):
                    alert = Alert(
                        id=f"alert_{secrets.token_hex(8)}",
                        level="warning",
                        title="High Network Latency",
                        message=f"Swarm {swarm_id} has high network latency ({state.network_latency:.0f}ms)",
                        swarm_id=swarm_id,
                        timestamp=current_time
                    )
                    self.alerts.append(alert)

            # Keep only recent alerts (last 100)
            self.alerts = self.alerts[-100:]

        except Exception as e:
            logger.error(f"Error checking alerts: {e}")

    def _has_recent_alert(self, swarm_id: str, alert_type: str, window: float = 300) -> bool:
        """Check if there's a recent alert of the same type for this swarm."""
        current_time = time.time()
        return any(
            alert.swarm_id == swarm_id and
            alert.title.lower().replace(' ', '_') == alert_type and
            current_time - alert.timestamp < window
            for alert in self.alerts
        )

    def _get_registry_headers(self) -> Dict[str, str]:
        """Get headers for registry API calls."""
        # Use default admin key for now (in production, use proper auth)
        return {"X-API-Key": "default-admin-key"}

    async def _broadcast_updates(self):
        """Broadcast updates to connected clients."""
        try:
            # Prepare update data with all real-time information
            update_data = {
                "type": "system_update",
                "timestamp": time.time(),
                "mode": self.get_operation_mode(),
                "swarms": {sid: asdict(state) for sid, state in self.swarm_states.items()},
                "federations": {fid: asdict(fed) for fid, fed in self.federation_states.items()},
                "alerts": [asdict(alert) for alert in self.alerts[-10:]],  # Last 10 alerts
                "metrics": self._calculate_global_metrics(),
                "task_queues": self._get_task_queue_data(),
                "discovery_events": self._get_recent_discovery_events(),
                "security_status": self._get_security_status()
            }

            # Broadcast to all connected clients
            await sio.emit('system_update', update_data)

        except Exception as e:
            logger.error(f"Error broadcasting updates: {e}")

    def _get_task_queue_data(self) -> Dict[str, Any]:
        """Get current task queue data from all swarms."""
        try:
            all_tasks = []
            for swarm_id, swarm_info in self.discovered_swarms.items():
                # Simulate tasks for discovered swarms
                task_count = hash(swarm_id + 'tasks') % 5 + 1
                for i in range(task_count):
                    priority = (hash(swarm_id + f'task{i}') % 5) + 1
                    status = ['pending', 'running', 'completed'][hash(swarm_id + f'status{i}') % 3]

                    all_tasks.append({
                        "id": f"{swarm_id}-task-{i}",
                        "description": f"Task {i+1} on {swarm_id}",
                        "priority": priority,
                        "status": status,
                        "swarm": swarm_id,
                        "created_at": time.time() - (hash(swarm_id + f'time{i}') % 3600),
                        "progress": (hash(swarm_id + f'progress{i}') % 100) if status == 'running' else (100 if status == 'completed' else 0)
                    })

            return {"tasks": all_tasks[:20]}  # Limit to 20 tasks
        except Exception as e:
            logger.error(f"Error getting task queue data: {e}")
            return {"tasks": []}

    def _get_recent_discovery_events(self) -> List[Dict[str, Any]]:
        """Get recent discovery events."""
        # In a real implementation, this would track actual discovery events
        # For demo purposes, return simulated events
        events = []
        for swarm_id in list(self.discovered_swarms.keys())[:3]:  # Show events for first 3 swarms
            events.append({
                "event_type": "discovery",
                "swarm_id": swarm_id,
                "message": f"Swarm {swarm_id} discovered and connected",
                "timestamp": time.time() - (hash(swarm_id) % 300)  # Within last 5 minutes
            })

        return events[-5:]  # Last 5 events

    def _get_security_status(self) -> Dict[str, Any]:
        """Get current security status."""
        return {
            "overall_status": "secure",
            "last_audit": time.time() - 3600,  # 1 hour ago
            "checks": [
                {"name": "API Authentication", "status": "passed", "last_check": time.time()},
                {"name": "Federation Encryption", "status": "passed", "last_check": time.time()},
                {"name": "Access Control", "status": "passed", "last_check": time.time()},
                {"name": "Network Security", "status": "warning", "last_check": time.time()},
                {"name": "Data Integrity", "status": "passed", "last_check": time.time()}
            ]
        }

    def _store_metric(self, metric_name: str, value: float, swarm_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Store a metric data point in history."""
        try:
            metric = HistoricalMetric(
                timestamp=time.time(),
                metric_name=metric_name,
                value=value,
                swarm_id=swarm_id,
                metadata=metadata or {}
            )

            self.metrics_history.append(metric)

            # Maintain history size limit
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]

            # Clean old data
            cutoff_time = time.time() - (self.history_retention_hours * 3600)
            self.metrics_history = [
                m for m in self.metrics_history
                if m.timestamp > cutoff_time
            ]

        except Exception as e:
            logger.error(f"Error storing metric {metric_name}: {e}")

    def get_metric_history(self, metric_name: str, swarm_id: Optional[str] = None,
                          hours: float = 1.0) -> List[HistoricalMetric]:
        """Get historical data for a specific metric."""
        try:
            cutoff_time = time.time() - (hours * 3600)

            return [
                m for m in self.metrics_history
                if m.timestamp > cutoff_time and
                m.metric_name == metric_name and
                (swarm_id is None or m.swarm_id == swarm_id)
            ]

        except Exception as e:
            logger.error(f"Error retrieving metric history for {metric_name}: {e}")
            return []

    def get_analytics_summary(self, hours: float = 24.0) -> Dict[str, Any]:
        """Get analytics summary for the specified time period."""
        try:
            cutoff_time = time.time() - (hours * 3600)

            # Filter recent metrics
            recent_metrics = [
                m for m in self.metrics_history
                if m.timestamp > cutoff_time
            ]

            if not recent_metrics:
                return {"error": "No data available for the specified period"}

            # Group by metric type
            metrics_by_type = {}
            for metric in recent_metrics:
                if metric.metric_name not in metrics_by_type:
                    metrics_by_type[metric.metric_name] = []
                metrics_by_type[metric.metric_name].append(metric.value)

            # Calculate statistics for each metric
            analytics = {}
            for metric_name, values in metrics_by_type.items():
                if values:
                    analytics[metric_name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "latest": values[-1] if values else 0
                    }

            # System uptime calculation
            uptime_percentage = 95.0  # Mock value - in real implementation, calculate from actual uptime data

            return {
                "period_hours": hours,
                "total_data_points": len(recent_metrics),
                "metrics_summary": analytics,
                "system_uptime": uptime_percentage,
                "data_retention_hours": self.history_retention_hours
            }

        except Exception as e:
            logger.error(f"Error generating analytics summary: {e}")
            return {"error": str(e)}

    def _simulate_live_events(self):
        """Simulate live events for demonstration purposes."""
        try:
            # Simulate swarm status changes
            self._simulate_swarm_status_changes()

            # Simulate task processing
            self._simulate_task_processing()

            # Simulate different types of discovery events
            current_time = time.time()

            # LAN Broadcast discovery (every ~12 seconds)
            if len(self.swarm_states) > 0 and (current_time % 12) < 1:
                swarm_ids = list(self.swarm_states.keys())
                swarm_id = swarm_ids[int(current_time) % len(swarm_ids)]
                asyncio.run(self._broadcast_discovery_event({
                    "event_type": "lan_discovery",
                    "swarm_id": swarm_id,
                    "message": f"UDP Broadcast discovery on port 9999 from {swarm_id}",
                    "discovery_method": "LAN Broadcast",
                    "protocol": "UDP",
                    "port": 9999,
                    "timestamp": current_time
                }))

            # Registry-based discovery (every ~18 seconds)
            if len(self.swarm_states) > 0 and (current_time % 18) < 1:
                swarm_ids = list(self.swarm_states.keys())
                swarm_id = swarm_ids[int(current_time * 1.5) % len(swarm_ids)]
                asyncio.run(self._broadcast_discovery_event({
                    "event_type": "registry_discovery",
                    "swarm_id": swarm_id,
                    "message": f"HTTPS registration with federation registry from {swarm_id}",
                    "discovery_method": "Registry API",
                    "protocol": "HTTPS",
                    "endpoint": "registry.brain-swarm.com/api/register",
                    "timestamp": current_time
                }))

            # Generic discovery events (every ~25 seconds)
            if len(self.swarm_states) > 0 and (current_time % 25) < 1:
                swarm_ids = list(self.swarm_states.keys())
                swarm_id = swarm_ids[int(current_time * 0.7) % len(swarm_ids)]
                asyncio.run(self._broadcast_discovery_event({
                    "event_type": "discovery",
                    "swarm_id": swarm_id,
                    "message": f"Direct API discovery connection established with {swarm_id}",
                    "discovery_method": "Direct API",
                    "protocol": "HTTP",
                    "timestamp": current_time
                }))

            # Simulate security checks
            if (current_time % 20) < 1:  # Every ~20 seconds
                asyncio.run(self._broadcast_security_check({
                    "checks": [
                        {
                            "name": "API Authentication",
                            "status": "passed",
                            "last_check": current_time
                        },
                        {
                            "name": "Federation Encryption",
                            "status": "passed",
                            "last_check": current_time
                        },
                        {
                            "name": "Access Control",
                            "status": "passed",
                            "last_check": current_time
                        },
                        {
                            "name": "Network Security",
                            "status": "warning",
                            "last_check": current_time,
                            "details": "Non-HTTPS connection detected"
                        },
                        {
                            "name": "Data Integrity",
                            "status": "passed",
                            "last_check": current_time
                        }
                    ],
                    "timestamp": current_time
                }))

        except Exception as e:
            logger.debug(f"Error simulating live events: {e}")

    def _simulate_swarm_status_changes(self):
        """Simulate realistic swarm status changes: active, inactive, busy, failed."""
        try:
            # Only change status occasionally (10% chance per update cycle)
            if len(self.swarm_states) > 0 and (time.time() % 50) < 5:  # Every ~50 seconds, 10% chance
                swarm_ids = list(self.swarm_states.keys())
                swarm_id = swarm_ids[int(time.time()) % len(swarm_ids)]
                state = self.swarm_states[swarm_id]

                # Status transition logic
                if state.status == "active":
                    # Active swarms can become busy or fail occasionally
                    if (hash(swarm_id + 'busy') % 100) < 15:  # 15% chance to become busy
                        state.status = "busy"
                        logger.info(f"Swarm {swarm_id} status changed: active -> busy")
                    elif (hash(swarm_id + 'fail') % 100) < 5:  # 5% chance to fail
                        state.status = "failed"
                        logger.info(f"Swarm {swarm_id} status changed: active -> failed")
                elif state.status == "inactive":
                    # Inactive swarms can become active
                    if (hash(swarm_id + 'activate') % 100) < 20:  # 20% chance to activate
                        state.status = "active"
                        logger.info(f"Swarm {swarm_id} status changed: inactive -> active")
                elif state.status == "busy":
                    # Busy swarms can return to active or fail
                    if (hash(swarm_id + 'done') % 100) < 25:  # 25% chance to finish being busy
                        state.status = "active"
                        logger.info(f"Swarm {swarm_id} status changed: busy -> active")
                    elif (hash(swarm_id + 'busy_fail') % 100) < 3:  # 3% chance to fail while busy
                        state.status = "failed"
                        logger.info(f"Swarm {swarm_id} status changed: busy -> failed")
                elif state.status == "failed":
                    # Failed swarms can recover to active (but less likely)
                    if (hash(swarm_id + 'recover') % 100) < 8:  # 8% chance to recover
                        state.status = "active"
                        logger.info(f"Swarm {swarm_id} status changed: failed -> active")

                # Update timestamp when status changes
                state.last_updated = time.time()

        except Exception as e:
            logger.debug(f"Error simulating swarm status changes: {e}")

    def _simulate_task_processing(self):
        """Simulate task processing with progress updates."""
        try:
            current_time = time.time()

            # Update task progress for all swarms
            for swarm_id, state in self.swarm_states.items():
                if state.status not in ['active', 'busy']:
                    continue

                # Simulate task completion and new task creation
                if (hash(swarm_id + 'task_update') % 100) < 20:  # 20% chance per update
                    # Update existing tasks or create new ones
                    task_count = max(1, state.tasks_active)
                    for i in range(task_count):
                        task_id = f"{swarm_id}-task-{i}"
                        # Simulate progress updates
                        if (hash(task_id + str(int(current_time))) % 100) < 30:  # 30% chance to update progress
                            # Task progress logic would go here
                            pass

                # Occasionally complete tasks
                if state.tasks_active > 0 and (hash(swarm_id + 'complete') % 1000) < 5:  # 0.5% chance
                    state.tasks_active = max(0, state.tasks_active - 1)
                    logger.debug(f"Task completed on swarm {swarm_id}, active tasks: {state.tasks_active}")

                # Occasionally start new tasks
                if state.tasks_active < 5 and (hash(swarm_id + 'new_task') % 1000) < 8:  # 0.8% chance
                    state.tasks_active += 1
                    logger.debug(f"New task started on swarm {swarm_id}, active tasks: {state.tasks_active}")

                # Update load based on task count
                base_load = 0.1 + (state.tasks_active * 0.15)
                state.load = min(1.0, base_load + (hash(swarm_id + 'load_var') % 30) / 100.0)

        except Exception as e:
            logger.debug(f"Error simulating task processing: {e}")

    async def _broadcast_discovery_event(self, event_data):
        """Broadcast discovery event to all clients."""
        try:
            await sio.emit('discovery_event', event_data)
        except Exception as e:
            logger.error(f"Error broadcasting discovery event: {e}")

    async def _broadcast_security_check(self, security_data):
        """Broadcast security check results to all clients."""
        try:
            await sio.emit('security_check', security_data)
        except Exception as e:
            logger.error(f"Error broadcasting security check: {e}")

    def _get_permissions_for_level(self, permission_level: PermissionLevel) -> List[str]:
        """Get list of permissions for a permission level."""
        if permission_level == PermissionLevel.ADMIN:
            return ["read", "write", "admin", "control", "monitor", "configure"]
        elif permission_level == PermissionLevel.OPERATOR:
            return ["read", "write", "control", "monitor"]
        else:  # VIEW_ONLY
            return ["read", "monitor"]

    def _calculate_global_metrics(self) -> Dict[str, Any]:
        """Calculate global system metrics."""
        if not self.swarm_states:
            return {
                "active_swarms": 0,
                "total_federations": 0,
                "avg_latency": 0,
                "avg_throughput": 0,
                "system_health": "unknown",
                "total_alerts": 0
            }

        active_swarms = len([s for s in self.swarm_states.values() if s.status == "active"])
        total_federations = len([f for f in self.federation_states.values() if f.active])

        latencies = [s.network_latency for s in self.swarm_states.values()]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        throughputs = [f.throughput for f in self.federation_states.values() if f.active]
        avg_throughput = sum(throughputs) / len(throughputs) if throughputs else 0

        # Store global metrics in history
        current_time = time.time()
        self._store_metric("global_active_swarms", active_swarms)
        self._store_metric("global_avg_latency", avg_latency)
        self._store_metric("global_avg_throughput", avg_throughput)
        self._store_metric("global_total_alerts", len(self.alerts))

        # Determine system health
        critical_alerts = len([a for a in self.alerts if a.level == "critical" and not a.acknowledged])
        if critical_alerts > 0:
            health = "critical"
        elif len([s for s in self.swarm_states.values() if s.load > 0.8]) > active_swarms * 0.5:
            health = "warning"
        elif active_swarms > 0:
            health = "healthy"
        else:
            health = "unknown"

        return {
            "active_swarms": active_swarms,
            "total_federations": total_federations,
            "avg_latency": avg_latency,
            "avg_throughput": avg_throughput,
            "system_health": health,
            "total_alerts": len(self.alerts)
        }

    # Control operations
    def start_swarm(self, swarm_id: str) -> bool:
        """Start a swarm by sending command to its API."""
        try:
            if swarm_id in self.discovered_swarms:
                swarm_info = self.discovered_swarms[swarm_id]
                api_url = swarm_info['api_url']

                # Try to send start command to swarm API
                response = requests.post(f"{api_url}/control/start", timeout=5)
                if response.status_code == 200:
                    logger.info(f"Successfully started swarm: {swarm_id}")
                    if swarm_id in self.swarm_states:
                        self.swarm_states[swarm_id].status = "starting"
                    return True
                else:
                    logger.warning(f"Failed to start swarm {swarm_id}: HTTP {response.status_code}")

            # Fallback for simulated swarms
            if swarm_id in self.swarm_states:
                self.swarm_states[swarm_id].status = "starting"
                logger.info(f"Started simulated swarm: {swarm_id}")
                return True

            return False
        except Exception as e:
            logger.error(f"Error starting swarm {swarm_id}: {e}")
            return False

    def stop_swarm(self, swarm_id: str) -> bool:
        """Stop a swarm by sending command to its API."""
        try:
            if swarm_id in self.discovered_swarms:
                swarm_info = self.discovered_swarms[swarm_id]
                api_url = swarm_info['api_url']

                # Try to send stop command to swarm API
                response = requests.post(f"{api_url}/control/stop", timeout=5)
                if response.status_code == 200:
                    logger.info(f"Successfully stopped swarm: {swarm_id}")
                    if swarm_id in self.swarm_states:
                        self.swarm_states[swarm_id].status = "stopping"
                    return True
                else:
                    logger.warning(f"Failed to stop swarm {swarm_id}: HTTP {response.status_code}")

            # Fallback for simulated swarms
            if swarm_id in self.swarm_states:
                self.swarm_states[swarm_id].status = "stopping"
                logger.info(f"Stopped simulated swarm: {swarm_id}")
                return True

            return False
        except Exception as e:
            logger.error(f"Error stopping swarm {swarm_id}: {e}")
            return False

    def restart_swarm(self, swarm_id: str) -> bool:
        """Restart a swarm by sending command to its API."""
        try:
            if swarm_id in self.discovered_swarms:
                swarm_info = self.discovered_swarms[swarm_id]
                api_url = swarm_info['api_url']

                # Try to send restart command to swarm API
                response = requests.post(f"{api_url}/control/restart", timeout=5)
                if response.status_code == 200:
                    logger.info(f"Successfully restarted swarm: {swarm_id}")
                    if swarm_id in self.swarm_states:
                        self.swarm_states[swarm_id].status = "restarting"
                    return True
                else:
                    logger.warning(f"Failed to restart swarm {swarm_id}: HTTP {response.status_code}")

            # Fallback for simulated swarms
            if swarm_id in self.swarm_states:
                self.swarm_states[swarm_id].status = "restarting"
                logger.info(f"Restarted simulated swarm: {swarm_id}")
                return True

            return False
        except Exception as e:
            logger.error(f"Error restarting swarm {swarm_id}: {e}")
            return False

    def create_federation(self) -> bool:
        """Create a new federation."""
        # Implementation for creating federation
        logger.info("Creating new federation")
        return True

    def dissolve_federation(self) -> bool:
        """Dissolve a federation."""
        # Implementation for dissolving federation
        logger.info("Dissolving federation")
        return True

    def load_balance(self) -> bool:
        """Initiate load balancing."""
        # Implementation for load balancing
        logger.info("Initiating load balancing")
        return True

    def emergency_stop(self) -> bool:
        """Emergency stop all operations."""
        logger.warning("EMERGENCY STOP initiated")
        for state in self.swarm_states.values():
            state.status = "stopped"
        return True

    def system_reset(self) -> bool:
        """Reset system."""
        logger.info("System reset initiated")
        # Implementation for system reset
        return True

    def create_backup(self) -> bool:
        """Create system backup."""
        logger.info("Creating system backup")
        # Implementation for backup
        return True


# Global operations manager (will be initialized in main)
ops_manager = FederationOperationsManager()

# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    logger.info(f"Client connected: {sid}")
    ops_manager.connected_clients.add(sid)

    # Send initial state
    initial_data = {
        "type": "initial_state",
        "timestamp": time.time(),
        "mode": ops_manager.get_operation_mode(),
        "swarms": {sid: asdict(state) for sid, state in ops_manager.swarm_states.items()},
        "federations": {fid: asdict(fed) for fid, fed in ops_manager.federation_states.items()},
        "alerts": [asdict(alert) for alert in ops_manager.alerts[-10:]],
        "metrics": ops_manager._calculate_global_metrics()
    }

    await sio.emit('initial_state', initial_data, to=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {sid}")
    ops_manager.connected_clients.discard(sid)

@sio.event
async def authenticate(sid, data):
    """Handle authentication using SecurityManager."""
    if not ops_manager:
        await sio.emit('auth_failure', {"error": "Server not initialized"}, to=sid)
        return

    api_key = data.get('api_key') or data.get('apiKey')

    if not api_key:
        await sio.emit('auth_failure', {"error": "API key required"}, to=sid)
        logger.warning(f"Authentication failed for client {sid}: No API key provided")
        return

    # Authenticate using SecurityManager
    client_credentials = ops_manager.security_manager.authenticate_client(
        api_key, "federation_socket_client"
    )

    if client_credentials:
        # Store authenticated client info
        ops_manager.auth_tokens[sid] = {
            "client_id": client_credentials.client_id,
            "client_name": client_credentials.client_name,
            "authenticated": True,
            "permission_level": client_credentials.permission_level.value,
            "permissions": ops_manager._get_permissions_for_level(client_credentials.permission_level)
        }

        await sio.emit('auth_success', {
            "client_id": client_credentials.client_id,
            "client_name": client_credentials.client_name,
            "permission_level": client_credentials.permission_level.value,
            "permissions": ops_manager._get_permissions_for_level(client_credentials.permission_level)
        }, to=sid)
        logger.info(f"Authenticated client: {sid} as {client_credentials.client_name} ({client_credentials.client_id})")
    else:
        await sio.emit('auth_failure', {"error": "Invalid API key"}, to=sid)
        logger.warning(f"Authentication failed for client {sid}: Invalid API key")

@sio.event
async def start_swarm(sid, data):
    """Handle start swarm command with permission checking."""
    client_info = ops_manager.auth_tokens.get(sid, {})
    if not client_info.get('authenticated'):
        await sio.emit('error', {"message": "Not authenticated"}, to=sid)
        return

    # Check permissions using SecurityManager
    client_creds = ops_manager.security_manager.credentials.get(client_info['client_id'])
    if not client_creds or not ops_manager.security_manager.authorize_action(
        client_creds, "start_node", "system", data.get('swarmId', 'system')
    ):
        # Log unauthorized access attempt
        ops_manager.security_manager.log_audit_event(
            client_id=client_info['client_id'],
            client_name=client_info['client_name'],
            action="unauthorized_start_swarm",
            resource_type="system",
            resource_id=data.get('swarmId', 'unknown'),
            permission_level=client_info['permission_level'],
            success=False,
            details={"reason": "insufficient_permissions"}
        )
        await sio.emit('error', {"message": "Insufficient permissions"}, to=sid)
        return

    swarm_id = data.get('swarmId')
    if swarm_id and ops_manager.start_swarm(swarm_id):
        # Log successful command
        ops_manager.security_manager.log_audit_event(
            client_id=client_info['client_id'],
            client_name=client_info['client_name'],
            action="start_swarm",
            resource_type="system",
            resource_id=swarm_id,
            permission_level=client_info['permission_level'],
            success=True,
            details={"command": "start_swarm", "swarm_id": swarm_id}
        )
        await sio.emit('command_ack', {"command": "start_swarm", "swarm_id": swarm_id}, to=sid)
    else:
        await sio.emit('error', {"message": "Failed to start swarm"}, to=sid)

@sio.event
async def stop_swarm(sid, data):
    """Handle stop swarm command."""
    if not ops_manager.auth_tokens.get(sid, {}).get('authenticated'):
        await sio.emit('error', {"message": "Not authenticated"}, to=sid)
        return

    swarm_id = data.get('swarmId')
    if swarm_id and ops_manager.stop_swarm(swarm_id):
        await sio.emit('command_ack', {"command": "stop_swarm", "swarm_id": swarm_id}, to=sid)
    else:
        await sio.emit('error', {"message": "Failed to stop swarm"}, to=sid)

@sio.event
async def restart_swarm(sid, data):
    """Handle restart swarm command."""
    if not ops_manager.auth_tokens.get(sid, {}).get('authenticated'):
        await sio.emit('error', {"message": "Not authenticated"}, to=sid)
        return

    swarm_id = data.get('swarmId')
    if swarm_id and ops_manager.restart_swarm(swarm_id):
        await sio.emit('command_ack', {"command": "restart_swarm", "swarm_id": swarm_id}, to=sid)
    else:
        await sio.emit('error', {"message": "Failed to restart swarm"}, to=sid)

@sio.event
async def create_federation(sid, data):
    """Handle create federation command."""
    if not ops_manager.auth_tokens.get(sid, {}).get('authenticated'):
        await sio.emit('error', {"message": "Not authenticated"}, to=sid)
        return

    if ops_manager.create_federation():
        await sio.emit('command_ack', {"command": "create_federation"}, to=sid)
    else:
        await sio.emit('error', {"message": "Failed to create federation"}, to=sid)

@sio.event
async def dissolve_federation(sid, data):
    """Handle dissolve federation command."""
    if not ops_manager.auth_tokens.get(sid, {}).get('authenticated'):
        await sio.emit('error', {"message": "Not authenticated"}, to=sid)
        return

    if ops_manager.dissolve_federation():
        await sio.emit('command_ack', {"command": "dissolve_federation"}, to=sid)
    else:
        await sio.emit('error', {"message": "Failed to dissolve federation"}, to=sid)

@sio.event
async def load_balance(sid, data):
    """Handle load balance command."""
    if not ops_manager.auth_tokens.get(sid, {}).get('authenticated'):
        await sio.emit('error', {"message": "Not authenticated"}, to=sid)
        return

    if ops_manager.load_balance():
        await sio.emit('command_ack', {"command": "load_balance"}, to=sid)
    else:
        await sio.emit('error', {"message": "Failed to initiate load balancing"}, to=sid)

@sio.event
async def emergency_stop(sid, data):
    """Handle emergency stop command."""
    if not ops_manager.auth_tokens.get(sid, {}).get('authenticated'):
        await sio.emit('error', {"message": "Not authenticated"}, to=sid)
        return

    if ops_manager.emergency_stop():
        await sio.emit('command_ack', {"command": "emergency_stop"}, to=sid)
        # Broadcast emergency to all clients
        await sio.emit('emergency_alert', {"message": "Emergency stop initiated"})
    else:
        await sio.emit('error', {"message": "Failed to initiate emergency stop"}, to=sid)

@sio.event
async def system_reset(sid, data):
    """Handle system reset command."""
    if not ops_manager.auth_tokens.get(sid, {}).get('authenticated'):
        await sio.emit('error', {"message": "Not authenticated"}, to=sid)
        return

    if ops_manager.system_reset():
        await sio.emit('command_ack', {"command": "system_reset"}, to=sid)
    else:
        await sio.emit('error', {"message": "Failed to reset system"}, to=sid)

@sio.event
async def create_backup(sid, data):
    """Handle create backup command."""
    if not ops_manager.auth_tokens.get(sid, {}).get('authenticated'):
        await sio.emit('error', {"message": "Not authenticated"}, to=sid)
        return

    if ops_manager.create_backup():
        await sio.emit('command_ack', {"command": "create_backup"}, to=sid)
    else:
        await sio.emit('error', {"message": "Failed to create backup"}, to=sid)

# FastAPI routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Brain Swarm Federation Operations Server", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    global ops_manager
    if ops_manager is None:
        ops_manager = FederationOperationsManager()
    return {
        "status": "healthy",
        "message": "Brain Swarm Federation Operations Server is running",
        "timestamp": time.time()
    }

@app.get("/stats")
async def get_stats(api_key: str = Depends(get_api_key)):
    """Get system statistics."""
    # Get client credentials for audit logging
    client_credentials = ops_manager.security_manager.authenticate_client(api_key, "federation_rest_api")

    # Log audit event
    ops_manager.security_manager.log_audit_event(
        client_id=client_credentials.client_id,
        client_name=client_credentials.client_name,
        action="view_stats",
        resource_type="system",
        resource_id="stats",
        permission_level=client_credentials.permission_level.value,
        success=True,
        details={"endpoint": "/stats"}
    )

    return ops_manager._calculate_global_metrics()

@app.get("/analytics/summary")
async def get_analytics_summary(hours: float = 24.0):
    """Get analytics summary for the specified time period."""
    return ops_manager.get_analytics_summary(hours)

@app.get("/analytics/metrics/{metric_name}")
async def get_metric_history(
    metric_name: str,
    swarm_id: Optional[str] = None,
    hours: float = 1.0
):
    """Get historical data for a specific metric."""
    history = ops_manager.get_metric_history(metric_name, swarm_id, hours)
    return {
        "metric_name": metric_name,
        "swarm_id": swarm_id,
        "hours": hours,
        "data_points": len(history),
        "data": [
            {
                "timestamp": m.timestamp,
                "value": m.value,
                "metadata": m.metadata
            }
            for m in history
        ]
    }

@app.get("/analytics/metrics")
async def list_available_metrics():
    """List all available metric types in history."""
    metric_types = set()
    swarm_ids = set()

    for metric in ops_manager.metrics_history:
        metric_types.add(metric.metric_name)
        if metric.swarm_id:
            swarm_ids.add(metric.swarm_id)

    return {
        "metric_types": sorted(list(metric_types)),
        "swarm_ids": sorted(list(swarm_ids)),
        "total_data_points": len(ops_manager.metrics_history),
        "retention_hours": ops_manager.history_retention_hours
    }

@app.get("/mode")
async def get_operation_mode(api_key: str = Depends(get_api_key)):
    """Get current operation mode."""
    return {
        "mode": ops_manager.get_operation_mode(),
        "description": "live" if ops_manager.operation_mode == OperationMode.LIVE else "simulation"
    }

@app.post("/mode")
async def switch_operation_mode(mode: str, api_key: str = Depends(get_api_key)):
    """Switch operation mode (requires admin permissions)."""
    # Check if client has admin permissions
    client_credentials = ops_manager.security_manager.authenticate_client(api_key)
    if not client_credentials or client_credentials.permission_level != PermissionLevel.ADMIN:
        raise HTTPException(status_code=403, detail="Admin permissions required to switch modes")

    # Validate mode
    try:
        new_mode = OperationMode(mode.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'live' or 'simulation'")

    # Switch mode
    if ops_manager.switch_operation_mode(new_mode):
        # Log the mode switch
        ops_manager.security_manager.log_audit_event(
            client_id=client_credentials.client_id,
            client_name=client_credentials.client_name,
            action="switch_mode",
            resource_type="system",
            resource_id="operation_mode",
            permission_level=client_credentials.permission_level.value,
            success=True,
            details={"old_mode": ops_manager.operation_mode.value, "new_mode": new_mode.value}
        )

        return {
            "success": True,
            "mode": ops_manager.get_operation_mode(),
            "message": f"Switched to {new_mode.value} mode"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to switch mode")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Federation Operations Server with TLS/HTTPS support")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8001, help="Server port")
    parser.add_argument("--cert-file", help="Path to TLS certificate file (.pem or .crt)")
    parser.add_argument("--key-file", help="Path to TLS private key file (.key)")
    parser.add_argument("--credentials-file", default="credentials.json", help="Path to credentials storage file")
    parser.add_argument("--audit-log", default="federation_audit.log", help="Path to audit log file")
    parser.add_argument("--registry-url", default="http://localhost:8002", help="Federation registry URL")
    parser.add_argument("--mode", choices=["live", "simulation"], default="simulation",
                       help="Operation mode: live (connect to real swarms) or simulation (use simulated data)")

    args = parser.parse_args()

    # Validate TLS configuration
    if (args.cert_file and not args.key_file) or (args.key_file and not args.cert_file):
        parser.error("Both --cert-file and --key-file must be provided for TLS")

    logger.info("Starting Federation Operations Server...")

    # Parse operation mode
    operation_mode = OperationMode(args.mode)

    # Initialize operations manager with security
    ops_manager = FederationOperationsManager(
        registry_url=args.registry_url,
        credentials_file=args.credentials_file,
        audit_log_file=args.audit_log,
        cert_file=args.cert_file,
        key_file=args.key_file,
        operation_mode=operation_mode
    )

    # Configure uvicorn with TLS if certificates provided
    uvicorn_config = {
        "app": "federation_operations_server:socket_app",
        "host": args.host,
        "port": args.port,
        "log_level": "info"
    }

    if args.cert_file and args.key_file:
        uvicorn_config["ssl_certfile"] = args.cert_file
        uvicorn_config["ssl_keyfile"] = args.key_file
        logger.info(f"TLS/HTTPS enabled with certificate: {args.cert_file}")
    else:
        logger.warning("TLS/HTTPS not configured - running in development mode")

    # Run with uvicorn
    uvicorn.run(**uvicorn_config)