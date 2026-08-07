import asyncio
import json
import math
import os
import sys
import time as _time

from binance import AsyncClient
from binance.client import Client
from binance.exceptions import BinanceAPIException

from config import BINANCE_API_KEY, BINANCE_API_SECRET

_client = None
MOCK_DATA_UNTIL = 0

def _is_mock_mode_active():
    if os.environ.get("OFFLINE_MOCK", "").lower() in ("true", "1"):
        return True
    return _time.time() < MOCK_DATA_UNTIL

def _activate_circuit_breaker(err_msg):
    global MOCK_DATA_UNTIL
    print(f"Warning: {err_msg}. Activating Offline Mock Mode for 60 seconds.", file=sys.stderr)
    MOCK_DATA_UNTIL = _time.time() + 60
# --- TTL Cache ---
_cache = {}

def _cache_get(key, ttl_seconds):
    """Return cached value if key exists and hasn't expired, else None."""
    entry = _cache.get(key)
    if entry is not None:
        value, ts = entry
        if _time.time() - ts < ttl_seconds:
            return value
    return None

def _cache_set(key, value):
    """Store a value in the cache with the current timestamp."""
    _cache[key] = (value, _time.time())

SYMBOLS_CACHE_TTL = 3600      # 1 hour
MARKET_DATA_CACHE_TTL = 900   # 15 minutes

def get_sync_client():
    global _client
    if _is_mock_mode_active():
        return None
    if _client is not None:
        return _client
    try:
        # Set a short timeout for the initial ping to avoid long hangs
        _client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, requests_params={'timeout': 5})
        return _client
    except Exception as e:
        _activate_circuit_breaker(f"Binance API connection failed ({type(e).__name__}: {e})")
        return None

def load_midas_allowlist():
    try:
        path = os.path.join(os.path.dirname(__file__), 'midas_coins.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return set(json.load(f))
    except Exception:
        pass
    return None

def get_tradeable_symbols(limit=30):
    # Check cache first
    cache_key = f"tradeable_symbols_{limit}"
    cached = _cache_get(cache_key, SYMBOLS_CACHE_TTL)
    if cached is not None:
        return cached

    allowlist = load_midas_allowlist()
    client = get_sync_client()
    if _is_mock_mode_active() or client is None:
        mock_symbols = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", 
            "XRPUSDT", "DOTUSDT", "LTCUSDT", "DOGEUSDT", "AVAXUSDT", 
            "LINKUSDT", "SHIBUSDT", "UNIUSDT", "ATOMUSDT", "SUIUSDT", 
            "PEPEUSDT", "WIFUSDT", "FLOKIUSDT", "BONKUSDT", "HYPEUSDT"
        ]
        if allowlist is not None:
            mock_symbols = [s for s in mock_symbols if s[:-4] in allowlist]
        result = mock_symbols[:limit]
        _cache_set(cache_key, result)
        return result
    try:
        tickers = client.get_ticker()
        excluded_bases = {"USDC", "FDUSD", "TUSD", "BUSD", "USD1", "EUR", "DAI", "USDD", "PYUSD", "USDP", "AEUR"}
        usdt_pairs = [
            t for t in tickers 
            if t['symbol'].endswith('USDT') and t['symbol'][:-4] not in excluded_bases
            and (allowlist is None or t['symbol'][:-4] in allowlist)
        ]
        usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        result = [t['symbol'] for t in usdt_pairs[:limit]]
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        _activate_circuit_breaker(f"Binance API get_ticker failed ({type(e).__name__}: {e})")
        return get_tradeable_symbols(limit=limit)

