#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
Trending Topic Detector - Finds and ranks trending topics for YouTube channels.
Scrapes Google Trends (RSS) and Twitter/X trending topics.
Uses Ollama for AI-powered ranking by virality, competition, and relevance.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"
SCRIPT_DIR = Path(__file__).parent
TRENDS_DIR = SCRIPT_DIR / "trends"
CHANNELS_FILE = Path(__file__).parent.parent / "06-content-pipeline" / "channels.json"

# Google Trends RSS endpoints
GOOGLE_TRENDS_RSS = "https://trends.google.com/trending/rss?geo=IN"
GOOGLE_TRENDS_DAILY = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=IN"

# Niche keywords mapping for filtering
NICHE_KEYWORDS = {
    "knowledge/education": ["science", "history", "discovery", "research", "facts", "study", "universe",
                            "brain", "psychology", "education", "learn", "explain", "how", "why"],
    "technology/tech news": ["ai", "google", "apple", "samsung", "software", "app", "phone", "tech",
                             "computer", "robot", "chatgpt", "openai", "startup", "digital", "cyber",
                             "iphone", "android", "update", "launch", "gadget"],
    "finance/money tips": ["stock", "market", "investment", "crypto", "bitcoin", "money", "bank",
                           "tax", "rbi", "sensex", "nifty", "mutual fund", "economy", "inflation",
                           "budget", "loan", "insurance", "wealth"],
    "productivity/self-improvement": ["productivity", "habit", "success", "mindset", "morning",
                                       "routine", "focus", "discipline", "goal", "motivation",
                                       "health", "fitness", "meditation", "sleep"],
    "horror stories": ["horror", "ghost", "haunted", "mysterious", "paranormal", "death",
                       "murder", "disappearance", "creepy", "unexplained", "dark", "night"],
    "relationship psychology": ["relationship", "love", "dating", "marriage", "breakup",
                                "psychology", "attraction", "partner", "toxic", "emotion",
                                "attachment", "communication"],
    "dark/controversial facts": ["secret", "conspiracy", "hidden", "banned", "dark", "controversial",
                                  "truth", "exposed", "scam", "fraud", "corruption", "cover-up"],
    "legal rights awareness": ["law", "court", "police", "rights", "justice", "crime", "legal",
                                "supreme court", "constitution", "arrest", "bail", "property",
                                "consumer", "complaint"],
    "hypothetical scenarios": ["what if", "imagine", "scenario", "future", "possibility",
                                "hypothetical", "alternate", "parallel", "impossible", "theory"]
}


def load_channels() -> dict | None:
    """Load channel configurations if available."""
    if CHANNELS_FILE.exists():
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)["channels"]
    return None


def get_channel_niche(channel_name: str, channels: dict) -> str | None:
    """Get niche for a channel."""
    if not channels:
        return None
    name_lower = channel_name.lower().replace(" ", "_").replace("-", "_")
    for key, config in channels.items():
        if key == name_lower or config["name"].lower().replace(" ", "_") == name_lower:
            return config["niche"]
        if name_lower in key or name_lower in config["name"].lower():
            return config["niche"]
    return None


def fetch_google_trends_rss() -> list[dict]:
    """Fetch trending topics from Google Trends RSS feed (India)."""
    topics = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    urls = [GOOGLE_TRENDS_RSS, GOOGLE_TRENDS_DAILY]

    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            # Handle RSS namespace
            ns = {"ht": "https://trends.google.com/trending/rss"}

            for item in root.findall(".//item"):
                title = item.find("title")
                traffic = item.find("ht:approx_traffic", ns)
                description = item.find("description")
                pub_date = item.find("pubDate")

                if title is not None and title.text:
                    topic_data = {
                        "title": title.text.strip(),
                        "source": "google_trends",
                        "traffic": traffic.text.strip() if traffic is not None else "N/A",
                        "description": description.text.strip() if description is not None else "",
                        "date": pub_date.text.strip() if pub_date is not None else "",
                    }
                    topics.append(topic_data)

        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  Google Trends RSS fetch failed ({url}): {e}")
        except ET.ParseError as e:
            print(f"  ⚠️  Google Trends RSS parse error: {e}")

    # Deduplicate by title
    seen = set()
    unique_topics = []
    for t in topics:
        if t["title"].lower() not in seen:
            seen.add(t["title"].lower())
            unique_topics.append(t)

    return unique_topics


