#!/usr/bin/env python3
"""AI Meeting Notes - Generate structured meeting notes from transcripts using Ollama."""

import argparse
import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"
OUTPUT_DIR = Path.home() / "Documents" / "meeting-notes"

TEMPLATES = {
    "general": "General meeting - capture all discussion points, decisions, and action items.",
    "standup": "Daily standup - focus on: what was done yesterday, what's planned today, and any blockers.",
    "planning": "Sprint/project planning - focus on: goals, task assignments, timelines, dependencies, and risks.",
    "retro": "Retrospective - focus on: what went well, what didn't go well, and improvement actions.",
    "1on1": "One-on-one meeting - focus on: career growth, feedback, concerns, goals, and support needed.",
}


def call_ollama(prompt: str) -> str:
    """Call Ollama API and return the response text."""
    import urllib.request
    import urllib.error

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
    except urllib.error.URLError as e:
        print(f"Error connecting to Ollama at {OLLAMA_URL}: {e}", file=sys.stderr)
        print("Make sure Ollama is running: ollama serve", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def get_transcript(args) -> str:
    """Get meeting transcript from the specified input source."""
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        return path.read_text(encoding="utf-8")
    elif args.paste:
        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
            text = result.stdout.strip()
            if not text:
                print("Error: Clipboard is empty.", file=sys.stderr)
                sys.exit(1)
            return text
        except FileNotFoundError:
            # Try xclip for Linux
            try:
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True, text=True, check=True,
                )
                return result.stdout.strip()
            except FileNotFoundError:
                print("Error: No clipboard tool found (pbpaste/xclip).", file=sys.stderr)
                sys.exit(1)
    elif args.record:
        print("=" * 50)
        print("AUDIO RECORDING (Placeholder)")
        print("=" * 50)
        print("Audio recording is not yet implemented.")
        print("This feature will use whisper for transcription.")
        print()
        print("For now, please paste your meeting notes below.")
        print("Press Ctrl+D (Unix) or Ctrl+Z (Windows) when done:")
        print("-" * 50)
        return sys.stdin.read()
    else:
        print("Enter meeting notes/transcript (Ctrl+D to finish):")
        return sys.stdin.read()


def build_prompt(transcript: str, template: str) -> str:
    """Build the AI prompt for processing meeting notes."""
    template_context = TEMPLATES.get(template, TEMPLATES["general"])

    return f"""You are a meeting notes assistant. Analyze the following meeting transcript and produce structured notes.

Meeting type: {template_context}

IMPORTANT: Respond ONLY with the structured output below. Do not add any preamble or explanation.

Produce the following sections:

## Summary
Write a concise summary of the meeting in 3-5 sentences.

## Key Decisions
List each decision made during the meeting as a bullet point. If no decisions were made, write "No decisions recorded."

## Action Items
List each action item as a bullet point in the format: "- [Assignee]: Task description (Deadline if mentioned)"
If no action items, write "No action items recorded."

## Follow-up Questions
List any unresolved questions or topics that need follow-up as bullet points. If none, write "No follow-up questions."

## Next Steps
List the next steps or upcoming milestones as bullet points. If none mentioned, write "No next steps defined."

---
MEETING TRANSCRIPT:
{transcript}
---

Structured meeting notes:"""


def parse_ai_response(response: str) -> dict:
    """Parse the AI response into structured sections."""
    sections = {
        "summary": "",
        "key_decisions": "",
        "action_items": "",
        "follow_up_questions": "",
        "next_steps": "",
    }

    current_section = None
    section_map = {
        "summary": "summary",
        "key decisions": "key_decisions",
        "action items": "action_items",
        "follow-up questions": "follow_up_questions",
        "follow up questions": "follow_up_questions",
        "next steps": "next_steps",
    }

    lines = response.split("\n")
    for line in lines:
        stripped = line.strip().lower().replace("#", "").strip()
        if stripped in section_map:
            current_section = section_map[stripped]
            continue
        if current_section:
            sections[current_section] += line + "\n"

    # Clean up trailing whitespace
    for key in sections:
        sections[key] = sections[key].strip()

    return sections


def format_markdown(sections: dict, template: str, timestamp: str) -> str:
    """Format sections as Markdown."""
    output = f"# Meeting Notes - {template.title()}\n"
    output += f"**Date:** {timestamp}\n\n"
    output += f"## Summary\n{sections['summary']}\n\n"
    output += f"## Key Decisions\n{sections['key_decisions']}\n\n"
    output += f"## Action Items\n{sections['action_items']}\n\n"
    output += f"## Follow-up Questions\n{sections['follow_up_questions']}\n\n"
    output += f"## Next Steps\n{sections['next_steps']}\n"
    return output


def format_json(sections: dict, template: str, timestamp: str) -> str:
    """Format sections as JSON."""
    data = {
        "metadata": {
            "template": template,
            "timestamp": timestamp,
            "generated_by": "ai-meeting-notes",
        },
        "summary": sections["summary"],
        "key_decisions": [
            line.lstrip("- ").strip()
            for line in sections["key_decisions"].split("\n")
            if line.strip() and line.strip().startswith("-")
        ],
        "action_items": [
            line.lstrip("- ").strip()
            for line in sections["action_items"].split("\n")
            if line.strip() and line.strip().startswith("-")
        ],
        "follow_up_questions": [
            line.lstrip("- ").strip()
            for line in sections["follow_up_questions"].split("\n")
            if line.strip() and line.strip().startswith("-")
        ],
        "next_steps": [
            line.lstrip("- ").strip()
            for line in sections["next_steps"].split("\n")
            if line.strip() and line.strip().startswith("-")
        ],
    }
    return json.dumps(data, indent=2)


