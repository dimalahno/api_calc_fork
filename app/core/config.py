from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    api_title: str
    api_version: str
    reference_file_path: str


@lru_cache
def get_settings() -> Settings:
    default_reference_path = str(
        Path(__file__).resolve().parents[2] / "справочник_УК_обновленный_2025_06_07_1.txt"
    )
    return Settings(
        api_title=os.getenv("API_TITLE", "Punishment API"),
        api_version=os.getenv("API_VERSION", "0.1.0"),
        reference_file_path=os.getenv("REFERENCE_FILE_PATH", default_reference_path),
    )