def fetch_twitter_trending() -> list[dict]:
    """Fetch trending topics from Twitter/X (via web scraping alternative sources)."""
    topics = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Try multiple sources for Twitter trends
    sources = [
        {
            "url": "https://getdaytrends.com/india/",
            "parser": "getdaytrends"
        },
        {
            "url": "https://trends24.in/india/",
            "parser": "trends24"
        }
    ]

    for source in sources:
        try:
            response = requests.get(source["url"], headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            if source["parser"] == "getdaytrends":
                # Parse getdaytrends.com
                trend_items = soup.select("table.table-hover td a")
                for item in trend_items[:30]:
                    text = item.get_text(strip=True)
                    if text and len(text) > 1:
                        topics.append({
                            "title": text.lstrip("#"),
                            "source": "twitter_trends",
                            "traffic": "trending",
                            "description": f"Trending on Twitter/X India",
                            "date": datetime.now().isoformat()
                        })

            elif source["parser"] == "trends24":
                # Parse trends24.in
                trend_cards = soup.select(".trend-card__list li a")
                for item in trend_cards[:30]:
                    text = item.get_text(strip=True)
                    if text and len(text) > 1:
                        topics.append({
                            "title": text.lstrip("#"),
                            "source": "twitter_trends",
                            "traffic": "trending",
                            "description": "Trending on Twitter/X India",
                            "date": datetime.now().isoformat()
                        })

            if topics:
                break  # Got results from one source, stop trying others

        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  Twitter trends fetch failed ({source['url']}): {e}")
        except Exception as e:
            print(f"  ⚠️  Twitter trends parse error: {e}")

    # Deduplicate
    seen = set()
    unique = []
    for t in topics:
        if t["title"].lower() not in seen:
            seen.add(t["title"].lower())
            unique.append(t)

    return unique


def filter_by_niche(topics: list[dict], niche: str) -> list[dict]:
    """Filter topics by relevance to a niche using keyword matching."""
    keywords = NICHE_KEYWORDS.get(niche, [])
    if not keywords:
        return topics

    filtered = []
    for topic in topics:
        title_lower = topic["title"].lower()
        desc_lower = topic.get("description", "").lower()
        combined = title_lower + " " + desc_lower

        # Check if any niche keyword matches
        relevance_score = sum(1 for kw in keywords if kw in combined)
        if relevance_score > 0:
            topic["keyword_relevance"] = relevance_score
            filtered.append(topic)

    # Sort by keyword relevance
    filtered.sort(key=lambda x: x.get("keyword_relevance", 0), reverse=True)
    return filtered


def ai_rank_topics(topics: list[dict], niche: str, channel_name: str | None = None) -> list[dict]:
    """Use AI to rank topics by virality, competition, and relevance."""
    if not topics:
        return []

    topics_text = "\n".join([f"{i+1}. {t['title']} (source: {t['source']}, traffic: {t['traffic']})"
                             for i, t in enumerate(topics[:20])])  # Limit to top 20 for AI

    channel_context = f"for the YouTube channel '{channel_name}'" if channel_name else ""
    prompt = f"""You are a YouTube content strategist. Rank these trending topics {channel_context}.
Niche: {niche}

TRENDING TOPICS:
{topics_text}

For each topic, provide a JSON array with objects containing:
- "rank": position (1 = best)
- "topic": the topic title
- "virality_score": 1-10 (how likely to go viral)
- "competition_score": 1-10 (10 = low competition, easy to rank)
- "relevance_score": 1-10 (how relevant to the niche)
- "overall_score": weighted average (virality*0.4 + competition*0.3 + relevance*0.3)
- "video_angle": one-line suggestion for a video angle
- "why": brief explanation of ranking

Respond with ONLY valid JSON array. No markdown, no explanation before or after."""

    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "system": "You are a YouTube growth expert. Respond only with valid JSON.",
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 4096}
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()["response"]

        # Try to extract JSON from response
        # Handle cases where AI wraps in markdown code blocks
        json_match = re.search(r'\[.*\]', result, re.DOTALL)
        if json_match:
            ranked = json.loads(json_match.group())
            return ranked
        else:
            print("  ⚠️  AI ranking returned non-JSON, using keyword scores")
            return []

    except requests.exceptions.ConnectionError:
        print("  ⚠️  Cannot connect to Ollama - skipping AI ranking")
        return []
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ⚠️  AI ranking parse error: {e}")
        return []
    except Exception as e:
        print(f"  ⚠️  AI ranking failed: {e}")
        return []


