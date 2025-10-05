"""
Alerting system for Brain Swarm
Provides monitoring dashboards, alerts, and notification capabilities
"""

import time
import smtplib
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Alert:
    """Represents an alert"""
    alert_id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    source: str
    component: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    created_at: float
    updated_at: float
    resolved_at: Optional[float] = None
    acknowledged_at: Optional[float] = None
    acknowledged_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "source": self.source,
            "component": self.component,
            "labels": self.labels,
            "annotations": self.annotations,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
            "acknowledged_at": self.acknowledged_at,
            "acknowledged_by": self.acknowledged_by
        }


class AlertRule:
    """Represents an alerting rule"""

    def __init__(self, rule_id: str, name: str, description: str,
                 condition: Callable[[Dict[str, Any]], bool],
                 severity: AlertSeverity, cooldown_seconds: int = 300,
                 labels: Dict[str, str] = None, annotations: Dict[str, str] = None):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.condition = condition
        self.severity = severity
        self.cooldown_seconds = cooldown_seconds
        self.labels = labels or {}
        self.annotations = annotations or {}
        self.last_triggered: Optional[float] = None

    def should_trigger(self, context: Dict[str, Any]) -> bool:
        """Check if the rule should trigger an alert"""
        # Check cooldown
        if self.last_triggered and (time.time() - self.last_triggered) < self.cooldown_seconds:
            return False

        # Evaluate condition
        try:
            return self.condition(context)
        except Exception:
            return False

    def trigger(self, context: Dict[str, Any]) -> Alert:
        """Trigger the alert"""
        self.last_triggered = time.time()

        alert = Alert(
            alert_id=f"{self.rule_id}_{int(time.time())}",
            title=self.name,
            description=self.description,
            severity=self.severity,
            status=AlertStatus.ACTIVE,
            source="alert_rule",
            component=self.rule_id,
            labels=self.labels.copy(),
            annotations=self.annotations.copy(),
            created_at=time.time(),
            updated_at=time.time()
        )

        # Add context-specific labels
        alert.labels.update({
            "rule_id": self.rule_id,
            "trigger_time": str(int(time.time()))
        })

        return alert


class NotificationChannel:
    """Base class for notification channels"""

    def send_alert(self, alert: Alert) -> bool:
        """Send an alert notification"""
        raise NotImplementedError


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel"""

    def __init__(self, smtp_server: str, smtp_port: int, username: str,
                 password: str, from_address: str, to_addresses: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_address = from_address
        self.to_addresses = to_addresses

    def send_alert(self, alert: Alert) -> bool:
        """Send alert via email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_address
            msg['To'] = ', '.join(self.to_addresses)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"

            body = f"""
Brain Swarm Alert

Title: {alert.title}
Description: {alert.description}
Severity: {alert.severity.value}
Status: {alert.status.value}
Component: {alert.component}
Source: {alert.source}

Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.created_at))}

Labels: {json.dumps(alert.labels, indent=2)}
Annotations: {json.dumps(alert.annotations, indent=2)}
"""
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.from_address, self.to_addresses, text)
            server.quit()

            return True

        except Exception as e:
            print(f"Failed to send email alert: {e}")
            return False


