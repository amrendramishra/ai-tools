#!/usr/bin/env python3
"""
Faceless YouTube Channel Automator - Complete zero-human-effort video pipeline.
Generates scripts, scenes, TTS, subtitles, and full video packages using Ollama.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
VOICE_PROFILES_FILE = BASE_DIR / "voice_profiles.json"
SCENE_TEMPLATES_FILE = BASE_DIR / "scene_templates.json"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:60]


def call_ollama(prompt: str, system: str = "", temperature: float = 0.7) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 4096}
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama at localhost:11434. Run: ollama serve")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ollama error: {e}")
        return ""


def extract_json_obj(text: str) -> dict:
    try:
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            return json.loads(m.group())
    except json.JSONDecodeError:
        pass
    return {}


def extract_json_arr(text: str) -> list:
    try:
        m = re.search(r'\[[\s\S]*\]', text)
        if m:
            return json.loads(m.group())
    except json.JSONDecodeError:
        pass
    return []


def load_voice_profiles() -> dict:
    if VOICE_PROFILES_FILE.exists():
        with open(VOICE_PROFILES_FILE) as f:
            return json.load(f)
    return {}


def load_scene_templates() -> dict:
    if SCENE_TEMPLATES_FILE.exists():
        with open(SCENE_TEMPLATES_FILE) as f:
            return json.load(f)
    return {}


def get_format_config(fmt: str) -> dict:
    configs = {
        "short": {"duration_seconds": 60, "word_count": 150, "label": "YouTube Short (60s)"},
        "medium": {"duration_seconds": 300, "word_count": 750, "label": "Medium (5 min)"},
        "long": {"duration_seconds": 600, "word_count": 1500, "label": "Long (10 min)"}
    }
    return configs.get(fmt, configs["medium"])


def pick_topic_auto(channel: str) -> str:
    """Auto-pick a trending topic for the channel."""
    profiles = load_voice_profiles()
    niche = profiles.get(channel, {}).get("niche", "technology and AI")

    prompt = f"""Suggest ONE viral video topic for a faceless YouTube channel in the niche: {niche}
The topic should be:
- Trending right now
- Easy to explain with stock footage
- Clickbait-worthy but not misleading
- Good for faceless narration

Return ONLY the topic title as a single line, nothing else."""

    result = call_ollama(prompt, "You are a YouTube trend expert.", 0.9)
    return result.strip().strip('"').strip("'") or f"Top 5 {niche} Tips You Need to Know"


def generate_script(topic: str, channel: str, fmt_config: dict) -> dict:
    """Generate full video script with SSML markup."""
    word_count = fmt_config["word_count"]
    duration = fmt_config["label"]

    prompt = f"""Write a complete video narration script for a faceless YouTube video.

Topic: {topic}
Format: {duration}
Word count: ~{word_count} words

Requirements:
- Include SSML-like markup for TTS:
  * <break time="0.5s"/> for pauses
  * <emphasis>word</emphasis> for emphasis
  * <prosody rate="slow">text</prosody> for pace changes
- Write in an engaging, conversational narrator voice
- NO "hey guys" or face-to-camera language
- Start with a hook that grabs attention in first 5 seconds
- Include natural transitions between points
- End with a call to action (like, subscribe, comment)
- Add [SCENE: description] markers for what visuals should show

Return the script as plain text with the markup included."""

    script_text = call_ollama(prompt, "You are a top faceless YouTube scriptwriter.", 0.7)
    return {"text": script_text, "word_count": len(script_text.split()), "format": duration}


def generate_scenes(topic: str, script: str, fmt_config: dict) -> list:
    """Generate scene-by-scene breakdown for video editing."""
    duration_sec = fmt_config["duration_seconds"]

    prompt = f"""Create a scene-by-scene breakdown for a faceless YouTube video.

Topic: {topic}
Total Duration: {duration_sec} seconds
Script excerpt: {script[:500]}...

Return ONLY valid JSON array:
[
    {{
        "scene_number": 1,
        "timestamp_start": "00:00",
        "timestamp_end": "00:05",
        "duration_seconds": 5,
        "narration_text": "What the narrator says",
        "visual_description": "What the viewer sees",
        "stock_footage_search": "search term for stock footage",
        "text_overlay": "text shown on screen or empty",
        "transition": "cut|fade|zoom|slide"
    }}
]

