#!/usr/bin/env python3
"""El predicado de elegibilidad del corpus de la Fase 0.5, ejecutable.

Este comando **implementa** el predicado de AC-4bis; **no lo define**. La definición la fijó Max el
2026-08-12, fuera de este archivo, y dice:

> Un **flujo** es un directorio hijo directo de `.plans/` o de `.plans/archived/`. Es **elegible** si
> y solo si (a) contiene `spec.md`, `plan.md` y `tasks.md`, los tres **archivos regulares y no
> vacíos**, y (b) **no pertenece a la Fase 0.5**.

Que el comando esté versionado acredita **reproducibilidad**, no que implemente el universo
pretendido: un comando que excluyera los flujos incómodos produciría salida, snapshot y manifest
perfectamente concordantes entre sí. Por eso los casos del autotest se derivan de la definición de
arriba y no de correr esto.

Modos:

- `--listar` — emite los flujos elegibles, uno por línea, y el conteo. Exit 0 si el recorrido fue
  íntegro.
- `--congelar` — escribe `scripts/corpus-elegibles.json`, la salida bruta versionada: la
  clasificación completa, elegibles y no elegibles con su motivo.

Códigos de salida: **0** sano, **1** el recorrido no fue íntegro (error de lectura), **2**
invocación inválida.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Callable, NamedTuple

RAIZ = Path(__file__).resolve().parent.parent
DIR_PLANS = RAIZ / ".plans"
RUTA_SNAPSHOT = RAIZ / "scripts" / "corpus-elegibles.json"

ARTEFACTOS = ("spec.md", "plan.md", "tasks.md")

# La Fase 0.5 se enumera **por slugs**, no por un patrón de nombre. Un patrón `dossier-*` fallaría
# cuando la fase archive sus flujos —pasarían a `.plans/archived/` y volverían a satisfacer (a)— y
# también si un flujo futuro ajeno a la fase eligiera ese prefijo. La lista se cierra al congelar y
# se versiona con el snapshot, así que no depende de que alguien la recuerde después.
SLUGS_FASE_05 = (
    "dossier-arnes",
    "dossier-de-task",
    "dossier-diff-de-task",
    "dossier-oraculo",
    "dossier-prompts",
)

# `archived` es el **contenedor** de los flujos archivados, no un flujo. Se nombra acá y no se
# deduce de que le falten los artefactos: si algún día alguien dejara un `spec.md` suelto ahí, la
# deducción lo convertiría en flujo.
CONTENEDORES = ("archived",)

MOTIVO_ELEGIBLE = "elegible"


class ErrorDeRecorrido(Exception):
    """Un artefacto existe pero no se pudo leer. **Aborta**, nunca degrada a «no elegible».

    Degradar sería indistinguible de un flujo incompleto, y un flujo que se cae del corpus por un
    permiso mal puesto se lleva sus ternas sin que nada lo diga.
    """


def _leer_real(ruta: Path) -> bytes:
    return ruta.read_bytes()


class Flujo(NamedTuple):
    slug: str            # identidad del flujo: `<id>` o `archived/<id>`
    directorio: Path


def enumerar_flujos(base: Path) -> list[Flujo]:
    """Los candidatos: hijos directos de `base` y de `base/archived`, en orden estable."""
    flujos: list[Flujo] = []
    for contenedor in (None,) + CONTENEDORES:
        raiz = base if contenedor is None else base / contenedor
        if not raiz.is_dir():
            continue
        for hijo in sorted(raiz.iterdir(), key=lambda p: p.name):
            if not hijo.is_dir() or hijo.is_symlink():
                continue
            if contenedor is None and hijo.name in CONTENEDORES:
                continue
            flujos.append(Flujo(hijo.name if contenedor is None
                                else f"{contenedor}/{hijo.name}", hijo))
    return flujos


def clasificar(flujo: Flujo, leer: Callable[[Path], bytes] = _leer_real) -> str:
    """El motivo por el que el flujo entra o no. `MOTIVO_ELEGIBLE` es el único positivo.

    El orden de las cláusulas es el de la definición: primero (a) los tres artefactos, después (b)
    la fase. Un flujo de la Fase 0.5 que además esté incompleto se reporta por lo que le falta;
    la pertenencia a la fase solo decide sobre los que ya cumplen (a).
    """
    faltan: list[str] = []
    vacios: list[str] = []
    no_regulares: list[str] = []

    for nombre in ARTEFACTOS:
        ruta = flujo.directorio / nombre
        if ruta.is_symlink():
            no_regulares.append(nombre)
            continue
        if not ruta.exists():
            faltan.append(nombre)
            continue
        if not ruta.is_file():
            no_regulares.append(nombre)
            continue
        try:
            contenido = leer(ruta)
        except FileNotFoundError as exc:
            raise ErrorDeRecorrido(
                f"{flujo.slug}/{nombre}: desapareció durante el recorrido ({exc})") from exc
        except OSError as exc:
            raise ErrorDeRecorrido(f"{flujo.slug}/{nombre}: apertura fallida ({exc})") from exc
        try:
            contenido.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ErrorDeRecorrido(
                f"{flujo.slug}/{nombre}: bytes no decodificables como UTF-8 ({exc})") from exc
        if not contenido:
            vacios.append(nombre)

    if no_regulares:
        return "artefacto no regular: " + ", ".join(no_regulares)
    if faltan:
        return f"faltan {len(faltan)} de {len(ARTEFACTOS)}: " + ", ".join(faltan)
    if vacios:
        return "artefacto vacío: " + ", ".join(vacios)
    if flujo.slug.rsplit("/", 1)[-1] in SLUGS_FASE_05:
        return "pertenece a la Fase 0.5"
    return MOTIVO_ELEGIBLE


def snapshot(base: Path = DIR_PLANS,
             leer: Callable[[Path], bytes] = _leer_real) -> dict:
    """La clasificación completa. Sin marca de tiempo: la salida tiene que ser reproducible."""
    elegibles: list[str] = []
    no_elegibles: list[dict] = []
    for flujo in enumerar_flujos(base):
        motivo = clasificar(flujo, leer)
        if motivo == MOTIVO_ELEGIBLE:
            elegibles.append(flujo.slug)
        else:
            no_elegibles.append({"flujo": flujo.slug, "motivo": motivo})
    return {
        "version_snapshot": "1",
        "predicado": (
            "Un flujo es un directorio hijo directo de `.plans/` o de `.plans/archived/`. Es "
            "elegible si y solo si (a) contiene spec.md, plan.md y tasks.md, los tres archivos "
            "regulares y no vacíos, y (b) no pertenece a la Fase 0.5."
        ),
        "artefactos_exigidos": list(ARTEFACTOS),
        "slugs_fase_05": list(SLUGS_FASE_05),
        "elegibles": elegibles,
        "no_elegibles": no_elegibles,
    }


def modo_listar(args: argparse.Namespace) -> int:
    del args
    try:
        datos = snapshot()
    except ErrorDeRecorrido as exc:
        print(f"ABORTA  {exc}", file=sys.stderr)
        print("RESULTADO: FALLA — el recorrido no fue íntegro; no se emite lista parcial",
              file=sys.stderr)
        return 1
    for slug in datos["elegibles"]:
        print(slug)
    print()
    print(f"RESULTADO: OK — {len(datos['elegibles'])} flujos elegibles, "
          f"{len(datos['no_elegibles'])} descartados")
    return 0


def modo_congelar(args: argparse.Namespace) -> int:
    del args
    try:
        datos = snapshot()
    except ErrorDeRecorrido as exc:
        print(f"ABORTA  {exc}", file=sys.stderr)
        return 1
    RUTA_SNAPSHOT.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    print(f"RESULTADO: OK — {RUTA_SNAPSHOT.relative_to(RAIZ)} con "
          f"{len(datos['elegibles'])} elegibles")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="oraculo-elegibilidad.py",
        description="Implementa el predicado de elegibilidad de AC-4bis.")
    parser.add_argument("--listar", action="store_true",
                        help="emite los flujos elegibles, uno por línea")
    parser.add_argument("--congelar", action="store_true",
                        help="escribe scripts/corpus-elegibles.json")
    args = parser.parse_args(argv)

    if args.listar == args.congelar:
        print("Invocación inválida: exactamente uno de --listar, --congelar.", file=sys.stderr)
        return 2
    return modo_listar(args) if args.listar else modo_congelar(args)


if __name__ == "__main__":
    sys.exit(main())
