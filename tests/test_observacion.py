"""Tests durables de las dimensiones y normalizaciones del oracle."""

from __future__ import annotations

from tests.observacion import (
    Evento,
    Observacion,
    comparar,
    normalizar_artefactos,
    normalizar_stdout,
)


def _observacion(exit: int = 0, stdout: bytes = b"igual\n",
                 artefactos: dict[str, bytes] | None = None) -> Observacion:
    return Observacion(
        exit=exit,
        stdout=stdout,
        stderr=b"",
        artefactos={"a.txt": b"igual\n"} if artefactos is None else artefactos,
    )


EVENTOS = [Evento("uno", (("entidad", "A"),)), Evento("dos", ())]


def _afirmar_dimension(dimension: str, clase_px: str = "aceptacion",
                       eventos_px: list[Evento] | None = None,
                       observacion_px: Observacion | None = None,
                       clase_ps: str = "aceptacion",
                       eventos_ps: list[Evento] | None = None,
                       observacion_ps: Observacion | None = None) -> None:
    veredicto = comparar(
        clase_px,
        EVENTOS if eventos_px is None else eventos_px,
        _observacion() if observacion_px is None else observacion_px,
        clase_ps,
        EVENTOS if eventos_ps is None else eventos_ps,
        _observacion() if observacion_ps is None else observacion_ps,
    )
    assert not veredicto.iguales
    assert veredicto.dimensiones_divergentes == [dimension]


def test_dimension_clase(_contexto: object | None) -> None:
    """La clase gobierna el veredicto por sí sola."""
    _afirmar_dimension("clase", clase_ps="rechazo")


def test_dimension_eventos(_contexto: object | None) -> None:
    """La multiplicidad de eventos gobierna; su orden no."""
    _afirmar_dimension("eventos", eventos_ps=EVENTOS + [EVENTOS[0]])
    assert comparar("aceptacion", EVENTOS, _observacion(),
                    "aceptacion", list(reversed(EVENTOS)), _observacion()).iguales


def test_dimension_stdout(_contexto: object | None) -> None:
    """Stdout gobierna el veredicto por sí solo y conserva mayúsculas."""
    _afirmar_dimension("stdout", observacion_ps=_observacion(stdout=b"Igual\n"))


def test_dimension_artefactos(_contexto: object | None) -> None:
    """Las rutas y el contenido de artefactos gobiernan por sí solos."""
    _afirmar_dimension(
        "artefactos",
        observacion_ps=_observacion(artefactos={"A.txt": b"igual\n"}),
    )


def test_dimension_codigo(_contexto: object | None) -> None:
    """Los códigos 2 y 99 divergen aunque la clase sea idéntica."""
    _afirmar_dimension(
        "codigo",
        observacion_px=_observacion(exit=2),
        observacion_ps=_observacion(exit=99),
    )


def _afirmar_normalizacion(izquierda: bytes, derecha: bytes) -> None:
    assert normalizar_stdout(izquierda) == normalizar_stdout(derecha)
    assert normalizar_artefactos({"a": izquierda}) == normalizar_artefactos({"a": derecha})


def test_normalizacion_crlf(_contexto: object | None) -> None:
    """CRLF se normaliza a LF en stdout y artefactos."""
    _afirmar_normalizacion(b"a\r\nb\r\n", b"a\nb\n")


def test_normalizacion_bom_inicial(_contexto: object | None) -> None:
    """Un BOM inicial se elimina en stdout y artefactos."""
    _afirmar_normalizacion("\ufeffa\n".encode("utf-8"), b"a\n")


def test_normalizacion_espacio_final(_contexto: object | None) -> None:
    """Espacios y tabuladores finales se eliminan por línea."""
    _afirmar_normalizacion(b"a  \nb\t\n", b"a\nb\n")


CASOS = [
    ("observacion-dimension-clase", "dimensiones", test_dimension_clase),
    ("observacion-dimension-eventos", "dimensiones", test_dimension_eventos),
    ("observacion-dimension-stdout", "dimensiones", test_dimension_stdout),
    ("observacion-dimension-artefactos", "dimensiones", test_dimension_artefactos),
    ("observacion-dimension-codigo", "dimensiones", test_dimension_codigo),
    ("observacion-normalizacion-crlf", "normalizaciones", test_normalizacion_crlf),
    ("observacion-normalizacion-bom", "normalizaciones", test_normalizacion_bom_inicial),
    ("observacion-normalizacion-espacio-final", "normalizaciones",
     test_normalizacion_espacio_final),
]
