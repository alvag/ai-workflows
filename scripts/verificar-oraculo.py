#!/usr/bin/env python3
"""Validador de los insumos congelados del oráculo de la Fase 0.5.

Este archivo **crece por tasks**: cada una agrega su modo y no reescribe lo de las otras. Los modos
vivos hoy:

- `--consumidor` — comprueba que el enunciado `Given/When/Then` de AC-11 de `dossier-arnes` no
  prescriba un método para el conjunto esperado y que su spec ancle el mismo `sha256` de contrato.
  Es la guarda bloqueante de AC-1: se corre **antes** de producir cualquiera de los cuatro
  artefactos, y otra vez al cerrar.
- `--autotest-consumidor` — control positivo y negativo del modo anterior sobre el recorte
  versionado de `scripts/fixtures-oraculo/consumidor/`, más los mutantes que prueban que puede
  ponerse rojo.

## Cómo se agrega un modo (normativo — diecinueve tasks escriben este mismo archivo)

1. Escribí la función `modo_<nombre>(args) -> int` en una sección propia al final del archivo,
   antes del bloque de registro.
2. Registrala con `registrar_modo(...)`, declarando bandera, ayuda y handler.
3. No toques `main()`: construye el parser y el despacho desde `MODOS`, así que un modo nuevo entra
   sin editar ninguna función existente.

Códigos de salida, iguales en todos los modos: **0** sano, **1** hallazgos, **2** invocación
inválida.

## Por qué el validador de schemas es propio

No hay `jsonschema` en el entorno y el repo no toma dependencias externas: solo stdlib. El
subconjunto de JSON Schema 2020-12 de este archivo está **portado y no importado** desde
`scripts/instrumento-baseline.py`, a propósito: esa sede está congelada y su modificación la
gobiernan otras guardas, así que importar de ahí acoplaría este flujo a un archivo que no puede
cambiar. Es la misma política que ese archivo declara sobre `verificar-matriz-despachos.py`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Callable, NamedTuple

RAIZ = Path(__file__).resolve().parent.parent
DIR_SCRIPTS = RAIZ / "scripts"
DIR_FIXTURES = DIR_SCRIPTS / "fixtures-oraculo"

# El contrato de extracción que esta fase congela. Es el mismo que `dossier-arnes` declara en su
# encabezado; que sigan siendo el mismo es la mitad de AC-1.
SHA_CONTRATO = "3a9412cbf169e74376c00bc8a13fb3ce5669064f9a520d7c69fe30bf7c0021ef"

# La spec del consumidor vive bajo `.plans/`, que está en `.git/info/exclude:11`. Que no sea
# versionada es exactamente el límite del cuarto proxy (AC-14): esta guarda lee el texto, no
# acredita que su gate humano haya vuelto a ocurrir.
RUTA_SPEC_CONSUMIDOR = RAIZ / ".plans" / "dossier-arnes" / "spec.md"


# ---------------------------------------------------------------------------------------------
# Registro de modos. La tabla desde la que `main()` construye el parser y el despacho.
# ---------------------------------------------------------------------------------------------

class Modo(NamedTuple):
    bandera: str
    ayuda: str
    handler: Callable[[argparse.Namespace], int]

    @property
    def destino(self) -> str:
        return self.bandera[2:].replace("-", "_")


MODOS: list[Modo] = []


def registrar_modo(bandera: str, ayuda: str, handler: Callable[[argparse.Namespace], int]) -> None:
    """Da de alta un modo. Es el único punto de contacto con el CLI: nadie edita `main()`."""
    if any(m.bandera == bandera for m in MODOS):
        raise ValueError(f"el modo {bandera} ya está registrado")
    MODOS.append(Modo(bandera, ayuda, handler))


# ---------------------------------------------------------------------------------------------
# Utilidades compartidas.
# ---------------------------------------------------------------------------------------------

def _sha256_de(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def _cargar_json(ruta: Path) -> tuple[object, str | None]:
    try:
        return json.loads(ruta.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"no existe: {ruta}"
    except json.JSONDecodeError as exc:
        return None, f"JSON inválido en {ruta}: {exc}"


def plegar(texto: str) -> str:
    """Minúsculas sin diacríticos. Un marcador de método no deja de serlo por un acento."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------------------------------------
# Modo `--consumidor` (AC-1). La alineación del consumidor, comprobada sobre el enunciado.
# ---------------------------------------------------------------------------------------------

# El conjunto cerrado de métodos que AC-11 **no** puede prescribir. No es una lista de palabras
# sospechosas: cada entrada nombra un camino de producción del conjunto esperado distinto del que
# AC-6 fija (detección independiente por la otra familia + adjudicación del conductor).
METODOS_PRESCRIPTIVOS: tuple[tuple[str, str], ...] = (
    ("barrido textual", "el método que AC-11 prescribía en su paréntesis y el sondeo descartó"),
    ("barrido lexico", "variante nominal del anterior"),
    ("derivacion mecanica", "el nombre con que el sondeo lo midió: comparte autor con el parser"),
    ("gramatica de r1", "prescribir la gramática del contrato como camino del conjunto esperado"),
    ("expresion regular", "prescribir el mecanismo de extracción en vez del dueño del método"),
    ("regex", "ídem, en su forma abreviada"),
    ("grep", "ídem, en su forma coloquial"),
)

# Un `sha256` en hexadecimal. Sirve para dos cosas distintas: encontrar el ancla de contrato de la
# spec y detectar un ancla divergente introducida dentro del enunciado.
PATRON_SHA = re.compile(r"\b[0-9a-f]{64}\b")
PATRON_AC11 = re.compile(r"^- \*\*AC-11\s+—")


class Enunciado(NamedTuple):
    texto: str
    linea_inicial: int  # 1-indexada, para nombrar la discrepancia donde vive


def extraer_enunciado_ac11(texto: str) -> tuple[Enunciado | None, str | None]:
    """El enunciado `Given/When/Then` de AC-11: el ítem de lista, hasta la primera línea en blanco.

    El corte no es cosmético. La prosa de fundamento que sigue **cita a propósito el método
    retirado** para explicar por qué se fue; un predicado que buscara el texto prohibido en todo el
    archivo lo encontraría ahí y daría rojo sobre una spec correcta. Es la distinción entre el
    artefacto *prescribiendo* algo y el artefacto *registrando que dejó de prescribirlo*.
    """
    lineas = texto.split("\n")
    inicio = None
    for i, linea in enumerate(lineas):
        if PATRON_AC11.match(linea):
            if inicio is not None:
                return None, ("AC-11 aparece más de una vez como ítem de lista "
                              f"(líneas {inicio + 1} y {i + 1}): el alcance sería ambiguo")
            inicio = i
    if inicio is None:
        return None, "no se encontró el ítem `- **AC-11 — …**` en la spec del consumidor"

    fin = inicio + 1
    while fin < len(lineas) and lineas[fin].strip() != "":
        fin += 1
    return Enunciado("\n".join(lineas[inicio:fin]), inicio + 1), None


def ancla_de_contrato(texto: str) -> tuple[str | None, str | None]:
    """El `sha256` de contrato que la spec declara en su encabezado.

    **El alcance de esta mitad es la spec, no el enunciado, y es deliberado.** El enunciado de
    AC-11 nunca llevó un hash: buscarlo ahí daría una guarda vacía —verde por ausencia, incapaz de
    ponerse roja—, que es peor que no tenerla. La spec ancla el contrato en su encabezado, y ese es
    el ancla que AC-1 compara. El enunciado se comprueba igual, pero por lo contrario: que **no**
    introduzca un ancla propia divergente.
    """
    for linea in texto.split("\n"):
        plegada = plegar(linea)
        if "sha256" not in plegada and "contrato" not in plegada:
            continue
        encontrado = PATRON_SHA.search(linea)
        if encontrado:
            return encontrado.group(0), None
    return None, "la spec del consumidor no declara ningún `sha256` de contrato"


def revisar_consumidor(texto: str, etiqueta: str) -> list[str]:
    """Los hallazgos de AC-1 sobre el texto de la spec del consumidor. Lista vacía es alineado."""
    hallazgos: list[str] = []

    enunciado, error = extraer_enunciado_ac11(texto)
    if error:
        return [f"{etiqueta}: {error}"]
    assert enunciado is not None

    plegado = plegar(enunciado.texto)
    for marcador, por_que in METODOS_PRESCRIPTIVOS:
        if marcador in plegado:
            hallazgos.append(
                f"{etiqueta}:{enunciado.linea_inicial}: el enunciado de AC-11 prescribe un método "
                f"—«{marcador}»— distinto del de AC-6 ({por_que})"
            )

    ancla, error = ancla_de_contrato(texto)
    if error:
        hallazgos.append(f"{etiqueta}: {error}")
    elif ancla != SHA_CONTRATO:
        hallazgos.append(
            f"{etiqueta}: la spec ancla el contrato {ancla} y esta fase congela {SHA_CONTRATO}"
        )

    for hallado in PATRON_SHA.findall(enunciado.texto):
        if hallado != SHA_CONTRATO:
            hallazgos.append(
                f"{etiqueta}:{enunciado.linea_inicial}: el enunciado de AC-11 ancla un contrato "
                f"propio y divergente ({hallado})"
            )

    return hallazgos


def modo_consumidor(args: argparse.Namespace) -> int:
    del args
    if not RUTA_SPEC_CONSUMIDOR.is_file():
        print(f"FALLA  no existe la spec del consumidor: {RUTA_SPEC_CONSUMIDOR}")
        print("RESULTADO: FALLA — sin el artefacto no hay alineación que comprobar; no degrada "
              "a verde")
        return 1

    texto = RUTA_SPEC_CONSUMIDOR.read_text(encoding="utf-8")
    hallazgos = revisar_consumidor(texto, "dossier-arnes/spec.md")
    for h in hallazgos:
        print(f"FALLA  {h}")

    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} discrepancias con AC-1; no producir ningún "
              "artefacto hasta resolverlas")
        return 1
    print(f"RESULTADO: OK — AC-11 del consumidor no prescribe método y su spec ancla "
          f"{SHA_CONTRATO[:8]}…")
    return 0


# ---------------------------------------------------------------------------------------------
# Modo `--autotest-consumidor`.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURE_CONSUMIDOR = DIR_FIXTURES / "consumidor"
RUTA_RECORTE = DIR_FIXTURE_CONSUMIDOR / "spec-arnes-recorte.md"

# El sha256 de otro contrato cualquiera. No es un valor mágico: es un hash de 64 hex distinto del
# congelado, y su único requisito es no ser `SHA_CONTRATO`.
SHA_AJENO = "0" * 63 + "1"


class Mutante(NamedTuple):
    nombre: str
    aplicar: Callable[[str], str]
    causa: str  # el fragmento que el mensaje del hallazgo tiene que contener


def _mut_metodo_en_el_enunciado(texto: str) -> str:
    """Reintroduce el paréntesis retirado **dentro del enunciado**, que es lo que AC-1 prohíbe."""
    return texto.replace(
        "producido por un **camino independiente del parser**",
        "producido por un **camino independiente del parser** (un barrido textual mínimo, no la "
        "gramática de R1–R2)",
        1,
    )


def _mut_ancla_divergente(texto: str) -> str:
    return texto.replace(SHA_CONTRATO, SHA_AJENO, 1)


def _mut_ancla_propia_en_el_enunciado(texto: str) -> str:
    return texto.replace(
        "con su causa del enum de AC-5 **nombrada**.",
        f"con su causa del enum de AC-5 **nombrada**, contra el contrato `{SHA_AJENO}`.",
        1,
    )


def _mut_sin_ac11(texto: str) -> str:
    return texto.replace("- **AC-11 —", "- **AC-99 —", 1)


def _mut_ac11_duplicado(texto: str) -> str:
    cabecera = next(x for x in texto.split("\n") if PATRON_AC11.match(x))
    return texto.replace(cabecera, cabecera + "\n\n" + cabecera, 1)


MUTANTES_CONSUMIDOR: tuple[Mutante, ...] = (
    Mutante("metodo-en-el-enunciado", _mut_metodo_en_el_enunciado, "prescribe un método"),
    Mutante("ancla-divergente", _mut_ancla_divergente, "ancla el contrato"),
    Mutante("ancla-propia-en-el-enunciado", _mut_ancla_propia_en_el_enunciado,
            "ancla un contrato propio y divergente"),
    Mutante("sin-ac-11", _mut_sin_ac11, "no se encontró el ítem"),
    Mutante("ac-11-duplicado", _mut_ac11_duplicado, "más de una vez"),
)


def _comprobar_recorte_vigente() -> list[str]:
    """El recorte versionado tiene que seguir siendo el enunciado que la spec real tiene hoy.

    Un fixture escrito por quien escribe el verificador prueba consistencia interna, no que el
    predicado pase sobre un texto ajeno. Acá el fixture **es** una copia literal del texto ajeno, y
    esto es lo que caza que haya dejado de serlo.
    """
    if not RUTA_SPEC_CONSUMIDOR.is_file():
        return ["AVISO  la spec real no está en el árbol: el recorte no se pudo contrastar"]

    real, err_real = extraer_enunciado_ac11(RUTA_SPEC_CONSUMIDOR.read_text(encoding="utf-8"))
    copia, err_copia = extraer_enunciado_ac11(RUTA_RECORTE.read_text(encoding="utf-8"))
    if err_real:
        return [f"FALLA  la spec real no expone su enunciado de AC-11: {err_real}"]
    if err_copia:
        return [f"FALLA  el recorte no expone su enunciado de AC-11: {err_copia}"]
    assert real is not None and copia is not None
    if real.texto != copia.texto:
        return ["FALLA  el recorte versionado ya no es el enunciado vigente de la spec real: "
                f"regenerarlo desde {RUTA_SPEC_CONSUMIDOR}"]
    return []


def modo_autotest_consumidor(args: argparse.Namespace) -> int:
    del args
    if not RUTA_RECORTE.is_file():
        print(f"FALLA  no existe el recorte versionado: {RUTA_RECORTE}")
        return 1

    fallas = 0
    for aviso in _comprobar_recorte_vigente():
        print(aviso)
        if aviso.startswith("FALLA"):
            fallas += 1

    base = RUTA_RECORTE.read_text(encoding="utf-8")

    # Control positivo: el recorte **incluye** la nota histórica que cita el método retirado, y
    # tiene que salir verde. Es el único control que caza un predicado que confunda el artefacto
    # prescribiendo con el artefacto registrando que dejó de prescribir.
    hallazgos = revisar_consumidor(base, "recorte")
    if hallazgos:
        print("FALLA  positivo: el recorte alineado —con su nota histórica— da hallazgos:")
        for h in hallazgos:
            print(f"       - {h}")
        fallas += 1
    else:
        print("OK     positivo: el recorte alineado pasa, y su nota histórica no lo pone rojo")

    for mutante in MUTANTES_CONSUMIDOR:
        mutado = mutante.aplicar(base)
        if mutado == base:
            print(f"FALLA  {mutante.nombre}: la mutación no se aplicó — el ancla que busca ya no "
                  "está en el recorte")
            fallas += 1
            continue
        hallazgos = revisar_consumidor(mutado, "recorte")
        if not hallazgos:
            print(f"FALLA  {mutante.nombre}: el predicado sigue verde sobre el mutante")
            fallas += 1
        elif not any(mutante.causa in h for h in hallazgos):
            print(f"FALLA  {mutante.nombre}: falla, pero por otra causa — se esperaba "
                  f"«{mutante.causa}» y llegó: {hallazgos}")
            fallas += 1
        else:
            print(f"OK     {mutante.nombre}: rojo por su propia causa")

    print()
    total = len(MUTANTES_CONSUMIDOR) + 1
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de `--consumidor` no se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de `--consumidor` pasan")
    return 0


# ---------------------------------------------------------------------------------------------
# Validador de JSON Schema. Subconjunto de 2020-12: lo que estos schemas usan y nada más. Toda
# palabra clave fuera de `PALABRAS_SOPORTADAS` es un error del schema, no una anotación inocua:
# ignorarla en silencio deja escrita una restricción que nadie aplica, que es peor que no haberla
# escrito. **Portado y no importado** desde `scripts/instrumento-baseline.py` — ver el docstring.
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


def _resolver(schema: dict, ref: str) -> dict:
    if not ref.startswith("#/$defs/"):
        raise ValueError(f"referencia no local o no soportada: {ref}")
    nombre = ref[len("#/$defs/"):]
    defs = schema.get("$defs", {})
    if nombre not in defs:
        raise ValueError(f"referencia a un `$defs` inexistente: {ref}")
    return defs[nombre]


def validar(instancia: object, schema: dict) -> list[Error]:
    """Valida `instancia` contra `schema`, que es el schema raíz."""
    return _validar(instancia, schema, schema, ())


def _validar(valor: object, esquema: dict, schema: dict, ruta: Ruta) -> list[Error]:
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
            # Cuál rama se reporta no lo decide el conteo de errores —eso atribuye mal en cuanto
            # dos ramas fallan con uno cada una— sino el discriminador.
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
            errores.append(Error(ruta, "el arreglo declara `uniqueItems` y tiene elementos "
                                       "repetidos"))
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


class SubEsquema(NamedTuple):
    definicion: str
    puntero: tuple
    esquema: dict
    en_condicion: bool  # True dentro de un `if`: ahí `properties` es una pregunta, no una forma


def _recorrer(nombre: str, esquema: dict, puntero: tuple) -> list[SubEsquema]:
    salida: list[SubEsquema] = []

    def caminar(sub: object, punt: tuple, en_condicion: bool) -> None:
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
            f"instancia debe declarar ({declarada!r})")

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


# ---------------------------------------------------------------------------------------------
# La lectura única instrumentada (D4). Toda producción de este flujo pasa por acá.
# ---------------------------------------------------------------------------------------------
#
# El `sha256`, el tamaño, el parseo y los rangos que AC-12 copia salen del **mismo buffer**, y el
# lector deja escrito de qué buffer salió cada cosa. Sin ese registro, el autotest probaría que el
# código *soporta* lectura única y no que la corrida productiva la *usó*: el productor real podría
# tomar otra ruta y los artefactos congelados quedar sin cubrir.

class Lectura(NamedTuple):
    ruta: str
    contenido: bytes
    identidad: str  # persistible: viaja a los artefactos congelados
    token: int      # en proceso: distingue dos buffers de contenido idéntico

    @property
    def sha256(self) -> str:
        return self.identidad.split(":", 1)[1]

    @property
    def tamano(self) -> int:
        return len(self.contenido)


class Derivacion(NamedTuple):
    ruta: str
    clase: str            # "hash" | "rango" | "parseo"
    detalle: str
    identidad: str | None
    token: int | None


class Lector:
    """La única puerta de lectura del corpus, con su libro de identidades.

    No es una envoltura de `open()`: es lo que permite afirmar, sobre los artefactos ya congelados,
    que el hash registrado y el rango copiado salieron del mismo acto de lectura.
    """

    def __init__(self) -> None:
        # Por ruta, **todos** los buffers que entraron por ella. Que la lista tenga más de uno es
        # exactamente la violación: dos aperturas de la misma ruta pueden traer bytes distintos.
        self._lecturas: dict[str, list[Lectura]] = {}
        self._derivaciones: list[Derivacion] = []
        self._siguiente_token = 1

    def leer_una_vez(self, ruta: Path) -> Lectura:
        """Devuelve el buffer de esa ruta. Si ya se leyó, **el mismo**: no vuelve a abrir.

        Que un consumidor la llame dos veces no es una violación —recibe el mismo objeto— y por
        eso no se registra como tal. La violación es que entre un buffer **distinto** para la misma
        ruta, que es lo que abrir de nuevo produce.
        """
        clave = str(ruta)
        if clave in self._lecturas:
            return self._lecturas[clave][0]
        return self._abrir(clave, ruta)

    def _abrir(self, clave: str, ruta: Path) -> Lectura:
        contenido = ruta.read_bytes()
        lectura = Lectura(clave, contenido, "sha256:" + _sha256_de(contenido),
                          self._siguiente_token)
        self._siguiente_token += 1
        self._lecturas.setdefault(clave, []).append(lectura)
        return lectura

    def derivar(self, lectura: Lectura, clase: str, detalle: str) -> Derivacion:
        derivacion = Derivacion(lectura.ruta, clase, detalle, lectura.identidad, lectura.token)
        self._derivaciones.append(derivacion)
        return derivacion

    # -- ganchos de mutación: el autotest los usa para forzar cada modo de fallo por separado --

    def _forzar_segunda_apertura(self, ruta: Path) -> None:
        self._abrir(str(ruta), ruta)

    def _borrar_identidad(self, indice: int) -> None:
        d = self._derivaciones[indice]
        self._derivaciones[indice] = d._replace(identidad=None, token=None)

    def _discordar_identidad(self, indice: int, identidad: str) -> None:
        self._derivaciones[indice] = self._derivaciones[indice]._replace(identidad=identidad)

    def _reapuntar_token(self, indice: int, token: int) -> None:
        self._derivaciones[indice] = self._derivaciones[indice]._replace(token=token)

    def auditar(self) -> list[str]:
        """Los hallazgos del libro de lectura. Lista vacía es una producción de una sola lectura."""
        hallazgos: list[str] = []

        for ruta, buffers in sorted(self._lecturas.items()):
            if len(buffers) > 1:
                hallazgos.append(f"apertura-repetida: {ruta} se abrió {len(buffers)} veces; el "
                                 "hash y los rangos podrían salir de bytes distintos")

        for derivacion in self._derivaciones:
            etiqueta = f"{derivacion.clase} de {derivacion.ruta} ({derivacion.detalle})"
            if derivacion.identidad is None or derivacion.token is None:
                hallazgos.append(f"identidad-ausente: la derivación {etiqueta} no registra de qué "
                                 "buffer salió")
                continue
            buffers = self._lecturas.get(derivacion.ruta)
            if not buffers:
                hallazgos.append(f"identidad-discordante: la derivación {etiqueta} no tiene "
                                 "lectura registrada para esa ruta")
                continue
            if derivacion.identidad != buffers[0].identidad:
                hallazgos.append(f"identidad-discordante: la derivación {etiqueta} declara "
                                 f"{derivacion.identidad} y el buffer leído fue "
                                 f"{buffers[0].identidad}")

        por_ruta: dict[str, set[int]] = {}
        for derivacion in self._derivaciones:
            if derivacion.token is not None:
                por_ruta.setdefault(derivacion.ruta, set()).add(derivacion.token)
        for ruta, tokens in sorted(por_ruta.items()):
            if len(tokens) > 1:
                hallazgos.append(f"buffers-distintos: las derivaciones de {ruta} salen de "
                                 f"{len(tokens)} buffers distintos ({sorted(tokens)})")

        return hallazgos

    def enlaces(self) -> dict[str, str]:
        """La identidad de lectura por ruta, tal como viaja a los artefactos congelados."""
        return {ruta: buffers[0].identidad for ruta, buffers in sorted(self._lecturas.items())}


