# 🎨 Thumbnail AI Analyzer

AI-powered YouTube thumbnail analyzer using Ollama's LLaVA vision model. Scores thumbnails on key metrics and provides actionable improvement suggestions.

## Features

- **Single Image Analysis**: Score any thumbnail on 5 key metrics (1-10 scale)
- **Thumbnail Comparison**: Compare two thumbnails side-by-side with a winner declared
- **Text Generation**: Get AI-suggested text overlays for your thumbnails
- **Batch Analysis**: Analyze entire folders of thumbnails with ranked results
- **Best Practices**: Built-in knowledge base of thumbnail optimization tips

## Scoring Categories

| Category | What It Measures |
|----------|-----------------|
| 📝 Text Readability | Font visibility, contrast, legibility at small sizes |
| 🌈 Color Contrast | Vibrancy, color harmony, standout potential |
| 👤 Face Detection | Presence, size, and expressiveness of faces |
| 💥 Emotional Impact | Curiosity, excitement, scroll-stopping power |
| 🖱️ Click-Worthiness | Overall likelihood of getting clicked |

## Prerequisites

- Python 3.8+
- Ollama running locally with the `llava` model
- Virtual environment at `~/Downloads/AI/.venv`

```bash
# Install Ollama and pull the LLaVA model
ollama pull llava
```

## Usage

### Analyze a Single Thumbnail
```bash
./thumbnail_analyzer.py --image path/to/thumbnail.png
```

### Compare Two Thumbnails
```bash
./thumbnail_analyzer.py --compare thumbnail_a.png thumbnail_b.png
```

### Generate Text Overlay Suggestions
```bash
# Generic suggestions
./thumbnail_analyzer.py --generate-text

# Tailored to a specific image
./thumbnail_analyzer.py --generate-text --image thumbnail.png
```

### Batch Analyze a Folder
```bash
./thumbnail_analyzer.py --batch ./my-thumbnails/
```

## Output

- Terminal scorecard with visual bars
- Detailed AI analysis with improvement suggestions
- JSON export for batch analysis results

## Supported Image Formats

PNG, JPG, JPEG, WebP, GIF, BMP

## Best Practices Reference

See `best_practices.json` for comprehensive thumbnail optimization guidelines covering:
- Text guidelines (fonts, sizes, colors)
- Color schemes that drive high CTR
- Face positioning and expressions
- Composition rules
- A/B testing tips
- Common mistakes to avoid
