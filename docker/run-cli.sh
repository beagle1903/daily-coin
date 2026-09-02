#!/usr/bin/env bash
set -euo pipefail
cd /workspace
exec python main.py run "$@"
