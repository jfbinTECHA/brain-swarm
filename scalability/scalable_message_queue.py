"""
Scalable Message Queue with Redis Clustering and Partitioning
Provides horizontal scaling, load balancing, and high availability for message processing
"""

import asyncio
import json
import time
import hashlib
from typing import Dict, List, Any, Optional, Callable, Awaitable, Set
import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster
from dataclasses import dataclass
from enum import Enum

from ..core.base import Message, MessageType, logger
from ..message_queue import MessageQueue


class QueueMode(Enum):
    """Message queue modes"""
    SINGLE_NODE = "single_node"
    CLUSTER = "cluster"
    PARTITIONED = "partitioned"


@dataclass
class PartitionInfo:
    """Information about a message partition"""
    partition_id: int
    stream_name: str
    consumer_group: str
    node_id: str
    message_count: int
    last_processed: float


class ScalableMessageQueue:
    """
    Scalable message queue with Redis clustering and partitioning support
    """

    def __init__(self,
                 redis_urls: List[str],
                 mode: QueueMode = QueueMode.SINGLE_NODE,
                 partitions: int = 8,
                 consumer_name: str = None):
        self.redis_urls = redis_urls
        self.mode = mode
        self.partitions = partitions
        self.consumer_name = consumer_name or f"consumer_{id(self)}"

        # Core components
        self.redis: Optional[redis.Redis] = None
        self.cluster: Optional[RedisCluster] = None
        self.stream_prefix = "brain_swarm_messages"
        self.consumer_group_prefix = "brain_swarm_consumers"

        # Partitioning
        self.partitions_info: Dict[int, PartitionInfo] = {}
        self.node_id = f"node_{hash(self.consumer_name) % 1000}"

        # Subscriptions and processing
        self.subscribers: Dict[str, List[Callable]] = {}
        self.running = False
        self._processing_tasks: List[asyncio.Task] = []

        # Metrics
        self.messages_processed = 0
        self.messages_failed = 0
        self.processing_times: List[float] = []

    async def connect(self):
        """Connect to Redis with appropriate mode"""
        try:
            if self.mode == QueueMode.CLUSTER:
                # Redis Cluster mode
                self.cluster = RedisCluster.from_url(self.redis_urls[0])
                await self.cluster.ping()
                logger.log("INFO", "ScalableMessageQueue", f"Connected to Redis Cluster: {self.redis_urls[0]}")

            elif self.mode == QueueMode.PARTITIONED:
                # Partitioned mode - connect to multiple nodes
                self.redis = redis.from_url(self.redis_urls[0])
                await self.redis.ping()
                logger.log("INFO", "ScalableMessageQueue", f"Connected to Redis (partitioned mode): {self.redis_urls[0]}")

                # Initialize partitions
                await self._initialize_partitions()

            else:
                # Single node mode
                self.redis = redis.from_url(self.redis_urls[0])
                await self.redis.ping()
                logger.log("INFO", "ScalableMessageQueue", f"Connected to Redis (single node): {self.redis_urls[0]}")

        except Exception as e:
            logger.log("ERROR", "ScalableMessageQueue", f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.cluster:
            await self.cluster.aclose()
            self.cluster = None
        if self.redis:
            await self.redis.aclose()
            self.redis = None
        logger.log("INFO", "ScalableMessageQueue", "Disconnected from Redis")

    def _get_partition(self, key: str) -> int:
        """Get partition for a key using consistent hashing"""
        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return hash_value % self.partitions

    def _get_stream_name(self, partition: int) -> str:
        """Get stream name for partition"""
        return f"{self.stream_prefix}_p{partition}"

    def _get_consumer_group(self, partition: int) -> str:
        """Get consumer group for partition"""
        return f"{self.consumer_group_prefix}_p{partition}"

    async def _initialize_partitions(self):
        """Initialize partition information"""
        for partition in range(self.partitions):
            stream_name = self._get_stream_name(partition)
            consumer_group = self._get_consumer_group(partition)

            # Create consumer group if it doesn't exist
            try:
                await self.redis.xgroup_create(stream_name, consumer_group, "0", mkstream=True)
            except redis.ResponseError:
                # Group already exists
                pass

            # Initialize partition info
            self.partitions_info[partition] = PartitionInfo(
                partition_id=partition,
                stream_name=stream_name,
                consumer_group=consumer_group,
                node_id=self.node_id,
                message_count=0,
                last_processed=time.time()
            )

        logger.log("INFO", "ScalableMessageQueue", f"Initialized {self.partitions} partitions")

    async def publish_message(self, message: Message) -> str:
        """Publish a message to the appropriate partition"""
        if not self.redis and not self.cluster:
            raise RuntimeError("MessageQueue not connected")

        # Convert message to dict
        message_dict = {
            "sender": message.sender,
            "receiver": message.receiver,
            "message_type": message.message_type.value,
            "content": message.content,
            "timestamp": message.timestamp,
            "swarm_id": message.swarm_id,
            "metadata": message.metadata or {}
        }

        # Determine partition
        partition_key = message.receiver if message.receiver != "broadcast" else message.sender
        partition = self._get_partition(partition_key)

        # Get appropriate Redis client
        redis_client = self.cluster or self.redis
        stream_name = self._get_stream_name(partition) if self.mode == QueueMode.PARTITIONED else self.stream_prefix

        # Add to stream
        message_id = await redis_client.xadd(stream_name, message_dict)

        # Update partition info
        if partition in self.partitions_info:
            self.partitions_info[partition].message_count += 1

        logger.log("DEBUG", "ScalableMessageQueue", f"Published message {message_id} to partition {partition}")
        return message_id

    async def subscribe(self, recipient: str, callback: Callable[[Message], Awaitable[None]]):
        """Subscribe to messages for a specific recipient"""
        if recipient not in self.subscribers:
            self.subscribers[recipient] = []
        self.subscribers[recipient].append(callback)

        # Create consumer groups for relevant partitions
        if self.mode == QueueMode.PARTITIONED:
            partition = self._get_partition(recipient)
            consumer_group = self._get_consumer_group(partition)
            stream_name = self._get_stream_name(partition)

            try:
                await self.redis.xgroup_create(stream_name, consumer_group, "0", mkstream=True)
            except redis.ResponseError:
                pass

        logger.log("INFO", "ScalableMessageQueue", f"Subscribed to messages for {recipient}")

    async def start_listening(self):
        """Start listening for messages"""
        if self.running:
            return

        self.running = True

        if self.mode == QueueMode.PARTITIONED:
            # Start partition processors
            for partition in range(self.partitions):
                task = asyncio.create_task(self._process_partition(partition))
                self._processing_tasks.append(task)
        else:
            # Single stream processing
            task = asyncio.create_task(self._process_single_stream())
            self._processing_tasks.append(task)

        logger.log("INFO", "ScalableMessageQueue", f"Started listening with {len(self._processing_tasks)} processors")

    async def stop_listening(self):
        """Stop listening for messages"""
        self.running = False

        # Cancel all processing tasks
        for task in self._processing_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._processing_tasks, return_exceptions=True)
        self._processing_tasks.clear()

        logger.log("INFO", "ScalableMessageQueue", "Stopped listening")

    async def _process_partition(self, partition: int):
        """Process messages for a specific partition"""
        partition_info = self.partitions_info[partition]
        stream_name = partition_info.stream_name
        consumer_group = partition_info.consumer_group

        last_id = "0"

        while self.running:
            try:
                # Read from partition stream
                messages = await self.redis.xreadgroup(
                    consumer_group,
                    self.consumer_name,
                    {stream_name: last_id},
                    count=10,
                    block=1000  # Block for 1 second
                )

                for stream_name_read, message_list in messages:
                    for message_id, message_data in message_list:
                        await self._process_message(message_id, message_data, partition)
                        last_id = message_id
                        partition_info.last_processed = time.time()

                # Acknowledge processed messages
                if messages:
                    await self.redis.xack(stream_name, consumer_group, last_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.log("ERROR", "ScalableMessageQueue", f"Error in partition {partition} processor: {e}")
                await asyncio.sleep(1)

    async def _process_single_stream(self):
        """Process messages from single stream (non-partitioned mode)"""
        consumer_group = f"{self.consumer_group_prefix}_single"
        last_id = "0"

        # Create consumer group
        try:
            await self.redis.xgroup_create(self.stream_prefix, consumer_group, "0", mkstream=True)
        except redis.ResponseError:
            pass

        while self.running:
            try:
                messages = await self.redis.xreadgroup(
                    consumer_group,
                    self.consumer_name,
                    {self.stream_prefix: last_id},
                    count=10,
                    block=1000  # Block for 1 second
                )

                for stream_name, message_list in messages:
                    for message_id, message_data in message_list:
                        await self._process_message(message_id, message_data, 0)
                        last_id = message_id

                # Acknowledge processed messages
                if messages:
                    await self.redis.xack(self.stream_prefix, consumer_group, last_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.log("ERROR", "ScalableMessageQueue", f"Error in single stream processor: {e}")
                await asyncio.sleep(1)

    async def _process_message(self, message_id: str, message_data: Dict[str, Any], partition: int):
        """Process a received message"""
        start_time = time.time()

        try:
            # Convert back to Message object
            message = Message(
                sender=message_data["sender"],
                receiver=message_data["receiver"],
                message_type=MessageType(message_data["message_type"]),
                content=message_data["content"],
                timestamp=message_data["timestamp"],
                swarm_id=message_data.get("swarm_id"),
                metadata=message_data.get("metadata")
            )

            # Deliver to subscribers
            recipient = message.receiver
            delivered = False

            if recipient in self.subscribers:
                for callback in self.subscribers[recipient]:
                    try:
                        await callback(message)
                        delivered = True
                    except Exception as e:
                        logger.log("ERROR", "ScalableMessageQueue", f"Error in message callback: {e}")

            # Also deliver to broadcast subscribers if it's a broadcast
            if recipient == "broadcast" and "broadcast" in self.subscribers:
                for callback in self.subscribers["broadcast"]:
                    try:
                        await callback(message)
                        delivered = True
                    except Exception as e:
                        logger.log("ERROR", "ScalableMessageQueue", f"Error in broadcast callback: {e}")

            if delivered:
                self.messages_processed += 1
                processing_time = time.time() - start_time
                self.processing_times.append(processing_time)

                # Keep only last 1000 processing times
                if len(self.processing_times) > 1000:
                    self.processing_times.pop(0)
            else:
                logger.log("WARNING", "ScalableMessageQueue", f"No subscribers for message to {recipient}")

        except Exception as e:
            self.messages_failed += 1
            logger.log("ERROR", "ScalableMessageQueue", f"Error processing message {message_id}: {e}")

    async def broadcast_message(self, message: Message) -> List[str]:
        """Broadcast a message to all partitions"""
        message_ids = []

        if self.mode == QueueMode.PARTITIONED:
            # Send to all partitions
            for partition in range(self.partitions):
                # Create partition-specific message
                partition_message = Message(
                    sender=message.sender,
                    receiver=f"broadcast_p{partition}",
                    message_type=message.message_type,
                    content=message.content,
                    timestamp=message.timestamp,
                    swarm_id=message.swarm_id,
                    metadata={**message.metadata, "broadcast": True, "partition": partition} if message.metadata else {"broadcast": True, "partition": partition}
                )

                message_id = await self.publish_message(partition_message)
                message_ids.append(message_id)
        else:
            # Single stream broadcast
            broadcast_message = Message(
                sender=message.sender,
                receiver="broadcast",
                message_type=message.message_type,
                content=message.content,
                timestamp=message.timestamp,
                swarm_id=message.swarm_id,
                metadata={**message.metadata, "broadcast": True} if message.metadata else {"broadcast": True}
            )

            message_id = await self.publish_message(broadcast_message)
            message_ids.append(message_id)

        return message_ids

    def get_metrics(self) -> Dict[str, Any]:
        """Get queue metrics"""
        total_messages = self.messages_processed + self.messages_failed
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0

        metrics = {
            "mode": self.mode.value,
            "partitions": self.partitions,
            "node_id": self.node_id,
            "messages_processed": self.messages_processed,
            "messages_failed": self.messages_failed,
            "success_rate": (self.messages_processed / total_messages) * 100 if total_messages > 0 else 0,
            "avg_processing_time": avg_processing_time,
            "active_processors": len([t for t in self._processing_tasks if not t.done()]),
            "subscribers_count": sum(len(callbacks) for callbacks in self.subscribers.values())
        }

        # Add partition metrics
        if self.partitions_info:
            partition_metrics = {}
            for partition, info in self.partitions_info.items():
                partition_metrics[partition] = {
                    "message_count": info.message_count,
                    "last_processed": info.last_processed,
                    "time_since_last": time.time() - info.last_processed
                }
            metrics["partitions"] = partition_metrics

        return metrics

    async def get_stream_info(self) -> Dict[str, Any]:
        """Get information about all streams"""
        redis_client = self.cluster or self.redis
        if not redis_client:
            return {}

        stream_info = {}

        try:
            if self.mode == QueueMode.PARTITIONED:
                for partition in range(self.partitions):
                    stream_name = self._get_stream_name(partition)
                    info = await redis_client.xinfo_stream(stream_name)
                    stream_info[f"partition_{partition}"] = {
                        "length": info["length"],
                        "first_entry": info.get("first-entry"),
                        "last_entry": info.get("last-entry")
                    }
            else:
                info = await redis_client.xinfo_stream(self.stream_prefix)
                stream_info["main"] = {
                    "length": info["length"],
                    "first_entry": info.get("first-entry"),
                    "last_entry": info.get("last-entry")
                }

        except Exception as e:
            logger.log("ERROR", "ScalableMessageQueue", f"Error getting stream info: {e}")

        return stream_info

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            redis_client = self.cluster or self.redis
            if redis_client:
                await redis_client.ping()
                redis_healthy = True
            else:
                redis_healthy = False

            return {
                "healthy": redis_healthy and self.running,
                "redis_connected": redis_healthy,
                "queue_running": self.running,
                "mode": self.mode.value,
                "partitions": self.partitions,
                "active_processors": len([t for t in self._processing_tasks if not t.done()]),
                "subscribers": len(self.subscribers),
                "metrics": self.get_metrics()
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "redis_connected": False,
                "queue_running": self.running
            }


class QueueClusterManager:
    """
    Manages multiple queue nodes in a cluster for load balancing and failover
    """

    def __init__(self, node_configs: List[Dict[str, Any]]):
        self.node_configs = node_configs
        self.nodes: Dict[str, ScalableMessageQueue] = {}
        self.active_nodes: Set[str] = set()
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False

    async def start_cluster(self):
        """Start all queue nodes in the cluster"""
        if self._running:
            return

        self._running = True

        # Start all nodes
        for config in self.node_configs:
            node_id = config["node_id"]
            queue = ScalableMessageQueue(
                redis_urls=config["redis_urls"],
                mode=config.get("mode", QueueMode.SINGLE_NODE),
                partitions=config.get("partitions", 8),
                consumer_name=node_id
            )

            await queue.connect()
            await queue.start_listening()

            self.nodes[node_id] = queue
            self.active_nodes.add(node_id)

        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_monitor())

        logger.log("INFO", "QueueClusterManager", f"Started cluster with {len(self.nodes)} nodes")

    async def stop_cluster(self):
        """Stop all queue nodes"""
        if not self._running:
            return

        self._running = False

        # Stop health monitoring
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()

        # Stop all nodes
        stop_tasks = [queue.stop_listening() for queue in self.nodes.values()]
        await asyncio.gather(*stop_tasks, return_exceptions=True)

        # Disconnect all nodes
        disconnect_tasks = [queue.disconnect() for queue in self.nodes.values()]
        await asyncio.gather(*disconnect_tasks, return_exceptions=True)

        logger.log("INFO", "QueueClusterManager", "Stopped cluster")

    async def _health_monitor(self):
        """Monitor health of all nodes"""
        while self._running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                for node_id, queue in self.nodes.items():
                    try:
                        health = await queue.health_check()
                        if not health["healthy"]:
                            if node_id in self.active_nodes:
                                self.active_nodes.remove(node_id)
                                logger.log("WARNING", "QueueClusterManager", f"Node {node_id} became unhealthy")
                        else:
                            if node_id not in self.active_nodes:
                                self.active_nodes.add(node_id)
                                logger.log("INFO", "QueueClusterManager", f"Node {node_id} recovered")

                    except Exception as e:
                        logger.log("ERROR", "QueueClusterManager", f"Health check failed for node {node_id}: {e}")
                        if node_id in self.active_nodes:
                            self.active_nodes.remove(node_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.log("ERROR", "QueueClusterManager", f"Error in health monitor: {e}")

    def get_cluster_metrics(self) -> Dict[str, Any]:
        """Get metrics for the entire cluster"""
        cluster_metrics = {
            "total_nodes": len(self.nodes),
            "active_nodes": len(self.active_nodes),
            "inactive_nodes": len(self.nodes) - len(self.active_nodes),
            "node_metrics": {}
        }

        for node_id, queue in self.nodes.items():
            cluster_metrics["node_metrics"][node_id] = {
                "active": node_id in self.active_nodes,
                "metrics": queue.get_metrics()
            }

        return cluster_metrics

    def get_least_loaded_node(self) -> Optional[str]:
        """Get the least loaded active node"""
        if not self.active_nodes:
            return None

        # Find node with lowest message processing load
        lowest_load = float('inf')
        selected_node = None

        for node_id in self.active_nodes:
            metrics = self.nodes[node_id].get_metrics()
            # Use messages processed as load indicator
            load = metrics["messages_processed"]
            if load < lowest_load:
                lowest_load = load
                selected_node = node_id

        return selected_node


# Global scalable message queue instance
scalable_message_queue: Optional[ScalableMessageQueue] = None
queue_cluster_manager: Optional[QueueClusterManager] = None


async def initialize_scalable_message_queue(
    redis_urls: List[str] = ["redis://localhost:6379"],
    mode: QueueMode = QueueMode.SINGLE_NODE,
    partitions: int = 8,
    enable_clustering: bool = False,
    cluster_configs: Optional[List[Dict[str, Any]]] = None
):
    """Initialize scalable message queue system"""
    global scalable_message_queue, queue_cluster_manager

    if enable_clustering and cluster_configs:
        # Initialize cluster manager
        queue_cluster_manager = QueueClusterManager(cluster_configs)
        await queue_cluster_manager.start_cluster()
        logger.log("INFO", "ScalableMessageQueue", "Initialized queue cluster")
    else:
        # Initialize single scalable queue
        scalable_message_queue = ScalableMessageQueue(
            redis_urls=redis_urls,
            mode=mode,
            partitions=partitions
        )
        await scalable_message_queue.connect()
        await scalable_message_queue.start_listening()
        logger.log("INFO", "ScalableMessageQueue", f"Initialized scalable queue (mode: {mode.value}, partitions: {partitions})")


async def shutdown_scalable_message_queue():
    """Shutdown scalable message queue system"""
    global scalable_message_queue, queue_cluster_manager

    if queue_cluster_manager:
        await queue_cluster_manager.stop_cluster()
        queue_cluster_manager = None

    if scalable_message_queue:
        await scalable_message_queue.stop_listening()
        await scalable_message_queue.disconnect()
        scalable_message_queue = None

    logger.log("INFO", "ScalableMessageQueue", "Shutdown complete")