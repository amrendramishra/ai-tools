#!/usr/bin/env python3
"""
DELTA Documentation AI (RAG) - Specialized RAG system for DELTA/OmniCheckout work documents.
Uses ChromaDB for vector storage, Ollama nomic-embed-text for embeddings, and llama3.2 for generation.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import chromadb
import requests

# ─── Configuration ───────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.json"


def load_config() -> dict:
    """Load configuration from config.json."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


CONFIG = load_config()
OLLAMA_URL = CONFIG["ollama_url"]
EMBEDDING_MODEL = CONFIG["embedding_model"]
GENERATION_MODEL = CONFIG["generation_model"]
CHUNK_SIZE = CONFIG["chunk_size"]
CHUNK_OVERLAP = CONFIG["chunk_overlap"]
TOP_K = CONFIG["top_k_results"]
CHROMA_DIR = str(SCRIPT_DIR / CONFIG["chroma_persist_dir"])
COLLECTION_NAME = CONFIG["collection_name"]
INDEX_STATE_FILE = str(SCRIPT_DIR / CONFIG["index_state_file"])
SUPPORTED_EXTENSIONS = set(CONFIG["supported_extensions"])
PATHS_TO_INDEX = [os.path.expanduser(p) for p in CONFIG["paths_to_index"]]


# ─── Embedding & Generation ─────────────────────────────────────────────────

def get_embedding(text: str) -> list[float]:
    """Get embedding from Ollama nomic-embed-text model."""
    resp = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBEDDING_MODEL, "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Get embeddings for a batch of texts."""
    embeddings = []
    for text in texts:
        embeddings.append(get_embedding(text))
    return embeddings


def generate_response(prompt: str, system: str = "") -> str:
    """Generate response using Ollama llama3.2."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": GENERATION_MODEL, "messages": messages, "stream": False},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


# ─── Document Processing ─────────────────────────────────────────────────────

def file_hash(filepath: str) -> str:
    """Compute MD5 hash of a file for change detection."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def read_file_content(filepath: str) -> Optional[str]:
    """Read file content with encoding fallback."""
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(filepath, encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, IOError):
            continue
    return None


def discover_files(paths: list[str]) -> list[str]:
    """Discover all indexable files in the given paths."""
    files = []
    for base_path in paths:
        if not os.path.exists(base_path):
            print(f"  ⚠️  Path not found: {base_path}")
            continue
        if os.path.isfile(base_path):
            if Path(base_path).suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(base_path)
        else:
            for root, _, filenames in os.walk(base_path):
                for fname in filenames:
                    fpath = os.path.join(root, fname)
                    if Path(fpath).suffix.lower() in SUPPORTED_EXTENSIONS:
                        files.append(fpath)
    return files


# ─── Index State Management ──────────────────────────────────────────────────

def load_index_state() -> dict:
    """Load the index state (file hashes for incremental indexing)."""
    if os.path.exists(INDEX_STATE_FILE):
        with open(INDEX_STATE_FILE) as f:
            return json.load(f)
    return {}


