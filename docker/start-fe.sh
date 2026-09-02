#!/usr/bin/env bash
set -euo pipefail

cd /workspace

if [[ ! -x "$(command -v python)" ]]; then
  echo "Python is missing from the image PATH." >&2
  exit 1
fi

LOCKFILE=/workspace/frontend/package-lock.json
STAMP=/workspace/frontend/node_modules/.package-lock.sha256
need_ci=0
if [[ ! -d /workspace/frontend/node_modules/vite ]]; then
  need_ci=1
elif [[ ! -f "${STAMP}" ]]; then
  need_ci=1
else
  current="$(sha256sum "${LOCKFILE}" | awk '{print $1}')"
  stored="$(cat "${STAMP}")"
  if [[ "${current}" != "${stored}" ]]; then
    need_ci=1
  fi
fi

if [[ "${need_ci}" -eq 1 ]]; then
  echo "Installing frontend dependencies into the node_modules volume..."
  (cd /workspace/frontend && npm ci)
  sha256sum "${LOCKFILE}" | awk '{print $1}' > "${STAMP}"
fi

echo "Starting Daily Coin API on 0.0.0.0:8000..."
python main.py serve --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "Starting Vite frontend on 0.0.0.0:5173..."
cd /workspace/frontend
npm run dev -- --host 0.0.0.0 --port 5173 &
FE_PID=$!

cleanup() {
  trap - EXIT INT TERM
  kill "${API_PID}" "${FE_PID}" 2>/dev/null || true
  wait "${API_PID}" "${FE_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait -n "${API_PID}" "${FE_PID}"
status=$?
exit "${status}"
