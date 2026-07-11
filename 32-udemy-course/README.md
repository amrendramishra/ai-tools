# 🎓 AI Course Generator for Udemy

Generate complete, publishable online courses using local AI (Ollama). Creates outlines, scripts, quizzes, descriptions, and full course packages optimized for Udemy, Skillshare, or YouTube playlists.

## Requirements

- Python 3.9+
- Ollama running locally (`ollama serve`)
- Model: `llama3.2` (or change MODEL in script)

## Installation

```bash
source ~/Downloads/AI/.venv/bin/activate
pip install requests
```

## Usage

### Generate just the outline
```bash
./udemy_course.py --topic 'AI Automation for Beginners' --generate outline
```

### Generate full course (all materials)
```bash
./udemy_course.py --topic 'Python Masterclass' --generate full --sections 12
```

### Generate video scripts only
```bash
./udemy_course.py --topic 'AWS for Beginners' --generate scripts --language hindi
```

### Generate quizzes only
```bash
./udemy_course.py --topic 'Machine Learning' --generate quizzes
```

### Generate Udemy listing description
```bash
./udemy_course.py --topic 'Android Development' --generate description --platform udemy
```

### For Skillshare format
```bash
./udemy_course.py --topic 'YouTube Growth' --generate full --platform skillshare
```

## Options

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--topic` | any string | required | Course topic |
| `--language` | hindi, english | english | Content language |
| `--sections` | 1-20 | 10 | Number of sections |
| `--generate` | outline, full, scripts, quizzes, description | required | What to generate |
| `--platform` | udemy, skillshare, youtube_playlist | udemy | Target platform |

## Output Structure

```
output/<course-slug>/
├── README.md                 # Course summary
├── course_complete.json      # Master file with all data
├── outline.json              # Course structure
├── description.json          # Platform listing
├── scripts/
│   ├── section-1/
│   │   ├── lecture-1.md
│   │   └── lecture-2.md
│   └── section-2/
├── quizzes/
│   ├── section-1.json
│   └── section-2.json
├── assignments/
│   ├── section-1.json
│   └── section-2.json
└── talking_points/
    ├── section-1/
    │   ├── lecture-1.json
    │   └── lecture-2.json
    └── section-2/
```

## Supporting Files

- **course_ideas.json** - 20 course ideas based on Python, AI, Automation, YouTube, AWS, Android skills
- **udemy_seo.json** - SEO keywords, trending topics, pricing strategy, competition analysis

## How It Works

1. Takes your topic and generates a structured course outline via LLM
2. For each section/lecture, generates full video scripts (~150 words/min)
3. Creates MCQ quizzes with explanations per section
4. Generates platform-optimized descriptions with SEO keywords
5. Produces assignments and slide talking points
6. Saves everything in organized directory structure
