#!/usr/bin/env python3
"""Verifica la matriz de despachos contra su schema cerrado.

Diecisiete modos, y por ahora solo diecisiete: los demás del catálogo los construyen otras tasks.

- `--schema [ruta]` — valida la matriz (por defecto `scripts/matriz-despachos.json`) contra
  `scripts/matriz-despachos.schema.json`. Comprueba tres cosas y no una: que el schema sea
  consistente consigo mismo, que la instancia lo satisfaga, y que los valores agregados coincidan
  con lo que sus reglas de derivación producen a partir de las hojas que los alimentan.
- `--autotest-schema` — control positivo y negativo del modo anterior sobre el corpus sintético de
  `scripts/fixtures-matriz/`.
- `--nombres-reservados [ruta]` — valida la lista de nombres reservados al contenedor de perfiles
  de ejecución (por defecto `scripts/nombres-reservados-perfil.json`): que sea estructuralmente
  válida, que cada nombre lleve su motivo, que describa el contenedor entero y que ningún nombre
  admitido abra un hueco.
- `--autotest-nombres-reservados` — control positivo y negativo del modo anterior sobre la lista
  real y sobre mutantes generados a partir de ella.
- `--correspondencia [ruta]` — compara la matriz contra el **inventario vigente** de puntos de
  despacho, que se deriva de la sección «Corridas delegadas en vuelo» de cada `SKILL.md` del árbol
  (`--arbol`, por defecto este repositorio). Reusa la primitiva de biyección de
  `verificar-sobre-en-vuelo.py` en vez de escribir una propia.
- `--autotest-correspondencia` — control positivo y negativo del modo anterior sobre el fixture
  sintético de `scripts/fixtures-matriz/inventario/`.
- `--completitud [ruta]` — un ancla de invocación propia por punto, los trece, y aparte el detector
  de sitios de despacho no inventariados. Cuando el detector no puede ser completo lo declara como
  adjudicación humana con su motivo, y esa declaración **no** sustituye a las anclas. Con `--salida`
  escribe el recibo que consume el documento de contrato.
- `--autotest-completitud` — control positivo y negativo del modo anterior sobre el mismo fixture.
- `--procedencia [ruta]` — recorre **todas las rutas hoja derivadas del schema** y exige exactamente
  una procedencia por cada una: la forma anclada o la marca de ausencia, y la marca solo donde el
  schema la admite. Informa cuántas hojas quedan sin sede.
- `--autotest-procedencia` — control positivo y negativo del modo anterior sobre el fixture
  sintético de `scripts/fixtures-matriz/anclas/`.
- `--anclas [ruta]` — el **resolutor tipado**: ejecuta cada procedencia anclada contra su sede con
  el pipeline que el schema congela y coteja el valor resuelto contra el declarado. Con `--raiz`,
  la raíz contra la que se interpretan las sedes.
- `--autotest-anclas` — control positivo y negativo de `--anclas` **y** de
  `--presupuesto-contractual` sobre el mismo fixture: dos modos, un control positivo cada uno.
- `--presupuesto-contractual [ruta]` — el presupuesto de espera contractual de cada punto: que el
  campo esté (la ausencia de la hoja entera no es una hoja sin sede), que lleve sede y que su valor
  sea el que la sede dice.
- `--condiciones [ruta]` — parsea la condición de existencia de cada punto **como árbol** —los
  conectores son estructura, los átomos son hojas— y la evalúa contra los escenarios de
  configuración y capacidad de `--escenarios` (por defecto, el archivo hermano de la matriz con el
  sufijo `-escenarios`). Cada escenario tiene que producir el conjunto de puntos activos que
  declara, y **ninguno puede producirlos todos**: los modos de implementación mutuamente
  excluyentes dejarían de serlo.
- `--autotest-condiciones` — control positivo y negativo del modo anterior sobre el corpus sintético
  de `scripts/fixtures-matriz/condiciones/`, con una familia de mutantes **derivada por átomo**.
- `--cobertura-condiciones [ruta]` — la otra mitad de AC-9, que es un criterio distinto: que los
  escenarios ejerzan **cada rama de cada condición y cada valor declarado de cada átomo**. Evaluar
  bien y cubrir del todo no se implican: una rama que ningún escenario ejerce deja el árbol entero
  en verde sin haberse probado.
- `--autotest-cobertura-condiciones` — control positivo y negativo del modo anterior, con tres
  familias derivadas: una por escenario, una por valor de átomo y una **por exclusión** —al
  eliminar una exclusión de una condición, algún escenario pasa a fallar—.

Tres reglas de diseño:

1. **Sin dependencias.** No hay `jsonschema` en esta máquina y el repo solo usa stdlib + PyYAML.
   El validador de acá cubre el subconjunto que el schema usa y **rechaza cualquier palabra clave
   que no implemente**: una palabra ignorada en silencio es una restricción que el schema declara y
   nadie aplica, o sea una guarda que no puede ponerse roja.
2. **El inventario se deriva del schema; lo que se congela es el criterio.** El autotest lee el
   schema y deriva la lista exacta de sus elementos en doce dimensiones —campos obligatorios,
   vocabularios cerrados, constantes, acoplamientos, restricciones de arreglo, mínimos y máximos,
   longitudes, patrones, objetos cerrados, agregados derivados, propiedades simultáneas y pares de
   la tabla de conversión—, y la compara contra `INVENTARIO_CONGELADO`. Divergir es rojo: un
   elemento nuevo en el schema sin su entrada acá nacería sin mutante y nadie lo notaría. **El valor
   va dentro del id del elemento**, no solo su nombre: congelar `enum_transporte` a secas deja pasar
   que alguien le agregue un token, congelar `cardinalidad_exactamente_n.n` a secas deja pasar que
   su mínimo baje de 1 a 0 —que es exactamente lo que el schema declara que no puede ocurrir—, y
   congelar un par de conversión por su texto deja pasar que su token cambie a otro del mismo enum.
   Las dos primeras pasaron al probar este autotest contra sí mismo.
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
                                                  | --nombres-reservados [ruta]
                                                  | --autotest-nombres-reservados
                                                  | --correspondencia [ruta] | --autotest-correspondencia
                                                  | --completitud [ruta] | --autotest-completitud
                                                  | --procedencia [ruta] | --autotest-procedencia
                                                  | --anclas [ruta] | --autotest-anclas
                                                  | --presupuesto-contractual [ruta]
                                                  | --condiciones [ruta] | --autotest-condiciones
                                                  | --cobertura-condiciones [ruta]
                                                  | --autotest-cobertura-condiciones
Exit 0 si el modo pasa, 1 si falla, 2 si la invocación es inválida.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import itertools
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

REPO = Path(__file__).resolve().parent.parent
RUTA_SCHEMA = REPO / "scripts" / "matriz-despachos.schema.json"
RUTA_MATRIZ = REPO / "scripts" / "matriz-despachos.json"
RUTA_NOMBRES_RESERVADOS = REPO / "scripts" / "nombres-reservados-perfil.json"
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
    "conversiones": (
        'autoridad_final."conductor"=conductor',
        'autoridad_final."usuario"=usuario',
        'escritura."crea rama, implementa task por task"=escritor',
        'escritura."escritor"=escritor',
        'escritura."read-only"=read_only',
        'escritura."solo lectura"=read_only',
        'escritura."workspace-write"=escritor',
        'familia."No es cross-model por defecto"=misma_del_conductor',
        'familia."Subagente del entorno"=misma_del_conductor',
        'familia."misma familia"=misma_del_conductor',
        'familia."misma"=misma_del_conductor',
        'familia."mismo modelo"=misma_del_conductor',
        'familia."otra familia"=opuesta_al_conductor',
        'familia."otra"=opuesta_al_conductor',
        'familia."otro modelo"=opuesta_al_conductor',
        'permiso_efectivo."**parado en `<repo>/`**"=workspace_write_acotado',
        'permiso_efectivo."read-only"=read_only',
        'permiso_efectivo."solo lectura"=read_only',
        'permiso_efectivo."workspace-write"=workspace_write_acotado',
        'skill."bitbucket-code-review"=bitbucket-code-review',
        'skill."co-explore"=co-explore',
        'skill."cross-implement"=cross-implement',
        'skill."cross-review"=cross-review',
        'skill."sdd-flow"=sdd-flow',
        'skill."sdd-orchestrator"=sdd-orchestrator',
        'skill."sdd-pr-feedback"=sdd-pr-feedback',
        'transporte."cli-exec"=cli-exec',
        'transporte."cli-resume"=cli-resume',
        'transporte."subagent"=subagent',
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
        "conversiones": {},
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

    for nombre, tabla in schema.get("x-conversiones", {}).get("reglas", {}).items():
        for i, par in enumerate(tabla.get("pares", [])):
            clave = _id_par_de_conversion(nombre, par)
            inventario["conversiones"][clave] = {
                "tabla": nombre, "indice": i, "enum": tabla.get("enum"),
                "texto": par.get("texto"), "token": par.get("token"),
            }

    return inventario


def _id_par_de_conversion(nombre: str, par: dict) -> str:
    """El id de un par de la tabla de conversión. El texto va entre comillas —contiene espacios,
    comas y backticks— y el token va dentro del id: cambiar cualquiera de los dos es cambiar el par,
    no editarlo."""
    return f"{nombre}.{json.dumps(par.get('texto'), ensure_ascii=False)}={_texto_de_valor(par.get('token'))}"


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

    problemas.extend(_problemas_de_conversiones(schema))

    return problemas


def _problemas_de_conversiones(schema: dict) -> list[str]:
    """Auto-consistencia de la tabla de conversión. `enum:<nombre>` sin tabla nombra un vocabulario
    y no dice cómo se llega a él; una tabla que emite un token fuera de su enum, o que declara dos
    tokens para el mismo texto, produce un resolutor que no puede ser correcto."""
    problemas: list[str] = []
    reglas = schema.get("x-conversiones", {}).get("reglas", {})
    if not reglas:
        problemas.append(
            "el schema admite `conversion: enum:<nombre>` y no declara ninguna tabla de conversión: "
            "el mapeo texto → token quedaría a criterio de quien implemente el resolutor"
        )
    for nombre, tabla in reglas.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", nombre):
            problemas.append(f"tabla de conversión `{nombre}`: su nombre no forma un `enum:<nombre>` que el schema admita")
        objetivo = schema.get("$defs", {}).get(tabla.get("enum"))
        vocabulario = objetivo.get("enum") if isinstance(objetivo, dict) else None
        if not vocabulario:
            problemas.append(f"tabla de conversión `{nombre}`: su enum `{tabla.get('enum')}` no es un vocabulario cerrado del schema")
        pares = tabla.get("pares") or []
        if not pares:
            problemas.append(f"tabla de conversión `{nombre}`: sin pares, no declara ninguna conversión")
        vistos: dict[str, Any] = {}
        producidos: list = []
        for par in pares:
            texto, token = par.get("texto"), par.get("token")
            if not isinstance(texto, str) or not texto:
                problemas.append(f"tabla de conversión `{nombre}`: un par sin texto no se puede cotejar contra nada")
                continue
            if texto in vistos:
                detalle = (
                    f"con dos tokens ({vistos[texto]!r} y {token!r}) — la conversión dejaría de ser determinista"
                    if not _mismo(vistos[texto], token) else "dos veces con el mismo token"
                )
                problemas.append(f"tabla de conversión `{nombre}`: el texto {texto!r} aparece {detalle}")
            vistos[texto] = token
            producidos.append(token)
            if vocabulario and not any(_mismo(token, v) for v in vocabulario):
                problemas.append(
                    f"tabla de conversión `{nombre}`: el texto {texto!r} convierte a {token!r}, "
                    f"que no pertenece al vocabulario de `{tabla.get('enum')}`"
                )
        for valor in vocabulario or []:
            if not any(_mismo(valor, t) for t in producidos):
                problemas.append(
                    f"tabla de conversión `{nombre}`: ningún texto produce el token {valor!r} — "
                    "un token que no se puede emitir desde ninguna sede deja la tabla incompleta o el enum de más"
                )
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

    # --- tabla de conversión: un token fuera del vocabulario de su enum ---
    for elemento, detalle in sorted(inventario["conversiones"].items()):
        mutantes.append(_mutante_de_conversion(elemento, detalle, schema))

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


def _mutante_de_conversion(elemento, detalle, schema) -> Mutante:
    """El par de conversión no vive en la matriz sino en el schema, así que su mutante es de
    auto-consistencia: el texto queda igual y su token sale del vocabulario del enum que la tabla
    declara. Que el par exista y diga lo que dice lo sostiene el inventario congelado, que lleva el
    texto y el token dentro del id."""
    mutado = copy.deepcopy(schema)
    mutado["x-conversiones"]["reglas"][detalle["tabla"]]["pares"][detalle["indice"]]["token"] = CENTINELA_VOCABULARIO
    return Mutante(
        "conversiones", elemento,
        f"en la tabla `{detalle['tabla']}`, el texto {detalle['texto']!r} pasa a convertir a un token "
        f"fuera del vocabulario de `{detalle['enum']}`",
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
# Nombres reservados al contenedor de perfiles de ejecución.
#
# La lista vive en `scripts/nombres-reservados-perfil.json` y es contrato compartido: la consume la
# guarda que prohíbe esos nombres en el esquema de configuración y también el documento que declara
# el schema del perfil. Una sola fuente para las dos, de modo que no puedan divergir.
#
# Acá se congela el **criterio** y no el dato: qué componentes tiene el contenedor, cómo se escribe
# una ruta de clave, y qué vuelve admisible a un nombre genérico. Los nombres, sus rutas y sus
# motivos son dato del archivo. Congelar los nombres en el código dejaría dos listas que se
# contradicen en silencio, que es exactamente lo que este contrato existe para evitar.
# ---------------------------------------------------------------------------------------------

CLAVES_DE_LA_LISTA = ("version_lista", "clave_raiz", "criterio", "reservados", "no_reservados")
CAMPOS_DE_ENTRADA = ("nombre", "componente", "ruta", "motivo")
CAMPO_DE_COBERTURA = "cubierto_por"

# Los componentes que el contenedor de perfiles declara. Si un componente deja de tener alguna
# entrada que lo declare —reservada o admitida—, el contenedor quedó descrito a medias y las dos
# consumidoras heredan una lista que no lo cubre entero.
COMPONENTES_DEL_CONTENEDOR = (
    "contenedor",
    "version",
    "perfiles_nombrados",
    "asignaciones_por_rol",
    "valor_por_defecto",
    "familias",
    "parametro_de_runtime",
)

# Los problemas que el modo sabe nombrar. Es el testigo del inventario, como el del schema: el
# autotest exige un mutante por código, y un código que nadie ejerce es una restricción declarada
# que no puede ponerse roja.
CODIGOS_DE_PROBLEMA = (
    "campo_ausente",
    "campo_no_declarado",
    "campo_vacio",
    "clave_de_raiz_ausente",
    "clave_de_raiz_no_declarada",
    "clave_raiz_mal_formada",
    "clave_raiz_sin_entrada",
    "cobertura_inexistente",
    "cobertura_no_es_ancestro",
    "componente_desconocido",
    "componente_sin_cobertura",
    "criterio_vacio",
    "entrada_no_objeto",
    "lista_no_es_arreglo",
    "lista_vacia",
    "nombre_duplicado",
    "nombre_en_ambas_listas",
    "raiz_no_objeto",
    "ruta_duplicada",
    "ruta_mal_formada",
    "ruta_no_termina_en_el_nombre",
    "ruta_sin_clave_raiz",
    "version_mal_formada",
)

PATRON_VERSION_DE_LISTA = re.compile(r"^\d+\.\d+\.\d+$")
PATRON_SEGMENTO = re.compile(r"^[a-z][a-z0-9_]*$")
PATRON_COMODIN = re.compile(r"^<[a-z][a-z0-9_]*>$")  # el tramo que nombra quien configura: <perfil>

CENTINELA_COMPONENTE = "__componente_inexistente__"
CENTINELA_NOMBRE = "__nombre_que_nadie_declara__"
CENTINELA_TRAMO = "Tramo Mal Formado"


class Problema(NamedTuple):
    codigo: str
    donde: str
    mensaje: str

    def __str__(self) -> str:
        return f"[{self.codigo}] {self.donde}: {self.mensaje}"


def _campos_requeridos(lista: str) -> tuple[str, ...]:
    """Un nombre admitido declara además cuál es el ancestro reservado que lo cubre; uno reservado
    no tiene a quién señalar."""
    return CAMPOS_DE_ENTRADA + ((CAMPO_DE_COBERTURA,) if lista == "no_reservados" else ())


def _entradas_de(datos: dict) -> list[tuple[str, int, dict]]:
    """(lista, índice, entrada) para todo lo que las dos listas contienen y es un objeto."""
    salida: list[tuple[str, int, dict]] = []
    for lista in ("reservados", "no_reservados"):
        valor = datos.get(lista)
        if not isinstance(valor, list):
            continue
        salida.extend((lista, i, e) for i, e in enumerate(valor) if isinstance(e, dict))
    return salida


def _es_ancestro(ruta_ancestro: Any, ruta: Any) -> bool:
    """True si `ruta_ancestro` es un prefijo estricto de `ruta`, tramo a tramo. La comparación es
    por tramos y no por texto: `subagents.bind` no es ancestro de `subagents.bindings`."""
    if not isinstance(ruta_ancestro, str) or not isinstance(ruta, str):
        return False
    tramos_ancestro, tramos = ruta_ancestro.split("."), ruta.split(".")
    return len(tramos_ancestro) < len(tramos) and tramos[:len(tramos_ancestro)] == tramos_ancestro


def verificar_nombres_reservados(datos: Any) -> list[Problema]:
    """Los problemas estructurales de la lista, cada uno con el código que lo nombra. El código no
    es decorativo: es lo que le permite al autotest exigir que cada mutante caiga **por su motivo**
    y no por un rechazo ajeno que se le parece."""
    if not isinstance(datos, dict):
        return [Problema("raiz_no_objeto", "$", f"se esperaba un objeto y llegó `{_nombre_tipo(datos)}`")]

    problemas: list[Problema] = []

    for clave in CLAVES_DE_LA_LISTA:
        if clave not in datos:
            problemas.append(Problema("clave_de_raiz_ausente", "$", f"falta la clave `{clave}`"))
    for clave in datos:
        if clave not in CLAVES_DE_LA_LISTA:
            problemas.append(Problema("clave_de_raiz_no_declarada", "$", f"clave no declarada `{clave}`"))

    if "version_lista" in datos:
        version = datos["version_lista"]
        if not isinstance(version, str) or PATRON_VERSION_DE_LISTA.match(version) is None:
            problemas.append(Problema(
                "version_mal_formada", "$.version_lista",
                f"se esperaba una versión de tres tramos numéricos y llegó {version!r}",
            ))

    if "criterio" in datos:
        criterio = datos["criterio"]
        if not isinstance(criterio, str) or not criterio.strip():
            problemas.append(Problema(
                "criterio_vacio", "$.criterio",
                "sin criterio escrito, la próxima edición de la lista agrega o quita nombres a ojo",
            ))

    clave_raiz = datos.get("clave_raiz")
    if not isinstance(clave_raiz, str) or PATRON_SEGMENTO.match(clave_raiz) is None:
        if "clave_raiz" in datos:
            problemas.append(Problema(
                "clave_raiz_mal_formada", "$.clave_raiz",
                f"{clave_raiz!r} no es un nombre de clave de configuración",
            ))
        clave_raiz = None

    for lista in ("reservados", "no_reservados"):
        if lista not in datos:
            continue
        valor = datos[lista]
        if not isinstance(valor, list):
            problemas.append(Problema(
                "lista_no_es_arreglo", f"$.{lista}",
                f"se esperaba un arreglo y llegó `{_nombre_tipo(valor)}`",
            ))
            continue
        if lista == "reservados" and not valor:
            problemas.append(Problema(
                "lista_vacia", "$.reservados",
                "una lista de nombres reservados vacía no prohíbe nada y deja pasar cualquier clave",
            ))
        for i, entrada in enumerate(valor):
            if not isinstance(entrada, dict):
                problemas.append(Problema(
                    "entrada_no_objeto", f"$.{lista}[{i}]",
                    f"se esperaba un objeto y llegó `{_nombre_tipo(entrada)}`",
                ))

    entradas = _entradas_de(datos)

    for lista, i, entrada in entradas:
        donde = f"$.{lista}[{i}]"
        requeridos = _campos_requeridos(lista)
        for campo in requeridos:
            if campo not in entrada:
                problemas.append(Problema("campo_ausente", f"{donde}.{campo}", f"falta el campo `{campo}`"))
                continue
            if not isinstance(entrada[campo], str) or not entrada[campo].strip():
                problemas.append(Problema(
                    "campo_vacio", f"{donde}.{campo}",
                    "el campo tiene que ser una cadena no vacía: un nombre sin motivo escrito no es "
                    "un nombre congelado, es uno que la próxima edición borra sin saber qué pierde",
                ))
        for campo in entrada:
            if campo not in requeridos:
                problemas.append(Problema("campo_no_declarado", f"{donde}.{campo}", f"campo no declarado `{campo}`"))

        componente = entrada.get("componente")
        if isinstance(componente, str) and componente.strip() and componente not in COMPONENTES_DEL_CONTENEDOR:
            problemas.append(Problema(
                "componente_desconocido", f"{donde}.componente",
                f"`{componente}` no es un componente del contenedor "
                f"({', '.join(COMPONENTES_DEL_CONTENEDOR)})",
            ))

        nombre, ruta = entrada.get("nombre"), entrada.get("ruta")
        if isinstance(ruta, str) and ruta.strip():
            tramos = ruta.split(".")
            malos = [t for t in tramos if PATRON_SEGMENTO.match(t) is None and PATRON_COMODIN.match(t) is None]
            if malos:
                problemas.append(Problema(
                    "ruta_mal_formada", f"{donde}.ruta",
                    f"el tramo {malos[0]!r} no es ni una clave ni un comodín de la forma `<nombre>`",
                ))
            elif clave_raiz is not None and tramos[0] != clave_raiz:
                problemas.append(Problema(
                    "ruta_sin_clave_raiz", f"{donde}.ruta",
                    f"la ruta empieza en {tramos[0]!r} y no en la clave raíz `{clave_raiz}`",
                ))
            if isinstance(nombre, str) and nombre.strip() and tramos[-1] != nombre:
                problemas.append(Problema(
                    "ruta_no_termina_en_el_nombre", f"{donde}.ruta",
                    f"la ruta termina en {tramos[-1]!r} y el nombre declarado es {nombre!r}",
                ))

    vistos_por_lista: dict[str, dict[str, int]] = {"reservados": {}, "no_reservados": {}}
    rutas_vistas: dict[str, str] = {}
    for lista, i, entrada in entradas:
        nombre, ruta = entrada.get("nombre"), entrada.get("ruta")
        if isinstance(nombre, str) and nombre.strip():
            previo = vistos_por_lista[lista].get(nombre)
            if previo is not None:
                problemas.append(Problema(
                    "nombre_duplicado", f"$.{lista}[{i}].nombre",
                    f"`{nombre}` ya está declarado en el índice {previo}: dos motivos para el mismo "
                    "nombre son dos motivos que pueden contradecirse",
                ))
            else:
                vistos_por_lista[lista][nombre] = i
        if isinstance(ruta, str) and ruta.strip():
            previa = rutas_vistas.get(ruta)
            if previa is not None:
                problemas.append(Problema(
                    "ruta_duplicada", f"$.{lista}[{i}].ruta",
                    f"la ruta `{ruta}` ya está declarada en {previa}",
                ))
            else:
                rutas_vistas[ruta] = f"$.{lista}[{i}]"

    for nombre in sorted(set(vistos_por_lista["reservados"]) & set(vistos_por_lista["no_reservados"])):
        problemas.append(Problema(
            "nombre_en_ambas_listas", "$",
            f"`{nombre}` está reservado y admitido a la vez: la lista no dice qué hacer con él",
        ))

    if clave_raiz is not None and not any(
        lista == "reservados" and e.get("nombre") == clave_raiz and e.get("ruta") == clave_raiz
        for lista, _, e in entradas
    ):
        problemas.append(Problema(
            "clave_raiz_sin_entrada", "$.clave_raiz",
            f"`{clave_raiz}` no figura entre los nombres reservados con su propia ruta: la clave que "
            "abre el contenedor tiene que estar prohibida ella misma",
        ))

    declarados = {e.get("componente") for _, _, e in entradas}
    for componente in COMPONENTES_DEL_CONTENEDOR:
        if componente not in declarados:
            problemas.append(Problema(
                "componente_sin_cobertura", "$",
                f"ningún nombre declara el componente `{componente}`: el contenedor queda descrito a medias",
            ))

    reservados_por_nombre = {
        e.get("nombre"): e for lista, _, e in entradas if lista == "reservados" and isinstance(e.get("nombre"), str)
    }
    for lista, i, entrada in entradas:
        if lista != "no_reservados" or CAMPO_DE_COBERTURA not in entrada:
            continue
        donde = f"$.{lista}[{i}].{CAMPO_DE_COBERTURA}"
        cubridor = entrada[CAMPO_DE_COBERTURA]
        ancestro = reservados_por_nombre.get(cubridor)
        if ancestro is None:
            problemas.append(Problema(
                "cobertura_inexistente", donde,
                f"{cubridor!r} no es un nombre reservado: un nombre admitido sin ancestro prohibido "
                "es un hueco, no una admisión",
            ))
        elif not _es_ancestro(ancestro.get("ruta"), entrada.get("ruta")):
            problemas.append(Problema(
                "cobertura_no_es_ancestro", donde,
                f"`{cubridor}` está reservado, pero su ruta no contiene a la de este nombre: "
                "no lo cubre",
            ))

    return problemas


def modo_nombres_reservados(ruta_lista: Path) -> int:
    datos, error = _cargar_json(ruta_lista)
    if error:
        print(f"FALLA  nombres reservados: {error}")
        return 1

    problemas = verificar_nombres_reservados(datos)
    if problemas:
        print(f"FALLA  {ruta_lista.name} — {len(problemas)} problemas:")
        for p in problemas[:20]:
            print(f"       - {p}")
        if len(problemas) > 20:
            print(f"       ... y {len(problemas) - 20} más")
        return 1

    reservados = len(datos.get("reservados", []))
    admitidos = len(datos.get("no_reservados", []))
    print(f"OK     {ruta_lista.name}: {reservados} nombres reservados a `{datos['clave_raiz']}` y "
          f"{admitidos} admitidos, cada uno con su motivo")
    print(f"OK     los {len(COMPONENTES_DEL_CONTENEDOR)} componentes del contenedor quedan declarados, "
          "y cada nombre admitido cuelga de un ancestro reservado")
    print()
    print("RESULTADO: OK")
    return 0


# ---------------------------------------------------------------------------------------------
# Modo `--autotest-nombres-reservados`.
# ---------------------------------------------------------------------------------------------

class MutanteNombres(NamedTuple):
    codigo: str          # el código de problema que este mutante tiene que disparar
    descripcion: str
    datos: Any


def _generar_mutantes_de_nombres(datos: dict) -> tuple[list[MutanteNombres], list[str]]:
    """Un mutante por elemento de la lista, generado desde ella y no transcrito: así la
    correspondencia entre lo que la lista declara y lo que el autotest ejerce es por construcción,
    y una entrada nueva nace con sus mutantes en vez de nacer sin cobertura."""
    mutantes: list[MutanteNombres] = []
    huecos: list[str] = []

    def nuevo(codigo: str, descripcion: str, transformar) -> None:
        copia = copy.deepcopy(datos)
        transformar(copia)
        mutantes.append(MutanteNombres(codigo, descripcion, copia))

    mutantes.append(MutanteNombres(
        "raiz_no_objeto", "la lista entera deja de ser un objeto",
        [e.get("nombre") for _, _, e in _entradas_de(datos)],
    ))
    for clave in CLAVES_DE_LA_LISTA:
        nuevo("clave_de_raiz_ausente", f"se quita `{clave}` de la raíz",
              lambda d, c=clave: d.pop(c, None))
    nuevo("clave_de_raiz_no_declarada", "se agrega una clave no declarada a la raíz",
          lambda d: d.update({CENTINELA_PROPIEDAD: True}))
    nuevo("version_mal_formada", "la versión de la lista pierde sus tres tramos",
          lambda d: d.update({"version_lista": "1"}))
    nuevo("criterio_vacio", "el criterio queda en blanco",
          lambda d: d.update({"criterio": "   "}))
    nuevo("clave_raiz_mal_formada", "la clave raíz deja de ser un nombre de clave",
          lambda d: d.update({"clave_raiz": CENTINELA_TRAMO}))
    nuevo("clave_raiz_sin_entrada", "la clave raíz pasa a un nombre que ninguna entrada declara",
          lambda d: d.update({"clave_raiz": "otra_raiz"}))
    nuevo("lista_vacia", "la lista de reservados queda vacía",
          lambda d: d.update({"reservados": []}))
    for lista in ("reservados", "no_reservados"):
        nuevo("lista_no_es_arreglo", f"`{lista}` deja de ser un arreglo",
              lambda d, l=lista: d.update({l: {}}))
        nuevo("entrada_no_objeto", f"la primera entrada de `{lista}` deja de ser un objeto",
              lambda d, l=lista: d[l].__setitem__(0, "un nombre suelto"))

    entradas = _entradas_de(datos)
    if not entradas:
        return mutantes, ["la lista no tiene entradas: no hay de qué generar mutantes por elemento"]

    for lista, i, entrada in entradas:
        etiqueta = f"{lista}[{i}] (`{entrada.get('nombre')}`)"
        for campo in _campos_requeridos(lista):
            nuevo("campo_ausente", f"se quita `{campo}` de {etiqueta}",
                  lambda d, l=lista, j=i, c=campo: d[l][j].pop(c, None))
            nuevo("campo_vacio", f"`{campo}` de {etiqueta} queda en blanco",
                  lambda d, l=lista, j=i, c=campo: d[l][j].update({c: "   "}))
        nuevo("campo_no_declarado", f"se agrega un campo no declarado a {etiqueta}",
              lambda d, l=lista, j=i: d[l][j].update({CENTINELA_PROPIEDAD: True}))
        nuevo("componente_desconocido", f"el componente de {etiqueta} sale del vocabulario",
              lambda d, l=lista, j=i: d[l][j].update({"componente": CENTINELA_COMPONENTE}))

        nombre, ruta = entrada.get("nombre"), entrada.get("ruta")
        if isinstance(nombre, str) and isinstance(ruta, str):
            nuevo("ruta_sin_clave_raiz", f"la ruta de {etiqueta} deja de colgar de la clave raíz",
                  lambda d, l=lista, j=i, n=nombre: d[l][j].update({"ruta": f"otra_raiz.{n}"}))
            nuevo("ruta_mal_formada", f"la ruta de {etiqueta} gana un tramo mal formado",
                  lambda d, l=lista, j=i, r=ruta: d[l][j].update(
                      {"ruta": ".".join([*r.split(".")[:-1], CENTINELA_TRAMO, r.split(".")[-1]])}))
            nuevo("ruta_no_termina_en_el_nombre", f"la ruta de {etiqueta} gana un tramo al final",
                  lambda d, l=lista, j=i, r=ruta: d[l][j].update({"ruta": f"{r}.otro_tramo"}))

        hermanas = [(k, e) for l, k, e in entradas if l == lista and k != i]
        if not hermanas:
            huecos.append(f"{lista}[{i}]: sin otra entrada en la misma lista, no hay con qué duplicar su nombre")
        else:
            k, hermana = hermanas[0]
            nuevo("nombre_duplicado", f"el nombre de {etiqueta} se repite en {lista}[{k}]",
                  lambda d, l=lista, j=i, n=hermana.get("nombre"): d[l][j].update({"nombre": n}))

        ajenas = [(l, k, e) for l, k, e in entradas if (l, k) != (lista, i) and e.get("ruta") != ruta]
        if not ajenas:
            huecos.append(f"{lista}[{i}]: sin otra ruta distinta en la lista, no hay con qué duplicarla")
        else:
            _, _, ajena = ajenas[0]
            nuevo("ruta_duplicada", f"la ruta de {etiqueta} pasa a ser la de otra entrada",
                  lambda d, l=lista, j=i, r=ajena.get("ruta"): d[l][j].update({"ruta": r}))

        if lista == "no_reservados":
            nuevo("cobertura_inexistente", f"{etiqueta} declara un ancestro que nadie reserva",
                  lambda d, j=i: d["no_reservados"][j].update({CAMPO_DE_COBERTURA: CENTINELA_NOMBRE}))
            reservadas = [e for l, _, e in entradas if l == "reservados" and isinstance(e.get("nombre"), str)]
            if not reservadas:
                huecos.append(f"no_reservados[{i}]: sin nombres reservados, no hay con qué probar "
                              "que un nombre esté en las dos listas")
            else:
                nuevo("nombre_en_ambas_listas", f"{etiqueta} pasa a llamarse como un nombre reservado",
                      lambda d, j=i, n=reservadas[0]["nombre"]: d["no_reservados"][j].update({"nombre": n}))
            lejanos = [
                e for l, _, e in entradas
                if l == "reservados" and not _es_ancestro(e.get("ruta"), ruta)
            ]
            if not lejanos:
                huecos.append(f"no_reservados[{i}]: todo nombre reservado es ancestro suyo, "
                              "no hay con qué probar una cobertura que no cubre")
            else:
                nuevo("cobertura_no_es_ancestro",
                      f"{etiqueta} se cubre con un reservado que no está en su ruta",
                      lambda d, j=i, n=lejanos[0].get("nombre"):
                          d["no_reservados"][j].update({CAMPO_DE_COBERTURA: n}))

    for componente in COMPONENTES_DEL_CONTENEDOR:
        alternativo = next(c for c in COMPONENTES_DEL_CONTENEDOR if c != componente)
        afectadas = [(l, k) for l, k, e in entradas if e.get("componente") == componente]
        if not afectadas:
            huecos.append(f"componentes/{componente}: ninguna entrada lo declara, "
                          "así que su mutante de cobertura no probaría nada")
            continue

        def reasignar(d, objetivo=componente, otro=alternativo):
            for lista_afectada, k in [(l, k) for l, k, e in _entradas_de(d) if e.get("componente") == objetivo]:
                d[lista_afectada][k]["componente"] = otro

        nuevo("componente_sin_cobertura",
              f"las {len(afectadas)} entradas que declaran `{componente}` pasan a `{alternativo}`",
              reasignar)

    return mutantes, huecos


def modo_autotest_nombres_reservados() -> int:
    datos, error = _cargar_json(RUTA_NOMBRES_RESERVADOS)
    if error:
        print(f"[A] FALLA  {error}")
        return 1

    resultados: list[tuple[str, bool, str]] = []

    # [A] El control positivo, que es el que falta cuando un autotest solo declara mutantes: sin él,
    # una implementación que rechace toda lista pone en rojo a los mutantes y cierra en verde sin
    # haber aceptado jamás una lista válida.
    problemas = verificar_nombres_reservados(datos)
    reservados = datos.get("reservados", []) if isinstance(datos, dict) else []
    admitidos = datos.get("no_reservados", []) if isinstance(datos, dict) else []
    resultados.append((
        "A", not problemas,
        f"control positivo: la lista real valida — {len(reservados)} nombres reservados y "
        f"{len(admitidos)} admitidos, cada uno con su motivo"
        if not problemas else f"control positivo — {len(problemas)} problemas: "
        + " | ".join(str(p) for p in problemas[:4]),
    ))

    # [B] El control positivo tiene que ejercer las variantes legítimas que **se parecen** a un
    # defecto, porque es ahí donde un rechazo indiscriminado se disfraza mejor de rigor: un mismo
    # componente declarado por dos entradas, un nombre del contenedor deliberadamente admitido, y
    # una ruta con un tramo que quien configura elige.
    faltas: list[str] = []
    entradas = _entradas_de(datos) if isinstance(datos, dict) else []
    conteo: dict[str, int] = {}
    for _, _, entrada in entradas:
        componente = entrada.get("componente")
        if isinstance(componente, str):
            conteo[componente] = conteo.get(componente, 0) + 1
    repetidos = sorted(c for c, n in conteo.items() if n > 1)
    if not repetidos:
        faltas.append("ningún componente lo declaran dos entradas: la repetición legítima queda sin ejercer")
    if not admitidos:
        faltas.append("ningún nombre admitido: la lista no ejerce el caso del nombre que sí se deja pasar")
    con_comodin = [e.get("ruta") for _, _, e in entradas if isinstance(e.get("ruta"), str) and "<" in e["ruta"]]
    if not con_comodin:
        faltas.append("ninguna ruta con comodín: el tramo que elige quien configura queda sin ejercer")
    resultados.append((
        "B", not faltas,
        f"el caso conforme ejerce las variantes que se parecen a un defecto: "
        f"componente repetido ({', '.join(repetidos)}), {len(admitidos)} nombres admitidos y "
        f"{len(con_comodin)} rutas con comodín"
        if not faltas else " | ".join(faltas),
    ))

    # [C] Los mutantes. Solo se generan si la lista real valida: derivarlos de una lista que ya
    # falla haría que un mutante "caiga" por un problema que la lista sana ya tenía.
    if problemas:
        mutantes, huecos = [], ["la lista real no valida: derivar mutantes de ella los haría caer por su defecto previo"]
    else:
        mutantes, huecos = _generar_mutantes_de_nombres(datos)
    sobrevivientes: list[str] = []
    desatribuidos: list[str] = []
    emitidos: set[str] = set()
    for mutante in mutantes:
        codigos = {p.codigo for p in verificar_nombres_reservados(mutante.datos)}
        emitidos |= codigos
        if not codigos:
            sobrevivientes.append(f"{mutante.codigo}: {mutante.descripcion}")
        elif mutante.codigo not in codigos:
            desatribuidos.append(
                f"{mutante.codigo}: {mutante.descripcion} — rechazado por {sorted(codigos)} y no por su motivo"
            )
    problemas_c = huecos + [f"SOBREVIVE {s}" for s in sobrevivientes] + [f"SIN ATRIBUIR {d}" for d in desatribuidos]
    codigos_ejercidos = {m.codigo for m in mutantes}
    resultados.append((
        "C", not problemas_c,
        f"{len(mutantes)} mutantes generados desde la lista real y los {len(mutantes)} rechazados "
        "por su propio motivo"
        if not problemas_c else f"{len(problemas_c)} problemas: " + " | ".join(problemas_c[:6]),
    ))

    # [D] Un mutante por código de problema, no uno por categoría: un código sin mutante es una
    # restricción que el modo declara y que nadie comprobó que pueda ponerse roja.
    problemas_d = [
        f"`{c}` está en el catálogo y ningún mutante lo ejerce"
        for c in CODIGOS_DE_PROBLEMA if c not in codigos_ejercidos
    ] + [
        f"`{c}` lo emite el modo y no está en el catálogo"
        for c in sorted((emitidos | codigos_ejercidos) - set(CODIGOS_DE_PROBLEMA))
    ]
    resultados.append((
        "D", not problemas_d,
        f"los {len(CODIGOS_DE_PROBLEMA)} códigos del catálogo tienen su mutante, y ninguno de los "
        f"{len(emitidos)} emitidos queda fuera del catálogo"
        if not problemas_d else f"{len(problemas_d)} huecos: " + " | ".join(problemas_d[:6]),
    ))

    orden = {"A": 0, "B": 1, "C": 2, "D": 3}
    ok_total = True
    for identificador, ok, mensaje in sorted(resultados, key=lambda r: orden[r[0]]):
        ok_total = ok_total and ok
        print(f"[{identificador}] {'OK   ' if ok else 'FALLA'} {mensaje}")
    print()
    if ok_total:
        print("RESULTADO: OK — la lista real se acepta y cada mutante se rechaza por su motivo")
        return 0
    print("RESULTADO: FALLA — ver detalle arriba")
    return 1


# ---------------------------------------------------------------------------------------------
# Correspondencia con el inventario vigente y completitud de los trece puntos.
#
# **El inventario no vive acá: se deriva del árbol.** Los puntos de despacho los declara la sección
# «Corridas delegadas en vuelo» de cada `skills/<nombre>/SKILL.md`, y eso es lo que estos dos modos
# leen. Congelar los trece en este archivo daría dos listas que se contradicen en silencio, que es
# justo lo que la matriz existe para evitar.
#
# **La correspondencia reusa la primitiva de biyección que ya existe en el repo** —`Ctx.biyeccion`
# de `scripts/verificar-sobre-en-vuelo.py`, la misma que `--ac 12` corre sobre esas secciones— en
# vez de escribir una propia. Exige las tres cosas a la vez: cada punto de la matriz cubierto por
# alguna declaración del árbol, cada declaración del árbol cubriendo algún punto, y cardinalidad
# exacta. Se reusan también sus parsers de sección y de declaraciones: derivar el inventario con un
# parser distinto del que ya lo lee sería dos lecturas del mismo artefacto que pueden discrepar, y
# entonces `--ac 12` y este modo podrían estar verdes sobre inventarios diferentes.
#
# Lo que la biyección **no** puede cerrar sola: un identificador renombrado a otro libre. Ahí no hay
# contra qué compararlo sin historia, y la inmutabilidad del identificador se verifica contra el blob
# histórico en su propio modo. Acá se cierra lo que sí es decidible sin historia —que el
# identificador exista y sea único—, porque dos puntos con el mismo identificador colapsan en una
# sola entrada y la correspondencia deja de ser punto a punto.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_INVENTARIO = REPO / "scripts" / "fixtures-matriz" / "inventario"
CONFORME_INVENTARIO = DIR_FIXTURES_INVENTARIO / "conforme"
RUTA_PRIMITIVA_BIYECCION = REPO / "scripts" / "verificar-sobre-en-vuelo.py"

SECCION_INVENTARIO = "Corridas delegadas en vuelo"
PUNTERO_NORMATIVO = "corridas-en-vuelo.md"

# El inventario son trece. El número no es un parámetro: es el desglose medido del árbol —`sdd-flow`
# 4 · `bitbucket-code-review` 2 · `co-explore` 2 · `cross-implement` 2 · `cross-review` 1 ·
# `sdd-orchestrator` 1 · `sdd-pr-feedback` 1— y la matriz lo reproduce entero o no lo reproduce.
TOTAL_PUNTOS = 13

# El catálogo de marcas del detector de sitios: la invocación literal de un worker de la otra familia
# por CLI headless. Es deliberadamente angosto —lo que no lleva marca no lo ve— y esa angostura es la
# razón por la que el modo emite un estado y no un veredicto: ver `_zonas_ciegas`.
MARCAS_DE_DESPACHO = ("codex exec", "claude -p")

# Los tres chequeos que la primitiva de biyección emite, en el orden en que los emite. Es su
# contrato: si emitiera otra cantidad, traducirlos por posición atribuiría mal, así que el traductor
# lo comprueba y se pone rojo en vez de adivinar.
CODIGOS_DE_LA_PRIMITIVA = ("biyeccion_cobertura", "biyeccion_sobrante", "biyeccion_cardinalidad")

CODIGOS_DE_ESTRUCTURA = ("matriz_no_objeto", "puntos_no_es_arreglo", "punto_no_objeto")

CODIGOS_CORRESPONDENCIA = tuple(sorted(CODIGOS_DE_ESTRUCTURA + CODIGOS_DE_LA_PRIMITIVA + (
    "etiqueta_ausente",
    "id_ausente",
    "id_duplicado",
    "primitiva_inesperada",
    "senales_ausentes",
    "skill_ausente",
    "skill_sin_inventario",
)))

CODIGOS_COMPLETITUD = tuple(sorted(CODIGOS_DE_ESTRUCTURA + (
    "ancla_ausente",
    "ancla_compartida",
    "ancla_no_es_unica",
    "sitio_no_inventariado",
    "total_de_puntos",
)))

# Enum cerrado del recibo que `--completitud` emite con `--salida`. `completa` afirma que el detector
# vio todo lo que había; `adjudicacion_humana` dice que no pudo, y con qué motivo.
ESTADO_COMPLETA = "completa"
ESTADO_ADJUDICACION = "adjudicacion_humana"
ESTADOS_DE_COMPLETITUD = (ESTADO_COMPLETA, ESTADO_ADJUDICACION)

_modulo_primitiva: Any = None


def primitiva_de_biyeccion() -> Any:
    """El módulo que trae `Ctx.biyeccion` y sus parsers. Se importa por ruta porque su nombre lleva
    guiones y no es un identificador de Python; ejecutarlo es inocuo, todo su trabajo cuelga de
    `__main__`.

    El bytecode se desactiva mientras dura el import: sin eso, cada corrida de una guarda deja un
    `scripts/__pycache__/` sin versionar en el árbol, y una guarda que ensucia el repo que audita
    convierte en ruido el `git status` con el que se la revisa."""
    global _modulo_primitiva
    if _modulo_primitiva is None:
        spec = importlib.util.spec_from_file_location(
            "verificar_sobre_en_vuelo", RUTA_PRIMITIVA_BIYECCION)
        if spec is None or spec.loader is None:
            raise FileNotFoundError(f"no se pudo cargar {RUTA_PRIMITIVA_BIYECCION}")
        modulo = importlib.util.module_from_spec(spec)
        previo = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(modulo)
        finally:
            sys.dont_write_bytecode = previo
        _modulo_primitiva = modulo
    return _modulo_primitiva


class PuntoDeMatriz(NamedTuple):
    """Lo que estos dos modos leen de un punto. El resto de sus hojas —rol, permisos, condición de
    existencia— las verifican otros modos: acá se lee poco y se lee tolerante, para que un campo mal
    formado dé su propio problema en vez de tirar la corrida entera."""

    indice: int
    identificador: Any
    etiqueta: Any
    skill: Any
    senales: Any
    ancla: Any

    @property
    def donde(self) -> str:
        return f"$.puntos[{self.indice}]"

    @property
    def nombre(self) -> str:
        return self.identificador if _es_cadena_util(self.identificador) else self.donde


def _es_cadena_util(valor: Any) -> bool:
    return isinstance(valor, str) and bool(valor.strip())


def _hoja(punto: dict, campo: str) -> Any:
    """El valor de una hoja de la matriz: `<campo>.valor`, que es la forma que declara el schema.
    Devuelve el centinela cuando la hoja no está o no tiene esa forma."""
    nodo = punto.get(campo)
    if not isinstance(nodo, dict) or "valor" not in nodo:
        return _SIN_VALOR
    return nodo["valor"]


def leer_puntos(datos: Any) -> tuple[list[PuntoDeMatriz], list[Problema]]:
    """Los puntos que la matriz declara, con los problemas estructurales que impiden leerlos."""
    if not isinstance(datos, dict):
        return [], [Problema("matriz_no_objeto", "$",
                             f"se esperaba un objeto y llegó `{_nombre_tipo(datos)}`")]
    crudos = datos.get("puntos")
    if not isinstance(crudos, list):
        return [], [Problema("puntos_no_es_arreglo", "$.puntos",
                             f"se esperaba un arreglo y llegó `{_nombre_tipo(crudos)}`")]
    puntos: list[PuntoDeMatriz] = []
    problemas: list[Problema] = []
    for i, punto in enumerate(crudos):
        if not isinstance(punto, dict):
            problemas.append(Problema("punto_no_objeto", f"$.puntos[{i}]",
                                      f"se esperaba un objeto y llegó `{_nombre_tipo(punto)}`"))
            continue
        puntos.append(PuntoDeMatriz(
            i,
            punto.get("id", _SIN_VALOR),
            punto.get("etiqueta", _SIN_VALOR),
            _hoja(punto, "skill"),
            _hoja(punto, "senales_de_deteccion"),
            _hoja(punto, "ancla_de_invocacion"),
        ))
    return puntos, problemas


def _inventario_del_arbol(arbol: Path) -> tuple[dict[str, list[str]], list[str]]:
    """El inventario vigente: por skill, las declaraciones de su sección de corridas en vuelo, sin
    el puntero normativo a la copia local del contrato. Devuelve además las skills que tienen
    `SKILL.md` y no declaran la sección: para la correspondencia son mudas, y para el detector de
    completitud son una zona ciega."""
    sev = primitiva_de_biyeccion()
    inventario: dict[str, list[str]] = {}
    sin_seccion: list[str] = []
    dir_skills = arbol / "skills"
    if not dir_skills.is_dir():
        return inventario, sin_seccion
    for sub in sorted(p for p in dir_skills.iterdir() if p.is_dir()):
        ruta = sub / "SKILL.md"
        if not ruta.is_file():
            continue
        cuerpo = sev.seccion(ruta.read_text(encoding="utf-8"), SECCION_INVENTARIO)
        if cuerpo is None:
            sin_seccion.append(sub.name)
            continue
        inventario[sub.name] = [d for d in sev.declaraciones(cuerpo) if PUNTERO_NORMATIVO not in d]
    return inventario, sin_seccion


def _traducir_biyeccion(skill: str, filas: list) -> list[Problema]:
    """Las filas que la primitiva emitió, traducidas al código que las nombra. La traducción es por
    posición y el contrato es el orden; si la primitiva cambiara de forma, atribuir por posición
    diría el motivo equivocado, así que acá se prefiere un rojo que lo diga."""
    if len(filas) != len(CODIGOS_DE_LA_PRIMITIVA):
        return [Problema(
            "primitiva_inesperada", f"skills/{skill}/SKILL.md",
            f"la primitiva de biyección emitió {len(filas)} chequeos y este modo traduce "
            f"{len(CODIGOS_DE_LA_PRIMITIVA)}: la atribución por posición dejó de ser válida",
        )]
    problemas: list[Problema] = []
    for codigo, (ok, nombre, detalle) in zip(CODIGOS_DE_LA_PRIMITIVA, filas):
        if not ok:
            problemas.append(Problema(codigo, f"skills/{skill}/SKILL.md",
                                      f"{nombre} — {detalle}" if detalle else nombre))
    return problemas


def _biyeccion_por_skill(skill: str, decls: list[str], senales: dict[str, list[str]]) -> list[Problema]:
    sev = primitiva_de_biyeccion()
    ctx = sev.Ctx(REPO)  # la raíz no se usa: la primitiva compara texto ya leído, no abre archivos
    ctx.biyeccion(f"{skill}: puntos de despacho", decls, senales)
    return _traducir_biyeccion(skill, ctx.filas)


def verificar_correspondencia(datos: Any, arbol: Path) -> tuple[list[Problema], dict]:
    """Matriz ↔ inventario vigente, skill por skill."""
    puntos, problemas = leer_puntos(datos)

    vistos: dict[str, int] = {}
    comparables: list[PuntoDeMatriz] = []
    for punto in puntos:
        entero = True
        if not _es_cadena_util(punto.identificador):
            problemas.append(Problema(
                "id_ausente", f"{punto.donde}.id",
                "el punto no declara identificador: sin él la correspondencia no puede señalar "
                "cuál es el punto afectado",
            ))
            entero = False
        elif punto.identificador in vistos:
            problemas.append(Problema(
                "id_duplicado", f"{punto.donde}.id",
                f"`{punto.identificador}` ya lo declara $.puntos[{vistos[punto.identificador]}]: "
                "dos puntos con el mismo identificador colapsan en una sola entrada del inventario "
                "y la correspondencia deja de ser punto a punto",
            ))
            entero = False
        else:
            vistos[punto.identificador] = punto.indice

        if not _es_cadena_util(punto.etiqueta):
            problemas.append(Problema(
                "etiqueta_ausente", f"{punto.donde}.etiqueta",
                "la etiqueta legible es editorial y su contenido no se compara con nada, pero un "
                "punto sin etiqueta deja de tener las tres identidades separadas que la matriz pide",
            ))

        if not _es_cadena_util(punto.skill):
            problemas.append(Problema(
                "skill_ausente", f"{punto.donde}.skill.valor",
                "el punto no declara a qué skill pertenece: no hay inventario contra el cual "
                "corresponderlo",
            ))
            entero = False

        if (not isinstance(punto.senales, list) or not punto.senales
                or not all(_es_cadena_util(s) for s in punto.senales)):
            problemas.append(Problema(
                "senales_ausentes", f"{punto.donde}.senales_de_deteccion.valor",
                "las señales de detección tienen que ser una lista no vacía de cadenas: son lo que "
                "ancla el punto a su declaración en el árbol",
            ))
            entero = False

        if entero:
            comparables.append(punto)

    inventario, _ = _inventario_del_arbol(arbol)
    skills = sorted(set(inventario) | {p.skill for p in comparables})
    for skill in skills:
        senales = {p.identificador: list(p.senales) for p in comparables if p.skill == skill}
        decls = inventario.get(skill)
        if decls is None:
            if senales:
                problemas.append(Problema(
                    "skill_sin_inventario", f"skills/{skill}/SKILL.md",
                    f"{len(senales)} puntos declaran la skill `{skill}` y el árbol no trae su "
                    f"sección «{SECCION_INVENTARIO}»: {', '.join(sorted(senales))}",
                ))
            continue
        problemas.extend(_biyeccion_por_skill(skill, decls, senales))

    resumen = {
        "puntos": len(puntos),
        "skills": len(skills),
        "declaraciones": sum(len(d) for d in inventario.values()),
    }
    return problemas, resumen


# --- Completitud: un ancla por punto, y el detector de sitios ---------------------------------

class Sitio(NamedTuple):
    ruta: str
    linea: int          # 1-based, para el mensaje
    marca: str
    texto: str


def _slug(titulo: str) -> str:
    """El fragmento con el que un ancla nombra un encabezado. Se apoya en la normalización de la
    primitiva —minúsculas, sin diacríticos, sin backticks— y colapsa el resto en guiones."""
    return re.sub(r"[^a-z0-9]+", "-", primitiva_de_biyeccion().norm(titulo)).strip("-")


def _rangos_de_secciones(texto: str) -> dict[str, tuple[int, int]]:
    """slug del encabezado → rango de líneas (0-based, inclusivo) de su sección, que termina en el
    próximo encabezado de nivel menor o igual. Ante slugs repetidos gana el primero."""
    lineas = texto.split("\n")
    encabezados: list[tuple[int, int, str]] = []
    for i, linea in enumerate(lineas):
        m = re.match(r"^(#+)\s+(.*)$", linea)
        if m:
            encabezados.append((i, len(m.group(1)), _slug(m.group(2))))
    rangos: dict[str, tuple[int, int]] = {}
    for j, (inicio, nivel, slug) in enumerate(encabezados):
        fin = len(lineas) - 1
        for otro_inicio, otro_nivel, _ in encabezados[j + 1:]:
            if otro_nivel <= nivel:
                fin = otro_inicio - 1
                break
        if slug and slug not in rangos:
            rangos[slug] = (inicio, fin)
    return rangos


def _secciones_ancladas(arbol: Path, anclas: list[str]) -> tuple[dict[str, tuple[str, int, int]], list[str]]:
    """ancla → (ruta relativa, primera línea, última línea) de la sección que señala, y la lista de
    anclas que no resuelven contra el árbol."""
    resueltas: dict[str, tuple[str, int, int]] = {}
    sin_resolver: list[str] = []
    for ancla in anclas:
        ruta_rel, _, fragmento = ancla.partition("#")
        archivo = arbol / ruta_rel
        if not fragmento or not archivo.is_file():
            sin_resolver.append(ancla)
            continue
        rango = _rangos_de_secciones(archivo.read_text(encoding="utf-8")).get(fragmento)
        if rango is None:
            sin_resolver.append(ancla)
            continue
        resueltas[ancla] = (ruta_rel, rango[0], rango[1])
    return resueltas, sin_resolver


def _sitios_de_despacho(arbol: Path) -> list[Sitio]:
    """Toda línea de `skills/**/*.md` que lleva una marca del catálogo."""
    sev = primitiva_de_biyeccion()
    salida: list[Sitio] = []
    dir_skills = arbol / "skills"
    if not dir_skills.is_dir():
        return salida
    for archivo in sorted(dir_skills.rglob("*.md")):
        rel = archivo.relative_to(arbol).as_posix()
        for i, linea in enumerate(archivo.read_text(encoding="utf-8").split("\n")):
            normalizada = sev.norm(linea)
            for marca in MARCAS_DE_DESPACHO:
                if marca in normalizada:
                    salida.append(Sitio(rel, i + 1, marca, linea.strip()[:90]))
                    break
    return salida


def _sitio_inventariado(sitio: Sitio, secciones: dict[str, tuple[str, int, int]]) -> bool:
    return any(ruta == sitio.ruta and inicio <= sitio.linea - 1 <= fin
               for ruta, inicio, fin in secciones.values())


def _zonas_ciegas(sin_seccion: list[str], sin_resolver: list[str],
                  secciones: dict[str, tuple[str, int, int]], sitios: list[Sitio]) -> list[str]:
    """Lo que el detector **no** puede ver. Su existencia es lo que separa `completa` de
    `adjudicacion_humana`: un detector que no distingue las dos cosas presenta como verificado lo
    que apenas miró."""
    ciegas: list[str] = []
    for skill in sorted(sin_seccion):
        ciegas.append(f"`skills/{skill}/SKILL.md` no declara la sección «{SECCION_INVENTARIO}»: "
                      "no se puede saber si esa skill despacha")
    for ancla in sorted(sin_resolver):
        ciegas.append(f"el ancla `{ancla}` no resuelve contra el árbol: el sitio que respalda no se "
                      "puede localizar")
    sin_marca = sorted(
        ancla for ancla, (ruta, inicio, fin) in secciones.items()
        if not any(s.ruta == ruta and inicio <= s.linea - 1 <= fin for s in sitios)
    )
    for ancla in sin_marca:
        ciegas.append(f"la sección que ancla `{ancla}` no contiene ninguna marca del catálogo "
                      f"({', '.join(MARCAS_DE_DESPACHO)}): cómo despacha ese punto queda fuera del "
                      "alcance del detector")
    if not sitios:
        ciegas.append("el catálogo de marcas no detectó ningún sitio en todo el árbol: un detector "
                      "que no ve nada no puede afirmar completitud")
    return ciegas


def verificar_completitud(datos: Any, arbol: Path) -> tuple[list[Problema], dict]:
    """Trece puntos, un ancla propia por punto, y el detector de sitios evaluado aparte."""
    puntos, problemas = leer_puntos(datos)
    ilegible = {p.codigo for p in problemas} & {"matriz_no_objeto", "puntos_no_es_arreglo"}
    if not ilegible and len(puntos) != TOTAL_PUNTOS:
        problemas.append(Problema(
            "total_de_puntos", "$.puntos",
            f"la matriz declara {len(puntos)} puntos y el inventario son {TOTAL_PUNTOS}",
        ))

    por_ancla: dict[str, list[str]] = {}
    for punto in puntos:
        donde = f"{punto.donde}.ancla_de_invocacion.valor"
        if isinstance(punto.ancla, list) and len(punto.ancla) > 1:
            problemas.append(Problema(
                "ancla_no_es_unica", donde,
                f"`{punto.nombre}` declara {len(punto.ancla)} anclas: el total puede seguir dando "
                f"{TOTAL_PUNTOS} mientras otro punto se queda sin la suya, y ahí la completitud "
                "sería un conteo y no una correspondencia punto a punto",
            ))
            continue
        if not _es_cadena_util(punto.ancla):
            llegado = ("no la declara" if punto.ancla is _SIN_VALOR
                       else f"llegó `{_nombre_tipo(punto.ancla)}`")
            problemas.append(Problema(
                "ancla_ausente", donde,
                f"`{punto.nombre}` no tiene un ancla de invocación utilizable ({llegado}): sin ella "
                "no hay dónde ejecutar el punto ni contra qué contrastar el sitio que lo despacha",
            ))
            continue
        por_ancla.setdefault(punto.ancla.strip(), []).append(punto.nombre)

    for ancla, duenos in sorted(por_ancla.items()):
        if len(duenos) > 1:
            problemas.append(Problema(
                "ancla_compartida", "$.puntos",
                f"`{ancla}` la declaran {len(duenos)} puntos ({', '.join(duenos)}): uno de ellos "
                "no tiene ancla propia aunque el total no baje",
            ))

    _, sin_seccion = _inventario_del_arbol(arbol)
    secciones, sin_resolver = _secciones_ancladas(arbol, sorted(por_ancla))
    sitios = _sitios_de_despacho(arbol)
    no_inventariados = [s for s in sitios if not _sitio_inventariado(s, secciones)]
    for sitio in no_inventariados:
        problemas.append(Problema(
            "sitio_no_inventariado", f"{sitio.ruta}:{sitio.linea}",
            f"despacha con `{sitio.marca}` fuera de toda sección anclada por la matriz — {sitio.texto}",
        ))

    ciegas = _zonas_ciegas(sin_seccion, sin_resolver, secciones, sitios)
    resumen = {
        "puntos": len(puntos),
        "anclas": len(por_ancla),
        "sitios_detectados": len(sitios),
        "sitios_no_inventariados": [f"{s.ruta}:{s.linea}" for s in no_inventariados],
        "estado": ESTADO_COMPLETA if not ciegas else ESTADO_ADJUDICACION,
        "motivo": "" if not ciegas else " | ".join(ciegas),
    }
    return problemas, resumen


# --- Modos de aplicación ----------------------------------------------------------------------

def _falta_la_primitiva() -> bool:
    if RUTA_PRIMITIVA_BIYECCION.is_file():
        return False
    print(f"FALLA  no está la primitiva de biyección ({RUTA_PRIMITIVA_BIYECCION.name}): este modo "
          "la reusa en vez de escribir una propia y sin ella no puede comparar nada")
    return True


def _informar(problemas: list[Problema], etiqueta: str) -> None:
    print(f"FALLA  {etiqueta} — {len(problemas)} problemas:")
    for p in problemas[:20]:
        print(f"       - {p}")
    if len(problemas) > 20:
        print(f"       ... y {len(problemas) - 20} más")


def modo_correspondencia(ruta_matriz: Path, arbol: Path) -> int:
    if _falta_la_primitiva():
        return 1
    datos, error = _cargar_json(ruta_matriz)
    if error:
        print(f"FALLA  correspondencia: {error}")
        return 1

    problemas, resumen = verificar_correspondencia(datos, arbol)
    if problemas:
        _informar(problemas, f"{ruta_matriz.name} contra el inventario vigente")
        return 1

    print(f"OK     {ruta_matriz.name}: {resumen['puntos']} puntos en correspondencia exacta con las "
          f"{resumen['declaraciones']} declaraciones de {resumen['skills']} skills del árbol")
    print("OK     sin altas, sin bajas y sin señales que ninguna declaración respalde")
    print()
    print("RESULTADO: OK")
    return 0


def modo_completitud(ruta_matriz: Path, arbol: Path, salida: Path | None) -> int:
    if _falta_la_primitiva():
        return 1
    datos, error = _cargar_json(ruta_matriz)
    if error:
        print(f"FALLA  completitud: {error}")
        return 1

    problemas, resumen = verificar_completitud(datos, arbol)
    if salida is not None:
        _escribir_recibo(salida, resumen, problemas)
        print(f"       recibo escrito en {salida}")

    if resumen["estado"] == ESTADO_ADJUDICACION:
        print(f"AVISO  el detector de sitios no puede ser completo: estado `{ESTADO_ADJUDICACION}`")
        for motivo in resumen["motivo"].split(" | ")[:6]:
            print(f"       - {motivo}")
    if problemas:
        _informar(problemas, f"{ruta_matriz.name}: completitud de los {TOTAL_PUNTOS} puntos")
        return 1

    print(f"OK     {resumen['puntos']} puntos y {resumen['anclas']} anclas de invocación distintas, "
          "una por punto")
    print(f"OK     {resumen['sitios_detectados']} sitios de despacho detectados y ninguno fuera del "
          f"inventario (estado `{resumen['estado']}`)")
    print()
    print("RESULTADO: OK")
    return 0


def _escribir_recibo(ruta: Path, resumen: dict, problemas: list[Problema]) -> None:
    """El recibo que consume la task del documento de contrato. Existe porque un handoff entre
    agentes frescos necesita un archivo: contado de palabra, el estado se pierde en el camino y la
    completitud se presenta como verificada sin que nadie lo haya comprobado."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({
        "version": "1.0.0",
        "estado": resumen["estado"],
        "motivo": resumen["motivo"],
        "puntos": resumen["puntos"],
        "anclas": resumen["anclas"],
        "sitios_detectados": resumen["sitios_detectados"],
        "sitios_no_inventariados": resumen["sitios_no_inventariados"],
        "problemas": [str(p) for p in problemas],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# --- Autotests de los dos modos ---------------------------------------------------------------
