#!/usr/bin/env python3
"""Arnés de extracción del dossier de una task: censo del corpus, fixtures del contrato y medición.

Implementa **R1–R9** del contrato de extracción (`.plans/dossier-arnes/contrato-extraccion.md`,
v13, `sha256 224167cf9d48ee40bc0a81e521051a0fa2ae047e2fff748cfa57c3e05555dadb`) y las prueba contra
los tres insumos congelados del árbol versionado. Tres subcomandos, y solo tres:

    censo            compara el corpus descubierto contra el declarado, clasifica las exclusiones
                     con el enum cerrado y emite su hash de identidad
    fixtures         corre cada caso del manifest congelado y los vectores propios del arnés
    medir-historico  publica el intervalo de reducción, consumiendo el conjunto de exclusiones
                     que emitió el censo

**Falla ruidoso a propósito.** Un dossier incompleto se lee igual que uno completo, así que cada
pieza que una task cita y no resuelve es una causa nombrada del enum, nunca una omisión silenciosa.
El predecesor de este archivo informaba «todas las referencias citadas resuelven» mientras 213 de
310 tasks salían sin un solo AC: no había ninguna que resolver, y cero es indistinguible de «no hay»
si nadie lo mira. Ese es el modo de fallo que el control positivo de AC-11 existe para cerrar.

**Las cuatro capas, en este orden dentro del archivo** (contrato interno del flujo `dossier-arnes`):

1. tipos y constantes cerradas — sin lógica, sin I/O;
2. funciones puras — reciben lo que necesitan por parámetro y **no imprimen nunca**. Tocan disco
   **exactamente dos**: `cargar_insumo` y `cargar_instantanea_verificada`;
3. casos de uso — `ejecutar_censo`, `ejecutar_fixtures`, `ejecutar_medicion`: devuelven `dict`, no
   imprimen ni llaman a `sys.exit`;
4. CLI — la **única** capa que imprime y que decide el código de salida.

`stdout` lleva exactamente un objeto JSON por invocación; todo diagnóstico humano va a `stderr`.
Se **porta, no se importa**: nada viene de `scripts/verificar-oraculo.py` ni de
`scripts/instrumento-baseline.py`, que son sedes congeladas gobernadas por otras guardas.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import statistics
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Callable, NamedTuple

# ════════════════════════════════════════════════════════════════════════════════════════════
# CAPA 1 — Tipos y constantes cerradas
# ════════════════════════════════════════════════════════════════════════════════════════════

RAIZ = Path(".")
RUTA_CORPUS = Path("scripts/corpus-dossier.json")
RUTA_CASOS = Path("scripts/casos-extraccion.json")
RUTA_ORACULO = Path("scripts/oraculo-cobertura.json")
SCHEMA_CORPUS = Path("scripts/corpus-dossier.schema.json")
SCHEMA_CASOS = Path("scripts/casos-extraccion.schema.json")
SCHEMA_ORACULO = Path("scripts/oraculo-cobertura.schema.json")

EXIT_OK = 0
EXIT_HALLAZGOS = 1
EXIT_INVOCACION = 2


class Identificador(NamedTuple):
    """Un id de R1: familia (`AC` o `T`), número y sufijo alfabético.

    El sufijo es **parte del id** y es sensible a mayúsculas: `T15A` y `T15a` son distintos, y
    `AC-14b` no es `AC-14`. El patrón que este archivo reemplazó enumeraba un sufijo
    (`AC-\\d+bis|AC-\\d+`) en vez de admitir la familia, y medido sobre `**AC-14b:**` **no
    matcheaba**: tras `AC-14` el lookahead exigía un delimitador y encontraba la `b`. O sea que
    perdía ids que el corpus congelado sí tiene."""
    familia: str
    numero: int
    sufijo: str

    def __str__(self) -> str:
        sep = "-" if self.familia == "AC" else ""
        return f"{self.familia}{sep}{self.numero}{self.sufijo}"


# Las dieciséis causas de AC-5, en el orden en que se serializan: es el orden de la tabla del AC,
# por grupo. El enum es **cerrado**: una exclusión que no encaje en ninguna es un error del arnés,
# no una exclusión silenciosa, y el censo la reporta como tal.
CAUSAS: tuple[str, ...] = (
    # cobertura (R2)
    "sin_cobertura",
    "cobertura_en_conflicto",
    # filas (R3)
    "fila_duplicada",
    "fila_inexistente",
    # duplicados (R4)
    "duplicado_normativo",
    # piezas consumidas (R5)
    "consume_no_tipado",
    "task_consumida_inexistente",
    "sin_produce",
    "bloque_global_inexistente",
    "bloque_global_duplicado",
    "bloque_global_ambiguo",
    # piezas siempre presentes (R5)
    "ac_inexistente",
    "enfoque_ausente",
    # rangos (R1)
    "rango_invertido",
    "extremo_inexistente",
    "rango_mixto",
)
ORDEN_DE_CAUSA = {c: i for i, c in enumerate(CAUSAS)}

# El mapa clase → rótulo de R7, literal y cerrado, **en el orden de la proyección canónica**. Un
# rótulo por clase **no vacía**, no por pieza. Los rótulos cuentan en el denominador: son bytes que
# el agente ingiere y que hoy no existen, y no contarlos haría ver la reducción mejor de lo que es.
ROTULOS: tuple[tuple[str, str], ...] = (
    ("task", "=== TASK ==="),
    ("ac", "=== CRITERIOS DE ACEPTACIÓN ==="),
    ("filas", "=== FILAS DEL CONTRATO ==="),
    ("produce", "=== INTERFACES QUE CONSUMES ==="),
    ("bloques_globales", "=== BLOQUES GLOBALES ==="),
    ("enfoque", "=== ENFOQUE DEL PLAN ==="),
)
ORDEN_DE_CLASE = {c: i for i, (c, _) in enumerate(ROTULOS)}

# Las tres fuentes de cobertura de R2, en orden de precedencia. Los nombres son los que usa
# `scripts/oraculo-cobertura.json` en su campo `fuente_r2`: el control positivo de AC-11 compara
# contra ese insumo, y dos vocabularios para el mismo hecho harían fallar la comparación por
# nomenclatura en vez de por contenido.
FUENTES_R2: tuple[str, ...] = ("cubre", "campo_con_vineta", "campo_sin_vineta")

# ─── Los esquemas de las tres salidas ───────────────────────────────────────────────────────
#
# Van embebidos como constantes cerradas y no como archivos `*.schema.json` hermanos: el alcance
# declarado de este flujo es el parser y el roadmap, y tres archivos nuevos entrarían al inventario
# de guardas de `CLAUDE.md` con su propio mantenimiento. El precio aceptado es que ninguna
# herramienta externa los consume. Cada handler del CLI valida su propio resultado contra su
# constante **antes** de serializarlo, así que la ausencia de un campo obligatorio falla igual.
#
# Los `required` están copiados de la tabla normativa de AC-8, y `autotest_esquemas_rechazan` los
# compara contra esa tabla: un esquema que valide solo su propia implementación es autorreferencial
# y pasa siempre.

_TERNA = {
    "type": "object", "additionalProperties": False,
    "required": ["flujo", "task_id", "ocurrencia"],
    "properties": {"flujo": {"type": "string"}, "task_id": {"type": "string"},
                   "ocurrencia": {"type": "integer", "minimum": 1}},
}
# `por_flujo[]` tiene **una sola** definición y es por flujo, no por terna: la tabla de AC-8 la fija
# y la primera redacción de la spec la describía con dos granularidades incompatibles.
_POR_FLUJO = {
    "type": "object", "additionalProperties": False,
    "required": ["flujo", "tasks_totales", "elegibles", "excluidas", "tasa_elegibilidad",
                 "degradado"],
    "properties": {
        "flujo": {"type": "string"},
        "tasks_totales": {"type": "integer", "minimum": 0},
        "elegibles": {"type": "integer", "minimum": 0},
        "excluidas": {"type": "integer", "minimum": 0},
        "tasa_elegibilidad": {"type": "number", "minimum": 0, "maximum": 1},
        "degradado": {"type": "boolean"},
    },
}
_FLUJO_CON_CAUSA = {
    "type": "object", "additionalProperties": False,
    "required": ["flujo", "causa", "tasa"],
    "properties": {"flujo": {"type": "string"}, "causa": {"type": "string"},
                   "tasa": {"type": "number", "minimum": 0, "maximum": 1}},
}
_DECLARACION = {
    "type": "object", "additionalProperties": False,
    "required": ["flujo", "task_id", "fuente_r2", "ac"],
    "properties": {"flujo": {"type": "string"}, "task_id": {"type": "string"},
                   "fuente_r2": {"type": "string"}, "ac": {"type": "string"}},
}

SCHEMA_CENSO: dict = {
    "type": "object", "additionalProperties": False,
    "required": ["declarados", "descubiertos", "sobran", "faltan", "hash_mismatch",
                 "tasks_excluidas", "hash_exclusiones", "denominador_tasks", "piso", "por_flujo",
                 "cobertura_por_fuente_r2", "perdidas_vs_esperado", "sobran_vs_esperado",
                 "maximo_corpus"],
    "properties": {
        # `declarados` y `descubiertos` son cardinalidades; la comparación de **conjuntos** que
        # exige AC-4 la hacen `sobran` y `faltan`, que enumeran las ternas de cada diferencia. Una
        # task perdida y una espuria dejan las dos listas no vacías aunque las cardinalidades
        # coincidan: comparar cantidades es exactamente lo que deja que se compensen.
        "declarados": {"type": "integer", "minimum": 0},
        "descubiertos": {"type": "integer", "minimum": 0},
        "sobran": {"type": "array", "items": _TERNA},
        "faltan": {"type": "array", "items": _TERNA},
        "hash_mismatch": {
            "type": "array",
            "items": {"type": "object", "additionalProperties": False,
                      "required": ["flujo", "artefacto", "campo", "esperado", "hallado"],
                      "properties": {"flujo": {"type": "string"},
                                     "artefacto": {"type": "string"},
                                     "campo": {"type": "string"},
                                     "esperado": {"type": "string"},
                                     "hallado": {"type": "string"}}},
        },
        "tasks_excluidas": {
            "type": "array",
            "items": {"type": "object", "additionalProperties": False,
                      "required": ["flujo", "task_id", "ocurrencia", "causas"],
                      "properties": {"flujo": {"type": "string"},
                                     "task_id": {"type": "string"},
                                     "ocurrencia": {"type": "integer", "minimum": 1},
                                     "causas": {"type": "array", "minItems": 1,
                                                "uniqueItems": True,
                                                "items": {"type": "string",
                                                          "enum": list(CAUSAS)}}}},
        },
        "hash_exclusiones": {"type": "string", "minLength": 64},
        "denominador_tasks": {"type": "integer", "minimum": 0},
        "piso": {"type": "number", "minimum": 0, "maximum": 1},
        "por_flujo": {"type": "array", "items": _POR_FLUJO},
        "cobertura_por_fuente_r2": {
            "type": "object", "additionalProperties": False,
            "required": list(FUENTES_R2),
            "properties": {f: {"type": "object", "additionalProperties": False,
                               "required": ["declaradas", "resueltas", "ocurrencias_reconocidas",
                                            "fuentes_efectivas"],
                               "properties": {"declaradas": {"type": "integer", "minimum": 0},
                                              "resueltas": {"type": "integer", "minimum": 0},
                                              "ocurrencias_reconocidas": {"type": "integer",
                                                                          "minimum": 0},
                                              "fuentes_efectivas": {"type": "integer",
                                                                    "minimum": 0}}}
                           for f in FUENTES_R2},
        },
        "perdidas_vs_esperado": {"type": "array", "items": _DECLARACION},
        "sobran_vs_esperado": {"type": "array", "items": _DECLARACION},
        # Campo propio de este flujo, no de la tabla de AC-8: AC-9 exige que **el censo derive** el
        # máximo del corpus, y la tabla no enumera ningún campo donde emitirlo. Sin él, la
        # verificación de V9 lo recalcularía por fuera y se perdería la procedencia que AC-9 pide.
        # No contradice AC-8, que enumera un mínimo: los trece siguen estando.
        "maximo_corpus": {"type": "object", "additionalProperties": False,
                          "required": ["flujo", "bytes"],
                          "properties": {"flujo": {"type": "string"},
                                         "bytes": {"type": "integer", "minimum": 0}}},
        "causas_fuera_del_enum": {"type": "array", "items": {"type": "string"}},
        "hallazgos": {"type": "array", "items": {"type": "string"}},
    },
}

SCHEMA_FIXTURES: dict = {
    "type": "object", "additionalProperties": False,
    "required": ["manifest_sha256", "casos_totales", "casos_ok", "divergencias"],
    "properties": {
        "manifest_sha256": {"type": "string", "minLength": 64},
        "casos_totales": {"type": "integer", "minimum": 0},
        "casos_ok": {"type": "integer", "minimum": 0},
        "divergencias": {
            "type": "array",
            "items": {"type": "object", "additionalProperties": False,
                      "required": ["caso_id", "esperado", "obtenido"],
                      "properties": {"caso_id": {"type": "string"},
                                     "regla": {"type": "string"},
                                     "esperado": {"type": "string"},
                                     "obtenido": {"type": "string"}}},
        },
        # Los vectores propios se cuentan **aparte** de los casos del manifest: mezclarlos
        # permitiría un verde con la mitad de los casos contados fuera del manifest, y
        # `manifest_sha256` responde solo por lo que ese archivo congela.
        "vectores_propios_totales": {"type": "integer", "minimum": 0},
        "vectores_propios_ok": {"type": "integer", "minimum": 0},
    },
}

_INTERVALO = {
    "type": "object", "additionalProperties": False,
    "required": ["cota_inferior", "cota_superior", "denominador"],
    "properties": {"cota_inferior": {"type": "integer", "minimum": 0},
                   "cota_superior": {"type": "integer", "minimum": 0},
                   "denominador": {"type": "integer", "minimum": 0},
                   "reduccion_inferior": {"type": "number", "minimum": 0},
                   "reduccion_superior": {"type": "number", "minimum": 0}},
}

SCHEMA_MEDICION: dict = {
    "type": "object", "additionalProperties": False,
    "required": ["poblacion", "elegibles", "flujos_incluidos", "flujos_degradados",
                 "proporcion_retenida", "hash_exclusiones", "cota_inferior", "cota_superior",
                 "denominador", "mediana_intervalo", "por_flujo", "implementer", "reviewer",
                 "par"],
    "properties": {
        "poblacion": {"type": "integer", "minimum": 0},
        "elegibles": {"type": "integer", "minimum": 0},
        "flujos_incluidos": {"type": "array", "items": _FLUJO_CON_CAUSA},
        "flujos_degradados": {"type": "array", "items": _FLUJO_CON_CAUSA},
        "proporcion_retenida": {"type": "number", "minimum": 0, "maximum": 1},
        "hash_exclusiones": {"type": "string", "minLength": 64},
        "cota_inferior": {"type": "integer", "minimum": 0},
        "cota_superior": {"type": "integer", "minimum": 0},
        "denominador": {"type": "integer", "minimum": 0},
        "mediana_intervalo": {
            "type": "object", "additionalProperties": False,
            "required": ["inferior", "superior"],
            "properties": {"inferior": {"type": "number", "minimum": 0},
                           "superior": {"type": "number", "minimum": 0}},
        },
        # Misma definición que en el censo: la tabla de AC-8 fija **una sola** por campo.
        "por_flujo": {"type": "array", "items": _POR_FLUJO},
        # AC-6 exige la reducción **por flujo**, con la cota de *ese* flujo. Sin un campo donde
        # emitirla no hay dónde verificarla, así que va acá, con la misma justificación con la que
        # el censo emite `maximo_corpus`.
        "intervalo_por_flujo": {
            "type": "array",
            "items": {"type": "object", "additionalProperties": False,
                      "required": ["flujo", "cota_inferior", "cota_superior", "denominador",
                                   "reduccion_inferior", "reduccion_superior", "tasks"],
                      "properties": {"flujo": {"type": "string"},
                                     "cota_inferior": {"type": "integer", "minimum": 0},
                                     "cota_superior": {"type": "integer", "minimum": 0},
                                     "denominador": {"type": "integer", "minimum": 0},
                                     "reduccion_inferior": {"type": "number", "minimum": 0},
                                     "reduccion_superior": {"type": "number", "minimum": 0},
                                     "tasks": {"type": "integer", "minimum": 0}}},
        },
        "implementer": _INTERVALO,
        "reviewer": _INTERVALO,
        "par": _INTERVALO,
        "unidad": {"type": "string"},
        "hallazgos": {"type": "array", "items": {"type": "string"}},
    },
}

# La tabla normativa de AC-8, transcrita para que `autotest_esquemas_rechazan` compare los
# `required` de cada esquema contra ella en vez de contra sí mismos. `maximo_corpus` va aparte
# porque es campo de este flujo, no del AC.
REQUIRED_NORMATIVOS: dict[str, tuple[str, ...]] = {
    "censo": ("declarados", "descubiertos", "sobran", "faltan", "hash_mismatch",
              "tasks_excluidas", "hash_exclusiones", "denominador_tasks", "piso", "por_flujo",
              "cobertura_por_fuente_r2", "perdidas_vs_esperado", "sobran_vs_esperado"),
    "fixtures": ("manifest_sha256", "casos_totales", "casos_ok", "divergencias"),
    "medir-historico": ("poblacion", "elegibles", "flujos_incluidos", "flujos_degradados",
                        "proporcion_retenida", "hash_exclusiones", "cota_inferior",
                        "cota_superior", "denominador", "mediana_intervalo", "por_flujo",
                        "implementer", "reviewer", "par"),
}
REQUIRED_PROPIOS: dict[str, tuple[str, ...]] = {
    "censo": ("maximo_corpus",),
    "fixtures": (),
    "medir-historico": (),
}

# Los tres cortes de AC-7, como constantes: el umbral se fija **antes** de medir, y bajarlo para
# que una corrida pase es exactamente lo prohibido.
UMBRAL_PISO = 0.25          # exclusiones sobre el corpus de tasks
UMBRAL_FLUJO = 0.50         # más del 50 % de sus tasks excluidas → flujo degradado
UMBRAL_POBLACION = 0.70     # flujos elegibles bajo el 70 % → la medición falla


# ════════════════════════════════════════════════════════════════════════════════════════════
# CAPA 2 — Funciones puras (y los dos únicos adaptadores de lectura)
# ════════════════════════════════════════════════════════════════════════════════════════════

# ─── Validador de JSON Schema 2020-12, subconjunto ──────────────────────────────────────────
#
# **Portado, no importado** de `scripts/verificar-oraculo.py:385-548`, siguiendo la política que ese
# archivo declara en su propia cabecera. Acá vale doble: importar de él acoplaría el arnés al
# validador del oráculo justo donde se exige que el oráculo sea un camino independiente del parser.
#
# Las keywords soportadas son las que los tres schemas congelados **usan**, derivadas de ellos y no
# supuestas. Una lista que omita `oneOf`, `minimum`, `maximum`, `minLength` o `pattern` acepta
# insumos inválidos en silencio.
PALABRAS_SOPORTADAS = frozenset({
    "$ref", "type", "enum", "const", "pattern", "minLength", "minimum", "maximum",
    "minItems", "maxItems", "uniqueItems", "properties", "required", "additionalProperties",
    "items", "oneOf", "allOf", "if", "then", "else",
})
PALABRAS_IGNORADAS = frozenset({"$schema", "$id", "title", "description", "$defs", "$comment"})


def _es_anotacion(clave: str) -> bool:
    """Las extensiones `x-*` son **anotaciones**, no restricciones: no hay nada que comprobar y no
    validarlas no deja pasar ningún insumo inválido. Los tres schemas congelados usan `x-version`."""
    return clave.startswith("x-")


def _fmt_ruta(ruta: tuple) -> str:
    salida = "$"
    for tramo in ruta:
        salida += f"[{tramo}]" if isinstance(tramo, int) else f".{tramo}"
    return salida


def _mismo(a: object, b: object) -> bool:
    """Igualdad con el tipo incluido: en Python `False == 0`, y un enum de cadenas no debe aceptar
    un booleano por accidente."""
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return a == b


def _nombre_tipo(valor: object) -> str:
    if isinstance(valor, bool):
        return "boolean"
    if isinstance(valor, int):
        return "integer"
    if isinstance(valor, float):
        return "number"
    if isinstance(valor, str):
        return "string"
    if isinstance(valor, list):
        return "array"
    if isinstance(valor, dict):
        return "object"
    if valor is None:
        return "null"
    return type(valor).__name__


def _tipo_ok(valor: object, tipo: str) -> bool:
    if tipo == "integer":
        return isinstance(valor, int) and not isinstance(valor, bool)
    if tipo == "number":
        return isinstance(valor, (int, float)) and not isinstance(valor, bool)
    return _nombre_tipo(valor) == tipo


def _hay_repetidos(valores: list) -> bool:
    vistos: list[str] = []
    for v in valores:
        clave = json.dumps(v, sort_keys=True, ensure_ascii=False)
        if clave in vistos:
            return True
        vistos.append(clave)
    return False


def _resolver_ref(schema: dict, ref: str) -> dict:
    if not ref.startswith("#/$defs/"):
        raise ValueError(f"referencia no local o no soportada: {ref}")
    nombre = ref[len("#/$defs/"):]
    defs = schema.get("$defs", {})
    if nombre not in defs:
        raise ValueError(f"referencia a un `$defs` inexistente: {ref}")
    return defs[nombre]


def validar(instancia: object, schema: dict) -> list[str]:
    """Valida `instancia` contra `schema` (que es el schema raíz). Lista vacía = válido."""
    return [f"{_fmt_ruta(r)}: {m}" for r, m in _validar(instancia, schema, schema, ())]


def _validar(valor: object, esquema: dict, schema: dict, ruta: tuple) -> list[tuple[tuple, str]]:
    errores: list[tuple[tuple, str]] = []

    if "$ref" in esquema:
        errores.extend(_validar(valor, _resolver_ref(schema, esquema["$ref"]), schema, ruta))

    if "oneOf" in esquema:
        exitosas = 0
        fallidas: list[tuple[bool, int, list[tuple[tuple, str]]]] = []
        for rama in esquema["oneOf"]:
            errs = _validar(valor, rama, schema, ruta)
            if errs:
                fallidas.append((_fallo_de_discriminador(errs, rama, schema, ruta), len(errs),
                                 errs))
            else:
                exitosas += 1
        if exitosas == 0:
            # Cuál rama se reporta no lo decide el conteo de errores —eso atribuye mal en cuanto
            # dos ramas fallan con uno cada una— sino el discriminador.
            errores.extend(min(fallidas, key=lambda f: (f[0], f[1]))[2])
        elif exitosas > 1:
            errores.append((ruta, "más de una variante del `oneOf` valida este nodo: la unión no "
                                  "está discriminada"))

    for sub in esquema.get("allOf", []):
        errores.extend(_validar(valor, sub, schema, ruta))

    if "if" in esquema:
        condicion = _validar(valor, esquema["if"], schema, ruta)
        rama = esquema.get("then") if not condicion else esquema.get("else")
        if rama is not None:
            errores.extend(_validar(valor, rama, schema, ruta))

    tipo = esquema.get("type")
    if tipo is not None and not _tipo_ok(valor, tipo):
        errores.append((ruta, f"se esperaba tipo `{tipo}` y llegó `{_nombre_tipo(valor)}`"))
        return errores  # sin el tipo correcto, el resto de las restricciones no significa nada

    if "enum" in esquema and not any(_mismo(valor, v) for v in esquema["enum"]):
        errores.append((ruta, f"valor fuera del vocabulario cerrado: {valor!r} no está en "
                              f"{esquema['enum']}"))
    if "const" in esquema and not _mismo(valor, esquema["const"]):
        errores.append((ruta, f"se esperaba la constante {esquema['const']!r} y llegó {valor!r}"))

    if isinstance(valor, str):
        if "minLength" in esquema and len(valor) < esquema["minLength"]:
            errores.append((ruta, f"cadena más corta que `minLength` ({esquema['minLength']})"))
        if "pattern" in esquema and re.search(esquema["pattern"], valor) is None:
            errores.append((ruta, f"la cadena {valor!r} no casa con el patrón "
                                  f"{esquema['pattern']!r}"))

    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        if "minimum" in esquema and valor < esquema["minimum"]:
            errores.append((ruta, f"valor menor que `minimum` ({esquema['minimum']})"))
        if "maximum" in esquema and valor > esquema["maximum"]:
            errores.append((ruta, f"valor mayor que `maximum` ({esquema['maximum']})"))

    if isinstance(valor, list):
        if "minItems" in esquema and len(valor) < esquema["minItems"]:
            errores.append((ruta, f"el arreglo tiene {len(valor)} elementos y `minItems` es "
                                  f"{esquema['minItems']}"))
        if "maxItems" in esquema and len(valor) > esquema["maxItems"]:
            errores.append((ruta, f"el arreglo tiene {len(valor)} elementos y `maxItems` es "
                                  f"{esquema['maxItems']}"))
        if esquema.get("uniqueItems") and _hay_repetidos(valor):
            errores.append((ruta, "el arreglo declara `uniqueItems` y tiene elementos repetidos"))
        if "items" in esquema:
            for i, elemento in enumerate(valor):
                errores.extend(_validar(elemento, esquema["items"], schema, ruta + (i,)))

    if isinstance(valor, dict):
        propiedades = esquema.get("properties", {})
        for campo in esquema.get("required", []):
            if campo not in valor:
                errores.append((ruta + (campo,), f"falta el campo obligatorio `{campo}`"))
        cerrado = esquema.get("additionalProperties", True) is False
        for clave, sub in valor.items():
            if clave in propiedades:
                errores.extend(_validar(sub, propiedades[clave], schema, ruta + (clave,)))
            elif cerrado:
                errores.append((ruta + (clave,),
                                f"propiedad no declarada `{clave}` en un objeto cerrado"))

    return errores


def _fallo_de_discriminador(errores: list[tuple[tuple, str]], rama: dict, schema: dict,
                            ruta: tuple) -> bool:
    """True si la rama falló en una de sus propias constantes: entonces no es la variante que se
    quiso escribir, y sus errores no explican nada del nodo que llegó."""
    objetivo = _resolver_ref(schema, rama["$ref"]) if "$ref" in rama else rama
    claves = {c for c, sub in objetivo.get("properties", {}).items() if "const" in sub}
    return any(r in {ruta + (c,) for c in claves} for r, _ in errores)


def keywords_no_soportadas(schema: dict) -> list[str]:
    """Las keywords que el schema usa y este validador **no** implementa.

    Sin esta comprobación, una keyword desconocida se ignora en silencio y el validador dice «sí» a
    un insumo que la viola: la lista de keywords soportadas dejaría de ser una garantía y pasaría a
    ser una declaración de intenciones. Se recorre el schema entero, no solo su raíz."""
    encontradas: set[str] = set()

    def _recorrer(nodo: object) -> None:
        if isinstance(nodo, dict):
            for clave, valor in nodo.items():
                if (clave not in PALABRAS_SOPORTADAS and clave not in PALABRAS_IGNORADAS
                        and not _es_anotacion(clave)):
                    # Las claves bajo `properties` y `$defs` son **nombres**, no keywords.
                    encontradas.add(clave)
                _recorrer(valor)
        elif isinstance(nodo, list):
            for elemento in nodo:
                _recorrer(elemento)

    for clave, valor in schema.items():
        if clave in ("properties", "$defs"):
            for sub in valor.values():
                _recorrer(sub)
        elif clave in ("items", "allOf", "oneOf", "if", "then", "else"):
            _recorrer(valor)
        elif (clave not in PALABRAS_SOPORTADAS and clave not in PALABRAS_IGNORADAS
                and not _es_anotacion(clave)):
            encontradas.add(clave)
    # `properties` anidados aportan nombres de campo, no keywords: se filtran comparando contra los
    # nombres declarados en cualquier `properties` del documento.
    nombres: set[str] = set()

    def _nombres(nodo: object) -> None:
        if isinstance(nodo, dict):
            for clave, valor in nodo.items():
                if clave in ("properties", "$defs") and isinstance(valor, dict):
                    nombres.update(valor)
                _nombres(valor)
        elif isinstance(nodo, list):
            for elemento in nodo:
                _nombres(elemento)

    _nombres(schema)
    return sorted(encontradas - nombres)


def cargar_insumo(ruta: Path, schema: dict) -> tuple[dict, list[str]]:
    """Lee un insumo del árbol versionado y lo valida. **Uno de los dos únicos puntos de I/O.**

    Sin validar antes de leer, un insumo malformado se manifiesta como un `KeyError` a mitad del
    censo en vez de como un error nombrado con su ruta dentro del documento."""
    try:
        crudo = ruta.read_bytes()
    except OSError as e:
        return {}, [f"no se pudo leer el insumo `{ruta}`: {e}"]
    try:
        datos = json.loads(crudo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return {}, [f"`{ruta}` no es JSON UTF-8 válido: {e}"]
    errores = [f"`{ruta}` usa la keyword `{k}`, que este validador no implementa: la validación "
               f"sería un «sí» sin haber comprobado esa restricción"
               for k in keywords_no_soportadas(schema)]
    return datos, errores + [f"`{ruta}` {e}" for e in validar(datos, schema)]


# ─── R1 — Gramática de identificadores, única y compartida ──────────────────────────────────
#
# **Una sola gramática**, usada por las declaraciones de AC, los encabezados de task, la expansión
# de rangos, la resolución de `Consume` y el orden natural de R7. Una gramática por sitio es cómo
# dos lugares del mismo parser leen el mismo id distinto: el archivo que esto reemplaza tenía
# cuatro, y la de `AC` enumeraba un sufijo (`bis`) en vez de admitir la familia.
GRAMATICA_ID = re.compile(r"(AC-|T)(\d+)([A-Za-z]*)")
_TOKEN_ID = re.compile(r"\b(?:AC-\d+[A-Za-z]*|T\d+[A-Za-z]*)\b")


def parsear_id(token: str) -> Identificador | None:
    """`AC-14b` → `Identificador('AC', 14, 'b')`. Sensible a mayúsculas: `T15A` ≠ `T15a`."""
    m = GRAMATICA_ID.fullmatch(token.strip())
    if m is None:
        return None
    return Identificador("AC" if m.group(1) == "AC-" else "T", int(m.group(2)), m.group(3))


def orden_natural(i: Identificador) -> tuple[str, int, str]:
    """Orden ascendente natural de R7: `AC-2` antes que `AC-10` —no lexicográfico— y el sufijo
    alfabético desempata después del número: `T16` · `T16b` · `T17`."""
    return (i.familia, i.numero, i.sufijo)


def clave_orden(token: str) -> tuple[str, int, str]:
    """`orden_natural` sobre el texto de un id; lo que no parsea va al final, por su texto."""
    i = parsear_id(token)
    return orden_natural(i) if i else ("￿", 0, token)


# Los rangos de R1, en las cuatro formas del corpus: `AC-1..AC-6`, `AC-1..6`, `T7-T9`, `T4–T6`.
# El guion simple solo separa rangos de la familia `T`: en `AC-` el guion es **parte del id**, y
# admitirlo ahí convertiría cada `AC-1` en el inicio de un rango.
RANGO = re.compile(
    r"\b(AC-\d+[A-Za-z]*)\s*(?:\.\.|–|—)\s*((?:AC-)?\d+[A-Za-z]*)\b"
    r"|\b(T\d+[A-Za-z]*)\s*(?:\.\.|–|—|-)\s*(T?\d+[A-Za-z]*)\b")


def expandir_rango(inicio: str, fin: str, declarados: set[str]) -> tuple[list[str], str | None]:
    """Expande **inclusivo** un rango de R1, o devuelve su causa de error.

    `declarados` es el universo contra el que se comprueban los **extremos**: un intermedio que no
    exista no es `extremo_inexistente`, es un `ac_inexistente` que el clasificador ve después."""
    ini = parsear_id(inicio)
    if ini is None:
        return [], "extremo_inexistente"
    fin_txt = fin.strip()
    # `AC-1..6`: el extremo final hereda la familia del inicial cuando no la trae.
    heredado = fin_txt if GRAMATICA_ID.fullmatch(fin_txt) else (
        f"{ini.familia}-{fin_txt}" if ini.familia == "AC" else f"{ini.familia}{fin_txt}")
    fn = parsear_id(heredado)
    if fn is None:
        return [], "extremo_inexistente"
    if ini.familia != fn.familia:
        return [], "rango_mixto"
    if ini.numero > fn.numero:
        return [], "rango_invertido"
    if declarados and (str(ini) not in declarados or str(fn) not in declarados):
        return [], "extremo_inexistente"
    sep = "-" if ini.familia == "AC" else ""
    return [f"{ini.familia}{sep}{n}" for n in range(ini.numero, fn.numero + 1)], None


def ids_en(texto: str, declarados: set[str] | None = None,
           familia: str | None = None) -> tuple[list[str], list[str]]:
    """Todos los ids que un texto declara, con los rangos ya expandidos. Devuelve `(ids, causas)`.

    Los rangos se consumen **antes** que los tokens sueltos: si no, `AC-1..AC-6` aportaría sus dos
    extremos y perdería el medio en silencio, que es el cuarto defecto de extracción del `~14x`.

    `familia` acota el resultado a una de las dos de R1. R2 se titula «dónde una task declara **qué
    AC** cubre»: un token `T27` dentro de esa declaración no es cobertura, sea cual sea la línea que
    la continuación haya alcanzado. Filtrarlo por familia es definicional y no un corte inventado —
    que es lo que haría falta, si no, para dejar afuera un ítem en negrita que **no** abre campo por
    la letra de R2 y que la continuación tiene que atravesar."""
    causas: list[str] = []
    salida: list[str] = []
    consumido = bytearray(len(texto))
    for m in RANGO.finditer(texto):
        a, b = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        ids, causa = expandir_rango(a, b, declarados or set())
        if causa:
            causas.append(causa)
        salida.extend(ids)
        for k in range(m.start(), m.end()):
            consumido[k] = 1
    for m in _TOKEN_ID.finditer(texto):
        if not any(consumido[m.start():m.end()]):
            salida.append(m.group(0))
    vistos: list[str] = []
    for i in salida:
        if i in vistos:
            continue
        ident = parsear_id(i)
        if familia is not None and (ident is None or ident.familia != familia):
            continue
        vistos.append(i)
    return vistos, causas


# ─── El indexador de eventos ────────────────────────────────────────────────────────────────
#
# **El parseo es una tubería por fases, no una colección de regex independientes.** Primero se
# indexan los eventos —headings, encabezados de task, declaraciones de AC, aperturas de campo— y
# recién después se cortan los bloques usando esos eventos **ya clasificados**. Así ningún patrón
# de inicio decide también el final: el archivo que esto reemplaza dejaba que `FILA_DE_CONTRATO`
# barriera el plan entero y ganara la última fila, con lo que `V13` llegaba desde `## Verify` en
# vez de desde `## Verification`.

class Evento(NamedTuple):
    """`clase` ∈ {`heading1`…`heading6`, `task`, `ac`, `campo`}. El nombre de un campo y el título
    de un heading **no** se guardan acá: se releen del buffer con `texto_de_linea`, que es lo que
    mantiene el evento en las cuatro columnas que el contrato interno declara."""
    clase: str
    ident: Identificador | None
    inicio: int
    fin_linea: int


# Un encabezado de task, en sus dos formas de R1. La segunda admite título tras el id —
# `## T1 — El verificador completo`—: exigir `## T12` a secas descarta el flujo entero que la usa.
_EV_TASK_VINETA = re.compile(rb"^- \[[ xX]\] \*\*(T\d+[A-Za-z]*)(?=\*\*|[\s:.,]|$)", re.M)
_EV_TASK_HEADING = re.compile(rb"^(#{2,6}) (T\d+[A-Za-z]*)(?=[\s:.,]|$)", re.M)
# Las **cinco formas** de declarar un AC (R1). Se conserva la lógica de delimitación del patrón
# anterior —`:`, el cierre `**`, o una raya— y se reemplaza **solo su gramática de id**. El
# delimitador no es cosmética: sin él, una línea de prosa en negrita como
# `**AC-24bis no es AC-24 repetido, y la diferencia importa.**` entra como declaración y el
# extractor termina con dos bloques para el mismo id, uno de ellos falso.
# Las rayas van por sus bytes UTF-8 (`—` = `\xe2\x80\x94`, `–` = `\xe2\x80\x93`): un literal de
# bytes no admite caracteres no ASCII.
_EV_AC = re.compile(rb"^(?:- )?\*\*(AC-\d+[A-Za-z]*)"
                    rb"(?=\*\*|:| \xe2\x80\x94| \xe2\x80\x93|\s*\*\*?:)", re.M)
_EV_HEADING = re.compile(rb"^(#{1,6}) ", re.M)
# Un campo abre de **tres** formas: las dos que R2 nombra —`- **<N>:**` y `- **<N>** *(nota)*:`—
# más la variante sin viñeta, que es la fuente 3 de R2 y que el corpus usa indentada. Nombrar solo
# la primera deja que la continuación **se coma el campo siguiente** y le atribuya a la task un id
# que nadie lee como declarado: es el defecto que la v13 del contrato corrigió.
# El nombre no lleva cota de longitud: acotarlo sería una convención inventada que el corpus no
# tiene por qué satisfacer —`- **Archivos (nuevo):**` ya es más largo que un nombre «normal»—, y el
# contrato retiró una regla así en su v3 justamente por invalidar 186 de 186 campos reales.
_EV_CAMPO = re.compile(
    rb"^[ \t]*(?:- )?\*\*([^*\n]+?):\*\*"
    rb"|^[ \t]*(?:- )?\*\*([^*\n]+?)\*\*[ \t]*\*\([^)\n]*\)\*[ \t]*:", re.M)


def _fin_de_linea(buf: bytes, pos: int) -> int:
    corte = buf.find(b"\n", pos)
    return len(buf) if corte < 0 else corte


def indexar_eventos(buf: bytes) -> list[Evento]:
    """Todos los eventos del buffer, ordenados por desplazamiento.

    Un `## T12` es a la vez heading de nivel 2 y encabezado de task: emite **un solo** evento, de
    clase `task`, porque R1 manda. Los `heading2` que quedan son entonces exactamente los
    candidatos a bloque global de R5 —«un heading `##` que **no** satisface la gramática de
    encabezado de task»—, sin necesidad de volver a decidirlo."""
    eventos: list[Evento] = []
    inicios_de_task: set[int] = set()
    for m in _EV_TASK_VINETA.finditer(buf):
        eventos.append(Evento("task", parsear_id(m.group(1).decode()), m.start(),
                              _fin_de_linea(buf, m.start())))
        inicios_de_task.add(m.start())
    for m in _EV_TASK_HEADING.finditer(buf):
        eventos.append(Evento("task", parsear_id(m.group(2).decode()), m.start(),
                              _fin_de_linea(buf, m.start())))
        inicios_de_task.add(m.start())
    for m in _EV_HEADING.finditer(buf):
        if m.start() in inicios_de_task:
            continue
        eventos.append(Evento(f"heading{len(m.group(1))}", None, m.start(),
                              _fin_de_linea(buf, m.start())))
    for m in _EV_AC.finditer(buf):
        eventos.append(Evento("ac", parsear_id(m.group(1).decode()), m.start(),
                              _fin_de_linea(buf, m.start())))
    declaraciones = {e.inicio for e in eventos if e.clase == "ac"}
    for m in _EV_CAMPO.finditer(buf):
        # Una declaración de AC de una spec —`- **AC-17:**`— también satisface la forma de apertura
        # de campo. Ya tiene su evento `ac`; emitir además un `campo` en el mismo desplazamiento
        # duplicaría el corte sin agregar información.
        if m.start() in declaraciones:
            continue
        eventos.append(Evento("campo", None, m.start(), _fin_de_linea(buf, m.start())))
    eventos.sort(key=lambda e: (e.inicio, 0 if e.clase == "task" else 1))
    return eventos


def texto_de_linea(buf: bytes, ev: Evento) -> str:
    return buf[ev.inicio:ev.fin_linea].decode("utf-8", "replace")


def nombre_de_campo(buf: bytes, ev: Evento) -> str | None:
    """El nombre de un evento `campo`, releído del buffer."""
    m = _EV_CAMPO.match(buf, ev.inicio)
    if m is None:
        return None
    crudo = m.group(1) if m.group(1) is not None else m.group(2)
    return crudo.decode("utf-8", "replace").strip()


def nivel_de_heading(clase: str) -> int | None:
    return int(clase[7:]) if clase.startswith("heading") else None


# ─── El corte de bloques, sobre los eventos ya clasificados ─────────────────────────────────

def _corte_de_bloque_con_id(eventos: list[Evento], i: int, fin_buf: int) -> int:
    """R1: un bloque con id va desde su encabezado hasta el próximo encabezado que satisfaga **esta
    misma gramática**, o el próximo heading Markdown. El patrón de corte es idéntico al de inicio:
    uno más laxo deja que una línea de prosa en negrita trunque un criterio."""
    clase = eventos[i].clase
    for e in eventos[i + 1:]:
        if e.clase == clase or e.clase.startswith("heading") or e.clase in ("task", "ac"):
            return e.inicio
    return fin_buf


def _es_linea_indentada(buf: bytes, inicio: int) -> bool:
    fin = _fin_de_linea(buf, inicio)
    linea = buf[inicio:fin]
    return linea[:1] in (b" ", b"\t")


def extender_continuacion(buf: bytes, cortes: set[int], desde: int, limite: int) -> int:
    """**La única función de continuación** de R2, compartida por las tres fuentes y por el corte de
    campos de R5.

    Una declaración continúa mientras las líneas siguientes estén **indentadas** y no abran otro
    campo ni otro encabezado de R1. `cortes` son los desplazamientos de todos esos eventos, ya
    clasificados por el indexador, así que ningún patrón de inicio decide también el final.

    Que un campo abra de **dos** formas —`- **<N>:**` y `- **<N>** *(nota)*:`— no es un detalle:
    reconocer solo la primera deja que la continuación se coma el campo siguiente y le atribuya a
    la task un id que nadie lee como declarado. Es el defecto que la v13 del contrato corrigió, y
    la quinta reaparición del defecto original de la fase."""
    pos = _fin_de_linea(buf, desde)
    while pos < limite:
        arranque = pos + 1
        if arranque >= limite or arranque in cortes or not _es_linea_indentada(buf, arranque):
            return pos
        pos = _fin_de_linea(buf, arranque)
    return min(pos, limite)


# ─── R2 — Dónde una task declara qué AC cubre ───────────────────────────────────────────────
#
# El defecto original de la fase: el extractor leía `- **AC:` mientras la plantilla normativa usaba
# `· cubre:`, y 213 de 310 tasks salían sin un solo AC — mientras el arnés informaba que «todas las
# referencias citadas resuelven», porque no había ninguna que resolver.

_MARCADOR_CUBRE = re.compile(rb"\xc2\xb7 cubre:")


class Cobertura(NamedTuple):
    fuente_efectiva: str
    ac: list[str]
    ocurrencias: list[str]
    causa: str | None


def _rango_de_task(eventos: list[Evento], i: int, fin_buf: int) -> tuple[int, int]:
    return eventos[i].inicio, _corte_de_bloque_con_id(eventos, i, fin_buf)


def _indice_de_task(eventos: list[Evento], task: Identificador) -> int | None:
    for i, e in enumerate(eventos):
        if e.clase == "task" and e.ident == task:
            return i
    return None


def capturar_cobertura(buf: bytes, ev: list[Evento], task: Identificador,
                       declarados: set[str] | None = None) -> Cobertura:
    """Las tres fuentes de R2, con continuación multilínea y reconciliación.

    La línea de `Verificar:` **no** declara cobertura, ni siquiera con el patrón
    `- **Verificar:** V25, V26 · **AC-21**`, que usa el mismo separador `·` de la fuente 1 y está en
    posición terminal fija. Acá eso sale gratis: se buscan los marcadores `· cubre:` y el campo de
    nombre exacto `AC`, y ninguno de los dos aparece en esa línea."""
    i = _indice_de_task(ev, task)
    if i is None:
        return Cobertura("", [], [], "sin_cobertura")
    ini, fin = _rango_de_task(ev, i, len(buf))
    cortes = {e.inicio for e in ev if e.clase in ("campo", "task", "ac")
              or e.clase.startswith("heading")}

    # El **preámbulo**: desde el encabezado hasta el primer campo del bloque. Es donde R2 admite la
    # fuente 1 — «empieza en la línea del encabezado o en la línea siguiente indentada»—, y
    # acotarla ahí impide que un `· cubre:` escrito dentro de `Pasos` cuente como declaración.
    primer_campo = next((e.inicio for e in ev if e.clase == "campo" and ini < e.inicio < fin), fin)

    crudos: dict[str, tuple[list[str], list[str]]] = {}

    mc = _MARCADOR_CUBRE.search(buf, ini, primer_campo)
    if mc is not None:
        hasta = extender_continuacion(buf, cortes, mc.end(), fin)
        crudos["cubre"] = ids_en(buf[mc.end():hasta].decode("utf-8", "replace"), declarados,
                                 familia="AC")

    for e in ev:
        if e.clase != "campo" or not (ini < e.inicio < fin):
            continue
        if nombre_de_campo(buf, e) != "AC":
            continue
        cuerpo = buf[e.inicio:e.fin_linea]
        con_vineta = cuerpo.lstrip(b" \t").startswith(b"- ")
        fuente = "campo_con_vineta" if con_vineta else "campo_sin_vineta"
        arranque = buf.find(b":**", e.inicio) + 3
        hasta = extender_continuacion(buf, cortes - {e.inicio}, arranque, fin)
        if fuente not in crudos:
            crudos[fuente] = ids_en(buf[arranque:hasta].decode("utf-8", "replace"), declarados,
                                    familia="AC")

    # Una fuente **presente pero vacía** no es una fuente: su marcador está y no declara ningún id,
    # así que tratarla como presente inventaría un `cobertura_en_conflicto` contra la que sí
    # declara. Lo que no declara nada cae, si no hay otra, en `sin_cobertura`.
    presentes = {f: v for f, v in crudos.items() if v[0]}
    causas_rango = [c for f in presentes for c in crudos[f][1]]
    ocurrencias = [f for f in FUENTES_R2 if f in presentes]
    if not presentes:
        causa = causas_rango[0] if causas_rango else "sin_cobertura"
        return Cobertura("", [], [], causa)

    conjuntos = {f: frozenset(v[0]) for f, v in presentes.items()}
    if len(set(conjuntos.values())) > 1:
        # Dos fuentes que se contradicen son un artefacto roto y la precedencia **no** las resuelve:
        # la precedencia decide cuál leer cuando hay una sola.
        return Cobertura("", [], ocurrencias, "cobertura_en_conflicto")

    efectiva = ocurrencias[0]
    ids = sorted(presentes[efectiva][0], key=clave_orden)
    return Cobertura(efectiva, ids, ocurrencias, causas_rango[0] if causas_rango else None)


# ─── R3 — De dónde sale la fila `Vn` ────────────────────────────────────────────────────────

_FILA = re.compile(rb"^\| *(V\d+[a-z]?) *\|", re.M)


def _rango_de_seccion(buf: bytes, ev: list[Evento], titulo: bytes,
                      nivel: int = 2) -> tuple[int, int] | None:
    """Una sección `##` completa: desde su heading hasta el próximo heading de nivel **menor o
    igual**, o el próximo encabezado de task. Los `###` internos son contenido."""
    for i, e in enumerate(ev):
        if e.clase != f"heading{nivel}":
            continue
        if buf[e.inicio:e.fin_linea].rstrip() != titulo:
            continue
        for sig in ev[i + 1:]:
            n = nivel_de_heading(sig.clase)
            if (n is not None and n <= nivel) or sig.clase == "task":
                return e.inicio, sig.inicio
        return e.inicio, len(buf)
    return None


def filas_del_contrato(buf: bytes) -> tuple[dict[str, tuple[int, int]], list[str]]:
    """Las filas `Vn`, indexadas **solo dentro de `## Verification`**.

    `## Verify` queda fuera **por construcción**, no por una exclusión que haya que recordar: el
    mismo id vive en las dos secciones —`instrumento-y-baseline/plan.md`, `V13` en l. 502 y 584— y
    la segunda es el **resultado observado**, no el contrato. El parser que esto reemplaza indexaba
    sobre el plan entero y ganaba la última ocurrencia, así que al dossier llegaba la evidencia en
    vez de la fila contractual. `## Verificación` en español **no** cuenta: R3 es literal, y el
    corpus lo paga con un flujo degradado que el censo reporta como defecto del corpus.

    El segundo elemento son los ids repetidos **dentro de la sección**, que es `fila_duplicada`."""
    ev = indexar_eventos(buf)
    rango = _rango_de_seccion(buf, ev, b"## Verification")
    if rango is None:
        return {}, []
    ini, fin = rango
    filas: dict[str, tuple[int, int]] = {}
    duplicadas: list[str] = []
    for m in _FILA.finditer(buf, ini, fin):
        ident = m.group(1).decode()
        if ident in filas:
            if ident not in duplicadas:
                duplicadas.append(ident)
            continue
        filas[ident] = (m.start(), _fin_de_linea(buf, m.start()))
    return filas, duplicadas


def extraer_enfoque(buf: bytes) -> tuple[int, int] | None:
    """El `## Enfoque` del plan, hasta el próximo heading de nivel menor o igual."""
    rango = _rango_de_seccion(buf, indexar_eventos(buf), b"## Enfoque")
    return rango


# ─── R4 — Duplicados de un id ───────────────────────────────────────────────────────────────

# El apéndice de fidelidad repite cada criterio heredado, **literal como venía del flujo padre**.
# Son declaraciones válidas y no vigentes: lo que la task tiene que leer es el criterio de las
# secciones de contenido. Medido sobre una spec del corpus: 13 de 16 AC aparecen dos veces, y un
# diccionario por id se queda con el último —el del apéndice— sin decir nada. Para AC-27 eso cambia
# 4.409 bytes por 355. Por eso el corte es explícito y las declaraciones se cuentan.
# La `é` va como **alternancia**, no como clase: en UTF-8 son los dos bytes `\xc3\xa9`, y una clase
# de caracteres sobre un patrón de bytes casa **un solo byte**. Con `[e\xc3\xa9]` el heading real
# no matchea nunca, el corte no se encuentra, y los trece duplicados legítimos del apéndice de una
# spec del corpus se convierten en `duplicado_normativo` — trece exclusiones inventadas.
CORTE_DE_APENDICE = re.compile(rb"^## Ap(?:e|\xc3\xa9)ndice de fidelidad", re.M)


def elegir_entre_duplicados(ocurrencias: list[tuple[int, int]],
                            corte_apendice: int | None) -> tuple[tuple[int, int] | None, str]:
    """La primera declaración gana **si y solo si** las repeticiones caen dentro del apéndice.

    Ante un duplicado bloqueante no se elige ninguno: `bloque_elegido` queda en `ninguno` —acá,
    `None`—. Exigir «cuál bloque se eligió» siempre era contradictorio, y las dos mitades habrían
    resuelto la contradicción por su cuenta y distinto."""
    if not ocurrencias:
        return None, ""
    if len(ocurrencias) == 1:
        return ocurrencias[0], ""
    if corte_apendice is not None and all(o[0] >= corte_apendice for o in ocurrencias[1:]):
        return ocurrencias[0], "duplicado_aceptado"
    return None, "duplicado_normativo"


def bloques_por_id(buf: bytes, ev: list[Evento],
                   clase: str) -> tuple[dict[str, tuple[int, int]], list[str]]:
    """Los bloques con id de una clase (`ac` o `task`), aplicando la política de R4.

    Devuelve `(bloques, duplicados_normativos)`. Un id con `duplicado_normativo` **no** entra al
    diccionario: no hay bloque elegido."""
    corte = CORTE_DE_APENDICE.search(buf)
    corte_pos = corte.start() if corte else None
    ocurrencias: dict[str, list[tuple[int, int]]] = {}
    for i, e in enumerate(ev):
        if e.clase != clase or e.ident is None:
            continue
        ocurrencias.setdefault(str(e.ident), []).append(
            (e.inicio, _corte_de_bloque_con_id(ev, i, len(buf))))
    bloques: dict[str, tuple[int, int]] = {}
    duplicados: list[str] = []
    for ident, ocs in ocurrencias.items():
        elegido, causa = elegir_entre_duplicados(ocs, corte_pos)
        if causa == "duplicado_normativo":
            duplicados.append(ident)
            continue
        if elegido is not None:
            bloques[ident] = elegido
    return bloques, duplicados


# ─── R5 — `Consume`, bloques globales y el corte de `Produce` ───────────────────────────────

def extraer_campo(buf: bytes, ev: list[Evento], task: Identificador,
                  nombre: str) -> tuple[int, int] | None:
    """Corta un campo de una task por su nombre, reconociendo **las dos formas de apertura** y
    usando la misma continuación de R2. Es lo que R5 ancla para `Produce`: repetir solo la primera
    forma dejaría que el corte se comiera el campo siguiente."""
    i = _indice_de_task(ev, task)
    if i is None:
        return None
    ini, fin = _rango_de_task(ev, i, len(buf))
    cortes = {e.inicio for e in ev if e.clase in ("campo", "task", "ac")
              or e.clase.startswith("heading")}
    for e in ev:
        if e.clase != "campo" or not (ini < e.inicio < fin):
            continue
        if nombre_de_campo(buf, e) != nombre:
            continue
        return e.inicio, extender_continuacion(buf, cortes - {e.inicio}, e.inicio, fin)
    return None


def slug_de(titulo: str) -> str:
    """Minúsculas, sin acentos, no alfanuméricos → guion, colapsando repetidos.

    `## Interfaz compartida — el contrato de los tres adaptadores` da
    `interfaz-compartida-el-contrato-de-los-tres-adaptadores`."""
    sin_marca = "".join(c for c in unicodedata.normalize("NFD", titulo)
                        if unicodedata.category(c) != "Mn")
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]", "-", sin_marca.lower())).strip("-")


def bloques_globales(buf: bytes, ev: list[Evento]) -> tuple[dict[str, tuple[int, int]],
                                                            list[str]]:
    """Los bloques globales de un `tasks.md`: cada heading `##` que **no** satisface la gramática de
    encabezado de task de R1. Su id es el slug de su heading.

    **Termina** en el próximo heading de nivel menor o igual al suyo, o en el próximo encabezado de
    task —lo que ocurra primero—. Un `###` interno **pertenece a su contenido**: un bloque global es
    una sección con estructura, y cortarlo en su primer subtítulo entregaría al agente una fracción
    del contrato que dice entregarle entero.

    El segundo elemento son los slugs declarados más de una vez: `bloque_global_duplicado`."""
    bloques: dict[str, tuple[int, int]] = {}
    duplicados: list[str] = []
    for i, e in enumerate(ev):
        if e.clase != "heading2":
            continue
        titulo = buf[e.inicio:e.fin_linea].decode("utf-8", "replace").lstrip("# ").strip()
        slug = slug_de(titulo)
        if not slug:
            continue
        fin = len(buf)
        for sig in ev[i + 1:]:
            n = nivel_de_heading(sig.clase)
            if (n is not None and n <= 2) or sig.clase == "task":
                fin = sig.inicio
                break
        if slug in bloques:
            if slug not in duplicados:
                duplicados.append(slug)
            continue
        bloques[slug] = (e.inicio, fin)
    return bloques, duplicados


_CITA_DE_BLOQUE = re.compile(r"bloque\s+global\s+`([^`]+)`", re.I)


def resolver_consume(texto: str, tasks: set[str], produce: set[str],
                     bloques: dict[str, tuple[int, int]],
                     duplicados: list[str] | None = None
                     ) -> tuple[list[str], list[str], list[str]]:
    """`Consume` se resuelve por **lo que contiene**, no por una plantilla que el texto deba seguir.

    Los backticks son obligatorios **solo para el bloque global**: un id de task tiene forma propia
    y se reconoce solo; un título en prosa —«la interfaz compartida»— no la tiene. La asimetría no
    es estética: exigir backticks también para las tasks fue el primer intento de esta regla y,
    medido contra el corpus, **no lo satisfacía ni un solo campo `Consume` existente**.

    Devuelve `(tasks_citadas, slugs_resueltos, causas)`."""
    causas: list[str] = []
    citas_bloque = [c.strip() for c in _CITA_DE_BLOQUE.findall(texto)]
    sin_bloques = _CITA_DE_BLOQUE.sub(" ", texto)
    tokens, _ = ids_en(sin_bloques)
    citadas = [t for t in tokens if (i := parsear_id(t)) and i.familia == "T"]

    if not tokens and not citas_bloque:
        causas.append("consume_no_tipado")

    for t in citadas:
        if t not in tasks:
            causas.append("task_consumida_inexistente")
        elif t not in produce:
            causas.append("sin_produce")

    resueltos: list[str] = []
    for cita in citas_bloque:
        clave = slug_de(cita)
        if clave in (duplicados or []):
            causas.append("bloque_global_duplicado")
            continue
        # **La coincidencia exacta se resuelve ANTES de evaluar prefijos.** Con dos bloques `foo` y
        # `foo-bar`, la cita `foo` es a la vez coincidencia exacta de uno y prefijo de los dos: sin
        # esta precedencia, una mitad la resuelve al bloque `foo` y la otra la declara ambigua,
        # **cada una aplicando la regla literalmente**.
        if clave in bloques:
            resueltos.append(clave)
            continue
        prefijos = [s for s in bloques if s.startswith(clave)]
        if len(prefijos) == 1:
            resueltos.append(prefijos[0])
        elif len(prefijos) > 1:
            # El prefijo corto es una **concesión de escritura** y nada garantiza que siga siendo
            # inequívoco cuando alguien agrega un bloque nuevo con el mismo comienzo. Ese caso no
            # está ausente ni duplicado: la cita es legítima y el documento cambió debajo.
            causas.append("bloque_global_ambiguo")
        else:
            causas.append("bloque_global_inexistente")
    return citadas, resueltos, causas


# ─── R7 — La proyección canónica del dossier ────────────────────────────────────────────────
#
# Los bytes del denominador de AC-6 son los de **este** payload. Su forma se fija byte a byte o el
# conductor renderiza de una manera y el arnés cuenta de otra, **cada uno conforme a su propio AC**:
# es el modo de fallo exacto que la partición de la fase introduce. Un salto de más y el número
# entero sale mal, con todos los fixtures de reglas en verde.

class Pieza(NamedTuple):
    clase: str
    clave: tuple
    orden: tuple
    texto: bytes


def recortar_pieza(buf: bytes, inicio: int, fin: int) -> bytes:
    """El rango de una pieza va desde el primer byte de su encabezado hasta el último byte de su
    **última línea no vacía**.

    Los saltos que la separan del siguiente encabezado son **delimitador Markdown externo** y no le
    pertenecen; las líneas en blanco **interiores** —las que tienen contenido después, dentro del
    mismo rango— son contenido y se conservan intactas.

    **Nunca `strip()`.** R7 manda conservar los saltos internos «tal como están en el artefacto, sin
    normalizar, sin recortar y sin reindentar», y el parser que esto reemplaza recortaba al cerrar
    cada bloque. El denominador de AC-6 son bytes de este payload: recortar un salto cambia el
    número. Y un `rstrip` genérico borraría contenido legítimo cuando la pieza termina en un bloque
    de código o una tabla, así que el recorte es **por líneas**, no por caracteres."""
    lineas = buf[inicio:fin].split(b"\n")
    while lineas and not lineas[-1].strip():
        lineas.pop()
    return b"\n".join(lineas)


def renderizar(piezas: list[Pieza]) -> bytes:
    """El payload renderizado, con los saltos exactos de R7.

    Un rótulo por **clase no vacía**, no por pieza; las piezas de una clase van bajo su rótulo,
    separadas entre sí por una línea en blanco. Así el dossier tiene entre 3 y 6 rótulos —task, AC y
    enfoque están siempre, porque cero AC bloquea— y el conteo es determinista.

    **Los rótulos cuentan** en el total: son bytes que el agente ingiere y que hoy no existen. No
    contarlos haría ver la reducción mejor de lo que es."""
    por_clase: dict[str, list[Pieza]] = {}
    vistas: set[tuple] = set()
    for p in piezas:
        # Deduplicación por **clave de clase**, nunca por contenido: deduplicar por contenido
        # escondería un id repetido con texto distinto, que es un defecto y no un ahorro.
        if p.clave in vistas:
            continue
        vistas.add(p.clave)
        por_clase.setdefault(p.clase, []).append(p)

    bloques: list[bytes] = []
    for clase, rotulo in ROTULOS:
        grupo = por_clase.get(clase)
        if not grupo:
            continue
        grupo.sort(key=lambda p: p.orden)
        cuerpo = b"\n\n".join(p.texto for p in grupo)
        bloques.append(rotulo.encode() + b"\n" + cuerpo)
    if not bloques:
        return b""
    return b"\n\n".join(bloques) + b"\n"


def clases_presentes(piezas: list[Pieza]) -> list[str]:
    """Las clases no vacías, en el orden canónico de R7."""
    presentes = {p.clase for p in piezas}
    return [c for c, _ in ROTULOS if c in presentes]


# ════════════════════════════════════════════════════════════════════════════════════════════
# CAPA 3 — Casos de uso
# ════════════════════════════════════════════════════════════════════════════════════════════
#
# Reciben sus insumos por parámetro (con default a la ruta real) y **devuelven** su resultado como
# `dict`. No imprimen ni llaman a `sys.exit`: eso es de la capa 4.

# ─── La tabla regla → operación ─────────────────────────────────────────────────────────────
#
# El manifest congelado declara `entrada` y `salida_esperada.valor` pero **no** qué operación
# produce ese valor, y no es la misma por regla. Esta tabla es **autoría de este flujo**, no del
# manifest: sin ella, «cada caso devuelve su salida exacta» no tiene referente y el modo puede
# declararse verde ejecutando cuatro casos de mentira — que es exactamente el riesgo con C16–C19,
# que no son fragmentos parseables sino enunciados sobre R7 y R8.

def _op_r1(entrada: str) -> tuple[list[str], str | None]:
    """R1 — reconocer el id del encabezado, o expandir el rango."""
    ev = indexar_eventos(entrada.encode())
    encabezados = [str(e.ident) for e in ev if e.clase == "task"]
    if encabezados:
        return encabezados, None
    ids, causas = ids_en(entrada)
    return ([], causas[0]) if causas else (ids, None)


def _op_r2(entrada: str) -> tuple[list[str], str | None]:
    """R2 — extraer el conjunto de AC que la cobertura declara.

    Las fuentes 2 y 3 viven **en el cuerpo** de una task, y varios casos del manifest recortan solo
    el campo. Cuando el fragmento no trae encabezado se le antepone uno sintético: es el contexto
    mínimo que la regla presupone, no una licencia sobre la entrada."""
    buf = entrada.encode()
    ev = indexar_eventos(buf)
    if not any(e.clase == "task" for e in ev):
        buf = b"- [ ] **T1 - contexto sintetico del fixture**\n" + buf
        ev = indexar_eventos(buf)
    task = next(e.ident for e in ev if e.clase == "task")
    cob = capturar_cobertura(buf, ev, task)
    return ([], cob.causa) if cob.causa else (cob.ac, None)


def _op_r3(entrada: str) -> tuple[list[str], str | None]:
    """R3 — extraer las filas citadas, o detectar la duplicación dentro de `## Verification`."""
    if entrada.lstrip().startswith("|"):
        filas, duplicadas = filas_del_contrato(b"## Verification\n\n" + entrada.encode())
        if duplicadas:
            return [], "fila_duplicada"
        return sorted(filas, key=lambda v: (int(re.sub(r"\D", "", v)), v)), None
    return re.findall(r"\bV\d+[a-z]?\b", entrada), None


def _op_r4(entrada: str) -> tuple[list[str], str | None]:
    """R4 — aplicar la política de duplicados y devolver el id tomado.

    El caso positivo del manifest recorta el apéndice con la **repetición**, y su propio campo
    `construccion` dice que abajo va «una repetición de un id ya declarado antes». Esa declaración
    anterior se sintetiza acá: sin ella el fragmento no tiene duplicado que politizar, y el caso
    quedaría probando otra cosa."""
    buf = entrada.encode()
    ids = sorted({str(e.ident) for e in indexar_eventos(buf) if e.clase == "ac"}, key=clave_orden)
    if CORTE_DE_APENDICE.search(buf):
        previas = b"".join(f"- **{i}:** declaracion vigente, anterior al apendice.\n\n".encode()
                           for i in ids)
        buf = previas + buf
    bloques, duplicados = bloques_por_id(buf, indexar_eventos(buf), "ac")
    if duplicados:
        return [], "duplicado_normativo"
    return sorted(bloques, key=clave_orden), None


def _op_r5(entrada: str) -> tuple[list[str], str | None]:
    """R5 — resolver el `Consume` a tasks o bloques globales.

    El universo de tasks son las citadas por el propio fragmento: el caso prueba la **resolución
    sintáctica**, y si existen o tienen `Produce` lo evalúa el clasificador contra el corpus."""
    citadas, _ = ids_en(_CITA_DE_BLOQUE.sub(" ", entrada))
    universo = {t for t in citadas if (i := parsear_id(t)) and i.familia == "T"}
    tasks, slugs, causas = resolver_consume(entrada, universo, universo, {})
    return ([], causas[0]) if causas else (tasks + slugs, None)


_MENCION_DE_CLASE: tuple[tuple[str, str], ...] = (
    ("enfoque", "enfoque"), ("bloques globales", "bloques_globales"), ("produce", "produce"),
    ("filas", "filas"), ("ac", "ac"), ("task", "task"),
)


def _op_r7(entrada: str) -> tuple[list[str], str | None]:
    """R7 — validar la enumeración de clases de la proyección.

    C16 y C17 **no pasan por el parser documental**: R7 es una regla sobre la proyección, y el
    corpus no contiene bytes que la instancien. El caso enumera las piezas en prosa y la operación
    las mapea a las clases del mapa cerrado de rótulos."""
    dentro = entrada[entrada.find("{") + 1:entrada.rfind("}")]
    piezas: list[Pieza] = []
    for item in dentro.split(","):
        texto = item.strip().lower()
        for aguja, clase in _MENCION_DE_CLASE:
            if aguja in texto:
                piezas.append(Pieza(clase, (clase,), (0,), b"x"))
                break
    presentes = clases_presentes(piezas)
    if "enfoque" not in presentes:
        return [], "enfoque_ausente"
    return presentes, None


def _op_r8(entrada: str) -> tuple[list[str], str | None]:
    """R8 — validar la terna enumerada frente a la consulta dinámica.

    El código de error de C19 es el que el manifest congelado declara. Es un nombre poco feliz para
    lo que el caso describe, pero el insumo es **autoridad** y este flujo lo consume sin poder
    regenerarlo: devolver otro código sería ajustar el parser al gusto en vez de al contrato."""
    try:
        datos = json.loads(entrada)
    except json.JSONDecodeError:
        return [], "ac_inexistente"
    if isinstance(datos, dict) and set(datos) == {"flujo", "task_id", "ocurrencia"}:
        return [str(datos["flujo"]), str(datos["task_id"]), str(datos["ocurrencia"])], None
    return [], "ac_inexistente"


OPERACION_POR_REGLA: dict[str, Callable[[str], tuple[list[str], str | None]]] = {
    "R1": _op_r1, "R2": _op_r2, "R3": _op_r3, "R4": _op_r4,
    "R5": _op_r5, "R7": _op_r7, "R8": _op_r8,
}


# ─── Los vectores propios del arnés ─────────────────────────────────────────────────────────
#
# **AC-2 se satisface con dos autoridades, y cuál respalda qué se declara.** El manifest congelado
# responde por lo que congela —las tres fuentes de R2, la continuación multilínea, y los casos de
# R1, R3, R4, R5, R7 y R8—. **No trae** ningún golden de payload byte a byte: sus dos casos de R7
# fijan el orden de las seis clases y nada más, ni rótulos, ni saltos, ni claves de deduplicación.
# Tampoco trae fuentes coincidentes, `cobertura_en_conflicto` ni un caso multicausa.
#
# Esos son estos vectores, y responden por eso. El manifest es de un flujo archivado y no puede
# crecer; atribuirle una cobertura que su `sha256` no sostiene sería afirmar una verificación
# inexistente — el defecto que esta fase entera existe para cerrar. Lo que la declaración impide es
# leer un `fixtures` en verde como prueba de que el manifest cubre R7.
#
# Van **dentro del archivo del parser** y no en un directorio hermano: un `scripts/fixtures-arnes/`
# leído en tiempo de ejecución sería una **dependencia** por el mecanismo
# `archivo_de_configuracion_leido` que `scripts/pathset-parser.json` declara, y ese pathset dice hoy
# `dependencias: []`. Dejarla afuera del conjunto auditado es el agujero que el pathset cierra.
#
# Y se cuentan **aparte** de los 19: `manifest_sha256`, `casos_totales` y `casos_ok` hablan **solo**
# del manifest. Mezclarlos permitiría un verde con la mitad de los casos contados fuera de él.

class Vector(NamedTuple):
    id: str
    descripcion: str
    prueba: Callable[[], str | None]  # `None` = en verde; una cadena describe la divergencia


def _cmp(que: str, obtenido: object, esperado: object) -> str | None:
    return None if obtenido == esperado else f"{que}: obtenido {obtenido!r}, esperado {esperado!r}"


_GOLDEN_PIEZAS = (
    ("task", ("task",), (0,), b"- [ ] **T1 - la task del golden**"),
    ("ac", ("ac", "AC-10"), ("AC", 10, ""), b"- **AC-10:** el decimo criterio."),
    ("ac", ("ac", "AC-2"), ("AC", 2, ""), b"- **AC-2:** el segundo criterio."),
    ("filas", ("fila", "V1"), ("V", 1, ""), b"| V1 | AC-2 | test | comando | 0 fallos | RED |"),
    ("produce", ("produce", "T2"), ("T", 2, ""), b"  - **Produce:** `def f() -> int`"),
    ("bloques_globales", ("bloque", "contrato-interno"), ("contrato-interno",),
     b"## Contrato interno\n\nla convencion que el archivo entero respeta."),
    ("enfoque", ("enfoque",), (0,), b"## Enfoque\n\nel enfoque del plan."),
)

# El payload exacto, byte a byte. Escrito a mano desde R7 —no capturado de una corrida—: un golden
# copiado de la salida que se quiere probar solo verifica que el código no cambió, no que sea el
# que el contrato manda.
GOLDEN_PAYLOAD = (
    b"=== TASK ===\n"
    b"- [ ] **T1 - la task del golden**\n"
    b"\n"
    b"=== CRITERIOS DE ACEPTACI\xc3\x93N ===\n"
    b"- **AC-2:** el segundo criterio.\n"
    b"\n"
    b"- **AC-10:** el decimo criterio.\n"
    b"\n"
    b"=== FILAS DEL CONTRATO ===\n"
    b"| V1 | AC-2 | test | comando | 0 fallos | RED |\n"
    b"\n"
    b"=== INTERFACES QUE CONSUMES ===\n"
    b"  - **Produce:** `def f() -> int`\n"
    b"\n"
    b"=== BLOQUES GLOBALES ===\n"
    b"## Contrato interno\n"
    b"\n"
    b"la convencion que el archivo entero respeta.\n"
    b"\n"
    b"=== ENFOQUE DEL PLAN ===\n"
    b"## Enfoque\n"
    b"\n"
    b"el enfoque del plan.\n"
)


def _piezas_golden() -> list[Pieza]:
    """Cada texto del golden se obtiene **pasando por `recortar_pieza`**, sobre un buffer con los
    delimitadores externos que tendría en un artefacto real: saltos finales y, en el `Produce`, la
    indentación de origen.

    Construirlo con literales ya recortados dejaba el golden midiendo solo a `renderizar`: medido
    con mutantes, ni un `strip()` ni un `rstrip()` genérico dentro de `recortar_pieza` movían un
    solo byte del payload, y los dos son justamente los errores que R7 prohíbe por nombre."""
    piezas = []
    for clase, clave, orden, texto in _GOLDEN_PIEZAS:
        buf = texto + b"\n\n\n"
        piezas.append(Pieza(clase, clave, orden, recortar_pieza(buf, 0, len(buf))))
    return piezas


def _v_payload_completo() -> str | None:
    obtenido = renderizar(_piezas_golden())
    if obtenido == GOLDEN_PAYLOAD:
        return None
    return (f"payload divergente: {len(obtenido)} b contra {len(GOLDEN_PAYLOAD)} b esperados; "
            f"primer byte distinto en {next((i for i, (a, b) in enumerate(zip(obtenido, GOLDEN_PAYLOAD)) if a != b), min(len(obtenido), len(GOLDEN_PAYLOAD)))}")


def _v_clase_vacia() -> str | None:
    piezas = [p for p in _piezas_golden() if p.clase in ("task", "ac", "enfoque")]
    salida = renderizar(piezas)
    return (_cmp("rótulos emitidos", salida.count(b"=== "), 3)
            or _cmp("rótulo de una clase vacía presente", b"FILAS DEL CONTRATO" in salida, False))


def _v_varias_piezas_de_una_clase() -> str | None:
    salida = renderizar(_piezas_golden())
    return (_cmp("rótulo de AC repetido por pieza", salida.count(b"=== CRITERIOS"), 1)
            or _cmp("las dos piezas bajo el mismo rótulo",
                    b"AC-2:** el segundo criterio.\n\n- **AC-10:" in salida, True))


def _v_orden_natural() -> str | None:
    salida = renderizar(_piezas_golden())
    return _cmp("AC-2 antes que AC-10", salida.index(b"AC-2:**") < salida.index(b"AC-10:**"), True)


def _v_deduplicacion_por_clave() -> str | None:
    piezas = _piezas_golden()
    gemela = piezas[2]._replace(texto=b"OTRO TEXTO CON LA MISMA CLAVE")
    salida = renderizar(piezas + [gemela])
    return (_cmp("la clave repetida entró dos veces", b"OTRO TEXTO" in salida, False)
            or _cmp("el payload cambió al deduplicar", salida, GOLDEN_PAYLOAD))


def _v_salto_final() -> str | None:
    salida = renderizar(_piezas_golden())
    return (_cmp("termina con `\\n`", salida.endswith(b"\n"), True)
            or _cmp("termina con línea en blanco", salida.endswith(b"\n\n"), False)
            or _cmp("empieza con el primer rótulo", salida.startswith(b"=== TASK ==="), True))


def _v_frontera_de_corte() -> str | None:
    """Cero, uno y varios saltos finales tienen que dar **el mismo** recorte: los saltos hasta el
    siguiente encabezado son delimitador externo y no pertenecen a la pieza."""
    for sufijo in (b"", b"\n", b"\n\n", b"\n\n\n", b"\n   \n"):
        buf = b"contenido de la pieza" + sufijo
        fallo = _cmp(f"recorte con sufijo {sufijo!r}", recortar_pieza(buf, 0, len(buf)),
                     b"contenido de la pieza")
        if fallo:
            return fallo
    # El corte es **por líneas**, no por caracteres, y no toca ninguno de los dos extremos de una
    # línea con contenido: la indentación de origen se conserva —un `strip()` la comería— y también
    # los espacios finales significativos, que en Markdown son un salto de línea duro y que un
    # `rstrip()` genérico borraría. Los dos son los errores que R7 prohíbe por nombre.
    indentada = b"  - **Produce:** `def f() -> int`\n\n"
    fallo = _cmp("indentación de origen", recortar_pieza(indentada, 0, len(indentada)),
                 b"  - **Produce:** `def f() -> int`")
    if fallo:
        return fallo
    tabla = b"| a | b |\n| c | d |  \n\n\n"
    return _cmp("espacios finales significativos de la última línea",
                recortar_pieza(tabla, 0, len(tabla)), b"| a | b |\n| c | d |  ")


def _v_blanco_interior() -> str | None:
    """Las líneas en blanco **interiores** son contenido y se conservan intactas."""
    buf = b"primera linea\n\n\nultima linea\n\n"
    return _cmp("blancos interiores", recortar_pieza(buf, 0, len(buf)),
                b"primera linea\n\n\nultima linea")


_TASK_FUENTES_COINCIDENTES = (
    b"- [ ] **T1 - dos fuentes que dicen lo mismo**  \xc2\xb7 cubre: AC-1, AC-2\n"
    b"  - **AC:** AC-1, AC-2\n"
    b"  - **Verificar:** V1\n"
)
_TASK_EN_CONFLICTO = (
    b"- [ ] **T1 - dos fuentes que se contradicen**  \xc2\xb7 cubre: AC-1\n"
    b"  - **AC:** AC-2\n"
)


def _v_fuentes_coincidentes() -> str | None:
    ev = indexar_eventos(_TASK_FUENTES_COINCIDENTES)
    cob = capturar_cobertura(_TASK_FUENTES_COINCIDENTES, ev, parsear_id("T1"))
    return (_cmp("causa", cob.causa, None)
            or _cmp("fuente efectiva (la de mayor precedencia)", cob.fuente_efectiva, "cubre")
            or _cmp("AC", cob.ac, ["AC-1", "AC-2"])
            # Las ocurrencias son un dato **distinto** de la fuente efectiva: la efectiva decide la
            # cobertura, y las ocurrencias son lo que permite medir qué formas usa el corpus.
            or _cmp("ocurrencias registradas", cob.ocurrencias, ["cubre", "campo_con_vineta"]))


def _v_cobertura_en_conflicto() -> str | None:
    ev = indexar_eventos(_TASK_EN_CONFLICTO)
    cob = capturar_cobertura(_TASK_EN_CONFLICTO, ev, parsear_id("T1"))
    return (_cmp("causa", cob.causa, "cobertura_en_conflicto")
            # La precedencia resuelve **cuál leer cuando hay una sola**; dos que se contradicen son
            # un artefacto roto, y que gane la de mayor precedencia taparía el defecto.
            or _cmp("no se elige fuente efectiva", cob.fuente_efectiva, ""))


_TASKS_MULTICAUSA = (
    b"- [ ] **T1 - tres fallas a la vez**  \xc2\xb7 cubre: AC-99\n"
    b"  - **Verificar:** V99\n"
    b"  - **Consume:** la interfaz compartida, en prosa y sin forma\n"
)


def _v_multicausa_observable() -> str | None:
    """Las **tres** señales de una task multicausa, observables a la vez con las funciones de
    R1–R5. Que el clasificador las **acumule** sin cortocircuito lo prueba
    `autotest_clasificador_multicausa`: acá se fija la precondición de que las tres existan
    simultáneamente, que es lo que hace posible el defecto que aquel autotest caza."""
    ev = indexar_eventos(_TASKS_MULTICAUSA)
    cob = capturar_cobertura(_TASKS_MULTICAUSA, ev, parsear_id("T1"))
    campo = extraer_campo(_TASKS_MULTICAUSA, ev, parsear_id("T1"), "Consume")
    _, _, causas = resolver_consume(_TASKS_MULTICAUSA[campo[0]:campo[1]].decode(),
                                    set(), set(), {})
    filas, _ = filas_del_contrato(b"## Verification\n\n| V1 | x |\n")
    spec = b"# Spec\n\n- **AC-1:** el unico criterio que esta spec declara.\n"
    declarados, _ = bloques_por_id(spec, indexar_eventos(spec), "ac")
    return (_cmp("AC citado", cob.ac, ["AC-99"])
            # Se consulta el índice **real** de la spec sintética. Escribir `"AC-99" in {"AC-1"}`
            # era una constante: ninguna mutación del parser podía ponerlo rojo.
            or _cmp("el AC citado no está declarado en la spec", "AC-99" in declarados, False)
            or _cmp("la spec sintética sí declara AC-1", "AC-1" in declarados, True)
            or _cmp("la fila citada no existe en el contrato", "V99" in filas, False)
            or _cmp("la sección sí declara V1", "V1" in filas, True)
            or _cmp("Consume sin tipo", causas, ["consume_no_tipado"]))


VECTORES: tuple[Vector, ...] = (
    Vector("ARN-R7-01", "payload completo byte a byte", _v_payload_completo),
    Vector("ARN-R7-02", "clase vacía: no emite su rótulo", _v_clase_vacia),
    Vector("ARN-R7-03", "varias piezas de una clase bajo un solo rótulo",
           _v_varias_piezas_de_una_clase),
    Vector("ARN-R7-04", "orden natural: AC-2 antes que AC-10", _v_orden_natural),
    Vector("ARN-R7-05", "deduplicación por clave de clase, nunca por contenido",
           _v_deduplicacion_por_clave),
    Vector("ARN-R7-06", "un único `\\n` final y ninguna línea en blanco antes del primer rótulo",
           _v_salto_final),
    Vector("ARN-R7-07", "frontera del corte: cero, uno y varios saltos finales",
           _v_frontera_de_corte),
    Vector("ARN-R7-08", "pieza con líneas en blanco interiores", _v_blanco_interior),
    Vector("ARN-R2-01", "fuentes coincidentes: una efectiva, todas las ocurrencias",
           _v_fuentes_coincidentes),
    Vector("ARN-R2-02", "`cobertura_en_conflicto`: la precedencia no lo resuelve",
           _v_cobertura_en_conflicto),
    Vector("ARN-R5-01", "task multicausa: las tres señales observables a la vez",
           _v_multicausa_observable),
)


def correr_vectores() -> list[dict]:
    """Cada vector propio con su id y su resultado. Es lo que el CLI enumera en la **traza de
    stderr**: en verde, `divergencias[]` está vacío por contrato, así que ahí los vectores propios
    serían invisibles y `fixtures` podría no correr ninguno sin que nada lo mostrara."""
    salida = []
    for v in VECTORES:
        try:
            detalle = v.prueba()
        except Exception as e:  # un vector que revienta es un vector rojo, no una corrida abortada
            detalle = f"excepción: {type(e).__name__}: {e}"
        salida.append({"id": v.id, "descripcion": v.descripcion, "ok": detalle is None,
                       "detalle": detalle})
    return salida


def _sha256_de(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def _canonico(valor: object) -> bytes:
    """JSON compacto, claves ordenadas y UTF-8 sin escapar. Es la forma en que este archivo
    convierte una estructura en **bytes con identidad**."""
    return json.dumps(valor, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def ejecutar_fixtures(manifest: Path | dict = RUTA_CASOS) -> dict:
    """Corre cada caso del manifest congelado por la tabla regla → operación, y aparte los vectores
    propios del arnés.

    `manifest` acepta un `dict` para que `autotest_fixtures_mutante` pueda inyectar una copia
    mutada **por parámetro de esta capa**: el CLI sigue teniendo exactamente tres subcomandos, y
    una opción pública nueva para probar el modo sería ampliar el contrato de AC-8 para poder
    verificarlo."""
    if isinstance(manifest, dict):
        datos, errores = manifest, []
        sha = _sha256_de(_canonico(manifest))
    else:
        schema = json.loads(SCHEMA_CASOS.read_bytes().decode("utf-8"))
        datos, errores = cargar_insumo(manifest, schema)
        sha = _sha256_de(manifest.read_bytes()) if manifest.exists() else ""

    divergencias: list[dict] = []
    for e in errores:
        divergencias.append({"caso_id": "(manifest)", "esperado": "insumo válido contra su schema",
                             "obtenido": e})

    casos = datos.get("casos", [])
    ok = 0
    for caso in casos:
        operacion = OPERACION_POR_REGLA.get(caso["regla"])
        if operacion is None:
            divergencias.append({"caso_id": caso["id"], "regla": caso["regla"],
                                 "esperado": "una operación declarada para la regla",
                                 "obtenido": f"la regla {caso['regla']} no está en la tabla"})
            continue
        try:
            valor, error = operacion(caso["entrada"])
        except Exception as exc:
            valor, error = [], f"excepción {type(exc).__name__}: {exc}"
        if "salida_esperada" in caso:
            esperado, obtenido = caso["salida_esperada"]["valor"], valor
            bien = error is None and valor == esperado
            if error is not None:
                obtenido = f"error {error}"
        else:
            esperado, obtenido = caso["error_esperado"]["codigo"], error
            bien = error == esperado
            if error is None:
                obtenido = f"salida {valor}"
        if bien:
            ok += 1
        else:
            divergencias.append({"caso_id": caso["id"], "regla": caso["regla"],
                                 "esperado": json.dumps(esperado, ensure_ascii=False),
                                 "obtenido": json.dumps(obtenido, ensure_ascii=False)})

    vectores = correr_vectores()
    for v in vectores:
        if not v["ok"]:
            divergencias.append({"caso_id": v["id"], "regla": "ARN",
                                 "esperado": v["descripcion"], "obtenido": v["detalle"]})

    return {
        # `manifest_sha256`, `casos_totales` y `casos_ok` hablan **solo** del manifest: los
        # vectores propios se cuentan aparte, o un verde podría tener la mitad de sus casos
        # contados fuera del archivo que el `sha256` respalda.
        "manifest_sha256": sha,
        "casos_totales": len(casos),
        "casos_ok": ok,
        "divergencias": divergencias,
        "vectores_propios_totales": len(vectores),
        "vectores_propios_ok": sum(1 for v in vectores if v["ok"]),
    }


def autotest_fixtures_mutante() -> int:
    """El modo `fixtures` **se pone rojo** cuando un caso diverge.

    Sin esto, un modo que no compare nada devolvería 19/19 y `divergencias` vacío exactamente igual
    que uno correcto. Se mutan las dos formas de caso —el que declara `salida_esperada.valor` y el
    que declara `error_esperado.codigo`—, porque son dos ramas distintas de la comparación."""
    schema = json.loads(SCHEMA_CASOS.read_bytes().decode("utf-8"))
    base, errores = cargar_insumo(RUTA_CASOS, schema)
    if errores:
        print(f"el manifest congelado no valida: {errores[:2]}", file=sys.stderr)
        return 1

    fallas: list[str] = []
    for clave, mutacion in (("salida_esperada", lambda c: c["salida_esperada"].__setitem__(
                                "valor", ["VALOR-QUE-EL-PARSER-NUNCA-DEVUELVE"])),
                            ("error_esperado", lambda c: c["error_esperado"].__setitem__(
                                "codigo", "codigo_inventado_que_no_existe"))):
        mutado = json.loads(json.dumps(base))
        objetivo = next((c for c in mutado["casos"] if clave in c), None)
        if objetivo is None:
            fallas.append(f"el manifest no tiene ningún caso con `{clave}`: la rama queda sin ejercer")
            continue
        mutacion(objetivo)
        salida = ejecutar_fixtures(manifest=mutado)
        nombrados = {d["caso_id"] for d in salida["divergencias"]}
        if salida["casos_ok"] >= salida["casos_totales"]:
            fallas.append(f"mutando `{clave}` de {objetivo['id']}: el modo siguió contando "
                          f"{salida['casos_ok']}/{salida['casos_totales']} casos en verde")
        if objetivo["id"] not in nombrados:
            fallas.append(f"mutando `{clave}`: el modo no nombró el caso {objetivo['id']} "
                          f"en `divergencias[]` (nombró {sorted(nombrados)})")
        else:
            d = next(x for x in salida["divergencias"] if x["caso_id"] == objetivo["id"])
            if not d.get("esperado") or not d.get("obtenido"):
                fallas.append(f"la divergencia de {objetivo['id']} no trae esperado y obtenido")

    # Control en la otra dirección: **sin** mutar, el modo tiene que estar en verde. Un autotest
    # que solo comprueba el rojo pasaría igual con un modo que declare divergencias siempre.
    limpio = ejecutar_fixtures(manifest=base)
    if limpio["divergencias"] or limpio["casos_ok"] != limpio["casos_totales"]:
        fallas.append(f"sin mutar, el modo no está en verde: {limpio['divergencias'][:2]}")

    for f in fallas:
        print(f"FALLA autotest_fixtures_mutante: {f}", file=sys.stderr)
    return 1 if fallas else 0


# ─── R8 / AC-3 — La instantánea verificada ──────────────────────────────────────────────────
#
# **La unidad de lectura es el buffer verificado, y se lee una sola vez.** `censo` y
# `medir-historico` arrancan los dos por acá: se validan los tres insumos, se lee cada artefacto
# como bytes, se comparan tamaño y `sha256` **sobre ese mismo buffer**, y solo si no hay ninguna
# discrepancia se construyen los índices. Leer el archivo una vez para hashear y otra para parsear
# deja una ventana donde el segundo contenido puede no ser el sellado — y `.plans/` no está
# versionado, así que el contenido puede cambiar sin alterar una sola terna. Al abrir el gate de la
# spec, el conteo de `· cubre:` ya se había movido de 185 a 187 sin que nadie pueda decir cuándo.

class IndiceDeFlujo(NamedTuple):
    """Todo lo que el clasificador necesita evaluar, ya calculado.

    Un índice incompleto obliga a recalcular por dentro del clasificador y rompe la función única
    de AC-4: dos caminos para el mismo hecho divergen. Los campos `ac_bloques` y `task_bloques`
    llevan los **rangos** que la proyección de R7 necesita; `ac_declarados` y `tasks` son sus
    conjuntos de claves, que es la forma en que el clasificador los consulta."""
    buffers: dict[str, bytes]
    eventos: dict[str, list[Evento]]
    ac_declarados: set[str]
    tasks: set[str]
    filas: dict[str, tuple[int, int]]
    filas_duplicadas: list[str]
    bloques: dict[str, tuple[int, int]]
    bloques_duplicados: list[str]
    produce: dict[str, tuple[int, int]]
    enfoque: tuple[int, int] | None
    ac_bloques: dict[str, tuple[int, int]]
    task_bloques: dict[str, tuple[int, int]]
    ac_duplicados: list[str]
    task_duplicadas: list[str]
    cobertura: dict[str, Cobertura]
    filas_citadas: dict[str, list[str]]
    consume: dict[str, tuple[int, int] | None]


class Indices(NamedTuple):
    flujos: dict[str, IndiceDeFlujo]
    ternas: list[tuple[str, str, int]]


def _indexar_flujo(buffers: dict[str, bytes]) -> IndiceDeFlujo:
    eventos = {a: indexar_eventos(b) for a, b in buffers.items()}
    ac_bloques, ac_dup = bloques_por_id(buffers["spec.md"], eventos["spec.md"], "ac")
    task_bloques, task_dup = bloques_por_id(buffers["tasks.md"], eventos["tasks.md"], "task")
    filas, filas_dup = filas_del_contrato(buffers["plan.md"])
    bloques, bloques_dup = bloques_globales(buffers["tasks.md"], eventos["tasks.md"])

    produce: dict[str, tuple[int, int]] = {}
    cobertura: dict[str, Cobertura] = {}
    citadas: dict[str, list[str]] = {}
    consume: dict[str, tuple[int, int] | None] = {}
    declarados = set(ac_bloques)
    for tid in task_bloques:
        ident = parsear_id(tid)
        if ident is None:
            continue
        rango = extraer_campo(buffers["tasks.md"], eventos["tasks.md"], ident, "Produce")
        if rango is not None:
            produce[tid] = rango
        cobertura[tid] = capturar_cobertura(buffers["tasks.md"], eventos["tasks.md"], ident,
                                            declarados)
        verificar = extraer_campo(buffers["tasks.md"], eventos["tasks.md"], ident, "Verificar")
        texto = (buffers["tasks.md"][verificar[0]:verificar[1]].decode("utf-8", "replace")
                 if verificar else "")
        citadas[tid] = re.findall(r"\bV\d+[a-z]?\b", texto)
        consume[tid] = extraer_campo(buffers["tasks.md"], eventos["tasks.md"], ident, "Consume")

    return IndiceDeFlujo(
        buffers=buffers, eventos=eventos, ac_declarados=declarados, tasks=set(task_bloques),
        filas=filas, filas_duplicadas=filas_dup, bloques=bloques, bloques_duplicados=bloques_dup,
        produce=produce, enfoque=extraer_enfoque(buffers["plan.md"]), ac_bloques=ac_bloques,
        task_bloques=task_bloques, ac_duplicados=ac_dup, task_duplicadas=task_dup,
        cobertura=cobertura, filas_citadas=citadas, consume=consume)


def cargar_instantanea_verificada(raiz: Path = RAIZ) -> tuple[Indices | None, list[str]]:
    """Valida los insumos, lee el corpus **una sola vez** y verifica sus sellos antes de indexar.

    Ante **cualquier** discrepancia de `sha256` o de tamaño se aborta nombrando flujo, artefacto,
    valor esperado y valor hallado. **No hay camino que continúe con advertencia**: imprimir una
    línea amarilla y seguir publicaría el número sobre un corpus que ya no es el declarado, que es
    el defecto exacto que AC-3 existe para impedir. Re-congelar el manifest es un acto deliberado y
    fechado, nunca un efecto de correr la medición.

    **El segundo de los dos únicos puntos de I/O** de la capa 2."""
    errores: list[str] = []
    for ruta, ruta_schema in ((RUTA_CORPUS, SCHEMA_CORPUS), (RUTA_CASOS, SCHEMA_CASOS),
                              (RUTA_ORACULO, SCHEMA_ORACULO)):
        try:
            schema = json.loads((raiz / ruta_schema).read_bytes().decode("utf-8"))
        except OSError as e:
            errores.append(f"no se pudo leer el schema `{ruta_schema}`: {e}")
            continue
        _, errs = cargar_insumo(raiz / ruta, schema)
        errores.extend(errs)
    if errores:
        return None, errores

    corpus = json.loads((raiz / RUTA_CORPUS).read_bytes().decode("utf-8"))
    flujos: dict[str, IndiceDeFlujo] = {}
    discrepancias: list[str] = []
    for entrada in corpus["flujos"]:
        buffers: dict[str, bytes] = {}
        for art in entrada["artefactos"]:
            destino = raiz / art["ruta"]
            try:
                buf = destino.read_bytes()
            except OSError as e:
                discrepancias.append(f"{entrada['flujo']} · {art['artefacto']}: no se pudo leer "
                                     f"`{art['ruta']}`: {e}")
                continue
            # Tamaño y hash se comparan **sobre este mismo buffer**, no releyendo el archivo.
            if len(buf) != art["tamano"]:
                discrepancias.append(
                    f"{entrada['flujo']} · {art['artefacto']}: tamaño esperado {art['tamano']} b, "
                    f"hallado {len(buf)} b")
                continue
            hallado = _sha256_de(buf)
            if hallado != art["sha256"]:
                discrepancias.append(
                    f"{entrada['flujo']} · {art['artefacto']}: sha256 esperado {art['sha256']}, "
                    f"hallado {hallado}")
                continue
            buffers[art["artefacto"]] = buf
        if len(buffers) == 3:
            flujos[entrada["flujo"]] = _indexar_flujo(buffers)

    if discrepancias:
        return None, discrepancias

    ternas = [(t["flujo"], t["task_id"], t["ocurrencia"]) for t in corpus["ternas"]]
    return Indices(flujos=flujos, ternas=ternas), []


def _copiar_arbol_minimo(destino: Path) -> None:
    """Los tres insumos, sus tres schemas y los artefactos que el manifest enumera. Nada más: es el
    árbol mínimo sobre el que la instantánea puede correr entera."""
    (destino / "scripts").mkdir(parents=True, exist_ok=True)
    for ruta in (RUTA_CORPUS, RUTA_CASOS, RUTA_ORACULO, SCHEMA_CORPUS, SCHEMA_CASOS,
                 SCHEMA_ORACULO):
        (destino / ruta).write_bytes(ruta.read_bytes())
    corpus = json.loads(RUTA_CORPUS.read_bytes().decode("utf-8"))
    for entrada in corpus["flujos"]:
        for art in entrada["artefactos"]:
            copia = destino / art["ruta"]
            copia.parent.mkdir(parents=True, exist_ok=True)
            copia.write_bytes(Path(art["ruta"]).read_bytes())


def _alterar(destino: Path, modo: str) -> tuple[str, str]:
    """Rompe **un** sello del árbol copiado y devuelve `(flujo, artefacto)` alterado.

    `hash` cambia un byte **conservando el tamaño**, para que la discrepancia solo pueda detectarla
    el `sha256`; `tamano` agrega un byte. Son dos discrepancias distintas y las dos tienen que
    abortar: un arnés que solo compare tamaños queda verde ante una edición del mismo largo."""
    corpus = json.loads((destino / RUTA_CORPUS).read_bytes().decode("utf-8"))
    entrada = corpus["flujos"][0]
    art = entrada["artefactos"][0]
    ruta = destino / art["ruta"]
    crudo = bytearray(ruta.read_bytes())
    if modo == "hash":
        crudo[0] = crudo[0] ^ 0x20  # mismo tamaño, distinto contenido
    else:
        crudo.extend(b"x")
    ruta.write_bytes(bytes(crudo))
    return entrada["flujo"], art["artefacto"]


def autotest_sellos_seam() -> int:
    """Las dos discrepancias —hash y tamaño— contra `cargar_instantanea_verificada` directamente.

    Los **cuatro cruces** de AC-3 (discrepancia × modo histórico) los corre `autotest_sellos_modos`,
    que vive en la capa del CLI porque es el primer punto donde los dos modos ya existen."""
    fallas: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp)
        _copiar_arbol_minimo(raiz)

        # Control en la dirección positiva: el árbol **copiado sin alterar** tiene que verificar.
        # Sin él, un seam que abortara siempre pasaría los dos casos negativos.
        indices, errores = cargar_instantanea_verificada(raiz)
        if indices is None or errores:
            fallas.append(f"el árbol copiado sin alterar no verifica: {errores[:2]}")

        for modo in ("hash", "tamano"):
            with tempfile.TemporaryDirectory() as otro:
                sucio = Path(otro)
                _copiar_arbol_minimo(sucio)
                flujo, artefacto = _alterar(sucio, modo)
                indices, errores = cargar_instantanea_verificada(sucio)
                if indices is not None:
                    fallas.append(f"discrepancia de {modo}: la instantánea NO abortó")
                    continue
                texto = " · ".join(errores)
                for que, aguja in (("flujo", flujo), ("artefacto", artefacto),
                                   ("valor esperado", "esperado"), ("valor hallado", "hallado")):
                    if aguja not in texto:
                        fallas.append(f"discrepancia de {modo}: el error no nombra el {que} "
                                      f"({aguja!r} no aparece en {texto[:160]!r})")
    for f in fallas:
        print(f"FALLA autotest_sellos_seam: {f}", file=sys.stderr)
    return 1 if fallas else 0


# ─── AC-4 / AC-5 — El clasificador total ────────────────────────────────────────────────────

def clasificar(flujo: str, task: Identificador, idx: IndiceDeFlujo) -> frozenset[str]:
    """`task → conjunto COMPLETO de causas`, **sin cortocircuito**.

    Una task con un AC inexistente, una fila inexistente y un `Consume` inválido tiene **tres**
    causas, no la primera que se encuentre. Detenerse en la primera y acumularlas todas son dos
    resultados conformes con «excluye con su causa nombrada», y el desglose por causa —del que se
    deriva el piso— sale distinto en cada uno.

    Ningún bloque de abajo hace `return`: cada uno agrega a un `set` y sigue. Es **una sola**
    función y alimenta tanto al censo como a la medición; no hay una versión resumida para uno y
    otra para el otro."""
    causas: set[str] = set()
    tid = str(task)

    # (1) y (9) cobertura y errores de rango de R1 — vienen los dos de la misma captura.
    cobertura = idx.cobertura.get(tid)
    if cobertura is None or cobertura.causa:
        causas.add(cobertura.causa if cobertura else "sin_cobertura")

    # (2) existencia de los AC citados. Un AC con `duplicado_normativo` no está en `ac_bloques`,
    # pero su causa es el duplicado y no la inexistencia: atribuirla mal haría que la corrección
    # apunte al lugar equivocado.
    for ac in (cobertura.ac if cobertura else []):
        if ac in idx.ac_duplicados:
            causas.add("duplicado_normativo")
        elif ac not in idx.ac_declarados:
            causas.add("ac_inexistente")

    # (3) y (4) filas citadas y sus duplicados.
    for v in idx.filas_citadas.get(tid, []):
        if v in idx.filas_duplicadas:
            causas.add("fila_duplicada")
        elif v not in idx.filas:
            causas.add("fila_inexistente")

    # (4bis) la propia task declarada dos veces fuera de un apéndice.
    if tid in idx.task_duplicadas:
        causas.add("duplicado_normativo")

    # (5), (6) y (7) `Consume`: tipado, tasks consumidas con su `Produce`, y bloques globales.
    rango = idx.consume.get(tid)
    if rango is not None:
        texto = idx.buffers["tasks.md"][rango[0]:rango[1]].decode("utf-8", "replace")
        _, _, causas_consume = resolver_consume(texto, idx.tasks, set(idx.produce), idx.bloques,
                                                idx.bloques_duplicados)
        causas.update(causas_consume)

    # (8) el `## Enfoque` del plan, una de las dos piezas siempre presentes.
    if idx.enfoque is None:
        causas.add("enfoque_ausente")

    return frozenset(causas)


# Los dos mutantes que la fila V5 exige. Viven acá, al lado de lo que mutan, porque son la única
# evidencia de que la propiedad «total y sin cortocircuito» se puede poner **roja**: un clasificador
# que cortara en la primera causa devolvería un resultado igual de conforme con la letra de AC-5.

def _clasificar_cortando(flujo: str, task: Identificador, idx: IndiceDeFlujo) -> frozenset[str]:
    """MUTANTE — corta en la primera causa que encuentra."""
    todas = clasificar(flujo, task, idx)
    return frozenset(list(sorted(todas, key=lambda c: ORDEN_DE_CAUSA[c]))[:1])


def _clasificar_omitiendo(flujo: str, task: Identificador, idx: IndiceDeFlujo,
                          omitida: str) -> frozenset[str]:
    """MUTANTE — evalúa todas las familias menos una."""
    return frozenset(c for c in clasificar(flujo, task, idx) if c != omitida)


_SPEC_MULTICAUSA = b"""# Spec sintetica

