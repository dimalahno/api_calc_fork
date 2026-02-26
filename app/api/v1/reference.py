from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_reference
from services.punishment_api.reference_loader import ReferenceService
from services.punishment_api.schemas import ReferenceStatusResponse

router = APIRouter()


@router.get("/reference/status", response_model=ReferenceStatusResponse)
def reference_status(ref: ReferenceService = Depends(get_reference)) -> ReferenceStatusResponse:
    return ReferenceStatusResponse(source=ref.source, count=ref.count, file_path=ref.file_path)


@router.post("/reference/reload")
def reference_reload(ref: ReferenceService = Depends(get_reference)) -> dict:
    ref.reload()
    return {"status": "reloaded", "count": ref.count, "source": ref.source}
