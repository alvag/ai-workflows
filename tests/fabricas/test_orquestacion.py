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


def test_delivery_profile_model(_context: Optional[object]) -> None:
    """The model enforces all-or-nothing fold and cross-artifact profile carriers."""
    script = ROOT / "skills" / "sdd-orchestrator" / "scripts" / "orchestration-model.py"

    def execute(root: Path, services=("servicio-a", "servicio-b")) -> subprocess.CompletedProcess:
        base = root / ".sdd" / "notificaciones-v2"
        plans = [root / service / ".plans" / "notificaciones-v2" / "plan.md"
                 for service in services]
        return subprocess.run(
            [sys.executable, str(script), str(base / "manifest.yml"),
             str(base / "master-spec.md"), *map(str, plans)],
            cwd=root, capture_output=True, text=True, check=False,
        )

    def run(scenario: str, services=("servicio-a", "servicio-b")) -> subprocess.CompletedProcess:
        temporary = tempfile.TemporaryDirectory(prefix="delivery profile model ")
        cleanups.append(temporary)
        root = Path(temporary.name)
        orquestacion.materialize(scenario, root)
        return execute(root, services)

    cleanups: List[tempfile.TemporaryDirectory] = []
    try:
        for scenario in ("MODELO_VALIDO", "PROFILE_LOW", "PROFILE_INTEGRATION_COMPLEX",
                         "PROFILE_HIGH_STANDARD", "PROFILE_UNKNOWN_STANDARD",
                         "PROFILE_SPACED_MANIFEST"):
            result = run(scenario)
            assert result.returncode == 0, (scenario, result.stderr)
        expected = {
            "PROFILE_EXPEDITED_HIGH": "GUARD:model expedited-inelegible",
            "PROFILE_PARTIAL": "GUARD:model par-parcial",
            "PROFILE_ENUM_UNKNOWN": "GUARD:model perfil-desconocido",
            "PROFILE_MIXED_PLAN": "GUARD:model carrier-mixto",
            "PROFILE_PAIR_DIVERGES": "GUARD:model perfil-manifest-plan-diverge",
            "PROFILE_COMPLEXITY_DIVERGES":
                "GUARD:model complexity-assessment-manifest-plan-diverge",
            "PROFILE_REPO_RISK_DIVERGES": "GUARD:model risk-assessment-manifest-diverge",
            "PROFILE_DUPLICATE_REPO": "GUARD:model repo-duplicado",
            "PROFILE_REPO_PATH_DUPLICATE": "GUARD:model clave-duplicada",
            "PROFILE_DUPLICATE_REPOS_SECTION": "GUARD:model clave-duplicada",
            "PROFILE_DUPLICATE_REPOS_INLINE": "GUARD:model clave-duplicada",
            "PROFILE_DUPLICATE_SPACED": "GUARD:model clave-duplicada",
            "PROFILE_REPO_RISK_SPACED_DUPLICATE": "GUARD:model carrier-mixto",
            "PROFILE_FOLD_DIVERGES": "GUARD:model risk-fold-diverge",
            "PROFILE_ASSESSMENT_EXTRA_FIELD": "GUARD:model assessment-forma-invalida",
            "PROFILE_ASSESSMENT_SCALAR_EVIDENCE": "GUARD:model assessment-forma-invalida",
            "PROFILE_ASSESSMENT_BAD_PROVENANCE":
                "GUARD:model assessment-provenance-invalida",
        }
        for scenario, diagnostic in expected.items():
            result = run(scenario)
            assert result.returncode == 1, (scenario, result.stderr)
            assert [line for line in result.stderr.splitlines() if line.startswith("GUARD:")] == [diagnostic]
            if scenario == "PROFILE_MIXED_PLAN":
                assert "  plan: " in result.stderr and "  manifest: " not in result.stderr
            if scenario == "PROFILE_PAIR_DIVERGES":
                assert "  el par del plan servicio-b difiere del manifest\n" in result.stderr
        reordered = run("PROFILE_REORDERED_ITEMS", ("servicio-a", "servicio-b", "servicio-c"))
        assert reordered.returncode == 0, reordered.stderr
        missing_reordered = run("PROFILE_REORDERED_ITEMS")
        assert missing_reordered.returncode == 1 and "GUARD:model repo-plans-divergen" in missing_reordered.stderr
        duplicated = run("PROFILE_LOW", ("servicio-a", "servicio-b", "servicio-b"))
        assert duplicated.returncode == 1 and [line for line in duplicated.stderr.splitlines() if line.startswith("GUARD:")] == ["GUARD:model plan-repo-duplicado"]

        enum_diagnostics = {
            "urgency": ("normal", "assessment-urgency-invalida"),
            "complexity": ("complex", "complejidad-desconocida"),
            "risk": ("low", "riesgo-desconocido"),
            "confidence": ("high", "assessment-confidence-invalida"),
        }
        for field, (value, diagnostic) in enum_diagnostics.items():
            with tempfile.TemporaryDirectory(
                    prefix=f"delivery-profile-model-{field}-list-") as directory:
                root = Path(directory)
                orquestacion.materialize("PROFILE_LOW", root)
                base = root / ".sdd" / "notificaciones-v2"
                manifest = base / "manifest.yml"
                text = manifest.read_text(encoding=ENCODING)
                needle = f"    {field}: {value}\n"
                assert needle in text
                manifest.write_text(
                    text.replace(needle, f"    {field}: [{value}]\n", 1),
                    encoding=ENCODING,
                )
                result = execute(root)
                assert result.returncode == 1, (field, result.stderr)
                assert [line for line in result.stderr.splitlines()
                        if line.startswith("GUARD:")] == [f"GUARD:model {diagnostic}"]
                assert "Traceback" not in result.stderr

        with tempfile.TemporaryDirectory(prefix="delivery-profile-duplicate-assessment-") as directory:
            root = Path(directory)
            orquestacion.materialize("PROFILE_LOW", root)
            base = root / ".sdd" / "notificaciones-v2"
            manifest = base / "manifest.yml"
            text = manifest.read_text(encoding=ENCODING)
            needle = "  - scope: repo:servicio-a\n"
            assert text.count(needle) == 1
            manifest.write_text(
                text.replace(needle, "delivery_assessment:\n" + needle),
                encoding=ENCODING,
            )
            result = execute(root)
            assert result.returncode == 1, result.stderr
            assert [line for line in result.stderr.splitlines()
                    if line.startswith("GUARD:")] == ["GUARD:model clave-duplicada"]

        with tempfile.TemporaryDirectory(prefix="delivery-profile-inline-duplicate-assessment-") as directory:
            root = Path(directory)
            orquestacion.materialize("PROFILE_LOW", root)
            base = root / ".sdd" / "notificaciones-v2"
            manifest = base / "manifest.yml"
            text = manifest.read_text(encoding=ENCODING)
            assert text.count("\nrepos:\n") == 1
            manifest.write_text(
                text.replace("\nrepos:\n", "\ndelivery_assessment: []\nrepos:\n", 1),
                encoding=ENCODING,
            )
            result = execute(root)
            assert result.returncode == 1, result.stderr
            assert [line for line in result.stderr.splitlines()
                    if line.startswith("GUARD:")] == ["GUARD:model clave-duplicada"]

        with tempfile.TemporaryDirectory(prefix="delivery-profile-inline-assessment-") as directory:
            root = Path(directory)
            orquestacion.materialize("PROFILE_LOW", root)
            base = root / ".sdd" / "notificaciones-v2"
            manifest = base / "manifest.yml"
            text = manifest.read_text(encoding=ENCODING)
            before, remainder = text.split("delivery_assessment:\n", 1)
            _assessment, after = remainder.split("repos:\n", 1)
            manifest.write_text(
                before + "delivery_assessment: []\nrepos:\n" + after,
                encoding=ENCODING,
            )
            result = execute(root)
            assert result.returncode == 1, result.stderr
            assert [line for line in result.stderr.splitlines()
                    if line.startswith("GUARD:")] == [
                        "GUARD:model assessment-forma-invalida"]

        with tempfile.TemporaryDirectory(prefix="delivery-profile-hyphen-extra-field-") as directory:
            root = Path(directory)
            orquestacion.materialize("PROFILE_LOW", root)
            base = root / ".sdd" / "notificaciones-v2"
            manifest = base / "manifest.yml"
            text = manifest.read_text(encoding=ENCODING)
            needle = "    confidence: high\n"
            assert needle in text
            manifest.write_text(
                text.replace(needle, needle + "    extra-field: nope\n", 1),
                encoding=ENCODING,
            )
            result = execute(root)
            assert result.returncode == 1, result.stderr
            assert [line for line in result.stderr.splitlines()
                    if line.startswith("GUARD:")] == [
                        "GUARD:model assessment-forma-invalida"]

        with tempfile.TemporaryDirectory(prefix="delivery profile regressions ") as directory:
            root = Path(directory)
            orquestacion.materialize("PROFILE_LOW", root)
            base = root / ".sdd/notificaciones-v2"
            paths = [base / "manifest.yml", *(root / repo / ".plans/notificaciones-v2/plan.md"
                                               for repo in ("servicio-a", "servicio-b"))]
            for path in paths:
                text = path.read_text(encoding=ENCODING)
                path.write_text(text.replace("delivery_profile: expedited", 'delivery_profile: "expedited"')
                                .replace("risk: low", "risk: 'low'"), encoding=ENCODING)
            quoted = execute(root)
            assert quoted.returncode == 0, quoted.stderr

            orquestacion.materialize("MODELO_VALIDO", root)
            legacy = root / "servicio-a/.plans/notificaciones-v2/plan.md"
            legacy.write_text(legacy.read_text(encoding=ENCODING).replace("---\n", "--\n", 1),
                              encoding=ENCODING)
            assert execute(root).returncode == 0

            orquestacion.materialize("MODELO_VALIDO", root)
            illegible = root / "servicio-a/.plans/notificaciones-v2/plan.md"
            illegible.write_bytes(illegible.read_bytes() + b"\xff")
            unreadable = execute(root)
            assert (unreadable.returncode == 1 and "GUARD:model archivo-ilegible" in unreadable.stderr
                    and f"  plan: {illegible}\n" in unreadable.stderr)

            for replacement in ("repos: []\n", "repos:\n- path: servicio-a\n",
                                "repos:\n    - path: servicio-a\n",
                                "repos:\n  - path: servicio-a\n    covers_ac:\n      - AC-1\n"):
                orquestacion.materialize("PROFILE_LOW", root)
                manifest = base / "manifest.yml"
                text = manifest.read_text(encoding=ENCODING)
                _prefix, suffix = text.split("repos:\n", 1)
                manifest.write_text(_prefix + replacement + suffix.split("  - path: servicio-a\n", 1)[1],
                                    encoding=ENCODING)
                invalid = execute(root)
                assert invalid.returncode == 1 and invalid.stderr.startswith(
                    "GUARD:model repos-forma-invalida\n  repos y sus filas deben usar")

            orquestacion.materialize("PROFILE_LOW", root)
            manifest = base / "manifest.yml"
            manifest.write_text(manifest.read_text(encoding=ENCODING).replace(
                "  - scope: global\n", "   - scope: global\n", 1), encoding=ENCODING)
            malformed_assessment = execute(root)
            assert (malformed_assessment.returncode == 1
                    and "GUARD:model assessment-forma-invalida" in malformed_assessment.stderr)

            orquestacion.materialize("PROFILE_LOW", root)
            manifest = base / "manifest.yml"
            text = manifest.read_text(encoding=ENCODING).replace(
                "delivery_profile: expedited\n", "delivery_profile: expedited\n" * 2, 1)
            manifest.write_text(text.replace(
                "  - path: servicio-a\n", "    - path: servicio-a\n", 1), encoding=ENCODING)
            precedence = execute(root)
            assert precedence.returncode == 1 and "GUARD:model clave-duplicada" in precedence.stderr

        with tempfile.TemporaryDirectory(prefix="delivery-profile-empty-plans-") as directory:
            root = Path(directory)
            orquestacion.materialize("MODELO_VALIDO", root)
            base = root / ".sdd" / "notificaciones-v2"
            result = subprocess.run(
                [sys.executable, str(script), str(base / "manifest.yml"),
                 str(base / "master-spec.md"), ""],
                cwd=root, capture_output=True, text=True, check=False,
            )
            assert result.returncode == 99
            assert result.stderr == "ARNES:orchestration-model repo_plans vacio\n"

        with tempfile.TemporaryDirectory(prefix="delivery-profile-model-dependency-") as directory:
            root = Path(directory)
            orquestacion.materialize("PROFILE_LOW", root)
            scripts = root / "skills" / "sdd-orchestrator" / "scripts"
            scripts.mkdir(parents=True)
            copied = scripts / script.name
            shutil.copy2(script, copied)
            shutil.copy2(script.parent / "_yaml.py", scripts / "_yaml.py")
            base = root / ".sdd" / "notificaciones-v2"
            plans = [root / service / ".plans" / "notificaciones-v2" / "plan.md"
                     for service in ("servicio-a", "servicio-b")]
            args = [sys.executable, str(copied), str(base / "manifest.yml"),
                    str(base / "master-spec.md"), *map(str, plans)]
            for kind, body in (("ausente", None),
                               ("incompatible", "DELIVERY_PROFILE_CONTRACT_VERSION = 2\n")):
                helper_dir = root / "skills" / "sdd-flow" / "scripts"
                if helper_dir.exists():
                    shutil.rmtree(helper_dir.parent.parent)
                if body is not None:
                    helper_dir.mkdir(parents=True)
                    (helper_dir / "delivery_profile.py").write_text(body, encoding=ENCODING)
                result = subprocess.run(args, cwd=root, capture_output=True, text=True, check=False)
                assert result.returncode == 99, result.stderr
                assert result.stderr == (
                    f"ARNES:orchestration-model delivery-profile-helper-{kind}\n")
                assert "Traceback" not in result.stderr
    finally:
        for temporary in cleanups:
            temporary.cleanup()
    print("DELIVERY_PROFILE_MODEL_OK")


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


