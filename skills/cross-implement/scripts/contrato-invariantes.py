"""Predicado: entre versiones consecutivas el conjunto de ID no cambia, y para cada ID tampoco
cambian Requisito ni Esperado. Se comparan POR ID, nunca por posición."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from _tabla import parsear_tabla_pipe


def versiones(texto: str) -> List[Tuple[int, str]]:
    lineas = texto.splitlines()
    halladas: List[Tuple[int, str]] = []
    cerca = False
    for indice, linea in enumerate(lineas):
        if linea.startswith("```"):
            cerca = not cerca
        match = None if cerca else re.fullmatch(r"(#+) v(\d+)", linea)
        if not match:
            continue
        nivel = len(match.group(1))
        cuerpo: List[str] = []
        interna = False
        for siguiente in lineas[indice + 1 :]:
            if siguiente.startswith("```"):
                interna = not interna
            encabezado = re.match(r"^(#+) ", siguiente) if not interna else None
            if encabezado and len(encabezado.group(1)) <= nivel:
                break
            cuerpo.append(siguiente)
        halladas.append((int(match.group(2)), "\n".join(cuerpo)))
    return sorted(halladas)


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:contrato-invariantes contract", file=sys.stderr)
        return 2
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        texto = ""
    datos: List[Tuple[int, Dict[str, Tuple[str, str]]]] = []
    for numero, cuerpo in versiones(texto):
        filas = {}
        for fila in parsear_tabla_pipe(cuerpo):
            if len(fila) == 6 and fila[0] != "ID":
                filas[fila[0]] = (fila[1], fila[4])
        datos.append((numero, filas))
    rc = 0
    for (anterior, filas_a), (actual, filas_b) in zip(datos, datos[1:]):
        if sorted(filas_a) != sorted(filas_b):
            print(f"GUARD:ids-invariantes el conjunto de ID cambia entre v{anterior} y v{actual}", file=sys.stderr)
            rc = 1
        cambios = sorted(
            identificador
            for identificador in filas_a.keys() & filas_b.keys()
            if filas_a[identificador] != filas_b[identificador]
        )
        if cambios:
            print(f"GUARD:requisito-esperado-invariantes cambian entre v{anterior} y v{actual}:", file=sys.stderr)
            print("\n".join(f"  {identificador}" for identificador in cambios), file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
