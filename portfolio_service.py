"""
Shared portfolio generation service used by both CLI (main.py) and API (server.py).
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


def _fill_bucket(picks, candidates, count, prices, scores):
    """
    Keep the picks that have a non-zero price, then add the highest-scoring other
    candidates with a price until ``count`` is reached. Returned best score first.
    """
    filled = [coin for coin in picks if prices.get(coin, 0.0) > 0]
    chosen = set(picks)
    for candidate in sorted(candidates, key=lambda coin: scores[coin], reverse=True):
        if len(filled) >= count:
            break
        if candidate not in chosen and prices.get(candidate, 0.0) > 0:
            filled.append(candidate)
    return sorted(filled, key=lambda coin: scores[coin], reverse=True)


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

    :returns: dict with keys: evaluation_results, held_evaluations, news,
              sentiment_impacts, portfolio (list of dicts), mock
              OR dict with an 'error' key on failure.
    """
    mock_mark = mock_serve_count()

    def used_mock():
        return mock_serve_count() != mock_mark

    # 1. Load history once
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

    scores, breakdowns = load_coin_scores(universe, history, impacts, market_data)

    # 5. Pick portfolio
    stable_picks, volatile_picks = pick_portfolio(
        available_stable, available_volatile, scores,
        stable_count=stable_count, volatile_count=volatile_count
    )

    # 6. Keep picks that have a non-zero price; top each bucket up from the
    #    remaining candidates by score
    picked = set(stable_picks + volatile_picks)
    prices = get_current_prices(stable_picks + volatile_picks)
    remaining = [s for s in universe if s not in picked]
    if remaining:
        prices.update(get_current_prices(remaining))

    final_stable = _fill_bucket(stable_picks, available_stable, stable_count, prices, scores)
    final_volatile = _fill_bucket(volatile_picks, available_volatile, volatile_count, prices, scores)
    final_portfolio = final_stable + final_volatile

    if not final_portfolio:
        return {"error": "Could not find any coins with non-zero prices."}

    is_mock = used_mock()

    # Build structured result
    bucket_stats = {
        "Stable": compute_bucket_stats(available_stable, scores),
        "Volatile": compute_bucket_stats(available_volatile, scores),
    }
    stable_set = set(final_stable)
    portfolio_items = []
    for coin in final_portfolio:
        display_name = coin.replace("USDT", "")
        bucket_type = "Stable" if coin in stable_set else "Volatile"
        breakdown = breakdowns[coin]
        stats = bucket_stats[bucket_type][coin]
        explanation = {
            "summary": format_pick_explanation(
                breakdown, stats, bucket_type, variance_percentile, display_name
            ),
            **breakdown,
            **stats,
        }
        portfolio_items.append({
            "coin": coin,
            "display_name": display_name,
            "type": bucket_type,
            "price": prices[coin],
            "score": scores[coin],
            "rsi": breakdown["rsi"],
            "variance": market_data[coin]["variance"],
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
    }
