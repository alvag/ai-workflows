#!/usr/bin/env python3
"""Separa el presupuesto de espera CONTRACTUAL del de RECOLECCIÓN (AC-20).

Dos modos:

- `--presupuestos` — aplica la separación sobre las fuentes **reales**: la matriz de despachos, el
  pre-registro congelado, las observaciones y el baseline publicado. Comprueba que cada presupuesto
  contractual tenga valor y procedencia propios y que su procedencia **resuelva** contra su sede,
  que el presupuesto de recolección esté declarado en su propio namespace y **sin** procedencia, que
  el número declarado sea el que el harness realmente espera, y que ningún presupuesto llegue al
  baseline como dato medido.
- `--autotest-presupuestos` — control positivo y negativo del modo anterior. Cada causa del conjunto
  cerrado tiene un mutante que la produce, y se exige que lo haga **por su propia causa**: un
  mutante que cae por otra cláusula deja la suya sin ejercer.

**Por qué es un script propio y no un modo del instrumento (D-26).** El contrato los nombraba como
modos de `scripts/instrumento-baseline.py`, pero ese archivo está **congelado**: la tabla de
identidad adjudica `instrumento_sha256` como bloqueo, así que agregarle un modo después de medir
pone en rojo las trece observaciones ya producidas. D-20 previó la colisión solo para el acto 3
—«los modos del acto 3 se construyen en el acto 1»— y estos dos se cayeron por el hueco.

**Qué se importa del instrumento y qué no.** Se importa `resolver_procedencia`, el motor de
extracción anclada, porque escribir un segundo motor es exactamente lo que el flujo evitó al
portarlo: dos extractores del mismo valor divergen y el que se relaja es siempre el que corre sobre
los datos reales. **No** se importa ningún juicio: las cinco comprobaciones de acá son propias.
Importar no toca el archivo ni cambia su hash.
"""
import argparse
import copy
import importlib.util
import inspect
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

RAIZ = Path(__file__).resolve().parent.parent
DIR_SCRIPTS = RAIZ / "scripts"
RUTA_MATRIZ = DIR_SCRIPTS / "matriz-despachos.json"
RUTA_RECOLECCION = DIR_SCRIPTS / "presupuesto-de-recoleccion-fase-0.json"
RUTA_PREREGISTRO = DIR_SCRIPTS / "preregistro-fase-0.json"
RUTA_BASELINE = DIR_SCRIPTS / "baseline-fase-0.md"
RUTA_RUNNER = DIR_SCRIPTS / "runner-cohorte.py"
RUTA_INSTRUMENTO = DIR_SCRIPTS / "instrumento-baseline.py"

# La clave bajo la que cada fuente declara SU presupuesto. Que sean dos claves distintas en dos
# archivos distintos es la mitad estructural de AC-20; la otra mitad es que ninguna aparezca donde
# vive la otra, que es lo que comprueba `[B]`.
CLAVE_CONTRACTUAL = "presupuesto_de_espera_contractual"
CLAVE_RECOLECCION = "presupuesto_de_recoleccion"
NAMESPACE_RECOLECCION = "harness_de_medicion"

# El conjunto cerrado de causas. Cada una tiene un mutante que la produce en `--autotest-presupuestos`
# y el arnés exige que caiga por LA SUYA: sin eso, un mutante que cae por otra cláusula deja la suya
# sin ejercer y el verde no dice nada sobre ella.
CAUSAS = (
    "contractual_sin_valor",
    "contractual_sin_procedencia",
    "contractual_discordante_con_su_sede",
    "namespaces_fusionados",
    "contractual_copiado_a_recoleccion",
    "recoleccion_copiada_a_la_matriz",
    "recoleccion_ausente",
    "recoleccion_con_procedencia",
    "recoleccion_declarada_como_medida",
    "recoleccion_desviada_del_harness",
    "presupuesto_publicado_como_medido",
)


