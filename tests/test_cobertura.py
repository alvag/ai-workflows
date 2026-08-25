"""Controles positivos de cobertura y descubrimiento del entrypoint."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from typing import Callable, List, Optional, Tuple

from tests import __main__ as runner
from tests.origenes import read_targets, validate_coverage


Case = Tuple[str, str, Callable[[Optional[object]], None]]


def test_v14_three_coverage_directions(_context: Optional[object]) -> None:
    """Las tres direcciones de cobertura fallan por separado."""
    cases = runner.descubrir()
    targets = read_targets()

    migrated = next(case for case in cases if case[0].startswith("escenario:"))
    try:
        validate_coverage([case for case in cases if case != migrated], targets)
    except ValueError as exc:
        assert "migrated cases without their test" in str(exc)
    else:
        raise AssertionError("a missing migrated case did not fail coverage")

    orphan = ("orphan-control", "unknown-origin", lambda _context: None)
    try:
        validate_coverage(cases + [orphan], targets)
    except ValueError as exc:
        assert "tests without origin" in str(exc)
    else:
        raise AssertionError("an orphan test did not fail coverage")

    phantom = "guard-without-test-control"
    missing_guard_targets = replace(targets, guards=targets.guards | {phantom})
    try:
        validate_coverage(cases, missing_guard_targets)
    except ValueError as exc:
        assert "inventory rows without a test" in str(exc)
    else:
        raise AssertionError("an inventory guard without tests did not fail coverage")


def test_v20_entrypoint_ids_match_tree_sweep(_context: Optional[object]) -> None:
    """Los IDs listados por el entrypoint coinciden con el barrido del arbol."""
    swept = {identifier for identifier, _group, _function in runner.descubrir()}
    result = subprocess.run(
        [sys.executable, "-m", "tests", "--listar"],
        cwd=str(runner.RAIZ.parent), capture_output=True, text=True,
        encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    listed = {
        line.lstrip().split(None, 1)[0]
        for line in result.stdout.splitlines()
        if line.startswith("  ")
    }
    assert listed == swept
    assert result.stdout.splitlines()[0] == "inventario: {0} casos".format(len(swept))


CASOS: List[Case] = [
    ("cobertura-v14:tres-direcciones", "cobertura-v14",
     test_v14_three_coverage_directions),
    ("entrypoint-v20:ids", "entrypoint-v20", test_v20_entrypoint_ids_match_tree_sweep),
]
