# Code Review Summary: daily-coin

**Date:** 2026-08-07  
**Reviewers:** Security, Architecture, Test Coverage, Performance, Business Logic

---

## P0 — Critical Issues

### 1. [ARCHITECTURE] Massive Code Duplication Between `main.py` and `server.py`
**Source:** Architecture Review  
**File(s):** [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py#L100-L168), [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py#L99-L175)  
**Description:** ~80 lines of portfolio generation logic (symbol categorization, score calculation, portfolio selection, $0-price replacement loop) are duplicated nearly identically between the CLI and API server. Any business logic change must be applied in two places.  
**Agent Prompt:**
> Extract the portfolio generation and fallback orchestration logic from `main.py` and `server.py` into a new `portfolio_service.py` file. The service should expose an async function `generate_portfolio(stable_count, volatile_count) -> PortfolioResult` that encapsulates: symbol fetching, market data retrieval, news analysis, scoring, portfolio selection, and price verification with replacement. Both `main.py` and `server.py` should call this unified service.

---

### 2. [BUSINESS LOGIC] Unbounded Score Inflation in Heuristic System
**Source:** Business Logic Review  
**File(s):** [`logic.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/logic.py#L14-L20)  
**Description:** `adjustment = p_change * 100` converts a 5% gain into +5.0 points. Adjustments stack linearly across ALL historical records with no upper cap. A coin with a history of strong performance will have a score of 50-100+, making it 10-100× more likely to be selected than others, destroying portfolio diversification.  
**Agent Prompt:**
> In `logic.py`, refactor `load_coin_scores` to: (1) cap per-record adjustment to ±5.0 max, (2) average adjustments across history records instead of summing, (3) add a global score ceiling of 30.0 and floor of 1.0. This prevents runaway feedback loops while still rewarding past performance.

---

### 3. [PERFORMANCE] Redundant History File I/O (3× per request)
**Source:** Performance Review  
**File(s):** [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py#L86-L126), [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py#L28-L113)  
**Description:** `load_history()` is called up to 3 times per single request (via `get_unevaluated_records`, directly, and again after evaluation). Each call reads from disk and parses JSON.  
**Agent Prompt:**
> Refactor the portfolio generation flow to call `load_history()` once at the start, pass the result through the pipeline, and only reload after `save_history()` mutations. Update `get_unevaluated_records()` to accept an optional `history` parameter.

---

### 4. [PERFORMANCE] No Caching of Market Data or Tradeable Symbols
**Source:** Performance Review  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py#L39-L66), [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py#L100-L108)  
**Description:** Both CLI and FastAPI server fetch `get_tradeable_symbols` (downloading ALL tickers) and 60 days of historical klines for 100 symbols on every execution/request. This adds 5-10s latency and risks Binance IP bans.  
**Agent Prompt:**
> Add TTL-based in-memory caching to `get_tradeable_symbols` (TTL: 1 hour) and `fetch_all_market_data` (TTL: 15 minutes) in `binance_client.py`. Use `functools.lru_cache` with a timestamp check or a simple dict-based cache with expiry.

---

### 5. [TEST COVERAGE] `news.py` and `server.py` Have Zero Tests
**Source:** Test Coverage Review  
**File(s):** [`news.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/news.py), [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py)  
**Description:** Two of the most complex modules — RSS fetching with sentiment analysis and the entire FastAPI server with 5 endpoints — have zero test coverage.  
**Agent Prompt:**
> Create `tests/test_news.py` and `tests/test_server.py`. For news: mock `feedparser.parse` with valid, empty, and malformed RSS responses; test `analyze_news_impact` with bullish/bearish/neutral headlines. For server: use FastAPI `TestClient` to test all 5 endpoints with mocked dependencies.

---

## P1 — High Priority Issues

### 6. [SECURITY] `.env` Not in `.gitignore`
**Source:** Security Review  
**File(s):** [`.gitignore`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/.gitignore)  
**Description:** The `.gitignore` only excludes `venv/` and `__pycache__/`. The `.env` file containing Binance API keys is NOT excluded, risking credential exposure.  
**Agent Prompt:**
> Add `.env` to the `.gitignore` file. Verify that `.env` has not been previously committed by running `git log --all -- .env`. If it has, remove it from git history using `git filter-branch` or `git-filter-repo`.

---

### 7. [SECURITY] Mutable Global State (`USE_MOCK_DATA`)
**Source:** Security Review, Architecture Review  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py#L12-L27)  
**Description:** A single transient Binance API failure permanently sets `USE_MOCK_DATA = True` globally. In the FastAPI server, this means ALL future requests for ALL users will return mock data until server restart. This is both a security and reliability issue.  
**Agent Prompt:**
> Refactor `binance_client.py` to replace the global `USE_MOCK_DATA` flag with per-request error handling. Each function should catch API errors and return a result object that indicates whether mock data was used, without mutating global state. Alternatively, implement a circuit-breaker pattern with auto-reset after a timeout.

---

### 8. [SECURITY] No API Authentication or Rate Limiting
**Source:** Security Review  
**File(s):** [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py#L47-L202)  
**Description:** All FastAPI endpoints are publicly accessible. The `/api/portfolio/generate` endpoint triggers expensive external API calls with no rate limiting, enabling DoS.  
**Agent Prompt:**
> Add API key authentication middleware to `server.py` using FastAPI's dependency injection. Implement rate limiting with `slowapi` (e.g., 10 requests/minute for `/api/portfolio/generate`). Add `Query(..., gt=0, le=50)` constraints on stable/volatile parameters.

---

### 9. [SECURITY] Race Conditions in JSON File Writes
**Source:** Security Review, Architecture Review  
**File(s):** [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py#L43-L45), [`history.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/history.py#L17-L19)  
**Description:** Concurrent API requests can trigger simultaneous writes to `settings.json` and `history.json`, causing file corruption. Writes are not atomic.  
**Agent Prompt:**
> Install the `filelock` package and wrap all JSON write operations in `history.py` and `server.py` with file locks. Implement atomic writes by writing to a temp file first, then renaming.

---

### 10. [BUSINESS LOGIC] 7-Day History TTL Discards Valuable Data
**Source:** Business Logic Review  
**File(s):** [`history.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/history.py#L6)  
**Description:** Records older than 7 days are permanently deleted. The scoring system only considers very recent performance, and portfolios generated more than 7 days ago can never be evaluated.  
**Agent Prompt:**
> Increase `TTL_SECONDS` in `history.py` to 30 days (30 * 24 * 60 * 60). Consider creating a separate 'score ledger' that persists aggregated performance data indefinitely, while the detailed history records can still be TTL'd.

---

### 11. [BUSINESS LOGIC] Variance-Based Stable/Volatile Split is Arbitrary
**Source:** Business Logic Review  
**File(s):** [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py#L106-L108), [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py#L119-L121)  
**Description:** The hardcoded 1/3 split for stable vs volatile is relative — in highly volatile markets, the "stable" coins may still be very volatile in absolute terms.  
**Agent Prompt:**
> Make the variance split configurable via `settings.json` (e.g., `variance_percentile: 33`). Additionally, consider adding an absolute variance threshold as a secondary filter.

---

### 12. [BUSINESS LOGIC] Performance Evaluation Misattributes Failed Fetches as -100%
**Source:** Business Logic Review  
**File(s):** [`logic.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/logic.py#L96-L103)  
**Description:** If `curr_p == 0` due to a transient API failure (not actual delisting), the coin gets a -100% penalty that permanently damages its future score.  
**Agent Prompt:**
> In `evaluate_performance` in `logic.py`, when `curr_p == 0` and `old_p > 0`, check if the coin still exists in the current tradeable symbols list before recording -100%. If it still exists, record 0.0 (neutral) instead.

---

### 13. [PERFORMANCE] Unbatched Price Lookups in Replacement Loop
**Source:** Performance Review  
**File(s):** [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py#L136-L164), [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py#L147-L171)  
**Description:** When a coin has $0 price, the replacement loop calls `get_current_prices([candidate])` one at a time — each is a separate API round-trip.  
**Agent Prompt:**
> Refactor the replacement logic to batch-fetch prices for ALL remaining candidates at once using `get_current_prices(remaining_candidates)`, then iterate locally to find valid replacements.

---

### 14. [PERFORMANCE] Blocking SentimentIntensityAnalyzer at Import Time
**Source:** Performance Review  
**File(s):** [`news.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/news.py#L6-L10)  
**Description:** `SentimentIntensityAnalyzer()` is instantiated at module import, adding ~200-500ms startup latency even for `--help` or `history` commands.  
**Agent Prompt:**
> Refactor `news.py` to use lazy initialization: replace the global `GLOBAL_ANALYZER` with a `_get_analyzer()` function that creates the instance on first call and caches it.

---

### 15. [TEST COVERAGE] No Error Path Tests for CLI
**Source:** Test Coverage Review  
**File(s):** [`tests/test_main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/tests/test_main.py)  
**Description:** Only the happy path is tested. No coverage for: empty symbols, $0 prices, news failures, market data failures, or the `history` command.  
**Agent Prompt:**
> Add error path tests to `tests/test_main.py`: (1) mock `get_tradeable_symbols` returning `[]`, verify error message; (2) mock `get_current_prices` returning `{coin: 0.0}`, verify replacement loop; (3) test the `history` command with mocked evaluated records.

---

### 16. [ARCHITECTURE] Tight Coupling of I/O in `history.py`
**Source:** Architecture Review  
**File(s):** [`history.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/history.py)  
**Description:** Functions like `add_portfolio_record()` directly read/write files, making them hard to test and preventing any future migration to a database.  
**Agent Prompt:**
> Separate data access from business logic in `history.py` by introducing a storage abstraction. Functions should operate on in-memory data structures, with a thin I/O layer that handles persistence.

---

## P2 — Medium Priority Issues

### 17. [SECURITY] Overly Permissive CORS Configuration
**Source:** Security Review  
**File(s):** [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py#L16-L22)  
**Agent Prompt:**
> Restrict CORS `allow_methods` to `['GET', 'POST']` and explicitly list required headers instead of `["*"]`.

---

### 18. [SECURITY] Information Disclosure in Error Logging
**Source:** Security Review  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py)  
**Agent Prompt:**
> Replace `print(f"Warning: ... {type(e).__name__}: {e}")` calls with Python's `logging` module at `WARNING` level.

---

### 19. [ARCHITECTURE] Recursive Fallback Pattern
**Source:** Architecture Review  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py#L64-L66)  
**Agent Prompt:**
> Replace recursive fallback calls (where functions set `USE_MOCK_DATA = True` then call themselves) with explicit if/else branching.

---

### 20. [ARCHITECTURE] Hardcoded Configuration Values
**Source:** Architecture Review  
**File(s):** Various  
**Agent Prompt:**
> Create a `constants.py` file centralizing all tunable parameters: semaphore size (15), RSI period (14), MACD periods (12/26/9), history TTL (7 days), variance split ratio (1/3), score initial value (10.0), sentiment threshold (0.1), sentiment multiplier (2.0).

---

### 21. [BUSINESS LOGIC] VADER Sentiment Poorly Suited for Crypto
**Source:** Business Logic Review  
**File(s):** [`news.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/news.py#L78-L106)  
**Agent Prompt:**
> Raise the VADER compound threshold from 0.1 to 0.25 to reduce false positives. Add crypto-specific lexicon entries to VADER (e.g., "moon" → positive, "rug pull" → negative, "pump" → positive).

---

### 22. [BUSINESS LOGIC] No Deduplication in Sentiment Impacts
**Source:** Business Logic Review  
**File(s):** [`news.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/news.py#L92-L105)  
**Agent Prompt:**
> In `analyze_news_impact`, aggregate sentiment impacts per coin by averaging the compound score across headlines, rather than applying each headline's adjustment additively.

---

### 23. [BUSINESS LOGIC] Simplistic Keyword Matching for News
**Source:** Business Logic Review  
**File(s):** [`news.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/news.py#L17-L39)  
**Agent Prompt:**
> Dynamically generate `KEYWORD_MAP` from the Binance tradeable symbols list instead of maintaining a hardcoded dictionary. Handle compound terms and special characters in matching.

---

### 24. [PERFORMANCE] `get_all_tickers()` Fallback Fetches Entire Exchange
**Source:** Performance Review  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py#L104-L107)  
**Agent Prompt:**
> Replace the `get_all_tickers()` fallback with individual per-symbol price fetches, or cache the full ticker list with a TTL.

---

### 25. [PERFORMANCE] Manual Math Loops for RSI/MACD/Variance
**Source:** Performance Review  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py#L113-L253)  
**Agent Prompt:**
> Consider replacing manual RSI, MACD, and variance loops with `numpy` vectorized operations or a dedicated library like `ta` for better performance at scale.

---

### 26. [TEST COVERAGE] Missing Edge Case Tests for `logic.py`
**Source:** Test Coverage Review  
**File(s):** [`tests/test_logic.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/tests/test_logic.py)  
**Agent Prompt:**
> Add edge case tests: `pick_portfolio` with empty `available_stable`, `load_coin_scores` with empty universe, `evaluate_performance` with all-zero entry prices.

---

### 27. [ARCHITECTURE] No Dependency Injection / Separation of Concerns
**Source:** Architecture Review  
**File(s):** [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py)  
**Agent Prompt:**
> Decouple presentation from logic. Ensure `portfolio_service.py` returns pure data structures, and relegate all Rich `Table` creation and `console.print` calls strictly to the outermost CLI presentation layer.

---

## Statistics

| Severity | Count |
|----------|-------|
| **P0 — Critical** | 5 |
| **P1 — High** | 11 |
| **P2 — Medium** | 11 |
| **Total** | 27 |

| Category | Count |
|----------|-------|
| Security | 4 (P1) + 2 (P2) = 6 |
| Architecture | 1 (P0) + 2 (P1) + 3 (P2) = 6 |
| Test Coverage | 1 (P0) + 1 (P1) + 1 (P2) = 3 |
| Performance | 2 (P0) + 2 (P1) + 2 (P2) = 6 |
| Business Logic | 1 (P0) + 3 (P1) + 3 (P2) = 7 |
