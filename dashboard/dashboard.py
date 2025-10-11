from typing import Dict, List, Any, Optional
from core.base import metrics, logger
from federation.federation import swarm_manager, federation_manager
from dashboard.recursive_improvement import recursive_improvement
import time
import json

# Optional import for SwarmCoordinator
try:
    from coordination.coordinator import SwarmCoordinator
except ImportError:
    SwarmCoordinator = None

class BrainSwarmDashboard:
    """Comprehensive dashboard for brain swarm monitoring and visualization"""

    def __init__(self, coordinator: Optional[SwarmCoordinator] = None, swarm_id: Optional[str] = None):
        self.coordinator = coordinator
        self.swarm_id = swarm_id  # Specific swarm to monitor, or None for all swarms
        self.dashboard_data = {}
        self.last_update = 0
        self.update_interval = 5  # Update every 5 seconds

    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive performance monitoring dashboard"""
        current_time = time.time()

        # Check if we need to refresh data
        if current_time - self.last_update > self.update_interval:
            self._refresh_dashboard_data()
            self.last_update = current_time

        dashboard = {
            "dashboard_type": "performance_monitoring",
            "generated_at": current_time,
            "time_range": "real-time",
            "sections": {}
        }

        # Agent Performance Section
        dashboard["sections"]["agent_performance"] = self._generate_agent_performance_section()

        # System Resources Section
        dashboard["sections"]["system_resources"] = self._generate_system_resources_section()

        # Task Execution Section
        dashboard["sections"]["task_execution"] = self._generate_task_execution_section()

        # Reasoning Performance Section
        dashboard["sections"]["reasoning_performance"] = self._generate_reasoning_performance_section()

        # Error & Recovery Section
        dashboard["sections"]["error_recovery"] = self._generate_error_recovery_section()

        return dashboard

    def get_learning_insights_dashboard(self) -> Dict[str, Any]:
        """Generate learning insights and adaptation visualization dashboard"""
        dashboard = {
            "dashboard_type": "learning_insights",
            "generated_at": time.time(),
            "sections": {}
        }

        # Recursive Improvement Section
        dashboard["sections"]["recursive_improvement"] = self._generate_recursive_improvement_section()

        # Failure Pattern Analysis Section
        dashboard["sections"]["failure_patterns"] = self._generate_failure_patterns_section()

        # Adaptation Timeline Section
        dashboard["sections"]["adaptation_timeline"] = self._generate_adaptation_timeline_section()

        # Meta-Learning Insights Section
        dashboard["sections"]["meta_learning"] = self._generate_meta_learning_section()

        return dashboard

    def get_operational_oversight_dashboard(self) -> Dict[str, Any]:
        """Generate operational oversight dashboard for swarm health"""
        dashboard = {
            "dashboard_type": "operational_oversight",
            "generated_at": time.time(),
            "sections": {}
        }

        # Swarm Health Section
        dashboard["sections"]["swarm_health"] = self._generate_swarm_health_section()

        # Task Queue Status Section
        dashboard["sections"]["task_queues"] = self._generate_task_queues_section()

        # Agent Load Distribution Section
        dashboard["sections"]["agent_load"] = self._generate_agent_load_section()

        # Memory Usage Section
        dashboard["sections"]["memory_usage"] = self._generate_memory_usage_section()

        return dashboard

    def get_federation_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive federation-level dashboard"""
        dashboard = {
            "dashboard_type": "federation_overview",
            "generated_at": time.time(),
            "sections": {}
        }

        # Federation Health Section
        dashboard["sections"]["federation_health"] = self._generate_federation_health_section()

        # Inter-Swarm Communications Section
        dashboard["sections"]["inter_swarm_communications"] = self._generate_inter_swarm_communications_section()

        # Resource Sharing Section
        dashboard["sections"]["resource_sharing"] = self._generate_resource_sharing_section()

        # Conflict Resolution Section
        dashboard["sections"]["conflict_resolution"] = self._generate_conflict_resolution_section()

        # Federation Optimization Section
        dashboard["sections"]["federation_optimization"] = self._generate_federation_optimization_section()

        return dashboard

    def get_predictive_control_dashboard(self) -> Dict[str, Any]:
        """Generate predictive control and resource allocation dashboard"""
        dashboard = {
            "dashboard_type": "predictive_control",
            "generated_at": time.time(),
            "sections": {}
        }

        # Load Forecasting Section
        dashboard["sections"]["load_forecasting"] = self._generate_load_forecasting_section()

        # Preventive Actions Section
        dashboard["sections"]["preventive_actions"] = self._generate_preventive_actions_section()

        # Resource Recommendations Section
        dashboard["sections"]["resource_recommendations"] = self._generate_resource_recommendations_section()

        # System Health Predictions Section
        dashboard["sections"]["system_health_predictions"] = self._generate_system_health_predictions_section()

        return dashboard

    def get_comprehensive_traceability_dashboard(self, task_id: str = None, agent_id: str = None,
                                               hours_back: int = 24) -> Dict[str, Any]:
        """Generate comprehensive traceability dashboard"""
        start_time = time.time() - (hours_back * 3600)

        dashboard = {
            "dashboard_type": "comprehensive_traceability",
            "generated_at": time.time(),
            "time_range_hours": hours_back,
            "filters": {"task_id": task_id, "agent_id": agent_id},
            "sections": {}
        }

        # Get comprehensive traceability report
        trace_report = metrics.get_comprehensive_traceability_report(
            task_id=task_id,
            agent_id=agent_id,
            start_time=start_time
        )

        dashboard["sections"]["traceability_data"] = trace_report

        # Add visualization data
        dashboard["sections"]["visualization"] = {
            "reasoning_flow": trace_report.get("reasoning_flow", {}),
            "timeline_data": self._generate_timeline_visualization(trace_report),
            "decision_tree": self._generate_decision_tree_visualization(trace_report),
            "tree_of_thought_maps": self._generate_tree_of_thought_maps(trace_report),
            "chain_of_thought_traces": self._generate_chain_of_thought_traces(trace_report)
        }

        return dashboard

    def get_reasoning_visualization_dashboard(self, task_id: str = None, agent_id: str = None) -> Dict[str, Any]:
        """Generate specialized reasoning visualization dashboard"""
        dashboard = {
            "dashboard_type": "reasoning_visualization",
            "generated_at": time.time(),
            "sections": {}
        }

        # Get reasoning data
        trace_report = metrics.get_comprehensive_traceability_report(
            task_id=task_id,
            agent_id=agent_id,
            start_time=time.time() - 3600  # Last hour
        )

        # Tree-of-Thought Maps Section
        dashboard["sections"]["tree_of_thought_maps"] = {
            "title": "Tree-of-Thought Maps",
            "description": "Graphical trees showing all reasoning branches, scores, and selected paths",
            "data": self._generate_tree_of_thought_maps(trace_report)
        }

        # Chain-of-Thought Traces Section
        dashboard["sections"]["chain_of_thought_traces"] = {
            "title": "Chain-of-Thought Traces",
            "description": "Step-by-step reasoning logs with decision points and clarifications",
            "data": self._generate_chain_of_thought_traces(trace_report)
        }

        # Reasoning Performance Section
        dashboard["sections"]["reasoning_performance"] = {
            "title": "Reasoning Performance Metrics",
            "data": self._generate_reasoning_performance_visualization(trace_report)
        }

        return dashboard

    def get_agent_performance_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive agent performance dashboard with metrics and visualizations"""
        dashboard = {
            "dashboard_type": "agent_performance",
            "generated_at": time.time(),
            "sections": {}
        }

        # Agent Overview Section
        dashboard["sections"]["agent_overview"] = {
            "title": "Agent Performance Overview",
            "description": "Comprehensive performance metrics for all agents",
            "data": self._generate_agent_performance_overview()
        }

        # Task Performance Section
        dashboard["sections"]["task_performance"] = {
            "title": "Task Execution Metrics",
            "description": "Task count, success rates, and execution times per agent",
            "data": self._generate_task_performance_metrics()
        }

        # Load and Resource Usage Section
        dashboard["sections"]["load_and_resources"] = {
            "title": "Load and Resource Utilization",
            "description": "Current load, branch usage, and memory footprint per agent",
            "data": self._generate_load_and_resource_metrics()
        }

        # Visual Elements Section
        dashboard["sections"]["visual_elements"] = {
            "title": "Performance Visualizations",
            "description": "Charts and indicators for performance analysis",
            "data": self._generate_performance_visualizations()
        }

        # Agent Comparison Section
        dashboard["sections"]["agent_comparison"] = {
            "title": "Agent Comparison Analysis",
            "description": "Comparative analysis across all agents",
            "data": self._generate_agent_comparison_data()
        }

        return dashboard

    def _refresh_dashboard_data(self):
        """Refresh cached dashboard data"""
        base_data = {
            "agent_metrics": metrics.agent_metrics.copy(),
            "reasoning_metrics": metrics.reasoning_metrics.copy(),
            "task_metrics": metrics.task_metrics.copy(),
            "consensus_metrics": metrics.consensus_metrics.copy() if hasattr(metrics, 'consensus_metrics') else [],
            "failure_logs": metrics.failure_logs.copy() if hasattr(metrics, 'failure_logs') else [],
            "performance_history": metrics.performance_history.copy() if hasattr(metrics, 'performance_history') else []
        }

        # Add swarm-specific data
        if self.swarm_id:
            # Single swarm mode
            coordinator = swarm_manager.get_swarm(self.swarm_id)
            if coordinator:
                swarm_data = {
                    "agent_loads": coordinator.agent_loads.copy(),
                    "active_tasks": len(coordinator.delegation_system.active_tasks),
                    "mini_coordinators": len(coordinator.mini_coordinators),
                    "swarm_id": self.swarm_id
                }
                base_data.update(swarm_data)
        else:
            # Multi-swarm mode - aggregate data from all swarms
            swarm_stats = swarm_manager.get_swarm_stats()
            multi_swarm_data = {
                "swarm_stats": swarm_stats,
                "total_swarms": len(swarm_stats),
                "all_agent_loads": {},
                "total_active_tasks": 0,
                "total_mini_coordinators": 0
            }

            for swarm_id, stats in swarm_stats.items():
                multi_swarm_data["all_agent_loads"].update({f"{swarm_id}_{agent}": load for agent, load in stats["load_balance"]["agent_loads"].items()})
                multi_swarm_data["total_active_tasks"] += stats["active_tasks"]
                multi_swarm_data["total_mini_coordinators"] += stats["mini_coordinators"]

            base_data.update(multi_swarm_data)

        # Add coordinator data if available (for backward compatibility)
        if self.coordinator:
            base_data.update({
                "agent_loads": self.coordinator.agent_loads.copy(),
                "active_tasks": len(self.coordinator.delegation_system.active_tasks),
                "mini_coordinators": len(self.coordinator.mini_coordinators)
            })

        self.dashboard_data = base_data

    def _generate_agent_performance_section(self) -> Dict[str, Any]:
        """Generate agent performance section"""
        section = {
            "title": "Agent Performance Rankings",
            "data": [],
            "summary": {}
        }

        agent_rankings = []
        total_tasks = 0
        total_success = 0

        for agent_id, metrics_data in self.dashboard_data.get("agent_metrics", {}).items():
            success_rate = (metrics_data["successful_tasks"] / metrics_data["total_tasks"]) * 100 if metrics_data["total_tasks"] > 0 else 0
            avg_time = metrics_data["total_execution_time"] / metrics_data["total_tasks"] if metrics_data["total_tasks"] > 0 else 0
            efficiency = success_rate / (avg_time + 1)  # Avoid division by zero

            agent_rankings.append({
                "agent_id": agent_id,
                "success_rate": round(success_rate, 1),
                "avg_execution_time": round(avg_time, 2),
                "efficiency_score": round(efficiency, 2),
                "total_tasks": metrics_data["total_tasks"],
                "quality_score": round(metrics_data["avg_quality"], 2),
                "task_types": metrics_data.get("task_types", {})
            })

            total_tasks += metrics_data["total_tasks"]
            total_success += metrics_data["successful_tasks"]

        # Sort by efficiency
        agent_rankings.sort(key=lambda x: x["efficiency_score"], reverse=True)

        section["data"] = agent_rankings
        section["summary"] = {
            "total_agents": len(agent_rankings),
            "overall_success_rate": round((total_success / total_tasks * 100) if total_tasks > 0 else 0, 1),
            "total_tasks_processed": total_tasks,
            "avg_agent_efficiency": round(sum(a["efficiency_score"] for a in agent_rankings) / len(agent_rankings), 2) if agent_rankings else 0
        }

        return section

    def _get_agent_decision_cards(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get recent decision cards for an agent showing confidence scores, self-ask prompts, and reasoning snippets"""
        decision_cards = []

        # Get recent reasoning traces for this agent
        trace_report = metrics.get_comprehensive_traceability_report(
            agent_id=agent_id,
            start_time=time.time() - 3600  # Last hour
        )

        reasoning_traces = trace_report.get("reasoning_traces", [])
        recent_traces = reasoning_traces[-5:]  # Last 5 decisions

        for trace in recent_traces:
            # Extract self-ask guidance if available
            self_ask_prompts = []
            if trace.get("reasoning_steps"):
                for step in trace["reasoning_steps"]:
                    if "clarify" in step.get("description", "").lower() or "?" in step.get("description", ""):
                        self_ask_prompts.append(step["description"])

            # Create decision card
            decision_card = {
                "timestamp": trace.get("timestamp", time.time()),
                "task_id": trace.get("task_id", "unknown"),
                "confidence_score": trace.get("confidence", 0),
                "self_ask_prompts": self_ask_prompts[:3],  # Limit to 3 prompts
                "reasoning_snippets": [
                    step.get("description", "")[:100] + "..." if len(step.get("description", "")) > 100 else step.get("description", "")
                    for step in trace.get("reasoning_steps", [])[:3]  # First 3 reasoning steps
                ],
                "final_decision": trace.get("final_decision", "Unknown")[:200] + "..." if len(trace.get("final_decision", "")) > 200 else trace.get("final_decision", ""),
                "decision_quality": self._assess_decision_quality(trace, trace_report)
            }
            decision_cards.append(decision_card)

        return decision_cards

    def _generate_system_resources_section(self) -> Dict[str, Any]:
        """Generate system resources section"""
        section = {
            "title": "System Resource Utilization",
            "data": {}
        }

        # Agent load data
        agent_loads = self.dashboard_data.get("agent_loads", {})
        total_load = sum(agent_loads.values())
        max_concurrent = self.coordinator.max_agent_load if self.coordinator else 3

        section["data"]["agent_load"] = {
            "current_load": total_load,
            "max_capacity": len(agent_loads) * max_concurrent if agent_loads else 0,
            "utilization_percent": round((total_load / (len(agent_loads) * max_concurrent)) * 100, 1) if agent_loads else 0,
            "agent_distribution": agent_loads
        }

        # Memory usage (estimated)
        section["data"]["memory_usage"] = {
            "working_memory_entries": len(metrics.memory_store) if hasattr(metrics, 'memory_store') else 0,
            "intermediate_results": len(metrics.intermediate_results) if hasattr(metrics, 'intermediate_results') else 0,
            "long_term_memory_entries": len(metrics.episodic_store) + len(metrics.semantic_store) if hasattr(metrics, 'episodic_store') else 0
        }

        # Active processes
        section["data"]["active_processes"] = {
            "active_tasks": self.dashboard_data.get("active_tasks", 0),
            "mini_coordinators": self.dashboard_data.get("mini_coordinators", 0),
            "reasoning_branches": sum(metrics.active_reasoning_branches.values()) if hasattr(metrics, 'active_reasoning_branches') else 0
        }

        return section

    def _generate_task_execution_section(self) -> Dict[str, Any]:
        """Generate task execution section"""
        section = {
            "title": "Task Execution Analytics",
            "data": {}
        }

        task_metrics = self.dashboard_data.get("task_metrics", [])
        if task_metrics:
            recent_tasks = task_metrics[-10:]  # Last 10 tasks

            section["data"]["recent_performance"] = {
                "avg_execution_time": round(sum(t["total_time"] for t in recent_tasks) / len(recent_tasks), 2),
                "avg_success_rate": round(sum(t["success_rate"] for t in recent_tasks) / len(recent_tasks) * 100, 1),
                "avg_quality": round(sum(t["final_quality"] for t in recent_tasks) / len(recent_tasks), 2),
                "task_count": len(recent_tasks)
            }

            # Task type distribution
            task_types = {}
            for task in recent_tasks:
                task_type = task.get("description", "").split()[0].lower()  # Simple extraction
                task_types[task_type] = task_types.get(task_type, 0) + 1

            section["data"]["task_type_distribution"] = task_types

        return section

    def _generate_reasoning_performance_section(self) -> Dict[str, Any]:
        """Generate reasoning performance section"""
        section = {
            "title": "Reasoning Performance Analysis",
            "data": {}
        }

        reasoning_metrics = self.dashboard_data.get("reasoning_metrics", {})

        for reasoning_type, data in reasoning_metrics.items():
            success_rate = (data["successful_runs"] / data["total_runs"]) * 100 if data["total_runs"] > 0 else 0
            avg_steps = data["total_steps"] / data["total_runs"] if data["total_runs"] > 0 else 0
            avg_time = data["total_time"] / data["total_runs"] if data["total_runs"] > 0 else 0

            section["data"][reasoning_type] = {
                "success_rate": round(success_rate, 1),
                "avg_steps": round(avg_steps, 1),
                "avg_execution_time": round(avg_time, 2),
                "total_runs": data["total_runs"],
                "efficiency": round(success_rate / avg_time, 2) if avg_time > 0 else 0
            }

        return section

    def _generate_error_recovery_section(self) -> Dict[str, Any]:
        """Generate error and recovery section"""
        section = {
            "title": "Error Analysis & Recovery",
            "data": {}
        }

        failure_logs = self.dashboard_data.get("failure_logs", [])
        if failure_logs:
            # Error type distribution
            error_types = {}
            recovery_success = 0

            for failure in failure_logs[-50:]:  # Last 50 failures
                error_type = failure.get("error_type", "Unknown")
                error_types[error_type] = error_types.get(error_type, 0) + 1

                if failure.get("recovery_successful", False):
                    recovery_success += 1

            section["data"]["error_distribution"] = error_types
            section["data"]["recovery_stats"] = {
                "total_failures": len(failure_logs),
                "recovery_success_rate": round((recovery_success / len(failure_logs)) * 100, 1) if failure_logs else 0,
                "most_common_error": max(error_types.items(), key=lambda x: x[1]) if error_types else ("None", 0)
            }

        return section

    def _generate_recursive_improvement_section(self) -> Dict[str, Any]:
        """Generate recursive improvement section"""
        improvement_report = recursive_improvement.get_improvement_report()

        section = {
            "title": "Recursive Improvement Progress",
            "data": improvement_report
        }

        return section

    def _generate_failure_patterns_section(self) -> Dict[str, Any]:
        """Generate failure patterns analysis section"""
        section = {
            "title": "Failure Pattern Analysis",
            "data": {}
        }

        # Get failure patterns from recursive improvement
        patterns = recursive_improvement.failure_patterns

        pattern_analysis = []
        for signature, data in patterns.items():
            pattern_analysis.append({
                "signature": signature,
                "frequency": data["count"],
                "first_seen": data["first_seen"],
                "last_seen": data["last_seen"],
                "avg_recovery_success": data.get("success_rate", 0),
                "recovery_attempts": len(data.get("recovery_attempts", []))
            })

        # Sort by frequency
        pattern_analysis.sort(key=lambda x: x["frequency"], reverse=True)

        section["data"]["patterns"] = pattern_analysis[:10]  # Top 10 patterns
        section["data"]["summary"] = {
            "total_patterns": len(patterns),
            "most_frequent": pattern_analysis[0] if pattern_analysis else None,
            "avg_recovery_rate": sum(p["avg_recovery_success"] for p in pattern_analysis) / len(pattern_analysis) if pattern_analysis else 0
        }

        return section

    def _generate_adaptation_timeline_section(self) -> Dict[str, Any]:
        """Generate adaptation timeline section"""
        section = {
            "title": "System Adaptation Timeline",
            "data": []
        }

        # Get improvement cycles
        cycles = recursive_improvement.improvement_cycles

        timeline_events = []
        for cycle in cycles[-20:]:  # Last 20 improvement cycles
            timeline_events.append({
                "timestamp": cycle["timestamp"],
                "event_type": "improvement_cycle",
                "description": f"Processed failure: {cycle['failure_data']['error_type']}",
                "recommendations_count": len(cycle["recommendations"]),
                "implemented": cycle.get("implemented", False)
            })

        # Sort by timestamp
        timeline_events.sort(key=lambda x: x["timestamp"])

        section["data"] = timeline_events

        return section

    def _generate_meta_learning_section(self) -> Dict[str, Any]:
        """Generate meta-learning insights section"""
        section = {
            "title": "Meta-Learning Insights",
            "data": {}
        }

        # Get optimal strategies
        optimal_strategies = metrics.get_optimal_strategy("general", list(metrics.agent_metrics.keys()))

        section["data"]["strategy_recommendations"] = optimal_strategies

        # Agent combination insights
        agent_combinations = metrics.agent_combination_success
        if agent_combinations:
            best_combo = max(agent_combinations.items(), key=lambda x: x[1]["avg_success"])
            section["data"]["best_agent_combination"] = {
                "combination": best_combo[0],
                "success_rate": best_combo[1]["avg_success"],
                "usage_count": best_combo[1]["uses"]
            }

        return section

    def _generate_swarm_health_section(self) -> Dict[str, Any]:
        """Generate swarm health section"""
        section = {
            "title": "Swarm Health Overview",
            "data": {}
        }

        # Overall health score calculation
        health_factors = {
            "agent_utilization": 0,
            "error_rate": 0,
            "task_success": 0,
            "memory_efficiency": 0
        }

        # Calculate agent utilization health
        agent_loads = self.dashboard_data.get("agent_loads", {})
        if agent_loads:
            avg_load = sum(agent_loads.values()) / len(agent_loads)
            max_load = self.coordinator.max_agent_load if self.coordinator else 3
            health_factors["agent_utilization"] = min(100, (avg_load / max_load) * 100)

        # Calculate error rate health (lower is better)
        failure_logs = self.dashboard_data.get("failure_logs", [])
        task_metrics = self.dashboard_data.get("task_metrics", [])
        if task_metrics:
            total_tasks = sum(m["subtasks_completed"] + m["total_subtasks"] - m["subtasks_completed"] for m in task_metrics)
            error_rate = len(failure_logs) / total_tasks if total_tasks > 0 else 0
            health_factors["error_rate"] = max(0, 100 - (error_rate * 1000))  # Scale appropriately

        # Calculate task success health
        if task_metrics:
            avg_success = sum(m["success_rate"] for m in task_metrics) / len(task_metrics)
            health_factors["task_success"] = avg_success * 100

        # Calculate memory efficiency health
        memory_entries = len(metrics.memory_store) if hasattr(metrics, 'memory_store') else 0
        max_memory = 100  # Arbitrary limit
        health_factors["memory_efficiency"] = max(0, 100 - (memory_entries / max_memory) * 100)

        # Overall health score
        overall_health = sum(health_factors.values()) / len(health_factors)

        section["data"] = {
            "overall_health_score": round(overall_health, 1),
            "health_factors": {k: round(v, 1) for k, v in health_factors.items()},
            "status": "healthy" if overall_health > 80 else "warning" if overall_health > 60 else "critical"
        }

        return section

    def _generate_task_queues_section(self) -> Dict[str, Any]:
        """Generate task queues status section"""
        section = {
            "title": "Task Queue Status",
            "data": {}
        }

        if self.coordinator:
            active_tasks = self.coordinator.delegation_system.active_tasks
            section["data"]["active_tasks"] = {
                "count": len(active_tasks),
                "tasks": [
                    {
                        "task_id": task_id,
                        "description": task_info["task"].description[:50],
                        "status": task_info["status"],
                        "assigned_agent": task_info["task"].assigned_agent,
                        "assigned_at": task_info["assigned_at"],
                        "priority": task_info.get("priority", 1)
                    }
                    for task_id, task_info in active_tasks.items()
                ]
            }

            # Queue statistics
            priorities = [t.get("priority", 1) for t in active_tasks.values()]
            section["data"]["queue_stats"] = {
                "high_priority": sum(1 for p in priorities if p >= 4),
                "medium_priority": sum(1 for p in priorities if p in [2, 3]),
                "low_priority": sum(1 for p in priorities if p == 1),
                "avg_wait_time": sum(time.time() - t["assigned_at"] for t in active_tasks.values()) / len(active_tasks) if active_tasks else 0
            }

        return section

    def _generate_agent_load_section(self) -> Dict[str, Any]:
        """Generate agent load distribution section"""
        section = {
            "title": "Agent Load Distribution",
            "data": {}
        }

        agent_loads = self.dashboard_data.get("agent_loads", {})
        max_load = self.coordinator.max_agent_load if self.coordinator else 3

        load_distribution = []
        for agent_id, load in agent_loads.items():
            utilization = (load / max_load) * 100
            status = "overloaded" if utilization > 100 else "busy" if utilization > 70 else "normal" if utilization > 30 else "idle"

            load_distribution.append({
                "agent_id": agent_id,
                "current_load": load,
                "max_capacity": max_load,
                "utilization_percent": round(utilization, 1),
                "status": status
            })

        # Sort by utilization
        load_distribution.sort(key=lambda x: x["utilization_percent"], reverse=True)

        section["data"]["load_distribution"] = load_distribution
        section["data"]["summary"] = {
            "total_agents": len(agent_loads),
            "avg_utilization": round(sum(l["utilization_percent"] for l in load_distribution) / len(load_distribution), 1) if load_distribution else 0,
            "overloaded_agents": sum(1 for l in load_distribution if l["status"] == "overloaded"),
            "idle_agents": sum(1 for l in load_distribution if l["status"] == "idle")
        }

        return section

    def _generate_memory_usage_section(self) -> Dict[str, Any]:
        """Generate memory usage section"""
        section = {
            "title": "Memory Usage Analytics",
            "data": {}
        }

        # Working memory
        working_entries = len(metrics.memory_store) if hasattr(metrics, 'memory_store') else 0
        intermediate_entries = len(metrics.intermediate_results) if hasattr(metrics, 'intermediate_results') else 0

        # Long-term memory
        ltm_entries = 0
        if hasattr(metrics, 'episodic_store'):
            ltm_entries += len(metrics.episodic_store)
        if hasattr(metrics, 'semantic_store'):
            ltm_entries += len(metrics.semantic_store)
        if hasattr(metrics, 'tool_use_store'):
            ltm_entries += len(metrics.tool_use_store)
        if hasattr(metrics, 'reflection_store'):
            ltm_entries += len(metrics.reflection_store)

        section["data"] = {
            "working_memory": {
                "total_entries": working_entries,
                "intermediate_results": intermediate_entries,
                "utilization_percent": min(100, (working_entries / 50) * 100)  # Assuming 50 is reasonable max
            },
            "long_term_memory": {
                "total_entries": ltm_entries,
                "utilization_percent": min(100, (ltm_entries / 1000) * 100)  # Assuming 1000 is reasonable max
            },
            "memory_health": "good" if working_entries < 40 and ltm_entries < 800 else "warning" if working_entries < 45 and ltm_entries < 900 else "critical"
        }

        return section

    def _generate_timeline_visualization(self, trace_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate timeline visualization data"""
        timeline = {
            "events": [],
            "time_range": {"start": time.time() - 86400, "end": time.time()}  # Last 24 hours
        }

        # Add reasoning traces to timeline
        for trace in trace_report.get("reasoning_traces", []):
            timeline["events"].append({
                "timestamp": trace["timestamp"],
                "type": "reasoning_trace",
                "agent": trace["agent_id"],
                "task": trace["task_id"],
                "confidence": trace.get("confidence", 0),
                "description": f"Agent {trace['agent_id']} completed reasoning for task {trace['task_id']}"
            })

        # Add decision events
        for entry in trace_report.get("decision_audit_trail", []):
            timeline["events"].append({
                "timestamp": entry.get("timestamp", 0),
                "type": entry.get("type", "unknown"),
                "agent": entry.get("agent_id", "system"),
                "description": f"Decision audit: {entry.get('type', 'unknown')}"
            })

        # Sort events by timestamp
        timeline["events"].sort(key=lambda x: x["timestamp"])

        return timeline

    def _generate_decision_tree_visualization(self, trace_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate decision tree visualization data"""
        decision_tree = {
            "nodes": [],
            "edges": []
        }

        # Build decision tree from reasoning traces
        for trace in trace_report.get("reasoning_traces", []):
            task_id = trace["task_id"]
            agent_id = trace["agent_id"]

            # Add root node (task)
            if not any(n["id"] == task_id for n in decision_tree["nodes"]):
                decision_tree["nodes"].append({
                    "id": task_id,
                    "type": "task",
                    "label": f"Task: {task_id}",
                    "level": 0
                })

            # Add agent node
            agent_node_id = f"{task_id}_agent_{agent_id}"
            decision_tree["nodes"].append({
                "id": agent_node_id,
                "type": "agent",
                "label": f"Agent: {agent_id}",
                "level": 1
            })

            decision_tree["edges"].append({
                "from": task_id,
                "to": agent_node_id,
                "type": "assigned_to"
            })

            # Add reasoning steps
            for i, step in enumerate(trace.get("reasoning_steps", [])):
                step_node_id = f"{task_id}_step_{i}"
                decision_tree["nodes"].append({
                    "id": step_node_id,
                    "type": "reasoning_step",
                    "label": step.get("description", "Unknown")[:30],
                    "level": 2 + i
                })

                # Connect to previous
                if i == 0:
                    decision_tree["edges"].append({
                        "from": agent_node_id,
                        "to": step_node_id,
                        "type": "initiated"
                    })
                else:
                    prev_step_id = f"{task_id}_step_{i-1}"
                    decision_tree["edges"].append({
                        "from": prev_step_id,
                        "to": step_node_id,
                        "type": "reasoned_to"
                    })

            # Add final decision
            final_decision = trace.get("final_decision", "Unknown")
            decision_node_id = f"{task_id}_decision"
            decision_tree["nodes"].append({
                "id": decision_node_id,
                "type": "decision",
                "label": f"Decision: {final_decision[:30]}",
                "level": 3 + len(trace.get("reasoning_steps", []))
            })

            if trace.get("reasoning_steps"):
                last_step_id = f"{task_id}_step_{len(trace['reasoning_steps'])-1}"
                decision_tree["edges"].append({
                    "from": last_step_id,
                    "to": decision_node_id,
                    "type": "produced"
                })

        return decision_tree

    def _generate_tree_of_thought_maps(self, trace_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Tree-of-Thought Maps with graphical trees and color-coded scoring"""
        tree_maps = {
            "maps": [],
            "color_scheme": {
                "high_confidence": "#22c55e",    # Green
                "medium_confidence": "#eab308",  # Yellow
                "low_confidence": "#ef4444",     # Red
                "selected_path": "#3b82f6",      # Blue
                "explored_branch": "#6b7280",    # Gray
                "pruned_branch": "#9ca3af"       # Light gray
            },
            "scoring_metrics": ["confidence", "relevance", "feasibility", "impact"]
        }

        # Process reasoning traces to build tree maps
        for trace in trace_report.get("reasoning_traces", []):
            task_id = trace["task_id"]
            agent_id = trace["agent_id"]

            # Get tree-of-thought data from working memory if available
            tree_data = self._extract_tree_of_thought_data(task_id, agent_id)

            if tree_data:
                tree_map = {
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "root_idea": tree_data.get("root", "Unknown"),
                    "branches": [],
                    "selected_path": [],
                    "branch_limit_applied": tree_data.get("branch_limit_applied", False),
                    "system_load": tree_data.get("system_load", 0),
                    "max_branches_allowed": tree_data.get("max_branches_allowed", 3)
                }

                # Process branches with scoring
                for branch_data in tree_data.get("branches", []):
                    branch = {
                        "path_id": branch_data.get("path", 1),
                        "nodes": branch_data.get("nodes", []),
                        "depth_limit": branch_data.get("depth_limit", 2),
                        "scores": self._calculate_branch_scores(branch_data),
                        "status": "explored",  # Could be "selected", "pruned", etc.
                        "color": self._get_branch_color(branch_data)
                    }
                    tree_map["branches"].append(branch)

                # Determine selected path (highest scoring branch)
                if tree_map["branches"]:
                    best_branch = max(tree_map["branches"], key=lambda b: b["scores"]["overall"])
                    tree_map["selected_path"] = best_branch["nodes"]
                    best_branch["status"] = "selected"

                tree_maps["maps"].append(tree_map)

        return tree_maps

    def _generate_chain_of_thought_traces(self, trace_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Chain-of-Thought Traces with step-by-step logs and highlights"""
        cot_traces = {
            "traces": [],
            "highlight_types": {
                "decision_point": {"color": "#3b82f6", "icon": "decision"},
                "clarification": {"color": "#eab308", "icon": "clarify"},
                "evidence": {"color": "#22c55e", "icon": "evidence"},
                "assumption": {"color": "#f59e0b", "icon": "assume"},
                "conclusion": {"color": "#ef4444", "icon": "conclude"}
            }
        }

        for trace in trace_report.get("reasoning_traces", []):
            cot_trace = {
                "task_id": trace["task_id"],
                "agent_id": trace["agent_id"],
                "timestamp": trace["timestamp"],
                "confidence": trace.get("confidence", 0),
                "step_count": trace.get("step_count", 0),
                "steps": [],
                "highlights": [],
                "final_decision": trace.get("final_decision", "Unknown")
            }

            # Process reasoning steps
            for i, step in enumerate(trace.get("reasoning_steps", [])):
                step_data = {
                    "step_number": i + 1,
                    "description": step.get("description", "Unknown step"),
                    "evidence": step.get("evidence", ""),
                    "conclusion": step.get("conclusion", ""),
                    "timestamp": step.get("timestamp", trace["timestamp"]),
                    "type": self._classify_step_type(step),
                    "confidence": step.get("confidence", trace.get("confidence", 0.5))
                }
                cot_trace["steps"].append(step_data)

                # Add highlights for decision points and clarifications
                highlights = self._extract_step_highlights(step, i + 1)
                cot_trace["highlights"].extend(highlights)

            # Add self-ask guidance highlights if available
            self_ask_data = self._extract_self_ask_highlights(trace)
            if self_ask_data:
                cot_trace["highlights"].extend(self_ask_data)

            cot_traces["traces"].append(cot_trace)

        return cot_traces

    def _generate_reasoning_performance_visualization(self, trace_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate reasoning performance visualization data"""
        performance_data = {
            "confidence_distribution": [],
            "step_efficiency": [],
            "decision_quality": [],
            "reasoning_patterns": []
        }

        for trace in trace_report.get("reasoning_traces", []):
            # Confidence distribution
            performance_data["confidence_distribution"].append({
                "agent": trace["agent_id"],
                "task": trace["task_id"],
                "confidence": trace.get("confidence", 0),
                "step_count": trace.get("step_count", 0)
            })

            # Step efficiency (steps per minute)
            duration = time.time() - trace.get("timestamp", time.time())
            if duration > 0:
                steps_per_minute = (trace.get("step_count", 0) / duration) * 60
                performance_data["step_efficiency"].append({
                    "agent": trace["agent_id"],
                    "task": trace["task_id"],
                    "steps_per_minute": steps_per_minute,
                    "total_steps": trace.get("step_count", 0),
                    "duration_seconds": duration
                })

            # Decision quality (based on audit trail)
            decision_quality = self._assess_decision_quality(trace, trace_report)
            performance_data["decision_quality"].append(decision_quality)

        # Reasoning patterns analysis
        performance_data["reasoning_patterns"] = self._analyze_reasoning_patterns(trace_report)

        return performance_data

    def _extract_tree_of_thought_data(self, task_id: str, agent_id: str) -> Dict[str, Any]:
        """Extract Tree-of-Thought data from memory systems"""
        # Check working memory for tree-of-thought results
        if hasattr(metrics, 'intermediate_results'):
            for key, data in metrics.intermediate_results.items():
                if f"tree_of_thought_{agent_id}" in key and task_id in key:
                    return data

        # Return mock data structure if no real data available
        return {
            "root": f"Task: {task_id}",
            "branches": [
                {
                    "path": 1,
                    "nodes": ["Initial analysis", "Consider options", "Evaluate best approach"],
                    "depth_limit": 2
                },
                {
                    "path": 2,
                    "nodes": ["Quick assessment", "Direct implementation"],
                    "depth_limit": 1
                }
            ],
            "branch_limit_applied": False,
            "system_load": 0.3,
            "max_branches_allowed": 3
        }

    def _calculate_branch_scores(self, branch_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate comprehensive scores for a reasoning branch"""
        nodes = branch_data.get("nodes", [])
        scores = {
            "confidence": 0.5,
            "relevance": 0.5,
            "feasibility": 0.5,
            "impact": 0.5,
            "overall": 0.5
        }

        # Simple scoring based on node content (in real implementation, this would be more sophisticated)
        if nodes:
            # Confidence based on presence of evidence words
            evidence_words = ["because", "therefore", "evidence", "data", "analysis"]
            evidence_count = sum(1 for node in nodes for word in evidence_words if word.lower() in node.lower())
            scores["confidence"] = min(0.9, 0.3 + (evidence_count * 0.1))

            # Relevance based on task-related keywords
            task_keywords = ["task", "goal", "objective", "requirement"]
            relevance_count = sum(1 for node in nodes for word in task_keywords if word.lower() in node.lower())
            scores["relevance"] = min(0.9, 0.4 + (relevance_count * 0.1))

            # Feasibility based on action-oriented language
            action_words = ["implement", "execute", "perform", "create", "build"]
            action_count = sum(1 for node in nodes for word in action_words if word.lower() in node.lower())
            scores["feasibility"] = min(0.9, 0.3 + (action_count * 0.15))

            # Impact based on outcome-focused language
            impact_words = ["result", "outcome", "benefit", "improvement", "solution"]
            impact_count = sum(1 for node in nodes for word in impact_words if word.lower() in node.lower())
            scores["impact"] = min(0.9, 0.3 + (impact_count * 0.15))

            # Overall score as weighted average
            scores["overall"] = (
                scores["confidence"] * 0.3 +
                scores["relevance"] * 0.25 +
                scores["feasibility"] * 0.25 +
                scores["impact"] * 0.2
            )

        return scores

    def _get_branch_color(self, branch_data: Dict[str, Any]) -> str:
        """Get color coding for branch based on scores"""
        scores = self._calculate_branch_scores(branch_data)
        overall_score = scores["overall"]

        if overall_score >= 0.8:
            return "#22c55e"  # High confidence - Green
        elif overall_score >= 0.6:
            return "#eab308"  # Medium confidence - Yellow
        else:
            return "#ef4444"  # Low confidence - Red

    def _classify_step_type(self, step: Dict[str, Any]) -> str:
        """Classify the type of reasoning step"""
        description = step.get("description", "").lower()

        if any(word in description for word in ["decide", "choose", "select", "pick"]):
            return "decision_point"
        elif any(word in description for word in ["clarify", "explain", "understand", "what is"]):
            return "clarification"
        elif any(word in description for word in ["because", "evidence", "data", "shows"]):
            return "evidence"
        elif any(word in description for word in ["assume", "suppose", "if", "given"]):
            return "assumption"
        elif any(word in description for word in ["therefore", "thus", "conclude", "result"]):
            return "conclusion"
        else:
            return "reasoning"

    def _extract_step_highlights(self, step: Dict[str, Any], step_number: int) -> List[Dict[str, Any]]:
        """Extract highlights from a reasoning step"""
        highlights = []
        description = step.get("description", "")

        # Highlight decision points
        if "decide" in description.lower() or "choose" in description.lower():
            highlights.append({
                "type": "decision_point",
                "step": step_number,
                "text": description[:100],
                "color": "#3b82f6"
            })

        # Highlight clarifications
        if "clarify" in description.lower() or "?" in description:
            highlights.append({
                "type": "clarification",
                "step": step_number,
                "text": description[:100],
                "color": "#eab308"
            })

        return highlights

    def _extract_self_ask_highlights(self, trace: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract highlights from self-ask guidance"""
        highlights = []

        # This would extract from actual self-ask data in the trace
        # For now, return mock highlights based on trace data
        if trace.get("confidence", 0) < 0.7:
            highlights.append({
                "type": "low_confidence",
                "step": "overall",
                "text": f"Low confidence in reasoning (confidence: {trace.get('confidence', 0):.2f})",
                "color": "#ef4444"
            })

        return highlights

    def _assess_decision_quality(self, trace: Dict[str, Any], trace_report: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of the final decision"""
        decision_quality = {
            "agent": trace["agent_id"],
            "task": trace["task_id"],
            "confidence_score": trace.get("confidence", 0),
            "reasoning_depth": trace.get("step_count", 0),
            "evidence_strength": 0,
            "alternative_consideration": 0,
            "overall_quality": 0
        }

        # Assess evidence strength
        steps = trace.get("reasoning_steps", [])
        evidence_indicators = ["because", "evidence", "data", "analysis", "therefore"]
        evidence_count = sum(1 for step in steps for indicator in evidence_indicators
                           if indicator in step.get("description", "").lower())
        decision_quality["evidence_strength"] = min(1.0, evidence_count / max(1, len(steps)))

        # Assess alternative consideration (simplified)
        alternative_indicators = ["alternative", "option", "versus", "compare"]
        alternative_count = sum(1 for step in steps for indicator in alternative_indicators
                              if indicator in step.get("description", "").lower())
        decision_quality["alternative_consideration"] = min(1.0, alternative_count / max(1, len(steps)))

        # Calculate overall quality
        decision_quality["overall_quality"] = (
            decision_quality["confidence_score"] * 0.4 +
            decision_quality["evidence_strength"] * 0.3 +
            decision_quality["alternative_consideration"] * 0.3
        )

        return decision_quality

    def _analyze_reasoning_patterns(self, trace_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze patterns in reasoning across traces"""
        patterns = []

        traces = trace_report.get("reasoning_traces", [])
        if not traces:
            return patterns

        # Pattern 1: Average reasoning depth
        avg_depth = sum(trace.get("step_count", 0) for trace in traces) / len(traces)
        patterns.append({
            "pattern": "reasoning_depth",
            "description": f"Average reasoning depth: {avg_depth:.1f} steps",
            "value": avg_depth,
            "trend": "stable"  # Would be calculated based on historical data
        })

        # Pattern 2: Confidence distribution
        confidences = [trace.get("confidence", 0) for trace in traces]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        patterns.append({
            "pattern": "confidence_distribution",
            "description": f"Average confidence: {avg_confidence:.2f}",
            "value": avg_confidence,
            "trend": "stable"
        })

        # Pattern 3: Decision speed vs quality trade-off
        # This would analyze correlation between reasoning time and decision quality

        return patterns

    def _generate_agent_performance_overview(self) -> Dict[str, Any]:
        """Generate comprehensive agent performance overview with recent decisions"""
        agent_metrics = self.dashboard_data.get("agent_metrics", {})

        overview = {
            "total_agents": len(agent_metrics),
            "active_agents": len([m for m in agent_metrics.values() if m["total_tasks"] > 0]),
            "total_tasks_executed": sum(m["total_tasks"] for m in agent_metrics.values()),
            "overall_success_rate": 0,
            "average_reasoning_time": 0,
            "top_performer": None,
            "agents_by_performance": []
        }

        if agent_metrics:
            total_successful = sum(m["successful_tasks"] for m in agent_metrics.values())
            total_tasks = sum(m["total_tasks"] for m in agent_metrics.values())
            total_time = sum(m["total_execution_time"] for m in agent_metrics.values())

            overview["overall_success_rate"] = round((total_successful / total_tasks * 100) if total_tasks > 0 else 0, 1)
            overview["average_reasoning_time"] = round(total_time / total_tasks if total_tasks > 0 else 0, 2)

            # Calculate performance scores and rank agents
            agent_rankings = []
            for agent_id, metrics in agent_metrics.items():
                if metrics["total_tasks"] > 0:
                    success_rate = (metrics["successful_tasks"] / metrics["total_tasks"]) * 100
                    avg_time = metrics["total_execution_time"] / metrics["total_tasks"]
                    efficiency_score = success_rate / (avg_time + 1)  # Avoid division by zero

                    # Get recent decision cards for this agent
                    recent_decisions = self._get_agent_decision_cards(agent_id)

                    agent_rankings.append({
                        "agent_id": agent_id,
                        "success_rate": round(success_rate, 1),
                        "avg_reasoning_time": round(avg_time, 2),
                        "efficiency_score": round(efficiency_score, 2),
                        "total_tasks": metrics["total_tasks"],
                        "quality_score": round(metrics["avg_quality"], 2),
                        "recent_decisions": recent_decisions
                    })

            # Sort by efficiency score
            agent_rankings.sort(key=lambda x: x["efficiency_score"], reverse=True)
            overview["agents_by_performance"] = agent_rankings

            if agent_rankings:
                overview["top_performer"] = agent_rankings[0]

        return overview

    def _generate_task_performance_metrics(self) -> Dict[str, Any]:
        """Generate detailed task performance metrics per agent"""
        agent_metrics = self.dashboard_data.get("agent_metrics", {})

        task_metrics = {
            "agents": {},
            "summary": {
                "total_tasks": 0,
                "successful_tasks": 0,
                "failed_tasks": 0,
                "avg_success_rate": 0,
                "avg_execution_time": 0
            }
        }

        for agent_id, metrics in agent_metrics.items():
            agent_task_data = {
                "task_count": metrics["total_tasks"],
                "successful_tasks": metrics["successful_tasks"],
                "failed_tasks": metrics["total_tasks"] - metrics["successful_tasks"],
                "success_rate": round((metrics["successful_tasks"] / metrics["total_tasks"] * 100) if metrics["total_tasks"] > 0 else 0, 1),
                "avg_execution_time": round(metrics["total_execution_time"] / metrics["total_tasks"] if metrics["total_tasks"] > 0 else 0, 2),
                "total_execution_time": round(metrics["total_execution_time"], 2),
                "quality_score": round(metrics["avg_quality"], 2),
                "task_types_breakdown": metrics.get("task_types", {})
            }

            task_metrics["agents"][agent_id] = agent_task_data

            # Update summary
            task_metrics["summary"]["total_tasks"] += metrics["total_tasks"]
            task_metrics["summary"]["successful_tasks"] += metrics["successful_tasks"]
            task_metrics["summary"]["failed_tasks"] += metrics["total_tasks"] - metrics["successful_tasks"]

        # Calculate summary averages
        if task_metrics["summary"]["total_tasks"] > 0:
            task_metrics["summary"]["avg_success_rate"] = round(
                (task_metrics["summary"]["successful_tasks"] / task_metrics["summary"]["total_tasks"]) * 100, 1
            )

            total_time = sum(metrics["total_execution_time"] for metrics in task_metrics["agents"].values())
            task_metrics["summary"]["avg_execution_time"] = round(
                total_time / task_metrics["summary"]["total_tasks"], 2
            )

        return task_metrics

    def _generate_load_and_resource_metrics(self) -> Dict[str, Any]:
        """Generate load and resource utilization metrics"""
        agent_loads = self.dashboard_data.get("agent_loads", {})
        max_load = self.coordinator.max_agent_load if self.coordinator else 3

        load_metrics = {
            "current_load_distribution": {},
            "branch_usage": {},
            "memory_footprint": {},
            "resource_limits": {
                "max_agent_load": max_load,
                "max_concurrent_branches": 2  # Default, will be updated from working memory
            }
        }

        # Current load distribution
        for agent_id, load in agent_loads.items():
            utilization_percent = (load / max_load) * 100
            status = "overloaded" if utilization_percent > 100 else "busy" if utilization_percent > 70 else "normal" if utilization_percent > 30 else "idle"

            load_metrics["current_load_distribution"][agent_id] = {
                "current_load": load,
                "max_capacity": max_load,
                "utilization_percent": round(utilization_percent, 1),
                "status": status,
                "available_capacity": max(0, max_load - load)
            }

        # Branch usage (if available)
        if hasattr(metrics, 'active_reasoning_branches'):
            total_branches = sum(metrics.active_reasoning_branches.values())
            max_branches = 2  # Default from WorkingMemory
            load_metrics["branch_usage"] = {
                "total_active_branches": total_branches,
                "max_concurrent_branches": max_branches,
                "utilization_percent": round((total_branches / max_branches) * 100, 1),
                "agent_distribution": metrics.active_reasoning_branches.copy()
            }

        # Memory footprint estimation
        for agent_id in agent_loads.keys():
            # Estimate memory usage based on agent activity
            # This is a simplified estimation - in practice would track actual memory usage
            base_memory = 10  # MB baseline
            activity_multiplier = min(agent_loads.get(agent_id, 0) / max_load, 2.0)
            estimated_memory = base_memory * (1 + activity_multiplier)

            load_metrics["memory_footprint"][agent_id] = {
                "estimated_working_memory_mb": round(estimated_memory, 1),
                "intermediate_results_count": len([k for k in metrics.intermediate_results.keys() if agent_id in k]) if hasattr(metrics, 'intermediate_results') else 0,
                "long_term_contributions": len([k for k in (metrics.episodic_store.keys() if hasattr(metrics, 'episodic_store') else []) if agent_id in str(k)]) if hasattr(metrics, 'episodic_store') else 0
            }

        return load_metrics

    def _generate_performance_visualizations(self) -> Dict[str, Any]:
        """Generate visualization data for performance charts and indicators"""
        agent_metrics = self.dashboard_data.get("agent_metrics", {})

        visualizations = {
            "bar_charts": {},
            "circular_progress": {},
            "heatmaps": {},
            "trend_lines": {}
        }

        # Success Rate Bar Chart
        success_rates = {}
        for agent_id, metrics in agent_metrics.items():
            if metrics["total_tasks"] > 0:
                success_rates[agent_id] = round((metrics["successful_tasks"] / metrics["total_tasks"]) * 100, 1)

        visualizations["bar_charts"]["success_rates"] = {
            "title": "Agent Success Rates",
            "data": success_rates,
            "units": "percentage",
            "color_scheme": "green_to_red"
        }

        # Execution Time Bar Chart
        avg_times = {}
        for agent_id, metrics in agent_metrics.items():
            if metrics["total_tasks"] > 0:
                avg_times[agent_id] = round(metrics["total_execution_time"] / metrics["total_tasks"], 2)

        visualizations["bar_charts"]["execution_times"] = {
            "title": "Average Execution Times",
            "data": avg_times,
            "units": "seconds",
            "color_scheme": "blue_scale"
        }

        # Circular Progress Indicators for Load
        agent_loads = self.dashboard_data.get("agent_loads", {})
        max_load = self.coordinator.max_agent_load if self.coordinator else 3

        load_indicators = {}
        for agent_id, load in agent_loads.items():
            utilization = min((load / max_load) * 100, 100)
            load_indicators[agent_id] = {
                "value": round(utilization, 1),
                "max_value": 100,
                "label": f"{load}/{max_load}",
                "color": "#22c55e" if utilization < 70 else "#eab308" if utilization < 90 else "#ef4444"
            }

        visualizations["circular_progress"]["load_indicators"] = {
            "title": "Agent Load Utilization",
            "indicators": load_indicators
        }

        # Task Count Heatmap
        task_counts = {}
        for agent_id, metrics in agent_metrics.items():
            task_counts[agent_id] = metrics["total_tasks"]

        visualizations["heatmaps"]["task_distribution"] = {
            "title": "Task Distribution Heatmap",
            "data": task_counts,
            "color_scale": "viridis",
            "max_value": max(task_counts.values()) if task_counts else 0
        }

        # Performance Trend Lines (simplified - would use historical data)
        trend_data = {}
        for agent_id in agent_metrics.keys():
            # Mock trend data - in practice would use historical metrics
            trend_data[agent_id] = [0.7, 0.75, 0.8, 0.78, 0.82]  # Last 5 performance points

        visualizations["trend_lines"]["performance_trends"] = {
            "title": "Performance Trends (Last 5 Tasks)",
            "data": trend_data,
            "time_labels": ["T-4", "T-3", "T-2", "T-1", "Current"]
        }

        return visualizations

    def _generate_agent_comparison_data(self) -> Dict[str, Any]:
        """Generate comparative analysis data across agents"""
        agent_metrics = self.dashboard_data.get("agent_metrics", {})

        comparison = {
            "performance_ranking": [],
            "strengths_weaknesses": {},
            "specialization_analysis": {},
            "collaboration_potential": {}
        }

        # Performance ranking
        rankings = []
        for agent_id, metrics in agent_metrics.items():
            if metrics["total_tasks"] > 0:
                success_rate = (metrics["successful_tasks"] / metrics["total_tasks"]) * 100
                avg_time = metrics["total_execution_time"] / metrics["total_tasks"]
                efficiency = success_rate / (avg_time + 1)

                rankings.append({
                    "agent_id": agent_id,
                    "rank": 0,  # Will be set after sorting
                    "success_rate": round(success_rate, 1),
                    "avg_time": round(avg_time, 2),
                    "efficiency": round(efficiency, 2),
                    "specialization_score": self._calculate_specialization_score(metrics)
                })

        # Sort and assign ranks
        rankings.sort(key=lambda x: x["efficiency"], reverse=True)
        for i, ranking in enumerate(rankings, 1):
            ranking["rank"] = i

        comparison["performance_ranking"] = rankings

        # Strengths and weaknesses analysis
        for agent_id, metrics in agent_metrics.items():
            if metrics["total_tasks"] > 0:
                success_rate = (metrics["successful_tasks"] / metrics["total_tasks"]) * 100
                avg_time = metrics["total_execution_time"] / metrics["total_tasks"]

                strengths = []
                weaknesses = []

                if success_rate > 80:
                    strengths.append("High reliability")
                elif success_rate < 60:
                    weaknesses.append("Low success rate")

                if avg_time < 1.0:
                    strengths.append("Fast execution")
                elif avg_time > 3.0:
                    weaknesses.append("Slow execution")

                if metrics["avg_quality"] > 0.8:
                    strengths.append("High quality output")
                elif metrics["avg_quality"] < 0.6:
                    weaknesses.append("Low quality output")

                comparison["strengths_weaknesses"][agent_id] = {
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "overall_assessment": "excellent" if len(strengths) > len(weaknesses) else "needs_improvement" if len(weaknesses) > len(strengths) else "balanced"
                }

        # Specialization analysis
        comparison["specialization_analysis"] = self._analyze_agent_specializations(agent_metrics)

        # Collaboration potential (simplified)
        comparison["collaboration_potential"] = self._analyze_collaboration_potential(agent_metrics)

        return comparison

    def _calculate_specialization_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate how specialized an agent is based on task types"""
        task_types = metrics.get("task_types", {})
        if not task_types:
            return 0.0

        # Calculate specialization as the ratio of the most frequent task type to total tasks
        max_task_count = max(task_type["count"] for task_type in task_types.values())
        specialization = max_task_count / metrics["total_tasks"]

        return round(specialization, 2)

    def _analyze_agent_specializations(self, agent_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze specialization patterns across agents"""
        specializations = {}

        for agent_id, metrics in agent_metrics.items():
            task_types = metrics.get("task_types", {})
            if task_types:
                # Find primary specialization
                primary_task = max(task_types.items(), key=lambda x: x[1]["count"])
                specializations[agent_id] = {
                    "primary_specialization": primary_task[0],
                    "primary_task_count": primary_task[1]["count"],
                    "primary_success_rate": primary_task[1]["success"],
                    "specialization_score": self._calculate_specialization_score(metrics),
                    "task_diversity": len(task_types)
                }

        return specializations

    def _analyze_collaboration_potential(self, agent_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze potential for agent collaboration"""
        collaboration = {
            "complementary_pairs": [],
            "collaboration_opportunities": []
        }

        agent_ids = list(agent_metrics.keys())

        # Simple complementary analysis based on task types
        for i, agent1 in enumerate(agent_ids):
            for agent2 in agent_ids[i+1:]:
                metrics1 = agent_metrics[agent1]
                metrics2 = agent_metrics[agent2]

                task_types1 = set(metrics1.get("task_types", {}).keys())
                task_types2 = set(metrics2.get("task_types", {}).keys())

                # Check for complementary skills (different task types)
                if task_types1 and task_types2 and task_types1.isdisjoint(task_types2):
                    collaboration["complementary_pairs"].append({
                        "agent1": agent1,
                        "agent2": agent2,
                        "complementary_tasks": list(task_types1.symmetric_difference(task_types2)),
                        "collaboration_potential": "high"
                    })

        return collaboration

    def get_memory_analytics_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive memory analytics dashboard"""
        dashboard = {
            "dashboard_type": "memory_analytics",
            "generated_at": time.time(),
            "sections": {}
        }

        # STM/LTM Status Section
        dashboard["sections"]["stm_ltm_status"] = {
            "title": "STM/LTM Memory Status",
            "description": "Current state of short-term and long-term memory systems",
            "data": self._generate_stm_ltm_status()
        }

        # Semantic Memory Coverage Section
        dashboard["sections"]["semantic_memory_coverage"] = {
            "title": "Semantic Memory Coverage",
            "description": "Knowledge domains and concepts stored in semantic memory",
            "data": self._generate_semantic_memory_coverage()
        }

        # Episodic Memory Heatmap Section
        dashboard["sections"]["episodic_memory_heatmap"] = {
            "title": "Episodic Memory Heatmap",
            "description": "Frequency and recency of past tasks and experiences",
            "data": self._generate_episodic_memory_heatmap()
        }

        # Memory Health and Performance Section
        dashboard["sections"]["memory_health"] = {
            "title": "Memory Health & Performance",
            "description": "Memory system performance metrics and health indicators",
            "data": self._generate_memory_health_metrics()
        }

        return dashboard

    def get_failure_recovery_insights_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive failure and recovery insights dashboard"""
        dashboard = {
            "dashboard_type": "failure_recovery_insights",
            "generated_at": time.time(),
            "sections": {}
        }

        # Failure Patterns Section
        dashboard["sections"]["failure_patterns"] = {
            "title": "Failure Patterns Analysis",
            "description": "Number of retries per task type and failure causes",
            "data": self._generate_failure_patterns_analysis()
        }

        # Recovery Strategies Section
        dashboard["sections"]["recovery_strategies"] = {
            "title": "Recovery Strategies Effectiveness",
            "description": "Analysis of which retry methods succeeded (backoff, subdivision, simplification)",
            "data": self._generate_recovery_strategies_analysis()
        }

        # Recursive Improvement Impact Section
        dashboard["sections"]["recursive_improvement_impact"] = {
            "title": "Recursive Improvement Impact",
            "description": "Visualization of learning over time (error rate reduction per task type)",
            "data": self._generate_recursive_improvement_impact()
        }

        return dashboard

    def get_task_operational_overview_dashboard(self, task_id: str = None) -> Dict[str, Any]:
        """Generate comprehensive task and operational overview dashboard"""
        dashboard = {
            "dashboard_type": "task_operational_overview",
            "generated_at": time.time(),
            "sections": {},
            "filters": {"task_id": task_id}
        }

        # Task Queue Visualization Section
        dashboard["sections"]["task_queue_visualization"] = {
            "title": "Task Queue Visualization",
            "description": "Pending, in-progress, and completed subtasks per swarm run",
            "data": self._generate_task_queue_visualization(task_id)
        }

        # Subtask Dependencies Section
        dashboard["sections"]["subtask_dependencies"] = {
            "title": "Subtask Dependencies Graph",
            "description": "Graph showing hierarchical relationships and completion status",
            "data": self._generate_subtask_dependencies_graph(task_id)
        }

        # Execution Timeline Section
        dashboard["sections"]["execution_timeline"] = {
            "title": "Execution Timeline",
            "description": "Chronological visualization of multi-agent execution with checkpoints",
            "data": self._generate_execution_timeline(task_id)
        }

        return dashboard

    def _generate_task_queue_visualization(self, task_id: str = None) -> Dict[str, Any]:
        """Generate task queue visualization with pending, in-progress, and completed subtasks"""
        task_queue_data = {
            "queue_status": {
                "pending": [],
                "in_progress": [],
                "completed": []
            },
            "queue_summary": {
                "total_pending": 0,
                "total_in_progress": 0,
                "total_completed": 0,
                "completion_rate": 0
            },
            "task_distribution": {},
            "priority_breakdown": {},
            "agent_workload": {}
        }

        if not self.coordinator:
            return task_queue_data

        # Get active tasks from coordinator
        active_tasks = self.coordinator.delegation_system.active_tasks

        # Get execution state for specific task if provided
        execution_state = None
        if task_id and hasattr(self.coordinator, 'working_memory') and self.coordinator.working_memory:
            execution_state = self.coordinator.working_memory.retrieve(f"execution_state_{task_id}")

        # Categorize tasks
        for task_key, task_info in active_tasks.items():
            task_data = {
                "task_id": task_key,
                "description": task_info["task"].description[:100],
                "assigned_agent": task_info["task"].assigned_agent,
                "priority": task_info.get("priority", 1),
                "assigned_at": task_info["assigned_at"],
                "status": task_info["status"],
                "level": task_info.get("level", 0)
            }

            if task_info["status"] == "assigned":
                task_queue_data["queue_status"]["in_progress"].append(task_data)
            elif task_info["status"] == "completed":
                task_queue_data["queue_status"]["completed"].append(task_data)
            else:
                task_queue_data["queue_status"]["pending"].append(task_data)

        # Add pending subtasks from execution state if available
        if execution_state:
            for pending_subtask in execution_state.get("pending_subtasks", []):
                if pending_subtask["type"] == "single_subtask":
                    task_data = {
                        "task_id": f"{execution_state['task_id']}_pending_{len(task_queue_data['queue_status']['pending'])}",
                        "description": pending_subtask["subtask"]["description"][:100],
                        "assigned_agent": None,
                        "priority": pending_subtask["subtask"].get("priority", 1),
                        "assigned_at": None,
                        "status": "pending",
                        "level": 0
                    }
                    task_queue_data["queue_status"]["pending"].append(task_data)

        # Calculate summary statistics
        task_queue_data["queue_summary"]["total_pending"] = len(task_queue_data["queue_status"]["pending"])
        task_queue_data["queue_summary"]["total_in_progress"] = len(task_queue_data["queue_status"]["in_progress"])
        task_queue_data["queue_summary"]["total_completed"] = len(task_queue_data["queue_status"]["completed"])

        total_tasks = (task_queue_data["queue_summary"]["total_pending"] +
                      task_queue_data["queue_summary"]["total_in_progress"] +
                      task_queue_data["queue_summary"]["total_completed"])

        if total_tasks > 0:
            task_queue_data["queue_summary"]["completion_rate"] = round(
                (task_queue_data["queue_summary"]["total_completed"] / total_tasks) * 100, 1
            )

        # Task distribution by agent
        for status_category in ["pending", "in_progress", "completed"]:
            for task in task_queue_data["queue_status"][status_category]:
                agent = task.get("assigned_agent", "unassigned")
                if agent not in task_queue_data["task_distribution"]:
                    task_queue_data["task_distribution"][agent] = {"pending": 0, "in_progress": 0, "completed": 0}
                task_queue_data["task_distribution"][agent][status_category] += 1

        # Priority breakdown
        for status_category in ["pending", "in_progress", "completed"]:
            for task in task_queue_data["queue_status"][status_category]:
                priority = task.get("priority", 1)
                priority_key = f"priority_{priority}"
                if priority_key not in task_queue_data["priority_breakdown"]:
                    task_queue_data["priority_breakdown"][priority_key] = {"pending": 0, "in_progress": 0, "completed": 0}
                task_queue_data["priority_breakdown"][priority_key][status_category] += 1

        # Agent workload from coordinator
        if hasattr(self.coordinator, 'agent_loads'):
            task_queue_data["agent_workload"] = self.coordinator.agent_loads.copy()

        return task_queue_data

    def _generate_subtask_dependencies_graph(self, task_id: str = None) -> Dict[str, Any]:
        """Generate subtask dependencies graph showing hierarchical relationships"""
        dependencies_graph = {
            "nodes": [],
            "edges": [],
            "node_types": ["task", "subtask", "cluster", "checkpoint"],
            "edge_types": ["depends_on", "parent_child", "checkpoint_link"],
            "graph_metadata": {
                "total_nodes": 0,
                "total_edges": 0,
                "max_depth": 0,
                "completion_percentage": 0
            }
        }

        if not self.coordinator or not task_id:
            return dependencies_graph

        # Get strategy and execution state
        strategy = None
        execution_state = None

        if hasattr(self.coordinator, 'working_memory') and self.coordinator.working_memory:
            strategy = self.coordinator.working_memory.retrieve(f"strategy_{task_id}")
            execution_state = self.coordinator.working_memory.retrieve(f"execution_state_{task_id}")

        if not strategy:
            return dependencies_graph

        # Build nodes from strategy subtasks
        node_id_counter = 0
        task_nodes = {}

        # Root task node
        root_node = {
            "id": f"task_{node_id_counter}",
            "label": strategy.get("task", "Main Task")[:50],
            "type": "task",
            "status": "completed" if execution_state and execution_state.get("status") == "completed" else "in_progress",
            "level": 0,
            "priority": 5,
            "agent": None,
            "start_time": execution_state.get("start_time") if execution_state else None,
            "end_time": execution_state.get("completed_at") if execution_state and execution_state.get("status") == "completed" else None
        }
        dependencies_graph["nodes"].append(root_node)
        task_nodes["root"] = root_node
        node_id_counter += 1

        # Process task clusters
        for cluster in strategy.get("task_clusters", []):
            if cluster.get("requires_mini_coordinator"):
                # Mini-coordinator cluster node
                cluster_node = {
                    "id": f"cluster_{node_id_counter}",
                    "label": f"Cluster: {cluster['cluster_id']}",
                    "type": "cluster",
                    "status": "in_progress",
                    "level": 1,
                    "priority": cluster.get("complexity", 1),
                    "agent": "MiniCoordinator",
                    "subtasks_count": len(cluster.get("subtasks", []))
                }
                dependencies_graph["nodes"].append(cluster_node)

                # Connect to root
                dependencies_graph["edges"].append({
                    "from": root_node["id"],
                    "to": cluster_node["id"],
                    "type": "parent_child",
                    "label": "contains"
                })

                # Add cluster subtasks
                for subtask in cluster.get("subtasks", []):
                    subtask_node = {
                        "id": f"subtask_{node_id_counter}",
                        "label": subtask["description"][:50],
                        "type": "subtask",
                        "status": "pending",
                        "level": 2,
                        "priority": subtask.get("priority", 1),
                        "agent": None
                    }
                    dependencies_graph["nodes"].append(subtask_node)
                    node_id_counter += 1

                    # Connect to cluster
                    dependencies_graph["edges"].append({
                        "from": cluster_node["id"],
                        "to": subtask_node["id"],
                        "type": "parent_child",
                        "label": "contains"
                    })
            else:
                # Individual subtasks
                for subtask in cluster.get("subtasks", []):
                    subtask_node = {
                        "id": f"subtask_{node_id_counter}",
                        "label": subtask["description"][:50],
                        "type": "subtask",
                        "status": "pending",
                        "level": 1,
                        "priority": subtask.get("priority", 1),
                        "agent": None
                    }
                    dependencies_graph["nodes"].append(subtask_node)

                    # Connect to root
                    dependencies_graph["edges"].append({
                        "from": root_node["id"],
                        "to": subtask_node["id"],
                        "type": "parent_child",
                        "label": "contains"
                    })

                    node_id_counter += 1

        # Update node status based on execution state
        if execution_state:
            completed_subtasks = execution_state.get("completed_subtasks", [])
            for completed in completed_subtasks:
                # Find matching node and update status
                for node in dependencies_graph["nodes"]:
                    if node["type"] == "subtask" and completed["subtask_id"] in node["label"]:
                        node["status"] = "completed"
                        node["end_time"] = completed.get("completed_at")

        # Add checkpoint nodes and edges
        if execution_state:
            checkpoints = execution_state.get("completed_subtasks", [])
            for i, checkpoint in enumerate(checkpoints):
                checkpoint_node = {
                    "id": f"checkpoint_{i}",
                    "label": f"Checkpoint {checkpoint['checkpoint']}",
                    "type": "checkpoint",
                    "status": "completed",
                    "level": 3,
                    "timestamp": checkpoint.get("completed_at"),
                    "result_summary": str(checkpoint.get("result", ""))[:50]
                }
                dependencies_graph["nodes"].append(checkpoint_node)

                # Link checkpoint to corresponding subtask
                checkpoint_subtask_id = checkpoint.get("subtask_id", "")
                for node in dependencies_graph["nodes"]:
                    if node["type"] == "subtask" and checkpoint_subtask_id in node.get("label", ""):
                        dependencies_graph["edges"].append({
                            "from": node["id"],
                            "to": checkpoint_node["id"],
                            "type": "checkpoint_link",
                            "label": "checkpoint"
                        })
                        break

        # Calculate graph metadata
        dependencies_graph["graph_metadata"]["total_nodes"] = len(dependencies_graph["nodes"])
        dependencies_graph["graph_metadata"]["total_edges"] = len(dependencies_graph["edges"])
        dependencies_graph["graph_metadata"]["max_depth"] = max((node["level"] for node in dependencies_graph["nodes"]), default=0)

        # Calculate completion percentage
        completed_nodes = sum(1 for node in dependencies_graph["nodes"] if node.get("status") == "completed")
        if dependencies_graph["graph_metadata"]["total_nodes"] > 0:
            dependencies_graph["graph_metadata"]["completion_percentage"] = round(
                (completed_nodes / dependencies_graph["graph_metadata"]["total_nodes"]) * 100, 1
            )

        return dependencies_graph

    def _generate_execution_timeline(self, task_id: str = None) -> Dict[str, Any]:
        """Generate execution timeline with chronological multi-agent execution and checkpoints"""
        timeline_data = {
            "events": [],
            "time_range": {"start": None, "end": None},
            "agent_timelines": {},
            "checkpoint_timeline": [],
            "timeline_summary": {
                "total_events": 0,
                "duration_seconds": 0,
                "agents_involved": [],
                "checkpoints_reached": 0
            }
        }

        if not self.coordinator or not task_id:
            return timeline_data

        # Get execution state and checkpoints
        execution_state = None
        checkpoints = []

        if hasattr(self.coordinator, 'working_memory') and self.coordinator.working_memory:
            execution_state = self.coordinator.working_memory.retrieve(f"execution_state_{task_id}")

            # Collect all checkpoints
            for key in self.coordinator.working_memory.memory_store.keys():
                if key.startswith(f"checkpoint_{task_id}_"):
                    checkpoint_data = self.coordinator.working_memory.retrieve(key)
                    if checkpoint_data:
                        checkpoints.append(checkpoint_data)

        if not execution_state:
            return timeline_data

        # Sort checkpoints by timestamp
        checkpoints.sort(key=lambda x: x.get("timestamp", 0))

        # Build timeline events
        events = []

        # Task start event
        task_start_time = getattr(self.coordinator, f"_task_start_{task_id}", time.time())
        events.append({
            "timestamp": task_start_time,
            "event_type": "task_start",
            "description": f"Task '{execution_state['strategy']['task'][:50]}' started",
            "agent": "Coordinator",
            "details": {"task_id": task_id, "strategy": execution_state["strategy"]["task_type"]}
        })

        # Subtask assignment events
        for pending_subtask in execution_state.get("pending_subtasks", []):
            if pending_subtask["type"] == "single_subtask":
                # Find when this subtask was assigned
                subtask_desc = pending_subtask["subtask"]["description"]
                assigned_time = None

                # Check active tasks for assignment time
                for task_key, task_info in self.coordinator.delegation_system.active_tasks.items():
                    if task_info["task"].description == subtask_desc:
                        assigned_time = task_info["assigned_at"]
                        break

                if assigned_time:
                    events.append({
                        "timestamp": assigned_time,
                        "event_type": "subtask_assigned",
                        "description": f"Subtask assigned: {subtask_desc[:50]}",
                        "agent": "Coordinator",
                        "details": {
                            "subtask_id": f"{task_id}_assigned",
                            "assigned_agent": None,  # Would need to track this
                            "priority": pending_subtask["subtask"].get("priority", 1)
                        }
                    })

        # Checkpoint events
        for checkpoint in checkpoints:
            events.append({
                "timestamp": checkpoint["timestamp"],
                "event_type": "checkpoint_reached",
                "description": f"Checkpoint {checkpoint['execution_state']['current_checkpoint']} completed",
                "agent": checkpoint.get("execution_state", {}).get("current_agent", "System"),
                "details": {
                    "checkpoint_number": checkpoint["execution_state"]["current_checkpoint"],
                    "subtask_id": checkpoint["subtask_id"],
                    "result_summary": str(checkpoint["result"])[:100]
                }
            })

        # Task completion event
        if execution_state.get("status") == "completed":
            events.append({
                "timestamp": execution_state.get("completed_at", time.time()),
                "event_type": "task_completed",
                "description": f"Task '{execution_state['strategy']['task'][:50]}' completed",
                "agent": "Coordinator",
                "details": {
                    "final_result": str(execution_state.get("final_result", ""))[:100],
                    "total_checkpoints": len(checkpoints)
                }
            })

        # Sort events by timestamp
        events.sort(key=lambda x: x["timestamp"])

        # Set time range
        if events:
            timeline_data["time_range"]["start"] = events[0]["timestamp"]
            timeline_data["time_range"]["end"] = events[-1]["timestamp"]
            timeline_data["timeline_summary"]["duration_seconds"] = round(
                timeline_data["time_range"]["end"] - timeline_data["time_range"]["start"], 2
            )

        timeline_data["events"] = events

        # Build agent-specific timelines
        agent_timelines = {}
        for event in events:
            agent = event.get("agent", "Unknown")
            if agent not in agent_timelines:
                agent_timelines[agent] = []
            agent_timelines[agent].append(event)

        timeline_data["agent_timelines"] = agent_timelines
        timeline_data["timeline_summary"]["agents_involved"] = list(agent_timelines.keys())
        timeline_data["timeline_summary"]["total_events"] = len(events)
        timeline_data["timeline_summary"]["checkpoints_reached"] = len(checkpoints)

        # Extract checkpoint timeline
        timeline_data["checkpoint_timeline"] = [
            {
                "checkpoint": cp["execution_state"]["current_checkpoint"],
                "timestamp": cp["timestamp"],
                "description": f"Completed subtask: {cp['subtask_id']}",
                "duration_from_start": round(cp["timestamp"] - task_start_time, 2) if task_start_time else 0
            }
            for cp in checkpoints
        ]

        return timeline_data

    def _generate_failure_patterns_analysis(self) -> Dict[str, Any]:
        """Generate failure patterns analysis with retries per task type and failure causes"""
        from .recursive_improvement import recursive_improvement

        failure_analysis = {
            "total_failures": len(recursive_improvement.failure_patterns),
            "retries_by_task_type": {},
            "failure_causes_distribution": {},
            "most_problematic_tasks": [],
            "retry_success_rates": {},
            "temporal_failure_trends": []
        }

        # Analyze failure patterns
        for signature, pattern_data in recursive_improvement.failure_patterns.items():
            # Parse signature to extract task type and error type
            parts = signature.split("|")
            if len(parts) >= 2:
                error_type = parts[0]
                task_type = parts[1]

                # Count retries by task type
                if task_type not in failure_analysis["retries_by_task_type"]:
                    failure_analysis["retries_by_task_type"][task_type] = 0
                failure_analysis["retries_by_task_type"][task_type] += pattern_data["count"]

                # Count failure causes
                if error_type not in failure_analysis["failure_causes_distribution"]:
                    failure_analysis["failure_causes_distribution"][error_type] = 0
                failure_analysis["failure_causes_distribution"][error_type] += pattern_data["count"]

                # Calculate retry success rate
                recovery_attempts = pattern_data.get("recovery_attempts", [])
                if recovery_attempts:
                    successful_recoveries = sum(1 for r in recovery_attempts if r.get("successful", False))
                    success_rate = successful_recoveries / len(recovery_attempts)
                    failure_analysis["retry_success_rates"][f"{task_type}_{error_type}"] = round(success_rate * 100, 1)

        # Identify most problematic tasks
        if failure_analysis["retries_by_task_type"]:
            sorted_tasks = sorted(
                failure_analysis["retries_by_task_type"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            failure_analysis["most_problematic_tasks"] = [
                {"task_type": task, "failure_count": count, "severity": "high" if count > 10 else "medium" if count > 5 else "low"}
                for task, count in sorted_tasks[:5]
            ]

        # Generate temporal trends (simplified - would need more detailed failure logs)
        failure_analysis["temporal_failure_trends"] = self._generate_failure_temporal_trends()

        return failure_analysis

    def _generate_recovery_strategies_analysis(self) -> Dict[str, Any]:
        """Generate recovery strategies analysis showing which retry methods succeeded"""
        from .recursive_improvement import recursive_improvement

        recovery_analysis = {
            "strategy_effectiveness": {},
            "backoff_success_rate": 0,
            "subdivision_success_rate": 0,
            "simplification_success_rate": 0,
            "strategy_usage_distribution": {},
            "best_strategies_by_error_type": {},
            "recovery_time_analysis": {}
        }

        # Analyze recovery attempts across all failure patterns
        strategy_counts = {"backoff": 0, "subdivision": 0, "simplification": 0}
        strategy_successes = {"backoff": 0, "subdivision": 0, "simplification": 0}

        for signature, pattern_data in recursive_improvement.failure_patterns.items():
            recovery_attempts = pattern_data.get("recovery_attempts", [])

            for attempt in recovery_attempts:
                strategy = attempt.get("strategy", "unknown")
                successful = attempt.get("successful", False)

                # Map strategy names to standard categories
                if "backoff" in strategy.lower() or "retry" in strategy.lower():
                    strategy = "backoff"
                elif "subdivision" in strategy.lower() or "split" in strategy.lower():
                    strategy = "subdivision"
                elif "simplification" in strategy.lower() or "simplify" in strategy.lower():
                    strategy = "simplification"

                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
                if successful:
                    strategy_successes[strategy] = strategy_successes.get(strategy, 0) + 1

        # Calculate success rates
        for strategy in ["backoff", "subdivision", "simplification"]:
            total_attempts = strategy_counts.get(strategy, 0)
            successful_attempts = strategy_successes.get(strategy, 0)

            if total_attempts > 0:
                success_rate = successful_attempts / total_attempts
                recovery_analysis["strategy_effectiveness"][strategy] = {
                    "success_rate": round(success_rate * 100, 1),
                    "total_attempts": total_attempts,
                    "successful_attempts": successful_attempts
                }

                # Set specific success rates
                if strategy == "backoff":
                    recovery_analysis["backoff_success_rate"] = round(success_rate * 100, 1)
                elif strategy == "subdivision":
                    recovery_analysis["subdivision_success_rate"] = round(success_rate * 100, 1)
                elif strategy == "simplification":
                    recovery_analysis["simplification_success_rate"] = round(success_rate * 100, 1)

        recovery_analysis["strategy_usage_distribution"] = strategy_counts

        # Analyze best strategies by error type
        recovery_analysis["best_strategies_by_error_type"] = self._analyze_best_strategies_by_error_type()

        return recovery_analysis

    def _generate_recursive_improvement_impact(self) -> Dict[str, Any]:
        """Generate recursive improvement impact visualization showing learning over time"""
        from .recursive_improvement import recursive_improvement

        improvement_impact = {
            "error_rate_reduction_over_time": [],
            "task_type_improvements": {},
            "learning_curve_data": [],
            "improvement_velocity": {},
            "predictive_accuracy_trends": []
        }

        # Analyze improvement cycles for error rate reduction
        improvement_cycles = recursive_improvement.improvement_cycles

        if improvement_cycles:
            # Group by task type and track error rates over time
            task_improvements = {}

            for cycle in improvement_cycles:
                failure_data = cycle.get("failure_data", {})
                task_type = failure_data.get("task_type", "unknown")

                if task_type not in task_improvements:
                    task_improvements[task_type] = []

                task_improvements[task_type].append({
                    "timestamp": cycle["timestamp"],
                    "error_type": failure_data.get("error_type", "unknown"),
                    "recommendations_count": len(cycle.get("recommendations", [])),
                    "implemented": cycle.get("implemented", False)
                })

            # Calculate improvement metrics for each task type
            for task_type, cycles in task_improvements.items():
                if len(cycles) > 1:
                    # Sort by timestamp
                    cycles.sort(key=lambda x: x["timestamp"])

                    # Calculate error rate reduction (simplified)
                    initial_failures = len([c for c in cycles[:len(cycles)//2]])
                    later_failures = len([c for c in cycles[len(cycles)//2:]])

                    if initial_failures > 0:
                        reduction_rate = ((initial_failures - later_failures) / initial_failures) * 100
                        improvement_impact["task_type_improvements"][task_type] = {
                            "error_rate_reduction": round(reduction_rate, 1),
                            "total_cycles": len(cycles),
                            "implemented_recommendations": sum(1 for c in cycles if c["implemented"]),
                            "learning_trend": "improving" if reduction_rate > 0 else "stable"
                        }

            # Generate learning curve data
            improvement_impact["learning_curve_data"] = self._generate_learning_curve_data(improvement_cycles)

            # Calculate improvement velocity
            if len(improvement_cycles) > 1:
                time_span = improvement_cycles[-1]["timestamp"] - improvement_cycles[0]["timestamp"]
                total_improvements = sum(len(c.get("recommendations", [])) for c in improvement_cycles)

                if time_span > 0:
                    improvement_impact["improvement_velocity"] = {
                        "recommendations_per_day": round(total_improvements / (time_span / 86400), 2),
                        "cycles_per_day": round(len(improvement_cycles) / (time_span / 86400), 2),
                        "learning_acceleration": "accelerating" if len(improvement_cycles) > 5 else "stable"
                    }

        return improvement_impact

    def _generate_failure_temporal_trends(self) -> List[Dict[str, Any]]:
        """Generate temporal failure trends data"""
        # This would analyze failure logs over time periods
        # For now, return mock data structure
        return [
            {"period": "last_24h", "total_failures": 5, "trend": "stable"},
            {"period": "last_7d", "total_failures": 23, "trend": "decreasing"},
            {"period": "last_30d", "total_failures": 89, "trend": "improving"}
        ]

    def _analyze_best_strategies_by_error_type(self) -> Dict[str, Any]:
        """Analyze which recovery strategies work best for different error types"""
        from .recursive_improvement import recursive_improvement

        best_strategies = {}

        for signature, pattern_data in recursive_improvement.failure_patterns.items():
            parts = signature.split("|")
            if len(parts) >= 1:
                error_type = parts[0]
                recovery_attempts = pattern_data.get("recovery_attempts", [])

                if recovery_attempts:
                    # Find most successful strategy for this error type
                    strategy_success = {}
                    for attempt in recovery_attempts:
                        strategy = attempt.get("strategy", "unknown")
                        if strategy not in strategy_success:
                            strategy_success[strategy] = {"attempts": 0, "successes": 0}

                        strategy_success[strategy]["attempts"] += 1
                        if attempt.get("successful", False):
                            strategy_success[strategy]["successes"] += 1

                    # Find best strategy
                    best_strategy = max(strategy_success.items(),
                                      key=lambda x: x[1]["successes"] / x[1]["attempts"] if x[1]["attempts"] > 0 else 0)

                    success_rate = best_strategy[1]["successes"] / best_strategy[1]["attempts"] if best_strategy[1]["attempts"] > 0 else 0

                    best_strategies[error_type] = {
                        "best_strategy": best_strategy[0],
                        "success_rate": round(success_rate * 100, 1),
                        "total_attempts": best_strategy[1]["attempts"]
                    }

        return best_strategies

    def _generate_learning_curve_data(self, improvement_cycles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate learning curve data showing improvement over time"""
        learning_curve = []

        if not improvement_cycles:
            return learning_curve

        # Sort cycles by timestamp
        sorted_cycles = sorted(improvement_cycles, key=lambda x: x["timestamp"])

        # Group by time periods (e.g., weekly)
        week_start = sorted_cycles[0]["timestamp"]
        current_week = 0
        weekly_data = {}

        for cycle in sorted_cycles:
            weeks_elapsed = int((cycle["timestamp"] - week_start) / (7 * 24 * 3600))

            if weeks_elapsed not in weekly_data:
                weekly_data[weeks_elapsed] = {
                    "week": weeks_elapsed,
                    "failures": 0,
                    "recommendations": 0,
                    "implemented": 0
                }

            weekly_data[weeks_elapsed]["failures"] += 1
            weekly_data[weeks_elapsed]["recommendations"] += len(cycle.get("recommendations", []))
            if cycle.get("implemented", False):
                weekly_data[weeks_elapsed]["implemented"] += 1

        # Convert to list and calculate improvement metrics
        for week_data in weekly_data.values():
            learning_curve.append({
                "week": week_data["week"],
                "failures": week_data["failures"],
                "recommendations_generated": week_data["recommendations"],
                "recommendations_implemented": week_data["implemented"],
                "implementation_rate": round((week_data["implemented"] / week_data["recommendations"]) * 100, 1) if week_data["recommendations"] > 0 else 0
            })

        return learning_curve

    def _generate_stm_ltm_status(self) -> Dict[str, Any]:
        """Generate STM/LTM memory status with entry counts, age distribution, and pruning metrics"""
        stm_status = {
            "total_entries": 0,
            "age_distribution": {},
            "pruned_items": 0,
            "utilization_percent": 0,
            "memory_health": "good"
        }

        ltm_status = {
            "episodic_entries": 0,
            "semantic_entries": 0,
            "tool_use_entries": 0,
            "reflection_entries": 0,
            "total_entries": 0,
            "age_distribution": {},
            "utilization_percent": 0,
            "memory_health": "good"
        }

        current_time = time.time()

        # STM Analysis (Working Memory)
        if hasattr(metrics, 'memory_store'):
            stm_entries = metrics.memory_store
            stm_status["total_entries"] = len(stm_entries)

            # Age distribution for STM
            age_bins = {"< 1h": 0, "1-6h": 0, "6-24h": 0, "1-7d": 0, "> 7d": 0}
            for entry in stm_entries.values():
                timestamp = entry.get("timestamp", current_time)
                age_hours = (current_time - timestamp) / 3600

                if age_hours < 1:
                    age_bins["< 1h"] += 1
                elif age_hours < 6:
                    age_bins["1-6h"] += 1
                elif age_hours < 24:
                    age_bins["6-24h"] += 1
                elif age_hours < 168:  # 7 days
                    age_bins["1-7d"] += 1
                else:
                    age_bins["> 7d"] += 1

            stm_status["age_distribution"] = age_bins

            # Utilization and health
            max_stm_entries = 50  # Configurable limit
            stm_status["utilization_percent"] = min(100, (len(stm_entries) / max_stm_entries) * 100)
            stm_status["memory_health"] = "good" if len(stm_entries) < 40 else "warning" if len(stm_entries) < 45 else "critical"

        # Intermediate results pruning info
        if hasattr(metrics, 'intermediate_results'):
            # Estimate pruned items (this would be tracked in a real implementation)
            stm_status["pruned_items"] = max(0, len(metrics.intermediate_results) - 10)  # Assuming 10 is the limit

        # LTM Analysis
        if hasattr(metrics, 'episodic_store'):
            episodic = metrics.episodic_store
            ltm_status["episodic_entries"] = len(episodic)

            # Age distribution for episodic memory
            episodic_age_bins = {"< 1d": 0, "1-7d": 0, "1-30d": 0, "1-90d": 0, "> 90d": 0}
            for entry in episodic.values():
                timestamp = entry.get("timestamp", current_time)
                age_days = (current_time - timestamp) / 86400

                if age_days < 1:
                    episodic_age_bins["< 1d"] += 1
                elif age_days < 7:
                    episodic_age_bins["1-7d"] += 1
                elif age_days < 30:
                    episodic_age_bins["1-30d"] += 1
                elif age_days < 90:
                    episodic_age_bins["1-90d"] += 1
                else:
                    episodic_age_bins["> 90d"] += 1

            ltm_status["age_distribution"]["episodic"] = episodic_age_bins

        if hasattr(metrics, 'semantic_store'):
            semantic = metrics.semantic_store
            ltm_status["semantic_entries"] = len(semantic)

        if hasattr(metrics, 'tool_use_store'):
            tool_use = metrics.tool_use_store
            ltm_status["tool_use_entries"] = len(tool_use)

        if hasattr(metrics, 'reflection_store'):
            reflection = metrics.reflection_store
            ltm_status["reflection_entries"] = len(reflection)

        # Total LTM entries
        ltm_status["total_entries"] = (
            ltm_status["episodic_entries"] +
            ltm_status["semantic_entries"] +
            ltm_status["tool_use_entries"] +
            ltm_status["reflection_entries"]
        )

        # LTM utilization and health
        max_ltm_entries = 1000  # Configurable limit
        ltm_status["utilization_percent"] = min(100, (ltm_status["total_entries"] / max_ltm_entries) * 100)
        ltm_status["memory_health"] = "good" if ltm_status["total_entries"] < 800 else "warning" if ltm_status["total_entries"] < 900 else "critical"

        return {
            "stm_status": stm_status,
            "ltm_status": ltm_status,
            "summary": {
                "total_memory_entries": stm_status["total_entries"] + ltm_status["total_entries"],
                "memory_efficiency": round((stm_status["utilization_percent"] + ltm_status["utilization_percent"]) / 2, 1),
                "overall_health": "good" if stm_status["memory_health"] == "good" and ltm_status["memory_health"] == "good" else "warning" if stm_status["memory_health"] != "critical" and ltm_status["memory_health"] != "critical" else "critical"
            }
        }

    def _generate_semantic_memory_coverage(self) -> Dict[str, Any]:
        """Generate semantic memory coverage visualization with knowledge domains as nodes"""
        semantic_coverage = {
            "knowledge_domains": [],
            "domain_connections": [],
            "coverage_metrics": {},
            "visualization_nodes": [],
            "visualization_edges": []
        }

        if not hasattr(metrics, 'semantic_store'):
            return semantic_coverage

        semantic_store = metrics.semantic_store

        # Extract knowledge domains and concepts
        domains = {}
        concepts = []

        for key, entry in semantic_store.items():
            data = entry.get("data", {})
            fact = data.get("fact", "")
            category = data.get("category", "general")

            if category not in domains:
                domains[category] = {
                    "name": category,
                    "concept_count": 0,
                    "facts": [],
                    "connections": set()
                }

            domains[category]["concept_count"] += 1
            domains[category]["facts"].append(fact)

            # Extract concepts from facts (simplified)
            words = fact.lower().split()
            key_concepts = [word for word in words if len(word) > 3 and word not in ["that", "with", "from", "this", "they", "have", "been"]]
            concepts.extend(key_concepts[:3])  # Limit to 3 concepts per fact

        # Create domain nodes for visualization
        for domain_name, domain_data in domains.items():
            node_size = min(50, 20 + domain_data["concept_count"] * 2)  # Size based on concept count
            color_intensity = min(255, 100 + domain_data["concept_count"] * 10)  # Color based on richness

            semantic_coverage["visualization_nodes"].append({
                "id": domain_name,
                "label": f"{domain_name}\n({domain_data['concept_count']} concepts)",
                "size": node_size,
                "color": f"rgb({color_intensity}, {200}, {255 - color_intensity})",
                "type": "domain"
            })

        # Create connections between domains (based on shared concepts)
        domain_list = list(domains.keys())
        for i, domain1 in enumerate(domain_list):
            for domain2 in domain_list[i+1:]:
                # Check for overlapping concepts (simplified)
                concepts1 = set()
                concepts2 = set()

                for fact in domains[domain1]["facts"]:
                    concepts1.update(fact.lower().split()[:5])  # First 5 words as concepts

                for fact in domains[domain2]["facts"]:
                    concepts2.update(fact.lower().split()[:5])

                overlap = len(concepts1.intersection(concepts2))
                if overlap > 0:
                    semantic_coverage["visualization_edges"].append({
                        "from": domain1,
                        "to": domain2,
                        "weight": overlap,
                        "color": f"rgba(100, 100, 100, {min(1.0, overlap / 5)})"
                    })

        # Coverage metrics
        semantic_coverage["coverage_metrics"] = {
            "total_domains": len(domains),
            "total_concepts": sum(d["concept_count"] for d in domains.values()),
            "avg_concepts_per_domain": round(sum(d["concept_count"] for d in domains.values()) / len(domains), 1) if domains else 0,
            "most_rich_domain": max(domains.items(), key=lambda x: x[1]["concept_count"]) if domains else None,
            "knowledge_gaps": self._identify_knowledge_gaps(domains)
        }

        semantic_coverage["knowledge_domains"] = list(domains.keys())

        return semantic_coverage

    def _generate_episodic_memory_heatmap(self) -> Dict[str, Any]:
        """Generate episodic memory heatmap showing frequency and recency of past tasks"""
        episodic_heatmap = {
            "task_frequency": {},
            "recency_matrix": {},
            "temporal_patterns": {},
            "visualization_data": {
                "heatmap_matrix": [],
                "time_labels": [],
                "task_labels": []
            }
        }

        if not hasattr(metrics, 'episodic_store'):
            return episodic_heatmap

        episodic_store = metrics.episodic_store
        current_time = time.time()

        # Analyze task patterns
        task_patterns = {}
        time_windows = {
            "last_hour": 3600,
            "last_6_hours": 21600,
            "last_24_hours": 86400,
            "last_7_days": 604800,
            "last_30_days": 2592000
        }

        for key, entry in episodic_store.items():
            data = entry.get("data", {})
            event = data.get("event", "")
            timestamp = entry.get("timestamp", current_time)

            # Extract task type from event (simplified)
            task_type = "unknown"
            if "task" in event.lower():
                task_type = "task_execution"
            elif "reasoning" in event.lower():
                task_type = "reasoning"
            elif "decision" in event.lower():
                task_type = "decision_making"
            elif "analysis" in event.lower():
                task_type = "analysis"

            if task_type not in task_patterns:
                task_patterns[task_type] = {
                    "count": 0,
                    "timestamps": [],
                    "time_distribution": {window: 0 for window in time_windows.keys()}
                }

            pattern = task_patterns[task_type]
            pattern["count"] += 1
            pattern["timestamps"].append(timestamp)

            # Count in time windows
            age_seconds = current_time - timestamp
            for window_name, window_seconds in time_windows.items():
                if age_seconds <= window_seconds:
                    pattern["time_distribution"][window_name] += 1

        # Create frequency data
        episodic_heatmap["task_frequency"] = {
            task_type: data["count"] for task_type, data in task_patterns.items()
        }

        # Create recency matrix
        episodic_heatmap["recency_matrix"] = {
            task_type: data["time_distribution"] for task_type, data in task_patterns.items()
        }

        # Temporal patterns analysis
        episodic_heatmap["temporal_patterns"] = self._analyze_temporal_patterns(task_patterns)

        # Visualization data for heatmap
        task_types = list(task_patterns.keys())
        time_periods = list(time_windows.keys())

        episodic_heatmap["visualization_data"]["task_labels"] = task_types
        episodic_heatmap["visualization_data"]["time_labels"] = time_periods

        # Create heatmap matrix
        heatmap_matrix = []
        for task_type in task_types:
            row = []
            for time_period in time_periods:
                count = task_patterns[task_type]["time_distribution"][time_period]
                # Normalize for visualization (0-1 scale)
                max_count = max(task_patterns[t]["time_distribution"][time_period] for t in task_types) if task_types else 1
                normalized_value = count / max_count if max_count > 0 else 0
                row.append(round(normalized_value, 2))
            heatmap_matrix.append(row)

        episodic_heatmap["visualization_data"]["heatmap_matrix"] = heatmap_matrix

        return episodic_heatmap

    def _generate_memory_health_metrics(self) -> Dict[str, Any]:
        """Generate memory health and performance metrics"""
        health_metrics = {
            "memory_performance": {},
            "access_patterns": {},
            "retention_rates": {},
            "optimization_suggestions": []
        }

        current_time = time.time()

        # Memory performance metrics
        if hasattr(metrics, 'memory_store'):
            stm_entries = len(metrics.memory_store)
            health_metrics["memory_performance"]["stm_utilization"] = round(min(100, (stm_entries / 50) * 100), 1)

        ltm_total = 0
        if hasattr(metrics, 'episodic_store'):
            ltm_total += len(metrics.episodic_store)
        if hasattr(metrics, 'semantic_store'):
            ltm_total += len(metrics.semantic_store)
        if hasattr(metrics, 'tool_use_store'):
            ltm_total += len(metrics.tool_use_store)
        if hasattr(metrics, 'reflection_store'):
            ltm_total += len(metrics.reflection_store)

        health_metrics["memory_performance"]["ltm_utilization"] = round(min(100, (ltm_total / 1000) * 100), 1)

        # Access patterns (simplified - would need actual access tracking)
        health_metrics["access_patterns"] = {
            "stm_access_frequency": "high" if hasattr(metrics, 'memory_store') and len(metrics.memory_store) > 10 else "low",
            "ltm_access_frequency": "medium",  # Would be calculated from actual access logs
            "cache_hit_rate": 0.85  # Mock value - would be calculated from access patterns
        }

        # Retention rates (simplified)
        health_metrics["retention_rates"] = {
            "short_term_retention": 0.9,  # 90% of STM entries retained
            "long_term_retention": 0.7,  # 70% of important info retained in LTM
            "knowledge_decay_rate": 0.05  # 5% decay per month
        }

        # Optimization suggestions
        suggestions = []

        if health_metrics["memory_performance"].get("stm_utilization", 0) > 80:
            suggestions.append("Consider increasing STM capacity or implementing more aggressive pruning")

        if health_metrics["memory_performance"].get("ltm_utilization", 0) > 90:
            suggestions.append("LTM nearing capacity - consider archiving old episodic memories")

        if health_metrics["access_patterns"].get("cache_hit_rate", 0) < 0.7:
            suggestions.append("Low cache hit rate - optimize memory access patterns")

        health_metrics["optimization_suggestions"] = suggestions

        return health_metrics

    def _identify_knowledge_gaps(self, domains: Dict[str, Any]) -> List[str]:
        """Identify potential knowledge gaps in semantic memory"""
        gaps = []

        # Check for common knowledge domains that might be missing
        expected_domains = ["reasoning", "decision_making", "problem_solving", "learning", "communication"]
        existing_domains = set(domains.keys())

        missing_domains = set(expected_domains) - existing_domains
        if missing_domains:
            gaps.extend([f"Missing knowledge domain: {domain}" for domain in missing_domains])

        # Check for domains with very few concepts
        for domain_name, domain_data in domains.items():
            if domain_data["concept_count"] < 3:
                gaps.append(f"Underdeveloped domain: {domain_name} (only {domain_data['concept_count']} concepts)")

        # Check for isolated domains (no connections)
        connected_domains = set()
        for domain_name in domains.keys():
            # Simple check - domains with names containing related terms are considered connected
            related_terms = {
                "reasoning": ["logic", "thinking", "analysis"],
                "decision": ["choice", "planning", "strategy"],
                "learning": ["adaptation", "improvement", "training"]
            }

            for base_domain, related in related_terms.items():
                if base_domain in domain_name.lower() or any(term in domain_name.lower() for term in related):
                    connected_domains.add(domain_name)

        isolated_domains = set(domains.keys()) - connected_domains
        if isolated_domains:
            gaps.extend([f"Isolated knowledge domain: {domain}" for domain in isolated_domains])

        return gaps

    def _analyze_temporal_patterns(self, task_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze temporal patterns in episodic memory"""
        patterns = {
            "peak_activity_times": [],
            "activity_trends": {},
            "predictive_insights": []
        }

        # Find peak activity times
        time_windows = ["last_hour", "last_6_hours", "last_24_hours", "last_7_days", "last_30_days"]
        for window in time_windows:
            total_activity = sum(pattern["time_distribution"][window] for pattern in task_patterns.values())
            if total_activity > 0:
                patterns["peak_activity_times"].append({
                    "time_window": window,
                    "total_activities": total_activity,
                    "most_active_task": max(task_patterns.items(), key=lambda x: x[1]["time_distribution"][window])[0]
                })

        # Activity trends (simplified)
        patterns["activity_trends"] = {
            "overall_trend": "stable",  # Would be calculated from historical data
            "task_type_evolution": "diversifying",  # Would analyze task type changes over time
            "frequency_stability": "consistent"  # Would measure variance in activity levels
        }

        # Predictive insights
        patterns["predictive_insights"] = [
            "Based on current patterns, expect increased reasoning activity",
            "Decision-making tasks show seasonal patterns",
            "Consider pre-loading frequently accessed knowledge domains"
        ]

        return patterns

    def _generate_federation_health_section(self) -> Dict[str, Any]:
        """Generate federation health overview section"""
        federation_metrics = federation_manager.get_federation_metrics()

        section = {
            "title": "Federation Health Overview",
            "data": {
                "federation_health_score": round(federation_metrics.get("federation_health", 0) * 100, 1),
                "total_swarms": federation_metrics.get("total_swarms", 0),
                "resource_utilization": federation_metrics.get("resource_utilization", {}),
                "cooperation_scores": federation_metrics.get("cooperation_scores", {}),
                "health_status": self._calculate_federation_health_status(federation_metrics),
                "federation_goals_progress": federation_metrics.get("federation_goals_progress", {})
            }
        }

        return section

    def _calculate_federation_health_status(self, metrics: Dict[str, Any]) -> str:
        """Calculate federation health status"""
        health_score = metrics.get("federation_health", 0)
        total_swarms = metrics.get("total_swarms", 0)

        if total_swarms == 0:
            return "no_swarms"
        elif health_score >= 0.8:
            return "excellent"
        elif health_score >= 0.6:
            return "good"
        elif health_score >= 0.4:
            return "fair"
        else:
            return "needs_attention"

    def _generate_inter_swarm_communications_section(self) -> Dict[str, Any]:
        """Generate inter-swarm communications section"""
        section = {
            "title": "Inter-Swarm Communications",
            "data": {
                "total_communications": len(federation_manager.inter_swarm_communications),
                "communication_types": {},
                "recent_communications": [],
                "communication_patterns": {}
            }
        }

        # Analyze communication types
        for comm in federation_manager.inter_swarm_communications[-50:]:  # Last 50 communications
            comm_type = comm.get("type", "unknown")
            section["data"]["communication_types"][comm_type] = section["data"]["communication_types"].get(comm_type, 0) + 1

        # Recent communications
        for comm in federation_manager.inter_swarm_communications[-10:]:  # Last 10
            section["data"]["recent_communications"].append({
                "type": comm.get("type"),
                "source_swarm": comm.get("source_swarm"),
                "target_swarm": comm.get("target_swarm"),
                "timestamp": comm.get("delegation_timestamp"),
                "description": f"{comm.get('type', 'unknown')} from {comm.get('source_swarm', 'unknown')} to {comm.get('target_swarm', 'unknown')}"
            })

        return section

    def _generate_resource_sharing_section(self) -> Dict[str, Any]:
        """Generate resource sharing section"""
        section = {
            "title": "Resource Sharing Across Federation",
            "data": {
                "resource_pool_status": federation_manager.resource_pool,
                "sharing_opportunities": [],
                "capability_distribution": {},
                "resource_utilization_trends": {}
            }
        }

        # Analyze capability distribution
        all_capabilities = set()
        for swarm_resources in federation_manager.resource_pool.values():
            capabilities = swarm_resources.get("capabilities", [])
            for cap in capabilities:
                all_capabilities.add(cap)
                section["data"]["capability_distribution"][cap] = section["data"]["capability_distribution"].get(cap, 0) + 1

        # Identify sharing opportunities
        for cap in all_capabilities:
            swarms_with_cap = [swarm_id for swarm_id, resources in federation_manager.resource_pool.items()
                             if cap in resources.get("capabilities", [])]
            if len(swarms_with_cap) > 1:
                section["data"]["sharing_opportunities"].append({
                    "capability": cap,
                    "available_in_swarms": swarms_with_cap,
                    "redundancy_level": len(swarms_with_cap),
                    "sharing_potential": "high" if len(swarms_with_cap) >= 3 else "medium"
                })

        return section

    def _generate_conflict_resolution_section(self) -> Dict[str, Any]:
        """Generate conflict resolution section"""
        section = {
            "title": "Conflict Resolution in Federation",
            "data": {
                "total_conflicts": len(federation_manager.conflict_history),
                "resolution_rate": federation_manager._calculate_conflict_resolution_rate(),
                "conflict_types": {},
                "recent_resolutions": [],
                "resolution_strategies": {}
            }
        }

        # Analyze conflict types and resolutions
        for conflict in federation_manager.conflict_history[-20:]:  # Last 20 conflicts
            conflict_type = conflict.get("conflict", {}).get("type", "unknown")
            resolution_strategy = conflict.get("strategy_used", "unknown")

            section["data"]["conflict_types"][conflict_type] = section["data"]["conflict_types"].get(conflict_type, 0) + 1
            section["data"]["resolution_strategies"][resolution_strategy] = section["data"]["resolution_strategies"].get(resolution_strategy, 0) + 1

        # Recent resolutions
        for conflict in federation_manager.conflict_history[-5:]:  # Last 5
            section["data"]["recent_resolutions"].append({
                "conflict_type": conflict.get("conflict", {}).get("type"),
                "resolution_decision": conflict.get("resolution", {}).get("decision"),
                "strategy_used": conflict.get("strategy_used"),
                "timestamp": conflict.get("timestamp"),
                "involved_swarms": conflict.get("conflict", {}).get("swarms", [])
            })

        return section

    def _generate_federation_optimization_section(self) -> Dict[str, Any]:
        """Generate federation optimization recommendations section"""
        optimization_results = federation_manager.optimize_federation()

        section = {
            "title": "Federation Optimization Recommendations",
            "data": {
                "optimization_actions": optimization_results,
                "total_recommendations": sum(len(actions) for actions in optimization_results.values()),
                "priority_actions": [],
                "implementation_status": {}
            }
        }

        # Identify priority actions
        for action_type, actions in optimization_results.items():
            for action in actions:
                if action.get("severity") == "high" or action_type == "load_balancing_actions":
                    section["data"]["priority_actions"].append({
                        "type": action_type,
                        "action": action,
                        "priority": "high"
                    })

        return section

    def _generate_load_forecasting_section(self) -> Dict[str, Any]:
        """Generate load forecasting section"""
        section = {
            "title": "Agent Load Forecasting",
            "description": "Predictive analytics for agent workload management",
            "data": {}
        }

        if not self.coordinator:
            return section

        # Get load forecasts for all agents
        forecasts = {}
        for agent_id in self.coordinator.registered_agents:
            forecast = self.coordinator.load_forecaster.forecast_agent_load(agent_id)
            forecasts[agent_id] = forecast

        section["data"]["agent_forecasts"] = forecasts

        # Summary statistics
        if forecasts:
            predicted_loads = [f['predicted_load'] for f in forecasts.values()]
            section["data"]["summary"] = {
                "total_predicted_load": sum(predicted_loads),
                "average_predicted_load": sum(predicted_loads) / len(predicted_loads),
                "high_load_agents": [agent for agent, f in forecasts.items() if f['predicted_load'] > 3.5],
                "low_load_agents": [agent for agent, f in forecasts.items() if f['predicted_load'] < 1.0]
            }

        return section

    def _generate_preventive_actions_section(self) -> Dict[str, Any]:
        """Generate preventive actions section"""
        section = {
            "title": "Preventive Action Analytics",
            "description": "Task rerouting and failure prevention metrics",
            "data": {}
        }

        if not self.coordinator:
            return section

        # Get rerouting effectiveness
        effectiveness = self.coordinator.preventive_retry_system.get_rerouting_effectiveness()
        section["data"]["rerouting_effectiveness"] = effectiveness

        # Recent preventive actions
        recent_actions = list(self.coordinator.preventive_retry_system.preventive_actions_taken)[-10:]
        section["data"]["recent_actions"] = recent_actions

        # Failure risk assessments (mock data for now)
        section["data"]["failure_risk_distribution"] = {
            "low_risk": 0.6,
            "medium_risk": 0.3,
            "high_risk": 0.1
        }

        return section

    def _generate_resource_recommendations_section(self) -> Dict[str, Any]:
        """Generate resource recommendations section"""
        section = {
            "title": "Resource Allocation Recommendations",
            "description": "AI-driven suggestions for optimal resource utilization",
            "data": {}
        }

        if not self.coordinator:
            return section

        # Get predictive insights
        insights = self.coordinator.get_predictive_control_insights()
        section["data"]["recommendations"] = insights.get("resource_recommendations", [])

        # Load balancing suggestions
        forecasts = insights.get("load_forecasts", {})
        balancing_suggestions = []

        if forecasts:
            high_load = [agent for agent, f in forecasts.items() if f['predicted_load'] > 3.5]
            low_load = [agent for agent, f in forecasts.items() if f['predicted_load'] < 1.5]

            if high_load and low_load:
                balancing_suggestions.append(f"Consider redistributing tasks from {', '.join(high_load)} to {', '.join(low_load)}")

        section["data"]["load_balancing_suggestions"] = balancing_suggestions

        return section

    def _generate_system_health_predictions_section(self) -> Dict[str, Any]:
        """Generate system health predictions section"""
        section = {
            "title": "System Health Predictions",
            "description": "Predictive health monitoring and early warning system",
            "data": {}
        }

        if not self.coordinator:
            return section

        # Get health predictions
        insights = self.coordinator.get_predictive_control_insights()
        health_predictions = insights.get("system_health_predictions", {})

        section["data"]["health_score"] = health_predictions.get("predicted_health_score", 0.8)
        section["data"]["status"] = "healthy" if health_predictions.get("predicted_health_score", 0) > 0.7 else "warning" if health_predictions.get("predicted_health_score", 0) > 0.5 else "critical"
        section["data"]["high_failure_agents"] = health_predictions.get("high_failure_agents", [])
        section["data"]["load_status"] = health_predictions.get("load_status", "unknown")
        section["data"]["health_recommendations"] = health_predictions.get("recommendations", [])

        return section

# Global dashboard instance
dashboard = BrainSwarmDashboard()