"""
Knowledge Cortex API
--------------------
FastAPI endpoints for /cortex/ingest and /cortex/query
"""

from fastapi import APIRouter, Body
from .vector_layer import add_embedding, query_similar
from .metrics import CORTEX_INGEST_TOTAL, CORTEX_QUERY_TOTAL

router = APIRouter()

@router.post("/ingest")
def ingest_record(record: dict = Body(...)):
    add_embedding(record["id"], record["vector"], record["metadata"])
    CORTEX_INGEST_TOTAL.inc()
    return {"status": "ok", "id": record["id"]}

@router.post("/query")
def query_record(payload: dict = Body(...)):
    results = query_similar(payload["vector"])
    CORTEX_QUERY_TOTAL.inc()
    return {"matches": results}