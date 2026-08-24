"""Predicado: cada línea de ownership trae checkId, clase válida, consumedRound y evidencia;
consumedRound es "sí" exactamente para IMPLEMENTATION_DEFECT; ningún delta se reparte entre
rondas; y desde la segunda aparición del mismo checkId la línea trae una razón que nombre un
observable."""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set


CLASES = {"IMPLEMENTATION_DEFECT", "VERIFICATION_DEFECT", "ENVIRONMENT_FAILURE", "DESIGN_GAP"}
GENERICO = re.compile(r"no cubrió|no cubrio|faltó manejar|falto manejar|no entendió|no entendio|algún borde|algun borde|no quedó bien|no quedo bien", re.IGNORECASE)


def valor(linea: str, campo: str) -> str:
    match = re.search(rf"`{campo}: ([^`]*)`", linea)
    return match.group(1) if match else ""


def lineas_ownership(texto: str) -> List[str]:
    resultado: List[str] = []
    dentro = False
    for linea in texto.splitlines():
        if linea == "Ownership:":
            dentro = True
            continue
        if dentro and (linea.startswith("## ") or not linea.strip()):
            dentro = False
        if dentro and linea.startswith("- `checkId: "):
            resultado.append(linea)
    return resultado


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:ownership-log log", file=sys.stderr)
        return 2
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        texto = ""
    lineas = lineas_ownership(texto)
    rc = 0
    apariciones: Dict[str, int] = defaultdict(int)
    for linea in lineas:
        check_id = valor(linea, "checkId")
        clase = valor(linea, "clase")
        consumida = valor(linea, "consumedRound")
        if clase not in CLASES:
            print(f'GUARD:log-clasificacion {check_id}: clase inválida "{clase}"', file=sys.stderr)
            rc = 1
        if not re.search(r"`evidencia: [^`]", linea):
            print(f"GUARD:log-clasificacion {check_id}: sin evidencia", file=sys.stderr)
            rc = 1
        esperado = "sí" if clase == "IMPLEMENTATION_DEFECT" else "no"
        if consumida != esperado:
            print(
                f'GUARD:log-clasificacion {check_id}: consumedRound="{consumida or "ausente"}" '
                f'y la clase {clase} exige "{esperado}"',
                file=sys.stderr,
            )
            rc = 1
        apariciones[check_id] += 1
        if apariciones[check_id] < 2:
            continue
        razon = valor(linea, "razón")
        if not razon:
            print(f"GUARD:razon-falsable {check_id}: aparición {apariciones[check_id]} sin razón registrada", file=sys.stderr)
            rc = 1
        elif GENERICO.search(razon):
            print(f"GUARD:razon-falsable {check_id}: la razón no nombra un observable que la refute", file=sys.stderr)
            rc = 1

    rondas: Dict[str, Set[int]] = defaultdict(set)
    ronda = 0
    for linea in texto.splitlines():
        if linea.startswith("## Ronda "):
            ronda += 1
        if linea.startswith("- `checkId: "):
            delta = valor(linea, "delta")
            if delta:
                rondas[delta].add(ronda)
    repartidos = [f"  {delta} en {len(indices)} rondas" for delta, indices in sorted(rondas.items()) if len(indices) > 1]
    if repartidos:
        print("GUARD:delta-una-ronda hay deltas repartidos entre rondas:", file=sys.stderr)
        print("\n".join(repartidos), file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