#
# Los casos se **generan** desde un único fixture conforme, congelado y sintético: `skill-alfa` …
# `skill-epsilon` no existen en el árbol real y sus puntos no describen a ninguna skill real. Es
# deliberado: un fixture copiado de la matriz real haría que el modo y el dato acordaran entre sí,
# y un modo ajustado hasta que la matriz real pase hereda la interpretación de esa matriz.

class CasoDeInventario(NamedTuple):
    codigo: str | None      # el problema que el caso tiene que disparar; None = caso conforme
    descripcion: str
    mutar_matriz: Any       # (datos) -> datos, o None
    mutar_arbol: Any        # (raíz) -> None, o None
    estado: str | None      # el estado del detector que el caso fija, cuando lo fija


def _mutando(transformar):
    """Envuelve una mutación in situ para que devuelva la matriz mutada."""
    def envuelto(datos):
        transformar(datos)
        return datos
    return envuelto


def _skill_muda(raiz: Path) -> None:
    """Una skill del árbol sin su sección de inventario: no declara puntos y nadie puede saber si
    despacha. Es la zona ciega del detector, y no es un defecto de la matriz."""
    ruta = raiz / "skills" / "skill-zeta" / "SKILL.md"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        "---\nname: skill-zeta\n---\n\n# skill-zeta (sintética)\n\n"
        "Skill sin sección de corridas delegadas en vuelo.\n", encoding="utf-8")


