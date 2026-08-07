import json
import os
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from filelock import FileLock

class HistoryRepository(ABC):
    @abstractmethod
    def load_history(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_history(self, history: List[Dict[str, Any]]) -> None:
        pass

    def clean_old_history_in_memory(self, history: List[Dict[str, Any]], ttl_seconds: int) -> List[Dict[str, Any]]:
        now = time.time()
        return [record for record in history if now - record.get("timestamp", 0) <= ttl_seconds]


class JsonHistoryRepository(HistoryRepository):
    def __init__(self, file_path: str = "history.json", ttl_seconds: int = 30 * 24 * 60 * 60):
        self.file_path = file_path
        self.lock_path = f"{file_path}.lock"
        self.ttl_seconds = ttl_seconds

    def load_history(self) -> List[Dict[str, Any]]:
        with FileLock(self.lock_path):
            if not os.path.exists(self.file_path):
                return []
            try:
                with open(self.file_path, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []

    def save_history(self, history: List[Dict[str, Any]]) -> None:
        temp_path = f"{self.file_path}.tmp"
        with FileLock(self.lock_path):
            with open(temp_path, "w") as f:
                json.dump(history, f, indent=2)
            os.replace(temp_path, self.file_path)

# Default global instance for backward compatibility with current function signatures
_default_repo = JsonHistoryRepository()

def load_history() -> List[Dict[str, Any]]:
    return _default_repo.load_history()

def save_history(history: List[Dict[str, Any]]) -> None:
    _default_repo.save_history(history)

def clean_old_history_in_memory(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _default_repo.clean_old_history_in_memory(history, _default_repo.ttl_seconds)

def add_portfolio_record(portfolio: List[str], prices: Dict[str, float]) -> None:
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

def get_unevaluated_records(history: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    if history is None:
        history = load_history()
    return [r for r in history if not r.get("evaluated", False)]
