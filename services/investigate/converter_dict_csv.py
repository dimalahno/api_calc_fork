#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
from pathlib import Path


ENCODING_FIXES = {
    "8A:;NG5=0": "Исключена",
    "8A:;NG5=": "Исключен",
    "(8A:;NG5=0)": "(Исключена)",
    "(8A:;NG5=)": "(Исключен)",
}


def decode_stat_field(field: bytes) -> str:
    restored = bytearray()
    for b in field:
        if b == 0x20 or b == 0x2E or 0x30 <= b <= 0x39:
            restored.append(b)
        elif 0x21 <= b <= 0x7E:
            nb = (b + 0xB0) % 256
            if 0xC0 <= nb <= 0xFF or nb in (0xA8, 0xB8):
                restored.append(nb)
            else:
                restored.append(b)
        else:
            restored.append(b)

    return bytes(restored).decode("cp1251", errors="replace")


def decode_text_field(field: bytes) -> str:
    restored = bytearray()
    for b in field:
        if b in (0x20, 0x09, 0x0A, 0x0D):
            restored.append(b)
        else:
            restored.append((b + 0xB0) % 256)

    return bytes(restored).decode("cp1251", errors="replace")


def decode_field(field: bytes, field_idx: int, line_idx: int) -> str:
    if not field:
        return ""

    if line_idx == 0:
        return field.decode("ascii", errors="replace")

    if field_idx == 0:
        return decode_stat_field(field)

    if field_idx in {7, 8}:
        return decode_text_field(field)

    try:
        return field.decode("ascii")
    except UnicodeDecodeError:
        return field.decode("latin-1", errors="replace")


def convert_to_utf8_csv(src_path: Path, dst_path: Path) -> None:
    raw = src_path.read_bytes()
    lines = raw.split(b"\n")

    rows: list[list[str]] = []

    for line_idx, line in enumerate(lines):
        line = line.rstrip(b"\r")
        fields = line.split(b"\t")
        decoded = [decode_field(f, i, line_idx) for i, f in enumerate(fields)]
        rows.append(decoded)

    # применяем исправления
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            for broken, fixed in ENCODING_FIXES.items():
                value = value.replace(broken, fixed)
            row[j] = value

    # запись CSV с разделителем ;
    with open(dst_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(
            f,
            delimiter=";",
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL
        )
        writer.writerows(rows)


def main():
    src = Path("../../справочник_УК_обновленный_2025_06_07_1.txt")
    dst = Path("../../справочник_УК_обновленный_2025_06_07_1.utf8.csv")

    if not src.exists():
        raise SystemExit(f"Source not found: {src.resolve()}")

    convert_to_utf8_csv(src, dst)
    print(f"OK: {dst.resolve()}")


if __name__ == "__main__":
    main()