def _sitio_fuera_del_inventario(raiz: Path) -> None:
    ruta = raiz / "skills" / "skill-alfa" / "SKILL.md"
    ruta.write_text(ruta.read_text(encoding="utf-8") + (
        "\n## Auditoría que nadie inventarió\n\n"
        "El conductor lanza al auditor con `codex exec -s read-only` sin declararlo entre sus "
        "puntos de despacho.\n"), encoding="utf-8")


PUNTO_DE_MAS = {
    "id": "skill-alfa-recolector-fantasma",
    "etiqueta": "Recolector que ninguna declaración del árbol respalda",
    "skill": {"valor": "skill-alfa"},
    "senales_de_deteccion": {"valor": ["recolector fantasma"]},
    "ancla_de_invocacion": {"valor": "skills/skill-alfa/SKILL.md#recolector-fantasma"},
}


def _trece_anclas_mal_repartidas(datos: dict) -> None:
    """El total de anclas sigue siendo trece y un punto se queda sin la suya, porque otro se lleva
    dos. Un modo que cuente anclas pasa; solo cae si la correspondencia es punto a punto."""
    primero, segundo = datos["puntos"][0], datos["puntos"][1]
    ajena = primero["ancla_de_invocacion"]["valor"]
    propia = segundo["ancla_de_invocacion"]["valor"]
    primero["ancla_de_invocacion"]["valor"] = []
    segundo["ancla_de_invocacion"]["valor"] = [propia, ajena]


