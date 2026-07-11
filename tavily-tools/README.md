# 🔬 Tavily Research Tool

AI-powered research assistant that combines [Tavily](https://tavily.com) search API with local Ollama LLM for intelligent analysis and synthesis.

## 🚀 Quick Start

```bash
# 1. Set API key
export TAVILY_API_KEY=tvly-your_key_here

# 2. Ensure Ollama is running
ollama serve

# 3. Research!
./tavily_research.py --topic "quantum computing"
```

## 📋 Requirements

- Python 3.10+ (venv at `~/Downloads/AI/.venv`)
- `httpx` (`pip install httpx`)
- Tavily API key ([get one](https://tavily.com))
- Ollama running locally for AI synthesis

## 🔧 Commands

| Command | Description |
|---------|-------------|
| `--topic <topic>` | Deep research with multiple searches + AI synthesis |
| `--news` | Latest news summary with AI digest |
| `--compare <A> <B>` | Side-by-side comparison |
| `--fact-check <claim>` | Verify a claim with sources |
| `--market-research <product>` | Market analysis |
| `--trend <topic>` | Trend analysis with predictions |

## ⚡ Examples

```bash
# Deep research
./tavily_research.py --topic "rust vs go for microservices"

# Compare technologies
./tavily_research.py --compare "FastAPI" "Express.js"

# Fact check
./tavily_research.py --fact-check "TypeScript is faster than JavaScript"

# Market research
./tavily_research.py --market-research "AI coding assistants"

# Trends
./tavily_research.py --trend "edge computing"

# News digest
./tavily_research.py --news
```

## 🤖 How It Works

1. **Multi-angle search**: Each command performs 3-5 searches from different angles
2. **Source aggregation**: Collects and deduplicates results
3. **AI synthesis**: Ollama analyzes all sources and generates structured insights
4. **Source citation**: All claims are backed by referenced sources

## 📁 Files

```
tavily-tools/
├── tavily_research.py    # Main research tool
├── .env.example          # Environment template
└── README.md             # This file
```

## 🔑 Environment Setup

```bash
# Add to ~/.zshrc
export TAVILY_API_KEY="tvly-your_key_here"

# Reload
source ~/.zshrc
```

## 📜 License

MIT
