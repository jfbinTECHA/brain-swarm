#!/usr/bin/env python3
"""
Simple test script for observability components
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Test basic functionality without relative imports
print("Testing observability components...")

try:
    # Test health checker
    from observability.health import HealthStatus
    print("✓ Health check enums imported successfully")

    # Test tracing
    from observability.tracing import get_correlation_id
    correlation_id = get_correlation_id()
    print(f"✓ Tracing correlation ID generated: {correlation_id[:16]}...")

    # Test governance
    from observability.governance import ComplianceLevel, PolicyCategory
    print("✓ Governance enums imported successfully")

    # Test alerting
    from observability.alerting import AlertSeverity
    print("✓ Alerting enums imported successfully")

    print("\n🎉 All observability components imported successfully!")
    print("Note: Prometheus metrics will use mock implementation if prometheus_client is not installed.")

except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)