#!/usr/bin/env python3
"""Auto Documentation Generator - AI-powered code documentation using Ollama."""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests

# Configuration
OLLAMA_URL = "http://localhost:11434"
MODEL = "codellama"
FALLBACK_MODEL = "llama3.2"
SCRIPT_DIR = Path(__file__).parent
TEMPLATES_DIR = SCRIPT_DIR / "templates"

SUPPORTED_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript (React)",
    ".tsx": "TypeScript (React)",
    ".java": "Java",
    ".sh": "Bash",
    ".bash": "Bash",
}


class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def query_ollama(prompt, model=MODEL):
    """Query Ollama for AI documentation."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}Error: Cannot connect to Ollama at {OLLAMA_URL}")
        print(f"Make sure Ollama is running: ollama serve{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        if model == MODEL:
            print(f"{Colors.YELLOW}Falling back to {FALLBACK_MODEL}...{Colors.RESET}")
            return query_ollama(prompt, model=FALLBACK_MODEL)
        print(f"{Colors.RED}Error querying Ollama: {e}{Colors.RESET}")
        return ""


def detect_functions_python(content):
    """Detect Python functions and classes."""
    items = []
    for match in re.finditer(r'^(class|def)\s+(\w+)\s*\(([^)]*)\)', content, re.MULTILINE):
        kind = match.group(1)
        name = match.group(2)
        params = match.group(3)
        # Get docstring
        pos = match.end()
        doc_match = re.search(r'"""(.*?)"""', content[pos:pos+500], re.DOTALL)
        doc = doc_match.group(1).strip() if doc_match else ""
        items.append({"type": kind, "name": name, "params": params, "doc": doc})
    return items


def detect_functions_js(content):
    """Detect JavaScript/TypeScript functions and classes."""
    items = []
    # function declarations
    for match in re.finditer(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', content):
        items.append({"type": "function", "name": match.group(1), "params": match.group(2), "doc": ""})
    # arrow functions assigned to const/let
    for match in re.finditer(r'(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>', content):
        items.append({"type": "function", "name": match.group(1), "params": match.group(2), "doc": ""})
    # classes
    for match in re.finditer(r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?', content):
        items.append({"type": "class", "name": match.group(1), "params": "", "doc": ""})
    # Express-style endpoints
    for match in re.finditer(r'(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)', content):
        items.append({"type": "endpoint", "name": f"{match.group(1).upper()} {match.group(2)}", "params": "", "doc": ""})
    return items


def detect_functions_java(content):
    """Detect Java classes and methods."""
    items = []
    for match in re.finditer(r'(?:public|private|protected)\s+(?:static\s+)?(?:class|interface)\s+(\w+)', content):
        items.append({"type": "class", "name": match.group(1), "params": "", "doc": ""})
    for match in re.finditer(
        r'(?:public|private|protected)\s+(?:static\s+)?(?:\w+(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)', content
    ):
        if match.group(1) not in ("if", "while", "for", "switch"):
            items.append({"type": "method", "name": match.group(1), "params": match.group(2), "doc": ""})
    # Spring endpoints
    for match in re.finditer(r'@(?:Get|Post|Put|Delete|Patch)Mapping\s*\(\s*[\'"]?([^\'")\s]+)', content):
        items.append({"type": "endpoint", "name": match.group(1), "params": "", "doc": ""})
    return items


def detect_functions_bash(content):
    """Detect Bash functions."""
    items = []
    for match in re.finditer(r'^(?:function\s+)?(\w+)\s*\(\s*\)', content, re.MULTILINE):
        items.append({"type": "function", "name": match.group(1), "params": "", "doc": ""})
    return items


def detect_items(content, language):
    """Detect code items based on language."""
    if language == "Python":
        return detect_functions_python(content)
    elif language in ("JavaScript", "TypeScript", "JavaScript (React)", "TypeScript (React)"):
        return detect_functions_js(content)
    elif language == "Java":
        return detect_functions_java(content)
    elif language == "Bash":
        return detect_functions_bash(content)
    return []


def document_file(filepath, output_format="markdown"):
    """Generate documentation for a single file."""
    filepath = Path(filepath).resolve()
    if not filepath.exists():
        print(f"{Colors.RED}File not found: {filepath}{Colors.RESET}")
        return ""
    ext = filepath.suffix.lower()
    language = SUPPORTED_EXTENSIONS.get(ext)
    if not language:
        print(f"{Colors.YELLOW}Unsupported file type: {ext}{Colors.RESET}")
        return ""
    print(f"{Colors.CYAN}Documenting: {filepath.name} ({language}){Colors.RESET}")
    content = filepath.read_text(errors="ignore")
    # Truncate very large files
    if len(content) > 8000:
        content = content[:8000] + "\n... (truncated)"
    items = detect_items(content, language)
    prompt = f"""Generate documentation for this {language} file.
File: {filepath.name}

Code:
```{language.lower()}
{content}
```

Detected items: {json.dumps(items, indent=2)}

