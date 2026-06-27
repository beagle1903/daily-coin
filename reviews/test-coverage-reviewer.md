# Test Coverage & Quality Review

## 📊 Overview
* **Overall Code Coverage:** 45% (251 / 456 lines missing)
* **Tested:** Pure algorithmic functions (RSI/MACD math), basic history in-memory filtering, CLI argument bounds, basic coin scoring logic.
* **Untested:** API integrations, async functions, complex aggregations (`pick_portfolio`, `evaluate_performance`), complete application flows (E2E), and data fetching (news RSS, Binance API).

## 🗂️ File-by-File Breakdown & Identified Gaps

### 1. `binance_client.py` (48% Coverage)
* **What is tested:** `calculate_rsi` and `calculate_macd` math calculations.
* **Untested Areas:** 
  * `get_tradeable_symbols`, `get_current_prices`
  * Async functionalities: `fetch_with_retry`, `get_30d_variance_async`, `get_technical_indicators_async`, `fetch_all_variances`, `fetch_all_technical_indicators`.
* **Missing Edge Cases & Fragile Logic:**
  * Network retries and API rate limit logic (`BinanceAPIException` with `status_code == 429` inside `fetch_with_retry`) are completely untested.
  * Timeout handling and network failures returning empty lists `[]` or empty dicts `{}`.
  * Empty `closes` logic inside `get_technical_indicators_async`.

### 2. `news.py` (20% Coverage)
* **What is tested:** None. The file has 0 dedicated test cases. Only module imports are hit.
* **Untested Areas:**
  * `get_latest_news`: The feedparser loop.
  * `analyze_news_impact`: Sentiment scoring via `vaderSentiment`.
* **Missing Edge Cases & Fragile Logic:**
  * Exception handling inside `get_latest_news` (e.g., malformed RSS feeds, network timeout).
  * The graceful degradation fallback if `vaderSentiment` is not installed (`GLOBAL_ANALYZER = None`).
  * Scenarios where an article has an empty title or no timestamp.

### 3. `logic.py` (32% Coverage)
* **What is tested:** `load_coin_scores` has basic mock coverage.
* **Untested Areas:**
  * `pick_portfolio`: Categorizing coins into stable vs volatile, applying weighted sample selections.
  * `evaluate_performance`: Fetching old prices, calculating change ratios, updating in-memory history records.
* **Missing Edge Cases & Fragile Logic:**
  * `evaluate_performance` lacks tests for a missing/delisted coin (where `old_prices.get(coin)` or `curr_p` is 0), which correctly avoids a zero-division error but remains untested.
  * Test randomness in `unique_weighted_sample` inside `pick_portfolio` is untested (could be tested by seeding random or checking output types/sizes).

### 4. `main.py` (20% Coverage)
* **What is tested:** `test_main.py` checks simple bounds constraints on CLI options (`--stable < 1`, `--volatile < 1`).
* **Untested Areas:**
  * The main CLI execution logic: `run_portfolio` and `show_history`.
  * E2E flow combining News, Binance Data, Logic evaluation, and saving to history.
* **Missing Edge Cases & Fragile Logic:**
  * Application behavior when `pick_portfolio` throws an exception.
  * What the CLI displays when `evaluate_performance` or `get_latest_news` returns empty arrays.
  * Testing output generation and rich Table formatting (integration testing with mock CLI runner).

### 5. `history.py` (70% Coverage)
* **What is tested:** `clean_old_history_in_memory`, generic save/load flows.
* **Untested Areas:**
  * `add_portfolio_record` and `get_unevaluated_records` functions.
  * `json.JSONDecodeError` exception block in `load_history`.
* **Missing Edge Cases & Fragile Logic:**
  * Corrupted `history.json` file parsing correctly returning `[]`.
  * Concurrent file write attempts (could be an issue since it reads, cleans, and dumps `history.json` linearly).

## 🛠️ Actionable Recommendations
1. **Mock the Binance API:** Add `pytest-asyncio` and `aioresponses` or standard `unittest.mock` to mock Binance responses. Cover `fetch_with_retry` comprehensively, simulating `429` rate limits.
2. **Mock RSS Feeds:** Provide local static XML strings to mock `feedparser.parse` to write robust tests for `news.py`.
3. **E2E Testing for the CLI:** Use Typer's `CliRunner` (which is already imported) to run the `run` command end-to-end, mocking only the lowest level API/RSS fetchers. 
4. **Fix the Missing History File Tests:** Write a test that provides a malformed json string to trigger `json.JSONDecodeError` and verify it degrades gracefully.
