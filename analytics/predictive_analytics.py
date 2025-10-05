from typing import Dict, List, Any, Optional, Tuple
from ..core.base import logger, metrics
import time
import statistics
from collections import deque
import math

class TaskCompletionPredictor:
    """Predicts task completion times based on historical data and current conditions"""

    def __init__(self, history_window: int = 100):
        self.completion_history: Dict[str, deque] = {}  # task_type -> completion times
        self.agent_performance: Dict[str, Dict[str, float]] = {}  # agent_id -> task_type -> avg_time
        self.complexity_factors: Dict[str, float] = {}  # task_type -> complexity multiplier
        self.history_window = history_window
        self.last_prediction_update = 0
        self.prediction_cache: Dict[str, Dict[str, Any]] = {}

    def record_task_completion(self, task_id: str, task_type: str, agent_id: str,
                             actual_time: float, success: bool):
        """Record a task completion for learning"""
        # Store in history by task type
        if task_type not in self.completion_history:
            self.completion_history[task_type] = deque(maxlen=self.history_window)

        if success:
            self.completion_history[task_type].append({
                'time': actual_time,
                'agent': agent_id,
                'timestamp': time.time()
            })

        # Update agent performance
        if agent_id not in self.agent_performance:
            self.agent_performance[agent_id] = {}

        if task_type not in self.agent_performance[agent_id]:
            self.agent_performance[agent_id][task_type] = actual_time
        else:
            # Exponential moving average
            alpha = 0.3
            self.agent_performance[agent_id][task_type] = (
                alpha * actual_time +
                (1 - alpha) * self.agent_performance[agent_id][task_type]
            )

        # Update complexity factors based on task characteristics
        self._update_complexity_factors(task_type, actual_time)

    def _update_complexity_factors(self, task_type: str, completion_time: float):
        """Update complexity factors based on completion times"""
        if task_type not in self.complexity_factors:
            self.complexity_factors[task_type] = 1.0

        # Adjust complexity factor based on how completion time compares to average
        if task_type in self.completion_history and len(self.completion_history[task_type]) > 5:
            avg_time = statistics.mean([entry['time'] for entry in self.completion_history[task_type]])
            if completion_time > avg_time * 1.5:
                self.complexity_factors[task_type] = min(self.complexity_factors[task_type] * 1.1, 3.0)
            elif completion_time < avg_time * 0.7:
                self.complexity_factors[task_type] = max(self.complexity_factors[task_type] * 0.9, 0.3)

    def predict_completion_time(self, task_description: str, task_type: str,
                              assigned_agent: str, current_load: int = 0) -> Dict[str, Any]:
        """Predict completion time for a task"""
        cache_key = f"{task_type}_{assigned_agent}_{hash(task_description) % 10000}"
        current_time = time.time()

        # Check cache (valid for 5 minutes)
        if (cache_key in self.prediction_cache and
            current_time - self.prediction_cache[cache_key]['timestamp'] < 300):
            return self.prediction_cache[cache_key]

        # Base prediction from historical data
        base_time = self._get_base_prediction(task_type, assigned_agent)

        # Adjust for task complexity
        complexity_multiplier = self._assess_task_complexity(task_description, task_type)

        # Adjust for agent load
        load_multiplier = 1.0 + (current_load * 0.2)  # 20% slower per load unit

        # Adjust for task dependencies and queue position
        dependency_multiplier = self._assess_dependencies(task_description)

        predicted_time = base_time * complexity_multiplier * load_multiplier * dependency_multiplier

        # Calculate confidence
        data_points = len(self.completion_history.get(task_type, []))
        confidence = min(0.9, data_points / 20.0)  # More data = higher confidence

        # Estimate range
        variance = self._calculate_prediction_variance(task_type)
        std_dev = math.sqrt(variance) if variance > 0 else predicted_time * 0.3
        time_range = {
            'lower': max(1, predicted_time - 1.96 * std_dev),
            'upper': predicted_time + 1.96 * std_dev
        }

        result = {
            'predicted_time': predicted_time,
            'time_range': time_range,
            'confidence': confidence,
            'factors': {
                'base_time': base_time,
                'complexity_multiplier': complexity_multiplier,
                'load_multiplier': load_multiplier,
                'dependency_multiplier': dependency_multiplier
            },
            'timestamp': current_time,
            'task_type': task_type,
            'agent': assigned_agent
        }

        # Cache result
        self.prediction_cache[cache_key] = result
        return result

    def _get_base_prediction(self, task_type: str, agent_id: str) -> float:
        """Get base prediction from historical data"""
        # Try agent-specific performance first
        if (agent_id in self.agent_performance and
            task_type in self.agent_performance[agent_id]):
            return self.agent_performance[agent_id][task_type]

        # Fall back to task type average
        if task_type in self.completion_history and self.completion_history[task_type]:
            times = [entry['time'] for entry in self.completion_history[task_type]]
            return statistics.mean(times)

        # Default estimates based on task type
        defaults = {
            'analysis': 45.0,
            'calculation': 30.0,
            'generation': 60.0,
            'search': 25.0,
            'processing': 40.0,
            'decision_making': 35.0
        }
        return defaults.get(task_type, 50.0)  # 50 seconds default

    def _assess_task_complexity(self, task_description: str, task_type: str) -> float:
        """Assess task complexity from description"""
        complexity = 1.0

        desc_lower = task_description.lower()
        word_count = len(task_description.split())

        # Length-based complexity
        if word_count > 100:
            complexity *= 1.5
        elif word_count > 50:
            complexity *= 1.2

        # Keyword-based complexity
        complex_keywords = ['complex', 'difficult', 'challenging', 'advanced', 'sophisticated',
                          'optimize', 'analyze', 'comprehensive', 'detailed']
        simple_keywords = ['simple', 'basic', 'quick', 'straightforward']

        complex_count = sum(1 for word in complex_keywords if word in desc_lower)
        simple_count = sum(1 for word in simple_keywords if word in desc_lower)

        complexity *= (1.0 + complex_count * 0.2 - simple_count * 0.1)

        # Apply learned complexity factor
        if task_type in self.complexity_factors:
            complexity *= self.complexity_factors[task_type]

        return max(0.5, min(complexity, 3.0))

    def _assess_dependencies(self, task_description: str) -> float:
        """Assess dependency impact on completion time"""
        desc_lower = task_description.lower()

        # Tasks that mention dependencies or prerequisites take longer
        if any(word in desc_lower for word in ['depends on', 'requires', 'after', 'following', 'based on']):
            return 1.3

        # Tasks that mention multiple steps
        if any(word in desc_lower for word in ['multiple', 'several', 'various', 'step-by-step']):
            return 1.2

        return 1.0

    def _calculate_prediction_variance(self, task_type: str) -> float:
        """Calculate variance in completion times for confidence intervals"""
        if task_type not in self.completion_history or len(self.completion_history[task_type]) < 2:
            return 0.0

        times = [entry['time'] for entry in self.completion_history[task_type]]
        if len(times) >= 2:
            return statistics.variance(times)
        return 0.0

