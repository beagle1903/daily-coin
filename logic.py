import random

def load_coin_scores(universe, history, sentiment_impacts=None, technical_indicators=None):
    """
    Pure function that calculates heuristic scores for the coin universe.
    
    :param universe: List of coin symbols in the universe
    :param history: List of historical portfolio records loaded from history.json
    :param sentiment_impacts: List of sentiment impact dicts from news analysis
    :param technical_indicators: Dict of symbol -> {"rsi": ..., "macd": ..., "signal": ...}
    """
    scores = {coin: 10.0 for coin in universe}
    
    # Adjust based on history
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
                    
    # Apply Technical Indicator modifiers
    if technical_indicators:
        for coin in scores:
            ti = technical_indicators.get(coin, {"rsi": 50.0, "macd": 0.0, "signal": 0.0})
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

def pick_portfolio(available_stable, available_volatile, scores, stable_count=3, volatile_count=6):
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
            weights = [scores.get(c, 10.0) for c in pop_copy]
            choice = random.choices(pop_copy, weights=weights, k=1)[0]
            selected.add(choice)
            pop_copy.remove(choice)
        return list(selected)

    stable_picks = unique_weighted_sample(available_stable, min(stable_count, len(available_stable)))
    volatile_picks = unique_weighted_sample(available_volatile, min(volatile_count, len(available_volatile)))
    
    return stable_picks, volatile_picks

def evaluate_performance(unevaluated_records, current_prices, history):
    """
    Pure function that evaluates the performance of unevaluated past records.
    
    :param unevaluated_records: List of unevaluated history records
    :param current_prices: Dict of coin symbol -> current price
    :param history: The complete list of history records to be updated
    :return: (updated_history, results)
    """
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
                # Coin was delisted or price fetch failed; record -100% performance loss
                performance[coin] = -1.0
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