class WebhookNotificationChannel(NotificationChannel):
    """Webhook notification channel"""

    def __init__(self, webhook_url: str, headers: Dict[str, str] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {}

    def send_alert(self, alert: Alert) -> bool:
        """Send alert via webhook"""
        try:
            import requests
            payload = alert.to_dict()

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={**self.headers, "Content-Type": "application/json"},
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:
            print(f"Failed to send webhook alert: {e}")
            return False


class AlertManager:
    """Manages alerts and notifications"""

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.rules: Dict[str, AlertRule] = {}
        self.notification_channels: List[NotificationChannel] = []
        self.alert_history: List[Alert] = []
        self.max_history = 1000
        self.alert_callbacks: List[Callable] = []

    def register_rule(self, rule: AlertRule):
        """Register an alert rule"""
        self.rules[rule.rule_id] = rule

    def unregister_rule(self, rule_id: str):
        """Unregister an alert rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]

    def add_notification_channel(self, channel: NotificationChannel):
        """Add a notification channel"""
        self.notification_channels.append(channel)

    def register_alert_callback(self, callback: Callable):
        """Register a callback for alert events"""
        self.alert_callbacks.append(callback)

    def evaluate_rules(self, context: Dict[str, Any]):
        """Evaluate all alert rules against the current context"""
        for rule in self.rules.values():
            if rule.should_trigger(context):
                alert = rule.trigger(context)
                self.fire_alert(alert)

    def fire_alert(self, alert: Alert):
        """Fire an alert"""
        # Store alert
        self.alerts[alert.alert_id] = alert
        self.alert_history.append(alert)

        # Maintain history size
        if len(self.alert_history) > self.max_history:
            self.alert_history.pop(0)

        # Send notifications
        self._send_notifications(alert)

        # Trigger callbacks
        self._trigger_callbacks(alert)

        from ..core.base import logger
        logger.log("WARNING", "AlertManager", f"Alert fired: {alert.title}",
                  {"alert_id": alert.alert_id, "severity": alert.severity.value})

    def resolve_alert(self, alert_id: str, resolved_by: str = "system"):
        """Resolve an alert"""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = time.time()
            alert.updated_at = time.time()

            from ..core.base import logger
            logger.log("INFO", "AlertManager", f"Alert resolved: {alert.title}",
                      {"alert_id": alert_id, "resolved_by": resolved_by})

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert"""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = time.time()
            alert.acknowledged_by = acknowledged_by
            alert.updated_at = time.time()

            from ..core.base import logger
            logger.log("INFO", "AlertManager", f"Alert acknowledged: {alert.title}",
                      {"alert_id": alert_id, "acknowledged_by": acknowledged_by})

    def _send_notifications(self, alert: Alert):
        """Send alert notifications through all channels"""
        for channel in self.notification_channels:
            try:
                success = channel.send_alert(alert)
                if not success:
                    print(f"Failed to send alert via {type(channel).__name__}")
            except Exception as e:
                print(f"Error sending alert via {type(channel).__name__}: {e}")

    def _trigger_callbacks(self, alert: Alert):
        """Trigger alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Alert callback failed: {e}")

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return [alert for alert in self.alerts.values()
                if alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]]

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        return self.alert_history[-limit:]

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for monitoring"""
        active_alerts = self.get_active_alerts()
        recent_alerts = self.get_alert_history(50)

        # Group alerts by severity
        severity_counts = {}
        for alert in active_alerts:
            severity = alert.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Group alerts by component
        component_counts = {}
        for alert in active_alerts:
            component = alert.component
            component_counts[component] = component_counts.get(component, 0) + 1

        # Recent alert timeline
        timeline = []
        for alert in recent_alerts[-20:]:  # Last 20 alerts
            timeline.append({
                "time": alert.created_at,
                "severity": alert.severity.value,
                "title": alert.title,
                "component": alert.component,
                "status": alert.status.value
            })

        return {
            "active_alerts": len(active_alerts),
            "severity_breakdown": severity_counts,
            "component_breakdown": component_counts,
            "timeline": timeline,
            "rules_active": len(self.rules),
            "channels_configured": len(self.notification_channels),
            "generated_at": time.time()
        }


# Predefined alert rules
def high_cpu_usage_rule(context: Dict[str, Any]) -> bool:
    """Alert when CPU usage is high"""
    cpu_percent = context.get("cpu_percent", 0)
    return cpu_percent > 90


def high_memory_usage_rule(context: Dict[str, Any]) -> bool:
    """Alert when memory usage is high"""
    memory_percent = context.get("memory_percent", 0)
    return memory_percent > 90


def agent_failure_rate_rule(context: Dict[str, Any]) -> bool:
    """Alert when agent failure rate is high"""
    agent_stats = context.get("agent_stats", {})
    for agent_id, stats in agent_stats.items():
        failure_rate = stats.get("failure_rate", 0)
        if failure_rate > 0.5:  # 50% failure rate
            return True
    return False


def task_queue_backlog_rule(context: Dict[str, Any]) -> bool:
    """Alert when task queue has a large backlog"""
    queue_size = context.get("queue_size", 0)
    return queue_size > 1000


def security_violation_rule(context: Dict[str, Any]) -> bool:
    """Alert on security violations"""
    violations = context.get("security_violations", [])
    return len(violations) > 0


# Global alert manager instance
alert_manager = AlertManager()

# Register default alert rules
alert_manager.register_rule(AlertRule(
    rule_id="high_cpu_usage",
    name="High CPU Usage",
    description="CPU usage exceeds 90%",
    condition=high_cpu_usage_rule,
    severity=AlertSeverity.WARNING,
    cooldown_seconds=300,  # 5 minutes
    labels={"category": "system", "resource": "cpu"},
    annotations={"summary": "High CPU usage detected", "runbook": "Check system processes and scale if needed"}
))

alert_manager.register_rule(AlertRule(
    rule_id="high_memory_usage",
    name="High Memory Usage",
    description="Memory usage exceeds 90%",
    condition=high_memory_usage_rule,
    severity=AlertSeverity.ERROR,
    cooldown_seconds=300,
    labels={"category": "system", "resource": "memory"},
    annotations={"summary": "High memory usage detected", "runbook": "Check memory leaks and consider scaling"}
))

alert_manager.register_rule(AlertRule(
    rule_id="agent_failure_rate",
    name="High Agent Failure Rate",
    description="Agent failure rate exceeds 50%",
    condition=agent_failure_rate_rule,
    severity=AlertSeverity.ERROR,
    cooldown_seconds=600,  # 10 minutes
    labels={"category": "agents", "type": "reliability"},
    annotations={"summary": "High agent failure rate detected", "runbook": "Check agent health and redeploy if needed"}
))

alert_manager.register_rule(AlertRule(
    rule_id="task_queue_backlog",
    name="Task Queue Backlog",
    description="Task queue size exceeds 1000",
    condition=task_queue_backlog_rule,
    severity=AlertSeverity.WARNING,
    cooldown_seconds=300,
    labels={"category": "tasks", "type": "performance"},
    annotations={"summary": "Large task queue backlog", "runbook": "Scale up workers or check for bottlenecks"}
))

alert_manager.register_rule(AlertRule(
    rule_id="security_violation",
    name="Security Violation",
    description="Security policy violation detected",
    condition=security_violation_rule,
    severity=AlertSeverity.CRITICAL,
    cooldown_seconds=60,  # 1 minute
    labels={"category": "security", "type": "violation"},
    annotations={"summary": "Security violation detected", "runbook": "Review security logs and take immediate action"}
))