#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
AI Phone Call Assistant - Record, transcribe, classify, and manage calls/messages.
Practical Mac implementation using system audio and Ollama for AI processing.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import wave
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))
from call_log import CallLog

# Configuration
OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2"
RECORDINGS_DIR = Path(__file__).parent / "recordings"
RECORDINGS_DIR.mkdir(exist_ok=True)
DB_PATH = Path(__file__).parent / "calls.db"

# Initialize database
call_log = CallLog(str(DB_PATH))


def call_ollama(prompt: str, system: str = None, temperature: float = 0.3) -> str:
    """Call Ollama API for text generation."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature}
    }
    if system:
        payload["system"] = system
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["response"].strip()
    except requests.exceptions.ConnectionError:
        return "[Error: Cannot connect to Ollama at localhost:11434. Is it running?]"
    except Exception as e:
        return f"[Error: {e}]"


def send_mac_notification(title: str, message: str, sound: str = "default"):
    """Send a macOS notification."""
    script = f'''display notification "{message}" with title "{title}" sound name "{sound}"'''
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    except Exception:
        pass


def get_audio_duration(filepath: str) -> float:
    """Get duration of a WAV file in seconds."""
    try:
        with wave.open(filepath, 'r') as f:
            frames = f.getnframes()
            rate = f.getframerate()
            return frames / float(rate)
    except Exception:
        return 0.0


def record_audio(output_file: str, duration: int = None, prompt_stop: bool = False) -> str:
    """Record audio from Mac microphone using sox (rec command)."""
    filepath = str(RECORDINGS_DIR / output_file)

    if duration:
        print(f"🎙️  Recording for {duration} seconds... ", end="", flush=True)
        cmd = ["rec", "-q", filepath, "rate", "16000", "channels", "1", "trim", "0", str(duration)]
    else:
        print("🎙️  Recording... Press Ctrl+C to stop.")
        cmd = ["rec", "-q", filepath, "rate", "16000", "channels", "1"]

    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=duration + 5 if duration else 3600)
        print("Done!")
    except subprocess.TimeoutExpired:
        print("Done! (timeout)")
    except KeyboardInterrupt:
        print("\n   Stopped.")
        time.sleep(0.5)
    except FileNotFoundError:
        # Fallback: try using afrecord or suggest installation
        print("\n⚠️  'sox' not found. Trying macOS native recording...")
        return record_audio_native(filepath, duration)

    if os.path.exists(filepath):
        return filepath
    return ""


def record_audio_native(filepath: str, duration: int = None) -> str:
    """Fallback: Record using macOS afrecord (if available) or ffmpeg."""
    # Try ffmpeg as fallback
    if duration:
        cmd = ["ffmpeg", "-y", "-f", "avfoundation", "-i", ":0", "-t", str(duration),
               "-ar", "16000", "-ac", "1", filepath]
    else:
        cmd = ["ffmpeg", "-y", "-f", "avfoundation", "-i", ":0",
               "-ar", "16000", "-ac", "1", filepath]

    try:
        print(f"🎙️  Recording with ffmpeg {'for ' + str(duration) + 's' if duration else '(Ctrl+C to stop)'}...")
        proc = subprocess.run(cmd, capture_output=True, timeout=duration + 5 if duration else 3600)
        print("Done!")
    except subprocess.TimeoutExpired:
        print("Done!")
    except KeyboardInterrupt:
        print("\n   Stopped.")
        time.sleep(0.5)
    except FileNotFoundError:
        print("\n❌ Neither 'sox' nor 'ffmpeg' found. Install one:")
        print("   brew install sox")
        print("   brew install ffmpeg")
        return ""

    if os.path.exists(filepath):
        return filepath
    return ""


def transcribe_audio(filepath: str) -> str:
    """Transcribe audio using Whisper via Ollama or local whisper."""
    if not os.path.exists(filepath):
        return "[Error: Audio file not found]"

    # Try using local whisper (python whisper package)
    try:
        import whisper
        print("🔊 Transcribing with Whisper...")
        model = whisper.load_model("base")
        result = model.transcribe(filepath)
        return result["text"].strip()
    except ImportError:
        pass

    # Fallback: Use Ollama to acknowledge we can't transcribe without whisper
    print("⚠️  Whisper not available. Install with: pip install openai-whisper")
    print("   Generating placeholder transcription using file metadata...")

    duration = get_audio_duration(filepath)
    return f"[Audio recording - {duration:.1f}s - requires whisper for transcription. Install: pip install openai-whisper]"


def classify_message(transcription: str) -> dict:
    """Use AI to classify a transcribed message."""
    prompt = f"""Analyze this transcribed phone message and classify it.
