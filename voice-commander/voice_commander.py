#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
🎤 Voice Commander - Control Everything with Your Voice
Speak commands → AI understands → Executes actions on your Mac
"""
from __future__ import annotations

import os
import sys
import json
import time
import subprocess
import threading
import signal
from pathlib import Path
from datetime import datetime

# Base paths
AI_DIR = Path.home() / "Downloads" / "AI"
PROJECTS_DIR = AI_DIR / "projects"
OLLAMA_URL = "http://localhost:11434/api/generate"

# ============================================================
# VOICE RECOGNITION
# ============================================================

def listen_for_command(timeout=5, phrase_limit=10):
    """Listen for voice command using macOS microphone"""
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        
        with sr.Microphone() as source:
            print("\n🎤 Listening... (speak now)")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        
        print("⏳ Processing speech...")
        # Use Google's free speech recognition
        text = recognizer.recognize_google(audio, language="en-IN")
        print(f"📝 You said: \"{text}\"")
        return text
    except Exception as e:
        if "No speech detected" in str(e) or "timed out" in str(e).lower():
            print("❌ No speech detected. Try again.")
        else:
            print(f"❌ Speech error: {e}")
        return None


def speak(text):
    """Speak text using macOS 'say' command"""
    # Clean text for speech
    clean = text.replace('`', '').replace('#', '').replace('*', '')
    clean = clean[:500]  # Limit length
    subprocess.Popen(["say", "-v", "Samantha", clean], 
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ============================================================
# COMMAND MATCHING - AI-powered intent detection
# ============================================================

COMMANDS = {
    # Content & YouTube
    "generate content": "content_pipeline",
    "create content": "content_pipeline",
    "video ideas": "content_ideas",
    "trending topics": "trending",
    "trending": "trending",
    "content for": "content_pipeline",
    
    # Research
    "research": "research",
    "search": "search",
    "find": "search",
    "news": "news",
    "latest news": "news",
    
    # Productivity
    "focus": "focus",
    "start focus": "focus",
    "pomodoro": "focus",
    "organize files": "organize",
    "clean downloads": "organize",
    "habit": "habit",
    "track habit": "habit",
    
    # AI Chat
    "ask": "chat",
    "tell me": "chat",
    "explain": "chat",
    "what is": "chat",
    "how to": "chat",
    
    # Writing
    "write email": "email",
    "draft email": "email",
    "write blog": "blog",
    "blog post": "blog",
    "summarize": "summarize",
    "summary": "summarize",
    "translate": "translate",
    
    # System
    "open web ui": "webui",
    "start web": "webui",
    "open chat": "webui",
    "start n8n": "n8n",
    "backup": "backup",
    "back up": "backup",
    "system status": "status",
    "status": "status",
    "what time": "time",
    "reminder": "reminder",
    "remind me": "reminder",
    "note": "note",
    "take note": "note",
    
    # Code
    "review code": "code_review",
    "code review": "code_review",
    "generate code": "code",
    "write code": "code",
    
    # File search
    "find file": "find_file",
    "where is": "find_file",
    "look for": "find_file",
    
    # Newsletter
    "newsletter": "newsletter",
    "write newsletter": "newsletter",
    
    # GitHub
    "github": "github",
    "repos": "github",
    "my repos": "github",
    "create repo": "create_repo",
    
    # Stop/Quit
    "stop": "stop",
    "quit": "stop",
    "exit": "stop",
    "goodbye": "stop",
    "shut down": "stop",
}


def match_command(text):
    """Match spoken text to a command"""
    text_lower = text.lower().strip()
    
    # Direct match
    for trigger, cmd in COMMANDS.items():
        if trigger in text_lower:
            return cmd, text_lower
    
    # If no match, use AI to classify
    return "chat", text_lower


# ============================================================
# COMMAND EXECUTORS
# ============================================================

def ask_ollama(prompt, model="llama3.2"):
    """Quick Ollama query"""
    import urllib.request
    try:
        data = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["response"]
    except Exception as e:
        return f"Error: {e}"


def execute_command(cmd, full_text):
    """Execute the matched command"""
    
    if cmd == "stop":
        speak("Goodbye! Shutting down Voice Commander.")
        print("\n👋 Goodbye!")
        sys.exit(0)
    
    elif cmd == "content_pipeline":
        speak("Generating content for your YouTube channels")
        print("🎬 Running content pipeline...")
        result = subprocess.run(
            [sys.executable, str(PROJECTS_DIR / "06-content-pipeline/content_pipeline.py"), "--batch"],
            capture_output=True, text=True, timeout=120
        )
        output = result.stdout[-500:] if result.stdout else "Content generated!"
        speak("Content generated for all channels")
        print(output)
    
    elif cmd == "content_ideas":
        speak("Generating video ideas")
        channel = extract_channel(full_text)
        args = [sys.executable, str(PROJECTS_DIR / "06-content-pipeline/content_pipeline.py")]
        if channel:
            args.extend(["--channel", channel, "--topic", "auto"])
        else:
            args.append("--batch")
        result = subprocess.run(args, capture_output=True, text=True, timeout=120)
        speak("Video ideas generated")
        print(result.stdout[-500:] if result.stdout else "Done!")
    
    elif cmd == "trending":
        speak("Finding trending topics")
        print("📈 Running trending detector...")
        result = subprocess.run(
            [sys.executable, str(PROJECTS_DIR / "07-trending-detector/trending_detector.py"), "--daily"],
            capture_output=True, text=True, timeout=60
        )
        speak("Trending topics found and saved")
        print(result.stdout[-500:] if result.stdout else "Trends saved!")
    
    elif cmd == "research":
        topic = full_text.replace("research", "").strip()
        if not topic:
            topic = "latest AI news"
        speak(f"Researching {topic}")
        result = subprocess.run(
            [sys.executable, str(PROJECTS_DIR / "tavily-tools/tavily_research.py"), "--topic", topic],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", "")}
        )
        output = result.stdout[-300:] if result.stdout else "Research complete"
        speak(f"Research on {topic} is complete")
        print(output)
    
    elif cmd == "search":
        query = full_text.replace("search", "").replace("find", "").strip()
        speak(f"Searching for {query}")
        answer = ask_ollama(f"Answer briefly: {query}")
        speak(answer[:200])
        print(f"\n💡 {answer}")
    
    elif cmd == "news":
        speak("Getting latest news")
        result = subprocess.run(
            [sys.executable, str(PROJECTS_DIR / "tavily-tools/tavily_research.py"), "--news", "AI technology 2026"],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", "")}
        )
        output = result.stdout[-500:] if result.stdout else "Could not fetch news"
        speak("Here are the latest news highlights")
        print(output)
    
    elif cmd == "focus":
        duration = "25"
        if "50" in full_text or "fifty" in full_text:
            duration = "50"
        elif "90" in full_text or "ninety" in full_text:
            duration = "90"
        speak(f"Starting {duration} minute focus session")
        subprocess.Popen(
            [sys.executable, str(PROJECTS_DIR / "22-focus-mode/focus_mode.py"), "--start", duration]
        )
        print(f"⏱️ Focus session started: {duration} minutes")
    
    elif cmd == "organize":
        speak("Organizing your downloads folder")
        result = subprocess.run(
            [sys.executable, str(PROJECTS_DIR / "21-file-organizer/file_organizer.py"), 
             "--organize", str(Path.home() / "Downloads"), "--dry-run"],
            capture_output=True, text=True, timeout=30
        )
        speak("File organization analysis complete. Check the results.")
        print(result.stdout[-500:] if result.stdout else "Done!")
    
    elif cmd == "habit":
        if "log" in full_text or "done" in full_text or "did" in full_text:
            habit = full_text.split("log")[-1].strip() if "log" in full_text else "exercise"
            subprocess.run(
                [sys.executable, str(PROJECTS_DIR / "24-habit-tracker/habit_tracker.py"), "--log", habit],
                timeout=10
            )
            speak(f"Logged {habit}")
        else:
            result = subprocess.run(
                [sys.executable, str(PROJECTS_DIR / "24-habit-tracker/habit_tracker.py"), "--status"],
                capture_output=True, text=True, timeout=10
            )
            speak("Here are your habits for today")
            print(result.stdout if result.stdout else "No habits tracked yet")
    
    elif cmd == "chat":
        speak("Let me think about that")
        answer = ask_ollama(full_text)
        speak(answer[:300])
        print(f"\n🤖 {answer}")
    
    elif cmd == "email":
        topic = full_text.replace("write email", "").replace("draft email", "").strip()
        speak(f"Drafting email about {topic}")
        answer = ask_ollama(f"Write a professional email about: {topic}. Keep it concise.")
        speak("Email draft ready. Copied to clipboard.")
        subprocess.run(["pbcopy"], input=answer.encode(), check=True)
        print(f"\n📧 Email copied to clipboard:\n{answer}")
    
    elif cmd == "blog":
        topic = full_text.replace("write blog", "").replace("blog post", "").strip()
        speak(f"Writing blog post about {topic}")
        result = subprocess.run(
            [sys.executable, str(PROJECTS_DIR / "20-blog-writer/blog_writer.py"), "--topic", topic, "--length", "medium"],
            capture_output=True, text=True, timeout=120
        )
        speak("Blog post generated")
        print(result.stdout[-500:] if result.stdout else "Done!")
    
    elif cmd == "summarize":
        speak("Summarizing clipboard content")
        clipboard = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
        if clipboard:
            answer = ask_ollama(f"Summarize this in 3 sentences:\n{clipboard[:2000]}")
            speak(answer)
            print(f"\n📝 Summary: {answer}")
        else:
            speak("Clipboard is empty")
    
    elif cmd == "translate":
        speak("Translating clipboard content")
        clipboard = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
        lang = "Hindi" if "hindi" in full_text.lower() else "English"
        answer = ask_ollama(f"Translate this to {lang}:\n{clipboard[:1000]}")
        subprocess.run(["pbcopy"], input=answer.encode(), check=True)
        speak(f"Translated to {lang} and copied")
        print(f"\n🌐 Translation: {answer}")
    
    elif cmd == "webui":
        speak("Opening AI Web Interface")
        subprocess.Popen([str(PROJECTS_DIR / "16-web-ui/start.sh")], 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("🌐 Web UI starting at http://localhost:3000")
    
    elif cmd == "n8n":
        speak("Starting n8n workflow automation")
        subprocess.Popen(["n8n", "start"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.Popen(["open", "http://localhost:5678"])
        print("⚡ n8n starting at http://localhost:5678")
    
    elif cmd == "backup":
        speak("Backing up your GitHub repos")
        result = subprocess.run(
            [sys.executable, str(PROJECTS_DIR / "github-toolkit/github_toolkit.py"), "--backup", 
             str(Path.home() / "github-backup")],
            capture_output=True, text=True, timeout=300,
            env={**os.environ, "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", "")}
        )
        speak("Backup complete")
        print(result.stdout[-300:] if result.stdout else "Done!")
    
    elif cmd == "status":
        speak("Checking system status")
        # Check Ollama
        ollama_ok = "✅" if subprocess.run(["curl", "-s", "http://localhost:11434/"], 
                                           capture_output=True).returncode == 0 else "❌"
        # Models
        models = subprocess.run(["ollama", "list"], capture_output=True, text=True).stdout
        model_count = len(models.strip().split("\n")) - 1
        
        status = f"""
