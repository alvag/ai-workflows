#!/usr/bin/env python3
"""Verifica la matriz de despachos contra su schema cerrado.

Dos modos, y por ahora solo dos: los demás del catálogo los construyen otras tasks.

- `--schema [ruta]` — valida la matriz (por defecto `scripts/matriz-despachos.json`) contra
  `scripts/matriz-despachos.schema.json`. Comprueba tres cosas y no una: que el schema sea
  consistente consigo mismo, que la instancia lo satisfaga, y que los valores agregados coincidan
  con lo que sus reglas de derivación producen a partir de las hojas que los alimentan.
- `--autotest-schema` — control positivo y negativo del modo anterior sobre el corpus sintético de
  `scripts/fixtures-matriz/`.

Tres reglas de diseño:

1. **Sin dependencias.** No hay `jsonschema` en esta máquina y el repo solo usa stdlib + PyYAML.
   El validador de acá cubre el subconjunto que el schema usa y **rechaza cualquier palabra clave
   que no implemente**: una palabra ignorada en silencio es una restricción que el schema declara y
   nadie aplica, o sea una guarda que no puede ponerse roja.
2. **El inventario se deriva del schema; lo que se congela es el criterio.** El autotest lee el
   schema y deriva la lista exacta de sus elementos en once dimensiones —campos obligatorios,
   vocabularios cerrados, constantes, acoplamientos, restricciones de arreglo, mínimos y máximos,
   longitudes, patrones, objetos cerrados, agregados derivados y propiedades simultáneas—, y la
   compara contra `INVENTARIO_CONGELADO`. Divergir es rojo: un elemento nuevo en el schema sin su
   entrada acá nacería sin mutante y nadie lo notaría. **El valor va dentro del id del elemento**,
   no solo su nombre: congelar `enum_transporte` a secas deja pasar que alguien le agregue un
   token, y congelar `cardinalidad_exactamente_n.n` a secas deja pasar que su mínimo baje de 1 a 0
   —que es exactamente lo que el schema declara que no puede ocurrir—. Las dos cosas pasaron al
   probar este autotest contra sí mismo.
3. **Un mutante por elemento, no uno por categoría.** Un representante correcto por categoría
   convive con otro campo mal modelado, y la fila de aplicación no cierra esa dirección porque
   valida contra el mismo schema. Los mutantes se **generan** desde el corpus conforme —no se
   transcriben— así que la correspondencia elemento ↔ mutante es por construcción.

Y la regla que gobierna a los autotests del flujo: además de sus mutantes, este modo declara casos
**conformes** que tienen que pasar. Sin ellos, un validador que rechace toda entrada satisface todos
los casos negativos y el autotest cierra en verde sin haber aceptado jamás una matriz válida. Acá el
control positivo tiene tres partes: los fixtures conformes validan; **todo** `$defs` queda
instanciado por alguno de ellos y **todo** valor de los vocabularios operacionales queda ejercido
—una operación declarada y nunca ejercida está tan sin probar como una que no existe—; y cada
propiedad simultánea aparece con dos valores o más, porque declararla arreglo y no ejercerla nunca la
deja tan colapsada como declararla escalar.

Uso: python3 scripts/verificar-matriz-despachos.py --schema [ruta] | --autotest-schema
Exit 0 si el modo pasa, 1 si falla, 2 si la invocación es inválida.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any, NamedTuple

REPO = Path(__file__).resolve().parent.parent
RUTA_SCHEMA = REPO / "scripts" / "matriz-despachos.schema.json"
RUTA_MATRIZ = REPO / "scripts" / "matriz-despachos.json"
DIR_FIXTURES = REPO / "scripts" / "fixtures-matriz"

# Los fixtures conformes, en el orden en que se reportan. Cada uno cubre algo que los otros no:
# el mínimo ejerce la ausencia legítima de sede; el de multiplicidad, los valores simultáneos y la
# derivación a `mixto`; el de operaciones, el vocabulario que a los otros dos no les toca.
CONFORMES = (
    "conforme-minimo.json",
    "conforme-multiplicidad.json",
    "conforme-operaciones.json",
)

# ---------------------------------------------------------------------------------------------
# Inventario congelado.
#
# NO es la fuente de verdad —el schema lo es—: es el testigo. El autotest deriva el inventario del
# schema en cada corrida y lo compara contra esto; si difieren, se pone rojo nombrando la
# diferencia. Congelarlo a mano como fuente ya salió mal en este repo; derivarlo sin congelarlo
# dejaría entrar un elemento nuevo sin mutante y sin que nada lo señale.
# ---------------------------------------------------------------------------------------------

INVENTARIO_CONGELADO: dict[str, tuple[str, ...]] = {
    "acoplamientos": (
        'condicion_atomo_comparacion.acoplamiento[0]',
        'condicion_atomo_comparacion.acoplamiento[1]',
        'procedencia_anclada.acoplamiento[0]',
        'procedencia_anclada.acoplamiento[1]',
        'procedencia_anclada.acoplamiento[2]',
        'procedencia_anclada.acoplamiento[3]',
    ),
    "agregados": (
        'escritura_agregada',
        'familias_cubiertas',
        'transporte_agregado',
    ),
    "cerrados": (
        'cardinalidad_al_menos_una',
        'cardinalidad_exactamente_n',
        'cardinalidad_exactamente_una',
        'condicion_atomo_capacidad',
        'condicion_atomo_comparacion',
        'condicion_no',
        'condicion_o',
        'condicion_siempre',
        'condicion_y',
        'extraccion_captura_de_grupo',
        'extraccion_literal',
        'extraccion_valor_de_clave',
        'hoja_booleano',
        'hoja_cadena_anclada',
        'hoja_entero',
        'hoja_entero_anclada',
        'hoja_enum_autoridad_final_anclada',
        'hoja_enum_escritura',
        'hoja_enum_familia',
        'hoja_enum_permiso_efectivo',
        'hoja_enum_rol',
        'hoja_enum_skill',
        'hoja_enum_transporte',
        'hoja_enum_variante',
        'hoja_lista_cadena',
        'hoja_referencia',
        'intento',
        'procedencia_anclada',
        'procedencia_ausente',
        'punto',
        'raiz',
        'selector_clave_estructurada',
        'selector_fila_de_tabla_markdown',
        'selector_heading_markdown',
        'selector_patron_de_linea',
        'trabajo_delegado',
    ),
    "constantes": (
        'cardinalidad_al_menos_una.tipo=al_menos_una',
        'cardinalidad_exactamente_n.tipo=exactamente_n',
        'cardinalidad_exactamente_una.tipo=exactamente_una',
        'condicion_atomo_capacidad.tipo=atomo',
        'condicion_atomo_comparacion.tipo=atomo',
        'condicion_no.tipo=no',
        'condicion_o.tipo=o',
        'condicion_siempre.tipo=siempre',
        'condicion_y.tipo=y',
        'extraccion_captura_de_grupo.tipo=captura_de_grupo',
        'extraccion_literal.tipo=literal',
        'extraccion_valor_de_clave.tipo=valor_de_clave',
        'raiz.version_schema=1.0.0',
    ),
    "longitudes": (
        'condicion_atomo_capacidad.clave.minLength=1',
        'condicion_atomo_comparacion.clave.minLength=1',
        'condicion_atomo_comparacion.valor.[].minLength=1',
        'condicion_atomo_comparacion.valor.minLength=1',
        'extraccion_captura_de_grupo.patron.minLength=1',
        'hoja_cadena_anclada.valor.minLength=1',
        'hoja_lista_cadena.valor.[].minLength=1',
        'hoja_referencia.valor.minLength=1',
        'intento.intento_id.minLength=1',
        'procedencia_ausente.ausencia.minLength=1',
        'punto.etiqueta.minLength=1',
        'ruta_de_archivo.minLength=1',
        'ruta_de_clave.[].minLength=1',
        'selector_clave_estructurada.lenguaje_del_bloque.minLength=1',
        'selector_fila_de_tabla_markdown.clave_primera_celda.minLength=1',
        'selector_fila_de_tabla_markdown.encabezado_de_columna.minLength=1',
        'selector_heading_markdown.texto.minLength=1',
        'selector_patron_de_linea.patron.minLength=1',
        'trabajo_delegado.nombre.minLength=1',
    ),
    "obligatorios": (
        'cardinalidad_al_menos_una.colapso',
        'cardinalidad_al_menos_una.orden',
        'cardinalidad_al_menos_una.tipo',
        'cardinalidad_exactamente_n.colapso',
        'cardinalidad_exactamente_n.n',
        'cardinalidad_exactamente_n.orden',
        'cardinalidad_exactamente_n.tipo',
        'cardinalidad_exactamente_una.tipo',
        'condicion_atomo_capacidad.clave',
        'condicion_atomo_capacidad.operador',
        'condicion_atomo_capacidad.procedencia',
        'condicion_atomo_capacidad.tipo',
        'condicion_atomo_comparacion.clave',
        'condicion_atomo_comparacion.operador',
        'condicion_atomo_comparacion.procedencia',
        'condicion_atomo_comparacion.tipo',
        'condicion_atomo_comparacion.valor',
        'condicion_no.operando',
        'condicion_no.tipo',
        'condicion_o.operandos',
        'condicion_o.tipo',
        'condicion_siempre.procedencia',
        'condicion_siempre.tipo',
        'condicion_y.operandos',
        'condicion_y.tipo',
        'extraccion_captura_de_grupo.grupo',
        'extraccion_captura_de_grupo.patron',
        'extraccion_captura_de_grupo.tipo',
        'extraccion_literal.tipo',
        'extraccion_valor_de_clave.clave',
        'extraccion_valor_de_clave.tipo',
        'hoja_booleano.procedencia',
        'hoja_booleano.valor',
        'hoja_cadena_anclada.procedencia',
        'hoja_cadena_anclada.valor',
        'hoja_entero.procedencia',
        'hoja_entero.valor',
        'hoja_entero_anclada.procedencia',
        'hoja_entero_anclada.valor',
        'hoja_enum_autoridad_final_anclada.procedencia',
        'hoja_enum_autoridad_final_anclada.valor',
        'hoja_enum_escritura.procedencia',
        'hoja_enum_escritura.valor',
        'hoja_enum_familia.procedencia',
        'hoja_enum_familia.valor',
        'hoja_enum_permiso_efectivo.procedencia',
        'hoja_enum_permiso_efectivo.valor',
        'hoja_enum_rol.procedencia',
        'hoja_enum_rol.valor',
        'hoja_enum_skill.procedencia',
        'hoja_enum_skill.valor',
        'hoja_enum_transporte.procedencia',
        'hoja_enum_transporte.valor',
        'hoja_enum_variante.procedencia',
        'hoja_enum_variante.valor',
        'hoja_lista_cadena.procedencia',
        'hoja_lista_cadena.valor',
        'hoja_referencia.procedencia',
        'hoja_referencia.valor',
        'intento.deadline_declarado',
        'intento.intento_id',
        'intento.transporte',
        'procedencia_anclada.cardinalidad',
        'procedencia_anclada.conversion',
        'procedencia_anclada.extraccion',
        'procedencia_anclada.normalizacion',
        'procedencia_anclada.sede',
        'procedencia_anclada.selector',
        'procedencia_anclada.tipo_de_sede',
        'procedencia_ausente.ausencia',
        'punto.ancla_de_invocacion',
        'punto.autoridad_final',
        'punto.condicion_de_existencia',
        'punto.contrato_de_salida',
        'punto.dueno',
        'punto.escritura_agregada',
        'punto.etiqueta',
        'punto.fallback',
        'punto.familias_cubiertas',
        'punto.id',
        'punto.modos',
        'punto.permisos_efectivos',
        'punto.presupuesto_de_espera_contractual',
        'punto.requiere_confirmacion_del_usuario',
        'punto.rol',
        'punto.senales_de_deteccion',
        'punto.skill',
        'punto.trabajos_delegados',
        'punto.transporte_agregado',
        'punto.variante',
        'raiz.puntos',
        'raiz.version_schema',
        'selector_clave_estructurada.formato',
        'selector_clave_estructurada.ruta',
        'selector_fila_de_tabla_markdown.clave_primera_celda',
        'selector_fila_de_tabla_markdown.encabezado_de_columna',
        'selector_heading_markdown.nivel',
        'selector_heading_markdown.texto',
        'selector_patron_de_linea.patron',
        'trabajo_delegado.escritura',
        'trabajo_delegado.familia',
        'trabajo_delegado.intentos',
        'trabajo_delegado.nombre',
    ),
    "patrones": (
        'conversion.pattern=^enum:[a-z][a-z0-9_]*$',
        'punto.id.pattern=^[a-z0-9]+(-[a-z0-9]+)*$',
        'ruta_de_archivo.pattern=^(?!.*(?:^|/)\\.\\.(?:/|$))[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$',
        'selector_patron_de_linea.patron.pattern=(^\\^)|(\\$$)',
    ),
    "restricciones_de_arreglo": (
        'condicion_atomo_comparacion.valor.minItems=1',
        'condicion_atomo_comparacion.valor.uniqueItems=true',
        'condicion_o.operandos.minItems=2',
        'condicion_y.operandos.minItems=2',
        'hoja_lista_cadena.valor.minItems=1',
        'hoja_lista_cadena.valor.uniqueItems=true',
        'punto.familias_cubiertas.minItems=1',
        'punto.familias_cubiertas.uniqueItems=true',
        'punto.trabajos_delegados.minItems=1',
        'raiz.puntos.minItems=1',
        'ruta_de_clave.minItems=1',
        'trabajo_delegado.intentos.minItems=1',
    ),
    "restricciones_numericas": (
        'cardinalidad_exactamente_n.n.minimum=1',
        'extraccion_captura_de_grupo.grupo.minimum=0',
        'hoja_entero.valor.minimum=0',
        'hoja_entero_anclada.valor.minimum=0',
        'ruta_de_clave.[].minimum=0',
        'selector_heading_markdown.nivel.maximum=6',
        'selector_heading_markdown.nivel.minimum=1',
    ),
    "simultaneas": (
        'punto.familias_cubiertas',
        'punto.modos.valor',
        'punto.senales_de_deteccion.valor',
    ),
    "vocabularios": (
        'conversion=cadena|entero|booleano|referencia|patron:^enum:[a-z][a-z0-9_]*$',
        'enum_autoridad_final=conductor|usuario',
        'enum_colapso=lista|unico_si_iguales',
        'enum_conversion_base=cadena|entero|booleano|referencia',
        'enum_escritura=read_only|escritor',
        'enum_escritura_agregada=read_only|escritor|mixta',
        'enum_familia=opuesta_al_conductor|misma_del_conductor',
        'enum_formato_estructurado=json|yaml',
        'enum_normalizacion=ninguna|trim|colapsar_espacios|minusculas',
        'enum_operador_capacidad=disponible|no_disponible',
        'enum_operador_comparacion=igual|distinto|en|no_en',
        'enum_orden=documento|lexicografico',
        'enum_permiso_efectivo=read_only|workspace_write_acotado',
        'enum_rol=explorer|investigator|design-reviewer|bounded-implementer|diff-reviewer',
        'enum_skill=bitbucket-code-review|co-explore|cross-implement|cross-review|sdd-flow|sdd-orchestrator|sdd-pr-feedback',
        'enum_tipo_de_sede=heading_markdown|fila_de_tabla_markdown|clave_estructurada|patron_de_linea',
        'enum_transporte=subagent|cli-exec|cli-resume',
        'enum_transporte_agregado=subagent|cli-exec|cli-resume|mixto',
        'enum_variante=ninguna|artifact-review|decision-debate|review|refute|work-order|task|repo-runner',
    ),
}

# Vocabularios cuyo valor a valor tiene que quedar ejercido por el corpus conforme, y no solo
# instanciado una vez: son las operaciones del contrato de procedencia y la gramática de las
# condiciones. Para los enums de dominio —skill, rol, variante, permisos— alcanza con que el
# vocabulario quede instanciado: su distribución real es dato de la matriz, no del schema.
VOCABULARIOS_CON_COBERTURA_DE_VALOR = (
    "conversion",
    "enum_colapso",
    "enum_formato_estructurado",
    "enum_normalizacion",
    "enum_operador_capacidad",
    "enum_operador_comparacion",
    "enum_orden",
    "enum_tipo_de_sede",
)

PALABRAS_SOPORTADAS = frozenset({
    "$ref", "type", "enum", "const", "pattern", "minLength", "minimum", "maximum",
    "minItems", "maxItems", "uniqueItems", "properties", "required", "additionalProperties",
    "items", "oneOf", "allOf", "if", "then", "else",
})
PALABRAS_IGNORADAS = frozenset({"$schema", "$id", "title", "description", "$defs", "$comment"})

REGLAS_DE_DERIVACION = frozenset({"valor_comun_o_marca_de_discrepancia", "conjunto_ordenado"})

CENTINELA_VOCABULARIO = "__fuera_del_vocabulario__"
CENTINELA_CONSTANTE = "__constante_cambiada__"
CENTINELA_PROPIEDAD = "__propiedad_no_declarada__"
CENTINELA_PATRON = ".. no casa con ningún patrón del schema .."

_SIN_VALOR = object()


# ---------------------------------------------------------------------------------------------
# Validador. Subconjunto de JSON Schema 2020-12, con dos particularidades deliberadas: registra
# qué `$defs` quedó instanciado en qué ruta (lo consume el generador de mutantes) y rechaza toda
# palabra clave que no implemente.
# ---------------------------------------------------------------------------------------------

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


class Contexto:
    """Lleva el schema raíz y el registro de instanciación de `$defs`."""

    def __init__(self, schema: dict) -> None:
        self.schema = schema
        self.instancias: list[tuple[str, Ruta]] = []

    def resolver(self, ref: str) -> dict:
        if not ref.startswith("#/$defs/"):
            raise ValueError(f"referencia no local o no soportada: {ref}")
        nombre = ref[len("#/$defs/"):]
        defs = self.schema.get("$defs", {})
        if nombre not in defs:
            raise ValueError(f"referencia a un `$defs` inexistente: {ref}")
        return defs[nombre]


def validar(instancia: Any, schema: dict, ctx: Contexto | None = None) -> tuple[list[Error], Contexto]:
    """Valida `instancia` contra `schema` (que es el schema raíz). Devuelve errores y contexto."""
    if ctx is None:
        ctx = Contexto(schema)
    errores = _validar(instancia, schema, ctx, ())
    if not errores:
        ctx.instancias.append(("raiz", ()))
    return errores, ctx


def _validar(valor: Any, esquema: dict, ctx: Contexto, ruta: Ruta) -> list[Error]:
    errores: list[Error] = []

    if "$ref" in esquema:
        nombre = esquema["$ref"][len("#/$defs/"):]
        marca = len(ctx.instancias)
        sub_err = _validar(valor, ctx.resolver(esquema["$ref"]), ctx, ruta)
        if sub_err:
            del ctx.instancias[marca:]
            errores.extend(sub_err)
        else:
            ctx.instancias.append((nombre, ruta))

    if "oneOf" in esquema:
        exitosas = 0
        fallidas: list[tuple[bool, int, list[Error]]] = []
        for rama in esquema["oneOf"]:
            marca = len(ctx.instancias)
            errs = _validar(valor, rama, ctx, ruta)
            if errs:
                del ctx.instancias[marca:]
                fallidas.append((_fallo_de_discriminador(errs, rama, ctx, ruta), len(errs), errs))
            else:
                exitosas += 1
        if exitosas == 0:
            # Se reporta una sola rama: reportarlas todas convierte un campo faltante en un muro de
            # ruido. Cuál, no lo decide el conteo de errores —eso atribuye mal en cuanto dos ramas
            # fallan con uno cada una—, lo decide el discriminador: una rama que falló en su propia
            # constante no es la que se quiso escribir.
            errores.extend(min(fallidas, key=lambda f: (f[0], f[1]))[2])
        elif exitosas > 1:
            errores.append(Error(ruta, "más de una variante del `oneOf` valida este nodo: la unión no está discriminada"))

    for sub in esquema.get("allOf", []):
        errores.extend(_validar(valor, sub, ctx, ruta))

    if "if" in esquema:
        marca = len(ctx.instancias)
        condicion = _validar(valor, esquema["if"], ctx, ruta)
        del ctx.instancias[marca:]  # la rama `if` es una pregunta, no una instanciación
        rama = esquema.get("then") if not condicion else esquema.get("else")
        if rama is not None:
            errores.extend(_validar(valor, rama, ctx, ruta))

    tipo = esquema.get("type")
    if tipo is not None and not _tipo_ok(valor, tipo):
        errores.append(Error(ruta, f"se esperaba tipo `{tipo}` y llegó `{_nombre_tipo(valor)}`"))
        return errores  # sin el tipo correcto, el resto de las restricciones no significa nada

    if "enum" in esquema and not any(_mismo(valor, v) for v in esquema["enum"]):
        errores.append(Error(ruta, f"valor fuera del vocabulario cerrado: {valor!r} no está en {esquema['enum']}"))
    if "const" in esquema and not _mismo(valor, esquema["const"]):
        errores.append(Error(ruta, f"se esperaba la constante {esquema['const']!r} y llegó {valor!r}"))

    if isinstance(valor, str):
        if "minLength" in esquema and len(valor) < esquema["minLength"]:
            errores.append(Error(ruta, f"cadena más corta que `minLength` ({esquema['minLength']})"))
        if "pattern" in esquema and re.search(esquema["pattern"], valor) is None:
            errores.append(Error(ruta, f"la cadena {valor!r} no casa con el patrón {esquema['pattern']!r}"))

    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        if "minimum" in esquema and valor < esquema["minimum"]:
            errores.append(Error(ruta, f"valor menor que `minimum` ({esquema['minimum']})"))
        if "maximum" in esquema and valor > esquema["maximum"]:
            errores.append(Error(ruta, f"valor mayor que `maximum` ({esquema['maximum']})"))

    if isinstance(valor, list):
        if "minItems" in esquema and len(valor) < esquema["minItems"]:
            errores.append(Error(ruta, f"el arreglo tiene {len(valor)} elementos y `minItems` es {esquema['minItems']}"))
        if "maxItems" in esquema and len(valor) > esquema["maxItems"]:
            errores.append(Error(ruta, f"el arreglo tiene {len(valor)} elementos y `maxItems` es {esquema['maxItems']}"))
        if esquema.get("uniqueItems") and _hay_repetidos(valor):
            errores.append(Error(ruta, "el arreglo declara `uniqueItems` y tiene elementos repetidos"))
        if "items" in esquema:
            for i, elemento in enumerate(valor):
                errores.extend(_validar(elemento, esquema["items"], ctx, ruta + (i,)))

    if isinstance(valor, dict):
        propiedades = esquema.get("properties", {})
        for campo in esquema.get("required", []):
            if campo not in valor:
                errores.append(Error(ruta + (campo,), f"falta el campo obligatorio `{campo}`"))
        cerrado = esquema.get("additionalProperties", True) is False
        for clave, sub in valor.items():
            if clave in propiedades:
                errores.extend(_validar(sub, propiedades[clave], ctx, ruta + (clave,)))
            elif cerrado:
                errores.append(Error(ruta + (clave,), f"propiedad no declarada `{clave}` en un objeto cerrado"))

    return errores


def _fallo_de_discriminador(errores: list[Error], rama: dict, ctx: Contexto, ruta: Ruta) -> bool:
    """True si la rama falló en una de sus propias constantes: entonces no es la variante que se
    quiso escribir, y sus errores no explican nada del nodo que llegó."""
    objetivo = ctx.resolver(rama["$ref"]) if "$ref" in rama else rama
    claves = {c for c, sub in objetivo.get("properties", {}).items() if "const" in sub}
    return any(e.ruta in {ruta + (c,) for c in claves} for e in errores)


def _hay_repetidos(valores: list) -> bool:
    vistos: list[str] = []
    for v in valores:
        clave = json.dumps(v, sort_keys=True, ensure_ascii=False)
        if clave in vistos:
            return True
        vistos.append(clave)
    return False


# ---------------------------------------------------------------------------------------------
# Recorrido del schema. Devuelve, por cada `$defs` (y por la raíz), todos sus sub-esquemas con dos
# coordenadas: el puntero dentro del schema —para mutarlo— y la ruta de instancia relativa —para
# mutar la matriz—. No cruza `$ref`: cada `$defs` se recorre una sola vez, por sí mismo.
# ---------------------------------------------------------------------------------------------

class SubEsquema(NamedTuple):
    definicion: str
    puntero: tuple
    ruta_rel: Ruta
    esquema: dict
    en_condicion: bool  # True dentro de un `if`: ahí `required` es una pregunta, no una obligación


def _recorrer_definicion(nombre: str, esquema: dict, puntero: tuple) -> list[SubEsquema]:
    salida: list[SubEsquema] = []

    def caminar(sub: dict, punt: tuple, rel: Ruta, en_condicion: bool) -> None:
        salida.append(SubEsquema(nombre, punt, rel, sub, en_condicion))
        if "$ref" in sub:
            return
        for clave, valor in sub.get("properties", {}).items():
            caminar(valor, punt + ("properties", clave), rel + (clave,), en_condicion)
        if "items" in sub:
            caminar(sub["items"], punt + ("items",), rel + ("[]",), en_condicion)
        for i, rama in enumerate(sub.get("oneOf", [])):
            caminar(rama, punt + ("oneOf", i), rel, en_condicion)
        for i, rama in enumerate(sub.get("allOf", [])):
            caminar(rama, punt + ("allOf", i), rel, en_condicion)
        if "if" in sub:
            caminar(sub["if"], punt + ("if",), rel, True)
        for clave in ("then", "else"):
            if clave in sub:
                caminar(sub[clave], punt + (clave,), rel, en_condicion)

    caminar(esquema, puntero, (), False)
    return salida


def _todos_los_subesquemas(schema: dict) -> list[SubEsquema]:
    salida = _recorrer_definicion("raiz", schema, ())
    for nombre, definicion in schema.get("$defs", {}).items():
        salida.extend(_recorrer_definicion(nombre, definicion, ("$defs", nombre)))
    return salida


def _id_elemento(definicion: str, ruta_rel: Ruta, sufijo: str = "", valor: Any = _SIN_VALOR) -> str:
    """El id de un elemento del inventario. Cuando el elemento declara un valor —el vocabulario de
    un enum, una constante, un `minimum`— el valor va **dentro del id**: congelar solo el nombre
    deja pasar que alguien amplíe el enum o baje el mínimo sin que el testigo lo note."""
    partes = [definicion, *[str(t) for t in ruta_rel]]
    if sufijo:
        partes.append(sufijo)
    identificador = ".".join(partes)
    if valor is _SIN_VALOR:
        return identificador
    return f"{identificador}={_texto_de_valor(valor)}"


def _texto_de_valor(valor: Any) -> str:
    if isinstance(valor, list):
        return "|".join(_texto_de_valor(v) for v in valor)
    return valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------------------------------------
# Derivación del inventario.
# ---------------------------------------------------------------------------------------------

def derivar_inventario(schema: dict) -> dict[str, dict[str, dict]]:
    """El inventario que el schema declara, por dimensión: id del elemento → detalle."""
    subs = _todos_los_subesquemas(schema)
    inventario: dict[str, dict[str, dict]] = {
        "obligatorios": {},
        "vocabularios": {},
        "constantes": {},
        "acoplamientos": {},
        "restricciones_de_arreglo": {},
        "restricciones_numericas": {},
        "longitudes": {},
        "patrones": {},
        "cerrados": {},
        "agregados": {},
        "simultaneas": {},
    }

    for sub in subs:
        if sub.en_condicion:
            continue
        e = sub.esquema

        for campo in e.get("required", []):
            clave = _id_elemento(sub.definicion, sub.ruta_rel, campo)
            inventario["obligatorios"][clave] = {
                "definicion": sub.definicion, "ruta_rel": sub.ruta_rel, "campo": campo,
            }

        valores = _vocabulario_cerrado(e, schema)
        if valores is not None:
            clave = _id_elemento(sub.definicion, sub.ruta_rel, valor=valores)
            inventario["vocabularios"][clave] = {
                "definicion": sub.definicion, "ruta_rel": sub.ruta_rel, "valores": valores,
            }

        if "const" in e:
            clave = _id_elemento(sub.definicion, sub.ruta_rel, valor=e["const"])
            inventario["constantes"][clave] = {
                "definicion": sub.definicion, "ruta_rel": sub.ruta_rel, "valor": e["const"],
            }

        for restriccion in ("minItems", "uniqueItems"):
            if restriccion in e:
                clave = _id_elemento(sub.definicion, sub.ruta_rel, restriccion, valor=e[restriccion])
                inventario["restricciones_de_arreglo"][clave] = {
                    "definicion": sub.definicion, "ruta_rel": sub.ruta_rel,
                    "restriccion": restriccion, "valor": e[restriccion],
                }

        for restriccion in ("minimum", "maximum"):
            if restriccion in e:
                clave = _id_elemento(sub.definicion, sub.ruta_rel, restriccion, valor=e[restriccion])
                inventario["restricciones_numericas"][clave] = {
                    "definicion": sub.definicion, "ruta_rel": sub.ruta_rel,
                    "restriccion": restriccion, "valor": e[restriccion],
                }

        if "minLength" in e:
            clave = _id_elemento(sub.definicion, sub.ruta_rel, "minLength", valor=e["minLength"])
            inventario["longitudes"][clave] = {
                "definicion": sub.definicion, "ruta_rel": sub.ruta_rel, "valor": e["minLength"],
            }

        if "pattern" in e:
            clave = _id_elemento(sub.definicion, sub.ruta_rel, "pattern", valor=e["pattern"])
            inventario["patrones"][clave] = {
                "definicion": sub.definicion, "ruta_rel": sub.ruta_rel, "patron": e["pattern"],
            }

        if e.get("type") == "object":
            clave = _id_elemento(sub.definicion, sub.ruta_rel)
            inventario["cerrados"][clave] = {
                "definicion": sub.definicion, "ruta_rel": sub.ruta_rel,
                "cerrado": e.get("additionalProperties", True) is False,
            }

        for i, rama in enumerate(e.get("allOf", [])):
            if "if" in rama and "then" in rama:
                clave = _id_elemento(sub.definicion, sub.ruta_rel, f"acoplamiento[{i}]")
                inventario["acoplamientos"][clave] = {
                    "definicion": sub.definicion, "ruta_rel": sub.ruta_rel,
                    "condicion": rama["if"], "consecuencia": rama["then"],
                }

    for nombre, regla in schema.get("x-derivaciones", {}).get("reglas", {}).items():
        inventario["agregados"][nombre] = {"nombre": nombre, "regla": regla}

    for propiedad in schema.get("x-simultaneas", {}).get("propiedades", []):
        inventario["simultaneas"][propiedad["ruta"]] = {"ruta": propiedad["ruta"]}

    return inventario


def _vocabulario_cerrado(esquema: dict, schema: dict) -> list | None:
    """Los valores de un vocabulario cerrado, o None si el sub-esquema no declara uno.

    Cuenta como vocabulario cerrado el `enum` directo y también la unión cuyas ramas son todas
    `enum` o `pattern` —que es como se escribe una forma parametrizada como `enum:<nombre>`—.
    Una unión de tipos (cadena o entero) no lo es: no enumera valores."""
    if "enum" in esquema:
        return list(esquema["enum"])
    ramas = esquema.get("oneOf")
    if not ramas or len(esquema.keys() - {"oneOf", "description", "title"}) > 0:
        return None
    valores: list = []
    for rama in ramas:
        objetivo = rama
        if "$ref" in rama:
            nombre = rama["$ref"][len("#/$defs/"):]
            objetivo = schema.get("$defs", {}).get(nombre, {})
        if "enum" in objetivo:
            valores.extend(objetivo["enum"])
        elif "pattern" in objetivo:
            valores.append(f"patron:{objetivo['pattern']}")
        else:
            return None
    return valores


def inventario_a_congelable(inventario: dict[str, dict[str, dict]]) -> dict[str, tuple[str, ...]]:
    return {dim: tuple(sorted(elementos)) for dim, elementos in inventario.items()}


# ---------------------------------------------------------------------------------------------
# Auto-consistencia del schema. Un schema que se contradice a sí mismo produce una validación que
# parece rigurosa y no lo es.
# ---------------------------------------------------------------------------------------------

def verificar_schema(schema: dict) -> list[str]:
    problemas: list[str] = []
    subs = _todos_los_subesquemas(schema)

    version = schema.get("x-version")
    declarada = schema.get("properties", {}).get("version_schema", {}).get("const")
    if not version:
        problemas.append("el schema no declara `x-version`: un schema sin versión no es versionado")
    elif version != declarada:
        problemas.append(f"`x-version` ({version!r}) no coincide con la constante que la matriz debe declarar ({declarada!r})")

    definiciones = set(schema.get("$defs", {}))
    referenciadas: set[str] = set()
    for sub in subs:
        for clave in sub.esquema:
            if clave not in PALABRAS_SOPORTADAS and clave not in PALABRAS_IGNORADAS and not clave.startswith("x-"):
                problemas.append(f"{_puntero(sub.puntero)}: palabra clave `{clave}` que el validador no implementa")
        ref = sub.esquema.get("$ref")
        if ref:
            if not ref.startswith("#/$defs/") or ref[len("#/$defs/"):] not in definiciones:
                problemas.append(f"{_puntero(sub.puntero)}: `$ref` que no resuelve: {ref}")
            else:
                referenciadas.add(ref[len("#/$defs/"):])
        if sub.esquema.get("type") == "object" and sub.esquema.get("additionalProperties", True) is not False:
            problemas.append(f"{_puntero(sub.puntero)}: objeto sin `additionalProperties: false` — el schema deja de ser cerrado ahí")

    for muerta in sorted(definiciones - referenciadas):
        problemas.append(f"`$defs/{muerta}` no la referencia nadie: una definición inalcanzable no se puede ejercer ni mutar")

    reglas = schema.get("x-derivaciones", {}).get("reglas", {})
    if not reglas:
        problemas.append("el schema no declara reglas de derivación para sus valores agregados")
    for nombre, regla in reglas.items():
        nodo = regla.get("nodo")
        definicion = schema.get("$defs", {}).get(nodo)
        if definicion is None:
            problemas.append(f"derivación `{nombre}`: su nodo `{nodo}` no es una definición del schema")
        elif nombre not in definicion.get("properties", {}):
            problemas.append(f"derivación `{nombre}`: el nodo `{nodo}` no declara esa propiedad")
        if regla.get("regla") not in REGLAS_DE_DERIVACION:
            problemas.append(f"derivación `{nombre}`: regla desconocida {regla.get('regla')!r}")
        if (regla.get("regla") == "valor_comun_o_marca_de_discrepancia") != ("marca_de_discrepancia" in regla):
            problemas.append(f"derivación `{nombre}`: la marca de discrepancia y la regla que la usa tienen que ir juntas")
        entradas = regla.get("entradas") or []
        if not entradas:
            problemas.append(f"derivación `{nombre}`: sin entradas, no hay de qué derivar")
        for entrada in entradas:
            for tramo in entrada.replace("[]", "").split("."):
                if tramo in reglas:
                    problemas.append(
                        f"derivación `{nombre}`: declara el agregado `{tramo}` como entrada. "
                        "Una derivación que se alimenta de otra derivación deja de tener una hoja anclada abajo."
                    )

    for propiedad in schema.get("x-simultaneas", {}).get("propiedades", []):
        ruta = propiedad.get("ruta", "")
        localizado = _localizar(schema, ruta)
        if localizado is None:
            problemas.append(f"propiedad simultánea `{ruta}`: no resuelve contra el schema")
        elif localizado[1].get("type") != "array":
            problemas.append(f"propiedad simultánea `{ruta}`: no está declarada como arreglo, o sea que está declarada como valor único")

    return problemas


def _puntero(puntero: tuple) -> str:
    return "#/" + "/".join(str(t) for t in puntero) if puntero else "#"


def _localizar(schema: dict, ruta: str) -> tuple[tuple, dict] | None:
    """Resuelve `<definicion>.<campo>.<campo>` cruzando `$ref`. Devuelve puntero y sub-esquema."""
    tramos = ruta.split(".")
    nombre, resto = tramos[0], tramos[1:]
    if nombre == "raiz":
        puntero: tuple = ()
        actual = schema
    else:
        if nombre not in schema.get("$defs", {}):
            return None
        puntero = ("$defs", nombre)
        actual = schema["$defs"][nombre]
    for tramo in resto:
        while "$ref" in actual:
            nombre_ref = actual["$ref"][len("#/$defs/"):]
            if nombre_ref not in schema.get("$defs", {}):
                return None
            puntero = ("$defs", nombre_ref)
            actual = schema["$defs"][nombre_ref]
        siguiente = actual.get("properties", {}).get(tramo)
        if siguiente is not None:
            puntero, actual = puntero + ("properties", tramo), siguiente
            continue
        for i, rama in enumerate(actual.get("allOf", [])):
            candidato = rama.get("then", {}).get("properties", {}).get(tramo)
            if candidato is not None:
                puntero, actual = puntero + ("allOf", i, "then", "properties", tramo), candidato
                break
        else:
            return None
    while "$ref" in actual:
        nombre_ref = actual["$ref"][len("#/$defs/"):]
        if nombre_ref not in schema.get("$defs", {}):
            return None
        puntero = ("$defs", nombre_ref)
        actual = schema["$defs"][nombre_ref]
    return puntero, actual


# ---------------------------------------------------------------------------------------------
# Reglas de derivación aplicadas a una matriz concreta.
# ---------------------------------------------------------------------------------------------

def verificar_agregados(matriz: Any, schema: dict) -> list[Error]:
    errores: list[Error] = []
    reglas = schema.get("x-derivaciones", {}).get("reglas", {})
    if not isinstance(matriz, dict):
        return errores
    for i, punto in enumerate(matriz.get("puntos", []) or []):
        if not isinstance(punto, dict):
            continue
        for nombre, regla in reglas.items():
            if regla.get("nodo") != "punto" or nombre not in punto:
                continue
            entradas: list = []
            for expresion in regla.get("entradas", []):
                entradas.extend(_resolver_expresion(punto, expresion))
            ruta = ("puntos", i, nombre)
            if not entradas:
                errores.append(Error(ruta, "el agregado no tiene ninguna hoja que lo alimente: no hay de qué derivarlo"))
                continue
            esperado = _aplicar_regla(regla, entradas)
            if not _mismo(punto[nombre], esperado):
                errores.append(Error(
                    ruta,
                    f"agregado derivado: sus entradas producen {esperado!r} y está declarado {punto[nombre]!r}",
                ))
    return errores


def _resolver_expresion(nodo: Any, expresion: str) -> list:
    """Resuelve `a[].b.c` sobre un nodo. `[]` itera el arreglo de esa clave."""
    actuales: list = [nodo]
    for tramo in expresion.split("."):
        itera = tramo.endswith("[]")
        clave = tramo[:-2] if itera else tramo
        siguientes: list = []
        for actual in actuales:
            if not isinstance(actual, dict) or clave not in actual:
                continue
            valor = actual[clave]
            if itera:
                if isinstance(valor, list):
                    siguientes.extend(valor)
            else:
                siguientes.append(valor)
        actuales = siguientes
    return actuales


def _aplicar_regla(regla: dict, entradas: list) -> Any:
    if regla["regla"] == "conjunto_ordenado":
        return sorted({json.dumps(e, sort_keys=True, ensure_ascii=False): e for e in entradas}.values(),
                      key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False))
    unicos = {json.dumps(e, sort_keys=True, ensure_ascii=False): e for e in entradas}
    if len(unicos) == 1:
        return next(iter(unicos.values()))
    return regla["marca_de_discrepancia"]


# ---------------------------------------------------------------------------------------------
# Modo `--schema`.
# ---------------------------------------------------------------------------------------------

def _cargar_json(ruta: Path) -> tuple[Any, str | None]:
    if not ruta.is_file():
        return None, f"no existe el archivo {ruta.relative_to(REPO) if ruta.is_relative_to(REPO) else ruta}"
    try:
        return json.loads(ruta.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as e:
        return None, f"JSON inválido en {ruta.name}: {e}"


def modo_schema(ruta_matriz: Path) -> int:
    schema, error = _cargar_json(RUTA_SCHEMA)
    if error:
        print(f"FALLA  schema: {error}")
        return 1

    problemas = verificar_schema(schema)
    if problemas:
        print(f"FALLA  auto-consistencia del schema — {len(problemas)} problemas:")
        for p in problemas:
            print(f"       - {p}")
        return 1
    print(f"OK     auto-consistencia del schema (versión {schema.get('x-version')})")

    matriz, error = _cargar_json(ruta_matriz)
    if error:
        print(f"FALLA  matriz: {error}")
        return 1

    errores, _ = validar(matriz, schema)
    errores.extend(verificar_agregados(matriz, schema))
    if errores:
        print(f"FALLA  {ruta_matriz.name} contra el schema — {len(errores)} errores:")
        for e in errores[:20]:
            print(f"       - {e}")
        if len(errores) > 20:
            print(f"       ... y {len(errores) - 20} más")
        return 1

    puntos = len(matriz.get("puntos", []) or [])
    print(f"OK     {ruta_matriz.name}: {puntos} "
          f"{'punto válido' if puntos == 1 else 'puntos válidos'} contra el schema, con sus agregados derivados")
    print()
    print("RESULTADO: OK")
    return 0


# ---------------------------------------------------------------------------------------------
# Modo `--autotest-schema`.
# ---------------------------------------------------------------------------------------------

class Mutante(NamedTuple):
    dimension: str
    elemento: str
    descripcion: str
    clase: str                  # "instancia" | "schema_autocheck"
    fixture: str | None
    matriz: Any | None
    schema: Any | None
    ruta_esperada: Ruta | None


def _obtener(datos: Any, ruta: Ruta) -> Any:
    actual = datos
    for tramo in ruta:
        if isinstance(tramo, int):
            if not isinstance(actual, list) or tramo >= len(actual):
                raise KeyError(ruta)
            actual = actual[tramo]
        else:
            if not isinstance(actual, dict) or tramo not in actual:
                raise KeyError(ruta)
            actual = actual[tramo]
    return actual


def _asignar(datos: Any, ruta: Ruta, valor: Any) -> None:
    padre = _obtener(datos, ruta[:-1])
    padre[ruta[-1]] = valor


def _borrar(datos: Any, ruta: Ruta) -> None:
    padre = _obtener(datos, ruta[:-1])
    del padre[ruta[-1]]


def _expandir(datos: Any, base: Ruta, ruta_rel: Ruta) -> list[Ruta]:
    """Rutas concretas de instancia: cada `[]` del recorrido del schema se expande a los índices
    que el fixture realmente tiene. Resolverlo siempre al índice 0 dejaría sin mutar todo lo que
    vive en la segunda posición de un arreglo."""
    rutas = [base]
    for tramo in ruta_rel:
        siguientes: list[Ruta] = []
        for ruta in rutas:
            if tramo == "[]":
                try:
                    arreglo = _obtener(datos, ruta)
                except (KeyError, IndexError):
                    continue
                if isinstance(arreglo, list):
                    siguientes.extend(ruta + (i,) for i in range(len(arreglo)))
            else:
                siguientes.append(ruta + (tramo,))
        rutas = siguientes
    return rutas


def _mapa_de_instancias(corpus: dict[str, Any], schema: dict) -> tuple[dict[str, list[tuple[str, Ruta]]], list[str]]:
    """def → [(fixture, ruta)] para todo lo que el corpus conforme instancia."""
    mapa: dict[str, list[tuple[str, Ruta]]] = {}
    fallos: list[str] = []
    for nombre, datos in corpus.items():
        errores, ctx = validar(datos, schema)
        if errores:
            fallos.append(f"{nombre}: {len(errores)} errores — " + "; ".join(str(e) for e in errores[:3]))
            continue
        for definicion, ruta in ctx.instancias:
            mapa.setdefault(definicion, []).append((nombre, ruta))
    return mapa, fallos


def _candidatos(mapa: dict[str, list[tuple[str, Ruta]]], definicion: str) -> list[tuple[str, Ruta]]:
    return mapa.get(definicion, [])


def _generar_mutantes(
    schema: dict,
    inventario: dict[str, dict[str, dict]],
    corpus: dict[str, Any],
    mapa: dict[str, list[tuple[str, Ruta]]],
) -> tuple[list[Mutante], list[str]]:
    """Un mutante por elemento del inventario. Si un elemento no tiene ninguna instancia en el
    corpus que lo ejerza, no se inventa: se reporta como hueco, que es un rojo distinto."""
    mutantes: list[Mutante] = []
    huecos: list[str] = []

    def instanciar(definicion: str, ruta_rel: Ruta, transformar) -> bool:
        """Prueba cada instancia de `definicion` hasta que la transformación se pueda aplicar."""
        for fixture, base in _candidatos(mapa, definicion):
            for ruta in _expandir(corpus[fixture], base, ruta_rel):
                datos = copy.deepcopy(corpus[fixture])
                try:
                    resultado = transformar(datos, ruta, fixture)
                except (KeyError, IndexError, TypeError):
                    continue
                if resultado:
                    return True
        return False

    # --- campos obligatorios: la matriz sin ese campo tiene que ser rechazada ---
    for elemento, detalle in sorted(inventario["obligatorios"].items()):
        def quitar(datos, ruta, fixture, elemento=elemento, detalle=detalle):
            objetivo = ruta + (detalle["campo"],)
            _obtener(datos, objetivo)
            _borrar(datos, objetivo)
            mutantes.append(Mutante(
                "obligatorios", elemento, f"se quita `{detalle['campo']}` de `{detalle['definicion']}`",
                "instancia", fixture, datos, None, objetivo,
            ))
            return True
        if not instanciar(detalle["definicion"], detalle["ruta_rel"], quitar):
            huecos.append(f"obligatorios/{elemento}: ningún fixture conforme instancia `{detalle['definicion']}` con ese campo")

    # --- vocabularios cerrados: un valor fuera del vocabulario tiene que ser rechazado ---
    for elemento, detalle in sorted(inventario["vocabularios"].items()):
        def fuera(datos, ruta, fixture, elemento=elemento):
            _obtener(datos, ruta)
            _asignar(datos, ruta, CENTINELA_VOCABULARIO)
            mutantes.append(Mutante(
                "vocabularios", elemento, "se sustituye el valor por uno fuera del vocabulario",
                "instancia", fixture, datos, None, ruta,
            ))
            return True
        if not instanciar(detalle["definicion"], detalle["ruta_rel"], fuera):
            huecos.append(f"vocabularios/{elemento}: ningún fixture conforme lo ejerce")

    # --- constantes: cambiarlas tiene que ser rechazado ---
    for elemento, detalle in sorted(inventario["constantes"].items()):
        def cambiar(datos, ruta, fixture, elemento=elemento, detalle=detalle):
            if not _mismo(_obtener(datos, ruta), detalle["valor"]):
                return False
            _asignar(datos, ruta, CENTINELA_CONSTANTE)
            mutantes.append(Mutante(
                "constantes", elemento, f"se cambia la constante {detalle['valor']!r}",
                "instancia", fixture, datos, None, ruta,
            ))
            return True
        if not instanciar(detalle["definicion"], detalle["ruta_rel"], cambiar):
            huecos.append(f"constantes/{elemento}: ningún fixture conforme la ejerce")

    # --- objetos cerrados: una propiedad no declarada tiene que ser rechazada ---
    for elemento, detalle in sorted(inventario["cerrados"].items()):
        def agregar(datos, ruta, fixture, elemento=elemento):
            objetivo = _obtener(datos, ruta)
            if not isinstance(objetivo, dict):
                return False
            objetivo[CENTINELA_PROPIEDAD] = True
            mutantes.append(Mutante(
                "cerrados", elemento, "se agrega una propiedad no declarada",
                "instancia", fixture, datos, None, ruta + (CENTINELA_PROPIEDAD,),
            ))
            return True
        if not instanciar(detalle["definicion"], detalle["ruta_rel"], agregar):
            huecos.append(f"cerrados/{elemento}: ningún fixture conforme lo instancia")

    # --- restricciones de arreglo: menos elementos de los declarados, o repetidos ---
    for elemento, detalle in sorted(inventario["restricciones_de_arreglo"].items()):
        def restringir(datos, ruta, fixture, elemento=elemento, detalle=detalle):
            arreglo = _obtener(datos, ruta)
            if not isinstance(arreglo, list):
                return False
            if detalle["restriccion"] == "minItems":
                objetivo = detalle["valor"] - 1
                if len(arreglo) < detalle["valor"]:
                    return False
                nuevo = arreglo[:objetivo]
                descripcion = f"el arreglo baja a {objetivo} elementos y `minItems` es {detalle['valor']}"
            else:
                if not arreglo:
                    return False
                nuevo = [arreglo[0], *arreglo]
                descripcion = "se repite un elemento en un arreglo con `uniqueItems`"
            _asignar(datos, ruta, nuevo)
            mutantes.append(Mutante(
                "restricciones_de_arreglo", elemento, descripcion, "instancia", fixture, datos, None, ruta,
            ))
            return True
        if not instanciar(detalle["definicion"], detalle["ruta_rel"], restringir):
            huecos.append(f"restricciones_de_arreglo/{elemento}: ningún fixture conforme lo ejerce")

    # --- mínimos y máximos: el valor justo afuera del rango tiene que ser rechazado ---
    for elemento, detalle in sorted(inventario["restricciones_numericas"].items()):
        def numerica(datos, ruta, fixture, elemento=elemento, detalle=detalle):
            actual = _obtener(datos, ruta)
            if not isinstance(actual, int) or isinstance(actual, bool):
                return False
            nuevo = detalle["valor"] - 1 if detalle["restriccion"] == "minimum" else detalle["valor"] + 1
            _asignar(datos, ruta, nuevo)
            mutantes.append(Mutante(
                "restricciones_numericas", elemento,
                f"el valor pasa a {nuevo}, fuera del `{detalle['restriccion']}` declarado ({detalle['valor']})",
                "instancia", fixture, datos, None, ruta,
            ))
            return True
        if not instanciar(detalle["definicion"], detalle["ruta_rel"], numerica):
            huecos.append(f"restricciones_numericas/{elemento}: ningún fixture conforme lo ejerce")

    # --- longitudes mínimas: la cadena vacía no es un valor declarado ---
    for elemento, detalle in sorted(inventario["longitudes"].items()):
        def acortar(datos, ruta, fixture, elemento=elemento, detalle=detalle):
            if not isinstance(_obtener(datos, ruta), str):
                return False
            _asignar(datos, ruta, "x" * (detalle["valor"] - 1))
            mutantes.append(Mutante(
                "longitudes", elemento,
                f"la cadena baja a {detalle['valor'] - 1} caracteres y `minLength` es {detalle['valor']}",
                "instancia", fixture, datos, None, ruta,
            ))
            return True
        if not instanciar(detalle["definicion"], detalle["ruta_rel"], acortar):
            huecos.append(f"longitudes/{elemento}: ningún fixture conforme lo ejerce")

    # --- patrones: una cadena que no casa tiene que ser rechazada ---
    for elemento, detalle in sorted(inventario["patrones"].items()):
        def descasar(datos, ruta, fixture, elemento=elemento, detalle=detalle):
            if not isinstance(_obtener(datos, ruta), str):
                return False
            if re.search(detalle["patron"], CENTINELA_PATRON) is not None:
                return False  # el centinela casaría: no probaría nada
            _asignar(datos, ruta, CENTINELA_PATRON)
            mutantes.append(Mutante(
                "patrones", elemento, f"la cadena deja de casar con {detalle['patron']!r}",
                "instancia", fixture, datos, None, ruta,
            ))
            return True
        if not instanciar(detalle["definicion"], detalle["ruta_rel"], descasar):
            huecos.append(f"patrones/{elemento}: ningún fixture conforme lo ejerce")

    # --- acoplamientos: la condición se cumple y la consecuencia se rompe ---
    for elemento, detalle in sorted(inventario["acoplamientos"].items()):
        mutante = _mutante_de_acoplamiento(elemento, detalle, corpus, mapa, schema)
        if mutante is None:
            huecos.append(f"acoplamientos/{elemento}: el corpus no tiene un donante con el discriminador distinto")
        else:
            mutantes.append(mutante)

    # --- propiedades simultáneas: colapsarlas a un escalar tiene que ser rechazado ---
    for elemento, detalle in sorted(inventario["simultaneas"].items()):
        mutante = _mutante_de_simultanea(elemento, schema, corpus, mapa)
        if mutante is None:
            huecos.append(f"simultaneas/{elemento}: ningún fixture conforme la instancia")
        else:
            mutantes.append(mutante)

    # --- agregados: dos mutantes por elemento, uno en cada dirección ---
    for elemento, detalle in sorted(inventario["agregados"].items()):
        instancia = _mutante_de_agregado(elemento, detalle, corpus, mapa)
        if instancia is None:
            huecos.append(f"agregados/{elemento}: ningún fixture conforme lo declara")
        else:
            mutantes.append(instancia)
        mutantes.append(_mutante_de_derivacion_circular(elemento, schema, inventario))

    # --- categórico: la jerarquía aplanada ---
    plana = _mutante_de_jerarquia_plana(corpus, mapa)
    if plana is None:
        huecos.append("jerarquia_plana: ningún fixture conforme tiene un punto con trabajos delegados")
    else:
        mutantes.append(plana)

    return mutantes, huecos


def _mutante_de_acoplamiento(elemento, detalle, corpus, mapa, schema) -> Mutante | None:
    """El acoplamiento se rompe injertando, en una instancia que cumple la condición, el valor que
    otra instancia usa para la forma contraria. Es el único mutante que la unión sola no caza: el
    valor injertado es válido para su propia forma y lo que falla es la correspondencia."""
    condicion, consecuencia = detalle["condicion"], detalle["consecuencia"]
    propiedades = list(consecuencia.get("properties", {}))
    if len(propiedades) != 1:
        return None
    campo = propiedades[0]
    discriminadores = list(condicion.get("properties", {}))
    if len(discriminadores) != 1:
        return None
    discriminador = discriminadores[0]
    admitidos = condicion["properties"][discriminador]
    esperados = [admitidos["const"]] if "const" in admitidos else list(admitidos.get("enum", []))
    if not esperados:
        return None

    candidatos = _candidatos(mapa, detalle["definicion"])
    receptor = donante = None
    for fixture, ruta in candidatos:
        try:
            nodo = _obtener(corpus[fixture], ruta)
        except (KeyError, IndexError):
            continue
        if not isinstance(nodo, dict) or discriminador not in nodo or campo not in nodo:
            continue
        if any(_mismo(nodo[discriminador], v) for v in esperados):
            receptor = receptor or (fixture, ruta, nodo)
        else:
            donante = donante or (fixture, ruta, nodo)
    if receptor is None or donante is None:
        return None

    fixture, ruta, _ = receptor
    datos = copy.deepcopy(corpus[fixture])
    _asignar(datos, ruta + (campo,), copy.deepcopy(donante[2][campo]))
    return Mutante(
        "acoplamientos", elemento,
        f"`{discriminador}` sigue en {esperados[0]!r} y `{campo}` pasa a la forma de otro tipo",
        "instancia", fixture, datos, None, ruta + (campo,),
    )


def _mutante_de_simultanea(elemento, schema, corpus, mapa) -> Mutante | None:
    tramos = elemento.split(".")
    definicion, ruta_rel = tramos[0], tuple(tramos[1:])
    for fixture, base in _candidatos(mapa, definicion):
        ruta = base + ruta_rel
        try:
            arreglo = _obtener(corpus[fixture], ruta)
        except (KeyError, IndexError):
            continue
        if not isinstance(arreglo, list) or not arreglo:
            continue
        datos = copy.deepcopy(corpus[fixture])
        _asignar(datos, ruta, arreglo[0])
        return Mutante(
            "simultaneas", elemento, "la propiedad simultánea se colapsa a un valor único",
            "instancia", fixture, datos, None, ruta,
        )
    return None


def _mutante_de_agregado(elemento, detalle, corpus, mapa) -> Mutante | None:
    regla = detalle["regla"]
    for fixture, base in _candidatos(mapa, regla.get("nodo", "")):
        ruta = base + (elemento,)
        try:
            declarado = _obtener(corpus[fixture], ruta)
        except (KeyError, IndexError):
            continue
        entradas: list = []
        nodo = _obtener(corpus[fixture], base)
        for expresion in regla.get("entradas", []):
            entradas.extend(_resolver_expresion(nodo, expresion))
        alternativo = _valor_alternativo(declarado, entradas, regla)
        if alternativo is None:
            continue
        datos = copy.deepcopy(corpus[fixture])
        _asignar(datos, ruta, alternativo)
        return Mutante(
            "agregados", elemento,
            f"el agregado declara {alternativo!r} cuando sus entradas producen {declarado!r}",
            "instancia", fixture, datos, None, ruta,
        )
    return None


def _valor_alternativo(declarado: Any, entradas: list, regla: dict) -> Any:
    """Otro valor que el schema acepte pero que la derivación no produzca: el mutante tiene que
    caer por la regla de derivación y no por el tipo, o no prueba la derivación."""
    if isinstance(declarado, list):
        if len(declarado) > 1:
            return declarado[:1]
        distintos = [e for e in entradas if not _mismo(e, declarado[0])]
        return None if not distintos else [*declarado, distintos[0]]
    marca = regla.get("marca_de_discrepancia")
    if marca is not None and not _mismo(declarado, marca):
        return marca
    distintos = [e for e in entradas if not _mismo(e, declarado)]
    return distintos[0] if distintos else None


def _mutante_de_derivacion_circular(elemento, schema, inventario) -> Mutante:
    """El otro lado del mismo elemento: no que la matriz mienta sobre el agregado, sino que el
    schema declare el agregado como entrada de una derivación."""
    mutado = copy.deepcopy(schema)
    otros = [n for n in inventario["agregados"] if n != elemento] or [elemento]
    mutado["x-derivaciones"]["reglas"][elemento]["entradas"] = [f"{otros[0]}.valor"]
    return Mutante(
        "agregados", f"{elemento}:derivacion_circular",
        f"la derivación de `{elemento}` declara el agregado `{otros[0]}` como entrada",
        "schema_autocheck", None, None, mutado, None,
    )


def _mutante_de_jerarquia_plana(corpus, mapa) -> Mutante | None:
    for fixture, base in _candidatos(mapa, "punto"):
        datos = copy.deepcopy(corpus[fixture])
        try:
            punto = _obtener(datos, base)
        except (KeyError, IndexError):
            continue
        trabajos = punto.get("trabajos_delegados")
        if not trabajos:
            continue
        intento = trabajos[0]["intentos"][0]
        punto["transporte"] = intento["transporte"]
        punto["deadline_declarado"] = intento["deadline_declarado"]
        punto["familia"] = trabajos[0]["familia"]
        del punto["trabajos_delegados"]
        return Mutante(
            "jerarquia_plana", "punto.trabajos_delegados",
            "los campos del intento y del trabajo delegado se suben al punto y la jerarquía desaparece",
            "instancia", fixture, datos, None, base + ("trabajos_delegados",),
        )
    return None


def _rechaza_en_ruta(errores: list[Error], ruta: Ruta | None) -> bool:
    """Un mutante caza si el rechazo ocurre en la ruta mutada o dentro de ella. Sin esta
    atribución, un mutante cazado por una regla ajena se reporta como cobertura que no existe."""
    if ruta is None:
        return bool(errores)
    return any(e.ruta[:len(ruta)] == ruta or ruta[:len(e.ruta)] == e.ruta for e in errores)


def modo_autotest() -> int:
    schema, error = _cargar_json(RUTA_SCHEMA)
    if error:
        print(f"[A] FALLA  {error}")
        return 1

    resultados: list[tuple[str, bool, str]] = []

    problemas = verificar_schema(schema)
    resultados.append((
        "B", not problemas,
        "auto-consistencia del schema" if not problemas
        else f"auto-consistencia del schema — {len(problemas)}: " + " | ".join(problemas[:4]),
    ))

    inventario = derivar_inventario(schema)
    derivado = inventario_a_congelable(inventario)
    diferencias: list[str] = []
    for dimension in sorted(set(derivado) | set(INVENTARIO_CONGELADO)):
        esperado = set(INVENTARIO_CONGELADO.get(dimension, ()))
        real = set(derivado.get(dimension, ()))
        for nuevo in sorted(real - esperado):
            diferencias.append(f"{dimension}: `{nuevo}` está en el schema y no en el inventario congelado")
        for perdido in sorted(esperado - real):
            diferencias.append(f"{dimension}: `{perdido}` está congelado y ya no está en el schema")
    total_elementos = sum(len(v) for v in derivado.values())
    resultados.append((
        "A", not diferencias,
        f"inventario congelado == derivado ({total_elementos} elementos en {len(derivado)} dimensiones)"
        if not diferencias else f"{len(diferencias)} divergencias: " + " | ".join(diferencias[:6]),
    ))

    corpus: dict[str, Any] = {}
    faltantes: list[str] = []
    for nombre in CONFORMES:
        datos, err = _cargar_json(DIR_FIXTURES / nombre)
        if err:
            faltantes.append(err)
        else:
            corpus[nombre] = datos

    mapa, fallos_conformes = _mapa_de_instancias(corpus, schema) if corpus else ({}, [])
    for nombre, datos in corpus.items():
        agregados = verificar_agregados(datos, schema)
        if agregados:
            fallos_conformes.append(f"{nombre}: agregados — " + "; ".join(str(e) for e in agregados[:3]))
    problemas_c = faltantes + fallos_conformes
    resultados.append((
        "C", not problemas_c and len(corpus) == len(CONFORMES),
        f"control positivo: los {len(corpus)} fixtures conformes validan"
        if not problemas_c else "control positivo — " + " | ".join(problemas_c[:4]),
    ))

    definiciones = set(schema.get("$defs", {})) | {"raiz"}
    sin_instanciar = sorted(definiciones - set(mapa))
    sin_ejercer: list[str] = []
    por_definicion = {
        d["definicion"]: d for d in inventario["vocabularios"].values() if not d["ruta_rel"]
    }
    for vocabulario in VOCABULARIOS_CON_COBERTURA_DE_VALOR:
        detalle = por_definicion.get(vocabulario)
        if detalle is None:
            sin_ejercer.append(f"`{vocabulario}` no es un vocabulario del schema")
            continue
        vistos = set()
        for fixture, ruta in _candidatos(mapa, vocabulario):
            try:
                vistos.add(_etiqueta_de_valor(_obtener(corpus[fixture], ruta), detalle["valores"]))
            except (KeyError, IndexError):
                continue
        for valor in detalle["valores"]:
            if valor not in vistos:
                sin_ejercer.append(f"{vocabulario}: el valor `{valor}` no lo ejerce ningún fixture conforme")
    problemas_d = [f"`$defs/{d}` sin instanciar en el corpus conforme" for d in sin_instanciar] + sin_ejercer
    resultados.append((
        "D", not problemas_d,
        f"cobertura: {len(definiciones)} definiciones instanciadas y "
        f"{len(VOCABULARIOS_CON_COBERTURA_DE_VALOR)} vocabularios operacionales ejercidos valor a valor"
        if not problemas_d else f"{len(problemas_d)} huecos: " + " | ".join(problemas_d[:5]),
    ))

    sin_multiplicidad: list[str] = []
    for elemento in sorted(inventario["simultaneas"]):
        tramos = elemento.split(".")
        maximo = 0
        for fixture, base in _candidatos(mapa, tramos[0]):
            try:
                arreglo = _obtener(corpus[fixture], base + tuple(tramos[1:]))
            except (KeyError, IndexError):
                continue
            if isinstance(arreglo, list):
                maximo = max(maximo, len(arreglo))
        if maximo < 2:
            sin_multiplicidad.append(
                f"`{elemento}` nunca aparece con dos valores (máximo visto: {maximo}) — "
                "su mutante de colapso pasaría por vacuidad"
            )
    resultados.append((
        "E", not sin_multiplicidad,
        f"multiplicidad ejercida en las {len(inventario['simultaneas'])} propiedades simultáneas"
        if not sin_multiplicidad else " | ".join(sin_multiplicidad),
    ))

    mutantes, huecos = _generar_mutantes(schema, inventario, corpus, mapa) if mapa else ([], ["sin corpus conforme válido, no se puede generar ningún mutante"])
    sobrevivientes: list[str] = []
    desatribuidos: list[str] = []
    for mutante in mutantes:
        if mutante.clase == "schema_autocheck":
            if not verificar_schema(mutante.schema):
                sobrevivientes.append(f"{mutante.dimension}/{mutante.elemento}: {mutante.descripcion}")
            continue
        errores, _ = validar(mutante.matriz, schema)
        errores.extend(verificar_agregados(mutante.matriz, schema))
        if not errores:
            sobrevivientes.append(f"{mutante.dimension}/{mutante.elemento}: {mutante.descripcion}")
        elif not _rechaza_en_ruta(errores, mutante.ruta_esperada):
            desatribuidos.append(
                f"{mutante.dimension}/{mutante.elemento}: rechazado, pero no en {fmt(mutante.ruta_esperada)} "
                f"(primero: {errores[0]})"
            )
    problemas_f = huecos + [f"SOBREVIVE {s}" for s in sobrevivientes] + [f"SIN ATRIBUIR {d}" for d in desatribuidos]
    resultados.append((
        "F", not problemas_f,
        f"{len(mutantes)} mutantes generados, uno por elemento del inventario, y los {len(mutantes)} rechazados en su ruta"
        if not problemas_f else f"{len(problemas_f)} problemas: " + " | ".join(problemas_f[:6]),
    ))

    orden = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}
    ok_total = True
    for identificador, ok, mensaje in sorted(resultados, key=lambda r: orden[r[0]]):
        ok_total = ok_total and ok
        print(f"[{identificador}] {'OK   ' if ok else 'FALLA'} {mensaje}")
    print()
    if ok_total:
        print("RESULTADO: OK — el schema acepta lo conforme y rechaza el inventario completo de mutantes")
        return 0
    print("RESULTADO: FALLA — ver detalle arriba")
    return 1


def _etiqueta_de_valor(valor: Any, vocabulario: list) -> Any:
    """Un valor de un vocabulario parametrizado (`enum:<nombre>`) se reporta por su patrón, que es
    el token que el vocabulario declara."""
    for token in vocabulario:
        if isinstance(token, str) and token.startswith("patron:"):
            if isinstance(valor, str) and re.search(token[len("patron:"):], valor):
                return token
    return valor


# ---------------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verifica la matriz de despachos contra su schema cerrado.",
        add_help=True,
    )
    parser.add_argument(
        "--schema", nargs="?", const=str(RUTA_MATRIZ), metavar="RUTA",
        help="valida una matriz contra el schema (por defecto scripts/matriz-despachos.json)",
    )
    parser.add_argument(
        "--autotest-schema", action="store_true",
        help="control positivo y negativo del modo --schema sobre los fixtures sintéticos",
    )
    args = parser.parse_args(argv)

    if bool(args.schema) == bool(args.autotest_schema):
        print("Invocación inválida: exactamente uno de --schema o --autotest-schema.", file=sys.stderr)
        return 2
    if args.autotest_schema:
        return modo_autotest()
    return modo_schema(Path(args.schema))


if __name__ == "__main__":
    sys.exit(main())
