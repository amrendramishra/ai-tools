#!/usr/bin/env python3
"""AI Blog Writer - Generate full blog posts with SEO optimization using AI."""

import argparse
import json
import sys
import os
import re
from datetime import datetime
from pathlib import Path

import requests

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"
OUTPUT_DIR = Path(__file__).parent / "output"

STYLES = {
    "technical": "Write in a technical, informative style with code examples and detailed explanations. Target developers and engineers.",
    "casual": "Write in a casual, conversational tone. Use humor, analogies, and relatable examples. Target general audience.",
    "storytelling": "Write as a narrative with a compelling story arc. Use anecdotes, scenes, and emotional hooks.",
    "listicle": "Write as a numbered list with clear headers. Each point should be self-contained and actionable."
}

LENGTHS = {
    "short": (500, "approximately 500 words"),
    "medium": (1000, "approximately 1000 words"),
    "long": (2000, "approximately 2000+ words, comprehensive and detailed")
}


def query_ollama(prompt: str) -> str:
    """Query Ollama for AI responses."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=300
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to Ollama at localhost:11434. Is it running?")
        sys.exit(1)
    except Exception as e:
        print(f"Error querying Ollama: {e}")
        return ""


def generate_outline(topic: str, style: str, length: str) -> str:
    """Generate a blog post outline."""
    style_desc = STYLES.get(style, STYLES["technical"])
    _, length_desc = LENGTHS.get(length, LENGTHS["medium"])

    prompt = f"""Create a detailed blog post outline for the topic: "{topic}"

Style: {style_desc}
Target length: {length_desc}

Provide:
1. A compelling title (with 2 alternatives)
2. Meta description (150 chars max)
3. Target keywords (5-7)
4. Detailed section outline with:
   - Introduction hook
   - Main sections (H2 headings) with bullet points for key content
   - Subheadings (H3) where appropriate
   - Conclusion with CTA (Call to Action)

Format as clean markdown."""

    return query_ollama(prompt)


def generate_blog_post(topic: str, style: str, length: str, seo: bool = False, outline: str = None) -> str:
    """Generate a full blog post."""
    style_desc = STYLES.get(style, STYLES["technical"])
    _, length_desc = LENGTHS.get(length, LENGTHS["medium"])

    outline_section = ""
    if outline:
        outline_section = f"\nFollow this outline:\n{outline}\n"

    seo_instructions = ""
    if seo:
        seo_instructions = """
SEO OPTIMIZATION:
- Include target keywords naturally (2-3% density)
- Use keywords in headings and first paragraph
- Write an engaging meta description (150 chars)
- Use descriptive H2 and H3 headings
- Include internal linking suggestions [LINK: topic]
- Add image alt text suggestions [IMG: description]
- Keep paragraphs short (2-3 sentences)
- Use bullet points and numbered lists for scannability"""

    prompt = f"""Write a complete blog post about: "{topic}"

Style: {style_desc}
Target length: {length_desc}
{outline_section}
{seo_instructions}

