# brainswarm.message_queue
# Temporary stub for BrainSwarm message queue system

import asyncio
from typing import Any, Dict, List

class MessageQueue:
    """Stub async message queue used for inter-agent communication."""

    def __init__(self):
        self._queue = asyncio.Queue()
        self.messages: List[Dict[str, Any]] = []

    async def publish(self, message: Dict[str, Any]):
        """Simulate publishing a message."""
        self.messages.append(message)
        await self._queue.put(message)

    async def subscribe(self):
        """Simulate subscribing to new messages."""
        while True:
            msg = await self._queue.get()
            yield msg

    def get_all(self) -> List[Dict[str, Any]]:
        """Return all messages for debugging or inspection."""
        return self.messages

# Export a global instance (the rest of the system expects this)
message_queue = MessageQueue()