# ---------------------------------------------------------------------------------------------
# Modo `--autotest-lectura-unica` (V28).
# ---------------------------------------------------------------------------------------------

def _lector_de_prueba(base: Path) -> tuple[Lector, Path]:
    """Un lector con una producción normal ya hecha: una lectura, su hash y dos rangos."""
    artefacto = base / "tasks.md"
    artefacto.write_bytes(b"- [ ] **T1 - algo**\n  . cubre: AC-1\n")
    lector = Lector()
    lectura = lector.leer_una_vez(artefacto)
    lector.derivar(lectura, "hash", lectura.sha256)
    lector.derivar(lectura, "rango", "0:19")
    lector.derivar(lectura, "rango", "20:38")
    return lector, artefacto


def modo_autotest_lectura_unica(args: argparse.Namespace) -> int:
    del args

    mutaciones: tuple[tuple[str, Callable[[Lector, Path], None], str], ...] = (
        ("segunda-apertura", lambda lector, ruta: lector._forzar_segunda_apertura(ruta),
         "apertura-repetida"),
        ("identidad-ausente", lambda lector, ruta: lector._borrar_identidad(1),
         "identidad-ausente"),
        ("identidad-discordante",
         lambda lector, ruta: lector._discordar_identidad(1, "sha256:" + "f" * 64),
         "identidad-discordante"),
        ("hash-y-rango-de-buffers-distintos",
         lambda lector, ruta: lector._reapuntar_token(1, 99),
         "buffers-distintos"),
    )

    fallas = 0
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        lector, _ = _lector_de_prueba(base)
        hallazgos = lector.auditar()
        if hallazgos:
            print("FALLA  positivo: una producción de una sola lectura da hallazgos:")
            for h in hallazgos:
                print(f"       - {h}")
            fallas += 1
        else:
            print("OK     positivo: hash y rangos del mismo buffer pasan la auditoría")

        for nombre, mutar, causa in mutaciones:
            lector, artefacto = _lector_de_prueba(base)
            mutar(lector, artefacto)
            hallazgos = lector.auditar()
            if not hallazgos:
                print(f"FALLA  {nombre}: la auditoría sigue verde sobre el mutante")
                fallas += 1
            elif not any(h.startswith(causa) for h in hallazgos):
                print(f"FALLA  {nombre}: falla, pero por otra causa — se esperaba «{causa}» y "
                      f"llegó: {hallazgos}")
                fallas += 1
            else:
                print(f"OK     {nombre}: rojo por su propia causa")

    print()
    total = len(mutaciones) + 1
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de la lectura única no se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de la lectura única pasan")
    return 0


# ---------------------------------------------------------------------------------------------
# Modo `--autotest-elegibilidad` (V2). El control positivo del predicado de AC-4bis.
# ---------------------------------------------------------------------------------------------
#
# El predicado se **importa** del comando que lo implementa, no se copia. Acá no rige la política
# de portar: esa política existe para no acoplar este flujo a un archivo congelado y ajeno, y
# `oraculo-elegibilidad.py` es de este mismo flujo. Una copia probaría la copia.

def _cargar_elegibilidad():
    import importlib.util

    ruta = DIR_SCRIPTS / "oraculo-elegibilidad.py"
    spec = importlib.util.spec_from_file_location("oraculo_elegibilidad", ruta)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"no se pudo cargar {ruta}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class CasoElegibilidad(NamedTuple):
    nombre: str
    construir: Callable[[Path], None]
    motivo_esperado: str   # `elegible`, o el prefijo del motivo de descarte


def _escribir(directorio: Path, nombres: tuple[str, ...], contenido: bytes = b"# algo\n") -> None:
    directorio.mkdir(parents=True, exist_ok=True)
    for nombre in nombres:
        (directorio / nombre).write_bytes(contenido)


CASOS_ELEGIBILIDAD: tuple[CasoElegibilidad, ...] = (
    CasoElegibilidad("los-tres-presentes",
                     lambda d: _escribir(d, ("spec.md", "plan.md", "tasks.md")),
                     "elegible"),
    CasoElegibilidad("dos-de-tres",
                     lambda d: _escribir(d, ("spec.md", "plan.md")),
                     "faltan 1 de 3"),
    CasoElegibilidad("uno-de-tres",
                     lambda d: _escribir(d, ("spec.md",)),
                     "faltan 2 de 3"),
    CasoElegibilidad("ninguno",
                     lambda d: d.mkdir(parents=True, exist_ok=True),
                     "faltan 3 de 3"),
    CasoElegibilidad("uno-vacio",
                     lambda d: (_escribir(d, ("spec.md", "plan.md")),
                                (d / "tasks.md").write_bytes(b""))[-1],
                     "artefacto vacío"),
    CasoElegibilidad("uno-symlink",
                     lambda d: (_escribir(d, ("spec.md", "plan.md", "real.md")),
                                (d / "tasks.md").symlink_to(d / "real.md"))[-1],
                     "artefacto no regular"),
)


def _clasificar_en(modulo, base: Path, slug: str, leer=None) -> str:
    flujo = next(f for f in modulo.enumerar_flujos(base) if f.slug == slug)
    return modulo.clasificar(flujo, leer) if leer else modulo.clasificar(flujo)


def modo_autotest_elegibilidad(args: argparse.Namespace) -> int:
    del args
    modulo = _cargar_elegibilidad()
    fallas = 0

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "archived").mkdir()

        for caso in CASOS_ELEGIBILIDAD:
            caso.construir(base / caso.nombre)
        # Cada rama estructural se ejerce **también dentro de `archived/`**: el corte de contenedor
        # no puede cambiar la clasificación, y si la cambiara nadie lo notaría.
        _escribir(base / "archived" / "archivado-completo", ("spec.md", "plan.md", "tasks.md"))
        # La rama de fase: el mismo contenido, dos veces, y solo el slug decide.
        for slug in modulo.SLUGS_FASE_05:
            _escribir(base / slug, ("spec.md", "plan.md", "tasks.md"))
        _escribir(base / "archived" / modulo.SLUGS_FASE_05[0],
                  ("spec.md", "plan.md", "tasks.md"))

        esperados: list[tuple[str, str]] = [(c.nombre, c.motivo_esperado)
                                            for c in CASOS_ELEGIBILIDAD]
        esperados.append(("archived/archivado-completo", "elegible"))
        esperados.extend((slug, "pertenece a la Fase 0.5") for slug in modulo.SLUGS_FASE_05)
        esperados.append((f"archived/{modulo.SLUGS_FASE_05[0]}", "pertenece a la Fase 0.5"))

        for slug, esperado in esperados:
            obtenido = _clasificar_en(modulo, base, slug)
            if obtenido.startswith(esperado):
                print(f"OK     {slug}: {obtenido}")
            else:
                print(f"FALLA  {slug}: se esperaba «{esperado}» y llegó «{obtenido}»")
                fallas += 1

        # El contenedor no es un flujo. Deducirlo de que le faltan los artefactos sería frágil:
        # un `spec.md` suelto ahí lo convertiría en candidato.
        slugs = {f.slug for f in modulo.enumerar_flujos(base)}
        if "archived" in slugs:
            print("FALLA  `archived` se enumeró como flujo: es el contenedor")
            fallas += 1
        else:
            print("OK     contenedor: `archived` no se enumera como flujo")

        # Los tres errores de lectura **abortan**; ninguno degrada a «no elegible».
        completo = base / "los-tres-presentes"
        lecturas: tuple[tuple[str, Callable[[Path], bytes], str], ...] = (
            ("apertura-fallida",
             _lector_que_falla(PermissionError(13, "permiso denegado")), "apertura fallida"),
            ("desaparicion-durante-el-recorrido",
             _lector_que_falla(FileNotFoundError(2, "no existe")), "desapareció durante"),
            ("bytes-no-decodificables",
             lambda ruta: b"\xff\xfe\x00binario", "no decodificables"),
        )
        for nombre, leer, causa in lecturas:
            try:
                obtenido = _clasificar_en(modulo, base, completo.name, leer)
            except modulo.ErrorDeRecorrido as exc:
                if causa in str(exc):
                    print(f"OK     {nombre}: aborta por su propia causa")
                else:
                    print(f"FALLA  {nombre}: aborta, pero por otra causa — «{exc}»")
                    fallas += 1
            else:
                print(f"FALLA  {nombre}: degradó a «{obtenido}» en vez de abortar")
                fallas += 1

    print()
    total = len(esperados) + 1 + len(lecturas)
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} ramas del predicado no se comportan como "
              "AC-4bis las define")
        return 1
    print(f"RESULTADO: OK — las {total} ramas del predicado se comportan como AC-4bis las define")
    return 0


def _lector_que_falla(error: OSError) -> Callable[[Path], bytes]:
    def leer(ruta: Path) -> bytes:
        raise error
    return leer


# ---------------------------------------------------------------------------------------------
# La población del corpus: encabezados de task (R1) y expansión en ternas.
# ---------------------------------------------------------------------------------------------
#
# **Esto no es el parser.** El parser —extracción de cobertura R2, piezas, dossier— es de
# `dossier-arnes` y este flujo no lo toca (AC-15). Lo que hay acá es la gramática de **encabezado**
# de R1, que es lo mínimo para enumerar la población que AC-4 manda congelar y para comprobar la
# cuarta invariante de AC-5: que cada `(task_id, ocurrencia)` exista literalmente en el `tasks.md`
# sellado. R6 lo admite explícitamente: verificar el contrato contra artefactos no es implementarlo.

RUTA_CORPUS = DIR_SCRIPTS / "corpus-dossier.json"
RUTA_ELEGIBLES = DIR_SCRIPTS / "corpus-elegibles.json"
DIR_PLANS = RAIZ / ".plans"
ARTEFACTOS = ("spec.md", "plan.md", "tasks.md")

# Las dos formas de encabezado de task que R1 fija. El sufijo es parte del id y las mayúsculas
# también: `T15A` y `T15a` son ids distintos.
PATRON_TASK_VINETA = re.compile(r"^\s*- \[[ xX]\] \*\*(T\d+[A-Za-z]*)\b")
PATRON_TASK_HEADING = re.compile(r"^#{2,6} +(T\d+[A-Za-z]*)\b")


class Terna(NamedTuple):
    flujo: str
    task_id: str
    ocurrencia: int

    def como_dict(self) -> dict:
        return {"flujo": self.flujo, "task_id": self.task_id, "ocurrencia": self.ocurrencia}


def encabezados_de_task(texto: str) -> list[tuple[str, int]]:
    """Los `(task_id, ocurrencia)` del `tasks.md`, en orden de aparición.

    `ocurrencia` es 1-indexada **por id**: la segunda vez que aparece `T3` es `(T3, 2)`. Es lo que
    vuelve identificable una task repetida sin duplicar la terna.
    """
    vistos: dict[str, int] = {}
    salida: list[tuple[str, int]] = []
    for linea in texto.split("\n"):
        encontrado = PATRON_TASK_VINETA.match(linea) or PATRON_TASK_HEADING.match(linea)
        if not encontrado:
            continue
        task_id = encontrado.group(1)
        vistos[task_id] = vistos.get(task_id, 0) + 1
        salida.append((task_id, vistos[task_id]))
    return salida


# La proyección canónica del corpus, declarada. AC-6 lo exige textualmente: decir «el sha256 del
# corpus» deja abierto si es el del JSON, el de sus bytes canónicos o el del conjunto ordenado de
# artefactos — y dos implementaciones sellan objetos distintos afirmando las dos que sellaron el
# corpus. Esta cadena viaja **dentro** del oráculo, en `procedencia.proyeccion_canonica`.
PROYECCION_CANONICA = (
    "sha256 sobre la concatenación, sin separador adicional, de una línea "
    "`<flujo>\\t<artefacto>\\t<sha256>\\t<tamano>\\n` por cada artefacto sellado del manifest de "
    "corpus, ordenadas ascendentemente por el par (flujo, artefacto) comparado sobre su "
    "codificación UTF-8, y codificadas en UTF-8 sin BOM. Se incluyen ruta lógica, identidad de "
    "contenido y tamaño; se excluye todo lo demás del manifest."
)


def identidad_canonica_del_corpus(corpus: dict) -> str:
    """La identidad del corpus según `PROYECCION_CANONICA`. Es la que liga oráculo y evidencia."""
    filas = []
    for flujo in corpus.get("flujos", []):
        for artefacto in flujo.get("artefactos", []):
            filas.append((flujo["flujo"].encode("utf-8"), artefacto["artefacto"].encode("utf-8"),
                          artefacto["sha256"], artefacto["tamano"]))
    filas.sort(key=lambda f: (f[0], f[1]))
    proyeccion = b"".join(
        f[0] + b"\t" + f[1] + b"\t" + f[2].encode("utf-8") + b"\t"
        + str(f[3]).encode("utf-8") + b"\n" for f in filas)
    return "sha256:" + _sha256_de(proyeccion)


def bloques_de_task(contenido: bytes) -> list[tuple[str, int, int, int]]:
    """`(task_id, ocurrencia, inicio, fin)` en **bytes**, con el corte de bloque de R1.

    El bloque de una task va desde su encabezado hasta el próximo encabezado que satisfaga la misma
    gramática. Es lo que permite decir que un rango pertenece a *esta* terna y no a otra que
    contiene el mismo texto — que en este corpus es lo habitual, porque las formas se repiten.
    """
    encabezados: list[tuple[str, int, int]] = []
    vistos: dict[str, int] = {}
    desplazamiento = 0
    for linea in contenido.split(b"\n"):
        try:
            texto = linea.decode("utf-8")
        except UnicodeDecodeError:
            texto = ""
        encontrado = PATRON_TASK_VINETA.match(texto) or PATRON_TASK_HEADING.match(texto)
        if encontrado:
            task_id = encontrado.group(1)
            vistos[task_id] = vistos.get(task_id, 0) + 1
            encabezados.append((task_id, vistos[task_id], desplazamiento))
        desplazamiento += len(linea) + 1  # el `\n` que `split` consumió

    salida = []
    for i, (task_id, ocurrencia, inicio) in enumerate(encabezados):
        fin = encabezados[i + 1][2] if i + 1 < len(encabezados) else len(contenido)
        salida.append((task_id, ocurrencia, inicio, fin))
    return salida


def ruta_de_artefacto(flujo: str, artefacto: str) -> Path:
    """La ruta canónica de un artefacto. Es la única forma admitida en el manifest."""
    return DIR_PLANS / flujo / artefacto


def expandir_poblacion(flujos: list[str],
                       lector: "Lector | None" = None) -> tuple[list[Terna], list[str]]:
    """Las ternas del universo dado, leyendo cada `tasks.md` **una sola vez**."""
    lector = lector or Lector()
    ternas: list[Terna] = []
    errores: list[str] = []
    for flujo in flujos:
        ruta = ruta_de_artefacto(flujo, "tasks.md")
        try:
            lectura = lector.leer_una_vez(ruta)
        except OSError as exc:
            errores.append(f"{flujo}/tasks.md: no se pudo leer ({exc})")
            continue
        try:
            texto = lectura.contenido.decode("utf-8")
        except UnicodeDecodeError as exc:
            errores.append(f"{flujo}/tasks.md: bytes no decodificables ({exc})")
            continue
        for task_id, ocurrencia in encabezados_de_task(texto):
            ternas.append(Terna(flujo, task_id, ocurrencia))
            lector.derivar(lectura, "terna", f"{task_id}#{ocurrencia}")
    return ternas, errores


# ---------------------------------------------------------------------------------------------
# Modo `--proyecciones` (V3) y `--autotest-proyecciones` (V4).
# ---------------------------------------------------------------------------------------------
#
# Son **dos** proyecciones con responsabilidades distintas, y su alcance está partido a propósito
# para que cada mutante caiga en la suya:
#
# - **elegibilidad** — el snapshot congelado contra la regla ejecutada. Es la única que mira
#   `corpus-elegibles.json`.
# - **población** — el manifest contra la expansión normativa del universo elegible, tomado de la
#   **regla**, no del snapshot. Si tomara el snapshot, quitarle un flujo pondría rojas las dos y el
#   autotest no podría probar que cada mutante cae en su propia proyección.
#
# Cuando las dos están verdes, snapshot y regla son el mismo universo, así que la segunda lectura no
# afloja nada: lo que compra es aislamiento causal.

def _comparar_conjuntos(nombre: str, esperado: set, obtenido: set,
                        formatear: Callable[[object], str] = str) -> list[str]:
    """Igualdad bidireccional, nombrando faltantes y sobrantes. Nunca cardinalidades."""
    hallazgos = []
    for faltante in sorted(esperado - obtenido, key=formatear):
        hallazgos.append(f"{nombre}: falta {formatear(faltante)}")
    for sobrante in sorted(obtenido - esperado, key=formatear):
        hallazgos.append(f"{nombre}: sobra {formatear(sobrante)}")
    return hallazgos


def _elegibles_de_la_regla() -> tuple[list[str], str | None]:
    modulo = _cargar_elegibilidad()
    try:
        return modulo.snapshot()["elegibles"], None
    except modulo.ErrorDeRecorrido as exc:
        return [], f"la regla abortó su recorrido: {exc}"


def _ternas_del_manifest(manifest: dict) -> set[Terna]:
    return {Terna(t["flujo"], t["task_id"], t["ocurrencia"]) for t in manifest.get("ternas", [])}


def revisar_proyecciones(snapshot: dict, manifest: dict) -> list[str]:
    hallazgos: list[str] = []

    de_la_regla, error = _elegibles_de_la_regla()
    if error:
        return [error]

    hallazgos.extend(_comparar_conjuntos(
        "proyección elegibilidad", set(de_la_regla), set(snapshot.get("elegibles", []))))

    universo = sorted(de_la_regla)
    esperadas, errores = expandir_poblacion(universo)
    hallazgos.extend(f"proyección población: {e}" for e in errores)
    hallazgos.extend(_comparar_conjuntos(
        "proyección población", set(esperadas), _ternas_del_manifest(manifest),
        formatear=lambda t: f"{t.flujo}/{t.task_id}#{t.ocurrencia}"))

    declarados = {f["flujo"] for f in manifest.get("flujos", [])}
    hallazgos.extend(_comparar_conjuntos(
        "proyección población (flujos)", set(universo), declarados))

    return hallazgos


def modo_proyecciones(args: argparse.Namespace) -> int:
    del args
    snapshot, err_s = _cargar_json(RUTA_ELEGIBLES)
    manifest, err_m = _cargar_json(RUTA_CORPUS)
    for error in (err_s, err_m):
        if error:
            print(f"FALLA  {error}")
    if err_s or err_m:
        return 1

    hallazgos = revisar_proyecciones(snapshot, manifest)
    for h in hallazgos:
        print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} discrepancias en las dos proyecciones de AC-4")
        return 1
    print(f"RESULTADO: OK — las dos proyecciones de AC-4 cierran bidireccionalmente "
          f"({len(snapshot['elegibles'])} flujos, {len(manifest['ternas'])} ternas)")
    return 0


