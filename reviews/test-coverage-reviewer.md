# Test Coverage & Quality Review: daily-coin

**Date:** 2026-08-07  
**Reviewer:** Test Coverage Review Agent

---

## 1. `news.py` Has ZERO Tests
**Severity:** P0  
**File(s):** [`news.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/news.py)  
**Finding:** The entire news fetching and sentiment analysis module (`get_latest_news`, `analyze_news_impact`) has no corresponding test file. This is the module most dependent on external services (RSS feeds) and complex text processing.  
**Fix Suggestion:**
> Create `tests/test_news.py`. Mock `feedparser.parse` to return both valid RSS entries and malformed/empty responses, and ensure `get_latest_news` handles them gracefully. Test `analyze_news_impact` with various headline sentiment patterns.

---

## 2. `server.py` Has ZERO Tests
**Severity:** P0  
**File(s):** [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py)  
**Finding:** All 5 FastAPI API endpoints are completely untested. The server contains significant business logic (the entire portfolio generation flow duplicated from `main.py`) that has no automated verification.  
**Fix Suggestion:**
> Create `tests/test_server.py` using FastAPI `TestClient` to verify all endpoints, especially validating persistent settings update and portfolio generation.

---

## 3. `config.py` Has ZERO Tests
**Severity:** P0  
**File(s):** [`config.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/config.py)  
**Finding:** While simple, the config module's warning behavior when env vars are missing is not tested.  
**Fix Suggestion:**
> Add tests that verify the warning is printed when env vars are absent, and that values are loaded correctly when present.

---

## 4. No Negative/Error Path Tests for `main.py`
**Severity:** P1  
**File(s):** [`tests/test_main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/tests/test_main.py)  
**Finding:** The `test_run_command_success` test only covers the happy path. There are no tests for: empty `valid_symbols`, coins with $0 prices triggering the replacement loop, news failures, or market data failures.  
**Fix Suggestion:**
> Add error path tests: mock `get_tradeable_symbols` returning `[]`, mock `get_current_prices` returning `{coin: 0.0}`, and verify the CLI handles these gracefully.

---

## 5. `add_portfolio_record` is Untested
**Severity:** P1  
**File(s):** [`history.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/history.py) (Line 25)  
**Finding:** This function writes to the history file and calls `clean_old_history_in_memory`, but has no dedicated test.  
**Fix Suggestion:**
> Add a test using `tmp_path` and `monkeypatch` to verify `add_portfolio_record` correctly appends records and cleans old entries.

---

## 6. `history` CLI Command is Untested
**Severity:** P1  
**File(s):** [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py) (Line 204)  
**Finding:** The `show_history` typer command has no test coverage.  
**Fix Suggestion:**
> Add a test that mocks `load_history` with evaluated records and verifies the CLI output contains expected table headers and performance data.

---

## 7. Mock Data Paths Untested for Edge Cases
**Severity:** P1  
**File(s):** [`tests/test_binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/tests/test_binance_client.py)  
**Finding:** Tests use `patch("binance_client.USE_MOCK_DATA", True)` but don't test the transition from live to mock mode (the fallback mechanism).  
**Fix Suggestion:**
> Enhance `test_binance_client.py` by mocking an `AsyncClient.get_historical_klines` failure that raises a `BinanceAPIException` with `status_code=429` to test the exponential backoff in `fetch_with_retry`.

---

## 8. No Integration or End-to-End Tests
**Severity:** P2  
**File(s):** All test files  
**Finding:** All tests are unit tests. There are no tests that verify the full flow from CLI invocation through to history persistence.  
**Fix Suggestion:**
> Create integration tests that exercise the full `run` command pipeline with all mocks in place, verifying the history file is written correctly.

---

## 9. Missing Edge Case Tests for `logic.py`
**Severity:** P2  
**File(s):** [`tests/test_logic.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/tests/test_logic.py)  
**Finding:** No tests for empty universe, all-zero scores, or universe with fewer coins than requested stable/volatile count.  
**Fix Suggestion:**
> Add edge case tests: `pick_portfolio` with empty `available_stable`, `load_coin_scores` with empty universe, `evaluate_performance` with all-zero prices.

---

## 10. Assertion Quality
**Severity:** P2  
**File(s):** [`tests/test_main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/tests/test_main.py)  
**Finding:** Assertions check broad strings in standard output. They should be more precise, verifying specific mock arguments (e.g., asserting `mock_add_record` was called with the correct exact portfolio list).  
**Fix Suggestion:**
> Enhance assertions to verify `mock_add_record.call_args` contains the expected portfolio and prices.

---

## Function Coverage Matrix

| Module | Function | Tested? |
|--------|----------|---------|
| `logic.py` | `load_coin_scores` | ✅ |
| `logic.py` | `pick_portfolio` | ✅ |
| `logic.py` | `evaluate_performance` | ✅ |
| `history.py` | `load_history` | ✅ |
| `history.py` | `save_history` | ✅ |
| `history.py` | `clean_old_history_in_memory` | ✅ |
| `history.py` | `add_portfolio_record` | ❌ |
| `history.py` | `get_unevaluated_records` | ❌ |
| `binance_client.py` | `calculate_rsi` | ✅ |
| `binance_client.py` | `calculate_macd` | ✅ |
| `binance_client.py` | `get_sync_client` | ✅ |
| `binance_client.py` | `get_current_prices` | ✅ (mock only) |
| `binance_client.py` | `get_tradeable_symbols` | ✅ (mock only) |
| `binance_client.py` | `fetch_all_market_data` | ✅ |
| `binance_client.py` | `load_midas_allowlist` | ❌ |
| `binance_client.py` | `fetch_with_retry` | ❌ |
| `binance_client.py` | `fetch_historical_data_async` | ❌ |
| `binance_client.py` | `_get_mock_market_data` | ❌ (internal) |
| `news.py` | `get_latest_news` | ❌ |
| `news.py` | `analyze_news_impact` | ❌ |
| `server.py` | All endpoints | ❌ |
| `config.py` | Module-level logic | ❌ |
| `main.py` | `run_portfolio` | ✅ |
| `main.py` | `show_history` | ❌ |
| `main.py` | `serve_api` | ❌ |
