#!/usr/bin/env bash
set -e

# Activate virtual environment if available
source .venv/bin/activate 2>/dev/null || true

exec uvicorn main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --reload
