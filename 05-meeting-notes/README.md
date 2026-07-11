# AI Meeting Notes

Generate structured meeting notes from transcripts using local AI (Ollama).

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai) running locally on port 11434
- A model pulled (default: `llama3.2`)

```bash
ollama pull llama3.2
ollama serve  # if not already running
```

## Scripts

### meeting_notes.py - Generate Meeting Notes

Processes meeting transcripts and generates structured notes with:
- Summary (3-5 sentences)
- Key decisions
- Action items with assignees
- Follow-up questions
- Next steps

#### Usage

```bash
# From a file
./meeting_notes.py --file transcript.txt

# From clipboard
./meeting_notes.py --paste

# Audio recording (placeholder)
./meeting_notes.py --record

# With specific template and format
./meeting_notes.py --file notes.txt --template standup --format json

# Interactive refinement mode
./meeting_notes.py --file notes.txt --interactive

# Don't save to disk
./meeting_notes.py --file notes.txt --no-save

# Use a different model
./meeting_notes.py --file notes.txt --model mistral
```

#### Options

| Option | Description |
|--------|-------------|
| `--file`, `-f` | Path to transcript file |
| `--paste`, `-p` | Read from clipboard (pbpaste/xclip) |
| `--record`, `-r` | Audio recording (placeholder) |
| `--format` | Output format: `markdown`, `json`, `text` (default: markdown) |
| `--template`, `-t` | Meeting type: `general`, `standup`, `planning`, `retro`, `1on1` |
| `--interactive`, `-i` | Enable interactive refinement after generation |
| `--no-save` | Don't save output file |
| `--model`, `-m` | Ollama model to use (default: llama3.2) |

#### Interactive Mode Commands

When using `--interactive`:
- `refine <section>` - Ask AI to improve a section
- `add <section> <text>` - Manually add text to a section
- `show` - Display current notes
- `done` - Accept and save

Sections: `summary`, `decisions`, `actions`, `questions`, `next_steps`

### meeting_tracker.py - Track & Search Notes

Manages all saved meeting notes.

#### Usage

```bash
# List all meeting notes
./meeting_tracker.py list

# Search across notes
./meeting_tracker.py search "deployment"

# Show pending action items
./meeting_tracker.py actions

# Generate weekly summary
./meeting_tracker.py weekly

# View a specific note (by number from list)
./meeting_tracker.py show 3
```

#### Commands

| Command | Description |
|---------|-------------|
| `list` | List all saved meeting notes with metadata |
| `search <query>` | Full-text search across all notes |
| `actions` | Show pending action items from all meetings |
| `weekly` | AI-generated weekly summary of recent meetings |
| `show <n>` | Display content of note #n |

## Templates

Meeting templates are in the `templates/` directory:

| Template | Use Case |
|----------|----------|
| `standup.md` | Daily standups (yesterday, today, blockers) |
| `planning.md` | Sprint/project planning sessions |
| `retro.md` | Retrospectives (went well, didn't, improve) |
| `1on1.md` | One-on-one meetings (growth, feedback, goals) |

## Output

Notes are saved to `~/Documents/meeting-notes/` with filenames like:
```
meeting_standup_20260710_143022.md
meeting_planning_20260710_150000.json
meeting_retro_20260710_160000.txt
```

## Examples

### Quick standup notes from clipboard
```bash
# Copy your standup notes, then:
./meeting_notes.py --paste --template standup
```

### Process a long meeting transcript
```bash
./meeting_notes.py --file ~/Downloads/meeting-recording.txt --template planning --interactive
```

### Weekly review workflow
```bash
# Check what happened this week
./meeting_tracker.py weekly

# Find unfinished action items
./meeting_tracker.py actions

# Search for a specific topic
./meeting_tracker.py search "database migration"
```

## Configuration

- **Ollama URL:** `http://localhost:11434` (hardcoded, edit scripts to change)
- **Default Model:** `llama3.2` (override with `--model`)
- **Notes Directory:** `~/Documents/meeting-notes/`
