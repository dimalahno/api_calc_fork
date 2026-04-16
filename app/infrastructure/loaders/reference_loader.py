"""Загрузка и кеширование справочника УК из CSV-файла d_fe1r10p1."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from threading import Lock
from typing import Optional


@dataclass(frozen=True)
class ArticleRecord:
    """Запись санкции по статье/части из CSV-справочника."""

    article_code: str
    hard: str
    koef_hard: str
    line: str
    prest: str
    punkt: str
    fs1r64: str
    fs1r64_add: str
    fs1r64_nn: str
    fs1r64_05n: str
    fs1r64_05x: str
    fs1r64_06n: str
    fs1r64_06x: str
    fs1r64_09n: str
    fs1r64_09x: str
    fs1r64_12n: str
    fs1r64_12x: str
    fs1r64_11n: str
    fs1r64_11x: str
    fs1r64_01n: str
    fs1r64_01x: str
    fs1r65_o: str
    fs1r65_n: str
    fs1r65_02n: str
    fs1r65_02x: str
    fl1u: str
    d_izm: Optional[date]


class ReferenceService:
    """Сервис доступа к справочнику: чтение CSV и выбор записи по дате."""

    def __init__(self, file_path: Optional[str] = None):
        self._lock = Lock()
        self._file_path = Path(file_path) if file_path else None
        self._records: dict[str, list[ArticleRecord]] = {}
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
            self._records = {}
            self._loaded = False
            self._ensure_loaded()

    @property
    def source(self) -> str:
        return self._source

    @property
    def file_path(self) -> str:
        if self._file_path:
            return str(self._file_path)
        return "(default)"

    @property
    def count(self) -> int:
        self._ensure_loaded()
        return sum(len(v) for v in self._records.values())

    def get_by_code(self, code: str, crime_date: date) -> Optional[ArticleRecord]:
        self._ensure_loaded()
        records = self._records.get(code or "")
        if not records:
            return None

        best = None
        best_date = None
        for rec in records:
            rec_date = rec.d_izm or date.min
            if rec_date <= crime_date and (best is None or rec_date > best_date):
                best = rec
                best_date = rec_date
        if best is not None:
            return best
        return records[0]

    def _get_file_path(self) -> Path:
        if self._file_path:
            return self._file_path
        return Path(__file__).resolve().parents[3] / "d_fe1r10p1.csv"

    def _load_from_file(self) -> None:
        file_path = self._get_file_path()
        if not file_path.exists():
            return

        with file_path.open("r", encoding="utf-8-sig", newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                self._parse_row({(k or "").strip().lower(): (v or "").strip() for k, v in row.items()})

    def _parse_row(self, row: dict[str, str]) -> None:
        code = row.get("p2", "").strip()
        if not code:
            return

        record = ArticleRecord(
            article_code=code,
            hard=row.get("hard", ""),
            koef_hard=row.get("koef_hard", ""),
            line=row.get("line", ""),
            prest=row.get("prest", ""),
            punkt=row.get("punkt", ""),
            fs1r64=row.get("fs1r64", ""),
            fs1r64_add=row.get("fs1r64_add", ""),
            fs1r64_nn=row.get("fs1r64_nn", ""),
            fs1r64_05n=row.get("fs1r64_05n", ""),
            fs1r64_05x=row.get("fs1r64_05x", ""),
            fs1r64_06n=row.get("fs1r64_06n", ""),
            fs1r64_06x=row.get("fs1r64_06x", ""),
            fs1r64_09n=row.get("fs1r64_09n", ""),
            fs1r64_09x=row.get("fs1r64_09x", ""),
            fs1r64_12n=row.get("fs1r64_12n", ""),
            fs1r64_12x=row.get("fs1r64_12x", ""),
            fs1r64_11n=row.get("fs1r64_11n", ""),
            fs1r64_11x=row.get("fs1r64_11x", ""),
            fs1r64_01n=row.get("fs1r64_01n", ""),
            fs1r64_01x=row.get("fs1r64_01x", ""),
            fs1r65_o=row.get("fs1r65_o", ""),
            fs1r65_n=row.get("fs1r65_n", ""),
            fs1r65_02n=row.get("fs1r65_02n", ""),
            fs1r65_02x=row.get("fs1r65_02x", ""),
            fl1u=row.get("fl1u", ""),
            d_izm=_parse_date(row.get("d_izm", "")),
        )

        self._records.setdefault(code, []).append(record)


def _parse_date(value: str) -> Optional[date]:
    if not value or value in {"-", "--"}:
        return None
    try:
        if "-" in value:
            return date.fromisoformat(value)
        day, month, year = value.split(".")
        return date(int(year), int(month), int(day))
    except Exception:
        return None


_SERVICE: Optional[ReferenceService] = None


def get_reference_service() -> ReferenceService:
    """Возвращает singleton-экземпляр `ReferenceService` для приложения."""
    global _SERVICE
    if _SERVICE is None:
        ref_path = os.environ.get("REFERENCE_FILE_PATH")
        _SERVICE = ReferenceService(ref_path)
    return _SERVICE
