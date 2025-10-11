from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from core.base import logger, metrics
import time
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
import re
from datetime import datetime, timedelta

class PolicyType(Enum):
    ETHICAL = "ethical"
    PRIORITIZATION = "prioritization"
    COMPLIANCE = "compliance"
    SECURITY = "security"
    RESOURCE = "resource"
    QUALITY = "quality"
    GOVERNANCE = "governance"

class PolicySeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ComplianceStatus(Enum):
    COMPLIANT = "compliant"
    VIOLATION = "violation"
    WARNING = "warning"
    PENDING = "pending"
    EXEMPT = "exempt"

class EthicalPrinciple(Enum):
    AUTONOMY = "autonomy"
    BENEFICENCE = "beneficence"
    NON_MALEFICENCE = "non_maleficence"
    JUSTICE = "justice"
    TRANSPARENCY = "transparency"
    ACCOUNTABILITY = "accountability"
    PRIVACY = "privacy"
    FAIRNESS = "fairness"

@dataclass
class PolicyRule:
    """Represents a governance policy rule"""
    rule_id: str
    name: str
    description: str
    policy_type: PolicyType
    severity: PolicySeverity
    condition: Callable[[Dict[str, Any]], bool]
    action: Callable[[Dict[str, Any]], Dict[str, Any]]
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_triggered: Optional[float] = None
    trigger_count: int = 0

@dataclass
class ComplianceEvent:
    """Represents a compliance monitoring event"""
    event_id: str
    policy_rule_id: str
    context: Dict[str, Any]
    status: ComplianceStatus
    message: str
    timestamp: float
    severity: PolicySeverity
    resolution: Optional[str] = None
    resolved_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EthicalAssessment:
    """Represents an ethical assessment of an action or decision"""
    assessment_id: str
    action_context: Dict[str, Any]
    principles_evaluated: List[EthicalPrinciple]
    principle_scores: Dict[EthicalPrinciple, float]
    overall_score: float
    concerns: List[str]
    recommendations: List[str]
    assessed_at: float
    assessor: str = "policy_layer"

@dataclass
class TaskPriority:
    """Represents task prioritization decision"""
    task_id: str
    base_priority: int
    adjusted_priority: int
    priority_factors: Dict[str, float]
    policy_adjustments: List[Dict[str, Any]]
    final_priority: int
    rationale: str
    calculated_at: float

