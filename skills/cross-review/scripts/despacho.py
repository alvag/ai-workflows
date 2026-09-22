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
    Detecta: una fila ausente o con una celda fuera de su enum; una clave prevista vacía o repetida;
    un operando ausente —`family`, `assignment_digest`, y `nucleo_digest` en las dos direcciones que
    la sede declara—; las CUATRO columnas enteras —los seis valores de `cardinalidad`, los seis de
    `familias`, los cinco de `encargos` y el único de `deadline`, que era el que no se evaluaba—,
    cada una contra el dato que su celda necesita; y la ausencia de ese dato, que **falla cerrado**
    en vez de pasar en silencio.
    `deadline: propio-por-worker` se hace cumplir acá porque sus dos mitades son decidibles antes de
    crear nada: que cada previsto tenga vencimiento (`deadline-invalido`) y que no sea el de otro
    (`deadline-compartido`). Medido antes de exigirlo, las dos violaciones salían
    `composicion-valida`.
    Los operandos se exigen ANTES de evaluar ninguna relación, porque una comparación entre dos
    ausencias da verdadero: medido, los dos `assignment_digest` en `null` satisfacían
    `identico-por-digest` y una `family` ausente satisfacía `opuesta-al-conductor`, las dos sobre
    puntos reales y las dos con el mensaje `composicion-valida`.
    Distingue `anterior` AUSENTE de `anterior: []`: la lista vacía **declara la ronda inicial** y
    satisface `delta-sobre-el-anterior` sin comparar nada, que es lo que las filas de `debate` y del
    loop de revisión necesitan en su ronda 0 y su ronda 1. La ausencia del campo sigue fallando
    cerrado, y **solo la lista literalmente vacía** cuenta como ronda inicial: cada entrada de
    `anterior` pasa la misma validación que la composición —clave no vacía y única, `family` y
    `assignment_digest` presentes—, porque filtrar en silencio las entradas sin clave convertía
    `anterior: [{}]` en un mapa vacío indistinguible de la ronda inicial.
    Los dos predicados multiworker comparan el conjunto entero y no solo su extremo: `nucleo-comun`
    coteja los núcleos SIEMPRE —no solo cuando los encargos difieren, porque el anexo privado hace
    que coincidir no diga nada del núcleo— y `distinto-por-worker` exige digests **únicos**, no
    «no todos iguales», que dejaba pasar el duplicado parcial `D, D, E`.
    La correlación con el intento anterior es **por clave, y la clave es estable a lo largo de las
    rondas**: un punto cuyas rondas reanudan el mismo worker tiene una entrada en `workers[]` con
    varios `attempts[]`, así que una composición que declare `ronda-2` contra un `anterior` de
    `ronda-1` describe dos workers distintos y se reporta como tal. Está en la sede, con la corrida
    real que lo mide.
    **El dato viaja en el nodo `dominio` de la composición**, y esa es la diferencia con la versión
    anterior de este modo: mientras el dominio no viajaba, cuatro valores de `cardinalidad` y tres de
    `familias` se evaluaban como `n >= 1` y como nada respectivamente. Medido entonces: un fan-out
    dual con UN worker previsto sobre un inventario de dos familias salía 0, y dos workers de la
    misma familia sobre una fila `opuesta-al-conductor` salían `composicion-valida` 0.
    NO detecta, y lo que queda es de otra clase —ya no es un dato que falta, es un juicio que ningún
    predicado hace:
      · que el `dominio` declarado sea **verdadero**. Que diga `cardinal: 3` no acredita que el
        reparto tenga tres repos: lo escribe el mismo conductor que escribe la composición, así que
        este modo comprueba coherencia entre lo que el conductor declara, nunca contra el mundo.
      · que el `assignment_digest` previsto sea el digest del encargo que el worker va a recibir de
        verdad. Compara digests entre sí; no los recomputa sobre ningún texto.
    NO detecta nada de lo que pasa DESPUÉS de correr: es previo a crear recursos por contrato, así
    que no puede ver un despacho, ni su orden, ni su vencimiento real.
    Su verde autoriza a afirmar: los previstos satisfacen las cuatro celdas de su fila **contra el
    dominio que el conductor declaró**. NO que ese dominio sea el real; NO que se haya despachado;
    NO que lo despachado coincida con lo previsto.

`despacho.py --corrida` — clase: veredicto. Dirección: admite-de-mas.
    Detecta: una clave prevista o efectiva vacía o repetida; un operando ausente en cualquiera de las
    dos listas —el mismo hueco dejaba pasar un sobre con todas sus familias y digests en `null` como
    `corrida-conforme`—; un worker sin ningún intento; un previsto sin despachar; un despachado sin
    prever; un worker despachado con familia o digest distintos de los suyos; un worker sin
    vencimiento, y dos que compartan el mismo.
    Empareja previsto con despachado por `expected_workers[].key` == `workers[].expected_key`, que
    la sede declara como el campo de correlación. **No** empareja por `name`: la sede define `name`
    como el nombre del worker despachado y `key` como la clave del dominio que cubre, y son cosas
    distintas — medido sobre corridas reales de este repositorio, `key: codex` convive con
    `name: ctr-codex`, así que emparejar por nombre daba `fan-out-incompleto` sobre un sobre
    conforme.
    Recorre los INTENTOS y no solo el último: el sellado gobierna el primero, y entre intentos
    gobierna lo que la fila declara —con `delta-sobre-el-anterior` cada uno difiere del anterior, y
    con cualquier otro valor todos valen el sellado, porque un relanzamiento reenvía el mismo
    encargo—. Quedarse con el último ponía en rojo la reanudación válida y dejaba pasar la que
    repetía el encargo de la ronda previa: las dos medidas. El `deadline` sigue la misma regla, y
    por eso el previsto acredita el primer intento y no los posteriores, que abren su propia espera.
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


def _claves(workers, etiqueta):
    """Las claves, validadas ANTES de indexar por ellas.

    Un mapa construido por comprehension sobre claves repetidas o ausentes **colapsa** entradas, y el
    colapso se lee como coincidencia: dos previstos con la misma clave frente a un efectivo daban
    `corrida-conforme` en vez de `fan-out-incompleto`, y varias entradas sin clave se fundían todas
    bajo `None`. La validación va primero porque después del mapa la evidencia del colapso ya no
    existe — los dos tamaños coinciden justamente porque uno se comió al otro."""
    claves = []
    for i, w in enumerate(workers):
        k = w.get("key")
        if not isinstance(k, str) or not k.strip():
            return None, (f"forma-no-reconocida: la entrada {i} de {etiqueta} no declara una clave "
                          f"no vacia (key={k!r})")
        if k in claves:
            return None, f"forma-no-reconocida: la clave {k!r} se repite en {etiqueta}"
        claves.append(k)
    return claves, None


def _operandos(workers, etiqueta, encargos=None):
    """Los valores que las relaciones **comparan**, exigidos antes de compararlas.

    Sin esto, la ausencia se comporta como coincidencia y el verde miente en la dirección más cara:
    dos digests `null` dan `len(set(...)) == 1` y satisfacen `identico-por-digest`; una `family`
    ausente nunca es igual a la del conductor y satisface `opuesta-al-conductor`. Los dos casos
    están medidos sobre puntos reales —el panel de revisores y el implementador inicial—, y los dos
    salían `composicion-valida` con exactamente cero datos comparados.

    `encargos` decide qué se hace con `nucleo_digest`: la sede lo declara **obligatorio** con
    `nucleo-comun` y **ausente en los demás valores**, así que las dos direcciones se hacen cumplir.
    Con `encargos=None` no se mira: es la forma de `workers[]`, que no lleva ese campo."""
    for i, w in enumerate(workers):
        for campo in ("family", "assignment_digest"):
            v = w.get(campo)
            if not isinstance(v, str) or not v.strip():
                return (f"forma-no-reconocida: la entrada {i} de {etiqueta} no declara `{campo}` "
                        f"({campo}={v!r}), y es uno de los valores que este modo compara")
        if encargos is None:
            continue
        n = w.get("nucleo_digest")
        if encargos == "nucleo-comun":
            if not isinstance(n, str) or not n.strip():
                return (f"forma-no-reconocida: la entrada {i} de {etiqueta} no declara "
                        f"`nucleo_digest` ({n!r}), que `encargos: nucleo-comun` exige")
        elif n is not None:
            return (f"forma-no-reconocida: la entrada {i} de {etiqueta} declara `nucleo_digest` "
                    f"y la sede lo quiere ausente con `encargos: {encargos}`")
    return None


