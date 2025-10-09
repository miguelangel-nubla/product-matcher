#!/bin/bash
set -e

# Check for mandatory environment variables
if [ -z "$VITE_API_URL" ]; then
    echo "ERROR: VITE_API_URL environment variable is required"
    exit 1
fi

echo "Setting VITE_API_URL to: $VITE_API_URL"

# Find the current hardcoded API URL in JS files and replace with the env var
# This assumes the pre-built image has some default URL that we need to replace
find /usr/share/nginx/html -name "*.js" -exec sed -i "s|__VITE_API_URL__|$VITE_API_URL|g" {} \;

# Start nginx
exec "$@"
