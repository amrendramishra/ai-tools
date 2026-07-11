# 🗂️ Smart File Organizer

AI-powered file organization tool that uses Ollama LLM to intelligently classify and organize files by name, extension, and content.

## Features

- **Extension-based classification**: Fast sorting by file extension into 10 default categories
- **AI classification**: Uses Ollama to analyze filenames and classify ambiguous files
- **Smart mode**: Reads file content and categorizes by topic (Finance, Health, Work, etc.)
- **Watch mode**: Monitors a directory and auto-organizes new files in real-time
- **Dry run**: Preview what would be moved without actually moving anything
- **Undo**: Reverses the last organization session using the move log
- **Custom rules**: Define your own categories and extension mappings via JSON
- **macOS notifications**: Get notified when files are organized

## Requirements

- Python 3.8+
- Ollama running at `localhost:11434` (for AI features)
- macOS (for notifications)

## Installation

```bash
# Activate the virtual environment
source ~/Downloads/AI/.venv/bin/activate

# Dependencies (already in venv)
pip install requests watchdog
```

## Usage

### One-time organize
```bash
# Organize files in a directory
./file_organizer.py --organize ~/Downloads

# Preview without moving
./file_organizer.py --organize ~/Downloads --dry-run

# Smart mode (AI reads content, categorizes by topic)
./file_organizer.py --organize ~/Downloads --smart

# Use custom rules
./file_organizer.py --organize ~/Downloads --rules my_rules.json

# Extension-only (no AI)
./file_organizer.py --organize ~/Downloads --no-ai
```

### Watch mode
```bash
# Watch for new files and auto-organize
./file_organizer.py --watch ~/Downloads

# Watch with smart mode
./file_organizer.py --watch ~/Downloads --smart
```

### Undo
```bash
# Undo the last organization session
./file_organizer.py --undo
```

## Default Categories

| Category | Extensions |
|----------|-----------|
| Documents | .doc, .docx, .txt, .rtf, .odt, .pages, .tex, .md |
| Images | .jpg, .jpeg, .png, .gif, .bmp, .svg, .webp, .tiff, .heic |
| Videos | .mp4, .avi, .mkv, .mov, .wmv, .flv, .webm |
| Audio | .mp3, .wav, .flac, .aac, .ogg, .wma, .m4a |
| Code | .py, .js, .ts, .java, .c, .cpp, .go, .rs, .html, .css |
| Archives | .zip, .tar, .gz, .7z, .rar, .dmg |
| Spreadsheets | .xls, .xlsx, .csv, .ods, .numbers |
| Presentations | .ppt, .pptx, .key, .odp |
| PDFs | .pdf |
| Other | Everything else |

## Custom Rules

Edit `rules.json` or provide your own:

```json
{
  "categories": {
    "MyCategory": [".ext1", ".ext2"],
    "AnotherCategory": [".ext3"]
  }
}
```

## How It Works

1. **Extension matching**: First tries to match the file extension against known categories
2. **AI classification**: If enabled, sends the filename (and optionally content) to Ollama for classification
3. **Smart mode**: Reads file content and asks AI to categorize by topic rather than file type
4. **Organization**: Creates category subdirectories and moves files into them
5. **Logging**: Every move is logged to `moves.log` for undo capability

## Files

- `file_organizer.py` - Main executable script
- `rules.json` - Default organization rules
- `moves.log` - Auto-generated move log (for undo)
