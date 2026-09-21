"""Caracteriza la fabrica de orquestacion desde su implementacion base."""

from __future__ import annotations

import os
import importlib.util
import runpy
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple
from unittest import mock

from tests.fabricas import orquestacion


ENCODING = "utf-8"
ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "tests" / "inventario-bloques.md"
Case = Tuple[str, str, Callable[[Optional[object]], None]]


def _expected_files(root: Path, include_service_c: bool = False) -> Set[Path]:
    base = root / ".sdd" / "notificaciones-v2"
    files = {
        base / "manifest.yml", base / "master-spec.md", base / "integracion.md",
        base / "bitacora.md", root / "skill" / "SKILL.md", root / "env.sh",
        root / "env.ps1",
    }
    services = ("servicio-a", "servicio-b", "servicio-c") if include_service_c else (
        "servicio-a", "servicio-b")
    files.update(root / service / ".plans" / "notificaciones-v2" / "plan.md"
                 for service in services)
    return files


def _expected_directories(root: Path, files: Set[Path]) -> Set[Path]:
    directories: Set[Path] = set()
    for path in files:
        parent = path.parent
        while parent != root:
            directories.add(parent)
            parent = parent.parent
    return directories


def _assert_tree_metadata(root: Path, files: Set[Path]) -> None:
    directories = _expected_directories(root, files)
    actual = set(root.rglob("*"))
    assert actual == files | directories
    for path in files:
        assert path.is_file() and not path.is_symlink(), path
        assert stat.S_IMODE(path.stat().st_mode) == 0o644, path
    for path in directories:
        assert path.is_dir() and not path.is_symlink(), path
        assert stat.S_IMODE(path.stat().st_mode) == 0o755, path


def _with_standard_umask(action: Callable[[], None]) -> None:
    previous = os.umask(0o022)
    try:
        action()
    finally:
        os.umask(previous)


def test_v12_single_declared_site_and_arity(_context: Optional[object]) -> None:
    """El inventario declara una sola sede y la aridad invalida no muta el cwd."""
    text = INVENTORY.read_text(encoding=ENCODING)
    rows = [line for line in text.splitlines()
            if line.startswith("| `fixtures-orquestacion` |")]
    assert len(rows) == 2  # Inventory classification and test-infrastructure signature.
    assert text.count("`tests/fabricas/orquestacion.py`") == 2
    classification = next(line for line in rows if "infraestructura de tests" in line)
    assert "| infraestructura de tests | `tests/fabricas/orquestacion.py` |" in classification
    sites = tuple(ROOT.rglob("orquestacion.py"))
    assert sites == (ROOT / "tests" / "fabricas" / "orquestacion.py",)

    with tempfile.TemporaryDirectory(prefix="fixtures-v12-arity-") as temporary:
        cwd = Path(temporary)
        sentinel = cwd / "sentinel.txt"
        sentinel.write_text("intact\n", encoding=ENCODING)
        result = subprocess.run(
            [sys.executable, str(sites[0])], cwd=str(cwd), capture_output=True,
            text=True, encoding=ENCODING, check=False,
        )
        assert result.returncode == 2
        assert result.stdout == ""
        assert result.stderr == "USO:fixtures-orquestacion scenario\n"
        assert tuple(cwd.iterdir()) == (sentinel,)


def test_v12_direct_publication(_context: Optional[object]) -> None:
    """Las salidas base son nodos regulares con permisos base y publicacion directa."""
    with tempfile.TemporaryDirectory(prefix="fixtures-v12-direct-") as temporary:
        root = Path(temporary)
        direct: List[Path] = []
        original = orquestacion._publish_direct

        def record(path: Path, body: str) -> None:
            direct.append(path)
            original(path, body)

        def action() -> None:
            with mock.patch.object(orquestacion, "_publish_direct", side_effect=record), \
                    mock.patch.object(orquestacion.os, "replace", wraps=os.replace) as replace:
                outputs = orquestacion.materialize("MODELO_VALIDO", root)
                expected = _expected_files(root)
                assert set(outputs) == expected
                assert set(direct) == expected
                assert replace.call_count == 0
                _assert_tree_metadata(root, expected)

        _with_standard_umask(action)


