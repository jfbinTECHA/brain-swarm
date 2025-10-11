# brainswarm.schemas.incident
# Minimal stub for alerting and incident schemas

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class Alert(BaseModel):
    id: str
    severity: str = "info"
    message: str
    timestamp: datetime = datetime.utcnow()

class AlertGroup(BaseModel):
    id: str
    name: str
    alerts: List[Alert] = []
    created_at: datetime = datetime.utcnow()
    metadata: Optional[Dict[str, Any]] = None
