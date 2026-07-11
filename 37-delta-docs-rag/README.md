# DELTA Documentation AI (RAG)

A specialized RAG (Retrieval-Augmented Generation) system for querying DELTA/OmniCheckout work documents using AI.

## Features

- **Intelligent Indexing**: Indexes all documents from DELTA_Unzipped, Summary, and DELTA_Related directories
- **Incremental Re-indexing**: Only processes new or changed files (uses file hashing)
- **Natural Language Queries**: Ask questions about your codebase in plain English
- **Component Explanations**: Get detailed breakdowns of any system component
- **Architecture Diagrams**: Generate text-based diagrams of system flows
- **Document Search**: Fast semantic search across all indexed documents
- **Onboarding Guide**: Auto-generate onboarding materials from existing docs
- **Incident Analysis**: AI-powered root cause analysis based on documentation

## Tech Stack

- **Vector Store**: ChromaDB (persistent, local)
- **Embeddings**: Ollama nomic-embed-text
- **Generation**: Ollama llama3.2
- **Language**: Python 3.10+

## Setup

```bash
# Activate the virtual environment
source ~/Downloads/AI/.venv/bin/activate

# Ensure Ollama is running with required models
ollama pull nomic-embed-text
ollama pull llama3.2

# Index your documents (first time)
./delta_rag.py --index
```

## Usage

```bash
# Index documents (incremental - only new/changed files)
./delta_rag.py --index

# Ask questions about your system
./delta_rag.py --query 'how does the checkout flow work?'
./delta_rag.py --query 'what happens when a payment fails?'

# Get component explanations
./delta_rag.py --explain 'OmniCheckout'
./delta_rag.py --explain 'payment service'

# Generate architecture diagrams
./delta_rag.py --diagram 'payment flow'
./delta_rag.py --diagram 'order processing pipeline'

# Search across documents
./delta_rag.py --search 'error handling'
./delta_rag.py --search 'retry logic'

# Generate onboarding guide
./delta_rag.py --onboarding

# Incident analysis
./delta_rag.py --incident 'customers getting timeout errors during checkout'
./delta_rag.py --incident 'payment service returning 500 errors'
```

## Configuration

Edit `config.json` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `paths_to_index` | 3 paths | Directories to scan for documents |
| `chunk_size` | 1000 | Characters per chunk |
| `chunk_overlap` | 200 | Overlap between chunks |
| `top_k_results` | 5 | Number of results to retrieve |
| `embedding_model` | nomic-embed-text | Ollama embedding model |
| `generation_model` | llama3.2 | Ollama generation model |

## How It Works

1. **Indexing**: Scans configured directories for supported file types (.md, .txt, .json, .py, .java, etc.)
2. **Chunking**: Splits documents into overlapping chunks for better retrieval
3. **Embedding**: Converts chunks to vectors using nomic-embed-text
4. **Storage**: Stores vectors in ChromaDB with metadata (source file, chunk position)
5. **Query**: Converts your question to a vector, finds similar chunks
6. **Generation**: Passes relevant chunks + your question to llama3.2 for a synthesized answer
7. **Sources**: Shows which documents contributed to the answer

## Indexed Paths

- `~/Downloads/DELTA_Unzipped/` - Full DELTA documentation and code
- `~/Downloads/Summary/` - OmniCheckout summaries
- `~/Downloads/DELTA_Related/` - Related architecture documents
