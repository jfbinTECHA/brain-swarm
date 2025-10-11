#!/usr/bin/env python3
"""
Brain Swarm Metrics Demo
Demonstrates comprehensive Prometheus instrumentation and metrics collection.
"""

import os
import sys
import time
import requests
import json

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from observability.metrics import prometheus_metrics


def demo_basic_metrics():
    """Demonstrate basic metrics collection"""
    print("📊 Brain Swarm Metrics Demo")
    print("=" * 50)

    # Record some basic metrics
    print("Recording basic system metrics...")

    # System info
    prometheus_metrics.record_system_info("1.0.0", "demo")

    # Agent metrics
    prometheus_metrics.record_agent_registration("agent_001", "worker", "swarm_main")
    prometheus_metrics.record_agent_registration("agent_002", "coordinator", "swarm_main")
    prometheus_metrics.update_agent_load("agent_001", "worker", "swarm_main", 0.7)
    prometheus_metrics.update_agent_load("agent_002", "coordinator", "swarm_main", 0.3)

    # Task metrics
    prometheus_metrics.record_task_created("analysis", 2, "swarm_main")
    prometheus_metrics.record_task_created("processing", 1, "swarm_main")
    prometheus_metrics.record_task_completed("analysis", "success", 45.2, "agent_001", "swarm_main")
    prometheus_metrics.update_active_tasks(1, "swarm_main")

    # API metrics
    prometheus_metrics.record_api_request("/tasks", "POST", 201, 0.023)
    prometheus_metrics.record_api_request("/health", "GET", 200, 0.001)

    # Memory operations
    prometheus_metrics.record_memory_operation("store", "vector_layer", 1024)
    prometheus_metrics.record_memory_operation("retrieve", "cache_layer", 512)

    # Federation operations
    prometheus_metrics.record_federation_operation("discovery", "swarm_main", "swarm_backup")

    print("✅ Basic metrics recorded")
    print()


def demo_error_metrics():
    """Demonstrate error and failure metrics"""
    print("❌ Error Metrics Demo")
    print("-" * 30)

    # Record various errors
    prometheus_metrics.record_error("connection_timeout", "message_queue", "high")
    prometheus_metrics.record_error("validation_error", "api_layer", "medium")
    prometheus_metrics.record_task_failure("analysis", "timeout", "agent_001")
    prometheus_metrics.record_task_failure("processing", "resource_exhausted", "agent_002")

    print("✅ Error metrics recorded")
    print()


def demo_performance_metrics():
    """Demonstrate performance and resource metrics"""
    print("⚡ Performance Metrics Demo")
    print("-" * 35)

    # Resource usage
    prometheus_metrics.update_resource_usage(
        component="api_server",
        cpu_percent=45.2,
        memory_percent=67.8,
        disk_bytes=1024*1024*1024  # 1GB
    )

    prometheus_metrics.update_resource_usage(
        component="vector_store",
        cpu_percent=23.1,
        memory_percent=89.4
    )

    # Learning metrics
    prometheus_metrics.record_learning_iteration("reinforcement_learning", "task_scheduler")
    prometheus_metrics.update_model_accuracy("embedding_model", "cosine_similarity", 0.87)

    print("✅ Performance metrics recorded")
    print()


def demo_metrics_output():
    """Demonstrate metrics output formats"""
    print("📤 Metrics Output Demo")
    print("-" * 30)

    # Get Prometheus format
    prometheus_output = prometheus_metrics.get_metrics_output()
    print("📋 Prometheus Format (first 20 lines):")
    lines = prometheus_output.split('\n')[:20]
    for line in lines:
        if line.strip():
            print(f"  {line}")
    print("  ...")

    print()

    # Get JSON format
    json_output = prometheus_metrics.get_metrics_json()
    print("📋 JSON Format Summary:")
    print(f"  Timestamp: {json_output.get('timestamp', 'N/A')}")
    print(f"  System Status: {json_output.get('system_status', 'N/A')}")
    print(f"  Metrics Available: {json_output.get('metrics_available', 'N/A')}")

    print()


