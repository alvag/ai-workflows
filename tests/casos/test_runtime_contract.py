"""Pruebas durables del resolvedor y del contrato de runtime."""

from __future__ import annotations

import ast
import importlib.util
import os
import re
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple


ENCODING = "utf-8"
RAIZ = Path(__file__).resolve().parents[2]
REFERENCIAS = (
    RAIZ / "skills" / "sdd-flow" / "reference.md",
    RAIZ / "skills" / "sdd-orchestrator" / "reference.md",
    RAIZ / "skills" / "cross-review" / "reference.md",
    RAIZ / "skills" / "co-explore" / "reference.md",
    RAIZ / "skills" / "cross-implement" / "reference.md",
)
CASOS_PATH = (
    ("alias-roto", "broken", "valid", "py -3", 0),
    ("python-3.8", "old", "valid", "py -3", 0),
    ("python-valido", "valid", "valid", "python3", 0),
    ("ambos-rotos", "broken", "broken", None, 1),
)
MARCA_HIJO_STDLIB = "AI_WORKFLOWS_STDLIB_CHILD"
Caso = Tuple[str, str, Callable[[Optional[object]], None]]


def _extraer_receta_posix(referencia: Path) -> str:
    texto = referencia.read_text(encoding=ENCODING)
    inicio = "<!-- resolvedor-python:inicio -->"
    fin = "<!-- resolvedor-python:fin -->"
    if texto.count(inicio) != 1 or texto.count(fin) != 1:
        raise AssertionError("marcas inválidas en {0}".format(referencia))
    region = texto.split(inicio, 1)[1].split(fin, 1)[0]
    bloques = re.findall(r"```sh\n(.*?)```", region, flags=re.DOTALL)
    if len(bloques) != 1:
        raise AssertionError("receta POSIX ausente o duplicada en {0}".format(referencia))
    return bloques[0]


def _escribir_stub(ruta: Path, variable_modo: str) -> None:
    ruta.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$0 $*\" >> \"$STUB_ARGV\"\n"
        "modo=${" + variable_modo + ":-broken}\n"
        "case \"$modo\" in\n"
        "  valid) exit 0 ;;\n"
        "  old)\n"
        "    case \"$*\" in\n"
        "      *'sys.version_info >= (3, 9)'*) exit 1 ;;\n"
        "      *) exit 0 ;;\n"
        "    esac ;;\n"
        "  *) exit 23 ;;\n"
        "esac\n",
        encoding=ENCODING,
    )
    ruta.chmod(0o755)


def _ejercer_receta(referencia: Path, modo_python3: str, modo_py: str,
                     elegido: Optional[str], codigo_esperado: int) -> None:
    receta = _extraer_receta_posix(referencia)
    with tempfile.TemporaryDirectory(prefix="resolvedor-python-") as temporal:
        raiz_temporal = Path(temporal)
        cwd = raiz_temporal / "cwd-arbitrario"
        cwd.mkdir()
        registro = raiz_temporal / "argv.log"
        _escribir_stub(raiz_temporal / "python3", "STUB_PYTHON3_MODE")
        _escribir_stub(raiz_temporal / "py", "STUB_PY_MODE")

        entorno = dict(os.environ)
        entorno.update({
            "PATH": str(raiz_temporal),
            "STUB_ARGV": str(registro),
            "STUB_PYTHON3_MODE": modo_python3,
            "STUB_PY_MODE": modo_py,
        })

        if modo_python3 == "old":
            control = subprocess.run(
                [str(raiz_temporal / "python3"), "-c", "raise SystemExit(0)"],
                cwd=str(cwd), env=entorno, capture_output=True, check=False,
            )
            assert control.returncode == 0, "el stub 3.8 no ejecuta código ajeno al probe"
            registro.write_text("", encoding=ENCODING)

        resultado = subprocess.run(
            ["/bin/sh", "-c", receta + "\nprintf 'ELEGIDO:%s\\n' \"$PYTHON_SKILL\"\n"],
            cwd=str(cwd), env=entorno, capture_output=True, text=True,
            encoding=ENCODING, check=False,
        )
        assert resultado.returncode == codigo_esperado, resultado.stderr
        if elegido is None:
            assert "python3 -c and py -3 -c failed" in resultado.stderr
        else:
            assert resultado.stdout.strip() == "ELEGIDO:" + elegido

        invocaciones = registro.read_text(encoding=ENCODING).splitlines()
        assert invocaciones, "la receta no ejecutó ningún candidato"
        for invocacion in invocaciones:
            assert "-c" in invocacion.split(), "probe sin -c: " + invocacion
        if elegido == "python3":
            assert all(Path(linea.split()[0]).name != "py" for linea in invocaciones)
        if elegido == "py -3":
            llamadas_py = [linea.split() for linea in invocaciones
                           if Path(linea.split()[0]).name == "py"]
            assert llamadas_py and all("-3" in llamada for llamada in llamadas_py)