def modo_autotest_proyecciones(args: argparse.Namespace) -> int:
    del args
    snapshot, err_s = _cargar_json(RUTA_ELEGIBLES)
    manifest, err_m = _cargar_json(RUTA_CORPUS)
    if err_s or err_m:
        print(f"FALLA  {err_s or err_m}")
        return 1

    fallas = 0
    hallazgos = revisar_proyecciones(snapshot, manifest)
    if hallazgos:
        print("FALLA  positivo: los artefactos vigentes no cierran:")
        for h in hallazgos:
            print(f"       - {h}")
        fallas += 1
    else:
        print("OK     positivo: snapshot y manifest vigentes cierran las dos proyecciones")

    import copy

    quitado = copy.deepcopy(snapshot)
    victima = quitado["elegibles"].pop()
    agregado = copy.deepcopy(manifest)
    intrusa = {"flujo": agregado["ternas"][0]["flujo"], "task_id": "T999", "ocurrencia": 1}
    agregado["ternas"].append(intrusa)

    mutantes = (
        ("flujo-quitado-del-snapshot", quitado, manifest, "proyección elegibilidad",
         "proyección población"),
        ("terna-agregada-al-manifest", snapshot, agregado, "proyección población",
         "proyección elegibilidad"),
    )
    for nombre, snap, man, propia, ajena in mutantes:
        hallazgos = revisar_proyecciones(snap, man)
        propias = [h for h in hallazgos if h.startswith(propia)]
        ajenas = [h for h in hallazgos if h.startswith(ajena)]
        if not propias:
            print(f"FALLA  {nombre}: «{propia}» no se puso roja ({hallazgos})")
            fallas += 1
        elif ajenas:
            print(f"FALLA  {nombre}: puso roja también «{ajena}» ({ajenas})")
            fallas += 1
        else:
            print(f"OK     {nombre}: solo «{propia}» se puso roja — {propias[0]}")

    del victima
    print()
    total = len(mutantes) + 1
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de las proyecciones no se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de las proyecciones pasan")
    return 0


# ---------------------------------------------------------------------------------------------
# Modo `--invariantes-corpus` (V5) y `--autotest-invariantes-corpus` (V6).
# ---------------------------------------------------------------------------------------------
#
# Las **cuatro** de AC-5, comprobadas por separado y nombrando el registro infractor. Cada una
# tiene su prefijo de mensaje, porque un autotest que solo mirara el código de salida no
# distinguiría «falló» de «falló por esta causa».

INV_TERNA_REPETIDA = "terna-repetida"
INV_ARTEFACTOS_DEL_FLUJO = "artefactos-del-flujo"
INV_IDENTIDAD_MULTIPLE = "identidad-multiple"
INV_TERNA_SIN_RESPALDO = "terna-sin-respaldo"


def revisar_invariantes_corpus(manifest: dict) -> list[str]:
    hallazgos: list[str] = []

    vistas: dict[tuple, int] = {}
    for terna in manifest.get("ternas", []):
        clave = (terna["flujo"], terna["task_id"], terna["ocurrencia"])
        vistas[clave] = vistas.get(clave, 0) + 1
    for clave, veces in sorted(vistas.items()):
        if veces > 1:
            hallazgos.append(f"{INV_TERNA_REPETIDA}: la terna {clave[0]}/{clave[1]}#{clave[2]} "
                             f"aparece {veces} veces")

    por_ruta: dict[str, set[str]] = {}
    for flujo in manifest.get("flujos", []):
        # La segunda invariante es sobre **cuáles** artefactos, y la tercera sobre **cuántas
        # identidades** tiene cada uno. Compararlas como listas fundía las dos: una entrada
        # repetida rompía las dos a la vez y ningún mutante podía aislar su causa.
        nombres = [a["artefacto"] for a in flujo.get("artefactos", [])]
        if set(nombres) != set(ARTEFACTOS):
            hallazgos.append(f"{INV_ARTEFACTOS_DEL_FLUJO}: {flujo['flujo']} declara "
                             f"{sorted(set(nombres))} y no exactamente {sorted(ARTEFACTOS)}")
        for artefacto in flujo.get("artefactos", []):
            esperada = str(ruta_de_artefacto(flujo["flujo"], artefacto["artefacto"])
                           .relative_to(RAIZ))
            if artefacto["ruta"] != esperada:
                hallazgos.append(f"{INV_ARTEFACTOS_DEL_FLUJO}: {flujo['flujo']}/"
                                 f"{artefacto['artefacto']} declara la ruta {artefacto['ruta']} y "
                                 f"la canónica es {esperada}")
            por_ruta.setdefault(artefacto["ruta"], set()).add(artefacto["sha256"])
            if artefacto["identidad_lectura"] != "sha256:" + artefacto["sha256"]:
                hallazgos.append(f"{INV_IDENTIDAD_MULTIPLE}: {artefacto['ruta']} sella el hash "
                                 f"{artefacto['sha256']} y declara haberlo derivado del buffer "
                                 f"{artefacto['identidad_lectura']}")

    for ruta, identidades in sorted(por_ruta.items()):
        if len(identidades) > 1:
            hallazgos.append(f"{INV_IDENTIDAD_MULTIPLE}: {ruta} tiene {len(identidades)} "
                             f"identidades de contenido distintas ({sorted(identidades)})")

    sellos = {(f["flujo"], a["artefacto"]): a
              for f in manifest.get("flujos", []) for a in f.get("artefactos", [])}
    por_flujo: dict[str, list[dict]] = {}
    for terna in manifest.get("ternas", []):
        por_flujo.setdefault(terna["flujo"], []).append(terna)
    lector = Lector()
    for flujo, ternas in sorted(por_flujo.items()):
        sello = sellos.get((flujo, "tasks.md"))
        if sello is None:
            hallazgos.append(f"{INV_TERNA_SIN_RESPALDO}: {flujo} tiene ternas y no sella su "
                             "tasks.md")
            continue
        ruta = RAIZ / sello["ruta"]
        try:
            lectura = lector.leer_una_vez(ruta)
        except OSError as exc:
            hallazgos.append(f"{INV_TERNA_SIN_RESPALDO}: {sello['ruta']} no se pudo leer ({exc})")
            continue
        if lectura.sha256 != sello["sha256"]:
            hallazgos.append(f"{INV_TERNA_SIN_RESPALDO}: {sello['ruta']} vale hoy "
                             f"{lectura.sha256[:12]}… y el manifest selló {sello['sha256'][:12]}…")
            continue
        presentes = set(encabezados_de_task(lectura.contenido.decode("utf-8")))
        for terna in ternas:
            if (terna["task_id"], terna["ocurrencia"]) not in presentes:
                hallazgos.append(f"{INV_TERNA_SIN_RESPALDO}: {flujo}/{terna['task_id']}"
                                 f"#{terna['ocurrencia']} no existe literalmente en el tasks.md "
                                 "sellado por su propio sha256")

    return hallazgos


def modo_invariantes_corpus(args: argparse.Namespace) -> int:
    del args
    manifest, error = _cargar_json(RUTA_CORPUS)
    if error:
        print(f"FALLA  {error}")
        return 1
    hallazgos = revisar_invariantes_corpus(manifest)
    for h in hallazgos:
        print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} registros infractores de las cuatro "
              "invariantes de AC-5")
        return 1
    print("RESULTADO: OK — las cuatro invariantes de AC-5 se cumplen sobre "
          f"{len(manifest['ternas'])} ternas y {len(manifest['flujos'])} flujos")
    return 0


def modo_autotest_invariantes_corpus(args: argparse.Namespace) -> int:
    del args
    import copy

    manifest, error = _cargar_json(RUTA_CORPUS)
    if error:
        print(f"FALLA  {error}")
        return 1

    def _repetir_terna(m: dict) -> None:
        m["ternas"].append(dict(m["ternas"][0]))

    def _quitar_artefacto(m: dict) -> None:
        # Se quita `spec.md`, no `tasks.md`: sin el sello del `tasks.md` caería también la cuarta
        # invariante y el mutante dejaría de aislar su causa.
        indice = next(i for i, a in enumerate(m["flujos"][0]["artefactos"])
                      if a["artefacto"] == "spec.md")
        m["flujos"][0]["artefactos"].pop(indice)

    def _duplicar_identidad(m: dict) -> None:
        gemelo = copy.deepcopy(next(a for a in m["flujos"][0]["artefactos"]
                                    if a["artefacto"] == "spec.md"))
        gemelo["sha256"] = "0" * 64
        gemelo["identidad_lectura"] = "sha256:" + gemelo["sha256"]
        m["flujos"][0]["artefactos"].append(gemelo)

    def _inventar_terna(m: dict) -> None:
        m["ternas"].append({"flujo": m["ternas"][0]["flujo"], "task_id": "T4242",
                            "ocurrencia": 1})

    mutantes = (
        ("terna-repetida", _repetir_terna, INV_TERNA_REPETIDA),
        ("flujo-sin-los-tres", _quitar_artefacto, INV_ARTEFACTOS_DEL_FLUJO),
        ("artefacto-con-dos-identidades", _duplicar_identidad, INV_IDENTIDAD_MULTIPLE),
        ("terna-que-no-existe-en-el-tasks-sellado", _inventar_terna, INV_TERNA_SIN_RESPALDO),
    )

    fallas = 0
    hallazgos = revisar_invariantes_corpus(manifest)
    if hallazgos:
        print("FALLA  positivo: el manifest vigente infringe invariantes:")
        for h in hallazgos:
            print(f"       - {h}")
        fallas += 1
    else:
        print("OK     positivo: el manifest vigente cumple las cuatro invariantes")

    for nombre, mutar, causa in mutantes:
        mutado = copy.deepcopy(manifest)
        mutar(mutado)
        hallazgos = revisar_invariantes_corpus(mutado)
        propios = [h for h in hallazgos if h.startswith(causa)]
        ajenos = [h for h in hallazgos if not h.startswith(causa)]
        if not propios:
            print(f"FALLA  {nombre}: «{causa}» no se puso roja ({hallazgos[:3]})")
            fallas += 1
        elif ajenos:
            print(f"FALLA  {nombre}: además de «{causa}» se pusieron rojas otras ({ajenos[:3]})")
            fallas += 1
        else:
            print(f"OK     {nombre}: rojo por «{causa}» y solo por ella")

    print()
    total = len(mutantes) + 1
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de las invariantes no se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de las invariantes pasan")
    return 0


# ---------------------------------------------------------------------------------------------
# Modo `--insumos` (V7) y `--autotest-insumos` (V8). La validación agregada de AC-3.
# ---------------------------------------------------------------------------------------------

INSUMOS = ("corpus-dossier.json", "casos-extraccion.json", "oraculo-cobertura.json")
NOMBRE_EVIDENCIA = "oraculo-evidencia"
NOMBRE_MANIFEST_EVIDENCIA = "manifest.json"
DIR_EVIDENCIA = DIR_SCRIPTS / NOMBRE_EVIDENCIA

CAUSA_INSUMO_AUSENTE = "insumo-ausente"
CAUSA_SCHEMA_AUSENTE = "schema-ausente"
CAUSA_SCHEMA_INAPLICABLE = "schema-inaplicable"
CAUSA_INSTANCIA_INVALIDA = "instancia-invalida"
CAUSA_EVIDENCIA_AUSENTE = "evidencia-ausente"
CAUSA_ENLACE_LECTURA = "enlace-lectura"


def _revisar_enlace_de_lectura(base: Path) -> list[str]:
    """El enlace de D4 sobre los artefactos **reales**: cada rango declara el buffer del que salió.

    V28 prueba, en proceso, que la función instrumentada puede ponerse roja. Esto es lo otro que
    hace falta: que los artefactos ya congelados **declaren** el enlace y que el enlace cierre. Sin
    esto, la corrida productiva podría haber tomado otra ruta y nadie lo sabría.
    """
    corpus, err_c = _cargar_json(base / "corpus-dossier.json")
    casos, err_k = _cargar_json(base / "casos-extraccion.json")
    if err_c or err_k:
        return []  # la ausencia ya la reporta su propia causa

    sellado = {(f["flujo"], a["artefacto"]): a["identidad_lectura"]
               for f in corpus.get("flujos", []) for a in f.get("artefactos", [])}
    hallazgos: list[str] = []
    for caso in casos.get("casos", []):
        origen = caso.get("origen")
        if not origen:
            continue
        clave = (origen["flujo"], origen["artefacto"])
        esperada = sellado.get(clave)
        if esperada is None:
            hallazgos.append(f"{CAUSA_ENLACE_LECTURA}: el caso {caso['id']} copia de "
                             f"{clave[0]}/{clave[1]}, que el manifest de corpus no sella")
        elif origen["identidad_lectura"] != esperada:
            hallazgos.append(f"{CAUSA_ENLACE_LECTURA}: el caso {caso['id']} declara haber copiado "
                             f"del buffer {origen['identidad_lectura']} y el hash sellado de "
                             f"{clave[0]}/{clave[1]} salió de {esperada}")
    return hallazgos


def revisar_insumos(base: Path) -> list[str]:
    """Los cuatro artefactos y los tres schemas, en una sola pasada."""
    hallazgos: list[str] = []

    for nombre in INSUMOS:
        ruta = base / nombre
        ruta_schema = base / (nombre[:-len(".json")] + ".schema.json")

        instancia, err_i = _cargar_json(ruta)
        if err_i:
            hallazgos.append(f"{CAUSA_INSUMO_AUSENTE}: {nombre} — {err_i}")
            continue
        schema, err_s = _cargar_json(ruta_schema)
        if err_s:
            hallazgos.append(f"{CAUSA_SCHEMA_AUSENTE}: {ruta_schema.name} — {err_s}")
            continue

        # Una palabra clave que el validador no implementa **aborta** este insumo: seguir sería
        # aplicar un schema al que le falta una restricción que alguien escribió y nadie ejerce.
        problemas = verificar_schema(schema)
        if problemas:
            for p in problemas:
                hallazgos.append(f"{CAUSA_SCHEMA_INAPLICABLE}: {ruta_schema.name} — {p}")
            continue

        try:
            errores = validar(instancia, schema)
        except ValueError as exc:
            hallazgos.append(f"{CAUSA_SCHEMA_INAPLICABLE}: {ruta_schema.name} — {exc}")
            continue
        for error in errores:
            hallazgos.append(f"{CAUSA_INSTANCIA_INVALIDA}: {nombre} — {error}")

    evidencia = base / NOMBRE_EVIDENCIA
    manifest = evidencia / NOMBRE_MANIFEST_EVIDENCIA
    if not evidencia.is_dir():
        hallazgos.append(f"{CAUSA_EVIDENCIA_AUSENTE}: no existe el directorio {evidencia.name}/")
    elif not manifest.is_file():
        hallazgos.append(f"{CAUSA_EVIDENCIA_AUSENTE}: {evidencia.name}/ no tiene su "
                         f"{NOMBRE_MANIFEST_EVIDENCIA}")

    hallazgos.extend(_revisar_enlace_de_lectura(base))
    return hallazgos


def modo_insumos(args: argparse.Namespace) -> int:
    del args
    hallazgos = revisar_insumos(DIR_SCRIPTS)
    for h in hallazgos:
        print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} problemas en los cuatro artefactos de AC-3")
        return 1
    print(f"RESULTADO: OK — los {len(INSUMOS)} JSON validan contra sus schemas, la evidencia está "
          "y el enlace de lectura cierra")
    return 0


DIR_FIXTURE_INSUMOS = DIR_FIXTURES / "insumos"


def _comprobar_schemas_del_fixture() -> list[str]:
    """Los schemas del fixture son copias literales de los reales. Esto caza que dejen de serlo."""
    hallazgos = []
    for nombre in INSUMOS:
        schema = nombre[:-len(".json")] + ".schema.json"
        real = (DIR_SCRIPTS / schema).read_bytes()
        copia = (DIR_FIXTURE_INSUMOS / schema).read_bytes()
        if real != copia:
            hallazgos.append(f"FALLA  el fixture ya no lleva el schema vigente de {nombre}: "
                             f"regenerar {DIR_FIXTURE_INSUMOS.name}/{schema}")
    return hallazgos


def modo_autotest_insumos(args: argparse.Namespace) -> int:
    del args
    import shutil

    if not DIR_FIXTURE_INSUMOS.is_dir():
        print(f"FALLA  no existe el corpus sintético: {DIR_FIXTURE_INSUMOS}")
        return 1

    fallas = 0
    for aviso in _comprobar_schemas_del_fixture():
        print(aviso)
        fallas += 1

    def _borrar(nombre: str) -> Callable[[Path], None]:
        def mutar(base: Path) -> None:
            objetivo = base / nombre
            shutil.rmtree(objetivo) if objetivo.is_dir() else objetivo.unlink()
        return mutar

    def _palabra_desconocida(schema: str) -> Callable[[Path], None]:
        def mutar(base: Path) -> None:
            ruta = base / schema
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            datos["properties"]["version_schema"]["multipleOf"] = 1
            ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        return mutar

    def _romper_instancia(nombre: str) -> Callable[[Path], None]:
        def mutar(base: Path) -> None:
            ruta = base / nombre
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            datos["version_schema"] = "no-es-la-constante"
            ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        return mutar

    def _romper_enlace(base: Path) -> None:
        ruta = base / "casos-extraccion.json"
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["casos"][0]["origen"]["identidad_lectura"] = "sha256:" + "b" * 64
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    mutantes: list[tuple[str, Callable[[Path], None], str]] = []
    for nombre in INSUMOS:
        schema = nombre[:-len(".json")] + ".schema.json"
        mutantes.append((f"sin-{nombre}", _borrar(nombre), CAUSA_INSUMO_AUSENTE))
        mutantes.append((f"sin-{schema}", _borrar(schema), CAUSA_SCHEMA_AUSENTE))
        mutantes.append((f"palabra-desconocida-en-{schema}", _palabra_desconocida(schema),
                         CAUSA_SCHEMA_INAPLICABLE))
        mutantes.append((f"instancia-rota-{nombre}", _romper_instancia(nombre),
                         CAUSA_INSTANCIA_INVALIDA))
    mutantes.append(("sin-evidencia", _borrar(NOMBRE_EVIDENCIA), CAUSA_EVIDENCIA_AUSENTE))
    mutantes.append(("sin-manifest-de-evidencia",
                     _borrar(f"{NOMBRE_EVIDENCIA}/{NOMBRE_MANIFEST_EVIDENCIA}"),
                     CAUSA_EVIDENCIA_AUSENTE))
    mutantes.append(("enlace-de-lectura-roto", _romper_enlace, CAUSA_ENLACE_LECTURA))

    with tempfile.TemporaryDirectory() as tmp:
        limpio = Path(tmp) / "limpio"
        shutil.copytree(DIR_FIXTURE_INSUMOS, limpio)
        hallazgos = revisar_insumos(limpio)
        if hallazgos:
            print("FALLA  positivo: el corpus sintético íntegro da hallazgos:")
            for h in hallazgos:
                print(f"       - {h}")
            fallas += 1
        else:
            print("OK     positivo: el corpus sintético íntegro valida entero")

        for nombre, mutar, causa in mutantes:
            copia = Path(tmp) / nombre
            shutil.copytree(DIR_FIXTURE_INSUMOS, copia)
            mutar(copia)
            hallazgos = revisar_insumos(copia)
            propios = [h for h in hallazgos if h.startswith(causa)]
            ajenos = [h for h in hallazgos if not h.startswith(causa)]
            if not propios:
                print(f"FALLA  {nombre}: «{causa}» no se puso roja ({hallazgos[:2]})")
                fallas += 1
            elif ajenos:
                print(f"FALLA  {nombre}: además de «{causa}» se pusieron rojas otras ({ajenos[:2]})")
                fallas += 1
            else:
                print(f"OK     {nombre}: rojo por «{causa}» y solo por ella")

    print()
    total = len(mutantes) + 1
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de `--insumos` no se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de `--insumos` pasan")
    return 0


# ---------------------------------------------------------------------------------------------
# Modos `--forma-oraculo` (V9) / `--autotest-forma-oraculo` (V10) y `--proxies` (V20) /
# `--autotest-proxies` (V21).
# ---------------------------------------------------------------------------------------------
#
# Los **autotests** viven acá porque se escriben sobre el corpus sintético y no necesitan el
# oráculo real. Los **modos productivos** se corren en la task del oráculo completo: ejecutarlos en
# la task que escribió su autotest los habría corrido contra un archivo inexistente, y un error de
# integración habría entrado después de que sus filas ya pasaron.

DIR_COMPARACION = DIR_EVIDENCIA / "comparacion"
RUTA_COMPARACION = DIR_COMPARACION / "comparacion.json"
RUTA_ORACULO = DIR_SCRIPTS / "oraculo-cobertura.json"

PROXIES_DE_AC14 = (
    "gate_estructural_de_git",
    "oraculo_congelado_como_autoridad",
    "adjudicacion_del_conductor",
    "alineacion_del_consumidor",
    "clausura_del_grafo_de_dependencias",
    "limpieza_de_la_plantilla_del_prompt",
)

CAUSA_PARTICION = "particion"
CAUSA_CAUSAS_VACIAS = "causas-vacias"
CAUSA_DELTA = "delta"
CAUSA_DISJUNCION = "disjuncion"
CAUSA_SECCION = "seccion"
CAUSA_PROXY = "proxy"


