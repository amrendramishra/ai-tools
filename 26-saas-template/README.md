# AI SaaS Template - NeuralAPI

A ready-to-deploy AI SaaS boilerplate with API key management, rate limiting, usage tracking, and multiple AI endpoints.

## Quick Start

```bash
# Activate venv
source ~/Downloads/AI/.venv/bin/activate

# Install dependencies
pip install flask requests

# Ensure Ollama is running
ollama serve

# Run the app
python app.py
```

Visit http://localhost:5000

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Landing page |
| GET | /health | Health check |
| POST | /api/generate | Text generation |
| POST | /api/summarize | Summarization |
| POST | /api/translate | Translation |
| GET | /api/usage | Usage stats |
| POST | /api/keys | Create API key |

## Authentication

All `/api/*` endpoints (except `/api/keys`) require an API key via:
- Header: `X-API-Key: your-key`
- Query param: `?api_key=your-key`

## Configuration

Edit `config.json` to customize:
- Pricing tiers and features
- Rate limits per tier
- Ollama model and URL

## Environment Variables

- `OLLAMA_URL` - Ollama server URL (default: http://localhost:11434)
- `OLLAMA_MODEL` - Model to use (default: llama3.2)

## Customization

1. Edit `config.json` for pricing/limits
2. Edit `static/index.html` for branding
3. Add new endpoints in `app.py`

## Deployment

Works with any WSGI server:
```bash
pip install gunicorn
gunicorn app:app -b 0.0.0.0:5000
```
