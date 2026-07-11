#!/usr/bin/env python3
"""Content Repurposer - Transform content across multiple formats using AI."""

import argparse
import json
import os
import sys
from datetime import datetime

import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

FORMATS = {
    "twitter_thread": "a Twitter/X thread of 5-10 tweets. Each tweet must be under 280 characters. Number them 1/, 2/, etc. Make them engaging with hooks.",
    "linkedin_post": "a professional LinkedIn post. Include a hook first line, use line breaks for readability, add a call-to-action, and relevant hashtags at the end.",
    "instagram_caption": "an Instagram caption. Keep it concise (under 150 words), engaging, with emojis and 20-30 relevant hashtags at the end.",
    "youtube_short": "a YouTube Shorts script (60 seconds max). Include: HOOK (first 3 sec), CONTENT (main points), CTA (subscribe/follow). Add timing markers.",
    "email_newsletter": "an email newsletter. Include: Subject line, Preview text, Greeting, Main content with subheadings, Key takeaways as bullet points, CTA, Sign-off.",
    "blog_post": "a full blog post with: Title, Meta description, Introduction with hook, 3-5 subheadings with content, Conclusion, and a call-to-action.",
    "podcast_outline": "a podcast episode outline with: Episode title, Hook/teaser, Introduction, 3-5 main talking points with sub-bullets, Listener questions to address, Wrap-up, and CTA."
}

SOURCE_FORMATS = ["blog", "video_script", "podcast", "article", "thread"]


def call_ollama(prompt, system_prompt):
    """Call Ollama for content generation."""
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "system": system_prompt, "stream": False}
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=180)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to Ollama at {OLLAMA_URL}")
        print("Make sure Ollama is running: ollama serve")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def load_brand_voice(path):
    """Load brand voice guidelines from JSON file."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Brand voice file not found: {path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in brand voice file: {path}")
        sys.exit(1)


def get_input_content(input_arg):
    """Get content from file path or direct text."""
    if os.path.isfile(input_arg):
        with open(input_arg, "r") as f:
            return f.read()
    return input_arg


def build_system_prompt(tone, brand_voice=None):
    """Build system prompt with tone and brand voice."""
    base = f"You are a professional content repurposer. Your tone is {tone}."
    if brand_voice:
        base += f"\n\nBrand Voice Guidelines:\n"
        base += f"- Brand: {brand_voice.get('brand_name', 'N/A')}\n"
        base += f"- Tone: {brand_voice.get('tone', 'N/A')}\n"
        base += f"- Audience: {brand_voice.get('audience', 'N/A')}\n"
        base += f"- Style: {json.dumps(brand_voice.get('writing_style', {}))}\n"
        if brand_voice.get('vocabulary_preferences'):
            base += f"- Preferred words: {', '.join(brand_voice['vocabulary_preferences'].get('use', []))}\n"
            base += f"- Avoid words: {', '.join(brand_voice['vocabulary_preferences'].get('avoid', []))}\n"
    return base


def repurpose_content(content, source_format, target_format, tone, brand_voice=None):
    """Transform content to a target format."""
    system_prompt = build_system_prompt(tone, brand_voice)
    format_desc = FORMATS[target_format]
    prompt = f"""Transform the following {source_format} content into {format_desc}

Original content:
---
{content}
---

Generate the repurposed content now:"""
    return call_ollama(prompt, system_prompt)


def save_output(content, target_format, output_dir):
    """Save generated content to file."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{target_format}.md"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        f.write(f"# {target_format.replace('_', ' ').title()}\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n---\n\n")
        f.write(content)
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Content Repurposer - Transform content across multiple formats using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input article.md --from blog --to twitter_thread linkedin_post
  %(prog)s --input "AI is transforming..." --from article --all --tone casual
  %(prog)s --input script.txt --from video_script --to blog_post --brand-voice brand.json
        """
    )
    parser.add_argument("--input", required=True, help="Source content (file path or text)")
    parser.add_argument("--from", dest="source_format", required=True,
                        choices=SOURCE_FORMATS, help="Source format")
    parser.add_argument("--to", nargs="+", choices=list(FORMATS.keys()),
                        help="Target format(s)")
    parser.add_argument("--all", action="store_true", help="Generate ALL formats")
    parser.add_argument("--tone", default="professional",
                        choices=["professional", "casual", "humorous", "inspirational"],
                        help="Content tone (default: professional)")
    parser.add_argument("--brand-voice", help="Path to brand voice JSON file")
    parser.add_argument("--output-dir", help="Custom output directory")

    args = parser.parse_args()

    if not args.to and not args.all:
        parser.error("Specify --to with target format(s) or use --all")

    # Load content
    content = get_input_content(args.input)
    if not content.strip():
        print("Error: Input content is empty.")
        sys.exit(1)

    print(f"📄 Source: {args.source_format} ({len(content)} chars)")
    print(f"🎨 Tone: {args.tone}")

    # Load brand voice if specified
    brand_voice = None
    if args.brand_voice:
        brand_voice = load_brand_voice(args.brand_voice)
        print(f"🏷️  Brand: {brand_voice.get('brand_name', 'Custom')}")

    # Determine target formats
    targets = list(FORMATS.keys()) if args.all else args.to

    # Set output directory
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = args.output_dir or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "output", date_str
    )

    print(f"📁 Output: {output_dir}")
    print(f"🔄 Generating {len(targets)} format(s)...\n")

    results = []
    for i, target in enumerate(targets, 1):
        print(f"  [{i}/{len(targets)}] {target.replace('_', ' ').title()}...", end=" ", flush=True)
        result = repurpose_content(content, args.source_format, target, args.tone, brand_voice)
        filepath = save_output(result, target, output_dir)
        results.append((target, filepath))
        print("✓")

    print(f"\n✅ Done! {len(results)} files generated:")
    for target, filepath in results:
        print(f"   • {filepath}")


if __name__ == "__main__":
    main()
