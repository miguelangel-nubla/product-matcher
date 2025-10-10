#!/bin/bash
set -e

echo "Starting backend with integrated prestart..."

# Run the existing prestart script
bash scripts/prestart.sh

echo "Prestart completed. Starting main application..."

# Start the main application
exec "$@"
