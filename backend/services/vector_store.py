import os

CHROMA_URL = os.getenv("CHROMA_URL")

def get_vector_client():
    if not CHROMA_URL:
        # No vector store configured; return a no-op shim
        class NullVector:
            def upsert(self, *a, **k): return {"ok": True, "count": 0}
            def query(self, *a, **k): return {"results": []}
        return NullVector()

    try:
        from chromadb import HttpClient
        host = CHROMA_URL.replace("http://", "").split(":")[0]
        port = int(CHROMA_URL.split(":")[-1])
        return HttpClient(host=host, port=port)
    except Exception as e:
        # Fail soft: log and fallback
        import logging
        logging.getLogger(__name__).warning("Vector store unavailable: %r", e)
        class Degraded:
            def upsert(self, *a, **k): return {"ok": False, "error": "vector-store-unavailable"}
            def query(self, *a, **k): return {"results": []}
        return Degraded()