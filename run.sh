#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo "🚀 Starting School-In-A-Box WhatsApp Automated System"
echo "=========================================================="

# Check and initialize database
python3 backend/seed_data.py

echo "Starting FastAPI Server on http://localhost:8000 ..."
exec python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