CASOS_CORRESPONDENCIA = (
    CasoDeInventario(None, "el fixture conforme corresponde con su inventario", None, None, None),
    CasoDeInventario(
        None, "cambiar únicamente la etiqueta legible no falla: la etiqueta es editorial",
        _mutando(lambda d: d["puntos"][0].update({"etiqueta": "Otro rótulo, de otra mano"})),
        None, None),
    CasoDeInventario("matriz_no_objeto", "la matriz entera deja de ser un objeto",
                     lambda d: [p["id"] for p in d["puntos"]], None, None),
    CasoDeInventario("puntos_no_es_arreglo", "`puntos` deja de ser un arreglo",
                     _mutando(lambda d: d.update({"puntos": {}})), None, None),
    CasoDeInventario("punto_no_objeto", "el primer punto deja de ser un objeto",
                     _mutando(lambda d: d["puntos"].__setitem__(0, "un punto suelto")), None, None),
    CasoDeInventario("id_ausente", "se quita el identificador de un punto",
                     _mutando(lambda d: d["puntos"][0].pop("id")), None, None),
    CasoDeInventario("id_duplicado", "cambio de identificador: un punto pasa a llamarse como otro",
                     _mutando(lambda d: d["puntos"][1].update({"id": d["puntos"][0]["id"]})),
                     None, None),
    CasoDeInventario("etiqueta_ausente", "la etiqueta legible queda en blanco",
                     _mutando(lambda d: d["puntos"][0].update({"etiqueta": "   "})), None, None),
    CasoDeInventario("skill_ausente", "se quita la skill de un punto",
                     _mutando(lambda d: d["puntos"][0].pop("skill")), None, None),
    CasoDeInventario("senales_ausentes", "las señales de detección quedan vacías",
                     _mutando(lambda d: d["puntos"][0]["senales_de_deteccion"].update({"valor": []})),
                     None, None),
    CasoDeInventario("skill_sin_inventario", "un punto declara una skill que el árbol no inventaría",
                     _mutando(lambda d: d["puntos"][0]["skill"].update({"valor": "skill-omega"})),
                     None, None),
    CasoDeInventario("biyeccion_cardinalidad", "alta: se agrega un punto que ninguna declaración respalda",
                     _mutando(lambda d: d["puntos"].append(copy.deepcopy(PUNTO_DE_MAS))), None, None),
    CasoDeInventario("biyeccion_sobrante", "baja: se quita un punto y su declaración queda huérfana",
                     _mutando(lambda d: d["puntos"].pop(0)), None, None),
    CasoDeInventario("biyeccion_cobertura", "se mueve un punto a otra skill",
                     _mutando(lambda d: d["puntos"][0]["skill"].update({"valor": "skill-delta"})),
                     None, None),
    CasoDeInventario("biyeccion_cobertura",
                     "se alteran las señales de detección sin actualizar su ancla en el árbol",
                     _mutando(lambda d: d["puntos"][0]["senales_de_deteccion"].update(
                         {"valor": ["explorador tardío"]})), None, None),
)

CASOS_COMPLETITUD = (
    CasoDeInventario(None, f"el fixture conforme: {TOTAL_PUNTOS} puntos, cada uno con su ancla y "
                           "ningún sitio adicional", None, None, ESTADO_COMPLETA),
    CasoDeInventario(None, "una skill muda deja al detector incompleto y eso se declara, no falla",
                     None, _skill_muda, ESTADO_ADJUDICACION),
    CasoDeInventario("matriz_no_objeto", "la matriz entera deja de ser un objeto",
                     lambda d: [p["id"] for p in d["puntos"]], None, None),
    CasoDeInventario("puntos_no_es_arreglo", "`puntos` deja de ser un arreglo",
                     _mutando(lambda d: d.update({"puntos": {}})), None, None),
    CasoDeInventario("punto_no_objeto", "el primer punto deja de ser un objeto",
                     _mutando(lambda d: d["puntos"].__setitem__(0, "un punto suelto")), None, None),
    CasoDeInventario("total_de_puntos", f"la matriz declara {TOTAL_PUNTOS + 1} puntos",
                     _mutando(lambda d: d["puntos"].append(copy.deepcopy(PUNTO_DE_MAS))), None, None),
    CasoDeInventario("ancla_ausente", "se retira el ancla de invocación de un punto",
                     _mutando(lambda d: d["puntos"][0].pop("ancla_de_invocacion")), None, None),
    CasoDeInventario("ancla_no_es_unica",
                     f"el total sigue en {TOTAL_PUNTOS} anclas: un punto sin la suya y dos para otro",
                     _mutando(_trece_anclas_mal_repartidas), None, None),
    CasoDeInventario("ancla_compartida", "dos puntos declaran el mismo ancla",
                     _mutando(lambda d: d["puntos"][1]["ancla_de_invocacion"].update(
                         {"valor": d["puntos"][0]["ancla_de_invocacion"]["valor"]})), None, None),
    CasoDeInventario("sitio_no_inventariado", "el árbol despacha en una sección que ninguna ancla señala",
                     None, _sitio_fuera_del_inventario, None),
    CasoDeInventario("ancla_ausente",
                     "la adjudicación humana no sustituye a las anclas: con el detector incompleto, "
                     "un punto sin ancla sigue siendo rojo",
                     _mutando(lambda d: d["puntos"][0].pop("ancla_de_invocacion")),
                     _skill_muda, ESTADO_ADJUDICACION),
)


def _correr_caso(caso: CasoDeInventario, verificar) -> tuple[list[Problema], dict]:
    """Cada caso corre sobre una copia temporal del fixture: los que mutan el árbol escriben
    archivos, y hacerlo sobre el fixture congelado lo dejaría mutado si el proceso muriera."""
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "arbol"
        shutil.copytree(CONFORME_INVENTARIO, raiz)
        datos = json.loads((raiz / "matriz.json").read_text(encoding="utf-8"))
        if caso.mutar_matriz is not None:
            datos = caso.mutar_matriz(datos)
        if caso.mutar_arbol is not None:
            caso.mutar_arbol(raiz)
        return verificar(datos, raiz)


def _autotest_de_inventario(titulo: str, casos: tuple[CasoDeInventario, ...],
                            verificar, catalogo: tuple[str, ...],
                            extra_ejercidos: tuple[str, ...] = ()) -> int:
    if not CONFORME_INVENTARIO.is_dir():
        print(f"[A] FALLA  no existe el fixture conforme ({CONFORME_INVENTARIO})")
        return 1
    if _falta_la_primitiva():
        return 1

    resultados: list[tuple[str, bool, str]] = []

    # [A] El control positivo. Sin él, una implementación que rechace toda matriz —`return
    # [Problema(...)]`— satisface todos los mutantes y cierra en verde sin haber aceptado nada.
    conformes = [c for c in casos if c.codigo is None]
    fallas_conformes: list[str] = []
    for caso in conformes:
        problemas, resumen = _correr_caso(caso, verificar)
        if problemas:
            fallas_conformes.append(f"{caso.descripcion} — {problemas[0]}")
        elif caso.estado is not None and resumen.get("estado") != caso.estado:
            fallas_conformes.append(
                f"{caso.descripcion} — estado {resumen.get('estado')!r}, esperado {caso.estado!r}")
        elif caso.estado == ESTADO_ADJUDICACION and not resumen.get("motivo"):
            fallas_conformes.append(f"{caso.descripcion} — sin motivo escrito de la adjudicación")
    resultados.append((
        "A", not fallas_conformes,
        f"control positivo: los {len(conformes)} casos conformes pasan "
        f"({' · '.join(c.descripcion.split(':')[0] for c in conformes)})"
        if not fallas_conformes else "control positivo — " + " | ".join(fallas_conformes[:3]),
    ))

    # [B] Los mutantes, cada uno rechazado **por su motivo**: un rechazo ajeno que se le parece
    # reportaría cobertura que no existe.
    mutantes = [c for c in casos if c.codigo is not None]
    sobrevivientes: list[str] = []
    desatribuidos: list[str] = []
    estados_mal: list[str] = []
    emitidos: set[str] = set()
    for caso in mutantes:
        problemas, resumen = _correr_caso(caso, verificar)
        codigos = {p.codigo for p in problemas}
        emitidos |= codigos
        if not codigos:
            sobrevivientes.append(f"{caso.codigo}: {caso.descripcion}")
        elif caso.codigo not in codigos:
            desatribuidos.append(f"{caso.codigo}: {caso.descripcion} — rechazado por "
                                 f"{sorted(codigos)} y no por su motivo")
        if caso.estado is not None and resumen.get("estado") != caso.estado:
            estados_mal.append(f"{caso.codigo}: estado {resumen.get('estado')!r}, "
                               f"esperado {caso.estado!r}")
    problemas_b = ([f"SOBREVIVE {s}" for s in sobrevivientes]
                   + [f"SIN ATRIBUIR {d}" for d in desatribuidos]
                   + [f"ESTADO {e}" for e in estados_mal])
    resultados.append((
        "B", not problemas_b,
        f"{len(mutantes)} mutantes generados desde el fixture conforme y los {len(mutantes)} "
        "rechazados por su propio motivo"
        if not problemas_b else f"{len(problemas_b)} problemas: " + " | ".join(problemas_b[:5]),
    ))

    # [C] Un mutante por código, no uno por categoría: un código sin mutante es una restricción que
    # el modo declara y que nadie comprobó que pueda ponerse roja.
    ejercidos = {c.codigo for c in mutantes} | set(extra_ejercidos)
    problemas_c = [f"`{c}` está en el catálogo y ningún caso lo ejerce"
                   for c in catalogo if c not in ejercidos]
    problemas_c += [f"`{c}` lo emite el modo y no está en el catálogo"
                    for c in sorted((emitidos | ejercidos) - set(catalogo))]
    resultados.append((
        "C", not problemas_c,
        f"los {len(catalogo)} códigos del catálogo tienen su caso, y ninguno de los "
        f"{len(emitidos)} emitidos queda fuera"
        if not problemas_c else f"{len(problemas_c)} huecos: " + " | ".join(problemas_c[:5]),
    ))

    ok_total = True
    for identificador, ok, mensaje in resultados:
        ok_total = ok_total and ok
        print(f"[{identificador}] {'OK   ' if ok else 'FALLA'} {mensaje}")
    print()
    if ok_total:
        print(f"RESULTADO: OK — {titulo}")
        return 0
    print("RESULTADO: FALLA — ver detalle arriba")
    return 1


def modo_autotest_correspondencia() -> int:
    # El código de la primitiva desalineada no se ejerce mutando la matriz —haría falta reescribir
    # el módulo que se reusa—: se ejerce sobre el traductor, que es donde vive la suposición.
    desalineada = _traducir_biyeccion("skill-alfa", [(True, "una sola fila", "")])
    if [p.codigo for p in desalineada] != ["primitiva_inesperada"]:
        print("[A] FALLA  el traductor no se pone rojo cuando la primitiva cambia de forma: "
              f"emitió {[p.codigo for p in desalineada]}")
        return 1
    return _autotest_de_inventario(
        "la matriz conforme corresponde con su inventario y cada mutante cae por su motivo",
        CASOS_CORRESPONDENCIA, verificar_correspondencia, CODIGOS_CORRESPONDENCIA,
        extra_ejercidos=("primitiva_inesperada",))


def modo_autotest_completitud() -> int:
    return _autotest_de_inventario(
        f"los {TOTAL_PUNTOS} puntos tienen su ancla propia y el detector nombra el sitio que nadie "
        "inventarió", CASOS_COMPLETITUD, verificar_completitud, CODIGOS_COMPLETITUD)


# ---------------------------------------------------------------------------------------------
# El resolutor tipado de anclas y los tres modos que lo consumen.
#
# **El verificador no guarda valores esperados: los extrae.** Una hoja declara su `valor` y su
# `procedencia`; el resolutor ejecuta la procedencia contra la sede y el modo compara. Un resolutor
# que devolviera el `valor` declarado —o que aceptara cualquier texto plausible— dejaría a la matriz
# verde contra sí misma, que es el defecto que este contrato existe para cerrar.
#
# **El pipeline corre en el orden que el schema congela y no en otro**, porque cambiarlo cambia el
# resultado. El orden no se transcribe acá: se lee de `x-pipeline.orden` y se compara contra el que
# este código implementa. Si el artefacto cambiara de orden, los modos se ponen rojos en vez de
# seguir con el suyo.
#
# **Dos comprobaciones sobre la sede preceden a `seleccionar`** y no son pasos del pipeline, son sus
# precondiciones: no se puede seleccionar sobre una sede que este flujo produce ni sobre una que no
# existe. Y van **en ese orden**: la admisibilidad antes que la existencia, o una hoja que se cita a
# sí misma en un archivo todavía inexistente se reportaría como `sede_inexistente` y la prohibición
# de autorreferencia quedaría indistinguible de un error de ruta.
# ---------------------------------------------------------------------------------------------

# El enum cerrado de errores del resolutor. Son seis y no siete: los subtipos —qué falló dentro de
# la conversión, por qué no hubo nodos— viajan en `causa`, que es texto de diagnóstico y no un
# séptimo error. El schema ya usa ese patrón: `x-conversiones` nombra `conversion_sin_par` y
# `conversion_sin_tabla` como causas de una sola falla de conversión.
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
PASOS_DEL_PIPELINE = (
    "seleccionar",
    "comprobar_cardinalidad",
    "extraer",
    "normalizar",
    "ordenar",
    "convertir",
    "colapsar",
)


def _artefactos_del_flujo() -> tuple[str, ...]:
    """Lo que este flujo produce, en forma de rutas relativas al repositorio. **Se deriva de las
    constantes del módulo**, no se transcribe: una lista escrita a mano quedaría vieja en cuanto un
    artefacto cambiara de nombre, y la autorreferencia volvería a pasar como sede legítima."""
    rutas = (RUTA_MATRIZ, RUTA_SCHEMA, DIR_FIXTURES, Path(__file__).resolve())
    return tuple(sorted(r.relative_to(REPO).as_posix() for r in rutas))


ARTEFACTOS_DEL_FLUJO = _artefactos_del_flujo()

# `booleano` y `referencia` no tienen tabla declarada en el schema: `x-conversiones` cubre solo
# `enum:<nombre>`. Lo que va acá es el cotejo mínimo que permite resolverlas —exacto y cerrado, con
# el mismo criterio que la tabla: sin par, falla—, y está marcado como hueco del contrato en el
# informe de esta task. Ampliarlo por analogía sería inventar el mapeo que `x-conversiones` existe
# para no dejar inventar.
TEXTOS_BOOLEANOS = {"true": True, "false": False}
PATRON_ENTERO = re.compile(r"^-?\d+$")
PATRON_REFERENCIA = re.compile(r"^[A-Za-z0-9._/-]+(#[A-Za-z0-9._-]+)?$")

PATRON_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
PATRON_FENCE = re.compile(r"^\s*(`{3,}|~{3,})\s*(\S*)")
PATRON_CELDA_SEPARADORA = re.compile(r"^:?-+:?$")
PATRON_CONVERSION_ENUM = re.compile(r"^enum:([a-z][a-z0-9_]*)$")

CODIGOS_PROCEDENCIA = (
    "ausencia_prohibida",
    "ausencia_sin_motivo",
    "forma_no_reconocida",
    "hoja_ausente",
    "procedencia_ausente",
    "procedencia_forma_desconocida",
    "procedencia_incompleta",
    "procedencia_no_objeto",
    "sede_no_admisible",
)

CODIGOS_ANCLAS = tuple(sorted(ERRORES_DE_RESOLUCION + (
    "procedencia_ilegible",
    "valor_no_coincide",
)))

CODIGOS_PRESUPUESTO = (
    "presupuesto_ausente",
    "presupuesto_no_coincide",
    "presupuesto_no_entero",
    "presupuesto_no_resuelve",
    "presupuesto_sin_ancla",
)


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


def _celdas(linea: str) -> list[str]:
    """Las celdas de una fila de tabla Markdown. El corte es por `|` no escapado: una celda que
    contiene `\\|` es una celda y no dos."""
    partes = re.split(r"(?<!\\)\|", linea.strip())
    if partes and not partes[0].strip():
        partes = partes[1:]
    if partes and not partes[-1].strip():
        partes = partes[:-1]
    return [p.replace("\\|", "|").strip() for p in partes]


def _es_separadora(linea: str) -> bool:
    celdas = _celdas(linea)
    return bool(celdas) and all(PATRON_CELDA_SEPARADORA.fullmatch(c) for c in celdas)


def _seleccionar_por_heading(texto: str, selector: dict) -> list[Any]:
    """El nodo de un `heading_markdown` es el **cuerpo de la sección**, no la línea del título: el
    schema declara este tipo de sede para «secciones normativas». La sección termina en el próximo
    heading de nivel menor o igual."""
    lineas, fuera = texto.splitlines(), _lineas_fuera_de_fence(texto)
    buscado, nivel = selector.get("texto"), selector.get("nivel")
    nodos: list[Any] = []
    i = 0
    while i < len(lineas):
        m = PATRON_HEADING.match(lineas[i]) if fuera[i] else None
        if m and len(m.group(1)) == nivel and m.group(2).strip() == buscado:
            j = i + 1
            cuerpo: list[str] = []
            while j < len(lineas):
                otro = PATRON_HEADING.match(lineas[j]) if fuera[j] else None
                if otro and len(otro.group(1)) <= nivel:
                    break
                cuerpo.append(lineas[j])
                j += 1
            nodos.append("\n".join(cuerpo).strip("\n"))
            i = j
            continue
        i += 1
    return nodos


def _seleccionar_por_fila(texto: str, selector: dict) -> list[Any]:
    """La celda de la columna pedida, en cada fila cuya primera celda es la clave. Una tabla que no
    tiene esa columna no aporta nodos: la sede más común del repo tiene la misma clave en varias
    tablas y solo algunas la describen en esa dimensión."""
    lineas, fuera = texto.splitlines(), _lineas_fuera_de_fence(texto)
    clave, columna = selector.get("clave_primera_celda"), selector.get("encabezado_de_columna")
    nodos: list[Any] = []
    i = 0
    while i < len(lineas) - 1:
        if not (fuera[i] and lineas[i].strip().startswith("|") and _es_separadora(lineas[i + 1])):
            i += 1
            continue
        encabezados = _celdas(lineas[i])
        indice = encabezados.index(columna) if columna in encabezados else None
        j = i + 2
        while j < len(lineas) and fuera[j] and lineas[j].strip().startswith("|"):
            celdas = _celdas(lineas[j])
            if indice is not None and celdas and celdas[0] == clave and indice < len(celdas):
                nodos.append(celdas[indice])
            j += 1
        i = j
    return nodos


def _bloques_cercados(texto: str, lenguaje: str) -> list[str]:
    bloques: list[str] = []
    cerca: str | None = None
    acumulado: list[str] = []
    coincide = False
    for linea in texto.splitlines():
        m = PATRON_FENCE.match(linea)
        if cerca is None:
            if m:
                cerca = m.group(1)[0] * 3
                coincide = m.group(2) == lenguaje
                acumulado = []
            continue
        if m and m.group(1).startswith(cerca):
            if coincide:
                bloques.append("\n".join(acumulado))
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


def _seleccionar_por_clave(texto: str, selector: dict) -> tuple[list[Any], str | None]:
    """Los documentos estructurados de la sede —el archivo entero, o cada bloque cercado del
    lenguaje declarado— y, en cada uno, el valor de la ruta. Cuando ese valor es una **lista**, sus
    elementos son los nodos: una sede genuinamente multivaluada se declara así y no como varios
    documentos."""
    formato = selector.get("formato")
    lenguaje = selector.get("lenguaje_del_bloque")
    documentos = _bloques_cercados(texto, lenguaje) if isinstance(lenguaje, str) else [texto]
    nodos: list[Any] = []
    for bruto in documentos:
        dato, error = _parsear(bruto, formato)
        if error:
            return [], error
        valor = _bajar(dato, selector.get("ruta"))
        if valor is _SIN_VALOR:
            continue
        nodos.extend(valor) if isinstance(valor, list) else nodos.append(valor)
    return nodos, None


def _seleccionar_por_patron(texto: str, selector: dict) -> tuple[list[Any], str | None]:
    try:
        patron = re.compile(selector.get("patron", ""))
    except re.error as e:
        return [], f"el patrón del selector no compila: {e}"
    return [linea for linea in texto.splitlines() if patron.search(linea)], None


def _seleccionar(procedencia: dict, texto: str) -> tuple[list[Any], str | None]:
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


def _extraer(extraccion: Any, nodo: Any) -> tuple[str | None, str]:
    if not isinstance(extraccion, dict):
        return None, "extraccion_no_declarada"
    tipo = extraccion.get("tipo")
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


_tablas_de_conversion_cache: dict[str, dict[str, Any]] | None = None


def tablas_de_conversion() -> dict[str, dict[str, Any]]:
    """El mapeo texto → token de cada `enum:<nombre>`, leído de `x-conversiones` del schema. **No se
    reescribe acá**: una segunda tabla distinta de la que usó quien pobló la matriz pondría en rojo
    hojas que están bien, y ese es el defecto que el bloque del schema existe para cerrar."""
    global _tablas_de_conversion_cache
    if _tablas_de_conversion_cache is None:
        schema, error = _cargar_json(RUTA_SCHEMA)
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
    normalizados: list[str] = []
    for nodo in nodos:
        texto_nodo, causa = _extraer(procedencia.get("extraccion"), nodo)
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

class Hoja(NamedTuple):
    """Una hoja de la matriz: lo que lleva `procedencia`. **Se descubre recorriendo el schema**, no
    enumerando nombres de campo: un campo nuevo con procedencia nacería sin recorrer si la lista
    fuera manual."""

    ruta: Ruta
    definicion: str
    nodo: dict
    exige_ancla: bool
    valor_declarado: Any

    @property
    def donde(self) -> str:
        return fmt(self.ruta)


def _resolver_ref(esquema: dict, schema: dict) -> tuple[dict, str]:
    nombre = ""
    while isinstance(esquema, dict) and "$ref" in esquema:
        nombre = esquema["$ref"][len("#/$defs/"):]
        esquema = schema.get("$defs", {}).get(nombre, {})
    return esquema, nombre


def _es_hoja(esquema: dict) -> bool:
    return "procedencia" in (esquema.get("properties") or {})


def _exige_ancla(esquema: dict) -> bool:
    ref = ((esquema.get("properties") or {}).get("procedencia") or {}).get("$ref")
    return ref == "#/$defs/procedencia_anclada"


def _rama_que_valida(instancia: Any, ramas: list, schema: dict) -> dict | None:
    """La rama del `oneOf` que la instancia satisface. Se decide **validando**, no por un
    discriminador transcrito: el schema ya declara las ramas y reusar su validador evita una segunda
    lectura del mismo acoplamiento que podría discrepar.

    Cuando ninguna valida se elige la que **falla menos**, y solo si esa es única. Sin eso, un átomo
    de condición al que le falta la procedencia deja de satisfacer cualquier rama y el modo lo
    reporta como forma irreconocible: cierto, pero atribuido al lugar equivocado, porque no dice si
    perdió la procedencia, la clave o el operador. Con el mínimo único, el recorrido sigue por la
    rama que la instancia estaba tratando de ser y el problema cae con su propio nombre."""
    fallas = [(len(_validar(instancia, rama, Contexto(schema), ())), i) for i, rama in enumerate(ramas)]
    minimo = min(n for n, _ in fallas)
    candidatas = [i for n, i in fallas if n == minimo]
    return ramas[candidatas[0]] if len(candidatas) == 1 else None


