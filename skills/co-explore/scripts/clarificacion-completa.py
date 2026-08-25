"""Predicado: un clarification-needed trae pregunta, impacto y el índice y detalle de lo que alcanzó
a mapear; el supuesto seguro es opcional pero, si falta, se declara que no hay."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:clarificacion-completa report", file=sys.stderr)
        return 2
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        texto = ""
    rc = 0
    for campo in ("pregunta:", "impacto:", "supuesto-seguro:"):
        if not re.search(rf"^{re.escape(campo)}[ \t]*\S", texto, re.MULTILINE):
            print(f'GUARD:clarification-completa falta o está vacío el campo "{campo}"', file=sys.stderr)
            rc = 1
    if not re.search(r"^## Índice", texto, re.MULTILINE):
        print("GUARD:clarification-completa no entrega el índice de lo mapeado", file=sys.stderr)
        rc = 1
    if not re.search(r"^## Detalle", texto, re.MULTILINE):
        print("GUARD:clarification-completa no entrega el detalle de lo mapeado", file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