Generate comprehensive documentation including:
1. File overview/purpose
2. Each function/class with description, parameters, return values
3. Usage examples where appropriate
4. Any notable dependencies or configurations

Format as {'markdown' if output_format == 'markdown' else 'HTML'}."""

    doc = query_ollama(prompt)
    return doc


def document_repo(repo_path, output_format="markdown", output_path=None):
    """Generate documentation for an entire repository."""
    repo_path = Path(repo_path).resolve()
    if not repo_path.exists():
        print(f"{Colors.RED}Repository path not found: {repo_path}{Colors.RESET}")
        return
    print(f"{Colors.BOLD}📚 Documenting repository: {repo_path.name}{Colors.RESET}\n")
    # Find supported files
    files = []
    skip_dirs = {"node_modules", "__pycache__", ".git", "venv", ".venv", "target", "build", "dist", ".next"}
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for f in filenames:
            fp = Path(root) / f
            if fp.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(fp)
    if not files:
        print(f"{Colors.YELLOW}No supported files found.{Colors.RESET}")
        return
    print(f"{Colors.GREEN}Found {len(files)} documentable files{Colors.RESET}\n")
    # Generate docs
    all_docs = []
    for fp in files:
        doc = document_file(fp, output_format)
        if doc:
            rel_path = fp.relative_to(repo_path)
            all_docs.append(f"## {rel_path}\n\n{doc}")
            print()
    # Combine
    ext = ".md" if output_format == "markdown" else ".html"
    output = output_path or (repo_path / f"DOCUMENTATION{ext}")
    full_doc = f"# Documentation: {repo_path.name}\n\n"
    full_doc += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    full_doc += f"---\n\n"
    full_doc += "\n\n---\n\n".join(all_docs)
    Path(output).write_text(full_doc)
    print(f"\n{Colors.GREEN}✓ Documentation saved to: {output}{Colors.RESET}")


def generate_readme(repo_path):
    """Generate or update README.md for a repository."""
    repo_path = Path(repo_path).resolve()
    print(f"{Colors.CYAN}Generating README for: {repo_path.name}{Colors.RESET}")
    # Gather project info
    files = []
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", ".git", "venv")]
        for f in filenames[:50]:
            rel = Path(root).relative_to(repo_path) / f
            files.append(str(rel))
    # Check for config files
    configs = []
    for cfg in ["package.json", "requirements.txt", "pom.xml", "Cargo.toml", "Makefile", "Dockerfile"]:
        if (repo_path / cfg).exists():
            configs.append(cfg)
    # Read main entry point if found
    main_content = ""
    for entry in ["main.py", "app.py", "index.js", "index.ts", "src/main.py", "src/index.ts"]:
        if (repo_path / entry).exists():
            main_content = (repo_path / entry).read_text(errors="ignore")[:3000]
            break
    template = (TEMPLATES_DIR / "readme.md").read_text() if (TEMPLATES_DIR / "readme.md").exists() else ""
    prompt = f"""Generate a comprehensive README.md for this project.

Project: {repo_path.name}
Files: {json.dumps(files[:30])}
Config files: {configs}
{'Main file content:' + main_content[:2000] if main_content else ''}
{'Template structure:' + template if template else ''}

Include: project title, description, features, installation, usage, project structure, and license placeholder.
Use proper markdown formatting."""

    readme = query_ollama(prompt)
    output = repo_path / "README.md"
    output.write_text(readme)
    print(f"{Colors.GREEN}✓ README.md generated: {output}{Colors.RESET}")


def generate_api_docs(repo_path, output_format="markdown", output_path=None):
    """Generate API documentation from code."""
    repo_path = Path(repo_path).resolve()
    print(f"{Colors.CYAN}Generating API documentation...{Colors.RESET}")
    # Find endpoint files
    endpoints = []
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", ".git")]
        for f in filenames:
            fp = Path(root) / f
            if fp.suffix.lower() in SUPPORTED_EXTENSIONS:
                content = fp.read_text(errors="ignore")
                if any(kw in content for kw in ["@app.", "@router.", "app.get", "app.post", "@GetMapping",
                                                   "@PostMapping", "express", "fastapi", "flask"]):
                    endpoints.append((fp, content[:4000]))
    if not endpoints:
        print(f"{Colors.YELLOW}No API endpoints detected.{Colors.RESET}")
        return
    print(f"{Colors.GREEN}Found {len(endpoints)} files with endpoints{Colors.RESET}")
    all_apis = []
    for fp, content in endpoints:
        prompt = f"""Extract and document all API endpoints from this code.
