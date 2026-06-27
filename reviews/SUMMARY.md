# Parallel Code Review Summary

**Date:** 2026-06-23
**Synthesis of Reviews:** Architecture, Performance, Business Logic, and Test Coverage.
*(Note: The Security review subagent was blocked from executing due to AI safety policies regarding automated vulnerability scanning. Manual review is recommended for security aspects.)*

## Priority 0 (Critical / Blockers / High Impact)

### 1. Network Bottlenecks & API Rate Limiting
- **Issue:** Redundant API calls (fetching 30-day and 60-day klines separately) result in 200 network requests for 100 symbols. Unbounded `asyncio.gather` calls cause immediate bursts, risking Binance API IP bans (HTTP 429).
- **Suggested Fix (Agent Prompt):**
  > "Refactor `binance_client.py` to use a single shared `AsyncClient` session. Consolidate kline fetching to request 60 days of data once per symbol, and compute both 30-day variance and technical indicators from this single dataset. Wrap the async API calls in `fetch_all_variances` and `fetch_all_technical_indicators` with an `asyncio.Semaphore` (limit 10-15) to prevent API burst rate limiting."

## Priority 1 (Important / Architecture / Edge Cases)

### 2. Missing Dependency Injection in `logic.py`
- **Issue:** `logic.py` directly imports and invokes I/O functions from `binance_client.py` and `history.py`, violating its goal of being purely functional and making unit testing difficult.
- **Suggested Fix (Agent Prompt):**
  > "Refactor `logic.py` to use Dependency Injection. Modify the scoring and selection functions to accept raw data (prices, variances, technical indicators, history) as arguments instead of fetching them internally. Move the orchestration of data fetching to `main.py`."

### 3. Delisted / Zero Price Coin Handling
- **Issue:** If a coin is delisted from Binance, its current price evaluates to `0`. The performance evaluation incorrectly treats this as `0.0` (0% change) rather than penalizing it. Zero-priced entry coins can also break future evaluations.
- **Suggested Fix (Agent Prompt):**
  > "Update `evaluate_performance` in `logic.py` so that if `curr_p == 0` but `old_p > 0`, the performance is recorded as `-1.0` (-100% loss) to heavily penalize the heuristic score. Also, update `pick_portfolio` to discard any symbols where a valid non-zero entry price cannot be fetched."

### 4. Synchronous RSS Parsing Overhead
- **Issue:** `news.py` iterates through RSS feeds synchronously, meaning total latency is the sum of all individual feed response times.
- **Suggested Fix (Agent Prompt):**
  > "Parallelize the RSS feed fetching in `news.py`'s `get_latest_news()` using `asyncio` and `aiohttp` (or a `ThreadPoolExecutor`) to fetch and parse the XML payloads concurrently."

## Priority 2 (Low Impact / Tech Debt / Testing)

### 5. Inconsistent Client Usage & Overfetching
- **Issue:** Global synchronous `Client` initialization in `binance_client.py` can cause import-time crashes. Ticker data overfetches the entire exchange instead of just the requested symbols.
- **Suggested Fix (Agent Prompt):**
  > "Remove the global synchronous `Client` initialization in `binance_client.py` and standardize on async. Optimize `get_current_prices` by passing a list of symbols to the Binance API endpoint instead of fetching all tickers."

### 6. Low Test Coverage on Async & E2E Flows
- **Issue:** The project has 45% coverage, primarily missing tests for async integrations, API retries, and the Typer CLI E2E flow.
- **Suggested Fix (Agent Prompt):**
  > "Increase test coverage for async integrations. Mock the Binance API using `pytest-asyncio` and `aioresponses` to test `fetch_with_retry` and rate-limit handling. Add Typer `CliRunner` tests for the `main.py` execution flow."