def _crear_caso_v4(referencia: Path, configuracion: Tuple[str, str, str,
                                                          Optional[str], int]
                   ) -> Callable[[Optional[object]], None]:
    nombre, modo_python3, modo_py, elegido, codigo_esperado = configuracion

    def test_resolvedor(_contexto: Optional[object]) -> None:
        """La receta publicada resuelve por ejecución desde un cwd arbitrario."""
        _ejercer_receta(referencia, modo_python3, modo_py, elegido, codigo_esperado)

    test_resolvedor.__doc__ = "{0}: {1}.".format(referencia.parent.name, nombre)
    return test_resolvedor


def _modulos_durables() -> Tuple[Path, ...]:
    rutas = list((RAIZ / "tests").rglob("*.py"))
    for scripts in (RAIZ / "skills").glob("*/scripts"):
        rutas.extend(scripts.rglob("*.py"))
    return tuple(sorted(set(rutas)))


def test_v5_compila_python39(_contexto: Optional[object]) -> None:
    """Todo módulo durable compila con la gramática mínima de Python 3.9."""
    for ruta in _modulos_durables():
        fuente = ruta.read_text(encoding=ENCODING)
        ast.parse(fuente, filename=str(ruta), mode="exec", feature_version=(3, 9))
        compile(fuente, str(ruta), "exec", dont_inherit=True)


def _esta_dentro(ruta: Path, directorio: Path) -> bool:
    try:
        ruta.relative_to(directorio)
    except ValueError:
        return False
    return True


def _imports_de(ruta: Path) -> Iterable[Tuple[str, int]]:
    arbol = ast.parse(ruta.read_text(encoding=ENCODING), filename=str(ruta))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for nombre in nodo.names:
                yield nombre.name.split(".", 1)[0], nodo.lineno
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            yield nodo.module.split(".", 1)[0], nodo.lineno


def test_v5_solo_stdlib(_contexto: Optional[object]) -> None:
    """Los módulos durables solo importan stdlib o módulos locales."""
    modulos = _modulos_durables()
    locales = {ruta.stem for ruta in modulos} | {"tests"}
    stdlib = Path(sysconfig.get_path("stdlib")).resolve()
    sitios = {
        Path(valor).resolve() for clave in ("purelib", "platlib")
        for valor in (sysconfig.get_path(clave),) if valor
    }
    for ruta in modulos:
        for raiz_import, linea in _imports_de(ruta):
            if raiz_import in locales:
                continue
            especificacion = importlib.util.find_spec(raiz_import)
            assert especificacion is not None, "{0}:{1}: import no resoluble: {2}".format(
                ruta, linea, raiz_import)
            if especificacion.origin in (None, "built-in", "frozen"):
                continue
            origen = Path(especificacion.origin).resolve()
            assert not any(_esta_dentro(origen, sitio) for sitio in sitios), \
                "{0}:{1}: import de tercero: {2}".format(ruta, linea, raiz_import)
            assert _esta_dentro(origen, stdlib), \
                "{0}:{1}: import fuera de stdlib: {2}".format(ruta, linea, raiz_import)


