#!/usr/bin/env python3
"""
Example Swarm Client for Real-Time Swarm Monitor
Demonstrates how swarms can publish events via WebSocket and REST API
"""

import asyncio
import json
import random
import time
import websockets
import aiohttp
from typing import Dict, Any


class SwarmClient:
    """Example swarm client that publishes events to the monitor server"""

    def __init__(self, swarm_id: str, server_host: str = "localhost",
                 ws_port: int = 8001, rest_port: int = 8002,
                 use_websocket: bool = True):
        self.swarm_id = swarm_id
        self.server_host = server_host
        self.ws_port = ws_port
        self.rest_port = rest_port
        self.use_websocket = use_websocket
        self.websocket = None
        self.running = False

    async def connect_websocket(self):
        """Connect to WebSocket server for real-time publishing"""
        uri = f"ws://{self.server_host}:{self.ws_port}/swarm-monitor"
        try:
            self.websocket = await websockets.connect(uri)
            # Send client identification
            await self.websocket.send(json.dumps({
                "type": "identify",
                "client_type": "swarm",
                "swarm_id": self.swarm_id
            }))
            print(f"Swarm {self.swarm_id} connected via WebSocket")
            return True
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
            return False

    async def publish_event_websocket(self, event_type: str, event_data: Dict[str, Any]):
        """Publish event via WebSocket"""
        if not self.websocket:
            return False

        try:
            message = {
                "type": "swarm_event",
                "swarm_id": self.swarm_id,
                "event_type": event_type,
                "data": event_data
            }
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            print(f"WebSocket publish failed: {e}")
            return False

    async def publish_event_rest(self, event_type: str, event_data: Dict[str, Any]):
        """Publish event via REST API"""
        url = f"http://{self.server_host}:{self.rest_port}/api/events"

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "swarm_id": self.swarm_id,
                    "event_type": event_type,
                    "data": event_data
                }
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        print(f"REST publish failed: {response.status}")
                        return False
        except Exception as e:
            print(f"REST publish failed: {e}")
            return False

    async def publish_event(self, event_type: str, event_data: Dict[str, Any]):
        """Publish event using configured method"""
        if self.use_websocket:
            return await self.publish_event_websocket(event_type, event_data)
        else:
            return await self.publish_event_rest(event_type, event_data)

    async def simulate_swarm_activity(self):
        """Simulate realistic swarm activity"""
        print(f"Starting swarm {self.swarm_id} activity simulation...")

        # Simulate node status updates
        node_count = random.randint(3, 8)
        nodes = {}

        for i in range(node_count):
            node_id = f"node-{i+1}"
            nodes[node_id] = {
                "node_id": node_id,
                "name": f"Node {i+1}",
                "type": random.choice(["enterprise", "cloud", "home"]),
                "status": "starting",
                "load": random.randint(10, 30),
                "tasks": 0,
                "cpu_usage": random.randint(5, 20),
                "memory_usage": random.randint(20, 40)
            }

            # Publish node startup
            await self.publish_event("node_status", nodes[node_id])
            await asyncio.sleep(0.5)

        # Main activity loop
        while self.running:
            try:
                # Randomly update node statuses
                for node_id, node in nodes.items():
                    if random.random() < 0.3:  # 30% chance of update
                        # Update node metrics
                        node["load"] = max(5, min(95, node["load"] + random.randint(-10, 10)))
                        node["cpu_usage"] = max(5, min(95, node["cpu_usage"] + random.randint(-5, 5)))
                        node["memory_usage"] = max(10, min(90, node["memory_usage"] + random.randint(-5, 5)))

                        # Change status occasionally
                        if random.random() < 0.1:
                            statuses = ["active", "busy", "inactive"]
                            node["status"] = random.choice(statuses)

                        # Update task count
                        node["tasks"] = max(0, node["tasks"] + random.randint(-1, 2))

                        await self.publish_event("node_status", node)

                # Simulate task updates
                if random.random() < 0.4:  # 40% chance
                    task_id = f"task_{int(time.time())}_{random.randint(1000, 9999)}"
                    task_data = {
                        "task_id": task_id,
                        "description": random.choice([
                            "Process user authentication",
                            "Analyze data patterns",
                            "Generate recommendations",
                            "Update system metrics",
                            "Handle API requests"
                        ]),
                        "status": random.choice(["running", "completed", "failed"]),
                        "progress": random.randint(0, 100),
                        "assigned_node": f"node-{random.randint(1, node_count)}",
                        "priority": random.randint(1, 5),
                        "created_at": time.time()
                    }
                    await self.publish_event("task_update", task_data)

                # Simulate discovery events
                if random.random() < 0.2:  # 20% chance
                    discovery_data = {
                        "type": random.choice(["lan_broadcast", "registry_discovery"]),
                        "message": random.choice([
                            "LAN broadcast detected from 192.168.1.100",
                            "Registry discovery successful",
                            "UDP broadcast received on port 9999",
                            "HTTPS registry connection established"
                        ]),
                        "target_swarm": f"swarm-{random.randint(1, 5)}"
                    }
                    await self.publish_event("discovery_event", discovery_data)

                # Simulate security events
                if random.random() < 0.15:  # 15% chance
                    security_data = {
                        "type": random.choice(["auth_success", "tls_handshake", "auth_failure"]),
                        "message": random.choice([
                            "Authentication successful for user",
                            "TLS 1.3 handshake completed",
                            "Certificate validation successful",
                            "Authentication failed: invalid credentials"
                        ]),
                        "severity": random.choice(["low", "medium", "high"])
                    }
                    await self.publish_event("security_event", security_data)

                await asyncio.sleep(2)  # Update every 2 seconds

            except Exception as e:
                print(f"Error in swarm activity simulation: {e}")
                await asyncio.sleep(5)

    async def run(self):
        """Run the swarm client"""
        self.running = True

        if self.use_websocket:
            if not await self.connect_websocket():
                print("Falling back to REST API")
                self.use_websocket = False

        try:
            await self.simulate_swarm_activity()
        except KeyboardInterrupt:
            print(f"Swarm {self.swarm_id} stopping...")
        finally:
            self.running = False
            if self.websocket:
                await self.websocket.close()


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Swarm Client Example")
    parser.add_argument("--swarm-id", required=True, help="Swarm identifier")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--ws-port", type=int, default=8001, help="WebSocket port")
    parser.add_argument("--rest-port", type=int, default=8002, help="REST API port")
    parser.add_argument("--use-websocket", action="store_true", default=True, help="Use WebSocket for publishing")
    parser.add_argument("--use-rest", action="store_false", dest="use_websocket", help="Use REST API for publishing")

    args = parser.parse_args()

    client = SwarmClient(
        swarm_id=args.swarm_id,
        server_host=args.host,
        ws_port=args.ws_port,
        rest_port=args.rest_port,
        use_websocket=args.use_websocket
    )

    print(f"Starting Swarm Client {args.swarm_id}")
    print(f"Publishing method: {'WebSocket' if args.use_websocket else 'REST API'}")

    try:
        await client.run()
    except KeyboardInterrupt:
        print("Client stopped by user")


if __name__ == "__main__":
    asyncio.run(main())