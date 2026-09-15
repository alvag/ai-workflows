"""Predicado: el conductor deriva la tabla y ejecuta el baseline, el usuario aprueba en el kickoff
antes de que se congele, cada aprobar-reparación queda entre ese kickoff y el congelamiento que le
corresponde, el congelamiento precede al despacho, y los timestamps respetan el orden del log."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def campo(texto: str, paso: str, nombre: str) -> str:
    for linea in texto.splitlines():
        if f"`paso: {paso}`" not in linea:
            continue
        match = re.search(rf"`{nombre}: ([^`]*)`", linea)
        return match.group(1) if match else ""
    return ""


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:gate-modo-directo log", file=sys.stderr)
        return 2
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        texto = ""
    rc = 0
    for paso in ("derivar-tabla", "ejecutar-baseline"):
        actor = campo(texto, paso, "actor")
        if actor != "conductor":
            print(f'GUARD:conductor-deriva-y-baseline "{paso}" lo hizo "{actor or "nadie"}"', file=sys.stderr)
            rc = 1
    timestamps = re.findall(r"`timestamp: ([^`]*)`", texto)
    if timestamps != sorted(timestamps):
        print("GUARD:kickoff-antes-de-congelar la bitácora lista los pasos fuera del orden de sus timestamps", file=sys.stderr)
        rc = 1
    lineas = texto.splitlines()
    indices = {
        paso: [indice for indice, linea in enumerate(lineas)
               if f"`paso: {paso}`" in linea]
        for paso in ("aprobar-kickoff", "aprobar-reparación", "congelar", "despachar")
    }
    kickoff = campo(texto, "aprobar-kickoff", "timestamp")
    congelar = campo(texto, "congelar", "timestamp")
    despachar = campo(texto, "despachar", "timestamp")
    if not kickoff or not congelar or kickoff > congelar:
        print("GUARD:kickoff-antes-de-congelar el kickoff no aprobó antes de congelar", file=sys.stderr)
        rc = 1
    if despachar and (not congelar or congelar > despachar):
        print("GUARD:congelar-antes-de-despachar se despachó sin congelar antes", file=sys.stderr)
        rc = 1
    for indice in indices["aprobar-reparación"]:
        linea = lineas[indice]
        anteriores = [valor for valor in indices["aprobar-kickoff"] + indices["congelar"]
                      if valor < indice]
        posteriores = [valor for valor in indices["congelar"] if valor > indice]
        if not anteriores or not posteriores:
            print("GUARD:reparacion-entre-anclas una aprobación de reparación queda fuera "
                  "de kickoff/congelamiento", file=sys.stderr)
            rc = 1
        if ":cobertura-agregada:" in linea and indices["congelar"] and \
                indice > indices["congelar"][0]:
            print("GUARD:cobertura-antes-del-primer-congelamiento una adición fue aprobada tarde",
                  file=sys.stderr)
            rc = 1
    if indices["despachar"] and indices["congelar"] and \
            min(indices["despachar"]) < max(indices["congelar"]):
        print("GUARD:congelar-antes-de-despachar el despacho precede al último congelamiento",
              file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
