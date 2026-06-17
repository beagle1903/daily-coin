import time
import pytest

from history import load_history, save_history, clean_old_history_in_memory, TTL_SECONDS

def test_clean_old_history_in_memory():
    old_time = time.time() - TTL_SECONDS - 100
    recent_time = time.time() - 100
    
    history = [
        {"timestamp": old_time, "portfolio": ["BTCUSDT"], "entry_prices": {}},
        {"timestamp": recent_time, "portfolio": ["ETHUSDT"], "entry_prices": {}}
    ]
    
    new_history = clean_old_history_in_memory(history)
    
    assert len(new_history) == 1
    assert new_history[0]["portfolio"] == ["ETHUSDT"]

def test_save_and_load_history(tmp_path, monkeypatch):
    test_file = tmp_path / "test_history.json"
    monkeypatch.setattr("history.HISTORY_FILE", str(test_file))
    
    history = [
        {"timestamp": time.time(), "portfolio": ["BTCUSDT"], "entry_prices": {}}
    ]
    save_history(history)
    
    loaded = load_history()
    assert len(loaded) == 1
    assert loaded[0]["portfolio"] == ["BTCUSDT"]

def test_load_history_empty(tmp_path, monkeypatch):
    test_file = tmp_path / "does_not_exist.json"
    monkeypatch.setattr("history.HISTORY_FILE", str(test_file))
    
    assert load_history() == []
