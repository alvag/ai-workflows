#!/usr/bin/env python3
"""Suite del instrumento `medir-techo.py`.

INVENTARIO AUTOCONTENIDO. Cada caso declara acá su identificador, cómo se construye su fixture y qué
resultado se espera. No remite a ningún otro archivo ni flujo: una suite que hay que leer con otro
documento al lado no se puede auditar sola.

Uso:
    medir-techo.test.py                      corre todos los casos
    medir-techo.test.py --caso ID [--caso ID]  corre los nombrados
    medir-techo.test.py --grupo G            corre un grupo (formula | fallos | modos | rutas)
    medir-techo.test.py --listar             imprime el inventario y el mapeo de defectos
    medir-techo.test.py --autotest           comprueba que la suite se pone roja al quitar un caso

Salida: una línea por caso —`caso ID: ok` o `caso ID: DIVERGE …`— y un cierre `N casos ok`.
Una selección vacía **falla**: si no, un identificador mal escrito daría verde sin ejercer nada.

LOS DOCE DEFECTOS QUE CUBRE, y el caso que cubre cada uno. Los doce se encontraron ejecutando el
instrumento —ninguno leyéndolo— a lo largo de tres flujos:

     1. path de rename en sintaxis de llaves, no matcheaba la extensión ......... rename-puro
     2. `exit 3` en awk igual ejecuta el END: imprimía DETENER y después PASA ... binario
     3. contador incrementado en un subshell, no salía de él .................... resumen-y-codigos
     4. `wc -l` da 0 en un archivo sin salto de línea final .................... untracked-sin-salto
     5. el path se partía por whitespace y se clasificaba por su primer trozo ... nombre-con-tab
     6. la función sobrescribía la base con su argumento: medía el árbol ........ modo-rango
     7. el pipeline fallaba abierto: git moría y el veredicto era PASA ......... fallo-diff
     8. no aceptaba un rango: el caso 2 nunca se había medido con el instrumento  modo-rango
     9. `nuevos` contaba solo untracked y omitía un alta ya trackeada .......... nuevos-union
    10. exits internos sin validar, y `|| true` tapando un error de lectura .... fallo-conteo
    11. la detección de renames dependía de la config del entorno ............. rename-sin-deteccion
    12. el parseo por tabulador se rompe con un tabulador en el nombre ........ nombre-con-tab

DESVIACIÓN DECLARADA respecto de AC-5. El criterio enumeraba cinco puntos de fallo —diff, enumeración
de untracked, creación del área temporal, cada escritura a ella, y conteo—, y esa lista describía el
instrumento cuando iba a ser un script de shell. La implementación es Python y **no crea área
temporal**, así que dos de esos cinco puntos no existen. Los cinco puntos inyectables que sí tiene son
`rev-parse`, `diff`, `diff-altas`, `ls-files` y `conteo`; los otros tres que puede cortar —`ancla`,
`parseo` y `fila_no_numerica`— los ejercen `divergencia-normativa` y `binario`. El requisito de fondo
no cambió: todo punto de fallo corta con el código de corte y nombra su punto.
"""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
INSTRUMENTO = pathlib.Path(os.environ.get("MEDIR_TECHO_BIN",
                                          RAIZ / "scripts" / "medir-techo.py"))
# MEDIR_TECHO_BIN permite apuntar a una COPIA mutada del instrumento, que es la única forma de
# comprobar que un caso puede ponerse rojo. Se muta la copia y nunca el archivo del árbol: si el
# proceso muere a mitad de camino, el repositorio no queda con el instrumento roto.

PASA, BLOQUEA, INVOCACION, DETENIDA = 0, 1, 2, 3


class Diverge(Exception):
    pass


def git(cwd, *args, env=None):
    p = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, env=env)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.decode('utf-8', 'replace')[:200]}")
    return p.stdout


