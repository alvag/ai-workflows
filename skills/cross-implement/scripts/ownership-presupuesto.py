"""Predicado: ningún checkId excede el presupuesto de su clase — IMPLEMENTATION_DEFECT hasta
max_fix_rounds, VERIFICATION_DEFECT y ENVIRONMENT_FAILURE hasta 2, DESIGN_GAP una sola vez."""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from typing import List, Tuple


def entradas(texto: str) -> List[Tuple[str, str]]:
    resultado: List[Tuple[str, str]] = []
    dentro = False
    for linea in texto.splitlines():
        if linea == "Ownership:":
            dentro = True
            continue
        if dentro and (linea.startswith("## ") or not linea.strip()):
            dentro = False
        if not dentro:
            continue
        match = re.match(r"^- `checkId: ([^`]*)`.*`clase: ([^`]*)`", linea)
        if match:
            resultado.append((match.group(1), match.group(2)))
    return resultado


def main() -> int:
    if len(sys.argv) != 3:
        print("USO:ownership-presupuesto log max_fix_rounds", file=sys.stderr)
        return 2
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
        max_fix_rounds = int(sys.argv[2])
    except (OSError, UnicodeError, ValueError):
        texto, max_fix_rounds = "", 0
    excesos = []
    for (check_id, clase), cantidad in sorted(Counter(entradas(texto)).items()):
        tope = max_fix_rounds if clase == "IMPLEMENTATION_DEFECT" else 1 if clase == "DESIGN_GAP" else 2
        if cantidad > tope:
            excesos.append(f"  {check_id} · {clase} · {cantidad} > {tope}")
    if excesos:
        print("GUARD:presupuesto-por-check presupuesto excedido:", file=sys.stderr)
        print("\n".join(excesos), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
