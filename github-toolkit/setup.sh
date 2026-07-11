#!/bin/bash
# GitHub Toolkit Setup Script
# Sets up GITHUB_TOKEN in .zshrc from .env file

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
ZSHRC="$HOME/.zshrc"

echo "🔧 GitHub Toolkit Setup"
echo "─────────────────────────"

# Check for .env file
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  No .env file found."
    echo "   Creating from .env.example..."
    cp "$SCRIPT_DIR/.env.example" "$ENV_FILE"
    echo ""
    echo "📝 Please edit .env and add your GitHub token:"
    echo "   $ENV_FILE"
    echo ""
    echo "   Get a token at: https://github.com/settings/tokens"
    echo "   Required scopes: repo, read:org, gist, read:user"
    exit 1
fi

# Read GITHUB_TOKEN from .env
GITHUB_TOKEN=$(grep -E "^GITHUB_TOKEN=" "$ENV_FILE" | cut -d'=' -f2 | tr -d ' "'"'"'')

if [ -z "$GITHUB_TOKEN" ] || [ "$GITHUB_TOKEN" = "ghp_xxx" ]; then
    echo "❌ Error: GITHUB_TOKEN not set in .env"
    echo "   Edit $ENV_FILE and add your token."
    exit 1
fi

# Check if already in .zshrc
if grep -q "export GITHUB_TOKEN=" "$ZSHRC" 2>/dev/null; then
    echo "ℹ️  GITHUB_TOKEN already exists in .zshrc"
    read -p "   Replace it? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove existing line
        sed -i '' '/^export GITHUB_TOKEN=/d' "$ZSHRC"
    else
        echo "   Skipped."
        exit 0
    fi
fi

# Add to .zshrc
echo "" >> "$ZSHRC"
echo "# GitHub Token (added by github-toolkit setup)" >> "$ZSHRC"
echo "export GITHUB_TOKEN=\"$GITHUB_TOKEN\"" >> "$ZSHRC"

echo "✅ GITHUB_TOKEN added to $ZSHRC"
echo ""
echo "🔄 Reload your shell:"
echo "   source ~/.zshrc"
echo ""
echo "🧪 Verify:"
echo "   echo \$GITHUB_TOKEN"
echo ""

# Install dependencies
echo "📦 Checking Python dependencies..."
VENV_PIP="$HOME/Downloads/AI/.venv/bin/pip"

if [ -f "$VENV_PIP" ]; then
    echo "   Installing httpx..."
    "$VENV_PIP" install httpx > /dev/null 2>&1
    echo "   ✅ Dependencies installed in venv"
else
    echo "   ⚠️  Venv not found at ~/Downloads/AI/.venv"
    echo "   Install manually: pip install httpx"
fi

echo ""
echo "🎉 Setup complete! Try:"
echo "   ./github_toolkit.py --repos"
echo "   ./repo_analyzer.py --health"
echo "   ./auto_commit.py --watch ."
