"""Caracteriza la fabrica de orquestacion desde su implementacion base."""

from __future__ import annotations

import os
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
                arguments = [base / "manifest.yml", base / "master-spec.md"]
            elif script == "orchestration-contract.py":
                arguments = [base / "manifest.yml", base / "integracion.md"]
            elif script == "orchestration-state.py":
                plans = " ".join(str(root / service / ".plans" / "notificaciones-v2" /
                                     "plan.md") for service in ("servicio-a", "servicio-b"))
                arguments = [base / "manifest.yml", base / "master-spec.md",
                             base / "integracion.md", base / "bitacora.md", plans]
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


CASOS: List[Case] = [
    ("fixtures-v12:sede-aridad", "fixtures-orquestacion-v12",
     test_v12_single_declared_site_and_arity),
    ("fixtures-v12:publicacion-directa", "fixtures-orquestacion-v12",
     test_v12_direct_publication),
    ("fixtures-v12:publicacion-rename", "fixtures-orquestacion-v12",
     test_v12_rename_publication),
    ("fixtures-v12:precedencias", "fixtures-orquestacion-v12",
     test_v12_consumers_preserve_precedence),
]
