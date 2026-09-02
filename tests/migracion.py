"""Recalculo de la evidencia irrepetible de la migracion, **fuera del gate**.

Salio de `python3 -m tests` el 2026-08-31, y se corre a mano cuando alguien quiera auditar el
snapshot:

    python3 tests/migracion.py

**Por que salio.** `verify_report` comprueba que el tag anotado exista, que alcance el commit
registrado y que el arbol coincida, y despues **extrae ese commit a un temporal y recalcula la
evidencia desde ahi**. Es decir: no verifica el codigo actual — ningun cambio en el arbol puede
romperlo ni arreglarlo. Es un acta historica, el mismo patron que el baseline del sobre en vuelo.

**Y era flaky.** Ese recalculo ejecuta subprocesos reales con `timeout=30 s` sobre el arbol viejo:
medido, 26-29 s y verde con la maquina tranquila, 178-194 s y rojo bajo carga, con un conjunto
distinto de identidades divergentes en cada corrida. Un caso que da resultados distintos sobre el
mismo commit no acredita nada, y obligaba a un juicio a mano en cada gate.

La cobertura no se pierde: se comprobo que `validate_coverage` cierra sin el —los 397 tests
`escenario:` ya cubren los casos migrados y las guardas estan cubiertas por `firma:` y
`mutante-v24:`—, asi que su aporte era redundante.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


ENCODING = "utf-8"
ROOT = Path(__file__).resolve().parent.parent
INVENTORY = ROOT / "tests" / "inventario-bloques.md"
CATALOG = ROOT / "tests" / "casos" / "escenarios.jsonl"
HARNESS = ROOT / "scripts" / "verificar-paridad-powershell.py"
CORPUS = ROOT / "scripts" / "paridad-casos"
REPORT_TAG = "migracion/acta-dual"
REPORT_BLOB = "b6197383abf43ba292a74370d232e52e039ee5a4"
TAG = "migracion/snapshot-dual"
BASE_COMMIT = "5013b4589d5b6429f9705539268eb0d8ac7ae3fc"
EXPECTED_CASES = 397
EXPECTED_GUARDS = 37
EXPECTED_MARKERS = 70
SECTION_TARGETS = "## 1. Nombres base y destino propuesto"
SECTION_SIGNATURES = "## 6. Tabla cerrada de firmas"
EVIDENCE_START = "<!-- evidencia-migracion:inicio -->"
EVIDENCE_END = "<!-- evidencia-migracion:fin -->"


def _section(text: str, title: str) -> str:
    if text.count(title) != 1:
        raise ValueError("inventory section is missing or duplicated: " + title)
    return text.split(title, 1)[1].split("\n## ", 1)[0]


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) < 2 or not value.startswith("`") or not value.endswith("`"):
        raise ValueError("expected inline code: " + value)
    return value[1:-1]


def _load_harness(root: Path) -> ModuleType:
    path = root / "scripts" / "verificar-paridad-powershell.py"
    name = "dual_harness_" + hashlib.sha256(str(root).encode(ENCODING)).hexdigest()[:12]
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load the old harness from " + str(path))
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def _read_destinations(root: Path) -> Dict[str, Path]:
    text = (root / "tests" / "inventario-bloques.md").read_text(encoding=ENCODING)
    destinations: Dict[str, Path] = {}
    for line in _section(text, SECTION_TARGETS).splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line[1:-1].split("|")]
        if cells[2] == "guarda":
            destinations[_unquote(cells[0])] = root / _unquote(cells[3])
    if len(destinations) != EXPECTED_GUARDS:
        raise ValueError("expected 37 guard destinations, found " + str(len(destinations)))
    return destinations


def _read_arities(root: Path) -> Dict[str, int]:
    text = (root / "tests" / "inventario-bloques.md").read_text(encoding=ENCODING)
    arities: Dict[str, int] = {}
    for line in _section(text, SECTION_SIGNATURES).splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line[1:-1].split("|")]
        if _unquote(cells[1]).startswith("skills/"):
            arities[_unquote(cells[0])] = int(cells[3])
    if len(arities) != EXPECTED_GUARDS:
        raise ValueError("expected 37 signatures, found " + str(len(arities)))
    return arities


def _read_catalog(root: Path) -> Dict[str, dict]:
    scenarios: Dict[str, dict] = {}
    path = root / "tests" / "casos" / "escenarios.jsonl"
    for line in path.read_text(encoding=ENCODING).splitlines():
        value = json.loads(line)
        identity = value["identidad"]
        if identity in scenarios:
            raise ValueError("duplicate generated identity: " + identity)
        scenarios[identity] = value
    if len(scenarios) != EXPECTED_CASES:
        raise ValueError("expected 397 generated scenarios, found " + str(len(scenarios)))
    return scenarios


def _sha_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _sha_json(value: object) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode(ENCODING, "surrogateescape")
    return _sha_bytes(body)


def _event_value(event: object) -> dict:
    return {"id": event.id, "fields": list(event.campos)}


def _observation_value(harness: ModuleType, observation: object,
                       parsed: Tuple[List[object], List[str]], result_class: str) -> dict:
    events = sorted((_event_value(event) for event in parsed[0]),
                    key=lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True))
    stdout = harness.normalizar_stdout(observation.stdout)
    artifacts = harness.normalizar_artefactos(observation.artefactos)
    value = {
        "class": result_class,
        "events": events,
        "stdout_sha256": _sha_bytes(stdout.encode(ENCODING, "surrogateescape")),
        "artifacts": {
            path: _sha_bytes(content.encode(ENCODING, "surrogateescape"))
            for path, content in artifacts.items()
        },
        "code": observation.exit,
    }
    value["observation_sha256"] = _sha_json(value)
    return value


def _assert_scenario(root: Path, matrix: str, case: dict, scenario: dict) -> None:
    identity = matrix + "/" + case["nombre"]
    if scenario["identidad"] != identity:
        raise AssertionError("generated scenario changed identity: " + identity)
    if scenario["matriz"] != matrix or scenario["caso"] != case["nombre"]:
        raise AssertionError("generated scenario does not reproduce matrix/case: " + identity)
    if scenario["entradas"] != case.get("entradas", {}):
        raise AssertionError("generated scenario changed inputs: " + identity)
    if scenario["reemplazos"] != case.get("reemplazos", []):
        raise AssertionError("generated scenario changed replacements: " + identity)
    fixture = case.get("fixture", "")
    expected_fixture = "scripts/paridad-casos/{0}/fixtures/{1}/".format(matrix, fixture)
    if scenario["fixture"] != expected_fixture:
        raise AssertionError("generated scenario changed fixture: " + identity)
    matrix_path = root / "scripts" / "paridad-casos" / matrix / "casos.json"
    if scenario["hash_matriz"] != _sha_bytes(matrix_path.read_bytes()):
        raise AssertionError("generated scenario changed matrix hash: " + identity)


def _new_body(script: Path, input_names: Sequence[str]) -> str:
    command = [shlex.quote(sys.executable), shlex.quote(str(script))]
    command.extend('"${' + name + '}"' for name in input_names)
    return "export PYTHONDONTWRITEBYTECODE=1\nexec " + " ".join(command)


def _run_dual(root: Path) -> Tuple[dict, Dict[str, dict]]:
    harness = _load_harness(root)
    pairs, orphan_ps, _posix_only = harness.descubrir_pares(root)
    if orphan_ps:
        raise AssertionError("orphan PowerShell blocks: " + repr(orphan_ps))
    scenarios = _read_catalog(root)
    destinations = _read_destinations(root)
    arities = _read_arities(root)
    cases_evidence: Dict[str, dict] = {}
    implementations: Dict[str, dict] = {}
    divergences = []

    scope = harness.cargar_alcance(root)
    matrices = scope.get("cubiertos", [])
    for matrix in matrices:
        pair = pairs[matrix]
        script = destinations[matrix]
        implementations[matrix] = {
            "old_path": pair.archivo + "#@bloque:" + matrix,
            "old_sha256": _sha_bytes(pair.cuerpo_posix.encode(ENCODING)),
            "new_path": str(script.relative_to(root)),
            "new_sha256": _sha_bytes(script.read_bytes()),
        }
        matrix_data = harness.cargar_casos(root, matrix)
        catalog = harness.cargar_catalogo(root, matrix)
        for case in matrix_data.get("casos", []):
            identity = matrix + "/" + case["nombre"]
            scenario = scenarios.get(identity)
            if scenario is None:
                raise AssertionError("missing generated scenario: " + identity)
            _assert_scenario(root, matrix, case, scenario)
            fixture = None
            if case.get("fixture"):
                fixture = root / "scripts" / "paridad-casos" / matrix / "fixtures" / case["fixture"]
            inputs = case.get("entradas", {})
            input_names = list(inputs)[:arities[matrix]]
            if len(input_names) != arities[matrix]:
                raise AssertionError("not enough positional inputs for " + identity)
            old_observation = harness.ejecutar(
                pair.cuerpo_posix, "posix", fixture, inputs,
                timeout=case.get("timeout", harness.TIMEOUT_DEFECTO),
                reemplazos=case.get("reemplazos", []),
            )
            new_observation = harness.ejecutar(
                _new_body(script, input_names), "posix", fixture, inputs,
                timeout=case.get("timeout", harness.TIMEOUT_DEFECTO),
                reemplazos=case.get("reemplazos", []),
            )
            old_parsed = harness.parsear_eventos(old_observation, catalog, "posix")
            new_parsed = harness.parsear_eventos(new_observation, catalog, "posix")
            if isinstance(old_parsed, harness.Fallo):
                raise AssertionError(identity + " old event parse failed: " + old_parsed.motivo)
            if isinstance(new_parsed, harness.Fallo):
                raise AssertionError(identity + " new event parse failed: " + new_parsed.motivo)
            old_class = harness.clasificar(old_observation, *old_parsed)
            new_class = harness.clasificar(new_observation, *new_parsed)
            verdict = harness.comparar(
                old_class, old_parsed[0], old_observation,
                new_class, new_parsed[0], new_observation,
            )
            if old_class != case["clase_esperada"]:
                raise AssertionError(
                    "{0} old class {1}, expected {2}".format(
                        identity, old_class, case["clase_esperada"]))
            if not verdict.iguales:
                divergences.append({
                    "identity": identity,
                    "dimensions": verdict.dimensiones_divergentes,
                })
            cases_evidence[identity] = {
                "old": _observation_value(harness, old_observation, old_parsed, old_class),
                "new": _observation_value(harness, new_observation, new_parsed, new_class),
            }

    if set(cases_evidence) != set(scenarios):
        missing = sorted(set(scenarios) - set(cases_evidence))
        extra = sorted(set(cases_evidence) - set(scenarios))
        raise AssertionError("dual identities do not close: missing={0}, extra={1}".format(
            missing, extra))
    if divergences:
        raise AssertionError("dual divergences: " + json.dumps(divergences, ensure_ascii=False))
    return ({
        "compared": len(cases_evidence),
        "divergences": divergences,
        "implementations": implementations,
        "cases": cases_evidence,
    }, scenarios)


def _version_blocks(text: str) -> List[Tuple[int, List[str]]]:
    lines = text.splitlines()
    blocks: List[Tuple[int, List[str]]] = []
    fenced = False
    for index, line in enumerate(lines):
        if line.startswith("```"):
            fenced = not fenced
        match = None if fenced else re.fullmatch(r"(#+) v(\d+)", line)
        if match is None:
            continue
        level = len(match.group(1))
        block = [line]
        inner_fence = False
        for following in lines[index + 1:]:
            if following.startswith("```"):
                inner_fence = not inner_fence
            heading = re.match(r"^(#+) ", following) if not inner_fence else None
            if heading is not None and len(heading.group(1)) <= level:
                break
            block.append(following)
        blocks.append((int(match.group(2)), block))
    return sorted(blocks)


def _calibrate_chain(root: Path) -> dict:
    matrix_path = root / "scripts" / "paridad-casos" / "contrato-cadena" / "casos.json"
    matrix = json.loads(matrix_path.read_text(encoding=ENCODING))
    script = root / "skills" / "cross-implement" / "scripts" / "contrato-cadena.py"
    fixtures: Dict[str, dict] = {}
    checked_hashes = 0
    for case in matrix["casos"]:
        name = case["nombre"]
        contract = root / "scripts" / "paridad-casos" / "contrato-cadena" / "fixtures" / name / "contrato.md"
        text = contract.read_text(encoding=ENCODING)
        previous = ""
        versions = []
        for number, block in _version_blocks(text):
            original = "\n".join(block)
            canonical = [re.sub(r"`hash: [^`]*`", "`hash: `", line).rstrip()
                         for line in block]
            while canonical and canonical[-1] == "":
                canonical.pop()
            calculated = hashlib.sha256(
                ("\n".join(canonical) + "\n").encode(ENCODING)).hexdigest()
            declared_match = re.search(r"`hash: ([0-9a-f]*)`", original)
            prior_match = re.search(r"`hash_previo: ?([0-9a-f]*)`", original)
            declared = declared_match.group(1) if declared_match else ""
            prior = prior_match.group(1) if prior_match else ""
            versions.append({
                "version": number,
                "declared": declared,
                "calculated": calculated,
                "hash_matches": declared == calculated,
                "declared_previous": prior,
                "expected_previous": previous,
                "previous_matches": prior == previous,
            })
            checked_hashes += 1
            previous = calculated

        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [sys.executable, str(script), str(contract)], cwd=str(contract.parent),
            env=environment, capture_output=True, text=True, encoding=ENCODING, check=False,
        )
        expected_exit = 0 if all(value == "valido" for value in case["clausulas"].values()) else 1
        if result.returncode != expected_exit:
            raise AssertionError(
                "contract-chain port exit for {0}: {1}, expected {2}\n{3}".format(
                    name, result.returncode, expected_exit, result.stderr))
        reported_mismatches = {
            (int(match.group(1)), match.group(2))
            for match in re.finditer(
                r"^GUARD:cadena-hash v(\d+): hash declarado .*?, recalculado ([0-9a-f]{64})$",
                result.stderr, flags=re.MULTILINE)
        }
        expected_mismatches = {
            (version["version"], version["calculated"])
            for version in versions if not version["hash_matches"]
        }
        if reported_mismatches != expected_mismatches:
            raise AssertionError(
                "contract-chain recalculated hashes disagree for {0}: reported={1}, expected={2}".format(
                    name, sorted(reported_mismatches), sorted(expected_mismatches)))
        fixtures[name] = {
            "port_exit": result.returncode,
            "reported_hash_mismatches": sorted(reported_mismatches),
            "versions": versions,
        }
    return {
        "fixtures": fixtures,
        "fixture_count": len(fixtures),
        "checked_hashes": checked_hashes,
        "corpus_path": "scripts/paridad-casos/contrato-cadena/fixtures",
    }


def compute_evidence(root: Path = ROOT) -> dict:
    if not (root / "scripts" / "verificar-paridad-powershell.py").is_file():
        raise AssertionError("the old harness is absent from the dual tree")
    if not (root / "scripts" / "paridad-casos").is_dir():
        raise AssertionError("the original corpus is absent from the dual tree")
    dual, _scenarios = _run_dual(root)
    chain = _calibrate_chain(root)
    return {"dual": dual, "chain": chain}


def _git(root: Path, arguments: Sequence[str], text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + list(arguments), cwd=str(root), capture_output=True,
        text=text, encoding=ENCODING if text else None, check=False,
    )


def render_report(snapshot: str, evidence: dict, root: Path = ROOT) -> str:
    tree_result = _git(root, ["show", "-s", "--format=%T", snapshot])
    if tree_result.returncode != 0:
        raise AssertionError(tree_result.stderr)
    payload = {
        "snapshot": {
            "base_commit": BASE_COMMIT,
            "commit": snapshot,
            "tree": tree_result.stdout.strip(),
            "tag": TAG,
        },
        "evidence": evidence,
    }
    lines = [
        "# Reporte de migración: snapshot dual",
        "",
        "El commit `{0}` sella el árbol irrepetible donde coexisten el arnés histórico, su corpus y los 37 ports.".format(snapshot),
        "El tag anotado `{0}` lo ancla fuera de la historia de entrega. Su publicación pertenece a T22.".format(TAG),
        "",
        "- Base histórica: `{0}`".format(BASE_COMMIT),
        "- Árbol sellado: `{0}`".format(payload["snapshot"]["tree"]),
        "- Pares comparados: **{0}**".format(evidence["dual"]["compared"]),
        "- Divergencias: **{0}**".format(len(evidence["dual"]["divergences"])),
        "- Fixtures de `contrato-cadena`: **{0}**, con **{1}** hashes declarados recalculados".format(
            evidence["chain"]["fixture_count"], evidence["chain"]["checked_hashes"]),
        "",
        "## Hashes de las implementaciones",
        "",
        "| Matriz | Implementación vieja | Implementación nueva |",
        "|---|---|---|",
    ]
    for matrix, value in sorted(evidence["dual"]["implementations"].items()):
        lines.append("| `{0}` | `{1}` | `{2}` |".format(
            matrix, value["old_sha256"], value["new_sha256"]))
    lines.extend([
        "",
        "## Evidencia recalculable",
        "",
        "El bloque JSON registra los 397 IDs y las observaciones vieja y nueva por sus cinco dimensiones. Los bytes normalizados de stdout y artefactos se sellan con SHA-256; eventos, clase y código exacto quedan explícitos.",
        "",
        EVIDENCE_START,
        "```json",
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        EVIDENCE_END,
        "",
    ])
    return "\n".join(lines)


def _exigir_identidad(ref: str, root: Path) -> None:
    """Exige que `ref` alcance exactamente el blob sellado del acta.

    Sin esta comprobacion un blob con el mismo bloque JSON y prosa distinta pasaria entero,
    porque `_parsear` ignora todo lo exterior a los marcadores.
    """
    resolved = _git(root, ["rev-parse", ref + "^{}"])
    if resolved.returncode != 0:
        raise AssertionError("the acta ref is absent: " + ref)
    if resolved.stdout.strip() != REPORT_BLOB:
        raise AssertionError("the acta ref does not reach the sealed blob: " + ref)


def _parsear(texto: str) -> dict:
    """Extrae el bloque de evidencia entre marcadores. No conoce la procedencia del texto."""
    if texto.count(EVIDENCE_START) != 1 or texto.count(EVIDENCE_END) != 1:
        raise AssertionError("migration evidence markers are absent or duplicated")
    block = texto.split(EVIDENCE_START, 1)[1].split(EVIDENCE_END, 1)[0].strip()
    if not block.startswith("```json\n") or not block.endswith("```"):
        raise AssertionError("migration evidence is not a JSON fence")
    return json.loads(block[len("```json\n"):-len("```")])


def read_report(ref: str = REPORT_TAG, root: Path = ROOT) -> dict:
    """Obtiene el acta EXCLUSIVAMENTE de `ref`.

    No hay fallback a la ruta: el acta ya no vive en el arbol, y una lectura que cayera a
    `tests/reporte-migracion.md` reabriria el camino que el sellado cierra.
    """
    _exigir_identidad(ref, root)
    blob = _git(root, ["cat-file", "blob", ref], text=False)
    if blob.returncode != 0:
        raise AssertionError("the acta blob could not be read: " + ref)
    return _parsear(blob.stdout.decode(ENCODING))


def _extract_snapshot(root: Path, commit: str, destination: Path) -> None:
    archive = _git(root, ["archive", "--format=tar", commit], text=False)
    if archive.returncode != 0:
        raise AssertionError(archive.stderr.decode(ENCODING, "replace"))
    with tarfile.TarFile(fileobj=io.BytesIO(archive.stdout), mode="r") as package:
        base = destination.resolve()
        for member in package.getmembers():
            target = (destination / member.name).resolve()
            try:
                target.relative_to(base)
            except ValueError as exc:
                raise AssertionError("snapshot archive escapes its destination") from exc
        package.extractall(destination)


def verify_report(ref: str = REPORT_TAG, root: Path = ROOT) -> dict:
    recorded = read_report(ref, root)
    snapshot = recorded["snapshot"]
    tag_type = _git(root, ["cat-file", "-t", "refs/tags/" + TAG])
    if tag_type.returncode != 0 or tag_type.stdout.strip() != "tag":
        raise AssertionError("the snapshot tag is absent or is not annotated")
    resolved = _git(root, ["rev-parse", "refs/tags/" + TAG + "^{commit}"])
    if resolved.returncode != 0 or resolved.stdout.strip() != snapshot["commit"]:
        raise AssertionError("the annotated tag does not reach the reported commit")
    tree = _git(root, ["show", "-s", "--format=%T", snapshot["commit"]])
    if tree.returncode != 0 or tree.stdout.strip() != snapshot["tree"]:
        raise AssertionError("the reported snapshot tree changed")

    with tempfile.TemporaryDirectory(prefix="snapshot-dual-") as temporary:
        extracted = Path(temporary)
        _extract_snapshot(root, snapshot["commit"], extracted)
        marker_count = 0
        for markdown in (extracted / "skills").rglob("*.md"):
            marker_count += markdown.read_text(encoding=ENCODING).count("# @bloque:")
        if marker_count != EXPECTED_MARKERS:
            raise AssertionError("snapshot marker count is " + str(marker_count))
        scripts = list((extracted / "skills").glob("*/scripts/*.py"))
        guard_scripts = [script for script in scripts if not script.name.startswith("_")]
        if len(guard_scripts) != EXPECTED_GUARDS:
            raise AssertionError("snapshot guard script count is " + str(len(guard_scripts)))
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [sys.executable, "-m", "tests.migracion", "--evidence"],
            cwd=str(extracted), env=environment, capture_output=True, text=True,
            encoding=ENCODING, check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)
        recalculated = json.loads(result.stdout)
    if recalculated != recorded["evidence"]:
        raise AssertionError("recalculated dual evidence differs from the report")
    return {
        "commit": snapshot["commit"],
        "tree": snapshot["tree"],
        "tag": TAG,
        "compared": recalculated["dual"]["compared"],
        "divergences": len(recalculated["dual"]["divergences"]),
        "chain_fixtures": recalculated["chain"]["fixture_count"],
        "chain_hashes": recalculated["chain"]["checked_hashes"],
        "markers": EXPECTED_MARKERS,
    }


def _rechazar_symlink(destino: Path) -> None:
    """Rechaza un destino que sea un enlace simbolico, antes de resolverlo.

    Va antes de `Path.resolve()` a proposito: resuelto, el enlace deja de distinguirse de su
    destino y el rechazo no tendria a que aplicarse.
    """
    if destino.is_symlink():
        raise AssertionError("the report destination is a symlink: " + str(destino))


def _rechazar_bajo_tests(efectivo: Path) -> None:
    """Rechaza un destino cuyo path EFECTIVO caiga bajo `tests/`.

    La comparacion es sobre el path ya resuelto y no lexical: una comprobacion lexical se elude
    con `../tests/...`.
    """
    if efectivo.is_relative_to(ROOT / "tests"):
        raise AssertionError("the report destination falls under tests/: " + str(efectivo))


def _abrir_exclusivo(efectivo: Path):
    """Abre el path EFECTIVO en modo exclusivo. Nunca trunca lo que ya existe.

    Tiene que abrir el efectivo y no el enlace: `open(<enlace>, "x")` falla siempre con
    `FileExistsError` —incluso sobre un enlace roto— porque `O_CREAT|O_EXCL` sobre un symlink
    falla por contrato de POSIX sin mirar el destino. Abriendo el enlace, el rechazo de
    `_rechazar_symlink` no seria observable.
    """
    return open(efectivo, "x", encoding=ENCODING)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--verify-report", action="store_true")
    parser.add_argument("--snapshot")
    parser.add_argument("--output")
    parser.add_argument("--from-acta", action="store_true")
    arguments = parser.parse_args(argv)
    selected = sum((arguments.evidence, arguments.write_report, arguments.verify_report))
    if selected != 1:
        parser.error("choose exactly one operation")
    if arguments.evidence:
        print(json.dumps(compute_evidence(), ensure_ascii=False, sort_keys=True))
        return 0
    if arguments.write_report:
        if not arguments.output:
            parser.error("--write-report requires --output")
        if arguments.from_acta:
            # Re-materializa el acta desde su tag: toma la evidencia y el snapshot que el acta ya
            # trae, en vez de recalcularlos. Es la unica via que produce el acta EXACTA, porque
            # `compute_evidence` no es ejecutable en este arbol —exige el arnes historico y su
            # corpus, que ya no estan versionados— y aborta antes de calcular nada.
            acta = read_report()
            snapshot, evidencia = acta["snapshot"]["commit"], acta["evidence"]
        else:
            if not arguments.snapshot:
                parser.error("--write-report requires --snapshot or --from-acta")
            snapshot, evidencia = arguments.snapshot, compute_evidence()
        destino = Path(arguments.output)
        _rechazar_symlink(destino)
        efectivo = destino.resolve()
        _rechazar_bajo_tests(efectivo)
        with _abrir_exclusivo(efectivo) as salida:
            salida.write(render_report(snapshot, evidencia))
        print(str(efectivo))
        return 0
    print(json.dumps(verify_report(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