def recolectar_hojas(instancia: Any, esquema: dict, schema: dict,
                     ruta: Ruta = ()) -> tuple[list[Hoja], list[Problema]]:
    esquema, nombre = _resolver_ref(esquema, schema)
    if not isinstance(esquema, dict) or not esquema:
        return [], []

    if _es_hoja(esquema):
        if not isinstance(instancia, dict):
            return [], [Problema("forma_no_reconocida", fmt(ruta),
                                 f"se esperaba una hoja y llegó `{_nombre_tipo(instancia)}`")]
        return [Hoja(ruta, nombre, instancia, _exige_ancla(esquema),
                     instancia.get("valor", _SIN_VALOR))], []

    if "oneOf" in esquema:
        rama = _rama_que_valida(instancia, esquema["oneOf"], schema)
        if rama is None:
            return [], [Problema("forma_no_reconocida", fmt(ruta),
                                 f"la instancia no satisface exactamente una rama de `{nombre}`: "
                                 "no hay forma de saber qué hojas debería llevar")]
        return recolectar_hojas(instancia, rama, schema, ruta)

    hojas: list[Hoja] = []
    problemas: list[Problema] = []
    if esquema.get("type") == "object" and isinstance(instancia, dict):
        propiedades = esquema.get("properties") or {}
        for campo in esquema.get("required", []):
            sub, _ = _resolver_ref(propiedades.get(campo, {}), schema)
            if campo not in instancia and (_es_hoja(sub) or "oneOf" in sub):
                problemas.append(Problema(
                    "hoja_ausente", fmt(ruta + (campo,)),
                    f"falta el campo `{campo}` entero: una hoja que no está no es una hoja sin sede"))
        for campo, sub in propiedades.items():
            if campo in instancia:
                sub_hojas, sub_problemas = recolectar_hojas(
                    instancia[campo], sub, schema, ruta + (campo,))
                hojas.extend(sub_hojas)
                problemas.extend(sub_problemas)
    elif esquema.get("type") == "array" and isinstance(instancia, list):
        for i, elemento in enumerate(instancia):
            sub_hojas, sub_problemas = recolectar_hojas(
                elemento, esquema.get("items", {}), schema, ruta + (i,))
            hojas.extend(sub_hojas)
            problemas.extend(sub_problemas)
    return hojas, problemas


def _pipeline_desalineado(schema: dict) -> str | None:
    """El orden que este código ejecuta contra el que el schema congela. Si divergen, los modos se
    ponen rojos: seguir con el propio sería volver a decidir el orden por cuenta propia, que es
    justo lo que `x-pipeline` existe para evitar."""
    declarado = tuple((schema.get("x-pipeline") or {}).get("orden") or ())
    if declarado != PASOS_DEL_PIPELINE:
        return (f"el pipeline del schema es {list(declarado)} y este resolutor ejecuta "
                f"{list(PASOS_DEL_PIPELINE)}")
    return None


# --- Modo `--procedencia` ---------------------------------------------------------------------

def verificar_procedencia(datos: Any, schema: dict) -> tuple[list[Problema], dict]:
    """Toda ruta hoja derivada del schema con **exactamente una** procedencia, y la marca de
    ausencia solo donde el schema la admite."""
    resumen = {"hojas": 0, "ancladas": 0, "sin_sede": 0}
    desalineado = _pipeline_desalineado(schema)
    if desalineado:
        return [Problema("forma_no_reconocida", "$", desalineado)], resumen

    hojas, problemas = recolectar_hojas(datos, schema, schema)
    resumen["hojas"] = len(hojas)
    for hoja in hojas:
        if "procedencia" not in hoja.nodo:
            problemas.append(Problema("procedencia_ausente", hoja.donde,
                                      "la hoja no declara procedencia ni marca de ausencia"))
            continue
        procedencia = hoja.nodo["procedencia"]
        if not isinstance(procedencia, dict):
            problemas.append(Problema("procedencia_no_objeto", hoja.donde,
                                      f"la procedencia llegó como `{_nombre_tipo(procedencia)}`"))
            continue
        anclada, ausente = "sede" in procedencia, "ausencia" in procedencia
        if anclada == ausente:
            problemas.append(Problema(
                "procedencia_forma_desconocida", hoja.donde,
                "la procedencia no es ni la forma anclada ni la marca de ausencia"
                if not anclada else "la procedencia declara sede y ausencia a la vez"))
            continue
        if ausente:
            resumen["sin_sede"] += 1
            if hoja.exige_ancla:
                problemas.append(Problema(
                    "ausencia_prohibida", hoja.donde,
                    f"`{hoja.definicion}` no admite la marca de ausencia: este campo se declara "
                    "contra una sede o no se declara"))
            elif not str(procedencia.get("ausencia") or "").strip():
                problemas.append(Problema("ausencia_sin_motivo", hoja.donde,
                                          "la marca de ausencia no dice por qué no hay sede"))
            continue
        resumen["ancladas"] += 1
        faltantes = [c for c in CAMPOS_DE_PROCEDENCIA_ANCLADA if c not in procedencia]
        if faltantes:
            problemas.append(Problema("procedencia_incompleta", hoja.donde,
                                      f"la procedencia anclada no trae {faltantes}"))
        if _sede_no_admisible(procedencia.get("sede")):
            problemas.append(Problema(
                "sede_no_admisible", hoja.donde,
                f"la sede `{procedencia.get('sede')}` es un artefacto de este flujo: una hoja que "
                "se cita a sí misma coincide siempre consigo misma"))
    return problemas, resumen


def _campos_de_procedencia_anclada() -> tuple[str, ...]:
    schema, error = _cargar_json(RUTA_SCHEMA)
    if error:
        return ()
    return tuple(schema.get("$defs", {}).get("procedencia_anclada", {}).get("required", []))


CAMPOS_DE_PROCEDENCIA_ANCLADA = _campos_de_procedencia_anclada()


# --- Modo `--anclas` --------------------------------------------------------------------------

def verificar_anclas(datos: Any, schema: dict, raiz: Path) -> tuple[list[Problema], dict]:
    """Cada hoja anclada resuelta contra su sede, y su valor declarado cotejado contra el resuelto.
    Las hojas con marca de ausencia se cuentan como adjudicación pendiente y **no** se le pasan al
    resolutor."""
    resumen = {"hojas": 0, "resueltas": 0, "pendientes": 0, "nodos": 0}
    desalineado = _pipeline_desalineado(schema)
    if desalineado:
        return [Problema("procedencia_ilegible", "$", desalineado)], resumen

    # Una hoja que falta es asunto de `--procedencia`: acá no hay nada que resolver. Lo que sí queda
    # es la forma irreconocible, traducida al código de este modo — un problema que el modo puede
    # emitir y que su catálogo no nombra sería un código sin mutante, o sea sin forma de comprobar
    # que pueda ponerse rojo.
    hojas, estructurales = recolectar_hojas(datos, schema, schema)
    problemas = [Problema("procedencia_ilegible", p.donde, p.mensaje)
                 for p in estructurales if p.codigo != "hoja_ausente"]
    resumen["hojas"] = len(hojas)
    for hoja in hojas:
        procedencia = hoja.nodo.get("procedencia")
        if not isinstance(procedencia, dict) or ("sede" in procedencia) == ("ausencia" in procedencia):
            problemas.append(Problema("procedencia_ilegible", hoja.donde,
                                      "la procedencia no es una de las dos formas declaradas: no "
                                      "hay nada que resolver ni nada que clasificar"))
            continue
        if "ausencia" in procedencia:
            resumen["pendientes"] += 1
            continue
        resultado = resolver_procedencia(procedencia, raiz)
        if not resultado.ok:
            problemas.append(Problema(resultado.error, hoja.donde,
                                      f"{resultado.detalle} [{resultado.causa}]"))
            continue
        resumen["resueltas"] += 1
        resumen["nodos"] += resultado.cardinalidad_observada or 0
        if hoja.valor_declarado is _SIN_VALOR:
            continue
        if not _mismo(hoja.valor_declarado, resultado.valor):
            problemas.append(Problema(
                "valor_no_coincide", hoja.donde,
                f"la sede dice {resultado.valor!r} y la matriz declara "
                f"{hoja.valor_declarado!r}"))
    return problemas, resumen


# --- Modo `--presupuesto-contractual` ----------------------------------------------------------

def _campo_del_presupuesto(schema: dict) -> tuple[str | None, str]:
    """Cuál de las hojas del punto es el presupuesto de espera contractual: la única cuyo tipo es
    `hoja_entero_anclada`. Se deriva del schema en vez de escribir el nombre: si mañana hubiera dos
    enteros anclados, el modo lo dice en vez de comprobar el que no era."""
    propiedades = schema.get("$defs", {}).get("punto", {}).get("properties", {})
    candidatos = [c for c, sub in propiedades.items()
                  if sub.get("$ref") == "#/$defs/hoja_entero_anclada"]
    if len(candidatos) == 1:
        return candidatos[0], ""
    return None, (f"el schema tiene {len(candidatos)} hojas `hoja_entero_anclada` "
                  f"({candidatos}): no hay una sola que sea el presupuesto contractual")


def verificar_presupuesto(datos: Any, schema: dict, raiz: Path) -> tuple[list[Problema], dict]:
    resumen = {"puntos": 0, "resueltos": 0, "campo": None}
    campo, error = _campo_del_presupuesto(schema)
    if campo is None:
        return [Problema("presupuesto_ausente", "$", error)], resumen
    resumen["campo"] = campo

    puntos = datos.get("puntos") if isinstance(datos, dict) else None
    problemas: list[Problema] = []
    for i, punto in enumerate(puntos if isinstance(puntos, list) else []):
        if not isinstance(punto, dict):
            continue
        resumen["puntos"] += 1
        donde = fmt(("puntos", i, campo))
        hoja = punto.get(campo)
        if not isinstance(hoja, dict):
            problemas.append(Problema(
                "presupuesto_ausente", donde,
                "el punto no declara el presupuesto de espera contractual: la ausencia del campo "
                "entero no puede pasar como hoja sin sede"))
            continue
        valor = hoja.get("valor", _SIN_VALOR)
        if not isinstance(valor, int) or isinstance(valor, bool):
            problemas.append(Problema("presupuesto_no_entero", donde,
                                      f"el presupuesto declarado es {valor!r} y tiene que ser un "
                                      "entero de segundos"))
        procedencia = hoja.get("procedencia")
        if isinstance(procedencia, dict) and "ausencia" in procedencia:
            problemas.append(Problema("presupuesto_sin_ancla", donde,
                                      "el presupuesto contractual no admite la marca de ausencia"))
            continue
        if not isinstance(procedencia, dict) or "sede" not in procedencia:
            problemas.append(Problema("presupuesto_sin_ancla", donde,
                                      "el presupuesto no declara una procedencia anclada"))
            continue
        resultado = resolver_procedencia(procedencia, raiz)
        if not resultado.ok:
            problemas.append(Problema("presupuesto_no_resuelve", donde,
                                      f"{resultado.detalle} [{resultado.error}/{resultado.causa}]"))
            continue
        resumen["resueltos"] += 1
        if valor is not _SIN_VALOR and not _mismo(valor, resultado.valor):
            problemas.append(Problema(
                "presupuesto_no_coincide", donde,
                f"la sede dice {resultado.valor!r} y la matriz declara {valor!r}"))
    return problemas, resumen


# --- Los tres modos de aplicación --------------------------------------------------------------

def _cargar_matriz_y_schema(ruta_matriz: Path, etiqueta: str) -> tuple[Any, dict, int]:
    schema, error = _cargar_json(RUTA_SCHEMA)
    if error:
        print(f"FALLA  {etiqueta}: {error}")
        return None, {}, 1
    matriz, error = _cargar_json(ruta_matriz)
    if error:
        print(f"FALLA  {etiqueta}: {error}")
        return None, {}, 1
    return matriz, schema, 0


def modo_procedencia(ruta_matriz: Path) -> int:
    matriz, schema, codigo = _cargar_matriz_y_schema(ruta_matriz, "procedencia")
    if codigo:
        return codigo
    problemas, resumen = verificar_procedencia(matriz, schema)
    if problemas:
        _informar(problemas, f"{ruta_matriz.name}: procedencia de las hojas")
        return 1
    print(f"OK     {ruta_matriz.name}: {resumen['hojas']} hojas, cada una con su procedencia "
          f"({resumen['ancladas']} ancladas)")
    print(f"OK     {resumen['sin_sede']} hojas sin sede, todas en campos que admiten la marca y "
          "todas con su motivo escrito")
    print()
    print("RESULTADO: OK")
    return 0


def modo_anclas(ruta_matriz: Path, raiz: Path) -> int:
    matriz, schema, codigo = _cargar_matriz_y_schema(ruta_matriz, "anclas")
    if codigo:
        return codigo
    problemas, resumen = verificar_anclas(matriz, schema, raiz)
    if problemas:
        _informar(problemas, f"{ruta_matriz.name}: resolución de las anclas contra {raiz}")
        return 1
    print(f"OK     {ruta_matriz.name}: {resumen['resueltas']} hojas ancladas resueltas contra su "
          f"sede sobre {resumen['nodos']} nodos seleccionados")
    print(f"OK     {resumen['pendientes']} hojas con marca de ausencia, clasificadas como "
          "adjudicación pendiente y no resueltas")
    print()
    print("RESULTADO: OK")
    return 0


def modo_presupuesto_contractual(ruta_matriz: Path, raiz: Path) -> int:
    matriz, schema, codigo = _cargar_matriz_y_schema(ruta_matriz, "presupuesto-contractual")
    if codigo:
        return codigo
    problemas, resumen = verificar_presupuesto(matriz, schema, raiz)
    if problemas:
        _informar(problemas, f"{ruta_matriz.name}: presupuesto de espera contractual")
        return 1
    print(f"OK     {ruta_matriz.name}: los {resumen['puntos']} puntos declaran `{resumen['campo']}` "
          f"y los {resumen['resueltos']} resuelven contra su sede con el valor declarado")
    print()
    print("RESULTADO: OK")
    return 0


# --- Autotests de los tres modos ---------------------------------------------------------------
#
# Los casos se generan desde un único fixture conforme y sintético: `skill-anclada` no existe en el
# árbol real. Un fixture copiado de la matriz real haría que el resolutor y el dato acordaran entre
# sí, y un resolutor ajustado hasta que la matriz real pase hereda la interpretación de esa matriz.

DIR_FIXTURES_ANCLAS = REPO / "scripts" / "fixtures-matriz" / "anclas"
CONFORME_ANCLAS = DIR_FIXTURES_ANCLAS / "conforme"


class CasoDeAncla(NamedTuple):
    codigo: str | None      # el problema que el caso tiene que disparar; None = caso conforme
    descripcion: str
    mutar_matriz: Any       # (datos) -> datos, o None
    mutar_arbol: Any        # (raíz) -> None, o None
    sin_sede: int | None    # el conteo de hojas sin sede que el caso fija, cuando lo fija


def _proc(datos: dict, campo: str) -> dict:
    return datos["puntos"][0][campo]["procedencia"]


def _intento(datos: dict) -> dict:
    return datos["puntos"][0]["trabajos_delegados"][0]["intentos"][0]


def _atomo(datos: dict, i: int = 0) -> dict:
    return datos["puntos"][0]["condicion_de_existencia"]["operandos"][i]


def _celda_de_perfil_efectivo(raiz: Path) -> None:
    """La segunda tabla deja de decir lo mismo que la primera: los dos nodos que el punto colapsa
    con `unico_si_iguales` pasan a convertir a tokens distintos."""
    ruta = raiz / "skills" / "skill-anclada" / "reference.md"
    texto = ruta.read_text(encoding="utf-8")
    ruta.write_text(texto.replace("| explorador | read-only |", "| explorador | workspace-write |"),
                    encoding="utf-8")


CASOS_PROCEDENCIA = (
    CasoDeAncla(None, "el fixture conforme: toda hoja con su procedencia y una ausencia legítima",
                None, None, 1),
    CasoDeAncla(None, "una segunda ausencia legítima en otro campo que la admite sigue en verde",
                _mutando(lambda d: d["puntos"][0]["requiere_confirmacion_del_usuario"].__setitem__(
                    "procedencia", {"ausencia": "el contrato no declara el gate punto por punto"})),
                None, 2),
    CasoDeAncla("hoja_ausente", "se omite el campo entero del presupuesto contractual",
                _mutando(lambda d: d["puntos"][0].pop("presupuesto_de_espera_contractual")),
                None, None),
    CasoDeAncla("procedencia_ausente", "se retira la procedencia de los permisos efectivos",
                _mutando(lambda d: d["puntos"][0]["permisos_efectivos"].pop("procedencia")),
                None, None),
    CasoDeAncla("procedencia_ausente", "se retira la procedencia del transporte del intento",
                _mutando(lambda d: _intento(d)["transporte"].pop("procedencia")), None, None),
    CasoDeAncla("procedencia_ausente", "se retira la procedencia del presupuesto contractual",
                _mutando(lambda d: d["puntos"][0]["presupuesto_de_espera_contractual"].pop(
                    "procedencia")), None, None),
    CasoDeAncla("procedencia_ausente", "se retira la procedencia del átomo de la condición",
                _mutando(lambda d: _atomo(d).pop("procedencia")), None, None),
    CasoDeAncla("procedencia_ausente", "se retira la procedencia del ancla de invocación (entrada)",
                _mutando(lambda d: d["puntos"][0]["ancla_de_invocacion"].pop("procedencia")),
                None, None),
    CasoDeAncla("procedencia_ausente", "se retira la procedencia del contrato de salida",
                _mutando(lambda d: d["puntos"][0]["contrato_de_salida"].pop("procedencia")),
                None, None),
    CasoDeAncla("ausencia_prohibida", "el dueño pasa a declarar ausencia de sede",
                _mutando(lambda d: d["puntos"][0]["dueno"].__setitem__(
                    "procedencia", {"ausencia": "nadie escribió quién es el dueño"})), None, None),
    CasoDeAncla("ausencia_prohibida", "el fallback pasa a declarar ausencia de sede",
                _mutando(lambda d: d["puntos"][0]["fallback"].__setitem__(
                    "procedencia", {"ausencia": "el fallback no está escrito en ninguna sede"})),
                None, None),
    CasoDeAncla("ausencia_prohibida", "la autoridad final pasa a declarar ausencia de sede",
                _mutando(lambda d: d["puntos"][0]["autoridad_final"].__setitem__(
                    "procedencia", {"ausencia": "la autoridad final no está escrita"})), None, None),
    CasoDeAncla("ausencia_prohibida", "el presupuesto contractual pasa a declarar ausencia de sede",
                _mutando(lambda d: d["puntos"][0]["presupuesto_de_espera_contractual"].__setitem__(
                    "procedencia", {"ausencia": "el deadline no está escrito"})), None, None),
    CasoDeAncla("ausencia_sin_motivo", "la ausencia legítima se queda sin motivo",
                _mutando(lambda d: _intento(d)["deadline_declarado"]["procedencia"].__setitem__(
                    "ausencia", "   ")), None, None),
    CasoDeAncla("procedencia_no_objeto", "la procedencia llega como cadena suelta",
                _mutando(lambda d: d["puntos"][0]["dueno"].__setitem__(
                    "procedencia", "skills/skill-anclada/SKILL.md")), None, None),
    CasoDeAncla("procedencia_forma_desconocida", "la procedencia declara sede y ausencia a la vez",
                _mutando(lambda d: _proc(d, "dueno").__setitem__("ausencia", "por las dudas")),
                None, None),
    CasoDeAncla("procedencia_forma_desconocida", "la procedencia no declara ni sede ni ausencia",
                _mutando(lambda d: d["puntos"][0]["dueno"].__setitem__("procedencia", {})),
                None, None),
    CasoDeAncla("procedencia_incompleta", "la procedencia anclada se queda sin cardinalidad",
                _mutando(lambda d: _proc(d, "dueno").pop("cardinalidad")), None, None),
    CasoDeAncla("sede_no_admisible", "una hoja se ancla en la propia matriz del flujo",
                _mutando(lambda d: _proc(d, "dueno").__setitem__(
                    "sede", "scripts/matriz-despachos.json")), None, None),
    CasoDeAncla("sede_no_admisible", "una hoja se ancla en su propia ubicación del corpus de fixtures",
                _mutando(lambda d: _proc(d, "dueno").__setitem__(
                    "sede", "scripts/fixtures-matriz/anclas/conforme/matriz.json")), None, None),
    CasoDeAncla("forma_no_reconocida", "la condición de existencia deja de ser una de sus formas",
                _mutando(lambda d: d["puntos"][0].__setitem__(
                    "condicion_de_existencia", {"tipo": "quizas"})), None, None),
)