def test_v5_suite_sin_terceros(_contexto: Optional[object]) -> None:
    """La suite completa corre con site-packages deshabilitado."""
    if os.environ.get(MARCA_HIJO_STDLIB) == "1":
        return
    codigo = (
        "import runpy,sys; "
        "sys.path.insert(0, {0!r}); "
        "sys.argv=['tests']; "
        "runpy.run_module('tests', run_name='__main__')"
    ).format(str(RAIZ))
    entorno = dict(os.environ)
    entorno[MARCA_HIJO_STDLIB] = "1"
    resultado = subprocess.run(
        [sys.executable, "-I", "-S", "-c", codigo],
        cwd=str(RAIZ), env=entorno, capture_output=True, text=True,
        encoding=ENCODING, check=False,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def _modo_open(nodo: ast.Call) -> Optional[str]:
    modo: object = "r"
    indice = 1 if isinstance(nodo.func, ast.Name) else 0
    if len(nodo.args) > indice:
        modo = nodo.args[indice]
    for clave in nodo.keywords:
        if clave.arg == "mode":
            modo = clave.value
    if isinstance(modo, str):
        return modo
    if isinstance(modo, ast.Constant) and isinstance(modo.value, str):
        return modo.value
    return None


def _tiene_keyword(nodo: ast.Call, nombre: str) -> bool:
    return any(clave.arg == nombre for clave in nodo.keywords)


def _motivo_binario_declarado(lineas: List[str], linea: int) -> bool:
    contexto = " ".join(lineas[max(0, linea - 4):linea]).lower()
    return any(testigo in contexto for testigo in ("binari", "binary", "bytes"))


def test_v5_aperturas_explicitas(_contexto: Optional[object]) -> None:
    """Toda apertura de texto declara encoding y toda binaria declara su motivo."""
    for ruta in _modulos_durables():
        fuente = ruta.read_text(encoding=ENCODING)
        lineas = fuente.splitlines()
        arbol = ast.parse(fuente, filename=str(ruta))
        for nodo in (item for item in ast.walk(arbol) if isinstance(item, ast.Call)):
            nombre = ""
            if isinstance(nodo.func, ast.Name):
                nombre = nodo.func.id
            elif isinstance(nodo.func, ast.Attribute):
                nombre = nodo.func.attr
            if nombre in ("read_text", "write_text"):
                assert _tiene_keyword(nodo, "encoding"), \
                    "{0}:{1}: apertura de texto sin encoding".format(ruta, nodo.lineno)
            elif nombre in ("read_bytes", "write_bytes"):
                assert _motivo_binario_declarado(lineas, nodo.lineno), \
                    "{0}:{1}: apertura binaria sin motivo".format(ruta, nodo.lineno)
            elif nombre == "open":
                modo = _modo_open(nodo)
                assert modo is not None, \
                    "{0}:{1}: modo de apertura no auditable".format(ruta, nodo.lineno)
                if "b" in modo:
                    assert _motivo_binario_declarado(lineas, nodo.lineno), \
                        "{0}:{1}: apertura binaria sin motivo".format(ruta, nodo.lineno)
                else:
                    assert _tiene_keyword(nodo, "encoding"), \
                        "{0}:{1}: apertura de texto sin encoding".format(ruta, nodo.lineno)


CASOS: List[Caso] = []
for indice_referencia, ruta_referencia in enumerate(REFERENCIAS, 1):
    for indice_configuracion, configuracion_path in enumerate(CASOS_PATH, 1):
        prueba = _crear_caso_v4(ruta_referencia, configuracion_path)
        prueba.__name__ = "test_v4_resolvedor_{0}_{1}".format(
            indice_referencia, indice_configuracion)
        globals()[prueba.__name__] = prueba
        CASOS.append((
            "runtime-v4:{0}:{1}".format(ruta_referencia.parent.name, configuracion_path[0]),
            "runtime-v4",
            prueba,
        ))

CASOS.extend((
    ("runtime-v5:python-3.9", "runtime-v5", test_v5_compila_python39),
    ("runtime-v5:stdlib", "runtime-v5", test_v5_solo_stdlib),
    ("runtime-v5:suite-aislada", "runtime-v5", test_v5_suite_sin_terceros),
    ("runtime-v5:aperturas", "runtime-v5", test_v5_aperturas_explicitas),
))
