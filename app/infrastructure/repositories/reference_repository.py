from __future__ import annotations

from datetime import date

from app.infrastructure.loaders.reference_loader import ArticleRecord, ReferenceService


class ReferenceRepository:
    """Repository facade for article reference lookups."""

    def __init__(self, service: ReferenceService):
        self._service = service

    def get_by_code(self, code: str, crime_date: date) -> ArticleRecord | None:
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
