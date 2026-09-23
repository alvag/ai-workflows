"""Predicado: todo requisito en alcance tiene al menos una fila, y toda fila referencia un requisito
en alcance. Las dos direcciones se reportan por separado.

Recibe el contrato y la lista de requisitos en alcance, con un identificador por línea: la forma la
declara `contrato-verificacion.md` → «Cobertura bidireccional». Las líneas en blanco se ignoran y un
BOM inicial se tolera; cualquier otra línea que no sea un identificador detiene la guarda antes de
comparar. De cada fila de la versión vigente cuenta la lista de identificadores, separados por comas,
con que abre su celda `Requisito`.

Qué detecta: un requisito de la lista que ninguna fila cita, una fila que cita un identificador que
la lista no tiene, y una fila cuya celda `Requisito` no abre con un identificador.

Qué NO detecta: que la lista sea el alcance correcto —confía en quien la escribió, así que un
requisito que falta en la lista y en el contrato a la vez da verde—; que una fila discrimine lo que
su requisito afirma, que es la pertinencia y sigue siendo manual; ni una cita que no esté al comienzo
de la celda o que use otro separador que la coma: la lista termina en lo primero que no sea una coma
seguida de otro identificador, y lo que viene después no se lee.

Campos: clase **veredicto**. `0` la cobertura cierra; `1` no cierra, con una línea
`GUARD:cobertura-bidireccional` por cada dirección que falla y otra para las filas sin identificador.
Dirección **admite-de-mas y rechaza-de-mas**. Admite de más porque su verde solo autoriza a afirmar
que la lista recibida y las citas de la versión vigente coinciden, no que la lista sea la correcta ni
que las filas discriminen. Rechaza de más porque una fila que sí prueba su requisito pero lo cita en
otra forma —entre backticks, con otro separador, detrás de una palabra— sale como fila sin
identificador o sin requisito en alcance.

Fallo de ejecución, aparte del resultado: `2` con una línea `USO:contrato-cobertura`. Sale así con
una aridad distinta de dos, un archivo que no se lee como UTF-8, una línea de la lista que no es un
identificador o una lista sin ninguno. En esos casos la cobertura no se evaluó: un `2` no es un
rechazo del contrato ni se puede leer como uno."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple

from _tabla import parsear_tabla_pipe


# Empieza y termina con letra o dígito; en el medio admite `.`, `_` y `-` (`AC-3`, `R-2`, `A`).
ID_PATTERN = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
ID_LIST = re.compile(rf"{ID_PATTERN}(?:\s*,\s*{ID_PATTERN})*")
LINE_PREVIEW = 60


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


def read_requirements(text: str) -> Tuple[Optional[Set[str]], Optional[str]]:
    """Devuelve el alcance, o el diagnóstico que impide evaluarlo; nunca los dos.

    Se valida entero antes de comparar: una spec pasada en lugar de la lista tiene que detenerse en
    su primera línea de prosa, no enumerarse como requisitos faltantes."""
    scope: Set[str] = set()
    for number, line in enumerate(text.splitlines(), 1):
        token = line.strip()
        if not token:
            continue
        if not re.fullmatch(ID_PATTERN, token):
            return None, (f"USO:contrato-cobertura requirements línea {number} no es un "
                          f"identificador: {token[:LINE_PREVIEW]}")
        scope.add(token)
    if not scope:
        return None, "USO:contrato-cobertura requirements sin ningún identificador"
    return scope, None


def cited_ids(cell: str) -> List[str]:
    """Los identificadores con que abre la celda `Requisito`; vacío si no abre con ninguno."""
    match = ID_LIST.match(cell)
    return re.findall(ID_PATTERN, match.group(0)) if match else []


def main() -> int:
    if len(sys.argv) != 3:
        print("USO:contrato-cobertura contract requirements", file=sys.stderr)
        return 2
    # Cada argumento se lee por separado: vaciar los dos ante un error dejaba dos conjuntos sin
    # diferencias, y una invocación rota salía 0 como una cobertura perfecta.
    try:
        contrato = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        print(f"USO:contrato-cobertura contract ilegible: {error}", file=sys.stderr)
        return 2
    try:
        requirements_text = Path(sys.argv[2]).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        print(f"USO:contrato-cobertura requirements ilegible: {error}", file=sys.stderr)
        return 2
    alcance, diagnostic = read_requirements(requirements_text)
    if alcance is None:
        print(diagnostic, file=sys.stderr)
        return 2
    citados: Set[str] = set()
    rows_without_id: List[str] = []
    for fila in parsear_tabla_pipe(version_vigente(contrato)):
        if len(fila) < 2 or fila[0] == "ID":
            continue
        ids = cited_ids(fila[1])
        if ids:
            citados.update(ids)
        else:
            rows_without_id.append(fila[0])
    rc = 0
    faltan = sorted(alcance - citados)
    sobran = sorted(citados - alcance)
    if faltan:
        print(f"GUARD:cobertura-bidireccional requisito en alcance sin fila: {' '.join(faltan)} ", file=sys.stderr)
        rc = 1
    if sobran:
        print(f"GUARD:cobertura-bidireccional fila sin requisito en alcance: {' '.join(sobran)} ", file=sys.stderr)
        rc = 1
    if rows_without_id:
        print("GUARD:cobertura-bidireccional fila sin identificador de requisito: "
              + " ".join(rows_without_id), file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
