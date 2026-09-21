"""Predicado: comprueba que SKILL y reference enseñen la misma cadena de producción, verificación,
ownership y recuperación, incluidas la proyección bloqueada y la rotación de secuencia."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Tuple


USO = "USO:verify-ejecuta sdd_flow_skill sdd_flow_reference"


# Cuatro identidades cerradas. El valor indica en qué sede debe aparecer cada marcador.
#
# Qué detecta: que `verify` siga CARGANDO su fila declarada en vez de elegir evidencia al final.
# Qué NO detecta: que la fila cargada sea la correcta, ni que el comando discrimine algo.
# Campos: clase **veredicto**; dirección **admite-de-mas** — es una guarda de literales textuales,
# así que una reescritura que conserve las frases y pierda la propiedad pasa igual.
IDENTIDADES: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "documentos-canonicos": ("ambos", ("El contrato de verificación, en dos formas",)),
    "cargar-ausente": ("skill", ("**CARGAR**",)),
    "identificar-presente": ("skill-ausente", ("**IDENTIFICAR**",)),
    "revert-ausente": ("skill", ("revert-to-confirm",)),
}


def main() -> int:
    if len(sys.argv) != 3:
        print(USO, file=sys.stderr)
        return 2
    try:
        skill = Path(sys.argv[1]).read_text(encoding="utf-8")
        reference = Path(sys.argv[2]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        print("GUARD:verify-solo-ejecuta documentos canónicos inaccesibles", file=sys.stderr)
        return 1
    if len(IDENTIDADES) != 4 or len(set(IDENTIDADES)) != 4:
        print("GUARD:verify-solo-ejecuta tabla interna distinta de cuatro", file=sys.stderr)
        return 1
    errores = []
    for identidad, (sede, marcadores) in IDENTIDADES.items():
        if sede == "skill-ausente":
            if any(marcador in skill for marcador in marcadores):
                errores.append(identidad)
            continue
        textos = (skill, reference) if sede == "ambos" else (skill,)
        if any(any(marcador not in texto for marcador in marcadores) for texto in textos):
            errores.append(identidad)
    if errores:
        print("GUARD:verify-solo-ejecuta faltan marcadores: " + ", ".join(errores), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
