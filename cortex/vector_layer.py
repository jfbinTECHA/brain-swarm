"""
Vector Memory Layer
-------------------
Stores and retrieves semantic embeddings using ChromaDB or FAISS.
"""

import chromadb, os

client = chromadb.Client()
collection = client.get_or_create_collection("cortex_vectors")

def add_embedding(embedding_id: str, vector: list[float], metadata: dict):
    collection.add(ids=[embedding_id], embeddings=[vector], metadatas=[metadata])

def query_similar(vector: list[float], top_k: int = 5):
    return collection.query(query_embeddings=[vector], n_results=top_k)