def medir(cwd, *args, env=None, capturar_canal=False):
    """Corre el instrumento y devuelve (codigo, resumen, rutas_del_canal_3).

    El canal 3 se redirige con un `sh -c 'exec 3>archivo'` y no con `pass_fds`: el descriptor que
    devuelve un temporal casi nunca es el 3, así que pasarlo tal cual dejaba la captura al azar — y con
    ella, cualquier comprobación sobre el canal.
    """
    entorno = dict(os.environ)
    if env:
        entorno.update(env)
    cmd = [sys.executable, str(INSTRUMENTO)] + list(args)
    if not capturar_canal:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, env=entorno,
                           stdin=subprocess.DEVNULL)
        salida = p.stdout.decode("utf-8", "replace").strip() or \
            p.stderr.decode("utf-8", "replace").strip()
        return p.returncode, salida, b""

    destino = pathlib.Path(tempfile.mkdtemp(prefix="canal3-")) / "rutas.bin"
    envoltorio = 'exec 3>"$1"; shift; exec "$@"'
    p = subprocess.run(["sh", "-c", envoltorio, "_", str(destino)] + cmd,
                       cwd=cwd, capture_output=True, env=entorno, stdin=subprocess.DEVNULL)
    rutas = destino.read_bytes() if destino.exists() else b""
    shutil.rmtree(destino.parent, ignore_errors=True)
    salida = p.stdout.decode("utf-8", "replace").strip() or \
        p.stderr.decode("utf-8", "replace").strip()
    return p.returncode, salida, rutas


def esperar(cond, detalle):
    if not cond:
        raise Diverge(detalle)


def repo(base_claude=True):
    """Un repositorio temporal fuera del árbol, con la sección normativa copiada para que el ancla del
    instrumento coincida. Los fixtures nunca se siembran dentro del repo real: la regla 3 lo prohíbe y
    además contaminaría las mediciones."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="medir-techo-"))
    git(d, "init", "-q", ".")
    git(d, "config", "user.email", "t@t")
    git(d, "config", "user.name", "t")
    if base_claude:
        shutil.copy(RAIZ / "CLAUDE.md", d / "CLAUDE.md")
    (d / "scripts").mkdir(exist_ok=True)
    (d / "skills").mkdir(exist_ok=True)
    return d


def commit(d, msg="c"):
    git(d, "add", "-A")
    git(d, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", msg)
    return git(d, "rev-parse", "HEAD").decode().strip()


def escribir(d, rel, lineas, con_salto_final=True):
    p = d / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    texto = "".join(f"l{i}\n" for i in range(lineas))
    if not con_salto_final and texto:
        texto = texto[:-1]
    p.write_bytes(texto.encode())
    return p


def stub_git_que_falla(subcomando):
    """Un `git` falso, primero en el PATH, que falla SOLO en un subcomando. Es lo que permite inyectar
    un fallo en cada punto sin romper el resto de la medición."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="stub-git-"))
    real = shutil.which("git")
    (d / "git").write_text(
        "#!/bin/sh\n"
        f'for a in "$@"; do case "$a" in {subcomando}) '
        f'echo "fatal: fallo inyectado en {subcomando}" >&2; exit 128;; esac; done\n'
        f'exec {real} "$@"\n'
    )
    (d / "git").chmod(0o755)
    return d


# ─────────────────────────────── los casos ───────────────────────────────

def caso_resumen_y_codigos(_):
    """La línea de resumen tiene los cuatro campos y ninguna ruta, y los tres códigos se distinguen."""
    d = repo()
    escribir(d, "skills/s.md", 1)
    base = commit(d)
    escribir(d, "skills/s.md", 3)
    rc, out, _ = medir(d, base)
    esperar(rc == PASA, f"esperaba exit {PASA}, dio {rc}: {out}")
    for campo in ("nuevos_en_scripts=", "num=", "den=", "PASA"):
        esperar(campo in out, f"falta '{campo}' en el resumen: {out}")
    esperar("\n" not in out, f"el resumen no es de una línea: {out!r}")
    esperar("/" not in out, f"el resumen nombra una ruta y no debe: {out}")
    escribir(d, "scripts/v.py", 50)
    rc2, out2, _ = medir(d, base)
    esperar(rc2 == BLOQUEA, f"esperaba exit {BLOQUEA}, dio {rc2}: {out2}")
    rc3, out3, _ = medir(d)
    esperar(rc3 == INVOCACION, f"sin argumentos esperaba {INVOCACION}, dio {rc3}: {out3}")
    shutil.rmtree(d)