REQUIREMENTS:
1. Start with # Title
2. Write an engaging introduction that hooks the reader
3. Use proper markdown formatting (## for H2, ### for H3)
4. Include practical examples and actionable insights
5. End with a strong conclusion and call-to-action
6. Add suggested tags at the end

Write the complete blog post now:"""

    return query_ollama(prompt)


def generate_series(topic: str, style: str) -> str:
    """Create a multi-part blog series plan."""
    style_desc = STYLES.get(style, STYLES["technical"])

    prompt = f"""Create a comprehensive multi-part blog series plan for: "{topic}"

Style: {style_desc}

Design a 4-6 part series that:
1. Progresses logically from basics to advanced
2. Each part stands alone but connects to the series
3. Builds reader engagement across posts

For each part provide:
- Title
- Key topics covered
- Target keywords
- Estimated length
- Hook to next post

Also include:
- Series overview/landing page description
- Publishing schedule recommendation
- Cross-linking strategy

Format as clean markdown."""

    return query_ollama(prompt)


def edit_post(file_path: str) -> str:
    """AI edits and improves an existing blog post."""
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    with open(file_path) as f:
        content = f.read()

    prompt = f"""You are an expert blog editor. Review and improve this blog post.

ORIGINAL POST:
{content[:4000]}

Provide:
1. EDITED VERSION: The improved post with better flow, clarity, and engagement
2. CHANGES MADE: List of specific improvements

Focus on:
- Stronger opening hook
- Better transitions between sections
- More engaging language
- Clearer structure
- Stronger conclusion and CTA
- Fix any grammar or style issues
- Improve readability

Write the complete edited version:"""

    return query_ollama(prompt)


def add_frontmatter(content: str, topic: str, style: str) -> str:
    """Add static site generator frontmatter (Hugo/Jekyll compatible)."""
    # Extract title from content
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else topic

    # Generate slug
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')

    # Extract tags from content end
    tags_match = re.search(r'[Tt]ags?:\s*(.+)$', content, re.MULTILINE)
    tags = []
    if tags_match:
        tags = [t.strip().strip('#').strip() for t in tags_match.group(1).split(',')]
    if not tags:
        tags = [topic.split()[0].lower(), style]

    date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
    if not date.endswith('+') and '+' not in date:
        date += "+00:00"

    frontmatter = f"""---
title: "{title}"
date: {datetime.now().strftime("%Y-%m-%dT%H:%M:%S+05:30")}
draft: false
slug: "{slug}"
tags: {json.dumps(tags)}
categories: ["{style}"]
description: "A {style} blog post about {topic}"
author: "AI Blog Writer"
---

"""
    return frontmatter + content


def save_post(content: str, topic: str, suffix: str = "") -> Path:
    """Save blog post to output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')[:50]
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"{timestamp}-{slug}{suffix}.md"
    filepath = OUTPUT_DIR / filename
    with open(filepath, "w") as f:
        f.write(content)
    print(f"✓ Saved to: {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="AI Blog Writer - Generate blog posts with AI")
    parser.add_argument("--topic", metavar="TOPIC", help="Blog post topic")
    parser.add_argument("--outline", action="store_true", help="Generate outline only")
    parser.add_argument("--style", choices=list(STYLES.keys()), default="technical", help="Writing style")
    parser.add_argument("--length", choices=list(LENGTHS.keys()), default="medium", help="Post length")
    parser.add_argument("--seo", action="store_true", help="Add SEO optimization")
    parser.add_argument("--series", action="store_true", help="Create multi-part series plan")
    parser.add_argument("--edit", metavar="FILE", help="AI edit/improve existing post")
    parser.add_argument("--publish-ready", action="store_true", dest="publish_ready",
                        help="Add frontmatter for Hugo/Jekyll")

    args = parser.parse_args()

    if not args.topic and not args.edit:
        parser.print_help()
        print("\nExamples:")
        print('  ./blog_writer.py --topic "Getting Started with Docker" --style technical --length medium')
        print('  ./blog_writer.py --topic "AI in 2026" --outline')
        print('  ./blog_writer.py --topic "Top 10 Python Tips" --style listicle --seo')
        print('  ./blog_writer.py --edit output/my-post.md')
        return

    if args.edit:
        print("✏️  AI editing your post...")
        result = edit_post(args.edit)
        print("\n" + result)
        save_post(result, Path(args.edit).stem, "-edited")
        return

    if args.series:
        print(f"📚 Creating series plan for: {args.topic}")
        result = generate_series(args.topic, args.style)
        print("\n" + result)
        save_post(result, args.topic, "-series-plan")
        return

    if args.outline:
        print(f"📋 Generating outline for: {args.topic}")
        result = generate_outline(args.topic, args.style, args.length)
        print("\n" + result)
        save_post(result, args.topic, "-outline")
        return

    # Full blog post generation
    print(f"✍️  Writing blog post: {args.topic}")
    print(f"   Style: {args.style} | Length: {args.length} | SEO: {'Yes' if args.seo else 'No'}")
    print()

    content = generate_blog_post(args.topic, args.style, args.length, args.seo)

    if args.publish_ready:
        content = add_frontmatter(content, args.topic, args.style)
        print("📦 Added frontmatter for static site generator")

    print("\n" + content)
    save_post(content, args.topic)
    print("\n✓ Blog post generation complete!")


if __name__ == "__main__":
    main()
