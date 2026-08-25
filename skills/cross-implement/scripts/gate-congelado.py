"""Predicado: hay contrato, su tabla no tiene ninguna fila con baseline sin resolver, y la bitácora
registra el congelamiento antes del despacho."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Tuple

from _tabla import parsear_tabla_pipe


def version_vigente(texto: str) -> str:
    lineas = texto.splitlines()
    versiones: List[Tuple[int, int, int]] = []
    cerca = False
    for indice, linea in enumerate(lineas):
        if linea.startswith("```"):
            cerca = not cerca
        match = None if cerca else re.fullmatch(r"(#+) v(\d+)", linea)
        if match:
            versiones.append((int(match.group(2)), indice, len(match.group(1))))
    if not versiones:
        return ""
    _, inicio, nivel = max(versiones)
    cuerpo: List[str] = []
    cerca = False
    for linea in lineas[inicio + 1 :]:
        if linea.startswith("```"):
            cerca = not cerca
        encabezado = re.match(r"^(#+) ", linea) if not cerca else None
        if encabezado and len(encabezado.group(1)) <= nivel:
            break
        cuerpo.append(linea)
    return "\n".join(cuerpo)


def main() -> int:
    if len(sys.argv) != 3:
        print("USO:gate-congelado contract log", file=sys.stderr)
        return 2
    try:
        contrato = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        contrato = ""
    try:
        bitacora = Path(sys.argv[2]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        bitacora = ""
    filas = [fila for fila in parsear_tabla_pipe(version_vigente(contrato)) if len(fila) == 6 and fila[0] != "ID"]
    rc = 0
    if not filas:
        print("GUARD:gate-contrato-congelado el work order no trae tabla", file=sys.stderr)
        rc = 1
    sin_resolver = [f"  {fila[0]}" for fila in filas if fila[5] in {"", "BLOCKED"}]
    if sin_resolver:
        print("GUARD:gate-contrato-congelado baseline sin resolver:", file=sys.stderr)
        print("\n".join(sin_resolver), file=sys.stderr)
        rc = 1
    if "`paso: congelar`" not in bitacora:
        print("GUARD:gate-contrato-congelado la bitácora no registra el congelamiento", file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
