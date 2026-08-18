# Progress Notes

*This file contains session-to-session handoff notes for the AI.*

## Current Status
- Fully implemented the core CLI application in `main.py` using `typer`.
- Developed `logic.py` to evaluate coins based on a heuristic scoring mechanism and qualitative groups.
- Integrated `binance_client.py` for fetching real-time market data.
- Built a 30-day TTL history state manager in `history.py` to learn from past picks.
- Integrated an RSS News feed via `news.py` using `feedparser`.
- Added VADER sentiment analysis to dynamically adjust heuristic scores based on bullish/bearish headlines.
- Expanded the coin universe in `logic.py` with more coins across conservative, moderate, and aggressive categories to offer a wider portfolio.
- Added `--stable` and `--volatile` command-line options in `main.py` to allow customized portfolio sizes (defaults to 2 stable and 3 volatile).
- Expanded the `KEYWORD_MAP` in `news.py` to properly cover all altcoins defined in `logic.py`.
- Refactored `main.py` Typer app to support multiple commands.
- Reverted identity shift: project is purely a daily crypto portfolio CLI.
- Implemented RSI and MACD technical indicators in `binance_client.py` and integrated them into `logic.py`'s scoring heuristic.
- Fixed `test_load_coin_scores` unit test to mock `get_technical_indicators`, preventing real Binance API calls and resolving test failure.
- Created unit tests for `calculate_rsi` and `calculate_macd` math in `tests/test_binance_client.py`.
- Implemented asynchronous API fetching (`AsyncClient` + `asyncio.gather`) to remove the N+1 network bottleneck in Binance data fetching.
- Removed hardcoded category arrays and replaced them with dynamic math-based 30-day variance sorting.
- Cleaned up inefficient memory I/O in `history.py` to prevent redundant reads and writes.
- Fixed a Unicode printing bug on Windows for the Rich console by injecting `chcp 65001`.
- Re-wrote the test suite to strictly use pytest `tmp_path` to avoid unsafe OS operations and patched API requests.
- Verified application execution and generated today's recommended portfolio.
- Added a new `history` subcommand to the Typer app to display performance of all past evaluated portfolios.
- Successfully ran the Typer CLI `run` command to evaluate the previous portfolio, fetch RSS news feeds, analyze news sentiment, and print today's recommended portfolio.
- Updated `AGENTS.md` and `docs/architecture.md` with quick command references and developer execution guides so future agents can run and test the app immediately without reading multiple documents.
- Refactored architecture from a daily 24-hour evaluation interval to a shorter 4-hour kline interval (`AsyncClient.KLINE_INTERVAL_4HOUR`), allowing for continuous intra-day portfolio generation and evaluation.
- Reduced `history.json` TTL from 30 days to 7 days to prevent bloat and align with the new faster cycle.
- Updated CLI text strings to remove "daily" constraints (e.g. "yesterday", "24h", "tomorrow").
- Added a resilient **Offline Mock Mode** fallback to `binance_client.py` to prevent crashes when the Binance API is blocked by the local ISP/network filter.
- Ensured module imports are safe and unit tests load and pass successfully.