def format_text(sections: dict, template: str, timestamp: str) -> str:
    """Format sections as plain text."""
    output = f"MEETING NOTES - {template.upper()}\n"
    output += f"Date: {timestamp}\n"
    output += "=" * 50 + "\n\n"
    output += f"SUMMARY\n{'-' * 30}\n{sections['summary']}\n\n"
    output += f"KEY DECISIONS\n{'-' * 30}\n{sections['key_decisions']}\n\n"
    output += f"ACTION ITEMS\n{'-' * 30}\n{sections['action_items']}\n\n"
    output += f"FOLLOW-UP QUESTIONS\n{'-' * 30}\n{sections['follow_up_questions']}\n\n"
    output += f"NEXT STEPS\n{'-' * 30}\n{sections['next_steps']}\n"
    return output


def save_output(content: str, fmt: str, template: str) -> Path:
    """Save the output to the meeting-notes directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = {"markdown": "md", "json": "json", "text": "txt"}[fmt]
    filename = f"meeting_{template}_{timestamp}.{ext}"
    filepath = OUTPUT_DIR / filename
    filepath.write_text(content, encoding="utf-8")
    return filepath


def interactive_refinement(sections: dict, transcript: str, template: str) -> dict:
    """Allow interactive refinement of the generated notes."""
    print("\n" + "=" * 50)
    print("INTERACTIVE REFINEMENT MODE")
    print("=" * 50)
    print("\nCommands:")
    print("  refine <section> - Ask AI to refine a specific section")
    print("  add <section> <text> - Manually add text to a section")
    print("  show - Display current notes")
    print("  done - Accept and save")
    print()
    print("Sections: summary, decisions, actions, questions, next_steps")
    print()

    section_alias = {
        "summary": "summary",
        "decisions": "key_decisions",
        "actions": "action_items",
        "questions": "follow_up_questions",
        "next_steps": "next_steps",
    }

    while True:
        try:
            cmd = input("\nrefine> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nDone.")
            break

        if not cmd:
            continue

        parts = cmd.split(maxsplit=2)
        action = parts[0].lower()

        if action == "done":
            break
        elif action == "show":
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            print("\n" + format_markdown(sections, template, timestamp))
        elif action == "refine" and len(parts) >= 2:
            section_key = section_alias.get(parts[1])
            if not section_key:
                print(f"Unknown section: {parts[1]}")
                continue
            print(f"Refining {parts[1]}...")
            refine_prompt = f"""Based on this meeting transcript, please improve the following section.
Make it more concise and actionable.

Current {parts[1]}:
{sections[section_key]}

Original transcript:
{transcript[:2000]}

Provide only the improved section content, nothing else:"""
            refined = call_ollama(refine_prompt)
            sections[section_key] = refined
            print(f"\nUpdated {parts[1]}:\n{refined}")
        elif action == "add" and len(parts) >= 3:
            section_key = section_alias.get(parts[1])
            if not section_key:
                print(f"Unknown section: {parts[1]}")
                continue
            sections[section_key] += "\n- " + parts[2]
            print(f"Added to {parts[1]}.")
        else:
            print("Unknown command. Use: refine, add, show, or done")

    return sections


def _set_model(model: str):
    """Update the module-level MODEL variable."""
    global MODEL
    MODEL = model


def main():
    parser = argparse.ArgumentParser(
        description="AI Meeting Notes - Generate structured meeting notes from transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s --file meeting.txt
  %(prog)s --paste --template standup --format json
  %(prog)s --file notes.txt --interactive
  %(prog)s --record""",
    )

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--file", "-f", help="Path to meeting transcript file")
    input_group.add_argument("--paste", "-p", action="store_true", help="Read from clipboard")
    input_group.add_argument("--record", "-r", action="store_true", help="Record audio (placeholder)")

    parser.add_argument(
        "--format", choices=["markdown", "json", "text"], default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--template", "-t", choices=list(TEMPLATES.keys()), default="general",
        help="Meeting template type (default: general)",
    )
    parser.add_argument("--interactive", "-i", action="store_true", help="Enable interactive refinement mode")
    parser.add_argument("--no-save", action="store_true", help="Don't save output to file")
    parser.add_argument("--model", "-m", default=MODEL, help=f"Ollama model to use (default: {MODEL})")

    args = parser.parse_args()

    # Update module-level model setting
    _set_model(args.model)

    # Get transcript
    print(f"📝 AI Meeting Notes ({args.template} template)")
    print(f"   Model: {MODEL} | Format: {args.format}")
    print("-" * 50)

    transcript = get_transcript(args)
    if not transcript.strip():
        print("Error: Empty transcript provided.", file=sys.stderr)
        sys.exit(1)

    print(f"\n📄 Transcript received ({len(transcript)} characters)")
    print("🤖 Processing with AI...")

    # Build prompt and get AI response
    prompt = build_prompt(transcript, args.template)
    response = call_ollama(prompt)

    # Parse response into sections
    sections = parse_ai_response(response)

    # Interactive refinement
    if args.interactive:
        sections = interactive_refinement(sections, transcript, args.template)

    # Format output
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    formatters = {
        "markdown": format_markdown,
        "json": format_json,
        "text": format_text,
    }
    output = formatters[args.format](sections, args.template, timestamp)

    # Display output
    print("\n" + "=" * 50)
    print(output)
    print("=" * 50)

    # Save output
    if not args.no_save:
        filepath = save_output(output, args.format, args.template)
        print(f"\n💾 Saved to: {filepath}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
