"""Separates raw output into index and detail, excluding the transport signal.

This descriptive docstring has no historical predicate span.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print("USO:split raw index detail", file=sys.stderr)
        return 2
    raw, index, detail = map(Path, sys.argv[1:])
    try:
        lineas = raw.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        lineas = []
    partes = {"index": [], "detail": []}
    modo = ""
    for linea in lineas:
        if linea.rstrip() == "## Índice":
            modo = "index"
            continue
        if linea.rstrip() == "## Detalle":
            modo = "detail"
            continue
        if linea.rstrip() == "STATUS: done":
            continue
        if modo:
            partes[modo].append(linea)
    index.write_text("".join(f"{linea}\n" for linea in partes["index"]), encoding="utf-8")
    detail.write_text("".join(f"{linea}\n" for linea in partes["detail"]), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
