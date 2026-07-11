#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""
Fine-Tune Data Preparation Tool

Scans directories for text files and converts them into JSONL training data
(instruction/input/output format) suitable for fine-tuning LLMs.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional, Set

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"


class DataStats:
    """Track statistics about processed data."""

    def __init__(self):
        self.total_files = 0
        self.processed_files = 0
        self.skipped_files = 0
        self.total_pairs = 0
        self.duplicates_removed = 0
        self.invalid_removed = 0
        self.total_tokens_approx = 0
        self.source_types: Dict[str, int] = {}
        self.file_types: Dict[str, int] = {}

    def summary(self) -> str:
        lines = [
            "",
            "╔══════════════════════════════════════════════════╗",
            "║           Data Preparation Statistics            ║",
            "╠══════════════════════════════════════════════════╣",
            f"║  📁 Total files scanned:     {self.total_files:>8}            ║",
            f"║  ✅ Files processed:          {self.processed_files:>8}            ║",
            f"║  ⏭  Files skipped:            {self.skipped_files:>8}            ║",
            f"║  📝 Training pairs generated: {self.total_pairs:>8}            ║",
            f"║  🔄 Duplicates removed:       {self.duplicates_removed:>8}            ║",
            f"║  ❌ Invalid entries removed:   {self.invalid_removed:>8}            ║",
            f"║  📊 Approx total tokens:      {self.total_tokens_approx:>8}            ║",
            "╠══════════════════════════════════════════════════╣",
            "║  File Types:                                     ║",
        ]
        for ext, count in sorted(self.file_types.items()):
            lines.append(f"║    {ext:<10}: {count:>6}                            ║")
        lines.append("╚══════════════════════════════════════════════════╝")
        return "\n".join(lines)


def approximate_tokens(text: str) -> int:
    """Rough token count approximation (words * 1.3)."""
    return int(len(text.split()) * 1.3)


def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    # Remove excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove null bytes
    text = text.replace("\x00", "")
    # Normalize unicode
    text = text.encode("utf-8", errors="ignore").decode("utf-8")
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def is_valid_pair(pair: dict) -> bool:
    """Validate a training pair has sufficient content."""
    instruction = pair.get("instruction", "").strip()
    output = pair.get("output", "").strip()

    if not instruction or not output:
        return False
    if len(instruction) < 10:
        return False
    if len(output) < 20:
        return False
    # Check for garbage content
    if output.count("�") > len(output) * 0.1:
        return False
    return True


def content_hash(pair: dict) -> str:
    """Generate a hash for deduplication."""
    content = f"{pair.get('instruction', '')}{pair.get('output', '')}"
    return hashlib.md5(content.encode()).hexdigest()


def scan_files(directory: Path, extensions: Optional[Set[str]] = None) -> Generator[Path, None, None]:
    """Recursively scan directory for text files."""
    if extensions is None:
        extensions = {".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
                      ".rst", ".csv", ".html", ".xml", ".log", ".sh", ".bash"}

    for root, dirs, files in os.walk(directory):
        # Skip hidden directories and common non-content dirs
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   {"node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build"}]
        for file in sorted(files):
            filepath = Path(root) / file
            if filepath.suffix.lower() in extensions:
                yield filepath


def extract_from_chat_history(text: str, filepath: Path) -> List[dict]:
    """Extract instruction/output pairs from chat-style content."""
    pairs = []

    # Pattern: look for Q&A, User/Assistant, or prompt/response patterns
    patterns = [
        (r"(?:User|Human|Q):\s*(.+?)(?:\n)(?:Assistant|AI|A):\s*(.+?)(?=(?:User|Human|Q):|$)",
         re.DOTALL | re.IGNORECASE),
        (r"(?:###\s*(?:Instruction|Question|Prompt)):\s*(.+?)(?:###\s*(?:Response|Answer|Output)):\s*(.+?)(?=###|$)",
         re.DOTALL | re.IGNORECASE),
    ]

    for pattern, flags in patterns:
        matches = re.findall(pattern, text, flags)
        for instruction, output in matches:
            pair = {
                "instruction": clean_text(instruction),
                "input": "",
                "output": clean_text(output),
                "source": str(filepath),
            }
            if is_valid_pair(pair):
                pairs.append(pair)

    # If no pattern matched, treat the whole file as a single example
    if not pairs and len(text.strip()) > 100:
        pairs.append({
            "instruction": f"Continue the following conversation or text from {filepath.name}",
            "input": text[:500].strip(),
            "output": text[500:].strip() if len(text) > 500 else text.strip(),
            "source": str(filepath),
        })

    return pairs


