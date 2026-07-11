#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
GitHub Toolkit - All-in-one GitHub CLI tool for amrendramishra.
Uses GITHUB_TOKEN from environment. Ollama at localhost:11434 for AI features.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Configuration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_API = "https://api.github.com"
GITHUB_USER = "amrendramishra"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"


def get_headers():
    """Get GitHub API headers."""
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN environment variable not set.")
        print("   Export it: export GITHUB_TOKEN=ghp_your_token_here")
        sys.exit(1)
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def ollama_generate(prompt: str, model: str = OLLAMA_MODEL) -> str:
    """Generate text using Ollama."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except httpx.ConnectError:
            return "⚠️  Ollama not available at localhost:11434. Start it with: ollama serve"
        except Exception as e:
            return f"⚠️  Ollama error: {e}"


async def fetch_all_repos() -> list:
    """Fetch all repos for the authenticated user with pagination."""
    repos = []
    page = 1
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            response = await client.get(
                f"{GITHUB_API}/user/repos",
                headers=get_headers(),
                params={"per_page": 100, "page": page, "sort": "updated"},
            )
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            repos.extend(data)
            page += 1
    return repos


async def cmd_repos():
    """List all repos with stats."""
    print(f"📦 Fetching repos for {GITHUB_USER}...\n")
    repos = await fetch_all_repos()

    print(f"{'Repository':<40} {'⭐':<6} {'🍴':<6} {'Last Updated':<20} {'Visibility':<10}")
    print("─" * 90)

    for repo in repos:
        updated = datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00"))
        updated_str = updated.strftime("%Y-%m-%d %H:%M")
        visibility = "🔒 Private" if repo["private"] else "🌐 Public"
        print(
            f"{repo['name']:<40} {repo['stargazers_count']:<6} "
            f"{repo['forks_count']:<6} {updated_str:<20} {visibility:<10}"
        )

    print(f"\n📊 Total: {len(repos)} repositories")


async def cmd_create(name: str, description: str = "", private: bool = False):
    """Create a new repository."""
    print(f"🔨 Creating repository: {name}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{GITHUB_API}/user/repos",
            headers=get_headers(),
            json={
                "name": name,
                "description": description,
                "private": private,
                "auto_init": True,
            },
        )
        if response.status_code == 201:
            repo = response.json()
            print(f"✅ Repository created: {repo['html_url']}")
            print(f"   Clone: git clone {repo['clone_url']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.json().get('message', '')}")


async def cmd_clone_all(directory: str = "./repos"):
    """Clone all repos to a directory."""
    repos = await fetch_all_repos()
    target = Path(directory).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    print(f"📥 Cloning {len(repos)} repos to {target}...\n")

    for repo in repos:
        repo_dir = target / repo["name"]
        if repo_dir.exists():
            print(f"  ⏭️  {repo['name']} (already exists, skipping)")
            continue
        print(f"  📦 Cloning {repo['name']}...")
        clone_url = repo["clone_url"].replace(
            "https://", f"https://{GITHUB_TOKEN}@"
        )
        result = subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, str(repo_dir)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  ✅ {repo['name']}")
        else:
            print(f"  ❌ {repo['name']}: {result.stderr.strip()}")

    print(f"\n✅ Done! Repos cloned to {target}")


async def cmd_backup(directory: str = "./backup"):
    """Backup all repos (clone new, pull existing)."""
    repos = await fetch_all_repos()
    target = Path(directory).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    print(f"💾 Backing up {len(repos)} repos to {target}...\n")

    for repo in repos:
        repo_dir = target / repo["name"]
        if repo_dir.exists() and (repo_dir / ".git").exists():
            print(f"  🔄 Pulling {repo['name']}...")
            result = subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=str(repo_dir), capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"  ✅ {repo['name']} (updated)")
            else:
                print(f"  ⚠️  {repo['name']}: {result.stderr.strip()}")
        else:
            print(f"  📦 Cloning {repo['name']}...")
            clone_url = repo["clone_url"].replace(
                "https://", f"https://{GITHUB_TOKEN}@"
            )
            result = subprocess.run(
                ["git", "clone", clone_url, str(repo_dir)],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"  ✅ {repo['name']} (cloned)")
            else:
                print(f"  ❌ {repo['name']}: {result.stderr.strip()}")

    print(f"\n✅ Backup complete! Location: {target}")


async def cmd_stats():
    """Show full profile stats."""
    print(f"📊 Profile Stats for {GITHUB_USER}\n")

    repos = await fetch_all_repos()
    total_stars = sum(r["stargazers_count"] for r in repos)
    total_forks = sum(r["forks_count"] for r in repos)
    languages = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get user info
        user_resp = await client.get(
            f"{GITHUB_API}/users/{GITHUB_USER}", headers=get_headers()
        )
        user = user_resp.json()

        # Get languages from repos
        for repo in repos[:20]:  # Sample first 20 repos
            lang_resp = await client.get(
                f"{GITHUB_API}/repos/{GITHUB_USER}/{repo['name']}/languages",
                headers=get_headers(),
            )
            if lang_resp.status_code == 200:
                for lang, bytes_count in lang_resp.json().items():
                    languages[lang] = languages.get(lang, 0) + bytes_count

    print(f"  👤 Name: {user.get('name', GITHUB_USER)}")
    print(f"  📍 Location: {user.get('location', 'N/A')}")
    print(f"  👥 Followers: {user.get('followers', 0)} | Following: {user.get('following', 0)}")
    print(f"  📦 Repos: {len(repos)} (Public: {user.get('public_repos', 0)})")
    print(f"  ⭐ Total Stars: {total_stars}")
    print(f"  🍴 Total Forks: {total_forks}")
    print(f"\n  🔤 Top Languages:")

    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10]
    total_bytes = sum(b for _, b in sorted_langs)
    for lang, bytes_count in sorted_langs:
        pct = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"    {lang:<15} {bar} {pct:.1f}%")


async def cmd_search(query: str):
    """Search across all repos' code."""
    print(f"🔍 Searching for '{query}' across your repos...\n")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{GITHUB_API}/search/code",
            headers=get_headers(),
            params={"q": f"{query} user:{GITHUB_USER}", "per_page": 30},
        )
        if response.status_code == 200:
            results = response.json()
            print(f"Found {results['total_count']} results:\n")
            for item in results.get("items", []):
                print(f"  📄 {item['repository']['name']}/{item['path']}")
                print(f"     {item['html_url']}")
                print()
        else:
            print(f"❌ Search failed: {response.status_code}")


