# Progress Notes

*Session-to-session handoff. Open work lives in GitHub Issues (`gh issue list --state open`). Markdown in `docs/` is the source of truth.*

## Current Status
- CLI (`main.py`), shared portfolio service, FastAPI backend (`server.py`), and Vite + React dashboard (`frontend/`) are implemented.
- P0–P2 findings in `reviews/SUMMARY.md` are largely done. Remaining product items are GitHub issues, not local task files.
- History TTL in code is 30 days (`history.py`). Default portfolio size is 3 stable + 6 volatile.
- GitHub Actions CI (`.github/workflows/ci.yml`) runs ruff and pytest on PRs and pushes to `main`.
- Local Docker workspace and Cloud Agent environment setup are on `main`.
- Portfolio query/settings counts are bounded (`gt=0`, `le=PORTFOLIO_COUNT_MAX`) from #12.

## Open work
See GitHub Issues. Do not use `tasks.json`. Next icebox item is #13 (database storage); do not implement until a multi-user requirement exists in `docs/context.md`.

## Last session
On `issue-11-api-auth-rate-limit`: FastAPI `/api/*` routes require `X-API-Key` matching `DAILY_COIN_API_KEY` (fail closed if unset). `/api/portfolio/generate` is limited to 10 requests/minute via slowapi. Dashboard sends `VITE_DAILY_COIN_API_KEY` and surfaces 401/429. Query/settings bounds were already on `main` from #12.
