# Pick Explanations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach a structured explanation and templated paragraph to every generated pick, and show the same fields in CLI `run` and the dashboard.

**Architecture:** `load_coin_scores` records component breakdowns in the same pass that produces scores. `compute_bucket_stats` adds rank/average for the pick’s variance bucket. `format_pick_explanation` builds `explanation.summary`. `portfolio_service` attaches the nested object to each pick; CLI and dashboard only render it.

**Tech Stack:** Python 3.10+, pytest, Typer/Rich CLI, FastAPI, Vite + React dashboard.

**Spec:** `docs/superpowers/specs/2026-09-07-pick-explanations-design.md`

## Global Constraints

- Work on branch `issue-19-explain-picks` from `main`. Do not commit `settings.json`.
- No second scoring/ranking path and no LLM. Picker stays weighted random.
- Do not persist explanations in `history.json`.
- API generate still returns only `evaluation_results`, `news`, `sentiment_impacts`, `portfolio`.
- `load_coin_scores(universe, history, sentiment_impacts=None, technical_indicators=None) -> tuple[dict[str, float], dict[str, dict]]`
- Breakdown dict keys: `base`, `history_adjustment`, `news_adjustment`, `news_headline`, `news_sentiment`, `rsi`, `rsi_adjustment`, `macd`, `signal`, `macd_adjustment`, `score`
- Explanation adds: `summary`, `bucket_size`, `bucket_rank`, `bucket_avg_score`
- `compute_bucket_stats(bucket_symbols, scores) -> dict[str, dict]` with `bucket_size`, `bucket_rank`, `bucket_avg_score`. Empty list → `{}`. Ties: score descending, then symbol ascending. Rank 1 = highest score.
- `format_pick_explanation(breakdown, bucket_stats, bucket_type, variance_percentile, display_name) -> str`
- Signed numbers in copy use ASCII `+`/`-` (e.g. `-2.0`, `+5.00`), not Unicode minus.
- Headline truncation: if `len(headline) > 80`, use `headline[:80] + "..."`.
- Tests: `.\venv\Scripts\python.exe -m pytest <args>`. Lint: `.\venv\Scripts\python.exe -m ruff check .`
- Python 3.10+: do not use `str | None` if the file currently avoids PEP 604; use `None` and plain dicts like the rest of `logic.py`.

## File map

| File | Responsibility |
|---|---|
| `logic.py` | Scores, breakdowns, bucket stats, paragraph template |
| `portfolio_service.py` | Attach `explanation` to each pick |
| `main.py` | Print Why these picks |
| `frontend/src/App.jsx` | MACD metric + summary paragraph |
| `frontend/src/App.css` | Explanation text styles |
| `tests/test_logic.py` | Breakdown, bucket stats, template |
| `tests/test_portfolio_service.py` | Generate payload shape |
| `tests/test_server.py` | API passes explanation, still strips internals |
| `tests/test_main.py` | CLI Why section |
| `docs/context.md`, `docs/architecture.md`, `progress.md` | Source of truth / handoff |

---

### Task 1: Return score breakdowns from `load_coin_scores`

**Files:**
- Modify: `logic.py` (`load_coin_scores`)
- Modify: `portfolio_service.py` (unpack the tuple; do not attach explanations yet)
- Test: `tests/test_logic.py`

**Interfaces:**
- Consumes: existing `load_coin_scores` formula (unchanged numeric results)
- Produces: `load_coin_scores(...) -> (scores, breakdowns)` where `scores` values stay `BTCUSDT=18.5`, `ETHUSDT=5.0`, `SOLUSDT=10.0` for the existing fixture. Each breakdown has the keys listed in Global Constraints. Empty universe → `({}, {})`.

- [ ] **Step 1: Create the branch**

```bash
git checkout main
git pull
git checkout -b issue-19-explain-picks
```

- [ ] **Step 2: Write the failing tests**

In `tests/test_logic.py`, change the existing score tests to unpack the tuple, add breakdown asserts, and fix the empty-universe test.

Replace `test_load_coin_scores` and `test_load_coin_scores_empty_universe` with:

```python
def test_load_coin_scores():
    universe = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    history = [{
        "evaluated": True,
        "performance": {
            "BTCUSDT": 0.05,
            "ETHUSDT": -0.02
        }
    }]
    sentiment_impacts = [
        {"coin": "BTCUSDT", "adjustment": 0.5, "headline": "Bitcoin rallies", "sentiment": "Bullish"}
    ]
    technical_indicators = {
        "BTCUSDT": {"rsi": 25.0, "macd": 0.1, "signal": 0.0},
        "ETHUSDT": {"rsi": 75.0, "macd": -0.1, "signal": 0.0},
        "SOLUSDT": {"rsi": 50.0, "macd": 0.0, "signal": 0.0}
    }

    scores, breakdowns = load_coin_scores(universe, history, sentiment_impacts, technical_indicators)
    assert scores["BTCUSDT"] == 18.5
    assert scores["ETHUSDT"] == 5.0
    assert scores["SOLUSDT"] == 10.0

    btc = breakdowns["BTCUSDT"]
    assert btc["base"] == 10.0
    assert btc["history_adjustment"] == 5.0
    assert btc["news_adjustment"] == 0.5
    assert btc["news_headline"] == "Bitcoin rallies"
    assert btc["news_sentiment"] == "Bullish"
    assert btc["rsi"] == 25.0
    assert btc["rsi_adjustment"] == 2.0
    assert btc["macd"] == 0.1
    assert btc["signal"] == 0.0
    assert btc["macd_adjustment"] == 1.0
    assert btc["score"] == 18.5

    eth = breakdowns["ETHUSDT"]
    assert eth["history_adjustment"] == -2.0
    assert eth["news_adjustment"] == 0.0
    assert eth["news_headline"] is None
    assert eth["news_sentiment"] is None
    assert eth["rsi_adjustment"] == -2.0
    assert eth["macd_adjustment"] == -1.0
    assert eth["score"] == 5.0

    sol = breakdowns["SOLUSDT"]
    assert sol["history_adjustment"] == 0.0
    assert sol["news_adjustment"] == 0.0
    assert sol["rsi_adjustment"] == 0.0
    assert sol["macd_adjustment"] == 0.0
    assert sol["score"] == 10.0


def test_load_coin_scores_empty_universe():
    scores, breakdowns = load_coin_scores([], [])
    assert scores == {}
    assert breakdowns == {}
```

