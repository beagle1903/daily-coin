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


def test_record_run_saves_evaluations_and_new_record_together(tmp_path, monkeypatch):
    from history import record_run

    _use_tmp_history(tmp_path, monkeypatch)
    old = {"timestamp": time.time() - 7200, "portfolio": ["BTCUSDT"],
           "entry_prices": {"BTCUSDT": 1.0}, "evaluated": False, "picks": [{"coin": "BTCUSDT"}]}
    save_history([old])

    record_run({old["timestamp"]: {"BTCUSDT": 0.1}}, ["ETHUSDT"], {"ETHUSDT": 2.0}, [{"coin": "ETHUSDT"}])

    saved = load_history()
    assert len(saved) == 2
    assert saved[0]["evaluated"] is True
    assert saved[0]["performance"] == {"BTCUSDT": 0.1}
    assert "picks" not in saved[0]
    assert saved[1]["portfolio"] == ["ETHUSDT"]
    assert saved[1]["picks"] == [{"coin": "ETHUSDT"}]


def test_record_run_does_not_overwrite_an_earlier_evaluation(tmp_path, monkeypatch):
    """If two runs evaluated the same record, the first saved result wins."""
    from history import record_run

    _use_tmp_history(tmp_path, monkeypatch)
    ts = time.time() - 7200
    save_history([{"timestamp": ts, "portfolio": ["BTCUSDT"], "entry_prices": {"BTCUSDT": 1.0},
                   "evaluated": True, "performance": {"BTCUSDT": 0.1}}])

    record_run({ts: {"BTCUSDT": -0.5}})

    assert load_history()[0]["performance"] == {"BTCUSDT": 0.1}


def test_record_run_with_nothing_to_add_keeps_history(tmp_path, monkeypatch):
    from history import record_run

    _use_tmp_history(tmp_path, monkeypatch)
    record = {"timestamp": time.time(), "portfolio": ["BTCUSDT"], "entry_prices": {}, "evaluated": False}
    save_history([record])

    record_run({})

    assert load_history() == [record]
