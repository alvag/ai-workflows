#!/usr/bin/env python3
"""Hace cumplir los invariantes que cada punto de despacho declara, en los dos momentos en que son
comprobables.

LA SEDE NORMATIVA DE LOS ENUMS ES `skills/cross-review/corridas-en-vuelo.md`, NO ESTE ARCHIVO. Acá se
los **lee** de su tabla delimitada; duplicarlos en el código crearía una segunda sede que puede
divergir en silencio. Es el mismo recurso que usa el verificador de aislamiento con su política.

Existe porque el adaptador de terminales hacía cumplir cuatro invariantes como **efecto secundario de
lanzar**, y al delegar el transporte a la skill de la plataforma ese efecto desaparece. Dos de los
cuatro son comprobables antes de lanzar y dos solo después, y por eso hay dos modos y no uno.

Uso:
    despacho.py --preflight <raiz> <skill> <punto> <composicion.json>
    despacho.py --corrida   <raiz> <skill> <punto> <sobre.json>
    despacho.py --autotest

Códigos de salida, iguales en los dos modos:
    0  la composición satisface lo que el punto declara
    1  violación, con su nombre del vocabulario vigente en stdout
    2  invocación mal formada
    3  una sede no se pudo leer — NO es un veredicto

FRONTERA DE PRUEBA — dos unidades comparten este pasaje, y no comparten su alcance.

`despacho.py --preflight` — clase: veredicto. Dirección: admite-de-mas.
    Detecta: una fila ausente o con una celda fuera de su enum; dos workers de la misma familia donde
    el punto exige una por worker; digests previstos que no satisfacen la relación declarada; y, de
    la cardinalidad, SOLO el valor `1`.
    NO detecta, y las tres ausencias tienen la MISMA causa —el dato contra el que se comprobaría no
    viaja en la composición— así que ninguna se repara con un predicado mejor:
      · CARDINALIDAD, en los otros cinco valores del enum —`1-por-familia`, `1-por-ronda`,
        `1-por-repo`, `1-por-hallazgo`, `n-acotado`—: el número que cada uno exige sale de las
        familias del inventario, las rondas, los repos del reparto o los hallazgos. Medido: un
        fan-out dual con UN worker previsto, sobre un inventario de dos familias, sale 0.
      · FAMILIAS, en cuatro de sus cinco valores. Solo `una-por-worker` se hace cumplir.
        `opuesta-al-conductor` y `misma-que-el-conductor` necesitan la familia del CONDUCTOR, que
        este modo no recibe; `continuacion-del-anterior` necesita el intento previo; `indiferente`
        no tiene nada que comprobar y su silencio es correcto. Medido: dos workers de la misma
        familia sobre una fila que declara `opuesta-al-conductor` salen `composicion-valida` 0.
      · ENCARGOS, en `delta-sobre-el-anterior`: sin el encargo anterior no hay delta que evaluar.
    NO detecta nada de lo que pasa DESPUÉS de correr: es previo a crear recursos por contrato, así
    que no puede ver un despacho, ni su orden, ni su vencimiento real.
    Su verde autoriza a afirmar: los previstos no se contradicen entre sí **en las celdas que este
    modo sí comprueba** — `familias: una-por-worker`, `encargos` identidad y núcleo común, y la
    cardinalidad `1`. NO que la composición satisfaga las demás celdas de su fila; NO que sean TODOS
    los que el punto exige; NO que se haya despachado; NO que lo despachado coincida con lo previsto.

`despacho.py --corrida` — clase: veredicto. Dirección: admite-de-mas.
    Detecta: un previsto sin despachar; un despachado sin prever; un worker despachado con familia o
    digest distintos de los suyos; un worker sin vencimiento, y dos que compartan el mismo.
    Empareja previsto con despachado por `expected_workers[].key` == `workers[].name`, que la sede
    declara: sin esa igualdad no hay reconciliación posible, solo dos listas sin relación.
    NO detecta el ORDEN de los despachos ni el instante de cada uno: lee el estado asentado, no una
    traza temporal, así que «todos despachados antes de esperar a ninguno» lo acredita solo en la
    forma débil de que ninguno falta al momento de leer.
    NO detecta un despacho que **nunca se asentó**, y es su punto ciego estructural: lee el sobre que
    el conductor escribió y lo contrasta contra la composición que el mismo conductor declaró, así
    que ningún worker fuera de ese documento existe para este modo. Esa dirección la cubre
    **únicamente** la reconciliación contra la fuente efectiva de la plataforma, que es otra unidad.
    Su verde autoriza a afirmar: lo asentado coincide con lo previsto. NO que lo asentado sea todo lo
    que se lanzó.

`--autotest` — clase: veredicto sobre este archivo. Corre controles positivos y negativos: cada
    violación tiene un caso que la produce, porque una guarda que solo se vio en verde es
    indistinguible de una que no puede ponerse roja.
"""
import json
import pathlib
import re
import sys
import unicodedata

