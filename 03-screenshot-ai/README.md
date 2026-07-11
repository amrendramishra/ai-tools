# Screenshot AI

Capture and analyze screenshots using Ollama's **llava** multimodal model on macOS.

## Features

- **Capture**: Take screenshots (full screen, selection, or window)
- **Analyze**: Extract text and describe screenshot content using AI vision
- **Explain**: Get an explanation of what's happening on screen
- **OCR Fallback**: Use macOS native VisionKit OCR (no Ollama needed)

## Prerequisites

- macOS (uses `screencapture` command)
- [Ollama](https://ollama.ai) running on localhost:11434
- llava model pulled: `./pull_model.sh`

## Setup

```bash
# Pull the llava vision model
./pull_model.sh

# Or manually:
ollama pull llava
```

## Usage

```bash
# Take a full screen screenshot
./screenshot_ai.py --capture

# Take screenshot with interactive selection
./screenshot_ai.py --capture --mode selection

# Capture a specific window
./screenshot_ai.py --capture --mode window

# Analyze the last screenshot
./screenshot_ai.py --analyze

# Explain what's on screen
./screenshot_ai.py --explain

# Capture and immediately analyze
./screenshot_ai.py --capture --analyze

# Analyze a specific image file
./screenshot_ai.py --analyze --image /path/to/image.png

# Use macOS native OCR (no Ollama required)
./screenshot_ai.py --capture --ocr
```

## How It Works

1. Uses macOS `screencapture` to take screenshots
2. Converts the image to base64
3. Sends to Ollama's llava model via `/api/generate`
4. Displays the AI's analysis/explanation

Screenshots are stored in `./captures/` with timestamps.
