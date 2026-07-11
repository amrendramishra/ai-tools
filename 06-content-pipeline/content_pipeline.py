#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
AI Content Pipeline - End-to-end YouTube content generator
Uses Ollama (localhost:11434) for AI generation with channel-specific personas.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"
SCRIPT_DIR = Path(__file__).parent
CHANNELS_FILE = SCRIPT_DIR / "channels.json"
OUTPUT_DIR = SCRIPT_DIR / "output"

# Format specifications
FORMAT_SPECS = {
    "short": {
        "duration": "60 seconds",
        "word_count": "150-180 words",
        "structure": "Hook (10s) → Core Point (40s) → CTA (10s)"
    },
    "medium": {
        "duration": "5 minutes",
        "word_count": "750-900 words",
        "structure": "Hook (30s) → Context (60s) → Main Points (180s) → Summary (30s) → CTA (20s)"
    },
    "long": {
        "duration": "10+ minutes",
        "word_count": "1500-2000 words",
        "structure": "Hook (30s) → Intro (60s) → Point 1 (120s) → Point 2 (120s) → Point 3 (120s) → Deep Dive (120s) → Summary (60s) → CTA (30s)"
    }
}


def load_channels() -> dict:
    """Load channel configurations from channels.json."""
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["channels"]


def get_channel_config(channel_name: str, channels: dict) -> dict | None:
    """Find channel config by name (fuzzy match on key or display name)."""
    # Direct key match
    if channel_name in channels:
        return channels[channel_name]
    # Match by display name (case-insensitive)
    name_lower = channel_name.lower().replace(" ", "_").replace("-", "_")
    for key, config in channels.items():
        if key == name_lower or config["name"].lower().replace(" ", "_") == name_lower:
            return config
        # Partial match
        if name_lower in key or name_lower in config["name"].lower():
            return config
    return None


def ollama_generate(prompt: str, system_prompt: str = "") -> str:
    """Generate text using Ollama API."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.8,
            "top_p": 0.9,
            "num_predict": 4096
        }
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to Ollama at localhost:11434")
        print("Make sure Ollama is running: ollama serve")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("ERROR: Ollama request timed out (120s)")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Ollama generation failed: {e}")
        sys.exit(1)


def generate_trending_topic(channel_config: dict) -> str:
    """Use AI to pick a trending topic for the channel."""
    prompt = f"""You are a YouTube content strategist. 
Pick ONE trending topic that would perform well for a {channel_config['niche']} channel.
Target audience: {channel_config['target_audience']}
Language: {channel_config['language']}

Requirements:
- Topic should be currently relevant (trending or evergreen with current angle)
- High search potential
- Engaging for the target audience

Respond with ONLY the topic in 5-10 words. No explanation, no quotes, just the topic."""

    topic = ollama_generate(prompt, "You are a YouTube trending topic expert.")
    return topic.strip().strip('"').strip("'")


def generate_title(topic: str, channel_config: dict, language: str) -> str:
    """Generate SEO-optimized title."""
    prompt = f"""Generate ONE YouTube title for this topic: {topic}

Channel: {channel_config['name']}
Niche: {channel_config['niche']}
Language: {language}
Target Audience: {channel_config['target_audience']}

Requirements:
- SEO optimized (include searchable keywords)
- Curiosity-inducing or value-promising
- Under 70 characters
- Language: {language}
- Use power words that drive clicks

Respond with ONLY the title. No quotes, no explanation."""

    title = ollama_generate(prompt, channel_config["persona"])
    return title.strip().strip('"').strip("'")


def generate_description(topic: str, title: str, channel_config: dict, language: str) -> str:
    """Generate YouTube video description."""
    prompt = f"""Write a YouTube video description for:
Title: {title}
Topic: {topic}
Channel: {channel_config['name']}
Language: {language}

Include:
- Compelling first 2 lines (shown in search results)
- Brief overview of what viewers will learn
- 3-5 timestamps (estimated)
- Call to subscribe
- Relevant hashtags (5-8)

Keep it under 300 words. Language: {language}"""

    return ollama_generate(prompt, channel_config["persona"])


def generate_tags(topic: str, title: str, channel_config: dict) -> list:
    """Generate video tags."""
    base_tags = channel_config.get("tags_base", [])
    prompt = f"""Generate 15-20 YouTube tags for:
