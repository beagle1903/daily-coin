# Architecture Blueprint

## System Overview
- **Language:** Python 3.12+ (the minimum; CI and the Docker image both use 3.12)
- **CLI Framework:** Typer (with Rich for terminal formatting)
- **API:** FastAPI (`server.py`) served via `python main.py serve`
- **Frontend:** Vite + React SPA in `frontend/`
- **Data Integration:** `python-binance` for market prices.
- **News Integration:** `feedparser` for RSS aggregation, `vaderSentiment` for NLP sentiment analysis.
- **Quality:** pytest, ruff (`E`, `F`, `I`, `B`; `target-version = "py312"`), and GitHub Actions CI on pull requests and pushes to `main`: a backend job (ruff + pytest on Python 3.12) and a frontend job (`npm ci`, `npm run lint`, `npm run build` on Node 22), with pip and npm caching.

## Project Structure
- `main.py`: Entry point for the Typer app (`run`, `history`, `serve`). Presentation layer only. `run` takes its counts and variance percentile from `settings.py`; `--stable`, `--volatile` and `--variance-percentile` override them for that run without saving.
- `portfolio_service.py`: Shared async portfolio generation pipeline used by the CLI and the API. Runs in one process are serialized, blocking Binance and file calls run in worker threads so the API stays responsive, and history is written once per run. Each pick in `portfolio` includes a nested `explanation` object (components + `summary`).
- `binance_client.py`: Handles all interactions with the Binance API (variance, RSI, MACD, caching, mock fallback). Mock data is display-only: it is never cached, and a run that used it returns `mock: true`, does not evaluate pending records, and does not append to `history.json`. A symbol whose klines cannot be fetched is logged and left out of that run's universe; the circuit breaker (and mock fallback) only trips when more than `KLINE_FAILURE_BREAKER_RATIO` of the symbols have no data or the client itself fails.
- `logic.py`: Pure functions containing the heuristic scoring, coin selection, portfolio generation logic, score breakdowns, bucket rank/average, and the pick-explanation paragraph template.
- `formatting.py`: CLI number formatting that keeps sub-cent prices readable (4 significant digits below 1).
- `history.py`: `JsonHistoryRepository` for saving and evaluating past portfolios (saved in `history.json`, 30-day TTL). Records younger than `MIN_EVALUATION_AGE_SECONDS` are left pending. `record_run` saves each run's evaluations and new record in one locked read-modify-write, and never overwrites a record that is already evaluated, so the CLI and the API can run side by side.
- `news.py`: Fetches RSS feeds from top crypto outlets, parses headlines, and executes VADER sentiment analysis to provide heuristic modifiers. Sentiment is scored over the newest `NEWS_ANALYZE_LIMIT` headlines (per feed and in total); only the newest `NEWS_DISPLAY_LIMIT` are returned for display. Feed dates are converted as UTC (`calendar.timegm`); a feed that fails is logged at warning level and skipped. Coin names match in any case; tickers match only as `$TICKER`, or in upper case when at least `NEWS_TICKER_MIN_LENGTH` long and not in `NEWS_AMBIGUOUS_TICKERS` (see `find_mentioned_symbols`).
- `constants.py`: Centralized tunable parameters (cache TTLs, indicator periods, score caps, VADER settings, portfolio count defaults/max, excluded stablequote bases, news headline limit).
- `settings.py`: User-adjustable settings (`stable_count`, `volatile_count`, `variance_percentile`) shared by the CLI and the API. Stored in `settings.json`, which is not in version control: it is created on the first save, and missing or out-of-range values fall back to the defaults in `constants.py`. Counts are bounded (`gt=0`, `le=PORTFOLIO_COUNT_MAX`) and `variance_percentile` must be above 0 and below 100.
- `server.py`: FastAPI REST endpoints for settings, history, and portfolio generation. `/api/*` routes require an `X-API-Key` header matching `DAILY_COIN_API_KEY`. `stable`/`volatile` query params are bounded (`gt=0`, `le=PORTFOLIO_COUNT_MAX`). `POST /api/settings` is a partial update: fields that are not sent keep their stored value. `POST /api/portfolio/generate` is rate-limited (`PORTFOLIO_GENERATE_RATE_LIMIT`); it is a POST because it evaluates pending records and appends to history. If Binance data is unavailable, generate returns `502` with a `detail` message (not `200 {"error": ...}`); the CLI still shows the service's `error`. CORS does not allow credentials (auth is a header). `python main.py serve` does not auto-reload; pass `--reload` in development (the Docker entrypoint does). `GET /api/history` is read-only, and its newest record carries `picks` (the full per-coin detail) so the dashboard can show the latest saved portfolio without generating.
- `schemas.py`: Pydantic response models (`Pick`, `Explanation`, `HistoryRecord`, `GenerateResponse`, ...) used as `response_model` so the OpenAPI schema describes the payloads. Old history records without `picks`/`performance` stay valid.
- `frontend/`: Vite + React dashboard for portfolio suggestions, history, and news sentiment. Pick cards show the score breakdown (base, history, news, RSI, MACD) next to the paragraph; the news panel lists each sentiment impact (coin, Bullish/Bearish, score adjustment); after a run that evaluated past picks, a "Just Evaluated" panel shows each portfolio's average and per-coin change. Settings/history load failures show as warnings instead of only in the console. It sends `VITE_DAILY_COIN_API_KEY` as `X-API-Key`. That Vite value is in the client bundle, so dashboard users can recover it; this is shared local-API protection, not per-user auth.
- `tests/`: Pytest suite for calculations, CLI, news, and API.

## Design Patterns
- **Separation of Concerns:** CLI routing (`main.py`) and HTTP routing (`server.py`) are separated from selection logic (`logic.py`) and data fetching (`binance_client.py`, `news.py`). Both entry points call `portfolio_service.generate_portfolio`.
- **Heuristic Feedback Loop:** The app "learns" by keeping a rotating 30-day memory of its past picks, applying percentage gain/loss adjustments to the baseline scores (capped in `logic.py`).

## Development & Execution Commands
See the [README](../README.md) for setup, running the CLI and web app, tests and lint, and [local-docker.md](local-docker.md) for Docker Desktop.
