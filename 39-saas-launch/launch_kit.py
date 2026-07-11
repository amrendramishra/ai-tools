#!/usr/bin/env python3
"""
SaaS Launch Kit - Everything needed to launch an AI SaaS product.
Generates marketing copy, emails, legal docs, pricing strategy, and more.
Uses Ollama llama3.2 for content generation.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# ─── Configuration ───────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2"
CHECKLIST_PATH = SCRIPT_DIR / "launch_checklist.json"
EMAIL_TEMPLATES_DIR = SCRIPT_DIR / "email_templates"

PRODUCT_CONTEXT = """
Product: AI-powered SaaS platform for developers
Key Features:
- AI code review and generation
- Automated testing and documentation
- Intelligent project management
- API-first architecture
- Team collaboration with AI assistance
Target Audience: Software development teams, startups, and enterprises
Value Proposition: 10x developer productivity with AI-powered tools
"""


# ─── Ollama Integration ──────────────────────────────────────────────────────

def generate(prompt: str, system: str = "") -> str:
    """Generate response using Ollama."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": MODEL, "messages": messages, "stream": False},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


# ─── File Output ─────────────────────────────────────────────────────────────

def save_output(content: str, filename: str, subdir: str = ""):
    """Save generated content to output directory."""
    out_dir = OUTPUT_DIR / subdir if subdir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    filepath = out_dir / filename
    with open(filepath, "w") as f:
        f.write(content)
    print(f"  ✅ Saved: {filepath}")
    return filepath


# ─── Generators ──────────────────────────────────────────────────────────────

def generate_landing():
    """Generate marketing landing page copy."""
    print("\n🌐 Generating Landing Page Copy...\n")

    prompt = f"""Create complete landing page copy for this SaaS product:

{PRODUCT_CONTEXT}

Generate the following sections:
1. **Hero Section**: Headline (max 10 words), subheadline (1 sentence), CTA button text
2. **Problem Statement**: 3 pain points developers face
3. **Solution Section**: How our product solves each pain point
4. **Features Grid**: 6 key features with icons (suggest emoji) and descriptions
5. **How It Works**: 3-step process
6. **Social Proof**: 3 testimonial templates (realistic fake quotes)
7. **Pricing Teaser**: Brief pricing overview with CTA
8. **FAQ**: 6 common questions and answers
9. **Final CTA**: Compelling closing with urgency

Format as markdown suitable for a developer to implement."""

    content = generate(prompt, "You are an expert SaaS copywriter who understands developers. Write compelling, concise copy that converts technical audiences.")
    save_output(content, "landing_page.md", "marketing")
    print(f"\n{content[:500]}...")


def generate_pricing():
    """Generate pricing strategy."""
    print("\n💰 Generating Pricing Strategy...\n")

    prompt = f"""Create a comprehensive pricing strategy for this SaaS product:

{PRODUCT_CONTEXT}

Include:
1. **Pricing Model Recommendation**: (per-seat, usage-based, hybrid) with reasoning
2. **Tier Structure**:
   - Free/Starter tier (what's included, limitations)
   - Pro tier (price point, features)
   - Team/Business tier (price point, features)
   - Enterprise tier (custom pricing, features)
3. **Price Points**: Specific monthly/annual pricing with justification
4. **Competitor Analysis**: How this compares to similar tools
5. **Discount Strategy**: Annual vs monthly, startup discounts
6. **Metrics**: Key metrics to track (MRR, churn, LTV, CAC targets)
7. **Launch Pricing**: Special launch offer recommendations
8. **Upsell Path**: How to move users up tiers

Be specific with numbers and rationale."""

    content = generate(prompt, "You are a SaaS pricing strategist with experience scaling B2B developer tools from $0 to $10M ARR.")
    save_output(content, "pricing_strategy.md", "marketing")
    print(f"\n{content[:500]}...")


def generate_emails():
    """Generate drip email campaign."""
    print("\n📧 Generating Drip Email Campaign (5 emails)...\n")

    emails = [
        ("Welcome & Quick Start", "Day 0 - Right after signup"),
        ("Key Feature Deep-Dive", "Day 2 - Showcase the #1 feature"),
        ("Success Story & Tips", "Day 5 - Social proof + power tips"),
        ("Upgrade Nudge", "Day 8 - Highlight pro features they're missing"),
        ("Personal Check-in", "Day 14 - Founder-style personal email"),
    ]

    all_emails = []
    for i, (email_name, timing) in enumerate(emails, 1):
        prompt = f"""Write email #{i} of a 5-email drip campaign for this SaaS:

{PRODUCT_CONTEXT}

This email: "{email_name}" - Sent: {timing}

Include:
- Subject line (and 2 A/B test variants)
- Preview text
- Email body (conversational, developer-friendly)
- CTA button text
- PS line

Keep it under 200 words for the body. Be genuine, not salesy."""

        content = generate(prompt, "You are a growth marketer writing email campaigns for developer tools. Your tone is helpful, concise, and technical.")
        all_emails.append(f"# Email {i}: {email_name}\n**Timing:** {timing}\n\n{content}\n\n---\n")
        save_output(content, f"email_{i}_{email_name.lower().replace(' ', '_')}.md", "emails")

    combined = "\n".join(all_emails)
    save_output(combined, "drip_campaign_complete.md", "emails")
    print(f"\n  Generated {len(emails)} emails")


