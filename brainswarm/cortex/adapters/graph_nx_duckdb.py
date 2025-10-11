from typing import Dict, Any, Iterable
import duckdb
import networkx as nx

EDGE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS edges (
    src TEXT,
    dst TEXT,
    edge_type TEXT,
    weight DOUBLE,
    ts DOUBLE,
    metadata JSON
);
"""

NODE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    label TEXT,
    ts DOUBLE,
    metadata JSON
);
"""

class GraphStore:
    def __init__(self, duckdb_path: str):
        self.db = duckdb.connect(duckdb_path)
        self.db.execute(EDGE_TABLE_SQL)
        self.db.execute(NODE_TABLE_SQL)
        self.G = nx.MultiDiGraph()

    def upsert_node(self, node_id: str, label: str = "", ts: float | None = None, metadata: Dict[str, Any] | None = None):
        self.db.execute("INSERT OR REPLACE INTO nodes (id,label,ts,metadata) VALUES (?,?,?,?)",
                        [node_id, label, ts, metadata or {}])
        self.G.add_node(node_id, label=label, ts=ts, metadata=metadata or {})

    def add_edge(self, src: str, dst: str, edge_type: str, weight: float = 1.0, ts: float | None = None, metadata: Dict[str, Any] | None = None):
        self.db.execute("INSERT INTO edges (src,dst,edge_type,weight,ts,metadata) VALUES (?,?,?,?,?,?)",
                        [src, dst, edge_type, weight, ts, metadata or {}])
        self.G.add_edge(src, dst, edge_type=edge_type, weight=weight, ts=ts, metadata=metadata or {})

    def neighbors(self, node_id: str, edge_type: str | None = None) -> Iterable[str]:
        for _, dst, data in self.G.out_edges(node_id, data=True):
            if edge_type is None or data.get("edge_type") == edge_type:
                yield dst