#!/bin/bash
# Install dependencies for Voice-to-AI
# Installs sox for audio recording capabilities

echo "🔧 Installing Voice-to-AI dependencies..."
echo ""

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Install it first:"
    echo '   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    exit 1
fi

echo "📦 Installing sox (for audio recording)..."
brew install sox

echo ""
echo "✅ sox installed. The 'rec' command is now available for audio recording."
echo ""
echo "Optional: Install Whisper for speech-to-text:"
echo "  ~/Downloads/AI/.venv/bin/pip install openai-whisper"
echo ""
echo "To run Voice-to-AI:"
echo "  ./voice_ai.py              # Text chat only"
echo "  ./voice_ai.py --speak      # Chat with voice output"
echo "  ./voice_ai.py --model llama3.2 --speak"
