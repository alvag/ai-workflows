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
import copy
import hashlib
import json
import re
import sys
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
    "--autotest-canonicalizacion",
    "prueba que la proyección canónica es completa —contra un fixture de punteros normativos "
    "externo al schema, comparado en las dos direcciones— y que el campo del hash está fuera de "
    "ella, más los mutantes que prueban que puede ponerse rojo",
    modo_autotest_canonicalizacion,
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
