#!/usr/bin/env python3
"""AI Knowledge Graph - Builds knowledge graphs from documents using AI entity extraction."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Optional

import requests

from graph_db import GraphDB

OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_graph.db")


def ollama_generate(prompt: str, model: str = MODEL) -> str:
    """Call Ollama API to generate text."""
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.1, "num_predict": 2048}
        }, timeout=120)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to Ollama at localhost:11434", file=sys.stderr)
        print("Make sure Ollama is running: ollama serve", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error calling Ollama: {e}", file=sys.stderr)
        return ""


def extract_entities_and_relationships(text: str, source_file: str) -> dict:
    """Use AI to extract entities and relationships from text."""
    prompt = f"""Analyze the following text and extract entities and their relationships.
Return ONLY valid JSON in this exact format (no other text):
{{
  "entities": [
    {{"name": "Entity Name", "category": "person|organization|location|concept|technology|event", "description": "brief description"}}
  ],
  "relationships": [
    {{"source": "Entity1", "target": "Entity2", "relationship": "verb/connection type"}}
  ]
}}

Text to analyze:
---
{text[:3000]}
---

Return ONLY the JSON, no explanation."""

    response = ollama_generate(prompt)
    try:
        # Try to extract JSON from response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass
    return {"entities": [], "relationships": []}


def file_hash(filepath: str) -> str:
    """Compute MD5 hash of a file."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def read_file_content(filepath: str) -> Optional[str]:
    """Read text content from a file."""
    text_extensions = {".txt", ".md", ".py", ".js", ".ts", ".java", ".c", ".cpp",
                       ".h", ".rs", ".go", ".rb", ".php", ".html", ".css", ".json",
                       ".yaml", ".yml", ".toml", ".xml", ".csv", ".log", ".sh", ".bat"}
    ext = Path(filepath).suffix.lower()
    if ext not in text_extensions:
        return None
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except (IOError, OSError):
        return None


def ingest_file(db: GraphDB, filepath: str) -> tuple:
    """Ingest a single file into the knowledge graph."""
    filepath = os.path.abspath(filepath)
    fhash = file_hash(filepath)

    if db.is_file_ingested(filepath, fhash):
        print(f"  Skipping (unchanged): {filepath}")
        return (0, 0)

    content = read_file_content(filepath)
    if not content or len(content.strip()) < 50:
        print(f"  Skipping (too short/binary): {filepath}")
        return (0, 0)

    print(f"  Processing: {filepath}")
    extracted = extract_entities_and_relationships(content, filepath)

    node_count = 0
    edge_count = 0

    for entity in extracted.get("entities", []):
        name = entity.get("name", "").strip()
        if not name:
            continue
        category = entity.get("category", "entity").lower()
        props = {"description": entity.get("description", "")}
        db.add_node(name, category=category, properties=props, source_file=filepath)
        node_count += 1

    for rel in extracted.get("relationships", []):
        source = rel.get("source", "").strip()
        target = rel.get("target", "").strip()
        relationship = rel.get("relationship", "related_to").strip()
        if source and target and relationship:
            db.add_edge(source, target, relationship, source_file=filepath)
            edge_count += 1

    db.log_ingestion(filepath, fhash, node_count, edge_count)
    print(f"    Extracted: {node_count} entities, {edge_count} relationships")
    return (node_count, edge_count)


