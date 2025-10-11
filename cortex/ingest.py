import time
from typing import Iterable
from .schemas import MemoryRecord, EdgeType
from .metrics import CORTEX_INGEST_COUNT

class Ingestor:
    def __init__(self, cortex: "KnowledgeCortex"):
        self.cortex = cortex

    def ingest_records(self, records: Iterable[MemoryRecord], link_temporal: bool = True):
        prev_id = None
        for rec in records:
            self.cortex.store_record(rec)
            CORTEX_INGEST_COUNT.labels(layer="vector").inc()
            if link_temporal and prev_id:
                self.cortex.link(prev_id, rec.id, EdgeType.TEMPORAL.value, weight=1.0, ts=rec.timestamp)
                CORTEX_INGEST_COUNT.labels(layer="graph").inc()
            prev_id = rec.id