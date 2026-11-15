import time

from history import (
    _default_repo,
    add_portfolio_record,
    clean_old_history_in_memory,
    get_unevaluated_records,
    load_history,
    save_history,
)

def test_clean_old_history_in_memory():
    old_time = time.time() - _default_repo.ttl_seconds - 100
    recent_time = time.time() - 100
    
    history = [
        {"timestamp": old_time, "portfolio": ["BTCUSDT"], "entry_prices": {}},
        {"timestamp": recent_time, "portfolio": ["ETHUSDT"], "entry_prices": {}}
    ]
    
    new_history = clean_old_history_in_memory(history)
    
    assert len(new_history) == 1
    assert new_history[0]["portfolio"] == ["ETHUSDT"]

def test_save_and_load_history(tmp_path, monkeypatch):
    test_file = str(tmp_path / "test_history.json")
    monkeypatch.setattr(_default_repo, "file_path", test_file)
    monkeypatch.setattr(_default_repo, "lock_path", f"{test_file}.lock")
    
    history = [
        {"timestamp": time.time(), "portfolio": ["BTCUSDT"], "entry_prices": {}}
    ]
    save_history(history)
    
    loaded = load_history()
    assert len(loaded) == 1
    assert loaded[0]["portfolio"] == ["BTCUSDT"]

def test_load_history_empty(tmp_path, monkeypatch):
    test_file = str(tmp_path / "does_not_exist.json")
    monkeypatch.setattr(_default_repo, "file_path", test_file)
    monkeypatch.setattr(_default_repo, "lock_path", f"{test_file}.lock")
    
    assert load_history() == []


def _use_tmp_history(tmp_path, monkeypatch):
    test_file = str(tmp_path / "test_history.json")
    monkeypatch.setattr(_default_repo, "file_path", test_file)
    monkeypatch.setattr(_default_repo, "lock_path", f"{test_file}.lock")


def test_get_unevaluated_records_respects_minimum_age():
    now = time.time()
    history = [
        {"timestamp": now - 7200, "portfolio": ["BTCUSDT"], "evaluated": False},
        {"timestamp": now - 60, "portfolio": ["ETHUSDT"], "evaluated": False},
        {"timestamp": now - 7200, "portfolio": ["SOLUSDT"], "evaluated": True},
    ]

    assert [r["portfolio"] for r in get_unevaluated_records(history)] == [["BTCUSDT"], ["ETHUSDT"]]
    due = get_unevaluated_records(history, min_age_seconds=3600)
    assert [r["portfolio"] for r in due] == [["BTCUSDT"]]


def test_add_portfolio_record_keeps_picks_on_latest_record_only(tmp_path, monkeypatch):
    _use_tmp_history(tmp_path, monkeypatch)

    add_portfolio_record(["BTCUSDT"], {"BTCUSDT": 1.0}, picks=[{"coin": "BTCUSDT", "score": 12.0}])
    add_portfolio_record(["ETHUSDT"], {"ETHUSDT": 2.0}, picks=[{"coin": "ETHUSDT", "score": 9.0}])

    saved = load_history()
    assert len(saved) == 2
    assert "picks" not in saved[0]
    assert saved[0]["portfolio"] == ["BTCUSDT"]
    assert saved[1]["picks"] == [{"coin": "ETHUSDT", "score": 9.0}]


def test_add_portfolio_record_without_picks(tmp_path, monkeypatch):
    _use_tmp_history(tmp_path, monkeypatch)

    add_portfolio_record(["BTCUSDT"], {"BTCUSDT": 1.0})

    assert "picks" not in load_history()[0]
