#!/usr/bin/env python3
"""Smart File Organizer - AI-powered file organization tool.

Uses Ollama LLM to classify files by name, extension, and content.
Supports watching directories, one-time organization, custom rules, and undo.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Configuration ---
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"
SCRIPT_DIR = Path(__file__).parent
MOVES_LOG = SCRIPT_DIR / "moves.log"
DEFAULT_RULES = SCRIPT_DIR / "rules.json"

# Default categories with their extensions
DEFAULT_CATEGORIES = {
    "Documents": [".doc", ".docx", ".txt", ".rtf", ".odt", ".pages", ".tex", ".md"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".ico", ".heic"],
    "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".aiff"],
    "Code": [".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".sh", ".bash", ".zsh", ".html", ".css", ".scss", ".json", ".xml", ".yaml", ".yml", ".toml"],
    "Archives": [".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz", ".tgz"],
    "Spreadsheets": [".xls", ".xlsx", ".csv", ".ods", ".numbers"],
    "Presentations": [".ppt", ".pptx", ".key", ".odp"],
    "PDFs": [".pdf"],
    "Other": []
}


def notify_macos(title: str, message: str):
    """Send macOS notification."""
    try:
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}"'
        ], capture_output=True, timeout=5)
    except Exception:
        pass


def query_ollama(prompt: str) -> str:
    """Query Ollama LLM for file classification."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        print("⚠️  Ollama not available at localhost:11434. Using extension-based classification.")
        return ""
    except Exception as e:
        print(f"⚠️  Ollama error: {e}")
        return ""


def classify_by_extension(filepath: Path, rules: dict) -> str:
    """Classify file by its extension using rules."""
    ext = filepath.suffix.lower()
    categories = rules.get("categories", DEFAULT_CATEGORIES)
    for category, extensions in categories.items():
        if ext in extensions:
            return category
    return "Other"