Keep every other test in this file unchanged.

- [ ] **Step 3: Run tests to verify they fail**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_logic.py::test_load_coin_scores tests/test_logic.py::test_load_coin_scores_empty_universe -v`

Expected: FAIL (tuple unpack / extra keys not returned).

- [ ] **Step 4: Implement breakdown recording**

Replace `load_coin_scores` in `logic.py` with:

```python
def load_coin_scores(universe, history, sentiment_impacts=None, technical_indicators=None):
    """
    Pure function that calculates heuristic scores for the coin universe.

    :return: (scores, breakdowns) where scores is dict[str, float] and
             breakdowns is dict[str, dict] of intended score components.
    """
    scores = {coin: INITIAL_SCORE for coin in universe}
    breakdowns = {
        coin: {
            "base": INITIAL_SCORE,
            "history_adjustment": 0.0,
            "news_adjustment": 0.0,
            "news_headline": None,
            "news_sentiment": None,
            "rsi": 50.0,
            "rsi_adjustment": 0.0,
            "macd": 0.0,
            "signal": 0.0,
            "macd_adjustment": 0.0,
            "score": INITIAL_SCORE,
        }
        for coin in universe
    }

    coin_adjustments = {coin: [] for coin in universe}
    for record in history:
        if record.get("evaluated") and "performance" in record:
            for coin, p_change in record["performance"].items():
                if coin in coin_adjustments:
                    raw = p_change * 100
                    capped = max(-MAX_PER_RECORD_ADJUSTMENT, min(MAX_PER_RECORD_ADJUSTMENT, raw))
                    coin_adjustments[coin].append(capped)

    for coin, adjustments in coin_adjustments.items():
        if adjustments:
            avg_adjustment = sum(adjustments) / len(adjustments)
            breakdowns[coin]["history_adjustment"] = avg_adjustment
            scores[coin] = max(SCORE_FLOOR, min(SCORE_CEILING, scores[coin] + avg_adjustment))

    if sentiment_impacts:
        for impact in sentiment_impacts:
            coin = impact["coin"]
            if coin in scores:
                breakdowns[coin]["news_adjustment"] += impact["adjustment"]
                if "headline" in impact:
                    breakdowns[coin]["news_headline"] = impact["headline"]
                if "sentiment" in impact:
                    breakdowns[coin]["news_sentiment"] = impact["sentiment"]
                scores[coin] = max(SCORE_FLOOR, min(SCORE_CEILING, scores[coin] + impact["adjustment"]))

    if technical_indicators:
        for coin in scores:
            ti = technical_indicators.get(coin, {"rsi": 50.0, "macd": 0.0, "signal": 0.0})
            rsi = ti["rsi"]
            macd = ti["macd"]
            signal = ti["signal"]
            breakdowns[coin]["rsi"] = rsi
            breakdowns[coin]["macd"] = macd
            breakdowns[coin]["signal"] = signal

            if rsi < 30:
                rsi_adj = 2.0
            elif rsi > 70:
                rsi_adj = -2.0
            else:
                rsi_adj = 0.0

            if macd > signal:
                macd_adj = 1.0
            elif macd < signal:
                macd_adj = -1.0
            else:
                macd_adj = 0.0

            breakdowns[coin]["rsi_adjustment"] = rsi_adj
            breakdowns[coin]["macd_adjustment"] = macd_adj
            scores[coin] += rsi_adj
            scores[coin] += macd_adj
            scores[coin] = max(SCORE_FLOOR, min(SCORE_CEILING, scores[coin]))

    for coin in scores:
        breakdowns[coin]["score"] = scores[coin]

    return scores, breakdowns
```

In `portfolio_service.py` change the call site only:

```python
    scores, breakdowns = load_coin_scores(universe, history, impacts, market_data)
```

`breakdowns` may be unused until Task 4. If ruff flags it, prefix with `_breakdowns` for this commit only and rename in Task 4. Prefer assigning `breakdowns` and using it in Task 4; for this task, `_breakdowns` is fine:

```python
    scores, _breakdowns = load_coin_scores(universe, history, impacts, market_data)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_logic.py -v`

Expected: PASS

Run: `.\venv\Scripts\python.exe -m ruff check logic.py portfolio_service.py tests/test_logic.py`

Expected: no issues (unused `_breakdowns` is allowed if prefixed).

- [ ] **Step 6: Commit**

```bash
git add logic.py portfolio_service.py tests/test_logic.py
git commit -m "Return per-coin score breakdowns from the existing heuristic."
```

---

### Task 2: `compute_bucket_stats`

**Files:**
- Modify: `logic.py`
- Test: `tests/test_logic.py`

**Interfaces:**
- Consumes: `scores: dict[str, float]` from Task 1
- Produces: `compute_bucket_stats(bucket_symbols, scores) -> dict[str, dict]` mapping each symbol to `{"bucket_size": int, "bucket_rank": int, "bucket_avg_score": float}`. Missing score keys use `INITIAL_SCORE`. Empty `bucket_symbols` returns `{}`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_logic.py`:

