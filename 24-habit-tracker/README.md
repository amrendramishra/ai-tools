# AI Habit Tracker

Track your daily and weekly habits with AI-powered coaching, reports, and suggestions.

## Features

- **Habit Management**: Add daily/weekly habits with goals
- **Streak Tracking**: Visual streak display with fire indicators
- **AI Coach**: Personalized motivation based on your patterns
- **AI Reports**: Weekly/monthly progress summaries
- **AI Suggestions**: Smart recommendations for new habits
- **Mood Tracking**: Attach notes and mood to log entries
- **Color-Coded Output**: Streaks and completion rates visualized in terminal

## Requirements

- Python 3.8+
- Ollama running at localhost:11434 (model: llama3.2)
- `requests` library

## Usage

```bash
# Add habits
./habit_tracker.py --add 'Morning meditation' --frequency daily
./habit_tracker.py --add 'Exercise' --frequency daily --goal 'Stay fit'
./habit_tracker.py --add 'Read a book' --frequency weekly

# Log completed habits
./habit_tracker.py --log 'Morning meditation'
./habit_tracker.py --log 'Exercise' --note 'Ran 5km' --mood 'energized'

# View status
./habit_tracker.py --status       # Today's habits (done/pending)
./habit_tracker.py --streak       # Current streaks
./habit_tracker.py --stats        # Detailed statistics

# AI features
./habit_tracker.py --coach        # Personalized motivation
./habit_tracker.py --report weekly   # AI weekly report
./habit_tracker.py --report monthly  # AI monthly report
./habit_tracker.py --suggest      # AI habit suggestions
```

## Data Storage

All data stored in `~/.habit_tracker.db` (SQLite).

## Status Display

- ✓ Green: Completed today
- ○ Red: Pending
- 🔥 Streaks ≥ 7 days
- ⭐ Streaks ≥ 3 days
- Progress bar with completion percentage
