from __future__ import annotations

from services.punishment_api.reference_loader import ReferenceService


class TxtReferenceLoader:
    """Adapter around legacy TXT reference loader/service."""

    def __init__(self, file_path: str | None = None):
        self._service = ReferenceService(file_path=file_path)

    def service(self) -> ReferenceService:
        return self._service
