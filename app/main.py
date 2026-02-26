from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    fastapi_app = FastAPI(title=settings.api_title, version=settings.api_version)
    fastapi_app.include_router(v1_router)
    return fastapi_app


app = create_app()
