"""Predicado: tras un recovery-required no hay ningún retry ni fallback registrado hasta que el
recurso original se resuelve."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:recovery-bloquea log", file=sys.stderr)
        return 2
    try:
        lineas = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        lineas = []
    recovery = next((indice for indice, linea in enumerate(lineas) if "recovery-required" in linea), None)
    if recovery is None:
        return 0
    resuelto = next((indice for indice, linea in enumerate(lineas) if "`recurso: resuelto`" in linea), len(lineas))
    posteriores = [
        f"{indice + 1}: {linea}"
        for indice, linea in enumerate(lineas)
        if recovery < indice < resuelto and ("`semanticAttempt:" in linea or "`transportAttempt:" in linea)
    ]
    if posteriores:
        print("GUARD:recovery-bloquea hubo reintento con el recurso sin resolver:", file=sys.stderr)
        print("\n".join(posteriores), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
