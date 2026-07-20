#!/usr/bin/env python3
"""
Trending Research Script for GitHub Actions
Searches Tavily API for trending topics across 9 YouTube channel niches.
"""

import os
import json
import requests
from datetime import datetime

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
TAVILY_SEARCH_URL = "https://api.tavily.com/search"

CHANNEL_NICHES = {
    "ai_tools": {
        "name": "AI Tools & Automation",
        "queries": [
            "trending AI tools 2025",
            "new AI automation tools released this week",
            "best free AI tools for productivity"
        ]
    },
    "tech_explained": {
        "name": "Tech Explained in Hindi",
        "queries": [
            "latest technology news India",
            "trending tech topics explained simply",
            "new gadgets and tech releases India"
        ]
    },
    "coding_tutorials": {
        "name": "Coding Tutorials",
        "queries": [
            "trending programming languages 2025",
            "most popular coding tutorials beginners",
            "new frameworks and libraries developers"
        ]
    },
    "startup_ideas": {
        "name": "Startup & Business Ideas",
        "queries": [
            "trending startup ideas India 2025",
            "new business opportunities technology",
            "successful Indian startups latest funding"
        ]
    },
    "personal_finance": {
        "name": "Personal Finance & Investment",
        "queries": [
            "trending investment opportunities India",
            "personal finance tips young professionals",
            "stock market trends India today"
        ]
    },
    "productivity": {
        "name": "Productivity & Self-Improvement",
        "queries": [
            "trending productivity hacks 2025",
            "best self-improvement techniques",
            "time management tools and methods"
        ]
    },
    "cloud_devops": {
        "name": "Cloud & DevOps",
        "queries": [
            "trending cloud computing topics AWS Azure",
            "new DevOps tools and practices",
            "Kubernetes Docker latest updates"
        ]
    },
    "data_science": {
        "name": "Data Science & ML",
        "queries": [
            "trending machine learning topics",
            "new data science tools and frameworks",
            "latest research papers AI ML simplified"
        ]
    },
    "side_hustle": {
        "name": "Side Hustle & Freelancing",
        "queries": [
            "trending side hustles online 2025",
            "freelancing opportunities India tech",
            "make money online skills in demand"
        ]
    }
}


def search_tavily(query, max_results=5):
    """Search Tavily API for a given query."""
    if not TAVILY_API_KEY:
        print("WARNING: TAVILY_API_KEY not set")
        return {"query": query, "results": [], "error": "API key not configured"}

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": True,
        "include_raw_content": False
    }

    try:
        response = requests.post(TAVILY_SEARCH_URL, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error searching for '{query}': {e}")
        return {"query": query, "results": [], "error": str(e)}


def research_niche(niche_id, niche_config):
    """Research trending topics for a specific niche."""
    print(f"\n🔍 Researching: {niche_config['name']}")
    niche_results = {
        "niche_id": niche_id,
        "niche_name": niche_config["name"],
        "timestamp": datetime.utcnow().isoformat(),
        "searches": []
    }
    for query in niche_config["queries"]:
        print(f"  Searching: {query}")
        result = search_tavily(query)
        search_entry = {
            "query": query,
            "answer": result.get("answer", ""),
            "results": []
        }
        for item in result.get("results", []):
            search_entry["results"].append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", "")[:500],
                "score": item.get("score", 0)
            })
        niche_results["searches"].append(search_entry)
    return niche_results


def main():
    """Main entry point."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    print(f"📈 Starting trending research for {today}")
    os.makedirs("trends", exist_ok=True)

    all_results = {
        "date": today,
        "generated_at": datetime.utcnow().isoformat(),
        "niches": {}
    }

    for niche_id, niche_config in CHANNEL_NICHES.items():
        niche_results = research_niche(niche_id, niche_config)
        all_results["niches"][niche_id] = niche_results
        niche_file = f"trends/{today}_{niche_id}.json"
        with open(niche_file, "w") as f:
            json.dump(niche_results, f, indent=2)
        print(f"  ✅ Saved: {niche_file}")

    combined_file = f"trends/{today}_all_trends.json"
    with open(combined_file, "w") as f:
        json.dump(all_results, f, indent=2)

    with open("trends/latest.json", "w") as f:
        json.dump({"date": today, "file": combined_file}, f, indent=2)

    print(f"\n✅ Research complete! Found trends across {len(CHANNEL_NICHES)} niches.")


if __name__ == "__main__":
    main()
