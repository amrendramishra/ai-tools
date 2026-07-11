#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
AI Shorts Factory - Generate YouTube Shorts scripts for 9 channels using Ollama LLM.
"""

import argparse
import json
import os
import sys
import random
from datetime import datetime
from pathlib import Path
import requests

# Project paths
SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / "output"
CHANNELS_CONFIG = SCRIPT_DIR / "channels_config.json"
HOOKS_LIBRARY = SCRIPT_DIR / "hooks_library.json"

# Ollama config
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# Style definitions
STYLES = ["hook_fact", "storytelling", "listicle", "question", "shocking"]
FORMATS = ["script", "srt", "json"]
LANGUAGES = ["hindi", "english", "hinglish"]


def load_config():
    """Load channels configuration."""
    with open(CHANNELS_CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def load_hooks():
    """Load hooks library."""
    with open(HOOKS_LIBRARY, "r", encoding="utf-8") as f:
        return json.load(f)


def get_channel_key(channel_name: str, config: dict) -> str:
    """Find channel key from partial name match."""
    channel_name_lower = channel_name.lower().replace(" ", "_").replace("-", "_")
    # Direct key match
    if channel_name_lower in config["channels"]:
        return channel_name_lower
    # Partial match
    for key, val in config["channels"].items():
        if channel_name_lower in key or channel_name_lower in val["name"].lower().replace(" ", "_"):
            return key
    # Fuzzy match on display name
    for key, val in config["channels"].items():
        if channel_name.lower() in val["name"].lower():
            return key
    return None


def get_relevant_hooks(hooks_data: dict, channel_config: dict, style: str = None, count: int = 3) -> list:
    """Get relevant hooks for a channel based on niche and style."""
    niche = channel_config["niche"].split("/")[0].strip()
    niche_map = {
        "knowledge": "knowledge", "tech": "tech", "finance": "finance",
        "productivity": "productivity", "horror": "horror",
        "relationships": "relationships", "dark facts": "dark_facts",
        "legal": "legal", "hypothetical": "hypothetical"
    }
    mapped_niche = niche_map.get(niche, niche)

    relevant = []
    for hook in hooks_data["hooks"]:
        if mapped_niche in hook["niches"]:
            if style:
                type_map = {"hook_fact": "fact", "storytelling": "story",
                           "listicle": "fact", "question": "question",
                           "shocking": "shock"}
                if hook["type"] == type_map.get(style, style):
                    relevant.append(hook)
            else:
                relevant.append(hook)

    relevant.sort(key=lambda x: x["engagement_score"], reverse=True)
    return relevant[:count] if relevant else hooks_data["hooks"][:count]


def call_ollama(prompt: str) -> str:
    """Call Ollama API to generate content."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "num_predict": 1024
                }
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to Ollama at localhost:11434")
        print("Make sure Ollama is running: ollama serve")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("ERROR: Ollama request timed out (120s)")
        return None
    except Exception as e:
        print(f"ERROR: Ollama request failed: {e}")
        return None


