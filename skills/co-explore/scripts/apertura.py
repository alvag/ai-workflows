"""Extracts one entry without opening the complete detail artifact.

This descriptive docstring has no historical predicate span.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("USO:apertura detail requested_id", file=sys.stderr)
        return 2
    try:
        lineas = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        lineas = []
    objetivo = f"### {sys.argv[2]}"
    salida = []
    dentro = False
    for linea in lineas:
        if linea == objetivo:
            dentro = True
        elif dentro and linea.startswith("### "):
            break
        if dentro:
            salida.append(linea)
    if salida:
        print("\n".join(salida))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