def caso_nombre_con_tab(_):
    """Un tabulador en el nombre: se clasifica por la ruta completa, no por su primer trozo.

    El archivo se **commitea**, así que la ruta llega por el parseo del diff. Ejercer la vía de
    untracked en su lugar dejaría el caso sin poder ponerse rojo: un mutante en el parseo del diff no
    se activaría nunca. Se comprobó mutando una copia del instrumento — con la vía de untracked el caso
    daba verde contra el mutante.
    """
    d = repo()
    escribir(d, "skills/s.md", 1)
    base = commit(d)
    (d / "skills" / "con\ttab.py").write_bytes(b"a\nb\n")
    head = commit(d, "tab")
    rc, out, rutas = medir(d, base, head, capturar_canal=True)
    esperar("\n" not in out, f"el resumen se partió por el nombre: {out!r}")
    esperar("/" not in out, f"el resumen nombra una ruta y no debe: {out}")
    # El canal 3 trae la ruta entera con su tabulador, clasificada como producto: empieza con
    # `skills/`, y un parseo por whitespace la habría clasificado por `skills/con`.
    registros = [r for r in rutas.split(b"\0") if r]
    esperar(registros, "el canal 3 no trajo ningún registro")
    hallado = [r for r in registros if b"con\ttab.py" in r]
    esperar(hallado, f"el canal 3 no trae la ruta con su tabulador: {registros!r}")
    esperar(hallado[0].startswith(b"producto\t"),
            f"la ruta con tabulador se clasificó mal: {hallado[0]!r}")
    shutil.rmtree(d)


def caso_nombre_con_salto(_):
    """Un salto de línea en el nombre: el resumen sigue siendo de una línea."""
    d = repo()
    escribir(d, "skills/s.md", 1)
    base = commit(d)
    (d / "skills" / "con\nsalto.py").write_bytes(b"a\nb\n")
    rc, out, _ = medir(d, base)
    esperar(rc in (PASA, BLOQUEA), f"esperaba un veredicto, dio {rc}: {out}")
    esperar("\n" not in out, f"el resumen se partió por el nombre: {out!r}")
    shutil.rmtree(d)


def caso_nuevos_union(_):
    """El conteo de nuevos bajo scripts/ toma las altas del diff Y los untracked, deduplicados."""
    d = repo()
    escribir(d, "skills/s.md", 1)
    base = commit(d)
    escribir(d, "scripts/ya-trackeado.py", 3)
    commit(d, "alta")
    escribir(d, "scripts/sin-trackear.py", 2)
    rc, out, _ = medir(d, base)
    esperar("nuevos_en_scripts=2" in out, f"esperaba 2 nuevos (uno trackeado, uno no): {out}")
    shutil.rmtree(d)


def caso_rename_sin_deteccion(_):
    """El veredicto de un rename puro no cambia con la detección desactivada por invocación."""
    d = repo()
    escribir(d, "scripts/v.py", 10)
    escribir(d, "skills/s.md", 20)
    base = commit(d)
    git(d, "mv", "scripts/v.py", "scripts/w.py")
    commit(d, "mv")
    rc_a, out_a, _ = medir(d, base, "HEAD")
    env = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "diff.renames", "GIT_CONFIG_VALUE_0": "false"}
    rc_b, out_b, _ = medir(d, base, "HEAD", env=env)
    esperar(out_a == out_b, f"el veredicto cambió con la detección apagada:\n  con: {out_a}\n  sin: {out_b}")
    shutil.rmtree(d)


def caso_divergencia_normativa(_):
    """Si la sección normativa cambió, el instrumento se detiene en vez de calcular."""
    d = repo()
    escribir(d, "skills/s.md", 1)
    base = commit(d)
    texto = (d / "CLAUDE.md").read_text()
    marcado = texto.replace("### Regla 2", "### Regla 2 MODIFICADA", 1)
    esperar(marcado != texto, "no se pudo modificar la sección normativa del fixture")
    (d / "CLAUDE.md").write_text(marcado)
    rc, out, _ = medir(d, base)
    esperar(rc == DETENIDA, f"esperaba {DETENIDA} por divergencia, dio {rc}: {out}")
    esperar("punto=ancla" in out, f"no nombró el punto: {out}")
    shutil.rmtree(d)