CASOS_ANCLAS = (
    CasoDeAncla(None, "el fixture conforme resuelve entero, incluida la hoja de dos nodos que "
                      "declara `exactamente_n` n=2 y colapsa a valor único porque coinciden",
                None, None, None),
    CasoDeAncla("sede_inexistente", "una hoja se ancla en un archivo que no está en el árbol",
                _mutando(lambda d: _proc(d, "dueno").__setitem__(
                    "sede", "skills/skill-anclada/inexistente.md")), None, None),
    CasoDeAncla("sede_no_admisible",
                "una hoja se ancla en la matriz del flujo, que ni siquiera existe bajo esta raíz: "
                "la admisibilidad se comprueba antes que la existencia",
                _mutando(lambda d: _proc(d, "dueno").__setitem__(
                    "sede", "scripts/matriz-despachos.json")), None, None),
    CasoDeAncla("selector_sin_resultado", "el selector apunta a una fila que ninguna tabla tiene",
                _mutando(lambda d: _proc(d, "autoridad_final")["selector"].__setitem__(
                    "clave_primera_celda", "inexistente")), None, None),
    CasoDeAncla("selector_sin_resultado", "el átomo de la condición apunta a una clave inexistente",
                _mutando(lambda d: _atomo(d)["procedencia"]["selector"].__setitem__(
                    "ruta", ["co_explore_inexistente"])), None, None),
    CasoDeAncla("cardinalidad_no_coincide",
                "por exceso: la hoja de dos nodos pasa a declarar `exactamente_una`",
                _mutando(lambda d: _proc(d, "permisos_efectivos").__setitem__(
                    "cardinalidad", {"tipo": "exactamente_una"})), None, None),
    CasoDeAncla("cardinalidad_no_coincide",
                "por defecto: la hoja de dos nodos pasa a declarar `exactamente_n` con n=3",
                _mutando(lambda d: _proc(d, "permisos_efectivos")["cardinalidad"].__setitem__("n", 3)),
                None, None),
    CasoDeAncla("colapso_no_unico",
                "las dos filas dejan de decir lo mismo y `unico_si_iguales` no puede elegir una",
                None, _celda_de_perfil_efectivo, None),
    CasoDeAncla("conversion_fallida", "enum sin tabla: el rol pasa a convertir con `enum:rol`",
                _mutando(lambda d: _proc(d, "rol").__setitem__("conversion", "enum:rol")), None, None),
    CasoDeAncla("conversion_fallida", "enum sin par: la variante pasa a convertir con `enum:familia`",
                _mutando(lambda d: _proc(d, "variante").__setitem__("conversion", "enum:familia")),
                None, None),
    CasoDeAncla("conversion_fallida",
                "la conversión recibe el valor crudo y no el normalizado: sin `minusculas`, "
                "`Conductor` no tiene par en la tabla",
                _mutando(lambda d: _proc(d, "autoridad_final").__setitem__("normalizacion", "ninguna")),
                None, None),
    CasoDeAncla("conversion_fallida", "número: el rol pasa a convertir a entero",
                _mutando(lambda d: _proc(d, "rol").__setitem__("conversion", "entero")), None, None),
    CasoDeAncla("conversion_fallida", "booleano: la clave extraída deja de ser un booleano",
                _mutando(lambda d: _proc(d, "requiere_confirmacion_del_usuario")[
                    "extraccion"].__setitem__("clave", ["gate"])), None, None),
    CasoDeAncla("conversion_fallida", "referencia: el contrato de salida apunta a una celda con espacios",
                _mutando(lambda d: _proc(d, "contrato_de_salida")["selector"].__setitem__(
                    "encabezado_de_columna", "familia")), None, None),
    CasoDeAncla("conversion_fallida", "la extracción por captura no casa con el nodo seleccionado",
                _mutando(lambda d: _proc(d, "skill")["extraccion"].__setitem__(
                    "patron", "^nombre: (.+)$")), None, None),
    CasoDeAncla("valor_no_coincide", "se sustituye el rol por otro plausible conservando la procedencia",
                _mutando(lambda d: d["puntos"][0]["rol"].__setitem__("valor", "explorer")), None, None),
    CasoDeAncla("valor_no_coincide", "tipo mal declarado: el booleano se declara como el entero 0",
                _mutando(lambda d: d["puntos"][0]["requiere_confirmacion_del_usuario"].__setitem__(
                    "valor", 0)), None, None),
    CasoDeAncla("valor_no_coincide",
                "el orden se aplica antes de normalizar: con `documento`, las señales salen en el "
                "orden del documento y no en el lexicográfico de su valor normalizado",
                _mutando(lambda d: _proc(d, "senales_de_deteccion")["cardinalidad"].__setitem__(
                    "orden", "documento")), None, None),
    CasoDeAncla("valor_no_coincide",
                "el orden se aplica después de convertir: con `documento`, los modos salen en el "
                "orden de sus tokens y no en el de sus textos normalizados",
                _mutando(lambda d: _proc(d, "modos")["cardinalidad"].__setitem__(
                    "orden", "documento")), None, None),
    CasoDeAncla("valor_no_coincide", "el átomo de la condición declara el valor que la sede no dice",
                _mutando(lambda d: _atomo(d).__setitem__("valor", "off")), None, None),
    CasoDeAncla("procedencia_ilegible", "la procedencia de una hoja deja de ser un objeto",
                _mutando(lambda d: d["puntos"][0]["dueno"].__setitem__("procedencia", "SKILL.md")),
                None, None),
    CasoDeAncla("procedencia_ilegible",
                "la condición de existencia deja de ser una de sus formas: sus hojas dejan de ser "
                "alcanzables y eso no puede pasar como resuelto",
                _mutando(lambda d: d["puntos"][0].__setitem__(
                    "condicion_de_existencia", {"tipo": "quizas"})), None, None),
)

CASOS_PRESUPUESTO = (
    CasoDeAncla(None, "el fixture conforme: el presupuesto resuelve contra su fila y coincide",
                None, None, None),
    CasoDeAncla("presupuesto_ausente", "se omite el campo entero en un punto",
                _mutando(lambda d: d["puntos"][0].pop("presupuesto_de_espera_contractual")),
                None, None),
    CasoDeAncla("presupuesto_sin_ancla", "el presupuesto pasa a declarar ausencia de sede",
                _mutando(lambda d: d["puntos"][0]["presupuesto_de_espera_contractual"].__setitem__(
                    "procedencia", {"ausencia": "el deadline no está escrito"})), None, None),
    CasoDeAncla("presupuesto_no_coincide",
                "se sustituye el valor por otro plausible —el de la otra fila— conservando la procedencia",
                _mutando(lambda d: d["puntos"][0]["presupuesto_de_espera_contractual"].__setitem__(
                    "valor", 900)), None, None),
    CasoDeAncla("presupuesto_no_entero", "el presupuesto se declara como el texto de su sede",
                _mutando(lambda d: d["puntos"][0]["presupuesto_de_espera_contractual"].__setitem__(
                    "valor", "600")), None, None),
    CasoDeAncla("presupuesto_no_resuelve", "el selector apunta a una columna que la tabla no tiene",
                _mutando(lambda d: _proc(d, "presupuesto_de_espera_contractual")[
                    "selector"].__setitem__("encabezado_de_columna", "inexistente")), None, None),
)


def _correr_caso_de_ancla(caso: CasoDeAncla, verificar) -> tuple[list[Problema], dict]:
    """Cada caso corre sobre una copia temporal del fixture: los que mutan el árbol escriben
    archivos, y hacerlo sobre el fixture congelado lo dejaría mutado si el proceso muriera."""
    schema, error = _cargar_json(RUTA_SCHEMA)
    if error:
        raise FileNotFoundError(error)
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "arbol"
        shutil.copytree(CONFORME_ANCLAS, raiz)
        datos = json.loads((raiz / "matriz.json").read_text(encoding="utf-8"))
        if caso.mutar_matriz is not None:
            datos = caso.mutar_matriz(datos)
        if caso.mutar_arbol is not None:
            caso.mutar_arbol(raiz)
        return verificar(datos, schema, raiz)


def _bloque_de_autotest(nombre: str, casos: tuple[CasoDeAncla, ...], verificar,
                        catalogo: tuple[str, ...]) -> list[tuple[str, bool, str]]:
    resultados: list[tuple[str, bool, str]] = []

    # [A] El control positivo, **por modo y no por task**: un modo cuyos casos son todos negativos
    # lo satisface una implementación que rechace cualquier entrada.
    conformes = [c for c in casos if c.codigo is None]
    fallas: list[str] = []
    for caso in conformes:
        problemas, resumen = _correr_caso_de_ancla(caso, verificar)
        if problemas:
            fallas.append(f"{caso.descripcion} — {problemas[0]}")
        elif caso.sin_sede is not None and resumen.get("sin_sede") != caso.sin_sede:
            fallas.append(f"{caso.descripcion} — {resumen.get('sin_sede')} hojas sin sede, "
                          f"esperadas {caso.sin_sede}")
    resultados.append((
        f"A/{nombre}", not fallas,
        f"control positivo: los {len(conformes)} casos conformes de `--{nombre}` pasan"
        if not fallas else "control positivo — " + " | ".join(fallas[:3]),
    ))

    # [B] Los mutantes, cada uno rechazado **por su motivo**.
    mutantes = [c for c in casos if c.codigo is not None]
    sobrevivientes: list[str] = []
    desatribuidos: list[str] = []
    emitidos: set[str] = set()
    for caso in mutantes:
        problemas, _ = _correr_caso_de_ancla(caso, verificar)
        codigos = {p.codigo for p in problemas}
        emitidos |= codigos
        if not codigos:
            sobrevivientes.append(f"{caso.codigo}: {caso.descripcion}")
        elif caso.codigo not in codigos:
            desatribuidos.append(f"{caso.codigo}: {caso.descripcion} — rechazado por "
                                 f"{sorted(codigos)} y no por su motivo")
    problemas_b = ([f"SOBREVIVE {s}" for s in sobrevivientes]
                   + [f"SIN ATRIBUIR {d}" for d in desatribuidos])
    resultados.append((
        f"B/{nombre}", not problemas_b,
        f"{len(mutantes)} mutantes de `--{nombre}` y los {len(mutantes)} rechazados por su motivo"
        if not problemas_b else f"{len(problemas_b)} problemas: " + " | ".join(problemas_b[:5]),
    ))

    # [C] Un mutante por código: un código sin caso es una restricción que nadie comprobó que pueda
    # ponerse roja.
    ejercidos = {c.codigo for c in mutantes}
    problemas_c = [f"`{c}` está en el catálogo y ningún caso lo ejerce"
                   for c in catalogo if c not in ejercidos]
    problemas_c += [f"`{c}` lo emite el modo y no está en el catálogo"
                    for c in sorted((emitidos | ejercidos) - set(catalogo))]
    resultados.append((
        f"C/{nombre}", not problemas_c,
        f"los {len(catalogo)} códigos de `--{nombre}` tienen su caso"
        if not problemas_c else f"{len(problemas_c)} huecos: " + " | ".join(problemas_c[:5]),
    ))
    return resultados


def _cierre(titulo: str, resultados: list[tuple[str, bool, str]]) -> int:
    ok_total = True
    for identificador, ok, mensaje in resultados:
        ok_total = ok_total and ok
        print(f"[{identificador}] {'OK   ' if ok else 'FALLA'} {mensaje}")
    print()
    if ok_total:
        print(f"RESULTADO: OK — {titulo}")
        return 0
    print("RESULTADO: FALLA — ver detalle arriba")
    return 1


def _preludio_de_autotest() -> list[tuple[str, bool, str]]:
    """Lo que tiene que valer antes de correr un solo caso: que el fixture exista, que sea una matriz
    válida contra el schema —un fixture que el schema rechaza no prueba nada del resolutor— y que el
    orden del pipeline que este código ejecuta sea el que el schema congela."""
    schema, error = _cargar_json(RUTA_SCHEMA)
    if error:
        return [("0.fixture", False, error)]
    if not CONFORME_ANCLAS.is_dir():
        return [("0.fixture", False, f"no existe el fixture conforme ({CONFORME_ANCLAS})")]
    matriz, error = _cargar_json(CONFORME_ANCLAS / "matriz.json")
    if error:
        return [("0.fixture", False, error)]
    errores, _ = validar(matriz, schema)
    errores.extend(verificar_agregados(matriz, schema))
    desalineado = _pipeline_desalineado(schema)
    return [
        ("0.fixture", not errores,
         "el fixture conforme es una matriz válida contra el schema"
         if not errores else f"el fixture no valida: {errores[0]}"),
        ("0.pipeline", desalineado is None,
         f"el pipeline ejecutado es el que el schema congela: {' → '.join(PASOS_DEL_PIPELINE)}"
         if desalineado is None else desalineado),
    ]


def modo_autotest_procedencia() -> int:
    resultados = _preludio_de_autotest()
    if all(ok for _, ok, _ in resultados):
        resultados += _bloque_de_autotest(
            "procedencia", CASOS_PROCEDENCIA,
            lambda datos, schema, raiz: verificar_procedencia(datos, schema),
            CODIGOS_PROCEDENCIA)
    return _cierre("toda hoja declara procedencia o marca de ausencia, y la marca solo donde el "
                   "schema la admite", resultados)


def modo_autotest_anclas() -> int:
    resultados = _preludio_de_autotest()
    if all(ok for _, ok, _ in resultados):
        resultados += _bloque_de_autotest("anclas", CASOS_ANCLAS, verificar_anclas, CODIGOS_ANCLAS)
        resultados += _bloque_de_autotest("presupuesto-contractual", CASOS_PRESUPUESTO,
                                          verificar_presupuesto, CODIGOS_PRESUPUESTO)
    return _cierre("el resolutor extrae de la sede lo que la matriz declara, y cada mutante cae por "
                   "su motivo", resultados)


# ---------------------------------------------------------------------------------------------
# Condiciones de existencia: evaluación por escenario y cobertura de ramas y valores.
#
# Los conectores (`y`, `o`, `no`) son estructura y los átomos son las hojas: la condición se
# **parsea como árbol** y se evalúa nodo a nodo, sin colapsarla a una cadena ni a un predicado
# opaco. Dos decisiones que gobiernan todo lo de abajo:
#
# 1. **La evaluación no cortocircuita.** `y` con un operando falso sigue evaluando los demás, y `o`
#    con uno verdadero también. Un evaluador perezoso es correcto para el resultado y **miente para
#    la cobertura**: los operandos que nunca llega a mirar quedarían reportados como no ejercidos
#    aunque el escenario los ejerza, y peor, un operando muerto pasaría por cubierto.
# 2. **Mundo cerrado para las capacidades, mundo declarado para la configuración.** Una capacidad
#    que el escenario no enumera está ausente —`no_disponible` es verdadero y eso es legítimo, no un
#    escenario incompleto—; una clave de configuración que el escenario no declara deja el átomo
#    **indecidible** y el modo se pone rojo. La asimetría es deliberada: la lista de capacidades es
#    el conjunto entero de lo que hay, mientras que una clave sin declarar no dice si el autor la
#    quiso vacía, la quiso en su default o se la olvidó.
# ---------------------------------------------------------------------------------------------

DIR_FIXTURES_CONDICIONES = REPO / "scripts" / "fixtures-matriz" / "condiciones"
CONFORME_CONDICIONES = DIR_FIXTURES_CONDICIONES / "conforme"

# Los escenarios viajan **con** la matriz y no dentro: el schema de la matriz es cerrado y no tiene
# dónde alojarlos, y hornearlos en este script los ataría a las claves de una matriz concreta. El
# archivo se deriva de la ruta de la matriz para que no haya que declararlo dos veces.
SUFIJO_ESCENARIOS = "-escenarios"

VERSION_ESCENARIOS = "1.0.0"

SCHEMA_ESCENARIOS = {
    "type": "object",
    "additionalProperties": False,
    "required": ["version", "escenarios"],
    "properties": {
        "version": {"const": VERSION_ESCENARIOS},
        "escenarios": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/escenario"}},
    },
    "$defs": {
        "escenario": {
            "type": "object",
            "additionalProperties": False,
            "required": ["id", "descripcion", "configuracion", "capacidades", "puntos_activos"],
            "properties": {
                "id": {"type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$"},
                "descripcion": {"type": "string", "minLength": 1},
                # Las claves son libres —las fija la matriz, no este schema— y sus valores tienen
                # que ser cadenas. Eso último lo comprueba `_leer_corpus`: el validador de acá
                # soporta `additionalProperties` como booleano y no como sub-esquema, y ensancharlo
                # tocaría el validador que los seis modos anteriores ya usan.
                "configuracion": {"type": "object"},
                "capacidades": {"type": "array", "uniqueItems": True,
                                "items": {"type": "string", "minLength": 1}},
                "puntos_activos": {"type": "array", "uniqueItems": True,
                                   "items": {"type": "string", "minLength": 1}},
            },
        },
    },
}

# Lo que los dos modos comparten: leer la matriz, leer los escenarios y comprobar que el par sea
# evaluable. Que el catálogo sea común no es cosmética — un modo que ignorara en silencio un
# escenario mal formado daría cobertura completa sobre un corpus que no evaluó.
CODIGOS_BASE_CONDICIONES = CODIGOS_DE_ESTRUCTURA + (
    "capacidad_no_referenciada",
    "clave_no_referenciada",
    "clave_sin_valor",
    "condicion_ausente",
    "condicion_invalida",
    "configuracion_no_cadena",
    "escenario_duplicado",
    "escenarios_invalidos",
    "id_ausente",
    "id_duplicado",
    "punto_desconocido",
)

CODIGOS_CONDICIONES = tuple(sorted(CODIGOS_BASE_CONDICIONES + (
    "escenario_activa_todos",
    "escenario_no_coincide",
)))

CODIGOS_COBERTURA = tuple(sorted(CODIGOS_BASE_CONDICIONES + (
    "rama_sin_cubrir",
    "valor_sin_ejercer",
)))

CAMPO_CONDICION = "condicion_de_existencia"
DEF_CONDICION = "#/$defs/condicion"


def ruta_de_escenarios(ruta_matriz: Path) -> Path:
    """`scripts/matriz-despachos.json` → `scripts/matriz-despachos-escenarios.json`."""
    return ruta_matriz.with_name(ruta_matriz.stem + SUFIJO_ESCENARIOS + ruta_matriz.suffix)


def _operadores(schema: dict, cual: str) -> tuple[str, ...]:
    """El vocabulario de operadores **se deriva del schema**. Transcribirlo acá lo declararía en dos
    lugares, y el que envejece es siempre la copia."""
    return tuple((schema.get("$defs", {}).get(cual) or {}).get("enum") or ())


class Corpus(NamedTuple):
    """La matriz y sus escenarios, ya comprobados como evaluables."""

    puntos: list[tuple[str, dict]]          # (id del punto, su condición)
    escenarios: list[dict]
    indecidibles: set[tuple[str, str]]      # (id de escenario, clave) sin valor utilizable


def _ruta_de_condicion(ruta: Ruta) -> str:
    return CAMPO_CONDICION + fmt(ruta)[1:]


def _donde(punto: str, ruta: Ruta) -> str:
    return f"{punto} · {_ruta_de_condicion(ruta)}"


def _nodos(condicion: dict, ruta: Ruta = ()) -> list[tuple[Ruta, dict]]:
    """Todos los nodos del árbol en preorden, con su ruta. Presupone una condición ya validada
    contra `#/$defs/condicion`."""
    salida = [(ruta, condicion)]
    tipo = condicion.get("tipo")
    if tipo in ("y", "o"):
        for i, operando in enumerate(condicion.get("operandos") or []):
            salida.extend(_nodos(operando, ruta + ("operandos", i)))
    elif tipo == "no":
        salida.extend(_nodos(condicion["operando"], ruta + ("operando",)))
    return salida


def _atomos(condicion: dict) -> list[tuple[Ruta, dict]]:
    return [(ruta, nodo) for ruta, nodo in _nodos(condicion) if nodo.get("tipo") == "atomo"]


def _leer_corpus(datos: Any, schema: dict,
                 escenarios: Any) -> tuple[Corpus | None, list[Problema]]:
    """La matriz y los escenarios, o `None` cuando el par no es evaluable. Los problemas que
    devuelve con un corpus vivo son los que no impiden evaluar —una clave de más, un punto activo
    inexistente—; los que lo impiden devuelven `None` y cortan, porque seguir evaluando sobre una
    condición irreconocible atribuiría el rojo al lugar equivocado."""
    problemas: list[Problema] = []
    if not isinstance(datos, dict):
        return None, [Problema("matriz_no_objeto", "$",
                               f"la matriz no es un objeto sino `{_nombre_tipo(datos)}`")]
    if not isinstance(datos.get("puntos"), list):
        return None, [Problema("puntos_no_es_arreglo", "$.puntos",
                               "la matriz no declara `puntos` como arreglo")]

    puntos: list[tuple[str, dict]] = []
    vistos: set[str] = set()
    for i, punto in enumerate(datos["puntos"]):
        donde = fmt(("puntos", i))
        if not isinstance(punto, dict):
            problemas.append(Problema("punto_no_objeto", donde,
                                      f"el punto no es un objeto sino `{_nombre_tipo(punto)}`"))
            continue
        identificador = punto.get("id")
        if not _es_cadena_util(identificador):
            problemas.append(Problema("id_ausente", donde, "el punto no declara `id`"))
            continue
        if identificador in vistos:
            problemas.append(Problema("id_duplicado", donde,
                                      f"`{identificador}` ya lo declaró otro punto"))
            continue
        vistos.add(identificador)
        if CAMPO_CONDICION not in punto:
            problemas.append(Problema("condicion_ausente", identificador,
                                      f"el punto no declara `{CAMPO_CONDICION}`"))
            continue
        condicion = punto[CAMPO_CONDICION]
        errores = _validar(condicion, {"$ref": DEF_CONDICION}, Contexto(schema), ())
        if errores:
            problemas.append(Problema("condicion_invalida", identificador,
                                      f"la condición no satisface la gramática del schema: "
                                      f"{errores[0]}"))
            continue
        puntos.append((identificador, condicion))

    errores, _ = validar(escenarios, SCHEMA_ESCENARIOS)
    if errores:
        problemas.append(Problema("escenarios_invalidos", "$",
                                  f"el archivo de escenarios no valida contra su schema: "
                                  f"{errores[0]}"))
    if problemas:
        return None, problemas

    # Cierre en las dos direcciones. Que toda clave y toda capacidad declarada la referencie algún
    # átomo es lo que caza un nombre mal tipeado: sin esta comprobación, `codex-cli` en vez de
    # `codex_cli` deja la capacidad ausente en silencio y el escenario evalúa otra cosa.
    claves = {nodo["clave"] for _, condicion in puntos for _, nodo in _atomos(condicion)
              if nodo.get("operador") in _operadores(schema, "enum_operador_comparacion")}
    capacidades = {nodo["clave"] for _, condicion in puntos for _, nodo in _atomos(condicion)
                   if nodo.get("operador") in _operadores(schema, "enum_operador_capacidad")}
    identificadores = {i for i, _ in puntos}
    indecidibles: set[tuple[str, str]] = set()
    ids_de_escenario: set[str] = set()
    for escenario in escenarios["escenarios"]:
        nombre = escenario["id"]
        if nombre in ids_de_escenario:
            problemas.append(Problema("escenario_duplicado", nombre,
                                      "dos escenarios comparten identificador"))
        ids_de_escenario.add(nombre)
        for clave, valor in escenario["configuracion"].items():
            if not isinstance(valor, str):
                problemas.append(Problema(
                    "configuracion_no_cadena", f"{nombre} · {clave}",
                    f"el valor es `{_nombre_tipo(valor)}` y los átomos comparan cadenas"))
                indecidibles.add((nombre, clave))
            elif clave not in claves:
                problemas.append(Problema(
                    "clave_no_referenciada", f"{nombre} · {clave}",
                    "la clave no la consulta ningún átomo de la matriz"))
        for capacidad in escenario["capacidades"]:
            if capacidad not in capacidades:
                problemas.append(Problema(
                    "capacidad_no_referenciada", f"{nombre} · {capacidad}",
                    "la capacidad no la consulta ningún átomo de la matriz"))
        for activo in escenario["puntos_activos"]:
            if activo not in identificadores:
                problemas.append(Problema("punto_desconocido", f"{nombre} · {activo}",
                                          "el escenario declara activo un punto que no está en la "
                                          "matriz"))
    return Corpus(puntos, escenarios["escenarios"], indecidibles), problemas


