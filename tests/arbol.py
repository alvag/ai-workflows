"""Instantánea pura de un árbol de archivos, sin efectos de importación."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Dict, Tuple

ENCODING = "utf-8"
Instantanea = Dict[str, Tuple[str, int, bytes]]


def _instantanea(raiz: Path) -> Instantanea:
    resultado: Instantanea = {}
    for ruta in sorted(raiz.rglob("*")):
        relativa = ruta.relative_to(raiz)
        if ".git" in relativa.parts:
            continue
        modo = stat.S_IMODE(ruta.lstat().st_mode)
        if ruta.is_symlink():
            contenido = os.readlink(ruta).encode(ENCODING)
            tipo = "symlink"
        elif ruta.is_dir():
            contenido = b""
            tipo = "directory"
        else:
            # The snapshot is binary because poststate comparison must preserve exact bytes.
            contenido = ruta.read_bytes()
            tipo = "file"
        resultado[str(relativa)] = (tipo, modo, contenido)
    return resultado
