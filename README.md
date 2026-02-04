this linter is an editorial tool for auditing technical content against W.I.P brand voice standards. This application uses Ollama and Model Context Protocol (MCP) to provide real-time, rule-based rewriting suggestions.

## Prerequisites

### Local Installation
- **Ollama**: Must be installed and running locally. [Download here](https://ollama.com).
- **Python 3.12+**: Managed automatically via the startup script.

### Container Installation
- **Container Engine**: Podman (recommended) or Docker
- **No other prerequisites** - Ollama and all dependencies are bundled inside the container

## Quick Start

### Option 1: Local Installation (Recommended)
The project is designed for a "zero-config" experience. Simply clone and run the startup script:

```bash
git clone https://github.com/soyr-redhat/redhat-linter.git
cd redhat-linter
./startup.sh
```

This will:
- Install `uv` package manager if needed
- Install all Python dependencies
- Check Ollama is running
- Pull the `qwen2.5:3b` model (fast, optimized for editorial tasks)
- Start the Streamlit app at http://localhost:8501

### Option 2: Container (Fully Automated)
For a completely isolated environment with zero dependencies:

```bash
./start_container.sh
```

**First run will take 5-10 minutes** as it downloads:
- Ollama (~500MB)
- The `qwen2.5:3b` model (~2GB)
- All Python dependencies

**Subsequent runs start in seconds** - everything is cached inside the container.
## Features

### Configuration Sidebar
The sidebar is the central hub for WIPEA's intelligence:
* **Model Selection**: Pick your preferred Ollama model (defaults to `qwen2.5:3b` for optimal speed)
    * **Note**: You must use a model that supports **Tool Calling** (e.g., qwen2.5, llama3.1, mistral, or command-r). Without tool calling, the agent cannot query the style guides.
* **Knowledge Base (Intelligent RAG)**: Manage your style guides with advanced semantic search
    * Upload documents in multiple formats: **PDF, DOCX, Markdown, HTML, TXT**
    * Powered by **docling** for intelligent document parsing
    * **Vector embeddings** with ChromaDB for semantic search (not just keyword matching)
    * Returns only the most relevant guideline chunks, ranked by relevance
    * Automatically cached for instant subsequent searches

### Side-by-Side Review
WIPEA provides a GitHub-style diff view to compare original text (red) with proposed rewrites (green).
* **Accept/Reject**: Choose to commit or ignore suggestions line-by-line.
* **Bulk Actions**: Use the "Accept All" or "Reject All" buttons to speed up large document reviews.
* **Paper Trail**: Expand the "Sources" on any suggestion to see exactly which style guide rule triggered the AI's feedback.

## Technical Architecture

1.  **Streamlit Frontend**: Manages the UI and session state for your edits.
2.  **LangGraph Agent**: Orchestrates the auditing logic and decides when to search for rules.
3.  **MCP Server with RAG**: A background process that provides intelligent semantic search over style guides
    - **Docling**: Parses PDFs, DOCX, and other formats into clean markdown
    - **Vector Embeddings**: Uses `sentence-transformers/all-MiniLM-L6-v2` for semantic understanding
    - **ChromaDB**: Local vector database for fast similarity search
    - Returns only the top-3 most relevant chunks instead of entire documents
4.  **Local LLM**: Powered by Ollama for privacy-first, local inference (defaults to `qwen2.5:3b` for speed).
