#!/usr/bin/env python3
"""AI-Powered Finder - Natural language file search using Ollama."""

import argparse
import json
import os
import platform
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests

# Configuration
OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2"
DB_PATH = Path.home() / ".ai_finder_index.db"
DEFAULT_SEARCH_DIRS = [
    Path.home() / "Documents",
    Path.home() / "Downloads",
    Path.home() / "Desktop",
    Path.home() / "IdeaProjects",
]


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def get_db():
    """Get SQLite database connection."""
    db = sqlite3.connect(str(DB_PATH))
    db.execute("""
        CREATE TABLE IF NOT EXISTS file_index (
            path TEXT PRIMARY KEY,
            name TEXT,
            extension TEXT,
            size INTEGER,
            modified_date TEXT,
            created_date TEXT,
            parent_dir TEXT,
            indexed_at TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS index_meta (
            directory TEXT PRIMARY KEY,
            last_indexed TEXT,
            file_count INTEGER
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_name ON file_index(name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_ext ON file_index(extension)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_modified ON file_index(modified_date)")
    db.commit()
    return db


def query_ollama(prompt, model=MODEL):
    """Query Ollama for AI interpretation."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}Error: Cannot connect to Ollama at {OLLAMA_URL}")
        print(f"Make sure Ollama is running: ollama serve{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}Error querying Ollama: {e}{Colors.RESET}")
        return ""


def fuzzy_match(query, text, threshold=0.4):
    """Simple fuzzy matching based on character sequences."""
    query = query.lower()
    text = text.lower()
    if query in text:
        return 1.0
    def bigrams(s):
        return set(s[i:i+2] for i in range(len(s) - 1))
    q_bigrams = bigrams(query)
    t_bigrams = bigrams(text)
    if not q_bigrams or not t_bigrams:
        return 0.0
    intersection = q_bigrams & t_bigrams
    union = q_bigrams | t_bigrams
    score = len(intersection) / len(union) if union else 0.0
    query_words = set(query.split())
    text_words = set(text.replace("-", " ").replace("_", " ").split())
    word_matches = query_words & text_words
    if word_matches:
        score += 0.3 * (len(word_matches) / len(query_words))
    return min(score, 1.0)


def format_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024*1024):.1f} MB"
    else:
        return f"{size_bytes / (1024*1024*1024):.1f} GB"


