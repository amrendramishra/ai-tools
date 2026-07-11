#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
Repo Analyzer - AI-powered repository analysis tool.
Analyzes repo structure, code quality, health, and suggests improvements.
Uses GitHub API + Ollama for intelligent analysis.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

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
        sys.exit(1)
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def ollama_generate(prompt: str) -> str:
    """Generate text using Ollama."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except httpx.ConnectError:
            return "⚠️  Ollama not available. Start it with: ollama serve"
        except Exception as e:
            return f"⚠️  Ollama error: {e}"


async def get_repo_info(repo_name: str) -> dict:
    """Get comprehensive repo information."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Basic repo info
        repo_resp = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_USER}/{repo_name}", headers=get_headers()
        )
        if repo_resp.status_code != 200:
            print(f"❌ Repository not found: {repo_name}")
            sys.exit(1)
        repo = repo_resp.json()

        # Get languages
        lang_resp = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_USER}/{repo_name}/languages",
            headers=get_headers(),
        )
        languages = lang_resp.json() if lang_resp.status_code == 200 else {}

        # Get file tree
        branch = repo.get("default_branch", "main")
        tree_resp = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_USER}/{repo_name}/git/trees/{branch}",
            headers=get_headers(),
            params={"recursive": "1"},
        )
        tree = []
        if tree_resp.status_code == 200:
            tree = [item["path"] for item in tree_resp.json().get("tree", [])]

        # Get recent commits
        commits_resp = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_USER}/{repo_name}/commits",
            headers=get_headers(),
            params={"per_page": 10},
        )
        commits = commits_resp.json() if commits_resp.status_code == 200 else []

        # Get contributors
        contrib_resp = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_USER}/{repo_name}/contributors",
            headers=get_headers(),
        )
        contributors = contrib_resp.json() if contrib_resp.status_code == 200 else []

        # Get open issues count
        issues_resp = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_USER}/{repo_name}/issues",
            headers=get_headers(),
            params={"state": "open", "per_page": 1},
        )

        return {
            "repo": repo,
            "languages": languages,
            "tree": tree,
            "commits": commits if isinstance(commits, list) else [],
            "contributors": contributors if isinstance(contributors, list) else [],
        }


async def cmd_analyze(repo_name: str):
    """Analyze a single repo."""
    print(f"🔬 Analyzing repository: {repo_name}\n")
    print("─" * 60)

    info = await get_repo_info(repo_name)
    repo = info["repo"]
    tree = info["tree"]
    languages = info["languages"]
    commits = info["commits"]

    # Basic info
    print(f"\n📦 Repository: {repo['full_name']}")
    print(f"📝 Description: {repo.get('description', 'None')}")
    print(f"🌿 Default Branch: {repo.get('default_branch', 'main')}")
    print(f"⭐ Stars: {repo['stargazers_count']} | 🍴 Forks: {repo['forks_count']}")
    print(f"👁️  Watchers: {repo['watchers_count']}")
    print(f"📅 Created: {repo['created_at'][:10]}")
    print(f"🔄 Last Updated: {repo['updated_at'][:10]}")
    print(f"📏 Size: {repo['size']} KB")

    # Languages
    print(f"\n🔤 Languages:")
    total_bytes = sum(languages.values()) if languages else 1
    for lang, bytes_count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]:
        pct = bytes_count / total_bytes * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"   {lang:<15} {bar} {pct:.1f}%")

    # Structure analysis
    print(f"\n📁 Structure ({len(tree)} files):")
    dirs = set()
    extensions = {}
    for path in tree:
        parts = path.split("/")
        if len(parts) > 1:
            dirs.add(parts[0])
        ext = path.rsplit(".", 1)[-1] if "." in path else "no-ext"
        extensions[ext] = extensions.get(ext, 0) + 1

    print(f"   Top-level directories: {', '.join(sorted(dirs)[:10])}")
    print(f"   File types: {', '.join(f'.{k}({v})' for k, v in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:8])}")

    # Recent activity
    print(f"\n📜 Recent Commits:")
    for commit in commits[:5]:
        msg = commit["commit"]["message"].split("\n")[0][:60]
        date = commit["commit"]["author"]["date"][:10]
        author = commit["commit"]["author"]["name"]
        print(f"   [{date}] {author}: {msg}")

    # AI Analysis
    print(f"\n🤖 AI Analysis:")
    print("─" * 40)

    tree_sample = "\n".join(tree[:40])
    prompt = (
        f"Analyze this GitHub repository and provide concise insights:\n"
        f"Name: {repo['name']}\n"
        f"Description: {repo.get('description', 'None')}\n"
        f"Language: {repo.get('language', 'None')}\n"
        f"Stars: {repo['stargazers_count']}, Forks: {repo['forks_count']}\n"
        f"Size: {repo['size']}KB, Files: {len(tree)}\n"
        f"File structure:\n{tree_sample}\n\n"
        f"Provide:\n"
        f"1. Code quality assessment (based on structure)\n"
        f"2. Architecture observations\n"
        f"3. Missing best practices\n"
        f"4. 3 specific improvement suggestions\n"
        f"Keep it concise and actionable."
    )

    analysis = await ollama_generate(prompt)
    print(analysis)


