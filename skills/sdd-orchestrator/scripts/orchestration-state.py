"""Predicado: el estado de la orquestación cierra contra su bitácora: ninguna tarea pasa a `done` sin
dueño real, con un `depends_on` abierto o con evidencia que no sea fresca y de su propia fila;
ningún repo se despacha con su gate abierto ni con el baseline de su fila local en `BLOCKED`, ni se
queda sin promover con el gate ya cerrado; cada evento lleva sus seis campos, un `resultado` del
enum y un `id` único y comparable, y solo un resultado consumado materializa su transición; y la
precedencia produce un único estado agregado que nunca oculta el más grave.
Un solo diagnóstico por corrida: gana el primero del orden de abajo, que es el de la fábrica."""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
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


def parsear_master(texto: str) -> Dict[str, str]:
    anclas: Dict[str, str] = {}
    dentro = False
    for linea in texto.splitlines():
        if re.match(r"^#+\s", linea):
            dentro = bool(re.fullmatch(r"#+\s*Anclas versionadas\s*", linea))
            continue
        if not dentro:
            continue
        match = re.search(r"`([^`]*)`", linea)
        if match and ":" in match.group(1):
            nombre, valor = match.group(1).split(":", 1)
            anclas[nombre.strip()] = valor.strip()
    return anclas


def parsear_manifest(texto: str) -> Tuple[str, List[Dict[str, str]], List[Dict[str, object]]]:
    outcome = ""
    repos: List[Dict[str, str]] = []
    tasks: List[Dict[str, object]] = []
    seccion = ""
    task: Optional[Dict[str, object]] = None
    campo = ""
    id_col = -1
    mapa = False
    for linea in texto.splitlines():
        if re.match(r"^\s*#", linea):
            continue
        if linea and not linea[0].isspace():
            seccion = ""
            if re.fullmatch(r"repos:\s*(?:#.*)?", linea):
                seccion = "repos"
            elif re.fullmatch(r"orchestration_tasks:\s*(?:#.*)?", linea):
                seccion = "tasks"
            else:
                match = re.match(r"^outcome:\s*(.*)$", linea)
                if match:
                    outcome = escalar(match.group(1))
            continue
        if seccion == "repos":
            match = re.match(r"^\s*-\s*path:\s*(.*)$", linea)
            if match:
                repos.append({"path": escalar(match.group(1)), "status": ""})
                continue
            match = re.match(r"^\s*status:\s*(.*)$", linea)
            if match and repos:
                repos[-1]["status"] = escalar(match.group(1))
            continue
        if seccion != "tasks":
            continue
        nonspace = len(linea) - len(linea.lstrip())
        match = re.match(r"^\s*-\s*id:\s*(.*)$", linea)
        if match:
            id_col = linea.index("id:")
            task = {
                "id": escalar(match.group(1)), "phase": "", "owner": "", "status": "",
                "done_when": "", "depends_on": [], "blocks_repos": [], "participants": [],
            }
            tasks.append(task)
            campo, mapa = "", False
            continue
        if task is None:
            continue
        if nonspace > id_col:
            item = re.match(r"^\s*-\s+(.*)$", linea)
            entrada = re.match(r"^\s*[^\s:]+:\s*(.*)$", linea)
            if mapa:
                if item:
                    task["participants"].append(escalar(item.group(1)))
                elif entrada:
                    task["participants"].extend(lista(entrada.group(1)))
            elif item and campo in {"depends_on", "blocks_repos"}:
                task[campo].append(escalar(item.group(1)))
            continue
        if nonspace != id_col:
            continue
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", linea)
        if not match:
            continue
        campo, valor = match.group(1), match.group(2)
        mapa = False
        if campo in {"phase", "owner", "status", "done_when"}:
            task[campo] = escalar(valor)
        elif campo == "participating_repos":
            mapa = not valor.strip()
        elif campo in {"depends_on", "blocks_repos"}:
            task[campo] = lista(valor)
    return outcome, repos, tasks