def generate_suggestions(niche: str, channel_name: str | None) -> list[dict]:
    """Generate original topic suggestions using AI (not from trends)."""
    channel_context = f"for the YouTube channel '{channel_name}'" if channel_name else ""
    prompt = f"""Generate 5 original trending video topic ideas {channel_context}.
Niche: {niche}
Region: India
Time: {datetime.now().strftime('%B %Y')}

Requirements:
- Topics should be timely and have high search potential
- Mix of evergreen and trending angles
- Suitable for YouTube Shorts and regular videos

Respond with a JSON array of objects:
- "topic": the topic (5-10 words)
- "type": "evergreen" or "trending"
- "virality_score": 1-10
- "video_angle": suggested hook/angle
- "target_keywords": list of 3-5 SEO keywords

Respond with ONLY valid JSON array."""

    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "system": "You are a YouTube content strategist specializing in the Indian market. Respond only with valid JSON.",
            "stream": False,
            "options": {"temperature": 0.8, "num_predict": 2048}
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=90)
        response.raise_for_status()
        result = response.json()["response"]

        json_match = re.search(r'\[.*\]', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return []

    except Exception as e:
        print(f"  ⚠️  AI suggestions failed: {e}")
        return []


def save_results(results: dict, channel_name: str | None = None) -> Path:
    """Save trend results to JSON file."""
    TRENDS_DIR.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H%M")

    if channel_name:
        slug = channel_name.lower().replace(" ", "_")
        filename = f"{date_str}_{slug}_{time_str}.json"
    else:
        filename = f"{date_str}_all_{time_str}.json"

    filepath = TRENDS_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return filepath


def run_detector(args):
    """Main detection logic."""
    channels = load_channels()
    niche = args.niche
    channel_name = args.channel

    # Resolve niche from channel if specified
    if channel_name and not niche:
        if channels:
            niche = get_channel_niche(channel_name, channels)
            if not niche:
                print(f"WARNING: Channel '{channel_name}' not found in channels.json")
                print("Proceeding without niche filter...")

    print("🔍 Trending Topic Detector")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if niche:
        print(f"🎯 Niche: {niche}")
    if channel_name:
        print(f"📺 Channel: {channel_name}")
    print(f"{'='*60}\n")

    # Fetch trends from multiple sources
    print("📡 Fetching Google Trends (India)...")
    google_topics = fetch_google_trends_rss()
    print(f"  ✅ Found {len(google_topics)} topics from Google Trends")

    print("📡 Fetching Twitter/X Trends (India)...")
    twitter_topics = fetch_twitter_trending()
    print(f"  ✅ Found {len(twitter_topics)} topics from Twitter/X")

    # Combine all topics
    all_topics = google_topics + twitter_topics
    print(f"\n📊 Total topics collected: {len(all_topics)}")

    # Filter by niche if specified
    if niche:
        print(f"\n🔎 Filtering for niche: {niche}")
        filtered_topics = filter_by_niche(all_topics, niche)
        print(f"  ✅ {len(filtered_topics)} topics match the niche")
    else:
        filtered_topics = all_topics

    # AI ranking
    ranked_topics = []
    if filtered_topics:
        print(f"\n🤖 AI ranking topics (virality × competition × relevance)...")
        ranked_topics = ai_rank_topics(filtered_topics, niche or "general", channel_name)
        if ranked_topics:
            print(f"  ✅ Ranked {len(ranked_topics)} topics")
        else:
            print("  ⚠️  AI ranking unavailable, using raw results")

    # Generate AI suggestions
    print(f"\n💡 Generating AI-powered topic suggestions...")
    suggestions = generate_suggestions(niche or "general", channel_name)
    if suggestions:
        print(f"  ✅ Generated {len(suggestions)} original suggestions")

    # Compile results
    results = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "niche": niche,
            "channel": channel_name,
            "sources": ["google_trends_rss", "twitter_trends"],
            "total_raw_topics": len(all_topics),
            "filtered_topics": len(filtered_topics)
        },
        "ranked_topics": ranked_topics,
        "raw_trends": {
            "google_trends": google_topics[:15],
            "twitter_trends": twitter_topics[:15]
        },
        "niche_filtered": filtered_topics[:20],
        "ai_suggestions": suggestions
    }

    # Save results
    filepath = save_results(results, channel_name)
    print(f"\n{'='*60}")
    print(f"✅ Results saved to: {filepath}")

    # Print top results
    if ranked_topics:
        print(f"\n🏆 TOP RANKED TOPICS:")
        print(f"{'-'*60}")
        for i, topic in enumerate(ranked_topics[:10], 1):
            score = topic.get("overall_score", "N/A")
            print(f"  {i}. {topic.get('topic', 'N/A')}")
            print(f"     Score: {score}/10 | Angle: {topic.get('video_angle', 'N/A')}")
    elif filtered_topics:
        print(f"\n📋 TOP TRENDING (unranked):")
        print(f"{'-'*60}")
        for i, topic in enumerate(filtered_topics[:10], 1):
            print(f"  {i}. {topic['title']} ({topic['source']}, {topic['traffic']})")

    if suggestions:
        print(f"\n💡 AI SUGGESTIONS:")
        print(f"{'-'*60}")
        for i, s in enumerate(suggestions[:5], 1):
            print(f"  {i}. {s.get('topic', 'N/A')}")
            print(f"     Type: {s.get('type', 'N/A')} | Angle: {s.get('video_angle', 'N/A')}")

    return results