def extract_from_documents(text: str, filepath: Path) -> List[dict]:
    """Extract pairs from documents (summarize, explain, etc.)."""
    pairs = []

    # Split into sections by headers
    sections = re.split(r"\n#{1,3}\s+", text)

    for section in sections:
        section = section.strip()
        if len(section) < 100:
            continue

        # Create summarization pair
        pairs.append({
            "instruction": "Summarize the following text concisely.",
            "input": section[:2000],
            "output": section[:500] if len(section) > 500 else section,
            "source": str(filepath),
        })

        # Create explanation pair
        if len(section) > 200:
            pairs.append({
                "instruction": f"Explain the key points from this document section about {filepath.stem.replace('_', ' ')}.",
                "input": section[:1500],
                "output": section[:800],
                "source": str(filepath),
            })

    return pairs


def extract_from_code(text: str, filepath: Path) -> List[dict]:
    """Extract pairs from code files."""
    pairs = []
    ext = filepath.suffix.lower()

    # Extract functions/classes with docstrings
    if ext == ".py":
        # Python functions
        func_pattern = r"(def\s+\w+\([^)]*\).*?:)\s*\n\s*\"\"\"(.*?)\"\"\"(.*?)(?=\ndef |\nclass |\Z)"
        matches = re.findall(func_pattern, text, re.DOTALL)
        for signature, docstring, body in matches:
            pairs.append({
                "instruction": f"Write a Python function that: {clean_text(docstring)}",
                "input": "",
                "output": clean_text(f"{signature}\n    \"\"\"{docstring}\"\"\"{body}"),
                "source": str(filepath),
            })

        # Class definitions
        class_pattern = r"(class\s+\w+.*?:)\s*\n\s*\"\"\"(.*?)\"\"\"(.*?)(?=\nclass |\Z)"
        matches = re.findall(class_pattern, text, re.DOTALL)
        for signature, docstring, body in matches:
            pairs.append({
                "instruction": f"Write a Python class that: {clean_text(docstring)}",
                "input": "",
                "output": clean_text(f"{signature}\n    \"\"\"{docstring}\"\"\"{body[:1500]}"),
                "source": str(filepath),
            })
    else:
        # Generic code: explain what the code does
        if len(text) > 100:
            pairs.append({
                "instruction": f"Explain what this {ext.lstrip('.')} code does and how it works.",
                "input": text[:2000],
                "output": f"This {ext.lstrip('.')} file ({filepath.name}) contains code that implements functionality. Here's a breakdown of the key components:\n\n{text[:1000]}",
                "source": str(filepath),
            })

    # If code file has comments, extract Q&A from them
    comment_blocks = re.findall(r"#\s*TODO:?\s*(.+)", text) if ext == ".py" else []
    for todo in comment_blocks[:5]:
        pairs.append({
            "instruction": f"Implement the following TODO: {todo.strip()}",
            "input": f"File: {filepath.name}",
            "output": f"Here's an implementation for: {todo.strip()}",
            "source": str(filepath),
        })

    return pairs


def extract_from_custom(text: str, filepath: Path) -> List[dict]:
    """Extract pairs using generic chunking approach."""
    pairs = []
    # Chunk the text into manageable pieces
    chunk_size = 1000
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    for i, chunk in enumerate(chunks[:20]):  # Limit to 20 chunks per file
        chunk = clean_text(chunk)
        if len(chunk) < 50:
            continue
        pairs.append({
            "instruction": f"Continue or respond to the following text (from {filepath.name}, part {i+1}).",
            "input": chunk[:200],
            "output": chunk[200:] if len(chunk) > 200 else chunk,
            "source": str(filepath),
        })

    return pairs


EXTRACTORS = {
    "chat_history": extract_from_chat_history,
    "documents": extract_from_documents,
    "code": extract_from_code,
    "custom": extract_from_custom,
}


