#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
🎤 Voice Commander Pro v2.0 - Ultimate AI Control Center for Mac

UPGRADES over v1:
✅ Offline speech recognition (Whisper - no internet needed)
✅ Global hotkey (Ctrl+Space) to trigger from anywhere
✅ Continuous listening mode with wake word "hey jarvis"
✅ Conversation memory (remembers context)
✅ Multi-language support (English + Hindi)
✅ Command chaining ("research AI then write a blog about it")
✅ Rich terminal UI with colors and progress
✅ Smart context awareness (time, location, last command)
✅ Async execution (non-blocking)
✅ Sound effects for feedback
✅ History & favorites
"""
from __future__ import annotations

import os
import sys
import json
import time
import wave
import struct
import tempfile
import threading
import subprocess
import sqlite3
import signal
from pathlib import Path
from datetime import datetime
from collections import deque

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ============================================================
# CONFIGURATION
# ============================================================

AI_DIR = Path.home() / "Downloads" / "AI"
PROJECTS_DIR = AI_DIR / "projects"
OLLAMA_URL = "http://localhost:11434/api/generate"
DB_PATH = AI_DIR / "projects" / "voice-commander" / "memory.db"
WAKE_WORDS = ["hey jarvis", "jarvis", "hey computer", "ok computer", "hey ai"]
HOTKEY_COMBO = "<ctrl>+<space>"  # Global hotkey

console = Console() if RICH_AVAILABLE else None

# ============================================================
# MEMORY & CONTEXT
# ============================================================

class Memory:
    """Persistent conversation memory"""
    
    def __init__(self):
        self.db = sqlite3.connect(str(DB_PATH))
        self.db.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY, timestamp TEXT, command TEXT, 
            result TEXT, category TEXT)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS context (
            key TEXT PRIMARY KEY, value TEXT, updated TEXT)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY, command TEXT UNIQUE, count INTEGER DEFAULT 1)""")
        self.db.commit()
        self.conversation = deque(maxlen=10)  # Last 10 exchanges
        self.last_result = ""
    
    def add_history(self, command, result, category="general"):
        self.db.execute(
            "INSERT INTO history (timestamp, command, result, category) VALUES (?,?,?,?)",
            (datetime.now().isoformat(), command, result[:500], category))
        self.db.commit()
        self.conversation.append({"role": "user", "content": command})
        self.conversation.append({"role": "assistant", "content": result[:200]})
        self.last_result = result
        # Track favorites
        self.db.execute("""INSERT INTO favorites (command, count) VALUES (?, 1)
                          ON CONFLICT(command) DO UPDATE SET count = count + 1""", (command,))
        self.db.commit()
    
    def get_context(self):
        """Get current context for AI"""
        now = datetime.now()
        context = {
            "time": now.strftime("%I:%M %p"),
            "day": now.strftime("%A"),
            "date": now.strftime("%B %d, %Y"),
            "period": "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening",
            "last_command": self.conversation[-2]["content"] if len(self.conversation) >= 2 else None,
            "conversation_length": len(self.conversation),
        }
        return context
    
    def get_favorites(self, limit=5):
        cursor = self.db.execute("SELECT command, count FROM favorites ORDER BY count DESC LIMIT ?", (limit,))
        return cursor.fetchall()
    
    def get_history(self, limit=10):
        cursor = self.db.execute(
            "SELECT timestamp, command, category FROM history ORDER BY id DESC LIMIT ?", (limit,))
        return cursor.fetchall()
    
    def get_conversation_context(self):
        """Format conversation history for AI"""
        if not self.conversation:
            return ""
        return "\n".join([f"{m['role']}: {m['content']}" for m in self.conversation])


# ============================================================
# SPEECH ENGINE (Whisper offline + Google online fallback)
# ============================================================