def save_index_state(state: dict):
    """Save index state."""
    with open(INDEX_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ─── ChromaDB Operations ─────────────────────────────────────────────────────

def get_collection():
    """Get or create the ChromaDB collection."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def index_documents():
    """Index all DELTA/OmniCheckout documents with incremental support."""
    print("🔍 Discovering files to index...")
    files = discover_files(PATHS_TO_INDEX)
    print(f"   Found {len(files)} files across {len(PATHS_TO_INDEX)} paths")

    state = load_index_state()
    collection = get_collection()

    new_count = 0
    updated_count = 0
    skipped_count = 0
    total_chunks = 0

    for i, filepath in enumerate(files):
        current_hash = file_hash(filepath)
        rel_path = filepath

        # Skip unchanged files
        if filepath in state and state[filepath] == current_hash:
            skipped_count += 1
            continue

        # Read and chunk the file
        content = read_file_content(filepath)
        if not content or not content.strip():
            continue

        chunks = chunk_text(content)
        if not chunks:
            continue

        # Remove old entries for this file if updating
        if filepath in state:
            old_ids = [f"{filepath}_chunk_{j}" for j in range(500)]
            try:
                collection.delete(where={"source": filepath})
            except Exception:
                pass
            updated_count += 1
        else:
            new_count += 1

        # Generate embeddings and add to collection
        print(f"  [{i+1}/{len(files)}] Indexing: {os.path.basename(filepath)} ({len(chunks)} chunks)")

        batch_size = 10
        for batch_start in range(0, len(chunks), batch_size):
            batch_chunks = chunks[batch_start:batch_start + batch_size]
            batch_ids = [f"{filepath}_chunk_{batch_start + j}" for j in range(len(batch_chunks))]
            batch_metadatas = [
                {
                    "source": filepath,
                    "filename": os.path.basename(filepath),
                    "chunk_index": batch_start + j,
                    "total_chunks": len(chunks),
                }
                for j in range(len(batch_chunks))
            ]

            try:
                embeddings = get_embeddings_batch(batch_chunks)
                collection.add(
                    ids=batch_ids,
                    embeddings=embeddings,
                    documents=batch_chunks,
                    metadatas=batch_metadatas,
                )
                total_chunks += len(batch_chunks)
            except Exception as e:
                print(f"    ⚠️  Error indexing batch: {e}")
                continue

        state[filepath] = current_hash

    save_index_state(state)

    print(f"\n✅ Indexing complete!")
    print(f"   New files: {new_count}")
    print(f"   Updated files: {updated_count}")
    print(f"   Skipped (unchanged): {skipped_count}")
    print(f"   Total chunks indexed: {total_chunks}")
    print(f"   Collection size: {collection.count()} documents")


# ─── Query Operations ────────────────────────────────────────────────────────

def search_docs(query: str, top_k: int = TOP_K) -> list[dict]:
    """Search documents using vector similarity."""
    collection = get_collection()
    if collection.count() == 0:
        print("⚠️  No documents indexed. Run with --index first.")
        return []

    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = []
    for i in range(len(results["documents"][0])):
        docs.append({
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return docs


def format_sources(docs: list[dict]) -> str:
    """Format source information for display."""
    sources = []
    seen = set()
    for doc in docs:
        source = doc["metadata"]["source"]
        if source not in seen:
            seen.add(source)
            filename = doc["metadata"]["filename"]
            sources.append(f"  • {filename} ({source})")
    return "\n".join(sources)


def query_docs(query: str):
    """Ask a question about the codebase/system."""
    print(f"🔎 Querying: {query}\n")
    docs = search_docs(query)
    if not docs:
        return

    context = "\n\n---\n\n".join([d["content"] for d in docs])

    system_prompt = """You are a knowledgeable AI assistant specialized in DELTA and OmniCheckout systems at Amazon.
Answer questions based on the provided documentation context. Be specific, accurate, and cite relevant details.
If the context doesn't contain enough information to fully answer, say so and provide what you can."""

    prompt = f"""Context from documentation:
{context}

Question: {query}

Provide a comprehensive answer based on the context above. Include specific details, component names, and technical information where available."""

    response = generate_response(prompt, system_prompt)
    print(f"📖 Answer:\n{response}\n")
    print(f"\n📄 Sources:\n{format_sources(docs)}")


def explain_component(component: str):
    """Get detailed explanation of a component."""
    print(f"📚 Explaining: {component}\n")
    docs = search_docs(f"{component} architecture design overview how it works")
    if not docs:
        return

    context = "\n\n---\n\n".join([d["content"] for d in docs])

    system_prompt = """You are an expert technical writer explaining Amazon's DELTA and OmniCheckout system components.
Provide clear, detailed explanations suitable for onboarding engineers."""

    prompt = f"""Context from documentation:
{context}

Provide a detailed explanation of "{component}" covering:
1. **What it is** - Overview and purpose
2. **How it works** - Architecture and key mechanisms
3. **Key components** - Sub-components and their roles
4. **Dependencies** - What it depends on and what depends on it
5. **Common patterns** - How developers typically interact with it
6. **Key considerations** - Performance, reliability, gotchas"""

    response = generate_response(prompt, system_prompt)
    print(f"{response}\n")
    print(f"\n📄 Sources:\n{format_sources(docs)}")


def generate_diagram(topic: str):
    """Generate a text-based architecture diagram."""
    print(f"📐 Generating diagram for: {topic}\n")
    docs = search_docs(f"{topic} architecture flow components interaction")
    if not docs:
        return

    context = "\n\n---\n\n".join([d["content"] for d in docs])

    system_prompt = """You are a technical architect creating ASCII/text-based architecture diagrams.
Use box-drawing characters, arrows, and clear labeling to create readable diagrams."""

    prompt = f"""Context from documentation:
{context}

Create a detailed text-based architecture diagram for "{topic}". Include:
- Components and services involved
- Data flow directions (use arrows: →, ←, ↓, ↑)
- Key interactions and protocols
- Use box-drawing characters for components:
  ┌─────────────┐
  │  Component  │
  └─────────────┘

Make it comprehensive but readable. Add a legend if needed."""

    response = generate_response(prompt, system_prompt)
    print(f"{response}\n")
    print(f"\n📄 Sources:\n{format_sources(docs)}")


def search_across_docs(query: str):
    """Search across all documents and display results."""
    print(f"🔍 Searching for: {query}\n")
    docs = search_docs(query, top_k=10)
    if not docs:
        return

    print(f"Found {len(docs)} relevant sections:\n")
    for i, doc in enumerate(docs, 1):
        score = 1 - doc["distance"]  # Convert distance to similarity
        filename = doc["metadata"]["filename"]
        source = doc["metadata"]["source"]
        snippet = doc["content"][:200].replace("\n", " ")
        print(f"  {i}. [{score:.2f}] {filename}")
        print(f"     {source}")
        print(f"     {snippet}...")
        print()


def generate_onboarding():
    """Generate an onboarding guide from docs."""
    print("📋 Generating onboarding guide...\n")

    topics = [
        "system overview architecture",
        "getting started setup development environment",
        "key services components",
        "checkout flow payment processing",
        "common operations deployment",
        "debugging troubleshooting",
    ]

    all_context = []
    for topic in topics:
        docs = search_docs(topic, top_k=3)
        for d in docs:
            all_context.append(d["content"])

    context = "\n\n---\n\n".join(all_context[:15])

    system_prompt = """You are creating a comprehensive onboarding guide for a new engineer joining the DELTA/OmniCheckout team at Amazon.
Structure the guide logically, from high-level overview to specific details."""

    prompt = f"""Context from team documentation:
{context}

Create a comprehensive onboarding guide covering:
1. **System Overview** - What DELTA/OmniCheckout is and its role
2. **Architecture** - High-level architecture and key services
3. **Key Concepts** - Important terminology and concepts
4. **Development Setup** - How to get started
5. **Common Workflows** - Day-to-day development tasks
6. **Key Contacts & Resources** - Where to find help
7. **First Week Checklist** - What to accomplish in the first week

Make it practical and actionable."""

    response = generate_response(prompt, system_prompt)
    print(f"{response}\n")


def analyze_incident(description: str):
    """AI suggests root cause based on docs."""
    print(f"🚨 Analyzing incident: {description}\n")
    docs = search_docs(f"error failure troubleshooting {description}")
    if not docs:
        return

    context = "\n\n---\n\n".join([d["content"] for d in docs])

    system_prompt = """You are a senior engineer doing incident analysis for Amazon's DELTA/OmniCheckout systems.
Based on documentation and known patterns, suggest likely root causes and remediation steps."""

    prompt = f"""Context from documentation:
{context}

Incident description: {description}

Provide an incident analysis:
1. **Likely Root Causes** (ranked by probability)
2. **Affected Components** - What services/components are likely involved
3. **Diagnostic Steps** - How to confirm the root cause
4. **Immediate Mitigation** - Quick fixes to restore service
5. **Long-term Fix** - Proper resolution
6. **Related Past Issues** - Similar patterns from documentation
7. **Prevention** - How to prevent recurrence"""

    response = generate_response(prompt, system_prompt)
    print(f"{response}\n")
    print(f"\n📄 Sources:\n{format_sources(docs)}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="DELTA Documentation AI (RAG) - Query your work documents with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --index                              Index all documents
  %(prog)s --query 'how does checkout work?'    Ask a question
  %(prog)s --explain 'OmniCheckout'             Explain a component
  %(prog)s --diagram 'payment flow'             Generate architecture diagram
  %(prog)s --search 'error handling'            Search across docs
  %(prog)s --onboarding                         Generate onboarding guide
  %(prog)s --incident 'timeout in payment svc'  Analyze an incident
        """,
    )

    parser.add_argument("--index", action="store_true", help="Index all DELTA/OmniCheckout documents")
    parser.add_argument("--query", type=str, help="Ask a question about your codebase/system")
    parser.add_argument("--explain", type=str, help="Get detailed explanation of a component")
    parser.add_argument("--diagram", type=str, help="Generate text-based architecture diagram")
    parser.add_argument("--search", type=str, help="Search across all documents")
    parser.add_argument("--onboarding", action="store_true", help="Generate onboarding guide from docs")
    parser.add_argument("--incident", type=str, help="AI suggests root cause based on docs")

    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        sys.exit(1)

    # Check Ollama connectivity
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
    except Exception:
        print("❌ Cannot connect to Ollama at", OLLAMA_URL)
        print("   Make sure Ollama is running: ollama serve")
        sys.exit(1)

    if args.index:
        index_documents()
    elif args.query:
        query_docs(args.query)
    elif args.explain:
        explain_component(args.explain)
    elif args.diagram:
        generate_diagram(args.diagram)
    elif args.search:
        search_across_docs(args.search)
    elif args.onboarding:
        generate_onboarding()
    elif args.incident:
        analyze_incident(args.incident)


if __name__ == "__main__":
    main()
