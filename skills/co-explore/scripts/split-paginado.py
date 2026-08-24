"""Predicado: la salida cruda se parte en detalle único y páginas de índice de a lo sumo
$por_pagina entradas, sin perder ninguna, y el metaíndice se publica al final."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

from _tabla import parsear_tabla_pipe


def publicar_atomico(contenidos: Dict[Path, str], orden: List[Path]) -> bool:
    temporales: Dict[Path, Path] = {}
    respaldos: Dict[Path, Path] = {}
    publicados: List[Path] = []
    try:
        for destino, contenido in contenidos.items():
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="", delete=False,
                dir=str(destino.parent), prefix=f".{destino.name}.", suffix=".tmp",
            ) as archivo:
                archivo.write(contenido)
                temporales[destino] = Path(archivo.name)
        for destino in orden:
            respaldo = destino.with_name(f".{destino.name}.{os.getpid()}.bak")
            if destino.exists():
                os.replace(destino, respaldo)
                respaldos[destino] = respaldo
            os.replace(temporales[destino], destino)
            publicados.append(destino)
        for respaldo in respaldos.values():
            respaldo.unlink(missing_ok=True)
        return True
    except OSError:
        for destino in reversed(publicados):
            destino.unlink(missing_ok=True)
            if destino in respaldos and respaldos[destino].exists():
                os.replace(respaldos[destino], destino)
        for destino, respaldo in respaldos.items():
            if destino not in publicados and respaldo.exists():
                os.replace(respaldo, destino)
        return False
    finally:
        for temporal in temporales.values():
            temporal.unlink(missing_ok=True)
        for respaldo in respaldos.values():
            respaldo.unlink(missing_ok=True)


def main() -> int:
    if len(sys.argv) != 4:
        print("USO:split-paginado raw base per_page", file=sys.stderr)
        return 2
    raw_path, base = Path(sys.argv[1]), Path(sys.argv[2])
    try:
        por_pagina = int(sys.argv[3])
        texto = raw_path.read_text(encoding="utf-8")
    except (ValueError, OSError, UnicodeError):
        return 1
    if por_pagina <= 0:
        return 1
    if not any(re.fullmatch(r"## Detalle\s*", linea) for linea in texto.splitlines()):
        print("GUARD:split-sin-detalle el informe no trae la sección `## Detalle`", file=sys.stderr)
        return 1
    indice: List[str] = []
    detalle: List[str] = []
    modo = ""
    for linea in texto.splitlines():
        if re.fullmatch(r"## Índice\s*", linea):
            modo = "index"
            continue
        if re.fullmatch(r"## Detalle\s*", linea):
            modo = "detail"
            continue
        if re.fullmatch(r"STATUS: done\s*", linea):
            continue
        if modo == "index":
            indice.append(linea)
        elif modo == "detail":
            detalle.append(linea)
    cabecera = next((linea for linea in indice if re.match(r"^\|\s*ID\s*\|", linea)), "")
    separador = next((linea for linea in indice if re.fullmatch(r"\|[-: |]+\|", linea)), "")
    filas = [fila for fila in parsear_tabla_pipe("\n".join(indice)) if fila and fila[0] != "ID"]

    contenidos: Dict[Path, str] = {}
    detail_path = base.parent / f"detail-{base.name}.md"
    contenidos[detail_path] = "".join(f"{linea}\n" for linea in detalle)
    paginas: List[tuple[str, Path, List[str]]] = []
    for inicio in range(0, len(filas), por_pagina):
        numero = f"{len(paginas) + 1:02d}"
        path = Path(f"{base}-p{numero}.md")
        lote = filas[inicio : inicio + por_pagina]
        lineas = [cabecera, separador] + ["| " + " | ".join(fila) + " |" for fila in lote]
        contenidos[path] = "".join(f"{linea}\n" for linea in lineas)
        paginas.append((numero, path, [fila[0] for fila in lote]))
    meta_path = Path(f"{base}.md")
    meta = ["## Páginas", "| Página | Ruta | Entradas | IDs |", "|---|---|---|---|"]
    meta.extend(f"| {numero} | {path.name} | {len(ids)} | {' '.join(ids)} |" for numero, path, ids in paginas)
    contenidos[meta_path] = "\n".join(meta) + "\n"
    orden = [detail_path] + [path for _, path, _ in paginas] + [meta_path]
    return 0 if publicar_atomico(contenidos, orden) else 1


if __name__ == "__main__":
    raise SystemExit(main())
