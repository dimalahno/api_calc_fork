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


def _format_range(min_v: float, max_v: float, with_year_suffix: bool = False) -> str:
    min_exists = min_v > 0
    max_exists = max_v > 0
    min_txt = f"{min_v:g}"
    max_txt = f"{max_v:g}"
    suffix = " лет" if with_year_suffix else ""

    if min_exists and max_exists:
        return f"от {min_txt} до {max_txt}{suffix}"
    if max_exists:
        return f"до {max_txt}{suffix}"
    if min_exists:
        return f"от {min_txt}{suffix}"
    return "предусмотрено"


def _extract_ymd(years_value: float) -> tuple[int, int, int]:
    if years_value <= 0:
        return 0, 0, 0
    return int(years_value), 0, 0


def _extract_sanction(article: ArticleRecord) -> Dict[str, Any]:
    main_codes = _codes_list(article.fs1r64)
    nn_codes = _codes_list(article.fs1r64_nn)
    all_main_codes = list(dict.fromkeys(main_codes + nn_codes))

    main_ranges = {
        "05": {"min": _parse_number(article.fs1r64_05n), "max": _parse_number(article.fs1r64_05x)},
        "06": {"min": _parse_number(article.fs1r64_06n), "max": _parse_number(article.fs1r64_06x)},
        "09": {"min": _parse_number(article.fs1r64_09n), "max": _parse_number(article.fs1r64_09x)},
        "11": {"min": _parse_number(article.fs1r64_11n), "max": _parse_number(article.fs1r64_11x)},
        "12": {"min": _parse_number(article.fs1r64_12n), "max": _parse_number(article.fs1r64_12x)},
        "01": {"min": _parse_number(article.fs1r64_01n), "max": _parse_number(article.fs1r64_01x)},
    }

    additional_optional_codes = _codes_list(article.fs1r65_o)
    additional_required_codes = _codes_list(article.fs1r65_n)

    return {
        "article_code": article.article_code,
        "hard": article.hard,
        "koef_hard": article.koef_hard,
        "prest": article.prest,
        "main_codes": all_main_codes,
        "main_ranges": main_ranges,
        "additional_required_codes": additional_required_codes,
        "additional_optional_codes": additional_optional_codes,
        "additional_ranges": {
            "02": {"min": _parse_number(article.fs1r65_02n), "max": _parse_number(article.fs1r65_02x)}
        },
    }


def _build_calculated_sanction(
    sanction: Dict[str, Any],
    payload: Dict[str, Any],
    episode: Dict[str, Any],
) -> Dict[str, Any]:
    # payload и episode намеренно приняты, чтобы позже наращивать правила (по мотивам count_srok).
    _ = payload
    _ = episode

    main_codes = set(sanction.get("main_codes", []))
    main_ranges = sanction.get("main_ranges", {})
    calculated_main: Dict[str, Dict[str, Any]] = {}
    for code in ("05", "06", "09", "11", "12", "01", "02", "03"):
        range_info = main_ranges.get(code, {})
        min_v = float(range_info.get("min", 0) or 0)
        max_v = float(range_info.get("max", 0) or 0)
        is_applicable = code in main_codes
        item = {
            "is_applicable": is_applicable,
            "min_value": min_v,
            "max_value": max_v,
            "formatted_text": _format_range(min_v, max_v),
        }
        if code in {"11", "01"}:
            min_y, min_m, min_d = _extract_ymd(min_v)
            max_y, max_m, max_d = _extract_ymd(max_v)
            item.update(
                {
                    "min_years": min_y,
                    "min_months": min_m,
                    "min_days": min_d,
                    "max_years": max_y,
                    "max_months": max_m,
                    "max_days": max_d,
                }
            )
        calculated_main[code] = item

    optional_codes = set(sanction.get("additional_optional_codes", []))
    required_codes = set(sanction.get("additional_required_codes", []))
    additional_ranges = sanction.get("additional_ranges", {})

    calculated_additional: Dict[str, Dict[str, Any]] = {}
    for code in ("01", "04", "22", "02", "05"):
        is_applicable = code in optional_codes or code in required_codes
        is_mandatory = code in required_codes
        min_v = max_v = 0.0
        if code == "02":
            min_v = float(additional_ranges.get("02", {}).get("min", 0) or 0)
            max_v = float(additional_ranges.get("02", {}).get("max", 0) or 0)
            text = _format_range(min_v, max_v, with_year_suffix=True)
        else:
            text = "предусмотрено"

        calculated_additional[code] = {
            "is_applicable": is_applicable,
            "is_mandatory": is_mandatory,
            "formatted_text": text if is_applicable else "",
            "min_years": int(min_v) if code == "02" else 0,
            "max_years": int(max_v) if code == "02" else 0,
        }

    return {
        "article_code": sanction.get("article_code", ""),
        "hard": sanction.get("hard", ""),
        "koef_hard": sanction.get("koef_hard", ""),
        "prest": sanction.get("prest", ""),
        "main": calculated_main,
        "additional": calculated_additional,
    }


