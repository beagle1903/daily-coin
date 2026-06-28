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

## Next Steps
- Consider implementing a live `watch` command dashboard for users who want continuous updates instead of manual `run` cycles.
- Add an explicit `--proxy` option to allow bypassing ISP blocks using user-defined proxy configurations.
