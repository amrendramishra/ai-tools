# 🎬 Faceless YouTube Channel Automator

Complete zero-human-effort video pipeline. Generates scripts with SSML markup, scene breakdowns, TTS voiceover, subtitles, SEO metadata, and thumbnail concepts — all using local AI (Ollama).

## Requirements

- Python 3.9+
- Ollama running locally (`ollama serve`)
- macOS (for `say` TTS command)
- Model: `llama3.2`

## Installation

```bash
source ~/Downloads/AI/.venv/bin/activate
pip install requests
```

## Usage

### Generate full video package
```bash
./faceless_automator.py --channel tech-facts --topic 'Why AI Will Replace Programmers' --generate full
```

### Auto-pick trending topic
```bash
./faceless_automator.py --channel tech-facts --auto --generate full
```

### Short format (60s) with TTS
```bash
./faceless_automator.py --channel science-shorts --topic 'Black Holes Explained' --generate full --format short --tts
```

### Long format (10 min)
```bash
./faceless_automator.py --channel money-mindset --topic '5 Money Habits' --generate full --format long
```

### Scene breakdown only
```bash
./faceless_automator.py --channel tech-facts --topic 'Quantum Computing' --scenes
```

### Daily generation for all channels
```bash
./faceless_automator.py --daily --format medium --tts
```

## Options

| Flag | Values | Description |
|------|--------|-------------|
| `--channel` | channel name | Target channel (must be in voice_profiles.json) |
| `--topic` | any string | Video topic |
| `--auto` | flag | Auto-pick trending topic for channel's niche |
| `--generate` | full | Generate complete video package |
| `--tts` | flag | Generate voiceover using macOS `say` |
| `--scenes` | flag | Generate only scene breakdown |
| `--daily` | flag | Generate for all channels in voice_profiles.json |
| `--format` | short, medium, long | Video length (60s, 5min, 10min) |

## Output Structure

```
output/<channel>/<date>/<video-slug>/
├── video_package.json    # Master file
├── script.md             # Full narration script with SSML
├── scenes.json           # Scene-by-scene breakdown
├── text_overlays.json    # On-screen text with timestamps
├── thumbnail.json        # Thumbnail design concept
├── seo.json              # Title, description, tags
├── subtitles.srt         # SRT subtitle file
└── voiceover.aiff        # TTS audio (if --tts used)
```

## Configuration Files

### voice_profiles.json
Define TTS settings per channel:
```json
{
  "channel-name": {
    "voice": "Daniel",
    "rate": 190,
    "niche": "technology and AI",
    "tone": "informative",
    "language": "english"
  }
}
```

Available macOS voices: `say -v '?'` to list all.

### scene_templates.json
Stock footage search terms organized by niche (technology, motivation, science, finance, education).

## Workflow

1. Pick or auto-generate a topic based on channel niche
2. Generate narration script with SSML markup for natural TTS
3. Break into scenes with stock footage search terms
4. Create text overlays with timestamps
5. Generate thumbnail concept
6. Optimize title/description/tags for YouTube SEO
7. Generate SRT subtitles from script
8. (Optional) Create TTS voiceover as .aiff file

## Video Editing Workflow

After generation, use the output to:
1. Search stock footage using `scenes.json` search terms
2. Match audio from `voiceover.aiff` to scene timestamps
3. Add text overlays at specified timestamps
4. Apply transitions between scenes
5. Upload with SEO metadata from `seo.json`
