"""Parse the restricted Markdown pipe tables used by skill guards."""

from __future__ import annotations

__all__ = ["parsear_tabla_pipe"]


def parsear_tabla_pipe(texto: str) -> list[list[str]]:
    """Return pipe-table rows, omitting separators and preserving case."""
    filas: list[list[str]] = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not (linea.startswith("|") and linea.endswith("|")):
            continue
        celdas = [celda.strip() for celda in linea[1:-1].split("|")]
        if celdas and all(celda and set(celda) <= {"-", ":"} for celda in celdas):
            continue
        filas.append(celdas)
    return filas