async def cmd_issues():
    """List open issues across all repos."""
    print(f"🐛 Open Issues for {GITHUB_USER}\n")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{GITHUB_API}/issues",
            headers=get_headers(),
            params={"filter": "all", "state": "open", "per_page": 50},
        )
        response.raise_for_status()
        issues = response.json()

    if not issues:
        print("  🎉 No open issues!")
        return

    for issue in issues:
        if "pull_request" in issue:
            continue
        repo_name = issue["repository"]["name"] if "repository" in issue else "unknown"
        labels = ", ".join(l["name"] for l in issue.get("labels", []))
        print(f"  [{repo_name}] #{issue['number']}: {issue['title']}")
        if labels:
            print(f"    🏷️  {labels}")
        print(f"    🔗 {issue['html_url']}")
        print()


async def cmd_pr_review():
    """AI reviews open PRs using Ollama."""
    print(f"🤖 AI PR Review for {GITHUB_USER}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get open PRs
        response = await client.get(
            f"{GITHUB_API}/search/issues",
            headers=get_headers(),
            params={"q": f"is:pr is:open author:{GITHUB_USER}", "per_page": 10},
        )
        response.raise_for_status()
        prs = response.json().get("items", [])

        if not prs:
            print("  No open PRs found.")
            return

        for pr in prs:
            print(f"\n  📋 PR #{pr['number']}: {pr['title']}")
            print(f"     {pr['html_url']}")

            # Get PR diff
            repo_full_name = pr["repository_url"].split("/repos/")[1]
            diff_resp = await client.get(
                f"{GITHUB_API}/repos/{repo_full_name}/pulls/{pr['number']}",
                headers={**get_headers(), "Accept": "application/vnd.github.v3.diff"},
            )

            if diff_resp.status_code == 200:
                diff_text = diff_resp.text[:3000]  # Limit diff size
                prompt = (
                    f"Review this Pull Request diff concisely. Highlight issues, "
                    f"suggest improvements, rate code quality 1-10:\n\n{diff_text}"
                )
                review = await ollama_generate(prompt)
                print(f"\n  🤖 AI Review:\n")
                for line in review.split("\n"):
                    print(f"     {line}")
            print()


async def cmd_readme_gen(repo: str):
    """AI generates README for a repo."""
    print(f"📝 Generating README for {repo}...\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get repo info
        repo_resp = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_USER}/{repo}", headers=get_headers()
        )
        if repo_resp.status_code != 200:
            print(f"❌ Repo not found: {repo}")
            return
        repo_data = repo_resp.json()

        # Get file tree
        tree_resp = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_USER}/{repo}/git/trees/main",
            headers=get_headers(),
            params={"recursive": "1"},
        )
        tree = []
        if tree_resp.status_code == 200:
            tree = [item["path"] for item in tree_resp.json().get("tree", [])[:50]]

    prompt = (
        f"Generate a professional README.md for this GitHub repository:\n"
        f"Name: {repo_data['name']}\n"
        f"Description: {repo_data.get('description', 'N/A')}\n"
        f"Language: {repo_data.get('language', 'N/A')}\n"
        f"Topics: {', '.join(repo_data.get('topics', []))}\n"
        f"File structure:\n{chr(10).join(tree)}\n\n"
        f"Include: Title, badges, description, features, installation, usage, "
        f"contributing, and license sections. Use emojis and make it visually appealing."
    )

    readme = await ollama_generate(prompt)
    print(readme)

    # Optionally save
    save_path = Path(f"README_{repo}.md")
    save_path.write_text(readme)
    print(f"\n💾 Saved to {save_path}")


