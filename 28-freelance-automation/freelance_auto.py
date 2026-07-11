#!/usr/bin/env python3
"""Freelance Automation - AI-powered proposal and pitch generator."""

import argparse
import json
import os
import sys
import datetime
import re
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
TEMPLATES_DIR = SCRIPT_DIR / "templates"
DEFAULT_PROFILE = SCRIPT_DIR / "my_profile.json"


def _update_model(new_model: str):
    """Update the global model name."""
    global MODEL
    MODEL = new_model


def query_ollama(prompt: str, model: str = None) -> str:
    """Send a prompt to Ollama and return the response."""
    import urllib.request
    import urllib.error

    if model is None:
        model = MODEL

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 2048}
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response", "").strip()
    except urllib.error.URLError as e:
        print(f"Error connecting to Ollama: {e}")
        sys.exit(1)


def load_profile(profile_path: str) -> dict:
    """Load freelancer profile from JSON file."""
    path = Path(profile_path)
    if not path.exists():
        print(f"Profile not found: {path}")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def load_template(template_name: str) -> str:
    """Load a proposal template by name."""
    template_file = TEMPLATES_DIR / f"{template_name}.md"
    if not template_file.exists():
        available = [f.stem for f in TEMPLATES_DIR.glob("*.md")]
        print(f"Template '{template_name}' not found. Available: {available}")
        sys.exit(1)
    return template_file.read_text()


def score_job_fit(profile: dict, job_text: str) -> int:
    """Rate job fit from 1-10 using AI."""
    prompt = f"""Rate how well this freelancer matches the job posting on a scale of 1-10.
Consider skills match, experience level, and project type alignment.

FREELANCER PROFILE:
Name: {profile.get('name', 'N/A')}
Title: {profile.get('title', 'N/A')}
Skills: {', '.join(profile.get('skills', []))}
Experience: {profile.get('experience_years', 'N/A')} years
Specializations: {', '.join(profile.get('specializations', []))}

JOB POSTING:
{job_text}

Respond with ONLY a JSON object: {{"score": <1-10>, "reasoning": "<brief explanation>", "matching_skills": [<list>], "missing_skills": [<list>]}}"""

    response = query_ollama(prompt)
    try:
        # Try to extract JSON from response
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            result = json.loads(match.group())
            return result
    except (json.JSONDecodeError, AttributeError):
        pass
    return {"score": 5, "reasoning": response, "matching_skills": [], "missing_skills": []}


def generate_proposal(profile: dict, job_text: str, template: str = None) -> str:
    """Generate a personalized proposal for a job posting."""
    template_context = ""
    if template:
        template_content = load_template(template)
        template_context = f"\nFollow this template structure:\n{template_content}\n"

    prompt = f"""Write a compelling freelance proposal for this job posting.
Make it personalized, professional, and highlight relevant experience.

FREELANCER PROFILE:
Name: {profile.get('name', 'N/A')}
Title: {profile.get('title', 'N/A')}
Skills: {', '.join(profile.get('skills', []))}
Experience: {profile.get('experience_years', 'N/A')} years
Specializations: {', '.join(profile.get('specializations', []))}
Portfolio highlights: {json.dumps(profile.get('portfolio_highlights', []))}
Hourly rate: ${profile.get('hourly_rate', 'N/A')}/hr
{template_context}
JOB POSTING:
{job_text}

Write a proposal that:
1. Opens with a hook showing you understand their problem
2. Highlights 2-3 most relevant experiences
3. Proposes a clear approach/timeline
4. Ends with a call to action
5. Keeps a confident but not arrogant tone"""

    return query_ollama(prompt)


