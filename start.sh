#!/bin/bash
# Start the Portfolio backend
cd "$(dirname "$0")"

# Load env if .env exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