def ingest(path: str):
    """Ingest a file or directory."""
    path = os.path.abspath(path)
    db = GraphDB(DB_PATH)

    total_nodes = 0
    total_edges = 0
    file_count = 0

    if os.path.isfile(path):
        n, e = ingest_file(db, path)
        total_nodes += n
        total_edges += e
        file_count = 1
    elif os.path.isdir(path):
        print(f"Ingesting directory: {path}")
        for root, dirs, files in os.walk(path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in sorted(files):
                if fname.startswith("."):
                    continue
                fpath = os.path.join(root, fname)
                n, e = ingest_file(db, fpath)
                total_nodes += n
                total_edges += e
                file_count += 1
    else:
        print(f"Error: Path not found: {path}", file=sys.stderr)
        sys.exit(1)

    print(f"\nIngestion complete:")
    print(f"  Files processed: {file_count}")
    print(f"  Entities extracted: {total_nodes}")
    print(f"  Relationships found: {total_edges}")
    db.close()


def query(question: str):
    """Query the knowledge graph using AI."""
    db = GraphDB(DB_PATH)
    # Extract keywords from question
    keywords = [w for w in question.lower().split() if len(w) > 3]
    subgraph = db.query_subgraph(keywords)

    if not subgraph["nodes"]:
        print("No relevant knowledge found in the graph.")
        db.close()
        return

    # Build context from subgraph
    context_parts = []
    for node in subgraph["nodes"][:20]:
        props = json.loads(node.get("properties", "{}")) if isinstance(node.get("properties"), str) else node.get("properties", {})
        desc = props.get("description", "")
        context_parts.append(f"- {node['name']} ({node['category']}){': ' + desc if desc else ''}")

    for edge in subgraph["edges"][:30]:
        context_parts.append(f"- {edge['source_name']} --[{edge['relationship']}]--> {edge['target_name']}")

    context = "\n".join(context_parts)
    prompt = f"""Based on the following knowledge graph data, answer the question.

Knowledge Graph Context:
{context}

Question: {question}

Provide a concise, informative answer based on the knowledge graph data above."""

    print(f"\n{'='*60}")
    print(f"Query: {question}")
    print(f"{'='*60}")
    print(f"\nFound {len(subgraph['nodes'])} relevant entities, {len(subgraph['edges'])} relationships\n")

    answer = ollama_generate(prompt)
    print(answer.strip())
    db.close()


def visualize(format_type: str = "dot"):
    """Export the graph for visualization."""
    db = GraphDB(DB_PATH)
    stats = db.get_stats()

    if stats["total_nodes"] == 0:
        print("Graph is empty. Ingest some documents first.")
        db.close()
        return

    if format_type == "json":
        data = db.export_json()
        output_file = "knowledge_graph.json"
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Exported JSON to: {output_file}")
        print(f"  Nodes: {len(data['nodes'])}, Edges: {len(data['edges'])}")
    else:
        dot = db.export_dot()
        output_file = "knowledge_graph.dot"
        with open(output_file, "w") as f:
            f.write(dot)
        print(f"Exported DOT to: {output_file}")
        print(f"  Render with: dot -Tpng {output_file} -o knowledge_graph.png")

    db.close()


def stats():
    """Show graph statistics."""
    db = GraphDB(DB_PATH)
    s = db.get_stats()

    print(f"\n{'='*50}")
    print(f"  Knowledge Graph Statistics")
    print(f"{'='*50}")
    print(f"\n  Total Nodes: {s['total_nodes']}")
    print(f"  Total Edges: {s['total_edges']}")

    if s["categories"]:
        print(f"\n  Categories:")
        for cat in s["categories"]:
            print(f"    {cat['category']}: {cat['count']}")

    if s["relationship_types"]:
        print(f"\n  Relationship Types:")
        for rel in s["relationship_types"][:10]:
            print(f"    {rel['relationship']}: {rel['count']}")

    if s["top_connected_nodes"]:
        print(f"\n  Most Connected Entities:")
        for node in s["top_connected_nodes"]:
            print(f"    {node['name']} ({node['category']}): {node['connections']} connections")

    if s["recent_sources"]:
        print(f"\n  Recent Sources:")
        for src in s["recent_sources"]:
            print(f"    {src['file_path']} ({src['node_count']} nodes, {src['edge_count']} edges)")

    print()
    db.close()


def related(entity: str):
    """Find entities related to the given entity."""
    db = GraphDB(DB_PATH)
    result = db.get_related(entity)

    if not result["found"]:
        # Try fuzzy search
        matches = db.search_nodes(entity)
        if matches:
            print(f"Entity '{entity}' not found exactly. Did you mean:")
            for m in matches[:5]:
                print(f"  - {m['name']} ({m['category']})")
        else:
            print(f"Entity '{entity}' not found in the graph.")
        db.close()
        return

    print(f"\n{'='*50}")
    print(f"  Related to: {entity}")
    print(f"{'='*50}\n")

    if not result["related"]:
        print("  No related entities found.")
    else:
        for item in result["related"]:
            indent = "  " * item["depth"]
            print(f"  {indent}{item['name']} ({item['category']})")
            print(f"  {indent}  via: {item['relationship']} (weight: {item['weight']})")

    print()
    db.close()


def main():
    parser = argparse.ArgumentParser(
        description="AI Knowledge Graph - Build and query knowledge graphs from documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --ingest ./documents/
  %(prog)s --ingest paper.md
  %(prog)s --query "What technologies are related to Python?"
  %(prog)s --related "Python"
  %(prog)s --visualize --format dot
  %(prog)s --stats
        """)

    parser.add_argument("--ingest", metavar="PATH", help="Ingest a file or directory")
    parser.add_argument("--query", metavar="QUESTION", help="Query the knowledge graph")
    parser.add_argument("--visualize", action="store_true", help="Export graph for visualization")
    parser.add_argument("--format", choices=["dot", "json"], default="dot",
                        help="Visualization format (default: dot)")
    parser.add_argument("--stats", action="store_true", help="Show graph statistics")
    parser.add_argument("--related", metavar="ENTITY", help="Find related concepts")
    parser.add_argument("--model", default=MODEL, help=f"Ollama model (default: {MODEL})")
    parser.add_argument("--db", default=DB_PATH, help="Database path")

    args = parser.parse_args()

    if not any([args.ingest, args.query, args.visualize, args.stats, args.related]):
        parser.print_help()
        sys.exit(1)

    _apply_config(args.model, args.db)

    if args.ingest:
        ingest(args.ingest)
    elif args.query:
        query(args.query)
    elif args.visualize:
        visualize(args.format)
    elif args.stats:
        stats()
    elif args.related:
        related(args.related)


def _apply_config(model: str, db_path: str):
    """Apply configuration from CLI args."""
    global MODEL, DB_PATH
    MODEL = model
    DB_PATH = db_path


if __name__ == "__main__":
    main()
