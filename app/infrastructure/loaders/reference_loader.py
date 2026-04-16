"""Загрузка и кеширование справочника санкций из CSV `d_fe1r10p1`."""

from __future__ import annotations

import csv
import os
from datetime import date
from pathlib import Path
from threading import Lock
from typing import Any


class ReferenceService:
    """Сервис доступа к CSV-справочнику с индексами по статье/коду."""

    REQUIRED_FIELDS = {
        "stat",
        "punkt",
        "hard",
        "koef_hard",
        "prest",
        "kodific",
        "fs1_neost",
        "fs1r64",
        "fs1r64_nn",
        "fs1r64_05n",
        "fs1r64_05x",
        "fs1r64_06n",
        "fs1r64_06x",
        "fs1r64_09n",
        "fs1r64_09x",
        "fs1r64_11n",
        "fs1r64_11x",
        "fs1r64_12n",
        "fs1r64_12x",
        "fs1r64_01n",
        "fs1r64_01x",
        "fs1r65_o",
        "fs1r65_n",
        "fs1r65_02n",
        "fs1r65_02x",
        "d_izm",
    }

    def __init__(self, file_path: str | None = None):
        self._lock = Lock()
        self._file_path = Path(file_path) if file_path else None
        self._records: list[dict[str, Any]] = []
        self._by_article: dict[str, list[dict[str, Any]]] = {}
        self._by_code: dict[str, list[dict[str, Any]]] = {}
        self._loaded = False
        self._source = "unknown"
        self._ensure_loaded()

    def _ensure_loaded(self) -> None:
        with self._lock:
            if self._loaded:
                return
            self._load_from_file()
            self._loaded = True
            self._source = "file"

    def reload(self) -> None:
        with self._lock:
            self._records = []
            self._by_article = {}
            self._by_code = {}
            self._loaded = False
            self._ensure_loaded()

    @property
    def source(self) -> str:
        return self._source

    @property
    def file_path(self) -> str:
        return str(self._get_file_path())

    @property
    def count(self) -> int:
        self._ensure_loaded()
        return len(self._records)

    def get_by_code(self, code: str, crime_date: date | None = None) -> dict[str, Any] | None:
        self._ensure_loaded()
        candidates = self._by_code.get((code or "").strip(), [])
        return self._pick_current(candidates, crime_date)

    def get_by_article(self, article: str, point: str | None = None, event_date: date | None = None) -> dict[str, Any] | None:
        self._ensure_loaded()
        candidates = self._by_article.get((article or "").strip(), [])
        if point:
            normalized_point = str(point).zfill(2)
            point_filtered = [
                row
                for row in candidates
                if normalized_point in _extract_points(row.get("punkt", ""))
            ]
            if point_filtered:
                candidates = point_filtered
        return self._pick_current(candidates, event_date)

    def get_rules_for_article(self, article: str) -> list[dict[str, Any]]:
        self._ensure_loaded()
        return list(self._by_article.get((article or "").strip(), []))

    def _pick_current(self, rows: list[dict[str, Any]], event_date: date | None) -> dict[str, Any] | None:
        if not rows:
            return None
        target = event_date or date.max
        suitable = [r for r in rows if (r.get("d_izm") or date.min) <= target]
        if suitable:
            return max(suitable, key=lambda r: r.get("d_izm") or date.min)
        return max(rows, key=lambda r: r.get("d_izm") or date.min)

    def _get_file_path(self) -> Path:
        if self._file_path:
            return self._file_path
        return Path(__file__).resolve().parents[3] / "d_fe1r10p1.csv"

    def _load_from_file(self) -> None:
        file_path = self._get_file_path()
        if not file_path.exists():
            return
        with file_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                return
            header_map = {h: _normalize_col(h) for h in reader.fieldnames}
            for raw in reader:
                row = {_normalize_col(header_map.get(k, k)): (v or "").strip() for k, v in raw.items() if k is not None}
                normalized = self._normalize_row(row)
                self._records.append(normalized)
                article = normalized.get("stat", "")
                if article:
                    self._by_article.setdefault(article, []).append(normalized)
                code = normalized.get("p2", "")
                if code:
                    self._by_code.setdefault(code, []).append(normalized)

    def _normalize_row(self, row: dict[str, str]) -> dict[str, Any]:
        normalized = {k: v for k, v in row.items()}
        for field in self.REQUIRED_FIELDS:
            normalized.setdefault(field, "")
        normalized["d_izm"] = _parse_date(normalized.get("d_izm", ""))
        return normalized


def _normalize_col(name: str) -> str:
    return name.strip().lower()


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    try:
        day, month, year = value.split(".")
        return date(int(year), int(month), int(day))
    except Exception:
        return None


def _extract_points(value: str) -> set[str]:
    return {item.strip().zfill(2) for item in value.split(",") if item.strip()}


_SERVICE: ReferenceService | None = None


def get_reference_service() -> ReferenceService:
    global _SERVICE
    if _SERVICE is None:
        ref_path = os.environ.get("REFERENCE_FILE_PATH")
        _SERVICE = ReferenceService(ref_path)
    return _SERVICE
