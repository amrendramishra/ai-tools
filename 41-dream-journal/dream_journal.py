#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""AI Dream Journal — Record, analyze, and find patterns in your dreams."""

import argparse
import json
import os
import sqlite3
import sys
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / "dreams.db"
SYMBOLS_FILE = SCRIPT_DIR / "symbols.json"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


def init_db():
    """Initialize the dreams database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS dreams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            title TEXT,
            mood TEXT,
            symbols TEXT,
            themes TEXT,
            analysis TEXT,
            lucidity_level INTEGER DEFAULT 0,
            vividness INTEGER DEFAULT 5,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def ask_ollama(prompt, model="llama3.2"):
    """Query Ollama."""
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 1500}
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response", "").strip()
    except Exception as e:
        return f"[Ollama error: {e}]"


def load_symbols():
    """Load dream symbol interpretations."""
    with open(SYMBOLS_FILE) as f:
        return json.load(f)


def record_dream(conn, voice=False):
    """Record a new dream entry."""
    if voice:
        print("🎙️  Voice Recording Mode")
        print("This requires the 'whisper' model in Ollama or openai-whisper package.")
        print("Recording not available in terminal mode. Please type your dream instead.\n")

    print("🌙 Record Your Dream")
    print("═" * 50)
    print("Describe your dream in as much detail as you remember.")
    print("(Press Enter twice to finish)\n")

    lines = []
    empty_count = 0
    while True:
        try:
            line = input()
            if line == "":
                empty_count += 1
                if empty_count >= 2:
                    break
                lines.append("")
            else:
                empty_count = 0
                lines.append(line)
        except EOFError:
            break

    raw_text = "\n".join(lines).strip()
    if not raw_text:
        print("❌ No dream text entered.")
        return

    print("\n🤖 AI is analyzing your dream...")

    # AI generates title, mood, symbols, themes
    prompt = f"""Analyze this dream journal entry and provide:
1. TITLE: A short evocative title (3-6 words)
2. MOOD: The dominant emotional tone (one word: peaceful, anxious, joyful, confused, fearful, nostalgic, adventurous, melancholic, empowered, surreal)
3. SYMBOLS: Key symbols present (comma-separated list, max 8)
4. THEMES: Main themes (comma-separated list, max 5)

Dream text: "{raw_text}"

Format exactly as:
TITLE: ...
MOOD: ...
SYMBOLS: ...
THEMES: ..."""

    response = ask_ollama(prompt)

    # Parse response
    title = "Untitled Dream"
    mood = "unknown"
    symbols = ""
    themes = ""

    for line in response.split('\n'):
        line = line.strip()
        if line.upper().startswith('TITLE:'):
            title = line.split(':', 1)[1].strip()
        elif line.upper().startswith('MOOD:'):
            mood = line.split(':', 1)[1].strip().lower()
        elif line.upper().startswith('SYMBOLS:'):
            symbols = line.split(':', 1)[1].strip()
        elif line.upper().startswith('THEMES:'):
            themes = line.split(':', 1)[1].strip()

    # Ask for optional ratings
    print(f"\n📝 Title: {title}")
    print(f"🎭 Mood: {mood}")
    print(f"🔮 Symbols: {symbols}")
    print(f"📂 Themes: {themes}")

    # Save to database
    now = datetime.now()
    c = conn.cursor()
    c.execute("""
        INSERT INTO dreams (date, time, raw_text, title, mood, symbols, themes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (now.strftime("%Y-%m-%d"), now.strftime("%H:%M"), raw_text, title, mood, symbols, themes, now.isoformat()))
    conn.commit()

    dream_id = c.lastrowid
    print(f"\n✅ Dream #{dream_id} saved! Use --analyze {dream_id} for deep analysis.")


