"""Ejercita la tabla autoritativa de firmas sin duplicar sus filas."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Callable, Dict, List, Optional, Tuple
from unittest import mock


ENCODING = "utf-8"
RAIZ = Path(__file__).resolve().parents[2]
INVENTARIO = RAIZ / "tests" / "inventario-bloques.md"
TITULO = "## 6. Tabla cerrada de firmas"
FIN = "### Firma de infraestructura de tests"
Caso = Tuple[str, str, Callable[[Optional[object]], None]]
Instantanea = Dict[str, Tuple[str, int, bytes]]


@dataclass(frozen=True)
class Firma:
    nombre: str
    archivo: Path
    posicionales: Tuple[str, ...]
    aridad: int
    cwd: str
    efectos: str
    limpieza: str
    codigo_aridad: int
    mensaje_aridad: str

    @property
    def muta(self) -> bool:
        return not self.efectos.startswith("solo lee")


def _sin_codigo(valor: str) -> str:
    if len(valor) < 2 or not valor.startswith("`") or not valor.endswith("`"):
        raise ValueError("valor sin delimitadores de código: " + valor)
    return valor[1:-1]


def _leer_firmas() -> Tuple[Firma, ...]:
    texto = INVENTARIO.read_text(encoding=ENCODING)
    if texto.count(TITULO) != 1:
        raise ValueError("la sección 6 del inventario está ausente o duplicada")
    seccion = texto.split(TITULO, 1)[1].split(FIN, 1)[0]
    firmas: List[Firma] = []
    for linea in seccion.splitlines():
        if not linea.startswith("| `"):
            continue
        celdas = [celda.strip() for celda in linea[1:-1].split("|")]
        if len(celdas) != 9:
            raise ValueError("fila de firma con cardinalidad inválida")
        aridad = int(celdas[3])
        posicionales = tuple(re.findall(r"\d+\. `([^`]+)`", celdas[2]))
        if len(posicionales) != aridad:
            raise ValueError("posicionales y aridad divergen para " + celdas[0])
        diagnostico = re.fullmatch(r"(\d+); stderr=`([^`]*)`; cero mutación", celdas[8])
        if diagnostico is None:
            raise ValueError("diagnóstico de aridad inválido para " + celdas[0])
        firmas.append(Firma(
            nombre=_sin_codigo(celdas[0]),
            archivo=RAIZ / _sin_codigo(celdas[1]),
            posicionales=posicionales,
            aridad=aridad,
            cwd=celdas[4],
            efectos=celdas[5],
            limpieza=celdas[7],
            codigo_aridad=int(diagnostico.group(1)),
            mensaje_aridad=diagnostico.group(2),
        ))
    nombres = [firma.nombre for firma in firmas]
    if not firmas or len(nombres) != len(set(nombres)):
        raise ValueError("la tabla de firmas está vacía o contiene nombres duplicados")
    return tuple(firmas)


def _instantanea(raiz: Path) -> Instantanea:
    resultado: Instantanea = {}
    for ruta in sorted(raiz.rglob("*")):
        relativa = ruta.relative_to(raiz)
        if ".git" in relativa.parts:
            continue
        modo = stat.S_IMODE(ruta.lstat().st_mode)
        if ruta.is_symlink():
            contenido = os.readlink(ruta).encode(ENCODING)
            tipo = "symlink"
        elif ruta.is_dir():
            contenido = b""
            tipo = "directory"
        else:
            # The snapshot is binary because poststate comparison must preserve exact bytes.
            contenido = ruta.read_bytes()
            tipo = "file"
        resultado[str(relativa)] = (tipo, modo, contenido)
    return resultado


def _ejecutar(archivo: Path, argumentos: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(archivo)] + argumentos,
        cwd=str(cwd), capture_output=True, text=True, encoding=ENCODING, check=False,
    )


def _argumentos_genericos(firma: Firma) -> List[str]:
    argumentos = []
    for indice, nombre in enumerate(firma.posicionales, 1):
        if nombre in {"max_fix_rounds", "per_page"}:
            argumentos.append("1")
        elif nombre == "pre_dispatch_sha":
            argumentos.append("0" * 40)
        elif nombre == "command":
            argumentos.append(":")
        else:
            argumentos.append("entrada-{0}-{1}".format(indice, nombre.replace("_", "-")))
    return argumentos


def _preparar_mutacion(firma: Firma, arena: Path) -> Tuple[Path, List[str]]:
    cwd = arena
    if firma.nombre == "promocion-tasks-ready":
        # El plan lleva su cadena de contrato porque a este gate no se llega sin ella: el script
        # congela la version vigente y el `hash` que ella declara, y sin cadena no hay que congelar.
        (cwd / "plan.md").write_text(
            "---\nstatus: planned\ncomplexity: normal\n"
            "contract_procedure: measured-v1\n---\ncontenido\n"
            "## v1\n\n`hash_previo:` · `hash: " + "a" * 64 + "`\n",
            encoding=ENCODING,
        )
        (cwd / "log.md").write_text(
            "- `paso: congelar` · `actor: conductor` · "
            "`timestamp: 2026-08-24T12:00:00Z`\n",
            encoding=ENCODING,
        )
        return cwd, ["plan.md", "log.md"]
    if firma.nombre == "split":
        (cwd / "raw.md").write_text(
            "STATUS: transport\n## Índice\n| A | uno |\n"
            "## Detalle\n### A\ndesarrollo\nSTATUS: done\n",
            encoding=ENCODING,
        )
        (cwd / "index.md").write_text("original-index\n", encoding=ENCODING)
        (cwd / "detail.md").write_text("original-detail\n", encoding=ENCODING)
        return cwd, ["raw.md", "index.md", "detail.md"]
    if firma.nombre == "split-paginado":
        (cwd / "salida").mkdir()
        (cwd / "raw.md").write_text(
            "## Índice\n| ID | Resumen |\n|---|---|\n| A | uno |\n| B | dos |\n"
            "## Detalle\n### A\ndesarrollo\nSTATUS: done\n",
            encoding=ENCODING,
        )
        return cwd, ["raw.md", "salida/index", "1"]
    if firma.nombre == "rebaseline-worktree":
        cwd = arena / "repo"
        cwd.mkdir()
        (cwd / "tracked.txt").write_text("base\n", encoding=ENCODING)
        for comando in (
            ["git", "init", "-q"],
            ["git", "config", "user.name", "V6"],
            ["git", "config", "user.email", "v6@example.invalid"],
            ["git", "add", "tracked.txt"],
            ["git", "commit", "-qm", "base"],
        ):
            subprocess.run(comando, cwd=str(cwd), capture_output=True, check=True)
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(cwd), capture_output=True,
            text=True, encoding=ENCODING, check=True,
        ).stdout.strip()
        return cwd, [sha, "V6", ":"]
    raise AssertionError("fila mutante sin preparación: " + firma.nombre)


def _comprobar_mutacion_correcta(firma: Firma, arena: Path,
                                  resultado: subprocess.CompletedProcess) -> None:
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stderr == ""
    if firma.nombre == "promocion-tasks-ready":
        plan = (arena / "plan.md").read_text(encoding=ENCODING)
        assert "status: tasks-ready\n" in plan
        # El congelamiento es el unico paso que escribe las dos claves congeladas: sin ellas el
        # calculo de cobertura da 3 y la receta de huellas no arranca en ningun flujo real.
        assert "contract_frozen_version: 1\n" in plan
        assert "contract_frozen_hash: " + "a" * 64 + "\n" in plan
        assert not tuple(arena.glob(".plan.md.promocion.*"))
    elif firma.nombre == "split":
        assert (arena / "index.md").read_text(encoding=ENCODING) == "| A | uno |\n"
        assert (arena / "detail.md").read_text(encoding=ENCODING) == "### A\ndesarrollo\n"
    elif firma.nombre == "split-paginado":
        assert (arena / "salida/index.md").is_file()
        assert (arena / "salida/index-p01.md").is_file()
        assert (arena / "salida/index-p02.md").is_file()
        assert (arena / "salida/detail-index.md").read_text(encoding=ENCODING) == \
            "### A\ndesarrollo\n"
        residuos = tuple((arena / "salida").glob(".*.tmp")) + \
            tuple((arena / "salida").glob(".*.bak"))
        assert not residuos, residuos
    elif firma.nombre == "rebaseline-worktree":
        assert "resultado: GREEN_ALREADY" in resultado.stdout
        assert not tuple(arena.glob(".rebaseline-wt-*"))


def _cargar_modulo(firma: Firma) -> ModuleType:
    nombre = "tests_firma_" + firma.nombre.replace("-", "_")
    especificacion = importlib.util.spec_from_file_location(nombre, firma.archivo)
    if especificacion is None or especificacion.loader is None:
        raise AssertionError("no se pudo cargar " + str(firma.archivo))
    modulo = importlib.util.module_from_spec(especificacion)
    sys.path.insert(0, str(firma.archivo.parent))
    try:
        especificacion.loader.exec_module(modulo)
    finally:
        sys.path.pop(0)
    return modulo


def _invocar_main(modulo: ModuleType, archivo: Path, argumentos: List[str], cwd: Path
                  ) -> Tuple[Optional[int], str, str, Optional[BaseException]]:
    argv_anterior = sys.argv
    cwd_anterior = Path.cwd()
    stdout = io.StringIO()
    stderr = io.StringIO()
    error: Optional[BaseException] = None
    codigo: Optional[int] = None
    try:
        sys.argv = [str(archivo)] + argumentos
        os.chdir(cwd)
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                codigo = modulo.main()
            except BaseException as exc:  # The injected failure may be intentionally propagated.
                error = exc
    finally:
        os.chdir(cwd_anterior)
        sys.argv = argv_anterior
    return codigo, stdout.getvalue(), stderr.getvalue(), error


def _comprobar_fallo_publicacion(firma: Firma) -> None:
    with tempfile.TemporaryDirectory(prefix="firma-v6-fallo-") as temporal:
        arena = Path(temporal)
        (arena / "sentinel.txt").write_text("intacto\n", encoding=ENCODING)
        cwd, argumentos = _preparar_mutacion(firma, arena)
        antes = _instantanea(arena)
        modulo = _cargar_modulo(firma)
        if firma.nombre == "promocion-tasks-ready":
            parche = mock.patch.object(
                modulo.os, "replace", side_effect=OSError("fallo inyectado"))
        elif firma.nombre == "split":
            parche = mock.patch.object(
                modulo.Path, "write_text", side_effect=OSError("fallo inyectado"))
        elif firma.nombre == "split-paginado":
            for ruta in (
                arena / "salida/detail-index.md",
                arena / "salida/index-p01.md",
                arena / "salida/index-p02.md",
                arena / "salida/index.md",
            ):
                ruta.write_text("original:" + ruta.name + "\n", encoding=ENCODING)
            antes = _instantanea(arena)
            parche = mock.patch.object(
                modulo.os, "replace", side_effect=OSError("fallo inyectado"))
        elif firma.nombre == "rebaseline-worktree":
            def ejecutar_fallido(*args: str, cwd: Path = None) -> subprocess.CompletedProcess:
                if args[1:3] == ("cat-file", "-e"):
                    return subprocess.CompletedProcess(args, 0, b"", b"")
                if args[1:3] == ("rev-parse", "--show-toplevel"):
                    return subprocess.CompletedProcess(args, 0, str(cwd_raiz).encode(ENCODING), b"")
                return subprocess.CompletedProcess(args, 1, b"", b"fallo inyectado")

            cwd_raiz = cwd
            parche = mock.patch.object(modulo, "ejecutar", side_effect=ejecutar_fallido)
        else:
            raise AssertionError("fila mutante sin inyección: " + firma.nombre)

        with parche:
            codigo, _stdout, _stderr, error = _invocar_main(
                modulo, firma.archivo, argumentos, cwd)
        if firma.nombre == "split":
            assert isinstance(error, OSError)
        else:
            assert error is None
            assert codigo != 0
        assert _instantanea(arena) == antes
        residuos = tuple(arena.rglob(".*.tmp")) + tuple(arena.rglob(".*.bak")) + \
            tuple(arena.glob(".rebaseline-wt-*"))
        assert not residuos, residuos


def _ejercer_firma(firma: Firma) -> None:
    assert firma.archivo.is_file(), firma.archivo
    assert "cwd aislado" in firma.cwd or "repositorio Git activo" in firma.cwd
    assert "temporal" in firma.limpieza or "artefactos" in firma.limpieza or \
        "worktree" in firma.limpieza

    argumentos = _argumentos_genericos(firma)
    for cantidad in (firma.aridad - 1, firma.aridad + 1):
        with tempfile.TemporaryDirectory(prefix="firma-v6-aridad-") as temporal:
            cwd = Path(temporal)
            (cwd / "sentinel.txt").write_text("intacto\n", encoding=ENCODING)
            antes = _instantanea(cwd)
            resultado = _ejecutar(firma.archivo, argumentos[:cantidad] if cantidad < firma.aridad
                                  else argumentos + ["sobrante"], cwd)
            assert resultado.returncode == firma.codigo_aridad
            assert resultado.stdout == ""
            assert resultado.stderr == firma.mensaje_aridad + "\n"
            assert _instantanea(cwd) == antes

    with tempfile.TemporaryDirectory(prefix="firma-v6-correcta-") as temporal:
        arena = Path(temporal)
        (arena / "sentinel.txt").write_text("intacto\n", encoding=ENCODING)
        if firma.muta:
            cwd, argumentos_correctos = _preparar_mutacion(firma, arena)
        else:
            cwd, argumentos_correctos = arena, argumentos
        antes = _instantanea(arena)
        resultado = _ejecutar(firma.archivo, argumentos_correctos, cwd)
        if firma.muta:
            _comprobar_mutacion_correcta(firma, arena, resultado)
        else:
            assert resultado.returncode in {0, 1, firma.codigo_aridad}
            assert (resultado.returncode, resultado.stderr) != (
                firma.codigo_aridad, firma.mensaje_aridad + "\n")
            assert _instantanea(arena) == antes

    if firma.muta:
        _comprobar_fallo_publicacion(firma)


def _crear_caso(firma: Firma) -> Callable[[Optional[object]], None]:
    def ejercer(_contexto: Optional[object]) -> None:
        """La firma publicada gobierna aridad, cwd, efectos y limpieza."""
        _ejercer_firma(firma)

    ejercer.__doc__ = "Firma completa de {0}.".format(firma.nombre)
    return ejercer


FIRMAS = _leer_firmas()
CASOS: List[Caso] = []
for indice, firma_inventariada in enumerate(FIRMAS, 1):
    prueba = _crear_caso(firma_inventariada)
    prueba.__name__ = "test_firma_{0:02d}".format(indice)
    globals()[prueba.__name__] = prueba
    CASOS.append(("firma:" + firma_inventariada.nombre, "firmas-v6", prueba))
