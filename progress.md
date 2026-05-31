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

## Next Steps
- Implement any further user requests for more advanced technical indicators (e.g., RSI, MACD).
