#!/usr/bin/env python3
"""
YouTube Analytics Dashboard - AI-powered analytics analysis and strategy recommendations.
Works with manual data input or simulated data for demo purposes.
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2"
SAMPLE_DATA_FILE = Path(__file__).parent / "sample_data.json"
REPORTS_DIR = Path(__file__).parent / "reports"
REPORT_TEMPLATE_FILE = Path(__file__).parent / "report_template.md"


def query_ollama(prompt: str) -> str:
    """Send a query to Ollama."""
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    try:
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to Ollama at localhost:11434")
        print("Make sure Ollama is running: ollama serve")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("Error: Request to Ollama timed out.")
        sys.exit(1)
    except Exception as e:
        print(f"Error communicating with Ollama: {e}")
        sys.exit(1)


def load_sample_data() -> dict:
    """Load sample analytics data."""
    if SAMPLE_DATA_FILE.exists():
        with open(SAMPLE_DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def load_data_from_file(file_path: str) -> dict:
    """Load analytics data from CSV or JSON file."""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    if path.suffix.lower() == ".json":
        with open(path, "r") as f:
            return json.load(f)
    elif path.suffix.lower() == ".csv":
        data = {"channels": {}}
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                channel = row.get("channel", "Unknown")
                if channel not in data["channels"]:
                    data["channels"][channel] = {"name": channel, "videos": [], "metrics": {"total_views": 0}}
                video_entry = {
                    "title": row.get("title", ""),
                    "views": int(row.get("views", 0)),
                    "likes": int(row.get("likes", 0)),
                    "comments": int(row.get("comments", 0)),
                    "date": row.get("date", ""),
                    "watch_time_hours": float(row.get("watch_time_hours", 0)),
                    "ctr": float(row.get("ctr", 0)),
                }
                data["channels"][channel]["videos"].append(video_entry)
                data["channels"][channel]["metrics"]["total_views"] += video_entry["views"]
        return data
    else:
        print(f"Error: Unsupported file format: {path.suffix}")
        sys.exit(1)


def generate_simulated_data() -> dict:
    """Generate realistic sample data for demo purposes."""
    channels_config = [
        {"name": "Tech Tutorials", "niche": "technology", "subs_base": 45000},
        {"name": "Gyaan in 5", "niche": "education", "subs_base": 120000},
        {"name": "Gaming Pulse", "niche": "gaming", "subs_base": 85000},
        {"name": "Fitness First", "niche": "fitness", "subs_base": 32000},
        {"name": "Cook with Dev", "niche": "cooking", "subs_base": 67000},
        {"name": "Code & Coffee", "niche": "programming", "subs_base": 28000},
        {"name": "Daily Vlog Life", "niche": "vlogging", "subs_base": 95000},
        {"name": "Finance Guru", "niche": "finance", "subs_base": 52000},
        {"name": "Music Vibes", "niche": "music", "subs_base": 41000},
    ]

    titles_map = {
        "technology": ["Top 10 VS Code Extensions", "Linux vs Windows", "Best Budget Laptop", "AI Tools Review"],
        "education": ["Learn DSA in 5 Min", "System Design Explained", "What is API?", "Git for Beginners"],
        "gaming": ["GTA 6 First Look", "Top FPS Games 2025", "Ultimate PC Build", "Pro Tips Valorant"],
        "fitness": ["30 Min Home Workout", "Best Protein Sources", "Morning Routine", "Common Gym Mistakes"],
        "cooking": ["5 Min Breakfast Ideas", "Restaurant Biryani", "Healthy Meal Prep", "Street Food at Home"],
        "programming": ["Build REST API", "React vs Next.js", "Clean Code Tips", "System Design Prep"],
        "vlogging": ["Day in My Life", "Room Tour 2025", "Moving to New City", "YouTube Income Reveal"],
        "finance": ["Invest 101 Beginners", "SIP vs Lump Sum", "Crypto Worth It?", "Tax Saving Tips"],
        "music": ["How I Produce Beats", "Guitar Tutorial", "Top Songs This Month", "Studio Tour"],
    }

    posting_hours = [9, 12, 15, 17, 19, 20, 21]
    data = {"channels": {}, "generated_at": datetime.now().isoformat(), "period": "last_90_days"}

    for ch_cfg in channels_config:
        name = ch_cfg["name"]
        niche = ch_cfg["niche"]
        subs = ch_cfg["subs_base"]
        titles = titles_map.get(niche, titles_map["technology"])

        videos = []
        for _ in range(random.randint(12, 20)):
            days_ago = random.randint(1, 90)
            date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            hour = random.choice(posting_hours)
            views = random.randint(int(subs * 0.02), int(subs * 0.4))
            likes = int(views * random.uniform(0.03, 0.12))
            comments_count = int(views * random.uniform(0.005, 0.03))
            ctr = round(random.uniform(3.0, 12.0), 1)
            watch_time = round(views * random.uniform(0.01, 0.08), 1)

            videos.append({
                "title": random.choice(titles),
                "date": date,
                "posting_hour": hour,
                "views": views,
                "likes": likes,
                "comments": comments_count,
                "shares": int(views * random.uniform(0.001, 0.01)),
                "ctr": ctr,
                "watch_time_hours": watch_time,
                "avg_view_duration_min": round(random.uniform(2.5, 12.0), 1),
                "retention_rate_pct": round(random.uniform(25.0, 65.0), 1),
                "new_subscribers_from_video": random.randint(5, int(views * 0.005) + 10),
            })

        videos.sort(key=lambda x: x["date"], reverse=True)
        total_views = sum(v["views"] for v in videos)
        growth = sum(v["new_subscribers_from_video"] for v in videos)
        avg_ctr = round(sum(v["ctr"] for v in videos) / len(videos), 1)
        best_video = max(videos, key=lambda v: v["views"])

        data["channels"][name] = {
            "name": name, "niche": niche, "subscribers": subs,
            "subscriber_growth_90d": growth, "total_views_90d": total_views,
            "total_watch_time_hours": round(sum(v["watch_time_hours"] for v in videos), 1),
            "avg_ctr": avg_ctr, "videos_published_90d": len(videos),
            "best_performing_video": best_video["title"], "videos": videos,
        }

    return data


def analyze_channel(channel_data: dict) -> str:
    """Use AI to analyze a single channel's data."""
    videos = channel_data.get("videos", [])
    total_views = sum(v["views"] for v in videos)
    avg_views = total_views // max(len(videos), 1)
    avg_ctr = sum(v.get("ctr", 0) for v in videos) / max(len(videos), 1)
    best_video = max(videos, key=lambda v: v["views"]) if videos else {}
    worst_video = min(videos, key=lambda v: v["views"]) if videos else {}

    hours = [v.get("posting_hour", 12) for v in videos]
    hour_counts = {}
    for h in hours:
        hour_counts[h] = hour_counts.get(h, 0) + 1
    most_common_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 12

    prompt = f"""Analyze this YouTube channel's performance and provide strategic recommendations:

CHANNEL: {channel_data.get('name', 'Unknown')}
NICHE: {channel_data.get('niche', 'Unknown')}
SUBSCRIBERS: {channel_data.get('subscribers', 0):,}
GROWTH (90d): +{channel_data.get('subscriber_growth_90d', 0):,}

PERFORMANCE (Last 90 Days):
- Videos Published: {len(videos)}
- Total Views: {total_views:,}
- Average Views/Video: {avg_views:,}
- Average CTR: {avg_ctr:.1f}%
- Most Common Posting Hour: {most_common_hour}:00

BEST VIDEO: "{best_video.get('title', 'N/A')}" - {best_video.get('views', 0):,} views, {best_video.get('ctr', 0)}% CTR
WORST VIDEO: "{worst_video.get('title', 'N/A')}" - {worst_video.get('views', 0):,} views, {worst_video.get('ctr', 0)}% CTR

Provide:
1. GROWTH TRENDS: Growing, stagnant, or declining?
2. CONTENT STRATEGY: What to make more of
3. OPTIMAL POSTING: Best times and frequency
4. ENGAGEMENT: How to improve interaction
5. TOP 5 ACTION ITEMS ranked by impact"""

    return query_ollama(prompt)


