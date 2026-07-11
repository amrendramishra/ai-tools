#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
Auto-Commit Tool - Smart auto-commit with AI-generated messages.
Watches directories for changes and auto-commits with intelligent messages.
Uses Ollama at localhost:11434 for commit message generation.
"""

import argparse
import asyncio
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

# Configuration
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"
DEFAULT_INTERVAL = 30  # seconds


async def ollama_generate(prompt: str) -> str:
    """Generate text using Ollama."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except httpx.ConnectError:
            return ""
        except Exception as e:
            return ""


def get_git_diff(path: str, staged: bool = False) -> str:
    """Get git diff for the given path."""
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--staged")
    cmd.append("--stat")

    result = subprocess.run(cmd, cwd=path, capture_output=True, text=True)
    stat = result.stdout

    cmd_full = ["git", "diff"]
    if staged:
        cmd_full.append("--staged")

    result_full = subprocess.run(cmd_full, cwd=path, capture_output=True, text=True)
    diff = result_full.stdout

    return stat + "\n" + diff[:3000]  # Limit diff size for AI


def get_untracked_files(path: str) -> list:
    """Get list of untracked files."""
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=path, capture_output=True, text=True
    )
    return [f for f in result.stdout.strip().split("\n") if f]


def get_modified_files(path: str) -> list:
    """Get list of modified files."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=path, capture_output=True, text=True
    )
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


def is_git_repo(path: str) -> bool:
    """Check if path is a git repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=path, capture_output=True, text=True
    )
    return result.returncode == 0


async def generate_commit_message(diff: str, files: list) -> str:
    """Generate a commit message using AI."""
    if not diff and not files:
        return "chore: minor updates"

    files_str = "\n".join(files[:20])
    prompt = (
        "Generate a concise, conventional commit message for these changes. "
        "Use format: type(scope): description\n"
        "Types: feat, fix, docs, style, refactor, test, chore\n"
        "Keep it under 72 characters. Only output the commit message, nothing else.\n\n"
        f"Changed files:\n{files_str}\n\n"
        f"Diff summary:\n{diff[:2000]}"
    )

    message = await ollama_generate(prompt)

    if not message or len(message) > 100 or "\n" in message.split(":")[0] if ":" in message else False:
        # Fallback: generate simple message from file names
        if files:
            first_file = files[0].split()[-1] if " " in files[0] else files[0]
            ext = Path(first_file).suffix
            type_map = {
                ".py": "feat", ".md": "docs", ".yml": "chore",
                ".json": "chore", ".html": "feat", ".css": "style",
                ".js": "feat", ".ts": "feat", ".sh": "chore",
            }
            commit_type = type_map.get(ext, "chore")
            return f"{commit_type}: update {Path(first_file).name}"
        return "chore: update files"

    # Clean up the message
    message = message.strip().strip('"').strip("'")
    first_line = message.split("\n")[0]
    return first_line[:72]


async def auto_commit(path: str):
    """Stage all changes and commit with AI message."""
    modified = get_modified_files(path)
    if not modified:
        return False

    # Stage all changes
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True)

    # Get staged diff
    diff = get_git_diff(path, staged=True)

    # Generate message
    message = await generate_commit_message(diff, modified)

    # Commit
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=path, capture_output=True, text=True
    )

    if result.returncode == 0:
        print(f"  ✅ [{time.strftime('%H:%M:%S')}] Committed: {message}")
        return True
    else:
        print(f"  ⚠️  Commit failed: {result.stderr.strip()}")
        return False


def get_directory_hash(path: str) -> str:
    """Get a hash of the directory state for change detection."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=path, capture_output=True, text=True
    )
    return hashlib.md5(result.stdout.encode()).hexdigest()


async def watch_mode(directory: str, interval: int = DEFAULT_INTERVAL):
    """Watch a directory and auto-commit on changes."""
    path = Path(directory).expanduser().resolve()

    if not path.exists():
        print(f"❌ Directory not found: {path}")
        sys.exit(1)

    if not is_git_repo(str(path)):
        print(f"❌ Not a git repository: {path}")
        sys.exit(1)

    print(f"👁️  Watching: {path}")
    print(f"⏱️  Interval: {interval}s")
    print(f"🤖 AI Model: {OLLAMA_MODEL}")
    print(f"   Press Ctrl+C to stop\n")

    last_hash = get_directory_hash(str(path))

    try:
        while True:
            await asyncio.sleep(interval)
            current_hash = get_directory_hash(str(path))

            if current_hash != last_hash:
                print(f"  🔄 Changes detected...")
                await auto_commit(str(path))
                last_hash = get_directory_hash(str(path))
    except KeyboardInterrupt:
        print("\n\n👋 Stopped watching.")


async def message_mode(path: str):
    """Generate a commit message for current staged changes."""
    target = Path(path).expanduser().resolve()

    if not is_git_repo(str(target)):
        print(f"❌ Not a git repository: {target}")
        sys.exit(1)

    # Check for staged changes
    diff = get_git_diff(str(target), staged=True)
    modified = get_modified_files(str(target))

    if not diff.strip() and not modified:
        print("ℹ️  No changes detected. Stage changes first: git add <files>")
        return

    print("🤖 Generating commit message...\n")
    message = await generate_commit_message(diff, modified)

    print(f"📝 Suggested commit message:\n")
    print(f"   {message}")
    print(f"\n💡 Use it: git commit -m \"{message}\"")


def main():
    parser = argparse.ArgumentParser(
        description="🤖 Auto-Commit - Smart auto-commit with AI-generated messages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --watch .                     Watch current directory
  %(prog)s --watch ~/projects/myapp --interval 60
  %(prog)s --message .                   Generate message for staged changes
        """,
    )

    parser.add_argument("--watch", metavar="DIR", help="Watch directory for changes")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help=f"Check interval in seconds (default: {DEFAULT_INTERVAL})")
    parser.add_argument("--message", metavar="PATH",
                        help="Generate commit message for staged changes")

    args = parser.parse_args()

    if args.watch:
        asyncio.run(watch_mode(args.watch, args.interval))
    elif args.message:
        asyncio.run(message_mode(args.message))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
