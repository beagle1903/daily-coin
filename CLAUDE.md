# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Start with `AGENTS.md`: it is the canonical agent map (read order for `docs/`, `progress.md`, and the GitHub-issue workflow). This file only adds what is needed to work quickly.

## Commands

On Windows use the venv interpreter directly (raw `pytest` causes import path errors):

```bash
.\venv\Scripts\python.exe -m pytest                              # all tests
.\venv\Scripts\python.exe -m pytest tests/test_logic.py::test_x  # single test
.\venv\Scripts\python.exe -m ruff check .                        # lint (CI runs ruff + pytest)
.\venv\Scripts\python.exe main.py run                            # CLI: generate portfolio
.\venv\Scripts\python.exe main.py history                        # CLI: past performance
.\venv\Scripts\python.exe main.py serve                          # API on http://127.0.0.1:8000
cd frontend && npm install && npm run dev                        # dashboard on http://localhost:5173
docker compose up --build                                        # both, in one Linux container
```

`.env` (see `.env.example`) needs `BINANCE_API_KEY`/`BINANCE_API_SECRET` and the same value in `DAILY_COIN_API_KEY` and `VITE_DAILY_COIN_API_KEY`. Without Binance keys the client falls back to mock data.

## Architecture

- `main.py` (Typer CLI) and `server.py` (FastAPI) are thin presentation layers; both call `portfolio_service.generate_portfolio`, the single async pipeline.
- Pipeline: `history.py` evaluates past picks (30-day TTL, `history.json`) → `news.py` pulls RSS headlines and scores them with VADER → `binance_client.py` fetches variance/RSI/MACD (cached, mock fallback) → `logic.py` (pure functions) scores, splits into stable/volatile buckets, selects, and builds each pick's nested `explanation`.
- Tunables live in `constants.py`; user-adjustable counts persist in `settings.json` via `/api/settings`.
- `/api/*` routes require `X-API-Key`; `/api/portfolio/generate` is rate-limited. The Vite key is shipped in the client bundle, so it is shared-local protection, not auth.
- `frontend/` is a single-page Vite + React app (`src/App.jsx`) calling the API at port 8000.

## Workflow

One GitHub issue per branch (`issue-N-short-slug`), PR with `Closes #N`, never commit ticket work to `main`. Update `progress.md` with short handoff notes at session end. Docs in `docs/` are the source of truth for domain rules and decisions.
