# AI Resume Generator

Tailor resumes and cover letters to specific job postings using AI. ATS-optimized with keyword matching and scoring.

## Features

- **Tailored Resumes**: AI customizes your resume for each specific job posting
- **Cover Letters**: Generates compelling, personalized cover letters
- **ATS Optimization**: Incorporates relevant keywords from job postings
- **Match Scoring**: See how well your profile matches a job (0-100)
- **Multiple Formats**: Output as Markdown, plain text, or HTML
- **Profile Template**: JSON-based profile for easy updates

## Requirements

- Python 3.8+
- Ollama running at `localhost:11434`
- Python packages: `requests`, `beautifulsoup4` (for URL fetching)

## Setup

```bash
source ~/Downloads/AI/.venv/bin/activate
pip install requests beautifulsoup4
```

## Usage

1. Edit `my_profile.json` with your actual experience and skills.

2. Generate tailored documents:

```bash
# Generate both resume and cover letter
./resume_generator.py --job "Senior Python Developer with AWS experience..." --generate both

# From a job posting URL
./resume_generator.py --job https://example.com/jobs/123 --generate resume

# From a text file
./resume_generator.py --job job_posting.txt --generate cover_letter

# Score your match
./resume_generator.py --job "Job description..." --score

# Use custom profile and format
./resume_generator.py --profile my_profile.json --job "..." --format html
```

## Output

Generated files are saved to the `output/` directory with timestamps:
- `resume_20260710_143000.md`
- `cover_letter_20260710_143000.md`
- `match_score_20260710_143000.txt`

## Profile Template

Edit `my_profile.json` with your:
- Contact information
- Technical and soft skills
- Work experience with quantified achievements
- Education and certifications
- Notable projects
