# 🍅 Focus Mode AI

AI-powered Pomodoro timer and productivity coach. Tracks focus sessions in SQLite, blocks distracting apps, and uses Ollama for intelligent suggestions and reports.

## Features

- **Pomodoro Timer**: 25, 50, and 90-minute session presets with visual countdown
- **Break Timer**: 5 and 15-minute break presets
- **App Blocking**: Kills distracting apps during focus sessions (macOS `killall`)
- **Session Tracking**: All sessions stored in SQLite with completion status
- **AI Suggestions**: Get recommendations on what to work on based on time of day and history
- **AI Productivity Tips**: Receives motivational and actionable tips between sessions
- **Statistics**: Daily and weekly focus statistics with progress bars
- **Reports**: Detailed daily/weekly reports with AI-powered insights
- **macOS Notifications**: Sound alerts for session start, midpoint, and completion
- **Goal Tracking**: Set daily/weekly focus goals and track progress

## Requirements

- Python 3.8+
- Ollama running at `localhost:11434` (for AI features)
- macOS (for notifications and app blocking)

## Installation

```bash
# Activate the virtual environment
source ~/Downloads/AI/.venv/bin/activate

# Dependencies (already in venv)
pip install requests
```

## Usage

### Start a Focus Session
```bash
# Standard Pomodoro (25 min)
./focus_mode.py --start 25

# Deep Work (50 min)
./focus_mode.py --start 50

# Flow State (90 min)
./focus_mode.py --start 90
```

### Take a Break
```bash
# Short break (5 min)
./focus_mode.py --break

# Long break (15 min)
./focus_mode.py --break 15
```

### Check Status & Stats
```bash
# Current session status
./focus_mode.py --status

# Today/week statistics
./focus_mode.py --stats
```

### AI Features
```bash
# Get AI suggestion on what to work on
./focus_mode.py --suggest

# Generate daily report with AI insights
./focus_mode.py --report

# Generate weekly report
./focus_mode.py --report weekly
```

### App Blocking
```bash
# Block distracting apps
./focus_mode.py --block

# Unblock apps
./focus_mode.py --unblock
```

## Configuration

Edit `config.json` to customize:

```json
{
  "blocked_apps": ["Twitter", "Reddit", "YouTube", ...],
  "goals": {
    "daily_focus_minutes": 180,
    "daily_sessions": 6,
    "weekly_focus_hours": 20
  }
}
```

### Blocked Apps
Add or remove apps from the `blocked_apps` list. These will be killed using `killall` when a focus session starts or when `--block` is used.

### Goals
- `daily_focus_minutes`: Target minutes per day (default: 180 = 3 hours)
- `daily_sessions`: Target number of sessions per day (default: 6)
- `weekly_focus_hours`: Target hours per week (default: 20)

## How It Works

1. **Start Session**: Begins a countdown timer, blocks apps, shows AI tip
2. **During Session**: Visual progress bar updates every second, midpoint notification
3. **Session Complete**: macOS notification with sound, AI encouragement, stats update
4. **Between Sessions**: AI suggests break or next session based on your history
5. **Reports**: Daily/weekly summaries with AI-analyzed productivity patterns

## Files

- `focus_mode.py` - Main executable script
- `config.json` - Configuration (blocked apps, goals, presets)
- `focus_sessions.db` - SQLite database (auto-created)
- `README.md` - This file

## Timer Display

```
🍅 Pomodoro (25 min)
   Started at: 14:30:00
   Ends at:    14:55:00

   💡 Start with your most challenging task while your energy is fresh.

   [████████████░░░░░░░░░░░░░░░░░░] 12:34 remaining
```
