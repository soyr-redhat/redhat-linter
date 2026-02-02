#!/bin/bash

# Exit on error
set -e

IMAGE_NAME="redhat-linter"
CONTAINER_PORT=8501

echo "Red Hat Editorial Auditor - Container Bootstrapper"

# 1. Detect Container Engine
if command -v podman &> /dev/null; then
    ENGINE="podman"
elif command -v docker &> /dev/null; then
    ENGINE="docker"
else
    echo "Error: No container engine (Podman or Docker) found."
    exit 1
fi

echo "Using container engine: $ENGINE"

# 2. Build the Image
echo "Building container image: $IMAGE_NAME..."
$ENGINE build -t $IMAGE_NAME .

# 3. Determine Host Gateway
# On Mac/Windows, 'host.docker.internal' is standard. 
# We map this so the container can talk to the host's Ollama.
GATEWAY="host.docker.internal"

echo "Starting container on http://localhost:$CONTAINER_PORT..."
echo "Bridging to Ollama on host via $GATEWAY..."

# 4. Run the Container
# --add-host maps the gateway so the app can reach the host machine
# -e OLLAMA_HOST tells app.py where to look
$ENGINE run -it --rm \
    -p $CONTAINER_PORT:$CONTAINER_PORT \
    --add-host=$GATEWAY:host-gateway \
    -e OLLAMA_HOST=http://$GATEWAY:11434 \
    $IMAGE_NAME
