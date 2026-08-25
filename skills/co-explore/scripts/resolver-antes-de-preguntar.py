"""Predicado: el conductor registra haber buscado la respuesta en el paquete y en el repositorio
antes de escalar la pregunta al usuario."""

from __future__ import annotations

import sys
from pathlib import Path


def primera(lineas: list[str], texto: str) -> int:
    return next((indice for indice, linea in enumerate(lineas, 1) if texto in linea), 0)


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:resolver-antes-de-preguntar log", file=sys.stderr)
        return 2
    try:
        lineas = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        lineas = []
    escalado = primera(lineas, "`paso: preguntar-al-usuario`")
    if not escalado:
        return 0
    rc = 0
    for paso in ("buscar-en-paquete", "buscar-en-repo"):
        numero = primera(lineas, f"`paso: {paso}`")
        if not numero:
            print(f'GUARD:resolver-antes-de-preguntar escaló sin registrar "{paso}"', file=sys.stderr)
            rc = 1
        elif numero > escalado:
            print(f'GUARD:resolver-antes-de-preguntar "{paso}" quedó DESPUÉS de escalar', file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