def _falta_dominio(campo, columna, valor):
    """El dato contra el que se comprobaría no viaja: falla cerrado.

    Es la diferencia entre este modo y el que lo precedía. Devolver `None` acá —«no puedo
    comprobarlo, entonces pasa»— es lo que dejaba cuatro valores de `cardinalidad` y tres de
    `familias` sin hacer cumplir, con el verde de un modo que decía comprobarlos."""
    return (f"forma-no-reconocida: {columna}={valor!r} se comprueba contra `{campo}` del nodo "
            f"`dominio`, y la composicion no lo declara")


def _anterior_por_clave(dominio):
    """Devuelve `(mapa, violacion)`. `mapa is None` = el campo **no viaja**; `{}` = lista vacía.

    Solo la lista **literalmente vacía** es la ronda inicial. Antes, cada entrada sin `key` de texto
    se descartaba en silencio y los duplicados se colapsaban al construir el diccionario, así que
    `anterior: [{}]` producía un mapa vacío y se leía como ronda inicial declarada: medido, el
    preflight real de `cross-review` salía `composicion-valida` sobre un anterior que no declaraba
    nada. Un anterior mal formado no es una ronda inicial, es un anterior mal formado, y ahora falla
    cerrado con la misma validación que se le exige a la composición — clave no vacía y única,
    `family` y `assignment_digest` presentes, que son los tres campos que la sede le pide."""
    if "anterior" not in dominio:
        return None, None
    previos = dominio.get("anterior")
    if not isinstance(previos, list):
        return None, (f"forma-no-reconocida: `dominio.anterior` no es una lista "
                      f"({type(previos).__name__})")
    _, mal = _claves(previos, "dominio.anterior")
    if mal:
        return None, mal
    mal = _operandos(previos, "dominio.anterior")
    if mal:
        return None, mal
    return {w["key"]: w for w in previos}, None


def _evaluar_cardinalidad(valor, workers, dominio):
    n = len(workers)
    if valor == "1":
        if n != 1:
            return f"cardinalidad-invalida: se previeron {n} workers y el punto declara 1"
        return None
    if valor == "1-por-familia":
        inventario = dominio.get("familias")
        if not isinstance(inventario, list) or not inventario:
            return _falta_dominio("familias", "cardinalidad", valor)
        esperadas = sorted(set(inventario))
        previstas = sorted(str(w.get("family")) for w in workers)
        if previstas != esperadas:
            return (f"cardinalidad-invalida: el inventario declara {len(esperadas)} familias "
                    f"({' '.join(esperadas)}) y se previeron {n} workers "
                    f"({' '.join(previstas) or 'ninguno'})")
        return None
    if valor in ("1-por-ronda", "1-por-repo", "1-por-hallazgo"):
        cardinal = dominio.get("cardinal")
        if not isinstance(cardinal, int) or isinstance(cardinal, bool) or cardinal < 1:
            return _falta_dominio("cardinal", "cardinalidad", valor)
        if n != cardinal:
            return (f"cardinalidad-invalida: el dominio de {valor} tiene {cardinal} elementos "
                    f"y se previeron {n} workers")
        return None
    if valor == "n-acotado":
        tope = dominio.get("tope")
        if not isinstance(tope, int) or isinstance(tope, bool) or tope < 1:
            return _falta_dominio("tope", "cardinalidad", valor)
        if not 1 <= n <= tope:
            return f"cardinalidad-invalida: se previeron {n} workers y el tope declarado es {tope}"
        return None
    return None


def _evaluar_familias(valor, workers, dominio):
    if valor == "una-por-worker":
        vistas = set()
        for w in workers:
            f = w.get("family")
            if f in vistas:
                return f"familia-duplicada: {f} aparece mas de una vez"
            vistas.add(f)
        return None
    if valor in ("opuesta-al-conductor", "misma-que-el-conductor"):
        conductor = dominio.get("conductor")
        if not isinstance(conductor, str) or not conductor.strip():
            return _falta_dominio("conductor", "familias", valor)
        for w in workers:
            f = w.get("family")
            if valor == "misma-que-el-conductor" and f != conductor:
                return (f"familia-invalida: el worker {w.get('key')} se previo {f} y el punto exige "
                        f"la del conductor ({conductor})")
            if valor == "opuesta-al-conductor" and f == conductor:
                return (f"familia-invalida: el worker {w.get('key')} se previo {f}, la misma del "
                        f"conductor, y el punto exige la opuesta")
        return None
    if valor == "opuesta-al-autor-del-codigo":
        autor = dominio.get("autor")
        if not isinstance(autor, str) or not autor.strip():
            return _falta_dominio("autor", "familias", valor)
        inventario = dominio.get("familias")
        if (not isinstance(inventario, list) or not inventario
                or any(not isinstance(f, str) or not f.strip() for f in inventario)):
            return _falta_dominio("familias", "familias", valor)
        degradacion = dominio.get("degradacion")
        if degradacion not in (None, "same-family"):
            return ("forma-no-reconocida: `dominio.degradacion` solo admite `same-family` "
                    "para la revisión final")
        opuestas = [f for f in set(inventario) if f != autor]
        if opuestas and degradacion is not None:
            return ("familia-invalida: se declaro degradacion aunque la familia opuesta al autor "
                    "esta disponible")
        for w in workers:
            f = w.get("family")
            if f not in inventario:
                return (f"familia-invalida: el worker {w.get('key')} se previo {f} fuera del "
                        "inventario resuelto")
            if opuestas and f == autor:
                return (f"familia-invalida: el worker {w.get('key')} se previo de la familia "
                        f"del autor ({autor}) aunque esta disponible la opuesta")
            if not opuestas and degradacion != "same-family":
                return (f"familia-invalida: el worker {w.get('key')} coincide con el autor "
                        "sin degradacion declarada")
        return None
    if valor == "continuacion-del-anterior":
        previos, mal = _anterior_por_clave(dominio)
        if mal:
            return mal
        if previos is None:
            return _falta_dominio("anterior", "familias", valor)
        for w in workers:
            prev = previos.get(w.get("key"))
            if prev is None:
                return (f"familia-invalida: el worker {w.get('key')} no tiene intento anterior que "
                        f"continuar y el punto declara continuacion-del-anterior")
            if w.get("family") != prev.get("family"):
                return (f"familia-invalida: el worker {w.get('key')} se previo {w.get('family')} "
                        f"y continua un intento de {prev.get('family')}")
        return None
    return None  # `indiferente` no tiene nada que comprobar, y su silencio es correcto


