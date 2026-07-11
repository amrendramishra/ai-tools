#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""AI DJ - Intelligent Music Mood Selector powered by Ollama."""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / "dj_history.db"
MOODS_FILE = SCRIPT_DIR / "moods.json"
PLAYLISTS_FILE = SCRIPT_DIR / "playlists.json"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


def init_db():
    """Initialize SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            mood TEXT,
            genre TEXT,
            action TEXT,
            details TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mood TEXT,
            created_at TEXT,
            songs TEXT
        )
    """)
    conn.commit()
    return conn


def log_action(conn, mood=None, genre=None, action="", details=""):
    """Log an action to history."""
    c = conn.cursor()
    c.execute(
        "INSERT INTO history (timestamp, mood, genre, action, details) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), mood, genre, action, details)
    )
    conn.commit()


def load_moods():
    """Load mood definitions."""
    with open(MOODS_FILE) as f:
        return json.load(f)


def load_playlists():
    """Load playlist data."""
    with open(PLAYLISTS_FILE) as f:
        return json.load(f)


def ask_ollama(prompt, model="llama3.2"):
    """Query Ollama for AI responses."""
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.8, "num_predict": 1024}
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response", "").strip()
    except Exception as e:
        return f"[Ollama error: {e}]"


def get_time_period():
    """Get current time period."""
    hour = datetime.now().hour
    if 6 <= hour < 9:
        return "morning"
    elif 9 <= hour < 17:
        return "work"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def get_time_mood():
    """Get suggested mood based on time."""
    moods_data = load_moods()
    period = get_time_period()
    time_info = moods_data["time_moods"].get(period, {})
    return time_info.get("moods", ["chill"])[0], period, time_info.get("description", "")


def display_mood_info(mood, genre=None):
    """Display mood information with songs."""
    moods_data = load_moods()
    playlists_data = load_playlists()

    mood_info = moods_data["moods"].get(mood)
    if not mood_info:
        print(f"❌ Unknown mood: {mood}")
        print(f"Available moods: {', '.join(moods_data['moods'].keys())}")
        return

    print(f"\n🎵 DJ Mode: {mood.upper()}")
    print(f"{'═' * 50}")
    print(f"📝 {mood_info['description']}")
    print(f"🎚️  Energy: {'█' * int(mood_info['energy_level'] * 10)}{'░' * (10 - int(mood_info['energy_level'] * 10))} {mood_info['energy_level']:.0%}")
    print(f"💓 Valence: {'█' * int(mood_info['valence'] * 10)}{'░' * (10 - int(mood_info['valence'] * 10))} {mood_info['valence']:.0%}")
    print(f"🥁 BPM: {mood_info['bpm_range'][0]}-{mood_info['bpm_range'][1]}")
    print(f"🎸 Genres: {', '.join(mood_info['genres'])}")
    print(f"🏷️  Keywords: {', '.join(mood_info['keywords'])}")

    # Find matching playlist
    for name, playlist in playlists_data["playlists"].items():
        if playlist["mood"] == mood:
            songs = playlist["songs"]
            if genre:
                songs = [s for s in songs if s.get("genre") == genre]
            if songs:
                print(f"\n🎶 Suggested Songs ({playlist['description']}):")
                print(f"{'─' * 40}")
                for i, song in enumerate(songs[:10], 1):
                    print(f"  {i:2}. {song['title']} — {song['artist']} [{song['genre']}]")
            break

    print()


def auto_mode(conn):
    """AI picks mood based on time and recent activity."""
    mood, period, desc = get_time_mood()

    # Check recent history for context
    c = conn.cursor()
    c.execute("SELECT mood, action FROM history ORDER BY timestamp DESC LIMIT 5")
    recent = c.fetchall()
    recent_moods = [r[0] for r in recent if r[0]]

    prompt = f"""You are an AI DJ. Current time period: {period} ({desc}).
Recent user moods: {recent_moods if recent_moods else 'No history yet'}.
Current hour: {datetime.now().hour}:00.
Day: {datetime.now().strftime('%A')}.

Suggest the perfect mood for right now. Choose from: happy, focus, chill, energetic, sad, romantic, party.
Give a brief 1-2 sentence explanation of why this mood fits.
Format: MOOD: <mood>
REASON: <reason>"""

    print("🤖 AI DJ analyzing your vibe...")
    response = ask_ollama(prompt)
    print(f"\n{response}")

    # Extract mood from response
    for line in response.split('\n'):
        if 'MOOD:' in line.upper():
            suggested = line.split(':')[-1].strip().lower()
            if suggested in load_moods()["moods"]:
                mood = suggested
                break

    print()
    display_mood_info(mood)
    log_action(conn, mood=mood, action="auto", details=f"period={period}")


