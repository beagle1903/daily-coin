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
- Implemented dummy `calculate-aid` command (per tasks.json, feat-1) to calculate financial aid from a student profile.
- Implemented RSI and MACD technical indicators in `binance_client.py` and integrated them into `logic.py`'s scoring heuristic.
- Fixed `test_load_coin_scores` unit test to mock `get_technical_indicators`, preventing real Binance API calls and resolving test failure.
- Created unit tests for `calculate_rsi` and `calculate_macd` math in `tests/test_binance_client.py`.

## Next Steps
- Implement actual financial aid eligibility logic in `calculate_aid` instead of the dummy placeholder.