```python
from logic import load_coin_scores, pick_portfolio, evaluate_performance, compute_bucket_stats
```

(Update the existing import line instead of adding a second import.)

```python
def test_compute_bucket_stats_ranks_by_score_then_symbol():
    scores = {"AAAUSDT": 10.0, "BTCUSDT": 18.5, "ETHUSDT": 18.5, "SOLUSDT": 5.0}
    stats = compute_bucket_stats(["SOLUSDT", "BTCUSDT", "ETHUSDT", "AAAUSDT"], scores)
    assert stats["BTCUSDT"]["bucket_rank"] == 1
    assert stats["ETHUSDT"]["bucket_rank"] == 2
    assert stats["AAAUSDT"]["bucket_rank"] == 3
    assert stats["SOLUSDT"]["bucket_rank"] == 4
    assert stats["BTCUSDT"]["bucket_size"] == 4
    assert stats["ETHUSDT"]["bucket_size"] == 4
    assert stats["BTCUSDT"]["bucket_avg_score"] == pytest.approx((10.0 + 18.5 + 18.5 + 5.0) / 4)


def test_compute_bucket_stats_empty():
    assert compute_bucket_stats([], {"BTCUSDT": 10.0}) == {}


def test_compute_bucket_stats_missing_score_uses_initial():
    stats = compute_bucket_stats(["NEWUSDT"], {})
    assert stats["NEWUSDT"]["bucket_rank"] == 1
    assert stats["NEWUSDT"]["bucket_size"] == 1
    assert stats["NEWUSDT"]["bucket_avg_score"] == 10.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_logic.py::test_compute_bucket_stats_ranks_by_score_then_symbol tests/test_logic.py::test_compute_bucket_stats_empty tests/test_logic.py::test_compute_bucket_stats_missing_score_uses_initial -v`

Expected: FAIL with `compute_bucket_stats` not defined.

- [ ] **Step 3: Implement**

Add to `logic.py` after `load_coin_scores`:

```python
def compute_bucket_stats(bucket_symbols, scores):
    """Rank coins in a variance bucket by score (desc), then symbol (asc)."""
    if not bucket_symbols:
        return {}
    size = len(bucket_symbols)
    avg = sum(scores.get(symbol, INITIAL_SCORE) for symbol in bucket_symbols) / size
    ranked = sorted(
        bucket_symbols,
        key=lambda symbol: (-scores.get(symbol, INITIAL_SCORE), symbol),
    )
    stats = {}
    for index, symbol in enumerate(ranked, start=1):
        stats[symbol] = {
            "bucket_size": size,
            "bucket_rank": index,
            "bucket_avg_score": avg,
        }
    return stats
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_logic.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add logic.py tests/test_logic.py
git commit -m "Rank each variance bucket so pick explanations can cite average and place."
```

---

### Task 3: `format_pick_explanation`

**Files:**
- Modify: `logic.py`
- Test: `tests/test_logic.py`

**Interfaces:**
- Consumes: a breakdown dict (Task 1 keys) plus a per-coin stats dict from `compute_bucket_stats` (Task 2)
- Produces: `format_pick_explanation(breakdown, bucket_stats, bucket_type, variance_percentile, display_name) -> str` matching the spec sentence order.

Sentence rules (implement exactly):

1. `{display_name} is in the {bucket_type} bucket ({lowest|highest} ~{int(round(variance_percentile))}% of 30-day variance among tradeable pairs this run).` Stable → `lowest`, Volatile → `highest`.
2. If `bucket_stats.get("bucket_size", 0)` is truthy: `Score {score:.2f} is {rel} the {bucket_type} average of {avg:.2f} (rank {n} of {size} by score).` `rel` from `delta = score - avg`: `|delta| >= 3` → well above/below; `|delta| >= 1` → above/below; else near.
3. History if `history_adjustment != 0`: `Past picks added a {bonus|penalty} of {history_adjustment:+.2f}.`
4. News if `news_adjustment != 0`: `{sentiment} news ({headline}) added {news_adjustment:+.2f}.` Truncate headline if longer than 80 chars. If sentiment is missing, use `Bullish` when adjustment > 0 else `Bearish`. If headline is `None`, use `""`.
5. RSI always: `RSI {rsi:.1f} is oversold; +2.0.` / `overbought; -2.0.` / `neutral; no RSI adjustment.` Thresholds `< 30` / `> 70`.
6. MACD always: `MACD is above its signal (+1.0).` / `below its signal (-1.0).` / `even with its signal (no MACD adjustment).` Compare `macd` to `signal`.
7. Always: `It was sampled with this weight, not chosen as a guaranteed top pick.`
8. Clamp: `unclamped = base + history_adjustment + news_adjustment + rsi_adjustment + macd_adjustment`. If `unclamped > 30.0` and `score == 30.0`: `The total was clamped to the 30.0 score limit.` If `unclamped < 1.0` and `score == 1.0`: `The total was clamped to the 1.0 score limit.`

Join sentences with a single space.

- [ ] **Step 1: Write the failing tests**

Add to the import: `format_pick_explanation`.

Append:

