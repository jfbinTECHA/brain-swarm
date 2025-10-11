"""
Asynchronous Message Queue System for Brain Swarm

Supports Redis Streams for persistent messaging, broadcast, and replay capabilities.
Provides decoupled communication between agents and coordinators.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable, Awaitable
import redis.asyncio as redis
from core.base import Message, MessageType, logger
from config import settings


class MessageQueue:
    """Asynchronous message queue using Redis Streams"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.stream_name = "brain_swarm_messages"
        self.consumer_group = "brain_swarm_consumers"
        self.consumer_name = f"consumer_{id(self)}"
        self.subscribers: Dict[str, List[Callable]] = {}  # recipient -> list of callbacks
        self.running = False
        self._listen_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(self.redis_url)
            # Test connection
            await self.redis.ping()
            logger.log("INFO", "MessageQueue", "Connected to Redis")
        except Exception as e:
            logger.log("ERROR", "MessageQueue", f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
            logger.log("INFO", "MessageQueue", "Disconnected from Redis")

    async def publish_message(self, message: Message) -> str:
        """Publish a message to the stream"""
        if not self.redis:
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

        # Add to stream
        message_id = await self.redis.xadd(self.stream_name, message_dict)
        logger.log("DEBUG", "MessageQueue", f"Published message {message_id} from {message.sender} to {message.receiver}")
        return message_id

    async def publish(self, topic: str, data: Dict[str, Any]) -> str:
        """Publish data to a specific topic/channel"""
        if not self.redis:
            raise RuntimeError("MessageQueue not connected")

        # Create a message dict for the topic
        message_dict = {
            "topic": topic,
            "data": json.dumps(data),
            "timestamp": asyncio.get_event_loop().time()
        }

        # Use topic as stream name or add to main stream with topic
        stream_name = f"{self.stream_name}_{topic.replace('.', '_')}"
        message_id = await self.redis.xadd(stream_name, message_dict)

        # Record message publishing metric
        from observability.metrics import prometheus_metrics
        prometheus_metrics.record_message("webhook_event", "webhook_service", "redis")

        logger.log("DEBUG", "MessageQueue", f"Published to topic {topic}: {message_id}")
        return message_id

    async def subscribe(self, recipient: str, callback: Callable[[Message], Awaitable[None]]):
        """Subscribe to messages for a specific recipient"""
        if recipient not in self.subscribers:
            self.subscribers[recipient] = []
        self.subscribers[recipient].append(callback)

        # Create consumer group if it doesn't exist
        try:
            await self.redis.xgroup_create(self.stream_name, self.consumer_group, "0", mkstream=True)
        except redis.ResponseError:
            # Group already exists
            pass

        logger.log("INFO", "MessageQueue", f"Subscribed to messages for {recipient}")

    async def unsubscribe(self, recipient: str, callback: Optional[Callable] = None):
        """Unsubscribe from messages for a recipient"""
        if recipient in self.subscribers:
            if callback:
                self.subscribers[recipient].remove(callback)
                if not self.subscribers[recipient]:
                    del self.subscribers[recipient]
            else:
                del self.subscribers[recipient]

    async def start_listening(self):
        """Start listening for messages"""
        if self.running:
            return

        self.running = True
        self._listen_task = asyncio.create_task(self._listen_loop())
        logger.log("INFO", "MessageQueue", "Started message listening")

    async def stop_listening(self):
        """Stop listening for messages"""
        self.running = False
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        logger.log("INFO", "MessageQueue", "Stopped message listening")

    async def _listen_loop(self):
        """Main listening loop"""
        last_id = "0"  # Start from beginning

        while self.running:
            try:
                # Read from stream
                messages = await self.redis.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_name: last_id},
                    count=10,
                    block=1000  # Block for 1 second
                )

                for stream_name, message_list in messages:
                    for message_id, message_data in message_list:
                        await self._process_message(message_id, message_data)
                        last_id = message_id

                # Acknowledge processed messages
                if messages:
                    await self.redis.xack(self.stream_name, self.consumer_group, last_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.log("ERROR", "MessageQueue", f"Error in listen loop: {e}")
                await asyncio.sleep(1)  # Back off on error

    async def _process_message(self, message_id: str, message_data: Dict[str, Any]):
        """Process a received message"""
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
            if recipient in self.subscribers:
                for callback in self.subscribers[recipient]:
                    try:
                        await callback(message)
                    except Exception as e:
                        logger.log("ERROR", "MessageQueue", f"Error in message callback: {e}")

            # Also deliver to broadcast subscribers if it's a broadcast
            if recipient == "broadcast" and "broadcast" in self.subscribers:
                for callback in self.subscribers["broadcast"]:
                    try:
                        await callback(message)
                    except Exception as e:
                        logger.log("ERROR", "MessageQueue", f"Error in broadcast callback: {e}")

        except Exception as e:
            logger.log("ERROR", "MessageQueue", f"Error processing message {message_id}: {e}")

    async def get_message_history(self, recipient: str, limit: int = 100) -> List[Message]:
        """Get message history for a recipient (for replay)"""
        if not self.redis:
            return []

        try:
            # Get all messages from stream
            messages = await self.redis.xrange(self.stream_name, "-", "+", count=1000)

            # Filter by recipient
            recipient_messages = []
            for message_id, message_data in messages:
                if message_data.get("receiver") == recipient:
                    message = Message(
                        sender=message_data["sender"],
                        receiver=message_data["receiver"],
                        message_type=MessageType(message_data["message_type"]),
                        content=message_data["content"],
                        timestamp=message_data["timestamp"],
                        swarm_id=message_data.get("swarm_id"),
                        metadata=message_data.get("metadata")
                    )
                    recipient_messages.append(message)

            return recipient_messages[-limit:]  # Return most recent

        except Exception as e:
            logger.log("ERROR", "MessageQueue", f"Error getting message history: {e}")
            return []

    async def broadcast_message(self, message: Message) -> str:
        """Broadcast a message to all subscribers"""
        # Set receiver to broadcast
        broadcast_message = Message(
            sender=message.sender,
            receiver="broadcast",
            message_type=message.message_type,
            content=message.content,
            timestamp=message.timestamp,
            swarm_id=message.swarm_id,
            metadata={**message.metadata, "broadcast": True} if message.metadata else {"broadcast": True}
        )

        return await self.publish_message(broadcast_message)

    async def get_stream_info(self) -> Dict[str, Any]:
        """Get information about the message stream"""
        if not self.redis:
            return {}

        try:
            info = await self.redis.xinfo_stream(self.stream_name)
            groups = await self.redis.xinfo_groups(self.stream_name)

            return {
                "stream_length": info["length"],
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
                "consumer_groups": len(groups),
                "groups_info": groups
            }
        except Exception as e:
            logger.log("ERROR", "MessageQueue", f"Error getting stream info: {e}")
            return {}


# Global message queue instance
message_queue = MessageQueue()


async def init_message_queue():
    """Initialize the global message queue"""
    redis_url = f"redis://localhost:{settings.node.port + 1}" if hasattr(settings.node, 'port') else "redis://localhost:6379"
    message_queue.redis_url = redis_url
    await message_queue.connect()


async def shutdown_message_queue():
    """Shutdown the global message queue"""
    await message_queue.stop_listening()
    await message_queue.disconnect()


# Synchronous wrapper for backward compatibility
class SyncMessageQueue:
    """Synchronous wrapper for the async message queue"""

    def __init__(self):
        self._loop = None
        self._queue = None

    def _get_queue(self):
        """Get or create the async queue"""
        if self._queue is None:
            if self._loop is None:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            self._queue = MessageQueue()
            # Run connect in the loop
            self._loop.run_until_complete(self._queue.connect())
        return self._queue

    def publish_message(self, message: Message) -> str:
        """Synchronous publish"""
        queue = self._get_queue()
        return self._loop.run_until_complete(queue.publish_message(message))

    def subscribe(self, recipient: str, callback: Callable[[Message], Awaitable[None]]):
        """Synchronous subscribe"""
        queue = self._get_queue()
        return self._loop.run_until_complete(queue.subscribe(recipient, callback))

    def start_listening(self):
        """Start listening (runs in background)"""
        queue = self._get_queue()
        # Start listening in a separate thread
        import threading
        def run_listen():
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(queue.start_listening())

        thread = threading.Thread(target=run_listen, daemon=True)
        thread.start()

    def stop_listening(self):
        """Stop listening"""
        if self._queue:
            self._loop.run_until_complete(self._queue.stop_listening())


# Global sync wrapper for backward compatibility
sync_message_queue = SyncMessageQueue()