### Parallel Code Review Implementation (Current Session)
- **Consolidated Binance Kline Fetching:** Refactored `binance_client.py` to retrieve 60 days of kline data once per symbol and calculate both 30-day variance and technical indicators in-memory. This cuts network request overhead by 50%.
- **Rate Limit & Connection Reuse:** Standardized async client fetching under a single `AsyncClient` connection pool, bounding request bursts using `asyncio.Semaphore(15)`.
- **Ticker Optimization:** Refactored `get_current_prices` to request prices for specified symbols only (using the `symbols` parameter) instead of downloading all tickers on the exchange, falling back to full tickers on failures.
- **Lazy client instantiation:** Removed global/import-time Binance client instantiations, resolving potential crash routes when offline.
- **Concurrent RSS Feed Fetching:** Parallelized blocking XML parser feeds in `news.py` using `asyncio.to_thread`.
- **Pure Logic Refactoring:** Implemented full Dependency Injection in `logic.py` by removing I/O dependencies. Moves news and market data orchestration to `main.py`, rendering business calculations pure.
- **Delisted Coin Safety:** Handled zero-price and delisted coins as a `-100%` performance loss (`-1.0`) to penalize future scores, and implemented candidate verification loops in `main.py` to discard and replace zero-priced picks.
- **Expanded Test Suite:** Wrote 8 new tests (expanding suite from 10 to 18) covering async fetching mocks, E2E CLI commands via `CliRunner`, and pure DI logic, achieving a **93.6% speedup** in total runtime (from 28.63s to 1.83s).
- **Stablecoin Filtering:** Updated `binance_client.py` to explicitly exclude fiat-pegged stablecoins (e.g., USDC, USD1, FDUSD) from being selected in the portfolio, ensuring the "stable" category only consists of low-volatility crypto assets.
- **Midas Allowlist Integration:** Implemented a manual filtering mechanism via `midas_coins.json` to ensure the portfolio generator strictly selects from user-verified coins available on the Midas platform, preventing the selection of un-tradeable assets.
- **Robust Offline Mock Fallback (Current Session):** Added proper exception handling to `get_tradeable_symbols`, `get_current_prices`, and `fetch_all_market_data` in `binance_client.py`. If any of the Binance API endpoints time out or throw network errors, the app prints a warning to `sys.stderr` and automatically transitions to `USE_MOCK_DATA = True`, ensuring graceful fallback and preventing CLI crashes under connection failures.

### Fullstack Web Application Upgrade (Current Session)
- **FastAPI Backend:** Created `server.py` containing REST endpoints to query past portfolio history (`/api/history`) and generate new recommended portfolios (`/api/portfolio/generate`).
# Progress Notes

*This file contains session-to-session handoff notes for the AI.*

## Current Status
- Fully implemented the core CLI application in `main.py` using `typer`.
- Developed `logic.py` to evaluate coins based on a heuristic scoring mechanism and qualitative groups.
- Integrated `binance_client.py` for fetching real-time market data.
- Built a 30-day TTL history state manager in `history.py` to learn from past picks.
- Integrated an RSS News feed via `news.py` using `feedparser`.
- Added VADER sentiment analysis to dynamically adjust heuristic scores based on bullish/bearish headlines.
- Expanded the coin universe in `logic.py` with more coins across conservative, moderate, and aggressive categories to offer a wider portfolio.
- Added `--stable` and `--volatile` command-line options in `main.py` to allow customized portfolio sizes (defaults to 2 stable and 3 volatile).
- Expanded the `KEYWORD_MAP` in `news.py` to properly cover all altcoins defined in `logic.py`.
- Refactored `main.py` Typer app to support multiple commands.
- Reverted identity shift: project is purely a daily crypto portfolio CLI.
- Implemented RSI and MACD technical indicators in `binance_client.py` and integrated them into `logic.py`'s scoring heuristic.
- Fixed `test_load_coin_scores` unit test to mock `get_technical_indicators`, preventing real Binance API calls and resolving test failure.
- Created unit tests for `calculate_rsi` and `calculate_macd` math in `tests/test_binance_client.py`.
- Implemented asynchronous API fetching (`AsyncClient` + `asyncio.gather`) to remove the N+1 network bottleneck in Binance data fetching.
- Removed hardcoded category arrays and replaced them with dynamic math-based 30-day variance sorting.
- Cleaned up inefficient memory I/O in `history.py` to prevent redundant reads and writes.
- Fixed a Unicode printing bug on Windows for the Rich console by injecting `chcp 65001`.
- Re-wrote the test suite to strictly use pytest `tmp_path` to avoid unsafe OS operations and patched API requests.
- Verified application execution and generated today's recommended portfolio.
- Added a new `history` subcommand to the Typer app to display performance of all past evaluated portfolios.
- Successfully ran the Typer CLI `run` command to evaluate the previous portfolio, fetch RSS news feeds, analyze news sentiment, and print today's recommended portfolio.
- Updated `AGENTS.md` and `docs/architecture.md` with quick command references and developer execution guides so future agents can run and test the app immediately without reading multiple documents.
- Refactored architecture from a daily 24-hour evaluation interval to a shorter 4-hour kline interval (`AsyncClient.KLINE_INTERVAL_4HOUR`), allowing for continuous intra-day portfolio generation and evaluation.
- Reduced `history.json` TTL from 30 days to 7 days to prevent bloat and align with the new faster cycle.
- Updated CLI text strings to remove "daily" constraints (e.g. "yesterday", "24h", "tomorrow").
- Added a resilient **Offline Mock Mode** fallback to `binance_client.py` to prevent crashes when the Binance API is blocked by the local ISP/network filter.
- Ensured module imports are safe and unit tests load and pass successfully.

