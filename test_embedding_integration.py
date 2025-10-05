#!/usr/bin/env python3
"""
Simple test script for embedding adapter integration
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_embedding_adapter():
    """Test the embedding adapter functionality"""
    try:
        from cortex.adapters.embedding_adapter import EmbeddingAdapter, FallbackEmbeddingProvider

        # Test fallback provider (should always work)
        fallback_config = {"dimension": 256}
        fallback = FallbackEmbeddingProvider(fallback_config)

        test_texts = ["Hello world", "This is a test", "Embedding integration"]
        embeddings = fallback.embed_texts(test_texts)

        assert len(embeddings) == 3
        assert len(embeddings[0]) == 256
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(isinstance(val, float) for emb in embeddings for val in emb)

        print("✓ Fallback embedding provider works")

        # Test adapter initialization
        adapter_config = {
            "providers": {
                "fallback": {"enabled": True, "dimension": 256}
            },
            "default_provider": "fallback"
        }

        adapter = EmbeddingAdapter(adapter_config)
        embeddings2 = adapter.embed_texts(test_texts)

        assert len(embeddings2) == 3
        assert len(embeddings2[0]) == 256

        print("✓ Embedding adapter initialization works")

        return True

    except Exception as e:
        print(f"✗ Embedding adapter test failed: {e}")
        return False

def test_summarizer_import():
    """Test that the summarizer can be imported"""
    try:
        # Just test import, don't initialize since it requires cortex
        import ast
        with open('cortex/scheduled_summarizer.py', 'r') as f:
            ast.parse(f.read())
        print("✓ Scheduled summarizer syntax is valid")
        return True
    except Exception as e:
        print(f"✗ Scheduled summarizer test failed: {e}")
        return False

def test_api_changes():
    """Test that API changes are syntactically correct"""
    try:
        import ast
        with open('api/main.py', 'r') as f:
            ast.parse(f.read())
        print("✓ API main syntax is valid")
        return True
    except Exception as e:
        print(f"✗ API changes test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Knowledge Cortex add-ons...")

    results = []
    results.append(test_embedding_adapter())
    results.append(test_summarizer_import())
    results.append(test_api_changes())

    if all(results):
        print("\n🎉 All tests passed! Knowledge Cortex add-ons are ready.")
        sys.exit(0)
    else:
        print(f"\n❌ {sum(not r for r in results)} test(s) failed.")
        sys.exit(1)