"""Упрощённая оркестрация расчёта по CSV d_fe1r10p1 без полной FoxPro parity."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.i18n import normalize_lang, setlang
from app.infrastructure.loaders.reference_loader import ArticleRecord, get_reference_service

# Основано на рабочих FoxPro скриптах из каталога fox_pro_prg.
FOXPRO_SCRIPT_FILES = (
    "log_proc_20260414_new_q.txt",
    "log_proc_smgr_20260414_new_q.txt",
    "log_proc_smgr_rtf_20260414_new_q.txt",
)

PUNISHMENT_ROW_BY_CODE = {
    "05": 0,
    "06": 1,
    "09": 2,
    "11": 3,
    "12": 4,
    "01": 5,
    "02": 6,
}

PUNISHMENT_WEIGHT = {
    "02": 70,
    "01": 60,
    "11": 50,
    "12": 40,
    "09": 30,
    "06": 20,
    "05": 10,
}


def _build_code(article: str, part: str | None, paragraph: str | None) -> str:
    art = str(article).strip()
    if not art:
        return ""

    import re

    m = re.match(r"^(\d+)(?:-(\d+))?$", art)
    if m:
        art_num = m.group(1)
        sub_art = m.group(2) or "0"
    else:
        art_num = art
        sub_art = "0"

    pt = str(part).strip() if part else "01"
    return f"{art_num.zfill(3)}{sub_art.zfill(2)}{pt.zfill(2)}"


def _resolve_article_code(article_code: str | None, article: str | None, part: str | None, paragraph: str | None) -> str:
    if article_code:
        code = str(article_code).strip()
        if code.isdigit():
            if len(code) in (5, 7):
                return code
            return code.zfill(7)
    if article and part:
        return _build_code(article, part, paragraph)
    return ""


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return None


def _parse_number(value: str) -> float:
    txt = (value or "").strip().replace(",", ".")
    if not txt:
        return 0.0
    try:
        return float(txt)
    except ValueError:
        return 0.0


def _codes_list(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _row_field_names(code: str) -> tuple[str, str] | None:
    mapping = {
        "05": ("fs1r64_05n", "fs1r64_05x"),
        "06": ("fs1r64_06n", "fs1r64_06x"),
        "09": ("fs1r64_09n", "fs1r64_09x"),
        "11": ("fs1r64_11n", "fs1r64_11x"),
        "12": ("fs1r64_12n", "fs1r64_12x"),
        "01": ("fs1r64_01n", "fs1r64_01x"),
        "02": ("", ""),
    }
    return mapping.get(code)


def _scripts_used() -> list[str]:
    folder = Path(__file__).resolve().parents[3] / "fox_pro_prg"
    return [name for name in FOXPRO_SCRIPT_FILES if (folder / name).exists()]


def _select_strictest(records: list[ArticleRecord]) -> ArticleRecord:
    def score(record: ArticleRecord) -> tuple[float, float, float]:
        hard = float(record.hard or 0)
        koef = _parse_number(record.koef_hard)
        max_p = 0.0
        for code in _codes_list(record.fs1r64):
            max_p = max(max_p, PUNISHMENT_WEIGHT.get(code, 0))
        return hard, koef, max_p

    return max(records, key=score)


def _apply_main_punishments(a_nakaz: List[List[Any]], article: ArticleRecord) -> str:
    selected_code = ""
    selected_weight = -1

    for code in _codes_list(article.fs1r64):
        row = PUNISHMENT_ROW_BY_CODE.get(code)
        if row is None:
            continue

        a_nakaz[row][0] = True
        a_nakaz[row][3] = setlang(5265, "ru")

        field_names = _row_field_names(code)
        if field_names and field_names[0]:
            min_v = _parse_number(getattr(article, field_names[0], ""))
            max_v = _parse_number(getattr(article, field_names[1], ""))
            a_nakaz[row][1] = min_v
            a_nakaz[row][2] = max_v
            a_nakaz[row][3] = f"{min_v:g} - {max_v:g}" if max_v else f"{min_v:g}"
            if row in (3, 5):
                a_nakaz[row][4] = int(min_v)
                a_nakaz[row][7] = int(max_v)
        else:
            a_nakaz[row][3] = "предусмотрено"

        weight = PUNISHMENT_WEIGHT.get(code, 0)
        if weight > selected_weight:
            selected_weight = weight
            selected_code = code

    return selected_code


def _apply_additional_punishments(a_nakaz: List[List[Any]], article: ArticleRecord) -> None:
    opt_codes = set(_codes_list(article.fs1r65_o))
    mandatory_codes = set(_codes_list(article.fs1r65_n))

    # Конфискация
    if "01" in opt_codes or "01" in mandatory_codes:
        a_nakaz[7][0] = True
        a_nakaz[7][1] = "01" in mandatory_codes
        a_nakaz[7][3] = "предусмотрено"

    # Выдворение
    if "04" in opt_codes or "04" in mandatory_codes:
        a_nakaz[8][0] = True
        a_nakaz[8][1] = "04" in mandatory_codes
        a_nakaz[8][3] = "предусмотрено"

    # Пожизненный запрет
    if "02" in opt_codes or "02" in mandatory_codes:
        a_nakaz[9][0] = True
        a_nakaz[9][1] = "02" in mandatory_codes
        a_nakaz[9][3] = "предусмотрено"

    # Срочный запрет
    if "22" in opt_codes or "22" in mandatory_codes:
        a_nakaz[10][0] = True
        a_nakaz[10][1] = "22" in mandatory_codes
        a_nakaz[10][4] = int(_parse_number(article.fs1r65_02n))
        a_nakaz[10][5] = int(_parse_number(article.fs1r65_02x))
        a_nakaz[10][3] = f"{a_nakaz[10][4]} - {a_nakaz[10][5]}"

    # Лишение гражданства
    if "03" in opt_codes or "03" in mandatory_codes:
        a_nakaz[11][0] = True
        a_nakaz[11][1] = "03" in mandatory_codes
        a_nakaz[11][3] = "предусмотрено"


def calculate_from_json(payload: Dict[str, Any]) -> Tuple[List[List[Any]], Dict[str, Any]]:
    """Упрощённый расчёт: берём наиболее тяжкий эпизод и санкции по CSV."""
    lang = normalize_lang(payload.get("lang", "ru"))
    crime = payload.get("crime", {}) or {}
    calc_date = _parse_date(payload.get("calc_date")) or date.today()

    episodes = payload.get("episodes")
    if not isinstance(episodes, list) or not episodes:
        episodes = [crime]

    ref = get_reference_service()
    candidates: list[ArticleRecord] = []

    for ep in episodes:
        if not isinstance(ep, dict):
            continue
        ep_date = _parse_date(ep.get("crime_date")) or calc_date
        article_code = _resolve_article_code(ep.get("article_code"), ep.get("article"), ep.get("part"), ep.get("paragraph"))
        if not article_code:
            continue
        article = ref.get_by_code(article_code, ep_date)
        if article is not None:
            candidates.append(article)

    a_nakaz = [[False, 0, 0, "", 0, 0, 0, 0, 0, 0, 0, 0, 0] for _ in range(15)]
    for idx in range(7):
        a_nakaz[idx][3] = setlang(5265, lang)

    if not candidates:
        structured = {
            "punishments": {},
            "additional_punishments": {},
            "meta": {
                "reference_found": False,
                "reason": "article_not_found",
                "foxpro_scripts": _scripts_used(),
            },
        }
        return a_nakaz, structured

    selected_article = _select_strictest(candidates)
    selected_punishment = _apply_main_punishments(a_nakaz, selected_article)
    _apply_additional_punishments(a_nakaz, selected_article)

    structured = _build_structured(a_nakaz)
    structured["meta"] = {
        "reference_found": True,
        "reason": "ok",
        "selected_article_code": selected_article.article_code,
        "selected_article_hard": selected_article.hard,
        "selected_main_punishment": selected_punishment,
        "foxpro_scripts": _scripts_used(),
    }
    return a_nakaz, structured


def _build_structured(a_nakaz: List[List[Any]]) -> Dict[str, Any]:
    def item(row: int) -> Dict[str, Any]:
        r = a_nakaz[row]
        data = {
            "is_applicable": bool(r[0]),
            "min_value": r[1],
            "max_value": r[2],
            "formatted_text": r[3],
        }
        if row in (3, 5):
            data.update(
                {
                    "min_years": r[4],
                    "min_months": r[5],
                    "min_days": r[6],
                    "max_years": r[7],
                    "max_months": r[8],
                    "max_days": r[9],
                }
            )
        return data

    def add_item(row: int) -> Dict[str, Any]:
        r = a_nakaz[row]
        data = {
            "is_applicable": bool(r[0]),
            "is_mandatory": bool(r[1]),
            "formatted_text": r[3],
        }
        if row == 10:
            data.update({"min_years": r[4], "max_years": r[5]})
        return data

    punishments = {
        "fine": item(0),
        "corrective_work": item(1),
        "mandatory_work": item(2),
        "restriction_of_freedom": item(3),
        "arrest": item(4),
        "imprisonment": item(5),
        "death_penalty": item(6),
    }
    additional = {
        "confiscation": add_item(7),
        "deportation": add_item(8),
        "lifetime_prohibition": add_item(9),
        "prohibition_term": add_item(10),
        "deprivation_of_citizenship": add_item(11),
    }
    return {"punishments": punishments, "additional_punishments": additional}
