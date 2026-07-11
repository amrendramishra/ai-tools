#!/usr/bin/env python3
"""Personal AI Assistant - Always-on assistant with memory and rich features."""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import Optional

import requests

from memory import MemoryDB

OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assistant_memory.db")

SYSTEM_PERSONA = """You are a helpful personal AI assistant. You are friendly, proactive, and remember things about the user.
Key traits:
- Remember user preferences and past conversations
- Be concise but warm
- Offer proactive suggestions when relevant
- Use the current context (time, day) naturally
- If you learn something new about the user (name, preferences, habits), note it for memory extraction."""


def ollama_chat(messages: list, model: str = MODEL) -> str:
    """Call Ollama chat API."""
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json={
            "model": model, "messages": messages, "stream": False,
            "options": {"temperature": 0.7, "num_predict": 1024}
        }, timeout=120)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")
    except requests.exceptions.ConnectionError:
        print("\n⚠️  Cannot connect to Ollama at localhost:11434")
        print("   Make sure Ollama is running: ollama serve")
        return "I'm having trouble connecting to my AI backend. Please make sure Ollama is running."
    except Exception as e:
        return f"Error: {e}"


def ollama_generate(prompt: str, model: str = MODEL) -> str:
    """Call Ollama generate API."""
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.3, "num_predict": 512}
        }, timeout=60)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception:
        return ""


def get_system_context() -> str:
    """Get current system context (time, day, etc.)."""
    now = datetime.now()
    return f"""Current context:
- Date: {now.strftime('%A, %B %d, %Y')}
- Time: {now.strftime('%I:%M %p')}
- Day of week: {now.strftime('%A')}
- Time of day: {'morning' if now.hour < 12 else 'afternoon' if now.hour < 17 else 'evening'}"""


def extract_memories(user_message: str, assistant_response: str, memory: MemoryDB):
    """Use AI to extract memorable facts from conversation."""
    prompt = f"""From this conversation exchange, extract any facts worth remembering about the user.
Return ONLY valid JSON (or empty object if nothing to remember):
{{"facts": [{{"key": "short_key", "value": "the fact", "category": "preference|personal|work|habit"}}]}}

User said: {user_message}
Assistant said: {assistant_response}

JSON only:"""
    response = ollama_generate(prompt)
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
            for fact in data.get("facts", []):
                if fact.get("key") and fact.get("value"):
                    memory.remember(fact["key"], fact["value"],
                                    category=fact.get("category", "general"))
    except (json.JSONDecodeError, KeyError):
        pass


def parse_time(time_str: str) -> Optional[str]:
    """Parse a time string into ISO format."""
    now = datetime.now()
    time_str = time_str.lower().strip()

    # Try common patterns
    formats = ["%Y-%m-%d %H:%M", "%H:%M", "%I:%M %p", "%I%p",
               "%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d %H:%M"]

    for fmt in formats:
        try:
            parsed = datetime.strptime(time_str, fmt)
            if parsed.year == 1900:  # Time only
                parsed = parsed.replace(year=now.year, month=now.month, day=now.day)
                if parsed < now:
                    parsed += timedelta(days=1)
            return parsed.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue

    # Relative times
    if "tomorrow" in time_str:
        tomorrow = now + timedelta(days=1)
        return tomorrow.strftime("%Y-%m-%d 09:00")
    if "hour" in time_str:
        try:
            hours = int("".join(filter(str.isdigit, time_str)) or "1")
            target = now + timedelta(hours=hours)
            return target.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass
    if "minute" in time_str:
        try:
            minutes = int("".join(filter(str.isdigit, time_str)) or "30")
            target = now + timedelta(minutes=minutes)
            return target.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass

    return time_str  # Return as-is if unparsable


def show_memory(memory: MemoryDB):
    """Display what the assistant remembers."""
    memories = memory.get_all_memories()
    conv_count = memory.get_conversation_count()

    print(f"\n{'='*50}")
    print(f"  🧠 Assistant Memory")
    print(f"{'='*50}")
    print(f"\n  Total conversations: {conv_count}")
    print(f"  Stored memories: {len(memories)}\n")

    if memories:
        current_cat = ""
        for m in memories:
            if m["category"] != current_cat:
                current_cat = m["category"]
                print(f"  [{current_cat.upper()}]")
            print(f"    • {m['key']}: {m['value']}")
        print()
    else:
        print("  No memories stored yet. Start chatting!\n")


def show_schedule(memory: MemoryDB):
    """Show today's schedule and reminders."""
    today_reminders = memory.get_today_reminders()
    pending = memory.get_pending_reminders()

    print(f"\n{'='*50}")
    print(f"  📅 Schedule - {datetime.now().strftime('%A, %B %d')}")
    print(f"{'='*50}\n")

    if today_reminders:
        print("  Today's Reminders:")
        for r in today_reminders:
            print(f"    ⏰ {r['remind_at'][11:16]} - {r['text']}")
    else:
        print("  No reminders for today.")

    upcoming = [r for r in pending if r not in today_reminders]
    if upcoming[:5]:
        print("\n  Upcoming:")
        for r in upcoming[:5]:
            print(f"    📌 {r['remind_at']} - {r['text']}")
    print()


def add_reminder(text: str, at_time: str, memory: MemoryDB):
    """Add a new reminder."""
    parsed_time = parse_time(at_time)
    memory.add_reminder(text, parsed_time)
    print(f"\n  ✅ Reminder set: '{text}' at {parsed_time}\n")


