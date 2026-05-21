import os
import time
import json
import pytest

from history import load_history, save_history, clean_old_history, HISTORY_FILE, TTL_SECONDS

@pytest.fixture(autouse=True)
def setup_teardown():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    yield
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)

def test_clean_old_history():
    old_time = time.time() - TTL_SECONDS - 100
    recent_time = time.time() - 100
    
    history = [
        {"timestamp": old_time, "portfolio": ["BTCUSDT"], "entry_prices": {}},
        {"timestamp": recent_time, "portfolio": ["ETHUSDT"], "entry_prices": {}}
    ]
    save_history(history)
    
    clean_old_history()
    
    new_history = load_history()
    assert len(new_history) == 1
    assert new_history[0]["portfolio"] == ["ETHUSDT"]
