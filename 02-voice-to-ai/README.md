# Voice-to-AI

Interactive AI chat with optional voice output. Uses Ollama (llama3.2) for AI responses and macOS `say` command for text-to-speech.

## Features

- **Interactive Chat**: Type or paste questions, get AI-powered answers
- **Voice Output**: AI responses spoken aloud via macOS TTS (--speak flag)
- **Audio Recording**: Record from microphone using sox (optional)
- **Speech-to-Text**: Whisper transcription support (optional)
- **Streaming**: Responses stream in real-time
- **Conversation Memory**: Maintains context across messages (last 20)
- **Multiple Models**: Switch between Ollama models mid-conversation

## Prerequisites

- macOS (uses `say` command for TTS)
- Python 3.9+ (via venv at `~/Downloads/AI/.venv`)
- Ollama running at `localhost:11434` with `llama3.2` model

## Installation

```bash
# Install sox for audio recording (optional)
./install.sh

# Or manually:
brew install sox
```

## Usage

```bash
# Basic text chat
./voice_ai.py

# Chat with voice output
./voice_ai.py --speak

# Use a different model
./voice_ai.py --model llama3.2 --speak

# Change TTS voice
./voice_ai.py --speak --voice "Alex"
```

## In-Chat Commands

| Command | Description |
|---------|-------------|
| `/speak` | Toggle voice output on/off |
| `/record [seconds]` | Record audio from microphone |
| `/model NAME` | Switch Ollama model |
| `/clear` | Clear conversation history |
| `/help` | Show help |
| `/quit` | Exit |

## How It Works

1. You type a question or paste text
2. The query is sent to Ollama's chat API with conversation context
3. Response streams back in real-time
4. If `--speak` is enabled, the response is spoken via macOS `say`
5. Optional: Record audio → transcribe with Whisper → send as chat input

## Adding Whisper (Speech-to-Text)

To enable speech-to-text transcription:

```bash
# Install Whisper
~/Downloads/AI/.venv/bin/pip install openai-whisper

# You may also need ffmpeg
brew install ffmpeg
```

Once installed, use `/record` in the chat to:
1. Record audio from your microphone
2. Automatically transcribe it with Whisper
3. Send the transcription as your chat input

## Available macOS Voices

List available voices:
```bash
say -v '?'
```

Popular voices: Samantha (default), Alex, Daniel, Karen, Moira, Tessa

## Files

- `voice_ai.py` - Main interactive chat script
- `install.sh` - Dependency installer
- `.chat_history` - Input history for readline (auto-created)
- `recording.wav` - Temporary audio recording file
