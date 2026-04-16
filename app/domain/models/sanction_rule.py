"""Внутренняя модель санкции из справочника d_fe1r10p1."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class SanctionRule:
    """Упрощённая доменная модель санкции по статье/пункту."""

    article: str
    point: str | None
    severity: str
    severity_coef: float
    is_offense: bool
    codification: str
    is_negligent: bool
    allowed_main_punishments: list[str] = field(default_factory=list)
    lower_than_lowest_allowed: bool = False
    main_punishment_ranges: dict[str, dict[str, float]] = field(default_factory=dict)
    required_additional_punishments: list[str] = field(default_factory=list)
    optional_additional_punishments: list[str] = field(default_factory=list)
    additional_punishment_ranges: dict[str, dict[str, float]] = field(default_factory=dict)
    effective_date: date | None = None
    raw_source: dict[str, Any] | None = None
