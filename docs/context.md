# Product Context (Crypto Portfolio CLI)

## Vision
To provide a fast, command-line tool that generates a cryptocurrency portfolio of 9 coins (6 volatile, 3 stable) using the Binance API, and features a heuristic feedback loop to "learn" from its previous picks.

## Target Users
- **Crypto Traders / Hobbyists:** Need a continuously updated set of recommended coins split between high variance and low variance.

## Core Features & Rules
- **Volatility vs. Stability:** Defined mathematically via 30-day historical klines from Binance. High standard deviation = volatile, low standard deviation = stable.
- **Learning Mechanism:** A heuristic rule-based loop. The app saves the 9 selected coins in `history.json` (7-day TTL). If a selected coin lost value by the next run, it receives a score penalty; if it gained, a bonus.
- **Unified Workflow:** A single `run` command assesses the previous portfolio, updates heuristic scores, and prints new picks.
