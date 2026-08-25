"""Predicado: el paso verify CARGA la fila declarada en vez de identificar evidencia en ese momento,
y revert-to-confirm sigue alcanzable."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:verify-ejecuta sdd_flow_skill", file=sys.stderr)
        return 2
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        texto = ""
    rc = 0
    if "**CARGAR**" not in texto:
        print("GUARD:verify-solo-ejecuta el paso verify no carga la fila del contrato", file=sys.stderr)
        rc = 1
    if "**IDENTIFICAR**" in texto:
        print("GUARD:verify-solo-ejecuta el paso verify sigue eligiendo evidencia (IDENTIFICAR)", file=sys.stderr)
        rc = 1
    if "revert-to-confirm" not in texto.lower():
        print("GUARD:verify-solo-ejecuta se perdió revert-to-confirm", file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
