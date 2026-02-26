from __future__ import annotations

from services.punishment_api.calculator import calculate_from_json


class PunishmentService:
    """Domain service orchestrating punishment calculation."""

    def calculate(self, payload: dict) -> tuple[list[list], dict]:
        return calculate_from_json(payload)
