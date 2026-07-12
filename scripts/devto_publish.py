#!/usr/bin/env python3
"""Auto-generate and publish AI/tech articles to Dev.to daily"""
import os
import json
import urllib.request
from datetime import datetime

DEVTO_KEY = os.environ.get("DEVTO_API_KEY", "")
OLLAMA_URL = "http://localhost:11434/api/generate"

# 30 article topics (rotates by day of year)
TOPICS = [
    ("5 AI Tools You Can Run Locally for Free in 2026", ["ai", "ollama", "automation", "productivity"]),
    ("How I Automated 9 YouTube Channels at ₹0/month", ["youtube", "automation", "python", "ai"]),
    ("Building a Multi-Agent AI System from Scratch", ["ai", "agents", "python", "langchain"]),
    ("Local RAG Pipeline: Ask Questions About Your Documents", ["rag", "chromadb", "ai", "tutorial"]),
    ("Voice-Controlled AI: Say 'Hey Jarvis' and It Does Everything", ["ai", "voice", "python", "mac"]),
    ("MCP (Model Context Protocol) Explained Simply", ["mcp", "ai", "claude", "tools"]),
    ("Why I Quit Cloud AI and Run Everything Locally", ["ai", "ollama", "privacy", "selfhosted"]),
    ("Build Your Own ChatGPT UI (Zero API Costs)", ["webdev", "ai", "javascript", "tutorial"]),
    ("AI Code Reviewer as a Git Hook — Never Ship Bugs Again", ["git", "ai", "devtools", "productivity"]),
    ("From SDE to VP: What Actually Matters in Your Career", ["career", "advice", "programming", "growth"]),
    ("Java 21 + Quarkus + AWS Lambda: The Ultimate Stack", ["java", "aws", "serverless", "quarkus"]),
    ("DynamoDB at Scale: 2M+ Daily Transactions, Sub-10ms", ["aws", "dynamodb", "database", "architecture"]),
    ("System Design: How PayPal Status Page Serves 400M Users", ["systemdesign", "architecture", "webdev", "scaling"]),
    ("LangGraph vs LangChain: When to Use What", ["ai", "langchain", "python", "agents"]),
    ("Automate Your Mac Like a Pro with AI", ["mac", "automation", "ai", "productivity"]),
    ("GitHub Actions: Run AI Workflows 24/7 for Free", ["github", "automation", "ai", "devops"]),
    ("Building a Telegram Bot with Local AI (No API Costs)", ["telegram", "bot", "ai", "python"]),
    ("The ₹0 Tech Stack: Everything Free, Everything Automated", ["opensource", "free", "tools", "automation"]),
    ("How to Fine-Tune Your Own AI Model on Apple Silicon", ["ai", "machinelearning", "mac", "tutorial"]),
    ("Smart File Organizer: AI Watches Your Downloads Folder", ["ai", "python", "automation", "productivity"]),
    ("AI Habit Tracker with Personalized Coaching", ["ai", "productivity", "python", "health"]),
    ("Content Repurposer: One Post → 7 Platforms Automatically", ["content", "automation", "ai", "marketing"]),
    ("Building an AI-Powered Resume Generator", ["ai", "career", "python", "tools"]),
    ("ChromaDB + Ollama: The Free Vector Database Stack", ["database", "ai", "tutorial", "python"]),
    ("How I Keep My GitHub Graph Green Without Trying", ["github", "automation", "devops", "productivity"]),
    ("Serverless Microservices: Cold Start to 60% Faster", ["aws", "serverless", "java", "performance"]),
    ("Production GenAI at Enterprise Scale: Lessons Learned", ["ai", "enterprise", "production", "architecture"]),
    ("Mock Interview Bot: Practice System Design with AI", ["interview", "ai", "career", "systemdesign"]),
    ("AI Newsletter Generator: Curate + Write Automatically", ["ai", "automation", "newsletter", "content"]),
    ("The VP Engineer's Toolkit: Tools I Use Every Day", ["productivity", "tools", "career", "engineering"]),
]