```python
def test_format_pick_explanation_btc_full_example():
    breakdown = {
        "base": 10.0,
        "history_adjustment": 5.0,
        "news_adjustment": 0.5,
        "news_headline": "Bitcoin rallies as ETF inflows hit a record",
        "news_sentiment": "Bullish",
        "rsi": 22.0,
        "rsi_adjustment": 2.0,
        "macd": 1.2,
        "signal": 0.8,
        "macd_adjustment": 1.0,
        "score": 18.5,
    }
    stats = {"bucket_size": 12, "bucket_rank": 3, "bucket_avg_score": 12.4}
    text = format_pick_explanation(breakdown, stats, "Stable", 33.3, "BTC")
    assert text == (
        "BTC is in the Stable bucket (lowest ~33% of 30-day variance among tradeable pairs this run). "
        "Score 18.50 is well above the Stable average of 12.40 (rank 3 of 12 by score). "
        "Past picks added a bonus of +5.00. "
        "Bullish news (Bitcoin rallies as ETF inflows hit a record) added +0.50. "
        "RSI 22.0 is oversold; +2.0. "
        "MACD is above its signal (+1.0). "
        "It was sampled with this weight, not chosen as a guaranteed top pick."
    )


def test_format_pick_explanation_omits_zero_history_and_news():
    breakdown = {
        "base": 10.0,
        "history_adjustment": 0.0,
        "news_adjustment": 0.0,
        "news_headline": None,
        "news_sentiment": None,
        "rsi": 50.0,
        "rsi_adjustment": 0.0,
        "macd": 0.0,
        "signal": 0.0,
        "macd_adjustment": 0.0,
        "score": 10.0,
    }
    stats = {"bucket_size": 5, "bucket_rank": 3, "bucket_avg_score": 10.2}
    text = format_pick_explanation(breakdown, stats, "Volatile", 33.3, "SOL")
    assert "Past picks" not in text
    assert "news" not in text
    assert "neutral; no RSI adjustment" in text
    assert "even with its signal (no MACD adjustment)" in text
    assert "near the Volatile average of 10.20" in text
    assert "highest ~33%" in text
    assert "It was sampled with this weight, not chosen as a guaranteed top pick." in text


def test_format_pick_explanation_penalty_overbought_below_signal():
    breakdown = {
        "base": 10.0,
        "history_adjustment": -2.0,
        "news_adjustment": -0.4,
        "news_headline": "ETH dumps after hack",
        "news_sentiment": "Bearish",
        "rsi": 75.0,
        "rsi_adjustment": -2.0,
        "macd": -0.1,
        "signal": 0.0,
        "macd_adjustment": -1.0,
        "score": 5.0,
    }
    stats = {"bucket_size": 8, "bucket_rank": 7, "bucket_avg_score": 11.0}
    text = format_pick_explanation(breakdown, stats, "Volatile", 33.3, "ETH")
    assert "Past picks added a penalty of -2.00." in text
    assert "Bearish news (ETH dumps after hack) added -0.40." in text
    assert "RSI 75.0 is overbought; -2.0." in text
    assert "MACD is below its signal (-1.0)." in text
    assert "well below the Volatile average of 11.00" in text


def test_format_pick_explanation_omits_average_when_bucket_empty():
    breakdown = {
        "base": 10.0,
        "history_adjustment": 0.0,
        "news_adjustment": 0.0,
        "news_headline": None,
        "news_sentiment": None,
        "rsi": 50.0,
        "rsi_adjustment": 0.0,
        "macd": 0.0,
        "signal": 0.0,
        "macd_adjustment": 0.0,
        "score": 10.0,
    }
    text = format_pick_explanation(breakdown, {}, "Stable", 33.3, "BTC")
    assert "average" not in text
    assert "rank" not in text


def test_format_pick_explanation_truncates_headline():
    headline = "A" * 90
    breakdown = {
        "base": 10.0,
        "history_adjustment": 0.0,
        "news_adjustment": 0.5,
        "news_headline": headline,
        "news_sentiment": "Bullish",
        "rsi": 50.0,
        "rsi_adjustment": 0.0,
        "macd": 0.0,
        "signal": 0.0,
        "macd_adjustment": 0.0,
        "score": 10.5,
    }
    stats = {"bucket_size": 2, "bucket_rank": 1, "bucket_avg_score": 10.0}
    text = format_pick_explanation(breakdown, stats, "Stable", 33.3, "BTC")
    assert ("A" * 80 + "...") in text
    assert ("A" * 81) not in text


def test_format_pick_explanation_mentions_ceiling_clamp():
    breakdown = {
        "base": 10.0,
        "history_adjustment": 5.0,
        "news_adjustment": 20.0,
        "news_headline": "Huge pump",
        "news_sentiment": "Bullish",
        "rsi": 20.0,
        "rsi_adjustment": 2.0,
        "macd": 1.0,
        "signal": 0.0,
        "macd_adjustment": 1.0,
        "score": 30.0,
    }
    stats = {"bucket_size": 3, "bucket_rank": 1, "bucket_avg_score": 12.0}
    text = format_pick_explanation(breakdown, stats, "Stable", 33.3, "BTC")
    assert "The total was clamped to the 30.0 score limit." in text


def test_format_pick_explanation_mentions_floor_clamp():
    breakdown = {
        "base": 10.0,
        "history_adjustment": -5.0,
        "news_adjustment": -5.0,
        "news_headline": "Rug",
        "news_sentiment": "Bearish",
        "rsi": 80.0,
        "rsi_adjustment": -2.0,
        "macd": -1.0,
        "signal": 0.0,
        "macd_adjustment": -1.0,
        "score": 1.0,
    }
    stats = {"bucket_size": 3, "bucket_rank": 3, "bucket_avg_score": 10.0}
    text = format_pick_explanation(breakdown, stats, "Volatile", 33.3, "ETH")
    assert "The total was clamped to the 1.0 score limit." in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_logic.py::test_format_pick_explanation_btc_full_example -v`

