#!/usr/bin/env python3
"""Focus Mode AI - Pomodoro timer with AI productivity coaching.

Tracks focus sessions in SQLite, blocks distracting apps,
provides AI-powered suggestions and productivity reports.
"""

import argparse
import json
import os
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

# --- Configuration ---
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
DB_FILE = SCRIPT_DIR / "focus_sessions.db"

# Default presets
SESSION_PRESETS = {
    25: "Pomodoro (25 min)",
    50: "Deep Work (50 min)",
    90: "Flow State (90 min)"
}

BREAK_PRESETS = {
    5: "Short Break (5 min)",
    15: "Long Break (15 min)"
}


def load_config() -> dict:
    """Load configuration from config.json."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "blocked_apps": [
            "Twitter", "Facebook", "Instagram", "TikTok",
            "Reddit", "YouTube", "Netflix", "Slack",
            "Discord", "Telegram", "WhatsApp"
        ],
        "presets": SESSION_PRESETS,
        "break_presets": BREAK_PRESETS,
        "goals": {
            "daily_focus_minutes": 180,
            "daily_sessions": 6,
            "weekly_focus_hours": 20
        }
    }


def notify_macos(title: str, message: str, sound: bool = True):
    """Send macOS notification."""
    try:
        sound_str = ' sound name "Glass"' if sound else ""
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}"{sound_str}'
        ], capture_output=True, timeout=5)
    except Exception:
        pass


def query_ollama(prompt: str) -> str:
    """Query Ollama for AI suggestions."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 300}
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return "💡 Tip: Stay focused on one task at a time. Break large tasks into smaller pieces."
    except Exception:
        return "💡 Tip: Take deep breaths and maintain good posture during your focus session."


# --- Database ---
def init_db():
    """Initialize SQLite database for tracking sessions."""
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            duration_minutes INTEGER NOT NULL,
            completed INTEGER DEFAULT 0,
            session_type TEXT DEFAULT 'focus',
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_active_session() -> dict:
    """Get currently active session if any."""
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    c.execute("""
        SELECT id, start_time, duration_minutes, session_type
        FROM sessions 
        WHERE end_time IS NULL 
        ORDER BY id DESC LIMIT 1
    """)
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "start_time": datetime.fromisoformat(row[1]),
            "duration_minutes": row[2],
            "session_type": row[3]
        }
    return None


def start_session(duration: int, session_type: str = "focus") -> int:
    """Start a new focus/break session."""
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    c.execute(
        "INSERT INTO sessions (start_time, duration_minutes, session_type) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), duration, session_type)
    )
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id


def complete_session(session_id: int, completed: bool = True):
    """Mark a session as completed."""
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    c.execute(
        "UPDATE sessions SET end_time = ?, completed = ? WHERE id = ?",
        (datetime.now().isoformat(), 1 if completed else 0, session_id)
    )
    conn.commit()
    conn.close()


def get_today_stats() -> dict:
    """Get today's focus statistics."""
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    c.execute("""
        SELECT COUNT(*), COALESCE(SUM(duration_minutes), 0)
        FROM sessions
        WHERE date(start_time) = ? AND session_type = 'focus' AND completed = 1
    """, (today,))
    row = c.fetchone()
    conn.close()
    return {
        "sessions": row[0],
        "total_minutes": row[1]
    }


def get_week_stats() -> dict:
    """Get this week's focus statistics."""
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")

    c.execute("""
        SELECT COUNT(*), COALESCE(SUM(duration_minutes), 0)
        FROM sessions
        WHERE date(start_time) >= ? AND session_type = 'focus' AND completed = 1
    """, (week_start,))
    row = c.fetchone()

    # Daily breakdown
    c.execute("""
        SELECT date(start_time) as day, COUNT(*), SUM(duration_minutes)
        FROM sessions
        WHERE date(start_time) >= ? AND session_type = 'focus' AND completed = 1
        GROUP BY day ORDER BY day
    """, (week_start,))
    daily = c.fetchall()
    conn.close()

    return {
        "sessions": row[0],
        "total_minutes": row[1],
        "total_hours": round(row[1] / 60, 1),
        "daily": daily
    }


