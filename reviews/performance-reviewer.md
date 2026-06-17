# Performance & Resource Management Review

## Executive Summary
A comprehensive review of the `daily-coin` codebase was conducted with a specific focus on performance, algorithmic efficiency, memory usage, and resource management. The application generally functions well given the current small-scale datasets, but there are multiple critical inefficiencies involving redundant network requests, blocking I/O, and unoptimized loops that will degrade user experience and runtimes.

## 1. Network & API Bottlenecks (Critical)

### 1.1 Sequential API Requests for Technical Indicators
In `logic.py` -> `load_coin_scores()`, the application iterates over the entire coin universe (currently 21 coins) and calls `get_technical_indicators(coin)`. Each call synchronously hits the Binance API for historical klines (`get_klines_closes`). 
- **Impact:** This results in ~21 sequential HTTP requests. If each request takes 300ms, this loop alone blocks execution for >6 seconds. 
- **Recommendation:** Utilize asynchronous requests (e.g., `aiohttp` or `asyncio.gather`) or multithreading to fetch klines concurrently. Alternatively, if Binance supports a batched kline endpoint, use it.

### 1.2 Redundant 'All Tickers' API Calls
In `logic.py` -> `evaluate_performance()`, the function iterates over all unevaluated records. Inside the loop, it calls `get_current_prices(portfolio)`, which internally executes `client.get_all_tickers()`.
- **Impact:** Fetching all ~2,000 Binance tickers is a heavy request. Doing this inside a loop means if there are 5 past portfolios to evaluate, the exact same giant payload is fetched 5 times in a row.
- **Recommendation:** Pull `get_current_prices()` outside the loop. Fetch the current market state once, and use that cached state to evaluate all historical portfolios.

### 1.3 Synchronous RSS Feed Parsing
In `news.py` -> `get_latest_news()`, RSS feeds are fetched sequentially using `feedparser.parse(url)`.
- **Impact:** `feedparser` blocks the execution thread while making HTTP requests. As more feeds are added, execution time will increase linearly.
- **Recommendation:** Fetch feed XMLs concurrently via async/threads, and parse them afterwards.

## 2. Disk I/O & Memory Inefficiencies

### 2.1 Redundant File Reads/Writes in `history.py`
When saving a new portfolio, `add_portfolio_record()` calls `load_history()`, appends data, and calls `save_history()`. It then immediately calls `clean_old_history()`, which *again* performs `load_history()`, filters, and `save_history()`. 
- **Impact:** Two full file reads and writes occur for a single operation. 
- **Recommendation:** Pass the loaded `history` list directly into a memory-cleaning function before saving it to disk once.

### 2.2 Inefficient File I/O in Loop
In `logic.py` -> `evaluate_performance()`, the entire `history.json` file is loaded into memory, modified, and written back to disk **for every single unevaluated record** in the loop.
- **Impact:** `O(N)` disk reads and writes where `N` is the number of unevaluated records.
- **Recommendation:** Load `history` once before the loop, update the records in memory as they are evaluated, and perform a single `save_history()` after the loop concludes.

## 3. Algorithmic & CPU Inefficiencies

### 3.1 Repeated Lexicon Initialization
In `news.py` -> `analyze_news_impact()`, the VADER `SentimentIntensityAnalyzer()` is instantiated inside the function.
- **Impact:** VADER loads its lexicon file from disk upon initialization. Doing this repeatedly adds hidden CPU and disk overhead.
- **Recommendation:** Instantiate `analyzer = SentimentIntensityAnalyzer()` once at the module level (globally) or implement a singleton pattern.

### 3.2 O(N) Array Removals in Weighted Sampling
In `logic.py` -> `pick_portfolio()` -> `unique_weighted_sample()`, elements are sampled without replacement by removing the chosen element from `pop_copy` (`pop_copy.remove(choice)`) and recreating the `weights` array on every iteration.
- **Impact:** `list.remove()` is an $O(N)$ operation. Building weights is also $O(N)$. Total complexity is $O(k \times N)$. 
- **Recommendation:** While negligible for $N=21$, as the coin universe grows, a more efficient weighted sampling without replacement algorithm (e.g., A-Res algorithm) or indexing manipulation should be used to avoid mid-array deletions.

### 3.3 Suboptimal Ticker Fetching Pattern
The CLI uses `client.get_ticker()` in `get_tradeable_symbols()` to sort by volume (returning a heavy payload of 24h stats for all coins). Almost immediately after, `pick_portfolio()` triggers `get_current_prices()`, which fetches `client.get_all_tickers()` (returning just prices).
- **Recommendation:** Cache the initial heavy 24h ticker payload in memory. It contains both prices and volumes, meaning the subsequent lightweight price-fetch call can be entirely eliminated.

## Conclusion
The immediate priority should be resolving the sequential Binance network requests and the O(N) file I/O operations in loops. These changes will yield the most noticeable runtime improvements for the end user.
