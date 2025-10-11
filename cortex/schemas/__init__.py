"""
Cortex schemas package
Contains data models specific to the Knowledge Cortex
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from enum import Enum

class EdgeType(str, Enum):
    RELATED = "related"
    SIMILAR = "similar"
    CAUSES = "causes"
    FOLLOWS = "follows"

class MemoryRecord(BaseModel):
    id: str
    content: str
    text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = {}
    timestamp: float

class QueryRequest(BaseModel):
    query: str
    limit: int = 10
    top_k: int = 10
    filters: Dict[str, Any] = {}
    filter: Dict[str, Any] = {}
    use_graph: bool = False
    use_archive: bool = False

class QueryHit(BaseModel):
    id: str
    content: str
    text: str
    score: float
    metadata: Dict[str, Any] = {}

class QueryResult(BaseModel):
    query: str
    hits: List[QueryHit]
    total: int
    diagnostics: Dict[str, Any] = {}