def build_prompt(channel_config: dict, style: str, topic: str, language: str, hooks: list) -> str:
    """Build the LLM prompt for generating a short script."""
    hook_examples = "\n".join([f"  - {h['template']}" for h in hooks])
    sample_hooks = "\n".join([f"  - {h}" for h in channel_config.get("sample_hooks", [])])

    lang_instruction = {
        "hindi": "Write entirely in Hindi (Devanagari transliteration in Roman script/Hinglish readable format). The audience speaks Hindi.",
        "english": "Write entirely in English.",
        "hinglish": "Write in Hinglish (mix of Hindi and English, Roman script). Natural code-mixing."
    }

    style_instruction = {
        "hook_fact": "Start with a mind-blowing fact that stops scrolling. Follow with supporting facts.",
        "storytelling": "Tell a mini-story with setup, tension, and payoff. Keep it gripping.",
        "listicle": "Present as a numbered list (3-5 items). Each point should be punchy.",
        "question": "Open with a provocative question. Build curiosity before revealing answer.",
        "shocking": "Lead with something shocking/unbelievable. Prove it with evidence."
    }

    topic_line = f"Topic: {topic}" if topic else f"Pick a trending/interesting topic in the {channel_config['niche']} niche."

    prompt = f"""You are a YouTube Shorts scriptwriter for the channel "{channel_config['name']}".
Channel niche: {channel_config['niche']}
Channel tone: {channel_config['tone']}
Target audience: {channel_config['target_audience']}

{lang_instruction.get(language, lang_instruction['hindi'])}

Style: {style} - {style_instruction.get(style, '')}

{topic_line}

Reference hook templates (for inspiration):
{hook_examples}

Channel's sample hooks:
{sample_hooks}

Generate a COMPLETE YouTube Short script (58 seconds total) with this EXACT structure:

HOOK (0-3 seconds):
[Write ONE powerful attention-grabbing line that stops scrolling]

BODY (3-48 seconds):
[00:03] Point 1 - ...
[00:10] Point 2 - ...
[00:18] Point 3 - ...
[00:28] Point 4 - ...
[00:38] Point 5 (if needed) - ...

CTA (48-58 seconds):
[Write a natural call-to-action asking to like, subscribe, or comment]

ON-SCREEN TEXT:
Line 1: [text overlay for first 3 sec]
Line 2: [text overlay for 3-10 sec]
Line 3: [text overlay for 10-20 sec]
Line 4: [text overlay for 20-35 sec]
Line 5: [text overlay for 35-48 sec]
Line 6: [text overlay for 48-58 sec - CTA]

MUSIC MOOD: [One word/phrase for background music - e.g., suspenseful, upbeat, dramatic]

HASHTAGS: [5-7 relevant hashtags]

Important:
- Make the HOOK absolutely scroll-stopping
- Keep language natural and conversational
- Each body point should be concise but impactful
- CTA should feel natural, not forced
- On-screen text should be SHORT (max 8-10 words per line)
"""
    return prompt


def parse_script_response(raw_response: str) -> dict:
    """Parse the LLM response into structured format."""
    result = {
        "hook": "",
        "body": [],
        "cta": "",
        "on_screen_text": [],
        "music_mood": "",
        "hashtags": []
    }

    if not raw_response:
        return result

    lines = raw_response.strip().split("\n")
    current_section = None

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Detect sections
        if "HOOK" in line_stripped.upper() and ("0-3" in line_stripped or "second" in line_stripped.lower() or line_stripped.upper().startswith("HOOK")):
            current_section = "hook"
            continue
        elif "BODY" in line_stripped.upper() and ("3-48" in line_stripped or "second" in line_stripped.lower() or line_stripped.upper().startswith("BODY")):
            current_section = "body"
            continue
        elif "CTA" in line_stripped.upper() and ("48-58" in line_stripped or "second" in line_stripped.lower() or line_stripped.upper().startswith("CTA")):
            current_section = "cta"
            continue
        elif "ON-SCREEN" in line_stripped.upper() or "ON SCREEN" in line_stripped.upper():
            current_section = "onscreen"
            continue
        elif "MUSIC MOOD" in line_stripped.upper() or "MUSIC:" in line_stripped.upper():
            current_section = "music"
            # Check if value is on same line
            if ":" in line_stripped:
                val = line_stripped.split(":", 1)[1].strip()
                if val:
                    result["music_mood"] = val
            continue
        elif "HASHTAG" in line_stripped.upper():
            current_section = "hashtags"
            # Check if hashtags on same line
            if "#" in line_stripped:
                tags = [t.strip() for t in line_stripped.split() if t.startswith("#")]
                result["hashtags"].extend(tags)
            continue

        # Fill sections
        if current_section == "hook":
            if line_stripped.startswith("["):
                line_stripped = line_stripped.split("]", 1)[-1].strip()
            if line_stripped and not result["hook"]:
                result["hook"] = line_stripped
        elif current_section == "body":
            if line_stripped.startswith("[") or line_stripped.startswith("Point") or line_stripped[0:1].isdigit():
                result["body"].append(line_stripped)
            elif line_stripped.startswith("-") or line_stripped.startswith("•"):
                result["body"].append(line_stripped)
        elif current_section == "cta":
            if line_stripped.startswith("["):
                line_stripped = line_stripped.split("]", 1)[-1].strip()
            if line_stripped and not result["cta"]:
                result["cta"] = line_stripped
        elif current_section == "onscreen":
            if "Line" in line_stripped or line_stripped.startswith("[") or ":" in line_stripped:
                val = line_stripped.split(":", 1)[-1].strip() if ":" in line_stripped else line_stripped
                val = val.strip("[]")
                if val:
                    result["on_screen_text"].append(val)
        elif current_section == "music":
            if not result["music_mood"] and line_stripped:
                result["music_mood"] = line_stripped
        elif current_section == "hashtags":
            tags = [t.strip() for t in line_stripped.split() if t.startswith("#")]
            if tags:
                result["hashtags"].extend(tags)
            elif line_stripped and not line_stripped.startswith("#"):
                # Sometimes hashtags don't have # prefix
                words = [w.strip(",. ") for w in line_stripped.split()]
                result["hashtags"].extend([f"#{w}" if not w.startswith("#") else w for w in words if w])

    # Fallback: if parsing failed, use raw response
    if not result["hook"] and raw_response:
        result["hook"] = raw_response[:100]
        result["body"] = [raw_response[100:500]]
        result["cta"] = "Like, subscribe aur bell icon dabao!"
        result["music_mood"] = "energetic"
        result["hashtags"] = ["#shorts", "#viral", "#trending"]

    return result


