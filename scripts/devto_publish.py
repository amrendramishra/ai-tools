#!/usr/bin/env python3
"""Auto-publish AI articles to Dev.to using curl (avoids bot detection)"""
import os
import json
import subprocess
import random
from datetime import datetime

DEVTO_KEY = os.environ.get("DEVTO_API_KEY", "")

TOPICS = [
    ("5 Local AI Tools That Replace Expensive Cloud APIs", ["ai", "ollama", "productivity", "tutorial"]),
    ("How I Run 9 YouTube Channels Without Lifting a Finger", ["youtube", "automation", "python", "ai"]),
    ("Multi-Agent AI Systems: Build Without CrewAI or AutoGen", ["ai", "agents", "python", "tutorial"]),
    ("RAG Pipeline from Scratch: Ask Your Documents Questions", ["rag", "ai", "chromadb", "tutorial"]),
    ("Voice Commander: Control Your Mac with Hey Jarvis", ["ai", "python", "productivity", "mac"]),
    ("MCP Protocol: The USB-C Standard for AI Tools", ["mcp", "ai", "claude", "tools"]),
    ("Java 21 Quarkus AWS Lambda: My Production Serverless Stack", ["java", "aws", "serverless", "backend"]),
    ("DynamoDB Design Lessons from 2M Daily Transactions", ["aws", "database", "architecture", "backend"]),
    ("System Design: Status Page for 400M Users", ["systemdesign", "architecture", "webdev", "backend"]),
    ("From SDE to VP in 12 Years: What Actually Works", ["career", "growth", "programming", "advice"]),
    ("AI Code Reviewer: Never Ship Bugs Again", ["ai", "git", "devtools", "productivity"]),
    ("Build a Local ChatGPT UI with Zero API Costs", ["ai", "webdev", "javascript", "tutorial"]),
    ("GitHub Actions for Free 24/7 AI Automation", ["github", "automation", "devops", "ai"]),
    ("LangGraph Practical Guide: When to Use It Over LangChain", ["ai", "langchain", "python", "tutorial"]),
    ("Smart File Organizer: AI Watches Your Downloads Folder", ["ai", "automation", "python", "productivity"]),
    ("Production GenAI: Hallucination Guardrails and PII Redaction", ["ai", "production", "enterprise", "architecture"]),
    ("Serverless Cold Start Optimization: 60 Percent Faster", ["aws", "serverless", "performance", "java"]),
    ("ChromaDB Tutorial: Vector Database for Your AI Apps", ["ai", "database", "python", "tutorial"]),
    ("Whisper Offline Speech Recognition Setup Guide", ["ai", "python", "tutorial", "mac"]),
    ("Mock Interview AI Bot: Practice System Design Daily", ["interview", "ai", "career", "systemdesign"]),
    ("Content Repurposer: One Article Becomes Seven Posts", ["automation", "content", "ai", "productivity"]),
    ("AI Resume Generator That Gets Shortlisted", ["career", "ai", "python", "tools"]),
    ("Kafka Migration: 200 Percent Data Freshness Improvement", ["kafka", "architecture", "java", "backend"]),
    ("Amazon Q in Production: 72 Percent Time Saved", ["aws", "ai", "productivity", "java"]),
    ("Telegram Bot with Local AI: No API Costs", ["telegram", "ai", "python", "tutorial"]),
    ("Habit Tracker with AI Coaching: My Daily System", ["productivity", "ai", "python", "health"]),
    ("Knowledge Graph from Your Documents Using AI", ["ai", "python", "knowledge", "tutorial"]),
    ("Auto-Documentation Generator for Any Code Repo", ["ai", "devtools", "python", "automation"]),
    ("Personal AI Assistant That Learns About You", ["ai", "python", "productivity", "tutorial"]),
    ("The Zero Cost Tech Stack: Everything Free Everything Automated", ["opensource", "automation", "tools", "ai"]),
]

BODIES = [
    """
## The Problem With Cloud AI

Every token costs money. Every API call adds up. And your data goes to their servers.

## The Local Alternative

```bash
brew install ollama
ollama pull llama3.2
ollama serve
```

Now you have a GPT-4 level model running on your MacBook. Free. Private. Fast.

## Real Code Example

```python
import requests

def ask_local_ai(question):
    r = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3.2", "prompt": question, "stream": False}
    )
    return r.json()["response"]

# Works immediately, no API key needed
answer = ask_local_ai("Explain Docker in one paragraph")
print(answer)
```

## Available Models

| Model | Size | Best For |
|-------|------|----------|
| llama3.2 | 2GB | General use |
| codellama | 4GB | Code tasks |
| mistral | 4.4GB | Fast reasoning |
| phi3 | 2.2GB | Lightweight tasks |
| gemma2 | 5.4GB | Complex reasoning |

## What You Can Build

- RAG systems for your documents
- Voice assistants that work offline
- Code reviewers on every git commit
- Content generators at zero cost
- Personal AI that remembers you

## My Setup

I built 45 tools using this stack. All free. All local. All open source.

[github.com/amrendramishra/ai-tools](https://github.com/amrendramishra/ai-tools)

---
*VP at JPMorgan Chase. Building AI tools at amrendranmishra.dev*
""",
    """
## Why Automate Content Creation

Creating content manually for 9 channels would take 8+ hours daily. I have a full-time job as VP at JPMorgan. The math doesnt work.

## The Pipeline

```
Trending Topic CSV
       ↓
  AI Script (Ollama/Gemini)
       ↓
  Google Cloud TTS (Voice)
       ↓
  Pexels Images + MoviePy Video
       ↓
  YouTube API Upload
```

## Scheduling with Mac LaunchAgents

```xml
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.gyaaninfive.youtube</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/path/to/upload.py</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>18</integer>
    <key>Minute</key><integer>15</integer>
  </dict>
</dict>
</plist>
```

One plist per channel. Runs at the exact scheduled time.

## Total Monthly Cost

Google Cloud TTS: Free (4M chars/month)
Pexels API: Free
YouTube API: Free
Ollama: Free (local)

**Total: ₹0/month**

[Full code on GitHub](https://github.com/amrendramishra/ai-tools)

---
*9 channels. Daily uploads. Zero manual work.*
""",
]

def publish(title, body, tags):
    """Use curl for Dev.to publishing - most reliable across environments"""
    payload = {
        "article": {
            "title": title,
            "body_markdown": body.strip(),
            "published": True,
            "tags": tags[:4],
            "series": "AI Tools and Automation"
        }
    }

    cmd = [
        "curl", "-s",
        "-X", "POST",
        "https://dev.to/api/articles",
        "-H", f"api-key: {DEVTO_KEY}",
        "-H", "Content-Type: application/json",
        "-H", "User-Agent: curl/7.88.1",
        "-H", "Accept: application/json",
        "-d", json.dumps(payload)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    response = json.loads(result.stdout)

    if "url" in response:
        return response["url"]
    else:
        raise Exception(f"Error: {response.get('error', response)}")

def main():
    if not DEVTO_KEY:
        raise Exception("DEVTO_API_KEY not set")

    day = datetime.now().timetuple().tm_yday % len(TOPICS)
    title, tags = TOPICS[day]
    body = BODIES[day % len(BODIES)]

    print(f"Publishing: {title}")
    url = publish(title, body, tags)
    print(f"Success: {url}")

if __name__ == "__main__":
    main()
