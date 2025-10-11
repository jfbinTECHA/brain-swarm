"""
Governance and policy compliance monitoring for Brain Swarm
Ensures system operations comply with policies, regulations, and best practices
"""

import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import re

from ..core.base import logger


class ComplianceLevel(Enum):
    """Compliance severity levels"""
    INFO = "info"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"


class PolicyCategory(Enum):
    """Policy categories"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    COMPLIANCE = "compliance"
    GOVERNANCE = "governance"
    OPERATIONAL = "operational"


@dataclass
class PolicyRule:
    """Represents a governance policy rule"""
    id: str
    name: str
    description: str
    category: PolicyCategory
    severity: ComplianceLevel
    enabled: bool = True
    check_function: Optional[Callable] = None
    parameters: Dict[str, Any] = None
    remediation_steps: List[str] = None

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate the policy rule against a context"""
        if not self.enabled or not self.check_function:
            return {
                "rule_id": self.id,
                "status": "skipped",
                "message": "Rule disabled or no check function",
                "severity": self.severity.value
            }

        try:
            result = self.check_function(context, **(self.parameters or {}))
            return {
                "rule_id": self.id,
                "status": result.get("status", "unknown"),
                "message": result.get("message", ""),
                "details": result.get("details", {}),
                "severity": self.severity.value,
                "remediation": self.remediation_steps or []
            }
        except Exception as e:
            return {
                "rule_id": self.id,
                "status": "error",
                "message": f"Policy evaluation failed: {str(e)}",
                "details": {"error": str(e)},
                "severity": self.severity.value
            }


@dataclass
class ComplianceEvent:
    """Represents a compliance monitoring event"""
    timestamp: float
    rule_id: str
    status: str
    message: str
    details: Dict[str, Any]
    severity: str
    category: str
    context: Dict[str, Any]