SEDE_ENUMS = "skills/cross-review/corridas-en-vuelo.md"
COLUMNAS = ("cardinalidad", "familias", "encargos", "deadline")


def _detener(msg):
    print(msg, file=sys.stderr)
    raise SystemExit(3)


def _norm(texto):
    """Minúsculas, SIN DIACRÍTICOS, sin énfasis ni backticks, espacios colapsados.

    La forma es **byte a byte la misma** que la de `verificar-sobre-en-vuelo.py`, y no por estilo:
    los dos leen las mismas tablas, así que dos normalizaciones distintas hacen que un punto exista
    para uno y no para el otro. Medido: sin quitar diacríticos, `revision final` no encontraba la
    fila que dice `revisión final` y este modo la reportaba como ausente —o sea, ponía en rojo un
    punto por cumplir su propio diseño."""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    for ch in "`*·—–…":
        texto = texto.replace(ch, " ")
    return re.sub(r"\s+", " ", texto).strip().lower()


def _filas_tabla(cuerpo):
    filas = []
    for linea in cuerpo.split("\n"):
        if not linea.strip().startswith("|"):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in celdas):
            continue
        filas.append(celdas)
    return filas


def _seccion(texto, titulo):
    """Cuerpo del primer encabezado que CONTIENE `titulo`, hasta el próximo del mismo nivel o menor."""
    objetivo = _norm(titulo)
    lineas = texto.split("\n")
    inicio = nivel = None
    for i, linea in enumerate(lineas):
        m = re.match(r"^(#+)\s+(.*)$", linea)
        if not m:
            continue
        if inicio is None:
            if objetivo in _norm(m.group(2)):
                inicio, nivel = i + 1, len(m.group(1))
        elif len(m.group(1)) <= nivel:
            return "\n".join(lineas[inicio:i])
    return "\n".join(lineas[inicio:]) if inicio is not None else None


def leer_enums(raiz):
    """Los cuatro dominios, leídos de su sede única. Sin ella el modo se detiene: calcular con enums
    inventados daría un veredicto sobre una regla que nadie escribió."""
    ruta = raiz / SEDE_ENUMS
    if not ruta.is_file():
        _detener(f"sede de enums ilegible: {ruta}")
    cuerpo = _seccion(ruta.read_text(encoding="utf-8"), "los invariantes que cada punto de despacho declara")
    if cuerpo is None:
        _detener("la sede no tiene la sección de invariantes")
    dominios = {}
    for celdas in _filas_tabla(cuerpo):
        if len(celdas) < 2:
            continue
        col = _norm(celdas[0])
        if col in COLUMNAS:
            dominios[col] = {v for v in re.findall(r"`([^`]+)`", celdas[1])}
    faltan = [c for c in COLUMNAS if not dominios.get(c)]
    if faltan:
        _detener(f"la sede no declara el dominio de: {' '.join(faltan)}")
    return dominios


