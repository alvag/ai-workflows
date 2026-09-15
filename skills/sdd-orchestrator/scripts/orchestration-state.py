"""Predicado: valida primero el perfil, assessment, fold y carriers de los planes recibidos; después
el estado de la orquestación cierra contra su bitácora: ninguna tarea pasa a `done` sin dueño real,
con un `depends_on` abierto o evidencia fresca de su propia fila; ningún repo se despacha con su gate
abierto o baseline local en `BLOCKED`, ni queda sin promover con el gate cerrado; cada evento lleva
seis campos, un `resultado` del enum y un `id` único y comparable; solo un resultado consumado
materializa su transición; además valida fase, claves congeladas, adopción, reparación y orden entre
anclas del contrato de integración, sin duplicar el parser global; y la precedencia nunca oculta el estado agregado más grave.
Un solo diagnóstico por corrida: gana el primero del orden de abajo, que es el de la fábrica."""

from __future__ import annotations

import re
import sys
import hashlib
import importlib.util
from collections import Counter, defaultdict
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Optional, Set, Tuple

from _yaml import (AssessmentError, DeliveryDependency, delivery_modulo, parsear_perfil_manifest,
                   parsear_valor_yaml, plegar_riesgo, validar_assessment)


USO = ("USO:orchestration-state manifest master_spec integration_contract log "
       "phase(candidate/final) [repo_plan ...]")
OPERACIONES = {
    "cobertura-agregada", "esperado-corregido", "pertinencia-corregida",
    "verificacion-corregida",
}
CLASES = {
    "IMPLEMENTATION_DEFECT", "VERIFICATION_DEFECT", "ENVIRONMENT_FAILURE", "DESIGN_GAP",
}


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


def parsear_manifest(
        texto: str,
) -> Tuple[str, List[Dict[str, str]], List[Dict[str, object]], Dict[str, object],
           Dict[str, List[str]]]:
    outcome = ""
    repos: List[Dict[str, str]] = []
    tasks: List[Dict[str, object]] = []
    seccion = ""
    repo: Optional[Dict[str, str]] = None
    task: Optional[Dict[str, object]] = None
    campo = ""
    id_col = -1
    mapa = False
    contract_state: Dict[str, List[str]] = {
        "integration_contract_frozen_version": [],
        "integration_contract_frozen_hash": [],
    }
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
                root_match = re.match(
                    r"^(integration_contract_frozen_version|integration_contract_frozen_hash)"
                    r"\s*:\s*(.*)$", linea)
                if root_match:
                    contract_state[root_match.group(1)].append(escalar(root_match.group(2)))
            continue
        if seccion == "repos":
            item = re.match(r"^\s{2}-\s*(.*)$", linea)
            if item:
                repo = {"path": "", "status": ""}
                repos.append(repo)
                match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)", item.group(1))
            else:
                match = re.match(r"^\s{4}([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", linea)
            if match and repo is not None and match.group(1) in {"path", "status"}:
                repo[match.group(1)] = escalar(match.group(2))
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
    return outcome, repos, tasks, parsear_perfil_manifest(texto), contract_state


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


def cargar_parser_reparaciones() -> ModuleType:
    """Carga por ruta absoluta la gramática que posee cross-implement."""
    ruta = (Path(__file__).resolve().parents[2] / "cross-implement" / "scripts" /
            "contrato-invariantes.py")
    if not ruta.is_file():
        raise RuntimeError("ausente")
    especificacion = importlib.util.spec_from_file_location(
        "sdd_orchestrator_contrato_invariantes", ruta)
    if especificacion is None or especificacion.loader is None:
        raise RuntimeError("incompatible")
    modulo = importlib.util.module_from_spec(especificacion)
    try:
        especificacion.loader.exec_module(modulo)
    except Exception as error:
        raise RuntimeError("incompatible") from error
    if not callable(getattr(modulo, "parsear_reparaciones", None)):
        raise RuntimeError("incompatible")
    return modulo


def _campos_linea(linea: str) -> Dict[str, str]:
    return {
        match.group(1): match.group(2)
        for match in re.finditer(r"`([^`:]+): ([^`]*)`", linea)
    }


