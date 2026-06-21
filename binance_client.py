import math
import asyncio
from binance.client import Client
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from config import BINANCE_API_KEY, BINANCE_API_SECRET

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

def get_tradeable_symbols(limit=30):
    try:
        tickers = client.get_ticker()
        usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
        usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        return [t['symbol'] for t in usdt_pairs[:limit]]
    except Exception:
        return []

def get_current_prices(symbols):
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
    async_client = await AsyncClient.create(BINANCE_API_KEY, BINANCE_API_SECRET)
    try:
        tasks = [get_30d_variance_async(async_client, s) for s in symbols]
        results = await asyncio.gather(*tasks)
        return dict(zip(symbols, results))
    finally:
        await async_client.close_connection()

async def fetch_all_technical_indicators(symbols):
    async_client = await AsyncClient.create(BINANCE_API_KEY, BINANCE_API_SECRET)
    try:
        tasks = [get_technical_indicators_async(async_client, s) for s in symbols]
        results = await asyncio.gather(*tasks)
        return dict(zip(symbols, results))
    finally:
        await async_client.close_connection()
