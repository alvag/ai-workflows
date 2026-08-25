"""Predicado: los cuatro consumidores normativos nombran clarification-needed — el envelope, la
escalera de degradación, y las dos vistas del SKILL.md."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def seccion(texto: str, heading: str) -> str:
    lineas = texto.splitlines()
    dentro = False
    salida = []
    for linea in lineas:
        if re.fullmatch(rf"#+ {re.escape(heading)}", linea):
            dentro = True
            continue
        if dentro and re.match(r"^#{2,3} ", linea):
            break
        if dentro:
            salida.append(linea)
    contenido = "\n".join(salida)
    return re.sub(r'`[a-z0-9-]+\.md` → "[^"]*"', "", contenido)


def main() -> int:
    if len(sys.argv) != 3:
        print("USO:cuarto-estado-consumidores reference skill", file=sys.stderr)
        return 2
    try:
        reference = Path(sys.argv[1]).read_text(encoding="utf-8")
        skill = Path(sys.argv[2]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        reference, skill = "", ""
    comprobaciones = (
        (reference, "Envelope de retorno", "el envelope no admite clarification-needed"),
        (reference, "Escalera de degradación", "la escalera de degradación lo ignora"),
        (skill, "Degradación", "la vista Degradación del SKILL.md lo ignora"),
        (skill, "Salida — el envelope", "la vista del envelope del SKILL.md lo ignora"),
    )
    rc = 0
    for texto, heading, error in comprobaciones:
        if "clarification-needed" not in seccion(texto, heading):
            print(f"GUARD:cuarto-estado-en-consumidores {error}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
