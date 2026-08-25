"""Predicado: toda materialización del contrato usa la MISMA cabecera normativa de seis columnas;
no existe una segunda forma de tabla haciéndose pasar por contrato."""

from __future__ import annotations

import sys
from pathlib import Path

from _tabla import parsear_tabla_pipe


CABECERA = "| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |"


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:materializacion-contrato plan", file=sys.stderr)
        return 2
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        texto = ""
    rc = 0
    if CABECERA not in texto.splitlines():
        print("GUARD:materializacion-unica el plan no materializa la cabecera normativa", file=sys.stderr)
        rc = 1
    dialectos = []
    for cruda in texto.splitlines():
        linea = cruda.strip()
        celdas = parsear_tabla_pipe(linea)
        if celdas and celdas[0][0] == "ID" and linea != CABECERA:
            dialectos.append(linea)
    if dialectos:
        print("GUARD:materializacion-unica hay una tabla de contrato con otro esquema:", file=sys.stderr)
        print("\n".join(dialectos), file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
