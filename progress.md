# Progress Notes

*Session-to-session handoff. Open work lives in GitHub Issues (`gh issue list --state open`). Markdown in `docs/` is the source of truth.*

## Current Status
- CLI (`main.py`), shared portfolio service, FastAPI backend (`server.py`), and Vite + React dashboard (`frontend/`) are implemented.
- P0–P2 findings in `reviews/SUMMARY.md` are largely done. Remaining product items are GitHub issues, not local task files.
- History TTL in code is 30 days (`history.py`). Default portfolio size is 3 stable + 6 volatile.
- GitHub Actions CI (`.github/workflows/ci.yml`) runs ruff and pytest on PRs and pushes to `main`.
- Local Docker workspace and Cloud Agent environment setup are on `main`.
- Portfolio query/settings counts are bounded (`gt=0`, `le=PORTFOLIO_COUNT_MAX`) from #12.
- Pick explanations (#19) are on `main`: nested `explanation` on each generate pick, CLI Why these picks, dashboard MACD + paragraph.
- Mock fallback is display-only (#28): not cached, not written to history, flagged as `mock` in the service/API result with a notice in the CLI and dashboard.
- A symbol with no kline data is skipped for that run (#29); the circuit breaker trips only on broad failure (`KLINE_FAILURE_BREAKER_RATIO`).
- Generation is on request only (#30): `POST /api/portfolio/generate`; the dashboard loads the latest saved portfolio from the newest history record's `picks`. Records younger than `MIN_EVALUATION_AGE_SECONDS` (1 hour) stay pending.
- News matching (#31): coin names match in any case; tickers need `$` or upper case (`news.find_mentioned_symbols`).
- Settings (#32): `settings.py` is shared by the CLI and the API; `POST /api/settings` is a partial update; `variance_percentile` is bounded; `settings.json` is untracked.

## Open work
See GitHub Issues. Do not use `tasks.json`. Audit findings are sub-issues of #45 (#28–#44); the six bugs (#28–#33) are done; next come the reductions (#43, #44; #42 in progress) and the remaining enhancements. Product backlog: #20 vs BTC, #21 constraints, #22 hold vs regenerate, #23 daily digest (suggested order). Icebox: #13 database storage — do not implement until a multi-user requirement exists in `docs/context.md`.

## Last session
#28–#33 merged via PRs #46–#51. #42 (backend dead code and duplication) implemented on branch `issue-42-backend-dead-code` with a PR open (`Closes #42`), not yet merged. 141 tests pass, ruff clean. Next in the suggested order are #43 (unused Vite template files) and #44 (stale docs).
