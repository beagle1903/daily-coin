import asyncio
from unittest.mock import AsyncMock, patch

from constants import MIN_EVALUATION_AGE_SECONDS
from portfolio_service import generate_portfolio

EXPLANATION_KEYS = {
    "summary",
    "base",
    "history_adjustment",
    "news_adjustment",
    "news_headline",
    "news_sentiment",
    "rsi",
    "rsi_adjustment",
    "macd",
    "signal",
    "macd_adjustment",
    "score",
    "bucket_size",
    "bucket_rank",
    "bucket_avg_score",
}


def test_generate_portfolio_attaches_explanation():
    market_data = {
        "BTCUSDT": {"variance": 0.01, "rsi": 25.0, "macd": 0.1, "signal": 0.0},
        "ETHUSDT": {"variance": 0.02, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "SOLUSDT": {"variance": 0.10, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "XRPUSDT": {"variance": 0.12, "rsi": 40.0, "macd": 0.0, "signal": 0.05},
    }
    prices = {symbol: 1.0 for symbol in market_data}
    symbols = list(market_data.keys())

    with patch("portfolio_service.load_history", return_value=[]), \
         patch("portfolio_service.get_unevaluated_records", return_value=[]), \
         patch("portfolio_service.get_tradeable_symbols", return_value=symbols), \
         patch("portfolio_service.get_latest_news", AsyncMock(return_value=[])), \
         patch("portfolio_service.fetch_all_market_data", AsyncMock(return_value=market_data)), \
         patch("portfolio_service.analyze_news_impact", return_value=[]), \
         patch("portfolio_service.get_current_prices", return_value=prices), \
         patch("portfolio_service.add_portfolio_record"):
        result = asyncio.run(
            generate_portfolio(stable_count=1, volatile_count=1, variance_percentile=50.0)
        )

    assert "error" not in result
    assert len(result["portfolio"]) == 2
    for item in result["portfolio"]:
        assert "explanation" in item
        explanation = item["explanation"]
        assert EXPLANATION_KEYS <= set(explanation.keys())
        assert explanation["summary"]
        assert item["score"] == explanation["score"]
        assert item["type"] in ("Stable", "Volatile")
        assert explanation["bucket_size"] >= 1
        assert explanation["bucket_rank"] >= 1


def _use_history_file(monkeypatch, path, records):
    import json

    from history import JsonHistoryRepository

    path.write_text(json.dumps(records))
    monkeypatch.setattr("history._default_repo", JsonHistoryRepository(str(path)))


def _pending_record():
    import time

    return {
        "timestamp": time.time() - 2 * MIN_EVALUATION_AGE_SECONDS,
        "portfolio": ["BTCUSDT", "ETHUSDT"],
        "entry_prices": {"BTCUSDT": 50000.0, "ETHUSDT": 2000.0},
        "evaluated": False,
    }


def test_mock_run_leaves_history_untouched(tmp_path, monkeypatch):
    import json

    import binance_client

    history_file = tmp_path / "history.json"
    _use_history_file(monkeypatch, history_file, [_pending_record()])
    before = history_file.read_text()

    with patch.dict(binance_client._cache, {}, clear=True), \
         patch("binance_client._is_mock_mode_active", return_value=True), \
         patch("portfolio_service.get_latest_news", AsyncMock(return_value=[])):
        result = asyncio.run(generate_portfolio(stable_count=2, volatile_count=3))

    assert "error" not in result
    assert result["mock"] is True
    assert result["portfolio"]
    assert result["evaluation_results"] == []
    assert history_file.read_text() == before
    assert json.loads(before)[0]["evaluated"] is False


def test_real_run_evaluates_and_saves_history(tmp_path, monkeypatch):
    import json

    market_data = {
        "BTCUSDT": {"variance": 0.01, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "ETHUSDT": {"variance": 0.10, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
    }
    prices = {"BTCUSDT": 55000.0, "ETHUSDT": 1900.0}
    history_file = tmp_path / "history.json"
    _use_history_file(monkeypatch, history_file, [_pending_record()])

    with patch("portfolio_service.get_tradeable_symbols", return_value=list(market_data)), \
         patch("portfolio_service.get_latest_news", AsyncMock(return_value=[])), \
         patch("portfolio_service.fetch_all_market_data", AsyncMock(return_value=market_data)), \
         patch("portfolio_service.get_current_prices", return_value=prices):
        result = asyncio.run(
            generate_portfolio(stable_count=1, volatile_count=1, variance_percentile=50.0)
        )

    assert result["mock"] is False
    assert len(result["evaluation_results"]) == 1
    saved = json.loads(history_file.read_text())
    assert len(saved) == 2
    assert saved[0]["evaluated"] is True
    assert saved[1]["evaluated"] is False


def test_mock_fallback_after_evaluation_skips_new_record(tmp_path, monkeypatch):
    """Real prices at evaluation time, mock fallback later: keep the evaluation, save no new pick."""
    import json

    import binance_client

    market_data = {
        "BTCUSDT": {"variance": 0.01, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "ETHUSDT": {"variance": 0.10, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
    }
    history_file = tmp_path / "history.json"
    _use_history_file(monkeypatch, history_file, [_pending_record()])
    calls = {"n": 0}

    def prices_then_mock(symbols):
        calls["n"] += 1
        if calls["n"] > 1:
            binance_client._note_mock_served()
        return {s: 100.0 for s in symbols}

    with patch("portfolio_service.get_tradeable_symbols", return_value=list(market_data)), \
         patch("portfolio_service.get_latest_news", AsyncMock(return_value=[])), \
         patch("portfolio_service.fetch_all_market_data", AsyncMock(return_value=market_data)), \
         patch("portfolio_service.get_current_prices", side_effect=prices_then_mock):
        result = asyncio.run(
            generate_portfolio(stable_count=1, volatile_count=1, variance_percentile=50.0)
        )

    assert result["mock"] is True
    assert len(result["evaluation_results"]) == 1
    saved = json.loads(history_file.read_text())
    assert len(saved) == 1
    assert saved[0]["evaluated"] is True


def test_partial_kline_failure_keeps_run_real(tmp_path, monkeypatch):
    """One symbol without klines: it is not picked, the rest use real data and prices."""
    import json

    import binance_client

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
    real_prices = {s: 10.0 * (i + 1) for i, s in enumerate(symbols)}

    async def get_klines(symbol, interval, limit):
        if symbol == "ADAUSDT":
            raise RuntimeError("klines unavailable")
        step = 1.0 + symbols.index(symbol)
        return [[0, "1", "1", "1", str(100.0 + step * (i % 7)), "1"] for i in range(60)]

    async_client = AsyncMock()
    async_client.get_klines = AsyncMock(side_effect=get_klines)

    class FakeSyncClient:
        def get_symbol_ticker(self, symbols=None, symbol=None):
            return [{"symbol": s, "price": str(real_prices[s])} for s in json.loads(symbols)]

    monkeypatch.delenv("OFFLINE_MOCK", raising=False)
    monkeypatch.setattr(binance_client, "MOCK_DATA_UNTIL", 0)
    history_file = tmp_path / "history.json"
    _use_history_file(monkeypatch, history_file, [])

    with patch.dict(binance_client._cache, {}, clear=True), \
         patch("portfolio_service.get_tradeable_symbols", return_value=symbols), \
         patch("portfolio_service.get_latest_news", AsyncMock(return_value=[])), \
         patch("binance_client.AsyncClient.create", AsyncMock(return_value=async_client)), \
         patch("binance_client.get_sync_client", return_value=FakeSyncClient()), \
         patch("binance_client.asyncio.sleep", AsyncMock()):
        result = asyncio.run(
            generate_portfolio(stable_count=2, volatile_count=2, variance_percentile=50.0)
        )
        assert binance_client._is_mock_mode_active() is False

    assert "error" not in result
    assert result["mock"] is False
    picked = {item["coin"] for item in result["portfolio"]}
    assert picked == {"BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"}
    for item in result["portfolio"]:
        assert item["price"] == real_prices[item["coin"]]
        assert item["variance"] > 0
    saved = json.loads(history_file.read_text())
    assert len(saved) == 1
    assert "ADAUSDT" not in saved[0]["portfolio"]


TWO_COIN_MARKET = {
    "BTCUSDT": {"variance": 0.01, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
    "ETHUSDT": {"variance": 0.10, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
}


def _run_two_coin_pipeline(prices):
    with patch("portfolio_service.get_tradeable_symbols", return_value=list(TWO_COIN_MARKET)), \
         patch("portfolio_service.get_latest_news", AsyncMock(return_value=[])), \
         patch("portfolio_service.fetch_all_market_data", AsyncMock(return_value=TWO_COIN_MARKET)), \
         patch("portfolio_service.get_current_prices", return_value=prices):
        return asyncio.run(
            generate_portfolio(stable_count=1, volatile_count=1, variance_percentile=50.0)
        )


def test_young_records_are_left_pending(tmp_path, monkeypatch):
    """A record under the minimum holding time is not evaluated; an older one is."""
    import json
    import time

    young = dict(_pending_record(), timestamp=time.time() - 60)
    history_file = tmp_path / "history.json"
    _use_history_file(monkeypatch, history_file, [_pending_record(), young])

    result = _run_two_coin_pipeline({"BTCUSDT": 55000.0, "ETHUSDT": 1900.0})

    assert len(result["evaluation_results"]) == 1
    assert result["held_evaluations"] == 1
    saved = json.loads(history_file.read_text())
    assert [r["evaluated"] for r in saved] == [True, False, False]
    assert "performance" not in saved[1]


def test_only_young_records_means_no_evaluation(tmp_path, monkeypatch):
    import json
    import time

    young = dict(_pending_record(), timestamp=time.time() - 60)
    history_file = tmp_path / "history.json"
    _use_history_file(monkeypatch, history_file, [young])

    result = _run_two_coin_pipeline({"BTCUSDT": 1.0, "ETHUSDT": 2.0})

    assert result["evaluation_results"] == []
    assert result["held_evaluations"] == 1
    saved = json.loads(history_file.read_text())
    assert [r["evaluated"] for r in saved] == [False, False]


def test_new_record_stores_picks_for_the_dashboard(tmp_path, monkeypatch):
    import json

    history_file = tmp_path / "history.json"
    _use_history_file(monkeypatch, history_file, [])

    result = _run_two_coin_pipeline({"BTCUSDT": 1.0, "ETHUSDT": 2.0})

    saved = json.loads(history_file.read_text())
    assert saved[-1]["picks"] == result["portfolio"]
    assert saved[-1]["picks"][0]["explanation"]["summary"]


def test_fill_bucket_replaces_unpriced_pick_with_best_scoring_candidate():
    from portfolio_service import _fill_bucket

    scores = {"A": 20.0, "B": 15.0, "C": 12.0, "D": 18.0}
    prices = {"A": 0.0, "B": 1.0, "C": 1.0, "D": 0.0}

    # A has no price; D scores higher than B and C but has no price either
    assert _fill_bucket(["A", "C"], ["A", "B", "C", "D"], 2, prices, scores) == ["B", "C"]


def test_fill_bucket_keeps_priced_picks_and_sorts_by_score():
    from portfolio_service import _fill_bucket

    scores = {"A": 5.0, "B": 9.0, "C": 7.0}
    prices = {"A": 1.0, "B": 1.0, "C": 1.0}

    assert _fill_bucket(["A", "B"], ["A", "B", "C"], 2, prices, scores) == ["B", "A"]
    assert _fill_bucket(["A"], ["A", "B", "C"], 5, prices, scores) == ["B", "C", "A"]


def test_unpriced_pick_is_replaced_in_the_pipeline(tmp_path, monkeypatch):
    """A sampled coin with no price is swapped for another candidate from the same bucket."""
    history_file = tmp_path / "history.json"
    _use_history_file(monkeypatch, history_file, [])
    market = {
        "BTCUSDT": {"variance": 0.01, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "ETHUSDT": {"variance": 0.02, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "SOLUSDT": {"variance": 0.10, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "XRPUSDT": {"variance": 0.12, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
    }
    prices = {"BTCUSDT": 0.0, "ETHUSDT": 3000.0, "SOLUSDT": 150.0, "XRPUSDT": 1.5}

    with patch("portfolio_service.get_tradeable_symbols", return_value=list(market)), \
         patch("portfolio_service.get_latest_news", AsyncMock(return_value=[])), \
         patch("portfolio_service.fetch_all_market_data", AsyncMock(return_value=market)), \
         patch("portfolio_service.get_current_prices", side_effect=lambda symbols: {s: prices[s] for s in symbols}), \
         patch("portfolio_service.pick_portfolio", return_value=(["BTCUSDT"], ["SOLUSDT"])):
        result = asyncio.run(
            generate_portfolio(stable_count=1, volatile_count=1, variance_percentile=50.0)
        )

    by_type = {item["type"]: item["coin"] for item in result["portfolio"]}
    assert by_type == {"Stable": "ETHUSDT", "Volatile": "SOLUSDT"}
    assert all(item["price"] > 0 for item in result["portfolio"])
