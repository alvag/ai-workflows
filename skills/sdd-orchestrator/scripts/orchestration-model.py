"""Predicado: el modelo de orquestación cierra contra la master-spec: cada AC [integration] lo cubre
exactamente una tarea, cada AC vive del lado que dice su etiqueta, el grafo de `depends_on` es
acíclico y ejecutable, los campos obligatorios están con valores de su enum, y el mapa de
participación tiene por claves exactamente el `covers_ac` de su tarea, con repos que existen.
Un solo diagnóstico por corrida: gana el primero del orden de abajo, que es el de la fábrica."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from _yaml import parsear_valor_yaml


def escalar(valor: str) -> str:
    parsed = parsear_valor_yaml(valor)
    return parsed if isinstance(parsed, str) else ""


def lista(valor: str) -> List[str]:
    parsed = parsear_valor_yaml(valor)
    if isinstance(parsed, list):
        return parsed
    return [parsed] if parsed else []


def parsear_manifest(texto: str) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    repos: List[Dict[str, object]] = []
    tasks: List[Dict[str, object]] = []
    seccion = ""
    repo_campo = ""
    task: Optional[Dict[str, object]] = None
    campo = ""
    id_col = -1
    mapa = False
    mapa_clave = ""
    for linea in texto.splitlines():
        if re.match(r"^\s*#", linea):
            continue
        if linea and not linea[0].isspace():
            if re.fullmatch(r"repos:\s*(?:#.*)?", linea):
                seccion = "repos"
            elif re.fullmatch(r"orchestration_tasks:\s*(?:#.*)?", linea):
                seccion = "tasks"
            else:
                seccion = ""
            continue
        if seccion == "repos":
            match = re.match(r"^\s*-\s*path:\s*(.*)$", linea)
            if match:
                repos.append({"path": escalar(match.group(1)), "covers_ac": []})
                repo_campo = "path"
                continue
            if not repos:
                continue
            match = re.match(r"^\s*covers_ac:\s*(.*)$", linea)
            if match:
                repos[-1]["covers_ac"] = lista(match.group(1))
                repo_campo = "covers_ac"
                continue
            match = re.match(r"^\s*-\s+(.*)$", linea)
            if repo_campo == "covers_ac" and match:
                repos[-1]["covers_ac"].append(escalar(match.group(1)))
                continue
            if re.match(r"^\s*[A-Za-z_][A-Za-z0-9_]*:", linea):
                repo_campo = "otro"
            continue
        if seccion != "tasks":
            continue
        nonspace = len(linea) - len(linea.lstrip())
        match = re.match(r"^\s*-\s*id:\s*(.*)$", linea)
        if match:
            id_col = linea.index("id:")
            task = {"id": escalar(match.group(1)), "fields": {}, "lists": {}, "participating": [], "participating_mode": "none"}
            tasks.append(task)
            campo, mapa, mapa_clave = "", False, ""
            continue
        if task is None:
            continue
        if nonspace > id_col:
            item = re.match(r"^\s*-\s+(.*)$", linea)
            clave = re.match(r"^\s*([^\s:]+):\s*(.*)$", linea)
            if mapa:
                if item and mapa_clave:
                    task["participating"][-1][1].append(escalar(item.group(1)))
                elif clave:
                    mapa_clave = escalar(clave.group(1))
                    task["participating"].append((mapa_clave, lista(clave.group(2))))
            elif campo and item:
                task["lists"].setdefault(campo, []).append(escalar(item.group(1)))
            continue
        if nonspace != id_col:
            continue
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", linea)
        if not match:
            continue
        campo, valor = match.group(1), match.group(2)
        mapa = False
        task["fields"][campo] = escalar(valor)
        if campo == "participating_repos":
            if not valor.strip():
                task["participating_mode"] = "map"
                mapa = True
            elif valor.strip() == "{}":
                task["participating_mode"] = "empty"
            else:
                task["participating_mode"] = "map"
            continue
        if campo in {"depends_on", "covers_ac", "blocks_repos"}:
            task["lists"][campo] = lista(valor)
    return repos, tasks


def main() -> int:
    if len(sys.argv) != 3:
        print("ARNES:orchestration-model argumentos invalidos", file=sys.stderr)
        return 99
    manifest_path, master_path = map(Path, sys.argv[1:])
    for path in (manifest_path, master_path):
        if not path.is_file():
            print(f"ARNES:no existe {path}", file=sys.stderr)
            return 99
    manifest = manifest_path.read_text(encoding="utf-8")
    master = master_path.read_text(encoding="utf-8")
    tags: Dict[str, str] = {}
    integration: List[str] = []
    for match in re.finditer(r"^-\s*\*\*(AC-[0-9]+)\s*\[([a-z-]+)\]", master, re.MULTILINE):
        tags[match.group(1)] = match.group(2)
        if match.group(2) == "integration":
            integration.append(match.group(1))
    repos, tasks = parsear_manifest(manifest)
    paths = {str(repo["path"]) for repo in repos}
    por_id: Dict[str, int] = {}
    fallo: Optional[Tuple[str, str]] = None

    def falla(codigo: str, contexto: str) -> None:
        nonlocal fallo
        if fallo is None:
            fallo = (codigo, contexto)

    for task in tasks:
        identificador = str(task["id"])
        por_id[identificador] = por_id.get(identificador, 0) + 1
    for task in tasks:
        identificador = str(task["id"])
        if por_id[identificador] > 1:
            falla("id-duplicado", f"el id {identificador} abre {por_id[identificador]} entradas de orchestration_tasks")
    for task in tasks:
        phase = task["fields"].get("phase", "")
        if phase not in {"gate", "closeout"}:
            falla("phase-fuera-de-enum", f"la tarea {task['id']} declara phase=[{phase}], fuera de {{gate, closeout}}")
    for task in tasks:
        status = task["fields"].get("status", "")
        if status not in {"pending", "in-progress", "done", "blocked"}:
            falla("status-fuera-de-enum", f"la tarea {task['id']} declara status=[{status}], fuera de {{pending, in-progress, done, blocked}}")
    for task in tasks:
        if "owner" not in task["fields"]:
            falla("owner-ausente", f"la tarea {task['id']} no declara owner")
    for task in tasks:
        if "owner" in task["fields"] and not task["fields"]["owner"]:
            falla("owner-vacio", f"la tarea {task['id']} declara owner vacío")
    for task in tasks:
        if "done_when" not in task["fields"]:
            falla("done_when-ausente", f"la tarea {task['id']} no declara done_when")
    for task in tasks:
        if "done_when" in task["fields"] and not task["fields"]["done_when"]:
            falla("done_when-vacio", f"la tarea {task['id']} declara done_when vacío")
    for task in tasks:
        blocks = task["lists"].get("blocks_repos", [])
        if blocks and task["fields"].get("phase") != "gate":
            falla("blocks_repos-en-closeout", f"la tarea {task['id']} es phase={task['fields'].get('phase', '')} y declara blocks_repos: [{', '.join(blocks)}]")
    for task in tasks:
        for dependencia in task["lists"].get("depends_on", []):
            if dependencia not in por_id:
                falla("depends_on-inexistente", f"la tarea {task['id']} depende de {dependencia}, que ninguna orchestration_task declara")
    for task in tasks:
        for repo in task["lists"].get("blocks_repos", []):
            if repo not in paths:
                falla("blocks_repos-inexistente", f"la tarea {task['id']} bloquea {repo}, que no es un path de repos")
    tasks_by_id = {str(task["id"]): task for task in tasks}
    for task in tasks:
        if task["fields"].get("phase") == "gate":
            for dependencia in task["lists"].get("depends_on", []):
                if dependencia in tasks_by_id and tasks_by_id[dependencia]["fields"].get("phase") == "closeout":
                    falla("gate-depende-de-closeout", f"el gate {task['id']} depende de {dependencia}, que es phase=closeout")
    vivos: Set[str] = set(tasks_by_id)
    cambio = True
    while cambio:
        cambio = False
        for identificador in list(vivos):
            deps = [dep for dep in tasks_by_id[identificador]["lists"].get("depends_on", []) if dep in por_id]
            if not any(dep in vivos for dep in deps):
                vivos.remove(identificador)
                cambio = True
    if vivos:
        orden = [str(task["id"]) for task in tasks if str(task["id"]) in vivos]
        falla("ciclo-en-depends_on", f"estas tareas no llegan a ejecutarse nunca: {', '.join(orden)}")
    for repo in repos:
        for ac in repo["covers_ac"]:
            if tags.get(ac) == "integration":
                falla("integration-en-covers_ac-de-repo", f"el repo {repo['path']} declara {ac}, que la master-spec etiqueta [integration]")
    for task in tasks:
        for ac in task["lists"].get("covers_ac", []):
            if tags.get(ac) == "repo-local":
                falla("repo-local-en-covers_ac-de-tarea", f"la tarea {task['id']} declara {ac}, que la master-spec etiqueta [repo-local]")
    huerfanos = []
    for ac in integration:
        dueñas = [str(task["id"]) for task in tasks if ac in task["lists"].get("covers_ac", [])]
        if not dueñas:
            huerfanos.append(ac)
        if len(dueñas) > 1:
            falla("ac-cubierto-por-dos-tareas", f"{ac} lo cubren {len(dueñas)} tareas de cierre: {', '.join(dueñas)}")
    detalle = False
    if huerfanos and fallo is None:
        falla("ac-integration-huerfano", f"ninguna orchestration_task cubre {', '.join(huerfanos)}")
        detalle = True
    for task in tasks:
        covers = task["lists"].get("covers_ac", [])
        if covers and task["participating_mode"] == "none":
            falla("participacion-ausente-con-covers_ac", f"la tarea {task['id']} cubre [{', '.join(covers)}] y no declara participating_repos")
        elif covers and (task["participating_mode"] == "empty" or not task["participating"]):
            falla("participacion-vacia-con-covers_ac", f"la tarea {task['id']} cubre [{', '.join(covers)}] con participating_repos vacío")
    for task in tasks:
        claves = [clave for clave, _ in task["participating"]]
        for clave in claves:
            if claves.count(clave) > 1:
                falla("participacion-clave-duplicada", f"la tarea {task['id']} repite la clave {clave} en participating_repos")
    for task in tasks:
        covers = task["lists"].get("covers_ac", [])
        for clave, _ in task["participating"]:
            if clave not in covers:
                falla("participacion-clave-ajena", f"la tarea {task['id']} declara la clave {clave}, que no está en su covers_ac [{', '.join(covers)}]")
        if task["participating_mode"] == "map":
            claves = [clave for clave, _ in task["participating"]]
            for ac in covers:
                if ac not in claves:
                    falla("participacion-ac-sin-clave", f"la tarea {task['id']} cubre {ac} y no le declara clave en participating_repos")
        for clave, participantes in task["participating"]:
            if tags.get(clave) != "integration":
                falla("participacion-ac-no-integration", f"la clave {clave} de la tarea {task['id']} no es un AC [integration] de la master-spec")
            for repo in participantes:
                if repo not in paths:
                    falla("participacion-repo-inexistente", f"la clave {clave} de la tarea {task['id']} nombra {repo}, que no es un path de repos")
    if fallo is None:
        return 0
    print(f"GUARD:model {fallo[0]}", file=sys.stderr)
    print(f"  {fallo[1]}", file=sys.stderr)
    print(f"  manifest: {manifest_path}", file=sys.stderr)
    if detalle:
        for ac in huerfanos:
            print(f"DETALLE:{ac}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
