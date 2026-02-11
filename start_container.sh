#!/bin/bash

# Exit on error
set -e

IMAGE_NAME="redhat-linter"
CONTAINER_PORT=8501

echo "W.I.P Editorial Auditor - Container Bootstrapper"
echo "======================================================"
echo ""
echo "NOTE: First run will download Ollama and the llama3.1:8b model (~5GB)."
echo "This model provides excellent tool-calling for style guide integration."
echo "Download may take 10-15 minutes depending on your internet connection."
echo "Subsequent runs will be much faster."
echo ""

# 1. Detect Container Engine
if command -v podman &> /dev/null; then
    ENGINE="podman"
elif command -v docker &> /dev/null; then
    ENGINE="docker"
else
    echo "Error: No container engine (Podman or Docker) found."
    echo "Please install Docker or Podman to continue."
    exit 1
fi

echo "Using container engine: $ENGINE"

# 2. Build the Image
echo "Building container image: $IMAGE_NAME..."
$ENGINE build -t $IMAGE_NAME .

echo ""
echo "Starting container..."
echo "Access the app at: http://localhost:$CONTAINER_PORT"
echo ""

# 3. Run the Container
# Fully self-contained - Ollama runs inside the container
$ENGINE run -it --rm \
    -p $CONTAINER_PORT:$CONTAINER_PORT \
    $IMAGE_NAME