def leer_fila(raiz, skill, punto):
    """La fila que ese punto declara en su propia sección. Ausente es fallo, no permiso."""
    ruta = raiz / "skills" / skill / "SKILL.md"
    if not ruta.is_file():
        _detener(f"skill ilegible: {ruta}")
    cuerpo = _seccion(ruta.read_text(encoding="utf-8"), "corridas delegadas en vuelo")
    if cuerpo is None:
        _detener(f"{skill} no declara la sección de corridas en vuelo")
    objetivo = _norm(punto)
    for celdas in _filas_tabla(cuerpo):
        if len(celdas) == 5 and objetivo in _norm(celdas[0]):
            return {c: _norm(v) for c, v in zip(COLUMNAS, celdas[1:])}
    return None


def validar_fila(fila, dominios, skill, punto):
    if fila is None:
        return f"forma-no-reconocida: {skill} no declara una fila para el punto {punto!r}"
    for col in COLUMNAS:
        if fila[col] not in dominios[col]:
            return (f"forma-no-reconocida: la celda {col}={fila[col]!r} esta fuera de su dominio "
                    f"({' '.join(sorted(dominios[col]))})")
    if fila["encargos"] == "no-aplica" and fila["cardinalidad"] != "1":
        return ("forma-no-reconocida: encargos=no-aplica solo es valido con cardinalidad=1, "
                f"y este punto declara {fila['cardinalidad']}")
    return None


def _cardinalidad_ok(valor, n):
    if valor == "1":
        return n == 1
    return n >= 1  # las demás dependen del dominio resuelto en runtime, no de un número fijo


def evaluar_composicion(fila, workers):
    """Los invariantes comprobables ANTES de lanzar."""
    n = len(workers)
    if not _cardinalidad_ok(fila["cardinalidad"], n):
        return f"cardinalidad-invalida: se previeron {n} workers y el punto declara {fila['cardinalidad']}"
    if fila["familias"] == "una-por-worker":
        fams = [w.get("family") for w in workers]
        vistas = set()
        for f in fams:
            if f in vistas:
                return f"familia-duplicada: {f} aparece mas de una vez"
            vistas.add(f)
    rel = fila["encargos"]
    digs = [w.get("assignment_digest") for w in workers]
    if rel in ("identico-por-digest", "nucleo-comun") and len(set(digs)) > 1:
        if rel == "identico-por-digest":
            return "encargo-divergente: los digests previstos difieren y el punto exige identidad"
        nucleos = [w.get("nucleo_digest", w.get("assignment_digest")) for w in workers]
        if len(set(nucleos)) > 1:
            return "encargo-divergente: los nucleos comunes previstos difieren"
    if rel == "distinto-por-worker" and n > 1 and len(set(digs)) == 1:
        return "encargo-divergente: el punto declara encargos distintos y todos los previstos coinciden"
    return None


def evaluar_corrida(fila, esperados, efectivos):
    """Los invariantes que solo son comprobables DESPUÉS, contrastando en las dos direcciones."""
    por_clave_esp = {w.get("key"): w for w in esperados}
    por_clave_efe = {w.get("key"): w for w in efectivos}
    faltan = sorted(k for k in por_clave_esp if k not in por_clave_efe)
    if faltan:
        return f"fan-out-incompleto: previstos sin despachar: {' '.join(map(str, faltan))}"
    sobran = sorted(k for k in por_clave_efe if k not in por_clave_esp)
    if sobran:
        return f"despacho-no-previsto: despachados sin prever: {' '.join(map(str, sobran))}"
    for clave, esp in por_clave_esp.items():
        efe = por_clave_efe[clave]
        if esp.get("family") != efe.get("family"):
            return (f"familia-duplicada: el worker {clave} se previo {esp.get('family')} "
                    f"y se despacho {efe.get('family')}")
        if esp.get("assignment_digest") != efe.get("assignment_digest"):
            return f"encargo-divergente: el worker {clave} se despacho con otro encargo"
        if not efe.get("deadline"):
            return f"deadline-compartido: el worker {clave} no lleva vencimiento propio"
    # PROPIO no es lo mismo que PRESENTE, y el nombre de la violación habla de lo primero: dos
    # workers con el mismo vencimiento exacto mueren por el mismo reloj, que es justo lo que este
    # invariante impide. Medido: comprobando solo presencia, ese caso salía `corrida-conforme`.
    vistos = {}
    for clave, efe in por_clave_efe.items():
        d = efe.get("deadline")
        if d in vistos:
            return (f"deadline-compartido: los workers {vistos[d]} y {clave} comparten "
                    f"el vencimiento {d}")
        vistos[d] = clave
    return None


