"""
Shared portfolio generation service used by both CLI (main.py) and API (server.py).
Eliminates code duplication and ensures a single history load per run.
"""
import asyncio

from constants import DEFAULT_VARIANCE_PERCENTILE, MIN_EVALUATION_AGE_SECONDS, NEWS_LIMIT
from binance_client import (
    fetch_all_market_data,
    get_current_prices,
    get_tradeable_symbols,
    mock_serve_count,
)
from history import add_portfolio_record, get_unevaluated_records, load_history, save_history
from logic import (
    compute_bucket_stats,
    evaluate_performance,
    format_pick_explanation,
    load_coin_scores,
    pick_portfolio,
)
from news import analyze_news_impact, get_latest_news


async def generate_portfolio(stable_count: int, volatile_count: int, variance_percentile: float = DEFAULT_VARIANCE_PERCENTILE):
    """
    Full portfolio generation pipeline:
    1. Load history once
    2. Evaluate past portfolios
    3. Fetch symbols, news, market data concurrently
    4. Score, pick, and verify prices
    5. Persist and return results

    If Binance was unavailable and any step fell back to mock data, the run is
    display-only: past records are not evaluated against mock prices, the new
    portfolio is not saved to history, and the result has ``mock`` set to True.

    Pending records younger than MIN_EVALUATION_AGE_SECONDS are not evaluated yet;
    ``held_evaluations`` is how many were left for a later run.

    :returns: dict with keys: evaluation_results, held_evaluations, news, sentiment_impacts,
              portfolio (list of dicts), mock, scores, market_data, final_stable,
              final_volatile, prices OR dict with 'error' key on failure.
    """
    mock_mark = mock_serve_count()

    def used_mock():
        return mock_serve_count() != mock_mark

    # 1. Load history ONCE (fixes P0-3: redundant I/O)
    history = load_history()
    # Only records past the minimum holding time are evaluated; younger ones stay pending
    unevaluated = get_unevaluated_records(
        history=history, min_age_seconds=MIN_EVALUATION_AGE_SECONDS
    )
    held_evaluations = len(get_unevaluated_records(history=history)) - len(unevaluated)
    evaluation_results = []

    # 2. Get tradeable symbols
    valid_symbols = get_tradeable_symbols(limit=100)
    if not valid_symbols:
        return {"error": "Could not fetch valid symbols from Binance."}

    if unevaluated and not used_mock():
        all_coins = set()
        for record in unevaluated:
            all_coins.update(record["portfolio"])

        current_prices = get_current_prices(list(all_coins))
        # Records stay pending if the prices came from the mock fallback
        if not used_mock():
            updated_history, results = evaluate_performance(unevaluated, current_prices, history, valid_symbols)
            save_history(updated_history)
            evaluation_results = results
            # Reload history after evaluation mutations
            history = updated_history

    # 3. Fetch news and market data concurrently
    news_task = get_latest_news(limit=NEWS_LIMIT)
    market_data_task = fetch_all_market_data(valid_symbols)

    news_items, market_data = await asyncio.gather(news_task, market_data_task)

    impacts = []
    if news_items:
        impacts = analyze_news_impact(news_items, valid_symbols)

    # 4. Categorize symbols based on variance
    sorted_symbols = sorted(
        [s for s in valid_symbols if s in market_data],
        key=lambda x: market_data[x]["variance"]
    )
    if not sorted_symbols:
        return {"error": "No valid market data retrieved from Binance."}

    threshold_idx = max(1, int(len(sorted_symbols) * (variance_percentile / 100.0)))
    available_stable = sorted_symbols[:threshold_idx]
    available_volatile = sorted_symbols[threshold_idx:]

    universe = available_stable + available_volatile

    # Use the already-loaded history (no redundant reload)
    scores, breakdowns = load_coin_scores(universe, history, impacts, market_data)

    # 5. Pick portfolio
    stable_picks, volatile_picks = pick_portfolio(
        available_stable, available_volatile, scores,
        stable_count=stable_count, volatile_count=volatile_count
    )

    # 6. Verify and resolve non-zero entry prices
    portfolio = stable_picks + volatile_picks
    prices = get_current_prices(portfolio)

    tried_symbols = set(portfolio)

    final_stable = [coin for coin in stable_picks if prices.get(coin, 0.0) > 0]
    final_volatile = [coin for coin in volatile_picks if prices.get(coin, 0.0) > 0]

    # Batch fetch prices for all remaining candidates
    remaining_stable = [s for s in available_stable if s not in tried_symbols]
    remaining_volatile = [v for v in available_volatile if v not in tried_symbols]
    all_remaining = remaining_stable + remaining_volatile
    
    if all_remaining:
        remaining_prices = get_current_prices(all_remaining)
        prices.update(remaining_prices)

    # Replacement loop for stable coins
    while len(final_stable) < stable_count and remaining_stable:
        remaining_stable.sort(key=lambda x: scores.get(x, 10.0), reverse=True)
        candidate = remaining_stable.pop(0)
        tried_symbols.add(candidate)
        cand_price = prices.get(candidate, 0.0)
        if cand_price > 0:
            final_stable.append(candidate)

    # Replacement loop for volatile coins
    while len(final_volatile) < volatile_count and remaining_volatile:
        remaining_volatile.sort(key=lambda x: scores.get(x, 10.0), reverse=True)
        candidate = remaining_volatile.pop(0)
        tried_symbols.add(candidate)
        cand_price = prices.get(candidate, 0.0)
        if cand_price > 0:
            final_volatile.append(candidate)

    final_stable.sort(key=lambda x: scores.get(x, 10.0), reverse=True)
    final_volatile.sort(key=lambda x: scores.get(x, 10.0), reverse=True)
    final_portfolio = final_stable + final_volatile

    if not final_portfolio:
        return {"error": "Could not find any coins with non-zero prices."}

    is_mock = used_mock()

    # Build structured result
    stable_set = set(final_stable)
    stable_stats = compute_bucket_stats(available_stable, scores)
    volatile_stats = compute_bucket_stats(available_volatile, scores)
    portfolio_items = []
    for coin in final_portfolio:
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

    if not is_mock:
        add_portfolio_record(final_portfolio, prices, picks=portfolio_items)

    return {
        "evaluation_results": evaluation_results,
        "held_evaluations": held_evaluations,
        "news": news_items,
        "sentiment_impacts": impacts,
        "portfolio": portfolio_items,
        "mock": is_mock,
        "scores": scores,
        "market_data": market_data,
        "final_stable": final_stable,
        "final_volatile": final_volatile,
        "prices": prices,
    }
