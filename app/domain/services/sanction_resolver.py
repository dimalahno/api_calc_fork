"""Сервис поиска санкции для эпизода."""

from __future__ import annotations

from app.domain.models.calculation_context import EpisodeContext
from app.domain.models.sanction_rule import SanctionRule
from app.infrastructure.repositories.reference_repository import ReferenceRepository


class SanctionResolver:
    """Извлекает статью/пункт из эпизода и возвращает правило санкции."""

    def __init__(self, repository: ReferenceRepository):
        self._repository = repository

    def resolve(self, episode: EpisodeContext) -> SanctionRule | None:
        if not episode.article:
            return None
        return self._repository.get_rule(
            article=episode.article,
            point=episode.point,
            event_date=episode.event_date,
        )