def demo_api_endpoints():
    """Demonstrate API metrics endpoints"""
    print("🌐 API Endpoints Demo")
    print("-" * 30)

    base_url = "http://localhost:8000"

    try:
        # Test /metrics endpoint
        print("Testing /metrics endpoint...")
        response = requests.get(f"{base_url}/metrics", timeout=5)
        if response.status_code == 200:
            print("✅ /metrics endpoint accessible")
            metrics_data = response.json()
            print(f"  Agents: {metrics_data.get('system_metrics', {}).get('total_agents', 'N/A')}")
            print(f"  Active Tasks: {metrics_data.get('system_metrics', {}).get('active_tasks', 'N/A')}")
        else:
            print(f"❌ /metrics endpoint returned {response.status_code}")

        # Test /metrics/prometheus endpoint
        print("\nTesting /metrics/prometheus endpoint...")
        response = requests.get(f"{base_url}/metrics/prometheus", timeout=5)
        if response.status_code == 200:
            print("✅ /metrics/prometheus endpoint accessible")
            prometheus_text = response.text
            brain_swarm_metrics = [line for line in prometheus_text.split('\n') if 'brain_swarm' in line][:5]
            print("  Sample brain_swarm metrics:")
            for metric in brain_swarm_metrics:
                print(f"    {metric}")
        else:
            print(f"❌ /metrics/prometheus endpoint returned {response.status_code}")

        # Test /metrics/dashboard endpoint
        print("\nTesting /metrics/dashboard endpoint...")
        response = requests.get(f"{base_url}/metrics/dashboard", timeout=5)
        if response.status_code == 200:
            print("✅ /metrics/dashboard endpoint accessible")
            dashboard_data = response.json()
            print(f"  System load: {dashboard_data.get('system', {}).get('system_load', 'N/A')}")
            print(f"  Active agents: {len(dashboard_data.get('agents', []))}")
        else:
            print(f"❌ /metrics/dashboard endpoint returned {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Could not connect to API server: {e}")
        print("💡 Make sure the Brain Swarm API is running on http://localhost:8000")

    print()


def demo_real_time_monitoring():
    """Demonstrate real-time metrics monitoring"""
    print("📈 Real-time Monitoring Demo")
    print("-" * 35)

    print("Simulating real-time activity...")

    # Simulate some activity with metrics
    for i in range(5):
        # Create a task
        prometheus_metrics.record_task_created("simulation", 3, "demo_swarm")

        # Simulate some load
        prometheus_metrics.update_agent_load("agent_001", "worker", "demo_swarm", 0.1 * (i + 1))

        # Record API call
        prometheus_metrics.record_api_request("/simulation", "POST", 200, 0.05)

        time.sleep(0.1)

    # Complete a task
    prometheus_metrics.record_task_completed("simulation", "success", 2.5, "agent_001", "demo_swarm")
    prometheus_metrics.update_active_tasks(0, "demo_swarm")

    print("✅ Real-time activity simulated")
    print()


def demo_metrics_analysis():
    """Demonstrate metrics analysis and insights"""
    print("🔍 Metrics Analysis Demo")
    print("-" * 30)

    # Get current metrics
    prometheus_output = prometheus_metrics.get_metrics_output()

    # Analyze some key metrics
    lines = prometheus_output.split('\n')

    # Count different metric types
    counters = [line for line in lines if line.startswith('brain_swarm') and '_total' in line]
    gauges = [line for line in lines if line.startswith('brain_swarm') and not '_total' in line and not '_bucket' in line and not '_sum' in line and not '_count' in line]
    histograms = [line for line in lines if '_bucket' in line or '_sum' in line or '_count' in line]

    print(f"📊 Current Metrics Summary:")
    print(f"  Counters: {len(counters)}")
    print(f"  Gauges: {len(gauges)}")
    print(f"  Histograms: {len(histograms)}")

    # Show some sample values
    print("\n📈 Sample Metric Values:")
    for line in lines[:10]:
        if line.strip() and not line.startswith('#'):
            parts = line.split(' ')
            if len(parts) >= 2:
                metric_name = parts[0]
                value = parts[1]
                print(f"  {metric_name}: {value}")

    print()


def main():
    """Run all metrics demos"""
    print("🚀 Brain Swarm Comprehensive Metrics Demo")
    print("=" * 50)
    print()

    try:
        demo_basic_metrics()
        demo_error_metrics()
        demo_performance_metrics()
        demo_metrics_output()
        demo_api_endpoints()
        demo_real_time_monitoring()
        demo_metrics_analysis()

        print("✅ All metrics demos completed successfully!")
        print()
        print("💡 Key Takeaways:")
        print("  - Comprehensive Prometheus instrumentation")
        print("  - Multiple output formats (JSON, Prometheus)")
        print("  - Real-time metrics collection")
        print("  - Multiple API endpoints for different use cases")
        print("  - Counters, gauges, and histograms for different metric types")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())