def format_as_script(parsed: dict, channel_name: str, style: str, topic: str) -> str:
    """Format parsed content as readable script."""
    output = []
    output.append("=" * 60)
    output.append(f"YOUTUBE SHORT SCRIPT")
    output.append(f"Channel: {channel_name}")
    output.append(f"Style: {style}")
    output.append(f"Topic: {topic or 'Auto-generated'}")
    output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    output.append("=" * 60)
    output.append("")
    output.append("🎬 HOOK (0-3 seconds):")
    output.append(f"   {parsed['hook']}")
    output.append("")
    output.append("📝 BODY (3-48 seconds):")
    for point in parsed["body"]:
        output.append(f"   {point}")
    output.append("")
    output.append("📢 CTA (48-58 seconds):")
    output.append(f"   {parsed['cta']}")
    output.append("")
    output.append("📱 ON-SCREEN TEXT OVERLAYS:")
    for i, text in enumerate(parsed["on_screen_text"], 1):
        output.append(f"   [{i}] {text}")
    output.append("")
    output.append(f"🎵 MUSIC MOOD: {parsed['music_mood']}")
    output.append("")
    output.append(f"# HASHTAGS: {' '.join(parsed['hashtags'])}")
    output.append("")
    output.append("-" * 60)
    return "\n".join(output)


def format_as_srt(parsed: dict) -> str:
    """Format parsed content as SRT subtitle file."""
    srt_lines = []
    counter = 1

    # Hook: 0-3 seconds
    if parsed["hook"]:
        srt_lines.append(str(counter))
        srt_lines.append("00:00:00,000 --> 00:00:03,000")
        srt_lines.append(parsed["hook"])
        srt_lines.append("")
        counter += 1

    # Body points distributed across 3-48 seconds
    body_points = parsed["body"]
    if body_points:
        duration_per_point = 45000 // max(len(body_points), 1)  # ms
        for i, point in enumerate(body_points):
            start_ms = 3000 + (i * duration_per_point)
            end_ms = start_ms + duration_per_point
            start_ts = f"00:00:{start_ms // 1000:02d},{start_ms % 1000:03d}"
            end_ts = f"00:00:{end_ms // 1000:02d},{end_ms % 1000:03d}"
            srt_lines.append(str(counter))
            srt_lines.append(f"{start_ts} --> {end_ts}")
            # Clean timestamp from body point text
            clean_point = point.lstrip("[0123456789:] ").lstrip("- •")
            srt_lines.append(clean_point)
            srt_lines.append("")
            counter += 1

    # CTA: 48-58 seconds
    if parsed["cta"]:
        srt_lines.append(str(counter))
        srt_lines.append("00:00:48,000 --> 00:00:58,000")
        srt_lines.append(parsed["cta"])
        srt_lines.append("")

    return "\n".join(srt_lines)


