#!/usr/bin/env python3
"""AI Habit Tracker - Track habits with AI coaching and insights."""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

# Configuration
OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2"
DB_PATH = Path.home() / ".habit_tracker.db"


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"


def get_db():
    """Get SQLite database connection."""
    db = sqlite3.connect(str(DB_PATH))
    db.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            frequency TEXT NOT NULL DEFAULT 'daily',
            created_at TEXT NOT NULL,
            goal TEXT,
            active INTEGER DEFAULT 1
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            logged_at TEXT NOT NULL,
            note TEXT,
            mood TEXT,
            FOREIGN KEY (habit_id) REFERENCES habits(id)
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_logs_habit ON logs(habit_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_logs_date ON logs(logged_at)")
    db.commit()
    return db


def query_ollama(prompt, model=MODEL):
    """Query Ollama for AI responses."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}Error: Cannot connect to Ollama at {OLLAMA_URL}")
        print(f"Make sure Ollama is running: ollama serve{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}Error querying Ollama: {e}{Colors.RESET}")
        return ""


def add_habit(db, name, frequency="daily", goal=None):
    """Add a new habit to track."""
    try:
        db.execute(
            "INSERT INTO habits (name, frequency, created_at, goal) VALUES (?, ?, ?, ?)",
            (name, frequency, datetime.now().isoformat(), goal),
        )
        db.commit()
        print(f"{Colors.GREEN}✓ Added habit: {Colors.BOLD}{name}{Colors.RESET}")
        print(f"  Frequency: {frequency}")
        if goal:
            print(f"  Goal: {goal}")
    except sqlite3.IntegrityError:
        print(f"{Colors.YELLOW}Habit '{name}' already exists.{Colors.RESET}")


def log_habit(db, name, note=None, mood=None):
    """Log a habit as completed."""
    cursor = db.execute("SELECT id FROM habits WHERE name = ? AND active = 1", (name,))
    row = cursor.fetchone()
    if not row:
        print(f"{Colors.RED}Habit '{name}' not found. Use --status to see habits.{Colors.RESET}")
        return
    habit_id = row[0]
    today = datetime.now().strftime("%Y-%m-%d")
    existing = db.execute(
        "SELECT id FROM logs WHERE habit_id = ? AND logged_at LIKE ?",
        (habit_id, f"{today}%"),
    ).fetchone()
    if existing:
        print(f"{Colors.YELLOW}'{name}' already logged today.{Colors.RESET}")
        return
    db.execute(
        "INSERT INTO logs (habit_id, logged_at, note, mood) VALUES (?, ?, ?, ?)",
        (habit_id, datetime.now().isoformat(), note, mood),
    )
    db.commit()
    streak = get_streak(db, habit_id)
    print(f"{Colors.GREEN}✓ Logged: {Colors.BOLD}{name}{Colors.RESET}")
    if note:
        print(f"  Note: {note}")
    if mood:
        print(f"  Mood: {mood}")
    print(f"  {Colors.CYAN}🔥 Streak: {streak} days{Colors.RESET}")


def get_streak(db, habit_id):
    """Calculate current streak for a habit."""
    cursor = db.execute(
        "SELECT DISTINCT DATE(logged_at) as d FROM logs WHERE habit_id = ? ORDER BY d DESC",
        (habit_id,),
    )
    dates = [row[0] for row in cursor.fetchall()]
    if not dates:
        return 0
    streak = 0
    today = datetime.now().date()
    check_date = today
    for d in dates:
        log_date = datetime.strptime(d, "%Y-%m-%d").date()
        if log_date == check_date:
            streak += 1
            check_date -= timedelta(days=1)
        elif log_date == check_date - timedelta(days=1):
            check_date = log_date
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    return streak


def show_status(db):
    """Show today's habits status."""
    today = datetime.now().strftime("%Y-%m-%d")
    day_of_week = datetime.now().weekday()
    habits = db.execute("SELECT id, name, frequency FROM habits WHERE active = 1").fetchall()
    if not habits:
        print(f"{Colors.YELLOW}No habits tracked yet. Use --add to start.{Colors.RESET}")
        return
    print(f"{Colors.BOLD}📋 Today's Habits ({today}):{Colors.RESET}\n")
    done_count = 0
    total_count = 0
    for habit_id, name, frequency in habits:
        if frequency == "weekly" and day_of_week != 0:
            week_start = (datetime.now() - timedelta(days=day_of_week)).strftime("%Y-%m-%d")
            logged = db.execute(
                "SELECT id FROM logs WHERE habit_id = ? AND logged_at >= ?",
                (habit_id, week_start),
            ).fetchone()
        else:
            logged = db.execute(
                "SELECT id FROM logs WHERE habit_id = ? AND logged_at LIKE ?",
                (habit_id, f"{today}%"),
            ).fetchone()
        total_count += 1
        if logged:
            done_count += 1
            print(f"  {Colors.GREEN}✓ {name}{Colors.RESET} {Colors.DIM}({frequency}){Colors.RESET}")
        else:
            print(f"  {Colors.RED}○ {name}{Colors.RESET} {Colors.DIM}({frequency}){Colors.RESET}")
    pct = (done_count / total_count * 100) if total_count else 0
    color = Colors.GREEN if pct >= 80 else Colors.YELLOW if pct >= 50 else Colors.RED
    print(f"\n  {color}Progress: {done_count}/{total_count} ({pct:.0f}%){Colors.RESET}")
    bar_len = 20
    filled = int(bar_len * pct / 100)
    bar = f"{color}{'█' * filled}{'░' * (bar_len - filled)}{Colors.RESET}"
    print(f"  [{bar}]")


def show_streaks(db):
    """Show current streaks for all habits."""
    habits = db.execute("SELECT id, name, frequency FROM habits WHERE active = 1").fetchall()
    if not habits:
        print(f"{Colors.YELLOW}No habits tracked yet.{Colors.RESET}")
        return
    print(f"{Colors.BOLD}🔥 Current Streaks:{Colors.RESET}\n")
    streaks = []
    for habit_id, name, frequency in habits:
        streak = get_streak(db, habit_id)
        streaks.append((streak, name, frequency))
    streaks.sort(key=lambda x: x[0], reverse=True)
    for streak, name, frequency in streaks:
        if streak >= 7:
            color = Colors.GREEN
            icon = "🔥"
        elif streak >= 3:
            color = Colors.YELLOW
            icon = "⭐"
        else:
            color = Colors.DIM
            icon = "  "
        bar = "█" * min(streak, 30)
        print(f"  {icon} {color}{name:20s} {streak:3d} days {bar}{Colors.RESET}")


def show_stats(db):
    """Show detailed statistics."""
    habits = db.execute("SELECT id, name, frequency, created_at FROM habits WHERE active = 1").fetchall()
    if not habits:
        print(f"{Colors.YELLOW}No habits tracked yet.{Colors.RESET}")
        return
    print(f"{Colors.BOLD}📊 Habit Statistics:{Colors.RESET}\n")
    for habit_id, name, frequency, created_at in habits:
        created = datetime.fromisoformat(created_at).date()
        days_tracked = (datetime.now().date() - created).days + 1
        total_logs = db.execute("SELECT COUNT(*) FROM logs WHERE habit_id = ?", (habit_id,)).fetchone()[0]
        if frequency == "daily":
            expected = days_tracked
        else:
            expected = max(1, days_tracked // 7)
        completion_rate = (total_logs / expected * 100) if expected else 0
        streak = get_streak(db, habit_id)
        best_streak = get_best_streak(db, habit_id)
        color = Colors.GREEN if completion_rate >= 80 else Colors.YELLOW if completion_rate >= 50 else Colors.RED
        print(f"  {Colors.BOLD}{name}{Colors.RESET} ({frequency})")
        print(f"    Completion: {color}{completion_rate:.0f}%{Colors.RESET} ({total_logs}/{expected} days)")
        print(f"    Current streak: {streak} days | Best: {best_streak} days")
        print(f"    Tracking since: {created}")
        # Last 7 days visualization
        last7 = []
        for i in range(6, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            logged = db.execute(
                "SELECT id FROM logs WHERE habit_id = ? AND logged_at LIKE ?",
                (habit_id, f"{d}%"),
            ).fetchone()
            last7.append("█" if logged else "░")
        print(f"    Last 7 days: [{Colors.GREEN}{''.join(last7)}{Colors.RESET}]")
        print()


def get_best_streak(db, habit_id):
    """Get the longest streak ever for a habit."""
    cursor = db.execute(
        "SELECT DISTINCT DATE(logged_at) as d FROM logs WHERE habit_id = ? ORDER BY d",
        (habit_id,),
    )
    dates = [datetime.strptime(row[0], "%Y-%m-%d").date() for row in cursor.fetchall()]
    if not dates:
        return 0
    best = 1
    current = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i-1]).days == 1:
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best


def ai_coach(db):
    """Get AI coaching based on habit patterns."""
    habits = db.execute("SELECT id, name, frequency, created_at FROM habits WHERE active = 1").fetchall()
    if not habits:
        print(f"{Colors.YELLOW}No habits to coach on. Add some habits first.{Colors.RESET}")
        return
    habit_data = []
    for habit_id, name, frequency, created_at in habits:
        streak = get_streak(db, habit_id)
        total = db.execute("SELECT COUNT(*) FROM logs WHERE habit_id = ?", (habit_id,)).fetchone()[0]
        days = (datetime.now().date() - datetime.fromisoformat(created_at).date()).days + 1
        rate = (total / days * 100) if days else 0
        recent_moods = db.execute(
            "SELECT mood FROM logs WHERE habit_id = ? AND mood IS NOT NULL ORDER BY logged_at DESC LIMIT 5",
            (habit_id,),
        ).fetchall()
        moods = [m[0] for m in recent_moods]
        habit_data.append(f"- {name}: {frequency}, streak={streak}, completion={rate:.0f}%, moods={moods}")
    data_str = "\n".join(habit_data)
    prompt = f"""You are a supportive habit coach. Based on these habit patterns, give brief personalized advice.

Habits:
{data_str}

Give 3-4 short, actionable tips. Be encouraging but honest. Focus on weak areas."""
    print(f"{Colors.BOLD}🧠 AI Coach:{Colors.RESET}\n")
    response = query_ollama(prompt)
    print(f"  {Colors.CYAN}{response}{Colors.RESET}")


def ai_report(db, period="weekly"):
    """Generate AI progress report."""
    days = 7 if period == "weekly" else 30
    since = (datetime.now() - timedelta(days=days)).isoformat()
    habits = db.execute("SELECT id, name, frequency FROM habits WHERE active = 1").fetchall()
    if not habits:
        print(f"{Colors.YELLOW}No habits to report on.{Colors.RESET}")
        return
    report_data = []
    for habit_id, name, frequency in habits:
        logs = db.execute(
            "SELECT COUNT(*) FROM logs WHERE habit_id = ? AND logged_at >= ?",
            (habit_id, since),
        ).fetchone()[0]
        report_data.append(f"- {name} ({frequency}): completed {logs}/{days if frequency=='daily' else days//7} times")
    data_str = "\n".join(report_data)
    prompt = f"""Generate a brief {period} habit progress report. Be encouraging and specific.

Period: last {days} days
Habits:
{data_str}

Format: Summary paragraph, highlights, areas to improve. Keep it under 150 words."""
    print(f"{Colors.BOLD}📝 {period.title()} Report:{Colors.RESET}\n")
    response = query_ollama(prompt)
    print(f"  {Colors.CYAN}{response}{Colors.RESET}")


def ai_suggest(db):
    """AI suggests new habits based on existing patterns."""
    habits = db.execute("SELECT name, frequency, goal FROM habits WHERE active = 1").fetchall()
    existing = "\n".join(f"- {n} ({f})" + (f" goal: {g}" if g else "") for n, f, g in habits)
    if not existing:
        existing = "No habits yet"
    prompt = f"""Based on these existing habits, suggest 3 complementary new habits.

Current habits:
{existing}

For each suggestion, give: habit name, recommended frequency, and why it pairs well.
Keep suggestions practical and achievable. Format as a numbered list."""
    print(f"{Colors.BOLD}💡 AI Suggestions:{Colors.RESET}\n")
    response = query_ollama(prompt)
    print(f"  {Colors.CYAN}{response}{Colors.RESET}")


def main():
    parser = argparse.ArgumentParser(description="AI Habit Tracker - Track and improve habits with AI")
    parser.add_argument("--add", type=str, help="Add a new habit")
    parser.add_argument("--frequency", type=str, choices=["daily", "weekly"], default="daily")
    parser.add_argument("--goal", type=str, help="Goal for the habit")
    parser.add_argument("--log", type=str, help="Log habit as done")
    parser.add_argument("--note", type=str, help="Add note to log entry")
    parser.add_argument("--mood", type=str, help="Add mood to log entry")
    parser.add_argument("--status", action="store_true", help="Show today's habit status")
    parser.add_argument("--streak", action="store_true", help="Show current streaks")
    parser.add_argument("--stats", action="store_true", help="Show detailed statistics")
    parser.add_argument("--coach", action="store_true", help="Get AI coaching")
    parser.add_argument("--report", type=str, choices=["weekly", "monthly"], help="AI progress report")
    parser.add_argument("--suggest", action="store_true", help="AI habit suggestions")
    args = parser.parse_args()

    if not any([args.add, args.log, args.status, args.streak, args.stats, args.coach, args.report, args.suggest]):
        parser.print_help()
        sys.exit(0)

    db = get_db()
    if args.add:
        add_habit(db, args.add, args.frequency, args.goal)
    elif args.log:
        log_habit(db, args.log, args.note, args.mood)
    elif args.status:
        show_status(db)
    elif args.streak:
        show_streaks(db)
    elif args.stats:
        show_stats(db)
    elif args.coach:
        ai_coach(db)
    elif args.report:
        ai_report(db, args.report)
    elif args.suggest:
        ai_suggest(db)
    db.close()


if __name__ == "__main__":
    main()
