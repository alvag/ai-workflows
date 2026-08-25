"""Predicado: el paquete entregado no se modifica —la respuesta crea una versión nueva— y el
truncado previo al dispatch alcanza a TODAS las versiones."""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("USO:paquete-versionado scratch v1_hash", file=sys.stderr)
        return 2
    scratch, esperado = Path(sys.argv[1]), sys.argv[2]
    rc = 0
    versiones = sorted(path for path in scratch.iterdir() if path.is_file()) if scratch.is_dir() else []
    v1 = next((path for path in versiones if re.fullmatch(r"paquete-.*-v1\.txt", path.name)), None)
    if v1 is not None:
        # Binary input is required because the contract hashes the file's exact bytes.
        actual = hashlib.sha256(v1.read_bytes()).hexdigest()
        if actual != esperado:
            print(f"GUARD:paquete-inmutable el paquete entregado cambió ({actual} ≠ {esperado})", file=sys.stderr)
            rc = 1
    if os.environ.get("redespachado", "0") == "1":
        restantes = sum(bool(re.fullmatch(r"paquete-.*-v[0-9]+\.txt", path.name)) for path in versiones)
        if restantes:
            print(f"GUARD:truncado-alcanza-versiones sobrevivieron {restantes} versiones al redespacho", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
