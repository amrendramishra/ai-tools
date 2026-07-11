# AI Code Reviewer

Automated code review powered by AI (codellama) — reviews files, diffs, repos, and PRs.

## Features

- **Single file review** - Deep analysis of any code file
- **Git diff review** - Review staged or unstaged changes
- **Repo review** - Analyze repository structure and key files
- **PR review** - Compare branches and assess changes
- **Auto-detect language** - Supports 20+ languages
- **Multiple output formats** - Markdown, JSON, inline comments
- **Fix suggestions** - AI-generated code fixes
- **Git hook** - Automated pre-commit reviews

## Checks Performed

- 🐛 Bugs and logical errors
- 🔒 Security vulnerabilities
- ⚡ Performance issues
- 🎨 Style and readability
- 📊 Complexity concerns

## Severity Levels

- 🔴 **Critical** - Must fix before merging
- 🟡 **Warning** - Should be addressed
- 🔵 **Info** - Good to know
- 💡 **Suggestion** - Optional improvement

## Usage

```bash
# Review a single file
./code_reviewer.py --file app.py
./code_reviewer.py --file main.rs --fix

# Review git diff (staged changes)
./code_reviewer.py --diff

# Review entire repository
./code_reviewer.py --repo ./my-project

# Review PR (current branch vs main)
./code_reviewer.py --pr

# Output formats
./code_reviewer.py --file app.py --format json
./code_reviewer.py --file app.py --format inline-comments
./code_reviewer.py --file app.py --format markdown

# Include fix suggestions
./code_reviewer.py --file app.py --fix

# Specify language
./code_reviewer.py --file config --language yaml
```

## Git Hook Installation

```bash
# Install to current repo
./install_hook.sh

# Install to specific repo
./install_hook.sh /path/to/repo
```

The hook will:
- Block commits with critical issues
- Show warnings but allow commits
- Skip gracefully if Ollama isn't running

## Architecture

- **code_reviewer.py** - Main CLI with review logic
- **git_hook.sh** - Pre-commit hook script
- **install_hook.sh** - Hook installer

## Requirements

- Python 3.9+
- Ollama running at localhost:11434
- `codellama` model (falls back to `llama3.2`)
- `requests` package (in project venv)
- Git (for diff/PR features)
