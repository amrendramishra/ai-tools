# 🤖 AI Comment Responder

AI-powered YouTube comment analysis and response generator using Ollama. Classifies comments by sentiment and generates persona-appropriate responses.

## Features

- **Sentiment Analysis**: Classifies comments as positive, negative, question, spam, or constructive
- **Smart Responses**: Generates contextually appropriate replies
- **Channel Personas**: Different tones for different channels (tech, gaming, education, etc.)
- **Spam Filtering**: Automatically detects and filters spam comments
- **Batch Processing**: Process hundreds of comments at once with CSV export
- **Interactive Approval**: Review, edit, or skip responses before posting

## Prerequisites

- Python 3.8+
- Ollama running locally with a language model (default: `llama3.2`)
- Virtual environment at `~/Downloads/AI/.venv`

```bash
ollama pull llama3.2
```

## Usage

### Single Comment
```bash
./comment_responder.py --text "This video saved my project! Thank you so much!"
```

### From File (CSV or JSON)
```bash
./comment_responder.py --file comments.csv --channel tech_channel
```

### Paste Mode (Interactive Input)
```bash
./comment_responder.py --paste
```

### Batch Processing with Export
```bash
./comment_responder.py --file comments.json --batch --output responses.csv
```

### Interactive Approval Mode
```bash
./comment_responder.py --file comments.csv --approve --channel gaming_channel
```

## Input Formats

### CSV Format
```csv
comment,author
"Great video!",User1
"When is the next upload?",User2
```

### JSON Format
```json
[
  "Great video!",
  "When is the next upload?",
  {"comment": "This helped me a lot", "author": "User3"}
]
```

## Channel Personas

Available personas (in `personas.json`):
- `tech_channel` - Knowledgeable, dev-friendly
- `gaming_channel` - Enthusiastic, gaming lingo
- `education_channel` - Patient, encouraging
- `cooking_channel` - Warm, passionate about food
- `fitness_channel` - Motivating, coach-like
- `vlog_channel` - Personal, relatable
- `music_channel` - Creative, appreciative
- `finance_channel` - Trustworthy, informative
- `hindi_channel` - Hinglish, culturally relatable

## Sentiment Categories

| Category | Icon | Description |
|----------|------|-------------|
| Positive | 😊 | Praise, compliments, support |
| Negative | 😟 | Criticism, complaints |
| Question | ❓ | Seeking information |
| Spam | 🚫 | Promotional, bot-like |
| Constructive | 💡 | Helpful suggestions |

## Output

- Terminal display with color-coded categories
- CSV export with comment, category, sentiment score, and response
- Spam statistics

## Customization

Edit `personas.json` to add your own channel personas with custom:
- Tone and style
- Language preferences
- Sign-off messages
- Response guidelines
