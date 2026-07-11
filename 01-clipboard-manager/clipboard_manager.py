#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
AI Clipboard Manager - Monitors clipboard, classifies content, stores in SQLite,
and provides AI-powered summarization via Ollama.
"""

import argparse
import datetime
import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import requests

# Configuration
DB_PATH = Path(__file__).parent / "clipboard.db"
PID_FILE = Path(__file__).parent / "daemon.pid"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"
POLL_INTERVAL = 1.0  # seconds
LONG_TEXT_THRESHOLD = 200  # characters before AI summarization kicks in


def init_db():
    """Initialize the SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            summary TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            length INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_clips_category ON clips(category)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_clips_timestamp ON clips(timestamp)
    """)
    conn.commit()
    conn.close()


def get_clipboard():
    """Get current clipboard content using pbpaste."""
    try:
        result = subprocess.run(
            ["pbpaste"], capture_output=True, text=True, timeout=5
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def classify_content(text):
    """Classify clipboard content into categories."""
    text_stripped = text.strip()

    # URL pattern
    if re.match(r'^https?://\S+$', text_stripped) or re.match(r'^www\.\S+$', text_stripped):
        return "url"

    # Email pattern
    if re.match(r'^[\w.+-]+@[\w-]+\.[\w.-]+$', text_stripped):
        return "email"

    # Phone number pattern (various formats)
    phone_pattern = r'^[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,15}$'
    if re.match(phone_pattern, text_stripped):
        return "phone"

    # Address pattern (contains number + street indicators)
    address_indicators = ['street', 'st.', 'avenue', 'ave.', 'road', 'rd.',
                          'boulevard', 'blvd.', 'drive', 'dr.', 'lane', 'ln.',
                          'floor', 'suite', 'apt', 'zip', 'pin']
    if any(indicator in text_stripped.lower() for indicator in address_indicators):
        if re.search(r'\d', text_stripped):
            return "address"

    # Code pattern (contains programming indicators)
    code_indicators = [
        r'def \w+\(', r'function\s+\w+', r'class \w+', r'import \w+',
        r'from \w+ import', r'const \w+\s*=', r'let \w+\s*=', r'var \w+\s*=',
        r'\{[\s\S]*\}', r'=>', r'if\s*\(', r'for\s*\(', r'while\s*\(',
        r'return\s+', r'#include', r'package \w+', r'public\s+class',
        r'<[a-zA-Z]+[^>]*>', r'SELECT\s+.*\s+FROM', r'\w+\.\w+\(.*\)',
    ]
    code_matches = sum(1 for pattern in code_indicators if re.search(pattern, text_stripped))
    if code_matches >= 2:
        return "code"

    # Multiple URLs in text
    urls_found = re.findall(r'https?://\S+', text_stripped)
    if len(urls_found) >= 2:
        return "url"

    # Multiple emails in text
    emails_found = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text_stripped)
    if len(emails_found) >= 2:
        return "email"

    return "text"


def ai_summarize(text):
    """Use Ollama to summarize long text."""
    try:
        prompt = f"Summarize the following text in one concise sentence (max 100 words):\n\n{text[:2000]}"
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=30,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "").strip()
    except (requests.RequestException, json.JSONDecodeError):
        pass
    return None


def send_notification(title, message):
    """Send a macOS notification."""
    # Escape special characters for AppleScript
    message_escaped = message.replace('\\', '\\\\').replace('"', '\\"')[:150]
    title_escaped = title.replace('\\', '\\\\').replace('"', '\\"')
    script = f'display notification "{message_escaped}" with title "{title_escaped}"'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, timeout=5
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


def store_clip(content, category, summary=None):
    """Store a clip in the database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "INSERT INTO clips (content, category, summary, length) VALUES (?, ?, ?, ?)",
        (content, category, summary, len(content))
    )
    conn.commit()
    conn.close()


def daemon_loop():
    """Main daemon loop - monitors clipboard for changes."""
    init_db()
    last_content = get_clipboard()
    print(f"[{datetime.datetime.now()}] Clipboard daemon started. Monitoring...")

    while True:
        try:
            current = get_clipboard()
            if current is not None and current != last_content and current.strip():
                last_content = current
                category = classify_content(current)

                # AI summarize long text
                summary = None
                if len(current) > LONG_TEXT_THRESHOLD and category == "text":
                    summary = ai_summarize(current)

                store_clip(current, category, summary)

                # Notification
                preview = current[:80].replace('\n', ' ')
                send_notification(
                    f"📋 Clip: {category.upper()}",
                    f"{preview}{'...' if len(current) > 80 else ''}"
                )
                print(f"[{datetime.datetime.now()}] Captured [{category}]: {preview[:50]}...")

            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\nDaemon stopped.")
            break
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            time.sleep(POLL_INTERVAL)


