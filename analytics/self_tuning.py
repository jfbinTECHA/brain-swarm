from typing import Dict, List, Any, Optional, Tuple, Set
from ..core.base import logger, metrics
import time
import statistics
import math
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
import random

class TuningParameter(Enum):
    REASONING_DEPTH = "reasoning_depth"
    BRANCH_LIMIT = "branch_limit"
    RETRY_STRATEGY = "retry_strategy"
    MEMORY_LIMIT = "memory_limit"
    TIMEOUT_DURATION = "timeout_duration"
    CONCURRENCY_LEVEL = "concurrency_level"
    QUALITY_THRESHOLD = "quality_threshold"
    RESOURCE_ALLOCATION = "resource_allocation"

class TuningStrategy(Enum):
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    BAYESIAN_OPTIMIZATION = "bayesian_optimization"
    EVOLUTIONARY_ALGORITHM = "evolutionary_algorithm"
    GRADIENT_DESCENT = "gradient_descent"
    ADAPTIVE_CONTROL = "adaptive_control"

class PerformanceMetric(Enum):
    TASK_SUCCESS_RATE = "task_success_rate"
    EXECUTION_TIME = "execution_time"
    RESOURCE_UTILIZATION = "resource_utilization"
    QUALITY_SCORE = "quality_score"
    ERROR_RATE = "error_rate"
    USER_SATISFACTION = "user_satisfaction"
    COST_EFFICIENCY = "cost_efficiency"

@dataclass
class ParameterConfiguration:
    """Represents a complete set of tuning parameters"""
    reasoning_depth: int = 3
    branch_limit: int = 2
    retry_attempts: int = 3
    retry_backoff_factor: float = 1.5
    memory_limit_mb: int = 512
    timeout_seconds: int = 300
    concurrency_limit: int = 5
    quality_threshold: float = 0.7
    resource_allocation_percent: float = 80.0
    timestamp: float = field(default_factory=time.time)
    performance_score: float = 0.0

@dataclass
class TuningExperiment:
    """Represents a parameter tuning experiment"""
    experiment_id: str
    parameters: ParameterConfiguration
    baseline_config: ParameterConfiguration
    start_time: float
    end_time: Optional[float] = None
    tasks_executed: int = 0
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    improvement_score: float = 0.0
    status: str = "running"  # running, completed, failed

@dataclass
class TuningDecision:
    """Represents a parameter adjustment decision"""
    decision_id: str
    parameter: TuningParameter
    old_value: Any
    new_value: Any
    reason: str
    confidence: float
    expected_improvement: float
    timestamp: float
    experiment_id: Optional[str] = None

