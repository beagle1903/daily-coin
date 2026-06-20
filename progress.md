# Progress Notes

*This file contains session-to-session handoff notes for the AI.*

## Current Status
- Fully implemented the core CLI application in `main.py` using `typer`.
- Developed `logic.py` to evaluate coins based on a heuristic scoring mechanism and qualitative groups.
- Integrated `binance_client.py` for fetching real-time market data.
- Built a 30-day TTL history state manager in `history.py` to learn from past picks.
- Integrated an RSS News feed via `news.py` using `feedparser`.
- Added VADER sentiment analysis to dynamically adjust heuristic scores based on bullish/bearish headlines.
- Expanded the coin universe in `logic.py` with more coins across conservative, moderate, and aggressive categories to offer a wider portfolio.
- Added `--stable` and `--volatile` command-line options in `main.py` to allow customized portfolio sizes (defaults to 2 stable and 3 volatile).

- Expanded the `KEYWORD_MAP` in `news.py` to properly cover all altcoins defined in `logic.py`.
- Refactored `main.py` Typer app to support multiple commands.
- Reverted identity shift: project is purely a daily crypto portfolio CLI.
- Implemented RSI and MACD technical indicators in `binance_client.py` and integrated them into `logic.py`'s scoring heuristic.
- Fixed `test_load_coin_scores` unit test to mock `get_technical_indicators`, preventing real Binance API calls and resolving test failure.
- Created unit tests for `calculate_rsi` and `calculate_macd` math in `tests/test_binance_client.py`.

- Implemented asynchronous API fetching (`AsyncClient` + `asyncio.gather`) to remove the N+1 network bottleneck in Binance data fetching.
- Removed hardcoded category arrays and replaced them with dynamic math-based 30-day variance sorting.
- Cleaned up inefficient memory I/O in `history.py` to prevent redundant reads and writes.
- Fixed a Unicode printing bug on Windows for the Rich console by injecting `chcp 65001`.
- Re-wrote the test suite to strictly use pytest `tmp_path` to avoid unsafe OS operations and patched API requests.
- Verified application execution and generated today's recommended portfolio.
- Added a new `history` subcommand to the Typer app to display performance of all past evaluated portfolios.
- Successfully ran the Typer CLI `run` command to evaluate the previous portfolio, fetch RSS news feeds, analyze news sentiment, and print today's recommended portfolio.
- Updated `AGENTS.md` and `docs/architecture.md` with quick command references and developer execution guides so future agents can run and test the app immediately without reading multiple documents.



## Next Steps
- Continue adding more rigorous tests and error handling.
- Review and refine the UI display as needed.