def _terna_de(registro: dict) -> Terna:
    return Terna(registro["flujo"], registro["task_id"], registro["ocurrencia"])


def _delta_de_la_comparacion(comparacion: dict) -> set[Terna]:
    """Las ternas donde las dos salidas difieren. Es lo que `desacuerdos[]` tiene que igualar."""
    delta = set()
    for unidad in comparacion.get("unidades", []):
        if set(unidad.get("detector", [])) != set(unidad.get("predicado", [])):
            delta.add(_terna_de(unidad))
    return delta


def revisar_forma_oraculo(oraculo: dict, corpus: dict, comparacion: dict) -> list[str]:
    hallazgos: list[str] = []

    for seccion in ("relacion", "exclusiones", "desacuerdos", "resoluciones", "procedencia",
                    "proxies"):
        if seccion not in oraculo:
            hallazgos.append(f"{CAUSA_SECCION}: falta la sección `{seccion}` de las seis de AC-2")
    if len(oraculo.get("proxies", [])) != 6:
        hallazgos.append(f"{CAUSA_SECCION}: `proxies[]` tiene "
                         f"{len(oraculo.get('proxies', []))} entradas y AC-14 fija seis")

    del_corpus = {Terna(t["flujo"], t["task_id"], t["ocurrencia"])
                  for t in corpus.get("ternas", [])}
    en_relacion = [_terna_de(r) for r in oraculo.get("relacion", [])]
    en_exclusiones = [_terna_de(e) for e in oraculo.get("exclusiones", [])]

    ambas = set(en_relacion) & set(en_exclusiones)
    for terna in sorted(ambas):
        hallazgos.append(f"{CAUSA_PARTICION}: {terna.flujo}/{terna.task_id}#{terna.ocurrencia} "
                         "está en `relacion[]` y en `exclusiones[]`: la partición no es disjunta")

    cubiertas = set(en_relacion) | set(en_exclusiones)
    for terna in sorted(del_corpus - cubiertas):
        hallazgos.append(f"{CAUSA_PARTICION}: {terna.flujo}/{terna.task_id}#{terna.ocurrencia} "
                         "es del corpus y no está en ninguna de las dos listas")
    for terna in sorted(cubiertas - del_corpus):
        hallazgos.append(f"{CAUSA_PARTICION}: {terna.flujo}/{terna.task_id}#{terna.ocurrencia} "
                         "está en el oráculo y no es una terna del corpus")

    for lista, nombre in ((en_relacion, "relacion"), (en_exclusiones, "exclusiones")):
        vistas: dict[Terna, int] = {}
        for terna in lista:
            vistas[terna] = vistas.get(terna, 0) + 1
        for terna, veces in sorted(vistas.items()):
            if veces > 1:
                hallazgos.append(f"{CAUSA_PARTICION}: {terna.flujo}/{terna.task_id}"
                                 f"#{terna.ocurrencia} aparece {veces} veces en `{nombre}[]`: la "
                                 "unión no cubre cada terna exactamente una vez")

    for exclusion in oraculo.get("exclusiones", []):
        if not exclusion.get("causas"):
            terna = _terna_de(exclusion)
            hallazgos.append(f"{CAUSA_CAUSAS_VACIAS}: {terna.flujo}/{terna.task_id}"
                             f"#{terna.ocurrencia} está excluida sin ninguna causa")

    delta = _delta_de_la_comparacion(comparacion)
    en_desacuerdos = {_terna_de(d) for d in oraculo.get("desacuerdos", [])}
    for terna in sorted(delta - en_desacuerdos):
        hallazgos.append(f"{CAUSA_DELTA}: {terna.flujo}/{terna.task_id}#{terna.ocurrencia} difiere "
                         "en la comparación sellada y no tiene entrada en `desacuerdos[]`")
    for terna in sorted(en_desacuerdos - delta):
        hallazgos.append(f"{CAUSA_DELTA}: {terna.flujo}/{terna.task_id}#{terna.ocurrencia} está en "
                         "`desacuerdos[]` y no tiene par en el delta de la comparación sellada")

    en_resoluciones = {_terna_de(r) for r in oraculo.get("resoluciones", [])}
    for terna in sorted(en_resoluciones & en_desacuerdos):
        hallazgos.append(f"{CAUSA_DISJUNCION}: {terna.flujo}/{terna.task_id}#{terna.ocurrencia} "
                         "está a la vez en `resoluciones[]` y en `desacuerdos[]`")

    return hallazgos


def revisar_proxies(oraculo: dict) -> list[str]:
    hallazgos: list[str] = []
    declarados = [p.get("proxy") for p in oraculo.get("proxies", [])]

    for esperado in PROXIES_DE_AC14:
        if esperado not in declarados:
            hallazgos.append(f"{CAUSA_PROXY}: falta el proxy `{esperado}` de los seis de AC-14")
    for declarado in declarados:
        if declarado not in PROXIES_DE_AC14:
            hallazgos.append(f"{CAUSA_PROXY}: `{declarado}` no es ninguno de los seis de AC-14")
    for nombre in sorted({p for p in declarados if declarados.count(p) > 1}):
        hallazgos.append(f"{CAUSA_PROXY}: el proxy `{nombre}` está declarado más de una vez")

    for proxy in oraculo.get("proxies", []):
        if not (proxy.get("acredita") or "").strip():
            hallazgos.append(f"{CAUSA_PROXY}: `{proxy.get('proxy')}` no declara qué acredita")
        if not (proxy.get("no_acredita") or "").strip():
            hallazgos.append(f"{CAUSA_PROXY}: `{proxy.get('proxy')}` no declara su límite —qué "
                             "**no** acredita—, que es lo que AC-14 exige")
    return hallazgos


def _cargar_trio_del_oraculo(base: Path,
                             evidencia: Path) -> tuple[dict, dict, dict, list[str]]:
    oraculo, e1 = _cargar_json(base / "oraculo-cobertura.json")
    corpus, e2 = _cargar_json(base / "corpus-dossier.json")
    comparacion, e3 = _cargar_json(evidencia / "comparacion" / "comparacion.json")
    errores = [e for e in (e1, e2, e3) if e]
    return oraculo or {}, corpus or {}, comparacion or {}, errores


def modo_forma_oraculo(args: argparse.Namespace) -> int:
    del args
    oraculo, corpus, comparacion, errores = _cargar_trio_del_oraculo(DIR_SCRIPTS, DIR_EVIDENCIA)
    for error in errores:
        print(f"FALLA  {error}")
    if errores:
        return 1
    hallazgos = revisar_forma_oraculo(oraculo, corpus, comparacion)
    for h in hallazgos:
        print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} problemas de forma en el oráculo (AC-2)")
        return 1
    print(f"RESULTADO: OK — las seis secciones, la partición exhaustiva de "
          f"{len(corpus['ternas'])} ternas y el delta bidireccional cierran")
    return 0


def modo_proxies(args: argparse.Namespace) -> int:
    del args
    oraculo, error = _cargar_json(RUTA_ORACULO)
    if error:
        print(f"FALLA  {error}")
        return 1
    hallazgos = revisar_proxies(oraculo)
    for h in hallazgos:
        print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} problemas en los seis proxies de AC-14")
        return 1
    print("RESULTADO: OK — los seis proxies de AC-14 declaran qué acreditan y qué no")
    return 0


def _fixture_del_oraculo() -> tuple[dict, dict, dict]:
    """El corpus sintético, con una comparación coherente derivada de él.

    La comparación se **deriva** del propio oráculo sintético para que el positivo sea verde por
    construcción; lo que los mutantes prueban es que romper cada propiedad la pone roja.
    """
    oraculo = json.loads((DIR_FIXTURE_INSUMOS / "oraculo-cobertura.json")
                         .read_text(encoding="utf-8"))
    corpus = json.loads((DIR_FIXTURE_INSUMOS / "corpus-dossier.json").read_text(encoding="utf-8"))
    comparacion = {
        "version": "1",
        "unidades": [{"flujo": r["flujo"], "task_id": r["task_id"], "ocurrencia": r["ocurrencia"],
                      "detector": r["ac"], "predicado": r["ac"]}
                     for r in oraculo["relacion"]],
    }
    return oraculo, corpus, comparacion


def modo_autotest_forma_oraculo(args: argparse.Namespace) -> int:
    del args
    import copy

    def _en_ambas(o: dict, c: dict, k: dict) -> None:
        o["exclusiones"].append({**{x: o["relacion"][0][x]
                                    for x in ("flujo", "task_id", "ocurrencia")},
                                 "causas": ["sin_cobertura"]})

    def _en_ninguna(o: dict, c: dict, k: dict) -> None:
        o["relacion"].clear()
        k["unidades"].clear()

    def _causas_vacias(o: dict, c: dict, k: dict) -> None:
        o["exclusiones"].append({**{x: o["relacion"][0][x]
                                    for x in ("flujo", "task_id", "ocurrencia")},
                                 "causas": []})
        o["relacion"].clear()
        k["unidades"].clear()

    def _desacuerdo_sin_par(o: dict, c: dict, k: dict) -> None:
        r = o["relacion"][0]
        o["desacuerdos"].append({
            "id": "D1", "flujo": r["flujo"], "task_id": r["task_id"],
            "ocurrencia": r["ocurrencia"], "fuente_r2": "cubre",
            "visto_detector": ["AC-2"], "visto_predicado": ["AC-1"],
            "clase_comparativa": "distintos", "clase_adjudicada": "exclusion_deliberada",
            "motivo": "sintético", "evidencia": "salidas/sintetica.json"})

    def _resolucion_no_disjunta(o: dict, c: dict, k: dict) -> None:
        _desacuerdo_sin_par(o, c, k)
        k["unidades"][0]["detector"] = ["AC-2"]  # el delta ahora sí existe: aísla la disjunción
        r = o["relacion"][0]
        o["resoluciones"].append({
            "id": "R1", "flujo": r["flujo"], "task_id": r["task_id"],
            "ocurrencia": r["ocurrencia"], "contrato_al_detectar": "a" * 64,
            "contrato_que_corrigio": "b" * 64, "evidencia_original": "salidas/vieja.json",
            "corrida_posterior": {"completa": True, "flujos_procesados": 1,
                                  "evidencia": "salidas/nueva.json"},
            "resultado": "desaparecio"})

    mutantes = (
        ("terna-en-ambas-listas", _en_ambas, CAUSA_PARTICION),
        ("terna-en-ninguna-lista", _en_ninguna, CAUSA_PARTICION),
        ("causas-vacia", _causas_vacias, CAUSA_CAUSAS_VACIAS),
        ("desacuerdo-sin-par-en-el-delta", _desacuerdo_sin_par, CAUSA_DELTA),
        ("resolucion-no-disjunta", _resolucion_no_disjunta, CAUSA_DISJUNCION),
    )

    fallas = 0
    oraculo, corpus, comparacion = _fixture_del_oraculo()
    hallazgos = revisar_forma_oraculo(oraculo, corpus, comparacion)
    if hallazgos:
        print("FALLA  positivo: el oráculo sintético íntegro da hallazgos:")
        for h in hallazgos:
            print(f"       - {h}")
        fallas += 1
    else:
        print("OK     positivo: el oráculo sintético íntegro cierra su forma")

    for nombre, mutar, causa in mutantes:
        o, c, k = (copy.deepcopy(x) for x in _fixture_del_oraculo())
        mutar(o, c, k)
        hallazgos = revisar_forma_oraculo(o, c, k)
        propios = [h for h in hallazgos if h.startswith(causa)]
        ajenos = [h for h in hallazgos if not h.startswith(causa)]
        if not propios:
            print(f"FALLA  {nombre}: «{causa}» no se puso roja ({hallazgos[:2]})")
            fallas += 1
        elif ajenos:
            print(f"FALLA  {nombre}: además de «{causa}» se pusieron rojas otras ({ajenos[:2]})")
            fallas += 1
        else:
            print(f"OK     {nombre}: rojo por «{causa}» y solo por ella")

    print()
    total = len(mutantes) + 1
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de la forma del oráculo no se "
              "sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de la forma del oráculo pasan")
    return 0


def modo_autotest_proxies(args: argparse.Namespace) -> int:
    del args
    import copy

    def _faltante(o: dict) -> None:
        o["proxies"].pop()

    def _sin_no_acredita(o: dict) -> None:
        o["proxies"][0]["no_acredita"] = ""

    def _uno_de_mas(o: dict) -> None:
        o["proxies"].append({"proxy": "gate_estructural_de_git", "acredita": "algo",
                             "no_acredita": "algo"})

    def _limite_vacio(o: dict) -> None:
        o["proxies"][2]["no_acredita"] = "   "

    mutantes = (
        ("proxy-faltante", _faltante),
        ("proxy-sin-clausula-de-no-acredita", _sin_no_acredita),
        ("proxy-de-mas", _uno_de_mas),
        ("proxy-con-limite-vacio", _limite_vacio),
    )

    base = json.loads((DIR_FIXTURE_INSUMOS / "oraculo-cobertura.json").read_text(encoding="utf-8"))
    fallas = 0
    hallazgos = revisar_proxies(base)
    if hallazgos:
        print("FALLA  positivo: los seis proxies sintéticos dan hallazgos:")
        for h in hallazgos:
            print(f"       - {h}")
        fallas += 1
    else:
        print("OK     positivo: los seis proxies sintéticos pasan")

    for nombre, mutar in mutantes:
        mutado = copy.deepcopy(base)
        mutar(mutado)
        hallazgos = revisar_proxies(mutado)
        if not hallazgos:
            print(f"FALLA  {nombre}: `--proxies` sigue verde sobre el mutante")
            fallas += 1
        else:
            print(f"OK     {nombre}: rojo — {hallazgos[0]}")

    print()
    total = len(mutantes) + 1
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de los proxies no se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de los proxies pasan")
    return 0


# ---------------------------------------------------------------------------------------------
# Modos `--casos` (V11) / `--autotest-casos` (V29) y `--casos-obligatorios` (V12) /
# `--autotest-casos-obligatorios` (V30).
# ---------------------------------------------------------------------------------------------

RUTA_CASOS = DIR_SCRIPTS / "casos-extraccion.json"
REGLAS_DE_R9 = ("R1", "R2", "R3", "R4", "R5", "R7", "R8")
IDENTIDADES_OBLIGATORIAS = (
    "cubre-continuado-en-lineas-indentadas",
    "cubre-con-el-marcador-solo-al-final",
    "ac-sin-vineta-bajo-encabezado-de-vineta",
    "ac-sin-vineta-bajo-encabezado-de-heading",
    "encabezado-de-task-con-titulo",
)

CAUSA_REGLA_SIN_CASO = "regla-sin-caso"
CAUSA_ORIGEN_NO_RESUELVE = "origen-no-resuelve"
CAUSA_BYTES_DISTINTOS = "bytes-distintos"
CAUSA_RANGO_AMBIGUO = "rango-ambiguo"
CAUSA_SINTETICO_INCOMPLETO = "sintetico-incompleto"
CAUSA_MODELO_NO_CUBIERTO = "modelo-no-cubierto"
CAUSA_OBLIGATORIO = "obligatorio"


def revisar_casos(casos: dict, corpus: dict, lector: "Lector | None" = None) -> list[str]:
    hallazgos: list[str] = []
    lector = lector or Lector()

    por_regla: dict[str, set[str]] = {}
    for caso in casos.get("casos", []):
        por_regla.setdefault(caso["regla"], set()).add(caso["signo"])
    for regla in REGLAS_DE_R9:
        for signo in ("positivo", "negativo"):
            if signo not in por_regla.get(regla, set()):
                hallazgos.append(f"{CAUSA_REGLA_SIN_CASO}: {regla} no tiene ningún caso {signo}")

    sellos = {(f["flujo"], a["artefacto"]): a
              for f in corpus.get("flujos", []) for a in f.get("artefactos", [])}

    for caso in casos.get("casos", []):
        if caso["clase"] == "caso_sintetico":
            for campo in ("justificacion", "construccion"):
                if not (caso.get(campo) or "").strip():
                    hallazgos.append(f"{CAUSA_SINTETICO_INCOMPLETO}: el caso {caso['id']} es "
                                     f"sintético y no declara `{campo}`")
            continue

        origen = caso["origen"]
        if origen["artefacto"] != "tasks.md":
            # La contención del rango está modelada solo para `tasks.md`, que es donde R1 define el
            # bloque con id. Un artefacto fuera del modelo **aborta**: pasar en silencio sería
            # declarar verde una comprobación que no se hizo.
            hallazgos.append(f"{CAUSA_MODELO_NO_CUBIERTO}: el caso {caso['id']} copia de "
                             f"{origen['artefacto']}, y la contención del rango solo está modelada "
                             "para tasks.md")
            continue

        sello = sellos.get((origen["flujo"], origen["artefacto"]))
        if sello is None:
            hallazgos.append(f"{CAUSA_ORIGEN_NO_RESUELVE}: el caso {caso['id']} apunta a "
                             f"{origen['flujo']}/{origen['artefacto']}, que el corpus no sella")
            continue
        try:
            lectura = lector.leer_una_vez(RAIZ / sello["ruta"])
        except OSError as exc:
            hallazgos.append(f"{CAUSA_ORIGEN_NO_RESUELVE}: {sello['ruta']} no se pudo leer ({exc})")
            continue
        if lectura.sha256 != sello["sha256"]:
            hallazgos.append(f"{CAUSA_ORIGEN_NO_RESUELVE}: {sello['ruta']} ya no es el artefacto "
                             f"que el corpus selló ({lectura.sha256[:12]}… vs "
                             f"{sello['sha256'][:12]}…)")
            continue

        inicio, fin = origen["rango"]["inicio"], origen["rango"]["fin"]
        if not 0 <= inicio < fin <= lectura.tamano:
            hallazgos.append(f"{CAUSA_RANGO_AMBIGUO}: el caso {caso['id']} declara el rango "
                             f"[{inicio}, {fin}) fuera de los {lectura.tamano} bytes del artefacto")
            continue

        bloques = [b for b in bloques_de_task(lectura.contenido)
                   if b[0] == origen["task_id"] and b[1] == origen["ocurrencia"]]
        if not bloques:
            hallazgos.append(f"{CAUSA_ORIGEN_NO_RESUELVE}: el caso {caso['id']} declara la terna "
                             f"{origen['task_id']}#{origen['ocurrencia']}, que no existe en "
                             f"{sello['ruta']}")
            continue

        if lectura.contenido[inicio:fin] != caso["entrada"].encode("utf-8"):
            hallazgos.append(f"{CAUSA_BYTES_DISTINTOS}: el caso {caso['id']} no coincide byte a "
                             f"byte con el rango [{inicio}, {fin}) de {sello['ruta']}")
            continue

        _, _, bloque_inicio, bloque_fin = bloques[0]
        if not (bloque_inicio <= inicio and fin <= bloque_fin):
            hallazgos.append(f"{CAUSA_RANGO_AMBIGUO}: el caso {caso['id']} copia bytes iguales, "
                             f"pero su rango [{inicio}, {fin}) cae fuera del bloque "
                             f"[{bloque_inicio}, {bloque_fin}) de {origen['task_id']}"
                             f"#{origen['ocurrencia']}: el fragmento no identifica la unidad")
        lector.derivar(lectura, "rango", f"{caso['id']}:{inicio}-{fin}")

    return hallazgos


def revisar_casos_obligatorios(casos: dict) -> list[str]:
    hallazgos: list[str] = []
    por_id = {c["id"]: c for c in casos.get("casos", [])}
    declaradas = {o["identidad"]: o for o in casos.get("obligatorios", [])}

    for identidad in IDENTIDADES_OBLIGATORIAS:
        entrada = declaradas.get(identidad)
        if entrada is None:
            hallazgos.append(f"{CAUSA_OBLIGATORIO}: falta la identidad obligatoria «{identidad}» "
                             "de las cinco de AC-13")
            continue
        caso = por_id.get(entrada["caso_id"])
        if caso is None:
            hallazgos.append(f"{CAUSA_OBLIGATORIO}: «{identidad}» apunta al caso "
                             f"{entrada['caso_id']}, que no está en el manifest")
        elif caso["clase"] != "caso_corpus":
            hallazgos.append(f"{CAUSA_OBLIGATORIO}: «{identidad}» resuelve al caso "
                             f"{caso['id']}, que es {caso['clase']} y AC-13 los exige de corpus")

    for identidad in declaradas:
        if identidad not in IDENTIDADES_OBLIGATORIAS:
            hallazgos.append(f"{CAUSA_OBLIGATORIO}: «{identidad}» no es ninguna de las cinco "
                             "identidades de AC-13")
    return hallazgos


def _cargar_casos_y_corpus() -> tuple[dict, dict, list[str]]:
    casos, e1 = _cargar_json(RUTA_CASOS)
    corpus, e2 = _cargar_json(RUTA_CORPUS)
    return casos or {}, corpus or {}, [e for e in (e1, e2) if e]


