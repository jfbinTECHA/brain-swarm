from __future__ import annotations
import time
from typing import List, Dict, Any

from .config import settings
from .cortex_schemas import MemoryRecord, QueryRequest, QueryResult, QueryHit, EdgeType
from .metrics import CORTEX_QUERY_COUNT, CORTEX_QUERY_LATENCY

from .adapters.cache_redis import CacheRedis
from .adapters.vector_chroma_faiss import VectorStore
from .adapters.graph_nx_duckdb import GraphStore
from .adapters.archive_s3_duckdb import ArchiveStore
from .adapters.embedding_adapter import embedding_adapter

# Use the embedding adapter for text embeddings
def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed texts using the configured embedding adapter"""
    if embedding_adapter:
        return embedding_adapter.embed_texts(texts)
    else:
        # Fallback to SHA256 if adapter failed to initialize
        import hashlib
        import numpy as np
        out = []
        for t in texts:
            h = hashlib.sha256(t.encode()).digest()
            vec = np.frombuffer(h[:256], dtype=np.uint8).astype("float32")
            vec = vec / (np.linalg.norm(vec) + 1e-9)
            out.append(vec.tolist())
        return out

class KnowledgeCortex:
    def __init__(self):
        self.cache = CacheRedis(settings.redis_url)
        self.vector = VectorStore(
            host=settings.chroma_host,
            port=settings.chroma_port,
            collection=settings.chroma_collection,
            faiss_enable=settings.faiss_enable,
            faiss_index_path=settings.faiss_index_path,
        )
        self.graph = GraphStore(settings.duckdb_path)
        self.archive = ArchiveStore(
            duckdb_path=settings.duckdb_path,
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint_url,
            region=settings.s3_region,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=settings.s3_secure,
        )

    # ---- Write Paths ----
    def store_record(self, rec: MemoryRecord):
        texts = [rec.text]
        embeddings = rec.embedding or embed_texts(texts)
        if rec.embedding is None:
            rec.embedding = embeddings[0]
        self.vector.add(ids=[rec.id], embeddings=[rec.embedding], metadatas=[rec.metadata], documents=[rec.text])
        # Persist in long-term archive as JSONL row (optional toggle)
        self.archive.write_jsonl(rec.id, payload={"text": rec.text, "metadata": rec.metadata, "ts": rec.timestamp or time.time()})
        # Insert/update node in graph as knowledge vertex
        self.graph.upsert_node(rec.id, label=rec.metadata.get("label", ""), ts=rec.timestamp, metadata=rec.metadata)

    def link(self, src_id: str, dst_id: str, edge_type: EdgeType, weight: float = 1.0, ts: float | None = None, metadata: Dict[str, Any] | None = None):
        self.graph.add_edge(src_id, dst_id, edge_type=edge_type.value, weight=weight, ts=ts, metadata=metadata or {})

    # ---- Read Paths ----
    def query(self, req: QueryRequest) -> QueryResult:
        # Cache-first key
        cache_key = f"cortex:q:{req.query}:{req.top_k}:{hash(str(req.filter))}"

        def _compute():
            diagnostics: Dict[str, Any] = {}

            # Vector search
            with CORTEX_QUERY_LATENCY.labels(layer="vector").time():
                vec = embed_texts([req.query])
                vs = self.vector.query(query_embeddings=vec, where=req.filter, n_results=req.top_k)
                CORTEX_QUERY_COUNT.labels(source="api", layer="vector").inc()
            diagnostics["vector_candidates"] = len(vs.get("ids", [[]])[0]) if vs else 0

            hits: List[QueryHit] = []
            ids = vs.get("ids", [[]])[0] if vs else []
            docs = vs.get("documents", [[]])[0] if vs else []
            metas = vs.get("metadatas", [[]])[0] if vs else []
            dists = vs.get("distances", [[]])[0] if vs else []

            for i, doc_id in enumerate(ids):
                hits.append(QueryHit(id=doc_id, score=float(dists[i]) if i < len(dists) else 0.0, text=docs[i], metadata=metas[i]))

            # Graph refinement (optional)
            if req.use_graph and hits:
                with CORTEX_QUERY_LATENCY.labels(layer="graph").time():
                    # naive expansion: add temporal neighbors of top-1 as context
                    top_id = hits[0].id
                    neighbors = list(self.graph.neighbors(top_id))
                    diagnostics["graph_neighbors_considered"] = len(neighbors)

            # Archive lookup (optional; illustrative only)
            if req.use_archive and not hits:
                with CORTEX_QUERY_LATENCY.labels(layer="archive").time():
                    diagnostics["archive_hint"] = "no direct hits; consider archive scan"

            return QueryResult(hits=hits, diagnostics=diagnostics).model_dump()

        data = self.cache.remember(cache_key, _compute, ttl=30)
        # Convert dict→model
        return QueryResult(**data)