Expected: FAIL with `format_pick_explanation` not defined.

- [ ] **Step 3: Implement**

Add to `logic.py` (import `SCORE_FLOOR` and `SCORE_CEILING` are already imported):

```python
def format_pick_explanation(breakdown, bucket_stats, bucket_type, variance_percentile, display_name):
    """Build the templated explanation paragraph for one pick."""
    parts = []
    percentile = int(round(variance_percentile))
    direction = "lowest" if bucket_type == "Stable" else "highest"
    parts.append(
        f"{display_name} is in the {bucket_type} bucket "
        f"({direction} ~{percentile}% of 30-day variance among tradeable pairs this run)."
    )

    size = 0
    if bucket_stats:
        size = bucket_stats.get("bucket_size", 0) or 0
    if size:
        score = breakdown["score"]
        avg = bucket_stats["bucket_avg_score"]
        rank = bucket_stats["bucket_rank"]
        delta = score - avg
        abs_delta = abs(delta)
        if abs_delta >= 3:
            rel = "well above" if delta > 0 else "well below"
        elif abs_delta >= 1:
            rel = "above" if delta > 0 else "below"
        else:
            rel = "near"
        parts.append(
            f"Score {score:.2f} is {rel} the {bucket_type} average of {avg:.2f} "
            f"(rank {rank} of {size} by score)."
        )

    history_adjustment = breakdown.get("history_adjustment", 0.0)
    if history_adjustment != 0:
        kind = "bonus" if history_adjustment > 0 else "penalty"
        parts.append(f"Past picks added a {kind} of {history_adjustment:+.2f}.")

    news_adjustment = breakdown.get("news_adjustment", 0.0)
    if news_adjustment != 0:
        sentiment = breakdown.get("news_sentiment")
        if not sentiment:
            sentiment = "Bullish" if news_adjustment > 0 else "Bearish"
        headline = breakdown.get("news_headline") or ""
        if len(headline) > 80:
            headline = headline[:80] + "..."
        parts.append(f"{sentiment} news ({headline}) added {news_adjustment:+.2f}.")

    rsi = breakdown.get("rsi", 50.0)
    if rsi < 30:
        rsi_clause = "oversold; +2.0"
    elif rsi > 70:
        rsi_clause = "overbought; -2.0"
    else:
        rsi_clause = "neutral; no RSI adjustment"
    parts.append(f"RSI {rsi:.1f} is {rsi_clause}.")

    macd = breakdown.get("macd", 0.0)
    signal = breakdown.get("signal", 0.0)
    if macd > signal:
        macd_clause = "above its signal (+1.0)"
    elif macd < signal:
        macd_clause = "below its signal (-1.0)"
    else:
        macd_clause = "even with its signal (no MACD adjustment)"
    parts.append(f"MACD is {macd_clause}.")

    parts.append("It was sampled with this weight, not chosen as a guaranteed top pick.")

    unclamped = (
        breakdown.get("base", INITIAL_SCORE)
        + breakdown.get("history_adjustment", 0.0)
        + breakdown.get("news_adjustment", 0.0)
        + breakdown.get("rsi_adjustment", 0.0)
        + breakdown.get("macd_adjustment", 0.0)
    )
    score = breakdown["score"]
    if unclamped > SCORE_CEILING and score == SCORE_CEILING:
        parts.append("The total was clamped to the 30.0 score limit.")
    elif unclamped < SCORE_FLOOR and score == SCORE_FLOOR:
        parts.append("The total was clamped to the 1.0 score limit.")

    return " ".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_logic.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add logic.py tests/test_logic.py
git commit -m "Add a deterministic paragraph template for each pick explanation."
```

---

### Task 4: Attach `explanation` on generated picks

**Files:**
- Modify: `portfolio_service.py`
- Create: `tests/test_portfolio_service.py`

**Interfaces:**
- Consumes: `load_coin_scores` → `(scores, breakdowns)`; `compute_bucket_stats(available_stable, scores)` and `compute_bucket_stats(available_volatile, scores)`; `format_pick_explanation(breakdown, per_coin_stats, type, variance_percentile, display_name)`
- Produces: each `portfolio[]` item includes nested `explanation` with keys: `summary`, `base`, `history_adjustment`, `news_adjustment`, `news_headline`, `news_sentiment`, `rsi`, `rsi_adjustment`, `macd`, `signal`, `macd_adjustment`, `score`, `bucket_size`, `bucket_rank`, `bucket_avg_score`. `summary` is a non-empty string. Existing pick keys unchanged.

- [ ] **Step 1: Write the failing test**

Create `tests/test_portfolio_service.py`:

