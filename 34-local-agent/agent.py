#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
Local AI Agent with Memory - Gets smarter the more you use it.
Learns about you, detects patterns, and provides personalized assistance.
"""

import argparse
import json
import sys
import uuid
import requests
from datetime import datetime
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))
from memory_engine import MemoryEngine

# Config
CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    """Load agent configuration."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


CONFIG = load_config()
OLLAMA_URL = CONFIG["agent"]["ollama_url"]
MODEL = CONFIG["agent"]["model"]

# Initialize memory engine
DB_PATH = Path(__file__).parent / CONFIG["memory"]["db_path"]
memory = MemoryEngine(str(DB_PATH))


def call_ollama(prompt: str, system: str = None, temperature: float = None) -> str:
    """Call Ollama API for text generation."""
    if temperature is None:
        temperature = CONFIG["agent"]["temperature"]

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature}
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["response"].strip()
    except requests.exceptions.ConnectionError:
        return "[Error: Cannot connect to Ollama at localhost:11434. Is it running?]"
    except Exception as e:
        return f"[Error: {e}]"


def build_system_prompt() -> str:
    """Build context-aware system prompt."""
    context = memory.get_context_summary()
    template = CONFIG["system_prompt_template"]

    # Format user facts
    facts_str = ""
    for cat, items in context["user_facts"].items():
        facts_str += f"\n  [{cat}]: " + "; ".join(items[:5])

    if not facts_str:
        facts_str = "\n  (No facts learned yet - this is a new user)"

    # Format patterns
    patterns_str = ""
    for p in context["patterns"][:5]:
        patterns_str += f"\n  - {p['desc']} (confidence: {p['confidence']:.0%})"

    if not patterns_str:
        patterns_str = "\n  (No patterns detected yet)"

    system = template.format(
        name=CONFIG["agent"]["name"],
        personality=CONFIG["agent"]["personality"],
        time=context["time_context"]["current_time"],
        day=context["time_context"]["day_of_week"],
        user_facts=facts_str,
        patterns=patterns_str,
    )

    # Add stats
    stats = context["stats"]
    system += f"\n\nStats: {stats['total_interactions']} interactions, {stats['facts_known']} facts known, {stats['patterns_detected']} patterns detected."

    return system


def extract_facts_from_response(user_msg: str, ai_response: str):
    """Use AI to extract learnable facts from a conversation exchange."""
    if not CONFIG["memory"]["auto_extract_facts"]:
        return

    extraction_prompt = f"""Analyze this conversation and extract any facts about the user.
Return ONLY a JSON array of objects with keys: category, key, value
Categories: preferences, habits, personal, work, interests, schedule, goals

User said: "{user_msg}"
AI responded: "{ai_response}"

If no facts can be extracted, return an empty array: []
Return ONLY valid JSON, nothing else."""

    result = call_ollama(extraction_prompt, temperature=0.1)

    try:
        # Try to extract JSON from response
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]

        facts = json.loads(result)
        if isinstance(facts, list):
            for fact in facts:
                if all(k in fact for k in ("category", "key", "value")):
                    memory.learn_fact(
                        category=fact["category"],
                        key=fact["key"],
                        value=fact["value"],
                        confidence=0.6,
                        source="auto_extraction"
                    )
    except (json.JSONDecodeError, KeyError):
        pass  # Extraction failed silently


def detect_time_patterns():
    """Detect patterns based on interaction timing."""
    now = datetime.now()
    hour = now.hour
    day = now.strftime("%A")

    # Record usage pattern
    if 6 <= hour < 9:
        memory.record_pattern("work_hours", f"Active early morning on {day}s",
                              {"hour": hour, "day": day})
    elif 9 <= hour < 17:
        memory.record_pattern("work_hours", f"Active during work hours on {day}s",
                              {"hour": hour, "day": day})
    elif 17 <= hour < 22:
        memory.record_pattern("work_hours", f"Active in evenings on {day}s",
                              {"hour": hour, "day": day})
    elif hour >= 22 or hour < 6:
        memory.record_pattern("work_hours", f"Night owl - active late on {day}s",
                              {"hour": hour, "day": day})


