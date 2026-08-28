"""Predicado: el re-baseline corre sobre el commit pre-dispatch en un worktree temporal, conserva
el código de salida y la última línea observable saneada, el árbol activo queda intacto, el temporal
se remueve y deja de figurar en git worktree list, y cualquier incertidumbre de creación o limpieza
deja la fila en BLOCKED."""

from __future__ import annotations

import os
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


def ejecutar(*args: str, cwd: Path = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def observable(salida: Path, codigo: int) -> str:
    texto = salida.read_bytes().decode("utf-8", errors="replace")
    ultima = next((linea for linea in reversed(texto.splitlines()) if linea), "")
    saneada = "".join(" " if unicodedata.category(caracter) == "Cc" else caracter for caracter in ultima)
    saneada = " ".join(saneada.replace("`", "").split())[:200] or "sin salida"
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
    print(f"id: {fila} · resultado: {estado} · commit: {commit} · timestamp: {timestamp} · observado: {observable(salida, resultado.returncode)}")
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
