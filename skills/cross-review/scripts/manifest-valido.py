"""Predicado: valida las formas `run-manifest/1` y `dispatch-log/1` según `record_type`: sus claves
raíz obligatorias, condicionales y prohibidas; los tipos, la cardinalidad y las claves de
`dispatches`; el UTC de `started_at`; y los enums aplicables a la fila de `skill`. En
`run-manifest/1`, `transporte_fuente` y `transporte_proceso` son obligatorias con transporte por
panel y admisibles en otro caso.

**Qué NO detecta.** No comprueba que `transporte_fuente` nombre una fuente existente ni que
`transporte_proceso` apunte a un proceso vivo: lee presencia y no verdad;
ninguna receta de productor invoca este predicado: su verde acredita la forma del archivo que se le
pasa, nunca que las corridas publiquen manifests validados. La precisión fraccionaria de
`started_at` no se aflojó porque no se reprodujo contra el árbol.

**Campos** (ver CLAUDE.md → "La frontera de prueba de una guarda"). Clase: **veredicto**.
Dirección: **admite-de-más** — su verde autoriza a afirmar que el registro cumple la forma y los
enums de su fila, nunca que lo registrado haya ocurrido."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


RUN_MANIFEST = "run-manifest/1"
DISPATCH_LOG = "dispatch-log/1"
FORMAS: Dict[str, Tuple[set[str], set[str], set[str]]] = {
    RUN_MANIFEST: (
        {
            "record_type", "run_id", "skill", "mode", "started_at", "duration_s", "families",
            "transport", "outcome", "degradation", "selection", "dispatches",
        },
        {"transporte_fuente", "transporte_proceso"},
        set(),
    ),
    DISPATCH_LOG: (
        {"record_type", "run_id", "skill", "mode", "started_at", "dispatches"},
        set(),
        {
            "duration_s", "families", "transport", "outcome", "degradation", "selection",
            "transporte_fuente", "transporte_proceso",
        },
    ),
}
# Los dos transportes por panel son los unicos que exigen la fuente consultable: un panel se puede
# interrogar, asi que un registro que lo use y no diga por donde no es auditable.
CON_PANEL = {"pane-herdr", "pane-orca"}
CLAVES_DESPACHO = {
    "attempt", "at", "role", "family", "requested", "resolved", "origin", "materialized",
    "sent", "outcome", "retry_of",
}
ROWS: Dict[str, Tuple[set[str], set[str], set[str], set[str]]] = {
    "co-explore": (
        {"explore", "counter-plan", "investigate", "debate"},
        {"completed", "map_failure"},
        {"none", "confirmed_wall", "launch_flake", "runtime_failure", "host_sandbox_wall", "branch-2", "branch-3", "branch-4", "deadline_exceeded"},
        {"none", "subagent", "cli-exec", "cli-resume", "pane-herdr", "pane-orca"},
    ),
    "cross-review": (
        {"spec", "plan", "tasks", "master-spec", "reparto", "sintesis", "draft"},
        {"APPROVED", "REVISE", "UNAVAILABLE"},
        {"none", "confirmed_wall", "launch_flake", "runtime_failure", "host_sandbox_wall", "rounds_exhausted", "deadline_exceeded"},
        {"none", "subagent", "cli-exec", "cli-resume", "pane-herdr", "pane-orca"},
    ),
    "cross-implement": (
        {"embebido", "directo"},
        {"IMPLEMENTED", "PARTIAL", "UNAVAILABLE"},
        {"none", "confirmed_wall", "launch_flake", "runtime_failure", "host_sandbox_wall", "takeover", "deadline_exceeded"},
        {"none", "subagent", "cli-exec", "cli-resume", "pane-herdr", "pane-orca"},
    ),
    "bitbucket-code-review": (
        {"conductor", "delegado", "mixto"},
        {"PUBLISHED", "PROPOSED", "UNAVAILABLE"},
        {"none", "confirmed_wall", "launch_flake", "runtime_failure", "host_sandbox_wall", "revisor_invalido", "panel_vacio"},
        {"none", "subagent", "cli-exec", "cli-resume", "pane-herdr", "pane-orca"},
    ),
    "sdd-pr-feedback": (
        {"apply"},
        set(),
        set(),
        set(),
    ),
}


def claves_raiz(texto: str) -> Tuple[dict, set[str]]:
    duplicadas_por_objeto: Dict[int, set[str]] = {}

    def hook(pares: List[Tuple[str, object]]) -> dict:
        objeto = {}
        duplicadas = set()
        for clave, valor in pares:
            if clave in objeto:
                duplicadas.add(clave)
            objeto[clave] = valor
        duplicadas_por_objeto[id(objeto)] = duplicadas
        return objeto

    objeto = json.loads(texto, object_pairs_hook=hook)
    return objeto, duplicadas_por_objeto.get(id(objeto), set())


def main() -> int:
    if len(sys.argv) != 2:
        print("ARNES:manifest-valido argumentos invalidos", file=sys.stderr)
        return 99
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
        objeto, duplicadas_en_raiz = claves_raiz(texto)
    except (OSError, UnicodeError, json.JSONDecodeError):
        print("GUARD:manifest-valido el archivo no es un objeto JSON válido", file=sys.stderr)
        return 1
    if not isinstance(objeto, dict):
        print("GUARD:manifest-valido el archivo no es un objeto JSON válido", file=sys.stderr)
        return 1

    claves = set(objeto)
    if "record_type" not in claves:
        print('GUARD:manifest-valido falta el campo "record_type"', file=sys.stderr)
        return 1
    record_type = objeto.get("record_type")
    if record_type not in FORMAS:
        print(f'GUARD:manifest-valido record_type desconocido: "{record_type}"', file=sys.stderr)
        return 1

    rc = 0
    obligatorias, condicionales, prohibidas = FORMAS[record_type]
    for campo in sorted(obligatorias):
        if campo not in claves:
            print(f'GUARD:manifest-valido falta el campo "{campo}"', file=sys.stderr)
            rc = 1
        if campo in duplicadas_en_raiz:
            print(f'GUARD:manifest-valido clave requerida duplicada: "{campo}"', file=sys.stderr)
            rc = 1
    for campo in sorted(claves & prohibidas):
        print(f'GUARD:manifest-valido campo "{campo}" no corresponde a {record_type}', file=sys.stderr)
        rc = 1
    for campo in sorted(claves - obligatorias - condicionales - prohibidas):
        print(f'GUARD:manifest-valido clave raíz desconocida: "{campo}"', file=sys.stderr)
        rc = 1

    if "started_at" in claves and "started_at" not in duplicadas_en_raiz:
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
    if "duration_s" in claves and "duration_s" not in duplicadas_en_raiz:
        duracion = objeto.get("duration_s")
        if isinstance(duracion, bool) or not isinstance(duracion, int) or duracion < 0:
            bruto = re.search(r'"duration_s"\s*:\s*([^,}]*)', texto)
            valor = bruto.group(1).strip() if bruto else ""
            print(f'GUARD:manifest-valido duration_s no es entero no negativo: "{valor}"', file=sys.stderr)
            rc = 1

    if "families" in claves and "families" not in duplicadas_en_raiz:
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
        if campo not in obligatorias and campo not in condicionales:
            continue
        if campo not in claves or campo in duplicadas_en_raiz:
            continue
        valor = objeto.get(campo, "")
        if valor not in permitidos:
            # el mensaje nombra el transporte en la lengua del contrato: un rechazo que solo diga
            # `transport` no se distingue del nombre de la clave JSON al leer el log
            sufijo = ": transporte fuera del enum" if campo == "transport" else ""
            print(f'GUARD:manifest-valido {campo} "{valor}" no pertenece a {skill}{sufijo}', file=sys.stderr)
            rc = 1

    if record_type == RUN_MANIFEST and objeto.get("transport") in CON_PANEL:
        for campo in condicionales:
            if not objeto.get(campo):
                print(f'GUARD:manifest-valido transporte por panel sin "{campo}": la fuente tiene que ser consultable', file=sys.stderr)
                rc = 1

    if "dispatches" in claves and "dispatches" not in duplicadas_en_raiz:
        dispatches = objeto.get("dispatches")
        if not isinstance(dispatches, list):
            print('GUARD:manifest-valido "dispatches" no es una lista', file=sys.stderr)
            rc = 1
        else:
            if record_type == DISPATCH_LOG and not dispatches:
                print("GUARD:manifest-valido dispatch-log/1 sin ninguna entrada", file=sys.stderr)
                rc = 1
            for indice, entrada in enumerate(dispatches, start=1):
                if not isinstance(entrada, dict):
                    print(f"GUARD:manifest-valido entrada {indice} no es un objeto", file=sys.stderr)
                    rc = 1
                    continue
                for campo in sorted(CLAVES_DESPACHO - set(entrada)):
                    print(f'GUARD:manifest-valido entrada {indice} sin la clave "{campo}"', file=sys.stderr)
                    rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