Return ONLY valid JSON with these keys:
- urgency: "low", "normal", "high", or "urgent"
- is_spam: true or false
- action_needed: brief description of required action, or empty string
- summary: one-sentence summary
- classification: category like "business", "personal", "spam", "medical", "delivery", etc.

Message: "{transcription}"

Return ONLY the JSON object:"""

    result = call_ollama(prompt, temperature=0.1)
    try:
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(result)
    except json.JSONDecodeError:
        return {
            "urgency": "normal",
            "is_spam": False,
            "action_needed": "",
            "summary": transcription[:100],
            "classification": "unknown"
        }


def cmd_listen(duration: int = 10):
    """Record audio from Mac microphone."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recording_{timestamp}.wav"
    filepath = record_audio(filename, duration=duration)

    if filepath:
        audio_duration = get_audio_duration(filepath)
        call_id = call_log.add_call(filepath, audio_duration, call_type="recording")
        print(f"\n✅ Saved: {filepath}")
        print(f"   Duration: {audio_duration:.1f}s | ID: {call_id}")
        print(f"   Next: ./phone_assistant.py --transcribe {filepath}")
    else:
        print("\n❌ Recording failed.")


def cmd_transcribe(filepath: str):
    """Transcribe an audio file."""
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    transcription = transcribe_audio(filepath)
    print(f"\n📝 Transcription:\n{'─' * 40}")
    print(transcription)
    print(f"{'─' * 40}\n")

    # Update DB if this file is tracked
    conn = call_log._get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM calls WHERE audio_file = ?", (filepath,))
    row = c.fetchone()
    conn.close()

    if row:
        call_log.update_transcription(row['id'], transcription)
        print(f"   Updated call record #{row['id']}")
    else:
        call_id = call_log.add_call(filepath, get_audio_duration(filepath), call_type="transcribed")
        call_log.update_transcription(call_id, transcription)
        print(f"   Saved as call record #{call_id}")

    return transcription


def cmd_respond(filepath: str = None, text: str = None):
    """Generate AI response to transcription."""
    if filepath:
        # Get transcription from DB or transcribe
        conn = call_log._get_conn()
        c = conn.cursor()
        c.execute("SELECT transcription FROM calls WHERE audio_file = ?", (filepath,))
        row = c.fetchone()
        conn.close()

        if row and row['transcription']:
            text = row['transcription']
        else:
            text = cmd_transcribe(filepath)

    if not text:
        print("❌ No text to respond to. Provide --filepath or pipe text.")
        return

    system = """You are a helpful phone assistant. Generate a polite, professional response 
to the caller's message. Be concise and address their main points."""

    response = call_ollama(text, system=system, temperature=0.5)
    print(f"\n🤖 Suggested Response:\n{'─' * 40}")
    print(response)
    print(f"{'─' * 40}\n")


def cmd_voicemail(duration: int = 30):
    """Full voicemail mode: Record → Transcribe → Summarize → Notify."""
    print("\n📞 VOICEMAIL MODE")
    print("=" * 40)

    # Step 1: Record
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"voicemail_{timestamp}.wav"
    filepath = record_audio(filename, duration=duration)

    if not filepath:
        print("❌ Recording failed.")
        return

    audio_duration = get_audio_duration(filepath)
    call_id = call_log.add_call(filepath, audio_duration, call_type="voicemail")
    print(f"   ✅ Recorded ({audio_duration:.1f}s)")

    # Step 2: Transcribe
    print("   📝 Transcribing...")
    transcription = transcribe_audio(filepath)
    call_log.update_transcription(call_id, transcription)
    print(f"   ✅ Transcribed")

    # Step 3: Classify
    print("   🏷️  Classifying...")
    classification = classify_message(transcription)
    call_log.update_classification(
        call_id,
        urgency=classification.get("urgency", "normal"),
        is_spam=classification.get("is_spam", False),
        action_needed=classification.get("action_needed", ""),
        summary=classification.get("summary", ""),
        classification=classification.get("classification", "unknown")
    )
    print(f"   ✅ Classified: {classification.get('classification', 'unknown')} | Urgency: {classification.get('urgency', 'normal')}")

    # Step 4: Notify
    urgency = classification.get("urgency", "normal")
    summary = classification.get("summary", transcription[:50])

    if urgency in ("urgent", "high"):
        send_mac_notification("⚠️ Urgent Voicemail", summary, sound="Basso")
        print(f"   🔔 Urgent notification sent!")
    elif not classification.get("is_spam", False):
        send_mac_notification("📞 New Voicemail", summary)
        print(f"   🔔 Notification sent")

    call_log.add_notification(call_id, summary, notif_type=urgency)

    # Summary
    print(f"\n{'─' * 40}")
    print(f"📋 Summary: {summary}")
    if classification.get("action_needed"):
        print(f"⚡ Action: {classification['action_needed']}")
    print(f"{'─' * 40}\n")


