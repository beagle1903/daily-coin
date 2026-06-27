# Performance Review

## Overview
A comprehensive performance analysis has been conducted on the `daily-coin` codebase. The focus was on algorithmic efficiency, network I/O, resource usage, and latency. The application is well-structured, but several critical network bottlenecks and minor algorithmic inefficiencies were identified. 

## Key Findings & Bottlenecks

### 1. Redundant Data Fetching (High Impact)
**Issue:** In `logic.py`, `pick_portfolio()` initiates two separate asynchronous batch fetch operations: `fetch_all_variances` (fetching 30 days of klines) and `fetch_all_technical_indicators` (fetching 60 days of klines). This means for an initial universe of up to 100 symbols, the application makes 200 separate historical kline requests to Binance instead of 100.
**Impact:** Doubles the network I/O time, increases the likelihood of hitting Binance's IP rate limits (HTTP 429), and significantly slows down the portfolio generation process.
**Recommendation:** Refactor data fetching to request 60 days of klines **once** per symbol. Compute both the 30-day variance and the technical indicators (RSI, MACD) from that single dataset in memory.

### 2. AsyncClient Session Overhead (Medium Impact)
**Issue:** Both `fetch_all_variances()` and `fetch_all_technical_indicators()` in `binance_client.py` instantiate a new `AsyncClient.create(...)` and close it at the end of the function. 
**Impact:** Re-creating the connection pool and completing TLS handshakes multiple times adds unnecessary latency.
**Recommendation:** Instantiate a single `AsyncClient` at the start of the `pick_portfolio` operation, pass the session to the fetch functions, and close it once all data for the run has been gathered.

### 3. Synchronous RSS Feed Parsing (Medium Impact)
**Issue:** In `news.py`, `get_latest_news()` iterates through `RSS_FEEDS` and uses `feedparser.parse(url)` sequentially. 
**Impact:** `feedparser.parse` performs a synchronous, blocking HTTP request. The total latency for fetching news is the sum of the latency of all individual RSS feed endpoints.
**Recommendation:** Parallelize the RSS fetching. Use an `asyncio` wrapper with a `ThreadPoolExecutor` or `aiohttp` to fetch the XML payloads concurrently, then parse them.

### 4. Over-fetching Ticker Data (Low Impact)
**Issue:** `get_current_prices(symbols)` uses `client.get_all_tickers()` to fetch prices for the entire Binance exchange, only to filter out a handful of symbols from the result.
**Impact:** Parses a massive JSON payload and consumes unnecessary memory and bandwidth.
**Recommendation:** If the `python-binance` client version supports it, use the endpoint that accepts a list of symbols (`/api/v3/ticker/price?symbols=["BTCUSDT","ETHUSDT"]`) to significantly reduce the response payload size.

### 5. Algorithmic Inefficiency in Weighted Sampling (Low Impact)
**Issue:** In `logic.py`, the `unique_weighted_sample` function rebuilds the `weights` array inside a `while` loop on every iteration: `weights = [scores[c] for c in pop_copy]`.
**Impact:** This results in $O(k \times N)$ complexity. Since $N$ (universe size) is currently $\le 100$ and $k$ is small, the real-world latency is negligible. However, if the symbol universe grows, this will become an algorithmic bottleneck.
**Recommendation:** Use a vectorized approach for weighted sampling without replacement, such as `numpy.random.choice(..., replace=False)`, or calculate the weights once and update them efficiently.

## Conclusion
The most critical performance optimizations for this application lie in reducing network latency. By consolidating the Binance Kline fetches into a single concurrent batch and parallelizing the RSS feed requests, the overall execution time of the CLI command can be reduced by more than 50%.
