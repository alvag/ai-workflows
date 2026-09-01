"""Predicado: un registro por fila, en el mismo orden y sin duplicados; todo registro con commit y
timestamp ISO-8601; evidencia dentro de su enum; observado no vacío en cada RED o GREEN_ALREADY, con
exit code si la evidencia es ejecutable y sin forma de ejecutable si es manual; adjudicación
already_satisfied en cada GREEN_ALREADY y justificación en cada NOT_APPLICABLE; y ninguno de esos
cinco campos aparece como columna de la tabla."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Tuple

from _tabla import parsear_tabla_pipe


def version_vigente(texto: str) -> str:
    lineas = texto.splitlines()
    versiones: List[Tuple[int, int, int]] = []
    cerca = False
    for indice, linea in enumerate(lineas):
        if linea.startswith("```"):
            cerca = not cerca
        match = None if cerca else re.fullmatch(r"(#+) v(\d+)", linea)
        if match:
            versiones.append((int(match.group(2)), indice, len(match.group(1))))
    if not versiones:
        return ""
    _, inicio, nivel = max(versiones)
    cuerpo: List[str] = []
    cerca = False
    for linea in lineas[inicio + 1 :]:
        if linea.startswith("```"):
            cerca = not cerca
        encabezado = re.match(r"^(#+) ", linea) if not cerca else None
        if encabezado and len(encabezado.group(1)) <= nivel:
            break
        cuerpo.append(linea)
    return "\n".join(cuerpo)


# Los tres tipos que corren un proceso, y el enum completo. Van en constantes porque el chequeo de
# forma necesita las dos preguntas por separado: si la evidencia es ejecutable, y si es una evidencia
# conocida. Con un solo `in {...}` incrustado, una evidencia desconocida —`Test`, `inspeccion` sin
# tilde— salteaba el chequeo en silencio y la guarda informaba verde sobre un registro que debía
# juzgar, apoyada en que otra guarda de la misma comprobación rechazara el enum.
EVIDENCIA_EJECUTABLE = {"test", "build", "inspección"}
EVIDENCIAS = EVIDENCIA_EJECUTABLE | {"manual"}


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:contrato-baseline contract", file=sys.stderr)
        return 2
    try:
        vigente = version_vigente(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        vigente = ""
    filas = [fila for fila in parsear_tabla_pipe(vigente) if len(fila) == 6 and fila[0] != "ID"]
    registros = [linea for linea in vigente.splitlines() if re.match(r"^- `id: ", linea)]
    rc = 0
    cabecera = next((linea for linea in vigente.splitlines() if re.match(r"^\|\s*ID\s*\|", linea)), "")
    if re.search(r"adjudicaci|justificaci|commit|timestamp|observado", cabecera, re.IGNORECASE):
        print("GUARD:ubicacion-baseline un campo del registro está puesto como columna", file=sys.stderr)
        rc = 1
    ids_tabla = [fila[0] for fila in filas]
    ids_reg = []
    for registro in registros:
        match = re.match(r"^- `id: ([^`]*)`", registro)
        ids_reg.append(match.group(1) if match else "")
    if ids_tabla != ids_reg:
        print(
            f"GUARD:baseline-record-parity tabla=[{' '.join(ids_tabla)} ] "
            f"registros=[{' '.join(ids_reg)} ]",
            file=sys.stderr,
        )
        rc = 1
    duplicados = sorted({identificador for identificador in ids_reg if ids_reg.count(identificador) > 1})
    if duplicados:
        print(f"GUARD:baseline-record-parity registro duplicado: {' '.join(duplicados)} ", file=sys.stderr)
        rc = 1
    estados = {fila[0]: fila[5] for fila in filas}
    evidencias = {fila[0]: fila[2] for fila in filas}
    for identificador, registro in zip(ids_reg, registros):
        if not re.search(r"`commit: [0-9a-f]+`", registro):
            print(f"GUARD:adjudicacion-obligatoria {identificador}: sin commit", file=sys.stderr)
            rc = 1
        if not re.search(r"`timestamp: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)`", registro):
            print(f"GUARD:adjudicacion-obligatoria {identificador}: timestamp no ISO-8601", file=sys.stderr)
            rc = 1
        observado = re.search(r"`observado: ([^`]*)`", registro)
        valor_observado = observado.group(1).strip() if observado else ""
        evidencia = evidencias.get(identificador)
        if evidencia not in EVIDENCIAS:
            print(f"GUARD:adjudicacion-obligatoria {identificador}: evidencia fuera del enum: {evidencia!r}",
                  file=sys.stderr)
            rc = 1
        # La forma se exige solo donde el campo se exige. `NOT_APPLICABLE` y `BLOCKED` declaran que no
        # hubo medición aplicable o que no se pudo hacer; pedirle un código de salida a un valor que
        # alguien dejó ahí como nota contradice el texto que dice que ahí el campo no se exige.
        if estados.get(identificador) in {"RED", "GREEN_ALREADY"}:
            if not valor_observado:
                print(f"GUARD:adjudicacion-obligatoria {identificador}: sin observado", file=sys.stderr)
                rc = 1
            elif evidencia in EVIDENCIA_EJECUTABLE and not re.fullmatch(r"exit -?[0-9]+; .+", valor_observado):
                print(f"GUARD:adjudicacion-obligatoria {identificador}: observado sin exit code", file=sys.stderr)
                rc = 1
            elif evidencia == "manual" and re.match(r"exit -?[0-9]+;", valor_observado):
                # Una observación humana no tiene proceso del que leer un código, así que la forma
                # ejecutable acá solo puede venir de copiar el marcador de relleno de la plantilla o
                # la fila de al lado. Sin esta rama, `manual` era el único tipo sin forma exigida —y
                # el más expuesto a escribirse de memoria, que es el defecto que el campo cierra.
                # Se busca la forma ejecutable, no el prefijo `exit `: una observación legítima puede
                # empezar con esa palabra —`exit button remains visible`— y rechazarla castigaría al
                # español y al inglés por igual sin que haya nada que delate una medición fabricada.
                print(f"GUARD:adjudicacion-obligatoria {identificador}: observado de evidencia manual con forma de ejecutable",
                      file=sys.stderr)
                rc = 1
        if estados.get(identificador) == "GREEN_ALREADY" and "`adjudicación: already_satisfied`" not in registro:
            print(
                f"GUARD:adjudicacion-obligatoria {identificador}: GREEN_ALREADY sin adjudicación already_satisfied",
                file=sys.stderr,
            )
            rc = 1
        if estados.get(identificador) == "NOT_APPLICABLE" and not re.search(r"`justificación: [^`]", registro):
            print(f"GUARD:adjudicacion-obligatoria {identificador}: NOT_APPLICABLE sin justificación", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