class GovernanceMonitor:
    """Monitors system governance and policy compliance"""

    def __init__(self):
        self.policies: Dict[str, PolicyRule] = {}
        self.compliance_events: List[ComplianceEvent] = []
        self.max_events = 10000
        self.evaluation_schedule: Dict[str, float] = {}  # rule_id -> next evaluation time
        self.alert_callbacks: List[Callable] = []

    def register_policy(self, policy: PolicyRule):
        """Register a governance policy"""
        self.policies[policy.id] = policy
        logger.log("INFO", "GovernanceMonitor", f"Registered policy: {policy.name}",
                  {"policy_id": policy.id, "category": policy.category.value})

    def unregister_policy(self, policy_id: str):
        """Unregister a governance policy"""
        if policy_id in self.policies:
            del self.policies[policy_id]
            if policy_id in self.evaluation_schedule:
                del self.evaluation_schedule[policy_id]

    def evaluate_policy(self, policy_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a specific policy"""
        policy = self.policies.get(policy_id)
        if not policy:
            return {
                "rule_id": policy_id,
                "status": "not_found",
                "message": "Policy not found"
            }

        result = policy.evaluate(context)

        # Create compliance event
        event = ComplianceEvent(
            timestamp=time.time(),
            rule_id=policy_id,
            status=result["status"],
            message=result["message"],
            details=result["details"],
            severity=result["severity"],
            category=policy.category.value,
            context=context
        )

        self._record_event(event)

        # Trigger alerts for violations
        if result["status"] in ["violation", "error"] and result["severity"] in ["violation", "critical"]:
            self._trigger_alerts(event)

        return result

    def evaluate_all_policies(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate all registered policies"""
        results = {}
        violations = []
        warnings = []

        for policy_id, policy in self.policies.items():
            result = self.evaluate_policy(policy_id, context)
            results[policy_id] = result

            if result["status"] == "violation":
                violations.append(result)
            elif result["status"] == "warning":
                warnings.append(result)

        summary = {
            "total_policies": len(results),
            "violations": len(violations),
            "warnings": len(warnings),
            "compliant": len(results) - len(violations) - len(warnings),
            "results": results,
            "timestamp": time.time()
        }

        # Log summary
        if violations:
            logger.log("WARNING", "GovernanceMonitor",
                      f"Policy evaluation complete: {len(violations)} violations, {len(warnings)} warnings",
                      {"violations": [v["rule_id"] for v in violations]})
        else:
            logger.log("INFO", "GovernanceMonitor",
                      f"Policy evaluation complete: all {len(results)} policies compliant")

        return summary

    def schedule_evaluation(self, policy_id: str, interval_seconds: float):
        """Schedule periodic evaluation of a policy"""
        self.evaluation_schedule[policy_id] = time.time() + interval_seconds

    def run_scheduled_evaluations(self, context: Dict[str, Any]):
        """Run all scheduled policy evaluations"""
        current_time = time.time()

        for policy_id, next_time in list(self.evaluation_schedule.items()):
            if current_time >= next_time:
                self.evaluate_policy(policy_id, context)
                # Reschedule
                interval = 300  # Default 5 minutes, could be configurable
                self.evaluation_schedule[policy_id] = current_time + interval

    def register_alert_callback(self, callback: Callable):
        """Register a callback for compliance alerts"""
        self.alert_callbacks.append(callback)

    def _record_event(self, event: ComplianceEvent):
        """Record a compliance event"""
        self.compliance_events.append(event)

        # Maintain size limit
        if len(self.compliance_events) > self.max_events:
            self.compliance_events.pop(0)

    def _trigger_alerts(self, event: ComplianceEvent):
        """Trigger alerts for compliance violations"""
        for callback in self.alert_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.log("ERROR", "GovernanceMonitor", f"Alert callback failed: {e}",
                          {"callback": str(callback), "event": event.rule_id})

    def get_compliance_report(self, start_time: Optional[float] = None,
                            end_time: Optional[float] = None) -> Dict[str, Any]:
        """Generate a compliance report"""
        events = self.compliance_events

        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        # Analyze events
        total_events = len(events)
        violations = [e for e in events if e.status == "violation"]
        warnings = [e for e in events if e.status == "warning"]
        errors = [e for e in events if e.status == "error"]

        # Group by category
        category_stats = {}
        for event in events:
            cat = event.category
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "violations": 0, "warnings": 0}
            category_stats[cat]["total"] += 1
            if event.status == "violation":
                category_stats[cat]["violations"] += 1
            elif event.status == "warning":
                category_stats[cat]["warnings"] += 1

        # Compliance score (0-100, higher is better)
        if total_events > 0:
            violation_rate = len(violations) / total_events
            compliance_score = max(0, 100 - (violation_rate * 100))
        else:
            compliance_score = 100

        return {
            "report_period": {
                "start_time": start_time,
                "end_time": end_time or time.time()
            },
            "summary": {
                "total_events": total_events,
                "violations": len(violations),
                "warnings": len(warnings),
                "errors": len(errors),
                "compliance_score": compliance_score
            },
            "category_breakdown": category_stats,
            "recent_violations": [
                {
                    "rule_id": e.rule_id,
                    "message": e.message,
                    "severity": e.severity,
                    "timestamp": e.timestamp
                }
                for e in violations[-10:]  # Last 10 violations
            ],
            "generated_at": time.time()
        }

    def get_policy_status(self) -> Dict[str, Any]:
        """Get status of all registered policies"""
        return {
            policy_id: {
                "name": policy.name,
                "category": policy.category.value,
                "severity": policy.severity.value,
                "enabled": policy.enabled,
                "description": policy.description
            }
            for policy_id, policy in self.policies.items()
        }


# Predefined policy check functions
def check_agent_load_policy(context: Dict[str, Any], max_load: float = 0.8) -> Dict[str, Any]:
    """Check agent load policy"""
    agent_loads = context.get("agent_loads", {})

    overloaded_agents = []
    for agent_id, load in agent_loads.items():
        if load > max_load:
            overloaded_agents.append({"agent_id": agent_id, "load": load})

    if overloaded_agents:
        return {
            "status": "violation",
            "message": f"{len(overloaded_agents)} agents exceed maximum load of {max_load}",
            "details": {"overloaded_agents": overloaded_agents, "max_load": max_load}
        }

    return {
        "status": "compliant",
        "message": f"All agents within load limits (max: {max_load})",
        "details": {"agent_count": len(agent_loads), "max_load": max_load}
    }


def check_task_failure_rate_policy(context: Dict[str, Any], max_failure_rate: float = 0.1) -> Dict[str, Any]:
    """Check task failure rate policy"""
    task_stats = context.get("task_stats", {})
    total_tasks = task_stats.get("total", 0)
    failed_tasks = task_stats.get("failed", 0)

    if total_tasks == 0:
        return {
            "status": "compliant",
            "message": "No tasks executed yet",
            "details": {"total_tasks": 0}
        }

    failure_rate = failed_tasks / total_tasks

    if failure_rate > max_failure_rate:
        return {
            "status": "violation",
            "message": f"Task failure rate {failure_rate:.2%} exceeds maximum of {max_failure_rate:.2%}",
            "details": {
                "failure_rate": failure_rate,
                "max_failure_rate": max_failure_rate,
                "total_tasks": total_tasks,
                "failed_tasks": failed_tasks
            }
        }

    return {
        "status": "compliant",
        "message": f"Task failure rate {failure_rate:.2%} within acceptable limits",
        "details": {
            "failure_rate": failure_rate,
            "max_failure_rate": max_failure_rate,
            "total_tasks": total_tasks,
            "failed_tasks": failed_tasks
        }
    }


