#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
Voice-to-AI - Interactive AI chat with optional voice output via macOS 'say' command.
Uses Ollama (llama3.2) for AI responses and macOS TTS for speaking answers.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import readline  # noqa: F401 - enables input history/editing
from pathlib import Path

import requests

# Configuration
OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"
HISTORY_FILE = Path(__file__).parent / ".chat_history"


def check_ollama():
    """Verify Ollama is running and model is available."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            return models
    except requests.RequestException:
        pass
    return None


def chat_with_ollama(prompt, model, conversation_history):
    """Send a message to Ollama and get a response."""
    messages = conversation_history + [{"role": "user", "content": prompt}]

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": True,
            },
            stream=True,
            timeout=120,
        )

        if response.status_code != 200:
            return None, f"Ollama returned status {response.status_code}"

        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    full_response += chunk
                    print(chunk, end="", flush=True)
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue

        print()  # newline after streaming
        return full_response, None

    except requests.Timeout:
        return None, "Request timed out (120s)"
    except requests.RequestException as e:
        return None, f"Connection error: {e}"


def speak(text, voice="Samantha"):
    """Speak text using macOS 'say' command."""
    # Clean text for speech (remove markdown, code blocks, etc.)
    clean = text.replace("```", "").replace("`", "")
    clean = clean.replace("#", "").replace("*", "")
    # Limit length for practical speech
    if len(clean) > 1000:
        clean = clean[:1000] + "... (truncated for speech)"

    try:
        subprocess.run(
            ["say", "-v", voice, clean],
            timeout=60,
            capture_output=True,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


def record_audio(duration=5):
    """Record audio using sox's rec command. Returns path to recorded file."""
    audio_file = Path(__file__).parent / "recording.wav"

    if not shutil.which("rec"):
        print("⚠️  'rec' (sox) not installed. Run: brew install sox")
        return None

    print(f"🎤 Recording for {duration} seconds... (speak now)")
    try:
        subprocess.run(
            ["rec", str(audio_file), "trim", "0", str(duration)],
            timeout=duration + 5,
            capture_output=True,
        )
        if audio_file.exists():
            print("✅ Recording saved.")
            return str(audio_file)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"Recording failed: {e}")

    return None


def transcribe_audio(audio_path):
    """Attempt to transcribe audio using Whisper if available."""
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return result["text"]
    except ImportError:
        print("⚠️  Whisper not installed. Install with: pip install openai-whisper")
        return None
    except Exception as e:
        print(f"Transcription error: {e}")
        return None


def print_banner(model, speak_enabled):
    """Print welcome banner."""
    speak_status = "🔊 ON" if speak_enabled else "🔇 OFF"
    print(f"""
╔══════════════════════════════════════════════════════════╗
║                  🤖 Voice-to-AI Chat                    ║
╠══════════════════════════════════════════════════════════╣
║  Model: {model:<20s} Speech: {speak_status:<12s}  ║
║                                                          ║
║  Commands:                                               ║
║    /speak      - Toggle voice output                     ║
║    /record     - Record audio (requires sox)             ║
║    /model NAME - Switch model                            ║
║    /clear      - Clear conversation history              ║
║    /help       - Show this help                          ║
║    /quit       - Exit                                    ║
║                                                          ║
║  Type your question or paste text to chat with AI.       ║
╚══════════════════════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(
        description="Voice-to-AI - Interactive chat with Ollama and optional voice output"
    )
    parser.add_argument(
        "--speak", action="store_true",
        help="Enable voice output (macOS 'say' command)"
    )
    parser.add_argument(
        "--model", "-m", type=str, default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--voice", "-v", type=str, default="Samantha",
        help="macOS voice for TTS (default: Samantha)"
    )
    parser.add_argument(
        "--record-duration", "-r", type=int, default=5,
        help="Audio recording duration in seconds (default: 5)"
    )

    args = parser.parse_args()
    model = args.model
    speak_enabled = args.speak
    voice = args.voice
    record_duration = args.record_duration

    # Check Ollama
    print("🔍 Checking Ollama connection...")
    models = check_ollama()
    if models is None:
        print("❌ Cannot connect to Ollama at localhost:11434")
        print("   Make sure Ollama is running: ollama serve")
        sys.exit(1)

    print(f"✅ Ollama connected. Available models: {', '.join(models[:5])}")

    if not any(model in m for m in models):
        print(f"⚠️  Model '{model}' may not be available. Pull it with: ollama pull {model}")

    print_banner(model, speak_enabled)

    # Conversation history for context
    conversation_history = []

    # Load readline history
    if HISTORY_FILE.exists():
        try:
            readline.read_history_file(str(HISTORY_FILE))
        except (OSError, AttributeError):
            pass

    while True:
        try:
            user_input = input("\n🧑 You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Goodbye!")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input.startswith("/"):
            cmd = user_input.lower().split()

            if cmd[0] == "/quit" or cmd[0] == "/exit":
                print("👋 Goodbye!")
                break

            elif cmd[0] == "/speak":
                speak_enabled = not speak_enabled
                status = "🔊 ON" if speak_enabled else "🔇 OFF"
                print(f"  Voice output: {status}")
                continue

            elif cmd[0] == "/model":
                if len(cmd) > 1:
                    model = cmd[1]
                    print(f"  Switched to model: {model}")
                else:
                    print(f"  Current model: {model}")
                    print(f"  Available: {', '.join(models[:10])}")
                continue

            elif cmd[0] == "/record":
                dur = int(cmd[1]) if len(cmd) > 1 else record_duration
                audio_path = record_audio(dur)
                if audio_path:
                    transcription = transcribe_audio(audio_path)
                    if transcription:
                        print(f"  📝 Transcription: {transcription}")
                        user_input = transcription
                    else:
                        print("  Could not transcribe. Type your question instead.")
                        continue
                else:
                    continue

            elif cmd[0] == "/clear":
                conversation_history = []
                print("  🧹 Conversation history cleared.")
                continue

            elif cmd[0] == "/help":
                print_banner(model, speak_enabled)
                continue

            else:
                print(f"  Unknown command: {cmd[0]}")
                continue

        # Chat with Ollama
        print(f"\n🤖 AI: ", end="", flush=True)
        response, error = chat_with_ollama(user_input, model, conversation_history)

        if error:
            print(f"\n❌ Error: {error}")
            continue

        if response:
            # Update conversation history (keep last 20 messages)
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": response})
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]

            # Speak the response if enabled
            if speak_enabled:
                speak(response, voice)

        # Save readline history
        try:
            readline.write_history_file(str(HISTORY_FILE))
        except (OSError, AttributeError):
            pass


if __name__ == "__main__":
    main()