async def cmd_compare(repo1: str, repo2: str):
    """Compare two repositories."""
    print(f"⚖️  Comparing: {repo1} vs {repo2}\n")
    print("─" * 60)

    info1 = await get_repo_info(repo1)
    info2 = await get_repo_info(repo2)

    r1, r2 = info1["repo"], info2["repo"]

    metrics = [
        ("Stars", r1["stargazers_count"], r2["stargazers_count"]),
        ("Forks", r1["forks_count"], r2["forks_count"]),
        ("Size (KB)", r1["size"], r2["size"]),
        ("Open Issues", r1["open_issues_count"], r2["open_issues_count"]),
        ("Watchers", r1["watchers_count"], r2["watchers_count"]),
    ]

    print(f"\n{'Metric':<20} {repo1:<20} {repo2:<20} {'Winner'}")
    print("─" * 70)
    for metric, v1, v2 in metrics:
        winner = "←" if v1 > v2 else ("→" if v2 > v1 else "=")
        print(f"{metric:<20} {v1:<20} {v2:<20} {winner}")

    # Languages comparison
    print(f"\n🔤 Languages:")
    print(f"   {repo1}: {r1.get('language', 'N/A')}")
    print(f"   {repo2}: {r2.get('language', 'N/A')}")

    # Activity comparison
    updated1 = datetime.fromisoformat(r1["updated_at"].replace("Z", "+00:00"))
    updated2 = datetime.fromisoformat(r2["updated_at"].replace("Z", "+00:00"))
    print(f"\n📅 Last Updated:")
    print(f"   {repo1}: {updated1.strftime('%Y-%m-%d')}")
    print(f"   {repo2}: {updated2.strftime('%Y-%m-%d')}")
    more_recent = repo1 if updated1 > updated2 else repo2
    print(f"   More active: {more_recent}")

    # AI Comparison
    print(f"\n🤖 AI Comparison:")
    print("─" * 40)

    prompt = (
        f"Compare these two repositories briefly:\n"
        f"Repo 1: {r1['name']} - {r1.get('description', 'N/A')} "
        f"({r1.get('language', 'N/A')}, {r1['stargazers_count']} stars, {len(info1['tree'])} files)\n"
        f"Repo 2: {r2['name']} - {r2.get('description', 'N/A')} "
        f"({r2.get('language', 'N/A')}, {r2['stargazers_count']} stars, {len(info2['tree'])} files)\n\n"
        f"Compare: purpose, code quality (from structure), community engagement, "
        f"and recommend which to focus on."
    )

    comparison = await ollama_generate(prompt)
    print(comparison)


