# 🎵 AI DJ — Intelligent Music Mood Selector

An AI-powered music mood selector that recommends songs and playlists based on your mood, time of day, and preferences.

## Features

- **Mood-based selection**: Happy, Focus, Chill, Energetic, Sad, Romantic, Party
- **Time-aware AI**: Automatically suggests music based on time of day
- **Genre filtering**: Lofi, Bollywood, Pop, Classical, Hip-Hop, Ambient
- **Quick modes**: Work focus, Wake-up energy, Sleep calm
- **Platform integration**: Opens Spotify or YouTube Music with AI-crafted searches
- **Playlist generation**: AI creates 30-song playlists for any mood
- **History tracking**: SQLite database remembers your preferences

## Time-Based Suggestions

| Time | Period | Mood |
|------|--------|------|
| 6-9 AM | Morning | Energetic/Motivational |
| 9-5 PM | Work | Focus/Lofi/Ambient |
| 5-9 PM | Evening | Chill/Bollywood |
| 9 PM+ | Night | Calm/Sleep |

## Usage

```bash
# AI picks your mood
./ai_dj.py --auto

# Set specific mood
./ai_dj.py --mood happy
./ai_dj.py --mood chill --genre lofi

# Quick modes
./ai_dj.py --work          # Focus music (no lyrics)
./ai_dj.py --wake-up       # Morning energy
./ai_dj.py --sleep         # Calming sleep music

# AI recommendations
./ai_dj.py --recommend
./ai_dj.py --recommend --mood romantic --genre bollywood

# Current status
./ai_dj.py --now-playing

# Open music platforms
./ai_dj.py --spotify "lofi beats study"
./ai_dj.py --youtube-music "bollywood chill"

# Create playlist
./ai_dj.py --create-playlist "Weekend Vibes" party
```

## Moods

| Mood | Energy | BPM | Genres |
|------|--------|-----|--------|
| Happy | 80% | 110-140 | Pop, Bollywood, Dance |
| Focus | 30% | 60-90 | Lofi, Ambient, Classical |
| Chill | 40% | 70-100 | Lofi, Indie, Jazz |
| Energetic | 95% | 128-160 | Hip-Hop, EDM, Rock |
| Sad | 20% | 50-80 | Indie, Acoustic, Classical |
| Romantic | 40% | 60-100 | Bollywood, R&B, Jazz |
| Party | 100% | 120-150 | EDM, Bollywood, Dance |

## Requirements

- Python 3.8+
- Ollama running locally (for AI features)

## Files

- `ai_dj.py` — Main executable
- `moods.json` — Mood definitions with genres, BPM, energy levels
- `playlists.json` — Pre-curated playlist suggestions
- `dj_history.db` — SQLite database (auto-created)
