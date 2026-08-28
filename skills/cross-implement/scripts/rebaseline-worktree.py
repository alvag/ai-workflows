"""Predicado: el re-baseline corre sobre el commit pre-dispatch en un worktree temporal, conserva
el código de salida y la última línea no vacía de la salida, saneada de caracteres de control y de
los dos separadores del registro y leída de una cola acotada, el árbol activo queda intacto, el
temporal se remueve y deja de figurar en git worktree list, y cualquier incertidumbre de creación o
limpieza deja la fila en BLOCKED."""

from __future__ import annotations

import os
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


def ejecutar(*args: str, cwd: Path = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


# La salida la escribe un comando arbitrario del contrato y puede pesar cientos de MB; de ella se
# consume UNA línea. Leer la cola acota el pico de memoria y, con él, la probabilidad de que esta
# función levante una excepción entre la ejecución y la limpieza del worktree.
COLA_BYTES = 65536
# Los dos caracteres que el registro usa como estructura: la comilla de código delimita el campo y
# el punto medio separa los campos entre sí. Si sobreviven dentro del valor, un consumidor que
# parsee la línea obtiene más campos que los declarados o corta el campo antes de tiempo.
ESTRUCTURA = {"`": "", "·": "-"}


def observable(salida: Path, codigo: int) -> str:
    # Modo binario porque la salida del comando son bytes arbitrarios y el reemplazo de los que no
    # decodifican lo hace esta función, no el lector: abrir en texto delegaría esa decisión al
    # encoding del entorno y haría que el mismo comando produjera observables distintos por máquina.
    with open(salida, "rb") as archivo:
        archivo.seek(0, os.SEEK_END)
        archivo.seek(max(0, archivo.tell() - COLA_BYTES))
        texto = archivo.read().decode("utf-8", errors="replace")
    # `if linea` acepta una línea de solo espacios: el saneado la deja vacía y el registro afirmaría
    # `sin salida` sobre un comando que sí produjo salida — indistinguible de no haber medido, que es
    # justo lo que este campo existe para impedir.
    ultima = next((linea for linea in reversed(texto.splitlines()) if linea.strip()), "")
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
