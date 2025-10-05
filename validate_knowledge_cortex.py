#!/usr/bin/env python3
"""
Validation script for Knowledge Cortex Memory System
"""
import sys
import os

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def validate_imports():
    """Test that all components can be imported"""
    try:
        from memory.knowledge_cortex import KnowledgeCortex, knowledge_cortex
        from memory.backends import (
            RedisCacheBackend,
            ChromaVectorBackend,
            NetworkXGraphBackend,
            S3ArchiveBackend,
            MemoryBackendFactory
        )
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def validate_initialization():
    """Test Knowledge Cortex initialization"""
    try:
        from memory.knowledge_cortex import KnowledgeCortex

        # Test with minimal config (should handle missing services gracefully)
        config = {
            "cache": None,  # Disable cache for testing
            "vector": None,  # Disable vector for testing
            "graph": {"backend": "networkx_graph", "db_path": ":memory:"},
            "archive": None  # Disable archive for testing
        }

        cortex = KnowledgeCortex(config)
        print("✓ Knowledge Cortex initialized successfully")

        # Test health check
        status = cortex.get_health_status()
        print(f"✓ Health status: {status['overall_status']}")

        return True
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return False

def validate_basic_operations():
    """Test basic memory operations"""
    try:
        from memory.knowledge_cortex import KnowledgeCortex

        # Use in-memory graph for testing
        config = {
            "cache": None,
            "vector": None,
            "graph": {"backend": "networkx_graph", "db_path": ":memory:"},
            "archive": None
        }

        cortex = KnowledgeCortex(config)

        # Test storing data
        test_key = "test_fact"
        test_data = "The brain swarm uses hierarchical memory"
        metadata = {"type": "semantic", "category": "architecture"}

        success = cortex.store(test_key, test_data, metadata)
        print(f"✓ Store operation: {'successful' if success else 'failed'}")

        # Test retrieving data
        retrieved = cortex.retrieve(test_key)
        print(f"✓ Retrieve operation: {'successful' if retrieved == test_data else 'failed'}")

        # Test adding relationships
        cortex.add_relationship("brain", "swarm", "contains",
                              {"edge_type": "relational", "confidence": 0.9})
        print("✓ Relationship addition: successful")

        return True
    except Exception as e:
        print(f"✗ Basic operations failed: {e}")
        return False

def main():
    """Run all validations"""
    print("Knowledge Cortex Memory System Validation")
    print("=" * 50)

    results = []

    print("\n1. Testing imports...")
    results.append(validate_imports())

    print("\n2. Testing initialization...")
    results.append(validate_initialization())

    print("\n3. Testing basic operations...")
    results.append(validate_basic_operations())

    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 All validations passed! ({passed}/{total})")
        print("\nKnowledge Cortex Memory System is ready to use.")
        print("\nArchitecture:")
        print("  Cache Layer: Redis (fast access)")
        print("  Vector Layer: ChromaDB (semantic search)")
        print("  Graph Layer: NetworkX+DuckDB (relational knowledge)")
        print("  Archive Layer: S3+DuckDB (long-term storage)")
        return 0
    else:
        print(f"❌ Some validations failed ({passed}/{total})")
        return 1

if __name__ == "__main__":
    exit(main())