class MemoryBottleneckPredictor:
    """Predicts memory bottlenecks based on usage patterns and task requirements"""

    def __init__(self, memory_threshold: float = 0.8, prediction_window: int = 3600):
        self.memory_history: deque = deque(maxlen=1000)  # Memory usage over time
        self.task_memory_requirements: Dict[str, Dict[str, Any]] = {}  # task_type -> memory stats
        self.agent_memory_patterns: Dict[str, Dict[str, Any]] = {}  # agent_id -> memory patterns
        self.memory_threshold = memory_threshold  # 80% of capacity
        self.prediction_window = prediction_window  # 1 hour prediction window
        self.bottleneck_predictions: List[Dict[str, Any]] = []

    def record_memory_usage(self, agent_id: str, memory_used: float, memory_capacity: float,
                          timestamp: float = None):
        """Record memory usage for analysis"""
        if timestamp is None:
            timestamp = time.time()

        self.memory_history.append({
            'agent_id': agent_id,
            'memory_used': memory_used,
            'memory_capacity': memory_capacity,
            'utilization': memory_used / memory_capacity if memory_capacity > 0 else 0,
            'timestamp': timestamp
        })

        # Update agent memory patterns
        if agent_id not in self.agent_memory_patterns:
            self.agent_memory_patterns[agent_id] = {
                'avg_utilization': memory_used / memory_capacity,
                'peak_utilization': memory_used / memory_capacity,
                'trend': 'stable',
                'samples': 1
            }
        else:
            pattern = self.agent_memory_patterns[agent_id]
            # Update running average
            pattern['avg_utilization'] = (
                (pattern['avg_utilization'] * pattern['samples'] + memory_used / memory_capacity) /
                (pattern['samples'] + 1)
            )
            pattern['peak_utilization'] = max(pattern['peak_utilization'], memory_used / memory_capacity)
            pattern['samples'] += 1

    def record_task_memory_impact(self, task_type: str, agent_id: str, memory_delta: float,
                                task_duration: float):
        """Record how tasks impact memory usage"""
        if task_type not in self.task_memory_requirements:
            self.task_memory_requirements[task_type] = {
                'memory_per_second': [],
                'peak_memory_increase': [],
                'duration_samples': []
            }

        req = self.task_memory_requirements[task_type]
        if task_duration > 0:
            req['memory_per_second'].append(memory_delta / task_duration)
        req['peak_memory_increase'].append(memory_delta)
        req['duration_samples'].append(task_duration)

        # Keep only recent samples
        max_samples = 50
        for key in req:
            if len(req[key]) > max_samples:
                req[key] = req[key][-max_samples:]

    def predict_memory_bottleneck(self, agent_id: str, upcoming_tasks: List[Dict[str, Any]],
                                time_horizon: int = 3600) -> Dict[str, Any]:
        """Predict if memory bottleneck will occur"""
        current_memory = self._get_current_memory_state(agent_id)
        if not current_memory:
            return {'bottleneck_predicted': False, 'confidence': 0.0}

        # Calculate projected memory usage
        projected_usage = current_memory['utilization']
        time_points = []

        current_time = time.time()
        for i, task in enumerate(upcoming_tasks):
            task_type = task.get('type', 'unknown')
            estimated_duration = task.get('estimated_duration', 60)  # Default 1 minute

            # Estimate memory impact
            memory_impact = self._estimate_task_memory_impact(task_type, agent_id)

            # Project memory usage over task duration
            task_start = current_time + sum(t.get('estimated_duration', 60) for t in upcoming_tasks[:i])
            task_end = task_start + estimated_duration

            # Linear memory increase during task
            for t in range(0, int(estimated_duration), 60):  # Sample every minute
                time_offset = sum(t.get('estimated_duration', 60) for t in upcoming_tasks[:i]) + t
                memory_at_time = projected_usage + (memory_impact * (t / estimated_duration))
                time_points.append({
                    'time_offset': time_offset,
                    'projected_utilization': min(1.0, memory_at_time),
                    'task_contribution': task.get('description', '')[:50]
                })

            projected_usage += memory_impact

        # Check for bottleneck
        bottleneck_time = None
        max_utilization = 0

        for point in time_points:
            if point['projected_utilization'] > self.memory_threshold:
                if bottleneck_time is None:
                    bottleneck_time = point['time_offset']
                max_utilization = max(max_utilization, point['projected_utilization'])

        # Calculate confidence based on data quality
        confidence = self._calculate_bottleneck_confidence(agent_id, upcoming_tasks)

        result = {
            'bottleneck_predicted': bottleneck_time is not None,
            'bottleneck_time_seconds': bottleneck_time,
            'max_projected_utilization': max_utilization,
            'confidence': confidence,
            'recommendations': self._generate_memory_recommendations(
                bottleneck_time is not None, max_utilization, upcoming_tasks
            ),
            'projection_points': time_points[:20]  # Limit for performance
        }

        # Store prediction for tracking
        self.bottleneck_predictions.append({
            'timestamp': time.time(),
            'agent_id': agent_id,
            'prediction': result
        })

        # Keep only recent predictions
        if len(self.bottleneck_predictions) > 100:
            self.bottleneck_predictions = self.bottleneck_predictions[-100:]

        return result

    def _get_current_memory_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get current memory state for an agent"""
        # Look for most recent memory reading for this agent
        for entry in reversed(self.memory_history):
            if entry['agent_id'] == agent_id:
                return entry
        return None

    def _estimate_task_memory_impact(self, task_type: str, agent_id: str) -> float:
        """Estimate memory impact of a task type"""
        if task_type in self.task_memory_requirements:
            req = self.task_memory_requirements[task_type]
            if req['peak_memory_increase']:
                return statistics.mean(req['peak_memory_increase'])
            elif req['memory_per_second']:
                # Estimate based on typical duration
                avg_rate = statistics.mean(req['memory_per_second'])
                typical_duration = statistics.mean(req['duration_samples']) if req['duration_samples'] else 60
                return avg_rate * typical_duration

        # Default estimates based on task type
        defaults = {
            'analysis': 0.1,    # 10% memory increase
            'processing': 0.15, # 15% memory increase
            'generation': 0.2,  # 20% memory increase
            'search': 0.05,     # 5% memory increase
            'calculation': 0.08 # 8% memory increase
        }
        return defaults.get(task_type, 0.1)

    def _calculate_bottleneck_confidence(self, agent_id: str, upcoming_tasks: List[Dict[str, Any]]) -> float:
        """Calculate confidence in bottleneck prediction"""
        confidence = 0.5  # Base confidence

        # More historical data = higher confidence
        agent_samples = len([e for e in self.memory_history if e['agent_id'] == agent_id])
        confidence += min(0.3, agent_samples / 100.0)

        # More task type data = higher confidence
        known_task_types = sum(1 for task in upcoming_tasks
                             if task.get('type') in self.task_memory_requirements)
        if upcoming_tasks:
            confidence += 0.2 * (known_task_types / len(upcoming_tasks))

        return min(0.9, confidence)

    def _generate_memory_recommendations(self, bottleneck_predicted: bool, max_utilization: float,
                                       upcoming_tasks: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations to prevent memory bottlenecks"""
        recommendations = []

        if bottleneck_predicted:
            recommendations.append("Memory bottleneck predicted - consider task reordering or resource allocation")

            if max_utilization > 0.95:
                recommendations.append("Critical memory usage predicted - immediate intervention required")

            # Suggest specific actions
            recommendations.append("Consider processing memory-intensive tasks sequentially")
            recommendations.append("Implement memory cleanup between tasks")

            # Task-specific recommendations
            memory_intensive_tasks = [task for task in upcoming_tasks
                                    if self._estimate_task_memory_impact(task.get('type', ''), '') > 0.15]
            if memory_intensive_tasks:
                recommendations.append(f"Schedule memory-intensive tasks separately: {[t.get('description', '')[:30] for t in memory_intensive_tasks]}")

        return recommendations