async def cmd_commit_history():
    """Show recent commits across all repos."""
    print(f"📜 Recent Commits for {GITHUB_USER}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{GITHUB_API}/users/{GITHUB_USER}/events",
            headers=get_headers(),
            params={"per_page": 50},
        )
        response.raise_for_status()
        events = response.json()

    push_events = [e for e in events if e["type"] == "PushEvent"]

    for event in push_events[:20]:
        repo_name = event["repo"]["name"].split("/")[-1]
        created = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
        created_str = created.strftime("%Y-%m-%d %H:%M")

        for commit in event["payload"].get("commits", []):
            msg = commit["message"].split("\n")[0][:60]
            print(f"  [{created_str}] {repo_name}: {msg}")


async def cmd_cleanup():
    """Find repos with no recent activity, suggest archiving."""
    print(f"🧹 Cleanup Analysis for {GITHUB_USER}\n")
    repos = await fetch_all_repos()

    now = datetime.now(timezone.utc)
    stale_repos = []

    for repo in repos:
        updated = datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00"))
        days_inactive = (now - updated).days
        if days_inactive > 180:
            stale_repos.append((repo, days_inactive))

    stale_repos.sort(key=lambda x: x[1], reverse=True)

    if not stale_repos:
        print("  🎉 All repos are active! Nothing to clean up.")
        return

    print(f"  Found {len(stale_repos)} repos inactive for 6+ months:\n")
    print(f"  {'Repository':<35} {'Days Inactive':<15} {'Stars':<8} {'Action'}")
    print("  " + "─" * 75)

    for repo, days in stale_repos:
        action = "📦 Archive" if repo["stargazers_count"] == 0 else "⚠️  Review"
        print(
            f"  {repo['name']:<35} {days:<15} {repo['stargazers_count']:<8} {action}"
        )

    print(f"\n  💡 Tip: Archive repos with `gh repo archive <repo-name>`")


async def cmd_deploy_pages(repo: str):
    """Enable GitHub Pages for a repo."""
    print(f"🌐 Enabling GitHub Pages for {repo}...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{GITHUB_API}/repos/{GITHUB_USER}/{repo}/pages",
            headers=get_headers(),
            json={"source": {"branch": "main", "path": "/"}},
        )
        if response.status_code in (201, 200):
            data = response.json()
            print(f"✅ Pages enabled!")
            print(f"   URL: {data.get('html_url', f'https://{GITHUB_USER}.github.io/{repo}/')}")
        elif response.status_code == 409:
            print(f"ℹ️  Pages already enabled for {repo}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")


async def cmd_create_gist(file_path: str):
    """Create a gist from file."""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ File not found: {file_path}")
        return

    content = path.read_text()
    filename = path.name

    print(f"📋 Creating gist from {filename}...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{GITHUB_API}/gists",
            headers=get_headers(),
            json={
                "description": f"Gist created from {filename}",
                "public": True,
                "files": {filename: {"content": content}},
            },
        )
        if response.status_code == 201:
            gist = response.json()
            print(f"✅ Gist created: {gist['html_url']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")