def generate_article_with_ollama(title, tags):
    """Generate article using Ollama"""
    prompt = f"""Write a technical blog post for Dev.to.

Title: {title}
Tags: {', '.join(tags)}

Requirements:
- Start with a compelling hook (2-3 sentences)
- Include code examples where relevant
- Use markdown formatting (headers, code blocks, bullet points)
- Keep it practical and actionable (800-1200 words)
- End with a call-to-action mentioning my GitHub: https://github.com/amrendramishra/ai-tools
- Mention my portfolio: https://amrendranmishra.dev
- Tone: direct, practical, no fluff
- Include at least one code snippet

Write the full article body in markdown (no title, I'll add that separately):"""

    try:
        data = json.dumps({"model": "llama3.2", "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())["response"]
    except:
        return None

def generate_article_without_ollama(title, tags):
    """Fallback: template-based article (for GitHub Actions where Ollama isn't available)"""
    return f"""
Are you tired of paying for AI APIs? What if I told you everything can run locally, for free?

## The Problem

Most developers think AI tools require expensive cloud subscriptions. OpenAI, Anthropic, Google — they all charge per token. But there's a better way.

## The Solution

I built **45 AI tools** that run entirely on my MacBook using [Ollama](https://ollama.com). Zero cloud costs. Zero subscriptions. Complete privacy.

## Quick Setup

```bash
# Install Ollama
brew install ollama
ollama serve
ollama pull llama3.2

# Test it
curl http://localhost:11434/api/generate -d '{{
  "model": "llama3.2",
  "prompt": "Hello!",
  "stream": false
}}'
```

## What You Can Build

Here are some tools from my collection:

1. **Voice Commander** — Say "Hey Jarvis" to execute any command
2. **Multi-Agent Crew** — 5 AI agents collaborate on content
3. **RAG Pipeline** — Ask questions about your documents
4. **AI Code Reviewer** — Reviews git diffs automatically
5. **Content Generator** — YouTube scripts for 9 channels

## Key Takeaway

You don't need expensive APIs to use AI. Local models are good enough for 90% of tasks, and they're completely free.

## Resources

- 🔗 All 45 tools: [github.com/amrendramishra/ai-tools](https://github.com/amrendramishra/ai-tools)
- 🌐 Portfolio: [amrendranmishra.dev](https://amrendranmishra.dev)
- 📊 Kaggle: [kaggle.com/amrendranmishra](https://www.kaggle.com/amrendranmishra)

---

*If you found this helpful, follow me for daily AI/engineering content. I share what actually works in production.*
"""

def publish_to_devto(title, body, tags):
    """Publish article to Dev.to"""
    article = {
        "article": {
            "title": title,
            "body_markdown": body,
            "published": True,
            "tags": tags[:4],  # Dev.to max 4 tags
            "series": "AI Tools & Automation",
            "canonical_url": f"https://amrendranmishra.dev"
        }
    }
    
    data = json.dumps(article).encode()
    req = urllib.request.Request(
        "https://dev.to/api/articles",
        data=data,
        headers={
            "Content-Type": "application/json",
            "api-key": DEVTO_KEY
        }
    )
    
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        return result.get("url", "")

def main():
    day = datetime.now().timetuple().tm_yday % len(TOPICS)
    title, tags = TOPICS[day]
    
    print(f"📝 Today's article: {title}")
    print(f"🏷️  Tags: {tags}")
    
    # Try Ollama first, fallback to template
    body = generate_article_with_ollama(title, tags)
    if not body:
        print("⚠️  Ollama unavailable, using template")
        body = generate_article_without_ollama(title, tags)
    
    print(f"📄 Generated {len(body)} chars")
    
    url = publish_to_devto(title, body, tags)
    print(f"✅ Published: {url}")
    return url

if __name__ == "__main__":
    main()
