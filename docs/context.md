# Product Context (Crypto Portfolio CLI)

## Vision
To provide a fast, command-line tool that generates a cryptocurrency portfolio of 9 coins (6 volatile, 3 stable) using the Binance API, and features a heuristic feedback loop to "learn" from its previous picks.

## Target Users
- **Crypto Traders / Hobbyists:** Need a continuously updated set of recommended coins split between high variance and low variance.

## Core Features & Rules
- **Volatility vs. Stability:** Defined mathematically via 30-day historical klines from Binance. High standard deviation = volatile, low standard deviation = stable.
- **Learning Mechanism:** A heuristic rule-based loop. The app saves the 9 selected coins in `history.json` (30-day TTL). If a selected coin lost value by the next run, it receives a score penalty; if it gained, a bonus.
- **Unified Workflow:** A single `run` command assesses the previous portfolio, updates heuristic scores, and prints new picks.

## Proposed features (backlog)

Tracked as GitHub issues. Suggested order: explainability, then strategy vs BTC, then the rest.

1. **Explain each pick:** Show why a coin was selected (score, variance bucket, RSI/MACD, news bump, history bonus/penalty) in CLI and dashboard.
2. **Strategy vs BTC:** After each run, show how the previous portfolio performed versus Bitcoin (or versus holding the last basket).
3. **Constraints / diversification:** User constraints (never pick X, always include BTC) and/or theme caps so variance split does not yield a clustered basket. See `docs/crypto_coin_mental_models_and_grouping_report.md`.
4. **Hold vs regenerate:** Optional mode that keeps winners and only replaces losers instead of a fresh 9 coins every `run`.
5. **Scheduled daily digest:** Unattended daily run that writes history and prints or sends a one-pager.
