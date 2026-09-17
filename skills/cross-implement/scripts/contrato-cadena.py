"""Predicado: valida la cadena de hashes y rechaza cuatro formas contractuales fuera de versiones.

FRONTERA DE PRUEBA — clase: veredicto; dirección: admite-de-más.
Detecta versiones no consecutivas, hashes rotos y cabeceras, registros, encabezados de baseline o
hashes canónicos fuera de un bloque de versión. NO detecta una fila de datos suelta sin su cabecera,
contenido huérfano dentro de una cerca ni el punto ciego de gate-congelado.py y gate-blocked.py, que
replican la frontera y no consumen este predicado. Campos: línea física y forma detectada; versión,
hash declarado, recalculado y previo para la cadena.

Fallo de ejecución, distinto del resultado: 2 ante una invocación mal formada, con
`USO:contrato-cadena contract` en stderr, y es el único que se distingue. Un contrato inexistente,
ilegible o no decodificable NO llega a 2: se lee como texto vacío y el modo sale 0, así que ese
verde no acredita que el archivo exista ni que se haya leído, solo que lo leído no violó el
predicado. Quien invoque comprueba la existencia por su cuenta; un baseline apoyado en ese 0 puede
haberse ganado por ausencia."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import List, Tuple


def _recorrer(texto: str) -> tuple[list[tuple[int, list[str]]], set[int]]:
    lineas = texto.splitlines()
    halladas: List[Tuple[int, List[str]]] = []
    cubiertas: set[int] = set()
    cerca = False
    for indice, linea in enumerate(lineas):
        if linea.startswith("```"):
            cerca = not cerca
        match = None if cerca else re.fullmatch(r"(#+) v(\d+)", linea)
        if not match:
            continue
        nivel = len(match.group(1))
        bloque = [linea]
        interna = False
        for siguiente in lineas[indice + 1 :]:
            if siguiente.startswith("```"):
                interna = not interna
            encabezado = re.match(r"^(#+) ", siguiente) if not interna else None
            if encabezado and len(encabezado.group(1)) <= nivel:
                break
            bloque.append(siguiente)
        halladas.append((int(match.group(2)), bloque))
        cubiertas.update(range(indice, indice + len(bloque)))
    return halladas, cubiertas


def versiones(texto: str) -> List[Tuple[int, List[str]]]:
    return sorted(_recorrer(texto)[0])


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:contrato-cadena contract", file=sys.stderr)
        return 2
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        texto = ""
    halladas, cubiertas = _recorrer(texto)
    halladas = sorted(halladas)
    rc = 0
    esperado = 1
    for numero, _ in halladas:
        if numero != esperado:
            print(f"GUARD:versiones-consecutivas se esperaba v{esperado} y vino v{numero}", file=sys.stderr)
            rc = 1
        esperado = numero + 1
    anterior = ""
    for numero, bloque in halladas:
        original = "\n".join(bloque)
        canon = [re.sub(r"`hash: [^`]*`", "`hash: `", linea).rstrip() for linea in bloque]
        while canon and canon[-1] == "":
            canon.pop()
        calculado = hashlib.sha256(("\n".join(canon) + "\n").encode("utf-8")).hexdigest()
        declarado_match = re.search(r"`hash: ([0-9a-f]*)`", original)
        previo_match = re.search(r"`hash_previo: ?([0-9a-f]*)`", original)
        declarado = declarado_match.group(1) if declarado_match else ""
        previo = previo_match.group(1) if previo_match else ""
        if declarado != calculado:
            print(
                f"GUARD:cadena-hash v{numero}: hash declarado {declarado or 'vacío'}, "
                f"recalculado {calculado}",
                file=sys.stderr,
            )
            rc = 1
        if previo != anterior:
            print(
                f"GUARD:cadena-hash v{numero}: hash_previo {previo or 'vacío'}, "
                f"se esperaba {anterior or 'vacío'}",
                file=sys.stderr,
            )
            rc = 1
        anterior = calculado
    cabecera = "| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |"
    hashes = re.compile(
        r"`hash: [0-9a-f]{64}`|`hash_previo:(?: [0-9a-f]{64})?`")
    cerca = False
    for indice, linea in enumerate(texto.splitlines()):
        if linea.startswith("```"):
            cerca = not cerca
        if indice in cubiertas or cerca:
            continue
        formas = []
        if linea.strip() == cabecera:
            formas.append("cabecera")
        if linea.startswith("- `id: "):
            formas.append("registro")
        if re.fullmatch(r"#{1,6} Baseline de v\d+", linea):
            formas.append("encabezado-baseline")
        if hashes.search(linea):
            formas.append("hashes")
        for forma in formas:
            print(
                f"GUARD:contrato-fuera-de-version línea {indice + 1}: {forma}",
                file=sys.stderr,
            )
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
