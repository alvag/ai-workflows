"""Ejercita la tabla autoritativa de firmas sin duplicar sus filas."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Callable, List, Optional, Tuple
from unittest import mock

from tests.arbol import Instantanea, _instantanea


ENCODING = "utf-8"
RAIZ = Path(__file__).resolve().parents[2]
INVENTARIO = RAIZ / "tests" / "inventario-bloques.md"
TITULO = "## 6. Tabla cerrada de firmas"
FIN = "### Firma de infraestructura de tests"
Caso = Tuple[str, str, Callable[[Optional[object]], None]]


@dataclass(frozen=True)
class Firma:
    nombre: str
    archivo: Path
    posicionales: Tuple[str, ...]
    aridad: int
    variadica: bool
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
        variadica = celdas[3].endswith("+")
        aridad = int(celdas[3].rstrip("+"))
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
            variadica=variadica,
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
        elif nombre == "phase":
            argumentos.append("final")
        else:
            argumentos.append("entrada-{0}-{1}".format(indice, nombre.replace("_", "-")))
    return argumentos


def _preparar_mutacion(firma: Firma, arena: Path) -> Tuple[Path, List[str]]:
    cwd = arena
    if firma.nombre == "promocion-tasks-ready":
        # El plan lleva su cadena de contrato porque a este gate no se llega sin ella: el script
        # congela la version vigente y el `hash` que ella declara, y sin cadena no hay que congelar.
        (cwd / "plan.md").write_text(
            "--- \nstatus : planned\ncomplexity: normal\n"
            "contract_procedure: measured-v1\n--- \ncontenido\n"
            "contract_frozen_hash: body-sentinel\n"
            # El hash es el **canónico** del bloque, no un relleno: el script valida la cadena antes
            # de congelar, así que un valor inventado bloquea. El fixture anterior usaba sesenta y
            # cuatro `a` y la promoción lo congelaba, que era justo el defecto.
            "## v1\n\n`hash_previo:` · `hash: bd3a154d6c9e3149aa6797ce77c5ceb975c0295a3a2eacc0f257b6b28021b7d8`\n",
            encoding=ENCODING,
        )
        (cwd / "bitacora.md").write_text(
            "- `paso: congelar` · `actor: conductor` · "
            "`timestamp: 2026-08-24T12:00:00Z`\n",
            encoding=ENCODING,
        )
        return cwd, ["plan.md", "bitacora.md", "sequence-ledger.yml",
                     str(cwd / ".cross-model/active/cross-implement")]
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
        assert "contract_frozen_hash: bd3a154d6c9e3149aa6797ce77c5ceb975c0295a3a2eacc0f257b6b28021b7d8\n" in plan
        assert "contract_frozen_hash: body-sentinel\n" in plan
        assert "no encontró una clave status reescribible en el header" in \
            firma.archivo.read_text(encoding=ENCODING)
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
    cantidades = (firma.aridad - 1,) if firma.variadica else (firma.aridad - 1, firma.aridad + 1)
    for cantidad in cantidades:
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


def _ejecutar_auxiliar(nombre: str, argumentos: List[str], cwd: Path) -> subprocess.CompletedProcess:
    archivo = RAIZ / "skills" / "cross-implement" / "scripts" / (nombre + ".py")
    return _ejecutar(archivo, argumentos, cwd)


def _probar_dependencia_rota(nombre: str, argumentos: List[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="aux-dependencia-rota-") as temporal:
        arena = Path(temporal)
        origen = RAIZ / "skills" / "cross-implement" / "scripts" / (nombre + ".py")
        copia = arena / origen.name
        copia.write_bytes(origen.read_bytes())
        (arena / "contrato-invariantes.py").write_text(
            "raise RuntimeError('dependencia rota')\n", encoding=ENCODING)
        resultado = _ejecutar(copia, argumentos, arena)
        assert resultado.returncode == 99, (nombre, resultado.returncode, resultado.stderr)
        assert f"ARNES:{nombre} dependencia contrato-invariantes.py no cargable" in resultado.stderr


def test_aux_contrato_baseline(_contexto: Optional[object]) -> None:
    """La matriz cerrada de baseline distingue sus cuatro adjudicaciones."""
    identidades = ("already-satisfied-ok", "weak-check-ok", "adjudicacion-ausente",
                   "adjudicacion-desconocida")
    assert len(set(identidades)) == 4
    with tempfile.TemporaryDirectory(prefix="aux-baseline-") as temporal:
        arena = Path(temporal)
        plantilla = (
            "## v1\n\n| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |\n"
            "|---|---|---|---|---|---|\n| A | conducta | test | : | ok | GREEN_ALREADY |\n\n"
            "- `id: A` · `commit: abc123` · `timestamp: 2026-01-01T00:00:00Z` · "
            "`observado: exit 0; ok`{adjudicacion}\n")
        for valor, codigo in (("already_satisfied", 0), ("weak_check", 0), ("", 1),
                              ("desconocida", 1)):
            sufijo = f" · `adjudicación: {valor}`" if valor else ""
            contrato = arena / (valor or "ausente")
            contrato.write_text(plantilla.format(adjudicacion=sufijo), encoding=ENCODING)
            resultado = _ejecutar_auxiliar("contrato-baseline", [str(contrato)], arena)
            assert resultado.returncode == codigo, (valor, resultado.stderr)


def test_aux_rebaseline_worktree(_contexto: Optional[object]) -> None:
    """La proyección separa la pareja reservada de un 125 ordinario."""
    identidades = ("pareja-reservada-blocked", "codigo-125-proyeccion-valida-red",
                   "sin-lf-blocked", "contenido-adicional-blocked")
    assert len(set(identidades)) == 4
    firma = next(item for item in FIRMAS if item.nombre == "rebaseline-worktree")
    modulo = _cargar_modulo(firma)
    assert not modulo._CONTRATO.es_envoltura_canonica("printf directo")
    envuelta = shlex.join(["sh", "-c", modulo._CONTRATO.PROJECTION_WRAPPER_BODY,
                           "sh", "printf predicado", "printf 'failures=0\\n'"])
    assert modulo._CONTRATO.es_envoltura_canonica(envuelta)
    with tempfile.TemporaryDirectory(prefix="aux-rebaseline-") as temporal:
        salida = Path(temporal) / "salida"
        for cuerpo, codigo, envuelta, esperado in (
                (b"CROSS_IMPLEMENT_PROJECTION_BLOCKED\n", 125, True, "BLOCKED"),
                (b"CROSS_IMPLEMENT_PROJECTION_BLOCKED\n", 125, False, "RED"),
                (b"raw\nfailures=2\n", 125, True, "RED"),
                (b"raw\nfailures=2", 0, True, "BLOCKED"),
                (b"raw\nfailures=2\nextra\n", 0, True, "BLOCKED"),
                (b"raw\ncount=12\nextra\n", 0, False, "GREEN_ALREADY")):
            # La forma incluye el LF final; se escriben bytes para no normalizarlo.
            salida.write_bytes(cuerpo)
            assert modulo.clasificar_proyeccion(salida, codigo, envuelta) == esperado

        repo = Path(temporal) / "repo"
        repo.mkdir()
        (repo / "tracked.txt").write_text("base\n", encoding=ENCODING)
        for comando in (
                ["git", "init", "-q"],
                ["git", "config", "user.name", "V12"],
                ["git", "config", "user.email", "v12@example.invalid"],
                ["git", "add", "tracked.txt"],
                ["git", "commit", "-qm", "base"]):
            subprocess.run(comando, cwd=repo, capture_output=True, check=True)
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True,
            text=True, encoding=ENCODING, check=True).stdout.strip()
        real_run = subprocess.run

        def rebaseline(comando: str, estado_forzado: Optional[str] = None) -> str:
            previo, argv = Path.cwd(), sys.argv
            out = io.StringIO()
            try:
                os.chdir(repo)
                sys.argv = [str(firma.archivo), sha, "V12", comando]
                parche = (mock.patch.object(modulo, "clasificar_proyeccion",
                                            return_value=estado_forzado)
                          if estado_forzado is not None else contextlib.nullcontext())
                with parche, contextlib.redirect_stdout(out):
                    assert modulo.main() == 0
            finally:
                os.chdir(previo)
                sys.argv = argv
            return out.getvalue()

        directo = rebaseline("printf 'count=12\\n'; exit 3")
        assert "resultado: RED" in directo and "observado: exit 3; count=12" in directo
        bloqueado = rebaseline("printf 'salida real\\n'; exit 3", "BLOCKED")
        assert "resultado: BLOCKED" in bloqueado
        assert "observado: exit 3; salida real" in bloqueado

        def fallo_despues_de_crear(*args: object, **kwargs: object) -> subprocess.CompletedProcess:
            if kwargs.get("shell"):
                raise OSError("fallo inyectado al ejecutar la fila")
            return real_run(*args, **kwargs)

        worktree = repo.parent / f".rebaseline-wt-{os.getpid()}"
        salida_temporal = Path(f"{worktree}.out")
        cwd_previo, argv_previo = Path.cwd(), sys.argv
        out, err = io.StringIO(), io.StringIO()
        try:
            os.chdir(repo)
            sys.argv = [str(firma.archivo), sha, "V12", ":"]
            with mock.patch.object(modulo.subprocess, "run", side_effect=fallo_despues_de_crear), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                codigo = modulo.main()
        finally:
            os.chdir(cwd_previo)
            sys.argv = argv_previo
            real_run(["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                     capture_output=True, check=False)
            real_run(["git", "-C", str(repo), "worktree", "prune"],
                     capture_output=True, check=False)
            salida_temporal.unlink(missing_ok=True)
        assert codigo == 1
        assert out.getvalue() == ""
        assert err.getvalue() == "BLOCKED V12: no se pudo ejecutar o limpiar el re-baseline\n"
        listado = real_run(
            ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
            capture_output=True, text=True, encoding=ENCODING, check=True).stdout
        assert str(worktree) not in listado and not salida_temporal.exists()
    _probar_dependencia_rota("rebaseline-worktree", ["sha", "V12", ":"])


def test_aux_gate_modo_directo(_contexto: Optional[object]) -> None:
    """La aprobación de reparación solo cabe entre sus anclas."""
    identidades = ("reparacion-entre-kickoff-y-freeze",
                   "reparacion-antes-de-kickoff-rechazada",
                   "reparacion-despues-de-freeze-rechazada")
    assert len(set(identidades)) == 3
    base = [
        "- `paso: derivar-tabla` · `actor: conductor` · `timestamp: 2026-01-01T00:00:00Z`",
        "- `paso: ejecutar-baseline` · `actor: conductor` · `timestamp: 2026-01-01T00:01:00Z`",
        "- `paso: aprobar-kickoff` · `actor: usuario` · `timestamp: 2026-01-01T00:02:00Z`",
        "- `paso: congelar` · `actor: conductor` · `timestamp: 2026-01-01T00:04:00Z`",
        "- `paso: despachar` · `actor: conductor` · `timestamp: 2026-01-01T00:05:00Z`",
    ]
    aprobacion = ("- `paso: aprobar-reparación` · `actor: usuario` · `token: 1:A:esperado-corregido:a1` · "
                  f"`hash: {'a' * 64}` · `timestamp: 2026-01-01T00:03:00Z`")
    with tempfile.TemporaryDirectory(prefix="aux-gate-directo-") as temporal:
        arena = Path(temporal)
        for lineas, codigo in ((base[:3] + [aprobacion] + base[3:], 0),
                               ([aprobacion] + base, 1), (base + [aprobacion], 1)):
            log = arena / "bitacora.md"
            log.write_text("\n".join(lineas) + "\n", encoding=ENCODING)
            resultado = _ejecutar_auxiliar("gate-modo-directo", [str(log)], arena)
            assert resultado.returncode == codigo, resultado.stderr
        tarde = aprobacion.replace("esperado-corregido", "cobertura-agregada")
        log.write_text("\n".join(base + [tarde]) + "\n", encoding=ENCODING)
        resultado = _ejecutar_auxiliar("gate-modo-directo", [str(log)], arena)
        assert "GUARD:cobertura-antes-del-primer-congelamiento" in resultado.stderr
        invalido = tarde.replace("cobertura-agregada:a1", "cobertura-agregada-a1")
        log.write_text("\n".join(base + [invalido]) + "\n", encoding=ENCODING)
        resultado = _ejecutar_auxiliar("gate-modo-directo", [str(log)], arena)
        assert resultado.returncode == 1 and "GUARD:aprobacion-reparacion-invalida" in resultado.stderr
        log.write_text("\n".join(base[:3] + [base[4], base[3]]) + "\n", encoding=ENCODING)
        resultado = _ejecutar_auxiliar("gate-modo-directo", [str(log)], arena)
        assert "GUARD:congelar-antes-de-despachar-orden-del-log" in resultado.stderr
        assert "GUARD:congelar-antes-de-despachar-timestamps" not in resultado.stderr
        log.write_text("\n".join(base[:3] + [base[3].replace("00:04:00", "00:06:00"), base[4]])
                       + "\n", encoding=ENCODING)
        resultado = _ejecutar_auxiliar("gate-modo-directo", [str(log)], arena)
        assert "GUARD:congelar-antes-de-despachar-timestamps" in resultado.stderr
        assert "GUARD:congelar-antes-de-despachar-orden-del-log" not in resultado.stderr
        clasificacion = ("- `paso: clasificar-falla` · `actor: conductor` · `checkId: V1` · "
                         "`clase: DESIGN_GAP` · `timestamp: 2026-01-01T00:00:30Z`")
        lineas = base[:2] + [clasificacion + " (reconstruido)"] + base[2:]
        log.write_text("\n".join(lineas) + "\n", encoding=ENCODING)
        resultado = _ejecutar_auxiliar("gate-modo-directo", [str(log)], arena)
        assert resultado.returncode == 1 and "GUARD:bitacora-linea-malformada" in resultado.stderr
        lineas[2] = clasificacion
        log.write_text("\n".join(lineas) + "\n", encoding=ENCODING)
        resultado = _ejecutar_auxiliar("gate-modo-directo", [str(log)], arena)
        assert resultado.returncode == 1 and "GUARD:kickoff-antes-de-congelar" in resultado.stderr
    _probar_dependencia_rota("gate-modo-directo", ["bitacora.md"])


def test_aux_ownership_log(_contexto: Optional[object]) -> None:
    """Las ocho formas cerradas conservan ownership delegado e inline."""
    identidades = ("delegado-canonico", "inline-canonico", "orquestador-canonico",
                   "auxiliar-incompleto", "campos-comunes-incompletos", "delegado-par-prohibido",
                   "no-implementable-ronda-cero", "implementacion-delta-fragmentado")
    assert len(set(identidades)) == 8
    delegado = ("Ownership:\n- `checkId: A` · `clase: IMPLEMENTATION_DEFECT` · "
                 "`consumedRound: sí` · `evidencia: diff rojo`\n")
    auxiliar = ("- `paso: clasificar-falla` · `actor: conductor` · `timestamp: 2026-01-01T00:00:00Z` · "
                "`checkId: A` · `clase: VERIFICATION_DEFECT` · `consumedRound: no` · "
                "`evidencia: salida divergente` · `delta: sha256:uno` · `fix_round: 0` · "
                "`contract_version: 2` · `verification_defect_ordinal: 1`\n")
    orquestado = auxiliar.replace("actor: conductor", "actor: orquestador")
    no_impl = auxiliar.replace("VERIFICATION_DEFECT", "DESIGN_GAP").replace(
        " · `contract_version: 2` · `verification_defect_ordinal: 1`", "")
    casos = (
        (delegado, 0), (auxiliar, 0), (orquestado, 0),
        (auxiliar.replace(" · `delta: sha256:uno`", ""), 1),
        (auxiliar.replace("`evidencia: salida divergente`", "`evidencia: `"), 1),
        (delegado.replace("`evidencia: diff rojo`", "`evidencia: diff rojo` · `contract_version: 2`"), 1),
        (no_impl, 0),
        ("## Ronda 1\n" + delegado.replace("`evidencia: diff rojo`", "`evidencia: uno` · `delta: d` · `fix_round: 1`")
         + "\n## Ronda 2\n" + delegado.replace("`evidencia: diff rojo`", "`evidencia: dos` · `delta: d` · `fix_round: 2` · `razón: cambió stderr`"), 1),
    )
    with tempfile.TemporaryDirectory(prefix="aux-ownership-log-") as temporal:
        arena = Path(temporal)
        for indice, (texto, codigo) in enumerate(casos):
            log = arena / f"log-{indice}.md"
            log.write_text(texto, encoding=ENCODING)
            resultado = _ejecutar_auxiliar("ownership-log", [str(log)], arena)
            assert resultado.returncode == codigo, (indice, resultado.stderr)
        firma = next(item for item in FIRMAS if item.nombre == "ownership-log")
        modulo = _cargar_modulo(firma)
        linea = delegado.splitlines()[1]
        citado = delegado + "\n## Ejemplo\n" + linea + "\n"
        with mock.patch.object(modulo, "lineas_ownership", wraps=modulo.lineas_ownership) as leer:
            assert modulo.clasificaciones(citado) == [("delegada", linea)]
            assert leer.call_count == 1
        log = arena / "citado.md"
        log.write_text(citado, encoding=ENCODING)
        assert _ejecutar_auxiliar("ownership-log", [str(log)], arena).returncode == 0
        invalido = delegado.replace("diff rojo", "diff · rojo")
        log.write_text(invalido, encoding=ENCODING)
        assert _ejecutar_auxiliar("ownership-log", [str(log)], arena).returncode == 1
    _probar_dependencia_rota("ownership-log", ["log.md"])


def test_aux_ownership_presupuesto(_contexto: Optional[object]) -> None:
    """El presupuesto usa apariciones físicas salvo para pares aprobados."""
    identidades = ("delegado-dos-y-tercero", "inline-misma-ruta", "entorno-byte-identico",
                   "integracion-cuatro-clases")
    assert len(set(identidades)) == 4
    with tempfile.TemporaryDirectory(prefix="aux-ownership-budget-") as temporal:
        arena = Path(temporal)
        impl = ("Ownership:\n" + "\n".join(
            f"- `checkId: A` · `clase: IMPLEMENTATION_DEFECT` · `consumedRound: sí` · `evidencia: e{n}`"
            for n in range(3)) + "\n")
        vacio = arena / "vacio.md"
        vacio.write_text("", encoding=ENCODING)
        log = arena / "impl.md"
        log.write_text(impl, encoding=ENCODING)
        assert _ejecutar_auxiliar("ownership-presupuesto", [str(log), str(vacio), "2"], arena).returncode == 1
        mismo = arena / "mismo.md"
        mismo.write_text(
            "Ownership:\n- `checkId: V` · `clase: VERIFICATION_DEFECT` · `consumedRound: no` · `evidencia: x`\n\n"
            "- `paso: aprobar-reparación` · `checkId: V` · `contract_version: 2` · "
            "`verification_defect_ordinal: 1`\n", encoding=ENCODING)
        assert _ejecutar_auxiliar("ownership-presupuesto", [str(mismo), str(mismo), "2"], arena).returncode == 0
        entorno = arena / "entorno.md"
        entorno.write_text(
            "Ownership:\n- `checkId: E` · `clase: ENVIRONMENT_FAILURE` · `consumedRound: no` · `evidencia: x`\n"
            "- `checkId: E` · `clase: ENVIRONMENT_FAILURE` · `consumedRound: no` · `evidencia: x`\n",
            encoding=ENCODING)
        assert _ejecutar_auxiliar("ownership-presupuesto", [str(entorno), str(vacio), "2"], arena).returncode == 0
        cuatro = arena / "cuatro.md"
        cuatro.write_text(
            "Ownership:\n- `checkId: I` · `clase: IMPLEMENTATION_DEFECT` · `consumedRound: sí` · `evidencia: x`\n"
            "- `checkId: V` · `clase: VERIFICATION_DEFECT` · `consumedRound: no` · `evidencia: x`\n"
            "- `checkId: E` · `clase: ENVIRONMENT_FAILURE` · `consumedRound: no` · `evidencia: x`\n"
            "- `checkId: D` · `clase: DESIGN_GAP` · `consumedRound: no` · `evidencia: x`\n",
            encoding=ENCODING)
        assert _ejecutar_auxiliar("ownership-presupuesto", [str(cuatro), str(vacio), "2"], arena).returncode == 0
        cuatro.write_text(cuatro.read_text(encoding=ENCODING).replace("evidencia: x", "evidencia: x · y", 1),
                          encoding=ENCODING)
        resultado = _ejecutar_auxiliar("ownership-presupuesto", [str(cuatro), str(vacio), "2"], arena)
        assert resultado.returncode == 1 and "clasificación inválida" in resultado.stderr
        aprobacion_mala = arena / "aprobacion-mala.md"
        aprobacion_mala.write_text(
            "- `paso: aprobar-reparación` · `checkId: V` · `contract_version: dos` · "
            "`verification_defect_ordinal: 1`\n", encoding=ENCODING)
        resultado = _ejecutar_auxiliar("ownership-presupuesto", [str(vacio), str(aprobacion_mala), "2"], arena)
        assert resultado.returncode == 1 and "versión u ordinal" in resultado.stderr
        resultado = _ejecutar_auxiliar("ownership-presupuesto", [str(vacio), str(arena / "ausente"), "2"], arena)
        assert resultado.returncode == 1 and "archivo ilegible" in resultado.stderr
    _probar_dependencia_rota("ownership-presupuesto", ["log.md", "aprobaciones.md", "2"])


def _ejercer_contrato_cadena(script: Path) -> List[str]:
    cabecera = "| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |"
    registro = "- `id: A` · `commit: abc123`"
    encabezado = "### Baseline de v1"
    hash_actual = "`hash: {0}`".format("a" * 64)
    hash_previo = "`hash_previo: {0}`".format("b" * 64)
    base = (
        "## v1\n\n"
        "`hash_previo:` · `hash: bd3a154d6c9e3149aa6797ce77c5ceb975c0295a3a2eacc0f257b6b28021b7d8`\n"
        "## Fin\n"
    )

    def diagnostico(linea: int, forma: str) -> str:
        return f"GUARD:contrato-fuera-de-version línea {linea}: {forma}"

    casos = [
        ("tabla-huerfana-completa",
         base + cabecera + "\n|---|---|---|---|---|---|\n" + registro + "\n" +
         encabezado + "\n`hash_previo:`\n", 1,
         (diagnostico(5, "cabecera"), diagnostico(7, "registro"),
          diagnostico(8, "encabezado-baseline"), diagnostico(9, "hashes"))),
        ("cabecera-huerfana", base + cabecera + "\n", 1, (diagnostico(5, "cabecera"),)),
        ("registro-huerfano", base + registro + "\n", 1, (diagnostico(5, "registro"),)),
        ("encabezado-huerfano", base + encabezado + "\n", 1,
         (diagnostico(5, "encabezado-baseline"),)),
        ("hash-huerfano", base + hash_actual + "\n", 1, (diagnostico(5, "hashes"),)),
        ("cabecera-con-espacio-previo", base + "  " + cabecera + " \n", 1,
         (diagnostico(5, "cabecera"),)),
        ("cabecera-celda-extra", base + cabecera[:-1] + " Extra |\n", 0, ()),
        ("cabecera-columnas-permutadas",
         base + "| Requisito | ID | Evidencia | Comando/observación | Esperado | Baseline |\n",
         0, ()),
        ("registro-sin-acento-grave", base + "- id: A`\n", 0, ()),
        ("registro-con-espacio-previo", base + " - `id: A`\n", 0, ()),
        ("encabezado-siete-almohadillas", base + "####### Baseline de v1\n", 0, ()),
        ("encabezado-sin-digito", base + "### Baseline de v\n", 0, ()),
        ("hash-minuscula-64", base + hash_actual + "\n", 1, (diagnostico(5, "hashes"),)),
        ("hash-previo-minuscula-64", base + hash_previo + "\n", 1,
         (diagnostico(5, "hashes"),)),
        ("hash-previo-vacio", base + "`hash_previo:`\n", 1, (diagnostico(5, "hashes"),)),
        ("hash-vacio", base + "`hash: `\n", 0, ()),
        ("hash-63", base + "`hash: {0}`\n".format("a" * 63), 0, ()),
        ("hash-65", base + "`hash: {0}`\n".format("a" * 65), 0, ()),
        ("hash-mayuscula-64", base + "`hash: {0}`\n".format("A" * 64), 0, ()),
        ("dos-literales-una-linea", base + hash_actual + " · " + hash_previo + "\n", 1,
         (diagnostico(5, "hashes"),)),
        ("sin-versiones", cabecera + "\n", 1, (diagnostico(1, "cabecera"),)),
        ("verify-ordinario",
         base + "## Verify\n| Caso | Comando | Esperado |\n|---|---|---|\n| uno | : | ok |\n",
         0, ()),
    ]
    for indice, forma in enumerate((cabecera, registro, encabezado, hash_actual), 1):
        casos.append((f"forma-cercada-{indice}", base + "```\n" + forma + "\n```\n", 0, ()))

    formas = [cabecera, registro, encabezado]
    lineas_version = ["## v1", *formas, "`hash_previo:` · `hash: `"]
    canon = [re.sub(r"`hash: [^`]*`", "`hash: `", linea).rstrip()
             for linea in lineas_version]
    hash_version = hashlib.sha256(("\n".join(canon) + "\n").encode(ENCODING)).hexdigest()
    lineas_version[-1] = f"`hash_previo:` · `hash: {hash_version}`"
    casos.append(("cuatro-formas-dentro-version",
                  "\n".join(lineas_version + ["## Fin", ""]), 0, ()))

    interior_base = ["### v1", registro, "`hash_previo:` · `hash: `"]
    hash_interior = hashlib.sha256(
        ("\n".join(interior_base) + "\n").encode(ENCODING)).hexdigest()
    interior = interior_base[:-1] + [f"`hash_previo:` · `hash: {hash_interior}`"]
    exterior_base = ["## v2", cabecera,
                     f"`hash_previo: {hash_interior}` · `hash: `", *interior]
    canon_exterior = [re.sub(r"`hash: [^`]*`", "`hash: `", linea).rstrip()
                      for linea in exterior_base]
    hash_exterior = hashlib.sha256(
        ("\n".join(canon_exterior) + "\n").encode(ENCODING)).hexdigest()
    exterior = exterior_base.copy()
    exterior[2] = f"`hash_previo: {hash_interior}` · `hash: {hash_exterior}`"
    anidado = "\n".join(exterior + ["## Fin", ""])
    casos.append(("bloques-anidados-union", anidado, 0, ()))

    desajustes: List[str] = []
    with tempfile.TemporaryDirectory(prefix="aux-contrato-cadena-") as temporal:
        arena = Path(temporal)
        for nombre, contenido, codigo, diagnosticos in casos:
            contrato = arena / (nombre + ".md")
            contrato.write_text(contenido, encoding=ENCODING)
            resultado = _ejecutar(script, [str(contrato)], arena)
            lineas_error = tuple(resultado.stderr.splitlines())
            if resultado.returncode != codigo or lineas_error != diagnosticos:
                desajustes.append(
                    f"{nombre}: rc={resultado.returncode}, stderr={lineas_error!r}, "
                    f"esperado=({codigo}, {diagnosticos!r})")

        nombre_modulo = "tests_contrato_cadena_" + str(abs(hash(str(script))))
        especificacion = importlib.util.spec_from_file_location(nombre_modulo, script)
        if especificacion is None or especificacion.loader is None:
            desajustes.append("versiones-anidadas: no se pudo cargar el módulo")
        else:
            modulo = importlib.util.module_from_spec(especificacion)
            especificacion.loader.exec_module(modulo)
            esperadas = sorted(((1, interior), (2, exterior)))
            if modulo.versiones(anidado) != esperadas:
                desajustes.append("versiones-anidadas: la salida cambió")
    return desajustes


def test_aux_contrato_cadena(_contexto: Optional[object]) -> None:
    """La matriz huérfana es roja en la base y verde en el árbol actual."""
    with tempfile.TemporaryDirectory(prefix="aux-contrato-cadena-base-") as temporal:
        base = Path(temporal) / "contrato-cadena.py"
        resultado = subprocess.run(
            ["git", "show", "48903a1:skills/cross-implement/scripts/contrato-cadena.py"],
            cwd=RAIZ, capture_output=True, check=False)
        assert resultado.returncode == 0, resultado.stderr.decode(ENCODING, "replace")
        base.write_bytes(resultado.stdout)
        desajustes_base = _ejercer_contrato_cadena(base)
        assert any(desajuste.startswith("tabla-huerfana-completa: rc=0")
                   for desajuste in desajustes_base), \
            "la regresión de la tabla huérfana no da rojo contra 48903a1"
    assert not _ejercer_contrato_cadena(
        RAIZ / "skills/cross-implement/scripts/contrato-cadena.py")


def test_aux_promocion_tasks_ready(_contexto: Optional[object]) -> None:
    """La promoción publica su matriz cerrada de dieciséis identidades."""
    firma = next(item for item in FIRMAS if item.nombre == "promocion-tasks-ready")
    modulo = _cargar_modulo(firma)
    modulo.verificar_promocion()
    with tempfile.TemporaryDirectory(prefix="aux-promocion-huerfano-") as temporal:
        arena = Path(temporal)
        estado = modulo.preparar_estado_refresh(arena)
        plan = estado[0]
        plan.write_text(
            plan.read_text(encoding=ENCODING) + "## Fin\n- `id: huerfano`\n",
            encoding=ENCODING,
        )
        antes = plan.read_bytes()
        header_antes = plan.read_text(encoding=ENCODING).split("---", 2)[1]
        argumentos = [str(ruta) for ruta in estado[:4]]
        codigo, stdout, stderr, error = _invocar_main(
            modulo, firma.archivo, argumentos, arena)
        assert error is None and codigo == 1 and stdout == ""
        assert "GUARD:contrato-fuera-de-version" in stderr and \
            "registro" in stderr and "línea" in stderr
        assert "la estructura o la cadena del contrato no valida" in stderr
        assert plan.read_bytes() == antes
        header_despues = plan.read_text(encoding=ENCODING).split("---", 2)[1]
        assert header_despues == header_antes
        assert header_despues.count("contract_frozen_version:") == 1
        assert header_despues.count("contract_frozen_hash:") == 1
    with tempfile.TemporaryDirectory(prefix="aux-promocion-dependencia-") as temporal:
        estado = modulo.preparar_estado_refresh(Path(temporal))
        previo, sys.argv = sys.argv, [str(firma.archivo)] + [str(ruta) for ruta in estado[:4]]
        stderr = io.StringIO()
        try:
            with mock.patch.object(modulo, "_cargar_invariantes", return_value=None), \
                    contextlib.redirect_stderr(stderr):
                codigo = modulo.main()
        finally:
            sys.argv = previo
        assert codigo == 99 and "ARNES:promocion-tasks-ready contrato-helper-no-cargable" in stderr.getvalue()


def test_aux_cadena_de_invocacion(_contexto: Optional[object]) -> None:
    """Las cinco guardas aparecen invocadas y con su salida leída."""
    contrato = (RAIZ / "skills/cross-implement/contrato-verificacion.md").read_text(encoding=ENCODING)
    skill = (RAIZ / "skills/cross-implement/SKILL.md").read_text(encoding=ENCODING)
    texto = contrato + "\n" + skill
    marcadores = (
        "contrato-invariantes.py <contrato> <log_de_aprobaciones> candidate",
        "contrato-invariantes.py <contrato> <log_de_aprobaciones> final",
        "código de salida de contrato-invariantes", "stderr de contrato-invariantes",
        "ownership-log.py <log>", "código de salida de ownership-log", "stderr de ownership-log",
        "ownership-presupuesto.py <log> <log_de_aprobaciones> <max_fix_rounds>",
        "código de salida de ownership-presupuesto", "stderr de ownership-presupuesto",
        "rebaseline-worktree.py", "código de salida de rebaseline-worktree",
        "stdout de rebaseline-worktree", "gate-modo-directo.py <bitacora>",
        "código de salida de gate-modo-directo", "stderr de gate-modo-directo",
    )
    assert len(marcadores) == 16 and all(marcador in texto for marcador in marcadores)


def test_aux_verify_ejecuta(_contexto: Optional[object]) -> None:
    """La guarda de verify coteja las veinte sedes de producción y recuperación."""
    script = RAIZ / "skills/sdd-flow/scripts/verify-ejecuta.py"
    argumentos = [str(RAIZ / "skills/sdd-flow/SKILL.md"),
                  str(RAIZ / "skills/sdd-flow/reference.md")]
    resultado = _ejecutar(script, argumentos, RAIZ)
    assert resultado.returncode == 0, resultado.stderr


CASOS.extend((
    ("contrato-auxiliar:contrato-baseline", "contrato-auxiliares-v1", test_aux_contrato_baseline),
    ("contrato-auxiliar:contrato-cadena", "contrato-auxiliares-v1", test_aux_contrato_cadena),
    ("contrato-auxiliar:rebaseline-worktree", "contrato-auxiliares-v1", test_aux_rebaseline_worktree),
    ("contrato-auxiliar:gate-modo-directo", "contrato-auxiliares-v1", test_aux_gate_modo_directo),
    ("contrato-auxiliar:ownership-log", "contrato-auxiliares-v1", test_aux_ownership_log),
    ("contrato-auxiliar:ownership-presupuesto", "contrato-auxiliares-v1", test_aux_ownership_presupuesto),
    ("contrato-auxiliar:promocion-tasks-ready", "contrato-auxiliares-v1", test_aux_promocion_tasks_ready),
    ("contrato-auxiliar:cadena-de-invocacion", "contrato-auxiliares-v1", test_aux_cadena_de_invocacion),
    ("contrato-auxiliar:verify-ejecuta", "contrato-auxiliares-v1", test_aux_verify_ejecuta),
))
