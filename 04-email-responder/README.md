# AI Email Responder

Analyze incoming emails and generate intelligent response options using Ollama.

## Features

- **Analyze**: Detect tone, urgency, key points, required actions
- **Generate**: 3 response options (brief, detailed, decline)
- **Tone Control**: Professional, casual, or friendly responses
- **Interactive**: Refine responses iteratively (shorter, longer, rewrite)
- **Clipboard**: Read from and copy to macOS clipboard

## Prerequisites

- macOS (uses `pbpaste`/`pbcopy` for clipboard)
- [Ollama](https://ollama.ai) running on localhost:11434
- A language model: `ollama pull llama3.2`

## Usage

```bash
# Read email from clipboard
./email_responder.py --paste

# Read from a file
./email_responder.py --file email.txt

# Pipe from stdin
cat email.txt | ./email_responder.py

# Set response tone
./email_responder.py --paste --tone casual
./email_responder.py --paste --tone friendly

# Add context for better responses
./email_responder.py --paste --context "I am busy this week"

# Only analyze without generating responses
./email_responder.py --paste --analyze-only

# Skip interactive refinement
./email_responder.py --paste --no-interactive
```

## Workflow

1. Provide email content (clipboard, file, or stdin)
2. AI analyzes: tone, urgency, key points, required action
3. AI generates 3 response options
4. Choose a response to refine interactively
5. Final response is copied to clipboard

## Interactive Refinement

After choosing a response:
- **Enter**: Accept and copy to clipboard
- **r**: Rewrite with custom instructions
- **s**: Make it shorter
- **l**: Make it longer
- **q**: Quit without copying
