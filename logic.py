import random
from binance_client import get_current_prices, get_tradeable_symbols
from history import load_history

# Qualitative grouping from docs/crypto_coin_mental_models_and_grouping_report.md
CONSERVATIVE = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"]
MODERATE = ["SOLUSDT", "LINKUSDT", "AVAXUSDT", "UNIUSDT", "DOTUSDT", "LTCUSDT", "MATICUSDT", "ATOMUSDT"]
AGGRESSIVE = ["SUIUSDT", "HYPEUSDT", "PEPEUSDT", "SHIBUSDT", "DOGEUSDT", "WIFUSDT", "BONKUSDT", "FLOKIUSDT"]

# Stable = Conservative, Volatile = Moderate + Aggressive

def get_coin_universe():
    return CONSERVATIVE + MODERATE + AGGRESSIVE

def load_coin_scores(sentiment_impacts=None):
    # Base score for all coins is 10.0
    universe = get_coin_universe()
    scores = {coin: 10.0 for coin in universe}
    
    # Adjust based on history
    history = load_history()
    for record in history:
        if record.get("evaluated") and "performance" in record:
            for coin, p_change in record["performance"].items():
                if coin in scores:
                    # heuristic: +1 score per 1% gain, -1 score per 1% loss
                    adjustment = p_change * 100
                    scores[coin] += adjustment
                    
                    # Prevent scores from going negative or zero
                    if scores[coin] < 1.0:
                        scores[coin] = 1.0
                        
    # Apply news sentiment impacts
    if sentiment_impacts:
        for impact in sentiment_impacts:
            coin = impact["coin"]
            if coin in scores:
                scores[coin] += impact["adjustment"]
                if scores[coin] < 1.0:
                    scores[coin] = 1.0
                    
    # Apply Technical Indicator modifiers
    from binance_client import get_technical_indicators
    for coin in scores:
        ti = get_technical_indicators(coin)
        rsi = ti["rsi"]
        macd = ti["macd"]
        signal = ti["signal"]
        
        # RSI Modifier
        if rsi < 30:
            scores[coin] += 2.0  # oversold, good buy
        elif rsi > 70:
            scores[coin] -= 2.0  # overbought, bad buy
            
        # MACD Modifier
        if macd > signal:
            scores[coin] += 1.0  # bullish trend
        elif macd < signal:
            scores[coin] -= 1.0  # bearish trend
            
        if scores[coin] < 1.0:
            scores[coin] = 1.0
                    
    return scores

def pick_portfolio(sentiment_impacts=None, stable_count=2, volatile_count=3):
    scores = load_coin_scores(sentiment_impacts)
    valid_symbols = get_tradeable_symbols(limit=100)
    
    available_stable = [c for c in CONSERVATIVE if c in valid_symbols]
    available_volatile = [c for c in MODERATE + AGGRESSIVE if c in valid_symbols]
    
    # Weighted random selection based on unique scores
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
    
    return portfolio, prices

def evaluate_performance():
    from history import get_unevaluated_records, load_history, save_history
    unevaluated = get_unevaluated_records()
    if not unevaluated:
        return []
        
    results = []
    for record in unevaluated:
        portfolio = record["portfolio"]
        old_prices = record["entry_prices"]
        current_prices = get_current_prices(portfolio)
        
        performance = {}
        for coin in portfolio:
            old_p = old_prices.get(coin, 0)
            curr_p = current_prices.get(coin, 0)
            if old_p > 0 and curr_p > 0:
                performance[coin] = (curr_p - old_p) / old_p
            else:
                performance[coin] = 0.0
                
        # save performance back to record
        history = load_history()
        for r in history:
            if r.get("timestamp") == record["timestamp"]:
                r["performance"] = performance
                r["evaluated"] = True
        save_history(history)
        
        results.append({
            "timestamp": record["timestamp"],
            "performance": performance
        })
        
    return results
