from typing import Dict, List, Any, Optional, Tuple, Set
from ..core.base import logger, metrics
import time
import json
import uuid
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
import re
from datetime import datetime, timedelta

class GoalType(Enum):
    IMPROVEMENT = "improvement"
    OPTIMIZATION = "optimization"
    EXPLORATION = "exploration"
    MAINTENANCE = "maintenance"
    INNOVATION = "innovation"
    LEARNING = "learning"
    EXPANSION = "expansion"

class GoalPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class PatternType(Enum):
    SUCCESS_PATTERN = "success_pattern"
    FAILURE_PATTERN = "failure_pattern"
    EFFICIENCY_PATTERN = "efficiency_pattern"
    USER_PREFERENCE = "user_preference"
    SYSTEM_IMPROVEMENT = "system_improvement"
    RESOURCE_OPTIMIZATION = "resource_optimization"
    QUALITY_IMPROVEMENT = "quality_improvement"

@dataclass
class ObservedPattern:
    """Represents a pattern observed in long-term memory"""
    pattern_id: str
    pattern_type: PatternType
    description: str
    frequency: int
    confidence: float
    supporting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    first_observed: float = field(default_factory=time.time)
    last_observed: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProposedGoal:
    """Represents a goal proposed by autonomous goal setting"""
    goal_id: str
    title: str
    description: str
    goal_type: GoalType
    priority: GoalPriority
    rationale: str
    expected_benefits: List[str]
    proposed_subtasks: List[Dict[str, Any]] = field(default_factory=list)
    based_on_patterns: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    estimated_effort: str = "medium"
    estimated_impact: str = "medium"
    proposed_at: float = field(default_factory=time.time)
    status: str = "proposed"  # proposed, accepted, rejected, implemented

@dataclass
class GoalImplementation:
    """Tracks implementation of autonomous goals"""
    implementation_id: str
    goal_id: str
    started_at: float
    completed_subtasks: List[str] = field(default_factory=list)
    status: str = "in_progress"  # in_progress, completed, failed
    outcomes: Dict[str, Any] = field(default_factory=dict)
    lessons_learned: List[str] = field(default_factory=dict)

