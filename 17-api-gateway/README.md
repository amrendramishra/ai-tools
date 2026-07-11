# Project 17: AI API Gateway

A unified OpenAI-compatible API gateway that routes requests to local Ollama models.

## Features

- **OpenAI-compatible API** - Drop-in replacement for OpenAI's API
- **Smart routing** - Auto-selects the best model based on task type
- **Streaming support** - SSE streaming for chat completions
- **Rate limiting** - In-memory per-key rate limiting
- **API key auth** - Configurable API key authentication
- **Request logging** - All requests logged to gateway.log
- **Image analysis** - Routes to llava for vision tasks
- **Embeddings** - Supports embedding generation

## Quick Start

```bash
./gateway.py
```

The gateway runs on port 8080 by default.

## Configuration

Edit `config.json` to customize:

```json
{
  "port": 8080,
  "ollama_base": "http://localhost:11434",
  "api_keys": ["sk-local-dev-key"],
  "rate_limit": {"requests_per_minute": 60},
  "routes": {
    "code": "codellama",
    "general": "llama3.2",
    "fast": "phi3",
    "reasoning": "gemma2",
    "vision": "llava"
  }
}
```

## API Endpoints

### Chat Completions (OpenAI-compatible)
```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-local-dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

### Smart Routing
```bash
curl http://localhost:8080/route \
  -H "Authorization: Bearer sk-local-dev-key" \
  -H "Content-Type: application/json" \
  -d '{"task": "Write a Python function to sort a list"}'
```

Routes automatically:
- Code questions → codellama
- General chat → llama3.2
- Fast/simple → phi3
- Complex reasoning → gemma2

### Embeddings
```bash
curl http://localhost:8080/v1/embeddings \
  -H "Authorization: Bearer sk-local-dev-key" \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic-embed-text", "input": "Hello world"}'
```

### Image Analysis
```bash
curl http://localhost:8080/v1/images/analyze \
  -H "Authorization: Bearer sk-local-dev-key" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is in this image?", "images": ["<base64>"]}'
```

### List Models
```bash
curl http://localhost:8080/v1/models
```

### Health Check
```bash
curl http://localhost:8080/health
```

## Authentication

Include the API key in the Authorization header:
```
Authorization: Bearer sk-local-dev-key
```

Default keys are in `config.json`. The `/health` and `/v1/models` endpoints don't require auth.

## Rate Limiting

Default: 60 requests per minute per API key. Returns 429 with `Retry-After` header when exceeded.

## Requirements

- Python 3.x (stdlib only)
- Ollama running on localhost:11434
