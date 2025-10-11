from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class EdgeType(str, Enum):
    TEMPORAL = "temporal"
    SEMANTIC = "semantic"
    RELATIONAL = "relational"

class MemoryRecord(BaseModel):
    id: str
    text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[float] = None  # unix seconds

class QueryRequest(BaseModel):
    query: str
    top_k: int = 8
    filter: Optional[Dict[str, Any]] = None
    use_graph: bool = True
    use_archive: bool = True

class QueryHit(BaseModel):
    id: str
    score: float
    text: str
    metadata: Dict[str, Any]

class QueryResult(BaseModel):
    hits: List[QueryHit]
    diagnostics: Dict[str, Any] = Field(default_factory=dict)