# Pick explanations design

GitHub: [#19](https://github.com/beagle1903/daily-coin/issues/19)  
Date: 2026-09-07

## Goal

Each generated pick includes a structured explanation of why it was scored as it was, plus a short templated paragraph. CLI (`run`) and the dashboard show the same fields, derived from the existing scoring pipeline. There is no second ranking path and no LLM.

## Non-goals

- Do not persist explanations in `history.json`.
- Do not change `pick_portfolio` sampling (still weighted random).
- Do not add user constraints, vs-BTC comparison, hold-vs-regenerate, or scheduled digest (#20–#23).
- Do not send stripped internals (`scores`, `market_data`, `prices`) through the generate API.
- Do not introduce a frontend test runner.

## Architecture

`load_coin_scores` remains the only place heuristic components are applied. It still produces the `scores: dict[str, float]` map that `pick_portfolio` uses, and in the same pass it produces a per-coin breakdown.

```text
scores, breakdowns = load_coin_scores(universe, history, impacts, market_data)
stable_picks, volatile_picks = pick_portfolio(...)  # unchanged; uses scores only
```

After variance buckets exist, `compute_bucket_stats(bucket_symbols, scores)` in `logic.py` returns, for every symbol in that bucket:

- `bucket_size`: number of coins in that bucket
- `bucket_rank`: 1 = highest score in that bucket (pick need not be rank 1)
- `bucket_avg_score`: mean of scores in that bucket

`portfolio_service` calls it once for `available_stable` and once for `available_volatile`. Tied scores: sort by score descending, then symbol ascending, so rank is deterministic. Empty `bucket_symbols` returns `{}`.

A pure `format_pick_explanation(breakdown, bucket_stats, bucket_type, variance_percentile)` in `logic.py` builds `explanation.summary`. CLI and dashboard render that string; they do not assemble copy themselves.

Zero-price replacements still come from the scored universe, so they receive the same breakdown and paragraph.

## Data model

Existing pick fields stay: `coin`, `display_name`, `type`, `price`, `score`, `rsi`, `variance`.

New nested object on every pick:

```json
{
  "explanation": {
    "summary": "string",
    "base": 10.0,
    "history_adjustment": 5.0,
    "news_adjustment": 0.5,
    "news_headline": "string or null",
    "news_sentiment": "Bullish | Bearish | null",
    "rsi": 22.0,
    "rsi_adjustment": 2.0,
    "macd": 1.2,
    "signal": 0.8,
    "macd_adjustment": 1.0,
    "score": 18.5,
    "bucket_size": 12,
    "bucket_rank": 3,
    "bucket_avg_score": 12.4
  }
}
```

Breakdown components are the **intended** deltas from the scorer (history average after per-record cap, news adjustment, RSI ±2 / 0, MACD ±1 / 0), plus the final clamped `score`. If `base + components` falls outside `[SCORE_FLOOR, SCORE_CEILING]` and the stored score was clamped, the template mentions the clamp. The scorer formula itself does not change.

`news_headline` / `news_sentiment` come from the `sentiment_impacts` row for that coin, or `null` when there is no impact.

API generate response still returns only `evaluation_results`, `news`, `sentiment_impacts`, `portfolio`. Explanations travel on `portfolio[]`.

## `load_coin_scores` return type

```python
def load_coin_scores(universe, history, sentiment_impacts=None, technical_indicators=None):
    """Return (scores, breakdowns). Empty universe → ({}, {})."""
```

- `scores`: `dict[str, float]` (same values as today)
- `breakdowns`: `dict[str, dict]` with keys `base`, `history_adjustment`, `news_adjustment`, `news_headline`, `news_sentiment`, `rsi`, `rsi_adjustment`, `macd`, `signal`, `macd_adjustment`, `score`

Existing callers and tests that treated the return as a single dict must unpack the pair. Empty-universe test expects `({}, {})`.

## Paragraph template

`format_pick_explanation` builds one paragraph. Sentences appear in this order. Omit a clause only when that component is zero/absent, except RSI and MACD which always render.

1. **Identity + bucket:** `{NAME} is in the {Stable|Volatile} bucket ({lowest|highest} ~{percentile}% of 30-day variance among tradeable pairs this run).`
   - Stable → `lowest`; Volatile → `highest`.
   - `{percentile}` is the run’s `variance_percentile` rounded to the nearest integer (default 33.3 → `33`).
   - `{NAME}` is the display name (USDT suffix stripped).
2. **Score vs bucket:** `Score {score:.2f} is {well above|above|near|below|well below} the {Stable|Volatile} average of {avg:.2f} (rank {n} of {size} by score).`
   - well above/below: `|score − avg| ≥ 3`
   - above/below: `|score − avg| ≥ 1`
   - else `near`
   - If `bucket_size` is 0, omit this sentence.
3. **History:** `Past picks added a {bonus|penalty} of {+|-}{x:.2f}.` Omit if `history_adjustment == 0`.
4. **News:** `{Bullish|Bearish} news ({headline}) added {+|-}{x:.2f}.` Omit if `news_adjustment == 0`. Truncate headline to 80 characters with an ellipsis. The stored `summary` is plain text (no Rich markup). CLI escapes the string when printing so `[` / `]` in a headline cannot inject markup; the dashboard renders the same plain string.
5. **RSI:** `RSI {value:.1f} is {oversold; +2.0|overbought; −2.0|neutral; no RSI adjustment}.`
   - Same thresholds as the scorer: `< 30` oversold, `> 70` overbought, else neutral.
6. **MACD:** `MACD is {above|below|even with} its signal ({+1.0|−1.0|no MACD adjustment}).`
7. **Sampling:** `It was sampled with this weight, not chosen as a guaranteed top pick.`
8. **Clamp:** If the unclamped sum of `base + history + news + rsi + macd` is outside `[1.0, 30.0]` and `score` equals the floor or ceiling, append `The total was clamped to the {1.0|30.0} score limit.`

Worked example (BTC from `tests/test_logic.py` scoring, with example bucket stats):

> BTC is in the Stable bucket (lowest ~33% of 30-day variance among tradeable pairs this run). Score 18.50 is well above the Stable average of 12.40 (rank 3 of 12 by score). Past picks added a bonus of +5.00. Bullish news (Bitcoin rallies as ETF inflows hit a record) added +0.50. RSI 22.0 is oversold; +2.0. MACD is above its signal (+1.0). It was sampled with this weight, not chosen as a guaranteed top pick.

## CLI

Keep the Recommended Portfolio table: Coin, Type, Entry Price, Heuristic Score.

Directly under it, print a **Why these picks** heading. For each pick, print the display name and `explanation.summary`. Do not put the paragraph in the table.

If `explanation` is missing or `summary` is empty, skip that coin’s Why line; still show the table row.

Escape summary text for Rich so headlines cannot inject markup.

Existing evaluation and news-impact tables are unchanged.

## Dashboard

Each coin card keeps symbol, type badge, price, Score, and RSI (14). Add a MACD metric (`macd` vs `signal` from `explanation`). Render `explanation.summary` under the metrics, always visible.

If `explanation` is missing, skip MACD and the paragraph; keep today’s card fields.

History panel is unchanged. Do not store explanations on generate for later history views.

## Error handling

- Generate API errors remain `{ "error": "..." }` with no portfolio/explanations.
- Frontend and CLI must not crash on missing `explanation`.
- Empty news/history → `0` adjustments and omitted sentences.
- Rank ties are deterministic (score desc, symbol asc).

## Tests

- `tests/test_logic.py`: keep BTC 18.5 / ETH 5.0 / SOL 10.0 score asserts via the `scores` half of the return. Assert breakdown fields for those coins. Empty universe → `({}, {})`. Tests for `compute_bucket_stats` (rank, ties, empty). New tests for `format_pick_explanation`: history bonus, no history/news, well-above vs near average, clamp sentence, sampling sentence, headline truncation.
- `tests/test_portfolio_service.py` (new): mocked `generate_portfolio` attaches `explanation` with the required keys on every pick; `summary` is non-empty.
- `tests/test_server.py`: generate JSON includes that shape on `portfolio[]`; `scores` / `market_data` / `prices` still stripped.
- `tests/test_main.py`: CLI prints `Why these picks` and a snippet of the templated summary when the mock pick includes `explanation`. Missing `explanation` still exits 0.

## Files

| File | Change |
|---|---|
| `logic.py` | Return `(scores, breakdowns)`; add `compute_bucket_stats` and `format_pick_explanation` |
| `portfolio_service.py` | Unpack scores; attach `explanation` to each pick |
| `main.py` | Why these picks section |
| `frontend/src/App.jsx` | MACD metric + summary paragraph |
| `frontend/src/App.css` | Paragraph / extra metric styles |
| `docs/context.md` | Note that picks now include explanations |
| `docs/architecture.md` | Note breakdown + explanation on portfolio items |
| `progress.md` | Handoff when the ticket lands |
| Tests listed above | Payload shape and template |

## Issue acceptance mapping

| Acceptance | How |
|---|---|
| Each pick includes a structured explanation | Nested `explanation` on every portfolio item |
| CLI and dashboard show the same explanation fields | Shared `summary` + same component fields; dashboard also shows MACD metric |
| Derived from data already used to select | Breakdown recorded inside `load_coin_scores`; picker still uses `scores` |
| Tests cover explanation payload shape | Service + API tests |