def modo_casos(args: argparse.Namespace) -> int:
    del args
    casos, corpus, errores = _cargar_casos_y_corpus()
    for error in errores:
        print(f"FALLA  {error}")
    if errores:
        return 1
    hallazgos = revisar_casos(casos, corpus)
    for h in hallazgos:
        print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} problemas en el manifest de casos")
        return 1
    print(f"RESULTADO: OK — las {len(REGLAS_DE_R9)} reglas con positivo y negativo, y los "
          f"{sum(1 for c in casos['casos'] if c['clase'] == 'caso_corpus')} casos de corpus "
          "resuelven su origen byte a byte")
    return 0


def modo_casos_obligatorios(args: argparse.Namespace) -> int:
    del args
    casos, error = _cargar_json(RUTA_CASOS)
    if error:
        print(f"FALLA  {error}")
        return 1
    hallazgos = revisar_casos_obligatorios(casos)
    for h in hallazgos:
        print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} problemas en los cinco casos obligatorios "
              "de AC-13")
        return 1
    print("RESULTADO: OK — las cinco identidades obligatorias de AC-13 están, todas de corpus")
    return 0


def modo_autotest_casos(args: argparse.Namespace) -> int:
    del args
    import copy

    casos, corpus, errores = _cargar_casos_y_corpus()
    if errores:
        print(f"FALLA  {errores[0]}")
        return 1

    def _primer_corpus(c: dict) -> dict:
        return next(x for x in c["casos"] if x["clase"] == "caso_corpus")

    def _quitar_positivo(regla: str) -> Callable[[dict], None]:
        def mutar(c: dict) -> None:
            c["casos"] = [x for x in c["casos"]
                          if not (x["regla"] == regla and x["signo"] == "positivo")]
        return mutar

    def _quitar_negativo(regla: str) -> Callable[[dict], None]:
        def mutar(c: dict) -> None:
            c["casos"] = [x for x in c["casos"]
                          if not (x["regla"] == regla and x["signo"] == "negativo")]
        return mutar

    def _origen_que_no_resuelve(c: dict) -> None:
        _primer_corpus(c)["origen"]["task_id"] = "T9999"

    def _bytes_distintos(c: dict) -> None:
        caso = _primer_corpus(c)
        caso["entrada"] = caso["entrada"] + " (alterado)"

    def _rango_ambiguo(c: dict) -> None:
        """Mueve el rango a **otra ocurrencia idéntica** del mismo texto, en otro bloque.

        Es el mutante que solo la contención caza: los bytes siguen siendo iguales, así que la
        comprobación byte a byte pasa. Sin el bloque, «el texto aparece en algún lugar» habría
        alcanzado.
        """
        caso = next((x for x in c["casos"] if x.get("ambiguo_en_el_corpus")), None)
        if caso is None:
            raise RuntimeError("ningún caso declara tener un gemelo literal en el corpus")
        gemelo = caso["ambiguo_en_el_corpus"]
        caso["origen"]["rango"] = {"inicio": gemelo["inicio"], "fin": gemelo["fin"]}

    def _sintetico_sin_justificacion(c: dict) -> None:
        caso = next(x for x in c["casos"] if x["clase"] == "caso_sintetico")
        caso["justificacion"] = ""

    def _sintetico_sin_construccion(c: dict) -> None:
        caso = next(x for x in c["casos"] if x["clase"] == "caso_sintetico")
        caso["construccion"] = "  "

    mutantes: list[tuple[str, Callable[[dict], None], str]] = []
    for regla in REGLAS_DE_R9:
        mutantes.append((f"{regla}-sin-positivo", _quitar_positivo(regla), CAUSA_REGLA_SIN_CASO))
        mutantes.append((f"{regla}-sin-negativo", _quitar_negativo(regla), CAUSA_REGLA_SIN_CASO))
    mutantes += [
        ("origen-que-no-resuelve", _origen_que_no_resuelve, CAUSA_ORIGEN_NO_RESUELVE),
        ("bytes-distintos-del-rango", _bytes_distintos, CAUSA_BYTES_DISTINTOS),
        ("rango-ambiguo", _rango_ambiguo, CAUSA_RANGO_AMBIGUO),
        ("sintetico-sin-justificacion", _sintetico_sin_justificacion, CAUSA_SINTETICO_INCOMPLETO),
        ("sintetico-sin-construccion", _sintetico_sin_construccion, CAUSA_SINTETICO_INCOMPLETO),
    ]

    fallas = 0
    hallazgos = revisar_casos(casos, corpus)
    if hallazgos:
        print("FALLA  positivo: el manifest vigente da hallazgos:")
        for h in hallazgos:
            print(f"       - {h}")
        fallas += 1
    else:
        print("OK     positivo: el manifest vigente resuelve todos sus casos")

    for nombre, mutar, causa in mutantes:
        mutado = copy.deepcopy(casos)
        mutar(mutado)
        hallazgos = revisar_casos(mutado, corpus)
        propios = [h for h in hallazgos if h.startswith(causa)]
        ajenos = [h for h in hallazgos if not h.startswith(causa)]
        if not propios:
            print(f"FALLA  {nombre}: «{causa}» no se puso roja ({hallazgos[:2]})")
            fallas += 1
        elif ajenos:
            print(f"FALLA  {nombre}: además de «{causa}» se pusieron rojas otras ({ajenos[:2]})")
            fallas += 1
        else:
            print(f"OK     {nombre}: rojo por «{causa}» y solo por ella")

    print()
    total = len(mutantes) + 1
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de `--casos` no se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de `--casos` pasan")
    return 0


def modo_autotest_casos_obligatorios(args: argparse.Namespace) -> int:
    del args
    import copy

    casos, error = _cargar_json(RUTA_CASOS)
    if error:
        print(f"FALLA  {error}")
        return 1
    corpus, error = _cargar_json(RUTA_CORPUS)
    if error:
        print(f"FALLA  {error}")
        return 1

    fallas = 0
    hallazgos = revisar_casos_obligatorios(casos)
    if hallazgos:
        print("FALLA  positivo: las cinco identidades vigentes dan hallazgos:")
        for h in hallazgos:
            print(f"       - {h}")
        fallas += 1
    else:
        print("OK     positivo: las cinco identidades vigentes resuelven a casos de corpus")

    # **Precondición declarada del fixture:** la cobertura de `--casos` tiene que ser redundante.
    # Sin eso, retirar una identidad obligatoria tumbaría también la fila de `--casos` y el
    # aislamiento causal sería insatisfacible: el mutante no probaría nada sobre esta guarda.
    for identidad in IDENTIDADES_OBLIGATORIAS:
        mutado = copy.deepcopy(casos)
        objetivo = next(o for o in mutado["obligatorios"] if o["identidad"] == identidad)
        mutado["casos"] = [c for c in mutado["casos"] if c["id"] != objetivo["caso_id"]]
        mutado["obligatorios"] = [o for o in mutado["obligatorios"]
                                  if o["identidad"] != identidad]

        hallazgos = revisar_casos_obligatorios(mutado)
        nombrada = [h for h in hallazgos if identidad in h]
        otras = [h for h in hallazgos if identidad not in h]
        residual = revisar_casos(mutado, corpus)

        if not nombrada:
            print(f"FALLA  sin-{identidad}: no se puso roja nombrándola ({hallazgos})")
            fallas += 1
        elif otras:
            print(f"FALLA  sin-{identidad}: puso roja también otra identidad ({otras})")
            fallas += 1
        elif residual:
            print(f"FALLA  sin-{identidad}: la cobertura de `--casos` no era redundante y también "
                  f"cayó ({residual[:2]})")
            fallas += 1
        else:
            print(f"OK     sin-{identidad}: rojo nombrándola, y `--casos` sigue verde")

    print()
    total = len(IDENTIDADES_OBLIGATORIAS) + 1
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de los casos obligatorios no se "
              "sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de los casos obligatorios pasan")
    return 0


# ---------------------------------------------------------------------------------------------
# Modos `--adaptadores` (V32) y `--autotest-adaptadores` (V33). Un adaptador por familia.
# ---------------------------------------------------------------------------------------------
#
# **Resolver el ejecutable por familia no hace portable el transporte.** `claude` no tiene flag de
# sandbox: su read-only se garantiza restringiendo tools, y un `claude -p` headless hereda settings
# del usuario y del proyecto. Dejar `--ignore-user-config` y la cosecha de `item.type` como si
# fueran universales era escribir una rama Claude que falla o no produce evidencia procesable.
#
# **Los dos llevan autotest aunque una corrida real use solo el opuesto al conductor.**

DIR_FIXTURE_ADAPTADORES = DIR_FIXTURES / "adaptadores"

CAUSA_SIN_MENSAJE = "sin-mensaje-final"
CAUSA_STREAM_TRUNCADO = "stream-truncado"
CAUSA_EXIT_NO_CERO = "exit-distinto-de-cero"
CAUSA_FORMATO_INESPERADO = "formato-inesperado"
CAUSA_AISLAMIENTO = "aislamiento-faltante"


def _cosechar_codex(salida: str) -> tuple[str | None, str]:
    """El último `item.type == agent_message` del stream JSONL.

    La clave es `item.type`, **no** `item.item_type`: un extractor que busque la segunda devuelve
    «no hay mensaje» sobre una corrida que entregó bien. Ya pasó, y por eso está escrito acá.
    """
    mensaje = None
    for linea in salida.splitlines():
        if not linea.strip():
            continue
        try:
            evento = json.loads(linea)
        except json.JSONDecodeError:
            return None, f"{CAUSA_STREAM_TRUNCADO}: una línea del JSONL no parsea"
        if not isinstance(evento, dict):
            return None, f"{CAUSA_FORMATO_INESPERADO}: un evento del stream no es un objeto"
        item = evento.get("item")
        if isinstance(item, dict) and item.get("type") == "agent_message":
            mensaje = item.get("text")
    if mensaje is None:
        return None, f"{CAUSA_SIN_MENSAJE}: el stream no trae ningún `agent_message`"
    return mensaje, ""


def _cosechar_claude(salida: str) -> tuple[str | None, str]:
    """El campo `result` del objeto `type: result`. No comparte el protocolo de Codex."""
    try:
        documento = json.loads(salida)
    except json.JSONDecodeError:
        return None, f"{CAUSA_STREAM_TRUNCADO}: la salida no es un JSON completo"
    if not isinstance(documento, dict) or documento.get("type") != "result":
        return None, f"{CAUSA_FORMATO_INESPERADO}: la salida no es un objeto `type: result`"
    if documento.get("is_error") is not False or documento.get("subtype") != "success":
        return None, f"{CAUSA_SIN_MENSAJE}: la corrida terminó sin resultado exitoso"
    mensaje = documento.get("result")
    if not isinstance(mensaje, str) or not mensaje:
        return None, f"{CAUSA_SIN_MENSAJE}: el objeto `result` no trae mensaje"
    return mensaje, ""


class Adaptador(NamedTuple):
    familia: str
    ejecutable: str
    fixture: str
    aislamiento: tuple[str, ...]
    cosechar: Callable[[str], tuple[str | None, str]]
    construir: Callable[["Adaptador", Path, Path], list[str]]

    def comando(self, working_dir: Path, prompt: Path) -> list[str]:
        return self.construir(self, working_dir, prompt)


def _comando_codex(adaptador: Adaptador, working_dir: Path, prompt: Path) -> list[str]:
    # El prompt viaja **por archivo**, nunca inline: el markdown con backticks rompe el quoting.
    return [adaptador.ejecutable, "exec", "-s", "read-only", "--ignore-user-config",
            "--skip-git-repo-check", "--json", "-C", str(working_dir), "-"]


def _comando_claude(adaptador: Adaptador, working_dir: Path, prompt: Path) -> list[str]:
    return [adaptador.ejecutable, "-p", "--allowedTools=Read,Grep,Glob", "--model", "sonnet",
            "--output-format", "json", "--add-dir", str(working_dir)]


ADAPTADORES: tuple[Adaptador, ...] = (
    Adaptador("gpt-codex", "codex", "gpt-codex.stream.jsonl",
              ("-s", "read-only", "--ignore-user-config", "--skip-git-repo-check", "--json"),
              _cosechar_codex, _comando_codex),
    Adaptador("claude", "claude", "claude.stream.json",
              ("--allowedTools=Read,Grep,Glob", "--model", "--output-format"),
              _cosechar_claude, _comando_claude),
)

ADAPTADOR_POR_FAMILIA = {a.familia: a for a in ADAPTADORES}


def revisar_adaptadores() -> list[str]:
    hallazgos: list[str] = []
    for adaptador in ADAPTADORES:
        comando = adaptador.comando(RAIZ, RAIZ / "prompt.txt")
        for argumento in adaptador.aislamiento:
            if argumento not in comando:
                hallazgos.append(f"{CAUSA_AISLAMIENTO}: el adaptador {adaptador.familia} no pasa "
                                 f"`{argumento}` en su invocación")
        fixture = DIR_FIXTURE_ADAPTADORES / adaptador.fixture
        if not fixture.is_file():
            hallazgos.append(f"{CAUSA_FORMATO_INESPERADO}: falta el stream grabado de "
                             f"{adaptador.familia} ({fixture.name})")
            continue
        mensaje, causa = adaptador.cosechar(fixture.read_text(encoding="utf-8"))
        if mensaje is None:
            hallazgos.append(f"{causa} — adaptador {adaptador.familia}")
        elif mensaje.strip() != "OK":
            hallazgos.append(f"{CAUSA_FORMATO_INESPERADO}: el adaptador {adaptador.familia} "
                             f"cosechó {mensaje!r} y el stream grabado responde «OK»")
    return hallazgos


def modo_adaptadores(args: argparse.Namespace) -> int:
    del args
    hallazgos = revisar_adaptadores()
    for h in hallazgos:
        print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} problemas en los dos adaptadores de familia")
        return 1
    for adaptador in ADAPTADORES:
        print(f"OK     {adaptador.familia}: aislamiento completo y cosecha del stream grabado")
    print(f"RESULTADO: OK — los {len(ADAPTADORES)} adaptadores resuelven su invocación y cosechan")
    return 0


def modo_autotest_adaptadores(args: argparse.Namespace) -> int:
    del args

    def _sin_mensaje(familia: str, salida: str) -> str:
        if familia == "gpt-codex":
            return "\n".join(x for x in salida.splitlines() if "agent_message" not in x) + "\n"
        documento = json.loads(salida)
        documento["result"] = ""
        return json.dumps(documento)

    def _truncado(familia: str, salida: str) -> str:
        return salida[:len(salida) // 2]

    def _formato_inesperado(familia: str, salida: str) -> str:
        if familia == "gpt-codex":
            return "[1, 2, 3]\n"
        documento = json.loads(salida)
        documento["type"] = "otra-cosa"
        return json.dumps(documento)

    mutaciones = (
        ("salida-sin-mensaje-final", _sin_mensaje, CAUSA_SIN_MENSAJE),
        ("stream-truncado", _truncado, CAUSA_STREAM_TRUNCADO),
        ("formato-inesperado", _formato_inesperado, CAUSA_FORMATO_INESPERADO),
    )

    fallas = 0
    total = 0
    for adaptador in ADAPTADORES:
        base = (DIR_FIXTURE_ADAPTADORES / adaptador.fixture).read_text(encoding="utf-8")

        total += 1
        mensaje, causa = adaptador.cosechar(base)
        if mensaje is None:
            print(f"FALLA  positivo {adaptador.familia}: el stream grabado no cosecha ({causa})")
            fallas += 1
        else:
            print(f"OK     positivo {adaptador.familia}: cosecha {mensaje.strip()!r}")

        for nombre, mutar, esperada in mutaciones:
            total += 1
            mensaje, causa = adaptador.cosechar(mutar(adaptador.familia, base))
            if mensaje is not None:
                print(f"FALLA  {adaptador.familia}/{nombre}: cosechó igual {mensaje!r}")
                fallas += 1
            elif not causa.startswith(esperada):
                print(f"FALLA  {adaptador.familia}/{nombre}: falló por otra causa — se esperaba "
                      f"«{esperada}» y llegó «{causa}»")
                fallas += 1
            else:
                print(f"OK     {adaptador.familia}/{nombre}: rojo por su propia causa")

        # Un exit distinto de cero no se cosecha: no importa qué haya en stdout.
        total += 1
        if _corrida_aceptada(adaptador, base, codigo=1)[0] is not None:
            print(f"FALLA  {adaptador.familia}/exit-distinto-de-cero: aceptó una corrida fallida")
            fallas += 1
        else:
            print(f"OK     {adaptador.familia}/exit-distinto-de-cero: rojo por su propia causa")

        # Y un argumento de aislamiento que falta invalida la invocación entera.
        total += 1
        comando = [x for x in adaptador.comando(RAIZ, RAIZ / "p.txt")
                   if x != adaptador.aislamiento[0]]
        faltantes = [a for a in adaptador.aislamiento if a not in comando]
        if not faltantes:
            print(f"FALLA  {adaptador.familia}/aislamiento-faltante: quitar "
                  f"`{adaptador.aislamiento[0]}` no se detecta")
            fallas += 1
        else:
            print(f"OK     {adaptador.familia}/aislamiento-faltante: se detecta la ausencia de "
                  f"`{faltantes[0]}`")

    print()
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de los adaptadores no se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de los adaptadores pasan")
    return 0


def _corrida_aceptada(adaptador: Adaptador, salida: str,
                      codigo: int) -> tuple[str | None, str]:
    """La cosecha con su criterio de éxito: un exit distinto de cero **no** se cosecha."""
    if codigo != 0:
        return None, f"{CAUSA_EXIT_NO_CERO}: {adaptador.ejecutable} salió con código {codigo}"
    return adaptador.cosechar(salida)


# ---------------------------------------------------------------------------------------------
# Modos `--prompt` (V26) y `--autotest-prompt` (V27). La plantilla cerrada y sus derivados.
# ---------------------------------------------------------------------------------------------
#
# **Sellar no alcanza, y esto corrige un razonamiento que ya estaba escrito.** El sello prueba
# integridad, no contenido: un prompt que incluya la gramática queda perfectamente sellado y su
# hash no dice nada. Lo que se automatiza acá es lo comprobable —identidad exacta de la plantilla,
# variables permitidas y ausencia de adjuntos y rutas prohibidos—. Que el texto de la plantilla no
# enseñe la gramática con otras palabras **no es automatizable**: es el sexto proxy, y su
# observación es del gate humano.

RUTA_PLANTILLA = DIR_SCRIPTS / "oraculo-prompt.plantilla.md"
DIR_PROMPTS = DIR_EVIDENCIA / "prompts"

VARIABLES_PERMITIDAS = ("FLUJO", "RUTA_SPEC", "RUTA_PLAN", "RUTA_TASKS")
PATRON_VARIABLE = re.compile(r"\{\{([A-Z_]+)\}\}")

# Lo que un prompt **no** puede contener. Cada entrada nombra un insumo cuya presencia destruye lo
# único que se está midiendo: el detector tiene que leer el corpus **sin** el contrato.
ADJUNTOS_PROHIBIDOS = (
    ("contrato-extraccion", "el contrato de extracción, por ruta o por nombre"),
    ("cubre:", "el marcador de la primera fuente de R2"),
    ("**ac:**", "el marcador de las otras dos fuentes de R2"),
    ("gramatica", "nombrar la gramática de las reglas"),
    ("declara", "la distinción declara-vs-menciona explicada como regla"),
    ("corpus-elegibles", "una salida del predicado de elegibilidad"),
    ("corpus-dossier", "el manifest de corpus"),
    ("oraculo-cobertura", "el oráculo que este prompt existe para producir"),
    ("comparacion", "una comparación previa"),
)

CAUSA_PLANTILLA_ALTERADA = "plantilla-alterada"
CAUSA_VARIABLE_NO_PERMITIDA = "variable-no-permitida"
CAUSA_ADJUNTO_PROHIBIDO = "adjunto-prohibido"
CAUSA_RUTA_PROHIBIDA = "ruta-prohibida"

# Una ruta citada **en línea**: entre backticks simples y sin cruzar salto de línea. Sin la
# restricción de línea el patrón se come el bloque de respuesta entero y reporta como «ruta» un
# JSON de doce líneas — un falso rojo que además tapa los verdaderos.
PATRON_RUTA = re.compile(r"`([^`\n]*/[^`\n]*)`")


def valores_del_flujo(flujo: str) -> dict[str, str]:
    return {
        "FLUJO": flujo,
        "RUTA_SPEC": str(ruta_de_artefacto(flujo, "spec.md").relative_to(RAIZ)),
        "RUTA_PLAN": str(ruta_de_artefacto(flujo, "plan.md").relative_to(RAIZ)),
        "RUTA_TASKS": str(ruta_de_artefacto(flujo, "tasks.md").relative_to(RAIZ)),
    }


def derivar_prompt(plantilla: str, flujo: str) -> str:
    texto = plantilla
    for nombre, valor in valores_del_flujo(flujo).items():
        texto = texto.replace("{{" + nombre + "}}", valor)
    return texto


def revisar_plantilla(plantilla: str) -> list[str]:
    hallazgos = []
    for variable in sorted(set(PATRON_VARIABLE.findall(plantilla))):
        if variable not in VARIABLES_PERMITIDAS:
            hallazgos.append(f"{CAUSA_VARIABLE_NO_PERMITIDA}: la plantilla usa `{{{{{variable}}}}}`, "
                             f"que no está entre {list(VARIABLES_PERMITIDAS)}")
    return hallazgos


def revisar_prompt(texto: str, flujo: str, plantilla: str, etiqueta: str) -> list[str]:
    hallazgos: list[str] = []

    if texto != derivar_prompt(plantilla, flujo):
        hallazgos.append(f"{CAUSA_PLANTILLA_ALTERADA}: {etiqueta} no es la plantilla vigente con "
                         "sus variables sustituidas")

    if PATRON_VARIABLE.search(texto):
        hallazgos.append(f"{CAUSA_VARIABLE_NO_PERMITIDA}: {etiqueta} dejó variables sin sustituir")

    plegado = plegar(texto)
    for marcador, por_que in ADJUNTOS_PROHIBIDOS:
        if plegar(marcador) in plegado:
            hallazgos.append(f"{CAUSA_ADJUNTO_PROHIBIDO}: {etiqueta} contiene «{marcador}» — "
                             f"{por_que}")

    permitidas = set(valores_del_flujo(flujo).values())
    for ruta in PATRON_RUTA.findall(texto):
        if ruta not in permitidas:
            hallazgos.append(f"{CAUSA_RUTA_PROHIBIDA}: {etiqueta} cita `{ruta}`, que no es ninguno "
                             "de los tres artefactos del flujo")
    return hallazgos


def _flujos_elegibles_congelados() -> list[str]:
    snapshot, error = _cargar_json(RUTA_ELEGIBLES)
    return [] if error else sorted(snapshot["elegibles"])


def modo_prompt(args: argparse.Namespace) -> int:
    del args
    if not RUTA_PLANTILLA.is_file():
        print(f"FALLA  no existe la plantilla versionada: {RUTA_PLANTILLA}")
        return 1
    plantilla = RUTA_PLANTILLA.read_text(encoding="utf-8")

    hallazgos = revisar_plantilla(plantilla)
    flujos = _flujos_elegibles_congelados()
    if not flujos:
        print("FALLA  no hay universo elegible congelado contra el cual comprobar los prompts")
        return 1

    for flujo in flujos:
        ruta = DIR_PROMPTS / f"{flujo.replace('/', '__')}.md"
        if not ruta.is_file():
            hallazgos.append(f"{CAUSA_PLANTILLA_ALTERADA}: falta el prompt de {flujo}")
            continue
        hallazgos.extend(revisar_prompt(ruta.read_text(encoding="utf-8"), flujo, plantilla,
                                        ruta.name))

    sobrantes = {p.name for p in DIR_PROMPTS.glob("*.md")} if DIR_PROMPTS.is_dir() else set()
    sobrantes -= {f"{f.replace('/', '__')}.md" for f in flujos}
    for nombre in sorted(sobrantes):
        hallazgos.append(f"{CAUSA_PLANTILLA_ALTERADA}: {nombre} no corresponde a ningún flujo "
                         "elegible")

    for h in hallazgos:
        print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} problemas estructurales en los prompts; no "
              "lanzar ninguna corrida")
        return 1
    print(f"RESULTADO: OK — los {len(flujos)} prompts son la plantilla vigente con sus variables "
          "permitidas, sin adjuntos ni rutas prohibidos")
    return 0


