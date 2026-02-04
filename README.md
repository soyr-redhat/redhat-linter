this linter is an editorial tool for auditing technical content against Red Hat brand voice standards. This application uses Ollama and Model Context Protocol (MCP) to provide real-time, rule-based rewriting suggestions.

## Prerequisites

- **Ollama**: Must be installed and running locally. [Download here](https://ollama.com).
- **Python 3.10+**: Managed automatically via the startup script.
- **Container Engine**: Podman (recommended) or Docker for containerized runs.

## Quick Start

The project is designed for a "zero-config" experience. Simply clone and run the native startup script:

```bash
git clone https://github.com/soyr-redhat/redhat-linter.git
cd redhat-linter
./startup.sh
```

### Running with Podman/Docker
If you prefer to run RHEA in an isolated environment, use the container bootstrapper. This handles the network bridge required to talk to Ollama on your host machine:

```bash
./start_container.sh
```
## Features

### Configuration Sidebar
The sidebar is the central hub for RHEA's intelligence:
* **Model Selection**: Pick your preferred Ollama model. 
    * **Note**: You must use a model that supports **Tool Calling** (e.g., llama3.1, mistral, or command-r). Without tool calling, the agent cannot query the style guides.
* **Knowledge Base (RAG)**: Manage your style guides directly.
    * Upload any .md file to the Knowledge Base via the UI. 
    * The MCP server dynamically indexes these rules, allowing the Auditor to cite them during the review.

### Side-by-Side Review
RHEA provides a GitHub-style diff view to compare original text (red) with proposed rewrites (green).
* **Accept/Reject**: Choose to commit or ignore suggestions line-by-line.
* **Bulk Actions**: Use the "Accept All" or "Reject All" buttons to speed up large document reviews.
* **Paper Trail**: Expand the "Sources" on any suggestion to see exactly which style guide rule triggered the AI's feedback.

## Technical Architecture

1.  **Streamlit Frontend**: Manages the UI and session state for your edits.
2.  **LangGraph Agent**: Orchestrates the auditing logic and decides when to search for rules.
3.  **MCP Server**: A background process that provides the Agent with access to the local guides/ directory.
4.  **Local LLM**: Powered by Ollama for privacy-first, local inference.
