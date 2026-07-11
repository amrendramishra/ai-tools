# AI Course Creator 📚

Generate complete course content using local LLMs via Ollama. Creates structured courses with lessons, quizzes, assignments, and summaries.

## Features

- **Course Outline Generation**: Create structured course outlines
- **Full Course Content**: Generate complete lessons with explanations and examples
- **Individual Lessons**: Generate specific lessons on demand
- **Quiz Generation**: MCQ and short answer questions per lesson
- **Assignments**: Practical exercises with requirements
- **Multi-Platform**: Tailored for Udemy, Skillshare, YouTube, or self-hosted
- **Multiple Formats**: Output as Markdown or JSON

## Requirements

- Python 3.8+
- Ollama running at localhost:11434
- A model pulled (default: llama3.2)

## Usage

### Generate Course Outline
```bash
./course_creator.py --topic "Python for Data Science" --level beginner --generate outline
```

### Generate Full Course
```bash
./course_creator.py --topic "React.js Masterclass" --level intermediate --modules 10 --generate full
```

### Generate Single Lesson
```bash
./course_creator.py --topic "Machine Learning" --level advanced --generate lesson 3
```

### Platform-Specific Course
```bash
./course_creator.py --topic "Docker & Kubernetes" --platform udemy --generate full
```

### JSON Output
```bash
./course_creator.py --topic "Web Development" --format json --generate outline
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--topic` | Course subject (required) | - |
| `--level` | beginner, intermediate, advanced | intermediate |
| `--modules` | Number of modules | 8 |
| `--generate` | outline, full, lesson \<n\> | - |
| `--format` | markdown, json | markdown |
| `--platform` | udemy, skillshare, youtube, self-hosted | self-hosted |
| `--model` | Ollama model name | llama3.2 |

## Output Structure

```
output/<course-slug>/
├── 00-outline.md
├── module-01-lesson-01.md
├── module-01-lesson-02.md
├── ...
└── README.md
```

## Generated Lesson Contents

Each lesson includes:
- 🎯 Learning objectives
- 📖 Lesson content with examples
- 💡 Tips and best practices
- 📝 Quiz (MCQ + short answer)
- 📋 Assignment with requirements
- 📌 Key takeaways
