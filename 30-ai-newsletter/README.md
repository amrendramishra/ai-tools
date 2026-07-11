# AI Newsletter Generator 📬

AI-powered newsletter creation tool. Fetches content from RSS feeds, curates with AI, and generates polished newsletters using local LLMs via Ollama.

## Features

- **RSS Feed Parsing**: Fetch content from multiple RSS sources
- **AI Curation**: Automatically picks the most relevant/interesting items
- **Newsletter Generation**: Full newsletter writing with multiple templates
- **Multiple Formats**: Markdown, HTML, and plain text output
- **Templates**: Weekly digest, daily brief, deep dive, roundup
- **Audience Personalization**: Tailor tone and content for specific audiences
- **Newsletter Calendar**: Schedule planning tool

## Requirements

- Python 3.8+
- Ollama running at localhost:11434
- A model pulled (default: llama3.2)

## Usage

### Curate and Write Newsletter
```bash
./newsletter.py --topic ai --curate --write
```

### Custom Sources
```bash
./newsletter.py --topic tech --sources https://feed.url/rss https://other.feed/rss --curate --write
```

### Different Templates
```bash
./newsletter.py --topic business --curate --write --template deep_dive
./newsletter.py --topic dev --curate --write --template daily_brief
```

### Personalize for Audience
```bash
./newsletter.py --topic ai --curate --write --personalize "startup founders"
```

### HTML Format
```bash
./newsletter.py --topic tech --curate --write --format html
```

### View Schedule
```bash
./newsletter.py --schedule
```

### Select Sections
```bash
./newsletter.py --topic ai --write --sections intro highlights tip_of_week closing
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--topic` | Newsletter niche/topic | - |
| `--sources` | RSS feed URLs | from sources.json |
| `--curate` | Fetch and AI-curate content | false |
| `--write` | Generate newsletter | false |
| `--format` | markdown, html, text | markdown |
| `--template` | weekly_digest, daily_brief, deep_dive, roundup | weekly_digest |
| `--sections` | Which sections to include | all |
| `--personalize` | Target audience | - |
| `--schedule` | Show newsletter calendar | false |

## Sources Configuration

Edit `sources.json` to add RSS feeds by topic:
```json
{
  "tech": ["https://feed1.url/rss", "https://feed2.url/rss"],
  "ai": ["https://ai-feed.url/rss"]
}
```

Pre-configured topics: tech, ai, business, dev, startup, design

## Output

Newsletters saved to `output/<date>/`:
```
output/
└── 2024-01-15/
    └── newsletter_143022.md
```

## Templates

- `weekly_digest` - Comprehensive weekly overview (best for Mon/Tue send)
- `daily_brief` - Quick scannable daily update
- `deep_dive` - 2-3 items analyzed in depth (bi-monthly)
- `roundup` - Curated list format (best for Friday)
