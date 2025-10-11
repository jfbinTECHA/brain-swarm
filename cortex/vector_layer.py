"""
Vector Memory Layer
-------------------
Stores and retrieves semantic embeddings using ChromaDB or FAISS.
"""

import chromadb, os

client = chromadb.Client()
collection = client.get_or_create_collection("cortex_vectors")

class VectorStore:
    """Vector store for semantic search"""

    def __init__(self):
        self.collection = collection

    def add(self, embedding_id: str, vector: list[float], metadata: dict):
        """Add an embedding to the store"""
        self.collection.add(ids=[embedding_id], embeddings=[vector], metadatas=[metadata])

    def query(self, vector: list[float], top_k: int = 5):
        """Query similar vectors"""
        return self.collection.query(query_embeddings=[vector], n_results=top_k)

    def delete(self, embedding_id: str):
        """Delete an embedding"""
        self.collection.delete(ids=[embedding_id])

def add_embedding(embedding_id: str, vector: list[float], metadata: dict):
    collection.add(ids=[embedding_id], embeddings=[vector], metadatas=[metadata])

def query_similar(vector: list[float], top_k: int = 5):
    return collection.query(query_embeddings=[vector], n_results=top_k)