# Progress Notes

*Session-to-session handoff. Open work lives in GitHub Issues (`gh issue list --state open`). Markdown in `docs/` is the source of truth.*

## Current Status
- CLI (`main.py`), shared portfolio service, FastAPI backend (`server.py`), and Vite + React dashboard (`frontend/`) are implemented.
- The 2026-08 code review (`reviews/`, removed in #44) is fully addressed; remaining work is in GitHub issues, not local task files.
- History TTL in code is 30 days (`history.py`). Default portfolio size is 3 stable + 6 volatile.
- GitHub Actions CI (`.github/workflows/ci.yml`) runs ruff and pytest on Python 3.12 (backend job), plus frontend lint and build on Node 22, on PRs and pushes to `main`.
- Local Docker workspace and Cloud Agent environment setup are on `main`.
- Portfolio query/settings counts are bounded (`gt=0`, `le=PORTFOLIO_COUNT_MAX`) from #12.
- Pick explanations (#19) are on `main`: nested `explanation` on each generate pick, CLI Why these picks, dashboard MACD + paragraph.
- Mock fallback is display-only (#28): not cached, not written to history, flagged as `mock` in the service/API result with a notice in the CLI and dashboard.
- A symbol with no kline data is skipped for that run (#29); the circuit breaker trips only on broad failure (`KLINE_FAILURE_BREAKER_RATIO`).
- Generation is on request only (#30): `POST /api/portfolio/generate`; the dashboard loads the latest saved portfolio from the newest history record's `picks`. Records younger than `MIN_EVALUATION_AGE_SECONDS` (1 hour) stay pending.
- News matching (#31): coin names match in any case; tickers need `$` or upper case (`news.find_mentioned_symbols`).
- Settings (#32): `settings.py` is shared by the CLI and the API; `POST /api/settings` is a partial update; `variance_percentile` is bounded; `settings.json` is untracked.

## Open work
See GitHub Issues. Do not use `tasks.json`. Audit findings are sub-issues of #45 (#28–#44); the six bugs (#28–#33) are done; the reductions (#42–#44) are done; of the enhancements, #34 is done, #39 is done, #38 is done, #35 is done, #37 is done, #36 is in progress and #40, #41 remain. Product backlog: #20 vs BTC, #21 constraints, #22 hold vs regenerate, #23 daily digest (suggested order). Icebox: #13 database storage — do not implement until a multi-user requirement exists in `docs/context.md`.

## Last session
#28–#34 and #42–#44 merged via PRs #46–#55. #39 (CI for the frontend, consistent Python version) on branch `issue-39-ci-frontend-python`: new frontend CI job, Python job as a 3.10/3.12 matrix, pip and npm caching, ruff `I` and `B` rules enabled (imports re-sorted, no `B` findings). Docs state 3.10+ as the supported minimum.

#38 on branch `issue-38-frontend-api-url`: frontend calls relative `/api` (Vite proxy, target `DAILY_COIN_API_TARGET`; `VITE_API_BASE` override), fetches live in `frontend/src/api.js`, inline styles moved to `App.css`. `oxlint` is clean. CORS in `server.py` is kept (tested, needed for `VITE_API_BASE`).

#35 on branch `issue-35-api-errors-response-models`: generate returns 502 with `detail` on Binance failures, Pydantic response models in `schemas.py`, `serve --reload/--no-reload` (default off; Docker passes `--reload`), `allow_credentials` removed. Dashboard shows the 502 `detail`. Same PR raises the Python minimum to 3.12: single `Backend` CI job (was a 3.10/3.12 matrix), ruff `target-version = "py312"`.

#37 on branch `issue-37-dashboard-sentiment-evaluations`: dashboard shows sentiment impacts, a Just Evaluated panel (average per portfolio), the score breakdown on pick cards, and settings/history load failures as warnings. Frontend only.

#36 on branch `issue-36-sentiment-all-headlines`: sentiment scored over `NEWS_ANALYZE_LIMIT` (50) headlines, `NEWS_DISPLAY_LIMIT` (5) shown; UTC timestamps via `calendar.timegm`; feed failures logged. Live check: averaging over more headlines dilutes single strong ones (neutral 0.0 headlines count), so impacts can drop; whether to skip neutral headlines is an open question.
