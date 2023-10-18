#!/usr/bin/env bash
set -euo pipefail

# One-time setup: build dataset, import, apply migrations.
teb dataset build
teb dataset import benchmark/data/v1.0.0/examples.jsonl || true
alembic upgrade head

case "${1:-api}" in
  api)
    exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000
    ;;
  ui)
    exec streamlit run app/ui/app.py --server.address 0.0.0.0 --server.port 8501 \
      --server.headless true
    ;;
  cli)
    shift
    exec teb "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
