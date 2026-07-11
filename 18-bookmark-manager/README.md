# AI Bookmark Manager

Intelligent bookmark organization with AI-powered summaries, tagging, and semantic search using Ollama.

## Features

- **Smart Bookmarking**: Fetches URL content, generates AI summaries and tags automatically
- **Auto-Categorization**: Classifies into tech, finance, learning, news, tools, etc.
- **Semantic Search**: AI-powered search that understands meaning, not just keywords
- **Tag Management**: View all tags with usage counts
- **Import/Export**: Compatible with browser bookmark HTML format and JSON
- **Daily Digest**: AI-generated summary of recently saved bookmarks

## Requirements

- Python 3.8+
- Ollama running at `localhost:11434`
- Python packages: `requests`, `beautifulsoup4`

## Setup

```bash
source ~/Downloads/AI/.venv/bin/activate
pip install requests beautifulsoup4
```

## Usage

```bash
# Add a bookmark (AI summarizes and tags it)
./bookmark_manager.py --add https://example.com/article

# List all bookmarks
./bookmark_manager.py --list

# Semantic search
./bookmark_manager.py --search "machine learning tutorials"

# Show all tags
./bookmark_manager.py --tags

# Export as HTML or JSON
./bookmark_manager.py --export
./bookmark_manager.py --export --format json

# Import browser bookmarks
./bookmark_manager.py --import-file bookmarks.html

# Filter by category
./bookmark_manager.py --category tech

# Daily digest of recent bookmarks
./bookmark_manager.py --daily-digest
```

## Categories

Bookmarks are auto-categorized into:
tech, finance, learning, news, tools, entertainment, health, science, design, other

## Storage

Bookmarks stored in local SQLite database (`bookmarks.db`) with fields:
URL, title, summary, tags, category, date added, content snippet.
