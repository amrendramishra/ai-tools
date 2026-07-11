#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
Tavily Research Tool - AI-powered research assistant.
Combines Tavily search API with Ollama for intelligent analysis.
Uses TAVILY_API_KEY from environment. Ollama at localhost:11434.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

import httpx

# Configuration
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
TAVILY_API = "https://api.tavily.com"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"


def check_tavily_key():
    """Verify Tavily API key is set."""
    if not TAVILY_API_KEY:
        print("❌ Error: TAVILY_API_KEY environment variable not set.")
        print("   Get your key at: https://tavily.com")
        print("   Export it: export TAVILY_API_KEY=tvly-your_key_here")
        sys.exit(1)


async def tavily_search(query: str, search_depth: str = "advanced",
                         max_results: int = 5, include_answer: bool = True,
                         topic: str = "general") -> dict:
    """Perform a Tavily search."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{TAVILY_API}/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_answer": include_answer,
                "include_raw_content": False,
                "topic": topic,
            },
        )
        response.raise_for_status()
        return response.json()


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
            return "⚠️  Ollama not available at localhost:11434. Start with: ollama serve"
        except Exception as e:
            return f"⚠️  Ollama error: {e}"


def format_sources(results: list) -> str:
    """Format search results as readable sources."""
    formatted = []
    for i, result in enumerate(results, 1):
        formatted.append(
            f"[{i}] {result.get('title', 'Untitled')}\n"
            f"    URL: {result.get('url', 'N/A')}\n"
            f"    {result.get('content', 'No content')[:200]}"
        )
    return "\n\n".join(formatted)


async def cmd_topic(topic: str):
    """Deep research on a topic with multiple searches + AI synthesis."""
    check_tavily_key()
    print(f"🔬 Deep Research: {topic}\n")
    print("─" * 60)

    # Multiple search angles
    queries = [
        topic,
        f"{topic} latest developments 2024 2025",
        f"{topic} pros cons analysis",
        f"{topic} expert opinions",
    ]

    all_results = []
    all_content = []

    for i, query in enumerate(queries):
        print(f"  🔍 Search {i+1}/{len(queries)}: {query[:50]}...")
        try:
            data = await tavily_search(query, max_results=3)
            results = data.get("results", [])
            all_results.extend(results)

            if data.get("answer"):
                all_content.append(f"Quick Answer: {data['answer']}")

            for r in results:
                all_content.append(f"Source ({r.get('title', '')}): {r.get('content', '')[:500]}")
        except Exception as e:
            print(f"    ⚠️  Error: {e}")

    print(f"\n  📊 Collected {len(all_results)} sources\n")
    print("─" * 60)

    # AI synthesis
    print("🤖 AI Synthesis:\n")

    combined_content = "\n\n".join(all_content[:10])  # Limit to avoid token overflow
    prompt = (
        f"Based on the following research results about '{topic}', "
        f"provide a comprehensive analysis:\n\n"
        f"{combined_content}\n\n"
        f"Structure your response as:\n"
        f"1. Overview (2-3 sentences)\n"
        f"2. Key Findings (bullet points)\n"
        f"3. Current State & Trends\n"
        f"4. Important Considerations\n"
        f"5. Conclusion\n\n"
        f"Be factual and cite information from the sources."
    )

    analysis = await ollama_generate(prompt)
    print(analysis)

    # Sources
    print(f"\n\n📚 Sources ({len(all_results)}):")
    print("─" * 40)
    seen_urls = set()
    for r in all_results:
        url = r.get("url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            print(f"  • {r.get('title', 'Untitled')}")
            print(f"    {url}")


async def cmd_news():
    """Get latest news summary."""
    check_tavily_key()
    print("📰 Latest News Summary\n")
    print("─" * 60)

    # Search for latest news
    queries = [
        "latest technology news today",
        "breaking news world today",
        "trending topics today",
    ]

    all_results = []
    for query in queries:
        try:
            data = await tavily_search(query, topic="news", max_results=5)
            all_results.extend(data.get("results", []))
        except Exception as e:
            print(f"  ⚠️  Error searching: {e}")

    if not all_results:
        print("  No news found.")
        return

    # Display news
    print(f"  Found {len(all_results)} articles:\n")

    news_text = []
    seen = set()
    for r in all_results:
        title = r.get("title", "")
        if title not in seen:
            seen.add(title)
            print(f"  📌 {title}")
            print(f"     {r.get('content', 'No summary')[:150]}...")
            print(f"     🔗 {r.get('url', '')}")
            print()
            news_text.append(f"{title}: {r.get('content', '')[:200]}")

    # AI summary
    print("\n🤖 AI News Digest:\n")
    prompt = (
        f"Summarize these news items into a brief daily digest. "
        f"Group by category (tech, world, etc). Keep it concise:\n\n"
        f"{chr(10).join(news_text[:10])}"
    )
    summary = await ollama_generate(prompt)
    print(summary)


async def cmd_compare(thing1: str, thing2: str):
    """Research comparison between two things."""
    check_tavily_key()
    print(f"⚖️  Comparing: {thing1} vs {thing2}\n")
    print("─" * 60)

    # Research both
    queries = [
        f"{thing1} vs {thing2} comparison",
        f"{thing1} advantages features",
        f"{thing2} advantages features",
        f"{thing1} vs {thing2} which is better",
    ]

    all_content = []
    for query in queries:
        print(f"  🔍 Searching: {query[:50]}...")
        try:
            data = await tavily_search(query, max_results=3)
            if data.get("answer"):
                all_content.append(data["answer"])
            for r in data.get("results", []):
                all_content.append(f"{r.get('title', '')}: {r.get('content', '')[:300]}")
        except Exception as e:
            print(f"    ⚠️  {e}")

    print(f"\n  📊 Research complete\n")
    print("─" * 60)

    # AI comparison
    print("🤖 AI Comparison:\n")
    prompt = (
        f"Compare '{thing1}' vs '{thing2}' based on this research:\n\n"
        f"{chr(10).join(all_content[:8])}\n\n"
        f"Provide a structured comparison:\n"
        f"1. Overview of each\n"
        f"2. Key Differences (table format)\n"
        f"3. Pros/Cons of each\n"
        f"4. Use cases (when to choose which)\n"
        f"5. Verdict/Recommendation\n"
        f"Be objective and data-driven."
    )
    comparison = await ollama_generate(prompt)
    print(comparison)


async def cmd_fact_check(claim: str):
    """Verify a claim using research."""
    check_tavily_key()
    print(f"🔎 Fact-Checking: \"{claim}\"\n")
    print("─" * 60)

    # Search for evidence
    queries = [
        f"is it true that {claim}",
        f"{claim} fact check",
        f"{claim} evidence research",
    ]

    all_content = []
    all_results = []

    for query in queries:
        print(f"  🔍 Checking: {query[:50]}...")
        try:
            data = await tavily_search(query, max_results=3)
            all_results.extend(data.get("results", []))
            if data.get("answer"):
                all_content.append(f"Direct answer: {data['answer']}")
            for r in data.get("results", []):
                all_content.append(f"[{r.get('title', '')}]: {r.get('content', '')[:300]}")
        except Exception as e:
            print(f"    ⚠️  {e}")

    print(f"\n  📊 Found {len(all_results)} sources\n")
    print("─" * 60)

    # AI verdict
    print("🤖 AI Fact-Check Verdict:\n")
    prompt = (
        f"Fact-check this claim: \"{claim}\"\n\n"
        f"Based on these sources:\n{chr(10).join(all_content[:8])}\n\n"
        f"Provide:\n"
        f"1. VERDICT: TRUE / FALSE / PARTIALLY TRUE / UNVERIFIABLE\n"
        f"2. Evidence supporting the verdict\n"
        f"3. Context and nuances\n"
        f"4. Confidence level (High/Medium/Low)\n"
        f"Be objective. If uncertain, say so."
    )
    verdict = await ollama_generate(prompt)
    print(verdict)

    # Sources
    print(f"\n📚 Sources checked:")
    seen = set()
    for r in all_results[:8]:
        url = r.get("url", "")
        if url not in seen:
            seen.add(url)
            print(f"  • {r.get('title', 'Untitled')}: {url}")


async def cmd_market_research(product: str):
    """Market analysis for a product/service."""
    check_tavily_key()
    print(f"📈 Market Research: {product}\n")
    print("─" * 60)

    queries = [
        f"{product} market size 2024 2025",
        f"{product} competitors market share",
        f"{product} market trends growth",
        f"{product} target audience demographics",
        f"{product} pricing strategy",
    ]

    all_content = []
    for query in queries:
        print(f"  🔍 {query[:50]}...")
        try:
            data = await tavily_search(query, max_results=3)
            if data.get("answer"):
                all_content.append(data["answer"])
            for r in data.get("results", []):
                all_content.append(f"{r.get('content', '')[:400]}")
        except Exception as e:
            print(f"    ⚠️  {e}")

    print(f"\n  📊 Research complete\n")
    print("─" * 60)

    # AI analysis
    print("🤖 AI Market Analysis:\n")
    prompt = (
        f"Provide a market research analysis for '{product}' based on:\n\n"
        f"{chr(10).join(all_content[:10])}\n\n"
        f"Structure:\n"
        f"1. Market Overview & Size\n"
        f"2. Key Players & Competition\n"
        f"3. Target Audience\n"
        f"4. Market Trends & Growth\n"
        f"5. Opportunities & Threats\n"
        f"6. Pricing Insights\n"
        f"7. Recommendations\n"
        f"Use data points where available."
    )
    analysis = await ollama_generate(prompt)
    print(analysis)


async def cmd_trend(topic: str):
    """Find trends for a topic."""
    check_tavily_key()
    print(f"📊 Trend Analysis: {topic}\n")
    print("─" * 60)

    queries = [
        f"{topic} trends 2025",
        f"{topic} growth statistics",
        f"{topic} future predictions",
        f"{topic} emerging developments",
    ]

    all_content = []
    all_results = []

    for query in queries:
        print(f"  🔍 {query[:50]}...")
        try:
            data = await tavily_search(query, max_results=3)
            all_results.extend(data.get("results", []))
            if data.get("answer"):
                all_content.append(data["answer"])
            for r in data.get("results", []):
                all_content.append(f"{r.get('content', '')[:400]}")
        except Exception as e:
            print(f"    ⚠️  {e}")

    print(f"\n  📊 Collected {len(all_results)} data points\n")
    print("─" * 60)

    # AI trend analysis
    print("🤖 AI Trend Analysis:\n")
    prompt = (
        f"Analyze trends for '{topic}' based on:\n\n"
        f"{chr(10).join(all_content[:10])}\n\n"
        f"Provide:\n"
        f"1. Current State (where things are now)\n"
        f"2. Key Trends (what's changing)\n"
        f"3. Growth Indicators\n"
        f"4. Future Predictions (next 1-3 years)\n"
        f"5. What to Watch\n"
        f"Use specific data points and dates where possible."
    )
    analysis = await ollama_generate(prompt)
    print(analysis)

    # Key sources
    print(f"\n📚 Key Sources:")
    seen = set()
    for r in all_results[:6]:
        url = r.get("url", "")
        if url not in seen:
            seen.add(url)
            print(f"  • {r.get('title', '')[:60]}")
            print(f"    {url}")


def main():
    parser = argparse.ArgumentParser(
        description="🔬 Tavily Research Tool - AI-powered research assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --topic "quantum computing applications"
  %(prog)s --news
  %(prog)s --compare "React" "Vue.js"
  %(prog)s --fact-check "Python is the most popular language"
  %(prog)s --market-research "AI code assistants"
  %(prog)s --trend "generative AI"
        """,
    )

    parser.add_argument("--topic", metavar="TOPIC", help="Deep research on a topic")
    parser.add_argument("--news", action="store_true", help="Latest news summary")
    parser.add_argument("--compare", nargs=2, metavar=("THING1", "THING2"),
                        help="Compare two things")
    parser.add_argument("--fact-check", metavar="CLAIM", help="Verify a claim")
    parser.add_argument("--market-research", metavar="PRODUCT", help="Market analysis")
    parser.add_argument("--trend", metavar="TOPIC", help="Find trends")

    args = parser.parse_args()

    if args.topic:
        asyncio.run(cmd_topic(args.topic))
    elif args.news:
        asyncio.run(cmd_news())
    elif args.compare:
        asyncio.run(cmd_compare(args.compare[0], args.compare[1]))
    elif args.fact_check:
        asyncio.run(cmd_fact_check(args.fact_check))
    elif args.market_research:
        asyncio.run(cmd_market_research(args.market_research))
    elif args.trend:
        asyncio.run(cmd_trend(args.trend))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
