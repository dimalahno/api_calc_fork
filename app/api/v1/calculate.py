from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services.punishment_api.calculator import calculate_from_json
from services.punishment_api.localization import normalize_lang
from services.punishment_api.schemas import CalculateRequest, CalculateResponse

router = APIRouter()


@router.post("/calculate", response_model=CalculateResponse)
def calculate(payload: CalculateRequest) -> CalculateResponse:
    lang = normalize_lang(payload.lang)
    if lang != "ru":
        raise HTTPException(status_code=400, detail="Only 'ru' is supported for now")

    if hasattr(payload, "model_dump"):
        data = payload.model_dump()
    else:
        data = payload.dict()

    a_nakaz, structured = calculate_from_json(data)

    return CalculateResponse(
        lang=lang,
        aNakaz=a_nakaz,
        structured=structured,
    )
