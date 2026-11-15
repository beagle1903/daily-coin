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

## Open work
See GitHub Issues. Do not use `tasks.json`. Audit findings are sub-issues of #45 (#28–#44); suggested order there is the data-integrity bugs first (#29, #30 remain). Product backlog: #20 vs BTC, #21 constraints, #22 hold vs regenerate, #23 daily digest (suggested order). Icebox: #13 database storage — do not implement until a multi-user requirement exists in `docs/context.md`.

## Last session
#28 implemented on branch `issue-28-mock-data-history` with a PR open (`Closes #28`), not yet merged. 80 tests pass, ruff clean. Next suggested ticket is #29 (partial kline failure trips the global circuit breaker).
