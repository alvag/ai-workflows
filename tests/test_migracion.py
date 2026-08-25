"""Verifica desde el tag la evidencia irrepetible de la migracion."""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from tests.migracion import EXPECTED_CASES, EXPECTED_MARKERS, REPORT, verify_report


Case = Tuple[str, str, Callable[[Optional[object]], None]]


def test_v10_v11_v13b_snapshot_dual(_context: Optional[object]) -> None:
    """El snapshot recalcula la corrida dual y la calibracion de cadena."""
    result = verify_report(REPORT)
    assert result["compared"] == EXPECTED_CASES
    assert result["divergences"] == 0
    assert result["chain_fixtures"] == 11
    assert result["chain_hashes"] > 0
    assert result["markers"] == EXPECTED_MARKERS


CASOS: List[Case] = [
    ("migracion-snapshot-v13b", "migracion-dual", test_v10_v11_v13b_snapshot_dual),
]
