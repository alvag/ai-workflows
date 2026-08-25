"""Entrypoint canónico de la suite durable."""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable, Optional

from tests.origenes import read_targets, validate_coverage


RAIZ = Path(__file__).resolve().parent
Caso = tuple[str, str, Callable[[Optional[object]], None]]


class InventarioInvalido(Exception):
    pass


def _cargar(ruta: Path) -> ModuleType:
    nombre = "tests_" + "_".join(ruta.relative_to(RAIZ).with_suffix("").parts)
    especificacion = importlib.util.spec_from_file_location(nombre, ruta)
    if especificacion is None or especificacion.loader is None:
        raise InventarioInvalido(f"no se pudo importar {ruta.relative_to(RAIZ)}")
    modulo = importlib.util.module_from_spec(especificacion)
    sys.modules[nombre] = modulo
    especificacion.loader.exec_module(modulo)
    return modulo


def _inventariar_modulo(ruta: Path, modulo: ModuleType, ids: set[str]) -> list[Caso]:
    inventario = getattr(modulo, "CASOS", None)
    if not isinstance(inventario, list) or not inventario:
        raise InventarioInvalido(f"{ruta.relative_to(RAIZ)} no declara un CASOS no vacío")

    elegibles = {nombre for nombre, valor in vars(modulo).items()
                 if nombre.startswith("test_") and callable(valor)}
    inventariados: list[str] = []
    casos: list[Caso] = []
    for entrada in inventario:
        if not isinstance(entrada, tuple) or len(entrada) != 3:
            raise InventarioInvalido(
                f"{ruta.relative_to(RAIZ)} contiene una entrada CASOS inválida")
        identificador, grupo, funcion = entrada
        if not isinstance(identificador, str) or not isinstance(grupo, str) or not callable(funcion):
            raise InventarioInvalido(
                f"{ruta.relative_to(RAIZ)} contiene una entrada CASOS inválida")
        if identificador in ids:
            raise InventarioInvalido(f"ID de caso duplicado: {identificador}")
        ids.add(identificador)
        inventariados.append(funcion.__name__)
        casos.append((identificador, grupo, funcion))

    if set(inventariados) != elegibles or len(inventariados) != len(elegibles):
        ocultos = sorted(elegibles - set(inventariados))
        ajenos = sorted(set(inventariados) - elegibles)
        raise InventarioInvalido(
            f"{ruta.relative_to(RAIZ)} no coincide con sus tests elegibles;"
            f" ocultos={ocultos}, no_elegibles={ajenos}")
    return casos


def descubrir() -> list[Caso]:
    casos: list[Caso] = []
    ids: set[str] = set()
    for ruta in sorted(RAIZ.rglob("test_*.py")):
        modulo = _cargar(ruta)
        casos.extend(_inventariar_modulo(ruta, modulo, ids))
    if not casos:
        raise InventarioInvalido("la selección quedó vacía")
    try:
        validate_coverage(casos, read_targets())
    except ValueError as exc:
        raise InventarioInvalido(str(exc)) from exc
    return casos


def listar(casos: list[Caso]) -> int:
    print(f"inventario: {len(casos)} casos")
    for identificador, grupo, funcion in casos:
        descripcion = (funcion.__doc__ or "").strip().split("\n")[0]
        print(f"  {identificador:<32} [{grupo}] {descripcion}")
    return 0


def correr(casos: list[Caso]) -> int:
    if not casos:
        print("ERROR: la selección quedó vacía", file=sys.stderr)
        return 1
    fallos = 0
    for identificador, _grupo, funcion in casos:
        try:
            funcion(None)
            print(f"caso {identificador}: ok")
        except Exception as exc:
            print(f"caso {identificador}: ERROR {type(exc).__name__}: {exc}")
            fallos += 1
    print(f"{len(casos) - fallos} casos ok" +
          (f", {fallos} con problema" if fallos else ""))
    return 1 if fallos else 0