def _bloques_contrato(texto: str) -> List[Tuple[int, List[str]]]:
    """Separa versiones solo para resolver el estado local; no parsea reparaciones."""
    lineas = texto.splitlines()
    resultado: List[Tuple[int, List[str]]] = []
    for indice, linea in enumerate(lineas):
        match = re.fullmatch(r"(#+) v([1-9][0-9]*)", linea)
        if match is None:
            continue
        nivel = len(match.group(1))
        bloque = [linea]
        for siguiente in lineas[indice + 1:]:
            encabezado = re.match(r"^(#+) ", siguiente)
            if encabezado and len(encabezado.group(1)) <= nivel:
                break
            bloque.append(siguiente)
        resultado.append((int(match.group(2)), bloque))
    return sorted(resultado)


def _estado_versiones(texto: str) -> Dict[int, Dict[str, object]]:
    tablas = {numero: filas for numero, filas in parsear_contrato(texto)}
    resultado: Dict[int, Dict[str, object]] = {}
    for numero, bloque in _bloques_contrato(texto):
        original = "\n".join(bloque)
        hash_match = re.search(r"`hash: ([0-9a-f]*)`", original)
        pertinencias = {}
        for linea in bloque:
            if linea.strip().startswith("- pertinencia: "):
                campos = _campos_linea(linea)
                if campos.get("id"):
                    pertinencias[campos["id"]] = campos
        resultado[numero] = {
            "hash": hash_match.group(1) if hash_match else "",
            "filas": {fila[0]: fila for fila in tablas.get(numero, []) if len(fila) == 6},
            "pertinencias": pertinencias,
        }
    return resultado


def _version_evento(evento: Dict[str, str]) -> Optional[int]:
    match = re.fullmatch(r"contrato-integracion:v([1-9][0-9]*)", evento.get("objeto", ""))
    return int(match.group(1)) if match else None


def _clasificar_sha_repos(valor: str, participantes: Set[str]) -> Optional[str]:
    pares = []
    for fragmento in valor.split(", ") if valor else []:
        if "=" not in fragmento:
            return "repos"
        repo, sha = fragmento.split("=", 1)
        if not repo or not re.fullmatch(r"[0-9a-f]{7,64}", sha):
            return "repos"
        pares.append((repo, sha))
    repos = [repo for repo, _sha in pares]
    if len(repos) != len(set(repos)) or set(repos) != participantes:
        return "repos"
    if repos != sorted(repos, key=lambda item: item.encode("utf-8")):
        return "orden"
    return None


