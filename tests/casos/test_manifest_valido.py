"""Regresión durable de las formas del manifest."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional, Tuple


RAIZ = Path(__file__).resolve().parents[2]
PREDICADO = RAIZ / "skills" / "cross-review" / "scripts" / "manifest-valido.py"
GRUPO = "manifest-valido-v1"
Caso = Tuple[str, str, Callable[[Optional[object]], None]]
DESPACHO = {
    "attempt": 1,
    "at": "2026-08-02T11:45:07Z",
    "role": "explore",
    "family": "codex",
    "requested": {"model": "heredado", "effort": "heredado"},
    "resolved": {"model": "heredado", "effort": "heredado"},
    "origin": {"model": 4, "effort": 4},
    "materialized": {"model": None, "effort": None},
    "sent": {"model": "no determinado", "effort": "no determinado"},
    "outcome": "completed",
    "retry_of": None,
}


def _run_manifest(dispatches: list[object]) -> dict[str, object]:
    return {
        "record_type": "run-manifest/1",
        "run_id": "sddhotfix-846f22f0",
        "skill": "co-explore",
        "mode": "explore",
        "started_at": "2026-09-09T17:07:35Z",
        "duration_s": 1610,
        "families": ["codex", "claude"],
        "transport": "cli-exec",
        "outcome": "completed",
        "degradation": "branch-3",
        "selection": "full",
        "dispatches": dispatches,
    }


def _dispatch_log(mode: str = "apply", dispatches: Optional[list[object]] = None,
                  **extra: object) -> dict[str, object]:
    return {
        "record_type": "dispatch-log/1",
        "skill": "sdd-pr-feedback",
        "mode": mode,
        "run_id": "3f10c4ab",
        "started_at": "2026-08-02T11:45:07Z",
        "dispatches": [DESPACHO] if dispatches is None else dispatches,
        **extra,
    }


def _resultado(texto: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as directorio:
        entrada = Path(directorio) / "manifest.json"
        entrada.write_text(texto, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(PREDICADO), str(entrada)], capture_output=True,
            text=True, encoding="utf-8", check=False)


def _afirmar(texto: str, esperado: int) -> None:
    resultado = _resultado(texto)
    assert resultado.returncode == esperado, (
        f"se esperaba {esperado}, vino {resultado.returncode}: "
        f"{(resultado.stdout + resultado.stderr).strip()}")


def _json(objeto: dict[str, object]) -> str:
    return json.dumps(objeto, ensure_ascii=False, indent=2) + "\n"


def test_dos_formas_y_conjuntos(_ctx: Optional[object] = None) -> None:
    """Las dos formas admiten exactamente sus claves raíz: ni de menos ni de más."""
    _afirmar(_json(_run_manifest([DESPACHO])), 0)
    _afirmar(_json(_dispatch_log()), 0)
    _afirmar(_json({**_run_manifest([DESPACHO]), "clave_inventada": 1}), 1)


def test_outcome_anidado_no_duplica_la_raiz(_ctx: Optional[object] = None) -> None:
    """Varias entradas repiten `outcome` sin que eso duplique el de la raíz."""
    # Tres entradas dejan cuatro `outcome` en el texto contando el de la raíz: es la forma del
    # defecto original, que contaba las claves sobre el texto plano en vez de por nivel. Con una
    # sola entrada la aserción sería la misma que la de `dos-formas` y el caso no podría fallar solo.
    entradas = [{**DESPACHO, "attempt": numero} for numero in (1, 2, 3)]
    _afirmar(_json(_run_manifest(entradas)), 0)


def test_duplicado_real_en_la_raiz(_ctx: Optional[object] = None) -> None:
    """Un outcome repetido en la raíz se rechaza.

    Fija comportamiento y no discrimina: el conteo global del predicado viejo ya rechazaba este
    archivo, así que el caso pasa en las dos versiones. Está para que el arreglo no se pase de
    largo y deje de ver el duplicado que sí importa.
    """
    texto = _json(_run_manifest([DESPACHO]))
    texto = texto.replace(
        '  "outcome": "completed",\n  "degradation"',
        '  "outcome": "completed",\n  "outcome": "REVISE",\n  "degradation"', 1)
    _afirmar(texto, 1)


def test_cardinalidad_asimetrica_de_dispatches(_ctx: Optional[object] = None) -> None:
    """run-manifest admite vacío; dispatch-log exige una entrada."""
    _afirmar(_json(_run_manifest([])), 0)
    _afirmar(_json(_dispatch_log(dispatches=[])), 1)


def test_quinto_productor(_ctx: Optional[object] = None) -> None:
    """La fila del quinto productor existe, y su modo es el único que le sirve."""
    # El positivo va con una carga distinta de la de `dos-formas`: si repitiera la de aquel caso no
    # ejercería nada propio, y si se quitara, este caso dejaría de distinguir el predicado anterior
    # —que rechazaba todo dispatch-log— del que declara la fila.
    _afirmar(_json(_dispatch_log(dispatches=[{**DESPACHO, "role": "review"}])), 0)
    _afirmar(_json(_dispatch_log(mode="modo-que-no-existe")), 1)


def test_prohibida_en_dispatch_log(_ctx: Optional[object] = None) -> None:
    """Un campo de telemetría en la raíz de dispatch-log/1 se rechaza nombrándolo."""
    resultado = _resultado(_json(_dispatch_log(duration_s=412)))
    assert resultado.returncode == 1, "una clave prohibida tiene que rechazar"
    # El diagnóstico exacto, no solo el nombre del campo: con el conjunto `prohibidas` vacío el
    # campo cae igual en "clave raíz desconocida", así que una aserción por nombre pasa en las dos
    # ramas y el caso no discrimina lo que dice discriminar.
    assert 'campo "duration_s" no corresponde a dispatch-log/1' in resultado.stderr, resultado.stderr


def test_entrada_de_despacho_incompleta(_ctx: Optional[object] = None) -> None:
    """A una entrada sin una de sus once claves se la nombra por índice y clave."""
    incompleta = {k: v for k, v in DESPACHO.items() if k != "at"}
    resultado = _resultado(_json(_dispatch_log(dispatches=[incompleta])))
    assert resultado.returncode == 1, "una entrada incompleta tiene que rechazar"
    assert 'entrada 1 sin la clave "at"' in resultado.stderr, resultado.stderr


def _sin_forma() -> dict[str, object]:
    """Un registro anterior al contrato: sin el discriminador y sin dos de las claves comunes."""
    return {k: v for k, v in _run_manifest([DESPACHO]).items()
            if k not in {"record_type", "run_id", "dispatches"}}


def test_sin_forma_exige_las_claves_comunes(_ctx: Optional[object] = None) -> None:
    """Sin `record_type` se siguen exigiendo las claves que las dos formas comparten."""
    resultado = _resultado(_json(_sin_forma()))
    assert resultado.returncode == 1, "un archivo sin forma reconocida tiene que rechazar"
    # Se afirma que los NOMBRA, no cuántos son: sin exigir las comunes sale un solo diagnóstico, y
    # un conteo no distingue "falta el discriminador" de "faltan además estas otras".
    for campo in ("run_id", "dispatches"):
        assert 'falta el campo "{0}"'.format(campo) in resultado.stderr, resultado.stderr


def test_sin_forma_no_repite_el_discriminador(_ctx: Optional[object] = None) -> None:
    """El `record_type` ausente se nombra una vez, no una por cada sede que lo mira."""
    salida = _resultado(_json(_sin_forma())).stderr
    # Ni el veredicto ni un conteo total sirven acá: repetir este diagnóstico no cambia qué archivos
    # pasan ni cuántos, solo cuántas veces se nombra el mismo problema. Solo lo ve el texto.
    assert salida.count('falta el campo "record_type"') == 1, salida


CASOS: list[Caso] = [
    ("manifest-valido:dos-formas", GRUPO, test_dos_formas_y_conjuntos),
    ("manifest-valido:outcome-anidado", GRUPO, test_outcome_anidado_no_duplica_la_raiz),
    ("manifest-valido:duplicado-raiz", GRUPO, test_duplicado_real_en_la_raiz),
    ("manifest-valido:cardinalidad", GRUPO, test_cardinalidad_asimetrica_de_dispatches),
    ("manifest-valido:quinto-productor", GRUPO, test_quinto_productor),
    ("manifest-valido:prohibida-dispatch-log", GRUPO, test_prohibida_en_dispatch_log),
    ("manifest-valido:entrada-incompleta", GRUPO, test_entrada_de_despacho_incompleta),
    ("manifest-valido:sin-forma-claves-comunes", GRUPO, test_sin_forma_exige_las_claves_comunes),
    ("manifest-valido:sin-forma-sin-repetir", GRUPO, test_sin_forma_no_repite_el_discriminador),
]
