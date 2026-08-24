"""Parse scalar and inline-list values from the orchestration YAML dialect."""

from __future__ import annotations

import re

__all__ = ["parsear_valor_yaml"]


def _escalar(valor: str) -> str:
    valor = valor.strip()
    if valor.startswith(("\"", "'")):
        cierre = valor.find(valor[0], 1)
        if cierre >= 0:
            valor = valor[: cierre + 1]
    else:
        comentario = re.search(r"[ \t]#", valor)
        if comentario:
            valor = valor[: comentario.start()]
    valor = valor.strip()
    if len(valor) >= 2 and valor[0] in {"\"", "'"} and valor[-1] == valor[0]:
        valor = valor[1:-1]
    return valor.strip()


def parsear_valor_yaml(valor: str) -> str | list[str]:
    """Return a restricted YAML scalar or comma-separated inline list."""
    limpio = valor.strip()
    if not limpio.startswith(("\"", "'")):
        comentario = re.search(r"[ \t]#", limpio)
        if comentario:
            limpio = limpio[: comentario.start()].strip()
    if limpio.startswith("[") and limpio.endswith("]"):
        cuerpo = limpio[1:-1].strip()
        if not cuerpo:
            return []
        return [item for parte in cuerpo.split(",") if (item := _escalar(parte))]
    return _escalar(limpio)
