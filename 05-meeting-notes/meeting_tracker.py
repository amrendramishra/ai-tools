#!/usr/bin/env python3
"""Meeting Tracker - Search, list, and summarize meeting notes."""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"
NOTES_DIR = Path.home() / "Documents" / "meeting-notes"


def call_ollama(prompt: str) -> str:
    """Call Ollama API and return the response text."""
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 2048},
    })

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip()
    except Exception as e:
        print(f"Error connecting to Ollama: {e}", file=sys.stderr)
        sys.exit(1)


def get_all_notes() -> list[dict]:
    """Get all saved meeting notes with metadata."""
    if not NOTES_DIR.exists():
        return []

    notes = []
    for filepath in sorted(NOTES_DIR.iterdir()):
        if filepath.is_file() and filepath.suffix in (".md", ".json", ".txt"):
            stat = filepath.stat()
            # Parse filename for metadata
            name = filepath.stem
            parts = name.split("_")
            template = parts[1] if len(parts) > 1 else "unknown"

            notes.append({
                "path": filepath,
                "filename": filepath.name,
                "template": template,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "content": filepath.read_text(encoding="utf-8"),
            })

    return notes


def cmd_list(args):
    """List all saved meeting notes."""
    notes = get_all_notes()

    if not notes:
        print("No meeting notes found.")
        print(f"Notes directory: {NOTES_DIR}")
        return

    print(f"📋 Meeting Notes ({len(notes)} total)")
    print(f"   Directory: {NOTES_DIR}")
    print("=" * 70)
    print(f"{'#':<4} {'Date':<20} {'Template':<12} {'Size':<10} {'Filename'}")
    print("-" * 70)

    for i, note in enumerate(notes, 1):
        date_str = note["modified"].strftime("%Y-%m-%d %H:%M")
        size_str = f"{note['size']:,}B"
        print(f"{i:<4} {date_str:<20} {note['template']:<12} {size_str:<10} {note['filename']}")

    print("-" * 70)


def cmd_search(args):
    """Search across all meeting notes."""
    query = args.search.lower()
    notes = get_all_notes()

    if not notes:
        print("No meeting notes found.")
        return

    print(f"🔍 Searching for: '{args.search}'")
    print("=" * 60)

    matches = 0
    for note in notes:
        content_lower = note["content"].lower()
        if query in content_lower:
            matches += 1
            print(f"\n📄 {note['filename']}")
            print(f"   Date: {note['modified'].strftime('%Y-%m-%d %H:%M')} | Template: {note['template']}")

            # Show matching lines with context
            lines = note["content"].split("\n")
            for i, line in enumerate(lines):
                if query in line.lower():
                    start = max(0, i - 1)
                    end = min(len(lines), i + 2)
                    for j in range(start, end):
                        prefix = ">>>" if j == i else "   "
                        print(f"   {prefix} {lines[j][:80]}")
                    print()
                    break  # Show first match per file

    print("-" * 60)
    print(f"Found {matches} matching file(s) out of {len(notes)} total.")


def cmd_actions(args):
    """Show pending action items across all meetings."""
    notes = get_all_notes()

    if not notes:
        print("No meeting notes found.")
        return

    print("✅ Pending Action Items Across All Meetings")
    print("=" * 60)

    total_actions = 0
    for note in notes:
        content = note["content"]
        # Extract action items section
        action_lines = []
        in_actions = False

        for line in content.split("\n"):
            lower_line = line.lower().strip()
            if "action items" in lower_line and ("#" in line or lower_line.startswith("action")):
                in_actions = True
                continue
            elif in_actions and (line.startswith("##") or line.startswith("=") or
                                 (lower_line and not lower_line.startswith("-") and
                                  not lower_line.startswith("*") and
                                  "no action" in lower_line)):
                if "no action" in lower_line:
                    in_actions = False
                    break
                if line.startswith("##") or line.startswith("="):
                    in_actions = False
                    break
            elif in_actions and line.strip().startswith(("-", "*")):
                action_lines.append(line.strip())

        if action_lines:
            total_actions += len(action_lines)
            date_str = note["modified"].strftime("%Y-%m-%d")
            print(f"\n📄 {note['filename']} ({date_str})")
            for action in action_lines:
                print(f"   {action}")

    print("\n" + "-" * 60)
    if total_actions == 0:
        print("No pending action items found.")
    else:
        print(f"Total: {total_actions} action item(s) across {len(notes)} meeting(s).")