def format_as_json(parsed: dict, channel_name: str, style: str, topic: str) -> str:
    """Format parsed content as JSON."""
    output = {
        "metadata": {
            "channel": channel_name,
            "style": style,
            "topic": topic or "auto-generated",
            "generated_at": datetime.now().isoformat(),
            "duration_seconds": 58
        },
        "script": {
            "hook": {
                "text": parsed["hook"],
                "duration": "0-3 seconds",
                "purpose": "Stop scrolling, grab attention"
            },
            "body": {
                "points": parsed["body"],
                "duration": "3-48 seconds",
                "purpose": "Deliver value"
            },
            "cta": {
                "text": parsed["cta"],
                "duration": "48-58 seconds",
                "purpose": "Drive engagement"
            }
        },
        "production": {
            "on_screen_text": parsed["on_screen_text"],
            "music_mood": parsed["music_mood"],
            "hashtags": parsed["hashtags"]
        }
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


def generate_short(channel_key: str, config: dict, hooks_data: dict,
                   style: str = None, topic: str = None, language: str = None,
                   output_format: str = "script") -> dict:
    """Generate a single short for a channel."""
    channel_config = config["channels"][channel_key]

    # Defaults
    if not style:
        style = random.choice(channel_config["shorts_style"])
    if not language:
        language = channel_config.get("language", "hindi")

    # Get relevant hooks
    hooks = get_relevant_hooks(hooks_data, channel_config, style)

    # Build prompt and call LLM
    prompt = build_prompt(channel_config, style, topic, language, hooks)
    print(f"  🤖 Generating for {channel_config['name']} [{style}]...")

    raw_response = call_ollama(prompt)
    if not raw_response:
        print(f"  ❌ Failed to generate for {channel_config['name']}")
        return None

    # Parse response
    parsed = parse_script_response(raw_response)

    # Format output
    if output_format == "script":
        formatted = format_as_script(parsed, channel_config["name"], style, topic)
    elif output_format == "srt":
        formatted = format_as_srt(parsed)
    elif output_format == "json":
        formatted = format_as_json(parsed, channel_config["name"], style, topic)
    else:
        formatted = format_as_script(parsed, channel_config["name"], style, topic)

    return {
        "channel_key": channel_key,
        "channel_name": channel_config["name"],
        "style": style,
        "topic": topic,
        "language": language,
        "format": output_format,
        "content": formatted,
        "parsed": parsed,
        "raw_response": raw_response
    }


def save_short(result: dict, output_dir: Path = None):
    """Save generated short to file."""
    if not result:
        return None

    date_str = datetime.now().strftime("%Y-%m-%d")
    channel_dir = (output_dir or OUTPUT_DIR) / result["channel_key"] / date_str
    channel_dir.mkdir(parents=True, exist_ok=True)

    # Determine extension
    ext_map = {"script": "txt", "srt": "srt", "json": "json"}
    ext = ext_map.get(result["format"], "txt")

    # Generate filename
    timestamp = datetime.now().strftime("%H%M%S")
    style = result["style"]
    filename = f"short_{style}_{timestamp}.{ext}"
    filepath = channel_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(result["content"])

    print(f"  💾 Saved: {filepath}")
    return filepath


def generate_for_channel(channel_key: str, config: dict, hooks_data: dict,
                         count: int = 1, style: str = None, topic: str = None,
                         language: str = None, output_format: str = "script"):
    """Generate multiple shorts for a channel."""
    results = []
    for i in range(count):
        if count > 1:
            print(f"\n  📹 Short {i + 1}/{count}")
        result = generate_short(channel_key, config, hooks_data, style, topic, language, output_format)
        if result:
            filepath = save_short(result)
            results.append({"result": result, "filepath": str(filepath)})
    return results


def batch_daily(config: dict, hooks_data: dict, language: str = None, output_format: str = "script"):
    """Generate daily batch of shorts for all channels."""
    print("\n🚀 BATCH DAILY GENERATION")
    print("=" * 50)

    all_results = []
    for channel_key, channel_config in config["channels"].items():
        freq = channel_config.get("posting_frequency", "1 short/day")
        count = int(freq.split()[0]) if freq[0].isdigit() else 1

        print(f"\n📺 {channel_config['name']} ({count} short{'s' if count > 1 else ''})")
        print("-" * 40)

        results = generate_for_channel(
            channel_key, config, hooks_data,
            count=count, language=language, output_format=output_format
        )
        all_results.extend(results)

    print(f"\n✅ BATCH COMPLETE: Generated {len(all_results)} shorts")
    return all_results


def list_channels(config: dict):
    """Display available channels."""
    print("\n📺 Available Channels:")
    print("-" * 50)
    for key, val in config["channels"].items():
        print(f"  {key:20s} | {val['name']:20s} | {val['niche']}")
    print(f"\nTotal: {len(config['channels'])} channels")


def main():
    parser = argparse.ArgumentParser(
        description="🎬 AI Shorts Factory - Generate YouTube Shorts scripts with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --channel gyaan_in_5
  %(prog)s --channel tech_in_5_hindi --style shocking --topic "AI replacing jobs"
  %(prog)s --all --format json
  %(prog)s --all --count 2 --language hinglish
  %(prog)s --batch-daily
  %(prog)s --list-channels
        """
    )

    # Channel selection
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--channel", type=str, help="Generate for specific channel (key or name)")
    group.add_argument("--all", action="store_true", help="Generate 1 short per channel")
    group.add_argument("--batch-daily", action="store_true", help="Generate full day's shorts for all channels")
    group.add_argument("--list-channels", action="store_true", help="List available channels")

    # Generation options
    parser.add_argument("--count", type=int, default=1, help="Number of shorts per channel (default: 1)")
    parser.add_argument("--topic", type=str, help="Specific topic for the short")
    parser.add_argument("--style", type=str, choices=STYLES, help="Script style")
    parser.add_argument("--format", type=str, choices=FORMATS, default="script", help="Output format (default: script)")
    parser.add_argument("--language", type=str, choices=LANGUAGES, help="Output language (default: channel's language)")
    parser.add_argument("--output-dir", type=str, help="Custom output directory")

    args = parser.parse_args()

    # Load configs
    config = load_config()
    hooks_data = load_hooks()

    # Custom output dir
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR

    if args.list_channels:
        list_channels(config)
        return

    if args.batch_daily:
        batch_daily(config, hooks_data, args.language, args.format)
        return

    if args.all:
        print("\n🚀 Generating shorts for ALL channels")
        print("=" * 50)
        all_results = []
        for channel_key in config["channels"]:
            print(f"\n📺 {config['channels'][channel_key]['name']}")
            print("-" * 40)
            results = generate_for_channel(
                channel_key, config, hooks_data,
                count=args.count, style=args.style, topic=args.topic,
                language=args.language, output_format=args.format
            )
            all_results.extend(results)
        print(f"\n✅ COMPLETE: Generated {len(all_results)} shorts")
        return

    if args.channel:
        channel_key = get_channel_key(args.channel, config)
        if not channel_key:
            print(f"❌ Channel not found: '{args.channel}'")
            print("Available channels:")
            list_channels(config)
            sys.exit(1)

        print(f"\n📺 Generating for: {config['channels'][channel_key]['name']}")
        print("=" * 50)
        generate_for_channel(
            channel_key, config, hooks_data,
            count=args.count, style=args.style, topic=args.topic,
            language=args.language, output_format=args.format
        )
        return

    # No arguments - show help
    parser.print_help()


if __name__ == "__main__":
    main()