def generate_ph_listing():
    """Generate ProductHunt listing."""
    print("\n🚀 Generating ProductHunt Listing...\n")

    prompt = f"""Create a complete ProductHunt listing for this SaaS:

{PRODUCT_CONTEXT}

Generate:
1. **Tagline** (max 60 chars): Catchy one-liner
2. **Description** (max 260 chars): Brief product description
3. **Detailed Description**: Full PH description (3-4 paragraphs)
4. **Topics/Categories**: 5 relevant PH topics
5. **Maker Comment**: First comment from the maker (personal, authentic)
6. **Gallery Descriptions**: Text descriptions for 5 screenshots/images:
   - Hero image concept
   - Feature 1 showcase
   - Feature 2 showcase
   - Dashboard view
   - Before/After comparison
7. **Launch Day Strategy**: Best time to post, how to get upvotes
8. **Hunter Notes**: What to tell the hunter

Make it compelling for the PH community (technical early adopters)."""

    content = generate(prompt, "You are a ProductHunt launch expert who has helped multiple products reach #1 Product of the Day.")
    save_output(content, "producthunt_listing.md", "marketing")
    print(f"\n{content[:500]}...")


def generate_social():
    """Generate social media launch posts."""
    print("\n📱 Generating Social Media Posts...\n")

    prompt = f"""Create launch-day social media posts for this SaaS:

{PRODUCT_CONTEXT}

Generate posts for:

## Twitter/X (5 posts):
1. Launch announcement (main tweet)
2. Thread opener (what problem we solve)
3. Feature highlight tweet
4. Social proof / early results tweet
5. CTA tweet (try it free)
Each: max 280 chars, include relevant hashtags

## LinkedIn (2 posts):
1. Founder story / launch announcement
2. Technical deep-dive post
Each: 150-300 words, professional but authentic

## Reddit (2 posts):
1. r/SideProject or r/startups launch post
2. r/programming or r/webdev value post (not salesy)
Include: title, body, subreddit suggestion

## Hacker News:
1. Show HN post (title + description)

Make each platform-native. Developers can smell marketing from a mile away."""

    content = generate(prompt, "You are a developer advocate who knows how to authentically launch products on social media without being cringe.")
    save_output(content, "social_media_posts.md", "marketing")
    print(f"\n{content[:500]}...")


def generate_docs():
    """Generate API documentation."""
    print("\n📖 Generating API Documentation...\n")

    prompt = f"""Create comprehensive API documentation for this SaaS:

{PRODUCT_CONTEXT}

Generate:
1. **Getting Started**:
   - Authentication (API key)
   - Base URL
   - Rate limits
   - Quick start example (curl + Python)

2. **Endpoints** (design 8 core endpoints):
   - POST /api/v1/code/review - Submit code for AI review
   - POST /api/v1/code/generate - Generate code from prompt
   - POST /api/v1/tests/generate - Generate tests for code
   - POST /api/v1/docs/generate - Generate documentation
   - GET /api/v1/projects - List projects
   - POST /api/v1/projects - Create project
   - GET /api/v1/usage - Get usage stats
   - POST /api/v1/webhooks - Configure webhooks

   For each: method, path, description, request body, response, example

3. **Error Handling**: Error codes and formats
4. **SDKs**: Python and JavaScript SDK examples
5. **Webhooks**: Event types and payload format
6. **Changelog**: Version history template

Format as developer-friendly markdown with code blocks."""

    content = generate(prompt, "You are a technical writer creating API documentation for developers. Be precise, include examples, and follow REST best practices.")
    save_output(content, "api_documentation.md", "docs")
    print(f"\n{content[:500]}...")


def generate_legal():
    """Generate privacy policy and terms of service templates."""
    print("\n⚖️  Generating Legal Documents...\n")

    # Privacy Policy
    privacy_prompt = f"""Generate a Privacy Policy template for this SaaS:

{PRODUCT_CONTEXT}

Include sections for:
1. Information We Collect (personal data, usage data, code data)
2. How We Use Your Information
3. Data Storage and Security
4. Third-Party Services
5. Your Rights (GDPR, CCPA)
6. Data Retention
7. Cookies
8. Children's Privacy
9. Changes to This Policy
10. Contact Information

Use [COMPANY_NAME], [WEBSITE_URL], [EMAIL] as placeholders.
Make it clear, fair, and developer-friendly. This is a TEMPLATE - note it needs legal review."""

    privacy = generate(privacy_prompt, "You are a legal professional creating fair, clear privacy policies for SaaS products. Include standard protections.")
    save_output(privacy, "privacy_policy.md", "legal")

    # Terms of Service
    tos_prompt = f"""Generate Terms of Service template for this SaaS:

{PRODUCT_CONTEXT}

Include sections for:
1. Acceptance of Terms
2. Description of Service
3. User Accounts
4. Acceptable Use (what code can be submitted)
5. Intellectual Property (users own their code)
6. API Usage and Rate Limits
7. Payment Terms
8. Refund Policy
9. Service Level Agreement (99.9% uptime target)
10. Limitation of Liability
11. Termination
12. Dispute Resolution
13. Changes to Terms
14. Contact Information

Use [COMPANY_NAME], [WEBSITE_URL], [EMAIL] as placeholders.
Be fair to users (they own their code/data). TEMPLATE - needs legal review."""

    tos = generate(tos_prompt, "You are a legal professional creating fair terms of service for developer-focused SaaS products.")
    save_output(tos, "terms_of_service.md", "legal")
    print("  Generated Privacy Policy and Terms of Service")


