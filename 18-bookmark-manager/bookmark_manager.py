#!/usr/bin/env python3
"""AI Bookmark Manager - Intelligent bookmark organization with AI-powered summaries and search."""

import argparse
import json
import sqlite3
import sys
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"
DB_PATH = Path(__file__).parent / "bookmarks.db"
CATEGORIES = ["tech", "finance", "learning", "news", "tools", "entertainment", "health", "science", "design", "other"]


def init_db():
    """Initialize SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            summary TEXT,
            tags TEXT,
            category TEXT,
            date_added TEXT NOT NULL,
            content_snippet TEXT
        )
    """)
    conn.commit()
    return conn


def query_ollama(prompt: str) -> str:
    """Query Ollama for AI responses."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to Ollama at localhost:11434. Is it running?")
        sys.exit(1)
    except Exception as e:
        print(f"Error querying Ollama: {e}")
        return ""


def fetch_url_content(url: str) -> tuple:
    """Fetch URL and extract title and text content."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else urlparse(url).netloc
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text)
        return title, text[:3000]
    except Exception as e:
        print(f"Warning: Could not fetch URL content: {e}")
        return urlparse(url).netloc, ""


def summarize_and_tag(title: str, content: str) -> tuple:
    """Use AI to summarize content and generate tags."""
    prompt = f"""Analyze this webpage and provide:
1. A concise 2-3 sentence summary
2. 3-5 relevant tags (single words or short phrases)
3. Category (choose ONE from: {', '.join(CATEGORIES)})

Title: {title}
Content: {content[:2000]}

Respond in this exact JSON format:
{{"summary": "...", "tags": ["tag1", "tag2", "tag3"], "category": "..."}}"""

    response = query_ollama(prompt)
    try:
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            summary = data.get("summary", "No summary available")
            tags = data.get("tags", [])
            category = data.get("category", "other")
            if category not in CATEGORIES:
                category = "other"
            return summary, tags, category
    except (json.JSONDecodeError, AttributeError):
        pass
    return "Summary generation failed", ["untagged"], "other"


def add_bookmark(url: str):
    """Add a new bookmark with AI-generated summary and tags."""
    conn = init_db()
    existing = conn.execute("SELECT id FROM bookmarks WHERE url = ?", (url,)).fetchone()
    if existing:
        print(f"Bookmark already exists: {url}")
        conn.close()
        return

    print(f"Fetching: {url}")
    title, content = fetch_url_content(url)
    print(f"Title: {title}")
    print("Generating AI summary and tags...")

    summary, tags, category = summarize_and_tag(title, content)
    conn.execute(
        "INSERT INTO bookmarks (url, title, summary, tags, category, date_added, content_snippet) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (url, title, summary, json.dumps(tags), category, datetime.now().isoformat(), content[:1000])
    )
    conn.commit()
    conn.close()

    print(f"\n✓ Bookmark added!")
    print(f"  Title:    {title}")
    print(f"  Summary:  {summary}")
    print(f"  Tags:     {', '.join(tags)}")
    print(f"  Category: {category}")


