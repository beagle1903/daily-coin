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
Opened PR for #12 (`issue-12-bound-portfolio-query-params`): bound `/api/portfolio/generate` query params and `SettingsModel` counts (`gt=0`, `le=PORTFOLIO_COUNT_MAX` = 50). Tests cover rejected out-of-range values. Auth and rate limiting remain #11.
