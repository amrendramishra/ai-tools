#!/usr/bin/env python3
"""AI Code Reviewer - Automated code review using AI analysis."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "codellama"
FALLBACK_MODEL = "llama3.2"

SEVERITY_COLORS = {
    "critical": "\033[91m",  # Red
    "warning": "\033[93m",   # Yellow
    "info": "\033[94m",      # Blue
    "suggestion": "\033[92m", # Green
}
RESET = "\033[0m"

LANGUAGE_EXTENSIONS = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".java": "java", ".c": "c", ".cpp": "cpp", ".h": "c",
    ".rs": "rust", ".go": "go", ".rb": "ruby", ".php": "php",
    ".swift": "swift", ".kt": "kotlin", ".scala": "scala",
    ".sh": "bash", ".bash": "bash", ".zsh": "zsh",
    ".html": "html", ".css": "css", ".sql": "sql",
    ".yaml": "yaml", ".yml": "yaml", ".json": "json",
    ".toml": "toml", ".xml": "xml", ".md": "markdown",
}


def ollama_generate(prompt: str, model: str = MODEL) -> str:
    """Call Ollama API."""
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.2, "num_predict": 4096}
        }, timeout=180)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to Ollama at localhost:11434", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError:
        # Try fallback model
        if model != FALLBACK_MODEL:
            try:
                resp = requests.post(f"{OLLAMA_URL}/api/generate", json={
                    "model": FALLBACK_MODEL, "prompt": prompt, "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 4096}
                }, timeout=180)
                resp.raise_for_status()
                return resp.json().get("response", "")
            except Exception:
                pass
        return ""
    except Exception as e:
        print(f"Error calling Ollama: {e}", file=sys.stderr)
        return ""


def detect_language(filepath: str) -> str:
    """Auto-detect programming language from file extension."""
    ext = Path(filepath).suffix.lower()
    return LANGUAGE_EXTENSIONS.get(ext, "unknown")


def review_code(code: str, language: str, filename: str = "", fix: bool = False) -> list:
    """Review code and return findings."""
    fix_instruction = """
Also for each issue, provide a "fix" field with a corrected code snippet.""" if fix else ""

    prompt = f"""You are an expert code reviewer. Review the following {language} code for:
1. Bugs and logical errors
2. Security vulnerabilities
3. Performance issues
4. Style and readability
5. Complexity concerns

Return ONLY valid JSON in this format (no other text):
{{
  "findings": [
    {{
      "severity": "critical|warning|info|suggestion",
      "category": "bug|security|performance|style|complexity",
      "line": <line_number_or_null>,
      "message": "description of the issue",
      "code_snippet": "relevant code line if applicable"{', "fix": "suggested fix code"' if fix else ''}
    }}
  ],
  "summary": "brief overall assessment",
  "score": <1-10 quality score>
}}
{fix_instruction}

File: {filename}
Language: {language}

Code:
```{language}
{code[:6000]}
```

