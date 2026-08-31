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
    medir-techo.test.py --autotest-banda     comprueba que ampliar, destapar o quitar la banda —o
                                             cambiarle el valor— pone rojo algún caso

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

GRUPO `dominio` — los seis casos del criterio de artefactos generados, y qué mutante ejerce cada uno.
Su control positivo es `--autotest-dominio`, que muta **una superficie por vez** conservando el hash del
ancla: un rojo por `punto=ancla` sería el exit code mintiendo sobre la causa, y el arnés lo rechaza.

| Caso | Qué prueba | Mutante que lo pone rojo |
|---|---|---|
| `invariancia-generados` | los seis patrones, en `scripts/` y `skills/`, por las dos vías | `numerador-y-denominador`, `contador` |
| `invariancia-ignore-designora` | des-ignorar localmente no incorpora | — (lo cubre la enumeración versionada) |
| `invariancia-ignore-oculta-legitimo` | ignorar localmente no saca producto ni andamiaje | — (ídem, en la otra dirección) |
| `descarte-artefactos-sdd` | un artefacto de flujo viejo no entra a ningún término | `numerador-y-denominador`, `untracked` |
| `script-nuevo-no-generado` | control inverso: un script escrito sí dispara la señal | — (es el positivo del contador) |
| `ignore-ausente-arbol-y-rango` | el `Detener` es del modo árbol y no del rango | — (rama de ausencia) |

Los cuatro casos sin mutante propio no son huecos: dos comprueban **invariancia frente al entorno**, que
ninguna mutación del descarte altera, y los otros dos son el control inverso y la rama de ausencia. Que
se declare cuál cubre qué es lo que impide contar como cubierto un mutante que su precondición saltea.

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
import re
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


# Los seis patrones del dominio, **literales y no derivados del instrumento**. Generar el fixture
# llamando a `--dominio` haría que un mutante del dominio mutara también el fixture, y el caso quedaría
# verde por comparar el mutante contra sí mismo.
GITIGNORE_FIXTURE = ".DS_Store\n.pytest_cache/\n__pycache__/\ncoverage/\ndist/\nnode_modules/\n"


_TEMPORALES = []


def _limpiar_temporales():
    """Barre los repositorios temporales que quedaron de casos que fallaron.

    La limpieza vive acá y no en cada `caso_*` porque es propiedad de **la corrida**: los 21 casos que
    no se construyen con `_formula` no tenían dónde poner su `finally`, y una corrida de mutantes hace
    fallar casos a propósito. Medido antes de esto: `--autotest-dominio` dejaba 4 directorios y 884 KB
    por corrida, que es justamente el número que el comentario del `finally` nombraba sin cubrir.
    """
    while _TEMPORALES:
        shutil.rmtree(_TEMPORALES.pop(), ignore_errors=True)