def classify_by_ai(filepath: Path, read_content: bool = False) -> str:
    """Use AI to classify a file by name and optionally content."""
    filename = filepath.name
    ext = filepath.suffix.lower()

    content_snippet = ""
    if read_content and ext in [".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".json", ".csv", ".xml", ".yaml", ".yml", ".sh", ".log", ".rtf", ".tex"]:
        try:
            text = filepath.read_text(encoding="utf-8", errors="ignore")[:2000]
            content_snippet = f"\nFile content (first 2000 chars):\n{text}"
        except Exception:
            pass

    categories_list = ", ".join(DEFAULT_CATEGORIES.keys())
    prompt = f"""Classify this file into exactly one category. 
Available categories: {categories_list}

Filename: {filename}
Extension: {ext}{content_snippet}

Respond with ONLY the category name, nothing else."""

    result = query_ollama(prompt)

    # Validate response is a known category
    for cat in DEFAULT_CATEGORIES.keys():
        if cat.lower() in result.lower():
            return cat
    return ""


def smart_classify(filepath: Path) -> str:
    """Use AI to classify file by reading its content and categorizing by topic."""
    ext = filepath.suffix.lower()
    readable_exts = [".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".json", ".csv", ".xml", ".yaml", ".yml", ".sh", ".log", ".rtf", ".tex", ".doc", ".pdf"]

    content_snippet = ""
    if ext in readable_exts:
        try:
            text = filepath.read_text(encoding="utf-8", errors="ignore")[:3000]
            content_snippet = text
        except Exception:
            pass

    if not content_snippet:
        return classify_by_extension(filepath, {"categories": DEFAULT_CATEGORIES})

    prompt = f"""Analyze this file's content and classify it into a topic-based category.

Filename: {filepath.name}
Content:
{content_snippet}

Suggest a specific topic category (e.g., "Finance", "Health", "Work", "Personal", "Education", "Travel", "Recipes", "Projects", "Research", "Notes").
Respond with ONLY the category name, nothing else."""

    result = query_ollama(prompt)
    if result and len(result) < 30:
        return result.strip().title()
    return classify_by_extension(filepath, {"categories": DEFAULT_CATEGORIES})


def load_rules(rules_path: str = None) -> dict:
    """Load organization rules from JSON file."""
    path = Path(rules_path) if rules_path else DEFAULT_RULES
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Error loading rules: {e}")
    return {"categories": DEFAULT_CATEGORIES}


def log_move(src: str, dst: str):
    """Log a file move for undo capability."""
    timestamp = datetime.now().isoformat()
    with open(MOVES_LOG, "a") as f:
        f.write(json.dumps({"time": timestamp, "src": src, "dst": dst}) + "\n")


def organize_file(filepath: Path, target_dir: Path, category: str, dry_run: bool = False) -> bool:
    """Move a file to its category directory."""
    category_dir = target_dir / category
    dest = category_dir / filepath.name

    # Handle name conflicts
    if dest.exists():
        stem = filepath.stem
        ext = filepath.suffix
        counter = 1
        while dest.exists():
            dest = category_dir / f"{stem}_{counter}{ext}"
            counter += 1

    if dry_run:
        print(f"  📁 {filepath.name} → {category}/{dest.name}")
        return True

    category_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(filepath), str(dest))
        log_move(str(dest), str(filepath))
        print(f"  ✅ {filepath.name} → {category}/{dest.name}")
        return True
    except Exception as e:
        print(f"  ❌ Error moving {filepath.name}: {e}")
        return False


def organize_directory(directory: str, rules: dict, dry_run: bool = False, smart: bool = False, use_ai: bool = True):
    """Organize all files in a directory."""
    dir_path = Path(directory).resolve()
    if not dir_path.is_dir():
        print(f"❌ Directory not found: {directory}")
        sys.exit(1)

    files = [f for f in dir_path.iterdir() if f.is_file() and not f.name.startswith(".")]

    if not files:
        print("📂 No files to organize.")
        return

    mode = "DRY RUN" if dry_run else "ORGANIZING"
    print(f"\n🗂️  {mode}: {dir_path}")
    print(f"   Found {len(files)} files\n")

    moved_count = 0
    for filepath in sorted(files):
        if smart:
            category = smart_classify(filepath)
        elif use_ai:
            category = classify_by_ai(filepath, read_content=True)
            if not category:
                category = classify_by_extension(filepath, rules)
        else:
            category = classify_by_extension(filepath, rules)

        if organize_file(filepath, dir_path, category, dry_run):
            moved_count += 1

    print(f"\n{'📋 Would move' if dry_run else '✅ Moved'} {moved_count}/{len(files)} files.")

    if not dry_run and moved_count > 0:
        notify_macos("Smart File Organizer", f"Organized {moved_count} files in {dir_path.name}")


def undo_last():
    """Undo the last organization by reading moves.log."""
    if not MOVES_LOG.exists():
        print("❌ No moves.log found. Nothing to undo.")
        return

    with open(MOVES_LOG) as f:
        lines = f.readlines()

    if not lines:
        print("❌ moves.log is empty. Nothing to undo.")
        return

    # Group moves by session (last batch of moves within 60 seconds)
    moves = [json.loads(line) for line in lines if line.strip()]
    if not moves:
        print("❌ No valid moves found.")
        return

    # Find last session (moves within 60 seconds of the last move)
    last_time = datetime.fromisoformat(moves[-1]["time"])
    session_moves = []
    for move in reversed(moves):
        move_time = datetime.fromisoformat(move["time"])
        if (last_time - move_time).total_seconds() <= 300:  # 5-minute window
            session_moves.append(move)
        else:
            break

    print(f"\n↩️  Undoing {len(session_moves)} moves...")
    undone = 0
    for move in session_moves:
        src = Path(move["src"])  # current location
        dst = Path(move["dst"])  # original location
        if src.exists():
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                print(f"  ↩️  {src.name} → {dst.parent.name}/")
                undone += 1
            except Exception as e:
                print(f"  ❌ Error: {e}")
        else:
            print(f"  ⚠️  File not found: {src}")

    # Remove undone entries from log
    remaining = moves[:-len(session_moves)] if len(session_moves) < len(moves) else []
    with open(MOVES_LOG, "w") as f:
        for move in remaining:
            f.write(json.dumps(move) + "\n")

    print(f"\n✅ Undone {undone}/{len(session_moves)} moves.")
    # Clean up empty category directories
    if session_moves:
        first_src = Path(session_moves[0]["src"])
        parent = first_src.parent.parent
        for d in parent.iterdir():
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
                print(f"  🗑️  Removed empty directory: {d.name}/")

    notify_macos("Smart File Organizer", f"Undone {undone} moves")


class FileOrganizerHandler(FileSystemEventHandler):
    """Watchdog handler for auto-organizing new files."""

    def __init__(self, watch_dir: str, rules: dict, smart: bool = False):
        self.watch_dir = Path(watch_dir).resolve()
        self.rules = rules
        self.smart = smart
        self.cooldown = {}

    def on_created(self, event):
        if event.is_directory:
            return

        filepath = Path(event.src_path)
        if filepath.name.startswith("."):
            return

        # Ignore files in category subdirectories
        if filepath.parent != self.watch_dir:
            return

        # Cooldown to avoid processing partial writes
        now = time.time()
        if filepath.name in self.cooldown and (now - self.cooldown[filepath.name]) < 2:
            return
        self.cooldown[filepath.name] = now

        # Wait for file to finish writing
        time.sleep(1)

        if not filepath.exists():
            return

        print(f"\n📥 New file detected: {filepath.name}")

        if self.smart:
            category = smart_classify(filepath)
        else:
            category = classify_by_ai(filepath, read_content=True)
            if not category:
                category = classify_by_extension(filepath, self.rules)

        organize_file(filepath, self.watch_dir, category)
        notify_macos("Smart File Organizer", f"Organized: {filepath.name} → {category}/")


def watch_directory(directory: str, rules: dict, smart: bool = False):
    """Watch a directory for new files and auto-organize them."""
    dir_path = Path(directory).resolve()
    if not dir_path.is_dir():
        print(f"❌ Directory not found: {directory}")
        sys.exit(1)

    print(f"\n👁️  Watching: {dir_path}")
    print(f"   Mode: {'Smart (AI topic)' if smart else 'AI + Extension'}")
    print("   Press Ctrl+C to stop\n")

    handler = FileOrganizerHandler(directory, rules, smart)
    observer = Observer()
    observer.schedule(handler, str(dir_path), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped watching.")
        observer.stop()
    observer.join()


def main():
    parser = argparse.ArgumentParser(
        description="🗂️  Smart File Organizer - AI-powered file organization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --organize ~/Downloads
  %(prog)s --organize ~/Downloads --dry-run
  %(prog)s --organize ~/Downloads --smart
  %(prog)s --watch ~/Downloads
  %(prog)s --undo
  %(prog)s --organize ~/Downloads --rules custom_rules.json
        """
    )

    parser.add_argument("--watch", metavar="DIR", help="Watch directory for new files and auto-organize")
    parser.add_argument("--organize", metavar="DIR", help="One-time organize existing files in directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be moved without actually moving")
    parser.add_argument("--rules", metavar="JSON", help="Path to custom organization rules JSON")
    parser.add_argument("--smart", action="store_true", help="Use AI to categorize by topic (reads file content)")
    parser.add_argument("--undo", action="store_true", help="Undo last organization")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI classification, use only extensions")

    args = parser.parse_args()

    if not any([args.watch, args.organize, args.undo]):
        parser.print_help()
        sys.exit(0)

    rules = load_rules(args.rules)

    if args.undo:
        undo_last()
    elif args.organize:
        organize_directory(args.organize, rules, dry_run=args.dry_run, smart=args.smart, use_ai=not args.no_ai)
    elif args.watch:
        watch_directory(args.watch, rules, smart=args.smart)


if __name__ == "__main__":
    main()
