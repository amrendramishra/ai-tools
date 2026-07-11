#!/usr/bin/env python3
"""AI Email Responder - Analyze emails and generate response options using Ollama."""

import argparse
import json
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2"
TEMPLATES_FILE = Path(__file__).parent / "templates.json"


def load_templates():
    """Load email response templates."""
    if TEMPLATES_FILE.exists():
        with open(TEMPLATES_FILE) as f:
            return json.load(f)
    return {}


def get_clipboard_content():
    """Get content from macOS clipboard."""
    result = subprocess.run(["pbpaste"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout
    print("Failed to read clipboard.", file=sys.stderr)
    sys.exit(1)


def copy_to_clipboard(text):
    """Copy text to macOS clipboard."""
    process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
    process.communicate(text.encode("utf-8"))
    if process.returncode == 0:
        print("\n📋 Response copied to clipboard!")
    else:
        print("Failed to copy to clipboard.", file=sys.stderr)


def query_ollama(prompt, system_prompt=""):
    """Send a prompt to Ollama and get a response."""
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    if system_prompt:
        payload["system"] = system_prompt

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "No response received.")
    except urllib.error.URLError as e:
        print(f"Error connecting to Ollama at {OLLAMA_URL}: {e}", file=sys.stderr)
        print("Make sure Ollama is running: ollama serve", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def analyze_email(email_content):
    """Analyze an email for tone, urgency, key points, and required actions."""
    system_prompt = (
        "You are an email analysis assistant. Analyze the given email and provide "
        "a structured breakdown. Be concise and actionable."
    )
    prompt = f"""Analyze this email and provide:

1. **Tone**: (e.g., formal, casual, urgent, friendly, demanding)
2. **Urgency**: (Low / Medium / High / Critical)
3. **Key Points**: (bullet list of main points)
4. **Required Action**: (what the sender expects from you)
5. **Sentiment**: (positive, neutral, negative)

Email:
---
{email_content}
---"""
    return query_ollama(prompt, system_prompt)


def generate_responses(email_content, tone="professional", context=""):
    """Generate three response options: brief, detailed, and decline."""
    context_note = ""
    if context:
        context_note = f"\nAdditional context: {context}"

    system_prompt = (
        f"You are an email response assistant. Generate responses in a {tone} tone. "
        "Be natural and human-sounding. Do not include subject lines."
    )

    responses = {}

    prompt = f"""Write a brief, concise reply (2-3 sentences max).
Tone: {tone}{context_note}

Original email:
---
{email_content}
---

Brief reply:"""
    responses["brief"] = query_ollama(prompt, system_prompt)

    prompt = f"""Write a detailed, thorough reply addressing all points.
Tone: {tone}{context_note}

Original email:
---
{email_content}
---

Detailed reply:"""
    responses["detailed"] = query_ollama(prompt, system_prompt)

    prompt = f"""Write a polite decline/rejection reply. Be respectful but clear.
Tone: {tone}{context_note}

Original email:
---
{email_content}
---

Decline reply:"""
    responses["decline"] = query_ollama(prompt, system_prompt)

    return responses


def interactive_refine(response, email_content, tone):
    """Interactively refine a response with user feedback."""
    current = response
    while True:
        print("\n" + "-" * 50)
        print("Current response:")
        print("-" * 50)
        print(current)
        print("-" * 50)
        print("\nOptions:")
        print("  [enter] Accept this response")
        print("  [r]     Rewrite with new instructions")
        print("  [s]     Make it shorter")
        print("  [l]     Make it longer")
        print("  [q]     Quit without copying")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "":
            return current
        elif choice == "q":
            return ""
        elif choice == "s":
            prompt = f"Make this shorter while keeping the same meaning:\n\n{current}"
            current = query_ollama(prompt)
        elif choice == "l":
            prompt = f"Expand this with more detail, same tone:\n\n{current}"
            current = query_ollama(prompt)
        elif choice == "r":
            instruction = input("How should I change it? ")
            prompt = (
                f"Rewrite based on: {instruction}\n\n"
                f"Current:\n{current}\n\nOriginal email:\n{email_content}"
            )
            current = query_ollama(prompt)
        else:
            print("Invalid option.")


def display_responses(responses):
    """Display the three response options."""
    labels = {
        "brief": "📝 Brief Response",
        "detailed": "📄 Detailed Response",
        "decline": "🚫 Decline Response",
    }
    for key, label in labels.items():
        print(f"\n{'=' * 60}")
        print(f"  {label}")
        print(f"{'=' * 60}")
        print(responses[key])
    print(f"\n{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(
        description="AI Email Responder - Analyze and respond to emails using Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --paste                           # Read email from clipboard
  %(prog)s --file email.txt                  # Read email from file
  echo "email text" | %(prog)s              # Read from stdin
  %(prog)s --paste --tone casual             # Casual tone
  %(prog)s --paste --context "I'm busy"      # Add context
  %(prog)s --paste --analyze-only            # Only analyze
        """,
    )

    input_group = parser.add_argument_group("Input")
    input_group.add_argument("--file", type=str, help="Read email from a file")
    input_group.add_argument("--paste", action="store_true", help="Read from clipboard")

    opts = parser.add_argument_group("Options")
    opts.add_argument(
        "--tone", choices=["professional", "casual", "friendly"],
        default="professional", help="Response tone (default: professional)",
    )
    opts.add_argument("--context", type=str, default="", help="Additional context")
    opts.add_argument("--analyze-only", action="store_true", help="Only analyze")
    opts.add_argument("--no-interactive", action="store_true", help="Skip refinement")

    args = parser.parse_args()

    # Get email content
    email_content = ""
    if args.paste:
        email_content = get_clipboard_content()
    elif args.file:
        p = Path(args.file)
        if not p.exists():
            print(f"File not found: {p}", file=sys.stderr)
            sys.exit(1)
        email_content = p.read_text()
    elif not sys.stdin.isatty():
        email_content = sys.stdin.read()
    else:
        print("No email content provided. Use --paste, --file, or pipe via stdin.",
              file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    if not email_content.strip():
        print("Email content is empty.", file=sys.stderr)
        sys.exit(1)

    print("📧 AI Email Responder")
    print("=" * 40)

    # Analyze
    print("\n🔍 Analyzing email...")
    analysis = analyze_email(email_content)
    print("\n📊 Email Analysis:")
    print("-" * 40)
    print(analysis)

    if args.analyze_only:
        return

    # Generate responses
    print("\n✍️  Generating response options...")
    responses = generate_responses(email_content, args.tone, args.context)
    display_responses(responses)

    if args.no_interactive:
        print("\nWhich response to copy? [1] Brief  [2] Detailed  [3] Decline  [q] Quit")
        choice = input("Choice: ").strip()
        choice_map = {"1": "brief", "2": "detailed", "3": "decline"}
        if choice in choice_map:
            copy_to_clipboard(responses[choice_map[choice]])
        return

    # Interactive mode
    print("\nWhich response to use? [1] Brief  [2] Detailed  [3] Decline  [q] Quit")
    choice = input("Choice: ").strip()

    choice_map = {"1": "brief", "2": "detailed", "3": "decline"}
    if choice not in choice_map:
        print("👋 Goodbye!")
        return

    selected = responses[choice_map[choice]]
    refined = interactive_refine(selected, email_content, args.tone)
    if refined:
        copy_to_clipboard(refined)
    else:
        print("👋 Response discarded.")


if __name__ == "__main__":
    main()
