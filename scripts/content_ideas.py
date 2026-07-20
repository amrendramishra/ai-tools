#!/usr/bin/env python3
"""
Content Ideas Generator for GitHub Actions
Generates 5 video ideas per channel based on trending research results.
Uses template-based generation + Tavily search for fresh angles.
"""

import os
import json
import requests
from datetime import datetime

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
TAVILY_SEARCH_URL = "https://api.tavily.com/search"

IDEA_TEMPLATES = {
    "ai_tools": [
        "🤖 {topic} - Complete Beginner's Guide (2025)",
        "⚡ Top 5 {topic} You Need to Try TODAY",
        "🔥 I Tested {topic} for 7 Days - Here's What Happened",
        "💡 {topic} vs {alt_topic}: Which One Wins?",
        "🚀 How to Use {topic} to 10x Your Productivity"
    ],
    "tech_explained": [
        "📱 {topic} - Explained in 5 Minutes (Hindi)",
        "🧠 How {topic} Actually Works - Simple Explanation",
        "⚠️ {topic}: 5 Things Nobody Tells You",
        "🇮🇳 {topic} in India - Complete Reality Check",
        "🔮 Future of {topic} - What's Coming Next?"
    ],
    "coding_tutorials": [
        "💻 Build {topic} from Scratch - Full Tutorial",
        "🎯 {topic} Crash Course for Beginners (2025)",
        "🏆 {topic} Project That Will Get You Hired",
        "⚡ {topic} in 10 Minutes - Quick Start Guide",
        "🔧 {topic}: Common Mistakes & How to Fix Them"
    ],
    "startup_ideas": [
        "💰 {topic} Business Idea - Zero Investment Start",
        "📈 How {topic} is Making Millions in India",
        "🎯 {topic}: Step-by-Step Business Plan",
        "🚀 Build a {topic} Startup in 30 Days",
        "💡 {topic} Opportunity Nobody is Talking About"
    ],
    "personal_finance": [
        "💰 {topic}: How to Start with ₹1000",
        "📊 {topic} Strategy That Made Me Money",
        "⚠️ {topic} Mistakes That Cost Me Lakhs",
        "🎯 {topic} for Beginners - Complete Guide",
        "🔥 {topic}: Should You Invest Now?"
    ],
    "productivity": [
        "⚡ {topic} Method: Double Your Productivity",
        "🧠 {topic}: Science-Backed Technique for Focus",
        "📱 {topic} Apps That Changed My Life",
        "🎯 {topic}: Morning Routine for Success",
        "💡 {topic}: The System That Actually Works"
    ],
    "cloud_devops": [
        "☁️ {topic}: Complete Hands-On Tutorial",
        "🔧 {topic} Setup in 15 Minutes - DevOps Guide",
        "🏗️ {topic} Architecture: Best Practices 2025",
        "💡 {topic}: From Zero to Production",
        "⚡ {topic} vs Traditional: Performance Comparison"
    ],
    "data_science": [
        "📊 {topic}: End-to-End Project Tutorial",
        "🧠 {topic} Explained Simply (No Math!)",
        "🔥 {topic}: Build Your First Model Today",
        "💡 {topic} Portfolio Project for Jobs",
        "🎯 {topic}: What You ACTUALLY Need to Know"
    ],
    "side_hustle": [
        "💰 Make 50K/Month with {topic} (Proof)",
        "🚀 {topic}: Start Earning in 7 Days",
        "🎯 {topic} Complete Roadmap for Beginners",
        "💡 {topic}: Skills That Pay 1 Lakh+/Month",
        "🔥 {topic}: Real Income Proof & Strategy"
    ]
}

NICHES = {
    "ai_tools": "AI Tools & Automation",
    "tech_explained": "Tech Explained in Hindi",
    "coding_tutorials": "Coding Tutorials",
    "startup_ideas": "Startup & Business Ideas",
    "personal_finance": "Personal Finance & Investment",
    "productivity": "Productivity & Self-Improvement",
    "cloud_devops": "Cloud & DevOps",
    "data_science": "Data Science & ML",
    "side_hustle": "Side Hustle & Freelancing"
}


