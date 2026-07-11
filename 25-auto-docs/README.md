# Auto Documentation Generator

AI-powered documentation generator that understands your code and produces comprehensive docs.

## Features

- **Full Repo Documentation**: Document an entire codebase at once
- **Single File Docs**: Quick docs for individual files
- **README Generation**: Auto-generate professional README.md
- **API Documentation**: Extract and document endpoints
- **Architecture Overview**: High-level system design docs
- **Multi-Language Support**: Python, JavaScript, TypeScript, Java, Bash
- **Change Detection**: Only document modified files (git diff)
- **Code Intelligence**: Detects functions, classes, endpoints, configs
- **Templates**: Customizable documentation templates

## Requirements

- Python 3.8+
- Ollama running at localhost:11434
- Models: `codellama` (primary), `llama3.2` (fallback)
- `requests` library
- Git (for --update feature)

## Usage

```bash
# Document entire repository
./auto_docs.py --repo ~/myproject

# Document single file
./auto_docs.py --file src/main.py
./auto_docs.py --file app.js --output docs/app.md

# Generate README
./auto_docs.py --readme ~/myproject

# Generate API docs
./auto_docs.py --api ~/myproject --format markdown

# Generate architecture overview
./auto_docs.py --architecture ~/myproject

# Document only changed files
./auto_docs.py --update ~/myproject

# HTML output
./auto_docs.py --repo ~/myproject --format html --output docs/
```

## Supported Languages

| Language | Extensions | Detects |
|----------|-----------|---------|
| Python | .py | functions, classes, decorators |
| JavaScript | .js, .jsx | functions, arrow functions, Express endpoints |
| TypeScript | .ts, .tsx | functions, interfaces, classes |
| Java | .java | classes, methods, Spring endpoints |
| Bash | .sh, .bash | functions |

## Templates

Customize documentation output by editing templates in `templates/`:
- `readme.md` - README structure
- `api.md` - API documentation format
- `architecture.md` - Architecture overview format

## Output

Generated documentation is saved as:
- `DOCUMENTATION.md` (--repo)
- `API_DOCS.md` (--api)
- `ARCHITECTURE.md` (--architecture)
- `CHANGES_DOC.md` (--update)
- `README.md` (--readme)