Create {max(5, duration_sec // 15)} scenes to cover the full video."""

    result = extract_json_arr(call_ollama(prompt, "Return ONLY valid JSON array.", 0.6))
    if result:
        return result

    # Fallback
    num_scenes = max(5, duration_sec // 15)
    scenes = []
    per_scene = duration_sec // num_scenes
    for i in range(num_scenes):
        start = i * per_scene
        end = start + per_scene
        scenes.append({
            "scene_number": i + 1,
            "timestamp_start": f"{start//60:02d}:{start%60:02d}",
            "timestamp_end": f"{end//60:02d}:{end%60:02d}",
            "duration_seconds": per_scene,
            "narration_text": f"Scene {i+1} narration",
            "visual_description": f"Scene {i+1} visuals",
            "stock_footage_search": topic.split()[0] + " footage",
            "text_overlay": "",
            "transition": "cut"
        })
    return scenes


def generate_text_overlays(topic: str, scenes: list) -> list:
    """Generate text overlays with timestamps."""
    prompt = f"""Create text overlays for a YouTube video about: {topic}
The video has {len(scenes)} scenes.

Return ONLY JSON array:
[{{"timestamp":"00:00","duration_seconds":3,"text":"overlay text","position":"center|top|bottom","style":"title|subtitle|callout|stat"}}]

Generate 5-8 key text overlays that reinforce the narration."""

    result = extract_json_arr(call_ollama(prompt, "Return ONLY valid JSON array.", 0.6))
    return result if result else [{"timestamp": "00:00", "duration_seconds": 3, "text": topic, "position": "center", "style": "title"}]


def generate_thumbnail(topic: str) -> dict:
    """Generate thumbnail text and design suggestions."""
    prompt = f"""Create a YouTube thumbnail concept for: {topic}

Return ONLY JSON:
{{"main_text":"3-5 words, CAPS, attention-grabbing","sub_text":"optional smaller text","text_color":"#FFFFFF","background_mood":"dark|bright|gradient|dramatic","suggested_elements":["element1","element2"],"style":"minimalist|bold|shocking|educational"}}"""

    result = extract_json_obj(call_ollama(prompt, "Return ONLY valid JSON.", 0.8))
    return result if result else {"main_text": topic.upper()[:30], "sub_text": "", "text_color": "#FFFFFF", "background_mood": "dramatic", "suggested_elements": ["icon"], "style": "bold"}


def generate_seo(topic: str, channel: str) -> dict:
    """Generate SEO-optimized title, description, and tags."""
    prompt = f"""Create YouTube SEO metadata for a video about: {topic}

Return ONLY JSON:
{{"title":"clickable title under 60 chars with keywords","description":"full YouTube description with timestamps, links section, keywords (2000+ chars)","tags":["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"],"hashtags":["#hash1","#hash2","#hash3"],"category":"Education|Science & Technology|Entertainment|Howto & Style"}}"""

    result = extract_json_obj(call_ollama(prompt, "You are a YouTube SEO expert. Return ONLY valid JSON.", 0.6))
    return result if result else {"title": topic, "description": f"In this video, we explore {topic}...", "tags": topic.split()[:10], "hashtags": ["#youtube", "#ai"], "category": "Education"}


def generate_subtitles(script_text: str, fmt_config: dict) -> str:
    """Generate SRT subtitle file from script."""
    # Clean script of SSML markup for subtitles
    clean = re.sub(r'<[^>]+>', '', script_text)
    clean = re.sub(r'\[SCENE:[^\]]*\]', '', clean)
    clean = clean.strip()

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', clean)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 3]

    if not sentences:
        return "1\n00:00:00,000 --> 00:00:05,000\n" + script_text[:100]

    duration_sec = fmt_config["duration_seconds"]
    time_per_sentence = duration_sec / max(len(sentences), 1)

    srt_lines = []
    for i, sentence in enumerate(sentences):
        start_sec = i * time_per_sentence
        end_sec = start_sec + time_per_sentence

        start_h = int(start_sec // 3600)
        start_m = int((start_sec % 3600) // 60)
        start_s = int(start_sec % 60)
        start_ms = int((start_sec % 1) * 1000)

        end_h = int(end_sec // 3600)
        end_m = int((end_sec % 3600) // 60)
        end_s = int(end_sec % 60)
        end_ms = int((end_sec % 1) * 1000)

        srt_lines.append(f"{i+1}")
        srt_lines.append(f"{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d} --> {end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}")
        # Wrap long lines
        if len(sentence) > 80:
            mid = len(sentence) // 2
            space_idx = sentence.find(' ', mid)
            if space_idx != -1:
                srt_lines.append(sentence[:space_idx] + "\n" + sentence[space_idx+1:])
            else:
                srt_lines.append(sentence)
        else:
            srt_lines.append(sentence)
        srt_lines.append("")

    return "\n".join(srt_lines)


def generate_tts(script_text: str, output_path: Path, channel: str):
    """Generate TTS voiceover using macOS 'say' command."""
    profiles = load_voice_profiles()
    profile = profiles.get(channel, {"voice": "Samantha", "rate": 180})

    # Clean SSML and scene markers for TTS
    clean = re.sub(r'<break[^>]*/?>', '... ', script_text)
    clean = re.sub(r'<emphasis>', '', clean)
    clean = re.sub(r'</emphasis>', '', clean)
    clean = re.sub(r'<prosody[^>]*>', '', clean)
    clean = re.sub(r'</prosody>', '', clean)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = re.sub(r'\[SCENE:[^\]]*\]', '', clean)
    clean = clean.strip()

    voice = profile.get("voice", "Samantha")
    rate = profile.get("rate", 180)
    aiff_path = output_path / "voiceover.aiff"

    print(f"   🔊 Generating TTS (voice: {voice}, rate: {rate})...")
    try:
        subprocess.run(
            ["say", "-v", voice, "-r", str(rate), "-o", str(aiff_path), clean],
            check=True, capture_output=True, timeout=120
        )
        print(f"   ✓ Saved: {aiff_path}")
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  TTS failed: {e.stderr.decode()[:200]}")
        # Try with default voice
        try:
            subprocess.run(
                ["say", "-r", str(rate), "-o", str(aiff_path), clean],
                check=True, capture_output=True, timeout=120
            )
            print(f"   ✓ Saved (default voice): {aiff_path}")
        except Exception as e2:
            print(f"   ❌ TTS failed: {e2}")
    except FileNotFoundError:
        print("   ❌ 'say' command not found (macOS only)")


def save_video_package(channel: str, video_slug: str, data: dict, tts: bool = False):
    """Save complete video package to output directory."""
    today = date.today().isoformat()
    video_dir = OUTPUT_DIR / channel / today / video_slug
    video_dir.mkdir(parents=True, exist_ok=True)

    # Save master JSON
    with open(video_dir / "video_package.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Save script
    if "script" in data:
        with open(video_dir / "script.md", "w", encoding="utf-8") as f:
            f.write(f"# {data.get('topic', 'Video')}\n\n")
            f.write(data["script"].get("text", ""))

    # Save scenes
    if "scenes" in data:
        with open(video_dir / "scenes.json", "w", encoding="utf-8") as f:
            json.dump(data["scenes"], f, indent=2, ensure_ascii=False)

    # Save text overlays
    if "text_overlays" in data:
        with open(video_dir / "text_overlays.json", "w", encoding="utf-8") as f:
            json.dump(data["text_overlays"], f, indent=2, ensure_ascii=False)

    # Save thumbnail
    if "thumbnail" in data:
        with open(video_dir / "thumbnail.json", "w", encoding="utf-8") as f:
            json.dump(data["thumbnail"], f, indent=2, ensure_ascii=False)

    # Save SEO
    if "seo" in data:
        with open(video_dir / "seo.json", "w", encoding="utf-8") as f:
            json.dump(data["seo"], f, indent=2, ensure_ascii=False)

    # Save subtitles
    if "subtitles" in data:
        with open(video_dir / "subtitles.srt", "w", encoding="utf-8") as f:
            f.write(data["subtitles"])

    # Generate TTS if requested
    if tts and "script" in data:
        generate_tts(data["script"].get("text", ""), video_dir, channel)

    print(f"\n✅ Video package saved: {video_dir}")
    for item in sorted(video_dir.rglob("*")):
        if item.is_file():
            print(f"   📄 {item.name}")

    return video_dir


def generate_full_package(channel: str, topic: str, fmt: str, tts: bool = False, scenes_only: bool = False):
    """Generate a complete video package."""
    fmt_config = get_format_config(fmt)
    video_slug = slugify(topic)

    print(f"🎬 Faceless Video Generator")
    print(f"{'='*50}")
    print(f"Channel: {channel}")
    print(f"Topic: {topic}")
    print(f"Format: {fmt_config['label']}")
    print(f"{'='*50}\n")

    data = {
        "channel": channel,
        "topic": topic,
        "format": fmt,
        "generated_at": datetime.now().isoformat()
    }

    # Generate script
    print("📝 Generating script...")
    script = generate_script(topic, channel, fmt_config)
    data["script"] = script
    print(f"   ✓ Script: {script['word_count']} words")

    # Generate scenes
    print("🎞️  Generating scene breakdown...")
    scenes = generate_scenes(topic, script["text"], fmt_config)
    data["scenes"] = scenes
    print(f"   ✓ {len(scenes)} scenes")

    if scenes_only:
        save_video_package(channel, video_slug, data, tts)
        return

    # Text overlays
    print("📌 Generating text overlays...")
    overlays = generate_text_overlays(topic, scenes)
    data["text_overlays"] = overlays
    print(f"   ✓ {len(overlays)} overlays")

    # Thumbnail
    print("🖼️  Generating thumbnail concept...")
    thumbnail = generate_thumbnail(topic)
    data["thumbnail"] = thumbnail
    print(f"   ✓ Thumbnail: \"{thumbnail.get('main_text', '')}\"")

    # SEO
    print("🔍 Generating SEO metadata...")
    seo = generate_seo(topic, channel)
    data["seo"] = seo
    print(f"   ✓ Title: \"{seo.get('title', '')}\"")

    # Subtitles
    print("📜 Generating subtitles...")
    subtitles = generate_subtitles(script["text"], fmt_config)
    data["subtitles"] = subtitles
    print(f"   ✓ SRT file generated")

    save_video_package(channel, video_slug, data, tts)


def run_daily(tts: bool = False, fmt: str = "medium"):
    """Generate video packages for all channels."""
    profiles = load_voice_profiles()
    if not profiles:
        print("❌ No channels in voice_profiles.json")
        return

    print(f"📅 Daily Generation - {date.today().isoformat()}")
    print(f"   Channels: {list(profiles.keys())}\n")

    for channel, profile in profiles.items():
        print(f"\n{'='*50}")
        print(f"📺 Channel: {channel}")
        print(f"{'='*50}")
        topic = pick_topic_auto(channel)
        print(f"   🎯 Auto-picked topic: {topic}")
        generate_full_package(channel, topic, fmt, tts)


def main():
    parser = argparse.ArgumentParser(
        description="🎬 Faceless YouTube Channel Automator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --channel tech-facts --topic 'Why AI Will Replace Programmers' --generate full
  %(prog)s --channel tech-facts --auto --generate full --format short --tts
  %(prog)s --channel motivation --topic 'Morning Routine' --generate full --tts
  %(prog)s --daily --format medium
  %(prog)s --channel science --topic 'Black Holes' --scenes --format long
        """
    )

    parser.add_argument("--channel", type=str, help="Target channel name")
    parser.add_argument("--topic", type=str, help="Video topic")
    parser.add_argument("--auto", action="store_true", help="Auto-pick trending topic")
    parser.add_argument("--generate", choices=["full"], help="Generate full video package")
    parser.add_argument("--tts", action="store_true", help="Generate TTS voiceover (.aiff)")
    parser.add_argument("--scenes", action="store_true", help="Generate scene breakdown only")
    parser.add_argument("--daily", action="store_true", help="Generate for all channels")
    parser.add_argument("--format", choices=["short", "medium", "long"], default="medium", help="Video format/length")

    args = parser.parse_args()

    if args.daily:
        run_daily(args.tts, args.format)
        return

    if not args.channel:
        parser.error("--channel is required (unless using --daily)")

    if args.auto:
        topic = pick_topic_auto(args.channel)
        print(f"🎯 Auto-picked topic: {topic}")
    elif args.topic:
        topic = args.topic
    else:
        parser.error("--topic or --auto is required")

    generate_full_package(args.channel, topic, args.format, args.tts, args.scenes)


if __name__ == "__main__":
    main()
