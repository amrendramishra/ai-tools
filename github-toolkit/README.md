# 🛠️ GitHub Toolkit

All-in-one GitHub automation toolkit for managing repositories, generating AI-powered insights, and streamlining your workflow.

## 🚀 Quick Start

```bash
# 1. Setup
cp .env.example .env
# Edit .env with your GitHub token
chmod +x setup.sh && ./setup.sh

# 2. Use
./github_toolkit.py --repos
./github_toolkit.py --stats
```

## 📋 Requirements

- Python 3.10+ (venv at `~/Downloads/AI/.venv`)
- `httpx` (`pip install httpx`)
- GitHub Personal Access Token ([create one](https://github.com/settings/tokens))
  - Scopes: `repo`, `read:org`, `gist`, `read:user`
- Ollama running locally (for AI features): `ollama serve`

## 🔧 Tools

### github_toolkit.py - All-in-One CLI

| Command | Description |
|---------|-------------|
| `--repos` | List all repos with stars, forks, last updated |
| `--create <name> --description <desc> --private` | Create new repo |
| `--clone-all [dir]` | Clone all repos to directory |
| `--backup [dir]` | Backup all repos (clone/pull) |
| `--stats` | Full profile statistics |
| `--search <query>` | Search code across repos |
| `--issues` | List open issues across all repos |
| `--pr-review` | AI reviews open PRs |
| `--readme-gen <repo>` | AI generates README |
| `--commit-history` | Recent commits across repos |
| `--cleanup` | Find inactive repos |
| `--deploy-pages <repo>` | Enable GitHub Pages |
| `--create-gist <file>` | Create gist from file |
| `--profile-readme` | AI generates profile README |

### auto_commit.py - Smart Auto-Commit

```bash
# Watch mode - auto-commits on changes
./auto_commit.py --watch ~/projects/myapp --interval 60

# Generate commit message for staged changes
./auto_commit.py --message .
```

### repo_analyzer.py - AI Repo Analysis

```bash
# Analyze a repo
./repo_analyzer.py --repo my-project

# Compare repos
./repo_analyzer.py --compare repo1 repo2

# Health check all repos
./repo_analyzer.py --health

# AI suggestions
./repo_analyzer.py --suggest-actions
```

### github_pages_portfolio.html

Beautiful auto-generated portfolio page that fetches your repos dynamically.
Deploy to `amrendramishra.github.io`.

## 🤖 AI Features

AI features use Ollama (local LLM) running at `localhost:11434`:

- **PR Review**: Analyzes diffs and provides code review
- **README Generation**: Creates professional READMEs
- **Commit Messages**: Generates conventional commit messages
- **Repo Analysis**: Suggests improvements and next steps
- **Profile README**: Generates stunning GitHub profile

Start Ollama: `ollama serve`
Pull a model: `ollama pull llama3.2`

## 📁 File Structure

```
github-toolkit/
├── github_toolkit.py      # Main CLI tool
├── auto_commit.py         # Auto-commit with AI messages
├── repo_analyzer.py       # AI repo analysis
├── github_pages_portfolio.html  # Portfolio page
├── setup.sh               # Setup script
├── .env.example           # Environment template
└── README.md              # This file
```

## ⚡ Examples

```bash
# Quick profile overview
./github_toolkit.py --stats

# Find stale repos to archive
./github_toolkit.py --cleanup

# AI-powered code review
./github_toolkit.py --pr-review

# Full repo health audit
./repo_analyzer.py --health

# Watch project and auto-commit
./auto_commit.py --watch ~/projects/myapp
```

## 📜 License

MIT
