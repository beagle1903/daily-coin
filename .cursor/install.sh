#!/usr/bin/env bash
# Idempotent bootstrap for the daily-coin CLI, API server, and frontend.
set -euo pipefail

cd "$(dirname "$0")/.."

# The default image ships python3 but may omit the venv/ensurepip module.
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y --no-install-recommends python3-venv python3.12-venv
fi

# Python backend + CLI dependencies inside a project-local virtualenv.
if [ ! -x venv/bin/python ]; then
  python3 -m venv venv
fi
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# Frontend dependencies (clean, lockfile-pinned install).
(cd frontend && npm ci)
