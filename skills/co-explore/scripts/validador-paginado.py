"""Predicado: la UNIÓN de las páginas tiene paridad exacta con el detalle — ni una entrada indexada
sin desarrollo, ni un desarrollo sin entrada en ninguna página."""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

from _tabla import parsear_tabla_pipe


def main() -> int:
    if len(sys.argv) != 3:
        print("USO:validador-paginado base detail", file=sys.stderr)
        return 2
    base, detail = Path(sys.argv[1]), Path(sys.argv[2])
    with tempfile.TemporaryDirectory():
        try:
            meta = Path(f"{base}.md").read_text(encoding="utf-8")
            detalle = detail.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            meta, detalle = "", ""
        rutas = [fila[1] for fila in parsear_tabla_pipe(meta) if len(fila) >= 2 and fila[0] != "Página"]
        union = []
        for ruta in rutas:
            pagina = base.parent / ruta
            if pagina.is_file():
                union.extend(fila[0] for fila in parsear_tabla_pipe(pagina.read_text(encoding="utf-8")) if fila and fila[0] != "ID")
        union.sort()
        desarrollos = sorted(
            match.group(1)
            for linea in detalle.splitlines()
            if (match := re.fullmatch(r"###\s+([A-Z]{3}-[A-Z]-[A-Z]{3}-[0-9]{3})\s*", linea))
        )
        rc = 0
        sin_desarrollo = sorted(set(union) - set(desarrollos))
        sin_entrada = sorted(set(desarrollos) - set(union))
        if sin_desarrollo:
            print(f"GUARD:paridad-union indexado sin desarrollo: {' '.join(sin_desarrollo)} ", file=sys.stderr)
            rc = 1
        if sin_entrada:
            print(f"GUARD:paridad-union desarrollo sin entrada: {' '.join(sin_entrada)} ", file=sys.stderr)
            rc = 1
        if not union:
            print("GUARD:paridad-union la unión de las páginas está vacía", file=sys.stderr)
            rc = 1
        return rc


if __name__ == "__main__":
    raise SystemExit(main())