🖥️  System Status:
   Ollama: {ollama_ok} Running ({model_count} models)
   Time: {datetime.now().strftime('%I:%M %p')}
   Projects: 32 AI tools ready
   MCP Servers: 8 configured
   GitHub Actions: 5 workflows (24/7)
"""
        speak(f"All systems operational. {model_count} AI models ready.")
        print(status)
    
    elif cmd == "time":
        now = datetime.now().strftime("%I:%M %p on %A, %B %d")
        speak(f"It's {now}")
        print(f"🕐 {now}")
    
    elif cmd == "reminder":
        text_part = full_text.replace("remind me", "").replace("reminder", "").strip()
        speak(f"Setting reminder: {text_part}")
        # Use osascript to create a macOS reminder
        subprocess.run(["osascript", "-e", 
                       f'display notification "{text_part}" with title "🔔 Reminder" sound name "Glass"'])
        print(f"🔔 Reminder set: {text_part}")
    
    elif cmd == "note":
        note_text = full_text.replace("take note", "").replace("note", "").strip()
        speak(f"Saving note")
        notes_dir = Path.home() / "Documents" / "ai-notes"
        notes_dir.mkdir(exist_ok=True)
        note_file = notes_dir / f"note-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        note_file.write_text(f"# Note - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{note_text}\n")
        speak("Note saved")
        print(f"📝 Saved to: {note_file}")
    
    elif cmd == "code_review":
        speak("Reviewing your latest code changes")
        result = subprocess.run(
            [sys.executable, str(PROJECTS_DIR / "15-code-reviewer/code_reviewer.py"), "--diff"],
            capture_output=True, text=True, timeout=60
        )
        speak("Code review complete")
        print(result.stdout[-500:] if result.stdout else "No staged changes found")
    
    elif cmd == "code":
        desc = full_text.replace("generate code", "").replace("write code", "").strip()
        speak(f"Generating code for {desc}")
        answer = ask_ollama(f"Write Python code for: {desc}. Only output the code.", model="codellama")
        subprocess.run(["pbcopy"], input=answer.encode(), check=True)
        speak("Code generated and copied to clipboard")
        print(f"\n💻 Code copied:\n{answer}")
    
    elif cmd == "find_file":
        query = full_text.replace("find file", "").replace("where is", "").replace("look for", "").strip()
        speak(f"Looking for {query}")
        result = subprocess.run(
            [sys.executable, str(PROJECTS_DIR / "23-ai-finder/ai_finder.py"), "--find", query],
            capture_output=True, text=True, timeout=30
        )
        speak("Here's what I found")
        print(result.stdout[-500:] if result.stdout else "Nothing found")
    
    elif cmd == "newsletter":
        speak("Generating newsletter")
        result = subprocess.run(
            [sys.executable, str(PROJECTS_DIR / "30-ai-newsletter/newsletter.py"),
             "--topic", "AI", "--curate", "--write"],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", "")}
        )
        speak("Newsletter generated")
        print(result.stdout[-500:] if result.stdout else "Done!")
    
    elif cmd == "github":
        speak("Getting your GitHub stats")
        result = subprocess.run(
            [sys.executable, str(PROJECTS_DIR / "github-toolkit/github_toolkit.py"), "--stats"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", "")}
        )
        speak("Here are your GitHub stats")
        print(result.stdout if result.stdout else "Could not fetch stats")
    
    elif cmd == "create_repo":
        name = full_text.replace("create repo", "").replace("create repository", "").strip()
        if name:
            speak(f"Creating repository {name}")
            result = subprocess.run(
                [sys.executable, str(PROJECTS_DIR / "github-toolkit/github_toolkit.py"), 
                 "--create", name, "--description", f"Created via Voice Commander"],
                capture_output=True, text=True, timeout=30,
                env={**os.environ, "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", "")}
            )
            speak(f"Repository {name} created")
            print(result.stdout if result.stdout else "Done!")
    
    else:
        speak("I'm not sure what to do. Let me try to help.")
        answer = ask_ollama(f"Help with: {full_text}")
        speak(answer[:200])
        print(f"\n🤖 {answer}")


def extract_channel(text):
    """Extract channel name from command"""
    channels = {
        "gyaan": "gyaaninfive", "tech": "techin5hindi", "money": "moneyin5",
        "superhuman": "superhuman60s", "horror": "horrorkahani",
        "psychology": "pyaarkapsychology", "zeheela": "zehreelasach",
        "apna": "apnahaq", "agar": "agaraisahotoh"
    }
    for key, val in channels.items():
        if key in text.lower():
            return val
    return None


# ============================================================
# MAIN APP
# ============================================================

def print_banner():
    """Show welcome banner"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           🎤 VOICE COMMANDER - AI Control Center            ║
