#!/usr/bin/env python3
"""AI Newsletter Generator - Curate and generate newsletters using local LLMs."""

import argparse
import json
import os
import sys
import re
import datetime
from pathlib import Path
from xml.etree import ElementTree

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
TEMPLATES_DIR = SCRIPT_DIR / "templates"
SOURCES_FILE = SCRIPT_DIR / "sources.json"

DEFAULT_SECTIONS = ["intro", "highlights", "analysis", "tools", "tip_of_week", "closing"]


def _update_model(new_model: str):
    """Update the global model name."""
    global MODEL
    MODEL = new_model


def query_ollama(prompt: str, model: str = None) -> str:
    """Send a prompt to Ollama and return the response."""
    import urllib.request
    import urllib.error

    if model is None:
        model = MODEL

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 4096}
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response", "").strip()
    except urllib.error.URLError as e:
        print(f"Error connecting to Ollama: {e}")
        sys.exit(1)


def fetch_rss(url: str) -> list:
    """Fetch and parse an RSS feed, returning list of items."""
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AI-Newsletter-Bot/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
    except (urllib.error.URLError, Exception) as e:
        print(f"  ⚠️  Failed to fetch {url}: {e}")
        return []

    items = []
    try:
        root = ElementTree.fromstring(content)
        # Handle RSS 2.0
        for item in root.iter("item"):
            entry = {
                "title": getattr(item.find("title"), "text", ""),
                "link": getattr(item.find("link"), "text", ""),
                "description": getattr(item.find("description"), "text", ""),
                "pubDate": getattr(item.find("pubDate"), "text", ""),
            }
            items.append(entry)

        # Handle Atom feeds
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            summary_el = entry.find("atom:summary", ns)
            published_el = entry.find("atom:published", ns)
            item = {
                "title": getattr(title_el, "text", "") if title_el is not None else "",
                "link": link_el.get("href", "") if link_el is not None else "",
                "description": getattr(summary_el, "text", "") if summary_el is not None else "",
                "pubDate": getattr(published_el, "text", "") if published_el is not None else "",
            }
            items.append(item)
    except ElementTree.ParseError as e:
        print(f"  ⚠️  Failed to parse {url}: {e}")

    return items


def load_sources(topic: str = None, source_urls: list = None) -> list:
    """Load RSS sources from file or arguments."""
    sources = []

    if source_urls:
        sources = source_urls
    elif SOURCES_FILE.exists():
        with open(SOURCES_FILE) as f:
            data = json.load(f)
        if topic and topic in data:
            sources = data[topic]
        else:
            # Flatten all sources
            for feeds in data.values():
                sources.extend(feeds)
    return sources


def curate_content(topic: str, items: list, max_items: int = 10) -> list:
    """Use AI to pick the best items from fetched content."""
    if not items:
        return []

    # Truncate descriptions and limit items for prompt
    summaries = []
    for i, item in enumerate(items[:30]):
        desc = (item.get("description", "") or "")[:200]
        desc = re.sub(r'<[^>]+>', '', desc)  # Strip HTML
        summaries.append(f"{i+1}. {item.get('title', 'Untitled')} - {desc}")

    items_text = "\n".join(summaries)

    prompt = f"""You are a newsletter curator for the topic: {topic}

From these articles, pick the {max_items} most interesting, relevant, and valuable ones for a newsletter audience.
Consider: relevance to topic, newsworthiness, practical value, uniqueness.

ARTICLES:
{items_text}

Return ONLY a JSON array of the selected article numbers (1-indexed):
[1, 5, 8, ...]"""

    response = query_ollama(prompt)
    try:
        match = re.search(r'\[[\d,\s]+\]', response)
        if match:
            selected_indices = json.loads(match.group())
            return [items[i-1] for i in selected_indices if 0 < i <= len(items)]
    except (json.JSONDecodeError, IndexError):
        pass

    # Fallback: return first max_items
    return items[:max_items]


def generate_newsletter(topic: str, curated_items: list, template: str,
                       sections: list, audience: str, fmt: str) -> str:
    """Generate newsletter content from curated items."""
    items_text = ""
    for item in curated_items:
        desc = re.sub(r'<[^>]+>', '', item.get("description", "") or "")[:300]
        items_text += f"- {item.get('title', 'Untitled')}: {desc}\n  Link: {item.get('link', '')}\n\n"

    sections_str = ", ".join(sections)
    audience_str = f"Target audience: {audience}" if audience else ""

    template_guide = get_template_guide(template)

    prompt = f"""Write a newsletter about {topic}.

{template_guide}

CURATED CONTENT TO COVER:
{items_text}

SECTIONS TO INCLUDE: {sections_str}
{audience_str}

FORMAT: {fmt}

Guidelines:
- Write engaging, informative content
- Include brief analysis/commentary, not just summaries
- Add practical takeaways
- Keep a consistent voice throughout
- Include relevant links
- Make it scannable with headers and bullet points

{"Use HTML formatting with proper tags." if fmt == "html" else "Use Markdown formatting." if fmt == "markdown" else "Use plain text."}

Write the complete newsletter now:"""

    return query_ollama(prompt)


def get_template_guide(template: str) -> str:
    """Get writing guide for the template type."""
    guides = {
        "weekly_digest": "Style: Weekly Digest - Comprehensive overview of the week's top stories. Cover 5-8 items with brief commentary on each. Include a 'What to watch' section.",
        "daily_brief": "Style: Daily Brief - Quick, scannable format. 3-5 key items with 1-2 sentence summaries each. Get to the point fast. Include one 'deep thought' or insight.",
        "deep_dive": "Style: Deep Dive - Pick 2-3 items and analyze them thoroughly. Include context, implications, and expert perspective. More essay-like, fewer items but more depth.",
        "roundup": "Style: Roundup - Curated list format. 8-12 items, each with a one-liner and link. Group by category. Add a brief intro and sign-off."
    }
    return guides.get(template, guides["weekly_digest"])