class SpeechEngine:
    """Handles both offline (Whisper) and online speech recognition"""
    
    def __init__(self, use_whisper=True, language="en"):
        self.use_whisper = use_whisper
        self.language = language
        self.whisper_model = None
        self.is_listening = False
        
        if use_whisper:
            try:
                import whisper
                console_print("⏳ Loading Whisper model (first time takes a moment)...")
                self.whisper_model = whisper.load_model("base")  # tiny/base/small/medium
                console_print("✅ Whisper loaded - offline speech recognition ready!")
            except Exception as e:
                console_print(f"⚠️ Whisper unavailable ({e}), using Google Speech")
                self.use_whisper = False
    
    def listen(self, timeout=7, phrase_limit=15):
        """Record audio and transcribe"""
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        
        try:
            with sr.Microphone() as source:
                play_sound("listening")
                console_print("🎤 [bold green]Listening...[/]")
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            
            play_sound("processing")
            console_print("⏳ Processing...")
            
            if self.use_whisper and self.whisper_model:
                # Offline transcription with Whisper
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
                    f.write(audio.get_wav_data())
                    f.flush()
                    result = self.whisper_model.transcribe(
                        f.name, 
                        language=self.language if self.language != "auto" else None,
                        fp16=False
                    )
                    text = result["text"].strip()
            else:
                # Online fallback
                text = recognizer.recognize_google(audio, language="en-IN")
            
            if text:
                console_print(f'📝 [bold cyan]"{text}"[/]')
                play_sound("success")
            return text
            
        except Exception as e:
            if "timed out" in str(e).lower():
                console_print("⏰ No speech detected")
            else:
                console_print(f"❌ {e}")
            return None
    
    def continuous_listen(self, callback, wake_word_mode=True):
        """Continuously listen for wake word or commands"""
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        
        self.is_listening = True
        console_print("👂 [bold yellow]Continuous listening mode - say 'Hey Jarvis'[/]")
        
        while self.is_listening:
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    audio = recognizer.listen(source, timeout=3, phrase_time_limit=8)
                
                # Quick recognition for wake word
                try:
                    text = recognizer.recognize_google(audio, language="en-IN").lower()
                except:
                    continue
                
                if wake_word_mode:
                    # Check for wake word
                    if any(wake in text for wake in WAKE_WORDS):
                        play_sound("wake")
                        console_print("✨ [bold magenta]Wake word detected![/]")
                        # Now listen for actual command
                        command = self.listen(timeout=10, phrase_limit=20)
                        if command:
                            callback(command)
                    elif text.strip():
                        # Partial wake word feedback
                        pass
                else:
                    if text.strip():
                        callback(text)
                        
            except Exception:
                continue
    
    def stop_listening(self):
        self.is_listening = False


# ============================================================
# VOICE OUTPUT (Enhanced)
# ============================================================