def test_v12_rename_publication(_context: Optional[object]) -> None:
    """Solo la edicion equivalente a _fx_sed reemplaza la bitacora por rename."""
    with tempfile.TemporaryDirectory(prefix="fixtures-v12-rename-") as temporary:
        root = Path(temporary)
        direct: List[Path] = []
        original = orquestacion._publish_direct

        def record(path: Path, body: str) -> None:
            direct.append(path)
            original(path, body)

        def action() -> None:
            with mock.patch.object(orquestacion, "_publish_direct", side_effect=record), \
                    mock.patch.object(orquestacion.os, "replace", wraps=os.replace) as replace:
                outputs = orquestacion.materialize("BITACORA_RESULTADO_INVALIDO", root)
                expected = _expected_files(root)
                log = root / ".sdd" / "notificaciones-v2" / "bitacora.md"
                assert set(outputs) == expected
                assert set(direct) == expected
                assert replace.call_count == 1
                source, target = replace.call_args.args
                assert Path(source) == log.with_name("bitacora.md.fxtmp")
                assert Path(target) == log
                assert not Path(source).exists()
                assert "resultado: ok" in log.read_text(encoding=ENCODING)
                _assert_tree_metadata(root, expected)

        _with_standard_umask(action)


def test_v12_consumers_preserve_precedence(_context: Optional[object]) -> None:
    """Las cuatro guardas consumen fixtures rojos con un solo diagnostico conductual."""
    scripts = ROOT / "skills" / "sdd-orchestrator" / "scripts"
    cases = (
        ("AC_MAL_UBICADO_LOCAL_EN_TAREA", "orchestration-model.py",
         "GUARD:model repo-local-en-covers_ac-de-tarea"),
        ("SOLO_GATES", "orchestration-contract.py",
         "GUARD:contract fila-closeout-ausente"),
        ("GATE_ABIERTO_DESPACHO_EXITOSO", "orchestration-state.py",
         "GUARD:state despacho-exitoso-con-gate-abierto"),
        ("FASE3_SIN_REVALIDAR", "gate-fase-3.py",
         "GUARD:gate-fase-3 no-revalida-version-vigente"),
    )
    for scenario, script, diagnostic in cases:
        with tempfile.TemporaryDirectory(prefix="fixtures-v12-consumer-") as temporary:
            root = Path(temporary)
            orquestacion.materialize(scenario, root)
            base = root / ".sdd" / "notificaciones-v2"
            if script == "orchestration-model.py":
                plans = [root / service / ".plans" / "notificaciones-v2" / "plan.md"
                         for service in ("servicio-a", "servicio-b")]
                arguments = [base / "manifest.yml", base / "master-spec.md", *plans]
            elif script == "orchestration-contract.py":
                arguments = [base / "manifest.yml", base / "integracion.md"]
            elif script == "orchestration-state.py":
                plans = [root / service / ".plans" / "notificaciones-v2" / "plan.md"
                         for service in ("servicio-a", "servicio-b")]
                arguments = [base / "manifest.yml", base / "master-spec.md",
                             base / "integracion.md", base / "bitacora.md", "final", *plans]
            else:
                arguments = [root / "skill" / "SKILL.md"]
            result = subprocess.run(
                [sys.executable, str(scripts / script)] + [str(item) for item in arguments],
                cwd=str(root), capture_output=True, text=True, encoding=ENCODING, check=False,
            )
            guard_lines = [line for line in result.stderr.splitlines()
                           if line.startswith("GUARD:")]
            assert result.returncode == 1, result.stderr
            assert guard_lines == [diagnostic]