def caso_untracked_sin_salto(_):
    """Un archivo nuevo cuya última línea no termina en salto cuenta 1, no 0."""
    d = repo()
    escribir(d, "skills/s.md", 1)
    base = commit(d)
    escribir(d, "scripts/una.py", 1, con_salto_final=False)
    rc, out, _ = medir(d, base)
    esperar("num=1 " in out, f"esperaba num=1 para un archivo de una línea sin salto final: {out}")
    shutil.rmtree(d)


def _fallo(punto, subcomando, prepara=None):
    def caso(_):
        d = repo()
        escribir(d, "skills/s.md", 1)
        base = commit(d)
        if prepara:
            prepara(d)
        stub = stub_git_que_falla(subcomando)
        env = {"PATH": f"{stub}:{os.environ['PATH']}"}
        rc, out, _ = medir(d, base, env=env)
        esperar(rc == DETENIDA, f"esperaba {DETENIDA}, dio {rc}: {out}")
        esperar(f"punto={punto}" in out, f"esperaba 'punto={punto}' en la salida: {out}")
        shutil.rmtree(d); shutil.rmtree(stub)
    caso.__doc__ = f"Un fallo inyectado en {punto} corta con {DETENIDA} y nombra su punto."
    return caso


def caso_fallo_conteo(_):
    """Un archivo nuevo ilegible corta en el conteo, no se cuenta como cero."""
    d = repo()
    escribir(d, "skills/s.md", 1)
    base = commit(d)
    p = escribir(d, "scripts/ilegible.py", 3)
    p.chmod(0o000)
    rc, out, _ = medir(d, base)
    p.chmod(0o644)
    esperar(rc == DETENIDA, f"esperaba {DETENIDA} por archivo ilegible, dio {rc}: {out}")
    esperar("punto=conteo" in out, f"no nombró el punto: {out}")
    shutil.rmtree(d)


def caso_modo_arbol(_):
    """Con un argumento se mide contra el árbol y SÍ se suman los untracked."""
    d = repo()
    escribir(d, "skills/s.md", 1)
    base = commit(d)
    escribir(d, "scripts/nuevo.py", 7)
    rc, out, _ = medir(d, base)
    esperar("num=7" in out, f"esperaba que sumara el untracked: {out}")
    shutil.rmtree(d)


def caso_modo_rango(_):
    """Con dos argumentos se mide el rango y NO se suman los untracked."""
    d = repo()
    escribir(d, "skills/s.md", 1)
    base = commit(d)
    escribir(d, "skills/s.md", 5)
    head = commit(d, "dos")
    escribir(d, "scripts/no-debe-contar.py", 99)
    rc, out, _ = medir(d, base, head)
    esperar("num=0" in out, f"el modo rango no debe sumar untracked: {out}")
    esperar("nuevos_en_scripts=0" in out, f"tampoco debe contarlos como nuevos: {out}")
    shutil.rmtree(d)


def _formula(nombre, construir, esperado):
    def caso(_):
        d = repo()
        base, head = construir(d)
        rc, out, _ = medir(d, base, *( [head] if head else [] ))
        esperar(esperado in out, f"esperaba '{esperado}', dio '{out}'")
        shutil.rmtree(d)
    caso.__doc__ = f"Conformidad de la fórmula: {nombre} → {esperado}"
    return caso


def _reordenamiento(d):
    escribir(d, "scripts/cat.json", 20)
    escribir(d, "skills/s.md", 1)
    b = commit(d)
    escribir(d, "scripts/cat.json", 20)          # mismo tamaño: reescritura
    (d / "scripts/cat.json").write_text("".join(f"x{i}\n" for i in range(20)))
    escribir(d, "skills/s.md", 4)
    return b, commit(d, "reord")

