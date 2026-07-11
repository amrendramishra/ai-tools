# AI Content Pipeline

End-to-end YouTube content generator powered by Ollama. Generates SEO-optimized titles, descriptions, tags, and full scripts with channel-specific AI personas.

## Requirements

- Python 3.11+ (venv at `~/Downloads/AI/.venv`)
- Ollama running at `localhost:11434`
- Model: `llama3.2` (configurable with `--model`)

## Dependencies

```bash
source ~/Downloads/AI/.venv/bin/activate
pip install requests
```

## Usage

### Single Channel
```bash
# AI picks topic automatically
./content_pipeline.py --channel gyaan_in_5 --auto

# Specify topic
./content_pipeline.py --channel horror_ki_kahani --topic "haunted railway stations of India" --format long

# Custom language and format
./content_pipeline.py --channel money_in_5 --auto --language hinglish --format medium
```

### Batch Mode (All Channels)
```bash
# Generate content for ALL 9 channels
./content_pipeline.py --batch --auto

# Batch with specific format
./content_pipeline.py --batch --auto --format short
```

## Options

| Flag | Description |
|------|-------------|
| `--channel, -c` | Channel name or key |
| `--topic, -t` | Video topic |
| `--auto, -a` | AI picks trending topic |
| `--format, -f` | short (60s), medium (5min), long (10min+) |
| `--language, -l` | hindi, english, hinglish |
| `--batch, -b` | Generate for ALL channels |
| `--model, -m` | Ollama model (default: llama3.2) |

## Output Structure

```
output/
├── gyaan_in_5/
│   └── 2026-07-10/
│       ├── title.txt
│       ├── description.txt
│       ├── tags.json
│       ├── script.txt
│       └── content.json
├── horror_ki_kahani/
│   └── ...
└── ...
```

## Channels

| Channel | Niche | Language |
|---------|-------|----------|
| Gyaan in 5 | Knowledge/Education | Hinglish |
| Tech in 5 Hindi | Tech News | Hindi |
| Money in 5 | Finance/Money | Hinglish |
| Superhuman 60s | Productivity | English |
| Horror Ki Kahani | Horror Stories | Hindi |
| Pyaar Ka Psychology | Relationships | Hinglish |
| Zeheela Sach | Dark Facts | Hindi |
| Apna Haq | Legal Rights | Hindi |
| Agar Aisa Ho Toh | Hypothetical Scenarios | Hinglish |

## Channel Configuration

Edit `channels.json` to modify:
- AI persona (writing style)
- Tone and language
- Target audience
- Posting schedule
- Base tags
- Default format preference