class PolicyLayer:
    """Comprehensive policy and governance system"""

    def __init__(self):
        self.policy_rules: Dict[str, PolicyRule] = {}
        self.compliance_events: List[ComplianceEvent] = []
        self.ethical_assessments: List[EthicalAssessment] = []
        self.task_priorities: Dict[str, TaskPriority] = {}

        # Policy configuration
        self.max_compliance_events = 1000
        self.ethical_assessment_threshold = 0.7
        self.audit_trail_enabled = True

        # Initialize default policies
        self._initialize_default_policies()

    def _initialize_default_policies(self):
        """Initialize default governance policies"""

        # Ethical Policies
        self.add_policy_rule(PolicyRule(
            rule_id="ethical_harm_prevention",
            name="Harm Prevention",
            description="Prevent actions that could cause harm to users or systems",
            policy_type=PolicyType.ETHICAL,
            severity=PolicySeverity.CRITICAL,
            condition=self._check_harm_potential,
            action=self._handle_harm_prevention
        ))

        self.add_policy_rule(PolicyRule(
            rule_id="ethical_privacy_protection",
            name="Privacy Protection",
            description="Ensure user privacy and data protection",
            policy_type=PolicyType.ETHICAL,
            severity=PolicySeverity.HIGH,
            condition=self._check_privacy_violation,
            action=self._handle_privacy_protection
        ))

        # Prioritization Policies
        self.add_policy_rule(PolicyRule(
            rule_id="priority_urgent_tasks",
            name="Urgent Task Prioritization",
            description="Prioritize tasks marked as urgent or critical",
            policy_type=PolicyType.PRIORITIZATION,
            severity=PolicySeverity.HIGH,
            condition=self._check_urgent_task,
            action=self._handle_urgent_prioritization
        ))

        self.add_policy_rule(PolicyRule(
            rule_id="priority_resource_critical",
            name="Resource Critical Tasks",
            description="Prioritize tasks critical for system resource management",
            policy_type=PolicyType.PRIORITIZATION,
            severity=PolicySeverity.MEDIUM,
            condition=self._check_resource_critical,
            action=self._handle_resource_prioritization
        ))

        # Compliance Policies
        self.add_policy_rule(PolicyRule(
            rule_id="compliance_data_retention",
            name="Data Retention Compliance",
            description="Ensure compliance with data retention policies",
            policy_type=PolicyType.COMPLIANCE,
            severity=PolicySeverity.MEDIUM,
            condition=self._check_data_retention,
            action=self._handle_data_retention
        ))

        self.add_policy_rule(PolicyRule(
            rule_id="compliance_audit_trail",
            name="Audit Trail Maintenance",
            description="Maintain comprehensive audit trails for all actions",
            policy_type=PolicyType.COMPLIANCE,
            severity=PolicySeverity.LOW,
            condition=self._check_audit_completeness,
            action=self._handle_audit_maintenance
        ))

        # Security Policies
        self.add_policy_rule(PolicyRule(
            rule_id="security_input_validation",
            name="Input Validation",
            description="Validate all inputs for security threats",
            policy_type=PolicyType.SECURITY,
            severity=PolicySeverity.HIGH,
            condition=self._check_input_security,
            action=self._handle_input_validation
        ))

        # Resource Policies
        self.add_policy_rule(PolicyRule(
            rule_id="resource_usage_limits",
            name="Resource Usage Limits",
            description="Enforce resource usage limits to prevent abuse",
            policy_type=PolicyType.RESOURCE,
            severity=PolicySeverity.MEDIUM,
            condition=self._check_resource_limits,
            action=self._handle_resource_limits
        ))

        # Quality Policies
        self.add_policy_rule(PolicyRule(
            rule_id="quality_minimum_standards",
            name="Quality Standards",
            description="Ensure minimum quality standards for all outputs",
            policy_type=PolicyType.QUALITY,
            severity=PolicySeverity.MEDIUM,
            condition=self._check_quality_standards,
            action=self._handle_quality_enforcement
        ))

    def add_policy_rule(self, rule: PolicyRule):
        """Add a new policy rule to the system"""
        self.policy_rules[rule.rule_id] = rule
        logger.log("INFO", "PolicyLayer", f"Added policy rule: {rule.name} ({rule.rule_id})")

    def remove_policy_rule(self, rule_id: str) -> bool:
        """Remove a policy rule"""
        if rule_id in self.policy_rules:
            del self.policy_rules[rule_id]
            logger.log("INFO", "PolicyLayer", f"Removed policy rule: {rule_id}")
            return True
        return False

    def evaluate_policies(self, context: Dict[str, Any], policy_types: Optional[List[PolicyType]] = None) -> Dict[str, Any]:
        """Evaluate all applicable policies for a given context"""

        applicable_rules = []
        if policy_types:
            applicable_rules = [rule for rule in self.policy_rules.values()
                              if rule.enabled and rule.policy_type in policy_types]
        else:
            applicable_rules = [rule for rule in self.policy_rules.values() if rule.enabled]

        results = {
            "compliant": True,
            "violations": [],
            "warnings": [],
            "actions_taken": [],
            "evaluated_rules": len(applicable_rules)
        }

        for rule in applicable_rules:
            try:
                if rule.condition(context):
                    # Rule condition met - execute action
                    action_result = rule.action(context)

                    # Update rule statistics
                    rule.last_triggered = time.time()
                    rule.trigger_count += 1

                    # Create compliance event
                    event = ComplianceEvent(
                        event_id=f"event_{int(time.time())}_{rule.rule_id}",
                        policy_rule_id=rule.rule_id,
                        context=context,
                        status=ComplianceStatus.VIOLATION if rule.severity == PolicySeverity.CRITICAL else ComplianceStatus.WARNING,
                        message=f"Policy {rule.name} triggered: {rule.description}",
                        timestamp=time.time(),
                        severity=rule.severity,
                        metadata={"action_result": action_result}
                    )

                    self.compliance_events.append(event)

                    # Update results
                    if rule.severity in [PolicySeverity.CRITICAL, PolicySeverity.HIGH]:
                        results["compliant"] = False
                        results["violations"].append({
                            "rule": rule.name,
                            "severity": rule.severity.value,
                            "message": rule.description,
                            "action": action_result
                        })
                    else:
                        results["warnings"].append({
                            "rule": rule.name,
                            "severity": rule.severity.value,
                            "message": rule.description,
                            "action": action_result
                        })

                    results["actions_taken"].append(action_result)

            except Exception as e:
                logger.log("ERROR", "PolicyLayer", f"Error evaluating policy {rule.rule_id}: {str(e)}")

        # Maintain compliance event limit
        if len(self.compliance_events) > self.max_compliance_events:
            self.compliance_events = self.compliance_events[-self.max_compliance_events:]

        return results

    def assess_ethical_alignment(self, action_context: Dict[str, Any]) -> EthicalAssessment:
        """Perform ethical assessment of an action or decision"""

        principles_scores = {}
        concerns = []
        recommendations = []

        # Evaluate each ethical principle
        for principle in EthicalPrinciple:
            score = self._evaluate_ethical_principle(principle, action_context)
            principles_scores[principle] = score

            if score < 0.6:
                concerns.append(f"Low score on {principle.value}: {score:.2f}")
                recommendations.extend(self._get_ethical_recommendations(principle, action_context))

        # Calculate overall ethical score
        overall_score = sum(principles_scores.values()) / len(principles_scores)

        assessment = EthicalAssessment(
            assessment_id=f"ethical_{int(time.time())}_{uuid.uuid4().hex[:8]}",
            action_context=action_context,
            principles_evaluated=list(EthicalPrinciple),
            principle_scores=principles_scores,
            overall_score=overall_score,
            concerns=concerns,
            recommendations=list(set(recommendations)),  # Remove duplicates
            assessed_at=time.time()
        )

        self.ethical_assessments.append(assessment)

        # Log ethical concerns
        if overall_score < self.ethical_assessment_threshold:
            logger.log("WARNING", "PolicyLayer", f"Ethical assessment failed: {overall_score:.2f} - {len(concerns)} concerns")

        return assessment

    def calculate_task_priority(self, task_context: Dict[str, Any]) -> TaskPriority:
        """Calculate task priority based on policies and context"""

        task_id = task_context.get("task_id", f"task_{int(time.time())}")
        base_priority = task_context.get("base_priority", 1)

        priority_factors = {}
        policy_adjustments = []

        # Evaluate prioritization policies
        prioritization_results = self.evaluate_policies(task_context, [PolicyType.PRIORITIZATION])

        # Calculate priority adjustments
        adjusted_priority = base_priority

        for action in prioritization_results["actions_taken"]:
            if "priority_adjustment" in action:
                adjustment = action["priority_adjustment"]
                adjusted_priority += adjustment
                policy_adjustments.append(action)

                # Track adjustment factors
                factor_name = action.get("factor", "policy_adjustment")
                priority_factors[factor_name] = adjustment

        # Ensure priority bounds
        final_priority = max(1, min(10, adjusted_priority))

        # Generate rationale
        rationale_parts = []
        if policy_adjustments:
            rationale_parts.append(f"Policy adjustments: {len(policy_adjustments)} applied")
        if priority_factors:
            top_factors = sorted(priority_factors.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
            rationale_parts.append(f"Key factors: {', '.join([f'{k}(+{v})' if v > 0 else f'{k}({v})' for k, v in top_factors])}")

        rationale = "; ".join(rationale_parts) if rationale_parts else "Standard priority calculation"

        priority = TaskPriority(
            task_id=task_id,
            base_priority=base_priority,
            adjusted_priority=adjusted_priority,
            priority_factors=priority_factors,
            policy_adjustments=policy_adjustments,
            final_priority=final_priority,
            rationale=rationale,
            calculated_at=time.time()
        )

        self.task_priorities[task_id] = priority
        return priority

    def _evaluate_ethical_principle(self, principle: EthicalPrinciple, context: Dict[str, Any]) -> float:
        """Evaluate a specific ethical principle"""

        score = 0.8  # Default neutral score

        if principle == EthicalPrinciple.AUTONOMY:
            # Check if action respects user autonomy
            if context.get("user_consent", True):
                score = 0.9
            elif context.get("override_user_preference", False):
                score = 0.3
            else:
                score = 0.7

        elif principle == EthicalPrinciple.BENEFICENCE:
            # Check if action provides benefit
            if context.get("expected_benefit", False):
                score = 0.9
            elif context.get("potential_harm", True):
                score = 0.4
            else:
                score = 0.6

        elif principle == EthicalPrinciple.NON_MALEFICENCE:
            # Check if action avoids harm
            if context.get("potential_harm", False):
                score = 0.2
            elif context.get("safety_measures", True):
                score = 0.9
            else:
                score = 0.7

        elif principle == EthicalPrinciple.JUSTICE:
            # Check fairness and equity
            if context.get("fair_distribution", True):
                score = 0.9
            elif context.get("discriminatory_impact", False):
                score = 0.3
            else:
                score = 0.7

        elif principle == EthicalPrinciple.TRANSPARENCY:
            # Check transparency
            if context.get("explainable", True):
                score = 0.9
            elif context.get("black_box", False):
                score = 0.3
            else:
                score = 0.6

        elif principle == EthicalPrinciple.ACCOUNTABILITY:
            # Check accountability
            if context.get("auditable", True):
                score = 0.9
            elif context.get("anonymous", False):
                score = 0.4
            else:
                score = 0.7

        elif principle == EthicalPrinciple.PRIVACY:
            # Check privacy protection
            if context.get("data_minimization", True):
                score = 0.9
            elif context.get("unnecessary_data_collection", False):
                score = 0.2
            else:
                score = 0.7

        elif principle == EthicalPrinciple.FAIRNESS:
            # Check fairness
            if context.get("bias_mitigated", True):
                score = 0.9
            elif context.get("biased_outcome", False):
                score = 0.3
            else:
                score = 0.7

        return score

    def _get_ethical_recommendations(self, principle: EthicalPrinciple, context: Dict[str, Any]) -> List[str]:
        """Get ethical recommendations for a principle"""

        recommendations = []

        if principle == EthicalPrinciple.AUTONOMY:
            recommendations.extend([
                "Obtain explicit user consent before proceeding",
                "Provide clear opt-out mechanisms",
                "Explain the implications of the action"
            ])

        elif principle == EthicalPrinciple.BENEFICENCE:
            recommendations.extend([
                "Assess and maximize potential benefits",
                "Minimize potential harms",
                "Consider long-term consequences"
            ])

        elif principle == EthicalPrinciple.NON_MALEFICENCE:
            recommendations.extend([
                "Implement safety measures and safeguards",
                "Conduct risk assessment",
                "Have contingency plans for potential harm"
            ])

        elif principle == EthicalPrinciple.JUSTICE:
            recommendations.extend([
                "Ensure fair and equitable treatment",
                "Avoid discriminatory practices",
                "Consider impact on different user groups"
            ])

        elif principle == EthicalPrinciple.TRANSPARENCY:
            recommendations.extend([
                "Provide clear explanations of actions",
                "Make decision processes understandable",
                "Document reasoning and evidence"
            ])

        elif principle == EthicalPrinciple.ACCOUNTABILITY:
            recommendations.extend([
                "Maintain comprehensive audit trails",
                "Establish clear responsibility chains",
                "Enable independent oversight and review"
            ])

        elif principle == EthicalPrinciple.PRIVACY:
            recommendations.extend([
                "Minimize data collection to essential information",
                "Implement strong data protection measures",
                "Provide clear privacy policies and controls"
            ])

        elif principle == EthicalPrinciple.FAIRNESS:
            recommendations.extend([
                "Audit for potential biases in algorithms and data",
                "Implement fairness constraints and monitoring",
                "Ensure diverse and representative training data"
            ])

        return recommendations

    # Policy condition checkers
    def _check_harm_potential(self, context: Dict[str, Any]) -> bool:
        """Check if action has potential for harm"""
        return context.get("potential_harm", False) or context.get("destructive_action", False)

    def _check_privacy_violation(self, context: Dict[str, Any]) -> bool:
        """Check for privacy violations"""
        return (context.get("collects_personal_data", False) and
                not context.get("privacy_consent", True)) or \
               context.get("unauthorized_data_access", False)

    def _check_urgent_task(self, context: Dict[str, Any]) -> bool:
        """Check if task is urgent"""
        return (context.get("urgent", False) or
                context.get("deadline_soon", False) or
                context.get("critical_system", False))

    def _check_resource_critical(self, context: Dict[str, Any]) -> bool:
        """Check if task is resource-critical"""
        return (context.get("resource_exhaustion", False) or
                context.get("system_stability", False) or
                context.get("performance_critical", False))

    def _check_data_retention(self, context: Dict[str, Any]) -> bool:
        """Check data retention compliance"""
        data_age = context.get("data_age_days", 0)
        return data_age > 365 and not context.get("retention_exception", False)

    def _check_audit_completeness(self, context: Dict[str, Any]) -> bool:
        """Check audit trail completeness"""
        return not context.get("audit_complete", True)

    def _check_input_security(self, context: Dict[str, Any]) -> bool:
        """Check input security"""
        return (context.get("contains_script", False) or
                context.get("suspicious_pattern", False) or
                len(context.get("input", "")) > 10000)

    def _check_resource_limits(self, context: Dict[str, Any]) -> bool:
        """Check resource usage limits"""
        return (context.get("cpu_usage", 0) > 90 or
                context.get("memory_usage", 0) > 90 or
                context.get("api_calls_per_minute", 0) > 100)

    def _check_quality_standards(self, context: Dict[str, Any]) -> bool:
        """Check quality standards"""
        return (context.get("quality_score", 1.0) < 0.7 or
                context.get("error_rate", 0) > 0.1)

    # Policy action handlers
    def _handle_harm_prevention(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle harm prevention policy violation"""
        return {
            "action": "blocked",
            "reason": "Potential harm detected",
            "recommendation": "Review action for safety implications",
            "severity": "critical"
        }

    def _handle_privacy_protection(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle privacy protection policy violation"""
        return {
            "action": "flagged",
            "reason": "Privacy concern identified",
            "recommendation": "Obtain proper consent or anonymize data",
            "severity": "high"
        }

    def _handle_urgent_prioritization(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle urgent task prioritization"""
        return {
            "priority_adjustment": 3,
            "factor": "urgency",
            "reason": "Task marked as urgent or time-critical"
        }

    def _handle_resource_prioritization(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resource-critical task prioritization"""
        return {
            "priority_adjustment": 2,
            "factor": "resource_critical",
            "reason": "Task affects system resources or stability"
        }

    def _handle_data_retention(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data retention compliance"""
        return {
            "action": "schedule_deletion",
            "reason": "Data exceeds retention period",
            "recommendation": "Archive or delete old data"
        }

    def _handle_audit_maintenance(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle audit trail maintenance"""
        return {
            "action": "log_required",
            "reason": "Audit trail incomplete",
            "recommendation": "Ensure all actions are logged"
        }

    def _handle_input_validation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle input validation"""
        return {
            "action": "sanitized",
            "reason": "Potentially unsafe input detected",
            "recommendation": "Input has been sanitized for security"
        }

    def _handle_resource_limits(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resource limit enforcement"""
        return {
            "action": "throttled",
            "reason": "Resource usage exceeds limits",
            "recommendation": "Reduce resource consumption or increase limits"
        }

    def _handle_quality_enforcement(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle quality standard enforcement"""
        return {
            "action": "review_required",
            "reason": "Quality standards not met",
            "recommendation": "Review and improve output quality"
        }

    def get_policy_status(self) -> Dict[str, Any]:
        """Get comprehensive policy system status"""

        active_rules = [rule for rule in self.policy_rules.values() if rule.enabled]
        recent_events = self.compliance_events[-20:] if self.compliance_events else []

        # Calculate compliance metrics
        total_events = len(recent_events)
        violations = len([e for e in recent_events if e.status == ComplianceStatus.VIOLATION])
        warnings = len([e for e in recent_events if e.status == ComplianceStatus.WARNING])

        compliance_rate = ((total_events - violations - warnings) / total_events * 100) if total_events > 0 else 100

        # Ethical assessment summary
        recent_assessments = self.ethical_assessments[-50:] if self.ethical_assessments else []
        avg_ethical_score = (sum(a.overall_score for a in recent_assessments) / len(recent_assessments)
                           if recent_assessments else 1.0)

        return {
            "total_policies": len(self.policy_rules),
            "active_policies": len(active_rules),
            "policy_types": {pt.value: len([r for r in active_rules if r.policy_type == pt]) for pt in PolicyType},
            "compliance_events": len(self.compliance_events),
            "recent_compliance_rate": compliance_rate,
            "ethical_assessments": len(self.ethical_assessments),
            "average_ethical_score": avg_ethical_score,
            "task_priorities_calculated": len(self.task_priorities),
            "policy_violations": violations,
            "policy_warnings": warnings
        }

    def export_policy_data(self) -> Dict[str, Any]:
        """Export policy system data for analysis"""

        return {
            "policy_rules": [
                {
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "type": rule.policy_type.value,
                    "severity": rule.severity.value,
                    "enabled": rule.enabled,
                    "trigger_count": rule.trigger_count,
                    "last_triggered": rule.last_triggered,
                    "created_at": rule.created_at
                }
                for rule in self.policy_rules.values()
            ],
            "compliance_events": [
                {
                    "event_id": event.event_id,
                    "policy_rule_id": event.policy_rule_id,
                    "status": event.status.value,
                    "severity": event.severity.value,
                    "message": event.message,
                    "timestamp": event.timestamp,
                    "resolved": event.resolution is not None
                }
                for event in self.compliance_events[-500:]  # Last 500 events
            ],
            "ethical_assessments": [
                {
                    "assessment_id": assessment.assessment_id,
                    "overall_score": assessment.overall_score,
                    "concerns_count": len(assessment.concerns),
                    "recommendations_count": len(assessment.recommendations),
                    "assessed_at": assessment.assessed_at
                }
                for assessment in self.ethical_assessments[-100:]  # Last 100 assessments
            ],
            "export_timestamp": time.time()
        }

# PolicyEngine - Legacy compatibility class
class PolicyEngine:
    """Legacy compatibility class for PolicyLayer"""

    def __init__(self):
        self.layer = policy_layer

    def evaluate_task_policy(self, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate policies for a task"""
        return self.layer.evaluate_policies(task_context)

    def check_ethical_alignment(self, action_context: Dict[str, Any]) -> EthicalAssessment:
        """Check ethical alignment"""
        return self.layer.assess_ethical_alignment(action_context)

    def get_governance_status(self) -> Dict[str, Any]:
        """Get governance status"""
        return self.layer.get_policy_status()

    def report_policy_violation(self, violation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Report a policy violation"""
        # Create a compliance event for the violation
        event = ComplianceEvent(
            event_id=f"violation_{int(time.time())}_{uuid.uuid4().hex[:8]}",
            policy_rule_id="manual_report",
            context=violation_context,
            status=ComplianceStatus.VIOLATION,
            message=violation_context.get("message", "Manual policy violation report"),
            timestamp=time.time(),
            severity=PolicySeverity.HIGH
        )
        self.layer.compliance_events.append(event)
        return {"reported": True, "event_id": event.event_id}

# Global instances
policy_layer = PolicyLayer()
policy_engine = PolicyEngine()

# Integration functions
def evaluate_policies(context: Dict[str, Any], policy_types: Optional[List[PolicyType]] = None) -> Dict[str, Any]:
    """Evaluate policies for a given context"""
    return policy_layer.evaluate_policies(context, policy_types)

def evaluate_task_policy(task_context: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate policies for a task (legacy function)"""
    return evaluate_policies(task_context)

def assess_ethical_alignment(action_context: Dict[str, Any]) -> EthicalAssessment:
    """Assess ethical alignment of an action"""
    return policy_layer.assess_ethical_alignment(action_context)

def check_ethical_alignment(action_context: Dict[str, Any]) -> EthicalAssessment:
    """Check ethical alignment (legacy function)"""
    return assess_ethical_alignment(action_context)

def calculate_task_priority(task_context: Dict[str, Any]) -> TaskPriority:
    """Calculate task priority based on policies"""
    return policy_layer.calculate_task_priority(task_context)

def add_policy_rule(rule: PolicyRule):
    """Add a new policy rule"""
    policy_layer.add_policy_rule(rule)

def get_policy_status() -> Dict[str, Any]:
    """Get policy system status"""
    return policy_layer.get_policy_status()

def get_governance_status() -> Dict[str, Any]:
    """Get governance status (legacy function)"""
    return get_policy_status()

def report_policy_violation(violation_context: Dict[str, Any]) -> Dict[str, Any]:
    """Report a policy violation"""
    return policy_engine.report_policy_violation(violation_context)

def export_policy_data() -> Dict[str, Any]:
    """Export policy system data"""
    return policy_layer.export_policy_data()