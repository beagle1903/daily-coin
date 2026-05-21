import json
import os
import time

HISTORY_FILE = "history.json"
TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def clean_old_history():
    history = load_history()
    now = time.time()
    valid_history = [record for record in history if now - record.get("timestamp", 0) <= TTL_SECONDS]
    
    if len(valid_history) != len(history):
        save_history(valid_history)

def add_portfolio_record(portfolio, prices):
    history = load_history()
    record = {
        "timestamp": time.time(),
        "portfolio": portfolio,
        "entry_prices": prices,
        "evaluated": False
    }
    history.append(record)
    save_history(history)
    clean_old_history()

def get_unevaluated_records():
    return [r for r in load_history() if not r.get("evaluated", False)]
