"""Репозиторий работы с санкциями из CSV-справочника."""

from __future__ import annotations

from datetime import date

from app.domain.models.sanction_rule import SanctionRule
from app.infrastructure.loaders.reference_loader import ReferenceService


class ReferenceRepository:
    """Фасад репозитория для получения доменных правил санкций."""

    def __init__(self, service: ReferenceService):
        self._service = service

    def get_rule(self, article: str, point: str | None = None, event_date: date | None = None) -> SanctionRule | None:
        row = self._service.get_by_article(article=article, point=point, event_date=event_date)
        return _to_rule(row) if row else None

    def get_rules_for_article(self, article: str) -> list[SanctionRule]:
        return [_to_rule(row) for row in self._service.get_rules_for_article(article) if row]

    def get_by_code(self, code: str, crime_date: date) -> dict | None:
        return self._service.get_by_code(code=code, crime_date=crime_date)

    def reload(self) -> None:
        self._service.reload()

    @property
    def source(self) -> str:
        return self._service.source

    @property
    def count(self) -> int:
        return self._service.count

    @property
    def file_path(self) -> str:
        return self._service.file_path


def _to_rule(row: dict) -> SanctionRule:
    main_allowed = _split_codes(row.get("fs1r64", ""))
    required_additional = _split_codes(row.get("fs1r65_o", ""))
    optional_additional = _split_codes(row.get("fs1r65_n", ""))
    ranges = {
        "05": _num_range(row.get("fs1r64_05n", ""), row.get("fs1r64_05x", "")),
        "06": _num_range(row.get("fs1r64_06n", ""), row.get("fs1r64_06x", "")),
        "09": _num_range(row.get("fs1r64_09n", ""), row.get("fs1r64_09x", "")),
        "11": _num_range(row.get("fs1r64_11n", ""), row.get("fs1r64_11x", "")),
        "12": _num_range(row.get("fs1r64_12n", ""), row.get("fs1r64_12x", "")),
        "01": _num_range(row.get("fs1r64_01n", ""), row.get("fs1r64_01x", "")),
    }
    add_ranges = {
        "02": _num_range(row.get("fs1r65_02n", ""), row.get("fs1r65_02x", "")),
    }
    point = None
    points = _split_codes(row.get("punkt", ""))
    if points:
        point = points[0]

    return SanctionRule(
        article=row.get("stat", ""),
        point=point,
        severity=row.get("hard", ""),
        severity_coef=_to_float(row.get("koef_hard", 0)),
        is_offense=str(row.get("prest", "")).strip() == "2",
        codification=row.get("kodific", ""),
        is_negligent=str(row.get("fs1_neost", "")).strip() in {"1", "yes", "true"},
        allowed_main_punishments=main_allowed,
        lower_than_lowest_allowed=bool(str(row.get("fs1r64_nn", "")).strip()),
        main_punishment_ranges=ranges,
        required_additional_punishments=required_additional,
        optional_additional_punishments=optional_additional,
        additional_punishment_ranges=add_ranges,
        effective_date=row.get("d_izm"),
        raw_source=row,
    )


def _split_codes(value: str) -> list[str]:
    return [item.strip().zfill(2) for item in str(value).split(",") if item.strip()]


def _to_float(value: str | float | int) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _num_range(min_value: str, max_value: str) -> dict[str, float]:
    return {"min": _to_float(min_value), "max": _to_float(max_value)}
