# AI Clipboard Manager

An intelligent clipboard monitor for macOS that automatically classifies, stores, and summarizes your clipboard history using AI (Ollama + llama3.2).

## Features

- **Auto-classification**: Detects code, URLs, emails, phone numbers, addresses, and plain text
- **AI Summarization**: Long text clips are automatically summarized via Ollama
- **macOS Notifications**: Get notified when clips are classified
- **SQLite Storage**: All clips stored locally in `clipboard.db`
- **Search & Stats**: Query your clipboard history from the command line
- **Background Daemon**: Runs silently in the background

## Prerequisites

- macOS (uses `pbpaste` and `osascript`)
- Python 3.9+ (via venv at `~/Downloads/AI/.venv`)
- Ollama running at `localhost:11434` with `llama3.2` model

## Usage

### Start/Stop the Daemon

```bash
./launch.sh start    # Start monitoring
./launch.sh stop     # Stop monitoring
./launch.sh status   # Check if running
./launch.sh restart  # Restart
```

### Query Clipboard History

```bash
# List last 20 clips
./clipboard_manager.py --list

# Search clips
./clipboard_manager.py --search "python"

# Show statistics
./clipboard_manager.py --stats
```

### Run in Foreground (for debugging)

```bash
./clipboard_manager.py --foreground
```

## How It Works

1. The daemon polls `pbpaste` every second for clipboard changes
2. New content is classified using regex pattern matching
3. Long text (>200 chars) is summarized using Ollama's llama3.2 model
4. Everything is stored in SQLite with category, timestamp, and optional summary
5. A macOS notification is sent for each new classified clip

## Categories

| Category | Detection |
|----------|-----------|
| `url`    | HTTP/HTTPS links |
| `email`  | Email addresses |
| `phone`  | Phone numbers (various formats) |
| `address`| Street addresses with numbers |
| `code`   | Programming language patterns |
| `text`   | Everything else |

## Files

- `clipboard_manager.py` - Main script
- `launch.sh` - Daemon management script
- `clipboard.db` - SQLite database (created on first run)
- `daemon.pid` - PID file for running daemon
- `daemon.log` - Log file for daemon output
