"""Validates the terminal artifact and its contributors.

This descriptive docstring has no historical predicate span.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path


def cabecera(texto: str) -> dict[str, str]:
    lineas = texto.splitlines()
    try:
        inicio = lineas.index("---")
        fin = lineas.index("---", inicio + 1)
    except ValueError:
        return {}
    valores = {}
    for linea in lineas[inicio + 1 : fin]:
        match = re.match(r"^([^:]+):\s*(.*)$", linea)
        if match:
            valores[match.group(1)] = match.group(2)
    return valores


def main() -> int:
    if len(sys.argv) != 3:
        print("USO:cierre closure co_explore_dir", file=sys.stderr)
        return 2
    cierre, directorio = Path(sys.argv[1]), Path(sys.argv[2])
    try:
        texto = cierre.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return 1
    with tempfile.TemporaryDirectory():
        valores = cabecera(texto)
        modo = valores.get("modo", "")
        rama = valores.get("rama", "")
        diversidad = valores.get("diversidad", "")
        contribuyentes = valores.get("contribuyentes", "").replace("[", "").replace("]", "").replace(",", " ").split()
        if not modo or not rama or not diversidad or not contribuyentes:
            return 1
        if modo not in {"explore", "counter-plan", "investigate"} or rama not in {"1", "2", "3", "4"} or diversidad not in {"cross_family", "same_family", "single_voice"}:
            return 1
        modo_id = {"explore": "EXP", "counter-plan": "CTR", "investigate": "INV"}[modo]
        patron = re.compile(rf"(CLD|CDX)-(W|C)-{modo_id}")
        if any(not patron.fullmatch(item) for item in contribuyentes) or len(contribuyentes) != len(set(contribuyentes)):
            return 1
        roles = [item.split("-")[1] for item in contribuyentes]
        familias = {item.split("-")[0] for item in contribuyentes}
        valido = {
            "1": len(contribuyentes) == 2 and roles.count("W") == 2 and len(familias) == 2 and diversidad == "cross_family",
            "2": len(contribuyentes) == 2 and roles.count("W") == 1 and roles.count("C") == 1 and len(familias) == 2 and diversidad == "cross_family",
            "3": len(contribuyentes) == 2 and roles.count("W") == 1 and roles.count("C") == 1 and len(familias) == 1 and diversidad == "same_family",
            "4": len(contribuyentes) == 1 and roles.count("C") == 1 and diversidad == "single_voice",
        }[rama]
        if not valido:
            return 1
        for hallazgo in set(re.findall(r"(?:CLD|CDX)-(?:W|C)-(?:EXP|CTR|INV)-[0-9]{3}", texto)):
            if "-".join(hallazgo.split("-")[:3]) not in contribuyentes:
                return 1
        if (directorio / f"synthesis-{modo}.md").is_file() and (directorio / f"cierre-conductor-{modo}.md").is_file():
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
