"""
Async Agent Framework for Horizontal Scaling
Provides high-concurrency agent execution with load balancing and resource management
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading
from enum import Enum

from ..core.base import BaseAgent, AgentRole, Message, MessageType, Task, logger
from ..message_queue import message_queue


class AgentState(Enum):
    """Agent execution states"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class AgentLoad:
    """Represents agent load and capacity"""
    agent_id: str
    current_load: int
    max_capacity: int
    active_tasks: int
    queue_size: int
    last_heartbeat: float

    @property
    def utilization(self) -> float:
        """Calculate current utilization percentage"""
        return (self.current_load / self.max_capacity) * 100 if self.max_capacity > 0 else 0

    @property
    def available_capacity(self) -> int:
        """Calculate available capacity"""
        return max(0, self.max_capacity - self.current_load)


class AsyncAgent(BaseAgent):
    """
    Enhanced async agent with concurrency support and load management
    """

    def __init__(self, agent_id: str, role: AgentRole, max_concurrent_tasks: int = 5):
        super().__init__(agent_id, role)
        self.max_concurrent_tasks = max_concurrent_tasks
        self.state = AgentState.IDLE
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_tasks, thread_name_prefix=f"agent-{agent_id}")
        self.load_metrics = AgentLoad(
            agent_id=agent_id,
            current_load=0,
            max_capacity=max_concurrent_tasks,
            active_tasks=0,
            queue_size=0,
            last_heartbeat=time.time()
        )

        # Async event loop management
        self._loop = None
        self._running = False
        self._task_processor = None

    async def start(self):
        """Start the async agent"""
        if self._running:
            return

        self._running = True
        self.state = AgentState.IDLE
        self._loop = asyncio.get_event_loop()

        # Subscribe to messages
        await message_queue.subscribe(self.agent_id, self._handle_message)

        # Start task processor
        self._task_processor = asyncio.create_task(self._process_task_queue())

        # Start heartbeat
        asyncio.create_task(self._heartbeat_loop())

        logger.log("INFO", f"AsyncAgent-{self.agent_id}", f"Started with capacity {self.max_concurrent_tasks}")

    async def stop(self):
        """Stop the async agent"""
        if not self._running:
            return

        self._running = False
        self.state = AgentState.SHUTDOWN

        # Cancel all active tasks
        for task_id, task in self.active_tasks.items():
            if not task.done():
                task.cancel()

        # Cancel task processor
        if self._task_processor and not self._task_processor.done():
            self._task_processor.cancel()

        # Shutdown executor
        self.executor.shutdown(wait=True)

        # Unsubscribe from messages
        await message_queue.unsubscribe(self.agent_id)

        logger.log("INFO", f"AsyncAgent-{self.agent_id}", "Stopped")

    async def _handle_message(self, message: Message):
        """Handle incoming messages"""
        if message.message_type == MessageType.TASK_ASSIGNMENT:
            task_data = message.content.get("task")
            if task_data:
                await self._enqueue_task(task_data)
        else:
            # Handle other message types
            await self.process_message(message)

    async def _enqueue_task(self, task_data: Dict[str, Any]):
        """Enqueue a task for processing"""
        await self.task_queue.put(task_data)
        self.load_metrics.queue_size = self.task_queue.qsize()
        self._update_state()

    async def _process_task_queue(self):
        """Process tasks from the queue with concurrency control"""
        while self._running:
            try:
                # Wait for a task with timeout
                task_data = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                self.load_metrics.queue_size = self.task_queue.qsize()

                # Check if we can handle more concurrent tasks
                if len(self.active_tasks) >= self.max_concurrent_tasks:
                    # Put back in queue and wait
                    await self.task_queue.put(task_data)
                    await asyncio.sleep(0.1)
                    continue

                # Create and start task
                task_id = task_data.get("task_id", f"task_{int(time.time())}")
                task = asyncio.create_task(self._execute_task_async(task_id, task_data))
                self.active_tasks[task_id] = task
                self.load_metrics.active_tasks = len(self.active_tasks)
                self._update_state()

                # Clean up completed tasks
                await self._cleanup_completed_tasks()

            except asyncio.TimeoutError:
                # No tasks available, continue
                continue
            except Exception as e:
                logger.log("ERROR", f"AsyncAgent-{self.agent_id}", f"Error processing task queue: {e}")
                await asyncio.sleep(1)

    async def _execute_task_async(self, task_id: str, task_data: Dict[str, Any]) -> Any:
        """Execute a task asynchronously"""
        try:
            self.load_metrics.current_load += 1
            self.state = AgentState.BUSY

            # Create task object
            task = Task(
                task_id=task_id,
                description=task_data.get("description", ""),
                metadata=task_data,
                assigned_agent=self.agent_id
            )

            # Execute in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.executor, self.execute_task, task)

            # Send completion message
            completion_message = Message(
                sender=self.agent_id,
                receiver="coordinator",
                message_type=MessageType.TASK_COMPLETED,
                content={
                    "task_id": task_id,
                    "result": result,
                    "execution_time": time.time() - task.created_at if hasattr(task, 'created_at') else 0
                },
                timestamp=time.time()
            )
            await message_queue.publish_message(completion_message)

            return result

        except Exception as e:
            logger.log("ERROR", f"AsyncAgent-{self.agent_id}", f"Task {task_id} failed: {e}")
            self.state = AgentState.ERROR

            # Send failure message
            failure_message = Message(
                sender=self.agent_id,
                receiver="coordinator",
                message_type=MessageType.TASK_FAILED,
                content={
                    "task_id": task_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                timestamp=time.time()
            )
            await message_queue.publish_message(failure_message)

            raise
        finally:
            self.load_metrics.current_load = max(0, self.load_metrics.current_load - 1)
            self._update_state()

    async def _cleanup_completed_tasks(self):
        """Clean up completed tasks from active tasks dict"""
        completed_tasks = []
        for task_id, task in self.active_tasks.items():
            if task.done():
                completed_tasks.append(task_id)
                try:
                    # Get result to propagate any exceptions
                    task.result()
                except Exception as e:
                    logger.log("ERROR", f"AsyncAgent-{self.agent_id}", f"Task {task_id} completed with error: {e}")

        for task_id in completed_tasks:
            del self.active_tasks[task_id]

        self.load_metrics.active_tasks = len(self.active_tasks)

    def _update_state(self):
        """Update agent state based on current load"""
        if self.state == AgentState.SHUTDOWN:
            return

        if len(self.active_tasks) > 0:
            self.state = AgentState.BUSY
        elif self.task_queue.qsize() > 0:
            self.state = AgentState.BUSY  # Has queued work
        else:
            self.state = AgentState.IDLE

    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages"""
        while self._running:
            try:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds

                heartbeat_message = Message(
                    sender=self.agent_id,
                    receiver="coordinator",
                    message_type=MessageType.HEARTBEAT,
                    content={
                        "agent_id": self.agent_id,
                        "state": self.state.value,
                        "load_metrics": {
                            "current_load": self.load_metrics.current_load,
                            "max_capacity": self.load_metrics.max_capacity,
                            "active_tasks": self.load_metrics.active_tasks,
                            "queue_size": self.load_metrics.queue_size,
                            "utilization": self.load_metrics.utilization
                        },
                        "timestamp": time.time()
                    },
                    timestamp=time.time()
                )

                await message_queue.publish_message(heartbeat_message)
                self.load_metrics.last_heartbeat = time.time()

            except Exception as e:
                logger.log("ERROR", f"AsyncAgent-{self.agent_id}", f"Heartbeat failed: {e}")

    def get_load_metrics(self) -> AgentLoad:
        """Get current load metrics"""
        return self.load_metrics

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "active_tasks": len(self.active_tasks),
            "queue_size": self.task_queue.qsize(),
            "utilization": self.load_metrics.utilization,
            "last_heartbeat": self.load_metrics.last_heartbeat,
            "healthy": self.state != AgentState.ERROR and time.time() - self.load_metrics.last_heartbeat < 60
        }


class AgentPool:
    """
    Pool of async agents with load balancing and scaling
    """

    def __init__(self, agent_factory: Callable[[str], AsyncAgent], min_agents: int = 1, max_agents: int = 10):
        self.agent_factory = agent_factory
        self.min_agents = min_agents
        self.max_agents = max_agents
        self.agents: Dict[str, AsyncAgent] = {}
        self.agent_loads: Dict[str, AgentLoad] = {}
        self._scaling_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the agent pool"""
        if self._running:
            return

        self._running = True

        # Start minimum agents
        for i in range(self.min_agents):
            agent_id = f"agent_{i+1}"
            await self._start_agent(agent_id)

        # Start scaling monitor
        self._scaling_task = asyncio.create_task(self._scaling_loop())

        logger.log("INFO", "AgentPool", f"Started with {self.min_agents} agents (min: {self.min_agents}, max: {self.max_agents})")

    async def stop(self):
        """Stop the agent pool"""
        if not self._running:
            return

        self._running = False

        # Stop scaling task
        if self._scaling_task and not self._scaling_task.done():
            self._scaling_task.cancel()

        # Stop all agents
        stop_tasks = [agent.stop() for agent in self.agents.values()]
        await asyncio.gather(*stop_tasks, return_exceptions=True)

        logger.log("INFO", "AgentPool", f"Stopped {len(self.agents)} agents")

    async def _start_agent(self, agent_id: str):
        """Start a new agent"""
        if len(self.agents) >= self.max_agents:
            logger.log("WARNING", "AgentPool", f"Cannot start agent {agent_id}: at max capacity {self.max_agents}")
            return

        agent = self.agent_factory(agent_id)
        await agent.start()
        self.agents[agent_id] = agent
        self.agent_loads[agent_id] = agent.get_load_metrics()

        logger.log("INFO", "AgentPool", f"Started agent {agent_id}")

    async def _stop_agent(self, agent_id: str):
        """Stop an agent"""
        if agent_id not in self.agents:
            return

        agent = self.agents[agent_id]
        await agent.stop()
        del self.agents[agent_id]
        del self.agent_loads[agent_id]

        logger.log("INFO", "AgentPool", f"Stopped agent {agent_id}")

    async def _scaling_loop(self):
        """Monitor load and scale agents as needed"""
        while self._running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds

                # Update load metrics
                for agent_id, agent in self.agents.items():
                    self.agent_loads[agent_id] = agent.get_load_metrics()

                # Calculate pool metrics
                total_load = sum(load.current_load for load in self.agent_loads.values())
                total_capacity = sum(load.max_capacity for load in self.agent_loads.values())
                avg_utilization = (total_load / total_capacity) * 100 if total_capacity > 0 else 0

                # Check for scaling decisions
                if avg_utilization > 80 and len(self.agents) < self.max_agents:
                    # Scale up
                    agent_id = f"agent_{len(self.agents) + 1}"
                    await self._start_agent(agent_id)
                    logger.log("INFO", "AgentPool", f"Scaled up to {len(self.agents)} agents (utilization: {avg_utilization:.1f}%)")

                elif avg_utilization < 30 and len(self.agents) > self.min_agents:
                    # Find least utilized agent to scale down
                    least_utilized = min(self.agent_loads.items(), key=lambda x: x[1].utilization)
                    agent_id = least_utilized[0]

                    # Only scale down if agent is idle
                    if least_utilized[1].current_load == 0:
                        await self._stop_agent(agent_id)
                        logger.log("INFO", "AgentPool", f"Scaled down to {len(self.agents)} agents (utilization: {avg_utilization:.1f}%)")

            except Exception as e:
                logger.log("ERROR", "AgentPool", f"Error in scaling loop: {e}")

    def get_least_loaded_agent(self) -> Optional[str]:
        """Get the least loaded agent"""
        if not self.agent_loads:
            return None

        return min(self.agent_loads.items(), key=lambda x: x[1].utilization)[0]

    def get_pool_metrics(self) -> Dict[str, Any]:
        """Get pool-wide metrics"""
        if not self.agent_loads:
            return {"total_agents": 0, "total_load": 0, "total_capacity": 0, "avg_utilization": 0}

        total_load = sum(load.current_load for load in self.agent_loads.values())
        total_capacity = sum(load.max_capacity for load in self.agent_loads.values())
        avg_utilization = (total_load / total_capacity) * 100 if total_capacity > 0 else 0

        return {
            "total_agents": len(self.agents),
            "active_agents": len([a for a in self.agents.values() if a.state != AgentState.IDLE]),
            "total_load": total_load,
            "total_capacity": total_capacity,
            "avg_utilization": avg_utilization,
            "min_utilization": min((load.utilization for load in self.agent_loads.values()), default=0),
            "max_utilization": max((load.utilization for load in self.agent_loads.values()), default=0)
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all agents"""
        health_results = {}
        for agent_id, agent in self.agents.items():
            try:
                health_results[agent_id] = await agent.health_check()
            except Exception as e:
                health_results[agent_id] = {
                    "agent_id": agent_id,
                    "state": "error",
                    "error": str(e),
                    "healthy": False
                }

        pool_metrics = self.get_pool_metrics()

        return {
            "pool_health": pool_metrics,
            "agent_health": health_results,
            "overall_healthy": all(result.get("healthy", False) for result in health_results.values())
        }


class LoadBalancer:
    """
    Load balancer for distributing tasks across agent pools
    """

    def __init__(self):
        self.pools: Dict[str, AgentPool] = {}
        self.routing_rules: Dict[str, Callable[[Dict[str, Any]], str]] = {}

    def add_pool(self, pool_name: str, pool: AgentPool):
        """Add an agent pool"""
        self.pools[pool_name] = pool

    def add_routing_rule(self, task_type: str, rule: Callable[[Dict[str, Any]], str]):
        """Add routing rule for task type"""
        self.routing_rules[task_type] = rule

    def route_task(self, task_data: Dict[str, Any]) -> Optional[str]:
        """Route a task to the appropriate pool"""
        task_type = task_data.get("type", "general")

        # Check for specific routing rule
        if task_type in self.routing_rules:
            pool_name = self.routing_rules[task_type](task_data)
            if pool_name in self.pools:
                return pool_name

        # Default: route to least loaded pool
        return self._find_least_loaded_pool()

    def _find_least_loaded_pool(self) -> Optional[str]:
        """Find the least loaded pool"""
        if not self.pools:
            return None

        pool_metrics = {}
        for pool_name, pool in self.pools.items():
            pool_metrics[pool_name] = pool.get_pool_metrics()

        # Find pool with lowest average utilization
        return min(pool_metrics.items(), key=lambda x: x[1]["avg_utilization"])[0]

    def get_routing_metrics(self) -> Dict[str, Any]:
        """Get routing metrics for all pools"""
        metrics = {}
        for pool_name, pool in self.pools.items():
            metrics[pool_name] = pool.get_pool_metrics()

        return metrics


# Global instances
agent_pool: Optional[AgentPool] = None
load_balancer = LoadBalancer()


def create_async_agent(agent_id: str, agent_type: str = "language_agent") -> AsyncAgent:
    """Factory function for creating async agents"""
    from ..plugin_registry import agent_registry

    # Create base agent from registry
    base_agent = agent_registry.create_agent(agent_type, agent_id, swarm_id="async_pool")
    if not base_agent:
        raise ValueError(f"Unknown agent type: {agent_type}")

    # Wrap in async agent
    async_agent = AsyncAgent(agent_id, base_agent.role, max_concurrent_tasks=3)
    # Copy methods from base agent
    async_agent.execute_task = base_agent.execute_task
    async_agent.process_message = base_agent.process_message

    return async_agent


async def initialize_async_agents(min_agents: int = 2, max_agents: int = 10, agent_types: Optional[List[str]] = None):
    """Initialize the async agent pool"""
    global agent_pool

    if agent_types is None:
        # Default mix of agent types
        agent_types = ["language_agent", "math_agent", "vision_agent", "simulation_agent"]

    # Create agent factory that cycles through agent types
    def agent_factory_with_types(agent_id: str) -> AsyncAgent:
        # Cycle through agent types based on agent_id hash
        type_index = hash(agent_id) % len(agent_types)
        agent_type = agent_types[type_index]
        return create_async_agent(agent_id, agent_type)

    agent_pool = AgentPool(
        agent_factory=agent_factory_with_types,
        min_agents=min_agents,
        max_agents=max_agents
    )

    await agent_pool.start()

    # Add to load balancer
    load_balancer.add_pool("default", agent_pool)

    logger.log("INFO", "AsyncAgents", f"Initialized agent pool with {min_agents}-{max_agents} agents using types: {agent_types}")


async def shutdown_async_agents():
    """Shutdown the async agent pool"""
    global agent_pool

    if agent_pool:
        await agent_pool.stop()
        agent_pool = None

    logger.log("INFO", "AsyncAgents", "Shutdown complete")