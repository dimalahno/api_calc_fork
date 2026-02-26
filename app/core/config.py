from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent

model_config = SettingsConfigDict(
    env_file=str(BASE_DIR / ".env"),
    env_file_encoding="utf-8"
)

# @dataclass(frozen=True)
# class Settings:
#     api_title: str
#     api_version: str
#     reference_file_path: str
#     APP_HOST: str
#     APP_PORT: int
#     DEBUG_MODE: bool

# @lru_cache
# def get_settings() -> Settings:
#     default_reference_path = str(
#         Path(__file__).resolve().parents[2] / "справочник_УК_обновленный_2025_06_07_1.txt"
#     )
#     return Settings(
#         api_title=os.getenv("API_TITLE", "Punishment API"),
#         api_version=os.getenv("API_VERSION", "0.1.0"),
#         reference_file_path=os.getenv("REFERENCE_FILE_PATH", default_reference_path),
#         APP_HOST=os.getenv("APP_HOST", "127.0.0.1"),
#         APP_PORT=int(os.getenv("APP_PORT", 8000)),
#         DEBUG_MODE=os.getenv("DEBUG_MODE", "True").lower() in ("true", "1", "yes"),
#     )

class Settings(BaseSettings):
    api_title: str = "Punishment API"
    api_version: str = "0.1.0"
    reference_file_path: str = str(
        Path(__file__).resolve().parents[2] / "справочник_УК_обновленный_2025_06_07_1.txt"
    )
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DEBUG_MODE: bool = True

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8"
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
