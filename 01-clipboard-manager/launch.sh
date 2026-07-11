#!/bin/bash
# Launch script for AI Clipboard Manager
# Usage: ./launch.sh start|stop|status|restart

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/daemon.pid"
PYTHON="$HOME/Downloads/AI/.venv/bin/python3"
SCRIPT="$SCRIPT_DIR/clipboard_manager.py"

start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "❌ Daemon already running (PID: $PID)"
            return 1
        else
            rm -f "$PID_FILE"
        fi
    fi
    echo "🚀 Starting AI Clipboard Manager..."
    "$PYTHON" "$SCRIPT" --daemon
    sleep 1
    if [ -f "$PID_FILE" ]; then
        echo "✅ Running (PID: $(cat "$PID_FILE"))"
    fi
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "🛑 Stopping daemon (PID: $PID)..."
            kill "$PID"
            rm -f "$PID_FILE"
            echo "✅ Stopped."
        else
            echo "⚠️  PID file exists but process not running. Cleaning up."
            rm -f "$PID_FILE"
        fi
    else
        echo "ℹ️  Daemon is not running."
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "✅ Daemon is running (PID: $PID)"
        else
            echo "⚠️  PID file exists but process not running."
        fi
    else
        echo "ℹ️  Daemon is not running."
    fi
}

case "${1:-}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the clipboard monitoring daemon"
        echo "  stop    - Stop the daemon"
        echo "  restart - Restart the daemon"
        echo "  status  - Check if the daemon is running"
        exit 1
        ;;
esac
