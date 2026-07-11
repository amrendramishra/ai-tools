# Project 16: Personal AI Web UI

A local ChatGPT-like web interface powered by Ollama.

## Features

- Modern dark theme chat interface
- Streams responses from Ollama in real-time
- Multiple conversations with sidebar navigation
- Model selector dropdown (auto-detects available models)
- Markdown rendering with code syntax highlighting
- Copy code button for code blocks
- Chat history persisted in localStorage
- Stop generation button
- Responsive design (mobile-friendly)
- No external dependencies - pure vanilla JS/CSS/HTML

## Quick Start

```bash
./start.sh
```

Or manually:

```bash
./server.py
# Open http://localhost:3000
```

## Requirements

- Python 3.x (uses only stdlib)
- Ollama running on localhost:11434

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Serves the chat UI |
| GET | /api/models | Lists available Ollama models |
| POST | /api/chat | Streams chat responses (SSE) |
| POST | /api/chat/stop | Stops active generation |
| GET | /health | Health check |

## Architecture

- `server.py` - Python HTTP server (no Flask, uses stdlib http.server)
- `static/index.html` - Single-page app with inline CSS and JS
- All communication with Ollama via streaming Server-Sent Events
