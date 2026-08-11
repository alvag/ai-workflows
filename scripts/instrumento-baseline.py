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
