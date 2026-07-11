# Mac Desktop AI Widget

A floating AI chat widget that stays on screen as an always-on-top overlay. Queries Ollama for local AI responses with streaming support.

## Two Modes

### 1. Native macOS Widget (`widget.py`)
Uses PyObjC/Cocoa to create a native floating window:
- `NSWindow` with `NSFloatingWindowLevel` (always on top)
- Draggable, resizable, semi-transparent
- Global hotkey: **Cmd+Shift+A** to toggle visibility
- Streaming responses with real-time text display
- Model selector dropdown
- Dark theme with colored message labels

### 2. Web-based Widget (`widget_web.py`)
Opens a compact browser window with a glassmorphism chat UI:
- Server-Sent Events (SSE) for streaming responses
- Chrome app mode (no toolbar/URL bar) for widget-like feel
- Beautiful dark glassmorphism design
- Draggable title bar
- Typing animation with cursor
- Model selector

## Quick Start

```bash
# Launch web-based widget (recommended)
./launch_widget.sh web

# Launch native macOS widget
./launch_widget.sh native
```

## Requirements

- Python 3.x with venv at `~/Downloads/AI/.venv`
- Ollama running at `localhost:11434`
- PyObjC (for native mode) - already in venv
- Chrome/Brave (optional, for web mode app window)

## Features

| Feature | Native | Web |
|---------|--------|-----|
| Always on top | ✅ | ✅ (Chrome app mode) |
| Streaming responses | ✅ | ✅ (SSE) |
| Model selector | ✅ | ✅ |
| Global hotkey | ✅ Cmd+Shift+A | ⚠️ Browser-only |
| Draggable | ✅ Title bar | ✅ Title bar |
| Resizable | ✅ | ✅ |
| Semi-transparent | ✅ 92% opacity | ✅ Glassmorphism |
| Typing animation | ✅ Char-by-char | ✅ Cursor blink |
| Minimize | ✅ | ✅ |

## Architecture

```
36-desktop-widget/
├── widget.py          # Native macOS widget (PyObjC/Cocoa)
├── widget_web.py      # Web-based widget server
├── static/
│   └── widget.html    # Widget UI (glassmorphism theme)
├── launch_widget.sh   # Launch script
└── README.md
```

## API Endpoints (Web Mode)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves widget.html |
| `/api/models` | GET | List available Ollama models |
| `/api/chat` | POST | Send message, returns SSE stream |
| `/health` | GET | Server health check |

## Chat Request Format

```json
POST /api/chat
{
    "model": "llama3.2",
    "messages": [
        {"role": "user", "content": "Hello!"}
    ]
}
```

Response is SSE stream:
```
data: {"content": "Hi", "done": false}
data: {"content": " there!", "done": false}
data: {"content": "", "done": true}
```

## Keyboard Shortcuts

- **Cmd+Shift+A**: Toggle widget visibility (native mode)
- **Enter**: Send message
- **Shift+Enter**: New line in input (web mode)