def _evaluar_encargos(valor, workers, dominio):
    n = len(workers)
    digs = [w.get("assignment_digest") for w in workers]
    if valor == "identico-por-digest":
        if len(set(digs)) > 1:
            return "encargo-divergente: los digests previstos difieren y el punto exige identidad"
        return None
    if valor == "nucleo-comun":
        # el núcleo se compara SIEMPRE, no solo cuando los encargos difieren. `nucleo-comun` admite
        # un anexo privado declarado por worker, así que dos `assignment_digest` iguales no dicen
        # nada del núcleo: medido sobre el fan-out dual, encargos `D, D` con núcleos `N, M` salía
        # `composicion-valida`, que es la violación que este valor existe para nombrar.
        nucleos = [w.get("nucleo_digest") for w in workers]
        if len(set(nucleos)) > 1:
            return "encargo-divergente: los nucleos comunes previstos difieren"
        return None
    if valor == "distinto-por-worker" and n > 1:
        # ÚNICOS, no «no todos iguales». Rechazar solo cuando los N coinciden deja pasar el duplicado
        # parcial, que es el caso realista: medido sobre el fan-out por repo, `D, D, E` con tres
        # repos salía `composicion-valida` con dos repos compartiendo encargo.
        if len(set(digs)) != n:
            repetidos = sorted({str(d) for d in digs if digs.count(d) > 1})
            return ("encargo-divergente: el punto declara encargos distintos por worker y se repite "
                    + " ".join(repetidos))
        return None
    if valor == "delta-sobre-el-anterior":
        previos, mal = _anterior_por_clave(dominio)
        if mal:
            return mal
        if previos is None:
            return _falta_dominio("anterior", "encargos", valor)
        if not previos:
            # ronda inicial DECLARADA: no hay encargo anterior sobre el cual medir un delta, y la
            # relación se satisface sin comparar nada. El predicado sigue pudiendo ponerse rojo en
            # toda ronda posterior, que es donde la relación tiene sujeto.
            return None
        for w in workers:
            prev = previos.get(w.get("key"))
            if prev is None:
                return (f"encargo-divergente: el worker {w.get('key')} no tiene encargo anterior "
                        f"contra el cual medir el delta")
            if w.get("assignment_digest") == prev.get("assignment_digest"):
                return (f"encargo-divergente: el worker {w.get('key')} repite el encargo anterior "
                        f"y el punto exige un delta sobre el")
        return None
    return None


def _deadlines_previstos(workers):
    """La columna `deadline` es la única que el preflight no evaluaba, y es decidible antes de crear.

    `propio-por-worker` dice dos cosas y las dos se comprueban acá: que cada worker **tenga** su
    vencimiento previsto —el campo existe justamente para ser el sujeto del invariante, porque
    retirada la CLI no había dónde leer qué vencimiento le tocaba a cada uno— y que sea **propio**,
    o sea distinto del de los demás. Medido antes de exigirlo: una composición sin `deadline` y otra
    con el mismo vencimiento para los dos workers salían las dos `composicion-valida`, y el segundo
    caso es exactamente «uno muere por el reloj del otro», que es lo que la columna impide."""
    vistos = {}
    for i, w in enumerate(workers):
        d = w.get("deadline")
        if not isinstance(d, str) or not d.strip():
            return (f"deadline-invalido: la entrada {i} de expected_workers no declara un `deadline` "
                    f"previsto ({d!r}), y la columna lo exige propio por worker")
        if d in vistos:
            return (f"deadline-compartido: los workers previstos {vistos[d]} y {w.get('key')} "
                    f"comparten el vencimiento {d}")
        vistos[d] = w.get("key")
    return None


def _operandos_efectivos(efectivos):
    """Lo que `_operandos` hace sobre lo previsto, acá sobre la forma de `workers[]`.

    La diferencia es que un worker efectivo tiene **una lista de intentos**, no un valor: un digest
    ausente en el tercer intento es tan mentiroso como en el primero, y quedarse con el último
    escondía a los anteriores."""
    for i, e in enumerate(efectivos):
        f = e.get("family")
        if not isinstance(f, str) or not f.strip():
            return (f"forma-no-reconocida: la entrada {i} de workers no declara `family` "
                    f"(family={f!r}), y es uno de los valores que este modo compara")
        digs = e.get("digests") or []
        if not digs:
            return f"forma-no-reconocida: la entrada {i} de workers no declara ningun intento"
        for j, d in enumerate(digs):
            if not isinstance(d, str) or not d.strip():
                return (f"forma-no-reconocida: el intento {j} de la entrada {i} de workers no "
                        f"declara `assignment_digest` ({d!r})")
    return None


def _encargos_por_intento(valor, clave, esp, efe):
    """El cotejo de encargos recorre los intentos, y no solo el último.

    **El sellado gobierna el primer intento, no todos**, y esa es la salida a una contradicción real
    del contrato: `expected_workers[]` se sella antes del primer efecto y lleva UN digest, pero el
    encargo de la ronda 2 de un fix loop es un delta que depende de lo que la ronda 1 encontró — no
    es predecible al sellar, así que ninguna expectativa sellada puede describirlo. Comparar el
    último intento contra el sellado ponía en rojo a la reanudación válida: medido, un sobre con
    `r1` y `r2` salía `encargo-divergente`.

    Lo que sí es comprobable desde el sobre es lo que la fila declara **entre rondas**: con
    `delta-sobre-el-anterior`, cada intento difiere del anterior —que es el invariante mismo, ahora
    también en runtime y no solo contra `dominio.anterior`—; con cualquier otro valor, un relanzamiento
    reenvía el mismo encargo, así que **todos** los intentos valen el digest sellado."""
    digs = efe["digests"]
    if digs[0] != esp.get("assignment_digest"):
        return (f"encargo-divergente: el primer intento del worker {clave} se despacho con un "
                f"encargo distinto del previsto")
    if valor == "delta-sobre-el-anterior":
        for j in range(1, len(digs)):
            if digs[j] == digs[j - 1]:
                return (f"encargo-divergente: el intento {j} del worker {clave} repite el encargo "
                        f"del intento anterior y el punto exige un delta")
        return None
    for j in range(1, len(digs)):
        if digs[j] != esp.get("assignment_digest"):
            return (f"encargo-divergente: el intento {j} del worker {clave} cambio de encargo y el "
                    f"punto no declara delta entre rondas")
    return None


def _deadline_por_intento(clave, esp, efe):
    """Cada intento lleva su vencimiento, y el primero acredita al que se selló.

    Un relanzamiento abre una espera nueva, así que sus intentos posteriores tienen presupuesto
    propio y el sellado no los gobierna; lo que el sellado sí gobierna es el lanzamiento para el que
    se escribió. Sin esta comparación el campo previsto no acreditaba nada: medido, un previsto `T1`
    contra un efectivo `T2` salía `corrida-conforme`."""
    dls = efe["deadlines"]
    for j, d in enumerate(dls):
        if not isinstance(d, str) or not d.strip():
            return (f"deadline-invalido: el intento {j} del worker {clave} no lleva vencimiento "
                    f"propio")
    if dls[0] != esp.get("deadline"):
        return (f"deadline-invalido: el primer intento del worker {clave} vencio en {dls[0]} y el "
                f"previsto sellado era {esp.get('deadline')}")
    return None


def evaluar_composicion(fila, workers, dominio=None):
    """Los invariantes comprobables ANTES de lanzar, contra el `dominio` que la composición declara.

    Las **cuatro** columnas se evalúan: los seis valores de `cardinalidad`, los seis de `familias`,
    los cinco de `encargos` y el único de `deadline`. El dato que cada celda necesita se exige: sin
    él **falla cerrado**."""
    dominio = dominio if isinstance(dominio, dict) else {}
    _, mal = _claves(workers, "expected_workers")
    if mal:
        return mal
    mal = _operandos(workers, "expected_workers", fila["encargos"])
    if mal:
        return mal
    mal = _deadlines_previstos(workers)
    if mal:
        return mal
    for evaluar, columna in ((_evaluar_cardinalidad, "cardinalidad"),
                             (_evaluar_familias, "familias"),
                             (_evaluar_encargos, "encargos")):
        mal = evaluar(fila[columna], workers, dominio)
        if mal:
            return mal
    return None


