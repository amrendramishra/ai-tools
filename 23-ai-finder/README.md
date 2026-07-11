# AI-Powered Finder

Natural language file search powered by Ollama AI. Ask for files the way you'd describe them to a person.

## Features

- **Natural Language Search**: Find files using plain English queries
- **Smart Indexing**: SQLite-cached index for fast repeated searches
- **Fuzzy Matching**: Finds files even with imprecise queries
- **AI Interpretation**: Converts natural language to search criteria
- **Recent Files**: View recently modified files with AI-generated descriptions
- **Quick Open**: Open found files directly from results

## Requirements

- Python 3.8+
- Ollama running at localhost:11434 (model: llama3.2)
- `requests` library

## Usage

```bash
# Index default directories (~/Documents, ~/Downloads, ~/Desktop, ~/IdeaProjects)
./ai_finder.py --index

# Index a specific directory
./ai_finder.py --index ~/Projects

# Natural language search
./ai_finder.py --find 'that PDF about taxes from March'
./ai_finder.py --find 'large video files'
./ai_finder.py --find 'python scripts about web scraping'

# Search and open top result
./ai_finder.py --find 'resume document' --open

# Show recently modified files
./ai_finder.py --recent
./ai_finder.py --recent --limit 10
```

## How It Works

1. **Indexing**: Walks directories, collecting file metadata (name, extension, size, dates)
2. **AI Interpretation**: Ollama converts your query to structured search criteria
3. **Search**: Combines SQL filtering with fuzzy name matching
4. **Scoring**: Results ranked by relevance score

## Data Storage

Index cached in `~/.ai_finder_index.db` (SQLite). Re-index anytime to update.