def show_launch_checklist():
    """Display the complete pre-launch checklist."""
    print("\n📋 PRE-LAUNCH CHECKLIST\n")

    with open(CHECKLIST_PATH) as f:
        data = json.load(f)

    checklist = data["launch_checklist"]
    categories = {}
    for item in checklist:
        categories.setdefault(item["category"], []).append(item)

    total = len(checklist)
    critical = sum(1 for i in checklist if i["priority"] == "critical")

    print(f"  Total items: {total} | Critical: {critical}\n")

    priority_icons = {"critical": "🔴", "high": "🟡", "medium": "🟢"}

    for category, items in categories.items():
        print(f"\n  ═══ {category.upper()} ═══")
        for item in items:
            icon = priority_icons.get(item["priority"], "⚪")
            print(f"  {icon} [ ] {item['item']}")

    print(f"\n  Legend: 🔴 Critical  🟡 High  🟢 Medium")
    print(f"  Complete all 🔴 items before launch!\n")


def run_competitor_analysis():
    """AI analyzes competitor landscape."""
    print("\n🔍 Running Competitor Analysis...\n")

    prompt = f"""Perform a comprehensive competitor analysis for this SaaS:

{PRODUCT_CONTEXT}

Analyze the competitive landscape:

1. **Direct Competitors** (5-7):
   For each: Name, pricing, key features, strengths, weaknesses, market position

2. **Indirect Competitors** (3-4):
   Tools that solve adjacent problems

3. **Market Positioning Map**:
   Create a text-based 2x2 matrix (price vs. features)

4. **Competitive Advantages**:
   What we can do better than each competitor

5. **Threats & Opportunities**:
   Market trends, gaps, and risks

6. **Differentiation Strategy**:
   How to position against each competitor

7. **Pricing Comparison Table**:
   Compare pricing across competitors

8. **GTM Recommendations**:
   Based on competitive gaps, suggest go-to-market strategy

Be specific and realistic about the AI developer tools market."""

    content = generate(prompt, "You are a market analyst specializing in developer tools and B2B SaaS. Provide data-driven, realistic competitive analysis.")
    save_output(content, "competitor_analysis.md", "strategy")
    print(f"\n{content[:500]}...")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SaaS Launch Kit - Generate everything needed to launch your AI SaaS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --generate landing              Landing page copy
  %(prog)s --generate pricing              Pricing strategy
  %(prog)s --generate emails               Drip email campaign
  %(prog)s --generate ph-listing           ProductHunt listing
  %(prog)s --generate social               Social media posts
  %(prog)s --generate docs                 API documentation
  %(prog)s --generate legal                Privacy policy + ToS
  %(prog)s --launch-checklist              Pre-launch checklist
  %(prog)s --competitor-analysis           Competitor landscape
        """,
    )

    parser.add_argument("--generate", type=str,
                        choices=["landing", "pricing", "emails", "ph-listing", "social", "docs", "legal"],
                        help="Generate specific content type")
    parser.add_argument("--launch-checklist", action="store_true", help="Show pre-launch checklist")
    parser.add_argument("--competitor-analysis", action="store_true", help="Run competitor analysis")

    args = parser.parse_args()

    if not any([args.generate, args.launch_checklist, args.competitor_analysis]):
        parser.print_help()
        sys.exit(1)

    # Check Ollama for generation tasks
    if args.generate or args.competitor_analysis:
        try:
            resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            resp.raise_for_status()
        except Exception:
            print("❌ Cannot connect to Ollama at", OLLAMA_URL)
            print("   Make sure Ollama is running: ollama serve")
            sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.launch_checklist:
        show_launch_checklist()
    elif args.competitor_analysis:
        run_competitor_analysis()
    elif args.generate == "landing":
        generate_landing()
    elif args.generate == "pricing":
        generate_pricing()
    elif args.generate == "emails":
        generate_emails()
    elif args.generate == "ph-listing":
        generate_ph_listing()
    elif args.generate == "social":
        generate_social()
    elif args.generate == "docs":
        generate_docs()
    elif args.generate == "legal":
        generate_legal()


if __name__ == "__main__":
    main()
