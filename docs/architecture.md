# Architecture Blueprint

## System Overview
- **Language:** Python 3.10+
- **CLI Framework:** Typer (with Rich for terminal formatting)
- **API:** FastAPI (`server.py`) served via `python main.py serve`
- **Frontend:** Vite + React SPA in `frontend/`
- **Data Integration:** `python-binance` for market prices.
- **News Integration:** `feedparser` for RSS aggregation, `vaderSentiment` for NLP sentiment analysis.
- **Quality:** pytest, ruff, GitHub Actions CI on pull requests and pushes to `main`.

## Project Structure
- `main.py`: Entry point for the Typer app (`run`, `history`, `serve`). Presentation layer only.
- `portfolio_service.py`: Shared async portfolio generation pipeline used by the CLI and the API.
- `binance_client.py`: Handles all interactions with the Binance API (variance, RSI, MACD, caching, mock fallback).
- `logic.py`: Pure functions containing the heuristic scoring, coin selection, and portfolio generation logic.
- `history.py`: `JsonHistoryRepository` for saving and evaluating past portfolios (saved in `history.json`, 30-day TTL).
- `news.py`: Fetches RSS feeds from top crypto outlets, parses headlines, and executes VADER sentiment analysis to provide heuristic modifiers.
- `constants.py`: Centralized tunable parameters (cache TTLs, indicator periods, score caps, VADER settings, portfolio count max).
- `server.py`: FastAPI REST endpoints for settings, history, and portfolio generation. `stable`/`volatile` query params and settings counts are bounded (`gt=0`, `le=PORTFOLIO_COUNT_MAX`).
- `frontend/`: Vite + React dashboard for portfolio suggestions, history, and news sentiment.
- `tests/`: Pytest suite for calculations, CLI, news, and API.

## Design Patterns
- **Separation of Concerns:** CLI routing (`main.py`) and HTTP routing (`server.py`) are separated from selection logic (`logic.py`) and data fetching (`binance_client.py`, `news.py`). Both entry points call `portfolio_service.generate_portfolio`.
- **Heuristic Feedback Loop:** The app "learns" by keeping a rotating 30-day memory of its past picks, applying percentage gain/loss adjustments to the baseline scores (capped in `logic.py`).

## Development & Execution Commands
- **Activate Virtual Environment (Windows):** `venv\Scripts\activate`
- **Install Dependencies:** `pip install -r requirements.txt`
- **Run the CLI Application:** `.\venv\Scripts\python.exe main.py run` (or `python main.py run` after activating venv)
- **Run the History Command:** `.\venv\Scripts\python.exe main.py history`
- **Run the API Server:** `.\venv\Scripts\python.exe main.py serve`
- **Run the Frontend:** `npm run dev` in `frontend/`
- **Run Tests:** `.\venv\Scripts\python.exe -m pytest`
- **Lint:** `.\venv\Scripts\python.exe -m ruff check .`
- **Docker Desktop (Windows 11):** `docker compose up --build` — API `http://localhost:8000`, frontend `http://localhost:5173`. See `docs/local-docker.md`.