def cmd_meeting_recorder(title: str = None):
    """Record a meeting/call live with real-time transcription."""
    print("\n🎤 MEETING RECORDER")
    print("=" * 40)
    print("Recording in 30-second chunks. Press Ctrl+C to stop.\n")

    meeting_title = title or f"Meeting {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    meeting_id = call_log.start_meeting(meeting_title)
    chunk_index = 0
    start_time = time.time()
    all_transcriptions = []

    try:
        while True:
            chunk_file = f"meeting_{meeting_id}_chunk_{chunk_index:03d}.wav"
            print(f"   📍 Chunk {chunk_index + 1}...", end=" ", flush=True)

            filepath = record_audio(chunk_file, duration=30)
            if not filepath:
                continue

            # Transcribe chunk
            transcription = transcribe_audio(filepath)
            if transcription and not transcription.startswith("["):
                all_transcriptions.append(transcription)
                print(f"→ {transcription[:60]}...")

                # Generate real-time notes for this chunk
                notes_prompt = f"Generate brief meeting notes for this segment: \"{transcription}\"\nReturn 1-2 bullet points only."
                notes = call_ollama(notes_prompt, temperature=0.2)

                call_log.add_meeting_chunk(meeting_id, chunk_index, transcription, notes, filepath)
            else:
                print(f"→ [silence/unclear]")
                call_log.add_meeting_chunk(meeting_id, chunk_index, transcription or "", None, filepath)

            chunk_index += 1

    except KeyboardInterrupt:
        print("\n\n   ⏹️  Stopping recording...")

    # Generate meeting summary
    duration = time.time() - start_time
    full_text = "\n".join(all_transcriptions)

    if full_text:
        print("   📊 Generating summary...")
        summary_prompt = f"""Summarize this meeting transcription. Include:
1. Key topics discussed
2. Decisions made
3. Action items

Transcription:
{full_text[:3000]}"""
        summary = call_ollama(summary_prompt, temperature=0.3)

        action_prompt = f"Extract action items from this meeting as a bullet list:\n{full_text[:2000]}"
        action_items = call_ollama(action_prompt, temperature=0.2)
    else:
        summary = "No clear audio captured."
        action_items = ""

    call_log.end_meeting(meeting_id, summary, action_items, duration)

    print(f"\n{'═' * 40}")
    print(f"📋 Meeting: {meeting_title}")
    print(f"⏱️  Duration: {duration / 60:.1f} minutes | Chunks: {chunk_index}")
    print(f"\n📊 Summary:\n{summary}")
    if action_items:
        print(f"\n✅ Action Items:\n{action_items}")
    print(f"{'═' * 40}\n")


def cmd_playback(filepath: str):
    """Play back a recorded message with AI summary."""
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    # Get record from DB
    conn = call_log._get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM calls WHERE audio_file = ?", (filepath,))
    row = c.fetchone()
    conn.close()

    print(f"\n🔊 Playing: {filepath}")
    print(f"{'─' * 40}")

    if row:
        record = dict(row)
        if record.get("summary"):
            print(f"📋 Summary: {record['summary']}")
        if record.get("urgency"):
            print(f"🏷️  Urgency: {record['urgency']}")
        if record.get("transcription"):
            print(f"\n📝 Transcription:\n{record['transcription']}")

    # Try to play audio
    try:
        subprocess.run(["afplay", filepath], timeout=120)
        print("\n✅ Playback complete.")
    except subprocess.TimeoutExpired:
        print("\n⏹️  Playback stopped (timeout).")
    except FileNotFoundError:
        print("\n⚠️  Cannot play audio (afplay not found).")
    except KeyboardInterrupt:
        print("\n⏹️  Playback stopped.")

    print(f"{'─' * 40}\n")


