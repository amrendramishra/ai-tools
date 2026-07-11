# Personal AI Assistant

An always-on personal AI assistant with persistent memory, reminders, and notes.

## Features

- **Interactive REPL** - Rich conversational interface with commands
- **Persistent Memory** - Remembers facts about you across sessions
- **Reminders** - Set and track time-based reminders
- **Notes** - Quick note-taking with search
- **Context-Aware** - Uses time of day, pending tasks for proactive suggestions
- **Memory Extraction** - Automatically learns preferences from conversations

## Usage

```bash
# Start interactive mode
./assistant.py

# Show what the assistant remembers
./assistant.py --memory

# Show today's schedule/reminders
./assistant.py --schedule

# Set a reminder
./assistant.py --remind "Buy groceries" --at "5pm"
./assistant.py --remind "Meeting prep" --at "tomorrow"
./assistant.py --remind "Check email" --at "30 minutes"

# Quick notes
./assistant.py --note "Great idea for the project refactor"
./assistant.py --search-notes "project"

# Clear memory
./assistant.py --forget
```

## Interactive Commands

While in the REPL:
- `/memory` - Show stored memories
- `/schedule` - Show today's reminders
- `/note <text>` - Save a note
- `/remind <text>` - Set a reminder
- `/notes [query]` - List or search notes
- `/forget` - Clear all memory
- `/quit` - Exit

## Architecture

- **assistant.py** - Main CLI and REPL with AI chat integration
- **memory.py** - SQLite memory management (conversations, facts, notes, reminders)

## Requirements

- Python 3.9+
- Ollama running at localhost:11434
- `requests` package (in project venv)
