import math
import asyncio
import os
import sys
from binance.client import Client
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from config import BINANCE_API_KEY, BINANCE_API_SECRET

client = None
USE_MOCK_DATA = os.environ.get("OFFLINE_MOCK", "").lower() in ("true", "1")

if not USE_MOCK_DATA:
    try:
        # Set a short timeout for the initial ping to avoid long hangs
        client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, requests_params={'timeout': 5})
    except Exception as e:
        print("Warning: Binance API connection failed. Falling back to Offline Mock Mode.", file=sys.stderr)
        USE_MOCK_DATA = True

def get_tradeable_symbols(limit=30):
    if USE_MOCK_DATA or client is None:
        return [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", 
            "XRPUSDT", "DOTUSDT", "LTCUSDT", "DOGEUSDT", "AVAXUSDT", 
            "LINKUSDT", "SHIBUSDT", "UNIUSDT", "ATOMUSDT", "SUIUSDT", 
            "PEPEUSDT", "WIFUSDT", "FLOKIUSDT", "BONKUSDT", "HYPEUSDT"
        ][:limit]
    try:
        tickers = client.get_ticker()
        usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
        usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        return [t['symbol'] for t in usdt_pairs[:limit]]
    except Exception:
        return []

def get_current_prices(symbols):
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

async def get_30d_variance_async(async_client, symbol):
    klines = await fetch_with_retry(async_client, symbol, 30)
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

async def get_technical_indicators_async(async_client, symbol):
    klines = await fetch_with_retry(async_client, symbol, 60)
    closes = [float(k[4]) for k in klines]
    if not closes:
        return {"rsi": 50.0, "macd": 0.0, "signal": 0.0}
    rsi = calculate_rsi(closes)
    macd, signal = calculate_macd(closes)
    return {"rsi": rsi, "macd": macd, "signal": signal}

async def fetch_all_variances(symbols):
    if USE_MOCK_DATA:
        import random
        res = {}
        for s in symbols:
            if s in ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "DOTUSDT", "LTCUSDT", "ATOMUSDT"]:
                res[s] = random.uniform(0.01, 0.03)
            else:
                res[s] = random.uniform(0.04, 0.10)
        return res
    async_client = await AsyncClient.create(BINANCE_API_KEY, BINANCE_API_SECRET)
    try:
        tasks = [get_30d_variance_async(async_client, s) for s in symbols]
        results = await asyncio.gather(*tasks)
        return dict(zip(symbols, results))
    finally:
        await async_client.close_connection()

async def fetch_all_technical_indicators(symbols):
    if USE_MOCK_DATA:
        import random
        res = {}
        for s in symbols:
            res[s] = {
                "rsi": random.uniform(25.0, 75.0),
                "macd": random.uniform(-1.0, 1.0),
                "signal": random.uniform(-1.0, 1.0)
            }
        return res
    async_client = await AsyncClient.create(BINANCE_API_KEY, BINANCE_API_SECRET)
    try:
        tasks = [get_technical_indicators_async(async_client, s) for s in symbols]
        results = await asyncio.gather(*tasks)
        return dict(zip(symbols, results))
    finally:
        await async_client.close_connection()
