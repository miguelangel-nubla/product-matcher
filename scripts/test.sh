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
docker compose -f docker-compose.yml -f docker-compose.test.yml build backend
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d db backend

# Run tests
docker compose -f docker-compose.yml -f docker-compose.test.yml exec -T backend bash scripts/tests-start.sh "$@"

# Clean up (optional - can be controlled with --no-cleanup flag)
if [[ "$*" != *"--no-cleanup"* ]]; then
    docker compose -f docker-compose.yml -f docker-compose.test.yml down -v --remove-orphans
fi
