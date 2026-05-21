# Progress Notes

*This file contains session-to-session handoff notes for the AI.*

## Current Status
- Fully implemented the core CLI application in `main.py` using `typer`.
- Developed `logic.py` to evaluate coins based on a heuristic scoring mechanism and qualitative groups.
- Integrated `binance_client.py` for fetching real-time market data.
- Built a 30-day TTL history state manager in `history.py` to learn from past picks.
- Integrated an RSS News feed via `news.py` using `feedparser`.
- **Active Feature:** Added VADER sentiment analysis to dynamically adjust heuristic scores based on bullish/bearish headlines.
- First session tasks completed successfully.

## Next Steps
- Implement any further user requests for more advanced technical indicators (e.g., RSI, MACD).
- Expand the `KEYWORD_MAP` in `news.py` to cover more altcoins.