def _crecimiento(d):
    escribir(d, "scripts/v.py", 5)
    b = commit(d)
    escribir(d, "scripts/v.py", 55)
    return b, commit(d, "crece")

def _reemplazo(d):
    escribir(d, "scripts/v.py", 30)
    b = commit(d)
    (d / "scripts/v.py").write_text("".join(f"y{i}\n" for i in range(30)))
    return b, commit(d, "reemplaza")

def _igualdad(d):
    escribir(d, "scripts/v.py", 1)
    escribir(d, "skills/s.md", 1)
    b = commit(d)
    escribir(d, "scripts/v.py", 2)
    escribir(d, "skills/s.md", 2)
    return b, commit(d, "igual")

def _untracked_nuevo(d):
    escribir(d, "skills/s.md", 1)
    b = commit(d)
    escribir(d, "scripts/nuevo.py", 7)
    return b, None

def _borrado(d):
    escribir(d, "scripts/v.py", 40)
    b = commit(d)
    git(d, "rm", "-q", "scripts/v.py")
    return b, commit(d, "borra")

def _rename(d):
    escribir(d, "scripts/v.py", 12)
    b = commit(d)
    git(d, "mv", "scripts/v.py", "scripts/w.py")
    return b, commit(d, "mv")

def _binario(d):
    escribir(d, "scripts/a.py", 1)
    b = commit(d)
    (d / "scripts/b.bin").write_bytes(bytes([0, 1, 2, 3]))
    return b, commit(d, "bin")

def _segunda_sede(d):
    escribir(d, "scripts/v.py", 1)
    b = commit(d)
    escribir(d, ".agents/skills/x/SKILL.md", 1)
    escribir(d, "scripts/v.py", 2)
    return b, commit(d, "ag")


def caso_binario(_):
    """Un binario en el diff detiene la medición y NO imprime un veredicto después."""
    d = repo()
    base, head = _binario(d)
    rc, out, _ = medir(d, base, head)
    esperar(rc == DETENIDA, f"esperaba {DETENIDA}, dio {rc}: {out}")
    esperar("punto=fila_no_numerica" in out, f"no nombró el punto: {out}")
    esperar("PASA" not in out and "BLOQUEA" not in out,
            f"imprimió un veredicto además de detenerse: {out}")
    shutil.rmtree(d)


CASOS = [
    ("resumen-y-codigos",     "rutas",   caso_resumen_y_codigos),
    ("nombre-con-tab",        "rutas",   caso_nombre_con_tab),
    ("nombre-con-salto",      "rutas",   caso_nombre_con_salto),
    ("nuevos-union",          "rutas",   caso_nuevos_union),
    ("untracked-sin-salto",   "rutas",   caso_untracked_sin_salto),
    ("rename-sin-deteccion",  "rutas",   caso_rename_sin_deteccion),
    ("divergencia-normativa", "rutas",   caso_divergencia_normativa),
    ("fallo-rev-parse",       "fallos",  _fallo("rev-parse", "rev-parse")),
    ("fallo-diff",            "fallos",  _fallo("diff", "--numstat")),
    ("fallo-diff-altas",      "fallos",  _fallo("diff-altas", "--diff-filter=A")),
    ("fallo-ls-files",        "fallos",  _fallo("ls-files", "ls-files")),
    ("fallo-conteo",          "fallos",  caso_fallo_conteo),
    ("modo-arbol",            "modos",   caso_modo_arbol),
    ("modo-rango",            "modos",   caso_modo_rango),
    ("reordenamiento-con-producto", "formula", _formula("reordenamiento con producto", _reordenamiento, "num=0 den=3 PASA")),
    ("crecimiento-sin-producto",    "formula", _formula("crecimiento sin producto", _crecimiento, "num=50 den=0 BLOQUEA")),
    ("reemplazo-neto-cero",         "formula", _formula("reemplazo con neto cero", _reemplazo, "num=30 den=0 BLOQUEA")),
    ("igualdad",                    "formula", _formula("numerador igual al denominador", _igualdad, "num=1 den=1 PASA")),
    ("untracked-nuevo",             "formula", _formula("untracked nuevo", _untracked_nuevo, "num=7 den=0 BLOQUEA")),
    ("borrado-entero",              "formula", _formula("borrado entero", _borrado, "num=0 den=0 PASA")),
    ("rename-puro",                 "formula", _formula("rename puro", _rename, "num=0 den=0 PASA")),
    ("binario",                     "formula", caso_binario),
    ("producto-segunda-sede",       "formula", _formula("producto en la segunda sede", _segunda_sede, "num=1 den=1 PASA")),
]

