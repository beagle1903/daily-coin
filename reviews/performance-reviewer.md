# Performance Review: daily-coin

**Date:** 2026-08-07  
**Reviewer:** Performance Review Agent

---

## 1. Redundant History File I/O
**Severity:** P0  
**File(s):** [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py) (Lines 86-87, 126), [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py) (Lines 29, 113)  
**Finding:** `load_history()` is called up to **3 times** per single request to `/api/portfolio/generate` (lines 86 indirectly via `get_unevaluated_records`, line 87, and line 126). The history file is read from disk and parsed from JSON each time, and the results are discarded between calls.  
**Estimated Impact:** 3× unnecessary disk I/O + JSON parsing per request.  
**Fix Suggestion:**
> Load history once at the start of each request/run, pass it through the pipeline, and only reload after mutations. Remove redundant `load_history()` calls.

---

## 2. Unbatched Price Lookups in Replacement Loop
**Severity:** P1  
**File(s):** [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py) (Lines 141, 160), [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py) (Lines 152, 168)  
**Finding:** When a coin in the initial portfolio has a $0 price, the replacement logic fetches prices one coin at a time in a `while` loop (`get_current_prices([candidate])`). Each call is a separate network round-trip to the Binance API.  
**Estimated Impact:** Up to N additional API calls (where N = number of replacements needed).  
**Fix Suggestion:**
> Batch fetch current prices for all replacement candidates upfront rather than inside the `while` loop. Improve error handling in `get_current_prices` to avoid falling back to `get_all_tickers()` unnecessarily.

---

## 3. `get_all_tickers()` Fallback is Expensive
**Severity:** P1  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py) (Line 105)  
**Finding:** The `get_current_prices` function has a fallback that calls `client.get_all_tickers()`, which downloads the price for **every single** trading pair on Binance (~2000+ pairs), when only a handful are needed.  
**Estimated Impact:** 10-100× more data transferred than necessary on fallback.  
**Fix Suggestion:**
> Replace the `get_all_tickers()` fallback with individual per-symbol fallback calls, or implement a more targeted error recovery strategy.

---

## 4. Blocking Network I/O on Module Import
**Severity:** P1  
**File(s):** [`news.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/news.py) (Line 8)  
**Finding:** `SentimentIntensityAnalyzer()` is instantiated at module import time, adding significant startup latency (~200-500ms) even when news analysis isn't needed (e.g., `main.py --help`, `main.py history`).  
**Estimated Impact:** 200-500ms added to every CLI invocation.  
**Fix Suggestion:**
> Refactor `news.py` to use lazy initialization for `SentimentIntensityAnalyzer`. Create a `get_analyzer()` function that only instantiates the analyzer the first time it is actually needed.

---

## 5. No Caching of Tradeable Symbols or Market Data
**Severity:** P0  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py) (Line 54), [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py)  
**Finding:** Both the CLI and FastAPI server fetch `get_tradeable_symbols` and 60 days of historical klines for up to 100 symbols on every single execution/request. This triggers Binance rate limits and adds 5-10 seconds of latency to every `/api/portfolio/generate` endpoint call.  
**Estimated Impact:** 5-10 seconds latency per request, risk of Binance IP ban.  
**Fix Suggestion:**
> Add an in-memory TTL caching layer for `get_tradeable_symbols` and `fetch_all_market_data` in `server.py` so rapid API requests resolve instantly from memory.

---

## 6. Synchronous `get_tradeable_symbols` Fetches All Tickers
**Severity:** P2  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py) (Line 54)  
**Finding:** `client.get_ticker()` downloads 24hr stats for every trading pair, even though only the top N by volume are needed.  
**Estimated Impact:** Fetches ~2000 tickers when only top 100 are needed.  
**Fix Suggestion:**
> Use a more targeted Binance API endpoint or cache the full ticker list with a TTL.

---

## 7. History File Grows Without Bounds (Within TTL)
**Severity:** P2  
**File(s):** [`history.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/history.py)  
**Finding:** Each run appends a new record. The 7-day TTL means the file can grow to contain many records if the tool runs frequently (e.g., every hour = ~168 records with full price maps).  
**Estimated Impact:** Increasing JSON parse time over the 7-day window.  
**Fix Suggestion:**
> Consider limiting the maximum number of records retained, or archiving old records to a separate file.

---

## 8. Data Processing Efficiency
**Severity:** P2  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py) (Lines 113-158, 230-253)  
**Finding:** `calculate_rsi`, `calculate_macd`, and variance calculations use nested standard Python loops. While functional, this is CPU-heavy when processing hundreds of candles for 100 symbols.  
**Estimated Impact:** Moderate — acceptable for 100 symbols but would not scale.  
**Fix Suggestion:**
> Replace the manual loops with optimized vector operations using `numpy`, or a dedicated library like `ta`.

---

## 9. Server Endpoint Efficiency
**Severity:** P2  
**File(s):** [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py)  
**Finding:** The `/api/portfolio/generate` endpoint is fully synchronous from the client's perspective — it blocks until all data fetching, analysis, and portfolio generation is complete. There is no background processing or progressive response.  
**Fix Suggestion:**
> Decouple data fetching from the endpoint. Use a background task to periodically refresh market data, so the endpoint only reads the latest cached state and returns immediately.
