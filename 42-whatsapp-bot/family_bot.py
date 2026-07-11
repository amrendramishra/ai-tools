#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""Family Chat Bot — Multi-platform AI bot (Telegram primary, WhatsApp-ready)."""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / "bot_data.db"
RESPONSES_FILE = SCRIPT_DIR / "responses.json"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Rate limiting
RATE_LIMIT = 10  # messages per minute per user
rate_tracker = defaultdict(list)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(SCRIPT_DIR / "bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def init_db():
    """Initialize bot database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id TEXT,
            username TEXT,
            command TEXT,
            message TEXT,
            response TEXT,
            platform TEXT DEFAULT 'telegram'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            remind_at TEXT,
            user_id TEXT,
            text TEXT,
            delivered INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def load_responses():
    """Load pre-canned responses."""
    with open(RESPONSES_FILE) as f:
        return json.load(f)


def ask_ollama(prompt, model="llama3.2"):
    """Query Ollama for AI responses."""
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 800}
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response", "").strip()
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return "Sorry, AI is taking a nap 😴 Try again in a moment!"


def check_rate_limit(user_id):
    """Check if user has exceeded rate limit."""
    now = time.time()
    # Clean old entries
    rate_tracker[user_id] = [t for t in rate_tracker[user_id] if now - t < 60]
    if len(rate_tracker[user_id]) >= RATE_LIMIT:
        return False
    rate_tracker[user_id].append(now)
    return True


def log_interaction(conn, user_id, username, command, message, response, platform="telegram"):
    """Log bot interaction."""
    c = conn.cursor()
    c.execute("""
        INSERT INTO interactions (timestamp, user_id, username, command, message, response, platform)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), user_id, username, command, message, response, platform))
    conn.commit()


# ─── Command Handlers ───────────────────────────────────────────────

def handle_ask(query):
    """General AI question answering."""
    prompt = f"""You are a friendly family group chatbot. Answer in a mix of Hindi and English (Hinglish).
Keep answers concise (2-4 sentences), family-friendly, and helpful.
Question: {query}"""
    return ask_ollama(prompt)


def handle_recipe(dish):
    """Get recipe in Hindi."""
    prompt = f"""Give a recipe for "{dish}" in Hindi (with English food terms where needed).
Format:
🍳 {dish}
सामग्री (Ingredients): bullet list
विधि (Method): numbered steps (keep brief, 5-7 steps)
💡 Tip: one pro tip

Keep it concise and practical for a family cook."""
    return ask_ollama(prompt)


def handle_health(query):
    """Health tips with disclaimer."""
    prompt = f"""Give brief health tips about: {query}
Respond in Hinglish (Hindi + English mix).
Include 3-4 practical tips.
Keep it general wellness advice.
End with: "⚠️ Note: Yeh general tips hain, serious issues ke liye doctor se zaroor milein." """
    return ask_ollama(prompt)


def handle_news():
    """Daily news summary."""
    prompt = """Generate a brief summary of typical daily news topics (5 items) in Hinglish format.
Since you don't have live news, provide a template that shows what kind of news summaries the bot would share.
Format each as: 📰 HEADLINE - brief summary
Include mix of: India news, tech, sports, entertainment, world."""
    return ask_ollama(prompt)


def handle_joke():
    """Tell a Hindi joke."""
    responses_data = load_responses()
    jokes = responses_data.get("jokes", [])

    # Mix of pre-canned and AI
    import random
    if jokes and random.random() < 0.5:
        return random.choice(jokes)

    prompt = """Tell a clean, family-friendly joke in Hindi/Hinglish. 
It should be funny for all ages. Format:
😂 [Joke]
Keep it short (2-4 lines)."""
    return ask_ollama(prompt)


def handle_motivate():
    """Daily motivational quote."""
    responses_data = load_responses()
    quotes = responses_data.get("motivational_quotes", [])

    import random
    if quotes and random.random() < 0.4:
        return random.choice(quotes)

    prompt = """Give an inspiring motivational quote or thought in Hinglish.
Include the source/author if it's a known quote.
Format: 🌟 [Quote] — [Author/Source]
Then add 1 line of your own encouragement in Hinglish."""
    return ask_ollama(prompt)


def handle_translate(text):
    """Hindi↔English translation."""
    prompt = f"""Translate the following text. If it's in Hindi, translate to English. If in English, translate to Hindi.
Text: "{text}"
Format:
🔄 Original: [original]
✅ Translation: [translation]
If there are multiple meanings, mention the most common one."""
    return ask_ollama(prompt)


