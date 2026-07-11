# 🤖 AI Tools — 45 AI-Powered Tools for Mac

> A complete local AI ecosystem built with Ollama, MCP, LangChain, and Python. All tools run locally, free, and private.

[![Models](https://img.shields.io/badge/Ollama_Models-6-blue)]()
[![Projects](https://img.shields.io/badge/Projects-45-green)]()
[![MCP](https://img.shields.io/badge/MCP_Servers-8-purple)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)]()

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  AI COMMAND CENTER                        │
│                                                          │
│  Voice Commander ──► 45 AI Tools ──► Ollama (6 models)  │
│       │                    │              │              │
│  Ctrl+Space /         MCP Servers    llama3.2           │
│  "Hey Jarvis"         (8 connected)  codellama          │
│                                      mistral            │
│  GitHub Actions (24/7 cloud)         phi3, gemma2       │
└─────────────────────────────────────────────────────────┘
```

## 📁 All 45 Projects

### 🚀 Quick Power-Ups
| # | Project | Description |
|---|---------|-------------|
| 01 | [clipboard-manager](./01-clipboard-manager/) | AI clipboard monitor — auto-classifies, summarizes, searches |
| 02 | [voice-to-ai](./02-voice-to-ai/) | Talk to AI, get spoken responses |
| 03 | [screenshot-ai](./03-screenshot-ai/) | Take screenshots, AI explains what's on screen |
| 04 | [email-responder](./04-email-responder/) | AI drafts email replies in 3 tones |
| 05 | [meeting-notes](./05-meeting-notes/) | Paste transcript → get structured notes + action items |

### 📺 YouTube Automation (9 channels)
| # | Project | Description |
|---|---------|-------------|
| 06 | [content-pipeline](./06-content-pipeline/) | Generate scripts for all channels at once |
| 07 | [trending-detector](./07-trending-detector/) | Find viral topics using Tavily + AI ranking |
| 08 | [thumbnail-analyzer](./08-thumbnail-analyzer/) | Score thumbnails with Ollama llava model |
| 09 | [comment-responder](./09-comment-responder/) | AI replies to comments per channel persona |
| 10 | [analytics-dashboard](./10-analytics-dashboard/) | AI analyzes growth and suggests strategy |

### 🤖 Advanced AI
| # | Project | Description |
|---|---------|-------------|
| 11 | [multi-agent-crew](./11-multi-agent-crew/) | 5 AI agents pipeline: Researcher→Writer→Editor→Reviewer→Publisher |
| 12 | [fine-tune](./12-fine-tune/) | Prepare data + create custom Ollama models |
| 13 | [knowledge-graph](./13-knowledge-graph/) | Build AI knowledge graph from documents |
| 14 | [personal-assistant](./14-personal-assistant/) | Persistent memory AI that remembers everything |
| 15 | [code-reviewer](./15-code-reviewer/) | AI reviews git diffs, installs as pre-commit hook |

### 🌐 Web & API
| # | Project | Description |
|---|---------|-------------|
| 16 | [web-ui](./16-web-ui/) | Local ChatGPT-like interface (http://localhost:3000) |
| 17 | [api-gateway](./17-api-gateway/) | OpenAI-compatible API with smart model routing |
| 18 | [bookmark-manager](./18-bookmark-manager/) | Save URLs → AI summarizes, tags, makes searchable |
| 19 | [resume-generator](./19-resume-generator/) | AI tailors resume to job postings |
| 20 | [blog-writer](./20-blog-writer/) | Full SEO blog posts with frontmatter |

### 🏠 Mac Productivity
| # | Project | Description |
|---|---------|-------------|
| 21 | [file-organizer](./21-file-organizer/) | AI watches folders, auto-organizes files |
| 22 | [focus-mode](./22-focus-mode/) | Pomodoro + AI coaching + app blocking |
| 23 | [ai-finder](./23-ai-finder/) | Natural language file search ("that tax PDF from March") |
| 24 | [habit-tracker](./24-habit-tracker/) | Track habits with AI coaching and streaks |
| 25 | [auto-docs](./25-auto-docs/) | Generate documentation from code repos |

### 💰 Money-Making
| # | Project | Description |
|---|---------|-------------|
| 26 | [saas-template](./26-saas-template/) | Ready-to-deploy AI SaaS with landing page |
| 27 | [content-repurposer](./27-content-repurposer/) | One input → 7 formats (tweets, LinkedIn, shorts, etc.) |
| 28 | [freelance-automation](./28-freelance-automation/) | AI-generated proposals and pitches |
| 29 | [course-creator](./29-course-creator/) | Complete Udemy/Skillshare course generator |
| 30 | [ai-newsletter](./30-ai-newsletter/) | Curate + write newsletters from RSS feeds |

### 🎬 Revenue Generators
| # | Project | Description |
|---|---------|-------------|
| 31 | [shorts-factory](./31-shorts-factory/) | Generate YouTube Shorts scripts (hook + body + CTA) |
| 32 | [udemy-course](./32-udemy-course/) | Full publishable course with scripts, quizzes, SEO |
| 33 | [faceless-automator](./33-faceless-automator/) | Zero-effort video pipeline with TTS |

### 🧪 Cutting Edge
| # | Project | Description |
|---|---------|-------------|
| 34 | [local-agent](./34-local-agent/) | AI agent that LEARNS about you over time |
| 35 | [phone-assistant](./35-phone-assistant/) | Record, transcribe, summarize calls/meetings |
| 36 | [desktop-widget](./36-desktop-widget/) | Floating AI chat on your Mac desktop |

### 🏢 Work & Career
| # | Project | Description |
|---|---------|-------------|
| 37 | [delta-docs-rag](./37-delta-docs-rag/) | RAG over your work documentation |
| 38 | [interview-prep](./38-interview-prep/) | Mock interviews: DSA, System Design, Behavioral |
| 39 | [saas-launch](./39-saas-launch/) | Complete launch kit: landing page, emails, legal |

### 🎮 Fun & Personal
| # | Project | Description |
|---|---------|-------------|
| 40 | [ai-dj](./40-ai-dj/) | AI picks music based on mood/time/activity |
| 41 | [dream-journal](./41-dream-journal/) | Record dreams, AI analyzes symbols and patterns |
| 42 | [whatsapp-bot](./42-whatsapp-bot/) | Family Telegram/WhatsApp bot with 10 commands |

### 🔧 Utilities
| # | Project | Description |
|---|---------|-------------|
| — | [github-toolkit](./github-toolkit/) | 14-command GitHub automation CLI |
| — | [tavily-tools](./tavily-tools/) | Deep research with Tavily API + Ollama |
| — | [voice-commander](./voice-commander/) | Control ALL tools by voice or hotkey |

---

## ⚡ Quick Start

```bash
# 1. Install Ollama
brew install ollama && brew services start ollama
ollama pull llama3.2

# 2. Set up Python environment
cd ~/Downloads/AI && python3 -m venv .venv
source .venv/bin/activate
pip install langchain chromadb openai httpx requests beautifulsoup4

# 3. Run any tool
./16-web-ui/start.sh              # Local ChatGPT UI
./voice-commander/vc              # Voice control everything
./14-personal-assistant/assistant.py  # AI that remembers you
./31-shorts-factory/batch_generate.sh # Generate YouTube Shorts
```

## 🎤 Voice Commander

Control all 45 tools with one command:
```bash
vc                    # Interactive mode
vc -c "generate content"  # Single command
vc --continuous       # Always listening ("Hey Jarvis")
```

## 🛠️ Tech Stack

- **AI Models**: Ollama (llama3.2, codellama, mistral, phi3, gemma2, nomic-embed-text)
- **Speech**: OpenAI Whisper (offline) + Google Speech (online)
- **Vector DB**: ChromaDB
- **Framework**: LangChain, Python stdlib
- **MCP**: Model Context Protocol (8 servers)
- **Cloud**: GitHub Actions (5 workflows, runs 24/7)
- **Platform**: macOS (Apple Silicon optimized)

## 📊 Stats

| Metric | Count |
|--------|-------|
| Projects | 45 |
| Executable Scripts | 53 |
| AI Models (local) | 6 |
| MCP Servers | 8 |
| GitHub Actions | 5 |
| YouTube Channels Automated | 9 |
| Cost | ₹0/month |

---

## 👨‍💻 Author

**Amrendra Narayan Mishra** — Software Engineer, AI Automation Enthusiast

- 🌐 [Portfolio](https://amrendranmishra.dev)
- 💼 [GitHub Profile](https://github.com/amrendramishra)
- 📺 9 YouTube channels (fully automated, ₹0/month)

---

## 📄 License

MIT — Use freely, build upon it, share it.