def cmd_search(query):
    """Search clips by content."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.execute(
        "SELECT id, category, content, summary, timestamp FROM clips "
        "WHERE content LIKE ? OR summary LIKE ? ORDER BY timestamp DESC LIMIT 20",
        (f"%{query}%", f"%{query}%")
    )
    results = cursor.fetchall()
    conn.close()

    if not results:
        print("No clips found matching your query.")
        return

    print(f"\n{'='*60}")
    print(f" Search Results for: '{query}' ({len(results)} found)")
    print(f"{'='*60}")
    for clip_id, category, content, summary, timestamp in results:
        preview = content[:100].replace('\n', ' ')
        print(f"\n  [{clip_id}] {timestamp} | {category.upper()}")
        print(f"  {preview}{'...' if len(content) > 100 else ''}")
        if summary:
            print(f"  Summary: {summary[:80]}")
    print()


def cmd_list():
    """List last 20 clips."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.execute(
        "SELECT id, category, content, summary, timestamp FROM clips "
        "ORDER BY timestamp DESC LIMIT 20"
    )
    results = cursor.fetchall()
    conn.close()

    if not results:
        print("No clips stored yet.")
        return

    print(f"\n{'='*60}")
    print(f" Last {len(results)} Clipboard Entries")
    print(f"{'='*60}")
    for clip_id, category, content, summary, timestamp in results:
        preview = content[:80].replace('\n', ' ')
        print(f"\n  [{clip_id}] {timestamp} | {category.upper()} | {len(content)} chars")
        print(f"  {preview}{'...' if len(content) > 80 else ''}")
        if summary:
            print(f"  📝 {summary[:60]}")
    print()


def cmd_stats():
    """Show clipboard statistics."""
    conn = sqlite3.connect(str(DB_PATH))

    total = conn.execute("SELECT COUNT(*) FROM clips").fetchone()[0]
    categories = conn.execute(
        "SELECT category, COUNT(*) as cnt FROM clips GROUP BY category ORDER BY cnt DESC"
    ).fetchall()
    today = conn.execute(
        "SELECT COUNT(*) FROM clips WHERE date(timestamp) = date('now')"
    ).fetchone()[0]
    avg_len = conn.execute("SELECT AVG(length) FROM clips").fetchone()[0]

    conn.close()

    print(f"\n{'='*60}")
    print(f" 📊 Clipboard Statistics")
    print(f"{'='*60}")
    print(f"\n  Total clips:     {total}")
    print(f"  Today's clips:   {today}")
    print(f"  Average length:  {int(avg_len) if avg_len else 0} chars")
    print(f"\n  Categories:")
    for cat, count in categories:
        bar = "█" * min(count, 30)
        print(f"    {cat:10s} : {count:4d} {bar}")
    print()


def daemonize():
    """Run the clipboard monitor as a background daemon."""
    # Fork the process
    try:
        pid = os.fork()
        if pid > 0:
            # Parent exits
            print(f"Daemon started with PID {pid}")
            with open(str(PID_FILE), 'w') as f:
                f.write(str(pid))
            sys.exit(0)
    except OSError as e:
        print(f"Fork failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Child process continues
    os.setsid()
    os.umask(0)

    # Redirect stdout/stderr to log file
    log_file = Path(__file__).parent / "daemon.log"
    sys.stdout = open(str(log_file), 'a')
    sys.stderr = sys.stdout

    # Handle signals
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

    daemon_loop()


def main():
    parser = argparse.ArgumentParser(
        description="AI Clipboard Manager - Monitor, classify, and search your clipboard history"
    )
    parser.add_argument("--search", "-s", type=str, help="Search clips by content")
    parser.add_argument("--list", "-l", action="store_true", help="List last 20 clips")
    parser.add_argument("--stats", action="store_true", help="Show clipboard statistics")
    parser.add_argument("--daemon", "-d", action="store_true", help="Run as background daemon")
    parser.add_argument("--foreground", "-f", action="store_true", help="Run in foreground (for testing)")

    args = parser.parse_args()

    # Ensure DB exists for query commands
    init_db()

    if args.search:
        cmd_search(args.search)
    elif args.list:
        cmd_list()
    elif args.stats:
        cmd_stats()
    elif args.daemon:
        daemonize()
    elif args.foreground:
        daemon_loop()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
