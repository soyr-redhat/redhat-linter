#!/bin/bash

# Exit on error
set -e

echo "Red Hat Editorial Auditor - Initialization"

# 1. Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing now..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# 2. Sync dependencies (creates .venv if missing)
echo "Syncing dependencies..."
uv sync

# 3. Create guides directory if it doesn't exist
mkdir -p guides

# 4. Check for Ollama
echo "Checking Ollama connection..."
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "Ollama is not running! Please start the Ollama app."
else
    echo "Ollama found."
fi

# 5. Launch Streamlit
echo "Launching Auditor UI..."
uv run streamlit run app.py