class SelfTuningEngine:
    """Autonomous parameter tuning system for swarm optimization"""

    def __init__(self):
        self.current_config = ParameterConfiguration()
        self.baseline_config = ParameterConfiguration()  # Never modify this

        # Tuning history and experiments
        self.tuning_history: List[TuningDecision] = []
        self.active_experiments: Dict[str, TuningExperiment] = {}
        self.completed_experiments: List[TuningExperiment] = []

        # Performance tracking
        self.performance_history: deque = deque(maxlen=1000)
        self.metric_baselines: Dict[str, float] = {}

        # Tuning strategies
        self.tuning_strategy = TuningStrategy.REINFORCEMENT_LEARNING
        self.exploration_rate = 0.1  # 10% exploration, 90% exploitation
        self.learning_rate = 0.01

        # Parameter bounds and constraints
        self.parameter_bounds = self._initialize_parameter_bounds()

        # Performance monitoring
        self.monitoring_window = 100  # Tasks to consider for tuning decisions
        self.tuning_interval = 300  # Tune every 5 minutes
        self.last_tuning_time = time.time()

        # Quality gates
        self.min_performance_threshold = 0.6  # Don't tune if performance is too low
        self.max_risk_tolerance = 0.1  # Maximum allowed performance degradation

    def _initialize_parameter_bounds(self) -> Dict[TuningParameter, Tuple[Any, Any]]:
        """Initialize parameter bounds and constraints"""
        return {
            TuningParameter.REASONING_DEPTH: (1, 5),
            TuningParameter.BRANCH_LIMIT: (1, 4),
            TuningParameter.RETRY_STRATEGY: (1, 5),  # Retry attempts
            TuningParameter.MEMORY_LIMIT: (128, 2048),  # MB
            TuningParameter.TIMEOUT_DURATION: (60, 1800),  # Seconds
            TuningParameter.CONCURRENCY_LEVEL: (1, 20),
            TuningParameter.QUALITY_THRESHOLD: (0.5, 0.9),
            TuningParameter.RESOURCE_ALLOCATION: (50.0, 95.0)  # Percentage
        }

    def record_task_performance(self, task_id: str, performance_data: Dict[str, Any]):
        """Record task performance for tuning analysis"""

        performance_entry = {
            'task_id': task_id,
            'timestamp': time.time(),
            'config': self.current_config.__dict__.copy(),
            'metrics': performance_data,
            'overall_score': self._calculate_overall_performance_score(performance_data)
        }

        self.performance_history.append(performance_entry)

        # Update active experiments
        for experiment in self.active_experiments.values():
            if experiment.status == "running":
                experiment.tasks_executed += 1
                self._update_experiment_metrics(experiment, performance_data)

    def _calculate_overall_performance_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall performance score from individual metrics"""

        # Weights for different performance aspects
        weights = {
            'success': 0.3,
            'execution_time': 0.2,
            'quality': 0.25,
            'efficiency': 0.15,
            'error_rate': 0.1
        }

        score = 0.0

        # Success rate (higher is better)
        if 'success' in metrics:
            score += weights['success'] * (1.0 if metrics['success'] else 0.0)

        # Execution time (normalized - faster is better)
        if 'execution_time' in metrics:
            time_score = max(0, 1.0 - (metrics['execution_time'] / 600.0))  # 10 minutes max
            score += weights['execution_time'] * time_score

        # Quality score (direct mapping)
        if 'quality_score' in metrics:
            score += weights['quality'] * metrics['quality_score']

        # Resource efficiency (lower utilization is better, but not too low)
        if 'resource_utilization' in metrics:
            utilization = metrics['resource_utilization']
            efficiency_score = 1.0 - abs(utilization - 0.7) / 0.7  # Optimal at 70%
            score += weights['efficiency'] * efficiency_score

        # Error rate (lower is better)
        if 'error_rate' in metrics:
            error_score = 1.0 - min(1.0, metrics['error_rate'])
            score += weights['error_rate'] * error_score

        return max(0.0, min(1.0, score))

    def _update_experiment_metrics(self, experiment: TuningExperiment, metrics: Dict[str, Any]):
        """Update experiment performance metrics"""

        # Simple averaging for now - could be more sophisticated
        for metric_name, value in metrics.items():
            if metric_name not in experiment.performance_metrics:
                experiment.performance_metrics[metric_name] = []
            experiment.performance_metrics[metric_name].append(value)

            # Keep only recent metrics
            if len(experiment.performance_metrics[metric_name]) > 50:
                experiment.performance_metrics[metric_name] = experiment.performance_metrics[metric_name][-50:]

    def evaluate_tuning_opportunity(self) -> bool:
        """Evaluate if conditions are right for parameter tuning"""

        current_time = time.time()

        # Check timing
        if current_time - self.last_tuning_time < self.tuning_interval:
            return False

        # Check performance history
        if len(self.performance_history) < self.monitoring_window:
            return False

        # Check current performance level
        recent_scores = [entry['overall_score'] for entry in list(self.performance_history)[-20:]]
        avg_performance = statistics.mean(recent_scores) if recent_scores else 0

        if avg_performance < self.min_performance_threshold:
            logger.log("INFO", "SelfTuningEngine", f"Performance too low for tuning: {avg_performance:.2f}")
            return False

        # Check for performance variance (indicating tuning opportunity)
        if len(recent_scores) > 5:
            variance = statistics.variance(recent_scores)
            if variance < 0.01:  # Very stable performance
                logger.log("INFO", "SelfTuningEngine", f"Performance stable, low tuning priority: variance={variance:.4f}")
                return False

        return True

    def perform_autonomous_tuning(self) -> List[TuningDecision]:
        """Perform autonomous parameter tuning"""

        if not self.evaluate_tuning_opportunity():
            return []

        logger.log("INFO", "SelfTuningEngine", "Starting autonomous parameter tuning")

        decisions = []

        # Choose tuning strategy
        if self.tuning_strategy == TuningStrategy.REINFORCEMENT_LEARNING:
            decisions = self._reinforcement_learning_tuning()
        elif self.tuning_strategy == TuningStrategy.BAYESIAN_OPTIMIZATION:
            decisions = self._bayesian_optimization_tuning()
        else:
            decisions = self._adaptive_control_tuning()

        # Apply decisions with safety checks
        safe_decisions = self._apply_safety_checks(decisions)

        # Record successful tuning
        self.tuning_history.extend(safe_decisions)
        self.last_tuning_time = time.time()

        # Log tuning results
        if safe_decisions:
            logger.log("INFO", "SelfTuningEngine", f"Applied {len(safe_decisions)} parameter adjustments")
            for decision in safe_decisions:
                logger.log("INFO", "SelfTuningEngine", f"Tuned {decision.parameter.value}: {decision.old_value} -> {decision.new_value} "
                          f"(confidence: {decision.confidence:.2f})")

        return safe_decisions

    def _reinforcement_learning_tuning(self) -> List[TuningDecision]:
        """Reinforcement learning-based parameter tuning"""

        decisions = []

        # Analyze recent performance patterns
        recent_performance = list(self.performance_history)[-50:]
        if len(recent_performance) < 10:
            return decisions

        # Calculate performance gradients for each parameter
        parameter_gradients = self._calculate_parameter_gradients(recent_performance)

        # Tune parameters with significant gradients
        for param, gradient in parameter_gradients.items():
            if abs(gradient) > 0.05:  # Significant gradient threshold
                decision = self._create_tuning_decision(param, gradient)
                if decision:
                    decisions.append(decision)

        # Exploration: randomly tune one parameter occasionally
        if random.random() < self.exploration_rate:
            random_param = random.choice(list(TuningParameter))
            exploration_decision = self._create_exploration_decision(random_param)
            if exploration_decision:
                decisions.append(exploration_decision)

        return decisions

    def _calculate_parameter_gradients(self, performance_data: List[Dict]) -> Dict[TuningParameter, float]:
        """Calculate performance gradients with respect to parameters"""

        gradients = {}

        for param in TuningParameter:
            param_values = []
            performance_values = []

            for entry in performance_data:
                config = entry['config']
                param_value = self._get_parameter_value_from_config(config, param)
                performance = entry['overall_score']

                if param_value is not None:
                    param_values.append(param_value)
                    performance_values.append(performance)

            if len(param_values) >= 5:
                # Calculate correlation coefficient as gradient proxy
                try:
                    correlation = self._calculate_correlation(param_values, performance_values)
                    gradients[param] = correlation
                except:
                    gradients[param] = 0.0
            else:
                gradients[param] = 0.0

        return gradients

    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        sum_y2 = sum(yi * yi for yi in y)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = math.sqrt((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))

        return numerator / denominator if denominator != 0 else 0.0

    def _create_tuning_decision(self, parameter: TuningParameter, gradient: float) -> Optional[TuningDecision]:
        """Create a tuning decision based on gradient analysis"""

        current_value = self._get_current_parameter_value(parameter)
        bounds = self.parameter_bounds.get(parameter)

        if current_value is None or bounds is None:
            return None

        # Determine direction of change based on gradient
        if gradient > 0.1:  # Positive correlation - increase parameter
            new_value = self._adjust_parameter_value(current_value, 1, bounds)
        elif gradient < -0.1:  # Negative correlation - decrease parameter
            new_value = self._adjust_parameter_value(current_value, -1, bounds)
        else:
            return None  # No significant gradient

        if new_value == current_value:
            return None  # No change needed

        confidence = min(0.9, abs(gradient) * 2.0)  # Scale confidence by gradient magnitude
        expected_improvement = abs(gradient) * 0.1  # Conservative improvement estimate

        return TuningDecision(
            decision_id=f"tuning_{int(time.time())}_{parameter.value}",
            parameter=parameter,
            old_value=current_value,
            new_value=new_value,
            reason=f"Performance gradient analysis (correlation: {gradient:.3f})",
            confidence=confidence,
            expected_improvement=expected_improvement,
            timestamp=time.time()
        )

    def _create_exploration_decision(self, parameter: TuningParameter) -> Optional[TuningDecision]:
        """Create an exploration tuning decision"""

        current_value = self._get_current_parameter_value(parameter)
        bounds = self.parameter_bounds.get(parameter)

        if current_value is None or bounds is None:
            return None

        # Random adjustment within bounds
        if isinstance(current_value, (int, float)):
            min_val, max_val = bounds
            range_size = max_val - min_val
            adjustment = random.uniform(-range_size * 0.2, range_size * 0.2)
            new_value = max(min_val, min(max_val, current_value + adjustment))
        else:
            # For non-numeric parameters, keep current value
            new_value = current_value

        if new_value == current_value:
            return None

        return TuningDecision(
            decision_id=f"explore_{int(time.time())}_{parameter.value}",
            parameter=parameter,
            old_value=current_value,
            new_value=new_value,
            reason="Exploration: Random parameter adjustment",
            confidence=0.3,  # Lower confidence for exploration
            expected_improvement=0.0,  # Unknown for exploration
            timestamp=time.time()
        )

    def _bayesian_optimization_tuning(self) -> List[TuningDecision]:
        """Bayesian optimization-based parameter tuning (simplified)"""
        # This would implement Gaussian processes and acquisition functions
        # For now, fall back to reinforcement learning
        return self._reinforcement_learning_tuning()

    def _adaptive_control_tuning(self) -> List[TuningDecision]:
        """Adaptive control-based parameter tuning"""

        decisions = []

        # Simple adaptive control: adjust based on recent performance trends
        recent_scores = [entry['overall_score'] for entry in list(self.performance_history)[-20:]]

        if len(recent_scores) < 10:
            return decisions

        # Calculate trend
        trend = self._calculate_trend(recent_scores)

        if trend < -0.02:  # Declining performance
            # Try increasing quality threshold and reducing concurrency
            quality_decision = self._create_adaptive_decision(
                TuningParameter.QUALITY_THRESHOLD, 0.05,
                "Adaptive: Increasing quality threshold due to declining performance"
            )
            if quality_decision:
                decisions.append(quality_decision)

            concurrency_decision = self._create_adaptive_decision(
                TuningParameter.CONCURRENCY_LEVEL, -1,
                "Adaptive: Reducing concurrency due to declining performance"
            )
            if concurrency_decision:
                decisions.append(concurrency_decision)

        elif trend > 0.02:  # Improving performance
            # Try increasing concurrency and reasoning depth
            concurrency_decision = self._create_adaptive_decision(
                TuningParameter.CONCURRENCY_LEVEL, 1,
                "Adaptive: Increasing concurrency due to improving performance"
            )
            if concurrency_decision:
                decisions.append(concurrency_decision)

        return decisions

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate linear trend in values"""
        if len(values) < 3:
            return 0.0

        n = len(values)
        x = list(range(n))
        slope = self._calculate_slope(x, values)
        return slope

    def _calculate_slope(self, x: List[float], y: List[float]) -> float:
        """Calculate slope using linear regression"""
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = n * sum_x2 - sum_x * sum_x

        return numerator / denominator if denominator != 0 else 0.0

    def _create_adaptive_decision(self, parameter: TuningParameter, adjustment: float,
                                 reason: str) -> Optional[TuningDecision]:
        """Create an adaptive control decision"""

        current_value = self._get_current_parameter_value(parameter)
        bounds = self.parameter_bounds.get(parameter)

        if current_value is None or bounds is None:
            return None

        new_value = self._adjust_parameter_value(current_value, adjustment, bounds)

        if new_value == current_value:
            return None

        return TuningDecision(
            decision_id=f"adaptive_{int(time.time())}_{parameter.value}",
            parameter=parameter,
            old_value=current_value,
            new_value=new_value,
            reason=reason,
            confidence=0.6,  # Moderate confidence for adaptive control
            expected_improvement=0.05,  # Conservative estimate
            timestamp=time.time()
        )

    def _adjust_parameter_value(self, current_value: Any, adjustment: float,
                               bounds: Tuple[Any, Any]) -> Any:
        """Adjust parameter value within bounds"""

        min_val, max_val = bounds

        if isinstance(current_value, int):
            new_value = int(current_value + adjustment)
            return max(min_val, min(max_val, new_value))
        elif isinstance(current_value, float):
            new_value = current_value + adjustment
            return max(min_val, min(max_val, new_value))
        else:
            # For non-numeric parameters, return current value
            return current_value

    def _get_current_parameter_value(self, parameter: TuningParameter) -> Any:
        """Get current value of a parameter"""

        param_map = {
            TuningParameter.REASONING_DEPTH: self.current_config.reasoning_depth,
            TuningParameter.BRANCH_LIMIT: self.current_config.branch_limit,
            TuningParameter.RETRY_STRATEGY: self.current_config.retry_attempts,
            TuningParameter.MEMORY_LIMIT: self.current_config.memory_limit_mb,
            TuningParameter.TIMEOUT_DURATION: self.current_config.timeout_seconds,
            TuningParameter.CONCURRENCY_LEVEL: self.current_config.concurrency_limit,
            TuningParameter.QUALITY_THRESHOLD: self.current_config.quality_threshold,
            TuningParameter.RESOURCE_ALLOCATION: self.current_config.resource_allocation_percent
        }

        return param_map.get(parameter)

    def _get_parameter_value_from_config(self, config: Dict, parameter: TuningParameter) -> Any:
        """Extract parameter value from configuration dict"""

        param_keys = {
            TuningParameter.REASONING_DEPTH: 'reasoning_depth',
            TuningParameter.BRANCH_LIMIT: 'branch_limit',
            TuningParameter.RETRY_STRATEGY: 'retry_attempts',
            TuningParameter.MEMORY_LIMIT: 'memory_limit_mb',
            TuningParameter.TIMEOUT_DURATION: 'timeout_seconds',
            TuningParameter.CONCURRENCY_LEVEL: 'concurrency_limit',
            TuningParameter.QUALITY_THRESHOLD: 'quality_threshold',
            TuningParameter.RESOURCE_ALLOCATION: 'resource_allocation_percent'
        }

        key = param_keys.get(parameter)
        return config.get(key)

    def _apply_safety_checks(self, decisions: List[TuningDecision]) -> List[TuningDecision]:
        """Apply safety checks before applying tuning decisions"""

        safe_decisions = []

        for decision in decisions:
            # Check if change is within safe bounds
            if not self._is_safe_change(decision):
                logger.log("WARNING", "SelfTuningEngine", f"Rejected unsafe tuning decision: {decision.parameter.value} "
                            f"{decision.old_value} -> {decision.new_value}")
                continue

            # Check if change magnitude is reasonable
            if not self._is_reasonable_magnitude(decision):
                logger.log("WARNING", "SelfTuningEngine", f"Rejected unreasonable magnitude: {decision.parameter.value} "
                            f"{decision.old_value} -> {decision.new_value}")
                continue

            # Apply the change
            self._apply_parameter_change(decision)
            safe_decisions.append(decision)

        return safe_decisions

    def _is_safe_change(self, decision: TuningDecision) -> bool:
        """Check if parameter change is safe"""

        bounds = self.parameter_bounds.get(decision.parameter)
        if not bounds:
            return False

        min_val, max_val = bounds
        return min_val <= decision.new_value <= max_val

    def _is_reasonable_magnitude(self, decision: TuningDecision) -> bool:
        """Check if parameter change magnitude is reasonable"""

        if isinstance(decision.old_value, (int, float)) and isinstance(decision.new_value, (int, float)):
            change_percent = abs(decision.new_value - decision.old_value) / max(1, abs(decision.old_value))
            return change_percent <= 0.5  # Maximum 50% change at once

        return True  # Non-numeric changes are assumed reasonable

    def _apply_parameter_change(self, decision: TuningDecision):
        """Apply parameter change to current configuration"""

        param_map = {
            TuningParameter.REASONING_DEPTH: 'reasoning_depth',
            TuningParameter.BRANCH_LIMIT: 'branch_limit',
            TuningParameter.RETRY_STRATEGY: 'retry_attempts',
            TuningParameter.MEMORY_LIMIT: 'memory_limit_mb',
            TuningParameter.TIMEOUT_DURATION: 'timeout_seconds',
            TuningParameter.CONCURRENCY_LEVEL: 'concurrency_limit',
            TuningParameter.QUALITY_THRESHOLD: 'quality_threshold',
            TuningParameter.RESOURCE_ALLOCATION: 'resource_allocation_percent'
        }

        attr_name = param_map.get(decision.parameter)
        if attr_name:
            setattr(self.current_config, attr_name, decision.new_value)
            self.current_config.timestamp = time.time()

            logger.log("INFO", "SelfTuningEngine", f"Applied parameter change: {decision.parameter.value} = {decision.new_value}")

    def get_tuning_status(self) -> Dict[str, Any]:
        """Get comprehensive tuning status"""

        recent_decisions = self.tuning_history[-10:] if self.tuning_history else []

        # Calculate tuning effectiveness
        if len(self.performance_history) >= 20:
            recent_performance = [entry['overall_score'] for entry in list(self.performance_history)[-20:]]
            baseline_performance = [entry['overall_score'] for entry in list(self.performance_history)[-40:-20]]

            if baseline_performance:
                improvement = statistics.mean(recent_performance) - statistics.mean(baseline_performance)
                effectiveness = "improving" if improvement > 0.05 else "stable" if improvement > -0.05 else "declining"
            else:
                effectiveness = "unknown"
        else:
            effectiveness = "insufficient_data"

        return {
            "current_config": self.current_config.__dict__,
            "baseline_config": self.baseline_config.__dict__,
            "tuning_strategy": self.tuning_strategy.value,
            "active_experiments": len(self.active_experiments),
            "completed_experiments": len(self.completed_experiments),
            "total_decisions": len(self.tuning_history),
            "recent_decisions": [
                {
                    "decision_id": d.decision_id,
                    "parameter": d.parameter.value,
                    "old_value": d.old_value,
                    "new_value": d.new_value,
                    "reason": d.reason,
                    "confidence": d.confidence,
                    "timestamp": d.timestamp
                }
                for d in recent_decisions
            ],
            "performance_metrics": {
                "total_measurements": len(self.performance_history),
                "average_score": statistics.mean([p['overall_score'] for p in self.performance_history]) if self.performance_history else 0,
                "effectiveness": effectiveness
            },
            "last_tuning": self.last_tuning_time,
            "next_tuning": self.last_tuning_time + self.tuning_interval
        }

    def reset_to_baseline(self):
        """Reset all parameters to baseline configuration"""
        self.current_config = ParameterConfiguration(
            reasoning_depth=self.baseline_config.reasoning_depth,
            branch_limit=self.baseline_config.branch_limit,
            retry_attempts=self.baseline_config.retry_attempts,
            retry_backoff_factor=self.baseline_config.retry_backoff_factor,
            memory_limit_mb=self.baseline_config.memory_limit_mb,
            timeout_seconds=self.baseline_config.timeout_seconds,
            concurrency_limit=self.baseline_config.concurrency_limit,
            quality_threshold=self.baseline_config.quality_threshold,
            resource_allocation_percent=self.baseline_config.resource_allocation_percent,
            timestamp=time.time(),
            performance_score=0.0
        )

        logger.log("INFO", "SelfTuningEngine", "Reset all parameters to baseline configuration")

    def export_tuning_data(self) -> Dict[str, Any]:
        """Export tuning data for analysis"""

        return {
            "current_config": self.current_config.__dict__,
            "baseline_config": self.baseline_config.__dict__,
            "tuning_history": [
                {
                    "decision_id": d.decision_id,
                    "parameter": d.parameter.value,
                    "old_value": d.old_value,
                    "new_value": d.new_value,
                    "reason": d.reason,
                    "confidence": d.confidence,
                    "expected_improvement": d.expected_improvement,
                    "timestamp": d.timestamp
                }
                for d in self.tuning_history
            ],
            "performance_history": list(self.performance_history),
            "active_experiments": [
                {
                    "experiment_id": exp.experiment_id,
                    "parameters": exp.parameters.__dict__,
                    "tasks_executed": exp.tasks_executed,
                    "performance_metrics": exp.performance_metrics,
                    "status": exp.status
                }
                for exp in self.active_experiments.values()
            ],
            "export_timestamp": time.time()
        }

