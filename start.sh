#!/bin/bash
set -e

echo "Starting action server..."
rasa run actions --port 5055 &

echo "Starting rasa server..."
rasa run --enable-api --cors "*" --port ${PORT:-5005}
