"""Predicado: la Fase 3 revalida la versión vigente del contrato antes de ejecutar evidencia y nunca
agrega ni quita IDs —la invariancia del conjunto entre versiones la hace cumplir el bloque
`orchestration-contract`; acá se comprueba que el documento lo declare así y no como un
congelado de la Fase 3—, y la agregación no puede dar verde con filas ausentes o BLOCKED."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("ARNES:gate-fase-3 argumentos invalidos", file=sys.stderr)
        return 99
    skill = Path(sys.argv[1])
    if not skill.is_file():
        print(f"ARNES:no existe {skill}", file=sys.stderr)
        return 99
    texto = skill.read_text(encoding="utf-8")
    rc = 0
    if "Gate de apertura del contrato de integración" not in texto:
        print("GUARD:gate-fase-3 sin-gate-de-apertura", file=sys.stderr)
        print("  la Fase 3 no declara el gate previo a ejecutar evidencia", file=sys.stderr)
        rc = 1
    if "revalida la versión vigente" not in texto or "Congelarlo **antes**" in texto:
        print("GUARD:gate-fase-3 no-revalida-version-vigente", file=sys.stderr)
        print("  la Fase 3 no declara que revalida la versión vigente del contrato antes de ejecutar evidencia", file=sys.stderr)
        rc = 1
    if "no verificado" not in texto:
        print("GUARD:gate-fase-3 sin-veredicto-no-verificado", file=sys.stderr)
        print("  la agregación no declara que una fila ausente impide el verde", file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
