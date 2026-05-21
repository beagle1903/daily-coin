# Daily Coin (Crypto Portfolio CLI)

A Python CLI application for generating a daily crypto portfolio of 5 coins (3 volatile, 2 stable) and learning from past performance.

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
