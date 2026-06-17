import random
import asyncio
from binance_client import (
    get_current_prices, 
    get_tradeable_symbols,
    fetch_all_technical_indicators,
    fetch_all_variances
)
from history import load_history, save_history, get_unevaluated_records

def load_coin_scores(universe, sentiment_impacts=None):
    scores = {coin: 10.0 for coin in universe}
    
    # Adjust based on history
    history = load_history()
    for record in history:
        if record.get("evaluated") and "performance" in record:
            for coin, p_change in record["performance"].items():
                if coin in scores:
                    adjustment = p_change * 100
                    scores[coin] = max(1.0, scores[coin] + adjustment)
                        
    # Apply news sentiment impacts
    if sentiment_impacts:
        for impact in sentiment_impacts:
            coin = impact["coin"]
            if coin in scores:
                scores[coin] = max(1.0, scores[coin] + impact["adjustment"])
                    
    # Apply Technical Indicator modifiers concurrently
    ti_data = asyncio.run(fetch_all_technical_indicators(universe))
    
    for coin in scores:
        ti = ti_data.get(coin, {"rsi": 50.0, "macd": 0.0, "signal": 0.0})
        rsi = ti["rsi"]
        macd = ti["macd"]
        signal = ti["signal"]
        
        if rsi < 30:
            scores[coin] += 2.0
        elif rsi > 70:
            scores[coin] -= 2.0
            
        if macd > signal:
            scores[coin] += 1.0
        elif macd < signal:
            scores[coin] -= 1.0
            
        scores[coin] = max(1.0, scores[coin])
                    
    return scores

def pick_portfolio(sentiment_impacts=None, stable_count=2, volatile_count=3):
    valid_symbols = get_tradeable_symbols(limit=100)
    if not valid_symbols:
        return [], {}, set()
        
    # Get variances to categorize coins
    variances = asyncio.run(fetch_all_variances(valid_symbols))
    
    # Sort symbols by variance
    sorted_symbols = sorted([s for s in valid_symbols if s in variances], key=lambda x: variances[x])
    
    # Categorize: lowest 1/3 stable, highest 2/3 volatile
    third = max(1, len(sorted_symbols) // 3)
    available_stable = sorted_symbols[:third]
    available_volatile = sorted_symbols[third:]
    
    universe = available_stable + available_volatile
    scores = load_coin_scores(universe, sentiment_impacts)
    
    def unique_weighted_sample(population, k):
        selected = set()
        pop_copy = list(population)
        while len(selected) < k and pop_copy:
            weights = [scores[c] for c in pop_copy]
            choice = random.choices(pop_copy, weights=weights, k=1)[0]
            selected.add(choice)
            pop_copy.remove(choice)
        return list(selected)

    stable_picks = unique_weighted_sample(available_stable, min(stable_count, len(available_stable)))
    volatile_picks = unique_weighted_sample(available_volatile, min(volatile_count, len(available_volatile)))
    
    portfolio = stable_picks + volatile_picks
    prices = get_current_prices(portfolio)
    
    return portfolio, prices, set(stable_picks), scores

def evaluate_performance():
    unevaluated = get_unevaluated_records()
    if not unevaluated:
        return []
        
    # Gather all unique coins to fetch prices once
    all_coins = set()
    for record in unevaluated:
        all_coins.update(record["portfolio"])
        
    current_prices = get_current_prices(list(all_coins))
    
    history = load_history()
    results = []
    
    for record in unevaluated:
        portfolio = record["portfolio"]
        old_prices = record["entry_prices"]
        
        performance = {}
        for coin in portfolio:
            old_p = old_prices.get(coin, 0)
            curr_p = current_prices.get(coin, 0)
            if old_p > 0 and curr_p > 0:
                performance[coin] = (curr_p - old_p) / old_p
            else:
                performance[coin] = 0.0
                
        # update the loaded history in memory
        for r in history:
            if r.get("timestamp") == record["timestamp"]:
                r["performance"] = performance
                r["evaluated"] = True
                break
                
        results.append({
            "timestamp": record["timestamp"],
            "performance": performance
        })
        
    save_history(history)
    return results
