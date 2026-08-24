"""Predicado: objeto JSON con exactamente nueve claves raíz, una vez cada una; started_at UTC real,
duration_s entero no negativo, families como lista de valores válidos (también vacía); mode,
outcome, degradation y transport en la fila de skill."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


EXPECTED = (
    "skill", "mode", "started_at", "duration_s", "families", "transport",
    "outcome", "degradation", "selection",
)
ROWS: Dict[str, Tuple[set[str], set[str], set[str], set[str]]] = {
    "co-explore": (
        {"explore", "counter-plan", "investigate", "debate"},
        {"completed", "map_failure"},
        {"none", "confirmed_wall", "launch_flake", "runtime_failure", "branch-2", "branch-3", "branch-4", "deadline_exceeded"},
        {"none", "subagent", "cli-exec", "cli-resume"},
    ),
    "cross-review": (
        {"spec", "plan", "tasks", "master-spec", "reparto", "sintesis", "draft"},
        {"APPROVED", "REVISE", "UNAVAILABLE"},
        {"none", "confirmed_wall", "launch_flake", "runtime_failure", "rounds_exhausted", "deadline_exceeded"},
        {"none", "subagent", "cli-exec", "cli-resume"},
    ),
    "cross-implement": (
        {"embebido", "directo"},
        {"IMPLEMENTED", "PARTIAL", "UNAVAILABLE"},
        {"none", "confirmed_wall", "launch_flake", "runtime_failure", "takeover", "deadline_exceeded"},
        {"none", "subagent", "cli-exec", "cli-resume"},
    ),
    "bitbucket-code-review": (
        {"conductor", "delegado", "mixto"},
        {"PUBLISHED", "PROPOSED", "UNAVAILABLE"},
        {"none", "confirmed_wall", "launch_flake", "runtime_failure", "revisor_invalido", "panel_vacio"},
        {"none", "subagent", "cli-exec", "cli-resume"},
    ),
}


def main() -> int:
    if len(sys.argv) != 2:
        print("ARNES:manifest-valido argumentos invalidos", file=sys.stderr)
        return 99
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
        objeto = json.loads(texto)
    except (OSError, UnicodeError, json.JSONDecodeError):
        print("GUARD:manifest-valido el archivo no es un objeto JSON válido", file=sys.stderr)
        return 1
    if not isinstance(objeto, dict):
        print("GUARD:manifest-valido el archivo no es un objeto JSON válido", file=sys.stderr)
        return 1

    rc = 0
    claves = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"\s*:', texto)
    for campo in EXPECTED:
        cantidad = claves.count(campo)
        if cantidad == 0:
            print(f'GUARD:manifest-valido falta el campo "{campo}"', file=sys.stderr)
            rc = 1
        if cantidad > 1:
            print(f'GUARD:manifest-valido clave requerida duplicada: "{campo}"', file=sys.stderr)
            rc = 1
    for campo in sorted(set(claves) - set(EXPECTED)):
        print(f'GUARD:manifest-valido clave raíz desconocida: "{campo}"', file=sys.stderr)
        rc = 1

    if claves.count("started_at") == 1:
        inicio = objeto.get("started_at", "")
        valido = isinstance(inicio, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", inicio)
        if valido:
            try:
                datetime.strptime(inicio, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                valido = False
        if not valido:
            print(f'GUARD:manifest-valido started_at no es UTC ISO-8601: "{inicio}"', file=sys.stderr)
            rc = 1
    if claves.count("duration_s") == 1:
        duracion = objeto.get("duration_s")
        if isinstance(duracion, bool) or not isinstance(duracion, int) or duracion < 0:
            bruto = re.search(r'"duration_s"\s*:\s*([^,}]*)', texto)
            valor = bruto.group(1).strip() if bruto else ""
            print(f'GUARD:manifest-valido duration_s no es entero no negativo: "{valor}"', file=sys.stderr)
            rc = 1

    if claves.count("families") == 1:
        families = objeto.get("families")
        if not isinstance(families, list):
            print('GUARD:manifest-valido "families" no es una lista', file=sys.stderr)
            rc = 1
        else:
            vistos: List[object] = []
            for family in families:
                cantidad = families.count(family)
                if family not in vistos and (not isinstance(family, str) or family not in {"claude", "codex"} or cantidad != 1):
                    mostrado = family if isinstance(family, str) else "<elemento no string>"
                    print(f'GUARD:manifest-valido family inválida o duplicada: "{mostrado}"', file=sys.stderr)
                    rc = 1
                vistos.append(family)

    skill = objeto.get("skill", "")
    if skill not in ROWS:
        print(f'GUARD:manifest-valido skill fuera del ecosistema: "{skill}"', file=sys.stderr)
        return 1
    modos, outcomes, degradations, transports = ROWS[skill]
    permits = {
        "mode": modos,
        "outcome": outcomes,
        "degradation": degradations,
        "transport": transports,
        "selection": {"full", "user_choice"},
    }
    for campo, permitidos in permits.items():
        if claves.count(campo) != 1:
            continue
        valor = objeto.get(campo, "")
        if valor not in permitidos:
            print(f'GUARD:manifest-valido {campo} "{valor}" no pertenece a {skill}', file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