# SelfTuningParameterManager - Legacy compatibility class
class SelfTuningParameterManager:
    """Legacy compatibility class for SelfTuningEngine"""

    def __init__(self):
        self.engine = self_tuning_engine

    def get_adaptive_parameters(self, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get adaptive parameters for task execution"""
        return {
            'reasoning_depth': self.engine.current_config.reasoning_depth,
            'branch_limit': self.engine.current_config.branch_limit,
            'retry_attempts': self.engine.current_config.retry_attempts,
            'timeout': self.engine.current_config.timeout_seconds
        }

    def record_performance(self, task_id: str, metrics: Dict[str, Any]):
        """Record task performance"""
        self.engine.record_task_performance(task_id, metrics)

# Global instances
self_tuning_engine = SelfTuningEngine()
self_tuning_parameter_manager = SelfTuningParameterManager()

# Integration functions
def record_task_performance(task_id: str, performance_data: Dict[str, Any]):
    """Record task performance for tuning"""
    self_tuning_engine.record_task_performance(task_id, performance_data)

def perform_autonomous_tuning() -> List[TuningDecision]:
    """Perform autonomous parameter tuning"""
    return self_tuning_engine.perform_autonomous_tuning()

def get_tuning_status() -> Dict[str, Any]:
    """Get tuning status"""
    return self_tuning_engine.get_tuning_status()

def get_current_config() -> ParameterConfiguration:
    """Get current parameter configuration"""
    return self_tuning_engine.current_config

def reset_tuning_to_baseline():
    """Reset tuning to baseline"""
    self_tuning_engine.reset_to_baseline()

def export_tuning_data() -> Dict[str, Any]:
    """Export tuning data"""
    return self_tuning_engine.export_tuning_data()

# Legacy compatibility functions
def get_adaptive_reasoning_depth(task_context: Dict[str, Any]) -> int:
    """Get adaptive reasoning depth based on task context"""
    complexity = task_context.get('complexity', 'medium')
    if complexity == 'high':
        return min(self_tuning_engine.current_config.reasoning_depth + 1, 5)
    elif complexity == 'low':
        return max(self_tuning_engine.current_config.reasoning_depth - 1, 1)
    else:
        return self_tuning_engine.current_config.reasoning_depth

def get_adaptive_branch_limits(task_context: Dict[str, Any]) -> int:
    """Get adaptive branch limits based on task context"""
    exploration = task_context.get('exploration_needed', False)
    if exploration:
        return min(self_tuning_engine.current_config.branch_limit + 1, 4)
    else:
        return self_tuning_engine.current_config.branch_limit

def get_adaptive_retry_strategy(task_context: Dict[str, Any]) -> Dict[str, Any]:
    """Get adaptive retry strategy"""
    return {
        'attempts': self_tuning_engine.current_config.retry_attempts,
        'backoff_factor': self_tuning_engine.current_config.retry_backoff_factor
    }

def record_task_performance_for_tuning(task_metrics: Dict[str, Any]):
    """Record task performance for tuning (legacy function)"""
    # Convert metrics to expected format
    performance_data = {
        'success': task_metrics.get('success', True),
        'execution_time': task_metrics.get('completion_time', 0),
        'quality_score': task_metrics.get('quality', 0.8),
        'resource_utilization': task_metrics.get('resource_usage', 0.5),
        'error_rate': 0.0 if task_metrics.get('success', True) else 0.2
    }
    self_tuning_engine.record_task_performance(f"task_{int(time.time())}", performance_data)

def get_self_tuning_status() -> Dict[str, Any]:
    """Get self-tuning status (legacy function)"""
    return self_tuning_engine.get_tuning_status()