Title: {title}
Topic: {topic}
Niche: {channel_config['niche']}

Requirements:
- Mix of broad and specific tags
- Include long-tail keywords
- Include trending variations
- Language-appropriate

Respond with ONLY a comma-separated list of tags. No numbering, no explanation."""

    result = ollama_generate(prompt)
    ai_tags = [tag.strip().strip('"').strip("'") for tag in result.split(",")]
    all_tags = list(set(base_tags + ai_tags))
    return all_tags[:30]  # YouTube limit is 500 chars, ~30 tags safe


def generate_script(topic: str, title: str, channel_config: dict, format_type: str, language: str) -> str:
    """Generate full video script with hook, body, and CTA."""
    spec = FORMAT_SPECS[format_type]
    prompt = f"""Write a complete YouTube video script.

Title: {title}
Topic: {topic}
Channel: {channel_config['name']}
Format: {format_type} ({spec['duration']})
Word Count Target: {spec['word_count']}
Structure: {spec['structure']}
Language: {language}

SCRIPT REQUIREMENTS:
1. HOOK (first 10-30 seconds): Start with a shocking fact, question, or bold statement that stops scrolling
2. BODY: Deliver value with clear points, examples, and storytelling
3. CTA (Call to Action): End with subscribe reminder + engagement prompt (comment question)

Additional guidelines:
- Write exactly as it should be spoken (conversational, not written)
- Include [PAUSE], [EMPHASIS], [SHOW ON SCREEN] cues where needed
- Match the tone: {channel_config['tone']}
- Target audience: {channel_config['target_audience']}

