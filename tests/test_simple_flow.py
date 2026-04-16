from __future__ import annotations

from datetime import date
from pathlib import Path

from app.domain.models.sanction_rule import SanctionRule
from app.domain.services.simple_calculator import _pick_top_punishment, _pick_top_rule
from app.infrastructure.loaders.reference_loader import ReferenceService
from app.infrastructure.repositories.reference_repository import ReferenceRepository
from app.api.v1.calculate import calculate
from app.domain.services.punishment_service import PunishmentService
from app.schemas.request import CalculateRequest


def _csv_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "d_fe1r10p1.csv")


def test_csv_loader_loads_new_file() -> None:
    service = ReferenceService(_csv_path())
    assert service.count > 0


def test_find_rule_by_article() -> None:
    repo = ReferenceRepository(ReferenceService(_csv_path()))
    rule = repo.get_rule(article="ст.99 ч.1", event_date=date(2026, 1, 1))
    assert rule is not None
    assert rule.article == "ст.99 ч.1"


def test_find_rule_by_article_and_point() -> None:
    repo = ReferenceRepository(ReferenceService(_csv_path()))
    rule = repo.get_rule(article="ст.99 ч.2", point="01", event_date=date(2026, 1, 1))
    assert rule is not None
    assert "01" in (rule.point or "") or rule.point is not None


def test_pick_most_severe_article() -> None:
    low = SanctionRule(article="a", point=None, severity="3", severity_coef=100.0, is_offense=False, codification="", is_negligent=False)
    high = SanctionRule(article="b", point=None, severity="4", severity_coef=200.0, is_offense=False, codification="", is_negligent=False)
    top = _pick_top_rule([low, high])
    assert top is high


def test_pick_most_severe_punishment() -> None:
    one = SanctionRule(article="a", point=None, severity="1", severity_coef=1, is_offense=False, codification="", is_negligent=False, allowed_main_punishments=["05", "06"])
    two = SanctionRule(article="b", point=None, severity="1", severity_coef=1, is_offense=False, codification="", is_negligent=False, allowed_main_punishments=["01"])
    assert _pick_top_punishment([one, two]) == "01"


def test_api_smoke_contract() -> None:
    payload = CalculateRequest.model_validate({
        "lang": "ru",
        "person": {"gender": "1"},
        "crime": {
            "article": "99",
            "part": "2",
            "paragraph": "01",
            "crime_date": "2025-01-01",
        },
    })
    response = calculate(payload=payload, service=PunishmentService())
    data = response.model_dump()
    assert set(data.keys()) == {"lang", "structured"}
    assert "punishments" in data["structured"]
    assert "additional_punishments" in data["structured"]
    assert "meta" in data["structured"]
