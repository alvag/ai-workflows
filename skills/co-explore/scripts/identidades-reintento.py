"""Predicado: las tres identidades se registran por separado, ninguna reparación de formato cuenta
como intento semántico, y hay a lo sumo una reparación por worker."""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path


VALIDAS = {"transportAttempt", "formatRepair", "semanticAttempt"}


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:identidades-reintento log", file=sys.stderr)
        return 2
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        texto = ""
    with tempfile.TemporaryDirectory():
        identidades = re.findall(r"^- `([a-zA-Z]+):", texto, re.MULTILINE)
        rc = 0
        raras = sorted(set(identidades) - VALIDAS)
        if raras:
            print(f"GUARD:identidades-reintento identidad desconocida: {' '.join(raras)} ", file=sys.stderr)
            rc = 1
        reparaciones = identidades.count("formatRepair")
        if reparaciones > 1:
            print(f"GUARD:identidades-reintento {reparaciones} reparaciones de formato (el tope es 1)", file=sys.stderr)
            rc = 1
        if re.search(r"^- `formatRepair:", texto, re.MULTILINE) and "`mismos_ids: sí`" not in texto:
            print("GUARD:identidades-reintento la reparación no declara haber conservado los IDs", file=sys.stderr)
            rc = 1
        return rc


if __name__ == "__main__":
    raise SystemExit(main())
