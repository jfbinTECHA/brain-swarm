"""
Brain-Swarm Federation Bridge
Enables multi-node communication and coordination.
"""

from .federation import (
    FederationBridge,
    register_peer,
    broadcast_heartbeat,
    sync_summary,
    get_peer_list,
    initialize_federation,
    shutdown_federation
)

__all__ = [
    "FederationBridge",
    "register_peer",
    "broadcast_heartbeat",
    "sync_summary",
    "get_peer_list",
    "initialize_federation",
    "shutdown_federation"
]