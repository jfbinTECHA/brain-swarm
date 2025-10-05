#!/usr/bin/env python3
"""
Real-Time Swarm Monitor WebSocket Server
Provides live monitoring data for swarm nodes, tasks, security events, and performance metrics.
Standalone version without complex dependencies.
"""

import asyncio
import json
import random
import time
import websockets
from typing import Dict, List, Any, Set, Optional
import threading
import logging
from collections import defaultdict
import aiohttp
from aiohttp import web
import ssl
from .security import SecurityManager, PermissionLevel
from .event_aggregation import EventAggregationService, EventType, EventPriority

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CentralEventBus:
    """Central event aggregation and distribution system"""

    def __init__(self):
        self.subscribers: Dict[str, Set] = defaultdict(set)  # event_type -> set of subscriber functions
        self.event_history: Dict[str, List] = defaultdict(list)  # event_type -> list of recent events
        self.max_history = 100  # Maximum events to keep per type
        self.event_stats = defaultdict(int)  # Track event counts

    def subscribe(self, event_type: str, callback):
        """Subscribe to events of a specific type"""
        self.subscribers[event_type].add(callback)
        logger.info(f"Subscribed to {event_type} events")

    def unsubscribe(self, event_type: str, callback):
        """Unsubscribe from events"""
        self.subscribers[event_type].discard(callback)

    def publish(self, event_type: str, event_data: Dict[str, Any]):
        """Publish an event to all subscribers"""
        # Add metadata
        enriched_event = {
            **event_data,
            "event_type": event_type,
            "timestamp": time.time(),
            "source": event_data.get("source", "unknown")
        }

        # Store in history
        self.event_history[event_type].append(enriched_event)
        if len(self.event_history[event_type]) > self.max_history:
            self.event_history[event_type].pop(0)

        # Update stats
        self.event_stats[event_type] += 1

        # Notify subscribers
        for callback in self.subscribers[event_type]:
            try:
                asyncio.create_task(callback(enriched_event))
            except Exception as e:
                logger.error(f"Error in event callback: {e}")

        logger.debug(f"Published {event_type} event: {enriched_event}")

    def get_recent_events(self, event_type: str, limit: int = 10) -> List[Dict]:
        """Get recent events of a specific type"""
        return list(self.event_history[event_type])[-limit:]

    def get_event_stats(self) -> Dict[str, int]:
        """Get event statistics"""
        return dict(self.event_stats)

    def clear_history(self, event_type: str = None):
        """Clear event history"""
        if event_type:
            self.event_history[event_type].clear()
        else:
            self.event_history.clear()

