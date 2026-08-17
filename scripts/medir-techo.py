#!/usr/bin/env python3
"""Aplica el techo de proporción (regla 2 de CLAUDE.md) a un diff.

LA SEDE NORMATIVA DE LA FÓRMULA ES `CLAUDE.md`, NO ESTE ARCHIVO. Acá se la implementa; si las dos
discrepan, manda la regla. Para que esa discrepancia no pase inadvertida, el script ancla el hash de
la sección normativa y se detiene si cambió (ver ANCLA_SHA256).

Este script **no tiene variante PowerShell**, y es una excepción deliberada a la regla de paridad del
repositorio. Esa regla rige para los comandos que invocan CLIs de modelos, donde difieren el quoting y
la forma de pasar el prompt; este solo lee la salida de `git`. Consecuencia asumida: en Windows el
techo se mide a mano.

Está en Python y no en shell por una medición, no por preferencia: `awk` no acepta NUL como separador
de registro —"\\0" es la cadena vacía, que activa el modo párrafo— así que el diff entero entra como un
solo registro y solo se procesa el primer archivo. El formato NUL es obligatorio para clasificar rutas
con tabuladores o saltos de línea en el nombre.

Uso:
    medir-techo.py <base>            mide contra el árbol de trabajo, sumando untracked no ignorados
    medir-techo.py <base> <head>     mide el rango; NO suma untracked (un rango no tiene árbol)
    medir-techo.py --ancla           imprime el hash esperado y el actual de la sección normativa

Salida:
    stdout  un resumen de UNA línea, sin ninguna ruta:
                nuevos_en_scripts=N num=N den=N VEREDICTO
    fd 3    si está abierto, las rutas clasificadas delimitadas por NUL: clase\\tadd\\truta\\0
    Los dos canales existen porque una ruta puede contener un salto de línea: "resumen de una línea" y
    "nombrar la ruta" no caben juntos.

Códigos de salida:
    0  pasa        el numerador no supera al denominador
    1  bloquea     lo supera
    2  invocación  argumentos faltantes o mal formados
    3  detenida    no se pudo medir; el mensaje nombra el punto de fallo

El 2 está sobrecargado: un módulo ausente también sale con 2. Quien lea este código debe exigir además
la marca literal de la salida. Y nunca leer un código de salida después de un pipe.
"""

import hashlib
import re
import subprocess
import sys

ANCLA_SHA256 = "0a50c2a4720e719a349fa15ac51238e7e7ae98051552686494aa2e5a858aaf00"
# Hash de la sección `### Regla 2 …` de CLAUDE.md, desde su encabezado hasta el siguiente de nivel <= 3,
# con los finales de línea recortados y sin líneas vacías al cierre.
#
# CÓMO SE RENUEVA cuando la regla cambia a propósito:
#   1. correr `medir-techo.py --ancla` y ver los dos valores;
#   2. leer el diff de la sección y confirmar que el cambio es el que se quería;
#   3. **releer la función clasificar() y calcular() contra la regla nueva** — este es el paso que no
#      se puede saltear;
#   4. recién entonces actualizar esta constante.
# Renovar el hash sin releer la fórmula es peor que no tener ancla: deja el script declarando
# conformidad con una regla que ya no implementa.

ANDAMIAJE = "andamiaje"
PRODUCTO = "producto"
NINGUNO = "ninguno"


class Detener(Exception):
    """Corta la medición nombrando el punto de fallo. Nunca se reporta como un veredicto."""

    def __init__(self, punto, detalle=""):
        super().__init__(f"punto={punto} {detalle}".rstrip())


class MalUso(Exception):
    pass


def correr(cmd, punto):
    """Ejecuta git y corta si falla. El fallo de un comando nunca se convierte en un cero."""
    try:
        p = subprocess.run(cmd, capture_output=True)
    except OSError as exc:
        raise Detener(punto, str(exc)) from exc
    if p.returncode != 0:
        primera = p.stderr.decode("utf-8", "replace").strip().split("\n")[0]
        raise Detener(punto, primera)
    return p.stdout


def seccion_normativa(raiz):
    """La sección de la regla 2, normalizada. No el archivo entero: un cambio en otra parte de
    CLAUDE.md no debe detener la medición."""
    try:
        texto = (raiz / "CLAUDE.md").read_text(encoding="utf-8")
    except OSError as exc:
        raise Detener("ancla", str(exc)) from exc
    lineas = texto.split("\n")
    try:
        i = next(k for k, l in enumerate(lineas) if l.startswith("### Regla 2"))
    except StopIteration:
        raise Detener("ancla", "no se encontró la sección '### Regla 2' en CLAUDE.md") from None
    j = len(lineas)
    for k in range(i + 1, len(lineas)):
        if re.match(r"^#{1,3} ", lineas[k]):
            j = k
            break
    corte = [l.rstrip() for l in lineas[i:j]]
    while corte and corte[-1] == "":
        corte.pop()
    return "\n".join(corte)


def clasificar(ruta):
    """La partición de la regla 2. Es una lista cerrada y su disparador de actualización está escrito
    en la propia regla: agregar una sede de producto, o un patrón de verificación nuevo."""
    if ruta.startswith("scripts/") or ruta.startswith("tests/"):
        return ANDAMIAJE
    base = ruta.rsplit("/", 1)[-1]
    if ".test." in base or base.startswith("verificar-"):
        return ANDAMIAJE
    if ruta.startswith("skills/") or ruta.startswith(".agents/skills/"):
        return PRODUCTO
    return NINGUNO


