# Test Coverage & Quality Review Report

**Date:** 2026-06-17
**Component:** `daily-coin` CLI Project
**Focus:** Test Coverage, Testing Strategies, Edge Cases, and Test Quality

## 1. Overall Test Coverage Summary

Based on a test run using `pytest --cov`, the project's overall coverage stands at **42%** (416 total statements, 242 missed).

- **`tests/test_binance_client.py`**: 100% line coverage of the test file, but tests only functional parts of `binance_client.py`, leaving the target file at **57%** covered.
- **`tests/test_history.py`**: 100% line coverage of the test file, leaving `history.py` at **70%** covered.
- **`tests/test_logic.py`**: 100% line coverage of the test file, leaving `logic.py` at **39%** covered.
- **`main.py`**: **0%** coverage.
- **`news.py`**: **0%** coverage.

---

## 2. File-by-File Analysis & Missing Coverage

### `main.py` (0% Covered)
- **Missing**: The entire CLI application logic (`run` and `calculate_aid` commands).
- **Recommendation**: Utilize Typer's `CliRunner` to test CLI entry points. Mock out side effects such as console printing and history writing to ensure the logic flows correctly without real I/O.

### `news.py` (0% Covered)
- **Missing**: RSS parsing (`get_latest_news`) and sentiment analysis (`analyze_news_impact`).
- **Recommendation**: Mock `feedparser.parse` to return deterministic sample RSS feeds. Test the sentiment logic using sample headlines to verify that the VADER integration works, including its fallback behavior if the dependency is missing.
- **Edge Cases Missed**: Network timeouts, missing or malformed RSS elements, and headlines without recognized keywords.

### `logic.py` (39% Covered)
- **Tested**: `get_coin_universe` and a basic sunny-day scenario for `load_coin_scores`.
- **Missing**: `pick_portfolio`, `evaluate_performance`, and various conditional modifiers in `load_coin_scores` (such as handling `sentiment_impacts`, RSI thresholds, and MACD comparisons).
- **Edge Cases Missed**:
  - Processing history when performance data is empty or structurally malformed.
  - Scenario where `stable_count` or `volatile_count` requested exceeds the available valid symbols.
  - Verification that the minimum score clamping logic (`score < 1.0`) actually engages correctly.

### `binance_client.py` (57% Covered)
- **Tested**: Pure mathematical calculations (`calculate_rsi`, `calculate_macd`).
- **Missing**: All direct Binance API interactions (`get_tradeable_symbols`, `get_current_prices`, `get_30d_variance`, `get_klines_closes`).
- **Edge Cases Missed**:
  - Handling of API rate limits, connection timeouts, and authentication errors. 
  - The current code uses a bare `except Exception:` in `get_klines_closes` to return an empty array—this error masking is completely untested.

### `history.py` (70% Covered)
- **Tested**: `clean_old_history`.
- **Missing**: `add_portfolio_record`, `get_unevaluated_records`, and error-handling paths inside `load_history`.
- **Edge Cases Missed**:
  - Handling `json.JSONDecodeError` if `history.json` becomes corrupted.
  - Attempting to load when the file is absent.

---

## 3. Test Quality and Strategy Observations

1. **Lack of Mocking for External Dependencies**: 
   The current test suite completely bypasses testing functions that hit the network (Binance API or RSS feeds). A comprehensive mocking strategy (using `unittest.mock` or `pytest-mock`) is critical. Currently, `test_logic.py` uses `monkeypatch` adequately for internal components, but this practice should be extended to external API clients.

2. **Dangerous File I/O in Tests**: 
   `test_history.py` writes to and deletes a physical `history.json` in the current working directory, relying on a setup/teardown fixture.
   - *Critique*: If the test crashes mid-execution, it leaves a dirty state, and it prevents reliable parallel test execution. It might also accidentally overwrite actual user data during local test runs.
   - *Improvement*: Refactor tests to utilize pytest's built-in `tmp_path` fixture to isolate file operations.

3. **Bare Exceptions Masking Failures**: 
   Files like `binance_client.py` and `news.py` use broad `except Exception:` blocks.
   - *Critique*: Bare exceptions are an anti-pattern as they swallow critical errors (including `KeyboardInterrupt`) and make debugging very difficult.
   - *Improvement*: Refactor code to catch specific network or parsing exceptions. Tests should then explicitly trigger these exceptions to guarantee the fallback logic functions as intended.

4. **Absence of Integration Testing**: 
   Currently, only isolated unit tests exist for pure functions. There are no tests to simulate an end-to-end portfolio generation pipeline. Establishing tests that verify data hand-offs (e.g., `news.py` -> `logic.py` -> `binance_client.py`) will significantly improve confidence in the system.

---

## 4. Prioritized Action Plan for Improvements

1. **Implement CLI Tests**: Introduce tests for `main.py` using `typer.testing.CliRunner`.
2. **Mock Network Clients**: Add `pytest-mock` or `responses` to properly simulate Binance Client API responses and RSS feed data, ensuring 100% coverage of external-facing functions.
3. **Refactor Error Handling**: Replace bare `except Exception:` with explicit exception classes, and add tests to verify the resilience of these specific failure paths.
4. **Fix Test Isolation**: Update `test_history.py` to use `tmp_path` instead of relying on a shared `history.json` file.
5. **Boost Branch Coverage**: Write targeted unit tests for untested conditional branches in `logic.py` (specifically RSI, MACD, and sentiment score modifications).