def parsear_contrato(texto: str) -> List[Tuple[int, List[List[str]]]]:
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
        limpia = linea.strip()
        if not limpia.endswith("|"):
            continue
        celdas = [celda.strip() for celda in limpia[1:-1].split("|")]
        if celdas and celdas[0] != "ID" and not all(celda and set(celda) <= {"-", ":"} for celda in celdas):
            actual.append(celdas)
    return versiones


def parsear_eventos(texto: str) -> List[Dict[str, str]]:
    eventos = []
    for linea in texto.splitlines():
        if not re.match(r"^\s*-\s*`", linea):
            continue
        evento = {}
        for contenido in re.findall(r"`([^`]*)`", linea):
            match = re.match(r"^([A-Za-z_]+):\s*(.*)$", contenido)
            if match:
                evento[match.group(1)] = match.group(2).strip()
        eventos.append(evento)
    return eventos


def parsear_plan(path: Path) -> Tuple[str, str, str, bool]:
    texto = path.read_text(encoding="utf-8")
    repo = status = sha = ""
    frontmatter = 0
    blocked = False
    for linea in texto.splitlines():
        if re.fullmatch(r"---\s*", linea):
            frontmatter += 1
            continue
        if frontmatter == 1:
            for nombre in ("repo", "status", "head_sha"):
                match = re.match(rf"^{nombre}:\s*(.*)$", linea)
                if match:
                    if nombre == "repo":
                        repo = match.group(1).strip()
                    elif nombre == "status":
                        status = match.group(1).strip()
                    else:
                        sha = match.group(1).strip()
            continue
        limpia = linea.strip()
        if limpia.startswith("|") and limpia.endswith("|"):
            celdas = [celda.strip() for celda in limpia[1:-1].split("|")]
            if celdas and celdas[-1] == "BLOCKED":
                blocked = True
    return repo, status, sha, blocked


def duenia(requisito: str, identificador: str) -> bool:
    if not requisito.startswith(identificador):
        return False
    resto = requisito[len(identificador) :]
    return bool(resto[:1].isspace() and resto.lstrip().startswith(("— ", "- ")))


def promovido(status: str) -> bool:
    return status != "planned"


def despachado(status: str) -> bool:
    return status not in {"planned", "tasks-ready", "blocked"}


def elegible(status: str) -> bool:
    return status not in {"planned", "blocked", "failed"}


def verde(status: str) -> bool:
    return status in {"verified", "committed", "pushed", "pr-open", "done"}