def search_tavily(query, max_results=3):
    if not TAVILY_API_KEY:
        return []
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": True
    }
    try:
        response = requests.post(TAVILY_SEARCH_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return [r.get("title", "") for r in data.get("results", [])]
    except Exception as e:
        print(f"  Warning: Search failed: {e}")
        return []


def extract_topics_from_trends(niche_id):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    trends_file = f"trends/{today}_{niche_id}.json"
    topics = []
    if os.path.exists(trends_file):
        with open(trends_file) as f:
            data = json.load(f)
        for search in data.get("searches", []):
            for result in search.get("results", []):
                title = result.get("title", "")
                if title:
                    topics.append(title.split(" - ")[0].split(" | ")[0].strip())
    return topics[:10]


def generate_ideas_for_niche(niche_id, niche_name):
    print(f"\n💡 Generating ideas for: {niche_name}")
    topics = extract_topics_from_trends(niche_id)
    if not topics:
        query = f"trending {niche_name} topics this week YouTube video ideas"
        titles = search_tavily(query)
        topics = [t.split(" - ")[0].split(" | ")[0].strip() for t in titles if len(t) > 5]
    if not topics:
        topics = [niche_name, f"Latest {niche_name}", f"Best {niche_name}"]

    templates = IDEA_TEMPLATES.get(niche_id, IDEA_TEMPLATES["ai_tools"])
    ideas = []
    for i, template in enumerate(templates):
        topic = topics[i % len(topics)]
        alt_topic = topics[(i + 1) % len(topics)] if len(topics) > 1 else "Alternative"
        title = template.format(topic=topic, alt_topic=alt_topic)
        ideas.append({
            "rank": i + 1,
            "title": title,
            "source_topic": topic,
            "niche": niche_name,
            "tags": [niche_name.lower(), "trending"],
            "appeal": "high" if i < 2 else "medium"
        })
    return {
        "niche_id": niche_id,
        "niche_name": niche_name,
        "ideas_count": len(ideas),
        "ideas": ideas,
        "generated_at": datetime.utcnow().isoformat()
    }


def main():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    print(f"💡 Generating content ideas for {today}")
    os.makedirs("content-ideas", exist_ok=True)

    all_ideas = {"date": today, "generated_at": datetime.utcnow().isoformat(), "total_ideas": 0, "channels": {}}

    for niche_id, niche_name in NICHES.items():
        ideas = generate_ideas_for_niche(niche_id, niche_name)
        all_ideas["channels"][niche_id] = ideas
        all_ideas["total_ideas"] += ideas["ideas_count"]

    output_file = f"content-ideas/{today}_ideas.json"
    with open(output_file, "w") as f:
        json.dump(all_ideas, f, indent=2)

    md_file = f"content-ideas/{today}_ideas.md"
    with open(md_file, "w") as f:
        f.write(f"# 💡 Content Ideas - {today}\n\n")
        f.write(f"**Total Ideas: {all_ideas['total_ideas']}** across {len(NICHES)} channels\n\n---\n\n")
        for niche_id, data in all_ideas["channels"].items():
            f.write(f"## 📺 {data['niche_name']}\n\n")
            for idea in data["ideas"]:
                emoji = "🔥" if idea["appeal"] == "high" else "📌"
                f.write(f"{idea['rank']}. {emoji} **{idea['title']}**\n\n")
            f.write("---\n\n")

    with open("content-ideas/latest.json", "w") as f:
        json.dump({"date": today, "file": output_file, "markdown": md_file}, f, indent=2)

    print(f"\n✅ Generated {all_ideas['total_ideas']} ideas across {len(NICHES)} channels")


if __name__ == "__main__":
    main()
