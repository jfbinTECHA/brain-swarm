"""
Federation and cross-swarm coordination.

This module enables multiple swarm nodes to coordinate and share resources,
providing distributed swarm intelligence capabilities.
"""

from .distributed_swarm import DistributedCoordinator

__all__ = ['DistributedCoordinator']