class Registro:
    """Lo que la evaluación observó. `ramas` guarda los valores que cada nodo tomó; `valores`, los
    valores que cada átomo de comparación vio en la clave que consulta."""

    def __init__(self) -> None:
        self.ramas: dict[tuple[str, Ruta], set[bool]] = {}
        self.valores: dict[tuple[str, Ruta], set[str]] = {}

    def rama(self, punto: str, ruta: Ruta, valor: bool | None) -> None:
        if valor is not None:
            self.ramas.setdefault((punto, ruta), set()).add(valor)

    def valor(self, punto: str, ruta: Ruta, texto: str) -> None:
        self.valores.setdefault((punto, ruta), set()).add(texto)


def _evaluar_atomo(nodo: dict, ruta: Ruta, punto: str, escenario: dict, schema: dict,
                   corpus: Corpus, problemas: list[Problema], registro: Registro) -> bool | None:
    operador, clave = nodo["operador"], nodo["clave"]
    if operador in _operadores(schema, "enum_operador_capacidad"):
        presente = clave in escenario["capacidades"]
        return presente if operador == "disponible" else not presente

    if (escenario["id"], clave) in corpus.indecidibles:
        return None  # el problema ya lo emitió `_leer_corpus`; repetirlo acá lo contaría dos veces
    if clave not in escenario["configuracion"]:
        problemas.append(Problema(
            "clave_sin_valor", f"{escenario['id']} · {_donde(punto, ruta)}",
            f"el escenario no declara la clave `{clave}` y el átomo no se puede decidir"))
        return None

    observado = escenario["configuracion"][clave]
    registro.valor(punto, ruta, observado)
    declarado = nodo["valor"]
    # Cotejo exacto, carácter por carácter: acá no hay normalización. La que había la aplicó el
    # resolutor al extraer el valor de su sede, y hacerla dos veces con criterios distintos daría
    # dos resultados para el mismo par.
    if operador == "igual":
        return observado == declarado
    if operador == "distinto":
        return observado != declarado
    if operador == "en":
        return observado in declarado
    return observado not in declarado


def _evaluar(condicion: dict, ruta: Ruta, punto: str, escenario: dict, schema: dict,
             corpus: Corpus, problemas: list[Problema], registro: Registro) -> bool | None:
    tipo = condicion["tipo"]
    if tipo == "siempre":
        valor: bool | None = True
    elif tipo == "atomo":
        valor = _evaluar_atomo(condicion, ruta, punto, escenario, schema, corpus, problemas,
                               registro)
    elif tipo in ("y", "o"):
        # Sin cortocircuito, a propósito: los operandos que un evaluador perezoso no miraría son
        # justamente los que la cobertura tiene que ver ejercidos.
        sub = [_evaluar(operando, ruta + ("operandos", i), punto, escenario, schema, corpus,
                        problemas, registro)
               for i, operando in enumerate(condicion["operandos"])]
        if any(s is None for s in sub):
            valor = None
        else:
            valor = all(sub) if tipo == "y" else any(sub)
    else:
        interno = _evaluar(condicion["operando"], ruta + ("operando",), punto, escenario, schema,
                           corpus, problemas, registro)
        valor = None if interno is None else not interno
    registro.rama(punto, ruta, valor)
    return valor


def _recorrer_escenarios(corpus: Corpus, schema: dict) -> tuple[
        list[Problema], Registro, dict[str, set[str] | None]]:
    """Evalúa cada punto en cada escenario. El tercer valor es el conjunto de puntos activos por
    escenario, o `None` cuando algún átomo quedó indecidible y el conjunto no significa nada."""
    problemas: list[Problema] = []
    registro = Registro()
    activos: dict[str, set[str] | None] = {}
    for escenario in corpus.escenarios:
        conjunto: set[str] = set()
        decidible = True
        for punto, condicion in corpus.puntos:
            valor = _evaluar(condicion, (), punto, escenario, schema, corpus, problemas, registro)
            if valor is None:
                decidible = False
            elif valor:
                conjunto.add(punto)
        activos[escenario["id"]] = conjunto if decidible else None
    return problemas, registro, activos


# --- Modo `--condiciones` ----------------------------------------------------------------------

def verificar_condiciones(datos: Any, schema: dict,
                          escenarios: Any) -> tuple[list[Problema], dict]:
    """Cada escenario produce el conjunto de puntos activos que declara, y ninguno los produce
    todos."""
    resumen = {"escenarios": 0, "puntos": 0, "activos_maximo": 0, "pares_excluyentes": 0}
    corpus, problemas = _leer_corpus(datos, schema, escenarios)
    if corpus is None:
        return problemas, resumen

    de_evaluacion, _, activos = _recorrer_escenarios(corpus, schema)
    problemas.extend(de_evaluacion)
    identificadores = {i for i, _ in corpus.puntos}
    resumen["escenarios"] = len(corpus.escenarios)
    resumen["puntos"] = len(corpus.puntos)

    for escenario in corpus.escenarios:
        conjunto = activos[escenario["id"]]
        if conjunto is None:
            continue
        resumen["activos_maximo"] = max(resumen["activos_maximo"], len(conjunto))
        declarados = set(escenario["puntos_activos"]) & identificadores
        for punto in sorted(conjunto - declarados):
            problemas.append(Problema(
                "escenario_no_coincide", f"{escenario['id']} · {punto}",
                "la condición lo activa y el escenario no lo declara activo"))
        for punto in sorted(declarados - conjunto):
            problemas.append(Problema(
                "escenario_no_coincide", f"{escenario['id']} · {punto}",
                "el escenario lo declara activo y su condición no lo activa"))
        if conjunto == identificadores and identificadores:
            problemas.append(Problema(
                "escenario_activa_todos", escenario["id"],
                f"el escenario activa los {len(identificadores)} puntos de la matriz a la vez: los "
                "modos de implementación mutuamente excluyentes dejarían de serlo"))

    completos = [c for c in activos.values() if c is not None]
    resumen["pares_excluyentes"] = sum(
        1 for a, b in itertools.combinations(sorted(identificadores), 2)
        if not any(a in c and b in c for c in completos))
    return problemas, resumen


# --- Modo `--cobertura-condiciones` -------------------------------------------------------------

class Elemento(NamedTuple):
    """Una unidad de cobertura, **derivada del corpus** y no transcrita: cada nodo del árbol aporta
    sus dos ramas y cada átomo de comparación aporta un elemento por valor declarado. Un átomo nuevo
    en la matriz nace con sus elementos y no puede pasar inadvertido."""

    clase: str          # "rama" | "valor"
    punto: str
    ruta: Ruta
    detalle: str

    @property
    def donde(self) -> str:
        return _donde(self.punto, self.ruta)


def _elementos_de_cobertura(corpus: Corpus, schema: dict) -> list[Elemento]:
    comparacion = _operadores(schema, "enum_operador_comparacion")
    elementos: list[Elemento] = []
    for punto, condicion in corpus.puntos:
        for ruta, nodo in _nodos(condicion):
            # `siempre` es constante: exigirle la rama falsa sería pedir una cobertura que ninguna
            # entrada puede dar, y una guarda que no puede ponerse verde no mide nada.
            valores = ("true",) if nodo["tipo"] == "siempre" else ("true", "false")
            elementos.extend(Elemento("rama", punto, ruta, v) for v in valores)
            if nodo.get("operador") in comparacion:
                declarados = (nodo["valor"] if isinstance(nodo["valor"], list) else [nodo["valor"]])
                elementos.extend(Elemento("valor", punto, ruta, v) for v in declarados)
    return elementos


def _sin_cubrir(elementos: list[Elemento], registro: Registro) -> list[Problema]:
    problemas: list[Problema] = []
    for elemento in elementos:
        clave = (elemento.punto, elemento.ruta)
        if elemento.clase == "rama":
            if (elemento.detalle == "true") in registro.ramas.get(clave, set()):
                continue
            problemas.append(Problema(
                "rama_sin_cubrir", elemento.donde,
                f"ningún escenario observó este nodo en `{elemento.detalle}`"))
        else:
            if elemento.detalle in registro.valores.get(clave, set()):
                continue
            problemas.append(Problema(
                "valor_sin_ejercer", elemento.donde,
                f"ningún escenario le asigna a la clave el valor `{elemento.detalle}`"))
    return problemas


def verificar_cobertura_condiciones(datos: Any, schema: dict,
                                    escenarios: Any) -> tuple[list[Problema], dict]:
    """Cada rama de cada condición observada en sus dos valores y cada valor declarado ejercido.
    Evaluar bien y cubrir del todo son criterios distintos: una rama que ningún escenario ejerce
    deja el árbol entero en verde sin haberse probado."""
    resumen = {"escenarios": 0, "elementos": 0, "ramas": 0, "valores": 0, "atomos_multivalor": 0}
    corpus, problemas = _leer_corpus(datos, schema, escenarios)
    if corpus is None:
        return problemas, resumen

    de_evaluacion, registro, _ = _recorrer_escenarios(corpus, schema)
    problemas.extend(de_evaluacion)
    elementos = _elementos_de_cobertura(corpus, schema)
    resumen["escenarios"] = len(corpus.escenarios)
    resumen["elementos"] = len(elementos)
    resumen["ramas"] = sum(1 for e in elementos if e.clase == "rama")
    resumen["valores"] = sum(1 for e in elementos if e.clase == "valor")
    por_atomo: dict[tuple[str, Ruta], int] = {}
    for elemento in elementos:
        if elemento.clase == "valor":
            clave = (elemento.punto, elemento.ruta)
            por_atomo[clave] = por_atomo.get(clave, 0) + 1
    resumen["atomos_multivalor"] = sum(1 for n in por_atomo.values() if n > 1)
    problemas.extend(_sin_cubrir(elementos, registro))
    return problemas, resumen


# --- Los dos modos de aplicación ----------------------------------------------------------------

def _cargar_par(ruta_matriz: Path, ruta_escenarios: Path | None,
                etiqueta: str) -> tuple[Any, dict, Any, Path, int]:
    schema, error = _cargar_json(RUTA_SCHEMA)
    if error:
        print(f"FALLA  {etiqueta}: {error}")
        return None, {}, None, Path(), 1
    matriz, error = _cargar_json(ruta_matriz)
    if error:
        print(f"FALLA  {etiqueta}: {error}")
        return None, {}, None, Path(), 1
    ruta = ruta_escenarios or ruta_de_escenarios(ruta_matriz)
    escenarios, error = _cargar_json(ruta)
    if error:
        print(f"FALLA  {etiqueta}: {error}")
        return None, {}, None, ruta, 1
    return matriz, schema, escenarios, ruta, 0


def modo_condiciones(ruta_matriz: Path, ruta_escenarios: Path | None) -> int:
    matriz, schema, escenarios, ruta, codigo = _cargar_par(ruta_matriz, ruta_escenarios,
                                                           "condiciones")
    if codigo:
        return codigo
    problemas, resumen = verificar_condiciones(matriz, schema, escenarios)
    if problemas:
        _informar(problemas, f"{ruta_matriz.name}: condiciones de existencia contra {ruta.name}")
        return 1
    print(f"OK     {ruta_matriz.name}: los {resumen['escenarios']} escenarios de {ruta.name} "
          f"producen su conjunto declarado de puntos activos")
    print(f"OK     ningún escenario activa los {resumen['puntos']} puntos a la vez (máximo "
          f"observado: {resumen['activos_maximo']}); {resumen['pares_excluyentes']} pares de puntos "
          "nunca coexisten")
    print()
    print("RESULTADO: OK")
    return 0


def modo_cobertura_condiciones(ruta_matriz: Path, ruta_escenarios: Path | None) -> int:
    matriz, schema, escenarios, ruta, codigo = _cargar_par(ruta_matriz, ruta_escenarios,
                                                           "cobertura-condiciones")
    if codigo:
        return codigo
    problemas, resumen = verificar_cobertura_condiciones(matriz, schema, escenarios)
    if problemas:
        _informar(problemas, f"{ruta_matriz.name}: cobertura de las condiciones contra {ruta.name}")
        return 1
    print(f"OK     {ruta_matriz.name}: los {resumen['escenarios']} escenarios cubren los "
          f"{resumen['elementos']} elementos derivados de las condiciones")
    print(f"OK     {resumen['ramas']} elementos de rama observados y {resumen['valores']} valores "
          "declarados de átomo ejercidos")
    print()
    print("RESULTADO: OK")
    return 0


# --- Autotests de los dos modos -----------------------------------------------------------------
#
# El corpus es sintético y no describe el árbol real: `skill-teta` y `skill-iota` no existen. Un
# corpus copiado de la matriz real haría que el evaluador y el dato acordaran entre sí, y un
# evaluador ajustado hasta que la matriz real pase hereda la interpretación de esa matriz.
#
# Las familias de mutantes se **derivan** del corpus —una por átomo, una por exclusión, una por
# escenario—: con un mutante por clase, un evaluador limitado a los casos elegidos para el fixture
# pasa igual y deja el resto sin inspeccionar.

class CasoDeCondicion(NamedTuple):
    codigo: str | None      # el problema que el caso tiene que disparar; None = caso conforme
    descripcion: str
    mutar_matriz: Any       # (datos) -> datos, o None
    mutar_escenarios: Any   # (escenarios) -> escenarios, o None


def _corpus_conforme() -> tuple[dict, dict]:
    matriz = json.loads((CONFORME_CONDICIONES / "matriz.json").read_text(encoding="utf-8"))
    escenarios = json.loads(
        (CONFORME_CONDICIONES / ("matriz" + SUFIJO_ESCENARIOS + ".json")).read_text(encoding="utf-8"))
    return matriz, escenarios


def _correr_caso_de_condicion(caso: CasoDeCondicion, verificar) -> tuple[list[Problema], dict]:
    """Cada caso parte de una lectura fresca del corpus: los mutantes trabajan sobre la copia en
    memoria y el fixture del repositorio no se toca nunca."""
    schema, error = _cargar_json(RUTA_SCHEMA)
    if error:
        raise FileNotFoundError(error)
    matriz, escenarios = _corpus_conforme()
    if caso.mutar_matriz is not None:
        matriz = caso.mutar_matriz(matriz)
    if caso.mutar_escenarios is not None:
        escenarios = caso.mutar_escenarios(escenarios)
    return verificar(matriz, schema, escenarios)


def _mutando_matriz(transformar):
    def aplicar(datos):
        transformar(datos)
        return datos
    return aplicar


def _condicion(datos: dict, i: int) -> dict:
    return datos["puntos"][i][CAMPO_CONDICION]


def _punto_de(datos: dict, identificador: str) -> dict:
    """Los casos fijos buscan su punto **por identificador y no por posición**: agregar un punto al
    corpus movería los índices y los mutantes pasarían a apuntar a otra condición sin que nada lo
    dijera."""
    for punto in datos["puntos"]:
        if punto["id"] == identificador:
            return punto
    raise KeyError(f"el corpus conforme no declara el punto `{identificador}`")


def _escenario(escenarios: dict, i: int) -> dict:
    return escenarios["escenarios"][i]


def _todo_siempre(datos: dict) -> dict:
    """Todas las condiciones constantes **y** todos los escenarios declarando todos los puntos: el
    invariante de los trece tiene que caer solo, sin apoyarse en el cotejo del conjunto declarado.
    Si el mutante hiciera fallar también la comparación, un modo que solo comparara conjuntos lo
    daría por cazado."""
    for punto in datos["puntos"]:
        punto[CAMPO_CONDICION] = {"tipo": "siempre",
                                  "procedencia": {"ausencia": "mutante del autotest"}}
    return datos


def _todos_activos(escenarios: dict, ids: tuple[str, ...]) -> dict:
    for escenario in escenarios["escenarios"]:
        escenario["puntos_activos"] = list(ids)
    return escenarios


def _ids_del_conforme() -> tuple[str, ...]:
    matriz, _ = _corpus_conforme()
    return tuple(p["id"] for p in matriz["puntos"])


CASOS_BASE_CONDICIONES = (
    CasoDeCondicion("matriz_no_objeto", "la matriz no es un objeto",
                    lambda datos: [], None),
    CasoDeCondicion("puntos_no_es_arreglo", "`puntos` no es un arreglo",
                    _mutando_matriz(lambda d: d.__setitem__("puntos", {})), None),
    CasoDeCondicion("punto_no_objeto", "un punto no es un objeto",
                    _mutando_matriz(lambda d: d["puntos"].__setitem__(0, "skill-teta")), None),
    CasoDeCondicion("id_ausente", "un punto sin identificador",
                    _mutando_matriz(lambda d: d["puntos"][0].pop("id")), None),
    CasoDeCondicion("id_duplicado", "dos puntos con el mismo identificador",
                    _mutando_matriz(lambda d: d["puntos"][1].__setitem__("id", d["puntos"][0]["id"])),
                    None),
    CasoDeCondicion("condicion_ausente", "un punto sin condición de existencia",
                    _mutando_matriz(lambda d: d["puntos"][0].pop(CAMPO_CONDICION)), None),
    CasoDeCondicion("condicion_invalida", "un operador fuera del vocabulario del schema",
                    _mutando_matriz(lambda d: _punto_de(d, "skill-teta-implementador-local")
                                      [CAMPO_CONDICION].__setitem__("operador", "empieza_con")),
                    None),
    CasoDeCondicion("escenarios_invalidos", "un escenario sin su conjunto de puntos activos",
                    None, lambda e: (_escenario(e, 0).pop("puntos_activos"), e)[1]),
    CasoDeCondicion("escenario_duplicado", "dos escenarios con el mismo identificador",
                    None,
                    lambda e: (_escenario(e, 1).__setitem__("id", _escenario(e, 0)["id"]), e)[1]),
    CasoDeCondicion("configuracion_no_cadena", "una clave de configuración con valor booleano",
                    None,
                    lambda e: (_escenario(e, 0)["configuracion"].__setitem__("co_explore", True),
                               e)[1]),
    CasoDeCondicion("clave_sin_valor", "un escenario que no declara una clave que un átomo consulta",
                    None,
                    lambda e: (_escenario(e, 0)["configuracion"].pop("pr_provider"), e)[1]),
    CasoDeCondicion("clave_no_referenciada", "una clave de configuración que ningún átomo consulta",
                    None,
                    lambda e: (_escenario(e, 0)["configuracion"].__setitem__("modo_fantasma", "x"),
                               e)[1]),
    CasoDeCondicion("capacidad_no_referenciada", "una capacidad que ningún átomo consulta",
                    None,
                    lambda e: (_escenario(e, 0)["capacidades"].append("transporte-fantasma"), e)[1]),
    CasoDeCondicion("punto_desconocido", "un escenario que declara activo un punto inexistente",
                    None,
                    lambda e: (_escenario(e, 0)["puntos_activos"].append("skill-omega-ausente"),
                               e)[1]),
)

CASOS_CONDICIONES = CASOS_BASE_CONDICIONES + (
    # [A] Los conformes. El primero es el corpus entero; los otros dos aíslan la combinación que más
    # se parece a un defecto y no lo es, para que el verde no dependa de leer los cuatro escenarios.
    CasoDeCondicion(None, "el corpus conforme: cada escenario produce su conjunto declarado",
                    None, None),
    CasoDeCondicion(None, "una capacidad ausente del escenario no es un escenario incompleto: "
                          "`no_disponible` es verdadero y la degradación existe",
                    None, lambda e: (_escenario(e, 1)["capacidades"].remove("mcp_bitbucket"),
                                     _escenario(e, 1)["puntos_activos"].append(
                                         "skill-iota-feedback-degradado"), e)[2]),
    CasoDeCondicion(None, "una clave presente con la cadena vacía es un valor y no una ausencia",
                    None, lambda e: (_escenario(e, 0)["configuracion"].__setitem__(
                        "review_depth", ""),
                        _escenario(e, 0)["puntos_activos"].remove(
                            "skill-teta-revision-por-profundidad"), e)[2]),
    CasoDeCondicion("escenario_no_coincide", "un conjunto declarado al que le falta un punto activo",
                    None,
                    lambda e: (_escenario(e, 0)["puntos_activos"].remove("skill-teta-siempre"),
                               e)[1]),
    CasoDeCondicion("escenario_activa_todos",
                    "todas las condiciones constantes: el conjunto declarado coincide y el "
                    "invariante cae igual",
                    _todo_siempre, lambda e: _todos_activos(e, _ids_del_conforme())),
)

def _tautologia(datos: dict) -> dict:
    """Un nodo que ningún escenario puede observar en falso, sin tocar ningún átomo: `o` entre un
    átomo y su negación. Es el **control en la dirección contraria** del caso de arriba, y hace
    falta: con un solo caso que exija la rama verdadera, un inventario de cobertura que solo pidiera
    ramas verdaderas lo pasaría igual y la mitad del criterio quedaría sin comprobar."""
    punto = _punto_de(datos, "skill-teta-implementador-local")
    atomo = punto[CAMPO_CONDICION]
    punto[CAMPO_CONDICION] = {
        "tipo": "o",
        "operandos": [atomo, {"tipo": "no", "operando": copy.deepcopy(atomo)}],
    }
    return datos


CASOS_COBERTURA = CASOS_BASE_CONDICIONES + (
    CasoDeCondicion(None, "el corpus conforme cubre cada rama y cada valor declarado", None, None),
    CasoDeCondicion("rama_sin_cubrir", "sin el primer escenario, una rama verdadera queda sin "
                                       "observar", None, lambda e: (e["escenarios"].pop(0), e)[1]),
    CasoDeCondicion("rama_sin_cubrir", "una tautología: el nodo nunca se observa en falso",
                    _tautologia, None),
    CasoDeCondicion("valor_sin_ejercer", "un valor nuevo en la lista de un átomo `en`",
                    _mutando_matriz(lambda d: _punto_de(d, "skill-teta-revision-por-profundidad")
                                      [CAMPO_CONDICION]["valor"].append("exhaustiva")),
                    None),
)


# --- Las familias derivadas ---------------------------------------------------------------------

class Derivado(NamedTuple):
    descripcion: str
    mutar_matriz: Any
    mutar_escenarios: Any
    atribucion: Any         # (problemas pertinentes) -> queja, o None si el rojo es el suyo


def _atribuir_al_punto(punto: str):
    def comprobar(problemas: list[Problema]) -> str | None:
        if any(punto in p.donde for p in problemas):
            return None
        return f"rojo en {sorted({p.donde for p in problemas})[:3]} y no en `{punto}`"
    return comprobar


_VALOR_FRESCO = "valor-que-ningun-escenario-asigna"


def _con_nodo(datos: dict, indice: int, ruta: Ruta) -> Any:
    nodo = _condicion(datos, indice)
    for tramo in ruta:
        nodo = nodo[tramo]
    return nodo


def _reemplazar_nodo(datos: dict, indice: int, ruta: Ruta, nuevo: Any) -> None:
    if not ruta:
        datos["puntos"][indice][CAMPO_CONDICION] = nuevo
        return
    padre = _con_nodo(datos, indice, ruta[:-1])
    padre[ruta[-1]] = nuevo