def evaluar_corrida(fila, esperados, efectivos):
    """Los invariantes que solo son comprobables DESPUÉS, contrastando en las dos direcciones."""
    claves_esp, mal = _claves(esperados, "expected_workers")
    if mal:
        return mal
    claves_efe, mal = _claves(efectivos, "workers")
    if mal:
        return mal
    mal = _operandos(esperados, "expected_workers", fila["encargos"])
    if mal:
        return mal
    mal = _deadlines_previstos(esperados)
    if mal:
        return mal
    mal = _operandos_efectivos(efectivos)
    if mal:
        return mal
    por_clave_esp = dict(zip(claves_esp, esperados))
    por_clave_efe = dict(zip(claves_efe, efectivos))
    faltan = sorted(k for k in por_clave_esp if k not in por_clave_efe)
    if faltan:
        return f"fan-out-incompleto: previstos sin despachar: {' '.join(faltan)}"
    sobran = sorted(k for k in por_clave_efe if k not in por_clave_esp)
    if sobran:
        return f"despacho-no-previsto: despachados sin prever: {' '.join(sobran)}"
    for clave, esp in por_clave_esp.items():
        efe = por_clave_efe[clave]
        if esp.get("family") != efe.get("family"):
            return (f"familia-invalida: el worker {clave} se previo {esp.get('family')} "
                    f"y se despacho {efe.get('family')}")
        mal = _encargos_por_intento(fila["encargos"], clave, esp, efe)
        if mal:
            return mal
        mal = _deadline_por_intento(clave, esp, efe)
        if mal:
            return mal
    # PROPIO no es lo mismo que PRESENTE, y el nombre de la violación habla de lo primero: dos
    # workers con el mismo vencimiento vigente mueren por el mismo reloj, que es justo lo que este
    # invariante impide. Medido: comprobando solo presencia, ese caso salía `corrida-conforme`.
    vistos = {}
    for clave, efe in por_clave_efe.items():
        d = efe["deadlines"][-1]
        if d in vistos:
            return (f"deadline-compartido: los workers {vistos[d]} y {clave} comparten "
                    f"el vencimiento vigente {d}")
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
        # una composición que es una lista pelada no puede declarar su dominio, así que solo sirve
        # para las filas que no lo necesitan; las demás fallan cerrado por `_falta_dominio`.
        lista = isinstance(datos, list)
        workers = datos if lista else datos.get("expected_workers", [])
        dominio = {} if lista else datos.get("dominio", {})
        mal = evaluar_composicion(fila, workers, dominio)
        if mal:
            print(mal)
            return 1
        print(f"composicion-valida: {len(workers)} previstos · {skill}/{punto}")
        return 0
    esperados = datos.get("expected_workers", [])
    # los nombres salen de la SEDE, no de la conveniencia: `assignment_digest` es el campo del
    # intento y `expected_key` el campo de correlación del worker. Leer un campo que el contrato no
    # declara deja a este modo sin poder ponerse verde sobre un sobre conforme — medido, y por eso
    # está escrito acá. `name` NO sirve de correlación: la sede lo define como el nombre del worker
    # despachado, y las corridas reales de este repositorio lo usan así (`ctr-codex` para la clave
    # de dominio `codex`), así que emparejar por él ponía en rojo sobres conformes.
    # Y se conserva la LISTA de intentos, no su último elemento: un worker reanudado lleva un digest
    # y un presupuesto de espera por ronda, así que quedarse con el último escondía a los anteriores
    # y ponía en rojo la reanudación válida contra un previsto que se selló para la primera.
    efectivos = []
    for w in datos.get("workers", []):
        intentos = w.get("attempts") or []
        efectivos.append({
            "key": w.get("expected_key"),
            "family": w.get("family"),
            "digests": [a.get("assignment_digest") for a in intentos],
            "deadlines": [(a.get("wait_budget") or {}).get("deadline") for a in intentos],
        })
    mal = evaluar_corrida(fila, esperados, efectivos)
    if mal:
        print(mal)
        return 1
    print(f"corrida-conforme: {len(efectivos)} despachados == {len(esperados)} previstos · {skill}/{punto}")
    return 0


