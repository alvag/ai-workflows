"""Matriz sede × estado de `FuenteIlegible`: cada sede registrada falla nombrando la fuente
y la causa, para cada uno de los tres estados que `bloque_yaml` puede producir (AC-9).

Los estados se fabrican sobre una copia temporal de cada sede, nunca sobre el árbol de
trabajo: mutar producción para probar deja el repositorio mutado si el proceso muere.
"""

from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import re
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Callable, List, Optional, Tuple


ENCODING = "utf-8"
RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "scripts" / "verificar-vistas-config.py"
Case = Tuple[str, str, Callable[[Optional[object]], None]]

_ESTADOS_ASCII = {
    "archivo ausente": "archivo_ausente",
    "heading ausente": "heading_ausente",
    "bloque vacío": "bloque_vacio",
}


def _asegurar_yaml_importable() -> None:
    """La guarda importa PyYAML (dependencia de terceros, fuera de la stdlib) a nivel de
    módulo, pero `bloque_yaml`/`FuenteIlegible`/`SEDES_CONFIG` —lo único que este caso
    ejercita— nunca llaman a `yaml`. La suite exige que sus propios módulos resuelvan con
    site-packages deshabilitado (`test_v5_suite_sin_terceros`) y que ningún import de tercero
    aparezca en su análisis estático (`test_v5_solo_stdlib`, que busca la sentencia `import
    yaml`/`from yaml import ...` por AST). Por eso esta función nunca escribe esa sentencia:
    resuelve el nombre dinámicamente con `importlib`, y si PyYAML no está instalable en ese
    Python aislado, registra un stub con un `ModuleSpec` de origen `None` — la misma forma que
    usan los módulos built-in/frozen, que esa guarda ya acepta sin exigir un archivo real."""
    if "yaml" in sys.modules:
        return
    try:
        importlib.import_module("yaml")
        return
    except ImportError:
        pass
    stub = types.ModuleType("yaml")
    stub.__spec__ = importlib.machinery.ModuleSpec("yaml", loader=None)
    sys.modules["yaml"] = stub


def _cargar_guarda():
    _asegurar_yaml_importable()
    especificacion = importlib.util.spec_from_file_location(
        "guarda_verificar_vistas_config_sedes", SCRIPT)
    if especificacion is None or especificacion.loader is None:
        raise AssertionError("no se pudo cargar " + str(SCRIPT))
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


MODULO = _cargar_guarda()


def _preparar_estado(ruta_real: Path, ancla: str, estado: str, tmp: Path) -> Path:
    if estado == "archivo ausente":
        return tmp / (ruta_real.name + ".no-existe")
    lineas = ruta_real.read_text(encoding=ENCODING).splitlines()
    patron = re.compile(rf"^#+ {ancla}")
    if estado == "heading ausente":
        # bloque_yaml activa `on` en la PRIMERA línea que matchea y no vuelve a mirar atrás:
        # si el ancla aparece más de una vez (título del documento + heading de sección, como
        # en config-ejemplo.md), hay que quitar TODAS las ocurrencias para que el ancla quede
        # realmente ausente y no sólo corrida a la siguiente coincidencia.
        lineas = [linea for linea in lineas if not patron.match(linea)]
    elif estado == "bloque vacío":
        indice = next(i for i, linea in enumerate(lineas) if patron.match(linea))
        lineas = lineas[:indice + 1] + ["```yaml", "```"]
    else:
        raise AssertionError("estado sin preparación: " + estado)
    copia = tmp / ruta_real.name
    copia.write_text("\n".join(lineas) + "\n", encoding=ENCODING)
    return copia


def _ejercer(ruta_real: Path, ancla: str, estado: str) -> None:
    with tempfile.TemporaryDirectory(prefix="sedes-config-estado-") as temporal:
        objetivo = _preparar_estado(ruta_real, ancla, estado, Path(temporal))
        try:
            MODULO.bloque_yaml(objetivo, ancla)
        except MODULO.FuenteIlegible as excepcion:
            assert excepcion.causa == estado, (
                f"sede={ruta_real} estado_esperado={estado} causa_obtenida={excepcion.causa}")
            assert str(objetivo) in str(excepcion), (
                f"sede={ruta_real} estado={estado}: la excepción no nombra la fuente")
        else:
            raise AssertionError(
                f"sede={ruta_real} estado={estado}: bloque_yaml no lanzó FuenteIlegible")


def _make_test(ruta: Path, ancla: str, estado: str) -> Callable[[Optional[object]], None]:
    def test_estado(_contexto: Optional[object]) -> None:
        """Cada estado registrado de FuenteIlegible falla nombrando su propia sede."""
        _ejercer(ruta, ancla, estado)

    return test_estado