def validar_estado_contrato(
        phase: str, contract_state: Dict[str, List[str]], contrato: str,
        reparaciones: List[Tuple[int, Dict[str, str]]], eventos: List[Dict[str, str]],
        tasks: List[Dict[str, object]]) -> Optional[Tuple[str, str]]:
    """Aplica solo las restricciones locales de integración, sin duplicar la gramática global."""
    versiones = _estado_versiones(contrato)
    if not versiones:
        return "contrato-sin-version-vigente", "el contrato de integración no contiene versiones"
    vigente = max(versiones)
    if sorted(versiones) != list(range(1, vigente + 1)):
        return "versiones-no-contiguas", "las versiones del contrato de integración tienen un salto"
    valores_version = contract_state["integration_contract_frozen_version"]
    valores_hash = contract_state["integration_contract_frozen_hash"]
    if len(valores_version) > 1 or len(valores_hash) > 1:
        return "estado-contrato-duplicado", "el manifest repite una clave congelada de integración"
    if bool(valores_version) != bool(valores_hash):
        return "estado-contrato-parcial", "el manifest materializa solo una clave congelada"
    frozen: Optional[Tuple[int, str]] = None
    if valores_version:
        if not re.fullmatch(r"[1-9][0-9]*", valores_version[0]) or not re.fullmatch(
                r"[0-9a-f]{64}", valores_hash[0]):
            return "estado-contrato-invalido", "las claves congeladas no usan versión y SHA-256 canónicos"
        frozen = (int(valores_version[0]), valores_hash[0])

    adopciones: List[Tuple[int, int, Dict[str, str]]] = []
    aprobaciones: List[Tuple[int, int, Dict[str, str]]] = []
    clasificaciones: List[Tuple[int, Dict[str, str]]] = []
    task_by_id = {str(task["id"]): task for task in tasks}
    for indice, evento in enumerate(eventos):
        paso = evento.get("paso")
        if paso == "adoptar-estado-contrato":
            version = _version_evento(evento)
            if version is None or evento.get("actor") != "orquestador" or evento.get("resultado") not in {
                    "consumado", "rechazado"} or evento.get("modo") not in {
                        "materializacion", "adopcion-retroactiva"}:
                return "evento-contrato-invalido", "adoptar-estado-contrato tiene forma inválida"
            if evento.get("hash") != versiones.get(version, {}).get("hash"):
                return "evento-contrato-hash-diverge", f"el ancla de v{version} no coincide con el contrato"
            if evento.get("resultado") == "consumado":
                adopciones.append((indice, version, evento))
        elif paso == "aprobar-reparación":
            version = _version_evento(evento)
            if version is None or evento.get("actor") != "usuario" or evento.get("resultado") not in {
                    "consumado", "rechazado"} or not evento.get("token") or not evento.get("hash"):
                return "aprobacion-contrato-invalida", "aprobar-reparación tiene forma inválida"
            if evento.get("resultado") == "consumado":
                aprobaciones.append((indice, version, evento))
        elif paso == "clasificar-falla":
            obligatorios = {"sha", "delta", "fix_round", "checkId", "clase", "consumedRound", "evidencia"}
            if evento.get("actor") != "orquestador" or not all(
                    evento.get(campo) for campo in obligatorios):
                return "clasificacion-incompleta", "clasificar-falla carece de campos locales obligatorios"
            if evento.get("resultado") != "consumado":
                return "clasificacion-no-consumada", "clasificar-falla debe registrar resultado consumado"
            task = task_by_id.get(evento.get("objeto", ""))
            if task is None:
                return "clasificacion-tarea-invalida", "clasificar-falla no resuelve la tarea que ejecutó el check"
            participantes = set(task["participants"])
            sha = evento.get("sha", "")
            defecto_sha = _clasificar_sha_repos(sha, participantes)
            if defecto_sha == "repos":
                return "clasificacion-sha-repos", "clasificar-falla no declara el conjunto exacto de repos"
            if defecto_sha == "orden":
                return "clasificacion-sha-orden", "clasificar-falla no ordena los repos canónicamente"
            digest = hashlib.sha256(sha.encode("utf-8")).hexdigest()
            if evento.get("delta") != "repos-sha256:" + digest:
                return "clasificacion-delta-invalido", "clasificar-falla no liga delta con el mapa de repos"
            if evento.get("clase") not in CLASES:
                return "clasificacion-fuera-de-enum", "clasificar-falla declara una clase desconocida"
            clasificaciones.append((indice, evento))

    retroactivas = [item for item in adopciones if item[2].get("modo") == "adopcion-retroactiva"]
    if len(retroactivas) > 1:
        return "adopcion-retroactiva-duplicada", "la corrida registra más de una adopción retroactiva"
    if frozen is not None:
        if not adopciones:
            return "estado-contrato-sin-ancla", "las claves congeladas carecen de adoptar-estado-contrato"
        ultima = adopciones[-1]
        if (ultima[1], ultima[2].get("hash", "")) != frozen:
            return "estado-contrato-diverge", "el último ancla consumada no coincide con las claves congeladas"
    if phase == "final":
        esperado = (vigente, str(versiones[vigente]["hash"]))
        if frozen != esperado or not adopciones or adopciones[-1][1] != vigente:
            return "estado-contrato-sin-ancla", "final exige materializar la versión vigente y su hash"

    primera_ancla = adopciones[0][0] if adopciones else None
    ancla_por_version = {version: indice for indice, version, _evento in adopciones}
    aprobacion_por_token = {
        evento.get("token", ""): (indice, version, evento)
        for indice, version, evento in aprobaciones
    }
    reparaciones_por_version_id: Dict[Tuple[int, str], Set[str]] = defaultdict(set)
    for version, reparacion in reparaciones:
        identificador = reparacion.get("id", "")
        operacion = reparacion.get("operación", "")
        reparaciones_por_version_id[(version, identificador)].add(operacion)
        if operacion not in OPERACIONES:
            continue
        aprobacion = aprobacion_por_token.get(reparacion.get("token", ""))
        if aprobacion is None:
            if phase == "final" or version < vigente:
                return "reparacion-sin-aprobacion", f"v{version}:{identificador} no tiene aprobación consumada"
            continue
        indice_aprobacion, version_aprobada, evento = aprobacion
        if version_aprobada != version or evento.get("hash") != versiones.get(version, {}).get("hash"):
            return "reparacion-aprobacion-diverge", f"v{version}:{identificador} no coincide con su aprobación"
        if operacion == "cobertura-agregada":
            if primera_ancla is not None and indice_aprobacion > primera_ancla:
                return "cobertura-agregada-post-ancla", "la integración no admite filas tras su primera ancla"
        else:
            previa = max((n for n in ancla_por_version if n < version), default=None)
            if previa is not None and indice_aprobacion <= ancla_por_version[previa]:
                return "aprobacion-anterior-al-ancla", f"v{version}:{identificador} se aprobó antes de su predecesora"
            if version in ancla_por_version and indice_aprobacion >= ancla_por_version[version]:
                return "aprobacion-posterior-al-ancla", f"v{version}:{identificador} se aprobó después de materializarla"

    for (version, identificador), operaciones in reparaciones_por_version_id.items():
        if "verificacion-corregida" not in operaciones:
            continue
        reparacion = next(
            valores for numero, valores in reparaciones
            if numero == version and valores.get("id") == identificador
            and valores.get("operación") == "verificacion-corregida")
        pertinencia_actual = versiones.get(version, {}).get("pertinencias", {}).get(identificador, {})
        pertinencia_previa = versiones.get(version - 1, {}).get("pertinencias", {}).get(identificador, {})
        emparejada = "pertinencia-corregida" in operaciones and \
            pertinencia_actual.get("baseline_tipo", "").startswith("fallos-")
        mecanica = (operaciones == {"verificacion-corregida"}
                    and reparacion.get("campos") == "comando"
                    and pertinencia_previa.get("baseline_tipo", "").startswith("fallos-")
                    and pertinencia_actual.get("baseline_tipo", "").startswith("fallos-"))
        if mecanica:
            aprobacion = aprobacion_por_token.get(reparacion.get("token", ""))
            ordinal = aprobacion[2].get("verification_defect_ordinal", "") if aprobacion else ""
            mecanica = any(
                indice < (aprobacion[0] if aprobacion else len(eventos))
                and evento.get("checkId") == identificador
                and evento.get("clase") == "VERIFICATION_DEFECT"
                and evento.get("contract_version") == str(version)
                and evento.get("verification_defect_ordinal") == ordinal
                for indice, evento in clasificaciones)
        if not (emparejada or mecanica):
            return "verificacion-no-admitida", (
                f"v{version}:{identificador} no es una transición local admitida de verificación")

    if phase == "candidate" and frozen is not None:
        posteriores = [item for item in aprobaciones if item[0] > adopciones[-1][0]]
        if posteriores and sorted({version for _i, version, _e in posteriores}) != list(
                range(frozen[0] + 1, vigente + 1)):
            return "secuencia-candidate-no-contigua", "las aprobaciones posteriores no forman una secuencia contigua"
    if phase == "final" and adopciones:
        if any(indice > adopciones[-1][0] for indice, _version, _evento in aprobaciones):
            return "aprobacion-pendiente", "final conserva una aprobación posterior al último ancla"
    return None