def main() -> int:
    if len(sys.argv) != 6:
        print("ARNES:orchestration-state argumentos invalidos", file=sys.stderr)
        return 99
    manifest_path, master_path, contrato_path, bitacora_path = map(Path, sys.argv[1:5])
    planes = [Path(item) for item in sys.argv[5].split()]
    for path in (manifest_path, master_path, contrato_path):
        if not path.is_file():
            print(f"ARNES:no existe el artefacto {path}", file=sys.stderr)
            return 99
    for plan in planes:
        if not plan.is_file():
            print(f"ARNES:no existe el plan {plan}", file=sys.stderr)
            return 99
    master = master_path.read_text(encoding="utf-8")
    manifest = manifest_path.read_text(encoding="utf-8")
    contrato = contrato_path.read_text(encoding="utf-8")
    bitacora = bitacora_path.read_text(encoding="utf-8") if bitacora_path.is_file() else ""
    anclas = parsear_master(master)
    outcome, repos, tasks = parsear_manifest(manifest)
    versiones = parsear_contrato(contrato)
    eventos = parsear_eventos(bitacora)
    planes_data = {repo: (status, sha, blocked, path) for path in planes for repo, status, sha, blocked in [parsear_plan(path)]}
    task_by_id = {str(task["id"]): task for task in tasks}
    repo_by_path = {repo["path"]: repo for repo in repos}
    vigente_num, vigente = max(versiones, default=(0, []), key=lambda item: item[0])
    fila: Dict[str, str] = {}
    esperado: Dict[str, str] = {}
    for task in tasks:
        for row in vigente:
            if len(row) >= 5 and duenia(row[1], str(task["id"])):
                fila[str(task["id"])] = row[0]
                esperado[str(task["id"])] = row[-2]
    retiene: Counter[str] = Counter()
    abierto: Counter[str] = Counter()
    for task in tasks:
        if task["phase"] != "gate":
            continue
        for repo in task["blocks_repos"]:
            retiene[repo] += 1
            if task["status"] != "done":
                abierto[repo] += 1
    promok: Set[str] = set()
    despok: Set[str] = set()
    cierreok: Set[str] = set()
    porfila: Counter[str] = Counter()
    evfila: Dict[str, Dict[str, str]] = {}
    evobj: Dict[str, Dict[str, str]] = {}
    hayreparto = False
    for evento in eventos:
        paso, objeto, resultado = evento.get("paso", ""), evento.get("objeto", ""), evento.get("resultado", "")
        if paso == "promover-repo":
            hayreparto = True
            if resultado == "consumado":
                promok.add(objeto)
        elif paso == "despachar-repo" and resultado == "consumado":
            despok.add(objeto)
        elif paso == "cerrar-tarea" and resultado == "consumado":
            cierreok.add(objeto)
        elif paso == "ejecutar-evidencia" and resultado == "consumado":
            porfila[evento.get("fila", "")] += 1
            evfila.setdefault(evento.get("fila", ""), evento)
            evobj.setdefault(objeto, evento)
    fallo: Optional[Tuple[str, str]] = None
    detalle_pendientes: List[str] = []

    def falla(codigo: str, contexto: str) -> None:
        nonlocal fallo
        if fallo is None:
            fallo = (codigo, contexto)

    if not bitacora.splitlines():
        falla("bitacora-ausente", f"no hay bitácora que leer en {bitacora_path}")
    obligatorios = ("id", "paso", "actor", "objeto", "resultado", "timestamp")
    for campo in obligatorios:
        for indice, evento in enumerate(eventos, 1):
            if campo not in evento:
                falla(f"evento-sin-{campo}", f"el evento {indice}º de la bitácora no declara {campo}")
    for evento in eventos:
        if "resultado" in evento and evento["resultado"] not in {"consumado", "rechazado"}:
            falla("resultado-fuera-de-enum", f"el evento {evento.get('id', '')} declara resultado=[{evento['resultado']}], fuera de {{consumado, rechazado}}")
    ids = Counter(evento["id"] for evento in eventos if "id" in evento)
    for evento in eventos:
        if "id" in evento and ids[evento["id"]] > 1:
            falla("evento-id-duplicado", f"el id {evento['id']} abre {ids[evento['id']]} eventos de la bitácora")
    for evento in eventos:
        if "id" in evento and not re.fullmatch(r"[0-9]+", evento["id"]):
            falla("orden-no-determinable", f"el evento con id [{evento['id']}] no lleva un entero comparable")
    if outcome == "archived":
        detalle_pendientes = [str(task["id"]) for task in tasks if task["status"] != "done"]
        if detalle_pendientes:
            falla("archive-con-tareas-pendientes", f"quedan {len(detalle_pendientes)} orchestration_tasks fuera de done: {', '.join(detalle_pendientes)}")
    for repo in repos:
        path, status = str(repo["path"]), str(repo["status"])
        if abierto[path] and path in despok:
            falla("despacho-exitoso-con-gate-abierto", f"el repo {path} se despachó con {abierto[path]} gate(s) fuera de done")
    for repo in repos:
        path, status = str(repo["path"]), str(repo["status"])
        if abierto[path] and elegible(status):
            falla("repo-bloqueado-promovido", f"el repo {path} está en {status} con {abierto[path]} gate(s) fuera de done")
    for repo in repos:
        path, status = str(repo["path"]), str(repo["status"])
        if hayreparto and status == "planned" and not retiene[path]:
            falla("repo-libre-sin-promover", f"el repo {path} sigue en planned y ninguna tarea gate lo retiene")
    for repo in repos:
        path, status = str(repo["path"]), str(repo["status"])
        if hayreparto and status == "planned" and retiene[path] and not abierto[path]:
            falla("gate-cerrado-sin-promover", f"el repo {path} sigue en planned con sus {retiene[path]} gate(s) en done")
    for repo in repos:
        path, status = str(repo["path"]), str(repo["status"])
        if status == "tasks-ready" and retiene[path] and not abierto[path] and path not in despok:
            falla("gate-cerrado-sin-despachar", f"el repo {path} se promovió al cerrar su gate y nunca se despachó")
    for repo in repos:
        path, status = str(repo["path"]), str(repo["status"])
        if path in planes_data and planes_data[path][2] and despachado(status):
            falla("despacho-con-baseline-blocked", f"el repo {path} está en {status} con una fila de baseline BLOCKED en su contrato local")
    for repo in repos:
        path, status = str(repo["path"]), str(repo["status"])
        if path in planes_data and planes_data[path][0] != status:
            falla("manifest-y-plan-divergen", f"el repo {path} vale {status} en el manifest y {planes_data[path][0]} en su plan.md")
    for indice, evento in enumerate(eventos):
        if evento.get("paso") == "liberar-lock" and evento.get("resultado") == "consumado":
            if not any("decision" in previo for previo in eventos[: indice + 1]):
                falla("liberacion-de-lock-sin-decision", f"el evento {evento.get('id', '')} liberó el lock de {evento.get('objeto', '')} sin una decisión registrada antes")
    for evento in eventos:
        paso, objeto, resultado = evento.get("paso", ""), evento.get("objeto", ""), evento.get("resultado", "")
        if paso == "cerrar-tarea":
            materializado = objeto in task_by_id and task_by_id[objeto]["status"] == "done"
        elif paso == "despachar-repo":
            materializado = objeto in repo_by_path and despachado(str(repo_by_path[objeto]["status"]))
        elif paso == "promover-repo":
            materializado = objeto in repo_by_path and promovido(str(repo_by_path[objeto]["status"]))
        else:
            continue
        if resultado == "consumado" and not materializado:
            falla("exito-sin-transicion", f"el evento {evento.get('id', '')} consumó {paso} sobre {objeto} y su estado no cambió")
        if resultado == "rechazado" and materializado:
            falla("rechazo-con-transicion", f"el evento {evento.get('id', '')} rechazó {paso} sobre {objeto} y su estado cambió igual")
    for task in tasks:
        if task["status"] == "done" and task["id"] not in cierreok:
            falla("transicion-sin-evento", f"la tarea {task['id']} está en done y ningún evento cerrar-tarea la consumó")
    for repo in repos:
        path, status = str(repo["path"]), str(repo["status"])
        if despachado(status) and path not in despok:
            falla("transicion-sin-evento", f"el repo {path} está en {status} y ningún evento despachar-repo lo consumó")
        if promovido(status) and path not in promok:
            falla("transicion-sin-evento", f"el repo {path} está en {status} y ningún evento promover-repo lo consumó")
    reporte = [str(task["id"]) for task in tasks if task["owner"] == "UNASSIGNED" and task["status"] != "done"]
    for task in tasks:
        if task["owner"] == "UNASSIGNED" and task["status"] == "done":
            falla("cierre-con-owner-unassigned", f"la tarea {task['id']} (phase={task['phase']}) cerró con owner UNASSIGNED")
    for task in tasks:
        if task["status"] != "done":
            continue
        for dependencia in task["depends_on"]:
            if dependencia not in task_by_id or task_by_id[dependencia]["status"] != "done":
                falla("depends_on-insatisfecho", f"la tarea {task['id']} cerró con {dependencia} fuera de done")
    for evento in eventos:
        if evento.get("paso") == "ejecutar-evidencia" and evento.get("resultado") == "consumado" and porfila[evento.get("fila", "")] > 1:
            falla("evidencia-duplicada", f"la fila {evento.get('fila', '')} la ejecutan {porfila[evento.get('fila', '')]} eventos de tareas distintas")
    owners: Dict[str, str] = {}
    for task in tasks:
        owner = str(task["owner"])
        if not owner or owner == "UNASSIGNED":
            continue
        if owner in owners:
            falla("dueno-duplicado", f"las tareas {owners[owner]} y {task['id']} declaran el mismo owner {owner}")
        owners[owner] = str(task["id"])
    for task in tasks:
        identificador = str(task["id"])
        if task["status"] != "done" or identificador not in fila:
            continue
        evento = evfila.get(fila[identificador])
        if evento and evento.get("objeto") != identificador:
            falla("evidencia-de-otra-tarea", f"la fila {fila[identificador]} de {identificador} la ejecutó un evento con objeto {evento.get('objeto', '')}")
        elif not evento and identificador in evobj:
            falla("evidencia-de-otra-fila", f"la tarea {identificador} cierra con {fila[identificador]} y su evidencia ejecutó {evobj[identificador].get('fila', '')}")
        elif not evento:
            falla("evidencia-obsoleta", f"la tarea {identificador} cerró sin ningún evento ejecutar-evidencia de su fila {fila[identificador]}")
    for task in tasks:
        identificador = str(task["id"])
        if task["status"] != "done" or identificador not in fila:
            continue
        evento = evfila.get(fila[identificador])
        if not evento or evento.get("objeto") != identificador:
            continue
        if evento.get("contrato") != f"v{vigente_num}":
            falla("evidencia-de-version-anterior", f"la fila {fila[identificador]} se midió contra el contrato {evento.get('contrato', '')} y la versión vigente es v{vigente_num}")
        participantes = list(task["participants"])
        if participantes:
            medidos = {}
            for par in evento.get("sha", "").split(","):
                if "=" in par:
                    nombre, valor = par.strip().split("=", 1)
                    if nombre:
                        medidos[nombre] = valor
            for repo in participantes:
                if repo not in medidos:
                    falla("repo-relevante-sin-sha", f"la tarea {identificador} participa {repo} y su evidencia no lo mide")
                elif repo in planes_data and medidos[repo] != planes_data[repo][1]:
                    falla("repo-cambiado-tras-medir", f"la tarea {identificador} midió {repo} en {medidos[repo]} y su plan.md declara {planes_data[repo][1]}")
        elif "ancla" not in evento:
            falla("ancla-versionada-ausente", f"la tarea {identificador} no participa ningún repo y su evidencia no declara ancla versionada")
        else:
            ancla = evento["ancla"]
            nombre, valor = ancla.split("=", 1) if "=" in ancla else (ancla, ancla)
            if nombre not in anclas or anclas[nombre] != valor:
                falla("ancla-versionada-obsoleta", f"la tarea {identificador} midió {nombre} en {valor} y la vigente es {anclas.get(nombre, 'ninguna declarada')}")
        if evento.get("observado") != esperado.get(identificador, ""):
            falla("esperado-no-satisfecho", f"la fila {fila[identificador]} esperaba [{esperado.get(identificador, '')}] y observó [{evento.get('observado', '')}]")
    for task in tasks:
        identificador = str(task["id"])
        if task["status"] == "done" and identificador in fila and task["done_when"] != fila[identificador]:
            falla("done_when-no-referencia-su-fila", f"la tarea {identificador} cierra en la fila {fila[identificador]} y su done_when dice {task['done_when'] or '—'}")
    if reporte:
        print("REPORTE:owner-unassigned")
        print(f"  sin dueño asignado y sin cerrar: {', '.join(reporte)}")
    if fallo is not None:
        print(f"GUARD:state {fallo[0]}", file=sys.stderr)
        print(f"  {fallo[1]}", file=sys.stderr)
        print(f"  manifest: {manifest_path}", file=sys.stderr)
        if detalle_pendientes:
            for pendiente in detalle_pendientes:
                print(f"DETALLE:{pendiente}", file=sys.stderr)
        return 1
    estado = "done"
    if any(task["status"] != "done" for task in tasks):
        estado = "no-verificado:integracion-pendiente"
    if any(not verde(str(repo["status"])) for repo in repos):
        estado = "en-curso"
    if any(task["phase"] == "gate" and task["status"] == "blocked" for task in tasks):
        estado = "no-verificado:gate-blocked"
    if any(repo["status"] == "blocked" for repo in repos):
        estado = "no-verificado:repo-blocked"
    if any(repo["status"] == "failed" for repo in repos):
        estado = "no-verificado:repo-failed"
    print(f"ESTADO:{estado}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