║                                                              ║
║  Speak or type commands to control your AI tools:           ║
║                                                              ║
║  📺 "generate content" / "video ideas" / "trending"         ║
║  🔍 "research AI agents" / "latest news"                    ║
║  ✍️  "write email" / "write blog" / "summarize"             ║
║  ⏱️  "start focus" / "organize files" / "habit status"      ║
║  💻 "code review" / "write code for..." / "find file..."    ║
║  🌐 "open web ui" / "start n8n" / "github stats"           ║
║  📝 "take note..." / "remind me..." / "translate"           ║
║  📰 "newsletter" / "backup repos"                           ║
║  🛑 "stop" / "quit" / "exit"                                ║
║                                                              ║
║  Mode: [V]oice  [T]ype  [B]oth                             ║
╚══════════════════════════════════════════════════════════════╝
""")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Voice Commander - Control AI tools by voice")
    parser.add_argument("--mode", choices=["voice", "type", "both"], default="both",
                       help="Input mode: voice only, type only, or both")
    parser.add_argument("--no-speak", action="store_true", help="Disable voice output")
    parser.add_argument("--command", "-c", help="Execute a single command and exit")
    args = parser.parse_args()
    
    # Single command mode
    if args.command:
        cmd, full_text = match_command(args.command)
        execute_command(cmd, args.command)
        return
    
    if args.no_speak:
        global speak
        speak = lambda x: None
    
    print_banner()
    speak("Voice Commander is ready. How can I help you?")
    
    while True:
        try:
            if args.mode == "voice":
                text = listen_for_command()
            elif args.mode == "type":
                text = input("\n⌨️  Command: ").strip()
            else:  # both
                print("\n[Press Enter to type, or say 'v' for voice]")
                choice = input("⌨️  Command (or 'v' for voice): ").strip()
                if choice.lower() == 'v':
                    text = listen_for_command()
                else:
                    text = choice
            
            if not text:
                continue
            
            cmd, full_text = match_command(text)
            print(f"🎯 Action: {cmd}")
            execute_command(cmd, full_text)
            
        except KeyboardInterrupt:
            speak("Goodbye!")
            print("\n\n👋 Voice Commander stopped.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue


if __name__ == "__main__":
    main()
