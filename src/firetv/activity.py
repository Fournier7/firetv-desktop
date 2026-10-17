"""Registro local do tempo de uso de cada app (só no PC do usuário)."""
from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from firetv.config import config_dir

LAUNCHER_PACKAGES = {"com.amazon.tv.launcher"}
MAX_SAMPLE_SECONDS = 10
RETENTION_DAYS = 90
_PERIOD_DAYS = {"today": 1, "7d": 7, "30d": 30}


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds} s"
    if seconds < 3600:
        return f"{seconds // 60} min"
    return f"{seconds // 3600} h {(seconds % 3600) // 60:02d} min"


def _valid_seconds(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


class ActivityLog:
    def __init__(self, path: Path | None = None, today: Callable[[], date] = date.today) -> None:
        self._path = path if path is not None else config_dir() / "activity.json"
        self._today = today
        self._days: dict[str, dict[str, float]] = {}
        self._last: float | None = None
        self._load()

    # --- gravação de amostras ---
    def record(self, package: str, now: float) -> None:
        last, self._last = self._last, now
        if last is None or now <= last or package in LAUNCHER_PACKAGES:
            return
        added = min(now - last, MAX_SAMPLE_SECONDS)
        bucket = self._days.setdefault(self._today().isoformat(), {})
        bucket[package] = bucket.get(package, 0.0) + added

    def reset_clock(self) -> None:
        self._last = None

    # --- consultas ---
    def totals(self, period: str) -> list[tuple[str, int]]:
        if period not in _PERIOD_DAYS:
            raise ValueError(f"período desconhecido: {period!r}")
        today = self._today()
        wanted = {(today - timedelta(days=i)).isoformat() for i in range(_PERIOD_DAYS[period])}
        sums: dict[str, float] = {}
        for day, bucket in self._days.items():
            if day in wanted:
                for package, seconds in bucket.items():
                    sums[package] = sums.get(package, 0.0) + seconds
        rows = [(p, int(round(s))) for p, s in sums.items() if s > 0]
        return sorted(rows, key=lambda row: (-row[1], row[0]))

    def total_seconds(self, period: str) -> int:
        return sum(seconds for _, seconds in self.totals(period))

    # --- persistência ---
    def save(self) -> None:
        self._prune()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        days = {
            day: {p: round(s, 2) for p, s in bucket.items()}
            for day, bucket in sorted(self._days.items())
        }
        self._path.write_text(json.dumps({"days": days}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            raw_days = data["days"]
            if not isinstance(raw_days, dict):
                raise TypeError("days")
        except (ValueError, KeyError, TypeError, OSError):
            self._path.replace(self._path.with_name(self._path.name + ".bak"))
            return
        for key, bucket in raw_days.items():
            try:
                day = date.fromisoformat(key).isoformat()
            except (TypeError, ValueError):
                continue
            if day != key or not isinstance(bucket, dict):
                continue
            clean = {
                p: float(s) for p, s in bucket.items() if isinstance(p, str) and _valid_seconds(s)
            }
            if clean:
                self._days[day] = clean
        self._prune()

    def _prune(self) -> None:
        cutoff = (self._today() - timedelta(days=RETENTION_DAYS)).isoformat()
        self._days = {day: b for day, b in self._days.items() if day >= cutoff}