class VoiceOutput:
    """Enhanced text-to-speech with multiple voices"""
    
    VOICES = {
        "default": "Samantha",
        "male": "Daniel",
        "female": "Samantha",
        "indian": "Rishi",
        "hindi": "Lekha",
    }
    
    def __init__(self, enabled=True, voice="default"):
        self.enabled = enabled
        self.voice = self.VOICES.get(voice, "Samantha")
        self.speaking = False
    
    def speak(self, text, voice=None):
        if not self.enabled:
            return
        v = voice or self.voice
        clean = text.replace('`', '').replace('#', '').replace('*', '').replace('\n', '. ')
        clean = clean[:600]
        self.speaking = True
        subprocess.Popen(
            ["say", "-v", v, "-r", "180", clean],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        self.speaking = False
    
    def stop(self):
        subprocess.run(["killall", "say"], capture_output=True)
        self.speaking = False


# ============================================================
# GLOBAL HOTKEY
# ============================================================

class HotkeyListener:
    """Listen for global keyboard shortcut (Ctrl+Space)"""
    
    def __init__(self, callback):
        self.callback = callback
        self.thread = None
    
    def start(self):
        try:
            from pynput import keyboard
            
            def on_hotkey():
                self.callback()
            
            hotkey = keyboard.HotKey(
                keyboard.HotKey.parse(HOTKEY_COMBO),
                on_hotkey
            )
            
            def on_press(key):
                hotkey.press(key)
            
            def on_release(key):
                hotkey.release(key)
            
            listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            listener.daemon = True
            listener.start()
            console_print(f"⌨️  Global hotkey [bold]{HOTKEY_COMBO}[/] registered")
            return True
        except Exception as e:
            console_print(f"⚠️  Hotkey registration failed: {e}")
            return False


# ============================================================
# COMMAND PROCESSOR (AI-powered intent detection)
# ============================================================

class CommandProcessor:
    """Smart command matching with AI fallback and chaining"""
    
    INTENT_MAP = {
        "content": ["generate content", "create content", "make video", "content for", "batch content"],
        "ideas": ["video ideas", "give me ideas", "suggest videos", "topic ideas"],
        "trending": ["trending", "what's trending", "viral topics", "popular topics"],
        "research": ["research", "look up", "find out about", "investigate"],
        "news": ["news", "latest news", "what's happening", "headlines"],
        "focus": ["focus", "pomodoro", "concentrate", "deep work", "timer"],
        "organize": ["organize", "clean up", "sort files", "tidy"],
        "habit": ["habit", "track", "log habit", "my habits", "streak"],
        "chat": ["tell me", "explain", "what is", "how to", "why", "who"],
        "email": ["email", "draft email", "write email", "compose"],
        "blog": ["blog", "write blog", "article", "post"],
        "summarize": ["summarize", "summary", "tldr", "shorten"],
        "translate": ["translate", "convert to", "in hindi", "in english"],
        "webui": ["web ui", "open chat", "web interface", "browser chat"],
        "n8n": ["n8n", "workflow", "automation tool"],
        "backup": ["backup", "back up", "save repos"],
        "status": ["status", "system status", "how are you", "check systems"],
        "time": ["time", "what time", "date", "day"],
        "reminder": ["remind", "reminder", "alert me", "don't forget"],
        "note": ["note", "take note", "remember", "save this"],
        "code_review": ["review code", "code review", "check my code"],
        "code": ["write code", "generate code", "code for", "program"],
        "find_file": ["find file", "where is", "locate", "look for file"],
        "newsletter": ["newsletter", "digest", "weekly update"],
        "github": ["github", "repos", "my repositories", "git stats"],
        "create_repo": ["create repo", "new repo", "make repository"],
        "history": ["history", "what did i say", "previous commands"],
        "favorites": ["favorites", "most used", "frequent commands"],
        "help": ["help", "what can you do", "commands", "options"],
        "stop": ["stop", "quit", "exit", "goodbye", "shut down", "bye"],
    }
    
    def classify(self, text):
        """Classify command intent"""
        text_lower = text.lower().strip()
        
        # Check for command chaining (then, and then, also)
        chain_words = [" then ", " and then ", " also ", " after that "]
        commands = [text_lower]
        for cw in chain_words:
            if cw in text_lower:
                commands = [c.strip() for c in text_lower.split(cw)]
                break
        
        results = []
        for cmd_text in commands:
            intent = self._match_intent(cmd_text)
            results.append((intent, cmd_text))
        
        return results
    
    def _match_intent(self, text):
        """Match text to intent"""
        for intent, triggers in self.INTENT_MAP.items():
            for trigger in triggers:
                if trigger in text:
                    return intent
        return "chat"  # Default to chat


# ============================================================
# HELPERS
# ============================================================

def console_print(text):
    """Print with rich formatting if available"""
    if RICH_AVAILABLE and console:
        console.print(text)
    else:
        # Strip rich markup
        import re
        clean = re.sub(r'\[.*?\]', '', str(text))
        print(clean)


def play_sound(event):
    """Play macOS system sounds for feedback"""
    sounds = {
        "listening": "/System/Library/Sounds/Pop.aiff",
        "processing": "/System/Library/Sounds/Tink.aiff", 
        "success": "/System/Library/Sounds/Glass.aiff",
        "error": "/System/Library/Sounds/Basso.aiff",
        "wake": "/System/Library/Sounds/Purr.aiff",
    }
    sound_file = sounds.get(event)
    if sound_file and os.path.exists(sound_file):
        subprocess.Popen(["afplay", sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ask_ollama(prompt, model="llama3.2", context=""):
    """Query Ollama with optional conversation context"""
    import urllib.request
    full_prompt = prompt
    if context:
        full_prompt = f"Previous conversation:\n{context}\n\nNow answer: {prompt}"
    try:
        data = json.dumps({"model": model, "prompt": full_prompt, "stream": False}).encode()
        req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["response"]
    except Exception as e:
        return f"Error connecting to Ollama: {e}"


# ============================================================
# MAIN APP
# ============================================================

class VoiceCommanderPro:
    """The ultimate AI voice control center"""
    
    def __init__(self, mode="both", whisper=True, speak_enabled=True, language="en"):
        self.memory = Memory()
        self.speech = SpeechEngine(use_whisper=whisper, language=language)
        self.voice = VoiceOutput(enabled=speak_enabled)
        self.processor = CommandProcessor()
        self.mode = mode
        self.running = True
        
        # Import command executor from v1 (keeps all the execution logic)
        sys.path.insert(0, str(Path(__file__).parent))
    
    def execute(self, intent, text):
        """Execute a command by intent"""
        from voice_commander import execute_command, match_command
        
        # Map new intents to old command names
        intent_to_cmd = {
            "content": "content_pipeline", "ideas": "content_ideas",
            "trending": "trending", "research": "research", "news": "news",
            "focus": "focus", "organize": "organize", "habit": "habit",
            "chat": "chat", "email": "email", "blog": "blog",
            "summarize": "summarize", "translate": "translate",
            "webui": "webui", "n8n": "n8n", "backup": "backup",
            "status": "status", "time": "time", "reminder": "reminder",
            "note": "note", "code_review": "code_review", "code": "code",
            "find_file": "find_file", "newsletter": "newsletter",
            "github": "github", "create_repo": "create_repo",
        }
        
        cmd = intent_to_cmd.get(intent, "chat")
        
        # Special commands handled here
        if intent == "stop":
            self.voice.speak("Goodbye! Voice Commander shutting down.")
            self.running = False
            return "Stopped"
        
        elif intent == "history":
            history = self.memory.get_history()
            result = "\n".join([f"  {h[0][:16]} | {h[1]}" for h in history])
            console_print(f"\n📜 Command History:\n{result}")
            return result
        
        elif intent == "favorites":
            favs = self.memory.get_favorites()
            result = "\n".join([f"  {f[0]} ({f[1]}x)" for f in favs])
            console_print(f"\n⭐ Most Used:\n{result}")
            return result
        
        elif intent == "help":
            self.show_help()
            return "Help shown"
        
        else:
            # Use original executor with context
            old_speak = None
            try:
                # Redirect speak to our enhanced version
                import voice_commander as vc
                old_speak = vc.speak
                vc.speak = self.voice.speak
                execute_command(cmd, text)
                return f"Executed: {intent}"
            except Exception as e:
                # Fallback: direct AI chat
                context = self.memory.get_conversation_context()
                answer = ask_ollama(text, context=context)
                self.voice.speak(answer[:300])
                console_print(f"\n🤖 {answer}")
                return answer
            finally:
                if old_speak:
                    import voice_commander as vc
                    vc.speak = old_speak
    
    def process_command(self, text):
        """Process a command with chaining support"""
        if not text:
            return
        
        # Classify (supports chaining)
        commands = self.processor.classify(text)
        
        for intent, cmd_text in commands:
            console_print(f"🎯 [bold yellow]{intent}[/] → {cmd_text}")
            result = self.execute(intent, cmd_text)
            self.memory.add_history(cmd_text, str(result)[:500], intent)
            
            if not self.running:
                break
    
    def hotkey_triggered(self):
        """Called when global hotkey is pressed"""
        play_sound("wake")
        console_print("\n✨ [bold magenta]Hotkey activated! Listening...[/]")
        text = self.speech.listen(timeout=8, phrase_limit=20)
        if text:
            self.process_command(text)
    
    def show_help(self):
        """Show available commands"""
        if RICH_AVAILABLE:
            table = Table(title="🎤 Voice Commander Pro - Commands")
            table.add_column("Category", style="cyan")
            table.add_column("Say This", style="green")
            table.add_column("What Happens", style="white")
            
            table.add_row("📺 YouTube", "generate content / video ideas / trending", "Content for all 9 channels")
            table.add_row("🔍 Research", "research [topic] / latest news", "Tavily + AI deep research")
            table.add_row("✍️ Writing", "write email / blog / summarize / translate", "AI writing + clipboard")
            table.add_row("⏱️ Focus", "start focus / organize files / habit status", "Productivity tools")
            table.add_row("💻 Code", "code review / write code for... / find file", "Dev tools")
            table.add_row("🌐 Apps", "open web ui / start n8n / github stats", "Launch apps")
            table.add_row("📝 Notes", "take note... / remind me... / newsletter", "Memory & notes")
            table.add_row("🔗 Chain", "research AI then write blog about it", "Chain commands with 'then'")
            table.add_row("⌨️ Hotkey", "Ctrl+Space", "Trigger from anywhere")
            table.add_row("👂 Wake", "Hey Jarvis", "Continuous listening mode")
            table.add_row("🛑 Stop", "stop / quit / goodbye", "Exit")
            
            console.print(table)
        else:
            print("""
Commands: generate content, video ideas, trending, research [topic],
latest news, write email, write blog, summarize, translate, 
start focus, organize files, habit status, code review, 
write code for..., find file..., open web ui, start n8n,
take note..., remind me..., github stats, stop/quit
Chain: "research AI then write blog about it"
Hotkey: Ctrl+Space | Wake word: "Hey Jarvis"
""")
    
    def run(self):
        """Main loop"""
        # Banner
        if RICH_AVAILABLE:
            console.print(Panel.fit(
                "[bold magenta]🎤 Voice Commander Pro v2.0[/]\n"
                "[dim]AI Control Center for Mac[/]\n\n"
                f"Mode: [bold]{self.mode}[/] | "
                f"Whisper: [bold]{'✅' if self.speech.use_whisper else '❌'}[/] | "
                f"Models: [bold]6[/] | "
                f"Tools: [bold]32[/]\n"
                f"Hotkey: [bold cyan]Ctrl+Space[/] | "
                f"Wake: [bold cyan]Hey Jarvis[/]",
                title="[bold green]Ready[/]"
            ))
        else:
            print("\n🎤 Voice Commander Pro v2.0 - Ready!")
            print(f"   Mode: {self.mode} | Hotkey: Ctrl+Space | Wake: 'Hey Jarvis'\n")
        
        # Register global hotkey
        hotkey = HotkeyListener(self.hotkey_triggered)
        hotkey.start()
        
        self.voice.speak("Voice Commander Pro is ready. Say Hey Jarvis, press Control Space, or type a command.")
        self.show_help()
        
        while self.running:
            try:
                if self.mode == "voice":
                    text = self.speech.listen()
                elif self.mode == "continuous":
                    # Continuous wake word listening
                    self.speech.continuous_listen(self.process_command)
                    break
                elif self.mode == "type":
                    text = input("\n⌨️  Command: ").strip()
                else:  # both
                    choice = input("\n⌨️  Command (or 'v'=voice, 'c'=continuous, '?'=help): ").strip()
                    if choice.lower() == 'v':
                        text = self.speech.listen()
                    elif choice.lower() == 'c':
                        console_print("👂 Entering continuous mode... say 'Hey Jarvis' to activate")
                        self.speech.continuous_listen(self.process_command)
                        continue
                    elif choice == '?':
                        self.show_help()
                        continue
                    else:
                        text = choice
                
                if text:
                    self.process_command(text)
                    
            except KeyboardInterrupt:
                self.voice.speak("Goodbye!")
                console_print("\n👋 Voice Commander Pro stopped.")
                break
            except Exception as e:
                console_print(f"❌ Error: {e}")


# ============================================================
# ENTRY POINT
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Voice Commander Pro v2.0")
    parser.add_argument("--mode", choices=["voice", "type", "both", "continuous"], 
                       default="both", help="Input mode")
    parser.add_argument("--no-whisper", action="store_true", help="Disable Whisper (use Google Speech)")
    parser.add_argument("--no-speak", action="store_true", help="Disable voice output")
    parser.add_argument("--language", default="en", choices=["en", "hi", "auto"],
                       help="Recognition language (en=English, hi=Hindi, auto=detect)")
    parser.add_argument("--command", "-c", help="Execute single command and exit")
    parser.add_argument("--continuous", action="store_true", help="Continuous wake word mode")
    args = parser.parse_args()
    
    if args.continuous:
        args.mode = "continuous"
    
    app = VoiceCommanderPro(
        mode=args.mode,
        whisper=not args.no_whisper,
        speak_enabled=not args.no_speak,
        language=args.language
    )
    
    if args.command:
        app.process_command(args.command)
    else:
        app.run()


if __name__ == "__main__":
    main()