def modo_autotest_prompt(args: argparse.Namespace) -> int:
    del args
    plantilla = RUTA_PLANTILLA.read_text(encoding="utf-8")
    flujo = "archived/flujo-de-prueba"
    base = derivar_prompt(plantilla, flujo)

    mutantes = (
        ("plantilla-alterada",
         lambda t: t.replace("Sos un lector, no un revisor", "Sos un revisor"),
         CAUSA_PLANTILLA_ALTERADA),
        ("adjunto-prohibido",
         lambda t: t + "\n\nAnexo: el contrato-extraccion.md, para que sepas qué formas cuentan.\n",
         CAUSA_ADJUNTO_PROHIBIDO),
        ("ruta-prohibida",
         lambda t: t.replace("`{}`".format(valores_del_flujo(flujo)["RUTA_SPEC"]),
                             "`scripts/corpus-dossier.json`"),
         CAUSA_RUTA_PROHIBIDA),
    )

    fallas = 0
    hallazgos = revisar_prompt(base, flujo, plantilla, "prompt-de-prueba")
    hallazgos += revisar_plantilla(plantilla)
    if hallazgos:
        print("FALLA  positivo: el prompt derivado de la plantilla vigente da hallazgos:")
        for h in hallazgos:
            print(f"       - {h}")
        fallas += 1
    else:
        print("OK     positivo: el prompt derivado de la plantilla vigente pasa")

    for nombre, mutar, causa in mutantes:
        hallazgos = revisar_prompt(mutar(base), flujo, plantilla, "prompt-de-prueba")
        propios = [h for h in hallazgos if h.startswith(causa)]
        if not propios:
            print(f"FALLA  {nombre}: «{causa}» no se puso roja ({hallazgos})")
            fallas += 1
        else:
            print(f"OK     {nombre}: rojo por «{causa}»")

    # La variable fuera de la lista se muta sobre la **plantilla**, que es donde vive.
    hallazgos = revisar_plantilla(plantilla.replace("{{FLUJO}}", "{{CONTRATO}}"))
    if not any(h.startswith(CAUSA_VARIABLE_NO_PERMITIDA) for h in hallazgos):
        print(f"FALLA  variable-fuera-de-la-lista: «{CAUSA_VARIABLE_NO_PERMITIDA}» no se puso roja")
        fallas += 1
    else:
        print("OK     variable-fuera-de-la-lista: rojo por «variable-no-permitida»")

    print()
    total = len(mutantes) + 2
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de `--prompt` no se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de `--prompt` pasan")
    return 0


# ---------------------------------------------------------------------------------------------
# Modos `--cobertura-deteccion` (V15) y `--autotest-cobertura-deteccion` (V16).
# ---------------------------------------------------------------------------------------------
#
# **Es el modo de fallo por vacuidad, y ya tuvo su ensayo:** el sondeo procesó 39 de 347 tasks.
# Adjudicar solo los desacuerdos *encontrados* deja que omitir tasks de la corrida elimine también
# sus desacuerdos, y todas las auditorías quedan en verde sobre una fracción del corpus.
#
# Las tres poblaciones se comparan como **multiconjuntos**, no como conjuntos: comparar conjuntos
# borra la multiplicidad que AC-7 manda nombrar, y un duplicado de un lado se compensa con una
# omisión del otro.

RUTA_ADJUDICACIONES = DIR_COMPARACION / "adjudicaciones.json"
RUTA_RECONCILIACIONES = DIR_COMPARACION / "reconciliaciones.json"

CAUSA_POBLACION = "poblacion"
CAUSA_SIN_REGISTRO = "sin-registro-de-contenido"
CAUSA_RESULTADO_INVENTADO = "resultado-inventado"
CAUSA_DUPLICADO = "duplicado"


def registro_canonico(unidad: dict) -> str:
    """La proyección del registro por terna, sin su propio hash. Es lo que `registro_sha256` sella."""
    proyeccion = json.dumps(
        {k: unidad[k] for k in ("flujo", "task_id", "ocurrencia", "detector", "predicado",
                                "identidad_contenido", "salida_cruda")},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return _sha256_de(proyeccion.encode("utf-8"))


def _multiconjunto(ternas) -> dict[Terna, int]:
    conteo: dict[Terna, int] = {}
    for terna in ternas:
        conteo[terna] = conteo.get(terna, 0) + 1
    return conteo


def _comparar_multiconjuntos(izquierda: str, a: dict[Terna, int],
                             derecha: str, b: dict[Terna, int],
                             causa_de_cardinalidad: str = CAUSA_POBLACION) -> list[str]:
    """La multiplicidad importa: un duplicado de un lado se compensa con una omisión del otro si
    solo se comparan conjuntos, y AC-7 manda nombrar los duplicados."""
    hallazgos = []
    for terna in sorted(set(a) | set(b)):
        na, nb = a.get(terna, 0), b.get(terna, 0)
        if na == nb:
            continue
        etiqueta = f"{terna.flujo}/{terna.task_id}#{terna.ocurrencia}"
        causa = CAUSA_DUPLICADO if na > 1 or nb > 1 else causa_de_cardinalidad
        hallazgos.append(f"{causa}: {etiqueta} aparece {na} vez/veces en {izquierda} y {nb} en "
                         f"{derecha}")
    return hallazgos


def _ternas_de_la_salida_cruda(contenido: str, flujo: str) -> tuple[list[Terna], str | None]:
    """Lo que el detector dice haber procesado, leído de su salida cruda."""
    adaptador = ADAPTADOR_POR_FAMILIA["gpt-codex"]
    mensaje, causa = adaptador.cosechar(contenido)
    if mensaje is None:
        return [], causa
    texto = mensaje.strip()
    if texto.startswith("```"):
        texto = texto.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        documento = json.loads(texto)
    except json.JSONDecodeError as exc:
        return [], f"{CAUSA_FORMATO_INESPERADO}: la respuesta no es JSON ({exc})"
    vistos: dict[str, int] = {}
    salida = []
    for tarea in documento.get("tareas", []):
        task_id = str(tarea.get("tarea", "")).strip()
        vistos[task_id] = vistos.get(task_id, 0) + 1
        salida.append(Terna(flujo, task_id, vistos[task_id]))
    return salida, None


def revisar_cobertura_deteccion(corpus: dict, comparacion: dict, oraculo: dict,
                                evidencia: Path) -> list[str]:
    hallazgos: list[str] = []

    del_corpus = _multiconjunto(Terna(t["flujo"], t["task_id"], t["ocurrencia"])
                                for t in corpus.get("ternas", []))

    procesadas: list[Terna] = []
    sellado = {(f["flujo"], a["artefacto"]): a["identidad_lectura"]
               for f in corpus.get("flujos", []) for a in f.get("artefactos", [])}
    por_flujo: dict[str, list[Terna]] = {}

    for unidad in comparacion.get("unidades", []):
        terna = _terna_de(unidad)
        procesadas.append(terna)
        por_flujo.setdefault(terna.flujo, []).append(terna)
        etiqueta = f"{terna.flujo}/{terna.task_id}#{terna.ocurrencia}"

        esperada = sellado.get((terna.flujo, "tasks.md"))
        if not unidad.get("identidad_contenido"):
            hallazgos.append(f"{CAUSA_SIN_REGISTRO}: {etiqueta} se cuenta como procesada sin "
                             "registrar la identidad del contenido leído")
        elif unidad["identidad_contenido"] != esperada:
            hallazgos.append(f"{CAUSA_SIN_REGISTRO}: {etiqueta} dice haber leído "
                             f"{unidad['identidad_contenido']} y el corpus selló {esperada}")
        if not unidad.get("salida_cruda"):
            hallazgos.append(f"{CAUSA_SIN_REGISTRO}: {etiqueta} no referencia ninguna salida cruda")
        elif unidad.get("registro_sha256") != registro_canonico(unidad):
            hallazgos.append(f"{CAUSA_SIN_REGISTRO}: {etiqueta} lleva un `registro_sha256` que no "
                             "es el de su propio registro")

    for flujo, ternas in sorted(por_flujo.items()):
        referencias = {u["salida_cruda"] for u in comparacion["unidades"]
                       if u["flujo"] == flujo and u.get("salida_cruda")}
        for referencia in sorted(referencias):
            ruta = evidencia / referencia
            if not ruta.is_file():
                hallazgos.append(f"{CAUSA_RESULTADO_INVENTADO}: {flujo} referencia {referencia}, "
                                 "que no está en la evidencia")
                continue
            crudas, causa = _ternas_de_la_salida_cruda(ruta.read_text(encoding="utf-8"), flujo)
            if causa:
                hallazgos.append(f"{CAUSA_RESULTADO_INVENTADO}: {referencia} — {causa}")
                continue
            # Una terna «procesada» sin par en la salida cruda es un **resultado inventado**, no
            # una diferencia de población: la población la fija el corpus, y esta comparación es
            # contra lo que el detector realmente entregó.
            hallazgos.extend(_comparar_multiconjuntos(
                "la salida cruda", _multiconjunto(crudas),
                "lo procesado", _multiconjunto(ternas), CAUSA_RESULTADO_INVENTADO))

    en_oraculo = _multiconjunto(
        [_terna_de(r) for r in oraculo.get("relacion", [])]
        + [_terna_de(e) for e in oraculo.get("exclusiones", [])])

    hallazgos.extend(_comparar_multiconjuntos("el corpus", del_corpus,
                                              "lo procesado", _multiconjunto(procesadas)))
    hallazgos.extend(_comparar_multiconjuntos("el corpus", del_corpus,
                                              "el oráculo", en_oraculo))
    return hallazgos


def modo_cobertura_deteccion(args: argparse.Namespace) -> int:
    del args
    oraculo, corpus, comparacion, errores = _cargar_trio_del_oraculo(DIR_SCRIPTS, DIR_EVIDENCIA)
    for error in errores:
        print(f"FALLA  {error}")
    if errores:
        return 1
    hallazgos = revisar_cobertura_deteccion(corpus, comparacion, oraculo, DIR_EVIDENCIA)
    for h in hallazgos:
        print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} discrepancias entre las tres poblaciones (AC-7)")
        return 1
    print(f"RESULTADO: OK — las tres poblaciones son el mismo multiconjunto de "
          f"{len(corpus['ternas'])} ternas, y cada procesada liga su salida cruda")
    return 0


def modo_autotest_cobertura_deteccion(args: argparse.Namespace) -> int:
    del args
    import copy

    oraculo, corpus, comparacion, errores = _cargar_trio_del_oraculo(DIR_SCRIPTS, DIR_EVIDENCIA)
    if errores:
        print(f"FALLA  {errores[0]}")
        return 1

    def _flujo_omitido(o, c, k):
        victima = k["unidades"][0]["flujo"]
        k["unidades"] = [u for u in k["unidades"] if u["flujo"] != victima]
        o["relacion"] = [r for r in o["relacion"] if r["flujo"] != victima]
        o["exclusiones"] = [e for e in o["exclusiones"] if e["flujo"] != victima]

    def _sin_registro(o, c, k):
        k["unidades"][0]["identidad_contenido"] = ""

    def _resultado_inventado(o, c, k):
        gemelo = copy.deepcopy(k["unidades"][0])
        gemelo["task_id"] = "T31337"
        gemelo["registro_sha256"] = registro_canonico(gemelo)
        k["unidades"].append(gemelo)
        o["exclusiones"].append({"flujo": gemelo["flujo"], "task_id": gemelo["task_id"],
                                 "ocurrencia": gemelo["ocurrencia"],
                                 "causas": ["sin_cobertura"]})
        c["ternas"].append({"flujo": gemelo["flujo"], "task_id": gemelo["task_id"],
                            "ocurrencia": gemelo["ocurrencia"]})

    def _duplicado_en_lo_procesado(o, c, k):
        k["unidades"].append(copy.deepcopy(k["unidades"][0]))

    def _duplicado_en_el_corpus(o, c, k):
        c["ternas"].append(copy.deepcopy(c["ternas"][0]))

    def _duplicado_en_el_oraculo(o, c, k):
        lista = o["relacion"] if o["relacion"] else o["exclusiones"]
        lista.append(copy.deepcopy(lista[0]))

    mutantes = (
        ("flujo-omitido-de-la-deteccion", _flujo_omitido, CAUSA_POBLACION),
        ("terna-procesada-sin-registro-de-contenido", _sin_registro, CAUSA_SIN_REGISTRO),
        ("resultado-inventado", _resultado_inventado, CAUSA_RESULTADO_INVENTADO),
        ("duplicado-en-lo-procesado", _duplicado_en_lo_procesado, CAUSA_DUPLICADO),
        ("duplicado-en-el-corpus", _duplicado_en_el_corpus, CAUSA_DUPLICADO),
        ("duplicado-en-el-oraculo", _duplicado_en_el_oraculo, CAUSA_DUPLICADO),
    )

    fallas = 0
    hallazgos = revisar_cobertura_deteccion(corpus, comparacion, oraculo, DIR_EVIDENCIA)
    if hallazgos:
        print("FALLA  positivo: las tres poblaciones vigentes no cierran:")
        for h in hallazgos[:5]:
            print(f"       - {h}")
        fallas += 1
    else:
        print("OK     positivo: las tres poblaciones vigentes son el mismo multiconjunto")

    for nombre, mutar, causa in mutantes:
        o, c, k = copy.deepcopy(oraculo), copy.deepcopy(corpus), copy.deepcopy(comparacion)
        mutar(o, c, k)
        hallazgos = revisar_cobertura_deteccion(c, k, o, DIR_EVIDENCIA)
        propios = [h for h in hallazgos if h.startswith(causa)]
        if not propios:
            print(f"FALLA  {nombre}: «{causa}» no se puso roja ({hallazgos[:2]})")
            fallas += 1
        else:
            print(f"OK     {nombre}: rojo por «{causa}» — {propios[0][:110]}")

    print()
    total = len(mutantes) + 1
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de la cobertura de detección no "
              "se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de la cobertura de detección pasan")
    return 0


# ---------------------------------------------------------------------------------------------
# Modos `--adjudicacion` (V17) / `--autotest-adjudicacion` (V18) y `--exclusiones` (V19) /
# `--autotest-exclusiones` (V31).
# ---------------------------------------------------------------------------------------------

CLASES_ADJUDICADAS = ("punto_ciego", "exclusion_deliberada")
CLASES_COMPARATIVAS = ("ve_mas", "ve_menos", "distintos")
RESULTADOS_DE_RECONCILIACION = ("desaparecio", "reclasificado_exclusion_deliberada")

# El enum cerrado de R5 / AC-5 de `dossier-arnes`. Vive replicado acá porque el consumidor todavía
# no existe como código: la **igualdad ejecutable** contra su clasificador la exige ese flujo (D6).
CAUSAS_DE_R5 = (
    "sin_cobertura", "cobertura_en_conflicto", "fila_duplicada", "fila_inexistente",
    "duplicado_normativo", "consume_no_tipado", "task_consumida_inexistente", "sin_produce",
    "bloque_global_inexistente", "bloque_global_duplicado", "bloque_global_ambiguo",
    "ac_inexistente", "enfoque_ausente", "rango_invertido", "extremo_inexistente", "rango_mixto",
)

CAUSA_CLASE = "clase"
CAUSA_MOTIVO = "motivo"
CAUSA_PUNTO_CIEGO_VIGENTE = "punto-ciego-vigente"
CAUSA_HISTORIAL = "historial"
CAUSA_CAUSA_FUERA_DEL_ENUM = "causa-fuera-del-enum"
CAUSA_CAUSAS_REPETIDAS = "causas-repetidas"
CAUSA_COBERTURA_EXCLUSIONES = "cobertura-exclusiones"


def revisar_adjudicacion(oraculo: dict, adjudicaciones: dict) -> list[str]:
    hallazgos: list[str] = []

    for desacuerdo in oraculo.get("desacuerdos", []):
        etiqueta = desacuerdo.get("id", "?")
        if desacuerdo.get("clase_adjudicada") not in CLASES_ADJUDICADAS:
            hallazgos.append(f"{CAUSA_CLASE}: el desacuerdo {etiqueta} lleva la clase "
                             f"{desacuerdo.get('clase_adjudicada')!r}, fuera del enum de dos")
        if desacuerdo.get("clase_comparativa") not in CLASES_COMPARATIVAS:
            hallazgos.append(f"{CAUSA_CLASE}: el desacuerdo {etiqueta} lleva la clase comparativa "
                             f"{desacuerdo.get('clase_comparativa')!r}, fuera del enum de tres")
        if not (desacuerdo.get("motivo") or "").strip():
            hallazgos.append(f"{CAUSA_MOTIVO}: el desacuerdo {etiqueta} no tiene motivo escrito")
        if desacuerdo.get("clase_adjudicada") == "punto_ciego":
            hallazgos.append(f"{CAUSA_PUNTO_CIEGO_VIGENTE}: el desacuerdo {etiqueta} sigue "
                             "clasificado como `punto_ciego` y AC-9 exige cero al congelar")

    # El historial se deriva de **todas** las adjudicaciones selladas, no de las vigentes: si el
    # punto ciego simplemente desaparece tras la nueva corrida, no queda registro desde el cual
    # verificar el enlace al contrato, el hash anterior ni la transición.
    historico = {(a["flujo"], a["task_id"], a["ocurrencia"])
                 for a in adjudicaciones.get("adjudicaciones", [])
                 if a.get("clase_adjudicada") == "punto_ciego"}
    resueltos = {(r["flujo"], r["task_id"], r["ocurrencia"])
                 for r in oraculo.get("resoluciones", [])}
    for clave in sorted(historico - resueltos):
        hallazgos.append(f"{CAUSA_HISTORIAL}: {clave[0]}/{clave[1]}#{clave[2]} fue adjudicado "
                         "`punto_ciego` alguna vez y no está en `resoluciones[]`")
    for clave in sorted(resueltos - historico):
        hallazgos.append(f"{CAUSA_HISTORIAL}: {clave[0]}/{clave[1]}#{clave[2]} está en "
                         "`resoluciones[]` y ninguna comparación sellada lo adjudicó `punto_ciego`")

    for resolucion in oraculo.get("resoluciones", []):
        etiqueta = resolucion.get("id", "?")
        if resolucion.get("contrato_al_detectar") == resolucion.get("contrato_que_corrigio"):
            hallazgos.append(f"{CAUSA_HISTORIAL}: la resolución {etiqueta} lleva un solo hash de "
                             "contrato: el que regía al detectarlo y el que lo corrigió son el mismo")
        if not (resolucion.get("evidencia_original") or "").strip():
            hallazgos.append(f"{CAUSA_HISTORIAL}: la resolución {etiqueta} no cita su evidencia "
                             "original")
        posterior = resolucion.get("corrida_posterior") or {}
        if posterior.get("completa") is not True:
            hallazgos.append(f"{CAUSA_HISTORIAL}: la resolución {etiqueta} se apoya en una corrida "
                             "posterior **parcial**: el punto ciego pudo desaparecer porque su "
                             "flujo no se procesó")
        if resolucion.get("resultado") not in RESULTADOS_DE_RECONCILIACION:
            hallazgos.append(f"{CAUSA_HISTORIAL}: la resolución {etiqueta} lleva el resultado "
                             f"{resolucion.get('resultado')!r}, fuera del enum")
    return hallazgos


