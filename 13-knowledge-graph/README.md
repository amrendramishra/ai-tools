# AI Knowledge Graph

Build and query knowledge graphs from documents using AI-powered entity extraction.

## Features

- **Ingest documents** - Extract entities and relationships from text files
- **Query** - Ask natural language questions answered from the knowledge graph
- **Visualize** - Export as DOT (Graphviz) or JSON format
- **Statistics** - View graph metrics (nodes, edges, clusters)
- **Related entities** - Find connected concepts via graph traversal
- **Incremental updates** - Only re-processes changed files

## Usage

```bash
# Ingest a file or directory
./knowledge_graph.py --ingest ./documents/
./knowledge_graph.py --ingest paper.md

# Query the knowledge graph
./knowledge_graph.py --query "What technologies are related to Python?"

# Find related entities
./knowledge_graph.py --related "Machine Learning"

# Visualize the graph
./knowledge_graph.py --visualize --format dot
./knowledge_graph.py --visualize --format json

# Show statistics
./knowledge_graph.py --stats
```

## Architecture

- **knowledge_graph.py** - Main CLI with AI extraction and query logic
- **graph_db.py** - SQLite-based graph storage (nodes table, edges table)

## Requirements

- Python 3.9+
- Ollama running at localhost:11434
- `requests` package (in project venv)

## Graph Storage

Uses SQLite with:
- `nodes` table: entities with name, category, properties
- `edges` table: relationships with source, target, type, weight
- `ingestion_log` table: tracks processed files for incremental updates

## Visualization

Export to DOT format and render with Graphviz:
```bash
./knowledge_graph.py --visualize --format dot
dot -Tpng knowledge_graph.dot -o knowledge_graph.png
```