def recommend_mode(conn, mood=None, genre=None):
    """AI recommends songs/playlists."""
    if not mood:
        mood, _, _ = get_time_mood()

    moods_data = load_moods()
    mood_info = moods_data["moods"].get(mood, {})

    prompt = f"""You are an AI DJ recommending music. The user wants: {mood} mood.
Genre preference: {genre or 'any'}.
Mood details: {mood_info.get('description', '')}.
BPM range: {mood_info.get('bpm_range', [80, 120])}.
Energy level: {mood_info.get('energy_level', 0.5)}.

Recommend 10 songs that perfectly match this mood. Mix of Bollywood and international.
Format each as: NUMBER. SONG_TITLE - ARTIST [GENRE]
Add a brief DJ intro at the top."""

    print(f"🎧 AI DJ recommending {mood} tracks{f' ({genre})' if genre else ''}...\n")
    response = ask_ollama(prompt)
    print(response)
    log_action(conn, mood=mood, genre=genre, action="recommend")


def now_playing(conn):
    """Show current suggestion based on context."""
    mood, period, desc = get_time_mood()
    playlists_data = load_playlists()

    print(f"🎵 Now Playing Mode — {period.title()} Vibes")
    print(f"{'═' * 50}")
    print(f"⏰ Time: {datetime.now().strftime('%H:%M')} | Period: {period}")
    print(f"🎭 Suggested mood: {mood}")
    print(f"📝 {desc}")
    print()

    for name, playlist in playlists_data["playlists"].items():
        if playlist["mood"] == mood and playlist.get("time") == period:
            print(f"📀 Playlist: {playlist['description']}")
            print(f"{'─' * 40}")
            for i, song in enumerate(playlist["songs"][:5], 1):
                marker = "▶️ " if i == 1 else "  "
                print(f"  {marker}{i}. {song['title']} — {song['artist']}")
            print(f"\n  ... and {len(playlist['songs']) - 5} more tracks")
            break

    log_action(conn, mood=mood, action="now_playing")


def work_mode(conn):
    """Optimal focus music."""
    print("💻 WORK MODE — Focus & Productivity")
    print(f"{'═' * 50}")
    print("🎧 No lyrics | Lofi/Ambient | Steady BPM\n")
    display_mood_info("focus")

    prompt = """Suggest 5 focus music techniques for maximum productivity:
1. Type of music (lofi, ambient, classical)
2. Ideal BPM range
3. Why it helps concentration
Keep it brief and actionable."""

    print("🧠 AI Focus Tips:")
    print(f"{'─' * 30}")
    response = ask_ollama(prompt)
    print(response)
    log_action(conn, mood="focus", genre="lofi/ambient", action="work_mode")


def wake_up_mode(conn):
    """Energetic morning playlist."""
    print("☀️ WAKE UP MODE — Rise & Shine!")
    print(f"{'═' * 50}")
    display_mood_info("energetic")
    log_action(conn, mood="energetic", action="wake_up")


def sleep_mode(conn):
    """Calming sleep music."""
    print("🌙 SLEEP MODE — Peaceful Dreams")
    print(f"{'═' * 50}")
    print("🎵 Ambient | Classical | Nature | 50-70 BPM\n")

    playlists_data = load_playlists()
    playlist = playlists_data["playlists"].get("sleep_mode", {})
    if playlist:
        print(f"📀 {playlist['description']}:")
        print(f"{'─' * 40}")
        for i, song in enumerate(playlist["songs"], 1):
            print(f"  {i:2}. {song['title']} — {song['artist']}")

    print("\n💤 Sweet dreams! Music will gradually fade...")
    log_action(conn, mood="chill", action="sleep_mode")


def open_spotify(query, conn):
    """Open Spotify search."""
    if not query:
        mood, _, _ = get_time_mood()
        query = f"{mood} music playlist"

    # AI enhance the query
    prompt = f"Generate a perfect Spotify search query for: {query}. Just the search query, nothing else. Make it specific and likely to find good results."
    enhanced = ask_ollama(prompt)
    search_query = enhanced.strip().strip('"').strip("'") if enhanced and "[" not in enhanced else query

    url = f"https://open.spotify.com/search/{urllib.parse.quote(search_query)}"
    print(f"🎵 Opening Spotify: {search_query}")
    print(f"🔗 {url}")
    webbrowser.open(url)
    log_action(conn, action="spotify", details=search_query)


def open_youtube_music(query, conn):
    """Open YouTube Music search."""
    if not query:
        mood, _, _ = get_time_mood()
        query = f"{mood} music mix"

    url = f"https://music.youtube.com/search?q={urllib.parse.quote(query)}"
    print(f"🎵 Opening YouTube Music: {query}")
    print(f"🔗 {url}")
    webbrowser.open(url)
    log_action(conn, action="youtube_music", details=query)


