# Business Logic Review

## Overview
A comprehensive review of the `daily-coin` business logic has been conducted to verify the alignment with domain rules, portfolio generation rules, and user workflows as outlined in `docs/context.md` and the recent changes in `progress.md`.

## Positive Findings
1. **Portfolio Pick Distribution**: The requirement for a 9-coin portfolio (3 stable, 6 volatile) is properly implemented via defaults in `main.py` (`stable=3, volatile=6`). The relative math for volatility splitting (lowest 1/3 variance as stable, highest 2/3 as volatile) in `logic.py` effectively handles market-wide volatility shifts without hardcoded lists.
2. **Heuristic Loop**: The heuristic feedback loop successfully reads from `history.json` and adjusts scores by applying a multiplier (`p_change * 100`). The floor limit of `1.0` in `scores[coin] = max(1.0, scores[coin] + adjustment)` ensures `random.choices` never crashes from negative or zero weights.
3. **News Sentiment Impact**: Correctly applies sentiment adjustments independently to the current run without persisting them permanently to the base scores, avoiding double-counting effects.
4. **Kline Math Limits**: Refactoring to 4-hour intervals while keeping 30-day (180 candles) and 60-day (360 candles) lookbacks fits safely within the Binance API's 1000-candle per-request limit. 

## Edge Cases and Potential Bugs
1. **Concurrency Burst Rate Limiting (Binance API Edge Case)**
   In `logic.py`, the `fetch_all_variances` and `fetch_all_technical_indicators` functions use `asyncio.gather(*tasks)` to fetch data for up to 100 valid symbols simultaneously. This results in an immediate burst of 100 concurrent requests to the Binance API. While `fetch_with_retry` offers an exponential backoff for HTTP 429s, an `asyncio.Semaphore` (e.g., limiting to 10-15 concurrent requests) should be implemented to prevent IP bans or dropped connections before the backoff even triggers.

2. **Delisted / Zero Price Coin Evaluation (Financial Logic Edge Case)**
   In `evaluate_performance` (`logic.py`), the performance change is calculated as:
   ```python
   if old_p > 0 and curr_p > 0:
       performance[coin] = (curr_p - old_p) / old_p
   else:
       performance[coin] = 0.0
   ```
   If a coin is delisted from Binance, or the API fails to fetch its price, `curr_p` evaluates to 0. The current logic treats this as `0.0` (0% change), meaning the coin escapes a penalty. A delisted or zeroed coin should technically represent a `-1.0` (-100%) loss and heavily penalize the heuristic score. Note: If `old_p == 0` (due to an API error during the initial pick), defaulting to `0.0` is correct to avoid division by zero.

3. **Zero Entry Price in Portfolio (API Fault Edge Case)**
   In `pick_portfolio`, `prices = get_current_prices(portfolio)` is used to map current prices. If the API drops a ticker, `prices.get(coin, 0)` allows an entry price of `$0.0000` into the portfolio. These coins will break the `old_p > 0` check in the *next* evaluation. The system should discard and replace picks if a valid non-zero entry price cannot be obtained.

4. **Redundant Run Weighting (Workflow Edge Case)**
   Because `evaluate_performance` iterates through all unevaluated past records and applies cumulative adjustments, running the CLI frequently (e.g., every 15 minutes) will heavily stack small time-delta performance adjustments. Since the team recently shifted to a 4-hour intra-day workflow, it is structurally safe, but users who spam the `run` command will see significantly magnified heuristic score weights compared to users who run it once daily.

## Conclusion
The application perfectly adheres to the core mathematical rules defined in the product context. Addressing the missing-price evaluation and concurrency rate limits will robustify the CLI for long-term uninterrupted background execution.
