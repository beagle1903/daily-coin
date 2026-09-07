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
See GitHub Issues. Do not use `tasks.json`. Product backlog: #19 explain picks, #20 vs BTC, #21 constraints, #22 hold vs regenerate, #23 daily digest (suggested order). Icebox: #13 database storage — do not implement until a multi-user requirement exists in `docs/context.md`.

## Last session
On `issue-24-p2-audit-closeout`: re-verified August 2026 P2 items 17–27. Most were already on `main`. Remaining gaps: phrase-level news aliases, log batch ticker fallback, `config.py` logging, extra `pick_portfolio` edge test, more values in `constants.py`. Status table is in `reviews/SUMMARY.md`.
