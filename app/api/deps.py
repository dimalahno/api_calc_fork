from __future__ import annotations

import os

from app.core.config import get_settings
from app.domain.services.punishment_service import PunishmentService
from services.punishment_api.reference_loader import get_reference_service


def get_reference():
    settings = get_settings()
    os.environ.setdefault("REFERENCE_FILE_PATH", settings.reference_file_path)
    return get_reference_service()


def get_punishment_service() -> PunishmentService:
    return PunishmentService()