def generate_pitch(profile: dict, job_text: str = None, template: str = None) -> str:
    """Generate a cold outreach pitch."""
    template_context = ""
    if template:
        template_content = load_template(template)
        template_context = f"\nFollow this template structure:\n{template_content}\n"

    context = f"\nTARGET/CONTEXT:\n{job_text}" if job_text else ""

    prompt = f"""Write a compelling cold outreach pitch for a freelancer.
Keep it concise (under 150 words), personalized, and action-oriented.

FREELANCER PROFILE:
Name: {profile.get('name', 'N/A')}
Title: {profile.get('title', 'N/A')}
Skills: {', '.join(profile.get('skills', []))}
Key achievements: {json.dumps(profile.get('achievements', []))}
{template_context}{context}

Write a pitch that:
1. Grabs attention in the first line
2. Shows specific value you can provide
3. Includes a brief social proof/result
4. Has a clear, low-friction CTA
5. Sounds human, not salesy"""

    return query_ollama(prompt)


def generate_portfolio_desc(profile: dict, job_text: str = None) -> str:
    """Generate a portfolio item description."""
    prompt = f"""Write a compelling portfolio item description for a freelancer.

FREELANCER PROFILE:
Name: {profile.get('name', 'N/A')}
Title: {profile.get('title', 'N/A')}
Skills: {', '.join(profile.get('skills', []))}

PROJECT CONTEXT (if any):
{job_text or 'Generate a general portfolio piece based on the freelancer skills.'}

Write a portfolio description that includes:
1. Project title
2. Client/industry context
3. Challenge/problem statement
4. Solution approach
5. Technologies used
6. Results/impact (with metrics if possible)
7. Key takeaways

Format it professionally for a portfolio website."""

    return query_ollama(prompt)


def interactive_customize(content: str, profile: dict, job_text: str) -> str:
    """Interactively refine generated content."""
    print("\n" + "=" * 60)
    print("GENERATED CONTENT:")
    print("=" * 60)
    print(content)
    print("=" * 60)

    while True:
        print("\nOptions:")
        print("  1. Make it more formal")
        print("  2. Make it more casual")
        print("  3. Make it shorter")
        print("  4. Make it longer")
        print("  5. Emphasize specific skill")
        print("  6. Custom instruction")
        print("  7. Accept and save")
        print("  8. Discard")

        choice = input("\nYour choice (1-8): ").strip()

        if choice == "7":
            return content
        elif choice == "8":
            return None

        instructions = {
            "1": "Rewrite this to be more formal and professional in tone.",
            "2": "Rewrite this to be more casual and conversational.",
            "3": "Make this more concise - cut it by about 30% while keeping key points.",
            "4": "Expand this with more detail, examples, and specifics.",
            "5": None,
            "6": None,
        }

        if choice == "5":
            skill = input("Which skill to emphasize? ").strip()
            instruction = f"Rewrite to heavily emphasize experience with {skill}."
        elif choice == "6":
            instruction = input("Your instruction: ").strip()
        elif choice in instructions:
            instruction = instructions[choice]
        else:
            print("Invalid choice.")
            continue

        prompt = f"""Revise the following content based on this instruction:
INSTRUCTION: {instruction}

ORIGINAL CONTENT:
{content}

CONTEXT - Freelancer Profile:
Name: {profile.get('name', 'N/A')}
Skills: {', '.join(profile.get('skills', []))}

Provide only the revised content, no explanations."""

        content = query_ollama(prompt)
        print("\n" + "=" * 60)
        print("REVISED CONTENT:")
        print("=" * 60)
        print(content)
        print("=" * 60)

    return content


