"""Predicado: todo AC declarado en el plan tiene al menos una fila del contrato que lo cita, y toda
fila cita un AC declarado. Las dos direcciones se reportan por separado."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _tabla import parsear_tabla_pipe


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:cobertura-ac-fila plan", file=sys.stderr)
        return 2
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        texto = ""
    declarados = set(re.findall(r"^- \*\*(AC-[0-9a-z]+)", texto, re.MULTILINE))
    citados = {
        fila[1].split()[0]
        for fila in parsear_tabla_pipe(texto)
        if len(fila) >= 2 and fila[0] != "ID" and fila[1].strip()
    }
    rc = 0
    faltan = sorted(declarados - citados)
    sobran = sorted(citados - declarados)
    if faltan:
        print(f"GUARD:cobertura-ac-fila AC sin fila: {' '.join(faltan)} ", file=sys.stderr)
        rc = 1
    if sobran:
        print(f"GUARD:cobertura-ac-fila fila sin AC declarado: {' '.join(sobran)} ", file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
