"""
Prometheus Metrics for Cortex Memory
------------------------------------
"""

from prometheus_client import Counter, Histogram

CORTEX_INGEST_TOTAL = Counter("cortex_ingest_total", "Number of ingested records")
CORTEX_QUERY_TOTAL = Counter("cortex_queries_total", "Number of semantic queries")
CORTEX_QUERY_COUNT = Counter("cortex_query_count", "Number of cortex queries")
CORTEX_QUERY_LATENCY = Histogram("cortex_query_latency", "Query latency in seconds", buckets=[0.1, 0.5, 1.0, 2.0, 5.0])
CORTEX_CONFIDENCE_SCORE = Histogram("cortex_ai_confidence_score", "AI confidence per triage", buckets=[0.5, 0.7, 0.85, 0.9, 0.95, 1.0])

# Dummy prometheus_metrics for compatibility
class PrometheusMetrics:
    def record_message(self, *args):
        pass

prometheus_metrics = PrometheusMetrics()