def revisar_exclusiones(oraculo: dict, comparacion: dict) -> list[str]:
    hallazgos: list[str] = []

    for exclusion in oraculo.get("exclusiones", []):
        etiqueta = f"{exclusion['flujo']}/{exclusion['task_id']}#{exclusion['ocurrencia']}"
        causas = exclusion.get("causas") or []
        if not causas:
            hallazgos.append(f"{CAUSA_CAUSA_FUERA_DEL_ENUM}: {etiqueta} no declara ninguna causa")
        for causa in causas:
            if causa not in CAUSAS_DE_R5:
                hallazgos.append(f"{CAUSA_CAUSA_FUERA_DEL_ENUM}: {etiqueta} declara «{causa}», que "
                                 "no está en el enum cerrado de R5")
        if len(set(causas)) != len(causas):
            hallazgos.append(f"{CAUSA_CAUSAS_REPETIDAS}: {etiqueta} repite una causa")

    # Cobertura: toda terna sin cobertura adjudicada tiene su entrada, y ninguna sobra. Es lo que
    # se puede verificar sin clasificador; la **igualdad** de `causas[]` la exige `dossier-arnes`.
    sin_cobertura = {_terna_de(u) for u in comparacion.get("unidades", [])
                     if not u.get("adjudicado")}
    declaradas = {_terna_de(e) for e in oraculo.get("exclusiones", [])}
    for terna in sorted(sin_cobertura - declaradas):
        hallazgos.append(f"{CAUSA_COBERTURA_EXCLUSIONES}: {terna.flujo}/{terna.task_id}"
                         f"#{terna.ocurrencia} quedó sin cobertura adjudicada y no tiene entrada "
                         "en `exclusiones[]`")
    for terna in sorted(declaradas - sin_cobertura):
        hallazgos.append(f"{CAUSA_COBERTURA_EXCLUSIONES}: {terna.flujo}/{terna.task_id}"
                         f"#{terna.ocurrencia} está en `exclusiones[]` y su adjudicación le dio "
                         "cobertura")
    return hallazgos


def modo_adjudicacion(args: argparse.Namespace) -> int:
    del args
    oraculo, e1 = _cargar_json(RUTA_ORACULO)
    adjudicaciones, e2 = _cargar_json(RUTA_ADJUDICACIONES)
    for error in (e1, e2):
        if error:
            print(f"FALLA  {error}")
    if e1 or e2:
        return 1
    hallazgos = revisar_adjudicacion(oraculo, adjudicaciones)
    for h in hallazgos:
        print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} problemas en la adjudicación (AC-8, AC-9)")
        return 1
    print(f"RESULTADO: OK — {len(oraculo['desacuerdos'])} desacuerdos con clase y motivo, cero "
          f"`punto_ciego` vigente, y {len(oraculo['resoluciones'])} resoluciones que cierran el "
          "histórico")
    return 0


def modo_exclusiones(args: argparse.Namespace) -> int:
    del args
    oraculo, e1 = _cargar_json(RUTA_ORACULO)
    comparacion, e2 = _cargar_json(RUTA_COMPARACION)
    for error in (e1, e2):
        if error:
            print(f"FALLA  {error}")
    if e1 or e2:
        return 1
    hallazgos = revisar_exclusiones(oraculo, comparacion)
    for h in hallazgos:
        print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} problemas en las exclusiones (AC-10)")
        return 1
    print(f"RESULTADO: OK — {len(oraculo['exclusiones'])} exclusiones con causas del enum de R5, "
          "sin repetidos, y su cobertura cierra en las dos direcciones")
    return 0


def modo_autotest_adjudicacion(args: argparse.Namespace) -> int:
    del args
    import copy

    oraculo, e1 = _cargar_json(RUTA_ORACULO)
    adjudicaciones, e2 = _cargar_json(RUTA_ADJUDICACIONES)
    if e1 or e2:
        print(f"FALLA  {e1 or e2}")
        return 1

    def _desacuerdo_base(o: dict) -> dict:
        if o["desacuerdos"]:
            return o["desacuerdos"][0]
        referencia = (o["relacion"] or o["exclusiones"])[0]
        nuevo = {"id": "D9000", "flujo": referencia["flujo"], "task_id": referencia["task_id"],
                 "ocurrencia": referencia["ocurrencia"], "fuente_r2": "cubre",
                 "visto_detector": ["AC-1"], "visto_predicado": [],
                 "clase_comparativa": "ve_mas", "clase_adjudicada": "exclusion_deliberada",
                 "motivo": "sintético del autotest", "evidencia": "salidas/sintetica.jsonl"}
        o["desacuerdos"].append(nuevo)
        return nuevo

    def _clase_fuera_del_enum(o, a):
        _desacuerdo_base(o)["clase_adjudicada"] = "otra_cosa"

    def _motivo_vacio(o, a):
        _desacuerdo_base(o)["motivo"] = "   "

    def _punto_ciego_vigente(o, a):
        desacuerdo = _desacuerdo_base(o)
        desacuerdo["clase_adjudicada"] = "punto_ciego"
        # También entra al histórico y a `resoluciones[]`, para que el único rojo sea el de AC-9.
        a["adjudicaciones"].append({k: desacuerdo[k] for k in
                                    ("flujo", "task_id", "ocurrencia", "clase_adjudicada")}
                                   | {"id": desacuerdo["id"], "contrato": SHA_CONTRATO,
                                      "clase_comparativa": desacuerdo["clase_comparativa"],
                                      "motivo": desacuerdo["motivo"],
                                      "evidencia": desacuerdo["evidencia"], "vigente": True})
        o["resoluciones"].append(_resolucion_sintetica(desacuerdo))

    def _historico_con_un_solo_hash(o, a):
        desacuerdo = _desacuerdo_base(o)
        _registrar_punto_ciego_historico(o, a, desacuerdo)
        o["resoluciones"][-1]["contrato_que_corrigio"] = \
            o["resoluciones"][-1]["contrato_al_detectar"]

    def _resolucion_omitida(o, a):
        desacuerdo = _desacuerdo_base(o)
        _registrar_punto_ciego_historico(o, a, desacuerdo)
        o["resoluciones"].pop()

    def _evidencia_original_incorrecta(o, a):
        desacuerdo = _desacuerdo_base(o)
        _registrar_punto_ciego_historico(o, a, desacuerdo)
        o["resoluciones"][-1]["evidencia_original"] = ""

    def _corrida_posterior_parcial(o, a):
        desacuerdo = _desacuerdo_base(o)
        _registrar_punto_ciego_historico(o, a, desacuerdo)
        o["resoluciones"][-1]["corrida_posterior"]["completa"] = False

    mutantes = (
        ("clase-fuera-del-enum", _clase_fuera_del_enum, CAUSA_CLASE),
        ("motivo-vacio", _motivo_vacio, CAUSA_MOTIVO),
        ("punto-ciego-vigente", _punto_ciego_vigente, CAUSA_PUNTO_CIEGO_VIGENTE),
        ("historico-con-un-solo-hash", _historico_con_un_solo_hash, CAUSA_HISTORIAL),
        ("resolucion-omitida", _resolucion_omitida, CAUSA_HISTORIAL),
        ("evidencia-original-incorrecta", _evidencia_original_incorrecta, CAUSA_HISTORIAL),
        ("corrida-posterior-parcial", _corrida_posterior_parcial, CAUSA_HISTORIAL),
    )

    fallas = 0
    hallazgos = revisar_adjudicacion(oraculo, adjudicaciones)
    if hallazgos:
        print("FALLA  positivo: la adjudicación vigente da hallazgos:")
        for h in hallazgos[:5]:
            print(f"       - {h}")
        fallas += 1
    else:
        print("OK     positivo: la adjudicación vigente cierra")

    for nombre, mutar, causa in mutantes:
        o, a = copy.deepcopy(oraculo), copy.deepcopy(adjudicaciones)
        mutar(o, a)
        hallazgos = revisar_adjudicacion(o, a)
        propios = [h for h in hallazgos if h.startswith(causa)]
        ajenos = [h for h in hallazgos if not h.startswith(causa)]
        if not propios:
            print(f"FALLA  {nombre}: «{causa}» no se puso roja ({hallazgos[:2]})")
            fallas += 1
        elif ajenos:
            print(f"FALLA  {nombre}: además de «{causa}» se pusieron rojas otras ({ajenos[:2]})")
            fallas += 1
        else:
            print(f"OK     {nombre}: rojo por «{causa}» y solo por ella")

    print()
    total = len(mutantes) + 1
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de la adjudicación no se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de la adjudicación pasan")
    return 0


def _resolucion_sintetica(desacuerdo: dict) -> dict:
    return {"id": "R9000", "flujo": desacuerdo["flujo"], "task_id": desacuerdo["task_id"],
            "ocurrencia": desacuerdo["ocurrencia"], "contrato_al_detectar": "a" * 64,
            "contrato_que_corrigio": "b" * 64,
            "evidencia_original": "salidas/anterior.jsonl",
            "corrida_posterior": {"completa": True, "flujos_procesados": 21,
                                  "evidencia": "salidas/posterior.jsonl"},
            "resultado": "desaparecio"}


def _registrar_punto_ciego_historico(o: dict, a: dict, desacuerdo: dict) -> None:
    """Deja el punto ciego en el histórico y **resuelto**, para mutar solo su resolución."""
    a["adjudicaciones"].append({"id": "D9001", "flujo": desacuerdo["flujo"],
                                "task_id": desacuerdo["task_id"],
                                "ocurrencia": desacuerdo["ocurrencia"],
                                "clase_comparativa": "ve_mas",
                                "clase_adjudicada": "punto_ciego",
                                "motivo": "sintético", "evidencia": "salidas/anterior.jsonl",
                                "contrato": "a" * 64, "vigente": False})
    o["resoluciones"].append(_resolucion_sintetica(desacuerdo))


def modo_autotest_exclusiones(args: argparse.Namespace) -> int:
    del args
    import copy

    oraculo, e1 = _cargar_json(RUTA_ORACULO)
    comparacion, e2 = _cargar_json(RUTA_COMPARACION)
    if e1 or e2:
        print(f"FALLA  {e1 or e2}")
        return 1

    def _causa_fuera_del_enum(o, k):
        o["exclusiones"][0]["causas"] = ["se_me_ocurrio"]

    def _causas_vacio(o, k):
        o["exclusiones"][0]["causas"] = []

    def _causa_repetida(o, k):
        o["exclusiones"][0]["causas"] = ["sin_cobertura", "sin_cobertura"]

    def _terna_sin_entrada(o, k):
        o["exclusiones"].pop(0)

    def _entrada_sobrante(o, k):
        gemela = copy.deepcopy(o["exclusiones"][0])
        gemela["task_id"] = "T31337"
        o["exclusiones"].append(gemela)

    mutantes = (
        ("causa-fuera-del-enum", _causa_fuera_del_enum, CAUSA_CAUSA_FUERA_DEL_ENUM),
        ("causas-vacio", _causas_vacio, CAUSA_CAUSA_FUERA_DEL_ENUM),
        ("causa-repetida", _causa_repetida, CAUSA_CAUSAS_REPETIDAS),
        ("terna-excluida-sin-entrada", _terna_sin_entrada, CAUSA_COBERTURA_EXCLUSIONES),
        ("entrada-sobrante-sin-terna", _entrada_sobrante, CAUSA_COBERTURA_EXCLUSIONES),
    )

    fallas = 0
    hallazgos = revisar_exclusiones(oraculo, comparacion)
    if hallazgos:
        print("FALLA  positivo: las exclusiones vigentes dan hallazgos:")
        for h in hallazgos[:5]:
            print(f"       - {h}")
        fallas += 1
    else:
        print("OK     positivo: las exclusiones vigentes cierran")

    for nombre, mutar, causa in mutantes:
        o, k = copy.deepcopy(oraculo), copy.deepcopy(comparacion)
        mutar(o, k)
        hallazgos = revisar_exclusiones(o, k)
        propios = [h for h in hallazgos if h.startswith(causa)]
        if not propios:
            print(f"FALLA  {nombre}: «{causa}» no se puso roja ({hallazgos[:2]})")
            fallas += 1
        else:
            print(f"OK     {nombre}: rojo por «{causa}» — {propios[0][:100]}")

    print()
    total = len(mutantes) + 1
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de las exclusiones no se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de las exclusiones pasan. Los mutantes de «causa "
          "válida omitida» y «causa válida espuria» NO van acá: solo un clasificador los distingue")
    return 0


# ---------------------------------------------------------------------------------------------
# Modos `--evidencia` (V13) y `--autotest-evidencia` (V14). El conjunto cerrado de AC-6.
# ---------------------------------------------------------------------------------------------
#
# **La evidencia es un conjunto cerrado, no solo la salida cruda.** Sellar únicamente la salida
# dejaba que faltara o cambiara el prompt, la comparación o una reconciliación sin invalidar ningún
# hash. Y va al **árbol versionado**: `.cross-model/` está en `.git/info/exclude:13`, así que un
# clon del commit conservaría el oráculo y perdería la evidencia que lo acredita.

RUTA_MANIFEST_EVIDENCIA = DIR_EVIDENCIA / NOMBRE_MANIFEST_EVIDENCIA

ROLES_DE_EVIDENCIA = {
    "prompt": "prompts",
    "salida": "salidas",
    "comparacion": "comparacion",
    "adjudicaciones": "comparacion",
    "reconciliaciones": "comparacion",
}

CAUSA_ROL_FALTANTE = "rol-faltante"
CAUSA_ARCHIVO_SOBRANTE = "archivo-sobrante"
CAUSA_HASH_CAMBIADO = "hash-cambiado"
CAUSA_PROCEDENCIA = "procedencia"
CAUSA_PRODUCTOR = "productor-ausente"
CAUSA_CONDICIONES = "condiciones-de-lectura"
CAUSA_FAMILIAS_IGUALES = "familias-iguales"


def manifest_canonico(manifest: dict) -> str:
    """La proyección canónica del manifest de evidencia, **sin** su propio hash."""
    proyeccion = json.dumps({k: v for k, v in manifest.items() if k != "sha256_canonico"},
                            sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + _sha256_de(proyeccion.encode("utf-8"))


def revisar_evidencia(base: Path, manifest: dict, oraculo: dict, corpus: dict,
                      esperados_por_rol: dict[str, int]) -> list[str]:
    hallazgos: list[str] = []

    declarados = manifest.get("archivos", [])
    por_rol: dict[str, list[dict]] = {}
    for archivo in declarados:
        por_rol.setdefault(archivo.get("rol", "?"), []).append(archivo)

    for rol, cuantos in sorted(esperados_por_rol.items()):
        presentes = len(por_rol.get(rol, []))
        if presentes != cuantos:
            hallazgos.append(f"{CAUSA_ROL_FALTANTE}: el rol `{rol}` declara {presentes} archivos y "
                             f"la cardinalidad obligatoria es {cuantos}")
    for rol in sorted(set(por_rol) - set(esperados_por_rol)):
        hallazgos.append(f"{CAUSA_ROL_FALTANTE}: el rol `{rol}` no es ninguno de los obligatorios "
                         f"({sorted(esperados_por_rol)})")

    en_disco = {str(p.relative_to(base)) for p in base.rglob("*")
                if p.is_file() and p.name != NOMBRE_MANIFEST_EVIDENCIA}
    en_manifest = {a["ruta"] for a in declarados}
    for sobrante in sorted(en_disco - en_manifest):
        hallazgos.append(f"{CAUSA_ARCHIVO_SOBRANTE}: {sobrante} está en la evidencia y el manifest "
                         "no lo enumera — el conjunto es cerrado, sin extras")
    for faltante in sorted(en_manifest - en_disco):
        hallazgos.append(f"{CAUSA_ROL_FALTANTE}: el manifest enumera {faltante}, que no está en "
                         "disco")

    for archivo in declarados:
        ruta = base / archivo["ruta"]
        if not ruta.is_file():
            continue
        datos = ruta.read_bytes()
        if _sha256_de(datos) != archivo.get("sha256"):
            hallazgos.append(f"{CAUSA_HASH_CAMBIADO}: {archivo['ruta']} vale hoy "
                             f"{_sha256_de(datos)[:12]}… y el manifest selló "
                             f"{str(archivo.get('sha256'))[:12]}…")
        if len(datos) != archivo.get("tamano"):
            hallazgos.append(f"{CAUSA_HASH_CAMBIADO}: {archivo['ruta']} mide {len(datos)} bytes y "
                             f"el manifest selló {archivo.get('tamano')}")

    if manifest.get("sha256_canonico") != manifest_canonico(manifest):
        hallazgos.append(f"{CAUSA_PROCEDENCIA}: el manifest no lleva su propio hash canónico")

    procedencia = oraculo.get("procedencia") or {}
    if procedencia.get("manifest_evidencia") != manifest.get("sha256_canonico"):
        hallazgos.append(f"{CAUSA_PROCEDENCIA}: la `procedencia` del oráculo apunta a "
                         f"{procedencia.get('manifest_evidencia')} y el manifest sellado es "
                         f"{manifest.get('sha256_canonico')}")

    identidad = identidad_canonica_del_corpus(corpus)
    for etiqueta, valor in (("el manifest de evidencia", manifest.get("corpus_identidad")),
                            ("la procedencia del oráculo", procedencia.get("corpus_identidad")),
                            ("el oráculo", oraculo.get("corpus_identidad"))):
        if valor != identidad:
            hallazgos.append(f"{CAUSA_PROCEDENCIA}: {etiqueta} declara la identidad de corpus "
                             f"{valor} y la proyección canónica da {identidad}")

    if not (manifest.get("productor") or "").strip():
        hallazgos.append(f"{CAUSA_PRODUCTOR}: el manifest no declara quién produjo la evidencia")
    if not (manifest.get("condiciones_de_lectura") or "").strip():
        hallazgos.append(f"{CAUSA_CONDICIONES}: el manifest no declara las condiciones de lectura "
                         "del detector")

    conductor = procedencia.get("familia_conductor")
    detector = procedencia.get("familia_detector")
    if conductor and detector and conductor == detector:
        hallazgos.append(f"{CAUSA_FAMILIAS_IGUALES}: el detector y el conductor son la misma "
                         f"familia (`{conductor}`): no hay lectura independiente que contrastar")
    if manifest.get("familia_detector") != detector:
        hallazgos.append(f"{CAUSA_PROCEDENCIA}: el manifest dice que detectó "
                         f"`{manifest.get('familia_detector')}` y la procedencia dice `{detector}`")
    if manifest.get("familia_conductor") != conductor:
        hallazgos.append(f"{CAUSA_PROCEDENCIA}: el manifest dice que condujo "
                         f"`{manifest.get('familia_conductor')}` y la procedencia dice "
                         f"`{conductor}`")
    return hallazgos


def _cardinalidades_esperadas(corpus: dict) -> dict[str, int]:
    flujos = len(corpus.get("flujos", []))
    return {"prompt": flujos, "salida": flujos, "comparacion": 1, "adjudicaciones": 1,
            "reconciliaciones": 1}


def modo_evidencia(args: argparse.Namespace) -> int:
    del args
    manifest, e1 = _cargar_json(RUTA_MANIFEST_EVIDENCIA)
    oraculo, e2 = _cargar_json(RUTA_ORACULO)
    corpus, e3 = _cargar_json(RUTA_CORPUS)
    for error in (e1, e2, e3):
        if error:
            print(f"FALLA  {error}")
    if e1 or e2 or e3:
        return 1
    hallazgos = revisar_evidencia(DIR_EVIDENCIA, manifest, oraculo, corpus,
                                  _cardinalidades_esperadas(corpus))
    for h in hallazgos:
        print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} problemas en la evidencia sellada (AC-6)")
        return 1
    print(f"RESULTADO: OK — {len(manifest['archivos'])} archivos sellados sin extras, procedencia "
          "ligada al hash canónico y dos familias distintas")
    return 0