def save_output(content: str, prefix: str, format_ext: str = "md") -> Path:
    """Save generated content to output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.{format_ext}"
    filepath = OUTPUT_DIR / filename
    filepath.write_text(content)
    print(f"\n✅ Saved to: {filepath}")
    return filepath


def process_batch(profile: dict, batch_file: str, template: str = None, do_score: bool = False):
    """Process multiple job postings from a file."""
    path = Path(batch_file)
    if not path.exists():
        print(f"Batch file not found: {path}")
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    jobs = data if isinstance(data, list) else data.get("jobs", [])
    print(f"Processing {len(jobs)} job postings...\n")

    results = []
    for i, job in enumerate(jobs, 1):
        job_text = job if isinstance(job, str) else job.get("description", job.get("text", str(job)))
        job_title = job.get("title", f"Job {i}") if isinstance(job, dict) else f"Job {i}"

        print(f"[{i}/{len(jobs)}] Processing: {job_title}")

        if do_score:
            score_result = score_job_fit(profile, job_text)
            score = score_result.get("score", 5) if isinstance(score_result, dict) else 5
            print(f"  Fit Score: {score}/10")
            if score < 5:
                print(f"  ⚠️  Low fit score, skipping...")
                results.append({"job": job_title, "score": score, "skipped": True})
                continue

        proposal = generate_proposal(profile, job_text, template)
        filepath = save_output(proposal, f"batch_proposal_{i}")
        results.append({"job": job_title, "file": str(filepath), "score": score_result if do_score else None})

    # Save summary
    summary = json.dumps(results, indent=2)
    save_output(summary, "batch_summary", "json")
    print(f"\n✅ Batch complete! Processed {len(jobs)} jobs.")


def main():
    parser = argparse.ArgumentParser(
        description="Freelance Automation - AI-powered proposals and pitches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --profile my_profile.json --job "Need a Python developer..." --generate proposal
  %(prog)s --profile my_profile.json --job "React app needed" --generate proposal --template upwork
  %(prog)s --profile my_profile.json --generate pitch --template cold_email
  %(prog)s --profile my_profile.json --job "Full-stack role" --score
  %(prog)s --profile my_profile.json --batch jobs.json --generate proposal
  %(prog)s --profile my_profile.json --job "..." --generate proposal --customize
        """
    )

    parser.add_argument("--profile", type=str, default=str(DEFAULT_PROFILE),
                        help="Path to freelancer profile JSON (default: my_profile.json)")
    parser.add_argument("--job", type=str, help="Job posting text or URL")
    parser.add_argument("--generate", type=str,
                        choices=["proposal", "pitch", "portfolio-desc"],
                        help="Type of content to generate")
    parser.add_argument("--template", type=str,
                        choices=["upwork", "fiverr", "linkedin", "cold_email"],
                        help="Use a saved template")
    parser.add_argument("--customize", action="store_true",
                        help="Interactive refinement of generated content")
    parser.add_argument("--batch", type=str,
                        help="Process multiple job postings from JSON file")
    parser.add_argument("--score", action="store_true",
                        help="Rate job fit (1-10) before writing proposal")
    parser.add_argument("--model", type=str, default=MODEL,
                        help=f"Ollama model to use (default: {MODEL})")

    args = parser.parse_args()

    if not args.generate and not args.score and not args.batch:
        parser.print_help()
        sys.exit(0)

    # Load profile
    profile = load_profile(args.profile)
    _update_model(args.model)

    # Batch mode
    if args.batch:
        process_batch(profile, args.batch, args.template, args.score)
        return

    # Score mode
    if args.score:
        if not args.job:
            print("Error: --score requires --job")
            sys.exit(1)
        result = score_job_fit(profile, args.job)
        print(f"\n📊 Job Fit Score: {result.get('score', 'N/A')}/10")
        print(f"💡 Reasoning: {result.get('reasoning', 'N/A')}")
        print(f"✅ Matching skills: {', '.join(result.get('matching_skills', []))}")
        print(f"❌ Missing skills: {', '.join(result.get('missing_skills', []))}")
        if not args.generate:
            return

    # Generate content
    if args.generate == "proposal":
        if not args.job:
            print("Error: --generate proposal requires --job")
            sys.exit(1)
        content = generate_proposal(profile, args.job, args.template)
        prefix = "proposal"
    elif args.generate == "pitch":
        content = generate_pitch(profile, args.job, args.template)
        prefix = "pitch"
    elif args.generate == "portfolio-desc":
        content = generate_portfolio_desc(profile, args.job)
        prefix = "portfolio_desc"
    else:
        parser.print_help()
        return

    # Interactive customization
    if args.customize:
        content = interactive_customize(content, profile, args.job or "")
        if content is None:
            print("Discarded.")
            return

    # Display and save
    print("\n" + "=" * 60)
    print(f"GENERATED {args.generate.upper()}:")
    print("=" * 60)
    print(content)
    print("=" * 60)

    save_output(content, prefix)


if __name__ == "__main__":
    main()
