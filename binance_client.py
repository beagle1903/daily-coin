import math
import asyncio
import os
import sys
import json
from binance.client import Client
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from config import BINANCE_API_KEY, BINANCE_API_SECRET

_client = None
USE_MOCK_DATA = os.environ.get("OFFLINE_MOCK", "").lower() in ("true", "1")

def get_sync_client():
    global _client, USE_MOCK_DATA
    if USE_MOCK_DATA:
        return None
    if _client is not None:
        return _client
    try:
        # Set a short timeout for the initial ping to avoid long hangs
        _client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, requests_params={'timeout': 5})
        return _client
    except Exception:
        print("Warning: Binance API connection failed. Falling back to Offline Mock Mode.", file=sys.stderr)
        USE_MOCK_DATA = True
        return None

def get_tradeable_symbols(limit=30):
    client = get_sync_client()
    if USE_MOCK_DATA or client is None:
        return [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", 
            "XRPUSDT", "DOTUSDT", "LTCUSDT", "DOGEUSDT", "AVAXUSDT", 
            "LINKUSDT", "SHIBUSDT", "UNIUSDT", "ATOMUSDT", "SUIUSDT", 
            "PEPEUSDT", "WIFUSDT", "FLOKIUSDT", "BONKUSDT", "HYPEUSDT"
        ][:limit]
    try:
        tickers = client.get_ticker()
        excluded_bases = {"USDC", "FDUSD", "TUSD", "BUSD", "USD1", "EUR", "DAI", "USDD", "PYUSD", "USDP", "AEUR"}
        usdt_pairs = [
            t for t in tickers 
            if t['symbol'].endswith('USDT') and t['symbol'][:-4] not in excluded_bases
        ]
        usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        return [t['symbol'] for t in usdt_pairs[:limit]]
    except Exception:
        return []

def get_current_prices(symbols):
    client = get_sync_client()
    if USE_MOCK_DATA or client is None:
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
        except Exception:
            return {}

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

async def fetch_with_retry(async_client, symbol, days):
    retries = 3
    for i in range(retries):
        try:
            return await async_client.get_historical_klines(symbol, AsyncClient.KLINE_INTERVAL_4HOUR, f"{days} days ago UTC")
        except BinanceAPIException as e:
            if e.status_code == 429 and i < retries - 1:
                await asyncio.sleep(2 ** i)
                continue
            return []
        except Exception:
            return []
    return []

async def fetch_historical_data_async(async_client, symbol, semaphore):
    async with semaphore:
        klines = await fetch_with_retry(async_client, symbol, 60)
        return symbol, klines

def _get_mock_market_data(symbols):
    import random
    res = {}
    for s in symbols:
        if s in ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "DOTUSDT", "LTCUSDT", "ATOMUSDT"]:
            var_val = random.uniform(0.01, 0.03)
        else:
            var_val = random.uniform(0.04, 0.10)
        res[s] = {
            "variance": var_val,
            "rsi": random.uniform(25.0, 75.0),
            "macd": random.uniform(-1.0, 1.0),
            "signal": random.uniform(-1.0, 1.0)
        }
    return res

async def fetch_all_market_data(symbols):
    global USE_MOCK_DATA
    if USE_MOCK_DATA:
        return _get_mock_market_data(symbols)
    try:
        async_client = await AsyncClient.create(BINANCE_API_KEY, BINANCE_API_SECRET)
    except Exception:
        print("Warning: Binance AsyncClient connection failed. Falling back to Offline Mock Mode.", file=sys.stderr)
        USE_MOCK_DATA = True
        return _get_mock_market_data(symbols)
    try:
        semaphore = asyncio.Semaphore(15)
        tasks = [fetch_historical_data_async(async_client, s, semaphore) for s in symbols]
        results = await asyncio.gather(*tasks)
        
        data_map = {}
        for symbol, klines in results:
            closes = [float(k[4]) for k in klines] if klines else []
            if not closes:
                data_map[symbol] = {
                    "variance": 0.0,
                    "rsi": 50.0,
                    "macd": 0.0,
                    "signal": 0.0
                }
                continue
            
            # Calculate 30-day variance (using last 180 candles of 4h interval)
            closes_30d = closes[-180:] if len(closes) >= 180 else closes
            variance = 0.0
            if len(closes_30d) >= 2:
                returns = []
                for i in range(1, len(closes_30d)):
                    prev = closes_30d[i-1]
                    curr = closes_30d[i]
                    if prev > 0:
                        returns.append((curr - prev) / prev)
                if returns:
                    mean_return = sum(returns) / len(returns)
                    var_val = sum((r - mean_return) ** 2 for r in returns) / len(returns)
                    variance = math.sqrt(var_val)
                    
            rsi = calculate_rsi(closes)
            macd, signal = calculate_macd(closes)
            data_map[symbol] = {
                "variance": variance,
                "rsi": rsi,
                "macd": macd,
                "signal": signal
            }
        return data_map
    finally:
        await async_client.close_connection()
