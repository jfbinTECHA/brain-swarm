from typing import List, Dict, Any, Optional
import os

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except Exception as e:
    chromadb = None  # allow import even if not installed

try:
    import faiss  # optional local cache
except Exception:
    faiss = None

class VectorStore:
    def __init__(self, host: str, port: int, collection: str, faiss_enable: bool, faiss_index_path: str):
        self.host = host
        self.port = port
        self.collection_name = collection
        self.faiss_enable = faiss_enable and (faiss is not None)
        self.faiss_index_path = faiss_index_path

        if chromadb is None:
            raise RuntimeError("chromadb is not installed")

        self.client = chromadb.HttpClient(host=host, port=port, settings=ChromaSettings())
        try:
            self.collection = self.client.get_collection(collection)
        except Exception:
            self.collection = self.client.create_collection(collection)

        # FAISS local cache (optional)
        self.faiss_index = None
        if self.faiss_enable:
            self._init_faiss()

    def _init_faiss(self):
        # Lazy build; this assumes fixed dim; will be inferred at first add.
        if os.path.exists(self.faiss_index_path):
            try:
                self.faiss_index = faiss.read_index(self.faiss_index_path)
            except Exception:
                self.faiss_index = None

    def add(self, ids: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]], documents: List[str]):
        self.collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
        if self.faiss_enable:
            self._add_to_faiss(embeddings)

    def _add_to_faiss(self, embeddings: List[List[float]]):
        import numpy as np
        vecs = np.array(embeddings).astype("float32")
        if self.faiss_index is None:
            self.faiss_index = faiss.IndexFlatIP(vecs.shape[1])
        self.faiss_index.add(vecs)
        try:
            faiss.write_index(self.faiss_index, self.faiss_index_path)
        except Exception:
            pass

    def query(self, query_embeddings: List[List[float]], where: Optional[Dict[str, Any]] = None, n_results: int = 8):
        # If FAISS cache exists, you can optionally do a coarse prefilter; here we go straight to Chroma for correctness.
        return self.collection.query(
            query_embeddings=query_embeddings, where=where, n_results=n_results
        )