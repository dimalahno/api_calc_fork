"""Оркестрация расчёта: адаптация payload -> контекст -> упрощённый расчёт -> response."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.domain.models.calculation_context import CalculationContext, EpisodeContext
from app.domain.services.sanction_resolver import SanctionResolver
from app.domain.services.simple_calculator import ADD_CODE_TO_KEY, MAIN_CODE_TO_KEY, SimplePunishmentCalculator
from app.infrastructure.loaders.reference_loader import get_reference_service
from app.infrastructure.repositories.reference_repository import ReferenceRepository


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return None


def calculate_from_json(payload: dict[str, Any]) -> tuple[list[list[Any]], dict[str, Any]]:
    context = _to_context(payload)

    repository = ReferenceRepository(get_reference_service())
    resolver = SanctionResolver(repository)
    calculator = SimplePunishmentCalculator(resolver)
    result = calculator.calculate(context)

    structured = _build_structured(result)
    a_nakaz = [[False, 0, 0, "", 0, 0, 0, 0, 0, 0, 0, 0, 0] for _ in range(15)]
    return a_nakaz, structured


def _to_context(payload: dict[str, Any]) -> CalculationContext:
    person = payload.get("person", {}) or {}
    crime = payload.get("crime", {}) or {}
    calc_date = _parse_date(payload.get("calc_date")) or date.today()

    episodes_payload = payload.get("episodes") or payload.get("crimes") or [crime]
    episodes: list[EpisodeContext] = []
    for item in episodes_payload:
        if not isinstance(item, dict):
            continue
        episodes.append(
            EpisodeContext(
                article=_resolve_article(item),
                point=(item.get("paragraph") or item.get("point") or None),
                event_date=_parse_date(item.get("crime_date")) or calc_date,
                raw=item,
            )
        )

    return CalculationContext(person=person, episodes=episodes, calc_date=calc_date, meta={"lang": payload.get("lang", "ru")})


def _resolve_article(item: dict[str, Any]) -> str:
    article = str(item.get("stat") or item.get("article") or "").strip()
    part = str(item.get("part") or "").strip()
    if article and part and "ч." not in article:
        return f"ст.{article} ч.{part}"
    return article


def _build_structured(result: dict[str, Any]) -> dict[str, Any]:
    punishments = {
        "fine": _empty_main(),
        "corrective_work": _empty_main(),
        "mandatory_work": _empty_main(),
        "restriction_of_freedom": _empty_main(),
        "arrest": _empty_main(),
        "imprisonment": _empty_main(),
        "death_penalty": _empty_main(),
    }
    additional = {
        "confiscation": _empty_additional(),
        "deportation": _empty_additional(),
        "lifetime_prohibition": _empty_additional(),
        "prohibition_term": _empty_additional(),
        "deprivation_of_citizenship": _empty_additional(),
    }

    top_rule = result.get("top_rule")
    if top_rule:
        for code in top_rule.allowed_main_punishments:
            key = MAIN_CODE_TO_KEY.get(code)
            if not key:
                continue
            value_range = top_rule.main_punishment_ranges.get(code, {"min": 0, "max": 0})
            punishments[key] = {
                "is_applicable": True,
                "min_value": value_range.get("min", 0),
                "max_value": value_range.get("max", 0),
                "formatted_text": f"{code}: {value_range.get('min', 0)}..{value_range.get('max', 0)}",
            }
        for code in result.get("required_additional", []):
            key = ADD_CODE_TO_KEY.get(code)
            if key:
                additional[key].update({"is_applicable": True, "is_mandatory": True, "formatted_text": code})
        for code in result.get("optional_additional", []):
            key = ADD_CODE_TO_KEY.get(code)
            if key and not additional[key]["is_mandatory"]:
                additional[key].update({"is_applicable": True, "is_mandatory": False, "formatted_text": code})

    return {
        "punishments": punishments,
        "additional_punishments": additional,
        "meta": {
            "reference_found": bool(top_rule),
            "top_article": top_rule.article if top_rule else "",
            "top_punishment": result.get("top_punishment") or "",
            "episodes": result.get("episodes", []),
        },
    }


def _empty_main() -> dict[str, Any]:
    return {"is_applicable": False, "min_value": 0, "max_value": 0, "formatted_text": ""}


def _empty_additional() -> dict[str, Any]:
    return {"is_applicable": False, "is_mandatory": False, "formatted_text": ""}
