"""
Graph Memory Layer
------------------
Uses NetworkX + DuckDB to maintain temporal, semantic, and relational graphs.
"""

import networkx as nx
import duckdb, os

graph = nx.DiGraph()
db_path = os.getenv("GRAPH_DB_PATH", "data/graph.duckdb")
con = duckdb.connect(db_path)

class GraphStore:
    """Graph store for relationships"""

    def __init__(self):
        self.graph = graph
        self.db = con

    def add_edge(self, a: str, b: str, relation: str):
        """Add an edge to the graph"""
        self.graph.add_edge(a, b, relation=relation)
        self.db.execute("CREATE TABLE IF NOT EXISTS relations (a TEXT, b TEXT, relation TEXT)")
        self.db.execute("INSERT INTO relations VALUES (?, ?, ?)", [a, b, relation])

    def get_neighbors(self, node: str):
        """Get neighbors of a node"""
        return list(self.graph.neighbors(node))

    def query_path(self, start: str, end: str):
        """Find path between nodes"""
        try:
            return nx.shortest_path(self.graph, start, end)
        except nx.NetworkXNoPath:
            return None

def add_relation(a: str, b: str, relation: str):
    graph.add_edge(a, b, relation=relation)
    con.execute("CREATE TABLE IF NOT EXISTS relations (a TEXT, b TEXT, relation TEXT)")
    con.execute("INSERT INTO relations VALUES (?, ?, ?)", [a, b, relation])

def get_neighbors(node: str):
    return list(graph.neighbors(node))