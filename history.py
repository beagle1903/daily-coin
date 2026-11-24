import json
import os
import time
from typing import Any, Callable, Dict, List

from filelock import FileLock

from constants import HISTORY_TTL_SECONDS


class JsonHistoryRepository:
    def __init__(self, file_path: str = "history.json", ttl_seconds: int = HISTORY_TTL_SECONDS):
        self.file_path = file_path
        self.lock_path = f"{file_path}.lock"
        self.ttl_seconds = ttl_seconds

    def _read(self) -> List[Dict[str, Any]]:
        """Read without locking; the caller holds the lock."""
        if not os.path.exists(self.file_path):
            return []
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def _write(self, history: List[Dict[str, Any]]) -> None:
        """Write atomically without locking; the caller holds the lock."""
        temp_path = f"{self.file_path}.tmp"
        with open(temp_path, "w") as f:
            json.dump(history, f, indent=2)
        os.replace(temp_path, self.file_path)

    def load_history(self) -> List[Dict[str, Any]]:
        with FileLock(self.lock_path):
            return self._read()

    def save_history(self, history: List[Dict[str, Any]]) -> None:
        with FileLock(self.lock_path):
            self._write(history)

    def update(self, mutate: Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]]) -> None:
        """
        Read, change and write the history under one file lock, so a concurrent
        writer (another API request, or the CLI in a second process) cannot slip
        in between the read and the write and have its change lost.
        """
        with FileLock(self.lock_path):
            self._write(mutate(self._read()))

    def clean_old_history_in_memory(self, history: List[Dict[str, Any]], ttl_seconds: int) -> List[Dict[str, Any]]:
        now = time.time()
        return [record for record in history if now - record.get("timestamp", 0) <= ttl_seconds]

# Default global instance for backward compatibility with current function signatures
_default_repo = JsonHistoryRepository()

def load_history() -> List[Dict[str, Any]]:
    return _default_repo.load_history()

def save_history(history: List[Dict[str, Any]]) -> None:
    _default_repo.save_history(history)

def clean_old_history_in_memory(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _default_repo.clean_old_history_in_memory(history, _default_repo.ttl_seconds)

def _new_record(
    portfolio: List[str],
    prices: Dict[str, float],
    picks: List[Dict[str, Any]] | None,
) -> Dict[str, Any]:
    record = {
        "timestamp": time.time(),
        "portfolio": portfolio,
        "entry_prices": prices,
        "evaluated": False,
    }
    if picks is not None:
        record["picks"] = picks
    return record


def _append_record(history: List[Dict[str, Any]], record: Dict[str, Any]) -> None:
    # Only the newest record keeps the full pick details, to keep the file small
    for old_record in history:
        old_record.pop("picks", None)
    history.append(record)


def add_portfolio_record(
    portfolio: List[str],
    prices: Dict[str, float],
    picks: List[Dict[str, Any]] | None = None,
) -> None:
    """
    Append a new record. ``picks`` is the full per-coin detail (score, indicators,
    explanation) so the dashboard can show the latest saved portfolio without
    generating a new one. Only the newest record keeps it, to keep the file small.
    """
    record_run({}, portfolio, prices, picks)


def record_run(
    performance_by_timestamp: Dict[float, Dict[str, float]],
    portfolio: List[str] | None = None,
    prices: Dict[str, float] | None = None,
    picks: List[Dict[str, Any]] | None = None,
) -> None:
    """
    Save everything one pipeline run changes in a single locked read-modify-write:
    the performance of the records it evaluated (keyed by record timestamp) and,
    when ``portfolio`` is given, the new record.

    A record that is already marked evaluated in the file is left alone, so if two
    runs evaluated the same record (for example the CLI and the API at once), only
    the first result is kept.
    """
    def mutate(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for record in history:
            performance = performance_by_timestamp.get(record.get("timestamp"))
            if performance is not None and not record.get("evaluated", False):
                record["performance"] = performance
                record["evaluated"] = True
        if portfolio is not None:
            _append_record(history, _new_record(portfolio, prices or {}, picks))
        return _default_repo.clean_old_history_in_memory(history, _default_repo.ttl_seconds)

    _default_repo.update(mutate)


def get_unevaluated_records(
    history: List[Dict[str, Any]] = None, min_age_seconds: float = 0
) -> List[Dict[str, Any]]:
    """Unevaluated records that are at least ``min_age_seconds`` old."""
    if history is None:
        history = load_history()
    cutoff = time.time() - min_age_seconds
    return [
        r for r in history
        if not r.get("evaluated", False) and r.get("timestamp", 0) <= cutoff
    ]