def _familia_por_atomo(schema: dict) -> list[Derivado]:
    """Un mutante por átomo: se le cambia el valor que compara —o el operador de capacidad— y algún
    escenario tiene que dejar de coincidir. Un átomo que sobreviva es un átomo que el conjunto de
    escenarios no discrimina: o está muerto, o los escenarios se eligieron para esquivarlo."""
    matriz, _ = _corpus_conforme()
    comparacion = _operadores(schema, "enum_operador_comparacion")
    familia: list[Derivado] = []
    for i, punto in enumerate(matriz["puntos"]):
        for ruta, nodo in _atomos(punto[CAMPO_CONDICION]):
            if nodo["operador"] in comparacion:
                nuevo = ([_VALOR_FRESCO] if isinstance(nodo["valor"], list) else _VALOR_FRESCO)
                detalle = f"el átomo pasa a comparar contra `{_VALOR_FRESCO}`"
            else:
                nuevo = ("no_disponible" if nodo["operador"] == "disponible" else "disponible")
                detalle = f"el operador de capacidad pasa a `{nuevo}`"

            def mutar(datos, i=i, ruta=ruta, nuevo=nuevo, nodo=nodo):
                campo = "valor" if nodo["operador"] in comparacion else "operador"
                _con_nodo(datos, i, ruta)[campo] = nuevo
                return datos

            familia.append(Derivado(f"{_donde(punto['id'], ruta)}: {detalle}", mutar, None,
                                    _atribuir_al_punto(punto["id"])))
    return familia


def _familia_por_exclusion(schema: dict) -> list[Derivado]:
    """Un mutante por exclusión. Una exclusión es un `no` —que se elimina reemplazándolo por su
    operando— o un operador negativo, que se reemplaza por su contrario. La propiedad que esto
    prueba es la de AC-9: al eliminar una exclusión, **algún escenario pasa a fallar**."""
    matriz, _ = _corpus_conforme()
    opuesto = {"distinto": "igual", "no_en": "en", "no_disponible": "disponible"}
    familia: list[Derivado] = []
    for i, punto in enumerate(matriz["puntos"]):
        for ruta, nodo in _nodos(punto[CAMPO_CONDICION]):
            if nodo["tipo"] == "no":
                def quitar(datos, i=i, ruta=ruta):
                    interno = copy.deepcopy(_con_nodo(datos, i, ruta)["operando"])
                    _reemplazar_nodo(datos, i, ruta, interno)
                    return datos

                familia.append(Derivado(f"{_donde(punto['id'], ruta)}: se elimina el `no`",
                                        quitar, None, _atribuir_al_punto(punto["id"])))
            elif nodo.get("operador") in opuesto:
                def positivar(datos, i=i, ruta=ruta, operador=nodo["operador"]):
                    _con_nodo(datos, i, ruta)["operador"] = opuesto[operador]
                    return datos

                familia.append(Derivado(
                    f"{_donde(punto['id'], ruta)}: `{nodo['operador']}` pasa a "
                    f"`{opuesto[nodo['operador']]}`", positivar, None,
                    _atribuir_al_punto(punto["id"])))
    return familia


def _familia_por_valor_nuevo(schema: dict) -> list[Derivado]:
    """Un mutante por átomo de comparación: un valor declarado que ningún escenario asigna tiene que
    salir reportado como no ejercido. Es lo que prueba que el inventario de cobertura se deriva del
    corpus y no de una lista escrita a mano."""
    matriz, _ = _corpus_conforme()
    comparacion = _operadores(schema, "enum_operador_comparacion")
    familia: list[Derivado] = []
    for i, punto in enumerate(matriz["puntos"]):
        for ruta, nodo in _atomos(punto[CAMPO_CONDICION]):
            if nodo["operador"] not in comparacion:
                continue

            def mutar(datos, i=i, ruta=ruta):
                objetivo = _con_nodo(datos, i, ruta)
                if isinstance(objetivo["valor"], list):
                    objetivo["valor"].append(_VALOR_FRESCO)
                else:
                    objetivo["valor"] = _VALOR_FRESCO
                return datos

            familia.append(Derivado(
                f"{_donde(punto['id'], ruta)}: declara un valor que ningún escenario asigna",
                mutar, None, _atribuir_al_punto(punto["id"])))
    return familia


def _cobertura_de_escenario(schema: dict, indice: int) -> set[str]:
    """Los sitios que un escenario cubre **por sí solo**, evaluándolo aislado del resto. Es el
    oráculo independiente con el que se atribuye el rojo de la familia de abajo: sin él, un modo que
    reportara cualquier elemento al quitar cualquier escenario pasaría igual."""
    matriz, escenarios = _corpus_conforme()
    escenarios["escenarios"] = [escenarios["escenarios"][indice]]
    corpus, _ = _leer_corpus(matriz, schema, escenarios)
    if corpus is None:
        return set()
    _, registro, _ = _recorrer_escenarios(corpus, schema)
    cubiertos: set[str] = set()
    for elemento in _elementos_de_cobertura(corpus, schema):
        clave = (elemento.punto, elemento.ruta)
        if elemento.clase == "rama":
            if (elemento.detalle == "true") in registro.ramas.get(clave, set()):
                cubiertos.add(elemento.donde)
        elif elemento.detalle in registro.valores.get(clave, set()):
            cubiertos.add(elemento.donde)
    return cubiertos


def _familia_por_escenario(schema: dict) -> list[Derivado]:
    """Un mutante por escenario: quitarlo tiene que dejar algún elemento sin cubrir, y ese elemento
    tiene que ser uno que el escenario cubría. Un escenario cuya baja no cambia nada no aporta
    cobertura, y un conjunto con escenarios de relleno es exactamente el que se puede elegir para
    esquivar una combinación."""
    _, escenarios = _corpus_conforme()
    familia: list[Derivado] = []
    for i, escenario in enumerate(escenarios["escenarios"]):
        def quitar(datos, i=i):
            datos["escenarios"].pop(i)
            return datos

        cubiertos = _cobertura_de_escenario(schema, i)

        def atribuir(problemas: list[Problema], cubiertos=cubiertos) -> str | None:
            ajenos = sorted({p.donde for p in problemas} - cubiertos)
            if ajenos:
                return f"reporta sin cubrir {ajenos[:3]}, que este escenario no cubría"
            return None

        familia.append(Derivado(f"sin el escenario `{escenario['id']}`", None, quitar, atribuir))
    return familia


def _bloque_derivado(etiqueta: str, familia: list[Derivado], verificar, codigos: tuple[str, ...],
                     leyenda: str) -> tuple[str, bool, str]:
    """Cada mutante de la familia cae, y cae **por su motivo**: con el código que la familia
    pretende disparar y atribuido a quien se mutó. Un mutante que pone rojo por otra razón es un
    falso verde disfrazado."""
    fallas: list[str] = []
    for mutante in familia:
        problemas, _ = _correr_caso_de_condicion(
            CasoDeCondicion(None, mutante.descripcion, mutante.mutar_matriz,
                            mutante.mutar_escenarios), verificar)
        pertinentes = [p for p in problemas if p.codigo in codigos]
        if not pertinentes:
            fallas.append(f"SOBREVIVE {mutante.descripcion}"
                          + (f" — rojo por {sorted({p.codigo for p in problemas})}"
                             if problemas else ""))
            continue
        queja = mutante.atribucion(pertinentes)
        if queja:
            fallas.append(f"SIN ATRIBUIR {mutante.descripcion} — {queja}")
    return (etiqueta, not fallas,
            f"{len(familia)} mutantes derivados: {leyenda}"
            if not fallas else f"{len(fallas)} problemas: " + " | ".join(fallas[:4]))


def _bloque_de_condiciones(nombre: str, casos: tuple[CasoDeCondicion, ...], verificar,
                           catalogo: tuple[str, ...],
                           medir_conforme=None) -> list[tuple[str, bool, str]]:
    resultados: list[tuple[str, bool, str]] = []

    # [A] El control positivo, **por modo y no por task**: sin él, un evaluador que repruebe toda
    # entrada satisface todos los mutantes y este autotest cierra en verde sin haber aceptado jamás
    # una condición válida.
    conformes = [c for c in casos if c.codigo is None]
    fallas: list[str] = []
    for caso in conformes:
        problemas, resumen = _correr_caso_de_condicion(caso, verificar)
        if problemas:
            fallas.append(f"{caso.descripcion} — {problemas[0]}")
        elif medir_conforme is not None:
            queja = medir_conforme(resumen)
            if queja:
                fallas.append(f"{caso.descripcion} — {queja}")
    resultados.append((
        f"A/{nombre}", not fallas,
        f"control positivo: los {len(conformes)} casos conformes de `--{nombre}` pasan"
        if not fallas else "control positivo — " + " | ".join(fallas[:3]),
    ))

    # [B] Los mutantes fijos, cada uno rechazado por su motivo.
    mutantes = [c for c in casos if c.codigo is not None]
    sobrevivientes: list[str] = []
    desatribuidos: list[str] = []
    emitidos: set[str] = set()
    for caso in mutantes:
        problemas, _ = _correr_caso_de_condicion(caso, verificar)
        codigos = {p.codigo for p in problemas}
        emitidos |= codigos
        if not codigos:
            sobrevivientes.append(f"{caso.codigo}: {caso.descripcion}")
        elif caso.codigo not in codigos:
            desatribuidos.append(f"{caso.codigo}: {caso.descripcion} — rechazado por "
                                 f"{sorted(codigos)} y no por su motivo")
    problemas_b = ([f"SOBREVIVE {s}" for s in sobrevivientes]
                   + [f"SIN ATRIBUIR {d}" for d in desatribuidos])
    resultados.append((
        f"B/{nombre}", not problemas_b,
        f"{len(mutantes)} mutantes de `--{nombre}` y los {len(mutantes)} rechazados por su motivo"
        if not problemas_b else f"{len(problemas_b)} problemas: " + " | ".join(problemas_b[:5]),
    ))

    # [C] Un mutante por código: un código sin caso es una restricción que nadie comprobó que pueda
    # ponerse roja.
    ejercidos = {c.codigo for c in mutantes}
    problemas_c = [f"`{c}` está en el catálogo y ningún caso lo ejerce"
                   for c in catalogo if c not in ejercidos]
    problemas_c += [f"`{c}` lo emite el modo y no está en el catálogo"
                    for c in sorted((emitidos | ejercidos) - set(catalogo))]
    resultados.append((
        f"C/{nombre}", not problemas_c,
        f"los {len(catalogo)} códigos de `--{nombre}` tienen su caso"
        if not problemas_c else f"{len(problemas_c)} huecos: " + " | ".join(problemas_c[:5]),
    ))
    return resultados


def _preludio_de_condiciones() -> list[tuple[str, bool, str]]:
    """Lo que tiene que valer antes de correr un caso: que el corpus exista, que cada condición
    satisfaga la gramática del schema —evaluar una condición que el schema rechaza no prueba nada
    del evaluador— y que los escenarios validen contra el suyo."""
    schema, error = _cargar_json(RUTA_SCHEMA)
    if error:
        return [("0.fixture", False, error)]
    if not CONFORME_CONDICIONES.is_dir():
        return [("0.fixture", False, f"no existe el corpus conforme ({CONFORME_CONDICIONES})")]
    try:
        matriz, escenarios = _corpus_conforme()
    except (OSError, ValueError) as error:
        return [("0.fixture", False, f"el corpus conforme no se puede leer: {error}")]

    corpus, problemas = _leer_corpus(matriz, schema, escenarios)
    faltantes = [c for c in ("enum_operador_comparacion", "enum_operador_capacidad")
                 if not _operadores(schema, c)]
    return [
        ("0.fixture", corpus is not None and not problemas,
         f"el corpus conforme es evaluable: {len(matriz['puntos'])} condiciones válidas contra el "
         f"schema y {len(escenarios['escenarios'])} escenarios"
         if corpus is not None and not problemas
         else f"el corpus no es evaluable: {problemas[0] if problemas else 'sin corpus'}"),
        ("0.operadores", not faltantes,
         "los operadores se derivan del schema y no de una lista transcrita"
         if not faltantes else f"el schema no declara {faltantes}"),
    ]


def _exige_varios_puntos(resumen: dict) -> str | None:
    """El conforme no solo tiene que pasar: tiene que **medir**. Un corpus de un punto y un
    escenario pasaría sin ejercer nada de lo que AC-9 pide."""
    if resumen["activos_maximo"] >= resumen["puntos"]:
        return (f"un escenario activa los {resumen['puntos']} puntos: el conforme no ejerce la "
                "exclusión mutua")
    if resumen["pares_excluyentes"] < 1:
        return "ningún par de puntos queda excluido: el conforme no ejerce la exclusión mutua"
    return None


def _exige_elementos(resumen: dict) -> str | None:
    """El conforme no solo tiene que pasar: tiene que **medir**. Un corpus sin átomos multivalor
    haría que la cobertura por valor colapsara en la cobertura por rama —para `igual`, un solo valor
    declarado se ejerce exactamente cuando el átomo es verdadero— y la mitad del criterio de AC-9
    quedaría verde sin ejercerse."""
    if resumen["ramas"] < 1 or resumen["valores"] < 1:
        return (f"el inventario derivado tiene {resumen['ramas']} ramas y {resumen['valores']} "
                "valores: sin elementos, la cobertura completa es vacía")
    if resumen["atomos_multivalor"] < 1:
        return ("ningún átomo declara más de un valor: la cobertura por valor no se distingue de la "
                "cobertura por rama")
    return None


def modo_autotest_condiciones() -> int:
    resultados = _preludio_de_condiciones()
    if all(ok for _, ok, _ in resultados):
        resultados += _bloque_de_condiciones("condiciones", CASOS_CONDICIONES,
                                             verificar_condiciones, CODIGOS_CONDICIONES,
                                             _exige_varios_puntos)
        schema, _ = _cargar_json(RUTA_SCHEMA)
        resultados.append(_bloque_derivado(
            "D/condiciones", _familia_por_atomo(schema), verificar_condiciones,
            ("escenario_no_coincide",),
            "alterar cualquier átomo hace que algún escenario deje de coincidir"))
    return _cierre("cada escenario produce su conjunto declarado de puntos activos y ninguno los "
                   "produce todos", resultados)


def modo_autotest_cobertura_condiciones() -> int:
    resultados = _preludio_de_condiciones()
    if all(ok for _, ok, _ in resultados):
        resultados += _bloque_de_condiciones("cobertura-condiciones", CASOS_COBERTURA,
                                             verificar_cobertura_condiciones, CODIGOS_COBERTURA,
                                             _exige_elementos)
        schema, _ = _cargar_json(RUTA_SCHEMA)
        resultados.append(_bloque_derivado(
            "D/cobertura-condiciones", _familia_por_escenario(schema),
            verificar_cobertura_condiciones,
            ("rama_sin_cubrir", "valor_sin_ejercer"),
            "cada escenario aporta cobertura que ningún otro da"))
        resultados.append(_bloque_derivado(
            "E/cobertura-condiciones", _familia_por_valor_nuevo(schema),
            verificar_cobertura_condiciones, ("valor_sin_ejercer",),
            "un valor declarado que ningún escenario asigna sale reportado"))
        # [F] La propiedad que AC-9 nombra por su nombre, y que se comprueba sobre `--condiciones`:
        # el corpus sin mutar no falla ningún escenario (bloque A) y al eliminar cada exclusión,
        # alguno pasa a fallar.
        resultados.append(_bloque_derivado(
            "F/cobertura-condiciones", _familia_por_exclusion(schema), verificar_condiciones,
            ("escenario_no_coincide",),
            "al eliminar una exclusión, algún escenario pasa a fallar"))
    return _cierre("los escenarios cubren cada rama y cada valor de átomo, y ninguna exclusión "
                   "sobrevive a su eliminación", resultados)


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
    parser.add_argument(
        "--nombres-reservados", nargs="?", const=str(RUTA_NOMBRES_RESERVADOS), metavar="RUTA",
        help="valida la lista de nombres reservados al contenedor de perfiles "
             "(por defecto scripts/nombres-reservados-perfil.json)",
    )
    parser.add_argument(
        "--autotest-nombres-reservados", action="store_true",
        help="control positivo y negativo del modo --nombres-reservados sobre la lista real",
    )
    parser.add_argument(
        "--correspondencia", nargs="?", const=str(RUTA_MATRIZ), metavar="RUTA",
        help="compara la matriz contra el inventario vigente de puntos de despacho del árbol",
    )
    parser.add_argument(
        "--autotest-correspondencia", action="store_true",
        help="control positivo y negativo del modo --correspondencia sobre el fixture sintético",
    )
    parser.add_argument(
        "--completitud", nargs="?", const=str(RUTA_MATRIZ), metavar="RUTA",
        help=f"comprueba que los {TOTAL_PUNTOS} puntos tengan su ancla de invocación y detecta "
             "sitios de despacho no inventariados",
    )
    parser.add_argument(
        "--autotest-completitud", action="store_true",
        help="control positivo y negativo del modo --completitud sobre el fixture sintético",
    )
    parser.add_argument(
        "--procedencia", nargs="?", const=str(RUTA_MATRIZ), metavar="RUTA",
        help="comprueba que toda hoja declare una procedencia o su marca de ausencia, que la marca "
             "no aparezca donde el schema la prohíbe, e informa cuántas hojas quedan sin sede",
    )
    parser.add_argument(
        "--autotest-procedencia", action="store_true",
        help="control positivo y negativo del modo anterior sobre el fixture sintético de anclas",
    )
    parser.add_argument(
        "--anclas", nargs="?", const=str(RUTA_MATRIZ), metavar="RUTA",
        help="resuelve cada hoja anclada contra su sede con el pipeline que el schema congela y "
             "coteja el valor resuelto contra el declarado",
    )
    parser.add_argument(
        "--autotest-anclas", action="store_true",
        help="control positivo y negativo de --anclas y de --presupuesto-contractual sobre el "
             "fixture sintético de anclas",
    )
    parser.add_argument(
        "--presupuesto-contractual", nargs="?", const=str(RUTA_MATRIZ), metavar="RUTA",
        help="comprueba el presupuesto de espera contractual de cada punto: que el campo esté, que "
             "lleve sede y que su valor sea el que la sede dice",
    )
    parser.add_argument(
        "--condiciones", nargs="?", const=str(RUTA_MATRIZ), metavar="RUTA",
        help="evalúa la condición de existencia de cada punto contra los escenarios de "
             "configuración y capacidad, y comprueba que ninguno active todos los puntos",
    )
    parser.add_argument(
        "--autotest-condiciones", action="store_true",
        help="control positivo y negativo del modo anterior sobre el corpus sintético de "
             "condiciones",
    )
    parser.add_argument(
        "--cobertura-condiciones", nargs="?", const=str(RUTA_MATRIZ), metavar="RUTA",
        help="comprueba que los escenarios ejerzan cada rama de cada condición y cada valor "
             "declarado de cada átomo",
    )
    parser.add_argument(
        "--autotest-cobertura-condiciones", action="store_true",
        help="control positivo y negativo del modo anterior, más la familia de mutantes por "
             "exclusión sobre el mismo corpus",
    )
    parser.add_argument(
        "--escenarios", metavar="RUTA", default=None,
        help="los escenarios de configuración y capacidad; por defecto, el archivo hermano de la "
             "matriz con el sufijo `-escenarios` (solo lo usan --condiciones y "
             "--cobertura-condiciones)",
    )
    parser.add_argument(
        "--arbol", metavar="RUTA", default=str(REPO),
        help="raíz del árbol del que se deriva el inventario (por defecto, este repositorio); "
             "solo lo usan --correspondencia y --completitud",
    )
    parser.add_argument(
        "--raiz", metavar="RUTA", default=str(REPO),
        help="raíz contra la que se interpretan las sedes, que son rutas relativas (por defecto, "
             "este repositorio); solo la usan --anclas y --presupuesto-contractual",
    )
    parser.add_argument(
        "--salida", metavar="RUTA", default=None,
        help="ruta donde --completitud escribe su recibo (estado del detector y su motivo); "
             "sin esta bandera no escribe nada",
    )
    args = parser.parse_args(argv)

    seleccionados = [
        bool(args.schema),
        args.autotest_schema,
        bool(args.nombres_reservados),
        args.autotest_nombres_reservados,
        bool(args.correspondencia),
        args.autotest_correspondencia,
        bool(args.completitud),
        args.autotest_completitud,
        bool(args.procedencia),
        args.autotest_procedencia,
        bool(args.anclas),
        args.autotest_anclas,
        bool(args.presupuesto_contractual),
        bool(args.condiciones),
        args.autotest_condiciones,
        bool(args.cobertura_condiciones),
        args.autotest_cobertura_condiciones,
    ]
    if sum(seleccionados) != 1:
        print("Invocación inválida: exactamente uno de --schema, --autotest-schema, "
              "--nombres-reservados, --autotest-nombres-reservados, --correspondencia, "
              "--autotest-correspondencia, --completitud, --autotest-completitud, --procedencia, "
              "--autotest-procedencia, --anclas, --autotest-anclas, --presupuesto-contractual, "
              "--condiciones, --autotest-condiciones, --cobertura-condiciones o "
              "--autotest-cobertura-condiciones.",
              file=sys.stderr)
        return 2
    if args.autotest_schema:
        return modo_autotest()
    if args.nombres_reservados:
        return modo_nombres_reservados(Path(args.nombres_reservados))
    if args.autotest_nombres_reservados:
        return modo_autotest_nombres_reservados()
    if args.correspondencia:
        return modo_correspondencia(Path(args.correspondencia), Path(args.arbol))
    if args.autotest_correspondencia:
        return modo_autotest_correspondencia()
    if args.completitud:
        return modo_completitud(Path(args.completitud), Path(args.arbol),
                                Path(args.salida) if args.salida else None)
    if args.autotest_completitud:
        return modo_autotest_completitud()
    if args.procedencia:
        return modo_procedencia(Path(args.procedencia))
    if args.autotest_procedencia:
        return modo_autotest_procedencia()
    if args.anclas:
        return modo_anclas(Path(args.anclas), Path(args.raiz))
    if args.autotest_anclas:
        return modo_autotest_anclas()
    if args.presupuesto_contractual:
        return modo_presupuesto_contractual(Path(args.presupuesto_contractual), Path(args.raiz))
    escenarios = Path(args.escenarios) if args.escenarios else None
    if args.condiciones:
        return modo_condiciones(Path(args.condiciones), escenarios)
    if args.autotest_condiciones:
        return modo_autotest_condiciones()
    if args.cobertura_condiciones:
        return modo_cobertura_condiciones(Path(args.cobertura_condiciones), escenarios)
    if args.autotest_cobertura_condiciones:
        return modo_autotest_cobertura_condiciones()
    return modo_schema(Path(args.schema))


if __name__ == "__main__":
    sys.exit(main())
