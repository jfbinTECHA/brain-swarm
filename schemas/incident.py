"""
Shared schemas for incident and alert handling
Used by SwarmOps Hook and Kilo Code AI orchestration
"""

from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime


class AlertData(BaseModel):
    """Individual alert data from Alertmanager"""
    labels: Dict[str, str]
    annotations: Dict[str, str]
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None
    value: Optional[str] = None


class AlertGroup(BaseModel):
    """Alertmanager webhook payload"""
    version: str
    groupKey: str
    status: str  # "firing" or "resolved"
    receiver: str
    groupLabels: Dict[str, str]
    commonLabels: Dict[str, str]
    commonAnnotations: Dict[str, str]
    externalURL: str
    alerts: List[AlertData]


class IncidentContext(BaseModel):
    """Enriched incident context for AI processing"""
    alert_group: AlertGroup
    incident_id: str
    created_at: datetime
    severity_score: float  # 0.0 to 1.0
    affected_services: List[str]
    suggested_actions: List[str]
    ai_analysis: Optional[Dict[str, Any]] = None
    resolution_steps: Optional[List[str]] = None


class IncidentResponse(BaseModel):
    """AI-generated response for incident handling"""
    incident_id: str
    summary: str
    triage_recommendation: str
    suggested_fixes: List[str]
    debug_steps: List[str]
    test_suggestions: List[str]
    confidence_score: float
    requires_human_intervention: bool
    escalation_recommended: bool


class TicketReference(BaseModel):
    """Reference to created tickets"""
    system: str  # "jira", "github", "servicenow"
    ticket_id: str
    url: str
    created_at: datetime


class IncidentStatus(BaseModel):
    """Complete incident status"""
    incident_id: str
    status: str  # "open", "investigating", "resolved", "closed"
    alerts: List[AlertData]
    tickets: List[TicketReference]
    ai_responses: List[IncidentResponse]
    last_updated: datetime
    resolution_time: Optional[int] = None  # seconds