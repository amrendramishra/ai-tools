# 🤖 Family Chat Bot — Telegram + WhatsApp Ready

A friendly, family-appropriate AI chatbot that works on Telegram (primary) with WhatsApp migration path. Responds in Hinglish (Hindi + English mix).

## Features

- **AI-powered responses** via local Ollama
- **Hindi/English bilingual** — natural Hinglish personality
- **Family-friendly** — appropriate for all ages
- **Rate limiting** — prevents spam (10 msgs/min/user)
- **Interaction logging** — SQLite database tracks all conversations
- **Pre-canned responses** — instant jokes, quotes, festival info
- **Multi-platform ready** — Telegram now, WhatsApp later

## Commands

| Command | Description |
|---------|-------------|
| `/ask <question>` | General AI answer |
| `/recipe <dish>` | Recipe in Hindi |
| `/health <topic>` | Health tips (with disclaimer) |
| `/news` | Top news summary |
| `/joke` | Hindi joke |
| `/motivate` | Motivational quote |
| `/translate <text>` | Hindi↔English translation |
| `/astro <sign>` | Fun daily horoscope |
| `/festival` | Upcoming Indian festivals |
| `/remind <text>` | Set a reminder |
| `/help` | Show all commands |

## Setup — Telegram

### 1. Create Bot
1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Choose name: "Family Bot" (or anything)
4. Choose username: `your_family_bot` (must end in `bot`)
5. Copy the token

### 2. Configure
```bash
cp .env.example .env
# Edit .env and paste your TELEGRAM_BOT_TOKEN
```

Or export directly:
```bash
export TELEGRAM_BOT_TOKEN="your_token_here"
```

### 3. Run
```bash
# Telegram mode (production)
./family_bot.py --telegram

# CLI mode (testing without Telegram)
./family_bot.py --cli

# Test all commands
./family_bot.py --test
```

### 4. Add to Family Group
1. Open your family WhatsApp/Telegram group
2. Add the bot by username
3. Make it admin (so it can read messages)
4. Everyone can use `/commands`!

## Usage Modes

### Telegram Bot (Primary)
```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
./family_bot.py --telegram
```

### CLI Testing
```bash
./family_bot.py --cli
# Then type: /joke, /ask what is AI, /recipe biryani
```

### Self-Test
```bash
./family_bot.py --test
```

## WhatsApp Migration Guide

### Option 1: WhatsApp Business API (Official)
1. Apply for WhatsApp Business API access
2. Set up a Meta Developer account
3. Configure webhook URL pointing to this bot
4. Modify `family_bot.py` to handle WhatsApp webhook format
5. Messages come as HTTP POST to your server

### Option 2: Twilio WhatsApp (Easier)
1. Create Twilio account
2. Enable WhatsApp Sandbox
3. Set webhook to your server
4. Format: incoming messages → process_command() → reply

### Option 3: WhatsApp Web Automation (Unofficial)
- Libraries like `whatsapp-web.js` (Node) or `pywhatkit` (Python)
- ⚠️ Against WhatsApp ToS, may get banned
- Only for personal/experimental use

### Webhook Server (for WhatsApp)
The bot includes a `--webhook PORT` option (future) that will:
1. Run Flask/FastAPI server on specified port
2. Accept POST requests from WhatsApp/Twilio
3. Process commands and return responses
4. Can be deployed behind ngrok for testing

## Architecture

```
family_bot.py
├── Command Handlers (handle_ask, handle_recipe, etc.)
├── Telegram Polling (long-poll for messages)
├── Rate Limiter (per-user, 10/min)
├── Interaction Logger (SQLite)
└── Ollama Integration (local AI)
```

## Requirements

- Python 3.8+
- Ollama running locally
- Telegram Bot Token (free from @BotFather)
- Internet connection (for Telegram API)

## Files

- `family_bot.py` — Main bot executable
- `responses.json` — Pre-canned jokes, quotes, festivals
- `.env.example` — Configuration template
- `bot_data.db` — Interaction logs (auto-created)
- `bot.log` — Activity log (auto-created)