class Hallazgo(tuple):
    """`(causa, detalle)`. Tupla y no dataclass para que el arnés compare causas sin ceremonia."""

    def __new__(cls, causa: str, detalle: str):
        if causa not in CAUSAS:
            raise ValueError(f"causa fuera del conjunto cerrado: {causa!r}")
        return super().__new__(cls, (causa, detalle))

    @property
    def causa(self) -> str:
        return self[0]

    @property
    def detalle(self) -> str:
        return self[1]


def _instrumento():
    """El motor de extracción anclada, importado y no reescrito."""
    spec = importlib.util.spec_from_file_location("instrumento_baseline", RUTA_INSTRUMENTO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _runner():
    spec = importlib.util.spec_from_file_location("runner_cohorte", RUTA_RUNNER)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _id_del_punto(entrada: dict) -> str:
    valor = entrada.get("id")
    return valor.get("valor") if isinstance(valor, dict) and "valor" in valor else valor


# ---------------------------------------------------------------------------------------------
# Las cinco comprobaciones. Todas reciben los datos YA CARGADOS y ninguna lee del disco: el arnés
# muta copias en memoria y las vuelve a pasar por acá. Una comprobación que leyera su fuente ella
# misma ignoraría la mutación y quedaría verde sin haber mirado nada.
# ---------------------------------------------------------------------------------------------

def revisar_contractuales(matriz: dict, raiz: Path, instrumento: Any) -> list[Hallazgo]:
    """[A] Cada punto declara su presupuesto con valor y procedencia propios, y la procedencia
    RESUELVE contra su sede al mismo valor.

    Resolver es lo que separa un dato derivado de uno transcrito. Sin esta parte, un presupuesto con
    una procedencia decorativa —que apunta a cualquier lado— pasaría igual, y la sustitución que
    AC-20 prohíbe es justamente escribir otro número dejando la procedencia intacta.
    """
    problemas: list[Hallazgo] = []
    for entrada in matriz.get("puntos", []):
        punto = _id_del_punto(entrada)
        presupuesto = entrada.get(CLAVE_CONTRACTUAL)
        if not isinstance(presupuesto, dict) or "valor" not in presupuesto:
            problemas.append(Hallazgo(
                "contractual_sin_valor",
                f"`{punto}` no declara `{CLAVE_CONTRACTUAL}.valor`: sin valor propio, el "
                f"presupuesto del punto solo puede salir de otro lado"))
            continue
        procedencia = presupuesto.get("procedencia")
        if not isinstance(procedencia, dict) or "ausencia" in procedencia:
            problemas.append(Hallazgo(
                "contractual_sin_procedencia",
                f"`{punto}` declara valor `{presupuesto['valor']}` sin procedencia anclada: un "
                f"presupuesto contractual sin sede no es un hecho del ecosistema, es una "
                f"transcripción"))
            continue
        resultado = instrumento.resolver_procedencia(procedencia, raiz)
        if resultado.error is not None:
            problemas.append(Hallazgo(
                "contractual_discordante_con_su_sede",
                f"`{punto}`: la procedencia no resolvió ({resultado.error}) — "
                f"{resultado.detalle}"))
            continue
        if resultado.valor != presupuesto["valor"]:
            problemas.append(Hallazgo(
                "contractual_discordante_con_su_sede",
                f"`{punto}` declara `{presupuesto['valor']}` y su sede "
                f"`{procedencia.get('sede')}` dice `{resultado.valor}`"))
    return problemas


def revisar_namespaces(matriz: dict, recoleccion: dict) -> list[Hallazgo]:
    """[B] Los dos presupuestos viven en namespaces disjuntos y ninguno invade al otro.

    Es la comprobación estructural de AC-20: si la misma clave nombrara a los dos, «el presupuesto»
    sería ambiguo y leerlo del lado equivocado daría un número plausible sin que nada lo notara. En
    esta cohorte esa ambigüedad sería especialmente silenciosa, porque los dos son enteros de
    segundos y diez de los trece contractuales valen 600.
    """
    problemas: list[Hallazgo] = []
    declarado = (recoleccion.get(CLAVE_RECOLECCION) or {}).get("namespace")
    if declarado != NAMESPACE_RECOLECCION:
        problemas.append(Hallazgo(
            "namespaces_fusionados",
            f"el presupuesto de recolección declara el namespace `{declarado}` y no "
            f"`{NAMESPACE_RECOLECCION}`: sin namespace propio no hay dos campos, hay uno"))
    if CLAVE_CONTRACTUAL in recoleccion or CLAVE_CONTRACTUAL in (
            recoleccion.get(CLAVE_RECOLECCION) or {}):
        problemas.append(Hallazgo(
            "contractual_copiado_a_recoleccion",
            f"la declaración de recolección trae `{CLAVE_CONTRACTUAL}`: el presupuesto contractual "
            f"vive en la matriz, y copiarlo acá es la segunda fuente que AC-23 prohíbe"))
    for entrada in matriz.get("puntos", []):
        if CLAVE_RECOLECCION in entrada:
            problemas.append(Hallazgo(
                "recoleccion_copiada_a_la_matriz",
                f"`{_id_del_punto(entrada)}` declara `{CLAVE_RECOLECCION}` en la matriz: el "
                f"presupuesto del harness no es un atributo del punto que mide"))
    return problemas


def revisar_recoleccion(recoleccion: dict) -> list[Hallazgo]:
    """[C] El presupuesto de recolección está declarado, con valor, y SIN procedencia.

    La ausencia de procedencia no es un hueco: es la comprobación. Una procedencia ancla el valor a
    una sede externa y lo vuelve un dato derivado del ecosistema; dársela a una decisión de este
    flujo es exactamente la sustitución que AC-20 prohíbe, y quedaría escrita como si se hubiera
    medido.
    """
    problemas: list[Hallazgo] = []
    presupuesto = recoleccion.get(CLAVE_RECOLECCION)
    if not isinstance(presupuesto, dict) or not isinstance(presupuesto.get("valor_segundos"), int):
        problemas.append(Hallazgo(
            "recoleccion_ausente",
            "no hay `presupuesto_de_recoleccion.valor_segundos` entero: sin valor declarado, el "
            "tope con el que se midió no está en ninguna parte y el lector solo puede tomar el "
            "contractual"))
        return problemas
    if "procedencia" in presupuesto:
        problemas.append(Hallazgo(
            "recoleccion_con_procedencia",
            "el presupuesto de recolección declara una procedencia: anclarlo a una sede externa lo "
            "presenta como un hecho del ecosistema, y es una decisión de este flujo"))
    if presupuesto.get("es_dato_medido") is not False:
        problemas.append(Hallazgo(
            "recoleccion_declarada_como_medida",
            "el presupuesto de recolección no se declara como NO medido: `es_dato_medido` tiene "
            f"que ser `false` y es `{presupuesto.get('es_dato_medido')!r}`"))
    return problemas


def revisar_contra_el_harness(recoleccion: dict, tope_real: int | None,
                              detalle_de_lectura: str) -> list[Hallazgo]:
    """[D] El número declarado es el que el harness realmente espera.

    Declarado y no derivado, este valor puede desviarse en silencio. La lectura del runner es una
    OBSERVACIÓN sobre el declarante y no su fuente: si fuera la fuente, el número se estaría
    comprobando contra sí mismo. Y si no se puede leer, se falla fuerte — un tope que no se
    encuentra no es un tope que coincide.
    """
    presupuesto = recoleccion.get(CLAVE_RECOLECCION) or {}
    declarado = presupuesto.get("valor_segundos")
    if tope_real is None:
        return [Hallazgo("recoleccion_desviada_del_harness",
                         f"no se pudo leer el tope que el harness aplica: {detalle_de_lectura}")]
    if declarado != tope_real:
        return [Hallazgo(
            "recoleccion_desviada_del_harness",
            f"la declaración dice `{declarado}` s y el harness espera `{tope_real}` s")]
    return []


def revisar_publicacion(publicados: dict, recoleccion: dict) -> list[Hallazgo]:
    """[E] Ningún presupuesto llega al baseline como número medido.

    Es la cláusula literal de AC-20 —«el segundo no sustituye al primero como dato medido»— leída
    sobre el artefacto que se publica. Un presupuesto publicado sería una decisión de este flujo
    presentada como una medición del ecosistema, y el lector no tendría cómo distinguirla.
    """
    problemas: list[Hallazgo] = []
    valor_de_recoleccion = (recoleccion.get(CLAVE_RECOLECCION) or {}).get("valor_segundos")
    for metrica_id, numero in publicados.items():
        if "presupuesto" in str(metrica_id).lower():
            problemas.append(Hallazgo(
                "presupuesto_publicado_como_medido",
                f"`{metrica_id}` se publica como número medido y su identidad es la de un "
                f"presupuesto"))
            continue
        valor = numero[1] if isinstance(numero, (tuple, list)) else getattr(numero, "valor", None)
        if valor is not None and valor == valor_de_recoleccion:
            problemas.append(Hallazgo(
                "presupuesto_publicado_como_medido",
                f"`{metrica_id}` publica `{valor}`, que es el presupuesto de recolección: un tope "
                f"del harness no es una medición del ecosistema"))
    return problemas


# ---------------------------------------------------------------------------------------------
# Carga de las fuentes y lectura del tope real.
# ---------------------------------------------------------------------------------------------

def _cargar(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def tope_del_harness(runner: Any) -> tuple[int | None, str]:
    """El tope que el runner aplica de verdad, anclado a SU FUNCIÓN y no a un número de línea.

    `_correr` es el único punto por donde pasa todo comando que el runner observa —el despacho del
    worker incluido—, así que su `timeout` es el presupuesto de recolección efectivo. Se lee con
    `inspect` sobre la función: anclarlo a una línea lo volvería una guarda que un reordenamiento
    apaga sin que nadie lo note.
    """
    try:
        fuente = inspect.getsource(runner._correr)
    except (AttributeError, OSError) as exc:
        return None, f"no se pudo leer la fuente de `_correr`: {type(exc).__name__}"
    topes = re.findall(r"timeout=(\d+)", fuente)
    if len(topes) != 1:
        return None, (f"`_correr` declara {len(topes)} topes y se esperaba exactamente uno: con "
                      f"varios, cuál es el presupuesto de recolección deja de estar determinado")
    return int(topes[0]), ""


def numeros_publicados(instrumento: Any) -> tuple[dict, str]:
    if not RUTA_BASELINE.is_file():
        return {}, f"`{RUTA_BASELINE.name}` todavía no existe: se comprueba lo que sí hay"
    publicados, errores = instrumento.numeros_publicados_del_markdown(
        RUTA_BASELINE.read_text(encoding="utf-8"))
    return publicados, ("; ".join(errores) if errores else "")


def revisar_todo(matriz: dict, recoleccion: dict, publicados: dict, tope_real: int | None,
                 detalle_de_lectura: str, instrumento: Any, raiz: Path) -> list[Hallazgo]:
    """Las cinco comprobaciones sobre datos ya cargados. Es lo que el arnés muta y vuelve a pasar."""
    return (revisar_contractuales(matriz, raiz, instrumento)
            + revisar_namespaces(matriz, recoleccion)
            + revisar_recoleccion(recoleccion)
            + revisar_contra_el_harness(recoleccion, tope_real, detalle_de_lectura)
            + revisar_publicacion(publicados, recoleccion))


# ---------------------------------------------------------------------------------------------
# Modo `--presupuestos` (V41).
# ---------------------------------------------------------------------------------------------

def modo_presupuestos(args: argparse.Namespace) -> int:
    raiz = Path(args.arbol).resolve() if args.arbol else RAIZ
    instrumento = _instrumento()
    matriz = _cargar(RUTA_MATRIZ)
    recoleccion = _cargar(RUTA_RECOLECCION)
    tope_real, detalle = tope_del_harness(_runner())
    publicados, aviso = numeros_publicados(instrumento)

    hallazgos = revisar_todo(matriz, recoleccion, publicados, tope_real, detalle, instrumento, raiz)

    contractuales = [e.get(CLAVE_CONTRACTUAL, {}).get("valor")
                     for e in matriz.get("puntos", [])]
    declarado = (recoleccion.get(CLAVE_RECOLECCION) or {}).get("valor_segundos")
    print(f"presupuestos contractuales: {len(contractuales)} puntos, valores "
          f"{sorted({v for v in contractuales if v is not None})} — cada uno resuelto contra su sede")
    print(f"presupuesto de recolección: {declarado} s, namespace "
          f"`{(recoleccion.get(CLAVE_RECOLECCION) or {}).get('namespace')}`, sin procedencia y "
          f"comprobado contra el tope real del harness")
    print(f"números publicados revisados: {len(publicados)}"
          + (f" · aviso: {aviso}" if aviso else ""))
    menor = [v for v in contractuales if v is not None and declarado is not None and declarado < v]
    if menor:
        print(f"nota: el presupuesto de recolección ({declarado} s) es MENOR que el contractual en "
              f"{len(menor)} de {len(contractuales)} puntos — es un límite de la medición, no del "
              f"ecosistema, y por eso no se publica")
    print()
    for hallazgo in hallazgos:
        print(f"FALLA  [{hallazgo.causa}] {hallazgo.detalle}")
    if hallazgos:
        print(f"\nRESULTADO: FALLA — {len(hallazgos)} hallazgos")
        return 1
    print("RESULTADO: OK — contractual y recolección son campos distintos, cada contractual "
          "resuelve contra su sede y ningún presupuesto se publica como dato medido")
    return 0


# ---------------------------------------------------------------------------------------------
# Modo `--autotest-presupuestos` (V28).
#
# Cada mutante se aplica sobre una COPIA en memoria de las fuentes reales, nunca sobre el árbol: un
# mutante escrito en disco es indistinguible de un cambio real mientras dura, y si el proceso muere
# queda aplicado.
# ---------------------------------------------------------------------------------------------

def _sin_procedencia(matriz: dict, recoleccion: dict) -> tuple[dict, dict]:
    matriz["puntos"][0][CLAVE_CONTRACTUAL].pop("procedencia", None)
    return matriz, recoleccion


def _sin_valor(matriz: dict, recoleccion: dict) -> tuple[dict, dict]:
    matriz["puntos"][0][CLAVE_CONTRACTUAL].pop("valor", None)
    return matriz, recoleccion


def _contractual_sustituido(matriz: dict, recoleccion: dict) -> tuple[dict, dict]:
    """El mutante que da nombre a AC-20: el contractual pasa a llevar el valor del harness.

    La procedencia queda INTACTA, que es lo que lo hace difícil: la única forma de cazarlo es
    resolverla y comparar. Un chequeo que solo exigiera «tiene procedencia» lo dejaría pasar.
    """
    matriz["puntos"][0][CLAVE_CONTRACTUAL]["valor"] = (
        recoleccion[CLAVE_RECOLECCION]["valor_segundos"])
    return matriz, recoleccion


def _namespaces_fusionados(matriz: dict, recoleccion: dict) -> tuple[dict, dict]:
    recoleccion[CLAVE_RECOLECCION]["namespace"] = CLAVE_CONTRACTUAL
    return matriz, recoleccion


def _contractual_copiado(matriz: dict, recoleccion: dict) -> tuple[dict, dict]:
    recoleccion[CLAVE_CONTRACTUAL] = copy.deepcopy(matriz["puntos"][0][CLAVE_CONTRACTUAL])
    return matriz, recoleccion


def _recoleccion_copiada(matriz: dict, recoleccion: dict) -> tuple[dict, dict]:
    matriz["puntos"][0][CLAVE_RECOLECCION] = copy.deepcopy(recoleccion[CLAVE_RECOLECCION])
    return matriz, recoleccion


def _recoleccion_como_medida(matriz: dict, recoleccion: dict) -> tuple[dict, dict]:
    recoleccion[CLAVE_RECOLECCION]["es_dato_medido"] = True
    return matriz, recoleccion


def _recoleccion_ausente(matriz: dict, recoleccion: dict) -> tuple[dict, dict]:
    recoleccion[CLAVE_RECOLECCION].pop("valor_segundos", None)
    return matriz, recoleccion


def _recoleccion_con_procedencia(matriz: dict, recoleccion: dict) -> tuple[dict, dict]:
    recoleccion[CLAVE_RECOLECCION]["procedencia"] = copy.deepcopy(
        matriz["puntos"][0][CLAVE_CONTRACTUAL]["procedencia"])
    return matriz, recoleccion


def _recoleccion_desviada(matriz: dict, recoleccion: dict) -> tuple[dict, dict]:
    recoleccion[CLAVE_RECOLECCION]["valor_segundos"] += 1
    return matriz, recoleccion


# Cada entrada es `(causa propia, cascada declarada, descripción, mutación)`. El arnés exige que el
# conjunto de causas observado sea EXACTAMENTE `{propia} | cascada`: con un `in` alcanzaría que la
# causa aparezca entre otras, y un mutante que además rompe media docena de cláusulas pasaría por
# preciso. Cuando una mutación arrastra otra cláusula de verdad —quitar el valor de recolección lo
# vuelve, además, imposible de comparar contra el harness— eso se ESCRIBE acá en vez de tolerarse.
MUTANTES: tuple[tuple[str, tuple[str, ...], str,
                      Callable[[dict, dict], tuple[dict, dict]]], ...] = (
    ("contractual_sin_valor", (), "el presupuesto del punto pierde su valor", _sin_valor),
    ("contractual_sin_procedencia", (), "el presupuesto del punto pierde su sede",
     _sin_procedencia),
    ("contractual_discordante_con_su_sede", (),
     "el contractual queda con el valor del harness y su procedencia intacta",
     _contractual_sustituido),
    ("namespaces_fusionados", (), "la recolección se declara bajo el namespace del contractual",
     _namespaces_fusionados),
    ("contractual_copiado_a_recoleccion", (),
     "el contractual del primer punto se copia al archivo de recolección", _contractual_copiado),
    ("recoleccion_copiada_a_la_matriz", (),
     "la recolección se copia dentro del primer punto de la matriz", _recoleccion_copiada),
    ("recoleccion_ausente", ("recoleccion_desviada_del_harness",),
     "la recolección pierde su valor", _recoleccion_ausente),
    ("recoleccion_con_procedencia", (), "la recolección se ancla a la sede de un contractual",
     _recoleccion_con_procedencia),
    ("recoleccion_declarada_como_medida", (), "la recolección se declara como dato medido",
     _recoleccion_como_medida),
    ("recoleccion_desviada_del_harness", (), "la recolección declara un segundo más que el real",
     _recoleccion_desviada),
)


def _mutante_publicacion(publicados: dict, recoleccion: dict) -> dict:
    """El octavo mutante actúa sobre los números publicados y no sobre las dos fuentes."""
    copia = dict(publicados)
    copia["presupuesto-de-espera"] = ("presupuesto-de-espera",
                                      recoleccion[CLAVE_RECOLECCION]["valor_segundos"],
                                      "segundos", "—")
    return copia


def modo_autotest_presupuestos(args: argparse.Namespace) -> int:
    raiz = Path(args.arbol).resolve() if args.arbol else RAIZ
    instrumento = _instrumento()
    matriz = _cargar(RUTA_MATRIZ)
    recoleccion = _cargar(RUTA_RECOLECCION)
    tope_real, detalle = tope_del_harness(_runner())
    publicados, _ = numeros_publicados(instrumento)
    fallas: list[str] = []

    def correr(m: dict, r: dict, p: dict) -> list[Hallazgo]:
        return revisar_todo(m, r, p, tope_real, detalle, instrumento, raiz)

    # [POSITIVO] Las fuentes reales pasan. Sin esto, un predicado que siempre falla daría verde en
    # todos los negativos y el arnés no podría distinguirlo de una cobertura perfecta.
    limpio = correr(copy.deepcopy(matriz), copy.deepcopy(recoleccion), publicados)
    if limpio:
        fallas.append(f"las fuentes reales no pasan: {[h.causa for h in limpio]}")
    print(f"[POSITIVO] {'OK    ' if not limpio else 'FALLA '} las fuentes reales pasan las cinco "
          f"comprobaciones")

    # [NEGATIVOS] Cada mutante tiene que caer, y caer POR SU CAUSA: uno que cae por otra cláusula
    # deja la suya sin ejercer y el verde global lo tapa.
    ejercidas: set[str] = set()
    for causa_esperada, cascada, descripcion, mutar in MUTANTES:
        original = (copy.deepcopy(matriz), copy.deepcopy(recoleccion))
        m, r = mutar(copy.deepcopy(matriz), copy.deepcopy(recoleccion))
        # Un mutante que no cambia nada da un verde que parece cobertura: el negativo «pasó» porque
        # nunca hubo defecto que detectar. Se exige que haya mutado antes de creerle al resultado.
        if (m, r) == original:
            fallas.append(f"`{causa_esperada}`: la mutación no cambió nada ({descripcion})")
            print(f"[{causa_esperada}] FALLA  {descripcion} — mutante inerte")
            continue
        causas = {h.causa for h in correr(m, r, publicados)}
        esperadas = {causa_esperada} | set(cascada)
        if causas == esperadas:
            ejercidas.add(causa_esperada)
            estado = "OK    "
        else:
            faltan, sobran = sorted(esperadas - causas), sorted(causas - esperadas)
            fallas.append(f"`{causa_esperada}`: causas observadas {sorted(causas)} ≠ esperadas "
                          f"{sorted(esperadas)}"
                          + (f" · sin ejercer: {faltan}" if faltan else "")
                          + (f" · no declaradas: {sobran}" if sobran else ""))
            estado = "FALLA "
        print(f"[{causa_esperada}] {estado} {descripcion}")

    # El octavo, sobre los números publicados.
    hallazgos = revisar_publicacion(_mutante_publicacion(publicados, recoleccion), recoleccion)
    causas = {h.causa for h in hallazgos}
    if "presupuesto_publicado_como_medido" not in causas:
        fallas.append("un presupuesto publicado como número medido no fue detectado")
    else:
        ejercidas.add("presupuesto_publicado_como_medido")
    print(f"[presupuesto_publicado_como_medido] "
          f"{'OK    ' if 'presupuesto_publicado_como_medido' in causas else 'FALLA '} "
          f"un presupuesto se publica como número medido del baseline")

    # El conjunto cerrado se acumula CORRIENDO, nunca transcrito: una causa declarada que ningún
    # mutante produce es cobertura fantasma, y se ve exigiendo que los dos conjuntos coincidan.
    huerfanas = set(CAUSAS) - ejercidas
    if huerfanas:
        fallas.append(f"causas sin mutante que las produzca: {sorted(huerfanas)}")
    print(f"\ncausas del conjunto cerrado: {len(CAUSAS)} · ejercidas corriendo: {len(ejercidas)}")

    for falla in fallas:
        print(f"FALLA  {falla}")
    if fallas:
        print(f"\nRESULTADO: FALLA — {len(fallas)} controles en rojo")
        return 1
    print(f"\nRESULTADO: OK — {len(CAUSAS)} controles en verde, cada uno con su mutante y cada "
          f"mutante cayendo por su causa")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="verificar-presupuestos.py",
        description="Separa el presupuesto de espera contractual del de recolección (AC-20).")
    parser.add_argument("--presupuestos", action="store_true",
                        help="aplica la separación sobre matriz, pre-registro, observaciones y "
                             "baseline reales")
    parser.add_argument("--autotest-presupuestos", action="store_true",
                        help="control positivo y negativo del modo anterior")
    parser.add_argument("--arbol", metavar="<dir>",
                        help="la raíz contra la que se resuelven las sedes (por defecto, este repo)")
    args = parser.parse_args()
    if args.presupuestos and args.autotest_presupuestos:
        parser.error("un modo por invocación")
    if args.autotest_presupuestos:
        return modo_autotest_presupuestos(args)
    if args.presupuestos:
        return modo_presupuestos(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
