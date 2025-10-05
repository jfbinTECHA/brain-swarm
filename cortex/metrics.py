from prometheus_client import Counter, Histogram

CORTEX_QUERY_COUNT = Counter(
    "cortex_queries_total", "Total number of cortex queries", ["source", "layer"]
)
CORTEX_INGEST_COUNT = Counter(
    "cortex_ingest_total", "Total number of cortex ingests", ["layer"]
)
CORTEX_QUERY_LATENCY = Histogram(
    "cortex_query_seconds", "Latency of cortex queries in seconds", ["layer"]
)