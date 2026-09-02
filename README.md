# Daily Coin (Crypto Portfolio CLI)

A Python CLI (with an optional web dashboard) that generates a cryptocurrency portfolio of 9 coins by default (6 volatile, 3 stable) and learns from past performance.

## Features
- **Heuristic Feedback Loop**: Learns from previous portfolio performance. Coins that gain value are rewarded; coins that lose value are penalized in future selections.
- **News Sentiment Analysis**: Pulls the latest crypto headlines via RSS, processes them using VADER NLP, and dynamically bumps or drops a coin's heuristic score based on bullish/bearish news.
- **State Rotation**: Automatically maintains a 30-day TTL history of past portfolios.
- **Web dashboard**: FastAPI backend plus a Vite + React UI in `frontend/`.

## Local Docker (Windows 11 + Docker Desktop)

One Linux container with the same ports as the cloud workspace (Vite `5173`, API `8000`):

```powershell
docker compose up --build
```

Open [http://localhost:5173](http://localhost:5173). Full steps: [docs/local-docker.md](docs/local-docker.md).

## Setup
Run the setup script to create a virtual environment and install dependencies:
```bash
./setup.sh
```

On Windows you can also create the venv and install manually:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Ensure you have a `.env` file in the root directory with your Binance API keys and the dashboard API key (same value in both `DAILY_COIN_API_KEY` and `VITE_DAILY_COIN_API_KEY`):
```
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
DAILY_COIN_API_KEY=your_local_api_key
VITE_DAILY_COIN_API_KEY=your_local_api_key
```

The FastAPI server requires the `X-API-Key` header on `/api/*` routes. `/api/portfolio/generate` is limited to 10 requests per minute. The CLI (`python main.py run`) does not use this key.

## Running the CLI
```bash
# On Windows:
venv\Scripts\activate
# On Unix:
source venv/bin/activate

# Generate a portfolio and evaluate previous picks
python main.py run

# Show past portfolio performance
python main.py history
```

## Running the web app
```bash
# API (http://127.0.0.1:8000)
python main.py serve

# Frontend (http://localhost:5173) — from the frontend/ directory
npm install
npm run dev
```

## Tests and lint
```bash
python -m pytest
python -m ruff check .
```
On Windows without an activated venv, use `.\venv\Scripts\python.exe -m pytest` (do not run raw `pytest`).
