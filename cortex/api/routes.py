from fastapi import APIRouter, Depends, HTTPException
from ..cortex import KnowledgeCortex
from ..schemas import MemoryRecord, QueryRequest, QueryResult

# If you have JWT deps already, import here and plug into Depends
# from security.jwt import jwt_required

router = APIRouter(prefix="/cortex", tags=["cortex"])

_cortex = KnowledgeCortex()

@router.post("/ingest")
# async def ingest(rec: MemoryRecord, auth=Depends(jwt_required)):
async def ingest(rec: MemoryRecord):
    try:
        _cortex.store_record(rec)
        return {"status": "ok", "id": rec.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query", response_model=QueryResult)
# async def query(req: QueryRequest, auth=Depends(jwt_required)):
async def query(req: QueryRequest):
    try:
        return _cortex.query(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))