"""Predicado: por skill, cuántas corridas, cuántas degradadas, cuántas por elección y la duración
mediana; más el total leído, para distinguir un directorio vacío de un filtro sin coincidencias."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:manifest-resumen runs_dir", file=sys.stderr)
        return 2
    runs = Path(sys.argv[1])
    cantidad = sum(1 for path in runs.rglob("*.json") if path.is_file()) if runs.is_dir() else 0
    print(f"corridas leídas: {cantidad}")
    if cantidad == 0:
        return 0

    por_skill: Dict[str, List[Dict[str, Any]]] = {}
    for path in runs.glob("*.json"):
        if not path.is_file():
            continue
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            item = {}
        por_skill.setdefault(str(item.get("skill", "")), []).append(item)
    for skill in sorted(por_skill):
        if not skill:
            continue
        filas = por_skill[skill]
        degradadas = sum(item.get("degradation") != "none" for item in filas)
        elegidas = sum(item.get("selection") == "user_choice" for item in filas)
        duraciones = sorted(int(item.get("duration_s", 0)) for item in filas)
        mediana = duraciones[(len(duraciones) - 1) // 2]
        print(
            f"{skill}: {len(filas)} corridas · {degradadas} degradadas · "
            f"{elegidas} por eleccion · mediana {mediana}s"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
