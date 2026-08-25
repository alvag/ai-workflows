"""Predicado: después de un DESIGN_GAP no hay ninguna ronda ni takeover posterior, y durante el
takeover la versión vigente del contrato no cambia."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:takeover-reglas log", file=sys.stderr)
        return 2
    try:
        lineas = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        lineas = []
    rc = 0
    gap = next((indice for indice, linea in enumerate(lineas) if "DESIGN_GAP" in linea), None)
    if gap is not None:
        posteriores = [f"{indice + 1}: {linea}" for indice, linea in enumerate(lineas) if indice > gap and (linea.startswith("## Ronda ") or linea.startswith("## Takeover"))]
        if posteriores:
            print("GUARD:design-gap-corta-takeover hay trabajo después del DESIGN_GAP:", file=sys.stderr)
            print("\n".join(posteriores), file=sys.stderr)
            rc = 1
    takeover = next((indice for indice, linea in enumerate(lineas) if linea.startswith("## Takeover")), None)
    if takeover is not None:
        antes = [match.group(1) for linea in lineas[:takeover] if (match := re.search(r"`contrato: (v\d+)`", linea))]
        durante = [match.group(1) for linea in lineas[takeover:] if (match := re.search(r"`contrato: (v\d+)`", linea))]
        if antes and durante and antes[-1] != durante[-1]:
            print(f"GUARD:takeover-no-ablanda el contrato pasó de {antes[-1]} a {durante[-1]} durante el takeover", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