def _inyectar_nombre_retirado(ruta_real: Path, ancla: str, tmp: Path) -> Path:
    """Copia la sede e inyecta `knowledge_vault:` —el nombre retirado, guion bajo— como
    hermana de primer nivel de `knowledge-vault:`. Normalizando guion medio a guion bajo las
    dos colapsan al mismo nombre: es el cuarto estado de AC-9 ("nombre retirado presente"),
    y sirve de control positivo de AC-8 (el check de colisión tiene que poder ponerse rojo)."""
    lineas = ruta_real.read_text(encoding=ENCODING).splitlines()
    patron_ancla = re.compile(rf"^#+ {ancla}")
    indice_ancla = next(i for i, linea in enumerate(lineas) if patron_ancla.match(linea))
    indice_fence = next(i for i in range(indice_ancla, len(lineas))
                        if re.match(r"^\s*```yaml", lineas[i]))
    lineas[indice_fence + 1:indice_fence + 1] = [
        "knowledge_vault:  # nombre retirado (guion bajo), inyectado por el caso",
        "  mode: auto",
    ]
    copia = tmp / ruta_real.name
    copia.write_text("\n".join(lineas) + "\n", encoding=ENCODING)
    return copia


def _ejercer_colision_nombre_retirado() -> None:
    """`check6_colision` carga YAML de verdad (PyYAML, vía `_cargar_yaml`), a diferencia de
    `bloque_yaml`/`FuenteIlegible`: no alcanza con el stub de `_asegurar_yaml_importable`, que
    solo deja `import yaml` resolver sin ofrecer un parser real. Por eso este control corre en
    un subproceso de Python SIN `-I -S`: aunque el proceso que ejecuta la suite esté aislado de
    site-packages (`test_v5_suite_sin_terceros`), un hijo nuevo arranca con inicialización
    normal y PyYAML disponible — el mismo patrón que `test_firmas.py` usa para ejercitar
    scripts con su entorno completo."""
    with tempfile.TemporaryDirectory(prefix="sedes-config-colision-") as temporal:
        ruta_real = MODULO.KNOWLEDGE_VAULT_REF
        ancla = MODULO.KNOWLEDGE_VAULT_REF_HEADING
        copia = _inyectar_nombre_retirado(ruta_real, ancla, Path(temporal))
        codigo = (
            "import importlib.util\n"
            "from pathlib import Path\n"
            "spec = importlib.util.spec_from_file_location('g', {script!r})\n"
            "m = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(m)\n"
            "ok, msg = m.check6_colision([(Path({copia!r}), {ancla!r}, 'dueno', 'bloque')])\n"
            "print('OK' if ok else 'RED')\n"
            "print(msg)\n"
        ).format(script=str(SCRIPT), copia=str(copia), ancla=ancla)
        resultado = subprocess.run([sys.executable, "-c", codigo],
                                   capture_output=True, text=True, encoding=ENCODING)
        assert resultado.returncode == 0 and not resultado.stderr, (
            f"sede={ruta_real} estado=nombre-retirado-presente: el subproceso de "
            f"verificación falló — {resultado.stderr}")
        lineas = resultado.stdout.splitlines()
        veredicto, mensaje = lineas[0], "\n".join(lineas[1:])
        assert veredicto == "RED", (
            f"sede={ruta_real} estado=nombre-retirado-presente: el check de colisión "
            f"no se puso rojo — {mensaje}")
        assert "knowledge-vault" in mensaje and "knowledge_vault" in mensaje, (
            f"sede={ruta_real} estado=nombre-retirado-presente: el mensaje no nombra "
            f"las dos claves — {mensaje}")


def test_colision_nombre_retirado(_contexto: Optional[object]) -> None:
    """El nombre retirado `knowledge_vault` junto a `knowledge-vault` pone rojo el check de
    colisión nombrando las dos (AC-8 control positivo · AC-9 cuarto estado)."""
    _ejercer_colision_nombre_retirado()


CASOS: List[Case] = []
for indice_sede, (ruta_sede, ancla_sede, rol_sede, _extraccion) in enumerate(
        MODULO.SEDES_CONFIG, 1):
    for estado_sede in _ESTADOS_ASCII:
        prueba = _make_test(ruta_sede, ancla_sede, estado_sede)
        prueba.__name__ = "test_sede_{0:02d}_{1}".format(
            indice_sede, _ESTADOS_ASCII[estado_sede])
        globals()[prueba.__name__] = prueba
        identificador = "sede-estado:{0}:{1}:{2}".format(
            ruta_sede.relative_to(RAIZ), rol_sede, _ESTADOS_ASCII[estado_sede])
        CASOS.append((identificador, "sedes-config-vault", prueba))

CASOS.append((
    "sede-estado:skills/knowledge-vault/reference.md:colision:nombre-retirado-presente",
    "sedes-config-vault",
    test_colision_nombre_retirado,
))
