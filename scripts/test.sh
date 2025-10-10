#! /usr/bin/env bash

# Exit in case of error
set -e
set -x

# Clean up any existing containers
docker compose -f docker-compose.yml -f docker-compose.test.yml down -v --remove-orphans

# Clean up __pycache__ files on Linux
if [ $(uname -s) = "Linux" ]; then
    echo "Remove __pycache__ files"
    sudo find . -type d -name __pycache__ -exec rm -r {} \+ 2>/dev/null || true
fi

# Build and start services
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d db backend

# Wait for backend health
BACKEND_CONTAINER=$(docker compose -f docker-compose.yml -f docker-compose.test.yml ps -q backend)
TIMEOUT=60
echo "⏳ Waiting up to ${TIMEOUT}s for backend to become healthy..."

for ((i=0; i<TIMEOUT; i++)); do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$BACKEND_CONTAINER" 2>/dev/null || echo "unknown")
    if [ "$STATUS" == "healthy" ]; then
        echo "✅ Backend is healthy!"
        break
    elif [ "$STATUS" == "unhealthy" ]; then
        echo "❌ Backend became unhealthy!"
        docker logs "$BACKEND_CONTAINER"
        exit 1
    fi
    sleep 1
done

if [ "$STATUS" != "healthy" ]; then
    echo "⏰ Timeout waiting for backend to become healthy!"
    docker logs "$BACKEND_CONTAINER"
    exit 1
fi

# Run tests
cd backend && uv run bash scripts/test.sh; cd ..

# Clean up (optional - can be controlled with --no-cleanup flag)
if [[ "$*" != *"--no-cleanup"* ]]; then
    docker compose -f docker-compose.yml -f docker-compose.test.yml down -v --remove-orphans
fi
