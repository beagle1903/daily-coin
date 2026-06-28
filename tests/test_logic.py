import pytest
from logic import load_coin_scores, pick_portfolio, evaluate_performance

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
        {"coin": "BTCUSDT", "adjustment": 0.5}
    ]
    technical_indicators = {
        "BTCUSDT": {"rsi": 25.0, "macd": 0.1, "signal": 0.0},
        "ETHUSDT": {"rsi": 75.0, "macd": -0.1, "signal": 0.0},
        "SOLUSDT": {"rsi": 50.0, "macd": 0.0, "signal": 0.0}
    }
    
    scores = load_coin_scores(universe, history, sentiment_impacts, technical_indicators)
    # BTCUSDT score: 10.0 + 5.0 (history) + 0.5 (sentiment) + 3.0 (technical) = 18.5
    # ETHUSDT score: 10.0 - 2.0 (history) - 3.0 (technical) = 5.0
    # SOLUSDT score: 10.0 (no history, sentiment, or tech changes) = 10.0
    assert scores["BTCUSDT"] == 18.5
    assert scores["ETHUSDT"] == 5.0
    assert scores["SOLUSDT"] == 10.0

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
