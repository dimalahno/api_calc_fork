from __future__ import annotations

from app.domain.services.calculator import calculate_from_json


class PunishmentService:
    """Domain service orchestrating punishment calculation."""

    def calculate(self, payload: dict) -> tuple[list[list], dict]:
        return calculate_from_json(payload)
