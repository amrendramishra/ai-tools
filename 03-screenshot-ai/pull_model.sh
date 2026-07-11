#!/bin/bash
# Pull the llava model for screenshot analysis

echo "🔄 Pulling llava model from Ollama..."
echo "   This model supports image understanding (vision + language)."
echo ""

ollama pull llava

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ llava model pulled successfully!"
    echo "   You can now use: ./screenshot_ai.py --capture --analyze"
else
    echo ""
    echo "❌ Failed to pull llava model."
    echo "   Make sure Ollama is running: ollama serve"
    exit 1
fi
