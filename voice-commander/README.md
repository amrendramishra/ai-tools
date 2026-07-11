# 🎤 Voice Commander - AI Control Center

Control ALL your 30+ AI tools with just your voice or a simple command.

## Quick Start

```bash
# Run it
vc

# Or with specific mode
vc --mode voice    # Voice only
vc --mode type     # Type only (no microphone needed)
vc --mode both     # Both (default)

# Single command (no interactive mode)
vc -c "generate content"
vc -c "research quantum computing"
vc -c "write email about meeting tomorrow"
vc -c "start focus 25"
```

## Available Voice Commands

| Say This | What Happens |
|----------|-------------|
| "generate content" | Runs content pipeline for all 9 YouTube channels |
| "video ideas" | Generates video ideas |
| "trending topics" | Finds trending topics for your niches |
| "research [topic]" | Deep research using Tavily API |
| "latest news" | Gets latest AI/tech news |
| "start focus" / "focus 25" | Starts Pomodoro timer |
| "organize files" | AI organizes your Downloads |
| "habit status" | Shows today's habits |
| "write email [topic]" | Drafts email, copies to clipboard |
| "write blog [topic]" | Generates full blog post |
| "summarize" | Summarizes clipboard content |
| "translate" | Translates clipboard to Hindi/English |
| "open web ui" | Opens local ChatGPT-like interface |
| "start n8n" | Opens workflow automation |
| "code review" | Reviews your latest git changes |
| "write code [description]" | Generates code, copies to clipboard |
| "find file [description]" | Natural language file search |
| "take note [text]" | Saves a quick note |
| "remind me [text]" | Sets a macOS notification |
| "newsletter" | Generates AI newsletter |
| "backup" | Backs up all GitHub repos |
| "github stats" | Shows your GitHub profile stats |
| "create repo [name]" | Creates a new GitHub repository |
| "status" | Shows system status |
| "stop" / "quit" | Exit Voice Commander |

## Modes

- **Voice mode**: Uses your Mac's microphone + Google Speech Recognition
- **Type mode**: Just type commands (works without microphone)
- **Both mode**: Type normally, or type 'v' to switch to voice

## Voice Tips

- Speak clearly and naturally
- Works with Indian English accent
- Supports Hindi words in commands
- If voice doesn't work, just type the same commands

## Run on Login (Optional)

Add to System Preferences → Login Items to auto-start.