def compare_channels(data: dict) -> str:
    """Compare performance across multiple channels."""
    channels = data.get("channels", {})
    if len(channels) < 2:
        return "Need at least 2 channels to compare."

    comparison_data = []
    for name, ch in channels.items():
        videos = ch.get("videos", [])
        total_views = sum(v["views"] for v in videos)
        comparison_data.append({
            "name": name, "niche": ch.get("niche", "unknown"),
            "subscribers": ch.get("subscribers", 0),
            "growth": ch.get("subscriber_growth_90d", 0),
            "total_views": total_views,
            "videos_count": len(videos),
            "avg_ctr": round(sum(v.get("ctr", 0) for v in videos) / max(len(videos), 1), 1),
        })

    comparison_data.sort(key=lambda x: x["total_views"], reverse=True)
    comparison_text = "\n".join(
        f"- {c['name']} ({c['niche']}): {c['subscribers']:,} subs, "
        f"{c['total_views']:,} views, {c['avg_ctr']}% CTR, "
        f"{c['videos_count']} videos, +{c['growth']} new subs"
        for c in comparison_data
    )

    prompt = f"""Compare these YouTube channels and provide cross-channel insights:

{comparison_text}

Provide:
1. RANKING by overall performance
2. BEST PRACTICES from top performers
3. CROSS-POLLINATION opportunities
4. RESOURCE ALLOCATION recommendations
5. GROWTH POTENTIAL assessment
6. STRATEGY per channel (2-3 sentences each)"""

    return query_ollama(prompt)


