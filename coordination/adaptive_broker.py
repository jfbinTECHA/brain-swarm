"""
Adaptive Task Broker with Reinforcement Learning-based routing
Uses audit log metrics to learn optimal task-agent assignments
Supports multiple RL methods: moving-average, contextual bandit, and PPO
"""

from typing import Dict, List, Any, Optional, Tuple
import time
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass
import json
import random
from enum import Enum

from ..core.base import logger

try:
    import torch
    import gymnasium as gym
    from gymnasium import spaces
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    from sklearn.linear_model import LogisticRegression
    import numpy as np
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False
    logger.log("WARNING", "AdaptiveTaskBroker", "RL dependencies not available, falling back to basic methods")


class RLMethod(Enum):
    """Reinforcement Learning methods for adaptive routing"""
    MOVING_AVERAGE = "moving_average"
    CONTEXTUAL_BANDIT = "contextual_bandit"
    PPO = "ppo"


class TaskRoutingEnv(gym.Env):
    """Gym environment for task routing with PPO"""

    def __init__(self, agent_ids: List[str], task_types: List[str]):
        super().__init__()

        self.agent_ids = agent_ids
        self.task_types = task_types
        self.num_agents = len(agent_ids)
        self.num_task_types = len(task_types)

        # Action space: choose agent for task
        self.action_space = spaces.Discrete(self.num_agents)

        # Observation space: task type (one-hot) + agent performance features
        obs_dim = self.num_task_types + self.num_agents * 3  # task_type + (success_rate, avg_latency, reward_score per agent)
        self.observation_space = spaces.Box(low=0, high=1, shape=(obs_dim,), dtype=np.float32)

        self.current_task_type = None
        self.agent_performance = {}

    def reset(self, seed=None, options=None):
        """Reset environment"""
        super().reset(seed=seed)
        return self._get_observation(), {}

    def step(self, action):
        """Execute action and return reward"""
        agent_id = self.agent_ids[action]

        # Get reward based on agent performance
        reward = self._calculate_reward(agent_id)

        # Create observation
        observation = self._get_observation()

        # Episode never ends in this continuous learning setup
        terminated = False
        truncated = False

        return observation, reward, terminated, truncated, {}

    def _get_observation(self):
        """Get current observation vector"""
        obs = []

        # Task type one-hot encoding
        for task_type in self.task_types:
            obs.append(1.0 if task_type == self.current_task_type else 0.0)

        # Agent performance features
        for agent_id in self.agent_ids:
            perf = self.agent_performance.get(agent_id, {
                'success_rate': 0.5,
                'avg_latency': 0.5,
                'reward_score': 0.5
            })
            obs.extend([
                perf['success_rate'],
                min(perf['avg_latency'] / 60.0, 1.0),  # Normalize latency
                perf['reward_score']
            ])

        return np.array(obs, dtype=np.float32)

    def _calculate_reward(self, agent_id):
        """Calculate reward for agent selection"""
        perf = self.agent_performance.get(agent_id, {
            'success_rate': 0.5,
            'avg_latency': 0.5,
            'reward_score': 0.5
        })

        # Reward based on success rate and efficiency
        reward = (perf['success_rate'] * 2.0) - 1.0  # Scale to [-1, 1]
        reward -= min(perf['avg_latency'] / 30.0, 0.5)  # Penalty for high latency
        reward += perf['reward_score']  # Bonus for good historical performance

        return reward

    def update_performance(self, agent_performance: Dict[str, Dict[str, float]]):
        """Update agent performance data"""
        self.agent_performance = agent_performance


