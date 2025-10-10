#!/bin/bash
# Simple benchmark runner script for CI integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🔬 Running Product Matching Benchmarks"
echo "Working directory: $BACKEND_DIR"

cd "$BACKEND_DIR"

# Ensure we're using the right Python environment
PYTHON_CMD="uv run python3"

# Set default format to table for interactive use, CI for automated
FORMAT=${1:-table}

echo "Running benchmarks..."
PYTHONUNBUFFERED=1 $PYTHON_CMD tests/benchmarks/benchmark_runner.py --format "$FORMAT"

echo "Benchmarks completed successfully!"