async def cmd_profile_readme():
    """AI generates a profile README.md."""
    print(f"✨ Generating Profile README for {GITHUB_USER}...\n")

    repos = await fetch_all_repos()
    total_stars = sum(r["stargazers_count"] for r in repos)
    languages = set()
    for r in repos:
        if r.get("language"):
            languages.add(r["language"])

    top_repos = sorted(repos, key=lambda x: x["stargazers_count"], reverse=True)[:5]
    top_repos_text = "\n".join(
        f"- {r['name']} ({r['stargazers_count']}⭐): {r.get('description', 'N/A')}"
        for r in top_repos
    )

    prompt = (
        f"Generate a stunning GitHub profile README.md for user '{GITHUB_USER}'.\n"
        f"Stats: {len(repos)} repos, {total_stars} total stars\n"
        f"Languages: {', '.join(sorted(languages))}\n"
        f"Top repos:\n{top_repos_text}\n\n"
        f"Include: animated greeting, about section, tech stack with badges, "
        f"GitHub stats cards (use github-readme-stats), top repos showcase, "
        f"and a connect section. Make it visually impressive with emojis and formatting."
    )

    readme = await ollama_generate(prompt)
    print(readme)

    save_path = Path("PROFILE_README.md")
    save_path.write_text(readme)
    print(f"\n💾 Saved to {save_path}")
    print(f"   Deploy: Copy to {GITHUB_USER}/{GITHUB_USER} repo as README.md")


def main():
    parser = argparse.ArgumentParser(
        description="🛠️  GitHub Toolkit - All-in-one CLI for managing your GitHub presence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --repos                    List all repositories
  %(prog)s --create my-new-repo --description "Cool project" --private
  %(prog)s --stats                    Show profile statistics
  %(prog)s --search "async def"       Search code across repos
  %(prog)s --pr-review                AI review of open PRs
  %(prog)s --readme-gen my-repo       Generate README with AI
  %(prog)s --profile-readme           Generate profile README
  %(prog)s --cleanup                  Find stale repos
        """,
    )

    parser.add_argument("--repos", action="store_true", help="List all repos with stats")
    parser.add_argument("--create", metavar="NAME", help="Create a new repository")
    parser.add_argument("--description", default="", help="Description for new repo")
    parser.add_argument("--private", action="store_true", help="Make new repo private")
    parser.add_argument("--clone-all", metavar="DIR", nargs="?", const="./repos", help="Clone all repos")
    parser.add_argument("--backup", metavar="DIR", nargs="?", const="./backup", help="Backup all repos")
    parser.add_argument("--stats", action="store_true", help="Show profile stats")
    parser.add_argument("--search", metavar="QUERY", help="Search across repos")
    parser.add_argument("--issues", action="store_true", help="List open issues")
    parser.add_argument("--pr-review", action="store_true", help="AI review open PRs")
    parser.add_argument("--readme-gen", metavar="REPO", help="AI generate README for repo")
    parser.add_argument("--commit-history", action="store_true", help="Recent commits")
    parser.add_argument("--cleanup", action="store_true", help="Find stale repos")
    parser.add_argument("--deploy-pages", metavar="REPO", help="Enable GitHub Pages")
    parser.add_argument("--create-gist", metavar="FILE", help="Create gist from file")
    parser.add_argument("--profile-readme", action="store_true", help="Generate profile README")

    args = parser.parse_args()

    if args.repos:
        asyncio.run(cmd_repos())
    elif args.create:
        asyncio.run(cmd_create(args.create, args.description, args.private))
    elif args.clone_all is not None:
        asyncio.run(cmd_clone_all(args.clone_all))
    elif args.backup is not None:
        asyncio.run(cmd_backup(args.backup))
    elif args.stats:
        asyncio.run(cmd_stats())
    elif args.search:
        asyncio.run(cmd_search(args.search))
    elif args.issues:
        asyncio.run(cmd_issues())
    elif args.pr_review:
        asyncio.run(cmd_pr_review())
    elif args.readme_gen:
        asyncio.run(cmd_readme_gen(args.readme_gen))
    elif args.commit_history:
        asyncio.run(cmd_commit_history())
    elif args.cleanup:
        asyncio.run(cmd_cleanup())
    elif args.deploy_pages:
        asyncio.run(cmd_deploy_pages(args.deploy_pages))
    elif args.create_gist:
        asyncio.run(cmd_create_gist(args.create_gist))
    elif args.profile_readme:
        asyncio.run(cmd_profile_readme())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
