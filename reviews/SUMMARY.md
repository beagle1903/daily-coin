# Parallel Code Review Summary

This document synthesizes the findings from 5 specialized subagents (Security, Architecture, Test Coverage, Performance, and Business Logic) regarding the `daily-coin` codebase. The findings are prioritized into P0 (Critical), P1 (High), and P2 (Medium) issues, with corresponding actionable agent prompts for remediation.

---

## P0: Critical Issues

### 1. Domain Identity Crisis & Dummy Implementation (Business Logic)
The codebase suffers from a split identity. The documentation strictly describes a "Crypto Portfolio CLI", but recent development added a `calculate_aid` command for a "Financial Aid CLI". This command is a dummy scaffold that blindly returns a hardcoded `$10,000` and does no validation on the inputted JSON. 
**Agent Prompt for Fix:** 
> "Resolve the domain identity of the repository. If pivoting to a Financial Aid tool, update `docs/context.md` to define the rules, implement a real rules engine in a separate module (e.g., `aid_calculator.py`), add JSON schema validation for the student profile, and remove the legacy crypto logic. Otherwise, delete the `calculate_aid` command."

### 2. Network Bottlenecks & The N+1 Problem (Performance & Architecture)
Synchronous HTTP requests to the Binance API are executed sequentially inside loops. `load_coin_scores()` fetches klines individually for every coin, causing severe blocking and making the application extremely slow. Furthermore, `evaluate_performance()` unnecessarily calls `get_all_tickers()` multiple times within a loop.
**Agent Prompt for Fix:** 
> "Refactor `binance_client.py` and `logic.py` to fetch technical indicators concurrently using `asyncio` or `AsyncClient`. Pull the `get_current_prices()`/`get_all_tickers()` call out of the `evaluate_performance` loop to execute only once and cache the state."

---

## P1: High Priority Issues

### 3. Missing External Mocks & Dangerous Test I/O (Test Coverage)
Overall coverage is only 42%. Core modules like `main.py` and `news.py` have 0% coverage. Tests do not mock external network calls, and `test_history.py` performs unsafe writes directly to the physical `history.json` file in the current working directory.
**Agent Prompt for Fix:** 
> "Implement a comprehensive mocking strategy using `pytest-mock` for all network calls (Binance API, RSS feeds). Refactor `test_history.py` to use pytest's `tmp_path` fixture for safe file I/O isolation. Add CLI tests using Typer's `CliRunner`."

### 4. Blueprint Violations in Heuristic Logic (Architecture)
The architecture dictates that volatility and stability should be determined mathematically via 30-day historical kline variance. Although `get_30d_variance()` exists, `logic.py` ignores it and uses hardcoded arrays (`CONSERVATIVE`, `MODERATE`, `AGGRESSIVE`).
**Agent Prompt for Fix:** 
> "Refactor `logic.py` to strictly adhere to the technical blueprint. Remove the hardcoded arrays for coin groups and dynamically categorize coins by consuming `get_30d_variance()` from `binance_client.py`."

### 5. Input Validation & API Rate Limiting (Security)
The Typer CLI arguments for `--stable` and `--volatile` lack bounds checking, allowing negative integers that will break downstream logic. Additionally, bare API requests lack rate-limit management.
**Agent Prompt for Fix:** 
> "Add numerical bound constraints to the Typer CLI inputs in `main.py`. Implement backoff and retry logic in `binance_client.py` to handle potential HTTP 429 rate limit exceptions securely."

---

## P2: Medium Priority Issues

### 6. Suboptimal File I/O & CPU Usage (Performance)
The `SentimentIntensityAnalyzer` is redundantly re-initialized, causing high disk/CPU overhead from loading lexicons. Additionally, operations in `history.py` and `evaluate_performance` cause $O(N)$ repeated reading and writing of `history.json`.
**Agent Prompt for Fix:** 
> "Optimize resource management: instantiate `SentimentIntensityAnalyzer` globally as a singleton. Refactor `history.py` and `evaluate_performance()` to read the JSON file once into memory, perform all operations, and write the file to disk exactly once."

### 7. Code Smells & Bare Exceptions (Architecture & Coverage)
`logic.py` uses inline imports to avoid circular dependencies, indicating blurred boundaries. Across the application, widespread `except Exception:` blocks mask errors like `KeyboardInterrupt` and network timeouts.
**Agent Prompt for Fix:** 
> "Replace all bare `except Exception:` blocks with specific exceptions and ensure tests trigger these paths. Resolve the circular dependencies causing inline imports in `logic.py` by refactoring the module boundaries."
