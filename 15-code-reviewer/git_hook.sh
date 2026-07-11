#!/bin/bash
# Git pre-commit hook that runs the AI Code Reviewer
# Installed by install_hook.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REVIEWER_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")/Downloads/AI/projects/15-code-reviewer"
VENV_DIR="$HOME/Downloads/AI/.venv"

# Colors
RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "🔍 Running AI Code Review on staged changes..."
echo "================================================"

# Activate venv if available
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
fi

# Find the reviewer script
REVIEWER=""
if [ -f "$REVIEWER_DIR/code_reviewer.py" ]; then
    REVIEWER="$REVIEWER_DIR/code_reviewer.py"
elif [ -f "$(git rev-parse --show-toplevel)/.git/hooks/code_reviewer.py" ]; then
    REVIEWER="$(git rev-parse --show-toplevel)/.git/hooks/code_reviewer.py"
fi

if [ -z "$REVIEWER" ]; then
    echo -e "${YELLOW}⚠️  Code reviewer not found. Skipping review.${NC}"
    exit 0
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Ollama not running. Skipping AI review.${NC}"
    exit 0
fi

# Get staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    echo "No staged files to review."
    exit 0
fi

# Run review on diff
REVIEW_OUTPUT=$(python3 "$REVIEWER" --diff --format markdown 2>/dev/null)

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Review encountered an error. Proceeding with commit.${NC}"
    exit 0
fi

# Check for critical issues
if echo "$REVIEW_OUTPUT" | grep -qi "critical"; then
    echo -e "${RED}🔴 CRITICAL issues found in staged changes:${NC}"
    echo ""
    echo "$REVIEW_OUTPUT"
    echo ""
    echo -e "${RED}Commit blocked due to critical issues.${NC}"
    echo "Use 'git commit --no-verify' to skip this check."
    exit 1
fi

# Show warnings but allow commit
if echo "$REVIEW_OUTPUT" | grep -qi "warning"; then
    echo -e "${YELLOW}🟡 Warnings found:${NC}"
    echo ""
    echo "$REVIEW_OUTPUT"
    echo ""
    echo -e "${GREEN}Proceeding with commit (warnings only).${NC}"
fi

echo -e "${GREEN}✅ Code review passed.${NC}"
exit 0