class AutonomousGoalSetter:
    """Autonomous goal setting system based on long-term memory patterns"""

    def __init__(self):
        self.observed_patterns: Dict[str, ObservedPattern] = {}
        self.proposed_goals: Dict[str, ProposedGoal] = {}
        self.implementations: Dict[str, GoalImplementation] = {}

        # Pattern recognition thresholds
        self.min_pattern_frequency = 3  # Minimum occurrences to consider a pattern
        self.min_pattern_confidence = 0.6  # Minimum confidence to propose goals
        self.max_proposed_goals = 5  # Maximum goals to propose at once

        # Goal generation intervals
        self.goal_generation_interval = 3600  # Generate goals every hour
        self.last_goal_generation = 0

        # Pattern analysis windows
        self.analysis_window_days = 7  # Analyze patterns from last 7 days
        self.trend_window_days = 30  # Analyze trends over 30 days

        # Goal categories and templates
        self.goal_templates = self._initialize_goal_templates()

    def _initialize_goal_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize goal templates for different pattern types"""
        return {
            "success_pattern": {
                "template": "Leverage successful {pattern} pattern",
                "subtasks": [
                    "Analyze successful instances",
                    "Identify key success factors",
                    "Create best practices guide",
                    "Implement pattern replication"
                ]
            },
            "failure_pattern": {
                "template": "Address recurring {pattern} failure pattern",
                "subtasks": [
                    "Analyze failure causes",
                    "Identify prevention strategies",
                    "Implement safeguards",
                    "Create monitoring alerts"
                ]
            },
            "efficiency_pattern": {
                "template": "Optimize {pattern} efficiency pattern",
                "subtasks": [
                    "Measure current efficiency",
                    "Identify bottlenecks",
                    "Implement optimizations",
                    "Monitor improvement metrics"
                ]
            },
            "user_preference": {
                "template": "Enhance user experience based on {pattern} preferences",
                "subtasks": [
                    "Analyze user feedback patterns",
                    "Identify preference trends",
                    "Implement preference-based features",
                    "Measure user satisfaction improvement"
                ]
            },
            "system_improvement": {
                "template": "Improve system {pattern} capabilities",
                "subtasks": [
                    "Assess current capabilities",
                    "Identify improvement opportunities",
                    "Implement enhancements",
                    "Validate improvements"
                ]
            },
            "resource_optimization": {
                "template": "Optimize {pattern} resource usage",
                "subtasks": [
                    "Analyze resource consumption patterns",
                    "Identify optimization opportunities",
                    "Implement resource optimizations",
                    "Monitor resource efficiency"
                ]
            },
            "quality_improvement": {
                "template": "Enhance {pattern} quality standards",
                "subtasks": [
                    "Assess current quality levels",
                    "Identify quality gaps",
                    "Implement quality improvements",
                    "Establish quality metrics"
                ]
            }
        }

    def analyze_long_term_memory(self, long_term_memory) -> List[ProposedGoal]:
        """Analyze long-term memory to identify patterns and propose goals"""

        current_time = time.time()

        # Check if it's time to generate goals
        if current_time - self.last_goal_generation < self.goal_generation_interval:
            return []

        logger.log("INFO", "AutonomousGoalSetter", "Starting long-term memory analysis for goal generation")

        # Extract patterns from long-term memory
        patterns = self._extract_patterns_from_memory(long_term_memory)

        # Update observed patterns
        self._update_observed_patterns(patterns)

        # Generate goals based on patterns
        proposed_goals = self._generate_goals_from_patterns()

        # Filter and prioritize goals
        filtered_goals = self._filter_and_prioritize_goals(proposed_goals)

        self.last_goal_generation = current_time

        logger.log("INFO", "AutonomousGoalSetter", f"Generated {len(filtered_goals)} autonomous goals")

        return filtered_goals

    def _extract_patterns_from_memory(self, long_term_memory) -> List[Dict[str, Any]]:
        """Extract patterns from long-term memory"""

        patterns = []
        analysis_cutoff = time.time() - (self.analysis_window_days * 24 * 60 * 60)

        # Analyze episodic memory (completed tasks)
        episodic_data = long_term_memory.search("completed_task")
        task_patterns = self._analyze_task_patterns(episodic_data, analysis_cutoff)
        patterns.extend(task_patterns)

        # Analyze semantic memory (learned concepts)
        semantic_data = long_term_memory.search("learned_concepts")
        concept_patterns = self._analyze_concept_patterns(semantic_data, analysis_cutoff)
        patterns.extend(concept_patterns)

        # Analyze tool usage patterns
        tool_data = long_term_memory.search("tool_use")
        tool_patterns = self._analyze_tool_patterns(tool_data, analysis_cutoff)
        patterns.extend(tool_patterns)

        # Analyze reflection patterns
        reflection_data = long_term_memory.search("reflection")
        reflection_patterns = self._analyze_reflection_patterns(reflection_data, analysis_cutoff)
        patterns.extend(reflection_patterns)

        return patterns

    def _analyze_task_patterns(self, task_data: List[Any], cutoff_time: float) -> List[Dict[str, Any]]:
        """Analyze patterns in completed tasks"""

        patterns = []
        recent_tasks = [task for task in task_data if isinstance(task, dict) and
                       task.get('timestamp', 0) > cutoff_time]

        if len(recent_tasks) < 5:
            return patterns

        # Analyze success/failure patterns
        success_count = sum(1 for task in recent_tasks if task.get('outcome') == 'success')
        success_rate = success_count / len(recent_tasks)

        if success_rate < 0.7:
            patterns.append({
                'type': PatternType.FAILURE_PATTERN,
                'description': f"Low task success rate: {success_rate:.1%}",
                'frequency': len(recent_tasks) - success_count,
                'confidence': 0.8,
                'evidence': recent_tasks,
                'metadata': {'success_rate': success_rate, 'total_tasks': len(recent_tasks)}
            })

        # Analyze task type performance
        task_types = Counter(task.get('task_type', 'unknown') for task in recent_tasks)
        for task_type, count in task_types.items():
            if count >= 3:
                type_tasks = [t for t in recent_tasks if t.get('task_type') == task_type]
                type_success_rate = sum(1 for t in type_tasks if t.get('outcome') == 'success') / len(type_tasks)

                if type_success_rate < 0.6:
                    patterns.append({
                        'type': PatternType.FAILURE_PATTERN,
                        'description': f"Poor performance in {task_type} tasks: {type_success_rate:.1%}",
                        'frequency': len(type_tasks),
                        'confidence': 0.7,
                        'evidence': type_tasks,
                        'metadata': {'task_type': task_type, 'success_rate': type_success_rate}
                    })

        # Analyze execution time patterns
        execution_times = [task.get('execution_time', 0) for task in recent_tasks if task.get('execution_time')]
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            long_running = [t for t in execution_times if t > avg_time * 2]

            if len(long_running) > len(execution_times) * 0.3:
                patterns.append({
                    'type': PatternType.EFFICIENCY_PATTERN,
                    'description': f"High number of long-running tasks: {len(long_running)}/{len(execution_times)}",
                    'frequency': len(long_running),
                    'confidence': 0.6,
                    'evidence': recent_tasks,
                    'metadata': {'avg_time': avg_time, 'long_running_count': len(long_running)}
                })

        return patterns

    def _analyze_concept_patterns(self, concept_data: List[Any], cutoff_time: float) -> List[Dict[str, Any]]:
        """Analyze patterns in learned concepts"""

        patterns = []
        recent_concepts = [concept for concept in concept_data if isinstance(concept, dict) and
                          concept.get('timestamp', 0) > cutoff_time]

        if len(recent_concepts) < 3:
            return patterns

        # Analyze concept categories
        categories = Counter(concept.get('category', 'unknown') for concept in recent_concepts)

        # Look for underrepresented categories
        total_concepts = len(recent_concepts)
        for category, count in categories.items():
            if count / total_concepts < 0.1:  # Less than 10% of concepts
                patterns.append({
                    'type': PatternType.LEARNING,
                    'description': f"Underrepresented knowledge area: {category}",
                    'frequency': count,
                    'confidence': 0.5,
                    'evidence': recent_concepts,
                    'metadata': {'category': category, 'percentage': count / total_concepts}
                })

        # Analyze concept learning trends
        concept_dates = [datetime.fromtimestamp(c.get('timestamp', 0)) for c in recent_concepts]
        if concept_dates:
            recent_week = datetime.now() - timedelta(days=7)
            recent_concepts_count = sum(1 for d in concept_dates if d > recent_week)

            if recent_concepts_count < 2:
                patterns.append({
                    'type': PatternType.LEARNING,
                    'description': "Low concept learning rate in recent period",
                    'frequency': recent_concepts_count,
                    'confidence': 0.6,
                    'evidence': recent_concepts,
                    'metadata': {'recent_count': recent_concepts_count, 'timeframe': '7 days'}
                })

        return patterns

    def _analyze_tool_patterns(self, tool_data: List[Any], cutoff_time: float) -> List[Dict[str, Any]]:
        """Analyze patterns in tool usage"""

        patterns = []
        recent_tools = [tool for tool in tool_data if isinstance(tool, dict) and
                       tool.get('timestamp', 0) > cutoff_time]

        if len(recent_tools) < 5:
            return patterns

        # Analyze tool usage frequency
        tool_usage = Counter(tool.get('tool_name', 'unknown') for tool in recent_tools)

        # Identify underutilized tools
        for tool_name, usage_count in tool_usage.items():
            if usage_count == 1 and len(recent_tools) > 10:  # Used only once
                patterns.append({
                    'type': PatternType.RESOURCE_OPTIMIZATION,
                    'description': f"Underutilized tool: {tool_name}",
                    'frequency': usage_count,
                    'confidence': 0.4,
                    'evidence': recent_tools,
                    'metadata': {'tool_name': tool_name, 'usage_count': usage_count}
                })

        # Analyze tool success patterns
        tool_success = {}
        for tool in recent_tools:
            tool_name = tool.get('tool_name', 'unknown')
            success = tool.get('success', False)
            if tool_name not in tool_success:
                tool_success[tool_name] = {'total': 0, 'success': 0}
            tool_success[tool_name]['total'] += 1
            if success:
                tool_success[tool_name]['success'] += 1

        for tool_name, stats in tool_success.items():
            if stats['total'] >= 3:
                success_rate = stats['success'] / stats['total']
                if success_rate < 0.5:
                    patterns.append({
                        'type': PatternType.SYSTEM_IMPROVEMENT,
                        'description': f"Low success rate for tool {tool_name}: {success_rate:.1%}",
                        'frequency': stats['total'] - stats['success'],
                        'confidence': 0.7,
                        'evidence': recent_tools,
                        'metadata': {'tool_name': tool_name, 'success_rate': success_rate}
                    })

        return patterns

    def _analyze_reflection_patterns(self, reflection_data: List[Any], cutoff_time: float) -> List[Dict[str, Any]]:
        """Analyze patterns in reflections"""

        patterns = []
        recent_reflections = [ref for ref in reflection_data if isinstance(ref, dict) and
                             ref.get('timestamp', 0) > cutoff_time]

        if len(recent_reflections) < 3:
            return patterns

        # Analyze reflection themes
        lessons = [ref.get('lesson', '') for ref in recent_reflections if ref.get('lesson')]
        lesson_themes = Counter()

        for lesson in lessons:
            # Simple theme extraction
            if 'efficiency' in lesson.lower():
                lesson_themes['efficiency'] += 1
            elif 'quality' in lesson.lower():
                lesson_themes['quality'] += 1
            elif 'performance' in lesson.lower():
                lesson_themes['performance'] += 1
            elif 'reliability' in lesson.lower():
                lesson_themes['reliability'] += 1
            else:
                lesson_themes['other'] += 1

        # Identify common improvement themes
        for theme, count in lesson_themes.items():
            if count >= 2:
                patterns.append({
                    'type': PatternType.SYSTEM_IMPROVEMENT,
                    'description': f"Recurring {theme} improvement theme in reflections",
                    'frequency': count,
                    'confidence': 0.6,
                    'evidence': recent_reflections,
                    'metadata': {'theme': theme, 'reflection_count': count}
                })

        return patterns

    def _update_observed_patterns(self, new_patterns: List[Dict[str, Any]]):
        """Update observed patterns with new pattern data"""

        for pattern_data in new_patterns:
            pattern_key = f"{pattern_data['type'].value}_{hash(pattern_data['description'])}"

            if pattern_key in self.observed_patterns:
                # Update existing pattern
                pattern = self.observed_patterns[pattern_key]
                pattern.frequency += pattern_data['frequency']
                pattern.confidence = min(1.0, pattern.confidence + 0.1)  # Increase confidence
                pattern.last_observed = time.time()
                pattern.supporting_evidence.extend(pattern_data['evidence'][:5])  # Keep recent evidence
                pattern.supporting_evidence = pattern.supporting_evidence[-10:]  # Limit evidence
            else:
                # Create new pattern
                pattern = ObservedPattern(
                    pattern_id=pattern_key,
                    pattern_type=pattern_data['type'],
                    description=pattern_data['description'],
                    frequency=pattern_data['frequency'],
                    confidence=pattern_data['confidence'],
                    supporting_evidence=pattern_data['evidence'][:10],
                    metadata=pattern_data.get('metadata', {})
                )
                self.observed_patterns[pattern_key] = pattern

    def _generate_goals_from_patterns(self) -> List[ProposedGoal]:
        """Generate goals based on observed patterns"""

        proposed_goals = []

        # Sort patterns by confidence and frequency
        sorted_patterns = sorted(
            self.observed_patterns.values(),
            key=lambda p: (p.confidence * p.frequency),
            reverse=True
        )

        for pattern in sorted_patterns[:self.max_proposed_goals]:
            if pattern.confidence >= self.min_pattern_confidence and pattern.frequency >= self.min_pattern_frequency:
                goal = self._create_goal_from_pattern(pattern)
                if goal:
                    proposed_goals.append(goal)

        return proposed_goals

    def _create_goal_from_pattern(self, pattern: ObservedPattern) -> Optional[ProposedGoal]:
        """Create a goal from an observed pattern"""

        template = self.goal_templates.get(pattern.pattern_type.value)
        if not template:
            return None

        # Generate goal title and description
        title = template['template'].format(pattern=pattern.description.split(':')[0].strip())
        description = f"Based on observed pattern: {pattern.description}"

        # Determine goal type and priority
        goal_type = self._map_pattern_to_goal_type(pattern.pattern_type)
        priority = self._calculate_goal_priority(pattern)

        # Generate rationale and benefits
        rationale = self._generate_goal_rationale(pattern)
        benefits = self._generate_expected_benefits(pattern)

        # Create subtasks
        subtasks = self._generate_subtasks_for_goal(pattern, template['subtasks'])

        # Calculate confidence score
        confidence_score = min(1.0, pattern.confidence * (pattern.frequency / 10.0))

        goal = ProposedGoal(
            goal_id=f"goal_{int(time.time())}_{pattern.pattern_id[:8]}",
            title=title,
            description=description,
            goal_type=goal_type,
            priority=priority,
            rationale=rationale,
            expected_benefits=benefits,
            proposed_subtasks=subtasks,
            based_on_patterns=[pattern.pattern_id],
            confidence_score=confidence_score,
            estimated_effort=self._estimate_goal_effort(pattern),
            estimated_impact=self._estimate_goal_impact(pattern)
        )

        return goal

    def _map_pattern_to_goal_type(self, pattern_type: PatternType) -> GoalType:
        """Map pattern type to goal type"""

        mapping = {
            PatternType.SUCCESS_PATTERN: GoalType.OPTIMIZATION,
            PatternType.FAILURE_PATTERN: GoalType.IMPROVEMENT,
            PatternType.EFFICIENCY_PATTERN: GoalType.OPTIMIZATION,
            PatternType.USER_PREFERENCE: GoalType.INNOVATION,
            PatternType.SYSTEM_IMPROVEMENT: GoalType.IMPROVEMENT,
            PatternType.RESOURCE_OPTIMIZATION: GoalType.OPTIMIZATION,
            PatternType.QUALITY_IMPROVEMENT: GoalType.IMPROVEMENT
        }

        return mapping.get(pattern_type, GoalType.IMPROVEMENT)

    def _calculate_goal_priority(self, pattern: ObservedPattern) -> GoalPriority:
        """Calculate goal priority based on pattern characteristics"""

        score = 0

        # Frequency contributes to priority
        if pattern.frequency >= 10:
            score += 3
        elif pattern.frequency >= 5:
            score += 2
        elif pattern.frequency >= 3:
            score += 1

        # Confidence contributes to priority
        if pattern.confidence >= 0.8:
            score += 2
        elif pattern.confidence >= 0.6:
            score += 1

        # Pattern type priority
        if pattern.pattern_type in [PatternType.FAILURE_PATTERN, PatternType.SYSTEM_IMPROVEMENT]:
            score += 2

        if score >= 5:
            return GoalPriority.CRITICAL
        elif score >= 3:
            return GoalPriority.HIGH
        elif score >= 2:
            return GoalPriority.MEDIUM
        else:
            return GoalPriority.LOW

    def _generate_goal_rationale(self, pattern: ObservedPattern) -> str:
        """Generate rationale for the goal"""

        rationales = {
            PatternType.SUCCESS_PATTERN: f"This goal leverages a successful pattern observed {pattern.frequency} times with {pattern.confidence:.1%} confidence.",
            PatternType.FAILURE_PATTERN: f"This goal addresses a recurring failure pattern observed {pattern.frequency} times that needs attention.",
            PatternType.EFFICIENCY_PATTERN: f"This goal optimizes an efficiency pattern that occurs {pattern.frequency} times regularly.",
            PatternType.USER_PREFERENCE: f"This goal enhances user experience based on observed preferences with {pattern.confidence:.1%} confidence.",
            PatternType.SYSTEM_IMPROVEMENT: f"This goal improves system capabilities based on {pattern.frequency} observations.",
            PatternType.RESOURCE_OPTIMIZATION: f"This goal optimizes resource usage for a pattern observed {pattern.frequency} times.",
            PatternType.QUALITY_IMPROVEMENT: f"This goal enhances quality standards for recurring patterns."
        }

        return rationales.get(pattern.pattern_type, f"This goal addresses the observed pattern: {pattern.description}")

    def _generate_expected_benefits(self, pattern: ObservedPattern) -> List[str]:
        """Generate expected benefits for the goal"""

        benefits = []

        if pattern.pattern_type == PatternType.SUCCESS_PATTERN:
            benefits.extend([
                "Increased success rates through pattern replication",
                "Improved consistency in task outcomes",
                "Better resource utilization"
            ])
        elif pattern.pattern_type == PatternType.FAILURE_PATTERN:
            benefits.extend([
                "Reduced failure rates and improved reliability",
                "Better error prevention and handling",
                "Increased system stability"
            ])
        elif pattern.pattern_type == PatternType.EFFICIENCY_PATTERN:
            benefits.extend([
                "Faster task completion times",
                "Reduced resource consumption",
                "Improved overall system performance"
            ])
        elif pattern.pattern_type == PatternType.USER_PREFERENCE:
            benefits.extend([
                "Enhanced user satisfaction",
                "Better alignment with user needs",
                "Improved user experience"
            ])
        else:
            benefits.extend([
                "General system improvement",
                "Enhanced capabilities",
                "Better performance metrics"
            ])

        return benefits

    def _generate_subtasks_for_goal(self, pattern: ObservedPattern, template_subtasks: List[str]) -> List[Dict[str, Any]]:
        """Generate specific subtasks for the goal"""

        subtasks = []

        for i, template_task in enumerate(template_subtasks):
            subtask = {
                "id": f"subtask_{i+1}",
                "description": template_task,
                "estimated_effort": "medium",
                "dependencies": [] if i == 0 else [f"subtask_{i}"]
            }
            subtasks.append(subtask)

        return subtasks

    def _estimate_goal_effort(self, pattern: ObservedPattern) -> str:
        """Estimate effort required for the goal"""

        if pattern.frequency >= 10 or pattern.confidence >= 0.8:
            return "high"
        elif pattern.frequency >= 5 or pattern.confidence >= 0.6:
            return "medium"
        else:
            return "low"

    def _estimate_goal_impact(self, pattern: ObservedPattern) -> str:
        """Estimate impact of the goal"""

        score = pattern.frequency * pattern.confidence

        if score >= 8:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"

    def _filter_and_prioritize_goals(self, goals: List[ProposedGoal]) -> List[ProposedGoal]:
        """Filter and prioritize proposed goals"""

        # Remove duplicate or very similar goals
        filtered_goals = []
        seen_descriptions = set()

        for goal in goals:
            # Simple deduplication based on description similarity
            desc_key = goal.description.lower()[:50]
            if desc_key not in seen_descriptions:
                filtered_goals.append(goal)
                seen_descriptions.add(desc_key)

        # Sort by priority and confidence
        priority_order = {GoalPriority.CRITICAL: 4, GoalPriority.HIGH: 3, GoalPriority.MEDIUM: 2, GoalPriority.LOW: 1}

        filtered_goals.sort(
            key=lambda g: (priority_order[g.priority], g.confidence_score),
            reverse=True
        )

        # Limit to top goals
        return filtered_goals[:self.max_proposed_goals]

    def accept_goal(self, goal_id: str) -> bool:
        """Accept a proposed goal for implementation"""

        if goal_id not in self.proposed_goals:
            return False

        goal = self.proposed_goals[goal_id]
        goal.status = "accepted"

        # Create implementation tracking
        implementation = GoalImplementation(
            implementation_id=f"impl_{goal_id}_{int(time.time())}",
            goal_id=goal_id,
            started_at=time.time()
        )

        self.implementations[implementation.implementation_id] = implementation

        logger.log("INFO", "AutonomousGoalSetter", f"Accepted autonomous goal: {goal.title}")
        return True

    def reject_goal(self, goal_id: str, reason: str = "") -> bool:
        """Reject a proposed goal"""

        if goal_id not in self.proposed_goals:
            return False

        goal = self.proposed_goals[goal_id]
        goal.status = "rejected"
        goal.metadata = goal.metadata or {}
        goal.metadata['rejection_reason'] = reason

        logger.log("INFO", "AutonomousGoalSetter", f"Rejected autonomous goal: {goal.title} - {reason}")
        return True

    def update_goal_progress(self, goal_id: str, completed_subtask: str, outcomes: Dict[str, Any] = None):
        """Update progress on a goal implementation"""

        # Find the implementation
        implementation = None
        for impl in self.implementations.values():
            if impl.goal_id == goal_id:
                implementation = impl
                break

        if not implementation:
            return

        if completed_subtask not in implementation.completed_subtasks:
            implementation.completed_subtasks.append(completed_subtask)

        if outcomes:
            implementation.outcomes.update(outcomes)

        # Check if goal is complete
        goal = self.proposed_goals.get(goal_id)
        if goal and len(implementation.completed_subtasks) >= len(goal.proposed_subtasks):
            implementation.status = "completed"
            goal.status = "implemented"

            logger.log("INFO", "AutonomousGoalSetter", f"Completed autonomous goal: {goal.title}")

    def get_goal_status(self) -> Dict[str, Any]:
        """Get comprehensive goal setting status"""

        return {
            "observed_patterns": len(self.observed_patterns),
            "proposed_goals": len(self.proposed_goals),
            "active_implementations": len([i for i in self.implementations.values() if i.status == "in_progress"]),
            "completed_goals": len([g for g in self.proposed_goals.values() if g.status == "implemented"]),
            "goal_types": Counter(g.goal_type.value for g in self.proposed_goals.values()),
            "goal_priorities": Counter(g.priority.value for g in self.proposed_goals.values()),
            "last_goal_generation": self.last_goal_generation,
            "next_goal_generation": self.last_goal_generation + self.goal_generation_interval
        }

    def export_goal_data(self) -> Dict[str, Any]:
        """Export goal setting data for analysis"""

        return {
            "observed_patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "type": p.pattern_type.value,
                    "description": p.description,
                    "frequency": p.frequency,
                    "confidence": p.confidence,
                    "first_observed": p.first_observed,
                    "last_observed": p.last_observed
                }
                for p in self.observed_patterns.values()
            ],
            "proposed_goals": [
                {
                    "goal_id": g.goal_id,
                    "title": g.title,
                    "description": g.description,
                    "type": g.goal_type.value,
                    "priority": g.priority.value,
                    "confidence_score": g.confidence_score,
                    "status": g.status,
                    "proposed_at": g.proposed_at,
                    "based_on_patterns": g.based_on_patterns
                }
                for g in self.proposed_goals.values()
            ],
            "implementations": [
                {
                    "implementation_id": i.implementation_id,
                    "goal_id": i.goal_id,
                    "status": i.status,
                    "started_at": i.started_at,
                    "completed_subtasks": i.completed_subtasks,
                    "outcomes": i.outcomes
                }
                for i in self.implementations.values()
            ],
            "export_timestamp": time.time()
        }

# Global autonomous goal setter instance
autonomous_goal_setter = AutonomousGoalSetter()

# Integration functions
def initialize_autonomous_goals(long_term_memory, working_memory) -> AutonomousGoalSetter:
    """Initialize autonomous goal setting system"""
    # The goal setter is already initialized globally
    # This function can be used to set up any initial goals or configurations
    return autonomous_goal_setter

def generate_autonomous_goals(context: Dict[str, Any]) -> List[ProposedGoal]:
    """Generate autonomous goals based on current context"""
    # This is a simplified version - in practice would analyze the context
    # For now, return any existing proposed goals
    return list(autonomous_goal_setter.proposed_goals.values())

def analyze_memory_for_goals(long_term_memory) -> List[ProposedGoal]:
    """Analyze long-term memory and propose new goals"""
    return autonomous_goal_setter.analyze_long_term_memory(long_term_memory)

def accept_proposed_goal(goal_id: str) -> bool:
    """Accept a proposed goal"""
    return autonomous_goal_setter.accept_goal(goal_id)

def reject_proposed_goal(goal_id: str, reason: str = "") -> bool:
    """Reject a proposed goal"""
    return autonomous_goal_setter.reject_goal(goal_id, reason)

def update_goal_progress(goal_id: str, completed_subtask: str, outcomes: Dict[str, Any] = None):
    """Update goal implementation progress"""
    autonomous_goal_setter.update_goal_progress(goal_id, completed_subtask, outcomes)

def get_goal_setting_status() -> Dict[str, Any]:
    """Get goal setting system status"""
    return autonomous_goal_setter.get_goal_status()

def get_goal_statistics() -> Dict[str, Any]:
    """Get goal statistics (alias for get_goal_setting_status)"""
    return get_goal_setting_status()

def export_goal_data() -> Dict[str, Any]:
    """Export goal setting data"""
    return autonomous_goal_setter.export_goal_data()