def autotest():
    """Un control POSITIVO y uno NEGATIVO por cada violación. Una guarda que solo se vio en verde es
    indistinguible de una que no puede ponerse roja, así que cada nombre del vocabulario tiene acá el
    caso que lo produce. Los SEIS valores de `cardinalidad` y los SEIS de `familias` tienen cada uno
    su par, más el negativo de **dominio ausente**: sin ese último, un valor podría pasar por no
    poder comprobarse, que es exactamente el defecto que este modo tenía."""
    dom = {"cardinalidad": {"1", "1-por-familia", "1-por-ronda", "1-por-repo", "1-por-hallazgo", "n-acotado"},
           "familias": {"una-por-worker", "opuesta-al-conductor", "opuesta-al-autor-del-codigo",
                        "misma-que-el-conductor",
                        "continuacion-del-anterior", "indiferente"},
           "encargos": {"identico-por-digest", "nucleo-comun", "distinto-por-worker",
                        "delta-sobre-el-anterior", "no-aplica"},
           "deadline": {"propio-por-worker"}}
    dual = {"cardinalidad": "1-por-familia", "familias": "una-por-worker",
            "encargos": "identico-por-digest", "deadline": "propio-por-worker"}
    uno = {"cardinalidad": "1", "familias": "misma-que-el-conductor",
           "encargos": "no-aplica", "deadline": "propio-por-worker"}
    fila = lambda **k: {**dual, **k}
    # el vencimiento por defecto se deriva de la clave: el corpus anterior le daba el MISMO a todos
    # los previstos, o sea era en sí mismo la violación que `deadline: propio-por-worker` nombra, y
    # pasaba porque el preflight no evaluaba esa columna. Es la segunda vez en este archivo.
    w = lambda k, f, d, dl=None: {"key": k, "family": f, "assignment_digest": d,
                                  "deadline": dl or f"2026-01-01T00:00:00Z#{k}"}
    # un worker EFECTIVO lleva sus intentos en orden, no un valor: `e` es el de un solo intento y
    # `em` el reanudado, que es el caso que la reconciliación rechazaba.
    e = lambda k, f, d, dl: {"key": k, "family": f, "digests": [d], "deadlines": [dl]}
    em = lambda k, f, digs, dls: {"key": k, "family": f, "digests": list(digs), "deadlines": list(dls)}
    inv = {"familias": ["claude", "codex"]}

    casos = []
    # --- validar_fila ---
    casos.append(("fila valida", validar_fila(dual, dom, "s", "p"), None))
    casos.append(("fila ausente", validar_fila(None, dom, "s", "p"), "forma-no-reconocida"))
    casos.append(("celda fuera del dominio",
                  validar_fila({**dual, "cardinalidad": "1-por-tanda"}, dom, "s", "p"), "forma-no-reconocida"))
    casos.append(("no-aplica con cardinalidad != 1",
                  validar_fila({**dual, "encargos": "no-aplica"}, dom, "s", "p"), "forma-no-reconocida"))
    casos.append(("no-aplica con cardinalidad 1", validar_fila(uno, dom, "s", "p"), None))

    # --- claves de la composición: el mapa colapsa si no se validan antes ---
    casos.append(("clave prevista ausente",
                  evaluar_composicion(dual, [w(None, "codex", "D"), w("b", "claude", "D")], inv),
                  "forma-no-reconocida"))
    casos.append(("clave prevista repetida",
                  evaluar_composicion(dual, [w("a", "codex", "D"), w("a", "claude", "D")], inv),
                  "forma-no-reconocida"))

    # --- cardinalidad: los seis valores, cada uno con su par ---
    casos.append(("cardinalidad 1 con un previsto",
                  evaluar_composicion(uno, [w("a", "claude", "D")], {"conductor": "claude"}), None))
    casos.append(("cardinalidad 1 con dos previstos",
                  evaluar_composicion(uno, [w("a", "claude", "D"), w("b", "claude", "D")],
                                      {"conductor": "claude"}), "cardinalidad-invalida"))
    casos.append(("1-por-familia con una por familia del inventario",
                  evaluar_composicion(dual, [w("a", "codex", "D"), w("b", "claude", "D")], inv), None))
    casos.append(("1-por-familia con UN worker sobre un inventario de dos",
                  evaluar_composicion(dual, [w("a", "codex", "D")], inv), "cardinalidad-invalida"))
    casos.append(("1-por-familia sin inventario en el dominio",
                  evaluar_composicion(dual, [w("a", "codex", "D"), w("b", "claude", "D")], {}),
                  "forma-no-reconocida"))
    ronda = fila(cardinalidad="1-por-ronda", familias="indiferente", encargos="distinto-por-worker")
    casos.append(("1-por-ronda con tantos workers como rondas",
                  evaluar_composicion(ronda, [w("a", "codex", "D"), w("b", "codex", "E")],
                                      {"cardinal": 2}), None))
    casos.append(("1-por-ronda con menos workers que rondas",
                  evaluar_composicion(ronda, [w("a", "codex", "D"), w("b", "codex", "E")],
                                      {"cardinal": 3}), "cardinalidad-invalida"))
    casos.append(("1-por-ronda sin cardinal en el dominio",
                  evaluar_composicion(ronda, [w("a", "codex", "D")], {}), "forma-no-reconocida"))
    repo = fila(cardinalidad="1-por-repo", familias="indiferente", encargos="distinto-por-worker")
    casos.append(("1-por-repo con un worker por repo",
                  evaluar_composicion(repo, [w("a", "codex", "D"), w("b", "codex", "E")],
                                      {"cardinal": 2}), None))
    casos.append(("1-por-repo con un worker de mas",
                  evaluar_composicion(repo, [w("a", "codex", "D"), w("b", "codex", "E")],
                                      {"cardinal": 1}), "cardinalidad-invalida"))
    hall = fila(cardinalidad="1-por-hallazgo", familias="indiferente", encargos="distinto-por-worker")
    casos.append(("1-por-hallazgo con un worker por hallazgo",
                  evaluar_composicion(hall, [w("a", "codex", "D")], {"cardinal": 1}), None))
    casos.append(("1-por-hallazgo con menos workers que hallazgos",
                  evaluar_composicion(hall, [w("a", "codex", "D")], {"cardinal": 2}),
                  "cardinalidad-invalida"))
    acot = fila(cardinalidad="n-acotado", familias="indiferente", encargos="distinto-por-worker")
    casos.append(("n-acotado dentro del tope",
                  evaluar_composicion(acot, [w("a", "codex", "D"), w("b", "codex", "E")],
                                      {"tope": 3}), None))
    casos.append(("n-acotado por encima del tope",
                  evaluar_composicion(acot, [w("a", "codex", "D"), w("b", "codex", "E")],
                                      {"tope": 1}), "cardinalidad-invalida"))
    casos.append(("n-acotado sin tope en el dominio",
                  evaluar_composicion(acot, [w("a", "codex", "D")], {}), "forma-no-reconocida"))

    # --- familias: los seis valores, cada uno con su par ---
    casos.append(("una-por-worker con una por worker",
                  evaluar_composicion(dual, [w("a", "codex", "D"), w("b", "claude", "D")], inv), None))
    casos.append(("una-por-worker con dos de la misma familia",
                  evaluar_composicion(fila(cardinalidad="n-acotado"),
                                      [w("a", "codex", "D"), w("b", "codex", "D")], {"tope": 2}),
                  "familia-duplicada"))
    opu = fila(cardinalidad="n-acotado", familias="opuesta-al-conductor")
    casos.append(("opuesta-al-conductor con la familia opuesta",
                  evaluar_composicion(opu, [w("a", "codex", "D")], {"tope": 2, "conductor": "claude"}),
                  None))
    casos.append(("opuesta-al-conductor con la MISMA familia del conductor",
                  evaluar_composicion(opu, [w("a", "claude", "D"), w("b", "claude", "D")],
                                      {"tope": 2, "conductor": "claude"}), "familia-invalida"))
    casos.append(("opuesta-al-conductor sin conductor en el dominio",
                  evaluar_composicion(opu, [w("a", "codex", "D")], {"tope": 2}), "forma-no-reconocida"))
    op_autor = fila(cardinalidad="1", familias="opuesta-al-autor-del-codigo", encargos="no-aplica")
    casos.append(("opuesta-al-autor con conductor de otra familia",
                  evaluar_composicion(op_autor, [w("a", "claude", "D")],
                                      {"autor": "codex", "conductor": "claude",
                                       "familias": ["codex", "claude"]}), None))
    casos.append(("opuesta-al-autor con autor Claude y conductor Codex",
                  evaluar_composicion(op_autor, [w("a", "codex", "D")],
                                      {"autor": "claude", "conductor": "codex",
                                       "familias": ["codex", "claude"]}), None))
    casos.append(("opuesta-al-autor admite familia opaca y duplicados en inventario",
                  evaluar_composicion(op_autor, [w("a", "tercera", "D")],
                                      {"autor": "codex", "familias": ["tercera", "tercera"]}),
                  None))
    casos.append(("opuesta-al-autor rechaza misma familia disponible",
                  evaluar_composicion(op_autor, [w("a", "codex", "D")],
                                      {"autor": "codex", "familias": ["codex", "claude"]}),
                  "familia-invalida"))
    casos.append(("opuesta-al-autor exige autor declarado",
                  evaluar_composicion(op_autor, [w("a", "claude", "D")],
                                      {"familias": ["codex", "claude"]}), "forma-no-reconocida"))
    casos.append(("opuesta-al-autor exige inventario declarado",
                  evaluar_composicion(op_autor, [w("a", "claude", "D")],
                                      {"autor": "codex"}), "forma-no-reconocida"))
    casos.append(("opuesta-al-autor rechaza inventario vacio",
                  evaluar_composicion(op_autor, [w("a", "codex", "D")],
                                      {"autor": "codex", "familias": []}),
                  "forma-no-reconocida"))
    casos.append(("opuesta-al-autor rechaza elemento vacio del inventario",
                  evaluar_composicion(op_autor, [w("a", "codex", "D")],
                                      {"autor": "codex", "familias": ["codex", ""]}),
                  "forma-no-reconocida"))
    casos.append(("opuesta-al-autor rechaza degradacion desconocida",
                  evaluar_composicion(op_autor, [w("a", "codex", "D")],
                                      {"autor": "codex", "familias": ["codex"],
                                       "degradacion": "desconocida"}), "forma-no-reconocida"))
    casos.append(("opuesta-al-autor admite degradacion declarada sin opuesta",
                  evaluar_composicion(op_autor, [w("a", "codex", "D")],
                                      {"autor": "codex", "familias": ["codex"],
                                       "degradacion": "same-family"}), None))
    casos.append(("opuesta-al-autor rechaza degradacion con worker opuesto disponible",
                  evaluar_composicion(op_autor, [w("a", "claude", "D")],
                                      {"autor": "codex", "familias": ["codex", "claude"],
                                       "degradacion": "same-family"}),
                  "familia-invalida: se declaro degradacion"))
    casos.append(("opuesta-al-autor rechaza degradacion no declarada",
                  evaluar_composicion(op_autor, [w("a", "codex", "D")],
                                      {"autor": "codex", "familias": ["codex"]}),
                  "familia-invalida"))
    casos.append(("opuesta-al-autor rechaza degradacion con opuesta disponible",
                  evaluar_composicion(op_autor, [w("a", "codex", "D")],
                                      {"autor": "codex", "familias": ["codex", "claude"],
                                       "degradacion": "same-family"}), "familia-invalida"))
    casos.append(("opuesta-al-autor rechaza worker fuera del inventario",
                  evaluar_composicion(op_autor, [w("a", "claude", "D")],
                                      {"autor": "codex", "familias": ["codex"]}),
                  "familia-invalida"))
    casos.append(("opuesta-al-autor rechaza worker ajeno con opuesta disponible",
                  evaluar_composicion(op_autor, [w("a", "tercera", "D")],
                                      {"autor": "codex", "familias": ["codex", "claude"]}),
                  "familia-invalida: el worker a se previo tercera fuera del inventario resuelto"))
    mis = fila(cardinalidad="n-acotado", familias="misma-que-el-conductor")
    casos.append(("misma-que-el-conductor con la del conductor",
                  evaluar_composicion(mis, [w("a", "claude", "D")], {"tope": 2, "conductor": "claude"}),
                  None))
    casos.append(("misma-que-el-conductor con otra familia",
                  evaluar_composicion(mis, [w("a", "codex", "D")], {"tope": 2, "conductor": "claude"}),
                  "familia-invalida"))
    cont = fila(cardinalidad="n-acotado", familias="continuacion-del-anterior")
    previo = {"tope": 2, "anterior": [{"key": "a", "family": "codex", "assignment_digest": "D0"}]}
    casos.append(("continuacion-del-anterior con la familia heredada",
                  evaluar_composicion(cont, [w("a", "codex", "D")], previo), None))
    casos.append(("continuacion-del-anterior con otra familia",
                  evaluar_composicion(cont, [w("a", "claude", "D")], previo), "familia-invalida"))
    casos.append(("continuacion-del-anterior sin intento previo para esa clave",
                  evaluar_composicion(cont, [w("z", "codex", "D")], previo), "familia-invalida"))
    casos.append(("continuacion-del-anterior sin anterior en el dominio",
                  evaluar_composicion(cont, [w("a", "codex", "D")], {"tope": 2}), "forma-no-reconocida"))
    ind = fila(cardinalidad="n-acotado", familias="indiferente", encargos="distinto-por-worker")
    uno_ind = {"cardinalidad": "1", "familias": "indiferente", "encargos": "no-aplica",
               "deadline": "propio-por-worker"}
    casos.append(("indiferente no mira la familia",
                  evaluar_composicion(ind, [w("a", "codex", "D"), w("b", "codex", "E")], {"tope": 2}),
                  None))

    # --- encargos: los cinco valores ---
    casos.append(("identico-por-digest con digests iguales",
                  evaluar_composicion(dual, [w("a", "codex", "D"), w("b", "claude", "D")], inv), None))
    casos.append(("identico-por-digest con digests distintos",
                  evaluar_composicion(dual, [w("a", "codex", "D"), w("b", "claude", "E")], inv),
                  "encargo-divergente"))
    nuc = fila(encargos="nucleo-comun")
    casos.append(("nucleo-comun con anexos distintos y nucleo igual",
                  evaluar_composicion(nuc, [{**w("a", "codex", "D"), "nucleo_digest": "N"},
                                            {**w("b", "claude", "E"), "nucleo_digest": "N"}], inv), None))
    casos.append(("nucleo-comun con nucleos distintos",
                  evaluar_composicion(nuc, [{**w("a", "codex", "D"), "nucleo_digest": "N"},
                                            {**w("b", "claude", "E"), "nucleo_digest": "M"}], inv),
                  "encargo-divergente"))
    casos.append(("distinto-por-worker con encargos distintos",
                  evaluar_composicion(ind, [w("a", "codex", "D"), w("b", "codex", "E")], {"tope": 2}),
                  None))
    casos.append(("distinto-por-worker con encargos iguales",
                  evaluar_composicion(ind, [w("a", "codex", "D"), w("b", "codex", "D")], {"tope": 2}),
                  "encargo-divergente"))
    delta = fila(cardinalidad="n-acotado", familias="indiferente", encargos="delta-sobre-el-anterior")
    casos.append(("delta-sobre-el-anterior con un encargo nuevo",
                  evaluar_composicion(delta, [w("a", "codex", "D1")], previo), None))
    casos.append(("delta-sobre-el-anterior repitiendo el encargo anterior",
                  evaluar_composicion(delta, [w("a", "codex", "D0")], previo), "encargo-divergente"))
    casos.append(("delta-sobre-el-anterior sin anterior en el dominio",
                  evaluar_composicion(delta, [w("a", "codex", "D1")], {"tope": 2}),
                  "forma-no-reconocida"))

    # --- evaluar_corrida ---
    # cada worker con SU vencimiento: el positivo con un deadline compartido era, en sí mismo, la
    # violación que `deadline-compartido` nombra — pasaba porque el predicado miraba presencia.
    esp = [w("a", "codex", "D", "2026-01-01T00:00:00Z"), w("b", "claude", "D", "2026-01-01T00:10:00Z")]
    efe = [e("a", "codex", "D", "2026-01-01T00:00:00Z"), e("b", "claude", "D", "2026-01-01T00:10:00Z")]
    casos.append(("corrida conforme", evaluar_corrida(dual, esp, efe), None))
    # las dos direcciones del colapso que el reviewer reprodujo: antes daban None, porque el mapa
    # se comía una entrada y los dos tamaños coincidían por la pérdida.
    # las entradas que colisionan son IDÉNTICAS salvo el vencimiento, y eso es deliberado: con
    # familias o digests distintos el caso lo cazaba `familia-invalida` por otra razón, y el rojo
    # mentía sobre qué se estaba probando. Sobre entradas iguales, el colapso es lo único que queda.
    casos.append(("dos previstos con la misma clave frente a un efectivo",
                  evaluar_corrida(dual, [w("a", "codex", "D", "T1"), w("a", "codex", "D", "T2")],
                                  [e("a", "codex", "D", "T1")]), "forma-no-reconocida"))
    casos.append(("un previsto frente a dos efectivos con la misma clave",
                  evaluar_corrida(dual, [w("a", "codex", "D", "T1")],
                                  [e("a", "codex", "D", "T1"), e("a", "codex", "D", "T2")]),
                  "forma-no-reconocida"))
    casos.append(("efectivo sin clave de correlacion",
                  evaluar_corrida(dual, esp, [e("a", "codex", "D", "T1"), e(None, "claude", "D", "T2")]),
                  "forma-no-reconocida"))
    casos.append(("dos workers comparten el mismo vencimiento",
                  evaluar_corrida(dual, [w("a", "codex", "D", "T"), w("b", "claude", "D", "T2")],
                                  [e("a", "codex", "D", "T"), e("b", "claude", "D", "T")]),
                  "deadline-invalido"))
    casos.append(("previsto sin despachar",
                  evaluar_corrida(dual, esp, [e("a", "codex", "D", "2026-01-01T00:00:00Z")]),
                  "fan-out-incompleto"))
    casos.append(("despachado sin prever",
                  evaluar_corrida(dual, esp, efe + [e("c", "codex", "D", "T3")]),
                  "despacho-no-previsto"))
    casos.append(("familia distinta de la prevista",
                  evaluar_corrida(dual, esp, [e("a", "codex", "D", "2026-01-01T00:00:00Z"),
                                              e("b", "codex", "D", "2026-01-01T00:10:00Z")]),
                  "familia-invalida"))
    casos.append(("encargo distinto del previsto",
                  evaluar_corrida(dual, esp, [e("a", "codex", "D", "2026-01-01T00:00:00Z"),
                                              e("b", "claude", "E", "2026-01-01T00:10:00Z")]),
                  "encargo-divergente"))
    casos.append(("worker sin vencimiento propio",
                  evaluar_corrida(dual, esp, [e("a", "codex", "D", "2026-01-01T00:00:00Z"),
                                              e("b", "claude", "D", None)]),
                  "deadline-invalido"))

    # --- operandos ausentes: la ausencia se comportaba como coincidencia ---
    casos.append(("family ausente donde la fila la compara",
                  evaluar_composicion(fila(cardinalidad="n-acotado", familias="opuesta-al-conductor"),
                                      [{"key": "a", "family": None, "assignment_digest": "D"}],
                                      {"tope": 2, "conductor": "claude"}), "forma-no-reconocida"))
    casos.append(("family vacía donde la fila la compara",
                  evaluar_composicion(dual, [w("a", "", "D"), w("b", "claude", "D")], inv),
                  "forma-no-reconocida"))
    casos.append(("los dos assignment_digest ausentes con identidad exigida",
                  evaluar_composicion(dual, [{"key": "a", "family": "codex", "assignment_digest": None},
                                             {"key": "b", "family": "claude", "assignment_digest": None}],
                                      inv), "forma-no-reconocida"))
    casos.append(("nucleo_digest ausente donde nucleo-comun lo exige",
                  evaluar_composicion(nuc, [w("a", "codex", "D"), w("b", "claude", "E")], inv),
                  "forma-no-reconocida"))
    casos.append(("nucleo_digest presente donde la sede lo quiere ausente",
                  evaluar_composicion(dual, [{**w("a", "codex", "D"), "nucleo_digest": "N"},
                                             {**w("b", "claude", "D"), "nucleo_digest": "N"}], inv),
                  "forma-no-reconocida"))
    casos.append(("corrida con family y digest ausentes en las dos listas",
                  evaluar_corrida(dual,
                                  [{"key": "a", "family": None, "assignment_digest": None, "deadline": "T1"},
                                   {"key": "b", "family": None, "assignment_digest": None, "deadline": "T2"}],
                                  [{"key": "a", "family": None, "digests": [None], "deadlines": ["T1"]},
                                   {"key": "b", "family": None, "digests": [None], "deadlines": ["T2"]}]),
                  "forma-no-reconocida"))

    # --- la ronda inicial DECLARADA, que es un dato y no un dato que falta ---
    inicial = {"tope": 2, "cardinal": 1, "conductor": "claude", "anterior": []}
    casos.append(("delta-sobre-el-anterior en una ronda inicial declarada",
                  evaluar_composicion(delta, [w("a", "codex", "D1")], inicial), None))
    casos.append(("delta-sobre-el-anterior con el campo AUSENTE sigue fallando cerrado",
                  evaluar_composicion(delta, [w("a", "codex", "D1")], {"tope": 2}),
                  "forma-no-reconocida"))
    casos.append(("continuacion-del-anterior no puede continuar una ronda inicial vacía",
                  evaluar_composicion(cont, [w("a", "codex", "D")], inicial), "familia-invalida"))

    # --- la reanudación: varios intentos con su digest por ronda ---
    esp_r = [w("revisor-codex", "codex", "sha256:r1", "2026-01-01T00:00:00Z")]
    casos.append(("reanudación válida: r1 luego r2 sobre una fila de delta",
                  evaluar_corrida(delta, esp_r,
                                  [em("revisor-codex", "codex", ["sha256:r1", "sha256:r2"],
                                      ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"])]), None))
    casos.append(("reanudación que repite el encargo de la ronda anterior",
                  evaluar_corrida(delta, esp_r,
                                  [em("revisor-codex", "codex", ["sha256:r1", "sha256:r1"],
                                      ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"])]),
                  "encargo-divergente"))
    casos.append(("el PRIMER intento se despacho con otro encargo que el sellado",
                  evaluar_corrida(delta, esp_r,
                                  [em("revisor-codex", "codex", ["sha256:otro", "sha256:r2"],
                                      ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"])]),
                  "encargo-divergente"))
    casos.append(("relanzamiento con el MISMO encargo donde no hay delta declarado",
                  evaluar_corrida(uno_ind, [w("a", "codex", "D", "T1")],
                                  [em("a", "codex", ["D", "D"], ["T1", "T9"])]), None))
    casos.append(("un intento cambia de encargo donde la fila no declara delta",
                  evaluar_corrida(uno_ind, [w("a", "codex", "D", "T1")],
                                  [em("a", "codex", ["D", "E"], ["T1", "T9"])]),
                  "encargo-divergente"))
    casos.append(("un worker sin ningun intento",
                  evaluar_corrida(uno_ind, [w("a", "codex", "D", "T1")],
                                  [em("a", "codex", [], [])]), "forma-no-reconocida"))
    casos.append(("un digest ausente en el SEGUNDO intento",
                  evaluar_corrida(delta, esp_r,
                                  [em("revisor-codex", "codex", ["sha256:r1", None],
                                      ["2026-01-01T00:00:00Z", "T9"])]), "forma-no-reconocida"))

    # --- el deadline previsto, que era la única columna que el preflight no evaluaba ---
    casos.append(("composicion sin deadline previsto",
                  evaluar_composicion(dual, [{"key": "a", "family": "codex", "assignment_digest": "D"},
                                             {"key": "b", "family": "claude", "assignment_digest": "D"}],
                                      inv), "deadline-invalido"))
    casos.append(("dos previstos con el MISMO vencimiento",
                  evaluar_composicion(dual, [w("a", "codex", "D", "T"), w("b", "claude", "D", "T")],
                                      inv), "deadline-compartido"))
    casos.append(("dos previstos con vencimiento propio",
                  evaluar_composicion(dual, [w("a", "codex", "D", "T1"), w("b", "claude", "D", "T2")],
                                      inv), None))
    casos.append(("el efectivo vence en otro momento que el previsto sellado",
                  evaluar_corrida(dual, [w("a", "codex", "D", "T1"), w("b", "claude", "D", "T3")],
                                  [e("a", "codex", "D", "T2"), e("b", "claude", "D", "T4")]),
                  "deadline-invalido"))
    casos.append(("el efectivo vence cuando el previsto sellado decia",
                  evaluar_corrida(dual, [w("a", "codex", "D", "T1"), w("b", "claude", "D", "T3")],
                                  [e("a", "codex", "D", "T1"), e("b", "claude", "D", "T3")]), None))
    casos.append(("la reanudación abre su propia espera y el sellado no la gobierna",
                  evaluar_corrida(delta, esp_r,
                                  [em("revisor-codex", "codex", ["sha256:r1", "sha256:r2"],
                                      ["2026-01-01T00:00:00Z", "2026-06-06T06:06:06Z"])]), None))

    # --- los PUNTOS REALES del árbol, no filas sintéticas ---
    raiz = pathlib.Path(__file__).resolve().parents[3]
    if not (raiz / SEDE_ENUMS).is_file():
        casos.append(("la sede se resuelve desde el árbol", f"sede ilegible en {raiz}", None))
    else:
        r = lambda skill, punto: leer_fila(raiz, skill, punto)
        wr = lambda k, f, d, **extra: {"key": k, "family": f, "assignment_digest": d,
                                       "role": "w", "scope": "/w",
                                       "deadline": f"2026-01-01T00:00:00Z#{k}", **extra}
        f_cr = r("cross-review", "revisor por ronda")
        f_ce = r("co-explore", "worker por ronda del modo")
        f_ci = r("cross-implement", "implementador inicial")
        f_bb = r("bitbucket-code-review", "panel de revisores")
        f_ce_dual = r("co-explore", "fan-out dual")
        f_or = r("sdd-orchestrator", "fan-out por repo")
        for nombre, f in (("cross-review/revisor por ronda", f_cr),
                          ("co-explore/worker por ronda", f_ce),
                          ("cross-implement/implementador inicial", f_ci),
                          ("bitbucket-code-review/panel de revisores", f_bb),
                          ("co-explore/fan-out dual", f_ce_dual),
                          ("sdd-orchestrator/fan-out por repo", f_or)):
            casos.append((f"la fila real de {nombre} se lee del árbol", None if f else "fila ausente", None))
        if f_cr and f_ce and f_ci and f_bb and f_ce_dual and f_or:
            ronda_ini = {"cardinal": 1, "conductor": "claude", "anterior": []}
            casos.append(("REAL cross-review · ronda 1, sin intento previo",
                          evaluar_composicion(f_cr, [wr("ronda-1", "codex", "sha256:r1")], ronda_ini), None))
            casos.append(("REAL co-explore · debate ronda 0, sin intento previo",
                          evaluar_composicion(f_ce, [wr("ronda-0", "codex", "sha256:d0")], ronda_ini), None))
            # la transición REAL de la ronda 1 a la 2: el worker se reanuda, así que su clave es
            # ESTABLE y lo que cambia es el encargo. El caso anterior reusaba `ronda-1` para el
            # worker actual, así que no ejercía ninguna transición y pasaba por vacuidad.
            prev_r1 = [{"key": "revisor-codex", "family": "codex", "assignment_digest": "sha256:r1"}]
            casos.append(("REAL cross-review · transición ronda 1 -> 2 con delta real",
                          evaluar_composicion(f_cr, [wr("revisor-codex", "codex", "sha256:r2")],
                                              {"cardinal": 1, "conductor": "claude",
                                               "anterior": prev_r1}), None))
            casos.append(("REAL cross-review · ronda 2 repitiendo el encargo de la ronda 1",
                          evaluar_composicion(f_cr, [wr("revisor-codex", "codex", "sha256:r1")],
                                              {"cardinal": 1, "conductor": "claude",
                                               "anterior": prev_r1}), "encargo-divergente"))
            casos.append(("REAL cross-review · clave por ronda (ronda-2 contra ronda-1) no correlaciona",
                          evaluar_composicion(f_cr, [wr("ronda-2", "codex", "sha256:r2")],
                                              {"cardinal": 1, "conductor": "claude",
                                               "anterior": [{"key": "ronda-1", "family": "codex",
                                                             "assignment_digest": "sha256:r1"}]}),
                          "encargo-divergente"))
            casos.append(("REAL cross-review · anterior mal formado NO es una ronda inicial",
                          evaluar_composicion(f_cr, [wr("revisor-codex", "codex", "sha256:r2")],
                                              {"cardinal": 1, "conductor": "claude",
                                               "anterior": [{}]}), "forma-no-reconocida"))
            casos.append(("REAL cross-review · anterior sin assignment_digest",
                          evaluar_composicion(f_cr, [wr("revisor-codex", "codex", "sha256:r2")],
                                              {"cardinal": 1, "conductor": "claude",
                                               "anterior": [{"key": "revisor-codex",
                                                             "family": "codex",
                                                             "assignment_digest": None}]}),
                          "forma-no-reconocida"))
            casos.append(("REAL cross-review · anterior con la clave repetida",
                          evaluar_composicion(f_cr, [wr("revisor-codex", "codex", "sha256:r2")],
                                              {"cardinal": 1, "conductor": "claude",
                                               "anterior": [{"key": "k", "family": "codex", "assignment_digest": "A"},
                                                            {"key": "k", "family": "claude", "assignment_digest": "B"}]}),
                          "forma-no-reconocida"))
            casos.append(("REAL fan-out dual · encargos iguales con nucleos divergentes",
                          evaluar_composicion(f_ce_dual,
                                              [wr("codex", "codex", "D", nucleo_digest="N"),
                                               wr("claude", "claude", "D", nucleo_digest="M")], inv),
                          "encargo-divergente"))
            casos.append(("REAL fan-out dual · encargos iguales con el mismo nucleo",
                          evaluar_composicion(f_ce_dual,
                                              [wr("codex", "codex", "D", nucleo_digest="N"),
                                               wr("claude", "claude", "D", nucleo_digest="N")], inv), None))
            casos.append(("REAL fan-out por repo · duplicado PARCIAL de encargos (D, D, E)",
                          evaluar_composicion(f_or, [wr("a", "codex", "D"), wr("b", "codex", "D"),
                                                     wr("c", "codex", "E")], {"cardinal": 3}),
                          "encargo-divergente"))
            er = lambda k, f, digs, dls: {"key": k, "family": f, "digests": list(digs),
                                          "deadlines": list(dls)}
            casos.append(("REAL cross-review · reanudación de dos intentos con delta por ronda",
                          evaluar_corrida(f_cr, [wr("revisor-codex", "codex", "sha256:r1")],
                                          [er("revisor-codex", "codex", ["sha256:r1", "sha256:r2"],
                                              ["2026-01-01T00:00:00Z#revisor-codex", "2026-01-01T09:00:00Z"])]),
                          None))
            casos.append(("REAL cross-review · reanudación que repite el encargo",
                          evaluar_corrida(f_cr, [wr("revisor-codex", "codex", "sha256:r1")],
                                          [er("revisor-codex", "codex", ["sha256:r1", "sha256:r1"],
                                              ["2026-01-01T00:00:00Z#revisor-codex", "2026-01-01T09:00:00Z"])]),
                          "encargo-divergente"))
            casos.append(("REAL panel de revisores · vencimiento previsto compartido",
                          evaluar_composicion(f_bb, [{**wr("codex", "codex", "D"), "deadline": "T"},
                                                     {**wr("claude", "claude", "D"), "deadline": "T"}],
                                              inv), "deadline-compartido"))
            casos.append(("REAL panel de revisores · sin vencimiento previsto",
                          evaluar_composicion(f_bb, [{k: v for k, v in wr("codex", "codex", "D").items() if k != "deadline"},
                                                     {k: v for k, v in wr("claude", "claude", "D").items() if k != "deadline"}],
                                              inv), "deadline-invalido"))
            casos.append(("REAL fan-out por repo · tres encargos distintos",
                          evaluar_composicion(f_or, [wr("a", "codex", "D"), wr("b", "codex", "F"),
                                                     wr("c", "codex", "E")], {"cardinal": 3}), None))
            casos.append(("REAL co-explore · debate con la familia del conductor",
                          evaluar_composicion(f_ce, [wr("ronda-0", "claude", "sha256:d0")], ronda_ini),
                          "familia-invalida"))
            casos.append(("REAL cross-implement · implementador inicial con family ausente",
                          evaluar_composicion(f_ci, [wr("impl", None, "sha256:aa")], {"conductor": "claude"}),
                          "forma-no-reconocida"))
            casos.append(("REAL cross-implement · implementador inicial bien formado",
                          evaluar_composicion(f_ci, [wr("impl", "codex", "sha256:aa")], {"conductor": "claude"}),
                          None))
            casos.append(("REAL panel de revisores con los dos digests ausentes",
                          evaluar_composicion(f_bb, [wr("codex", "codex", None), wr("claude", "claude", None)],
                                              inv), "forma-no-reconocida"))
            casos.append(("REAL panel de revisores bien formado",
                          evaluar_composicion(f_bb, [wr("codex", "codex", "D"), wr("claude", "claude", "D")],
                                              inv), None))

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