File: {fp.name}
```
{content}
```
For each endpoint list: HTTP method, path, parameters, request body, response format, description.
Format as {'markdown' if output_format == 'markdown' else 'HTML'} table or list."""
        doc = query_ollama(prompt)
        if doc:
            all_apis.append(f"### {fp.relative_to(repo_path)}\n\n{doc}")
    ext = ".md" if output_format == "markdown" else ".html"
    output = output_path or (repo_path / f"API_DOCS{ext}")
    full = f"# API Documentation\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    full += "\n\n---\n\n".join(all_apis)
    Path(output).write_text(full)
    print(f"{Colors.GREEN}✓ API docs saved: {output}{Colors.RESET}")


def generate_architecture(repo_path, output_format="markdown", output_path=None):
    """Generate architecture overview."""
    repo_path = Path(repo_path).resolve()
    print(f"{Colors.CYAN}Generating architecture overview...{Colors.RESET}")
    # Build directory tree
    tree_lines = []
    skip = {"node_modules", "__pycache__", ".git", "venv", ".venv", "target", "build", "dist"}
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = sorted([d for d in dirs if d not in skip and not d.startswith(".")])
        level = len(Path(root).relative_to(repo_path).parts)
        if level > 3:
            continue
        indent = "  " * level
        tree_lines.append(f"{indent}{Path(root).name}/")
        for f in sorted(filenames)[:10]:
            tree_lines.append(f"{indent}  {f}")
    tree = "\n".join(tree_lines[:60])
    # Check for configs
    config_content = ""
    for cfg in ["package.json", "requirements.txt", "pom.xml", "docker-compose.yml", "Dockerfile"]:
        cfg_path = repo_path / cfg
        if cfg_path.exists():
            config_content += f"\n--- {cfg} ---\n{cfg_path.read_text(errors='ignore')[:1000]}\n"
    template = (TEMPLATES_DIR / "architecture.md").read_text() if (TEMPLATES_DIR / "architecture.md").exists() else ""
    prompt = f"""Generate an architecture overview for this project.

Directory structure:
{tree}

Config files:
{config_content[:3000] if config_content else 'None found'}

{'Template:' + template if template else ''}

Include: high-level overview, component descriptions, data flow, tech stack, deployment notes.
Format as {'markdown' if output_format == 'markdown' else 'HTML'}."""

    doc = query_ollama(prompt)
    ext = ".md" if output_format == "markdown" else ".html"
    output = output_path or (repo_path / f"ARCHITECTURE{ext}")
    Path(output).write_text(doc)
    print(f"{Colors.GREEN}✓ Architecture doc saved: {output}{Colors.RESET}")


def update_docs(repo_path, output_format="markdown"):
    """Only document new/changed files using git diff."""
    repo_path = Path(repo_path).resolve()
    print(f"{Colors.CYAN}Checking for changed files...{Colors.RESET}")
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1"],
            cwd=repo_path, capture_output=True, text=True
        )
        if result.returncode != 0:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path, capture_output=True, text=True
            )
            changed = [line[3:].strip() for line in result.stdout.strip().split("\n") if line]
        else:
            changed = result.stdout.strip().split("\n")
    except FileNotFoundError:
        print(f"{Colors.RED}Git not found. Cannot detect changes.{Colors.RESET}")
        return
    changed_supported = [f for f in changed if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS]
    if not changed_supported:
        print(f"{Colors.GREEN}No supported files changed.{Colors.RESET}")
        return
    print(f"{Colors.GREEN}Found {len(changed_supported)} changed files{Colors.RESET}\n")
    docs = []
    for f in changed_supported:
        fp = repo_path / f
        if fp.exists():
            doc = document_file(fp, output_format)
            if doc:
                docs.append(f"## {f}\n\n{doc}")
    if docs:
        ext = ".md" if output_format == "markdown" else ".html"
        output = repo_path / f"CHANGES_DOC{ext}"
        full = f"# Documentation Update\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        full += "\n\n---\n\n".join(docs)
        output.write_text(full)
        print(f"\n{Colors.GREEN}✓ Updated docs saved: {output}{Colors.RESET}")


def main():
    parser = argparse.ArgumentParser(description="Auto Documentation Generator - AI-powered code docs")
    parser.add_argument("--repo", type=str, help="Generate docs for entire repository")
    parser.add_argument("--file", type=str, help="Document a single file")
    parser.add_argument("--readme", type=str, help="Generate README.md for repo path")
    parser.add_argument("--api", type=str, help="Generate API documentation for repo path")
    parser.add_argument("--architecture", type=str, help="Generate architecture overview")
    parser.add_argument("--format", type=str, choices=["markdown", "html"], default="markdown")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--update", type=str, help="Document only changed files (git diff)")
    args = parser.parse_args()

    if not any([args.repo, args.file, args.readme, args.api, args.architecture, args.update]):
        parser.print_help()
        sys.exit(0)

    if args.file:
        doc = document_file(args.file, args.format)
        if doc:
            if args.output:
                Path(args.output).write_text(doc)
                print(f"{Colors.GREEN}✓ Saved to: {args.output}{Colors.RESET}")
            else:
                print(f"\n{doc}")
    elif args.repo:
        document_repo(args.repo, args.format, args.output)
    elif args.readme:
        generate_readme(args.readme)
    elif args.api:
        generate_api_docs(args.api, args.format, args.output)
    elif args.architecture:
        generate_architecture(args.architecture, args.format, args.output)
    elif args.update:
        update_docs(args.update, args.format)


if __name__ == "__main__":
    main()
