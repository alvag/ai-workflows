#!/usr/bin/env python3
"""Instrumento de medición del baseline de la fase 0.

Seis modos por ahora: los demás del catálogo los construyen otras tasks.

- `--validar-schemas` — valida los cinco contratos de datos de la fase contra el meta-contrato del
  repo: versionados, cerrados en todos sus niveles, sin `$ref` que no resuelva, sin definición
  inalcanzable y sin ninguna palabra clave que el validador de este archivo no implemente.
- `--autotest-schemas` — control positivo y negativo del modo anterior sobre el corpus sintético de
  `scripts/fixtures-baseline/schemas/`, comparado en las dos direcciones contra su manifest
  independiente, más los mutantes que prueban que `--validar-schemas` puede ponerse rojo.
- `--vocabulario-metricas` — enumera el vocabulario cerrado de `scripts/metricas-fase-0.json` y lo
  comprueba en seis controles: las cinco categorías obligatorias contra su manifest independiente,
  la unidad y la agregación de cada métrica, la integridad referencial, la tasa de degradación y la
  ejecutabilidad de cada fórmula, que el instrumento RESUELVE en vez de interpretar.
- `--autotest-vocabulario` — control positivo y negativo del modo anterior sobre el corpus de
  `scripts/fixtures-baseline/vocabulario/`, más los mutantes que prueban que puede ponerse rojo.
  Con `--tasa` se acota a la tasa de degradación.
- `--canonicalizar` — emite los bytes canónicos de un pre-registro y su SHA-256. La proyección
  excluye explícitamente el campo del hash, que es el punto fijo de la decisión heredada 15. Con
  `--solo-bytes` escribe la proyección cruda a stdout, para que el hash lo pueda recomputar
  `shasum` y no haga falta creerle a este archivo.
- `--autotest-canonicalizacion` — prueba que la proyección es completa y que el campo del hash está
  fuera de ella, sobre el corpus de `scripts/fixtures-baseline/canonicalizacion/` y contra un
  fixture de punteros normativos **externo al schema**.

## Cómo se agrega un modo (normativo — dieciséis tasks escriben este mismo archivo)

Cada task **agrega** su modo y no reescribe nada de lo que ya está. El despacho es una tabla:

1. Escribí la función `modo_<nombre>(args) -> int` en una sección propia al final del archivo,
   antes del bloque de registro.
2. Registrala con `registrar_modo(...)`, declarando su bandera, su ayuda, su handler y —si lleva
   valor— su `Argumento`, más las `Auxiliares` que la acompañen (`--combinados`, `--base`, …).
3. No toques `main()`: construye el parser y el despacho desde `MODOS`, así que un modo nuevo entra
   sin editar ninguna función existente. El mensaje de invocación inválida también se deriva de la
   tabla: no hay ninguna lista de banderas escrita a mano que pueda quedar desactualizada.

Códigos de salida, iguales en todos los modos: **0** sano, **1** hallazgos, **2** invocación
inválida.

## Por qué el validador es propio

No hay `jsonschema` en el entorno y el repo no toma dependencias externas: solo stdlib. El
validador de acá implementa un subconjunto de JSON Schema 2020-12 y **rechaza toda palabra clave
que no implemente**. Ignorar una en silencio deja escrita en el schema una restricción que nadie
aplica, que es peor que no haberla escrito. Es el mismo criterio —y el mismo subconjunto— de
`scripts/verificar-matriz-despachos.py`; el código está portado y no importado a propósito, para
que ese archivo pueda cambiar sin arrastrar a este.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unicodedata
import urllib.request
from pathlib import Path
from typing import Any, Callable, NamedTuple

RAIZ = Path(__file__).resolve().parent.parent
DIR_SCRIPTS = RAIZ / "scripts"
DIR_FIXTURES = DIR_SCRIPTS / "fixtures-baseline" / "schemas"
RUTA_MANIFEST_FIXTURES = DIR_FIXTURES / "manifest.json"


# ---------------------------------------------------------------------------------------------
# Los cinco contratos de datos de la fase. Es la lista congelada: el corpus de fixtures se compara
# contra ella en las dos direcciones, así que un contrato nuevo sin fixtures no pasa desapercibido
# y un fixture de un contrato que no existe tampoco.
# ---------------------------------------------------------------------------------------------

class Contrato(NamedTuple):
    nombre: str
    ruta: Path
    que_es: str


CONTRATOS: tuple[Contrato, ...] = (
    Contrato("observacion", DIR_SCRIPTS / "observacion.schema.json",
             "la observación derivada de un bundle"),
    Contrato("preregistro", DIR_SCRIPTS / "preregistro.schema.json",
             "el pre-registro congelado de la cohorte"),
    Contrato("bundle-corrida", DIR_SCRIPTS / "bundle-corrida.schema.json",
             "el bundle de evidencia de una corrida"),
    Contrato("recibo-frontera",
             DIR_SCRIPTS / "recibos-frontera-fase-0" / "recibo-frontera.schema.json",
             "el recibo de frontera del adaptador de sesión"),
    Contrato("journal-anomalias",
             DIR_SCRIPTS / "journal-anomalias-fase-0" / "journal-anomalias.schema.json",
             "el journal de anomalías del runner"),
)

CONTRATOS_POR_NOMBRE = {c.nombre: c for c in CONTRATOS}


# ---------------------------------------------------------------------------------------------
# Validador. Subconjunto de JSON Schema 2020-12: lo que estos schemas usan y nada más. Toda
# palabra clave fuera de `PALABRAS_SOPORTADAS` es un error del schema, no una anotación inocua.
# ---------------------------------------------------------------------------------------------

PALABRAS_SOPORTADAS = frozenset({
    "$ref", "type", "enum", "const", "pattern", "minLength", "minimum", "maximum",
    "minItems", "maxItems", "uniqueItems", "properties", "required", "additionalProperties",
    "items", "oneOf", "allOf", "if", "then", "else",
})
PALABRAS_IGNORADAS = frozenset({"$schema", "$id", "title", "description", "$defs", "$comment"})

Ruta = tuple


class Error(NamedTuple):
    ruta: Ruta
    mensaje: str

    def __str__(self) -> str:
        return f"{fmt(self.ruta)}: {self.mensaje}"


def fmt(ruta: Ruta) -> str:
    salida = "$"
    for tramo in ruta:
        salida += f"[{tramo}]" if isinstance(tramo, int) else f".{tramo}"
    return salida


def _mismo(a: Any, b: Any) -> bool:
    """Igualdad con el tipo incluido: en Python `False == 0` y `True == 1`, y un enum de cadenas
    no debe aceptar un booleano por accidente."""
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return a == b


def _nombre_tipo(valor: Any) -> str:
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


def _tipo_ok(valor: Any, tipo: str) -> bool:
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


def _resolver(schema: dict, ref: str) -> dict:
    if not ref.startswith("#/$defs/"):
        raise ValueError(f"referencia no local o no soportada: {ref}")
    nombre = ref[len("#/$defs/"):]
    defs = schema.get("$defs", {})
    if nombre not in defs:
        raise ValueError(f"referencia a un `$defs` inexistente: {ref}")
    return defs[nombre]


def validar(instancia: Any, schema: dict) -> list[Error]:
    """Valida `instancia` contra `schema`, que es el schema raíz."""
    return _validar(instancia, schema, schema, ())


def _validar(valor: Any, esquema: dict, schema: dict, ruta: Ruta) -> list[Error]:
    errores: list[Error] = []

    if "$ref" in esquema:
        errores.extend(_validar(valor, _resolver(schema, esquema["$ref"]), schema, ruta))

    if "oneOf" in esquema:
        exitosas = 0
        fallidas: list[tuple[bool, int, list[Error]]] = []
        for rama in esquema["oneOf"]:
            errs = _validar(valor, rama, schema, ruta)
            if errs:
                fallidas.append((_fallo_de_discriminador(errs, rama, schema, ruta), len(errs), errs))
            else:
                exitosas += 1
        if exitosas == 0:
            # Se reporta una sola rama, y cuál no lo decide el conteo de errores —eso atribuye mal
            # en cuanto dos ramas fallan con uno cada una— sino el discriminador: una rama que
            # falló en su propia constante no es la variante que se quiso escribir.
            errores.extend(min(fallidas, key=lambda f: (f[0], f[1]))[2])
        elif exitosas > 1:
            errores.append(Error(ruta, "más de una variante del `oneOf` valida este nodo: "
                                       "la unión no está discriminada"))

    for sub in esquema.get("allOf", []):
        errores.extend(_validar(valor, sub, schema, ruta))

    if "if" in esquema:
        condicion = _validar(valor, esquema["if"], schema, ruta)
        rama = esquema.get("then") if not condicion else esquema.get("else")
        if rama is not None:
            errores.extend(_validar(valor, rama, schema, ruta))

    tipo = esquema.get("type")
    if tipo is not None and not _tipo_ok(valor, tipo):
        errores.append(Error(ruta, f"se esperaba tipo `{tipo}` y llegó `{_nombre_tipo(valor)}`"))
        return errores  # sin el tipo correcto, el resto de las restricciones no significa nada

    if "enum" in esquema and not any(_mismo(valor, v) for v in esquema["enum"]):
        errores.append(Error(ruta, f"valor fuera del vocabulario cerrado: {valor!r} no está "
                                   f"en {esquema['enum']}"))
    if "const" in esquema and not _mismo(valor, esquema["const"]):
        errores.append(Error(ruta, f"se esperaba la constante {esquema['const']!r} "
                                   f"y llegó {valor!r}"))

    if isinstance(valor, str):
        if "minLength" in esquema and len(valor) < esquema["minLength"]:
            errores.append(Error(ruta, f"cadena más corta que `minLength` ({esquema['minLength']})"))
        if "pattern" in esquema and re.search(esquema["pattern"], valor) is None:
            errores.append(Error(ruta, f"la cadena {valor!r} no casa con el patrón "
                                       f"{esquema['pattern']!r}"))

    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        if "minimum" in esquema and valor < esquema["minimum"]:
            errores.append(Error(ruta, f"valor menor que `minimum` ({esquema['minimum']})"))
        if "maximum" in esquema and valor > esquema["maximum"]:
            errores.append(Error(ruta, f"valor mayor que `maximum` ({esquema['maximum']})"))

    if isinstance(valor, list):
        if "minItems" in esquema and len(valor) < esquema["minItems"]:
            errores.append(Error(ruta, f"el arreglo tiene {len(valor)} elementos y `minItems` "
                                       f"es {esquema['minItems']}"))
        if "maxItems" in esquema and len(valor) > esquema["maxItems"]:
            errores.append(Error(ruta, f"el arreglo tiene {len(valor)} elementos y `maxItems` "
                                       f"es {esquema['maxItems']}"))
        if esquema.get("uniqueItems") and _hay_repetidos(valor):
            errores.append(Error(ruta, "el arreglo declara `uniqueItems` y tiene elementos repetidos"))
        if "items" in esquema:
            for i, elemento in enumerate(valor):
                errores.extend(_validar(elemento, esquema["items"], schema, ruta + (i,)))

    if isinstance(valor, dict):
        propiedades = esquema.get("properties", {})
        for campo in esquema.get("required", []):
            if campo not in valor:
                errores.append(Error(ruta + (campo,), f"falta el campo obligatorio `{campo}`"))
        cerrado = esquema.get("additionalProperties", True) is False
        for clave, sub in valor.items():
            if clave in propiedades:
                errores.extend(_validar(sub, propiedades[clave], schema, ruta + (clave,)))
            elif cerrado:
                errores.append(Error(ruta + (clave,),
                                     f"propiedad no declarada `{clave}` en un objeto cerrado"))

    return errores


def _fallo_de_discriminador(errores: list[Error], rama: dict, schema: dict, ruta: Ruta) -> bool:
    """True si la rama falló en una de sus propias constantes: entonces no es la variante que se
    quiso escribir, y sus errores no explican nada del nodo que llegó."""
    objetivo = _resolver(schema, rama["$ref"]) if "$ref" in rama else rama
    claves = {c for c, sub in objetivo.get("properties", {}).items() if "const" in sub}
    return any(e.ruta in {ruta + (c,) for c in claves} for e in errores)


# ---------------------------------------------------------------------------------------------
# Meta-contrato del schema. Lo que un contrato de esta fase tiene que cumplir para poder aplicarse.
# ---------------------------------------------------------------------------------------------

class SubEsquema(NamedTuple):
    definicion: str
    puntero: tuple
    esquema: dict
    en_condicion: bool  # True dentro de un `if`: ahí `properties` es una pregunta, no una forma


def _recorrer(nombre: str, esquema: dict, puntero: tuple) -> list[SubEsquema]:
    salida: list[SubEsquema] = []

    def caminar(sub: Any, punt: tuple, en_condicion: bool) -> None:
        if not isinstance(sub, dict):
            return
        salida.append(SubEsquema(nombre, punt, sub, en_condicion))
        for clave, hijo in (sub.get("properties") or {}).items():
            caminar(hijo, punt + ("properties", clave), en_condicion)
        if "items" in sub:
            caminar(sub["items"], punt + ("items",), en_condicion)
        for i, rama in enumerate(sub.get("oneOf") or []):
            caminar(rama, punt + ("oneOf", i), en_condicion)
        for i, rama in enumerate(sub.get("allOf") or []):
            caminar(rama, punt + ("allOf", i), en_condicion)
        if "if" in sub:
            caminar(sub["if"], punt + ("if",), True)
        for clave in ("then", "else"):
            if clave in sub:
                caminar(sub[clave], punt + (clave,), en_condicion)

    caminar(esquema, puntero, False)
    return salida


def _todos_los_subesquemas(schema: dict) -> list[SubEsquema]:
    salida = _recorrer("raiz", {k: v for k, v in schema.items() if k != "$defs"}, ())
    for nombre, definicion in (schema.get("$defs") or {}).items():
        salida.extend(_recorrer(nombre, definicion, ("$defs", nombre)))
    return salida


def _puntero(puntero: tuple) -> str:
    return "#/" + "/".join(str(t) for t in puntero) if puntero else "#"


def verificar_schema(schema: dict) -> list[str]:
    """Los problemas del schema consigo mismo. Lista vacía es un schema aplicable."""
    problemas: list[str] = []

    version = schema.get("x-version")
    declarada = schema.get("properties", {}).get("version_schema", {}).get("const")
    if not version:
        problemas.append("el schema no declara `x-version`: un schema sin versión no es versionado")
    elif version != declarada:
        problemas.append(
            f"`x-version` ({version!r}) no coincide con la constante `version_schema` que la "
            f"instancia debe declarar ({declarada!r})"
        )

    if schema.get("type") != "object" or schema.get("additionalProperties", True) is not False:
        problemas.append("la raíz del schema no es un objeto cerrado")

    definiciones = set(schema.get("$defs") or {})
    referenciadas: set[str] = set()
    for sub in _todos_los_subesquemas(schema):
        for clave in sub.esquema:
            if (clave not in PALABRAS_SOPORTADAS and clave not in PALABRAS_IGNORADAS
                    and not clave.startswith("x-")):
                problemas.append(f"{_puntero(sub.puntero)}: palabra clave `{clave}` que el "
                                 "validador no implementa")
        ref = sub.esquema.get("$ref")
        if ref:
            if not ref.startswith("#/$defs/") or ref[len("#/$defs/"):] not in definiciones:
                problemas.append(f"{_puntero(sub.puntero)}: `$ref` que no resuelve: {ref}")
            else:
                referenciadas.add(ref[len("#/$defs/"):])
        if sub.en_condicion:
            continue  # dentro de un `if` no se declara una forma, se hace una pregunta
        if sub.esquema.get("type") == "object":
            if sub.esquema.get("additionalProperties", True) is not False:
                problemas.append(f"{_puntero(sub.puntero)}: objeto sin `additionalProperties: "
                                 "false` — el schema deja de ser cerrado ahí")
        elif "properties" in sub.esquema:
            problemas.append(f"{_puntero(sub.puntero)}: declara `properties` sin `type: object`, "
                             "así que su cierre no se aplica a nada")

    for muerta in sorted(definiciones - referenciadas):
        problemas.append(f"`$defs/{muerta}` no la referencia nadie: una definición inalcanzable "
                         "no se puede ejercer ni mutar")

    return problemas


def _cargar_json(ruta: Path) -> tuple[Any, str | None]:
    try:
        return json.loads(ruta.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"no existe: {ruta}"
    except json.JSONDecodeError as exc:
        return None, f"JSON inválido en {ruta}: {exc}"


# ---------------------------------------------------------------------------------------------
# Registro de modos. La tabla desde la que `main()` construye el parser y el despacho.
# ---------------------------------------------------------------------------------------------

class Argumento(NamedTuple):
    """El valor que acompaña a la bandera del modo. `const` es lo que vale si se omite."""
    metavar: str
    const: str | None = None


class Auxiliar(NamedTuple):
    """Una bandera que modifica a un modo (`--combinados`, `--base`…), nunca lo selecciona."""
    bandera: str
    ayuda: str
    metavar: str | None = None
    por_defecto: str | None = None


class Modo(NamedTuple):
    bandera: str
    ayuda: str
    handler: Callable[[argparse.Namespace], int]
    argumento: Argumento | None = None
    auxiliares: tuple[Auxiliar, ...] = ()

    @property
    def destino(self) -> str:
        return self.bandera[2:].replace("-", "_")


MODOS: list[Modo] = []


def registrar_modo(bandera: str, ayuda: str, handler: Callable[[argparse.Namespace], int],
                   argumento: Argumento | None = None,
                   auxiliares: tuple[Auxiliar, ...] = ()) -> None:
    """Da de alta un modo. Es el único punto de contacto con el CLI: nadie edita `main()`."""
    if any(m.bandera == bandera for m in MODOS):
        raise ValueError(f"el modo {bandera} ya está registrado")
    MODOS.append(Modo(bandera, ayuda, handler, argumento, auxiliares))


# ---------------------------------------------------------------------------------------------
# Modo `--validar-schemas`.
# ---------------------------------------------------------------------------------------------

def modo_validar_schemas(args: argparse.Namespace) -> int:
    del args
    fallas = 0
    for contrato in CONTRATOS:
        schema, error = _cargar_json(contrato.ruta)
        if error:
            print(f"FALLA  {contrato.nombre}: {error}")
            fallas += 1
            continue
        problemas = verificar_schema(schema)
        if problemas:
            print(f"FALLA  {contrato.nombre} — {len(problemas)} problemas:")
            for p in problemas:
                print(f"       - {p}")
            fallas += 1
            continue
        cerrados = sum(1 for s in _todos_los_subesquemas(schema)
                       if s.esquema.get("type") == "object")
        print(f"OK     {contrato.nombre} v{schema['x-version']} — {contrato.que_es}: "
              f"{len(schema.get('$defs') or {})} definiciones, {cerrados} objetos cerrados")

    print()
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {len(CONTRATOS)} contratos con problemas")
        return 1
    print(f"RESULTADO: OK — los {len(CONTRATOS)} contratos son aplicables")
    return 0


# ---------------------------------------------------------------------------------------------
# Modo `--autotest-schemas`.
#
# Cinco controles, y ninguno reemplaza a otro. El corpus NO se valida contra sí mismo (D-16): el
# manifest declara aparte qué fixtures tienen que existir y se compara con el directorio en las dos
# direcciones, así que borrar un negativo pone el modo rojo en vez de reducir el conjunto validado.
# ---------------------------------------------------------------------------------------------

class Mutante(NamedTuple):
    nombre: str
    que_rompe: str
    aplicar: Callable[[dict], bool]


def _quitar_cierre(schema: dict) -> bool:
    for definicion in (schema.get("$defs") or {}).values():
        if definicion.get("type") == "object":
            definicion.pop("additionalProperties", None)
            return True
    return False


def _agregar_palabra_no_implementada(schema: dict) -> bool:
    for definicion in (schema.get("$defs") or {}).values():
        if definicion.get("type") == "object":
            definicion["multipleOf"] = 2
            return True
    return False


def _romper_referencia(schema: dict) -> bool:
    for definicion in (schema.get("$defs") or {}).values():
        for sub in (definicion.get("properties") or {}).values():
            if "$ref" in sub:
                sub["$ref"] = "#/$defs/definicion_que_no_existe"
                return True
    return False


def _dejar_definicion_muerta(schema: dict) -> bool:
    (schema.setdefault("$defs", {}))["definicion_inalcanzable"] = {
        "type": "object", "additionalProperties": False, "properties": {},
    }
    return True


def _desalinear_version(schema: dict) -> bool:
    schema["x-version"] = "9.9.9"
    return True


MUTANTES_DE_META_CONTRATO: tuple[Mutante, ...] = (
    Mutante("cierre-quitado", "un objeto sin `additionalProperties: false`", _quitar_cierre),
    Mutante("palabra-no-implementada", "una palabra clave que el validador no aplica",
            _agregar_palabra_no_implementada),
    Mutante("ref-rota", "un `$ref` que no resuelve", _romper_referencia),
    Mutante("definicion-muerta", "una definición que nadie referencia", _dejar_definicion_muerta),
    Mutante("version-desalineada", "`x-version` distinta de la constante de la instancia",
            _desalinear_version),
)


def _leer_corpus() -> tuple[dict, list[str]]:
    manifest, error = _cargar_json(RUTA_MANIFEST_FIXTURES)
    if error:
        return {}, [f"manifest de fixtures: {error}"]
    return manifest, []


def _fixtures_en_disco() -> set[str]:
    encontrados: set[str] = set()
    for sub in ("conformes", "negativos"):
        directorio = DIR_FIXTURES / sub
        if not directorio.is_dir():
            continue
        for archivo in directorio.glob("*.json"):
            encontrados.add(f"{sub}/{archivo.name}")
    return encontrados


def modo_autotest_schemas(args: argparse.Namespace) -> int:
    del args
    manifest, problemas = _leer_corpus()
    if problemas:
        for p in problemas:
            print(f"[A] FALLA  {p}")
        return 1

    resultados: list[tuple[str, bool, str]] = []
    esperados_conformes = manifest.get("conformes") or []
    esperados_negativos = manifest.get("negativos") or []

    # [A] El manifest y el directorio, en las dos direcciones. Un negativo borrado del disco tiene
    # que poner esto rojo; un fixture agregado sin declararlo, también.
    declarados = {e["fixture"] for e in esperados_conformes + esperados_negativos}
    en_disco = _fixtures_en_disco()
    diferencias = [f"declarado y ausente del disco: {f}" for f in sorted(declarados - en_disco)]
    diferencias += [f"en disco y no declarado: {f}" for f in sorted(en_disco - declarados)]
    resultados.append((
        "A", not diferencias,
        f"manifest ↔ directorio ({len(declarados)} fixtures)" if not diferencias
        else f"{len(diferencias)} divergencias: " + " | ".join(diferencias[:6]),
    ))

    # [B] Cada contrato tiene al menos un conforme y un negativo, comparado contra la lista
    # congelada de contratos y no contra los que el corpus resulte cubrir.
    faltantes: list[str] = []
    for contrato in CONTRATOS:
        if not any(e["contrato"] == contrato.nombre for e in esperados_conformes):
            faltantes.append(f"{contrato.nombre}: sin fixture conforme")
        if not any(e["contrato"] == contrato.nombre for e in esperados_negativos):
            faltantes.append(f"{contrato.nombre}: sin fixture negativo")
    desconocidos = sorted({e["contrato"] for e in esperados_conformes + esperados_negativos}
                          - set(CONTRATOS_POR_NOMBRE))
    faltantes += [f"contrato inexistente en el manifest: {c}" for c in desconocidos]
    resultados.append((
        "B", not faltantes,
        f"cobertura de los {len(CONTRATOS)} contratos" if not faltantes
        else " | ".join(faltantes[:6]),
    ))

    schemas: dict[str, dict] = {}
    for contrato in CONTRATOS:
        datos, error = _cargar_json(contrato.ruta)
        if error:
            print(f"[C] FALLA  {contrato.nombre}: {error}")
            return 1
        schemas[contrato.nombre] = datos

    # [C] Los conformes validan limpio. Es el control positivo: sin él, un negativo que falla por
    # una razón estructural compartida parecería estar probando su cláusula.
    fallas_positivas: list[str] = []
    for entrada in esperados_conformes:
        instancia, error = _cargar_json(DIR_FIXTURES / entrada["fixture"])
        if error:
            fallas_positivas.append(f"{entrada['fixture']}: {error}")
            continue
        errores = validar(instancia, schemas[entrada["contrato"]])
        if errores:
            fallas_positivas.append(f"{entrada['fixture']}: {len(errores)} errores — {errores[0]}")
    resultados.append((
        "C", not fallas_positivas,
        f"{len(esperados_conformes)} fixtures conformes validan limpio" if not fallas_positivas
        else " | ".join(fallas_positivas[:4]),
    ))

    # [D] Cada negativo falla, y falla por SU cláusula: se exige un error en la ruta declarada y
    # con el motivo declarado. Un negativo que falla en otro lado deja su cláusula sin probar.
    fallas_negativas: list[str] = []
    for entrada in esperados_negativos:
        instancia, error = _cargar_json(DIR_FIXTURES / entrada["fixture"])
        if error:
            fallas_negativas.append(f"{entrada['fixture']}: {error}")
            continue
        errores = validar(instancia, schemas[entrada["contrato"]])
        if not errores:
            fallas_negativas.append(f"{entrada['fixture']}: valida y no debería")
            continue
        ruta = entrada["ruta_esperada"]
        motivo = entrada["motivo_esperado"]
        if not any(fmt(e.ruta) == ruta and motivo in e.mensaje for e in errores):
            fallas_negativas.append(
                f"{entrada['fixture']}: falla, pero no en {ruta} por «{motivo}» — "
                f"lo que se vio: {errores[0]}"
            )
    resultados.append((
        "D", not fallas_negativas,
        f"{len(esperados_negativos)} fixtures negativos fallan por su cláusula"
        if not fallas_negativas else " | ".join(fallas_negativas[:4]),
    ))

    # [E] `--validar-schemas` puede ponerse rojo. Sobre una COPIA en memoria de cada contrato real
    # —mutar el archivo del árbol dejaría el repo mutado si el proceso muere—, cada mutante tiene
    # que ser detectado; y sin mutar, cero problemas.
    fallas_de_mutacion: list[str] = []
    for contrato in CONTRATOS:
        if verificar_schema(copy.deepcopy(schemas[contrato.nombre])):
            fallas_de_mutacion.append(f"{contrato.nombre}: el schema sin mutar ya reporta problemas")
            continue
        for mutante in MUTANTES_DE_META_CONTRATO:
            copia = copy.deepcopy(schemas[contrato.nombre])
            if not mutante.aplicar(copia):
                fallas_de_mutacion.append(
                    f"{contrato.nombre}/{mutante.nombre}: la mutación no se pudo aplicar, "
                    "así que este contrato queda sin ese control"
                )
                continue
            if not verificar_schema(copia):
                fallas_de_mutacion.append(
                    f"{contrato.nombre}/{mutante.nombre}: {mutante.que_rompe} pasa sin detectarse"
                )
    total_mutantes = len(CONTRATOS) * len(MUTANTES_DE_META_CONTRATO)
    resultados.append((
        "E", not fallas_de_mutacion,
        f"{total_mutantes} mutantes del meta-contrato detectados" if not fallas_de_mutacion
        else " | ".join(fallas_de_mutacion[:4]),
    ))

    for etiqueta, ok, detalle in resultados:
        print(f"[{etiqueta}] {'OK    ' if ok else 'FALLA '} {detalle}")
    print()
    rojos = [e for e, ok, _ in resultados if not ok]
    if rojos:
        print(f"RESULTADO: FALLA — controles en rojo: {', '.join(rojos)}")
        return 1
    print(f"RESULTADO: OK — {len(resultados)} controles en verde")
    return 0


# ---------------------------------------------------------------------------------------------
# Modos `--vocabulario-metricas` y `--autotest-vocabulario`.
#
# El vocabulario de `scripts/metricas-fase-0.json` es cerrado y EJECUTABLE: cada fórmula la resuelve
# un resolvedor de acá abajo y cada métrica lleva las comprobaciones que lo demuestran corriendo.
# Una fórmula descrita en prosa la interpreta una persona, y dos personas la interpretan distinto.
#
# Ningún conjunto se comprueba contra sí mismo (D-16). Las categorías obligatorias viven en un
# manifest independiente y congelado —`scripts/fixtures-baseline/vocabulario/manifest.json`— y se
# comparan en las DOS direcciones contra el vocabulario y contra el enum `enum_categoria_de_metrica`
# del schema de pre-registro de T1, que es una tercera pata que nadie escribió para esta fila.
# ---------------------------------------------------------------------------------------------

RUTA_VOCABULARIO = DIR_SCRIPTS / "metricas-fase-0.json"
DIR_FIXTURES_VOCABULARIO = DIR_SCRIPTS / "fixtures-baseline" / "vocabulario"
RUTA_MANIFEST_VOCABULARIO = DIR_FIXTURES_VOCABULARIO / "manifest.json"

VERSION_VOCABULARIO = "1.0.0"

CLAVES_DEL_VOCABULARIO = frozenset({
    "version_vocabulario", "descripcion", "unidades", "predicados", "formulas", "agregaciones",
    "categorias",
})

SEDES = frozenset({"corrida", "trabajo_delegado"})
PUBLICACIONES = frozenset({"escalar", "tasa"})
TIPOS_DE_PARAMETRO = frozenset({"predicado", "tipo_de_evento", "campo_de_hecho", "entero_positivo"})

# De dónde sale el vocabulario de campos y valores de cada clase de hecho. El vocabulario no puede
# nombrar un campo que la evidencia no lleva: se comprueba contra los schemas de T1, no contra una
# lista transcrita acá que envejecería en silencio.
FUENTES_DE_HECHO: dict[str, tuple[str, str]] = {
    "evento": ("bundle-corrida", "evento"),
    "recurso": ("bundle-corrida", "recurso"),
    "intento": ("observacion", "estado_derivado"),
}

TOLERANCIA = 1e-9


def _casi_igual(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCIA * max(1.0, abs(b))


def _predicado_satisface(predicado: dict, hecho: dict) -> bool:
    valor = hecho.get(predicado.get("campo"))
    return any(_mismo(valor, admitido) for admitido in predicado.get("valores") or [])


# --- Resolvedores de fórmula. Cada `forma` del vocabulario es una de estas funciones. ---
# Firma: (entradas, hechos, predicados) -> (valor, error). Un error no es un cero: una métrica que
# no se pudo calcular se publica sin valor y con su adjudicación escrita (AC-21).

def _forma_diferencia_de_sellos(entradas: dict, hechos: list, predicados: dict):
    del predicados
    sellos: dict[str, int] = {}
    for extremo in ("evento_inicial", "evento_final"):
        tipo = entradas.get(extremo)
        coincidencias = [h for h in hechos if h.get("tipo") == tipo]
        if len(coincidencias) != 1:
            return None, (f"no hay exactamente un evento «{tipo}»: hay {len(coincidencias)}")
        valor_ns = (coincidencias[0].get("sello") or {}).get("valor_ns")
        if not isinstance(valor_ns, int) or isinstance(valor_ns, bool):
            return None, f"el evento «{tipo}» no lleva un `sello.valor_ns` entero"
        sellos[extremo] = valor_ns
    if sellos["evento_final"] < sellos["evento_inicial"]:
        return None, "sellos no monotonicos: el evento final es anterior al inicial"
    divisor = entradas.get("divisor_a_unidad")
    if not isinstance(divisor, int) or isinstance(divisor, bool) or divisor <= 0:
        return None, "el divisor a la unidad no es un entero positivo"
    return (sellos["evento_final"] - sellos["evento_inicial"]) / divisor, None


def _forma_conteo_de_hechos(entradas: dict, hechos: list, predicados: dict):
    predicado = predicados.get(entradas.get("predicado"))
    if predicado is None:
        return None, f"predicado inexistente: «{entradas.get('predicado')}»"
    return float(sum(1 for h in hechos if _predicado_satisface(predicado, h))), None


def _forma_conteo_de_hechos_distintos(entradas: dict, hechos: list, predicados: dict):
    predicado = predicados.get(entradas.get("predicado"))
    if predicado is None:
        return None, f"predicado inexistente: «{entradas.get('predicado')}»"
    clave = entradas.get("clave")
    vistos: set[str] = set()
    for hecho in hechos:
        if not _predicado_satisface(predicado, hecho):
            continue
        if clave not in hecho:
            return None, f"un hecho satisface «{predicado['predicado_id']}» y no lleva «{clave}»"
        vistos.add(json.dumps(hecho[clave], sort_keys=True, ensure_ascii=False))
    return float(len(vistos)), None


def _forma_cociente_de_hechos(entradas: dict, hechos: list, predicados: dict):
    numerador = predicados.get(entradas.get("predicado_numerador"))
    denominador = predicados.get(entradas.get("predicado_denominador"))
    if numerador is None or denominador is None:
        return None, "predicado inexistente en el numerador o en el denominador"
    elegibles = [h for h in hechos if _predicado_satisface(denominador, h)]
    if not elegibles:
        return None, ("sin poblacion elegible: la metrica queda sin observaciones, "
                      "nunca en cero")
    arriba = sum(1 for h in elegibles if _predicado_satisface(numerador, h))
    return arriba / len(elegibles), None


def _forma_conjuncion_de_predicados(entradas: dict, hechos: list, predicados: dict):
    predicado = predicados.get(entradas.get("predicado"))
    if predicado is None:
        return None, f"predicado inexistente: «{entradas.get('predicado')}»"
    if not hechos:
        return None, "sin hechos que evaluar: una conjuncion vacia no es un 1"
    return (1.0 if all(_predicado_satisface(predicado, h) for h in hechos) else 0.0), None


RESOLVEDORES_DE_FORMA: dict[str, Callable[[dict, list, dict], tuple]] = {
    "diferencia_de_sellos": _forma_diferencia_de_sellos,
    "conteo_de_hechos": _forma_conteo_de_hechos,
    "conteo_de_hechos_distintos": _forma_conteo_de_hechos_distintos,
    "cociente_de_hechos": _forma_cociente_de_hechos,
    "conjuncion_de_predicados": _forma_conjuncion_de_predicados,
}


# --- Resolvedores de agregación. La regla de agregación también se ejecuta: declararla como texto
# la deja a interpretación de quien publique el número. ---

def _numeros(valores: list) -> tuple[list, str | None]:
    for valor in valores:
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return [], "un valor no numerico no se agrega"
    return list(valores), None


def _agregacion_mediana(valores: list):
    numeros, error = _numeros(valores)
    if error:
        return None, error
    if not numeros:
        return None, "sin valores que agregar"
    ordenados = sorted(numeros)
    medio = len(ordenados) // 2
    if len(ordenados) % 2:
        return float(ordenados[medio]), None
    return (ordenados[medio - 1] + ordenados[medio]) / 2, None


def _agregacion_suma(valores: list):
    numeros, error = _numeros(valores)
    if error:
        return None, error
    if not numeros:
        return None, "sin valores que agregar"
    return float(sum(numeros)), None


def _agregacion_conjuncion(valores: list):
    numeros, error = _numeros(valores)
    if error:
        return None, error
    if not numeros:
        return None, "sin valores que agregar"
    return (1.0 if all(n == 1 for n in numeros) else 0.0), None


def _agregacion_cociente_de_sumas(valores: list):
    if not valores:
        return None, "sin valores que agregar"
    arriba = 0.0
    abajo = 0.0
    for par in valores:
        if not isinstance(par, list) or len(par) != 2:
            return None, "cada valor tiene que ser un par [numerador, denominador]"
        numeros, error = _numeros(par)
        if error:
            return None, error
        arriba += numeros[0]
        abajo += numeros[1]
    if abajo == 0:
        return None, "sin poblacion elegible: no hay tasa que publicar"
    return arriba / abajo, None


RESOLVEDORES_DE_AGREGACION: dict[str, Callable[[list], tuple]] = {
    "mediana": _agregacion_mediana,
    "suma": _agregacion_suma,
    "conjuncion": _agregacion_conjuncion,
    "cociente_de_sumas": _agregacion_cociente_de_sumas,
}


# --- La revisión del vocabulario: seis controles, y ninguno reemplaza a otro. ---

CONTROLES_DEL_VOCABULARIO: tuple[tuple[str, str], ...] = (
    ("A", "las cinco categorías obligatorias, en las dos direcciones contra el manifest y el schema"),
    ("B", "estructura del vocabulario y de cada métrica"),
    ("C", "integridad referencial de fórmulas, agregaciones, unidades, predicados y entradas"),
    ("D", "la degradación se publica como tasa, con su conteo absoluto al lado"),
    ("E", "ejecutabilidad: cada fórmula y cada agregación se resuelven y dan lo declarado"),
    ("F", "catálogo de fórmulas: manifest ↔ vocabulario ↔ resolvedores implementados"),
)


def _metricas_del(vocabulario: dict):
    for categoria in vocabulario.get("categorias") or []:
        for metrica in categoria.get("metricas") or []:
            yield categoria, metrica


def _por_id(entradas: list, clave: str) -> dict:
    return {e.get(clave): e for e in entradas or [] if isinstance(e, dict)}


def _enum_del_campo(schema: dict, contenedor: str, campo: str) -> tuple[list | None, str | None]:
    """Enum admitido por `campo` dentro de `contenedor`, leído del schema de T1. `None, None` es un
    campo que existe y no está acotado por enum."""
    definicion = (schema.get("$defs") or {}).get(contenedor) or {}
    propiedades = definicion.get("properties") or {}
    if campo not in propiedades:
        return None, "no existe en el schema"
    esquema = propiedades[campo]
    if "$ref" in esquema:
        try:
            esquema = _resolver(schema, esquema["$ref"])
        except ValueError as exc:
            return None, str(exc)
    return esquema.get("enum"), None


def revisar_vocabulario(vocabulario: dict, manifest: dict,
                        schemas: dict[str, dict]) -> dict[str, list[str]]:
    """Corre los seis controles y devuelve los mensajes de cada uno. Sin mensajes es verde."""
    fallas: dict[str, list[str]] = {etiqueta: [] for etiqueta, _ in CONTROLES_DEL_VOCABULARIO}

    formulas = _por_id(vocabulario.get("formulas"), "formula_id")
    predicados = _por_id(vocabulario.get("predicados"), "predicado_id")
    agregaciones = _por_id(vocabulario.get("agregaciones"), "agregacion_id")
    unidades = _por_id(vocabulario.get("unidades"), "unidad_id")

    # ---------------- [A] categorías obligatorias, en las dos direcciones ----------------
    obligatorias = manifest.get("categorias_obligatorias") or []
    del_manifest = [c.get("categoria") for c in obligatorias]
    del_vocabulario = [c.get("categoria") for c in vocabulario.get("categorias") or []]
    enum_del_schema = ((schemas["preregistro"].get("$defs") or {})
                       .get("enum_categoria_de_metrica") or {}).get("enum") or []

    for categoria in del_manifest:
        if categoria not in del_vocabulario:
            fallas["A"].append(f"declarada en el manifest y ausente del vocabulario: {categoria}")
    for categoria in del_vocabulario:
        if categoria not in del_manifest:
            fallas["A"].append(f"en el vocabulario y no declarada en el manifest: {categoria}")
    for categoria in del_manifest:
        if categoria not in enum_del_schema:
            fallas["A"].append(
                f"declarada en el manifest y ausente de `enum_categoria_de_metrica`: {categoria}")
    for categoria in enum_del_schema:
        if categoria not in del_manifest:
            fallas["A"].append(
                f"en `enum_categoria_de_metrica` y no declarada en el manifest: {categoria}")
    if _hay_repetidos(del_vocabulario):
        fallas["A"].append("el vocabulario declara una categoría dos veces")

    for esperada in obligatorias:
        nombre = esperada.get("categoria")
        presentes = [c for c in vocabulario.get("categorias") or []
                     if c.get("categoria") == nombre]
        if not presentes:
            continue
        minimo = esperada.get("minimo_de_metricas", 1)
        cuantas = len(presentes[0].get("metricas") or [])
        if cuantas < minimo:
            fallas["A"].append(
                f"la categoría «{nombre}» declara {cuantas} métricas y el manifest exige {minimo}")

    # ---------------- [B] estructura ----------------
    if vocabulario.get("version_vocabulario") != VERSION_VOCABULARIO:
        fallas["B"].append(
            f"`version_vocabulario` es {vocabulario.get('version_vocabulario')!r} y el instrumento "
            f"implementa {VERSION_VOCABULARIO!r}")
    for clave in CLAVES_DEL_VOCABULARIO:
        if clave not in vocabulario:
            fallas["B"].append(f"el vocabulario no declara `{clave}`")
    for clave in vocabulario:
        if clave not in CLAVES_DEL_VOCABULARIO and not clave.startswith("x-"):
            fallas["B"].append(f"clave de primer nivel no declarada: `{clave}`")

    identidades: list[str] = []
    for _, metrica in _metricas_del(vocabulario):
        nombre = metrica.get("metrica_id")
        identidades.append(nombre)
        etiqueta = f"la métrica «{nombre}»"
        if not nombre:
            fallas["B"].append("hay una métrica sin `metrica_id`")
        if "agregacion" not in metrica:
            fallas["B"].append(f"{etiqueta} está sin regla de agregación")
        if "unidad" not in metrica:
            fallas["B"].append(f"{etiqueta} no declara unidad")
        admitidas = metrica.get("formulas_admitidas")
        if not isinstance(admitidas, list) or not admitidas:
            fallas["B"].append(f"{etiqueta} no admite ninguna fórmula")
        elif _hay_repetidos(admitidas):
            fallas["B"].append(f"{etiqueta} repite una fórmula admitida")
        if metrica.get("sede") not in SEDES:
            fallas["B"].append(f"{etiqueta} no declara una sede admitida")
        if metrica.get("publicacion") not in PUBLICACIONES:
            fallas["B"].append(f"{etiqueta} no declara una forma de publicación admitida")
        if not isinstance(metrica.get("entradas"), dict):
            fallas["B"].append(f"{etiqueta} no ata las entradas de su fórmula")
        if not metrica.get("comprobaciones"):
            fallas["B"].append(f"{etiqueta} no lleva ninguna comprobación")
    if _hay_repetidos(identidades):
        fallas["B"].append("hay dos métricas con la misma identidad")
    for coleccion, clave in ((vocabulario.get("formulas"), "formula_id"),
                             (vocabulario.get("predicados"), "predicado_id"),
                             (vocabulario.get("agregaciones"), "agregacion_id"),
                             (vocabulario.get("unidades"), "unidad_id")):
        valores = [e.get(clave) for e in coleccion or [] if isinstance(e, dict)]
        if _hay_repetidos(valores):
            fallas["B"].append(f"hay dos entradas con el mismo `{clave}`")

    # ---------------- [C] integridad referencial ----------------
    for predicado in vocabulario.get("predicados") or []:
        nombre = predicado.get("predicado_id")
        clase = predicado.get("clase_de_hecho")
        if clase not in FUENTES_DE_HECHO:
            fallas["C"].append(f"el predicado «{nombre}» declara una clase de hecho inexistente: "
                               f"{clase}")
            continue
        contrato, contenedor = FUENTES_DE_HECHO[clase]
        admitidos, error = _enum_del_campo(schemas[contrato], contenedor, predicado.get("campo"))
        if error:
            fallas["C"].append(
                f"el predicado «{nombre}» mira el campo «{predicado.get('campo')}», que {error} "
                f"de {contrato} ({contenedor})")
            continue
        if admitidos is not None:
            for valor in predicado.get("valores") or []:
                if valor not in admitidos:
                    fallas["C"].append(
                        f"el predicado «{nombre}» admite «{valor}», que no está en el enum de "
                        f"«{predicado.get('campo')}» de {contrato}")
        if not predicado.get("valores"):
            fallas["C"].append(f"el predicado «{nombre}» no admite ningún valor")

    enum_tipo_de_evento = ((schemas["bundle-corrida"].get("$defs") or {})
                           .get("enum_tipo_de_evento") or {}).get("enum") or []

    for _, metrica in _metricas_del(vocabulario):
        nombre = metrica.get("metrica_id")
        etiqueta = f"la métrica «{nombre}»"
        if "unidad" in metrica and metrica["unidad"] not in unidades:
            fallas["C"].append(f"{etiqueta} publica en una unidad inexistente: "
                               f"«{metrica['unidad']}»")
        if "agregacion" in metrica and metrica["agregacion"] not in agregaciones:
            fallas["C"].append(f"{etiqueta} agrega con una regla inexistente: "
                               f"«{metrica['agregacion']}»")

        entradas = metrica.get("entradas") if isinstance(metrica.get("entradas"), dict) else {}
        admitidas_reales: list[dict] = []
        for formula_id in metrica.get("formulas_admitidas") or []:
            formula = formulas.get(formula_id)
            if formula is None:
                fallas["C"].append(f"{etiqueta} declara una fórmula admitida inexistente: "
                                   f"«{formula_id}»")
                continue
            admitidas_reales.append(formula)

        parametros: dict[str, dict] = {}
        for formula in admitidas_reales:
            for parametro in formula.get("parametros") or []:
                previo = parametros.get(parametro.get("nombre"))
                if previo is not None and previo.get("tipo") != parametro.get("tipo"):
                    fallas["C"].append(
                        f"{etiqueta} admite dos fórmulas que exigen «{parametro.get('nombre')}» con "
                        f"tipos distintos")
                parametros[parametro.get("nombre")] = parametro
                if parametro.get("nombre") not in entradas:
                    fallas["C"].append(
                        f"{etiqueta} no ata «{parametro.get('nombre')}», que «"
                        f"{formula.get('formula_id')}» exige")
        for clave in entradas:
            if clave not in parametros:
                fallas["C"].append(f"{etiqueta} ata «{clave}», que ninguna fórmula admitida exige")

        clases = {f.get("clase_de_hecho") for f in admitidas_reales}
        for clave, valor in entradas.items():
            parametro = parametros.get(clave)
            if parametro is None:
                continue
            tipo = parametro.get("tipo")
            if tipo not in TIPOS_DE_PARAMETRO:
                fallas["C"].append(f"{etiqueta} usa un parámetro de tipo desconocido: «{tipo}»")
            elif tipo == "predicado":
                predicado = predicados.get(valor)
                if predicado is None:
                    fallas["C"].append(f"{etiqueta} referencia un predicado inexistente: «{valor}»")
                elif predicado.get("clase_de_hecho") not in clases:
                    fallas["C"].append(
                        f"{etiqueta} usa el predicado «{valor}», que mira hechos de clase "
                        f"«{predicado.get('clase_de_hecho')}» y no {sorted(clases)}")
            elif tipo == "tipo_de_evento" and valor not in enum_tipo_de_evento:
                fallas["C"].append(f"{etiqueta} nombra un tipo de evento inexistente: «{valor}»")
            elif tipo == "campo_de_hecho":
                for clase in clases:
                    if clase not in FUENTES_DE_HECHO:
                        continue
                    contrato, contenedor = FUENTES_DE_HECHO[clase]
                    _, error = _enum_del_campo(schemas[contrato], contenedor, valor)
                    if error:
                        fallas["C"].append(
                            f"{etiqueta} usa el campo «{valor}», que {error} de {contrato} "
                            f"({contenedor})")
            elif tipo == "entero_positivo":
                if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
                    fallas["C"].append(f"{etiqueta} ata «{clave}» con algo que no es un entero "
                                       f"positivo")

        for comprobacion in metrica.get("comprobaciones") or []:
            if comprobacion.get("formula_id") not in (metrica.get("formulas_admitidas") or []):
                fallas["C"].append(
                    f"{etiqueta} tiene una comprobación de «{comprobacion.get('formula_id')}», que "
                    f"no está entre sus fórmulas admitidas")

    # ---------------- [D] la degradación se publica como tasa ----------------
    for esperada in obligatorias:
        nombre = esperada.get("categoria")
        presentes = [c for c in vocabulario.get("categorias") or [] if c.get("categoria") == nombre]
        if not presentes:
            continue
        metricas = presentes[0].get("metricas") or []
        if esperada.get("exige_tasa"):
            tasas = [m for m in metricas if m.get("publicacion") == "tasa"]
            if not tasas:
                fallas["D"].append(
                    f"la categoría «{nombre}» quedó sin ninguna métrica publicada como tasa: un "
                    f"conteo absoluto no responde con qué frecuencia degrada el ecosistema")
        if esperada.get("exige_conteo_absoluto"):
            conteos = [m for m in metricas
                       if m.get("publicacion") == "escalar"
                       and all((formulas.get(f) or {}).get("forma") == "conteo_de_hechos"
                               for f in m.get("formulas_admitidas") or [None])]
            if not conteos:
                fallas["D"].append(
                    f"la categoría «{nombre}» quedó sin el conteo absoluto que permite auditar la "
                    f"tasa")

    for _, metrica in _metricas_del(vocabulario):
        if metrica.get("publicacion") != "tasa":
            continue
        etiqueta = f"la métrica «{metrica.get('metrica_id')}»"
        for campo in ("numerador", "denominador", "regla_de_elegibilidad"):
            if not (metrica.get(campo) or "").strip():
                fallas["D"].append(f"{etiqueta} se publica como tasa sin declarar su {campo}")
        for formula_id in metrica.get("formulas_admitidas") or []:
            formula = formulas.get(formula_id)
            if formula is not None and formula.get("forma") != "cociente_de_hechos":
                fallas["D"].append(
                    f"{etiqueta} se publica como tasa y admite «{formula_id}», que no es un cociente")

    # ---------------- [E] ejecutabilidad ----------------
    # Se evalúan las fórmulas admitidas que EXISTEN en el catálogo y tienen resolvedor: las que no,
    # ya las condenaron [C] y [F], y volver a nombrarlas acá haría ruido sin agregar señal.
    for _, metrica in _metricas_del(vocabulario):
        nombre = metrica.get("metrica_id")
        etiqueta = f"la métrica «{nombre}»"
        entradas = metrica.get("entradas") if isinstance(metrica.get("entradas"), dict) else {}
        comprobaciones = metrica.get("comprobaciones") or []
        for formula_id in metrica.get("formulas_admitidas") or []:
            formula = formulas.get(formula_id)
            if formula is None or formula.get("forma") not in RESOLVEDORES_DE_FORMA:
                continue
            propias = [c for c in comprobaciones if c.get("formula_id") == formula_id]
            if not propias:
                fallas["E"].append(
                    f"el par ({nombre}, {formula_id}) no lleva comprobación: la fórmula queda "
                    f"declarada y no resuelta")
            resolvedor = RESOLVEDORES_DE_FORMA[formula["forma"]]
            for comprobacion in propias:
                valor, error = resolvedor(entradas, comprobacion.get("hechos") or [], predicados)
                esperado = comprobacion.get("resultado_esperado")
                error_esperado = comprobacion.get("error_esperado")
                que = comprobacion.get("que_prueba", "")
                if esperado is None and error_esperado is None:
                    fallas["E"].append(
                        f"{etiqueta} tiene una comprobación de «{formula_id}» sin resultado ni error "
                        f"esperado")
                elif error_esperado is not None:
                    if error is None:
                        fallas["E"].append(
                            f"{etiqueta}/«{formula_id}» ({que}): se esperaba el error "
                            f"«{error_esperado}» y resolvió {valor}")
                    elif error_esperado not in error:
                        fallas["E"].append(
                            f"{etiqueta}/«{formula_id}» ({que}): se esperaba el error "
                            f"«{error_esperado}» y falló por «{error}»")
                elif error is not None:
                    fallas["E"].append(
                        f"{etiqueta}/«{formula_id}» ({que}): se esperaba {esperado} y falló por "
                        f"«{error}»")
                elif not _casi_igual(valor, float(esperado)):
                    fallas["E"].append(
                        f"{etiqueta}/«{formula_id}» ({que}): se esperaba {esperado} y resolvió "
                        f"{valor}")

    for agregacion in vocabulario.get("agregaciones") or []:
        nombre = agregacion.get("agregacion_id")
        forma = agregacion.get("forma")
        if forma not in RESOLVEDORES_DE_AGREGACION:
            fallas["E"].append(f"la agregación «{nombre}» declara la forma «{forma}», que el "
                               f"instrumento no resuelve")
            continue
        comprobaciones = agregacion.get("comprobaciones") or []
        if not comprobaciones:
            fallas["E"].append(f"la agregación «{nombre}» no lleva ninguna comprobación")
        resolvedor = RESOLVEDORES_DE_AGREGACION[forma]
        for comprobacion in comprobaciones:
            valor, error = resolvedor(comprobacion.get("valores") or [])
            esperado = comprobacion.get("resultado_esperado")
            error_esperado = comprobacion.get("error_esperado")
            que = comprobacion.get("que_prueba", "")
            if esperado is None and error_esperado is None:
                fallas["E"].append(f"la agregación «{nombre}» tiene una comprobación sin resultado "
                                   f"ni error esperado")
            elif error_esperado is not None:
                if error is None:
                    fallas["E"].append(f"la agregación «{nombre}» ({que}): se esperaba el error "
                                       f"«{error_esperado}» y resolvió {valor}")
                elif error_esperado not in error:
                    fallas["E"].append(f"la agregación «{nombre}» ({que}): se esperaba el error "
                                       f"«{error_esperado}» y falló por «{error}»")
            elif error is not None:
                fallas["E"].append(f"la agregación «{nombre}» ({que}): se esperaba {esperado} y "
                                   f"falló por «{error}»")
            elif not _casi_igual(valor, float(esperado)):
                fallas["E"].append(f"la agregación «{nombre}» ({que}): se esperaba {esperado} y "
                                   f"resolvió {valor}")

    # ---------------- [F] catálogo de fórmulas, en las dos direcciones ----------------
    esperadas = _por_id(manifest.get("formulas_esperadas"), "formula_id")
    for formula_id, esperada in esperadas.items():
        if formula_id not in formulas:
            fallas["F"].append(f"declarada en el manifest y ausente del catálogo: {formula_id}")
        elif formulas[formula_id].get("forma") != esperada.get("forma"):
            fallas["F"].append(
                f"«{formula_id}» resuelve con la forma «{formulas[formula_id].get('forma')}» y el "
                f"manifest congeló «{esperada.get('forma')}»")
    for formula_id in formulas:
        if formula_id not in esperadas:
            fallas["F"].append(f"en el catálogo y no declarada en el manifest: {formula_id}")
    formas_del_manifest = {e.get("forma") for e in esperadas.values()}
    for forma in sorted(formas_del_manifest):
        if forma not in RESOLVEDORES_DE_FORMA:
            fallas["F"].append(f"el manifest congela la forma «{forma}» y el instrumento no la "
                               f"resuelve")
    for forma in sorted(RESOLVEDORES_DE_FORMA):
        if forma not in formas_del_manifest:
            fallas["F"].append(f"el instrumento resuelve la forma «{forma}» y ninguna fórmula "
                               f"congelada la usa")
    for formula in vocabulario.get("formulas") or []:
        if formula.get("forma") not in RESOLVEDORES_DE_FORMA:
            fallas["F"].append(
                f"la fórmula «{formula.get('formula_id')}» declara la forma "
                f"«{formula.get('forma')}», que el instrumento no resuelve")
        if formula.get("clase_de_hecho") not in FUENTES_DE_HECHO:
            fallas["F"].append(
                f"la fórmula «{formula.get('formula_id')}» consume hechos de una clase inexistente: "
                f"«{formula.get('clase_de_hecho')}»")

    return fallas


def _cargar_schemas_de_t1() -> tuple[dict, list[str]]:
    schemas: dict[str, dict] = {}
    problemas: list[str] = []
    for nombre in ("preregistro", "observacion", "bundle-corrida"):
        datos, error = _cargar_json(CONTRATOS_POR_NOMBRE[nombre].ruta)
        if error:
            problemas.append(f"schema {nombre}: {error}")
        else:
            schemas[nombre] = datos
    return schemas, problemas


def _cargar_entorno_del_vocabulario() -> tuple[dict, dict, dict, list[str]]:
    vocabulario, error_v = _cargar_json(RUTA_VOCABULARIO)
    manifest, error_m = _cargar_json(RUTA_MANIFEST_VOCABULARIO)
    schemas, problemas = _cargar_schemas_de_t1()
    if error_v:
        problemas.append(f"vocabulario: {error_v}")
    if error_m:
        problemas.append(f"manifest del vocabulario: {error_m}")
    return vocabulario or {}, manifest or {}, schemas, problemas


def modo_vocabulario_metricas(args: argparse.Namespace) -> int:
    del args
    vocabulario, manifest, schemas, problemas = _cargar_entorno_del_vocabulario()
    if problemas:
        for problema in problemas:
            print(f"FALLA  {problema}")
        return 1

    for categoria in vocabulario.get("categorias") or []:
        print(f"CATEGORÍA {categoria.get('categoria')}")
        for metrica in categoria.get("metricas") or []:
            admitidas = ", ".join(metrica.get("formulas_admitidas") or [])
            print(f"  {metrica.get('metrica_id')} [{metrica.get('sede')}] — "
                  f"unidad: {metrica.get('unidad')} · agregación: {metrica.get('agregacion')}")
            print(f"      fórmulas admitidas: {admitidas}")
            if metrica.get("publicacion") == "tasa":
                print(f"      tasa — numerador: {metrica.get('numerador')}")
                print(f"             denominador: {metrica.get('denominador')}")
                print(f"             elegibilidad: {metrica.get('regla_de_elegibilidad')}")
    print()

    fallas = revisar_vocabulario(vocabulario, manifest, schemas)
    for etiqueta, que_comprueba in CONTROLES_DEL_VOCABULARIO:
        propias = fallas[etiqueta]
        if propias:
            print(f"[{etiqueta}] FALLA  {que_comprueba} — {len(propias)} problemas:")
            for problema in propias:
                print(f"       - {problema}")
        else:
            print(f"[{etiqueta}] OK     {que_comprueba}")

    print()
    rojos = [e for e, _ in CONTROLES_DEL_VOCABULARIO if fallas[e]]
    if rojos:
        print(f"RESULTADO: FALLA — controles en rojo: {', '.join(rojos)}")
        return 1
    cuantas = sum(1 for _ in _metricas_del(vocabulario))
    print(f"RESULTADO: OK — {len(vocabulario.get('categorias') or [])} categorías, {cuantas} "
          f"métricas y {len(vocabulario.get('formulas') or [])} fórmulas ejecutables")
    return 0


# ---------------------------------------------------------------------------------------------
# Modo `--autotest-vocabulario`.
#
# Cinco bloques. El corpus no se comprueba contra sí mismo: el manifest declara aparte qué fixtures
# tienen que existir y con qué controles tiene que fallar cada negativo, y la comparación es exacta
# en las dos direcciones. Los mutantes corren sobre COPIAS EN MEMORIA del vocabulario canónico: mutar
# el archivo del árbol dejaría el repo mutado si el proceso muere.
# ---------------------------------------------------------------------------------------------

class MutanteDeVocabulario(NamedTuple):
    nombre: str
    que_rompe: str
    controles_esperados: frozenset
    aplicar: Callable[[dict, dict], bool]


def _categoria_de(vocabulario: dict, nombre: str) -> dict | None:
    for categoria in vocabulario.get("categorias") or []:
        if categoria.get("categoria") == nombre:
            return categoria
    return None


def _metrica_de(vocabulario: dict, nombre: str) -> dict | None:
    for _, metrica in _metricas_del(vocabulario):
        if metrica.get("metrica_id") == nombre:
            return metrica
    return None


def _mut_eliminar_categoria(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    categoria = _categoria_de(vocabulario, "limpieza")
    if categoria is None:
        return False
    vocabulario["categorias"].remove(categoria)
    return True


def _mut_agregar_categoria_no_declarada(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    vocabulario["categorias"].append({
        "categoria": "velocidad_de_lectura",
        "por_que": "categoría inventada",
        "metricas": [],
    })
    return True


def _mut_eliminar_categoria_del_manifest(vocabulario: dict, manifest: dict) -> bool:
    del vocabulario
    obligatorias = manifest.get("categorias_obligatorias") or []
    for esperada in obligatorias:
        if esperada.get("categoria") == "hallazgos":
            obligatorias.remove(esperada)
            return True
    return False


def _mut_quitar_agregacion(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    metrica = _metrica_de(vocabulario, "salidas-invalidas")
    return metrica is not None and metrica.pop("agregacion", None) is not None


def _mut_quitar_unidad(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    metrica = _metrica_de(vocabulario, "limpieza-completa")
    return metrica is not None and metrica.pop("unidad", None) is not None


def _mut_vaciar_formulas_admitidas(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    # Sobre una métrica de `hallazgos` a propósito: vaciar la de `degradacion` dejaría también sin
    # conteo auditor a la tasa, y el mutante pondría rojo un control que no dice probar.
    metrica = _metrica_de(vocabulario, "hallazgos-emitidos")
    if metrica is None:
        return False
    metrica["formulas_admitidas"] = []
    metrica["comprobaciones"] = []
    metrica["entradas"] = {}
    return True


def _mut_referenciar_formula_inexistente(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    metrica = _metrica_de(vocabulario, "limpieza-completa")
    if metrica is None:
        return False
    metrica["formulas_admitidas"] = ["conjuncion-que-no-existe"]
    metrica["comprobaciones"] = [
        {"formula_id": "conjuncion-que-no-existe", "que_prueba": "no se puede resolver",
         "hechos": [], "resultado_esperado": 1}
    ]
    return True


def _mut_valor_de_predicado_fuera_del_enum(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    for predicado in vocabulario.get("predicados") or []:
        if predicado.get("predicado_id") == "intento-degradado":
            predicado["valores"] = list(predicado["valores"]) + ["degradado_a_medias"]
            return True
    return False


def _mut_tasa_a_escalar(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    metrica = _metrica_de(vocabulario, "tasa-de-degradacion")
    if metrica is None:
        return False
    metrica["publicacion"] = "escalar"
    return True


def _mut_quitar_numerador_de_la_tasa(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    metrica = _metrica_de(vocabulario, "tasa-de-degradacion")
    return metrica is not None and metrica.pop("numerador", None) is not None


def _mut_eliminar_conteo_auditor(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    categoria = _categoria_de(vocabulario, "degradacion")
    if categoria is None:
        return False
    antes = len(categoria["metricas"])
    categoria["metricas"] = [m for m in categoria["metricas"]
                             if m.get("metrica_id") != "conteo-de-degradaciones"]
    return len(categoria["metricas"]) < antes


def _mut_forma_sin_resolvedor(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    for formula in vocabulario.get("formulas") or []:
        if formula.get("formula_id") == "conteo-de-eventos":
            formula["forma"] = "conteo_a_ojo"
            return True
    return False


def _mut_eliminar_formula_del_manifest(vocabulario: dict, manifest: dict) -> bool:
    del vocabulario
    esperadas = manifest.get("formulas_esperadas") or []
    for esperada in esperadas:
        if esperada.get("formula_id") == "conteo-de-intentos":
            esperadas.remove(esperada)
            return True
    return False


def _mut_alterar_resultado_esperado(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    metrica = _metrica_de(vocabulario, "latencia-hasta-resultado-utilizable")
    if metrica is None:
        return False
    for comprobacion in metrica.get("comprobaciones") or []:
        if comprobacion.get("resultado_esperado") is not None:
            comprobacion["resultado_esperado"] += 1
            return True
    return False


def _mut_alterar_hechos_de_comprobacion(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    metrica = _metrica_de(vocabulario, "tasa-de-degradacion")
    if metrica is None:
        return False
    for comprobacion in metrica.get("comprobaciones") or []:
        for hecho in comprobacion.get("hechos") or []:
            if hecho.get("ciclo_operativo") == "completado":
                hecho["ciclo_operativo"] = "degradado"
                return True
    return False


def _mut_eliminar_comprobacion(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    metrica = _metrica_de(vocabulario, "hallazgos-emitidos")
    if metrica is None:
        return False
    antes = len(metrica["comprobaciones"])
    metrica["comprobaciones"] = [c for c in metrica["comprobaciones"]
                                 if c.get("formula_id") != "conteo-de-eventos-sin-reemision"]
    return len(metrica["comprobaciones"]) < antes


def _mut_alterar_comprobacion_de_agregacion(vocabulario: dict, manifest: dict) -> bool:
    del manifest
    for agregacion in vocabulario.get("agregaciones") or []:
        if agregacion.get("agregacion_id") != "suma-de-numeradores-sobre-suma-de-denominadores":
            continue
        for comprobacion in agregacion.get("comprobaciones") or []:
            if comprobacion.get("resultado_esperado") is not None:
                comprobacion["resultado_esperado"] = 0.99
                return True
    return False


MUTANTES_DE_VOCABULARIO: tuple[MutanteDeVocabulario, ...] = (
    MutanteDeVocabulario("categoria-eliminada", "una categoría obligatoria borrada del vocabulario",
                         frozenset({"A"}), _mut_eliminar_categoria),
    MutanteDeVocabulario("categoria-inventada", "una categoría que el manifest no declara",
                         frozenset({"A"}), _mut_agregar_categoria_no_declarada),
    MutanteDeVocabulario("categoria-eliminada-del-manifest",
                         "el manifest recortado para que el vocabulario le cierre",
                         frozenset({"A"}), _mut_eliminar_categoria_del_manifest),
    MutanteDeVocabulario("agregacion-quitada", "una métrica sin regla de agregación",
                         frozenset({"B"}), _mut_quitar_agregacion),
    MutanteDeVocabulario("unidad-quitada", "una métrica sin unidad",
                         frozenset({"B"}), _mut_quitar_unidad),
    MutanteDeVocabulario("formulas-admitidas-vacia", "una métrica que no admite ninguna fórmula",
                         frozenset({"B"}), _mut_vaciar_formulas_admitidas),
    MutanteDeVocabulario("formula-inexistente-referenciada",
                         "una fórmula admitida fuera del catálogo",
                         frozenset({"C"}), _mut_referenciar_formula_inexistente),
    MutanteDeVocabulario("valor-de-predicado-fuera-del-enum",
                         "un predicado que admite un valor que el schema de T1 no declara",
                         frozenset({"C"}), _mut_valor_de_predicado_fuera_del_enum),
    MutanteDeVocabulario("tasa-a-escalar", "la degradación publicada solo como escalar",
                         frozenset({"D"}), _mut_tasa_a_escalar),
    MutanteDeVocabulario("numerador-quitado", "una tasa sin numerador declarado",
                         frozenset({"D"}), _mut_quitar_numerador_de_la_tasa),
    MutanteDeVocabulario("conteo-auditor-eliminado",
                         "la tasa sin el conteo absoluto que permite auditarla",
                         frozenset({"D"}), _mut_eliminar_conteo_auditor),
    MutanteDeVocabulario("resultado-esperado-alterado",
                         "el resultado declarado de una fórmula, corrido en uno",
                         frozenset({"E"}), _mut_alterar_resultado_esperado),
    MutanteDeVocabulario("hechos-de-comprobacion-alterados",
                         "los hechos de entrada de una comprobación, cambiados",
                         frozenset({"E"}), _mut_alterar_hechos_de_comprobacion),
    MutanteDeVocabulario("comprobacion-eliminada",
                         "una fórmula admitida que se queda sin comprobación",
                         frozenset({"E"}), _mut_eliminar_comprobacion),
    MutanteDeVocabulario("comprobacion-de-agregacion-alterada",
                         "el resultado declarado de una agregación",
                         frozenset({"E"}), _mut_alterar_comprobacion_de_agregacion),
    MutanteDeVocabulario("forma-sin-resolvedor",
                         "una fórmula con una forma que el instrumento no implementa",
                         frozenset({"F"}), _mut_forma_sin_resolvedor),
    MutanteDeVocabulario("formula-eliminada-del-manifest",
                         "el manifest recortado para que el catálogo le cierre",
                         frozenset({"F"}), _mut_eliminar_formula_del_manifest),
)

MUTANTES_DE_TASA = frozenset({"tasa-a-escalar", "numerador-quitado", "conteo-auditor-eliminado"})


def _fixtures_de_vocabulario_en_disco() -> set[str]:
    encontrados: set[str] = set()
    for sub in ("conformes", "negativos"):
        directorio = DIR_FIXTURES_VOCABULARIO / sub
        if not directorio.is_dir():
            continue
        for archivo in directorio.glob("*.json"):
            encontrados.add(f"{sub}/{archivo.name}")
    return encontrados


def _rojos(fallas: dict[str, list[str]]) -> set[str]:
    return {etiqueta for etiqueta, mensajes in fallas.items() if mensajes}


def modo_autotest_vocabulario(args: argparse.Namespace) -> int:
    solo_tasa = bool(getattr(args, "tasa", False))
    vocabulario, manifest, schemas, problemas = _cargar_entorno_del_vocabulario()
    if problemas:
        for problema in problemas:
            print(f"[1] FALLA  {problema}")
        return 1

    resultados: list[tuple[str, bool, str]] = []
    esperados_conformes = manifest.get("conformes") or []
    esperados_negativos = manifest.get("negativos") or []

    # [1] El manifest y el directorio, en las dos direcciones.
    declarados = {e["fixture"] for e in esperados_conformes + esperados_negativos}
    en_disco = _fixtures_de_vocabulario_en_disco()
    diferencias = [f"declarado y ausente del disco: {f}" for f in sorted(declarados - en_disco)]
    diferencias += [f"en disco y no declarado: {f}" for f in sorted(en_disco - declarados)]
    resultados.append((
        "1", not diferencias,
        f"manifest ↔ directorio ({len(declarados)} fixtures)" if not diferencias
        else f"{len(diferencias)} divergencias: " + " | ".join(diferencias[:6]),
    ))

    # [2] Control positivo: el vocabulario canónico y los conformes del manifest pasan los seis
    # controles. Sin esto, un rojo de los negativos no prueba nada: podría ser el modo roto.
    fallas_positivas: list[str] = []
    del_canonico = revisar_vocabulario(vocabulario, manifest, schemas)
    for etiqueta in sorted(_rojos(del_canonico)):
        fallas_positivas.append(
            f"el vocabulario canónico falla el control [{etiqueta}]: {del_canonico[etiqueta][0]}")
    for entrada in esperados_conformes:
        alterno, error = _cargar_json(DIR_FIXTURES_VOCABULARIO / entrada["fixture"])
        if error:
            fallas_positivas.append(f"{entrada['fixture']}: {error}")
            continue
        de_este = revisar_vocabulario(alterno, manifest, schemas)
        for etiqueta in sorted(_rojos(de_este)):
            fallas_positivas.append(
                f"{entrada['fixture']} falla el control [{etiqueta}]: {de_este[etiqueta][0]}")
    resultados.append((
        "2", not fallas_positivas,
        f"el canónico y {len(esperados_conformes)} vocabularios conformes pasan los seis controles"
        if not fallas_positivas else " | ".join(fallas_positivas[:4]),
    ))

    # [3] Cada negativo falla EXACTAMENTE en los controles que declara y con su mensaje. Exacto y no
    # «al menos»: un negativo que derivó y arrastra otro control deja sin probar el que dice probar.
    negativos = [e for e in esperados_negativos
                 if not solo_tasa or "D" in set(e.get("controles_esperados") or [])]
    fallas_negativas: list[str] = []
    for entrada in negativos:
        instancia, error = _cargar_json(DIR_FIXTURES_VOCABULARIO / entrada["fixture"])
        if error:
            fallas_negativas.append(f"{entrada['fixture']}: {error}")
            continue
        de_este = revisar_vocabulario(instancia, manifest, schemas)
        rojos = _rojos(de_este)
        esperados = set(entrada.get("controles_esperados") or [])
        if rojos != esperados:
            fallas_negativas.append(
                f"{entrada['fixture']}: se esperaban en rojo {sorted(esperados)} y se vieron "
                f"{sorted(rojos) or 'ninguno'}")
            continue
        mensaje = entrada.get("mensaje_esperado", "")
        vistos = [m for etiqueta in esperados for m in de_este[etiqueta]]
        if not any(mensaje in m for m in vistos):
            fallas_negativas.append(
                f"{entrada['fixture']}: falla en {sorted(esperados)} pero no por «{mensaje}» — "
                f"lo que se vio: {vistos[0]}")
    resultados.append((
        "3", not fallas_negativas,
        f"{len(negativos)} negativos fallan exactamente en su control"
        if not fallas_negativas else " | ".join(fallas_negativas[:4]),
    ))

    # [4] Los mutantes. Sobre copias en memoria del vocabulario y del manifest: el árbol no se toca.
    mutantes = [m for m in MUTANTES_DE_VOCABULARIO
                if not solo_tasa or m.nombre in MUTANTES_DE_TASA]
    fallas_de_mutacion: list[str] = []
    for mutante in mutantes:
        copia_vocabulario = copy.deepcopy(vocabulario)
        copia_manifest = copy.deepcopy(manifest)
        if not mutante.aplicar(copia_vocabulario, copia_manifest):
            fallas_de_mutacion.append(
                f"{mutante.nombre}: la mutación no se pudo aplicar, así que ese control queda sin "
                f"probar")
            continue
        rojos = _rojos(revisar_vocabulario(copia_vocabulario, copia_manifest, schemas))
        if rojos != set(mutante.controles_esperados):
            fallas_de_mutacion.append(
                f"{mutante.nombre} ({mutante.que_rompe}): se esperaban en rojo "
                f"{sorted(mutante.controles_esperados)} y se vieron {sorted(rojos) or 'ninguno'}")
    resultados.append((
        "4", not fallas_de_mutacion,
        f"{len(mutantes)} mutantes detectados, cada uno por su control" if not fallas_de_mutacion
        else " | ".join(fallas_de_mutacion[:4]),
    ))

    # [5] Cobertura: ningún control se queda sin un mutante que pueda ponerlo rojo. Un control sin
    # mutante es un control que nadie probó que funcione.
    exigidos = {"D"} if solo_tasa else {e for e, _ in CONTROLES_DEL_VOCABULARIO}
    cubiertos = {c for m in mutantes for c in m.controles_esperados}
    sin_cubrir = sorted(exigidos - cubiertos)
    resultados.append((
        "5", not sin_cubrir,
        f"los {len(exigidos)} controles exigidos tienen mutante" if not sin_cubrir
        else f"controles sin mutante que los ponga rojos: {', '.join(sin_cubrir)}",
    ))

    for etiqueta, ok, detalle in resultados:
        print(f"[{etiqueta}] {'OK    ' if ok else 'FALLA '} {detalle}")
    print()
    rojos_del_autotest = [e for e, ok, _ in resultados if not ok]
    if rojos_del_autotest:
        print(f"RESULTADO: FALLA — bloques en rojo: {', '.join(rojos_del_autotest)}")
        return 1
    alcance = "la tasa de degradación" if solo_tasa else "el vocabulario completo"
    print(f"RESULTADO: OK — {len(resultados)} bloques en verde sobre {alcance}")
    return 0


# ---------------------------------------------------------------------------------------------
# Modos `--canonicalizar` y `--autotest-canonicalizacion`.
#
# El hash del pre-registro NO vive dentro de lo que hashea (decisión heredada 15): calcular el
# SHA-256 del contenido y escribirlo en ese mismo contenido pide un punto fijo criptográfico, y la
# fila que exige que hash y contenido coincidan no podría pasar nunca. Por eso hay una proyección
# canónica que excluye explícitamente el campo del hash, y el hash se computa sobre ella.
#
# Lo que distingue a esto de una canonicalización cualquiera es la COMPLETITUD: AC-17 exige que la
# proyección cubra, por invariante cerrada, toda decisión que afecte selección, ejecución,
# transformación, elegibilidad, agregación o promoción. Esa completitud NO se prueba contra el
# schema. Si una decisión se borra del schema Y de la proyección, el conjunto esperado se reduce
# solo y el test sigue verde. Por eso hay tres artefactos y no dos:
#
#   1. el schema de T1                         — qué campos existen;
#   2. `punteros-normativos.json`              — qué decide cada campo, EXTERNO al schema;
#   3. `OBLIGACIONES_DE_AC17`, acá abajo       — qué exige el criterio, congelado en código.
#
# Se comparan de a pares y en las dos direcciones. (1)↔(2) caza el campo agregado sin clasificar y
# el puntero que ya no resuelve; (2)↔(3) caza la decisión borrada de los dos lados, que es la que
# (1)↔(2) no puede ver, porque después de borrarla los dos conjuntos siguen coincidiendo.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_CANONICALIZACION = DIR_SCRIPTS / "fixtures-baseline" / "canonicalizacion"
RUTA_MANIFEST_CANONICALIZACION = DIR_FIXTURES_CANONICALIZACION / "manifest.json"
RUTA_PUNTEROS_NORMATIVOS = DIR_FIXTURES_CANONICALIZACION / "punteros-normativos.json"

# El pre-registro materializado que T19 escribe. Todavía no existe: `--canonicalizar` sin ruta lo
# nombra igual, para que el default sea la sede canónica y no un fixture.
RUTA_PREREGISTRO_FASE_0 = "scripts/preregistro-fase-0.json"

# El único campo que la proyección excluye. Está escrito acá y NO se lee del schema: derivarlo del
# schema haría que borrarlo de allá cambiara la proyección en silencio. El control [D] compara este
# nombre contra `x-congelamiento.campos`, así que las dos sedes tienen que moverse juntas.
CAMPO_DEL_HASH = "preregistro_sha256"

# Las seis clases de decisión que AC-17 enumera. Es un conjunto cerrado: una clase inventada en el
# fixture de punteros no clasifica nada, solo esconde el campo detrás de una etiqueta nueva.
CLASES_DE_DECISION: tuple[str, ...] = (
    "seleccion", "ejecucion", "transformacion", "elegibilidad", "agregacion", "promocion",
)


class Obligacion(NamedTuple):
    nombre: str
    exige: str


# Las obligaciones que AC-17 nombra con todas las letras, congeladas acá y repetidas en el fixture
# de punteros. Es la tercera sede a propósito (D-16): borrar una decisión del schema y del fixture
# deja su obligación sin cubrir, y eso es lo que pone el modo rojo.
OBLIGACIONES_DE_AC17: tuple[Obligacion, ...] = (
    Obligacion("formulas", "con qué fórmula se calcula cada métrica"),
    Obligacion("denominadores", "qué población va abajo en una tasa"),
    Obligacion("exclusiones", "qué queda fuera y con qué causa del conjunto cerrado"),
    Obligacion("cobertura_minima", "cuántas muestras hacen falta por métrica y estrato"),
    Obligacion("reglas_de_agregacion", "cómo se combinan intentos y muestras"),
    Obligacion("tratamiento_de_ausencias", "qué veredicto emite una métrica sin observaciones"),
    Obligacion("recetas_de_invocacion", "con qué receta y adaptador se despacha cada muestra"),
    Obligacion("precision", "con qué precisión se publica y se compara cada número"),
    Obligacion("redondeo", "qué pasa con el valor que cae justo en el umbral"),
    Obligacion("identidad_del_entorno", "el conjunto cerrado que identifica al entorno de la corrida"),
)

NOMBRES_DE_OBLIGACION = frozenset(o.nombre for o in OBLIGACIONES_DE_AC17)


# --- La proyección canónica. Cuatro reglas, y las cuatro son verificables desde afuera. ---

def _normalizar_saltos(valor: Any) -> Any:
    """Normaliza a LF los saltos de línea DENTRO de los valores de cadena y de las claves.

    Es la única normalización de contenido que hace la proyección: la misma acta editada en Windows
    y en POSIX tiene que dar el mismo identificador. Lo que NO se toca es el orden de los elementos
    de un arreglo — la cohorte es una secuencia con repeticiones numeradas, no un conjunto—.
    """
    if isinstance(valor, str):
        return valor.replace("\r\n", "\n").replace("\r", "\n")
    if isinstance(valor, list):
        return [_normalizar_saltos(v) for v in valor]
    if isinstance(valor, dict):
        return {_normalizar_saltos(k): _normalizar_saltos(v) for k, v in valor.items()}
    return valor


def proyeccion_canonica(documento: dict) -> bytes:
    """Los bytes sobre los que se computa `preregistro_sha256`.

    - **Codificación:** UTF-8 sobre el texto ya decodificado, sin BOM. Escribir `ó` o `\\u00f3` es
      el mismo contenido y da el mismo hash.
    - **Orden de claves:** lexicográfico por punto de código, en todos los niveles. El orden en que
      un editor deja el archivo no es contenido.
    - **Saltos de línea:** CRLF y CR se normalizan a LF dentro de las cadenas; la proyección es una
      sola línea terminada en exactamente un LF, así que el formato del JSON de origen —indentación,
      espacios, saltos entre tokens— tampoco es contenido.
    - **Exclusión explícita:** `CAMPO_DEL_HASH` se quita del objeto raíz, y solo de ahí. Es el punto
      fijo de la decisión heredada 15.
    """
    if not isinstance(documento, dict):
        raise ValueError("la proyección canónica se computa sobre un objeto JSON")
    proyectado = {k: _normalizar_saltos(v) for k, v in documento.items() if k != CAMPO_DEL_HASH}
    texto = json.dumps(proyectado, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False)
    return texto.encode("utf-8") + b"\n"


def hash_canonico(documento: dict) -> str:
    return hashlib.sha256(proyeccion_canonica(documento)).hexdigest()


# --- Punteros. El fixture habla en punteros de INSTANCIA; acá se los resuelve contra el schema. ---

def _resolver_cadena(schema: dict, sub: dict) -> dict:
    vueltas = 0
    while "$ref" in sub:
        sub = _resolver(schema, sub["$ref"])
        vueltas += 1
        if vueltas > 32:
            raise ValueError("cadena de `$ref` demasiado profunda")
    return sub


def _navegar_schema(schema: dict, puntero: str) -> tuple[dict, str, dict] | None:
    """Resuelve un puntero de instancia contra el schema.

    Devuelve `(esquema_del_objeto_contenedor, clave, esquema_de_la_hoja)`, o `None` si el schema no
    declara ese camino. `-` atraviesa un arreglo. Un puntero que termina en `-` no nombra un campo y
    se rechaza como mal formado.
    """
    tramos = [t for t in puntero.split("/") if t != ""]
    if not tramos or tramos[-1] == "-":
        return None
    actual = _resolver_cadena(schema, schema)
    contenedor: dict | None = None
    clave = ""
    for tramo in tramos:
        if tramo == "-":
            items = actual.get("items")
            if items is None:
                return None
            actual = _resolver_cadena(schema, items)
            continue
        propiedades = actual.get("properties") or {}
        if tramo not in propiedades:
            return None
        contenedor, clave = actual, tramo
        actual = _resolver_cadena(schema, propiedades[tramo])
    if contenedor is None:
        return None
    return contenedor, clave, actual


def _hojas_declaradas(schema: dict) -> list[str]:
    """Todos los punteros de instancia que el schema declara y que llevan un valor.

    Hoja es lo que no es objeto con propiedades ni arreglo de objetos: un escalar, un enum o un
    arreglo de escalares. `/cohorte` y `/cohorte/muestras` son tramos, no hojas.
    """
    hojas: list[str] = []

    def recorrer(sub: dict, puntero: str, en_curso: tuple[int, ...]) -> None:
        resuelto = _resolver_cadena(schema, sub)
        if id(resuelto) in en_curso:
            return  # ciclo de `$ref`: no hay ninguno hoy, y si aparece no cuelga el modo
        camino = en_curso + (id(resuelto),)
        propiedades = resuelto.get("properties")
        if propiedades:
            for clave in propiedades:
                recorrer(propiedades[clave], f"{puntero}/{clave}", camino)
            return
        items = resuelto.get("items")
        if items is not None and (_resolver_cadena(schema, items).get("properties")):
            recorrer(items, f"{puntero}/-", camino)
            return
        hojas.append(puntero)

    recorrer(schema, "", ())
    return hojas


def _ubicaciones_en_documento(documento: Any, puntero: str) -> list[tuple[Any, Any]]:
    """Las ubicaciones concretas de un puntero en un documento, como pares `(contenedor, clave)`.

    Un puntero con `-` se expande sobre los índices que el documento realmente tiene. La lista vacía
    significa que el documento no instancia ese campo — y un campo sin valor no se puede mutar, así
    que su mutante pasaría en verde sin haber probado nada.
    """
    actuales: list[Any] = [documento]
    tramos = [t for t in puntero.split("/") if t != ""]
    for indice, tramo in enumerate(tramos):
        ultimo = indice == len(tramos) - 1
        siguientes: list[Any] = []
        for actual in actuales:
            if tramo == "-":
                if isinstance(actual, list):
                    siguientes.extend(actual)
                continue
            if isinstance(actual, dict) and tramo in actual:
                siguientes.append((actual, tramo) if ultimo else actual[tramo])
        actuales = siguientes
    return [a for a in actuales if isinstance(a, tuple)]


def _mutar_valor(valor: Any) -> Any:
    """Una mutación puntual que cambia el valor sin cambiar su tipo."""
    if isinstance(valor, bool):
        return not valor
    if isinstance(valor, (int, float)):
        return valor + 1
    if isinstance(valor, str):
        return valor + "-mutado"
    if isinstance(valor, list):
        return valor + ["elemento-mutado"]
    if isinstance(valor, dict):
        return dict(valor, campo_mutado=True)
    return "mutado"


# --- Las revisiones. Están sueltas porque los mutantes las reejecutan sobre copias alteradas. ---

def revisar_punteros(schema: dict, punteros: dict) -> list[str]:
    """Fixture de punteros ↔ schema, en las dos direcciones.

    Hacia el schema: todo puntero declarado tiene que resolver. Hacia el fixture: toda hoja que el
    schema declara tiene que estar clasificada, como normativa o como no normativa con su razón.
    El silencio no es una clasificación.
    """
    fallas: list[str] = []
    normativos = punteros.get("normativos") or []
    no_normativos = punteros.get("no_normativos") or []

    declarados: list[str] = []
    for entrada in normativos:
        puntero = entrada.get("puntero", "")
        declarados.append(puntero)
        if _navegar_schema(schema, puntero) is None:
            fallas.append(f"puntero normativo que el schema no declara: {puntero}")
        if entrada.get("clase") not in CLASES_DE_DECISION:
            fallas.append(f"{puntero}: clase fuera del conjunto cerrado: {entrada.get('clase')!r}")
        if not (entrada.get("por_que") or "").strip():
            fallas.append(f"{puntero}: sin decir qué decide")
    for entrada in no_normativos:
        puntero = entrada.get("puntero", "")
        declarados.append(puntero)
        if _navegar_schema(schema, puntero) is None:
            fallas.append(f"puntero no normativo que el schema no declara: {puntero}")
        if not (entrada.get("razon") or "").strip():
            fallas.append(f"{puntero}: declarado no normativo sin razón escrita")

    repetidos = sorted({p for p in declarados if declarados.count(p) > 1})
    fallas += [f"puntero declarado dos veces: {p}" for p in repetidos]

    sin_clasificar = [h for h in _hojas_declaradas(schema) if h not in set(declarados)]
    fallas += [f"hoja del schema sin clasificar: {h}" for h in sin_clasificar]
    return fallas


def revisar_obligaciones(punteros: dict) -> list[str]:
    """Obligaciones congeladas ↔ obligaciones cubiertas por el fixture, en las dos direcciones.

    Es el control que caza la decisión borrada del schema Y del fixture: después de ese borrado los
    dos conjuntos de `revisar_punteros` vuelven a coincidir, pero la obligación queda sin ningún
    puntero que la cubra.
    """
    fallas: list[str] = []
    cubiertas: dict[str, list[str]] = {}
    for entrada in punteros.get("normativos") or []:
        for nombre in entrada.get("obligaciones") or []:
            cubiertas.setdefault(nombre, []).append(entrada.get("puntero", ""))

    for obligacion in OBLIGACIONES_DE_AC17:
        if not cubiertas.get(obligacion.nombre):
            fallas.append(
                f"obligación de AC-17 sin ningún puntero que la cubra: {obligacion.nombre} "
                f"({obligacion.exige})"
            )
    for nombre in sorted(set(cubiertas) - NOMBRES_DE_OBLIGACION):
        fallas.append(f"obligación citada por el fixture y ausente de la lista congelada: {nombre}")

    # La lista cerrada, transcrita también en el fixture. No es redundancia: es lo que obliga a que
    # sacar una obligación toque los dos archivos, y por eso la ausencia de la lista es roja y no
    # una exención silenciosa.
    declaradas = (punteros.get("obligaciones_de_ac17") or {}).get("nombres")
    if declaradas is None:
        fallas.append("el fixture no transcribe la lista cerrada de obligaciones de AC-17")
    elif set(declaradas) != NOMBRES_DE_OBLIGACION:
        faltan = sorted(NOMBRES_DE_OBLIGACION - set(declaradas))
        sobran = sorted(set(declaradas) - NOMBRES_DE_OBLIGACION)
        fallas.append(f"la lista del fixture difiere de la congelada — faltan: {faltan}; "
                      f"sobran: {sobran}")

    faltan_clases = [c for c in CLASES_DE_DECISION
                     if not any(e.get("clase") == c for e in punteros.get("normativos") or [])]
    fallas += [f"clase de decisión sin ningún puntero: {c}" for c in faltan_clases]
    return fallas


def revisar_sensibilidad(base: dict, punteros: dict) -> list[str]:
    """Cada campo normativo mutado individualmente altera el hash; el campo del hash no lo altera.

    La dirección de la igualdad es tan importante como la de la diferencia: si `no_normativos`
    admitiera cualquier campo, declarar uno ahí sería la forma de sacarlo de la proyección sin que
    nada se ponga rojo. Como la proyección solo excluye `CAMPO_DEL_HASH`, cualquier otra entrada de
    `no_normativos` deja este control en rojo.
    """
    fallas: list[str] = []
    referencia = hash_canonico(base)

    for entrada in punteros.get("normativos") or []:
        puntero = entrada.get("puntero", "")
        copia = copy.deepcopy(base)
        ubicaciones = _ubicaciones_en_documento(copia, puntero)
        if not ubicaciones:
            fallas.append(f"{puntero}: el documento base no lo instancia, así que no se puede mutar")
            continue
        contenedor, clave = ubicaciones[0]
        contenedor[clave] = _mutar_valor(contenedor[clave])
        if hash_canonico(copia) == referencia:
            fallas.append(f"{puntero}: es normativo y mutarlo NO altera el hash")

    for entrada in punteros.get("no_normativos") or []:
        puntero = entrada.get("puntero", "")
        copia = copy.deepcopy(base)
        ubicaciones = _ubicaciones_en_documento(copia, puntero)
        if not ubicaciones:
            fallas.append(f"{puntero}: el documento base no lo instancia, así que no se puede mutar")
            continue
        contenedor, clave = ubicaciones[0]
        contenedor[clave] = _mutar_valor(contenedor[clave])
        if hash_canonico(copia) != referencia:
            fallas.append(f"{puntero}: está fuera de la proyección y mutarlo SÍ altera el hash")
    return fallas


def _borrar_hoja_del_schema(schema: dict, puntero: str) -> bool:
    """Borra del schema el campo que nombra un puntero, podando el objeto que queda vacío.

    La poda importa: un objeto sin propiedades pasaría a ser una hoja nueva y sin clasificar, y el
    mutante que quiere probar «borrada de los dos lados» se pondría rojo por el motivo equivocado.
    """
    tramos = [t for t in puntero.split("/") if t != ""]
    while tramos:
        navegacion = _navegar_schema(schema, "/" + "/".join(tramos))
        if navegacion is None:
            return False
        contenedor, clave, _ = navegacion
        (contenedor.get("properties") or {}).pop(clave, None)
        if "required" in contenedor:
            contenedor["required"] = [r for r in contenedor["required"] if r != clave]
        if contenedor.get("properties"):
            return True
        tramos = tramos[:-1]
        while tramos and tramos[-1] == "-":
            tramos = tramos[:-1]
    return True


def _sin_obligacion(punteros: dict, nombre: str) -> dict:
    copia = copy.deepcopy(punteros)
    copia["normativos"] = [e for e in copia.get("normativos") or []
                           if nombre not in (e.get("obligaciones") or [])]
    return copia


def _fixtures_de_canonicalizacion_en_disco() -> set[str]:
    encontrados: set[str] = set()
    for sub in ("conformes", "variantes"):
        directorio = DIR_FIXTURES_CANONICALIZACION / sub
        if not directorio.is_dir():
            continue
        for archivo in directorio.glob("*.json"):
            encontrados.add(f"{sub}/{archivo.name}")
    return encontrados


def modo_canonicalizar(args: argparse.Namespace) -> int:
    ruta = Path(getattr(args, "canonicalizar"))
    if not ruta.is_absolute():
        ruta = RAIZ / ruta
    solo_bytes = bool(getattr(args, "solo_bytes", False))
    informe = sys.stderr if solo_bytes else sys.stdout

    documento, error = _cargar_json(ruta)
    if error:
        print(f"FALLA  {ruta}: {error}", file=informe)
        return 1
    if not isinstance(documento, dict):
        print(f"FALLA  {ruta}: la proyección canónica se computa sobre un objeto JSON", file=informe)
        return 1

    bytes_canonicos = proyeccion_canonica(documento)
    digest = hashlib.sha256(bytes_canonicos).hexdigest()

    if solo_bytes:
        sys.stdout.buffer.write(bytes_canonicos)
        sys.stdout.buffer.flush()
    else:
        print(f"OK     {ruta}")
        print(f"       proyección canónica: {len(bytes_canonicos)} bytes, UTF-8, claves ordenadas, "
              f"saltos de línea normalizados a LF")
        print(f"       campo excluido: {CAMPO_DEL_HASH} (decisión heredada 15)")
        print(f"SHA-256: {digest}")

    declarado = documento.get(CAMPO_DEL_HASH)
    if declarado is None:
        print(f"NOTA   el documento no lleva `{CAMPO_DEL_HASH}`: es una propuesta de acta, todavía "
              f"anterior al congelamiento", file=informe)
        return 0
    if declarado != digest:
        print(f"FALLA  `{CAMPO_DEL_HASH}` declarado como {declarado} y no coincide con el computado",
              file=informe)
        return 1
    print(f"       `{CAMPO_DEL_HASH}` declarado coincide con el computado", file=informe)

    if solo_bytes:
        return 0
    print()
    print(bytes_canonicos.decode("utf-8"), end="")
    return 0


def modo_autotest_canonicalizacion(args: argparse.Namespace) -> int:
    del args
    manifest, error = _cargar_json(RUTA_MANIFEST_CANONICALIZACION)
    if error:
        print(f"[A] FALLA  manifest del corpus: {error}")
        return 1
    punteros, error = _cargar_json(RUTA_PUNTEROS_NORMATIVOS)
    if error:
        print(f"[B] FALLA  fixture de punteros normativos: {error}")
        return 1
    schema, error = _cargar_json(DIR_SCRIPTS / "preregistro.schema.json")
    if error:
        print(f"[C] FALLA  schema de pre-registro: {error}")
        return 1

    resultados: list[tuple[str, bool, str]] = []
    entrada_base = manifest.get("base") or {}
    variantes = manifest.get("variantes") or []

    # [A] El manifest y el directorio, en las dos direcciones. Borrar la variante que prueba la
    # insensibilidad al campo del hash tiene que poner esto rojo, no reducir el conjunto probado.
    declarados = {entrada_base.get("fixture", "")} | {v.get("fixture", "") for v in variantes}
    en_disco = _fixtures_de_canonicalizacion_en_disco()
    diferencias = [f"declarado y ausente del disco: {f}" for f in sorted(declarados - en_disco)]
    diferencias += [f"en disco y no declarado: {f}" for f in sorted(en_disco - declarados)]
    if manifest.get("punteros_normativos") != RUTA_PUNTEROS_NORMATIVOS.name:
        diferencias.append("el manifest no apunta al fixture de punteros normativos")
    resultados.append((
        "A", not diferencias,
        f"manifest ↔ directorio ({len(declarados)} fixtures)" if not diferencias
        else f"{len(diferencias)} divergencias: " + " | ".join(diferencias[:6]),
    ))

    # [B] Las obligaciones de AC-17 congeladas ↔ las que el fixture cubre, en las dos direcciones.
    fallas = revisar_obligaciones(punteros)
    resultados.append((
        "B", not fallas,
        f"las {len(OBLIGACIONES_DE_AC17)} obligaciones de AC-17 y las "
        f"{len(CLASES_DE_DECISION)} clases de decisión, cubiertas" if not fallas
        else " | ".join(fallas[:4]),
    ))

    # [C] El fixture de punteros ↔ el schema, en las dos direcciones.
    fallas = revisar_punteros(schema, punteros)
    normativos = punteros.get("normativos") or []
    no_normativos = punteros.get("no_normativos") or []
    resultados.append((
        "C", not fallas,
        f"{len(normativos)} punteros normativos y {len(no_normativos)} no normativos cubren las "
        f"{len(_hojas_declaradas(schema))} hojas del schema" if not fallas
        else " | ".join(fallas[:4]),
    ))

    # [D] El nombre del campo excluido, contra el que el schema declara exento en la propuesta. Son
    # dos sedes del mismo hecho y tienen que moverse juntas.
    exentos = (schema.get("x-congelamiento") or {}).get("campos") or []
    coincide = list(exentos) == [CAMPO_DEL_HASH]
    resultados.append((
        "D", coincide,
        f"el campo excluido de la proyección es `{CAMPO_DEL_HASH}` en las dos sedes" if coincide
        else f"`x-congelamiento.campos` es {exentos} y la proyección excluye `{CAMPO_DEL_HASH}`",
    ))

    # [E] El documento base: válido contra el schema y EXHAUSTIVO. Una hoja sin valor no se puede
    # mutar, y su mutante pasaría en verde sin haber probado nada.
    base, error = _cargar_json(DIR_FIXTURES_CANONICALIZACION / entrada_base.get("fixture", ""))
    if error:
        print(f"[E] FALLA  documento base: {error}")
        return 1
    problemas = [f"no valida: {e}" for e in validar(base, schema)[:3]]
    problemas += [f"hoja sin valor en el base: {h}" for h in _hojas_declaradas(schema)
                  if not _ubicaciones_en_documento(base, h)]
    resultados.append((
        "E", not problemas,
        f"el documento base valida y lleva valor en las {len(_hojas_declaradas(schema))} hojas"
        if not problemas else " | ".join(problemas[:4]),
    ))

    # [F] Las variantes, en las dos direcciones: las que declaran `igual` hashean igual y las que
    # declaran `distinto` hashean distinto. Sin las segundas, una proyección que dejara fuera medio
    # documento seguiría pasando las primeras.
    referencia = hash_canonico(base)
    fallas = []
    for variante in variantes:
        documento, error = _cargar_json(DIR_FIXTURES_CANONICALIZACION / variante.get("fixture", ""))
        if error:
            fallas.append(f"{variante.get('fixture')}: {error}")
            continue
        esperado = variante.get("hash")
        obtenido = hash_canonico(documento)
        if esperado == "igual" and obtenido != referencia:
            fallas.append(f"{variante.get('fixture')}: declara `igual` y hashea distinto")
        elif esperado == "distinto" and obtenido == referencia:
            fallas.append(f"{variante.get('fixture')}: declara `distinto` y hashea igual")
        elif esperado not in ("igual", "distinto"):
            fallas.append(f"{variante.get('fixture')}: veredicto de hash no declarado")
    resultados.append((
        "F", not fallas,
        f"las {len(variantes)} variantes hashean como declaran" if not fallas
        else " | ".join(fallas[:4]),
    ))

    # [G] El punto fijo, cerrado: el documento base DECLARA su propio hash y el declarado coincide
    # con el computado. Es la fila que la decisión heredada 15 dice que no puede pasar nunca sin una
    # proyección que excluya el campo — acá pasa, y eso es lo que la proyección compra.
    declarado = base.get(CAMPO_DEL_HASH)
    cierra = declarado == referencia
    resultados.append((
        "G", cierra,
        f"el documento base declara su propio hash y coincide: {referencia[:12]}…" if cierra
        else f"`{CAMPO_DEL_HASH}` declarado es {declarado} y el computado es {referencia}",
    ))

    # [H] Campo por campo: cada normativo mutado individualmente altera el hash, y el campo del hash
    # no lo altera. Es lo que prueba que la proyección no dejó nada afuera.
    fallas = revisar_sensibilidad(base, punteros)
    resultados.append((
        "H", not fallas,
        f"{len(normativos)} campos normativos alteran el hash y {len(no_normativos)} no"
        if not fallas else " | ".join(fallas[:4]),
    ))

    # [I] Que las guardas de arriba puedan ponerse rojas. Sobre COPIAS en memoria del schema y del
    # fixture —mutar los archivos del árbol dejaría el repo mutado si el proceso muere—.
    fallas = []
    aplicados: list[str] = []

    def comprobar(nombre: str, hallazgos: list[str]) -> None:
        """Un mutante aplicado y su veredicto. El conteo se deriva de acá, nunca se escribe a mano."""
        aplicados.append(nombre)
        if not hallazgos:
            fallas.append(f"{nombre}: pasa sin detectarse")

    con_puntero_roto = copy.deepcopy(punteros)
    con_puntero_roto["normativos"].append(
        {"puntero": "/campo_que_no_existe", "clase": "seleccion", "obligaciones": [],
         "por_que": "puntero que el schema no declara"})
    comprobar("puntero-que-no-resuelve", revisar_punteros(schema, con_puntero_roto))

    sin_un_puntero = copy.deepcopy(punteros)
    sin_un_puntero["normativos"] = sin_un_puntero["normativos"][1:]
    comprobar("puntero-quitado-del-fixture", revisar_punteros(schema, sin_un_puntero))

    schema_con_campo_nuevo = copy.deepcopy(schema)
    schema_con_campo_nuevo["properties"]["campo_agregado_sin_clasificar"] = {"type": "string"}
    comprobar("hoja-agregada-al-schema", revisar_punteros(schema_con_campo_nuevo, punteros))

    con_clase_inventada = copy.deepcopy(punteros)
    con_clase_inventada["normativos"][0]["clase"] = "clase-inventada"
    comprobar("clase-inventada", revisar_punteros(schema, con_clase_inventada))

    con_obligacion_de_mas = copy.deepcopy(punteros)
    con_obligacion_de_mas["normativos"][0].setdefault("obligaciones", []).append("obligacion-nueva")
    comprobar("obligacion-que-no-esta-congelada", revisar_obligaciones(con_obligacion_de_mas))

    sin_la_lista_transcrita = copy.deepcopy(punteros)
    sin_la_lista_transcrita["obligaciones_de_ac17"].pop("nombres", None)
    comprobar("lista-de-obligaciones-sin-transcribir", revisar_obligaciones(sin_la_lista_transcrita))

    con_la_lista_recortada = copy.deepcopy(punteros)
    con_la_lista_recortada["obligaciones_de_ac17"]["nombres"] = \
        con_la_lista_recortada["obligaciones_de_ac17"]["nombres"][1:]
    comprobar("lista-de-obligaciones-recortada", revisar_obligaciones(con_la_lista_recortada))

    con_el_hash_normativo = copy.deepcopy(punteros)
    con_el_hash_normativo["no_normativos"] = []
    con_el_hash_normativo["normativos"].append(
        {"puntero": f"/{CAMPO_DEL_HASH}", "clase": "transformacion", "obligaciones": [],
         "por_que": "declarar normativo al campo que la proyección excluye"})
    comprobar("campo-del-hash-declarado-normativo",
              revisar_sensibilidad(base, con_el_hash_normativo))

    fuera_de_la_proyeccion = copy.deepcopy(punteros)
    fuera_de_la_proyeccion["normativos"] = [e for e in fuera_de_la_proyeccion["normativos"]
                                            if e.get("puntero") != "/code_commit"]
    fuera_de_la_proyeccion["no_normativos"].append(
        {"puntero": "/code_commit", "razon": "declarar no normativo un campo que sí entra al hash"})
    comprobar("campo-normativo-declarado-no-normativo",
              revisar_sensibilidad(base, fuera_de_la_proyeccion))

    # El mutante que da nombre a esta task: la decisión borrada de los DOS lados. Después del
    # borrado, `revisar_punteros` vuelve a coincidir consigo mismo —por eso tiene que seguir en
    # verde, o el mutante estaría probando otra cosa— y lo único que se pone rojo es la obligación
    # que quedó sin cubrir.
    for obligacion in OBLIGACIONES_DE_AC17:
        nombre = f"borrada-de-ambos/{obligacion.nombre}"
        aplicados.append(nombre)
        fixture_podado = _sin_obligacion(punteros, obligacion.nombre)
        schema_podado = copy.deepcopy(schema)
        borrados = [e["puntero"] for e in punteros.get("normativos") or []
                    if obligacion.nombre in (e.get("obligaciones") or [])]
        if not borrados:
            fallas.append(f"{nombre}: no hay punteros que borrar")
            continue
        if not all(_borrar_hoja_del_schema(schema_podado, p) for p in borrados):
            fallas.append(f"{nombre}: la poda del schema no se aplicó")
            continue
        residuo = revisar_punteros(schema_podado, fixture_podado)
        if residuo:
            fallas.append(f"{nombre}: el par quedó inconsistente ({residuo[0]}), así que el "
                          "mutante prueba otra cosa")
            continue
        if not revisar_obligaciones(fixture_podado):
            fallas.append(f"{nombre}: borrarla del schema Y del fixture pasa sin detectarse")
    resultados.append((
        "I", not fallas,
        f"{len(aplicados)} mutantes de las guardas, detectados" if not fallas
        else " | ".join(fallas[:4]),
    ))

    for etiqueta, ok, detalle in resultados:
        print(f"[{etiqueta}] {'OK    ' if ok else 'FALLA '} {detalle}")
    print()
    rojos = [e for e, ok, _ in resultados if not ok]
    if rojos:
        print(f"RESULTADO: FALLA — controles en rojo: {', '.join(rojos)}")
        return 1
    print(f"RESULTADO: OK — {len(resultados)} controles en verde")
    return 0


# ---------------------------------------------------------------------------------------------
# Modos `--validar-bundles`, `--recolectar` y `--autotest-bundles`.
#
# El recolector es lo que convierte evidencia cruda en observación. Sin él, cada corrida se
# interpreta a mano y el baseline deja de ser recomponible: el número publicado ya no tiene una
# cadena que lo devuelva a un hecho.
#
# La regla que gobierna todo este bloque: **la observación se deriva SOLO del bundle**. Ningún dato
# sale de la memoria del operador, de lo que la corrida declare sobre sí misma en prosa, ni de un
# valor plausible puesto donde faltaba un hecho. Donde la cadena no cierra, la métrica se emite SIN
# valor y con su adjudicación escrita —que es para lo que el schema tiene la variante sin `valor`—,
# y donde no cierra la observación entera, la recolección FALLA en lugar de completarla.
#
# Frontera del bundle en disco, que hasta acá no estaba fijada: una corrida es un directorio
# `<dir>/<run_id>/` y su bundle es el archivo `bundle.json` que está adentro. `bundle_sha256` es el
# SHA-256 de los BYTES de ese archivo tal como quedaron en disco, así que se recomputa con
# `shasum -a 256 <dir>/<run_id>/bundle.json` sin creerle a este programa.
# ---------------------------------------------------------------------------------------------

DIR_CORRIDAS_FASE_0 = DIR_SCRIPTS / "corridas-fase-0"
DIR_OBSERVACIONES_FASE_0 = DIR_SCRIPTS / "observaciones-fase-0"
DIR_FIXTURES_BUNDLES = DIR_SCRIPTS / "fixtures-baseline" / "bundles"
RUTA_MANIFEST_BUNDLES = DIR_FIXTURES_BUNDLES / "manifest.json"

NOMBRE_DEL_BUNDLE = "bundle.json"

RUTA_CORRIDAS_FASE_0 = "scripts/corridas-fase-0"

# Qué invocación acredita cada adaptador. Un bundle de script que registra una acción no deja
# constancia de ningún comando, y «comando literal registrado» pasa a no exigir nada.
INVOCACION_POR_ADAPTADOR: dict[str, tuple[str, tuple[str, ...]]] = {
    "script": ("comando", ("comando_literal",)),
    "sesion_de_agente": ("accion", ("accion_literal", "prompt_sha256")),
}

# Eje 2 y eje 3 de la observación, uno por hecho del bundle. Son mapeos y no juicios: el hecho lo
# registra el runner al capturar, y el recolector no lo reinterpreta.
VALIDEZ_POR_ESTADO_DEL_REPORTE: dict[str, str] = {
    "interpretable": "valido",
    "malformado": "malformado",
    "ausente": "ausente",
}
SEMANTICA_POR_VEREDICTO: dict[str, str] = {
    "correcto": "correcto",
    "incorrecto": "incorrecto",
    "no_evaluable": "no_evaluable",
}


class BundleEnDisco(NamedTuple):
    """Una corrida leída de `<dir>/<run_id>/`. `datos` es None cuando no se pudo cargar."""
    directorio: str
    ruta: Path
    datos: dict | None
    sha256: str | None
    error: str | None


def _leer_bundle(directorio: Path) -> BundleEnDisco:
    ruta = directorio / NOMBRE_DEL_BUNDLE
    try:
        crudo = ruta.read_bytes()
    except FileNotFoundError:
        return BundleEnDisco(directorio.name, ruta, None, None,
                             f"no existe {NOMBRE_DEL_BUNDLE} en la corrida")
    try:
        datos = json.loads(crudo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return BundleEnDisco(directorio.name, ruta, None, None, f"JSON inválido: {exc}")
    if not isinstance(datos, dict):
        return BundleEnDisco(directorio.name, ruta, None, None, "el bundle no es un objeto JSON")
    return BundleEnDisco(directorio.name, ruta, datos, hashlib.sha256(crudo).hexdigest(), None)


def leer_conjunto_de_bundles(raiz: Path) -> list[BundleEnDisco]:
    """Cada hijo directorio de `raiz` es una corrida. El orden es el del nombre, para que dos
    corridas del mismo conjunto se reporten siempre igual."""
    if not raiz.is_dir():
        return []
    return [_leer_bundle(hijo) for hijo in sorted(raiz.iterdir()) if hijo.is_dir()]


# --- Las comprobaciones del conjunto. Es una tabla y no una función larga a propósito: las tasks
# que siguen —aislamiento, cobertura del protocolo, identidad del entorno, sanitización— agregan
# las suyas registrándolas acá, sin reescribir ni el modo ni las anteriores. ---

class ComprobacionDeBundles(NamedTuple):
    clave: str
    que_prueba: str
    revisar: Callable[[list[BundleEnDisco], dict], list[str]]


COMPROBACIONES_DE_BUNDLES: list[ComprobacionDeBundles] = []


def registrar_comprobacion_de_bundles(clave: str, que_prueba: str,
                                      revisar: Callable[[list[BundleEnDisco], dict],
                                                        list[str]]) -> None:
    if any(c.clave == clave for c in COMPROBACIONES_DE_BUNDLES):
        raise ValueError(f"la comprobación de bundles {clave} ya está registrada")
    COMPROBACIONES_DE_BUNDLES.append(ComprobacionDeBundles(clave, que_prueba, revisar))


def _comprobar_conjunto_no_vacio(bundles: list[BundleEnDisco], schema: dict) -> list[str]:
    del schema
    if bundles:
        return []
    # Un conjunto vacío satisface en el vacío todo lo demás. Sin esta comprobación, apuntar el modo
    # a un directorio equivocado da exit 0 y se lee como «los bundles están bien».
    return ["el conjunto no tiene ninguna corrida: un directorio vacío no es un conjunto válido"]


def _comprobar_bundle_presente_y_conforme(bundles: list[BundleEnDisco], schema: dict) -> list[str]:
    fallas: list[str] = []
    for bundle in bundles:
        if bundle.error:
            fallas.append(f"{bundle.directorio}: {bundle.error}")
            continue
        errores = validar(bundle.datos, schema)
        if errores:
            fallas.append(f"{bundle.directorio}: {len(errores)} errores contra el schema — "
                          f"{errores[0]}")
    return fallas


def _comprobar_identidad_contra_el_directorio(bundles: list[BundleEnDisco],
                                              schema: dict) -> list[str]:
    del schema
    fallas: list[str] = []
    for bundle in bundles:
        if bundle.datos is None:
            continue  # ya lo reportó la comprobación anterior
        declarado = bundle.datos.get("run_id")
        if declarado != bundle.directorio:
            fallas.append(f"{bundle.directorio}: declara `run_id` {declarado!r}, que no es el "
                          "nombre de su directorio")
    return fallas


def _comprobar_run_id_unico(bundles: list[BundleEnDisco], schema: dict) -> list[str]:
    del schema
    vistos: dict[str, str] = {}
    fallas: list[str] = []
    for bundle in bundles:
        if bundle.datos is None:
            continue
        declarado = bundle.datos.get("run_id")
        if declarado in vistos:
            fallas.append(f"{bundle.directorio}: `run_id` {declarado!r} repetido — ya lo declara "
                          f"{vistos[declarado]}")
            continue
        vistos[declarado] = bundle.directorio
    return fallas


def _comprobar_invocacion_registrada(bundles: list[BundleEnDisco], schema: dict) -> list[str]:
    del schema
    fallas: list[str] = []
    for bundle in bundles:
        if bundle.datos is None:
            continue
        adaptador = bundle.datos.get("adaptador")
        esperado = INVOCACION_POR_ADAPTADOR.get(adaptador)
        if esperado is None:
            fallas.append(f"{bundle.directorio}: adaptador {adaptador!r} sin invocación declarada")
            continue
        tipo_esperado, campos = esperado
        invocacion = bundle.datos.get("invocacion") or {}
        if invocacion.get("tipo") != tipo_esperado:
            fallas.append(f"{bundle.directorio}: el adaptador {adaptador!r} despacha por "
                          f"«{tipo_esperado}» y la invocación registrada es "
                          f"«{invocacion.get('tipo')}»: no queda constancia de con qué corrió")
            continue
        for campo in campos:
            if not invocacion.get(campo):
                fallas.append(f"{bundle.directorio}: la invocación no registra `{campo}`")
    return fallas


registrar_comprobacion_de_bundles(
    "A", "el conjunto tiene al menos una corrida", _comprobar_conjunto_no_vacio)
registrar_comprobacion_de_bundles(
    "B", "cada corrida lleva su bundle y valida contra el schema",
    _comprobar_bundle_presente_y_conforme)
registrar_comprobacion_de_bundles(
    "C", "el `run_id` declarado es el nombre de su directorio",
    _comprobar_identidad_contra_el_directorio)
registrar_comprobacion_de_bundles(
    "D", "el `run_id` es único en el conjunto", _comprobar_run_id_unico)
registrar_comprobacion_de_bundles(
    "E", "la invocación registra su literal, y el que corresponde a su adaptador",
    _comprobar_invocacion_registrada)


# --- La derivación. Cada campo de la observación dice de qué hecho del bundle sale. ---

class FallaDeDerivacion(NamedTuple):
    campo: str
    motivo: str

    def __str__(self) -> str:
        return f"{self.campo}: {self.motivo}"


def derivar_observation_id(bundle: dict, reglas: dict | None = None) -> str:
    """La observación es una por intento, así que su identidad se deriva de la del intento y no de
    la de la corrida.

    Con `reglas` —las `reglas_de_derivacion_de_identidad` que el pre-registro congela— la identidad
    sale de la plantilla congelada, que es la única forma admitida en producción. Sin ellas queda
    la forma por defecto, que es lo que permite recolectar un bundle antes de que exista el
    pre-registro; una observación derivada así no satisface la regla congelada y el control de
    derivación de T5 la reporta."""
    if reglas:
        valor, error = aplicar_regla_de_identidad(reglas.get("observation_id") or {},
                                                  contexto_de_identidad(bundle))
        if error is None:
            return valor
    return f"obs-{bundle.get('attempt_id')}"


def _eventos_de_tipo(bundle: dict, tipo: str) -> list[dict]:
    return [e for e in bundle.get("eventos") or [] if e.get("tipo") == tipo]


# Los cinco valores del ciclo operativo, con la condición que los deriva. El orden es de severidad
# DECLARADA y no de conveniencia: un bloqueo tapa todo lo demás porque la corrida no siguió; una
# corrida sin despacho no tiene ciclo que juzgar; y un presupuesto vencido con un proceso vivo es
# peor que una degradación, porque además deja algo corriendo. T6 somete este orden a los casos que
# COMBINAN fallas, que es donde una prioridad arbitraria se rompe.
def _derivar_ciclo_operativo(bundle: dict) -> tuple[str, str | None]:
    """Devuelve (ciclo, causa_de_bloqueo). La causa es None salvo en `bloqueado`."""
    bloqueos = _eventos_de_tipo(bundle, "bloqueo")
    if bloqueos:
        return "bloqueado", bloqueos[0].get("detalle")
    if not _eventos_de_tipo(bundle, "despacho"):
        return "sin_eventos", None
    utilizable = _eventos_de_tipo(bundle, "resultado_utilizable")
    vivos = [r for r in bundle.get("recursos") or [] if r.get("life_state") == "vivo"]
    if not utilizable and vivos:
        return "presupuesto_vencido_con_proceso_vivo", None
    if _eventos_de_tipo(bundle, "degradacion_observada") or not utilizable:
        return "degradado", None
    return "completado", None


def derivar_estado(bundle: dict) -> tuple[dict | None, list[FallaDeDerivacion]]:
    fallas: list[FallaDeDerivacion] = []
    ciclo, causa = _derivar_ciclo_operativo(bundle)

    estado_del_reporte = (bundle.get("reporte_del_worker") or {}).get("estado")
    validez = VALIDEZ_POR_ESTADO_DEL_REPORTE.get(estado_del_reporte)
    if validez is None:
        fallas.append(FallaDeDerivacion(
            "estado.validez_del_reporte",
            f"el bundle no registra un `reporte_del_worker` interpretable: estado "
            f"{estado_del_reporte!r}"))

    veredicto = (bundle.get("veredicto_de_conformance") or {}).get("resultado")
    semantica = SEMANTICA_POR_VEREDICTO.get(veredicto)
    if semantica is None:
        fallas.append(FallaDeDerivacion(
            "estado.resultado_semantico",
            f"el bundle no registra un `veredicto_de_conformance` conocido: resultado "
            f"{veredicto!r}"))

    if ciclo == "bloqueado" and not causa:
        # La causa es obligatoria y sale del `detalle` del evento de bloqueo. Copiarla del campo
        # declarativo `estado_del_intento` sería tomarla de lo que la corrida dice de sí misma; y
        # rellenarla con un texto genérico dejaría un bloqueo sin causa vestido de causa.
        fallas.append(FallaDeDerivacion(
            "estado.causa_de_bloqueo",
            "el evento de bloqueo no lleva `detalle`, y la causa no se toma de otro lado"))

    if fallas:
        return None, fallas

    estado = {
        "ciclo_operativo": ciclo,
        "validez_del_reporte": validez,
        "resultado_semantico": semantica,
    }
    if causa:
        estado["causa_de_bloqueo"] = causa
    return estado, []


def derivar_estrato(bundle: dict) -> str:
    """El estrato sale del valor EFECTIVO registrado: los eventos de intervención de la identidad
    del entorno, más el evento de confirmación humana de la corrida. Se toman los dos porque son
    dos registros distintos del mismo hecho, y con que uno lo acredite el intento ya no transcurrió
    sin intervención. T8 le agrega qué muestras la EXIGEN, que se deriva de la matriz."""
    entorno = bundle.get("identidad_del_entorno") or {}
    intervenciones = entorno.get("eventos_de_intervencion_humana") or []
    if intervenciones or _eventos_de_tipo(bundle, "confirmacion_humana"):
        return "con_intervencion_humana"
    return "automatizable"


def _hecho_del_intento(bundle: dict, estado: dict) -> dict:
    """El intento, visto como hecho contable. Es lo que consumen los predicados de clase `intento`
    del vocabulario, y sus campos son los del estado derivado: contar sobre lo que el bundle
    declara en vez de sobre lo derivado dejaría la métrica midiendo la declaración."""
    return {
        "attempt_id": bundle.get("attempt_id"),
        "ciclo_operativo": estado["ciclo_operativo"],
        "validez_del_reporte": estado["validez_del_reporte"],
        "resultado_semantico": estado["resultado_semantico"],
    }


def _conteos_de_la_tasa(entradas: dict, hechos: list, predicados: dict) -> tuple[int, int] | None:
    """Numerador y denominador de un cociente. El valor lo sigue produciendo el resolvedor del
    vocabulario —esta función no lo recalcula—: acá salen los dos conteos que la tasa necesita para
    ser auditable, y el llamador comprueba que dividirlos dé exactamente el valor resuelto."""
    numerador = predicados.get(entradas.get("predicado_numerador"))
    denominador = predicados.get(entradas.get("predicado_denominador"))
    if numerador is None or denominador is None:
        return None
    elegibles = [h for h in hechos if _predicado_satisface(denominador, h)]
    if not elegibles:
        return None
    return sum(1 for h in elegibles if _predicado_satisface(numerador, h)), len(elegibles)


def _hechos_de_la_metrica(clase: str, bundle: dict, hecho_del_intento: dict,
                          trabajo_delegado_id: str | None) -> list:
    if clase == "intento":
        return [hecho_del_intento]
    if clase == "recurso":
        return list(bundle.get("recursos") or [])
    if clase != "evento":
        return []
    eventos = [{**e, "detalle": identidad_de_hallazgo(e.get("detalle"))}
               if e.get("tipo") == "hallazgo_emitido" and "detalle" in e else e
               for e in bundle.get("eventos") or []]
    if trabajo_delegado_id is None:
        return eventos
    # Una métrica de sede `trabajo_delegado` ve los eventos de SU trabajo más los de la corrida
    # entera —el despacho, que abre la ventana, es uno solo y no pertenece a ningún trabajo—. Sin
    # este filtro, un bundle con dos workers tiene dos eventos terminales y la fórmula no resuelve.
    return [e for e in eventos
            if e.get("trabajo_delegado_id") in (None, trabajo_delegado_id)]


def _derivar_metrica(metrica: dict, vocabulario_por_id: dict, bundle: dict,
                     hecho_del_intento: dict, trabajo_delegado_id: str | None,
                     formulas_elegidas: dict | None = None) -> dict:
    """Una entrada de `metricas`. Nunca devuelve un cero por un cálculo que no cerró: la variante
    sin `valor` lleva su adjudicación escrita, que es lo que AC-21 exige."""
    metrica_id = metrica.get("metrica_id")
    categoria = vocabulario_por_id["categoria_de"][metrica_id]
    admitidas = metrica.get("formulas_admitidas") or []

    sin_observacion = {
        "metrica_id": metrica_id,
        "categoria": categoria,
    }
    # Quién elige la fórmula: el pre-registro, dentro del enum que la métrica admite (decisión
    # heredada 13). El instrumento la resuelve cuando la métrica admite una sola —ahí no hay nada
    # que elegir— y en ningún otro caso: elegir por defecto sería fijar metodología desde donde no
    # corresponde, y es lo que el pre-registro existe para impedir.
    elegida = (formulas_elegidas or {}).get(metrica_id)
    if elegida is not None and elegida not in admitidas:
        return {**sin_observacion, "estado_de_medicion": "bloqueada",
                "adjudicacion": f"el pre-registro elige «{elegida}», que esta métrica no admite"}
    if elegida is None:
        if len(admitidas) != 1:
            return {**sin_observacion, "estado_de_medicion": "no_observada",
                    "adjudicacion": f"la métrica admite {len(admitidas)} fórmulas y el "
                                    "pre-registro no eligió: la metodología no la fija el "
                                    "instrumento"}
        elegida = admitidas[0]

    formula = vocabulario_por_id["formulas"].get(elegida) or {}
    resolvedor = RESOLVEDORES_DE_FORMA.get(formula.get("forma"))
    if resolvedor is None:
        return {**sin_observacion, "estado_de_medicion": "bloqueada",
                "adjudicacion": f"la fórmula «{elegida}» no tiene resolvedor implementado"}

    hechos = _hechos_de_la_metrica(formula.get("clase_de_hecho"), bundle, hecho_del_intento,
                                   trabajo_delegado_id)
    entradas = metrica.get("entradas") or {}
    valor, error = resolvedor(entradas, hechos, vocabulario_por_id["predicados"])
    if error is not None:
        return {**sin_observacion, "estado_de_medicion": "bloqueada", "adjudicacion": error}

    medida = {**sin_observacion, "estado_de_medicion": "medida", "valor": valor,
              "unidad": metrica.get("unidad")}
    if metrica.get("publicacion") != "tasa":
        return medida
    conteos = _conteos_de_la_tasa(entradas, hechos, vocabulario_por_id["predicados"])
    if conteos is None or not _casi_igual(conteos[0] / conteos[1], valor):
        # Si los conteos no reproducen el valor que resolvió el vocabulario, la tasa no es
        # auditable: publicarla igual sería publicar un cociente que sus propios términos no dan.
        return {**sin_observacion, "estado_de_medicion": "bloqueada",
                "adjudicacion": "el numerador y el denominador no reproducen la tasa resuelta"}
    return {**medida, "numerador": float(conteos[0]), "denominador": float(conteos[1])}


def _indice_del_vocabulario(vocabulario: dict) -> dict:
    categoria_de: dict[str, str] = {}
    por_sede: dict[str, list[dict]] = {"corrida": [], "trabajo_delegado": []}
    for categoria, metrica in _metricas_del(vocabulario):
        categoria_de[metrica.get("metrica_id")] = categoria.get("categoria")
        por_sede.setdefault(metrica.get("sede"), []).append(metrica)
    return {
        "categoria_de": categoria_de,
        "por_sede": por_sede,
        "formulas": _por_id(vocabulario.get("formulas") or [], "formula_id"),
        "predicados": _por_id(vocabulario.get("predicados") or [], "predicado_id"),
    }


def derivar_observacion(bundle: dict, bundle_sha256: str, vocabulario: dict,
                        schema_observacion: dict,
                        reglas_de_identidad: dict | None = None,
                        formulas_elegidas: dict | None = None) -> tuple[dict | None,
                                                                       list[FallaDeDerivacion]]:
    """El bundle entra, la observación sale. Todo campo tiene su hecho de origen acá adentro.

    `reglas_de_identidad` son las que el pre-registro congela: con ellas, `observation_id` sale de
    la plantilla congelada y no de la forma por defecto del recolector."""
    estado, fallas = derivar_estado(bundle)
    if estado is None:
        return None, fallas

    indice = _indice_del_vocabulario(vocabulario)
    hecho = _hecho_del_intento(bundle, estado)

    observacion = {
        "version_schema": schema_observacion.get("x-version"),
        "observation_id": derivar_observation_id(bundle, reglas_de_identidad),
        "sample_id": bundle.get("sample_id"),
        "attempt_id": bundle.get("attempt_id"),
        "attempt_ordinal": bundle.get("attempt_ordinal"),
        "preregistro_sha256": bundle.get("preregistro_sha256"),
        "procedencia": {"run_id": bundle.get("run_id"), "bundle_sha256": bundle_sha256},
        "punto_de_despacho": bundle.get("punto_de_despacho"),
        "skill": bundle.get("skill"),
        "familia_de_rol": bundle.get("familia_de_rol"),
        "transporte": bundle.get("transporte"),
        "estrato": derivar_estrato(bundle),
        "estado": estado,
        "metricas": [_derivar_metrica(m, indice, bundle, hecho, None, formulas_elegidas)
                     for m in indice["por_sede"]["corrida"]],
        "trabajos_delegados": [
            {
                "trabajo_delegado_id": trabajo.get("trabajo_delegado_id"),
                # El estado terminal se copia tal cual: es un hecho que el runner comprobó al
                # capturar, no algo que el recolector pueda reinterpretar. Cuando no está
                # comprobado, la latencia terminal cae sola en su variante sin valor, porque el
                # evento que la cierra no existe.
                "estado_terminal": trabajo.get("estado_terminal"),
                "metricas": [_derivar_metrica(m, indice, bundle, hecho,
                                              trabajo.get("trabajo_delegado_id"),
                                              formulas_elegidas)
                             for m in indice["por_sede"]["trabajo_delegado"]],
            }
            for trabajo in bundle.get("trabajos_delegados") or []
        ],
    }

    # La observación se valida contra su propio contrato antes de salir. Un recolector que emite
    # algo que el schema rechaza deja el error para el paso siguiente, y ahí ya no se sabe si lo
    # produjo la derivación o la escritura.
    errores = validar(observacion, schema_observacion)
    if errores:
        return None, [FallaDeDerivacion(fmt(e.ruta), e.mensaje) for e in errores]
    return observacion, []


def _cargar_insumos_de_recoleccion() -> tuple[dict, dict, list[str]]:
    """Los dos contratos y el vocabulario que la recolección necesita, con sus errores de carga."""
    problemas: list[str] = []
    vocabulario, error = _cargar_json(RUTA_VOCABULARIO)
    if error:
        problemas.append(f"vocabulario de métricas: {error}")
    esquemas: dict[str, dict] = {}
    for nombre in ("bundle-corrida", "observacion"):
        datos, error = _cargar_json(CONTRATOS_POR_NOMBRE[nombre].ruta)
        if error:
            problemas.append(f"schema de {nombre}: {error}")
        else:
            esquemas[nombre] = datos
    return vocabulario or {}, esquemas, problemas


def _ruta_absoluta(valor: str) -> Path:
    ruta = Path(valor)
    return ruta if ruta.is_absolute() else RAIZ / ruta


def modo_validar_bundles(args: argparse.Namespace) -> int:
    raiz = _ruta_absoluta(getattr(args, "validar_bundles"))
    _, esquemas, problemas = _cargar_insumos_de_recoleccion()
    if "bundle-corrida" not in esquemas:
        for p in problemas:
            print(f"FALLA  {p}")
        return 1

    bundles = leer_conjunto_de_bundles(raiz)
    print(f"Conjunto: {raiz} — {len(bundles)} corridas")
    rojas: list[str] = []
    for comprobacion in COMPROBACIONES_DE_BUNDLES:
        fallas = comprobacion.revisar(bundles, esquemas["bundle-corrida"])
        if fallas:
            rojas.append(comprobacion.clave)
            print(f"[{comprobacion.clave}] FALLA  {comprobacion.que_prueba} — {len(fallas)}:")
            for falla in fallas[:6]:
                print(f"       - {falla}")
        else:
            print(f"[{comprobacion.clave}] OK     {comprobacion.que_prueba}")

    print()
    if rojas:
        print(f"RESULTADO: FALLA — comprobaciones en rojo: {', '.join(rojas)}")
        return 1
    print(f"RESULTADO: OK — {len(bundles)} bundles pasan las "
          f"{len(COMPROBACIONES_DE_BUNDLES)} comprobaciones")
    return 0


def modo_recolectar(args: argparse.Namespace) -> int:
    crudo = getattr(args, "bundle", None)  # el modo se selecciona con `--recolectar`; el insumo
    if not crudo:                          # viaja en `--bundle`, que es su auxiliar obligatoria
        print("FALLA  `--recolectar` necesita `--bundle <ruta-de-la-corrida>`", file=sys.stderr)
        return 2
    directorio = _ruta_absoluta(crudo)

    vocabulario, esquemas, problemas = _cargar_insumos_de_recoleccion()
    if problemas:
        for p in problemas:
            print(f"FALLA  {p}")
        return 1

    bundle = _leer_bundle(directorio)
    if bundle.error:
        print(f"FALLA  {directorio.name}: {bundle.error}")
        return 1
    errores = validar(bundle.datos, esquemas["bundle-corrida"])
    if errores:
        print(f"FALLA  {directorio.name}: el bundle no valida contra su contrato — "
              f"{len(errores)} errores")
        for e in errores[:6]:
            print(f"       - {e}")
        return 1

    # En producción el pre-registro ya está congelado y es quien fija las reglas de identidad y la
    # fórmula de cada métrica. Antes de que exista, el recolector deriva igual y deja constancia de
    # lo que no pudo resolver: bloquear del todo impediría probar el instrumento contra fixtures.
    preregistro, _ = _cargar_json(RAIZ / RUTA_PREREGISTRO_FASE_0)
    preregistro = preregistro if isinstance(preregistro, dict) else {}
    observacion, fallas = derivar_observacion(
        bundle.datos, bundle.sha256, vocabulario, esquemas["observacion"],
        preregistro.get("reglas_de_derivacion_de_identidad"),
        formulas_del_preregistro(preregistro))
    if observacion is None:
        print(f"FALLA  {directorio.name}: la observación no se pudo derivar del bundle — "
              f"{len(fallas)} campos sin hecho de origen:")
        for falla in fallas[:8]:
            print(f"       - {falla}")
        return 1

    salida = getattr(args, "salida", None)
    ruta = (_ruta_absoluta(salida) if salida
            else DIR_OBSERVACIONES_FASE_0 / f"{bundle.datos['run_id']}.json")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(observacion, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")

    medidas = [m for m in observacion["metricas"] if m["estado_de_medicion"] == "medida"]
    sin_valor = [m for m in observacion["metricas"] if m["estado_de_medicion"] != "medida"]
    print(f"OK     {bundle.datos['run_id']} → {ruta}")
    print(f"       procedencia: bundle_sha256 {bundle.sha256}")
    print(f"       estado: {observacion['estado']['ciclo_operativo']} · "
          f"{observacion['estado']['validez_del_reporte']} · "
          f"{observacion['estado']['resultado_semantico']} · estrato "
          f"{observacion['estrato']}")
    print(f"       métricas de la corrida: {len(medidas)} medidas, {len(sin_valor)} sin "
          f"observación y con su adjudicación escrita")
    for metrica in sin_valor:
        print(f"       - {metrica['metrica_id']}: {metrica['estado_de_medicion']} — "
              f"{metrica['adjudicacion']}")
    print(f"       trabajos delegados: {len(observacion['trabajos_delegados'])}")
    return 0


# --- `--autotest-bundles`. El corpus NO se valida contra sí mismo (D-16): el manifest declara
# aparte qué conjuntos tienen que existir y con qué resultado, y se compara con el disco en las dos
# direcciones. ---

def _conjuntos_en_disco() -> set[str]:
    raiz = DIR_FIXTURES_BUNDLES / "conjuntos"
    if not raiz.is_dir():
        return set()
    return {hijo.name for hijo in raiz.iterdir() if hijo.is_dir()}


def _revisar_conjunto(nombre: str, schema: dict) -> set[str]:
    """Las claves de las comprobaciones que se ponen rojas sobre este conjunto."""
    bundles = leer_conjunto_de_bundles(DIR_FIXTURES_BUNDLES / "conjuntos" / nombre)
    return {c.clave for c in COMPROBACIONES_DE_BUNDLES if c.revisar(bundles, schema)}


class MutanteDeRecoleccion(NamedTuple):
    nombre: str
    que_rompe: str
    aplicar: Callable[[dict], bool]


def _mut_borrar_evento_utilizable(bundle: dict) -> bool:
    # Solo ejerce a una corrida que completó: donde ya hay una degradación o un bloqueo, el ciclo
    # no depende del resultado utilizable y quitarlo daría un verde que no probó nada.
    if _eventos_de_tipo(bundle, "degradacion_observada") or _eventos_de_tipo(bundle, "bloqueo"):
        return False
    eventos = bundle.get("eventos") or []
    for i, evento in enumerate(eventos):
        if evento.get("tipo") == "resultado_utilizable":
            del eventos[i]
            return True
    return False


def _mut_reporte_a_interpretable(bundle: dict) -> bool:
    reporte = bundle.get("reporte_del_worker") or {}
    if reporte.get("estado") == "interpretable":
        return False
    bundle["reporte_del_worker"] = {
        "estado": "interpretable",
        "ruta_relativa": "arboles-desechables/mutante/salida.md",
        "sha256": "0" * 64,
    }
    return True


def _mut_recurso_a_vivo(bundle: dict) -> bool:
    recursos = bundle.get("recursos") or []
    # Solo ejerce a una corrida cuya limpieza esté completa: donde ya hay un recurso sin cese
    # comprobado, la métrica vale 0 antes de mutar y el mutante daría un verde que no probó nada.
    if not recursos or any(r.get("life_state") != "terminado_comprobado" for r in recursos):
        return False
    recursos[0]["life_state"] = "vivo"
    return True


def _mut_agregar_intervencion_humana(bundle: dict) -> bool:
    entorno = bundle.get("identidad_del_entorno") or {}
    if entorno.get("eventos_de_intervencion_humana"):
        return False
    entorno["eventos_de_intervencion_humana"] = ["evt-confirmacion-inyectada"]
    return True


def _mut_veredicto_a_incorrecto(bundle: dict) -> bool:
    veredicto = bundle.get("veredicto_de_conformance") or {}
    if veredicto.get("resultado") == "incorrecto":
        return False
    bundle["veredicto_de_conformance"] = {
        "resultado": "incorrecto",
        "evidencia": "mutante: la salida no trae las secciones que la receta exige",
    }
    return True


# Cada mutante altera UN hecho del bundle y nombra qué campo derivado tiene que moverse con él. Es
# el control que prueba que la derivación lee el hecho en vez de copiar una declaración: si el
# campo no cambia, el recolector no lo estaba derivando de ahí.
MUTANTES_DE_RECOLECCION: tuple[tuple[MutanteDeRecoleccion, str], ...] = (
    (MutanteDeRecoleccion("sin-resultado-utilizable",
                          "la corrida deja de tener su evento de resultado utilizable",
                          _mut_borrar_evento_utilizable), "estado.ciclo_operativo"),
    (MutanteDeRecoleccion("reporte-interpretable",
                          "el reporte del worker pasa a ser interpretable",
                          _mut_reporte_a_interpretable), "estado.validez_del_reporte"),
    (MutanteDeRecoleccion("recurso-vivo", "un recurso queda vivo en lugar de terminado",
                          _mut_recurso_a_vivo), "metricas.limpieza-completa"),
    (MutanteDeRecoleccion("con-intervencion-humana",
                          "la identidad del entorno registra una intervención",
                          _mut_agregar_intervencion_humana), "estrato"),
    (MutanteDeRecoleccion("veredicto-incorrecto", "el veredicto de conformance pasa a incorrecto",
                          _mut_veredicto_a_incorrecto), "estado.resultado_semantico"),
)


def _proyectar_campo(observacion: dict, campo: str) -> Any:
    if campo == "estrato":
        return observacion.get("estrato")
    if campo.startswith("estado."):
        return (observacion.get("estado") or {}).get(campo.split(".", 1)[1])
    if campo.startswith("metricas."):
        buscado = campo.split(".", 1)[1]
        for metrica in observacion.get("metricas") or []:
            if metrica.get("metrica_id") == buscado:
                return (metrica.get("estado_de_medicion"), metrica.get("valor"))
    return None


def modo_autotest_bundles(args: argparse.Namespace) -> int:
    del args
    manifest, error = _cargar_json(RUTA_MANIFEST_BUNDLES)
    if error:
        print(f"[A] FALLA  manifest del corpus de bundles: {error}")
        return 1
    vocabulario, esquemas, problemas = _cargar_insumos_de_recoleccion()
    if problemas:
        for p in problemas:
            print(f"[A] FALLA  {p}")
        return 1
    schema_bundle = esquemas["bundle-corrida"]
    schema_observacion = esquemas["observacion"]

    resultados: list[tuple[str, bool, str]] = []
    conjuntos = manifest.get("conjuntos") or []
    recolecciones = manifest.get("recolecciones") or []

    # [A] Manifest ↔ disco, en las dos direcciones. Un conjunto borrado tiene que poner esto rojo,
    # no reducir en silencio lo que el modo comprueba.
    declarados = {c["conjunto"] for c in conjuntos}
    en_disco = _conjuntos_en_disco()
    diferencias = [f"declarado y ausente del disco: {c}" for c in sorted(declarados - en_disco)]
    diferencias += [f"en disco y no declarado: {c}" for c in sorted(en_disco - declarados)]
    resultados.append(("A", not diferencias,
                       f"manifest ↔ directorio ({len(declarados)} conjuntos)" if not diferencias
                       else " | ".join(diferencias[:6])))

    # [B] Cada comprobación registrada tiene al menos un conjunto que la pone roja. Una
    # comprobación sin negativo es una comprobación que nadie probó que pueda fallar.
    ejercidas = {clave for c in conjuntos for clave in c.get("claves_esperadas") or []}
    sin_negativo = [c.clave for c in COMPROBACIONES_DE_BUNDLES if c.clave not in ejercidas]
    inexistentes = sorted(ejercidas - {c.clave for c in COMPROBACIONES_DE_BUNDLES})
    problemas_de_cobertura = [f"la comprobación {c} no la ejerce ningún conjunto"
                              for c in sin_negativo]
    problemas_de_cobertura += [f"el manifest espera una comprobación inexistente: {c}"
                               for c in inexistentes]
    resultados.append(("B", not problemas_de_cobertura,
                       f"las {len(COMPROBACIONES_DE_BUNDLES)} comprobaciones tienen quien las "
                       "ponga rojas" if not problemas_de_cobertura
                       else " | ".join(problemas_de_cobertura[:6])))

    # [C] Cada conjunto se pone rojo exactamente en las comprobaciones que declara, ni una más ni
    # una menos. Un negativo que además falla en otra cláusula deja la suya sin probar.
    fallas_de_conjunto: list[str] = []
    for entrada in conjuntos:
        esperadas = set(entrada.get("claves_esperadas") or [])
        obtenidas = _revisar_conjunto(entrada["conjunto"], schema_bundle)
        if obtenidas != esperadas:
            fallas_de_conjunto.append(
                f"{entrada['conjunto']}: esperaba rojas {sorted(esperadas) or '∅'} y se pusieron "
                f"rojas {sorted(obtenidas) or '∅'}")
    resultados.append(("C", not fallas_de_conjunto,
                       f"{len(conjuntos)} conjuntos se ponen rojos donde deben"
                       if not fallas_de_conjunto else " | ".join(fallas_de_conjunto[:4])))

    # [D] La recolección sobre cada corrida declarada da el estado y el reparto de métricas que el
    # manifest espera. Es el control positivo: sin él, un recolector que fallara siempre pasaría
    # todos los negativos.
    fallas_de_recoleccion: list[str] = []
    observaciones: dict[str, dict] = {}
    for entrada in recolecciones:
        directorio = DIR_FIXTURES_BUNDLES / "conjuntos" / entrada["conjunto"] / entrada["corrida"]
        bundle = _leer_bundle(directorio)
        etiqueta = f"{entrada['conjunto']}/{entrada['corrida']}"
        if bundle.error:
            fallas_de_recoleccion.append(f"{etiqueta}: {bundle.error}")
            continue
        observacion, fallas = derivar_observacion(bundle.datos, bundle.sha256, vocabulario,
                                                  schema_observacion)
        if entrada.get("no_derivable"):
            if observacion is not None:
                fallas_de_recoleccion.append(
                    f"{etiqueta}: la observación se derivó y no debería — "
                    f"{entrada['no_derivable']}")
            elif not any(entrada["campo_sin_origen"] == f.campo for f in fallas):
                fallas_de_recoleccion.append(
                    f"{etiqueta}: falla, pero no en `{entrada['campo_sin_origen']}` — "
                    f"lo que se vio: {fallas[0]}")
            continue
        if observacion is None:
            fallas_de_recoleccion.append(f"{etiqueta}: no se derivó — {fallas[0]}")
            continue
        observaciones[etiqueta] = observacion
        esperado = entrada["estado_esperado"]
        obtenido = {k: v for k, v in observacion["estado"].items() if k in esperado}
        if obtenido != esperado:
            fallas_de_recoleccion.append(f"{etiqueta}: estado {obtenido} y se esperaba {esperado}")
        if observacion["estrato"] != entrada["estrato_esperado"]:
            fallas_de_recoleccion.append(
                f"{etiqueta}: estrato {observacion['estrato']!r} y se esperaba "
                f"{entrada['estrato_esperado']!r}")
        # Una métrica sin observación NUNCA lleva `valor`: es el schema el que lo impide, y este
        # control comprueba que el recolector se apoye en esa variante en vez de escribir un cero.
        sin_valor = {m["metrica_id"] for m in observacion["metricas"]
                     if m["estado_de_medicion"] != "medida"}
        if sin_valor != set(entrada["metricas_sin_observacion"]):
            fallas_de_recoleccion.append(
                f"{etiqueta}: sin observación {sorted(sin_valor)} y se esperaba "
                f"{sorted(entrada['metricas_sin_observacion'])}")
        con_cero = [m["metrica_id"] for m in observacion["metricas"]
                    if m["estado_de_medicion"] != "medida" and "valor" in m]
        if con_cero:
            fallas_de_recoleccion.append(f"{etiqueta}: métricas sin observación con valor escrito: "
                                         f"{con_cero}")
    resultados.append(("D", not fallas_de_recoleccion,
                       f"{len(recolecciones)} recolecciones dan el estado y el reparto declarados"
                       if not fallas_de_recoleccion else " | ".join(fallas_de_recoleccion[:4])))

    # [E] La derivación se mueve con el hecho. Sobre una COPIA en memoria de cada corrida del
    # control positivo —mutar el archivo del árbol dejaría el repo mutado si el proceso muere—,
    # cada mutante altera un hecho y el campo que ese hecho deriva tiene que cambiar. Si no cambia,
    # el recolector no lo estaba derivando de ahí: lo estaba copiando de algún otro lado.
    fallas_de_mutacion: list[str] = []
    ejercidos: set[str] = set()
    for etiqueta, base in observaciones.items():
        conjunto, corrida = etiqueta.split("/")
        bundle = _leer_bundle(DIR_FIXTURES_BUNDLES / "conjuntos" / conjunto / corrida)
        for mutante, campo in MUTANTES_DE_RECOLECCION:
            copia = copy.deepcopy(bundle.datos)
            if not mutante.aplicar(copia):
                continue  # el hecho ya estaba en ese valor: esta corrida no ejerce este mutante
            ejercidos.add(mutante.nombre)
            if validar(copia, schema_bundle):
                fallas_de_mutacion.append(f"{etiqueta}/{mutante.nombre}: la mutación deja el "
                                          "bundle fuera de su contrato y no prueba nada")
                continue
            mutada, _ = derivar_observacion(copia, bundle.sha256, vocabulario, schema_observacion)
            if mutada is None:
                continue  # la mutación hace inderivable la observación: el rojo es igual de válido
            if _proyectar_campo(mutada, campo) == _proyectar_campo(base, campo):
                fallas_de_mutacion.append(
                    f"{etiqueta}/{mutante.nombre}: {mutante.que_rompe} y `{campo}` no se mueve")
    # Un mutante que ninguna corrida ejerce es cobertura fantasma: aparece en la tabla, no corre
    # nunca, y el verde de este control se lee como si lo hubiera probado.
    fallas_de_mutacion += [f"el mutante «{m.nombre}» no lo ejerce ninguna corrida del corpus"
                           for m, _ in MUTANTES_DE_RECOLECCION if m.nombre not in ejercidos]
    resultados.append(("E", not fallas_de_mutacion,
                       f"{len(MUTANTES_DE_RECOLECCION)} mutantes ejercidos, y cada uno mueve el "
                       "campo que deriva" if not fallas_de_mutacion
                       else " | ".join(fallas_de_mutacion[:4])))

    for etiqueta, ok, detalle in resultados:
        print(f"[{etiqueta}] {'OK    ' if ok else 'FALLA '} {detalle}")
    print()
    rojos = [e for e, ok, _ in resultados if not ok]
    if rojos:
        print(f"RESULTADO: FALLA — controles en rojo: {', '.join(rojos)}")
        return 1
    print(f"RESULTADO: OK — {len(resultados)} controles en verde")
    return 0


# ---------------------------------------------------------------------------------------------
# Modos `--autotest-recoleccion`, `--autotest-derivacion` y `--autotest-muestras-intentos`.
#
# Validar la ENTRADA del recolector no prueba que su TRANSFORMACIÓN sea correcta. Un recolector que
# copiara las clasificaciones que el bundle declara pasaría la validación estructural entera y
# produciría datos limpios y falsos. Estos tres modos atacan eso desde tres lados:
#
# - `--autotest-recoleccion` — un golden bundle → observación esperada, comparado CAMPO POR CAMPO,
#   más los mutantes de transformación: clasificación copiada de un campo declarativo, identidad
#   alterada, evento omitido y dato incorporado que el bundle no contiene.
# - `--autotest-derivacion` — una observación se prueba derivada RE-EJECUTANDO el recolector sobre
#   su bundle y comparando byte a byte. Nunca confiando en los campos que ella declara: una escrita
#   a mano que copia el hash y la identidad los declara igual de bien que una legítima.
# - `--autotest-muestras-intentos` — lo que el pre-registro congela son las MUESTRAS; los intentos
#   se derivan (D-12). El conjunto esperado de muestras se deriva aparte, como producto punto ×
#   repetición, y la cadena de intentos se compara contra un manifest independiente (D-16), porque
#   borrar el último intento bloqueado —o borrarlo y renumerar— deja un conjunto final válido.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_GOLDEN = DIR_SCRIPTS / "fixtures-baseline" / "golden"
RUTA_MANIFEST_GOLDEN = DIR_FIXTURES_GOLDEN / "manifest.json"

# Qué puede leer una plantilla de identidad. No se transcribe: sale del enum del schema de
# pre-registro, que es donde la lista está congelada. Una copia acá envejecería en silencio.
def _componentes_de_identidad_admitidos() -> set[str]:
    schema, error = _cargar_json(CONTRATOS_POR_NOMBRE["preregistro"].ruta)
    if error:
        return set()
    return set(((schema.get("$defs") or {}).get("enum_componente_de_identidad") or {})
               .get("enum") or [])


_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def contexto_de_identidad(bundle: dict) -> dict:
    """Los valores con los que se resuelve una plantilla. Salen del bundle y de ningún otro lado:
    una identidad que se alimentara del orden de llegada de los archivos no sería derivada."""
    return {
        "sample_id": bundle.get("sample_id"),
        "attempt_id": bundle.get("attempt_id"),
        "attempt_ordinal": bundle.get("attempt_ordinal"),
        "punto_de_despacho": bundle.get("punto_de_despacho"),
        "run_id": bundle.get("run_id"),
        "repeticion": bundle.get("repeticion"),
    }


def aplicar_regla_de_identidad(regla: dict, contexto: dict) -> tuple[str | None, str | None]:
    """Resuelve la plantilla congelada. `componentes` es el conjunto cerrado de lo que la plantilla
    puede leer, así que se exige que coincida EXACTAMENTE con los marcadores que usa: un marcador
    no declarado es una entrada que el acta no congeló, y un componente declarado que la plantilla
    no usa es una declaración que no restringe nada."""
    plantilla = regla.get("plantilla")
    if not isinstance(plantilla, str) or not plantilla:
        return None, "la regla no declara plantilla"
    declarados = set(regla.get("componentes") or [])
    admitidos = _componentes_de_identidad_admitidos()
    if admitidos and not declarados <= admitidos:
        return None, (f"componentes fuera del vocabulario congelado: "
                      f"{sorted(declarados - admitidos)}")
    usados = set(_PLACEHOLDER.findall(plantilla))
    if usados != declarados:
        return None, (f"la plantilla usa {sorted(usados)} y declara {sorted(declarados)}: "
                      "no coinciden")
    faltantes = [c for c in usados if contexto.get(c) is None]
    if faltantes:
        return None, f"el bundle no aporta {sorted(faltantes)}"
    return plantilla.format(**{c: contexto[c] for c in usados}), None


def derivar_identidades(bundle: dict, reglas: dict) -> tuple[dict, list[str]]:
    """Las tres identidades de D-12. `sample_id` y `attempt_id` los trae el bundle —el runner los
    fija antes de despachar— y `observation_id` lo produce la regla congelada. Que las tres sean
    DISTINTAS entre sí no es cosmético: el caso barato es un solo `run_id` haciendo de las tres, y
    ahí un reintento legítimo y una observación duplicada dejan de distinguirse."""
    problemas: list[str] = []
    contexto = contexto_de_identidad(bundle)
    identidades = {"sample_id": bundle.get("sample_id"), "attempt_id": bundle.get("attempt_id")}

    for campo in ("attempt_id", "observation_id"):
        valor, error = aplicar_regla_de_identidad(reglas.get(campo) or {}, contexto)
        if error:
            problemas.append(f"{campo}: {error}")
            continue
        if campo == "observation_id":
            identidades["observation_id"] = valor
        elif valor != bundle.get("attempt_id"):
            problemas.append(f"attempt_id: el bundle declara {bundle.get('attempt_id')!r} y la "
                             f"regla congelada produce {valor!r}")

    distintas = {k: v for k, v in identidades.items() if v is not None}
    if len(set(distintas.values())) != len(distintas):
        problemas.append(f"las tres identidades no son distintas entre sí: {distintas}")
    return identidades, problemas


# --- La política de reintentos, aplicada. Declararla y no ejecutarla la deja a interpretación de
# quien publique el número, que es exactamente lo que D-12 existe para impedir. ---

# Qué disparador del conjunto cerrado justifica reintentar después de un intento así. Es una tabla
# y no un juicio: sin ella, «mutar un disparador» no cambiaría ningún resultado y la política
# quedaría declarada sin aplicarse.
def disparador_del_intento(estado: dict) -> str | None:
    ciclo = estado.get("ciclo_operativo")
    if ciclo == "bloqueado":
        return "bloqueo_de_aislamiento"
    if ciclo == "presupuesto_vencido_con_proceso_vivo":
        return "presupuesto_vencido"
    if ciclo == "sin_eventos":
        return "error_de_transporte"
    if estado.get("validez_del_reporte") in ("malformado", "ausente"):
        return "salida_invalida"
    return None  # un intento que completó con reporte válido no habilita ningún reintento


def comprobar_cadena_de_intentos(sample_id: str, observaciones: list[dict],
                                 politica: dict) -> list[str]:
    """La cadena de una muestra contra la política congelada: ordinales sin huecos, tope de
    intentos, cada reintento con su disparador admitido y la terminación respetada."""
    problemas: list[str] = []
    ordenadas = sorted(observaciones, key=lambda o: o.get("attempt_ordinal", 0))
    ordinales = [o.get("attempt_ordinal") for o in ordenadas]
    if ordinales != list(range(1, len(ordenadas) + 1)):
        problemas.append(f"{sample_id}: la cadena de intentos es {ordinales} y tiene que ser "
                         f"1..{len(ordenadas)} sin huecos")

    maximo = politica.get("maximo_de_intentos_por_muestra")
    if isinstance(maximo, int) and len(ordenadas) > maximo:
        problemas.append(f"{sample_id}: {len(ordenadas)} intentos y la política congela un máximo "
                         f"de {maximo}")

    admitidos = set(politica.get("disparadores") or [])
    for previa, siguiente in zip(ordenadas, ordenadas[1:]):
        disparador = disparador_del_intento(previa.get("estado") or {})
        ordinal = siguiente.get("attempt_ordinal")
        if disparador is None:
            problemas.append(f"{sample_id}: el intento {ordinal} reintenta sobre uno que completó "
                             "con reporte válido, y eso no lo habilita ningún disparador")
        elif disparador not in admitidos:
            problemas.append(f"{sample_id}: el intento {ordinal} reintenta por «{disparador}», que "
                             f"la política congelada no admite ({sorted(admitidos) or '∅'})")

    terminacion = politica.get("condicion_de_terminacion")
    if terminacion == "sin_reintento" and len(ordenadas) > 1:
        problemas.append(f"{sample_id}: {len(ordenadas)} intentos y la política termina "
                         "«sin_reintento»")
    if terminacion == "primer_intento_valido":
        for previa, siguiente in zip(ordenadas, ordenadas[1:]):
            if (previa.get("estado") or {}).get("validez_del_reporte") == "valido":
                problemas.append(
                    f"{sample_id}: el intento {siguiente.get('attempt_ordinal')} viene después de "
                    "uno con reporte válido, y la política termina en el primero válido")
    return problemas


def _metrica_de_la_observacion(observacion: dict, metrica_id: str) -> dict | None:
    for metrica in observacion.get("metricas") or []:
        if metrica.get("metrica_id") == metrica_id:
            return metrica
    return None


def aplicar_seleccion_por_metrica(metrica_id: str, observaciones: list[dict], politica: dict,
                                  vocabulario: dict) -> tuple[float | None, str | None]:
    """Con qué intento se publica esta métrica. La regla la congela el acta; elegirla después de
    ver los números es quedarse con el intento favorable, y las filas seguirían verdes porque
    estarían validando esa misma elección no congelada."""
    regla = next((s.get("regla") for s in politica.get("seleccion_por_metrica") or []
                  if s.get("metrica_id") == metrica_id), None)
    if regla is None:
        return None, f"la política congelada no declara regla de selección para «{metrica_id}»"
    ordenadas = sorted(observaciones, key=lambda o: o.get("attempt_ordinal", 0))

    if regla == "agregacion":
        metrica = next((m for _, m in _metricas_del(vocabulario)
                        if m.get("metrica_id") == metrica_id), None)
        if metrica is None:
            return None, f"«{metrica_id}» no está en el vocabulario"
        resolvedor = RESOLVEDORES_DE_AGREGACION.get(
            (_por_id(vocabulario.get("agregaciones") or [], "agregacion_id")
             .get(metrica.get("agregacion")) or {}).get("forma"))
        if resolvedor is None:
            return None, f"la agregación de «{metrica_id}» no tiene resolvedor"
        valores = []
        for observacion in ordenadas:
            medida = _metrica_de_la_observacion(observacion, metrica_id) or {}
            if medida.get("estado_de_medicion") != "medida":
                continue
            valores.append([medida.get("numerador"), medida.get("denominador")]
                           if "numerador" in medida else medida.get("valor"))
        return resolvedor(valores)

    if regla == "primer_intento_valido":
        elegidas = [o for o in ordenadas
                    if (o.get("estado") or {}).get("validez_del_reporte") == "valido"]
    elif regla == "primer_intento":
        elegidas = ordenadas[:1]
    elif regla == "ultimo_intento":
        elegidas = ordenadas[-1:]
    else:
        return None, f"regla de selección no implementada: «{regla}»"

    if not elegidas:
        return None, f"ningún intento satisface la regla «{regla}»"
    medida = _metrica_de_la_observacion(elegidas[0], metrica_id) or {}
    if medida.get("estado_de_medicion") != "medida":
        return None, (f"el intento elegido por «{regla}» no tiene la métrica medida: "
                      f"{medida.get('adjudicacion', 'no está en la observación')}")
    return medida.get("valor"), None


def derivar_muestras_esperadas(preregistro: dict, declaracion: dict) -> list[str]:
    """El conjunto esperado de `sample_id`, derivado APARTE como producto punto × repetición.

    Los puntos salen de `cobertura.puntos_observados` del pre-registro y las repeticiones, de la
    DECLARACIÓN INDEPENDIENTE —igual que la plantilla con la que se arma cada identidad—. Derivar
    las repeticiones de la propia lista de muestras sería contarlas sobre el conjunto que se quiere
    validar: quitar una muestra bajaría el máximo, el producto la dejaría de esperar y la ausencia
    no se vería (D-16)."""
    plantilla = declaracion.get("plantilla_de_sample_id") or "mst-{punto_de_despacho}-r{repeticion}"
    repeticiones = declaracion.get("repeticiones_por_punto") or {}
    esperadas: list[str] = []
    for punto in (preregistro.get("cobertura") or {}).get("puntos_observados") or []:
        for repeticion in range(1, (repeticiones.get(punto) or 0) + 1):
            esperadas.append(plantilla.format(punto_de_despacho=punto, repeticion=repeticion))
    return esperadas


# --- Los tres modos. ---

def _cargar_corpus_golden() -> tuple[dict, dict, dict, dict, list[str]]:
    """Manifest, pre-registro, vocabulario y schemas del corpus golden."""
    problemas: list[str] = []
    manifest, error = _cargar_json(RUTA_MANIFEST_GOLDEN)
    if error:
        problemas.append(f"manifest del corpus golden: {error}")
    preregistro, error = _cargar_json(DIR_FIXTURES_GOLDEN / "preregistro.json")
    if error:
        problemas.append(f"pre-registro del corpus golden: {error}")
    vocabulario, esquemas, mas = _cargar_insumos_de_recoleccion()
    return manifest or {}, preregistro or {}, vocabulario, esquemas, problemas + mas


def _bundle_golden(run_id: str) -> BundleEnDisco:
    return _leer_bundle(DIR_FIXTURES_GOLDEN / "bundles" / run_id)


def formulas_del_preregistro(preregistro: dict) -> dict:
    """Qué fórmula eligió el acta para cada métrica. Es lo que el recolector resuelve en lugar de
    elegir: el acta escoge dentro del enum que la métrica admite y no lo amplía."""
    return {m.get("metrica_id"): m.get("formula_id")
            for m in preregistro.get("metricas") or [] if m.get("formula_id")}


def serializar_observacion(observacion: dict) -> bytes:
    """La forma canónica en la que el recolector escribe una observación. Está acá para que
    «comparar byte a byte» compare contra lo mismo que se escribe, y no contra otra serialización
    que casualmente coincida."""
    return (json.dumps(observacion, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _diferencias_de_campo(esperada: dict, obtenida: dict, prefijo: str = "") -> list[str]:
    """Campo por campo, y no una igualdad global: un golden que solo dice «no coincide» obliga a
    diffear a mano justo cuando lo que importa es qué transformación se movió."""
    diferencias: list[str] = []
    for clave in sorted(set(esperada) | set(obtenida)):
        ruta = f"{prefijo}{clave}"
        if clave not in esperada:
            diferencias.append(f"{ruta}: sobra en lo obtenido ({obtenida[clave]!r})")
        elif clave not in obtenida:
            diferencias.append(f"{ruta}: falta en lo obtenido (esperaba {esperada[clave]!r})")
        elif isinstance(esperada[clave], dict) and isinstance(obtenida[clave], dict):
            diferencias.extend(_diferencias_de_campo(esperada[clave], obtenida[clave], ruta + "."))
        elif esperada[clave] != obtenida[clave]:
            diferencias.append(f"{ruta}: esperaba {esperada[clave]!r} y llegó {obtenida[clave]!r}")
    return diferencias


def _derivar_del_golden(run_id: str, preregistro: dict, vocabulario: dict,
                        esquemas: dict) -> tuple[dict | None, list[str]]:
    bundle = _bundle_golden(run_id)
    if bundle.error:
        return None, [f"{run_id}: {bundle.error}"]
    observacion, fallas = derivar_observacion(
        bundle.datos, bundle.sha256, vocabulario, esquemas["observacion"],
        preregistro.get("reglas_de_derivacion_de_identidad"),
        formulas_del_preregistro(preregistro))
    return observacion, [str(f) for f in fallas]


# Cada mutante ataca una forma concreta de que la TRANSFORMACIÓN esté mal aunque la entrada y la
# salida sean estructuralmente impecables.
def _mutt_clasificacion_declarada(bundle: dict) -> bool:
    """La clasificación sale del campo declarativo en vez de los eventos observados."""
    declarado = (bundle.get("estado_del_intento") or {}).get("resultado")
    if declarado != "completado":
        return False
    for evento in list(bundle.get("eventos") or []):
        if evento.get("tipo") == "degradacion_observada":
            bundle["eventos"].remove(evento)
            return True
    return False


def _mutt_identidad_alterada(bundle: dict) -> bool:
    bundle["attempt_ordinal"] = (bundle.get("attempt_ordinal") or 1) + 10
    return True


def _mutt_evento_omitido(bundle: dict) -> bool:
    hallazgos = _eventos_de_tipo(bundle, "hallazgo_emitido")
    # Solo ejerce donde borrar el evento cambia el conteo: con dos re-emisiones del mismo hallazgo,
    # perder una NO altera el conteo sin re-emisión, y eso es correcto, no un hueco del recolector.
    detalles = [h.get("detalle") for h in hallazgos]
    if not hallazgos or len(set(detalles)) != len(detalles):
        return False
    bundle["eventos"].remove(hallazgos[0])
    return True


def _mutt_dato_incorporado(bundle: dict) -> bool:
    """Un dato que el bundle no contiene, incorporado a la evidencia."""
    recursos = bundle.get("recursos") or []
    # Solo ejerce donde la limpieza estaba completa: si ya había un recurso sin cese comprobado, la
    # métrica valía 0 antes de agregar el inventado y el mutante no movería nada.
    if not recursos or any(r.get("life_state") != "terminado_comprobado" for r in recursos):
        return False
    recursos.append({
        "recurso_id": "rec-inventado",
        "clase": "proceso",
        "life_state": "vivo",
        "ownership_state": "sin_transferir",
        "evidencia_de_cese": "recurso que la corrida no registro",
    })
    return True


MUTANTES_DE_TRANSFORMACION: tuple[MutanteDeRecoleccion, ...] = (
    MutanteDeRecoleccion("clasificacion-declarada",
                         "la clasificación se toma del campo declarativo del intento",
                         _mutt_clasificacion_declarada),
    MutanteDeRecoleccion("identidad-alterada", "el ordinal del intento cambia",
                         _mutt_identidad_alterada),
    MutanteDeRecoleccion("evento-omitido", "se pierde un evento de la corrida",
                         _mutt_evento_omitido),
    MutanteDeRecoleccion("dato-incorporado", "aparece un recurso que la corrida no registró",
                         _mutt_dato_incorporado),
)


def modo_autotest_recoleccion(args: argparse.Namespace) -> int:
    del args
    manifest, preregistro, vocabulario, esquemas, problemas = _cargar_corpus_golden()
    if problemas:
        for p in problemas:
            print(f"[A] FALLA  {p}")
        return 1

    resultados: list[tuple[str, bool, str]] = []
    goldens = manifest.get("goldens") or []

    # [A] Manifest ↔ disco, en las dos direcciones (D-16).
    declarados = {g["run_id"] for g in goldens}
    en_disco = {d.name for d in (DIR_FIXTURES_GOLDEN / "bundles").iterdir()
                if d.is_dir()} if (DIR_FIXTURES_GOLDEN / "bundles").is_dir() else set()
    diferencias = [f"declarado y ausente: {r}" for r in sorted(declarados - en_disco)]
    diferencias += [f"en disco y no declarado: {r}" for r in sorted(en_disco - declarados)]
    resultados.append(("A", not diferencias,
                       f"manifest ↔ bundles del golden ({len(declarados)})" if not diferencias
                       else " | ".join(diferencias[:6])))

    # [B] El golden, campo por campo.
    fallas: list[str] = []
    derivadas: dict[str, dict] = {}
    for entrada in goldens:
        run_id = entrada["run_id"]
        esperada, error = _cargar_json(DIR_FIXTURES_GOLDEN / "esperadas" / f"{run_id}.json")
        if error:
            fallas.append(f"{run_id}: observación esperada — {error}")
            continue
        obtenida, errores = _derivar_del_golden(run_id, preregistro, vocabulario, esquemas)
        if obtenida is None:
            fallas.append(f"{run_id}: no se derivó — {errores[0] if errores else 'sin motivo'}")
            continue
        derivadas[run_id] = obtenida
        diferencias = _diferencias_de_campo(esperada, obtenida)
        if diferencias:
            fallas.append(f"{run_id}: {len(diferencias)} campos — {diferencias[0]}")
    resultados.append(("B", not fallas,
                       f"{len(goldens)} goldens coinciden campo por campo" if not fallas
                       else " | ".join(fallas[:4])))

    # [C] Los mutantes de transformación. Cada uno tiene que MOVER el golden: si el resultado no
    # cambia, esa transformación no estaba leyendo lo que se mutó.
    fallas_de_mutacion: list[str] = []
    ejercidos: set[str] = set()
    for run_id, base in derivadas.items():
        bundle = _bundle_golden(run_id)
        for mutante in MUTANTES_DE_TRANSFORMACION:
            copia = copy.deepcopy(bundle.datos)
            if not mutante.aplicar(copia):
                continue
            ejercidos.add(mutante.nombre)
            mutada, _ = derivar_observacion(
                copia, bundle.sha256, vocabulario, esquemas["observacion"],
                preregistro.get("reglas_de_derivacion_de_identidad"),
                formulas_del_preregistro(preregistro))
            if mutada is not None and not _diferencias_de_campo(base, mutada):
                fallas_de_mutacion.append(
                    f"{run_id}/{mutante.nombre}: {mutante.que_rompe} y el golden no se mueve")
    fallas_de_mutacion += [f"el mutante «{m.nombre}» no lo ejerce ningún golden"
                           for m in MUTANTES_DE_TRANSFORMACION if m.nombre not in ejercidos]
    resultados.append(("C", not fallas_de_mutacion,
                       f"{len(MUTANTES_DE_TRANSFORMACION)} mutantes de transformación ejercidos y "
                       "detectados" if not fallas_de_mutacion
                       else " | ".join(fallas_de_mutacion[:4])))

    return _cerrar(resultados)


def comprobar_observacion_derivada(observacion: dict, preregistro: dict, vocabulario: dict,
                                   esquemas: dict) -> list[str]:
    """La prueba de que una observación se derivó: se re-ejecuta el recolector sobre el bundle que
    ella dice, y se comparan los bytes. Sus propios campos NO se usan como evidencia —una escrita a
    mano declara el hash y la identidad igual de bien que una legítima—: lo único que se toma de
    ella es a qué bundle apunta."""
    procedencia = observacion.get("procedencia") or {}
    run_id = procedencia.get("run_id")
    if not run_id:
        return ["la observación no declara de qué corrida salió: no hay nada que re-ejecutar"]
    bundle = _bundle_golden(run_id)
    if bundle.error:
        return [f"la corrida {run_id!r} que declara no se puede leer: {bundle.error}"]

    problemas: list[str] = []
    if procedencia.get("bundle_sha256") != bundle.sha256:
        problemas.append(f"el hash declarado no es el del bundle en disco: declara "
                         f"{procedencia.get('bundle_sha256')} y el archivo da {bundle.sha256}")

    derivada, fallas = derivar_observacion(
        bundle.datos, bundle.sha256, vocabulario, esquemas["observacion"],
        preregistro.get("reglas_de_derivacion_de_identidad"),
        formulas_del_preregistro(preregistro))
    if derivada is None:
        return problemas + [f"el bundle no produce ninguna observación: "
                            f"{fallas[0] if fallas else 'sin motivo'}"]

    if serializar_observacion(derivada) == serializar_observacion(observacion):
        return problemas
    diferencias = _diferencias_de_campo(derivada, observacion)
    if diferencias:
        problemas.append(f"re-ejecutar el recolector da otra observación: {diferencias[0]}"
                         + (f" (y {len(diferencias) - 1} más)" if len(diferencias) > 1 else ""))
    else:
        problemas.append("los campos coinciden y los bytes no: la observación está reordenada o "
                         "reformateada respecto de la que el recolector emite")
    return problemas


def modo_autotest_derivacion(args: argparse.Namespace) -> int:
    del args
    manifest, preregistro, vocabulario, esquemas, problemas = _cargar_corpus_golden()
    if problemas:
        for p in problemas:
            print(f"[A] FALLA  {p}")
        return 1

    resultados: list[tuple[str, bool, str]] = []

    # [A] Control positivo: lo que el recolector produce pasa su propia prueba de derivación.
    fallas: list[str] = []
    for entrada in manifest.get("goldens") or []:
        run_id = entrada["run_id"]
        derivada, errores = _derivar_del_golden(run_id, preregistro, vocabulario, esquemas)
        if derivada is None:
            fallas.append(f"{run_id}: no se derivó — {errores[0] if errores else 'sin motivo'}")
            continue
        malos = comprobar_observacion_derivada(derivada, preregistro, vocabulario, esquemas)
        if malos:
            fallas.append(f"{run_id}: lo que el recolector emite no pasa su prueba — {malos[0]}")
    resultados.append(("A", not fallas,
                       "las observaciones del recolector se prueban derivadas" if not fallas
                       else " | ".join(fallas[:4])))

    # [B] Cada observación escrita a mano falla, y falla por SU motivo. Es el control que V26 pide:
    # una que copia el hash y la identidad tiene que caer igual.
    fallas_a_mano: list[str] = []
    a_mano = manifest.get("escritas_a_mano") or []
    for entrada in a_mano:
        instancia, error = _cargar_json(DIR_FIXTURES_GOLDEN / "a-mano" / entrada["fixture"])
        if error:
            fallas_a_mano.append(f"{entrada['fixture']}: {error}")
            continue
        if validar(instancia, esquemas["observacion"]):
            fallas_a_mano.append(f"{entrada['fixture']}: no valida contra el schema, así que caería "
                                 "por estructura y no por derivación")
            continue
        malos = comprobar_observacion_derivada(instancia, preregistro, vocabulario, esquemas)
        if not malos:
            fallas_a_mano.append(f"{entrada['fixture']}: se prueba derivada y no debería")
            continue
        if not any(entrada["motivo_esperado"] in m for m in malos):
            fallas_a_mano.append(f"{entrada['fixture']}: falla, pero no por «"
                                 f"{entrada['motivo_esperado']}» — se vio: {malos[0]}")
    resultados.append(("B", not fallas_a_mano,
                       f"{len(a_mano)} observaciones escritas a mano fallan por su motivo"
                       if not fallas_a_mano else " | ".join(fallas_a_mano[:4])))

    return _cerrar(resultados)


class MutanteDePolitica(NamedTuple):
    nombre: str
    que_rompe: str
    aplicar: Callable[[dict], bool]


def _mutp_quitar_disparador(preregistro: dict) -> bool:
    politica = preregistro.get("politica_de_reintentos") or {}
    if not politica.get("disparadores"):
        return False
    politica["disparadores"] = politica["disparadores"][:-1]
    return True


def _mutp_bajar_maximo(preregistro: dict) -> bool:
    politica = preregistro.get("politica_de_reintentos") or {}
    if (politica.get("maximo_de_intentos_por_muestra") or 1) <= 1:
        return False
    politica["maximo_de_intentos_por_muestra"] = 1
    return True


def _mutp_terminacion_sin_reintento(preregistro: dict) -> bool:
    politica = preregistro.get("politica_de_reintentos") or {}
    if politica.get("condicion_de_terminacion") == "sin_reintento":
        return False
    politica["condicion_de_terminacion"] = "sin_reintento"
    return True


def _mutp_cambiar_seleccion(preregistro: dict) -> bool:
    for seleccion in (preregistro.get("politica_de_reintentos") or {}).get(
            "seleccion_por_metrica") or []:
        if seleccion.get("regla") == "primer_intento_valido":
            seleccion["regla"] = "primer_intento"
            return True
    return False


MUTANTES_DE_POLITICA: tuple[MutanteDePolitica, ...] = (
    MutanteDePolitica("disparador-retirado",
                      "el reintento deja de tener un disparador que lo admita",
                      _mutp_quitar_disparador),
    MutanteDePolitica("maximo-bajado", "la cadena excede el máximo de intentos por muestra",
                      _mutp_bajar_maximo),
    MutanteDePolitica("terminacion-sin-reintento",
                      "la política pasa a no admitir ningún reintento",
                      _mutp_terminacion_sin_reintento),
    MutanteDePolitica("seleccion-cambiada",
                      "la métrica se publica desde otro intento del que el acta congeló",
                      _mutp_cambiar_seleccion),
)


def _observaciones_por_muestra(manifest: dict, preregistro: dict, vocabulario: dict,
                               esquemas: dict) -> tuple[dict[str, list[dict]], list[str]]:
    por_muestra: dict[str, list[dict]] = {}
    problemas: list[str] = []
    for entrada in manifest.get("goldens") or []:
        derivada, errores = _derivar_del_golden(entrada["run_id"], preregistro, vocabulario,
                                                esquemas)
        if derivada is None:
            problemas.append(f"{entrada['run_id']}: {errores[0] if errores else 'no se derivó'}")
            continue
        por_muestra.setdefault(derivada["sample_id"], []).append(derivada)
    return por_muestra, problemas


def _revisar_muestras_e_intentos(manifest_intentos: dict, preregistro: dict,
                                 por_muestra: dict[str, list[dict]],
                                 vocabulario: dict) -> dict[str, list[str]]:
    """Los cuatro frentes de V31, cada uno con su clave. Devolver un dict por clave —y no una lista
    plana— es lo que permite que un mutante declare EXACTAMENTE qué frente tiene que romper."""
    fallas: dict[str, list[str]] = {"muestras": [], "cadena": [], "identidad": [], "seleccion": []}
    politica = preregistro.get("politica_de_reintentos") or {}

    # Las muestras esperadas se derivan aparte y se comparan en las dos direcciones.
    esperadas = set(derivar_muestras_esperadas(preregistro, manifest_intentos))
    declaradas = {m.get("sample_id") for m in
                  ((preregistro.get("cohorte") or {}).get("muestras") or [])}
    fallas["muestras"] += [f"muestra derivada del producto punto × repetición y ausente de la "
                           f"cohorte: {m}" for m in sorted(esperadas - declaradas)]
    fallas["muestras"] += [f"muestra en la cohorte que el producto no produce: {m}"
                           for m in sorted(declaradas - esperadas)]

    # El manifest de intentos es independiente (D-16): declara qué intentos tienen que existir. Sin
    # él, borrar el último intento bloqueado deja un conjunto final perfectamente válido.
    esperados = {(e.get("sample_id"), e.get("attempt_ordinal")): e
                 for e in manifest_intentos.get("intentos") or []}
    observados = {(o["sample_id"], o["attempt_ordinal"]): o
                  for obs in por_muestra.values() for o in obs}
    fallas["cadena"] += [f"intento declarado en el manifest y sin observación: {s} #{n}"
                         for s, n in sorted(esperados.keys() - observados.keys())]
    fallas["cadena"] += [f"observación de un intento que el manifest no declara: {s} #{n}"
                         for s, n in sorted(observados.keys() - esperados.keys())]

    for sample_id, observaciones in sorted(por_muestra.items()):
        fallas["cadena"] += comprobar_cadena_de_intentos(sample_id, observaciones, politica)

    reglas = preregistro.get("reglas_de_derivacion_de_identidad") or {}
    identidades_vistas: dict[str, str] = {}
    for clave, observacion in sorted(observados.items()):
        entrada = esperados.get(clave)
        if entrada is None:
            continue
        for campo in ("attempt_id", "observation_id"):
            valor, error = aplicar_regla_de_identidad(
                reglas.get(campo) or {},
                {**contexto_de_identidad(observacion), "attempt_id": observacion.get("attempt_id")})
            if error:
                fallas["identidad"].append(f"{clave[0]} #{clave[1]}: {campo} — {error}")
                continue
            if observacion.get(campo) != valor:
                fallas["identidad"].append(
                    f"{clave[0]} #{clave[1]}: {campo} es {observacion.get(campo)!r} y la regla "
                    f"congelada produce {valor!r}")
            duenio = identidades_vistas.get(valor)
            if duenio is not None and duenio != f"{clave[0]}#{clave[1]}":
                fallas["identidad"].append(
                    f"{valor!r} lo produce {duenio} y también {clave[0]}#{clave[1]}: la regla "
                    "colisiona entre repeticiones")
            identidades_vistas[valor] = f"{clave[0]}#{clave[1]}"

    for entrada in manifest_intentos.get("selecciones_esperadas") or []:
        observaciones = por_muestra.get(entrada["sample_id"]) or []
        valor, error = aplicar_seleccion_por_metrica(entrada["metrica_id"], observaciones,
                                                     politica, vocabulario)
        if error:
            fallas["seleccion"].append(f"{entrada['sample_id']}/{entrada['metrica_id']}: {error}")
        elif not _casi_igual(valor, entrada["valor_esperado"]):
            fallas["seleccion"].append(
                f"{entrada['sample_id']}/{entrada['metrica_id']}: la política publica {valor} y se "
                f"esperaba {entrada['valor_esperado']}")
    return fallas


def modo_autotest_muestras_intentos(args: argparse.Namespace) -> int:
    del args
    manifest, preregistro, vocabulario, esquemas, problemas = _cargar_corpus_golden()
    manifest_intentos, error = _cargar_json(DIR_FIXTURES_GOLDEN / "manifest-intentos.json")
    if error:
        problemas.append(f"manifest independiente de intentos: {error}")
    if problemas:
        for p in problemas:
            print(f"[A] FALLA  {p}")
        return 1

    por_muestra, malos = _observaciones_por_muestra(manifest, preregistro, vocabulario, esquemas)
    if malos:
        for m in malos:
            print(f"[A] FALLA  {m}")
        return 1

    resultados: list[tuple[str, bool, str]] = []
    base = _revisar_muestras_e_intentos(manifest_intentos, preregistro, por_muestra, vocabulario)
    # Qué frentes se ponen rojos DE VERDAD en los controles de abajo. Se acumula corriendo, no se
    # transcribe: una lista escrita a mano acá dejaría de reflejar los negativos que existen.
    ejercidos: set[str] = set()

    # [A] Control positivo: el corpus conforme no rompe ninguno de los cuatro frentes. Un intento
    # extra legítimo —el segundo de una muestra, admitido por la política— NO invalida su muestra.
    en_rojo = {clave for clave, lista in base.items() if lista}
    resultados.append(("A", not en_rojo,
                       f"{len(por_muestra)} muestras y "
                       f"{sum(len(v) for v in por_muestra.values())} intentos conformes"
                       if not en_rojo
                       else " | ".join(f"{c}: {base[c][0]}" for c in sorted(en_rojo))))

    # [B] Los negativos de la cadena, sobre COPIAS del conjunto de observaciones. Los dos que D-12
    # nombra: borrar el último intento bloqueado, y borrarlo renumerando la cadena.
    fallas_de_cadena: list[str] = []
    for caso in manifest_intentos.get("negativos_de_cadena") or []:
        copia = copy.deepcopy(por_muestra)
        objetivo = copia.get(caso["sample_id"]) or []
        objetivo.sort(key=lambda o: o["attempt_ordinal"])
        if caso["ataque"] == "borrar_ultimo":
            objetivo.pop()
        elif caso["ataque"] == "borrar_ultimo_y_renumerar":
            objetivo.pop()
            for i, observacion in enumerate(objetivo, start=1):
                observacion["attempt_ordinal"] = i
        elif caso["ataque"] == "attempt_id_fuera_de_la_regla":
            objetivo[-1]["attempt_id"] = "int-inventado-a9"
        else:
            fallas_de_cadena.append(f"{caso['ataque']}: ataque no implementado")
            continue
        resultado = _revisar_muestras_e_intentos(manifest_intentos, preregistro, copia,
                                                 vocabulario)
        ejercidos |= {f for f, lista in resultado.items() if lista}
        if not resultado[caso["frente_esperado"]]:
            fallas_de_cadena.append(f"{caso['ataque']}: el frente «{caso['frente_esperado']}» no se "
                                    "pone rojo")
    resultados.append(("B", not fallas_de_cadena,
                       f"{len(manifest_intentos.get('negativos_de_cadena') or [])} ataques a la "
                       "cadena detectados" if not fallas_de_cadena
                       else " | ".join(fallas_de_cadena[:4])))

    # [C] Mutar la política congelada cambia el resultado. Es lo que prueba que la política se
    # APLICA y no se elige a posteriori: una declarada y no ejecutada dejaría este control verde.
    fallas_de_politica: list[str] = []
    for mutante in MUTANTES_DE_POLITICA:
        copia = copy.deepcopy(preregistro)
        if not mutante.aplicar(copia):
            fallas_de_politica.append(f"{mutante.nombre}: la mutación no se pudo aplicar, así que "
                                      "esa parte de la política queda sin control")
            continue
        resultado = _revisar_muestras_e_intentos(manifest_intentos, copia, por_muestra,
                                                 vocabulario)
        ejercidos |= {f for f, lista in resultado.items() if lista}
        if not any(resultado.values()):
            fallas_de_politica.append(f"{mutante.nombre}: {mutante.que_rompe} y ningún frente se "
                                      "pone rojo")
    resultados.append(("C", not fallas_de_politica,
                       f"{len(MUTANTES_DE_POLITICA)} mutantes de la política congelada cambian el "
                       "resultado" if not fallas_de_politica
                       else " | ".join(fallas_de_politica[:4])))

    # [D] Los negativos del conjunto de muestras. Sin ellos, ese frente no tiene quien lo ponga
    # rojo: la comparación pasaría en el vacío y nadie lo notaría.
    fallas_de_muestras: list[str] = []
    for caso in manifest_intentos.get("negativos_de_muestras") or []:
        copia = copy.deepcopy(preregistro)
        muestras = (copia.get("cohorte") or {}).get("muestras") or []
        if caso["ataque"] == "quitar_muestra":
            restantes = [m for m in muestras if m.get("sample_id") != caso["sample_id"]]
            if len(restantes) == len(muestras):
                fallas_de_muestras.append(f"{caso['ataque']}: la muestra {caso['sample_id']} no "
                                          "está en la cohorte, así que el ataque no se aplicó")
                continue
            copia["cohorte"]["muestras"] = restantes
        elif caso["ataque"] == "agregar_muestra_que_el_producto_no_produce":
            copia["cohorte"]["muestras"] = muestras + [{**muestras[0],
                                                        "sample_id": caso["sample_id"]}]
        else:
            fallas_de_muestras.append(f"{caso['ataque']}: ataque no implementado")
            continue
        resultado = _revisar_muestras_e_intentos(manifest_intentos, copia, por_muestra,
                                                 vocabulario)
        ejercidos |= {f for f, lista in resultado.items() if lista}
        if not resultado["muestras"]:
            fallas_de_muestras.append(f"{caso['ataque']}: el frente «muestras» no se pone rojo")
    resultados.append(("D", not fallas_de_muestras,
                       f"{len(manifest_intentos.get('negativos_de_muestras') or [])} ataques al "
                       "conjunto de muestras detectados" if not fallas_de_muestras
                       else " | ".join(fallas_de_muestras[:4])))

    # [E] Los mutantes de derivación de identidad que D-12 nombra: por `run_id` solo, asignación por
    # orden de llegada y colisión entre repeticiones.
    fallas_de_identidad: list[str] = []
    for caso in manifest_intentos.get("mutantes_de_identidad") or []:
        copia = copy.deepcopy(preregistro)
        copia.setdefault("reglas_de_derivacion_de_identidad", {})[caso["campo"]] = caso["regla"]
        resultado = _revisar_muestras_e_intentos(manifest_intentos, copia, por_muestra,
                                                 vocabulario)
        ejercidos |= {f for f, lista in resultado.items() if lista}
        if not resultado["identidad"]:
            fallas_de_identidad.append(f"{caso['nombre']}: la regla mutada no rompe la identidad")
    resultados.append(("E", not fallas_de_identidad,
                       f"{len(manifest_intentos.get('mutantes_de_identidad') or [])} mutantes de "
                       "derivación de identidad detectados" if not fallas_de_identidad
                       else " | ".join(fallas_de_identidad[:4])))

    # [F] Cada uno de los cuatro frentes se puso rojo en ALGUNO de los controles de arriba. El
    # conjunto se acumuló corriendo: un frente que ningún negativo ejerce pasa siempre, y su verde
    # se lee como si hubiera comprobado algo.
    sin_negativo = sorted(set(base) - ejercidos)
    resultados.append(("F", not sin_negativo,
                       f"los {len(base)} frentes tienen quien los ponga rojos"
                       if not sin_negativo
                       else f"frentes sin ningún negativo que los ejerza: {sin_negativo}"))

    return _cerrar(resultados)


def _cerrar(resultados: list[tuple[str, bool, str]]) -> int:
    """El cierre común de los modos de autotest: una línea por control y el veredicto."""
    for etiqueta, ok, detalle in resultados:
        print(f"[{etiqueta}] {'OK    ' if ok else 'FALLA '} {detalle}")
    print()
    rojos = [e for e, ok, _ in resultados if not ok]
    if rojos:
        print(f"RESULTADO: FALLA — controles en rojo: {', '.join(rojos)}")
        return 1
    print(f"RESULTADO: OK — {len(resultados)} controles en verde")
    return 0


# ---------------------------------------------------------------------------------------------
# Modos `--autotest-clasificacion` y `--fixture-historico`.
#
# Una observación limpia no prueba que el instrumento clasifique bien. El corpus de control existe
# para eso, y su forma la fija AC-18: **el resultado esperado de cada caso se declara por los TRES
# EJES normativos —ciclo operativo, validez del reporte y resultado semántico— más las métricas
# derivadas por separado, nunca como una etiqueta única**. Una etiqueta única obliga a resolver por
# prioridad arbitraria los casos que combinan varias fallas, y una corrida real los combina.
#
# El corpus NO se valida contra sí mismo (D-16): las categorías obligatorias y las combinaciones
# mínimas viven en un manifest independiente y se comparan en las dos direcciones, y cada caso
# requerido lleva su mutante de eliminación — borrar el de ausencia de eventos tiene que poner el
# modo rojo, no reducir el conjunto que valida.
#
# `--fixture-historico` es el caso que la serie del propio repositorio aporta: un registro que
# **declara** que no hubo degradación y **narra** dos. Se reconstruye, no se copia (decisión
# heredada 7): el documento original lleva un término que una guarda vigente prohíbe en el árbol
# trackeado, y copiarlo la pondría roja por una razón ajena al cambio. El fixture reproduce solo la
# contradicción, conserva un puntero de procedencia y es **autónomo**: no lee nada fuera de su
# directorio, así que una clonación limpia puede ejecutarlo.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_CLASIFICACION = DIR_SCRIPTS / "fixtures-baseline" / "clasificacion"
RUTA_MANIFEST_CLASIFICACION = DIR_FIXTURES_CLASIFICACION / "manifest.json"
DIR_CASO_HISTORICO = DIR_FIXTURES_CLASIFICACION / "historico"

# Los tres ejes, por su nombre en el estado derivado. Un caso que no declare los tres no está
# declarando una terna: está declarando una etiqueta con dos campos de adorno.
EJES_NORMATIVOS: tuple[str, ...] = ("ciclo_operativo", "validez_del_reporte", "resultado_semantico")


def _bundle_de_caso(caso_id: str) -> BundleEnDisco:
    return _leer_bundle(DIR_FIXTURES_CLASIFICACION / "casos" / caso_id)


def _casos_en_disco() -> set[str]:
    raiz = DIR_FIXTURES_CLASIFICACION / "casos"
    if not raiz.is_dir():
        return set()
    return {hijo.name for hijo in raiz.iterdir() if hijo.is_dir()}


def clasificar_caso(caso_id: str, vocabulario: dict,
                    esquemas: dict) -> tuple[dict | None, list[str]]:
    """La observación del caso, derivada por el mismo recolector que corre en producción. El corpus
    no ejercita un clasificador aparte: si lo hiciera, probaría un código que nadie usa."""
    bundle = _bundle_de_caso(caso_id)
    if bundle.error:
        return None, [f"{caso_id}: {bundle.error}"]
    errores = validar(bundle.datos, esquemas["bundle-corrida"])
    if errores:
        return None, [f"{caso_id}: el bundle no valida contra su contrato — {errores[0]}"]
    observacion, fallas = derivar_observacion(bundle.datos, bundle.sha256, vocabulario,
                                              esquemas["observacion"])
    return observacion, [f"{caso_id}: {f}" for f in fallas]


def _valor_de_metrica(observacion: dict, metrica_id: str) -> Any:
    """Lo que el caso declara esperar de una métrica: su valor si está medida, y su estado de
    medición si no. Las dos cosas se comparan igual, porque «bloqueada» es un resultado tan
    declarable como un número — y es el que AC-21 exige donde no hubo medición."""
    metrica = _metrica_de_la_observacion(observacion, metrica_id)
    if metrica is None:
        return None
    if metrica.get("estado_de_medicion") != "medida":
        return metrica.get("estado_de_medicion")
    return metrica.get("valor")


def revisar_caso(entrada: dict, observacion: dict) -> list[str]:
    """Un caso contra su declaración. Los ejes y las métricas se comparan POR SEPARADO: fundirlos en
    un veredicto único es lo que deja pasar un clasificador que acierta la etiqueta y deriva mal."""
    problemas: list[str] = []
    caso_id = entrada["caso_id"]
    esperado = entrada.get("estado_esperado") or {}

    faltantes = [eje for eje in EJES_NORMATIVOS if eje not in esperado]
    if faltantes:
        problemas.append(f"{caso_id}: el esperado no declara {faltantes}: sin los tres ejes no es "
                         "una terna, es una etiqueta única")
    obtenido = observacion.get("estado") or {}
    for clave, valor in esperado.items():
        if obtenido.get(clave) != valor:
            problemas.append(f"{caso_id}: `{clave}` es {obtenido.get(clave)!r} y se esperaba "
                             f"{valor!r}")

    for metrica_id, valor in (entrada.get("metricas_esperadas") or {}).items():
        obtenido_metrica = _valor_de_metrica(observacion, metrica_id)
        if isinstance(valor, (int, float)) and isinstance(obtenido_metrica, (int, float)):
            if not _casi_igual(obtenido_metrica, valor):
                problemas.append(f"{caso_id}: `{metrica_id}` vale {obtenido_metrica} y se esperaba "
                                 f"{valor}")
        elif obtenido_metrica != valor:
            problemas.append(f"{caso_id}: `{metrica_id}` es {obtenido_metrica!r} y se esperaba "
                             f"{valor!r}")
    return problemas


def _ejes_sin_separar(observaciones: list[dict]) -> list[str]:
    """Los pares de ejes que este corpus NO separa. Si para cada valor del primero el segundo toma
    siempre el mismo, un clasificador que derivara el segundo del primero pasaría igual: el corpus
    no distingue tres ejes de uno con dos campos calculados."""
    problemas: list[str] = []
    for primero, segundo in ((0, 1), (0, 2), (1, 2)):
        eje_a, eje_b = EJES_NORMATIVOS[primero], EJES_NORMATIVOS[segundo]
        por_valor: dict[Any, set] = {}
        for observacion in observaciones:
            estado = observacion.get("estado") or {}
            por_valor.setdefault(estado.get(eje_a), set()).add(estado.get(eje_b))
        if not any(len(valores) > 1 for valores in por_valor.values()):
            problemas.append(f"ningún caso del alcance separa `{eje_b}` de `{eje_a}`: con este "
                             "corpus, un clasificador que derivara el segundo del primero pasaría "
                             "igual")
    return problemas


# Un corpus donde los tres ejes se mueven juntos. Existe solo para ejercer el predicado de arriba:
# es el control positivo que prueba que puede ponerse rojo.
_CORPUS_DEGENERADO: tuple[dict, ...] = (
    {"estado": {"ciclo_operativo": "completado", "validez_del_reporte": "valido",
                "resultado_semantico": "correcto"}},
    {"estado": {"ciclo_operativo": "bloqueado", "validez_del_reporte": "ausente",
                "resultado_semantico": "no_evaluable"}},
)


def _huecos_de_cobertura(casos: list[dict], manifest: dict, solo_combinados: bool) -> list[str]:
    """Qué le falta al corpus, en las dos direcciones. La misma función la usan el control de
    cobertura y su mutante de eliminación: si divergieran, el mutante probaría un criterio que el
    control real no aplica, y quitar un caso podría pasar por un lado y fallar por el otro.

    Un caso COMBINADO no cubre ninguna categoría —no representa una falla aislada—, así que las
    categorías se miden solo sobre los simples. Si los combinados contaran, quitar el caso simple
    de una categoría no se notaría: el combinado la mantendría cubierta."""
    huecos: list[str] = []
    simples = [c for c in casos if len(c.get("fallas") or []) <= 1]
    combinados = [c for c in casos if len(c.get("fallas") or []) > 1]

    if not solo_combinados:
        requeridas = manifest.get("categorias_obligatorias") or []
        cubiertas = {c.get("categoria") for c in simples}
        huecos += [f"categoría obligatoria sin ningún caso simple: {c}"
                   for c in requeridas if c not in cubiertas]
        huecos += [f"categoría de un caso simple que el manifest no declara: {c}"
                   for c in sorted(cubiertas - set(requeridas))]

    minimas = [sorted(c) for c in manifest.get("combinaciones_minimas") or []]
    cubiertas_c = [sorted(c.get("fallas") or []) for c in combinados]
    huecos += [f"combinación mínima sin ningún caso: {c}" for c in minimas if c not in cubiertas_c]
    huecos += [f"caso combinado que ninguna combinación mínima declara: {c['caso_id']}"
               for c in combinados if sorted(c.get("fallas") or []) not in minimas]
    return huecos


def modo_autotest_clasificacion(args: argparse.Namespace) -> int:
    solo_combinados = bool(getattr(args, "combinados", False))
    manifest, error = _cargar_json(RUTA_MANIFEST_CLASIFICACION)
    if error:
        print(f"[A] FALLA  manifest del corpus de clasificación: {error}")
        return 1
    vocabulario, esquemas, problemas = _cargar_insumos_de_recoleccion()
    if problemas:
        for p in problemas:
            print(f"[A] FALLA  {p}")
        return 1

    casos = manifest.get("casos") or []
    # Un caso COMBINADO no representa una falla aislada, así que no cubre ninguna categoría: si lo
    # hiciera, quitar el caso simple de esa categoría no se notaría —el combinado la mantendría
    # cubierta— y el corpus no podría detectar su ausencia.
    combinados = [c for c in casos if len(c.get("fallas") or []) > 1]
    simples = [c for c in casos if len(c.get("fallas") or []) <= 1]
    alcance = combinados if solo_combinados else casos
    resultados: list[tuple[str, bool, str]] = []

    # [A] Manifest ↔ disco, en las dos direcciones. Con `--combinados` se compara igual sobre el
    # corpus entero: acotar el ALCANCE de la revisión no puede acotar la detección de una ausencia.
    declarados = {c["caso_id"] for c in casos}
    en_disco = _casos_en_disco()
    diferencias = [f"declarado y ausente del disco: {c}" for c in sorted(declarados - en_disco)]
    diferencias += [f"en disco y no declarado: {c}" for c in sorted(en_disco - declarados)]
    resultados.append(("A", not diferencias,
                       f"manifest ↔ directorio ({len(declarados)} casos)" if not diferencias
                       else " | ".join(diferencias[:6])))

    # [B] Las categorías obligatorias —o las combinaciones mínimas— contra el manifest
    # independiente, en las dos direcciones. Es lo que hace que borrar el caso de ausencia de
    # eventos ponga el modo rojo en vez de reducir el conjunto validado.
    huecos = _huecos_de_cobertura(casos, manifest, solo_combinados)
    etiqueta = (f"las {len(manifest.get('combinaciones_minimas') or [])} combinaciones mínimas"
                if solo_combinados
                else f"las {len(manifest.get('categorias_obligatorias') or [])} categorías "
                     f"obligatorias y las {len(manifest.get('combinaciones_minimas') or [])} "
                     "combinaciones mínimas")
    resultados.append(("B", not huecos, f"{etiqueta}, en las dos direcciones" if not huecos
                       else " | ".join(huecos[:6])))

    # [C] Cada caso del alcance clasifica en su terna y en sus métricas, declaradas por separado.
    fallas: list[str] = []
    observaciones: dict[str, dict] = {}
    for entrada in alcance:
        observacion, malos = clasificar_caso(entrada["caso_id"], vocabulario, esquemas)
        if observacion is None:
            fallas.extend(malos)
            continue
        observaciones[entrada["caso_id"]] = observacion
        fallas.extend(revisar_caso(entrada, observacion))
    resultados.append(("C", not fallas,
                       f"{len(alcance)} casos clasifican en su terna y sus métricas"
                       if not fallas else " | ".join(fallas[:4])))

    # [D] Ningún eje se resuelve por prioridad. Se comprueba sobre el corpus mostrando que cada eje
    # toma valores DISTINTOS con el mismo valor en otro eje: si el eje 1 determinara al 2, no
    # existirían dos casos con el mismo ciclo y distinta validez.
    independencias = _ejes_sin_separar(list(observaciones.values()))
    # Y el control se ejerce en las dos direcciones: sobre un corpus DEGENERADO —donde cada valor
    # del primer eje viene siempre con el mismo del segundo— el predicado tiene que dar rojo. Sin
    # este positivo, anularlo dejaría [D] en verde para siempre y nadie lo notaría.
    if not _ejes_sin_separar(_CORPUS_DEGENERADO):
        independencias.append("el predicado de independencia no se pone rojo ni sobre un corpus "
                              "donde los tres ejes se mueven juntos: no está comprobando nada")
    resultados.append(("D", not independencias,
                       f"los {len(EJES_NORMATIVOS)} ejes se mueven por separado en el corpus, y el "
                       "predicado se pone rojo cuando no" if not independencias
                       else " | ".join(independencias[:3])))

    # [E] El mutante de eliminación de cada caso requerido. Quitar un caso del corpus tiene que
    # poner rojo el control [B]: sin esto, [B] compara dos conjuntos que se mueven juntos.
    fallas_de_eliminacion: list[str] = []
    for entrada in alcance:
        restantes = [c for c in casos if c["caso_id"] != entrada["caso_id"]]
        if not _huecos_de_cobertura(restantes, manifest, solo_combinados):
            fallas_de_eliminacion.append(
                f"quitar {entrada['caso_id']} del corpus no pone rojo el control de cobertura: ese "
                "caso no lo exige nadie")
    resultados.append(("E", not fallas_de_eliminacion,
                       f"{len(alcance)} mutantes de eliminación detectados"
                       if not fallas_de_eliminacion
                       else " | ".join(fallas_de_eliminacion[:4])))

    return _cerrar(resultados)


def modo_fixture_historico(args: argparse.Namespace) -> int:
    del args
    vocabulario, esquemas, problemas = _cargar_insumos_de_recoleccion()
    procedencia, error = _cargar_json(DIR_CASO_HISTORICO / "procedencia.json")
    if error:
        problemas.append(f"puntero de procedencia del fixture histórico: {error}")
    if problemas:
        for p in problemas:
            print(f"[A] FALLA  {p}")
        return 1

    bundle = _leer_bundle(DIR_CASO_HISTORICO)
    if bundle.error:
        print(f"[A] FALLA  fixture histórico: {bundle.error}")
        return 1

    resultados: list[tuple[str, bool, str]] = []

    # [A] El fixture es AUTÓNOMO. Es la razón de reconstruirlo en vez de copiarlo: el documento del
    # que sale ya no está en el árbol, así que un fixture que dependiera de él no se podría ejecutar
    # en una clonación limpia. Se comprueba que la ruta de origen NO exista y que el fixture no la
    # necesite: todo lo que usa está en su propio directorio.
    origen = procedencia.get("documento_de_origen") or ""
    encontrados = sorted(str(p.relative_to(RAIZ)) for p in RAIZ.glob(origen)) if origen else []
    problemas_de_autonomia: list[str] = []
    if not origen:
        problemas_de_autonomia.append("la procedencia no declara de qué documento sale")
    if encontrados:
        problemas_de_autonomia.append(
            f"el documento de origen está en el árbol ({encontrados[0]}): el fixture tiene que "
            "reproducir la contradicción, no apoyarse en él")
    if not procedencia.get("commit_de_eliminacion"):
        problemas_de_autonomia.append("la procedencia no declara en qué commit dejó de existir")
    resultados.append(("A", not problemas_de_autonomia,
                       f"fixture autónomo, con su puntero a «{origen}»"
                       if not problemas_de_autonomia
                       else " | ".join(problemas_de_autonomia)))

    # [B] La contradicción está reproducida, y en las dos direcciones: cada degradación que la
    # procedencia declara narrada tiene su evento en el bundle, y cada evento tiene la suya.
    narradas = {d["identificador"]: d for d in procedencia.get("degradaciones_narradas") or []}
    eventos = {e.get("evento_id"): e for e in _eventos_de_tipo(bundle.datos or {},
                                                              "degradacion_observada")}
    faltan = [f"degradación narrada sin evento en el bundle: {i}"
              for i in sorted(narradas.keys() - eventos.keys())]
    faltan += [f"evento de degradación que la procedencia no narra: {i}"
               for i in sorted(eventos.keys() - narradas.keys())]
    if len(narradas) < 2:
        faltan.append(f"la contradicción son DOS degradaciones y la procedencia narra "
                      f"{len(narradas)}")
    resultados.append(("B", not faltan,
                       f"las {len(narradas)} degradaciones narradas están reproducidas, en las dos "
                       "direcciones" if not faltan else " | ".join(faltan[:4])))

    # [C] Y el registro las DECLARA ausentes: sin esa declaración no hay contradicción que
    # reproducir, solo una corrida degradada más.
    declarada = procedencia.get("degradacion_declarada")
    resultados.append(("C", declarada == "ausente",
                       "el registro declara la degradación ausente y narra dos: esa es la "
                       "contradicción" if declarada == "ausente"
                       else f"la procedencia declara `degradacion_declarada` = {declarada!r}, y "
                            "sin «ausente» no hay contradicción"))

    # [D] El instrumento lo clasifica DERIVANDO las dos degradaciones, no con un rechazo genérico.
    observacion, fallas = derivar_observacion(bundle.datos, bundle.sha256, vocabulario,
                                              esquemas["observacion"])
    if observacion is None:
        resultados.append(("D", False, f"la observación no se derivó — "
                                       f"{fallas[0] if fallas else 'sin motivo'}"))
        return _cerrar(resultados)

    estado = observacion.get("estado") or {}
    derivadas = len(_eventos_de_tipo(bundle.datos, "degradacion_observada"))
    malos: list[str] = []
    if estado.get("resultado_semantico") != "incorrecto":
        malos.append(f"`resultado_semantico` es {estado.get('resultado_semantico')!r} y tiene que "
                     "ser «incorrecto»")
    if estado.get("ciclo_operativo") != "degradado":
        malos.append(f"`ciclo_operativo` es {estado.get('ciclo_operativo')!r}: las degradaciones "
                     "narradas tienen que derivar el ciclo, no quedar como prosa")
    if derivadas != 2:
        malos.append(f"se derivaron {derivadas} degradaciones y son dos")
    resultados.append(("D", not malos,
                       f"clasificado incorrecto, con las {derivadas} degradaciones derivadas de "
                       "sus eventos" if not malos else " | ".join(malos)))

    if not any(not ok for _, ok, _ in resultados):
        print(f"       procedencia: {origen} · commit {procedencia['commit_de_eliminacion']}")
        for identificador, dato in sorted(narradas.items()):
            print(f"       - {identificador}: {dato['que_se_degrado']}")
    return _cerrar(resultados)


# ---------------------------------------------------------------------------------------------
# Modos `--hallazgos` y `--autotest-hallazgos`.
#
# AC-15 exige cinco categorías de métrica y esta era la única sin productor. El conteo se deriva de
# los EVENTOS del bundle y de ningún campo declarativo, con la regla de agregación que el
# vocabulario declara.
#
# ## Qué cuenta como hallazgo, y qué es una re-emisión
#
# Cuenta **un evento `hallazgo_emitido`**, y nada más: ni un artefacto producido, ni una mención en
# el reporte del worker, ni una entrada del journal de anomalías —que es otra cosa: el journal
# registra fallas del runner, no hallazgos del worker—.
#
# La **identidad** del hallazgo es su `detalle`. En un evento de hallazgo ese campo no es narración
# libre: es el **identificador del tema**, y el runner emite el mismo para el mismo hallazgo. Dos
# eventos con la misma identidad son **una re-emisión**: el mismo tema visto en dos rondas es un
# hallazgo, no dos. Contarlo dos veces mide convergencia y la publica como producción.
#
# La identidad se compara **normalizada** —minúsculas, espacios colapsados y sin puntuación final—
# porque la alternativa es que «El adaptador no deja constancia.» y «el adaptador no deja
# constancia» cuenten como dos hallazgos distintos. La normalización se aplica solo a los eventos
# de hallazgo, que son los únicos cuyo `detalle` hace de clave.
#
# El vocabulario admite las dos fórmulas —con y sin re-emisión— y **elige el pre-registro**. El
# instrumento no elige: donde el acta no eligió, la métrica sale sin observación con su adjudicación
# escrita, que es distinto de salir en cero.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_HALLAZGOS = DIR_SCRIPTS / "fixtures-baseline" / "hallazgos"
RUTA_MANIFEST_HALLAZGOS = DIR_FIXTURES_HALLAZGOS / "manifest.json"

METRICA_DE_HALLAZGOS = "hallazgos-emitidos"

_PUNTUACION_FINAL = re.compile(r"[\s.;,:!?¡¿]+$")
_ESPACIOS = re.compile(r"\s+")


def identidad_de_hallazgo(detalle: Any) -> Any:
    """La identidad de un hallazgo, normalizada. Sin esto, dos emisiones del mismo tema que difieren
    en una mayúscula o en un punto final se cuentan como dos hallazgos distintos, y la métrica pasa
    a medir cómo se redactó el detalle en vez de cuánto hallazgo distinto se produjo."""
    if not isinstance(detalle, str):
        return detalle
    return _PUNTUACION_FINAL.sub("", _ESPACIOS.sub(" ", detalle.strip()).casefold())


def hallazgos_del_bundle(bundle: dict) -> list[dict]:
    return _eventos_de_tipo(bundle, "hallazgo_emitido")


def _cargar_corpus_de_hallazgos() -> tuple[dict, dict, dict, dict, list[str]]:
    problemas: list[str] = []
    manifest, error = _cargar_json(RUTA_MANIFEST_HALLAZGOS)
    if error:
        problemas.append(f"manifest del corpus de hallazgos: {error}")
    preregistro, error = _cargar_json(DIR_FIXTURES_HALLAZGOS / "preregistro.json")
    if error:
        problemas.append(f"pre-registro del corpus de hallazgos: {error}")
    vocabulario, esquemas, mas = _cargar_insumos_de_recoleccion()
    return manifest or {}, preregistro or {}, vocabulario, esquemas, problemas + mas


def _observacion_de_hallazgos(directorio: Path, preregistro: dict, vocabulario: dict,
                              esquemas: dict, con_formula: bool) -> tuple[dict | None, list[str]]:
    bundle = _leer_bundle(directorio)
    if bundle.error:
        return None, [bundle.error]
    observacion, fallas = derivar_observacion(
        bundle.datos, bundle.sha256, vocabulario, esquemas["observacion"],
        preregistro.get("reglas_de_derivacion_de_identidad"),
        formulas_del_preregistro(preregistro) if con_formula else None)
    return observacion, [str(f) for f in fallas]


# --- Las tres reglas de conteo que el corpus tiene que distinguir. La primera es la correcta; las
# otras dos son las formas concretas de contar mal que la task nombra, y existen acá para que el
# autotest pueda exigir que el corpus las separe. Una regla equivocada que ningún caso distingue de
# la correcta es un mutante que el corpus no caza. ---

def _conteo_correcto(bundle: dict) -> float:
    return float(len({json.dumps(identidad_de_hallazgo(e.get("detalle")), ensure_ascii=False)
                      for e in hallazgos_del_bundle(bundle)}))


def _conteo_desde_campo_declarativo(bundle: dict) -> float:
    # El journal registra anomalías del RUNNER, no hallazgos del worker. Tomarlo de ahí es contar
    # otra cosa con el nombre correcto.
    return float(len(bundle.get("journal_candidate_ids") or []))


def _conteo_con_reemision(bundle: dict) -> float:
    return float(len(hallazgos_del_bundle(bundle)))


REGLAS_DE_CONTEO_ERRADAS: tuple[tuple[str, str, Callable[[dict], float]], ...] = (
    ("desde-campo-declarativo", "el conteo sale de `journal_candidate_ids` en vez de los eventos",
     _conteo_desde_campo_declarativo),
    ("con-reemision", "cada re-emisión del mismo hallazgo cuenta como uno nuevo",
     _conteo_con_reemision),
)


def modo_hallazgos(args: argparse.Namespace) -> int:
    raiz = _ruta_absoluta(getattr(args, "hallazgos"))
    ruta_acta = getattr(args, "preregistro", None) or RUTA_PREREGISTRO_FASE_0
    preregistro, _ = _cargar_json(_ruta_absoluta(ruta_acta))
    preregistro = preregistro if isinstance(preregistro, dict) else {}
    vocabulario, esquemas, problemas = _cargar_insumos_de_recoleccion()
    if problemas:
        for p in problemas:
            print(f"FALLA  {p}")
        return 1

    bundles = leer_conjunto_de_bundles(raiz)
    if not bundles:
        print(f"FALLA  {raiz}: el conjunto no tiene ninguna corrida")
        return 1

    print(f"Conjunto: {raiz} — {len(bundles)} corridas · acta: {ruta_acta}")
    fallas = 0
    medidas = 0
    for bundle in bundles:
        if bundle.error:
            print(f"FALLA  {bundle.directorio}: {bundle.error}")
            fallas += 1
            continue
        observacion, malas = derivar_observacion(
            bundle.datos, bundle.sha256, vocabulario, esquemas["observacion"],
            preregistro.get("reglas_de_derivacion_de_identidad"),
            formulas_del_preregistro(preregistro))
        if observacion is None:
            print(f"FALLA  {bundle.directorio}: no se derivó — "
                  f"{malas[0] if malas else 'sin motivo'}")
            fallas += 1
            continue
        metrica = _metrica_de_la_observacion(observacion, METRICA_DE_HALLAZGOS) or {}
        emisiones = len(hallazgos_del_bundle(bundle.datos))
        distintos = int(_conteo_correcto(bundle.datos))
        if metrica.get("estado_de_medicion") == "medida":
            medidas += 1
            print(f"OK     {bundle.directorio}: {metrica['valor']:g} {metrica.get('unidad')} — "
                  f"{emisiones} emisiones, {distintos} distintos "
                  f"({emisiones - distintos} re-emisiones)")
        else:
            # Sin observación NO es cero: se informa como lo que es, con su adjudicación escrita.
            print(f"SIN    {bundle.directorio}: {metrica.get('estado_de_medicion')} — "
                  f"{metrica.get('adjudicacion')}")
    print()
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {len(bundles)} corridas sin métrica de hallazgos")
        return 1
    # El conteo de medidas va en el veredicto: un conjunto donde NINGUNA se midió también pasa —sin
    # observación es un resultado válido— y decir «OK» a secas se leería como que todas se midieron.
    print(f"RESULTADO: OK — {len(bundles)} corridas revisadas: {medidas} con la métrica medida y "
          f"{len(bundles) - medidas - fallas} sin observación, con su adjudicación escrita")
    return 0


def modo_autotest_hallazgos(args: argparse.Namespace) -> int:
    del args
    manifest, preregistro, vocabulario, esquemas, problemas = _cargar_corpus_de_hallazgos()
    if problemas:
        for p in problemas:
            print(f"[A] FALLA  {p}")
        return 1

    casos = manifest.get("casos") or []
    resultados: list[tuple[str, bool, str]] = []

    # [A] Manifest ↔ disco, en las dos direcciones (D-16).
    raiz = DIR_FIXTURES_HALLAZGOS / "casos"
    declarados = {c["caso_id"] for c in casos}
    en_disco = {d.name for d in raiz.iterdir() if d.is_dir()} if raiz.is_dir() else set()
    diferencias = [f"declarado y ausente del disco: {c}" for c in sorted(declarados - en_disco)]
    diferencias += [f"en disco y no declarado: {c}" for c in sorted(en_disco - declarados)]
    resultados.append(("A", not diferencias,
                       f"manifest ↔ directorio ({len(declarados)} casos)" if not diferencias
                       else " | ".join(diferencias[:6])))

    # [B] Cada caso da el valor declarado —o el estado de medición declarado—. Es donde se prueba
    # que la ausencia NO se publica como cero: el caso sin fórmula elegida espera `no_observada`,
    # y un cero ahí sería un hallazgo contado donde no se midió nada.
    fallas: list[str] = []
    bundles: dict[str, dict] = {}
    for entrada in casos:
        caso_id = entrada["caso_id"]
        bundle = _leer_bundle(raiz / caso_id)
        if bundle.error:
            fallas.append(f"{caso_id}: {bundle.error}")
            continue
        bundles[caso_id] = bundle.datos
        observacion, malas = _observacion_de_hallazgos(
            raiz / caso_id, preregistro, vocabulario, esquemas,
            entrada.get("formula_elegida", True))
        if observacion is None:
            fallas.append(f"{caso_id}: no se derivó — {malas[0] if malas else 'sin motivo'}")
            continue
        metrica = _metrica_de_la_observacion(observacion, METRICA_DE_HALLAZGOS) or {}
        if "valor_esperado" in entrada:
            if metrica.get("estado_de_medicion") != "medida":
                fallas.append(f"{caso_id}: se esperaba {entrada['valor_esperado']} y la métrica "
                              f"salió {metrica.get('estado_de_medicion')}")
            elif not _casi_igual(metrica.get("valor"), entrada["valor_esperado"]):
                fallas.append(f"{caso_id}: vale {metrica.get('valor')} y se esperaba "
                              f"{entrada['valor_esperado']}")
        else:
            if metrica.get("estado_de_medicion") != entrada["estado_esperado"]:
                fallas.append(f"{caso_id}: el estado de medición es "
                              f"{metrica.get('estado_de_medicion')!r} y se esperaba "
                              f"{entrada['estado_esperado']!r}")
            elif "valor" in metrica:
                fallas.append(f"{caso_id}: la métrica sin observación trae `valor` "
                              f"{metrica['valor']}: la ausencia no se publica como un número")
    resultados.append(("B", not fallas,
                       f"{len(casos)} casos dan su valor, y la ausencia no sale en cero"
                       if not fallas else " | ".join(fallas[:4])))

    # [C] La identidad del hallazgo, en las dos direcciones: los casos que el manifest declara como
    # re-emisión tienen que colapsar a uno, y los que declara distintos NO tienen que colapsar.
    # Sin la segunda mitad, una normalización que fusionara todo pasaría la primera.
    fallas_de_identidad: list[str] = []
    for entrada in casos:
        datos = bundles.get(entrada["caso_id"])
        if datos is None or "emisiones_esperadas" not in entrada:
            continue
        emisiones = len(hallazgos_del_bundle(datos))
        distintos = int(_conteo_correcto(datos))
        if emisiones != entrada["emisiones_esperadas"]:
            fallas_de_identidad.append(f"{entrada['caso_id']}: {emisiones} eventos de hallazgo y "
                                       f"se declaran {entrada['emisiones_esperadas']}")
        if distintos != entrada["distintos_esperados"]:
            fallas_de_identidad.append(f"{entrada['caso_id']}: {distintos} identidades distintas y "
                                       f"se declaran {entrada['distintos_esperados']}")
    resultados.append(("C", not fallas_de_identidad,
                       "emisiones e identidades distintas, declaradas por separado en cada caso"
                       if not fallas_de_identidad else " | ".join(fallas_de_identidad[:4])))

    # [D] El corpus separa la regla correcta de cada una de las formas de contar mal. Una regla
    # equivocada que ningún caso distingue de la correcta es un mutante que este corpus no caza, y
    # su verde se lee como si lo hubiera probado.
    sin_separar: list[str] = []
    for nombre, que_hace, regla in REGLAS_DE_CONTEO_ERRADAS:
        if not any(regla(datos) != _conteo_correcto(datos) for datos in bundles.values()):
            sin_separar.append(f"ningún caso separa la regla correcta de «{nombre}» ({que_hace})")
    resultados.append(("D", not sin_separar,
                       f"el corpus separa las {len(REGLAS_DE_CONTEO_ERRADAS)} formas de contar mal"
                       if not sin_separar else " | ".join(sin_separar)))

    # [E] Y la normalización se ejerce en las dos direcciones sobre entradas construidas acá: las
    # variantes de formato del mismo texto colapsan, y dos textos distintos no.
    variantes = ["El adaptador no deja constancia.", "el adaptador no deja constancia",
                 "  El   adaptador  no deja constancia  "]
    distinto = "el adaptador no deja constancia del retiro"
    problemas_de_normalizacion: list[str] = []
    if len({identidad_de_hallazgo(v) for v in variantes}) != 1:
        problemas_de_normalizacion.append("las variantes de formato del mismo hallazgo no colapsan")
    if identidad_de_hallazgo(distinto) in {identidad_de_hallazgo(v) for v in variantes}:
        problemas_de_normalizacion.append("dos hallazgos distintos colapsan en uno: la "
                                          "normalización fusiona lo que no debe")
    resultados.append(("E", not problemas_de_normalizacion,
                       "la normalización colapsa las variantes y no fusiona lo distinto"
                       if not problemas_de_normalizacion
                       else " | ".join(problemas_de_normalizacion)))

    return _cerrar(resultados)


# ---------------------------------------------------------------------------------------------
# Modos `--latencias`, `--autotest-latencias` y `--autotest-reloj`.
#
# AC-19 pide DOS magnitudes y prohíbe compararlas: el tiempo hasta el estado terminal comprobado de
# cada trabajo delegado, y el tiempo hasta el resultado utilizable de la corrida. Viven en sedes
# distintas de la observación justamente para que ningún agregado las junte, y ningún agregador de
# acá toma valores de las dos.
#
# La interfaz de reloj vive en `scripts/interfaz-de-reloj.json` y es lo que esta task PRODUCE: el
# conjunto cerrado de procedencias, la precisión admitida, el redondeo canónico y los invariantes.
# El schema del bundle ya exige que todo sello declare su procedencia, pero como texto libre; sin
# cerrar el conjunto, «declararla» y «que sea una de las que el harness implementa» son dos cosas
# distintas, y un adaptador puede emitir tiempo de pared con la forma correcta.
#
# Los estratos: el de intervención humana se deriva del valor EFECTIVO registrado, y qué muestras lo
# exigen se deriva de la MATRIZ. Un punto que la matriz marca con confirmación del usuario y una
# corrida sin evento de confirmación no se reclasifica como automatizable: bloquea.
# ---------------------------------------------------------------------------------------------

RUTA_INTERFAZ_DE_RELOJ = DIR_SCRIPTS / "interfaz-de-reloj.json"
RUTA_MATRIZ = DIR_SCRIPTS / "matriz-despachos.json"
DIR_FIXTURES_LATENCIAS = DIR_SCRIPTS / "fixtures-baseline" / "latencias"
RUTA_MANIFEST_LATENCIAS = DIR_FIXTURES_LATENCIAS / "manifest.json"

RUTA_OBSERVACIONES_FASE_0 = "scripts/observaciones-fase-0"

LATENCIA_DE_CORRIDA = "latencia-hasta-resultado-utilizable"
LATENCIA_DE_TRABAJO = "latencia-hasta-estado-terminal"


def cargar_interfaz_de_reloj() -> tuple[dict, str | None]:
    return _cargar_json(RUTA_INTERFAZ_DE_RELOJ)


def redondear_canonico(valor: float, interfaz: dict) -> float:
    """El redondeo que la interfaz declara. Sin una regla escrita, el último dígito del número
    publicado lo decide la aritmética de coma flotante, y dos corridas del mismo instrumento sobre
    los mismos sellos pueden diferir."""
    redondeo = interfaz.get("redondeo") or {}
    if redondeo.get("regla") != "half_even":
        return valor
    return round(float(valor), int(redondeo.get("decimales", 3)))


def _sellos_del_bundle(bundle: dict):
    for evento in bundle.get("eventos") or []:
        yield evento, (evento.get("sello") or {})


def revisar_sellos(bundle: dict, interfaz: dict) -> list[str]:
    """Cada sello contra la interfaz declarada: procedencia del conjunto cerrado, precisión dentro
    del rango, y la fuente y la autoridad que la interfaz fija."""
    problemas: list[str] = []
    admitidas = {p.get("procedencia_id"): p
                 for p in interfaz.get("procedencias_admitidas") or []}
    rango = interfaz.get("precision_ns") or {}
    adaptador = bundle.get("adaptador")

    for evento, sello in _sellos_del_bundle(bundle):
        etiqueta = f"{bundle.get('run_id')}/{evento.get('evento_id')}"
        procedencia = sello.get("procedencia")
        if procedencia not in admitidas:
            problemas.append(f"{etiqueta}: la procedencia {procedencia!r} no está en el conjunto "
                             "cerrado de la interfaz de reloj")
        elif adaptador not in (admitidas[procedencia].get("adaptadores") or []):
            problemas.append(f"{etiqueta}: la procedencia {procedencia!r} no está declarada para "
                             f"el adaptador {adaptador!r}")
        if sello.get("fuente") != interfaz.get("fuente"):
            problemas.append(f"{etiqueta}: la fuente es {sello.get('fuente')!r} y la interfaz "
                             f"declara {interfaz.get('fuente')!r}")
        if sello.get("autoridad") != interfaz.get("autoridad"):
            problemas.append(f"{etiqueta}: la autoridad es {sello.get('autoridad')!r} y la "
                             f"interfaz declara {interfaz.get('autoridad')!r}")
        precision = sello.get("precision_ns")
        if not isinstance(precision, int) or isinstance(precision, bool):
            problemas.append(f"{etiqueta}: la precisión no es un entero")
        elif not (rango.get("minimo", 1) <= precision <= rango.get("maximo", 10 ** 9)):
            problemas.append(f"{etiqueta}: precisión {precision} ns fuera del rango declarado "
                             f"[{rango.get('minimo')}, {rango.get('maximo')}]")
    return problemas


def revisar_orden_de_eventos(bundle: dict, interfaz: dict) -> list[str]:
    """Los invariantes de orden y de duración posible. Un evento fuera de orden se RECHAZA: no se
    reordena por sello ni se promedia con el resto."""
    problemas: list[str] = []
    eventos = bundle.get("eventos") or []
    tope = next((i.get("tope_ns") for i in interfaz.get("invariantes") or []
                 if i.get("invariante_id") == "duracion-posible"), None)

    # La secuencia de apertura, en el orden que el schema del bundle declara.
    schema_bundle, error = _cargar_json(CONTRATOS_POR_NOMBRE["bundle-corrida"].ruta)
    orden = ((schema_bundle or {}).get("x-secuencia-de-apertura") or {}).get("orden") or []
    posicion = {tipo: i for i, tipo in enumerate(orden)}
    if error:
        problemas.append(f"secuencia de apertura: {error}")

    ultimos: list[tuple[int, str, int]] = []
    for evento in eventos:
        tipo = evento.get("tipo")
        if tipo not in posicion:
            continue
        ultimos.append((posicion[tipo], evento.get("evento_id"),
                        (evento.get("sello") or {}).get("valor_ns", 0)))
    for anterior, siguiente in zip(ultimos, ultimos[1:]):
        if siguiente[0] < anterior[0]:
            problemas.append(f"{bundle.get('run_id')}: el evento de apertura {siguiente[1]!r} "
                             f"aparece después de {anterior[1]!r} y su orden declarado es el "
                             "inverso")
        if siguiente[2] < anterior[2]:
            problemas.append(f"{bundle.get('run_id')}: el sello de {siguiente[1]!r} es anterior al "
                             f"de {anterior[1]!r}: la secuencia de apertura no es monótona")

    valores = [s.get("valor_ns") for _, s in _sellos_del_bundle(bundle)
               if isinstance(s.get("valor_ns"), int)]
    if valores and tope and (max(valores) - min(valores)) > tope:
        problemas.append(f"{bundle.get('run_id')}: la corrida abarca "
                         f"{max(valores) - min(valores)} ns, por encima del tope declarado "
                         f"({tope} ns): es un sello corrupto o un reloj reiniciado, y se rechaza")
    return problemas


def puntos_que_exigen_confirmacion() -> tuple[set[str], str | None]:
    """De la MATRIZ, no de una lista transcrita acá: qué muestras exigen intervención humana lo
    declara el punto de despacho, y una copia local envejecería en silencio."""
    matriz, error = _cargar_json(RUTA_MATRIZ)
    if error:
        return set(), error
    exigen = set()
    for punto in matriz.get("puntos") or []:
        campo = punto.get("requiere_confirmacion_del_usuario") or {}
        if campo.get("valor") is True:
            exigen.add(punto.get("id"))
    return exigen, None


def revisar_estrato(observacion: dict, bundle: dict, exigen: set[str]) -> list[str]:
    """El estrato contra la matriz. Un punto que exige confirmación y una corrida sin su evento no
    se reclasifica como automatizable: **bloquea siempre**. La salida barata sería tratar la
    ausencia del evento como prueba de que no hizo falta."""
    problemas: list[str] = []
    punto = observacion.get("punto_de_despacho")
    if punto not in exigen:
        return problemas
    hay_evento = bool(_eventos_de_tipo(bundle, "confirmacion_humana"))
    if observacion.get("estrato") == "automatizable":
        problemas.append(
            f"{observacion.get('observation_id')}: el punto «{punto}» exige confirmación del "
            "usuario según la matriz, y la observación se clasificó `automatizable`"
            + ("" if hay_evento else " sin ningún evento de confirmación registrado"))
    elif not hay_evento:
        problemas.append(
            f"{observacion.get('observation_id')}: el punto «{punto}» exige confirmación y no hay "
            "evento que la acredite: el intento bloquea, no se estratifica")
    return problemas


class ValorDeLatencia(NamedTuple):
    observation_id: str
    magnitud: str
    estrato: str
    valor: float


def valores_de_latencia(observacion: dict) -> list[ValorDeLatencia]:
    """Las dos magnitudes, extraídas de sus DOS sedes. Cada valor lleva su magnitud pegada: es lo
    que permite que el agregador rechace una mezcla en vez de promediarla."""
    salida: list[ValorDeLatencia] = []
    estrato = observacion.get("estrato")
    metrica = _metrica_de_la_observacion(observacion, LATENCIA_DE_CORRIDA)
    if metrica and metrica.get("estado_de_medicion") == "medida":
        salida.append(ValorDeLatencia(observacion.get("observation_id"), LATENCIA_DE_CORRIDA,
                                      estrato, metrica["valor"]))
    for trabajo in observacion.get("trabajos_delegados") or []:
        for metrica in trabajo.get("metricas") or []:
            if (metrica.get("metrica_id") == LATENCIA_DE_TRABAJO
                    and metrica.get("estado_de_medicion") == "medida"):
                salida.append(ValorDeLatencia(observacion.get("observation_id"),
                                              LATENCIA_DE_TRABAJO, estrato, metrica["valor"]))
    return salida


def agregar_latencias(valores: list[ValorDeLatencia], vocabulario: dict,
                      interfaz: dict) -> tuple[float | None, str | None]:
    """Agrega un conjunto de latencias, o lo RECHAZA. Rechaza si mezcla las dos magnitudes —AC-19
    prohíbe compararlas— y si mezcla estratos: un promedio global de corridas automatizables y con
    intervención humana no es la latencia de ninguna de las dos poblaciones."""
    if not valores:
        return None, "sin valores que agregar"
    magnitudes = {v.magnitud for v in valores}
    if len(magnitudes) > 1:
        return None, ("el conjunto mezcla las dos magnitudes de latencia, que AC-19 prohíbe "
                      f"comparar: {sorted(magnitudes)}")
    estratos = {v.estrato for v in valores}
    if len(estratos) > 1:
        return None, (f"el conjunto mezcla estratos {sorted(estratos)}: un promedio global no es "
                      "la latencia de ninguna de las dos poblaciones")
    magnitud = magnitudes.pop()
    metrica = next((m for _, m in _metricas_del(vocabulario)
                    if m.get("metrica_id") == magnitud), None)
    if metrica is None:
        return None, f"la magnitud «{magnitud}» no está en el vocabulario"
    agregacion = (_por_id(vocabulario.get("agregaciones") or [], "agregacion_id")
                  .get(metrica.get("agregacion")) or {})
    resolvedor = RESOLVEDORES_DE_AGREGACION.get(agregacion.get("forma"))
    if resolvedor is None:
        return None, f"la agregación «{metrica.get('agregacion')}» no tiene resolvedor"
    valor, error = resolvedor([v.valor for v in valores])
    return (None, error) if error else (redondear_canonico(valor, interfaz), None)


def revisar_reglas_de_latencia(observaciones: list[dict], bundles: dict[str, dict],
                               manifest_de_intentos: dict | None) -> list[str]:
    """Las cuatro reglas que AC-19 exige declarar: reintentos, despachos múltiples, presupuesto
    vencido y muestra incompleta. Cada una tiene su negativo en el corpus."""
    problemas: list[str] = []
    por_muestra: dict[str, list[dict]] = {}
    for observacion in observaciones:
        por_muestra.setdefault(observacion.get("sample_id"), []).append(observacion)

    for observacion in observaciones:
        bundle = bundles.get((observacion.get("procedencia") or {}).get("run_id")) or {}
        etiqueta = observacion.get("observation_id")

        # Despachos múltiples: la ventana no está definida y la latencia se bloquea. Elegir uno de
        # los despachos —el primero, el último— sería fijar metodología desde el instrumento.
        despachos = _eventos_de_tipo(bundle, "despacho")
        metrica = _metrica_de_la_observacion(observacion, LATENCIA_DE_CORRIDA) or {}
        if len(despachos) > 1 and metrica.get("estado_de_medicion") == "medida":
            problemas.append(f"{etiqueta}: la corrida tiene {len(despachos)} despachos y la "
                             "latencia salió medida: con más de una ventana no hay duración que "
                             "publicar")

        # Presupuesto vencido: sin resultado utilizable no hay latencia de corrida, y publicarla en
        # cero la haría indistinguible de una corrida instantánea.
        if (not _eventos_de_tipo(bundle, "resultado_utilizable")
                and metrica.get("estado_de_medicion") == "medida"):
            problemas.append(f"{etiqueta}: no hay evento de resultado utilizable y la latencia "
                             "salió medida")

        # Reintentos: la latencia es POR INTENTO. Dos intentos de la misma muestra no se promedian
        # acá: con qué intento se publica lo fija la política congelada del acta (D-12).
        hermanas = por_muestra.get(observacion.get("sample_id")) or []
        if len(hermanas) > 1 and manifest_de_intentos is None:
            problemas.append(f"{etiqueta}: su muestra tiene {len(hermanas)} intentos y no hay "
                             "política congelada que diga con cuál se publica: agregar acá sería "
                             "elegir después de ver los números")

    # Muestra incompleta: si el manifest declara intentos que no están, el agregado se rechaza en
    # lugar de recomponerse sobre el subconjunto que llegó.
    if manifest_de_intentos is not None:
        esperados = {(e.get("sample_id"), e.get("attempt_ordinal"))
                     for e in manifest_de_intentos.get("intentos") or []}
        observados = {(o.get("sample_id"), o.get("attempt_ordinal")) for o in observaciones}
        faltantes = sorted(esperados - observados)
        if faltantes:
            problemas.append(f"muestra incompleta: faltan {len(faltantes)} intentos declarados "
                             f"({faltantes[0]} y otros): el agregado se rechaza en vez de "
                             "recomponerse sobre lo que llegó")
    return problemas


def modo_latencias(args: argparse.Namespace) -> int:
    raiz = _ruta_absoluta(getattr(args, "latencias"))
    dir_bundles = _ruta_absoluta(getattr(args, "bundles", None) or RUTA_CORRIDAS_FASE_0)
    interfaz, error = cargar_interfaz_de_reloj()
    if error:
        print(f"FALLA  interfaz de reloj: {error}")
        return 1
    vocabulario, esquemas, problemas = _cargar_insumos_de_recoleccion()
    exigen, error = puntos_que_exigen_confirmacion()
    if error:
        problemas.append(f"matriz de despachos: {error}")
    if problemas:
        for p in problemas:
            print(f"FALLA  {p}")
        return 1

    if not raiz.is_dir():
        print(f"FALLA  {raiz}: no hay directorio de observaciones que revisar")
        return 1
    observaciones: list[dict] = []
    for archivo in sorted(raiz.glob("*.json")):
        datos, error = _cargar_json(archivo)
        if error:
            print(f"FALLA  {archivo.name}: {error}")
            return 1
        observaciones.append(datos)
    if not observaciones:
        print(f"FALLA  {raiz}: el directorio no tiene ninguna observación")
        return 1

    bundles: dict[str, dict] = {}
    faltantes: list[str] = []
    for observacion in observaciones:
        run_id = (observacion.get("procedencia") or {}).get("run_id")
        bundle = _leer_bundle(dir_bundles / run_id)
        if bundle.error:
            faltantes.append(f"{run_id}: {bundle.error}")
            continue
        bundles[run_id] = bundle.datos

    print(f"Observaciones: {raiz} ({len(observaciones)}) · bundles: {dir_bundles}")
    revisiones: list[tuple[str, list[str]]] = [
        ("procedencia y precisión de cada sello",
         faltantes + [p for b in bundles.values() for p in revisar_sellos(b, interfaz)]),
        ("orden de la apertura y duración posible",
         [p for b in bundles.values() for p in revisar_orden_de_eventos(b, interfaz)]),
        ("estratos derivados del valor efectivo y exigidos por la matriz",
         [p for o in observaciones
          for p in revisar_estrato(o, bundles.get((o.get("procedencia") or {}).get("run_id")) or {},
                                   exigen)]),
        ("reglas de reintento, despacho múltiple, presupuesto vencido y muestra incompleta",
         revisar_reglas_de_latencia(observaciones, bundles,
                                    getattr(args, "_manifest_de_intentos", None))),
    ]

    # Y las dos magnitudes, agregadas por separado y por estrato. Es donde se ve que no se mezclan:
    # un agregado por magnitud × estrato, nunca uno global.
    todos = [v for o in observaciones for v in valores_de_latencia(o)]
    grupos: dict[tuple[str, str], list[ValorDeLatencia]] = {}
    for valor in todos:
        grupos.setdefault((valor.magnitud, valor.estrato), []).append(valor)
    mezcla = agregar_latencias(todos, vocabulario, interfaz)[1] if len(
        {(v.magnitud) for v in todos}) > 1 else None

    rojos = 0
    for etiqueta, problemas_de_la_revision in revisiones:
        if problemas_de_la_revision:
            rojos += 1
            print(f"FALLA  {etiqueta} — {len(problemas_de_la_revision)}:")
            for problema in problemas_de_la_revision[:6]:
                print(f"       - {problema}")
        else:
            print(f"OK     {etiqueta}")

    print()
    for (magnitud, estrato), valores in sorted(grupos.items()):
        agregado, error = agregar_latencias(valores, vocabulario, interfaz)
        detalle = f"{agregado:g}" if error is None else f"sin agregar — {error}"
        print(f"       {magnitud} · {estrato}: {len(valores)} valores → {detalle}")
    if mezcla:
        print(f"       las dos magnitudes NO se agregan juntas: {mezcla}")

    print()
    if rojos:
        print(f"RESULTADO: FALLA — {rojos} revisiones en rojo")
        return 1
    print(f"RESULTADO: OK — {len(observaciones)} observaciones con sus latencias verificadas, en "
          f"{len(grupos)} grupos de magnitud × estrato")
    return 0


def _observacion_de_latencias(caso_id: str, preregistro: dict, vocabulario: dict,
                              esquemas: dict) -> tuple[dict | None, dict | None, list[str]]:
    bundle = _leer_bundle(DIR_FIXTURES_LATENCIAS / "casos" / caso_id)
    if bundle.error:
        return None, None, [f"{caso_id}: {bundle.error}"]
    observacion, fallas = derivar_observacion(
        bundle.datos, bundle.sha256, vocabulario, esquemas["observacion"],
        preregistro.get("reglas_de_derivacion_de_identidad"),
        formulas_del_preregistro(preregistro))
    return observacion, bundle.datos, [f"{caso_id}: {f}" for f in fallas]


def modo_autotest_latencias(args: argparse.Namespace) -> int:
    solo_estratos = bool(getattr(args, "estratos", False))
    manifest, error = _cargar_json(RUTA_MANIFEST_LATENCIAS)
    if error:
        print(f"[A] FALLA  manifest del corpus de latencias: {error}")
        return 1
    preregistro, error = _cargar_json(DIR_FIXTURES_LATENCIAS / "preregistro.json")
    if error:
        print(f"[A] FALLA  pre-registro del corpus de latencias: {error}")
        return 1
    interfaz, error = cargar_interfaz_de_reloj()
    if error:
        print(f"[A] FALLA  interfaz de reloj: {error}")
        return 1
    vocabulario, esquemas, problemas = _cargar_insumos_de_recoleccion()
    exigen, error = puntos_que_exigen_confirmacion()
    if error:
        problemas.append(f"matriz de despachos: {error}")
    if problemas:
        for p in problemas:
            print(f"[A] FALLA  {p}")
        return 1

    casos = manifest.get("casos") or []
    resultados: list[tuple[str, bool, str]] = []

    # [A] Manifest ↔ disco, en las dos direcciones (D-16).
    raiz = DIR_FIXTURES_LATENCIAS / "casos"
    declarados = {c["caso_id"] for c in casos}
    en_disco = {d.name for d in raiz.iterdir() if d.is_dir()} if raiz.is_dir() else set()
    diferencias = [f"declarado y ausente del disco: {c}" for c in sorted(declarados - en_disco)]
    diferencias += [f"en disco y no declarado: {c}" for c in sorted(en_disco - declarados)]
    resultados.append(("A", not diferencias,
                       f"manifest ↔ directorio ({len(declarados)} casos)" if not diferencias
                       else " | ".join(diferencias[:6])))

    observaciones: dict[str, dict] = {}
    bundles: dict[str, dict] = {}
    fallas: list[str] = []
    for entrada in casos:
        observacion, bundle, malas = _observacion_de_latencias(entrada["caso_id"], preregistro,
                                                               vocabulario, esquemas)
        if bundle is not None:
            bundles[entrada["caso_id"]] = bundle
        if observacion is None:
            if not entrada.get("no_derivable"):
                fallas.append(malas[0] if malas else f"{entrada['caso_id']}: no se derivó")
            continue
        observaciones[entrada["caso_id"]] = observacion

    if not solo_estratos:
        # [B] Las dos magnitudes, cada una en su sede y con el valor declarado. Un caso que
        # declarara solo «la latencia» no distinguiría cuál de las dos se movió.
        for entrada in casos:
            observacion = observaciones.get(entrada["caso_id"])
            if observacion is None:
                continue
            for magnitud, esperado in (entrada.get("magnitudes_esperadas") or {}).items():
                obtenido = None
                if magnitud == LATENCIA_DE_CORRIDA:
                    metrica = _metrica_de_la_observacion(observacion, magnitud) or {}
                else:
                    metrica = next((m for t in observacion.get("trabajos_delegados") or []
                                    for m in t.get("metricas") or []
                                    if m.get("metrica_id") == magnitud), {})
                obtenido = (metrica.get("valor") if metrica.get("estado_de_medicion") == "medida"
                            else metrica.get("estado_de_medicion"))
                if isinstance(esperado, (int, float)) and isinstance(obtenido, (int, float)):
                    if not _casi_igual(obtenido, esperado):
                        fallas.append(f"{entrada['caso_id']}/{magnitud}: vale {obtenido} y se "
                                      f"esperaba {esperado}")
                elif obtenido != esperado:
                    fallas.append(f"{entrada['caso_id']}/{magnitud}: es {obtenido!r} y se esperaba "
                                  f"{esperado!r}")
        resultados.append(("B", not fallas,
                           f"{len(observaciones)} casos con sus dos magnitudes en sus dos sedes"
                           if not fallas else " | ".join(fallas[:4])))

        # [C] Un negativo por regla, cada uno con su ESCENARIO: unas reglas se rompen con una
        # sola observación y otras necesitan un conjunto —reintentos son dos intentos de la misma
        # muestra, y la muestra incompleta es un manifest que declara uno que no llegó—. Donde el
        # recolector ya emite la métrica sin valor, el escenario la fuerza a `medida`: es la única
        # forma de comprobar que la regla dispara, porque un instrumento sano nunca produce esa
        # observación.
        fallas_de_regla: list[str] = []
        reglas_ejercidas: set[str] = set()
        for escenario in manifest.get("escenarios_de_regla") or []:
            regla = escenario["regla"]
            reglas_ejercidas.add(regla)
            del_escenario: list[dict] = []
            bundles_del_escenario: dict[str, dict] = {}
            for caso_id in escenario["casos"]:
                observacion = observaciones.get(caso_id)
                if observacion is None:
                    fallas_de_regla.append(f"{regla}: el caso {caso_id} no se derivó")
                    continue
                observacion = copy.deepcopy(observacion)
                if escenario.get("forzar_metrica_medida"):
                    for metrica in observacion.get("metricas") or []:
                        if metrica.get("metrica_id") == LATENCIA_DE_CORRIDA:
                            metrica.clear()
                            metrica.update({"metrica_id": LATENCIA_DE_CORRIDA,
                                            "categoria": "latencia",
                                            "estado_de_medicion": "medida", "valor": 1.0,
                                            "unidad": "milisegundos"})
                del_escenario.append(observacion)
                bundles_del_escenario[(observacion.get("procedencia") or {}).get("run_id")] = (
                    bundles[caso_id])
            if not del_escenario:
                continue
            problemas_de_regla = revisar_reglas_de_latencia(
                del_escenario, bundles_del_escenario, escenario.get("manifest_de_intentos"))
            if not any(escenario["motivo_esperado"] in p for p in problemas_de_regla):
                fallas_de_regla.append(
                    f"{regla}: no se rompe por «{escenario['motivo_esperado']}» — se vio: "
                    f"{problemas_de_regla[0] if problemas_de_regla else 'nada'}")
        faltan = sorted(set(manifest.get("reglas_obligatorias") or []) - reglas_ejercidas)
        fallas_de_regla += [f"regla obligatoria sin ningún negativo: {r}" for r in faltan]
        sobran = sorted(reglas_ejercidas - set(manifest.get("reglas_obligatorias") or []))
        fallas_de_regla += [f"escenario de una regla que el manifest no declara: {r}"
                            for r in sobran]
        resultados.append(("C", not fallas_de_regla,
                           f"las {len(reglas_ejercidas)} reglas obligatorias, cada una con su "
                           "negativo" if not fallas_de_regla else " | ".join(fallas_de_regla[:4])))

    # [D] Los estratos: ninguna corrida sin evento de confirmación se reclasifica como
    # automatizable, y qué muestras lo exigen sale de la MATRIZ.
    fallas_de_estrato: list[str] = []
    ejercido = False
    for entrada in casos:
        observacion = observaciones.get(entrada["caso_id"])
        if observacion is None or "estrato_esperado" not in entrada:
            continue
        if observacion.get("estrato") != entrada["estrato_esperado"]:
            fallas_de_estrato.append(f"{entrada['caso_id']}: estrato "
                                     f"{observacion.get('estrato')!r} y se esperaba "
                                     f"{entrada['estrato_esperado']!r}")
        problemas_de_estrato = revisar_estrato(observacion, bundles[entrada["caso_id"]], exigen)
        if entrada.get("reclasificacion_indebida"):
            ejercido = True
            if not problemas_de_estrato:
                fallas_de_estrato.append(f"{entrada['caso_id']}: se clasificó automatizable en un "
                                         "punto que exige confirmación y nadie lo detectó")
        elif problemas_de_estrato:
            fallas_de_estrato.append(f"{entrada['caso_id']}: {problemas_de_estrato[0]}")
    if not ejercido:
        fallas_de_estrato.append("ningún caso intenta la reclasificación indebida: el control no "
                                 "tiene quien lo ponga rojo")
    resultados.append(("D", not fallas_de_estrato,
                       "los estratos salen del valor efectivo y la matriz, y la reclasificación "
                       "indebida se detecta" if not fallas_de_estrato
                       else " | ".join(fallas_de_estrato[:4])))

    # [E] El agregador rechaza entradas mixtas: las dos magnitudes juntas, y dos estratos juntos.
    # Y acepta lo homogéneo, que es la otra mitad: uno que rechazara todo pasaría la primera.
    valores = [v for o in observaciones.values() for v in valores_de_latencia(o)]
    por_grupo: dict[tuple[str, str], list[ValorDeLatencia]] = {}
    for valor in valores:
        por_grupo.setdefault((valor.magnitud, valor.estrato), []).append(valor)
    problemas_de_mezcla: list[str] = []
    # Cada mezcla se prueba AISLADA: un conjunto que mezcle las dos cosas a la vez lo rechaza el
    # primer control que dispare, y el otro queda sin ejercer. El de magnitudes va sobre un solo
    # estrato, y el de estratos sobre una sola magnitud.
    mixto_por_magnitud = [v for v in valores if v.estrato == "automatizable"]
    if len({v.magnitud for v in mixto_por_magnitud}) > 1 and agregar_latencias(
            mixto_por_magnitud, vocabulario, interfaz)[1] is None:
        problemas_de_mezcla.append("el agregador promedió las dos magnitudes juntas")
    elif len({v.magnitud for v in mixto_por_magnitud}) < 2:
        problemas_de_mezcla.append("ningún estrato del corpus tiene las dos magnitudes: la mezcla "
                                   "de magnitudes no se ejerce")
    mixto_por_estrato = [v for v in valores if v.magnitud == LATENCIA_DE_CORRIDA]
    if len({v.estrato for v in mixto_por_estrato}) > 1 and agregar_latencias(
            mixto_por_estrato, vocabulario, interfaz)[1] is None:
        problemas_de_mezcla.append("el agregador promedió dos estratos juntos")
    elif len({v.estrato for v in mixto_por_estrato}) < 2:
        problemas_de_mezcla.append("la magnitud de corrida no aparece en dos estratos: la mezcla "
                                   "de estratos no se ejerce")
    if not por_grupo:
        problemas_de_mezcla.append("no hay ningún grupo homogéneo que agregar")
    for grupo, homogeneos in sorted(por_grupo.items()):
        _, error = agregar_latencias(homogeneos, vocabulario, interfaz)
        if error:
            problemas_de_mezcla.append(f"el agregador rechaza el grupo homogéneo {grupo}: {error}")
    resultados.append(("E", not problemas_de_mezcla,
                       f"el agregador rechaza las mezclas y acepta los {len(por_grupo)} grupos "
                       "homogéneos" if not problemas_de_mezcla
                       else " | ".join(problemas_de_mezcla[:4])))

    return _cerrar(resultados)


def modo_autotest_reloj(args: argparse.Namespace) -> int:
    del args
    interfaz, error = cargar_interfaz_de_reloj()
    if error:
        print(f"[A] FALLA  interfaz de reloj: {error}")
        return 1
    vocabulario, esquemas, problemas = _cargar_insumos_de_recoleccion()
    if problemas:
        for p in problemas:
            print(f"[A] FALLA  {p}")
        return 1

    resultados: list[tuple[str, bool, str]] = []

    # [A] La interfaz declara lo que el schema no puede: un conjunto CERRADO de procedencias, el
    # rango de precisión y el redondeo. Y su fuente y autoridad coinciden con las constantes que el
    # schema del bundle fija, que es la tercera pata que nadie escribió para esta fila.
    schema_bundle = esquemas["bundle-corrida"]
    sello = (schema_bundle.get("$defs") or {}).get("sello") or {}
    propiedades = sello.get("properties") or {}
    problemas_de_interfaz: list[str] = []
    if propiedades.get("fuente", {}).get("const") != interfaz.get("fuente"):
        problemas_de_interfaz.append("la fuente de la interfaz no coincide con la constante del "
                                     "schema de bundle")
    if propiedades.get("autoridad", {}).get("const") != interfaz.get("autoridad"):
        problemas_de_interfaz.append("la autoridad de la interfaz no coincide con la constante del "
                                     "schema de bundle")
    if not interfaz.get("procedencias_admitidas"):
        problemas_de_interfaz.append("la interfaz no cierra el conjunto de procedencias")
    adaptadores = set((schema_bundle.get("$defs") or {}).get("enum_adaptador", {}).get("enum") or [])
    cubiertos = {a for p in interfaz.get("procedencias_admitidas") or []
                 for a in p.get("adaptadores") or []}
    if adaptadores - cubiertos:
        problemas_de_interfaz.append(f"adaptadores sin ninguna procedencia declarada: "
                                     f"{sorted(adaptadores - cubiertos)} — los DOS cargan las "
                                     "mismas obligaciones (D-5)")
    resultados.append(("A", not problemas_de_interfaz,
                       f"la interfaz cierra {len(interfaz.get('procedencias_admitidas') or [])} "
                       f"procedencias para los {len(adaptadores)} adaptadores, y coincide con el "
                       "schema" if not problemas_de_interfaz
                       else " | ".join(problemas_de_interfaz)))

    # [B] Un evento fuera de orden y una duración imposible se RECHAZAN. Se construyen acá, en las
    # dos direcciones: el bundle sano no dispara nada, y cada ataque dispara lo suyo.
    base = {
        "run_id": "run-reloj", "adaptador": "script",
        "eventos": [
            {"evento_id": "e1", "tipo": "validacion_de_hash_congelado",
             "sello": {"valor_ns": 100, "fuente": "reloj_monotonico_del_harness",
                       "autoridad": "harness", "precision_ns": 1000,
                       "procedencia": "time.monotonic_ns del proceso del runner"}},
            {"evento_id": "e2", "tipo": "preflight_de_receta",
             "sello": {"valor_ns": 200, "fuente": "reloj_monotonico_del_harness",
                       "autoridad": "harness", "precision_ns": 1000,
                       "procedencia": "time.monotonic_ns del proceso del runner"}},
            {"evento_id": "e3", "tipo": "despacho",
             "sello": {"valor_ns": 300, "fuente": "reloj_monotonico_del_harness",
                       "autoridad": "harness", "precision_ns": 1000,
                       "procedencia": "time.monotonic_ns del proceso del runner"}},
        ],
    }
    ataques: list[tuple[str, Callable[[dict], None], str]] = [
        ("evento-fuera-de-orden",
         lambda b: b["eventos"].insert(0, b["eventos"].pop(2)), "orden declarado es el inverso"),
        ("sello-no-monotono",
         lambda b: b["eventos"][2]["sello"].__setitem__("valor_ns", 50), "es anterior al de"),
        ("duracion-imposible",
         lambda b: b["eventos"][2]["sello"].__setitem__("valor_ns", 10 ** 15),
         "por encima del tope declarado"),
    ]
    problemas_de_orden: list[str] = []
    if revisar_orden_de_eventos(copy.deepcopy(base), interfaz):
        problemas_de_orden.append("el bundle sano ya dispara el control de orden")
    for nombre, aplicar, motivo in ataques:
        copia = copy.deepcopy(base)
        aplicar(copia)
        detectados = revisar_orden_de_eventos(copia, interfaz)
        if not any(motivo in d for d in detectados):
            problemas_de_orden.append(f"«{nombre}» no se rechaza por «{motivo}» — se vio: "
                                      f"{detectados[0] if detectados else 'nada'}")
    resultados.append(("B", not problemas_de_orden,
                       f"{len(ataques)} ataques al orden y a la duración se rechazan, y el bundle "
                       "sano no" if not problemas_de_orden else " | ".join(problemas_de_orden)))

    # [C] La procedencia y la precisión, en las dos direcciones.
    ataques_de_sello: list[tuple[str, Callable[[dict], None], str]] = [
        ("procedencia-de-pared",
         lambda b: b["eventos"][0]["sello"].__setitem__("procedencia", "reloj de pared del host"),
         "no está en el conjunto cerrado"),
        ("procedencia-de-otro-adaptador",
         lambda b: b.__setitem__("adaptador", "adaptador-inventado"),
         "no está declarada para el adaptador"),
        ("precision-fuera-de-rango",
         lambda b: b["eventos"][0]["sello"].__setitem__("precision_ns", 10 ** 9),
         "fuera del rango declarado"),
        ("autoridad-del-worker",
         lambda b: b["eventos"][0]["sello"].__setitem__("autoridad", "worker"),
         "la autoridad es"),
    ]
    problemas_de_sello: list[str] = []
    if revisar_sellos(copy.deepcopy(base), interfaz):
        problemas_de_sello.append("el bundle sano ya dispara el control de sellos")
    for nombre, aplicar, motivo in ataques_de_sello:
        copia = copy.deepcopy(base)
        aplicar(copia)
        detectados = revisar_sellos(copia, interfaz)
        if not any(motivo in d for d in detectados):
            problemas_de_sello.append(f"«{nombre}» no se rechaza por «{motivo}» — se vio: "
                                      f"{detectados[0] if detectados else 'nada'}")
    resultados.append(("C", not problemas_de_sello,
                       f"{len(ataques_de_sello)} ataques al sello se rechazan, y el sano no"
                       if not problemas_de_sello else " | ".join(problemas_de_sello)))

    # [D] El redondeo canónico, ejercido sobre los casos que lo requieren. Sin regla declarada, el
    # último dígito lo decide la coma flotante; con `half_even`, el empate va al par.
    casos_de_redondeo = [(1.0005, 1.0), (1.0015, 1.002), (2.5, 2.5), (184300.0, 184300.0),
                         (0.0004, 0.0)]
    problemas_de_redondeo = [f"{valor} redondea a {redondear_canonico(valor, interfaz)} y se "
                             f"esperaba {esperado}"
                             for valor, esperado in casos_de_redondeo
                             if not _casi_igual(redondear_canonico(valor, interfaz), esperado)]
    sin_redondeo = {"redondeo": {"regla": "ninguna"}}
    if _casi_igual(redondear_canonico(1.0015, sin_redondeo), 1.002):
        problemas_de_redondeo.append("el redondeo se aplica aunque la interfaz no lo declare: no "
                                     "sale de la interfaz")
    resultados.append(("D", not problemas_de_redondeo,
                       f"{len(casos_de_redondeo)} casos de redondeo canónico, y la regla sale de "
                       "la interfaz" if not problemas_de_redondeo
                       else " | ".join(problemas_de_redondeo[:4])))

    return _cerrar(resultados)


# ---------------------------------------------------------------------------------------------
# Modos `--recomponer`, `--autotest-recomposicion` y `--autotest-procedencia-dag`.
#
# Un número publicado que no se puede reconstruir no es una medición: es una afirmación. La
# recomposición reconstruye cada número **desde la fuente canónica de su clase** —las mediciones
# desde las observaciones, la metodología desde el pre-registro, el presupuesto contractual desde la
# matriz— y falla ante faltante, sobrante o duplicado EN LUGAR de recomponer sobre el subconjunto
# que llegó. Recomponer sobre lo que hay siempre cierra: da un número, y ese número no es el del
# conjunto que se pre-registró.
#
# El grafo de procedencia vive en `scripts/dag-procedencia.json` y es lo que hace comprobable la
# frase «cada insumo con una sola fuente canónica»: sin declararlo, dos sedes para la misma clase de
# dato se resuelven eligiendo la que da el número esperado.
# ---------------------------------------------------------------------------------------------

RUTA_DAG_PROCEDENCIA = DIR_SCRIPTS / "dag-procedencia.json"
DIR_FIXTURES_RECOMPOSICION = DIR_SCRIPTS / "fixtures-baseline" / "recomposicion"
RUTA_MANIFEST_RECOMPOSICION = DIR_FIXTURES_RECOMPOSICION / "manifest.json"


def cargar_dag() -> tuple[dict, str | None]:
    return _cargar_json(RUTA_DAG_PROCEDENCIA)


def revisar_dag(dag: dict) -> list[str]:
    """El grafo consigo mismo: una sola fuente canónica por clase, sin ciclos, sin dependencias que
    apunten a nodos inexistentes y sin nodos derivados que no dependan de nada."""
    problemas: list[str] = []
    nodos = {n.get("nodo_id"): n for n in dag.get("nodos") or []}
    if len(nodos) != len(dag.get("nodos") or []):
        problemas.append("hay identificadores de nodo repetidos")

    # Una clase de dato, una fuente. Con dos, una discrepancia entre ellas no tiene resolución
    # declarada y se elige la que da el número esperado.
    por_clase: dict[str, list[str]] = {}
    for clase in dag.get("clases_de_dato") or []:
        por_clase.setdefault(clase.get("clase"), []).append(clase.get("fuente_canonica"))
    for clase, fuentes in sorted(por_clase.items()):
        if len(fuentes) > 1:
            problemas.append(f"la clase «{clase}» declara {len(fuentes)} fuentes canónicas "
                             f"({sorted(fuentes)}): con dos, la discrepancia se resuelve eligiendo")
        if fuentes[0] not in nodos:
            problemas.append(f"la clase «{clase}» apunta a un nodo inexistente: {fuentes[0]!r}")

    for nodo_id, nodo in sorted(nodos.items()):
        dependencias = nodo.get("depende_de") or []
        if nodo.get("es_raiz"):
            if dependencias:
                problemas.append(f"el nodo raíz «{nodo_id}» declara dependencias")
            continue
        if not dependencias:
            problemas.append(f"el nodo derivado «{nodo_id}» no depende de nada y no es raíz")
        if not nodo.get("formula"):
            problemas.append(f"el nodo derivado «{nodo_id}» no declara con qué fórmula se produce")
        for dependencia in dependencias:
            if dependencia not in nodos:
                problemas.append(f"«{nodo_id}» depende de «{dependencia}», que no existe")

    # Aciclicidad, por recorrido en profundidad. El ciclo INDIRECTO es el que sobrevive a una
    # revisión por inspección, así que la detección no puede ser «ningún nodo se nombra a sí mismo».
    estado: dict[str, int] = {}

    def visitar(nodo_id: str, camino: list[str]) -> None:
        if estado.get(nodo_id) == 2:
            return
        if estado.get(nodo_id) == 1:
            ciclo = camino[camino.index(nodo_id):] + [nodo_id]
            problemas.append(f"ciclo en la procedencia: {' → '.join(ciclo)}")
            return
        estado[nodo_id] = 1
        for dependencia in (nodos.get(nodo_id) or {}).get("depende_de") or []:
            if dependencia in nodos:
                visitar(dependencia, camino + [nodo_id])
        estado[nodo_id] = 2

    for nodo_id in nodos:
        visitar(nodo_id, [])

    for arista in dag.get("aristas") or []:
        for extremo in ("de", "a"):
            if arista.get(extremo) not in nodos:
                problemas.append(f"la arista «{arista.get('arista_id')}» apunta a un nodo "
                                 f"inexistente en `{extremo}`: {arista.get(extremo)!r}")
        minimo = arista.get("minimo")
        if not isinstance(minimo, int) or minimo < 0:
            problemas.append(f"la arista «{arista.get('arista_id')}» no declara un mínimo entero")
    return problemas


class Cardinalidad(NamedTuple):
    """Lo observado en una arista: por cada origen, qué destinos aparecieron."""
    arista_id: str
    por_origen: dict[str, list[str]]


def revisar_cardinalidades(dag: dict, observado: dict[str, Cardinalidad],
                           esperado: dict[str, set[str]],
                           destinos: dict[str, dict[str, set[str]]] | None = None) -> list[str]:
    """Cada arista contra su cardinalidad declarada, contra el conjunto ESPERADO de orígenes y
    contra los destinos que cada origen tiene que tener.

    Sin el esperado de orígenes, un origen que falta entero no se ve: sus destinos tampoco están y
    la cardinalidad de lo que quedó cierra perfecta. Y sin el de destinos, perder UNO de los varios
    destinos de un origen tampoco se ve: la arista `muestra-a-intentos` admite «uno o más», así que
    una muestra con dos intentos sigue cumpliendo con uno. El conjunto de destinos lo congela el
    manifest independiente, no el grafo."""
    problemas: list[str] = []
    for arista in dag.get("aristas") or []:
        arista_id = arista.get("arista_id")
        medida = observado.get(arista_id)
        if medida is None:
            continue
        minimo, maximo = arista.get("minimo"), arista.get("maximo")
        origenes_esperados = esperado.get(arista_id)
        if origenes_esperados is not None:
            faltantes = sorted(origenes_esperados - set(medida.por_origen))
            sobrantes = sorted(set(medida.por_origen) - origenes_esperados)
            problemas += [f"{arista_id}: falta el origen {o!r}" for o in faltantes]
            problemas += [f"{arista_id}: sobra el origen {o!r}, que nadie declara" for o in sobrantes]
        esperados_por_origen = (destinos or {}).get(arista_id) or {}
        for origen, observados in sorted(medida.por_origen.items()):
            declarados = esperados_por_origen.get(origen)
            if declarados is not None:
                problemas += [f"{arista_id}: al origen {origen!r} le falta el destino {d!r}"
                              for d in sorted(declarados - set(observados))]
                problemas += [f"{arista_id}: el origen {origen!r} tiene el destino {d!r}, que "
                              "nadie declara" for d in sorted(set(observados) - declarados)]
            if len(observados) != len(set(observados)):
                repetidos = sorted({d for d in observados if observados.count(d) > 1})
                problemas.append(f"{arista_id}: el origen {origen!r} tiene destinos duplicados "
                                 f"{repetidos}: un duplicado no es una segunda medición")
            if minimo is not None and len(observados) < minimo:
                problemas.append(f"{arista_id}: el origen {origen!r} tiene {len(observados)} "
                                 f"destinos y el mínimo declarado es {minimo}")
            if maximo is not None and len(observados) > maximo:
                problemas.append(f"{arista_id}: el origen {origen!r} tiene {len(observados)} "
                                 f"destinos y el máximo declarado es {maximo}")
    return problemas


def cardinalidades_observadas(preregistro: dict, manifest_de_intentos: dict,
                              observaciones: list[dict],
                              bundles: dict[str, dict]) -> dict[str, Cardinalidad]:
    """Lo que el conjunto real tiene, arista por arista."""
    muestras = [m.get("sample_id") for m in
                ((preregistro.get("cohorte") or {}).get("muestras") or [])]
    por_muestra: dict[str, list[str]] = {}
    por_intento: dict[str, list[str]] = {}
    por_bundle: dict[str, list[str]] = {}
    for observacion in observaciones:
        muestra = observacion.get("sample_id")
        intento = observacion.get("attempt_id")
        run_id = (observacion.get("procedencia") or {}).get("run_id")
        por_muestra.setdefault(muestra, []).append(intento)
        if run_id in bundles:
            por_intento.setdefault(intento, []).append(run_id)
        por_bundle.setdefault(run_id, []).append(observacion.get("observation_id"))

    return {
        "manifest-a-muestras": Cardinalidad(
            "manifest-a-muestras", {"manifest": list(muestras)}),
        "muestra-a-intentos": Cardinalidad("muestra-a-intentos", por_muestra),
        "intento-a-bundle": Cardinalidad("intento-a-bundle", por_intento),
        "bundle-a-observacion": Cardinalidad("bundle-a-observacion", por_bundle),
        "muestras-a-agregado": Cardinalidad(
            "muestras-a-agregado", {"agregado": list(por_muestra)}),
    }


class Recomposicion(NamedTuple):
    metrica_id: str
    valor: float | None
    error: str | None
    por_muestra: dict[str, float]


def insumo_de_agregacion(metrica_id: str, observaciones: list[dict], politica: dict,
                         vocabulario: dict) -> tuple[Any, str | None]:
    """Lo que una muestra aporta al agregado ENTRE muestras, que no siempre es su valor publicable.

    En una métrica publicada como tasa, el valor de la muestra es un cociente y el agregado se hace
    sumando numeradores y denominadores y dividiendo una sola vez: promediar los cocientes pesaría
    igual una muestra con un elegible que una con veinte. Así que el insumo es el PAR, aunque lo que
    se publique de esa muestra sea el cociente. Para el resto de las métricas, insumo y valor son lo
    mismo."""
    metrica = next((m for _, m in _metricas_del(vocabulario)
                    if m.get("metrica_id") == metrica_id), None)
    if metrica is None:
        return None, f"«{metrica_id}» no está en el vocabulario"
    if metrica.get("publicacion") != "tasa":
        return aplicar_seleccion_por_metrica(metrica_id, observaciones, politica, vocabulario)

    regla = next((s.get("regla") for s in politica.get("seleccion_por_metrica") or []
                  if s.get("metrica_id") == metrica_id), None)
    if regla is None:
        return None, f"la política congelada no declara regla de selección para «{metrica_id}»"
    ordenadas = sorted(observaciones, key=lambda o: o.get("attempt_ordinal", 0))
    if regla == "agregacion":
        elegidas = ordenadas
    elif regla == "primer_intento_valido":
        elegidas = [o for o in ordenadas
                    if (o.get("estado") or {}).get("validez_del_reporte") == "valido"][:1]
    elif regla == "primer_intento":
        elegidas = ordenadas[:1]
    elif regla == "ultimo_intento":
        elegidas = ordenadas[-1:]
    else:
        return None, f"regla de selección no implementada: «{regla}»"

    arriba = abajo = 0.0
    aportaron = 0
    for observacion in elegidas:
        medida = _metrica_de_la_observacion(observacion, metrica_id) or {}
        if medida.get("estado_de_medicion") != "medida" or "numerador" not in medida:
            continue
        arriba += medida["numerador"]
        abajo += medida["denominador"]
        aportaron += 1
    if not aportaron:
        return None, (f"ningún intento elegido por «{regla}» aporta numerador y denominador: la "
                      "tasa de la muestra no es auditable")
    return [arriba, abajo], None


def recomponer_metricas(preregistro: dict, observaciones: list[dict],
                        vocabulario: dict) -> list[Recomposicion]:
    """Cada número del baseline, reconstruido desde su fuente canónica: el valor por muestra sale de
    las observaciones con la regla de selección congelada, y el agregado sale de esas muestras con
    la regla de agregación del acta. Ningún paso lee el baseline publicado."""
    politica = preregistro.get("politica_de_reintentos") or {}
    por_muestra: dict[str, list[dict]] = {}
    for observacion in observaciones:
        por_muestra.setdefault(observacion.get("sample_id"), []).append(observacion)

    salida: list[Recomposicion] = []
    for metrica_pre in preregistro.get("metricas") or []:
        metrica_id = metrica_pre.get("metrica_id")
        valores_por_muestra: dict[str, float] = {}
        errores: list[str] = []
        insumos: dict[str, Any] = {}
        for sample_id, intentos in sorted(por_muestra.items()):
            valor, error = aplicar_seleccion_por_metrica(metrica_id, intentos, politica,
                                                         vocabulario)
            insumo, error_de_insumo = insumo_de_agregacion(metrica_id, intentos, politica,
                                                           vocabulario)
            if error or error_de_insumo:
                errores.append(f"{sample_id}: {error or error_de_insumo}")
                continue
            valores_por_muestra[sample_id] = valor
            insumos[sample_id] = insumo
        if errores:
            salida.append(Recomposicion(metrica_id, None, errores[0], valores_por_muestra))
            continue
        agregacion = (_por_id(vocabulario.get("agregaciones") or [], "agregacion_id")
                      .get(metrica_pre.get("agregacion")) or {})
        resolvedor = RESOLVEDORES_DE_AGREGACION.get(agregacion.get("forma"))
        if resolvedor is None:
            salida.append(Recomposicion(metrica_id, None,
                                        f"la agregación «{metrica_pre.get('agregacion')}» no tiene "
                                        "resolvedor", valores_por_muestra))
            continue
        valor, error = resolvedor([insumos[k] for k in sorted(insumos)])
        salida.append(Recomposicion(metrica_id, valor, error, valores_por_muestra))
    return salida


def _numeros_publicados(baseline: dict) -> dict[str, Any]:
    return {n.get("metrica_id"): n.get("valor") for n in baseline.get("numeros") or []}


def revisar_recomposicion(preregistro: dict, observaciones: list[dict], vocabulario: dict,
                          baseline: dict) -> list[str]:
    """Los números publicados contra los recompuestos, en las dos direcciones. Un número publicado
    que nadie recompone es tan grave como uno que difiere: los dos significan que la cadena que lo
    devuelve a un hecho está rota."""
    problemas: list[str] = []
    recompuestos = {r.metrica_id: r for r in recomponer_metricas(preregistro, observaciones,
                                                                vocabulario)}
    publicados = _numeros_publicados(baseline)

    for metrica_id in sorted(set(recompuestos) | set(publicados)):
        if metrica_id not in publicados:
            problemas.append(f"{metrica_id}: se recompone y el baseline no lo publica")
            continue
        if metrica_id not in recompuestos:
            problemas.append(f"{metrica_id}: el baseline lo publica y no sale de ninguna fuente "
                             "canónica")
            continue
        recompuesto = recompuestos[metrica_id]
        if recompuesto.error:
            problemas.append(f"{metrica_id}: no se pudo recomponer — {recompuesto.error}")
            continue
        if not _casi_igual(recompuesto.valor, publicados[metrica_id]):
            problemas.append(f"{metrica_id}: el baseline publica {publicados[metrica_id]} y la "
                             f"recomposición da {recompuesto.valor}")
    return problemas


def modo_recomponer(args: argparse.Namespace) -> int:
    raiz = _ruta_absoluta(getattr(args, "recomponer"))
    ruta_acta = getattr(args, "preregistro", None) or RUTA_PREREGISTRO_FASE_0
    preregistro, error = _cargar_json(_ruta_absoluta(ruta_acta))
    if error:
        print(f"FALLA  pre-registro: {error}")
        return 1
    vocabulario, esquemas, problemas = _cargar_insumos_de_recoleccion()
    dag, error = cargar_dag()
    if error:
        problemas.append(f"DAG de procedencia: {error}")
    if problemas:
        for p in problemas:
            print(f"FALLA  {p}")
        return 1

    # El modo acepta dos cosas y hace lo mismo con las dos: un DIRECTORIO de observaciones —desde
    # el que recompone y reporta— o el DOCUMENTO publicado, que además compara publicado contra
    # recompuesto con `revisar_baseline`. V40 lo invoca con el `.md`: recomponer solo desde las
    # observaciones deja sin comprobar el artefacto que el lector termina viendo, que es donde un
    # número escrito a mano sobreviviría.
    documento = raiz if raiz.is_file() and raiz.suffix == ".md" else None
    crudo_obs = getattr(args, "observaciones", None)
    dir_observaciones = (_ruta_absoluta(crudo_obs or RUTA_OBSERVACIONES_FASE_0) if documento
                         else raiz)

    observaciones: list[dict] = []
    for archivo in sorted(dir_observaciones.glob("*.json")) if dir_observaciones.is_dir() else []:
        datos, error = _cargar_json(archivo)
        if error:
            print(f"FALLA  {archivo.name}: {error}")
            return 1
        observaciones.append(datos)
    if not observaciones:
        print(f"FALLA  {dir_observaciones}: no hay observaciones desde las que recomponer")
        return 1

    problemas_del_dag = revisar_dag(dag)
    print(f"Observaciones: {dir_observaciones} ({len(observaciones)}) · acta: {ruta_acta}"
          + (f" · documento: {documento}" if documento else ""))
    if problemas_del_dag:
        print(f"FALLA  el DAG de procedencia — {len(problemas_del_dag)}:")
        for p in problemas_del_dag[:6]:
            print(f"       - {p}")
        return 1
    print(f"OK     el DAG de procedencia: {len(dag.get('nodos') or [])} nodos, "
          f"{len(dag.get('aristas') or [])} aristas, acíclico y con una fuente por clase")

    for recomposicion in recomponer_metricas(preregistro, observaciones, vocabulario):
        if recomposicion.error:
            print(f"SIN    {recomposicion.metrica_id}: {recomposicion.error}")
        else:
            print(f"OK     {recomposicion.metrica_id}: {recomposicion.valor:g} — desde "
                  f"{len(recomposicion.por_muestra)} muestras")

    if documento is not None:
        problemas = revisar_baseline(documento.read_text(encoding="utf-8"), preregistro,
                                     observaciones, vocabulario)
        print()
        if problemas:
            print(f"FALLA  el documento publicado contra lo recompuesto — {len(problemas)}:")
            for p in problemas[:8]:
                print(f"       - {p}")
            print()
            print(f"RESULTADO: FALLA — {len(problemas)} problemas")
            return 1
        print(f"OK     el documento publica exactamente lo recompuesto, en las dos direcciones")

    print()
    print(f"RESULTADO: OK — {len(observaciones)} observaciones recompuestas desde su fuente "
          "canónica" + (" y comparadas contra el documento publicado" if documento else ""))
    return 0


def _corpus_de_recomposicion() -> tuple[dict, dict, list[dict], dict, dict, list[str]]:
    """El corpus completo: manifest, pre-registro, observaciones, bundles y baseline esperado."""
    problemas: list[str] = []
    manifest, error = _cargar_json(RUTA_MANIFEST_RECOMPOSICION)
    if error:
        problemas.append(f"manifest del corpus de recomposición: {error}")
    preregistro, error = _cargar_json(DIR_FIXTURES_RECOMPOSICION / "preregistro.json")
    if error:
        problemas.append(f"pre-registro del corpus: {error}")
    baseline, error = _cargar_json(DIR_FIXTURES_RECOMPOSICION / "baseline-esperado.json")
    if error:
        problemas.append(f"baseline esperado del corpus: {error}")

    observaciones: list[dict] = []
    bundles: dict[str, dict] = {}
    raiz = DIR_FIXTURES_RECOMPOSICION / "observaciones"
    for archivo in sorted(raiz.glob("*.json")) if raiz.is_dir() else []:
        datos, error = _cargar_json(archivo)
        if error:
            problemas.append(f"{archivo.name}: {error}")
            continue
        observaciones.append(datos)
        # El bundle de cada observación no se lee del disco: el corpus de recomposición prueba la
        # cadena desde la observación en adelante, y el tramo bundle → observación ya lo prueban
        # `--autotest-derivacion` y `--autotest-bundles`. Acá alcanza con su identidad.
        bundles[(datos.get("procedencia") or {}).get("run_id")] = {}
    return manifest or {}, preregistro or {}, observaciones, bundles, baseline or {}, problemas


def esperado_de_las_aristas(preregistro: dict,
                            manifest: dict) -> tuple[dict[str, set[str]],
                                                     dict[str, dict[str, set[str]]]]:
    """Orígenes y destinos esperados de cada arista. Los orígenes de la primera salen del
    pre-registro —la cohorte congelada— y todo lo demás, del manifest INDEPENDIENTE de intentos: es
    lo único que sabe cuántos intentos tuvo cada muestra, y sin eso perder uno no se ve."""
    muestras = {m.get("sample_id") for m in
                ((preregistro.get("cohorte") or {}).get("muestras") or [])}
    intentos = manifest.get("intentos_esperados") or []
    por_muestra: dict[str, set[str]] = {}
    por_intento: dict[str, set[str]] = {}
    por_bundle: dict[str, set[str]] = {}
    for entrada in intentos:
        por_muestra.setdefault(entrada["sample_id"], set()).add(entrada["attempt_id"])
        por_intento.setdefault(entrada["attempt_id"], set()).add(entrada["run_id"])
        por_bundle.setdefault(entrada["run_id"], set()).add(entrada["observation_id"])

    origenes = {
        "manifest-a-muestras": {"manifest"},
        "muestra-a-intentos": set(por_muestra) or muestras,
        "intento-a-bundle": set(por_intento),
        "bundle-a-observacion": set(por_bundle),
        "muestras-a-agregado": {"agregado"},
    }
    destinos = {
        "manifest-a-muestras": {"manifest": muestras},
        "muestra-a-intentos": por_muestra,
        "intento-a-bundle": por_intento,
        "bundle-a-observacion": por_bundle,
        "muestras-a-agregado": {"agregado": set(por_muestra) or muestras},
    }
    return origenes, destinos


class AtaqueALaRecomposicion(NamedTuple):
    nombre: str
    que_rompe: str
    aplicar: Callable[[list[dict], dict], None]


def _falta_una_observacion(observaciones: list[dict], baseline: dict) -> None:
    del baseline
    observaciones.pop()


def _sobra_una_observacion(observaciones: list[dict], baseline: dict) -> None:
    del baseline
    extra = copy.deepcopy(observaciones[0])
    extra["observation_id"] = "obs-sobrante"
    extra["sample_id"] = "mst-sobrante-r1"
    extra["attempt_id"] = "int-sobrante-r1-a1"
    (extra.setdefault("procedencia", {}))["run_id"] = "run-sobrante"
    observaciones.append(extra)


def _duplica_una_observacion(observaciones: list[dict], baseline: dict) -> None:
    del baseline
    observaciones.append(copy.deepcopy(observaciones[0]))


def _altera_un_numero(observaciones: list[dict], baseline: dict) -> None:
    del observaciones
    for numero in baseline.get("numeros") or []:
        if isinstance(numero.get("valor"), (int, float)):
            numero["valor"] = numero["valor"] + 1
            return


ATAQUES_A_LA_RECOMPOSICION: tuple[AtaqueALaRecomposicion, ...] = (
    AtaqueALaRecomposicion("faltante", "se cae una observación del conjunto",
                           _falta_una_observacion),
    AtaqueALaRecomposicion("sobrante", "aparece una observación que nadie pre-registró",
                           _sobra_una_observacion),
    AtaqueALaRecomposicion("duplicado", "una observación aparece dos veces",
                           _duplica_una_observacion),
    AtaqueALaRecomposicion("numero-alterado", "un número publicado cambia en una unidad",
                           _altera_un_numero),
)


def modo_autotest_recomposicion(args: argparse.Namespace) -> int:
    del args
    manifest, preregistro, observaciones, bundles, baseline, problemas = _corpus_de_recomposicion()
    vocabulario, esquemas, mas = _cargar_insumos_de_recoleccion()
    dag, error = cargar_dag()
    if error:
        mas.append(f"DAG de procedencia: {error}")
    if problemas + mas:
        for p in problemas + mas:
            print(f"[A] FALLA  {p}")
        return 1

    resultados: list[tuple[str, bool, str]] = []

    # [A] Manifest ↔ disco, en las dos direcciones (D-16).
    declaradas = set(manifest.get("observaciones") or [])
    en_disco = {o.get("observation_id") for o in observaciones}
    diferencias = [f"declarada y ausente del disco: {o}" for o in sorted(declaradas - en_disco)]
    diferencias += [f"en disco y no declarada: {o}" for o in sorted(en_disco - declaradas)]
    resultados.append(("A", not diferencias,
                       f"manifest ↔ directorio ({len(declaradas)} observaciones)"
                       if not diferencias else " | ".join(diferencias[:6])))

    # [B] El control positivo: el conjunto íntegro recompone EXACTAMENTE los números publicados.
    # Sin él, un recompositor que fallara siempre pasaría los cuatro ataques.
    problemas_positivos = revisar_recomposicion(preregistro, observaciones, vocabulario, baseline)
    resultados.append(("B", not problemas_positivos,
                       f"el conjunto íntegro recompone los {len(baseline.get('numeros') or [])} "
                       "números publicados" if not problemas_positivos
                       else " | ".join(problemas_positivos[:4])))

    # [C] Los cuatro ataques: faltante, sobrante, duplicado y número alterado en una unidad. Cada
    # uno tiene que romper la recomposición o las cardinalidades — «recomponer sobre lo que llegó»
    # siempre cierra, y es exactamente lo que hay que impedir.
    esperado, destinos = esperado_de_las_aristas(preregistro, manifest)
    fallas: list[str] = []
    for ataque in ATAQUES_A_LA_RECOMPOSICION:
        copia_obs = copy.deepcopy(observaciones)
        copia_base = copy.deepcopy(baseline)
        ataque.aplicar(copia_obs, copia_base)
        copia_bundles = {(o.get("procedencia") or {}).get("run_id"): {} for o in copia_obs}
        detectado = bool(revisar_recomposicion(preregistro, copia_obs, vocabulario, copia_base))
        detectado = detectado or bool(revisar_cardinalidades(
            dag, cardinalidades_observadas(preregistro, {}, copia_obs, copia_bundles), esperado,
            destinos))
        if not detectado:
            fallas.append(f"«{ataque.nombre}»: {ataque.que_rompe} y la recomposición cierra igual")
    resultados.append(("C", not fallas,
                       f"los {len(ATAQUES_A_LA_RECOMPOSICION)} ataques rompen la recomposición"
                       if not fallas else " | ".join(fallas[:4])))

    # [D] Y las cardinalidades del conjunto íntegro NO se rompen: es la otra dirección del control
    # anterior. Uno que rechazara todo pasaría [C] entero.
    limpias = revisar_cardinalidades(
        dag, cardinalidades_observadas(preregistro, {}, observaciones, bundles), esperado,
        destinos)
    resultados.append(("D", not limpias,
                       "las cardinalidades del conjunto íntegro cierran" if not limpias
                       else " | ".join(limpias[:4])))

    # [E] La rama del DOCUMENTO publicado (V40), de punta a punta por el modo entero.
    #
    # `revisar_baseline` ya tiene sus propios ataques; lo que este control ejerce es el CABLEADO:
    # que pasarle un `.md` al modo lo haga comparar publicado contra recompuesto en vez de solo
    # recomponer. Sin él, la rama sería código que ninguna corrida recorre — y su verde vendría de
    # que nadie la ejecuta, no de que funcione.
    fallas = []
    with tempfile.TemporaryDirectory(prefix="recomponer-md-") as tmp:
        raiz = Path(tmp)
        dir_obs = raiz / "observaciones"
        dir_obs.mkdir()
        for observacion in observaciones:
            _escribir_json(dir_obs / f"{observacion['observation_id']}.json", observacion)
        ruta_acta = raiz / "preregistro.json"
        _escribir_json(ruta_acta, preregistro)

        publicado = raiz / "baseline.md"
        publicado.write_text(_baseline_publicable(preregistro, observaciones, vocabulario),
                             encoding="utf-8")
        if _codigo_de_modo(modo_recomponer, recomponer=str(publicado),
                           preregistro=str(ruta_acta), observaciones=str(dir_obs)) != 0:
            fallas.append("el modo devolvió distinto de 0 sobre un documento que publica "
                          "exactamente lo recompuesto")

        # El ataque: un número publicado que no es el recompuesto. Es el defecto que la fila V40
        # existe para cazar —un valor escrito a mano en el artefacto final—, y el que la versión
        # anterior del modo no podía ver, porque nunca leía el documento.
        texto = publicado.read_text(encoding="utf-8")
        alterado = raiz / "alterado.md"
        alterado.write_text(re.sub(r"`(\d+(?:\.\d+)?)`", "`999.0`", texto, count=1),
                            encoding="utf-8")
        if alterado.read_text(encoding="utf-8") == texto:
            fallas.append("el ataque no alteró ningún número: el documento sintético no tiene "
                          "valores publicados y el control no prueba nada")
        elif _codigo_de_modo(modo_recomponer, recomponer=str(alterado),
                             preregistro=str(ruta_acta), observaciones=str(dir_obs)) == 0:
            fallas.append("el modo devolvió 0 sobre un documento con un número que no es el "
                          "recompuesto")
    resultados.append(("E", not fallas,
                       "el modo acepta el documento publicado y lo compara contra lo recompuesto: "
                       "pasa con el fiel y falla con un número alterado"
                       if not fallas else " | ".join(fallas)))

    return _cerrar(resultados)


def _baseline_publicable(preregistro: dict, observaciones: list[dict],
                         vocabulario: dict) -> str:
    """La tabla normativa de `## Números publicados`, con lo que el corpus recompone.

    Se arma desde `recomponer_metricas` y no a mano: un documento sintético escrito aparte podría
    diferir de lo recompuesto por su propia construcción, y entonces el positivo del control fallaría
    por el fixture en vez de por el modo.
    """
    recompuestas = {r.metrica_id: r for r in recomponer_metricas(preregistro, observaciones,
                                                                vocabulario)}
    filas = []
    for metrica in preregistro.get("metricas") or []:
        ident = metrica["metrica_id"]
        recompuesta = recompuestas.get(ident)
        valor = (f"`{recompuesta.valor!r}`"
                 if recompuesta is not None and recompuesta.error is None
                 else "sin observaciones")
        filas.append(f"| {ident} | {valor} | {metrica['unidad']} | {metrica['agregacion']} | "
                     f"{len(recompuesta.por_muestra) if recompuesta and not recompuesta.error else 0}"
                     f" | pre-registrada |")
    cuerpo = "\n".join(filas)
    return ("# Baseline\n\n## Números publicados\n\n"
            "| métrica | valor | unidad | agregación | muestras | adjudicación |\n"
            "|---|---|---|---|---|---|\n" + cuerpo + "\n")


class AtaqueAlDag(NamedTuple):
    nombre: str
    que_rompe: str
    motivo_esperado: str
    aplicar: Callable[[dict], bool]


def _dag_ciclo_directo(dag: dict) -> bool:
    for nodo in dag.get("nodos") or []:
        if not nodo.get("es_raiz"):
            nodo.setdefault("depende_de", []).append(nodo["nodo_id"])
            return True
    return False


def _dag_ciclo_indirecto(dag: dict) -> bool:
    # El que sobrevive a una revisión por inspección: ningún nodo se nombra a sí mismo.
    nodos = {n.get("nodo_id"): n for n in dag.get("nodos") or []}
    if "preregistro" not in nodos or "observacion" not in nodos:
        return False
    nodos["preregistro"].pop("es_raiz", None)
    nodos["preregistro"]["depende_de"] = ["agregado_final"]
    nodos["preregistro"]["formula"] = "mutante"
    return True


def _dag_dependencia_omitida(dag: dict) -> bool:
    for nodo in dag.get("nodos") or []:
        if nodo.get("nodo_id") == "observacion":
            nodo["depende_de"] = []
            return True
    return False


def _dag_dependencia_extra(dag: dict) -> bool:
    for nodo in dag.get("nodos") or []:
        if nodo.get("nodo_id") == "muestra":
            nodo.setdefault("depende_de", []).append("nodo-que-no-existe")
            return True
    return False


def _dag_doble_fuente_canonica(dag: dict) -> bool:
    clases = dag.get("clases_de_dato") or []
    if not clases:
        return False
    clases.append({**clases[0], "fuente_canonica": "preregistro"})
    return True


ATAQUES_AL_DAG: tuple[AtaqueAlDag, ...] = (
    AtaqueAlDag("ciclo-directo", "un nodo depende de sí mismo", "ciclo en la procedencia",
                _dag_ciclo_directo),
    AtaqueAlDag("ciclo-indirecto", "el ciclo pasa por otros nodos y ninguno se nombra a sí mismo",
                "ciclo en la procedencia", _dag_ciclo_indirecto),
    AtaqueAlDag("dependencia-omitida", "un nodo derivado deja de declarar de qué depende",
                "no depende de nada", _dag_dependencia_omitida),
    AtaqueAlDag("dependencia-extra", "un nodo depende de algo que no existe en el grafo",
                "que no existe", _dag_dependencia_extra),
    AtaqueAlDag("doble-fuente-canonica", "una clase de dato declara dos fuentes",
                "fuentes canónicas", _dag_doble_fuente_canonica),
)


def modo_autotest_procedencia_dag(args: argparse.Namespace) -> int:
    del args
    dag, error = cargar_dag()
    if error:
        print(f"[A] FALLA  DAG de procedencia: {error}")
        return 1
    manifest, preregistro, observaciones, bundles, baseline, problemas = _corpus_de_recomposicion()
    if problemas:
        for p in problemas:
            print(f"[A] FALLA  {p}")
        return 1

    resultados: list[tuple[str, bool, str]] = []

    # [A] El grafo real está sano: acíclico, con una fuente por clase y sin punteros rotos.
    limpio = revisar_dag(copy.deepcopy(dag))
    resultados.append(("A", not limpio,
                       f"el grafo declarado: {len(dag.get('nodos') or [])} nodos y "
                       f"{len(dag.get('aristas') or [])} aristas, sano" if not limpio
                       else " | ".join(limpio[:4])))

    # [B] Los cinco ataques al grafo, cada uno detectado POR SU MOTIVO. Uno que fallara por otra
    # razón dejaría su cláusula sin probar.
    fallas: list[str] = []
    for ataque in ATAQUES_AL_DAG:
        copia = copy.deepcopy(dag)
        if not ataque.aplicar(copia):
            fallas.append(f"«{ataque.nombre}»: la mutación no se pudo aplicar")
            continue
        detectados = revisar_dag(copia)
        if not any(ataque.motivo_esperado in d for d in detectados):
            fallas.append(f"«{ataque.nombre}»: {ataque.que_rompe} y no se detecta por "
                          f"«{ataque.motivo_esperado}» — se vio: "
                          f"{detectados[0] if detectados else 'nada'}")
    resultados.append(("B", not fallas,
                       f"los {len(ATAQUES_AL_DAG)} ataques al grafo se detectan por su motivo"
                       if not fallas else " | ".join(fallas[:4])))

    # [C] Cada arista, con faltante, sobrante y duplicado. Es lo que hace que la cardinalidad
    # signifique algo: declararla y no ejercerla la deja de adorno.
    esperado_base, destinos_base = esperado_de_las_aristas(preregistro, manifest)
    observado_base = cardinalidades_observadas(preregistro, {}, observaciones, bundles)
    fallas_de_arista: list[str] = []
    if revisar_cardinalidades(dag, observado_base, esperado_base, destinos_base):
        fallas_de_arista.append("el conjunto íntegro ya rompe alguna cardinalidad")
    for arista in dag.get("aristas") or []:
        arista_id = arista.get("arista_id")
        medida = observado_base.get(arista_id)
        if medida is None or not medida.por_origen:
            fallas_de_arista.append(f"{arista_id}: el corpus no la ejerce")
            continue
        primero = sorted(medida.por_origen)[0]
        for nombre, mutar in (
            ("faltante", lambda p: {k: v for k, v in p.items() if k != primero}),
            ("sobrante", lambda p: {**p, "origen-inventado": list(next(iter(p.values())))}),
            ("duplicado", lambda p: {**p, primero: p[primero] + [p[primero][0]]}),
            # El cuarto ataque cambia UN destino por otro nombre sin tocar el conteo: la
            # cardinalidad sigue cerrando y los orígenes también. Solo el conjunto de destinos
            # declarado lo caza, que es lo que prueba que esa comparación no es redundante.
            ("destino-cambiado",
             lambda p: {**p, primero: ["destino-inventado"] + p[primero][1:]}),
        ):
            mutado = dict(observado_base)
            mutado[arista_id] = Cardinalidad(arista_id, mutar(medida.por_origen))
            if not revisar_cardinalidades(dag, mutado, esperado_base, destinos_base):
                fallas_de_arista.append(f"{arista_id}/{nombre}: no se detecta")
    resultados.append(("C", not fallas_de_arista,
                       f"las {len(dag.get('aristas') or [])} aristas, cada una con faltante, "
                       "sobrante, duplicado y destino cambiado" if not fallas_de_arista
                       else " | ".join(fallas_de_arista[:4])))

    return _cerrar(resultados)


# ---------------------------------------------------------------------------------------------
# Modos `--generar-baseline` y `--autotest-generacion`.
#
# El baseline se GENERA. Un documento escrito a mano con los números copiados de una corrida no se
# distingue de uno correcto mirándolo: los dos tienen tablas plausibles. La diferencia es que del
# generado se puede volver, número por número, a la observación que lo produjo, y que reproducirlo
# con el mismo insumo da los MISMOS BYTES — así que una edición manual posterior se ve como un diff.
#
# Dos cláusulas de AC-21 gobiernan la forma de la salida y no son negociables:
#
# - **Una métrica sin observaciones se declara, nunca se publica en cero.** El cero es un número
#   medido: usarlo para «no lo medimos» destruye la distinción exacta que la fase tiene que reportar.
#   Acá esa métrica sale con su celda de valor no numérica y con su adjudicación escrita.
# - **La adjudicación es la del agregado Y la de cada observación.** Solo la primera diría «sin
#   valores que agregar» para dos causas distintas —la cohorte no la cubre, o la corrida impidió
#   medirla—, y el lector no podría saber cuál.
#
# La lectura inversa (`numeros_publicados_del_markdown`) es lo que hace comprobable «coincide
# exactamente con lo publicado» sobre el artefacto real, donde no hay golden contra el cual comparar:
# sin ella, el único control posible es volver a generar, que compara el generador consigo mismo.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_GENERACION = DIR_SCRIPTS / "fixtures-baseline" / "generacion"
RUTA_MANIFEST_GENERACION = DIR_FIXTURES_GENERACION / "manifest.json"
RUTA_BASELINE_FASE_0 = "scripts/baseline-fase-0.md"

# La celda de valor de una métrica que no se midió. No es un número y no se puede confundir con uno:
# el parser la devuelve como ausencia, no como cero.
SIN_OBSERVACIONES = "sin observaciones"
SIN_ADJUDICACION = "—"


def _formato_numero(valor: float) -> str:
    """El número publicado, en una forma que vuelve a leerse EXACTA.

    `repr` de un float en Python round-trips por construcción. Un formato «lindo» —dos decimales,
    separador de miles— publicaría un número distinto del recompuesto y la comparación de AC-22bis
    fallaría por presentación, o peor: pasaría por tolerancia y taparía una diferencia real."""
    return repr(float(valor))


def _celda(texto: str) -> str:
    """Un texto libre dentro de una celda de tabla. La barra se escapa y los saltos se colapsan: sin
    eso, una adjudicación con `|` parte la fila en columnas que nadie declaró."""
    return " ".join(str(texto).split()).replace("|", "\\|")


def _descelda(texto: str) -> str:
    return texto.strip().replace("\\|", "|")


def _fila(*celdas: str) -> str:
    return "| " + " | ".join(celdas) + " |"


def _metricas_sin_valor_por_observacion(observaciones: list[dict],
                                        metrica_id: str) -> list[tuple[str, str, str]]:
    """Qué dijo cada observación sobre una métrica que no tiene valor: su estado y su adjudicación,
    tal como las escribió el recolector. Ordenado por identidad de la observación."""
    detalle: list[tuple[str, str, str]] = []
    for observacion in sorted(observaciones, key=lambda o: o.get("observation_id") or ""):
        medida = _metrica_de_la_observacion(observacion, metrica_id)
        if medida is None or medida.get("estado_de_medicion") == "medida":
            continue
        detalle.append((observacion.get("observation_id") or "",
                        medida.get("estado_de_medicion") or "",
                        medida.get("adjudicacion") or ""))
    return detalle


def generar_baseline(preregistro: dict, observaciones: list[dict],
                     vocabulario: dict) -> tuple[str | None, list[str]]:
    """El baseline completo, derivado. Ningún número entra por parámetro ni se lee del documento
    anterior: todos salen de `recomponer_metricas`, que a su vez sale de las observaciones."""
    problemas: list[str] = []
    acta = preregistro.get("preregistro_sha256")
    for observacion in observaciones:
        citada = observacion.get("preregistro_sha256")
        if citada != acta:
            problemas.append(
                f"{observacion.get('observation_id')} cita el acta {citada!r} y el pre-registro es "
                f"{acta!r}: un baseline que mezcla dos cohortes no tiene una cohorte")
    if problemas:
        return None, problemas

    recompuestas = {r.metrica_id: r for r in recomponer_metricas(preregistro, observaciones,
                                                                 vocabulario)}
    muestras = (preregistro.get("cohorte") or {}).get("muestras") or []

    lineas = [
        "# Baseline de la fase 0",
        "",
        "Documento **generado**: cada número se deriva de las observaciones y ninguno se escribe a "
        "mano. Se",
        "reproduce con `python3 scripts/instrumento-baseline.py --generar-baseline "
        "<dir-de-observaciones>`.",
        "",
        "## Procedencia",
        "",
        _fila("insumo", "identidad"),
        _fila("---", "---"),
        _fila("acta congelada (`preregistro_sha256`)", f"`{acta}`"),
        _fila("commit del código medido", f"`{preregistro.get('code_commit')}`"),
        _fila("muestras de la cohorte", str(len(muestras))),
        _fila("observaciones recolectadas", str(len(observaciones))),
        "",
        "## Números publicados",
        "",
        _fila("métrica", "valor", "unidad", "agregación", "muestras", "adjudicación"),
        _fila("---", "---", "---", "---", "---", "---"),
    ]

    sin_valor: list[str] = []
    for metrica_pre in preregistro.get("metricas") or []:
        metrica_id = metrica_pre.get("metrica_id")
        recompuesta = recompuestas.get(metrica_id)
        if recompuesta is None or recompuesta.error is not None:
            sin_valor.append(metrica_id)
            adjudicacion = (recompuesta.error if recompuesta is not None
                            else "la métrica está pre-registrada y no se recompone desde ninguna "
                                 "fuente canónica")
            lineas.append(_fila(f"`{metrica_id}`", SIN_OBSERVACIONES,
                                _celda(metrica_pre.get("unidad")),
                                _celda(metrica_pre.get("agregacion")),
                                str(len(recompuesta.por_muestra) if recompuesta else 0),
                                _celda(adjudicacion)))
            continue
        lineas.append(_fila(f"`{metrica_id}`", f"`{_formato_numero(recompuesta.valor)}`",
                            _celda(metrica_pre.get("unidad")),
                            _celda(metrica_pre.get("agregacion")),
                            str(len(recompuesta.por_muestra)), SIN_ADJUDICACION))

    lineas += ["", "## Valor por muestra", "",
               _fila("métrica", "muestra", "valor"), _fila("---", "---", "---")]
    for metrica_pre in preregistro.get("metricas") or []:
        recompuesta = recompuestas.get(metrica_pre.get("metrica_id"))
        if recompuesta is None or recompuesta.error is not None:
            continue
        for sample_id in sorted(recompuesta.por_muestra):
            lineas.append(_fila(f"`{recompuesta.metrica_id}`", f"`{sample_id}`",
                                f"`{_formato_numero(recompuesta.por_muestra[sample_id])}`"))

    lineas += ["", "## Métricas sin observaciones", ""]
    if not sin_valor:
        lineas.append(f"Ninguna: las {len(preregistro.get('metricas') or [])} métricas "
                      "pre-registradas se publican con su valor.")
    else:
        lineas += ["Ninguna se publica como cero. Cada una declara por qué el agregado no tiene "
                   "valor y qué dijo",
                   "cada observación, que es lo único que separa «la cohorte no la cubre» de «la "
                   "corrida impidió",
                   "medirla»."]
        for metrica_id in sin_valor:
            recompuesta = recompuestas.get(metrica_id)
            lineas += ["", f"### `{metrica_id}`", "",
                       "Adjudicación del agregado: "
                       f"{_celda(recompuesta.error if recompuesta else 'sin recomposición')}", "",
                       _fila("observación", "estado de la medición", "adjudicación"),
                       _fila("---", "---", "---")]
            detalle = _metricas_sin_valor_por_observacion(observaciones, metrica_id)
            if not detalle:
                lineas.append(_fila("—", "—", "ninguna observación declara esta métrica"))
            for observation_id, estado, adjudicacion in detalle:
                lineas.append(_fila(f"`{observation_id}`", _celda(estado), _celda(adjudicacion)))

    return "\n".join(lineas) + "\n", []


class NumeroPublicado(NamedTuple):
    metrica_id: str
    valor: float | None
    unidad: str
    adjudicacion: str


def numeros_publicados_del_markdown(texto: str) -> tuple[dict[str, NumeroPublicado], list[str]]:
    """Lo que el documento publica, leído de vuelta desde su tabla normativa.

    Se lee la TABLA, no la prosa: la sección tiene un encabezado fijo y un orden de columnas fijo, y
    una fila que no encaje se reporta en vez de saltearse. Un lector tolerante convertiría un
    documento corrompido en uno con menos números, que es la forma de corrupción que nadie ve."""
    problemas: list[str] = []
    publicados: dict[str, NumeroPublicado] = {}
    lineas = texto.splitlines()
    try:
        inicio = lineas.index("## Números publicados")
    except ValueError:
        return {}, ["el documento no tiene la sección «## Números publicados»"]

    for linea in lineas[inicio + 1:]:
        if linea.startswith("## "):
            break
        if not linea.startswith("|"):
            continue
        celdas = [_descelda(c) for c in re.split(r"(?<!\\)\|", linea)[1:-1]]
        if celdas[:1] == ["métrica"] or set(celdas) == {"---"}:
            continue
        if len(celdas) != 6:
            problemas.append(f"fila con {len(celdas)} columnas y no 6: {linea}")
            continue
        metrica_id = celdas[0].strip("`")
        bruto = celdas[1]
        if bruto == SIN_OBSERVACIONES:
            valor = None
        else:
            try:
                valor = float(bruto.strip("`"))
            except ValueError:
                problemas.append(f"«{metrica_id}»: la celda de valor no es un número ni "
                                 f"«{SIN_OBSERVACIONES}»: {bruto!r}")
                continue
        if metrica_id in publicados:
            problemas.append(f"«{metrica_id}» aparece dos veces en la tabla de números")
            continue
        publicados[metrica_id] = NumeroPublicado(metrica_id, valor, celdas[2], celdas[5])
    return publicados, problemas


def revisar_baseline(texto: str, preregistro: dict, observaciones: list[dict],
                     vocabulario: dict) -> list[str]:
    """El documento contra sus fuentes. Es el predicado que los ataques tienen que poner rojo, y por
    eso trabaja sobre el TEXTO publicado y no sobre la estructura intermedia: un ataque a la
    estructura no prueba nada sobre lo que el lector del baseline termina viendo."""
    publicados, problemas = numeros_publicados_del_markdown(texto)
    recompuestas = {r.metrica_id: r for r in recomponer_metricas(preregistro, observaciones,
                                                                 vocabulario)}
    pre_registradas = [m.get("metrica_id") for m in preregistro.get("metricas") or []]

    for metrica_id in sorted(set(publicados) - set(pre_registradas)):
        problemas.append(f"«{metrica_id}»: el documento lo publica y el acta no lo pre-registra")

    for metrica_id in pre_registradas:
        publicado = publicados.get(metrica_id)
        recompuesta = recompuestas.get(metrica_id)
        if publicado is None:
            problemas.append(f"«{metrica_id}»: está pre-registrado y el documento no lo publica")
            continue
        if recompuesta is None or recompuesta.error is not None:
            if publicado.valor is not None:
                problemas.append(
                    f"«{metrica_id}»: no se recompone desde ninguna observación y el documento "
                    f"publica {publicado.valor!r} — una métrica sin observaciones nunca es un número")
            elif not publicado.adjudicacion or publicado.adjudicacion == SIN_ADJUDICACION:
                problemas.append(f"«{metrica_id}»: se declara sin observaciones y sin adjudicación: "
                                 "quedaría sin razón escrita de por qué no tiene valor")
            continue
        if publicado.valor is None:
            problemas.append(f"«{metrica_id}»: se recompone en {recompuesta.valor!r} y el documento "
                             "lo declara sin observaciones")
            continue
        if not _casi_igual(publicado.valor, recompuesta.valor):
            problemas.append(f"«{metrica_id}»: el documento publica {publicado.valor!r} y la "
                             f"recomposición da {recompuesta.valor!r}")
    return problemas


def _observaciones_de(raiz: Path) -> tuple[list[dict], list[str]]:
    """Las observaciones de un directorio, en orden de identidad y no de disco."""
    problemas: list[str] = []
    observaciones: list[dict] = []
    for archivo in sorted(raiz.glob("*.json")) if raiz.is_dir() else []:
        datos, error = _cargar_json(archivo)
        if error:
            problemas.append(f"{archivo.name}: {error}")
            continue
        observaciones.append(datos)
    if not observaciones and not problemas:
        problemas.append(f"{raiz}: no hay observaciones desde las que generar")
    return observaciones, problemas


def modo_generar_baseline(args: argparse.Namespace) -> int:
    raiz = _ruta_absoluta(getattr(args, "generar_baseline"))
    ruta_acta = getattr(args, "preregistro", None) or RUTA_PREREGISTRO_FASE_0
    salida = _ruta_absoluta(getattr(args, "salida", None) or RUTA_BASELINE_FASE_0)

    preregistro, error = _cargar_json(_ruta_absoluta(ruta_acta))
    if error:
        print(f"FALLA  pre-registro: {error}")
        return 1
    vocabulario, _, problemas = _cargar_insumos_de_recoleccion()
    observaciones, mas = _observaciones_de(raiz)
    if problemas + mas:
        for p in problemas + mas:
            print(f"FALLA  {p}")
        return 1

    texto, problemas = generar_baseline(preregistro, observaciones, vocabulario)
    if texto is None:
        for p in problemas:
            print(f"FALLA  {p}")
        return 1

    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(texto, encoding="utf-8")
    publicados, _ = numeros_publicados_del_markdown(texto)
    con_valor = [n for n in publicados.values() if n.valor is not None]
    print(f"Observaciones: {raiz} ({len(observaciones)}) · acta: {ruta_acta}")
    print(f"OK     {salida}: {len(con_valor)} números derivados y "
          f"{len(publicados) - len(con_valor)} métricas declaradas sin observaciones")
    print()
    print(f"RESULTADO: OK — baseline generado desde {len(observaciones)} observaciones")
    return 0


def _corpus_de_generacion() -> tuple[dict, dict, list[dict], str, list[str]]:
    """Manifest, acta, observaciones y golden del corpus de generación."""
    problemas: list[str] = []
    manifest, error = _cargar_json(RUTA_MANIFEST_GENERACION)
    if error:
        problemas.append(f"manifest del corpus de generación: {error}")
    preregistro, error = _cargar_json(DIR_FIXTURES_GENERACION / "preregistro.json")
    if error:
        problemas.append(f"acta del corpus de generación: {error}")
    golden = ""
    ruta_golden = DIR_FIXTURES_GENERACION / "baseline-esperado.md"
    try:
        golden = ruta_golden.read_text(encoding="utf-8")
    except FileNotFoundError:
        problemas.append(f"golden del corpus de generación: no existe: {ruta_golden}")
    observaciones, mas = _observaciones_de(DIR_FIXTURES_GENERACION / "observaciones")
    return manifest or {}, preregistro or {}, observaciones, golden, problemas + mas


class AtaqueAlBaseline(NamedTuple):
    """Un ataque al DOCUMENTO ya generado: lo que un editor a mano podría hacerle.

    Cada uno declara por qué motivo tiene que caer. Sin eso, un ataque detectado por otra cláusula
    —la tabla que ya no parsea, una fila de más— deja sin ejercer la que decía estar probando."""
    nombre: str
    que_rompe: str
    motivo_esperado: str
    aplicar: Callable[[str, dict], str | None]


def _ataque_numero_alterado(texto: str, manifest: dict) -> str | None:
    del manifest
    for linea in texto.splitlines():
        coincidencia = re.match(r"^\| `[^`]+` \| `(-?\d+\.\d+)` \|", linea)
        if coincidencia:
            crudo = coincidencia.group(1)
            alterado = _formato_numero(float(crudo) + 1)
            return texto.replace(f"| `{crudo}` |", f"| `{alterado}` |", 1)
    return None


def _linea_sin_observaciones(texto: str, manifest: dict) -> str | None:
    ids = [m.get("metrica_id") for m in manifest.get("metricas_sin_observaciones") or []]
    for linea in texto.splitlines():
        if linea.startswith("| `") and f"| {SIN_OBSERVACIONES} |" in linea:
            if linea.split("`")[1] in ids:
                return linea
    return None


def _ataque_sin_observaciones_omitida(texto: str, manifest: dict) -> str | None:
    linea = _linea_sin_observaciones(texto, manifest)
    return texto.replace(linea + "\n", "", 1) if linea else None


def _ataque_sin_observaciones_en_cero(texto: str, manifest: dict) -> str | None:
    linea = _linea_sin_observaciones(texto, manifest)
    if linea is None:
        return None
    return texto.replace(linea, linea.replace(f"| {SIN_OBSERVACIONES} |", "| `0.0` |", 1), 1)


def _ataque_adjudicacion_borrada(texto: str, manifest: dict) -> str | None:
    linea = _linea_sin_observaciones(texto, manifest)
    if linea is None:
        return None
    celdas = linea.split(" | ")
    celdas[-1] = " |"
    return texto.replace(linea, " | ".join(celdas[:-1]) + " |  |", 1)


def _ataque_metrica_inventada(texto: str, manifest: dict) -> str | None:
    del manifest
    marca = "\n\n## Valor por muestra"
    if marca not in texto:
        return None
    fila = _fila("`metrica-que-nadie-pre-registro`", "`0.0`", "conteo", "suma", "3",
                 SIN_ADJUDICACION)
    return texto.replace(marca, "\n" + fila + marca, 1)


ATAQUES_AL_BASELINE: tuple[AtaqueAlBaseline, ...] = (
    AtaqueAlBaseline("numero-alterado", "un número publicado cambia en una unidad",
                     "y la recomposición da", _ataque_numero_alterado),
    AtaqueAlBaseline("sin-observaciones-omitida",
                     "la métrica sin observaciones desaparece de la tabla",
                     "el documento no lo publica", _ataque_sin_observaciones_omitida),
    AtaqueAlBaseline("sin-observaciones-en-cero",
                     "la métrica sin observaciones se publica como cero",
                     "nunca es un número", _ataque_sin_observaciones_en_cero),
    AtaqueAlBaseline("adjudicacion-borrada",
                     "la métrica sin observaciones queda sin razón escrita",
                     "sin adjudicación", _ataque_adjudicacion_borrada),
    AtaqueAlBaseline("metrica-inventada", "aparece una métrica que el acta no pre-registra",
                     "el acta no lo pre-registra", _ataque_metrica_inventada),
)


class AtaqueAlInsumo(NamedTuple):
    """Un ataque a las OBSERVACIONES: prueba que el número sale de ellas y no está escrito."""
    nombre: str
    que_rompe: str
    aplicar: Callable[[list[dict]], bool]


def _insumo_valor_alterado(observaciones: list[dict]) -> bool:
    for observacion in sorted(observaciones, key=lambda o: o.get("observation_id") or ""):
        for metrica in observacion.get("metricas") or []:
            if metrica.get("estado_de_medicion") == "medida":
                metrica["valor"] = metrica["valor"] + 1
                return True
    return False


def _insumo_de_otra_acta(observaciones: list[dict]) -> bool:
    if not observaciones:
        return False
    observaciones[0]["preregistro_sha256"] = "9" * 64
    return True


ATAQUES_AL_INSUMO: tuple[AtaqueAlInsumo, ...] = (
    AtaqueAlInsumo("valor-alterado", "una observación cambia y el documento generado no",
                   _insumo_valor_alterado),
    AtaqueAlInsumo("observacion-de-otra-acta",
                   "una observación cita otra acta y el baseline mezcla dos cohortes",
                   _insumo_de_otra_acta),
)


def _correr_el_modo(observaciones: list[dict], etiqueta: str) -> tuple[int, str | None]:
    """Invoca `--generar-baseline` de punta a punta sobre un conjunto de observaciones en disco, y
    devuelve su código de salida y lo que quedó escrito. Un modo que revienta cuenta como código
    distinto de 0: el veredicto es el código, no el mensaje."""
    with tempfile.TemporaryDirectory() as temporal:
        raiz = Path(temporal) / etiqueta
        raiz.mkdir()
        for observacion in observaciones:
            (raiz / f"{observacion.get('observation_id')}.json").write_text(
                json.dumps(observacion, ensure_ascii=False), encoding="utf-8")
        destino = Path(temporal) / "baseline-fase-0.md"
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                codigo = modo_generar_baseline(argparse.Namespace(
                    generar_baseline=str(raiz),
                    preregistro=str(DIR_FIXTURES_GENERACION / "preregistro.json"),
                    salida=str(destino)))
        except Exception:  # noqa: BLE001 — reventar es una forma de no terminar bien, no un verde
            codigo = -1
        return codigo, destino.read_text(encoding="utf-8") if destino.exists() else None


def modo_autotest_generacion(args: argparse.Namespace) -> int:
    del args
    manifest, preregistro, observaciones, golden, problemas = _corpus_de_generacion()
    vocabulario, esquemas, mas = _cargar_insumos_de_recoleccion()
    if problemas + mas:
        for p in problemas + mas:
            print(f"[A] FALLA  {p}")
        return 1

    resultados: list[tuple[str, bool, str]] = []

    # [A] Manifest ↔ disco en las dos direcciones, y cada observación válida contra su contrato
    # (D-16). Un corpus que se declara a sí mismo no ve la observación que alguien borró.
    declaradas = set(manifest.get("observaciones") or [])
    en_disco = {o.get("observation_id") for o in observaciones}
    diferencias = [f"declarada y ausente del disco: {o}" for o in sorted(declaradas - en_disco)]
    diferencias += [f"en disco y no declarada: {o}" for o in sorted(en_disco - declaradas)]
    for observacion in observaciones:
        for error in validar(observacion, esquemas["observacion"]):
            diferencias.append(f"{observacion.get('observation_id')}: {error.ruta}: {error.mensaje}")
    resultados.append(("A", not diferencias,
                       f"manifest ↔ directorio y schema ({len(declaradas)} observaciones)"
                       if not diferencias else " | ".join(diferencias[:4])))

    # [B] El control positivo: generar da EXACTAMENTE el golden, que está escrito a mano. Un
    # esperado producido por el propio generador probaría que su salida no cambia, no que sea la
    # correcta.
    texto, fallas_de_generacion = generar_baseline(preregistro, observaciones, vocabulario)
    if texto is None:
        resultados.append(("B", False, " | ".join(fallas_de_generacion[:4])))
    else:
        iguales = texto == golden
        detalle = "el documento generado coincide byte a byte con el golden escrito a mano"
        if not iguales:
            esperadas, obtenidas = golden.splitlines(), texto.splitlines()
            primera = next((i for i in range(max(len(esperadas), len(obtenidas)))
                            if esperadas[i:i + 1] != obtenidas[i:i + 1]), 0)
            detalle = (f"difiere del golden en la línea {primera + 1}: "
                       f"esperada {esperadas[primera:primera + 1]} · "
                       f"obtenida {obtenidas[primera:primera + 1]}")
        resultados.append(("B", iguales, detalle))

    # [C] Determinismo: mismo insumo, mismos bytes — y el orden en que llegan las observaciones no
    # cambia nada. Es el control que caza un generador que ordena por el glob del disco.
    fallas: list[str] = []
    if texto is not None:
        repetido, _ = generar_baseline(preregistro, copy.deepcopy(observaciones), vocabulario)
        if repetido != texto:
            fallas.append("dos generaciones con el mismo insumo dan bytes distintos")
        invertido, _ = generar_baseline(preregistro,
                                        list(reversed(copy.deepcopy(observaciones))), vocabulario)
        if invertido != texto:
            fallas.append("el orden en que se leen las observaciones cambia el documento")
    resultados.append(("C", texto is not None and not fallas,
                       "misma entrada y orden invertido dan los mismos bytes" if not fallas
                       else " | ".join(fallas)))

    # [D] Las métricas que el manifest declara sin observaciones salen declaradas como tales, con
    # su adjudicación y con el detalle por observación de POR QUÉ. El manifest es independiente: sin
    # él, una métrica que dejara de emitirse no tendría quién la reclame.
    publicados, fallas_de_lectura = numeros_publicados_del_markdown(texto or "")
    fallas = list(fallas_de_lectura)
    for entrada in manifest.get("metricas_sin_observaciones") or []:
        metrica_id = entrada.get("metrica_id")
        publicado = publicados.get(metrica_id)
        if publicado is None:
            fallas.append(f"«{metrica_id}»: el manifest la declara sin observaciones y el documento "
                          "no la publica")
            continue
        if publicado.valor is not None:
            fallas.append(f"«{metrica_id}»: se publica como {publicado.valor!r} y el manifest la "
                          "declara sin observaciones")
        if not publicado.adjudicacion or publicado.adjudicacion == SIN_ADJUDICACION:
            fallas.append(f"«{metrica_id}»: sin adjudicación en la tabla de números")
        causa = entrada.get("causa")
        if texto and f"| {causa} |" not in texto:
            fallas.append(f"«{metrica_id}»: el documento no declara la causa «{causa}» que cada "
                          "observación escribió: el agregado solo no la distingue")
    for metrica_id in manifest.get("metricas_publicadas") or []:
        publicado = publicados.get(metrica_id)
        if publicado is None or publicado.valor is None:
            fallas.append(f"«{metrica_id}»: el manifest la declara publicada con valor y el "
                          "documento no la publica así")
    resultados.append(("D", not fallas,
                       f"{len(manifest.get('metricas_sin_observaciones') or [])} métricas "
                       f"declaradas sin observaciones y "
                       f"{len(manifest.get('metricas_publicadas') or [])} con valor, contra el "
                       "manifest independiente" if not fallas else " | ".join(fallas[:4])))

    # [E] El documento se lee de vuelta y da EXACTAMENTE lo recompuesto. Es lo que permitirá
    # comprobar el baseline real, donde no hay golden contra el cual comparar.
    vuelta = revisar_baseline(texto or "", preregistro, observaciones, vocabulario)
    resultados.append(("E", not vuelta,
                       f"los {len(publicados)} números del documento se leen de vuelta y coinciden "
                       "con la recomposición" if not vuelta else " | ".join(vuelta[:4])))

    # [F] Los ataques al documento: cada uno tiene que poner rojo a `revisar_baseline`. Un ataque que
    # no se puede aplicar es cobertura fantasma y se reporta como falla, no se saltea.
    fallas = []
    for ataque in ATAQUES_AL_BASELINE:
        atacado = ataque.aplicar(texto or "", manifest)
        if atacado is None or atacado == texto:
            fallas.append(f"«{ataque.nombre}»: la mutación no se pudo aplicar")
            continue
        detectados = revisar_baseline(atacado, preregistro, observaciones, vocabulario)
        if not any(ataque.motivo_esperado in d for d in detectados):
            fallas.append(f"«{ataque.nombre}»: {ataque.que_rompe} y no cae por "
                          f"«{ataque.motivo_esperado}» — se vio: "
                          f"{detectados[0] if detectados else 'nada'}")
    resultados.append(("F", not fallas,
                       f"los {len(ATAQUES_AL_BASELINE)} ataques al documento lo ponen rojo"
                       if not fallas else " | ".join(fallas[:4])))

    # [G] Los ataques al insumo: si el número estuviera escrito en el generador en vez de derivado,
    # cambiar la observación no cambiaría el documento y esto pasaría igual.
    fallas = []
    for ataque in ATAQUES_AL_INSUMO:
        copia = copy.deepcopy(observaciones)
        if not ataque.aplicar(copia):
            fallas.append(f"«{ataque.nombre}»: la mutación no se pudo aplicar")
            continue
        otro, problemas_del_ataque = generar_baseline(preregistro, copia, vocabulario)
        if otro is None:
            continue  # la generación se negó a producir: es la detección más fuerte
        del problemas_del_ataque
        if otro == texto:
            fallas.append(f"«{ataque.nombre}»: {ataque.que_rompe}")
    resultados.append(("G", not fallas,
                       f"los {len(ATAQUES_AL_INSUMO)} ataques al insumo cambian o detienen la "
                       "generación" if not fallas else " | ".join(fallas[:4])))

    # [H] El MODO entero, no sus funciones: carga de rutas, escritura a disco y código de salida.
    # Un generador correcto detrás de un modo roto deja los seis controles de arriba en verde y el
    # comando que T22 invoca sin producir nada. Va con su NEGATIVO —un insumo que la generación
    # rechaza— porque el camino feliz solo no distingue un modo que se detiene de uno que ignora la
    # negativa y escribe igual.
    fallas = []
    codigo, escrito = _correr_el_modo(observaciones, "sano")
    if codigo != 0:
        fallas.append(f"sobre el corpus sano el modo devolvió {codigo}")
    elif escrito != golden:
        fallas.append("sobre el corpus sano el modo escribió un documento distinto del golden")

    rechazadas = copy.deepcopy(observaciones)
    if not _insumo_de_otra_acta(rechazadas):
        fallas.append("no se pudo armar el insumo que la generación tiene que rechazar")
    else:
        codigo, escrito = _correr_el_modo(rechazadas, "rechazado")
        if codigo == 0:
            fallas.append("con una observación de otra acta el modo devolvió 0")
        if escrito is not None:
            fallas.append("con una observación de otra acta el modo escribió el documento igual")
    resultados.append(("H", not fallas,
                       "el modo escribe y sale en 0 sobre el corpus sano, y sobre el rechazado no "
                       "escribe y sale distinto de 0" if not fallas else " | ".join(fallas[:4])))

    return _cerrar(resultados)


# ---------------------------------------------------------------------------------------------
# El motor de extracción tipada, PORTADO (D-1).
#
# `resolver_procedencia()` de `scripts/verificar-matriz-despachos.py` es exactamente lo que AC-34
# necesita para derivar cada receta de su ancla. **Se porta y no se importa**: importar ese archivo
# como módulo ataría el comportamiento del instrumento —y por lo tanto los números del baseline— a
# un archivo cuyo hash el pre-registro no cubre. El costo asumido es duplicación real.
#
# La protección contra divergencia **no es un fixture del resultado final**: es el corpus
# diferencial de `--autotest-procedencia-portada`, que ejercita cada forma tipada que usan las trece
# recetas, con las salidas producidas por el motor ORIGINAL y congeladas. Ese corpus es la frontera
# de compatibilidad **declarada**: lo que no está en él puede divergir sin que nada lo note, y eso
# queda dicho acá en vez de supuesto.
#
# Las cuatro adaptaciones del port, y ninguna más:
#
# 1. `_celdas` → `_celdas_de_fila`, porque `_celda` de este archivo hace lo contrario (emite una
#    celda en vez de parsearla) y dos nombres a una letra de distancia con sentidos opuestos son
#    una trampa. No cambia comportamiento.
# 2. `RUTA_SCHEMA` → `RUTA_SCHEMA_MATRIZ`: el schema de la matriz, que es de donde
#    `tablas_de_conversion()` lee `x-conversiones`. Sigue siendo la misma sede.
# 3. `_slug` importaba `norm` de `verificar-sobre-en-vuelo.py` por ruta; acá esa normalización se
#    porta como `_titulo_normalizado`, por el mismo motivo que el resto.
# 4. `ARTEFACTOS_DEL_FLUJO` se deriva de las constantes de ESTE flujo, no de las del flujo 1. La
#    precondición existe para impedir que una hoja se cite a sí misma, y quién es «sí misma»
#    depende de quién resuelve. Si esta constante quedara con los artefactos del otro flujo, una
#    receta podría declarar como sede el archivo de recetas y el resolutor le daría la razón.
# ---------------------------------------------------------------------------------------------

RUTA_SCHEMA_MATRIZ = DIR_SCRIPTS / "matriz-despachos.schema.json"
RUTA_RECETAS = DIR_SCRIPTS / "recetas-cohorte.json"


def _titulo_normalizado(texto: str) -> str:
    """Minúsculas, sin diacríticos, sin énfasis markdown ni backticks, con la puntuación de
    enumeración convertida en espacio y los espacios colapsados. Portada de la primitiva de
    biyección: es la ortografía con la que las anclas de la matriz nombran sus secciones, y una
    segunda ortografía escrita acá daría dos slugs del mismo encabezado."""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    for ch in "`*·—–…":
        texto = texto.replace(ch, " ")
    return re.sub(r"\s+", " ", texto).strip().lower()


def _artefactos_de_este_flujo() -> tuple[str, ...]:
    """Lo que ESTE flujo produce, en rutas relativas al repositorio. Se deriva de las constantes del
    módulo y no se transcribe: una lista escrita a mano quedaría vieja en cuanto un artefacto
    cambiara de nombre, y la autorreferencia volvería a pasar como sede legítima."""
    rutas = (RUTA_RECETAS, DIR_SCRIPTS / "preregistro-fase-0.json",
             DIR_SCRIPTS / "metricas-fase-0.json", DIR_SCRIPTS / "dag-procedencia.json",
             DIR_SCRIPTS / "interfaz-de-reloj.json", DIR_SCRIPTS / "fixtures-baseline",
             DIR_SCRIPTS / "corridas-fase-0", DIR_SCRIPTS / "observaciones-fase-0",
             Path(RUTA_BASELINE_FASE_0), Path(__file__).resolve())
    return tuple(sorted(
        (r if not r.is_absolute() else r.relative_to(RAIZ)).as_posix() for r in rutas))


ARTEFACTOS_DEL_FLUJO = _artefactos_de_este_flujo()

# El centinela de «la ruta no existe», distinto de un `None` que la sede sí declara.
_SIN_VALOR = object()

_tablas_de_conversion_cache: dict[str, dict[str, Any]] | None = None


ERRORES_DE_RESOLUCION = (
    "sede_inexistente",
    "selector_sin_resultado",
    "cardinalidad_no_coincide",
    "conversion_fallida",
    "sede_no_admisible",
    "colapso_no_unico",
)

# Los pasos del pipeline, en el orden en que este código los ejecuta. NO es la fuente: la fuente es
# `x-pipeline.orden` del schema, y `_pipeline_desalineado()` compara los dos. Congelarlo acá sin
# comparar daría dos órdenes que pueden divergir en silencio.


TEXTOS_BOOLEANOS = {"true": True, "false": False}

# El texto que emite `presencia_de_clausula` cuando la cláusula está. **No se escribe a mano**: se
# deriva de `TEXTOS_BOOLEANOS`, que es quien declara la ortografía que `conversion: booleano` sabe
# cotejar. Dos ortografías —una acá y otra allá— dejarían la extracción produciendo un texto que su
# propia conversión no reconoce, y el rojo aparecería lejos de su causa.
TEXTO_AFIRMATIVO = next(t for t, v in TEXTOS_BOOLEANOS.items() if v is True)


PATRON_ENTERO = re.compile(r"^-?\d+$")
PATRON_REFERENCIA = re.compile(r"^[A-Za-z0-9._/-]+(#[A-Za-z0-9._-]+)?$")

PATRON_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
PATRON_FENCE = re.compile(r"^\s*(`{3,}|~{3,})\s*(\S*)")
PATRON_CELDA_SEPARADORA = re.compile(r"^:?-+:?$")
PATRON_CONVERSION_ENUM = re.compile(r"^enum:([a-z][a-z0-9_]*)$")


class Resultado(NamedTuple):
    """Lo que devuelve `resolver_procedencia`.

    En el caso exitoso trae los tres campos del contrato —`valor`, `cardinalidad_observada` y
    `sede_resuelta`— y `error is None`. En el fallido, `error` es uno de `ERRORES_DE_RESOLUCION` y
    `valor` es `None`: nunca hay valor y error a la vez, porque un resolutor que devolviera un valor
    junto con su falla invitaría a usarlo.

    `cardinalidad_observada` se informa también en varios fallos —es el dato que
    `cardinalidad_no_coincide` necesita nombrar—; `causa` y `detalle` son diagnóstico."""

    valor: Any = None
    cardinalidad_observada: int | None = None
    sede_resuelta: Path | None = None
    error: str | None = None
    causa: str | None = None
    detalle: str = ""

    @property
    def ok(self) -> bool:
        return self.error is None


def _falla(error: str, causa: str, detalle: str, **extra: Any) -> Resultado:
    return Resultado(error=error, causa=causa, detalle=detalle, **extra)


# --- Lectura de la sede -----------------------------------------------------------------------


def _lineas_fuera_de_fence(texto: str) -> list[bool]:
    """Para cada línea, si está dentro de un bloque cercado. Lo consumen la selección por heading y
    la de filas de tabla: un `##` dentro de un bloque de código es texto, no una sección. La
    selección por patrón **sí** mira adentro, porque el schema la declara para «prosa y bloques de
    código»."""
    fuera: list[bool] = []
    cerca: str | None = None
    for linea in texto.splitlines():
        m = PATRON_FENCE.match(linea)
        if cerca is None:
            if m:
                cerca = m.group(1)[0] * 3
                fuera.append(False)
                continue
            fuera.append(True)
        else:
            fuera.append(False)
            if m and m.group(1).startswith(cerca):
                cerca = None
    return fuera


def _celdas_de_fila(linea: str) -> list[str]:
    """Las celdas de una fila de tabla Markdown. El corte es por `|` no escapado: una celda que
    contiene `\\|` es una celda y no dos."""
    partes = re.split(r"(?<!\\)\|", linea.strip())
    if partes and not partes[0].strip():
        partes = partes[1:]
    if partes and not partes[-1].strip():
        partes = partes[:-1]
    return [p.replace("\\|", "|").strip() for p in partes]


def _es_separadora(linea: str) -> bool:
    celdas = _celdas_de_fila(linea)
    return bool(celdas) and all(PATRON_CELDA_SEPARADORA.fullmatch(c) for c in celdas)


class NodoSeleccionado(NamedTuple):
    """Un nodo con su posición en la sede. La línea la consume `ancla_de_seccion`, la única
    extracción cuyo resultado depende de **dónde** está el nodo y no solo de qué dice."""

    valor: Any
    linea: int      # 0-based, la línea de la sede donde el nodo aparece


def _seleccionar_por_heading(texto: str, selector: dict) -> list[NodoSeleccionado]:
    """El nodo de un `heading_markdown` es el **texto del propio encabezado** —sin los `#` ni el
    espacio que los separa—, no el cuerpo de la sección. Es lo que el schema declara y es lo que
    hace consistente a este tipo de sede con los otros tres: en todos, el nodo es la unidad más
    chica que el selector nombra —la celda y no la fila, la línea y no el párrafo, el valor de la
    ruta y no el documento—, y acá el selector nombra un encabezado."""
    lineas, fuera = texto.splitlines(), _lineas_fuera_de_fence(texto)
    buscado, nivel = selector.get("texto"), selector.get("nivel")
    nodos: list[NodoSeleccionado] = []
    for i, linea in enumerate(lineas):
        m = PATRON_HEADING.match(linea) if fuera[i] else None
        if m and len(m.group(1)) == nivel and m.group(2).strip() == buscado:
            nodos.append(NodoSeleccionado(m.group(2).strip(), i))
    return nodos


def _seleccionar_por_fila(texto: str, selector: dict) -> list[NodoSeleccionado]:
    """La celda de la columna pedida, en cada fila cuya primera celda es la clave. Una tabla que no
    tiene esa columna no aporta nodos: la sede más común del repo tiene la misma clave en varias
    tablas y solo algunas la describen en esa dimensión."""
    lineas, fuera = texto.splitlines(), _lineas_fuera_de_fence(texto)
    clave, columna = selector.get("clave_primera_celda"), selector.get("encabezado_de_columna")
    nodos: list[NodoSeleccionado] = []
    i = 0
    while i < len(lineas) - 1:
        if not (fuera[i] and lineas[i].strip().startswith("|") and _es_separadora(lineas[i + 1])):
            i += 1
            continue
        encabezados = _celdas_de_fila(lineas[i])
        indice = encabezados.index(columna) if columna in encabezados else None
        j = i + 2
        while j < len(lineas) and fuera[j] and lineas[j].strip().startswith("|"):
            celdas = _celdas_de_fila(lineas[j])
            if indice is not None and celdas and celdas[0] == clave and indice < len(celdas):
                nodos.append(NodoSeleccionado(celdas[indice], j))
            j += 1
        i = j
    return nodos


def _bloques_cercados(texto: str, lenguaje: str) -> list[tuple[str, int]]:
    """Cada bloque cercado del lenguaje pedido, con la línea de su fence de apertura. La línea es
    lo que ancla el bloque a una sección: un documento estructurado embebido no tiene encabezados
    propios, así que su sección es la del Markdown que lo contiene."""
    bloques: list[tuple[str, int]] = []
    cerca: str | None = None
    acumulado: list[str] = []
    coincide = False
    apertura = 0
    for i, linea in enumerate(texto.splitlines()):
        m = PATRON_FENCE.match(linea)
        if cerca is None:
            if m:
                cerca = m.group(1)[0] * 3
                coincide = m.group(2) == lenguaje
                acumulado = []
                apertura = i
            continue
        if m and m.group(1).startswith(cerca):
            if coincide:
                bloques.append(("\n".join(acumulado), apertura))
            cerca = None
            continue
        acumulado.append(linea)
    return bloques


def _parsear(texto: str, formato: str) -> tuple[Any, str | None]:
    if formato == "json":
        try:
            return json.loads(texto), None
        except json.JSONDecodeError as e:
            return None, f"JSON ilegible: {e}"
    if formato == "yaml":
        try:
            import yaml  # PyYAML: el repo ya lo usa en sus otras guardas
        except ImportError:
            return None, "sin PyYAML no se puede leer una sede `yaml`"
        try:
            return yaml.safe_load(texto), None
        except yaml.YAMLError as e:
            return None, f"YAML ilegible: {e}"
    return None, f"formato estructurado desconocido: {formato!r}"


def _bajar(dato: Any, ruta: Any) -> Any:
    """Baja por una ruta de clave —lista de segmentos: cadenas para claves, enteros para índices—.
    Devuelve el centinela cuando el camino no existe."""
    if not isinstance(ruta, list) or not ruta:
        return _SIN_VALOR
    actual = dato
    for segmento in ruta:
        if isinstance(segmento, bool):
            return _SIN_VALOR
        if isinstance(segmento, int):
            if not isinstance(actual, list) or not -len(actual) <= segmento < len(actual):
                return _SIN_VALOR
            actual = actual[segmento]
        elif isinstance(segmento, str):
            if not isinstance(actual, dict) or segmento not in actual:
                return _SIN_VALOR
            actual = actual[segmento]
        else:
            return _SIN_VALOR
    return actual


def _seleccionar_por_clave(texto: str, selector: dict) -> tuple[list[NodoSeleccionado], str | None]:
    """Los documentos estructurados de la sede —el archivo entero, o cada bloque cercado del
    lenguaje declarado— y, en cada uno, el valor de la ruta. Cuando ese valor es una **lista**, sus
    elementos son los nodos: una sede genuinamente multivaluada se declara así y no como varios
    documentos."""
    formato = selector.get("formato")
    lenguaje = selector.get("lenguaje_del_bloque")
    documentos = (_bloques_cercados(texto, lenguaje) if isinstance(lenguaje, str)
                  else [(texto, 0)])
    nodos: list[NodoSeleccionado] = []
    for bruto, linea in documentos:
        dato, error = _parsear(bruto, formato)
        if error:
            return [], error
        valor = _bajar(dato, selector.get("ruta"))
        if valor is _SIN_VALOR:
            continue
        crudos = valor if isinstance(valor, list) else [valor]
        nodos.extend(NodoSeleccionado(v, linea) for v in crudos)
    return nodos, None


def _seleccionar_por_patron(texto: str, selector: dict) -> tuple[list[NodoSeleccionado], str | None]:
    try:
        patron = re.compile(selector.get("patron", ""))
    except re.error as e:
        return [], f"el patrón del selector no compila: {e}"
    return [NodoSeleccionado(linea, i) for i, linea in enumerate(texto.splitlines())
            if patron.search(linea)], None


def _seleccionar(procedencia: dict, texto: str) -> tuple[list[NodoSeleccionado], str | None]:
    tipo = procedencia.get("tipo_de_sede")
    selector = procedencia.get("selector")
    if not isinstance(selector, dict):
        return [], "la procedencia no trae un `selector` que ejecutar"
    if tipo == "heading_markdown":
        return _seleccionar_por_heading(texto, selector), None
    if tipo == "fila_de_tabla_markdown":
        return _seleccionar_por_fila(texto, selector), None
    if tipo == "clave_estructurada":
        return _seleccionar_por_clave(texto, selector)
    if tipo == "patron_de_linea":
        return _seleccionar_por_patron(texto, selector)
    return [], f"`tipo_de_sede` desconocido: {tipo!r}"


# --- Los pasos del pipeline -------------------------------------------------------------------


def _texto_de_nodo(nodo: Any) -> str | None:
    """El texto de un nodo. Un nodo estructurado escalar se textualiza con la ortografía de su
    formato —`true`/`false` y no `True`/`False`—, para que la tabla de conversión coteje contra lo
    que la sede dice. Un objeto o un arreglo no son texto: extraerlos como si lo fueran produciría
    un valor plausible falso."""
    if isinstance(nodo, str):
        return nodo
    if isinstance(nodo, bool):
        return "true" if nodo else "false"
    if isinstance(nodo, (int, float)):
        return str(nodo)
    return None


def _encabezados_de(texto: str) -> list[tuple[int, str]]:
    """Los encabezados de la sede, en orden de documento, con su línea. Los que viven dentro de un
    bloque cercado no cuentan: ahí un `##` es texto y no una sección, el mismo criterio que usan la
    selección por heading y la de filas."""
    fuera = _lineas_fuera_de_fence(texto)
    encabezados: list[tuple[int, str]] = []
    for i, linea in enumerate(texto.splitlines()):
        m = PATRON_HEADING.match(linea) if fuera[i] else None
        if m:
            encabezados.append((i, m.group(2).strip()))
    return encabezados


def _ancla_de_seccion(sede: str, encabezados: list[tuple[int, str]], linea: int) -> str | None:
    """`<sede>#<slug>` de la sección que contiene al nodo: el encabezado más cercano **en o antes**
    de su línea, de cualquier nivel. «En o antes» es lo que hace que un `heading_markdown` —cuyo
    nodo ES el encabezado— quede anclado a su propia sección y no a la anterior.

    El slug lo produce `_slug`, la misma primitiva con la que `--completitud` coteja las anclas
    contra el árbol. Un segundo slug escrito acá daría dos ortografías del mismo fragmento y los
    dos modos podrían estar verdes sobre anclas distintas."""
    titulo = next((t for i, t in reversed(encabezados) if i <= linea), None)
    return f"{sede}#{_slug(titulo)}" if titulo is not None else None


def _extraer(extraccion: Any, nodo: Any, ancla: str | None = None) -> tuple[str | None, str]:
    if not isinstance(extraccion, dict):
        return None, "extraccion_no_declarada"
    tipo = extraccion.get("tipo")
    if tipo == "ancla_de_seccion":
        return (ancla, "") if ancla else (None, "ancla_sin_seccion")
    if tipo == "literal":
        texto = _texto_de_nodo(nodo)
        return (texto, "") if texto is not None else (None, "nodo_no_escalar")
    if tipo == "captura_de_grupo":
        texto = _texto_de_nodo(nodo)
        if texto is None:
            return None, "nodo_no_escalar"
        try:
            m = re.search(extraccion.get("patron", ""), texto)
        except re.error:
            return None, "extraccion_patron_invalido"
        if m is None:
            return None, "extraccion_sin_coincidencia"
        grupo = extraccion.get("grupo")
        if (not isinstance(grupo, int) or isinstance(grupo, bool)
                or not 0 <= grupo <= len(m.groups())):
            return None, "extraccion_grupo_inexistente"
        capturado = m.group(grupo)
        return (capturado, "") if capturado is not None else (None, "extraccion_grupo_vacio")
    if tipo == "presencia_de_clausula":
        texto = _texto_de_nodo(nodo)
        if texto is None:
            return None, "nodo_no_escalar"
        clausula = extraccion.get("clausula")
        if not isinstance(clausula, str) or not clausula:
            return None, "clausula_no_declarada"
        # `in` y no `re.search`: la cláusula es literal. Compilarla como patrón dejaría que un `.*`
        # case cualquier cosa, que es justo la degeneración que este subtipo tiene que impedir.
        # Se emite el texto afirmativo y nunca el negativo: la ausencia de la cláusula es rojo, no
        # `false`, porque que la sede no lo diga no es que la sede diga lo contrario.
        return (TEXTO_AFIRMATIVO, "") if clausula in texto else (None, "clausula_ausente")
    if tipo == "valor_de_clave":
        valor = _bajar(nodo, extraccion.get("clave"))
        if valor is _SIN_VALOR:
            return None, "extraccion_clave_ausente"
        texto = _texto_de_nodo(valor)
        return (texto, "") if texto is not None else (None, "nodo_no_escalar")
    return None, "extraccion_desconocida"


def _normalizar(normalizacion: Any, texto: str) -> tuple[str | None, str]:
    if normalizacion == "ninguna":
        return texto, ""
    if normalizacion == "trim":
        return texto.strip(), ""
    if normalizacion == "colapsar_espacios":
        return re.sub(r"\s+", " ", texto).strip(), ""
    if normalizacion == "minusculas":
        return texto.lower(), ""
    return None, "normalizacion_desconocida"


def _ordenar(orden: Any, valores: list[str]) -> tuple[list[str] | None, str]:
    """Sobre el valor **normalizado**, antes de convertir. `lexicografico` compara por punto de
    código —el orden natural de `str` en Python— y no por locale."""
    if orden is None or orden == "documento":
        return list(valores), ""
    if orden == "lexicografico":
        return sorted(valores), ""
    return None, "orden_desconocido"


def tablas_de_conversion() -> dict[str, dict[str, Any]]:
    """El mapeo texto → token de cada `enum:<nombre>`, leído de `x-conversiones` del schema. **No se
    reescribe acá**: una segunda tabla distinta de la que usó quien pobló la matriz pondría en rojo
    hojas que están bien, y ese es el defecto que el bloque del schema existe para cerrar."""
    global _tablas_de_conversion_cache
    if _tablas_de_conversion_cache is None:
        schema, error = _cargar_json(RUTA_SCHEMA_MATRIZ)
        reglas = {} if error else (schema.get("x-conversiones", {}).get("reglas", {}) or {})
        _tablas_de_conversion_cache = {
            nombre: {par["texto"]: par["token"] for par in tabla.get("pares", [])
                     if isinstance(par, dict) and isinstance(par.get("texto"), str)}
            for nombre, tabla in reglas.items() if isinstance(tabla, dict)
        }
    return _tablas_de_conversion_cache


def _convertir(conversion: Any, texto: str) -> tuple[Any, str]:
    if conversion == "cadena":
        return texto, ""
    if conversion == "entero":
        return (int(texto), "") if PATRON_ENTERO.fullmatch(texto) else (None, "entero_no_reconocido")
    if conversion == "booleano":
        if texto in TEXTOS_BOOLEANOS:
            return TEXTOS_BOOLEANOS[texto], ""
        return None, "booleano_sin_par"
    if conversion == "referencia":
        return (texto, "") if PATRON_REFERENCIA.fullmatch(texto) else (None, "referencia_mal_formada")
    m = PATRON_CONVERSION_ENUM.fullmatch(conversion) if isinstance(conversion, str) else None
    if m is None:
        return None, "conversion_desconocida"
    tabla = tablas_de_conversion().get(m.group(1))
    if tabla is None:
        return None, "conversion_sin_tabla"
    if texto not in tabla:
        return None, "conversion_sin_par"
    return tabla[texto], ""


def _cardinalidad_satisfecha(cardinalidad: Any, observada: int) -> tuple[bool, str]:
    """Cada variante con su predicado, sin una regla general que los contradiga. Cero resultados no
    llega hasta acá: lo ataja `selector_sin_resultado`, que es más específico.

    Devuelve el mensaje ya armado y no una plantilla: un `tipo` que llegue como objeto mete llaves en
    el texto, y una plantilla formateada después reventaría justo sobre el dato mal formado que se
    estaba por reportar."""
    if not isinstance(cardinalidad, dict):
        return False, "la hoja no declara `cardinalidad`"
    tipo = cardinalidad.get("tipo")
    if tipo == "exactamente_una":
        return observada == 1, f"se declaró `exactamente_una` y el selector devolvió {observada}"
    if tipo == "al_menos_una":
        return observada >= 1, f"se declaró `al_menos_una` y el selector devolvió {observada}"
    if tipo == "exactamente_n":
        n = cardinalidad.get("n")
        if not isinstance(n, int) or isinstance(n, bool):
            return False, "`exactamente_n` sin un `n` entero"
        return observada == n, (f"se declaró `exactamente_n` con n={n} y el selector devolvió "
                                f"{observada}")
    return False, f"variante de cardinalidad desconocida: {tipo!r}"


def _colapsar(cardinalidad: Any, valores: list[Any]) -> tuple[Any, str]:
    """`exactamente_una` no declara `colapso` —su único valor es el resultado—; las otras dos sí.
    `unico_si_iguales` opera sobre los valores **convertidos**: dos textos distintos que convergen al
    mismo token son un colapso legítimo, y rechazarlos sería el resolutor demasiado estricto."""
    if isinstance(cardinalidad, dict) and cardinalidad.get("tipo") == "exactamente_una":
        return valores[0], ""
    colapso = cardinalidad.get("colapso") if isinstance(cardinalidad, dict) else None
    if colapso == "lista":
        return valores, ""
    if colapso == "unico_si_iguales":
        primero = valores[0]
        if all(_mismo(primero, v) for v in valores[1:]):
            return primero, ""
        return None, "colapso_no_unico"
    return None, "colapso_desconocido"


def _sede_no_admisible(sede: Any) -> bool:
    """Una hoja que se cita a sí misma coincide siempre consigo misma: el resolutor, la matriz y su
    fila quedan los tres verdes sin ninguna evidencia independiente."""
    if not isinstance(sede, str):
        return False
    limpia = sede.strip().lstrip("./")
    return any(limpia == a or limpia.startswith(a + "/") for a in ARTEFACTOS_DEL_FLUJO)


def resolver_procedencia(procedencia: dict, raiz: Path) -> Resultado:
    """Ejecuta una procedencia **anclada** contra su sede y devuelve el valor que la sede dice.

    Contrato de invocación —lo consumen los modos de acá y las otras tasks que resuelven contra
    sedes que no son la matriz—:

    - `procedencia`: la forma anclada, con sus siete campos.
    - `raiz`: la raíz contra la que se interpreta `sede`, que es una ruta relativa.
    - Devuelve `Resultado`: `valor`, `cardinalidad_observada` y `sede_resuelta` cuando resuelve, o
      `error` ∈ `ERRORES_DE_RESOLUCION` cuando no.

    **Su dominio es solo la variante anclada.** Una procedencia `{ausencia: <motivo>}` no se le pasa:
    no hay nada que resolver y devolver un resultado para ella obligaría a inventar un valor. Quien
    la encuentra la clasifica como adjudicación pendiente. Pasarla igual levanta `ValueError` y no
    un `Resultado`: un error de programa no puede confundirse con una resolución fallida."""
    if not isinstance(procedencia, dict):
        raise ValueError("resolver_procedencia espera un objeto de procedencia anclada")
    if "ausencia" in procedencia:
        raise ValueError(
            "resolver_procedencia no admite la variante de ausencia: una hoja con `{ausencia}` es "
            "adjudicación pendiente y se clasifica sin llamar a esta función")

    sede = procedencia.get("sede")
    # Precondición 1: la sede no puede ser un artefacto de este flujo. Va antes que la existencia.
    if _sede_no_admisible(sede):
        return _falla("sede_no_admisible", "artefacto_del_flujo",
                      f"la sede `{sede}` es un artefacto que este flujo produce: una hoja que se "
                      "cita a sí misma coincide siempre consigo misma")
    if not isinstance(sede, str) or not sede:
        return _falla("sede_inexistente", "sede_no_declarada", "la procedencia no declara `sede`")
    # Precondición 2: existencia.
    ruta_sede = (raiz / sede).resolve()
    if not ruta_sede.is_file():
        return _falla("sede_inexistente", "archivo_ausente",
                      f"no existe la sede `{sede}` bajo {raiz}", sede_resuelta=ruta_sede)
    try:
        texto = ruta_sede.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return _falla("sede_inexistente", "sede_ilegible", f"no se puede leer `{sede}`: {e}",
                      sede_resuelta=ruta_sede)

    # 1 · seleccionar
    nodos, error = _seleccionar(procedencia, texto)
    if error:
        return _falla("selector_sin_resultado", "selector_inejecutable", error,
                      sede_resuelta=ruta_sede)
    observada = len(nodos)
    if observada == 0:
        return _falla("selector_sin_resultado", "sin_nodos",
                      f"el selector no seleccionó ningún nodo en `{sede}`",
                      cardinalidad_observada=0, sede_resuelta=ruta_sede)

    # 2 · comprobar cardinalidad, **sobre los nodos seleccionados y antes de extraer**
    cardinalidad = procedencia.get("cardinalidad")
    satisface, mensaje = _cardinalidad_satisfecha(cardinalidad, observada)
    if not satisface:
        return _falla("cardinalidad_no_coincide", "predicado_no_satisfecho", mensaje,
                      cardinalidad_observada=observada, sede_resuelta=ruta_sede)

    # 3 · extraer  ·  4 · normalizar
    encabezados = _encabezados_de(texto)
    normalizados: list[str] = []
    for nodo in nodos:
        texto_nodo, causa = _extraer(procedencia.get("extraccion"), nodo.valor,
                                     _ancla_de_seccion(sede, encabezados, nodo.linea))
        if texto_nodo is None:
            return _falla("conversion_fallida", causa,
                          f"no se pudo extraer el valor de un nodo de `{sede}`",
                          cardinalidad_observada=observada, sede_resuelta=ruta_sede)
        normalizado, causa = _normalizar(procedencia.get("normalizacion"), texto_nodo)
        if normalizado is None:
            return _falla("conversion_fallida", causa,
                          f"normalizacion no declarada: {procedencia.get('normalizacion')!r}",
                          cardinalidad_observada=observada, sede_resuelta=ruta_sede)
        normalizados.append(normalizado)

    # 5 · ordenar, sobre el valor normalizado y antes de convertir
    orden = cardinalidad.get("orden") if isinstance(cardinalidad, dict) else None
    ordenados, causa = _ordenar(orden, normalizados)
    if ordenados is None:
        return _falla("conversion_fallida", causa, f"orden no declarado: {orden!r}",
                      cardinalidad_observada=observada, sede_resuelta=ruta_sede)

    # 6 · convertir
    convertidos: list[Any] = []
    for normalizado in ordenados:
        convertido, causa = _convertir(procedencia.get("conversion"), normalizado)
        if causa:
            return _falla("conversion_fallida", causa,
                          f"{normalizado!r} no convierte a `{procedencia.get('conversion')}`",
                          cardinalidad_observada=observada, sede_resuelta=ruta_sede)
        convertidos.append(convertido)

    # 7 · colapsar
    valor, causa = _colapsar(cardinalidad, convertidos)
    if causa == "colapso_no_unico":
        return _falla("colapso_no_unico", causa,
                      f"`unico_si_iguales` sobre valores que difieren: {convertidos!r}",
                      cardinalidad_observada=observada, sede_resuelta=ruta_sede)
    if causa:
        return _falla("conversion_fallida", causa,
                      f"colapso no declarado: {cardinalidad.get('colapso')!r}",
                      cardinalidad_observada=observada, sede_resuelta=ruta_sede)
    return Resultado(valor=valor, cardinalidad_observada=observada, sede_resuelta=ruta_sede)


# --- El recorrido de las hojas, derivado del schema --------------------------------------------


def _slug(titulo: str) -> str:
    """El fragmento con el que un ancla nombra un encabezado. Se apoya en la normalización
    portada —minúsculas, sin diacríticos, sin backticks— y colapsa el resto en guiones."""
    return re.sub(r"[^a-z0-9]+", "-", _titulo_normalizado(titulo)).strip("-")


# ---------------------------------------------------------------------------------------------
# Modos `--recetas`, `--autotest-recetas` y `--autotest-procedencia-portada`.
#
# AC-34 nace de una medición: la mayoría de las anclas de la matriz **no permiten derivar el
# comando**. Una cohorte que se ejecuta «siguiendo la skill» no es repetible — dos operadores leen
# la misma sección y corren cosas distintas—, así que cada punto necesita una receta congelada.
#
# Lo que hace que la receta no sea una transcripción con otro nombre es la **derivación**: cada una
# declara de dónde salió, con una procedencia tipada que se ejecuta contra la sede, o con una
# adjudicación humana explícita cuando esa derivación no existe. Las dos son aceptables; lo que no
# lo es es un comando sin origen declarado, que es indistinguible de uno inventado.
#
# La adjudicación **no** dice que el comando no exista: dice que no se pudo derivar. El comando se
# escribe igual —el runner lo necesita— y queda marcado, con la condición que obligaría a revisarlo.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_RECETAS = DIR_SCRIPTS / "fixtures-baseline" / "recetas"
RUTA_MANIFEST_RECETAS = DIR_FIXTURES_RECETAS / "manifest.json"
NOMBRE_SEDE_SINTETICA = "sede-sintetica.md"
DIR_FIXTURES_PROCEDENCIA = DIR_SCRIPTS / "fixtures-baseline" / "procedencia"
RUTA_MANIFEST_PROCEDENCIA = DIR_FIXTURES_PROCEDENCIA / "manifest.json"

# Los seis campos que AC-34 exige por receta, más el que depende del transporte. Se enumeran acá
# porque son la cláusula literal del criterio; que falte uno no es un detalle de forma.
CAMPOS_DE_RECETA = ("entrada_congelada", "adaptador", "directorio_de_trabajo",
                    "variables_admitidas", "salida_esperada", "derivacion")

# Qué invocación lleva cada transporte, y con qué adaptador se ejecuta. Un punto de subagente con
# `comando` sería indistinguible de uno CLI, y el preflight probaría un binario que no usa.
INVOCACION_POR_TRANSPORTE = {
    "subagent": ("accion", "sesion_de_agente"),
    "cli-exec": ("comando", "script"),
    "cli-resume": ("comando", "script"),
    "mixto": ("comando", "script"),
}


def _recetas_por_id(recetas: list[dict]) -> dict[str, dict]:
    return {r.get("receta_id"): r for r in recetas}


def revisar_recetas(recetas: list[dict], matriz: dict) -> list[str]:
    """Las recetas contra la matriz y contra AC-34. En las dos direcciones: un punto sin receta deja
    la cohorte sin ejecutar ese caso, y una receta sin punto mide algo que la matriz no indexa."""
    problemas: list[str] = []
    puntos = {p.get("id"): p for p in matriz.get("puntos") or []}
    por_punto: dict[str, list[str]] = {}
    for receta in recetas:
        por_punto.setdefault(receta.get("punto_de_despacho"), []).append(receta.get("receta_id"))

    for punto_id in sorted(set(puntos) - set(por_punto)):
        problemas.append(f"el punto «{punto_id}» no tiene receta: la cohorte no lo puede ejecutar")
    for punto_id in sorted(set(por_punto) - set(puntos)):
        problemas.append(f"la receta de «{punto_id}» apunta a un punto que la matriz no indexa")
    for punto_id, ids in sorted(por_punto.items()):
        if len(ids) > 1:
            problemas.append(f"el punto «{punto_id}» tiene {len(ids)} recetas: {sorted(ids)}")

    vistos: set[str] = set()
    for receta in recetas:
        rid = receta.get("receta_id")
        if not isinstance(rid, str) or not rid:
            problemas.append("hay una receta sin `receta_id`")
            continue
        if rid in vistos:
            problemas.append(f"«{rid}» está declarada dos veces")
        vistos.add(rid)
        for campo in CAMPOS_DE_RECETA:
            if not receta.get(campo):
                problemas.append(f"«{rid}» no declara `{campo}`, que AC-34 exige")

        punto = puntos.get(receta.get("punto_de_despacho")) or {}
        transporte = receta.get("transporte")
        if punto and transporte != punto.get("transporte_agregado"):
            problemas.append(f"«{rid}» declara transporte «{transporte}» y la matriz dice "
                             f"«{punto.get('transporte_agregado')}»")
        esperado = INVOCACION_POR_TRANSPORTE.get(transporte)
        if esperado is None:
            problemas.append(f"«{rid}» declara un transporte que no está en la matriz: "
                             f"{transporte!r}")
            continue
        invocacion, adaptador = esperado
        otra = "accion" if invocacion == "comando" else "comando"
        if not receta.get(invocacion):
            problemas.append(f"«{rid}» es «{transporte}» y no declara `{invocacion}`")
        if receta.get(otra):
            problemas.append(f"«{rid}» es «{transporte}» y declara `{otra}`, que no le corresponde")
        if receta.get("adaptador") != adaptador:
            problemas.append(f"«{rid}» es «{transporte}» y su adaptador debería ser «{adaptador}», "
                             f"no «{receta.get('adaptador')}»")
    problemas += revisar_escenarios(recetas)
    return problemas


def revisar_escenarios(recetas: list[dict]) -> list[str]:
    """Los pasos encadenados (D-17). Lo que se congela es la **regla de enlace**, no el valor: el
    `session_id` que el paso dependiente consume no existe cuando la cohorte se congela, y
    escribirlo sería congelar un valor futuro — o, peor, uno de otra corrida."""
    problemas: list[str] = []
    por_id = _recetas_por_id(recetas)
    for receta in recetas:
        escenario = receta.get("escenario")
        if not isinstance(escenario, dict):
            continue
        rid = receta.get("receta_id")
        depende_de = escenario.get("depende_de")
        enlace = escenario.get("regla_de_enlace")
        if depende_de is None:
            if enlace is not None:
                problemas.append(f"«{rid}» no depende de nadie y declara una regla de enlace")
            if not escenario.get("produce"):
                problemas.append(f"«{rid}» es el paso inicial de un escenario y no declara qué "
                                 "produce para el que depende de él")
            continue
        if depende_de not in por_id:
            problemas.append(f"«{rid}» depende de «{depende_de}», que no es una receta")
            continue
        if not isinstance(enlace, dict):
            problemas.append(f"«{rid}» depende de «{depende_de}» y no declara `regla_de_enlace`: "
                             "sin ella el paso se ejecutaría aislado, sobre una sesión fresca o "
                             "ajena")
            continue
        if not enlace.get("entrada") or not isinstance(enlace.get("sale_de"), dict):
            problemas.append(f"«{rid}»: la regla de enlace no dice qué entrada sale de qué salida")
            continue
        origen = enlace["sale_de"]
        if origen.get("receta_id") != depende_de:
            problemas.append(f"«{rid}»: la regla de enlace sale de «{origen.get('receta_id')}» y la "
                             f"dependencia declarada es «{depende_de}»")
        producidas = {p.get("nombre") for p in
                      (por_id[depende_de].get("escenario") or {}).get("produce") or []}
        if origen.get("salida") not in producidas:
            problemas.append(f"«{rid}»: la regla de enlace consume «{origen.get('salida')}» y "
                             f"«{depende_de}» no declara producirla ({sorted(producidas)})")
        if "valor" in enlace or "valor" in origen:
            problemas.append(f"«{rid}»: la regla de enlace congela un VALOR. El identificador de "
                             "sesión no existe cuando la cohorte se congela: lo que se congela es "
                             "la regla, no su resultado futuro")
        if not enlace.get("negativos"):
            problemas.append(f"«{rid}»: la regla de enlace no declara sus negativos —sesión "
                             "ausente, ajena, reutilizada—, que son lo que el preflight prueba")
    return problemas


def revisar_derivacion(recetas: list[dict], raiz: Path) -> tuple[list[str], dict[str, str]]:
    """Cada receta contra su origen declarado, EJECUTÁNDOLO. Devuelve los problemas y cómo quedó
    clasificada cada una.

    Una derivación tipada que no resuelve —cero nodos, o más de uno— es un problema y no una
    adjudicación implícita: el punto de AC-34 es que la ambigüedad se declare, no que se resuelva
    eligiendo el primero."""
    problemas: list[str] = []
    clasificacion: dict[str, str] = {}
    for receta in recetas:
        rid = receta.get("receta_id")
        derivacion = receta.get("derivacion")
        if not isinstance(derivacion, dict):
            problemas.append(f"«{rid}» no declara `derivacion`: un comando sin origen declarado no "
                             "se distingue de uno inventado")
            continue
        tipo = derivacion.get("tipo")
        if tipo == "adjudicacion_humana":
            clasificacion[rid] = "adjudicada"
            if not derivacion.get("motivo"):
                problemas.append(f"«{rid}» se adjudica a mano y no dice por qué no se pudo derivar")
            if not derivacion.get("adjudicado_por"):
                problemas.append(f"«{rid}» se adjudica a mano y no dice quién la adjudicó")
            continue
        if tipo != "extraccion_tipada":
            problemas.append(f"«{rid}» declara una derivación de tipo desconocido: {tipo!r}")
            continue
        clasificacion[rid] = "derivada"
        procedencia = derivacion.get("procedencia")
        if not isinstance(procedencia, dict) or "ausencia" in procedencia:
            problemas.append(f"«{rid}» dice derivarse y no trae una procedencia anclada que "
                             "ejecutar")
            continue
        resultado = resolver_procedencia(procedencia, raiz)
        if not resultado.ok:
            problemas.append(f"«{rid}» no resuelve contra su sede: {resultado.error} "
                             f"({resultado.causa}) — {resultado.detalle}")
    return problemas, clasificacion


def _insumos_de_recetas() -> tuple[dict, dict, list[str]]:
    problemas: list[str] = []
    recetas, error = _cargar_json(RUTA_RECETAS)
    if error:
        problemas.append(f"recetas de la cohorte: {error}")
    matriz, error = _cargar_json(RUTA_MATRIZ)
    if error:
        problemas.append(f"matriz de despachos: {error}")
    return recetas or {}, matriz or {}, problemas


def modo_recetas(args: argparse.Namespace) -> int:
    del args
    documento, matriz, problemas = _insumos_de_recetas()
    if problemas:
        for p in problemas:
            print(f"FALLA  {p}")
        return 1
    recetas = documento.get("recetas") or []

    problemas = revisar_recetas(recetas, matriz)
    de_derivacion, clasificacion = revisar_derivacion(recetas, RAIZ)
    for receta in recetas:
        rid = receta.get("receta_id")
        marca = {"derivada": "deriv", "adjudicada": "adjud"}.get(clasificacion.get(rid), "  ?  ")
        invocacion = "comando" if receta.get("comando") else "accion"
        print(f"{marca}  {rid:32} {receta.get('transporte',''):11} {invocacion}")
    print()
    derivadas = sum(1 for v in clasificacion.values() if v == "derivada")
    adjudicadas = sum(1 for v in clasificacion.values() if v == "adjudicada")
    print(f"{len(recetas)} recetas · {derivadas} derivadas del ancla · {adjudicadas} adjudicadas")
    todos = problemas + de_derivacion
    if todos:
        for p in todos[:12]:
            print(f"FALLA  {p}")
        print()
        print(f"RESULTADO: FALLA — {len(todos)} problemas")
        return 1
    print()
    print(f"RESULTADO: OK — {len(recetas)} recetas ejecutables contra los "
          f"{len(matriz.get('puntos') or [])} puntos de la matriz")
    return 0


@contextlib.contextmanager
def _raiz_con_sede_sintetica(manifest: dict):
    """Una raíz temporal con la sede sintética del corpus copiada dentro, con nombre propio.

    Hace falta porque la sede vive bajo `scripts/fixtures-baseline/`, y el resolutor —con razón—
    rechaza como sede cualquier artefacto de este flujo: una hoja que se cita a sí misma coincide
    siempre consigo misma. Copiarla afuera es lo que permite ejercer los dos extremos de AC-34
    sin desactivar esa precondición ni editar una skill real."""
    origen = DIR_FIXTURES_RECETAS / "sedes" / NOMBRE_SEDE_SINTETICA
    with tempfile.TemporaryDirectory() as temporal:
        raiz = Path(temporal)
        (raiz / NOMBRE_SEDE_SINTETICA).write_text(origen.read_text(encoding="utf-8"),
                                                  encoding="utf-8")
        yield raiz

class AtaqueALaReceta(NamedTuple):
    """Un ataque al documento de recetas, con el motivo por el que tiene que caer. Sin el motivo, un
    ataque detectado por otra cláusula deja la suya sin ejercer."""
    nombre: str
    que_rompe: str
    motivo_esperado: str
    aplicar: Callable[[list[dict]], bool]


def _ar_borrar_una(recetas: list[dict]) -> bool:
    recetas.pop()
    return True


def _ar_campo_ausente(recetas: list[dict]) -> bool:
    recetas[0].pop("salida_esperada", None)
    return True


def _ar_comando_en_subagente(recetas: list[dict]) -> bool:
    for receta in recetas:
        if receta.get("transporte") == "subagent":
            receta["comando"] = "codex exec -s read-only -"
            return True
    return False


def _ar_transporte_cambiado(recetas: list[dict]) -> bool:
    for receta in recetas:
        if receta.get("transporte") == "cli-exec":
            receta["transporte"] = "subagent"
            return True
    return False


def _ar_enlace_borrado(recetas: list[dict]) -> bool:
    for receta in recetas:
        escenario = receta.get("escenario") or {}
        if escenario.get("depende_de"):
            escenario.pop("regla_de_enlace")
            return True
    return False


def _ar_enlace_con_valor(recetas: list[dict]) -> bool:
    """El defecto que D-17 existe para impedir: congelar el `session_id` en vez de la regla."""
    for receta in recetas:
        enlace = (receta.get("escenario") or {}).get("regla_de_enlace")
        if isinstance(enlace, dict):
            enlace["valor"] = "01JQZ-sesion-de-otra-corrida"
            return True
    return False


def _ar_dependencia_inventada(recetas: list[dict]) -> bool:
    for receta in recetas:
        escenario = receta.get("escenario") or {}
        if escenario.get("depende_de"):
            escenario["depende_de"] = "rec-que-no-existe"
            return True
    return False


def _ar_produce_desalineado(recetas: list[dict]) -> bool:
    """El paso inicial deja de producir lo que el dependiente consume: los dos siguen declarando su
    escenario y la cadena ya no cierra."""
    for receta in recetas:
        producciones = (receta.get("escenario") or {}).get("produce")
        if producciones:
            producciones[0]["nombre"] = "otra-cosa"
            return True
    return False


ATAQUES_A_LAS_RECETAS: tuple[AtaqueALaReceta, ...] = (
    AtaqueALaReceta("receta-faltante", "un punto de la matriz se queda sin receta",
                    "no tiene receta", _ar_borrar_una),
    AtaqueALaReceta("campo-ausente", "una receta pierde un campo que AC-34 exige",
                    "no declara `salida_esperada`", _ar_campo_ausente),
    AtaqueALaReceta("comando-en-subagente", "un punto de subagente declara un comando",
                    "declara `comando`, que no le corresponde", _ar_comando_en_subagente),
    AtaqueALaReceta("transporte-cambiado", "el transporte deja de coincidir con la matriz",
                    "y la matriz dice", _ar_transporte_cambiado),
    AtaqueALaReceta("enlace-borrado", "el paso dependiente se queda sin regla de enlace",
                    "no declara `regla_de_enlace`", _ar_enlace_borrado),
    AtaqueALaReceta("enlace-con-valor", "la regla de enlace congela el identificador de sesión",
                    "congela un VALOR", _ar_enlace_con_valor),
    AtaqueALaReceta("dependencia-inventada", "el paso depende de una receta que no existe",
                    "que no es una receta", _ar_dependencia_inventada),
    AtaqueALaReceta("produce-desalineado", "el paso inicial deja de producir lo que el otro consume",
                    "no declara producirla", _ar_produce_desalineado),
)


class AtaqueALaDerivacion(NamedTuple):
    """`sede_sintetica` marca los dos ataques que no se pueden montar sobre el árbol real: una
    skill con dos invocaciones idénticas —o sin ninguna— sería un cambio al repositorio. Esos se
    resuelven contra una raíz aparte, donde la sede del corpus se copia con nombre propio: bajo
    `scripts/fixtures-baseline/` el resolutor la rechaza, y con razón — es un artefacto de este
    flujo, y una hoja que se cita a sí misma coincide siempre consigo misma."""
    nombre: str
    que_rompe: str
    motivo_esperado: str
    aplicar: Callable[[list[dict], dict], bool]
    sede_sintetica: bool = False


def _ad_sin_derivacion(recetas: list[dict], manifest: dict) -> bool:
    del manifest
    recetas[0].pop("derivacion", None)
    return True


def _ad_adjudicacion_sin_motivo(recetas: list[dict], manifest: dict) -> bool:
    del manifest
    for receta in recetas:
        derivacion = receta.get("derivacion") or {}
        if derivacion.get("tipo") == "adjudicacion_humana":
            derivacion.pop("motivo")
            return True
    return False


def _ad_tipo_desconocido(recetas: list[dict], manifest: dict) -> bool:
    del manifest
    (recetas[0].get("derivacion") or {})["tipo"] = "de_memoria"
    return True


def _ad_cero_resultados(recetas: list[dict], manifest: dict) -> bool:
    """El selector deja de casar: la derivación no resuelve y NO se degrada a adjudicación."""
    sede = manifest.get("sede_sintetica") or {}
    for receta in recetas:
        derivacion = receta.get("derivacion") or {}
        if derivacion.get("tipo") == "extraccion_tipada":
            derivacion["procedencia"] = {
                **derivacion["procedencia"], "sede": NOMBRE_SEDE_SINTETICA,
                "tipo_de_sede": "patron_de_linea",
                "selector": {"patron": sede.get("patron_sin_coincidencia")},
                "cardinalidad": {"tipo": "exactamente_una"},
                "extraccion": {"tipo": "literal"}}
            return True
    return False


def _ad_multiples_resultados(recetas: list[dict], manifest: dict) -> bool:
    """El selector casa dos invocaciones legítimas de puntos distintos. Devolver «la primera» daría
    un comando plausible y falso; la cardinalidad es lo que lo impide."""
    sede = manifest.get("sede_sintetica") or {}
    for receta in recetas:
        derivacion = receta.get("derivacion") or {}
        if derivacion.get("tipo") == "extraccion_tipada":
            derivacion["procedencia"] = {
                **derivacion["procedencia"], "sede": NOMBRE_SEDE_SINTETICA,
                "tipo_de_sede": "patron_de_linea",
                "selector": {"patron": sede.get("patron_ambiguo")},
                "cardinalidad": {"tipo": "exactamente_una"},
                "extraccion": {"tipo": "literal"}}
            return True
    return False


ATAQUES_A_LA_DERIVACION: tuple[AtaqueALaDerivacion, ...] = (
    AtaqueALaDerivacion("sin-derivacion", "una receta no declara de dónde salió su comando",
                        "no declara `derivacion`", _ad_sin_derivacion),
    AtaqueALaDerivacion("adjudicacion-sin-motivo", "se adjudica a mano sin decir por qué",
                        "no dice por qué no se pudo derivar", _ad_adjudicacion_sin_motivo),
    AtaqueALaDerivacion("tipo-desconocido", "la derivación declara un tipo que nadie implementa",
                        "tipo desconocido", _ad_tipo_desconocido),
    AtaqueALaDerivacion("cero-resultados", "el selector no casa nada en su sede",
                        "selector_sin_resultado", _ad_cero_resultados, sede_sintetica=True),
    AtaqueALaDerivacion("multiples-resultados", "el selector casa dos invocaciones distintas",
                        "cardinalidad_no_coincide", _ad_multiples_resultados,
                        sede_sintetica=True),
)


def modo_autotest_recetas(args: argparse.Namespace) -> int:
    documento, matriz, problemas = _insumos_de_recetas()
    manifest, error = _cargar_json(RUTA_MANIFEST_RECETAS)
    if error:
        problemas.append(f"manifest del corpus de recetas: {error}")
    if problemas:
        for p in problemas:
            print(f"[A] FALLA  {p}")
        return 1
    recetas = documento.get("recetas") or []
    solo_derivacion = bool(getattr(args, "derivacion", False))
    resultados: list[tuple[str, bool, str]] = []

    if not solo_derivacion:
        # [A] El positivo: las trece reales pasan enteras.
        fallas = revisar_recetas(recetas, matriz)
        resultados.append(("A", not fallas,
                           f"las {len(recetas)} recetas contra los "
                           f"{len(matriz.get('puntos') or [])} puntos de la matriz"
                           if not fallas else " | ".join(fallas[:4])))

        # [B] Los ataques al documento, cada uno por SU motivo.
        fallas = []
        for ataque in ATAQUES_A_LAS_RECETAS:
            copia = copy.deepcopy(recetas)
            if not ataque.aplicar(copia):
                fallas.append(f"«{ataque.nombre}»: la mutación no se pudo aplicar")
                continue
            detectados = revisar_recetas(copia, matriz)
            if not any(ataque.motivo_esperado in d for d in detectados):
                fallas.append(f"«{ataque.nombre}»: {ataque.que_rompe} y no cae por "
                              f"«{ataque.motivo_esperado}» — se vio: "
                              f"{detectados[0] if detectados else 'nada'}")
        resultados.append(("B", not fallas,
                           f"los {len(ATAQUES_A_LAS_RECETAS)} ataques al documento caen por su "
                           "motivo" if not fallas else " | ".join(fallas[:4])))

        # [C] El escenario encadenado, contra el manifest INDEPENDIENTE: sus pasos existen, están en
        # el orden declarado y el enlace es el que el manifest dice.
        fallas = []
        por_id = _recetas_por_id(recetas)
        for esperado in manifest.get("escenarios_esperados") or []:
            pasos = esperado.get("pasos") or []
            ausentes = [p for p in pasos if p not in por_id]
            if ausentes:
                fallas.append(f"«{esperado.get('escenario_id')}»: faltan los pasos {ausentes}")
                continue
            del_escenario = [r.get("receta_id") for r in recetas
                             if (r.get("escenario") or {}).get("escenario_id")
                             == esperado.get("escenario_id")]
            if sorted(del_escenario) != sorted(pasos):
                fallas.append(f"«{esperado.get('escenario_id')}»: el manifest declara {sorted(pasos)}"
                              f" y las recetas dicen {sorted(del_escenario)}")
                continue
            dependiente = next((p for p in pasos
                                if (por_id[p].get("escenario") or {}).get("depende_de")), None)
            enlace = (por_id[dependiente].get("escenario") or {}).get("regla_de_enlace") or {}
            if enlace.get("entrada", "").lower() != (esperado.get("enlace") or "").lower():
                fallas.append(f"«{esperado.get('escenario_id')}»: el manifest declara que el enlace "
                              f"es «{esperado.get('enlace')}» y la receta enlaza por "
                              f"«{enlace.get('entrada')}»")
        resultados.append(("C", not fallas,
                           f"{len(manifest.get('escenarios_esperados') or [])} escenario encadenado "
                           "contra el manifest independiente" if not fallas
                           else " | ".join(fallas[:4])))

    # [D/A'] La derivación real de cada receta, EJECUTADA, y su clasificación contra el manifest.
    de_derivacion, clasificacion = revisar_derivacion(recetas, RAIZ)
    esperada = manifest.get("clasificacion_esperada") or {}
    fallas = list(de_derivacion)
    for rid in sorted(set(esperada) | set(clasificacion)):
        if esperada.get(rid) != clasificacion.get(rid):
            fallas.append(f"«{rid}»: el manifest la declara {esperada.get(rid)!r} y quedó "
                          f"{clasificacion.get(rid)!r}")
    etiqueta = "A" if solo_derivacion else "D"
    derivadas = sum(1 for v in clasificacion.values() if v == "derivada")
    resultados.append((etiqueta, not fallas,
                       f"{derivadas} derivaciones resueltas contra su sede y "
                       f"{len(clasificacion) - derivadas} adjudicadas, contra el manifest"
                       if not fallas else " | ".join(fallas[:4])))

    if solo_derivacion:
        # [B'] Los ataques a la derivación, cada uno por su motivo. Los dos últimos son las dos
        # formas que AC-34 nombra: cero resultados y múltiples.
        fallas = []
        for ataque in ATAQUES_A_LA_DERIVACION:
            copia = copy.deepcopy(recetas)
            if not ataque.aplicar(copia, manifest):
                fallas.append(f"«{ataque.nombre}»: la mutación no se pudo aplicar")
                continue
            if ataque.sede_sintetica:
                # Solo la receta mutada, y contra la raíz aparte: evaluarlas todas ahí sumaría doce
                # sedes inexistentes, y el ataque caería por su motivo entre doce falsos.
                mutadas = [r for r in copia
                           if ((r.get("derivacion") or {}).get("procedencia") or {}).get("sede")
                           == NOMBRE_SEDE_SINTETICA]
                if len(mutadas) != 1:
                    fallas.append(f"«{ataque.nombre}»: la mutación tocó {len(mutadas)} recetas y "
                                  "tiene que tocar una")
                    continue
                with _raiz_con_sede_sintetica(manifest) as raiz:
                    detectados, _ = revisar_derivacion(mutadas, raiz)
            else:
                detectados, _ = revisar_derivacion(copia, RAIZ)
            if not any(ataque.motivo_esperado in d for d in detectados):
                fallas.append(f"«{ataque.nombre}»: {ataque.que_rompe} y no cae por "
                              f"«{ataque.motivo_esperado}» — se vio: "
                              f"{detectados[0] if detectados else 'nada'}")
        resultados.append(("B", not fallas,
                           f"los {len(ATAQUES_A_LA_DERIVACION)} ataques a la derivación caen por su "
                           "motivo" if not fallas else " | ".join(fallas[:4])))

        # [C'] La sede sintética resuelve como el manifest declara: uno con el patrón único y dos
        # con el ambiguo. Es el control POSITIVO de los dos ataques anteriores: sin él, un motor que
        # fallara siempre los pasaría a los dos.
        sede = manifest.get("sede_sintetica") or {}
        fallas = []
        base = {"sede": NOMBRE_SEDE_SINTETICA, "tipo_de_sede": "patron_de_linea",
                "extraccion": {"tipo": "literal"}, "normalizacion": "trim", "conversion": "cadena"}
        with _raiz_con_sede_sintetica(manifest) as raiz:
            uno = resolver_procedencia({**base, "selector": {"patron": sede.get("patron_unico")},
                                        "cardinalidad": {"tipo": "exactamente_una"}}, raiz)
            dos = resolver_procedencia({**base, "selector": {"patron": sede.get("patron_ambiguo")},
                                        "cardinalidad": {"tipo": "exactamente_n",
                                                         "n": sede.get("nodos_del_ambiguo"),
                                                         "colapso": "lista", "orden": "documento"}},
                                       raiz)
        if not uno.ok:
            fallas.append(f"el patrón único no resuelve: {uno.error} ({uno.causa})")
        if not dos.ok:
            fallas.append(f"el patrón ambiguo no resuelve a {sede.get('nodos_del_ambiguo')}: "
                          f"{dos.error} ({dos.causa})")
        elif dos.cardinalidad_observada != sede.get("nodos_del_ambiguo"):
            fallas.append(f"el patrón ambiguo devolvió {dos.cardinalidad_observada} nodos y el "
                          f"manifest declara {sede.get('nodos_del_ambiguo')}")
        resultados.append(("C", not fallas,
                           "la sede sintética resuelve a uno y a dos como el manifest declara"
                           if not fallas else " | ".join(fallas[:4])))

    return _cerrar(resultados)

def dimensiones_de(procedencia: dict) -> dict[str, str | None]:
    """Las piezas del motor que una procedencia ejerce. Es la unidad de la frontera declarada: por
    dimensión y no por combinación, porque las trece recetas usan dos combinaciones y declarar la
    frontera así dejaría afuera a cualquier receta nueva."""
    cardinalidad = procedencia.get("cardinalidad") or {}
    return {
        "tipo_de_sede": procedencia.get("tipo_de_sede"),
        "cardinalidad": cardinalidad.get("tipo"),
        "extraccion": (procedencia.get("extraccion") or {}).get("tipo"),
        "normalizacion": procedencia.get("normalizacion"),
        "conversion": procedencia.get("conversion"),
        "colapso": cardinalidad.get("colapso"),
        "orden": cardinalidad.get("orden"),
    }


def modo_autotest_procedencia_portada(args: argparse.Namespace) -> int:
    del args
    problemas: list[str] = []
    corpus, error = _cargar_json(DIR_FIXTURES_PROCEDENCIA / "corpus.json")
    if error:
        problemas.append(f"corpus diferencial: {error}")
    manifest, error = _cargar_json(RUTA_MANIFEST_PROCEDENCIA)
    if error:
        problemas.append(f"manifest del corpus diferencial: {error}")
    documento, _, mas = _insumos_de_recetas()
    if problemas + mas:
        for p in problemas + mas:
            print(f"[A] FALLA  {p}")
        return 1

    casos = corpus.get("casos") or []
    resultados: list[tuple[str, bool, str]] = []

    # [A] Las dimensiones declaradas ↔ las que el corpus ejerce, en las dos direcciones. Una
    # declarada sin caso es frontera que nadie ejerce; una ejercida sin declarar es la frontera
    # creciendo sin que nadie lo decida.
    declaradas = {k: set(v) for k, v in (manifest.get("dimensiones_cubiertas") or {}).items()}
    ejercidas: dict[str, set] = {}
    for caso in casos:
        for dimension, valor in dimensiones_de(caso.get("procedencia") or {}).items():
            if valor is not None:
                ejercidas.setdefault(dimension, set()).add(valor)
    fallas: list[str] = []
    for dimension in sorted(set(declaradas) | set(ejercidas)):
        faltan = sorted(declaradas.get(dimension, set()) - ejercidas.get(dimension, set()))
        sobran = sorted(ejercidas.get(dimension, set()) - declaradas.get(dimension, set()))
        fallas += [f"{dimension}: «{v}» está declarada y ningún caso la ejerce" for v in faltan]
        fallas += [f"{dimension}: «{v}» la ejerce un caso y el manifest no la declara"
                   for v in sobran]
    resultados.append(("A", not fallas,
                       f"{sum(len(v) for v in declaradas.values())} valores de dimensión "
                       f"declarados ↔ ejercidos por los {len(casos)} casos"
                       if not fallas else " | ".join(fallas[:4])))

    # [B] La cobertura que importa: cada dimensión que usan las TRECE RECETAS está dentro de la
    # frontera. Es la dirección que convierte al corpus en una protección y no en una colección.
    fallas = []
    for receta in documento.get("recetas") or []:
        procedencia = (receta.get("derivacion") or {}).get("procedencia")
        if not isinstance(procedencia, dict) or "ausencia" in procedencia:
            continue
        for dimension, valor in dimensiones_de(procedencia).items():
            if valor is not None and valor not in declaradas.get(dimension, set()):
                fallas.append(f"«{receta.get('receta_id')}» usa {dimension}=«{valor}», que la "
                              "frontera declarada no cubre: ahí el motor portado puede divergir "
                              "sin que nada lo note")
    resultados.append(("B", not fallas,
                       "las trece recetas usan solo dimensiones que la frontera cubre"
                       if not fallas else " | ".join(sorted(set(fallas))[:4])))

    # [C] El control diferencial: el motor PORTADO reproduce cada salida congelada, que produjo el
    # ORIGINAL. Es lo único que compara los dos motores; el resto compara al portado consigo mismo.
    divergencias = corpus.get("divergencias_declaradas") or []
    fallas = []
    with _raiz_con_sede_del_corpus(corpus) as raiz:
        for caso, contra, donde in ([(c, "el original", raiz) for c in casos]
                                    + [(c, "el port", RAIZ) for c in divergencias]):
            esperado = caso.get("esperado") or {}
            obtenido = resolver_procedencia(caso.get("procedencia") or {}, donde)
            visto = {"valor": obtenido.valor,
                     "cardinalidad_observada": obtenido.cardinalidad_observada,
                     "error": obtenido.error, "causa": obtenido.causa}
            # Los campos salen de las CLAVES del esperado, no de una lista escrita acá: una lista
            # se puede acortar y el corpus seguiría en verde comparando de menos.
            if set(esperado) - set(visto):
                fallas.append(f"«{caso.get('caso_id')}»: el esperado declara campos que el "
                              f"resolutor no devuelve: {sorted(set(esperado) - set(visto))}")
                continue
            if set(visto) - set(esperado):
                fallas.append(f"«{caso.get('caso_id')}»: el resolutor devuelve "
                              f"{sorted(set(visto) - set(esperado))} y el esperado no lo congela")
                continue
            for campo, valor in sorted(esperado.items()):
                if not _mismo(visto[campo], valor):
                    fallas.append(f"«{caso.get('caso_id')}»: {campo} congelado por {contra} es "
                                  f"{valor!r} y el portado da {visto[campo]!r}")
    resultados.append(("C", not fallas,
                       f"los {len(casos)} casos reproducen la salida que congeló el motor original, "
                       f"y {len(divergencias)} divergencia declarada la del port"
                       if not fallas else " | ".join(fallas[:4])))

    # [D] Las causas de fallo, ejercidas. Un motor que resolviera todo bien y nunca fallara pasaría
    # [C] entero si el corpus fuera solo de positivos.
    ejercidos = {c["esperado"].get("error") for c in casos if (c.get("esperado") or {}).get("error")}
    declarados = set(manifest.get("errores_ejercidos") or [])
    en_otro_lado = set(manifest.get("error_no_ejercido_aca") or {})
    fallas = [f"«{e}» está declarado ejercido y ningún caso lo produce" for e in
              sorted(declarados - ejercidos)]
    fallas += [f"«{e}» lo produce un caso y el manifest no lo declara" for e in
               sorted(ejercidos - declarados)]
    fallas += [f"«{e}» de ERRORES_DE_RESOLUCION no lo ejerce nadie ni se declara dónde se ejerce"
               for e in sorted(set(ERRORES_DE_RESOLUCION) - ejercidos - en_otro_lado)]
    resultados.append(("D", not fallas,
                       f"las {len(ERRORES_DE_RESOLUCION)} causas de fallo del resolutor, ejercidas "
                       f"acá ({len(ejercidos)}) o declaradas dónde ({len(en_otro_lado)})"
                       if not fallas else " | ".join(fallas[:4])))

    return _cerrar(resultados)


@contextlib.contextmanager
def _raiz_con_sede_del_corpus(corpus: dict):
    """Igual que la del corpus de recetas: la sede se copia a una raíz temporal porque bajo
    `scripts/fixtures-baseline/` el resolutor la rechaza por ser un artefacto de este flujo."""
    nombre = corpus.get("sede")
    origen = DIR_FIXTURES_PROCEDENCIA / "sedes" / nombre
    with tempfile.TemporaryDirectory() as temporal:
        raiz = Path(temporal)
        (raiz / nombre).write_text(origen.read_text(encoding="utf-8"), encoding="utf-8")
        yield raiz

# ---------------------------------------------------------------------------------------------
# Modos `--aislamiento`, `--autotest-aislamiento`, `--autotest-egreso` y `--autotest-recursos`.
#
# Este es el modo que **juzga** la evidencia de aislamiento. Producirla es otra capacidad y vive en
# el runner: acá no se provisiona nada, se decide si lo capturado alcanza.
#
# No se registra ninguna comprobación en `COMPROBACIONES_DE_BUNDLES` a propósito. Esas cláusulas
# corren sobre **todo** conjunto que pase por `--validar-bundles`, incluidos los corpus que las
# tasks anteriores escribieron para probar otra cosa: exigirles ahora un inventario de egreso
# re-ejecutado los pondría rojos por una regla que no existía cuando se congelaron. El juicio de
# aislamiento tiene su modo y su corpus, que es lo que sus tres filas del contrato invocan.
# ---------------------------------------------------------------------------------------------

RUTA_SUPERFICIES = DIR_SCRIPTS / "superficies-de-egreso.json"
DIR_FIXTURES_AISLAMIENTO = DIR_SCRIPTS / "fixtures-baseline" / "aislamiento"
RUTA_MANIFEST_AISLAMIENTO = DIR_FIXTURES_AISLAMIENTO / "manifest.json"
RUTA_CORPUS_AISLAMIENTO = DIR_FIXTURES_AISLAMIENTO / "bundles.json"

# Las tres pruebas son tres y se exigen por separado (decisión heredada 6): una sola prueba
# «de aislamiento» dejaría que la que pasa cubra a la que nadie corrió.
PRUEBAS_DE_AISLAMIENTO = (
    "refs_y_objetos_identicos",
    "sin_red_ni_credenciales",
    "arbol_original_intacto",
)


class ProblemaDeAislamiento(NamedTuple):
    clave: str
    detalle: str

    def __str__(self) -> str:
        return f"[{self.clave}] {self.detalle}"


# Las cláusulas del juicio. Como en el resto del archivo, el conjunto es cerrado y cada una tiene
# que tener quien la ponga roja: una cláusula sin caso que la ejerza es una cláusula que nadie
# probó que pueda fallar.
# Las cláusulas son disjuntas a propósito. Una que se solape con otra deja que un caso «cubierto»
# esté cayendo por la de al lado, y la suya sin ejercer.
CLAUSULAS_DE_AISLAMIENTO = (
    "prueba_faltante",
    "permiso_falseado",
    "prueba_fallida",
    "evidencia_declarativa",
    "evidencia_repetida",
)

CLAUSULAS_DE_RECURSOS = (
    "sin_recursos",
    "transferido_sin_owner",
    "transferido_sin_next_action",
    "vivo_sin_transferir",
    "cese_inferido_del_arbol",
    "evidencia_de_cese_copiada",
)


def _permiso_efectivo_de(punto: str, matriz: dict) -> str | None:
    for p in matriz.get("puntos") or []:
        if p.get("id") == punto:
            valor = p.get("escritura_agregada")
            valor = valor.get("valor") if isinstance(valor, dict) else valor
            return valor if isinstance(valor, str) else None
    return None


def revisar_aislamiento(bundle: dict, matriz: dict) -> list[ProblemaDeAislamiento]:
    """Las tres pruebas, exigidas según el permiso efectivo que declara **la matriz**.

    El permiso no se lee del bundle: se lee de la matriz y se compara contra lo que el bundle
    declara. Leerlo del bundle dejaría que una corrida se eximiera de las tres pruebas escribiendo
    que es de solo lectura, que es exactamente la vía que el criterio nombra.
    """
    problemas: list[ProblemaDeAislamiento] = []
    punto = bundle.get("punto_de_despacho", "<sin punto>")
    permiso = _permiso_efectivo_de(punto, matriz)
    pruebas = bundle.get("pruebas_de_aislamiento") or {}

    faltan = [c for c in PRUEBAS_DE_AISLAMIENTO if c not in pruebas]
    if faltan:
        problemas.append(ProblemaDeAislamiento(
            "prueba_faltante",
            f"`{punto}`: faltan pruebas de aislamiento: {faltan} — una corrida con menos de las "
            f"tres no sostiene la ausencia de publicación"))
        return problemas

    exentas = [c for c in PRUEBAS_DE_AISLAMIENTO
               if pruebas[c].get("resultado") == "not_applicable"]
    if exentas and permiso != "read_only":
        # Una sola cláusula para la exención indebida: el permiso lo dice la matriz, y que el
        # bundle escriba `read_only` no lo convierte en uno. Partirla en dos dejaría que un caso
        # cayera por las dos y ninguna quedara ejercida sola.
        problemas.append(ProblemaDeAislamiento(
            "permiso_falseado",
            f"`{punto}` se eximió de {exentas} declarando solo lectura, y la matriz dice que su "
            f"permiso efectivo es `{permiso}`: falsear el permiso no exime de las tres pruebas"))
        return problemas

    for clave in PRUEBAS_DE_AISLAMIENTO:
        prueba = pruebas[clave]
        resultado = prueba.get("resultado")
        if resultado == "falla":
            problemas.append(ProblemaDeAislamiento(
                "prueba_fallida",
                f"`{punto}`: la prueba `{clave}` falló — {prueba.get('evidencia')}"))
        elif resultado not in ("pasa", "not_applicable"):
            problemas.append(ProblemaDeAislamiento(
                "prueba_faltante",
                f"`{punto}`: la prueba `{clave}` no declara un resultado del conjunto"))

    if permiso != "read_only" and not problemas:
        problemas.extend(_revisar_evidencia_de_no_publicacion(bundle, punto))

    evidencias = [pruebas[c].get("evidencia") for c in PRUEBAS_DE_AISLAMIENTO
                  if pruebas[c].get("resultado") in ("pasa", "falla")]
    if not problemas and len(evidencias) != len(set(evidencias)):
        problemas.append(ProblemaDeAislamiento(
            "evidencia_repetida",
            f"`{punto}`: dos pruebas citan la misma evidencia — tres pruebas separadas con una "
            f"sola observación son una prueba escrita tres veces"))
    return problemas


def _revisar_evidencia_de_no_publicacion(bundle: dict,
                                         punto: str) -> list[ProblemaDeAislamiento]:
    """Una declaración de no publicación no es evidencia, y eso se comprueba por estructura.

    La prueba de que no hubo red se sostiene sobre el **inventario de egreso re-ejecutado**: si el
    bundle no trae ninguna superficie descubierta, la regla de canales no corrió y lo que hay es una
    afirmación. Detectarlo por el texto de la evidencia sería grep sobre prosa; detectarlo por la
    ausencia del inventario es exacto.
    """
    inventario = bundle.get("inventario_de_egreso_reejecutado") or {}
    superficies = inventario.get("superficies")
    if superficies:
        return []
    return [ProblemaDeAislamiento(
        "evidencia_declarativa",
        f"`{punto}`: la prueba de ausencia de red no trae inventario de egreso re-ejecutado — sin "
        f"él lo que hay es una declaración de no publicación, no una auditoría")]


def revisar_recursos(bundle: dict) -> list[ProblemaDeAislamiento]:
    """Vida y propiedad por separado: la transferencia resuelve quién responde, no si sigue vivo."""
    problemas: list[ProblemaDeAislamiento] = []
    punto = bundle.get("punto_de_despacho", "<sin punto>")
    recursos = bundle.get("recursos") or []
    if not recursos:
        return [ProblemaDeAislamiento(
            "sin_recursos",
            f"`{punto}`: la corrida no declara ningún recurso — un despacho abre al menos uno, y "
            f"no declararlo lo deja vivo y sin dueño sin que nada lo note")]

    evidencias_de_aislamiento = {
        (bundle.get("pruebas_de_aislamiento") or {}).get(c, {}).get("evidencia")
        for c in PRUEBAS_DE_AISLAMIENTO}
    vistas: dict[str, str] = {}

    for recurso in recursos:
        ident = recurso.get("recurso_id", "<sin id>")
        vida = recurso.get("life_state")
        propiedad = recurso.get("ownership_state")
        evidencia = recurso.get("evidencia_de_cese")

        if propiedad == "transferido":
            if not recurso.get("owner"):
                problemas.append(ProblemaDeAislamiento(
                    "transferido_sin_owner",
                    f"`{ident}` está transferido y no declara dueño: la transferencia sin dueño "
                    f"es un abandono con nombre"))
            if not recurso.get("next_action"):
                problemas.append(ProblemaDeAislamiento(
                    "transferido_sin_next_action",
                    f"`{ident}` está transferido y no declara próxima acción: un dueño sin "
                    f"próxima acción es un recurso abandonado con dueño"))
        elif vida != "terminado_comprobado":
            problemas.append(ProblemaDeAislamiento(
                "vivo_sin_transferir",
                f"`{ident}` quedó en `{vida}` y sin transferir: solo un estado terminal "
                f"comprobado cuenta como limpieza, y lo que no cesó necesita dueño"))

        if evidencia in evidencias_de_aislamiento:
            problemas.append(ProblemaDeAislamiento(
                "cese_inferido_del_arbol",
                f"`{ident}` sostiene su cese con la misma observación que una prueba del árbol: "
                f"el cese de un recurso NUNCA se infiere por efectos en el árbol"))
        if evidencia in vistas:
            problemas.append(ProblemaDeAislamiento(
                "evidencia_de_cese_copiada",
                f"`{ident}` y `{vistas[evidencia]}` citan la misma evidencia de cese: una sola "
                f"observación no acredita el cese de dos recursos"))
        elif isinstance(evidencia, str):
            vistas[evidencia] = ident
    return problemas


def modo_aislamiento(args: argparse.Namespace) -> int:
    raiz = _ruta_absoluta(getattr(args, "aislamiento"))
    matriz, error = _cargar_json(RUTA_MATRIZ)
    if error:
        print(f"FALLA  {error}")
        return 1

    bundles = leer_conjunto_de_bundles(raiz)
    print(f"Conjunto: {raiz} — {len(bundles)} corridas")
    if not bundles:
        print()
        print("RESULTADO: FALLA — el conjunto no tiene ninguna corrida que juzgar")
        return 1

    bloqueadas: list[str] = []
    for bundle in bundles:
        datos = bundle.datos or {}
        problemas = revisar_aislamiento(datos, matriz) + revisar_recursos(datos)
        if problemas:
            bloqueadas.append(bundle.directorio)
            print(f"[{bundle.directorio}] BLOQUEADA — {len(problemas)}:")
            for p in problemas[:8]:
                print(f"       - {p}")
        else:
            print(f"[{bundle.directorio}] OK     las tres pruebas y sus recursos sostienen la "
                  f"observación")

    print()
    if bloqueadas:
        print(f"RESULTADO: FALLA — observaciones bloqueadas: {', '.join(bloqueadas)}")
        return 1
    print(f"RESULTADO: OK — las {len(bundles)} observaciones sostienen su aislamiento")
    return 0


# --- El inventario de egreso y sus cuatro mutantes -------------------------------------------
#
# Los mutantes recorren su **adaptador real** y se interceptan en la frontera contra un canary
# local. Un adaptador falso probaría el doble y el harness; permitir la publicación produciría
# justamente lo que el criterio prohíbe. La superficie que no admite redirección segura se prueba
# por **denegación comprobable**, y la que no admite ninguna de las dos bloquea.

class Canary:
    """Destino local que registra lo que le llega, para que nada salga del host.

    Registra también el `User-Agent`, y eso no es un detalle: es lo que permite comprobar **quién**
    llegó. Sin él, un mutante que anotara a mano una entrada en el registro sería indistinguible de
    uno que recorrió su adaptador real, y la prueba pasaría a medir el arnés.
    """

    def __init__(self) -> None:
        self.recibido: list[dict] = []
        self._servidor: Any = None
        self.puerto = 0

    def __enter__(self) -> "Canary":
        import http.server

        recibido = self.recibido

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - nombre impuesto por la biblioteca
                largo = int(self.headers.get("Content-Length") or 0)
                cuerpo = self.rfile.read(largo).decode("utf-8", "replace")
                recibido.append({"metodo": self.command, "ruta": self.path, "cuerpo": cuerpo,
                                 "agente": self.headers.get("User-Agent") or ""})
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")

            do_GET = do_POST  # noqa: N815 - misma respuesta para el otro verbo

            def log_message(self, *_: Any) -> None:
                return

        self._servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.puerto = self._servidor.server_address[1]
        hilo = threading.Thread(target=self._servidor.serve_forever, daemon=True)
        hilo.start()
        self._hilo = hilo
        return self

    def __exit__(self, *_: Any) -> None:
        self._servidor.shutdown()
        self._servidor.server_close()
        self._hilo.join(timeout=5)

    def ceso(self) -> bool:
        """Comprueba el cese conectándose: un canary vivo es un recurso sin dueño."""
        with socket.socket() as s:
            s.settimeout(1)
            return s.connect_ex(("127.0.0.1", self.puerto)) != 0


class ResultadoDeMutante(NamedTuple):
    mutante_id: str
    tratamiento: str
    alcanzo_el_canary: bool
    alcanzo_un_servicio: bool
    evidencia: str
    # Qué tiene que haber observado el control **por su cuenta** para creerle a este resultado. El
    # mutante no se acredita a sí mismo: `alcanzo_el_canary` es lo que el mutante dice, y esto es
    # con qué se comprueba. Sin esta separación, declarar el alcance sin recorrer el adaptador real
    # es indistinguible de recorrerlo.
    huella_esperada: str = ""


def variables_que_la_regla_descubre(entorno: dict, inventario: dict) -> list[str]:
    """Los nombres que la regla de descubrimiento marcaría como credencial en este entorno."""
    definidas = next(c for c in inventario["clases"] if c["clase"] == "variable_de_entorno")
    patrones = definidas["patrones_de_nombre"]
    return [n for n in sorted(entorno)
            if n in definidas["variables_de_token"] or any(p in n for p in patrones)]


def _entorno_desechable(hogar: Path, inventario: dict | None = None) -> dict:
    """Configuración local al proceso: nunca se toca la del usuario.

    Qué variables se retiran **se deriva de la regla**, no de una lista escrita al lado. Con dos
    listas paralelas, la regla descubre credenciales que el entorno cree haber quitado —medido: tres
    tokens reales de este host sobrevivían—, y el entorno «desechable» le entregaría al worker
    justo lo que se quería retirar.
    """
    if inventario is None:
        inventario, _ = _cargar_json(RUTA_SUPERFICIES)
    entorno = dict(os.environ)
    entorno["HOME"] = str(hogar)
    entorno["GIT_CONFIG_GLOBAL"] = os.devnull
    entorno["GIT_CONFIG_SYSTEM"] = os.devnull
    # `GIT_CONFIG_SYSTEM` NO alcanza. Medido sobre este host con git 2.50.1 (Apple Git-155): el
    # `credential.helper osxkeychain` vive en el gitconfig que Xcode instala junto al binario, y
    # apuntando `GIT_CONFIG_SYSTEM` a /dev/null se sigue leyendo. `GIT_CONFIG_NOSYSTEM` es lo único
    # que lo apaga. Sin esta línea el entorno «desechable» le deja al worker un helper capaz de
    # devolver credenciales del llavero: el mismo modo de fallar que las tres variables de token,
    # en la superficie que quedaba.
    entorno["GIT_CONFIG_NOSYSTEM"] = "1"
    entorno["GIT_TERMINAL_PROMPT"] = "0"
    entorno["GH_CONFIG_DIR"] = str(hogar / "gh-desechable")
    entorno.pop("SSH_AUTH_SOCK", None)
    for variable in variables_que_la_regla_descubre(entorno, inventario or {}):
        entorno.pop(variable, None)
    return entorno


def _correr_en(comando: list[str], cwd: Path | None, entorno: dict) -> tuple[int, str]:
    try:
        proc = subprocess.run(comando, cwd=str(cwd) if cwd else None, env=entorno,
                              capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        return 127, f"no se encontró {comando[0]}"
    except subprocess.TimeoutExpired:
        return 124, "no terminó dentro del tope"
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def correr_mutantes_de_publicacion(canary: Canary,
                                   taller: Path) -> list[ResultadoDeMutante]:
    """Los cuatro mutantes, cada uno por su ruta real y con su frontera interceptada."""
    hogar = taller / "hogar"
    hogar.mkdir(parents=True, exist_ok=True)
    entorno = _entorno_desechable(hogar)
    resultados: list[ResultadoDeMutante] = []
    url = f"http://127.0.0.1:{canary.puerto}/publicar"

    # mut-shell — `git push` real, con el remoto apuntado a un repositorio bare LOCAL.
    bare = taller / "canary.git"
    _correr_en(["git", "init", "--quiet", "--bare", str(bare)], None, entorno)
    repo = taller / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    _correr_en(["git", "init", "--quiet", "-b", "main", str(repo)], None, entorno)
    (repo / "archivo.txt").write_text("contenido a publicar\n", encoding="utf-8")
    _correr_en(["git", "-C", str(repo), "add", "archivo.txt"], None, entorno)
    _correr_en(["git", "-C", str(repo), "-c", "user.email=canary@local",
                "-c", "user.name=canary", "commit", "--quiet", "-m", "canary"], None, entorno)
    _correr_en(["git", "-C", str(repo), "remote", "add", "origin", str(bare)], None, entorno)
    _, sha = _correr_en(["git", "-C", str(repo), "rev-parse", "HEAD"], None, entorno)
    codigo, salida = _correr_en(["git", "-C", str(repo), "push", "--quiet", "origin", "main"],
                                None, entorno)
    _, refs = _correr_en(["git", "-C", str(bare), "for-each-ref"], None, entorno)
    resultados.append(ResultadoDeMutante(
        "mut-shell", "redireccion", bool(refs.strip()), False,
        f"`git push` salió en {codigo}; el repositorio bare local recibió: "
        f"{refs.strip() or 'nada'}{'' if codigo == 0 else ' — ' + salida[:120]}",
        # La huella es el objeto en el canary: el control lo busca ahí él mismo, así que declarar
        # el alcance sin haber empujado nada no alcanza.
        huella_esperada=f"objeto-en-canary:{bare}:{sha.strip()}"))

    # mut-url — `curl` real contra el canary.
    antes = len(canary.recibido)
    codigo, salida = _correr_en(
        ["curl", "--silent", "--show-error", "--max-time", "10", "--noproxy", "127.0.0.1",
         "-X", "POST", "--data", "contenido a publicar", url], None, entorno)
    resultados.append(ResultadoDeMutante(
        "mut-url", "redireccion", len(canary.recibido) > antes, False,
        f"`curl` salió en {codigo}; el canary registró "
        f"{len(canary.recibido) - antes} intentos{'' if codigo == 0 else ' — ' + salida[:120]}",
        huella_esperada="agente-en-canary:curl/"))

    # mut-api — cliente HTTP del runtime contra el canary.
    antes = len(canary.recibido)
    detalle = "publicación aceptada por el canary"
    try:
        peticion = urllib.request.Request(url, data=b"contenido a publicar", method="POST")
        with urllib.request.urlopen(peticion, timeout=10) as respuesta:
            respuesta.read()
    except Exception as exc:  # el intento tiene que quedar registrado igual que si funciona
        detalle = f"la publicación por API falló: {type(exc).__name__}"
    resultados.append(ResultadoDeMutante(
        "mut-api", "redireccion", len(canary.recibido) > antes, False,
        f"{detalle}; el canary registró {len(canary.recibido) - antes} intentos",
        huella_esperada="agente-en-canary:Python-urllib"))

    # mut-herramienta — denegación comprobable: la herramienta autenticada del host no alcanza.
    antes = len(canary.recibido)
    codigo, salida = _correr_en(["gh", "auth", "status"], None, entorno)
    denegada = codigo != 0
    resultados.append(ResultadoDeMutante(
        "mut-herramienta", "denegacion", len(canary.recibido) > antes, not denegada,
        f"`gh auth status` en el entorno desechable salió en {codigo} "
        f"({'sin sesión: denegada' if denegada else 'ENCONTRÓ SESIÓN'}); el canary registró "
        f"{len(canary.recibido) - antes} intentos",
        huella_esperada="ningun-agente-en-canary"))
    return resultados


def comprobar_huellas(resultados: list[ResultadoDeMutante], canary: Canary) -> list[str]:
    """Comprueba, por observación propia, que cada mutante recorrió su adaptador real.

    Es lo que separa «el mutante dice que llegó» de «el control lo vio llegar». Un mutante que
    anotara su propio alcance sin ejecutar nada pasaría lo primero y no lo segundo.
    """
    problemas: list[str] = []
    agentes = [r.get("agente", "") for r in canary.recibido]
    for resultado in resultados:
        huella = resultado.huella_esperada
        if huella.startswith("objeto-en-canary:"):
            _, ruta, sha = huella.split(":", 2)
            codigo, tipo = _correr_en(["git", "-C", ruta, "cat-file", "-t", sha], None,
                                      dict(os.environ))
            if codigo != 0 or tipo.strip() != "commit":
                problemas.append(f"`{resultado.mutante_id}`: el canary no tiene el objeto "
                                 f"`{sha[:12]}` que el `push` tenía que dejarle — el adaptador "
                                 f"real no recorrió su ruta")
        elif huella.startswith("agente-en-canary:"):
            esperado = huella.split(":", 1)[1]
            if not any(a.startswith(esperado) for a in agentes):
                problemas.append(f"`{resultado.mutante_id}`: ninguna entrada del canary viene de "
                                 f"`{esperado}` — el intento no lo hizo su adaptador real, y los "
                                 f"agentes vistos son {agentes}")
        elif huella == "ningun-agente-en-canary":
            continue
        else:
            problemas.append(f"`{resultado.mutante_id}`: no declara huella con la que "
                             f"comprobarlo por observación propia")
    return problemas


def revisar_invariantes(snapshot_antes: tuple, snapshot_despues: tuple, canary_ceso: bool,
                        hogar_desechable: Path, inventario: dict) -> list[str]:
    """Los cuatro invariantes de la prueba, en una función propia y con su negativo posible."""
    problemas: list[str] = []
    if snapshot_antes != snapshot_despues:
        problemas.append("el árbol observado cambió mientras corrían los mutantes: dejaron de ser "
                         "una prueba y pasaron a ser el efecto que se quería impedir")
    if not canary_ceso:
        problemas.append("el canary sigue escuchando: un recurso vivo sin dueño")
    if not hogar_desechable.is_dir():
        problemas.append("los mutantes no corrieron sobre un HOME desechable")
    declarados = {i["invariante_id"] for i in inventario["invariantes_de_la_prueba"]}
    if declarados != {"entorno-desechable", "snapshot-igual", "canary-cesado",
                      "ningun-servicio-alcanzado"}:
        problemas.append(f"los invariantes declarados no son los que el control comprueba: "
                         f"{sorted(declarados)}")
    return problemas


def revisar_mutantes(resultados: list[ResultadoDeMutante],
                     inventario: dict) -> list[str]:
    """Cada mutante tiene que haber recorrido su ruta y no haber alcanzado ningún servicio."""
    problemas: list[str] = []
    declarados = {m["mutante_id"]: m for m in inventario["mutantes_de_publicacion"]}
    corridos = {r.mutante_id: r for r in resultados}

    faltan = sorted(set(declarados) - set(corridos))
    sobran = sorted(set(corridos) - set(declarados))
    if faltan:
        problemas.append(f"mutantes declarados que no se corrieron: {faltan}")
    if sobran:
        problemas.append(f"se corrieron mutantes que el inventario no declara: {sobran}")

    admitidos = set(inventario["tratamientos_admitidos"])
    # La superficie que el inventario declara sin un tratamiento admitido bloquea ANTES de correr
    # nada: es la cláusula de «sin redirección segura ni denegación comprobable». Va separada de la
    # de abajo —que compara lo corrido contra lo declarado— porque si estuvieran juntas un caso
    # caería por las dos y ninguna quedaría ejercida sola.
    for ident, declarado in sorted(declarados.items()):
        if declarado["tratamiento"] not in admitidos:
            problemas.append(f"`{ident}`: el inventario le declara el tratamiento "
                             f"`{declarado['tratamiento']}`, que no es ni redirección segura ni "
                             f"denegación comprobable — la superficie bloquea")

    for ident, resultado in sorted(corridos.items()):
        declarado = declarados.get(ident)
        if declarado is None:
            continue
        if resultado.tratamiento != declarado["tratamiento"]:
            problemas.append(f"`{ident}`: corrió por `{resultado.tratamiento}` y el inventario "
                             f"declara `{declarado['tratamiento']}`")
        if resultado.alcanzo_un_servicio:
            problemas.append(f"`{ident}`: alcanzó un destino fuera del host — {resultado.evidencia}")
        if resultado.tratamiento == "redireccion" and not resultado.alcanzo_el_canary:
            problemas.append(f"`{ident}`: no llegó al canary, así que su ruta real no se recorrió "
                             f"— {resultado.evidencia}")
        if resultado.tratamiento == "denegacion" and resultado.alcanzo_el_canary:
            problemas.append(f"`{ident}`: la superficie que se declaró denegada publicó igual — "
                             f"{resultado.evidencia}")
    return problemas


def descubrir_canales(arbol: Path, entorno: dict, inventario: dict) -> list[dict]:
    """La regla de descubrimiento de canales: siete clases, todas del conjunto cerrado."""
    hogar = Path(entorno.get("HOME", str(Path.home())))
    superficies: list[dict] = []

    def agregar(clase: str, ident: str, descripcion: str) -> None:
        superficies.append({"superficie_id": ident, "clase": clase, "descripcion": descripcion})

    por_clase = {c["clase"]: c for c in inventario["clases"]}

    for nombre in por_clase["binario_en_path"]["binarios_con_capacidad_de_publicar"]:
        ruta = shutil.which(nombre, path=entorno.get("PATH"))
        if ruta:
            agregar("binario_en_path", f"bin-{nombre}", f"`{nombre}` alcanzable por PATH")

    for relativa in por_clase["credencial_en_disco"]["rutas_de_credencial"]:
        if (hogar / relativa).exists():
            agregar("credencial_en_disco", f"cred-{relativa.replace('/', '-').lstrip('.')}",
                    f"`{relativa}` alcanzable desde el HOME efectivo")

    definidas = por_clase["variable_de_entorno"]
    patrones = definidas["patrones_de_nombre"]
    for nombre in sorted(entorno):
        if nombre in definidas["variables_de_token"] or any(p in nombre for p in patrones):
            agregar("variable_de_entorno", f"env-{nombre.lower().replace('_', '-')}",
                    f"`{nombre}` presente en el entorno del proceso")

    codigo, salida = _correr_en(["git", "config", "--get-all", "credential.helper"], arbol, entorno)
    if codigo == 0 and salida.strip():
        for linea in salida.splitlines():
            agregar("credential_helper_de_git", f"helper-{_slug(linea)}",
                    f"credential.helper `{linea}` resuelto en el entorno efectivo")

    socket_ssh = entorno.get("SSH_AUTH_SOCK")
    if socket_ssh and Path(socket_ssh).exists():
        agregar("socket_o_agente_ssh", "ssh-agent", "SSH_AUTH_SOCK apunta a un socket existente")

    codigo, salida = _correr_en(["git", "-C", str(arbol), "remote"], None, entorno)
    if codigo == 0:
        for remoto in salida.split():
            agregar("remoto_configurado", f"remoto-{_slug(remoto)}",
                    f"remoto `{remoto}` configurado en el árbol observado")

    for herramienta in por_clase["herramienta_autenticada"]["herramientas"]:
        if shutil.which(herramienta["nombre"], path=entorno.get("PATH")) is None:
            continue
        codigo, _ = _correr_en(herramienta["comando_de_estado"].split(), None, entorno)
        if codigo == 0:
            agregar("herramienta_autenticada", f"tool-{herramienta['nombre']}",
                    f"`{herramienta['nombre']}` reporta sesión abierta")
    return superficies


def modo_autotest_egreso(args: argparse.Namespace) -> int:
    del args
    resultados: list[tuple[str, bool, str]] = []
    inventario, error = _cargar_json(RUTA_SUPERFICIES)
    if error:
        print(f"FALLA  {error}")
        return 1

    with tempfile.TemporaryDirectory(prefix="egreso-") as tmp:
        taller = Path(tmp)
        hogar = taller / "hogar"
        snapshot_antes = _snapshot_de_egreso(RAIZ)
        with Canary() as canary:
            corridas = correr_mutantes_de_publicacion(canary, taller)
            recibido_por_el_canary = list(canary.recibido)
            # El cese se comprueba en las DOS direcciones: acá adentro el canary está vivo y tiene
            # que decirlo. Sin este positivo, un `ceso()` que devolviera siempre True pasaría.
            vivo_mientras_escucha = not canary.ceso()
        ceso = canary.ceso()
        snapshot_despues = _snapshot_de_egreso(RAIZ)

        # [A] Los cuatro mutantes corrieron por su ruta real, comprobado POR OBSERVACIÓN PROPIA:
        #     el objeto que el `push` dejó en el canary, y el agente de cada intento HTTP.
        problemas = revisar_mutantes(corridas, inventario)
        problemas += comprobar_huellas(corridas, canary)
        resultados.append(("A", not problemas,
                           "los cuatro mutantes recorren su adaptador real —el objeto en el canary "
                           "y el agente de cada intento lo prueban— y ninguno sale del host"
                           if not problemas else " | ".join(problemas[:6])))

        # [B] El canary recibió lo que las redirecciones mandaron, y nada de la denegación.
        por_http = [r for r in corridas
                    if r.tratamiento == "redireccion" and r.mutante_id in ("mut-url", "mut-api")]
        fallas = []
        if len(recibido_por_el_canary) != len(por_http):
            fallas.append(f"el canary registró {len(recibido_por_el_canary)} intentos y los "
                          f"mutantes por HTTP fueron {len(por_http)}")
        if any("contenido a publicar" not in r["cuerpo"] for r in recibido_por_el_canary):
            fallas.append("el canary registró algo que no es lo que los mutantes mandaron")
        agentes = sorted(r["agente"].split("/")[0] for r in recibido_por_el_canary)
        if len(set(agentes)) != len(agentes):
            fallas.append(f"dos intentos del canary vienen del mismo agente ({agentes}): los dos "
                          f"mutantes por HTTP tienen que recorrer adaptadores distintos")
        resultados.append(("B", not fallas,
                           f"el canary registró los {len(por_http)} intentos por HTTP, cada uno de "
                           f"su adaptador ({', '.join(agentes)}), y nada más"
                           if not fallas else " | ".join(fallas)))

        # [C] Los invariantes de la prueba, con su negativo y con el cese comprobado en las dos
        #     direcciones.
        fallas = list(revisar_invariantes(snapshot_antes, snapshot_despues, ceso, hogar,
                                          inventario))
        if not vivo_mientras_escucha:
            fallas.append("el canary se declaró cesado mientras seguía escuchando: el cese no se "
                          "está comprobando, se está afirmando")
        if not revisar_invariantes(("refs-a", "objs-a"), ("refs-b", "objs-b"), ceso, hogar,
                                   inventario):
            fallas.append("un snapshot distinto antes y después no se detectó")
        if not revisar_invariantes(snapshot_antes, snapshot_despues, False, hogar, inventario):
            fallas.append("un canary sin cesar no se detectó")
        if not revisar_invariantes(snapshot_antes, snapshot_despues, ceso,
                                   taller / "hogar-que-no-existe", inventario):
            fallas.append("la ausencia del HOME desechable no se detectó")
        resultados.append(("C", not fallas,
                           "entorno desechable, snapshot igual antes y después y canary cesado, "
                           "con el negativo de cada uno" if not fallas else " | ".join(fallas)))

        # [D] La regla de descubrimiento mira EL ENTORNO, y eso se comprueba por clase: en el
        #     desechable no puede quedar ninguna credencial, ningún token, ningún agente SSH ni
        #     ninguna herramienta con sesión. Comparar solo los totales dejaba pasar una clase que
        #     siguiera mirando el HOME del usuario.
        fallas = []
        cerradas = {c["clase"] for c in inventario["clases"]}
        del_contrato = set(json.loads(
            CONTRATOS_POR_NOMBRE["bundle-corrida"].ruta.read_text(encoding="utf-8"))
            ["$defs"]["enum_clase_de_superficie"]["enum"])
        if cerradas != del_contrato:
            fallas.append(f"las clases de la regla no son las del contrato: {sorted(cerradas)} "
                          f"contra {sorted(del_contrato)}")
        del_host = descubrir_canales(RAIZ, dict(os.environ), inventario)
        desechable = descubrir_canales(RAIZ, _entorno_desechable(hogar), inventario)
        if not del_host:
            fallas.append("la regla no descubrió ninguna superficie en el entorno del host")
        por_clase_host = {c: sum(1 for s in del_host if s["clase"] == c) for c in cerradas}
        por_clase_desechable = {c: sum(1 for s in desechable if s["clase"] == c)
                                for c in cerradas}
        for clase in ("credencial_en_disco", "variable_de_entorno", "socket_o_agente_ssh",
                      "herramienta_autenticada"):
            if por_clase_desechable[clase]:
                fallas.append(f"el entorno desechable todavía descubre {clase}: la regla no está "
                              f"mirando el entorno que se le pasa")
            if not por_clase_host[clase]:
                fallas.append(f"la regla no descubre `{clase}` ni en el entorno del host, así que "
                              f"su cero en el desechable no prueba nada")
        clases_vistas = {s["clase"] for s in del_host}
        if not clases_vistas <= cerradas:
            fallas.append(f"la regla produjo clases fuera del conjunto cerrado: "
                          f"{sorted(clases_vistas - cerradas)}")
        resultados.append(("D", not fallas,
                           f"la regla descubre {len(del_host)} superficies en el host y "
                           f"{len(desechable)} en el desechable, y las cuatro clases que dependen "
                           f"del entorno caen a cero" if not fallas else " | ".join(fallas)))

        # [E] Los negativos del revisor: cada cláusula tiene una entrada que la pone roja, y el
        #     positivo de las huellas está en [A].
        fallas = []
        alcanzo = ResultadoDeMutante("mut-url", "redireccion", True, True, "e")
        if not any("alcanzó un destino fuera del host" in p
                   for p in revisar_mutantes([alcanzo], inventario)):
            fallas.append("un mutante que alcanza un servicio no bloqueó por ese motivo")
        no_llego = ResultadoDeMutante("mut-api", "redireccion", False, False, "e")
        if not any("no llegó al canary" in p for p in revisar_mutantes([no_llego], inventario)):
            fallas.append("un mutante redirigido que no llega al canary no bloqueó por ese motivo")
        publico = ResultadoDeMutante("mut-herramienta", "denegacion", True, False, "e")
        if not any("publicó igual" in p for p in revisar_mutantes([publico], inventario)):
            fallas.append("una superficie declarada denegada que publica no bloqueó por ese motivo")
        distinto = ResultadoDeMutante("mut-shell", "denegacion", True, False, "e")
        if not any("y el inventario declara" in p
                   for p in revisar_mutantes([distinto], inventario)):
            fallas.append("un mutante corrido por otro tratamiento que el declarado no se detectó")
        if not revisar_mutantes(corridas[:1], inventario):
            fallas.append("correr un solo mutante de los cuatro declarados no se detectó")
        sin_tratamiento = json.loads(json.dumps(inventario))
        sin_tratamiento["mutantes_de_publicacion"][0]["tratamiento"] = "ninguno"
        if not any("la superficie bloquea" in p
                   for p in revisar_mutantes(corridas, sin_tratamiento)):
            fallas.append("una superficie sin redirección segura ni denegación comprobable no "
                          "bloqueó")
        sin_huella = ResultadoDeMutante("mut-url", "redireccion", True, False, "e")
        if not any("no declara huella" in p for p in comprobar_huellas([sin_huella], canary)):
            fallas.append("un mutante sin huella con la que comprobarlo no se detectó")
        resultados.append(("E", not fallas,
                           "el revisor bloquea con servicio alcanzado, sin llegar al canary, con "
                           "denegación que publica, con tratamiento cambiado, con mutantes "
                           "faltantes, sin tratamiento admitido y sin huella"
                           if not fallas else " | ".join(fallas)))

    return _cerrar(resultados)


def _bundle_del_caso(caso: dict) -> dict:
    """El caso del corpus, visto como el bundle que el juicio lee."""
    return {
        "punto_de_despacho": caso["punto_de_despacho"],
        "pruebas_de_aislamiento": caso["pruebas_de_aislamiento"],
        "recursos": caso["recursos"],
        "inventario_de_egreso_reejecutado": caso["inventario_de_egreso_reejecutado"],
    }


def modo_autotest_aislamiento(args: argparse.Namespace) -> int:
    del args
    resultados: list[tuple[str, bool, str]] = []
    corpus, error_corpus = _cargar_json(RUTA_CORPUS_AISLAMIENTO)
    manifest, error_manifest = _cargar_json(RUTA_MANIFEST_AISLAMIENTO)
    matriz, error_matriz = _cargar_json(RUTA_MATRIZ)
    for error in (error_corpus, error_manifest, error_matriz):
        if error:
            print(f"FALLA  {error}")
            return 1

    por_id = {c["caso_id"]: c for c in corpus["casos"]}
    casos = manifest["casos"]
    ejercidas: set[str] = set()

    # [A] Corpus y manifest, comparados en las dos direcciones.
    del_corpus = [c["caso_id"] for c in corpus["casos"]]
    del_manifest = [c["caso_id"] for c in casos]
    diferencias = [f"del corpus y sin caso en el manifest: {c}"
                   for c in del_corpus if c not in del_manifest]
    diferencias += [f"del manifest y sin caso en el corpus: {c}"
                    for c in del_manifest if c not in del_corpus]
    resultados.append(("A", not diferencias,
                       f"corpus ↔ manifest ({len(del_corpus)} casos)" if not diferencias
                       else " | ".join(diferencias[:6])))

    # [B] El permiso lo resuelve LA MATRIZ, y sigue diciendo lo que el corpus supone.
    fallas = []
    for punto, esperado in manifest["puntos_del_corpus"].items():
        if punto == "por_que_se_declaran":
            continue
        efectivo = _permiso_efectivo_de(punto, matriz)
        if efectivo != esperado:
            fallas.append(f"la matriz declara `{efectivo}` para `{punto}` y el corpus mide "
                          f"suponiendo `{esperado}`")
    if _permiso_efectivo_de("punto-que-la-matriz-no-tiene", matriz) is not None:
        fallas.append("un punto ausente de la matriz devolvió permiso: el juicio se estaría "
                      "apoyando en un valor por omisión")
    resultados.append(("B", not fallas,
                       "el permiso efectivo sale de la matriz y es el que el corpus supone"
                       if not fallas else " | ".join(fallas)))

    # [C] Cada caso cae por SU cláusula y por su motivo, y ninguna más.
    fallas = []
    for caso in casos:
        datos = _bundle_del_caso(por_id[caso["caso_id"]])
        problemas = revisar_aislamiento(datos, matriz) + revisar_recursos(datos)
        claves = sorted({p.clave for p in problemas})
        esperadas = sorted(caso["clausulas_esperadas"])
        if claves != esperadas:
            fallas.append(f"`{caso['caso_id']}`: cayó por {claves} y se esperaba {esperadas}")
            continue
        fragmento = caso.get("fragmento_esperado")
        if fragmento and not any(fragmento in p.detalle for p in problemas):
            fallas.append(f"`{caso['caso_id']}`: cayó por {claves} pero no por su motivo — se "
                          f"esperaba «{fragmento}»")
            continue
        ejercidas.update(claves)
    resultados.append(("C", not fallas,
                       f"los {len(casos)} casos caen por su cláusula y por su motivo"
                       if not fallas else " | ".join(fallas[:6])))

    # [D] Cobertura de las dos familias de cláusulas, acumulada corriendo.
    fallas = []
    todas = set(CLAUSULAS_DE_AISLAMIENTO) | set(CLAUSULAS_DE_RECURSOS)
    sin_ejercer = sorted(todas - ejercidas)
    inexistentes = sorted(ejercidas - todas)
    if sin_ejercer:
        fallas.append(f"cláusulas sin ningún caso que las ponga rojas: {sin_ejercer}")
    if inexistentes:
        fallas.append(f"se ejercieron cláusulas que no existen: {inexistentes}")
    declaradas = set(manifest["clausulas_de_aislamiento_ejercidas"]) | \
        set(manifest["clausulas_de_recursos_ejercidas"])
    if declaradas != todas:
        fallas.append(f"el manifest declara otras cláusulas que los conjuntos cerrados: "
                      f"{sorted(declaradas ^ todas)}")
    resultados.append(("D", not fallas,
                       f"las {len(todas)} cláusulas tienen quien las ponga rojas, acumulado "
                       f"corriendo" if not fallas else " | ".join(fallas)))

    # [E] El modo entero, con su negativo: un conjunto sano sale en 0 y uno bloqueado no.
    fallas = []
    with tempfile.TemporaryDirectory(prefix="aislamiento-") as tmp:
        raiz = Path(tmp)
        for caso_id in ("ais-escritor-sano", "rec-sano"):
            _materializar_caso(raiz / f"run-{caso_id}", por_id[caso_id])
        codigo = _codigo_de_modo(modo_aislamiento, aislamiento=str(raiz))
        if codigo != 0:
            fallas.append(f"un conjunto sano devolvió {codigo}")
    with tempfile.TemporaryDirectory(prefix="aislamiento-") as tmp:
        raiz = Path(tmp)
        _materializar_caso(raiz / "run-ais-escritor-sano", por_id["ais-escritor-sano"])
        _materializar_caso(raiz / "run-ais-permiso-falseado", por_id["ais-permiso-falseado"])
        codigo = _codigo_de_modo(modo_aislamiento, aislamiento=str(raiz))
        if codigo == 0:
            fallas.append("un conjunto con una observación bloqueada devolvió 0")
    with tempfile.TemporaryDirectory(prefix="aislamiento-") as tmp:
        if _codigo_de_modo(modo_aislamiento, aislamiento=tmp) == 0:
            fallas.append("un conjunto vacío devolvió 0: nada que juzgar no es lo mismo que "
                          "juzgado")
    resultados.append(("E", not fallas,
                       "el modo devuelve 0 sobre un conjunto sano y distinto de 0 sobre uno "
                       "bloqueado o vacío" if not fallas else " | ".join(fallas)))

    return _cerrar(resultados)


def modo_autotest_recursos(args: argparse.Namespace) -> int:
    del args
    resultados: list[tuple[str, bool, str]] = []
    corpus, error_corpus = _cargar_json(RUTA_CORPUS_AISLAMIENTO)
    manifest, error_manifest = _cargar_json(RUTA_MANIFEST_AISLAMIENTO)
    for error in (error_corpus, error_manifest):
        if error:
            print(f"FALLA  {error}")
            return 1
    por_id = {c["caso_id"]: c for c in corpus["casos"]}

    # [A] Los cuatro campos se modelan por separado: cambiar uno no cambia a los otros.
    fallas = []
    base = _bundle_del_caso(por_id["rec-sano"])
    sesion = next(r for r in base["recursos"] if r["ownership_state"] == "transferido")
    if sesion["life_state"] == "terminado_comprobado":
        fallas.append("el caso sano no ejerce la independencia: su recurso transferido también "
                      "está terminado, así que vida y propiedad no se distinguen")
    terminado = next(r for r in base["recursos"] if r["ownership_state"] == "sin_transferir")
    if terminado["life_state"] != "terminado_comprobado":
        fallas.append("el caso sano no tiene ningún recurso terminado y sin transferir")
    if revisar_recursos(base):
        fallas.append(f"el caso sano fue bloqueado: {[str(p) for p in revisar_recursos(base)]}")
    resultados.append(("A", not fallas,
                       "vida y propiedad se modelan por separado: un recurso vivo pero "
                       "transferido y otro terminado sin transferir conviven"
                       if not fallas else " | ".join(fallas)))

    # [B] Un negativo POR CAMPO ausente del recurso transferido.
    fallas = []
    for campo, clausula in (("owner", "transferido_sin_owner"),
                            ("next_action", "transferido_sin_next_action")):
        caso = json.loads(json.dumps(base))
        recurso = next(r for r in caso["recursos"] if r["ownership_state"] == "transferido")
        recurso.pop(campo, None)
        claves = {p.clave for p in revisar_recursos(caso)}
        if claves != {clausula}:
            fallas.append(f"quitar `{campo}` cayó por {sorted(claves)} y se esperaba `{clausula}`")
    resultados.append(("B", not fallas,
                       "quitar el dueño y quitar la próxima acción bloquean por separado, un "
                       "negativo por campo" if not fallas else " | ".join(fallas)))

    # [C] Solo un estado terminal comprobado cuenta como limpieza.
    fallas = []
    for vida in ("vivo", "cese_no_comprobable"):
        caso = json.loads(json.dumps(base))
        caso["recursos"] = [dict(terminado, life_state=vida)]
        if "vivo_sin_transferir" not in {p.clave for p in revisar_recursos(caso)}:
            fallas.append(f"un recurso en `{vida}` y sin transferir no bloqueó")
        caso["recursos"] = [dict(terminado, life_state=vida, ownership_state="transferido",
                                 owner="el conductor", next_action="cerrarlo al terminar")]
        if revisar_recursos(caso):
            fallas.append(f"un recurso en `{vida}` pero transferido con dueño y próxima acción "
                          f"bloqueó: la transferencia resuelve quién responde, no si sigue vivo")
    resultados.append(("C", not fallas,
                       "solo el terminal comprobado cuenta como limpieza, y lo que sigue vivo se "
                       "salva transfiriéndolo" if not fallas else " | ".join(fallas)))

    # [D] El cese nunca se infiere por efectos en el árbol, ni se copia entre recursos.
    fallas = []
    for caso_id, clausula in (("rec-cese-inferido", "cese_inferido_del_arbol"),
                              ("rec-cese-copiado", "evidencia_de_cese_copiada")):
        claves = {p.clave for p in revisar_recursos(_bundle_del_caso(por_id[caso_id]))}
        if claves != {clausula}:
            fallas.append(f"`{caso_id}` cayó por {sorted(claves)} y se esperaba `{clausula}`")
    resultados.append(("D", not fallas,
                       "el cese no se infiere del árbol ni se acredita copiando la evidencia de "
                       "otro recurso" if not fallas else " | ".join(fallas)))

    # [E] Cada cláusula de recursos tiene su caso, acumulado corriendo.
    fallas = []
    ejercidas = set()
    for caso in manifest["casos"]:
        claves = {p.clave for p in revisar_recursos(_bundle_del_caso(por_id[caso["caso_id"]]))}
        ejercidas.update(claves & set(CLAUSULAS_DE_RECURSOS))
    sin_ejercer = sorted(set(CLAUSULAS_DE_RECURSOS) - ejercidas)
    if sin_ejercer:
        fallas.append(f"cláusulas de recursos sin caso que las ponga rojas: {sin_ejercer}")
    if sorted(manifest["clausulas_de_recursos_ejercidas"]) != sorted(CLAUSULAS_DE_RECURSOS):
        fallas.append("el manifest declara otras cláusulas de recursos que el conjunto cerrado")
    resultados.append(("E", not fallas,
                       f"las {len(CLAUSULAS_DE_RECURSOS)} cláusulas de recursos tienen quien las "
                       f"ponga rojas" if not fallas else " | ".join(fallas)))

    return _cerrar(resultados)


def _materializar_caso(directorio: Path, caso: dict) -> None:
    """Escribe el caso como el bundle que el modo lee del disco."""
    directorio.mkdir(parents=True, exist_ok=True)
    (directorio / "bundle.json").write_text(
        json.dumps(_bundle_del_caso(caso), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _escribir_json(ruta: Path, datos: Any) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _codigo_de_modo(handler: Callable[[argparse.Namespace], int], **kwargs: Any) -> int:
    """Corre un modo capturando su salida: un `RESULTADO: FALLA` de un negativo impreso en medio
    de un autotest verde se lee como una regresión y no como el negativo que es."""
    with contextlib.redirect_stdout(io.StringIO()):
        return handler(argparse.Namespace(**kwargs))


def _snapshot_de_egreso(arbol: Path) -> tuple[str, str]:
    entorno = dict(os.environ)
    return (_correr_en(["git", "-C", str(arbol), "for-each-ref",
                        "--format=%(refname) %(objectname)"], None, entorno)[1],
            _correr_en(["git", "-C", str(arbol), "count-objects", "-v"], None, entorno)[1])


# --- Modo `--recibo-de-egreso`: materializar el inventario y probar cada superficie -------------
#
# `--autotest-egreso` prueba que la REGLA discrimina; este modo la APLICA sobre el entorno real y
# emite lo que el acta adjunta. Son dos cosas distintas y por eso son dos modos: un autotest verde
# no es un inventario, y el acta no puede congelar un conjunto de superficies que nadie materializó
# (D-14). El preflight del runner lo invoca como PROCESO APARTE, igual que al validador de bundles:
# quien produce la evidencia y quien la juzga no comparten proceso.
#
# El inventario que se congela es el del **entorno desechable**, porque ése es el que cada corrida
# reejecuta y compara. El del host viaja al lado como evidencia del retiro —no como el congelado—:
# sin él, «la regla no descubrió nada» y «no había nada que descubrir» se leen igual.

def hash_de_objeto(objeto: dict) -> str:
    """El hash de un objeto adjunto al acta, con la MISMA canonicalización que el pre-registro.

    Reusa `proyeccion_canonica` en vez de serializar aparte: dos canonicalizaciones distintas
    divergen, y la que se relaja es siempre la que corre sobre los datos reales. La exclusión de
    `CAMPO_DEL_HASH` que esa proyección aplica es un no-op acá —estos objetos no lo llevan—, así
    que el campo del hash se calcula sobre el objeto SIN él y se agrega después.
    """
    return hashlib.sha256(proyeccion_canonica(objeto)).hexdigest()


def recibos_por_superficie(superficies: list[dict], corridas: list[ResultadoDeMutante],
                           inventario: dict) -> tuple[list[dict], list[str]]:
    """Un recibo por superficie descubierta, con el mutante de su clase y su resultado.

    Una superficie cuya clase no tiene mutante queda **sin tratamiento**, y el inventario declara
    que eso `bloquea`: se reporta como problema en vez de omitirse, porque una superficie que nadie
    probó es exactamente la que puede publicar.
    """
    por_clase: dict[str, list[dict]] = {}
    for mutante in inventario["mutantes_de_publicacion"]:
        por_clase.setdefault(mutante["clase_de_superficie"], []).append(mutante)

    recibos: list[dict] = []
    problemas: list[str] = []
    por_id = {c.mutante_id: c for c in corridas}
    for superficie in superficies:
        mutantes = por_clase.get(superficie["clase"], [])
        if not mutantes:
            problemas.append(f"`{superficie['superficie_id']}` es de clase "
                             f"`{superficie['clase']}`, que no tiene mutante que la pruebe: "
                             f"sin tratamiento, {inventario['que_pasa_sin_tratamiento']}")
            continue
        for mutante in mutantes:
            corrida = por_id.get(mutante["mutante_id"])
            if corrida is None:
                problemas.append(f"el mutante `{mutante['mutante_id']}` de "
                                 f"`{superficie['superficie_id']}` no corrió")
                continue
            recibos.append({
                "superficie_id": superficie["superficie_id"],
                "clase": superficie["clase"],
                "adaptador_real": mutante["adaptador_real"],
                "mutante_id": mutante["mutante_id"],
                "tratamiento": mutante["tratamiento"],
                "frontera_interceptada": mutante["frontera_interceptada"],
                "alcanzo_el_canary": corrida.alcanzo_el_canary,
                "alcanzo_un_servicio": corrida.alcanzo_un_servicio,
                "resultado": corrida.evidencia,
            })
    return recibos, problemas


def modo_recibo_de_egreso(args: argparse.Namespace) -> int:
    inventario, error = _cargar_json(RUTA_SUPERFICIES)
    if error:
        print(f"FALLA  {error}")
        return 1

    with tempfile.TemporaryDirectory(prefix="recibo-egreso-") as tmp:
        taller = Path(tmp)
        hogar = taller / "hogar"
        hogar.mkdir(parents=True, exist_ok=True)
        entorno_desechable = _entorno_desechable(hogar, inventario)

        del_host = descubrir_canales(RAIZ, dict(os.environ), inventario)
        desechable = descubrir_canales(RAIZ, entorno_desechable, inventario)

        snapshot_antes = _snapshot_de_egreso(RAIZ)
        with Canary() as canary:
            corridas = correr_mutantes_de_publicacion(canary, taller)
        ceso = canary.ceso()
        snapshot_despues = _snapshot_de_egreso(RAIZ)

    problemas: list[str] = []
    problemas += revisar_mutantes(corridas, inventario)
    recibos, sin_tratamiento = recibos_por_superficie(desechable, corridas, inventario)
    problemas += sin_tratamiento
    if snapshot_antes != snapshot_despues:
        problemas.append("el árbol observado cambió entre el snapshot previo y el posterior: un "
                         "mutante que altera el árbol dejó de ser una prueba")
    if not ceso:
        problemas.append("el canary sigue escuchando: un canary vivo es un recurso sin dueño")

    inventario_de_egreso = {"superficies": desechable}
    inventario_de_egreso["inventario_sha256"] = hash_de_objeto(inventario_de_egreso)

    recibo = {
        "version_recibo": "1.0.0",
        "inventario_de_egreso": inventario_de_egreso,
        "superficies_del_host": del_host,
        "recibos_por_superficie": recibos,
        "invariantes": {
            "entorno_desechable": True,
            "snapshot_igual": snapshot_antes == snapshot_despues,
            "canary_cesado": ceso,
            "ningun_servicio_alcanzado": not any(c.alcanzo_un_servicio for c in corridas),
        },
    }
    recibo["recibo_sha256"] = hash_de_objeto(recibo)

    for entrada in recibos:
        print(f"[{entrada['tratamiento']:11s}] {entrada['superficie_id']} — "
              f"{entrada['mutante_id']} por `{entrada['adaptador_real']}`: {entrada['resultado']}")
    print(f"\nInventario del host: {len(del_host)} superficies · "
          f"del entorno desechable: {len(desechable)} · recibos: {len(recibos)}")
    print(f"inventario_sha256 {inventario_de_egreso['inventario_sha256']}")
    print(f"recibo_sha256     {recibo['recibo_sha256']}")

    salida = getattr(args, "salida", None)
    if salida:
        ruta = _ruta_absoluta(salida)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(recibo, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        relativa = ruta.relative_to(RAIZ) if ruta.is_relative_to(RAIZ) else ruta
        print(f"escrito en {relativa}")

    if problemas:
        for problema in problemas:
            print(f"  - {problema}")
        print(f"\nRESULTADO: FALLA — {len(problemas)} problemas")
        return 1
    print("\nRESULTADO: OK — inventario materializado y cada superficie descubierta con su "
          "tratamiento probado")
    return 0


# ---------------------------------------------------------------------------------------------
# Modos `--validar-protocolo`, `--cobertura`, `--promocion`, `--cobertura-final`,
# `--promocion-final`, `--autotest-cobertura` y `--autotest-promocion`.
#
# Los tres primeros leen el **pre-registro**; los dos `-final` leen el **baseline generado**. Son
# modos distintos y no banderas del mismo porque leen artefactos distintos en momentos distintos:
# los primeros corren antes de que exista ninguna observación, y los `-final` después de publicar.
#
# El evaluador de promoción vive en `evaluar_promocion` y no dentro de un modo: esta fase congela y
# verifica **el evaluador**, y el veredicto material de cada fase se emite en su propio gate. Un
# evaluador escrito dentro del modo que lo aplica no se podría verificar antes de aplicarlo.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_PROTOCOLO = DIR_SCRIPTS / "fixtures-baseline" / "protocolo"
RUTA_CORPUS_PROTOCOLO = DIR_FIXTURES_PROTOCOLO / "preregistros.json"
RUTA_MANIFEST_PROTOCOLO = DIR_FIXTURES_PROTOCOLO / "manifest.json"

# Las cinco categorías que AC-15 exige que el conjunto de métricas cubra. Se leen del vocabulario y
# no se transcriben: una categoría nueva ahí tiene que exigirse acá sin editar este archivo.
CLAUSULAS_DEL_PROTOCOLO = (
    "cohorte_sin_muestras",
    "muestra_sin_repeticion",
    "entorno_incompleto",
    "exclusiones_ausentes",
    "metrica_fuera_del_vocabulario",
    "formula_no_admitida",
    "unidad_discordante",
    "agregacion_discordante",
    "categoria_sin_metrica",
    "degradacion_sin_tasa",
)

CLAUSULAS_DE_COBERTURA = (
    "exclusion_con_causa_no_admisible",
    "metrica_obligatoria_sin_cohorte",
    "minimo_de_metrica_no_pre_registrada",
    "punto_en_las_dos_listas",
    "ecosistema_incompleto",
)

CLAUSULAS_DE_PROMOCION = (
    "metrica_obligatoria_sin_umbral",
    "umbral_de_metrica_no_pre_registrada",
    "fase_repetida",
    "composicion_ausente",
)


class Hallazgo(NamedTuple):
    clave: str
    detalle: str

    def __str__(self) -> str:
        return f"[{self.clave}] {self.detalle}"


def _metricas_del_vocabulario(vocabulario: dict) -> dict[str, dict]:
    """Índice `metrica_id` → su declaración, con la categoría adentro."""
    indice: dict[str, dict] = {}
    for categoria in vocabulario.get("categorias") or []:
        for metrica in categoria.get("metricas") or []:
            indice[metrica["metrica_id"]] = dict(metrica, categoria=categoria["categoria"])
    return indice


def revisar_protocolo(preregistro: dict, vocabulario: dict) -> list[Hallazgo]:
    """AC-15: casos, repeticiones, entorno, exclusiones y, por métrica, lo que el vocabulario dice.

    La unidad, la agregación y las fórmulas admitidas **no se validan contra el propio
    pre-registro**: se comparan contra el vocabulario cerrado. Un pre-registro que declarara su
    propia unidad sería un conjunto validándose a sí mismo.
    """
    problemas: list[Hallazgo] = []
    del_vocabulario = _metricas_del_vocabulario(vocabulario)
    categorias_obligatorias = [c["categoria"] for c in vocabulario.get("categorias") or []]

    muestras = (preregistro.get("cohorte") or {}).get("muestras") or []
    if not muestras:
        problemas.append(Hallazgo("cohorte_sin_muestras",
                                  "el protocolo no enumera ningún caso a medir"))
    for muestra in muestras:
        if not isinstance(muestra.get("repeticion"), int) or muestra["repeticion"] < 1:
            problemas.append(Hallazgo(
                "muestra_sin_repeticion",
                f"la muestra `{muestra.get('sample_id')}` no declara su número de repetición: sin "
                f"él, dos muestras del mismo punto son indistinguibles"))

    entorno = preregistro.get("entorno_esperado")
    if not isinstance(entorno, dict) or not entorno:
        problemas.append(Hallazgo("entorno_incompleto",
                                  "el protocolo no declara el entorno esperado"))
    if "exclusiones" not in preregistro:
        problemas.append(Hallazgo(
            "exclusiones_ausentes",
            "el protocolo no declara sus exclusiones: una lista vacía dice «no excluí nada», y la "
            "ausencia del campo no dice nada"))

    categorias_vistas: set[str] = set()
    for metrica in preregistro.get("metricas") or []:
        ident = metrica.get("metrica_id")
        declarada = del_vocabulario.get(ident)
        if declarada is None:
            problemas.append(Hallazgo(
                "metrica_fuera_del_vocabulario",
                f"`{ident}` no está en el vocabulario cerrado: el pre-registro elige dentro del "
                f"vocabulario, no lo amplía"))
            continue
        categorias_vistas.add(declarada["categoria"])
        if metrica.get("formula_id") not in (declarada.get("formulas_admitidas") or []):
            problemas.append(Hallazgo(
                "formula_no_admitida",
                f"`{ident}` elige la fórmula `{metrica.get('formula_id')}` y el vocabulario admite "
                f"{declarada.get('formulas_admitidas')}"))
        if metrica.get("unidad") != declarada.get("unidad"):
            problemas.append(Hallazgo(
                "unidad_discordante",
                f"`{ident}` declara la unidad `{metrica.get('unidad')}` y el vocabulario dice "
                f"`{declarada.get('unidad')}`"))
        if metrica.get("agregacion") != declarada.get("agregacion"):
            problemas.append(Hallazgo(
                "agregacion_discordante",
                f"`{ident}` declara la agregación `{metrica.get('agregacion')}` y el vocabulario "
                f"dice `{declarada.get('agregacion')}`"))
        if metrica.get("categoria") != declarada.get("categoria"):
            problemas.append(Hallazgo(
                "metrica_fuera_del_vocabulario",
                f"`{ident}` se declara de la categoría `{metrica.get('categoria')}` y el "
                f"vocabulario la pone en `{declarada.get('categoria')}`"))

    faltan = [c for c in categorias_obligatorias if c not in categorias_vistas]
    if faltan:
        problemas.append(Hallazgo(
            "categoria_sin_metrica",
            f"el conjunto de métricas no cubre {faltan}: las cinco categorías son obligatorias"))

    problemas.extend(_revisar_tasa_de_degradacion(preregistro, del_vocabulario))
    return problemas


def _revisar_tasa_de_degradacion(preregistro: dict,
                                 del_vocabulario: dict[str, dict]) -> list[Hallazgo]:
    """La degradación se publica como al menos una TASA, con sus tres campos declarados.

    Un conteo absoluto satisface «una métrica de degradación» sin contestar con qué frecuencia
    degrada el ecosistema, y es incomparable entre cohortes de tamaños distintos.
    """
    tasas = []
    for metrica in preregistro.get("metricas") or []:
        declarada = del_vocabulario.get(metrica.get("metrica_id"))
        if declarada is None or declarada.get("categoria") != "degradacion":
            continue
        if metrica.get("unidad") != "proporcion":
            continue
        if all(metrica.get(campo) for campo in ("numerador", "denominador",
                                                "regla_de_elegibilidad")):
            tasas.append(metrica["metrica_id"])
    if tasas:
        return []
    return [Hallazgo(
        "degradacion_sin_tasa",
        "ninguna métrica de degradación se publica como tasa con numerador, denominador y regla "
        "de elegibilidad declarados: un conteo absoluto no dice con qué frecuencia degrada el "
        "ecosistema y no se compara entre cohortes de tamaños distintos")]


def revisar_cobertura(preregistro: dict, puntos_del_ecosistema: set[str]) -> list[Hallazgo]:
    """AC-16: cobertura mínima por métrica y estrato, y causas de exclusión de conjunto cerrado."""
    problemas: list[Hallazgo] = []
    cobertura = preregistro.get("cobertura") or {}
    admisibles = {c["causa_id"] for c in preregistro.get("causas_admisibles_de_exclusion") or []}
    pre_registradas = {m["metrica_id"] for m in preregistro.get("metricas") or []}

    for exclusion in preregistro.get("exclusiones") or []:
        if exclusion.get("causa_id") not in admisibles:
            problemas.append(Hallazgo(
                "exclusion_con_causa_no_admisible",
                f"la exclusión de `{exclusion.get('identidad')}` cita la causa "
                f"`{exclusion.get('causa_id')}`, que no está en el conjunto cerrado "
                f"{sorted(admisibles)}: bloquea el cierre de la fase"))

    minimos = cobertura.get("minima_por_metrica_y_estrato") or []
    for minimo in minimos:
        if minimo.get("metrica_id") not in pre_registradas:
            problemas.append(Hallazgo(
                "minimo_de_metrica_no_pre_registrada",
                f"hay un mínimo de cobertura para `{minimo.get('metrica_id')}`, que el "
                f"pre-registro no declara como métrica"))

    con_minimo = {m["metrica_id"] for m in minimos}
    obligatorias = {ident for fase in preregistro.get("fases_comprometidas") or []
                    for ident in fase.get("metricas_obligatorias") or []}
    estratos_de_la_cohorte = {m.get("estrato_esperado") for m
                              in (preregistro.get("cohorte") or {}).get("muestras") or []}
    for ident in sorted(obligatorias):
        if ident not in con_minimo:
            problemas.append(Hallazgo(
                "metrica_obligatoria_sin_cohorte",
                f"`{ident}` es obligatoria para alguna fase y no tiene cobertura mínima declarada: "
                f"bloquea el cierre de la fase"))
            continue
        estratos_del_minimo = {m["estrato"] for m in minimos if m["metrica_id"] == ident
                               and m["minimo_de_muestras"] > 0}
        if estratos_del_minimo and not (estratos_del_minimo & estratos_de_la_cohorte):
            problemas.append(Hallazgo(
                "metrica_obligatoria_sin_cohorte",
                f"`{ident}` exige muestras en {sorted(estratos_del_minimo)} y la cohorte solo "
                f"tiene {sorted(e for e in estratos_de_la_cohorte if e)}: queda sin cohorte que "
                f"la mida"))

    observados = set(cobertura.get("puntos_observados") or [])
    no_observados = set(cobertura.get("puntos_no_observados") or [])
    en_ambas = observados & no_observados
    if en_ambas:
        problemas.append(Hallazgo(
            "punto_en_las_dos_listas",
            f"estos puntos se declaran observados y no observados a la vez: {sorted(en_ambas)}"))
    sin_declarar = puntos_del_ecosistema - observados - no_observados
    if sin_declarar:
        problemas.append(Hallazgo(
            "ecosistema_incompleto",
            f"la cobertura no dice nada de {sorted(sin_declarar)}: declarar qué se observa sin "
            f"declarar qué no deja el resto del ecosistema fuera del informe"))
    return problemas


# --- El evaluador determinista de promoción ---------------------------------------------------

VEREDICTOS = ("promovible", "no_promovible", "blocked", "not_evaluated")


class Veredicto(NamedTuple):
    fase_id: str
    veredicto: str
    por_umbral: tuple[tuple[str, bool | None], ...]
    razon: str


def _cumple(valor: float, umbral: dict) -> bool:
    """La comparación, con la dirección y el tratamiento del límite declarados.

    Sin el tratamiento del límite el veredicto no es determinista: el valor exactamente igual al
    umbral se resolvería por la implementación y no por el pre-registro.
    """
    limite = umbral["valor"]
    inclusivo = umbral["tratamiento_del_limite"] == "inclusivo"
    if umbral["direccion"] == "mayor_o_igual":
        return valor >= limite if inclusivo else valor > limite
    return valor <= limite if inclusivo else valor < limite


def evaluar_promocion(fase: dict, valores: dict[str, float | None],
                      la_fase_corrio: bool) -> Veredicto:
    """El veredicto de promoción de una fase, determinista.

    `not_evaluated` y `blocked` son veredictos distintos y no se funden: el primero dice que la fase
    **todavía no corrió**, el segundo que corrió y **falta una observación obligatoria**. Fundirlos
    haría que un baseline emitido hoy declarara bloqueadas a las fases que nadie ejecutó.
    """
    fase_id = fase["fase_id"]
    if not la_fase_corrio:
        return Veredicto(fase_id, "not_evaluated", (),
                         "la fase todavía no corrió: no hay nada que evaluar, y eso no es un "
                         "bloqueo")

    faltantes = [m for m in fase["metricas_obligatorias"] if valores.get(m) is None]
    if faltantes:
        efecto = fase["efecto_de_la_ausencia"]
        return Veredicto(fase_id, efecto, tuple((m, None) for m in faltantes),
                         f"la fase corrió y faltan observaciones de {faltantes}; el pre-registro "
                         f"declara que la ausencia produce `{efecto}`")

    por_umbral: list[tuple[str, bool | None]] = []
    for umbral in fase["umbrales"]:
        valor = valores.get(umbral["metrica_id"])
        por_umbral.append((umbral["metrica_id"],
                           None if valor is None else _cumple(valor, umbral)))
    comprobados = [ok for _, ok in por_umbral if ok is not None]
    if fase["composicion"] == "todas":
        promueve = bool(comprobados) and all(comprobados)
    else:
        promueve = any(comprobados)
    return Veredicto(
        fase_id, "promovible" if promueve else "no_promovible", tuple(por_umbral),
        f"composición `{fase['composicion']}` sobre {len(comprobados)} umbrales comprobados")


def revisar_promocion(preregistro: dict) -> list[Hallazgo]:
    """Que el evaluador tenga con qué decidir: sin esto, declarar umbrales no decide nada."""
    problemas: list[Hallazgo] = []
    pre_registradas = {m["metrica_id"] for m in preregistro.get("metricas") or []}
    vistas: set[str] = set()
    for fase in preregistro.get("fases_comprometidas") or []:
        fase_id = fase.get("fase_id")
        if fase_id in vistas:
            problemas.append(Hallazgo("fase_repetida",
                                      f"la fase `{fase_id}` está declarada dos veces"))
        vistas.add(fase_id)
        if not fase.get("composicion"):
            problemas.append(Hallazgo(
                "composicion_ausente",
                f"`{fase_id}` no declara cómo componer sus umbrales: con varios, el veredicto "
                f"dependería de quién lo calcula"))
        con_umbral = {u["metrica_id"] for u in fase.get("umbrales") or []}
        for ident in fase.get("metricas_obligatorias") or []:
            if ident not in con_umbral:
                problemas.append(Hallazgo(
                    "metrica_obligatoria_sin_umbral",
                    f"`{ident}` es obligatoria para `{fase_id}` y no tiene umbral: declarar la "
                    f"métrica sin compararla satisface la letra y no decide nada"))
        for ident in sorted(con_umbral):
            if ident not in pre_registradas:
                problemas.append(Hallazgo(
                    "umbral_de_metrica_no_pre_registrada",
                    f"`{fase_id}` pone un umbral sobre `{ident}`, que el pre-registro no declara "
                    f"como métrica"))
    return problemas


def _puntos_del_ecosistema() -> set[str]:
    matriz, error = _cargar_json(RUTA_MATRIZ)
    if error:
        return set()
    return {p["id"] for p in matriz.get("puntos") or []}


def _valor_de_campo(campo: Any) -> Any:
    """El valor de un campo de la matriz, que puede venir con su procedencia al lado."""
    return campo["valor"] if isinstance(campo, dict) and "valor" in campo else campo


def dimensiones_derivadas_de_la_matriz() -> tuple[dict[str, str], dict[str, str]]:
    """Qué skill y qué familia de rol le corresponde a cada punto, según la MATRIZ.

    Se derivan acá y no se leen del pre-registro a propósito: la cobertura por skill y por familia
    que el acta declara es la **prevista**, y compararla contra sí misma no comprueba nada. La
    efectiva sale de la matriz, que es la sede de esa relación.
    """
    matriz, error = _cargar_json(RUTA_MATRIZ)
    if error:
        return {}, {}
    skill_de: dict[str, str] = {}
    familia_de: dict[str, str] = {}
    for punto in matriz.get("puntos") or []:
        ident = _valor_de_campo(punto.get("id"))
        skill_de[ident] = _valor_de_campo(punto.get("skill"))
        familia_de[ident] = _valor_de_campo(punto.get("rol"))
    return skill_de, familia_de


def revisar_dimensiones_derivadas(preregistro: dict, skill_de: dict[str, str],
                                  familia_de: dict[str, str]) -> list[Hallazgo]:
    """AC-16 · V37: la cobertura por skill y por familia, contra la derivada de la matriz.

    `revisar_cobertura` cruza la dimensión de **puntos** contra el ecosistema y deja las otras dos
    declaradas sin comprobar: un acta podía omitir una skill de las dos listas —o declarar observada
    una que ningún punto observado usa— y nada lo notaba.

    Cada dimensión se comprueba en las dos direcciones y por separado, para que un hallazgo no
    enmascare al otro: que la unión cubra el universo de la matriz, y que lo declarado observado
    coincida exactamente con lo que los puntos observados implican.
    """
    problemas: list[Hallazgo] = []
    cobertura = preregistro.get("cobertura") or {}
    observados = set(cobertura.get("puntos_observados") or [])

    for nombre, mapa, clave_si, clave_no in (
            ("skill", skill_de, "skills_observadas", "skills_no_observadas"),
            ("familia_de_rol", familia_de, "familias_observadas", "familias_no_observadas")):
        if not mapa:
            problemas.append(Hallazgo(
                f"{nombre}_no_derivable",
                f"la matriz no resolvió la dimensión `{nombre}` de ningún punto: sin ella, la "
                f"cobertura declarada no se puede contrastar contra nada"))
            continue

        universo = {v for v in mapa.values() if v}
        declarado_si = set(cobertura.get(clave_si) or [])
        declarado_no = set(cobertura.get(clave_no) or [])

        sin_declarar = universo - declarado_si - declarado_no
        if sin_declarar:
            problemas.append(Hallazgo(
                f"{nombre}_sin_declarar",
                f"la cobertura no dice nada de {sorted(sin_declarar)} en la dimensión `{nombre}`: "
                f"la matriz las tiene y el acta no las declara ni observadas ni no observadas"))

        en_ambas = declarado_si & declarado_no
        if en_ambas:
            problemas.append(Hallazgo(
                f"{nombre}_en_las_dos_listas",
                f"{sorted(en_ambas)} se declaran observadas y no observadas a la vez en la "
                f"dimensión `{nombre}`"))

        efectivas = {mapa[p] for p in observados if mapa.get(p)}
        de_mas = declarado_si - efectivas
        if de_mas:
            problemas.append(Hallazgo(
                f"{nombre}_declarada_sin_punto_que_la_observe",
                f"la cobertura declara observadas {sorted(de_mas)} en la dimensión `{nombre}`, y "
                f"ningún punto observado las usa según la matriz"))
        de_menos = efectivas - declarado_si
        if de_menos:
            problemas.append(Hallazgo(
                f"{nombre}_observada_y_no_declarada",
                f"los puntos observados cubren {sorted(de_menos)} en la dimensión `{nombre}` y la "
                f"cobertura no las declara observadas"))
    return problemas


def _reportar(titulo: str, problemas: list[Hallazgo], cuando_esta_bien: str) -> int:
    if problemas:
        print(f"FALLA  {titulo} — {len(problemas)} problemas:")
        for p in problemas:
            print(f"       - {p}")
        print()
        print(f"RESULTADO: FALLA — {len(problemas)} problemas bloquean el cierre de la fase")
        return 1
    print(f"OK     {titulo}")
    print()
    print(f"RESULTADO: OK — {cuando_esta_bien}")
    return 0


def modo_validar_protocolo(args: argparse.Namespace) -> int:
    preregistro, error = _cargar_json(_ruta_absoluta(getattr(args, "validar_protocolo")))
    vocabulario, error_vocabulario = _cargar_json(RUTA_VOCABULARIO)
    for e in (error, error_vocabulario):
        if e:
            print(f"FALLA  {e}")
            return 1
    return _reportar("el protocolo del baseline", revisar_protocolo(preregistro, vocabulario),
                     "el protocolo enumera casos, repeticiones, entorno y exclusiones, y cada "
                     "métrica toma su fórmula, unidad y agregación del vocabulario cerrado")


def modo_cobertura(args: argparse.Namespace) -> int:
    preregistro, error = _cargar_json(_ruta_absoluta(getattr(args, "cobertura")))
    if error:
        print(f"FALLA  {error}")
        return 1
    skill_de, familia_de = dimensiones_derivadas_de_la_matriz()
    return _reportar("la cobertura declarada",
                     revisar_cobertura(preregistro, _puntos_del_ecosistema())
                     + revisar_dimensiones_derivadas(preregistro, skill_de, familia_de),
                     "la cobertura declara qué se observa y qué no, con mínimo por métrica y "
                     "estrato, y toda exclusión cita una causa del conjunto cerrado")


def modo_promocion(args: argparse.Namespace) -> int:
    preregistro, error = _cargar_json(_ruta_absoluta(getattr(args, "promocion")))
    if error:
        print(f"FALLA  {error}")
        return 1
    problemas = revisar_promocion(preregistro)
    if problemas:
        return _reportar("el evaluador de promoción", problemas, "")

    print("OK     el evaluador de promoción tiene con qué decidir en cada fase")
    print()
    # Sin observaciones, cada fase se evalúa como lo que es: una fase que todavía no corrió. El
    # veredicto material de cada una se emite en su propio gate, no acá.
    for fase in preregistro.get("fases_comprometidas") or []:
        veredicto = evaluar_promocion(fase, {}, la_fase_corrio=False)
        print(f"[{veredicto.fase_id}] {veredicto.veredicto} — {veredicto.razon}")
    print()
    print("RESULTADO: OK — el evaluador está congelado y verificado; el veredicto material de "
          "cada fase lo emite su propio gate")
    return 0


def _valores_publicados(ruta: Path) -> tuple[dict[str, float | None], list[str]]:
    """Los números del baseline publicado, leídos con la lectura inversa de su tabla normativa."""
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, [f"no se pudo leer {_relativa(ruta)}: {exc}"]
    publicados, problemas = numeros_publicados_del_markdown(texto)
    return {ident: n.valor for ident, n in publicados.items()}, problemas


def modo_cobertura_final(args: argparse.Namespace) -> int:
    ruta = _ruta_absoluta(getattr(args, "cobertura_final"))
    crudo = getattr(args, "preregistro", None)
    if not crudo:
        print("FALLA  `--cobertura-final` necesita `--preregistro <ruta>`", file=sys.stderr)
        return 2
    preregistro, error = _cargar_json(_ruta_absoluta(crudo))
    if error:
        print(f"FALLA  {error}")
        return 1
    valores, problemas_de_lectura = _valores_publicados(ruta)
    if problemas_de_lectura:
        for p in problemas_de_lectura:
            print(f"FALLA  {p}")
        return 1

    skill_de, familia_de = dimensiones_derivadas_de_la_matriz()
    problemas = (revisar_cobertura(preregistro, _puntos_del_ecosistema())
                 + revisar_dimensiones_derivadas(preregistro, skill_de, familia_de))
    cobertura = preregistro.get("cobertura") or {}
    no_observados = list(cobertura.get("puntos_no_observados") or [])
    texto = ruta.read_text(encoding="utf-8")
    for punto in no_observados:
        if punto not in texto:
            problemas.append(Hallazgo(
                "ecosistema_incompleto",
                f"el baseline no informa que `{punto}` quedó sin observar: el criterio exige que "
                f"el documento diga qué parte del ecosistema no pudo verse"))
    for minimo in cobertura.get("minima_por_metrica_y_estrato") or []:
        if minimo["minimo_de_muestras"] > 0 and valores.get(minimo["metrica_id"]) is None:
            problemas.append(Hallazgo(
                "metrica_obligatoria_sin_cohorte",
                f"`{minimo['metrica_id']}` exige {minimo['minimo_de_muestras']} muestras en "
                f"`{minimo['estrato']}` y el baseline la publica sin valor"))
    return _reportar("la cobertura del baseline publicado", problemas,
                     f"la cobertura mínima se cumplió y el documento informa los "
                     f"{len(no_observados)} puntos que no pudieron observarse")


def modo_promocion_final(args: argparse.Namespace) -> int:
    ruta = _ruta_absoluta(getattr(args, "promocion_final"))
    crudo = getattr(args, "preregistro", None)
    if not crudo:
        print("FALLA  `--promocion-final` necesita `--preregistro <ruta>`", file=sys.stderr)
        return 2
    preregistro, error = _cargar_json(_ruta_absoluta(crudo))
    if error:
        print(f"FALLA  {error}")
        return 1
    valores, problemas_de_lectura = _valores_publicados(ruta)
    problemas = [Hallazgo("lectura_del_baseline", p) for p in problemas_de_lectura]
    problemas += revisar_promocion(preregistro)
    if problemas:
        return _reportar("el veredicto de promoción", problemas, "")

    bloqueadas = []
    for fase in preregistro.get("fases_comprometidas") or []:
        veredicto = evaluar_promocion(fase, valores, la_fase_corrio=True)
        print(f"[{veredicto.fase_id}] {veredicto.veredicto} — {veredicto.razon}")
        for metrica, cumple in veredicto.por_umbral:
            marca = "—" if cumple is None else ("cumple" if cumple else "no cumple")
            print(f"       {metrica}: {marca}")
        if veredicto.veredicto == "blocked":
            bloqueadas.append(veredicto.fase_id)
    print()
    if bloqueadas:
        print(f"RESULTADO: FALLA — fases bloqueadas por observaciones obligatorias ausentes: "
              f"{', '.join(bloqueadas)}")
        return 1
    print("RESULTADO: OK — el evaluador emitió un veredicto por fase sobre los números publicados")
    return 0


# --- `--autotest-cobertura` y `--autotest-promocion` ------------------------------------------
#
# Las variantes del corpus se derivan del caso sano alterando UN punto. Así la única diferencia
# entre el positivo y cada negativo es la que el manifest declara, y una cláusula que cayera por
# otra causa se ve en el acto.

RUTA_PROTOCOLO_SANO = DIR_FIXTURES_PROTOCOLO / "sano.json"


def _revisar_por_modo(modo: str, preregistro: dict, vocabulario: dict) -> list[Hallazgo]:
    if modo == "protocolo":
        return revisar_protocolo(preregistro, vocabulario)
    if modo == "cobertura":
        return revisar_cobertura(preregistro, _puntos_del_ecosistema())
    if modo == "promocion":
        return revisar_promocion(preregistro)
    raise ValueError(f"modo desconocido en el manifest: {modo!r}")


def _insumos_del_protocolo() -> tuple[dict, dict, dict, dict, list[str]]:
    sano, e1 = _cargar_json(RUTA_PROTOCOLO_SANO)
    corpus, e2 = _cargar_json(RUTA_CORPUS_PROTOCOLO)
    manifest, e3 = _cargar_json(RUTA_MANIFEST_PROTOCOLO)
    vocabulario, e4 = _cargar_json(RUTA_VOCABULARIO)
    return sano, corpus, manifest, vocabulario, [e for e in (e1, e2, e3, e4) if e]


def _controles_del_corpus(modos: tuple[str, ...], clausulas: tuple[str, ...],
                          claves_del_manifest: tuple[str, ...]) -> list[tuple[str, bool, str]]:
    """Los controles que comparten `--autotest-cobertura` y `--autotest-promocion`.

    Comparten el corpus y la disciplina —cada variante cae por su cláusula y por su motivo—, así que
    compartirlos evita dos copias que puedan divergir; lo que cambia es qué modos mira cada uno.
    """
    resultados: list[tuple[str, bool, str]] = []
    sano, corpus, manifest, vocabulario, errores = _insumos_del_protocolo()
    if errores:
        return [("A", False, " | ".join(errores))]

    variantes = corpus["variantes"]
    del_manifest = [v for v in manifest["variantes"] if v["modo"] in modos]

    # [A] Corpus y manifest, en las dos direcciones. Se compara el corpus ENTERO y no solo las
    # variantes de estos modos: una variante que nadie declara tiene que verse desde los dos
    # autotests, no quedar en la zona ciega del otro.
    esperadas = {v["variante"] for v in del_manifest}
    en_corpus = set(variantes)
    faltan = sorted(esperadas - en_corpus)
    sobran = sorted({v["variante"] for v in manifest["variantes"]} - en_corpus)
    diferencias = ([f"declaradas en el manifest y ausentes del corpus: {faltan}"] if faltan else [])
    diferencias += ([f"en el manifest y sin variante en el corpus: {sobran}"] if sobran else [])
    if len(manifest["variantes"]) != len(variantes):
        diferencias.append(f"el corpus tiene {len(variantes)} variantes y el manifest declara "
                           f"{len(manifest['variantes'])}")
    resultados.append(("A", not diferencias,
                       f"corpus ↔ manifest ({len(variantes)} variantes)" if not diferencias
                       else " | ".join(diferencias)))

    # [B] El caso sano no cae por ninguna cláusula de estos modos.
    fallas = []
    for modo in modos:
        problemas = _revisar_por_modo(modo, sano, vocabulario)
        if problemas:
            fallas.append(f"`{modo}` bloqueó el caso sano: {[str(p) for p in problemas][:3]}")
    resultados.append(("B", not fallas,
                       f"el pre-registro sano pasa {', '.join(modos)}"
                       if not fallas else " | ".join(fallas)))

    # [C] Cada variante cae por SU cláusula y por su motivo, y ninguna más.
    fallas = []
    ejercidas: set[str] = set()
    for declarada in del_manifest:
        problemas = _revisar_por_modo(declarada["modo"], variantes[declarada["variante"]],
                                      vocabulario)
        claves = sorted({p.clave for p in problemas})
        if claves != [declarada["clausula"]]:
            fallas.append(f"`{declarada['variante']}`: cayó por {claves} y se esperaba "
                          f"`{declarada['clausula']}`")
            continue
        if not any(declarada["fragmento"] in p.detalle for p in problemas):
            fallas.append(f"`{declarada['variante']}`: cayó por `{declarada['clausula']}` pero no "
                          f"por su motivo — se esperaba «{declarada['fragmento']}»")
            continue
        ejercidas.add(declarada["clausula"])
    resultados.append(("C", not fallas,
                       f"las {len(del_manifest)} variantes caen por su cláusula y por su motivo"
                       if not fallas else " | ".join(fallas[:6])))

    # [D] Cobertura de las cláusulas, acumulada corriendo.
    fallas = []
    sin_ejercer = sorted(set(clausulas) - ejercidas)
    inexistentes = sorted(ejercidas - set(clausulas))
    if sin_ejercer:
        fallas.append(f"cláusulas sin variante que las ponga rojas: {sin_ejercer}")
    if inexistentes:
        fallas.append(f"se ejercieron cláusulas que no existen: {inexistentes}")
    declaradas = [c for clave in claves_del_manifest for c in manifest[clave]]
    if sorted(declaradas) != sorted(clausulas):
        fallas.append(f"el manifest declara otras cláusulas que el conjunto cerrado: "
                      f"{sorted(set(declaradas) ^ set(clausulas))}")
    resultados.append(("D", not fallas,
                       f"las {len(clausulas)} cláusulas tienen quien las ponga rojas, acumulado "
                       f"corriendo" if not fallas else " | ".join(fallas)))
    return resultados


def modo_autotest_cobertura(args: argparse.Namespace) -> int:
    del args
    resultados = _controles_del_corpus(
        ("protocolo", "cobertura"), CLAUSULAS_DEL_PROTOCOLO + CLAUSULAS_DE_COBERTURA,
        ("clausulas_del_protocolo_ejercidas", "clausulas_de_cobertura_ejercidas"))
    sano, corpus, manifest, _, errores = _insumos_del_protocolo()
    if errores:
        return _cerrar(resultados)

    # [D] de arriba solo cubre las del protocolo; las de cobertura se comprueban aparte porque el
    # manifest las declara en su propia lista.
    fallas = []
    if sorted(manifest["clausulas_de_cobertura_ejercidas"]) != sorted(CLAUSULAS_DE_COBERTURA):
        fallas.append("el manifest declara otras cláusulas de cobertura que el conjunto cerrado")
    resultados.append(("E", not fallas,
                       f"el manifest declara las {len(CLAUSULAS_DE_COBERTURA)} cláusulas de "
                       f"cobertura del conjunto cerrado" if not fallas else " | ".join(fallas)))

    # [F] Los modos enteros, con su negativo, y `--cobertura-final` sobre un baseline publicado.
    fallas = []
    with tempfile.TemporaryDirectory(prefix="protocolo-") as tmp:
        raiz = Path(tmp)
        ruta_sano = raiz / "sano.json"
        _escribir_json(ruta_sano, sano)
        for bandera, handler in (("validar_protocolo", modo_validar_protocolo),
                                 ("cobertura", modo_cobertura)):
            if _codigo_de_modo(handler, **{bandera: str(ruta_sano)}) != 0:
                fallas.append(f"`--{bandera.replace('_', '-')}` devolvió distinto de 0 sobre el "
                              f"caso sano")
        ruta_mala = raiz / "mala.json"
        _escribir_json(ruta_mala, corpus["variantes"]["c-causa-no-admisible"])
        if _codigo_de_modo(modo_cobertura, cobertura=str(ruta_mala)) == 0:
            fallas.append("`--cobertura` devolvió 0 sobre una exclusión con causa no admisible")

        baseline = raiz / "baseline.md"
        baseline.write_text(_baseline_sintetico(sano), encoding="utf-8")
        if _codigo_de_modo(modo_cobertura_final, cobertura_final=str(baseline),
                           preregistro=str(ruta_sano)) != 0:
            fallas.append("`--cobertura-final` devolvió distinto de 0 sobre un baseline que "
                          "informa lo que no pudo observarse y cumple los mínimos")
        sin_informe = raiz / "sin-informe.md"
        sin_informe.write_text(
            _baseline_sintetico(sano).replace("sdd-pr-feedback-implement-delegado", "otro-punto"),
            encoding="utf-8")
        if _codigo_de_modo(modo_cobertura_final, cobertura_final=str(sin_informe),
                           preregistro=str(ruta_sano)) == 0:
            fallas.append("`--cobertura-final` devolvió 0 sobre un baseline que no informa qué "
                          "parte del ecosistema quedó sin observar")
        sin_valor = raiz / "sin-valor.md"
        sin_valor.write_text(_baseline_sintetico(sano, sin_valores={"tasa-de-degradacion"}),
                             encoding="utf-8")
        if _codigo_de_modo(modo_cobertura_final, cobertura_final=str(sin_valor),
                           preregistro=str(ruta_sano)) == 0:
            fallas.append("`--cobertura-final` devolvió 0 con una métrica de cobertura mínima "
                          "publicada sin valor")
    resultados.append(("F", not fallas,
                       "los modos devuelven 0 sobre el caso sano y distinto de 0 sobre sus "
                       "negativos, incluido `--cobertura-final`"
                       if not fallas else " | ".join(fallas)))

    # [G] La dimensión derivada de la matriz (V37), con un ataque por cláusula y su mutante.
    #
    # El mutante que importa es el de **eliminación de la dimensión**: sin él, agregar la
    # comprobación y no ejercitarla deja una guarda que nace salteada —el corpus de este autotest
    # ya pasaba entero antes de que existiera—. Acá se anula la dimensión reemplazando los mapas
    # derivados por vacíos y se exige que los cuatro ataques dejen de caer: si alguno sigue
    # cayendo, lo está cazando otra cláusula y la suya no está ejercida.
    fallas = []
    skill_de, familia_de = dimensiones_derivadas_de_la_matriz()
    if not skill_de or not familia_de:
        fallas.append("la matriz no resolvió las dimensiones: el control no puede correr")
    else:
        def con(mutacion) -> list[Hallazgo]:
            copia = copy.deepcopy(sano)
            mutacion(copia)
            return revisar_dimensiones_derivadas(copia, skill_de, familia_de)

        una_skill = sorted({skill_de[p] for p in (sano["cobertura"]["puntos_observados"] or [])})[0]
        una_familia = sorted({familia_de[p]
                              for p in (sano["cobertura"]["puntos_observados"] or [])})[0]
        ataques = {
            "skill_sin_declarar":
                lambda d: d["cobertura"]["skills_observadas"].remove(una_skill),
            "skill_en_las_dos_listas":
                lambda d: d["cobertura"]["skills_no_observadas"].append(una_skill),
            "familia_de_rol_declarada_sin_punto_que_la_observe":
                lambda d: d["cobertura"]["familias_observadas"].append("investigator"),
            "familia_de_rol_observada_y_no_declarada":
                lambda d: d["cobertura"]["familias_observadas"].remove(una_familia),
        }
        if revisar_dimensiones_derivadas(sano, skill_de, familia_de):
            fallas.append("el caso sano tiene hallazgos en la dimensión derivada")
        for clase, mutacion in ataques.items():
            clases = {h.clave for h in con(mutacion)}
            if clase not in clases:
                fallas.append(f"el ataque de `{clase}` no cayó por su cláusula "
                              f"(cayó por {sorted(clases) or 'ninguna'})")
        # El mutante: sin la dimensión, ningún ataque puede caer.
        vivos = [clase for clase, mutacion in ataques.items()
                 if _con_dimension_anulada(sano, mutacion)]
        if vivos:
            fallas.append(f"con la dimensión eliminada, estos ataques siguen cayendo y por lo "
                          f"tanto no la ejercen: {vivos}")
    resultados.append(("G", not fallas,
                       f"la dimensión derivada de la matriz cruza skill y familia en las dos "
                       f"direcciones: {len(ataques) if not fallas else 0} ataques caen por su "
                       f"cláusula y ninguno sobrevive a eliminarla"
                       if not fallas else " | ".join(fallas)))
    return _cerrar(resultados)


def _con_dimension_anulada(sano: dict, mutacion) -> bool:
    """¿El ataque sigue cayendo con la dimensión derivada eliminada?

    Eliminar la dimensión es pasarle los mapas vacíos: es la mutación que un implementador
    descuidado produciría al borrar la derivación. La función reporta el hallazgo
    `<dimension>_no_derivable`, que NO es uno de los ataques: por eso se lo excluye acá — si se
    contara, el mutante parecería detectado por una cláusula que solo dice que la matriz no cargó.
    """
    copia = copy.deepcopy(sano)
    mutacion(copia)
    clases = {h.clave for h in revisar_dimensiones_derivadas(copia, {}, {})}
    return bool(clases - {"skill_no_derivable", "familia_de_rol_no_derivable"})


def _baseline_sintetico(preregistro: dict, sin_valores: set[str] | None = None) -> str:
    """Un baseline con la tabla normativa que fija el generador, para los modos `-final`.

    Se escribe acá y no se genera con `--generar-baseline` a propósito: ese modo necesita
    observaciones, y lo que estos controles prueban es la **lectura** del documento publicado.
    """
    sin_valores = sin_valores or set()
    filas = []
    for metrica in preregistro["metricas"]:
        ident = metrica["metrica_id"]
        celda = SIN_OBSERVACIONES if ident in sin_valores else "`1.0`"
        adjudicacion = ("la cohorte no cubre esta métrica" if ident in sin_valores
                        else SIN_ADJUDICACION)
        filas.append(f"| `{ident}` | {celda} | {metrica['unidad']} | {metrica['agregacion']} | "
                     f"3 | {adjudicacion} |")
    no_observados = (preregistro.get("cobertura") or {}).get("puntos_no_observados") or []
    sin_observar = "\n".join(f"- `{p}`" for p in no_observados) or "- ninguno"
    return (
        "# Baseline de la fase 0\n\n"
        "## Números publicados\n\n"
        "| métrica | valor | unidad | agregación | muestras | adjudicación |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        + "\n".join(filas) + "\n\n"
        "## Lo que no pudo observarse\n\n" + sin_observar + "\n")


def modo_autotest_promocion(args: argparse.Namespace) -> int:
    del args
    resultados = _controles_del_corpus(("promocion",), CLAUSULAS_DE_PROMOCION,
                                       ("clausulas_de_promocion_ejercidas",))
    sano, corpus, manifest, _, errores = _insumos_del_protocolo()
    if errores:
        return _cerrar(resultados)
    evaluador = manifest["evaluador"]

    # [E] La dirección del umbral y el tratamiento del límite, en las cuatro combinaciones.
    fallas = []
    for caso in evaluador["casos"]:
        umbral = {"metrica_id": "m", "direccion": caso["direccion"], "valor": caso["umbral"],
                  "tratamiento_del_limite": caso["tratamiento"]}
        if _cumple(caso["valor"], umbral) != caso["cumple"]:
            fallas.append(f"`{caso['caso']}`: el evaluador dijo "
                          f"{_cumple(caso['valor'], umbral)} y se esperaba {caso['cumple']}")
    en_el_limite = [c for c in evaluador["casos"] if c["valor"] == c["umbral"]]
    if len({(c["direccion"], c["tratamiento"]) for c in en_el_limite}) != 4:
        fallas.append("el valor límite no se ejerce en las cuatro combinaciones de dirección y "
                      "tratamiento: el campo que decide ahí quedaría sin probar")
    resultados.append(("E", not fallas,
                       f"la dirección y el tratamiento del límite deciden en los "
                       f"{len(evaluador['casos'])} casos, con el valor límite en las cuatro "
                       f"combinaciones" if not fallas else " | ".join(fallas)))

    # [F] La regla de composición, con `todas` y `alguna` y sus dos resultados cada una.
    fallas = []
    for caso in evaluador["composicion"]:
        fase = {"fase_id": caso["caso"], "composicion": caso["composicion"],
                "metricas_obligatorias": [],
                "efecto_de_la_ausencia": "blocked",
                "umbrales": [{"metrica_id": f"m{i}", "direccion": "mayor_o_igual",
                              "valor": 1.0, "tratamiento_del_limite": "inclusivo"}
                             for i, _ in enumerate(caso["cumplen"])]}
        valores = {f"m{i}": (1.0 if ok else 0.0) for i, ok in enumerate(caso["cumplen"])}
        veredicto = evaluar_promocion(fase, valores, la_fase_corrio=True)
        esperado = "promovible" if caso["promueve"] else "no_promovible"
        if veredicto.veredicto != esperado:
            fallas.append(f"`{caso['caso']}`: veredicto `{veredicto.veredicto}` y se esperaba "
                          f"`{esperado}`")
    if len({c["composicion"] for c in evaluador["composicion"]}) != 2:
        fallas.append("la composición no se ejerce en sus dos formas")
    resultados.append(("F", not fallas,
                       f"la composición decide en los {len(evaluador['composicion'])} casos, con "
                       f"`todas` y `alguna` en sus dos resultados"
                       if not fallas else " | ".join(fallas)))

    # [G] `not_evaluated` y `blocked` son veredictos DISTINTOS y no se funden.
    fallas = []
    for caso in evaluador["veredictos_distinguidos"]:
        fase = {"fase_id": caso["caso"], "composicion": "todas",
                "metricas_obligatorias": ["m"],
                "efecto_de_la_ausencia": caso.get("efecto_de_la_ausencia", "blocked"),
                "umbrales": [{"metrica_id": "m", "direccion": "mayor_o_igual", "valor": 1.0,
                              "tratamiento_del_limite": "inclusivo"}]}
        veredicto = evaluar_promocion(fase, {}, la_fase_corrio=caso["la_fase_corrio"])
        if veredicto.veredicto != caso["veredicto"]:
            fallas.append(f"`{caso['caso']}`: veredicto `{veredicto.veredicto}` y se esperaba "
                          f"`{caso['veredicto']}`")
    distinguidos = {c["veredicto"] for c in evaluador["veredictos_distinguidos"]}
    if {"blocked", "not_evaluated"} - distinguidos:
        fallas.append("el corpus no ejerce los dos veredictos: fundirlos declararía bloqueadas a "
                      "las fases que nadie ejecutó")
    # La misma fase, con las mismas métricas ausentes, da veredictos distintos según haya corrido:
    # si diera el mismo, los dos veredictos estarían fundidos y el corpus no lo notaría.
    fase = {"fase_id": "f", "composicion": "todas", "metricas_obligatorias": ["m"],
            "efecto_de_la_ausencia": "blocked",
            "umbrales": [{"metrica_id": "m", "direccion": "mayor_o_igual", "valor": 1.0,
                          "tratamiento_del_limite": "inclusivo"}]}
    if (evaluar_promocion(fase, {}, True).veredicto
            == evaluar_promocion(fase, {}, False).veredicto):
        fallas.append("una fase que corrió y otra que no dieron el mismo veredicto con las mismas "
                      "ausencias: los dos veredictos están fundidos")
    if sorted(VEREDICTOS) != sorted({"promovible", "no_promovible", "blocked", "not_evaluated"}):
        fallas.append(f"el conjunto de veredictos cambió: {VEREDICTOS}")
    resultados.append(("G", not fallas,
                       "`not_evaluated` y `blocked` se distinguen, y la misma ausencia da "
                       "veredictos distintos según la fase haya corrido"
                       if not fallas else " | ".join(fallas)))

    # [H] El modo entero y `--promocion-final` sobre un baseline publicado.
    fallas = []
    with tempfile.TemporaryDirectory(prefix="promocion-") as tmp:
        raiz = Path(tmp)
        ruta_sano = raiz / "sano.json"
        _escribir_json(ruta_sano, sano)
        if _codigo_de_modo(modo_promocion, promocion=str(ruta_sano)) != 0:
            fallas.append("`--promocion` devolvió distinto de 0 sobre el caso sano")
        ruta_mala = raiz / "mala.json"
        _escribir_json(ruta_mala, corpus["variantes"]["pr-obligatoria-sin-umbral"])
        if _codigo_de_modo(modo_promocion, promocion=str(ruta_mala)) == 0:
            fallas.append("`--promocion` devolvió 0 con una métrica obligatoria sin umbral")

        baseline = raiz / "baseline.md"
        baseline.write_text(_baseline_sintetico(sano), encoding="utf-8")
        if _codigo_de_modo(modo_promocion_final, promocion_final=str(baseline),
                           preregistro=str(ruta_sano)) != 0:
            fallas.append("`--promocion-final` devolvió distinto de 0 con todas las obligatorias "
                          "publicadas")
        bloqueado = raiz / "bloqueado.md"
        bloqueado.write_text(_baseline_sintetico(sano, sin_valores={"limpieza-completa"}),
                             encoding="utf-8")
        if _codigo_de_modo(modo_promocion_final, promocion_final=str(bloqueado),
                           preregistro=str(ruta_sano)) == 0:
            fallas.append("`--promocion-final` devolvió 0 con una métrica obligatoria publicada "
                          "sin observaciones: la fase corrió y falta, así que está bloqueada")
    resultados.append(("H", not fallas,
                       "`--promocion` y `--promocion-final` devuelven 0 sobre el caso sano y "
                       "distinto de 0 sobre sus negativos" if not fallas else " | ".join(fallas)))
    return _cerrar(resultados)


# ---------------------------------------------------------------------------------------------
# Modos `--validar-preregistro-congelado`, `--validar-manifest-observaciones`,
# `--autotest-preregistro` y `--autotest-identidad-entorno`.
#
# Las dos fases del ciclo del pre-registro son **dos modos y no dos banderas del mismo**, porque
# corren en momentos donde la misma pregunta tiene respuestas opuestas: la primera pasa cuando no
# hay ninguna observación —es su condición de uso: se corre para poder empezar a medir— y la
# segunda exige que no falte ninguna respecto del manifest. Un solo modo que hiciera las dos cosas
# o rechazaría el árbol antes de la primera corrida, o dejaría pasar un conjunto incompleto al
# final; y una bandera que lo relajara sería la que se pasa sin pensar cuando el conjunto no cierra.
#
# La anterioridad NO se declara: se deriva. El commit que fija el pre-registro lo resuelve Git
# sobre la ruta del archivo, y cada corrida se ordena contra su fecha con el sello de pared que el
# bundle registra para eso —el schema lo dice con todas las letras: «sirve para ordenar la corrida
# contra los commits y nunca para calcular duraciones»—.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_PREREGISTRO = DIR_SCRIPTS / "fixtures-baseline" / "preregistro"
RUTA_PREREGISTRO_SANO = DIR_FIXTURES_PREREGISTRO / "sano.json"
RUTA_CORPUS_PREREGISTRO = DIR_FIXTURES_PREREGISTRO / "casos.json"
RUTA_MANIFEST_PREREGISTRO = DIR_FIXTURES_PREREGISTRO / "manifest.json"

# La ruta del pre-registro dentro del repositorio. El commit de congelamiento se resuelve contra
# ella y no contra la ruta que llegue por la línea de comandos: apuntar el modo a una copia fuera
# del árbol tiene que fallar por «no está versionado», no comprobar el commit de otro archivo.
RUTA_CANONICA_DEL_PREREGISTRO = "scripts/preregistro-fase-0.json"

CLAUSULAS_DEL_CONGELADO = (
    "hash_discordante",
    "congelamiento_no_resoluble",
    "congelamiento_no_es_descendiente_directo",
    "congelamiento_con_cambios_ajenos",
    "corrida_anterior_al_congelamiento",
    "corrida_con_otro_congelamiento",
    "cohorte_vacia",
    "muestras_duplicadas",
)

CLAUSULAS_DEL_MANIFEST = (
    "observacion_con_otro_preregistro",
    "muestra_faltante",
    "muestra_sobrante",
    "cadena_rota",
    "identidad_fuera_de_la_regla",
    "dependencia_de_paso_rota",
    "conjunto_vacio",
    "entorno_divergente_incorporado",
    "seleccion_declarada_fuera_de_su_modo",
)


# --- Fase 1: el pre-registro congelado --------------------------------------------------------

class Congelamiento(NamedTuple):
    """El commit que fija el pre-registro, resuelto por Git y no declarado por nadie."""
    commit: str | None
    fecha: str | None
    padres: tuple[str, ...]
    cambios: tuple[str, ...]
    error: str | None


def _git(repo: Path, *argumentos: str) -> tuple[int, str]:
    return _correr_en(["git", "-C", str(repo), *argumentos], None, dict(os.environ))


def resolver_congelamiento(repo: Path, ruta_en_el_repo: str) -> Congelamiento:
    """El último commit que tocó `ruta_en_el_repo`, con sus padres y su diff contra el primero.

    Se resuelve con plumbing y no se lee de ningún campo del documento (D-18): un pre-registro que
    declarara el SHA del commit que lo contiene pediría otro punto fijo, y uno que lo declarara a
    mano sería exactamente la declaración que este modo existe para no creer.
    """
    codigo, salida = _git(repo, "log", "-1", "--format=%H%x00%cI", "--", ruta_en_el_repo)
    if codigo != 0:
        return Congelamiento(None, None, (), (), f"git no pudo resolver el historial: {salida}")
    if not salida.strip():
        return Congelamiento(None, None, (), (),
                             f"`{ruta_en_el_repo}` no tiene ningún commit que lo fije: un "
                             "pre-registro sin commit no es anterior a nada")
    commit, _, fecha = salida.strip().partition("\0")

    codigo, salida = _git(repo, "rev-list", "--parents", "-n", "1", commit)
    if codigo != 0:
        return Congelamiento(commit, fecha, (), (), f"no se pudieron resolver los padres: {salida}")
    padres = tuple(salida.split()[1:])

    cambios: tuple[str, ...] = ()
    if padres:
        codigo, salida = _git(repo, "diff", "--name-only", padres[0], commit)
        if codigo != 0:
            return Congelamiento(commit, fecha, padres, (),
                                 f"no se pudo resolver el cambio del commit: {salida}")
        cambios = tuple(línea for línea in salida.splitlines() if línea.strip())
    return Congelamiento(commit, fecha, padres, cambios, None)


def revisar_congelamiento(preregistro: dict, congelamiento: Congelamiento,
                          corridas: list[BundleEnDisco]) -> list[Hallazgo]:
    """AC-17 · D-18: hash por contenido, anterioridad demostrable y muestras sin duplicados.

    **No exige observaciones**: con cero corridas, las dos cláusulas de anterioridad se cumplen en
    el vacío, que es el estado en el que este modo se corre —antes de medir—.
    """
    problemas: list[Hallazgo] = []

    declarado = preregistro.get("preregistro_sha256")
    computado = hashlib.sha256(proyeccion_canonica(preregistro)).hexdigest()
    if declarado != computado:
        problemas.append(Hallazgo(
            "hash_discordante",
            f"el documento declara `{declarado}` y su proyección canónica da `{computado}`: el "
            f"identificador por contenido no identifica este contenido"))

    if congelamiento.error is not None:
        problemas.append(Hallazgo("congelamiento_no_resoluble", congelamiento.error))
    else:
        problemas.extend(_revisar_relacion_de_commits(preregistro, congelamiento))
        problemas.extend(_revisar_anterioridad(congelamiento, corridas))

    muestras = (preregistro.get("cohorte") or {}).get("muestras") or []
    if not muestras:
        problemas.append(Hallazgo(
            "cohorte_vacia",
            "la cohorte no declara ninguna muestra: un conjunto vacío satisface en el vacío todo "
            "lo que el manifest compare después"))
    problemas.extend(_revisar_duplicados_de_muestra(muestras))
    return problemas


def _revisar_relacion_de_commits(preregistro: dict,
                                 congelamiento: Congelamiento) -> list[Hallazgo]:
    """D-18: descendiente directo de `code_commit`, con el pre-registro como único cambio."""
    problemas: list[Hallazgo] = []
    code_commit = preregistro.get("code_commit") or ""
    if len(congelamiento.padres) != 1:
        return [Hallazgo(
            "congelamiento_no_es_descendiente_directo",
            f"el commit que fija el pre-registro tiene {len(congelamiento.padres)} padres y tiene "
            f"que tener exactamente uno: `code_commit`")]
    padre = congelamiento.padres[0]
    # Sin `code_commit` la comparación por prefijo se satisface en el vacío —todo SHA empieza con
    # la cadena vacía—, así que un acta que no lo declare pasaría la relación que D-18 exige.
    if not code_commit or not (padre.startswith(code_commit) or code_commit.startswith(padre)):
        problemas.append(Hallazgo(
            "congelamiento_no_es_descendiente_directo",
            f"el commit que fija el pre-registro desciende de `{padre[:12]}` y el acta congela "
            f"`code_commit` `{code_commit}`: entre el árbol medido y el congelamiento hay historia "
            f"que nadie declaró"))
    ajenos = [c for c in congelamiento.cambios if c != RUTA_CANONICA_DEL_PREREGISTRO]
    if ajenos:
        problemas.append(Hallazgo(
            "congelamiento_con_cambios_ajenos",
            f"el commit que fija el pre-registro cambia además {sorted(ajenos)}: el árbol que se "
            f"midió deja de ser el que `code_commit` nombra"))
    if not congelamiento.cambios:
        problemas.append(Hallazgo(
            "congelamiento_con_cambios_ajenos",
            "el commit que fija el pre-registro no cambia el pre-registro: no es el commit que lo "
            "congela"))
    return problemas


def _instante(sello: str | None) -> datetime.datetime | None:
    """Los dos sellos que se comparan vienen en formatos distintos —Git emite `+00:00` y el bundle
    `Z`—, así que se ordenan como instantes y nunca como cadenas: `"…Z" < "…+00:00"` es cierto para
    el mismo momento, y la comparación textual daría «anterior» en todas las corridas."""
    if not sello:
        return None
    try:
        instante = datetime.datetime.fromisoformat(sello)
    except ValueError:
        return None
    if instante.tzinfo is None:
        return instante.replace(tzinfo=datetime.timezone.utc)
    return instante


def _revisar_anterioridad(congelamiento: Congelamiento,
                          corridas: list[BundleEnDisco]) -> list[Hallazgo]:
    """Cada corrida arrancó después del congelamiento, y cita ese mismo commit."""
    problemas: list[Hallazgo] = []
    fijado = _instante(congelamiento.fecha)
    for corrida in corridas:
        if corrida.datos is None:
            continue
        inicio = ((corrida.datos.get("ventana_de_pared_utc") or {}).get("inicio") or "")
        arranque = _instante(inicio)
        if arranque is not None and fijado is not None and arranque < fijado:
            problemas.append(Hallazgo(
                "corrida_anterior_al_congelamiento",
                f"{corrida.directorio}: arrancó en {inicio} y el pre-registro se fijó en "
                f"{congelamiento.fecha}: se midió con una metodología que todavía podía cambiar"))
        declarado = ((corrida.datos.get("identidad_del_entorno") or {})
                     .get("preregistration_commit") or "")
        if declarado and congelamiento.commit and not (
                congelamiento.commit.startswith(declarado)
                or declarado.startswith(congelamiento.commit)):
            problemas.append(Hallazgo(
                "corrida_con_otro_congelamiento",
                f"{corrida.directorio}: declara haber corrido con el pre-registro fijado en "
                f"`{declarado[:12]}` y el que fija este documento es "
                f"`{congelamiento.commit[:12]}`"))
    return problemas


def _revisar_duplicados_de_muestra(muestras: list[dict]) -> list[Hallazgo]:
    """Dos formas de duplicar: el mismo `sample_id`, y el mismo par punto × repetición con otro.

    La segunda es la que sobrevive a una revisión por inspección: los identificadores se ven
    distintos y el producto que el manifest deriva después espera uno solo de los dos.
    """
    problemas: list[Hallazgo] = []
    vistos: set[str] = set()
    pares: dict[tuple[str, int], str] = {}
    for muestra in muestras:
        ident = muestra.get("sample_id")
        if ident in vistos:
            problemas.append(Hallazgo(
                "muestras_duplicadas",
                f"`{ident}` aparece más de una vez en la cohorte"))
        vistos.add(ident)
        par = (muestra.get("punto_de_despacho"), muestra.get("repeticion"))
        if par in pares:
            problemas.append(Hallazgo(
                "muestras_duplicadas",
                f"`{ident}` y `{pares[par]}` son la repetición {par[1]} del mismo punto "
                f"`{par[0]}`: el producto punto × repetición produce una sola"))
            continue
        pares[par] = ident
    return problemas


def modo_validar_preregistro_congelado(args: argparse.Namespace) -> int:
    ruta = Path(getattr(args, "validar_preregistro_congelado"))
    if not ruta.is_absolute():
        ruta = RAIZ / ruta
    preregistro, error = _cargar_json(ruta)
    if error:
        print(f"FALLA  {error}")
        return 1
    if not isinstance(preregistro, dict):
        print(f"FALLA  {ruta} no es un objeto JSON: un pre-registro que no lo sea no tiene "
              f"proyección canónica que hashear")
        return 1

    dir_corridas = Path(getattr(args, "corridas", None) or RUTA_CORRIDAS_FASE_0)
    if not dir_corridas.is_absolute():
        dir_corridas = RAIZ / dir_corridas
    repo = Path(getattr(args, "repo", None) or RAIZ)

    try:
        relativa = ruta.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        relativa = None
    if relativa is None:
        congelamiento = Congelamiento(None, None, (), (),
                                      f"{ruta} está fuera del repositorio {repo}: no hay commit "
                                      "que pueda fijarlo")
    else:
        congelamiento = resolver_congelamiento(repo, relativa)

    corridas = leer_conjunto_de_bundles(dir_corridas)
    problemas = revisar_congelamiento(preregistro, congelamiento, corridas)

    print(f"pre-registro: {ruta}")
    print(f"commit que lo fija: {congelamiento.commit or '∅'} · {congelamiento.fecha or '∅'}")
    print(f"corridas contra las que se ordena: {len(corridas)}")
    for problema in problemas:
        print(f"FALLA  {problema}")
    print()
    if problemas:
        print(f"RESULTADO: FALLA — {len(problemas)} hallazgos")
        return 1
    print("RESULTADO: OK — hash por contenido, anterioridad demostrable y muestras sin duplicados")
    return 0


# --- Fase 2: el manifest de observaciones -----------------------------------------------------

def leer_observaciones(raiz: Path) -> tuple[dict[str, list[dict]], list[str]]:
    """Las observaciones de un directorio, agrupadas por muestra. Una que no parsea es un error y
    no una ausencia: descartarla en silencio la volvería indistinguible de una que nunca existió."""
    por_muestra: dict[str, list[dict]] = {}
    errores: list[str] = []
    if not raiz.is_dir():
        return {}, [f"no existe el directorio de observaciones: {raiz}"]
    for ruta in sorted(raiz.glob("*.json")):
        datos, error = _cargar_json(ruta)
        if error:
            errores.append(f"{ruta.name}: {error}")
            continue
        if not isinstance(datos, dict):
            errores.append(f"{ruta.name}: la observación no es un objeto JSON")
            continue
        por_muestra.setdefault(datos.get("sample_id"), []).append(datos)
    return por_muestra, errores


def revisar_manifest_de_observaciones(preregistro: dict, manifest_intentos: dict,
                                      por_muestra: dict[str, list[dict]],
                                      vocabulario: dict,
                                      bundles: dict[str, dict] | None = None) -> list[Hallazgo]:
    """AC-17 · AC-22bis: cada observación cita el acta, el conjunto coincide y la cadena es
    append-only derivada de la regla congelada, sin descartar los bloqueados (D-12, D-15).

    Los cuatro frentes de la cadena, la identidad y la selección **no se reimplementan**: son los
    mismos de `--autotest-muestras-intentos`, aplicados acá sobre observaciones leídas del disco.
    Dos comprobaciones equivalentes escritas aparte divergen, y la que se relaja es siempre la que
    corre sobre los datos reales.
    """
    problemas: list[Hallazgo] = []
    esperado = preregistro.get("preregistro_sha256")

    todas = [o for observaciones in por_muestra.values() for o in observaciones]
    if not todas:
        problemas.append(Hallazgo(
            "conjunto_vacio",
            "el conjunto no tiene ninguna observación: esta fase se corre sobre lo medido, y un "
            "directorio vacío satisface en el vacío toda comparación que venga después"))

    for observacion in sorted(todas, key=lambda o: str(o.get("observation_id"))):
        citado = observacion.get("preregistro_sha256")
        if citado != esperado:
            problemas.append(Hallazgo(
                "observacion_con_otro_preregistro",
                f"`{observacion.get('observation_id')}` cita el pre-registro `{citado}` y el acta "
                f"es `{esperado}`: se rechaza en vez de incorporarla"))

    # Las observaciones que citan otra acta ya están rechazadas: dejarlas participar del conjunto
    # las haría contar como cobertura de una muestra que nadie midió bajo esta metodología.
    del_acta = {ident: [o for o in observaciones if o.get("preregistro_sha256") == esperado]
                for ident, observaciones in por_muestra.items()}
    del_acta = {ident: observaciones for ident, observaciones in del_acta.items() if observaciones}

    # La **selección por métrica** es el cuarto frente de V31 y no se reparte en las cláusulas de
    # este modo: la comprueba `--autotest-muestras-intentos`, que tiene el corpus con métricas para
    # ejercerla. Que no se reparta no puede volverse silencio: un manifest que la declarara acá
    # dejaría de comprobarse sin que nada se pusiera rojo, así que declararla es un hallazgo.
    if manifest_intentos.get("selecciones_esperadas"):
        problemas.append(Hallazgo(
            "seleccion_declarada_fuera_de_su_modo",
            "el manifest de intentos declara `selecciones_esperadas`, que este modo no aplica: "
            "la política de selección por métrica se comprueba en `--autotest-muestras-intentos`, "
            "y dejarla acá la haría pasar sin evaluarse"))

    frentes = _revisar_muestras_e_intentos(manifest_intentos, preregistro, del_acta, vocabulario)
    problemas.extend(_hallazgos_de_frentes(frentes, preregistro, del_acta))
    problemas.extend(_revisar_dependencias_de_paso(preregistro, del_acta))
    problemas.extend(_revisar_identidad_de_las_corridas(preregistro, del_acta, bundles))
    return problemas


def _revisar_identidad_de_las_corridas(preregistro: dict, por_muestra: dict[str, list[dict]],
                                       bundles: dict[str, dict] | None) -> list[Hallazgo]:
    """La adjudicación de la identidad del entorno, comprobada sobre lo que se recolectó.

    Quien **aplica** la adjudicación es el runner, antes de recolectar; este modo comprueba que la
    haya aplicado. Una divergencia que el acta bloquea no puede haber producido una observación:
    si está en el conjunto, se incorporó una medición que el protocolo no admite, y agregarla es
    exactamente lo que AC-17 prohíbe. Las de `estratificacion` **no** bloquean acá: su efecto es el
    estrato, y ése lo comprueban las latencias.
    """
    if not bundles:
        return []
    problemas: list[Hallazgo] = []
    esperado = preregistro.get("entorno_esperado") or {}
    muestras = {m.get("sample_id"): m for m
                in ((preregistro.get("cohorte") or {}).get("muestras") or [])}
    for observaciones in por_muestra.values():
        for observacion in sorted(observaciones, key=lambda o: str(o.get("observation_id"))):
            run_id = (observacion.get("procedencia") or {}).get("run_id")
            bundle = bundles.get(run_id)
            if bundle is None:
                continue  # sin bundle no hay identidad efectiva que comparar; lo ve `--validar-bundles`
            bloqueos = [d for d in adjudicar_identidad_del_entorno(
                esperado, bundle, muestras.get(observacion.get("sample_id")))
                if d.adjudicacion == "bloqueo"]
            for divergencia in bloqueos:
                problemas.append(Hallazgo(
                    "entorno_divergente_incorporado",
                    f"`{observacion.get('observation_id')}` se incorporó y su corrida diverge en "
                    f"un campo que el acta bloquea — {divergencia}"))
    return problemas


def _hallazgos_de_frentes(frentes: dict[str, list[str]], preregistro: dict,
                          por_muestra: dict[str, list[dict]]) -> list[Hallazgo]:
    """Reparte los cuatro frentes de V31 en las cláusulas de este modo.

    `muestra_faltante` y `muestra_sobrante` se separan porque son fallas distintas: la primera dice
    que algo no se midió y la segunda que se midió algo que el acta no congeló, y una sola cláusula
    para las dos dejaría a la segunda sin negativo propio.
    """
    problemas: list[Hallazgo] = []
    declaradas = {m.get("sample_id") for m
                  in ((preregistro.get("cohorte") or {}).get("muestras") or [])}
    observadas = set(por_muestra)
    for ident in sorted(declaradas - observadas):
        problemas.append(Hallazgo(
            "muestra_faltante",
            f"la muestra `{ident}` está congelada en el acta y no tiene ninguna observación: un "
            f"punto con cero intentos falla en vez de desaparecer de los dos lados"))
    for ident in sorted(observadas - declaradas):
        problemas.append(Hallazgo(
            "muestra_sobrante",
            f"hay observaciones de `{ident}`, que el acta no congela como muestra"))
    for detalle in frentes["muestras"]:
        problemas.append(Hallazgo("muestra_faltante", detalle)
                         if "ausente de la cohorte" in detalle
                         else Hallazgo("muestra_sobrante", detalle))
    problemas.extend(Hallazgo("cadena_rota", d) for d in frentes["cadena"])
    problemas.extend(Hallazgo("identidad_fuera_de_la_regla", d) for d in frentes["identidad"])
    return problemas


def _revisar_dependencias_de_paso(preregistro: dict,
                                  por_muestra: dict[str, list[dict]]) -> list[Hallazgo]:
    """V39: los pasos encadenados conservan su dependencia con las cardinalidades declaradas.

    Una muestra que declara depender de otra (D-17) no se sostiene sola: si la que produce el
    enlace no se midió, la que lo consume mide otra cosa —una sesión fresca en vez de una
    reanudada— y su número entra al baseline como si fuera el pre-registrado.
    """
    problemas: list[Hallazgo] = []
    por_ident = {m.get("sample_id"): m for m
                 in ((preregistro.get("cohorte") or {}).get("muestras") or [])}
    for ident, muestra in sorted(por_ident.items()):
        dependencia = muestra.get("dependencia")
        if not dependencia:
            continue
        de = dependencia.get("de_sample_id")
        if de not in por_ident:
            problemas.append(Hallazgo(
                "dependencia_de_paso_rota",
                f"`{ident}` depende de `{de}`, que el acta no congela como muestra"))
            continue
        if not por_muestra.get(ident):
            continue  # su ausencia ya la reporta `muestra_faltante`
        alimentan = len(por_muestra.get(de) or [])
        cardinalidad = dependencia.get("cardinalidad") or 1
        if alimentan < cardinalidad:
            problemas.append(Hallazgo(
                "dependencia_de_paso_rota",
                f"`{ident}` tiene observaciones y `{de}`, del que depende, aporta {alimentan} de "
                f"las {cardinalidad} que su cardinalidad declara: el paso encadenado se midió sin "
                f"el paso que lo produce"))
    return problemas


def modo_validar_manifest_observaciones(args: argparse.Namespace) -> int:
    dir_observaciones = Path(getattr(args, "validar_manifest_observaciones"))
    if not dir_observaciones.is_absolute():
        dir_observaciones = RAIZ / dir_observaciones
    ruta_acta = Path(getattr(args, "preregistro", None) or RUTA_PREREGISTRO_FASE_0)
    if not ruta_acta.is_absolute():
        ruta_acta = RAIZ / ruta_acta
    ruta_intentos = getattr(args, "intentos", None)

    preregistro, error = _cargar_json(ruta_acta)
    if error:
        print(f"FALLA  pre-registro: {error}")
        return 1
    if ruta_intentos is None:
        print("FALLA  falta `--intentos`: el manifest de intentos esperados es independiente del "
              "conjunto que valida (D-16), y derivarlo de las observaciones sería contarlas sobre "
              "sí mismas")
        return 1
    ruta_intentos = Path(ruta_intentos)
    if not ruta_intentos.is_absolute():
        ruta_intentos = RAIZ / ruta_intentos
    manifest_intentos, error = _cargar_json(ruta_intentos)
    if error:
        print(f"FALLA  manifest de intentos: {error}")
        return 1
    vocabulario, error = _cargar_json(RUTA_VOCABULARIO)
    if error:
        print(f"FALLA  vocabulario: {error}")
        return 1

    dir_bundles = Path(getattr(args, "bundles", None) or RUTA_CORRIDAS_FASE_0)
    if not dir_bundles.is_absolute():
        dir_bundles = RAIZ / dir_bundles
    bundles = {b.datos.get("run_id"): b.datos for b in leer_conjunto_de_bundles(dir_bundles)
               if b.datos is not None}

    por_muestra, errores = leer_observaciones(dir_observaciones)
    for problema in errores:
        print(f"FALLA  {problema}")
    problemas = revisar_manifest_de_observaciones(preregistro, manifest_intentos, por_muestra,
                                                  vocabulario, bundles)

    print(f"observaciones: {dir_observaciones}")
    print(f"corridas contra las que se adjudica la identidad: {len(bundles)}")
    print(f"muestras observadas: {len(por_muestra)} · "
          f"intentos: {sum(len(v) for v in por_muestra.values())}")
    for problema in problemas:
        print(f"FALLA  {problema}")
    print()
    if problemas or errores:
        print(f"RESULTADO: FALLA — {len(problemas) + len(errores)} hallazgos")
        return 1
    print("RESULTADO: OK — cada observación cita el acta, el conjunto coincide y la cadena es "
          "append-only")
    return 0


# --- La identidad del entorno como conjunto cerrado -------------------------------------------
#
# La tabla dice qué hace una divergencia de cada campo, y las dos adjudicaciones son las únicas
# expresables: **agregar registrando la divergencia no existe**. Si existiera, sería la salida
# barata de toda corrida que no cumple el protocolo, y el baseline promediaría mediciones que el
# pre-registro declaró idénticas y no lo son.

ADJUDICACIONES_DE_DIVERGENCIA = ("bloqueo", "estratificacion")


class CampoDeIdentidad(NamedTuple):
    esperado: str          # campo de `entorno_esperado` del pre-registro
    efectivo: str          # campo de `identidad_del_entorno` del bundle, con `.` para anidar
    adjudicacion: str
    porque: str


CORRESPONDENCIA_DE_IDENTIDAD: tuple[CampoDeIdentidad, ...] = (
    CampoDeIdentidad("arbol_limpio_exigido", "arbol_limpio", "bloqueo",
                     "un árbol sucio mide un código que ningún commit nombra"),
    CampoDeIdentidad("matriz_sha256", "matriz_sha256", "bloqueo",
                     "la matriz define los puntos: otra matriz es otra cohorte"),
    CampoDeIdentidad("instrumento_sha256", "instrumento_sha256", "bloqueo",
                     "otro instrumento mide otra cosa, y el número no es comparable ni "
                     "reproducible"),
    CampoDeIdentidad("runner_sha256", "runner_sha256", "bloqueo",
                     "otro runner despacha distinto, y la latencia deja de ser la del protocolo"),
    CampoDeIdentidad("ejecutor_esperado", "ejecutor.perfil_esperado", "bloqueo",
                     "el perfil es lo que el acta congeló: correr con otro es correr otro "
                     "protocolo, no otra instancia del mismo"),
    CampoDeIdentidad("version_cli", "version_cli", "estratificacion",
                     "dos versiones del CLI dan latencias comparables solo dentro de su estrato"),
    CampoDeIdentidad("version_runtime", "version_runtime", "estratificacion",
                     "ídem el runtime: comparable dentro del estrato, no entre estratos"),
    CampoDeIdentidad("hooks", "hooks", "estratificacion",
                     "D-7: dos entornos con hooks distintos producen latencias que el "
                     "pre-registro declara idénticas y no lo son"),
)

# Campos de la identidad efectiva sin contraparte esperada, con quién los comprueba. Están acá para
# que el conjunto sea CERRADO en las dos direcciones: un campo nuevo en cualquiera de los dos
# schemas que nadie adjudique tiene que poner rojo el autotest, no quedarse sin regla en silencio.
SOLO_EFECTIVOS = {
    "code_commit": "lo compara el acta, que congela el mismo campo",
    "preregistration_commit": "lo comprueba `--validar-preregistro-congelado` contra Git (D-18)",
    "eventos_de_intervencion_humana": "derivan el estrato efectivo, que se compara contra el "
                                      "`estrato_esperado` de la muestra",
    "modelo": "es un dato de plataforma: trae su propia adjudicación cuando no se expone",
}

SOLO_ESPERADOS = {
    "transportes_admitidos": "se compara contra el `transporte` del bundle, que no vive dentro de "
                             "la identidad del entorno",
}


class Divergencia(NamedTuple):
    campo: str
    esperado: Any
    efectivo: Any
    adjudicacion: str
    motivo: str

    def __str__(self) -> str:
        return (f"[{self.adjudicacion}] {self.campo}: el acta esperaba {self.esperado!r} y la "
                f"corrida registró {self.efectivo!r} — {self.motivo}")


def _valor_anidado(datos: dict, camino: str) -> Any:
    actual: Any = datos
    for tramo in camino.split("."):
        if not isinstance(actual, dict):
            return None
        actual = actual.get(tramo)
    return actual


def adjudicar_identidad_del_entorno(esperado: dict, bundle: dict,
                                    muestra: dict | None = None) -> list[Divergencia]:
    """Compara la identidad esperada contra la efectiva y adjudica cada divergencia.

    Devuelve divergencias con su adjudicación —`bloqueo` o `estratificacion`— y nunca una tercera:
    lo que AC-17 prohíbe es agregar registrando la divergencia, así que no hay valor de retorno que
    lo exprese. Un campo cuya adjudicación la tabla no declare **no puede llegar acá**: el conjunto
    cerrado se comprueba contra los dos schemas en `--autotest-identidad-entorno`.
    """
    efectivo = bundle.get("identidad_del_entorno") or {}
    divergencias: list[Divergencia] = []

    for campo in CORRESPONDENCIA_DE_IDENTIDAD:
        valor_esperado = esperado.get(campo.esperado)
        valor_efectivo = _valor_anidado(efectivo, campo.efectivo)
        if campo.esperado == "arbol_limpio_exigido":
            # El único par que no se compara por igualdad: el acta declara si EXIGE limpieza, y la
            # corrida declara si lo estaba. Exigir `False` no obliga a ensuciar el árbol.
            if valor_esperado and valor_efectivo is not True:
                divergencias.append(Divergencia(campo.efectivo, "árbol limpio", valor_efectivo,
                                                campo.adjudicacion, campo.porque))
            continue
        if _normalizar_identidad(valor_esperado) != _normalizar_identidad(valor_efectivo):
            divergencias.append(Divergencia(campo.efectivo, valor_esperado, valor_efectivo,
                                            campo.adjudicacion, campo.porque))

    admitidos = esperado.get("transportes_admitidos") or []
    if bundle.get("transporte") not in admitidos:
        divergencias.append(Divergencia(
            "transporte", admitidos, bundle.get("transporte"), "bloqueo",
            "el transporte no está entre los que el acta admite: la muestra mide una vía que la "
            "cohorte no congeló"))

    if muestra is not None and muestra.get("estrato_esperado"):
        efectivo_estrato = derivar_estrato(bundle)
        if efectivo_estrato != muestra["estrato_esperado"]:
            divergencias.append(Divergencia(
                "estrato", muestra["estrato_esperado"], efectivo_estrato, "estratificacion",
                "el estrato efectivo sale de los eventos registrados, y mezclarlo con el esperado "
                "promedia intervención humana con automatización"))

    divergencias.extend(_divergencias_de_plataforma(efectivo))
    return divergencias


def _normalizar_identidad(valor: Any) -> Any:
    """Las listas de la identidad —hooks— son conjuntos: su orden no es un hecho de la corrida."""
    if isinstance(valor, list):
        return sorted(str(v) for v in valor)
    return valor


def _divergencias_de_plataforma(efectivo: dict) -> list[Divergencia]:
    """Los datos que la plataforma puede no exponer traen su adjudicación adentro (D-7).

    El instrumento la **respeta**, no la elige: un dato no expuesto cuya adjudicación no esté en el
    conjunto cerrado se trata como bloqueo, que es la lectura conservadora — la alternativa sería
    seguir midiendo con un dato que nadie sabe cuál es.
    """
    divergencias: list[Divergencia] = []
    candidatos = [("modelo.solicitado", _valor_anidado(efectivo, "modelo.solicitado")),
                  ("modelo.efectivo", _valor_anidado(efectivo, "modelo.efectivo")),
                  ("ejecutor.instancia_efectiva",
                   _valor_anidado(efectivo, "ejecutor.instancia_efectiva"))]
    for campo, dato in candidatos:
        if not isinstance(dato, dict) or dato.get("estado") != "no_expuesto":
            continue
        adjudicacion = dato.get("adjudicacion")
        if adjudicacion not in ADJUDICACIONES_DE_DIVERGENCIA:
            divergencias.append(Divergencia(
                campo, "un dato expuesto, o una adjudicación del conjunto cerrado", adjudicacion,
                "bloqueo",
                "la plataforma no lo expone y el bundle no adjudica qué hacer: se bloquea, que es "
                "lo único que no inventa el valor"))
            continue
        divergencias.append(Divergencia(
            campo, "expuesto", "no expuesto", adjudicacion,
            "la plataforma no lo expone y el acta adjudicó qué hacer con eso"))
    return divergencias


# --- `--autotest-preregistro` -----------------------------------------------------------------
#
# El repositorio de los controles se **siembra**, no se simula: la anterioridad y la relación entre
# los dos commits las resuelve Git, así que un doble del historial probaría el doble. Cada escenario
# es un repo temporal con dos o tres commits reales, y el modo corre sobre él sin saber que es
# sintético.

def con_hash_renovado(preregistro: dict) -> dict:
    """El documento con su `preregistro_sha256` recomputado sobre su propia proyección canónica."""
    copia = copy.deepcopy(preregistro)
    copia["preregistro_sha256"] = hashlib.sha256(proyeccion_canonica(copia)).hexdigest()
    return copia


class RepoSembrado(NamedTuple):
    repo: Path
    preregistro: dict
    ruta: Path
    congelamiento: str
    fecha_de_congelamiento: str


_FECHA_ANCLA = "2026-01-01T00:00:00+00:00"
_FECHA_CONGELAMIENTO = "2026-01-02T00:00:00+00:00"


def _commitear(repo: Path, mensaje: str, fecha: str) -> str:
    entorno = {**os.environ, "GIT_AUTHOR_DATE": fecha, "GIT_COMMITTER_DATE": fecha,
               "GIT_AUTHOR_NAME": "control", "GIT_AUTHOR_EMAIL": "control@local",
               "GIT_COMMITTER_NAME": "control", "GIT_COMMITTER_EMAIL": "control@local"}
    _correr_en(["git", "-C", str(repo), "add", "-A"], None, entorno)
    _correr_en(["git", "-C", str(repo), "commit", "--quiet", "-m", mensaje], None, entorno)
    return _git(repo, "rev-parse", "HEAD")[1].strip()


def sembrar_repo(raiz: Path, preregistro: dict, *, intermedio: bool = False,
                 cambio_ajeno: bool = False, sin_commitear: bool = False,
                 fecha_de_congelamiento: str = _FECHA_CONGELAMIENTO) -> RepoSembrado:
    """Un repo con el ancla, el pre-registro congelado encima y su `code_commit` ya inyectado."""
    repo = raiz / "repo"
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    _correr_en(["git", "init", "--quiet", "-b", "main", str(repo)], None, dict(os.environ))
    (repo / "scripts" / "ancla.txt").write_text("el árbol que se mide\n", encoding="utf-8")
    ancla = _commitear(repo, "ancla", _FECHA_ANCLA)

    if intermedio:
        (repo / "scripts" / "intermedio.txt").write_text("historia que nadie declaró\n",
                                                         encoding="utf-8")
        _commitear(repo, "intermedio", _FECHA_ANCLA)

    congelado = con_hash_renovado({**preregistro, "code_commit": ancla})
    ruta = repo / RUTA_CANONICA_DEL_PREREGISTRO
    _escribir_json(ruta, congelado)
    if cambio_ajeno:
        (repo / "scripts" / "de-paso.txt").write_text("un cambio que viajó con el acta\n",
                                                      encoding="utf-8")
    if sin_commitear:
        return RepoSembrado(repo, congelado, ruta, "", "")
    commit = _commitear(repo, "congela el pre-registro", fecha_de_congelamiento)
    fecha = _git(repo, "log", "-1", "--format=%cI", commit)[1].strip()
    return RepoSembrado(repo, congelado, ruta, commit, fecha)


def _corrida_sintetica(destino: Path, run_id: str, inicio: str, congelamiento: str) -> None:
    """Lo mínimo que las cláusulas de anterioridad leen de una corrida: cuándo arrancó y con qué
    pre-registro dice haber corrido. No es un bundle completo a propósito: este modo ordena
    corridas contra commits, y validarlas contra su contrato es de `--validar-bundles`."""
    (destino / run_id).mkdir(parents=True, exist_ok=True)
    _escribir_json(destino / run_id / "bundle.json", {
        "run_id": run_id,
        "ventana_de_pared_utc": {"inicio": inicio, "fin": inicio},
        "identidad_del_entorno": {"preregistration_commit": congelamiento},
    })


def _codigo_del_congelado(sembrado: RepoSembrado, corridas: Path | None = None) -> int:
    return _codigo_de_modo(modo_validar_preregistro_congelado,
                           validar_preregistro_congelado=str(sembrado.ruta),
                           repo=str(sembrado.repo),
                           corridas=str(corridas) if corridas else str(sembrado.repo / "vacio"))


def _hallazgos_del_congelado(sembrado: RepoSembrado, corridas: Path | None = None) -> list[str]:
    preregistro, _ = _cargar_json(sembrado.ruta)
    congelamiento = resolver_congelamiento(sembrado.repo, RUTA_CANONICA_DEL_PREREGISTRO)
    conjunto = leer_conjunto_de_bundles(corridas) if corridas else []
    return sorted({p.clave for p in revisar_congelamiento(preregistro, congelamiento, conjunto)})


def modo_autotest_preregistro(args: argparse.Namespace) -> int:
    del args
    resultados: list[tuple[str, bool, str]] = []
    sano, error_sano = _cargar_json(RUTA_PREREGISTRO_SANO)
    corpus, error_corpus = _cargar_json(RUTA_CORPUS_PREREGISTRO)
    manifest, error_manifest = _cargar_json(RUTA_MANIFEST_PREREGISTRO)
    vocabulario, error_vocabulario = _cargar_json(RUTA_VOCABULARIO)
    errores = [e for e in (error_sano, error_corpus, error_manifest, error_vocabulario) if e]
    if errores:
        print(f"[A] FALLA  {' | '.join(errores)}")
        return 1

    # [A] Corpus y manifest, en las dos direcciones.
    fallas = []
    del_corpus = set(corpus["casos"])
    del_manifest = {c["caso"] for c in manifest["casos"]}
    if del_corpus != del_manifest:
        fallas.append(f"corpus ↔ manifest: solo en el corpus {sorted(del_corpus - del_manifest)}, "
                      f"solo en el manifest {sorted(del_manifest - del_corpus)}")
    if len(manifest["casos"]) != len(corpus["casos"]):
        fallas.append(f"el corpus tiene {len(corpus['casos'])} casos y el manifest declara "
                      f"{len(manifest['casos'])}")
    resultados.append(("A", not fallas,
                       f"corpus ↔ manifest ({len(del_corpus)} casos)" if not fallas
                       else " | ".join(fallas)))

    # [B] El caso sano de esta task es el de T14 con su hash renovado, y nada más. Sin este
    # control, dos corpus que declaran el mismo pre-registro pueden divergir sin que nadie lo note.
    fallas = []
    de_t14, error = _cargar_json(RUTA_PROTOCOLO_SANO)
    if error:
        fallas.append(f"el pre-registro de T14: {error}")
    else:
        diferencias = _diferencias_de_campo(
            {k: v for k, v in de_t14.items() if k != "preregistro_sha256"},
            {k: v for k, v in sano.items() if k != "preregistro_sha256"})
        if diferencias:
            fallas.append(f"el caso sano difiere del de T14 en más que el hash: {diferencias[:3]}")
        if sano.get("preregistro_sha256") == de_t14.get("preregistro_sha256"):
            fallas.append("el caso sano copió el hash de T14, que no es el de su proyección")
    resultados.append(("B", not fallas,
                       "el caso sano es el pre-registro de T14 con su hash renovado"
                       if not fallas else " | ".join(fallas)))

    ejercidas: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="preregistro-") as tmp:
        raiz = Path(tmp)

        # [C] La fase congelada pasa SIN NINGUNA observación. Es la condición de uso del modo: se
        # corre para poder empezar a medir, cuando todavía no hay nada medido.
        sembrado = sembrar_repo(raiz / "sano", sano)
        vacio = raiz / "sano" / "sin-corridas"
        vacio.mkdir(parents=True, exist_ok=True)
        hallazgos = _hallazgos_del_congelado(sembrado, vacio)
        resultados.append(("C", not hallazgos,
                           "el pre-registro congelado pasa con cero corridas"
                           if not hallazgos else f"cayó por {hallazgos}"))

        # [D] …y la fase del manifest FALLA con cero observaciones. Es el otro lado del mismo
        # hecho: si las dos pasaran en el vacío, un solo modo alcanzaría y esta task no existiría.
        intentos = raiz / "manifest-intentos.json"
        _escribir_json(intentos, manifest["manifest_de_intentos"])
        observaciones = raiz / "observaciones-vacias"
        observaciones.mkdir(parents=True, exist_ok=True)
        acta = raiz / "acta.json"
        _escribir_json(acta, sembrado.preregistro)
        codigo = _codigo_de_modo(modo_validar_manifest_observaciones,
                                 validar_manifest_observaciones=str(observaciones),
                                 preregistro=str(acta), intentos=str(intentos))
        # No alcanza con que el modo falle: con el acta entera, un conjunto vacío cae igual por
        # doce muestras faltantes, así que exigir solo el código de salida dejaría este control
        # verde aunque nadie mirara el vacío. Se exige la cláusula.
        vacio_claves = sorted({p.clave for p in revisar_manifest_de_observaciones(
            sembrado.preregistro, manifest["manifest_de_intentos"], {}, vocabulario)})
        fallas = []
        if codigo == 0:
            fallas.append("el manifest de observaciones devolvió 0 sobre cero observaciones: "
                          "pasa en el vacío")
        if "conjunto_vacio" not in vacio_claves:
            fallas.append(f"el conjunto vacío no cae por `conjunto_vacio` sino por "
                          f"{vacio_claves}: la cláusula no la ejerce nadie")
        resultados.append(("D", not fallas,
                           "el manifest de observaciones falla con el conjunto vacío, y por su "
                           "cláusula" if not fallas else " | ".join(fallas)))

        # [E] Cada caso del corpus cae por SU cláusula y por su motivo.
        fallas = []
        for declarado in manifest["casos"]:
            caso = corpus["casos"][declarado["caso"]]
            claves, detalles = _ejercer_caso(raiz, declarado, caso, sano, manifest, vocabulario)
            if claves is None:
                fallas.append(f"`{declarado['caso']}`: {detalles}")
                continue
            if claves != [declarado["clausula"]]:
                fallas.append(f"`{declarado['caso']}`: cayó por {claves} y se esperaba "
                              f"`{declarado['clausula']}`")
                continue
            if not any(declarado["fragmento"] in d for d in detalles):
                fallas.append(f"`{declarado['caso']}`: cayó por su cláusula pero no por su motivo "
                              f"— se esperaba «{declarado['fragmento']}»")
                continue
            ejercidas.add(declarado["clausula"])
        resultados.append(("E", not fallas,
                           f"los {len(manifest['casos'])} casos caen por su cláusula y por su "
                           f"motivo" if not fallas else " | ".join(fallas[:5])))

        # [F] Los modos enteros: exit 0 sobre el caso sano y distinto de 0 sobre un negativo de
        # cada fase. Los controles de arriba llaman a las funciones; éste, al modo.
        fallas = []
        if _codigo_del_congelado(sembrado, vacio) != 0:
            fallas.append("`--validar-preregistro-congelado` devolvió distinto de 0 sobre el "
                          "caso sano")
        roto = sembrar_repo(raiz / "ajeno", sano, cambio_ajeno=True)
        if _codigo_del_congelado(roto) == 0:
            fallas.append("`--validar-preregistro-congelado` devolvió 0 con un cambio ajeno en el "
                          "commit que congela")
        pobladas, _ = _poblar_observaciones(raiz / "conformes", manifest, sembrado.preregistro)
        codigo = _codigo_de_modo(modo_validar_manifest_observaciones,
                                 validar_manifest_observaciones=str(pobladas),
                                 preregistro=str(acta), intentos=str(intentos))
        if codigo != 0:
            fallas.append("`--validar-manifest-observaciones` devolvió distinto de 0 sobre el "
                          "conjunto conforme")
        codigo = _codigo_de_modo(modo_validar_manifest_observaciones,
                                 validar_manifest_observaciones=str(pobladas),
                                 preregistro=str(acta), intentos=None)
        if codigo == 0:
            fallas.append("`--validar-manifest-observaciones` devolvió 0 sin manifest de "
                          "intentos: derivarlo del conjunto que valida lo cuenta sobre sí mismo")
        # El consumidor de la adjudicación, con su positivo: una corrida conforme no bloquea nada.
        # Sin este control, la comprobación de identidad solo se vería en su negativo, y una que
        # bloqueara siempre daría el mismo rojo.
        corrida = manifest["corrida_conforme_de_la_primera_muestra"]
        con_bundles = raiz / "con-bundles"
        _materializar_bundle(con_bundles, corrida["run_id"], corrida["bundle"])
        conectadas, _ = _poblar_observaciones(raiz / "conectadas", manifest,
                                              sembrado.preregistro,
                                              procedencia={corrida["run_id"]: 0})
        codigo = _codigo_de_modo(modo_validar_manifest_observaciones,
                                 validar_manifest_observaciones=str(conectadas),
                                 preregistro=str(acta), intentos=str(intentos),
                                 bundles=str(con_bundles))
        if codigo != 0:
            fallas.append("`--validar-manifest-observaciones` devolvió distinto de 0 con una "
                          "corrida conforme: la adjudicación de identidad bloquea lo que no diverge")
        resultados.append(("F", not fallas,
                           "los dos modos devuelven 0 sobre lo conforme y distinto de 0 sobre sus "
                           "negativos" if not fallas else " | ".join(fallas)))

    # [G] Cobertura de las cláusulas, acumulada corriendo.
    fallas = []
    cerradas = set(CLAUSULAS_DEL_CONGELADO) | set(CLAUSULAS_DEL_MANIFEST)
    sin_ejercer = sorted(cerradas - ejercidas)
    if sin_ejercer:
        fallas.append(f"cláusulas sin caso que las ponga rojas: {sin_ejercer}")
    inexistentes = sorted(ejercidas - cerradas)
    if inexistentes:
        fallas.append(f"se ejercieron cláusulas fuera del conjunto cerrado: {inexistentes}")
    declaradas = set(manifest["clausulas_del_congelado"]) | set(manifest["clausulas_del_manifest"])
    if declaradas != cerradas:
        fallas.append(f"el manifest declara otras cláusulas que el conjunto cerrado: "
                      f"{sorted(declaradas ^ cerradas)}")
    resultados.append(("G", not fallas,
                       f"las {len(cerradas)} cláusulas tienen quien las ponga rojas, acumulado "
                       f"corriendo" if not fallas else " | ".join(fallas)))
    return _cerrar(resultados)


def _materializar_bundle(destino: Path, run_id: str, bundle: dict) -> None:
    _escribir_json(destino / run_id / "bundle.json", {**bundle, "run_id": run_id})


def _poblar_observaciones(destino: Path, manifest: dict, preregistro: dict,
                          procedencia: dict[str, int] | None = None) -> tuple[Path, list[dict]]:
    """Escribe el conjunto conforme de observaciones que el manifest declara, ya citando el acta.

    `procedencia` mapea `run_id` → índice de la observación que dice haber salido de esa corrida.
    Solo las nombradas la llevan: una observación sin procedencia no tiene identidad efectiva que
    comparar, y darle una inventada probaría el doble.
    """
    destino.mkdir(parents=True, exist_ok=True)
    de_la_corrida = {indice: run_id for run_id, indice in (procedencia or {}).items()}
    escritas: list[dict] = []
    for indice, plantilla in enumerate(manifest["observaciones_conformes"]):
        observacion = {**copy.deepcopy(plantilla),
                       "preregistro_sha256": preregistro["preregistro_sha256"]}
        if indice in de_la_corrida:
            observacion["procedencia"] = {"run_id": de_la_corrida[indice],
                                          "bundle_sha256": "a" * 64}
        _escribir_json(destino / f"{observacion['observation_id']}.json", observacion)
        escritas.append(observacion)
    return destino, escritas


def _preregistro_del_caso(caso: dict, sano: dict) -> dict:
    """El caso sano con los parches que el corpus declara.

    Se parchea en vez de copiar el documento entero por caso: doce muestras transcritas por
    variante divergirían del sano en el primer cambio, y el negativo dejaría de diferenciarse del
    positivo en un solo punto — que es lo único que hace legible por qué cayó.
    """
    preregistro = copy.deepcopy(sano)
    muestras = (preregistro.get("cohorte") or {}).get("muestras") or []
    if caso.get("cohorte_vacia"):
        preregistro["cohorte"]["muestras"] = []
        muestras = preregistro["cohorte"]["muestras"]
    for ident, dependencia in (caso.get("dependencias") or {}).items():
        for muestra in muestras:
            if muestra.get("sample_id") == ident:
                muestra["dependencia"] = dependencia
    for extra in caso.get("muestras_extra") or []:
        muestras.append({**copy.deepcopy(muestras[0]), **extra} if muestras else dict(extra))
    return preregistro


def _ejercer_caso(raiz: Path, declarado: dict, caso: dict, sano: dict, manifest: dict,
                  vocabulario: dict) -> tuple[list[str] | None, Any]:
    """Corre un caso del corpus por la fase que declara y devuelve sus cláusulas y sus detalles."""
    nombre = declarado["caso"]
    if declarado["fase"] == "congelado":
        sembrado = sembrar_repo(raiz / nombre, _preregistro_del_caso(caso, sano),
                                intermedio=caso.get("intermedio", False),
                                cambio_ajeno=caso.get("cambio_ajeno", False),
                                sin_commitear=caso.get("sin_commitear", False),
                                fecha_de_congelamiento=caso.get("fecha_de_congelamiento")
                                or _FECHA_CONGELAMIENTO)
        # Los parches que van DESPUÉS de sembrar: el repo inyecta `code_commit` y renueva el hash,
        # así que atacar cualquiera de los dos antes lo dejaría pisado por el sembrado.
        if caso.get("hash_falseado") or caso.get("code_commit_borrado"):
            documento, _ = _cargar_json(sembrado.ruta)
            if caso.get("hash_falseado"):
                documento["preregistro_sha256"] = caso["hash_falseado"]
            if caso.get("code_commit_borrado"):
                documento.pop("code_commit", None)
                documento = con_hash_renovado(documento)
            _escribir_json(sembrado.ruta, documento)
        corridas = None
        if caso.get("corridas"):
            corridas = raiz / nombre / "corridas"
            for corrida in caso["corridas"]:
                _corrida_sintetica(corridas, corrida["run_id"], corrida["inicio"],
                                   corrida.get("preregistration_commit")
                                   or sembrado.congelamiento)
        documento, error = _cargar_json(sembrado.ruta)
        if error:
            return None, error
        congelamiento = resolver_congelamiento(sembrado.repo, RUTA_CANONICA_DEL_PREREGISTRO)
        problemas = revisar_congelamiento(documento, congelamiento,
                                          leer_conjunto_de_bundles(corridas) if corridas else [])
    elif declarado["fase"] == "manifest":
        preregistro = con_hash_renovado(_preregistro_del_caso(caso, sano))
        intentos = copy.deepcopy(manifest["manifest_de_intentos"])
        intentos.update(caso.get("manifest_de_intentos") or {})
        por_muestra: dict[str, list[dict]] = {}
        for plantilla in caso.get("observaciones", manifest["observaciones_conformes"]):
            observacion = {**copy.deepcopy(plantilla)}
            observacion.setdefault("preregistro_sha256", preregistro["preregistro_sha256"])
            por_muestra.setdefault(observacion.get("sample_id"), []).append(observacion)
        problemas = revisar_manifest_de_observaciones(preregistro, intentos, por_muestra,
                                                      vocabulario, caso.get("bundles"))
    else:
        return None, f"fase desconocida en el manifest: {declarado['fase']!r}"
    return sorted({p.clave for p in problemas}), [p.detalle for p in problemas]


# --- `--autotest-identidad-entorno` -----------------------------------------------------------

def _campos_del_schema(nombre: str, definicion: str) -> set[str]:
    """Los campos que un `$defs` declara. Salen del schema y no se transcriben: el conjunto cerrado
    de AC-17 lo fija el contrato, y una copia acá envejecería sin que nada se pusiera rojo."""
    schema, error = _cargar_json(CONTRATOS_POR_NOMBRE[nombre].ruta)
    if error:
        return set()
    return set((((schema.get("$defs") or {}).get(definicion) or {}).get("properties") or {}))


def modo_autotest_identidad_entorno(args: argparse.Namespace) -> int:
    del args
    resultados: list[tuple[str, bool, str]] = []
    manifest, error = _cargar_json(RUTA_MANIFEST_PREREGISTRO)
    if error:
        print(f"[A] FALLA  manifest: {error}")
        return 1
    identidad = manifest["identidad_del_entorno"]

    # [A] El conjunto es CERRADO en las dos direcciones contra los dos schemas. Un campo nuevo en
    # cualquiera de los dos sin regla de adjudicación pone esto rojo, en vez de quedar sin
    # adjudicar en silencio — que es como una divergencia se «agrega» sin que nadie lo decida.
    fallas = []
    esperados_del_schema = _campos_del_schema("preregistro", "entorno_esperado")
    efectivos_del_schema = _campos_del_schema("bundle-corrida", "identidad_del_entorno")
    esperados_cubiertos = {c.esperado for c in CORRESPONDENCIA_DE_IDENTIDAD} | set(SOLO_ESPERADOS)
    efectivos_cubiertos = ({c.efectivo.split(".")[0] for c in CORRESPONDENCIA_DE_IDENTIDAD}
                           | set(SOLO_EFECTIVOS))
    if esperados_cubiertos != esperados_del_schema:
        fallas.append(f"`entorno_esperado`: sin adjudicar "
                      f"{sorted(esperados_del_schema - esperados_cubiertos)}, adjudicados y "
                      f"ausentes del schema {sorted(esperados_cubiertos - esperados_del_schema)}")
    if efectivos_cubiertos != efectivos_del_schema:
        fallas.append(f"`identidad_del_entorno`: sin adjudicar "
                      f"{sorted(efectivos_del_schema - efectivos_cubiertos)}, adjudicados y "
                      f"ausentes del schema {sorted(efectivos_cubiertos - efectivos_del_schema)}")
    resultados.append(("A", not fallas,
                       f"el conjunto es cerrado contra los dos schemas "
                       f"({len(esperados_del_schema)} esperados, {len(efectivos_del_schema)} "
                       f"efectivos)" if not fallas else " | ".join(fallas)))

    # [B] La tabla de adjudicación coincide con el manifest independiente, campo por campo.
    fallas = []
    declarada = {c["campo"]: c["adjudicacion"] for c in identidad["adjudicacion_por_campo"]}
    nuestra = {c.efectivo: c.adjudicacion for c in CORRESPONDENCIA_DE_IDENTIDAD}
    if declarada != nuestra:
        fallas.append(f"la tabla adjudica {nuestra} y el manifest declara {declarada}")
    fuera = [a for a in nuestra.values() if a not in ADJUDICACIONES_DE_DIVERGENCIA]
    if fuera:
        fallas.append(f"adjudicaciones fuera del conjunto cerrado: {sorted(set(fuera))}")
    resultados.append(("B", not fallas,
                       f"las {len(nuestra)} adjudicaciones coinciden con el manifest y son del "
                       f"conjunto cerrado" if not fallas else " | ".join(fallas)))

    esperado = identidad["entorno_esperado"]
    conforme = identidad["bundle_conforme"]
    muestra = identidad["muestra"]

    # [C] Control positivo: la corrida conforme no diverge en nada.
    divergencias = adjudicar_identidad_del_entorno(esperado, conforme, muestra)
    resultados.append(("C", not divergencias,
                       "la corrida conforme no diverge en ningún campo"
                       if not divergencias else " | ".join(str(d) for d in divergencias[:3])))

    # [D] Cada divergencia, ejercida POR SEPARADO y con su adjudicación. Probar dos juntas dejaría
    # que un bloqueo enmascare la estratificación de la otra.
    fallas = []
    ejercidos: set[str] = set()
    for caso in identidad["divergencias"]:
        bundle = copy.deepcopy(conforme)
        objetivo = bundle["identidad_del_entorno"] if caso["donde"] == "entorno" else bundle
        _fijar_anidado(objetivo, caso["campo"], caso["valor"])
        propia = copy.deepcopy(muestra)
        propia.update(caso.get("muestra") or {})
        divergencias = adjudicar_identidad_del_entorno(esperado, bundle, propia)
        claves = sorted({d.campo for d in divergencias})
        if claves != [caso["esperada"]]:
            fallas.append(f"`{caso['nombre']}`: divergieron {claves} y se esperaba solo "
                          f"`{caso['esperada']}`")
            continue
        if divergencias[0].adjudicacion != caso["adjudicacion"]:
            fallas.append(f"`{caso['nombre']}`: adjudicó `{divergencias[0].adjudicacion}` y se "
                          f"esperaba `{caso['adjudicacion']}`")
            continue
        ejercidos.add(caso["esperada"])
    resultados.append(("D", not fallas,
                       f"las {len(identidad['divergencias'])} divergencias se adjudican por "
                       f"separado" if not fallas else " | ".join(fallas[:5])))

    # [E] Cada campo de la tabla —y los que no tienen contraparte esperada— tiene quien lo ponga
    # divergente. El conjunto se acumula corriendo.
    fallas = []
    comparables = ({c.efectivo for c in CORRESPONDENCIA_DE_IDENTIDAD}
                   | {"transporte", "estrato", "modelo.solicitado", "modelo.efectivo",
                      "ejecutor.instancia_efectiva"})
    sin_ejercer = sorted(comparables - ejercidos)
    if sin_ejercer:
        fallas.append(f"campos sin ninguna divergencia que los ejerza: {sin_ejercer}")
    resultados.append(("E", not fallas,
                       f"los {len(comparables)} campos comparados tienen quien los ponga "
                       f"divergentes" if not fallas else " | ".join(fallas)))

    # [F] «Agregar registrando la divergencia» no es expresable. El mutante escribe esa
    # adjudicación en un dato de plataforma; el instrumento la rechaza y bloquea, que es lo único
    # que no inventa el valor.
    fallas = []
    bundle = copy.deepcopy(conforme)
    _fijar_anidado(bundle["identidad_del_entorno"], "modelo.efectivo",
                   {"estado": "no_expuesto", "adjudicacion": "agregar"})
    divergencias = adjudicar_identidad_del_entorno(esperado, bundle, muestra)
    if [d.adjudicacion for d in divergencias] != ["bloqueo"]:
        fallas.append(f"una adjudicación fuera del conjunto cerrado produjo "
                      f"{[d.adjudicacion for d in divergencias]} en vez de bloquear")
    resultados.append(("F", not fallas,
                       "una adjudicación fuera del conjunto cerrado bloquea, y no se agrega"
                       if not fallas else " | ".join(fallas)))

    # [G] Los mutantes de la tabla: cambiar la adjudicación de un campo o borrar su fila tiene que
    # ponerse rojo. Sin esto, la tabla podría decir cualquier cosa y los controles seguirían verdes.
    fallas = []
    for mutante in identidad["mutantes_de_la_tabla"]:
        tabla = tuple(c for c in CORRESPONDENCIA_DE_IDENTIDAD if c.efectivo != mutante["campo"])
        if mutante["ataque"] == "cambiar_adjudicacion":
            original = next(c for c in CORRESPONDENCIA_DE_IDENTIDAD
                            if c.efectivo == mutante["campo"])
            tabla = tabla + (original._replace(adjudicacion=mutante["nueva"]),)
        elif mutante["ataque"] != "borrar_fila":
            fallas.append(f"`{mutante['nombre']}`: ataque no implementado")
            continue
        if not _la_tabla_mutada_se_ve(tabla, esperado, conforme, muestra, identidad, mutante):
            fallas.append(f"`{mutante['nombre']}`: la tabla mutada no cambia ningún resultado")
    resultados.append(("G", not fallas,
                       f"los {len(identidad['mutantes_de_la_tabla'])} mutantes de la tabla se ven"
                       if not fallas else " | ".join(fallas[:4])))
    return _cerrar(resultados)


def _fijar_anidado(datos: dict, camino: str, valor: Any) -> None:
    tramos = camino.split(".")
    actual = datos
    for tramo in tramos[:-1]:
        actual = actual.setdefault(tramo, {})
    actual[tramos[-1]] = valor


def _la_tabla_mutada_se_ve(tabla: tuple[CampoDeIdentidad, ...], esperado: dict, conforme: dict,
                           muestra: dict, identidad: dict, mutante: dict) -> bool:
    """Corre la divergencia del campo mutado con la tabla alterada y mira si el resultado cambia.

    Se sustituye la tabla global —y se restaura— en vez de parametrizar la función: el ataque tiene
    que caer sobre el mismo camino de código que corre en producción, y una versión de la función
    que aceptara la tabla por parámetro probaría esa versión y no la que se usa.
    """
    global CORRESPONDENCIA_DE_IDENTIDAD
    caso = next((c for c in identidad["divergencias"] if c["esperada"] == mutante["campo"]), None)
    if caso is None:
        return False
    bundle = copy.deepcopy(conforme)
    objetivo = bundle["identidad_del_entorno"] if caso["donde"] == "entorno" else bundle
    _fijar_anidado(objetivo, caso["campo"], caso["valor"])
    antes = adjudicar_identidad_del_entorno(esperado, bundle, muestra)
    original = CORRESPONDENCIA_DE_IDENTIDAD
    try:
        CORRESPONDENCIA_DE_IDENTIDAD = tabla
        despues = adjudicar_identidad_del_entorno(esperado, bundle, muestra)
    finally:
        CORRESPONDENCIA_DE_IDENTIDAD = original
    return ([(d.campo, d.adjudicacion) for d in antes]
            != [(d.campo, d.adjudicacion) for d in despues])


# ---------------------------------------------------------------------------------------------
# Modos `--sanitizar`, `--autotest-sanitizacion` y `--autotest-escaneo`.
#
# AC-41 pide un pipeline **ordenado**, y el orden no es prolijidad: fija sobre qué evidencia se
# calcula el hash. Si `canonicalizacion_y_hash` corre antes de la normalización de rutas o del
# escaneo, el número identifica un **crudo que nunca se versiona**, y el bundle que sí queda en el
# repositorio no es el que ningún hash acredita. Las dos operaciones se aplicarían a evidencias
# distintas sin que nada lo dijera.
#
# El orden canónico **no se transcribe**: sale del enum del contrato de bundle, que es donde está
# congelado. Una copia acá envejecería en silencio, y el modo seguiría verde comparando contra una
# lista que ya no es la del schema.
#
# El escaneo bloquea secretos, credenciales y rutas **absolutas del host**, y no bloquea rutas
# relativas al repositorio: los comandos de las trece recetas y el directorio de trabajo son
# relativos a propósito, así que un escáner que marcara toda ruta haría imposible publicar la
# evidencia que la fase existe para publicar.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_SANITIZACION = DIR_SCRIPTS / "fixtures-baseline" / "sanitizacion"
RUTA_CORPUS_SANITIZACION = DIR_FIXTURES_SANITIZACION / "casos.json"
RUTA_MANIFEST_SANITIZACION = DIR_FIXTURES_SANITIZACION / "manifest.json"

CLAUSULAS_DEL_PIPELINE = (
    "paso_faltante",
    "hash_antes_de_sanitizar",
    "orden_no_canonico",
    "manifest_desordenado",
    "manifest_sha256_discordante",
)

CLAUSULAS_DEL_ESCANEO = (
    "secreto",
    "credencial",
    "ruta_absoluta_del_host",
)


def pasos_canonicos() -> tuple[str, ...]:
    """El pipeline, en orden, leído del enum del contrato de bundle."""
    schema, error = _cargar_json(CONTRATOS_POR_NOMBRE["bundle-corrida"].ruta)
    if error:
        return ()
    return tuple(((schema.get("$defs") or {}).get("enum_paso_de_sanitizacion") or {})
                 .get("enum") or [])


class ReglaDeEscaneo(NamedTuple):
    clave: str
    patron: re.Pattern[str]
    que_prueba: str


# Cada regla busca la **forma** del contenido no publicable, no una lista de valores conocidos: una
# allowlist de secretos concretos solo caza los que ya se filtraron alguna vez.
#
# `credencial` exige el par nombre **y** valor. El nombre solo no basta y no puede bastar: el runner
# nombra `ENGRAM_CLOUD_TOKEN` y compañía al declarar de qué credenciales se retira, y una regla que
# marcara el nombre volvería no publicable justo la evidencia de que la corrida quedó aislada.
REGLAS_DE_ESCANEO: tuple[ReglaDeEscaneo, ...] = (
    ReglaDeEscaneo(
        "secreto",
        re.compile(r"sk-[A-Za-z0-9_\-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}"
                   r"|xox[baprs]-|-----BEGIN [A-Z ]*PRIVATE KEY-----"
                   r"|Bearer\s+[A-Za-z0-9._\-]{20,}"),
        "un token, una clave de API o una clave privada, por su forma"),
    ReglaDeEscaneo(
        "credencial",
        re.compile(r"\b[A-Z][A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL)"
                   r"[A-Z0-9_]*\s*[=:]\s*\S+"),
        "el par nombre=valor de una variable de credencial; el nombre solo NO bloquea"),
    ReglaDeEscaneo(
        "ruta_absoluta_del_host",
        re.compile(r"(?:^|[\s\"'=:(])(?:/Users/|/home/|/root/|/private/|/var/folders/|/tmp/)"
                   r"|(?:^|[\s\"'=])[A-Za-z]:\\\\|file://"),
        "una ruta que solo existe en la máquina que midió, incluida la de Windows y `file://`"),
)


def textos_del_documento(documento: Any, puntero: str = "") -> list[tuple[str, str]]:
    """Cada cadena del documento con su puntero. El escaneo recorre la INSTANCIA y no el schema:
    un campo de texto libre puede llevar cualquier cosa, y es justo donde el contenido no publicable
    entra sin violar ninguna restricción estructural."""
    if isinstance(documento, dict):
        return [par for clave, valor in documento.items()
                for par in textos_del_documento(valor, f"{puntero}/{clave}")]
    if isinstance(documento, list):
        return [par for indice, valor in enumerate(documento)
                for par in textos_del_documento(valor, f"{puntero}/{indice}")]
    if isinstance(documento, str):
        return [(puntero or "/", documento)]
    return []


def escanear(documento: Any) -> list[Hallazgo]:
    """AC-41: lo que no se puede publicar bloquea antes de versionarse."""
    problemas: list[Hallazgo] = []
    for puntero, texto in textos_del_documento(documento):
        for regla in REGLAS_DE_ESCANEO:
            encontrado = regla.patron.search(texto)
            if encontrado is None:
                continue
            problemas.append(Hallazgo(
                regla.clave,
                f"{puntero}: {regla.que_prueba} — «{encontrado.group(0).strip()[:60]}»"))
    return problemas


def manifest_canonico(artefactos: list[dict]) -> bytes:
    """El manifest ordenado por ruta relativa, tamaño y hash de contenido.

    Es el orden que AC-41 pide y también el que hace reproducible el número: dos capturas del mismo
    conjunto en distinto orden de recorrido tienen que dar el mismo `manifest_sha256`, o el hash
    estaría midiendo el orden del sistema de archivos.
    """
    filas = sorted((str(a.get("ruta_relativa", "")), int(a.get("bytes", 0) or 0),
                    str(a.get("sha256", ""))) for a in artefactos)
    return "".join(f"{ruta}\t{tamano}\t{sha}\n" for ruta, tamano, sha in filas).encode("utf-8")


def hash_del_manifest(artefactos: list[dict]) -> str:
    return hashlib.sha256(manifest_canonico(artefactos)).hexdigest()


def revisar_pipeline(bundle: dict) -> list[Hallazgo]:
    """El pipeline declarado contra el canónico, y el manifest contra su hash."""
    problemas: list[Hallazgo] = []
    canonicos = pasos_canonicos()
    aplicado = list((bundle.get("pipeline_de_sanitizacion") or {}).get("orden_aplicado") or [])

    faltan = [paso for paso in canonicos if paso not in aplicado]
    if faltan:
        problemas.append(Hallazgo(
            "paso_faltante",
            f"el pipeline no aplicó {faltan}: un paso que no corrió no se puede declarar hecho por "
            f"el orden de los que sí"))
    elif aplicado != list(canonicos):
        # El desorden que AC-41 nombra tiene clave propia: hashear antes de normalizar rutas o de
        # escanear deja el número identificando un crudo que nunca se versiona. Cualquier otro
        # desorden cae por la cláusula general, y así los dos negativos no se tapan entre sí.
        posicion = {paso: indice for indice, paso in enumerate(aplicado)}
        antes_de_hashear = [paso for paso in ("normalizacion_de_rutas", "validacion_y_escaneo")
                            if posicion.get(paso, -1) > posicion.get("canonicalizacion_y_hash", -1)]
        if antes_de_hashear:
            problemas.append(Hallazgo(
                "hash_antes_de_sanitizar",
                f"`canonicalizacion_y_hash` corrió antes de {antes_de_hashear}: el hash identifica "
                f"un crudo que nunca se versiona, y el bundle que queda en el repositorio no es el "
                f"que ese número acredita"))
        else:
            problemas.append(Hallazgo(
                "orden_no_canonico",
                f"el pipeline declara {aplicado} y el orden canónico del contrato es "
                f"{list(canonicos)}"))

    artefactos = bundle.get("artefactos_producidos") or []
    ordenadas = [(str(a.get("ruta_relativa", "")), int(a.get("bytes", 0) or 0),
                  str(a.get("sha256", ""))) for a in artefactos]
    if ordenadas != sorted(ordenadas):
        problemas.append(Hallazgo(
            "manifest_desordenado",
            "el manifest no está ordenado por ruta relativa, tamaño y hash: el mismo conjunto "
            "capturado en otro orden daría otro número"))

    declarado = (bundle.get("pipeline_de_sanitizacion") or {}).get("manifest_sha256")
    computado = hash_del_manifest(artefactos)
    if declarado != computado:
        problemas.append(Hallazgo(
            "manifest_sha256_discordante",
            f"el bundle declara `{declarado}` y el manifest ordenado da `{computado}`"))
    return problemas


def modo_sanitizar(args: argparse.Namespace) -> int:
    raiz = Path(getattr(args, "sanitizar"))
    if not raiz.is_absolute():
        raiz = RAIZ / raiz
    corridas = leer_conjunto_de_bundles(raiz)
    if not corridas:
        print(f"FALLA  el conjunto no tiene ninguna corrida: {raiz}")
        return 1

    problemas: list[tuple[str, Hallazgo]] = []
    for corrida in corridas:
        if corrida.error:
            print(f"FALLA  {corrida.directorio}: {corrida.error}")
            return 1
        for hallazgo in revisar_pipeline(corrida.datos) + escanear(corrida.datos):
            problemas.append((corrida.directorio, hallazgo))

    print(f"corridas: {len(corridas)} · pipeline canónico: {list(pasos_canonicos())}")
    for directorio, hallazgo in problemas:
        print(f"FALLA  {directorio}: {hallazgo}")
    print()
    if problemas:
        print(f"RESULTADO: FALLA — {len(problemas)} hallazgos")
        return 1
    print("RESULTADO: OK — el pipeline corrió en orden canónico, el hash es el de la evidencia "
          "sanitizada y nada del contenido bloquea su publicación")
    return 0


# El orden del pipeline y el escaneo se registran en `--validar-bundles`; el hash del manifest
# **no**. Los cincuenta bundles de los corpus de T4, T5, T6, T13 y T14 declaran un
# `manifest_sha256` sintético —existen para probar otra cosa—, así que exigirlo ahí los pondría
# rojos por una regla que no existía cuando se escribieron. Es la misma decisión que T13 tomó con
# sus cláusulas de aislamiento, y con el mismo precio: quien quiera ese registro necesita su task y
# su migración de corpus. El hash sí lo exige `--sanitizar`, que es la fila V29.

def _comprobar_orden_del_pipeline(bundles: list[BundleEnDisco], schema: dict) -> list[str]:
    del schema
    fallas: list[str] = []
    for bundle in bundles:
        if bundle.datos is None:
            continue
        fallas += [f"{bundle.directorio}: {h}" for h in revisar_pipeline(bundle.datos)
                   if h.clave in ("paso_faltante", "hash_antes_de_sanitizar", "orden_no_canonico",
                                  "manifest_desordenado")]
    return fallas


def _comprobar_contenido_publicable(bundles: list[BundleEnDisco], schema: dict) -> list[str]:
    del schema
    fallas: list[str] = []
    for bundle in bundles:
        if bundle.datos is None:
            continue
        fallas += [f"{bundle.directorio}: {h}" for h in escanear(bundle.datos)]
    return fallas


registrar_comprobacion_de_bundles(
    "F", "el pipeline de sanitización corrió en el orden canónico del contrato, y el manifest está "
         "ordenado", _comprobar_orden_del_pipeline)
registrar_comprobacion_de_bundles(
    "G", "ninguna cadena del bundle lleva contenido no publicable",
    _comprobar_contenido_publicable)


# --- `--autotest-sanitizacion` y `--autotest-escaneo` -----------------------------------------

def _insumos_de_sanitizacion() -> tuple[dict, dict, list[str]]:
    corpus, e1 = _cargar_json(RUTA_CORPUS_SANITIZACION)
    manifest, e2 = _cargar_json(RUTA_MANIFEST_SANITIZACION)
    return corpus or {}, manifest or {}, [e for e in (e1, e2) if e]


def texto_del_caso(declaracion: dict) -> str:
    """El texto de una entrada del corpus, ensamblado desde sus `partes`.

    **Ninguna cadena no publicable se escribe entera en el corpus.** El corpus vive en `scripts/`,
    que es lo que el propio escaneo recorre: un token de ejemplo escrito completo haría que el
    árbol quedara impublicable por el archivo que existe para probar que eso se detecta. La
    alternativa —exceptuar el corpus del escaneo— es justo la excepción silenciosa que después
    nadie retira, y dejaría al control ciego sobre el único directorio donde ya hubo una.
    """
    if "partes" in declaracion:
        return "".join(declaracion["partes"])
    return declaracion.get("texto", "")


def _bundle_del_caso_de_sanitizacion(caso: dict, sano: dict) -> dict:
    """El caso sano con el parche que el corpus declara, y su hash renovado salvo que el caso lo
    ataque: un negativo del hash que además lo recalculara no atacaría nada."""
    bundle = copy.deepcopy(sano)
    if caso.get("orden_aplicado") is not None:
        bundle["pipeline_de_sanitizacion"]["orden_aplicado"] = caso["orden_aplicado"]
    if caso.get("artefactos_producidos") is not None:
        bundle["artefactos_producidos"] = caso["artefactos_producidos"]
    for puntero, valor in (caso.get("inyecciones") or {}).items():
        _fijar_anidado(bundle, puntero, valor)
    for puntero, partes in (caso.get("inyecciones_partidas") or {}).items():
        _fijar_anidado(bundle, puntero, "".join(partes))
    if caso.get("manifest_sha256_falseado"):
        bundle["pipeline_de_sanitizacion"]["manifest_sha256"] = caso["manifest_sha256_falseado"]
    elif not caso.get("conservar_hash"):
        bundle["pipeline_de_sanitizacion"]["manifest_sha256"] = hash_del_manifest(
            bundle.get("artefactos_producidos") or [])
    return bundle


def modo_autotest_sanitizacion(args: argparse.Namespace) -> int:
    del args
    corpus, manifest, errores = _insumos_de_sanitizacion()
    if errores:
        print(f"[A] FALLA  {' | '.join(errores)}")
        return 1
    sano = corpus["sano"]
    resultados: list[tuple[str, bool, str]] = []

    # [A] Corpus y manifest, en las dos direcciones.
    fallas = []
    del_corpus = set(corpus["casos"])
    del_manifest = {c["caso"] for c in manifest["casos"]}
    if del_corpus != del_manifest:
        fallas.append(f"solo en el corpus {sorted(del_corpus - del_manifest)}, solo en el manifest "
                      f"{sorted(del_manifest - del_corpus)}")
    resultados.append(("A", not fallas,
                       f"corpus ↔ manifest ({len(del_corpus)} casos)" if not fallas
                       else " | ".join(fallas)))

    # [B] El orden canónico sale del contrato y no de una copia. Se compara contra el manifest
    # independiente: si alguien lo transcribiera acá, este control seguiría verde con el schema
    # cambiado, y ése es justo el envejecimiento silencioso que se quiere impedir.
    fallas = []
    if list(pasos_canonicos()) != manifest["orden_canonico"]:
        fallas.append(f"el contrato declara {list(pasos_canonicos())} y el manifest "
                      f"{manifest['orden_canonico']}")
    resultados.append(("B", not fallas,
                       f"el orden canónico son los {len(pasos_canonicos())} pasos del contrato"
                       if not fallas else " | ".join(fallas)))

    # [C] Control positivo: el bundle sano no cae por ninguna cláusula.
    problemas = revisar_pipeline(sano) + escanear(sano)
    resultados.append(("C", not problemas,
                       "el bundle sano pasa el pipeline y el escaneo"
                       if not problemas else " | ".join(str(p) for p in problemas[:3])))

    # [D] Cada caso cae por SU cláusula y por su motivo.
    fallas = []
    ejercidas: set[str] = set()
    for declarado in manifest["casos"]:
        bundle = _bundle_del_caso_de_sanitizacion(corpus["casos"][declarado["caso"]], sano)
        problemas = revisar_pipeline(bundle) + escanear(bundle)
        claves = sorted({p.clave for p in problemas})
        if claves != [declarado["clausula"]]:
            fallas.append(f"`{declarado['caso']}`: cayó por {claves} y se esperaba "
                          f"`{declarado['clausula']}`")
            continue
        if not any(declarado["fragmento"] in p.detalle for p in problemas):
            fallas.append(f"`{declarado['caso']}`: cayó por su cláusula pero no por su motivo — se "
                          f"esperaba «{declarado['fragmento']}»")
            continue
        ejercidas.add(declarado["clausula"])
    resultados.append(("D", not fallas,
                       f"los {len(manifest['casos'])} casos caen por su cláusula y por su motivo"
                       if not fallas else " | ".join(fallas[:5])))

    # [E] El hash se calcula sobre la evidencia SANITIZADA. Se prueba con el hecho que lo
    # distingue: normalizar una ruta cambia el manifest, así que el número de antes y el de después
    # NO pueden coincidir. Un pipeline que hasheara el crudo daría el mismo en los dos.
    fallas = []
    crudo = [{"ruta_relativa": "scripts/salida.txt", "bytes": 12, "sha256": "a" * 64}]
    normalizado = [{"ruta_relativa": "scripts/salida.txt", "bytes": 12, "sha256": "b" * 64}]
    if hash_del_manifest(crudo) == hash_del_manifest(normalizado):
        fallas.append("el hash no cambia cuando cambia el contenido del manifest")
    invertido = list(reversed(sano["artefactos_producidos"]))
    if hash_del_manifest(invertido) != hash_del_manifest(sano["artefactos_producidos"]):
        fallas.append("el hash depende del orden de recorrido: dos capturas del mismo conjunto "
                      "darían números distintos")
    if sano["pipeline_de_sanitizacion"]["manifest_sha256"] != hash_del_manifest(
            sano["artefactos_producidos"]):
        fallas.append("el bundle sano declara un hash que no es el de su manifest ordenado")
    resultados.append(("E", not fallas,
                       "el hash sale del manifest ordenado, cambia con su contenido y no con el "
                       "orden de recorrido" if not fallas else " | ".join(fallas)))

    # [F] El modo entero, con su positivo y su negativo.
    fallas = []
    with tempfile.TemporaryDirectory(prefix="sanitizacion-") as tmp:
        raiz = Path(tmp)
        _materializar_bundle(raiz / "sano", sano["run_id"], sano)
        if _codigo_de_modo(modo_sanitizar, sanitizar=str(raiz / "sano")) != 0:
            fallas.append("`--sanitizar` devolvió distinto de 0 sobre el conjunto sano")
        malo = _bundle_del_caso_de_sanitizacion(corpus["casos"]["c-hash-antes-de-sanitizar"], sano)
        _materializar_bundle(raiz / "malo", malo["run_id"], malo)
        if _codigo_de_modo(modo_sanitizar, sanitizar=str(raiz / "malo")) == 0:
            fallas.append("`--sanitizar` devolvió 0 con el hash calculado antes de sanitizar")
        vacio = raiz / "vacio"
        vacio.mkdir(parents=True, exist_ok=True)
        if _codigo_de_modo(modo_sanitizar, sanitizar=str(vacio)) == 0:
            fallas.append("`--sanitizar` devolvió 0 sobre un directorio sin corridas")
    resultados.append(("F", not fallas,
                       "`--sanitizar` devuelve 0 sobre lo sano y distinto de 0 sobre sus negativos"
                       if not fallas else " | ".join(fallas)))

    # [G] Cobertura de las cláusulas del pipeline, acumulada corriendo.
    fallas = []
    sin_ejercer = sorted(set(CLAUSULAS_DEL_PIPELINE) - ejercidas)
    if sin_ejercer:
        fallas.append(f"cláusulas del pipeline sin caso que las ponga rojas: {sin_ejercer}")
    if sorted(manifest["clausulas_del_pipeline"]) != sorted(CLAUSULAS_DEL_PIPELINE):
        fallas.append("el manifest declara otras cláusulas del pipeline que el conjunto cerrado")
    resultados.append(("G", not fallas,
                       f"las {len(CLAUSULAS_DEL_PIPELINE)} cláusulas del pipeline tienen quien las "
                       f"ponga rojas" if not fallas else " | ".join(fallas)))
    return _cerrar(resultados)


def _negativos_declarados_de_escaneo() -> tuple[list[Path], list[str]]:
    """Los conjuntos de bundles que el manifest de T4 declara como negativos del escaneo.

    La clave `G` no está transcrita en dos lados: es la que `registrar_comprobacion_de_bundles` le
    dio a la comprobación de contenido publicable, y se busca por su texto en el registro. Así,
    renumerar las comprobaciones no deja esta excepción apuntando a otra.
    """
    clave = next((c.clave for c in COMPROBACIONES_DE_BUNDLES
                  if "no publicable" in c.que_prueba), None)
    manifest, error = _cargar_json(RUTA_MANIFEST_BUNDLES)
    if error or clave is None:
        return [], []
    directorios: list[Path] = []
    sin_disparar: list[str] = []
    for declarado in manifest.get("conjuntos") or []:
        if clave not in (declarado.get("claves_esperadas") or []):
            continue
        directorio = DIR_FIXTURES_BUNDLES / "conjuntos" / declarado["conjunto"]
        directorios.append(directorio)
        if not any(escanear(b.datos) for b in leer_conjunto_de_bundles(directorio)
                   if b.datos is not None):
            sin_disparar.append(declarado["conjunto"])
    return directorios, sin_disparar


def modo_autotest_escaneo(args: argparse.Namespace) -> int:
    del args
    corpus, manifest, errores = _insumos_de_sanitizacion()
    if errores:
        print(f"[A] FALLA  {' | '.join(errores)}")
        return 1
    resultados: list[tuple[str, bool, str]] = []
    escaneo = manifest["escaneo"]

    # [A] Las reglas son las del manifest independiente, en las dos direcciones.
    fallas = []
    nuestras = {r.clave for r in REGLAS_DE_ESCANEO}
    declaradas = {r["clave"] for r in escaneo["reglas"]}
    if nuestras != declaradas:
        fallas.append(f"reglas solo en el código {sorted(nuestras - declaradas)}, solo en el "
                      f"manifest {sorted(declaradas - nuestras)}")
    if nuestras != set(CLAUSULAS_DEL_ESCANEO):
        fallas.append(f"las reglas no son el conjunto cerrado: "
                      f"{sorted(nuestras ^ set(CLAUSULAS_DEL_ESCANEO))}")
    resultados.append(("A", not fallas,
                       f"las {len(nuestras)} reglas coinciden con el manifest y con el conjunto "
                       f"cerrado" if not fallas else " | ".join(fallas)))

    # [B] Lo que BLOQUEA, una entrada por regla y cada una violando solo la suya.
    fallas = []
    ejercidas: set[str] = set()
    for caso in escaneo["bloquean"]:
        problemas = escanear({"campo": texto_del_caso(caso)})
        claves = sorted({p.clave for p in problemas})
        if claves != [caso["regla"]]:
            fallas.append(f"`{caso['nombre']}`: cayó por {claves} y se esperaba `{caso['regla']}`")
            continue
        ejercidas.add(caso["regla"])
    resultados.append(("B", not fallas,
                       f"las {len(escaneo['bloquean'])} entradas no publicables bloquean, cada una "
                       f"por su regla" if not fallas else " | ".join(fallas[:5])))

    # [C] Lo que NO bloquea. Es el control que impide el escáner que marca todo: con él, «bloquea
    # todo» pasaría [B] entero y la evidencia que la fase existe para publicar sería impublicable.
    fallas = []
    for caso in escaneo["no_bloquean"]:
        problemas = escanear({"campo": texto_del_caso(caso)})
        if problemas:
            fallas.append(f"`{caso['nombre']}`: bloqueó por {[p.clave for p in problemas]} y no "
                          f"debía — {caso['por_que']}")
    resultados.append(("C", not fallas,
                       f"las {len(escaneo['no_bloquean'])} entradas publicables pasan"
                       if not fallas else " | ".join(fallas[:5])))

    # [D] Sobre el árbol REAL: ninguna de las recetas ni de los corpus de la fase queda bloqueada.
    # Un escáner calibrado solo contra sus propios ejemplos es un corpus verde de autoría propia.
    #
    # Hay UNA excepción y no es silenciosa: el conjunto que pone roja la comprobación de escaneo en
    # `--validar-bundles` tiene que llevar la cadena entera en disco —ese modo lee el archivo, no lo
    # ensambla—, así que sería el único imposible de partir. La lista se **deriva** del manifest de
    # bundles y no se escribe acá: exceptúa exactamente los conjuntos que declaran ejercer esa
    # comprobación, y se exige que cada uno **efectivamente** dispare. Una excepción que dejara de
    # ejercer nada sería una ruta que el escáner ya no mira y nadie notaría.
    fallas = []
    exceptuados, sin_disparar = _negativos_declarados_de_escaneo()
    fallas += [f"el conjunto `{c}` está exceptuado del escaneo y no dispara ninguna regla: la "
               f"excepción dejó de ejercer algo" for c in sin_disparar]
    revisados = 0
    for ruta in sorted(DIR_SCRIPTS.rglob("*.json")):
        if any(ruta.is_relative_to(directorio) for directorio in exceptuados):
            continue
        documento, error = _cargar_json(ruta)
        if error:
            continue
        revisados += 1
        problemas = escanear(documento)
        if problemas:
            fallas.append(f"{ruta.relative_to(RAIZ)}: {problemas[0]}")
    resultados.append(("D", not fallas,
                       f"los {revisados} documentos JSON de scripts/ pasan el escaneo, con "
                       f"{len(exceptuados)} conjunto(s) exceptuado(s) que el manifest declara y "
                       f"que sí disparan" if not fallas else " | ".join(fallas[:4])))

    # [E] El escaneo recorre la INSTANCIA: un secreto en un campo anidado y en un elemento de
    # arreglo se ve igual que en la raíz.
    fallas = []
    anidado = {"a": {"b": [{"c": texto_del_caso(escaneo["bloquean"][0])}]}}
    problemas = escanear(anidado)
    if not problemas:
        fallas.append("un secreto anidado en un arreglo de objetos no se ve")
    elif "/a/b/0/c" not in problemas[0].detalle:
        fallas.append(f"el hallazgo no señala dónde está: {problemas[0].detalle[:80]}")
    resultados.append(("E", not fallas,
                       "el escaneo recorre la instancia entera y señala el puntero"
                       if not fallas else " | ".join(fallas)))

    # [F] La partición del corpus es correcta en las DOS direcciones: ninguna parte suelta dispara
    # una regla —o el árbol quedaría impublicable por el archivo que prueba que eso se detecta— y
    # el texto ensamblado sí. Partir de más lo vería [B]; partir de menos lo ve [D], pero recién
    # cuando ya está escrito en disco: acá se dice por qué, en vez de reportar el archivo entero.
    fallas = []
    partidas = 0
    for caso in escaneo["bloquean"]:
        if "partes" not in caso:
            fallas.append(f"`{caso['nombre']}`: escribe su texto entero en el corpus, que es lo "
                          f"que el escaneo recorre")
            continue
        partidas += 1
        if len(caso["partes"]) < 2:
            fallas.append(f"`{caso['nombre']}`: declara `partes` con un solo elemento, que es el "
                          f"texto entero con otro nombre")
        for indice, parte in enumerate(caso["partes"]):
            problemas = escanear({"parte": parte})
            if problemas:
                fallas.append(f"`{caso['nombre']}`: la parte {indice} dispara "
                              f"{[p.clave for p in problemas]} por sí sola")
    resultados.append(("F", not fallas,
                       f"las {partidas} entradas no publicables viven partidas, y ninguna parte "
                       f"dispara sola" if not fallas else " | ".join(fallas[:5])))

    # [G] Cobertura, acumulada corriendo.
    fallas = []
    sin_ejercer = sorted(set(CLAUSULAS_DEL_ESCANEO) - ejercidas)
    if sin_ejercer:
        fallas.append(f"reglas sin entrada que las ponga rojas: {sin_ejercer}")
    resultados.append(("G", not fallas,
                       f"las {len(CLAUSULAS_DEL_ESCANEO)} reglas tienen quien las ponga rojas"
                       if not fallas else " | ".join(fallas)))
    return _cerrar(resultados)


# ---------------------------------------------------------------------------------------------
# Modos del acto 3, construidos y probados ACÁ (D-20).
#
# `--altas-topologia`, `--integracion`, `--guardas-previas`, `--ledger`, `--seccion-defectos` y sus
# autotests se aplican en el acto 3 —sobre datos que T25, T26 y T27 materializan—, pero se
# construyen en el acto 1 y por una razón dura: el pre-registro congela el hash de este archivo, y
# la cohorte corre con ese commit. Agregarlos después dejaría el árbol final con **otro**
# instrumento, la identidad cerrada de AC-17 quedaría falsa y AC-25 obligaría a renovar el baseline
# acoplado al archivo. Acá se prueban **solo con fixtures sintéticos**; sus datos reales llegan
# después y esas tasks **no tocan este archivo**.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_TOPOLOGIA = DIR_SCRIPTS / "fixtures-baseline" / "topologia"
DIR_FIXTURES_INTEGRACION = DIR_SCRIPTS / "fixtures-baseline" / "integracion"
DIR_FIXTURES_GUARDAS = DIR_SCRIPTS / "fixtures-baseline" / "guardas"
DIR_FIXTURES_LEDGER = DIR_SCRIPTS / "fixtures-baseline" / "ledger"

RUTA_REGISTRO_ARTEFACTOS = "scripts/artefactos-fase-0.json"
RUTA_MANIFIESTO_GUARDAS = "scripts/guardas-fase-0.json"
RUTA_INSTRUCCIONES = "CLAUDE.md"

CLAUSULAS_DE_TOPOLOGIA = (
    "alta_esperada_ausente",
    "alta_no_esperada",
    "identidad_incompleta",
    "base_no_resoluble",
)

CLAUSULAS_DE_INTEGRACION = (
    "unidad_ausente",
    "no_declara_script_propio",
    "momento_ausente",
    "comando_ausente",
    "codigo_sano_ausente",
    "bandera_inexistente",
    "codigo_declarado_falso",
)

CLAUSULAS_DE_GUARDAS_PREVIAS = (
    "guarda_previa_ausente",
    "guarda_previa_alterada",
    "exclusion_previa_ausente",
    "base_no_resoluble",
)

CLAUSULAS_DEL_LEDGER = (
    "fuente_no_declarada",
    "candidato_fuera_del_ledger",
    "entrada_del_ledger_sin_fuente",
    "candidato_sin_adjudicar",
    "despacho_sin_reporte",
    "incorporado_ausente_del_documento",
    "cero_candidatos_sin_declarar",
)

CLAUSULAS_DE_LA_SECCION = (
    "seccion_ausente",
    "seccion_sin_ninguna_rama",
    "incorporado_sin_ubicacion",
    "ubicacion_no_resuelve",
)


# --- `--altas-topologia`: el conjunto previo se DERIVA de `base_commit` ------------------------

def _json_en_commit(repo: Path, sha: str, ruta: str) -> tuple[Any, str | None]:
    """El contenido de un archivo tal como estaba en un commit. Es plumbing y no lectura del disco:
    el conjunto previo tiene que salir del árbol de `base_commit`, no de lo que hoy haya."""
    codigo, salida = _correr_en(["git", "-C", str(repo), "show", f"{sha}:{ruta}"], None,
                               dict(os.environ))
    if codigo != 0:
        return None, f"`{ruta}` en `{sha}`: {salida.splitlines()[0] if salida else 'sin salida'}"
    try:
        return json.loads(salida), None
    except json.JSONDecodeError as exc:
        return None, f"`{ruta}` en `{sha}` no es JSON válido: {exc}"


CAMPOS_DE_UN_ARTEFACTO = ("path", "owner", "dato", "source_status", "versioned")


def revisar_altas_de_topologia(previo: Any, candidato: Any, esperadas: list[dict],
                               error_de_base: str | None) -> list[Hallazgo]:
    """AC-23: las altas del acto, comparadas en las dos direcciones contra las esperadas.

    `--topologia` valida las entradas **presentes** y no conoce la lista: un alta que faltara del
    árbol **y** del registro lo dejaría verde. Acá el conjunto previo se deriva de `base_commit` y
    la diferencia se compara contra un manifest independiente, que es lo único que puede decir que
    falta algo que nadie escribió.
    """
    if error_de_base is not None:
        return [Hallazgo("base_no_resoluble", error_de_base)]
    problemas: list[Hallazgo] = []
    antes = {a.get("path") for a in (previo or {}).get("artefactos") or []}
    ahora = {a.get("path"): a for a in (candidato or {}).get("artefactos") or []}
    altas = {ruta: entrada for ruta, entrada in ahora.items() if ruta not in antes}
    de_esperadas = {e["path"]: e for e in esperadas}

    for ruta in sorted(set(de_esperadas) - set(altas)):
        problemas.append(Hallazgo(
            "alta_esperada_ausente",
            f"`{ruta}` está declarada como alta de este acto y no aparece en el registro"))
    for ruta in sorted(set(altas) - set(de_esperadas)):
        problemas.append(Hallazgo(
            "alta_no_esperada",
            f"`{ruta}` se dio de alta y no está entre las declaradas: un artefacto nuevo sin "
            f"declaración es indistinguible de uno que se coló"))
    for ruta in sorted(set(altas) & set(de_esperadas)):
        faltan = [campo for campo in CAMPOS_DE_UN_ARTEFACTO if not altas[ruta].get(campo)
                  and altas[ruta].get(campo) is not False]
        if faltan:
            problemas.append(Hallazgo(
                "identidad_incompleta",
                f"`{ruta}` se dio de alta sin {faltan}: una entrada sin dueño o sin dato no fija "
                f"ninguna ubicación canónica"))
            continue
        distintos = [campo for campo in ("owner", "dato") if ruta in de_esperadas
                     and de_esperadas[ruta].get(campo) is not None
                     and altas[ruta].get(campo) != de_esperadas[ruta][campo]]
        if distintos:
            problemas.append(Hallazgo(
                "identidad_incompleta",
                f"`{ruta}` se dio de alta con {[(c, altas[ruta].get(c)) for c in distintos]} y se "
                f"esperaba {[(c, de_esperadas[ruta][c]) for c in distintos]}"))
    return problemas


def modo_altas_topologia(args: argparse.Namespace) -> int:
    base = getattr(args, "base", None)
    if not base:
        print("FALLA  falta `--base <sha>`: el conjunto previo se deriva del commit base y no se "
              "escribe a mano, o el modo compararía contra la lista que quien lo corre recuerde")
        return 1
    repo = Path(getattr(args, "repo", None) or RAIZ)
    ruta_esperadas = getattr(args, "esperadas", None) or (
        DIR_FIXTURES_TOPOLOGIA / "altas-esperadas.json")
    esperadas, error = _cargar_json(Path(ruta_esperadas))
    if error:
        print(f"FALLA  altas esperadas: {error}")
        return 1

    previo, error_de_base = _json_en_commit(repo, base, RUTA_REGISTRO_ARTEFACTOS)
    candidato, error_actual = _cargar_json(RAIZ / RUTA_REGISTRO_ARTEFACTOS)
    if error_actual:
        print(f"FALLA  registro candidato: {error_actual}")
        return 1

    problemas = revisar_altas_de_topologia(previo, candidato, esperadas["altas"], error_de_base)
    print(f"base: {base} · esperadas: {len(esperadas['altas'])}")
    for problema in problemas:
        print(f"FALLA  {problema}")
    print()
    if problemas:
        print(f"RESULTADO: FALLA — {len(problemas)} hallazgos")
        return 1
    print(f"RESULTADO: OK — las {len(esperadas['altas'])} altas están registradas con su identidad")
    return 0


# --- `--integracion`: lo declarado en las instrucciones tiene que ser cierto -------------------
#
# El `--integracion` heredado tiene el nombre del otro verificador congelado en una constante y una
# comparación literal (D-8): corre verde hoy y seguiría verde aunque este instrumento nunca se
# documentara. Una fila que no puede ponerse roja. Este modo trae el mismo rigor y lo aplica a su
# propio script.

class UnidadDeIntegracion(NamedTuple):
    texto: str
    comando: str | None
    codigo_sano: int | None


def _unidad_del_instrumento(instrucciones: str, script: str) -> UnidadDeIntegracion | None:
    """La unidad de las instrucciones que habla de este script.

    Unidad es el ítem de lista con sus continuaciones indentadas: las instrucciones envuelven a 100
    columnas, así que buscar por línea partiría la declaración justo donde está el dato.
    """
    unidades: list[str] = []
    actual: list[str] = []
    for linea in instrucciones.splitlines():
        if linea.startswith("- "):
            if actual:
                unidades.append("\n".join(actual))
            actual = [linea]
        elif actual and (linea.startswith(("  ", "\t")) or not linea.strip()):
            actual.append(linea)
        elif actual:
            unidades.append("\n".join(actual))
            actual = []
    if actual:
        unidades.append("\n".join(actual))

    for unidad in unidades:
        if script not in unidad:
            continue
        comando = None
        encontrado = re.search(rf"`(python3 {re.escape(script)}[^`]*)`", unidad)
        if encontrado:
            comando = encontrado.group(1).strip()
        codigo = None
        encontrado = re.search(r"c[óo]digo de salida sano[^0-9]{0,40}(\d+)", unidad,
                               flags=re.IGNORECASE)
        if encontrado:
            codigo = int(encontrado.group(1))
        return UnidadDeIntegracion(unidad, comando, codigo)
    return None


def revisar_integracion(instrucciones: str, script: str,
                        correr: Callable[[str], int | None]) -> list[Hallazgo]:
    """AC-25: la unidad declara script propio, momento, comando y código sano — y es cierta."""
    unidad = _unidad_del_instrumento(instrucciones, script)
    if unidad is None:
        return [Hallazgo("unidad_ausente",
                         f"las instrucciones no tienen ninguna unidad que hable de `{script}`")]
    problemas: list[Hallazgo] = []
    if not re.search(r"script propio", unidad.texto, flags=re.IGNORECASE):
        problemas.append(Hallazgo(
            "no_declara_script_propio",
            "la unidad no declara que es un script propio del repo: sin eso se lee como un modo "
            "agregado a otro verificador, y quien lo corra buscará la bandera donde no está"))
    if not re.search(r"^\s*-\s*Si\b|cuando\b|antes de\b|después de\b|al (tocar|editar|crear)\b",
                     unidad.texto, flags=re.IGNORECASE | re.MULTILINE):
        problemas.append(Hallazgo(
            "momento_ausente",
            "la unidad no dice cuándo hay que correrlo: una guarda sin momento no se corre nunca "
            "o se corre siempre, y las dos cosas la vacían"))
    if unidad.comando is None:
        problemas.append(Hallazgo(
            "comando_ausente",
            f"la unidad no trae el comando exacto entre backticks: `python3 {script} …`"))
    if unidad.codigo_sano is None:
        problemas.append(Hallazgo(
            "codigo_sano_ausente",
            "la unidad no declara cuál es el código de salida sano: sin él, cualquier código se "
            "lee como el esperado"))
    if unidad.comando is None or unidad.codigo_sano is None:
        return problemas

    devuelto = correr(unidad.comando)
    if devuelto is None:
        problemas.append(Hallazgo(
            "bandera_inexistente",
            f"el comando declarado no es invocable: `{unidad.comando}`"))
        return problemas
    if devuelto != unidad.codigo_sano:
        problemas.append(Hallazgo(
            "codigo_declarado_falso",
            f"la unidad declara que el código sano es {unidad.codigo_sano} y `{unidad.comando}` "
            f"devuelve {devuelto}"))
    return problemas


def _correr_comando_declarado(comando: str) -> int | None:
    """Corre el comando de la unidad. Devuelve `None` si la bandera no existe: un modo inexistente
    y un modo que falla no son lo mismo, y el argparse de este archivo los distingue con el 2."""
    partes = comando.split()
    if len(partes) < 2:
        return None
    banderas = [p for p in partes[2:] if p.startswith("--")]
    if not banderas or not any(m.bandera in banderas for m in MODOS):
        return None
    codigo, _ = _correr_en([sys.executable, *partes[1:]], RAIZ, dict(os.environ))
    return codigo


def modo_integracion(args: argparse.Namespace) -> int:
    ruta = Path(getattr(args, "instrucciones", None) or (RAIZ / RUTA_INSTRUCCIONES))
    if not ruta.exists():
        print(f"FALLA  no existe: {ruta}")
        return 1
    script = getattr(args, "script", None) or "scripts/instrumento-baseline.py"
    problemas = revisar_integracion(ruta.read_text(encoding="utf-8"), script,
                                    _correr_comando_declarado)
    print(f"instrucciones: {ruta} · script: {script}")
    for problema in problemas:
        print(f"FALLA  {problema}")
    print()
    if problemas:
        print(f"RESULTADO: FALLA — {len(problemas)} hallazgos")
        return 1
    print("RESULTADO: OK — la unidad declara script propio, momento, comando y código sano, y los "
          "tres son ciertos contra el árbol")
    return 0


# --- `--guardas-previas`: el conjunto previo, derivado de `base_commit` -----------------------

def _identidad_de_guarda(entrada: dict) -> tuple:
    return (entrada.get("id"), entrada.get("script"), tuple(entrada.get("argumentos") or []),
            json.dumps(entrada.get("criterio") or {}, sort_keys=True, ensure_ascii=False))


def revisar_guardas_previas(previo: Any, candidato: Any,
                            error_de_base: str | None) -> list[Hallazgo]:
    """AC-26: las guardas de `base_commit` siguen presentes y sin cambios.

    Se comparan identidad, comando **y** criterio. Con solo el `id`, cambiar el código esperado de
    una guarda de 0 a 4 la dejaría «presente» y sin nada que comprobar.
    """
    if error_de_base is not None:
        return [Hallazgo("base_no_resoluble", error_de_base)]
    problemas: list[Hallazgo] = []
    for clave, campo, ausente, alterada in (
            ("guardas", "guarda", "guarda_previa_ausente", "guarda_previa_alterada"),
            ("exclusiones", "exclusión", "exclusion_previa_ausente", "guarda_previa_alterada")):
        antes = {e.get("id"): e for e in (previo or {}).get(clave) or []}
        ahora = {e.get("id"): e for e in (candidato or {}).get(clave) or []}
        for ident in sorted(set(antes) - set(ahora)):
            problemas.append(Hallazgo(
                ausente,
                f"la {campo} `{ident}` estaba en el manifiesto de la base y ya no está"))
        for ident in sorted(set(antes) & set(ahora)):
            if _identidad_de_guarda(antes[ident]) != _identidad_de_guarda(ahora[ident]):
                problemas.append(Hallazgo(
                    alterada,
                    f"la {campo} `{ident}` cambió de comando o de criterio: "
                    f"{_identidad_de_guarda(antes[ident])[1:]} → "
                    f"{_identidad_de_guarda(ahora[ident])[1:]}"))
    return problemas


def modo_guardas_previas(args: argparse.Namespace) -> int:
    base = getattr(args, "base", None)
    if not base:
        print("FALLA  falta `--base <sha>`: el conjunto previo se deriva del commit base")
        return 1
    repo = Path(getattr(args, "repo", None) or RAIZ)
    previo, error_de_base = _json_en_commit(repo, base, RUTA_MANIFIESTO_GUARDAS)
    candidato, error_actual = _cargar_json(RAIZ / RUTA_MANIFIESTO_GUARDAS)
    if error_actual:
        print(f"FALLA  manifiesto candidato: {error_actual}")
        return 1
    problemas = revisar_guardas_previas(previo, candidato, error_de_base)

    ejecutadas = 0
    if not getattr(args, "sin_ejecutar", False) and not problemas:
        for entrada in (previo or {}).get("guardas") or []:
            comando = [sys.executable, entrada["script"], *(entrada.get("argumentos") or [])]
            codigo, _ = _correr_en(comando, RAIZ, dict(os.environ))
            ejecutadas += 1
            criterio = entrada.get("criterio") or {}
            if criterio.get("tipo") == "codigo_de_salida" and codigo != criterio.get("esperado"):
                problemas.append(Hallazgo(
                    "guarda_previa_alterada",
                    f"la guarda `{entrada['id']}` devuelve {codigo} y su criterio congelado espera "
                    f"{criterio.get('esperado')}"))

    print(f"base: {base} · guardas previas: {len((previo or {}).get('guardas') or [])} · "
          f"ejecutadas: {ejecutadas}")
    for problema in problemas:
        print(f"FALLA  {problema}")
    print()
    if problemas:
        print(f"RESULTADO: FALLA — {len(problemas)} hallazgos")
        return 1
    print("RESULTADO: OK — el conjunto previo sigue presente, sin cambios de comando ni de criterio")
    return 0


# --- `--ledger`: las cuatro fuentes, reconciliadas en las dos direcciones ---------------------
#
# El `--defectos` heredado valida la **forma** del puntero y no lo resuelve contra el árbol, ni sabe
# nada de reconciliación (D-11). Acá el ledger se compara contra cada fuente en las dos
# direcciones y contra el **manifest de despachos**, que es lo único que puede decir que falta un
# reporte que nadie escribió: reconciliar solo «las fuentes que encuentre» deja invisible la
# ausencia.

FUENTES_DEL_LEDGER = (
    "anomalias_del_runner",
    "fallos_de_fixtures",
    "adjudicaciones_de_cohorte",
    "reportes_de_implementacion",
)

ADJUDICACIONES_DEL_LEDGER = ("incorporado", "descartado")


def revisar_ledger(ledger: dict, fuentes: dict, despachos: list[dict],
                   documento: str) -> list[Hallazgo]:
    """AC-24bis: reconciliación bidireccional, adjudicación de cada candidato y captura obligatoria.

    `fuentes` mapea el nombre de cada fuente a la lista de sus candidatos; `despachos`, el manifest
    append-only de ternas `task · actor · intento`. Los dos llegan derivados de afuera: el modo
    reconcilia, no descubre — descubrir sobre el mismo árbol que valida sería contarlo sobre sí
    mismo.
    """
    problemas: list[Hallazgo] = []
    declaradas = {f.get("fuente"): f for f in ledger.get("fuentes") or []}
    for nombre in FUENTES_DEL_LEDGER:
        declarada = declaradas.get(nombre)
        faltan = [campo for campo in ("ruta", "schema", "regla_de_identidad", "momento_de_emision")
                  if not (declarada or {}).get(campo)]
        if declarada is None or faltan:
            problemas.append(Hallazgo(
                "fuente_no_declarada",
                f"la fuente `{nombre}` no está declarada con {faltan or 'ninguno de sus campos'}: "
                f"sin ruta, schema, regla de identidad y momento de emisión, «reconciliar» no "
                f"tiene contra qué"))
    for nombre in sorted(set(declaradas) - set(FUENTES_DEL_LEDGER)):
        problemas.append(Hallazgo(
            "fuente_no_declarada",
            f"`{nombre}` no es una de las cuatro fuentes cerradas: {list(FUENTES_DEL_LEDGER)}"))

    entradas = {c.get("candidate_id"): c for c in ledger.get("candidatos") or []}
    de_las_fuentes: dict[str, str] = {}
    for nombre, candidatos in sorted(fuentes.items()):
        for candidato in candidatos:
            de_las_fuentes[candidato["candidate_id"]] = nombre

    for ident in sorted(set(de_las_fuentes) - set(entradas)):
        problemas.append(Hallazgo(
            "candidato_fuera_del_ledger",
            f"`{ident}` aparece en la fuente `{de_las_fuentes[ident]}` y no está en el ledger"))
    for ident in sorted(set(entradas) - set(de_las_fuentes)):
        problemas.append(Hallazgo(
            "entrada_del_ledger_sin_fuente",
            f"`{ident}` está en el ledger y ninguna fuente lo produjo"))

    for ident in sorted(set(entradas) & set(de_las_fuentes)):
        entrada = entradas[ident]
        if entrada.get("adjudicacion") not in ADJUDICACIONES_DEL_LEDGER or not entrada.get("razon"):
            problemas.append(Hallazgo(
                "candidato_sin_adjudicar",
                f"`{ident}` tiene adjudicación `{entrada.get('adjudicacion')}` y razón "
                f"`{entrada.get('razon')}`: cada candidato se incorpora o se descarta, con su "
                f"razón escrita"))

    problemas.extend(_revisar_captura_obligatoria(ledger, despachos))
    problemas.extend(_revisar_incorporados_en_el_documento(entradas, documento))

    if not entradas and not ledger.get("declara_cero_candidatos"):
        problemas.append(Hallazgo(
            "cero_candidatos_sin_declarar",
            "el ledger no tiene candidatos y no declara explícitamente que no se descubrió "
            "ninguno: la ausencia de hallazgos y la ausencia de búsqueda se ven igual"))
    return problemas


def _revisar_captura_obligatoria(ledger: dict, despachos: list[dict]) -> list[Hallazgo]:
    """Cada terna del manifest tiene su reporte, o su adjudicación explícita de «sin reporte».

    Una task inline no produce reporte delegado, y eso es correcto; lo que no puede es verse igual
    que un reporte que se perdió. Por eso la ausencia se **declara** y no se infiere.
    """
    problemas: list[Hallazgo] = []
    capturados = {(c.get("task"), c.get("actor"), c.get("intento"))
                  for c in ledger.get("capturas") or []}
    sin_reporte = {(c.get("task"), c.get("actor"), c.get("intento"))
                   for c in ledger.get("capturas") or []
                   if c.get("adjudicacion") == "sin_reporte_delegado"}
    for despacho in despachos:
        terna = (despacho.get("task"), despacho.get("actor"), despacho.get("intento"))
        if terna not in capturados:
            problemas.append(Hallazgo(
                "despacho_sin_reporte",
                f"el manifest declara el despacho {terna} y el ledger no lo captura ni lo adjudica "
                f"como «sin reporte delegado»"))
    del sin_reporte  # la adjudicación explícita ya satisface la captura; queda nombrada a propósito
    return problemas


def _revisar_incorporados_en_el_documento(entradas: dict[str, dict],
                                          documento: str) -> list[Hallazgo]:
    return [Hallazgo(
        "incorporado_ausente_del_documento",
        f"`{ident}` está adjudicado como incorporado y no aparece en el inventario del documento")
        for ident, entrada in sorted(entradas.items())
        if entrada.get("adjudicacion") == "incorporado" and ident not in documento]


def modo_ledger(args: argparse.Namespace) -> int:
    ruta = Path(getattr(args, "ledger"))
    if not ruta.is_absolute():
        ruta = RAIZ / ruta
    ledger, error = _cargar_json(ruta)
    if error:
        print(f"FALLA  ledger: {error}")
        return 1
    ruta_fuentes = getattr(args, "fuentes", None)
    if ruta_fuentes is None:
        print("FALLA  falta `--fuentes`: el conjunto de candidatos se deriva de las cuatro fuentes "
              "y no del propio ledger, que es lo que se está validando")
        return 1
    reconciliacion, error = _cargar_json(Path(ruta_fuentes) if Path(ruta_fuentes).is_absolute()
                                         else RAIZ / ruta_fuentes)
    if error:
        print(f"FALLA  fuentes: {error}")
        return 1
    # La forma se comprueba antes de usarla. Un archivo que no la cumple —el propio ledger, por
    # ejemplo, cuya clave `fuentes` es una lista y no un mapa— tiene que reportarse y no reventar:
    # un traceback y un hallazgo salen los dos distinto de 0, y quien lea el código de salida no
    # los distingue.
    if not isinstance(reconciliacion, dict) or not isinstance(
            reconciliacion.get("fuentes"), dict) or not isinstance(
            reconciliacion.get("despachos"), list):
        print(f"FALLA  fuentes: `{ruta_fuentes}` no tiene la forma esperada — un objeto con "
              f"`fuentes` (mapa de nombre a lista de candidatos) y `despachos` (lista de ternas). "
              f"El propio ledger no sirve como fuentes: reconciliarlo contra sí mismo no compara "
              f"nada")
        return 1
    ruta_documento = Path(getattr(args, "documento", None)
                          or "docs/superpowers/specs/2026-08-09-subagentes-perfiles-fase-0.md")
    if not ruta_documento.is_absolute():
        ruta_documento = RAIZ / ruta_documento
    documento = ruta_documento.read_text(encoding="utf-8") if ruta_documento.exists() else ""

    problemas = revisar_ledger(ledger, reconciliacion.get("fuentes") or {},
                               reconciliacion.get("despachos") or [], documento)
    print(f"ledger: {ruta} · candidatos: {len(ledger.get('candidatos') or [])} · "
          f"despachos: {len(reconciliacion.get('despachos') or [])}")
    for problema in problemas:
        print(f"FALLA  {problema}")
    print()
    if problemas:
        print(f"RESULTADO: FALLA — {len(problemas)} hallazgos")
        return 1
    print("RESULTADO: OK — las cuatro fuentes reconcilian en las dos direcciones y cada candidato "
          "está adjudicado")
    return 0


# --- `--seccion-defectos`: la sección se REEMPLAZA, no se borra -------------------------------

TITULO_DE_LA_SECCION = "Los defectos de este flujo"


def revisar_seccion_de_defectos(documento: str, incorporados: list[dict]) -> list[Hallazgo]:
    """AC-24bis: la sección existe por identidad y cubre sus dos ramas.

    La mera ausencia de la frase anterior no satisface nada: borrar «lo que este inventario no va a
    incluir» deja el documento sin decir qué pasó con los defectos del flujo, que es la misma
    omisión con menos texto.
    """
    problemas: list[Hallazgo] = []
    encontrado = re.search(rf"^#+\s+.*{re.escape(TITULO_DE_LA_SECCION)}.*$", documento,
                           flags=re.IGNORECASE | re.MULTILINE)
    if encontrado is None:
        return [Hallazgo(
            "seccion_ausente",
            f"el documento no tiene la sección «{TITULO_DE_LA_SECCION}»: sin ella no dice qué "
            f"trato reciben los defectos de este flujo")]
    cuerpo = documento[encontrado.end():]
    siguiente = re.search(r"^#+\s+", cuerpo, flags=re.MULTILINE)
    cuerpo = cuerpo[:siguiente.start()] if siguiente else cuerpo

    declara_ninguno = re.search(r"no se descubri[óo] ninguno", cuerpo, flags=re.IGNORECASE)
    if not incorporados and not declara_ninguno:
        problemas.append(Hallazgo(
            "seccion_sin_ninguna_rama",
            "la sección no lista ningún defecto incorporado ni declara que no se descubrió "
            "ninguno: las dos ramas tienen que ser explícitas"))
    for incorporado in incorporados:
        ident = incorporado.get("candidate_id")
        if ident not in cuerpo:
            problemas.append(Hallazgo(
                "seccion_sin_ninguna_rama",
                f"`{ident}` está incorporado y no aparece en la sección"))
            continue
        ubicacion = incorporado.get("ubicacion")
        if not ubicacion:
            problemas.append(Hallazgo(
                "incorporado_sin_ubicacion",
                f"`{ident}` entra al inventario sin ubicación: un defecto sin dónde no se puede "
                f"comprobar corregido"))
            continue
        ruta = RAIZ / str(ubicacion).split(":")[0]
        if not ruta.exists():
            problemas.append(Hallazgo(
                "ubicacion_no_resuelve",
                f"`{ident}` apunta a `{ubicacion}`, que no existe en el árbol: la forma del "
                f"puntero es válida y no resuelve, que es el defecto que el modo heredado no ve"))
    return problemas


def modo_seccion_defectos(args: argparse.Namespace) -> int:
    ruta = Path(getattr(args, "seccion_defectos"))
    if not ruta.is_absolute():
        ruta = RAIZ / ruta
    if not ruta.exists():
        print(f"FALLA  no existe: {ruta}")
        return 1
    incorporados: list[dict] = []
    ruta_ledger = getattr(args, "ledger_de_la_seccion", None)
    if ruta_ledger:
        ledger, error = _cargar_json(Path(ruta_ledger) if Path(ruta_ledger).is_absolute()
                                     else RAIZ / ruta_ledger)
        if error:
            print(f"FALLA  ledger: {error}")
            return 1
        incorporados = [c for c in ledger.get("candidatos") or []
                        if c.get("adjudicacion") == "incorporado"]
    problemas = revisar_seccion_de_defectos(ruta.read_text(encoding="utf-8"), incorporados)
    print(f"documento: {ruta} · incorporados: {len(incorporados)}")
    for problema in problemas:
        print(f"FALLA  {problema}")
    print()
    if problemas:
        print(f"RESULTADO: FALLA — {len(problemas)} hallazgos")
        return 1
    print("RESULTADO: OK — la sección existe por identidad y declara el trato real de los defectos")
    return 0


# --- `--autotest-identidad-congelada`: probar que el comparador puede ponerse rojo -------------
#
# **El comparador es Git, no este archivo** (D-23): V55 corre `git cat-file blob …` contra
# `git hash-object …` y compara. Este modo no reimplementa esa comparación —eso sería probar el
# doble—: la **ejecuta** sobre copias mutadas y exige que difieran. Es lo único que puede decir que
# la fila de identidad congelada no es un verde estructural.

ARCHIVOS_CONGELADOS = ("scripts/instrumento-baseline.py", "scripts/runner-cohorte.py")


def _hash_de_git(ruta: Path) -> str | None:
    codigo, salida = _correr_en(["git", "hash-object", str(ruta)], RAIZ, dict(os.environ))
    return salida.strip() if codigo == 0 else None


def modo_autotest_identidad_congelada(args: argparse.Namespace) -> int:
    del args
    resultados: list[tuple[str, bool, str]] = []

    # [A] Los dos archivos congelados existen y Git les da un hash. Sin esto, el resto compararía
    # `None` contra `None` y saldría verde por vacío — y con la lista vacía, el modo entero pasaría
    # sin mirar nada, así que se exige que sean exactamente los que el pre-registro congela.
    fallas = []
    esperados = {"scripts/instrumento-baseline.py", "scripts/runner-cohorte.py"}
    if set(ARCHIVOS_CONGELADOS) != esperados:
        fallas.append(f"los archivos congelados son {sorted(ARCHIVOS_CONGELADOS)} y el "
                      f"pre-registro congela el hash de {sorted(esperados)}")
    originales: dict[str, str] = {}
    for relativa in ARCHIVOS_CONGELADOS:
        hash_actual = _hash_de_git(RAIZ / relativa)
        if hash_actual is None:
            fallas.append(f"`{relativa}`: git no pudo hashearlo")
            continue
        originales[relativa] = hash_actual
    resultados.append(("A", not fallas,
                       f"los {len(originales)} archivos congelados tienen hash de Git"
                       if not fallas else " | ".join(fallas)))

    # [B] Mutilar cada uno por separado cambia SU hash y no el del otro. Por separado a propósito:
    # mutilar los dos juntos dejaría que uno enmascare al otro, y un comparador que solo mirara el
    # primero pasaría igual.
    fallas = []
    with tempfile.TemporaryDirectory(prefix="identidad-congelada-") as tmp:
        for relativa in ARCHIVOS_CONGELADOS:
            if relativa not in originales:
                continue
            copia = Path(tmp) / Path(relativa).name
            copia.write_text((RAIZ / relativa).read_text(encoding="utf-8")
                             + "\n# una línea que el pre-registro no congeló\n", encoding="utf-8")
            mutilado = _hash_de_git(copia)
            if mutilado is None:
                fallas.append(f"`{relativa}`: git no pudo hashear la copia mutilada")
                continue
            if mutilado == originales[relativa]:
                fallas.append(f"`{relativa}`: el hash no cambió al mutilarlo, así que la "
                              f"comprobación de identidad no puede ponerse roja")
            for otro, hash_del_otro in originales.items():
                if otro != relativa and _hash_de_git(RAIZ / otro) != hash_del_otro:
                    fallas.append(f"mutilar `{relativa}` cambió el hash de `{otro}`: los dos no "
                                  f"se comprueban por separado")
    resultados.append(("B", not fallas,
                       f"mutilar cada uno de los {len(originales)} archivos cambia su hash y solo "
                       f"el suyo" if not fallas else " | ".join(fallas)))

    # [C] El comparador es Git y no este archivo: el hash que produce `git hash-object` coincide
    # con el de `git cat-file blob` del mismo contenido. Si este modo calculara el hash por su
    # cuenta, mutilar el propio modo dejaría la comprobación verde — que es el tercer caso que la
    # fila V56 pide.
    fallas = []
    with tempfile.TemporaryDirectory(prefix="identidad-comparador-") as tmp:
        copia = Path(tmp) / "contenido.txt"
        copia.write_text("el mismo contenido\n", encoding="utf-8")
        por_hash_object = _hash_de_git(copia)
        codigo, salida = _correr_en(
            ["git", "hash-object", "--stdin"], RAIZ, dict(os.environ))
        del codigo, salida
        crudo = copia.read_bytes()
        esperado = hashlib.sha1(b"blob %d\0" % len(crudo) + crudo).hexdigest()  # noqa: S324
        if por_hash_object != esperado:
            fallas.append(f"`git hash-object` da {por_hash_object} y el formato de objeto de Git "
                          f"da {esperado}: el comparador no es el que la fila declara")
    resultados.append(("C", not fallas,
                       "el hash es el del objeto de Git, no uno propio de este archivo"
                       if not fallas else " | ".join(fallas)))
    return _cerrar(resultados)


# --- `--autotest-integracion` -----------------------------------------------------------------

def modo_autotest_integracion(args: argparse.Namespace) -> int:
    del args
    corpus, error_corpus = _cargar_json(DIR_FIXTURES_INTEGRACION / "casos.json")
    manifest, error_manifest = _cargar_json(DIR_FIXTURES_INTEGRACION / "manifest.json")
    if error_corpus or error_manifest:
        print(f"[A] FALLA  {error_corpus or ''} {error_manifest or ''}".strip())
        return 1
    resultados: list[tuple[str, bool, str]] = []
    script = manifest["script"]

    # [A] Corpus y manifest, en las dos direcciones.
    fallas = []
    if set(corpus["casos"]) != {c["caso"] for c in manifest["casos"]}:
        fallas.append(f"solo en el corpus "
                      f"{sorted(set(corpus['casos']) - {c['caso'] for c in manifest['casos']})}, "
                      f"solo en el manifest "
                      f"{sorted({c['caso'] for c in manifest['casos']} - set(corpus['casos']))}")
    resultados.append(("A", not fallas,
                       f"corpus ↔ manifest ({len(corpus['casos'])} casos)" if not fallas
                       else " | ".join(fallas)))

    # Los casos declaran qué devuelve el comando: el modo real lo ejecuta, y el control necesita
    # decidirlo para poder ejercer `bandera_inexistente` y `codigo_declarado_falso` sin depender de
    # que exista un script que devuelva justo eso.
    def correr_falso(devuelve: int | None) -> Callable[[str], int | None]:
        return lambda comando: devuelve

    # [B] Control positivo: la unidad conforme pasa.
    problemas = revisar_integracion(corpus["conforme"], script, correr_falso(0))
    resultados.append(("B", not problemas,
                       "la unidad conforme declara script propio, momento, comando y código sano"
                       if not problemas else " | ".join(str(p) for p in problemas[:3])))

    # [C] Cada caso cae por SU cláusula y por su motivo.
    fallas = []
    ejercidas: set[str] = set()
    for declarado in manifest["casos"]:
        caso = corpus["casos"][declarado["caso"]]
        texto = caso.get("instrucciones", corpus["conforme"])
        problemas = revisar_integracion(texto, script, correr_falso(caso.get("devuelve", 0)))
        claves = sorted({p.clave for p in problemas})
        if claves != [declarado["clausula"]]:
            fallas.append(f"`{declarado['caso']}`: cayó por {claves} y se esperaba "
                          f"`{declarado['clausula']}`")
            continue
        if not any(declarado["fragmento"] in p.detalle for p in problemas):
            fallas.append(f"`{declarado['caso']}`: cayó por su cláusula y no por su motivo")
            continue
        ejercidas.add(declarado["clausula"])
    resultados.append(("C", not fallas,
                       f"los {len(manifest['casos'])} casos caen por su cláusula y por su motivo"
                       if not fallas else " | ".join(fallas[:5])))

    # [D] La unidad se lee ENTERA, con sus continuaciones indentadas. Las instrucciones envuelven a
    # ~100 columnas, así que un lector por línea partiría la declaración justo donde está el dato:
    # el caso conforme trae el comando en una línea distinta de la del script.
    fallas = []
    unidad = _unidad_del_instrumento(corpus["conforme"], script)
    if unidad is None or unidad.comando is None or unidad.codigo_sano is None:
        fallas.append("la unidad conforme no se lee completa: el comando o el código quedaron "
                      "fuera de la unidad")
    elif "\n" not in unidad.texto:
        fallas.append("la unidad conforme del corpus cabe en una línea, así que este control no "
                      "prueba nada sobre el envoltorio")
    resultados.append(("D", not fallas,
                       "la unidad se lee entera, con sus continuaciones indentadas"
                       if not fallas else " | ".join(fallas)))

    # [E] El modo entero contra un archivo real, con su positivo y su negativo.
    fallas = []
    with tempfile.TemporaryDirectory(prefix="integracion-") as tmp:
        bueno = Path(tmp) / "CONFORME.md"
        bueno.write_text(corpus["conforme"], encoding="utf-8")
        # El comando del corpus conforme apunta a un modo REAL de este archivo, así que el modo
        # entero lo ejecuta de verdad: si el comando fuera inventado, este control probaría el
        # doble en vez del instrumento.
        if _codigo_de_modo(modo_integracion, integracion=True, instrucciones=str(bueno),
                           script=script) != 0:
            fallas.append("`--integracion` devolvió distinto de 0 sobre la unidad conforme")
        malo = Path(tmp) / "SIN-UNIDAD.md"
        malo.write_text("- Una instrucción cualquiera que no habla del instrumento.\n",
                        encoding="utf-8")
        if _codigo_de_modo(modo_integracion, integracion=True, instrucciones=str(malo),
                           script=script) == 0:
            fallas.append("`--integracion` devolvió 0 sin ninguna unidad que hable del script")
    resultados.append(("E", not fallas,
                       "`--integracion` devuelve 0 sobre la unidad conforme —ejecutando su comando "
                       "real— y distinto de 0 sin unidad" if not fallas else " | ".join(fallas)))

    # [F] Cobertura, acumulada corriendo.
    fallas = []
    sin_ejercer = sorted(set(CLAUSULAS_DE_INTEGRACION) - ejercidas)
    if sin_ejercer:
        fallas.append(f"cláusulas sin caso que las ponga rojas: {sin_ejercer}")
    resultados.append(("F", not fallas,
                       f"las {len(CLAUSULAS_DE_INTEGRACION)} cláusulas tienen quien las ponga rojas"
                       if not fallas else " | ".join(fallas)))
    return _cerrar(resultados)


# --- `--autotest-guardas-previas`: cubre los DOS modos que derivan de `base_commit` -----------
#
# `--guardas-previas` y `--altas-topologia` comparten mecanismo —resolver el conjunto previo con
# plumbing sobre un commit— y comparten el modo de fallar: si la base no resuelve, los dos
# compararían contra un conjunto vacío y saldrían verdes. Se prueban juntos y sobre repos
# **sembrados** con commits reales, por lo mismo que en T15: un doble del historial probaría el
# doble.

def sembrar_repo_con_registros(raiz: Path, previo: dict[str, Any],
                               candidato: dict[str, Any]) -> Path:
    """Un repo con un commit base que trae `previo` y un HEAD que trae `candidato`."""
    repo = raiz / "repo"
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    _correr_en(["git", "init", "--quiet", "-b", "main", str(repo)], None, dict(os.environ))
    for ruta, datos in previo.items():
        _escribir_json(repo / ruta, datos)
    _commitear(repo, "base", _FECHA_ANCLA)
    for ruta, datos in candidato.items():
        _escribir_json(repo / ruta, datos)
    _commitear(repo, "candidato", _FECHA_CONGELAMIENTO)
    return repo


def modo_autotest_guardas_previas(args: argparse.Namespace) -> int:
    del args
    corpus, error_corpus = _cargar_json(DIR_FIXTURES_GUARDAS / "casos.json")
    manifest, error_manifest = _cargar_json(DIR_FIXTURES_GUARDAS / "manifest.json")
    topologia, error_topologia = _cargar_json(DIR_FIXTURES_TOPOLOGIA / "casos.json")
    if error_corpus or error_manifest or error_topologia:
        print(f"[A] FALLA  {error_corpus or ''} {error_manifest or ''} "
              f"{error_topologia or ''}".strip())
        return 1
    resultados: list[tuple[str, bool, str]] = []

    # [A] Corpus y manifest, en las dos direcciones, para los dos modos.
    fallas = []
    del_corpus = set(corpus["casos"]) | set(topologia["casos"])
    del_manifest = {c["caso"] for c in manifest["casos"]}
    if del_corpus != del_manifest:
        fallas.append(f"solo en los corpus {sorted(del_corpus - del_manifest)}, solo en el "
                      f"manifest {sorted(del_manifest - del_corpus)}")
    resultados.append(("A", not fallas,
                       f"corpus ↔ manifest ({len(del_corpus)} casos entre los dos modos)"
                       if not fallas else " | ".join(fallas)))

    # [B] Control positivo de los dos: sin cambios respecto de la base, y con las altas declaradas.
    fallas = []
    problemas = revisar_guardas_previas(corpus["previo"], corpus["candidato_conforme"], None)
    if problemas:
        fallas.append(f"`--guardas-previas` bloqueó el candidato conforme: "
                      f"{[str(p) for p in problemas[:2]]}")
    problemas = revisar_altas_de_topologia(topologia["previo"], topologia["candidato_conforme"],
                                           topologia["altas_esperadas"], None)
    if problemas:
        fallas.append(f"`--altas-topologia` bloqueó el candidato conforme: "
                      f"{[str(p) for p in problemas[:2]]}")
    resultados.append(("B", not fallas,
                       "los dos modos pasan sobre su candidato conforme"
                       if not fallas else " | ".join(fallas)))

    # [C] Cada caso cae por SU cláusula y por su motivo.
    fallas = []
    ejercidas: set[str] = set()
    for declarado in manifest["casos"]:
        if declarado["modo"] == "guardas":
            caso = corpus["casos"][declarado["caso"]]
            problemas = revisar_guardas_previas(
                caso.get("previo", corpus["previo"]),
                caso.get("candidato", corpus["candidato_conforme"]),
                caso.get("error_de_base"))
        else:
            caso = topologia["casos"][declarado["caso"]]
            problemas = revisar_altas_de_topologia(
                caso.get("previo", topologia["previo"]),
                caso.get("candidato", topologia["candidato_conforme"]),
                caso.get("altas_esperadas", topologia["altas_esperadas"]),
                caso.get("error_de_base"))
        claves = sorted({p.clave for p in problemas})
        if claves != [declarado["clausula"]]:
            fallas.append(f"`{declarado['caso']}`: cayó por {claves} y se esperaba "
                          f"`{declarado['clausula']}`")
            continue
        if not any(declarado["fragmento"] in p.detalle for p in problemas):
            fallas.append(f"`{declarado['caso']}`: cayó por su cláusula y no por su motivo")
            continue
        ejercidas.add(declarado["clausula"])
    resultados.append(("C", not fallas,
                       f"los {len(manifest['casos'])} casos caen por su cláusula y por su motivo"
                       if not fallas else " | ".join(fallas[:5])))

    # [D] Los dos modos sobre un repo SEMBRADO, resolviendo el conjunto previo con Git. Es lo que
    # separa «la función compara dos dicts» de «el modo deriva el previo del commit base».
    fallas = []
    with tempfile.TemporaryDirectory(prefix="guardas-previas-") as tmp:
        repo = sembrar_repo_con_registros(
            Path(tmp),
            {RUTA_MANIFIESTO_GUARDAS: corpus["previo"],
             RUTA_REGISTRO_ARTEFACTOS: topologia["previo"]},
            {RUTA_MANIFIESTO_GUARDAS: corpus["candidato_conforme"],
             RUTA_REGISTRO_ARTEFACTOS: topologia["candidato_conforme"]})
        base = _git(repo, "rev-parse", "HEAD~1")[1].strip()
        recuperado, error = _json_en_commit(repo, base, RUTA_MANIFIESTO_GUARDAS)
        if error or recuperado != corpus["previo"]:
            fallas.append(f"el manifiesto previo no se recuperó del commit base: {error or 'difiere'}")
        _, error = _json_en_commit(repo, "0000000000000000000000000000000000000000",
                                   RUTA_MANIFIESTO_GUARDAS)
        if error is None:
            fallas.append("un commit inexistente resolvió sin error: la base no resoluble tiene "
                          "que bloquear, no comparar contra el vacío")
    resultados.append(("D", not fallas,
                       "el conjunto previo se deriva del commit base con plumbing, y una base que "
                       "no resuelve bloquea" if not fallas else " | ".join(fallas)))

    # [E] Los modos enteros exigen `--base`, y **por esa causa**. No alcanza con que fallen: sin
    # repo, o con un registro ausente, fallarían igual por otra razón y el control quedaría verde
    # aunque nadie exigiera el argumento. Se mira el mensaje.
    fallas = []
    for nombre, handler, destino in (("--guardas-previas", modo_guardas_previas, "guardas_previas"),
                                     ("--altas-topologia", modo_altas_topologia,
                                      "altas_topologia")):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = handler(argparse.Namespace(**{destino: True, "base": None}))
        if codigo == 0:
            fallas.append(f"`{nombre}` devolvió 0 sin `--base`")
        elif "falta `--base" not in salida.getvalue():
            fallas.append(f"`{nombre}` falló sin `--base` pero por otra causa: "
                          f"{salida.getvalue().strip().splitlines()[0][:80] if salida.getvalue() else '(sin salida)'}")
    resultados.append(("E", not fallas,
                       "los dos modos exigen `--base`, y fallan por esa causa: sin él no hay "
                       "conjunto previo que derivar" if not fallas else " | ".join(fallas)))

    # [F] Cobertura de las cláusulas de los dos modos, acumulada corriendo.
    fallas = []
    cerradas = set(CLAUSULAS_DE_GUARDAS_PREVIAS) | set(CLAUSULAS_DE_TOPOLOGIA)
    sin_ejercer = sorted(cerradas - ejercidas)
    if sin_ejercer:
        fallas.append(f"cláusulas sin caso que las ponga rojas: {sin_ejercer}")
    resultados.append(("F", not fallas,
                       f"las {len(cerradas)} cláusulas de los dos modos tienen quien las ponga "
                       f"rojas" if not fallas else " | ".join(fallas)))
    return _cerrar(resultados)


# --- `--autotest-ledger` ----------------------------------------------------------------------

def modo_autotest_ledger(args: argparse.Namespace) -> int:
    del args
    corpus, error_corpus = _cargar_json(DIR_FIXTURES_LEDGER / "casos.json")
    manifest, error_manifest = _cargar_json(DIR_FIXTURES_LEDGER / "manifest.json")
    if error_corpus or error_manifest:
        print(f"[A] FALLA  {error_corpus or ''} {error_manifest or ''}".strip())
        return 1
    resultados: list[tuple[str, bool, str]] = []
    conforme = corpus["conforme"]

    # [A] Corpus y manifest, en las dos direcciones.
    fallas = []
    if set(corpus["casos"]) != {c["caso"] for c in manifest["casos"]}:
        fallas.append("el corpus y el manifest no declaran los mismos casos")
    resultados.append(("A", not fallas,
                       f"corpus ↔ manifest ({len(corpus['casos'])} casos)" if not fallas
                       else " | ".join(fallas)))

    # [B] Control positivo del ledger y de la sección.
    fallas = []
    problemas = revisar_ledger(conforme["ledger"], conforme["fuentes"], conforme["despachos"],
                               conforme["documento"])
    if problemas:
        fallas.append(f"el ledger conforme cayó por {[str(p) for p in problemas[:2]]}")
    incorporados = [c for c in conforme["ledger"]["candidatos"]
                    if c.get("adjudicacion") == "incorporado"]
    problemas = revisar_seccion_de_defectos(conforme["documento"], incorporados)
    if problemas:
        fallas.append(f"la sección conforme cayó por {[str(p) for p in problemas[:2]]}")
    resultados.append(("B", not fallas,
                       "el ledger y la sección conformes pasan" if not fallas
                       else " | ".join(fallas)))

    # [C] Cada caso cae por SU cláusula y por su motivo.
    fallas = []
    ejercidas: set[str] = set()
    for declarado in manifest["casos"]:
        caso = corpus["casos"][declarado["caso"]]
        ledger = caso.get("ledger", conforme["ledger"])
        documento = caso.get("documento", conforme["documento"])
        if declarado["modo"] == "ledger":
            problemas = revisar_ledger(ledger, caso.get("fuentes", conforme["fuentes"]),
                                       caso.get("despachos", conforme["despachos"]), documento)
        else:
            problemas = revisar_seccion_de_defectos(
                documento, caso.get("incorporados",
                                    [c for c in ledger.get("candidatos") or []
                                     if c.get("adjudicacion") == "incorporado"]))
        claves = sorted({p.clave for p in problemas})
        if claves != [declarado["clausula"]]:
            fallas.append(f"`{declarado['caso']}`: cayó por {claves} y se esperaba "
                          f"`{declarado['clausula']}`")
            continue
        if not any(declarado["fragmento"] in p.detalle for p in problemas):
            fallas.append(f"`{declarado['caso']}`: cayó por su cláusula y no por su motivo")
            continue
        ejercidas.add(declarado["clausula"])
    resultados.append(("C", not fallas,
                       f"los {len(manifest['casos'])} casos caen por su cláusula y por su motivo"
                       if not fallas else " | ".join(fallas[:5])))

    # [D] La reconciliación es BIDIRECCIONAL: un candidato en la fuente y no en el ledger, y una
    # entrada del ledger sin fuente, son fallas distintas. Con una sola dirección, escribir el
    # ledger a mano con lo que uno recuerda pasaría entero.
    fallas = []
    solo_en_la_fuente = {c.clave for c in revisar_ledger(
        {**conforme["ledger"], "candidatos": conforme["ledger"]["candidatos"][:-1]},
        conforme["fuentes"], conforme["despachos"], conforme["documento"])}
    if "candidato_fuera_del_ledger" not in solo_en_la_fuente:
        fallas.append("quitar un candidato del ledger no se ve")
    sin_fuentes = {c.clave for c in revisar_ledger(conforme["ledger"], {}, conforme["despachos"],
                                                   conforme["documento"])}
    if "entrada_del_ledger_sin_fuente" not in sin_fuentes:
        fallas.append("un ledger sin ninguna fuente que lo respalde no se ve")
    resultados.append(("D", not fallas,
                       "la reconciliación se rompe en las dos direcciones, con fallas distintas"
                       if not fallas else " | ".join(fallas)))

    # [E] «Cero candidatos» exige declaración explícita. Sin esto, un ledger vacío —el resultado de
    # no haber buscado— sería indistinguible de haber buscado y no encontrar nada.
    fallas = []
    vacio = {"fuentes": conforme["ledger"]["fuentes"], "candidatos": [], "capturas": []}
    claves = {c.clave for c in revisar_ledger(vacio, {}, [], "")}
    if "cero_candidatos_sin_declarar" not in claves:
        fallas.append("un ledger vacío sin declaración explícita no se ve")
    declarado = {**vacio, "declara_cero_candidatos": True}
    if any(c.clave == "cero_candidatos_sin_declarar"
           for c in revisar_ledger(declarado, {}, [], "")):
        fallas.append("declarar cero candidatos explícitamente sigue fallando")
    resultados.append(("E", not fallas,
                       "la rama «no se descubrió ninguno» exige declaración, y declararla alcanza"
                       if not fallas else " | ".join(fallas)))

    # [F] Los dos modos enteros, con sus argumentos obligatorios.
    fallas = []
    with tempfile.TemporaryDirectory(prefix="ledger-") as tmp:
        raiz = Path(tmp)
        ruta_ledger = raiz / "ledger.json"
        _escribir_json(ruta_ledger, conforme["ledger"])
        ruta_fuentes = raiz / "fuentes.json"
        _escribir_json(ruta_fuentes, {"fuentes": conforme["fuentes"],
                                      "despachos": conforme["despachos"]})
        documento = raiz / "documento.md"
        documento.write_text(conforme["documento"], encoding="utf-8")
        if _codigo_de_modo(modo_ledger, ledger=str(ruta_ledger), fuentes=str(ruta_fuentes),
                           documento=str(documento)) != 0:
            fallas.append("`--ledger` devolvió distinto de 0 sobre el conjunto conforme")
        # Igual que el `--base` de `--autotest-guardas-previas`: no alcanza con que falle. Un modo
        # que tomara el propio ledger como fuentes también fallaría —por forma, o por reconciliar
        # un conjunto contra sí mismo— y este control quedaría verde sin que nadie exigiera el
        # argumento. Se mira el mensaje.
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = modo_ledger(argparse.Namespace(ledger=str(ruta_ledger), fuentes=None,
                                                    documento=str(documento)))
        if codigo == 0:
            fallas.append("`--ledger` devolvió 0 sin `--fuentes`: reconciliaría el ledger contra "
                          "sí mismo")
        elif "falta `--fuentes`" not in salida.getvalue():
            fallas.append(f"`--ledger` falló sin `--fuentes` pero por otra causa: "
                          f"{salida.getvalue().strip().splitlines()[0][:90]}")
        if _codigo_de_modo(modo_seccion_defectos, seccion_defectos=str(documento),
                           ledger_de_la_seccion=str(ruta_ledger)) != 0:
            fallas.append("`--seccion-defectos` devolvió distinto de 0 sobre el documento conforme")
        sin_seccion = raiz / "sin-seccion.md"
        sin_seccion.write_text("# Otro documento\n\nsin la sección.\n", encoding="utf-8")
        if _codigo_de_modo(modo_seccion_defectos, seccion_defectos=str(sin_seccion),
                           ledger_de_la_seccion=str(ruta_ledger)) == 0:
            fallas.append("`--seccion-defectos` devolvió 0 sobre un documento sin la sección")
    resultados.append(("F", not fallas,
                       "`--ledger` y `--seccion-defectos` devuelven 0 sobre lo conforme y distinto "
                       "de 0 sobre sus negativos" if not fallas else " | ".join(fallas)))

    # [G] Cobertura de las cláusulas de los dos modos, acumulada corriendo.
    fallas = []
    cerradas = set(CLAUSULAS_DEL_LEDGER) | set(CLAUSULAS_DE_LA_SECCION)
    sin_ejercer = sorted(cerradas - ejercidas)
    if sin_ejercer:
        fallas.append(f"cláusulas sin caso que las ponga rojas: {sin_ejercer}")
    resultados.append(("G", not fallas,
                       f"las {len(cerradas)} cláusulas de los dos modos tienen quien las ponga "
                       f"rojas" if not fallas else " | ".join(fallas)))
    return _cerrar(resultados)


# ---------------------------------------------------------------------------------------------
# Registro de los modos de esta task. Cada task nueva agrega los suyos acá abajo, sin tocar los
# anteriores ni `main()`.
# ---------------------------------------------------------------------------------------------

registrar_modo(
    "--validar-schemas",
    "valida los cinco contratos de datos de la fase contra el meta-contrato: versionados, "
    "cerrados, sin `$ref` roto, sin definición inalcanzable y sin palabras clave que el "
    "validador no implemente",
    modo_validar_schemas,
)

registrar_modo(
    "--autotest-schemas",
    "control positivo y negativo del modo anterior sobre el corpus de "
    "scripts/fixtures-baseline/schemas/, comparado en las dos direcciones contra su manifest",
    modo_autotest_schemas,
)

registrar_modo(
    "--vocabulario-metricas",
    "enumera el vocabulario cerrado de scripts/metricas-fase-0.json y lo comprueba: las cinco "
    "categorías obligatorias contra su manifest independiente, la unidad y la agregación de cada "
    "métrica, la integridad referencial, la tasa de degradación y la ejecutabilidad de cada fórmula",
    modo_vocabulario_metricas,
)

registrar_modo(
    "--autotest-vocabulario",
    "control positivo y negativo del modo anterior sobre el corpus de "
    "scripts/fixtures-baseline/vocabulario/, más los mutantes que prueban que puede ponerse rojo",
    modo_autotest_vocabulario,
    auxiliares=(
        Auxiliar("--tasa",
                 "acota el autotest a la tasa de degradación: el negativo y los mutantes que "
                 "prueban que un vocabulario con solo conteo absoluto falla"),
    ),
)

registrar_modo(
    "--canonicalizar",
    "emite los bytes canónicos de un pre-registro y su SHA-256, con el campo del hash excluido de "
    "la proyección; si el documento ya lo declara, comprueba que coincida",
    modo_canonicalizar,
    argumento=Argumento("<ruta-del-preregistro>", const=RUTA_PREREGISTRO_FASE_0),
    auxiliares=(
        Auxiliar("--solo-bytes",
                 "escribe únicamente la proyección canónica a stdout, para recomputar el hash con "
                 "una herramienta externa: `... --canonicalizar <ruta> --solo-bytes | shasum -a 256`"),
    ),
)

registrar_modo(
    "--validar-bundles",
    "valida un conjunto de corridas: cada `<dir>/<run_id>/bundle.json` contra su contrato, el "
    "`run_id` declarado contra el nombre de su directorio y único en el conjunto, y la invocación "
    "con el literal que corresponde a su adaptador",
    modo_validar_bundles,
    argumento=Argumento("<dir-de-corridas>", const=RUTA_CORRIDAS_FASE_0),
)

registrar_modo(
    "--recolectar",
    "deriva la observación de una corrida SOLO desde su bundle y la escribe: ningún dato sale de "
    "la memoria del operador ni de lo que la corrida declare de sí misma, y toda métrica que no "
    "cierre se emite sin valor y con su adjudicación escrita",
    modo_recolectar,
    auxiliares=(
        Auxiliar("--bundle", "la corrida a recolectar: el directorio `<dir>/<run_id>/` que "
                             "contiene su bundle.json", metavar="<ruta-de-la-corrida>"),
        Auxiliar("--salida", "dónde escribir la observación; por omisión, "
                             "scripts/observaciones-fase-0/<run_id>.json",
                 metavar="<ruta-de-la-observacion>"),
    ),
)

registrar_modo(
    "--autotest-bundles",
    "control positivo y negativo de los dos modos anteriores sobre el corpus de "
    "scripts/fixtures-baseline/bundles/, comparado en las dos direcciones contra su manifest, más "
    "los mutantes que prueban que cada campo se deriva de su hecho y no se copia",
    modo_autotest_bundles,
)

registrar_modo(
    "--autotest-recoleccion",
    "golden bundle → observación esperada, comparado campo por campo, más los mutantes de "
    "transformación: clasificación copiada de un campo declarativo, identidad alterada, evento "
    "omitido y dato incorporado que el bundle no contiene",
    modo_autotest_recoleccion,
)

registrar_modo(
    "--autotest-derivacion",
    "prueba que cada observación se derivó RE-EJECUTANDO el recolector sobre su bundle y "
    "comparando byte a byte: una escrita a mano que copia el hash y la identidad falla igual",
    modo_autotest_derivacion,
)

registrar_modo(
    "--autotest-muestras-intentos",
    "las muestras congeladas frente a los intentos derivados (D-12): el conjunto de muestras "
    "derivado aparte como producto punto × repetición, la cadena append-only contra su manifest "
    "independiente, la regla de identidad congelada y la política de reintentos aplicada",
    modo_autotest_muestras_intentos,
)

registrar_modo(
    "--recomponer",
    "reconstruye cada número del baseline desde la fuente canónica de su clase —las mediciones "
    "desde las observaciones, la metodología desde el pre-registro, el presupuesto contractual "
    "desde la matriz— y comprueba el DAG de procedencia antes de empezar; con un `.md` compara "
    "además, en las dos direcciones, lo PUBLICADO contra lo recompuesto",
    modo_recomponer,
    argumento=Argumento("<dir-de-observaciones-o-baseline.md>",
                        const=RUTA_OBSERVACIONES_FASE_0),
    auxiliares=(
        Auxiliar("--observaciones", "de dónde salen las observaciones cuando el argumento es un "
                                    "documento publicado; por omisión, las de la fase",
                 metavar="<dir>"),
    ),
)

registrar_modo(
    "--autotest-recomposicion",
    "control del modo anterior sobre el corpus de scripts/fixtures-baseline/recomposicion/: el "
    "conjunto íntegro recompone los números publicados, y faltante, sobrante, duplicado y número "
    "alterado en una unidad lo rompen en vez de recomponer sobre el subconjunto que llegó",
    modo_autotest_recomposicion,
)

registrar_modo(
    "--autotest-procedencia-dag",
    "el grafo de procedencia: aciclicidad —con el ciclo indirecto, que sobrevive a una revisión "
    "por inspección—, una sola fuente canónica por clase de dato, dependencia omitida y extra, y "
    "cada arista ejercida con faltante, sobrante y duplicado",
    modo_autotest_procedencia_dag,
)

registrar_modo(
    "--latencias",
    "las dos magnitudes de latencia de un conjunto de observaciones REALES, verificadas contra la "
    "interfaz de reloj: procedencia y precisión de cada sello, orden de la apertura, duración "
    "posible, estratos derivados del valor efectivo y exigidos por la matriz, y las reglas de "
    "reintento, despacho múltiple, presupuesto vencido y muestra incompleta",
    modo_latencias,
    argumento=Argumento("<dir-de-observaciones>", const=RUTA_OBSERVACIONES_FASE_0),
    auxiliares=(
        Auxiliar("--bundles", "dónde están los bundles de los que salieron esas observaciones; "
                              f"por omisión, {RUTA_CORRIDAS_FASE_0}",
                 metavar="<dir-de-corridas>"),
    ),
)

registrar_modo(
    "--autotest-latencias",
    "control del modo anterior sobre el corpus de scripts/fixtures-baseline/latencias/: las dos "
    "magnitudes en sus dos sedes y un negativo por regla. Con `--estratos` se acota al estrato y "
    "al agregador, que rechaza entradas mixtas en vez de promediarlas",
    modo_autotest_latencias,
    auxiliares=(
        Auxiliar("--estratos",
                 "acota el autotest al estrato de intervención humana y al rechazo de mezclas"),
    ),
)

registrar_modo(
    "--autotest-reloj",
    "el reloj monotónico bajo autoridad del harness: la interfaz cierra el conjunto de "
    "procedencias para los dos adaptadores y coincide con el schema; un evento fuera de orden y "
    "una duración imposible se rechazan, no se promedian; y el redondeo canónico sale de la "
    "interfaz",
    modo_autotest_reloj,
)

registrar_modo(
    "--hallazgos",
    "la métrica de hallazgos de un conjunto de corridas, derivada de sus EVENTOS: por corrida, "
    "emisiones totales, hallazgos distintos y re-emisiones. Donde el acta no eligió fórmula, la "
    "métrica se informa sin observación y con su adjudicación, nunca en cero",
    modo_hallazgos,
    argumento=Argumento("<dir-de-corridas>", const=RUTA_CORRIDAS_FASE_0),
    auxiliares=(
        Auxiliar("--preregistro", "el acta congelada de la que sale la fórmula elegida; por "
                                  f"omisión, {RUTA_PREREGISTRO_FASE_0}",
                 metavar="<ruta-del-preregistro>"),
    ),
)

registrar_modo(
    "--autotest-hallazgos",
    "control del modo anterior sobre el corpus de scripts/fixtures-baseline/hallazgos/: la "
    "re-emisión del mismo hallazgo cuenta una vez, la ausencia no se reporta como cero, y el "
    "corpus separa la regla correcta de las dos formas de contar mal",
    modo_autotest_hallazgos,
)

registrar_modo(
    "--autotest-clasificacion",
    "el corpus de control de AC-18: cada caso declara su terna de ejes normativos y sus métricas "
    "POR SEPARADO —nunca una etiqueta única—, comparado en las dos direcciones contra el manifest "
    "independiente de categorías obligatorias, con el mutante de eliminación de cada caso",
    modo_autotest_clasificacion,
    auxiliares=(
        Auxiliar("--combinados",
                 "acota el autotest a los casos que combinan varias fallas, y compara contra las "
                 "combinaciones mínimas en vez de las categorías obligatorias"),
    ),
)

registrar_modo(
    "--fixture-historico",
    "el registro contradictorio de la serie del propio repositorio —degradación declarada ausente "
    "frente a dos degradaciones narradas— reconstruido y no copiado: comprueba que el fixture es "
    "autónomo, que reproduce las dos degradaciones y que el instrumento lo clasifica incorrecto "
    "derivándolas",
    modo_fixture_historico,
)

registrar_modo(
    "--recetas",
    "enumera las trece recetas ejecutables de la cohorte y las comprueba contra la matriz: una por "
    "punto en las dos direcciones, con los seis campos que AC-34 exige, la invocación que "
    "corresponde a su transporte, los pasos encadenados con su regla de enlace, y la derivación de "
    "cada una EJECUTADA contra su sede",
    modo_recetas,
)

registrar_modo(
    "--autotest-recetas",
    "control del modo anterior sobre el corpus de scripts/fixtures-baseline/recetas/: las trece "
    "recetas contra la matriz y contra el manifest independiente de clasificación, el escenario "
    "encadenado, y los ataques al documento —receta faltante, campo ausente, comando en un punto de "
    "subagente, transporte cambiado, enlace borrado y enlace que congela el identificador de "
    "sesión—. Con `--derivacion` se acota al origen de cada comando: cada derivación ejecutada "
    "contra su sede, y los dos extremos que AC-34 nombra —cero resultados y múltiples— sobre una "
    "sede sintética",
    modo_autotest_recetas,
    auxiliares=(
        Auxiliar("--derivacion",
                 "acota el autotest al origen declarado de cada comando: derivación tipada "
                 "ejecutada, o adjudicación humana con su motivo"),
    ),
)

registrar_modo(
    "--autotest-procedencia-portada",
    "el corpus DIFERENCIAL del motor de extracción portado (D-1): cada caso ejerce una forma tipada "
    "sobre una sede controlada y su salida esperada la congeló el motor ORIGINAL, no el portado. "
    "Comprueba además que las dimensiones que usan las trece recetas caen dentro de la frontera "
    "declarada, y que las seis causas de fallo del resolutor están ejercidas o dicen dónde lo están",
    modo_autotest_procedencia_portada,
)

registrar_modo(
    "--generar-baseline",
    "genera el baseline en Markdown desde las observaciones: cada número derivado de su fuente "
    "canónica, la salida determinista byte a byte, y toda métrica sin observaciones declarada como "
    "tal —con la adjudicación del agregado y la de cada observación— y nunca en cero",
    modo_generar_baseline,
    argumento=Argumento("<dir-de-observaciones>", const=RUTA_OBSERVACIONES_FASE_0),
    auxiliares=(
        Auxiliar("--salida", "dónde escribir el documento; por omisión, "
                             f"{RUTA_BASELINE_FASE_0}",
                 metavar="<ruta-del-baseline>"),
    ),
)

registrar_modo(
    "--autotest-generacion",
    "control del modo anterior sobre el corpus de scripts/fixtures-baseline/generacion/: golden "
    "escrito a mano y comparado byte a byte, determinismo bajo orden invertido, lectura inversa "
    "de la tabla de números, y los ataques al documento —número alterado, métrica sin "
    "observaciones omitida, publicada en cero o sin adjudicación, métrica inventada— y al insumo",
    modo_autotest_generacion,
)

registrar_modo(
    "--autotest-canonicalizacion",
    "prueba que la proyección canónica es completa —contra un fixture de punteros normativos "
    "externo al schema, comparado en las dos direcciones— y que el campo del hash está fuera de "
    "ella, más los mutantes que prueban que puede ponerse rojo",
    modo_autotest_canonicalizacion,
)

registrar_modo(
    "--aislamiento",
    "juzga la evidencia de aislamiento de un conjunto de corridas: las tres pruebas por separado, "
    "exigidas según el permiso efectivo que declara LA MATRIZ —no el bundle—, y los recursos con "
    "vida y propiedad modeladas aparte; una observación que no las sostiene queda bloqueada",
    modo_aislamiento,
    argumento=Argumento("<dir-de-corridas>", const=RUTA_CORRIDAS_FASE_0),
)

registrar_modo(
    "--autotest-egreso",
    "corre los cuatro mutantes de publicación —shell, URL, API y herramienta autenticada— por su "
    "adaptador REAL interceptado en la frontera contra un canary local, en entorno desechable, con "
    "snapshot previo y posterior iguales y cese del canary comprobado",
    modo_autotest_egreso,
)

registrar_modo(
    "--recibo-de-egreso",
    "APLICA la regla de egreso sobre el entorno real: materializa el inventario del entorno "
    "desechable —el que cada corrida reejecuta y compara—, con el del host al lado como evidencia "
    "del retiro, y emite un recibo por superficie descubierta con su mutante, su frontera "
    "interceptada y su resultado; una superficie sin tratamiento bloquea",
    modo_recibo_de_egreso,
    auxiliares=(
        Auxiliar("--salida", "dónde escribir el recibo materializado", metavar="<ruta>"),
    ),
)

registrar_modo(
    "--autotest-aislamiento",
    "control positivo y negativo del juicio de aislamiento sobre su corpus: un escritor con menos "
    "de las tres pruebas queda bloqueado, un caso de solo lectura registra `not_applicable` con "
    "causa derivada de la matriz, y falsear ese permiso para esquivarlas falla",
    modo_autotest_aislamiento,
)

registrar_modo(
    "--autotest-recursos",
    "control de que vida, propiedad, dueño y próxima acción se modelan por separado: un recurso "
    "transferido exige dueño Y próxima acción —con un negativo por campo—, solo el terminal "
    "comprobado cuenta como limpieza, y el cese inferido por efectos en el árbol bloquea",
    modo_autotest_recursos,
)

registrar_modo(
    "--validar-protocolo",
    "exige que el protocolo enumere casos, repeticiones, entorno y exclusiones, y que cada métrica "
    "tome su fórmula, su unidad y su agregación DEL VOCABULARIO CERRADO; el conjunto cubre las "
    "cinco categorías y la degradación se publica como al menos una tasa auditable",
    modo_validar_protocolo,
    argumento=Argumento("<ruta-del-preregistro>", const=RUTA_PREREGISTRO_FASE_0),
)

registrar_modo(
    "--cobertura",
    "exige la cobertura mínima por métrica y estrato y el conjunto cerrado de causas de exclusión: "
    "una exclusión fuera de ese conjunto, o una métrica obligatoria sin cohorte que la mida, "
    "bloquean el cierre de la fase",
    modo_cobertura,
    argumento=Argumento("<ruta-del-preregistro>", const=RUTA_PREREGISTRO_FASE_0),
)

registrar_modo(
    "--promocion",
    "comprueba que el evaluador de promoción tenga con qué decidir en cada fase comprometida "
    "—métricas obligatorias, umbral con su dirección y su tratamiento del límite, y regla de "
    "composición— y emite el veredicto de una fase que todavía no corrió: `not_evaluated`",
    modo_promocion,
    argumento=Argumento("<ruta-del-preregistro>", const=RUTA_PREREGISTRO_FASE_0),
)

registrar_modo(
    "--cobertura-final",
    "sobre el BASELINE GENERADO: comprueba que la cobertura mínima se cumplió y que el documento "
    "informa explícitamente qué parte del ecosistema no pudo observarse",
    modo_cobertura_final,
    argumento=Argumento("<ruta-del-baseline>", const=RUTA_BASELINE_FASE_0),
)

registrar_modo(
    "--promocion-final",
    "sobre el BASELINE GENERADO: corre el evaluador congelado con los números publicados y emite "
    "el veredicto de cada fase, distinguiendo `not_evaluated` de `blocked`",
    modo_promocion_final,
    argumento=Argumento("<ruta-del-baseline>", const=RUTA_BASELINE_FASE_0),
)

registrar_modo(
    "--autotest-cobertura",
    "control positivo y negativo del protocolo y de la cobertura sobre su corpus: una exclusión "
    "fuera del conjunto cerrado y una métrica obligatoria sin cohorte bloquean, y cada variante "
    "cae por su cláusula y por su motivo",
    modo_autotest_cobertura,
)

registrar_modo(
    "--autotest-promocion",
    "control del evaluador determinista: dirección del umbral, tratamiento del valor límite en las "
    "cuatro combinaciones y regla de composición en sus dos formas, con `not_evaluated` y "
    "`blocked` distinguidos",
    modo_autotest_promocion,
)

registrar_modo(
    "--validar-preregistro-congelado",
    "primera fase del ciclo: el hash de la proyección canónica identifica este contenido, el "
    "commit que fija el pre-registro es descendiente directo de `code_commit` con el acta como "
    "único cambio y es anterior a toda corrida, y las muestras no están vacías ni duplicadas. NO "
    "exige observaciones: se corre para poder empezar a medir",
    modo_validar_preregistro_congelado,
    argumento=Argumento("<ruta-del-preregistro>", const=RUTA_PREREGISTRO_FASE_0),
    auxiliares=(
        Auxiliar("--corridas", "dónde están las corridas contra las que se ordena el "
                               f"congelamiento; por omisión, {RUTA_CORRIDAS_FASE_0}",
                 metavar="<dir-de-corridas>"),
        Auxiliar("--repo", "el repositorio contra el que se resuelve el commit que fija el "
                           "pre-registro; por omisión, la raíz de este árbol",
                 metavar="<dir-del-repo>"),
    ),
)

registrar_modo(
    "--validar-manifest-observaciones",
    "segunda fase del ciclo: cada observación cita el acta —y la que cita otra se rechaza en vez "
    "de incorporarse—, el conjunto de muestras coincide exactamente con el pre-registro, la "
    "cadena de intentos es append-only y derivada de la regla congelada sin descartar los "
    "bloqueados, y los pasos encadenados conservan su dependencia",
    modo_validar_manifest_observaciones,
    argumento=Argumento("<dir-de-observaciones>", const=RUTA_OBSERVACIONES_FASE_0),
    auxiliares=(
        Auxiliar("--intentos", "el manifest independiente de intentos esperados (D-16): sin él el "
                               "modo falla, porque derivarlo del conjunto que valida sería "
                               "contarlo sobre sí mismo",
                 metavar="<ruta-del-manifest>"),
        Auxiliar("--bundles", "dónde están los bundles de los que salieron esas observaciones, "
                              "contra los que se adjudica la identidad del entorno; por omisión, "
                              f"{RUTA_CORRIDAS_FASE_0}",
                 metavar="<dir-de-corridas>"),
    ),
)

registrar_modo(
    "--autotest-preregistro",
    "control de las dos fases sobre repositorios SEMBRADOS con commits reales: la fase congelada "
    "pasa con cero corridas y la del manifest falla con el conjunto vacío, y cada caso del corpus "
    "de scripts/fixtures-baseline/preregistro/ cae por su cláusula y por su motivo",
    modo_autotest_preregistro,
)

registrar_modo(
    "--autotest-identidad-entorno",
    "la identidad del entorno como conjunto cerrado: los campos salen de los dos schemas y se "
    "comparan en las dos direcciones contra la tabla de adjudicación, cada divergencia se ejerce "
    "por separado con su bloqueo o su estratificación, y una adjudicación fuera del conjunto "
    "cerrado bloquea en vez de agregar",
    modo_autotest_identidad_entorno,
)

registrar_modo(
    "--sanitizar",
    "juzga el pipeline de evidencia de un conjunto de corridas: el orden canónico del contrato "
    "—con el hash DESPUÉS de normalizar rutas y escanear, para que identifique la evidencia "
    "sanitizada y no un crudo que nunca se versiona—, el manifest ordenado por ruta, tamaño y "
    "hash, y el contenido publicable",
    modo_sanitizar,
    argumento=Argumento("<dir-de-corridas>", const=RUTA_CORRIDAS_FASE_0),
)

registrar_modo(
    "--autotest-sanitizacion",
    "control del modo anterior sobre el corpus de scripts/fixtures-baseline/sanitizacion/: el "
    "orden canónico sale del contrato y no de una copia, el hash cambia con el contenido del "
    "manifest y no con el orden de recorrido, y cada ataque al pipeline cae por su cláusula",
    modo_autotest_sanitizacion,
)

registrar_modo(
    "--autotest-escaneo",
    "control del escaneo: secreto, credencial y ruta absoluta del host bloquean, cada uno por su "
    "regla; la ruta relativa al repositorio y el nombre de una credencial sin valor NO bloquean; y "
    "ningún documento JSON del árbol real queda impublicable",
    modo_autotest_escaneo,
)

registrar_modo(
    "--altas-topologia",
    "las altas de este acto: el conjunto previo se DERIVA de `--base` con plumbing y la diferencia "
    "se compara en las dos direcciones contra las identidades esperadas — `--topologia` valida las "
    "entradas presentes y no conoce la lista, así que un alta que faltara del árbol y del registro "
    "lo dejaría verde",
    modo_altas_topologia,
    auxiliares=(
        Auxiliar("--base", "el commit del que se deriva el conjunto previo",
                 metavar="<sha>"),
        Auxiliar("--esperadas", "el manifest independiente de altas esperadas; por omisión, "
                                "scripts/fixtures-baseline/topologia/altas-esperadas.json",
                 metavar="<ruta>"),
    ),
)

registrar_modo(
    "--integracion",
    "la unidad de las instrucciones que documenta este script: que declare que es script propio, "
    "cuándo correrlo, el comando exacto y el código de salida sano, y que los tres sean CIERTOS "
    "contra el árbol —la bandera existe y devuelve lo que se declara—",
    modo_integracion,
    auxiliares=(
        Auxiliar("--instrucciones", f"el documento de instrucciones; por omisión, "
                                    f"{RUTA_INSTRUCCIONES}", metavar="<ruta>"),
        Auxiliar("--script", "el script cuya unidad se busca; por omisión, este mismo",
                 metavar="<ruta>"),
    ),
)

registrar_modo(
    "--autotest-integracion",
    "control del modo anterior sobre el corpus de scripts/fixtures-baseline/integracion/: "
    "disparador ausente, comando distinto del real, código sano falso y «modo de otro script» "
    "fallan, y la unidad se lee entera con sus continuaciones indentadas",
    modo_autotest_integracion,
)

registrar_modo(
    "--guardas-previas",
    "el conjunto de guardas de `--base`, derivado con plumbing: cada identidad, comando y criterio "
    "sigue presente sin cambios, y se ejecutan. Con `--sin-ejecutar` se acota a la comparación",
    modo_guardas_previas,
    auxiliares=(
        Auxiliar("--sin-ejecutar", "compara el conjunto previo sin correr las guardas"),
    ),
)

registrar_modo(
    "--autotest-guardas-previas",
    "control de los DOS modos que derivan de `base_commit` —guardas y altas de topología— sobre "
    "sus corpus y sobre un repo sembrado con commits reales: una guarda borrada, un criterio "
    "cambiado, un alta faltante y una base que no resuelve fallan",
    modo_autotest_guardas_previas,
)

registrar_modo(
    "--ledger",
    "reconcilia el ledger de candidatos contra las cuatro fuentes cerradas en las dos direcciones "
    "y contra el manifest de despachos: cada candidato adjudicado con su razón, cada despacho con "
    "su reporte o su adjudicación explícita de «sin reporte delegado», y los incorporados "
    "presentes en el documento",
    modo_ledger,
    argumento=Argumento("<ruta-del-ledger>", const="scripts/ledger-candidatos-fase-0.json"),
    auxiliares=(
        Auxiliar("--fuentes", "el conjunto de candidatos derivado de las cuatro fuentes y el "
                              "manifest de despachos; sin él el modo falla, porque derivarlo del "
                              "propio ledger sería reconciliarlo contra sí mismo",
                 metavar="<ruta>"),
        Auxiliar("--documento", "el documento cuyo inventario tiene que contener los incorporados",
                 metavar="<ruta>"),
    ),
)

registrar_modo(
    "--autotest-ledger",
    "control de `--ledger` y `--seccion-defectos` sobre el corpus de "
    "scripts/fixtures-baseline/ledger/: un hallazgo presente en una fuente y ausente del ledger "
    "falla, un candidato sin adjudicar falla, la rama «cero candidatos» exige declaración "
    "explícita, y dos candidatos del mismo despacho se reconcilian por su `candidate_id`",
    modo_autotest_ledger,
)

registrar_modo(
    "--seccion-defectos",
    "la sección del inventario existe POR IDENTIDAD y declara el trato real de los defectos de "
    "este flujo, con sus dos ramas —incorporados con su ubicación resuelta contra el árbol, o «no "
    "se descubrió ninguno»—: la mera ausencia de la frase anterior no la satisface",
    modo_seccion_defectos,
    argumento=Argumento("<ruta-del-documento>",
                        const="docs/superpowers/specs/2026-08-09-subagentes-perfiles-fase-0.md"),
    auxiliares=(
        Auxiliar("--ledger-de-la-seccion", "el ledger del que salen los incorporados que la "
                                           "sección tiene que listar", metavar="<ruta>"),
    ),
)

registrar_modo(
    "--autotest-identidad-congelada",
    "prueba que la comprobación de identidad de los scripts congelados PUEDE ponerse roja: mutila "
    "el instrumento y el runner por separado sobre copias y exige que su hash de Git cambie —y "
    "solo el suyo—, y comprueba que el comparador es el objeto de Git y no un hash propio de este "
    "archivo (D-23)",
    modo_autotest_identidad_congelada,
)


# ---------------------------------------------------------------------------------------------
# CLI. Se construye desde `MODOS`: agregar un modo no toca nada de acá.
# ---------------------------------------------------------------------------------------------

def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Instrumento de medición del baseline de la fase 0.",
        add_help=True,
    )
    declaradas: set[str] = set()
    for modo in MODOS:
        if modo.argumento is None:
            parser.add_argument(modo.bandera, action="store_true", help=modo.ayuda)
        else:
            parser.add_argument(modo.bandera, nargs="?", const=modo.argumento.const,
                                metavar=modo.argumento.metavar, help=modo.ayuda)
        for aux in modo.auxiliares:
            if aux.bandera in declaradas:
                continue  # una auxiliar compartida entre modos se declara una sola vez
            declaradas.add(aux.bandera)
            if aux.metavar is None:
                parser.add_argument(aux.bandera, action="store_true", help=aux.ayuda)
            else:
                parser.add_argument(aux.bandera, metavar=aux.metavar, default=aux.por_defecto,
                                    help=aux.ayuda)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _construir_parser()
    args = parser.parse_args(argv)

    seleccionados = [m for m in MODOS if getattr(args, m.destino)]
    if len(seleccionados) != 1:
        banderas = ", ".join(m.bandera for m in MODOS)
        print(f"Invocación inválida: exactamente uno de {banderas}.", file=sys.stderr)
        return 2
    return seleccionados[0].handler(args)


if __name__ == "__main__":
    sys.exit(main())
