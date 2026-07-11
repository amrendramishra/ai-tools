#!/usr/bin/env python3
"""
AI Comment Responder - Analyzes YouTube comments and generates appropriate responses
using Ollama AI with channel-specific personas.
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2"
PERSONAS_FILE = Path(__file__).parent / "personas.json"


def load_personas() -> dict:
    """Load channel-specific personas."""
    if PERSONAS_FILE.exists():
        with open(PERSONAS_FILE, "r") as f:
            return json.load(f)
    return {}


def query_ollama(prompt: str) -> str:
    """Send a query to Ollama."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to Ollama at localhost:11434")
        print("Make sure Ollama is running: ollama serve")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("Error: Request to Ollama timed out.")
        sys.exit(1)
    except Exception as e:
        print(f"Error communicating with Ollama: {e}")
        sys.exit(1)


def analyze_sentiment(comment: str) -> dict:
    """Analyze the sentiment and type of a comment."""
    prompt = f"""Analyze this YouTube comment and classify it. Respond ONLY with a JSON object (no other text):

Comment: "{comment}"

Classify into exactly one primary category:
- positive: Praise, compliments, appreciation
- negative: Criticism, complaints, dissatisfaction
- question: Asking something, seeking information
- spam: Promotional, irrelevant, bot-like content
- constructive: Helpful feedback with specific suggestions

Also provide:
- sentiment_score: -1.0 to 1.0 (negative to positive)
- is_spam: true/false
- requires_response: true/false (spam usually doesn't need response)
- topics: list of topics mentioned

JSON format:
{{"category": "...", "sentiment_score": 0.0, "is_spam": false, "requires_response": true, "topics": ["..."]}}"""

    response = query_ollama(prompt)

    # Parse JSON from response
    try:
        # Try to find JSON in the response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass

    # Fallback classification
    return {
        "category": "positive",
        "sentiment_score": 0.0,
        "is_spam": False,
        "requires_response": True,
        "topics": [],
    }


def generate_response(comment: str, sentiment: dict, channel: str = None) -> str:
    """Generate an appropriate response to a comment."""
    personas = load_personas()
    persona = personas.get("channels", {}).get(channel, personas.get("default", {}))

    tone = persona.get("tone", "friendly and professional")
    style = persona.get("style", "conversational")
    sign_off = persona.get("sign_off", "")
    language = persona.get("language", "English")
    guidelines = persona.get("guidelines", [])

    category = sentiment.get("category", "positive")
    guidelines_text = "\n".join(f"- {g}" for g in guidelines) if guidelines else "- Be helpful and engaging"

    prompt = f"""Generate a YouTube comment reply with these specifications:

ORIGINAL COMMENT: "{comment}"
COMMENT TYPE: {category}
SENTIMENT SCORE: {sentiment.get('sentiment_score', 0)}

CHANNEL PERSONA:
- Tone: {tone}
- Style: {style}
- Language: {language}
- Guidelines:
{guidelines_text}

RESPONSE RULES:
1. If the comment is a QUESTION: Answer it helpfully and accurately
2. If POSITIVE: Thank them warmly, engage further
3. If NEGATIVE: Acknowledge their concern, be empathetic, offer to help
4. If CONSTRUCTIVE: Thank for feedback, explain how you'll use it
5. If SPAM: Return "SPAM_SKIP"

Keep the response:
- Under 150 words
- Authentic and human-sounding (not generic/robotic)
- Matching the persona tone
- Including a call-to-action when appropriate (subscribe, check out, etc.)
{f'- End with: {sign_off}' if sign_off else ''}

Generate ONLY the reply text, nothing else."""

    response = query_ollama(prompt)
    return response.strip()


def is_spam(sentiment: dict) -> bool:
    """Check if a comment is classified as spam."""
    return sentiment.get("is_spam", False) or sentiment.get("category") == "spam"


def process_comment(comment: str, channel: str = None) -> dict:
    """Process a single comment: analyze and generate response."""
    sentiment = analyze_sentiment(comment)

    if is_spam(sentiment):
        return {
            "comment": comment,
            "sentiment": sentiment,
            "response": None,
            "status": "spam_filtered",
        }

    response = generate_response(comment, sentiment, channel)

    if "SPAM_SKIP" in response:
        return {
            "comment": comment,
            "sentiment": sentiment,
            "response": None,
            "status": "spam_filtered",
        }

    return {
        "comment": comment,
        "sentiment": sentiment,
        "response": response,
        "status": "response_generated",
    }