# --- App Blocking ---
def block_apps(config: dict):
    """Block distracting apps by killing them."""
    blocked = config.get("blocked_apps", [])
    killed = []
    for app in blocked:
        try:
            result = subprocess.run(
                ["killall", app],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                killed.append(app)
        except Exception:
            pass

    if killed:
        print(f"🚫 Blocked: {', '.join(killed)}")
    else:
        print("🚫 No distracting apps were running.")
    notify_macos("Focus Mode", f"Blocked {len(killed)} distracting apps")


def unblock_apps(config: dict):
    """Unblock apps (just notify - they can reopen)."""
    blocked = config.get("blocked_apps", [])
    print(f"✅ Unblocked: {', '.join(blocked)}")
    print("   Apps can now be reopened.")
    notify_macos("Focus Mode", "Apps unblocked. Focus session ended.")


# --- Timer ---
def run_timer(duration_minutes: int, session_type: str = "focus"):
    """Run a countdown timer with notifications."""
    active = get_active_session()
    if active:
        elapsed = (datetime.now() - active["start_time"]).total_seconds() / 60
        remaining = active["duration_minutes"] - elapsed
        if remaining > 0:
            print(f"⚠️  Session already active ({active['session_type']}, {remaining:.0f} min remaining)")
            print("   Wait for it to finish or Ctrl+C to cancel.")
            return

    session_id = start_session(duration_minutes, session_type)
    total_seconds = duration_minutes * 60
    start_time = time.time()

    emoji = "🍅" if session_type == "focus" else "☕"
    label = SESSION_PRESETS.get(duration_minutes, f"{duration_minutes} min") if session_type == "focus" else BREAK_PRESETS.get(duration_minutes, f"{duration_minutes} min break")

    print(f"\n{emoji} {label}")
    print(f"   Started at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"   Ends at:    {(datetime.now() + timedelta(minutes=duration_minutes)).strftime('%H:%M:%S')}")
    print("\n   Press Ctrl+C to stop early\n")

    notify_macos("Focus Mode", f"Started: {label}")

    # Show AI tip at start
    if session_type == "focus":
        hour = datetime.now().hour
        tip = query_ollama(
            f"Give one brief, actionable productivity tip for someone starting a {duration_minutes}-minute focus session at {hour}:00. Keep it under 2 sentences."
        )
        print(f"   💡 {tip}\n")

    try:
        while True:
            elapsed = time.time() - start_time
            remaining = total_seconds - elapsed

            if remaining <= 0:
                break

            mins = int(remaining // 60)
            secs = int(remaining % 60)
            bar_width = 30
            progress = elapsed / total_seconds
            filled = int(bar_width * progress)
            bar = "█" * filled + "░" * (bar_width - filled)

            print(f"\r   [{bar}] {mins:02d}:{secs:02d} remaining", end="", flush=True)

            # Midpoint notification
            if abs(elapsed - total_seconds / 2) < 1:
                notify_macos("Focus Mode", f"Halfway! {mins} minutes remaining.")

            time.sleep(1)

        # Session complete
        print(f"\r   [{'█' * 30}] 00:00 - Complete!     ")
        complete_session(session_id, completed=True)

        if session_type == "focus":
            notify_macos("Focus Mode", f"🎉 Session complete! Great work!", sound=True)
            print(f"\n🎉 Focus session complete!")

            # AI tip between sessions
            stats = get_today_stats()
            tip = query_ollama(
                f"Someone just completed a {duration_minutes}-minute focus session. They've done {stats['sessions']} sessions today ({stats['total_minutes']} total minutes). Give a brief encouraging message and suggest whether to take a break or continue. Keep it under 3 sentences."
            )
            print(f"\n   💡 {tip}")
            print(f"\n   📊 Today: {stats['sessions']} sessions, {stats['total_minutes']} minutes")
        else:
            notify_macos("Focus Mode", "Break over! Ready for next session?", sound=True)
            print(f"\n☕ Break complete! Ready to focus again?")

    except KeyboardInterrupt:
        elapsed_mins = (time.time() - start_time) / 60
        print(f"\n\n⏹️  Session stopped after {elapsed_mins:.1f} minutes.")
        complete_session(session_id, completed=elapsed_mins >= duration_minutes * 0.8)


# --- Commands ---
def cmd_status():
    """Show current session status."""
    active = get_active_session()
    if active:
        elapsed = (datetime.now() - active["start_time"]).total_seconds() / 60
        remaining = active["duration_minutes"] - elapsed
        if remaining > 0:
            emoji = "🍅" if active["session_type"] == "focus" else "☕"
            print(f"\n{emoji} Active {active['session_type']} session")
            print(f"   Duration: {active['duration_minutes']} minutes")
            print(f"   Elapsed:  {elapsed:.0f} minutes")
            print(f"   Remaining: {remaining:.0f} minutes")
            print(f"   Started:  {active['start_time'].strftime('%H:%M:%S')}")
        else:
            print("\n✅ No active session (last one ended).")
    else:
        print("\n💤 No active session.")

    stats = get_today_stats()
    print(f"\n📊 Today: {stats['sessions']} sessions, {stats['total_minutes']} min focused")


def cmd_stats():
    """Show focus statistics."""
    config = load_config()
    goals = config.get("goals", {})
    today = get_today_stats()
    week = get_week_stats()

    daily_goal = goals.get("daily_focus_minutes", 180)
    weekly_goal = goals.get("weekly_focus_hours", 20)

    print("\n📊 Focus Statistics")
    print("=" * 40)

    # Today
    print(f"\n📅 Today:")
    print(f"   Sessions:  {today['sessions']}")
    print(f"   Focus:     {today['total_minutes']} min / {daily_goal} min goal")
    progress = min(today['total_minutes'] / daily_goal, 1.0) if daily_goal > 0 else 0
    bar = "█" * int(20 * progress) + "░" * (20 - int(20 * progress))
    print(f"   Progress:  [{bar}] {progress*100:.0f}%")

    # This week
    print(f"\n📅 This Week:")
    print(f"   Sessions:  {week['sessions']}")
    print(f"   Focus:     {week['total_hours']} hrs / {weekly_goal} hrs goal")
    progress = min(week['total_hours'] / weekly_goal, 1.0) if weekly_goal > 0 else 0
    bar = "█" * int(20 * progress) + "░" * (20 - int(20 * progress))
    print(f"   Progress:  [{bar}] {progress*100:.0f}%")

    if week["daily"]:
        print(f"\n   Daily breakdown:")
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for day_str, count, minutes in week["daily"]:
            day_date = datetime.strptime(day_str, "%Y-%m-%d")
            day_name = days[day_date.weekday()]
            mini_bar = "█" * min(int(minutes / 15), 12)
            print(f"   {day_name} {day_str}: {count} sessions, {minutes} min {mini_bar}")


def cmd_suggest():
    """AI suggests what to work on."""
    hour = datetime.now().hour
    stats = get_today_stats()
    week = get_week_stats()

    time_of_day = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"

    prompt = f"""Based on the following context, suggest what someone should focus on right now.

Time: {datetime.now().strftime('%H:%M')} ({time_of_day})
Today's focus: {stats['total_minutes']} minutes across {stats['sessions']} sessions
This week's focus: {week['total_hours']} hours across {week['sessions']} sessions

Consider:
- Time of day energy levels (mornings for creative/hard work, afternoons for meetings/routine, evenings for planning)
- How much focus has already been done today
- Suggest an appropriate session duration (25, 50, or 90 min)
- Give a specific type of task to work on

Keep your response brief (3-4 sentences max). Be specific and actionable."""

    print(f"\n🤖 AI Suggestion ({time_of_day.title()}):")
    print(f"   Current stats: {stats['sessions']} sessions, {stats['total_minutes']} min today")
    print()

    suggestion = query_ollama(prompt)
    print(f"   {suggestion}")
    print()


def cmd_report(period: str = "daily"):
    """Generate focus report."""
    config = load_config()
    goals = config.get("goals", {})

    if period == "weekly":
        week = get_week_stats()
        weekly_goal = goals.get("weekly_focus_hours", 20)

        print("\n📈 Weekly Focus Report")
        print("=" * 40)
        print(f"   Total sessions: {week['sessions']}")
        print(f"   Total focus:    {week['total_hours']} hours")
        print(f"   Weekly goal:    {weekly_goal} hours")
        print(f"   Achievement:    {(week['total_hours']/weekly_goal*100) if weekly_goal else 0:.0f}%")

        if week['sessions'] > 0:
            avg_per_day = week['total_minutes'] / max(len(week['daily']), 1)
            print(f"   Avg per day:    {avg_per_day:.0f} minutes")

        if week["daily"]:
            print(f"\n   📅 Daily Breakdown:")
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for day_str, count, minutes in week["daily"]:
                day_date = datetime.strptime(day_str, "%Y-%m-%d")
                day_name = days[day_date.weekday()]
                bar = "█" * min(int(minutes / 10), 15)
                print(f"      {day_name}: {minutes:3d} min ({count} sessions) {bar}")

        # AI insight
        prompt = f"""Analyze this weekly focus data and give a brief productivity insight:
- Total: {week['total_hours']} hours across {week['sessions']} sessions
- Goal: {weekly_goal} hours/week
- Days active: {len(week['daily'])}

Give 2-3 sentences of actionable feedback on productivity patterns."""

        print(f"\n   🤖 AI Insight:")
        insight = query_ollama(prompt)
        print(f"      {insight}")
    else:
        today = get_today_stats()
        daily_goal = goals.get("daily_focus_minutes", 180)

        print("\n📈 Daily Focus Report")
        print("=" * 40)
        print(f"   Date:          {datetime.now().strftime('%A, %B %d, %Y')}")
        print(f"   Sessions:      {today['sessions']}")
        print(f"   Total focus:   {today['total_minutes']} minutes")
        print(f"   Daily goal:    {daily_goal} minutes")
        print(f"   Achievement:   {(today['total_minutes']/daily_goal*100) if daily_goal else 0:.0f}%")

        remaining = max(daily_goal - today['total_minutes'], 0)
        if remaining > 0:
            sessions_needed = -(-remaining // 25)  # Ceiling division
            print(f"   Remaining:     {remaining} min (~{sessions_needed} Pomodoros)")
        else:
            print(f"   🎉 Daily goal achieved!")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="🍅 Focus Mode AI - Pomodoro timer with AI productivity coaching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --start 25        # Start 25-min Pomodoro
  %(prog)s --start 50        # Start 50-min deep work session
  %(prog)s --break            # Take a 5-min break
  %(prog)s --break 15         # Take a 15-min break
  %(prog)s --status           # Check current session
  %(prog)s --stats            # View statistics
  %(prog)s --suggest          # Get AI suggestion
  %(prog)s --block            # Block distracting apps
  %(prog)s --report           # Daily report
  %(prog)s --report weekly    # Weekly report
        """
    )

    parser.add_argument("--start", metavar="MINUTES", type=int, help="Start focus session (25, 50, or 90 min)")
    parser.add_argument("--break", dest="take_break", nargs="?", const=5, type=int, metavar="MINUTES", help="Take a break (default 5 min, or 15 min)")
    parser.add_argument("--status", action="store_true", help="Show current session status")
    parser.add_argument("--stats", action="store_true", help="Show focus statistics")
    parser.add_argument("--suggest", action="store_true", help="AI suggests what to work on")
    parser.add_argument("--block", action="store_true", help="Block distracting apps")
    parser.add_argument("--unblock", action="store_true", help="Unblock apps")
    parser.add_argument("--report", nargs="?", const="daily", metavar="PERIOD", help="Focus report (daily or weekly)")

    args = parser.parse_args()

    if not any([args.start, args.take_break, args.status, args.stats, args.suggest, args.block, args.unblock, args.report]):
        parser.print_help()
        sys.exit(0)

    # Initialize database
    init_db()
    config = load_config()

    if args.status:
        cmd_status()
    elif args.stats:
        cmd_stats()
    elif args.suggest:
        cmd_suggest()
    elif args.block:
        block_apps(config)
    elif args.unblock:
        unblock_apps(config)
    elif args.report:
        cmd_report(args.report)
    elif args.start:
        duration = args.start
        if duration not in SESSION_PRESETS:
            print(f"⚠️  Non-standard duration: {duration} min (presets: 25, 50, 90)")
        config_blocked = config.get("blocked_apps", [])
        if config_blocked:
            print("🚫 Blocking distracting apps...")
            block_apps(config)
        run_timer(duration, "focus")
    elif args.take_break:
        duration = args.take_break
        if duration not in BREAK_PRESETS:
            print(f"⚠️  Non-standard break: {duration} min (presets: 5, 15)")
        run_timer(duration, "break")


if __name__ == "__main__":
    main()
