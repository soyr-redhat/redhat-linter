# Use a lightweight Python image
FROM python:3.12-slim

# Install system dependencies and Ollama
RUN apt-get update && apt-get install -y \
    curl zstd \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen

# Copy the rest of the application
COPY . .

# Ensure guides directory exists
RUN mkdir -p guides

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting Ollama service..."\n\
ollama serve > /tmp/ollama.log 2>&1 &\n\
OLLAMA_PID=$!\n\
echo "Ollama PID: $OLLAMA_PID"\n\
\n\
# Wait for Ollama to be ready\n\
echo "Waiting for Ollama to start..."\n\
for i in {1..30}; do\n\
  if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then\n\
    echo "Ollama is ready!"\n\
    break\n\
  fi\n\
  sleep 1\n\
done\n\
\n\
# Pull the required model if not present\n\
echo "Checking for model qwen2.5:3b..."\n\
if ! ollama list | grep -q "qwen2.5:3b"; then\n\
  echo "Pulling qwen2.5:3b model (this may take a few minutes on first run)..."\n\
  ollama pull qwen2.5:3b\n\
  echo "Model downloaded successfully!"\n\
else\n\
  echo "Model qwen2.5:3b already available."\n\
fi\n\
\n\
# Start Streamlit\n\
echo "Starting Streamlit..."\n\
exec uv run streamlit run app.py --server.address 0.0.0.0\n\
' > /app/container_start.sh && chmod +x /app/container_start.sh

# Expose Streamlit and Ollama ports
EXPOSE 8501
EXPOSE 11434

# Run the startup script
CMD ["/app/container_start.sh"]
