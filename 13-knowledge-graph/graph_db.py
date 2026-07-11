#!/usr/bin/env python3
"""SQLite-based graph database module for knowledge graph storage."""

import sqlite3
import json
from datetime import datetime
from typing import Optional


class GraphDB:
    """SQLite-backed graph database with nodes and edges."""

    def __init__(self, db_path: str = "knowledge_graph.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'entity',
                properties TEXT DEFAULT '{}',
                source_file TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(name, category)
            );
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                relationship TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                properties TEXT DEFAULT '{}',
                source_file TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE,
                UNIQUE(source_id, target_id, relationship)
            );
            CREATE TABLE IF NOT EXISTS ingestion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                file_hash TEXT,
                ingested_at TEXT DEFAULT (datetime('now')),
                node_count INTEGER DEFAULT 0,
                edge_count INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name);
            CREATE INDEX IF NOT EXISTS idx_nodes_category ON nodes(category);
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_edges_rel ON edges(relationship);
        """)
        self.conn.commit()

    def add_node(self, name: str, category: str = "entity",
                 properties: Optional[dict] = None, source_file: Optional[str] = None) -> int:
        """Add or update a node. Returns node ID."""
        props = json.dumps(properties or {})
        cursor = self.conn.execute("""
            INSERT INTO nodes (name, category, properties, source_file)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name, category) DO UPDATE SET
                properties = excluded.properties,
                updated_at = datetime('now'),
                source_file = COALESCE(excluded.source_file, nodes.source_file)
            RETURNING id
        """, (name, category, props, source_file))
        row = cursor.fetchone()
        self.conn.commit()
        return row[0]

    def add_edge(self, source_name: str, target_name: str, relationship: str,
                 weight: float = 1.0, properties: Optional[dict] = None,
                 source_file: Optional[str] = None) -> Optional[int]:
        """Add an edge between two nodes by name. Creates nodes if needed."""
        source_id = self.add_node(source_name, source_file=source_file)
        target_id = self.add_node(target_name, source_file=source_file)
        props = json.dumps(properties or {})
        try:
            cursor = self.conn.execute("""
                INSERT INTO edges (source_id, target_id, relationship, weight, properties, source_file)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, relationship) DO UPDATE SET
                    weight = edges.weight + excluded.weight,
                    properties = excluded.properties
                RETURNING id
            """, (source_id, target_id, relationship, weight, props, source_file))
            row = cursor.fetchone()
            self.conn.commit()
            return row[0]
        except sqlite3.Error:
            self.conn.rollback()
            return None

    def get_node(self, name: str) -> Optional[dict]:
        """Get a node by name."""
        cursor = self.conn.execute(
            "SELECT * FROM nodes WHERE name = ? COLLATE NOCASE", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def search_nodes(self, query: str, limit: int = 20) -> list:
        """Search nodes by name (fuzzy)."""
        cursor = self.conn.execute("""
            SELECT * FROM nodes WHERE name LIKE ? COLLATE NOCASE
            ORDER BY name LIMIT ?
        """, (f"%{query}%", limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_related(self, entity_name: str, max_depth: int = 2) -> dict:
        """Find all entities related to the given entity."""
        node = self.get_node(entity_name)
        if not node:
            return {"entity": entity_name, "found": False, "related": []}
        visited = set()
        related = []
        self._traverse(node["id"], visited, related, max_depth, 0)
        return {"entity": entity_name, "found": True, "related": related}

    def _traverse(self, node_id: int, visited: set, related: list,
                  max_depth: int, current_depth: int):
        """BFS traversal to find related nodes."""
        if current_depth >= max_depth or node_id in visited:
            return
        visited.add(node_id)
        # Outgoing
        cursor = self.conn.execute("""
            SELECT e.relationship, e.weight, n.name, n.category, n.id
            FROM edges e JOIN nodes n ON e.target_id = n.id
            WHERE e.source_id = ?
        """, (node_id,))
        for row in cursor.fetchall():
            if row["id"] not in visited:
                related.append({
                    "name": row["name"], "category": row["category"],
                    "relationship": row["relationship"],
                    "weight": row["weight"], "depth": current_depth + 1
                })
                self._traverse(row["id"], visited, related, max_depth, current_depth + 1)
        # Incoming
        cursor = self.conn.execute("""
            SELECT e.relationship, e.weight, n.name, n.category, n.id
            FROM edges e JOIN nodes n ON e.source_id = n.id
            WHERE e.target_id = ?
        """, (node_id,))
        for row in cursor.fetchall():
            if row["id"] not in visited:
                related.append({
                    "name": row["name"], "category": row["category"],
                    "relationship": f"(inverse) {row['relationship']}",
                    "weight": row["weight"], "depth": current_depth + 1
                })
                self._traverse(row["id"], visited, related, max_depth, current_depth + 1)

    def get_stats(self) -> dict:
        """Get graph statistics."""
        node_count = self.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edge_count = self.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        categories = self.conn.execute(
            "SELECT category, COUNT(*) as count FROM nodes GROUP BY category ORDER BY count DESC"
        ).fetchall()
        relationships = self.conn.execute(
            "SELECT relationship, COUNT(*) as count FROM edges GROUP BY relationship ORDER BY count DESC"
        ).fetchall()
        top_nodes = self.conn.execute("""
            SELECT n.name, n.category,
                (SELECT COUNT(*) FROM edges WHERE source_id=n.id OR target_id=n.id) as connections
            FROM nodes n ORDER BY connections DESC LIMIT 10
        """).fetchall()
        sources = self.conn.execute(
            "SELECT file_path, node_count, edge_count, ingested_at FROM ingestion_log ORDER BY ingested_at DESC LIMIT 10"
        ).fetchall()
        return {
            "total_nodes": node_count, "total_edges": edge_count,
            "categories": [dict(c) for c in categories],
            "relationship_types": [dict(r) for r in relationships],
            "top_connected_nodes": [dict(n) for n in top_nodes],
            "recent_sources": [dict(s) for s in sources]
        }

    def export_dot(self) -> str:
        """Export graph in DOT format for Graphviz."""
        colors = {"person": "lightyellow", "organization": "lightgreen",
                  "location": "lightsalmon", "concept": "lightcyan",
                  "technology": "plum", "event": "wheat", "entity": "lightblue"}
        lines = ["digraph KnowledgeGraph {", "    rankdir=LR;",
                 "    node [shape=box, style=filled, fillcolor=lightblue];", ""]
        nodes = self.conn.execute("SELECT id, name, category FROM nodes").fetchall()
        for node in nodes:
            color = colors.get(node["category"], "lightgray")
            label = node["name"].replace('"', '\\"')
            lines.append(f'    n{node["id"]} [label="{label}" fillcolor={color}];')
        lines.append("")
        edges = self.conn.execute("SELECT source_id, target_id, relationship FROM edges").fetchall()
        for edge in edges:
            label = edge["relationship"].replace('"', '\\"')
            lines.append(f'    n{edge["source_id"]} -> n{edge["target_id"]} [label="{label}"];')
        lines.append("}")
        return "\n".join(lines)

    def export_json(self) -> dict:
        """Export graph as JSON."""
        nodes = self.conn.execute("SELECT * FROM nodes").fetchall()
        edges = self.conn.execute("SELECT * FROM edges").fetchall()
        return {"nodes": [dict(n) for n in nodes], "edges": [dict(e) for e in edges],
                "exported_at": datetime.now().isoformat()}

    def query_subgraph(self, keywords: list, limit: int = 50) -> dict:
        """Query a subgraph relevant to the given keywords."""
        conditions = " OR ".join(["n.name LIKE ? COLLATE NOCASE"] * len(keywords))
        params = [f"%{kw}%" for kw in keywords]
        cursor = self.conn.execute(
            f"SELECT DISTINCT n.* FROM nodes n WHERE {conditions} LIMIT ?",
            params + [limit])
        relevant_nodes = [dict(r) for r in cursor.fetchall()]
        if not relevant_nodes:
            return {"nodes": [], "edges": []}
        node_ids = [n["id"] for n in relevant_nodes]
        ph = ",".join(["?"] * len(node_ids))
        cursor = self.conn.execute(f"""
            SELECT DISTINCT e.*, ns.name as source_name, nt.name as target_name
            FROM edges e JOIN nodes ns ON e.source_id=ns.id JOIN nodes nt ON e.target_id=nt.id
            WHERE e.source_id IN ({ph}) OR e.target_id IN ({ph}) LIMIT ?
        """, node_ids + node_ids + [limit * 2])
        relevant_edges = [dict(r) for r in cursor.fetchall()]
        return {"nodes": relevant_nodes, "edges": relevant_edges}

    def log_ingestion(self, file_path: str, file_hash: str, node_count: int, edge_count: int):
        """Log file ingestion."""
        self.conn.execute("""
            INSERT INTO ingestion_log (file_path, file_hash, node_count, edge_count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_hash=excluded.file_hash, ingested_at=datetime('now'),
                node_count=excluded.node_count, edge_count=excluded.edge_count
        """, (file_path, file_hash, node_count, edge_count))
        self.conn.commit()

    def is_file_ingested(self, file_path: str, file_hash: str) -> bool:
        """Check if file was already ingested with same hash."""
        cursor = self.conn.execute(
            "SELECT file_hash FROM ingestion_log WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()
        return row is not None and row[0] == file_hash

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