def parsear_plan(path: Path, helper) -> Tuple[str, str, str, bool, str, object]:
    parsed = helper.read_plan_frontmatter(path)
    fields = parsed.fields
    repo_values = fields.get("repo", ())
    status_values = fields.get("status", ())
    sha_values = fields.get("head_sha", ())
    complexity_values = fields.get("complexity", ())
    if len(repo_values) > 1:
        raise helper.DeliveryProfileError("clave-duplicada", f"{path} repite repo")
    repo = repo_values[0] if repo_values else ""
    status = status_values[-1] if status_values else ""
    sha = sha_values[-1] if sha_values else ""
    if len(complexity_values) > 1:
        raise helper.DeliveryProfileError("clave-duplicada", f"{path} repite complexity")
    complexity = complexity_values[0] if complexity_values else ""
    pair = helper.resolve_delivery_pair(fields, complexity)
    blocked = False
    for linea in parsed.body_lines:
        limpia = linea.strip()
        if limpia.startswith("|") and limpia.endswith("|"):
            celdas = [celda.strip() for celda in limpia[1:-1].split("|")]
            if celdas and celdas[-1] == "BLOCKED":
                blocked = True
    return repo, status, sha, blocked, complexity, pair


def validar_perfil(profile: Dict[str, object], planes: List[Tuple[str, str, str, bool, str, object]],
                    helper, plan_paths: List[Path]) -> Optional[Tuple[str, str, Optional[Path]]]:
    root = profile["root"]
    assessment = profile["assessment"]
    assessment_sections = profile["assessment_sections"]
    assessment_invalid = profile["assessment_invalid"]
    manifest_repos = profile["repos"]
    repos_sections = profile["repos_sections"]
    repos_invalid = profile["repos_invalid"]
    root_present = bool(root["delivery_profile"] or root["risk"])
    repo_present = any(repo["complexity"] or repo["risk"] for repo in manifest_repos)
    plan_present = any(not plan[5].legacy for plan in planes)
    if not (root_present or assessment_sections or repo_present or plan_present
            or repos_sections > 1):
        return None

    if repos_sections > 1:
        return "clave-duplicada", "el manifest repite repos", None
    if assessment_sections > 1:
        return "clave-duplicada", "el manifest repite delivery_assessment", None
    for key in ("delivery_profile", "risk"):
        if len(root[key]) > 1:
            return "clave-duplicada", f"el manifest repite {key}", None
    if repos_invalid:
        return ("repos-forma-invalida",
                "repos y sus filas deben usar lista en bloque con sangría 2/4 y listas inline", None)
    if assessment_invalid:
        return ("assessment-forma-invalida",
                "delivery_assessment debe expresarse como lista en bloque con sangría 2/4", None)
    try:
        pair = helper.resolve_delivery_pair(root, None)
    except helper.DeliveryProfileError as error:
        return error.code, error.message, None
    if pair.legacy:
        return "carrier-mixto", "el manifest no materializa el par pero otro carrier sí", None
    if planes and any(plan[5].legacy for plan in planes):
        source = next(path for path, plan in zip(plan_paths, planes) if plan[5].legacy)
        return "carrier-mixto", "no todos los planes materializan el par", source

    if any(repo["duplicates"] for repo in manifest_repos):
        return "clave-duplicada", "una entrada de repos repite path", None
    repo_paths = [str(repo["path"]) for repo in manifest_repos]
    if len(repo_paths) != len(set(repo_paths)):
        return "repo-duplicado", "repos contiene paths duplicados", None
    plan_repos = [plan[0] for plan in planes]
    if len(plan_repos) != len(set(plan_repos)):
        duplicate_index = next(index for index, repo in enumerate(plan_repos)
                               if repo in plan_repos[:index])
        return ("plan-repo-duplicado", "varios planes declaran el mismo repo",
                plan_paths[duplicate_index])
    try:
        scopes = validar_assessment(assessment)
    except AssessmentError as error:
        return error.code, error.message, None
    expected_scopes = {"global", "integration"} | {f"repo:{path}" for path in repo_paths}
    if set(scopes) != expected_scopes:
        return ("assessment-scopes-divergen",
                f"esperado={sorted(expected_scopes)} actual={sorted(scopes)}", None)

    folded = plegar_riesgo(scopes, repo_paths)
    if scopes["global"]["risk"] != folded or pair.risk != folded:
        return ("risk-fold-diverge",
                f"fold={folded}, global={scopes['global']['risk']}, manifest={pair.risk}", None)

    repos_by_path = {str(repo["path"]): repo for repo in manifest_repos}
    plans_by_repo = {plan[0]: plan for plan in planes}
    plan_sources = {plan[0]: path for path, plan in zip(plan_paths, planes)}
    if not set(plans_by_repo) <= set(repos_by_path):
        repo = next(path for path in plans_by_repo if path not in repos_by_path)
        return ("carrier-mixto", "un plan no corresponde a ningún repo del manifest",
                plan_sources[repo])
    for path, repo in repos_by_path.items():
        if len(repo["complexity"]) != 1 or len(repo["risk"]) != 1:
            return ("carrier-mixto",
                    f"repo {path} no materializa complexity y risk exactamente una vez", None)
        row = scopes[f"repo:{path}"]
        if repo["complexity"][0] != row["complexity"]:
            return ("complexity-assessment-manifest-plan-diverge",
                    f"assessment y manifest divergen para {path}", None)
        if repo["risk"][0] != row["risk"]:
            return ("risk-assessment-manifest-diverge",
                    f"assessment y manifest divergen para {path}", None)
        plan = plans_by_repo.get(path)
        if plan is None:
            continue
        if plan[4] != row["complexity"]:
            return ("complexity-assessment-manifest-plan-diverge",
                    f"assessment={row['complexity']}, plan={plan[4]} para {path}",
                    plan_sources[path])
        if plan[5].profile != pair.profile or plan[5].risk != pair.risk:
            return ("perfil-manifest-plan-diverge",
                    f"el par del plan {path} difiere del manifest", plan_sources[path])

    eligible = (folded == "low" and scopes["integration"]["risk"] == "low"
                and all(scopes[f"repo:{path}"]["complexity"] in {"trivial", "normal"}
                        and scopes[f"repo:{path}"]["risk"] == "low" for path in repo_paths))
    if pair.profile == "expedited" and not eligible:
        return "expedited-inelegible", "el fold o algún repo impide el perfil expedito", None
    return None


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
    if len(sys.argv) < 6:
        print("ARNES:orchestration-state argumentos invalidos", file=sys.stderr)
        return 99
    manifest_path, master_path, contrato_path, bitacora_path = map(Path, sys.argv[1:5])
    phase = sys.argv[5]
    if phase not in {"candidate", "final"}:
        print(USO, file=sys.stderr)
        return 2
    if any(not item.strip() for item in sys.argv[6:]):
        print("ARNES:orchestration-state repo_plans vacio", file=sys.stderr)
        return 99
    planes = [Path(item) for item in sys.argv[6:]]
    for path in (manifest_path, master_path, contrato_path):
        if not path.is_file():
            print(f"ARNES:no existe el artefacto {path}", file=sys.stderr)
            return 99
    for plan in planes:
        if not plan.is_file():
            print(f"ARNES:no existe el plan {plan}", file=sys.stderr)
            return 99
    try:
        helper = delivery_modulo()
    except DeliveryDependency as error:
        print(f"ARNES:orchestration-state delivery-profile-helper-{error.kind}", file=sys.stderr)
        return 99
    master = master_path.read_text(encoding="utf-8")
    manifest = manifest_path.read_text(encoding="utf-8")
    contrato = contrato_path.read_text(encoding="utf-8")
    bitacora = bitacora_path.read_text(encoding="utf-8") if bitacora_path.is_file() else ""
    anclas = parsear_master(master)
    outcome, repos, tasks, profile, contract_state = parsear_manifest(manifest)
    versiones = parsear_contrato(contrato)
    eventos = parsear_eventos(bitacora)
    parsed_plans = []
    for path in planes:
        try:
            parsed_plans.append(parsear_plan(path, helper))
        except helper.DeliveryProfileError as error:
            print(f"GUARD:state {error.code}", file=sys.stderr)
            print(f"  {error.message}", file=sys.stderr)
            print(f"  plan: {path}", file=sys.stderr)
            return 1
    profile_failure = validar_perfil(profile, parsed_plans, helper, planes)
    if profile_failure is not None:
        print(f"GUARD:state {profile_failure[0]}", file=sys.stderr)
        print(f"  {profile_failure[1]}", file=sys.stderr)
        source = profile_failure[2]
        print(f"  {'plan' if source else 'manifest'}: {source or manifest_path}", file=sys.stderr)
        return 1
    try:
        parser_contrato = cargar_parser_reparaciones()
        reparaciones = parser_contrato.parsear_reparaciones(contrato)
    except RuntimeError as error:
        print(f"ARNES:orchestration-state contrato-helper-{error}", file=sys.stderr)
        return 99
    planes_data = {
        repo: (status, sha, blocked, path, complexity, pair)
        for path, (repo, status, sha, blocked, complexity, pair) in zip(planes, parsed_plans)
    }
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
    contract_failure = validar_estado_contrato(
        phase, contract_state, contrato, reparaciones, eventos, tasks)
    if contract_failure is not None:
        falla(contract_failure[0], contract_failure[1])
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
