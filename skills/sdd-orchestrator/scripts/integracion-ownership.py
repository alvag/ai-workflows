"""Predicado: ninguna fila de un AC [integration] vive completa en el contrato de un repo, y cada
repo referencia en solo-lectura EXACTAMENTE los AC en los que participating_repos lo declara
participante —ni uno de menos ni uno de más, y ninguno cuando no participa en ninguno—, con la
evidencia N/A: orchestration-owned y apuntando a la fila autoritativa V-<id-tarea>.
Un solo diagnóstico por corrida: gana el primero del orden de abajo, que mira la forma de cada
fila antes que el conjunto del repo, porque son dos defectos distintos sobre la misma referencia."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from _yaml import parsear_valor_yaml


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


def parsear_manifest(texto: str) -> List[Dict[str, object]]:
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
            seccion = "tasks" if re.fullmatch(r"orchestration_tasks:\s*(?:#.*)?", linea) else ""
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
    return tasks


def parsear_plan(path: Path) -> Tuple[str, List[Tuple[str, str, str, str]]]:
    texto = path.read_text(encoding="utf-8")
    repo = ""
    frontmatter = 0
    filas = []
    for linea in texto.splitlines():
        if re.fullmatch(r"---\s*", linea):
            frontmatter += 1
            continue
        if frontmatter == 1:
            match = re.match(r"^repo:\s*(.*)$", linea)
            if match:
                repo = match.group(1).strip()
            continue
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
    return repo, filas


def main() -> int:
    if len(sys.argv) != 3:
        print("ARNES:integracion-ownership argumentos invalidos", file=sys.stderr)
        return 99
    manifest_path = Path(sys.argv[1])
    planes = [Path(item) for item in sys.argv[2].split()]
    if not manifest_path.is_file():
        print(f"ARNES:no existe el manifest {manifest_path}", file=sys.stderr)
        return 99
    for plan in planes:
        if not plan.is_file():
            print(f"ARNES:no existe el plan {plan}", file=sys.stderr)
            return 99
    tasks = parsear_manifest(manifest_path.read_text(encoding="utf-8"))
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
    for plan in planes:
        repo, filas = parsear_plan(plan)
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
    for plan in planes:
        repo, _ = parsear_plan(plan)
        faltan = [ac for ac in esperados.get(repo, []) if ac not in presentes.get(repo, set())]
        if faltan:
            falla("referencia-esperada-ausente", f"el repo {repo} participa en {', '.join(faltan)} y no lo referencia", plan)
    for plan in planes:
        repo, _ = parsear_plan(plan)
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
