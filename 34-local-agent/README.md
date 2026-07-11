# 🤖 Local AI Agent with Memory (Project 34)

A personal AI agent that **learns about you** over time and becomes increasingly personalized. The more you use it, the smarter it gets.

## Features

- **Persistent Memory**: Remembers everything across sessions using SQLite
- **Automatic Learning**: Extracts facts from every conversation
- **Pattern Detection**: Notices when you're active, what you work on, habits
- **Predictions**: Anticipates what you might need
- **Context-Aware**: Uses time of day, day of week, recent activity
- **Personality**: Friendly, proactive, slightly humorous

## Architecture

```
agent.py          → Main executable (CLI interface)
memory_engine.py  → Memory/learning system (SQLite-backed)
config.json       → Personality & settings
agent_memory.db   → Auto-created database (your memories)
```

## Usage

```bash
# Start an interactive conversation (it remembers everything)
./agent.py --chat

# Teach it something explicitly
./agent.py --teach "I prefer Python over JavaScript"
./agent.py --teach "I work from 9am to 5pm"
./agent.py --teach "My name is Alex"

# Get proactive suggestions based on time and patterns
./agent.py --suggest

# See what it knows about you
./agent.py --memory

# Forget specific memories
./agent.py --forget "work schedule"

# Get a personalized daily briefing
./agent.py --daily-briefing

# Weekly activity review
./agent.py --weekly-review
```

## Memory Database Schema

| Table | Purpose |
|-------|---------|
| `facts` | Things learned about you (preferences, habits, schedule) |
| `interactions` | Full conversation history |
| `patterns` | Detected behavioral patterns |
| `predictions` | What you might need next |
| `sessions` | Conversation session tracking |

## Configuration

Edit `config.json` to customize:

- **Agent name & personality**: Change how it behaves
- **Model**: Switch Ollama model (default: llama3.2)
- **Learning rate**: How aggressively it extracts facts
- **Memory retention**: How long facts are kept
- **Pattern detection**: Types of patterns to look for

## How It Learns

1. **Explicit teaching**: `--teach` stores facts with 100% confidence
2. **Conversation extraction**: AI analyzes every exchange for learnable facts
3. **Pattern detection**: Time-based and behavioral patterns accumulate
4. **Confidence scoring**: Facts get more confident when referenced repeatedly

## Requirements

- Python 3.10+
- Ollama running locally (localhost:11434)
- `requests` library
- Model: llama3.2 (or change in config.json)

## Tips

- Chat regularly to build up a knowledge base
- Use `--teach` for important facts you want stored immediately
- Check `--memory` periodically to see what it's learning
- The agent improves significantly after 20+ interactions