async def cmd_health(repo_name: str = None):
    """Check repo health (license, CI, tests, docs)."""
    if repo_name:
        repos_to_check = [repo_name]
    else:
        # Check all repos
        async with httpx.AsyncClient(timeout=30.0) as client:
            repos = []
            page = 1
            while True:
                resp = await client.get(
                    f"{GITHUB_API}/user/repos",
                    headers=get_headers(),
                    params={"per_page": 100, "page": page},
                )
                data = resp.json()
                if not data:
                    break
                repos.extend(data)
                page += 1
        repos_to_check = [r["name"] for r in repos]

    print(f"🏥 Health Check {'for ' + repo_name if repo_name else f'({len(repos_to_check)} repos)'}\n")
    print(f"{'Repository':<30} {'README':<8} {'License':<9} {'CI':<5} {'Tests':<7} {'Score'}")
    print("─" * 75)

    async with httpx.AsyncClient(timeout=30.0) as client:
        for name in repos_to_check[:30]:  # Limit to avoid rate limiting
            checks = {"readme": False, "license": False, "ci": False, "tests": False}

            # Get tree
            tree_resp = await client.get(
                f"{GITHUB_API}/repos/{GITHUB_USER}/{name}/git/trees/main",
                headers=get_headers(),
                params={"recursive": "1"},
            )

            if tree_resp.status_code == 200:
                tree_paths = [item["path"].lower() for item in tree_resp.json().get("tree", [])]

                checks["readme"] = any("readme" in p for p in tree_paths)
                checks["license"] = any("license" in p for p in tree_paths)
                checks["ci"] = any(
                    ".github/workflows" in p or "jenkinsfile" in p or
                    ".travis.yml" in p or ".circleci" in p
                    for p in tree_paths
                )
                checks["tests"] = any(
                    "test" in p or "spec" in p or "__tests__" in p
                    for p in tree_paths
                )

            score = sum(checks.values())
            score_bar = "🟢" * score + "🔴" * (4 - score)

            print(
                f"{name:<30} "
                f"{'✅' if checks['readme'] else '❌':<8} "
                f"{'✅' if checks['license'] else '❌':<9} "
                f"{'✅' if checks['ci'] else '❌':<5} "
                f"{'✅' if checks['tests'] else '❌':<7} "
                f"{score_bar} {score}/4"
            )

    print(f"\n💡 Tips:")
    print(f"   - Add LICENSE: gh repo edit --add-license mit")
    print(f"   - Add CI: Create .github/workflows/ci.yml")
    print(f"   - Add tests: Create tests/ directory with test files")


async def cmd_suggest_actions():
    """AI suggests next steps for each repo."""
    print(f"💡 AI Suggestions for {GITHUB_USER}'s Repos\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        repos = []
        page = 1
        while True:
            resp = await client.get(
                f"{GITHUB_API}/user/repos",
                headers=get_headers(),
                params={"per_page": 100, "page": page, "sort": "updated"},
            )
            data = resp.json()
            if not data:
                break
            repos.extend(data)
            page += 1

    # Focus on most recent repos
    recent_repos = repos[:10]

    repos_summary = "\n".join(
        f"- {r['name']}: {r.get('description', 'No desc')} "
        f"(lang: {r.get('language', 'N/A')}, stars: {r['stargazers_count']}, "
        f"issues: {r['open_issues_count']}, updated: {r['updated_at'][:10]})"
        for r in recent_repos
    )

    prompt = (
        f"Here are the 10 most recently updated repos for a developer:\n"
        f"{repos_summary}\n\n"
        f"For each repo, suggest ONE specific actionable next step. "
        f"Consider: adding features, fixing issues, improving docs, "
        f"setting up CI/CD, adding tests, or marketing/sharing. "
        f"Be specific and practical. Format as a list."
    )

    print("🤖 Analyzing your repos...\n")
    suggestions = await ollama_generate(prompt)
    print(suggestions)


def main():
    parser = argparse.ArgumentParser(
        description="🔬 Repo Analyzer - AI-powered repository analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --repo my-project              Analyze a repo
  %(prog)s --compare repo1 repo2          Compare two repos
  %(prog)s --health                       Health check all repos
  %(prog)s --health --repo my-project     Health check specific repo
  %(prog)s --suggest-actions              AI suggestions for all repos
        """,
    )

    parser.add_argument("--repo", metavar="NAME", help="Repository to analyze")
    parser.add_argument("--compare", nargs=2, metavar=("REPO1", "REPO2"),
                        help="Compare two repos")
    parser.add_argument("--health", action="store_true", help="Check repo health")
    parser.add_argument("--suggest-actions", action="store_true",
                        help="AI suggests next steps")

    args = parser.parse_args()

    if args.compare:
        asyncio.run(cmd_compare(args.compare[0], args.compare[1]))
    elif args.health:
        asyncio.run(cmd_health(args.repo))
    elif args.suggest_actions:
        asyncio.run(cmd_suggest_actions())
    elif args.repo:
        asyncio.run(cmd_analyze(args.repo))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