Return ONLY the JSON:"""

    response = ollama_generate(prompt)
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass
    return {"findings": [], "summary": "Unable to parse review results", "score": None}


def format_findings_markdown(review: dict, filename: str = "") -> str:
    """Format findings as markdown."""
    lines = []
    if filename:
        lines.append(f"# Code Review: {filename}\n")

    if review.get("summary"):
        lines.append(f"**Summary:** {review['summary']}")
    if review.get("score"):
        lines.append(f"**Quality Score:** {review['score']}/10\n")

    findings = review.get("findings", [])
    if not findings:
        lines.append("\n✅ No issues found!")
        return "\n".join(lines)

    # Group by severity
    for severity in ["critical", "warning", "info", "suggestion"]:
        items = [f for f in findings if f.get("severity") == severity]
        if items:
            emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵", "suggestion": "💡"}
            lines.append(f"\n## {emoji.get(severity, '')} {severity.upper()} ({len(items)})\n")
            for item in items:
                line_info = f" (line {item['line']})" if item.get("line") else ""
                lines.append(f"- **[{item.get('category', 'general')}]**{line_info}: {item['message']}")
                if item.get("code_snippet"):
                    lines.append(f"  ```\n  {item['code_snippet']}\n  ```")
                if item.get("fix"):
                    lines.append(f"  **Fix:**\n  ```\n  {item['fix']}\n  ```")

    return "\n".join(lines)


def format_findings_inline(review: dict, filename: str = "") -> str:
    """Format findings as inline comments."""
    lines = []
    if filename:
        lines.append(f"// Review: {filename}")

    findings = sorted(review.get("findings", []),
                      key=lambda f: f.get("line") or 0)

    for item in findings:
        severity = item.get("severity", "info").upper()
        line = item.get("line", "?")
        cat = item.get("category", "general")
        lines.append(f"// [{severity}] Line {line} ({cat}): {item['message']}")
        if item.get("fix"):
            lines.append(f"//   Fix: {item['fix']}")

    if not findings:
        lines.append("// ✅ No issues found")

    return "\n".join(lines)


def format_findings_json(review: dict, filename: str = "") -> str:
    """Format findings as JSON."""
    if filename:
        review["file"] = filename
    return json.dumps(review, indent=2)


def format_output(review: dict, fmt: str, filename: str = "") -> str:
    """Format review output in the specified format."""
    if fmt == "json":
        return format_findings_json(review, filename)
    elif fmt == "inline-comments":
        return format_findings_inline(review, filename)
    else:
        return format_findings_markdown(review, filename)


def review_file(filepath: str, fmt: str = "markdown", fix: bool = False,
                language: Optional[str] = None) -> str:
    """Review a single file."""
    filepath = os.path.abspath(filepath)
    if not os.path.isfile(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    lang = language or detect_language(filepath)
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
    except IOError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    if not code.strip():
        return "File is empty."

    print(f"Reviewing: {filepath} ({lang})...", file=sys.stderr)
    review = review_code(code, lang, filename=os.path.basename(filepath), fix=fix)
    return format_output(review, fmt, filename=filepath)


def review_diff(fmt: str = "markdown", fix: bool = False) -> str:
    """Review staged git diff."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--no-color"],
            capture_output=True, text=True, check=True)
        diff = result.stdout
    except subprocess.CalledProcessError:
        # Try unstaged diff
        try:
            result = subprocess.run(
                ["git", "diff", "--no-color"],
                capture_output=True, text=True, check=True)
            diff = result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error getting git diff: {e}", file=sys.stderr)
            sys.exit(1)

    if not diff.strip():
        return "No changes to review (no staged or unstaged changes)."

    prompt = f"""Review this git diff for bugs, security issues, performance problems, and style issues.
Return ONLY valid JSON:
{{
  "findings": [
    {{
      "severity": "critical|warning|info|suggestion",
      "category": "bug|security|performance|style|complexity",
      "file": "filename",
      "line": <line_number_or_null>,
      "message": "description"{', "fix": "suggested fix"' if fix else ''}
    }}
  ],
  "summary": "overall assessment",
  "score": <1-10>
}}

Diff:
```
{diff[:6000]}
```

JSON only:"""

    print("Reviewing git diff...", file=sys.stderr)
    response = ollama_generate(prompt)
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            review = json.loads(response[start:end])
            return format_output(review, fmt, filename="git diff")
    except json.JSONDecodeError:
        pass
    return "Unable to parse review results."


def review_repo(repo_path: str, fmt: str = "markdown", fix: bool = False) -> str:
    """Review repository structure and key files."""
    repo_path = os.path.abspath(repo_path)
    if not os.path.isdir(repo_path):
        print(f"Error: Directory not found: {repo_path}", file=sys.stderr)
        sys.exit(1)

    # Collect repo structure
    structure = []
    code_files = []
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv",
                 "dist", "build", ".tox", ".eggs", "target"}

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel_root = os.path.relpath(root, repo_path)
        for f in sorted(files):
            rel_path = os.path.join(rel_root, f) if rel_root != "." else f
            structure.append(rel_path)
            ext = Path(f).suffix.lower()
            if ext in LANGUAGE_EXTENSIONS:
                full_path = os.path.join(root, f)
                size = os.path.getsize(full_path)
                if size < 50000:  # Skip very large files
                    code_files.append(full_path)

    struct_text = "\n".join(structure[:100])
    prompt = f"""Review this repository structure for architectural issues, missing files, and organization.
Return ONLY valid JSON:
{{
  "findings": [
    {{
      "severity": "critical|warning|info|suggestion",
      "category": "architecture|organization|missing|config",
      "message": "description"
    }}
  ],
  "summary": "overall assessment",
  "score": <1-10>
}}

Repository structure:
```
{struct_text}
```

JSON only:"""

    print(f"Reviewing repo structure: {repo_path}...", file=sys.stderr)
    response = ollama_generate(prompt)

    all_findings = []
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            struct_review = json.loads(response[start:end])
            all_findings.extend(struct_review.get("findings", []))
    except json.JSONDecodeError:
        pass

    # Review up to 5 key files
    key_files = code_files[:5]
    for fpath in key_files:
        lang = detect_language(fpath)
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
            if code.strip():
                print(f"  Reviewing: {os.path.relpath(fpath, repo_path)}", file=sys.stderr)
                file_review = review_code(code, lang, os.path.basename(fpath), fix=fix)
                for finding in file_review.get("findings", []):
                    finding["file"] = os.path.relpath(fpath, repo_path)
                    all_findings.append(finding)
        except IOError:
            continue

    combined = {
        "findings": all_findings,
        "summary": f"Reviewed {len(key_files)} files in {repo_path}",
        "score": None
    }
    return format_output(combined, fmt, filename=repo_path)


