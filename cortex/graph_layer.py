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

def add_relation(a: str, b: str, relation: str):
    graph.add_edge(a, b, relation=relation)
    con.execute("CREATE TABLE IF NOT EXISTS relations (a TEXT, b TEXT, relation TEXT)")
    con.execute("INSERT INTO relations VALUES (?, ?, ?)", [a, b, relation])

def get_neighbors(node: str):
    return list(graph.neighbors(node))