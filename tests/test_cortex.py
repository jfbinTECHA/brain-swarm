import time
from cortex.cortex import KnowledgeCortex
from cortex.schemas import MemoryRecord, QueryRequest


def test_ingest_and_query(tmp_path, monkeypatch):
    # Point duckdb/faiss to tmp dir if needed by env vars
    c = KnowledgeCortex()

    rec = MemoryRecord(id="r1", text="The apple grows on a tree.", metadata={"topic": "fruit"}, timestamp=time.time())
    c.store_record(rec)

    out = c.query(QueryRequest(query="Where does an apple grow?", top_k=3))
    assert len(out.hits) >= 1