# 🎬 AI Shorts Factory

Generate YouTube Shorts scripts for 9 channels using local AI (Ollama + llama3.2).

## Channels

| Channel | Niche | Language | Frequency |
|---------|-------|----------|-----------|
| Gyaan in 5 | Knowledge/Education | Hindi | 2/day |
| Tech in 5 Hindi | Tech News | Hindi | 2/day |
| Money in 5 | Finance | Hindi | 2/day |
| Superhuman 60s | Productivity | Hinglish | 2/day |
| Horror Ki Kahani | Horror Stories | Hindi | 1/day |
| Pyaar Ka Psychology | Relationships | Hindi | 2/day |
| Zeheela Sach | Dark Facts | Hindi | 1/day |
| Apna Haq | Legal Rights | Hindi | 1/day |
| Agar Aisa Ho Toh | Hypothetical | Hindi | 1/day |

## Quick Start

```bash
# Generate for one channel
./shorts_factory.py --channel gyaan_in_5

# Generate for all channels (1 each)
./shorts_factory.py --all

# Full daily batch (respects posting frequency)
./shorts_factory.py --batch-daily

# Or use the batch script
./batch_generate.sh
```

## Usage

```bash
# Specific topic and style
./shorts_factory.py --channel tech_in_5_hindi --style shocking --topic "AI replacing jobs"

# Multiple shorts per channel
./shorts_factory.py --channel money_in_5 --count 3

# Different output formats
./shorts_factory.py --all --format json
./shorts_factory.py --channel horror_ki_kahani --format srt

# Specify language
./shorts_factory.py --all --language hinglish

# List available channels
./shorts_factory.py --list-channels
```

## Script Styles

- `hook_fact` - Mind-blowing fact opener → supporting facts
- `storytelling` - Mini-story with setup, tension, payoff
- `listicle` - Numbered list (3-5 punchy points)
- `question` - Provocative question → curiosity → answer
- `shocking` - Unbelievable claim → proof/evidence

## Output Structure

Each generated short includes:
- **Hook** (0-3s): Scroll-stopping opener
- **Body** (3-48s): Key points with timestamps
- **CTA** (48-58s): Subscribe/like prompt
- **On-screen text**: Line-by-line overlays for editing
- **Music mood**: Background audio suggestion
- **Hashtags**: 5-7 relevant tags

## Output Formats

- `script` (.txt) - Human-readable format for voiceover recording
- `srt` (.srt) - Subtitle file for video editing
- `json` (.json) - Structured data for automation pipelines

## File Structure

```
output/
├── gyaan_in_5/
│   └── 2026-07-11/
│       ├── short_hook_fact_091523.txt
│       └── short_listicle_091545.json
├── tech_in_5_hindi/
│   └── ...
└── ...
```

## Configuration

- `channels_config.json` - Channel definitions, tones, sample hooks
- `hooks_library.json` - 105 proven hook templates with engagement scores

## Requirements

- Python 3.9+
- Ollama running locally (`ollama serve`)
- llama3.2 model (`ollama pull llama3.2`)
- `requests` package (in venv)

## Automation

Add to crontab for daily generation:
```bash
# Generate shorts daily at 6 AM
0 6 * * * /Users/amrendranarayanmishra/Downloads/AI/projects/31-shorts-factory/batch_generate.sh
```
