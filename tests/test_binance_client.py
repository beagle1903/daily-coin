import asyncio
from unittest.mock import AsyncMock, patch

from binance_client import (
    calculate_macd,
    calculate_rsi,
    fetch_all_market_data,
    get_current_prices,
    get_sync_client,
    get_tradeable_symbols,
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
    with patch("binance_client._is_mock_mode_active", return_value=True):
        assert get_sync_client() is None

def test_get_current_prices_targeted_fallback_when_batch_fails():
    class FakeClient:
        def get_symbol_ticker(self, symbols=None, symbol=None):
            if symbols is not None:
                raise RuntimeError("batch ticker failed")
            return {"symbol": symbol, "price": "101.5"}

    with patch("binance_client._is_mock_mode_active", return_value=False), \
         patch("binance_client.get_sync_client", return_value=FakeClient()), \
         patch("binance_client.logging.warning") as warn:
        prices = get_current_prices(["BTCUSDT"])
        assert prices == {"BTCUSDT": 101.5}
        warn.assert_called_once()
        assert "batch" in warn.call_args[0][0].lower()


def test_get_current_prices_mock_mode():
    with patch("binance_client._is_mock_mode_active", return_value=True):
        prices = get_current_prices(["BTCUSDT"])
        assert "BTCUSDT" in prices
        assert prices["BTCUSDT"] == 95230.15

def test_get_tradeable_symbols_mock_mode():
    with patch("binance_client._is_mock_mode_active", return_value=True):
        symbols = get_tradeable_symbols(limit=5)
        assert len(symbols) == 5
        assert "BTCUSDT" in symbols

def test_fetch_all_market_data_mock_mode():
    with patch("binance_client._is_mock_mode_active", return_value=True):
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
    mock_async_client.get_klines = AsyncMock(return_value=mock_klines)
    
    with patch("binance_client._is_mock_mode_active", return_value=False), \
         patch("binance_client.AsyncClient.create", AsyncMock(return_value=mock_async_client)):
         
        res = asyncio.run(fetch_all_market_data(["BTCUSDT"]))
        
        assert "BTCUSDT" in res
        assert res["BTCUSDT"]["variance"] > 0
        assert 0 <= res["BTCUSDT"]["rsi"] <= 100
        mock_async_client.get_klines.assert_called_once()
        mock_async_client.close_connection.assert_called_once()


def _fake_ticker_client():
    class FakeClient:
        def get_ticker(self):
            return [
                {"symbol": "BTCUSDT", "quoteVolume": "300"},
                {"symbol": "ETHUSDT", "quoteVolume": "200"},
                {"symbol": "SOLUSDT", "quoteVolume": "100"},
            ]

    return FakeClient()


def test_mock_symbols_are_not_cached_after_recovery():
    import binance_client

    with patch.dict(binance_client._cache, {}, clear=True):
        with patch("binance_client._is_mock_mode_active", return_value=True):
            mock_symbols = get_tradeable_symbols(limit=3)
        assert binance_client._cache == {}

        with patch("binance_client._is_mock_mode_active", return_value=False), \
             patch("binance_client.get_sync_client", return_value=_fake_ticker_client()), \
             patch("binance_client.load_midas_allowlist", return_value=None):
            real_symbols = get_tradeable_symbols(limit=3)

        assert mock_symbols == ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        assert real_symbols == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        assert binance_client._cache["tradeable_symbols_3"][0] == real_symbols


def test_mock_market_data_is_not_cached():
    import binance_client

    with patch.dict(binance_client._cache, {}, clear=True), \
         patch("binance_client._is_mock_mode_active", return_value=True):
        asyncio.run(fetch_all_market_data(["BTCUSDT"]))
        assert binance_client._cache == {}


def test_mock_serve_count_tracks_only_mock_fallbacks():
    import binance_client

    with patch.dict(binance_client._cache, {}, clear=True):
        before = binance_client.mock_serve_count()
        with patch("binance_client._is_mock_mode_active", return_value=True):
            get_tradeable_symbols(limit=3)
            get_current_prices(["BTCUSDT"])
            asyncio.run(fetch_all_market_data(["BTCUSDT"]))
        assert binance_client.mock_serve_count() == before + 3

        with patch("binance_client._is_mock_mode_active", return_value=False), \
             patch("binance_client.get_sync_client", return_value=_fake_ticker_client()), \
             patch("binance_client.load_midas_allowlist", return_value=None):
            get_tradeable_symbols(limit=3)
        assert binance_client.mock_serve_count() == before + 3


def _klines(n=60, start=100.0):
    return [
        ["123", "1.0", "1.0", "1.0", str(start + i), "1.0", "123", "1.0", 1, "1.0", "1.0", "1.0"]
        for i in range(n)
    ]


def _kline_client(failing=(), empty=()):
    async def get_klines(symbol, interval, limit):
        if symbol in failing:
            raise RuntimeError(f"no klines for {symbol}")
        if symbol in empty:
            return []
        return _klines()

    client = AsyncMock()
    client.get_klines = AsyncMock(side_effect=get_klines)
    return client


def _live_binance(monkeypatch):
    """Real mock-mode logic with the breaker reset; restored after the test."""
    import binance_client

    monkeypatch.delenv("OFFLINE_MOCK", raising=False)
    monkeypatch.setattr(binance_client, "MOCK_DATA_UNTIL", 0)
    return binance_client


def test_partial_kline_failure_skips_symbol_without_tripping_breaker(monkeypatch):
    binance_client = _live_binance(monkeypatch)
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "NEWUSDT"]
    client = _kline_client(failing={"SOLUSDT"}, empty={"NEWUSDT"})
    mock_count = binance_client.mock_serve_count()

    with patch.dict(binance_client._cache, {}, clear=True), \
         patch("binance_client.AsyncClient.create", AsyncMock(return_value=client)), \
         patch("binance_client.asyncio.sleep", AsyncMock()), \
         patch("binance_client.logging.warning") as warn:
        res = asyncio.run(fetch_all_market_data(symbols))

    assert set(res) == {"BTCUSDT", "ETHUSDT"}
    assert all(item["variance"] > 0 for item in res.values())
    assert binance_client._is_mock_mode_active() is False
    assert binance_client.mock_serve_count() == mock_count
    logged = [call.args for call in warn.call_args_list]
    assert any("SOLUSDT" in args for args in logged)


def test_broad_kline_failure_trips_breaker_and_serves_mock(monkeypatch):
    binance_client = _live_binance(monkeypatch)
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    client = _kline_client(failing={"BTCUSDT", "ETHUSDT"})
    mock_count = binance_client.mock_serve_count()

    with patch.dict(binance_client._cache, {}, clear=True), \
         patch("binance_client.AsyncClient.create", AsyncMock(return_value=client)), \
         patch("binance_client.asyncio.sleep", AsyncMock()):
        res = asyncio.run(fetch_all_market_data(symbols))
        assert binance_client._cache == {}

    assert set(res) == set(symbols)
    assert binance_client._is_mock_mode_active() is True
    assert binance_client.mock_serve_count() == mock_count + 1
    client.close_connection.assert_called_once()
