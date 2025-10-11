"""
Predictive analytics and performance optimization.

This module provides predictive analytics capabilities for task completion times,
memory bottleneck detection, failure prediction, and self-tuning optimization.
"""

from .predictive_analytics import (
    TaskCompletionPredictor, MemoryBottleneckPredictor, FailurePredictor,
    task_completion_predictor, memory_bottleneck_predictor, failure_predictor
)
from .self_tuning import (
    SelfTuningParameterManager, get_adaptive_reasoning_depth, get_adaptive_branch_limits,
    get_adaptive_retry_strategy, record_task_performance_for_tuning, get_self_tuning_status
)
from .autonomous_goals import (
    initialize_autonomous_goals, generate_autonomous_goals, get_goal_statistics
)

__all__ = [
    # Predictive analytics
    'TaskCompletionPredictor', 'MemoryBottleneckPredictor', 'FailurePredictor',
    'task_completion_predictor', 'memory_bottleneck_predictor', 'failure_predictor',

    # Self-tuning
    'SelfTuningParameterManager', 'get_adaptive_reasoning_depth', 'get_adaptive_branch_limits',
    'get_adaptive_retry_strategy', 'record_task_performance_for_tuning', 'get_self_tuning_status',

    # Autonomous goals
    'initialize_autonomous_goals', 'generate_autonomous_goals', 'get_goal_statistics'
]