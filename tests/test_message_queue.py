"""
Tests for the MessageQueue system
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from ..message_queue import MessageQueue
from ..core.base import Message, MessageType


class TestMessageQueue:
    """Test cases for MessageQueue"""

    @pytest.fixture
    async def message_queue(self):
        """Create a message queue instance"""
        queue = MessageQueue()
        # Mock Redis connection
        queue.redis = AsyncMock()
        queue.redis.ping = AsyncMock(return_value=True)
        queue.redis.xadd = AsyncMock(return_value="1234567890-0")
        queue.redis.xreadgroup = AsyncMock(return_value=[])
        queue.redis.xack = AsyncMock()
        queue.redis.xinfo_stream = AsyncMock(return_value={
            "length": 10,
            "first-entry": None,
            "last-entry": None
        })
        queue.redis.xinfo_groups = AsyncMock(return_value=[])
        yield queue
        # Cleanup
        if queue.running:
            await queue.stop_listening()

    @pytest.mark.asyncio
    async def test_connect(self, message_queue):
        """Test connecting to Redis"""
        await message_queue.connect()
        message_queue.redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_message(self, message_queue):
        """Test publishing a message"""
        message = Message(
            sender="test_agent",
            receiver="coordinator",
            message_type=MessageType.TASK_ASSIGNMENT,
            content={"task": "test"}
        )

        message_id = await message_queue.publish_message(message)
        assert message_id == "1234567890-0"
        message_queue.redis.xadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_and_callback(self, message_queue):
        """Test subscribing and receiving callbacks"""
        callback_called = False
        received_message = None

        async def test_callback(message):
            nonlocal callback_called, received_message
            callback_called = True
            received_message = message

        # Subscribe
        await message_queue.subscribe("test_recipient", test_callback)

        # Simulate receiving a message
        test_message = Message(
            sender="sender",
            receiver="test_recipient",
            message_type=MessageType.TASK_ASSIGNMENT,
            content={"test": "data"}
        )

        await message_queue._process_message("123-0", {
            "sender": "sender",
            "receiver": "test_recipient",
            "message_type": "task_assignment",
            "content": {"test": "data"},
            "timestamp": 1234567890,
            "swarm_id": None,
            "metadata": {}
        })

        assert callback_called
        assert received_message.sender == "sender"
        assert received_message.receiver == "test_recipient"

    @pytest.mark.asyncio
    async def test_broadcast_message(self, message_queue):
        """Test broadcasting a message"""
        message = Message(
            sender="broadcaster",
            receiver="specific",
            message_type=MessageType.SHARE_KNOWLEDGE,
            content={"knowledge": "test"}
        )

        message_id = await message_queue.broadcast_message(message)
        assert message_id == "1234567890-0"

        # Check that receiver was set to broadcast
        call_args = message_queue.redis.xadd.call_args[1]
        assert call_args["receiver"] == "broadcast"

    @pytest.mark.asyncio
    async def test_get_stream_info(self, message_queue):
        """Test getting stream information"""
        info = await message_queue.get_stream_info()
        assert "stream_length" in info
        assert "consumer_groups" in info
        message_queue.redis.xinfo_stream.assert_called_once()
        message_queue.redis.xinfo_groups.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_loop_error_handling(self, message_queue):
        """Test that listen loop handles errors gracefully"""
        # Mock xreadgroup to raise an exception
        message_queue.redis.xreadgroup = AsyncMock(side_effect=Exception("Test error"))

        # Start listening
        await message_queue.start_listening()

        # Let it run briefly
        await asyncio.sleep(0.1)

        # Stop listening
        await message_queue.stop_listening()

        # Should not have crashed
        assert not message_queue.running