def load_comments_from_file(file_path: str) -> list:
    """Load comments from a CSV or JSON file."""
    path = Path(file_path)

    if not path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    if path.suffix.lower() == ".json":
        with open(path, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            # Handle list of strings or list of dicts
            comments = []
            for item in data:
                if isinstance(item, str):
                    comments.append(item)
                elif isinstance(item, dict):
                    comments.append(item.get("comment", item.get("text", str(item))))
            return comments
        return []

    elif path.suffix.lower() == ".csv":
        comments = []
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Try common column names
                comment = (
                    row.get("comment")
                    or row.get("text")
                    or row.get("Comment")
                    or row.get("Text")
                    or row.get("content")
                    or ""
                )
                if comment:
                    comments.append(comment)
        return comments

    else:
        # Try to read as plain text, one comment per line
        with open(path, "r") as f:
            return [line.strip() for line in f if line.strip()]


def display_result(result: dict, index: int = None):
    """Display a single comment analysis result."""
    prefix = f"[{index}] " if index else ""
    sentiment = result["sentiment"]
    category = sentiment.get("category", "unknown")
    score = sentiment.get("sentiment_score", 0)

    # Category icons
    icons = {
        "positive": "😊",
        "negative": "😟",
        "question": "❓",
        "spam": "🚫",
        "constructive": "💡",
    }
    icon = icons.get(category, "💬")

    print(f"\n{prefix}{icon} [{category.upper()}] (sentiment: {score:+.1f})")
    print(f"  💬 Comment: {result['comment'][:100]}{'...' if len(result['comment']) > 100 else ''}")

    if result["status"] == "spam_filtered":
        print("  🚫 FILTERED: Spam detected, no response generated")
    else:
        print(f"  ✅ Response: {result['response']}")


def interactive_approve(results: list) -> list:
    """Interactive mode to approve/edit/skip each response."""
    approved = []
    print("\n" + "=" * 60)
    print("📝 INTERACTIVE APPROVAL MODE")
    print("=" * 60)
    print("Commands: [a]pprove, [e]dit, [s]kip, [q]uit\n")

    for i, result in enumerate(results, 1):
        if result["status"] == "spam_filtered":
            print(f"[{i}/{len(results)}] 🚫 Spam filtered - auto-skipped")
            continue

        display_result(result, i)
        print()

        while True:
            choice = input(f"  [{i}/{len(results)}] Action (a/e/s/q): ").strip().lower()

            if choice == "a":
                approved.append(result)
                print("  ✓ Approved")
                break
            elif choice == "e":
                new_response = input("  New response: ").strip()
                if new_response:
                    result["response"] = new_response
                    result["status"] = "manually_edited"
                    approved.append(result)
                    print("  ✓ Edited and approved")
                break
            elif choice == "s":
                print("  ⏭️  Skipped")
                break
            elif choice == "q":
                print("\n  Quitting approval mode.")
                return approved
            else:
                print("  Invalid choice. Use: a (approve), e (edit), s (skip), q (quit)")

    return approved


def export_results(results: list, output_path: str = None):
    """Export results to CSV."""
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(Path(__file__).parent / f"responses_{timestamp}.csv")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["comment", "category", "sentiment_score", "response", "status"])

        for result in results:
            writer.writerow([
                result["comment"],
                result["sentiment"].get("category", ""),
                result["sentiment"].get("sentiment_score", 0),
                result.get("response", ""),
                result.get("status", ""),
            ])

    print(f"\n💾 Results exported to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="🤖 AI Comment Responder - Generate intelligent responses to YouTube comments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --text "Great video! Really loved the editing."
  %(prog)s --file comments.csv --channel tech_channel
  %(prog)s --file comments.json --batch --approve
  %(prog)s --paste --channel gaming_channel
        """,
    )

    # Input methods
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--text", type=str, help="Single comment text to respond to"
    )
    input_group.add_argument(
        "--file", type=str, help="Path to CSV/JSON file containing comments"
    )
    input_group.add_argument(
        "--paste", action="store_true",
        help="Paste comments interactively (one per line, empty line to finish)"
    )

    # Options
    parser.add_argument(
        "--channel", type=str, default=None,
        help="Channel name to use specific persona/tone"
    )
    parser.add_argument(
        "--batch", action="store_true",
        help="Process all comments and output response CSV"
    )
    parser.add_argument(
        "--approve", action="store_true",
        help="Interactive mode to approve/edit/skip each response"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path for CSV export"
    )

    args = parser.parse_args()

    if not any([args.text, args.file, args.paste]):
        parser.print_help()
        sys.exit(0)

    # Collect comments
    comments = []

    if args.text:
        comments = [args.text]
    elif args.file:
        comments = load_comments_from_file(args.file)
        print(f"📂 Loaded {len(comments)} comments from: {args.file}")
    elif args.paste:
        print("📋 Paste comments (one per line, empty line to finish):")
        while True:
            try:
                line = input()
                if not line.strip():
                    break
                comments.append(line.strip())
            except EOFError:
                break
        print(f"📋 Received {len(comments)} comments")

    if not comments:
        print("No comments to process.")
        sys.exit(0)

    # Process comments
    results = []
    total = len(comments)
    spam_count = 0

    print(f"\n🔄 Processing {total} comment{'s' if total > 1 else ''}...")
    if args.channel:
        print(f"📺 Using channel persona: {args.channel}")

    for i, comment in enumerate(comments, 1):
        if total > 1:
            print(f"  [{i}/{total}] Processing...", end="\r")

        result = process_comment(comment, args.channel)
        results.append(result)

        if result["status"] == "spam_filtered":
            spam_count += 1

    # Summary
    print(f"\n\n{'=' * 60}")
    print(f"📊 PROCESSING COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Total comments: {total}")
    print(f"  Responses generated: {total - spam_count}")
    print(f"  Spam filtered: {spam_count}")

    # Interactive approval mode
    if args.approve:
        results = interactive_approve(results)
        print(f"\n  Approved responses: {len(results)}")

    # Display results
    if not args.approve:
        for i, result in enumerate(results, 1):
            display_result(result, i)

    # Export if batch mode or explicit output
    if args.batch or args.output:
        export_results(results, args.output)


if __name__ == "__main__":
    main()
