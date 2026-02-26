from __future__ import annotations

import os
import sys
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Iterable

# ВАЖНО:
# положите этот скрипт рядом с reference_loader.py или поправьте sys.path ниже.
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from reference_loader import get_reference_service  # noqa: E402


REPLACEMENT_CHAR = "\ufffd"


def _has_replacement_char(value: str) -> bool:
    return REPLACEMENT_CHAR in value


def _iter_all_records(service) -> Iterable[tuple[str, object]]:
    # service._records: dict[str, list[ArticleRecord]]
    # Используем напрямую для отладки.
    for code, recs in service._records.items():
        for rec in recs:
            yield code, rec


def main() -> None:
    # 1) Явно задайте путь к справочнику через env (удобно для отладки)
    os.environ["REFERENCE_FILE_PATH"] = r"../../справочник_УК_обновленный_2025_06_07_1.txt"
    os.environ["DEBUG_CODE"] = r"99"

    svc = get_reference_service()
    svc._ensure_loaded()  # на всякий случай

    print("=== ReferenceService debug ===")
    print(f"source: {svc.source}")
    print(f"file_path: {svc.file_path}")
    print(f"codes: {len(svc._records)}")
    print(f"records_total: {svc.count}")

    # 2) Топ кодов с максимальным количеством версий (d_izm)
    top = sorted(((k, len(v)) for k, v in svc._records.items()), key=lambda x: x[1], reverse=True)[:20]
    print("\n=== TOP codes by versions (top 20) ===")
    for code, cnt in top:
        print(f"{code:>12}  versions={cnt}")

    # 3) Пример: показать конкретный код (передайте через env)
    debug_code = os.environ.get("DEBUG_CODE", "").strip()
    if debug_code:
        recs = list(svc._records.get(debug_code, []))
        recs.sort(key=lambda r: (r.d_izm or date.min))
        print(f"\n=== Records for code={debug_code} (sorted by d_izm) ===")
        for i, r in enumerate(recs, 1):
            print(f"\n--- #{i} d_izm={r.d_izm} ---")
            # печатаем ключевые поля; добавьте при необходимости
            print(f"article_code={r.article_code}")
            print(f"hard={r.hard}")
            print(f"prest={r.prest}")
            print(f"fs1r64={r.fs1r64}")
            print(f"fs1r65_o={r.fs1r65_o}")
            print(f"fs1r65_n={r.fs1r65_n}")
            print(f"fl1u={r.fl1u}")

        # и как выбирается "актуальная" запись на дату преступления
        crime_date_str = os.environ.get("CRIME_DATE", "2026-02-25")
        y, m, d = map(int, crime_date_str.split("-"))
        chosen = svc.get_by_code(debug_code, date(y, m, d))
        print(f"\n=== get_by_code({debug_code}, {crime_date_str}) ===")
        print("chosen d_izm:", chosen.d_izm if chosen else None)

    # 4) Поиск проблемных символов U+FFFD ("�") по всем полям
    print("\n=== Scan for replacement char (U+FFFD) ===")
    bad_cells = 0
    bad_rows = 0
    for code, rec in _iter_all_records(svc):
        rec_dict = asdict(rec)
        row_has_bad = False
        for k, v in rec_dict.items():
            if isinstance(v, str) and _has_replacement_char(v):
                bad_cells += 1
                row_has_bad = True
        if row_has_bad:
            bad_rows += 1
    print(f"rows_with_ufffd: {bad_rows}")
    print(f"cells_with_ufffd: {bad_cells}")

    # 5) Проверка "ASCII-колонок": loader пытается их decode ascii/latin-1.
    # Если там вдруг кириллица/не-ASCII — подсветим.
    # (в вашем loader это все поля кроме 0,7,8 и строки заголовка)
    print("\n=== Scan for non-ASCII chars in 'ascii fields' ===")
    # берём заголовок из уже распарсенного файла невозможно (он уже нормализован),
    # поэтому ориентируемся по dataclass-полям.
    ascii_fields = {
        # те, которые НЕ 0/7/8 по логике loader и чаще всего цифро-кодовые
        "hard",
        "prest",
        "fs1r64",
        "fs1r64_nn",
        "fs1r64_05n",
        "fs1r64_05x",
        "fs1r64_06n",
        "fs1r64_06x",
        "fs1r64_09n",
        "fs1r64_09x",
        "fs1r64_12n",
        "fs1r64_12x",
        "fs1r64_11n",
        "fs1r64_11x",
        "fs1r64_01n",
        "fs1r64_01x",
        "fs1r65_o",
        "fs1r65_n",
        "fs1r65_02n",
        "fs1r65_02x",
        "fl1u",
    }
    non_ascii_hits = 0
    examples = []
    for code, rec in _iter_all_records(svc):
        rec_dict = asdict(rec)
        for k in ascii_fields:
            v = rec_dict.get(k, "")
            if isinstance(v, str) and any(ord(ch) > 127 for ch in v):
                non_ascii_hits += 1
                if len(examples) < 10:
                    examples.append((code, k, v))
    print(f"non_ascii_hits: {non_ascii_hits}")
    if examples:
        print("examples (up to 10):")
        for code, k, v in examples:
            print(f"  code={code} field={k} value={v!r}")

    # 6) (Опционально) Дамп первых N записей в JSON (удобно смотреть глазами/в IDE)
    dump_n = int(os.environ.get("DUMP_N", "0"))
    if dump_n > 0:
        out = []
        i = 0
        for code, rec in _iter_all_records(svc):
            out.append(asdict(rec))
            i += 1
            if i >= dump_n:
                break

        dump_path = Path(os.environ.get("DUMP_PATH", "reference_dump_sample.json")).resolve()
        dump_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n=== Dumped {dump_n} records to: {dump_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()