#!/usr/bin/env python3
"""
Federation Demo - Demonstrates the complete Brain Swarm Federation

This script shows how to use the FederationOrchestrator to create
a fully integrated federation with discovery, connections, and cross-swarm coordination.
"""

import asyncio
import logging
import argparse
import sys
from typing import Dict, Any

# Add the parent directory to the path so we can import brain_swarm
sys.path.insert(0, '.')

from brain_swarm.federation.federation import (
    FederationOrchestrator,
    SharedTask,
    MemorySync,
    AnalyticsData
)
from brain_swarm.memory import WorkingMemory  # Optional
from brain_swarm.analytics.predictive_analytics import TaskCompletionPredictor  # Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FederationDemo:
    """Demonstration of the complete federation system."""

    def __init__(self, swarm_id: str, node_name: str):
        self.swarm_id = swarm_id
        self.node_name = node_name
        self.orchestrator: FederationOrchestrator = None

    async def initialize(self):
        """Initialize the federation orchestrator."""
        logger.info(f"Initializing federation demo for {self.swarm_id}")

        # Create orchestrator with custom config
        config = {
            "discovery": {
                "enabled": True,
                "broadcast_port": 9999,
                "api_port": 8000,
                "broadcast_interval": 10.0,  # Faster for demo
            },
            "connection": {
                "auth_token": "demo-federation-token",
                "reconnect_interval": 15.0,
            },
            "sharing": {
                "enable_task_sharing": True,
                "enable_memory_sync": True,
                "enable_analytics_sharing": True,
                "auto_discovery_connections": True,
            }
        }

        self.orchestrator = FederationOrchestrator(
            local_swarm_id=self.swarm_id,
            local_node_name=self.node_name,
            federation_config=config
        )

        # Set up optional integrations (if available)
        try:
            memory_manager = WorkingMemory()
            self.orchestrator.set_memory_manager(memory_manager)
            logger.info("Memory manager integrated")
        except ImportError:
            logger.info("Memory manager not available")

        try:
            analytics_manager = TaskCompletionPredictor()
            self.orchestrator.set_analytics_manager(analytics_manager)
            logger.info("Analytics manager integrated")
        except ImportError:
            logger.info("Analytics manager not available")

        # Set up federation callbacks
        self.orchestrator.federation_manager.on_task_received = self.on_task_received
        self.orchestrator.federation_manager.on_memory_update = self.on_memory_update
        self.orchestrator.federation_manager.on_analytics_received = self.on_analytics_received

        await self.orchestrator.initialize()
        logger.info("Federation demo initialized")

    async def start(self):
        """Start the federation."""
        await self.orchestrator.start()
        logger.info(f"Federation started for {self.swarm_id}")

    async def stop(self):
        """Stop the federation."""
        await self.orchestrator.stop()
        logger.info(f"Federation stopped for {self.swarm_id}")

    def on_task_received(self, task: SharedTask):
        """Handle received task."""
        logger.info(f"🎯 Received shared task: {task.task_id} ({task.task_type}) from {task.origin_swarm}")

    def on_memory_update(self, memory: MemorySync):
        """Handle memory update."""
        logger.info(f"🧠 Received memory sync: {memory.memory_type}:{memory.key} from {memory.origin_swarm}")

    def on_analytics_received(self, analytics: AnalyticsData):
        """Handle analytics data."""
        logger.info(f"📊 Received analytics: {analytics.data_type} from {analytics.origin_swarm}")

    async def demo_task_sharing(self):
        """Demonstrate task sharing."""
        logger.info("🚀 Demonstrating task sharing...")

        # Create a sample task
        task = SharedTask(
            task_id=f"demo-task-{self.swarm_id}",
            task_type="computation",
            priority=1,
            payload={"operation": "calculate", "parameters": [1, 2, 3, 4, 5]},
            origin_swarm=self.swarm_id,
            created_at=asyncio.get_event_loop().time()
        )

        # Share the task
        success = await self.orchestrator.share_task_federation_wide(task)
        if success:
            logger.info(f"✅ Task {task.task_id} shared with federation")
        else:
            logger.warning("❌ Failed to share task")

    async def demo_memory_sync(self):
        """Demonstrate memory synchronization."""
        logger.info("🧠 Demonstrating memory synchronization...")

        # Create sample memory data
        memory = MemorySync(
            memory_type="episodic",
            key=f"demo-experience-{self.swarm_id}",
            value={"event": "federation_demo", "outcome": "successful", "timestamp": asyncio.get_event_loop().time()},
            origin_swarm=self.swarm_id,
            timestamp=asyncio.get_event_loop().time(),
            ttl=3600.0  # 1 hour
        )

        # Share memory
        success = await self.orchestrator.synchronize_memory_federation(memory)
        if success:
            logger.info(f"✅ Memory synchronized: {memory.key}")
        else:
            logger.warning("❌ Failed to synchronize memory")

    async def demo_analytics_sharing(self):
        """Demonstrate analytics sharing."""
        logger.info("📊 Demonstrating analytics sharing...")

        # Create sample analytics data
        analytics = AnalyticsData(
            data_type="performance_metrics",
            metrics={
                "tasks_completed": 42,
                "average_completion_time": 45.2,
                "success_rate": 0.95,
                "load_factor": 0.7
            },
            origin_swarm=self.swarm_id,
            time_range=(asyncio.get_event_loop().time() - 3600, asyncio.get_event_loop().time()),
            timestamp=asyncio.get_event_loop().time()
        )

        # Share analytics
        success = await self.orchestrator.broadcast_analytics_federation(analytics)
        if success:
            logger.info(f"✅ Analytics shared: {analytics.data_type}")
        else:
            logger.warning("❌ Failed to share analytics")

    async def demo_resource_request(self):
        """Demonstrate resource requesting."""
        logger.info("🔍 Demonstrating resource requests...")

        requirements = {
            "cpu_cores": 2,
            "memory_gb": 4,
            "task_types": ["computation", "analysis"]
        }

        resources = await self.orchestrator.request_federation_resources(requirements)
        if resources:
            logger.info(f"✅ Found resources from {len(resources)} swarms:")
            for swarm_id, res in resources.items():
                logger.info(f"  - {swarm_id}: {res}")
        else:
            logger.info("ℹ️  No resources available or no connected swarms")

    def show_status(self):
        """Show current federation status."""
        status = self.orchestrator.get_federation_status()
        logger.info("📈 Federation Status:")
        logger.info(f"  Running: {status['is_running']}")
        logger.info(f"  Swarm ID: {status['local_swarm_id']}")
        logger.info(f"  Uptime: {status['uptime']:.1f} seconds")

        if 'discovery' in status:
            discovery = status['discovery']
            logger.info(f"  Discovery: {discovery['is_running']} ({discovery['discovered_swarms_count']} swarms discovered)")

        if 'federation' in status:
            fed = status['federation']
            logger.info(f"  Federation: {fed['total_connected_swarms']} connected swarms")
            logger.info(f"  Shared Tasks: {fed['shared_tasks_count']}")
            logger.info(f"  Memory Cache: {fed['memory_cache_size']} entries")
            logger.info(f"  Analytics Cache: {fed['analytics_cache_size']} entries")