def review_pr(fmt: str = "markdown", fix: bool = False) -> str:
    """Review changes between current branch and main."""
    # Detect default branch
    for branch in ["main", "master"]:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", branch],
            capture_output=True, text=True)
        if result.returncode == 0:
            base_branch = branch
            break
    else:
        base_branch = "main"

    try:
        result = subprocess.run(
            ["git", "diff", f"{base_branch}...HEAD", "--no-color"],
            capture_output=True, text=True, check=True)
        diff = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error getting PR diff: {e}", file=sys.stderr)
        sys.exit(1)

    if not diff.strip():
        return "No changes between current branch and main."

    prompt = f"""Review this pull request diff for bugs, security issues, performance, and style.
Return ONLY valid JSON:
{{
  "findings": [
    {{
      "severity": "critical|warning|info|suggestion",
      "category": "bug|security|performance|style|complexity",
      "file": "filename",
      "line": <line_or_null>,
      "message": "description"{', "fix": "suggested fix"' if fix else ''}
    }}
  ],
  "summary": "PR assessment",
  "score": <1-10>,
  "approval": "approve|request_changes|comment"
}}

PR Diff:
```
{diff[:8000]}
```

JSON only:"""

    print("Reviewing PR changes...", file=sys.stderr)
    response = ollama_generate(prompt)
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            review = json.loads(response[start:end])
            return format_output(review, fmt, filename="PR Review")
    except json.JSONDecodeError:
        pass
    return "Unable to parse PR review results."


def main():
    parser = argparse.ArgumentParser(
        description="AI Code Reviewer - Automated code review powered by AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file app.py
  %(prog)s --file src/main.rs --fix --format markdown
  %(prog)s --diff
  %(prog)s --repo ./my-project
  %(prog)s --pr --format json
  %(prog)s --file utils.js --language javascript
        """)

    parser.add_argument("--file", metavar="PATH", help="Review a single file")
    parser.add_argument("--diff", action="store_true", help="Review git diff (staged changes)")
    parser.add_argument("--repo", metavar="PATH", help="Review entire repo structure")
    parser.add_argument("--pr", action="store_true", help="Review PR (changes vs main)")
    parser.add_argument("--format", choices=["markdown", "json", "inline-comments"],
                        default="markdown", help="Output format (default: markdown)")
    parser.add_argument("--fix", action="store_true", help="Include suggested fixes")
    parser.add_argument("--language", help="Specify language (auto-detected by default)")
    parser.add_argument("--model", default=MODEL, help=f"Ollama model (default: {MODEL})")

    args = parser.parse_args()

    _apply_model(args.model)

    if not any([args.file, args.diff, args.repo, args.pr]):
        parser.print_help()
        sys.exit(1)

    if args.file:
        output = review_file(args.file, fmt=args.format, fix=args.fix, language=args.language)
    elif args.diff:
        output = review_diff(fmt=args.format, fix=args.fix)
    elif args.repo:
        output = review_repo(args.repo, fmt=args.format, fix=args.fix)
    elif args.pr:
        output = review_pr(fmt=args.format, fix=args.fix)

    print(output)


def _apply_model(model: str):
    """Apply model configuration."""
    global MODEL
    MODEL = model


if __name__ == "__main__":
    main()