PATRON_NODE = "tests/skills/knowledge-vault/*.test.mjs"


def correr_node() -> int:
    """Corre la suite Node **completa** y propaga su veredicto.

    El entrypoint durable enumeraba sólo tests de Python, así que el
    comportamiento destructivo del vault podía degradarse sin que ningún
    verificador canónico lo notara. Correr un subconjunto no alcanza: lo que se
    exige es la ejecución completa y el conteo a la vista.

    **Falla cerrado ante cero casos recolectados.** `node --test` sale 0 sobre
    una selección vacía, así que leer sólo el código de salida daría verde sobre
    una suite que no corrió — que es indistinguible de una que pasó.
    """
    node = shutil.which("node")
    if node is None:
        print("ERROR-SUITE: node no está en el PATH y la suite Node es obligatoria",
              file=sys.stderr)
        return 1

    proceso = subprocess.run(
        [node, "--test", "--test-reporter=tap", PATRON_NODE],
        cwd=RAIZ.parent, capture_output=True, text=True, check=False,
    )
    salida = proceso.stdout + proceso.stderr

    def contar(clave: str) -> int:
        hallazgo = re.search(rf"^# {clave} (\d+)$", salida, re.MULTILINE)
        return int(hallazgo.group(1)) if hallazgo else -1

    pasados, fallidos = contar("pass"), contar("fail")
    if pasados < 0 or fallidos < 0:
        print("ERROR-SUITE: la salida de node no trae su resumen TAP", file=sys.stderr)
        print(salida[-2000:], file=sys.stderr)
        return 1
    if pasados + fallidos == 0:
        print("ERROR-SUITE: la suite Node recolectó cero casos", file=sys.stderr)
        return 1

    print(f"{pasados} casos node ok" + (f", {fallidos} con problema" if fallidos else ""))
    if fallidos or proceso.returncode != 0:
        print(salida[-4000:], file=sys.stderr)
        return 1
    return 0


def autotest(casos: list[Caso]) -> int:
    if correr([]) == 0:
        print("autotest: la selección vacía dio verde", file=sys.stderr)
        return 1
    identificador, grupo, funcion = casos[0]
    modulo = sys.modules[funcion.__module__]
    original = list(modulo.CASOS)
    try:
        modulo.CASOS = [caso for caso in original if caso[0] != identificador]
        try:
            _inventariar_modulo(Path(modulo.__file__).resolve(), modulo, set())
        except InventarioInvalido:
            pass
        else:
            print("autotest: ocultar un test elegible no puso rojo el inventario", file=sys.stderr)
            return 1
    finally:
        modulo.CASOS = original
    escenario = next((caso for caso in casos if caso[0].startswith("escenario:")), None)
    if escenario is None:
        print("autotest: no existe un escenario para probar cobertura", file=sys.stderr)
        return 1
    try:
        validate_coverage([caso for caso in casos if caso[0] != escenario[0]], read_targets())
    except ValueError:
        pass
    else:
        print("autotest: ocultar un caso migrado no puso roja la cobertura", file=sys.stderr)
        return 1
    print(f"autotest: ocultar {identificador} fue detectado")
    print(f"autotest: ocultar {escenario[0]} fue detectado por cobertura")
    return 0


def main(argv: list[str]) -> int:
    try:
        casos = descubrir()
    except (InventarioInvalido, OSError, ImportError) as exc:
        print(f"ERROR-SUITE: {exc}", file=sys.stderr)
        return 1
    if argv == ["--listar"]:
        return listar(casos)
    if argv == ["--autotest"]:
        return autotest(casos)
    if argv:
        print(f"USO argumento no reconocido: {argv[0]}", file=sys.stderr)
        return 2
    # Las dos suites, y el veredicto es la peor de las dos. Correr la de Python y
    # salir cero mientras la de Node está roja es exactamente el hueco que este
    # entrypoint tenía.
    veredicto_py = correr(casos)
    veredicto_node = correr_node()
    return veredicto_py or veredicto_node


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
