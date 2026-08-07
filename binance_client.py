import asyncio
import json
import math
import os
import sys
import logging
import time as _time

import numpy as np

from binance import AsyncClient
from binance.client import Client
from binance.exceptions import BinanceAPIException

from config import BINANCE_API_KEY, BINANCE_API_SECRET
from constants import (
    SEMAPHORE_LIMIT, SYMBOLS_CACHE_TTL, MARKET_DATA_CACHE_TTL,
    MOCK_CIRCUIT_BREAKER_SECONDS, RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL
)

_client = None
MOCK_DATA_UNTIL = 0

def _is_mock_mode_active():
    if os.environ.get("OFFLINE_MOCK", "").lower() in ("true", "1"):
        return True
    return _time.time() < MOCK_DATA_UNTIL

def _activate_circuit_breaker(err_msg):
    global MOCK_DATA_UNTIL
    logging.warning(f"{err_msg}. Activating Offline Mock Mode for {MOCK_CIRCUIT_BREAKER_SECONDS} seconds.")
    MOCK_DATA_UNTIL = _time.time() + MOCK_CIRCUIT_BREAKER_SECONDS

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

def _get_mock_tradeable_symbols(allowlist, limit):
    mock_symbols = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", 
        "XRPUSDT", "DOTUSDT", "LTCUSDT", "DOGEUSDT", "AVAXUSDT", 
        "LINKUSDT", "SHIBUSDT", "UNIUSDT", "ATOMUSDT", "SUIUSDT", 
        "PEPEUSDT", "WIFUSDT", "FLOKIUSDT", "BONKUSDT", "HYPEUSDT"
    ]
    if allowlist is not None:
        mock_symbols = [s for s in mock_symbols if s[:-4] in allowlist]
    return mock_symbols[:limit]

def get_tradeable_symbols(limit=30):
    cache_key = f"tradeable_symbols_{limit}"
    cached = _cache_get(cache_key, SYMBOLS_CACHE_TTL)
    if cached is not None:
        return cached

    allowlist = load_midas_allowlist()
    
    if not _is_mock_mode_active():
        client = get_sync_client()
        if client is not None:
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
                
    result = _get_mock_tradeable_symbols(allowlist, limit)
    _cache_set(cache_key, result)
    return result

def _get_mock_prices(symbols):
    mock_prices = {
        "BTCUSDT": 95230.15, "ETHUSDT": 3120.45, "BNBUSDT": 652.80, "SOLUSDT": 188.90,
        "ADAUSDT": 0.68, "XRPUSDT": 1.78, "DOTUSDT": 6.42, "LTCUSDT": 89.60,
        "DOGEUSDT": 0.34, "AVAXUSDT": 31.85, "LINKUSDT": 17.95, "SHIBUSDT": 0.0000245,
        "UNIUSDT": 11.25, "ATOMUSDT": 8.12, "SUIUSDT": 3.05, "PEPEUSDT": 0.0000142,
        "WIFUSDT": 3.15, "FLOKIUSDT": 0.000175, "BONKUSDT": 0.0000272, "HYPEUSDT": 14.85
    }
    import random
    return {s: mock_prices.get(s, random.uniform(1.0, 50.0)) for s in symbols}

def get_current_prices(symbols):
    if not _is_mock_mode_active():
        client = get_sync_client()
        if client is not None:
            try:
                res = client.get_symbol_ticker(symbols=json.dumps(symbols, separators=(',', ':')))
                if isinstance(res, list):
                    return {item['symbol']: float(item['price']) for item in res}
                elif isinstance(res, dict):
                    return {res['symbol']: float(res['price'])}
                return {}
            except Exception:
                try:
                    # Targeted fallback instead of get_all_tickers()
                    prices = {}
                    for s in symbols:
                        res = client.get_symbol_ticker(symbol=s)
                        prices[s] = float(res['price'])
                    return prices
                except Exception as e2:
                    _activate_circuit_breaker(f"Binance API get_current_prices targeted fallback failed ({type(e2).__name__}: {e2})")

    return _get_mock_prices(symbols)

def calculate_rsi(closes, period=RSI_PERIOD):
    if len(closes) < period + 1:
        return 50.0
    arr = np.array(closes)
    diffs = np.diff(arr)
    gains = np.where(diffs > 0, diffs, 0.0)
    losses = np.where(diffs < 0, -diffs, 0.0)
    
    if period == 0: return 50.0
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    for i in range(period, len(diffs)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def calculate_macd(closes):
    if len(closes) < MACD_SLOW + MACD_SIGNAL:
        return 0.0, 0.0
    
    arr = np.array(closes)
    
    def ema(data, p):
        alpha = 2 / (p + 1)
        res = np.empty_like(data)
        res[0] = data[0]
        for i in range(1, len(data)):
            res[i] = data[i] * alpha + res[i-1] * (1 - alpha)
        return res
        
    ema_fast = ema(arr, MACD_FAST)
    ema_slow = ema(arr, MACD_SLOW)
    macd_series = ema_fast - ema_slow
    
    valid_macd = macd_series[MACD_SLOW-1:]
    if len(valid_macd) < MACD_SIGNAL:
        return 0.0, 0.0
        
    signal_series = ema(valid_macd, MACD_SIGNAL)
    return float(macd_series[-1]), float(signal_series[-1])

async def fetch_all_market_data(symbols, max_retries=3):
    cache_key = f"market_data_{hash(tuple(sorted(symbols)))}"
    cached = _cache_get(cache_key, MARKET_DATA_CACHE_TTL)
    if cached is not None:
        return cached

    def get_mock_data():
        import random
        return {
            s: {"rsi": random.uniform(30.0, 70.0), "variance": random.uniform(0.01, 0.15), "macd": 0.0, "signal": 0.0}
            for s in symbols
        }

    if not _is_mock_mode_active():
        client = None
        try:
            client = await AsyncClient.create(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)
            sem = asyncio.Semaphore(SEMAPHORE_LIMIT)

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
                    arr = np.array(closes_30d)
                    valid_idx = arr[:-1] > 0
                    if np.any(valid_idx):
                        returns = (arr[1:][valid_idx] - arr[:-1][valid_idx]) / arr[:-1][valid_idx]
                        variance = float(np.std(returns))
                        
                rsi = calculate_rsi(closes)
                macd, signal = calculate_macd(closes)
                data_map[symbol] = {"variance": variance, "rsi": rsi, "macd": macd, "signal": signal}
            
            _cache_set(cache_key, data_map)
            return data_map
        except Exception as e:
            _activate_circuit_breaker(f"Binance API fetch_all_market_data gather failed ({type(e).__name__}: {e})")
        finally:
            if client:
                await client.close_connection()

    mock_data = get_mock_data()
    _cache_set(cache_key, mock_data)
    return mock_data
