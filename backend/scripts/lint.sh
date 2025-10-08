#!/usr/bin/env bash

set -e
set -x

# If --fix is passed, run ruff format without --check to actually format files
# Otherwise, run with --check to only validate formatting
if [[ "$1" == "--fix" ]]; then
    uv run mypy app
    uv run ruff check app --fix
    uv run ruff format app
else
    uv run mypy app
    uv run ruff check app
    uv run ruff format app --check
fi
