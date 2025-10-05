from typing import Dict, List, Any, Optional
from ..core.base import BaseAgent, AgentRole, Message, MessageType, Task, DebateResult, logger, metrics
from ..analytics.predictive_analytics import (
    TaskCompletionPredictor, MemoryBottleneckPredictor, FailurePredictor,
    task_completion_predictor, memory_bottleneck_predictor, failure_predictor
)
from ..analytics.self_tuning import (
    SelfTuningParameterManager, get_adaptive_reasoning_depth, get_adaptive_branch_limits,
    get_adaptive_retry_strategy, record_task_performance_for_tuning, get_self_tuning_status
)
from ..analytics.autonomous_goals import (
    initialize_autonomous_goals, generate_autonomous_goals, get_goal_statistics
)
from ..security.policy_layer import (
    PolicyEngine, evaluate_task_policy, check_ethical_alignment,
    get_governance_status, report_policy_violation
)
from .adaptive_broker import AdaptiveTaskBroker
import time
import statistics
from collections import deque
import random

class PlanningModule:
    def __init__(self):
        self.strategies = {}
        self.strategy_weights = {
            "priority_based": 0.6,
            "simulation_guided": 0.4,
            "experience_based": 0.3
        }

    def generate_strategy(self, task_description: str, available_agents: List[str]) -> Dict[str, Any]:
        """Generate high-level strategy for task execution with priorities, mini-coordinators, and meta-learning"""
        # Determine task type for meta-learning
        task_type = self._classify_task_type(task_description)

        # Get meta-learning recommendations
        meta_recommendations = metrics.get_optimal_strategy(task_type, available_agents)

        subtasks = self.break_down_task(task_description)
        prioritized_subtasks = self.assign_priorities(subtasks, task_description)

        # Apply meta-learning insights to strategy
        if meta_recommendations["recommended_strategy"]:
            # Adjust strategy weights based on learned preferences
            rec_strategy = meta_recommendations["recommended_strategy"]["strategy"]
            if "priority" in rec_strategy.lower():
                # Increase priority weighting for tasks where it succeeded
                for subtask in prioritized_subtasks:
                    if subtask["priority"] < 4:  # Don't over-prioritize already high priority tasks
                        subtask["priority"] = min(subtask["priority"] + 1, 5)

        # Group complex subtasks into clusters for mini-coordinators
        task_clusters = self.cluster_complex_subtasks(prioritized_subtasks)

        # Apply agent combination recommendations
        agent_assignments = self.assign_agents_to_subtasks(available_agents, prioritized_subtasks)
        if meta_recommendations["recommended_agents"]:
            rec_agents = meta_recommendations["recommended_agents"]["agents"]
            # Bias agent assignments toward successful combinations
            for agent in rec_agents:
                if agent in agent_assignments:
                    # Increase preference for these agents
                    pass  # Could implement agent preference scoring

        strategy = {
            "task": task_description,
            "task_type": task_type,
            "subtasks": prioritized_subtasks,
            "task_clusters": task_clusters,
            "agent_assignments": agent_assignments,
            "estimated_complexity": self.estimate_complexity(task_description),
            "risk_factors": self.identify_risks(task_description),
            "meta_learning_used": meta_recommendations["meta_learning_confidence"] > 0.5
        }
        return strategy

    def break_down_task(self, task: str, level: int = 0, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Break down complex task into hierarchical subtasks"""
        if level >= max_depth:
            return [{"description": f"Execute: {task}", "level": level, "subtasks": []}]

        # Check for batch processing patterns (e.g., "summarize 10 articles")
        batch_pattern = self._detect_batch_processing(task)
        if batch_pattern and level == 0:
            return self._create_batch_subtasks(task, batch_pattern)

        # Simple heuristic - split by keywords with hierarchy
        subtasks = []

        task_lower = task.lower()
        if "analyze" in task_lower:
            analysis_task = {
                "description": "Gather and analyze relevant data",
                "level": level,
                "subtasks": self.break_down_task("Gather relevant data", level + 1, max_depth)
            }
            subtasks.append(analysis_task)

        if "process" in task_lower:
            process_task = {
                "description": "Process and transform data",
                "level": level,
                "subtasks": self.break_down_task("Process and transform data", level + 1, max_depth)
            }
            subtasks.append(process_task)

        if "decide" in task_lower or "choose" in task_lower:
            decision_task = {
                "description": "Evaluate options and make decision",
                "level": level,
                "subtasks": self.break_down_task("Evaluate options and make decision", level + 1, max_depth)
            }
            subtasks.append(decision_task)

        if not subtasks:
            subtasks = [{"description": f"Execute: {task}", "level": level, "subtasks": []}]

        return subtasks

    def _detect_batch_processing(self, task: str) -> Optional[Dict[str, Any]]:
        """Detect if task involves processing multiple similar items"""
        import re

        task_lower = task.lower()

        # Patterns for batch processing: "summarize X articles", "process Y items", etc.
        patterns = [
            (r'summarize\s+(\d+)\s+(articles?|documents?|papers?|reports?)', 'summarize', 'article'),
            (r'analyze\s+(\d+)\s+(articles?|documents?|papers?|reports?)', 'analyze', 'article'),
            (r'process\s+(\d+)\s+(items?|files?|records?)', 'process', 'item'),
            (r'review\s+(\d+)\s+(articles?|documents?|papers?|reports?)', 'review', 'article'),
            (r'evaluate\s+(\d+)\s+(options?|items?|candidates?)', 'evaluate', 'item'),
        ]

        for pattern, action, item_type in patterns:
            match = re.search(pattern, task_lower)
            if match:
                count = int(match.group(1))
                return {
                    "action": action,
                    "count": count,
                    "item_type": item_type,
                    "original_task": task
                }

        return None

    def _create_batch_subtasks(self, task: str, batch_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create hierarchical subtasks for batch processing"""
        action = batch_info["action"]
        count = batch_info["count"]
        item_type = batch_info["item_type"]

        subtasks = []

        # Create individual processing subtasks
        for i in range(1, count + 1):
            agent_name = chr(ord('A') + (i - 1) % 26)  # A, B, C, ... for agent naming
            subtask = {
                "description": f"Agent {agent_name} → {action.capitalize()} {item_type} {i}",
                "level": 0,
                "subtasks": [],
                "batch_item": i,
                "batch_action": action,
                "priority": 2  # Medium priority for individual items
            }
            subtasks.append(subtask)

        # Add aggregation subtask
        aggregation_subtask = {
            "description": f"Coordinator → Aggregate {action} results from {count} {item_type}s",
            "level": 0,
            "subtasks": [],
            "is_aggregation": True,
            "priority": 3  # High priority for aggregation
        }
        subtasks.append(aggregation_subtask)

        # Add final synthesis/report generation
        final_subtask = {
            "description": f"LanguageAgent → Generate final {action} report",
            "level": 0,
            "subtasks": [],
            "is_final_synthesis": True,
            "priority": 4  # Highest priority for final output
        }
        subtasks.append(final_subtask)

        return subtasks

    def assign_agents_to_subtasks(self, available_agents: List[str], subtasks: List[Dict[str, Any]] = None) -> Dict[str, str]:
        """Assign agents to subtasks based on expertise and batch processing needs"""
        assignments = {}
        agent_expertise = {
            "VisionAgent": ["visual", "image", "see"],
            "LanguageAgent": ["text", "language", "summarize", "dialogue", "report", "generate"],
            "MathReasoningAgent": ["calculate", "math", "logic", "reason"],
            "SimulationAgent": ["simulate", "test", "scenario"]
        }

        # Handle batch processing assignments
        if subtasks:
            for subtask in subtasks:
                if subtask.get("batch_item"):
                    # Individual batch items - assign based on action type
                    action = subtask.get("batch_action", "")
                    if action in ["summarize", "analyze", "review"]:
                        assignments["LanguageAgent"] = agent_expertise.get("LanguageAgent", [])
                    elif action in ["process", "evaluate"]:
                        # Use available agents based on expertise
                        for agent in available_agents:
                            if agent in agent_expertise:
                                assignments[agent] = agent_expertise[agent]
                elif subtask.get("is_aggregation"):
                    # Aggregation tasks - prefer coordinator or language agent
                    assignments["LanguageAgent"] = agent_expertise.get("LanguageAgent", [])
                elif subtask.get("is_final_synthesis"):
                    # Final synthesis - specifically language agent
                    assignments["LanguageAgent"] = agent_expertise.get("LanguageAgent", [])

        # Default assignments for all available agents
        for agent in available_agents:
            if agent in agent_expertise:
                assignments[agent] = agent_expertise[agent]

        return assignments

    def estimate_complexity(self, task: str) -> str:
        """Estimate task complexity"""
        word_count = len(task.split())
        if word_count < 10:
            return "low"
        elif word_count < 50:
            return "medium"
        else:
            return "high"

    def identify_risks(self, task: str) -> List[str]:
        """Identify potential risks"""
        risks = []
        if "urgent" in task.lower():
            risks.append("Time pressure may affect quality")
        if "complex" in task.lower():
            risks.append("High complexity may require multiple iterations")
        return risks

    def assign_priorities(self, subtasks: List[Dict[str, Any]], task_description: str) -> List[Dict[str, Any]]:
        """Assign priorities to subtasks based on task requirements with urgency levels"""
        task_lower = task_description.lower()

        # Determine overall task urgency
        urgency_keywords = ["urgent", "emergency", "critical", "asap", "immediate"]
        task_urgency = sum(1 for keyword in urgency_keywords if keyword in task_lower)

        for subtask in subtasks:
            # Skip if priority already set (e.g., from batch processing)
            if "priority" in subtask:
                continue

            priority = 1  # Default medium priority
            urgency = 0  # Additional urgency boost
            subtask_desc = subtask["description"]

            # High priority for foundational tasks
            if any(word in subtask_desc.lower() for word in ["gather", "collect", "analyze", "understand"]):
                priority = 3

            # High priority for decision tasks
            elif any(word in subtask_desc.lower() for word in ["decide", "choose", "evaluate"]):
                priority = 3

            # Low priority for summary/reporting tasks
            elif any(word in subtask_desc.lower() for word in ["summarize", "report", "document"]):
                priority = 1

            # Adjust based on main task urgency
            if task_urgency > 0 and priority < 3:
                urgency = min(task_urgency, 2)  # Cap urgency boost

            # Check for subtask-specific urgency indicators
            subtask_lower = subtask_desc.lower()
            subtask_urgency_keywords = ["deadline", "time-sensitive", "blocking", "critical path"]
            subtask_urgency = sum(1 for keyword in subtask_urgency_keywords if keyword in subtask_lower)
            urgency += subtask_urgency

            # Calculate final priority with urgency boost
            final_priority = min(priority + urgency, 5)  # Cap at 5

            subtask["priority"] = final_priority
            subtask["urgency"] = urgency
            subtask["base_priority"] = priority

        # Sort by priority (highest first), then by urgency
        subtasks.sort(key=lambda x: (x["priority"], x.get("urgency", 0)), reverse=True)
        return subtasks

    def cluster_complex_subtasks(self, subtasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group complex subtasks into clusters for mini-coordinator handling"""
        clusters = []
        remaining_subtasks = subtasks.copy()

        # Group subtasks by complexity and relatedness
        while remaining_subtasks:
            cluster = []
            base_subtask = remaining_subtasks.pop(0)
            cluster.append(base_subtask)

            # Find related subtasks to cluster together
            i = 0
            while i < len(remaining_subtasks):
                subtask = remaining_subtasks[i]
                if self._are_subtasks_related(base_subtask, subtask) or subtask["priority"] >= 4:
                    cluster.append(subtask)
                    remaining_subtasks.pop(i)
                else:
                    i += 1

            # Create cluster if it has multiple high-priority or complex tasks
            if len(cluster) > 1 and any(s["priority"] >= 3 for s in cluster):
                cluster_id = f"cluster_{len(clusters)}"
                clusters.append({
                    "cluster_id": cluster_id,
                    "subtasks": cluster,
                    "complexity": sum(s["priority"] for s in cluster) / len(cluster),
                    "requires_mini_coordinator": True
                })
            else:
                # Single tasks or simple clusters don't need mini-coordinators
                for subtask in cluster:
                    clusters.append({
                        "cluster_id": f"simple_{len(clusters)}",
                        "subtasks": [subtask],
                        "complexity": subtask["priority"],
                        "requires_mini_coordinator": False
                    })

        return clusters

    def _are_subtasks_related(self, task1: Dict[str, Any], task2: Dict[str, Any]) -> bool:
        """Check if two subtasks are related and should be clustered"""
        desc1 = task1["description"].lower()
        desc2 = task2["description"].lower()

        # Simple relatedness check based on keywords
        related_keywords = [
            ("analyze", "data"), ("process", "data"), ("evaluate", "decision"),
            ("gather", "collect"), ("plan", "execute")
        ]

        for kw1, kw2 in related_keywords:
            if (kw1 in desc1 and kw2 in desc2) or (kw1 in desc2 and kw2 in desc1):
                return True

        return False

    def _classify_task_type(self, task_description: str) -> str:
        """Classify task type for meta-learning"""
        desc_lower = task_description.lower()

        if any(word in desc_lower for word in ["analyze", "examine", "study", "review"]):
            return "analysis"
        elif any(word in desc_lower for word in ["create", "design", "plan", "develop"]):
            return "creative"
        elif any(word in desc_lower for word in ["calculate", "solve", "compute", "math"]):
            return "mathematical"
        elif any(word in desc_lower for word in ["decide", "choose", "evaluate", "assess"]):
            return "decision_making"
        elif any(word in desc_lower for word in ["simulate", "model", "predict", "forecast"]):
            return "simulation"
        elif any(word in desc_lower for word in ["communicate", "explain", "describe", "summarize"]):
            return "communication"
        else:
            return "general"

    def automated_memory_handoff(self, task_id: str, strategy: Dict[str, Any], final_result: Any):
        """Automatically transfer relevant data from STM to LTM after task completion"""
        # Transfer successful strategy to episodic memory
        self.long_term_memory.episodic_memory(
            f"Completed task: {strategy.get('task', '')}",
            {
                "strategy": strategy,
                "outcome": "completed",
                "task_id": task_id,
                "final_result": final_result,
                "completion_time": time.time()
            }
        )

        # Extract and store key learnings in semantic memory
        key_concepts = self.extract_key_concepts(strategy, final_result)
        for concept in key_concepts:
            self.long_term_memory.update_semantic_memory(concept, "learned_concepts")

        # Transfer intermediate results if valuable
        intermediate_results = self.working_memory.search(f"intermediate_{task_id}")
        for result in intermediate_results[:3]:  # Limit to most recent
            self.long_term_memory.store(f"archived_intermediate_{task_id}_{time.time()}",
                                      result, {"type": "episodic"})

    def extract_key_concepts(self, strategy: Dict[str, Any], final_result: Any) -> List[str]:
        """Extract key concepts from completed task for semantic memory"""
        concepts = []
        task_desc = strategy.get("task", "").lower()

        # Extract domain-specific concepts
        if "analyze" in task_desc:
            concepts.append("data analysis techniques")
        if "decision" in task_desc:
            concepts.append("decision making frameworks")
        if "problem" in task_desc:
            concepts.append("problem solving approaches")

        # Extract from subtasks
        for subtask in strategy.get("subtasks", []):
            if isinstance(subtask, dict):
                desc = subtask.get("description", "")
            else:
                desc = subtask
            if "evaluate" in desc.lower():
                concepts.append("evaluation methods")

        return list(set(concepts))  # Remove duplicates

    def delegate_hierarchical_subtasks(self, subtasks: List[Dict[str, Any]], parent_task_id: str,
                                      agent_assignments: Dict[str, str], level: int = 0):
        """Recursively delegate hierarchical subtasks"""
        for i, subtask_info in enumerate(subtasks):
            subtask_desc = subtask_info["description"]
            priority = subtask_info.get("priority", 1)  # Default priority if not set

            # Check resource availability for high-priority tasks
            if priority >= 3 and not self.check_resource_availability():
                # Queue high-priority tasks if resources limited
                continue

            # Use load balancing for agent assignment
            required_expertise = None
            for agent_type, expertise in agent_assignments.items():
                if any(keyword in subtask_desc.lower() for keyword in expertise):
                    required_expertise = agent_type
                    break

            assigned_agent = self.get_least_loaded_agent(required_expertise)
            if not assigned_agent:
                # Fallback to original method if load balancing fails
                assigned_agent = self.delegation_system.assign_subtask(
                    subtask_desc, self.registered_agents, agent_assignments
                )

            if assigned_agent:
                subtask_id = f"{parent_task_id}_sub_{level}_{i}"
                subtask_obj = Task(subtask_id, subtask_desc,
                                 {"priority": priority, "level": level}, assigned_agent)
                self.delegation_system.active_tasks[subtask_id] = {
                    "task": subtask_obj,
                    "status": "assigned",
                    "assigned_at": time.time(),
                    "priority": priority,
                    "level": level
                }

                # Update agent load
                self.update_agent_load(assigned_agent, 1)

                # Send task assignment message
                self.send_message(assigned_agent, MessageType.TASK_ASSIGNMENT,
                                {"task": subtask_obj})

                # Recursively delegate child subtasks
                if subtask_info.get("subtasks"):
                    self.delegate_hierarchical_subtasks(subtask_info["subtasks"], subtask_id,
                                                      agent_assignments, level + 1)

    def update_with_feedback(self, feedback: Dict[str, Any]):
        """Update planning strategies with imagination feedback"""
        # Incorporate potential outcomes into strategy generation
        if "possible_outcomes" in feedback:
            # Adjust subtasks based on simulated outcomes
            outcomes = feedback["possible_outcomes"]
            # Learn from simulation: prefer strategies that lead to positive outcomes
            self.reinforcement_learning_update(outcomes)
        return "Planning updated with imagination feedback"

    def reinforcement_learning_update(self, outcomes: List[str]):
        """Simple reinforcement learning: adjust strategy preferences based on outcomes"""
        # Track successful patterns
        positive_indicators = ["success", "efficient", "optimal"]
        negative_indicators = ["failure", "inefficient", "problematic"]

        for outcome in outcomes:
            outcome_lower = outcome.lower()
            if any(ind in outcome_lower for ind in positive_indicators):
                # Reinforce this type of approach
                self.strategy_weights["simulation_guided"] = min(1.0, self.strategy_weights.get("simulation_guided", 0.5) + 0.1)
            elif any(ind in outcome_lower for ind in negative_indicators):
                # Reduce preference for this approach
                self.strategy_weights["simulation_guided"] = max(0.0, self.strategy_weights.get("simulation_guided", 0.5) - 0.1)

    def incorporate_emergent_insights(self, patterns: List[str]):
        """Incorporate emergent behavior patterns into planning strategies"""
        for pattern in patterns:
            if "cooperation" in pattern.lower():
                self.strategy_weights["collaborative"] = min(1.0, self.strategy_weights.get("collaborative", 0.5) + 0.1)
            elif "efficiency" in pattern.lower():
                self.strategy_weights["efficiency_focused"] = min(1.0, self.strategy_weights.get("efficiency_focused", 0.5) + 0.1)

    def incorporate_imagination_feedback(self, feedback: Dict[str, Any]):
        """Incorporate imagination simulation feedback into planning"""
        self.planning_module.update_with_feedback(feedback)

    def incorporate_emergent_feedback(self, feedback: Dict[str, Any]):
        """Incorporate emergent behavior feedback into planning and delegation"""
        recommendations = feedback.get("recommendations", [])
        patterns = feedback.get("emergent_patterns", [])

        # Adjust delegation strategy based on emergent patterns
        for rec in recommendations:
            if "collaborative" in rec.lower():
                self.delegation_system.collaboration_bias = min(1.0, getattr(self.delegation_system, 'collaboration_bias', 0.5) + 0.1)
            elif "resource sharing" in rec.lower():
                self.delegation_system.resource_sharing = True

        # Update planning with insights
        self.planning_module.incorporate_emergent_insights(patterns)

class DelegationSystem:
    def __init__(self):
        self.active_tasks = {}

    def assign_subtask(self, subtask: str, available_agents: List[str],
                      agent_expertise: Dict[str, List[str]]) -> Optional[str]:
        """Assign subtask to most suitable agent"""
        best_agent = None
        best_score = 0

        for agent in available_agents:
            if agent in agent_expertise:
                expertise = agent_expertise[agent]
                score = sum(1 for keyword in expertise if keyword in subtask.lower())
                if score > best_score:
                    best_score = score
                    best_agent = agent

        return best_agent or available_agents[0] if available_agents else None

    def track_task_progress(self, task_id: str, status: str):
        """Track progress of delegated tasks"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = status
            if status == "completed":
                self.active_tasks[task_id]["completed_at"] = time.time()

class CriticDebateConsensus:
    def __init__(self):
        self.debate_history = []

    def conduct_debate(self, topic: str, participants: List[str],
                      context: Dict[str, Any]) -> DebateResult:
        """Simulate multi-agent debate and reach consensus"""
        start_time = time.time()
        logger.log("INFO", "CriticDebateConsensus", "Debate started", {"topic": topic, "participants": participants})

        contributions = []

        # Simulate debate contributions (in real implementation, this would involve actual agent communication)
        for participant in participants:
            contribution = {
                "agent": participant,
                "opinion": f"Analysis from {participant} perspective",
                "confidence": 0.8,  # Mock confidence score
                "evidence": f"Evidence based on {participant} expertise"
            }
            contributions.append(contribution)
            logger.log("INFO", "CriticDebateConsensus", "Contribution received", {"agent": participant, "confidence": contribution["confidence"]})

        # Simple consensus mechanism - majority vote or highest confidence
        consensus = self.determine_consensus(contributions)
        execution_time = time.time() - start_time

        # Calculate consensus score (based on highest confidence)
        consensus_score = max(c["confidence"] for c in contributions) if contributions else 0.0

        metrics.track_consensus(topic, len(participants), consensus_score, execution_time)

        logger.log("INFO", "CriticDebateConsensus", "Consensus reached", {"consensus": str(consensus), "score": consensus_score})

        result = DebateResult(topic, contributions, consensus)
        self.debate_history.append(result)

        return result

    def determine_consensus(self, contributions: List[Dict[str, Any]]) -> Any:
        """Determine consensus from debate contributions with scoring"""
        if not contributions:
            return None

        # Score each contribution based on accuracy, creativity, reliability, efficiency
        scored_contributions = []
        task_type = context.get("task_type", "general")

        for contrib in contributions:
            scores = self.score_output(contrib, task_type)
            weights = self.get_scoring_weights(task_type)
            total_score = (scores["accuracy"] * weights["accuracy"] +
                          scores["creativity"] * weights["creativity"] +
                          scores["reliability"] * weights["reliability"] +
                          scores["efficiency"] * weights["efficiency"])
            scored_contributions.append({
                "contribution": contrib,
                "scores": scores,
                "total_score": total_score
            })

        # Return the highest scoring contribution
        best_scored = max(scored_contributions, key=lambda x: x["total_score"])
        best_contribution = best_scored["contribution"]

        # Add scoring feedback for fine-tuning
        actual_quality = best_contribution.get("confidence", 0.5)  # Use confidence as proxy for actual quality
        predicted_quality = best_scored["total_score"]
        outcome = "success" if predicted_quality > 0.7 else "partial" if predicted_quality > 0.5 else "failure"

        metrics.add_scoring_feedback(task_type, actual_quality, predicted_quality,
                                   best_scored["scores"], outcome)

        return best_contribution["opinion"]

    def score_output(self, contribution: Dict[str, Any], task_type: str = "general") -> Dict[str, float]:
        """Score an output based on accuracy, creativity, reliability, and efficiency"""
        opinion = contribution.get("opinion", "")
        evidence = contribution.get("evidence", "")
        confidence = contribution.get("confidence", 0.5)

        # Accuracy: Factual correctness and relevance
        accuracy = 0.6
        if task_type in ["analysis", "fact_checking"]:
            if any(word in evidence.lower() for word in ["data", "evidence", "facts", "verified"]):
                accuracy += 0.3
        if len(opinion.split()) > 10:  # Substantial responses
            accuracy += 0.1
        if "uncertain" not in opinion.lower():
            accuracy += 0.1

        # Creativity: Novel approaches and innovative solutions
        creativity = 0.4
        if any(word in opinion.lower() for word in ["alternative", "innovative", "novel", "creative"]):
            creativity += 0.4
        unique_words = len(set(opinion.lower().split()))
        total_words = len(opinion.split())
        if total_words > 0 and unique_words / total_words > 0.7:  # High lexical diversity
            creativity += 0.2

        # Reliability: Consistency and trustworthiness
        reliability = confidence
        if any(word in evidence.lower() for word in ["expertise", "proven", "tested", "reliable"]):
            reliability += 0.2
        if task_type == "decision_making" and "risk" in opinion.lower():
            reliability += 0.1

        # Efficiency: Conciseness and resource usage
        efficiency = 0.8
        word_count = len(opinion.split())
        if word_count < 5:
            efficiency -= 0.2  # Too brief
        elif word_count > 100:
            efficiency -= 0.3  # Too verbose
        if "step-by-step" in opinion.lower():
            efficiency += 0.1  # Structured approach

        return {
            "accuracy": min(accuracy, 1.0),
            "creativity": min(creativity, 1.0),
            "reliability": min(reliability, 1.0),
            "efficiency": min(efficiency, 1.0)
        }

    def get_scoring_weights(self, task_type: str) -> Dict[str, float]:
        """Get scoring weights based on task type"""
        weights = {
            "general": {"accuracy": 0.3, "creativity": 0.2, "reliability": 0.3, "efficiency": 0.2},
            "analysis": {"accuracy": 0.4, "creativity": 0.1, "reliability": 0.3, "efficiency": 0.2},
            "creative": {"accuracy": 0.2, "creativity": 0.4, "reliability": 0.2, "efficiency": 0.2},
            "decision_making": {"accuracy": 0.3, "creativity": 0.2, "reliability": 0.4, "efficiency": 0.1},
            "problem_solving": {"accuracy": 0.3, "creativity": 0.3, "reliability": 0.2, "efficiency": 0.2},
            "urgent": {"accuracy": 0.2, "creativity": 0.1, "reliability": 0.3, "efficiency": 0.4}
        }
        return weights.get(task_type, weights["general"])

class MiniCoordinator:
    """Temporary coordinator for handling complex subtask clusters"""

    def __init__(self, coordinator_id: str, parent_coordinator, cluster_tasks: List[Dict[str, Any]],
                 available_agents: List[str], level: int = 1):
        self.coordinator_id = coordinator_id
        self.parent_coordinator = parent_coordinator
        self.cluster_tasks = cluster_tasks
        self.available_agents = available_agents
        self.level = level
        self.active_subtasks = {}
        self.completed_results = {}
        self.status = "initialized"

    def execute_cluster(self) -> Dict[str, Any]:
        """Execute the subtask cluster and return results"""
        self.status = "executing"
        logger.log("INFO", f"MiniCoordinator-{self.level}", f"Starting cluster execution",
                  {"cluster_size": len(self.cluster_tasks), "level": self.level})

        # Plan and delegate subtasks within this cluster
        for i, task_info in enumerate(self.cluster_tasks):
            subtask_id = f"{self.coordinator_id}_sub_{i}"
            assigned_agent = self._select_agent_for_task(task_info)

            if assigned_agent:
                # Create subtask
                subtask_obj = Task(subtask_id, task_info["description"],
                                 {"priority": task_info.get("priority", 1), "level": self.level},
                                 assigned_agent)

                self.active_subtasks[subtask_id] = {
                    "task": subtask_obj,
                    "status": "assigned",
                    "assigned_at": time.time()
                }

                # Send to parent coordinator for actual agent assignment
                self.parent_coordinator.send_message(assigned_agent, MessageType.TASK_ASSIGNMENT,
                                                   {"task": subtask_obj})

        # Wait for completion (simplified - in real implementation would be event-driven)
        self.status = "waiting_for_completion"
        return {"status": "cluster_delegated", "subtasks": list(self.active_subtasks.keys())}

    def _select_agent_for_task(self, task_info: Dict[str, Any]) -> Optional[str]:
        """Select appropriate agent for task within this cluster"""
        task_desc = task_info["description"]

        # Use parent's agent selection logic
        return self.parent_coordinator.get_least_loaded_agent()

    def handle_subtask_completion(self, subtask_id: str, result: Any):
        """Handle completion of a subtask in this cluster"""
        if subtask_id in self.active_subtasks:
            self.active_subtasks[subtask_id]["status"] = "completed"
            self.active_subtasks[subtask_id]["completed_at"] = time.time()
            self.completed_results[subtask_id] = result

            # Check if cluster is complete
            if self._is_cluster_complete():
                self._finalize_cluster()

    def _is_cluster_complete(self) -> bool:
        """Check if all subtasks in cluster are completed"""
        return all(task["status"] == "completed" for task in self.active_subtasks.values())

    def _finalize_cluster(self):
        """Finalize cluster execution and report results"""
        self.status = "completed"

        # Synthesize cluster results
        cluster_results = {
            "cluster_id": self.coordinator_id,
            "level": self.level,
            "completed_subtasks": len(self.completed_results),
            "total_subtasks": len(self.cluster_tasks),
            "results": self.completed_results,
            "execution_time": time.time() - min(t["assigned_at"] for t in self.active_subtasks.values())
        }

        logger.log("INFO", f"MiniCoordinator-{self.level}", "Cluster execution completed", cluster_results)

        # Report back to parent coordinator
        self.parent_coordinator.handle_mini_coordinator_completion(self.coordinator_id, cluster_results)

class PredictiveLoadForecaster:
    """AI-based forecasting system for agent load prediction and proactive resource allocation"""

    def __init__(self, history_window: int = 50):
        self.history_window = history_window
        self.load_history: Dict[str, deque] = {}  # Agent load history
        self.task_completion_times: Dict[str, deque] = {}  # Task completion time history
        self.failure_patterns: Dict[str, Dict[str, Any]] = {}  # Failure prediction patterns
        self.forecast_cache: Dict[str, Dict[str, Any]] = {}  # Cached forecasts
        self.last_forecast_update = 0
        self.forecast_interval = 30  # Update forecasts every 30 seconds

    def record_load_change(self, agent_id: str, new_load: int, timestamp: float = None):
        """Record agent load change for forecasting"""
        if timestamp is None:
            timestamp = time.time()

        if agent_id not in self.load_history:
            self.load_history[agent_id] = deque(maxlen=self.history_window)

        self.load_history[agent_id].append({
            'load': new_load,
            'timestamp': timestamp
        })

    def record_task_completion(self, agent_id: str, task_type: str, completion_time: float):
        """Record task completion for performance forecasting"""
        if agent_id not in self.task_completion_times:
            self.task_completion_times[agent_id] = deque(maxlen=self.history_window)

        self.task_completion_times[agent_id].append({
            'task_type': task_type,
            'completion_time': completion_time,
            'timestamp': time.time()
        })

    def forecast_agent_load(self, agent_id: str, time_horizon: int = 300) -> Dict[str, Any]:
        """Forecast agent load for the next time_horizon seconds"""
        current_time = time.time()

        # Check cache
        cache_key = f"{agent_id}_{time_horizon}"
        if (cache_key in self.forecast_cache and
            current_time - self.forecast_cache[cache_key]['timestamp'] < self.forecast_interval):
            return self.forecast_cache[cache_key]

        if agent_id not in self.load_history or len(self.load_history[agent_id]) < 3:
            # Not enough data, return conservative estimate
            return {
                'agent_id': agent_id,
                'predicted_load': 0.5,  # Conservative estimate
                'confidence': 0.3,
                'time_horizon': time_horizon,
                'timestamp': current_time,
                'trend': 'unknown'
            }

        # Analyze load trend
        recent_loads = [entry['load'] for entry in list(self.load_history[agent_id])[-10:]]
        if len(recent_loads) >= 2:
            trend = 'increasing' if recent_loads[-1] > recent_loads[0] else 'decreasing' if recent_loads[-1] < recent_loads[0] else 'stable'
            avg_load = statistics.mean(recent_loads)
            load_variance = statistics.variance(recent_loads) if len(recent_loads) > 1 else 0
        else:
            trend = 'stable'
            avg_load = recent_loads[0] if recent_loads else 0
            load_variance = 0

        # Simple exponential smoothing forecast
        if len(recent_loads) >= 3:
            alpha = 0.3  # Smoothing factor
            forecast = recent_loads[-1] * alpha + avg_load * (1 - alpha)
        else:
            forecast = avg_load

        # Adjust forecast based on trend
        if trend == 'increasing':
            forecast *= 1.2  # Expect 20% increase
        elif trend == 'decreasing':
            forecast *= 0.8  # Expect 20% decrease

        # Calculate confidence based on data quality and variance
        data_points = len(self.load_history[agent_id])
        confidence = min(0.9, data_points / 20.0)  # More data = higher confidence
        if load_variance > 1:
            confidence *= 0.8  # High variance reduces confidence

        forecast_result = {
            'agent_id': agent_id,
            'predicted_load': max(0, min(forecast, 5)),  # Cap at reasonable maximum
            'confidence': confidence,
            'time_horizon': time_horizon,
            'timestamp': current_time,
            'trend': trend,
            'data_points': data_points,
            'avg_historical_load': avg_load
        }

        # Cache result
        self.forecast_cache[cache_key] = forecast_result
        return forecast_result

    def predict_task_failure_risk(self, agent_id: str, task_description: str, task_type: str = None) -> Dict[str, Any]:
        """Predict failure risk for a task based on agent history and task characteristics"""
        if agent_id not in self.failure_patterns:
            self.failure_patterns[agent_id] = {
                'total_tasks': 0,
                'failed_tasks': 0,
                'task_type_failures': {},
                'recent_failures': deque(maxlen=20)
            }

        pattern = self.failure_patterns[agent_id]

        # Analyze task description for risk factors
        risk_factors = self._analyze_task_risk_factors(task_description, task_type)

        # Calculate base failure rate from agent history
        base_failure_rate = pattern['failed_tasks'] / pattern['total_tasks'] if pattern['total_tasks'] > 0 else 0.1

        # Adjust for task type specific failures
        task_failure_rate = 0
        if task_type and task_type in pattern['task_type_failures']:
            task_stats = pattern['task_type_failures'][task_type]
            task_failure_rate = task_stats['failures'] / task_stats['attempts'] if task_stats['attempts'] > 0 else 0

        # Combine base rate with task-specific rate
        combined_failure_rate = (base_failure_rate * 0.7 + task_failure_rate * 0.3)

        # Adjust for risk factors
        risk_multiplier = 1.0
        for factor, weight in risk_factors.items():
            if factor == 'complexity_high':
                risk_multiplier *= 1.5
            elif factor == 'time_pressure':
                risk_multiplier *= 1.3
            elif factor == 'resource_intensive':
                risk_multiplier *= 1.2
            elif factor == 'novel_task':
                risk_multiplier *= 1.4

        predicted_risk = min(0.95, combined_failure_rate * risk_multiplier)

        # Calculate confidence in prediction
        data_points = pattern['total_tasks']
        confidence = min(0.8, data_points / 30.0)  # Need substantial history for good predictions

        return {
            'agent_id': agent_id,
            'task_description': task_description[:100],
            'predicted_failure_risk': predicted_risk,
            'confidence': confidence,
            'risk_factors': list(risk_factors.keys()),
            'base_failure_rate': base_failure_rate,
            'task_specific_rate': task_failure_rate,
            'recommendations': self._generate_failure_prevention_recommendations(predicted_risk, risk_factors)
        }

    def _analyze_task_risk_factors(self, task_description: str, task_type: str = None) -> Dict[str, float]:
        """Analyze task description for risk factors"""
        risk_factors = {}
        desc_lower = task_description.lower()

        # Complexity indicators
        complexity_keywords = ['complex', 'difficult', 'challenging', 'advanced', 'sophisticated']
        if any(word in desc_lower for word in complexity_keywords):
            risk_factors['complexity_high'] = 0.8

        # Time pressure indicators
        urgency_keywords = ['urgent', 'deadline', 'asap', 'immediate', 'rush']
        if any(word in desc_lower for word in urgency_keywords):
            risk_factors['time_pressure'] = 0.7

        # Resource intensity indicators
        resource_keywords = ['resource', 'memory', 'compute', 'intensive', 'heavy']
        if any(word in desc_lower for word in resource_keywords):
            risk_factors['resource_intensive'] = 0.6

        # Novelty indicators
        if task_type and len(task_description.split()) < 20:  # Short, potentially novel tasks
            risk_factors['novel_task'] = 0.5

        # Length-based complexity (very long tasks might be complex)
        if len(task_description.split()) > 100:
            risk_factors['complexity_high'] = max(risk_factors.get('complexity_high', 0), 0.6)

        return risk_factors

    def _generate_failure_prevention_recommendations(self, risk: float, risk_factors: Dict[str, float]) -> List[str]:
        """Generate recommendations to prevent task failures"""
        recommendations = []

        if risk > 0.7:
            recommendations.append("High failure risk - consider task decomposition")
        elif risk > 0.5:
            recommendations.append("Medium failure risk - monitor closely")

        if 'complexity_high' in risk_factors:
            recommendations.append("Break complex task into smaller subtasks")
            recommendations.append("Consider using specialized agent for complex tasks")

        if 'time_pressure' in risk_factors:
            recommendations.append("Reduce concurrent load to meet deadline")
            recommendations.append("Prioritize this task in queue")

        if 'resource_intensive' in risk_factors:
            recommendations.append("Ensure adequate resources before assignment")
            recommendations.append("Consider load balancing across multiple agents")

        if 'novel_task' in risk_factors:
            recommendations.append("Assign to agent with similar experience")
            recommendations.append("Consider additional validation steps")

        return recommendations

    def update_failure_history(self, agent_id: str, task_type: str, success: bool):
        """Update failure patterns with new task outcome"""
        if agent_id not in self.failure_patterns:
            self.failure_patterns[agent_id] = {
                'total_tasks': 0,
                'failed_tasks': 0,
                'task_type_failures': {},
                'recent_failures': deque(maxlen=20)
            }

        pattern = self.failure_patterns[agent_id]
        pattern['total_tasks'] += 1

        if not success:
            pattern['failed_tasks'] += 1
            pattern['recent_failures'].append({
                'timestamp': time.time(),
                'task_type': task_type
            })

        # Update task type specific stats
        if task_type not in pattern['task_type_failures']:
            pattern['task_type_failures'][task_type] = {'attempts': 0, 'failures': 0}

        pattern['task_type_failures'][task_type]['attempts'] += 1
        if not success:
            pattern['task_type_failures'][task_type]['failures'] += 1

    def get_predictive_insights(self) -> Dict[str, Any]:
        """Get comprehensive predictive insights for resource allocation"""
        insights = {
            'load_forecasts': {},
            'high_risk_agents': [],
            'resource_recommendations': [],
            'preventive_actions': []
        }

        # Generate load forecasts for all agents
        for agent_id in self.load_history.keys():
            forecast = self.forecast_agent_load(agent_id)
            insights['load_forecasts'][agent_id] = forecast

            # Identify high-risk agents
            if forecast['predicted_load'] > 3.5:  # Above 70% of typical max load
                insights['high_risk_agents'].append({
                    'agent_id': agent_id,
                    'predicted_load': forecast['predicted_load'],
                    'confidence': forecast['confidence'],
                    'recommendation': 'Reduce load or add capacity'
                })

        # Generate resource recommendations
        total_predicted_load = sum(f['predicted_load'] for f in insights['load_forecasts'].values())
        avg_predicted_load = total_predicted_load / len(insights['load_forecasts']) if insights['load_forecasts'] else 0

        if avg_predicted_load > 2.5:
            insights['resource_recommendations'].append("High overall load predicted - consider scaling up")
        elif avg_predicted_load < 1.0:
            insights['resource_recommendations'].append("Low load predicted - consider scaling down or adding tasks")

        # Generate preventive actions based on failure patterns
        for agent_id, pattern in self.failure_patterns.items():
            if pattern['total_tasks'] > 10:
                failure_rate = pattern['failed_tasks'] / pattern['total_tasks']
                if failure_rate > 0.3:
                    insights['preventive_actions'].append(f"Agent {agent_id} has high failure rate ({failure_rate:.1%}) - review task assignments")

        return insights

class PreventiveRetrySystem:
    """System for preventing task failures through proactive rerouting and resource allocation"""

    def __init__(self, forecaster: PredictiveLoadForecaster):
        self.forecaster = forecaster
        self.rerouting_history: Dict[str, List[Dict[str, Any]]] = {}
        self.preventive_actions_taken: deque = deque(maxlen=100)

    def should_reroute_task(self, agent_id: str, task_description: str, task_type: str = None) -> Dict[str, Any]:
        """Determine if a task should be rerouted to prevent failure"""
        # Get failure risk prediction
        risk_assessment = self.forecaster.predict_task_failure_risk(agent_id, task_description, task_type)

        # Get agent load forecast
        load_forecast = self.forecaster.forecast_agent_load(agent_id, time_horizon=600)  # 10 minutes

        # Decision criteria
        should_reroute = False
        reason = ""
        alternative_agent = None

        # High failure risk
        if risk_assessment['predicted_failure_risk'] > 0.6:
            should_reroute = True
            reason = f"High failure risk ({risk_assessment['predicted_failure_risk']:.1%})"

        # Agent overload predicted
        elif load_forecast['predicted_load'] > 3.5:  # Near capacity
            should_reroute = True
            reason = f"Agent overload predicted (load: {load_forecast['predicted_load']:.1f})"

        # Recent failure streak
        elif self._has_recent_failure_streak(agent_id):
            should_reroute = True
            reason = "Recent failure streak detected"

        if should_reroute:
            # Find alternative agent
            alternative_agent = self._find_alternative_agent(agent_id, task_description, task_type)

        return {
            'should_reroute': should_reroute,
            'reason': reason,
            'original_agent': agent_id,
            'alternative_agent': alternative_agent,
            'risk_assessment': risk_assessment,
            'load_forecast': load_forecast,
            'confidence': min(risk_assessment['confidence'], load_forecast['confidence'])
        }

    def _has_recent_failure_streak(self, agent_id: str, streak_length: int = 3) -> bool:
        """Check if agent has a recent streak of failures"""
        if agent_id not in self.forecaster.failure_patterns:
            return False

        recent_failures = list(self.forecaster.failure_patterns[agent_id]['recent_failures'])
        if len(recent_failures) < streak_length:
            return False

        # Check if last N tasks were failures
        recent_outcomes = recent_failures[-streak_length:]
        return len(recent_outcomes) >= streak_length

    def _find_alternative_agent(self, current_agent: str, task_description: str, task_type: str = None) -> Optional[str]:
        """Find alternative agent for task rerouting"""
        # This would need access to the coordinator's agent list
        # For now, return a placeholder - in real implementation would query coordinator
        return f"alternative_to_{current_agent}"

    def record_rerouting_action(self, original_agent: str, new_agent: str, task_id: str, reason: str):
        """Record a rerouting action for analytics"""
        action_record = {
            'timestamp': time.time(),
            'original_agent': original_agent,
            'new_agent': new_agent,
            'task_id': task_id,
            'reason': reason,
            'outcome': 'pending'  # Will be updated when task completes
        }

        if original_agent not in self.rerouting_history:
            self.rerouting_history[original_agent] = []

        self.rerouting_history[original_agent].append(action_record)
        self.preventive_actions_taken.append(action_record)

    def update_rerouting_outcome(self, task_id: str, success: bool):
        """Update the outcome of a rerouting action"""
        for agent_history in self.rerouting_history.values():
            for action in agent_history:
                if action['task_id'] == task_id:
                    action['outcome'] = 'success' if success else 'failure'

    def get_rerouting_effectiveness(self) -> Dict[str, Any]:
        """Analyze the effectiveness of rerouting actions"""
        total_actions = len(self.preventive_actions_taken)
        if total_actions == 0:
            return {'total_actions': 0, 'success_rate': 0, 'effectiveness': 'unknown'}

        successful_actions = sum(1 for action in self.preventive_actions_taken if action.get('outcome') == 'success')
        success_rate = successful_actions / total_actions

        effectiveness = 'highly_effective' if success_rate > 0.8 else 'effective' if success_rate > 0.6 else 'needs_improvement'

        return {
            'total_actions': total_actions,
            'successful_actions': successful_actions,
            'success_rate': success_rate,
            'effectiveness': effectiveness,
            'recent_trend': self._analyze_rerouting_trend()
        }

    def record_preventive_action(self, agent_id: str, task_id: str, action_type: str, reason: str):
        """Record a preventive action taken (simplification, etc.)"""
        action_record = {
            'timestamp': time.time(),
            'agent_id': agent_id,
            'task_id': task_id,
            'action_type': action_type,
            'reason': reason,
            'outcome': 'pending'  # Will be updated when task completes
        }

        self.preventive_actions_taken.append(action_record)

        # Keep only recent actions
        if len(self.preventive_actions_taken) > 100:
            self.preventive_actions_taken = self.preventive_actions_taken[-100:]

    def update_preventive_action_outcome(self, task_id: str, success: bool):
        """Update the outcome of preventive actions for a completed task"""
        for action in self.preventive_actions_taken:
            if action['task_id'] == task_id:
                action['outcome'] = 'success' if success else 'failure'

    def _analyze_rerouting_trend(self) -> str:
        """Analyze recent rerouting effectiveness trend"""
        recent_actions = list(self.preventive_actions_taken)[-20:]  # Last 20 actions
        if len(recent_actions) < 10:
            return 'insufficient_data'

        recent_success_rate = sum(1 for action in recent_actions if action.get('outcome') == 'success') / len(recent_actions)

        # Compare with overall success rate
        overall_success_rate = sum(1 for action in self.preventive_actions_taken if action.get('outcome') == 'success') / len(self.preventive_actions_taken)

        if recent_success_rate > overall_success_rate + 0.1:
            return 'improving'
        elif recent_success_rate < overall_success_rate - 0.1:
            return 'declining'
        else:
            return 'stable'

    def _infer_task_type(self, task_description: str) -> str:
        """Infer task type from description for predictive analytics"""
        desc_lower = task_description.lower()

        if any(word in desc_lower for word in ["analyze", "examine", "study", "review"]):
            return "analysis"
        elif any(word in desc_lower for word in ["create", "design", "plan", "develop"]):
            return "creative"
        elif any(word in desc_lower for word in ["calculate", "solve", "compute", "math"]):
            return "mathematical"
        elif any(word in desc_lower for word in ["decide", "choose", "evaluate", "assess"]):
            return "decision_making"
        elif any(word in desc_lower for word in ["simulate", "model", "predict", "forecast"]):
            return "simulation"
        elif any(word in desc_lower for word in ["communicate", "explain", "describe", "summarize"]):
            return "communication"
        else:
            return "general"

class RetryManager:
    """Manages task retries with exponential backoff and fault tolerance"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0, jitter: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.retry_history: Dict[str, List[Dict[str, Any]]] = {}
        self.circuit_breaker_state: Dict[str, Dict[str, Any]] = {}  # Agent circuit breaker states

    def should_retry(self, task_id: str, agent_id: str, error_type: str = "general") -> Dict[str, Any]:
        """Determine if a task should be retried and calculate backoff delay"""
        if task_id not in self.retry_history:
            self.retry_history[task_id] = []

        retry_count = len(self.retry_history[task_id])

        # Check circuit breaker for agent
        if self._is_circuit_breaker_open(agent_id):
            return {
                'should_retry': False,
                'reason': 'circuit_breaker_open',
                'circuit_breaker_info': self.circuit_breaker_state[agent_id]
            }

        # Check max retries
        if retry_count >= self.max_retries:
            return {
                'should_retry': False,
                'reason': 'max_retries_exceeded',
                'retry_count': retry_count
            }

        # Calculate exponential backoff delay
        delay = self._calculate_backoff_delay(retry_count)

        return {
            'should_retry': True,
            'delay': delay,
            'retry_count': retry_count + 1,
            'next_retry_time': time.time() + delay
        }

    def record_retry_attempt(self, task_id: str, agent_id: str, error_details: Dict[str, Any]):
        """Record a retry attempt for analytics and circuit breaker logic"""
        if task_id not in self.retry_history:
            self.retry_history[task_id] = []

        retry_record = {
            'timestamp': time.time(),
            'agent_id': agent_id,
            'error_details': error_details,
            'attempt_number': len(self.retry_history[task_id]) + 1
        }

        self.retry_history[task_id].append(retry_record)

        # Update circuit breaker state
        self._update_circuit_breaker(agent_id, error_details)

        # Log retry attempt
        from ..core.base import logger
        logger.log("WARNING", "RetryManager", f"Task retry attempt: {task_id} on agent {agent_id}",
                  {"attempt": retry_record['attempt_number'], "error": error_details.get('error_type', 'unknown')})

    def get_retry_statistics(self, task_id: str = None) -> Dict[str, Any]:
        """Get retry statistics for monitoring"""
        if task_id:
            task_retries = self.retry_history.get(task_id, [])
            return {
                'task_id': task_id,
                'total_retries': len(task_retries),
                'agents_attempted': list(set(r['agent_id'] for r in task_retries)),
                'error_types': [r['error_details'].get('error_type', 'unknown') for r in task_retries],
                'retry_history': task_retries
            }

        # Global statistics
        all_retries = []
        for task_retries in self.retry_history.values():
            all_retries.extend(task_retries)

        agent_failure_rates = {}
        for retry in all_retries:
            agent_id = retry['agent_id']
            if agent_id not in agent_failure_rates:
                agent_failure_rates[agent_id] = {'total_attempts': 0, 'failures': 0}
            agent_failure_rates[agent_id]['total_attempts'] += 1
            # Assume all retries are due to failures
            agent_failure_rates[agent_id]['failures'] += 1

        return {
            'total_retry_events': len(all_retries),
            'unique_tasks_retried': len(self.retry_history),
            'agent_failure_rates': agent_failure_rates,
            'circuit_breaker_states': self.circuit_breaker_state
        }

    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """Calculate exponential backoff delay with optional jitter"""
        delay = self.base_delay * (2 ** retry_count)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add random jitter (±25% of delay)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0.1, delay)  # Minimum 100ms delay

    def _is_circuit_breaker_open(self, agent_id: str) -> bool:
        """Check if circuit breaker is open for an agent"""
        if agent_id not in self.circuit_breaker_state:
            return False

        state = self.circuit_breaker_state[agent_id]
        if state['status'] == 'open':
            # Check if timeout has expired
            if time.time() - state['opened_at'] > state['timeout']:
                # Reset to half-open
                state['status'] = 'half_open'
                state['last_attempt'] = time.time()
                return False
            return True

        return False

    def _update_circuit_breaker(self, agent_id: str, error_details: Dict[str, Any]):
        """Update circuit breaker state based on error patterns"""
        if agent_id not in self.circuit_breaker_state:
            self.circuit_breaker_state[agent_id] = {
                'status': 'closed',
                'failure_count': 0,
                'success_count': 0,
                'last_failure': None,
                'opened_at': None,
                'timeout': 300,  # 5 minutes default timeout
                'failure_threshold': 5,  # Open after 5 consecutive failures
                'last_attempt': time.time()
            }

        state = self.circuit_breaker_state[agent_id]
        state['failure_count'] += 1
        state['last_failure'] = time.time()

        # Check if should open circuit breaker
        if state['failure_count'] >= state['failure_threshold']:
            state['status'] = 'open'
            state['opened_at'] = time.time()

            from ..core.base import logger
            logger.log("ERROR", "RetryManager", f"Circuit breaker opened for agent {agent_id}",
                      {"failure_count": state['failure_count'], "threshold": state['failure_threshold']})

    def record_success(self, agent_id: str):
        """Record successful task completion for circuit breaker recovery"""
        if agent_id in self.circuit_breaker_state:
            state = self.circuit_breaker_state[agent_id]
            state['success_count'] += 1
            state['failure_count'] = max(0, state['failure_count'] - 1)  # Gradually reduce failure count

            # Close circuit breaker if it was open/half-open and we have successes
            if state['status'] in ['open', 'half_open'] and state['success_count'] >= 2:
                state['status'] = 'closed'
                state['failure_count'] = 0

                from ..core.base import logger
                logger.log("INFO", "RetryManager", f"Circuit breaker closed for agent {agent_id}",
                          {"success_count": state['success_count']})

class SwarmCoordinator(BaseAgent):
    def __init__(self, agent_id: str, swarm_id: Optional[str] = None):
        super().__init__(agent_id, AgentRole.PREFRONTAL_CORTEX, swarm_id)
        self.planning_module = PlanningModule()
        self.delegation_system = DelegationSystem()
        self.critic_debate = CriticDebateConsensus()
        self.registered_agents = []
        self.working_memory = None
        self.long_term_memory = None
        self.agent_loads = {}  # Track agent workload
        self.max_agent_load = 3  # Maximum concurrent tasks per agent
        self.mini_coordinators = {}  # Track active mini-coordinators

        # Adaptive Task Broker for reinforcement learning-based routing
        self.adaptive_broker = AdaptiveTaskBroker(alpha=0.1, reward_window=50)

        # Fault tolerance and retry system
        self.retry_manager = RetryManager(max_retries=3, base_delay=2.0, max_delay=300.0)

        # Predictive control systems
        self.load_forecaster = PredictiveLoadForecaster()
        self.preventive_retry_system = PreventiveRetrySystem(self.load_forecaster)

        # Advanced predictive analytics
        self.task_completion_predictor = task_completion_predictor
        self.memory_bottleneck_predictor = memory_bottleneck_predictor
        self.failure_predictor = failure_predictor

        # Autonomous goal generation
        self.autonomous_goal_generator = None
        self.goal_generation_interval = 300  # Generate goals every 5 minutes
        self.last_goal_generation = 0

        # Dynamic load balancing
        self.load_balancer = DynamicLoadBalancer(self.load_forecaster, self)
        self.load_rebalancing_interval = 60  # Check for rebalancing every 60 seconds

        # Auto-scaling system
        self.auto_scaler = AutoScaler(self, self.load_forecaster)
        self.auto_scaling_interval = 90  # Check for scaling every 90 seconds
        self.last_load_rebalance = 0

    def register_agent(self, agent_id: str):
        """Register an agent with the coordinator"""
        if agent_id not in self.registered_agents:
            self.registered_agents.append(agent_id)
            # Register with adaptive broker for learning
            self.adaptive_broker.register_agent(agent_id)

    def set_memory_systems(self, working_memory, long_term_memory):
        """Set working and long-term memory systems"""
        self.working_memory = working_memory
        self.long_term_memory = long_term_memory

        # Initialize autonomous goal generator
        self.autonomous_goal_generator = initialize_autonomous_goals(long_term_memory, working_memory)

    def process_message(self, message: Message) -> Optional[Message]:
        """Process incoming messages from agents"""
        if message.message_type == MessageType.RESULT_REPORT:
            return self.handle_result_report(message)
        elif message.message_type == MessageType.DEBATE_CONTRIBUTION:
            return self.handle_debate_contribution(message)
        elif message.message_type == MessageType.SIMULATION_REQUEST:
            return self.handle_simulation_feedback(message)
        return None

    def receive_message_for_agent(self, agent_id: str, message: Message):
        """Receive a message for a specific agent in this swarm"""
        # This method allows the SwarmManager to deliver messages to specific agents
        # In a real implementation, this would look up the agent instance and call receive_message
        # For now, we'll handle it through the coordinator's message processing
        if agent_id in self.registered_agents:
            # Forward to the appropriate handler based on message type
            self.process_message(message)
        else:
            logger.log("WARNING", "SwarmCoordinator", f"Received message for unknown agent {agent_id} in swarm {self.swarm_id}")

    def handle_result_report(self, message: Message) -> Optional[Message]:
        """Handle task result reports from agents with incremental checkpointing, logging, and retry logic"""
        task_id = message.content.get("task_id")
        result = message.content.get("result")

        if task_id and self.delegation_system.active_tasks.get(task_id):
            task_info = self.delegation_system.active_tasks[task_id]
            assigned_agent = task_info["task"].assigned_agent

            # Determine if task was successful
            success = not any(word in str(result).lower() for word in ['failed', 'error', 'exception'])

            # Check if task failed and should be retried
            if not success:
                retry_decision = self.retry_manager.should_retry(task_id, assigned_agent, "task_failure")

                if retry_decision['should_retry']:
                    # Record retry attempt
                    self.retry_manager.record_retry_attempt(task_id, assigned_agent, {
                        'error_type': 'task_failure',
                        'result': str(result)[:200],
                        'attempt_number': retry_decision['retry_count']
                    })

                    # Schedule retry with backoff delay
                    retry_delay = retry_decision['delay']
                    logger.log("WARNING", "SwarmCoordinator", f"Scheduling retry for task {task_id} in {retry_delay:.1f}s",
                              {"agent": assigned_agent, "attempt": retry_decision['retry_count'], "reason": retry_decision.get('reason', 'unknown')})

                    # For now, immediately retry with different agent (simplified)
                    # In production, this would be scheduled asynchronously
                    alternative_agent = self._find_alternative_agent_for_retry(assigned_agent, task_info['task'].description)
                    if alternative_agent:
                        # Reassign to alternative agent
                        task_info["task"].assigned_agent = alternative_agent
                        self.delegation_system.active_tasks[task_id] = task_info

                        # Update load tracking
                        self.update_agent_load(assigned_agent, -1)  # Remove from old agent
                        self.update_agent_load(alternative_agent, 1)  # Add to new agent

                        # Resend task assignment
                        self.send_message(alternative_agent, MessageType.TASK_ASSIGNMENT, {"task": task_info["task"]})

                        logger.log("INFO", "SwarmCoordinator", f"Task {task_id} reassigned from {assigned_agent} to {alternative_agent} for retry",
                                  {"attempt": retry_decision['retry_count']})
                        return None  # Don't complete the task yet

                else:
                    # Max retries exceeded or circuit breaker open
                    logger.log("ERROR", "SwarmCoordinator", f"Task {task_id} failed permanently",
                              {"agent": assigned_agent, "reason": retry_decision.get('reason', 'unknown'), "attempts": retry_decision.get('retry_count', 0)})

            # Task completed successfully or max retries exceeded
            self.delegation_system.track_task_progress(task_id, "completed")

            # Update agent load (decrease)
            if assigned_agent:
                self.update_agent_load(assigned_agent, -1)

            # Record success for circuit breaker recovery
            if success:
                self.retry_manager.record_success(assigned_agent)

            # Record task completion for predictive analytics
            task_type = self._infer_task_type(task_info['task'].description)
            completion_time = time.time() - task_info.get("assigned_at", time.time())

            # Record for existing forecaster
            self.load_forecaster.record_task_completion(assigned_agent, task_type, completion_time)

            # Update adaptive broker with task outcome for learning
            resource_cost = 0.5  # Placeholder - could be calculated based on actual resource usage
            self.adaptive_broker.complete_task(task_id, success, completion_time, resource_cost)

            # Record for new comprehensive predictors
            self.task_completion_predictor.record_task_completion(
                task_id, task_type, assigned_agent, completion_time, success
            )

            # Record memory impact (simplified - would need actual memory monitoring)
            memory_delta = 0.05  # Placeholder - estimate memory impact
            self.memory_bottleneck_predictor.record_task_memory_impact(
                task_type, assigned_agent, memory_delta, completion_time
            )

            # Record agent health metrics
            health_metrics = {
                'last_task_duration': completion_time,
                'last_task_success': success,
                'task_type': task_type
            }
            self.failure_predictor.update_agent_health(assigned_agent, health_metrics)

            # Update preventive retry system with outcome
            self.preventive_retry_system.update_rerouting_outcome(task_id, success)

            # Also update any preventive actions (simplifications, etc.) for this task
            self.preventive_retry_system.update_preventive_action_outcome(task_id, success)

            # Record performance data for self-tuning system
            task_metrics = {
                'completion_time': completion_time,
                'success': success,
                'quality': final_quality if 'final_quality' in locals() else (0.8 if success else 0.3),
                'resource_usage': len(self.agent_loads) / max(len(self.registered_agents), 1),
                'complexity': self._assess_task_complexity(task_info['task'].description),
                'reasoning_depth_used': execution_state.get('adaptive_parameters', {}).get('reasoning_depth', 3) if 'execution_state' in locals() else 3,
                'branch_limit_used': execution_state.get('adaptive_parameters', {}).get('branch_limit', 3) if 'execution_state' in locals() else 3,
                'parallelism_achieved': len(self.delegation_system.active_tasks) / max(len(self.registered_agents), 1)
            }
            record_task_performance_for_tuning(task_metrics)

            # Log subtask completion
            from .base import logger
            logger.log_subtask(task_id, task_info.get("parent_task_id", "unknown"), assigned_agent,
                              f"Completed: {task_info['task'].description[:50]}...", "completed",
                              task_info.get("priority", 1), {"result_summary": str(result)[:100]})

            # Store result in working memory
            if self.working_memory:
                self.working_memory.store(f"task_result_{task_id}", result)

            # Checkpoint this subtask completion
            self._checkpoint_subtask_completion(task_id, task_id, result)

            # Check if all subtasks completed (for incremental execution)
            execution_state = self.working_memory.retrieve(f"execution_state_{task_id}") if self.working_memory else None
            if execution_state and not execution_state["pending_subtasks"]:
                # All subtasks completed, synthesize final result
                strategy = execution_state["strategy"]
                final_result = self.synthesize_final_result(task_id, strategy)

                # Mark execution as completed
                execution_state["status"] = "completed"
                execution_state["final_result"] = final_result
                execution_state["completed_at"] = time.time()
                if self.working_memory:
                    self.working_memory.store(f"execution_state_{task_id}", execution_state)

                # Track task performance
                task_start_time = getattr(self, f"_task_start_{task_id}", time.time())
                total_task_time = time.time() - task_start_time
                subtasks_completed = len(execution_state["completed_subtasks"])
                total_subtasks = subtasks_completed + len(execution_state["pending_subtasks"])
                final_quality = 0.8 if subtasks_completed == total_subtasks else 0.5  # Simple quality metric

                metrics.track_task_performance(task_id, strategy.get("task", ""), total_task_time,
                                             subtasks_completed, total_subtasks, final_quality)

                # Track strategy success for meta-learning
                task_type = strategy.get("task_type", "general")
                strategy_used = "incremental"  # New incremental strategy
                agents_used = list(set([t["task"].assigned_agent for t in self.delegation_system.active_tasks.values()
                                      if t["task"].assigned_agent]))
                success_score = final_quality

                metrics.track_strategy_success(task_type, strategy_used, success_score, agents_used, total_task_time)

                # Automated STM to LTM handoff
                if self.long_term_memory and self.working_memory:
                    self.automated_memory_handoff(task_id, strategy, final_result)

                    # Clean up intermediate results after task completion
                    self.working_memory.cleanup_task_intermediates(task_id, keep_top=2)

                return self.send_message("user", MessageType.RESULT_REPORT,
                                        {"task_id": task_id, "final_result": final_result})

        return None

    def handle_debate_contribution(self, message: Message) -> Optional[Message]:
        """Handle debate contributions"""
        # Process debate contribution and potentially trigger consensus
        return None

    def handle_simulation_feedback(self, message: Message) -> Optional[Message]:
        """Handle simulation feedback from imagination module"""
        feedback = message.content.get("feedback")
        emergent_feedback = message.content.get("emergent_feedback")

        if feedback:
            self.incorporate_imagination_feedback(feedback)
        if emergent_feedback:
            self.incorporate_emergent_feedback(emergent_feedback)
        return None

    def handle_mini_coordinator_completion(self, mini_coordinator_id: str, results: Dict[str, Any]):
        """Handle completion of a mini-coordinator cluster"""
        logger.log("INFO", "SwarmCoordinator", f"Mini-coordinator {mini_coordinator_id} completed",
                  {"results": results})

        # Store results and clean up
        if mini_coordinator_id in self.mini_coordinators:
            del self.mini_coordinators[mini_coordinator_id]

        # Store cluster results in working memory
        if self.working_memory:
            self.working_memory.store(f"cluster_result_{mini_coordinator_id}", results)

    def execute_task(self, task: Dict[str, Any]) -> Any:
        """Execute high-level task coordination with incremental execution, self-tuning parameters, and policy governance"""
        task_description = task.get("description", "")
        task_id = task.get("task_id", f"task_{int(time.time())}")

        # Policy evaluation before task execution
        task_policy_context = {
            'action': 'task_execution',
            'task_description': task_description,
            'task_type': task.get('type', 'general'),
            'user_id': task.get('user_id', 'system'),
            'priority': task.get('priority', 1),
            'data_types': self._extract_data_types(task_description),
            'resource_requirements': task.get('resource_requirements', 'medium'),
            'ethical_impact': self._assess_ethical_impact(task_description),
            'compliance_requirements': task.get('compliance_requirements', [])
        }

        policy_result = evaluate_task_policy(task_policy_context)
        policy_warnings = policy_result.get("warnings", [])

        if not policy_result.get("compliant", True):
            logger.log("ERROR", "SwarmCoordinator", f"Task denied by policy: {task_description}")
            return {
                "task_id": task_id,
                "status": "denied",
                "reason": "Policy violation",
                "policy_warnings": policy_warnings
            }
        elif policy_warnings:
            logger.log("WARNING", "SwarmCoordinator", f"Task approved with warnings: {policy_warnings}")

        # Check ethical alignment
        if not check_ethical_alignment(task_policy_context):
            logger.log("ERROR", "SwarmCoordinator", f"Task failed ethical alignment check: {task_description}")
            return {
                "task_id": task_id,
                "status": "denied",
                "reason": "Ethical alignment violation"
            }

        # Track task start time for performance metrics
        setattr(self, f"_task_start_{task_id}", time.time())

        # Get self-tuning parameters for this task
        task_context = {
            'complexity': self._assess_task_complexity(task_description),
            'time_pressure': 'urgent' in task_description.lower() or 'deadline' in task_description.lower(),
            'quality_requirement': 'high_quality' in task or 'detailed' in task_description.lower() and 'high' or 'medium',
            'parallelism_opportunity': self._detect_parallelism_opportunity(task_description),
            'resource_constrained': self._check_resource_constraints(),
            'exploration_needed': 'explore' in task_description.lower() or 'investigate' in task_description.lower()
        }

        # Apply self-tuning parameters
        reasoning_depth = get_adaptive_reasoning_depth(task_context)
        branch_limit = get_adaptive_branch_limits(task_context)

        logger.log("INFO", "SwarmCoordinator", f"Task execution started with adaptive parameters",
                  {"task_id": task_id, "reasoning_depth": reasoning_depth, "branch_limit": branch_limit,
                   "complexity": task_context['complexity']})

        # Generate strategy with adaptive parameters
        strategy = self.planning_module.generate_strategy(task_description, self.registered_agents)

        # Apply adaptive reasoning depth to strategy
        if 'max_depth' in strategy:
            strategy['max_depth'] = reasoning_depth
        if 'branch_limit' in strategy:
            strategy['branch_limit'] = branch_limit

        logger.log("INFO", "PlanningModule", "Strategy generated with adaptive parameters",
                  {"task_id": task_id, "subtasks": len(strategy.get("subtasks", [])),
                   "reasoning_depth": reasoning_depth, "branch_limit": branch_limit})

        # Store strategy in working memory
        if self.working_memory:
            self.working_memory.store(f"strategy_{task_id}", strategy)

        # Initialize incremental execution state with adaptive parameters
        execution_state = {
            "task_id": task_id,
            "strategy": strategy,
            "pending_subtasks": [],
            "completed_subtasks": [],
            "current_checkpoint": 0,
            "status": "initialized",
            "adaptive_parameters": {
                "reasoning_depth": reasoning_depth,
                "branch_limit": branch_limit,
                "task_context": task_context
            }
        }

        # Flatten all subtasks into a sequential execution queue
        for cluster in strategy["task_clusters"]:
            if cluster["requires_mini_coordinator"]:
                # For mini-coordinators, add the entire cluster as one executable unit
                execution_state["pending_subtasks"].append({
                    "type": "mini_coordinator",
                    "cluster": cluster,
                    "task_id": task_id
                })
            else:
                # Add individual subtasks
                for subtask in cluster["subtasks"]:
                    execution_state["pending_subtasks"].append({
                        "type": "single_subtask",
                        "subtask": subtask,
                        "task_id": task_id,
                        "agent_assignments": strategy["agent_assignments"]
                    })

        # Store execution state
        if self.working_memory:
            self.working_memory.store(f"execution_state_{task_id}", execution_state)

        # Start incremental execution
        self._execute_next_subtask(task_id)

        return {"task_id": task_id, "strategy": strategy, "status": "incremental_execution_started"}

    def _execute_next_subtask(self, task_id: str):
        """Execute the next pending subtask in the incremental execution queue"""
        execution_state = self.working_memory.retrieve(f"execution_state_{task_id}") if self.working_memory else None
        if not execution_state or not execution_state["pending_subtasks"]:
            logger.log("INFO", "SwarmCoordinator", f"No more subtasks for task {task_id}")
            return

        # Get next subtask
        next_subtask = execution_state["pending_subtasks"].pop(0)
        execution_state["current_checkpoint"] += 1

        logger.log("INFO", "SwarmCoordinator", f"Executing subtask {execution_state['current_checkpoint']} for task {task_id}",
                  {"subtask_type": next_subtask["type"]})

        if next_subtask["type"] == "mini_coordinator":
            # Execute mini-coordinator cluster
            cluster = next_subtask["cluster"]
            mini_coord = MiniCoordinator(
                cluster["cluster_id"],
                self,
                cluster["subtasks"],
                self.registered_agents,
                level=1
            )
            self.mini_coordinators[cluster["cluster_id"]] = mini_coord
            mini_coord.execute_cluster()

        elif next_subtask["type"] == "single_subtask":
            # Execute single subtask
            self._delegate_single_subtask(
                next_subtask["subtask"],
                next_subtask["task_id"],
                next_subtask["agent_assignments"]
            )

        # Update execution state
        execution_state["status"] = "executing"
        if self.working_memory:
            self.working_memory.store(f"execution_state_{task_id}", execution_state)

    def _checkpoint_subtask_completion(self, task_id: str, subtask_id: str, result: Any):
        """Store checkpoint after subtask completion"""
        execution_state = self.working_memory.retrieve(f"execution_state_{task_id}") if self.working_memory else None
        if not execution_state:
            return

        # Add to completed subtasks
        execution_state["completed_subtasks"].append({
            "subtask_id": subtask_id,
            "result": result,
            "completed_at": time.time(),
            "checkpoint": execution_state["current_checkpoint"]
        })

        # Store checkpoint in working memory
        checkpoint_data = {
            "task_id": task_id,
            "subtask_id": subtask_id,
            "result": result,
            "execution_state": execution_state,
            "timestamp": time.time()
        }

        if self.working_memory:
            self.working_memory.store(f"checkpoint_{task_id}_{execution_state['current_checkpoint']}", checkpoint_data)

        # Store in long-term memory for important checkpoints
        if self.long_term_memory and execution_state["current_checkpoint"] % 3 == 0:  # Every 3rd checkpoint
            self.long_term_memory.store(f"checkpoint_{task_id}_{execution_state['current_checkpoint']}", checkpoint_data, {"type": "episodic"})

        logger.log("INFO", "SwarmCoordinator", f"Checkpoint stored for subtask {subtask_id}",
                  {"checkpoint": execution_state["current_checkpoint"], "task_id": task_id})

        # Update execution state
        if self.working_memory:
            self.working_memory.store(f"execution_state_{task_id}", execution_state)

        # Continue with next subtask
        self._execute_next_subtask(task_id)

    def _delegate_single_subtask(self, subtask: Dict[str, Any], parent_task_id: str, agent_assignments: Dict[str, str]):
        """Delegate a single subtask directly with predictive control and comprehensive logging"""
        subtask_desc = subtask["description"]
        priority = subtask.get("priority", 1)

        # Check resource availability for high-priority tasks
        if priority >= 3 and not self.check_resource_availability():
            return  # Skip if resources not available

        # Perform dynamic load balancing check before assignment
        self._check_dynamic_load_balancing()

        # Check for auto-scaling needs
        self._check_auto_scaling()

        # Use adaptive broker for intelligent task routing
        task_type = self._infer_task_type(subtask_desc)
        assigned_agent = self.adaptive_broker.assign_task(
            subtask_id, subtask_desc, self.registered_agents, task_type
        )

        # Fallback to traditional methods if adaptive broker fails
        if not assigned_agent:
            assigned_agent = self.get_least_loaded_agent()
            if not assigned_agent:
                assigned_agent = self.delegation_system.assign_subtask(
                    subtask_desc, self.registered_agents, agent_assignments
                )

        if assigned_agent:
            # Predictive control: Check if task should be rerouted to prevent failure
            task_type = self._infer_task_type(subtask_desc)
            rerouting_decision = self.preventive_retry_system.should_reroute_task(
                assigned_agent, subtask_desc, task_type
            )

            if rerouting_decision['should_reroute']:
                if rerouting_decision['alternative_agent']:
                    # Reroute to alternative agent
                    original_agent = assigned_agent
                    assigned_agent = rerouting_decision['alternative_agent']

                    logger.log("INFO", "SwarmCoordinator", f"Preventive rerouting: {original_agent} -> {assigned_agent}",
                               {"reason": rerouting_decision['reason'], "task_id": parent_task_id})

                    # Record the rerouting action
                    subtask_id_temp = f"{parent_task_id}_temp_{len(self.delegation_system.active_tasks)}"
                    self.preventive_retry_system.record_rerouting_action(
                        original_agent, assigned_agent, subtask_id_temp, rerouting_decision['reason']
                    )
                else:
                    # No alternative agent available - try task simplification
                    simplified_task = self._simplify_high_risk_task(subtask, rerouting_decision['risk_assessment'])
                    if simplified_task:
                        subtask_desc = simplified_task['description']
                        priority = simplified_task.get('priority', priority)

                        logger.log("INFO", "SwarmCoordinator", f"Task simplification applied for high-risk task",
                                   {"original": subtask['description'][:50], "simplified": subtask_desc[:50],
                                    "risk": rerouting_decision['risk_assessment']['predicted_failure_risk']})

                        # Record simplification action
                        self.preventive_retry_system.record_preventive_action(
                            assigned_agent, f"{parent_task_id}_simplified", "task_simplification",
                            f"Simplified high-risk task (risk: {rerouting_decision['risk_assessment']['predicted_failure_risk']:.1%})"
                        )

            subtask_id = f"{parent_task_id}_simple_{len(self.delegation_system.active_tasks)}"
            subtask_obj = Task(subtask_id, subtask_desc, {"priority": priority}, assigned_agent)

            self.delegation_system.active_tasks[subtask_id] = {
                "task": subtask_obj,
                "status": "assigned",
                "assigned_at": time.time(),
                "priority": priority
            }

            # Log subtask delegation with predictive control info
            from ..core.base import logger
            delegation_metadata = {
                "subtask_type": "single",
                "coordinator_decision": True,
                "predictive_control_used": rerouting_decision['should_reroute'],
                "rerouting_reason": rerouting_decision.get('reason', None)
            }

            from ..core.base import logger
            logger.log_subtask(subtask_id, parent_task_id, assigned_agent,
                               f"Delegated: {subtask_desc[:50]}...", "assigned", priority,
                               delegation_metadata)

            self.update_agent_load(assigned_agent, 1)
            self.send_message(assigned_agent, MessageType.TASK_ASSIGNMENT, {"task": subtask_obj})

    def check_resource_availability(self) -> bool:
        """Check if resources are available for new high-priority tasks"""
        active_high_priority = sum(1 for task_info in self.delegation_system.active_tasks.values()
                                  if task_info.get("priority", 1) >= 3)
        max_concurrent_high_priority = 2  # Limit concurrent high-priority tasks
        return active_high_priority < max_concurrent_high_priority

    def get_least_loaded_agent(self, required_expertise: str = None) -> Optional[str]:
        """Get the least loaded agent, optionally with required expertise"""
        available_agents = []
        for agent_id in self.registered_agents:
            current_load = self.agent_loads.get(agent_id, 0)
            if current_load < self.max_agent_load:
                # Check expertise if required
                if required_expertise:
                    agent_expertise = self.planning_module.assign_agents_to_subtasks([agent_id])
                    if required_expertise in agent_expertise.get(agent_id, []):
                        available_agents.append((agent_id, current_load))
                else:
                    available_agents.append((agent_id, current_load))

        if not available_agents:
            return None

        # Return agent with lowest load
        available_agents.sort(key=lambda x: x[1])
        return available_agents[0][0]

    def update_agent_load(self, agent_id: str, increment: int = 1):
        """Update agent load (positive to increase, negative to decrease)"""
        old_load = self.agent_loads.get(agent_id, 0)
        new_load = old_load + increment

        self.agent_loads[agent_id] = new_load
        if self.agent_loads[agent_id] <= 0:
            self.agent_loads.pop(agent_id, None)

        # Record load change for forecasting
        self.load_forecaster.record_load_change(agent_id, new_load if new_load > 0 else 0)

    def get_load_balance_report(self) -> Dict[str, Any]:
        """Get load balancing statistics"""
        total_load = sum(self.agent_loads.values())
        avg_load = total_load / len(self.registered_agents) if self.registered_agents else 0

        return {
            "total_agents": len(self.registered_agents),
            "total_load": total_load,
            "average_load": avg_load,
            "agent_loads": self.agent_loads.copy(),
            "load_distribution": "balanced" if avg_load <= self.max_agent_load * 0.8 else "high"
        }

    def all_subtasks_completed(self, strategy: Dict[str, Any]) -> bool:
        """Check if all hierarchical subtasks are completed"""
        return self.check_hierarchical_completion(strategy["subtasks"])

    def check_hierarchical_completion(self, subtasks: List[Dict[str, Any]]) -> bool:
        """Recursively check if hierarchical subtasks are completed"""
        for subtask_info in subtasks:
            subtask_desc = subtask_info["description"]
            # Find the task ID for this subtask (simplified matching)
            matching_tasks = [tid for tid, tinfo in self.delegation_system.active_tasks.items()
                            if tinfo["task"].description == subtask_desc]

            if not matching_tasks:
                return False  # Task not found

            task_id = matching_tasks[0]
            if self.delegation_system.active_tasks[task_id]["status"] != "completed":
                return False

            # Check child subtasks recursively
            if subtask_info.get("subtasks") and not self.check_hierarchical_completion(subtask_info["subtasks"]):
                return False

        return True

    def synthesize_final_result(self, task_id: str, strategy: Dict[str, Any]) -> Any:
        """Synthesize final result from completed hierarchical subtasks"""
        results = self.collect_hierarchical_results(strategy["subtasks"], task_id)

        # Conduct debate for consensus if multiple results
        if len(results) > 1:
            task_type = "general"  # Could be inferred from task_description
            debate_result = self.critic_debate.conduct_debate(
                f"Consensus for task {task_id}",
                self.registered_agents[:3],  # Use first 3 agents for debate
                {"results": results, "task_type": task_type}
            )
            # Store debate result in working and long-term memory
            if self.working_memory:
                self.working_memory.store(f"debate_result_{task_id}", debate_result)
            if self.long_term_memory:
                self.long_term_memory.store(f"debate_{task_id}", {
                    "topic": debate_result.topic,
                    "consensus": debate_result.consensus,
                    "contributions": debate_result.contributions
                }, {"type": "episodic"})
            return debate_result.consensus
        elif results:
            return results[0]
        else:
            return "No results available"

    def collect_hierarchical_results(self, subtasks: List[Dict[str, Any]], parent_task_id: str) -> List[Any]:
        """Recursively collect results from hierarchical subtasks"""
        results = []
        for i, subtask_info in enumerate(subtasks):
            subtask_desc = subtask_info["description"]
            level = subtask_info.get("level", 0)
            subtask_id = f"{parent_task_id}_sub_{level}_{i}"

            result = self.working_memory.retrieve(f"task_result_{subtask_id}") if self.working_memory else None
            if result:
                results.append(result)

            # Collect from child subtasks
            if subtask_info.get("subtasks"):
                child_results = self.collect_hierarchical_results(subtask_info["subtasks"], subtask_id)
                results.extend(child_results)

        return results
    def review_past_tasks(self) -> Dict[str, Any]:
        """Periodically evaluate LTM for patterns and improvements"""
        if not self.long_term_memory:
            return {"patterns": [], "improvements": []}

        # Search for completed tasks and reflections
        completed_tasks = self.long_term_memory.search("completed_task")
        reflections = self.long_term_memory.search("reflection")

        patterns = self.analyze_patterns(completed_tasks)
        improvements = self.identify_improvements(reflections)

        return {"patterns": patterns, "improvements": improvements}

    def adjust_delegation_strategy(self, performance_data: Dict[str, Any]):
        """Optimize agent assignments based on past performance"""
        # Update agent expertise based on performance
        for agent, performance in performance_data.items():
            if performance > 0.8:  # High performance
                # Increase priority for this agent type
                pass  # Mock implementation
        return "Delegation strategy adjusted"

    def update_planning_module(self, lessons: List[str]):
        """Refine high-level strategies using lessons from LTM"""
        for lesson in lessons:
            if "complex" in lesson.lower():
                # Adjust complexity estimation
                pass
            if "urgent" in lesson.lower():
                # Adjust risk assessment
                pass
        return "Planning module updated with lessons"

    def analyze_patterns(self, tasks: List[Any]) -> List[str]:
        """Analyze patterns from completed tasks (mock implementation)"""
        patterns = []
        if len(tasks) > 5:
            patterns.append("High task volume detected")
        return patterns

    def identify_improvements(self, reflections: List[Any]) -> List[str]:
        """Identify improvements from reflections (mock implementation)"""
        improvements = []
        for reflection in reflections:
            if isinstance(reflection, dict) and "lesson" in reflection:
                improvements.append(reflection["lesson"])
        return improvements

    def perform_periodic_meta_learning_update(self):
        """Perform periodic meta-learning updates and heuristic adaptation"""
        adaptations = metrics.adapt_heuristics_from_meta_learning()

        if adaptations:
            logger.log("INFO", "SwarmCoordinator", "Applied meta-learning adaptations",
                      {"adaptations": adaptations})

            # Update planning module with learned preferences
            for adaptation_key, description in adaptations.items():
                if "prefer_" in adaptation_key:
                    strategy_name = adaptation_key.replace("prefer_", "")
                    # Increase weight for successful strategies
                    if hasattr(self.planning_module, 'strategy_weights'):
                        task_type = strategy_name.split("_")[0]
                        if task_type in self.planning_module.strategy_weights:
                            self.planning_module.strategy_weights[task_type] = min(
                                1.0, self.planning_module.strategy_weights[task_type] + 0.1
                            )

    def get_predictive_control_insights(self) -> Dict[str, Any]:
        """Get comprehensive predictive control insights"""
        return {
            'load_forecasts': {agent_id: self.load_forecaster.forecast_agent_load(agent_id)
                             for agent_id in self.registered_agents},
            'preventive_actions': self.preventive_retry_system.get_rerouting_effectiveness(),
            'resource_recommendations': self._generate_resource_recommendations(),
            'system_health_predictions': self._predict_system_health()
        }

    def get_comprehensive_predictive_insights(self, upcoming_tasks: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get comprehensive predictive analytics including task completion, memory, and failure predictions"""
        insights = {
            'task_completion_predictions': {},
            'memory_bottleneck_predictions': {},
            'failure_predictions': {},
            'system_state': self._get_current_system_state(),
            'load_balancing_status': self.load_balancer.get_load_balancing_stats(),
            'auto_scaling_status': self.auto_scaler.get_scaling_metrics(),
            'self_tuning_status': get_self_tuning_status(),
            'autonomous_goals': self.get_autonomous_goals(5),  # Top 5 goals
            'goal_statistics': get_goal_statistics() if self.autonomous_goal_generator else {},
            'governance_status': get_governance_status(),
            'retry_statistics': self.retry_manager.get_retry_statistics(),
            'adaptive_broker_performance': self.adaptive_broker.get_performance_report(),
            'recommendations': [],
            'risk_assessment': {},
            'timestamp': time.time()
        }

        # Task completion predictions for upcoming tasks
        if upcoming_tasks:
            for task in upcoming_tasks:
                task_desc = task.get('description', '')
                task_type = task.get('type', self._infer_task_type(task_desc))
                agent_id = task.get('assigned_agent', self.get_least_loaded_agent())

                if agent_id:
                    prediction = self.task_completion_predictor.predict_completion_time(
                        task_desc, task_type, agent_id, self.agent_loads.get(agent_id, 0)
                    )
                    insights['task_completion_predictions'][f"{task.get('task_id', 'unknown')}"] = prediction

        # Memory bottleneck predictions
        if upcoming_tasks:
            memory_prediction = self.memory_bottleneck_predictor.predict_memory_bottleneck(
                self.registered_agents[0] if self.registered_agents else 'unknown',
                upcoming_tasks
            )
            insights['memory_bottleneck_predictions'] = memory_prediction

        # Failure predictions for agents
        for agent_id in self.registered_agents:
            task_context = {'task_type': 'general', 'complexity': 1.0}  # Default context
            system_state = insights['system_state']
            failure_prediction = self.failure_predictor.predict_potential_failures(
                agent_id, task_context, system_state
            )
            insights['failure_predictions'][agent_id] = failure_prediction

        # Generate overall recommendations
        insights['recommendations'] = self._generate_comprehensive_recommendations(insights)

        # Risk assessment
        insights['risk_assessment'] = self._assess_overall_system_risk(insights)

        return insights

    def _get_current_system_state(self) -> Dict[str, Any]:
        """Get current system state for predictive analysis"""
        return {
            'system_load': sum(self.agent_loads.values()) / max(len(self.registered_agents), 1),
            'agent_loads': self.agent_loads.copy(),
            'active_tasks': len(self.delegation_system.active_tasks),
            'memory_pressure': 0.5,  # Placeholder - would integrate with actual memory monitoring
            'total_agents': len(self.registered_agents)
        }

    def _generate_comprehensive_recommendations(self, insights: Dict[str, Any]) -> List[str]:
        """Generate comprehensive recommendations based on all predictive insights"""
        recommendations = []

        # Task completion recommendations
        completion_preds = insights.get('task_completion_predictions', {})
        long_running_tasks = [
            task_id for task_id, pred in completion_preds.items()
            if pred.get('predicted_time', 0) > 300  # Over 5 minutes
        ]
        if long_running_tasks:
            recommendations.append(f"Consider breaking down long-running tasks: {', '.join(long_running_tasks[:3])}")

        # Memory recommendations
        memory_pred = insights.get('memory_bottleneck_predictions', {})
        if memory_pred.get('bottleneck_predicted'):
            recommendations.append("Memory bottleneck predicted - consider task sequencing or resource allocation")
            recommendations.extend(memory_pred.get('recommendations', [])[:2])

        # Failure recommendations
        failure_preds = insights.get('failure_predictions', {})
        high_risk_agents = [
            agent_id for agent_id, pred in failure_preds.items()
            if pred.get('overall_risk', 0) > 0.3
        ]
        if high_risk_agents:
            recommendations.append(f"High failure risk for agents: {', '.join(high_risk_agents)} - consider load redistribution")

        # System-level recommendations
        system_state = insights.get('system_state', {})
        if system_state.get('system_load', 0) > 2.0:
            recommendations.append("High system load detected - consider scaling or task prioritization")

        return recommendations[:5]  # Limit to top 5 recommendations

    def _check_dynamic_load_balancing(self):
        """Check if dynamic load balancing is needed and perform it"""
        current_time = time.time()
        if current_time - self.last_load_rebalance > self.load_rebalancing_interval:
            rebalance_result = self.load_balancer.check_and_rebalance_load()
            if rebalance_result['action'] != 'no_action':
                logger.log("INFO", "SwarmCoordinator", f"Dynamic load balancing: {rebalance_result['message']}")
                if rebalance_result.get('rebalance_actions'):
                    for action in rebalance_result['rebalance_actions']:
                        logger.log("INFO", "SwarmCoordinator", f"Load rebalanced: {action['from_agent']} -> {action['to_agent']} ({action['task_id']})")
            self.last_load_rebalance = current_time

    def _check_auto_scaling(self):
        """Check if auto-scaling is needed and perform it"""
        current_time = time.time()
        if hasattr(self, 'last_auto_scale_check'):
            if current_time - self.last_auto_scale_check < self.auto_scaling_interval:
                return
        else:
            self.last_auto_scale_check = 0

        scaling_result = self.auto_scaler.check_scaling_needed()
        if scaling_result['action'] != 'no_action':
            logger.log("INFO", "SwarmCoordinator", f"Auto-scaling: {scaling_result['message']}")
            if scaling_result['action'] in ['scaled_up', 'scaled_down']:
                # Log agent changes
                if 'agents_added' in scaling_result:
                    for agent_id in scaling_result['agents_added']:
                        logger.log("INFO", "SwarmCoordinator", f"Agent added: {agent_id}")
                if 'agents_removed' in scaling_result:
                    for agent_id in scaling_result['agents_removed']:
                        logger.log("INFO", "SwarmCoordinator", f"Agent removed: {agent_id}")

        self.last_auto_scale_check = current_time

    def check_autonomous_goal_generation(self):
        """Check if autonomous goals should be generated"""
        current_time = time.time()
        if (self.autonomous_goal_generator and
            current_time - self.last_goal_generation > self.goal_generation_interval):
            try:
                context = self._get_current_system_context()
                goals = self.autonomous_goal_generator.generate_autonomous_goals(context)

                if goals:
                    logger.log("INFO", "SwarmCoordinator", f"Generated {len(goals)} autonomous goals")
                    # Store goals in working memory for access
                    if self.working_memory:
                        self.working_memory.store("autonomous_goals", goals, {"type": "goals", "timestamp": current_time})

                self.last_goal_generation = current_time
                return goals
            except Exception as e:
                logger.log("ERROR", "SwarmCoordinator", f"Failed to generate autonomous goals: {str(e)}")
                return []
        return []

    def get_autonomous_goals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get currently available autonomous goals"""
        if self.working_memory:
            goals = self.working_memory.retrieve("autonomous_goals") or []
            # Sort by priority and return top N
            goals.sort(key=lambda x: x.get('calculated_priority', 0), reverse=True)
            return goals[:limit]
        return []

    def _infer_task_type(self, task_description: str) -> str:
        """Infer task type from description for predictive analytics"""
        desc_lower = task_description.lower()

        if any(word in desc_lower for word in ["analyze", "examine", "study", "review"]):
            return "analysis"
        elif any(word in desc_lower for word in ["create", "design", "plan", "develop"]):
            return "creative"
        elif any(word in desc_lower for word in ["calculate", "solve", "compute", "math"]):
            return "mathematical"
        elif any(word in desc_lower for word in ["decide", "choose", "evaluate", "assess"]):
            return "decision_making"
        elif any(word in desc_lower for word in ["simulate", "model", "predict", "forecast"]):
            return "simulation"
        elif any(word in desc_lower for word in ["communicate", "explain", "describe", "summarize"]):
            return "communication"
        else:
            return "general"

    def approve_autonomous_goal(self, goal_id: str) -> bool:
        """Approve an autonomous goal for implementation"""
        goals = self.get_autonomous_goals(100)  # Get all available goals
        goal = next((g for g in goals if g['id'] == goal_id), None)

        if goal:
            # Create a task from the goal
            task_description = f"Autonomous Goal: {goal['title']}\n\n{goal['description']}\n\nProposed Actions:\n" + "\n".join(f"- {action}" for action in goal.get('proposed_actions', []))

            # Execute as a new task
            task = {
                "description": task_description,
                "task_id": f"autonomous_{goal_id}",
                "priority": goal.get('priority', 3),
                "autonomous_origin": True,
                "goal_data": goal
            }

            result = self.execute_task(task)
            logger.log("INFO", "SwarmCoordinator", f"Approved autonomous goal: {goal['title']}")
            return True

        return False

    def reject_autonomous_goal(self, goal_id: str, reason: str = "User rejected") -> bool:
        """Reject an autonomous goal"""
        goals = self.get_autonomous_goals(100)
        goal = next((g for g in goals if g['id'] == goal_id), None)

        if goal:
            logger.log("INFO", "SwarmCoordinator", f"Rejected autonomous goal: {goal['title']} - {reason}")
            # Could store rejection feedback for learning
            return True

        return False

    def _get_current_system_context(self) -> Dict[str, Any]:
        """Get current system context for goal generation"""
        return {
            'agent_count': len(self.registered_agents),
            'current_load': sum(self.agent_loads.values()) / max(len(self.registered_agents), 1),
            'active_tasks': len(self.delegation_system.active_tasks),
            'recent_performance': self._get_recent_performance_summary(),
            'system_health': self._predict_system_health(),
            'time_since_last_goal_generation': time.time() - self.last_goal_generation
        }

    def _get_recent_performance_summary(self) -> Dict[str, Any]:
        """Get summary of recent system performance"""
        # This would analyze recent task performance
        # For now, return basic metrics
        return {
            'avg_completion_time': 120,  # Mock data
            'success_rate': 0.85,
            'active_tasks': len(self.delegation_system.active_tasks),
            'agent_utilization': sum(self.agent_loads.values()) / max(len(self.registered_agents), 1)
        }

    def _assess_overall_system_risk(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall system risk based on all predictive insights"""
        risk_factors = []

        # Memory risk
        memory_pred = insights.get('memory_bottleneck_predictions', {})
        if memory_pred.get('bottleneck_predicted'):
            risk_factors.append({
                'type': 'memory_bottleneck',
                'severity': 'high' if memory_pred.get('max_projected_utilization', 0) > 0.9 else 'medium',
                'description': 'Memory bottleneck predicted in upcoming tasks'
            })

        # Agent failure risk
        failure_preds = insights.get('failure_predictions', {})
        high_risk_count = sum(1 for pred in failure_preds.values() if pred.get('overall_risk', 0) > 0.3)
        if high_risk_count > 0:
            risk_factors.append({
                'type': 'agent_failures',
                'severity': 'high' if high_risk_count > len(failure_preds) * 0.5 else 'medium',
                'description': f'{high_risk_count} agents at high failure risk'
            })

        # System load risk
        system_state = insights.get('system_state', {})
        system_load = system_state.get('system_load', 0)
        if system_load > 2.5:
            risk_factors.append({
                'type': 'system_overload',
                'severity': 'high',
                'description': 'System operating near capacity'
            })

        overall_risk_level = 'low'
        if any(f['severity'] == 'high' for f in risk_factors):
            overall_risk_level = 'high'
        elif risk_factors:
            overall_risk_level = 'medium'

        return {
            'overall_risk_level': overall_risk_level,
            'risk_factors': risk_factors,
            'mitigation_priority': 'high' if overall_risk_level == 'high' else 'medium' if overall_risk_level == 'medium' else 'low'
        }

    def _generate_resource_recommendations(self) -> List[str]:
        """Generate resource allocation recommendations based on predictive analytics"""
        recommendations = []

        # Analyze load forecasts
        forecasts = {agent_id: self.load_forecaster.forecast_agent_load(agent_id)
                    for agent_id in self.registered_agents}

        high_load_agents = [agent for agent, forecast in forecasts.items()
                          if forecast['predicted_load'] > 3.5]

        if high_load_agents:
            recommendations.append(f"High load predicted for agents: {', '.join(high_load_agents)} - consider load balancing")

        # Check for overall system load
        total_predicted_load = sum(f['predicted_load'] for f in forecasts.values())
        if total_predicted_load > len(self.registered_agents) * 2.5:
            recommendations.append("System approaching high load - prepare for scaling")

        # Check preventive system effectiveness
        rerouting_effectiveness = self.preventive_retry_system.get_rerouting_effectiveness()
        if rerouting_effectiveness.get('effectiveness') == 'needs_improvement':
            recommendations.append("Preventive rerouting effectiveness needs improvement - review failure patterns")

        return recommendations

    def _predict_system_health(self) -> Dict[str, Any]:
        """Predict overall system health based on current trends"""
        # Simple health prediction based on current metrics
        current_loads = list(self.agent_loads.values())
        avg_load = sum(current_loads) / len(current_loads) if current_loads else 0

        health_score = 1.0
        if avg_load > 2.5:
            health_score -= 0.3
        if avg_load > 3.5:
            health_score -= 0.4

        # Factor in failure rates from forecaster
        high_failure_agents = []
        for agent_id in self.registered_agents:
            if agent_id in self.load_forecaster.failure_patterns:
                pattern = self.load_forecaster.failure_patterns[agent_id]
                if pattern['total_tasks'] > 5:
                    failure_rate = pattern['failed_tasks'] / pattern['total_tasks']
                    if failure_rate > 0.3:
                        high_failure_agents.append(agent_id)
                        health_score -= 0.2

        return {
            'predicted_health_score': max(0.1, health_score),
            'high_failure_agents': high_failure_agents,
            'load_status': 'high' if avg_load > 3 else 'medium' if avg_load > 2 else 'low',
            'recommendations': self._generate_health_recommendations(health_score, high_failure_agents)
        }

    def _generate_health_recommendations(self, health_score: float, high_failure_agents: List[str]) -> List[str]:
        """Generate health improvement recommendations"""
        recommendations = []

        if health_score < 0.5:
            recommendations.append("Critical: System health is low - immediate intervention required")
        elif health_score < 0.7:
            recommendations.append("Warning: System health declining - monitor closely")

        if high_failure_agents:
            recommendations.append(f"Address high failure rates for agents: {', '.join(high_failure_agents)}")

        if health_score < 0.8:
            recommendations.append("Consider implementing additional preventive measures")

        return recommendations

    def _assess_task_complexity(self, task_description: str) -> str:
        """Assess the complexity level of a task"""
        desc_lower = task_description.lower()
        word_count = len(task_description.split())

        # Complexity indicators
        complexity_keywords = ['complex', 'difficult', 'challenging', 'advanced', 'sophisticated', 'analyze', 'optimize']
        simple_keywords = ['simple', 'basic', 'straightforward', 'easy']

        complexity_score = 0

        # Word count factor
        if word_count > 100:
            complexity_score += 2
        elif word_count > 50:
            complexity_score += 1

        # Keyword analysis
        complexity_matches = sum(1 for keyword in complexity_keywords if keyword in desc_lower)
        simple_matches = sum(1 for keyword in simple_keywords if keyword in desc_lower)

        complexity_score += complexity_matches - simple_matches

        # Special patterns
        if 'step-by-step' in desc_lower or 'detailed' in desc_lower:
            complexity_score += 1
        if 'quick' in desc_lower or 'fast' in desc_lower:
            complexity_score -= 1

        # Determine complexity level
        if complexity_score >= 3:
            return 'high'
        elif complexity_score >= 1:
            return 'medium'
        else:
            return 'low'

    def _detect_parallelism_opportunity(self, task_description: str) -> bool:
        """Detect if a task has opportunities for parallel execution"""
        desc_lower = task_description.lower()

        # Parallelism indicators
        parallel_keywords = ['multiple', 'several', 'various', 'different', 'parallel', 'concurrent', 'simultaneous']
        batch_keywords = ['batch', 'process all', 'handle all', 'analyze all']

        has_parallel_indicators = any(keyword in desc_lower for keyword in parallel_keywords)
        has_batch_indicators = any(keyword in desc_lower for keyword in batch_keywords)

        # Check for numbered lists or itemized tasks
        has_numbered_items = len([word for word in task_description.split() if word.replace('.', '').isdigit()]) > 2
        has_bullet_points = '•' in task_description or '*' in task_description or '-' in task_description

        return has_parallel_indicators or has_batch_indicators or has_numbered_items or has_bullet_points

    def _check_resource_constraints(self) -> bool:
        """Check if the system is currently resource constrained"""
        if not self.registered_agents:
            return True

        # Calculate current system load
        total_load = sum(self.agent_loads.values())
        avg_load = total_load / len(self.registered_agents)

        # Check memory pressure (simplified)
        memory_pressure = len(self.delegation_system.active_tasks) > 10

        # Check agent saturation
        saturated_agents = sum(1 for load in self.agent_loads.values() if load >= self.max_agent_load)

        return avg_load > 2.0 or memory_pressure or saturated_agents > len(self.registered_agents) * 0.7

    def _extract_data_types(self, task_description: str) -> List[str]:
        """Extract data types mentioned in task description for policy evaluation"""
        data_types = []
        desc_lower = task_description.lower()

        # Common data type indicators
        data_type_patterns = {
            'personal': ['personal', 'user', 'individual', 'person'],
            'sensitive': ['password', 'secret', 'confidential', 'private'],
            'health': ['medical', 'health', 'patient', 'diagnosis'],
            'financial': ['financial', 'payment', 'credit', 'bank', 'money'],
            'logs': ['log', 'audit', 'trace', 'debug'],
            'pii': ['email', 'phone', 'address', 'ssn', 'social']
        }

        for data_type, patterns in data_type_patterns.items():
            if any(pattern in desc_lower for pattern in patterns):
                data_types.append(data_type)

        return data_types

    def _assess_ethical_impact(self, task_description: str) -> str:
        """Assess the ethical impact level of a task"""
        desc_lower = task_description.lower()

        # High ethical impact indicators
        high_impact_keywords = [
            'harm', 'damage', 'destroy', 'delete', 'exploit', 'manipulate',
            'discriminate', 'bias', 'privacy', 'surveillance', 'control'
        ]

        # Medium ethical impact indicators
        medium_impact_keywords = [
            'analyze', 'profile', 'track', 'monitor', 'collect', 'share',
            'recommend', 'decide', 'evaluate', 'assess'
        ]

        if any(keyword in desc_lower for keyword in high_impact_keywords):
            return 'high'
        elif any(keyword in desc_lower for keyword in medium_impact_keywords):
            return 'medium'
        else:
            return 'low'

    def _find_alternative_agent_for_retry(self, failed_agent: str, task_description: str) -> Optional[str]:
        """Find an alternative agent for retrying a failed task"""
        available_agents = [agent for agent in self.registered_agents if agent != failed_agent]

        if not available_agents:
            return None

        # Try to find agent with similar expertise but different from failed agent
        task_type = self._infer_task_type(task_description)
        agent_expertise = self.planning_module.assign_agents_to_subtasks(available_agents)

        # Look for agents with relevant expertise
        suitable_agents = []
        for agent in available_agents:
            if agent in agent_expertise:
                expertise = agent_expertise[agent]
                # Check if agent has relevant expertise for the task
                if any(keyword.lower() in task_description.lower() for keyword in expertise):
                    suitable_agents.append(agent)

        if suitable_agents:
            # Return least loaded suitable agent
            return min(suitable_agents, key=lambda a: self.agent_loads.get(a, 0))

        # Fallback: return least loaded available agent
        return min(available_agents, key=lambda a: self.agent_loads.get(a, 0))

    def _simplify_high_risk_task(self, subtask: Dict[str, Any], risk_assessment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Simplify a high-risk task to reduce failure probability"""
        task_desc = subtask['description']
        risk_level = risk_assessment.get('predicted_failure_risk', 0)

        # Only simplify if risk is very high (>70%)
        if risk_level < 0.7:
            return None

        simplified = subtask.copy()

        # Apply simplification strategies based on task content
        desc_lower = task_desc.lower()

        if "analyze" in desc_lower and "complex" in desc_lower:
            # Simplify complex analysis tasks
            simplified['description'] = task_desc.replace("complex", "basic").replace("detailed", "summary")
            simplified['priority'] = min(subtask.get('priority', 1) + 1, 5)  # Increase priority for simplified task

        elif "process" in desc_lower and ("large" in desc_lower or "big" in desc_lower):
            # Simplify large data processing tasks
            simplified['description'] = task_desc.replace("large", "small sample").replace("big", "subset")
            simplified['priority'] = min(subtask.get('priority', 1) + 1, 5)

        elif len(task_desc.split()) > 50:
            # Simplify overly complex task descriptions
            words = task_desc.split()[:30]  # Truncate to first 30 words
            simplified['description'] = ' '.join(words) + "... (simplified)"
            simplified['priority'] = min(subtask.get('priority', 1) + 1, 5)

        else:
            # Generic simplification - reduce scope
            simplified['description'] = f"Simplified: {task_desc[:100]}..."
            simplified['priority'] = min(subtask.get('priority', 1) + 1, 5)

        # Mark as simplified
        simplified['was_simplified'] = True
        simplified['original_complexity'] = 'high'
        simplified['simplification_reason'] = f"High failure risk ({risk_level:.1%})"

        return simplified

        # Log meta-learning insights
        optimal_strategies = metrics.get_optimal_strategy("general", self.registered_agents)
        if optimal_strategies["meta_learning_confidence"] > 0.3:
            logger.log("INFO", "SwarmCoordinator", "Meta-learning insights available",
                       {"confidence": optimal_strategies["meta_learning_confidence"]})

class DynamicLoadBalancer:
    """Dynamic load balancing system that forecasts agent load and redistributes tasks automatically"""

    def __init__(self, load_forecaster: PredictiveLoadForecaster, coordinator: 'SwarmCoordinator'):
        self.load_forecaster = load_forecaster
        self.coordinator = coordinator
        self.rebalance_history: List[Dict[str, Any]] = []
        self.overload_threshold = 3.5  # Agent load threshold for rebalancing
        self.underload_threshold = 0.5  # Threshold for considering agent underutilized
        self.rebalance_cooldown = 30  # Minimum seconds between rebalance operations

    def check_and_rebalance_load(self) -> Dict[str, Any]:
        """Check current load distribution and perform automatic rebalancing if needed"""
        current_time = time.time()

        # Check cooldown
        if hasattr(self, 'last_rebalance_time') and current_time - self.last_rebalance_time < self.rebalance_cooldown:
            return {'action': 'cooldown', 'message': 'Rebalance cooldown active'}

        # Get current load forecasts
        load_forecasts = {}
        for agent_id in self.coordinator.registered_agents:
            forecast = self.load_forecaster.forecast_agent_load(agent_id, time_horizon=300)  # 5 minutes
            load_forecasts[agent_id] = forecast

        # Analyze load distribution
        overloaded_agents = []
        underloaded_agents = []

        for agent_id, forecast in load_forecasts.items():
            predicted_load = forecast['predicted_load']
            if predicted_load > self.overload_threshold:
                overloaded_agents.append({
                    'agent_id': agent_id,
                    'predicted_load': predicted_load,
                    'confidence': forecast['confidence']
                })
            elif predicted_load < self.underload_threshold:
                underloaded_agents.append({
                    'agent_id': agent_id,
                    'predicted_load': predicted_load,
                    'confidence': forecast['confidence']
                })

        # Perform rebalancing if needed
        if overloaded_agents and underloaded_agents:
            return self._perform_load_rebalancing(overloaded_agents, underloaded_agents)
        elif overloaded_agents:
            return self._handle_overload_situation(overloaded_agents)
        else:
            return {'action': 'no_action', 'message': 'Load distribution is balanced'}

    def _perform_load_rebalancing(self, overloaded: List[Dict], underloaded: List[Dict]) -> Dict[str, Any]:
        """Perform automatic task redistribution from overloaded to underloaded agents"""
        rebalance_actions = []

        # Sort by severity (highest load first, lowest load first)
        overloaded.sort(key=lambda x: x['predicted_load'], reverse=True)
        underloaded.sort(key=lambda x: x['predicted_load'])

        for overload_info in overloaded:
            overloaded_agent = overload_info['agent_id']

            # Find suitable tasks to redistribute
            candidate_tasks = self._find_redistributable_tasks(overloaded_agent)
            if not candidate_tasks:
                continue

            for underload_info in underloaded:
                underloaded_agent = underload_info['agent_id']

                # Check if underloaded agent can handle the task type
                suitable_tasks = self._filter_tasks_by_agent_capability(candidate_tasks, underloaded_agent)
                if not suitable_tasks:
                    continue

                # Redistribute the highest priority suitable task
                task_to_redistribute = suitable_tasks[0]  # Already sorted by priority

                success = self._redistribute_task(task_to_redistribute, overloaded_agent, underloaded_agent)
                if success:
                    rebalance_actions.append({
                        'type': 'redistribution',
                        'from_agent': overloaded_agent,
                        'to_agent': underloaded_agent,
                        'task_id': task_to_redistribute['task_id'],
                        'reason': f'Load balancing: {overloaded_agent} overload ({overload_info["predicted_load"]:.1f}) -> {underloaded_agent} underload ({underload_info["predicted_load"]:.1f})'
                    })

                    # Update load tracking
                    self.coordinator.update_agent_load(overloaded_agent, -1)
                    self.coordinator.update_agent_load(underloaded_agent, 1)

                    # Record the rebalancing action
                    self._record_rebalance_action(rebalance_actions[-1])
                    break  # Move to next overloaded agent

        self.last_rebalance_time = time.time()

        return {
            'action': 'rebalanced',
            'rebalance_actions': rebalance_actions,
            'message': f'Performed {len(rebalance_actions)} load rebalancing actions'
        }

    def _handle_overload_situation(self, overloaded: List[Dict]) -> Dict[str, Any]:
        """Handle situation where agents are overloaded but no underloaded agents available"""
        # Could implement task deferral or scaling recommendations
        critical_overloads = [agent for agent in overloaded if agent['predicted_load'] > 4.0]

        if critical_overloads:
            return {
                'action': 'scaling_recommended',
                'critical_agents': critical_overloads,
                'message': f'Critical overload detected for {len(critical_overloads)} agents - scaling recommended'
            }
        else:
            return {
                'action': 'monitoring',
                'overloaded_agents': overloaded,
                'message': f'Monitoring {len(overloaded)} overloaded agents'
            }

    def _find_redistributable_tasks(self, agent_id: str) -> List[Dict[str, Any]]:
        """Find tasks that can be safely redistributed from an overloaded agent"""
        redistributable_tasks = []

        for task_id, task_info in self.coordinator.delegation_system.active_tasks.items():
            if (task_info['task'].assigned_agent == agent_id and
                task_info.get('status') in ['assigned', 'pending'] and
                task_info.get('priority', 1) < 4):  # Don't redistribute critical tasks

                redistributable_tasks.append({
                    'task_id': task_id,
                    'task_info': task_info,
                    'description': task_info['task'].description,
                    'priority': task_info.get('priority', 1)
                })

        # Sort by priority (lowest first - safer to redistribute)
        redistributable_tasks.sort(key=lambda x: x['priority'])

        return redistributable_tasks

    def _filter_tasks_by_agent_capability(self, tasks: List[Dict], target_agent: str) -> List[Dict]:
        """Filter tasks that the target agent can handle based on expertise"""
        suitable_tasks = []

        # Get agent expertise (simplified - would need proper agent capability mapping)
        agent_expertise = self.coordinator.planning_module.assign_agents_to_subtasks([target_agent])
        if target_agent in agent_expertise:
            expertise_keywords = agent_expertise[target_agent]

            for task in tasks:
                task_desc = task['description'].lower()
                # Check if task description matches agent expertise
                if any(keyword.lower() in task_desc for keyword in expertise_keywords):
                    suitable_tasks.append(task)

        return suitable_tasks

    def _redistribute_task(self, task_info: Dict, from_agent: str, to_agent: str) -> bool:
        """Perform the actual task redistribution"""
        try:
            task_id = task_info['task_id']
            task_obj = self.coordinator.delegation_system.active_tasks[task_id]['task']

            # Update task assignment
            task_obj.assigned_agent = to_agent
            self.coordinator.delegation_system.active_tasks[task_id]['task'] = task_obj

            # Send message to new agent
            self.coordinator.send_message(to_agent, MessageType.TASK_ASSIGNMENT, {"task": task_obj})

            # Log the redistribution
            from ..core.base import logger
            logger.log("INFO", "DynamicLoadBalancer", f"Task redistributed: {from_agent} -> {to_agent}",
                        {"task_id": task_id, "reason": "load_balancing"})

            return True

        except Exception as e:
            logger.log("ERROR", "DynamicLoadBalancer", f"Failed to redistribute task {task_info['task_id']}: {str(e)}")
            return False

    def _record_rebalance_action(self, action: Dict[str, Any]):
        """Record a rebalancing action for analytics"""
        action_record = {
            'timestamp': time.time(),
            **action,
            'outcome': 'completed'  # Will be updated if task fails
        }
        self.rebalance_history.append(action_record)

        # Keep only recent history
        if len(self.rebalance_history) > 50:
            self.rebalance_history = self.rebalance_history[-50:]

    def get_load_balancing_stats(self) -> Dict[str, Any]:
        """Get statistics about load balancing effectiveness"""
        total_actions = len(self.rebalance_history)
        if total_actions == 0:
            return {'total_actions': 0, 'effectiveness': 'no_data'}

        successful_actions = sum(1 for action in self.rebalance_history if action.get('outcome') == 'completed')

        return {
            'total_actions': total_actions,
            'successful_actions': successful_actions,
            'success_rate': successful_actions / total_actions if total_actions > 0 else 0,
            'recent_actions': self.rebalance_history[-5:]  # Last 5 actions
        }

class AutoScaler:
    """Auto-scaling system for agents based on workload spikes"""

    def __init__(self, coordinator: 'SwarmCoordinator', load_forecaster: PredictiveLoadForecaster):
        self.coordinator = coordinator
        self.load_forecaster = load_forecaster

        # Scaling configuration
        self.scale_up_threshold = 3.0  # Average load threshold for scaling up
        self.scale_down_threshold = 0.3  # Average load threshold for scaling down
        self.critical_load_threshold = 4.0  # Critical load requiring immediate scaling
        self.min_agents = 2  # Minimum number of agents to maintain
        self.max_agents = 20  # Maximum number of agents to prevent resource exhaustion
        self.scale_cooldown = 120  # Minimum seconds between scaling operations
        self.agent_startup_time = 30  # Estimated time for new agent to become operational

        # Scaling state
        self.last_scale_time = 0
        self.scaling_history: List[Dict[str, Any]] = []
        self.active_scaling_operations: Dict[str, Dict[str, Any]] = {}

        # Agent templates for instantiation
        self.agent_templates = {
            'VisionAgent': {'class': 'VisionAgent', 'capabilities': ['vision', 'image_analysis']},
            'LanguageAgent': {'class': 'LanguageAgent', 'capabilities': ['language', 'nlp']},
            'MathReasoningAgent': {'class': 'MathReasoningAgent', 'capabilities': ['math', 'logic']},
            'SimulationAgent': {'class': 'SimulationAgent', 'capabilities': ['simulation', 'modeling']}
        }

        # Scaling metrics
        self.scaling_metrics = {
            'scale_up_events': 0,
            'scale_down_events': 0,
            'failed_scaling_operations': 0,
            'average_scaling_time': 0,
            'cost_savings': 0
        }

    def check_scaling_needed(self) -> Dict[str, Any]:
        """Check if scaling is needed based on current workload"""
        current_time = time.time()

        # Check cooldown
        if current_time - self.last_scale_time < self.scale_cooldown:
            return {'action': 'cooldown', 'message': 'Scaling cooldown active'}

        # Get current system load
        system_load = self._calculate_system_load()
        agent_loads = {agent_id: self.coordinator.agent_loads.get(agent_id, 0)
                      for agent_id in self.coordinator.registered_agents}

        # Get load forecasts
        load_forecasts = {}
        for agent_id in self.coordinator.registered_agents:
            forecast = self.load_forecaster.forecast_agent_load(agent_id, time_horizon=600)  # 10 minutes
            load_forecasts[agent_id] = forecast

        # Analyze scaling needs
        scaling_decision = self._analyze_scaling_needs(system_load, agent_loads, load_forecasts)

        if scaling_decision['action'] != 'no_action':
            self.last_scale_time = current_time
            return self._execute_scaling(scaling_decision)
        else:
            return {'action': 'no_action', 'message': 'No scaling needed'}

    def _calculate_system_load(self) -> Dict[str, Any]:
        """Calculate overall system load metrics"""
        if not self.coordinator.registered_agents:
            return {'average_load': 0, 'max_load': 0, 'total_load': 0, 'active_tasks': 0}

        agent_loads = [self.coordinator.agent_loads.get(agent_id, 0)
                      for agent_id in self.coordinator.registered_agents]

        return {
            'average_load': sum(agent_loads) / len(agent_loads),
            'max_load': max(agent_loads) if agent_loads else 0,
            'total_load': sum(agent_loads),
            'active_tasks': len(self.coordinator.delegation_system.active_tasks),
            'agent_count': len(self.coordinator.registered_agents)
        }

    def _analyze_scaling_needs(self, system_load: Dict[str, Any], agent_loads: Dict[str, float],
                             load_forecasts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze whether scaling up or down is needed"""

        current_avg_load = system_load['average_load']
        current_max_load = system_load['max_load']
        agent_count = system_load['agent_count']

        # Calculate forecasted average load
        forecasted_loads = [forecast['predicted_load'] for forecast in load_forecasts.values()]
        avg_forecasted_load = sum(forecasted_loads) / len(forecasted_loads) if forecasted_loads else 0

        # Check for critical overload (immediate scaling needed)
        critical_agents = [agent_id for agent_id, load in agent_loads.items()
                          if load >= self.critical_load_threshold]

        if critical_agents:
            return {
                'action': 'scale_up',
                'reason': 'critical_overload',
                'critical_agents': critical_agents,
                'agents_to_add': min(len(critical_agents), 3),  # Add up to 3 agents for critical overload
                'urgency': 'high'
            }

        # Check for sustained high load (scale up)
        if (current_avg_load >= self.scale_up_threshold or
            avg_forecasted_load >= self.scale_up_threshold * 1.2):  # Forecast shows higher load

            # Determine how many agents to add
            load_pressure = max(current_avg_load, avg_forecasted_load) - self.scale_up_threshold
            agents_needed = max(1, int(load_pressure / 0.5))  # Add 1 agent per 0.5 load units over threshold

            # Don't exceed max agents
            max_can_add = self.max_agents - agent_count
            agents_to_add = min(agents_needed, max_can_add, 5)  # Cap at 5 agents per scaling event

            if agents_to_add > 0:
                return {
                    'action': 'scale_up',
                    'reason': 'high_load',
                    'current_load': current_avg_load,
                    'forecasted_load': avg_forecasted_load,
                    'agents_to_add': agents_to_add,
                    'urgency': 'medium'
                }

        # Check for sustained low load (scale down)
        if (current_avg_load <= self.scale_down_threshold and
            agent_count > self.min_agents and
            avg_forecasted_load <= self.scale_down_threshold):

            # Determine how many agents to remove
            underutilization = self.scale_down_threshold - current_avg_load
            agents_to_remove = max(1, int(underutilization / 0.3))  # Remove 1 agent per 0.3 load units under threshold

            # Don't go below minimum agents
            agents_to_remove = min(agents_to_remove, agent_count - self.min_agents, 3)  # Cap at 3 agents per scaling event

            if agents_to_remove > 0:
                return {
                    'action': 'scale_down',
                    'reason': 'low_load',
                    'current_load': current_avg_load,
                    'forecasted_load': avg_forecasted_load,
                    'agents_to_remove': agents_to_remove,
                    'urgency': 'low'
                }

        return {'action': 'no_action', 'reason': 'load_within_normal_range'}

    def _execute_scaling(self, scaling_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the scaling decision"""
        action = scaling_decision['action']

        if action == 'scale_up':
            return self._scale_up(scaling_decision)
        elif action == 'scale_down':
            return self._scale_down(scaling_decision)
        else:
            return {'action': 'error', 'message': 'Unknown scaling action'}

    def _scale_up(self, scaling_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Scale up by adding new agents"""
        agents_to_add = scaling_decision['agents_to_add']
        reason = scaling_decision['reason']

        scaling_operation_id = f"scale_up_{int(time.time())}_{reason}"

        # Determine which agent types to add based on current workload patterns
        agent_types_to_add = self._determine_agent_types_to_add(agents_to_add)

        added_agents = []
        for agent_type in agent_types_to_add:
            agent_id = self._instantiate_agent(agent_type)
            if agent_id:
                added_agents.append(agent_id)
                # Register with coordinator
                self.coordinator.register_agent(agent_id)
                # Initialize load tracking
                self.coordinator.agent_loads[agent_id] = 0

        # Record scaling operation
        operation_record = {
            'operation_id': scaling_operation_id,
            'action': 'scale_up',
            'timestamp': time.time(),
            'reason': reason,
            'agents_added': added_agents,
            'target_count': agents_to_add,
            'actual_count': len(added_agents),
            'system_load_before': self._calculate_system_load(),
            'urgency': scaling_decision.get('urgency', 'medium')
        }

        self.scaling_history.append(operation_record)
        self.active_scaling_operations[scaling_operation_id] = operation_record

        # Update metrics
        self.scaling_metrics['scale_up_events'] += 1

        # Log scaling event
        logger.log("INFO", "AutoScaler", f"Scaled up: added {len(added_agents)} agents",
                   {"reason": reason, "agents": added_agents})

        return {
            'action': 'scaled_up',
            'agents_added': added_agents,
            'operation_id': scaling_operation_id,
            'message': f'Successfully added {len(added_agents)} agents due to {reason}'
        }

    def _scale_down(self, scaling_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Scale down by removing idle agents"""
        agents_to_remove = scaling_decision['agents_to_remove']
        reason = scaling_decision['reason']

        scaling_operation_id = f"scale_down_{int(time.time())}_{reason}"

        # Select agents to remove (prefer least loaded, non-critical agents)
        agents_to_remove_list = self._select_agents_for_removal(agents_to_remove)

        removed_agents = []
        for agent_id in agents_to_remove_list:
            if self._safely_remove_agent(agent_id):
                removed_agents.append(agent_id)

        # Record scaling operation
        operation_record = {
            'operation_id': scaling_operation_id,
            'action': 'scale_down',
            'timestamp': time.time(),
            'reason': reason,
            'agents_removed': removed_agents,
            'target_count': agents_to_remove,
            'actual_count': len(removed_agents),
            'system_load_before': self._calculate_system_load(),
            'urgency': scaling_decision.get('urgency', 'low')
        }

        self.scaling_history.append(operation_record)
        self.active_scaling_operations[scaling_operation_id] = operation_record

        # Update metrics
        self.scaling_metrics['scale_down_events'] += 1

        # Log scaling event
        logger.log("INFO", "AutoScaler", f"Scaled down: removed {len(removed_agents)} agents",
                   {"reason": reason, "agents": removed_agents})

        return {
            'action': 'scaled_down',
            'agents_removed': removed_agents,
            'operation_id': scaling_operation_id,
            'message': f'Successfully removed {len(removed_agents)} agents due to {reason}'
        }

    def _determine_agent_types_to_add(self, count: int) -> List[str]:
        """Determine which types of agents to add based on workload patterns"""
        # Analyze current agent distribution and task types
        current_agent_types = {}
        for agent_id in self.coordinator.registered_agents:
            # Extract agent type from ID (simplified - would need proper agent type tracking)
            if 'Vision' in agent_id:
                agent_type = 'VisionAgent'
            elif 'Language' in agent_id:
                agent_type = 'LanguageAgent'
            elif 'Math' in agent_id:
                agent_type = 'MathReasoningAgent'
            elif 'Simulation' in agent_id:
                agent_type = 'SimulationAgent'
            else:
                agent_type = 'LanguageAgent'  # Default

            current_agent_types[agent_type] = current_agent_types.get(agent_type, 0) + 1

        # Analyze recent tasks to determine needed capabilities
        task_types = self._analyze_recent_task_types()

        # Determine agent types to add
        agent_types_to_add = []

        # Prioritize based on task demand
        for task_type, demand in task_types.items():
            if demand > 0.3:  # High demand for this task type
                if task_type == 'vision':
                    agent_types_to_add.extend(['VisionAgent'] * max(1, int(demand * count)))
                elif task_type == 'language':
                    agent_types_to_add.extend(['LanguageAgent'] * max(1, int(demand * count)))
                elif task_type == 'math':
                    agent_types_to_add.extend(['MathReasoningAgent'] * max(1, int(demand * count)))
                elif task_type == 'simulation':
                    agent_types_to_add.extend(['SimulationAgent'] * max(1, int(demand * count)))

        # Fill remaining slots with balanced distribution
        while len(agent_types_to_add) < count:
            # Add the least represented agent type
            min_type = min(current_agent_types.keys(),
                          key=lambda x: current_agent_types.get(x, 0))
            agent_types_to_add.append(min_type)

        return agent_types_to_add[:count]

    def _instantiate_agent(self, agent_type: str) -> Optional[str]:
        """Instantiate a new agent of the specified type"""
        try:
            # Generate unique agent ID
            timestamp = int(time.time())
            agent_id = f"{agent_type}_{timestamp}_{len(self.coordinator.registered_agents)}"

            # Import agent class dynamically
            if agent_type == 'VisionAgent':
                from .agents import VisionAgent
                agent_class = VisionAgent
            elif agent_type == 'LanguageAgent':
                from .agents import LanguageAgent
                agent_class = LanguageAgent
            elif agent_type == 'MathReasoningAgent':
                from .agents import MathReasoningAgent
                agent_class = MathReasoningAgent
            elif agent_type == 'SimulationAgent':
                from .agents import SimulationAgent
                agent_class = SimulationAgent
            else:
                logger.log("ERROR", "AutoScaler", f"Unknown agent type: {agent_type}")
                return None

            # Create agent instance
            agent = agent_class(agent_id, self.coordinator.swarm_id)

            # Store agent instance (in real implementation, this would be managed by a registry)
            # For now, just return the ID - the coordinator will handle messaging

            logger.log("INFO", "AutoScaler", f"Instantiated new {agent_type}: {agent_id}")
            return agent_id

        except Exception as e:
            logger.log("ERROR", "AutoScaler", f"Failed to instantiate {agent_type}: {str(e)}")
            self.scaling_metrics['failed_scaling_operations'] += 1
            return None

    def _select_agents_for_removal(self, count: int) -> List[str]:
        """Select agents for removal based on load and criticality"""
        candidates = []

        for agent_id in self.coordinator.registered_agents:
            load = self.coordinator.agent_loads.get(agent_id, 0)
            active_tasks = sum(1 for task_info in self.coordinator.delegation_system.active_tasks.values()
                             if task_info['task'].assigned_agent == agent_id)

            # Only consider agents with low load and no active tasks
            if load <= 0.5 and active_tasks == 0:
                candidates.append({
                    'agent_id': agent_id,
                    'load': load,
                    'active_tasks': active_tasks,
                    'priority': 1  # Lower priority for removal
                })

        # Sort by load (lowest first) and ensure we don't go below minimum agents
        candidates.sort(key=lambda x: x['load'])
        max_to_remove = len(self.coordinator.registered_agents) - self.min_agents

        return [c['agent_id'] for c in candidates[:min(count, max_to_remove)]]

    def _safely_remove_agent(self, agent_id: str) -> bool:
        """Safely remove an agent from the system"""
        try:
            # Check if agent has any active tasks
            active_tasks = [task_id for task_id, task_info in self.coordinator.delegation_system.active_tasks.items()
                           if task_info['task'].assigned_agent == agent_id]

            if active_tasks:
                logger.log("WARNING", "AutoScaler", f"Cannot remove agent {agent_id} - has {len(active_tasks)} active tasks")
                return False

            # Remove from coordinator
            if agent_id in self.coordinator.registered_agents:
                self.coordinator.registered_agents.remove(agent_id)

            # Clean up load tracking
            self.coordinator.agent_loads.pop(agent_id, None)

            logger.log("INFO", "AutoScaler", f"Successfully removed agent: {agent_id}")
            return True

        except Exception as e:
            logger.log("ERROR", "AutoScaler", f"Failed to remove agent {agent_id}: {str(e)}")
            return False

    def _analyze_recent_task_types(self) -> Dict[str, float]:
        """Analyze recent task types to determine capability demands"""
        # Analyze recent tasks to determine which agent types are needed
        task_counts = {'vision': 0, 'language': 0, 'math': 0, 'simulation': 0}
        total_tasks = 0

        # Look at recent delegation history (simplified)
        for task_info in list(self.coordinator.delegation_system.active_tasks.values())[-20:]:  # Last 20 tasks
            task_desc = task_info['task'].description.lower()
            total_tasks += 1

            if any(word in task_desc for word in ['image', 'vision', 'visual', 'picture']):
                task_counts['vision'] += 1
            elif any(word in task_desc for word in ['text', 'language', 'summarize', 'analyze']):
                task_counts['language'] += 1
            elif any(word in task_desc for word in ['calculate', 'math', 'solve', 'equation']):
                task_counts['math'] += 1
            elif any(word in task_desc for word in ['simulate', 'model', 'scenario']):
                task_counts['simulation'] += 1
            else:
                task_counts['language'] += 1  # Default to language

        # Calculate proportions
        if total_tasks > 0:
            return {task_type: count / total_tasks for task_type, count in task_counts.items()}
        else:
            return {task_type: 0.25 for task_type in task_counts.keys()}  # Equal distribution if no data

    def get_scaling_metrics(self) -> Dict[str, Any]:
        """Get comprehensive scaling metrics"""
        current_system_load = self._calculate_system_load()

        return {
            'current_system_load': current_system_load,
            'scaling_history': self.scaling_history[-10:],  # Last 10 scaling events
            'active_operations': self.active_scaling_operations,
            'scaling_metrics': self.scaling_metrics,
            'agent_distribution': self._get_agent_distribution(),
            'scaling_efficiency': self._calculate_scaling_efficiency(),
            'recommendations': self._generate_scaling_recommendations()
        }

    def _get_agent_distribution(self) -> Dict[str, int]:
        """Get current agent type distribution"""
        distribution = {}
        for agent_id in self.coordinator.registered_agents:
            if 'Vision' in agent_id:
                agent_type = 'VisionAgent'
            elif 'Language' in agent_id:
                agent_type = 'LanguageAgent'
            elif 'Math' in agent_id:
                agent_type = 'MathReasoningAgent'
            elif 'Simulation' in agent_id:
                agent_type = 'SimulationAgent'
            else:
                agent_type = 'Unknown'

            distribution[agent_type] = distribution.get(agent_type, 0) + 1

        return distribution

    def _calculate_scaling_efficiency(self) -> Dict[str, Any]:
        """Calculate scaling efficiency metrics"""
        if not self.scaling_history:
            return {'efficiency_score': 0, 'average_response_time': 0}

        # Calculate efficiency based on how well scaling maintained optimal load
        optimal_load_range = (self.scale_down_threshold, self.scale_up_threshold)
        efficiency_scores = []

        for operation in self.scaling_history[-20:]:  # Last 20 operations
            load_before = operation.get('system_load_before', {}).get('average_load', 1.0)
            # Simplified: assume scaling improved load balance
            if operation['action'] == 'scale_up' and load_before > self.scale_up_threshold:
                efficiency_scores.append(0.8)  # Good scaling up
            elif operation['action'] == 'scale_down' and load_before < self.scale_down_threshold:
                efficiency_scores.append(0.7)  # Good scaling down
            else:
                efficiency_scores.append(0.5)  # Neutral

        return {
            'efficiency_score': sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0,
            'total_operations': len(self.scaling_history),
            'successful_operations': sum(1 for op in self.scaling_history if op.get('actual_count', 0) > 0)
        }

    def _generate_scaling_recommendations(self) -> List[str]:
        """Generate scaling recommendations based on current state"""
        recommendations = []
        current_load = self._calculate_system_load()

        if current_load['average_load'] > self.scale_up_threshold * 1.5:
            recommendations.append("Consider increasing scale_up_threshold or max_agents for better performance")

        if current_load['agent_count'] >= self.max_agents:
            recommendations.append("At maximum agent capacity - consider optimizing task distribution")

        if current_load['agent_count'] <= self.min_agents and current_load['average_load'] < self.scale_down_threshold:
            recommendations.append("System is under-utilized - consider reducing minimum agent count")

        # Check scaling frequency
        recent_scalings = [op for op in self.scaling_history if time.time() - op['timestamp'] < 3600]  # Last hour
        if len(recent_scalings) > 5:
            recommendations.append("Frequent scaling detected - consider adjusting scaling thresholds")

        return recommendations