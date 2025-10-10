#!/usr/bin/env bash

set -e
set -x

# If --fix is passed, run ruff format without --check to actually format files
# Otherwise, run with --check to only validate formatting
if [[ "$1" == "--fix" ]]; then
    mypy app
    ruff check app --fix
    ruff format app
else
    mypy app
    ruff check app
    ruff format app --check
fi