def test_delivery_profile_parser_boundary(_context: Optional[object]) -> None:
    """One structural parser owns key order and root-key multiplicity for both guards."""
    scripts = ROOT / "skills" / "sdd-orchestrator" / "scripts"
    parser = runpy.run_path(str(scripts / "_yaml.py"))["parsear_perfil_manifest"]
    with tempfile.TemporaryDirectory(prefix="delivery-profile-parser-boundary-") as directory:
        root = Path(directory)
        orquestacion.materialize("PROFILE_REORDERED_ITEMS", root)
        manifest = (root / ".sdd/notificaciones-v2/manifest.yml").read_text(encoding=ENCODING)
    parsed = parser(manifest)
    assert parsed["assessment"][0]["values"]["scope"] == "repo:servicio-c"
    assert parsed["repos"][0]["path"] == "servicio-c" and parsed["repos_sections"] == 1
    duplicated_path = parser(manifest.replace("    path: servicio-c\n",
                                               "    path: servicio-c\n    path: servicio-z\n", 1))
    assert duplicated_path["repos"][0]["duplicates"] == {"path"}
    _head, _repos = manifest.split("repos:\n", 1)
    assert parser(_head + "repos: []\n" + _repos)["repos_invalid"]
    assert not parser("repos:\n  - path: a\n      branch: feature/x\n")["repos_invalid"]
    for section, field, collection in (("repos", "path: servicio-a", "repos"),
                                       ("delivery_assessment", "scope: global", "assessment")):
        for indent in ("", "   ", "    ", "\t"):
            parsed = parser(f"{section}:\n{indent}- {field}\n")
            assert parsed[collection] == [] and parsed[f"{collection}_invalid"], (section, repr(indent), parsed)
    for second in ("repos:\n", "repos: []\n", "repos : null\n"):
        assert parser(manifest + second)["repos_sections"] == 2
    for consumer in ("orchestration-model.py", "orchestration-state.py"):
        source = (scripts / consumer).read_text(encoding=ENCODING)
        assert "def parsear_perfil_manifest" not in source
        assert "parsear_perfil_manifest" in source and "validar_assessment" in source
        assert "def delivery_modulo" not in source and "ASSESSMENT_FIELDS" not in source
    assert 'repo_campo == "covers_ac" and nested' not in (scripts / "orchestration-model.py").read_text(
        encoding=ENCODING)
    print("DELIVERY_PROFILE_PARSER_BOUNDARY_OK")