DEFECTOS = {
    1: "rename-puro", 2: "binario", 3: "resumen-y-codigos", 4: "untracked-sin-salto",
    5: "nombre-con-tab", 6: "modo-rango", 7: "fallo-diff", 8: "modo-rango",
    9: "nuevos-union", 10: "fallo-conteo", 11: "rename-sin-deteccion", 12: "nombre-con-tab",
}


def listar():
    print(f"inventario: {len(CASOS)} casos")
    for cid, grupo, fn in CASOS:
        doc = (fn.__doc__ or "").strip().split("\n")[0]
        print(f"  {cid:<28} [{grupo}] {doc}")
    print(f"\nmapeo de los {len(DEFECTOS)} defectos:")
    for n in sorted(DEFECTOS):
        print(f"  defecto {n:>2} -> {DEFECTOS[n]}")
    faltan = [c for c in DEFECTOS.values() if c not in {x[0] for x in CASOS}]
    if faltan:
        print(f"\nERROR: el mapeo nombra casos que no existen: {faltan}")
        return 1
    return 0


def correr(seleccion):
    if not seleccion:
        print("ERROR: la selección quedó vacía; un identificador mal escrito no puede dar verde",
              file=sys.stderr)
        return 1
    fallos = 0
    for cid, _grupo, fn in seleccion:
        try:
            fn(None)
            print(f"caso {cid}: ok")
        except Diverge as exc:
            print(f"caso {cid}: DIVERGE {exc}")
            fallos += 1
        except Exception as exc:  # un error de la propia suite no puede leerse como caso verde
            print(f"caso {cid}: ERROR-SUITE {type(exc).__name__}: {exc}")
            fallos += 1
    print(f"{len(seleccion) - fallos} casos ok" + (f", {fallos} con problema" if fallos else ""))
    return 1 if fallos else 0


def autotest():
    """Quitar un caso tiene que poner la suite roja. Sin esto, una suite que no ejerce nada es
    indistinguible de una que pasa."""
    original = list(CASOS)
    try:
        CASOS.clear()
        rc_vacio = correr(list(CASOS))
        if rc_vacio == 0:
            print("autotest: FALLA — con la selección vacía la suite dio verde", file=sys.stderr)
            return 1
    finally:
        CASOS.extend(original)
    # y un caso alterado para que su esperado no se cumpla
    cid, grupo, fn = CASOS[0]
    def roto(_):
        raise Diverge("alterado a propósito por el autotest")
    rc_roto = correr([(cid, grupo, roto)])
    if rc_roto == 0:
        print("autotest: FALLA — un caso alterado no puso roja la suite", file=sys.stderr)
        return 1
    print("autotest: la suite se puso roja al quitar un caso")
    return 0


def main(argv):
    if "--listar" in argv:
        return listar()
    if "--autotest" in argv:
        return autotest()
    ids, grupos = [], []
    i = 0
    while i < len(argv):
        if argv[i] == "--caso" and i + 1 < len(argv):
            ids.append(argv[i + 1]); i += 2
        elif argv[i] == "--grupo" and i + 1 < len(argv):
            grupos.append(argv[i + 1]); i += 2
        else:
            print(f"USO argumento no reconocido: {argv[i]}", file=sys.stderr)
            return 2
    if not ids and not grupos:
        return correr(list(CASOS))
    seleccion = [c for c in CASOS if c[0] in ids or c[1] in grupos]
    desconocidos = set(ids) - {c[0] for c in CASOS}
    if desconocidos:
        print(f"USO casos desconocidos: {sorted(desconocidos)}", file=sys.stderr)
        return 2
    return correr(seleccion)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