### Parallel Code Review Implementation (Current Session)
- **Consolidated Binance Kline Fetching:** Refactored `binance_client.py` to retrieve 60 days of kline data once per symbol and calculate both 30-day variance and technical indicators in-memory. This cuts network request overhead by 50%.
- **Rate Limit & Connection Reuse:** Standardized async client fetching under a single `AsyncClient` connection pool, bounding request bursts using `asyncio.Semaphore(15)`.
- **Ticker Optimization:** Refactored `get_current_prices` to request prices for specified symbols only (using the `symbols` parameter) instead of downloading all tickers on the exchange, falling back to full tickers on failures.
- **Lazy client instantiation:** Removed global/import-time Binance client instantiations, resolving potential crash routes when offline.
- **Concurrent RSS Feed Fetching:** Parallelized blocking XML parser feeds in `news.py` using `asyncio.to_thread`.
- **Pure Logic Refactoring:** Implemented full Dependency Injection in `logic.py` by removing I/O dependencies. Moves news and market data orchestration to `main.py`, rendering business calculations pure.
- **Delisted Coin Safety:** Handled zero-price and delisted coins as a `-100%` performance loss (`-1.0`) to penalize future scores, and implemented candidate verification loops in `main.py` to discard and replace zero-priced picks.
- **Expanded Test Suite:** Wrote 8 new tests (expanding suite from 10 to 18) covering async fetching mocks, E2E CLI commands via `CliRunner`, and pure DI logic, achieving a **93.6% speedup** in total runtime (from 28.63s to 1.83s).
- **Stablecoin Filtering:** Updated `binance_client.py` to explicitly exclude fiat-pegged stablecoins (e.g., USDC, USD1, FDUSD) from being selected in the portfolio, ensuring the "stable" category only consists of low-volatility crypto assets.
- **Midas Allowlist Integration:** Implemented a manual filtering mechanism via `midas_coins.json` to ensure the portfolio generator strictly selects from user-verified coins available on the Midas platform, preventing the selection of un-tradeable assets.
- **Robust Offline Mock Fallback (Current Session):** Added proper exception handling to `get_tradeable_symbols`, `get_current_prices`, and `fetch_all_market_data` in `binance_client.py`. If any of the Binance API endpoints time out or throw network errors, the app prints a warning to `sys.stderr` and automatically transitions to `USE_MOCK_DATA = True`, ensuring graceful fallback and preventing CLI crashes under connection failures.

### Fullstack Web Application Upgrade (Current Session)
- **FastAPI Backend:** Created `server.py` containing REST endpoints to query past portfolio history (`/api/history`) and generate new recommended portfolios (`/api/portfolio/generate`).
- **Settings Persistence:** Added `/api/settings` endpoints to persist stable/volatile target counts dynamically in `settings.json`.
- **Event Loop Optimization:** Wrapped all synchronous blocking calls (e.g. file I/O, synchronous Binance API fallback) in `asyncio.to_thread` to ensure non-blocking concurrent execution in FastAPI.
- **CLI serve command:** Added a `serve` subcommand to `main.py` allowing developers to launch the FastAPI server locally.
- **Glassmorphism React Dashboard:** Developed a premium Vite + React SPA in `/frontend` styled with a dark theme and glassmorphic designs to visual portfolio suggestions, history evaluation logs, and sentiment news analysis.
- **Agent Skill Update**: Updated the `/run-fe` agent skill to start BOTH the frontend development server and backend API server simultaneously, and to print the clickable application URL (`http://localhost:5173`) in the chat after startup.