def handle_astro(sign):
    """Fun daily horoscope."""
    prompt = f"""Give a fun, positive daily horoscope for {sign} in Hinglish.
Keep it lighthearted and family-friendly. Include:
⭐ Aaj ka din: (brief prediction)
💰 Career/Money: (one line)
❤️ Relationships: (one line)
🍀 Lucky: (color/number)
Keep it fun and positive - this is entertainment, not real astrology!"""
    return ask_ollama(prompt)


def handle_festival():
    """Upcoming Indian festivals."""
    responses_data = load_responses()
    festivals = responses_data.get("festivals", [])

    now = datetime.now()
    upcoming = []
    for f in festivals:
        try:
            fest_date = datetime.strptime(f["date"], "%Y-%m-%d")
            if fest_date >= now:
                days_left = (fest_date - now).days
                upcoming.append(f"🎉 {f['name']} — {f['date']} ({days_left} days left)\n   {f.get('description', '')}")
        except ValueError:
            continue

    if upcoming:
        return "📅 Upcoming Festivals:\n\n" + "\n\n".join(upcoming[:5])

    # Fallback to AI
    prompt = f"""List 5 upcoming Indian festivals from today ({now.strftime('%B %Y')}).
Format each as:
🎉 FESTIVAL NAME — approximate date
   Brief description in Hinglish
Include major Hindu, Muslim, Sikh, and national festivals."""
    return ask_ollama(prompt)


def handle_remind(text, user_id, conn):
    """Set a reminder."""
    c = conn.cursor()
    c.execute("""
        INSERT INTO reminders (created_at, user_id, text)
        VALUES (?, ?, ?)
    """, (datetime.now().isoformat(), user_id, text))
    conn.commit()
    return f"⏰ Reminder set: \"{text}\"\n(Note: Reminders are stored. In Telegram mode, you'll get notified!)"


def process_command(message, user_id="local", username="user", conn=None):
    """Process a bot command and return response."""
    if not message.startswith('/'):
        return None

    parts = message.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    # Remove bot mention if present
    if '@' in command:
        command = command.split('@')[0]

    response = ""

    if command == "/ask":
        if not args:
            response = "❓ Kya puchna hai? Usage: /ask <your question>"
        else:
            response = handle_ask(args)
    elif command == "/recipe":
        if not args:
            response = "🍳 Kya banana hai? Usage: /recipe <dish name>"
        else:
            response = handle_recipe(args)
    elif command == "/health":
        if not args:
            response = "🏥 Health ke baare mein kya jaanna hai? Usage: /health <topic>"
        else:
            response = handle_health(args)
    elif command == "/news":
        response = handle_news()
    elif command == "/joke":
        response = handle_joke()
    elif command == "/motivate":
        response = handle_motivate()
    elif command == "/translate":
        if not args:
            response = "🔄 Kya translate karna hai? Usage: /translate <text>"
        else:
            response = handle_translate(args)
    elif command == "/astro":
        if not args:
            response = "⭐ Apni rashi batao! Usage: /astro <sign>\nSigns: aries, taurus, gemini, cancer, leo, virgo, libra, scorpio, sagittarius, capricorn, aquarius, pisces"
        else:
            response = handle_astro(args)
    elif command == "/festival":
        response = handle_festival()
    elif command == "/remind":
        if not args:
            response = "⏰ Kya yaad dilana hai? Usage: /remind <text>"
        else:
            response = handle_remind(args, user_id, conn)
    elif command == "/help" or command == "/start":
        response = """🤖 Family Bot Commands:

/ask <question> — AI se kuch bhi puchho
/recipe <dish> — Recipe in Hindi
/health <topic> — Health tips
/news — Aaj ki headlines
/joke — Hindi joke sunao
/motivate — Motivation dose
/translate <text> — Hindi↔English
/astro <sign> — Fun horoscope
/festival — Upcoming festivals
/remind <text> — Reminder set karo

Made with ❤️ for family!"""
    else:
        response = f"🤔 '{command}' command nahi samjha. /help type karo for commands!"

    return response


# ─── Telegram Bot Mode ──────────────────────────────────────────────

