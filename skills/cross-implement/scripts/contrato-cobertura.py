"""Predicado: todo requisito en alcance tiene al menos una fila, y toda fila referencia un requisito
en alcance. Las dos direcciones se reportan por separado."""

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
        print("USO:contrato-cobertura contract requirements", file=sys.stderr)
        return 2
    try:
        contrato = Path(sys.argv[1]).read_text(encoding="utf-8")
        alcance = set(Path(sys.argv[2]).read_text(encoding="utf-8").splitlines())
    except (OSError, UnicodeError):
        contrato, alcance = "", set()
    citados = {
        fila[1].split()[0]
        for fila in parsear_tabla_pipe(version_vigente(contrato))
        if len(fila) >= 2 and fila[0] != "ID" and fila[1]
    }
    rc = 0
    faltan = sorted(alcance - citados)
    sobran = sorted(citados - alcance)
    if faltan:
        print(f"GUARD:cobertura-bidireccional requisito en alcance sin fila: {' '.join(faltan)} ", file=sys.stderr)
        rc = 1
    if sobran:
        print(f"GUARD:cobertura-bidireccional fila sin requisito en alcance: {' '.join(sobran)} ", file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
