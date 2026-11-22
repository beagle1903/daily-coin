---
name: run-cli
description: Run the daily-coin CLI (`main.py run`) and show the results. Use when asked to run the CLI, generate or print the portfolio, or check the current picks.
---
# Run the CLI and show the results

Run the portfolio generator for real and report what it printed. Do not run pytest or import functions instead.

## Steps

1. Run from the repo root with the venv interpreter (a bare `python` can hit import errors on Windows):
   - PowerShell: `.\venv\Scripts\python.exe main.py run`
   - Bash: `./venv/Scripts/python.exe main.py run`
2. Wait for it to exit. It fetches news and market data, so it can take a while. Check the exit code.
3. Show the results in your reply, not just "it worked":
   - Past portfolio performance (if one was evaluated): coin and change %.
   - News sentiment rows (coin, bullish/bearish, score adjustment).
   - The new portfolio table: coin, Stable/Volatile, entry price, score.
   - Any pick whose score is low and why (past-pick penalty, bearish news), taken from "Why these picks".

## Data source (say which one was used)

- With no Binance keys the CLI still tries Binance public data. If it prints "Binance is unavailable", the picks are mock placeholders, were not saved to history, and past picks are not evaluated. Say so clearly.
- `OFFLINE_MOCK=true` forces mock data (set it for a safe, offline run): `$env:OFFLINE_MOCK = "true"` in PowerShell, `OFFLINE_MOCK=true` prefix in Bash.
- A normal live run writes the new portfolio to `history.json`. That file is gitignored, so it will not show up in `git status`, but tell the user the run was recorded.

## Variants

- Past results only: `main.py history`.
- Other commands: `main.py --help` (`run`, `history`, `serve`).
