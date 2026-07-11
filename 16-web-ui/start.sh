#!/bin/bash
# Start Personal AI Web UI
cd "$(dirname "$0")"

echo "🤖 Starting Personal AI Web UI..."
echo "   Opening http://localhost:3000 in your browser..."

# Open browser after a short delay
(sleep 1 && open "http://localhost:3000" 2>/dev/null || xdg-open "http://localhost:3000" 2>/dev/null) &

# Start server
exec ./server.py