class FailurePredictor:
    """Predicts potential failures based on system state and historical patterns"""

    def __init__(self, failure_threshold: float = 0.3):
        self.failure_history: Dict[str, deque] = {}  # agent_id -> failure records
        self.system_failure_patterns: Dict[str, Dict[str, Any]] = {}  # Pattern -> failure stats
        self.agent_health_indicators: Dict[str, Dict[str, Any]] = {}  # agent_id -> health metrics
        self.failure_threshold = failure_threshold
        self.prediction_window = 3600  # 1 hour prediction window

    def record_agent_failure(self, agent_id: str, failure_type: str, context: Dict[str, Any]):
        """Record an agent failure for pattern analysis"""
        if agent_id not in self.failure_history:
            self.failure_history[agent_id] = deque(maxlen=200)

        self.failure_history[agent_id].append({
            'failure_type': failure_type,
            'context': context,
            'timestamp': time.time()
        })

        # Update failure patterns
        pattern_key = f"{failure_type}_{context.get('task_type', 'unknown')}"
        if pattern_key not in self.system_failure_patterns:
            self.system_failure_patterns[pattern_key] = {
                'count': 0,
                'recent_failures': deque(maxlen=50),
                'common_context': {}
            }

        pattern = self.system_failure_patterns[pattern_key]
        pattern['count'] += 1
        pattern['recent_failures'].append({
            'agent_id': agent_id,
            'timestamp': time.time(),
            'context': context
        })

    def update_agent_health(self, agent_id: str, health_metrics: Dict[str, Any]):
        """Update health indicators for an agent"""
        if agent_id not in self.agent_health_indicators:
            self.agent_health_indicators[agent_id] = {}

        self.agent_health_indicators[agent_id].update(health_metrics)
        self.agent_health_indicators[agent_id]['last_update'] = time.time()

    def predict_potential_failures(self, agent_id: str, task_context: Dict[str, Any],
                                 system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Predict potential failures for an agent in given context"""
        failure_risks = {}

        # Check agent-specific failure patterns
        agent_risk = self._assess_agent_failure_risk(agent_id, task_context)
        if agent_risk['risk'] > 0.1:
            failure_risks['agent_history'] = agent_risk

        # Check task-specific failure patterns
        task_risk = self._assess_task_failure_risk(task_context.get('task_type', 'unknown'), agent_id)
        if task_risk['risk'] > 0.1:
            failure_risks['task_type'] = task_risk

        # Check system-level failure patterns
        system_risk = self._assess_system_failure_risk(system_state, agent_id, task_context)
        if system_risk['risk'] > 0.1:
            failure_risks['system_state'] = system_risk

        # Check agent health indicators
        health_risk = self._assess_health_failure_risk(agent_id)
        if health_risk['risk'] > 0.1:
            failure_risks['agent_health'] = health_risk

        # Overall assessment
        overall_risk = max((risk['risk'] for risk in failure_risks.values()), default=0.0)
        overall_confidence = statistics.mean([risk['confidence'] for risk in failure_risks.values()]) if failure_risks else 0.0

        # Generate prevention recommendations
        recommendations = self._generate_failure_prevention_recommendations(failure_risks, overall_risk)

        return {
            'failure_predicted': overall_risk > self.failure_threshold,
            'overall_risk': overall_risk,
            'confidence': overall_confidence,
            'risk_breakdown': failure_risks,
            'recommendations': recommendations,
            'prediction_timestamp': time.time()
        }

    def _assess_agent_failure_risk(self, agent_id: str, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess failure risk based on agent's historical performance"""
        if agent_id not in self.failure_history:
            return {'risk': 0.05, 'confidence': 0.3, 'reason': 'No failure history'}

        failures = list(self.failure_history[agent_id])
        if not failures:
            return {'risk': 0.05, 'confidence': 0.3, 'reason': 'No recorded failures'}

        # Calculate failure rate
        total_tasks = len(failures)  # This is approximate since we don't track successes
        failure_rate = len([f for f in failures if f['timestamp'] > time.time() - 3600]) / max(total_tasks, 1)

        # Adjust for task type
        task_type = task_context.get('task_type', 'unknown')
        task_specific_failures = [f for f in failures if f.get('context', {}).get('task_type') == task_type]
        task_failure_rate = len(task_specific_failures) / max(len(failures), 1)

        risk = (failure_rate * 0.7 + task_failure_rate * 0.3)
        confidence = min(0.8, len(failures) / 20.0)

        return {
            'risk': risk,
            'confidence': confidence,
            'reason': f'Historical failure rate: {failure_rate:.1%}',
            'task_specific_risk': task_failure_rate
        }

    def _assess_task_failure_risk(self, task_type: str, agent_id: str) -> Dict[str, Any]:
        """Assess failure risk based on task type patterns"""
        pattern_key = f"unknown_{task_type}"  # Generic pattern for task type

        if pattern_key not in self.system_failure_patterns:
            return {'risk': 0.1, 'confidence': 0.2, 'reason': 'No pattern data for task type'}

        pattern = self.system_failure_patterns[pattern_key]
        recent_failures = len([f for f in pattern['recent_failures']
                             if f['timestamp'] > time.time() - 3600])

        # Calculate risk based on recent failure frequency
        risk = min(0.8, recent_failures / 10.0)  # Scale based on failures per hour
        confidence = min(0.7, pattern['count'] / 30.0)

        return {
            'risk': risk,
            'confidence': confidence,
            'reason': f'Recent failures for {task_type}: {recent_failures}',
            'total_pattern_failures': pattern['count']
        }

    def _assess_system_failure_risk(self, system_state: Dict[str, Any], agent_id: str,
                                  task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess failure risk based on current system state"""
        risk = 0.0
        reasons = []

        # Check system load
        system_load = system_state.get('system_load', 0.5)
        if system_load > 0.8:
            risk += 0.3
            reasons.append("High system load")
        elif system_load > 0.6:
            risk += 0.1
            reasons.append("Moderate system load")

        # Check agent load
        agent_load = system_state.get('agent_loads', {}).get(agent_id, 0)
        if agent_load >= 3:  # Near capacity
            risk += 0.25
            reasons.append("Agent near capacity")
        elif agent_load >= 2:
            risk += 0.1
            reasons.append("Agent moderately loaded")

        # Check memory pressure
        memory_pressure = system_state.get('memory_pressure', 0.5)
        if memory_pressure > 0.8:
            risk += 0.2
            reasons.append("High memory pressure")

        # Check task complexity vs agent capability
        task_complexity = task_context.get('complexity', 1.0)
        if task_complexity > 2.0 and agent_load > 1:
            risk += 0.15
            reasons.append("Complex task on loaded agent")

        confidence = 0.6  # System state assessment is moderately reliable

        return {
            'risk': min(risk, 1.0),
            'confidence': confidence,
            'reason': '; '.join(reasons) if reasons else 'System state normal'
        }

    def _assess_health_failure_risk(self, agent_id: str) -> Dict[str, Any]:
        """Assess failure risk based on agent health indicators"""
        if agent_id not in self.agent_health_indicators:
            return {'risk': 0.1, 'confidence': 0.2, 'reason': 'No health data available'}

        health = self.agent_health_indicators[agent_id]
        risk = 0.0
        reasons = []

        # Check response time degradation
        if 'avg_response_time' in health:
            response_time = health['avg_response_time']
            if response_time > 5000:  # 5 seconds
                risk += 0.3
                reasons.append("Slow response time")
            elif response_time > 2000:
                risk += 0.1
                reasons.append("Elevated response time")

        # Check error rate
        if 'error_rate' in health:
            error_rate = health['error_rate']
            if error_rate > 0.2:
                risk += 0.4
                reasons.append("High error rate")
            elif error_rate > 0.1:
                risk += 0.2
                reasons.append("Elevated error rate")

        # Check memory issues
        if 'memory_utilization' in health:
            mem_util = health['memory_utilization']
            if mem_util > 0.9:
                risk += 0.25
                reasons.append("Critical memory usage")
            elif mem_util > 0.8:
                risk += 0.1
                reasons.append("High memory usage")

        # Check staleness of health data
        last_update = health.get('last_update', 0)
        hours_old = (time.time() - last_update) / 3600
        if hours_old > 1:
            risk += 0.1  # Stale data increases uncertainty
            reasons.append("Health data outdated")

        confidence = 0.7 if hours_old < 1 else 0.4

        return {
            'risk': min(risk, 1.0),
            'confidence': confidence,
            'reason': '; '.join(reasons) if reasons else 'Agent health normal'
        }

    def _generate_failure_prevention_recommendations(self, failure_risks: Dict[str, Dict[str, Any]],
                                                   overall_risk: float) -> List[str]:
        """Generate recommendations to prevent predicted failures"""
        recommendations = []

        if overall_risk > self.failure_threshold:
            recommendations.append("High failure risk detected - consider preventive measures")

        # Agent-specific recommendations
        if 'agent_history' in failure_risks and failure_risks['agent_history']['risk'] > 0.2:
            recommendations.append("Agent has history of failures - consider alternative agent or reduced load")

        # Task-specific recommendations
        if 'task_type' in failure_risks and failure_risks['task_type']['risk'] > 0.2:
            recommendations.append("Task type has high failure rate - consider task decomposition or different approach")

        # System-level recommendations
        if 'system_state' in failure_risks:
            system_risk = failure_risks['system_state']
            if 'High system load' in system_risk['reason']:
                recommendations.append("Reduce system load by deferring non-critical tasks")
            if 'Agent near capacity' in system_risk['reason']:
                recommendations.append("Redistribute tasks to less loaded agents")

        # Health-based recommendations
        if 'agent_health' in failure_risks:
            health_risk = failure_risks['agent_health']
            if 'Slow response time' in health_risk['reason']:
                recommendations.append("Agent performance degraded - consider restart or health check")
            if 'High error rate' in health_risk['reason']:
                recommendations.append("Agent error rate elevated - investigate root cause")

        if not recommendations:
            recommendations.append("Monitor system closely for emerging issues")

        return recommendations

# Global predictor instances
task_completion_predictor = TaskCompletionPredictor()
memory_bottleneck_predictor = MemoryBottleneckPredictor()
failure_predictor = FailurePredictor()