def _cargar(ruta):
    p = pathlib.Path(ruta)
    if not p.is_file():
        _detener(f"no se puede leer {ruta}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        _detener(f"{ruta} no es JSON legible: {e}")


def main(argv):
    if len(argv) == 2 and argv[1] == "--autotest":
        return autotest()
    if len(argv) != 6 or argv[1] not in ("--preflight", "--corrida"):
        print("uso: despacho.py --preflight|--corrida <raiz> <skill> <punto> <documento.json>",
              file=sys.stderr)
        return 2
    return ejecutar(argv[1], pathlib.Path(argv[2]), argv[3], argv[4], argv[5])


def ejecutar(modo, raiz, skill, punto, documento):
    dominios = leer_enums(raiz)
    fila = leer_fila(raiz, skill, punto)
    mal = validar_fila(fila, dominios, skill, punto)
    if mal:
        print(mal)
        return 1
    datos = _cargar(documento)
    if modo == "--preflight":
        workers = datos if isinstance(datos, list) else datos.get("expected_workers", [])
        mal = evaluar_composicion(fila, workers)
        if mal:
            print(mal)
            return 1
        print(f"composicion-valida: {len(workers)} previstos · {skill}/{punto}")
        return 0
    esperados = datos.get("expected_workers", [])
    # los nombres salen de la SEDE, no de la conveniencia: `assignment_digest` es el campo del
    # intento y `name` el del worker. Leer un campo que el contrato no declara deja a este modo sin
    # poder ponerse verde sobre un sobre conforme — medido, y por eso está escrito acá.
    efectivos = [{"key": w.get("name"), "family": w.get("family"),
                  "assignment_digest": (w.get("attempts") or [{}])[-1].get("assignment_digest"),
                  "deadline": ((w.get("attempts") or [{}])[-1].get("wait_budget") or {}).get("deadline")}
                 for w in datos.get("workers", [])]
    mal = evaluar_corrida(fila, esperados, efectivos)
    if mal:
        print(mal)
        return 1
    print(f"corrida-conforme: {len(efectivos)} despachados == {len(esperados)} previstos · {skill}/{punto}")
    return 0


def autotest():
    """Un control POSITIVO y uno NEGATIVO por cada violación. Una guarda que solo se vio en verde es
    indistinguible de una que no puede ponerse roja, así que cada nombre del vocabulario tiene acá el
    caso que lo produce."""
    dom = {"cardinalidad": {"1", "1-por-familia", "1-por-ronda", "1-por-repo", "1-por-hallazgo", "n-acotado"},
           "familias": {"una-por-worker", "opuesta-al-conductor", "misma-que-el-conductor",
                        "continuacion-del-anterior", "indiferente"},
           "encargos": {"identico-por-digest", "nucleo-comun", "distinto-por-worker",
                        "delta-sobre-el-anterior", "no-aplica"},
           "deadline": {"propio-por-worker"}}
    dual = {"cardinalidad": "1-por-familia", "familias": "una-por-worker",
            "encargos": "identico-por-digest", "deadline": "propio-por-worker"}
    uno = {"cardinalidad": "1", "familias": "misma-que-el-conductor",
           "encargos": "no-aplica", "deadline": "propio-por-worker"}
    w = lambda k, f, d, dl="2026-01-01": {"key": k, "family": f, "assignment_digest": d, "deadline": dl}

    casos = []
    # --- validar_fila ---
    casos.append(("fila valida", validar_fila(dual, dom, "s", "p"), None))
    casos.append(("fila ausente", validar_fila(None, dom, "s", "p"), "forma-no-reconocida"))
    casos.append(("celda fuera del dominio",
                  validar_fila({**dual, "cardinalidad": "1-por-tanda"}, dom, "s", "p"), "forma-no-reconocida"))
    casos.append(("no-aplica con cardinalidad != 1",
                  validar_fila({**dual, "encargos": "no-aplica"}, dom, "s", "p"), "forma-no-reconocida"))
    casos.append(("no-aplica con cardinalidad 1", validar_fila(uno, dom, "s", "p"), None))
    # --- evaluar_composicion ---
    casos.append(("composicion valida",
                  evaluar_composicion(dual, [w("a", "codex", "D"), w("b", "claude", "D")]), None))
    casos.append(("dos de la misma familia",
                  evaluar_composicion(dual, [w("a", "codex", "D"), w("b", "codex", "D")]), "familia-duplicada"))
    casos.append(("digests distintos donde se exige identidad",
                  evaluar_composicion(dual, [w("a", "codex", "D"), w("b", "claude", "E")]), "encargo-divergente"))
    casos.append(("cardinalidad 1 con dos previstos",
                  evaluar_composicion(uno, [w("a", "claude", "D"), w("b", "claude", "D")]), "cardinalidad-invalida"))
    repo = {**dual, "cardinalidad": "1-por-repo", "familias": "indiferente", "encargos": "distinto-por-worker"}
    casos.append(("encargos iguales donde se exigen distintos",
                  evaluar_composicion(repo, [w("a", "codex", "D"), w("b", "codex", "D")]), "encargo-divergente"))
    casos.append(("encargos distintos donde se exigen distintos",
                  evaluar_composicion(repo, [w("a", "codex", "D"), w("b", "codex", "E")]), None))
    # --- evaluar_corrida ---
    # cada worker con SU vencimiento: el positivo con un deadline compartido era, en sí mismo, la
    # violación que `deadline-compartido` nombra — pasaba porque el predicado miraba presencia.
    esp = [w("a", "codex", "D", "2026-01-01T00:00:00Z"), w("b", "claude", "D", "2026-01-01T00:10:00Z")]
    casos.append(("corrida conforme", evaluar_corrida(dual, esp, esp), None))
    casos.append(("dos workers comparten el mismo vencimiento",
                  evaluar_corrida(dual, esp, [w("a", "codex", "D", "T"), w("b", "claude", "D", "T")]),
                  "deadline-compartido"))
    casos.append(("previsto sin despachar",
                  evaluar_corrida(dual, esp, [w("a", "codex", "D", "T1")]), "fan-out-incompleto"))
    casos.append(("despachado sin prever",
                  evaluar_corrida(dual, esp, esp + [w("c", "codex", "D", "T3")]), "despacho-no-previsto"))
    casos.append(("familia distinta de la prevista",
                  evaluar_corrida(dual, esp, [w("a", "codex", "D", "T1"), w("b", "codex", "D", "T2")]), "familia-duplicada"))
    casos.append(("encargo distinto del previsto",
                  evaluar_corrida(dual, esp, [w("a", "codex", "D", "T1"), w("b", "claude", "E", "T2")]), "encargo-divergente"))
    casos.append(("worker sin vencimiento propio",
                  evaluar_corrida(dual, esp, [w("a", "codex", "D", "2026-01-01T00:00:00Z"),
                                              w("b", "claude", "D", None)]),
                  "deadline-compartido"))

    malos = 0
    for nombre, obtenido, esperado in casos:
        if esperado is None:
            ok = obtenido is None
        else:
            ok = obtenido is not None and obtenido.startswith(esperado)
        print(f"[{'OK   ' if ok else 'FALLA'}] {nombre}" + ("" if ok else f" -> {obtenido!r}"))
        malos += 0 if ok else 1
    positivos = sum(1 for _, _, e in casos if e is None)
    print(f"{len(casos) - malos}/{len(casos)} casos · {positivos} positivos · {len(casos) - positivos} negativos")
    return 1 if malos else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
