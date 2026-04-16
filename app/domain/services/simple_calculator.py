"""Упрощённый расчёт наказаний на основе санкций d_fe1r10p1."""

from __future__ import annotations

from app.domain.models.calculation_context import CalculationContext
from app.domain.models.sanction_rule import SanctionRule
from app.domain.services.sanction_resolver import SanctionResolver

PUNISHMENT_ORDER = ["02", "03", "01", "11", "12", "09", "06", "05"]
MAIN_CODE_TO_KEY = {
    "05": "fine",
    "06": "corrective_work",
    "09": "mandatory_work",
    "11": "restriction_of_freedom",
    "12": "arrest",
    "01": "imprisonment",
    "02": "death_penalty",
}
ADD_CODE_TO_KEY = {
    "01": "confiscation",
    "03": "deportation",
    "04": "lifetime_prohibition",
    "02": "prohibition_term",
    "14": "deprivation_of_citizenship",
}


class SimplePunishmentCalculator:
    """Выполняет минимально необходимый расчёт по эпизодам и агрегирует итог."""

    def __init__(self, resolver: SanctionResolver):
        self._resolver = resolver

    def calculate(self, context: CalculationContext) -> dict:
        episodes: list[dict] = []
        resolved_rules: list[SanctionRule] = []
        all_optional_add: set[str] = set()
        all_required_add: set[str] = set()

        for episode in context.episodes:
            rule = self._resolver.resolve(episode)
            if not rule:
                episodes.append({"article": episode.article, "point": episode.point, "found": False})
                continue
            resolved_rules.append(rule)
            all_required_add.update(rule.required_additional_punishments)
            all_optional_add.update(rule.optional_additional_punishments)
            episodes.append(
                {
                    "article": rule.article,
                    "point": rule.point,
                    "found": True,
                    "severity": rule.severity,
                    "severity_coef": rule.severity_coef,
                    "allowed_main": rule.allowed_main_punishments,
                    "required_additional": rule.required_additional_punishments,
                    "optional_additional": rule.optional_additional_punishments,
                }
            )

        top_rule = _pick_top_rule(resolved_rules)
        top_punishment = _pick_top_punishment(resolved_rules)

        return {
            "episodes": episodes,
            "resolved_rules": resolved_rules,
            "top_rule": top_rule,
            "top_punishment": top_punishment,
            "required_additional": sorted(all_required_add),
            "optional_additional": sorted(all_optional_add),
        }


def _pick_top_rule(rules: list[SanctionRule]) -> SanctionRule | None:
    if not rules:
        return None
    return max(rules, key=lambda r: (r.severity_coef, _safe_int(r.severity)))


def _pick_top_punishment(rules: list[SanctionRule]) -> str | None:
    best = None
    best_rank = 10_000
    for rule in rules:
        for code in rule.allowed_main_punishments:
            rank = PUNISHMENT_ORDER.index(code) if code in PUNISHMENT_ORDER else 9999
            if rank < best_rank:
                best_rank = rank
                best = code
    return best


def _safe_int(value: str | int) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0