class SwarmMonitorServer:
    """Enhanced WebSocket and REST API server for real-time swarm monitoring data with security"""

    def __init__(self, host: str = "localhost", ws_port: int = 8001, rest_port: int = 8002,
                 cert_file: Optional[str] = None, key_file: Optional[str] = None,
                 credentials_file: str = "credentials.json", audit_log_file: str = "audit.log",
                 enable_aggregation: bool = True, max_aggregation_queue: int = 100000):
        self.host = host
        self.ws_port = ws_port
        self.rest_port = rest_port
        self.cert_file = cert_file
        self.key_file = key_file

        # Security Manager
        self.security_manager = SecurityManager(
            credentials_file=credentials_file,
            audit_log_file=audit_log_file,
            cert_file=cert_file,
            key_file=key_file
        )

        # WebSocket connections with authentication
        self.connected_clients = {}  # websocket -> client_credentials
        self.swarm_connections = {}  # swarm_id -> websocket connection

        # Central Event Bus
        self.event_bus = CentralEventBus()

        # Event Aggregation Service for high-volume processing
        self.event_aggregation = None
        if enable_aggregation:
            self.event_aggregation = EventAggregationService(
                max_queue_size=max_aggregation_queue,
                batch_size=50,  # Smaller batches for real-time processing
                batch_timeout=0.5,  # Faster batching for real-time
                max_workers=8,  # More workers for high throughput
                enable_buffering=True,
                buffer_size=25000  # Buffer for recent events
            )

        # Data stores
        self.swarm_nodes = {}
        self.task_queues = []
        self.discovery_events = []
        self.security_events = []
        self.performance_metrics = {
            "latency": 45,
            "load": 67,
            "throughput": 23,
            "completionRate": 94
        }

        # REST API polling data
        self.polling_swarms = {}  # swarm_id -> last_poll_time
        self.poll_interval = 30  # seconds

        # Server state
        self.running = False
        self.ws_server = None
        self.rest_server = None
        self.loop = None

    async def handle_client(self, websocket):
        """Handle individual WebSocket client connections with authentication"""
        remote_address = websocket.remote_address
        logger.info(f"New client connected: {remote_address}")

        client_credentials = None
        client_type = "unknown"
        swarm_id = None

        try:
            # First message must be authentication
            auth_timeout = 10  # 10 seconds to authenticate
            try:
                auth_message = await asyncio.wait_for(websocket.recv(), timeout=auth_timeout)
                auth_data = json.loads(auth_message)

                if auth_data.get("type") != "authenticate":
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Authentication required. Send authentication message first."
                    }))
                    await websocket.close(1008, "Authentication required")
                    return

                # Authenticate client
                api_key = auth_data.get("api_key")
                if not api_key:
                    await websocket.send(json.dumps({
                        "type": "auth_failure",
                        "message": "API key required"
                    }))
                    await websocket.close(1008, "API key required")
                    return

                client_credentials = self.security_manager.authenticate_client(
                    api_key, "websocket_client", remote_address[0] if remote_address else None
                )

                if not client_credentials:
                    await websocket.send(json.dumps({
                        "type": "auth_failure",
                        "message": "Invalid API key"
                    }))
                    await websocket.close(1008, "Invalid API key")
                    return

                # Authentication successful
                await websocket.send(json.dumps({
                    "type": "auth_success",
                    "client_id": client_credentials.client_id,
                    "client_name": client_credentials.client_name,
                    "permission_level": client_credentials.permission_level.value
                }))

                logger.info(f"Client authenticated: {client_credentials.client_name} ({client_credentials.client_id})")

            except asyncio.TimeoutError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Authentication timeout"
                }))
                await websocket.close(1008, "Authentication timeout")
                return

            # Store authenticated client
            self.connected_clients[websocket] = client_credentials

            # Send initial state based on permissions
            await self.send_initial_state(websocket, client_credentials)

            # Keep connection alive and handle authenticated messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    client_type = data.get("client_type", client_type)
                    swarm_id = data.get("swarm_id", swarm_id)

                    # Register swarm connections
                    if client_type == "swarm" and swarm_id:
                        self.swarm_connections[swarm_id] = websocket
                        logger.info(f"Swarm {swarm_id} registered for real-time publishing")

                    await self.handle_authenticated_client_message(websocket, data, client_credentials)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from {client_credentials.client_name}: {message}")

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {remote_address}")
            # Clean up swarm connections
            if swarm_id and swarm_id in self.swarm_connections:
                del self.swarm_connections[swarm_id]
        finally:
            # Clean up authenticated client
            if websocket in self.connected_clients:
                del self.connected_clients[websocket]

    async def handle_authenticated_client_message(self, websocket, data, client_credentials):
        """Handle messages from authenticated clients with permission checking"""
        message_type = data.get("type", "unknown")
        logger.info(f"Received message type: {message_type} from {client_credentials.client_name}")

        if message_type == "subscribe":
            # Client wants to subscribe to specific data streams
            subscriptions = data.get("subscriptions", [])
            logger.info(f"Client {client_credentials.client_name} subscribed to: {subscriptions}")
            # Could implement selective broadcasting here

        elif message_type == "swarm_event":
            # Handle real-time events published by swarms
            # Check if client has permission to publish events
            if client_credentials.permission_level in [PermissionLevel.OPERATOR, PermissionLevel.ADMIN]:
                await self.handle_swarm_event(data, client_credentials)
            else:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Insufficient permissions to publish events"
                }))

        elif message_type == "command":
            # Handle control commands with permission checking
            await self.handle_command_with_permissions(websocket, data, client_credentials)

    async def handle_command_with_permissions(self, websocket, data, client_credentials):
        """Handle control commands from clients with permission checking and audit logging"""
        command_type = data.get("commandType")
        target_id = data.get("targetId")
        parameters = data.get("parameters", {})

        # Check permissions for this command
        if not self.security_manager.authorize_action(
            client_credentials, command_type, "system", target_id or "system"
        ):
            # Log unauthorized access attempt
            self.security_manager.log_audit_event(
                client_id=client_credentials.client_id,
                client_name=client_credentials.client_name,
                action=f"unauthorized_{command_type}",
                resource_type="system",
                resource_id=target_id or "system",
                permission_level=client_credentials.permission_level.value,
                success=False,
                details={"command": command_type, "reason": "insufficient_permissions"},
                ip_address=websocket.remote_address[0] if websocket.remote_address else None
            )

            await websocket.send(json.dumps({
                "type": "command_ack",
                "commandType": command_type,
                "targetId": target_id,
                "result": {"success": False, "message": "Insufficient permissions"},
                "timestamp": time.time()
            }))
            return

        logger.info(f"Executing command: {command_type} on {target_id or 'system'} by {client_credentials.client_name}")

        # Execute command and get result
        result = await self.execute_command(command_type, target_id, parameters)

        # Log successful command execution
        self.security_manager.log_audit_event(
            client_id=client_credentials.client_id,
            client_name=client_credentials.client_name,
            action=command_type,
            resource_type="system",
            resource_id=target_id or "system",
            permission_level=client_credentials.permission_level.value,
            success=result.get("success", False),
            details={"command": command_type, "parameters": parameters, "result": result},
            ip_address=websocket.remote_address[0] if websocket.remote_address else None
        )

        # Send command acknowledgment
        ack_data = {
            "type": "command_ack",
            "commandType": command_type,
            "targetId": target_id,
            "result": result,
            "timestamp": time.time()
        }
        await websocket.send(json.dumps(ack_data))

        # Broadcast state updates if command affected system state
        if command_type in ["start_node", "stop_node", "reset_node", "inject_scenario"]:
            # Trigger immediate updates
            for node in self.swarm_nodes.values():
                asyncio.run_coroutine_threadsafe(
                    self.broadcast_update("node_status_update", {"node": node}),
                    self.loop
                )

    async def handle_swarm_event(self, data, client_credentials=None):
        """Handle real-time events published by swarms with aggregation support"""
        event_type = data.get("event_type", "unknown")
        swarm_id = data.get("swarm_id", "unknown")

        # Log event publishing for audit
        if client_credentials:
            self.security_manager.log_audit_event(
                client_id=client_credentials.client_id,
                client_name=client_credentials.client_name,
                action=f"publish_{event_type}",
                resource_type="event",
                resource_id=f"{swarm_id}_{event_type}",
                permission_level=client_credentials.permission_level.value,
                success=True,
                details={"event_type": event_type, "swarm_id": swarm_id},
                ip_address=None  # Would need to be passed from WebSocket handler
            )

        # Determine event priority for aggregation
        priority_map = {
            "node_status": EventPriority.LOW,
            "task_update": EventPriority.MEDIUM,
            "discovery_event": EventPriority.MEDIUM,
            "security_event": EventPriority.HIGH,
            "performance_metric": EventPriority.LOW,
            "heartbeat": EventPriority.DEBUG
        }
        priority = priority_map.get(event_type, EventPriority.MEDIUM)

        # Prepare event data for aggregation
        event_data = {
            "event_id": data.get("event_id", f"evt_{int(time.time() * 1000000)}"),
            "event_type": event_type,
            "priority": priority.value,
            "source_node": data.get("source_node", f"swarm_{swarm_id}"),
            "swarm_id": swarm_id,
            "timestamp": data.get("timestamp", time.time()),
            "data": data.get("data", {})
        }

        # Submit to aggregation service if available, otherwise use direct processing
        if self.event_aggregation:
            # Use event aggregation for high-volume processing
            accepted = await self.event_aggregation.submit_event(event_data)
            if not accepted:
                logger.warning(f"Event rejected by aggregation service: {event_type}")
                return

            # Set up event handlers for processed events
            await self._setup_aggregation_handlers()

        else:
            # Fallback to direct event bus processing
            self.event_bus.publish(event_type, {
                "swarm_id": swarm_id,
                "data": data.get("data", {}),
                "source": f"swarm_{swarm_id}"
            })

            # Update local state directly
            await self._update_local_state_from_event(event_type, swarm_id, data)

        # Broadcast updates to dashboard clients
        await self.broadcast_event_update(event_type, data)

    async def _setup_aggregation_handlers(self):
        """Set up event handlers for processed events from aggregation service"""
        if not self.event_aggregation:
            return

        # Set up handlers for different event types
        async def handle_node_status_event(event):
            await self._update_local_state_from_event("node_status", event.swarm_id,
                                                    {"data": event.data, "swarm_id": event.swarm_id})

        async def handle_task_event(event):
            await self._update_local_state_from_event("task_update", event.swarm_id,
                                                    {"data": event.data, "swarm_id": event.swarm_id})

        async def handle_discovery_event(event):
            await self._update_local_state_from_event("discovery_event", event.swarm_id,
                                                    {"data": event.data, "swarm_id": event.swarm_id})

        async def handle_security_event(event):
            await self._update_local_state_from_event("security_event", event.swarm_id,
                                                    {"data": event.data, "swarm_id": event.swarm_id})

        # Register handlers with aggregation service
        self.event_aggregation.add_route_handler("node_status", handle_node_status_event)
        self.event_aggregation.add_route_handler("task_update", handle_task_event)
        self.event_aggregation.add_route_handler("discovery_event", handle_discovery_event)
        self.event_aggregation.add_route_handler("security_event", handle_security_event)

    async def _update_local_state_from_event(self, event_type: str, swarm_id: str, data: Dict[str, Any]):
        """Update local state from processed events"""
        if event_type == "node_status":
            node_data = data.get("data", {})
            node_id = f"{swarm_id}_{node_data.get('node_id', 'unknown')}"
            self.swarm_nodes[node_id] = {
                "id": node_id,
                "name": node_data.get("name", node_id),
                "type": node_data.get("type", "enterprise"),
                "status": node_data.get("status", "unknown"),
                "load": node_data.get("load", 0),
                "tasks": node_data.get("tasks", 0),
                "cpu_usage": node_data.get("cpu_usage", 0),
                "memory_usage": node_data.get("memory_usage", 0),
                "last_updated": time.time(),
                "swarm_id": swarm_id
            }

        elif event_type == "task_update":
            task_data = data.get("data", {})
            task_id = task_data.get("task_id")
            # Update or add task
            existing_task = next((t for t in self.task_queues if t["id"] == task_id), None)
            if existing_task:
                existing_task.update(task_data)
            else:
                self.task_queues.append({
                    "id": task_id,
                    "description": task_data.get("description", "Unknown task"),
                    "status": task_data.get("status", "unknown"),
                    "progress": task_data.get("progress", 0),
                    "assigned_node": task_data.get("assigned_node"),
                    "priority": task_data.get("priority", 1),
                    "created_at": task_data.get("created_at", time.time()),
                    "swarm_id": swarm_id
                })

        elif event_type == "discovery_event":
            discovery_data = data.get("data", {})
            discovery_data["swarm_id"] = swarm_id
            self.discovery_events.append(discovery_data)
            if len(self.discovery_events) > 20:
                self.discovery_events.pop(0)

        elif event_type == "security_event":
            security_data = data.get("data", {})
            security_data["source"] = swarm_id
            self.security_events.append(security_data)
            if len(self.security_events) > 20:
                self.security_events.pop(0)

    async def broadcast_event_update(self, event_type, original_data):
        """Broadcast event updates to dashboard clients"""
        if event_type == "node_status":
            node_data = original_data.get("data", {})
            node_id = f"{original_data.get('swarm_id')}_{node_data.get('node_id')}"
            await self.broadcast_update("node_status_update", {"node": self.swarm_nodes.get(node_id)})

        elif event_type == "task_update":
            await self.broadcast_update("task_queue_update", {"tasks": self.task_queues})

        elif event_type == "discovery_event":
            await self.broadcast_update("discovery_event", {"event": original_data.get("data")})

        elif event_type == "security_event":
            await self.broadcast_update("security_event", {"event": original_data.get("data")})

    async def execute_command(self, command_type, target_id, parameters):
        """Execute a control command"""
        try:
            if command_type == "start_node":
                if target_id and target_id in self.swarm_nodes:
                    self.swarm_nodes[target_id]["status"] = "active"
                    return {"success": True, "message": f"Node {target_id} started"}

            elif command_type == "stop_node":
                if target_id and target_id in self.swarm_nodes:
                    self.swarm_nodes[target_id]["status"] = "inactive"
                    return {"success": True, "message": f"Node {target_id} stopped"}

            elif command_type == "reset_node":
                if target_id and target_id in self.swarm_nodes:
                    node = self.swarm_nodes[target_id]
                    node["status"] = "active"
                    node["load"] = 10
                    node["cpu_usage"] = 15
                    node["tasks"] = 0
                    return {"success": True, "message": f"Node {target_id} reset"}

            elif command_type == "start_task":
                if target_id:
                    for task in self.task_queues:
                        if task["id"] == target_id:
                            task["status"] = "running"
                            task["progress"] = 0
                            break
                    return {"success": True, "message": f"Task {target_id} started"}

            elif command_type == "stop_task":
                if target_id:
                    for task in self.task_queues:
                        if task["id"] == target_id:
                            task["status"] = "pending"
                            break
                    return {"success": True, "message": f"Task {target_id} stopped"}

            elif command_type == "update_parameter":
                param = parameters.get("parameter")
                value = parameters.get("value")
                # In a real system, this would update actual system parameters
                return {"success": True, "message": f"Parameter {param} updated to {value}"}

            elif command_type == "update_task_priority":
                priority = parameters.get("priority")
                if target_id:
                    for task in self.task_queues:
                        if task["id"] == target_id:
                            task["priority"] = priority
                            break
                    return {"success": True, "message": f"Task {target_id} priority updated"}

            elif command_type == "inject_scenario":
                scenario_type = parameters.get("scenarioType")
                await self.inject_scenario(scenario_type, parameters)
                return {"success": True, "message": f"Scenario {scenario_type} injected"}

            return {"success": False, "message": f"Unknown command: {command_type}"}

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {"success": False, "message": str(e)}

    async def inject_scenario(self, scenario_type, parameters):
        """Inject a test scenario into the system"""
        if scenario_type == "node_failure":
            node_id = parameters.get("nodeId")
            if node_id and node_id in self.swarm_nodes:
                self.swarm_nodes[node_id]["status"] = "failed"
                # Add security event for the failure
                self.simulate_security_events()

        elif scenario_type == "high_load":
            duration = parameters.get("duration", 30)
            # Increase load on all nodes
            for node in self.swarm_nodes.values():
                node["load"] = min(95, node["load"] + 30)
                node["cpu_usage"] = min(90, node["cpu_usage"] + 25)
            # Schedule load reduction after duration
            asyncio.run_coroutine_threadsafe(
                self.reduce_load_after_delay(duration),
                self.loop
            )

        elif scenario_type == "network_partition":
            duration = parameters.get("duration", 60)
            # Simulate network issues by setting some nodes to unreachable
            affected_nodes = list(self.swarm_nodes.keys())[:2]  # Affect first 2 nodes
            for node_id in affected_nodes:
                self.swarm_nodes[node_id]["status"] = "unreachable"
            # Schedule recovery after duration
            asyncio.run_coroutine_threadsafe(
                self.recover_nodes_after_delay(affected_nodes, duration),
                self.loop
            )

        elif scenario_type == "security_breach":
            severity = parameters.get("severity", "medium")
            # Generate multiple security events
            for _ in range(5 if severity == "high" else 3):
                self.simulate_security_events()

        elif scenario_type == "task_backlog":
            task_count = parameters.get("taskCount", 10)
            # Add many pending tasks
            for i in range(task_count):
                new_task = {
                    "id": f"backlog_task_{int(time.time())}_{i}",
                    "description": f"Backlog task {i+1}",
                    "status": "pending",
                    "progress": None,
                    "assigned_node": None,
                    "priority": 1,
                    "created_at": time.time()
                }
                self.task_queues.append(new_task)

    async def reduce_load_after_delay(self, delay_seconds):
        """Reduce system load after a delay"""
        await asyncio.sleep(delay_seconds)
        for node in self.swarm_nodes.values():
            node["load"] = max(10, node["load"] - 30)
            node["cpu_usage"] = max(5, node["cpu_usage"] - 25)

    async def recover_nodes_after_delay(self, node_ids, delay_seconds):
        """Recover nodes after a delay"""
        await asyncio.sleep(delay_seconds)
        for node_id in node_ids:
            if node_id in self.swarm_nodes:
                self.swarm_nodes[node_id]["status"] = "active"

    async def send_initial_state(self, websocket, client_credentials):
        """Send initial state to newly connected authenticated client"""
        # Filter data based on permissions
        swarm_nodes = list(self.swarm_nodes.values())
        task_queues = self.task_queues
        discovery_events = self.discovery_events[-10:]  # Last 10 events
        security_events = self.security_events[-10:]    # Last 10 events

        # View-only clients get limited data
        if client_credentials.permission_level == PermissionLevel.VIEW_ONLY:
            # Remove sensitive information for view-only clients
            swarm_nodes = [
                {k: v for k, v in node.items() if k not in ['internal_config', 'secrets']}
                for node in swarm_nodes
            ]

        initial_data = {
            "type": "initial_state",
            "swarm_nodes": swarm_nodes,
            "task_queues": task_queues,
            "discovery_events": discovery_events,
            "security_events": security_events,
            "performance_metrics": self.performance_metrics,
            "event_stats": self.event_bus.get_event_stats(),
            "client_permissions": {
                "level": client_credentials.permission_level.value,
                "can_control_nodes": client_credentials.permission_level in [PermissionLevel.OPERATOR, PermissionLevel.ADMIN],
                "can_inject_scenarios": client_credentials.permission_level == PermissionLevel.ADMIN,
                "can_publish_events": client_credentials.permission_level in [PermissionLevel.OPERATOR, PermissionLevel.ADMIN]
            }
        }
        await websocket.send(json.dumps(initial_data))

    # REST API Endpoints
    async def handle_rest_state_snapshot(self, request):
        """REST API endpoint for periodic state snapshots"""
        swarm_id = request.query.get('swarm_id')
        if swarm_id:
            # Return state for specific swarm
            swarm_nodes = [node for node in self.swarm_nodes.values() if node.get('swarm_id') == swarm_id]
            swarm_tasks = [task for task in self.task_queues if task.get('swarm_id') == swarm_id]

            return web.json_response({
                "swarm_id": swarm_id,
                "timestamp": time.time(),
                "nodes": swarm_nodes,
                "tasks": swarm_tasks,
                "last_updated": self.polling_swarms.get(swarm_id, 0)
            })
        else:
            # Return global state snapshot
            return web.json_response({
                "timestamp": time.time(),
                "total_swarms": len(set(node.get('swarm_id') for node in self.swarm_nodes.values())),
                "total_nodes": len(self.swarm_nodes),
                "total_tasks": len(self.task_queues),
                "active_connections": len(self.swarm_connections),
                "event_stats": self.event_bus.get_event_stats()
            })

    async def handle_rest_publish_event(self, request):
        """REST API endpoint for swarms to publish events via polling"""
        try:
            data = await request.json()
            swarm_id = data.get('swarm_id')

            if swarm_id:
                self.polling_swarms[swarm_id] = time.time()

                # Handle the event like a WebSocket swarm_event
                await self.handle_swarm_event({
                    "type": "swarm_event",
                    "swarm_id": swarm_id,
                    "event_type": data.get("event_type"),
                    "data": data.get("data", {})
                })

                return web.json_response({"status": "accepted", "timestamp": time.time()})
            else:
                return web.json_response({"error": "swarm_id required"}, status=400)

        except Exception as e:
            logger.error(f"REST event publish error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_rest_metrics(self, request):
        """REST API endpoint for metrics data"""
        return web.json_response({
            "timestamp": time.time(),
            "metrics": self.performance_metrics,
            "heatmap_data": {
                "swarm_density": self._generate_swarm_density_data(),
                "network_utilization": self._generate_network_utilization_data(),
                "load_balancing": self._generate_load_balancing_data()
            }
        })

    async def handle_rest_events(self, request):
        """REST API endpoint for event history"""
        client_credentials = request['client_credentials']
        event_type = request.query.get('type')
        limit = int(request.query.get('limit', 50))

        # Log audit event for event access
        self.security_manager.log_audit_event(
            client_id=client_credentials.client_id,
            client_name=client_credentials.client_name,
            action="access_events",
            resource_type="events",
            resource_id=event_type or "all",
            permission_level=client_credentials.permission_level.value,
            success=True,
            details={"limit": limit},
            ip_address=request.remote
        )

        if event_type:
            events = self.event_bus.get_recent_events(event_type, limit)
        else:
            # Return all event types
            events = []
            for et in self.event_bus.event_history.keys():
                events.extend(self.event_bus.get_recent_events(et, limit // len(self.event_bus.event_history)))

        return web.json_response({
            "timestamp": time.time(),
            "events": events[-limit:],  # Limit total results
            "event_stats": self.event_bus.get_event_stats()
        })

    async def handle_rest_list_clients(self, request):
        """REST API endpoint to list client credentials (admin only)"""
        client_credentials = request['client_credentials']

        # Only admins can list clients
        if client_credentials.permission_level != PermissionLevel.ADMIN:
            return web.json_response({"error": "Admin access required"}, status=403)

        clients = self.security_manager.list_clients()

        # Log audit event
        self.security_manager.log_audit_event(
            client_id=client_credentials.client_id,
            client_name=client_credentials.client_name,
            action="list_clients",
            resource_type="security",
            resource_id="clients",
            permission_level=client_credentials.permission_level.value,
            success=True,
            details={"client_count": len(clients)},
            ip_address=request.remote
        )

        return web.json_response({"clients": clients})

    async def handle_rest_create_client(self, request):
        """REST API endpoint to create new client credentials (admin only)"""
        client_credentials = request['client_credentials']

        # Only admins can create clients
        if client_credentials.permission_level != PermissionLevel.ADMIN:
            return web.json_response({"error": "Admin access required"}, status=403)

        try:
            data = await request.json()
            client_name = data.get('client_name')
            permission_level_str = data.get('permission_level', 'view_only')
            swarm_id = data.get('swarm_id')

            # Validate permission level
            try:
                permission_level = PermissionLevel(permission_level_str)
            except ValueError:
                return web.json_response({"error": f"Invalid permission level: {permission_level_str}"}, status=400)

            client_id, api_key = self.security_manager.create_client_credentials(
                client_name, permission_level, swarm_id
            )

            # Log audit event
            self.security_manager.log_audit_event(
                client_id=client_credentials.client_id,
                client_name=client_credentials.client_name,
                action="create_client",
                resource_type="security",
                resource_id=client_id,
                permission_level=client_credentials.permission_level.value,
                success=True,
                details={"new_client_name": client_name, "new_client_level": permission_level_str},
                ip_address=request.remote
            )

            return web.json_response({
                "client_id": client_id,
                "client_name": client_name,
                "api_key": api_key,  # Only returned once for security
                "permission_level": permission_level_str,
                "swarm_id": swarm_id
            })

        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_rest_revoke_client(self, request):
        """REST API endpoint to revoke client credentials (admin only)"""
        client_credentials = request['client_credentials']
        target_client_id = request.match_info['client_id']

        # Only admins can revoke clients
        if client_credentials.permission_level != PermissionLevel.ADMIN:
            return web.json_response({"error": "Admin access required"}, status=403)

        # Prevent self-revocation
        if target_client_id == client_credentials.client_id:
            return web.json_response({"error": "Cannot revoke your own credentials"}, status=400)

        success = self.security_manager.revoke_client_credentials(target_client_id)

        # Log audit event
        self.security_manager.log_audit_event(
            client_id=client_credentials.client_id,
            client_name=client_credentials.client_name,
            action="revoke_client",
            resource_type="security",
            resource_id=target_client_id,
            permission_level=client_credentials.permission_level.value,
            success=success,
            details={"target_client_id": target_client_id},
            ip_address=request.remote
        )

        if success:
            return web.json_response({"message": f"Client {target_client_id} revoked"})
        else:
            return web.json_response({"error": f"Client {target_client_id} not found"}, status=404)

    async def handle_rest_security_status(self, request):
        """REST API endpoint to get security status"""
        client_credentials = request['client_credentials']

        # Only operators and admins can view security status
        if client_credentials.permission_level == PermissionLevel.VIEW_ONLY:
            return web.json_response({"error": "Insufficient permissions"}, status=403)

        status = self.security_manager.get_security_status()

        # Log audit event
        self.security_manager.log_audit_event(
            client_id=client_credentials.client_id,
            client_name=client_credentials.client_name,
            action="view_security_status",
            resource_type="security",
            resource_id="status",
            permission_level=client_credentials.permission_level.value,
            success=True,
            details={},
            ip_address=request.remote
        )

        return web.json_response(status)

    async def handle_rest_audit_log(self, request):
        """REST API endpoint to view audit logs (admin only)"""
        client_credentials = request['client_credentials']

        # Only admins can view audit logs
        if client_credentials.permission_level != PermissionLevel.ADMIN:
            return web.json_response({"error": "Admin access required"}, status=403)

        limit = int(request.query.get('limit', 100))

        # Read audit log file
        audit_entries = []
        try:
            with open(self.security_manager.audit_log_file, 'r') as f:
                lines = f.readlines()[-limit:]  # Get last N lines
                for line in lines:
                    # Parse log line (simplified parsing)
                    audit_entries.append({"log_entry": line.strip()})
        except FileNotFoundError:
            audit_entries = []

        # Log audit event
        self.security_manager.log_audit_event(
            client_id=client_credentials.client_id,
            client_name=client_credentials.client_name,
            action="view_audit_log",
            resource_type="security",
            resource_id="audit_log",
            permission_level=client_credentials.permission_level.value,
            success=True,
            details={"limit": limit, "entries_returned": len(audit_entries)},
            ip_address=request.remote
        )

        return web.json_response({
            "audit_entries": audit_entries,
            "total_entries": len(audit_entries)
        })

    async def handle_rest_aggregation_metrics(self, request):
        """REST API endpoint for aggregation service metrics"""
        client_credentials = request['client_credentials']

        # Only operators and admins can view aggregation metrics
        if client_credentials.permission_level == PermissionLevel.VIEW_ONLY:
            return web.json_response({"error": "Insufficient permissions"}, status=403)

        if not self.event_aggregation:
            return web.json_response({
                "enabled": False,
                "message": "Event aggregation service not enabled"
            })

        metrics = self.event_aggregation.get_metrics()
        swarm_stats = self.event_aggregation.get_swarm_stats()

        # Log audit event
        self.security_manager.log_audit_event(
            client_id=client_credentials.client_id,
            client_name=client_credentials.client_name,
            action="view_aggregation_metrics",
            resource_type="aggregation",
            resource_id="metrics",
            permission_level=client_credentials.permission_level.value,
            success=True,
            details={"metrics_requested": True},
            ip_address=request.remote
        )

        return web.json_response({
            "enabled": True,
            "metrics": metrics,
            "swarm_stats": swarm_stats,
            "timestamp": time.time()
        })

    async def handle_rest_aggregation_events(self, request):
        """REST API endpoint for querying aggregated events"""
        client_credentials = request['client_credentials']

        # Only operators and admins can query events
        if client_credentials.permission_level == PermissionLevel.VIEW_ONLY:
            return web.json_response({"error": "Insufficient permissions"}, status=403)

        if not self.event_aggregation:
            return web.json_response({"error": "Event aggregation service not enabled"}, status=503)

        # Parse query parameters
        limit = int(request.query.get('limit', 100))
        event_type = request.query.get('event_type')
        swarm_id = request.query.get('swarm_id')
        start_time = request.query.get('start_time')
        end_time = request.query.get('end_time')

        # Build filters
        filters = {}
        if event_type:
            filters['event_type'] = event_type
        if swarm_id:
            filters['swarm_id'] = swarm_id
        if start_time:
            filters['start_time'] = float(start_time)
        if end_time:
            filters['end_time'] = float(end_time)

        # Query events
        events = await self.event_aggregation.query_events(filters, limit)

        # Log audit event
        self.security_manager.log_audit_event(
            client_id=client_credentials.client_id,
            client_name=client_credentials.client_name,
            action="query_aggregation_events",
            resource_type="aggregation",
            resource_id="events",
            permission_level=client_credentials.permission_level.value,
            success=True,
            details={"filters": filters, "limit": limit, "results": len(events)},
            ip_address=request.remote
        )

        return web.json_response({
            "events": events,
            "total_count": len(events),
            "filters": filters,
            "timestamp": time.time()
        })

    async def handle_rest_aggregation_health(self, request):
        """REST API endpoint for aggregation service health check"""
        if not self.event_aggregation:
            return web.json_response({
                "status": "disabled",
                "message": "Event aggregation service not enabled"
            })

        # Get recent events as health indicator
        recent_events = self.event_aggregation.get_recent_events(limit=10)
        metrics = self.event_aggregation.get_metrics()

        # Determine health status
        health_status = "healthy"
        issues = []

        if metrics['error_count'] > 10:
            health_status = "warning"
            issues.append("High error count")

        if metrics['current_queue_size'] > metrics['max_queue_size'] * 0.9:
            health_status = "warning"
            issues.append("High queue utilization")

        if time.time() - metrics['last_health_check'] > 60:
            health_status = "critical"
            issues.append("Health check overdue")

        return web.json_response({
            "status": health_status,
            "issues": issues,
            "metrics": metrics,
            "recent_events_count": len(recent_events),
            "last_event_time": recent_events[0]['timestamp'] if recent_events else None,
            "timestamp": time.time()
        })

    def create_rest_app(self):
        """Create aiohttp REST API application with authentication"""
        app = web.Application(middlewares=[self.auth_middleware])

        # State snapshot endpoints
        app.router.add_get('/api/state', self.handle_rest_state_snapshot)
        app.router.add_get('/api/state/{swarm_id}', self.handle_rest_state_snapshot)

        # Event publishing endpoints
        app.router.add_post('/api/events', self.handle_rest_publish_event)

        # Metrics endpoints
        app.router.add_get('/api/metrics', self.handle_rest_metrics)

        # Event history endpoints
        app.router.add_get('/api/events', self.handle_rest_events)

        # Security management endpoints (admin only)
        app.router.add_get('/api/security/clients', self.handle_rest_list_clients)
        app.router.add_post('/api/security/clients', self.handle_rest_create_client)
        app.router.add_delete('/api/security/clients/{client_id}', self.handle_rest_revoke_client)
        app.router.add_get('/api/security/status', self.handle_rest_security_status)
        app.router.add_get('/api/security/audit', self.handle_rest_audit_log)

        # Event aggregation endpoints
        app.router.add_get('/api/aggregation/metrics', self.handle_rest_aggregation_metrics)
        app.router.add_get('/api/aggregation/events', self.handle_rest_aggregation_events)
        app.router.add_get('/api/aggregation/health', self.handle_rest_aggregation_health)

        # Health check (no auth required)
        app.router.add_get('/health', lambda r: web.json_response({"status": "healthy", "timestamp": time.time()}))

        return app

    @web.middleware
    async def auth_middleware(self, request, handler):
        """Authentication middleware for REST API"""
        # Skip authentication for health check
        if request.path == '/health':
            return await handler(request)

        # Check for API key in header or query parameter
        api_key = (request.headers.get('X-API-Key') or
                  request.headers.get('Authorization', '').replace('Bearer ', '') or
                  request.query.get('api_key'))

        if not api_key:
            return web.json_response(
                {"error": "API key required", "message": "Provide API key in X-API-Key header, Authorization header, or api_key query parameter"},
                status=401
            )

        # Authenticate client
        client_credentials = self.security_manager.authenticate_client(
            api_key, "rest_api_client", request.remote
        )

        if not client_credentials:
            return web.json_response(
                {"error": "Invalid API key", "message": "Authentication failed"},
                status=401
            )

        # Store credentials in request for use in handlers
        request['client_credentials'] = client_credentials
        return await handler(request)

    async def broadcast_update(self, update_type: str, data: Dict[str, Any]):
        """Broadcast update to all authenticated connected clients"""
        if not self.connected_clients:
            return

        message = {
            "type": update_type,
            **data
        }

        # Remove disconnected clients
        disconnected_clients = []
        for client_ws, client_creds in self.connected_clients.items():
            try:
                await client_ws.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(client_ws)

        # Clean up disconnected clients
        for client_ws in disconnected_clients:
            del self.connected_clients[client_ws]

    def generate_mock_data(self):
        """Generate mock swarm monitoring data"""
        # Generate swarm nodes
        node_types = ["enterprise", "cloud", "home"]
        statuses = ["active", "inactive", "busy", "failed", "starting"]

        for i in range(5):
            node_id = f"swarm-{i+1}"
            self.swarm_nodes[node_id] = {
                "id": node_id,
                "name": f"Swarm Node {i+1}",
                "type": random.choice(node_types),
                "status": random.choice(statuses),
                "load": random.randint(10, 95),
                "tasks": random.randint(0, 8),
                "cpu_usage": random.randint(5, 90),
                "memory_usage": random.randint(20, 85),
                "last_updated": time.time()
            }

        # Generate task queues
        task_statuses = ["pending", "running", "completed", "failed"]
        task_descriptions = [
            "Process user authentication",
            "Analyze data patterns",
            "Generate recommendations",
            "Update system metrics",
            "Handle API requests",
            "Process background tasks",
            "Validate user input",
            "Generate reports"
        ]

        self.task_queues = []
        for i in range(8):
            self.task_queues.append({
                "id": f"task-{i+1}",
                "description": random.choice(task_descriptions),
                "status": random.choice(task_statuses),
                "progress": random.randint(0, 100) if random.choice([True, False]) else None,
                "assigned_node": f"swarm-{random.randint(1, 5)}",
                "priority": random.randint(1, 5),
                "created_at": time.time() - random.randint(0, 3600)
            })

    def simulate_discovery_events(self):
        """Simulate discovery events"""
        discovery_types = [
            {"type": "lan_broadcast", "message": "LAN broadcast detected from 192.168.1.100"},
            {"type": "registry_discovery", "message": "Registry discovery successful for swarm-3"},
            {"type": "lan_broadcast", "message": "UDP broadcast received on port 9999"},
            {"type": "registry_discovery", "message": "HTTPS registry connection established"},
            {"type": "lan_broadcast", "message": "Local network scan completed"},
        ]

        event = random.choice(discovery_types)
        event["swarm_id"] = f"swarm-{random.randint(1, 5)}"
        self.discovery_events.append(event)

        # Keep only last 20 events
        if len(self.discovery_events) > 20:
            self.discovery_events.pop(0)

        return event

    def simulate_security_events(self):
        """Simulate security events"""
        security_types = [
            {"type": "auth_success", "message": "Authentication successful for admin user"},
            {"type": "tls_handshake", "message": "TLS 1.3 handshake completed"},
            {"type": "auth_failure", "message": "Authentication failed: invalid credentials"},
            {"type": "tls_handshake", "message": "Certificate validation successful"},
            {"type": "auth_success", "message": "API key authentication successful"},
        ]

        event = random.choice(security_types)
        event["source"] = f"swarm-{random.randint(1, 5)}"
        self.security_events.append(event)

        # Keep only last 20 events
        if len(self.security_events) > 20:
            self.security_events.pop(0)

        return event

    def update_performance_metrics(self):
        """Update performance metrics with some variation"""
        # Add some realistic variation to metrics
        self.performance_metrics["latency"] = max(10, min(200,
            self.performance_metrics["latency"] + random.randint(-10, 10)))
        self.performance_metrics["load"] = max(20, min(95,
            self.performance_metrics["load"] + random.randint(-5, 5)))
        self.performance_metrics["throughput"] = max(5, min(50,
            self.performance_metrics["throughput"] + random.randint(-3, 3)))
        self.performance_metrics["completionRate"] = max(85, min(98,
            self.performance_metrics["completionRate"] + random.randint(-2, 2)))

    def update_node_statuses(self):
        """Randomly update node statuses to simulate real-time changes"""
        for node in self.swarm_nodes.values():
            # Small chance of status change
            if random.random() < 0.1:  # 10% chance
                statuses = ["active", "inactive", "busy", "failed", "starting"]
                node["status"] = random.choice(statuses)

            # Update metrics with some variation
            node["load"] = max(5, min(95, node["load"] + random.randint(-5, 5)))
            node["cpu_usage"] = max(5, min(95, node["cpu_usage"] + random.randint(-3, 3)))
            node["tasks"] = max(0, min(10, node["tasks"] + random.randint(-1, 1)))
            node["last_updated"] = time.time()

    def simulation_loop(self):
        """Main simulation loop running in background thread"""
        while self.running:
            try:
                # Update node statuses
                self.update_node_statuses()

                # Update performance metrics
                self.update_performance_metrics()

                # Simulate random events
                if random.random() < 0.3:  # 30% chance per cycle
                    if random.random() < 0.5:
                        event = self.simulate_discovery_events()
                        # Schedule broadcast in the main event loop
                        asyncio.run_coroutine_threadsafe(
                            self.broadcast_update("discovery_event", {"event": event}),
                            self.loop
                        )
                    else:
                        event = self.simulate_security_events()
                        # Schedule broadcast in the main event loop
                        asyncio.run_coroutine_threadsafe(
                            self.broadcast_update("security_event", {"event": event}),
                            self.loop
                        )

                # Broadcast node updates
                for node in self.swarm_nodes.values():
                    asyncio.run_coroutine_threadsafe(
                        self.broadcast_update("node_status_update", {"node": node}),
                        self.loop
                    )

                # Broadcast performance metrics with enhanced data
                enhanced_metrics = self.performance_metrics.copy()
                enhanced_metrics.update({
                    "activeConnections": len(self.swarm_nodes),
                    "networkUtilization": random.randint(30, 90),
                    "memoryUsage": random.randint(40, 85),
                    "cpuUsage": sum(node.get("cpu_usage", 0) for node in self.swarm_nodes.values()) / max(len(self.swarm_nodes), 1)
                })

                metrics_data = {
                    "metrics": enhanced_metrics,
                    "heatmap_data": {
                        "swarm_density": self._generate_swarm_density_data(),
                        "network_utilization": self._generate_network_utilization_data(),
                        "load_balancing": self._generate_load_balancing_data()
                    }
                }

                asyncio.run_coroutine_threadsafe(
                    self.broadcast_update("performance_metrics", metrics_data),
                    self.loop
                )

                # Broadcast task queue updates
                asyncio.run_coroutine_threadsafe(
                    self.broadcast_update("task_queue_update", {"tasks": self.task_queues}),
                    self.loop
                )

                time.sleep(2)  # Update every 2 seconds

            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
                time.sleep(5)

    async def start_server(self):
        """Start both WebSocket and REST API servers with TLS/HTTPS support"""
        # Determine protocol and ports
        ws_protocol = "wss" if self.cert_file and self.key_file else "ws"
        rest_protocol = "https" if self.cert_file and self.key_file else "http"

        logger.info(f"Starting Swarm Monitor Server on {self.host}")
        logger.info(f"Security: {'TLS/HTTPS enabled' if self.cert_file else 'No encryption (development mode)'}")
        logger.info(f"WebSocket: {ws_protocol}://{self.host}:{self.ws_port}/swarm-monitor")
        logger.info(f"REST API: {rest_protocol}://{self.host}:{self.rest_port}")

        # Store the event loop for thread communication
        self.loop = asyncio.get_running_loop()

        # Start event aggregation service if enabled
        if self.event_aggregation:
            await self.event_aggregation.start_service()
            logger.info("Event Aggregation Service started for high-volume processing")

        # Generate initial mock data
        self.generate_mock_data()

        # Start simulation in background thread
        self.running = True
        simulation_thread = threading.Thread(target=self.simulation_loop, daemon=True)
        simulation_thread.start()

        # Create SSL context if certificates provided
        ssl_context = self.security_manager.create_ssl_context()

        # Create REST API app
        rest_app = self.create_rest_app()
        self.rest_server = web.AppRunner(rest_app)
        await self.rest_server.setup()

        # Start REST API server with SSL if available
        if ssl_context:
            rest_site = web.TCPSite(self.rest_server, self.host, self.rest_port, ssl_context=ssl_context)
            logger.info(f"REST API server started with TLS on {rest_protocol}://{self.host}:{self.rest_port}")
        else:
            rest_site = web.TCPSite(self.rest_server, self.host, self.rest_port)
            logger.info(f"REST API server started on {rest_protocol}://{self.host}:{self.rest_port}")

        await rest_site.start()

        # Start WebSocket server with SSL if available
        if ssl_context:
            ws_server = await websockets.serve(
                self.handle_client,
                self.host,
                self.ws_port,
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=10
            )
            logger.info(f"WebSocket server started with TLS on {ws_protocol}://{self.host}:{self.ws_port}/swarm-monitor")
        else:
            ws_server = await websockets.serve(
                self.handle_client,
                self.host,
                self.ws_port,
                ping_interval=30,
                ping_timeout=10
            )
            logger.info(f"WebSocket server started on {ws_protocol}://{self.host}:{self.ws_port}/swarm-monitor")

        # Set up event bus subscriptions for broadcasting
        self.event_bus.subscribe("node_status", self._broadcast_node_update)
        self.event_bus.subscribe("task_update", self._broadcast_task_update)
        self.event_bus.subscribe("discovery_event", self._broadcast_discovery_event)
        self.event_bus.subscribe("security_event", self._broadcast_security_event)

        try:
            # Run both servers concurrently
            await asyncio.gather(
                ws_server.wait_closed(),
                asyncio.sleep(float('inf'))  # Keep REST server running
            )
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        finally:
            self.running = False

            # Stop event aggregation service
            if self.event_aggregation:
                await self.event_aggregation.stop_service()

            await self.rest_server.cleanup()
            simulation_thread.join(timeout=5)

    async def _broadcast_node_update(self, event):
        """Broadcast node status updates"""
        await self.broadcast_update("node_status_update", {"node": event.get("data", {})})

    async def _broadcast_task_update(self, event):
        """Broadcast task updates"""
        await self.broadcast_update("task_queue_update", {"tasks": self.task_queues})

    async def _broadcast_discovery_event(self, event):
        """Broadcast discovery events"""
        await self.broadcast_update("discovery_event", {"event": event.get("data", {})})

    async def _broadcast_security_event(self, event):
        """Broadcast security events"""
        await self.broadcast_update("security_event", {"event": event.get("data", {})})

    def _generate_swarm_density_data(self):
        """Generate swarm density heatmap data"""
        grid_size = 10
        density = [[0 for _ in range(grid_size)] for _ in range(grid_size)]

        for i, (node_id, node) in enumerate(self.swarm_nodes.items()):
            # Create a simple mapping based on node index and activity
            grid_x = (ord(node_id[-1]) - ord('0')) % grid_size if node_id[-1].isdigit() else i % grid_size
            grid_y = (node.get("tasks", 0) + node.get("load", 0)) // 20  # Activity level determines Y position
            if grid_x < grid_size and grid_y < grid_size:
                density[grid_y][grid_x] += node.get("tasks", 1)

        return density

    def _generate_network_utilization_data(self):
        """Generate network utilization heatmap data"""
        grid_size = 10
        utilization = [[0 for _ in range(grid_size)] for _ in range(grid_size)]

        for i, (node1_id, node1) in enumerate(self.swarm_nodes.items()):
            for j, (node2_id, node2) in enumerate(self.swarm_nodes.items()):
                if i != j:
                    # Simulate network connections between nearby nodes
                    distance = abs(i - j)
                    if distance <= 2:  # Close proximity = higher utilization
                        grid_x = i % grid_size
                        grid_y = j % grid_size
                        if grid_x < grid_size and grid_y < grid_size:
                            utilization[grid_y][grid_x] += (node1.get("tasks", 0) + node2.get("tasks", 0))

        return utilization

    def _generate_load_balancing_data(self):
        """Generate load balancing heatmap data"""
        grid_size = 10
        load_balance = [[0 for _ in range(grid_size)] for _ in range(grid_size)]

        for i, (node_id, node) in enumerate(self.swarm_nodes.items()):
            load = node.get("load", 0)
            grid_x = i % grid_size
            grid_y = min(load // 10, grid_size - 1)  # Load level determines Y position
            if grid_x < grid_size and grid_y < grid_size:
                load_balance[grid_y][grid_x] = load

        return load_balance


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Secure Swarm Monitor Server (WebSocket + REST API with TLS)")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--ws-port", type=int, default=8001, help="WebSocket server port")
    parser.add_argument("--rest-port", type=int, default=8002, help="REST API server port")
    parser.add_argument("--cert-file", help="Path to TLS certificate file (.pem or .crt)")
    parser.add_argument("--key-file", help="Path to TLS private key file (.key)")
    parser.add_argument("--credentials-file", default="credentials.json", help="Path to credentials storage file")
    parser.add_argument("--audit-log", default="audit.log", help="Path to audit log file")
    parser.add_argument("--enable-aggregation", action="store_true", default=True, help="Enable event aggregation service")
    parser.add_argument("--max-aggregation-queue", type=int, default=100000, help="Maximum events in aggregation queue")

    args = parser.parse_args()

    # Validate TLS configuration
    if (args.cert_file and not args.key_file) or (args.key_file and not args.cert_file):
        parser.error("Both --cert-file and --key-file must be provided for TLS")

    server = SwarmMonitorServer(
        host=args.host,
        ws_port=args.ws_port,
        rest_port=args.rest_port,
        cert_file=args.cert_file,
        key_file=args.key_file,
        credentials_file=args.credentials_file,
        audit_log_file=args.audit_log,
        enable_aggregation=args.enable_aggregation,
        max_aggregation_queue=args.max_aggregation_queue
    )

    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    main()