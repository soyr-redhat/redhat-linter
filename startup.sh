#!/bin/bash

# Exit on error
set -e

echo "Red Hat Editorial Auditor - Initialization"

# 1. Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing now..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the environment if uv was just installed
    source $HOME/.cargo/env
fi

# 2. Sync dependencies (creates .venv and installs from pyproject.toml)
echo "Syncing dependencies..."
uv sync

# 3. Create required directories
mkdir -p guides

# 4. Ollama Infrastructure Check
echo "Checking Ollama connection..."
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "Error: Ollama is not running."
    echo "Please start the Ollama application and try again."
    exit 1
fi

# 5. Model Management
REQUIRED_MODEL="qwen2.5:3b"
echo "Verifying local model: $REQUIRED_MODEL"

# Check if model exists in local library
if ! ollama list | grep -q "$REQUIRED_MODEL"; then
    echo "Model '$REQUIRED_MODEL' not found. Pulling now..."
    ollama pull "$REQUIRED_MODEL"
    echo "Model successfully installed."
else
    echo "Model '$REQUIRED_MODEL' is already available."
fi

# 6. Launch Application
echo "Starting Streamlit..."
uv run streamlit run app.py
