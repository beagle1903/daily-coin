# Architecture Review: daily-coin

**Date:** 2026-08-07  
**Reviewer:** Architecture Review Agent

---

## 1. Massive Code Duplication Between `main.py` and `server.py`
**Severity:** P0  
**File(s):** [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py) (Lines 122-168), [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py) (Lines 135-175)  
**Finding:** The complex business logic of verifying non-zero entry prices, discarding invalid coins, and searching for replacements is duplicated exactly between the CLI and API server. ~80 lines of portfolio generation logic are nearly identical across both modules. This is a maintenance nightmare — any business logic change must be applied in two places.  
**Fix Suggestion:**
> Extract the portfolio generation and fallback orchestration logic from `main.py` and `server.py` into a new `portfolio_service.py` file. Both `main.py` and `server.py` should call this unified service instead of duplicating the logic.

---

## 2. Mutable Global State (`USE_MOCK_DATA`, `_client`)
**Severity:** P1  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py) (Lines 12, 26, 65, 110, 203, 215, 257)  
**Finding:** Any single API failure mutates the global `USE_MOCK_DATA` variable to `True`. In the context of `server.py`, a single transient failure will force all future web requests for all users into offline mock mode until the server restarts.  
**Fix Suggestion:**
> Refactor `binance_client.py` to remove global state mutation of `USE_MOCK_DATA`. Implement transient error retries or bubble up specific errors so the caller can decide whether to use mock data for that specific request.

---

## 3. Concurrency & Scalability Risks
**Severity:** P1  
**File(s):** [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py) (Lines 43, 96, 180), [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py) (Line 200)  
**Finding:** `server.py` writes to `history.json` and `settings.json` without file locks, risking file corruption on concurrent requests. Furthermore, `fetch_all_market_data` creates and destroys a new `AsyncClient` connection on every single request.  
**Fix Suggestion:**
> Implement thread-safe file locking (using the `filelock` package) for all JSON write operations. Refactor `binance_client.py` to maintain a singleton `AsyncClient` connection pool during the lifetime of the FastAPI app.

---

## 4. Missing PEP 8 Spacing
**Severity:** P2  
**File(s):** [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py) (Lines 227-228)  
**Finding:** The `show_history()` and `serve_api()` functions lack proper PEP 8 spacing (missing blank line between top-level definitions), suggesting rushed additions.  
**Fix Suggestion:**
> Add a blank line between `show_history()` and the `@app.command(name="serve")` decorator.

---

## 5. Async/Sync Mixing
**Severity:** P2  
**File(s):** [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py) (Lines 124, 141), [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py)  
**Finding:** `main.py` executes in an asyncio event loop but makes blocking synchronous network calls like `get_current_prices` which halts the entire loop.  
**Fix Suggestion:**
> Migrate all network-bound functions in `binance_client.py` to use `AsyncClient` exclusively. Update callers in `main.py` and `server.py` to `await` these functions directly.

---

## 6. Tight Coupling of I/O in `history.py`
**Severity:** P1  
**File(s):** [`history.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/history.py)  
**Finding:** Functions like `add_portfolio_record()` directly read/write files, making them hard to test and preventing any future migration to a database.  
**Fix Suggestion:**
> Separate data access from business logic by introducing a storage abstraction layer.

---

## 7. Hardcoded Configuration Values
**Severity:** P2  
**File(s):** Various  
**Finding:** Magic numbers throughout (semaphore=15, RSI period=14, MACD periods, TTL=7 days, variance split=1/3) should be in a central config.  
**Fix Suggestion:**
> Create a `constants.py` or extend `config.py` to centralize all tunable parameters.

---

## 8. Recursive Fallback Pattern
**Severity:** P2  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py) (Lines 64-66, 109-111)  
**Finding:** `get_tradeable_symbols()` and `get_current_prices()` recursively call themselves after toggling `USE_MOCK_DATA`, which is fragile.  
**Fix Suggestion:**
> Replace recursive fallback with explicit if/else branching to return mock data directly.

---

## 9. No Dependency Injection
**Severity:** P2  
**File(s):** Various  
**Finding:** All modules directly import their dependencies, making testing and swapping implementations difficult.  
**Fix Suggestion:**
> Introduce dependency injection patterns, especially for `logic.py` which should accept data as parameters rather than importing I/O modules.

---

## 10. Separation of Concerns
**Severity:** P2  
**File(s):** [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py) (Lines 83-94, 177-190)  
**Finding:** Business logic is tightly coupled with presentation. `main.py` creates Rich tables and prints to the console directly within the core execution path.  
**Fix Suggestion:**
> Decouple presentation from logic. Ensure the future `portfolio_service.py` returns pure data structures, and relegate all Rich `Table` creation and `console.print` calls strictly to the outermost CLI presentation layer.
