# AI Blog Writer

Generate full blog posts, outlines, and series plans with AI. Supports multiple styles, SEO optimization, and static site generator integration.

## Features

- **Full Posts**: Generate complete blog posts on any topic
- **Outlines**: Preview structure before committing to a full post
- **Multiple Styles**: technical, casual, storytelling, listicle
- **Length Control**: short (500w), medium (1000w), long (2000w+)
- **SEO Optimization**: Keywords, meta descriptions, proper headings
- **Series Planning**: Multi-part blog series with cross-linking strategy
- **AI Editing**: Improve existing posts with AI feedback
- **Publish Ready**: Hugo/Jekyll frontmatter for static site generators

## Requirements

- Python 3.8+
- Ollama running at `localhost:11434`
- Python packages: `requests`

## Setup

```bash
source ~/Downloads/AI/.venv/bin/activate
pip install requests
```

## Usage

```bash
# Generate a full blog post
./blog_writer.py --topic "Getting Started with Docker" --style technical --length medium

# Generate outline only (review before writing)
./blog_writer.py --topic "AI in 2026" --outline

# SEO-optimized listicle
./blog_writer.py --topic "Top 10 Python Tips" --style listicle --seo

# Long-form storytelling post
./blog_writer.py --topic "My Journey into Open Source" --style storytelling --length long

# Create a multi-part series plan
./blog_writer.py --topic "Complete Guide to Kubernetes" --series

# Edit/improve an existing post
./blog_writer.py --edit output/my-post.md

# Publish-ready with frontmatter
./blog_writer.py --topic "Docker Best Practices" --style technical --publish-ready
```

## Output

All generated content is saved to `output/` as markdown files:
- `20260710-getting-started-with-docker.md`
- `20260710-ai-in-2026-outline.md`
- `20260710-complete-guide-to-kubernetes-series-plan.md`

## Writing Styles

| Style | Best For |
|-------|----------|
| technical | Dev tutorials, how-tos, documentation |
| casual | Opinion pieces, personal blogs, newsletters |
| storytelling | Case studies, journey posts, thought leadership |
| listicle | Tips, tools, resources, comparisons |
