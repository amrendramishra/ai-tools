#!/bin/bash
# Install the AI Code Reviewer as a git pre-commit hook
# Usage: ./install_hook.sh [/path/to/repo]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_SOURCE="$SCRIPT_DIR/git_hook.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Get target repo
REPO_PATH="${1:-.}"
REPO_PATH="$(cd "$REPO_PATH" && pwd)"

# Verify it's a git repo
if [ ! -d "$REPO_PATH/.git" ]; then
    echo -e "${RED}Error: $REPO_PATH is not a git repository.${NC}"
    echo "Usage: $0 [/path/to/git/repo]"
    exit 1
fi

HOOKS_DIR="$REPO_PATH/.git/hooks"
HOOK_TARGET="$HOOKS_DIR/pre-commit"

# Create hooks directory if needed
mkdir -p "$HOOKS_DIR"

# Check for existing hook
if [ -f "$HOOK_TARGET" ]; then
    echo -e "${YELLOW}⚠️  Existing pre-commit hook found at:${NC}"
    echo "   $HOOK_TARGET"
    echo ""
    read -p "Overwrite? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Aborted."
        exit 0
    fi
    # Backup existing hook
    cp "$HOOK_TARGET" "$HOOK_TARGET.backup"
    echo "   Backup saved: $HOOK_TARGET.backup"
fi

# Install hook
cp "$HOOK_SOURCE" "$HOOK_TARGET"
chmod +x "$HOOK_TARGET"

echo -e "${GREEN}✅ AI Code Reviewer hook installed!${NC}"
echo ""
echo "   Repository: $REPO_PATH"
echo "   Hook: $HOOK_TARGET"
echo ""
echo "   The reviewer will run on each commit."
echo "   Skip with: git commit --no-verify"
echo ""
echo "   Requirements:"
echo "   - Ollama running at localhost:11434"
echo "   - Python venv at ~/Downloads/AI/.venv"
echo "   - codellama model pulled in Ollama"