```python
import asyncio
from unittest.mock import AsyncMock, patch

from portfolio_service import generate_portfolio

EXPLANATION_KEYS = {
    "summary",
    "base",
    "history_adjustment",
    "news_adjustment",
    "news_headline",
    "news_sentiment",
    "rsi",
    "rsi_adjustment",
    "macd",
    "signal",
    "macd_adjustment",
    "score",
    "bucket_size",
    "bucket_rank",
    "bucket_avg_score",
}


def test_generate_portfolio_attaches_explanation():
    market_data = {
        "BTCUSDT": {"variance": 0.01, "rsi": 25.0, "macd": 0.1, "signal": 0.0},
        "ETHUSDT": {"variance": 0.02, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "SOLUSDT": {"variance": 0.10, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "XRPUSDT": {"variance": 0.12, "rsi": 40.0, "macd": 0.0, "signal": 0.05},
    }
    prices = {symbol: 1.0 for symbol in market_data}
    symbols = list(market_data.keys())

    with patch("portfolio_service.load_history", return_value=[]), \
         patch("portfolio_service.get_unevaluated_records", return_value=[]), \
         patch("portfolio_service.get_tradeable_symbols", return_value=symbols), \
         patch("portfolio_service.get_latest_news", AsyncMock(return_value=[])), \
         patch("portfolio_service.fetch_all_market_data", AsyncMock(return_value=market_data)), \
         patch("portfolio_service.analyze_news_impact", return_value=[]), \
         patch("portfolio_service.get_current_prices", return_value=prices), \
         patch("portfolio_service.add_portfolio_record"):
        result = asyncio.run(
            generate_portfolio(stable_count=1, volatile_count=1, variance_percentile=50.0)
        )

    assert "error" not in result
    assert len(result["portfolio"]) == 2
    for item in result["portfolio"]:
        assert "explanation" in item
        explanation = item["explanation"]
        assert EXPLANATION_KEYS <= set(explanation.keys())
        assert explanation["summary"]
        assert item["score"] == explanation["score"]
        assert item["type"] in ("Stable", "Volatile")
        assert explanation["bucket_size"] >= 1
        assert explanation["bucket_rank"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_portfolio_service.py::test_generate_portfolio_attaches_explanation -v`

Expected: FAIL (`explanation` missing).

- [ ] **Step 3: Attach explanations in `portfolio_service.py`**

Update the import:

```python
from logic import (
    compute_bucket_stats,
    evaluate_performance,
    format_pick_explanation,
    load_coin_scores,
    pick_portfolio,
)
```

Keep `scores, breakdowns = load_coin_scores(...)` (rename from `_breakdowns`).

After `stable_set = set(final_stable)` and before the `portfolio_items` loop, add:

```python
    stable_stats = compute_bucket_stats(available_stable, scores)
    volatile_stats = compute_bucket_stats(available_volatile, scores)
```

Replace the `portfolio_items.append({...})` body with:

```python
        display_name = coin.replace("USDT", "")
        bucket_type = "Stable" if coin in stable_set else "Volatile"
        per_coin_stats = (
            stable_stats.get(coin, {}) if bucket_type == "Stable" else volatile_stats.get(coin, {})
        )
        breakdown = dict(breakdowns.get(coin, {
            "base": 10.0,
            "history_adjustment": 0.0,
            "news_adjustment": 0.0,
            "news_headline": None,
            "news_sentiment": None,
            "rsi": market_data.get(coin, {}).get("rsi", 50.0) if market_data else 50.0,
            "rsi_adjustment": 0.0,
            "macd": market_data.get(coin, {}).get("macd", 0.0) if market_data else 0.0,
            "signal": market_data.get(coin, {}).get("signal", 0.0) if market_data else 0.0,
            "macd_adjustment": 0.0,
            "score": scores.get(coin, 10.0),
        }))
        explanation = {
            "summary": format_pick_explanation(
                breakdown, per_coin_stats, bucket_type, variance_percentile, display_name
            ),
            "base": breakdown["base"],
            "history_adjustment": breakdown["history_adjustment"],
            "news_adjustment": breakdown["news_adjustment"],
            "news_headline": breakdown["news_headline"],
            "news_sentiment": breakdown["news_sentiment"],
            "rsi": breakdown["rsi"],
            "rsi_adjustment": breakdown["rsi_adjustment"],
            "macd": breakdown["macd"],
            "signal": breakdown["signal"],
            "macd_adjustment": breakdown["macd_adjustment"],
            "score": breakdown["score"],
            "bucket_size": per_coin_stats.get("bucket_size", 0),
            "bucket_rank": per_coin_stats.get("bucket_rank", 0),
            "bucket_avg_score": per_coin_stats.get("bucket_avg_score", 10.0),
        }
        portfolio_items.append({
            "coin": coin,
            "display_name": display_name,
            "type": bucket_type,
            "price": prices.get(coin, 0.0),
            "score": scores.get(coin, 10.0),
            "rsi": market_data.get(coin, {}).get("rsi", 50.0) if market_data else 50.0,
            "variance": market_data.get(coin, {}).get("variance", 0.0) if market_data else 0.0,
            "explanation": explanation,
        })
```

Use `INITIAL_SCORE` from constants instead of literal `10.0` in the fallback dict if you already import constants; otherwise keep `10.0` to match the current file (it already uses `10.0` in replacement loops). Do not change `pick_portfolio` or history persistence.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_portfolio_service.py tests/test_logic.py -v`

Expected: PASS

Run: `.\venv\Scripts\python.exe -m ruff check portfolio_service.py tests/test_portfolio_service.py`

Expected: no issues

- [ ] **Step 5: Commit**

```bash
git add portfolio_service.py tests/test_portfolio_service.py
git commit -m "Attach structured pick explanations from the scoring pipeline."
```

---

### Task 5: API generate payload includes explanation

**Files:**
- Modify: `tests/test_server.py` (`test_generate_portfolio_success`)

**Interfaces:**
- Consumes: `portfolio[]` items as produced by Task 4 (nested `explanation`)
- Produces: HTTP generate JSON includes those keys on `portfolio[0].explanation`; still omits `scores`, `prices`, `market_data`

- [ ] **Step 1: Write the failing assertions**

In `tests/test_server.py`, replace the `portfolio` list inside `test_generate_portfolio_success` with:

```python
        "portfolio": [
            {
                "coin": "BTCUSDT",
                "display_name": "BTC",
                "type": "Stable",
                "price": 90000.0,
                "score": 15.0,
                "rsi": 50.0,
                "variance": 0.02,
                "explanation": {
                    "summary": "BTC is in the Stable bucket (lowest ~33% of 30-day variance among tradeable pairs this run).",
                    "base": 10.0,
                    "history_adjustment": 0.0,
                    "news_adjustment": 0.0,
                    "news_headline": None,
                    "news_sentiment": None,
                    "rsi": 50.0,
                    "rsi_adjustment": 0.0,
                    "macd": 0.0,
                    "signal": 0.0,
                    "macd_adjustment": 0.0,
                    "score": 15.0,
                    "bucket_size": 4,
                    "bucket_rank": 1,
                    "bucket_avg_score": 12.0,
                },
            }
        ],
