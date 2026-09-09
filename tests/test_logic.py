import pytest
from logic import load_coin_scores, pick_portfolio, evaluate_performance, compute_bucket_stats

def test_load_coin_scores():
    universe = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    history = [{
        "evaluated": True,
        "performance": {
            "BTCUSDT": 0.05,
            "ETHUSDT": -0.02
        }
    }]
    sentiment_impacts = [
        {"coin": "BTCUSDT", "adjustment": 0.5, "headline": "Bitcoin rallies", "sentiment": "Bullish"}
    ]
    technical_indicators = {
        "BTCUSDT": {"rsi": 25.0, "macd": 0.1, "signal": 0.0},
        "ETHUSDT": {"rsi": 75.0, "macd": -0.1, "signal": 0.0},
        "SOLUSDT": {"rsi": 50.0, "macd": 0.0, "signal": 0.0}
    }

    scores, breakdowns = load_coin_scores(universe, history, sentiment_impacts, technical_indicators)
    assert scores["BTCUSDT"] == 18.5
    assert scores["ETHUSDT"] == 5.0
    assert scores["SOLUSDT"] == 10.0

    btc = breakdowns["BTCUSDT"]
    assert btc["base"] == 10.0
    assert btc["history_adjustment"] == 5.0
    assert btc["news_adjustment"] == 0.5
    assert btc["news_headline"] == "Bitcoin rallies"
    assert btc["news_sentiment"] == "Bullish"
    assert btc["rsi"] == 25.0
    assert btc["rsi_adjustment"] == 2.0
    assert btc["macd"] == 0.1
    assert btc["signal"] == 0.0
    assert btc["macd_adjustment"] == 1.0
    assert btc["score"] == 18.5

    eth = breakdowns["ETHUSDT"]
    assert eth["history_adjustment"] == -2.0
    assert eth["news_adjustment"] == 0.0
    assert eth["news_headline"] is None
    assert eth["news_sentiment"] is None
    assert eth["rsi_adjustment"] == -2.0
    assert eth["macd_adjustment"] == -1.0
    assert eth["score"] == 5.0

    sol = breakdowns["SOLUSDT"]
    assert sol["history_adjustment"] == 0.0
    assert sol["news_adjustment"] == 0.0
    assert sol["rsi_adjustment"] == 0.0
    assert sol["macd_adjustment"] == 0.0
    assert sol["score"] == 10.0

def test_pick_portfolio():
    available_stable = ["USDT", "USDC"]
    available_volatile = ["BTC", "ETH", "SOL"]
    scores = {"USDT": 10.0, "USDC": 10.0, "BTC": 10.0, "ETH": 10.0, "SOL": 10.0}
    
    stable_picks, volatile_picks = pick_portfolio(available_stable, available_volatile, scores, stable_count=1, volatile_count=2)
    assert len(stable_picks) == 1
    assert len(volatile_picks) == 2
    assert stable_picks[0] in available_stable
    assert volatile_picks[0] in available_volatile
    assert volatile_picks[1] in available_volatile

def test_evaluate_performance():
    unevaluated = [
        {
            "timestamp": 123456,
            "portfolio": ["BTCUSDT", "ETHUSDT", "DELISTEDUSDT"],
            "entry_prices": {"BTCUSDT": 100.0, "ETHUSDT": 50.0, "DELISTEDUSDT": 10.0}
        }
    ]
    current_prices = {
        "BTCUSDT": 110.0,
        "ETHUSDT": 45.0,
        "DELISTEDUSDT": 0.0
    }
    history = [
        {
            "timestamp": 123456,
            "portfolio": ["BTCUSDT", "ETHUSDT", "DELISTEDUSDT"],
            "entry_prices": {"BTCUSDT": 100.0, "ETHUSDT": 50.0, "DELISTEDUSDT": 10.0},
            "evaluated": False
        }
    ]
    
    updated_history, results = evaluate_performance(unevaluated, current_prices, history)
    
    assert len(results) == 1
    perf = results[0]["performance"]
    assert perf["BTCUSDT"] == pytest.approx(0.10)
    assert perf["ETHUSDT"] == pytest.approx(-0.10)
    assert perf["DELISTEDUSDT"] == pytest.approx(-1.0)
    
    assert updated_history[0]["evaluated"] is True
    assert updated_history[0]["performance"] == perf

def test_pick_portfolio_empty():
    stable_picks, volatile_picks = pick_portfolio([], [], {}, stable_count=1, volatile_count=2)
    assert len(stable_picks) == 0
    assert len(volatile_picks) == 0


def test_pick_portfolio_empty_stable_only():
    scores = {"BTC": 10.0, "ETH": 8.0}
    stable_picks, volatile_picks = pick_portfolio([], ["BTC", "ETH"], scores, stable_count=1, volatile_count=1)
    assert stable_picks == []
    assert len(volatile_picks) == 1
    assert volatile_picks[0] in {"BTC", "ETH"}

def test_load_coin_scores_empty_universe():
    scores, breakdowns = load_coin_scores([], [])
    assert scores == {}
    assert breakdowns == {}

def test_evaluate_performance_all_zero():
    unevaluated = [
        {
            "timestamp": 123456,
            "portfolio": ["BTCUSDT", "ETHUSDT"],
            "entry_prices": {"BTCUSDT": 0.0, "ETHUSDT": 0.0}
        }
    ]
    current_prices = {"BTCUSDT": 100.0, "ETHUSDT": 50.0}
    history = [
        {
            "timestamp": 123456,
            "portfolio": ["BTCUSDT", "ETHUSDT"],
            "entry_prices": {"BTCUSDT": 0.0, "ETHUSDT": 0.0},
            "evaluated": False
        }
    ]
    updated_history, results = evaluate_performance(unevaluated, current_prices, history, ["BTCUSDT", "ETHUSDT"])
    
    assert results[0]["performance"]["BTCUSDT"] == 0.0
    assert results[0]["performance"]["ETHUSDT"] == 0.0


def test_compute_bucket_stats_ranks_by_score_then_symbol():
    scores = {"AAAUSDT": 10.0, "BTCUSDT": 18.5, "ETHUSDT": 18.5, "SOLUSDT": 5.0}
    stats = compute_bucket_stats(["SOLUSDT", "BTCUSDT", "ETHUSDT", "AAAUSDT"], scores)
    assert stats["BTCUSDT"]["bucket_rank"] == 1
    assert stats["ETHUSDT"]["bucket_rank"] == 2
    assert stats["AAAUSDT"]["bucket_rank"] == 3
    assert stats["SOLUSDT"]["bucket_rank"] == 4
    assert stats["BTCUSDT"]["bucket_size"] == 4
    assert stats["ETHUSDT"]["bucket_size"] == 4
    assert stats["BTCUSDT"]["bucket_avg_score"] == pytest.approx((10.0 + 18.5 + 18.5 + 5.0) / 4)


def test_compute_bucket_stats_empty():
    assert compute_bucket_stats([], {"BTCUSDT": 10.0}) == {}


def test_compute_bucket_stats_missing_score_uses_initial():
    stats = compute_bucket_stats(["NEWUSDT"], {})
    assert stats["NEWUSDT"]["bucket_rank"] == 1
    assert stats["NEWUSDT"]["bucket_size"] == 1
    assert stats["NEWUSDT"]["bucket_avg_score"] == 10.0