def check_security_audit_policy(context: Dict[str, Any], max_age_hours: int = 24) -> Dict[str, Any]:
    """Check security audit log freshness"""
    last_audit_time = context.get("last_audit_time")

    if not last_audit_time:
        return {
            "status": "violation",
            "message": "No audit logs found",
            "details": {"last_audit_time": None}
        }

    age_hours = (time.time() - last_audit_time) / 3600

    if age_hours > max_age_hours:
        return {
            "status": "violation",
            "message": f"Security audit logs are {age_hours:.1f} hours old (max allowed: {max_age_hours}h)",
            "details": {"age_hours": age_hours, "max_age_hours": max_age_hours, "last_audit_time": last_audit_time}
        }

    return {
        "status": "compliant",
        "message": f"Security audit logs are current ({age_hours:.1f}h old)",
        "details": {"age_hours": age_hours, "max_age_hours": max_age_hours}
    }


def check_data_retention_policy(context: Dict[str, Any], max_age_days: int = 90) -> Dict[str, Any]:
    """Check data retention policy compliance"""
    old_data_count = context.get("old_data_count", 0)
    total_data_count = context.get("total_data_count", 0)

    if total_data_count == 0:
        return {
            "status": "compliant",
            "message": "No data to check retention for",
            "details": {"total_data_count": 0}
        }

    old_data_percentage = old_data_count / total_data_count

    if old_data_percentage > 0.1:  # More than 10% old data
        return {
            "status": "warning",
            "message": f"{old_data_percentage:.1%} of data exceeds retention period of {max_age_days} days",
            "details": {
                "old_data_count": old_data_count,
                "total_data_count": total_data_count,
                "old_data_percentage": old_data_percentage,
                "max_age_days": max_age_days
            }
        }

    return {
        "status": "compliant",
        "message": f"Data retention compliant ({old_data_percentage:.1%} exceeds limit)",
        "details": {
            "old_data_count": old_data_count,
            "total_data_count": total_data_count,
            "max_age_days": max_age_days
        }
    }


# Global governance monitor instance
governance_monitor = GovernanceMonitor()

# Register default policies
governance_monitor.register_policy(PolicyRule(
    id="agent_load_limit",
    name="Agent Load Limit",
    description="Ensures no agent exceeds maximum load threshold",
    category=PolicyCategory.PERFORMANCE,
    severity=ComplianceLevel.WARNING,
    check_function=check_agent_load_policy,
    parameters={"max_load": 0.8},
    remediation_steps=[
        "Reduce task assignments to overloaded agents",
        "Scale up additional agent instances",
        "Review task distribution algorithm"
    ]
))

governance_monitor.register_policy(PolicyRule(
    id="task_failure_rate",
    name="Task Failure Rate Limit",
    description="Monitors task failure rates for system reliability",
    category=PolicyCategory.RELIABILITY,
    severity=ComplianceLevel.VIOLATION,
    check_function=check_task_failure_rate_policy,
    parameters={"max_failure_rate": 0.1},
    remediation_steps=[
        "Investigate root causes of task failures",
        "Improve error handling in task execution",
        "Review agent capabilities and task assignments"
    ]
))

governance_monitor.register_policy(PolicyRule(
    id="security_audit_freshness",
    name="Security Audit Freshness",
    description="Ensures security audit logs are current",
    category=PolicyCategory.SECURITY,
    severity=ComplianceLevel.CRITICAL,
    check_function=check_security_audit_policy,
    parameters={"max_age_hours": 24},
    remediation_steps=[
        "Check audit logging system status",
        "Verify audit log storage and rotation",
        "Review system monitoring configuration"
    ]
))

governance_monitor.register_policy(PolicyRule(
    id="data_retention_compliance",
    name="Data Retention Compliance",
    description="Ensures data retention policies are followed",
    category=PolicyCategory.COMPLIANCE,
    severity=ComplianceLevel.WARNING,
    check_function=check_data_retention_policy,
    parameters={"max_age_days": 90},
    remediation_steps=[
        "Implement automated data cleanup procedures",
        "Review data retention policies",
        "Archive old data to long-term storage"
    ]
))