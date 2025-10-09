#!/usr/bin/env bash

set -e
set -x

# Set config path for tests to use local config file
export BACKENDS_CONFIG_PATH="../config/backends.yaml"

uv run coverage run -m pytest tests/
uv run coverage report
uv run coverage html --title "${@-coverage}"