def cmd_history():
    """Show all recorded calls/messages."""
    history = call_log.get_history(limit=30)
    stats = call_log.get_stats()

    print(f"\n📞 CALL HISTORY ({stats['total_calls']} total)")
    print(f"   Urgent: {stats['urgent']} | Spam: {stats['spam']} | Unread: {stats['unread']} | Meetings: {stats['meetings']}")
    print("═" * 60)

    if not history:
        print("   No recordings yet. Use --listen or --voicemail to start.")
        print("═" * 60 + "\n")
        return

    for call in history:
        urgency_icon = {"urgent": "🔴", "high": "🟠", "normal": "🟢", "low": "⚪"}.get(call["urgency"], "⚪")
        spam_tag = " [SPAM]" if call["is_spam"] else ""
        ts = call["recorded_at"][:16] if call["recorded_at"] else "?"
        summary = call.get("summary") or call.get("transcription", "")
        summary = summary[:60] + "..." if len(summary) > 60 else summary

        print(f"\n   {urgency_icon} #{call['id']} | {ts} | {call['type']}{spam_tag}")
        print(f"      {summary or '[No transcription yet]'}")
        if call.get("action_needed"):
            print(f"      ⚡ Action: {call['action_needed']}")

    print("\n" + "═" * 60 + "\n")


def cmd_filter(filter_type: str):
    """Filter messages by category."""
    results = call_log.filter_calls(filter_type)

    print(f"\n🔍 Filtered: {filter_type.upper()} ({len(results)} results)")
    print("─" * 50)

    if not results:
        print(f"   No {filter_type} messages found.")
    else:
        for call in results:
            ts = call["recorded_at"][:16] if call["recorded_at"] else "?"
            summary = call.get("summary") or call.get("transcription", "")[:60] or "[no content]"
            print(f"   #{call['id']} | {ts} | {summary}")

    print("─" * 50 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="📞 AI Phone Call Assistant - Record, transcribe, and manage calls",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --listen                  Record from microphone (10s default)
  %(prog)s --listen --duration 30    Record for 30 seconds
  %(prog)s --transcribe rec.wav      Transcribe an audio file
  %(prog)s --respond rec.wav         Generate AI response
  %(prog)s --voicemail               Full voicemail pipeline
  %(prog)s --meeting-recorder        Record a live meeting
  %(prog)s --playback rec.wav        Play with AI summary
  %(prog)s --history                 Show all recordings
  %(prog)s --filter urgent           Show urgent messages only
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--listen", action="store_true", help="Record audio from Mac mic")
    group.add_argument("--transcribe", type=str, metavar="FILE", help="Transcribe audio file")
    group.add_argument("--respond", type=str, metavar="FILE", help="Generate AI response to transcription")
    group.add_argument("--voicemail", action="store_true", help="Full voicemail mode")
    group.add_argument("--meeting-recorder", action="store_true", help="Record meeting live")
    group.add_argument("--playback", type=str, metavar="FILE", help="Play back recording with summary")
    group.add_argument("--history", action="store_true", help="Show all recorded calls")
    group.add_argument("--filter", type=str, choices=["urgent", "missed", "spam", "action"],
                       help="Filter messages by category")

    parser.add_argument("--duration", type=int, default=10, help="Recording duration in seconds (default: 10)")
    parser.add_argument("--title", type=str, help="Meeting title (for --meeting-recorder)")

    args = parser.parse_args()

    if args.listen:
        cmd_listen(args.duration)
    elif args.transcribe:
        cmd_transcribe(args.transcribe)
    elif args.respond:
        cmd_respond(filepath=args.respond)
    elif args.voicemail:
        cmd_voicemail(args.duration)
    elif args.meeting_recorder:
        cmd_meeting_recorder(args.title)
    elif args.playback:
        cmd_playback(args.playback)
    elif args.history:
        cmd_history()
    elif args.filter:
        cmd_filter(args.filter)


if __name__ == "__main__":
    main()