class ContextualBanditRouter:
    """Contextual bandit for task routing decisions"""

    def __init__(self, agent_ids: List[str], task_types: List[str], alpha: float = 0.1):
        self.agent_ids = agent_ids
        self.task_types = task_types
        self.alpha = alpha
        self.num_agents = len(agent_ids)

        # Models for each task type
        self.models: Dict[str, LogisticRegression] = {}
        self.training_data: Dict[str, List[Tuple[np.ndarray, int]]] = defaultdict(list)

        # Initialize models
        for task_type in task_types:
            self.models[task_type] = LogisticRegression(random_state=42, max_iter=1000)

    def select_agent(self, task_type: str, context_features: np.ndarray) -> str:
        """Select best agent using contextual bandit"""
        if task_type not in self.models or len(self.training_data[task_type]) < 5:
            # Not enough data, use random selection
            return random.choice(self.agent_ids)

        model = self.models[task_type]

        # Get probabilities for each agent
        agent_features = []
        for agent_id in self.agent_ids:
            # Create feature vector for this agent
            agent_context = np.concatenate([context_features, self._get_agent_features(agent_id)])
            agent_features.append(agent_context)

        agent_features = np.array(agent_features)

        try:
            # Get prediction probabilities
            probs = model.predict_proba(agent_features)[:, 1]  # Probability of success

            # Select agent with highest probability
            best_agent_idx = np.argmax(probs)
            return self.agent_ids[best_agent_idx]

        except Exception as e:
            logger.log("WARNING", "ContextualBanditRouter", f"Model prediction failed: {e}")
            return random.choice(self.agent_ids)

    def update(self, task_type: str, agent_id: str, context_features: np.ndarray, reward: float):
        """Update model with new experience"""
        agent_idx = self.agent_ids.index(agent_id)

        # Create feature vector
        agent_features = self._get_agent_features(agent_id)
        full_features = np.concatenate([context_features, agent_features])

        # Convert reward to binary outcome (success/failure)
        outcome = 1 if reward > 0 else 0

        # Store training data
        self.training_data[task_type].append((full_features, outcome))

        # Retrain model if we have enough data
        if len(self.training_data[task_type]) >= 10:
            self._retrain_model(task_type)

    def _get_agent_features(self, agent_id: str) -> np.ndarray:
        """Get agent-specific features (placeholder)"""
        # In real implementation, this would include agent performance metrics
        # For now, return random features
        return np.array([random.random() for _ in range(5)])

    def _retrain_model(self, task_type: str):
        """Retrain the logistic regression model"""
        if len(self.training_data[task_type]) < 2:
            return

        X = []
        y = []

        for features, outcome in self.training_data[task_type][-100:]:  # Use last 100 samples
            X.append(features)
            y.append(outcome)

        X = np.array(X)
        y = np.array(y)

        try:
            self.models[task_type].fit(X, y)
        except Exception as e:
            logger.log("WARNING", "ContextualBanditRouter", f"Model training failed: {e}")


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
    Supports multiple RL methods: moving-average, contextual bandit, and PPO
    """

    def __init__(self, alpha: float = 0.1, reward_window: int = 50, rl_method: RLMethod = RLMethod.MOVING_AVERAGE):
        """
        Initialize the adaptive broker

        Args:
            alpha: Learning rate for reward updates
            reward_window: Window size for moving average calculations
            rl_method: Reinforcement learning method to use
        """
        self.alpha = alpha
        self.reward_window = reward_window
        self.rl_method = rl_method

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

        # RL components
        self.ppo_model = None
        self.ppo_env = None
        self.contextual_bandit = None

        # Initialize RL components if available
        if RL_AVAILABLE:
            self._initialize_rl_components()
        else:
            logger.log("WARNING", "AdaptiveTaskBroker", "RL dependencies not available, using basic moving average")

        logger.log("INFO", "AdaptiveTaskBroker", "Initialized adaptive task broker",
                  {"alpha": alpha, "reward_window": reward_window, "rl_method": rl_method.value})

    def _initialize_rl_components(self):
        """Initialize RL components based on selected method"""
        if self.rl_method == RLMethod.PPO:
            self._initialize_ppo()
        elif self.rl_method == RLMethod.CONTEXTUAL_BANDIT:
            self._initialize_contextual_bandit()

    def _initialize_ppo(self):
        """Initialize PPO model and environment"""
        try:
            task_types = ["general", "analysis", "computation", "communication", "creative"]
            agent_ids = []  # Will be populated when agents register

            # Create environment
            self.ppo_env = TaskRoutingEnv(agent_ids, task_types)

            # Create PPO model
            self.ppo_model = PPO(
                "MlpPolicy",
                self.ppo_env,
                learning_rate=3e-4,
                n_steps=2048,
                batch_size=64,
                n_epochs=10,
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2,
                verbose=0
            )

            logger.log("INFO", "AdaptiveTaskBroker", "PPO components initialized")

        except Exception as e:
            logger.log("ERROR", "AdaptiveTaskBroker", f"Failed to initialize PPO: {e}")
            self.rl_method = RLMethod.MOVING_AVERAGE

    def _initialize_contextual_bandit(self):
        """Initialize contextual bandit"""
        try:
            task_types = ["general", "analysis", "computation", "communication", "creative"]
            agent_ids = []  # Will be populated when agents register

            self.contextual_bandit = ContextualBanditRouter(agent_ids, task_types, self.alpha)
            logger.log("INFO", "AdaptiveTaskBroker", "Contextual bandit initialized")

        except Exception as e:
            logger.log("ERROR", "AdaptiveTaskBroker", f"Failed to initialize contextual bandit: {e}")
            self.rl_method = RLMethod.MOVING_AVERAGE

    def register_agent(self, agent_id: str, capabilities: List[str] = None):
        """Register a new agent with the broker"""
        if agent_id not in self.agent_performance:
            self.agent_performance[agent_id] = AgentPerformance(agent_id)

            # Initialize routing weights for task types
            for task_type in ["general", "analysis", "computation", "communication", "creative"]:
                self.routing_weights[task_type][agent_id] = 1.0  # Start with neutral weights

            # Update RL components
            self._update_rl_components()

            logger.log("INFO", "AdaptiveTaskBroker", f"Registered agent {agent_id}",
                      {"capabilities": capabilities, "rl_method": self.rl_method.value})

    def _update_rl_components(self):
        """Update RL components when agents change"""
        if not RL_AVAILABLE:
            return

        agent_ids = list(self.agent_performance.keys())

        if self.rl_method == RLMethod.PPO and self.ppo_env:
            # Update environment with new agents
            task_types = ["general", "analysis", "computation", "communication", "creative"]
            self.ppo_env.agent_ids = agent_ids
            self.ppo_env.num_agents = len(agent_ids)

            # Recreate action space
            self.ppo_env.action_space = spaces.Discrete(len(agent_ids))

            # Update observation space
            obs_dim = len(task_types) + len(agent_ids) * 3
            self.ppo_env.observation_space = spaces.Box(low=0, high=1, shape=(obs_dim,), dtype=np.float32)

        elif self.rl_method == RLMethod.CONTEXTUAL_BANDIT and self.contextual_bandit:
            # Update contextual bandit with new agents
            self.contextual_bandit.agent_ids = agent_ids
            self.contextual_bandit.num_agents = len(agent_ids)

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

        # Use appropriate RL method
        if self.rl_method == RLMethod.PPO and self.ppo_model and RL_AVAILABLE:
            selected_agent = self._assign_task_ppo(task_id, task_description, available_agents, task_type)
        elif self.rl_method == RLMethod.CONTEXTUAL_BANDIT and self.contextual_bandit and RL_AVAILABLE:
            selected_agent = self._assign_task_contextual_bandit(task_id, task_description, available_agents, task_type)
        else:
            selected_agent = self._assign_task_moving_average(task_id, task_description, available_agents, task_type)

        # Record the assignment
        assignment = TaskAssignment(
            task_id=task_id,
            agent_id=selected_agent,
            start_time=time.time(),
            task_type=task_type
        )
        self.active_assignments[task_id] = assignment

        logger.log("INFO", "AdaptiveTaskBroker", f"Assigned task {task_id} to agent {selected_agent}",
                  {"task_type": task_type, "rl_method": self.rl_method.value})

        return selected_agent

    def _assign_task_moving_average(self, task_id: str, task_description: str, available_agents: List[str],
                                   task_type: str = "general") -> str:
        """Assign task using moving average reward scores"""
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
            return available_agents[0]

        # Select agent with highest combined score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _assign_task_ppo(self, task_id: str, task_description: str, available_agents: List[str],
                        task_type: str = "general") -> str:
        """Assign task using PPO policy"""
        try:
            # Update environment with current performance
            perf_data = {}
            for agent_id, perf in self.agent_performance.items():
                perf_data[agent_id] = {
                    'success_rate': perf.success_rate,
                    'avg_latency': perf.avg_latency,
                    'reward_score': perf.reward_score
                }
            self.ppo_env.update_performance(perf_data)
            self.ppo_env.current_task_type = task_type

            # Get action from PPO model
            observation = self.ppo_env._get_observation()
            action, _ = self.ppo_model.predict(observation, deterministic=True)

            # Map action to available agent
            agent_id = self.ppo_env.agent_ids[action]
            if agent_id in available_agents:
                return agent_id
            else:
                # Fallback if selected agent not available
                return available_agents[0]

        except Exception as e:
            logger.log("WARNING", "AdaptiveTaskBroker", f"PPO assignment failed: {e}, falling back to moving average")
            return self._assign_task_moving_average(task_id, task_description, available_agents, task_type)

    def _assign_task_contextual_bandit(self, task_id: str, task_description: str, available_agents: List[str],
                                      task_type: str = "general") -> str:
        """Assign task using contextual bandit"""
        try:
            # Create context features from task description
            context_features = self._extract_task_features(task_description)

            # Select agent using contextual bandit
            selected_agent = self.contextual_bandit.select_agent(task_type, context_features)

            # Ensure selected agent is available
            if selected_agent in available_agents:
                return selected_agent
            else:
                return available_agents[0]

        except Exception as e:
            logger.log("WARNING", "AdaptiveTaskBroker", f"Contextual bandit assignment failed: {e}, falling back to moving average")
            return self._assign_task_moving_average(task_id, task_description, available_agents, task_type)

    def _extract_task_features(self, task_description: str) -> np.ndarray:
        """Extract features from task description for contextual bandit"""
        desc_lower = task_description.lower()

        # Simple feature extraction
        features = [
            len(task_description.split()),  # Length
            1.0 if 'urgent' in desc_lower else 0.0,  # Urgency
            1.0 if 'complex' in desc_lower else 0.0,  # Complexity
            1.0 if 'analysis' in desc_lower else 0.0,  # Analysis task
            1.0 if 'computation' in desc_lower else 0.0,  # Computation task
        ]

        return np.array(features)

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

        # Update RL models
        self._update_rl_models(assignment)

        # Move to history
        self.assignment_history.append(assignment)
        del self.active_assignments[task_id]

        logger.log("INFO", "AdaptiveTaskBroker", f"Task {task_id} completed",
                  {"success": success, "latency": latency, "agent": assignment.agent_id, "rl_method": self.rl_method.value})

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

    def _update_rl_models(self, assignment: TaskAssignment):
        """Update RL models with task completion feedback"""
        if not RL_AVAILABLE:
            return

        reward = self._calculate_reward(assignment)

        if self.rl_method == RLMethod.PPO and self.ppo_model:
            self._update_ppo_model(assignment, reward)
        elif self.rl_method == RLMethod.CONTEXTUAL_BANDIT and self.contextual_bandit:
            self._update_contextual_bandit(assignment, reward)

    def _update_ppo_model(self, assignment: TaskAssignment, reward: float):
        """Update PPO model with experience"""
        try:
            # Update environment performance data
            perf_data = {}
            for agent_id, perf in self.agent_performance.items():
                perf_data[agent_id] = {
                    'success_rate': perf.success_rate,
                    'avg_latency': perf.avg_latency,
                    'reward_score': perf.reward_score
                }
            self.ppo_env.update_performance(perf_data)

            # Set current task type for environment
            self.ppo_env.current_task_type = assignment.task_type

            # Get observation
            observation = self.ppo_env._get_observation()

            # For simplicity, we'll do online learning with single steps
            # In production, you'd batch experiences
            self.ppo_model.learn(total_timesteps=1, reset_num_timesteps=False)

        except Exception as e:
            logger.log("WARNING", "AdaptiveTaskBroker", f"PPO model update failed: {e}")

    def _update_contextual_bandit(self, assignment: TaskAssignment, reward: float):
        """Update contextual bandit with experience"""
        try:
            # Extract context features (we'd need to store these during assignment)
            # For now, use simple features
            context_features = self._extract_task_features(f"Task type: {assignment.task_type}")

            # Update the bandit
            self.contextual_bandit.update(
                assignment.task_type,
                assignment.agent_id,
                context_features,
                reward
            )

        except Exception as e:
            logger.log("WARNING", "AdaptiveTaskBroker", f"Contextual bandit update failed: {e}")

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

    def switch_rl_method(self, new_method: RLMethod):
        """Switch to a different RL method"""
        if new_method == self.rl_method:
            return

        old_method = self.rl_method
        self.rl_method = new_method

        # Reset RL components
        self.ppo_model = None
        self.ppo_env = None
        self.contextual_bandit = None

        # Initialize new RL components
        if RL_AVAILABLE:
            self._initialize_rl_components()
        else:
            logger.log("WARNING", "AdaptiveTaskBroker", "RL dependencies not available")

        logger.log("INFO", "AdaptiveTaskBroker", f"Switched RL method from {old_method.value} to {new_method.value}")

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "total_assignments": len(self.assignment_history),
            "active_assignments": len(self.active_assignments),
            "agent_performance": {},
            "routing_weights": dict(self.routing_weights),
            "learning_stats": {
                "alpha": self.alpha,
                "reward_window": self.reward_window,
                "rl_method": self.rl_method.value,
                "rl_available": RL_AVAILABLE
            }
        }

        # Add RL-specific stats
        if self.rl_method == RLMethod.PPO and self.ppo_model:
            report["rl_stats"] = {
                "ppo_learning_steps": getattr(self.ppo_model, '_n_updates', 0) if hasattr(self.ppo_model, '_n_updates') else 0
            }
        elif self.rl_method == RLMethod.CONTEXTUAL_BANDIT and self.contextual_bandit:
            report["rl_stats"] = {
                "bandit_training_samples": sum(len(samples) for samples in self.contextual_bandit.training_data.values())
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