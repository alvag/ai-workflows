"""Predicado: el re-baseline corre sobre el commit pre-dispatch en un worktree temporal, conserva
el código de salida y la última línea no vacía de la salida, saneada de caracteres de control y de
los dos separadores del registro y leída con un recorrido acotado en memoria, el árbol activo
queda intacto, el
temporal se remueve y deja de figurar en git worktree list, y cualquier incertidumbre de creación o
limpieza deja la fila en BLOCKED; la pareja 125/CROSS_IMPLEMENT_PROJECTION_BLOCKED también bloquea,
pero un 125 del predicado con proyección canónica conserva su resultado RED."""

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
PROYECCION = re.compile(
    rb"(?:failures=[0-9]+|count=[0-9]+;sha256=[0-9a-f]{64})\n")
PROYECCION_BLOQUEADA = b"CROSS_IMPLEMENT_PROJECTION_BLOCKED\n"
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


def clasificar_proyeccion(salida: Path, codigo: int) -> str:
    """Clasifica solo salidas que pertenecen al transporte de proyección."""
    try:
        # La proyección es un protocolo de bytes: el LF final y la ausencia de bytes adicionales
        # son parte de su forma, por eso no se abre como texto.
        contenido = salida.read_bytes()
    except OSError:
        return "BLOCKED"
    if contenido == PROYECCION_BLOQUEADA and codigo == 125:
        return "BLOCKED"
    lineas = contenido.splitlines(keepends=True)
    parece_proyeccion = any(
        linea.startswith((b"failures=", b"count=", b"CROSS_IMPLEMENT_"))
        for linea in lineas)
    if parece_proyeccion and (not lineas or PROYECCION.fullmatch(lineas[-1]) is None):
        return "BLOCKED"
    return "GREEN_ALREADY" if codigo == 0 else "RED"


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
    registro = ""
    fallo = False
    try:
        # Binary mode preserves the command's combined output without decoding it.
        with open(salida, "wb") as archivo:
            resultado = subprocess.run(
                comando, cwd=worktree, shell=True, stdout=archivo,
                stderr=subprocess.STDOUT, check=False)
        commit_resultado = ejecutar("git", "-C", str(worktree), "rev-parse", "HEAD")
        if commit_resultado.returncode != 0:
            raise OSError("no se pudo leer el commit del worktree")
        commit = commit_resultado.stdout.decode("utf-8").strip()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        estado = clasificar_proyeccion(salida, resultado.returncode)
        obs = ("exit 125; CROSS_IMPLEMENT_PROJECTION_BLOCKED" if estado == "BLOCKED"
               else observable(salida, resultado.returncode))
        registro = (f"id: {fila} · resultado: {estado} · commit: {commit} · "
                    f"timestamp: {timestamp} · observado: {obs}")
    except (OSError, UnicodeError, ValueError, MemoryError):
        fallo = True

    limpieza_ok = True
    try:
        limpieza_ok = ejecutar(
            "git", "worktree", "remove", "--force", str(worktree)).returncode == 0
        limpieza_ok = ejecutar("git", "worktree", "prune").returncode == 0 and limpieza_ok
        listado_resultado = ejecutar("git", "worktree", "list", "--porcelain")
        limpieza_ok = listado_resultado.returncode == 0 and limpieza_ok
        listado = listado_resultado.stdout.decode("utf-8", errors="replace")
        limpieza_ok = str(worktree) not in listado and limpieza_ok
        salida.unlink(missing_ok=True)
    except (OSError, UnicodeError):
        limpieza_ok = False
    if fallo or not limpieza_ok:
        print(f"BLOCKED {fila}: no se pudo ejecutar o limpiar el re-baseline", file=sys.stderr)
        return 1
    print(registro)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
