import pytest
from logic import get_coin_universe, load_coin_scores

def test_get_coin_universe():
    universe = get_coin_universe()
    assert "BTCUSDT" in universe
    assert "ETHUSDT" in universe
    assert "PEPEUSDT" in universe
    assert len(universe) > 5

def test_load_coin_scores(monkeypatch):
    def mock_load_history():
        return [{
            "evaluated": True,
            "performance": {
                "BTCUSDT": 0.05,
                "ETHUSDT": -0.02
            }
        }]
        
    import logic
    monkeypatch.setattr(logic, "load_history", mock_load_history)
    
    scores = load_coin_scores()
    assert scores["BTCUSDT"] == 15.0  # 10.0 + 5.0
    assert scores["ETHUSDT"] == 8.0   # 10.0 - 2.0
    assert scores["SOLUSDT"] == 10.0  # untouched
