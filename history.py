import json
import os
import time

HISTORY_FILE = "history.json"
TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days

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

def clean_old_history_in_memory(history):
    now = time.time()
    return [record for record in history if now - record.get("timestamp", 0) <= TTL_SECONDS]

def add_portfolio_record(portfolio, prices):
    history = load_history()
    record = {
        "timestamp": time.time(),
        "portfolio": portfolio,
        "entry_prices": prices,
        "evaluated": False
    }
    history.append(record)
    valid_history = clean_old_history_in_memory(history)
    save_history(valid_history)

def get_unevaluated_records():
    return [r for r in load_history() if not r.get("evaluated", False)]
