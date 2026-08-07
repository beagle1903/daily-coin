# Business Logic Review: daily-coin

**Date:** 2026-08-07  
**Reviewer:** Business Logic Review Agent

---

## 1. Unbounded Score Inflation
**Severity:** P0  
**File(s):** [`logic.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/logic.py) (Lines 14-20)  
**Finding:** The `load_coin_scores` function has no upper cap on scores. `adjustment = p_change * 100` converts a 5% gain into +5.0 points, while a 50% gain yields +50.0 points. Because the initial score is 10.0, large price swings permanently distort scores, dwarfing both RSI adjustments (±2.0 max) and Sentiment adjustments (±2.0 max). Historical adjustments stack linearly across all past records, creating a runaway positive feedback loop.  
**Fix Suggestion:**
> Refactor `load_coin_scores` in `logic.py` to normalize the historical performance adjustment. Cap the maximum historical impact (e.g., ±5.0 max per record) and average the adjustments across history records instead of summing them, preventing runaway scores. Consider implementing a score ceiling (e.g., 50.0).

---

## 2. History-Dependent Weighted Sampling is Fragile
**Severity:** P1  
**File(s):** [`logic.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/logic.py) (Lines 62-70)  
**Finding:** `pick_portfolio` uses `random.choices` with scores as weights. With unbounded scores, a coin with score 100 is 100× more likely to be selected than a coin with score 1, effectively eliminating diversification.  
**Fix Suggestion:**
> Introduce a temperature parameter or logarithmic scaling function to the weights before passing them to `random.choices` to ensure low-scoring coins still have a non-zero chance of being selected.

---

## 3. 7-Day History TTL Discards Valuable Data
**Severity:** P1  
**File(s):** [`history.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/history.py) (Line 6)  
**Finding:** The `clean_old_history_in_memory` function deletes records older than 7 days. This means the scoring system only considers very recent performance, making it reactive rather than predictive. If a user generates a portfolio and checks back 8 days later, it won't be evaluated at all.  
**Fix Suggestion:**
> Increase the `TTL_SECONDS` to at least 30 or 90 days. Alternatively, decouple evaluation TTL from scoring memory by keeping a persistent running 'score ledger' for each coin rather than recalculating from raw history every run.

---

## 4. VADER Sentiment Poorly Suited for Crypto Headlines
**Severity:** P2  
**File(s):** [`news.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/news.py) (Lines 78-106)  
**Finding:** VADER is a general-purpose sentiment analyzer trained on social media text, not financial or crypto-specific language. Terms like "crash" (bearish) or "moon" (bullish in crypto) may not be correctly weighted. The threshold `abs(compound) > 0.1` is quite low and easily triggered by neutral words.  
**Fix Suggestion:**
> Raise the VADER compound threshold to >0.25 to reduce noise from neutral crypto headlines. Consider fine-tuning VADER's lexicon with crypto-specific terms or using a finance-specific sentiment model.

---

## 5. Variance-Based Stable/Volatile Split is Arbitrary
**Severity:** P1  
**File(s):** [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py) (Lines 106-108), [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py) (Lines 119-121)  
**Finding:** The 1/3 split for classifying coins as "stable" vs "volatile" is a hardcoded heuristic with no empirical basis. With 100 symbols, the top 33 by lowest variance are "stable" regardless of absolute variance values. In a highly volatile market, the "bottom 33%" might still be extremely volatile in absolute terms.  
**Fix Suggestion:**
> Extract the variance threshold logic into a configurable parameter or use an absolute variance threshold alongside the relative ranking.

---

## 6. Performance Evaluation Misattributes Failed Fetches
**Severity:** P1  
**File(s):** [`logic.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/logic.py) (Lines 96-103)  
**Finding:** If `curr_p == 0`, performance is recorded as `-1.0` (-100%). However, due to Binance API occasional hiccups, a price of 0 might simply mean the fetch failed — not that the coin was delisted. This causes an unwarranted 100% penalty that permanently damages the coin's future score.  
**Fix Suggestion:**
> Differentiate between a failed price fetch (where the coin still exists in the universe) and a genuine delisting. Skip evaluation (or score as 0.0) if it's just a temporary network issue.

---

## 7. MACD Signal Line Calculation
**Severity:** P2  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py) (Lines 137-158)  
**Finding:** The `calculate_macd` function applies EMA on the already-computed MACD values array rather than using a running signal calculation, which can produce slightly different results than standard implementations.  
**Fix Suggestion:**
> Verify the MACD implementation against a reference library (e.g., TA-Lib) and align the signal line calculation.

---

## 8. News Keyword Matching is Simplistic
**Severity:** P2  
**File(s):** [`news.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/news.py) (Lines 17-39, 85-90)  
**Finding:** The `analyze_news_impact` function uses exact single-word matching against a fixed dictionary. "Ethereum upgrade" works, but "ETH/BTC pair" won't match because the regex strips the slash. Also, only ~21 coins are mapped, meaning 79+ coins in the top 100 never receive sentiment adjustments.  
**Fix Suggestion:**
> Dynamically generate the `KEYWORD_MAP` from the Binance active tradeable symbols list. Handle compound terms and special characters in matching.

---

## 9. No Deduplication in Sentiment Impacts
**Severity:** P2  
**File(s):** [`news.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/news.py) (Lines 92-105)  
**Finding:** If multiple headlines mention the same coin, the adjustment is applied multiple times additively, potentially over-weighting a single news event.  
**Fix Suggestion:**
> Aggregate sentiment impacts per coin (e.g., average or cap the total adjustment per coin).

---

## 10. Coin Replacement Loop Breaks Weighted Random Property
**Severity:** P2  
**File(s):** [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py) (Lines 136-164), [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py) (Lines 147-171)  
**Finding:** When replacing coins with $0 prices, the loop sorts remaining candidates by score and greedily picks the highest-scored one. This breaks the weighted random property of the portfolio selection.  
**Fix Suggestion:**
> Use the same `unique_weighted_sample` logic from `logic.py` for replacements instead of a greedy sort. Batch fetch replacement prices.

---

## 11. Midas Allowlist Edge Case
**Severity:** P2  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py) (Lines 29-52)  
**Finding:** If `midas_coins.json` contains very few coins, the 1/3 split logic might fail or return too few coins to satisfy the requested stable + volatile count.  
**Fix Suggestion:**
> Add validation in `get_tradeable_symbols` to ensure the allowlist filtering yields at least `stable_count + volatile_count` coins. If it yields fewer, fall back to ignoring the allowlist with a warning.
