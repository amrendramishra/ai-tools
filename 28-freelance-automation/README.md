# Freelance Automation 🚀

AI-powered tool for generating freelance proposals, pitches, and portfolio descriptions using local LLMs via Ollama.

## Features

- **Proposal Generation**: Create personalized proposals from job postings
- **Cold Outreach Pitches**: Generate attention-grabbing cold emails and messages
- **Portfolio Descriptions**: Craft compelling portfolio item descriptions
- **Job Fit Scoring**: AI rates how well a job matches your profile (1-10)
- **Templates**: Pre-built templates for Upwork, Fiverr, LinkedIn, and cold email
- **Batch Processing**: Process multiple job postings at once
- **Interactive Refinement**: Iteratively improve generated content

## Requirements

- Python 3.8+
- Ollama running at localhost:11434
- A model pulled (default: llama3.2)

## Setup

```bash
# Ensure Ollama is running
ollama serve

# Pull a model
ollama pull llama3.2

# Edit your profile
cp my_profile.json my_profile.json  # Edit with your details
```

## Usage

### Generate a Proposal
```bash
./freelance_auto.py --job "Looking for a Python developer to build an API..." --generate proposal
```

### Generate with Template
```bash
./freelance_auto.py --job "Need React developer..." --generate proposal --template upwork
```

### Score Job Fit
```bash
./freelance_auto.py --job "Senior ML engineer needed..." --score
```

### Generate Cold Pitch
```bash
./freelance_auto.py --generate pitch --template cold_email
```

### Portfolio Description
```bash
./freelance_auto.py --job "Built a SaaS dashboard" --generate portfolio-desc
```

### Batch Processing
```bash
./freelance_auto.py --batch jobs.json --generate proposal --score
```

### Interactive Customization
```bash
./freelance_auto.py --job "..." --generate proposal --customize
```

## Batch File Format (jobs.json)
```json
[
  {"title": "Python API Developer", "description": "Need a Python dev to..."},
  {"title": "React Frontend", "description": "Looking for a React expert..."}
]
```

## Templates

| Template | Best For |
|----------|----------|
| `upwork` | Upwork job proposals |
| `fiverr` | Fiverr buyer requests |
| `linkedin` | LinkedIn outreach messages |
| `cold_email` | Cold email campaigns |

## Output

All generated content is saved to `output/` with timestamps:
- `proposal_20240101_120000.md`
- `pitch_20240101_120000.md`
- `portfolio_desc_20240101_120000.md`
- `batch_summary_20240101_120000.json`

## Profile Configuration

Edit `my_profile.json` with your details:
- Name, title, and contact info
- Skills and specializations
- Experience and hourly rate
- Portfolio highlights with metrics
- Achievements and certifications