def run_telegram_bot(conn):
    """Run as Telegram bot using polling."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set! Set it in .env or environment.")
        print("❌ Set TELEGRAM_BOT_TOKEN environment variable first.")
        print("   Get token from @BotFather on Telegram.")
        sys.exit(1)

    logger.info("Starting Telegram bot...")

    base_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    offset = 0

    # Get bot info
    try:
        req = urllib.request.Request(f"{base_url}/getMe")
        with urllib.request.urlopen(req) as resp:
            bot_info = json.loads(resp.read().decode())
            if bot_info.get("ok"):
                bot_name = bot_info["result"].get("username", "unknown")
                logger.info(f"Bot connected: @{bot_name}")
                print(f"✅ Bot connected: @{bot_name}")
            else:
                logger.error("Failed to connect to Telegram")
                sys.exit(1)
    except Exception as e:
        logger.error(f"Telegram connection failed: {e}")
        print(f"❌ Failed to connect: {e}")
        sys.exit(1)

    print("🤖 Bot is running! Press Ctrl+C to stop.\n")

    while True:
        try:
            # Get updates
            url = f"{base_url}/getUpdates?offset={offset}&timeout=30"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=35) as resp:
                updates = json.loads(resp.read().decode())

            if not updates.get("ok"):
                continue

            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message", {})
                text = message.get("text", "")
                user = message.get("from", {})
                chat_id = message.get("chat", {}).get("id")
                user_id = str(user.get("id", ""))
                username = user.get("first_name", "User")

                if not text or not chat_id:
                    continue

                # Rate limiting
                if not check_rate_limit(user_id):
                    response = "⏳ Thoda slow karo! Rate limit hit. 1 minute mein try karo."
                else:
                    response = process_command(text, user_id, username, conn)

                if response:
                    # Send response
                    send_payload = json.dumps({
                        "chat_id": chat_id,
                        "text": response,
                        "parse_mode": "Markdown"
                    }).encode()

                    send_req = urllib.request.Request(
                        f"{base_url}/sendMessage",
                        data=send_payload,
                        headers={"Content-Type": "application/json"}
                    )
                    try:
                        urllib.request.urlopen(send_req)
                    except Exception:
                        # Retry without markdown
                        send_payload = json.dumps({
                            "chat_id": chat_id,
                            "text": response
                        }).encode()
                        send_req = urllib.request.Request(
                            f"{base_url}/sendMessage",
                            data=send_payload,
                            headers={"Content-Type": "application/json"}
                        )
                        urllib.request.urlopen(send_req)

                    # Log interaction
                    log_interaction(conn, user_id, username, text.split()[0], text, response[:200])
                    logger.info(f"[{username}] {text[:50]} → responded")

            time.sleep(0.5)

        except KeyboardInterrupt:
            print("\n👋 Bot stopped.")
            break
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)


# ─── CLI Interactive Mode ───────────────────────────────────────────

def run_cli_mode(conn):
    """Run in CLI interactive mode for testing."""
    print("🤖 Family Bot — CLI Mode (for testing)")
    print("═" * 50)
    print("Type commands like /joke, /ask what is AI, /recipe dal")
    print("Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 Bye!")
                break
            if not user_input:
                continue

            response = process_command(user_input, "cli_user", "TestUser", conn)
            if response:
                print(f"\n🤖 Bot: {response}\n")
            else:
                # Treat as general question
                response = handle_ask(user_input)
                print(f"\n🤖 Bot: {response}\n")

            log_interaction(conn, "cli_user", "TestUser", user_input.split()[0], user_input, response[:200] if response else "", "cli")

        except (EOFError, KeyboardInterrupt):
            print("\n👋 Bye!")
            break


def main():
    parser = argparse.ArgumentParser(
        description="🤖 Family Chat Bot — Telegram + WhatsApp Ready",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  family_bot.py --telegram    Run as Telegram bot
  family_bot.py --cli         Interactive CLI testing mode
  family_bot.py --test        Run self-test of all commands
        """
    )

    parser.add_argument("--telegram", action="store_true", help="Run as Telegram bot")
    parser.add_argument("--cli", action="store_true", help="Interactive CLI mode")
    parser.add_argument("--test", action="store_true", help="Test all commands")
    parser.add_argument("--webhook", type=int, metavar="PORT", help="Run webhook server on port")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        print("\n🤖 Quick start: --cli for testing, --telegram for live bot")
        return

    conn = init_db()

    try:
        if args.telegram:
            run_telegram_bot(conn)
        elif args.cli:
            run_cli_mode(conn)
        elif args.test:
            print("🧪 Testing all commands...\n")
            test_commands = [
                "/help",
                "/joke",
                "/motivate",
                "/festival",
                "/astro leo",
                "/translate hello how are you",
            ]
            for cmd in test_commands:
                print(f"📨 {cmd}")
                response = process_command(cmd, "test", "Tester", conn)
                print(f"📬 {response[:100]}...\n")
                time.sleep(1)
            print("✅ All commands tested!")
        elif args.webhook:
            print(f"🌐 Webhook mode on port {args.webhook}")
            print("(Use with WhatsApp Business API or custom integrations)")
            print("Not implemented yet — use --telegram for now.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
