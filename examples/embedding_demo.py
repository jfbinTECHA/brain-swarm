#!/usr/bin/env python3
"""
Embedding Adapter Demo
Demonstrates the multi-provider embedding capabilities of Brain Swarm.
"""

import os
import sys
import time

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cortex.adapters.embedding_adapter import EmbeddingAdapter, embedding_adapter


def demo_basic_embedding():
    """Demonstrate basic embedding functionality"""
    print("🔍 Brain Swarm Embedding Adapter Demo")
    print("=" * 50)

    # Test texts
    texts = [
        "Machine learning algorithms for natural language processing",
        "Neural network architectures and deep learning models",
        "Data science and statistical analysis techniques",
        "Cloud computing and distributed systems design"
    ]

    print(f"📝 Embedding {len(texts)} text samples...")

    start_time = time.time()
    embeddings = embedding_adapter.embed_texts(texts)
    elapsed = time.time() - start_time

    print(".2f")
    print(f"📏 Embedding dimensions: {len(embeddings[0])}")
    print(f"🔧 Current provider: {type(embedding_adapter.current_provider).__name__}")
    print()


def demo_provider_switching():
    """Demonstrate provider switching"""
    print("🔄 Provider Switching Demo")
    print("-" * 30)

    available_providers = embedding_adapter.get_available_providers()
    print(f"Available providers: {', '.join(available_providers)}")

    # Try switching to different providers
    for provider in available_providers:
        try:
            embedding_adapter.switch_provider(provider)
            print(f"✅ Switched to: {provider} ({type(embedding_adapter.current_provider).__name__})")
        except Exception as e:
            print(f"❌ Failed to switch to {provider}: {e}")

    print()


def demo_custom_configuration():
    """Demonstrate custom embedding adapter configuration"""
    print("⚙️ Custom Configuration Demo")
    print("-" * 30)

    # Create custom configuration
    custom_config = {
        "providers": {
            "openai": {
                "enabled": bool(os.getenv("OPENAI_API_KEY")),
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model": "text-embedding-3-small",
                "dimension": 1536
            },
            "openrouter": {
                "enabled": bool(os.getenv("OPENROUTER_API_KEY")),
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "model": "text-embedding-3-small",
                "dimension": 1536
            },
            "local": {
                "enabled": True,
                "model_name": "all-MiniLM-L6-v2",
                "dimension": 384
            },
            "fallback": {
                "enabled": True,
                "dimension": 256
            }
        },
        "default_provider": "local"
    }

    custom_adapter = EmbeddingAdapter(custom_config)
    print(f"Custom adapter initialized with {len(custom_adapter.get_available_providers())} providers")

    # Test embedding with custom adapter
    test_text = ["Custom embedding adapter test"]
    embeddings = custom_adapter.embed_texts(test_text)
    print(f"Custom adapter embedding dimension: {len(embeddings[0])}")
    print()


def demo_semantic_similarity():
    """Demonstrate semantic similarity using embeddings"""
    print("🎯 Semantic Similarity Demo")
    print("-" * 30)

    # Test texts with semantic relationships
    texts = [
        "Python programming language",
        "Java programming language",
        "Machine learning with Python",
        "Cooking recipes",
        "Data structures in Python"
    ]

    print("Computing embeddings for semantic similarity...")
    embeddings = embedding_adapter.embed_texts(texts)

    # Simple cosine similarity calculation
    import numpy as np

    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    print("\n📊 Semantic Similarity Matrix:")
    print("Text".ljust(25), end="")
    for i, text in enumerate(texts):
        print("2d")
    print("-" * (25 + 6 * len(texts)))

    for i, text1 in enumerate(texts):
        print(text1[:24].ljust(25), end="")
        for j, text2 in enumerate(texts):
            if i == j:
                print("1.00".rjust(5), end=" ")
            else:
                similarity = cosine_similarity(embeddings[i], embeddings[j])
                print(".2f")
        print()

    print()


def demo_knowledge_cortex_integration():
    """Demonstrate integration with Knowledge Cortex"""
    print("🧠 Knowledge Cortex Integration Demo")
    print("-" * 40)

    try:
        from memory.knowledge_cortex import knowledge_cortex

        # Store some content with vectorization
        test_content = {
            "title": "Advanced AI Techniques",
            "content": "This document covers advanced artificial intelligence techniques including machine learning, deep learning, and neural networks.",
            "tags": ["AI", "ML", "Deep Learning"]
        }

        print("Storing content in Knowledge Cortex with vectorization...")
        success = knowledge_cortex.store("ai_techniques_doc", test_content, {
            "vectorize": True,
            "data_type": "document"
        })

        if success:
            print("✅ Content stored successfully")

            # Try semantic search
            print("Searching for related content...")
            results = knowledge_cortex.search("artificial intelligence techniques", search_type="semantic")

            if results:
                print(f"Found {len(results)} related results")
                for result in results[:3]:  # Show top 3
                    print(f"  - {result.get('source', 'unknown')}: {type(result.get('data', {}))}")
            else:
                print("No semantic search results (vector layer may not be available)")
        else:
            print("❌ Failed to store content")

    except ImportError as e:
        print(f"❌ Knowledge Cortex not available: {e}")
        print("This demo requires the full Brain Swarm memory system")

    print()


def main():
    """Run all embedding demos"""
    print("🚀 Brain Swarm Embedding System Demo")
    print("=" * 50)
    print()

    try:
        demo_basic_embedding()
        demo_provider_switching()
        demo_custom_configuration()
        demo_semantic_similarity()
        demo_knowledge_cortex_integration()

        print("✅ All embedding demos completed successfully!")
        print()
        print("💡 Tips:")
        print("  - Set OPENAI_API_KEY for OpenAI embeddings")
        print("  - Set OPENROUTER_API_KEY for OpenRouter access")
        print("  - Install sentence-transformers for local embeddings")
        print("  - The system automatically falls back to hash-based embeddings")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())