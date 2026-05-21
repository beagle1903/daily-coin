import math
from binance.client import Client
from config import BINANCE_API_KEY, BINANCE_API_SECRET

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

def get_tradeable_symbols(limit=30):
    """
    Fetch a list of top USDT-paired symbols by trading volume to consider for portfolio.
    """
    tickers = client.get_ticker()
    
    # Filter for USDT pairs, excluding stablecoin pairs like BUSDUSDT, USDCUSDT if possible
    # We will just grab everything ending in USDT for simplicity, then sort by volume.
    usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
    
    # Sort by quote volume descending to get top liquid pairs
    usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
    
    # Return just the symbols of top `limit`
    return [t['symbol'] for t in usdt_pairs[:limit]]

def get_current_prices(symbols):
    """
    Fetch current prices for the given symbols.
    """
    prices = client.get_all_tickers()
    prices_map = {p['symbol']: float(p['price']) for p in prices}
    return {s: prices_map[s] for s in symbols if s in prices_map}

def get_30d_variance(symbol):
    """
    Fetch 30 days of daily klines and calculate standard deviation of daily returns.
    """
    try:
        klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1DAY, "30 days ago UTC")
    except Exception as e:
        return 0.0

    closes = [float(k[4]) for k in klines]
    
    if len(closes) < 2:
        return 0.0
        
    returns = []
    for i in range(1, len(closes)):
        prev = closes[i-1]
        curr = closes[i]
        if prev > 0:
            returns.append((curr - prev) / prev)
            
    if not returns:
        return 0.0
        
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    return math.sqrt(variance)
