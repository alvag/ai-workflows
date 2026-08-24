"""Predicado: toda página que el metaíndice declara existe, no hay páginas huérfanas ni duplicadas,
y el conjunto de IDs que el metaíndice lista coincide exactamente con el de las páginas."""

from __future__ import annotations

import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

from _tabla import parsear_tabla_pipe


def filas_datos(texto: str, cabecera: str) -> list[list[str]]:
    return [fila for fila in parsear_tabla_pipe(texto) if fila and fila[0] != cabecera]


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:metaindice base", file=sys.stderr)
        return 2
    base = Path(sys.argv[1])
    meta = Path(f"{base}.md")
    with tempfile.TemporaryDirectory():
        if not meta.is_file():
            print("GUARD:metaindice-completo no existe el metaíndice", file=sys.stderr)
            return 1
        try:
            declaradas = filas_datos(meta.read_text(encoding="utf-8"), "Página")
        except (OSError, UnicodeError):
            declaradas = []
        rutas = sorted(fila[1] for fila in declaradas if len(fila) >= 4)
        rc = 0
        for ruta in rutas:
            if not (base.parent / ruta).is_file():
                print(f"GUARD:pagina-declarada-existe el metaíndice declara {ruta} y no existe", file=sys.stderr)
                rc = 1
        duplicadas = sorted(ruta for ruta, cantidad in Counter(rutas).items() if cantidad > 1)
        if duplicadas:
            print(f"GUARD:pagina-declarada-existe página declarada dos veces: {' '.join(duplicadas)} ", file=sys.stderr)
            rc = 1
        patron = re.compile(rf"{re.escape(base.name)}-p[0-9]{{2}}\.md")
        disco = sorted(path.name for path in base.parent.iterdir() if path.is_file() and patron.fullmatch(path.name))
        huerfanas = sorted(set(disco) - set(rutas))
        if huerfanas:
            print(f"GUARD:pagina-declarada-existe página huérfana, no listada: {' '.join(huerfanas)} ", file=sys.stderr)
            rc = 1
        ids_meta = sorted(item for fila in declaradas if len(fila) >= 4 for item in fila[3].split())
        ids_paginas = []
        for ruta in rutas:
            pagina = base.parent / ruta
            if pagina.is_file():
                ids_paginas.extend(fila[0] for fila in filas_datos(pagina.read_text(encoding="utf-8"), "ID"))
        ids_paginas.sort()
        if ids_meta != ids_paginas:
            print(
                f"GUARD:metaindice-completo meta=[{' '.join(ids_meta)} ] "
                f"paginas=[{' '.join(ids_paginas)} ]",
                file=sys.stderr,
            )
            rc = 1
        for fila in declaradas:
            if len(fila) < 4:
                continue
            pagina = base.parent / fila[1]
            if not pagina.is_file():
                continue
            real = len(filas_datos(pagina.read_text(encoding="utf-8"), "ID"))
            if fila[2] != str(real):
                print(f"GUARD:paridad-por-pagina {fila[1]} declara {fila[2]} entradas y tiene {real}", file=sys.stderr)
                rc = 1
        return rc


if __name__ == "__main__":
    raise SystemExit(main())
