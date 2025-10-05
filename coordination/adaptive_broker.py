"""
Adaptive Task Broker with Reinforcement Learning-based routing
Uses audit log metrics to learn optimal task-agent assignments
"""

from typing import Dict, List, Any, Optional, Tuple
import time
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass
import json

from ..core.base import logger


@dataclass
class TaskAssignment:
    """Represents a task assignment with metrics"""
    task_id: str
    agent_id: str
    start_time: float
    end_time: Optional[float] = None
    success: Optional[bool] = None
    latency: Optional[float] = None
    resource_cost: Optional[float] = None
    task_type: str = "general"


@dataclass
class AgentPerformance:
    """Tracks agent performance metrics"""
    agent_id: str
    total_assignments: int = 0
    successful_assignments: int = 0
    avg_latency: float = 0.0
    avg_resource_cost: float = 0.0
    success_rate: float = 0.0
    reward_score: float = 1.0  # Moving average reward
    recent_rewards: deque = None

    def __post_init__(self):
        if self.recent_rewards is None:
            self.recent_rewards = deque(maxlen=50)  # Keep last 50 rewards


class AdaptiveTaskBroker:
    """
    Adaptive task broker that learns optimal routing using reinforcement learning
    Initially uses moving-average reward scores, extensible to PPO/contextual bandits
    """

    def __init__(self, alpha: float = 0.1, reward_window: int = 50):
        """
        Initialize the adaptive broker

        Args:
            alpha: Learning rate for reward updates
            reward_window: Window size for moving average calculations
        """
        self.alpha = alpha
        self.reward_window = reward_window

        # Agent performance tracking
        self.agent_performance: Dict[str, AgentPerformance] = {}

        # Task type to agent mapping with learned weights
        self.routing_weights: Dict[str, Dict[str, float]] = defaultdict(dict)

        # Active assignments for tracking completion
        self.active_assignments: Dict[str, TaskAssignment] = {}

        # Historical data for analysis
        self.assignment_history: List[TaskAssignment] = []

        # Task type patterns
        self.task_type_patterns: Dict[str, Dict[str, Any]] = {}

        logger.log("INFO", "AdaptiveTaskBroker", "Initialized adaptive task broker",
                  {"alpha": alpha, "reward_window": reward_window})

    def register_agent(self, agent_id: str, capabilities: List[str] = None):
        """Register a new agent with the broker"""
        if agent_id not in self.agent_performance:
            self.agent_performance[agent_id] = AgentPerformance(agent_id)

            # Initialize routing weights for task types
            for task_type in ["general", "analysis", "computation", "communication", "creative"]:
                self.routing_weights[task_type][agent_id] = 1.0  # Start with neutral weights

            logger.log("INFO", "AdaptiveTaskBroker", f"Registered agent {agent_id}",
                      {"capabilities": capabilities})

    def assign_task(self, task_id: str, task_description: str, available_agents: List[str],
                   task_type: str = "general") -> Optional[str]:
        """
        Assign a task to the best agent based on learned routing weights

        Args:
            task_id: Unique task identifier
            task_description: Task description for analysis
            available_agents: List of available agent IDs
            task_type: Type of task (analysis, computation, etc.)

        Returns:
            Selected agent ID or None if no suitable agent found
        """
        if not available_agents:
            return None

        # Get routing weights for this task type
        weights = self.routing_weights.get(task_type, {})

        # Filter to available agents and get their performance
        candidates = []
        for agent_id in available_agents:
            if agent_id in self.agent_performance:
                performance = self.agent_performance[agent_id]
                weight = weights.get(agent_id, 1.0)
                reward_score = performance.reward_score

                # Combined score: weight * reward_score * (1 + success_rate)
                combined_score = weight * reward_score * (1 + performance.success_rate)

                candidates.append((agent_id, combined_score, performance))

        if not candidates:
            # Fallback to random selection if no performance data
            selected_agent = available_agents[0]
        else:
            # Select agent with highest combined score
            candidates.sort(key=lambda x: x[1], reverse=True)
            selected_agent = candidates[0][0]

        # Record the assignment
        assignment = TaskAssignment(
            task_id=task_id,
            agent_id=selected_agent,
            start_time=time.time(),
            task_type=task_type
        )
        self.active_assignments[task_id] = assignment

        logger.log("INFO", "AdaptiveTaskBroker", f"Assigned task {task_id} to agent {selected_agent}",
                  {"task_type": task_type, "candidates": len(candidates)})

        return selected_agent

    def complete_task(self, task_id: str, success: bool, latency: float = None,
                     resource_cost: float = None):
        """
        Record task completion and update agent performance

        Args:
            task_id: Task identifier
            success: Whether the task was successful
            latency: Task execution time in seconds
            resource_cost: Resource usage cost (0-1 scale)
        """
        if task_id not in self.active_assignments:
            logger.log("WARNING", "AdaptiveTaskBroker", f"Unknown task completion: {task_id}")
            return

        assignment = self.active_assignments[task_id]
        assignment.end_time = time.time()
        assignment.success = success
        assignment.latency = latency or (assignment.end_time - assignment.start_time)
        assignment.resource_cost = resource_cost or 0.5

        # Update agent performance
        self._update_agent_performance(assignment)

        # Update routing weights based on outcome
        self._update_routing_weights(assignment)

        # Move to history
        self.assignment_history.append(assignment)
        del self.active_assignments[task_id]

        logger.log("INFO", "AdaptiveTaskBroker", f"Task {task_id} completed",
                  {"success": success, "latency": latency, "agent": assignment.agent_id})

    def _update_agent_performance(self, assignment: TaskAssignment):
        """Update agent performance metrics"""
        agent_id = assignment.agent_id
        performance = self.agent_performance[agent_id]

        # Update basic metrics
        performance.total_assignments += 1
        if assignment.success:
            performance.successful_assignments += 1

        performance.success_rate = performance.successful_assignments / performance.total_assignments

        # Update averages
        if assignment.latency:
            performance.avg_latency = (
                (performance.avg_latency * (performance.total_assignments - 1)) + assignment.latency
            ) / performance.total_assignments

        if assignment.resource_cost is not None:
            performance.avg_resource_cost = (
                (performance.avg_resource_cost * (performance.total_assignments - 1)) + assignment.resource_cost
            ) / performance.total_assignments

        # Calculate reward based on multiple factors
        reward = self._calculate_reward(assignment)
        performance.recent_rewards.append(reward)

        # Update moving average reward score
        if len(performance.recent_rewards) > 1:
            performance.reward_score = statistics.mean(performance.recent_rewards)
        else:
            performance.reward_score = reward

    def _calculate_reward(self, assignment: TaskAssignment) -> float:
        """
        Calculate reward for task assignment based on multiple metrics

        Reward components:
        - Success: +1.0 for success, -1.0 for failure
        - Latency: Penalty for high latency (normalized)
        - Resource cost: Penalty for high resource usage
        """
        reward = 0.0

        # Success bonus/penalty
        if assignment.success:
            reward += 1.0
        else:
            reward -= 1.0

        # Latency penalty (normalized to 0-1 scale, lower is better)
        if assignment.latency:
            # Assume optimal latency is < 5 seconds, penalize longer times
            latency_score = min(assignment.latency / 30.0, 1.0)  # Cap at 30 seconds
            reward -= latency_score * 0.5  # Max penalty of -0.5

        # Resource cost penalty
        if assignment.resource_cost is not None:
            reward -= assignment.resource_cost * 0.3  # Max penalty of -0.3

        return reward

    def _update_routing_weights(self, assignment: TaskAssignment):
        """Update routing weights using reinforcement learning"""
        task_type = assignment.task_type
        agent_id = assignment.agent_id

        # Get current weight
        current_weight = self.routing_weights[task_type].get(agent_id, 1.0)

        # Calculate reward
        reward = self._calculate_reward(assignment)

        # Update weight using simple reinforcement learning
        # Weight increases for positive rewards, decreases for negative
        weight_update = self.alpha * reward
        new_weight = max(0.1, current_weight + weight_update)  # Minimum weight of 0.1

        self.routing_weights[task_type][agent_id] = new_weight

        # Normalize weights for this task type to prevent unbounded growth
        self._normalize_weights(task_type)

    def _normalize_weights(self, task_type: str):
        """Normalize routing weights for a task type"""
        weights = self.routing_weights[task_type]
        if not weights:
            return

        total_weight = sum(weights.values())
        if total_weight > 0:
            for agent_id in weights:
                weights[agent_id] = weights[agent_id] / total_weight

    def get_routing_recommendation(self, task_type: str, available_agents: List[str]) -> Dict[str, Any]:
        """Get routing recommendation with confidence scores"""
        weights = self.routing_weights.get(task_type, {})
        recommendations = []

        for agent_id in available_agents:
            if agent_id in self.agent_performance:
                performance = self.agent_performance[agent_id]
                weight = weights.get(agent_id, 1.0)

                score = weight * performance.reward_score * (1 + performance.success_rate)
                recommendations.append({
                    "agent_id": agent_id,
                    "score": score,
                    "weight": weight,
                    "reward_score": performance.reward_score,
                    "success_rate": performance.success_rate,
                    "total_assignments": performance.total_assignments
                })

        recommendations.sort(key=lambda x: x["score"], reverse=True)

        return {
            "task_type": task_type,
            "recommendations": recommendations,
            "best_agent": recommendations[0]["agent_id"] if recommendations else None,
            "confidence": len(recommendations) / len(available_agents) if available_agents else 0
        }

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "total_assignments": len(self.assignment_history),
            "active_assignments": len(self.active_assignments),
            "agent_performance": {},
            "routing_weights": dict(self.routing_weights),
            "learning_stats": {
                "alpha": self.alpha,
                "reward_window": self.reward_window
            }
        }

        for agent_id, performance in self.agent_performance.items():
            report["agent_performance"][agent_id] = {
                "total_assignments": performance.total_assignments,
                "success_rate": performance.success_rate,
                "avg_latency": performance.avg_latency,
                "avg_resource_cost": performance.avg_resource_cost,
                "reward_score": performance.reward_score,
                "recent_rewards_count": len(performance.recent_rewards)
            }

        return report

    def reset_learning(self):
        """Reset all learned weights and performance data"""
        self.routing_weights.clear()
        self.agent_performance.clear()
        self.assignment_history.clear()
        self.active_assignments.clear()

        logger.log("INFO", "AdaptiveTaskBroker", "Reset all learning data")

    def export_learning_state(self) -> str:
        """Export current learning state as JSON"""
        state = {
            "agent_performance": {
                agent_id: {
                    "total_assignments": perf.total_assignments,
                    "successful_assignments": perf.successful_assignments,
                    "avg_latency": perf.avg_latency,
                    "avg_resource_cost": perf.avg_resource_cost,
                    "success_rate": perf.success_rate,
                    "reward_score": perf.reward_score,
                    "recent_rewards": list(perf.recent_rewards)
                }
                for agent_id, perf in self.agent_performance.items()
            },
            "routing_weights": dict(self.routing_weights),
            "assignment_history": [
                {
                    "task_id": a.task_id,
                    "agent_id": a.agent_id,
                    "start_time": a.start_time,
                    "end_time": a.end_time,
                    "success": a.success,
                    "latency": a.latency,
                    "resource_cost": a.resource_cost,
                    "task_type": a.task_type
                }
                for a in self.assignment_history[-100:]  # Last 100 assignments
            ]
        }

        return json.dumps(state, indent=2, default=str)

    def import_learning_state(self, state_json: str):
        """Import learning state from JSON"""
        try:
            state = json.loads(state_json)

            # Restore agent performance
            for agent_id, perf_data in state.get("agent_performance", {}).items():
                performance = AgentPerformance(agent_id)
                performance.total_assignments = perf_data["total_assignments"]
                performance.successful_assignments = perf_data["successful_assignments"]
                performance.avg_latency = perf_data["avg_latency"]
                performance.avg_resource_cost = perf_data["avg_resource_cost"]
                performance.success_rate = perf_data["success_rate"]
                performance.reward_score = perf_data["reward_score"]
                performance.recent_rewards = deque(perf_data["recent_rewards"], maxlen=self.reward_window)

                self.agent_performance[agent_id] = performance

            # Restore routing weights
            self.routing_weights = defaultdict(dict, state.get("routing_weights", {}))

            logger.log("INFO", "AdaptiveTaskBroker", "Imported learning state",
                      {"agents": len(self.agent_performance), "task_types": len(self.routing_weights)})

        except json.JSONDecodeError as e:
            logger.log("ERROR", "AdaptiveTaskBroker", f"Failed to import learning state: {e}")