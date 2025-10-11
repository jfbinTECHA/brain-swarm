"""
Federation Bridge for Brain-Swarm v3
Enables multiple Brain-Swarm nodes to discover and communicate with each other.

This module provides peer discovery, heartbeat broadcasting, and summary synchronization
across distributed Brain-Swarm nodes using Redis as the coordination backend.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
import redis.asyncio as redis

from ..core.base import logger
from ..message_queue import message_queue


class FederationBridge:
    """Manages federation between Brain-Swarm nodes"""

    def __init__(self, node_id: str, redis_url: str = "redis://localhost:6379"):
        self.node_id = node_id
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.peers_key = "brain_swarm:peers"
        self.heartbeat_channel = "brain_swarm:federation:heartbeat"
        self.summary_channel = "brain_swarm:federation:summary"
        self.heartbeat_interval = 30  # seconds
        self.peer_timeout = 120  # seconds (2x heartbeat interval)
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Connect to Redis for federation coordination"""
        try:
            self.redis = redis.from_url(self.redis_url)
            await self.redis.ping()
            logger.log("INFO", "FederationBridge", f"Connected to Redis for federation: {self.node_id}")

            # Register this node
            await self._register_self()

            # Start heartbeat broadcasting
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # Start peer cleanup
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        except Exception as e:
            logger.log("ERROR", "FederationBridge", f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Disconnect from federation"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Remove self from peer registry
        if self.redis:
            try:
                await self.redis.hdel(self.peers_key, self.node_id)
                logger.log("INFO", "FederationBridge", f"Unregistered from federation: {self.node_id}")
            except Exception as e:
                logger.log("WARNING", "FederationBridge", f"Failed to unregister: {e}")

        if self.redis:
            await self.redis.aclose()
            self.redis = None

    async def _register_self(self):
        """Register this node in the peer registry"""
        if not self.redis:
            return

        peer_info = {
            "node_id": self.node_id,
            "address": f"brain_swarm_{self.node_id}",  # Could be IP:port in real implementation
            "last_seen": time.time(),
            "status": "active"
        }

        await self.redis.hset(self.peers_key, self.node_id, json.dumps(peer_info))
        logger.log("INFO", "FederationBridge", f"Registered self in federation: {self.node_id}")

    async def _heartbeat_loop(self):
        """Continuously broadcast heartbeat"""
        while True:
            try:
                await self.broadcast_heartbeat()
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.log("ERROR", "FederationBridge", f"Heartbeat loop error: {e}")
                await asyncio.sleep(5)

    async def _cleanup_loop(self):
        """Periodically clean up stale peers"""
        while True:
            try:
                await self._cleanup_stale_peers()
                await asyncio.sleep(self.heartbeat_interval * 2)  # Clean every 2 heartbeats
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.log("ERROR", "FederationBridge", f"Cleanup loop error: {e}")
                await asyncio.sleep(5)

    async def _cleanup_stale_peers(self):
        """Remove peers that haven't sent heartbeats recently"""
        if not self.redis:
            return

        try:
            peers = await self.redis.hgetall(self.peers_key)
            current_time = time.time()
            removed_count = 0

            for node_id, peer_data_str in peers.items():
                try:
                    peer_data = json.loads(peer_data_str)
                    last_seen = peer_data.get("last_seen", 0)

                    if current_time - last_seen > self.peer_timeout:
                        await self.redis.hdel(self.peers_key, node_id)
                        removed_count += 1
                        logger.log("INFO", "FederationBridge", f"Removed stale peer: {node_id}")

                except (json.JSONDecodeError, KeyError) as e:
                    logger.log("WARNING", "FederationBridge", f"Invalid peer data for {node_id}: {e}")
                    await self.redis.hdel(self.peers_key, node_id)

            if removed_count > 0:
                logger.log("INFO", "FederationBridge", f"Cleaned up {removed_count} stale peers")

        except Exception as e:
            logger.log("ERROR", "FederationBridge", f"Failed to cleanup stale peers: {e}")


async def register_peer(node_id: str, address: str):
    """
    Add this node to the peer registry (Redis hash).

    Args:
        node_id: Unique identifier for the peer node
        address: Network address of the peer node
    """
    global _federation_bridge

    if not _federation_bridge or not _federation_bridge.redis:
        logger.log("WARNING", "FederationBridge", "Federation bridge not connected")
        return False

    try:
        peer_info = {
            "node_id": node_id,
            "address": address,
            "last_seen": time.time(),
            "status": "active",
            "registered_by": _federation_bridge.node_id
        }

        await _federation_bridge.redis.hset(_federation_bridge.peers_key, node_id, json.dumps(peer_info))

        # Broadcast peer registration
        registration_msg = {
            "type": "peer_registration",
            "node_id": node_id,
            "address": address,
            "timestamp": time.time()
        }

        await message_queue.publish("federation.peers", registration_msg)

        logger.log("INFO", "FederationBridge", f"Registered peer: {node_id} at {address}")
        return True

    except Exception as e:
        logger.log("ERROR", "FederationBridge", f"Failed to register peer {node_id}: {e}")
        return False


async def broadcast_heartbeat():
    """
    Publish 'I'm alive' messages on the federation channel.
    """
    global _federation_bridge

    if not _federation_bridge or not _federation_bridge.redis:
        logger.log("WARNING", "FederationBridge", "Federation bridge not connected")
        return

    try:
        heartbeat_msg = {
            "node_id": _federation_bridge.node_id,
            "timestamp": time.time(),
            "type": "heartbeat",
            "status": "alive"
        }

        # Update our last_seen in peer registry
        peer_info = {
            "node_id": _federation_bridge.node_id,
            "address": f"brain_swarm_{_federation_bridge.node_id}",
            "last_seen": time.time(),
            "status": "active"
        }

        await _federation_bridge.redis.hset(_federation_bridge.peers_key, _federation_bridge.node_id, json.dumps(peer_info))

        # Publish heartbeat to federation channel
        await message_queue.publish("federation.heartbeat", heartbeat_msg)

        logger.log("DEBUG", "FederationBridge", f"Broadcast heartbeat from {_federation_bridge.node_id}")

    except Exception as e:
        logger.log("ERROR", "FederationBridge", f"Failed to broadcast heartbeat: {e}")


async def sync_summary(peer_id: str):
    """
    Exchange cortex summaries across nodes.

    Args:
        peer_id: ID of the peer node to sync with
    """
    global _federation_bridge

    if not _federation_bridge or not _federation_bridge.redis:
        logger.log("WARNING", "FederationBridge", "Federation bridge not connected")
        return None

    try:
        # Get peer information
        peer_data_str = await _federation_bridge.redis.hget(_federation_bridge.peers_key, peer_id)
        if not peer_data_str:
            logger.log("WARNING", "FederationBridge", f"Peer not found: {peer_id}")
            return None

        peer_data = json.loads(peer_data_str)

        # Request summary from peer (in a real implementation, this would be an RPC call)
        summary_request = {
            "type": "summary_request",
            "from_node": _federation_bridge.node_id,
            "to_node": peer_id,
            "timestamp": time.time()
        }

        # Publish summary sync request
        await message_queue.publish("federation.summary", summary_request)

        # In a real implementation, we'd wait for a response
        # For now, return a placeholder summary
        summary = {
            "peer_id": peer_id,
            "node_id": _federation_bridge.node_id,
            "timestamp": time.time(),
            "status": "sync_requested",
            "summary_data": {
                "events_processed": 0,
                "active_agents": 0,
                "memory_records": 0
            }
        }

        logger.log("INFO", "FederationBridge", f"Initiated summary sync with peer: {peer_id}")
        return summary

    except Exception as e:
        logger.log("ERROR", "FederationBridge", f"Failed to sync summary with {peer_id}: {e}")
        return None


async def get_peer_list() -> List[Dict[str, Any]]:
    """
    Get list of all known peers.

    Returns:
        List of peer information dictionaries
    """
    global _federation_bridge

    if not _federation_bridge or not _federation_bridge.redis:
        return []

    try:
        peers = await _federation_bridge.redis.hgetall(_federation_bridge.peers_key)
        peer_list = []

        for node_id, peer_data_str in peers.items():
            try:
                peer_data = json.loads(peer_data_str)
                peer_list.append(peer_data)
            except json.JSONDecodeError:
                continue

        return peer_list

    except Exception as e:
        logger.log("ERROR", "FederationBridge", f"Failed to get peer list: {e}")
        return []


# Global federation bridge instance
_federation_bridge: Optional[FederationBridge] = None


async def initialize_federation(node_id: str, redis_url: str = "redis://localhost:6379"):
    """Initialize the global federation bridge"""
    global _federation_bridge

    if _federation_bridge:
        await _federation_bridge.disconnect()

    _federation_bridge = FederationBridge(node_id, redis_url)
    await _federation_bridge.connect()

    logger.log("INFO", "FederationBridge", f"Federation bridge initialized for node: {node_id}")


async def shutdown_federation():
    """Shutdown the global federation bridge"""
    global _federation_bridge

    if _federation_bridge:
        await _federation_bridge.disconnect()
        _federation_bridge = None

        logger.log("INFO", "FederationBridge", "Federation bridge shutdown")