# 🌙 AI Dream Journal — Record & Analyze Your Dreams

An AI-powered dream journal that records, analyzes, and finds patterns in your dreams using local AI.

## Features

- **Record dreams**: Text input with AI-generated titles, moods, and symbol detection
- **Deep analysis**: Jungian + modern psychology dream interpretation
- **Pattern detection**: Find recurring symbols, themes, and mood trends
- **Search**: Find dreams by content, symbols, or themes
- **Statistics**: Track your dreaming patterns over time
- **Export**: Full markdown journal export
- **Lucid dreaming**: Personalized tips based on your dream patterns
- **Voice recording**: Microphone input with Whisper transcription (optional)

## Usage

```bash
# Record a new dream
./dream_journal.py --record

# Record via voice (requires whisper)
./dream_journal.py --record-voice

# List all dreams
./dream_journal.py --list

# Deep analysis of a specific dream
./dream_journal.py --analyze 3

# Find patterns across all dreams
./dream_journal.py --patterns

# Search dreams
./dream_journal.py --search "water"
./dream_journal.py --search "flying"

# View statistics
./dream_journal.py --stats

# Export journal
./dream_journal.py --export

# Lucid dreaming tips
./dream_journal.py --lucid-tips
```

## Dream Entry Structure

Each dream stores:
- Date & time of recording
- Raw dream text
- AI-generated title
- Detected mood (peaceful, anxious, joyful, etc.)
- Identified symbols
- Themes
- Analysis (when requested)

## Symbol Database

Contains 100+ dream symbols with interpretations, organized by categories:
- Nature (water, fire, mountains, etc.)
- Animals (snake, bird, cat, etc.)
- Places (house, school, temple, etc.)
- Objects (key, mirror, clock, etc.)
- Actions (flying, falling, swimming, etc.)
- People (stranger, teacher, child self, etc.)

## Tips for Better Dream Recall

1. Keep this journal by your bed
2. Record immediately upon waking
3. Don't move too much before recording
4. Write even fragments — AI can still analyze them
5. Note emotions first, then details

## Requirements

- Python 3.8+
- Ollama running locally (for AI analysis)
- SQLite (built-in with Python)

## Files

- `dream_journal.py` — Main executable
- `symbols.json` — 100+ dream symbol interpretations
- `dreams.db` — SQLite database (auto-created)
