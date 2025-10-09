# cortex/schemas/incident.py
from pydantic import BaseModel
from typing import Optional, Dict

class Incident(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    source: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    status: str = "open"
    created_at: float
    resolved_at: Optional[float] = None