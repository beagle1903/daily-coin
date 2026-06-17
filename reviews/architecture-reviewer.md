# Architecture Review: Daily-Coin CLI

## Overview
This document contains an architectural review of the `daily-coin` codebase. The review assesses the project's adherence to its defined technical blueprints, separation of concerns, scalability, and overall code quality.

## 1. Adherence to Technical Blueprint
**Overall Status:** Partial Adherence

**Findings:**
- **Violation of Volatility/Stability Rules:** The primary domain rule in `docs/context.md` explicitly states: *"Volatility vs. Stability: Defined mathematically via 30-day historical klines from Binance. High standard deviation = volatile, low standard deviation = stable."* 
  However, in `logic.py`, the `CONSERVATIVE`, `MODERATE`, and `AGGRESSIVE` coin groups are hardcoded lists. Furthermore, while the mathematical variance calculation (`get_30d_variance()`) is correctly implemented in `binance_client.py`, it is completely unused (dead code). This is a critical divergence from the product context.
- **Heuristic Feedback Loop:** Successfully implemented. The application correctly records picks in `history.json` and evaluates past portfolios in `logic.py` (`load_coin_scores` and `evaluate_performance`), appropriately adjusting heuristic scores based on percentage gains/losses.
- **News Integration:** Aligns perfectly with ADR 003 and 004. It utilizes `feedparser` and `vaderSentiment` successfully to derive sentiment and apply heuristic modifiers dynamically without bloat.

## 2. Separation of Concerns & Modularity
**Overall Status:** Good

**Findings:**
- **Presentation vs. Logic:** The presentation layer (`main.py` utilizing `Typer` and `Rich`) is well segregated from business rules (`logic.py`), data fetching (`binance_client.py`), and persistence (`history.py`).
- **Inline Imports:** `logic.py` contains inline imports (e.g., `from history import get_unevaluated_records, load_history, save_history` inside `evaluate_performance()` and `from binance_client import get_technical_indicators` inside `load_coin_scores()`). While this avoids circular dependencies, it suggests that the responsibility boundaries might be slightly blurred. Refactoring the dependency graph (possibly using a dependency injection approach or moving performance evaluation logic closer to the history module) would result in cleaner architecture.
- **Orphan Context:** `main.py` contains a `calculate_aid` dummy command. This financial-aid context appears entirely unrelated to the daily crypto portfolio domain and should be evaluated for removal or separation if it stems from a broader monorepo requirement.

## 3. Scalability and Performance
**Overall Status:** Needs Improvement

**Findings:**
- **Synchronous Network Bottlenecks (N+1 Problem):** In `logic.py`'s `load_coin_scores()`, the system iterates over the entire coin universe and calls `get_technical_indicators(coin)`. This function sequentially performs synchronous HTTP requests (`client.get_historical_klines`) for each coin. For a universe of 21 coins, this results in 21 blocking network requests, noticeably degrading the CLI's responsiveness. If the coin universe scales to 100+ coins via `get_tradeable_symbols()`, the delay will be severe.
- **Recommendation for Asynchrony:** The application should migrate from the synchronous Binance `Client` to the asynchronous `AsyncClient` (provided by `python-binance`) to allow parallel fetching of klines, or utilize bulk endpoints if available. Similarly, RSS feeds in `news.py` are fetched sequentially and would benefit from `asyncio.gather`.
- **Stateless Score Calculation:** `load_coin_scores()` recalculates all historical heuristic modifiers by traversing `history.json` on every run. While fine for a 30-day TTL, performance may eventually degrade. Caching or saving a running baseline score state would be more scalable than continuous replay.

## 4. Summary of Action Items
1. **Refactor `logic.py`** to replace hardcoded arrays (`CONSERVATIVE`, etc.) with dynamic filtering using `binance_client.py`'s `get_30d_variance()` to adhere to the mathematical definition of volatility.
2. **Optimize API Calls** by introducing parallel asynchronous fetching in `binance_client.py` (specifically for klines and technical indicators) to eliminate the N+1 request bottleneck.
3. **Clean up Inline Imports** in `logic.py` by resolving circular dependencies at the architectural level.
4. **Remove or Clarify** the unrelated `calculate_aid` command in `main.py`.