def add_note(text: str, memory: MemoryDB):
    """Save a quick note."""
    memory.add_note(text)
    print(f"\n  📝 Note saved: '{text[:50]}{'...' if len(text) > 50 else ''}'\n")


def search_notes(query: str, memory: MemoryDB):
    """Search saved notes."""
    results = memory.search_notes(query)
    print(f"\n{'='*50}")
    print(f"  🔍 Notes matching: '{query}'")
    print(f"{'='*50}\n")

    if results:
        for note in results:
            print(f"  [{note['created_at']}]")
            print(f"    {note['content']}")
            print()
    else:
        print("  No matching notes found.\n")


def interactive_repl(memory: MemoryDB):
    """Run the interactive REPL."""
    session_id = str(uuid.uuid4())[:8]

    print(f"\n{'='*50}")
    print(f"  🤖 Personal AI Assistant")
    print(f"{'='*50}")
    print(f"  {get_system_context().split(chr(10))[1].strip()}")
    print(f"\n  Commands: /memory /schedule /note /remind /notes /forget /quit")
    print(f"{'='*50}\n")

    # Check for due reminders
    today_reminders = memory.get_today_reminders()
    if today_reminders:
        print(f"  ⏰ You have {len(today_reminders)} reminder(s) for today:")
        for r in today_reminders:
            print(f"     • {r['text']} (at {r['remind_at'][11:16]})")
        print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  👋 Goodbye! I'll remember our conversation.\n")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input.startswith("/"):
            cmd = user_input.lower().split()
            if cmd[0] in ("/quit", "/exit", "/q"):
                print("\n  👋 Goodbye! I'll remember our conversation.\n")
                break
            elif cmd[0] == "/memory":
                show_memory(memory)
                continue
            elif cmd[0] == "/schedule":
                show_schedule(memory)
                continue
            elif cmd[0] == "/forget":
                memory.forget_all()
                print("\n  🗑️  Memory cleared.\n")
                continue
            elif cmd[0] == "/note":
                note_text = " ".join(cmd[1:]) if len(cmd) > 1 else input("  Note: ").strip()
                if note_text:
                    add_note(note_text, memory)
                continue
            elif cmd[0] == "/notes":
                query = " ".join(cmd[1:]) if len(cmd) > 1 else ""
                if query:
                    search_notes(query, memory)
                else:
                    notes = memory.get_recent_notes()
                    if notes:
                        print("\n  📝 Recent Notes:")
                        for n in notes:
                            print(f"    [{n['created_at']}] {n['content'][:60]}")
                        print()
                    else:
                        print("\n  No notes yet.\n")
                continue
            elif cmd[0] == "/remind":
                text = " ".join(cmd[1:]) if len(cmd) > 1 else input("  Reminder text: ").strip()
                at_time = input("  When? ").strip()
                if text and at_time:
                    add_reminder(text, at_time, memory)
                continue
            else:
                print(f"  Unknown command: {cmd[0]}")
                print("  Available: /memory /schedule /note /remind /notes /forget /quit")
                continue

        # Build messages for AI
        context = memory.build_context(limit=8)
        sys_context = get_system_context()

        messages = [
            {"role": "system", "content": f"{SYSTEM_PERSONA}\n\n{sys_context}\n\n{context}"}
        ]

        # Add recent conversation
        recent = memory.get_recent_messages(limit=6)
        for msg in recent:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_input})

        # Get AI response
        response = ollama_chat(messages)
        print(f"\nAssistant: {response}\n")

        # Store conversation
        memory.add_message("user", user_input, session_id)
        memory.add_message("assistant", response, session_id)

        # Extract and store memories in background
        extract_memories(user_input, response, memory)


def main():
    parser = argparse.ArgumentParser(
        description="Personal AI Assistant - Your always-on helper with memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Start interactive mode
  %(prog)s --memory                 # Show stored memories
  %(prog)s --schedule               # Show today's schedule
  %(prog)s --remind 'Buy milk' --at '5pm'
  %(prog)s --note 'Great idea for project'
  %(prog)s --search-notes 'project'
  %(prog)s --forget                 # Clear all memory
        """)

    parser.add_argument("--memory", action="store_true", help="Show what assistant remembers")
    parser.add_argument("--forget", action="store_true", help="Clear all memory")
    parser.add_argument("--schedule", action="store_true", help="Show today's tasks/reminders")
    parser.add_argument("--remind", metavar="TEXT", help="Set a reminder")
    parser.add_argument("--at", metavar="TIME", help="Reminder time (used with --remind)")
    parser.add_argument("--note", metavar="TEXT", help="Save a quick note")
    parser.add_argument("--search-notes", metavar="QUERY", help="Search saved notes")
    parser.add_argument("--model", default=MODEL, help=f"Ollama model (default: {MODEL})")
    parser.add_argument("--db", default=DB_PATH, help="Database path")

    args = parser.parse_args()

    _apply_config(args.model, args.db)

    memory = MemoryDB(DB_PATH)

    if args.memory:
        show_memory(memory)
    elif args.forget:
        memory.forget_all()
        print("\n  🗑️  All memory cleared.\n")
    elif args.schedule:
        show_schedule(memory)
    elif args.remind:
        at_time = args.at or "1 hour"
        add_reminder(args.remind, at_time, memory)
    elif args.note:
        add_note(args.note, memory)
    elif args.search_notes:
        search_notes(args.search_notes, memory)
    else:
        interactive_repl(memory)

    memory.close()


def _apply_config(model: str, db_path: str):
    """Apply configuration from CLI args."""
    global MODEL, DB_PATH
    MODEL = model
    DB_PATH = db_path


if __name__ == "__main__":
    main()
