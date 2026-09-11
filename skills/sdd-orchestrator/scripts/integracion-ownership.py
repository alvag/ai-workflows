"""Predicado: valida primero el par global de los planes recibidos; después ninguna fila de un AC
[integration] vive completa en el contrato de un repo, y cada repo referencia en solo-lectura
EXACTAMENTE los AC en los que participating_repos lo declara participante —ni uno de menos ni uno de
más, y ninguno cuando no participa en ninguno—, con la evidencia N/A: orchestration-owned y
apuntando a la fila autoritativa V-<id-tarea>.
Un solo diagnóstico por corrida: gana el primero del orden de abajo, que mira la forma de cada
fila antes que el conjunto del repo, porque son dos defectos distintos sobre la misma referencia."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from _yaml import DeliveryDependency, delivery_modulo, parsear_valor_yaml


OWNED = "N/A: orchestration-owned"
VIEJO = "N/A: Fase 3"


def escalar(valor: str) -> str:
    parsed = parsear_valor_yaml(valor)
    return parsed if isinstance(parsed, str) else ""


def lista(valor: str) -> List[str]:
    parsed = parsear_valor_yaml(valor)
    if isinstance(parsed, list):
        return parsed
    return [parsed] if parsed else []


def parsear_manifest(texto: str) -> Tuple[Dict[str, List[str]], List[Dict[str, object]]]:
    root: Dict[str, List[str]] = {"delivery_profile": [], "risk": []}
    tasks: List[Dict[str, object]] = []
    seccion = ""
    task: Optional[Dict[str, object]] = None
    campo = ""
    id_col = -1
    mapa = False
    clave = ""
    for linea in texto.splitlines():
        if re.match(r"^\s*#", linea):
            continue
        if linea and not linea[0].isspace():
            scalar = re.match(r"^(delivery_profile|risk)\s*:\s*(.*)$", linea)
            if scalar:
                root[scalar.group(1)].append(escalar(scalar.group(2)))
                seccion = ""
            else:
                seccion = "tasks" if re.fullmatch(
                    r"orchestration_tasks:\s*(?:#.*)?", linea) else ""
            continue
        if seccion != "tasks":
            continue
        nonspace = len(linea) - len(linea.lstrip())
        match = re.match(r"^\s*-\s*id:\s*(.*)$", linea)
        if match:
            id_col = linea.index("id:")
            task = {"id": escalar(match.group(1)), "covers_ac": [], "participating": []}
            tasks.append(task)
            campo, mapa, clave = "", False, ""
            continue
        if task is None:
            continue
        if nonspace > id_col:
            item = re.match(r"^\s*-\s+(.*)$", linea)
            entrada = re.match(r"^\s*([^\s:]+):\s*(.*)$", linea)
            if mapa:
                if item and clave:
                    task["participating"][-1][1].append(escalar(item.group(1)))
                elif entrada:
                    clave = escalar(entrada.group(1))
                    task["participating"].append((clave, lista(entrada.group(2))))
            elif campo == "covers_ac" and item:
                task["covers_ac"].append(escalar(item.group(1)))
            continue
        if nonspace != id_col:
            continue
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", linea)
        if not match:
            continue
        campo, valor = match.group(1), match.group(2)
        mapa = False
        if campo == "participating_repos":
            mapa = not valor.strip()
        elif campo == "covers_ac":
            task["covers_ac"] = lista(valor)
    return root, tasks


def parsear_plan(path: Path, helper) -> Tuple[str, List[Tuple[str, str, str, str]], object]:
    parsed = helper.read_plan_frontmatter(path)
    fields = parsed.fields
    repo_values = fields.get("repo", ())
    complexity_values = fields.get("complexity", ())
    if len(repo_values) > 1:
        raise helper.DeliveryProfileError("clave-duplicada", f"{path} repite repo")
    repo = repo_values[0] if repo_values else ""
    if len(complexity_values) > 1:
        raise helper.DeliveryProfileError("clave-duplicada", f"{path} repite complexity")
    complexity = complexity_values[0] if complexity_values else ""
    pair = helper.resolve_delivery_pair(fields, complexity)
    filas = []
    for linea in parsed.body_lines:
        if not linea.lstrip().startswith("|") or "[integration]" not in linea:
            continue
        limpia = linea.strip()
        if not limpia.endswith("|"):
            continue
        celdas = [celda.strip() for celda in limpia[1:-1].split("|")]
        if len(celdas) != 6 or celdas[0] == "ID":
            continue
        ac = re.search(r"AC-[0-9]+", celdas[1])
        if ac:
            filas.append((ac.group(0), celdas[2], celdas[3], celdas[5]))
    return repo, filas, pair


def validar_perfil(
        root: Dict[str, List[str]], planes: List[Tuple[str, object]], helper,
) -> Optional[Tuple[str, str, Optional[str]]]:
    root_present = bool(root["delivery_profile"] or root["risk"])
    plan_present = any(not pair.legacy for _repo, pair in planes)
    if not root_present and not plan_present:
        return None
    for key in ("delivery_profile", "risk"):
        if len(root[key]) > 1:
            return "clave-duplicada", f"el manifest repite {key}", None
    try:
        pair = helper.resolve_delivery_pair(root, None)
    except helper.DeliveryProfileError as error:
        return error.code, error.message, None
    if pair.legacy:
        return "carrier-mixto", "manifest y todos los planes deben materializar el par juntos", None
    if any(plan_pair.legacy for _repo, plan_pair in planes):
        repo = next(repo for repo, plan_pair in planes if plan_pair.legacy)
        return "carrier-mixto", "manifest y todos los planes deben materializar el par juntos", repo
    for repo, plan_pair in planes:
        if plan_pair.profile != pair.profile or plan_pair.risk != pair.risk:
            return ("perfil-manifest-plan-diverge",
                    f"el par del plan {repo} difiere del manifest", repo)
    return None


def main() -> int:
    if len(sys.argv) < 2:
        print("ARNES:integracion-ownership argumentos invalidos", file=sys.stderr)
        return 99
    manifest_path = Path(sys.argv[1])
    if any(not item.strip() for item in sys.argv[2:]):
        print("ARNES:integracion-ownership repo_plans vacio", file=sys.stderr)
        return 99
    planes = [Path(item) for item in sys.argv[2:]]
    if not manifest_path.is_file():
        print(f"ARNES:no existe el manifest {manifest_path}", file=sys.stderr)
        return 99
    for plan in planes:
        if not plan.is_file():
            print(f"ARNES:no existe el plan {plan}", file=sys.stderr)
            return 99
    try:
        helper = delivery_modulo()
    except DeliveryDependency as error:
        print(f"ARNES:integracion-ownership delivery-profile-helper-{error.kind}", file=sys.stderr)
        return 99
    root, tasks = parsear_manifest(manifest_path.read_text(encoding="utf-8"))
    parsed_plans = []
    for path in planes:
        try:
            parsed_plans.append((path, parsear_plan(path, helper)))
        except helper.DeliveryProfileError as error:
            print(f"GUARD:integracion {error.code}", file=sys.stderr)
            print(f"  {error.message}", file=sys.stderr)
            print(f"  plan: {path}", file=sys.stderr)
            return 1
    profile_failure = validar_perfil(
        root, [(repo, pair) for _path, (repo, _rows, pair) in parsed_plans], helper)
    if profile_failure is not None:
        print(f"GUARD:integracion {profile_failure[0]}", file=sys.stderr)
        print(f"  {profile_failure[1]}", file=sys.stderr)
        source = next((path for path, (repo, _rows, _pair) in parsed_plans
                       if repo == profile_failure[2]), None)
        print(f"  {'plan' if source else 'manifest'}: {source or manifest_path}", file=sys.stderr)
        return 1
    autoritativa = {}
    participa: Set[Tuple[str, str]] = set()
    esperados: Dict[str, List[str]] = {}
    for task in tasks:
        for ac in task["covers_ac"]:
            autoritativa.setdefault(ac, f"V-{task['id']}")
        for ac, repos in task["participating"]:
            for repo in repos:
                if (repo, ac) not in participa:
                    participa.add((repo, ac))
                    esperados.setdefault(repo, []).append(ac)
    fallo: Optional[Tuple[str, str, Path]] = None

    def falla(codigo: str, contexto: str, archivo: Path) -> None:
        nonlocal fallo
        if fallo is None:
            fallo = (codigo, contexto, archivo)

    presentes: Dict[str, Set[str]] = {}
    for plan, (repo, filas, _pair) in parsed_plans:
        if not repo:
            print(f"ARNES:el plan {plan} no declara repo: en su frontmatter", file=sys.stderr)
            return 99
        presentes[repo] = set()
        for ac, evidencia, observacion, baseline in filas:
            presentes[repo].add(ac)
            if VIEJO in evidencia or VIEJO in baseline:
                falla("referencia-obsoleta-fase-3", f"el repo {repo} referencia {ac} con el literal viejo, que anuncia una fase y no un dueño", plan)
            elif "NOT_APPLICABLE" in evidencia or "NOT_APPLICABLE" in baseline:
                falla("fila-integration-not-applicable", f"el repo {repo} marca NOT_APPLICABLE la fila de {ac}, que borraría una obligación global", plan)
            elif evidencia != OWNED or baseline != OWNED:
                falla("fila-integration-con-evidencia-local", f"el repo {repo} cierra {ac} de su lado: evidencia [{evidencia}] y baseline [{baseline}]", plan)
            else:
                referencia = re.search(r"V-[A-Za-z0-9_.-]+", observacion)
                actual = referencia.group(0) if referencia else ""
                if autoritativa.get(ac) and actual != autoritativa[ac]:
                    falla("referencia-a-fila-equivocada", f"el repo {repo} referencia {ac} apuntando a [{actual}], y su fila autoritativa es {autoritativa[ac]}", plan)
    for plan, (repo, _rows, _pair) in parsed_plans:
        faltan = [ac for ac in esperados.get(repo, []) if ac not in presentes.get(repo, set())]
        if faltan:
            falla("referencia-esperada-ausente", f"el repo {repo} participa en {', '.join(faltan)} y no lo referencia", plan)
    for plan, (repo, _rows, _pair) in parsed_plans:
        sobran = [ac for ac in presentes.get(repo, set()) if (repo, ac) not in participa]
        if sobran:
            falla("referencia-en-repo-no-participante", f"el repo {repo} referencia {', '.join(sorted(sobran))}, y participating_repos no lo declara participante", plan)
    if fallo is None:
        return 0
    print(f"GUARD:integracion {fallo[0]}", file=sys.stderr)
    print(f"  {fallo[1]}", file=sys.stderr)
    print(f"  plan: {fallo[2]}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