Write the FULL script now:"""

    return ollama_generate(prompt, channel_config["persona"])


def save_content(channel_config: dict, content: dict, output_dir: Path) -> Path:
    """Save generated content to organized directory structure."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    channel_slug = channel_config["name"].lower().replace(" ", "_")
    save_dir = output_dir / channel_slug / date_str

    # If directory exists, add a counter
    if save_dir.exists():
        counter = 1
        while (save_dir.parent / f"{date_str}_{counter}").exists():
            counter += 1
        save_dir = save_dir.parent / f"{date_str}_{counter}"

    save_dir.mkdir(parents=True, exist_ok=True)

    # Save individual files
    with open(save_dir / "title.txt", "w", encoding="utf-8") as f:
        f.write(content["title"])

    with open(save_dir / "description.txt", "w", encoding="utf-8") as f:
        f.write(content["description"])

    with open(save_dir / "tags.json", "w", encoding="utf-8") as f:
        json.dump(content["tags"], f, indent=2, ensure_ascii=False)

    with open(save_dir / "script.txt", "w", encoding="utf-8") as f:
        f.write(content["script"])

    # Save complete content as single JSON
    with open(save_dir / "content.json", "w", encoding="utf-8") as f:
        json.dump({
            "channel": channel_config["name"],
            "topic": content["topic"],
            "title": content["title"],
            "description": content["description"],
            "tags": content["tags"],
            "script": content["script"],
            "format": content["format"],
            "language": content["language"],
            "generated_at": datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)

    return save_dir


def generate_for_channel(channel_config: dict, topic: str | None, format_type: str,
                         language: str | None, auto_topic: bool) -> dict:
    """Generate all content for a single channel."""
    # Determine language
    lang = language or channel_config["language"]

    # Determine topic
    if auto_topic or topic is None:
        print(f"  🔍 AI picking trending topic for {channel_config['name']}...")
        topic = generate_trending_topic(channel_config)
        print(f"  📌 Topic: {topic}")
    else:
        print(f"  📌 Topic: {topic}")

    # Determine format
    fmt = format_type or channel_config.get("format_preference", "medium")

    # Generate title
    print(f"  ✍️  Generating SEO title...")
    title = generate_title(topic, channel_config, lang)
    print(f"  📝 Title: {title}")

    # Generate description
    print(f"  ✍️  Generating description...")
    description = generate_description(topic, title, channel_config, lang)

    # Generate tags
    print(f"  🏷️  Generating tags...")
    tags = generate_tags(topic, title, channel_config)

    # Generate script
    print(f"  🎬 Generating {fmt} script ({FORMAT_SPECS[fmt]['duration']})...")
    script = generate_script(topic, title, channel_config, fmt, lang)

    return {
        "topic": topic,
        "title": title,
        "description": description,
        "tags": tags,
        "script": script,
        "format": fmt,
        "language": lang
    }


def run_pipeline(args):
    """Main pipeline execution."""
    channels = load_channels()

    if args.batch:
        # Generate for ALL channels
        print("🚀 BATCH MODE: Generating content for ALL channels\n")
        results = []
        for key, config in channels.items():
            print(f"\n{'='*60}")
            print(f"📺 Channel: {config['name']}")
            print(f"{'='*60}")
            try:
                content = generate_for_channel(
                    config, args.topic, args.format, args.language, args.auto
                )
                save_path = save_content(config, content, OUTPUT_DIR)
                print(f"  ✅ Saved to: {save_path}")
                results.append({"channel": config["name"], "status": "success", "path": str(save_path)})
            except Exception as e:
                print(f"  ❌ Failed: {e}")
                results.append({"channel": config["name"], "status": "failed", "error": str(e)})

        # Summary
        print(f"\n{'='*60}")
        print("📊 BATCH SUMMARY")
        print(f"{'='*60}")
        success = sum(1 for r in results if r["status"] == "success")
        print(f"✅ Success: {success}/{len(results)}")
        for r in results:
            icon = "✅" if r["status"] == "success" else "❌"
            print(f"  {icon} {r['channel']}")

    else:
        # Single channel mode
        if not args.channel:
            print("ERROR: Specify --channel <name> or use --batch for all channels")
            print("\nAvailable channels:")
            for key, config in channels.items():
                print(f"  - {key} ({config['name']})")
            sys.exit(1)

        config = get_channel_config(args.channel, channels)
        if not config:
            print(f"ERROR: Channel '{args.channel}' not found")
            print("\nAvailable channels:")
            for key, cfg in channels.items():
                print(f"  - {key} ({cfg['name']})")
            sys.exit(1)

        print(f"📺 Channel: {config['name']}")
        print(f"🎯 Niche: {config['niche']}")
        print(f"{'='*60}")

        content = generate_for_channel(
            config, args.topic, args.format, args.language, args.auto
        )
        save_path = save_content(config, content, OUTPUT_DIR)

        print(f"\n{'='*60}")
        print(f"✅ Content generated and saved!")
        print(f"📁 Location: {save_path}")
        print(f"{'='*60}")
        print(f"\nFiles created:")
        print(f"  - title.txt")
        print(f"  - description.txt")
        print(f"  - tags.json")
        print(f"  - script.txt")
        print(f"  - content.json (complete package)")


def main():
    parser = argparse.ArgumentParser(
        description="AI Content Pipeline - YouTube content generator using Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --channel gyaan_in_5 --topic "quantum computing basics" --format medium
  %(prog)s --channel horror_ki_kahani --auto --format long --language hindi
  %(prog)s --batch --auto --format medium
  %(prog)s --channel money_in_5 --auto --language hinglish
        """
    )
    parser.add_argument("--channel", "-c", help="Channel name or key")
    parser.add_argument("--topic", "-t", help="Video topic (or use --auto)")
    parser.add_argument("--auto", "-a", action="store_true",
                        help="AI picks trending topic for channel")
    parser.add_argument("--format", "-f", choices=["short", "medium", "long"],
                        default=None, help="Video format/duration (default: channel preference)")
    parser.add_argument("--language", "-l", choices=["hindi", "english", "hinglish"],
                        default=None, help="Script language (default: channel setting)")
    parser.add_argument("--batch", "-b", action="store_true",
                        help="Generate content for ALL channels")
    parser.add_argument("--model", "-m", default=None,
                        help="Ollama model to use (default: llama3.2)")

    args = parser.parse_args()

    # Update model if specified
    global MODEL
    if args.model:
        MODEL = args.model

    if not args.topic and not args.auto and not args.batch:
        print("ERROR: Specify --topic <topic> or --auto (AI picks topic)")
        parser.print_help()
        sys.exit(1)

    print("🎬 AI Content Pipeline")
    print(f"🤖 Model: {MODEL}")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    run_pipeline(args)


if __name__ == "__main__":
    main()
