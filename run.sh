#!/usr/bin/env bash
# Start StudyBuddy. Requires only Python 3.10+ (standard library only — no pip install).
set -euo pipefail
cd "$(dirname "$0")"
export PORT="${PORT:-8000}"
export HOST="${HOST:-127.0.0.1}"
echo "Starting StudyBuddy on http://${HOST}:${PORT}  (Ctrl+C to stop)"
exec python3 -m app.server
