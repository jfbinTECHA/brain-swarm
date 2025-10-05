"""
Swarm coordination and task management.

This module contains the core coordination logic for managing agent swarms,
including task delegation, load balancing, planning, and execution orchestration.
"""

from .coordinator import SwarmCoordinator
from .auto_scaling import AutoScaler

__all__ = ['SwarmCoordinator', 'AutoScaler']