def list_dreams(conn):
    """List all recorded dreams."""
    c = conn.cursor()
    c.execute("SELECT id, date, title, mood FROM dreams ORDER BY date DESC, time DESC")
    dreams = c.fetchall()

    if not dreams:
        print("📭 No dreams recorded yet. Use --record to add your first dream!")
        return

    print(f"\n🌙 Dream Journal — {len(dreams)} entries")
    print("═" * 60)
    print(f"{'ID':<5} {'Date':<12} {'Mood':<12} {'Title'}")
    print("─" * 60)

    for d in dreams:
        mood_emoji = {
            "peaceful": "😌", "anxious": "😰", "joyful": "😊",
            "confused": "😕", "fearful": "😨", "nostalgic": "🥹",
            "adventurous": "🏔️", "melancholic": "😢", "empowered": "💪",
            "surreal": "🌀"
        }.get(d["mood"], "🌙")
        print(f"{d['id']:<5} {d['date']:<12} {mood_emoji} {d['mood']:<10} {d['title']}")

    print()


def analyze_dream(conn, dream_id):
    """Deep AI analysis of a specific dream."""
    c = conn.cursor()
    c.execute("SELECT * FROM dreams WHERE id = ?", (dream_id,))
    dream = c.fetchone()

    if not dream:
        print(f"❌ Dream #{dream_id} not found.")
        return

    symbols_db = load_symbols()

    print(f"\n🔮 Deep Analysis: Dream #{dream_id}")
    print(f"{'═' * 60}")
    print(f"📅 Date: {dream['date']} {dream['time']}")
    print(f"📝 Title: {dream['title']}")
    print(f"🎭 Mood: {dream['mood']}")
    print(f"\n📖 Dream Text:")
    print(f"{'─' * 40}")
    print(f"  {dream['raw_text'][:500]}{'...' if len(dream['raw_text']) > 500 else ''}")
    print()

    # Check for known symbols
    dream_symbols = [s.strip().lower() for s in (dream['symbols'] or '').split(',')]
    known_interpretations = []
    for sym in dream_symbols:
        for key, interpretation in symbols_db.get("symbols", {}).items():
            if sym and (sym in key.lower() or key.lower() in sym):
                known_interpretations.append(f"  • {key}: {interpretation}")
                break

    if known_interpretations:
        print("📚 Symbol Interpretations (from database):")
        print("─" * 40)
        for interp in known_interpretations[:6]:
            print(interp)
        print()

    # Deep AI analysis
    prompt = f"""You are a dream analyst combining Jungian psychology, modern neuroscience, and cultural symbolism.
Provide a deep analysis of this dream:

Title: {dream['title']}
Mood: {dream['mood']}
Dream: "{dream['raw_text']}"
Symbols identified: {dream['symbols']}
Themes: {dream['themes']}

Provide analysis in these sections:
1. SYMBOL ANALYSIS: What each symbol might represent
2. EMOTIONAL LANDSCAPE: Emotions and what they suggest
3. WAKING LIFE CONNECTIONS: How this might relate to daily life
4. RECURRING PATTERNS: What patterns this dream suggests
5. PERSONAL GROWTH: What your subconscious might be processing

Be insightful but not prescriptive. Use "might suggest" rather than definitive statements."""

    print("🧠 AI Deep Analysis:")
    print("─" * 40)
    analysis = ask_ollama(prompt)
    print(analysis)

    # Save analysis
    c.execute("UPDATE dreams SET analysis = ? WHERE id = ?", (analysis, dream_id))
    conn.commit()
    print(f"\n✅ Analysis saved to dream #{dream_id}")