def cmd_chat():
    """Interactive chat mode with memory."""
    session_id = str(uuid.uuid4())[:8]
    memory.start_session(session_id)
    detect_time_patterns()

    context = memory.get_context_summary()
    time_of_day = context["time_context"]["time_of_day"]
    name = CONFIG["agent"]["name"]

    # Personalized greeting
    facts = memory.get_facts(limit=1)
    if facts:
        print(f"\n🤖 {name}: Hey! Good {time_of_day}. Ready to help — I remember our past conversations.")
    else:
        print(f"\n🤖 {name}: Hey there! I'm {name}, your personal AI. I learn and adapt to you over time.")
        print(f"   The more we chat, the smarter I get about what you need. Let's go!\n")

    print("   (Type 'quit' or 'exit' to end, 'memory' to see what I know)\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print(f"\n🤖 {name}: Catch you later! I'll remember everything from today. 👋\n")
            break
        if user_input.lower() == "memory":
            cmd_memory()
            continue

        # Store user interaction
        memory.store_interaction("user", user_input, session_id=session_id)

        # Get recent context for conversation
        recent = memory.get_recent_interactions(limit=CONFIG["memory"]["context_window_interactions"],
                                                session_id=session_id)

        # Build conversation context
        conversation = ""
        for msg in recent[:-1]:  # Exclude the one we just added
            role = "User" if msg["role"] == "user" else name
            conversation += f"{role}: {msg['content']}\n"

        prompt = f"{conversation}User: {user_input}\n{name}:"

        # Generate response
        system = build_system_prompt()
        response = call_ollama(prompt, system=system)

        print(f"\n🤖 {name}: {response}\n")

        # Store AI response
        memory.store_interaction("assistant", response, session_id=session_id)

        # Extract facts in background (non-blocking would be ideal, but keeping simple)
        extract_facts_from_response(user_input, response)

    memory.end_session(session_id)


def cmd_suggest():
    """Suggest actions based on patterns and time."""
    context = memory.get_context_summary()
    system = build_system_prompt()

    prompt = f"""Based on what you know about the user, the current time ({context['time_context']['current_time']} on {context['time_context']['day_of_week']}), and detected patterns, suggest 3-5 things they might want to do right now.

Be specific and actionable. Reference what you know about them.
Format as a numbered list with brief explanations."""

    suggestions = call_ollama(prompt, system=system)
    print(f"\n💡 Suggestions for you right now ({context['time_context']['current_time']}, {context['time_context']['day_of_week']}):\n")
    print(suggestions)
    print()


def cmd_teach(fact: str):
    """Explicitly teach the agent a fact."""
    # Use AI to categorize and structure the fact
    prompt = f"""The user wants to teach me this fact about themselves: "{fact}"

Categorize this into a JSON object with keys: category, key, value
Categories: preferences, habits, personal, work, interests, schedule, goals

Return ONLY valid JSON, nothing else."""

    result = call_ollama(prompt, temperature=0.1)

    try:
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]

        parsed = json.loads(result)
        memory.learn_fact(
            category=parsed.get("category", "personal"),
            key=parsed.get("key", fact[:30]),
            value=parsed.get("value", fact),
            confidence=1.0,
            source="explicit_teaching"
        )
        print(f"\n✅ Got it! I've learned: [{parsed.get('category', 'personal')}] {parsed.get('key', '')}: {parsed.get('value', fact)}")
        print("   I'll remember this going forward.\n")
    except (json.JSONDecodeError, KeyError):
        # Fallback: store raw
        memory.learn_fact("personal", fact[:50], fact, confidence=1.0, source="explicit_teaching")
        print(f"\n✅ Noted! I've stored that fact. I'll remember it.\n")


