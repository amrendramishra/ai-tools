#!/usr/bin/env python3
"""AI Resume Generator - Tailors resumes and cover letters to job postings using AI."""

import argparse
import json
import sys
import os
import re
from datetime import datetime
from pathlib import Path

import requests

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"
OUTPUT_DIR = Path(__file__).parent / "output"
PROFILE_TEMPLATE = Path(__file__).parent / "my_profile.json"


def query_ollama(prompt: str) -> str:
    """Query Ollama for AI responses."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=180
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to Ollama at localhost:11434. Is it running?")
        sys.exit(1)
    except Exception as e:
        print(f"Error querying Ollama: {e}")
        return ""


def load_profile(profile_path: str) -> dict:
    """Load user profile from JSON file."""
    path = Path(profile_path)
    if not path.exists():
        print(f"Error: Profile not found: {profile_path}")
        print(f"Create one using the template: {PROFILE_TEMPLATE}")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def get_job_description(job_input: str) -> str:
    """Get job description from URL or text file."""
    if job_input.startswith("http"):
        try:
            from bs4 import BeautifulSoup
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
            resp = requests.get(job_input, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return re.sub(r'\s+', ' ', text)[:4000]
        except Exception as e:
            print(f"Warning: Could not fetch URL: {e}")
            return job_input
    elif os.path.exists(job_input):
        with open(job_input) as f:
            return f.read()[:4000]
    else:
        return job_input


def format_profile_summary(profile: dict) -> str:
    """Format profile data as text for AI context."""
    lines = []
    lines.append(f"Name: {profile.get('name', 'N/A')}")
    lines.append(f"Title: {profile.get('title', 'N/A')}")
    lines.append(f"Summary: {profile.get('summary', 'N/A')}")
    lines.append(f"Email: {profile.get('contact', {}).get('email', '')}")
    lines.append(f"Location: {profile.get('contact', {}).get('location', '')}")
    lines.append(f"\nSkills: {', '.join(profile.get('skills', {}).get('technical', []))}")
    lines.append(f"Soft Skills: {', '.join(profile.get('skills', {}).get('soft', []))}")

    lines.append("\nExperience:")
    for exp in profile.get("experience", []):
        lines.append(f"  - {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('duration', '')})")
        for ach in exp.get("achievements", []):
            lines.append(f"    • {ach}")

    lines.append("\nEducation:")
    for edu in profile.get("education", []):
        lines.append(f"  - {edu.get('degree', '')} from {edu.get('institution', '')} ({edu.get('year', '')})")

    lines.append("\nCertifications:")
    for cert in profile.get("certifications", []):
        lines.append(f"  - {cert}")

    return "\n".join(lines)


def generate_resume(profile: dict, job_desc: str, fmt: str = "markdown") -> str:
    """Generate a tailored resume using AI."""
    profile_text = format_profile_summary(profile)

    prompt = f"""You are an expert resume writer. Create a professional, ATS-optimized resume tailored to this job posting.

CANDIDATE PROFILE:
{profile_text}

JOB POSTING:
{job_desc[:2500]}

INSTRUCTIONS:
1. Tailor the resume to highlight relevant skills and experience for this specific job
2. Use keywords from the job posting naturally throughout
3. Quantify achievements where possible
4. Keep it concise (1-2 pages equivalent)
5. Use action verbs and results-oriented language
6. Format as {fmt}

Generate the complete resume now:"""

    return query_ollama(prompt)


def generate_cover_letter(profile: dict, job_desc: str, fmt: str = "markdown") -> str:
    """Generate a tailored cover letter using AI."""
    profile_text = format_profile_summary(profile)

    prompt = f"""You are an expert career coach. Write a compelling cover letter tailored to this job posting.

CANDIDATE PROFILE:
{profile_text}

JOB POSTING:
{job_desc[:2500]}

INSTRUCTIONS:
1. Address specific requirements from the job posting
2. Show enthusiasm and cultural fit
3. Highlight 2-3 most relevant achievements
4. Keep it to 3-4 paragraphs
5. Professional but personable tone
6. Format as {fmt}

Write the complete cover letter:"""

    return query_ollama(prompt)


def score_match(profile: dict, job_desc: str) -> str:
    """Score how well the profile matches the job."""
    profile_text = format_profile_summary(profile)

    prompt = f"""You are an ATS (Applicant Tracking System) analyzer. Score how well this candidate matches the job.

CANDIDATE PROFILE:
{profile_text}

JOB POSTING:
{job_desc[:2500]}

Provide:
1. Overall Match Score: X/100
2. Skills Match: List matched and missing skills
3. Experience Match: How well experience aligns
4. Keyword Analysis: Key terms present/missing from resume
5. Recommendations: Top 3 things to improve for this application

Be specific and actionable."""

    return query_ollama(prompt)


def save_output(content: str, filename: str, fmt: str):
    """Save generated content to output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ext_map = {"markdown": "md", "text": "txt", "html": "html"}
    ext = ext_map.get(fmt, "md")
    filepath = OUTPUT_DIR / f"{filename}.{ext}"

    with open(filepath, "w") as f:
        f.write(content)

    print(f"✓ Saved to: {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="AI Resume Generator - Tailor resumes to job postings")
    parser.add_argument("--profile", metavar="JSON", default=str(PROFILE_TEMPLATE),
                        help="Path to profile JSON file")
    parser.add_argument("--job", metavar="URL_OR_TEXT", help="Job posting URL, file, or text")
    parser.add_argument("--generate", choices=["resume", "cover_letter", "both"], default="both",
                        help="What to generate")
    parser.add_argument("--format", choices=["markdown", "text", "html"], default="markdown",
                        help="Output format")
    parser.add_argument("--score", action="store_true", help="Score profile-job match")

    args = parser.parse_args()

    if not args.job and not args.score:
        parser.print_help()
        print("\nExample: ./resume_generator.py --job 'Senior Python Developer at...' --generate both")
        return

    profile = load_profile(args.profile)
    job_desc = get_job_description(args.job) if args.job else ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.score:
        if not args.job:
            print("Error: --score requires --job")
            return
        print("🎯 Analyzing profile-job match...\n")
        result = score_match(profile, job_desc)
        print(result)
        save_output(result, f"match_score_{timestamp}", "text")
        return

    if args.generate in ("resume", "both"):
        print("📝 Generating tailored resume...")
        resume = generate_resume(profile, job_desc, args.format)
        print("\n" + resume)
        save_output(resume, f"resume_{timestamp}", args.format)

    if args.generate in ("cover_letter", "both"):
        print("\n✉️  Generating cover letter...")
        letter = generate_cover_letter(profile, job_desc, args.format)
        print("\n" + letter)
        save_output(letter, f"cover_letter_{timestamp}", args.format)

    print("\n✓ Generation complete! Files saved to output/")


if __name__ == "__main__":
    main()