def run_daily_scan(args):
    """Run scan for all channels and save results."""
    channels = load_channels()
    if not channels:
        print("ERROR: channels.json not found. Cannot run daily scan.")
        sys.exit(1)

    print("🔄 DAILY SCAN - Running for all channels\n")
    all_results = {}

    for key, config in channels.items():
        print(f"\n{'='*60}")
        print(f"📺 {config['name']} ({config['niche']})")
        print(f"{'='*60}")

        # Create a mock args with channel info
        class ChannelArgs:
            def __init__(self, name, niche):
                self.channel = name
                self.niche = niche
                self.daily = False

        chan_args = ChannelArgs(config["name"], config["niche"])
        results = run_detector(chan_args)
        all_results[key] = {
            "channel": config["name"],
            "niche": config["niche"],
            "top_topics": results.get("ranked_topics", [])[:5],
            "suggestions": results.get("ai_suggestions", [])[:3]
        }

    # Save combined daily report
    TRENDS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    daily_file = TRENDS_DIR / f"{date_str}_daily_report.json"

    with open(daily_file, "w", encoding="utf-8") as f:
        json.dump({
            "report_date": date_str,
            "generated_at": datetime.now().isoformat(),
            "channels": all_results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"📊 DAILY REPORT SAVED: {daily_file}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Trending Topic Detector - Find viral topics for YouTube channels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --niche "technology/tech news"
  %(prog)s --channel tech_in_5_hindi
  %(prog)s --channel horror_ki_kahani --niche "horror stories"
  %(prog)s --daily
        """
    )
    parser.add_argument("--niche", "-n", help="Filter by content niche")
    parser.add_argument("--channel", "-c", help="Suggest topics for a specific channel")
    parser.add_argument("--daily", "-d", action="store_true",
                        help="Run daily scan for all channels")
    parser.add_argument("--model", "-m", default=None,
                        help="Ollama model (default: llama3.2)")

    args = parser.parse_args()

    global MODEL
    if args.model:
        MODEL = args.model

    if args.daily:
        run_daily_scan(args)
    else:
        run_detector(args)


if __name__ == "__main__":
    main()
