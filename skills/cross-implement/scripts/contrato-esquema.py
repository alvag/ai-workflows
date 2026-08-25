"""Predicado: la tabla tiene las seis columnas normativas, en ese orden, y todo valor de Evidencia y
de Baseline cae dentro de su enum cerrado."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Tuple

from _tabla import parsear_tabla_pipe


CABECERA = "| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |"


def secciones(texto: str) -> List[Tuple[int, List[str]]]:
    lineas = texto.splitlines()
    resultado: List[Tuple[int, List[str]]] = []
    cerca = False
    for indice, linea in enumerate(lineas):
        if linea.startswith("```"):
            cerca = not cerca
        match = None if cerca else re.fullmatch(r"(#+) v(\d+)", linea)
        if not match:
            continue
        nivel = len(match.group(1))
        cuerpo: List[str] = []
        dentro = False
        for siguiente in lineas[indice + 1 :]:
            if siguiente.startswith("```"):
                dentro = not dentro
            encabezado = re.match(r"^(#+) ", siguiente) if not dentro else None
            if encabezado and len(encabezado.group(1)) <= nivel:
                break
            cuerpo.append(siguiente)
        resultado.append((int(match.group(2)), cuerpo))
    return resultado


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:contrato-esquema contract", file=sys.stderr)
        return 2
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        texto = ""
    disponibles = secciones(texto)
    cuerpo = "\n".join(max(disponibles, default=(0, []), key=lambda item: item[0])[1])
    filas = [fila for fila in parsear_tabla_pipe(cuerpo) if fila and fila[0] != "ID"]
    rc = 0
    if CABECERA not in cuerpo.splitlines():
        print("GUARD:esquema-tabla cabecera no normativa", file=sys.stderr)
        rc = 1
    errores = [f"   {fila[0] if fila else ''} : {len(fila)} columnas" for fila in filas if len(fila) != 6]
    if errores:
        print("GUARD:esquema-tabla columnas fuera del esquema", file=sys.stderr)
        print("\n".join(errores), file=sys.stderr)
        rc = 1
    errores = [f"   {fila[0]} : Evidencia={fila[2]}" for fila in filas if len(fila) == 6 and fila[2] not in {"test", "build", "inspección", "manual"}]
    if errores:
        print("GUARD:esquema-tabla enum de Evidencia", file=sys.stderr)
        print("\n".join(errores), file=sys.stderr)
        rc = 1
    errores = [f"   {fila[0]} : Baseline={fila[5]}" for fila in filas if len(fila) == 6 and fila[5] not in {"RED", "GREEN_ALREADY", "NOT_APPLICABLE", "BLOCKED"}]
    if errores:
        print("GUARD:esquema-tabla enum de Baseline", file=sys.stderr)
        print("\n".join(errores), file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