```

After the existing asserts in that test, add:

```python
        explanation = data["portfolio"][0]["explanation"]
        assert explanation["summary"]
        assert explanation["score"] == 15.0
        assert explanation["bucket_rank"] == 1
        assert "market_data" not in data
```

Keep `assert "scores" not in data` and `assert "prices" not in data`.

- [ ] **Step 2: Run the test**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_server.py::test_generate_portfolio_success -v`

Expected: PASS without server.py changes, because generate already forwards `portfolio`. If it fails, the strip dict in `server.py` is dropping extra keys — do not strip `explanation`; only strip `scores`, `prices`, `market_data`, `final_stable`, `final_volatile`.

Current strip (leave as-is unless the test fails):

```python
    return {
        "evaluation_results": result.get("evaluation_results", []),
        "news": result.get("news", []),
        "sentiment_impacts": result.get("sentiment_impacts", []),
        "portfolio": result.get("portfolio", []),
    }
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_server.py
git commit -m "Assert generate API returns pick explanations and still strips internals."
```

---

### Task 6: CLI Why these picks

**Files:**
- Modify: `main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `item["explanation"]["summary"]` from Task 4
- Produces: after the Recommended Portfolio table, a `Why these picks` heading and one escaped line per pick that has a non-empty summary. Missing `explanation` skips that coin’s Why line and still prints the table.

- [ ] **Step 1: Write the failing tests**

In `tests/test_main.py`, add `explanation` to the success mock’s first pick only, and assert output. Also add a missing-explanation test.

Update `test_run_command_success` portfolio to:

```python
        "portfolio": [
            {
                "coin": "BTCUSDT",
                "display_name": "BTC",
                "type": "Stable",
                "price": 90000.0,
                "score": 15.0,
                "rsi": 50.0,
                "variance": 0.02,
                "explanation": {
                    "summary": "BTC is in the Stable bucket (lowest ~33% of 30-day variance among tradeable pairs this run). It was sampled with this weight, not chosen as a guaranteed top pick.",
                    "base": 10.0,
                    "history_adjustment": 0.0,
                    "news_adjustment": 0.0,
                    "news_headline": None,
                    "news_sentiment": None,
                    "rsi": 50.0,
                    "rsi_adjustment": 0.0,
                    "macd": 0.0,
                    "signal": 0.0,
                    "macd_adjustment": 0.0,
                    "score": 15.0,
                    "bucket_size": 2,
                    "bucket_rank": 1,
                    "bucket_avg_score": 12.5,
                },
            },
            {"coin": "ETHUSDT", "display_name": "ETH", "type": "Volatile", "price": 3000.0, "score": 10.0, "rsi": 50.0, "variance": 0.05},
        ],
```

Add to that test’s asserts:

```python
        assert "Why these picks" in result.output
        assert "BTC is in the Stable bucket" in result.output
        assert "sampled with this weight" in result.output