def _state_module():
    script = ROOT / "skills/sdd-orchestrator/scripts/orchestration-state.py"
    spec = importlib.util.spec_from_file_location("orchestration_state_contract_test", script)
    if spec is None or spec.loader is None:
        raise AssertionError("no se pudo cargar orchestration-state")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(script.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def _local_contract(versions=(1,), baseline_types=None) -> str:
    types = baseline_types or {}
    blocks = []
    for version in versions:
        contract_hash = chr(96 + min(version, 6)) * 64
        blocks.append("\n".join((
            f"## v{version}",
            "| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |",
            "|---|---|---|---|---|---|",
            "| V1 | C1 — integración | test | predicado | verde | RED |",
            ("- pertinencia: `id: V1` · `autoridad: test local` · `relación: no-aplica` · "
             f"`baseline_tipo: {types.get(version, 'otro')}` · `baseline_fundamento: fixture`"),
            f"`hash_previo: ` · `hash: {contract_hash}`",
        )))
    return "\n\n".join(blocks) + "\n"


def _contract_event(index: int, step: str, version: int, contract_hash: str,
                    **extra: str) -> Dict[str, str]:
    event = {
        "id": str(index), "paso": step,
        "actor": "usuario" if step == "aprobar-reparación" else "orquestador",
        "objeto": f"contrato-integracion:v{version}", "resultado": "consumado",
        "timestamp": f"2026-01-01T00:{index:02d}:00Z", "hash": contract_hash,
    }
    if step == "adoptar-estado-contrato":
        event["modo"] = "materializacion"
    event.update(extra)
    return event


def _classification_event(index: int, *, task: str = "C1", check_id: str = "V1",
                          participants: Optional[Dict[str, str]] = None,
                          classification: str = "VERIFICATION_DEFECT", version: int = 2,
                          ordinal: int = 1, **extra: str) -> Dict[str, str]:
    repos = participants or {"servicio-a": "aaa1111", "servicio-b": "bbb2222"}
    sha = ", ".join(f"{repo}={repos[repo]}" for repo in sorted(repos, key=str.encode))
    event = {
        "id": str(index), "paso": "clasificar-falla", "actor": "orquestador",
        "objeto": task, "resultado": "consumado",
        "timestamp": f"2026-01-01T00:{index:02d}:00Z", "checkId": check_id,
        "clase": classification, "consumedRound": "no", "evidencia": "salida",
        "sha": sha,
        "delta": "repos-sha256:" + __import__("hashlib").sha256(sha.encode()).hexdigest(),
        "fix_round": "0", "contract_version": str(version),
        "verification_defect_ordinal": str(ordinal),
    }
    event.update(extra)
    return event


def _local_call(module, *, phase="final", versions=(1,), frozen=True, events=None,
                repairs=None, types=None, tasks=None, frozen_version=None):
    contract = _local_contract(versions, types)
    current = max(versions)
    state_version = current if frozen_version is None else frozen_version
    contract_hash = chr(96 + min(state_version, 6)) * 64
    state = {
        "integration_contract_frozen_version": [str(state_version)] if frozen else [],
        "integration_contract_frozen_hash": [contract_hash] if frozen else [],
    }
    if events is None:
        events = [_contract_event(1, "adoptar-estado-contrato", current, contract_hash)]
    if tasks is None:
        tasks = [{"id": "C1", "participants": ["servicio-a", "servicio-b"]}]
    return module.validar_estado_contrato(
        phase, state, contract, repairs or [], events, tasks)


def _ownership_environment_budget() -> None:
    script = ROOT / "skills/cross-implement/scripts/ownership-presupuesto.py"
    line = ("- `paso: clasificar-falla` · `checkId: V1` · "
            "`clase: ENVIRONMENT_FAILURE`\n")
    with tempfile.TemporaryDirectory(prefix="orchestration-environment-budget-") as temporary:
        root = Path(temporary)
        approvals = root / "approvals.md"
        approvals.write_text("", encoding=ENCODING)
        for count, expected in ((2, 0), (3, 1)):
            log = root / f"log-{count}.md"
            log.write_text(line * count, encoding=ENCODING)
            result = subprocess.run(
                [sys.executable, str(script), str(log), str(approvals), "2"],
                cwd=root, capture_output=True, text=True, encoding=ENCODING, check=False,
            )
            assert result.returncode == expected, (count, result.stderr)
            if expected == 0:
                assert result.stderr == ""
            else:
                assert "V1 · ENVIRONMENT_FAILURE · 3 > 2" in result.stderr


def _factory_state_code(scenario: str) -> str:
    script = ROOT / "skills/sdd-orchestrator/scripts/orchestration-state.py"
    with tempfile.TemporaryDirectory(prefix="orchestration-precedence-") as temporary:
        root = Path(temporary)
        orquestacion.materialize(scenario, root)
        base = root / ".sdd" / "notificaciones-v2"
        plans = [root / service / ".plans" / "notificaciones-v2" / "plan.md"
                 for service in ("servicio-a", "servicio-b")]
        result = subprocess.run(
            [sys.executable, str(script), str(base / "manifest.yml"),
             str(base / "master-spec.md"), str(base / "integracion.md"),
             str(base / "bitacora.md"), "final", *map(str, plans)],
            cwd=root, capture_output=True, text=True, encoding=ENCODING, check=False,
        )
        guards = [line.removeprefix("GUARD:state ") for line in result.stderr.splitlines()
                  if line.startswith("GUARD:state ")]
        assert result.returncode == 1 and len(guards) == 1, (scenario, result.stderr)
        return guards[0]


TRANSICIONES_CONTRATO = (
    "adopcion-seguida-de-reparacion", "correccion-emparejada", "proyector-mecanico",
    "verificacion-aislada", "candidate-previo", "final-posterior", "legado-contiguo",
    "legado-con-salto", "tareas-comparten-fila", "aprobacion-entre-anclas",
    "aprobacion-anterior-al-ancla", "clasificacion-abandonada",
    "proyector-con-clasificacion-desfasada", "implementation-defect",
    "verification-defect", "environment-failure", "design-gap",
    "cobertura-antes-del-primer-ancla", "cobertura-despues-del-primer-ancla",
    "claves-sin-ancla", "adopcion-retroactiva-unica", "adopcion-retroactiva-duplicada",
    "clasificacion-sin-cambio-de-estado", "evento-auxiliar-incompleto",
    "agotamiento-de-entorno",
)


PRECEDENCIAS_CONTRATO = (
    "campos-base", "resultado-base", "identidad-base", "clasificacion-no-consumada",
    "tarea-invalida", "repos-ausentes", "repos-repetidos", "repos-distintos",
    "orden-de-repos", "digest-de-repos", "verificacion-no-admitida", "hash-de-adopcion",
    "modo-de-adopcion", "adopcion-retroactiva-duplicada", "estado-sin-ancla",
)


def test_orchestration_contract_transitions(_context: Optional[object]) -> None:
    """La tabla local ejecuta sus veinticinco transiciones cerradas."""
    module = _state_module()
    a, b = "a" * 64, "b" * 64
    adopt1 = _contract_event(1, "adoptar-estado-contrato", 1, a)
    approve2 = _contract_event(
        2, "aprobar-reparación", 2, b, token="2:V1:esperado-corregido:a1",
        checkId="V1", contract_version="2", verification_defect_ordinal="1")
    adopt2 = _contract_event(3, "adoptar-estado-contrato", 2, b)
    repair = [(2, {"id": "V1", "operación": "esperado-corregido",
                   "token": "2:V1:esperado-corregido:a1"})]
    paired_approvals = [
        _contract_event(2, "aprobar-reparación", 2, b,
                        token="2:V1:pertinencia-corregida:a1"),
        _contract_event(3, "aprobar-reparación", 2, b,
                        token="2:V1:verificacion-corregida:a1",
                        checkId="V1", contract_version="2",
                        verification_defect_ordinal="1"),
    ]
    paired_repairs = [
        (2, {"id": "V1", "operación": "pertinencia-corregida",
             "token": "2:V1:pertinencia-corregida:a1"}),
        (2, {"id": "V1", "operación": "verificacion-corregida",
             "token": "2:V1:verificacion-corregida:a1", "campos": "evidencia"}),
    ]
    mechanical_approval = _contract_event(
        3, "aprobar-reparación", 2, b, token="2:V1:verificacion-corregida:a1",
        checkId="V1", contract_version="2", verification_defect_ordinal="1")
    mechanical_repair = [(2, {
        "id": "V1", "operación": "verificacion-corregida",
        "token": "2:V1:verificacion-corregida:a1", "campos": "comando",
    })]
    classification_v2 = _classification_event(2)
    classification_v3 = _classification_event(3, version=3)
    approve3 = _contract_event(
        4, "aprobar-reparación", 3, "c" * 64,
        token="3:V1:verificacion-corregida:a1", checkId="V1",
        contract_version="3", verification_defect_ordinal="1")
    repair3 = [(3, {
        "id": "V1", "operación": "verificacion-corregida",
        "token": "3:V1:verificacion-corregida:a1", "campos": "comando",
    })]
    shared_tasks = [
        {"id": "C1", "participants": ["servicio-a"]},
        {"id": "C2", "participants": ["servicio-b"]},
    ]
    _ownership_environment_budget()
    checks = [
        _local_call(module, phase="candidate", versions=(1, 2), frozen_version=1,
                    events=[adopt1, approve2], repairs=repair),
        _local_call(module, versions=(1, 2), types={2: "fallos-ejecucion"},
                    events=[adopt1, *paired_approvals,
                            _contract_event(4, "adoptar-estado-contrato", 2, b)],
                    repairs=paired_repairs),
        _local_call(module, versions=(1, 2), types={1: "fallos-previos", 2: "fallos-previos"},
                    events=[adopt1, classification_v2, mechanical_approval,
                            _contract_event(4, "adoptar-estado-contrato", 2, b)],
                    repairs=mechanical_repair),
        _local_call(module, versions=(1, 2), types={1: "fallos-previos", 2: "fallos-previos"},
                    events=[adopt1, mechanical_approval,
                            _contract_event(4, "adoptar-estado-contrato", 2, b)],
                    repairs=mechanical_repair),
        _local_call(module, phase="candidate", versions=(1, 2), events=[adopt1], repairs=repair,
                    frozen_version=1),
        _local_call(module, versions=(1, 2), events=[adopt1, approve2, adopt2], repairs=repair),
        _local_call(module, phase="candidate", versions=(1, 2), frozen=False,
                    events=[approve2], repairs=repair),
        _local_call(module, versions=(1, 3)),
        _local_call(module, events=[adopt1,
                                    _classification_event(2, task="C1", participants={"servicio-a": "aaa1111"}),
                                    _classification_event(3, task="C2", participants={"servicio-b": "bbb2222"})],
                    tasks=shared_tasks),
        _local_call(module, versions=(1, 2), events=[adopt1, approve2, adopt2], repairs=repair),
        _local_call(module, versions=(1, 2), events=[approve2, adopt1, adopt2], repairs=repair),
        _local_call(module, versions=(1, 2, 3), types={2: "fallos-previos", 3: "fallos-previos"},
                    events=[adopt1, classification_v2, classification_v3, approve3,
                            _contract_event(5, "adoptar-estado-contrato", 3, "c" * 64)],
                    repairs=repair3),
        _local_call(module, phase="candidate", versions=(1, 2), frozen_version=1,
                    types={1: "fallos-previos", 2: "fallos-previos"},
                    events=[adopt1, _classification_event(2, version=1), mechanical_approval],
                    repairs=mechanical_repair),
        _local_call(module, events=[adopt1, _classification_event(
            2, classification="IMPLEMENTATION_DEFECT", version=1)]),
        _local_call(module, events=[adopt1, _classification_event(
            2, classification="VERIFICATION_DEFECT", version=1)]),
        _local_call(module, events=[adopt1, _classification_event(
            2, classification="ENVIRONMENT_FAILURE", version=1)]),
        _local_call(module, events=[adopt1, _classification_event(
            2, classification="DESIGN_GAP", version=1)]),
        _local_call(module, versions=(1, 2), events=[approve2, adopt1, adopt2], repairs=[(
            2, {"id": "V1", "operación": "cobertura-agregada",
                "token": "2:V1:esperado-corregido:a1"})]),
        _local_call(module, versions=(1, 2), events=[adopt1,
                    _contract_event(2, "aprobar-reparación", 2, b,
                                    token="2:V2:cobertura-agregada:a1"), adopt2],
                    repairs=[(2, {"id": "V2", "operación": "cobertura-agregada",
                                  "token": "2:V2:cobertura-agregada:a1"})]),
        _local_call(module, events=[]),
        _local_call(module, events=[_contract_event(
            1, "adoptar-estado-contrato", 1, a, modo="adopcion-retroactiva")]),
        _local_call(module, events=[_contract_event(
            1, "adoptar-estado-contrato", 1, a, modo="adopcion-retroactiva"),
            _contract_event(2, "adoptar-estado-contrato", 1, a, modo="adopcion-retroactiva")]),
        _local_call(module, events=[adopt1, _classification_event(
            2, classification="IMPLEMENTATION_DEFECT", version=1)]),
        _local_call(module, events=[{"paso": "clasificar-falla", "actor": "orquestador",
                                    "resultado": "consumado"}]),
        None,
    ]
    expected_codes = {
        "legado-con-salto": "versiones-no-contiguas",
        "aprobacion-anterior-al-ancla": "aprobacion-anterior-al-ancla",
        "cobertura-despues-del-primer-ancla": "cobertura-agregada-post-ancla",
        "claves-sin-ancla": "estado-contrato-sin-ancla",
        "adopcion-retroactiva-duplicada": "adopcion-retroactiva-duplicada",
        "evento-auxiliar-incompleto": "clasificacion-incompleta",
        "verificacion-aislada": "verificacion-no-admitida",
        "proyector-con-clasificacion-desfasada": "verificacion-no-admitida",
    }
    assert len(TRANSICIONES_CONTRATO) == len(checks) == 25
    for identity, result in zip(TRANSICIONES_CONTRATO, checks):
        expected = expected_codes.get(identity)
        assert (result[0] if result else None) == expected, (identity, result)
    print("orchestration-state transiciones: 25/25 casos ok")


def test_orchestration_contract_precedence(_context: Optional[object]) -> None:
    """Quince precedencias mantienen un único diagnóstico local dominante."""
    module = _state_module()
    a, b = "a" * 64, "b" * 64
    valid_sha = "servicio-a=aaa1111, servicio-b=bbb2222"
    valid_delta = "repos-sha256:" + __import__("hashlib").sha256(valid_sha.encode()).hexdigest()

    def classification(**changes: str) -> Dict[str, str]:
        event = _classification_event(2)
        event.update(changes)
        return event

    adopt = _contract_event(1, "adoptar-estado-contrato", 1, a)
    bad_verification = [(2, {"id": "V1", "operación": "verificacion-corregida",
                             "token": "2:V1:verificacion-corregida:a1", "campos": "evidencia"})]
    results = [
        _factory_state_code("BITACORA_EVENTO_SIN_ACTOR"),
        _factory_state_code("BITACORA_RESULTADO_INVALIDO"),
        _factory_state_code("BITACORA_ORDEN_AMBIGUO"),
        _local_call(module, events=[adopt, classification(resultado="rechazado")]),
        _local_call(module, events=[adopt, classification(objeto="C9")]),
        _local_call(module, events=[adopt, classification(sha="servicio-a=aaa1111")]),
        _local_call(module, events=[adopt, classification(
            sha="servicio-a=aaa1111, servicio-a=aaa1111, servicio-b=bbb2222")]),
        _local_call(module, events=[adopt, classification(
            sha="servicio-a=aaa1111, servicio-z=zzz1111")]),
        _local_call(module, events=[adopt, classification(
            sha="servicio-b=bbb2222, servicio-a=aaa1111")]),
        _local_call(module, events=[adopt, classification(delta="repos-sha256:" + "0" * 64)]),
        _local_call(module, phase="candidate", versions=(1, 2), events=[adopt],
                    repairs=bad_verification, frozen_version=1),
        _local_call(module, events=[_contract_event(1, "adoptar-estado-contrato", 1, b)]),
        _local_call(module, events=[_contract_event(
            1, "adoptar-estado-contrato", 1, a, modo="otro")]),
        _local_call(module, events=[_contract_event(
            1, "adoptar-estado-contrato", 1, a, modo="adopcion-retroactiva"),
            _contract_event(2, "adoptar-estado-contrato", 1, a, modo="adopcion-retroactiva")]),
        _local_call(module, events=[]),
    ]
    expected = (
        "evento-sin-actor", "resultado-fuera-de-enum", "orden-no-determinable",
        "clasificacion-no-consumada", "clasificacion-tarea-invalida",
        "clasificacion-sha-repos", "clasificacion-sha-repos",
        "clasificacion-sha-repos", "clasificacion-sha-orden",
        "clasificacion-delta-invalido", "verificacion-no-admitida",
        "evento-contrato-hash-diverge", "evento-contrato-invalido",
        "adopcion-retroactiva-duplicada", "estado-contrato-sin-ancla",
    )
    assert len(PRECEDENCIAS_CONTRATO) == len(results) == len(expected) == 15
    for identity, result, code in zip(PRECEDENCIAS_CONTRATO, results, expected):
        observed = result[0] if isinstance(result, tuple) else result
        assert observed == code, (identity, result)
    print("orchestration-state precedencias: 15/15 casos ok")


CASOS: List[Case] = [
    ("delivery-profile:parser-boundary", "delivery-profile",
     test_delivery_profile_parser_boundary),
    ("fixtures-v12:sede-aridad", "fixtures-orquestacion-v12",
     test_v12_single_declared_site_and_arity),
    ("fixtures-v12:publicacion-directa", "fixtures-orquestacion-v12",
     test_v12_direct_publication),
    ("fixtures-v12:publicacion-rename", "fixtures-orquestacion-v12",
     test_v12_rename_publication),
    ("fixtures-v12:precedencias", "fixtures-orquestacion-v12",
     test_v12_consumers_preserve_precedence),
    ("orchestration-state:transiciones", "orchestration-state-v1",
     test_orchestration_contract_transitions),
    ("orchestration-state:precedencias", "orchestration-state-v1",
     test_orchestration_contract_precedence),
]
