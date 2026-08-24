"""Predicado: ninguna fila queda en BLOCKED al despachar, y ninguna justificación de NOT_APPLICABLE
alega indisponibilidad del entorno."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Tuple

from _tabla import parsear_tabla_pipe


AMBIENTE = re.compile(r"no hay entorno|no disponible|sin acceso|no tengo|falta el|no está instalad|no se pudo instalar", re.IGNORECASE)


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
        print("USO:gate-blocked contract log", file=sys.stderr)
        return 2
    try:
        vigente = version_vigente(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        vigente = ""
    try:
        bitacora = Path(sys.argv[2]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        bitacora = ""
    filas = [fila for fila in parsear_tabla_pipe(vigente) if len(fila) == 6 and fila[0] != "ID"]
    rc = 0
    bloqueadas = [f"  {fila[0]}" for fila in filas if fila[5] == "BLOCKED"]
    if bloqueadas and "`paso: despachar`" in bitacora:
        print("GUARD:blocked-no-despacha hay filas BLOCKED y la bitácora despacha igual:", file=sys.stderr)
        print("\n".join(bloqueadas), file=sys.stderr)
        rc = 1
    registros = [linea for linea in vigente.splitlines() if re.match(r"^- `id: ", linea) and AMBIENTE.search(linea)]
    if registros:
        print("GUARD:blocked-no-despacha NOT_APPLICABLE justificado por el entorno:", file=sys.stderr)
        print("\n".join(registros), file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
