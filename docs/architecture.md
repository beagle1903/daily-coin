# Architecture Blueprint

## System Overview
- **Language:** Python 3.10+
- **CLI Framework:** Typer (with Rich for terminal formatting)
- **Data Integration:** `python-binance` for market prices.
- **News Integration:** `feedparser` for RSS aggregation, `vaderSentiment` for NLP sentiment analysis.

## Project Structure
- `main.py`: Entry point for the Typer app. Orchestrates flow.
- `binance_client.py`: Handles all interactions with the Binance API.
- `logic.py`: Pure functions containing the heuristic scoring, coin selection, and portfolio generation logic.
- `history.py`: Handles saving and evaluating past portfolios to create a feedback loop (saved in `history.json`).
- `news.py`: Fetches RSS feeds from top crypto outlets, parses headlines, and executes VADER sentiment analysis to provide heuristic modifiers.
- `tests/`: Pytest suite for calculations and logic.

## Design Patterns
- **Separation of Concerns:** CLI routing (in `main.py`) is completely separated from selection logic (`logic.py`) and data fetching (`binance_client.py`, `news.py`).
- **Heuristic Feedback Loop:** The app "learns" by keeping a rotating 30-day memory of its past picks, applying percentage gain/loss adjustments to the baseline scores.
