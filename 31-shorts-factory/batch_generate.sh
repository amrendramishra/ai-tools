#!/bin/bash
# batch_generate.sh - Generate all daily shorts for every channel
# Run this once daily to generate all content

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3"
FACTORY="$SCRIPT_DIR/shorts_factory.py"

echo "🎬 AI Shorts Factory - Daily Batch Generation"
echo "================================================"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Check Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌ Ollama is not running! Starting..."
    ollama serve &
    sleep 3
fi

# Check model is available
if ! curl -s http://localhost:11434/api/tags | grep -q "llama3.2"; then
    echo "⚠️  llama3.2 model not found. Pulling..."
    ollama pull llama3.2
fi

echo ""
echo "🚀 Starting batch generation..."
echo ""

# Generate daily batch (respects each channel's posting_frequency)
"$PYTHON" "$FACTORY" --batch-daily --format script

echo ""
echo "📊 Also generating JSON versions for automation..."
"$PYTHON" "$FACTORY" --batch-daily --format json

echo ""
echo "================================================"
echo "✅ Daily batch complete!"
echo "📁 Output: $SCRIPT_DIR/output/"
echo ""

# Show summary
echo "📈 Generated files:"
find "$SCRIPT_DIR/output" -name "*.txt" -newer "$SCRIPT_DIR/output" -o -name "*.json" -newer "$SCRIPT_DIR/output" 2>/dev/null | wc -l | xargs echo "   Total files today:"
echo ""
echo "🕐 Next run: Tomorrow at your scheduled time"
echo "   Add to crontab: 0 6 * * * $SCRIPT_DIR/batch_generate.sh"
