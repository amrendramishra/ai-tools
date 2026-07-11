#!/bin/bash
# Launch the AI Desktop Widget
# Usage: ./launch_widget.sh [native|web]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/Downloads/AI/.venv"
PYTHON="$VENV/bin/python"

# Check venv
if [ ! -f "$PYTHON" ]; then
    echo "Error: Python venv not found at $VENV"
    exit 1
fi

# Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Warning: Ollama not reachable at localhost:11434"
    echo "   Start Ollama first: ollama serve"
    echo ""
fi

MODE="${1:-web}"

case "$MODE" in
    native)
        echo "🖥  Launching native macOS widget..."
        echo "   Toggle: Cmd+Shift+A"
        echo ""
        "$PYTHON" "$SCRIPT_DIR/widget.py"
        ;;
    web)
        echo "🌐 Launching web-based widget..."
        echo "   Server: http://127.0.0.1:3001"
        echo "   Press Ctrl+C to stop"
        echo ""
        "$PYTHON" "$SCRIPT_DIR/widget_web.py"
        ;;
    *)
        echo "Usage: $0 [native|web]"
        echo ""
        echo "  native  - Native macOS window (PyObjC/Cocoa)"
        echo "  web     - Web-based widget (Chrome app mode)"
        exit 1
        ;;
esac
