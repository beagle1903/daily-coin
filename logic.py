import random

from constants import SCORE_FLOOR, SCORE_CEILING, MAX_PER_RECORD_ADJUSTMENT, INITIAL_SCORE, DEFAULT_STABLE_COUNT, DEFAULT_VOLATILE_COUNT


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

def pick_portfolio(available_stable, available_volatile, scores, stable_count=DEFAULT_STABLE_COUNT, volatile_count=DEFAULT_VOLATILE_COUNT):
    """
    Pure function that selects stable and volatile picks based on scores.
    
    :param available_stable: List of stable symbols sorted by variance (lowest first)
    :param available_volatile: List of volatile symbols sorted by variance
    :param scores: Dict of symbol -> score
    :param stable_count: Number of stable coins to select
    :param volatile_count: Number of volatile coins to select
    :return: (selected_stable_picks, selected_volatile_picks)
    """
    def unique_weighted_sample(population, k):
        selected = set()
        pop_copy = list(population)
        while len(selected) < k and pop_copy:
            weights = [scores.get(c, INITIAL_SCORE) for c in pop_copy]
            choice = random.choices(pop_copy, weights=weights, k=1)[0]
            selected.add(choice)
            pop_copy.remove(choice)
        return list(selected)

    stable_picks = unique_weighted_sample(available_stable, min(stable_count, len(available_stable)))
    volatile_picks = unique_weighted_sample(available_volatile, min(volatile_count, len(available_volatile)))
    
    return stable_picks, volatile_picks

def evaluate_performance(unevaluated_records, current_prices, history, tradeable_symbols=None):
    """
    Pure function that evaluates the performance of unevaluated past records.
    
    :param unevaluated_records: List of unevaluated history records
    :param current_prices: Dict of coin symbol -> current price
    :param history: The complete list of history records to be updated
    :param tradeable_symbols: Optional set/list of currently tradeable symbols to distinguish between fetch failure and delisting
    :return: (updated_history, results)
    """
    if tradeable_symbols is None:
        tradeable_symbols = set()
    else:
        tradeable_symbols = set(tradeable_symbols)

    results = []
    updated_history = [dict(r) for r in history]
    
    for record in unevaluated_records:
        portfolio = record["portfolio"]
        old_prices = record["entry_prices"]
        
        performance = {}
        for coin in portfolio:
            old_p = old_prices.get(coin, 0)
            curr_p = current_prices.get(coin, 0)
            if old_p > 0 and curr_p > 0:
                performance[coin] = (curr_p - old_p) / old_p
            elif curr_p == 0 and old_p > 0:
                if not tradeable_symbols or coin not in tradeable_symbols:
                    # Coin was delisted; record -100% performance loss
                    performance[coin] = -1.0
                else:
                    # Transient price fetch error, but coin still tradeable. Assume 0.0 change.
                    performance[coin] = 0.0
            else:
                performance[coin] = 0.0
                
        for r in updated_history:
            if r.get("timestamp") == record["timestamp"]:
                r["performance"] = performance
                r["evaluated"] = True
                break
                
        results.append({
            "timestamp": record["timestamp"],
            "performance": performance
        })
        
    return updated_history, results