- **AC-1:** Given algo, When otra cosa, Then el unico criterio declarado.
"""
_PLAN_MULTICAUSA = b"""# Plan sintetico

## Enfoque

el enfoque del plan sintetico.

## Verification

| ID | Requisito | Evidencia |
|---|---|---|
| V1 | AC-1 | test |
"""
_TASKS_MULTICAUSA_FLUJO = (
    b"# Tasks sinteticas\n\n"
    b"- [ ] **T1 - tres fallas a la vez**  \xc2\xb7 cubre: AC-99\n"
    b"  - **Verificar:** V99\n"
    b"  - **Consume:** la interfaz compartida, en prosa y sin ninguna forma reconocible\n"
)


def _indice_multicausa() -> IndiceDeFlujo:
    return _indexar_flujo({"spec.md": _SPEC_MULTICAUSA, "plan.md": _PLAN_MULTICAUSA,
                           "tasks.md": _TASKS_MULTICAUSA_FLUJO})


def autotest_clasificador_multicausa() -> int:
    """El vector sintético multicausa devuelve **las tres** causas, y los dos mutantes lo ponen rojo.

    La propiedad no se apoya en que el corpus tenga tasks multicausa: eso es accidente del corpus,
    no diseño. Por eso el vector es sintético y está escrito para tener exactamente tres."""
    fallas: list[str] = []
    idx = _indice_multicausa()
    task = parsear_id("T1")
    esperado = frozenset({"ac_inexistente", "fila_inexistente", "consume_no_tipado"})

    obtenido = clasificar("sintetico", task, idx)
    if obtenido != esperado:
        fallas.append(f"el vector multicausa devolvió {sorted(obtenido)} y no {sorted(esperado)}")

    cortado = _clasificar_cortando("sintetico", task, idx)
    if cortado == esperado:
        fallas.append("el mutante que corta en la primera causa NO puso el vector en rojo: "
                      "la propiedad «sin cortocircuito» no se está midiendo")
    for omitida in sorted(esperado):
        parcial = _clasificar_omitiendo("sintetico", task, idx, omitida)
        if parcial == esperado:
            fallas.append(f"el mutante que omite `{omitida}` NO puso el vector en rojo")

    # Control en la otra dirección: una task **sana** no debe devolver ninguna causa. Sin él, un
    # clasificador que devolviera las dieciséis siempre pasaría los mutantes de arriba.
    sana = _indexar_flujo({
        "spec.md": _SPEC_MULTICAUSA, "plan.md": _PLAN_MULTICAUSA,
        "tasks.md": (b"# Tasks sinteticas\n\n"
                     b"- [ ] **T1 - sana**  \xc2\xb7 cubre: AC-1\n"
                     b"  - **Verificar:** V1\n"
                     b"  - **Produce:** algo\n")})
    limpio = clasificar("sintetico", parsear_id("T1"), sana)
    if limpio:
        fallas.append(f"una task sana devolvió causas: {sorted(limpio)}")

    # Y el enum es **cerrado**: nada de lo que salga puede estar fuera de las dieciséis.
    for c in obtenido | limpio:
        if c not in ORDEN_DE_CAUSA:
            fallas.append(f"causa fuera del enum cerrado: `{c}`")

    for f in fallas:
        print(f"FALLA autotest_clasificador_multicausa: {f}", file=sys.stderr)
    return 1 if fallas else 0


# ─── AC-4 / AC-11 — El censo ────────────────────────────────────────────────────────────────

# **El alcance de la comparación de `causas[]` contra el oráculo.** AC-11 manda compararlas
# bidireccionalmente y fallar. Se compara el grupo de **cobertura**, que es la dimensión que el
# método del oráculo observó: sus tres etapas —detectar, comparar, adjudicar— corrieron sobre
# declaraciones de cobertura, y sus veintisiete `desacuerdos[]` traen `fuente_r2` y listas de AC.
# Ninguna etapa miró un campo `Consume`.
#
# El dato que lo decide: el **mismo flujo**, en el **mismo commit**, congeló el caso C15 del
# manifest declarando que el `Consume` de `herdr-transporte-skills/T8` es `consume_no_tipado`.
# Exigir igualdad sobre el conjunto completo pondría a los dos insumos congelados a contradecirse
# entre sí en tres ternas. Las causas de fuera del grupo se **reportan** en `tasks_excluidas[]`,
# donde el desglose del piso las usa; lo que no hacen es fallar contra un oráculo que no las mira.
# Decidido en el gate de implementación (2026-08-12).
CAUSAS_DE_COBERTURA: frozenset[str] = frozenset({"sin_cobertura", "cobertura_en_conflicto"})


def canonicalizar_exclusiones(exclusiones: list[dict]) -> bytes:
    """La identidad observable del conjunto de exclusiones.

    Orden por flujo, id natural y ocurrencia; `causas[]` en el orden de `CAUSAS`; JSON compacto,
    claves ordenadas y UTF-8 sin escapar. Se hashean **esos** bytes. Sin una identidad que viaje
    entre los dos modos, «consume el conjunto del censo» y «reclasifica por su cuenta» producen
    salidas indistinguibles."""
    ordenadas = sorted(exclusiones,
                       key=lambda e: (e["flujo"], clave_orden(e["task_id"]), e["ocurrencia"]))
    normalizadas = [{"flujo": e["flujo"], "task_id": e["task_id"], "ocurrencia": e["ocurrencia"],
                     "causas": sorted(e["causas"], key=lambda c: ORDEN_DE_CAUSA[c])}
                    for e in ordenadas]
    return _canonico(normalizadas)


def censo_desde_indices(indices: Indices, oraculo: dict, corpus: dict) -> dict:
    """El censo, sobre índices ya verificados. Separado de `ejecutar_censo` para que los mutantes de
    V11b puedan inyectar un corpus o un esperado alterados **sin** tocar el disco ni el CLI."""
    hallazgos: list[str] = []

    # (1) Conjuntos, bidireccionalmente. Comparar **cantidades** dejaría que una task perdida y una
    # espuria se compensen, y el censo quedaría verde con el corpus movido.
    declaradas = {(f, t, o) for f, t, o in indices.ternas}
    descubiertas: set[tuple[str, str, int]] = set()
    for flujo, idx in indices.flujos.items():
        for tid in idx.tasks:
            descubiertas.add((flujo, tid, 1))
    sobran = sorted(descubiertas - declaradas)
    faltan = sorted(declaradas - descubiertas)
    if sobran or faltan:
        hallazgos.append(f"el conjunto descubierto no coincide con el declarado: "
                         f"{len(sobran)} sobran, {len(faltan)} faltan")

    # (2) Clasificación, con la **misma** función que usa la medición.
    excluidas: list[dict] = []
    fuera_del_enum: list[str] = []
    causas_por_terna: dict[tuple[str, str], frozenset[str]] = {}
    por_flujo: list[dict] = []
    for flujo in sorted(indices.flujos):
        idx = indices.flujos[flujo]
        totales = 0
        cuenta_excluidas = 0
        for tid in sorted(idx.tasks, key=clave_orden):
            ident = parsear_id(tid)
            if ident is None:
                continue
            totales += 1
            causas = clasificar(flujo, ident, idx)
            causas_por_terna[(flujo, tid)] = causas
            for c in causas:
                if c not in ORDEN_DE_CAUSA:
                    fuera_del_enum.append(f"{flujo} {tid}: `{c}`")
            if causas:
                cuenta_excluidas += 1
                excluidas.append({"flujo": flujo, "task_id": tid, "ocurrencia": 1,
                                  "causas": sorted(causas, key=lambda c: ORDEN_DE_CAUSA[c])})
        elegibles = totales - cuenta_excluidas
        por_flujo.append({
            "flujo": flujo, "tasks_totales": totales, "elegibles": elegibles,
            "excluidas": cuenta_excluidas,
            "tasa_elegibilidad": (elegibles / totales) if totales else 0.0,
            "degradado": bool(totales) and (cuenta_excluidas / totales) > UMBRAL_FLUJO,
        })
    if fuera_del_enum:
        # Una task que no encaja en ninguna causa es un **error del arnés**, no una exclusión
        # silenciosa: el enum es cerrado.
        hallazgos.append(f"causas fuera del enum cerrado: {fuera_del_enum[:5]}")

    # (3) Cobertura por fuente de R2 — el control positivo de AC-11.
    por_fuente = {f: {"declaradas": 0, "resueltas": 0, "ocurrencias_reconocidas": 0,
                      "fuentes_efectivas": 0} for f in FUENTES_R2}
    obtenida: dict[tuple[str, str], tuple[str, frozenset[str]]] = {}
    for flujo in sorted(indices.flujos):
        idx = indices.flujos[flujo]
        for tid, cob in idx.cobertura.items():
            for f in cob.ocurrencias:
                por_fuente[f]["declaradas"] += 1
                por_fuente[f]["ocurrencias_reconocidas"] += 1
                if any(ac in idx.ac_declarados for ac in cob.ac):
                    por_fuente[f]["resueltas"] += 1
            if cob.fuente_efectiva:
                por_fuente[cob.fuente_efectiva]["fuentes_efectivas"] += 1
                obtenida[(flujo, tid)] = (cob.fuente_efectiva, frozenset(cob.ac))

    if sum(v["resueltas"] for v in por_fuente.values()) == 0:
        hallazgos.append("el total global de declaraciones resueltas es CERO: es indistinguible de "
                         "un corpus sin cobertura, y es el modo de fallo que este control cierra")
    for f in FUENTES_R2:
        if por_fuente[f]["resueltas"] == 0:
            hallazgos.append(f"la fuente `{f}` de R2 resuelve CERO en todo el corpus: un parser "
                             f"ciego a una forma convierte en exclusiones a los flujos que la usan")

    # (4) Comparación bidireccional contra el conjunto esperado: faltantes **y** espurios. Un
    # control que solo mira lo que el parser pierde deja pasar al parser que **inventa**.
    esperada = {(r["flujo"], r["task_id"]): (r["fuente_r2"], frozenset(r["ac"]))
                for r in oraculo["relacion"]}
    perdidas: list[dict] = []
    sobrantes: list[dict] = []
    for clave, (fuente, acs) in sorted(esperada.items()):
        vistos = obtenida.get(clave)
        for ac in sorted(acs - (vistos[1] if vistos else frozenset()), key=clave_orden):
            perdidas.append({"flujo": clave[0], "task_id": clave[1], "fuente_r2": fuente,
                             "ac": ac})
    for clave, (fuente, acs) in sorted(obtenida.items()):
        ref = esperada.get(clave)
        for ac in sorted(acs - (ref[1] if ref else frozenset()), key=clave_orden):
            sobrantes.append({"flujo": clave[0], "task_id": clave[1], "fuente_r2": fuente,
                              "ac": ac})
    if perdidas:
        hallazgos.append(f"{len(perdidas)} declaraciones del conjunto esperado que el parser NO "
                         f"resuelve: {perdidas[:3]}")
    if sobrantes:
        hallazgos.append(f"{len(sobrantes)} declaraciones que el parser atribuye y el conjunto "
                         f"esperado no tiene: {sobrantes[:3]}")

    # (5) Las `causas[]` de cada terna que el oráculo declara excluida, bidireccionalmente y
    # **acotadas al grupo de cobertura** (ver la nota de `CAUSAS_DE_COBERTURA`).
    for e in oraculo["exclusiones"]:
        clave = (e["flujo"], e["task_id"])
        del_oraculo = set(e["causas"]) & CAUSAS_DE_COBERTURA
        del_clasificador = set(causas_por_terna.get(clave, frozenset())) & CAUSAS_DE_COBERTURA
        if del_oraculo != del_clasificador:
            hallazgos.append(
                f"{clave[0]} {clave[1]}: causas de cobertura del oráculo "
                f"{sorted(del_oraculo)} contra las del clasificador {sorted(del_clasificador)} "
                f"(faltan {sorted(del_oraculo - del_clasificador)}, "
                f"sobran {sorted(del_clasificador - del_oraculo)})")

    # (6) El máximo del corpus lo **deriva el censo**, no se cita a mano: AC-9 exige esa
    # procedencia, y sin un campo donde emitirlo V9 lo recalcularía por fuera y la perdería.
    tamanos = {e["flujo"]: sum(a["tamano"] for a in e["artefactos"]) for e in corpus["flujos"]}
    flujo_maximo = max(tamanos, key=lambda f: (tamanos[f], f)) if tamanos else ""

    denominador = len(indices.ternas)
    return {
        "declarados": len(declaradas),
        "descubiertos": len(descubiertas),
        "sobran": [{"flujo": f, "task_id": t, "ocurrencia": o} for f, t, o in sobran],
        "faltan": [{"flujo": f, "task_id": t, "ocurrencia": o} for f, t, o in faltan],
        "hash_mismatch": [],
        "tasks_excluidas": excluidas,
        "hash_exclusiones": _sha256_de(canonicalizar_exclusiones(excluidas)),
        "denominador_tasks": denominador,
        "piso": (len(excluidas) / denominador) if denominador else 0.0,
        "por_flujo": por_flujo,
        "cobertura_por_fuente_r2": por_fuente,
        "perdidas_vs_esperado": perdidas,
        "sobran_vs_esperado": sobrantes,
        "maximo_corpus": {"flujo": flujo_maximo, "bytes": tamanos.get(flujo_maximo, 0)},
        "causas_fuera_del_enum": fuera_del_enum,
        "hallazgos": hallazgos,
    }


def ejecutar_censo(raiz: Path = RAIZ) -> dict:
    """Compara el corpus descubierto contra el declarado, clasifica y emite el hash de exclusiones."""
    indices, errores = cargar_instantanea_verificada(raiz)
    if indices is None:
        # Ante discrepancia de sello **se aborta**: no hay camino que continúe con advertencia.
        return {
            "declarados": 0, "descubiertos": 0, "sobran": [], "faltan": [],
            "hash_mismatch": [{"flujo": "(varios)", "artefacto": "(varios)", "campo": "sello",
                               "esperado": "el sello del manifest", "hallado": e}
                              for e in errores],
            "tasks_excluidas": [], "hash_exclusiones": "0" * 64, "denominador_tasks": 0,
            "piso": 0.0, "por_flujo": [], "perdidas_vs_esperado": [], "sobran_vs_esperado": [],
            "cobertura_por_fuente_r2": {f: {"declaradas": 0, "resueltas": 0,
                                            "ocurrencias_reconocidas": 0, "fuentes_efectivas": 0}
                                        for f in FUENTES_R2},
            "maximo_corpus": {"flujo": "", "bytes": 0}, "causas_fuera_del_enum": [],
            "hallazgos": errores,
        }
    oraculo = json.loads((raiz / RUTA_ORACULO).read_bytes().decode("utf-8"))
    corpus = json.loads((raiz / RUTA_CORPUS).read_bytes().decode("utf-8"))
    return censo_desde_indices(indices, oraculo, corpus)


def _indices_con_cobertura(indices: Indices, transformar: Callable[[str, str, Cobertura],
                                                                   Cobertura]) -> Indices:
    """Copia los índices aplicando una transformación a cada `Cobertura`. Es el vehículo de los
    mutantes: alteran lo que el parser **resolvió**, sin tocar el disco ni el corpus congelado."""
    flujos = {}
    for flujo, idx in indices.flujos.items():
        flujos[flujo] = idx._replace(
            cobertura={t: transformar(flujo, t, c) for t, c in idx.cobertura.items()})
    return indices._replace(flujos=flujos)


_VACIA = Cobertura("", [], [], "sin_cobertura")


def autotest_control_positivo() -> int:
    """Los **ocho** mutantes de V11b, cada uno con su id y aislado de los demás.

    Son ocho y no cinco: las fuentes de R2 son **tres** y hay que vaciarlas por separado —vaciar
    «alguna» no prueba que el control mire las tres—, y las causas se comparan en **las dos**
    direcciones. Contar cinco dejaría condiciones bloqueantes sin prueba.

    Cada mutante verifica además que el censo falla **por su propia causa** y no por otra: un
    `hallazgos` no vacío solo dice que algo falló, no que falló por lo que el mutante rompió."""
    fallas: list[str] = []
    indices, errores = cargar_instantanea_verificada()
    if indices is None:
        print(f"la instantánea no verifica: {errores[:2]}", file=sys.stderr)
        return 1
    oraculo = json.loads(RUTA_ORACULO.read_bytes().decode("utf-8"))
    corpus = json.loads(RUTA_CORPUS.read_bytes().decode("utf-8"))

    # Control en la dirección positiva, **primero**: sin mutar, el censo tiene que estar limpio. Un
    # control que solo recorre el camino negativo pasaría con un censo que falla siempre — y un
    # control que solo recorre el positivo es exactamente el defecto del `control_positivo` que este
    # archivo reemplazó, que pasaba mientras 213 de 310 tasks salían sin un solo AC.
    base = censo_desde_indices(indices, oraculo, corpus)
    if base["hallazgos"]:
        fallas.append(f"sin mutar, el censo ya trae hallazgos: {base['hallazgos'][:2]}")

    una = next((f, t) for f in sorted(indices.flujos)
               for t, c in sorted(indices.flujos[f].cobertura.items()) if c.ac)

    def _sin_ninguna(_f: str, _t: str, _c: Cobertura) -> Cobertura:
        return _VACIA

    def _sin_fuente(fuente: str) -> Callable[[str, str, Cobertura], Cobertura]:
        return lambda _f, _t, c: _VACIA if c.fuente_efectiva == fuente else c

    def _perdiendo_una(f: str, t: str, c: Cobertura) -> Cobertura:
        return _VACIA if (f, t) == una else c

    def _agregando_espuria(f: str, t: str, c: Cobertura) -> Cobertura:
        if (f, t) != una:
            return c
        # Un AC que **sí existe** en la spec pero que la task no declara: es el parser que
        # *inventa* atribuyendo desde una mención incidental, no uno que pierde.
        libres = sorted(indices.flujos[f].ac_declarados - set(c.ac), key=clave_orden)
        return c._replace(ac=sorted(c.ac + libres[:1], key=clave_orden)) if libres else c

    mutantes: list[tuple[str, str, Indices, dict, str]] = [
        ("M1", "cobertura global vacía", _indices_con_cobertura(indices, _sin_ninguna), oraculo,
         "total global de declaraciones resueltas es CERO"),
    ]
    for n, fuente in zip(("M2", "M3", "M4"), FUENTES_R2):
        mutantes.append((n, f"la fuente `{fuente}` vaciada",
                         _indices_con_cobertura(indices, _sin_fuente(fuente)), oraculo,
                         f"la fuente `{fuente}` de R2 resuelve CERO"))
    mutantes.append(("M5", "una declaración esperada perdida",
                     _indices_con_cobertura(indices, _perdiendo_una), oraculo,
                     "que el parser NO resuelve"))
    mutantes.append(("M6", "una declaración espuria agregada",
                     _indices_con_cobertura(indices, _agregando_espuria), oraculo,
                     "el conjunto esperado no tiene"))

    # M7 y M8 mutan el **esperado**, no el parser: son las dos direcciones de la igualdad de causas.
    con_causa_de_mas = json.loads(json.dumps(oraculo))
    con_causa_de_mas["exclusiones"][0]["causas"] = ["cobertura_en_conflicto"]
    mutantes.append(("M7", "el oráculo declara una causa de cobertura que el clasificador no da",
                     indices, con_causa_de_mas, "faltan ['cobertura_en_conflicto']"))

    excluida = next(e for e in oraculo["exclusiones"]
                    if set(e["causas"]) & CAUSAS_DE_COBERTURA)
    sin_causa = json.loads(json.dumps(oraculo))
    objetivo = next(e for e in sin_causa["exclusiones"]
                    if (e["flujo"], e["task_id"]) == (excluida["flujo"], excluida["task_id"]))
    objetivo["causas"] = ["enfoque_ausente"]  # ninguna del grupo de cobertura
    mutantes.append(("M8", "el oráculo omite una causa de cobertura que el clasificador sí da",
                     indices, sin_causa, "sobran ['sin_cobertura']"))

    for mid, descripcion, idx_mutado, oraculo_mutado, aguja in mutantes:
        salida = censo_desde_indices(idx_mutado, oraculo_mutado, corpus)
        texto = " · ".join(salida["hallazgos"])
        if not salida["hallazgos"]:
            fallas.append(f"{mid} ({descripcion}): el censo quedó LIMPIO — la condición no es "
                          f"bloqueante")
        elif aguja not in texto:
            fallas.append(f"{mid} ({descripcion}): el censo falló, pero no por su causa "
                          f"({aguja!r} no aparece en {texto[:200]!r})")

    for f in fallas:
        print(f"FALLA autotest_control_positivo: {f}", file=sys.stderr)
    return 1 if fallas else 0


# ─── AC-7 — Los tres cortes ─────────────────────────────────────────────────────────────────
#
# Cada uno tapa el agujero del anterior, y ninguno se puede dar por bueno corriéndolo solo sobre el
# desenlace verde conocido. Sin el corte por población los dos primeros **se anulan entre sí**: cada
# flujo excluido por concentración sale de la mediana y sus tasks siguen contando en el denominador
# global, así que el 25 % nunca se alcanza mientras la población real se vacía.

class Cortes(NamedTuple):
    piso: float
    degradados: list[dict]
    incluidos: list[dict]
    retenida: float
    falla: str | None


def aplicar_cortes(censo: dict) -> Cortes:
    """Umbral global de 25 %, corte por flujo con **más** del 50 %, y corte por población al 70 %.

    Los tres comparadores son estrictos donde el AC lo es: exactamente 50 % **no** degrada, y una
    población retenida de exactamente 70 % **pasa**. Bajar el umbral para que una corrida pase es
    lo explícitamente prohibido; subirlo es un acto deliberado, fechado y con su motivo escrito."""
    degradados: list[dict] = []
    incluidos: list[dict] = []
    for f in censo["por_flujo"]:
        totales = f["tasks_totales"]
        tasa_excluidas = (f["excluidas"] / totales) if totales else 1.0
        if not totales or f["elegibles"] == 0:
            # Un flujo sin ninguna task elegible se excluye del cálculo de la mediana y **se
            # nombra**: promediar sobre él sería dividir por cero, y omitirlo callado lo borraría
            # de la población sin dejar rastro.
            degradados.append({"flujo": f["flujo"], "causa": "sin_tasks_elegibles",
                               "tasa": tasa_excluidas})
        elif tasa_excluidas > UMBRAL_FLUJO:
            degradados.append({"flujo": f["flujo"], "causa": "concentracion_de_exclusiones",
                               "tasa": tasa_excluidas})
        else:
            incluidos.append({"flujo": f["flujo"], "causa": "elegible",
                              "tasa": f["tasa_elegibilidad"]})

    total_flujos = len(censo["por_flujo"])
    retenida = (len(incluidos) / total_flujos) if total_flujos else 0.0
    piso = censo["piso"]

    falla = None
    if piso > UMBRAL_PISO:
        falla = (f"el piso de exclusiones es {piso:.1%} y supera el umbral de "
                 f"{UMBRAL_PISO:.0%}: más de una de cada cuatro tasks no resuelve, así que el "
                 f"problema no es el umbral sino el parser o el corpus")
    elif retenida < UMBRAL_POBLACION:
        falla = (f"la población retenida es {retenida:.1%} y queda bajo el "
                 f"{UMBRAL_POBLACION:.0%}: la mediana se publicaría sobre una minoría no "
                 f"representativa")
    return Cortes(piso=piso, degradados=degradados, incluidos=incluidos, retenida=retenida,
                  falla=falla)


class FixtureCorte(NamedTuple):
    id: str
    descripcion: str
    censo: dict
    falla_esperada: bool
    degradados_esperados: tuple[str, ...]


def _censo_sintetico(flujos: list[tuple[str, int, int]], piso: float | None = None) -> dict:
    """`flujos` son ternas `(nombre, tasks_totales, excluidas)`. El piso se deriva salvo que se
    fuerce, para poder poner los fixtures **a ambos lados** del valor exacto."""
    por_flujo = []
    total = excluidas_totales = 0
    for nombre, totales, excluidas in flujos:
        total += totales
        excluidas_totales += excluidas
        elegibles = totales - excluidas
        por_flujo.append({"flujo": nombre, "tasks_totales": totales, "elegibles": elegibles,
                          "excluidas": excluidas,
                          "tasa_elegibilidad": (elegibles / totales) if totales else 0.0,
                          "degradado": bool(totales) and (excluidas / totales) > UMBRAL_FLUJO})
    return {"por_flujo": por_flujo, "denominador_tasks": total,
            "piso": piso if piso is not None else ((excluidas_totales / total) if total else 0.0)}


# Diez flujos sanos como fondo, para que el corte por población no dispare cuando lo que se está
# probando es otro corte. Cada fixture aísla **una** frontera.
_SANOS = [(f"sano-{i}", 10, 0) for i in range(10)]

FIXTURES_CORTES: tuple[FixtureCorte, ...] = (
    FixtureCorte("FC-PISO-01", "piso exactamente en 25 %: NO falla",
                 _censo_sintetico(_SANOS, piso=0.25), False, ()),
    FixtureCorte("FC-PISO-02", "piso apenas por encima de 25 %: falla",
                 _censo_sintetico(_SANOS, piso=0.2501), True, ()),
    # Exclusiones **repartidas**: ningún flujo llega al 50 %, así que el corte por flujo no las
    # toca. Es el modo de fallo que el umbral global cubre y que el corte de al lado no ve.
    FixtureCorte("FC-PISO-03", "26 % repartido: ningún flujo degrada y el global sí falla",
                 _censo_sintetico([(f"repartido-{i}", 100, 26) for i in range(10)]), True, ()),
    FixtureCorte("FC-FLUJO-01", "un flujo con exactamente 50 %: NO degrada",
                 _censo_sintetico(_SANOS + [("mitad", 10, 5)]), False, ()),
    # Degradar **no** es fallar: el flujo sale de la mediana y la medición sigue. Solo el piso y la
    # población hacen fallar. Este fixture nació esperando `falla=True` y lo desmintió: es el único
    # que ejerce `concentracion_de_exclusiones`, porque los tres flujos degradados del corpus real
    # tienen cero elegibles y caen por la otra causa.
    FixtureCorte("FC-FLUJO-02", "un flujo con 50,1 %: degrada, y la medición NO falla por eso",
                 _censo_sintetico(_SANOS + [("pasada", 1000, 501)], piso=0.1), False,
                 ("pasada",)),
    FixtureCorte("FC-FLUJO-03", "un flujo sin ninguna task elegible: degrada y se nombra",
                 _censo_sintetico(_SANOS + [("vacio", 7, 7)], piso=0.1), False, ("vacio",)),
    FixtureCorte("FC-POBLA-01", "población retenida exactamente en 70 %: pasa",
                 _censo_sintetico([(f"ok-{i}", 10, 0) for i in range(7)]
                                  + [(f"malo-{i}", 10, 10) for i in range(3)], piso=0.1),
                 False, tuple(f"malo-{i}" for i in range(3))),
    FixtureCorte("FC-POBLA-02", "población retenida en 69,9 %: falla",
                 _censo_sintetico([(f"ok-{i}", 10, 0) for i in range(699)]
                                  + [(f"malo-{i}", 10, 10) for i in range(301)], piso=0.1),
                 True, ()),
)


def autotest_cortes() -> int:
    """Corre los fixtures de frontera **a ambos lados** de 25 %, 50 % y 70 %, más el flujo sin
    ninguna task elegible, y exige que cada uno ponga su corte en rojo del lado que corresponde.

    Es el callable que la fila V7 invoca. Sin él, V7 solo podría correr el corpus real, que ya se
    sabe verde: un corte que nunca se ejerció del lado rojo no está verificado."""
    fallas: list[str] = []
    for fx in FIXTURES_CORTES:
        cortes = aplicar_cortes(fx.censo)
        if bool(cortes.falla) != fx.falla_esperada:
            fallas.append(f"{fx.id} ({fx.descripcion}): falla={cortes.falla!r}, "
                          f"esperada={fx.falla_esperada}")
        obtenidos = tuple(d["flujo"] for d in cortes.degradados)
        if fx.degradados_esperados and set(obtenidos) != set(fx.degradados_esperados):
            fallas.append(f"{fx.id}: degradados {obtenidos}, esperados "
                          f"{fx.degradados_esperados}")
        for d in cortes.degradados:
            if not d.get("causa") or d.get("tasa") is None:
                fallas.append(f"{fx.id}: un flujo degradado sin causa o sin tasa: {d}")
    for f in fallas:
        print(f"FALLA autotest_cortes: {f}", file=sys.stderr)
    return 1 if fallas else 0


# ─── AC-6 — La medición ─────────────────────────────────────────────────────────────────────
#
# **Se mide solo el contexto de diseño que el dossier reemplaza.** Todo lo idéntico en los dos
# tratamientos —el delta del diff, la lista de archivos, las reglas duras del prompt, el formato del
# reporte— queda fuera del numerador y del denominador. Es lo que hace la medición posible: el
# prompt renderizado *completo* del reviewer incluye el delta, y los flujos archivados no conservan
# baselines ni working trees intermedios. Y es lo que la hace correcta: numerador y denominador
# quedan en la **misma unidad**, bytes UTF-8.
#
# **Lo que se mide es una cota, y se publica como tal.** El prompt de hoy entrega **rutas a archivos
# completos**, y cuánto lea el agente de cada uno no está bajo control del conductor: los flujos
# archivados no conservan ninguna traza de lectura. Afirmar «bytes ingeridos» sería inventar un dato
# que no existe — el mismo error que produjo el número que esta fase reemplaza.

_HEADER = re.compile(rb"\A---\n.*?\n---\n", re.S)


def piezas_de_task(flujo: str, task: Identificador, idx: IndiceDeFlujo) -> list[Pieza]:
    """Las seis piezas de R5 para una task, ya recortadas."""
    tid = str(task)
    tasks_buf, spec_buf, plan_buf = (idx.buffers["tasks.md"], idx.buffers["spec.md"],
                                     idx.buffers["plan.md"])
    piezas: list[Pieza] = []

    rango = idx.task_bloques.get(tid)
    if rango:
        piezas.append(Pieza("task", ("task",), (0,), recortar_pieza(tasks_buf, *rango)))

    cobertura = idx.cobertura.get(tid)
    for ac in (cobertura.ac if cobertura else []):
        if ac in idx.ac_bloques:
            piezas.append(Pieza("ac", ("ac", ac), orden_natural(parsear_id(ac)),
                                recortar_pieza(spec_buf, *idx.ac_bloques[ac])))
    for v in idx.filas_citadas.get(tid, []):
        if v in idx.filas:
            piezas.append(Pieza("filas", ("fila", v), (int(re.sub(r"\D", "", v)), v),
                                recortar_pieza(plan_buf, *idx.filas[v])))

    rango_consume = idx.consume.get(tid)
    if rango_consume is not None:
        texto = tasks_buf[rango_consume[0]:rango_consume[1]].decode("utf-8", "replace")
        citadas, slugs, _ = resolver_consume(texto, idx.tasks, set(idx.produce), idx.bloques,
                                             idx.bloques_duplicados)
        for t in citadas:
            if t in idx.produce:
                piezas.append(Pieza("produce", ("produce", t), orden_natural(parsear_id(t)),
                                    recortar_pieza(tasks_buf, *idx.produce[t])))
        for slug in slugs:
            piezas.append(Pieza("bloques_globales", ("bloque", slug), (slug,),
                                recortar_pieza(tasks_buf, *idx.bloques[slug])))

    if idx.enfoque is not None:
        piezas.append(Pieza("enfoque", ("enfoque",), (0,),
                            recortar_pieza(plan_buf, *idx.enfoque)))
    return piezas


def cota_inferior_de_task(flujo: str, task: Identificador, idx: IndiceDeFlujo) -> int:
    """Las secciones que el prompt de hoy **nombra**: header + `## Enfoque` del plan, los AC de la
    spec, y la task. Es lo que el agente ingiere si lee exactamente lo pedido y nada más.

    «Los AC de la spec» son **todos** los declarados, no solo los que la task cubre: el prompt de
    hoy manda leer la spec y no dice cuáles mirar. Acotarlo a los cubiertos convertiría la cota
    inferior en el dossier mismo y la reducción daría ~1x por construcción."""
    plan_buf, spec_buf, tasks_buf = (idx.buffers["plan.md"], idx.buffers["spec.md"],
                                     idx.buffers["tasks.md"])
    m = _HEADER.match(plan_buf)
    total = len(m.group(0)) if m else 0
    if idx.enfoque is not None:
        total += len(recortar_pieza(plan_buf, *idx.enfoque))
    for rango in idx.ac_bloques.values():
        total += len(recortar_pieza(spec_buf, *rango))
    rango = idx.task_bloques.get(str(task))
    if rango:
        total += len(recortar_pieza(tasks_buf, *rango))
    return total


def _mediana_reduccion(intervalo: list[dict], extremo: str) -> float:
    if not intervalo:
        return 0.0
    return statistics.median([f[f"reduccion_{extremo}"] for f in intervalo])


def medicion_desde_indices(indices: Indices, censo: dict, cortes: Cortes,
                           tamanos: dict[str, int]) -> dict:
    """El intervalo publicado. Consume el conjunto de exclusiones del censo **sin reclasificar**."""
    excluidas = {(e["flujo"], e["task_id"]) for e in censo["tasks_excluidas"]}
    degradados = {d["flujo"] for d in cortes.degradados}

    intervalo_por_flujo: list[dict] = []
    elegibles_totales = 0
    for flujo in sorted(indices.flujos):
        idx = indices.flujos[flujo]
        inferiores: list[int] = []
        dossiers: list[int] = []
        for tid in sorted(idx.tasks, key=clave_orden):
            if (flujo, tid) in excluidas:
                continue
            ident = parsear_id(tid)
            if ident is None:
                continue
            payload = renderizar(piezas_de_task(flujo, ident, idx))
            if not payload:
                continue  # una task cuyo dossier no se renderiza no es elegible
            elegibles_totales += 1
            dossiers.append(len(payload))
            inferiores.append(cota_inferior_de_task(flujo, ident, idx))
        if flujo in degradados or not dossiers:
            continue
        # **Reducción por flujo, con la cota de ESE flujo.** Mezclar el numerador de un flujo con el
        # promedio global de todos produce un cociente sin significado; ya pasó dos veces en la
        # redacción de esta fase.
        cota_inf = round(sum(inferiores) / len(inferiores))
        cota_sup = tamanos.get(flujo, 0)
        denominador = round(sum(dossiers) / len(dossiers))
        intervalo_por_flujo.append({
            "flujo": flujo, "cota_inferior": cota_inf, "cota_superior": cota_sup,
            "denominador": denominador,
            "reduccion_inferior": cota_inf / denominador if denominador else 0.0,
            "reduccion_superior": cota_sup / denominador if denominador else 0.0,
            "tasks": len(dossiers),
        })

    def _mediana(clave: str) -> float:
        return statistics.median([f[clave] for f in intervalo_por_flujo]) \
            if intervalo_por_flujo else 0.0

    # **Mediana ENTRE FLUJOS del intervalo**, nunca entre tasks: la unidad de la publicación es el
    # flujo, y una mediana sin su población es un número sin significado.
    inferior, superior, denom = (round(_mediana("cota_inferior")),
                                 round(_mediana("cota_superior")),
                                 round(_mediana("denominador")))
    # El reviewer recibe **el mismo dossier** que el implementer (el delta del diff queda fuera del
    # numerador y del denominador por R7), y hoy los dos leen los mismos tres artefactos. Por eso
    # sus tres campos coinciden y `par` es la suma exacta de los dos.
    uno = {"cota_inferior": inferior, "cota_superior": superior, "denominador": denom,
           "reduccion_inferior": inferior / denom if denom else 0.0,
           "reduccion_superior": superior / denom if denom else 0.0}
    par = {"cota_inferior": inferior * 2, "cota_superior": superior * 2, "denominador": denom * 2,
           "reduccion_inferior": uno["reduccion_inferior"],
           "reduccion_superior": uno["reduccion_superior"]}

    hallazgos = list(censo["hallazgos"])
    if cortes.falla:
        hallazgos.append(cortes.falla)

    return {
        "poblacion": len(indices.ternas),
        "elegibles": elegibles_totales,
        "flujos_incluidos": cortes.incluidos,
        "flujos_degradados": cortes.degradados,
        "proporcion_retenida": cortes.retenida,
        # El **mismo** hash que emitió el censo: es la identidad observable que distingue «consume
        # el conjunto del censo» de «reclasifica por su cuenta».
        "hash_exclusiones": censo["hash_exclusiones"],
        "cota_inferior": inferior,
        "cota_superior": superior,
        "denominador": denom,
        "mediana_intervalo": {"inferior": _mediana_reduccion(intervalo_por_flujo, "inferior"),
                              "superior": _mediana_reduccion(intervalo_por_flujo, "superior")},
        "por_flujo": censo["por_flujo"],
        "intervalo_por_flujo": intervalo_por_flujo,
        "implementer": uno, "reviewer": dict(uno), "par": par,
        "unidad": "bytes UTF-8",
        "hallazgos": hallazgos,
    }


def ejecutar_medicion(raiz: Path = RAIZ) -> dict:
    indices, errores = cargar_instantanea_verificada(raiz)
    if indices is None:
        vacio = {"cota_inferior": 0, "cota_superior": 0, "denominador": 0,
                 "reduccion_inferior": 0.0, "reduccion_superior": 0.0}
        return {"poblacion": 0, "elegibles": 0, "flujos_incluidos": [], "flujos_degradados": [],
                "proporcion_retenida": 0.0, "hash_exclusiones": "0" * 64, "cota_inferior": 0,
                "cota_superior": 0, "denominador": 0,
                "mediana_intervalo": {"inferior": 0.0, "superior": 0.0}, "por_flujo": [],
                "intervalo_por_flujo": [], "implementer": dict(vacio), "reviewer": dict(vacio),
                "par": dict(vacio), "unidad": "bytes UTF-8", "hallazgos": errores}
    oraculo = json.loads((raiz / RUTA_ORACULO).read_bytes().decode("utf-8"))
    corpus = json.loads((raiz / RUTA_CORPUS).read_bytes().decode("utf-8"))
    censo = censo_desde_indices(indices, oraculo, corpus)
    tamanos = {e["flujo"]: sum(a["tamano"] for a in e["artefactos"]) for e in corpus["flujos"]}
    return medicion_desde_indices(indices, censo, aplicar_cortes(censo), tamanos)


# ─── El corpus sintético de bytes calculables a mano ────────────────────────────────────────
#
# Las piezas se declaran **primero**, como constantes, y los buffers se componen a partir de ellas.
# Así el autotest deriva sus valores esperados con `len()` sobre las mismas constantes, por
# aritmética que no pasa por el código de medición. Un golden capturado de una corrida solo
# verificaría que el resultado no cambió, no que sea el que R7 manda.

_SIN_HEADER = b"---\nid: sintetico\n---\n"
_SIN_AC1 = b"- **AC-1:** el primer criterio, con su Given y su Then."
_SIN_AC2 = b"- **AC-2:** el segundo criterio, tambien con los suyos."
_SIN_ENFOQUE = b"## Enfoque\n\nel enfoque sintetico, en una sola linea."
_SIN_V1 = b"| V1 | AC-1 | test | `comando` | 0 fallos | RED |"
_SIN_PRODUCE = b"  - **Produce:** `def f() -> int`"
_SIN_T1 = (b"- [ ] **T1 - la primera**  \xc2\xb7 cubre: AC-1\n"
           b"  - **Verificar:** V1\n"
           + _SIN_PRODUCE)
_SIN_T2 = (b"- [ ] **T2 - la segunda**  \xc2\xb7 cubre: AC-2\n"
           b"  - **Verificar:** V1\n"
           b"  - **Consume:** la interfaz de T1")

CORPUS_SINTETICO: dict = {
    "spec.md": b"# Spec sintetica\n\n" + _SIN_AC1 + b"\n\n" + _SIN_AC2 + b"\n",
    "plan.md": (_SIN_HEADER + b"\n# Plan sintetico\n\n" + _SIN_ENFOQUE
                + b"\n\n## Verification\n\n| ID | Requisito |\n|---|---|\n" + _SIN_V1 + b"\n"),
    "tasks.md": b"# Tasks sinteticas\n\n" + _SIN_T1 + b"\n\n" + _SIN_T2 + b"\n",
}


def _rotulo(clase: str) -> bytes:
    return dict(ROTULOS)[clase].encode()


def _payload_esperado(piezas: list[tuple[str, bytes]]) -> int:
    """Los bytes que R7 manda, compuestos a mano: por clase, rótulo + `\\n` + sus piezas separadas
    por una línea en blanco; las clases separadas entre sí por una línea en blanco; un `\\n` final."""
    bloques = []
    for clase, _ in ROTULOS:
        cuerpo = [t for c, t in piezas if c == clase]
        if cuerpo:
            bloques.append(_rotulo(clase) + b"\n" + b"\n\n".join(cuerpo))
    return len(b"\n\n".join(bloques) + b"\n")


def autotest_medicion() -> int:
    """Los valores **exactos** sobre el corpus sintético, y los invariantes recomputados aparte
    sobre el corpus real. Es el callable que la fila V6 invoca."""
    fallas: list[str] = []
    idx = _indexar_flujo(dict(CORPUS_SINTETICO))
    indices = Indices(flujos={"sintetico": idx},
                      ternas=[("sintetico", "T1", 1), ("sintetico", "T2", 1)])

    # Las piezas que el parser debería haber cortado, comparadas contra las constantes de origen.
    # Si esto falla, cualquier número posterior mide otra cosa.
    cortes_esperados = {
        "task T1": (recortar_pieza(idx.buffers["tasks.md"], *idx.task_bloques["T1"]), _SIN_T1),
        "task T2": (recortar_pieza(idx.buffers["tasks.md"], *idx.task_bloques["T2"]), _SIN_T2),
        "AC-1": (recortar_pieza(idx.buffers["spec.md"], *idx.ac_bloques["AC-1"]), _SIN_AC1),
        "AC-2": (recortar_pieza(idx.buffers["spec.md"], *idx.ac_bloques["AC-2"]), _SIN_AC2),
        "fila V1": (recortar_pieza(idx.buffers["plan.md"], *idx.filas["V1"]), _SIN_V1),
        "enfoque": (recortar_pieza(idx.buffers["plan.md"], *idx.enfoque), _SIN_ENFOQUE),
        "Produce de T1": (recortar_pieza(idx.buffers["tasks.md"], *idx.produce["T1"]),
                          _SIN_PRODUCE),
    }
    for que, (obtenido, esperado) in cortes_esperados.items():
        if obtenido != esperado:
            fallas.append(f"el corte de {que} dio {obtenido!r} y no {esperado!r}")

    d1 = _payload_esperado([("task", _SIN_T1), ("ac", _SIN_AC1), ("filas", _SIN_V1),
                            ("enfoque", _SIN_ENFOQUE)])
    d2 = _payload_esperado([("task", _SIN_T2), ("ac", _SIN_AC2), ("filas", _SIN_V1),
                            ("produce", _SIN_PRODUCE), ("enfoque", _SIN_ENFOQUE)])
    # La cota inferior lleva **todos** los AC de la spec, no solo el que la task cubre.
    ac_todos = len(_SIN_AC1) + len(_SIN_AC2)
    ci1 = len(_SIN_HEADER) + len(_SIN_ENFOQUE) + ac_todos + len(_SIN_T1)
    ci2 = len(_SIN_HEADER) + len(_SIN_ENFOQUE) + ac_todos + len(_SIN_T2)
    cota_sup = sum(len(b) for b in CORPUS_SINTETICO.values())

    censo = {"tasks_excluidas": [], "hash_exclusiones": "s" * 64, "hallazgos": [],
             "piso": 0.0, "denominador_tasks": 2,
             "por_flujo": [{"flujo": "sintetico", "tasks_totales": 2, "elegibles": 2,
                            "excluidas": 0, "tasa_elegibilidad": 1.0, "degradado": False}]}
    salida = medicion_desde_indices(indices, censo, aplicar_cortes(censo),
                                    {"sintetico": cota_sup})

    esperados = {
        "elegibles": 2,
        "denominador": round((d1 + d2) / 2),
        "cota_inferior": round((ci1 + ci2) / 2),
        "cota_superior": cota_sup,
    }
    for campo, esperado in esperados.items():
        if salida[campo] != esperado:
            fallas.append(f"{campo}: obtenido {salida[campo]}, esperado {esperado}")

    # Promedio por flujo, intervalo y mediana — con un solo flujo, la mediana ES su valor.
    flujo = salida["intervalo_por_flujo"][0] if salida["intervalo_por_flujo"] else {}
    if flujo.get("reduccion_superior") != cota_sup / round((d1 + d2) / 2):
        fallas.append(f"la reducción superior del flujo dio {flujo.get('reduccion_superior')} y no "
                      f"{cota_sup / round((d1 + d2) / 2)}")
    if salida["mediana_intervalo"]["superior"] != flujo.get("reduccion_superior"):
        fallas.append("con un solo flujo, la mediana entre flujos no coincide con ese flujo")
    for campo in ("cota_inferior", "cota_superior", "denominador"):
        if salida["par"][campo] != salida["implementer"][campo] + salida["reviewer"][campo]:
            fallas.append(f"par.{campo} no es implementer + reviewer")

    # Invariantes recomputados **aparte** sobre el corpus real.
    real = ejecutar_medicion()
    if real["cota_inferior"] > real["cota_superior"]:
        fallas.append(f"corpus real: cota_inferior {real['cota_inferior']} > cota_superior "
                      f"{real['cota_superior']}")
    for campo in ("cota_inferior", "cota_superior", "denominador"):
        if real["par"][campo] != real["implementer"][campo] + real["reviewer"][campo]:
            fallas.append(f"corpus real: par.{campo} no es implementer + reviewer")
    for f in real["intervalo_por_flujo"]:
        if f["cota_inferior"] > f["cota_superior"]:
            fallas.append(f"{f['flujo']}: cota_inferior > cota_superior")
        if f["reduccion_superior"] != f["cota_superior"] / f["denominador"]:
            fallas.append(f"{f['flujo']}: la reducción no usa la cota de ESE flujo")
    # La mediana es **entre flujos**, no entre tasks: recomputada aparte desde `intervalo_por_flujo`.
    if real["intervalo_por_flujo"]:
        entre_flujos = statistics.median([f["reduccion_superior"]
                                          for f in real["intervalo_por_flujo"]])
        if real["mediana_intervalo"]["superior"] != entre_flujos:
            fallas.append("la mediana publicada no es la mediana entre flujos")

    for f in fallas:
        print(f"FALLA autotest_medicion: {f}", file=sys.stderr)
    return 1 if fallas else 0


# ─── Autotests que necesitan el CLI o los dos modos ya construidos ──────────────────────────

def autotest_esquemas_rechazan() -> int:
    """El esquema embebido rechaza lo que debe rechazar, y sus `required` salen de la tabla de AC-8.

    Un esquema que valide **solo su propia implementación** es autorreferencial y pasa siempre: por
    eso los `required` se comparan contra `REQUIRED_NORMATIVOS`, transcrito de la tabla del AC, y no
    contra la salida que producen los modos."""
    fallas: list[str] = []
    salidas = {"censo": (ejecutar_censo(), SCHEMA_CENSO),
               "fixtures": (ejecutar_fixtures(), SCHEMA_FIXTURES),
               "medir-historico": (ejecutar_medicion(), SCHEMA_MEDICION)}

    for modo, (_, schema) in salidas.items():
        declarados = set(schema["required"])
        esperados = set(REQUIRED_NORMATIVOS[modo]) | set(REQUIRED_PROPIOS[modo])
        if declarados != esperados:
            fallas.append(f"{modo}: los `required` del esquema {sorted(declarados)} no coinciden "
                          f"con la tabla normativa de AC-8 más los campos propios "
                          f"{sorted(esperados)}")

    for modo, (salida, schema) in salidas.items():
        if validar(salida, schema):
            fallas.append(f"{modo}: la salida real no valida contra su propio esquema")
            continue
        # (1) quitar cada campo obligatorio
        for campo in schema["required"]:
            mutante = {k: v for k, v in salida.items() if k != campo}
            if not validar(mutante, schema):
                fallas.append(f"{modo}: el esquema aceptó una salida SIN `{campo}`")
        # (2) cambiar el tipo de cada elemento anidado
        for campo, sub in schema["properties"].items():
            if campo not in salida:
                continue
            mutante = dict(salida)
            if sub.get("type") == "array" and salida[campo]:
                elemento = salida[campo][0]
                if isinstance(elemento, dict) and elemento:
                    roto = dict(elemento)
                    roto[sorted(roto)[0]] = ["tipo", "equivocado"]
                    mutante[campo] = [roto] + salida[campo][1:]
                else:
                    mutante[campo] = [{"tipo": "equivocado"}]
            elif sub.get("type") == "object" and isinstance(salida[campo], dict):
                mutante[campo] = {k: "cadena donde iba un objeto" for k in salida[campo]}
            elif sub.get("type") == "integer":
                mutante[campo] = "no es un entero"
            elif sub.get("type") == "number":
                mutante[campo] = "no es un número"
            elif sub.get("type") == "string":
                mutante[campo] = 12345
            else:
                continue
            if not validar(mutante, schema):
                fallas.append(f"{modo}: el esquema aceptó `{campo}` con el tipo cambiado")
        # (3) agregar una propiedad no declarada
        if not validar({**salida, "propiedad_no_declarada": 1}, schema):
            fallas.append(f"{modo}: el esquema aceptó una propiedad no declarada")

    for f in fallas:
        print(f"FALLA autotest_esquemas_rechazan: {f}", file=sys.stderr)
    return 1 if fallas else 0


def autotest_sellos_modos() -> int:
    """Los **cuatro cruces** de AC-3: discrepancia (hash · tamaño) × modo histórico
    (`censo` · `medir-historico`), corridos a través del CLI real.

    Vive acá porque es el primer punto del orden de construcción donde los dos modos y el CLI ya
    existen: `autotest_sellos_seam` prueba la función, y esto prueba que **ningún modo** continúa
    con advertencia."""
    fallas: list[str] = []
    previo = os.getcwd()
    for modo_discrepancia in ("hash", "tamano"):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            _copiar_arbol_minimo(raiz)
            flujo, artefacto = _alterar(raiz, modo_discrepancia)
            try:
                os.chdir(raiz)
                for subcomando in ("censo", "medir-historico"):
                    salida, traza = io.StringIO(), io.StringIO()
                    with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(traza):
                        codigo = main([subcomando])
                    etiqueta = f"{subcomando} con discrepancia de {modo_discrepancia}"
                    if codigo == 0:
                        fallas.append(f"{etiqueta}: exit 0 — el modo continuó con el corpus movido")
                    texto = traza.getvalue() + salida.getvalue()
                    for que, aguja in (("el flujo", flujo), ("el artefacto", artefacto)):
                        if aguja not in texto:
                            fallas.append(f"{etiqueta}: la salida no nombra {que} ({aguja!r})")
            finally:
                os.chdir(previo)
    for f in fallas:
        print(f"FALLA autotest_sellos_modos: {f}", file=sys.stderr)
    return 1 if fallas else 0


# ════════════════════════════════════════════════════════════════════════════════════════════
# CAPA 4 — CLI
# ════════════════════════════════════════════════════════════════════════════════════════════
#
# La **única** capa que imprime y que decide el código de salida. `stdout` lleva exactamente un
# objeto JSON por invocación; todo diagnóstico humano va a `stderr`.

def _emitir(resultado: dict, schema: dict, modo: str) -> int:
    """Valida el resultado contra su esquema **antes** de serializarlo, lo imprime y decide el
    código de salida. Sin la validación previa, la ausencia de un campo obligatorio se publicaría
    en silencio y el gate no podría fallar por ausencia."""
    errores = validar(resultado, schema)
    if errores:
        for e in errores[:10]:
            print(f"ERROR el resultado de `{modo}` no satisface su esquema: {e}", file=sys.stderr)
        return EXIT_HALLAZGOS
    print(json.dumps(resultado, ensure_ascii=False, indent=2, sort_keys=True))
    hallazgos = resultado.get("hallazgos") or resultado.get("divergencias") or []
    mismatch = resultado.get("hash_mismatch") or []
    for h in hallazgos:
        print(f"HALLAZGO {h if isinstance(h, str) else json.dumps(h, ensure_ascii=False)}",
              file=sys.stderr)
    for h in mismatch:
        print(f"SELLO {json.dumps(h, ensure_ascii=False)}", file=sys.stderr)
    return EXIT_HALLAZGOS if (hallazgos or mismatch) else EXIT_OK


def _handler_censo() -> int:
    return _emitir(ejecutar_censo(), SCHEMA_CENSO, "censo")


def _handler_fixtures() -> int:
    resultado = ejecutar_fixtures()
    # La traza de los vectores propios va a **stderr**: en verde `divergencias[]` está vacío por
    # contrato, así que ahí serían invisibles y el modo podría no correr ninguno sin que se note.
    print(f"vectores propios del arnés ({resultado['vectores_propios_ok']}/"
          f"{resultado['vectores_propios_totales']}):", file=sys.stderr)
    for v in correr_vectores():
        print(f"  {v['id']:10} {'ok   ' if v['ok'] else 'FALLA'} {v['descripcion']}"
              + (f" — {v['detalle']}" if not v["ok"] else ""), file=sys.stderr)
    return _emitir(resultado, SCHEMA_FIXTURES, "fixtures")


def _handler_medicion() -> int:
    return _emitir(ejecutar_medicion(), SCHEMA_MEDICION, "medir-historico")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="medir-dossier-de-task.py",
        description="Arnés de extracción del dossier: censo, fixtures y medición histórica.")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("censo", help="compara el corpus contra el manifest y clasifica las exclusiones")
    sub.add_parser("fixtures", help="corre el manifest congelado y los vectores propios")
    sub.add_parser("medir-historico", help="publica el intervalo de reducción")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # Una invocación inválida —sin subcomando o con uno desconocido— devuelve **2**, no 1: el
        # script anterior daba 1 con un `FileNotFoundError` y no distinguía «me invocaste mal» de
        # «encontré hallazgos».
        return EXIT_INVOCACION
    return {"censo": _handler_censo, "fixtures": _handler_fixtures,
            "medir-historico": _handler_medicion}[args.comando]()


if __name__ == "__main__":
    sys.exit(main())