def list_bookmarks(category: str = None):
    """List all bookmarks with summaries."""
    conn = init_db()
    if category:
        rows = conn.execute(
            "SELECT url, title, summary, tags, category, date_added FROM bookmarks WHERE category = ? ORDER BY date_added DESC",
            (category,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT url, title, summary, tags, category, date_added FROM bookmarks ORDER BY date_added DESC"
        ).fetchall()
    conn.close()

    if not rows:
        print("No bookmarks found.")
        return

    print(f"\n{'='*70}")
    print(f" BOOKMARKS ({len(rows)} total)")
    print(f"{'='*70}\n")

    for url, title, summary, tags, cat, date_added in rows:
        tags_list = json.loads(tags) if tags else []
        date_str = datetime.fromisoformat(date_added).strftime("%Y-%m-%d %H:%M")
        print(f"  📌 {title}")
        print(f"     URL:      {url}")
        print(f"     Summary:  {summary}")
        print(f"     Tags:     {', '.join(tags_list)}")
        print(f"     Category: {cat} | Added: {date_str}")
        print()


def search_bookmarks(query: str):
    """AI-powered semantic search across bookmarks."""
    conn = init_db()
    rows = conn.execute(
        "SELECT url, title, summary, tags, category, content_snippet FROM bookmarks"
    ).fetchall()
    conn.close()

    if not rows:
        print("No bookmarks to search.")
        return

    bookmark_list = []
    for i, (url, title, summary, tags, category, snippet) in enumerate(rows):
        bookmark_list.append(f"[{i}] Title: {title} | Summary: {summary} | Tags: {tags} | Category: {category}")

    prompt = f"""Given these bookmarks, find the ones most relevant to the query: "{query}"

Bookmarks:
{chr(10).join(bookmark_list)}

Return the indices of relevant bookmarks (most relevant first) as a JSON array of numbers.
Only include genuinely relevant results. Response format: [0, 3, 5]"""

    response = query_ollama(prompt)
    try:
        indices_match = re.search(r'\[[\d,\s]*\]', response)
        if indices_match:
            indices = json.loads(indices_match.group())
            print(f"\n🔍 Search results for: '{query}'\n")
            for idx in indices:
                if 0 <= idx < len(rows):
                    url, title, summary, tags, category, _ = rows[idx]
                    tags_list = json.loads(tags) if tags else []
                    print(f"  📌 {title}")
                    print(f"     URL:      {url}")
                    print(f"     Summary:  {summary}")
                    print(f"     Tags:     {', '.join(tags_list)}")
                    print()
            if not indices:
                print("  No relevant bookmarks found.")
        else:
            print("Could not parse search results.")
    except (json.JSONDecodeError, ValueError):
        print("Search encountered an error. Try again.")


def show_tags():
    """Show all tags and their counts."""
    conn = init_db()
    rows = conn.execute("SELECT tags FROM bookmarks").fetchall()
    conn.close()

    tag_counts = {}
    for (tags_json,) in rows:
        tags = json.loads(tags_json) if tags_json else []
        for tag in tags:
            tag_lower = tag.lower()
            tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1

    if not tag_counts:
        print("No tags found.")
        return

    print(f"\n🏷️  All Tags ({len(tag_counts)} unique)\n")
    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {tag:<20} {count:>3} {'█' * count}")


def export_bookmarks(format_type: str = "html"):
    """Export bookmarks as HTML or JSON."""
    conn = init_db()
    rows = conn.execute(
        "SELECT url, title, summary, tags, category, date_added FROM bookmarks ORDER BY category, date_added DESC"
    ).fetchall()
    conn.close()

    if not rows:
        print("No bookmarks to export.")
        return

    if format_type == "json":
        output_file = Path(__file__).parent / "bookmarks_export.json"
        data = []
        for url, title, summary, tags, category, date_added in rows:
            data.append({"url": url, "title": title, "summary": summary,
                         "tags": json.loads(tags) if tags else [], "category": category, "date_added": date_added})
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
    else:
        output_file = Path(__file__).parent / "bookmarks_export.html"
        html = ['<!DOCTYPE NETSCAPE-Bookmark-file-1>',
                '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
                '<TITLE>Bookmarks</TITLE>', '<H1>AI Bookmark Manager Export</H1>', '<DL><p>']
        categories = {}
        for url, title, summary, tags, category, date_added in rows:
            categories.setdefault(category, []).append((url, title, summary, date_added))
        for cat, items in sorted(categories.items()):
            html.append(f'    <DT><H3>{cat.upper()}</H3>')
            html.append('    <DL><p>')
            for url, title, summary, date_added in items:
                ts = int(datetime.fromisoformat(date_added).timestamp())
                html.append(f'        <DT><A HREF="{url}" ADD_DATE="{ts}">{title}</A>')
                html.append(f'        <DD>{summary}')
            html.append('    </DL><p>')
        html.append('</DL><p>')
        with open(output_file, "w") as f:
            f.write("\n".join(html))

    print(f"✓ Exported {len(rows)} bookmarks to: {output_file}")


def import_bookmarks(file_path: str):
    """Import bookmarks from browser HTML export."""
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    links = soup.find_all("a")

    if not links:
        print("No bookmarks found in file.")
        return

    print(f"Found {len(links)} bookmarks. Importing...")
    conn = init_db()
    imported = 0
    skipped = 0

    for link in links:
        url = link.get("href", "")
        title = link.get_text(strip=True)
        if not url or not url.startswith("http"):
            continue
        existing = conn.execute("SELECT id FROM bookmarks WHERE url = ?", (url,)).fetchone()
        if existing:
            skipped += 1
            continue
        category = "other"
        combined = (url + title).lower()
        if any(kw in combined for kw in ["github", "stackoverflow", "dev", "code", "api", "programming"]):
            category = "tech"
        elif any(kw in combined for kw in ["news", "bbc", "cnn", "reuters"]):
            category = "news"
        elif any(kw in combined for kw in ["course", "learn", "tutorial", "education"]):
            category = "learning"
        elif any(kw in combined for kw in ["finance", "invest", "stock", "bank"]):
            category = "finance"
        elif any(kw in combined for kw in ["tool", "app", "utility", "software"]):
            category = "tools"
        conn.execute(
            "INSERT INTO bookmarks (url, title, summary, tags, category, date_added, content_snippet) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (url, title, "Imported - run search to generate summary", json.dumps(["imported"]), category, datetime.now().isoformat(), "")
        )
        imported += 1

    conn.commit()
    conn.close()
    print(f"✓ Imported: {imported} | Skipped (duplicates): {skipped}")


def daily_digest():
    """AI summary of recently saved bookmarks."""
    conn = init_db()
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    rows = conn.execute(
        "SELECT url, title, summary, tags, category FROM bookmarks WHERE date_added > ? ORDER BY date_added DESC",
        (yesterday,)
    ).fetchall()
    conn.close()

    if not rows:
        print("No bookmarks added in the last 24 hours.")
        return

    summaries = [f"- [{cat}] {title}: {summary}" for url, title, summary, tags, cat in rows]
    prompt = f"""Create a brief daily digest of these {len(rows)} bookmarks saved today.
Group by theme, highlight key insights, and suggest connections between topics.

Bookmarks:
{chr(10).join(summaries)}

Write a concise, engaging digest (3-5 paragraphs)."""

    print(f"\n📰 Daily Digest ({len(rows)} bookmarks from last 24h)\n{'─'*50}")
    print(query_ollama(prompt))
    print("\n" + "─" * 50)


def main():
    parser = argparse.ArgumentParser(description="AI Bookmark Manager - Intelligent bookmark organization")
    parser.add_argument("--add", metavar="URL", help="Add a bookmark with AI summary")
    parser.add_argument("--list", action="store_true", help="List all bookmarks")
    parser.add_argument("--search", metavar="QUERY", help="Semantic search across bookmarks")
    parser.add_argument("--tags", action="store_true", help="Show all tags and counts")
    parser.add_argument("--export", action="store_true", help="Export bookmarks")
    parser.add_argument("--format", choices=["html", "json"], default="html", help="Export format")
    parser.add_argument("--import-file", metavar="FILE", dest="import_file", help="Import from browser bookmarks HTML")
    parser.add_argument("--category", metavar="NAME", help="Filter by category")
    parser.add_argument("--daily-digest", action="store_true", dest="daily_digest", help="AI digest of recent bookmarks")

    args = parser.parse_args()

    if args.add:
        add_bookmark(args.add)
    elif args.list:
        list_bookmarks()
    elif args.search:
        search_bookmarks(args.search)
    elif args.tags:
        show_tags()
    elif args.export:
        export_bookmarks(args.format)
    elif args.import_file:
        import_bookmarks(args.import_file)
    elif args.category:
        list_bookmarks(args.category)
    elif args.daily_digest:
        daily_digest()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