def find_patterns(conn):
    """Analyze patterns across all dreams."""
    c = conn.cursor()
    c.execute("SELECT * FROM dreams ORDER BY date")
    dreams = c.fetchall()

    if len(dreams) < 2:
        print("📊 Need at least 2 dreams to find patterns. Keep journaling!")
        return

    print(f"\n🔍 Dream Pattern Analysis — {len(dreams)} dreams")
    print("═" * 60)

    # Mood distribution
    moods = Counter(d["mood"] for d in dreams if d["mood"])
    print("\n🎭 Mood Distribution:")
    print("─" * 30)
    for mood, count in moods.most_common():
        bar = "█" * int(count / len(dreams) * 20)
        print(f"  {mood:<14} {bar} ({count})")

    # Common symbols
    all_symbols = []
    for d in dreams:
        if d["symbols"]:
            all_symbols.extend([s.strip().lower() for s in d["symbols"].split(",")])

    symbol_counts = Counter(all_symbols)
    if symbol_counts:
        print("\n🔮 Most Common Symbols:")
        print("─" * 30)
        for sym, count in symbol_counts.most_common(10):
            if sym:
                print(f"  {sym:<20} × {count}")

    # Common themes
    all_themes = []
    for d in dreams:
        if d["themes"]:
            all_themes.extend([t.strip().lower() for t in d["themes"].split(",")])

    theme_counts = Counter(all_themes)
    if theme_counts:
        print("\n📂 Recurring Themes:")
        print("─" * 30)
        for theme, count in theme_counts.most_common(8):
            if theme:
                print(f"  {theme:<20} × {count}")

    # Day of week frequency
    day_counts = Counter()
    for d in dreams:
        try:
            dt = datetime.strptime(d["date"], "%Y-%m-%d")
            day_counts[dt.strftime("%A")] += 1
        except ValueError:
            pass

    if day_counts:
        print("\n📅 Dreams by Day of Week:")
        print("─" * 30)
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in days_order:
            count = day_counts.get(day, 0)
            bar = "█" * count
            print(f"  {day:<10} {bar} ({count})")

    # AI pattern analysis
    dream_summaries = "\n".join([
        f"- [{d['date']}] {d['title']} (mood: {d['mood']}, symbols: {d['symbols']})"
        for d in dreams[-20:]  # Last 20 dreams
    ])

    prompt = f"""Analyze these dream journal entries for patterns:

{dream_summaries}

Identify:
1. RECURRING PATTERNS: What keeps appearing?
2. EMOTIONAL TRENDS: How is the emotional landscape changing over time?
3. SUBCONSCIOUS THEMES: What might the subconscious be processing?
4. GROWTH INDICATORS: Signs of personal development in the dreams

Be insightful and specific. Reference actual content from the dreams."""

    print("\n🧠 AI Pattern Insights:")
    print("─" * 40)
    response = ask_ollama(prompt)
    print(response)


def search_dreams(conn, query):
    """Search dreams by content."""
    c = conn.cursor()
    c.execute("""
        SELECT id, date, title, mood, raw_text 
        FROM dreams 
        WHERE raw_text LIKE ? OR title LIKE ? OR symbols LIKE ? OR themes LIKE ?
        ORDER BY date DESC
    """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))
    results = c.fetchall()

    if not results:
        print(f"🔍 No dreams found matching '{query}'")
        return

    print(f"\n🔍 Search results for '{query}' — {len(results)} dreams found")
    print("═" * 60)

    for d in results:
        print(f"\n  #{d['id']} [{d['date']}] {d['title']} ({d['mood']})")
        # Show context around match
        text = d["raw_text"]
        idx = text.lower().find(query.lower())
        if idx >= 0:
            start = max(0, idx - 40)
            end = min(len(text), idx + len(query) + 40)
            snippet = text[start:end]
            print(f"  ...{snippet}...")
    print()