def create_playlist(name, mood, conn):
    """Generate a playlist concept with 30 songs."""
    moods_data = load_moods()
    mood_info = moods_data["moods"].get(mood, {})

    prompt = f"""Create a playlist called "{name}" with exactly 30 songs for the "{mood}" mood.
Mood details: {mood_info.get('description', mood)}
Genres: {mood_info.get('genres', ['various'])}
Energy: {mood_info.get('energy_level', 0.5)}

Mix of Bollywood (40%) and international (60%) songs.
Format each as: NUMBER. SONG_TITLE - ARTIST [GENRE]
Group them into sections (Opening, Building, Peak, Cool Down) for good flow."""

    print(f"🎨 Creating playlist: '{name}' ({mood} mood)")
    print(f"{'═' * 50}")
    response = ask_ollama(prompt)
    print(response)

    # Save to database
    c = conn.cursor()
    c.execute(
        "INSERT INTO playlists (name, mood, created_at, songs) VALUES (?, ?, ?, ?)",
        (name, mood, datetime.now().isoformat(), response)
    )
    conn.commit()
    print(f"\n✅ Playlist '{name}' saved! ({c.lastrowid})")
    log_action(conn, mood=mood, action="create_playlist", details=name)


def main():
    parser = argparse.ArgumentParser(
        description="🎵 AI DJ — Intelligent Music Mood Selector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ai_dj.py --mood happy              Set happy mood
  ai_dj.py --auto                    AI picks mood for you
  ai_dj.py --mood chill --genre lofi Chill lofi vibes
  ai_dj.py --work                    Focus mode for productivity
  ai_dj.py --spotify "lofi beats"    Open Spotify search
  ai_dj.py --create-playlist "Vibe" party  Generate party playlist
        """
    )

    parser.add_argument("--mood", choices=["happy", "focus", "chill", "energetic", "sad", "romantic", "party"],
                        help="Set music mood")
    parser.add_argument("--auto", action="store_true", help="AI picks mood based on time/activity")
    parser.add_argument("--recommend", action="store_true", help="AI recommends songs")
    parser.add_argument("--now-playing", action="store_true", help="Show current suggestion")
    parser.add_argument("--genre", choices=["lofi", "bollywood", "pop", "classical", "hip-hop", "ambient"],
                        help="Filter by genre")
    parser.add_argument("--work", action="store_true", help="Focus music mode")
    parser.add_argument("--wake-up", action="store_true", help="Energetic morning music")
    parser.add_argument("--sleep", action="store_true", help="Calming sleep music")
    parser.add_argument("--spotify", nargs="?", const="", help="Open Spotify search")
    parser.add_argument("--youtube-music", nargs="?", const="", help="Open YouTube Music search")
    parser.add_argument("--create-playlist", nargs=2, metavar=("NAME", "MOOD"),
                        help="Generate playlist (name mood)")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        print("\n🎵 Quick: Use --auto for AI-powered mood selection!")
        return

    conn = init_db()

    try:
        if args.auto:
            auto_mode(conn)
        elif args.work:
            work_mode(conn)
        elif args.wake_up:
            wake_up_mode(conn)
        elif args.sleep:
            sleep_mode(conn)
        elif args.now_playing:
            now_playing(conn)
        elif args.recommend:
            recommend_mode(conn, mood=args.mood, genre=args.genre)
        elif args.mood:
            display_mood_info(args.mood, genre=args.genre)
            log_action(conn, mood=args.mood, genre=args.genre, action="mood_select")
        elif args.spotify is not None:
            open_spotify(args.spotify, conn)
        elif args.youtube_music is not None:
            open_youtube_music(args.youtube_music, conn)
        elif args.create_playlist:
            name, mood = args.create_playlist
            if mood not in ["happy", "focus", "chill", "energetic", "sad", "romantic", "party"]:
                print(f"❌ Invalid mood: {mood}")
                print("Valid moods: happy, focus, chill, energetic, sad, romantic, party")
                return
            create_playlist(name, mood, conn)
        elif args.genre:
            # Just show genre info
            moods_data = load_moods()
            genre_info = moods_data["genres"].get(args.genre)
            if genre_info:
                print(f"\n🎸 Genre: {args.genre.upper()}")
                print(f"📝 {genre_info['description']}")
                print(f"🥁 Typical BPM: {genre_info['typical_bpm'][0]}-{genre_info['typical_bpm'][1]}")
                print(f"🎭 Best for moods: {', '.join(genre_info['mood_affinity'])}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
