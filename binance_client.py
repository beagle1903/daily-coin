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

def get_klines_closes(symbol, days=60):
    """
    Fetch daily closes for the last X days.
    """
    try:
        klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1DAY, f"{days} days ago UTC")
        return [float(k[4]) for k in klines]
    except Exception:
        return []

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(diff))
            
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(closes)-1):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def calculate_macd(closes):
    if len(closes) < 35:
        return 0.0, 0.0
        
    def ema_array(data, p):
        res = [sum(data[:p])/p]
        mul = 2 / (p + 1)
        for d in data[p:]:
            res.append(d * mul + res[-1] * (1 - mul))
        return [None]*(p-1) + res

    ema_12 = ema_array(closes, 12)
    ema_26 = ema_array(closes, 26)
    
    macd_series = []
    for e12, e26 in zip(ema_12, ema_26):
        if e12 is not None and e26 is not None:
            macd_series.append(e12 - e26)
        else:
            macd_series.append(None)
            
    valid_macd = [m for m in macd_series if m is not None]
    if len(valid_macd) < 9:
        return 0.0, 0.0
        
    signal_series = ema_array(valid_macd, 9)
    
    return valid_macd[-1], signal_series[-1]

def get_technical_indicators(symbol):
    """
    Returns a dict with RSI and MACD signals.
    """
    closes = get_klines_closes(symbol, days=60)
    if not closes:
        return {"rsi": 50.0, "macd": 0.0, "signal": 0.0}
        
    rsi = calculate_rsi(closes)
    macd, signal = calculate_macd(closes)
    return {"rsi": rsi, "macd": macd, "signal": signal}