def repo(base_claude=True, con_gitignore=True):
    """Un repositorio temporal fuera del árbol, con la sección normativa copiada para que el ancla del
    instrumento coincida. Los fixtures nunca se siembran dentro del repo real: la regla 3 lo prohíbe y
    además contaminaría las mediciones.

    `con_gitignore` existe por la misma razón que `base_claude`: el modo árbol del instrumento **exige**
    el archivo versionado, así que sin él todos los casos de ese modo se detendrían. Y no se crea
    siempre porque entonces la rama de ausencia no se podría ejercer nunca.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="medir-techo-"))
    _TEMPORALES.append(d)
    git(d, "init", "-q", ".")
    git(d, "config", "user.email", "t@t")
    git(d, "config", "user.name", "t")
    if con_gitignore:
        (d / ".gitignore").write_text(GITIGNORE_FIXTURE)
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


PATRONES = [("__pycache__", "x.pyc"), (".pytest_cache", "x"), ("dist", "x"),
            ("coverage", "x"), ("node_modules", "x"), (None, ".DS_Store")]


def _tupla(salida):
    """La tupla completa del resumen. Comparar la tupla y no un fragmento: un caso que solo mire `num`
    no ve que el generado se fue al denominador o al contador."""
    m = re.search(r"nuevos_en_scripts=(\d+) num=(\d+) den=(\d+) (\w+)", salida)
    esperar(m is not None, f"resumen ilegible: {salida}")
    return m.groups()


def caso_invariancia_generados(_):
    """Ninguno de los seis patrones altera la tupla, bajo scripts/ y bajo skills/, por las dos vías."""
    for dire, nombre in PATRONES:
        for superficie in ("scripts", "skills"):
            rel = f"{superficie}/{dire}/{nombre}" if dire else f"{superficie}/{nombre}"
            # vía A — untracked: ejerce la ENUMERACIÓN (el archivo no llega al descarte)
            d = repo()
            escribir(d, "skills/s.md", 3)
            base = commit(d)
            _, limpio, _ = medir(d, base)
            escribir(d, rel, 40)                      # contenido NO vacío: uno vacío no altera nada
            _, con, _ = medir(d, base)
            esperar(_tupla(limpio) == _tupla(con),
                    f"[untracked {rel}] la tupla cambió: {_tupla(limpio)} → {_tupla(con)}")
            shutil.rmtree(d)
            # vía B — forzado al diff: es la ÚNICA que ejerce el descarte, porque el ignore impide que
            # un untracked llegue hasta ahí y `commit()` usa `git add -A`, que no toma ignorados
            d = repo()
            escribir(d, "skills/s.md", 3)
            base = commit(d)
            escribir(d, rel, 40)
            git(d, "add", "-f", rel)
            git(d, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "forzado")
            _, con_b, _ = medir(d, base)
            esperar(_tupla(con_b) == _tupla(limpio),
                    f"[diff {rel}] la tupla cambió: {_tupla(limpio)} → {_tupla(con_b)}")
            shutil.rmtree(d)


def caso_invariancia_ignore_designora(_):
    """Un ignore local que des-ignora un generado no lo incorpora a la cuenta."""
    d = repo()
    escribir(d, "skills/s.md", 3)
    base = commit(d)
    escribir(d, "scripts/__pycache__/x.pyc", 40)
    _, sin, _ = medir(d, base)
    (d / ".git/info/exclude").write_text("!__pycache__/\n")
    _, con, _ = medir(d, base)
    esperar(_tupla(sin) == _tupla(con), f"la config local movió la tupla: {_tupla(sin)} → {_tupla(con)}")
    shutil.rmtree(d)


def caso_invariancia_ignore_oculta_legitimo(_):
    """La SEGUNDA dirección: un ignore local no puede sacar de la cuenta producto ni andamiaje.

    Es la que se olvida, y la que un fixture vacío dejaría sin probar: los dos archivos llevan
    contenido y la tupla esperada exige que ambos aporten observablemente.
    """
    d = repo()
    escribir(d, "skills/viejo.md", 1)
    base = commit(d)
    escribir(d, "skills/nuevo.md", 7)        # producto → denominador
    escribir(d, "scripts/nuevo.py", 5)       # andamiaje → numerador y contador
    _, sin, _ = medir(d, base)
    n, num, den, _v = _tupla(sin)
    esperar((n, num, den) == ("1", "5", "7"),
            f"el fixture no aporta a los tres términos: nuevos={n} num={num} den={den}")
    (d / ".git/info/exclude").write_text("nuevo.md\nnuevo.py\n")
    _, con, _ = medir(d, base)
    esperar(_tupla(sin) == _tupla(con),
            f"un ignore local sacó archivos legítimos: {_tupla(sin)} → {_tupla(con)}")
    shutil.rmtree(d)


def caso_descarte_artefactos_sdd(_):
    """Un artefacto de un flujo viejo no entra a ningún término, ni por el diff.

    La ruta es la clase real medida en el repositorio: un `*.test.*` bajo `.plans/archived/`, que
    `clasificar()` manda a andamiaje y que sin este descarte suma al numerador.
    """
    d = repo()
    escribir(d, "skills/s.md", 3)
    base = commit(d)
    _, limpio, _ = medir(d, base)
    rel = ".plans/archived/x/work/install.test.mjs.before-promotion"
    escribir(d, rel, 60)
    _, untracked, _ = medir(d, base)
    esperar(_tupla(limpio) == _tupla(untracked), f"[untracked] {_tupla(limpio)} → {_tupla(untracked)}")
    git(d, "add", "-f", rel)
    git(d, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "sdd")
    _, en_diff, _ = medir(d, base)
    esperar(_tupla(limpio) == _tupla(en_diff), f"[diff] {_tupla(limpio)} → {_tupla(en_diff)}")
    shutil.rmtree(d)


def caso_script_nuevo_no_generado(_):
    """Control inverso: un archivo nuevo fuera del dominio SIGUE contando y disparando la señal.

    Sin este caso, "los generados no cuentan" se podría implementar silenciando el contador entero y
    todos los demás casos seguirían verdes.
    """
    d = repo()
    escribir(d, "skills/s.md", 3)
    base = commit(d)
    escribir(d, "scripts/nuevo_de_verdad.py", 12)
    _, out, _ = medir(d, base)
    n, num, den, _v = _tupla(out)
    esperar(n == "1", f"esperaba nuevos_en_scripts=1 para un script escrito, dio {n}: {out}")
    esperar(num == "12", f"esperaba num=12, dio {num}: {out}")
    shutil.rmtree(d)


def caso_ignore_ausente_arbol_y_rango(_):
    """Sin archivo de ignore, el modo árbol se detiene y el modo rango NO: no consulta ignores."""
    d = repo(con_gitignore=False)
    escribir(d, "skills/s.md", 3)
    base = commit(d)
    escribir(d, "skills/s.md", 9)
    head = commit(d, "mas")
    rc_arbol, out_arbol, _ = medir(d, base)
    esperar(rc_arbol == DETENIDA, f"el modo árbol debía detenerse, dio {rc_arbol}: {out_arbol}")
    esperar("punto=ls-files" in out_arbol, f"no nombró el punto: {out_arbol}")
    rc_rango, out_rango, _ = medir(d, base, head)
    esperar(rc_rango in (PASA, BLOQUEA), f"el modo rango no debía detenerse, dio {rc_rango}: {out_rango}")
    esperar("den=6" in out_rango, f"el modo rango perdió su resultado: {out_rango}")
    shutil.rmtree(d)


def _formula(nombre, construir, esperado):
    # El código esperado se DERIVA del propio `esperado` en vez de venir por parámetro. Un parámetro
    # obligaría a tocar las ocho llamadas que ya existían y, peor, dejaría declarar un código que
    # contradiga al texto — que es exactamente lo que esta comprobación existe para impedir. Los ocho
    # casos validaban solo el resumen: un cambio que acertara el texto y errara el código pasaba.
    if esperado.endswith("BLOQUEA"):
        rc_esperado = BLOQUEA
    elif esperado.endswith("PASA"):
        rc_esperado = PASA
    else:
        raise ValueError(f"'{esperado}' no termina en PASA ni en BLOQUEA: no se deriva el código")

    def caso(_):
        d = repo()
        try:
            base, head = construir(d)
            rc, out, _ = medir(d, base, *( [head] if head else [] ))
            esperar(esperado in out, f"esperaba '{esperado}', dio '{out}'")
            esperar(rc == rc_esperado, f"esperaba código {rc_esperado} para '{esperado}', dio {rc}: {out}")
        finally:
            # El borrado va en `finally` porque el PROPÓSITO de una corrida de mutantes es que estos
            # `esperar` fallen: con el borrado al final del cuerpo, cada mutante dejaba su repositorio
            # temporal huérfano. Medido antes de esto: 8 directorios y 1,8 MB por corrida de
            # `--autotest-banda`, 4 por la de `--autotest-dominio`.
            shutil.rmtree(d, ignore_errors=True)
    caso.__doc__ = f"Conformidad de la fórmula: {nombre} → {esperado} (código {rc_esperado})"
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


def caso_banda_dos_representaciones(_):
    """El valor de la banda vive en dos sedes —la regla y el instrumento— y este caso las compara.

    Sin él, `--banda` no tiene consumidor durable: la única comparación que existía vivía en la fila de
    un contrato de flujo, que es local y desaparece al archivarlo. Es la forma «guarda que nadie
    invoca», y acá el consumidor queda dentro de la suite.

    Va en el grupo `formula`, que es lo que lo pone bajo `--autotest-banda` —el único disparador
    documentado para un cambio de la banda— y lo deja con control positivo. Estuvo un momento en
    `modos` con el argumento de que en `formula` «barrería» a la frontera `den > 20`, y ese argumento
    era **falso**: `_autotest_mutantes` acumula todos los casos caídos y los reporta juntos, sin cortar
    en el primero, así que el mutante del valor aparece detectado por los dos.
    """
    texto = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")
    declarados = re.findall(r"la banda es de (\d+) líneas", texto)
    esperar(len(declarados) == 1,
            f"la sede normativa debe declarar el valor de la banda exactamente una vez, "
            f"halladas {len(declarados)}")
    # Segunda mitad, y es la que más duele: la FÓRMULA no puede reenunciar el número. Medido, el
    # documento llegó a declararlo siete veces mientras esta guarda veía una sola, así que cambiar
    # `BANDA` y actualizar la línea declarada la dejaba verde con seis enunciaciones viejas.
    formulas = re.findall(r"min\(\s*\d+\s*,\s*denominador\s*\)", texto)
    esperar(not formulas,
            f"la sede normativa no debe reenunciar el valor dentro de la fórmula: {formulas}")
    rc, out, _ = medir(RAIZ, "--banda")
    esperar(rc == PASA, f"--banda debía salir {PASA}, dio {rc}: {out}")
    esperar(out.strip() == declarados[0],
            f"la regla declara {declarados[0]} y el instrumento imprime {out.strip()!r}")


def _banda(altas_andamiaje, altas_producto):
    """Un diff con exactamente `altas_andamiaje` líneas de andamiaje y `altas_producto` de producto.

    Las dos rutas nacen con una línea y crecen por el final, así que `git` las lee como altas puras: el
    numerador queda en el neto por archivo y el denominador en las altas de producto. Es lo que permite
    pedir un par (num, den) exacto y parar justo sobre la frontera de la banda.
    """
    def construir(d):
        escribir(d, "scripts/v.py", 1)
        escribir(d, "skills/s.md", 1)
        b = commit(d)
        escribir(d, "scripts/v.py", 1 + altas_andamiaje)
        escribir(d, "skills/s.md", 1 + altas_producto)
        return b, commit(d, "banda")
    return construir


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
    ("invariancia-generados",            "dominio", caso_invariancia_generados),
    ("invariancia-ignore-designora",     "dominio", caso_invariancia_ignore_designora),
    ("invariancia-ignore-oculta-legitimo", "dominio", caso_invariancia_ignore_oculta_legitimo),
    ("descarte-artefactos-sdd",          "dominio", caso_descarte_artefactos_sdd),
    ("script-nuevo-no-generado",         "dominio", caso_script_nuevo_no_generado),
    ("ignore-ausente-arbol-y-rango",     "dominio", caso_ignore_ausente_arbol_y_rango),
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
    # Las ocho fronteras de la banda. Van en pares —justo dentro y justo fuera— porque solo el par
    # distingue el umbral de un número que casualmente cae del lado correcto. Y van en CUATRO
    # denominadores porque la banda tiene dos ramas y `den=20` es el punto de EMPATE, no el corte:
    # con `den` en {1, 19, 20} siempre vale `min(BANDA, den) == den`, así que la fórmula se reduce a
    # `num > 2*den` y una banda plana es indistinguible de una acotada. Medido: con `BANDA = 1000`, o
    # con el predicado `num > den + den`, los seis primeros casos seguían dando `35 casos ok`. El par
    # con `den=25` es el único que ata el VALOR de la banda, y por eso es el que puede ponerse rojo
    # cuando cambia.
    ("banda-exceso-20",             "formula", _formula("exceso de 20 con den=20", _banda(40, 20), "num=40 den=20 PASA")),
    ("banda-exceso-21",             "formula", _formula("exceso de 21 con den=20", _banda(41, 20), "num=41 den=20 BLOQUEA")),
    ("banda-den1-exceso1",          "formula", _formula("exceso de 1 con den=1", _banda(2, 1), "num=2 den=1 PASA")),
    ("banda-den1-exceso2",          "formula", _formula("exceso de 2 con den=1", _banda(3, 1), "num=3 den=1 BLOQUEA")),
    ("banda-den19-exceso19",        "formula", _formula("exceso de 19 con den=19", _banda(38, 19), "num=38 den=19 PASA")),
    ("banda-den19-exceso20",        "formula", _formula("exceso de 20 con den=19", _banda(39, 19), "num=39 den=19 BLOQUEA")),
    ("banda-den25-exceso20",        "formula", _formula("exceso de 20 con den=25", _banda(45, 25), "num=45 den=25 PASA")),
    ("banda-den25-exceso21",        "formula", _formula("exceso de 21 con den=25", _banda(46, 25), "num=46 den=25 BLOQUEA")),
    ("banda-dos-representaciones",  "formula", caso_banda_dos_representaciones),
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
    _limpiar_temporales()              # un caso que falla no llega a borrar su repositorio
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


# Un mutante por superficie del descarte. Las tres son distintas y ninguna cubre a las otras: el
# descarte del diff alimenta numerador y denominador, el de los untracked alimenta el numerador por la
# otra vía, y el del conjunto alimenta el contador de archivos nuevos.
MUTANTES_DOMINIO = [
    ("numerador-y-denominador",
     "filas = [f for f in registros(diff) if not generado(f[2])]",
     "filas = list(registros(diff))"),
    ("untracked",
     "            if not generado(r):",
     "            if True:"),
    ("contador",
     "conjunto = {r for r in rutas(altas) if not generado(r)}",
     "conjunto = set(rutas(altas))"),
]

# **Por qué el mutante del contador apunta a las ALTAS y no a los untracked.** La primera versión mutaba
# `conjunto |= {r for r in rutas(nuevos) …}` y **ningún caso lo detectaba**; el arnés lo reportó en vez de
# darlo por cubierto. La causa es real y no del arnés: con el archivo de ignore sincronizado, un cache
# untracked no aparece en `ls-files`, y los artefactos SDD —que sí aparecen, porque el ignore no los
# cubre— nunca viven bajo `scripts/`. Esa línea es inalcanzable **para el contador**, así que mutarla no
# puede poner nada rojo. La superficie que sí lo gobierna de forma observable es el descarte de las altas
# del diff, que la vía forzada de `invariancia-generados` ejerce. La línea de untracked se conserva en el
# instrumento —es correcta y barata— pero no se pretende cubrirla con un mutante que no puede caer.


def _autotest_mutantes(etiqueta, grupo, mutantes):
    """Motor común de los dos controles positivos: muta el instrumento una superficie por vez y exige
    que algún caso del grupo se ponga rojo.

    Dos condiciones lo vuelven un control y no un adorno. **El hash del ancla se conserva**: se muta el
    código y nunca `CLAUDE.md`, así que un rojo por `punto=ancla` sería el exit code mintiendo sobre la
    causa y acá se rechaza explícitamente. Y **se reporta qué caso cayó** por cada mutante: uno cuya
    precondición ningún caso ejerce daría verde y se leería como cobertura.

    Es uno y no dos porque las dos versiones anteriores compartían 35 de sus 50 líneas y solo diferían
    en el grupo, la lista de mutantes y tres etiquetas: dos sedes que podían divergir sin que nada lo
    detectara, y ~35 líneas que el techo de la regla 2 contaba en el numerador.
    """
    global INSTRUMENTO
    casos = [c for c in CASOS if c[1] == grupo]
    if not casos:
        print(f"{etiqueta}: FALLA — no hay casos en el grupo '{grupo}'", file=sys.stderr)
        return 4
    fuente = INSTRUMENTO.read_text(encoding="utf-8")
    problemas = []
    for nombre, viejo, nuevo in mutantes:
        if callable(viejo):
            derivado = viejo(fuente)
            if derivado is None:
                problemas.append(f"{nombre}: no se pudo derivar el mutante de la fuente — la constante "
                                 "no tiene la forma esperada")
                continue
            viejo, nuevo = derivado
        if fuente.count(viejo) != 1:
            problemas.append(f"{nombre}: el ancla del mutante aparece {fuente.count(viejo)} veces, "
                             "no 1 — el mutante no se puede aplicar donde se cree")
            continue
        tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"mutante-{grupo}-"))
        copia = tmp / "medir-techo.py"
        copia.write_text(fuente.replace(viejo, nuevo, 1), encoding="utf-8")
        original, INSTRUMENTO = INSTRUMENTO, copia
        caidos, por_ancla = [], []
        for cid, _g, fn in casos:
            try:
                fn(None)
            except Diverge as exc:
                (por_ancla if "punto=ancla" in str(exc) else caidos).append(cid)
            except Exception as exc:                     # noqa: BLE001 — cualquier fallo cuenta
                caidos.append(f"{cid}({type(exc).__name__})")
        INSTRUMENTO = original
        shutil.rmtree(tmp, ignore_errors=True)
        _limpiar_temporales()          # los casos caen a propósito acá: sus fixtures no se borran solos
        if por_ancla:
            problemas.append(f"{nombre}: cayó por punto=ancla ({por_ancla}) — el rojo no vino del "
                             "criterio; el hash debía conservarse")
        if not caidos:
            problemas.append(f"{nombre}: NINGÚN caso lo detectó — su precondición no se ejerce")
        else:
            print(f"mutante {nombre}: detectado por {caidos}")
    if problemas:
        for p in problemas:
            print(f"{etiqueta}: FALLA — {p}", file=sys.stderr)
        return 4
    print(f"{etiqueta}: {len(mutantes)} mutantes, los {len(mutantes)} detectados")
    return 0


def autotest_dominio():
    """Control positivo del criterio: cada superficie del descarte, mutada por separado, tiene que
    poner rojo a algún caso del grupo `dominio`."""
    return _autotest_mutantes("autotest-dominio", "dominio", MUTANTES_DOMINIO)


def _mutante_valor_banda(fuente):
    """Deriva el mutante de la constante a partir del valor que el instrumento declara hoy.

    Devuelve el par (viejo, nuevo) o `None` si la constante no se encuentra con la forma esperada, que
    `_autotest_mutantes` reporta como problema en vez de confundirlo con un mutante inaplicable.

    **Al cambiar `BANDA` hay que mover también la frontera `banda-den25-*`**, que existe para estar por
    ENCIMA de la banda: con `BANDA >= 25` deja de ser la que ata el valor. Los casos se ponen rojos al
    cambiar la constante, así que el cambio no pasa inadvertido, pero el arreglo correcto es subir la
    frontera y no relajar la expectativa.
    """
    m = re.search(r"^BANDA = (\d+)$", fuente, re.M)
    if not m:
        return None
    return (f"BANDA = {m.group(1)}", f"BANDA = {int(m.group(1)) + 1}")


MUTANTES_BANDA = [
    # Los tres primeros anclan la LÍNEA COMPLETA del predicado y no `min(BANDA, den)` a secas: ese texto vive
    # también en un comentario y en el docstring del instrumento, así que un ancla corta mutaría prosa
    # y daría un verde por vacuidad. El propio autotest exige que aparezca una sola vez.
    ("banda-sin-cota",
     "    bloquea = num > den + (min(BANDA, den) if den > 0 else 0)",
     "    bloquea = num > den + (max(BANDA, den) if den > 0 else 0)"),
    ("banda-mas-ancha",
     "    bloquea = num > den + (min(BANDA, den) if den > 0 else 0)",
     "    bloquea = num > den + (min(BANDA, den) + 1 if den > 0 else 0)"),
    # Los dos de arriba solo AMPLÍAN, así que solo los casos del lado BLOQUEA pueden detectarlos y el
    # lado PASA nunca llega a ser detector. Este la quita del todo —la regresión exacta que este cambio
    # previene— y lo detectan los tres del lado PASA. Sin él, el control positivo cubre media banda.
    ("banda-quitada",
     "    bloquea = num > den + (min(BANDA, den) if den > 0 else 0)",
     "    bloquea = num > den"),
    # Este muta la CONSTANTE, que los tres de arriba no tocaban: sin él el control positivo no podía
    # ponerse rojo por el NÚMERO —que la regla 2 declara como una de sus dos representaciones—. Medido:
    # con `BANDA = 1000` la suite daba `35 casos ok` y el autotest imprimía `3 de 3`.
    # Su ancla se DERIVA del valor vigente y no se escribe literal: anclado a `BANDA = 20`, un cambio
    # querido del valor hacía fallar el autotest con «el ancla del mutante aparece 0 veces», que es un
    # diagnóstico que miente sobre la causa. Medido con `BANDA = 25`.
    ("banda-otro-valor", _mutante_valor_banda, None),
]


def autotest_banda():
    """Control positivo de la banda: ampliarla, destaparla, quitarla o cambiarle el valor tiene que
    poner rojo a algún caso del grupo `formula`."""
    return _autotest_mutantes("autotest-banda", "formula", MUTANTES_BANDA)


def main(argv):
    if "--autotest-banda" in argv:
        return autotest_banda()
    if "--autotest-dominio" in argv:
        return autotest_dominio()
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
