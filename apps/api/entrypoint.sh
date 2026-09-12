#!/bin/sh
set -e

mkdir -p /app/data

if [ ! -f "/app/data/gridmind.db" ]; then
  echo "No existing database found -- running synthetic data seed..."
  python -m seed.run_seed
else
  echo "Existing database found -- skipping seed (delete the api_data volume to force a reseed)."
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
