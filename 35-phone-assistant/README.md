# 📞 AI Phone Call Assistant (Project 35)

A practical macOS phone/call assistant that records, transcribes, classifies, and manages audio messages using local AI.

## Features

- **Audio Recording**: Capture from Mac microphone (sox or ffmpeg)
- **Transcription**: Convert audio to text using Whisper
- **AI Classification**: Urgency level, spam detection, action items
- **Voicemail Mode**: Full pipeline (record → transcribe → classify → notify)
- **Meeting Recorder**: Live recording with chunked transcription and summary
- **macOS Notifications**: Alert for urgent messages
- **SQLite Storage**: All calls/messages stored and searchable

## Architecture

```
phone_assistant.py  → Main executable (CLI interface)
call_log.py         → Database module (SQLite-backed)
recordings/         → Auto-created directory for audio files
calls.db            → Auto-created database
```

## Usage

```bash
# Record from microphone (default 10 seconds)
./phone_assistant.py --listen
./phone_assistant.py --listen --duration 30

# Transcribe a recording
./phone_assistant.py --transcribe recordings/recording_20240101_120000.wav

# Generate AI response to a message
./phone_assistant.py --respond recordings/recording_20240101_120000.wav

# Full voicemail mode (record → transcribe → classify → notify)
./phone_assistant.py --voicemail
./phone_assistant.py --voicemail --duration 60

# Record a live meeting with real-time notes
./phone_assistant.py --meeting-recorder
./phone_assistant.py --meeting-recorder --title "Team Standup"

# Play back a recording with AI summary
./phone_assistant.py --playback recordings/voicemail_20240101_120000.wav

# View history
./phone_assistant.py --history

# Filter messages
./phone_assistant.py --filter urgent
./phone_assistant.py --filter spam
./phone_assistant.py --filter missed
./phone_assistant.py --filter action
```

## AI Classification

Every message is automatically classified with:

| Field | Description |
|-------|-------------|
| Urgency | low, normal, high, urgent |
| Spam | Whether it's likely spam/robocall |
| Action Needed | What action should be taken |
| Summary | One-line summary |
| Classification | Category (business, personal, medical, etc.) |

## Requirements

- Python 3.10+
- Ollama running locally (localhost:11434)
- `requests` library
- **Audio recording** (one of):
  - `sox` - recommended: `brew install sox`
  - `ffmpeg` - alternative: `brew install ffmpeg`
- **Transcription** (optional but recommended):
  - `openai-whisper`: `pip install openai-whisper`

## macOS Notifications

Urgent messages trigger macOS notifications automatically. The assistant uses:
- 🔴 Urgent: "Basso" alert sound
- 🟠 High: Standard notification
- 🟢 Normal: Silent notification
- ⚪ Low/Spam: No notification

## Database Schema

**calls**: All recorded messages with transcription, classification, and metadata
**meetings**: Meeting recordings with full transcription and summaries
**meeting_chunks**: Real-time transcription chunks during meetings
**notifications**: History of sent notifications

## Tips

- Install `sox` for the best recording experience: `brew install sox`
- Install `whisper` for accurate transcription: `pip install openai-whisper`
- Use `--voicemail` for the complete automated pipeline
- Check `--filter urgent` regularly for important messages
- Meeting recorder works great for video calls (captures system audio)
