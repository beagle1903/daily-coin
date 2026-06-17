import pytest
from logic import load_coin_scores

def test_load_coin_scores(monkeypatch):
    def mock_load_history():
        return [{
            "evaluated": True,
            "performance": {
                "BTCUSDT": 0.05,
                "ETHUSDT": -0.02
            }
        }]
        
    async def mock_fetch_all_technical_indicators(universe):
        return {
            u: {"rsi": 50.0, "macd": 0.0, "signal": 0.0} for u in universe
        }
        
    import logic
    monkeypatch.setattr(logic, "load_history", mock_load_history)
    monkeypatch.setattr(logic, "fetch_all_technical_indicators", mock_fetch_all_technical_indicators)
    
    universe = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    scores = load_coin_scores(universe)
    assert scores["BTCUSDT"] == 15.0  # 10.0 + 5.0
    assert scores["ETHUSDT"] == 8.0   # 10.0 - 2.0
    assert scores["SOLUSDT"] == 10.0  # untouched