def generate_report(data: dict, channel_name: str = None) -> str:
    """Generate a full markdown report."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    channels = data.get("channels", {})

    if channel_name:
        if channel_name not in channels:
            print(f"Error: Channel '{channel_name}' not found.")
            print(f"Available: {', '.join(channels.keys())}")
            sys.exit(1)
        channels = {channel_name: channels[channel_name]}

    lines = [
        f"# YouTube Analytics Report\n",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Period:** Last 90 Days",
        f"**Channels Analyzed:** {len(channels)}\n",
        f"---\n",
        f"## Channel Overview\n",
        f"| Channel | Niche | Subscribers | Views (90d) | Videos | Avg CTR |",
        f"|---------|-------|-------------|-------------|--------|---------|",
    ]

    for name, ch in channels.items():
        videos = ch.get("videos", [])
        total_views = sum(v["views"] for v in videos)
        avg_ctr = round(sum(v.get("ctr", 0) for v in videos) / max(len(videos), 1), 1)
        lines.append(f"| {name} | {ch.get('niche', 'N/A')} | {ch.get('subscribers', 0):,} | {total_views:,} | {len(videos)} | {avg_ctr}% |")

    lines.append("\n---\n")

    for name, ch in channels.items():
        print(f"  Analyzing: {name}...")
        analysis = analyze_channel(ch)
        videos = ch.get("videos", [])
        total_views = sum(v["views"] for v in videos)
        top_videos = sorted(videos, key=lambda v: v["views"], reverse=True)[:5]

        lines.append(f"## {name}\n")
        lines.append(f"**Niche:** {ch.get('niche', 'N/A')} | **Subs:** {ch.get('subscribers', 0):,} | **Growth:** +{ch.get('subscriber_growth_90d', 0):,}\n")
        lines.append(f"### Top Videos\n")
        lines.append(f"| # | Title | Views | CTR |")
        lines.append(f"|---|-------|-------|-----|")
        for i, v in enumerate(top_videos, 1):
            lines.append(f"| {i} | {v['title']} | {v['views']:,} | {v.get('ctr', 0)}% |")
        lines.append(f"\n### AI Analysis\n")
        lines.append(analysis)
        lines.append(f"\n---\n")

    if len(channels) > 1:
        print("  Generating cross-channel comparison...")
        comparison = compare_channels(data)
        lines.append(f"## Cross-Channel Comparison\n")
        lines.append(comparison)
        lines.append(f"\n---\n")

    lines.append("*Generated by YouTube Analytics Dashboard*\n")

    report_content = "\n".join(lines)
    filename = f"report_{channel_name or 'all'}_{timestamp}.md"
    report_path = REPORTS_DIR / filename
    with open(report_path, "w") as f:
        f.write(report_content)
    return str(report_path)


def display_summary(data: dict):
    """Display a terminal summary of the analytics data."""
    channels = data.get("channels", {})
    print("\n" + "=" * 70)
    print("  YOUTUBE ANALYTICS DASHBOARD")
    print("=" * 70)
    print(f"  Channels: {len(channels)} | Period: {data.get('period', 'Unknown')}")
    print("-" * 70)
    print(f"\n{'Channel':<20} {'Subs':<12} {'Views(90d)':<14} {'Videos':<8} {'CTR':<8} {'Growth'}")
    print("-" * 70)

    for name, ch in sorted(channels.items(), key=lambda x: sum(v["views"] for v in x[1].get("videos", [])), reverse=True):
        videos = ch.get("videos", [])
        total_views = sum(v["views"] for v in videos)
        avg_ctr = round(sum(v.get("ctr", 0) for v in videos) / max(len(videos), 1), 1)
        growth = ch.get("subscriber_growth_90d", 0)
        subs = ch.get("subscribers", 0)
        print(f"  {name:<18} {subs:<11,} {total_views:<13,} {len(videos):<7} {avg_ctr}%{'':<4} +{growth}")

    print("-" * 70)

    all_videos = []
    for ch in channels.values():
        for v in ch.get("videos", []):
            v["_channel"] = ch.get("name", "Unknown")
            all_videos.append(v)
    if all_videos:
        best = max(all_videos, key=lambda v: v["views"])
        print(f"\n  Best Video: \"{best['title']}\" ({best['_channel']}) - {best['views']:,} views")
        highest_ctr = max(all_videos, key=lambda v: v.get("ctr", 0))
        print(f"  Highest CTR: \"{highest_ctr['title']}\" ({highest_ctr['_channel']}) - {highest_ctr.get('ctr', 0)}%")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Analytics Dashboard - AI-powered channel analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --simulate
  %(prog)s --input data.json --report
  %(prog)s --simulate --report --channel "Tech Tutorials"
  %(prog)s --simulate --compare-channels
        """,
    )
    parser.add_argument("--input", type=str, help="Path to analytics data file (CSV/JSON)")
    parser.add_argument("--simulate", action="store_true", help="Generate sample data for demo")
    parser.add_argument("--report", action="store_true", help="Generate full markdown report")
    parser.add_argument("--compare-channels", action="store_true", help="Compare performance across channels")
    parser.add_argument("--channel", type=str, default=None, help="Focus on a specific channel")

    args = parser.parse_args()

    if not any([args.input, args.simulate]):
        parser.print_help()
        sys.exit(0)

    if args.simulate:
        print("Generating simulated analytics data...")
        data = generate_simulated_data()
        sim_path = Path(__file__).parent / "simulated_data.json"
        with open(sim_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Simulated data saved to: {sim_path}")
    elif args.input:
        print(f"Loading data from: {args.input}")
        data = load_data_from_file(args.input)
    else:
        data = load_sample_data()

    if not data or not data.get("channels"):
        print("Error: No channel data found.")
        sys.exit(1)

    display_summary(data)

    if args.compare_channels:
        print("\nComparing channels...")
        comparison = compare_channels(data)
        print("\n" + "=" * 70)
        print("  CROSS-CHANNEL COMPARISON")
        print("=" * 70)
        print(comparison)
        print()

    if args.report:
        print("\nGenerating comprehensive report...")
        report_path = generate_report(data, args.channel)
        print(f"\nReport generated: {report_path}")
        print(f"All reports: {REPORTS_DIR}/")


if __name__ == "__main__":
    main()
