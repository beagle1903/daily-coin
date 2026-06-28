import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from binance_client import (
    calculate_rsi, 
    calculate_macd, 
    fetch_all_market_data, 
    get_sync_client, 
    get_current_prices, 
    get_tradeable_symbols
)

def test_calculate_rsi_short_list():
    closes = [100.0] * 10
    assert calculate_rsi(closes) == 50.0

def test_calculate_rsi_all_gains():
    closes = [float(i) for i in range(20)]
    assert calculate_rsi(closes) == 100.0

def test_calculate_rsi_all_losses():
    closes = [float(100 - i) for i in range(20)]
    assert calculate_rsi(closes) == 0.0

def test_calculate_macd_short_list():
    closes = [100.0] * 30
    macd, signal = calculate_macd(closes)
    assert macd == 0.0
    assert signal == 0.0

def test_calculate_macd_sufficient_data():
    closes = [100.0] * 50
    macd, signal = calculate_macd(closes)
    assert macd == 0.0
    assert signal == 0.0

def test_get_sync_client_mock_mode():
    with patch("binance_client.USE_MOCK_DATA", True):
        assert get_sync_client() is None

def test_get_current_prices_mock_mode():
    with patch("binance_client.USE_MOCK_DATA", True):
        prices = get_current_prices(["BTCUSDT"])
        assert "BTCUSDT" in prices
        assert prices["BTCUSDT"] == 95230.15

def test_get_tradeable_symbols_mock_mode():
    with patch("binance_client.USE_MOCK_DATA", True):
        symbols = get_tradeable_symbols(limit=5)
        assert len(symbols) == 5
        assert "BTCUSDT" in symbols

def test_fetch_all_market_data_mock_mode():
    with patch("binance_client.USE_MOCK_DATA", True):
        res = asyncio.run(fetch_all_market_data(["BTCUSDT", "ETHUSDT"]))
        assert "BTCUSDT" in res
        assert "ETHUSDT" in res
        assert "variance" in res["BTCUSDT"]
        assert "rsi" in res["BTCUSDT"]
        assert "macd" in res["BTCUSDT"]
        assert "signal" in res["BTCUSDT"]

def test_fetch_all_market_data_real_api_mocked():
    # Generates 60 candles with slightly increasing prices to avoid 0 variance
    mock_klines = [
        ["123", "1.0", "1.0", "1.0", str(100.0 + i), "1.0", "123", "1.0", 1, "1.0", "1.0", "1.0"]
        for i in range(60)
    ]
    
    mock_async_client = AsyncMock()
    mock_async_client.get_historical_klines = AsyncMock(return_value=mock_klines)
    
    with patch("binance_client.USE_MOCK_DATA", False), \
         patch("binance_client.AsyncClient.create", AsyncMock(return_value=mock_async_client)):
         
        res = asyncio.run(fetch_all_market_data(["BTCUSDT"]))
        
        assert "BTCUSDT" in res
        assert res["BTCUSDT"]["variance"] > 0
        assert 0 <= res["BTCUSDT"]["rsi"] <= 100
        mock_async_client.get_historical_klines.assert_called_once()
        mock_async_client.close_connection.assert_called_once()
