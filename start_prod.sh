#!/bin/bash
# Production start (no reload, 4 workers)
cd "$(dirname "$0")"
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
