"""Внутренняя модель контекста расчёта (без привязки к API-схемам)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class EpisodeContext:
    """Нормализованный эпизод для расчёта."""

    article: str
    point: str | None = None
    event_date: date | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CalculationContext:
    """Контекст карточки и эпизодов для внутреннего расчётчика."""

    person: dict[str, Any]
    episodes: list[EpisodeContext]
    calc_date: date
    meta: dict[str, Any] = field(default_factory=dict)
