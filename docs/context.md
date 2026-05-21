# Product Context (Daily Crypto Portfolio CLI)

## Vision
To provide a fast, command-line tool that generates a daily cryptocurrency portfolio of 5 coins (3 volatile, 2 stable) using the Binance API, and features a heuristic feedback loop to "learn" from its previous picks.

## Target Users
- **Crypto Traders / Hobbyists:** Need a daily set of recommended coins split between high variance and low variance.

## Core Features & Rules
- **Volatility vs. Stability:** Defined mathematically via 30-day historical klines from Binance. High standard deviation = volatile, low standard deviation = stable.
- **Learning Mechanism:** A heuristic rule-based loop. The app saves the 5 selected coins in `history.json` (30-day TTL). If a selected coin lost value by the next run, it receives a score penalty; if it gained, a bonus.
- **Unified Workflow:** A single `run` command assesses yesterday's portfolio, updates heuristic scores, and prints today's picks.
