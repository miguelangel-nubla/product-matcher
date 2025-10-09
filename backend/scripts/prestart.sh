#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Create backends config
if [ ! -f "/app/config/backends.yaml" ]; then
    echo "Creating backends.yaml from example..."
    cp /app/config/backends.example.yaml /app/config/backends.yaml
fi

# Run migrations
alembic upgrade head

# Create initial data in DB
python app/initial_data.py
