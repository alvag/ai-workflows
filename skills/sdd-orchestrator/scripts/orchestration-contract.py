"""Predicado: el contrato de integración cierra contra las tareas del manifest: cada tarea posee
exactamente una fila de v1 y ninguna fila queda huérfana, v1 aloja las tres clases de cierre
—gate, closeout y auxiliar—, el baseline de toda fila está resuelto, y ninguna versión posterior
agrega ni quita IDs.
Un solo diagnóstico por corrida: gana el primero del orden de abajo, que es el de la fábrica."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from _yaml import parsear_valor_yaml


def escalar(valor: str) -> str:
    parsed = parsear_valor_yaml(valor)
    return parsed if isinstance(parsed, str) else ""


def lista(valor: str) -> List[str]:
    parsed = parsear_valor_yaml(valor)
    if isinstance(parsed, list):
        return parsed
    return [parsed] if parsed else []


def parsear_tasks(texto: str) -> List[Dict[str, object]]:
    tasks: List[Dict[str, object]] = []
    seccion = ""
    task: Optional[Dict[str, object]] = None
    campo = ""
    id_col = -1
    for linea in texto.splitlines():
        if re.match(r"^\s*#", linea):
            continue
        if linea and not linea[0].isspace():
            seccion = "tasks" if re.fullmatch(r"orchestration_tasks:\s*(?:#.*)?", linea) else ""
            continue
        if seccion != "tasks":
            continue
        nonspace = len(linea) - len(linea.lstrip())
        match = re.match(r"^\s*-\s*id:\s*(.*)$", linea)
        if match:
            id_col = linea.index("id:")
            task = {"id": escalar(match.group(1)), "phase": "", "done_when": "", "covers_ac": []}
            tasks.append(task)
            campo = ""
            continue
        if task is None:
            continue
        if nonspace > id_col:
            item = re.match(r"^\s*-\s+(.*)$", linea)
            if campo == "covers_ac" and item:
                task["covers_ac"].append(escalar(item.group(1)))
            continue
        if nonspace != id_col:
            continue
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", linea)
        if not match:
            continue
        campo, valor = match.group(1), match.group(2)
        if campo in {"phase", "done_when"}:
            task[campo] = escalar(valor)
        elif campo == "covers_ac":
            task[campo] = lista(valor)
    return tasks


def parsear_versiones(texto: str) -> List[Tuple[int, List[List[str]]]]:
    versiones: List[Tuple[int, List[List[str]]]] = []
    actual: Optional[List[List[str]]] = None
    for linea in texto.splitlines():
        match = re.fullmatch(r"#+\s*v(\d+)\s*", linea)
        if match:
            actual = []
            versiones.append((int(match.group(1)), actual))
            continue
        if actual is None or not linea.lstrip().startswith("|"):
            continue
        celdas = [celda.strip() for celda in linea.strip()[1:-1].split("|")] if linea.strip().endswith("|") else []
        if celdas and celdas[0] != "ID" and not all(celda and set(celda) <= {"-", ":"} for celda in celdas):
            actual.append(celdas)
    return versiones


def duenia(requisito: str, identificador: str) -> bool:
    if not requisito.startswith(identificador):
        return False
    resto = requisito[len(identificador) :]
    return bool(resto[:1].isspace() and resto.lstrip().startswith(("— ", "- ")))


def main() -> int:
    if len(sys.argv) != 3:
        print("ARNES:orchestration-contract argumentos invalidos", file=sys.stderr)
        return 99
    manifest_path, contrato_path = map(Path, sys.argv[1:])
    for path in (manifest_path, contrato_path):
        if not path.is_file():
            print(f"ARNES:no existe {path}", file=sys.stderr)
            return 99
    tasks = parsear_tasks(manifest_path.read_text(encoding="utf-8"))
    versiones = parsear_versiones(contrato_path.read_text(encoding="utf-8"))
    v1 = next((filas for numero, filas in versiones if numero == 1), [])
    fallo: Optional[Tuple[str, str]] = None

    def falla(codigo: str, contexto: str) -> None:
        nonlocal fallo
        if fallo is None:
            fallo = (codigo, contexto)

    propias: Dict[str, List[str]] = {str(task["id"]): [] for task in tasks}
    dueños: Dict[str, int] = {fila[0]: 0 for fila in v1 if fila}
    for fila in v1:
        if len(fila) < 2:
            continue
        for task in tasks:
            if duenia(fila[1], str(task["id"])) or (task["done_when"] and fila[0] == task["done_when"]):
                propias[str(task["id"])].append(fila[0])
                dueños[fila[0]] = dueños.get(fila[0], 0) + 1
    closeouts = [task for task in tasks if task["phase"] == "closeout"]
    auxiliares = [task for task in closeouts if not task["covers_ac"]]
    if closeouts and not any(propias[str(task["id"])] for task in closeouts):
        sin = [str(task["id"]) for task in closeouts if not propias[str(task["id"])]]
        falla("fila-closeout-ausente", f"v1 no aloja el cierre de ninguna tarea phase=closeout; sin fila: {', '.join(sin)}")
    if auxiliares and not any(propias[str(task["id"])] for task in auxiliares):
        sin = [str(task["id"]) for task in auxiliares if not propias[str(task["id"])]]
        falla("fila-auxiliar-ausente", f"v1 no aloja el cierre de ninguna tarea auxiliar; sin fila: {', '.join(sin)}")
    for task in tasks:
        filas = propias[str(task["id"])]
        if not filas:
            falla("tarea-sin-fila", f"la tarea {task['id']} no tiene fila en v1 (done_when: {task['done_when'] or '—'})")
        if len(filas) > 1:
            falla("tarea-con-dos-filas", f"la tarea {task['id']} tiene {len(filas)} filas en v1: {', '.join(filas)}")
    for fila in v1:
        if fila and dueños.get(fila[0], 0) == 0:
            falla("fila-sin-tarea", f"la fila {fila[0]} de v1 no cierra ninguna orchestration_task")
    permitidos = {"RED", "GREEN_ALREADY", "NOT_APPLICABLE", "BLOCKED"}
    for numero, filas in versiones:
        for fila in filas:
            baseline = fila[-1] if fila else ""
            if baseline not in permitidos:
                falla("baseline-sin-resolver", f"la fila {fila[0]} de v{numero} declara baseline [{baseline}], fuera de {{RED, GREEN_ALREADY, NOT_APPLICABLE, BLOCKED}}")
    for (anterior, filas_a), (actual, filas_b) in zip(versiones, versiones[1:]):
        ids_a = [fila[0] for fila in filas_a if fila]
        ids_b = [fila[0] for fila in filas_b if fila]
        for identificador in ids_b:
            if identificador not in ids_a:
                falla("id-agregado-entre-versiones", f"v{actual} estrena la fila {identificador}, que v{anterior} no declara")
        for identificador in ids_a:
            if identificador not in ids_b:
                falla("id-quitado-entre-versiones", f"v{actual} no lleva la fila {identificador}, que v{anterior} declara")
    if fallo is None:
        return 0
    print(f"GUARD:contract {fallo[0]}", file=sys.stderr)
    print(f"  {fallo[1]}", file=sys.stderr)
    print(f"  contrato: {contrato_path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