def cmd_weekly(args):
    """Generate weekly summary of all meetings."""
    notes = get_all_notes()

    if not notes:
        print("No meeting notes found.")
        return

    # Filter to last 7 days
    cutoff = datetime.now() - timedelta(days=7)
    weekly_notes = [n for n in notes if n["modified"] >= cutoff]

    if not weekly_notes:
        print("No meeting notes from the past 7 days.")
        return

    print(f"📊 Weekly Meeting Summary ({len(weekly_notes)} meetings)")
    print(f"   Period: {cutoff.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 60)

    # Combine all notes content for AI summary
    combined = ""
    for note in weekly_notes:
        combined += f"\n--- Meeting: {note['filename']} ({note['modified'].strftime('%Y-%m-%d')}) ---\n"
        combined += note["content"][:1500] + "\n"

    if len(combined) > 6000:
        combined = combined[:6000]

    prompt = f"""Summarize the following week's meeting notes into a brief weekly report.
Include: overall themes, key decisions across meetings, outstanding action items, and priorities for next week.
Keep it concise but comprehensive.

{combined}

Weekly summary:"""

    print("\n🤖 Generating weekly summary with AI...\n")
    summary = call_ollama(prompt)
    print(summary)
    print("\n" + "=" * 60)

    # Also show basic stats
    print("\n📈 Stats:")
    templates_used = {}
    for note in weekly_notes:
        templates_used[note["template"]] = templates_used.get(note["template"], 0) + 1
    for tpl, count in sorted(templates_used.items()):
        print(f"   {tpl}: {count} meeting(s)")


def cmd_show(args):
    """Show content of a specific meeting note."""
    notes = get_all_notes()
    if not notes:
        print("No meeting notes found.")
        return

    idx = args.number - 1
    if idx < 0 or idx >= len(notes):
        print(f"Error: Invalid note number. Choose 1-{len(notes)}.")
        return

    note = notes[idx]
    print(f"📄 {note['filename']}")
    print("=" * 60)
    print(note["content"])


def _set_model(model: str):
    """Update the module-level MODEL variable."""
    global MODEL
    MODEL = model


def main():
    parser = argparse.ArgumentParser(
        description="Meeting Tracker - Manage and search meeting notes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s list                   - List all meeting notes
  %(prog)s search "deployment"    - Search across all notes
  %(prog)s actions                - Show pending action items
  %(prog)s weekly                 - Generate weekly summary
  %(prog)s show 3                 - Show meeting note #3""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list
    subparsers.add_parser("list", help="List all saved meeting notes")

    # search
    search_parser = subparsers.add_parser("search", help="Search across meeting notes")
    search_parser.add_argument("search", help="Search query")

    # actions
    subparsers.add_parser("actions", help="Show pending action items across all meetings")

    # weekly
    subparsers.add_parser("weekly", help="Generate weekly summary of all meetings")

    # show
    show_parser = subparsers.add_parser("show", help="Show a specific meeting note")
    show_parser.add_argument("number", type=int, help="Note number (from list command)")

    parser.add_argument("--model", "-m", default=MODEL, help=f"Ollama model (default: {MODEL})")

    args = parser.parse_args()

    _set_model(args.model)

    if args.command == "list":
        cmd_list(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "actions":
        cmd_actions(args)
    elif args.command == "weekly":
        cmd_weekly(args)
    elif args.command == "show":
        cmd_show(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
