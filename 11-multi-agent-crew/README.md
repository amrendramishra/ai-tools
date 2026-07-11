# Multi-Agent Crew

A from-scratch multi-agent pipeline system that orchestrates AI agents through configurable workflows to produce polished content.

## Overview

This system defines specialized AI agents (Researcher, Writer, Editor, Reviewer, Publisher) that work together in a pipeline. Each agent processes the output of the previous one, progressively refining content from raw research to publication-ready material.

## Architecture

```
Topic → [Researcher] → [Writer] → [Editor] → [Reviewer] → [Publisher] → Output
           │               │           │            │             │
           ▼               ▼           ▼            ▼             ▼
       Research         Draft      Improved      Scored       Formatted
        Brief          Content     Content       Review       Output
```

## Requirements

- Python 3.10+
- Ollama running locally (default: localhost:11434)
- A model pulled in Ollama (default: llama3.2)

## Setup

```bash
# Ensure Ollama is running
ollama serve

# Pull the default model
ollama pull llama3.2

# Run the pipeline
./crew.py --topic "Your Topic Here"
```

## Usage

```bash
# Run full pipeline with default (blog) pipeline
./crew.py --topic "AI in Healthcare"

# Use a specific pipeline
./crew.py --topic "Python Best Practices" --pipeline video_script

# Specify output format
./crew.py --topic "Climate Change" --output json

# List available agents
./crew.py --agents

# Show pipeline steps
./crew.py --steps --pipeline research

# Use custom agent configurations
./crew.py --topic "My Topic" --agents-file custom_agents.json
```

## Pipelines

| Pipeline | Description | Steps |
|----------|-------------|-------|
| blog | Blog post creation | Researcher → Writer → Editor → Reviewer → Publisher |
| video_script | Video script with cues | Researcher → Writer → Editor → Publisher |
| research | Academic research report | Researcher → Editor → Reviewer → Publisher |
| social_media | Multi-platform social content | Researcher → Writer → Publisher |

## Configuration

### agents.json

Define custom agents with:
- `name`: Display name
- `role`: Role identifier (used in pipeline steps)
- `model`: Ollama model to use
- `system_prompt`: Agent's instructions
- `temperature`: Creativity level (0.0-1.0)
- `max_tokens`: Maximum response length

### pipelines.json

Define custom pipelines with:
- `name`: Display name
- `steps`: Ordered list of agent roles
- `output_format`: Default output format (markdown/json)
- `context`: Additional context for all agents

## Output

Results are saved to the `output/` directory with filenames like:
```
blog_ai-in-healthcare_20240115_143022.md
```

## Environment Variables

- `OLLAMA_BASE_URL`: Override Ollama endpoint (default: http://localhost:11434)
