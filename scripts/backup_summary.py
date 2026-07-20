#!/usr/bin/env python3
"""
Backup Summary Script for GitHub Actions
Lists all user repos and summarizes recent changes.
"""

import os
import json
import requests
from datetime import datetime, timedelta

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "amrendramishra")
GITHUB_API = "https://api.github.com"


def get_user_repos():
    """Get all repos for the user."""
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    repos = []
    page = 1
    while True:
        url = f"{GITHUB_API}/user/repos?per_page=100&page={page}&sort=updated"
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"Error fetching repos: {response.status_code}")
            break
        data = response.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos


def get_recent_commits(repo_full_name, since_days=1):
    """Get recent commits for a repo."""
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    since = (datetime.utcnow() - timedelta(days=since_days)).isoformat() + "Z"
    url = f"{GITHUB_API}/repos/{repo_full_name}/commits?since={since}&per_page=10"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"  Error getting commits for {repo_full_name}: {e}")
    return []


def main():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    print(f"💾 Generating backup summary for {today}")
    os.makedirs("backups", exist_ok=True)

    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN not set")
        return

    repos = get_user_repos()
    print(f"  Found {len(repos)} repositories")

    summary = {
        "date": today,
        "generated_at": datetime.utcnow().isoformat(),
        "total_repos": len(repos),
        "repos_with_changes": 0,
        "repos": []
    }

    for repo in repos:
        repo_info = {
            "name": repo["full_name"],
            "description": repo.get("description", ""),
            "language": repo.get("language", ""),
            "updated_at": repo.get("updated_at", ""),
            "recent_commits": []
        }
        commits = get_recent_commits(repo["full_name"])
        if commits:
            summary["repos_with_changes"] += 1
            for commit in commits[:5]:
                repo_info["recent_commits"].append({
                    "sha": commit.get("sha", "")[:7],
                    "message": commit.get("commit", {}).get("message", "").split("\n")[0],
                    "author": commit.get("commit", {}).get("author", {}).get("name", ""),
                    "date": commit.get("commit", {}).get("author", {}).get("date", "")
                })
        summary["repos"].append(repo_info)

    # Save JSON
    json_file = f"backups/{today}_summary.json"
    with open(json_file, "w") as f:
        json.dump(summary, f, indent=2)

    # Save markdown
    md_file = f"backups/{today}_summary.md"
    with open(md_file, "w") as f:
        f.write(f"# 💾 Daily Backup Summary - {today}\n\n")
        f.write(f"**Total Repos:** {summary['total_repos']}\n")
        f.write(f"**Repos with Changes (24h):** {summary['repos_with_changes']}\n\n---\n\n")
        for repo in summary["repos"]:
            if repo["recent_commits"]:
                f.write(f"## 📁 {repo['name']}\n\n")
                for commit in repo["recent_commits"]:
                    f.write(f"- `{commit['sha']}` {commit['message']} ({commit['author']})\n")
                f.write("\n")

    with open("backups/latest.json", "w") as f:
        json.dump({"date": today, "json": json_file, "markdown": md_file}, f, indent=2)

    print(f"\n✅ Backup summary: {len(repos)} repos, {summary['repos_with_changes']} with changes")


if __name__ == "__main__":
    main()