def get_current_prices(symbols):
    client = get_sync_client()
    if _is_mock_mode_active() or client is None:
        mock_prices = {
            "BTCUSDT": 95230.15,
            "ETHUSDT": 3120.45,
            "BNBUSDT": 652.80,
            "SOLUSDT": 188.90,
            "ADAUSDT": 0.68,
            "XRPUSDT": 1.78,
            "DOTUSDT": 6.42,
            "LTCUSDT": 89.60,
            "DOGEUSDT": 0.34,
            "AVAXUSDT": 31.85,
            "LINKUSDT": 17.95,
            "SHIBUSDT": 0.0000245,
            "UNIUSDT": 11.25,
            "ATOMUSDT": 8.12,
            "SUIUSDT": 3.05,
            "PEPEUSDT": 0.0000142,
            "WIFUSDT": 3.15,
            "FLOKIUSDT": 0.000175,
            "BONKUSDT": 0.0000272,
            "HYPEUSDT": 14.85
        }
        import random
        return {s: mock_prices.get(s, random.uniform(1.0, 50.0)) for s in symbols}
    try:
        res = client.get_symbol_ticker(symbols=json.dumps(symbols, separators=(',', ':')))
        if isinstance(res, list):
            return {item['symbol']: float(item['price']) for item in res}
        elif isinstance(res, dict):
            return {res['symbol']: float(res['price'])}
        return {}
    except Exception:
        try:
            prices = client.get_all_tickers()
            prices_map = {p['symbol']: float(p['price']) for p in prices}
            return {s: prices_map[s] for s in symbols if s in prices_map}
        except Exception as e2:
            _activate_circuit_breaker(f"Binance API get_current_prices failed ({type(e2).__name__}: {e2})")
            return get_current_prices(symbols)

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
    if period == 0: return 50.0
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

async def fetch_all_market_data(symbols, max_retries=3):
    import random
    # Check cache first
    cache_key = f"market_data_{hash(tuple(sorted(symbols)))}"
    cached = _cache_get(cache_key, MARKET_DATA_CACHE_TTL)
    if cached is not None:
        return cached

    if _is_mock_mode_active():
        mock_data = {
            s: {"rsi": random.uniform(30.0, 70.0), "variance": random.uniform(0.01, 0.15), "macd": 0.0, "signal": 0.0}
            for s in symbols
        }
        _cache_set(cache_key, mock_data)
        return mock_data

    client = None
    try:
        client = await AsyncClient.create(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)
    except Exception as e:
        _activate_circuit_breaker(f"Binance AsyncClient creation failed ({type(e).__name__}: {e})")
        return await fetch_all_market_data(symbols)

    sem = asyncio.Semaphore(15)

    async def fetch_with_semaphore(symbol):
        for attempt in range(max_retries):
            try:
                async with sem:
                    klines = await asyncio.wait_for(
                        client.get_klines(
                            symbol=symbol,
                            interval=AsyncClient.KLINE_INTERVAL_4HOUR,
                            limit=360  # ~60 days of 4h klines
                        ),
                        timeout=5.0
                    )
                    return symbol, klines
            except Exception as e:
                if attempt == max_retries - 1:
                    _activate_circuit_breaker(f"Binance API kline fetch failed for {symbol} after {max_retries} attempts ({type(e).__name__}: {e})")
                    return symbol, None
                await asyncio.sleep(1)

    try:
        tasks = [fetch_with_semaphore(s) for s in symbols]
        results = await asyncio.gather(*tasks)
        
        data_map = {}
        for symbol, klines in results:
            closes = [float(k[4]) for k in klines] if klines else []
            if not closes:
                data_map[symbol] = {"variance": 0.0, "rsi": 50.0, "macd": 0.0, "signal": 0.0}
                continue
            
            closes_30d = closes[-180:] if len(closes) >= 180 else closes
            variance = 0.0
            if len(closes_30d) >= 2:
                returns = [(closes_30d[i] - closes_30d[i-1]) / closes_30d[i-1] for i in range(1, len(closes_30d)) if closes_30d[i-1] > 0]
                if returns:
                    mean = sum(returns) / len(returns)
                    variance = math.sqrt(sum((r - mean) ** 2 for r in returns) / len(returns))
                    
            rsi = calculate_rsi(closes)
            macd, signal = calculate_macd(closes)
            data_map[symbol] = {"variance": variance, "rsi": rsi, "macd": macd, "signal": signal}
        
        _cache_set(cache_key, data_map)
        return data_map
    except Exception as e:
        _activate_circuit_breaker(f"Binance API fetch_all_market_data gather failed ({type(e).__name__}: {e})")
        return await fetch_all_market_data(symbols)
    finally:
        if client:
            await client.close_connection()