```

Add a new test:

```python
def test_run_command_skips_why_line_when_explanation_missing():
    mock_portfolio_result = {
        "evaluation_results": [],
        "news": [],
        "sentiment_impacts": [],
        "portfolio": [
            {"coin": "BTCUSDT", "display_name": "BTC", "type": "Stable", "price": 90000.0, "score": 15.0, "rsi": 50.0, "variance": 0.02},
        ],
        "scores": {},
        "prices": {},
        "final_stable": ["BTCUSDT"],
        "final_volatile": [],
        "market_data": {},
    }
    with patch("main.generate_portfolio", AsyncMock(return_value=mock_portfolio_result)):
        result = runner.invoke(app, ["run", "--stable", "1", "--volatile", "1"])
        assert result.exit_code == 0
        assert "Recommended Portfolio" in result.output
        assert "BTC is in the Stable bucket" not in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_main.py::test_run_command_success -v`

Expected: FAIL (`Why these picks` not in output).

- [ ] **Step 3: Implement CLI section**

In `main.py`, add:

```python
from rich.markup import escape
```

Immediately after `console.print(p_table)` and before the Done message:

```python
    console.print("\n[bold yellow]Why these picks[/bold yellow]")
    for item in portfolio_items:
        explanation = item.get("explanation") or {}
        summary = explanation.get("summary")
        if not summary:
            continue
        console.print(f"[magenta]{escape(str(item['display_name']))}[/magenta]  {escape(summary)}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_main.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "Print the shared pick explanation paragraph in the CLI."
```

---

### Task 7: Dashboard MACD and summary

**Files:**
- Modify: `frontend/src/App.jsx` (coin card)
- Modify: `frontend/src/App.css`

**Interfaces:**
- Consumes: `coin.explanation.macd`, `coin.explanation.signal`, `coin.explanation.summary`
- Produces: card shows MACD as `{macd:.2f} / {signal:.2f}` when `explanation` exists; always-visible paragraph when `summary` is present; no crash when `explanation` is missing.

- [ ] **Step 1: Update the coin card**

Replace the card inner content in `frontend/src/App.jsx` (the `portfolio.map` block) with:

```jsx
                  {portfolio.map((coin) => (
                    <div key={coin.coin} className="coin-card">
                      <div className="coin-card-header">
                        <span className="coin-symbol">{coin.display_name}</span>
                        <span className={`coin-badge ${coin.type.toLowerCase()}`}>
                          {coin.type}
                        </span>
                      </div>
                      <div className="coin-price">
                        ${coin.price > 1 ? coin.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : coin.price.toFixed(4)}
                      </div>
                      <div className="coin-metrics">
                        <div className="metric-item">
                          <span className="metric-label">Score</span>
                          <span className="metric-value highlight">{coin.score.toFixed(2)}</span>
                        </div>
                        <div className="metric-item">
                          <span className="metric-label">RSI (14)</span>
                          <span className="metric-value">{coin.rsi.toFixed(1)}</span>
                        </div>
                        {coin.explanation && (
                          <div className="metric-item">
                            <span className="metric-label">MACD</span>
                            <span className="metric-value">
                              {coin.explanation.macd.toFixed(2)} / {coin.explanation.signal.toFixed(2)}
                            </span>
                          </div>
                        )}
                      </div>
                      {coin.explanation?.summary && (
                        <p className="coin-explanation">{coin.explanation.summary}</p>
                      )}
                    </div>
                  ))}
```

- [ ] **Step 2: Style the paragraph**

In `frontend/src/App.css`, change `.portfolio-grid` minmax from `220px` to `280px`, change `.coin-metrics` to three columns, and add:

```css
.coin-explanation {
  font-size: 0.78rem;
  line-height: 1.45;
  color: var(--text-secondary);
  margin: 0;
}
```

Replace the existing `.coin-metrics` rule with:

```css
.coin-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 12px;
}
```

- [ ] **Step 3: Manual check**

There is no frontend test runner. Confirm `App.jsx` uses optional chaining so a pick without `explanation` still renders Score and RSI. If `/run-fe` is available, generate a portfolio and confirm each card shows Score, RSI, MACD, and the paragraph.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.jsx frontend/src/App.css
git commit -m "Show MACD and the pick explanation paragraph on dashboard cards."
```

---

### Task 8: Docs and handoff

**Files:**
- Modify: `docs/context.md`
- Modify: `docs/architecture.md`
- Modify: `progress.md`

**Interfaces:**
- Consumes: shipped behavior from Tasks 1–7
- Produces: markdown source of truth matches the feature; `progress.md` last-session note for #19

- [ ] **Step 1: Update `docs/context.md`**

Add this bullet under **Core Features & Rules**:

```markdown
- **Pick explanations:** Each generated coin includes a structured breakdown (history, news, RSI/MACD, bucket rank vs average) and a templated paragraph in both the CLI and the dashboard. Copy is derived from the same scoring pass used to pick.
```

Change proposed feature 1 to:

```markdown
1. **Explain each pick:** Shipped in #19 (CLI `run` + dashboard cards). Remaining backlog starts at strategy vs BTC.
```

- [ ] **Step 2: Update `docs/architecture.md`**

Replace the `logic.py` and `portfolio_service.py` bullets with:

```markdown
- `logic.py`: Pure functions containing the heuristic scoring, coin selection, portfolio generation logic, score breakdowns, bucket rank/average, and the pick-explanation paragraph template.
- `portfolio_service.py`: Shared async portfolio generation pipeline used by the CLI and the API. Each pick in `portfolio` includes a nested `explanation` object (components + `summary`).
```

- [ ] **Step 3: Update `progress.md`**

Replace **Last session** with:

```markdown
## Last session
On `issue-19-explain-picks`: picks now carry a nested `explanation` (score components, bucket rank/average, templated `summary`) from the existing scoring pipeline. CLI `run` prints Why these picks; dashboard cards show MACD plus the paragraph. Spec: `docs/superpowers/specs/2026-09-07-pick-explanations-design.md`.
```

Under **Open work**, change `#19 explain picks` to note it is on this branch / PR.

- [ ] **Step 4: Run the full suite**

Run: `.\venv\Scripts\python.exe -m pytest`

Expected: PASS

Run: `.\venv\Scripts\python.exe -m ruff check .`

Expected: no issues

- [ ] **Step 5: Commit**

```bash
git add docs/context.md docs/architecture.md progress.md docs/superpowers/specs/2026-09-07-pick-explanations-design.md docs/superpowers/plans/2026-09-07-pick-explanations.md
git commit -m "Document pick explanations in product and architecture notes."
```

Include the spec and plan in this commit if they are still untracked.

---

## Spec coverage check

| Spec section | Task |
|---|---|
| `load_coin_scores` tuple + breakdown keys | Task 1 |
| `compute_bucket_stats` rank/ties/empty | Task 2 |
| Paragraph sentence order, omit zeros, clamp, truncation | Task 3 |
| Attach `explanation` on picks, replacements still explained | Task 4 |
| API strip internals, explanation on portfolio | Task 5 |
| CLI Why section + Rich escape + missing explanation | Task 6 |
| Dashboard MACD + summary, missing explanation safe | Task 7 |
| `history.json` unchanged | Tasks 4–7 never write it |
| Docs | Task 8 |
| No LLM / no second ranking | All tasks |
