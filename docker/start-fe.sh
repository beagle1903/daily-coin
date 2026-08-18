#!/usr/bin/env bash
set -euo pipefail

cd /workspace

if [[ ! -x "$(command -v python)" ]]; then
  echo "Python is missing from the image PATH." >&2
  exit 1
fi

if [[ ! -d /workspace/frontend/node_modules/vite ]]; then
  echo "Installing frontend dependencies into the node_modules volume..."
  (cd /workspace/frontend && npm ci)
fi

echo "Starting Daily Coin API on 0.0.0.0:8000..."
python main.py serve --host 0.0.0.0 --port 8000 &
API_PID=$!

cleanup() {
  kill "${API_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting Vite frontend on 0.0.0.0:5173..."
cd /workspace/frontend
npm run dev -- --host 0.0.0.0 --port 5173