def modo_autotest_evidencia(args: argparse.Namespace) -> int:
    del args
    import copy

    manifest, e1 = _cargar_json(RUTA_MANIFEST_EVIDENCIA)
    oraculo, e2 = _cargar_json(RUTA_ORACULO)
    corpus, e3 = _cargar_json(RUTA_CORPUS)
    if e1 or e2 or e3:
        print(f"FALLA  {e1 or e2 or e3}")
        return 1
    esperados = _cardinalidades_esperadas(corpus)

    def _resellar(m: dict) -> None:
        m["sha256_canonico"] = manifest_canonico(m)

    def _quitar_rol(rol: str) -> Callable[[dict, dict], None]:
        def mutar(m, o):
            victima = next(a for a in m["archivos"] if a["rol"] == rol)
            m["archivos"].remove(victima)
            _resellar(m)
        return mutar

    def _archivo_sobrante(m, o):
        m["archivos"] = [a for a in m["archivos"] if a["rol"] != "prompt"] + \
                        [a for a in m["archivos"] if a["rol"] == "prompt"][:-1]
        _resellar(m)

    def _hash_cambiado(m, o):
        m["archivos"][0]["sha256"] = "0" * 64
        _resellar(m)

    def _procedencia_a_otra_identidad(m, o):
        o["procedencia"]["manifest_evidencia"] = "sha256:" + "c" * 64

    def _productor_ausente(m, o):
        m["productor"] = ""
        _resellar(m)

    def _condiciones_alteradas(m, o):
        m["condiciones_de_lectura"] = "  "
        _resellar(m)

    def _familias_iguales(m, o):
        o["procedencia"]["familia_detector"] = o["procedencia"]["familia_conductor"]
        m["familia_detector"] = m["familia_conductor"]
        _resellar(m)

    mutantes = [(f"sin-rol-{rol}", _quitar_rol(rol), CAUSA_ROL_FALTANTE) for rol in ROLES_DE_EVIDENCIA]
    mutantes += [
        ("archivo-sobrante", _archivo_sobrante, CAUSA_ARCHIVO_SOBRANTE),
        ("hash-cambiado", _hash_cambiado, CAUSA_HASH_CAMBIADO),
        ("procedencia-a-otra-identidad", _procedencia_a_otra_identidad, CAUSA_PROCEDENCIA),
        ("productor-ausente", _productor_ausente, CAUSA_PRODUCTOR),
        ("condiciones-de-lectura-alteradas", _condiciones_alteradas, CAUSA_CONDICIONES),
        ("familia-del-detector-igual-a-la-del-conductor", _familias_iguales, CAUSA_FAMILIAS_IGUALES),
    ]

    fallas = 0
    hallazgos = revisar_evidencia(DIR_EVIDENCIA, manifest, oraculo, corpus, esperados)
    if hallazgos:
        print("FALLA  positivo: la evidencia vigente da hallazgos:")
        for h in hallazgos[:5]:
            print(f"       - {h}")
        fallas += 1
    else:
        print("OK     positivo: la evidencia vigente cierra su sello")

    for nombre, mutar, causa in mutantes:
        m, o = copy.deepcopy(manifest), copy.deepcopy(oraculo)
        mutar(m, o)
        hallazgos = revisar_evidencia(DIR_EVIDENCIA, m, o, corpus, esperados)
        propios = [h for h in hallazgos if h.startswith(causa)]
        if not propios:
            print(f"FALLA  {nombre}: «{causa}» no se puso roja ({hallazgos[:2]})")
            fallas += 1
        else:
            print(f"OK     {nombre}: rojo por «{causa}» — {propios[0][:100]}")

    print()
    total = len(mutantes) + 1
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles de la evidencia no se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles de la evidencia pasan")
    return 0


# ---------------------------------------------------------------------------------------------
# Modos `--gate-precommit` (V24) y `--autotest-gate-precommit` (V25). La comprobación 2 de R9.
# ---------------------------------------------------------------------------------------------
#
# Va **precommit** porque `sdd-flow` verifica todos los AC antes de commitear: un AC anclado al
# commit final nunca se pone verde dentro de su propio ciclo.
#
# El conjunto a commitear es la **unión exacta** de cuatro fuentes —diff contra `HEAD`, index,
# working tree y untracked no ignorados—, con semántica declarada para renames y deletions. El caso
# **untracked no es opcional**: todos los entregables de este flujo son nuevos y `git diff HEAD` no
# los ve.

RUTA_PATHSET = DIR_SCRIPTS / "pathset-parser.json"

CAUSA_INTRUSO = "intruso"
CAUSA_GRAFO_DESACTUALIZADO = "grafo-desactualizado"
CAUSA_MECANISMO_FUERA_DEL_MODELO = "mecanismo-fuera-del-modelo"

# Los mecanismos de dependencia que el modelo declara. Todo lo que caiga fuera **aborta**.
# La ruta del caso untracked: un archivo nuevo que el pathset declara dependencia del parser.
NUEVA_DEPENDENCIA = "scripts/nuevo-ayudante-del-parser.py"

MECANISMOS_SOPORTADOS = ("import_estatico", "import_dinamico_conocido", "script_ejecutado",
                         "archivo_de_configuracion_leido")

PATRON_IMPORT = re.compile(r"^\s*(?:from\s+([.\w]+)\s+import|import\s+([.\w]+))")
PATRON_IMPORT_DINAMICO = re.compile(r"\b(?:importlib|__import__|exec|eval)\b")


def _git(*argumentos: str, raiz: Path | None = None) -> tuple[str, int]:
    import subprocess
    proceso = subprocess.run(["git", *argumentos], capture_output=True,
                             cwd=str(raiz or RAIZ))
    return proceso.stdout.decode("utf-8", errors="replace"), proceso.returncode


def conjunto_a_commitear(raiz: Path | None = None) -> tuple[set[str], list[str]]:
    """La unión exacta de las cuatro fuentes, con su semántica de renames y deletions.

    Un rename aporta **las dos** rutas: la vieja se borra y la nueva se crea, y tocar el parser de
    cualquiera de los dos lados es tocarlo. Una deletion aporta la ruta borrada, por la misma razón.
    """
    rutas: set[str] = set()
    problemas: list[str] = []

    salida, codigo = _git("diff", "--name-status", "-M", "HEAD", raiz=raiz)
    if codigo != 0:
        problemas.append("`git diff HEAD` falló: no se puede definir el conjunto a commitear")
    for linea in salida.splitlines():
        if not linea.strip():
            continue
        campos = linea.split("\t")
        rutas.update(campos[1:])

    for argumentos in (("diff", "--name-only", "--cached", "-M"), ("diff", "--name-only")):
        salida, _ = _git(*argumentos, raiz=raiz)
        rutas.update(x for x in salida.splitlines() if x.strip())

    salida, _ = _git("ls-files", "--others", "--exclude-standard", raiz=raiz)
    rutas.update(x for x in salida.splitlines() if x.strip())

    return rutas, problemas


def dependencias_del_pathset(pathset: dict) -> tuple[set[str], list[str]]:
    """El grafo dentro del repo, con los mecanismos declarados. Hoy el conjunto es **vacío**."""
    encontradas: set[str] = set()
    problemas: list[str] = []

    for mecanismo in pathset.get("mecanismos_soportados", []):
        if mecanismo not in MECANISMOS_SOPORTADOS:
            problemas.append(f"{CAUSA_MECANISMO_FUERA_DEL_MODELO}: el pathset declara el mecanismo "
                             f"`{mecanismo}`, que el validador no modela")

    for ruta in pathset.get("archivos", []):
        absoluta = RAIZ / ruta
        if not absoluta.is_file():
            problemas.append(f"{CAUSA_GRAFO_DESACTUALIZADO}: el pathset enumera {ruta}, que no "
                             "existe en el árbol")
            continue
        texto = absoluta.read_text(encoding="utf-8", errors="replace")
        if PATRON_IMPORT_DINAMICO.search(texto):
            problemas.append(f"{CAUSA_MECANISMO_FUERA_DEL_MODELO}: {ruta} usa carga dinámica; la "
                             "clausura del grafo no es demostrable por análisis estático")
        for linea in texto.split("\n"):
            encontrado = PATRON_IMPORT.match(linea)
            if not encontrado:
                continue
            modulo = (encontrado.group(1) or encontrado.group(2)).split(".")[0]
            candidata = f"{Path(ruta).parent}/{modulo}.py"
            if (RAIZ / candidata).is_file():
                encontradas.add(candidata)

    declaradas = set(pathset.get("dependencias", []))
    for faltante in sorted(encontradas - declaradas):
        problemas.append(f"{CAUSA_GRAFO_DESACTUALIZADO}: {faltante} es dependencia del parser en "
                         "HEAD y el pathset no la declara")
    for sobrante in sorted(declaradas - encontradas):
        problemas.append(f"{CAUSA_GRAFO_DESACTUALIZADO}: el pathset declara la dependencia "
                         f"{sobrante}, que el grafo en HEAD no encuentra")
    return declaradas | encontradas, problemas


def revisar_gate_precommit(pathset: dict, a_commitear: set[str]) -> list[str]:
    hallazgos: list[str] = []
    dependencias, problemas = dependencias_del_pathset(pathset)
    hallazgos.extend(problemas)

    vigilados = set(pathset.get("archivos", [])) | dependencias
    for intruso in sorted(a_commitear & vigilados):
        hallazgos.append(f"{CAUSA_INTRUSO}: el conjunto a commitear toca {intruso}, que es del "
                         "parser o de sus dependencias")
    return hallazgos


def modo_gate_precommit(args: argparse.Namespace) -> int:
    del args
    pathset, error = _cargar_json(RUTA_PATHSET)
    if error:
        print(f"FALLA  {error}")
        return 1
    a_commitear, problemas = conjunto_a_commitear()
    for problema in problemas:
        print(f"FALLA  {problema}")
    hallazgos = revisar_gate_precommit(pathset, a_commitear) + problemas
    for h in hallazgos:
        if h not in problemas:
            print(f"FALLA  {h}")
    print()
    if hallazgos:
        print(f"RESULTADO: FALLA — {len(hallazgos)} problemas: el commit tocaría el parser (AC-15)")
        return 1
    print(f"RESULTADO: OK — {len(a_commitear)} rutas a commitear, ninguna interseca el pathset "
          f"({len(pathset['archivos'])} archivos) ni sus dependencias "
          f"({len(pathset['dependencias'])})")
    return 0


def modo_autotest_gate_precommit(args: argparse.Namespace) -> int:
    del args
    import copy

    pathset, error = _cargar_json(RUTA_PATHSET)
    if error:
        print(f"FALLA  {error}")
        return 1
    reales, problemas = conjunto_a_commitear()
    if problemas:
        print(f"FALLA  {problemas[0]}")
        return 1

    parser = pathset["archivos"][0]
    fallas = 0

    hallazgos = revisar_gate_precommit(pathset, reales)
    if hallazgos:
        print("FALLA  positivo: el conjunto real a commitear ya toca el parser:")
        for h in hallazgos[:5]:
            print(f"       - {h}")
        fallas += 1
    else:
        print(f"OK     positivo: las {len(reales)} rutas reales no tocan el parser")

    # Control positivo **por estado de git, separado**, y sobre la maquinaria **real**: cada estado
    # se produce en un clon del repo y el conjunto se recalcula con `conjunto_a_commitear`. Agregar
    # la ruta a mano al conjunto probaría el filtro y no el descubrimiento — y el descubrimiento es
    # justo lo que puede perder el caso untracked, que `git diff HEAD` no ve.
    estados = ("staged", "unstaged", "untracked", "rename", "deletion")
    with tempfile.TemporaryDirectory() as tmp:
        for estado in estados:
            clon = Path(tmp) / estado
            _git("clone", "--quiet", "--no-hardlinks", str(RAIZ), str(clon))
            objetivo = clon / parser
            if estado == "staged":
                objetivo.write_text(objetivo.read_text(encoding="utf-8") + "\n# tocado\n",
                                    encoding="utf-8")
                _git("add", parser, raiz=clon)
            elif estado == "unstaged":
                objetivo.write_text(objetivo.read_text(encoding="utf-8") + "\n# tocado\n",
                                    encoding="utf-8")
            elif estado == "untracked":
                # Un archivo **nuevo**, nunca trackeado, que el pathset declara dependencia. No es
                # `git rm --cached` sobre el parser: eso aparecería también como `D` en
                # `git diff HEAD`, y el caso quedaría cubierto por otra fuente. Acá la única que lo
                # ve es `ls-files --others`, que es exactamente lo que V25 exige probar.
                (clon / NUEVA_DEPENDENCIA).write_text("# ayudante nuevo del parser\n",
                                                      encoding="utf-8")
            elif estado == "rename":
                _git("mv", parser, parser.replace(".py", "-renombrado.py"), raiz=clon)
            else:
                _git("rm", "--quiet", parser, raiz=clon)

            conjunto, problemas = conjunto_a_commitear(clon)
            vigilado = copy.deepcopy(pathset)
            if estado == "untracked":
                vigilado["dependencias"] = [NUEVA_DEPENDENCIA]
            hallazgos = revisar_gate_precommit(vigilado, conjunto) + problemas
            propios = [h for h in hallazgos if h.startswith(CAUSA_INTRUSO)]
            if not propios:
                print(f"FALLA  {estado}: el parser en estado {estado} no se detecta como intruso "
                      f"(el conjunto descubierto tiene {len(conjunto)} rutas)")
                fallas += 1
            else:
                print(f"OK     {estado}: rojo nombrando el intruso, descubierto por git")

    # Un archivo nuevo **importado** por el parser tiene que dar rojo aunque el pathset no lo
    # declare. Se ejerce sobre el **escáner real** de imports, no sobre una lista escrita a mano.
    ficticio = copy.deepcopy(pathset)
    ficticio["archivos"] = ["scripts/fixtures-oraculo/grafo/parser-ficticio.py"]
    ficticio["dependencias"] = []
    dependencias, problemas = dependencias_del_pathset(ficticio)
    esperadas = {"scripts/fixtures-oraculo/grafo/ayudante.py",
                 "scripts/fixtures-oraculo/grafo/ayudante_dos.py"}
    if dependencias != esperadas:
        print(f"FALLA  archivo-nuevo-importado: el escáner encontró {sorted(dependencias)} y el "
              f"fixture importa {sorted(esperadas)}")
        fallas += 1
    elif not any(p.startswith(CAUSA_GRAFO_DESACTUALIZADO) for p in problemas):
        print("FALLA  archivo-nuevo-importado: el pathset no las declara y no se reporta")
        fallas += 1
    else:
        hallazgos = revisar_gate_precommit(ficticio, reales | esperadas)
        if not any(h.startswith(CAUSA_INTRUSO) for h in hallazgos):
            print("FALLA  archivo-nuevo-importado: no se detecta como intruso")
            fallas += 1
        else:
            print("OK     archivo-nuevo-importado: el escáner lo encuentra y el gate lo prohíbe")

    # Un mecanismo fuera del modelo declarado **aborta**, nunca pasa en silencio. Dos formas: un
    # nombre de mecanismo que el validador no modela, y carga dinámica real en el fixture.
    for nombre, mutar in (
        ("mecanismo-no-modelado",
         lambda p: p.__setitem__("mecanismos_soportados",
                                 list(p["mecanismos_soportados"]) + ["carga_por_plugin"])),
        ("carga-dinamica-en-el-pathset",
         lambda p: p.__setitem__(
             "archivos", ["scripts/fixtures-oraculo/grafo/parser-con-carga-dinamica.py"])),
    ):
        fuera = copy.deepcopy(pathset)
        mutar(fuera)
        hallazgos = revisar_gate_precommit(fuera, reales)
        if not any(h.startswith(CAUSA_MECANISMO_FUERA_DEL_MODELO) for h in hallazgos):
            print(f"FALLA  {nombre}: no aborta")
            fallas += 1
        else:
            print(f"OK     {nombre}: aborta en vez de pasar en silencio")

    print()
    total = len(estados) + 4
    if fallas:
        print(f"RESULTADO: FALLA — {fallas} de {total} controles del gate precommit no se sostienen")
        return 1
    print(f"RESULTADO: OK — los {total} controles del gate precommit pasan")
    return 0


# ---------------------------------------------------------------------------------------------
# Registro y CLI.
# ---------------------------------------------------------------------------------------------

registrar_modo("--consumidor",
               "comprueba la alineación de AC-11 de `dossier-arnes` (AC-1, bloqueante)",
               modo_consumidor)
registrar_modo("--autotest-consumidor",
               "control positivo y negativo de `--consumidor`",
               modo_autotest_consumidor)
registrar_modo("--autotest-elegibilidad",
               "control positivo y negativo del predicado de AC-4bis",
               modo_autotest_elegibilidad)
registrar_modo("--autotest-lectura-unica",
               "control positivo de la función de lectura única instrumentada (D4)",
               modo_autotest_lectura_unica)
registrar_modo("--insumos",
               "valida en una ejecución los cuatro artefactos y los tres schemas (AC-3)",
               modo_insumos)
registrar_modo("--autotest-insumos",
               "control positivo y negativo de `--insumos` sobre el corpus sintético",
               modo_autotest_insumos)
registrar_modo("--evidencia",
               "el conjunto cerrado de la evidencia sellada y su procedencia (AC-6)",
               modo_evidencia)
registrar_modo("--autotest-evidencia",
               "control positivo y negativo de `--evidencia`, un mutante por rol y por enlace",
               modo_autotest_evidencia)
registrar_modo("--gate-precommit",
               "el conjunto a commitear no interseca el pathset del parser (AC-15)",
               modo_gate_precommit)
registrar_modo("--autotest-gate-precommit",
               "control positivo del gate, por estado de git y por mecanismo",
               modo_autotest_gate_precommit)
registrar_modo("--cobertura-deteccion",
               "las tres poblaciones de AC-7, como multiconjuntos",
               modo_cobertura_deteccion)
registrar_modo("--autotest-cobertura-deteccion",
               "control positivo y negativo de `--cobertura-deteccion`",
               modo_autotest_cobertura_deteccion)
registrar_modo("--adjudicacion",
               "clase, motivo, cero punto ciego vigente e historial (AC-8, AC-9)",
               modo_adjudicacion)
registrar_modo("--autotest-adjudicacion",
               "control positivo y negativo de `--adjudicacion`",
               modo_autotest_adjudicacion)
registrar_modo("--exclusiones",
               "causas del enum de R5, sin repetidos, con su cobertura (AC-10)",
               modo_exclusiones)
registrar_modo("--autotest-exclusiones",
               "control positivo y negativo de `--exclusiones`",
               modo_autotest_exclusiones)
registrar_modo("--prompt",
               "identidad, variables y ausencia de adjuntos prohibidos en los prompts (AC-6)",
               modo_prompt)
registrar_modo("--autotest-prompt",
               "control positivo y negativo de `--prompt`",
               modo_autotest_prompt)
registrar_modo("--adaptadores",
               "los dos adaptadores de familia: aislamiento y cosecha (AC-6)",
               modo_adaptadores)
registrar_modo("--autotest-adaptadores",
               "control positivo y negativo de `--adaptadores`, por adaptador y por causa",
               modo_autotest_adaptadores)
registrar_modo("--casos",
               "las siete reglas con positivo y negativo, y cada origen resuelto (AC-11, AC-12)",
               modo_casos)
registrar_modo("--autotest-casos",
               "control positivo y negativo de `--casos`",
               modo_autotest_casos)
registrar_modo("--casos-obligatorios",
               "las cinco identidades obligatorias de AC-13",
               modo_casos_obligatorios)
registrar_modo("--autotest-casos-obligatorios",
               "control positivo y negativo de `--casos-obligatorios`",
               modo_autotest_casos_obligatorios)
registrar_modo("--forma-oraculo",
               "las seis secciones del oráculo y sus invariantes (AC-2)",
               modo_forma_oraculo)
registrar_modo("--autotest-forma-oraculo",
               "control positivo y negativo de `--forma-oraculo`",
               modo_autotest_forma_oraculo)
registrar_modo("--proxies",
               "los seis proxies de AC-14, con su límite declarado",
               modo_proxies)
registrar_modo("--autotest-proxies",
               "control positivo y negativo de `--proxies`",
               modo_autotest_proxies)
registrar_modo("--proyecciones",
               "las dos proyecciones bidireccionales de AC-4",
               modo_proyecciones)
registrar_modo("--autotest-proyecciones",
               "control positivo y negativo de `--proyecciones`",
               modo_autotest_proyecciones)
registrar_modo("--invariantes-corpus",
               "las cuatro invariantes de unicidad y referencialidad de AC-5",
               modo_invariantes_corpus)
registrar_modo("--autotest-invariantes-corpus",
               "control positivo y negativo de `--invariantes-corpus`",
               modo_autotest_invariantes_corpus)


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verificar-oraculo.py",
        description="Validador de los insumos congelados del oráculo de la Fase 0.5.",
    )
    for modo in MODOS:
        parser.add_argument(modo.bandera, action="store_true", help=modo.ayuda)
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
