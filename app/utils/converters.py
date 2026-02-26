from __future__ import annotations

from datetime import date


def to_payload_dict(model) -> dict:
    """Convert Pydantic v1/v2 models to a dict payload."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def resolve_date(value: date | None, fallback: date) -> date:
    return value or fallback
