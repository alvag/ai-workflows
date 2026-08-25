"""Predicado: el marcador y la constancia canónica acreditan el congelamiento; solo el preestado
propio de la complejidad se promueve, y tasks-ready se acepta como reintento sin escritura."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


def fallo(mensaje: str, codigo: int) -> int:
    print(f"GUARD:promocion-tasks-ready {mensaje}", file=sys.stderr)
    return codigo


def leer_header(texto: str) -> Tuple[bool, Dict[str, List[str]]]:
    lineas = texto.splitlines()
    if not lineas or lineas[0].rstrip("\r") != "---":
        return False, {}
    campos: Dict[str, List[str]] = {"status": [], "complexity": [], "contract_procedure": []}
    for linea in lineas[1:]:
        linea = linea.rstrip("\r")
        if linea == "---":
            return True, campos
        for clave in campos:
            match = re.match(rf"^{clave}:\s*(.*?)\s*$", linea)
            if match:
                campos[clave].append(match.group(1))
                break
    return False, campos


def timestamp_valido(valor: str) -> bool:
    match = re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})", valor)
    if not match:
        return False
    zona = match.group(1)
    if zona != "Z":
        horas, minutos = map(int, zona[1:].split(":"))
        if horas > 14 or minutos > 59 or (horas == 14 and minutos != 0):
            return False
    try:
        datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def clasificar_constancia(texto: str) -> str:
    paso = actor = todos = timestamp_invalido = False
    prefijo = "- `paso: congelar` · `actor: conductor` · `timestamp: "
    for linea in texto.splitlines():
        tiene_paso = "`paso: congelar`" in linea
        tiene_actor = "`actor: conductor`" in linea
        tiene_timestamp = "`timestamp: " in linea
        paso = paso or tiene_paso
        actor = actor or (tiene_paso and tiene_actor)
        todos = todos or (tiene_paso and tiene_actor and tiene_timestamp)
        if linea.startswith(prefijo) and linea.endswith("`"):
            if timestamp_valido(linea[len(prefijo) : -1]):
                return "ok"
            timestamp_invalido = True
    if not paso:
        return "paso"
    if not actor:
        return "actor"
    if not todos or timestamp_invalido:
        return "timestamp"
    return "formato/anclaje"


def main() -> int:
    if len(sys.argv) != 3:
        print("USO:promocion-tasks-ready plan log", file=sys.stderr)
        return 2
    plan_arg, log_arg = sys.argv[1:]
    for valor, nombre, etiqueta in ((plan_arg, "plan", "plan"), (log_arg, "bitacora", "bitácora")):
        if not valor:
            return fallo(f"la entrada {nombre} no fue declarada", 2)
        ruta = Path(valor)
        if not ruta.is_file():
            return fallo(f"el {etiqueta} no existe: {valor}", 2)
        if not os.access(ruta, os.R_OK):
            return fallo(f"el {etiqueta} no es legible: {valor}", 2)
    try:
        # newline="" preserves the plan's original LF/CRLF representation.
        with open(plan_arg, encoding="utf-8", newline="") as archivo:
            plan = archivo.read()
        with open(log_arg, encoding="utf-8", newline="") as archivo:
            bitacora = archivo.read()
    except (OSError, UnicodeError):
        return fallo("el frontmatter del plan no se pudo leer", 2)

    delimitado, campos = leer_header(plan)
    if not delimitado:
        return fallo("el frontmatter del plan está mal delimitado", 2)
    status = campos["status"][0] if campos["status"] else ""
    complexity = campos["complexity"][0] if campos["complexity"] else ""
    marker = campos["contract_procedure"][0] if campos["contract_procedure"] else ""
    if not campos["status"]:
        return fallo("falta la clave status en el frontmatter", 2)
    if status not in {"planned", "plan-approved", "tasks-ready", "implementing", "verified", "committed", "pushed", "pr-open", "done"}:
        return fallo(f'status tiene un valor no soportado: "{status}"', 2)
    if not campos["complexity"]:
        return fallo("falta la clave complexity en el frontmatter", 2)
    if complexity not in {"trivial", "normal", "complex"}:
        return fallo(f'complexity tiene un valor no soportado: "{complexity}"', 2)
    if len(campos["status"]) != 1:
        return fallo("la clave status está duplicada", 2)
    if len(campos["complexity"]) != 1:
        return fallo("la clave complexity está duplicada", 2)
    if len(campos["contract_procedure"]) > 1:
        return fallo("la clave contract_procedure está duplicada", 2)
    if len(campos["contract_procedure"]) != 1:
        return fallo("falta el marcador contract_procedure", 1)
    if marker != "measured-v1":
        return fallo(f'contract_procedure tiene un valor no soportado: "{marker}"', 1)

    constancia = clasificar_constancia(bitacora)
    if constancia != "ok":
        return fallo(f"la constancia canónica falla en {constancia}", 1)
    esperado = "plan-approved" if complexity == "complex" else "planned"
    if status == "tasks-ready":
        return 0
    if status != esperado:
        return fallo(f'status "{status}" no permite promover; se esperaba "{esperado}"', 1)

    lineas = plan.splitlines(keepends=True)
    dentro = False
    cambiado = False
    salida: List[str] = []
    for indice, linea in enumerate(lineas):
        contenido = linea.rstrip("\r\n")
        fin = linea[len(contenido) :]
        if indice == 0 and contenido == "---":
            dentro = True
        elif dentro and contenido == "---":
            dentro = False
        elif dentro and not cambiado and re.match(r"^status:\s*", contenido):
            contenido = "status: tasks-ready"
            cambiado = True
        salida.append(contenido + fin)
    if not cambiado:
        return fallo("falló la escritura del temporal hermano del plan", 2)

    ruta = Path(plan_arg)
    fd = -1
    temporal = ""
    try:
        fd, temporal = tempfile.mkstemp(prefix=f".{ruta.name}.promocion.", dir=str(ruta.parent))
        os.close(fd)
        fd = -1
    except OSError:
        if fd >= 0:
            os.close(fd)
        if temporal:
            Path(temporal).unlink(missing_ok=True)
        return fallo("falló la creación del temporal hermano del plan", 2)
    try:
        with open(temporal, "w", encoding="utf-8", newline="") as archivo:
            archivo.write("".join(salida))
    except OSError:
        Path(temporal).unlink(missing_ok=True)
        return fallo("falló la escritura del temporal hermano del plan", 2)
    candidato = "".join(salida)
    delimitado, nuevos = leer_header(candidato)
    consistente = (
        delimitado
        and nuevos["status"] == ["tasks-ready"]
        and nuevos["complexity"] == [complexity]
        and nuevos["contract_procedure"] == ["measured-v1"]
    )
    if not consistente:
        Path(temporal).unlink(missing_ok=True)
        return fallo("falló la validación del candidato: promoción o contrato inconsistente", 2)
    try:
        os.replace(temporal, ruta)
    except OSError:
        Path(temporal).unlink(missing_ok=True)
        return fallo("falló el reemplazo atómico del plan", 2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