def cmd_memory():
    """Show what the agent knows about the user."""
    facts = memory.get_facts(limit=50)
    patterns = memory.get_patterns()
    predictions = memory.get_predictions()
    stats = memory.get_context_summary()["stats"]

    print("\n" + "=" * 60)
    print("🧠 WHAT I KNOW ABOUT YOU")
    print("=" * 60)

    if facts:
        # Group by category
        by_cat = {}
        for f in facts:
            cat = f["category"]
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(f)

        for cat, items in sorted(by_cat.items()):
            print(f"\n📂 {cat.upper()} ({len(items)} facts):")
            for item in items:
                conf = "●" * int(item["confidence"] * 5) + "○" * (5 - int(item["confidence"] * 5))
                print(f"   [{conf}] {item['key']}: {item['value']}")
    else:
        print("\n   No facts learned yet. Chat with me or use --teach!")

    if patterns:
        print(f"\n📊 DETECTED PATTERNS ({len(patterns)}):")
        for p in patterns[:10]:
            print(f"   🔄 {p['description']} (seen {p['occurrences']}x, confidence: {p['confidence']:.0%})")

    if predictions:
        print(f"\n🔮 PREDICTIONS:")
        for p in predictions[:5]:
            print(f"   💭 {p['prediction']} (confidence: {p['confidence']:.0%})")

    print(f"\n📈 STATS:")
    print(f"   Total interactions: {stats['total_interactions']}")
    print(f"   Facts stored: {stats['facts_known']}")
    print(f"   Patterns found: {stats['patterns_detected']}")
    print("=" * 60 + "\n")


def cmd_forget(topic: str):
    """Forget memories about a specific topic."""
    count = memory.forget_topic(topic)
    if count > 0:
        print(f"\n🗑️  Done! Removed {count} memories related to '{topic}'.")
    else:
        print(f"\n🤷 I don't have any memories specifically about '{topic}'.")
    print()


def cmd_daily_briefing():
    """Generate a personalized morning briefing."""
    context = memory.get_context_summary()
    system = build_system_prompt()

    prompt = f"""Generate a personalized daily briefing for the user. It's {context['time_context']['current_time']} on {context['time_context']['day_of_week']}, {context['time_context']['date']}.

Include:
1. A friendly greeting appropriate for the time
2. Quick recap of recent activity/what they were working on
3. Suggestions for today based on their patterns
4. Any predictions about what they might need
5. A motivational or fun closing note

Keep it concise but warm. Use what you know about them. If you don't know much yet, give a general helpful briefing and invite them to chat more."""

    briefing = call_ollama(prompt, system=system)
    print(f"\n☀️  DAILY BRIEFING — {context['time_context']['day_of_week']}, {context['time_context']['date']}")
    print("─" * 50)
    print(briefing)
    print("─" * 50 + "\n")


def cmd_weekly_review():
    """Generate a weekly review of activity."""
    weekly_data = memory.get_weekly_summary()
    context = memory.get_context_summary()
    system = build_system_prompt()

    data_summary = json.dumps(weekly_data, indent=2, default=str)

    prompt = f"""Generate a weekly review based on this data:
{data_summary}

Include:
1. Activity summary (how many interactions, most active days)
2. New things learned about the user
3. Patterns that emerged or strengthened
4. Accomplishments or progress
5. Suggestions for next week

If limited data, acknowledge that and encourage more interaction.
Be specific about numbers and facts. Keep it motivating."""

    review = call_ollama(prompt, system=system)
    print("\n📊 WEEKLY REVIEW")
    print("═" * 50)
    print(review)
    print("═" * 50 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description=f"🤖 {CONFIG['agent']['name']} - Your Personal AI Agent with Memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --chat              Start an interactive conversation
  %(prog)s --teach 'I love Python'  Teach a fact
  %(prog)s --suggest           Get proactive suggestions
  %(prog)s --memory            See what I know about you
  %(prog)s --daily-briefing    Get your personalized briefing
  %(prog)s --forget 'work'     Remove memories about work
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--chat", action="store_true", help="Interactive conversation (I remember everything)")
    group.add_argument("--suggest", action="store_true", help="Get proactive suggestions based on time/patterns")
    group.add_argument("--teach", type=str, metavar="FACT", help="Explicitly teach me something")
    group.add_argument("--memory", action="store_true", help="Show what I know about you")
    group.add_argument("--forget", type=str, metavar="TOPIC", help="Remove specific memories")
    group.add_argument("--daily-briefing", action="store_true", help="Personalized morning briefing")
    group.add_argument("--weekly-review", action="store_true", help="Weekly activity review")

    args = parser.parse_args()

    if args.chat:
        cmd_chat()
    elif args.suggest:
        cmd_suggest()
    elif args.teach:
        cmd_teach(args.teach)
    elif args.memory:
        cmd_memory()
    elif args.forget:
        cmd_forget(args.forget)
    elif args.daily_briefing:
        cmd_daily_briefing()
    elif args.weekly_review:
        cmd_weekly_review()


if __name__ == "__main__":
    main()
