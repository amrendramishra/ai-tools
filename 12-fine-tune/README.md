# Fine-Tune Setup

A complete toolkit for fine-tuning and customizing LLMs on Apple Silicon Macs. Includes data preparation, method guides, and Ollama model creation tools.

## Overview

This project provides three approaches to customizing LLM behavior:

1. **Ollama Modelfile** (Easiest) - Custom persona via system prompts
2. **MLX Fine-Tuning** (Recommended) - Native Apple Silicon LoRA training
3. **LoRA Advanced** (Most Flexible) - Full training pipeline with multiple frameworks

## Files

| File | Purpose |
|------|---------|
| `prepare_data.py` | Scan files and create JSONL training data |
| `finetune_guide.py` | Interactive guide and Modelfile creator |
| `Modelfile.template` | Template for Ollama custom models |

## Quick Start

### 1. Create a Custom Ollama Model (No Training)

```bash
# Interactive wizard
./finetune_guide.py --create-modelfile

# Or generate non-interactively
./finetune_guide.py --generate-modelfile my-assistant \
  --base-model llama3.2 \
  --system-prompt "You are a Python expert who writes clean code." \
  --temperature 0.3

# Test it
./finetune_guide.py --test my-assistant
```

### 2. Prepare Training Data

```bash
# From documents
./prepare_data.py --input ~/Documents/notes --source documents

# From chat histories
./prepare_data.py --input ~/chats --source chat_history

# From code repos
./prepare_data.py --input ~/projects/my-app --source code

# Output is saved to data/training.jsonl
```

### 3. Fine-Tune with MLX (Apple Silicon)

```bash
# Read the guide
./finetune_guide.py --method mlx

# Install MLX
pip install mlx mlx-lm

# Convert model
python -m mlx_lm.convert --hf-path mistralai/Mistral-7B-v0.1 --mlx-path ./mlx-model

# Train
python -m mlx_lm.lora \
  --model ./mlx-model \
  --data ./data \
  --train \
  --batch-size 4 \
  --lora-layers 16 \
  --iters 1000
```

## Data Preparation

The `prepare_data.py` tool supports multiple source types:

### Source Types

| Source | Best For | Extraction Method |
|--------|----------|-------------------|
| `chat_history` | Conversation logs | Extracts Q&A pairs |
| `documents` | Markdown, text files | Creates summary/explanation pairs |
| `code` | Source code | Extracts functions with docstrings |
| `custom` | Everything else | Generic text chunking |

### Output Format (Alpaca/Stanford)

```json
{"instruction": "Explain what this function does", "input": "def add(a, b): return a + b", "output": "This function takes two parameters..."}
```

### Data Quality Tips

- **Quality > Quantity**: 500 excellent pairs beat 5000 mediocre ones
- **Consistency**: Keep instruction style consistent
- **Diversity**: Cover different aspects of desired behavior
- **Length**: Aim for 100-500 token responses
- **Deduplication**: The tool handles this automatically

## Fine-Tuning Methods Comparison

| Feature | Ollama Modelfile | MLX LoRA | Full LoRA |
|---------|-----------------|----------|-----------|
| Difficulty | Easy | Medium | Hard |
| Training Time | None | 1-2 hours | 2-4 hours |
| RAM Needed | Model only | 16-32GB | 32-64GB |
| Customization | Behavior only | Weights | Full |
| Quality | Good | Very Good | Best |
| Apple Silicon | ✅ | ✅ Native | ✅ via MLX |

## Hardware Requirements

| Model Size | Min RAM | Recommended | Training Time |
|-----------|---------|-------------|---------------|
| 1B-3B | 8GB | 16GB | 15-30 min |
| 7B | 16GB | 32GB | 1-2 hours |
| 13B | 32GB | 64GB | 3-5 hours |
| 70B | 64GB+ | 128GB | Not practical |

## Workflow Recommendation

```
┌─────────────────────────────────────────────────┐
│  Start Here                                      │
│  ↓                                              │
│  Try Ollama Modelfile (instant, no training)     │
│  ↓                                              │
│  Good enough? → Done!                            │
│  ↓ No                                           │
│  Prepare data with prepare_data.py               │
│  ↓                                              │
│  Fine-tune with MLX LoRA                         │
│  ↓                                              │
│  Convert & import to Ollama                      │
│  ↓                                              │
│  Test & iterate                                  │
└─────────────────────────────────────────────────┘
```

## Environment Variables

- `OLLAMA_BASE_URL`: Override Ollama endpoint (default: http://localhost:11434)