def registros(salida):
    """Parte la salida de `--numstat -z` en (add, del, ruta).

    El path se toma como **todo lo que sigue al segundo tabulador**: los dos primeros campos son
    números y nunca contienen uno, mientras un nombre de archivo sí puede. Un rename se emite como
    `add\\tdel\\t\\0origen\\0destino\\0`, y se atribuye al **destino**, así que un rename puro aporta
    cero y una ruta que ENTRA a scripts/ por un rename cuenta como alta ahí.
    """
    partes = salida.split(b"\0")
    i = 0
    while i < len(partes):
        crudo = partes[i]
        i += 1
        if not crudo:
            continue
        campos = crudo.split(b"\t", 2)
        if len(campos) != 3:
            raise Detener("parseo", "un registro del diff no tiene los dos tabuladores")
        add_b, del_b, ruta_b = campos
        if not (add_b.isdigit() and del_b.isdigit()):
            raise Detener("fila_no_numerica", "el diff trae una fila no numérica (¿binario?)")
        if ruta_b == b"":
            if i + 1 >= len(partes):
                raise Detener("parseo", "el diff termina en un registro de rename incompleto")
            ruta_b = partes[i + 1]          # [i] es el origen, [i+1] el destino
            i += 2
        yield int(add_b), int(del_b), ruta_b.decode("utf-8", "surrogateescape")


def contar_lineas(ruta):
    """Cuenta líneas lógicas. `wc -l` cuenta saltos de línea, así que da 0 en un archivo cuya última
    línea no termina en uno; medido contra git, ese archivo tiene 1 línea."""
    try:
        with open(ruta, "rb") as fh:
            datos = fh.read()
    except OSError as exc:
        raise Detener("conteo", f"no se pudo leer un archivo nuevo: {exc}") from exc
    if not datos:
        return 0
    n = datos.count(b"\n")
    return n if datos.endswith(b"\n") else n + 1


def main(argv):
    if argv[1:2] == ["--ancla"]:
        raiz = correr(["git", "rev-parse", "--show-toplevel"], "rev-parse").decode().strip()
        import pathlib
        print(f"esperado={ANCLA_SHA256}")
        actual = hashlib.sha256(seccion_normativa(pathlib.Path(raiz)).encode("utf-8")).hexdigest()
        print(f"actual__={actual}")
        return 0

    if not 1 <= len(argv[1:]) <= 2:
        raise MalUso("medir-techo.py <base> [head]  |  medir-techo.py --ancla")
    base = argv[1]
    head = argv[2] if len(argv) > 2 else None

    import pathlib
    raiz = pathlib.Path(correr(["git", "rev-parse", "--show-toplevel"], "rev-parse").decode().strip())

    for ref in filter(None, (base, head)):
        p = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref], capture_output=True)
        if p.returncode != 0:
            raise MalUso(f"'{ref}' no es una referencia válida")

    actual = hashlib.sha256(seccion_normativa(raiz).encode("utf-8")).hexdigest()
    if actual != ANCLA_SHA256:
        raise Detener(
            "ancla",
            f"la sección normativa de la regla 2 cambió (esperado {ANCLA_SHA256}, actual {actual}): "
            "revisar la fórmula antes de medir",
        )

    # --find-renames explícito: sin él la detección depende de la configuración de quien corra el
    # script, y un rename puro pasa de aportar cero a aportar sus líneas en el destino.
    rango = [base, head] if head else [base]
    diff = correr(["git", "diff", "--numstat", "-z", "--find-renames"] + rango, "diff")
    altas = correr(
        ["git", "diff", "--name-only", "--diff-filter=A", "-z", "--find-renames"] + rango,
        "diff-altas",
    )

    nuevos = b""
    if head is None:
        nuevos = correr(["git", "ls-files", "--others", "--exclude-standard", "-z"], "ls-files")

    def rutas(blob):
        return [r.decode("utf-8", "surrogateescape") for r in blob.split(b"\0") if r]

    filas = list(registros(diff))
    if head is None:
        for r in rutas(nuevos):
            filas.append((contar_lineas(raiz / r), 0, r))

    # El conjunto de archivos nuevos bajo scripts/: las altas del diff, más los untracked SOLO en el
    # modo de árbol de trabajo, deduplicados.
    conjunto = set(rutas(altas))
    if head is None:
        conjunto |= set(rutas(nuevos))
    nuevos_en_scripts = sum(1 for r in conjunto if r.startswith("scripts/"))

    bruto = neto = den = 0
    canal = None
    try:
        canal = open(3, "wb", closefd=False)
    except OSError:
        canal = None
    for add, dele, ruta in filas:
        clase = clasificar(ruta)
        if canal is not None:
            canal.write(f"{clase}\t{add}\t{ruta}".encode("utf-8", "surrogateescape") + b"\0")
        if clase == ANDAMIAJE:
            bruto += add
            neto += max(0, add - dele)
        elif clase == PRODUCTO:
            den += add
    if canal is not None:
        canal.flush()

    num = neto if den > 0 else bruto
    veredicto = "BLOQUEA" if num > den else "PASA"
    print(f"nuevos_en_scripts={nuevos_en_scripts} num={num} den={den} {veredicto}")
    return 1 if num > den else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except MalUso as exc:
        print(f"USO {exc}", file=sys.stderr)
        sys.exit(2)
    except Detener as exc:
        print(f"DETENER {exc}", file=sys.stderr)
        sys.exit(3)
