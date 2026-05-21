# Daily Coin (Crypto Portfolio CLI)

A Python CLI application for generating a daily crypto portfolio of 5 coins (3 volatile, 2 stable) and learning from past performance.

## Features
- **Heuristic Feedback Loop**: Learns from yesterday's portfolio performance. Coins that gain value are rewarded; coins that lose value are penalized in future selections.
- **News Sentiment Analysis**: Pulls the latest crypto headlines via RSS, processes them using VADER NLP, and dynamically bumps or drops a coin's heuristic score based on bullish/bearish news.
- **State Rotation**: Automatically maintains a 30-day TTL history of past portfolios.

## Setup
Run the setup script to create a virtual environment and install dependencies:
```bash
./setup.sh
```

Ensure you have a `.env` file in the root directory with your Binance API keys:
```
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
```

## Running the CLI
```bash
# On Windows:
venv\Scripts\activate
# On Unix:
source venv/bin/activate

# Generate today's portfolio and evaluate yesterday's picks
python main.py run
```