def show_schedule():
    """Display newsletter calendar for the current month."""
    today = datetime.date.today()
    year = today.year
    month = today.month

    print(f"\n📅 Newsletter Calendar - {today.strftime('%B %Y')}")
    print("=" * 50)

    import calendar
    cal = calendar.monthcalendar(year, month)

    print(f"{'Mon':>5} {'Tue':>5} {'Wed':>5} {'Thu':>5} {'Fri':>5} {'Sat':>5} {'Sun':>5}")
    for week in cal:
        row = ""
        for day in week:
            if day == 0:
                row += "     "
            elif day == today.day:
                row += f" [{day:2d}]"
            else:
                row += f"  {day:2d} "
        print(row)

    print("\nSuggested schedule:")
    print("  📨 Weekly Digest: Every Monday")
    print("  📨 Daily Brief: Mon-Fri")
    print("  📨 Deep Dive: 1st & 15th of month")
    print("  📨 Roundup: Every Friday")


def save_newsletter(content: str, fmt: str) -> Path:
    """Save newsletter to output directory with date."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    date_dir = OUTPUT_DIR / today
    date_dir.mkdir(parents=True, exist_ok=True)

    ext = {"markdown": "md", "html": "html", "text": "txt"}.get(fmt, "md")
    timestamp = datetime.datetime.now().strftime("%H%M%S")
    filename = f"newsletter_{timestamp}.{ext}"
    filepath = date_dir / filename
    filepath.write_text(content)
    return filepath


def load_template_file(template_name: str, fmt: str) -> str:
    """Load a template file if it exists."""
    ext = {"markdown": "md", "html": "html", "text": "txt"}.get(fmt, "md")
    template_file = TEMPLATES_DIR / f"{template_name}.{ext}"
    if template_file.exists():
        return template_file.read_text()
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="AI Newsletter Generator - Curate and write newsletters with local LLMs",
        epilog="Examples:\n  %(prog)s --topic ai --curate --write\n  %(prog)s --topic tech --sources https://feed.url/rss --write --template deep_dive\n  %(prog)s --schedule",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--topic", type=str, help="Newsletter topic/niche")
    parser.add_argument("--sources", type=str, nargs="+", help="RSS feed URLs to aggregate")
    parser.add_argument("--curate", action="store_true", help="Fetch and curate content from sources")
    parser.add_argument("--write", action="store_true", help="Generate newsletter from curated content")
    parser.add_argument("--format", type=str, default="markdown", choices=["markdown", "html", "text"])
    parser.add_argument("--template", type=str, default="weekly_digest",
                        choices=["weekly_digest", "daily_brief", "deep_dive", "roundup"])
    parser.add_argument("--sections", type=str, nargs="+", default=DEFAULT_SECTIONS,
                        choices=["intro", "highlights", "analysis", "tools", "tip_of_week", "closing"])
    parser.add_argument("--personalize", type=str, help="Target audience description")
    parser.add_argument("--schedule", action="store_true", help="Show newsletter calendar")
    parser.add_argument("--model", type=str, default=MODEL, help=f"Ollama model (default: {MODEL})")

    args = parser.parse_args()

    if not args.schedule and not args.curate and not args.write:
        parser.print_help()
        sys.exit(0)

    _update_model(args.model)

    if args.schedule:
        show_schedule()
        if not args.curate and not args.write:
            return

    if not args.topic:
        print("Error: --topic is required for --curate and --write")
        sys.exit(1)

    curated_items = []

    if args.curate:
        print(f"📡 Fetching content for topic: {args.topic}")
        sources = load_sources(args.topic, args.sources)

        if not sources:
            print("⚠️  No sources found. Add URLs with --sources or configure sources.json")
            sys.exit(1)

        all_items = []
        for url in sources:
            print(f"  Fetching: {url}")
            items = fetch_rss(url)
            print(f"    Got {len(items)} items")
            all_items.extend(items)

        print(f"\n📊 Total items fetched: {len(all_items)}")

        if all_items:
            print("🤖 AI curating best content...")
            curated_items = curate_content(args.topic, all_items)
            print(f"✅ Selected {len(curated_items)} items\n")

            print("Curated items:")
            for i, item in enumerate(curated_items, 1):
                print(f"  {i}. {item.get('title', 'Untitled')}")
            print()

    if args.write:
        if not curated_items and not args.curate:
            # Generate without curated content - AI creates from topic
            print("📝 Generating newsletter (no curated content - AI will create from topic)...")
            curated_items = [{"title": f"{args.topic} trends", "description": f"Latest in {args.topic}", "link": ""}]

        print(f"✍️  Writing newsletter...")
        print(f"   Template: {args.template}")
        print(f"   Format: {args.format}")
        print(f"   Sections: {', '.join(args.sections)}")
        if args.personalize:
            print(f"   Audience: {args.personalize}")

        content = generate_newsletter(
            args.topic, curated_items, args.template,
            args.sections, args.personalize, args.format
        )

        # Display
        print("\n" + "=" * 60)
        print("GENERATED NEWSLETTER:")
        print("=" * 60)
        print(content)
        print("=" * 60)

        # Save
        filepath = save_newsletter(content, args.format)
        print(f"\n✅ Saved to: {filepath}")


if __name__ == "__main__":
    main()