async def run_interactive_demo(swarm_id: str, node_name: str):
    """Run an interactive federation demo."""
    demo = FederationDemo(swarm_id, node_name)

    try:
        await demo.initialize()
        await demo.start()

        print("\n" + "="*60)
        print("🧠 BRAIN SWARM FEDERATION DEMO")
        print("="*60)
        print(f"Swarm ID: {swarm_id}")
        print(f"Node Name: {node_name}")
        print("\nCommands:")
        print("  status    - Show federation status")
        print("  task      - Share a demo task")
        print("  memory    - Synchronize demo memory")
        print("  analytics - Share demo analytics")
        print("  resources - Request federation resources")
        print("  quit      - Exit demo")
        print("="*60 + "\n")

        while True:
            try:
                cmd = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input(f"{swarm_id}> ").strip().lower()
                )

                if cmd == "status":
                    demo.show_status()
                elif cmd == "task":
                    await demo.demo_task_sharing()
                elif cmd == "memory":
                    await demo.demo_memory_sync()
                elif cmd == "analytics":
                    await demo.demo_analytics_sharing()
                elif cmd == "resources":
                    await demo.demo_resource_request()
                elif cmd == "quit":
                    break
                else:
                    print("Unknown command. Type 'status', 'task', 'memory', 'analytics', 'resources', or 'quit'")

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Command error: {e}")

    except Exception as e:
        logger.error(f"Demo error: {e}")
    finally:
        if demo.orchestrator:
            await demo.stop()


async def run_auto_demo(swarm_id: str, node_name: str, duration: int = 60):
    """Run an automated federation demo."""
    demo = FederationDemo(swarm_id, node_name)

    try:
        await demo.initialize()
        await demo.start()

        logger.info(f"🚀 Starting automated demo for {duration} seconds...")

        # Wait for connections to establish
        await asyncio.sleep(5)

        # Run demo actions
        await demo.demo_task_sharing()
        await asyncio.sleep(3)

        await demo.demo_memory_sync()
        await asyncio.sleep(3)

        await demo.demo_analytics_sharing()
        await asyncio.sleep(3)

        await demo.demo_resource_request()

        # Show final status
        await asyncio.sleep(2)
        demo.show_status()

        # Keep running for the specified duration
        logger.info(f"Demo running for {duration} seconds... (press Ctrl+C to stop early)")
        await asyncio.sleep(duration)

    except KeyboardInterrupt:
        logger.info("Demo interrupted")
    except Exception as e:
        logger.error(f"Demo error: {e}")
    finally:
        if demo.orchestrator:
            await demo.stop()


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Brain Swarm Federation Demo")
    parser.add_argument("--swarm-id", default="demo-swarm",
                       help="Swarm ID for this demo instance")
    parser.add_argument("--node-name", default="demo-node",
                       help="Node name for this demo instance")
    parser.add_argument("--interactive", action="store_true",
                       help="Run interactive demo")
    parser.add_argument("--duration", type=int, default=60,
                       help="Duration for automated demo (seconds)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.interactive:
            logger.info("Starting interactive federation demo...")
            asyncio.run(run_interactive_demo(args.swarm_id, args.node_name))
        else:
            logger.info(f"Starting automated federation demo ({args.duration}s)...")
            asyncio.run(run_auto_demo(args.swarm_id, args.node_name, args.duration))

    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()