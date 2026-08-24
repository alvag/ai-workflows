"""Predicado: las versiones son consecutivas desde v1, y para cada una hash_previo es el hash de la
anterior (vacío en v1) y hash es el SHA-256 de sus bytes canónicos."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import List, Tuple


def versiones(texto: str) -> List[Tuple[int, List[str]]]:
    lineas = texto.splitlines()
    halladas: List[Tuple[int, List[str]]] = []
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
    return sorted(halladas)


def main() -> int:
    if len(sys.argv) != 2:
        print("USO:contrato-cadena contract", file=sys.stderr)
        return 2
    try:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        texto = ""
    halladas = versiones(texto)
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
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