def _apply_main_punishments(a_nakaz: List[List[Any]], calculated: Dict[str, Any]) -> str:
    selected_code = ""
    selected_weight = -1
    main = calculated.get("main", {})

    for code in ("05", "06", "09", "11", "12", "01", "02"):
        row = PUNISHMENT_ROW_BY_CODE.get(code)
        if row is None:
            continue
        item = main.get(code, {})
        if not item.get("is_applicable", False):
            continue

        a_nakaz[row][0] = True
        a_nakaz[row][1] = item.get("min_value", 0)
        a_nakaz[row][2] = item.get("max_value", 0)
        a_nakaz[row][3] = item.get("formatted_text", "предусмотрено")
        if row in (3, 5):
            a_nakaz[row][4] = int(item.get("min_years", 0) or 0)
            a_nakaz[row][5] = int(item.get("min_months", 0) or 0)
            a_nakaz[row][6] = int(item.get("min_days", 0) or 0)
            a_nakaz[row][7] = int(item.get("max_years", 0) or 0)
            a_nakaz[row][8] = int(item.get("max_months", 0) or 0)
            a_nakaz[row][9] = int(item.get("max_days", 0) or 0)

        weight = PUNISHMENT_WEIGHT.get(code, 0)
        if weight > selected_weight:
            selected_weight = weight
            selected_code = code

    if selected_code == "01" and main.get("03", {}).get("is_applicable"):
        a_nakaz[PUNISHMENT_ROW_BY_CODE["01"]][3] = "предусмотрено (возможно пожизненное)"
    return selected_code


def _apply_additional_punishments(a_nakaz: List[List[Any]], calculated: Dict[str, Any]) -> None:
    additional = calculated.get("additional", {})

    confiscation = additional.get("01", {})
    if confiscation.get("is_applicable"):
        a_nakaz[7][0] = True
        a_nakaz[7][1] = bool(confiscation.get("is_mandatory"))
        a_nakaz[7][3] = confiscation.get("formatted_text", "предусмотрено")

    deportation = additional.get("04", {})
    if deportation.get("is_applicable"):
        a_nakaz[8][0] = True
        a_nakaz[8][1] = bool(deportation.get("is_mandatory"))
        a_nakaz[8][3] = deportation.get("formatted_text", "предусмотрено")

    lifetime_prohibition = additional.get("22", {})
    if lifetime_prohibition.get("is_applicable"):
        a_nakaz[9][0] = True
        a_nakaz[9][1] = bool(lifetime_prohibition.get("is_mandatory"))
        a_nakaz[9][3] = lifetime_prohibition.get("formatted_text", "предусмотрено")

    prohibition_term = additional.get("02", {})
    if prohibition_term.get("is_applicable"):
        a_nakaz[10][0] = True
        a_nakaz[10][1] = bool(prohibition_term.get("is_mandatory"))
        a_nakaz[10][4] = int(prohibition_term.get("min_years", 0) or 0)
        a_nakaz[10][5] = int(prohibition_term.get("max_years", 0) or 0)
        a_nakaz[10][3] = prohibition_term.get("formatted_text", "предусмотрено")

    deprivation = additional.get("05", {})
    if deprivation.get("is_applicable"):
        a_nakaz[11][0] = True
        a_nakaz[11][1] = bool(deprivation.get("is_mandatory"))
        a_nakaz[11][3] = deprivation.get("formatted_text", "предусмотрено")


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
    selected_episode = next(
        (
            ep
            for ep in episodes
            if isinstance(ep, dict)
            and _resolve_article_code(ep.get("article_code"), ep.get("article"), ep.get("part"), ep.get("paragraph"))
            == selected_article.article_code
        ),
        crime if isinstance(crime, dict) else {},
    )
    sanction = _extract_sanction(selected_article)
    calculated = _build_calculated_sanction(sanction, payload, selected_episode)
    selected_punishment = _apply_main_punishments(a_nakaz, calculated)
    _apply_additional_punishments(a_nakaz, calculated)

    structured = _build_structured(a_nakaz)
    structured["meta"] = {
        "reference_found": True,
        "reason": "ok",
        "selected_article_code": selected_article.article_code,
        "selected_article_hard": selected_article.hard,
        "selected_main_punishment": selected_punishment,
        "sanction_source": "count_srok_simplified",
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