### Codebase Maintenance, Review & P0 Defect Fixes (Current Session)
- **Dependency Upgrades:** Upgraded 18 outdated dependencies (7 direct, 11 transitive) one-by-one with pytest verification. Pinned direct dependencies in `requirements.txt`.
- **Code Quality & Linting:** Analyzed dead code with Vulture (0 dead code items at 80% confidence) and auto-fixed linting/import formatting issues with Ruff.
- **Parallel Specialized Code Reviews:** Conducted 5 specialized code reviews across Security, Architecture, Test Coverage, Performance, and Business Logic. Consolidated all 27 findings into `reviews/SUMMARY.md`.
- **P0 Defect Fixes:**
  - *Extracted Shared Portfolio Service (`portfolio_service.py`):* Eliminated ~80 lines of duplicate portfolio orchestration code between `main.py` and `server.py`.
  - *Fixed Unbounded Score Inflation (`logic.py`):* Capped per-record historical adjustments to ±5.0, averaged adjustments across history records, and enforced global score floor (1.0) and ceiling (30.0).
  - *Deduplicated History File I/O (`history.py` & `portfolio_service.py`):* Refactored history loading to load once per generation cycle and pass through the pipeline.
  - *In-Memory TTL Caching (`binance_client.py`):* Added TTL-based caching for tradeable symbols (1 hr) and market data (15 mins) to prevent API rate limits.
  - *Expanded Test Coverage:* Created `tests/test_news.py` (11 tests) and `tests/test_server.py` (9 tests), growing the total test suite from 18 to 39 passing tests.

### P1 Defect Fixes (Current Session)
- **Concurrency Integrity:** Implemented `filelock` and atomic `os.replace` operations in `history.py` and `server.py` to prevent data corruption during simultaneous writes.
- **Repository Pattern:** Refactored `history.py` into `JsonHistoryRepository`, separating file I/O from business logic.
- **Resilient Circuit Breaker:** Removed permanent `USE_MOCK_DATA` flag in `binance_client.py` and replaced it with a 60-second `MOCK_DATA_UNTIL` fallback.
- **Configurable Variance Split:** Replaced hardcoded `len // 3` stable/volatile threshold with a math-driven `variance_percentile` dynamically adjustable via settings.
- **Batched Fetching:** The portfolio replacement loop now batch-fetches candidate prices concurrently, removing the N+1 API bottleneck.
- **Accurate Delisting Penalties:** Only coins proven to be delisted from `get_tradeable_symbols` receive the -100% logic penalty, protecting against transient fetch errors.
- **Lazy Init:** VADER sentiment analysis in `news.py` is now lazy-loaded, speeding up CLI non-news commands.
- **Testing:** Fixed and expanded coverage for all new functionality. Test suite remains 100% passing (40/40).

### P2 Defect Fixes & Performance Optimization (Current Session)
- **Numpy Vectorization:** Refactored RSI, MACD, and Variance computations in `binance_client.py` using `numpy` arrays for high-speed mathematical throughput.
- **Targeted Fallbacks:** Removed `get_all_tickers()` mass exchange fetching in favor of per-symbol price lookups.
- **Guard Clauses:** Eliminated recursive error fallback loops across `binance_client.py`, replacing them with flat early returns.
- **Centralized Constants:** Extracted all magic numbers across the codebase into `constants.py`.
- **Enhanced Crypto VADER & News Logic:** Added crypto lexicon dictionary to VADER, raised compound score threshold to `0.25`, deduplicated per-coin sentiment impacts by averaging compound scores, and dynamically built symbol keyword maps from active tradeable symbols.
- **Restricted CORS:** Tightened FastAPI CORS headers and allowed methods to `GET` and `POST`.
- **Standardized Logging:** Replaced raw `sys.stderr` `print` calls with standard `logging.warning()` statements.
- **Expanded Unit Testing:** Added edge case unit tests in `test_logic.py`, expanding the test suite to 43/43 passing tests.

### Skill Management (Current Session)
- **Repo Skills Mirror:** Created `skills/run/SKILL.md` and `skills/run-fe/SKILL.md` in the repository root directory to ensure skills are checked into the repo alongside `.agents/skills`.

### Local Docker workspace (Windows 11 + Docker Desktop)
- Added `Dockerfile`, `compose.yaml`, `.devcontainer/devcontainer.json`, and `docs/local-docker.md`.
- `docker compose up --build` starts the API (`8000`) and Vite (`5173`) in one Linux container, with host port publishing (same ports as the cloud agent).
- Pinned `pydantic` to `2.13.4` so image builds succeed (`2.48.0` is not on PyPI).
- Vite watches with polling when `CHOKIDAR_USEPOLLING=true` so Windows bind mounts pick up edits.

## Next Steps
- Revisit optional P1 security items (e.g. API key authentication & `slowapi` rate limiting).
- Implement database storage / ORM for multi-user tracking.
