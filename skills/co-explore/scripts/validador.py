"""Validates form, uniqueness, and index/detail parity.

This descriptive docstring has no historical predicate span.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

from _tabla import parsear_tabla_pipe


ID = re.compile(r"[A-Z]{3}-[A-Z]-[A-Z]{3}-[0-9]{3}")


def main() -> int:
    if len(sys.argv) != 6:
        print("USO:validador index detail family role mode", file=sys.stderr)
        return 2
    index_path, detail_path = map(Path, sys.argv[1:3])
    familia, rol, modo = sys.argv[3:]
    try:
        index = index_path.read_text(encoding="utf-8")
        detail = detail_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return 1
    with tempfile.TemporaryDirectory():
        filas = [fila for fila in parsear_tabla_pipe(index) if fila and fila[0] != "ID"]
        headings = [linea for linea in detail.splitlines() if linea.startswith("### ")]
        previo = []
        for linea in detail.splitlines():
            if linea.startswith("### "):
                break
            if linea.strip():
                previo.append(linea)
        if previo:
            return 1
        ids_index = [fila[0] for fila in filas if ID.fullmatch(fila[0])]
        ids_detail = [linea[4:].strip() for linea in headings if ID.fullmatch(linea[4:].strip())]
        if len(ids_index) != len(filas) or len(ids_detail) != len(headings):
            return 1
        esperado = re.compile(rf"{re.escape(familia)}-{re.escape(rol)}-{re.escape(modo)}-[0-9]{{3}}")
        if any(not esperado.fullmatch(item) for item in ids_index + ids_detail):
            return 1
        if not ids_index:
            return 1
        for fila in filas:
            if len(fila) != 5 or fila[2] not in {"high", "medium", "low"} or fila[3] not in {"high", "medium", "low"}:
                return 1
            if not re.fullmatch(r"(?:[^ :]+:[0-9]+)(?:\s*,\s*[^ :]+:[0-9]+)*|N/A: .+", fila[4]):
                return 1
        if len(ids_index) != len(set(ids_index)) or len(ids_detail) != len(set(ids_detail)):
            return 1
        return 0 if sorted(ids_index) == sorted(ids_detail) else 1


if __name__ == "__main__":
    raise SystemExit(main())
