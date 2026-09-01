"""Predicado: el re-baseline corre sobre el commit pre-dispatch en un worktree temporal, conserva
el código de salida y la última línea no vacía de la salida, saneada de caracteres de control y de
los dos separadores del registro y leída con un recorrido acotado en memoria, el árbol activo
queda intacto, el
temporal se remueve y deja de figurar en git worktree list, y cualquier incertidumbre de creación o
limpieza deja la fila en BLOCKED."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


def ejecutar(*args: str, cwd: Path = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


# La salida la escribe un comando arbitrario del contrato y puede pesar cientos de MB; de ella se
# consume UNA línea. Se recorre hacia atrás de a bloques para acotar el pico de memoria y, con él,
# la probabilidad de que esta función levante una excepción entre la ejecución y la limpieza del
# worktree. El bloque acota cuánto se lee por vez, NO hasta dónde se busca: una cola de tamaño fijo
# acotaba las dos cosas a la vez y devolvía `sin salida` cuando la última línea real quedaba fuera
# de ella —medido, con una línea seguida de 80 KiB de líneas en blanco—, que es justo el veredicto
# indistinguible de no haber medido que este campo existe para impedir. Lo que sigue sin acotar es
# una línea única gigantesca: hay que recorrerla entera porque de ella se conserva el comienzo, y
# ese caso lo cubre el `except` de quien llama, que degrada sin dejar el worktree sin limpiar.
BLOQUE_BYTES = 65536
# Los dos caracteres que el registro usa como estructura: la comilla de código delimita el campo y
# el punto medio separa los campos entre sí. Si sobreviven dentro del valor, un consumidor que
# parsee la línea obtiene más campos que los declarados o corta el campo antes de tiempo.
ESTRUCTURA = {"`": "", "·": "-"}
# Qué es una línea lo define `str.splitlines()`, que corta en bastante más que `\n` —`\r` suelto, que
# es lo que emite todo indicador de progreso, más `\v`, `\f`, los tres separadores de C1 y NEL, LS y
# PS—. El recorrido trabaja sobre bytes, así que el corte se busca con las codificaciones UTF-8 de
# esos separadores, DERIVADAS de Python y no transcritas: una lista escrita a mano se desincroniza
# en silencio, y su modo de fallo es perder una línea real y afirmar `sin salida`.
CORTE = re.compile(b"|".join(
    re.escape(chr(punto).encode("utf-8"))
    for punto in sorted(list(range(0x20)) + [0x85, 0x2028, 0x2029],
                        key=lambda p: -len(chr(p).encode("utf-8")))
    if len(f"a{chr(punto)}b".splitlines()) > 1))


def ultima_linea_no_vacia(archivo) -> str:
    """Recorre el archivo hacia atrás de a bloques y devuelve la última línea que no sea solo blancos."""
    archivo.seek(0, os.SEEK_END)
    posicion, resto = archivo.tell(), b""
    while posicion > 0:
        leer = min(BLOQUE_BYTES, posicion)
        posicion -= leer
        archivo.seek(posicion)
        cola = archivo.read(leer) + resto
        if posicion:
            # La primera línea del buffer puede continuar hacia atrás, así que no se juzga todavía;
            # con el archivo agotado (`posicion == 0`) ya está completa y entra entera.
            corte = CORTE.search(cola)
            if corte is None:
                resto = cola
                continue
            cuerpo, resto = cola[corte.end():], cola[:corte.start()]
        else:
            cuerpo = cola
        # Se decodifica para juzgar con `str`: `bytes.strip()` solo conoce el blanco ASCII, así que
        # una línea de solo NBSP contaría como contenido y taparía a la última línea real.
        for linea in reversed(cuerpo.decode("utf-8", errors="replace").splitlines()):
            if linea.strip():
                return linea
    return ""


def observable(salida: Path, codigo: int) -> str:
    # Una línea de solo blancos no cuenta como última: el saneado la dejaría vacía y el registro
    # afirmaría `sin salida` sobre un comando que sí produjo salida — indistinguible de no haber
    # medido, que es justo lo que este campo existe para impedir.
    # Modo binario porque la salida del comando son bytes arbitrarios y el reemplazo de los que no
    # decodifican lo hace esta función, no el lector: abrir en texto delegaría esa decisión al
    # encoding del entorno y haría que el mismo comando produjera observables distintos por máquina.
    with open(salida, "rb") as archivo:
        ultima = ultima_linea_no_vacia(archivo)
    # `Cf` va junto a `Cc` y no por simetría: ahí vive U+202E, que reordena visualmente lo que sigue
    # dentro del registro. En un campo cuya única función es que un humano lea qué se observó, un
    # carácter que altera lo que se lee ataca la propiedad entera.
    saneada = "".join(" " if unicodedata.category(caracter) in {"Cc", "Cf"} else caracter
                      for caracter in ultima)
    for caracter, reemplazo in ESTRUCTURA.items():
        saneada = saneada.replace(caracter, reemplazo)
    saneada = " ".join(saneada.split())[:200] or "sin salida"
    return f"exit {codigo}; {saneada}"


def main() -> int:
    if len(sys.argv) != 4:
        print("USO:rebaseline-worktree pre_dispatch_sha check_id command", file=sys.stderr)
        return 2
    sha_pre, fila, comando = sys.argv[1:]
    if ejecutar("git", "cat-file", "-e", f"{sha_pre}^{{commit}}").returncode != 0:
        print(f"BLOCKED {fila}: sha pre-dispatch inválido", file=sys.stderr)
        return 1
    raiz_res = ejecutar("git", "rev-parse", "--show-toplevel")
    if raiz_res.returncode != 0:
        print(f"BLOCKED {fila}: no se pudo crear el worktree", file=sys.stderr)
        return 1
    raiz = Path(raiz_res.stdout.decode("utf-8").strip())
    worktree = raiz.parent / f".rebaseline-wt-{os.getpid()}"
    salida = Path(f"{worktree}.out")
    if ejecutar("git", "worktree", "add", "--detach", str(worktree), sha_pre).returncode != 0:
        print(f"BLOCKED {fila}: no se pudo crear el worktree", file=sys.stderr)
        return 1
    # Binary mode preserves the command's combined output without decoding it.
    with open(salida, "wb") as archivo:
        resultado = subprocess.run(comando, cwd=worktree, shell=True, stdout=archivo, stderr=subprocess.STDOUT, check=False)
    commit = ejecutar("git", "-C", str(worktree), "rev-parse", "HEAD").stdout.decode("utf-8").strip()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    estado = "GREEN_ALREADY" if resultado.returncode == 0 else "RED"
    # La limpieza va en `finally` porque calcular el observable es la primera operación de esta
    # función que puede fallar: antes de que existiera, `print` no tenía modo de fallo. Sin esto,
    # una excepción acá deja el worktree registrado y la fila sin el `BLOCKED` que el predicado
    # promete ante cualquier incertidumbre de limpieza.
    try:
        obs = observable(salida, resultado.returncode)
    except (OSError, ValueError, MemoryError) as error:
        obs = f"exit {resultado.returncode}; sin salida legible ({type(error).__name__})"
    try:
        print(f"id: {fila} · resultado: {estado} · commit: {commit} · timestamp: {timestamp} · observado: {obs}")
    finally:
        ejecutar("git", "worktree", "remove", "--force", str(worktree))
        ejecutar("git", "worktree", "prune")
    listado = ejecutar("git", "worktree", "list", "--porcelain").stdout.decode("utf-8", errors="replace")
    if str(worktree) in listado:
        print(f"BLOCKED {fila}: el worktree sigue registrado en git worktree list", file=sys.stderr)
        return 1
    salida.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
