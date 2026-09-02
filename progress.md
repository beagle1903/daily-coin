# Progress Notes

*Session-to-session handoff. Open work lives in GitHub Issues (`gh issue list --state open`). Markdown in `docs/` is the source of truth.*

## Current Status
- CLI (`main.py`), shared portfolio service, FastAPI backend (`server.py`), and Vite + React dashboard (`frontend/`) are implemented.
- P0–P2 findings in `reviews/SUMMARY.md` are largely done. Remaining product items are GitHub issues, not local task files.
- History TTL in code is 30 days (`history.py`). Default portfolio size is 3 stable + 6 volatile.
- GitHub Actions CI (`.github/workflows/ci.yml`) runs ruff and pytest on PRs and pushes to `main` (landed in #14).
- Local Docker workspace and Cloud Agent environment setup are on `main`.

## Open work
See GitHub Issues. Do not use `tasks.json`.

## Last session
Merged `main` into `issue-8-workflow` so the wait-for-CI rule in `AGENTS.md` is backed by the workflow from #14. Docker workspace stays ADR 005; GitHub Issues/PRs is ADR 006.
