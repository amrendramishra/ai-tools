# Content Repurposer

Transform any content into multiple formats using AI. Turn a blog post into a Twitter thread, LinkedIn post, Instagram caption, YouTube Short script, email newsletter, and more.

## Quick Start

```bash
source ~/Downloads/AI/.venv/bin/activate
pip install requests

# Ensure Ollama is running
ollama serve

# Repurpose content
python repurposer.py --input article.md --from blog --to twitter_thread linkedin_post
```

## Usage

```bash
# Single format
python repurposer.py --input "Your content here" --from article --to twitter_thread

# Multiple formats
python repurposer.py --input post.md --from blog --to twitter_thread linkedin_post email_newsletter

# All formats at once
python repurposer.py --input script.txt --from video_script --all

# With tone
python repurposer.py --input content.md --from article --to linkedin_post --tone casual

# With brand voice
python repurposer.py --input blog.md --from blog --all --brand-voice brand_voice.json
```

## Source Formats

- `blog` - Blog post
- `video_script` - Video script
- `podcast` - Podcast transcript
- `article` - News/magazine article
- `thread` - Social media thread

## Target Formats

| Format | Description |
|--------|-------------|
| `twitter_thread` | 5-10 tweet thread |
| `linkedin_post` | Professional LinkedIn post |
| `instagram_caption` | Short caption + hashtags |
| `youtube_short` | 60-second video script |
| `email_newsletter` | Newsletter format |
| `blog_post` | Full blog post |
| `podcast_outline` | Podcast talking points |

## Tone Options

- `professional` (default)
- `casual`
- `humorous`
- `inspirational`

## Brand Voice

Create a `brand_voice.json` to maintain consistent voice:
```json
{
  "brand_name": "Your Brand",
  "tone": "professional yet approachable",
  "audience": "Your target audience",
  "writing_style": { ... }
}
```

See `brand_voice.json` for a full template.

## Output

Files are saved to `output/<date>/` with one file per format.