def test_delivery_profile_materialization(_context: Optional[object]) -> None:
    """The complete profile carrier exists and validates before the distribution gate."""
    script = ROOT / "skills" / "sdd-orchestrator" / "scripts" / "orchestration-model.py"
    skill = (ROOT / "skills" / "sdd-orchestrator" / "SKILL.md").read_text(encoding=ENCODING)

    with tempfile.TemporaryDirectory(prefix="delivery-profile-materialization-") as directory:
        root = Path(directory)
        outputs = set(orquestacion.materialize("PROFILE_LOW", root))
        expected = _expected_files(root)
        assert outputs == expected

        base = root / ".sdd" / "notificaciones-v2"
        manifest = (base / "manifest.yml").read_text(encoding=ENCODING)
        assert "delivery_profile: expedited\n" in manifest
        assert "risk: low\n" in manifest
        assert manifest.count("  - scope: ") == 4
        for scope in ("global", "integration", "repo:servicio-a", "repo:servicio-b"):
            assert f"  - scope: {scope}\n" in manifest

        plans = []
        expected_complexities = {"servicio-a": "normal", "servicio-b": "trivial"}
        for repo, complexity in expected_complexities.items():
            plan = root / repo / ".plans" / "notificaciones-v2" / "plan.md"
            plans.append(str(plan))
            text = plan.read_text(encoding=ENCODING)
            assert f"repo: {repo}\n" in text
            assert f"complexity: {complexity}\n" in text
            assert "delivery_profile: expedited\n" in text
            assert "risk: low\n" in text

        assert (base / "master-spec.md") in outputs
        assert (base / "integracion.md") in outputs
        result = subprocess.run(
            [sys.executable, str(script), str(base / "manifest.yml"),
             str(base / "master-spec.md"), *plans],
            cwd=root, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr

    assert ("(`id`, `repo`, `branch`, `base_commit`, `change_type`, `complexity`, "
            "`delivery_profile`, `risk`, `status: planned`, `created_at`)" in skill)

    router = skill.split("<!-- delivery-profile-router:start -->", 1)[1].split(
        "<!-- delivery-profile-router:end -->", 1)[0].lower()
    for token in ("todos los candidatos", "antes del gate", "solo después de aprobar",
                  "hash o cadena", "reabre diseño/reparto"):
        assert token in router
    print("DELIVERY_PROFILE_MATERIALIZATION_OK")


def test_delivery_profile_predispatch(_context: Optional[object]) -> None:
    """The pre-dispatch guards reject drift without blocking independent repositories."""
    scripts = ROOT / "skills" / "sdd-orchestrator" / "scripts"
    skill = (ROOT / "skills" / "sdd-orchestrator" / "SKILL.md").read_text(encoding=ENCODING)
    router = skill.split("<!-- delivery-profile-predispatch:start -->", 1)[1].split(
        "<!-- delivery-profile-predispatch:end -->", 1)[0]
    router = " ".join(router.split())
    assert "Solo `orchestration-state.py`" in router
    assert "`integracion-ownership.py` valida el par global sin asumir esa autoridad local" in router

    def run(script_name: str, scenario: str, repos=("servicio-a", "servicio-b"),
            blank: bool = False) -> subprocess.CompletedProcess:
        temporary = tempfile.TemporaryDirectory(prefix="delivery profile predispatch ")
        cleanups.append(temporary)
        root = Path(temporary.name)
        orquestacion.materialize(scenario, root)
        base = root / ".sdd" / "notificaciones-v2"
        plans = [""] if blank else [
            root / repo / ".plans" / "notificaciones-v2" / "plan.md" for repo in repos]
        if script_name == "orchestration-state.py":
            arguments = [base / "manifest.yml", base / "master-spec.md",
                         base / "integracion.md", base / "bitacora.md", "final", *plans]
        else:
            arguments = [base / "manifest.yml", *plans]
        return subprocess.run(
            [sys.executable, str(scripts / script_name), *map(str, arguments)],
            cwd=root, capture_output=True, text=True, check=False,
        )

    cleanups: List[tempfile.TemporaryDirectory] = []
    try:
        for script_name in ("orchestration-state.py", "integracion-ownership.py"):
            for scenario in ("PROFILE_LOW", "PROFILE_SPACED_MANIFEST", "PROFILE_BAD_DELIMITER"):
                valid = run(script_name, scenario)
                assert valid.returncode == 0, (script_name, scenario, valid.stderr)
            assert run(script_name, "PROFILE_LOW", ()).returncode == 0
            blank = run(script_name, "PROFILE_LOW", (), True)
            assert blank.returncode == 99 and blank.stderr == \
                f"ARNES:{script_name.removesuffix('.py')} repo_plans vacio\n"
            expected = {
                "PROFILE_PAIR_DIVERGES": "perfil-manifest-plan-diverge",
                "PROFILE_MIXED_PLAN": "carrier-mixto",
                "PROFILE_DUPLICATE_SPACED": "clave-duplicada",
                "PROFILE_PLAN_REPO_DUPLICATE": "clave-duplicada",
            }
            prefix = "state" if script_name == "orchestration-state.py" else "integracion"
            for scenario, diagnostic in expected.items():
                result = run(script_name, scenario)
                assert result.returncode == 1, (script_name, scenario, result.stderr)
                assert [line for line in result.stderr.splitlines()
                        if line.startswith("GUARD:")] == [f"GUARD:{prefix} {diagnostic}"]
                assert "ESTADO:" not in result.stdout + result.stderr

        reordered = run("orchestration-state.py", "PROFILE_REORDERED_ITEMS",
                        ("servicio-a", "servicio-b", "servicio-c"))
        assert reordered.returncode == 0 and "ESTADO:done" in reordered.stdout

        with tempfile.TemporaryDirectory(prefix="delivery profile wrong repo ") as directory:
            root = Path(directory)
            orquestacion.materialize("PROFILE_LOW", root)
            base = root / ".sdd/notificaciones-v2"
            plans = [root / repo / ".plans/notificaciones-v2/plan.md"
                     for repo in ("servicio-a", "servicio-b")]
            plans[1].write_text(plans[1].read_text(encoding=ENCODING).replace(
                "repo: servicio-b", "repo: servicio-z"), encoding=ENCODING)
            wrong_repo = subprocess.run(
                [sys.executable, str(scripts / "orchestration-state.py"),
                 str(base / "manifest.yml"), str(base / "master-spec.md"),
                 str(base / "integracion.md"), str(base / "bitacora.md"), "final", *map(str, plans)],
                cwd=root, capture_output=True, text=True, check=False)
            assert (wrong_repo.returncode == 1 and "GUARD:state carrier-mixto" in wrong_repo.stderr
                    and f"  plan: {plans[1]}\n" in wrong_repo.stderr)

        cases = (
            ("PROFILE_COMPLEXITY_DIVERGES", "complexity-assessment-manifest-plan-diverge", None),
            ("PROFILE_REPO_RISK_DIVERGES", "risk-assessment-manifest-diverge", None),
            ("PROFILE_DUPLICATE_REPO", "repo-duplicado", None),
            ("PROFILE_REPO_PATH_DUPLICATE", "clave-duplicada", None),
            ("PROFILE_DUPLICATE_REPOS_SECTION", "clave-duplicada", None),
            ("PROFILE_DUPLICATE_REPOS_INLINE", "clave-duplicada", None),
            ("PROFILE_REPO_RISK_SPACED_DUPLICATE", "carrier-mixto", None),
            ("PROFILE_LOW", "plan-repo-duplicado", ("servicio-a", "servicio-b", "servicio-b")),
        )
        for scenario, diagnostic, repos in cases:
            result = run("orchestration-state.py", scenario, repos or ("servicio-a", "servicio-b"))
            assert result.returncode == 1, (scenario, result.stdout, result.stderr)
            assert [line for line in result.stderr.splitlines() if line.startswith("GUARD:")] == [f"GUARD:state {diagnostic}"]
            assert "ESTADO:" not in result.stdout + result.stderr
        assert run("integracion-ownership.py", "PROFILE_REPO_RISK_DIVERGES").returncode == 0

        provenance = run("orchestration-state.py", "PROFILE_ASSESSMENT_BAD_PROVENANCE")
        assert provenance.returncode == 1
        assert [line for line in provenance.stderr.splitlines()
                if line.startswith("GUARD:")] == [
                    "GUARD:state assessment-provenance-invalida"]
        assert "ESTADO:" not in provenance.stdout + provenance.stderr

        enum_diagnostics = {
            "urgency": ("normal", "assessment-urgency-invalida"),
            "complexity": ("complex", "complejidad-desconocida"),
            "risk": ("low", "riesgo-desconocido"),
            "confidence": ("high", "assessment-confidence-invalida"),
        }
        for field, (value, diagnostic) in enum_diagnostics.items():
            with tempfile.TemporaryDirectory(
                    prefix=f"delivery-profile-state-{field}-list-") as directory:
                root = Path(directory)
                orquestacion.materialize("PROFILE_LOW", root)
                base = root / ".sdd" / "notificaciones-v2"
                manifest = base / "manifest.yml"
                text = manifest.read_text(encoding=ENCODING)
                needle = f"    {field}: {value}\n"
                assert needle in text
                manifest.write_text(
                    text.replace(needle, f"    {field}: [{value}]\n", 1),
                    encoding=ENCODING,
                )
                plans = [root / repo / ".plans" / "notificaciones-v2" / "plan.md"
                         for repo in ("servicio-a", "servicio-b")]
                result = subprocess.run(
                    [sys.executable, str(scripts / "orchestration-state.py"),
                     str(manifest), str(base / "master-spec.md"),
                     str(base / "integracion.md"), str(base / "bitacora.md"), "final", *map(str, plans)],
                    cwd=root, capture_output=True, text=True, check=False,
                )
                assert result.returncode == 1, (field, result.stderr)
                assert [line for line in result.stderr.splitlines()
                        if line.startswith("GUARD:")] == [f"GUARD:state {diagnostic}"]
                assert "Traceback" not in result.stderr

        with tempfile.TemporaryDirectory(prefix="delivery-profile-state-authority-") as directory:
            root = Path(directory)
            orquestacion.materialize("PROFILE_LOW", root)
            base = root / ".sdd" / "notificaciones-v2"
            manifest = base / "manifest.yml"
            text = manifest.read_text(encoding=ENCODING)
            assert text.count("    complexity: trivial\n") == 2
            manifest.write_text(
                text.replace("    complexity: trivial\n", "    complexity: complex\n"),
                encoding=ENCODING,
            )
            only_independent_plan = (
                root / "servicio-a" / ".plans" / "notificaciones-v2" / "plan.md")
            result = subprocess.run(
                [sys.executable, str(scripts / "orchestration-state.py"),
                 str(manifest), str(base / "master-spec.md"),
                 str(base / "integracion.md"), str(base / "bitacora.md"), "final",
                 str(only_independent_plan)],
                cwd=root, capture_output=True, text=True, check=False,
            )
            assert result.returncode == 1, result.stderr
            assert [line for line in result.stderr.splitlines()
                    if line.startswith("GUARD:")] == ["GUARD:state expedited-inelegible"]
            assert "ESTADO:" not in result.stdout + result.stderr

        with tempfile.TemporaryDirectory(prefix="delivery-profile-state-duplicate-assessment-") as directory:
            root = Path(directory)
            orquestacion.materialize("PROFILE_LOW", root)
            base = root / ".sdd" / "notificaciones-v2"
            manifest = base / "manifest.yml"
            text = manifest.read_text(encoding=ENCODING)
            needle = "  - scope: repo:servicio-a\n"
            assert text.count(needle) == 1
            manifest.write_text(
                text.replace(needle, "delivery_assessment:\n" + needle),
                encoding=ENCODING,
            )
            plan = root / "servicio-a" / ".plans" / "notificaciones-v2" / "plan.md"
            result = subprocess.run(
                [sys.executable, str(scripts / "orchestration-state.py"),
                 str(manifest), str(base / "master-spec.md"),
                 str(base / "integracion.md"), str(base / "bitacora.md"), "final", str(plan)],
                cwd=root, capture_output=True, text=True, check=False,
            )
            assert result.returncode == 1, result.stderr
            assert [line for line in result.stderr.splitlines()
                    if line.startswith("GUARD:")] == ["GUARD:state clave-duplicada"]
            assert "ESTADO:" not in result.stdout + result.stderr

        with tempfile.TemporaryDirectory(prefix="delivery-profile-state-inline-duplicate-") as directory:
            root = Path(directory)
            orquestacion.materialize("PROFILE_LOW", root)
            base = root / ".sdd" / "notificaciones-v2"
            manifest = base / "manifest.yml"
            text = manifest.read_text(encoding=ENCODING)
            assert text.count("\nrepos:\n") == 1
            manifest.write_text(
                text.replace("\nrepos:\n", "\ndelivery_assessment: []\nrepos:\n", 1),
                encoding=ENCODING,
            )
            plan = root / "servicio-a" / ".plans" / "notificaciones-v2" / "plan.md"
            result = subprocess.run(
                [sys.executable, str(scripts / "orchestration-state.py"),
                 str(manifest), str(base / "master-spec.md"),
                 str(base / "integracion.md"), str(base / "bitacora.md"), "final", str(plan)],
                cwd=root, capture_output=True, text=True, check=False,
            )
            assert result.returncode == 1, result.stderr
            assert [line for line in result.stderr.splitlines()
                    if line.startswith("GUARD:")] == ["GUARD:state clave-duplicada"]
            assert "ESTADO:" not in result.stdout + result.stderr

        with tempfile.TemporaryDirectory(prefix="delivery-profile-state-inline-assessment-") as directory:
            root = Path(directory)
            orquestacion.materialize("PROFILE_LOW", root)
            base = root / ".sdd" / "notificaciones-v2"
            manifest = base / "manifest.yml"
            text = manifest.read_text(encoding=ENCODING)
            before, remainder = text.split("delivery_assessment:\n", 1)
            _assessment, after = remainder.split("repos:\n", 1)
            manifest.write_text(
                before + "delivery_assessment: []\nrepos:\n" + after,
                encoding=ENCODING,
            )
            plan = root / "servicio-a" / ".plans" / "notificaciones-v2" / "plan.md"
            result = subprocess.run(
                [sys.executable, str(scripts / "orchestration-state.py"),
                 str(manifest), str(base / "master-spec.md"),
                 str(base / "integracion.md"), str(base / "bitacora.md"), "final", str(plan)],
                cwd=root, capture_output=True, text=True, check=False,
            )
            assert result.returncode == 1, result.stderr
            assert [line for line in result.stderr.splitlines()
                    if line.startswith("GUARD:")] == [
                        "GUARD:state assessment-forma-invalida"]

        with tempfile.TemporaryDirectory(prefix="delivery-profile-state-hyphen-extra-") as directory:
            root = Path(directory)
            orquestacion.materialize("PROFILE_LOW", root)
            base = root / ".sdd" / "notificaciones-v2"
            manifest = base / "manifest.yml"
            text = manifest.read_text(encoding=ENCODING)
            needle = "    confidence: high\n"
            assert needle in text
            manifest.write_text(
                text.replace(needle, needle + "    extra-field: nope\n", 1),
                encoding=ENCODING,
            )
            plan = root / "servicio-a" / ".plans" / "notificaciones-v2" / "plan.md"
            result = subprocess.run(
                [sys.executable, str(scripts / "orchestration-state.py"),
                 str(manifest), str(base / "master-spec.md"),
                 str(base / "integracion.md"), str(base / "bitacora.md"), "final", str(plan)],
                cwd=root, capture_output=True, text=True, check=False,
            )
            assert result.returncode == 1, result.stderr
            assert [line for line in result.stderr.splitlines()
                    if line.startswith("GUARD:")] == [
                        "GUARD:state assessment-forma-invalida"]
            assert "ESTADO:" not in result.stdout + result.stderr
            assert "ESTADO:" not in result.stdout + result.stderr

        with tempfile.TemporaryDirectory(prefix="delivery-profile-rejected-") as directory:
            root = Path(directory)
            orquestacion.materialize("PROFILE_PREDISPATCH_REJECTED", root)
            base = root / ".sdd" / "notificaciones-v2"
            plans = [root / repo / ".plans" / "notificaciones-v2" / "plan.md"
                     for repo in ("servicio-a", "servicio-b")]
            observed = {
                path: path.read_bytes() for path in (
                    base / "manifest.yml", base / "bitacora.md",
                    root / "servicio-a" / ".plans" / "notificaciones-v2" / "plan.md",
                    root / "servicio-b" / ".plans" / "notificaciones-v2" / "plan.md",
                )
            }
            result = subprocess.run(
                [sys.executable, str(scripts / "orchestration-state.py"),
                 str(base / "manifest.yml"), str(base / "master-spec.md"),
                 str(base / "integracion.md"), str(base / "bitacora.md"), "final", *map(str, plans)],
                cwd=root, capture_output=True, text=True, check=False,
            )
            assert result.returncode == 1
            assert "GUARD:state complexity-assessment-manifest-plan-diverge" in result.stderr
            independent_plan = root / "servicio-a" / ".plans" / "notificaciones-v2" / "plan.md"
            independent = subprocess.run(
                [sys.executable, str(scripts / "orchestration-state.py"),
                 str(base / "manifest.yml"), str(base / "master-spec.md"),
                 str(base / "integracion.md"), str(base / "bitacora.md"), "final",
                 str(independent_plan)],
                cwd=root, capture_output=True, text=True, check=False,
            )
            assert independent.returncode == 0, independent.stderr
            assert "ESTADO:en-curso" in independent.stdout
            log = (base / "bitacora.md").read_text(encoding=ENCODING)
            assert "objeto: servicio-b" in log and "resultado: rechazado" in log
            assert "status: tasks-ready" in (root / "servicio-a" / ".plans" /
                                               "notificaciones-v2" / "plan.md").read_text(
                                                   encoding=ENCODING)
            assert all(path.read_bytes() == body for path, body in observed.items())
            assert not (root / ".cross-model").exists()

        for script_name in ("orchestration-state.py", "integracion-ownership.py"):
            with tempfile.TemporaryDirectory(prefix="delivery-profile-dependency-") as directory:
                root = Path(directory)
                orquestacion.materialize("PROFILE_LOW", root)
                target = root / "skills" / "sdd-orchestrator" / "scripts"
                target.mkdir(parents=True)
                shutil.copy2(scripts / script_name, target / script_name)
                shutil.copy2(scripts / "_yaml.py", target / "_yaml.py")
                base = root / ".sdd" / "notificaciones-v2"
                plans = [root / repo / ".plans" / "notificaciones-v2" / "plan.md"
                         for repo in ("servicio-a", "servicio-b")]
                if script_name == "orchestration-state.py":
                    arguments = [base / "manifest.yml", base / "master-spec.md",
                                 base / "integracion.md", base / "bitacora.md", "final", *plans]
                    label = "orchestration-state"
                else:
                    arguments = [base / "manifest.yml", *plans]
                    label = "integracion-ownership"
                helper = root / "skills" / "sdd-flow" / "scripts" / "delivery_profile.py"
                for kind, body in (("ausente", None),
                                   ("incompatible", "DELIVERY_PROFILE_CONTRACT_VERSION = 2\n")):
                    if helper.parent.parent.exists():
                        shutil.rmtree(helper.parent.parent)
                    if body is not None:
                        helper.parent.mkdir(parents=True)
                        helper.write_text(body, encoding=ENCODING)
                    result = subprocess.run(
                        [sys.executable, str(target / script_name), *map(str, arguments)],
                        cwd=root, capture_output=True, text=True, check=False,
                    )
                    assert result.returncode == 99, (script_name, kind, result.stderr)
                    assert result.stderr == f"ARNES:{label} delivery-profile-helper-{kind}\n"
                    assert "Traceback" not in result.stderr
    finally:
        for temporary in cleanups:
            temporary.cleanup()

    skill = (ROOT / "skills" / "sdd-orchestrator" / "SKILL.md").read_text(encoding=ENCODING)
    block = skill.split("<!-- delivery-profile-predispatch:start -->", 1)[1].split(
        "<!-- delivery-profile-predispatch:end -->", 1)[0]
    block = " ".join(block.split())
    for token in ("registrar intento rechazado", "no crear sobre",
                  "conservar el estado del repo", "bloquear sus dependientes",
                  "repos independientes continúan"):
        assert token in block


def test_delivery_profile_dispatch(_context: Optional[object]) -> None:
    """Materialization and pre-dispatch enforcement form one dispatch contract."""
    test_delivery_profile_materialization(_context)
    test_delivery_profile_predispatch(_context)
    print("DELIVERY_PROFILE_DISPATCH_OK")


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
    ("delivery-profile:model", "delivery-profile", test_delivery_profile_model),
    ("delivery-profile:materialization", "delivery-profile",
     test_delivery_profile_materialization),
    ("delivery-profile:predispatch", "delivery-profile", test_delivery_profile_predispatch),
    ("delivery-profile:dispatch", "delivery-profile", test_delivery_profile_dispatch),
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