def process_directory(input_dir: Path, source: str, stats: DataStats) -> List[dict]:
    """Process all files in a directory and extract training pairs."""
    all_pairs = []
    seen_hashes: Set[str] = set()
    extractor = EXTRACTORS.get(source, extract_from_custom)

    print(f"\n🔍 Scanning: {input_dir}")
    print(f"📋 Source type: {source}")
    print(f"{'─'*50}")

    for filepath in scan_files(input_dir):
        stats.total_files += 1
        ext = filepath.suffix.lower()
        stats.file_types[ext] = stats.file_types.get(ext, 0) + 1

        try:
            # Read file
            text = filepath.read_text(encoding="utf-8", errors="ignore")
            if len(text.strip()) < 50:
                stats.skipped_files += 1
                continue

            # Extract pairs
            pairs = extractor(text, filepath)

            # Deduplicate and validate
            valid_pairs = []
            for pair in pairs:
                if not is_valid_pair(pair):
                    stats.invalid_removed += 1
                    continue
                h = content_hash(pair)
                if h in seen_hashes:
                    stats.duplicates_removed += 1
                    continue
                seen_hashes.add(h)
                valid_pairs.append(pair)
                stats.total_tokens_approx += approximate_tokens(pair["output"])

            all_pairs.extend(valid_pairs)
            stats.processed_files += 1

            if valid_pairs:
                print(f"  ✓ {filepath.name}: {len(valid_pairs)} pairs")

        except Exception as e:
            stats.skipped_files += 1
            print(f"  ✗ {filepath.name}: {e}")

    stats.total_pairs = len(all_pairs)
    return all_pairs


def save_jsonl(pairs: List[dict], output_path: Path):
    """Save training pairs as JSONL file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for pair in pairs:
            # Output format: instruction, input, output (standard Alpaca format)
            entry = {
                "instruction": pair["instruction"],
                "input": pair.get("input", ""),
                "output": pair["output"],
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\n💾 Saved {len(pairs)} training pairs to: {output_path}")
    file_size = output_path.stat().st_size
    print(f"   File size: {file_size / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser(
        description="Fine-Tune Data Preparation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input ./my_data --source documents
  %(prog)s --input ./chats --source chat_history --format
  %(prog)s --input ./code_repo --source code
  %(prog)s --input ./mixed_content --source custom

Source Types:
  chat_history  - Extracts Q&A pairs from conversation logs
  documents     - Creates summarization/explanation pairs from docs
  code          - Extracts code examples with docstring explanations
  custom        - Generic chunking approach for any text
        """,
    )
    parser.add_argument("--input", "-i", type=str, required=True,
                        help="Directory to scan for training data")
    parser.add_argument("--format", "-f", action="store_true",
                        help="Convert to JSONL format (instruction/input/output pairs)")
    parser.add_argument("--source", "-s", type=str, default="custom",
                        choices=["chat_history", "documents", "code", "custom"],
                        help="Source type for extraction strategy")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output JSONL file path (default: data/training.jsonl)")
    parser.add_argument("--max-pairs", type=int, default=10000,
                        help="Maximum number of training pairs to generate")

    args = parser.parse_args()

    input_dir = Path(args.input).expanduser().resolve()
    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        sys.exit(1)
    if not input_dir.is_dir():
        print(f"Error: Path is not a directory: {input_dir}")
        sys.exit(1)

    output_path = Path(args.output) if args.output else DATA_DIR / "training.jsonl"

    print("╔══════════════════════════════════════════════════╗")
    print("║       Fine-Tune Data Preparation Tool            ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"\n⚙  Configuration:")
    print(f"   Input:  {input_dir}")
    print(f"   Source: {args.source}")
    print(f"   Output: {output_path}")
    print(f"   Max pairs: {args.max_pairs}")

    # Process
    stats = DataStats()
    pairs = process_directory(input_dir, args.source, stats)

    # Limit pairs
    if len(pairs) > args.max_pairs:
        pairs = pairs[:args.max_pairs]
        print(f"\n⚠  Truncated to {args.max_pairs} pairs (use --max-pairs to adjust)")

    # Save
    if pairs:
        if args.format or True:  # Always save as JSONL
            save_jsonl(pairs, output_path)
    else:
        print("\n⚠  No valid training pairs were generated.")
        print("   Try a different --source type or check your input directory.")

    # Print statistics
    print(stats.summary())


if __name__ == "__main__":
    main()