def show_stats(conn):
    """Show dream statistics."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as total FROM dreams")
    total = c.fetchone()["total"]

    if total == 0:
        print("📊 No dreams recorded yet!")
        return

    c.execute("SELECT AVG(LENGTH(raw_text)) as avg_len FROM dreams")
    avg_len = c.fetchone()["avg_len"] or 0

    c.execute("SELECT MIN(date) as first, MAX(date) as last FROM dreams")
    dates = c.fetchone()

    c.execute("SELECT mood, COUNT(*) as cnt FROM dreams GROUP BY mood ORDER BY cnt DESC")
    mood_dist = c.fetchall()

    print(f"\n📊 Dream Journal Statistics")
    print("═" * 40)
    print(f"  📝 Total dreams: {total}")
    print(f"  📏 Average length: {int(avg_len)} characters")
    print(f"  📅 First entry: {dates['first']}")
    print(f"  📅 Latest entry: {dates['last']}")

    if mood_dist:
        print(f"\n  🎭 Mood breakdown:")
        for m in mood_dist:
            pct = m["cnt"] / total * 100
            print(f"     {m['mood']:<14} {m['cnt']:>3} ({pct:.0f}%)")

    # Streak info
    c.execute("SELECT DISTINCT date FROM dreams ORDER BY date DESC LIMIT 7")
    recent_dates = [r["date"] for r in c.fetchall()]
    print(f"\n  🔥 Recent activity: {len(recent_dates)} days with dreams in last week")
    print()


def export_journal(conn):
    """Export all dreams as markdown."""
    c = conn.cursor()
    c.execute("SELECT * FROM dreams ORDER BY date DESC, time DESC")
    dreams = c.fetchall()

    if not dreams:
        print("📭 No dreams to export.")
        return

    export_path = SCRIPT_DIR / f"dream_export_{datetime.now().strftime('%Y%m%d')}.md"

    lines = ["# 🌙 Dream Journal Export\n"]
    lines.append(f"*Exported on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    lines.append(f"**Total Dreams: {len(dreams)}**\n")
    lines.append("---\n")

    for d in dreams:
        lines.append(f"\n## #{d['id']} — {d['title']}")
        lines.append(f"**Date:** {d['date']} {d['time']}  ")
        lines.append(f"**Mood:** {d['mood']}  ")
        lines.append(f"**Symbols:** {d['symbols']}  ")
        lines.append(f"**Themes:** {d['themes']}\n")
        lines.append(f"### Dream")
        lines.append(f"{d['raw_text']}\n")
        if d['analysis']:
            lines.append(f"### Analysis")
            lines.append(f"{d['analysis']}\n")
        lines.append("---\n")

    with open(export_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f"📄 Journal exported to: {export_path}")
    print(f"   {len(dreams)} dreams exported.")


def lucid_tips(conn):
    """AI suggests lucid dreaming techniques."""
    c = conn.cursor()
    c.execute("SELECT * FROM dreams ORDER BY date DESC LIMIT 10")
    dreams = c.fetchall()

    dream_context = ""
    if dreams:
        dream_context = f"""Based on the user's recent dreams:
{chr(10).join([f'- {d["title"]} (mood: {d["mood"]}, symbols: {d["symbols"]})' for d in dreams])}
"""

    prompt = f"""You are a lucid dreaming coach. {dream_context}

Provide personalized lucid dreaming tips:
1. REALITY CHECKS: 3 techniques suited to this person's dream patterns
2. DREAM SIGNS: Common elements in their dreams they can recognize
3. MILD TECHNIQUE: How to use Mnemonic Induction (personalized)
4. WILD TECHNIQUE: Wake-Initiated Lucid Dreaming tips
5. DREAM JOURNALING TIPS: How to improve dream recall
6. TONIGHT'S PLAN: A specific plan for lucid dreaming tonight

Be practical and encouraging."""

    print("🦋 Lucid Dreaming Tips")
    print("═" * 50)
    response = ask_ollama(prompt)
    print(response)


def main():
    parser = argparse.ArgumentParser(
        description="🌙 AI Dream Journal — Record & Analyze Your Dreams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  dream_journal.py --record          Record a new dream
  dream_journal.py --list            See all dreams
  dream_journal.py --analyze 3       Deep analysis of dream #3
  dream_journal.py --patterns        Find patterns across dreams
  dream_journal.py --search water    Search for dreams about water
  dream_journal.py --stats           View statistics
  dream_journal.py --export          Export as markdown
  dream_journal.py --lucid-tips      Lucid dreaming guidance
        """
    )

    parser.add_argument("--record", action="store_true", help="Record a new dream")
    parser.add_argument("--record-voice", action="store_true", help="Record via microphone")
    parser.add_argument("--list", action="store_true", help="List all dreams")
    parser.add_argument("--analyze", type=int, metavar="ID", help="Analyze a dream by ID")
    parser.add_argument("--patterns", action="store_true", help="Find patterns across dreams")
    parser.add_argument("--search", type=str, metavar="QUERY", help="Search dreams")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--export", action="store_true", help="Export as markdown")
    parser.add_argument("--lucid-tips", action="store_true", help="Lucid dreaming tips")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        print("\n🌙 Start with: --record to journal your dream!")
        return

    conn = init_db()

    try:
        if args.record or args.record_voice:
            record_dream(conn, voice=args.record_voice)
        elif args.list:
            list_dreams(conn)
        elif args.analyze is not None:
            analyze_dream(conn, args.analyze)
        elif args.patterns:
            find_patterns(conn)
        elif args.search:
            search_dreams(conn, args.search)
        elif args.stats:
            show_stats(conn)
        elif args.export:
            export_journal(conn)
        elif args.lucid_tips:
            lucid_tips(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
