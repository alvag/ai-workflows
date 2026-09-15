"""Prueba que un refresh no altera la entrada de un worker todavía activo."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from tests.arbol import _instantanea


ENCODING = "utf-8"
RAIZ = Path(__file__).resolve().parents[2]
PROMOCION = RAIZ / "skills" / "sdd-flow" / "scripts" / "promocion-tasks-ready.py"
Caso = Tuple[str, str, object]


def _preparar(arena: Path) -> Tuple[Path, Path, Path, Path, str]:
    spec = importlib.util.spec_from_file_location("promotion_immutability", PROMOCION)
    if spec is None or spec.loader is None:
        raise AssertionError("no se pudo cargar promoción")
    modulo = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(PROMOCION.parent))
    try:
        spec.loader.exec_module(modulo)
    finally:
        sys.path.pop(0)
    return modulo.preparar_estado_refresh(arena, sobre=True)


def test_refresh_respeta_worker_en_vuelo(_contexto: Optional[object]) -> None:
    """Bloquea con sobre activo y admite la nueva secuencia después de retirarlo."""
    with tempfile.TemporaryDirectory(prefix="contrato-inmutabilidad-") as temporal:
        arena = Path(temporal)
        plan, bitacora, ledger, envelopes, hash_v2 = _preparar(arena)
        antes = _instantanea(arena / ".plans" / "caso")
        comando = [sys.executable, str(PROMOCION), str(plan), str(bitacora), str(ledger),
                   str(envelopes)]
        bloqueado = subprocess.run(
            comando, capture_output=True, text=True, encoding=ENCODING, check=False)
        assert bloqueado.returncode == 1
        assert "refresh sin ledger terminal" in bloqueado.stderr
        assert _instantanea(arena / ".plans" / "caso") == antes
        (envelopes / "activo.json").unlink()
        admitido = subprocess.run(
            comando, capture_output=True, text=True, encoding=ENCODING, check=False)
        assert admitido.returncode == 0, admitido.stderr
        texto = plan.read_text(encoding=ENCODING)
        assert "contract_frozen_version: 2\n" in texto
        assert f"contract_frozen_hash: {hash_v2}\n" in texto
        paquetes = tuple((plan.parent / "sequences").iterdir())
        assert len(paquetes) == 1
        assert set(ruta.name for ruta in paquetes[0].iterdir()) == {
            "plan.md", "rotation-link.json", "sequence-ledger.yml",
        }


CASOS: List[Caso] = [
    ("contrato-inmutabilidad:refresh-worker", "contrato-inmutabilidad-v1",
     test_refresh_respeta_worker_en_vuelo),
]