def index_directory(directory, db):
    """Build search index for a directory."""
    directory = Path(directory).expanduser().resolve()
    if not directory.exists():
        print(f"{Colors.YELLOW}Warning: Directory does not exist: {directory}{Colors.RESET}")
        return 0
    print(f"{Colors.CYAN}Indexing: {directory}{Colors.RESET}")
    count = 0
    skip_dirs = {"node_modules", "__pycache__", ".git", "venv", ".venv", "target", "build", "dist"}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in skip_dirs]
        for filename in files:
            if filename.startswith("."):
                continue
            filepath = Path(root) / filename
            try:
                stat = filepath.stat()
                db.execute(
                    """INSERT OR REPLACE INTO file_index
                       (path, name, extension, size, modified_date, created_date, parent_dir, indexed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(filepath), filename, filepath.suffix.lower(), stat.st_size,
                        datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        str(filepath.parent), datetime.now().isoformat(),
                    ),
                )
                count += 1
            except (PermissionError, OSError):
                continue
    db.execute(
        "INSERT OR REPLACE INTO index_meta (directory, last_indexed, file_count) VALUES (?, ?, ?)",
        (str(directory), datetime.now().isoformat(), count),
    )
    db.commit()
    print(f"{Colors.GREEN}  Indexed {count} files{Colors.RESET}")
    return count


def interpret_query(query):
    """Use AI to interpret natural language query into search criteria."""
    prompt = f"""Convert this file search query into JSON search criteria.
Query: "{query}"
Return ONLY valid JSON with these optional fields:
- "keywords": list of filename keywords to search for
- "extensions": list of file extensions (e.g., [".pdf", ".doc"])
- "date_after": ISO date string if time reference mentioned
- "date_before": ISO date string if applicable
- "min_size": minimum file size in bytes if mentioned
- "max_size": maximum file size in bytes if mentioned
Current date: {datetime.now().strftime('%Y-%m-%d')}
Respond with ONLY the JSON object."""
    response = query_ollama(prompt)
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass
    return {"keywords": query.lower().split()}


def search_files(query, db, limit=20):
    """Search indexed files using AI-interpreted criteria."""
    print(f"{Colors.CYAN}🔍 Interpreting query...{Colors.RESET}")
    criteria = interpret_query(query)
    print(f"{Colors.DIM}Criteria: {json.dumps(criteria, indent=2)}{Colors.RESET}\n")
    conditions = []
    params = []
    if criteria.get("extensions"):
        placeholders = ",".join("?" * len(criteria["extensions"]))
        conditions.append(f"extension IN ({placeholders})")
        params.extend(criteria["extensions"])
    if criteria.get("date_after"):
        conditions.append("modified_date >= ?")
        params.append(criteria["date_after"])
    if criteria.get("date_before"):
        conditions.append("modified_date <= ?")
        params.append(criteria["date_before"])
    if criteria.get("min_size"):
        conditions.append("size >= ?")
        params.append(criteria["min_size"])
    if criteria.get("max_size"):
        conditions.append("size <= ?")
        params.append(criteria["max_size"])
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    sql = f"SELECT path, name, extension, size, modified_date FROM file_index WHERE {where_clause}"
    cursor = db.execute(sql, params)
    results = cursor.fetchall()
    keywords = criteria.get("keywords", query.lower().split())
    scored = []
    for path, name, ext, size, modified in results:
        score = 0
        for kw in keywords:
            score += fuzzy_match(kw, name.lower())
            if kw in path.lower():
                score += 0.2
        if score > 0.2:
            scored.append((score, path, name, ext, size, modified))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]


def show_recent(db, count=20):
    """Show recently modified files with AI descriptions."""
    cursor = db.execute(
        "SELECT path, name, extension, size, modified_date FROM file_index ORDER BY modified_date DESC LIMIT ?",
        (count,),
    )
    results = cursor.fetchall()
    if not results:
        print(f"{Colors.YELLOW}No files indexed. Run --index first.{Colors.RESET}")
        return
    print(f"{Colors.BOLD}📂 Recently Modified Files:{Colors.RESET}\n")
    file_list = "\n".join(f"- {n} ({e}, {format_size(s)})" for _, n, e, s, _ in results[:10])
    prompt = f"For each file, give a 5-word description based on name:\n{file_list}\nOne per line."
    descriptions = query_ollama(prompt).split("\n")
    for i, (path, name, ext, size, modified) in enumerate(results):
        mod_date = modified[:10] if modified else "unknown"
        desc = descriptions[i].strip("- ") if i < len(descriptions) else ""
        print(f"  {Colors.GREEN}{i+1:2}.{Colors.RESET} {Colors.BOLD}{name}{Colors.RESET} "
              f"{Colors.DIM}({format_size(size)}, {mod_date}){Colors.RESET}")
        if desc:
            print(f"      {Colors.CYAN}{desc}{Colors.RESET}")


def open_file(filepath):
    """Open a file with the default application."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", filepath], check=True)
        elif system == "Linux":
            subprocess.run(["xdg-open", filepath], check=True)
        else:
            os.startfile(filepath)
        print(f"{Colors.GREEN}✓ Opened: {filepath}{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}Error opening file: {e}{Colors.RESET}")


def display_results(results, open_flag=False):
    """Display search results."""
    if not results:
        print(f"{Colors.YELLOW}No matching files found.{Colors.RESET}")
        print(f"{Colors.DIM}Try running --index to build/update the search index.{Colors.RESET}")
        return
    print(f"{Colors.BOLD}Found {len(results)} matching files:{Colors.RESET}\n")
    for i, (score, path, name, ext, size, modified) in enumerate(results):
        mod_date = modified[:10] if modified else "unknown"
        bar = "█" * int(score * 5) + "░" * (5 - int(score * 5))
        print(f"  {Colors.GREEN}{i+1:2}.{Colors.RESET} {Colors.BOLD}{name}{Colors.RESET}")
        print(f"      {Colors.DIM}{path}{Colors.RESET}")
        print(f"      {Colors.CYAN}{format_size(size)}{Colors.RESET} | "
              f"{Colors.YELLOW}{mod_date}{Colors.RESET} | Score: {bar} {score:.2f}\n")
    if open_flag and results:
        open_file(results[0][1])


def main():
    parser = argparse.ArgumentParser(description="AI-Powered Finder - Natural language file search")
    parser.add_argument("--find", type=str, help="Natural language search query")
    parser.add_argument("--index", type=str, nargs="?", const="all", help="Build search index")
    parser.add_argument("--recent", action="store_true", help="Show recently modified files")
    parser.add_argument("--open", action="store_true", help="Open the top result")
    parser.add_argument("--limit", type=int, default=20, help="Max results to show")
    args = parser.parse_args()

    if not any([args.find, args.index, args.recent]):
        parser.print_help()
        sys.exit(0)

    db = get_db()
    if args.index:
        if args.index == "all":
            print(f"{Colors.BOLD}🗂️  Indexing default directories...{Colors.RESET}\n")
            total = sum(index_directory(d, db) for d in DEFAULT_SEARCH_DIRS)
            print(f"\n{Colors.GREEN}✓ Total indexed: {total} files{Colors.RESET}")
        else:
            index_directory(args.index, db)
    elif args.recent:
        show_recent(db, count=args.limit)
    elif args.find:
        results = search_files(args.find, db, limit=args.limit)
        display_results(results, open_flag=args.open)
    db.close()


if __name__ == "__main__":
    main()
