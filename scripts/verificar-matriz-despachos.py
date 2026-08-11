#!/usr/bin/env python3
"""Verifica la matriz de despachos contra su schema cerrado.

Cuarenta y seis modos, y por ahora solo cuarenta y seis: los demás del catálogo los construyen
otras tasks.

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
- `--claves-perfil [ruta]` — comprueba que ningún nombre reservado al contenedor de perfiles de
  ejecución (por defecto los de `scripts/nombres-reservados-perfil.json`) aparezca como **clave** en
  una superficie de configuración del árbol (`--arbol`). El inventario de superficies —dueños que
  declaran el esquema y vistas que lo reproducen— se **deriva** del árbol, y la extracción es
  estructural: una mención en prosa o en un comentario no es una clave del esquema. Es un criterio
  distinto del de `verificar-vistas-config.py`, que compara vistas contra dueños y aceptaría una
  clave reservada agregada de forma consistente en los dos lados.
- `--autotest-claves-perfil` — control positivo y negativo del modo anterior, con un mutante **por
  superficie derivada** —no uno por clase— y otro por cada nombre reservado.
- `--parear-reporte <ruta|->` — clasifica un reporte de `verificar-paridad-powershell.py --reporte`
  leyendo su **cuerpo**: cero clases prohibidas y `fallo` en un conjunto de pares **exactamente
  igual** al autorizado. El código de salida 4 de ese arnés es su estado sano y este modo no lo lee
  como enfermedad; con `--codigo-de-salida` se coteja contra el que el reporte declara y se informa.
  El vocabulario de clases se deriva del arnés y los pares autorizados, de qué matriz de casos
  declara un caso `clase_esperada: fallo`.
- `--autotest-parear-reporte` — control positivo y negativo del modo anterior sobre el corpus
  sintético de `scripts/fixtures-matriz/paridad/`, con un mutante **por clase prohibida derivada** y
  el de sustitución que separa la igualdad de identidades de un tope de cantidad.
- `--identidad [ruta]` — compara la identidad de los puntos contra la **atestación histórica**: el
  blob de la matriz en el commit congelado en `COMMIT_ATESTACION`. Compara **por punto y no por
  conjunto** —el intercambio de dos identificadores conserva el conjunto— y su clave de
  correspondencia es el **sitio** del punto, no su posición ni su identificador. Si la atestación no
  se puede leer se detiene: **no cae de vuelta a la matriz vigente**.
- `--autotest-identidad` — control positivo y negativo del modo anterior sobre repositorios git
  sintéticos, con el caso del intercambio —el que distingue una comparación por punto de una por
  conjunto— y el que prueba que la precondición no degrada.
- `--contrato [ruta]` — el documento de contrato: su alcance comprometido, cada corrección con sus
  cinco componentes —texto anterior, corregido, evidencia, supersesión y documento fuente— y sus
  decisiones diferidas con su fase de destino. **La atribución se resuelve, no se cuenta:** el texto
  reemplazado tiene que vivir en el documento declarado como fuente, y esa fuente no puede ser el
  propio contrato. Con `--raiz`, la raíz contra la que se resuelven las fuentes.
- `--autotest-contrato` — control positivo y negativo del modo anterior sobre el corpus sintético de
  `scripts/fixtures-contrato/`, con los dos mutantes de atribución que un oráculo de «hay fuente» no
  caza y los tres que ejercen el alcance y las decisiones diferidas.
- `--ejes [ruta]` — los tres ejes del contrato —ciclo de vida operativo, validez del reporte
  entregado y resultado semántico— comparados por **igualdad exacta** contra `INVENTARIO_DE_EJES`,
  con puntero por literal. Rojo ante pérdida de namespace, enum de un eje usado en otro y enum
  unión; **verde** ante un literal compartido por dos ejes que conserve tipo, sede y significado.
- `--autotest-ejes` — control positivo y negativo del modo anterior. Su preludio resuelve los
  dieciséis punteros del inventario contra el árbol real: los mutantes impiden que el verificador
  sea laxo, y solo el puntero impide que el inventario sea inventado.
- `--capacidades [ruta]` — toda afirmación de plataforma del contrato marcada `portable`,
  `dependiente` (con la versión con la que se comprobó) o `no_verificable` (con el motivo por el que
  el runtime no la expone).
- `--autotest-capacidades` — control positivo y negativo del modo anterior, con mutantes
  **unitarios** dentro de un documento de afirmaciones válidas: el cuantificador de su criterio es
  «toda afirmación», y con el defecto global un verificador de «alguna» quedaría verde.
- `--perfil-schema [ruta]` — el contenedor del perfil de ejecución: sus **cinco componentes**
  —versión, perfiles nombrados, asignaciones por rol, valor por defecto y familias— son obligatorios,
  y lo que lleva **lista blanca cerrada** es el objeto de parámetros de cada perfil, que admite
  exclusivamente modelo y esfuerzo de razonamiento. Son dos niveles y confundirlos invierte el
  criterio. La forma del contenedor no se transcribe: se **deriva** de
  `scripts/nombres-reservados-perfil.json`, que es su única fuente.
- `--autotest-perfil-schema` — control positivo y negativo del modo anterior, con un mutante por
  cada una de las cinco clases que una hoja de perfil no puede alterar **más uno que agrega un
  tercer parámetro de runtime**, que no es ninguna de las cinco: sin él, una lista de prohibidos
  pasaría por lista blanca.
- `--perfil-precedencia [ruta]` — **ejecuta** la precedencia declarada contra el corpus de
  escenarios del contrato y coteja cada resolución contra la que el documento declara. Perfil sin
  uso, asignación a perfil inexistente y referencia rota resuelven **inválidos**; las dos ausencias
  legítimas —punto sin asignación habiendo superficie, y punto sin superficie— caen al default
  portable **por causas distintas**, y las dos son obligatorias.
- `--autotest-perfil-precedencia` — control positivo y negativo del modo anterior, con el mutante
  que intercambia las causas de las dos ausencias y los dos que retiran una de las dos.
- `--roles [ruta]` — los contratos de las **cinco familias de rol** y el mapa de las **trece
  asignaciones**, que se congelan distinto: las familias se **derivan** de la tabla del roadmap con
  puntero por literal, y el mapa punto → variante es una **decisión escrita** que se compara por
  igualdad exacta. Los campos vigentes u observados pasan por `resolver_procedencia`, el mismo
  verificador semántico que las hojas de la matriz. Con `--raiz` la raíz de esas sedes y con
  `--arbol` la del árbol contra el que se resuelven los punteros normativos.
- `--autotest-roles` — control positivo y negativo del modo anterior, con un mutante **por
  asignación** —trece, cada uno nombrando su propia fila— y las tres sustituciones de entrada,
  salida y scope que solo el resolutor semántico puede ver.
- `--diversidad [ruta]` — por intento, las tres identidades y sus relaciones; la topología agregada
  se **deriva** de esos registros y se coteja contra la declarada; y la regla de evidencia
  independiente como ejecutable: contar un resultado de una sola familia, o de una sola voz, es rojo.
- `--autotest-diversidad` — control positivo y negativo del modo anterior, con el fixture cuya
  topología declarada **contradice sus propios registros** en las dos direcciones.
- `--defectos [ruta]` — el inventario de defectos: los **seis mínimos comparados por identidad**,
  cada uno con ubicación, naturaleza y fase. Acepta más y rechaza menos.
- `--autotest-defectos` — control positivo y negativo del modo anterior, con la sustitución que
  conserva el total —lo que un `len(defectos) >= 6` no ve— y el séptimo defecto bien formado que
  tiene que pasar.
- `--guardas [ruta]` — el **conjunto cerrado** de invocaciones de guarda del repositorio (por
  defecto `scripts/guardas-fase-0.json`): las ejecuta y emite un **recibo** con qué corrió, con qué
  código de salida y qué se concluyó de cada una. **Falla si omite una del manifiesto aunque todas
  las ejecutadas estén verdes** —la comparación con el conjunto ejercido es una igualdad y no una
  inclusión, así que correr de más tampoco es correr bien— y falla si el manifiesto y lo que
  documentan las instrucciones (`--instrucciones`, por defecto `CLAUDE.md`) no coinciden **en las
  dos direcciones**. El conjunto documentado se **deriva** del texto: lo congelado es el criterio de
  extracción, no la lista. Con `--salida` escribe el recibo, que otra fila consume.
- `--autotest-guardas` — control positivo y negativo del modo anterior **sin ejecutar ninguna
  guarda**: el recibo conforme se sintetiza del manifiesto y las instrucciones se mutan en memoria.
  Los mutantes atacan las tres piezas por separado —manifiesto, recibo e instrucciones—, incluidas
  las tres sustituciones que conservan el total, que son las únicas que separan comparar identidades
  de contar.
- `--topologia [ruta]` — el **registro canónico** de artefactos (por defecto
  `scripts/artefactos-fase-0.json`): una entrada por artefacto con su ubicación canónica, su dueño
  **único**, el dato del que es sede y si debe estar versionado. Comprueba que ningún dato esté
  declarado como fuente en dos rutas y que la indexación cierre **en las dos direcciones**: los
  `versioned: true` dentro del árbol candidato y los `false` fuera. El árbol candidato es
  `git ls-files` menos las bajas del cambio más las altas no ignoradas —un archivo nuevo sin stage
  no está en `git ls-files` y sí en el árbol candidato—, y un árbol vacío es error, no un conjunto
  vacío. Con `--arbol`, la raíz.
- `--descubrimiento [ruta]` — la **regla de descubrimiento** —directorios, patrones y excepciones
  con motivo— aplicada al árbol candidato, y comparada contra el registro en las dos direcciones. Es
  una fuente **distinta** del registro: una regla transcrita de sus rutas se rechaza, porque comparar
  un conjunto consigo mismo no prueba nada. Cada excepción lleva **predicado de vigencia** —la ruta
  no existe en disco—, se evalúa en cada corrida y **falla por caducidad** cuando la ruta aparece,
  con ese motivo y no con el genérico de una ruta ausente del registro.
- `--autotest-topologia` — control positivo y negativo de los dos modos anteriores sobre el registro
  y el árbol reales, mutados **en memoria**. Incluye las dos direcciones de la comparación por
  separado: el archivo descubierto sin entrada y la entrada que ninguna regla alcanza.
- `--autotest-caducidad-excepcion` — las **dos** direcciones del predicado de vigencia sobre una
  raíz sintética en un directorio temporal: verde con la excepción vigente, rojo **por caducidad** al
  materializar la ruta exceptuada, y verde otra vez al retirar la excepción y darle entrada en el
  registro. Con una sola dirección, el predicado especial puede quedar sin implementar y nada lo
  notaría.
- `--integracion [ruta]` — la **integración declarada** del verificador nuevo en las instrucciones
  del repositorio (por defecto `CLAUDE.md`, vía `--instrucciones`): que la unidad que lo documenta
  declare que es un script propio (y no un modo de uno existente), cuándo debe ejecutarse, el
  comando exacto y el código de salida sano — y que **lo declarado sea cierto**, no solo que esté
  escrito. Comprueba contra el árbol real: la bandera documentada aparece en el `--help` del propio
  script, el código de salida declarado coincide con el que este modo devuelve en verde, y el
  baseline acoplado al contenido de un archivo (`scripts/baseline-sobre-en-vuelo.md`, vía
  `--validar-baseline`) está renovado.

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
                                                  | --claves-perfil [ruta]
                                                  | --autotest-claves-perfil
                                                  | --parear-reporte <ruta|->
                                                  | --autotest-parear-reporte
                                                  | --identidad [ruta] | --autotest-identidad
                                                  | --contrato [ruta] | --autotest-contrato
                                                  | --ejes [ruta] | --autotest-ejes
                                                  | --capacidades [ruta] | --autotest-capacidades
                                                  | --perfil-schema [ruta]
                                                  | --autotest-perfil-schema
                                                  | --perfil-precedencia [ruta]
                                                  | --autotest-perfil-precedencia
                                                  | --roles [ruta] | --autotest-roles
                                                  | --diversidad [ruta] | --autotest-diversidad
                                                  | --defectos [ruta] | --autotest-defectos
                                                  | --guardas [ruta] | --autotest-guardas
                                                  | --topologia [ruta]
                                                  | --descubrimiento [ruta]
                                                  | --autotest-topologia
                                                  | --autotest-caducidad-excepcion
                                                  | --integracion [ruta]
Exit 0 si el modo pasa, 1 si falla, 2 si la invocación es inválida, y 3 cuando los ocho modos que
leen el documento de contrato no lo encuentran: no hay veredicto, y una ausencia no es una
conformidad.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import fnmatch
import importlib.util
import io
import itertools
import json
import os
import re
import shutil
import subprocess
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
        'extraccion_ancla_de_seccion',
        'extraccion_captura_de_grupo',
        'extraccion_literal',
        'extraccion_presencia_de_clausula',
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
        'extraccion_ancla_de_seccion.tipo=ancla_de_seccion',
        'extraccion_captura_de_grupo.tipo=captura_de_grupo',
        'extraccion_literal.tipo=literal',
        'extraccion_presencia_de_clausula.tipo=presencia_de_clausula',
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
        'extraccion_presencia_de_clausula.clausula.minLength=1',
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
        'extraccion_ancla_de_seccion.tipo',
        'extraccion_captura_de_grupo.grupo',
        'extraccion_captura_de_grupo.patron',
        'extraccion_captura_de_grupo.tipo',
        'extraccion_literal.tipo',
        'extraccion_presencia_de_clausula.clausula',
        'extraccion_presencia_de_clausula.tipo',
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
        encabezados = _celdas(lineas[i])
        indice = encabezados.index(columna) if columna in encabezados else None
        j = i + 2
        while j < len(lineas) and fuera[j] and lineas[j].strip().startswith("|"):
            celdas = _celdas(lineas[j])
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


def _clausula_borrada_de_la_sede(raiz: Path) -> None:
    """La sede deja de afirmar el gate y **conserva la línea que el selector nombra**: lo que
    desaparece es la cláusula, no el nodo. Borrar la línea entera daría `selector_sin_resultado` y
    probaría el selector, que es lo que este caso justamente no está probando."""
    ruta = raiz / "skills" / "skill-anclada" / "SKILL.md"
    texto = ruta.read_text(encoding="utf-8")
    ruta.write_text(texto.replace("se anuncia y se espera confirmación explícita",
                                  "cada worker decide por su cuenta"), encoding="utf-8")


def _sede_reescrita_alrededor_de_la_clausula(raiz: Path) -> None:
    """Control no-op: la línea cambia en todo menos en la cláusula. Si esto también se pusiera rojo,
    `presencia_de_clausula` estaría comparando el texto de la sede —como hace `literal`— y no la
    presencia, y el rojo del caso de al lado no probaría lo que dice probar."""
    ruta = raiz / "skills" / "skill-anclada" / "SKILL.md"
    texto = ruta.read_text(encoding="utf-8")
    ruta.write_text(
        texto.replace("se anuncia y se espera confirmación explícita.",
                      "se anuncia y se espera confirmación explícita, sin excepción, en cada gate."),
        encoding="utf-8")


def _sede_sin_encabezados(raiz: Path) -> None:
    """La sede pierde todos sus encabezados y conserva todo lo demás. El nodo del contrato de salida
    sigue estando y sigue siendo el mismo texto: lo que desaparece es la sección que lo contiene, o
    sea lo único de lo que `ancla_de_seccion` puede sacar el fragmento."""
    ruta = raiz / "skills" / "skill-anclada" / "reference.md"
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    ruta.write_text("\n".join(l for l in lineas if not PATRON_HEADING.match(l)) + "\n",
                    encoding="utf-8")


# La procedencia que el ancla de invocación tenía antes de derivarse: la misma ancla, transcrita a
# mano en una celda de la sede. Sostiene el caso conforme que impide que `conversion: referencia`
# quede ejercida solo contra cadenas que este mismo resolutor fabrica.
PROCEDENCIA_ANCLA_TRANSCRITA = {
    "sede": "skills/skill-anclada/reference.md",
    "tipo_de_sede": "fila_de_tabla_markdown",
    "selector": {"clave_primera_celda": "explorador", "encabezado_de_columna": "ancla"},
    "cardinalidad": {"tipo": "exactamente_una"},
    "extraccion": {"tipo": "literal"},
    "normalizacion": "trim",
    "conversion": "referencia",
}


# La procedencia con la que se ejerce `presencia_de_clausula`. **Sustituye** a la hoja booleana del
# fixture en vez de agregarse: la del fixture resuelve `false` desde una clave que lo dice literal, y
# esta resuelve `true` desde una sede que afirma el gate sin decir su valor, que es el caso que el
# subtipo existe para cubrir. Las dos tienen que quedar ejercidas, y por eso la sustitución vive en
# los casos y no en el fixture.
PROCEDENCIA_PRESENCIA_DE_CLAUSULA = {
    "sede": "skills/skill-anclada/SKILL.md",
    "tipo_de_sede": "patron_de_linea",
    "selector": {"patron": "^El punto no se despacha solo:"},
    "cardinalidad": {"tipo": "exactamente_una"},
    "extraccion": {"tipo": "presencia_de_clausula",
                   "clausula": "se espera confirmación explícita"},
    "normalizacion": "colapsar_espacios",
    "conversion": "booleano",
}


def _por_presencia(datos: dict, clausula: str | None = None, valor: Any = True) -> dict:
    """La hoja booleana del fixture pasa a resolverse por presencia de cláusula. `clausula` y
    `valor` se parametrizan porque los mutantes del subtipo se distinguen justamente ahí: uno
    cambia lo que se busca, otro lo que la matriz declara haber encontrado."""
    procedencia = copy.deepcopy(PROCEDENCIA_PRESENCIA_DE_CLAUSULA)
    if clausula is not None:
        procedencia["extraccion"]["clausula"] = clausula
    datos["puntos"][0]["requiere_confirmacion_del_usuario"] = {
        "valor": valor, "procedencia": procedencia,
    }
    return datos


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
    CasoDeAncla(None, "el ancla de invocación leída de la celda que la transcribe da el mismo valor "
                      "que la construida con `ancla_de_seccion`: sin este caso, `referencia` solo "
                      "quedaría ejercida contra cadenas que este resolutor fabrica",
                _mutando(lambda d: d["puntos"][0]["ancla_de_invocacion"].__setitem__(
                    "procedencia", copy.deepcopy(PROCEDENCIA_ANCLA_TRANSCRITA))), None, None),
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
    CasoDeAncla("conversion_fallida",
                "referencia: el contrato de salida extrae la línea en vez de su ancla, y la línea "
                "tiene espacios — `ancla_de_seccion` y `literal` no son intercambiables",
                _mutando(lambda d: _proc(d, "contrato_de_salida").__setitem__(
                    "extraccion", {"tipo": "literal"})), None, None),
    CasoDeAncla("conversion_fallida",
                "ancla sin sección: la sede pierde sus encabezados y el nodo deja de estar "
                "contenido en ninguno, así que no hay fragmento que construir",
                None, _sede_sin_encabezados, None),
    CasoDeAncla("conversion_fallida", "la extracción por captura no casa con el nodo seleccionado",
                _mutando(lambda d: _proc(d, "skill")["extraccion"].__setitem__(
                    "patron", "^nombre: (.+)$")), None, None),
    CasoDeAncla(None, "presencia: la sede afirma el gate sin decir su valor y la hoja resuelve "
                      "`true` por la existencia de la cláusula",
                _mutando(_por_presencia), None, None),
    CasoDeAncla(None, "presencia: la línea cambia en todo menos en la cláusula y la hoja sigue "
                      "verde — el control no-op de que se comprueba la cláusula y no la línea",
                _mutando(_por_presencia), _sede_reescrita_alrededor_de_la_clausula, None),
    CasoDeAncla("conversion_fallida",
                "presencia: la sede deja de decir la cláusula y conserva la línea que el selector "
                "nombra, así que la hoja ya no puede afirmar lo que afirmaba",
                _mutando(_por_presencia), _clausula_borrada_de_la_sede, None),
    CasoDeAncla("conversion_fallida",
                "presencia: la cláusula declarada no está en el nodo — una cláusula que no casa "
                "nada NO produce `true`, que es la degeneración a «cualquier texto no vacío»",
                _mutando(lambda d: _por_presencia(d, clausula="se despacha sin avisar a nadie")),
                None, None),
    CasoDeAncla("conversion_fallida",
                "presencia: la cláusula se escribe como patrón — el `.*` se busca verbatim y no "
                "comodinea, así que no casa este nodo. Prueba que la cláusula NO se compila; no "
                "prueba que todo comodín caiga, porque `.*` es texto real en Markdown (`palabra.**`)",
                _mutando(lambda d: _por_presencia(d, clausula="se espera confirmación.*")),
                None, None),
    CasoDeAncla("valor_no_coincide", "se sustituye el rol por otro plausible conservando la procedencia",
                _mutando(lambda d: d["puntos"][0]["rol"].__setitem__("valor", "explorer")), None, None),
    CasoDeAncla("valor_no_coincide",
                "presencia: la hoja declara `false` sobre una extracción que solo puede afirmar — "
                "que el subtipo no exprese el caso simétrico no es prosa, se pone rojo",
                _mutando(lambda d: _por_presencia(d, valor=False)), None, None),
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
# Claves de perfil: ningún nombre reservado al contenedor de perfiles de ejecución aparece en una
# superficie de configuración del árbol.
#
# **La extracción es estructural, no textual.** Lo que se busca no es la cadena `subagents` en un
# archivo: es una **clave** del esquema de configuración cuyo nombre sea uno de los reservados. Las
# dos cosas se separan porque el repo ya contiene menciones legítimas en prosa —`co-explore/
# reference.md` explica por qué se retiró `cross_model.profiles`—, y un buscador de cadenas las
# reportaría como materialización del contenedor. Aquí se recorta el bloque YAML, se compone su
# árbol de nodos y se recolectan **las claves de sus mappings**: la prosa de alrededor no entra, los
# comentarios del propio bloque no entran (el parser los descarta) y los **valores** tampoco —
# `reviewer: auto | claude | codex` nombra dos familias sin declarar ninguna clave—.
#
# **El inventario de superficies se deriva del árbol; lo que se congela es el criterio.** Escribir a
# mano la lista de dueños y vistas la deja vieja en cuanto alguien agregue una skill, y nada lo
# señalaría. Lo congelado son tres cosas: los dos artefactos de configuración que las skills
# documentan, el nombre de la sección donde una skill declara la suya, y la carpeta que se recorre.
# De ahí sale el inventario en dos pasos:
#
#   1. **Semillas por encabezado** — un bloque YAML cuyo encabezado se declara configuración: nombra
#      uno de los dos artefactos (esquema o ejemplo) o es la sección `Configuración` de la skill.
#   2. **Expansión por vocabulario** — cualquier otro bloque YAML cuyo mapping raíz declare al menos
#      una de las claves raíz que las semillas declaran. Sin este paso quedaría fuera el esquema que
#      `sdd-flow/SKILL.md` documenta bajo «Adaptación al proyecto», que es el bloque más completo del
#      repo y el lugar donde una clave de perfil se filtraría con menos ruido.
#
# El frontmatter queda excluido de la expansión: los artefactos del flujo (`plan.md`, `handoff.md`)
# comparten nombres de campo con la configuración —`id`, `created_at`, `branch_prefix`— y no son
# superficies de configuración. Se los reconoce porque el bloque abre con el separador de documento.
#
# **Lo que no se recorre.** Solo `skills/`. `docs/superpowers/specs/` contiene el esquema de perfiles
# que este flujo declara descartado, con su clave `profiles` escrita en un bloque YAML: es historia
# de una decisión, no una superficie que un proyecto pueda escribir, y barrerla pondría la guarda en
# rojo por un documento que registra precisamente que el contenedor no se materializó.
# ---------------------------------------------------------------------------------------------

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover — el repo la usa en verificar-vistas-config.py
    _yaml = None

# Los dos artefactos de configuración que las skills de este repo documentan. Es criterio, no
# inventario: de acá sale qué encabezado se declara configuración, no qué archivos la tienen.
ARTEFACTOS_DE_CONFIGURACION = (".specify/config.yml", "manifest.yml")

# El encabezado con que una skill declara la configuración que posee.
HEADING_DE_CONFIGURACION = "Configuración"

# El encabezado con que un documento se declara **vista**: reproduce el esquema de un artefacto en
# vez de declararlo. Las dos clases importan por separado — un extractor que solo recorriera las
# vistas dejaría los dueños sin mirar, y al revés.
PREFIJO_DE_VISTA = "Ejemplo"

# La carpeta del árbol donde viven las superficies de configuración.
CARPETA_DE_SUPERFICIES = "skills"

CODIGOS_CLAVES_PERFIL = (
    "lista_ilegible",
    "sin_superficies",
    "clase_sin_superficies",
    "bloque_ilegible",
    "clave_reservada",
)


class Superficie(NamedTuple):
    identificador: str   # `<ruta>#<encabezado>#<ordinal>`: estable aunque la mutación mueva líneas
    ruta: str            # relativa al árbol
    heading: str
    linea: int           # línea del cercado de apertura, 1-based
    clase: str           # "dueño" | "vista"
    origen: str          # "encabezado" | "vocabulario"
    cuerpo: str          # el bloque YAML, sin la indentación del cercado

    @property
    def donde(self) -> str:
        return f"{self.ruta}:{self.linea} → {self.heading}"


class ClaveYaml(NamedTuple):
    nombre: str
    ruta: tuple[str, ...]
    linea: int           # relativa al cuerpo del bloque, 1-based

    @property
    def puntero(self) -> str:
        return ".".join(self.ruta)


def _bloques_yaml_con_encabezado(texto: str) -> list[tuple[str, int, str]]:
    """Cada bloque YAML **de nivel superior** con el encabezado que lo domina y su línea.

    Rastrea el cercado abierto y su lenguaje: un ```yaml anidado dentro del cercado de otro
    lenguaje es el cuerpo de un ejemplo ajeno —el prompt de un subagente, una plantilla— y no un
    bloque del documento.
    """
    lineas = texto.splitlines()
    bloques: list[tuple[str, int, str]] = []
    heading: str | None = None
    abierto: tuple[str, int] | None = None   # (lenguaje, indentación) del cercado en curso
    cuerpo: list[str] = []
    inicio = 0
    for numero, linea in enumerate(lineas, 1):
        cercado = re.match(r"^(\s*)(`{3,})\s*([A-Za-z0-9_+-]*)\s*$", linea)
        if abierto is not None:
            if cercado is not None and not cercado.group(3):
                if abierto[0] in ("yaml", "yml"):
                    margen = abierto[1]
                    bloques.append((heading or "", inicio, "\n".join(
                        c[margen:] if c[:margen].strip() == "" else c.lstrip() for c in cuerpo)))
                abierto, cuerpo = None, []
            else:
                cuerpo.append(linea)
            continue
        if cercado is not None:
            abierto, inicio = (cercado.group(3).lower(), len(cercado.group(1))), numero
            continue
        encabezado = re.match(r"^(#{1,6})\s+(.*?)\s*$", linea)
        if encabezado is not None:
            heading = encabezado.group(2)
    return bloques


def _encabezado_de_configuracion(heading: str) -> bool:
    """El encabezado se declara configuración: nombra uno de los artefactos, o es la sección con que
    una skill declara la config que posee."""
    if heading.strip() == HEADING_DE_CONFIGURACION:
        return True
    return any(artefacto in heading for artefacto in ARTEFACTOS_DE_CONFIGURACION)


def _clase_de_superficie(heading: str) -> str:
    return "vista" if heading.lstrip().startswith(PREFIJO_DE_VISTA) else "dueño"


def _es_frontmatter(cuerpo: str) -> bool:
    return cuerpo.lstrip().startswith("---")


def _mapping_raiz(cuerpo: str) -> set[str] | None:
    """Las claves raíz del bloque, o None si no es un mapping o no parsea."""
    try:
        datos = _yaml.safe_load(cuerpo)
    except Exception:      # noqa: BLE001 — cualquier error del parser es "no es configuración"
        return None
    return set(datos) if isinstance(datos, dict) else None


def claves_del_bloque(cuerpo: str) -> tuple[list[ClaveYaml], str | None]:
    """Todas las claves de todos los mappings del bloque, con su ruta punteada y su línea.

    Compone el árbol de nodos en vez de cargar a `dict`: así entran las claves repetidas —que
    `safe_load` colapsa quedándose con la última— y las de los mappings en línea, y sale la línea de
    cada una para el diagnóstico.
    """
    claves: list[ClaveYaml] = []

    def recorrer(nodo: Any, ruta: tuple[str, ...]) -> None:
        if isinstance(nodo, _yaml.MappingNode):
            for clave, valor in nodo.value:
                if not isinstance(clave, _yaml.ScalarNode):
                    recorrer(clave, ruta)
                    recorrer(valor, ruta)
                    continue
                nombre = str(clave.value)
                claves.append(ClaveYaml(nombre, ruta + (nombre,), clave.start_mark.line + 1))
                recorrer(valor, ruta + (nombre,))
        elif isinstance(nodo, _yaml.SequenceNode):
            for indice, item in enumerate(nodo.value):
                recorrer(item, ruta + (f"[{indice}]",))

    try:
        documentos = list(_yaml.compose_all(cuerpo))
    except Exception as error:      # noqa: BLE001 — el mensaje del parser es el diagnóstico
        return [], str(error).replace("\n", " ")
    for documento in documentos:
        if documento is not None:
            recorrer(documento, ())
    return claves, None


def derivar_superficies(arbol: Path) -> list[Superficie]:
    """El inventario de superficies de configuración del árbol, derivado en los dos pasos."""
    candidatos: list[tuple[str, str, int, str]] = []
    for ruta in sorted((arbol / CARPETA_DE_SUPERFICIES).rglob("*.md")):
        rel = ruta.relative_to(arbol).as_posix()
        for heading, linea, cuerpo in _bloques_yaml_con_encabezado(
                ruta.read_text(encoding="utf-8")):
            candidatos.append((rel, heading, linea, cuerpo))

    vocabulario: set[str] = set()
    for _, heading, _, cuerpo in candidatos:
        if _encabezado_de_configuracion(heading):
            vocabulario |= _mapping_raiz(cuerpo) or set()

    superficies: list[Superficie] = []
    ordinales: dict[tuple[str, str], int] = {}
    for rel, heading, linea, cuerpo in candidatos:
        if _encabezado_de_configuracion(heading):
            origen = "encabezado"
        elif _es_frontmatter(cuerpo) or not ((_mapping_raiz(cuerpo) or set()) & vocabulario):
            continue
        else:
            origen = "vocabulario"
        ordinal = ordinales.get((rel, heading), 0)
        ordinales[(rel, heading)] = ordinal + 1
        superficies.append(Superficie(
            f"{rel}#{heading}#{ordinal}", rel, heading, linea,
            _clase_de_superficie(heading), origen, cuerpo))
    return superficies


def nombres_reservados(ruta_lista: Path) -> tuple[tuple[str, ...], tuple[str, ...], str | None]:
    """Los nombres reservados y los admitidos, leídos del archivo. No se transcriben acá: esa lista
    tiene un dueño y este modo es su consumidor."""
    datos, error = _cargar_json(ruta_lista)
    if error:
        return (), (), error
    if not isinstance(datos, dict):
        return (), (), f"{ruta_lista.name} no es un objeto"
    reservados: list[str] = []
    admitidos: list[str] = []
    for lista, destino in (("reservados", reservados), ("no_reservados", admitidos)):
        entradas = datos.get(lista)
        if not isinstance(entradas, list) or not entradas:
            return (), (), f"{ruta_lista.name}: `{lista}` no es una lista con entradas"
        for entrada in entradas:
            nombre = entrada.get("nombre") if isinstance(entrada, dict) else None
            if not isinstance(nombre, str) or not nombre.strip():
                return (), (), f"{ruta_lista.name}: una entrada de `{lista}` no declara `nombre`"
            destino.append(nombre)
    return tuple(reservados), tuple(admitidos), None


def verificar_claves_perfil(arbol: Path, ruta_lista: Path) -> tuple[list[Problema], dict]:
    reservados, admitidos, error = nombres_reservados(ruta_lista)
    if error:
        return [Problema("lista_ilegible", ruta_lista.name, error)], {}

    superficies = derivar_superficies(arbol)
    resumen = {
        "superficies": len(superficies),
        "dueños": sum(1 for s in superficies if s.clase == "dueño"),
        "vistas": sum(1 for s in superficies if s.clase == "vista"),
        "por_vocabulario": sum(1 for s in superficies if s.origen == "vocabulario"),
        "claves": 0,
        "reservados": len(reservados),
        "admitidos": list(admitidos),
        "inventario": [s.donde for s in superficies],
    }
    if not superficies:
        return [Problema("sin_superficies", f"{arbol}/{CARPETA_DE_SUPERFICIES}",
                         "el árbol no produjo ninguna superficie de configuración: sin superficies "
                         "que mirar, este modo daría verde sin haber leído nada")], resumen

    # Las dos clases tienen que existir. Un inventario de una sola clase deja la otra sin inspeccionar
    # y el verde no distingue "no hay claves reservadas" de "no se miró esa mitad del árbol".
    problemas = [
        Problema("clase_sin_superficies", f"{arbol}/{CARPETA_DE_SUPERFICIES}",
                 f"ninguna superficie derivada es de clase `{clase}`: la mitad del inventario "
                 "quedaría sin inspeccionar")
        for clase in ("dueño", "vista") if not any(s.clase == clase for s in superficies)
    ]

    reservado = set(reservados)
    for superficie in superficies:
        claves, error = claves_del_bloque(superficie.cuerpo)
        if error:
            problemas.append(Problema(
                "bloque_ilegible", superficie.donde,
                f"el bloque no compone como YAML y sus claves no pueden leerse: {error}"))
            continue
        resumen["claves"] += len(claves)
        for clave in claves:
            if clave.nombre in reservado:
                problemas.append(Problema(
                    "clave_reservada", superficie.donde,
                    f"la clave `{clave.puntero}` (línea {clave.linea} del bloque) se llama "
                    f"`{clave.nombre}`, reservado al contenedor de perfiles de ejecución: el "
                    "contenedor quedaría materializado en el esquema de configuración"))
    return problemas, resumen


def modo_claves_perfil(arbol: Path, ruta_lista: Path) -> int:
    if _yaml is None:
        print("FALLA  falta PyYAML: sin el parser no hay extracción estructural, y buscar los "
              "nombres como cadenas confundiría la prosa con el esquema")
        return 1

    problemas, resumen = verificar_claves_perfil(arbol, ruta_lista)
    if problemas:
        _informar(problemas, f"claves de perfil en las superficies de configuración de {arbol}")
        return 1

    print(f"OK     {resumen['superficies']} superficies de configuración derivadas de "
          f"{CARPETA_DE_SUPERFICIES}/: {resumen['dueños']} dueños y {resumen['vistas']} vistas "
          f"({resumen['por_vocabulario']} por vocabulario, el resto por encabezado)")
    print(f"OK     {resumen['claves']} claves extraídas y ninguna es uno de los "
          f"{resumen['reservados']} nombres reservados al contenedor de perfiles")
    print(f"OK     los {len(resumen['admitidos'])} nombres admitidos no se buscan: "
          f"{', '.join('`' + n + '`' for n in resumen['admitidos'])}")
    print()
    print("RESULTADO: OK")
    return 0


# --- Autotest del modo -------------------------------------------------------------------------
#
# El fixture es **el árbol real, copiado a un temporal**, y no un corpus sintético: lo que la task
# exige comprobar es que se inspeccione cada superficie que hoy existe, y un corpus inventado con
# dos archivos dejaría trece sin mirar mientras el autotest cierra en verde. La copia es obligatoria
# en la otra dirección: mutar el worktree deja un archivo alterado si el proceso muere, y ahí es
# indistinguible de un cambio real.

class CasoDeClaves(NamedTuple):
    codigo: str | None      # el problema que el caso tiene que disparar; None = caso conforme
    descripcion: str
    mutar: Any              # (raíz, superficies) -> None, o None
    superficie: str | None  # el identificador de la superficie a la que el problema debe atribuirse


def _linea_de_cierre(lineas: list[str], apertura: int) -> int:
    """Índice 0-based de la línea del cercado que cierra el que abre en `apertura` (1-based)."""
    for indice in range(apertura, len(lineas)):
        if re.match(r"^\s*`{3,}\s*$", lineas[indice]):
            return indice
    return len(lineas)


def _margen(linea: str) -> str:
    return linea[:len(linea) - len(linea.lstrip())]


def _insertar_en_bloque(raiz: Path, superficie: Superficie, texto: str) -> None:
    """Agrega líneas al final del bloque de una superficie, con la indentación de su cercado."""
    ruta = raiz / superficie.ruta
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    cierre = _linea_de_cierre(lineas, superficie.linea)
    margen = _margen(lineas[superficie.linea - 1])
    lineas[cierre:cierre] = [margen + l if l else l for l in texto.splitlines()]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def _insertar_anidado(raiz: Path, superficie: Superficie, nombre: str) -> None:
    """Cuelga una clave de un mapping que ya existe dentro del bloque: un reservado no deja de serlo
    por estar anidado, y un extractor que solo mirara las claves raíz lo dejaría pasar."""
    ruta = raiz / superficie.ruta
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    cierre = _linea_de_cierre(lineas, superficie.linea)
    for indice in range(superficie.linea, cierre):
        padre = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*):\s*(#.*)?$", lineas[indice])
        if padre is not None and indice + 1 < cierre:
            lineas.insert(indice + 1, f"{padre.group(1)}  {nombre}: opus")
            ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
            return
    raise AssertionError(f"{superficie.donde}: el bloque no tiene ningún mapping donde anidar")


def _prosa_junto_al_bloque(raiz: Path, superficie: Superficie) -> None:
    """Prosa que nombra el contenedor **fuera** del bloque, en el archivo de una superficie. Es lo
    que un buscador de cadenas reportaría y una extracción de claves no."""
    ruta = raiz / superficie.ruta
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    cierre = _linea_de_cierre(lineas, superficie.linea)
    lineas[cierre + 1:cierre + 1] = [
        "",
        "Todavía no existe el contenedor `subagents:`, con su mapa `profiles:` y sus `bindings:`;",
        "tampoco se configuran `model:` ni `reasoning:` desde acá. Se declara en el contrato y nada más.",
    ]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def _sin_vistas(raiz: Path) -> None:
    """Ningún encabezado se declara ya un ejemplo, así que la clase `vista` desaparece del
    inventario. No alcanza con borrar los documentos `*-ejemplo.md`: `sdd-orchestrator/reference.md`
    tiene tres bloques bajo «Ejemplos de `manifest.yml`» y la clase seguiría poblada — el primer
    mutante que se escribió acá sobrevivía por eso, y el sobreviviente era el mutante, no la guarda.
    """
    for ruta in sorted((raiz / CARPETA_DE_SUPERFICIES).rglob("*.md")):
        texto = ruta.read_text(encoding="utf-8")
        nuevo = re.sub(rf"^(#{{1,6}}\s+){PREFIJO_DE_VISTA}", r"\1Muestra", texto, flags=re.M)
        if nuevo != texto:
            ruta.write_text(nuevo, encoding="utf-8")


# La skill que el caso de alta agrega al árbol copiado. No existe en el repo: si existiera, el caso
# comprobaría que la derivación ve algo que ya veía.
SKILL_DE_ALTA = "skill-sintetica-de-alta"


def _alta(raiz: Path) -> None:
    """Agrega al árbol una skill con **una superficie por cada camino de la derivación**: un dueño y
    una vista que entran por encabezado (paso 1), y un tercer bloque que solo entra por expansión de
    vocabulario (paso 2).

    El tercero es el que hace falta para que el paso 2 esté ejercido. Su encabezado no nombra ningún
    artefacto de configuración ni es la sección `Configuración`, así que el paso 1 no lo ve; lo que
    lo trae es su clave raíz `sintetica`, que el `SKILL.md` de esta misma skill declara bajo
    `Configuración` y que por eso está en el vocabulario. Es autocontenido a propósito: no depende de
    qué claves tenga el árbol real. Sin él, `derivar_superficies` puede quedarse solo con el paso 1 y
    los cinco bloques del autotest cierran en verde —se midió: el árbol pasa de 15 superficies a 12,
    y las tres que se pierden son las que documentan el esquema de config más grande del repo—.
    """
    base = raiz / CARPETA_DE_SUPERFICIES / SKILL_DE_ALTA
    base.mkdir(parents=True, exist_ok=True)
    (base / "SKILL.md").write_text(
        f"---\nname: {SKILL_DE_ALTA}\n---\n\n# {SKILL_DE_ALTA}\n\nSkill sintética.\n\n"
        f"## {HEADING_DE_CONFIGURACION}\n\n```yaml\n"
        "sintetica:\n  mode: auto\n  deadline: 600\n```\n", encoding="utf-8")
    (base / "config-ejemplo.md").write_text(
        f"# {SKILL_DE_ALTA}\n\n## {PREFIJO_DE_VISTA} de `{ARTEFACTOS_DE_CONFIGURACION[0]}`\n\n"
        "```yaml\nsintetica:\n  mode: auto\n```\n", encoding="utf-8")
    (base / "reference.md").write_text(
        f"# {SKILL_DE_ALTA} — referencia\n\n## Adaptación al proyecto\n\n"
        "El esquema, documentado bajo un encabezado que no se declara configuración.\n\n"
        "```yaml\nsintetica:\n  mode: auto\n  execution: sync\n```\n", encoding="utf-8")


def _de_la_alta(superficies: list[Superficie]) -> list[Superficie]:
    return [s for s in superficies
            if s.ruta.startswith(f"{CARPETA_DE_SUPERFICIES}/{SKILL_DE_ALTA}/")]


def _primera(superficies: list[Superficie], clase: str | None = None) -> Superficie:
    for superficie in superficies:
        if clase is None or superficie.clase == clase:
            return superficie
    raise AssertionError(f"no hay superficie de clase {clase}")


def _con_mapping_anidable(superficies: list[Superficie]) -> Superficie:
    for superficie in superficies:
        for linea in superficie.cuerpo.splitlines():
            if re.match(r"^\s*[A-Za-z_][A-Za-z0-9_]*:\s*(#.*)?$", linea):
                return superficie
    raise AssertionError("ninguna superficie tiene un mapping donde anidar una clave")


# Nombres que **no** son reservados y se parecen a los que sí lo son. Un extractor que comparara por
# subcadena —`"model" in nombre`— los rechazaría a todos, y el rojo hablaría de claves legítimas.
PARECIDOS = ("models", "model_name", "submodel", "reasoning_effort", "subagent", "profiles_dir")


def _casos_de_claves(superficies: list[Superficie], reservados: tuple[str, ...],
                     admitidos: tuple[str, ...]) -> list[CasoDeClaves]:
    """Los casos se **generan** desde el inventario derivado: la correspondencia superficie ↔ mutante
    es por construcción, y una superficie nueva en el árbol nace con su mutante en vez de nacer sin
    él y sin que nada lo señale."""
    casos: list[CasoDeClaves] = [
        CasoDeClaves(None, f"el árbol real, limpio: {len(superficies)} superficies y ninguna clave "
                           "reservada", None, None),
    ]

    # [Conformes] Los nombres que la lista admite tienen que poder aparecer, y en cualquier
    # superficie: son genéricos, o preexisten al contenedor. Uno por nombre, no uno por la lista
    # entera: con un solo caso que los inserte todos, un extractor que rechace uno de los cinco cae
    # igual y el reporte no dice cuál.
    for nombre in admitidos:
        casos.append(CasoDeClaves(
            None, f"el nombre admitido `{nombre}` aparece como clave y no es materialización",
            lambda raiz, sups, n=nombre: _insertar_en_bloque(
                raiz, _primera(sups), f"bloque_de_prueba:\n  {n}: 1"),
            None))
    for nombre in PARECIDOS:
        casos.append(CasoDeClaves(
            None, f"`{nombre}` se parece a un reservado y no lo es: la comparación es por nombre "
                  "completo",
            lambda raiz, sups, n=nombre: _insertar_en_bloque(raiz, _primera(sups), f"{n}: 1"),
            None))
    casos.append(CasoDeClaves(
        None, "prosa que nombra el contenedor fuera del bloque: no es una clave del esquema",
        lambda raiz, sups: _prosa_junto_al_bloque(raiz, _primera(sups)), None))
    casos.append(CasoDeClaves(
        None, "un comentario dentro del bloque que nombra el contenedor: el parser lo descarta",
        lambda raiz, sups: _insertar_en_bloque(
            raiz, _primera(sups),
            "# sin `subagents:` todavía — ni `profiles:`, ni `bindings:`, ni `model:`/`reasoning:`"),
        None))
    casos.append(CasoDeClaves(
        None, "un reservado como **valor** y no como clave: nombrarlo no lo declara",
        lambda raiz, sups: _insertar_en_bloque(
            raiz, _primera(sups), "bloque_de_prueba:\n  que_delega: subagents\n  con: model"),
        None))

    # [A] Un mutante por superficie, no uno por clase. Con uno por clase, un extractor limitado al
    # dueño y a la vista elegidos para los fixtures pasa los dos y deja el resto sin inspeccionar.
    for superficie in superficies:
        casos.append(CasoDeClaves(
            "clave_reservada",
            f"{superficie.clase} `{superficie.ruta} → {superficie.heading}`: se materializa el "
            "contenedor en su bloque",
            lambda raiz, sups, s=superficie: _insertar_en_bloque(
                raiz, _buscar(sups, s.identificador), "subagents:\n  profiles: {}"),
            superficie.identificador))

    # [B] Un mutante por nombre reservado, repartidos por el inventario: la familia [A] ejerce un
    # solo nombre, y un extractor que buscara únicamente la clave raíz pasaría los otros cuatro.
    for indice, nombre in enumerate(reservados):
        destino = superficies[indice % len(superficies)]
        casos.append(CasoDeClaves(
            "clave_reservada",
            f"el reservado `{nombre}` como clave raíz de `{destino.ruta} → {destino.heading}`",
            lambda raiz, sups, n=nombre, s=destino: _insertar_en_bloque(
                raiz, _buscar(sups, s.identificador), f"{n}: valor"),
            destino.identificador))

    # [C] Anidado: el nombre no deja de estar reservado por colgar de otro bloque del esquema.
    anidable = _con_mapping_anidable(superficies)
    for nombre in ("model", "reasoning"):
        casos.append(CasoDeClaves(
            "clave_reservada",
            f"`{nombre}` anidado bajo un mapping de `{anidable.ruta} → {anidable.heading}`",
            lambda raiz, sups, n=nombre, s=anidable: _insertar_anidado(
                raiz, _buscar(sups, s.identificador), n),
            anidable.identificador))

    # [D] La derivación misma. Sin estos casos, un inventario que se vaciara daría verde por no
    # haber mirado nada, que es la forma en que esta guarda no podría ponerse roja.
    casos += [
        CasoDeClaves("sin_superficies", "el árbol se queda sin superficies de configuración",
                     lambda raiz, sups: shutil.rmtree(raiz / CARPETA_DE_SUPERFICIES), None),
        CasoDeClaves("clase_sin_superficies",
                     "ningún encabezado se declara un ejemplo y la clase `vista` desaparece",
                     lambda raiz, sups: _sin_vistas(raiz), None),
        CasoDeClaves("bloque_ilegible", "el bloque de una superficie deja de componer como YAML",
                     lambda raiz, sups: _insertar_en_bloque(
                         raiz, _primera(sups), "clave: [sin cerrar"), None),
        CasoDeClaves("lista_ilegible", "la lista de nombres reservados no se puede leer", None, None),
    ]
    return casos


def _buscar(superficies: list[Superficie], identificador: str) -> Superficie:
    for superficie in superficies:
        if superficie.identificador == identificador:
            return superficie
    raise AssertionError(f"la superficie `{identificador}` no está en el inventario derivado")


def _correr_caso_de_claves(caso: CasoDeClaves,
                           ruta_lista: Path) -> tuple[list[Problema], dict, list[Superficie]]:
    """Cada caso corre sobre una copia temporal del árbol: los mutantes escriben archivos, y hacerlo
    sobre el worktree lo dejaría alterado si el proceso muriera a mitad."""
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "arbol"
        shutil.copytree(REPO / CARPETA_DE_SUPERFICIES, raiz / CARPETA_DE_SUPERFICIES)
        if caso.mutar is not None:
            caso.mutar(raiz, derivar_superficies(raiz))
        problemas, resumen = verificar_claves_perfil(raiz, ruta_lista)
        posteriores = derivar_superficies(raiz) if (raiz / CARPETA_DE_SUPERFICIES).is_dir() else []
        return problemas, resumen, posteriores


def _lista_ilegible() -> Path:
    """Una ruta que no existe: el modo no puede saber qué buscar y eso es rojo, no verde."""
    return REPO / "scripts" / "nombres-reservados-perfil.inexistente.json"


def _bloque_de_alta(base: int) -> list[tuple[str, bool, str]]:
    """[E] La derivación tiene que ver una skill que hasta recién no existía.

    Los bloques [A]–[D] generan sus casos del **mismo** inventario que el modo deriva, así que una
    derivación recortada recorta también sus mutantes y los cuatro cierran en verde comparando el
    inventario contra sí mismo: un `derivar_superficies` reemplazado por una lista de rutas escrita a
    mano los sobrevive a todos. Se comprobó mutando este archivo en una copia, y fue el único de once
    ataques que escapó. Lo que lo caza es un árbol que el inventario a mano no puede haber previsto:
    se agrega una skill nueva y se exige que la derivación la vea y que sus claves reservadas caigan.

    **Y se exige por camino, no en total.** El mismo defecto tiene una segunda forma: recortar la
    derivación a uno de sus dos pasos. Con un alta cuyas superficies entraran todas por encabezado,
    el paso de expansión por vocabulario se puede borrar entero y los cinco bloques siguen en verde
    —medido: el árbol pasa de 15 superficies a 12 sin que nada se ponga rojo—. Por eso el alta trae
    **tres** superficies, una por cada camino, y acá se comprueba que estén los dos orígenes y las
    dos clases: un total correcto por la suma de dos caminos, con uno de ellos muerto, no lo es.
    """
    limpio = CasoDeClaves(None, "alta limpia", lambda raiz, sups: _alta(raiz), None)
    problemas, _, posteriores = _correr_caso_de_claves(limpio, RUTA_NOMBRES_RESERVADOS)
    nuevas = _de_la_alta(posteriores)
    clases = {s.clase for s in nuevas}
    origenes = {s.origen for s in nuevas}
    fallas: list[str] = []
    if problemas:
        fallas.append(f"el alta limpia no pasa: {problemas[0]}")
    if len(posteriores) != base + 3:
        fallas.append(f"la derivación ve {len(posteriores) - base} superficies nuevas, esperadas 3")
    if clases != {"dueño", "vista"} or origenes != {"encabezado", "vocabulario"}:
        fallas.append(f"las superficies del alta son de clases {sorted(clases)} y orígenes "
                      f"{sorted(origenes)}: falta un camino de la derivación o una clase")
    resultados = [(
        "E.1/claves-perfil", not fallas,
        f"la derivación ve la skill nueva por sus dos caminos: {base} → {len(posteriores)} "
        "superficies, con las dos clases y los dos orígenes"
        if not fallas else " | ".join(fallas),
    )]
    if fallas:
        return resultados

    sobrevivientes: list[str] = []
    for nueva in nuevas:
        def mutar(raiz: Path, sups: list[Superficie], destino: str = nueva.identificador) -> None:
            _alta(raiz)
            _insertar_en_bloque(raiz, _buscar(derivar_superficies(raiz), destino),
                                "subagents:\n  bindings: {}")
        caso = CasoDeClaves("clave_reservada", f"alta mutada: {nueva.donde}", mutar,
                            nueva.identificador)
        detectados, _, finales = _correr_caso_de_claves(caso, RUTA_NOMBRES_RESERVADOS)
        donde = _buscar(finales, nueva.identificador).donde
        if not any(p.codigo == "clave_reservada" and p.donde == donde for p in detectados):
            sobrevivientes.append(f"{nueva.clase} `{donde}` — {sorted({p.donde for p in detectados})[:2]}")
    resultados.append((
        "E.2/claves-perfil", not sobrevivientes,
        f"las {len(nuevas)} superficies del alta se inspeccionan, una por camino: su clave "
        "reservada cae en las tres"
        if not sobrevivientes else "SOBREVIVE " + " | ".join(sobrevivientes),
    ))
    return resultados


def modo_autotest_claves_perfil() -> int:
    if _yaml is None:
        print("[0] FALLA  falta PyYAML: sin el parser no hay extracción estructural")
        return 1

    reservados, admitidos, error = nombres_reservados(RUTA_NOMBRES_RESERVADOS)
    if error:
        return _cierre("claves de perfil", [("0.lista", False, error)])
    superficies = derivar_superficies(REPO)
    resultados: list[tuple[str, bool, str]] = [
        ("0.inventario", bool(superficies),
         f"el inventario se deriva del árbol: {len(superficies)} superficies "
         f"({sum(1 for s in superficies if s.clase == 'dueño')} dueños, "
         f"{sum(1 for s in superficies if s.clase == 'vista')} vistas)"
         if superficies else "la derivación no produjo superficies"),
    ]
    if not superficies:
        return _cierre("claves de perfil", resultados)

    casos = _casos_de_claves(superficies, reservados, admitidos)

    # [A] El control positivo. Sin él, un extractor que devuelva siempre rojo —`return
    # [Problema(...)]`— satisface todos los mutantes y cierra en verde sin haber aceptado jamás un
    # árbol sano.
    conformes = [c for c in casos if c.codigo is None]
    fallas: list[str] = []
    for caso in conformes:
        problemas, _, _ = _correr_caso_de_claves(caso, RUTA_NOMBRES_RESERVADOS)
        if problemas:
            fallas.append(f"{caso.descripcion} — {problemas[0]}")
    resultados.append((
        "A/claves-perfil", not fallas,
        f"control positivo: los {len(conformes)} casos conformes pasan, incluidos los "
        f"{len(admitidos)} nombres admitidos y los {len(PARECIDOS)} parecidos"
        if not fallas else "control positivo — " + " | ".join(fallas[:3]),
    ))

    # [B] Los mutantes, cada uno rechazado por su motivo **y atribuido a su superficie**: un
    # extractor que mirara una sola superficie sobrevive a los mutantes de las demás.
    mutantes = [c for c in casos if c.codigo is not None]
    sobrevivientes: list[str] = []
    desatribuidos: list[str] = []
    emitidos: set[str] = set()
    for caso in mutantes:
        problemas, _, posteriores = _correr_caso_de_claves(
            caso, _lista_ilegible() if caso.codigo == "lista_ilegible" else RUTA_NOMBRES_RESERVADOS)
        codigos = {p.codigo for p in problemas}
        emitidos |= codigos
        if not codigos:
            sobrevivientes.append(f"{caso.codigo}: {caso.descripcion}")
            continue
        if caso.codigo not in codigos:
            desatribuidos.append(f"{caso.codigo}: {caso.descripcion} — rechazado por "
                                 f"{sorted(codigos)} y no por su motivo")
            continue
        if caso.superficie is None:
            continue
        donde = _buscar(posteriores, caso.superficie).donde
        if not any(p.codigo == caso.codigo and p.donde == donde for p in problemas):
            desatribuidos.append(f"{caso.codigo}: {caso.descripcion} — el problema no se atribuye a "
                                 f"`{donde}` sino a {sorted({p.donde for p in problemas})[:2]}")
    problemas_b = ([f"SOBREVIVE {s}" for s in sobrevivientes]
                   + [f"SIN ATRIBUIR {d}" for d in desatribuidos])
    resultados.append((
        "B/claves-perfil", not problemas_b,
        f"{len(mutantes)} mutantes rechazados por su motivo, uno por cada una de las "
        f"{len(superficies)} superficies y uno por cada uno de los {len(reservados)} nombres"
        if not problemas_b else f"{len(problemas_b)} problemas: " + " | ".join(problemas_b[:5]),
    ))

    # [C] Un caso por código: un código sin caso es una restricción que nadie comprobó que pueda
    # ponerse roja.
    ejercidos = {c.codigo for c in mutantes}
    problemas_c = [f"`{c}` está en el catálogo y ningún caso lo ejerce"
                   for c in CODIGOS_CLAVES_PERFIL if c not in ejercidos]
    problemas_c += [f"`{c}` lo emite el modo y no está en el catálogo"
                    for c in sorted((emitidos | ejercidos) - set(CODIGOS_CLAVES_PERFIL))]
    resultados.append((
        "C/claves-perfil", not problemas_c,
        f"los {len(CODIGOS_CLAVES_PERFIL)} códigos del modo tienen su caso"
        if not problemas_c else f"{len(problemas_c)} huecos: " + " | ".join(problemas_c[:5]),
    ))

    # [D] Cada superficie del inventario tiene su mutante. Es la comprobación de que la familia [A]
    # se generó del inventario y no de una lista escrita a mano que quedó corta.
    con_mutante = {c.superficie for c in mutantes if c.superficie is not None}
    faltantes = [s.donde for s in superficies if s.identificador not in con_mutante]
    resultados.append((
        "D/claves-perfil", not faltantes,
        f"las {len(superficies)} superficies derivadas tienen su mutante, una por una"
        if not faltantes else f"{len(faltantes)} sin mutante: " + " | ".join(faltantes[:5]),
    ))

    resultados += _bloque_de_alta(len(superficies))
    return _cierre("ningún nombre reservado al contenedor de perfiles aparece como clave en una "
                   "superficie de configuración, y cada superficie tiene quien la mute", resultados)


# ---------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------
# El parser del reporte de paridad.
#
# `verificar-paridad-powershell.py --reporte` devuelve **4 y ese es su estado sano**: cinco pares
# del arnés declaran un caso cuya clase esperada es `fallo` —invocaciones sobre una entrada
# inexistente, que no son incumplimientos—, y la precedencia global hace que cualquier `fallo`
# domine el código de salida. Leer ese 4 como enfermedad es el malentendido que este modo existe
# para cerrar, así que la salud se lee del **cuerpo** del reporte.
#
# Tres decisiones gobiernan lo de abajo:
#
# 1. **La propiedad es igualdad de identidades, no un tope de cantidad.** El conjunto de pares con
#    `fallo` tiene que ser exactamente igual al autorizado. Un parser que aceptara «hasta cinco
#    pares con fallo» rechazaría el sexto y dejaría pasar la sustitución de un autorizado por otro
#    que no lo es, que es el cambio que de verdad rompe la norma sin cambiar el conteo.
# 2. **El vocabulario de clases se deriva del arnés**, no se transcribe: una clase nueva allá
#    nacería acá sin mutante y sin prohibición. Lo que este archivo congela es el **criterio**
#    —cualquier clase que no sea `paridad` ni `fallo` está prohibida— y el testigo de los cinco
#    autorizados.
# 3. **La tabla se parsea por tokens y por literales, nunca por columnas.** Está alineada por
#    espacios y no lleva separadores: un predicado que busque `|` devuelve cero filas y con ellas
#    un verde que contradice la norma. Ya ocurrió una vez, con `grep`.
#
# Y el estado de fila `sin casos` **no es una clase**: no aparece en el vocabulario y sin embargo
# aporta `fallo` al código global. Un parser que solo buscara los literales de clase lo dejaría
# pasar, así que se reconoce aparte.
# ---------------------------------------------------------------------------------------------

RUTA_ARNES_PARIDAD = REPO / "scripts" / "verificar-paridad-powershell.py"
DIR_CASOS_PARIDAD = REPO / "scripts" / "paridad-casos"
DIR_FIXTURES_PARIDAD = DIR_FIXTURES / "paridad"

# Los dos estados de fila que el arnés emite y que **no** son clases de resultado. El primero es
# una exclusión declarada —el par no se comprobó y eso está decidido en `alcance.json`—; el segundo
# es un par cubierto que se quedó sin matriz de casos, que el arnés cuenta como `fallo` en el
# global aunque la fila no lo diga. Se comprueba que sigan siendo estos literales en [0.formato].
ESTADO_SIN_MATRIZ = "sin matriz (no comprobado)"
ESTADO_SIN_CASOS = "sin casos"

ENCABEZADO_TABLA = ("par", "resultado", "evidencia")
PREFIJO_INTERPRETE = "intérprete:"
MARCA_INTERPRETE_AUSENTE = "AUSENTE"
PREFIJO_GLOBAL = "resultado global: "

# La única clase sana por sí sola. `fallo` es sana **solo** en los pares autorizados; cualquier otra
# está prohibida siempre, incluida una que el arnés agregue mañana (mundo cerrado a propósito).
CLASE_SANA = "paridad"
CLASE_FALLO = "fallo"

# El testigo de los cinco pares autorizados. NO es la fuente de verdad: la fuente es qué pares
# declaran un caso con `clase_esperada: fallo` en `scripts/paridad-casos/<par>/casos.json`, y eso se
# **deriva** en `derivar_pares_con_fallo_declarado`. Esto es lo que permite que el modo funcione
# sobre un reporte suelto sin el arnés al lado, y lo que hace que una divergencia entre las dos
# fuentes sea visible en vez de silenciosa: el autotest compara las dos y se pone rojo si difieren.
PARES_CON_FALLO_AUTORIZADO = (
    "gate-fase-3",
    "integracion-ownership",
    "orchestration-contract",
    "orchestration-model",
    "orchestration-state",
)

CODIGOS_FIJOS_PAREAR = (
    "reporte_ilegible",
    "interprete_ausente",
    "estado_no_reconocido",
    "sin_casos",
    "fallo_no_autorizado",
    "fallo_autorizado_ausente",
    "global_incoherente",
    "codigo_incoherente",
)


def vocabulario_de_paridad(ruta_arnes: Path) -> tuple[list[str], dict[str, int], str | None]:
    """El vocabulario de clases y su código, derivados del arnés **sin ejecutarlo**.

    Se leen `PRECEDENCIA` y `CODIGO` del módulo por AST. Transcribirlos acá dejaría que una clase
    nueva del arnés naciera sin prohibición ni mutante; importarlo ejecutaría su cuerpo, que detecta
    intérpretes y toca el disco. Devuelve (precedencia, códigos, error).
    """
    try:
        arbol = ast.parse(ruta_arnes.read_text(encoding="utf-8"), filename=str(ruta_arnes))
    except (OSError, SyntaxError) as exc:
        return [], {}, f"no se puede derivar el vocabulario de {ruta_arnes.name}: {exc}"

    hallados: dict[str, Any] = {}
    for nodo in arbol.body:
        if not isinstance(nodo, ast.Assign):
            continue
        for destino in nodo.targets:
            if isinstance(destino, ast.Name) and destino.id in ("PRECEDENCIA", "CODIGO"):
                try:
                    hallados[destino.id] = ast.literal_eval(nodo.value)
                except ValueError:
                    return [], {}, f"`{destino.id}` de {ruta_arnes.name} no es un literal"

    precedencia = hallados.get("PRECEDENCIA")
    codigos = hallados.get("CODIGO")
    if not isinstance(precedencia, list) or not all(isinstance(c, str) for c in precedencia):
        return [], {}, f"{ruta_arnes.name} no declara `PRECEDENCIA` como lista de clases"
    if not isinstance(codigos, dict):
        return [], {}, f"{ruta_arnes.name} no declara `CODIGO` como diccionario"
    if set(precedencia) != set(codigos):
        return [], {}, (f"`PRECEDENCIA` y `CODIGO` de {ruta_arnes.name} no cubren las mismas "
                        f"clases: {sorted(set(precedencia) ^ set(codigos))}")
    if CLASE_SANA not in precedencia or CLASE_FALLO not in precedencia:
        return [], {}, (f"el vocabulario de {ruta_arnes.name} no incluye `{CLASE_SANA}` y "
                        f"`{CLASE_FALLO}`, sobre las que este modo define la salud")
    return precedencia, codigos, None


def codigos_de_parear(precedencia: list[str]) -> tuple[str, ...]:
    """El catálogo del modo: los códigos fijos más uno **por clase prohibida derivada**. Una clase
    nueva en el arnés entra sola al catálogo, y el bloque [C] exige entonces que alguien la ejerza."""
    return CODIGOS_FIJOS_PAREAR + tuple(
        f"clase_{c}" for c in precedencia if c not in (CLASE_SANA, CLASE_FALLO))


def derivar_pares_con_fallo_declarado(dir_casos: Path) -> tuple[tuple[str, ...], str | None]:
    """Los pares autorizados a fallar, derivados de su matriz de casos: los que declaran al menos un
    caso con `clase_esperada: fallo`. Es la definición operativa de la norma —«los pares que declaran
    un caso de ese tipo»— y no una lista escrita a mano."""
    if not dir_casos.is_dir():
        return (), f"no está el directorio de casos del arnés ({dir_casos})"
    con_fallo: list[str] = []
    for sub in sorted(dir_casos.iterdir()):
        ruta = sub / "casos.json"
        if not sub.is_dir() or not ruta.is_file():
            continue
        datos, error = _cargar_json(ruta)
        if error:
            return (), error
        casos = datos.get("casos") if isinstance(datos, dict) else None
        if not isinstance(casos, list):
            return (), f"{ruta}: no declara una lista `casos`"
        if any(isinstance(c, dict) and c.get("clase_esperada") == CLASE_FALLO for c in casos):
            con_fallo.append(sub.name)
    return tuple(con_fallo), None


class FilaDeReporte(NamedTuple):
    par: str
    estado: str
    evidencia: str
    linea: int


class ReporteDeParidad(NamedTuple):
    filas: tuple[FilaDeReporte, ...]
    interprete: str | None
    interprete_ausente: bool
    clase_global: str | None
    codigo_global: int | None
    texto_global: str | None
    errores: tuple[str, ...]


def _es_raya_del_reporte(linea_de_reporte: str) -> bool:
    desnuda = linea_de_reporte.strip()
    return len(desnuda) >= 3 and set(desnuda) == {"-"}


def parsear_reporte(texto: str, clases: list[str]) -> ReporteDeParidad:
    """Lee el reporte por tokens: el primer campo de cada fila es el par —los nombres son slugs sin
    espacios— y el resto empieza por uno de los literales conocidos. Los literales se prueban de
    más largo a más corto porque `sin matriz (no comprobado)` y `sin casos` comparten prefijo."""
    lineas = texto.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    errores: list[str] = []

    interprete = None
    ausente = False
    for linea in lineas:
        if linea.startswith(PREFIJO_INTERPRETE):
            interprete = linea[len(PREFIJO_INTERPRETE):].strip()
            ausente = interprete.startswith(MARCA_INTERPRETE_AUSENTE)
            break
    if interprete is None:
        errores.append(f"el reporte no declara `{PREFIJO_INTERPRETE}`: está truncado o no es un "
                       "reporte de paridad")

    texto_global = None
    for linea in lineas:
        if linea.startswith(PREFIJO_GLOBAL):
            texto_global = linea[len(PREFIJO_GLOBAL):].strip()
            break
    clase_global: str | None = None
    codigo_global: int | None = None
    if texto_global is None:
        errores.append(f"el reporte no declara `{PREFIJO_GLOBAL.strip()}`")
    else:
        m = re.fullmatch(r"(?P<clase>.+?) \(código (?P<codigo>\d+)\)", texto_global)
        if m:
            clase_global = m.group("clase")
            codigo_global = int(m.group("codigo"))

    inicio = next((i for i, l in enumerate(lineas) if tuple(l.split()) == ENCABEZADO_TABLA), None)
    filas: list[FilaDeReporte] = []
    if inicio is None:
        if not ausente:
            errores.append("el reporte no tiene la tabla de pares: no se encontró el encabezado "
                           f"`{' '.join(ENCABEZADO_TABLA)}`")
    elif inicio + 1 >= len(lineas) or not _es_raya_del_reporte(lineas[inicio + 1]):
        errores.append("al encabezado de la tabla no le sigue su línea separadora")
    else:
        cierre = next((i for i in range(inicio + 2, len(lineas)) if _es_raya_del_reporte(lineas[i])), None)
        if cierre is None:
            errores.append("la tabla de pares no cierra con su línea separadora")
        else:
            candidatos = sorted(list(clases) + [ESTADO_SIN_MATRIZ, ESTADO_SIN_CASOS],
                                key=len, reverse=True)
            for i in range(inicio + 2, cierre):
                cruda = lineas[i]
                if not cruda.strip():
                    continue
                partes = cruda.split(None, 1)
                par = partes[0]
                resto = partes[1].rstrip() if len(partes) > 1 else ""
                estado = next((c for c in candidatos
                               if resto == c or resto.startswith(c + " ")), None)
                if estado is None:
                    filas.append(FilaDeReporte(par, resto, "", i + 1))
                else:
                    filas.append(FilaDeReporte(par, estado, resto[len(estado):].strip(), i + 1))
            if not filas:
                errores.append("la tabla de pares está vacía")

    return ReporteDeParidad(tuple(filas), interprete, ausente,
                            clase_global, codigo_global, texto_global, tuple(errores))


def verificar_reporte_de_paridad(
    texto: str,
    autorizados: tuple[str, ...],
    precedencia: list[str],
    codigos: dict[str, int],
    codigo_de_salida: int | None = None,
) -> tuple[list[Problema], dict]:
    """El criterio de AC-26 sobre el cuerpo del reporte: cero clases prohibidas, `fallo` exactamente
    en los pares autorizados, y ninguna fila con una forma que el arnés no emita.

    El código de salida **no** entra en el veredicto: se coteja contra el que el propio reporte
    declara y se informa. Un 4 coherente con la tabla es un reporte sano.
    """
    reporte = parsear_reporte(texto, precedencia)
    problemas: list[Problema] = []
    resumen: dict[str, Any] = {
        "pares": len(reporte.filas),
        "comprobados": 0,
        "exclusiones": [],
        "con_fallo": [],
        "autorizados": list(autorizados),
        "por_clase": {},
        "clase_global": reporte.clase_global,
        "codigo_global": reporte.codigo_global,
        "codigo_de_salida": codigo_de_salida,
        "interprete": reporte.interprete,
    }

    for error in reporte.errores:
        problemas.append(Problema("reporte_ilegible", "reporte", error))
    if reporte.interprete_ausente:
        problemas.append(Problema(
            "interprete_ausente", "reporte",
            f"la corrida no comprobó un solo par: {reporte.interprete}"))
    if problemas:
        return problemas, resumen

    por_clase: dict[str, list[str]] = {}
    con_fallo: list[str] = []
    for fila in reporte.filas:
        if fila.estado == ESTADO_SIN_MATRIZ:
            resumen["exclusiones"].append(fila.par)
            continue
        if fila.estado == ESTADO_SIN_CASOS:
            problemas.append(Problema(
                "sin_casos", fila.par,
                f"línea {fila.linea}: cubierto y sin matriz de casos — el arnés lo cuenta como "
                f"`{CLASE_FALLO}` en el global aunque la fila no lo diga"))
            continue
        if fila.estado not in precedencia:
            problemas.append(Problema(
                "estado_no_reconocido", fila.par,
                f"línea {fila.linea}: `{fila.estado}` no es una clase del arnés ni un estado de "
                "fila conocido — una forma no reconocida es rojo, no omisión"))
            continue
        resumen["comprobados"] += 1
        por_clase.setdefault(fila.estado, []).append(fila.par)
        if fila.estado == CLASE_FALLO:
            con_fallo.append(fila.par)
        elif fila.estado != CLASE_SANA:
            problemas.append(Problema(
                f"clase_{fila.estado}", fila.par,
                f"línea {fila.linea}: la norma exige cero `{fila.estado}` — {fila.evidencia}"))

    resumen["por_clase"] = {c: sorted(p) for c, p in sorted(por_clase.items())}
    resumen["con_fallo"] = sorted(con_fallo)

    # La igualdad de identidades, en sus dos direcciones. Solo la primera dejaría pasar un
    # autorizado que dejó de fallar; solo la segunda, cualquier par nuevo que empiece a fallar.
    permitidos = set(autorizados)
    for par in sorted(set(con_fallo) - permitidos):
        problemas.append(Problema(
            "fallo_no_autorizado", par,
            f"`{CLASE_FALLO}` en un par que no lo declara: los autorizados son "
            f"{sorted(permitidos)}"))
    for par in sorted(permitidos - set(con_fallo)):
        problemas.append(Problema(
            "fallo_autorizado_ausente", par,
            f"declara un caso `{CLASE_FALLO}` y el reporte no lo muestra fallando: el conjunto con "
            f"`{CLASE_FALLO}` tiene que ser **igual** al autorizado, no estar contenido en él"))

    # Coherencia entre la tabla y la línea global. Sin ella, un reporte al que le recortaron filas
    # —o al que le reescribieron el pie— pasaría por sano leyendo solo lo que quedó.
    contribuciones = [f.estado for f in reporte.filas if f.estado in precedencia]
    contribuciones += [CLASE_FALLO for f in reporte.filas if f.estado == ESTADO_SIN_CASOS]
    peor = (max(contribuciones, key=precedencia.index) if contribuciones else CLASE_FALLO)
    resumen["peor_observado"] = peor
    if reporte.clase_global is None:
        problemas.append(Problema(
            "global_incoherente", "reporte",
            f"la línea global dice `{reporte.texto_global}` y no declara clase con su código"))
    else:
        if reporte.clase_global != peor:
            problemas.append(Problema(
                "global_incoherente", "reporte",
                f"la tabla da `{peor}` por precedencia y la línea global declara "
                f"`{reporte.clase_global}`"))
        esperado = codigos.get(reporte.clase_global)
        if esperado is not None and esperado != reporte.codigo_global:
            problemas.append(Problema(
                "global_incoherente", "reporte",
                f"`{reporte.clase_global}` es el código {esperado} en el arnés y la línea global "
                f"declara el {reporte.codigo_global}"))

    if codigo_de_salida is not None and reporte.codigo_global is not None \
            and codigo_de_salida != reporte.codigo_global:
        problemas.append(Problema(
            "codigo_incoherente", "reporte",
            f"la corrida devolvió {codigo_de_salida} y el reporte declara "
            f"{reporte.codigo_global}: uno de los dos no es de esta corrida"))

    return problemas, resumen


# --- Modo de aplicación -----------------------------------------------------------------------

def _leer_reporte(ruta: str) -> tuple[str, str | None]:
    if ruta == "-":
        return sys.stdin.read(), None
    try:
        return Path(ruta).read_text(encoding="utf-8"), None
    except OSError as exc:
        return "", f"no se puede leer el reporte: {exc}"


def modo_parear_reporte(ruta: str, autorizados: tuple[str, ...] | None,
                        codigo_de_salida: int | None) -> int:
    precedencia, codigos, error = vocabulario_de_paridad(RUTA_ARNES_PARIDAD)
    if error:
        print(f"FALLA  parear-reporte: {error}")
        return 1
    texto, error = _leer_reporte(ruta)
    if error:
        print(f"FALLA  parear-reporte: {error}")
        return 1

    if autorizados is None:
        derivados, error = derivar_pares_con_fallo_declarado(DIR_CASOS_PARIDAD)
        if error:
            print(f"AVISO  {error}")
            print(f"       se usa el testigo congelado: {list(PARES_CON_FALLO_AUTORIZADO)}")
            autorizados = PARES_CON_FALLO_AUTORIZADO
        else:
            autorizados = derivados
            if set(derivados) != set(PARES_CON_FALLO_AUTORIZADO):
                print("FALLA  parear-reporte: los pares que declaran un caso `fallo` en el arnés "
                      f"({sorted(derivados)}) no son los del testigo congelado "
                      f"({sorted(PARES_CON_FALLO_AUTORIZADO)}): la norma del repositorio y el arnés "
                      "dejaron de decir lo mismo y este modo no puede decidir por su cuenta cuál "
                      "manda")
                return 1

    problemas, resumen = verificar_reporte_de_paridad(
        texto, autorizados, precedencia, codigos, codigo_de_salida)
    origen = "stdin" if ruta == "-" else Path(ruta).name
    if problemas:
        _informar(problemas, f"{origen}: el reporte de paridad no está sano")
        return 1

    prohibidas = [c for c in precedencia if c not in (CLASE_SANA, CLASE_FALLO)]
    excluidos = resumen["exclusiones"]
    print(f"OK     {origen}: {resumen['comprobados']} pares comprobados y "
          f"{len(excluidos)} {'exclusión declarada' if len(excluidos) == 1 else 'exclusiones declaradas'}"
          f" ({', '.join(excluidos) or 'ninguna'})")
    print(f"OK     cero {', cero '.join(prohibidas)}")
    print(f"OK     `{CLASE_FALLO}` exactamente en los {len(resumen['con_fallo'])} pares "
          f"autorizados: {', '.join(resumen['con_fallo'])}")
    print(f"OK     la tabla y la línea global coinciden en `{resumen['peor_observado']}` "
          f"(código {resumen['codigo_global']}), y ese código NO se lee como enfermedad")
    print()
    print("RESULTADO: OK")
    return 0


# --- Autotest: el corpus sintético y sus mutantes ----------------------------------------------
#
# Los conformes viven en disco (`scripts/fixtures-matriz/paridad/`) y los mutantes se **generan**
# transformándolos. Guardar los mutantes como archivos los volvería una transcripción a mano de algo
# que el vocabulario ya declara: una clase nueva en el arnés nacería sin mutante y nadie lo notaría.
# Generándolos, la correspondencia clase ↔ mutante es por construcción.

FIXTURE_CONFORME = "conforme-sintetico.txt"
FIXTURE_IDENTIDADES = "conforme-identidades.txt"
FIXTURE_CINCO_CLASES = "cinco-clases.txt"
FIXTURE_SIN_INTERPRETE = "interprete-ausente.txt"

# Los autorizados del conforme sintético. Sus pares no existen en el arnés real a propósito: un
# fixture copiado del reporte real haría que el parser y el dato acordaran entre sí.
AUTORIZADOS_SINTETICOS = ("fixture-beta", "fixture-gamma")


class CasoDeReporte(NamedTuple):
    codigo: str | None
    descripcion: str
    fixture: str
    mutar: Any  # Callable[[str, list[str], dict[str, int]], str] | None
    autorizados: tuple[str, ...]
    codigo_de_salida: int | None


def _fila_formateada(par: str, estado: str, evidencia: str) -> str:
    """El mismo formateo que `cmd_reporte`: nombre a 30, estado a 22, evidencia libre."""
    return f"{par:<30} {estado:<22} {evidencia}".rstrip()


def _reescribir_fila(texto: str, par: str, estado: str, evidencia: str) -> str:
    lineas = texto.split("\n")
    for i, linea in enumerate(lineas):
        partes = linea.split(None, 1)
        if partes and partes[0] == par and not _es_raya_del_reporte(linea):
            lineas[i] = _fila_formateada(par, estado, evidencia)
    return "\n".join(lineas)


def _sincronizar_global(texto: str, precedencia: list[str], codigos: dict[str, int]) -> str:
    """Reescribe la línea global con lo que la tabla mutada implica.

    Sin esto, todo mutante de clase caería además por `global_incoherente` y ninguno probaría lo
    suyo: el mutante tiene que romper **una** cosa."""
    reporte = parsear_reporte(texto, precedencia)
    contribuciones = [f.estado for f in reporte.filas if f.estado in precedencia]
    contribuciones += [CLASE_FALLO for f in reporte.filas if f.estado == ESTADO_SIN_CASOS]
    peor = max(contribuciones, key=precedencia.index) if contribuciones else CLASE_FALLO
    lineas = texto.split("\n")
    for i, linea in enumerate(lineas):
        if linea.startswith(PREFIJO_GLOBAL):
            lineas[i] = f"{PREFIJO_GLOBAL}{peor} (código {codigos[peor]})"
    return "\n".join(lineas)


def _mutar_estado(par: str, estado: str, evidencia: str):
    def mutar(texto: str, precedencia: list[str], codigos: dict[str, int]) -> str:
        return _sincronizar_global(_reescribir_fila(texto, par, estado, evidencia),
                                   precedencia, codigos)
    return mutar


def _mutar_global(clase: str):
    def mutar(texto: str, precedencia: list[str], codigos: dict[str, int]) -> str:
        lineas = texto.split("\n")
        for i, linea in enumerate(lineas):
            if linea.startswith(PREFIJO_GLOBAL):
                lineas[i] = f"{PREFIJO_GLOBAL}{clase} (código {codigos[clase]})"
        return "\n".join(lineas)
    return mutar


def _mutar_sustitucion(texto: str, precedencia: list[str], codigos: dict[str, int]) -> str:
    """Sustituye un `fallo` autorizado por uno que no lo es **conservando la cantidad**. Es el caso
    que separa la igualdad de identidades del tope de cantidad: un parser que contara lo pasaría."""
    salida = _reescribir_fila(texto, "fixture-beta", CLASE_SANA, "4 casos · paridad")
    salida = _reescribir_fila(salida, "fixture-delta", CLASE_FALLO, "12 casos · fallo, paridad")
    return _sincronizar_global(salida, precedencia, codigos)


def _mutar_sin_encabezado(texto: str, precedencia: list[str], codigos: dict[str, int]) -> str:
    return "\n".join(l for l in texto.split("\n") if tuple(l.split()) != ENCABEZADO_TABLA)


def _casos_de_reporte(precedencia: list[str]) -> tuple[CasoDeReporte, ...]:
    """Los casos, con una familia **derivada por clase prohibida**: si el arnés agrega una clase, su
    mutante aparece solo. Uno por clase y no uno por categoría."""
    casos: list[CasoDeReporte] = [
        CasoDeReporte(None, "el conforme sintético: paridad salvo sus dos autorizados, y la línea "
                            "global en `fallo (código 4)`",
                      FIXTURE_CONFORME, None, AUTORIZADOS_SINTETICOS, 4),
        CasoDeReporte(None, "el conforme de identidades: `fallo` exactamente en los cinco pares "
                            "autorizados del repositorio, con código de salida 4",
                      FIXTURE_IDENTIDADES, None, PARES_CON_FALLO_AUTORIZADO, 4),
    ]
    for clase in precedencia:
        if clase in (CLASE_SANA, CLASE_FALLO):
            continue
        casos.append(CasoDeReporte(
            f"clase_{clase}", f"un par sano pasa a `{clase}`", FIXTURE_CONFORME,
            _mutar_estado("fixture-alfa", clase, f"7 casos · {clase}, paridad"),
            AUTORIZADOS_SINTETICOS, None))
    casos += [
        CasoDeReporte("fallo_no_autorizado",
                      "aparece un `fallo` en un par que no lo declara (los dos autorizados siguen)",
                      FIXTURE_CONFORME,
                      _mutar_estado("fixture-delta", CLASE_FALLO, "12 casos · fallo, paridad"),
                      AUTORIZADOS_SINTETICOS, None),
        CasoDeReporte("fallo_autorizado_ausente",
                      "un par autorizado deja de fallar: el conjunto se achica",
                      FIXTURE_CONFORME,
                      _mutar_estado("fixture-beta", CLASE_SANA, "4 casos · paridad"),
                      AUTORIZADOS_SINTETICOS, None),
        CasoDeReporte("fallo_no_autorizado",
                      "se sustituye un `fallo` autorizado por uno que no lo es, **conservando la "
                      "cantidad**",
                      FIXTURE_CONFORME, _mutar_sustitucion, AUTORIZADOS_SINTETICOS, None),
        CasoDeReporte("sin_casos",
                      "un par cubierto se queda sin matriz: aporta `fallo` al global sin decirlo",
                      FIXTURE_CONFORME,
                      _mutar_estado("fixture-delta", ESTADO_SIN_CASOS, ""),
                      AUTORIZADOS_SINTETICOS, None),
        CasoDeReporte("estado_no_reconocido",
                      "una fila trae un estado que el arnés no emite",
                      FIXTURE_CONFORME,
                      _mutar_estado("fixture-delta", "sospechoso", "12 casos · sospechoso"),
                      AUTORIZADOS_SINTETICOS, None),
        CasoDeReporte("global_incoherente",
                      "se reescribe solo el pie: la tabla dice `fallo` y el global declara paridad",
                      FIXTURE_CONFORME, _mutar_global(CLASE_SANA), AUTORIZADOS_SINTETICOS, None),
        CasoDeReporte("codigo_incoherente",
                      "el código de salida observado no es el que el reporte declara",
                      FIXTURE_CONFORME, None, AUTORIZADOS_SINTETICOS, 0),
        CasoDeReporte("reporte_ilegible",
                      "el reporte llega sin el encabezado de su tabla",
                      FIXTURE_CONFORME, _mutar_sin_encabezado, AUTORIZADOS_SINTETICOS, None),
        CasoDeReporte("interprete_ausente",
                      "la corrida no encontró intérprete y no comprobó un solo par",
                      FIXTURE_SIN_INTERPRETE, None, PARES_CON_FALLO_AUTORIZADO, None),
    ]
    return tuple(casos)


def _correr_caso_de_reporte(caso: CasoDeReporte, precedencia: list[str],
                            codigos: dict[str, int]) -> tuple[list[Problema], dict, str]:
    texto = (DIR_FIXTURES_PARIDAD / caso.fixture).read_text(encoding="utf-8")
    if caso.mutar is not None:
        texto = caso.mutar(texto, precedencia, codigos)
    problemas, resumen = verificar_reporte_de_paridad(
        texto, caso.autorizados, precedencia, codigos, caso.codigo_de_salida)
    return problemas, resumen, texto


def _preludio_de_parear() -> tuple[list[tuple[str, bool, str]], list[str], dict[str, int]]:
    """[0] Lo que tiene que valer antes de correr un caso: que el vocabulario se derive del arnés y
    que los literales que este parser reconoce sigan existiendo allá.

    El segundo no es cosmético. `sin matriz (no comprobado)` y `sin casos` no están en ninguna
    constante del arnés —son literales dentro de sus `print`—, así que acá se congelan y se comprueba
    que el arnés los siga escribiendo. Si alguien los cambia, este parser dejaría de reconocer esas
    filas y las contaría como estado no reconocido sin que nada explicara por qué."""
    precedencia, codigos, error = vocabulario_de_paridad(RUTA_ARNES_PARIDAD)
    if error:
        return [("0.vocabulario", False, error)], [], {}
    resultados = [(
        "0.vocabulario", True,
        f"el vocabulario se deriva de {RUTA_ARNES_PARIDAD.name}: {len(precedencia)} clases en "
        f"precedencia ({' < '.join(precedencia)})",
    )]
    fuente = RUTA_ARNES_PARIDAD.read_text(encoding="utf-8")
    literales = [ESTADO_SIN_MATRIZ, ESTADO_SIN_CASOS, PREFIJO_GLOBAL.strip(),
                 PREFIJO_INTERPRETE, MARCA_INTERPRETE_AUSENTE] + list(ENCABEZADO_TABLA)
    faltantes = [lit for lit in literales if lit not in fuente]
    resultados.append((
        "0.formato", not faltantes,
        f"los {len(literales)} literales que este parser reconoce siguen escritos en "
        f"{RUTA_ARNES_PARIDAD.name}"
        if not faltantes else f"el arnés ya no escribe: {faltantes}",
    ))
    if not DIR_FIXTURES_PARIDAD.is_dir():
        resultados.append(("0.fixtures", False, f"no existe {DIR_FIXTURES_PARIDAD}"))
        return resultados, precedencia, codigos
    esperados = (FIXTURE_CONFORME, FIXTURE_IDENTIDADES, FIXTURE_CINCO_CLASES,
                 FIXTURE_SIN_INTERPRETE)
    ausentes = [f for f in esperados if not (DIR_FIXTURES_PARIDAD / f).is_file()]
    resultados.append((
        "0.fixtures", not ausentes,
        f"los {len(esperados)} fixtures del corpus están en {DIR_FIXTURES_PARIDAD.name}/"
        if not ausentes else f"faltan fixtures: {ausentes}",
    ))
    return resultados, precedencia, codigos


def _bloque_de_cardinalidad(precedencia: list[str], codigos: dict[str, int]
                            ) -> list[tuple[str, bool, str]]:
    """[D] La propiedad es igualdad de identidades, no un tope de cantidad.

    El mutante de sustitución solo prueba eso si de verdad conserva la cantidad de pares con
    `fallo`. Acá se mide sobre el texto mutado: si la sustitución cambiara el conteo, el mutante
    caería por cardinalidad y un parser que contara seguiría pasando este autotest en verde."""
    conforme = (DIR_FIXTURES_PARIDAD / FIXTURE_CONFORME).read_text(encoding="utf-8")
    mutado = _mutar_sustitucion(conforme, precedencia, codigos)
    antes = [f.par for f in parsear_reporte(conforme, precedencia).filas
             if f.estado == CLASE_FALLO]
    despues = [f.par for f in parsear_reporte(mutado, precedencia).filas
               if f.estado == CLASE_FALLO]
    fallas: list[str] = []
    if len(antes) != len(despues):
        fallas.append(f"la sustitución cambia el conteo: {len(antes)} → {len(despues)}")
    if set(antes) == set(despues):
        fallas.append("la sustitución no cambió las identidades: no muta nada")
    return [(
        "D/parear-reporte", not fallas,
        f"el mutante de sustitución conserva la cantidad ({len(antes)} pares con `{CLASE_FALLO}`) y "
        f"cambia las identidades ({sorted(antes)} → {sorted(despues)}): un parser que contara lo "
        "dejaría pasar"
        if not fallas else " | ".join(fallas),
    )]


def _bloque_de_clases(precedencia: list[str]) -> list[tuple[str, bool, str]]:
    """[E] Las cinco clases, atribuidas una por una sobre el fixture que las trae juntas.

    Los mutantes prueban que cada clase prohibida se rechaza; esto prueba que el parser las
    **distingue**, que es lo que un `startswith` mal ordenado o una lectura por columnas rompen sin
    cambiar ningún veredicto."""
    texto = (DIR_FIXTURES_PARIDAD / FIXTURE_CINCO_CLASES).read_text(encoding="utf-8")
    reporte = parsear_reporte(texto, precedencia)
    observadas = {f.estado for f in reporte.filas}
    faltantes = [c for c in precedencia if c not in observadas]
    ajenas = sorted(observadas - set(precedencia))
    fallas: list[str] = []
    if faltantes:
        fallas.append(f"el fixture no ejerce {faltantes}")
    if ajenas:
        fallas.append(f"el parser leyó estados que no son clases: {ajenas}")
    if reporte.errores:
        fallas.append(f"el fixture no parsea: {reporte.errores[0]}")
    return [(
        "E/parear-reporte", not fallas,
        f"las {len(precedencia)} clases del arnés aparecen en el corpus y el parser las atribuye "
        f"a su par, una por una: "
        + ", ".join(f"{f.estado}→{f.par}" for f in reporte.filas)
        if not fallas else " | ".join(fallas),
    )]


def _bloque_de_autorizados() -> list[tuple[str, bool, str]]:
    """[F] El testigo congelado contra la derivación del arnés.

    Los cinco pares autorizados se **derivan** de qué matriz de casos declara un caso
    `clase_esperada: fallo`; la constante de este archivo es el testigo. Compararlos es lo que
    convierte una divergencia silenciosa —el arnés autoriza un sexto par y la norma del repositorio
    sigue diciendo cinco— en un rojo."""
    derivados, error = derivar_pares_con_fallo_declarado(DIR_CASOS_PARIDAD)
    if error:
        return [("F/parear-reporte", False, error)]
    coinciden = set(derivados) == set(PARES_CON_FALLO_AUTORIZADO)
    return [(
        "F/parear-reporte", coinciden,
        f"los {len(derivados)} pares que declaran un caso `{CLASE_FALLO}` en el arnés son los del "
        f"testigo congelado: {', '.join(sorted(derivados))}"
        if coinciden else
        f"derivados {sorted(derivados)} y congelados {sorted(PARES_CON_FALLO_AUTORIZADO)}",
    )]


def modo_autotest_parear_reporte() -> int:
    resultados, precedencia, codigos = _preludio_de_parear()
    if not all(ok for _, ok, _ in resultados):
        return _cierre("el reporte de paridad se lee por su cuerpo", resultados)

    casos = _casos_de_reporte(precedencia)

    # [A] El control positivo, y acá no es un trámite: un reporte sano completo trae `fallo` en sus
    # pares autorizados y **código de salida 4**. Sin este caso, los mutantes los pasa cualquier
    # parser que repruebe todo reporte —incluido el que lea el código de salida y trate el 4 como
    # enfermedad, que es exactamente el malentendido que este modo existe para cerrar—.
    conformes = [c for c in casos if c.codigo is None]
    fallas: list[str] = []
    for caso in conformes:
        problemas, resumen, _ = _correr_caso_de_reporte(caso, precedencia, codigos)
        if problemas:
            fallas.append(f"{caso.descripcion} — {problemas[0]}")
        elif sorted(resumen["con_fallo"]) != sorted(caso.autorizados):
            fallas.append(f"{caso.descripcion} — el parser vio `{CLASE_FALLO}` en "
                          f"{resumen['con_fallo']}, esperados {sorted(caso.autorizados)}")
        elif resumen["codigo_global"] != caso.codigo_de_salida:
            fallas.append(f"{caso.descripcion} — el reporte declara código "
                          f"{resumen['codigo_global']} y la corrida devolvió {caso.codigo_de_salida}")
    resultados.append((
        "A/parear-reporte", not fallas,
        f"control positivo: los {len(conformes)} reportes sanos pasan con código de salida "
        f"{conformes[0].codigo_de_salida}, que NO se lee como fallo"
        if not fallas else "control positivo — " + " | ".join(fallas[:3]),
    ))

    # [B] Los mutantes, cada uno rechazado **por su motivo**.
    mutantes = [c for c in casos if c.codigo is not None]
    sobrevivientes: list[str] = []
    desatribuidos: list[str] = []
    emitidos: set[str] = set()
    for caso in mutantes:
        problemas, _, _ = _correr_caso_de_reporte(caso, precedencia, codigos)
        obtenidos = {p.codigo for p in problemas}
        emitidos |= obtenidos
        if not obtenidos:
            sobrevivientes.append(f"{caso.codigo}: {caso.descripcion}")
        elif caso.codigo not in obtenidos:
            desatribuidos.append(f"{caso.codigo}: {caso.descripcion} — rechazado por "
                                 f"{sorted(obtenidos)} y no por su motivo")
    problemas_b = ([f"SOBREVIVE {s}" for s in sobrevivientes]
                   + [f"SIN ATRIBUIR {d}" for d in desatribuidos])
    resultados.append((
        "B/parear-reporte", not problemas_b,
        f"{len(mutantes)} mutantes de `--parear-reporte` y los {len(mutantes)} rechazados por su "
        "motivo"
        if not problemas_b else f"{len(problemas_b)} problemas: " + " | ".join(problemas_b[:5]),
    ))

    # [C] Un caso por código: un código sin caso es una restricción que nadie comprobó que pueda
    # ponerse roja, y un código emitido y no catalogado es una que nadie declaró.
    catalogo = codigos_de_parear(precedencia)
    ejercidos = {c.codigo for c in mutantes}
    problemas_c = [f"`{c}` está en el catálogo y ningún caso lo ejerce"
                   for c in catalogo if c not in ejercidos]
    problemas_c += [f"`{c}` lo emite el modo y no está en el catálogo"
                    for c in sorted((emitidos | ejercidos) - set(catalogo))]
    resultados.append((
        "C/parear-reporte", not problemas_c,
        f"los {len(catalogo)} códigos del modo tienen su caso, incluido uno por cada clase "
        "prohibida derivada del arnés"
        if not problemas_c else f"{len(problemas_c)} huecos: " + " | ".join(problemas_c[:5]),
    ))

    resultados += _bloque_de_cardinalidad(precedencia, codigos)
    resultados += _bloque_de_clases(precedencia)
    resultados += _bloque_de_autorizados()
    return _cierre("el reporte de paridad se clasifica por su cuerpo —cero clases prohibidas y "
                   f"`{CLASE_FALLO}` exactamente en los pares autorizados— y su código de salida 4 "
                   "no es enfermedad", resultados)


# ---------------------------------------------------------------------------------------------
# Identidad de los puntos contra la atestación histórica.
#
# **Comparar la matriz contra sí misma no prueba nada.** Todos los demás modos validan contra el
# estado *vigente*: `--correspondencia` contra el inventario que el árbol declara hoy, `--anclas`
# contra las sedes que existen hoy. Un renombre a un identificador libre y único los deja a todos en
# verde, porque después del renombre la matriz sigue siendo internamente coherente y ninguna skill
# del árbol nombra identificadores. La única referencia que un renombre no puede acomodar es una
# **anterior e inmutable**: el blob de la matriz en el commit que la atestigua.
#
# Cuatro decisiones gobiernan todo lo de abajo.
#
# 1. **La referencia se congela como constante: no se deriva y no se pasa por bandera.** Derivarla
#    —`git log -1 -- <matriz>`, el tag más reciente, `HEAD~1`— la ata al mismo historial que este
#    modo audita: el commit que renombra el identificador sería justamente el que la derivación
#    elige, y el modo terminaría comparando la mutación consigo misma. Una bandera `--atestacion`
#    tiene el defecto simétrico: deja mover la referencia desde la línea de comandos, con lo cual un
#    verde deja de significar «contra la atestación». El costo asumido es que la constante envejece;
#    renovarla cuando un acto nuevo congele otra matriz es editar esta línea, que es un acto
#    deliberado y revisable, y ese es el punto de una atestación. Los parámetros `ref` y `repo` de
#    las funciones existen para que el autotest corra contra repositorios sintéticos.
#
# 2. **La correspondencia punto histórico ↔ punto actual se apoya en el sitio.** Por el
#    identificador no puede: es justamente lo que se audita, y un renombre parecería una baja más un
#    alta. Por la posición tampoco: reordenar el arreglo es editorial y pondría los trece puntos en
#    rojo. El **sitio** —la skill que lo declara y el ancla de invocación que lo señala— sobrevive a
#    un reordenamiento, es único por punto (lo exige `--completitud` con `ancla_compartida`) y es
#    independiente del identificador, que es la condición para poder cotejar uno contra el otro.
#
# 3. **El corte: identificador, skill y ancla. Nada más.** La etiqueta queda afuera porque AC-5 y
#    AC-6 la declaran editorial. Y **todas las demás hojas también** —señales de detección, rol,
#    permisos, condición de existencia, presupuesto—: su autoridad es el árbol vigente y ya tienen
#    dueño, `--correspondencia` las re-deriva del inventario y `--anclas` las resuelve contra su
#    sede. Congelarlas contra un blob viejo pondría este modo en rojo cada vez que alguien reescribe
#    una frase de una skill, y duplicaría un criterio que ya se verifica en otro lado. Comparar el
#    blob entero es el extremo de ese error: cualquier cambio legítimo de la matriz lo pondría rojo
#    y el modo se volvería ruido que se aprende a ignorar.
#
# 4. **Toda divergencia de identidad es roja, incluida la legítima.** Un alta, una baja o un punto
#    que cambia de sitio son rojos aunque el árbol los respalde. Es deliberado: si las altas y las
#    bajas fueran informativas, renombrar un punto **y** moverlo de sitio en el mismo cambio quedaría
#    verde —una baja informativa más un alta informativa— y esa es la evasión exacta que este modo
#    existe para cerrar. El modo no puede distinguir un alta legítima de un renombre camuflado y
#    fingir que sí abriría el hueco. Limpiar ese rojo es renovar la atestación, que vuelve a ser un
#    acto deliberado.
# ---------------------------------------------------------------------------------------------

# El commit del acto 2: el estado en que la matriz alcanza sus 256 hojas resolviendo. Sha completo y
# no abreviado, porque una abreviatura puede volverse ambigua a medida que el historial crece y
# resolvería a otro objeto sin que nadie lo note.
COMMIT_ATESTACION = "5e20a35a57b7f23223243b541423d49ec5b26e82"

# La ruta dentro del commit se **deriva** de la ruta de la matriz: transcribirla dejaría dos lugares
# diciendo lo mismo, y uno de los dos envejecería.
RUTA_EN_ATESTACION = RUTA_MATRIZ.relative_to(REPO).as_posix()

PATRON_SHA_COMPLETO = re.compile(r"^[0-9a-f]{40}$")

# Cómo se nombra cada lado en el `donde` de un problema. Sin esto, `matriz_no_objeto` en la
# atestación y en la matriz vigente serían indistinguibles en el reporte.
LADO_VIGENTE = "matriz"
LADO_HISTORICO = "atestación"

# Los tres modos de fallar de la precondición. Van juntos porque comparten una consecuencia: cuando
# alguno se dispara **no hay veredicto de identidad**, y el modo se detiene en vez de degradar la
# referencia a la matriz que iba a auditar.
CODIGOS_DE_ATESTACION = (
    "atestacion_ilegible",
    "atestacion_irresoluble",
    "atestacion_no_inmutable",
)

CODIGOS_IDENTIDAD = tuple(sorted(CODIGOS_DE_ESTRUCTURA + CODIGOS_DE_ATESTACION + (
    "id_ausente",
    "id_duplicado",
    "id_renombrado",
    "identidad_intercambiada",
    "punto_movido",
    "punto_nuevo",
    "punto_retirado",
    "sitio_ausente",
    "sitio_duplicado",
)))


class Identidad(NamedTuple):
    """Lo único que este modo compara de un punto. Que sean tres campos y no veinte es el corte
    declarado arriba, no una simplificación del lector."""

    indice: int
    identificador: str
    skill: str
    ancla: str

    @property
    def sitio(self) -> tuple[str, str]:
        return (self.skill, self.ancla)

    @property
    def sitio_legible(self) -> str:
        return f"{self.skill} · {self.ancla}"


def _lee_git(repo: Path, *args: str) -> tuple[str | None, str]:
    """La salida de un git de lectura, o `None` y el motivo. No hay ningún comando de escritura acá:
    el modo audita el historial, no lo toca."""
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                              encoding="utf-8", errors="replace", check=False)
    except OSError as exc:
        return None, f"no se pudo ejecutar git: {exc}"
    if proc.returncode != 0:
        detalle = [l for l in (proc.stderr or proc.stdout).strip().splitlines() if l.strip()]
        return None, detalle[0] if detalle else f"git terminó con código {proc.returncode}"
    return proc.stdout, ""


def leer_atestacion(ref: str, repo: Path) -> tuple[Any, Problema | None]:
    """La matriz tal como la congeló el commit de la atestación. La precondición de T11 se comprueba
    acá y antes de nada: si el blob no resuelve, esto devuelve el problema y **nadie construye un
    sustituto**."""
    donde = f"{LADO_HISTORICO} `{ref}`"
    if not PATRON_SHA_COMPLETO.match(ref or ""):
        return None, Problema(
            "atestacion_no_inmutable", donde,
            "la referencia histórica tiene que ser el sha completo de 40 hexadecimales de un "
            "commit: un nombre simbólico —una rama, `HEAD`, un tag movible— se mueve con el mismo "
            "cambio que este modo audita, así que no atestigua nada")
    texto, error = _lee_git(repo, "show", f"{ref}:{RUTA_EN_ATESTACION}")
    if texto is None:
        return None, Problema(
            "atestacion_irresoluble", donde,
            f"`git show {ref}:{RUTA_EN_ATESTACION}` no resolvió: {error}")
    try:
        return json.loads(texto), None
    except json.JSONDecodeError as exc:
        return None, Problema("atestacion_ilegible", donde,
                              f"el blob resolvió pero no es JSON válido: {exc}")


def _con_lado(problemas: list[Problema], lado: str) -> list[Problema]:
    return [Problema(p.codigo, f"{lado} {p.donde}", p.mensaje) for p in problemas]


def _identidades(puntos: list[PuntoDeMatriz],
                 lado: str) -> tuple[dict[str, Identidad], dict[tuple, Identidad], list[Problema]]:
    """Los dos índices sobre los que se coteja —por identificador y por sitio— y lo que impide
    construirlos. Un identificador repetido o un sitio repetido dejan la correspondencia ambigua, y
    emparejar sobre una correspondencia ambigua da un veredicto arbitrario que se parece a uno."""
    por_id: dict[str, Identidad] = {}
    por_sitio: dict[tuple, Identidad] = {}
    problemas: list[Problema] = []
    for punto in puntos:
        donde = f"{lado} {punto.donde}"
        if not _es_cadena_util(punto.identificador):
            problemas.append(Problema("id_ausente", donde,
                                      "el punto no declara un identificador utilizable"))
            continue
        if not (_es_cadena_util(punto.skill) and _es_cadena_util(punto.ancla)):
            problemas.append(Problema(
                "sitio_ausente", donde,
                f"el punto `{punto.identificador}` no declara su sitio (skill y ancla de "
                "invocación), que es la clave con la que se lo coteja contra la atestación"))
            continue
        identidad = Identidad(punto.indice, punto.identificador.strip(),
                              punto.skill.strip(), punto.ancla.strip())
        if identidad.identificador in por_id:
            problemas.append(Problema(
                "id_duplicado", donde,
                f"`{identidad.identificador}` ya lo declara "
                f"$.puntos[{por_id[identidad.identificador].indice}]"))
        else:
            por_id[identidad.identificador] = identidad
        if identidad.sitio in por_sitio:
            problemas.append(Problema(
                "sitio_duplicado", donde,
                f"el sitio {identidad.sitio_legible} ya lo ocupa "
                f"`{por_sitio[identidad.sitio].identificador}`: dos puntos en el mismo sitio dejan "
                "la correspondencia con la atestación sin decidir"))
        else:
            por_sitio[identidad.sitio] = identidad
    return por_id, por_sitio, problemas


def _comparar_identidad(vigentes_por_id: dict[str, Identidad],
                        vigentes_por_sitio: dict[tuple, Identidad],
                        historicos_por_id: dict[str, Identidad],
                        historicos_por_sitio: dict[tuple, Identidad]) -> list[Problema]:
    """El cotejo **punto a punto**, con el sitio como clave.

    Que sea por punto y no por conjunto es lo que separa a este modo de uno inútil:
    `set(vigentes) == set(historicos)` acepta el cambio de etiqueta y rechaza un identificador
    nuevo —pasa los dos primeros casos de AC-5— y deja **verde el intercambio**, porque
    intercambiar dos identificadores conserva el conjunto.

    La distinción entre renombre e intercambio es local y no necesita analizar la permutación
    entera: si el identificador histórico de este sitio **sigue existiendo** en otro punto, los
    identificadores se barajaron; si desapareció del todo, el punto se renombró a un nombre fresco.
    """
    problemas: list[Problema] = []
    for sitio, historico in historicos_por_sitio.items():
        vigente = vigentes_por_sitio.get(sitio)
        if vigente is None:
            mudado = vigentes_por_id.get(historico.identificador)
            if mudado is not None:
                problemas.append(Problema(
                    "punto_movido", f"{LADO_HISTORICO} `{historico.identificador}`",
                    f"el punto estaba en {historico.sitio_legible} y ahora está en "
                    f"{mudado.sitio_legible}"))
            else:
                problemas.append(Problema(
                    "punto_retirado", f"{LADO_HISTORICO} `{historico.identificador}`",
                    f"la atestación lo declara en {historico.sitio_legible} y la matriz vigente ya "
                    "no lo tiene"))
            continue
        if vigente.identificador == historico.identificador:
            continue
        if historico.identificador in vigentes_por_id:
            ocupante = vigentes_por_id[historico.identificador]
            problemas.append(Problema(
                "identidad_intercambiada", f"{LADO_HISTORICO} `{historico.identificador}`",
                f"el punto de {historico.sitio_legible} pasó a llamarse "
                f"`{vigente.identificador}`, y `{historico.identificador}` sigue existiendo en "
                f"{ocupante.sitio_legible}: el conjunto de identificadores se conserva y la "
                "asignación no"))
        else:
            problemas.append(Problema(
                "id_renombrado", f"{LADO_HISTORICO} `{historico.identificador}`",
                f"el punto de {historico.sitio_legible} se llamaba `{historico.identificador}` y "
                f"ahora se llama `{vigente.identificador}`; el identificador es inmutable y la "
                "etiqueta es el nombre que sí puede cambiar"))
    for sitio, vigente in vigentes_por_sitio.items():
        if sitio in historicos_por_sitio or vigente.identificador in historicos_por_id:
            continue  # el segundo caso ya se reportó como `punto_movido`
        problemas.append(Problema(
            "punto_nuevo", f"{LADO_VIGENTE} `{vigente.identificador}`",
            f"la matriz lo declara en {vigente.sitio_legible} y la atestación no lo tiene"))
    return problemas


def verificar_identidad(datos: Any, ref: str, repo: Path) -> tuple[list[Problema], dict]:
    """La identidad de los puntos vigentes contra la atestación, y el resumen de lo que se comparó.

    `comparados` no es decorativo: es la evidencia de que hubo cotejo. Cuando la precondición falla
    vale 0, y ese cero es lo que distingue detenerse de degradar la referencia a la matriz vigente
    —que daría un verde por construcción—."""
    resumen = {"atestacion": ref, "puntos_vigentes": 0, "puntos_historicos": 0, "comparados": 0}

    historicos_crudos, problema = leer_atestacion(ref, repo)
    if problema is not None:
        return [problema], resumen

    vigentes, estructura_v = leer_puntos(datos)
    historicos, estructura_h = leer_puntos(historicos_crudos)
    resumen["puntos_vigentes"] = len(vigentes)
    resumen["puntos_historicos"] = len(historicos)
    estructurales = _con_lado(estructura_v, LADO_VIGENTE) + _con_lado(estructura_h, LADO_HISTORICO)
    if estructurales:
        # Una atestación que no se puede leer como matriz **no es una atestación vacía**: seguir
        # dejaría trece `punto_nuevo` y un rojo que atribuye mal.
        return estructurales, resumen

    vig_por_id, vig_por_sitio, problemas_v = _identidades(vigentes, LADO_VIGENTE)
    his_por_id, his_por_sitio, problemas_h = _identidades(historicos, LADO_HISTORICO)
    if problemas_v or problemas_h:
        return problemas_v + problemas_h, resumen

    resumen["comparados"] = len(set(his_por_sitio) & set(vig_por_sitio))
    return _comparar_identidad(vig_por_id, vig_por_sitio, his_por_id, his_por_sitio), resumen


def modo_identidad(ruta_matriz: Path) -> int:
    datos, error = _cargar_json(ruta_matriz)
    if error:
        print(f"FALLA  identidad: {error}")
        return 1

    problemas, resumen = verificar_identidad(datos, COMMIT_ATESTACION, REPO)
    if problemas and problemas[0].codigo in CODIGOS_DE_ATESTACION:
        print(f"FALLA  la atestación histórica no se pudo leer: {problemas[0]}")
        print("       el modo se detiene acá y NO cae de vuelta a la matriz vigente: comparar la "
              "matriz contra sí misma la deja verde por construcción, que es exactamente lo que "
              "esta comparación existe para impedir")
        return 1
    if problemas:
        _informar(problemas, f"{ruta_matriz.name} contra la atestación {COMMIT_ATESTACION[:7]}")
        return 1

    print(f"OK     {resumen['comparados']} puntos cotejados uno a uno contra "
          f"{COMMIT_ATESTACION[:7]}:{RUTA_EN_ATESTACION}, con el sitio como clave")
    print("OK     ningún identificador renombrado, intercambiado ni movido de sitio; la etiqueta y "
          "las demás hojas quedan fuera del corte y pueden cambiar")
    print()
    print("RESULTADO: OK")
    return 0


# --- Autotest del modo de identidad -----------------------------------------------------------
#
# El corpus es el fixture sintético del inventario: es la única matriz conforme del repo que trae
# las cinco hojas que este modo lee sobre trece puntos, con anclas únicas y **varios puntos que
# comparten skill** —lo que hace que el caso del intercambio no sea vacuo: intercambiar dos
# identificadores dentro de una misma skill solo se detecta si el ancla entra en la
# correspondencia—. Es sintético a propósito: un fixture copiado de la matriz real haría que el modo
# y el dato acordaran entre sí.
#
# La atestación de cada caso se **commitea en un repositorio git de verdad**, en un directorio
# temporal. El camino que se ejerce es el mismo que corre en producción —`git show <sha>:<ruta>`— y
# no una simulación suya: si ese camino se rompiera, un doble de prueba lo taparía. Nada de esto
# toca el repositorio real ni el árbol de trabajo.

SHA_INEXISTENTE = "d" * 40
RUTA_AJENA_EN_COMMIT = "scripts/matriz-que-no-es.json"

# Config explícita para que el repositorio sintético no herede la del usuario: una firma gpg
# obligatoria o un hook de pre-commit harían fallar el commit y el autotest reportaría un rojo que
# no es del modo.
CONFIG_GIT_SINTETICO = (
    "-c", "user.name=autotest",
    "-c", "user.email=autotest@ejemplo.invalid",
    "-c", "commit.gpgsign=false",
    "-c", "core.autocrlf=false",
)


class CasoDeIdentidad(NamedTuple):
    codigo: str | None       # el problema que el caso tiene que disparar; None = caso conforme
    descripcion: str
    mutar_vigente: Any = None      # (datos) -> datos, sobre la matriz que se audita
    mutar_atestacion: Any = None   # (datos) -> datos, sobre la matriz que se commitea
    texto_atestacion: Any = None   # texto crudo a commitear, en vez del JSON
    ruta_en_commit: Any = None     # dónde se commitea, si no es la ruta real
    ref: Any = None                # la referencia que recibe el modo; None = el sha del commit
    con_repo: bool = True          # False: el directorio no es un repositorio git


def _matriz_de_identidad() -> dict:
    return json.loads((CONFORME_INVENTARIO / "matriz.json").read_text(encoding="utf-8"))


def _dos_del_mismo_skill(datos: dict) -> tuple[int, int]:
    """Los índices de dos puntos que comparten skill, **derivados** del fixture y no transcritos: el
    intercambio tiene que ejercer el caso donde la skill no alcanza para distinguirlos, que es donde
    el ancla es lo único que sostiene la correspondencia."""
    vistos: dict[str, int] = {}
    for i, punto in enumerate(datos["puntos"]):
        skill = punto["skill"]["valor"]
        if skill in vistos:
            return vistos[skill], i
        vistos[skill] = i
    raise ValueError("el fixture no tiene dos puntos de la misma skill")


def _intercambiar_identificadores(datos: dict) -> dict:
    i, j = _dos_del_mismo_skill(datos)
    puntos = datos["puntos"]
    puntos[i]["id"], puntos[j]["id"] = puntos[j]["id"], puntos[i]["id"]
    return datos


def _claves_reordenadas(datos: dict) -> dict:
    """Un no-op de verdad: las mismas hojas con las claves de cada punto en otro orden. Un modo que
    compare el texto del blob —o su serialización— se pone rojo acá; uno que compare la propiedad,
    no. Sin este caso, un rojo del intercambio podría venir de estar comparando cadenas."""
    datos["puntos"] = [dict(sorted(p.items(), reverse=True)) for p in datos["puntos"]]
    return datos


def _otra_skill(datos: dict) -> str:
    """Una skill del fixture distinta de la del primer punto: mover el punto a una skill inventada
    lo dejaría además fuera del inventario, y el caso mediría dos cosas a la vez."""
    propia = datos["puntos"][0]["skill"]["valor"]
    return next(p["skill"]["valor"] for p in datos["puntos"] if p["skill"]["valor"] != propia)


PUNTO_POSTERIOR_A_LA_ATESTACION = {
    "id": "skill-omega-recolector-tardio",
    "etiqueta": "Recolector tardío, agregado después de la atestación",
    "skill": {"valor": "skill-omega"},
    "senales_de_deteccion": {"valor": ["recolector tardío"]},
    "ancla_de_invocacion": {"valor": "skills/skill-omega/SKILL.md#recolector-tardio"},
}


def _casos_de_identidad() -> tuple[CasoDeIdentidad, ...]:
    """Los casos se construyen tarde —y no como constante de módulo— porque sus mutaciones derivan
    índices del fixture, y el preludio es el que comprueba que el fixture los tenga."""
    return (
        # Los conformes. Los tres últimos son la parte que se paga cara al perderla: ejercen las
        # variantes legítimas que **más se parecen a un defecto**, que es donde un rechazo
        # indiscriminado se disfraza mejor de rigor.
        CasoDeIdentidad(None, "el fixture conforme contra su propia atestación"),
        CasoDeIdentidad(
            None, "cambiar únicamente la etiqueta legible: el nombre legible puede cambiar",
            mutar_vigente=_mutando(
                lambda d: d["puntos"][0].update({"etiqueta": "Otro rótulo, de otra mano"}))),
        CasoDeIdentidad(
            None, "reordenar el arreglo: la correspondencia no se apoya en la posición",
            mutar_vigente=_mutando(lambda d: d["puntos"].reverse())),
        CasoDeIdentidad(
            None, "cambiar las señales de detección: quedan fuera del corte y las verifica "
                  "--correspondencia contra el árbol vigente",
            mutar_vigente=_mutando(lambda d: d["puntos"][0]["senales_de_deteccion"].update(
                {"valor": ["otra frase que la skill dirá mañana"]}))),
        CasoDeIdentidad(
            None, "no-op: las mismas hojas con las claves en otro orden", _claves_reordenadas),

        # Los tres casos que AC-5 y V12 nombran. El tercero es el que obliga a comparar por punto.
        CasoDeIdentidad(
            "id_renombrado", "cambiar el identificador de un punto por uno libre y único",
            _mutando(lambda d: d["puntos"][0].update({"id": "skill-alfa-explorador-rebautizado"}))),
        CasoDeIdentidad(
            "identidad_intercambiada",
            "intercambiar los identificadores de dos puntos de la misma skill, conservando el "
            "conjunto", _intercambiar_identificadores),

        CasoDeIdentidad(
            "punto_movido", "un punto conserva su identificador y cambia de skill",
            _mutando(lambda d: d["puntos"][0]["skill"].update({"valor": _otra_skill(d)}))),
        CasoDeIdentidad(
            "punto_movido", "un punto conserva su identificador y su skill, y cambia de ancla",
            _mutando(lambda d: d["puntos"][0]["ancla_de_invocacion"].update(
                {"valor": "skills/skill-alfa/SKILL.md#otra-seccion"}))),
        CasoDeIdentidad("punto_retirado", "la matriz vigente pierde un punto",
                        _mutando(lambda d: d["puntos"].pop(0))),
        CasoDeIdentidad(
            "punto_nuevo", "la matriz vigente estrena un punto que la atestación no tiene",
            _mutando(lambda d: d["puntos"].append(copy.deepcopy(PUNTO_POSTERIOR_A_LA_ATESTACION)))),

        # Lo que impide construir la correspondencia. Se ejercen los dos lados: un defecto en la
        # atestación no puede leerse como «la atestación no decía nada».
        CasoDeIdentidad("id_ausente", "un punto vigente se queda sin identificador",
                        _mutando(lambda d: d["puntos"][0].pop("id"))),
        CasoDeIdentidad(
            "id_duplicado", "la atestación trae dos puntos con el mismo identificador",
            mutar_atestacion=_mutando(
                lambda d: d["puntos"][1].update({"id": d["puntos"][0]["id"]}))),
        CasoDeIdentidad("sitio_ausente", "un punto vigente se queda sin skill",
                        _mutando(lambda d: d["puntos"][0].pop("skill"))),
        CasoDeIdentidad(
            "sitio_duplicado", "dos puntos vigentes ocupan el mismo sitio",
            _mutando(lambda d: d["puntos"][1].update({
                "skill": copy.deepcopy(d["puntos"][0]["skill"]),
                "ancla_de_invocacion": copy.deepcopy(d["puntos"][0]["ancla_de_invocacion"])}))),
        CasoDeIdentidad("matriz_no_objeto", "la matriz vigente deja de ser un objeto",
                        lambda d: [p["id"] for p in d["puntos"]]),
        CasoDeIdentidad(
            "puntos_no_es_arreglo",
            "la atestación resuelve pero sus `puntos` no son un arreglo: una atestación rota no es "
            "una atestación vacía", mutar_atestacion=_mutando(lambda d: d.update({"puntos": {}}))),
        CasoDeIdentidad("punto_no_objeto", "un punto vigente deja de ser un objeto",
                        _mutando(lambda d: d["puntos"].__setitem__(0, "un punto suelto"))),

        # La precondición. Los cuatro corren con la matriz vigente **sin mutar**, que es lo que los
        # vuelve el control de la degradación: una implementación que ante una atestación ilegible
        # cayera de vuelta a la matriz vigente la compararía consigo misma y daría verde.
        CasoDeIdentidad("atestacion_no_inmutable",
                        "la referencia es un nombre simbólico y no un sha", ref="HEAD"),
        CasoDeIdentidad("atestacion_irresoluble",
                        "el sha tiene la forma correcta y no existe en el repositorio",
                        ref=SHA_INEXISTENTE),
        CasoDeIdentidad("atestacion_irresoluble",
                        "el commit existe y no lleva la matriz en esa ruta",
                        ruta_en_commit=RUTA_AJENA_EN_COMMIT, ref=SHA_INEXISTENTE),
        CasoDeIdentidad("atestacion_irresoluble", "el directorio no es un repositorio git",
                        con_repo=False),
        CasoDeIdentidad("atestacion_ilegible", "el blob resuelve y no es JSON",
                        texto_atestacion="{ esto no es una matriz, es una nota\n"),
    )


def _atestacion_sintetica(taller: dict, texto: str, ruta: str,
                          con_repo: bool) -> tuple[str, Path, str]:
    """El repositorio con la atestación commiteada, memoizado por contenido: los casos comparten
    atestación casi siempre y crear un repo por caso multiplicaría el costo sin agregar cobertura."""
    clave = (texto, ruta, con_repo)
    if clave in taller["repos"]:
        return taller["repos"][clave]

    destino = taller["base"] / f"repo-{len(taller['repos'])}"
    archivo = destino / ruta
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(texto, encoding="utf-8")
    if not con_repo:
        # Sin `git init`. La referencia es un sha inexistente además, para que el caso siga siendo
        # rojo aunque el temporal cayera dentro de un repositorio ajeno.
        taller["repos"][clave] = (SHA_INEXISTENTE, destino, "")
        return taller["repos"][clave]

    for orden in (("init", "-q"), ("add", "-f", "--", ruta),
                  ("commit", "-q", "--no-verify", "-m", "atestación sintética")):
        _, error = _lee_git(destino, *CONFIG_GIT_SINTETICO, *orden)
        if error:
            taller["repos"][clave] = ("", destino, f"`git {orden[0]}` falló: {error}")
            return taller["repos"][clave]
    sha, error = _lee_git(destino, "rev-parse", "HEAD")
    if sha is None:
        taller["repos"][clave] = ("", destino, f"`git rev-parse` falló: {error}")
    else:
        taller["repos"][clave] = (sha.strip(), destino, "")
    return taller["repos"][clave]


def _correr_caso_de_identidad(caso: CasoDeIdentidad,
                              taller: dict) -> tuple[list[Problema], dict, str]:
    base = _matriz_de_identidad()
    historica = caso.mutar_atestacion(copy.deepcopy(base)) if caso.mutar_atestacion else base
    texto = (caso.texto_atestacion if caso.texto_atestacion is not None
             else json.dumps(historica, ensure_ascii=False, indent=2) + "\n")
    sha, repo, error = _atestacion_sintetica(
        taller, texto, caso.ruta_en_commit or RUTA_EN_ATESTACION, caso.con_repo)
    if error:
        return [], {}, error

    vigente = caso.mutar_vigente(copy.deepcopy(base)) if caso.mutar_vigente else base
    problemas, resumen = verificar_identidad(vigente, caso.ref if caso.ref is not None else sha,
                                             repo)
    return problemas, resumen, ""


def _preludio_de_identidad() -> list[tuple[str, bool, str]]:
    """Lo que tiene que valer antes de correr un solo caso: que haya git, que la constante congelada
    sea inmutable de verdad, y que el fixture tenga las propiedades que los casos suponen. Un
    fixture con anclas repetidas o sin dos puntos de la misma skill dejaría al caso del intercambio
    probando menos de lo que dice."""
    version, error = _lee_git(REPO, "--version")
    resultados = [("0.git", version is not None,
                   f"git disponible ({(version or '').strip()})" if version is not None
                   else f"sin git, y este modo lee el historial con él: {error}")]

    inmutable = bool(PATRON_SHA_COMPLETO.match(COMMIT_ATESTACION))
    resultados.append((
        "0.constante", inmutable,
        f"`COMMIT_ATESTACION` es un sha completo ({COMMIT_ATESTACION[:7]}…) y no un nombre que se "
        "mueva" if inmutable else
        f"`COMMIT_ATESTACION` = {COMMIT_ATESTACION!r} no es un sha completo de 40 hexadecimales"))

    if not (CONFORME_INVENTARIO / "matriz.json").is_file():
        return resultados + [("0.fixture", False,
                              f"no existe el fixture conforme ({CONFORME_INVENTARIO})")]
    datos = _matriz_de_identidad()
    puntos, estructura = leer_puntos(datos)
    ids = [p.identificador for p in puntos]
    sitios = [(p.skill, p.ancla) for p in puntos]
    skills = [p.skill for p in puntos]
    faltas = []
    if estructura:
        faltas.append(str(estructura[0]))
    if len(puntos) < 2:
        faltas.append(f"tiene {len(puntos)} puntos y hacen falta al menos dos")
    if len(set(ids)) != len(ids):
        faltas.append("tiene identificadores repetidos")
    if len(set(sitios)) != len(sitios):
        faltas.append("tiene sitios repetidos y la correspondencia sería ambigua")
    acompanados = sum(1 for s in skills if skills.count(s) > 1)
    if not acompanados:
        faltas.append("no tiene dos puntos de la misma skill, así que el intercambio no ejercería "
                      "el papel del ancla en la correspondencia")
    resultados.append((
        "0.fixture", not faltas,
        f"el fixture conforme sirve: {len(puntos)} puntos, identificadores y sitios únicos, y "
        f"{acompanados} de ellos comparten skill con otro"
        if not faltas else "el fixture no sirve — " + " | ".join(faltas)))
    return resultados


def _bloque_de_identidad(casos: tuple[CasoDeIdentidad, ...],
                         taller: dict) -> list[tuple[str, bool, str]]:
    resultados: list[tuple[str, bool, str]] = []

    # [A] El control positivo. Sin él, un modo que rechace toda matriz satisface los veinte mutantes
    # y cierra en verde sin haber aceptado jamás una identidad intacta.
    conformes = [c for c in casos if c.codigo is None]
    fallas: list[str] = []
    for caso in conformes:
        problemas, resumen, error = _correr_caso_de_identidad(caso, taller)
        if error:
            fallas.append(f"{caso.descripcion} — {error}")
        elif problemas:
            fallas.append(f"{caso.descripcion} — {problemas[0]}")
        elif resumen["comparados"] != resumen["puntos_historicos"]:
            fallas.append(f"{caso.descripcion} — se cotejaron {resumen['comparados']} de "
                          f"{resumen['puntos_historicos']} puntos históricos")
    resultados.append((
        "A/identidad", not fallas,
        f"control positivo: los {len(conformes)} casos conformes pasan y cotejan los puntos, no "
        "los saltean"
        if not fallas else "control positivo — " + " | ".join(fallas[:3])))

    # [B] Los mutantes, cada uno rechazado **por su motivo**: un rechazo ajeno que se le parece
    # reportaría una cobertura que no existe.
    mutantes = [c for c in casos if c.codigo is not None]
    sobrevivientes: list[str] = []
    desatribuidos: list[str] = []
    rotos: list[str] = []
    emitidos: set[str] = set()
    for caso in mutantes:
        problemas, _, error = _correr_caso_de_identidad(caso, taller)
        if error:
            rotos.append(f"{caso.codigo}: {caso.descripcion} — {error}")
            continue
        codigos = {p.codigo for p in problemas}
        emitidos |= codigos
        if not codigos:
            sobrevivientes.append(f"{caso.codigo}: {caso.descripcion}")
        elif caso.codigo not in codigos:
            desatribuidos.append(f"{caso.codigo}: {caso.descripcion} — rechazado por "
                                 f"{sorted(codigos)} y no por su motivo")
    problemas_b = ([f"SOBREVIVE {s}" for s in sobrevivientes]
                   + [f"SIN ATRIBUIR {d}" for d in desatribuidos]
                   + [f"NO CORRIÓ {r}" for r in rotos])
    resultados.append((
        "B/identidad", not problemas_b,
        f"{len(mutantes)} mutantes y los {len(mutantes)} rechazados por su propio motivo"
        if not problemas_b else f"{len(problemas_b)} problemas: " + " | ".join(problemas_b[:5])))

    # [C] Un caso por código: un código sin caso es una restricción que nadie comprobó que pueda
    # ponerse roja, y un código emitido y no catalogado es una que nadie declaró.
    ejercidos = {c.codigo for c in mutantes}
    problemas_c = [f"`{c}` está en el catálogo y ningún caso lo ejerce"
                   for c in CODIGOS_IDENTIDAD if c not in ejercidos]
    problemas_c += [f"`{c}` lo emite el modo y no está en el catálogo"
                    for c in sorted((emitidos | ejercidos) - set(CODIGOS_IDENTIDAD))]
    resultados.append((
        "C/identidad", not problemas_c,
        f"los {len(CODIGOS_IDENTIDAD)} códigos del modo tienen su caso"
        if not problemas_c else f"{len(problemas_c)} huecos: " + " | ".join(problemas_c[:5])))
    return resultados


def _bloque_de_precondicion(casos: tuple[CasoDeIdentidad, ...],
                            taller: dict) -> list[tuple[str, bool, str]]:
    """[D] La precondición se detiene y **no degrada**. Que el caso dé rojo no alcanza: hay que
    mostrar que no hubo cotejo. Una implementación que ante una atestación ilegible cayera de vuelta
    a la matriz vigente daría rojo igual si además reportara el problema, y estaría comparando la
    matriz consigo misma."""
    de_precondicion = [c for c in casos if c.codigo in CODIGOS_DE_ATESTACION]
    fallas: list[str] = []
    for caso in de_precondicion:
        problemas, resumen, error = _correr_caso_de_identidad(caso, taller)
        codigos = {p.codigo for p in problemas}
        if error:
            fallas.append(f"{caso.descripcion} — {error}")
        elif codigos != {caso.codigo}:
            fallas.append(f"{caso.descripcion} — emitió {sorted(codigos)} y no solo "
                          f"`{caso.codigo}`")
        elif resumen["comparados"] != 0:
            fallas.append(f"{caso.descripcion} — cotejó {resumen['comparados']} puntos con la "
                          "precondición fallada: cayó de vuelta a alguna referencia")
    resultados = [(
        "D/identidad", not fallas,
        f"los {len(de_precondicion)} casos de precondición se detienen sin cotejar nada: la "
        "referencia no se degrada a la matriz vigente"
        if not fallas else f"{len(fallas)} problemas: " + " | ".join(fallas[:3]))]

    # Y la otra dirección: la precondición sana **sí** cotejó. Sin esto, un modo que devolviera
    # siempre `comparados: 0` satisfaría el bloque entero.
    problemas, resumen, error = _correr_caso_de_identidad(
        CasoDeIdentidad(None, "atestación sana"), taller)
    sano = not error and not problemas and resumen["comparados"] > 0
    resultados.append((
        "D2/identidad", sano,
        f"y con la atestación sana el cotejo ocurre: {resumen.get('comparados', 0)} puntos"
        if sano else f"la atestación sana no cotejó: {error or (problemas[0] if problemas else '')}"))
    return resultados


def _bloque_por_punto(taller: dict) -> list[tuple[str, bool, str]]:
    """[E] Lo que separa una comparación por punto de una por conjunto. No alcanza con que el
    intercambio dé rojo: hay que **mostrar** que el conjunto de identificadores no cambió, o el caso
    no distingue las dos implementaciones y su rojo podría venir de cualquier otra cosa."""
    base = _matriz_de_identidad()
    intercambiada = _intercambiar_identificadores(copy.deepcopy(base))
    ids_antes = sorted(p["id"] for p in base["puntos"])
    ids_despues = sorted(p["id"] for p in intercambiada["puntos"])
    i, j = _dos_del_mismo_skill(base)
    misma_skill = base["puntos"][i]["skill"]["valor"] == base["puntos"][j]["skill"]["valor"]

    problemas, _, error = _correr_caso_de_identidad(
        CasoDeIdentidad("identidad_intercambiada", "intercambio", _intercambiar_identificadores),
        taller)
    codigos = {p.codigo for p in problemas}

    return [
        ("E1/identidad", ids_antes == ids_despues,
         "el intercambio conserva el conjunto de identificadores: `set(vigentes) == "
         "set(historicos)` quedaría verde acá"
         if ids_antes == ids_despues else "el intercambio alteró el conjunto y el caso no "
                                          "distingue una comparación por punto de una por conjunto"),
        ("E2/identidad", misma_skill,
         f"y los dos puntos intercambiados comparten skill (`{base['puntos'][i]['skill']['valor']}`): "
         "la skill no los distingue y la correspondencia se apoya en el ancla"
         if misma_skill else "los dos puntos intercambiados no comparten skill"),
        ("E3/identidad", not error and codigos == {"identidad_intercambiada"},
         "y aun así el modo se pone rojo y lo atribuye al intercambio"
         if not error and codigos == {"identidad_intercambiada"} else
         f"el modo no atribuyó el intercambio: {error or sorted(codigos)}"),
    ]


def modo_autotest_identidad() -> int:
    resultados = _preludio_de_identidad()
    if all(ok for _, ok, _ in resultados):
        with tempfile.TemporaryDirectory() as tmp:
            taller = {"base": Path(tmp), "repos": {}}
            casos = _casos_de_identidad()
            resultados += _bloque_de_identidad(casos, taller)
            resultados += _bloque_de_precondicion(casos, taller)
            resultados += _bloque_por_punto(taller)
    return _cierre("la identidad de los puntos se coteja punto a punto contra un blob anterior e "
                   "inmutable, y el intercambio de dos identificadores es rojo", resultados)


# ---------------------------------------------------------------------------------------------
# El documento de contrato: correcciones, los tres ejes y las capacidades de plataforma.
#
# **El documento todavía no existe.** Estos tres modos se construyen contra un corpus sintético
# congelado —`scripts/fixtures-contrato/`— y se aplican sobre el documento real en otra task. El
# orden no es una comodidad: al revés, el parser heredaría la interpretación de quien escribió el
# texto y los dos pasarían de acuerdo entre sí aunque ambos estuvieran mal.
#
# Tres decisiones gobiernan todo lo de abajo:
#
# 1. **La forma es tabular, no prosa.** Cada sección del contrato declara una tabla Markdown con
#    columnas fijas. Un predicado que rasque prosa se endurece hasta que acepta lo que el autor
#    escribió; una tabla se lee igual la escriba quien la escriba, y este repo ya tiene su parser
#    (`_celdas`, `_es_separadora`, `_rangos_de_secciones`).
# 2. **El inventario de literales de los tres ejes se congela acá, con puntero por literal, y cada
#    puntero apunta a una sede real de `skills/` que ya existe.** Los mutantes impiden que el
#    verificador sea laxo; **no** impiden que el inventario sea inventado. Contra eso hay una sola
#    defensa y es el puntero: el preludio resuelve los dieciséis contra el árbol real y comprueba
#    que el literal esté ahí. Un literal que se citara a sí mismo, al documento de contrato o a
#    estos fixtures coincidiría siempre consigo mismo, y el modo, el inventario y la fila quedarían
#    los tres verdes sin ninguna evidencia independiente.
# 3. **Un documento ausente no es un documento conforme.** Los tres modos terminan con
#    `CODIGO_DOCUMENTO_AUSENTE` cuando no encuentran el archivo, que no es 0 y no es 1: no hay
#    veredicto porque no hay nada que verificar.
#
# El corte del inventario, declarado para que se pueda discutir: entra un literal si (a) es valor de
# un vocabulario **cerrado y declarado** en una sede de `skills/` —una tabla de estados, un enum del
# contrato de salida— y (b) clasifica **la corrida delegada o su entrega**, no un objeto interno de
# una skill. Por (b) quedan afuera el ciclo de vida del *finding* de `cross-review`, los estados de
# baseline de `cross-implement/contrato-verificacion.md` y los `status` por repo del `manifest.yml`
# de `sdd-orchestrator`, que clasifican otras cosas. Y las cuatro causas de `UNAVAILABLE` quedan
# afuera por ser un sub-enum **acoplado a un solo literal**, no hermanas de los demás.
# ---------------------------------------------------------------------------------------------

# Provisional y de una sola línea: la ruta del documento la fija la task que lo escribe. Se declara
# acá para que los tres modos tengan un default y para que renombrarlo sea un cambio y no una
# búsqueda. Mientras no exista, los tres modos terminan con `CODIGO_DOCUMENTO_AUSENTE`.
RUTA_CONTRATO = REPO / "docs" / "superpowers" / "specs" / "contrato-de-ejecucion.md"

DIR_FIXTURES_CONTRATO = REPO / "scripts" / "fixtures-contrato"
CONFORME_CONTRATO = DIR_FIXTURES_CONTRATO / "conforme"
DOCUMENTO_CONFORME = CONFORME_CONTRATO / "contrato.md"

# Ni 0 (pasa) ni 1 (falla): no hay veredicto. Un documento ausente que terminara en 0 sería la forma
# más barata de cerrar las tres filas sin haber escrito el contrato.
CODIGO_DOCUMENTO_AUSENTE = 3

SLUG_ALCANCE = "alcance-comprometido"
SLUG_CORRECCIONES = "correcciones"
SLUG_DECISIONES = "decisiones-diferidas"
SLUG_CAPACIDADES = "capacidades-de-plataforma"

# Los encabezados se comparan **normalizados** (sin diacríticos ni backticks): «afirmación anterior»
# y «afirmacion anterior» son la misma columna, y exigir la ortografía exacta convertiría un acento
# en un rojo.
COLUMNAS_ALCANCE = ("tramo", "estado")
COLUMNAS_CORRECCIONES = ("id", "afirmacion anterior", "afirmacion corregida", "evidencia",
                         "supersesion", "documento fuente")
COLUMNAS_DECISIONES = ("id", "decision", "estado", "fase de destino")
COLUMNAS_EJE = ("literal", "tipo", "sede", "significado")
COLUMNAS_CAPACIDADES = ("afirmacion", "marca", "version", "motivo")

# El texto con el que una celda dice «acá no va nada». Sin una marca declarada, una celda vacía y
# una celda con un guion serían dos formas de lo mismo y cada consumidor elegiría una.
MARCAS_DE_VACIO = ("", "—", "–")

ESTADO_DIFERIDA = "diferida"

MARCAS_DE_CAPACIDAD = ("portable", "dependiente", "no_verificable")

# Una versión comprobada nombra **qué** se comprobó y **con qué número**: `3.12.0` a secas no dice
# de qué, y `comprobado` no dice con qué. AC-3 pide «la versión con la que se comprobaron», que son
# las dos cosas.
PATRON_VERSION_COMPROBADA = re.compile(r"^\S.*\s+v?\d+(?:\.\d+)+$")

PREFIJO_DE_SEDE_NORMATIVA = "skills/"

EJES = ("ciclo_de_vida_operativo", "validez_del_reporte_entregado", "resultado_semantico")


def _slug_de_eje(eje: str) -> str:
    """El slug de la sección de un eje se **deriva** de su namespace. Transcribir los tres dejaría
    dos lugares diciendo lo mismo y uno de los dos envejecería."""
    return "eje-" + eje.replace("_", "-")


SLUGS_DE_EJE = {eje: _slug_de_eje(eje) for eje in EJES}


class LiteralDeEje(NamedTuple):
    """Un literal del inventario normativo, con lo que lo hace comprobable.

    `sede` es un ancla `<ruta>#<slug>` —la misma gramática que usa `ancla_de_invocacion` en la
    matriz— y es lo único que impide que este inventario sea una lista inventada: el preludio la
    resuelve contra el árbol real y exige que el literal aparezca ahí."""

    literal: str
    tipo: str
    sede: str


# ---------------------------------------------------------------------------------------------
# INVENTARIO NORMATIVO DE LOS TRES EJES
#
# **Los nombres de los tres ejes no aparecen en `skills/`; sus vocabularios sí.** Nombrarlos y
# separarlos es el aporte del contrato; los literales salen de sedes que ya existen. Cada fila lleva
# su puntero, y `_preludio_de_ejes` los resuelve todos antes de correr un solo caso.
#
# `done` aparece en dos ejes **a propósito y sin ser una fusión**: en el operativo es el marcador de
# cierre del crudo —«pertenece al transporte, no al contenido», dice su sede— y en el semántico es
# el veredicto de una task delegada. Distinto tipo, distinta sede, distinto significado. Es el caso
# que más se parece a un defecto sin serlo, y por eso es el control positivo del modo.
# ---------------------------------------------------------------------------------------------

INVENTARIO_DE_EJES: dict[str, tuple[LiteralDeEje, ...]] = {
    "ciclo_de_vida_operativo": (
        LiteralDeEje("resultado_entregado", "outcome_de_espera",
                     "skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera"),
        LiteralDeEje("corte_presupuesto", "outcome_de_espera",
                     "skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera"),
        LiteralDeEje("error", "outcome_de_espera",
                     "skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera"),
        LiteralDeEje("cancelacion", "outcome_de_espera",
                     "skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera"),
        LiteralDeEje("UNAVAILABLE", "terminal_sin_entrega",
                     "skills/co-explore/reference.md#estados-del-worker"),
        LiteralDeEje("done", "marcador_de_cierre",
                     "skills/co-explore/reference.md#senal-de-finalizacion"),
    ),
    "validez_del_reporte_entregado": (
        LiteralDeEje("READY", "clase_de_validez",
                     "skills/co-explore/reference.md#estados-del-worker"),
        LiteralDeEje("INVALID", "clase_de_validez",
                     "skills/co-explore/reference.md#estados-del-worker"),
        LiteralDeEje("clarification-needed", "clase_de_validez",
                     "skills/co-explore/reference.md#clarification-needed-el-cuarto-estado"),
    ),
    "resultado_semantico": (
        LiteralDeEje("APPROVED", "veredicto_de_revision",
                     "skills/cross-review/reference.md#veredicto-derivado"),
        LiteralDeEje("REVISE", "veredicto_de_revision",
                     "skills/cross-review/reference.md#veredicto-derivado"),
        LiteralDeEje("done", "estado_de_task",
                     "skills/sdd-flow/reference.md#prompt-del-subagente-por-task"),
        LiteralDeEje("failed", "estado_de_task",
                     "skills/sdd-flow/reference.md#prompt-del-subagente-por-task"),
        LiteralDeEje("verified", "estado_de_repo_delegado",
                     "skills/sdd-orchestrator/reference.md#prompt-del-agente-delegado"),
        LiteralDeEje("PARTIAL", "cierre_de_unidad",
                     "skills/cross-implement/ownership.md#la-matriz-de-control-de-flujo"),
        LiteralDeEje("BLOCKED", "cierre_de_unidad",
                     "skills/cross-implement/ownership.md#la-matriz-de-control-de-flujo"),
    ),
}

CODIGOS_CONTRATO = (
    "afirmacion_inexistente_en_la_fuente",
    "alcance_ausente",
    "columna_ausente",
    "correcciones_ausentes",
    "correccion_sin_evidencia",
    "correccion_sin_fuente",
    "correccion_sin_supersesion",
    "correccion_sin_texto_anterior",
    "correccion_sin_texto_corregido",
    "decisiones_ausentes",
    "decision_no_diferida",
    "decision_sin_fase",
    "fuente_equivocada",
    "fuente_irresoluble",
    "fuente_no_admisible",
    "id_duplicado",
    "supersesion_no_nombra_la_fuente",
)

CODIGOS_EJES = (
    "columna_ausente",
    "compartido_sin_distincion",
    "eje_ausente",
    "eje_desconocido",
    "eje_sin_literales",
    "enum_ajeno",
    "enum_union",
    "literal_ausente_en_la_sede",
    "literal_de_mas",
    "literal_de_menos",
    "literal_duplicado",
    "literal_sustituido",
    "namespace_no_coincide",
    "perdida_de_namespace",
    "sede_ausente",
    "sede_fuera_de_skills",
    "sede_irresoluble",
    "sede_no_coincide",
    "significado_ausente",
    "tipo_ausente",
    "tipo_no_coincide",
)

CODIGOS_CAPACIDADES = (
    "afirmacion_sin_marca",
    "afirmacion_vacia",
    "capacidades_ausentes",
    "columna_ausente",
    "dependiente_sin_version",
    "marca_desconocida",
    "no_verificable_con_version",
    "no_verificable_sin_motivo",
    "version_sin_forma",
)

# Los defectos que ocurren **en una fila**, y no en la tabla entera. El cuantificador de su criterio
# es «toda afirmación», así que sus mutantes tienen que ser unitarios: con un fixture donde el
# defecto sea global —todas sin marca, todas sin versión— un verificador que comprobara que existe
# *alguna* marca y *alguna* versión lo satisface. Que sean unitarios de verdad lo comprueba el
# bloque E y no la prosa: los dos estructurales (`capacidades_ausentes` y `columna_ausente`) quedan
# afuera porque no son de una fila.
CODIGOS_UNITARIOS_DE_CAPACIDAD = tuple(
    c for c in CODIGOS_CAPACIDADES if c not in ("capacidades_ausentes", "columna_ausente"))


# --- Lectura del documento --------------------------------------------------------------------

class Tabla(NamedTuple):
    """Una tabla Markdown ubicada dentro de una sección, con las líneas que ocupa.

    Las líneas no son decorativas: son lo que permite **mutar** el documento por celda en el
    autotest en vez de por búsqueda y reemplazo de texto, que confundiría dos celdas con el mismo
    contenido."""

    encabezados: tuple[str, ...]
    filas: tuple[tuple[str, ...], ...]
    linea_encabezado: int
    lineas_de_fila: tuple[int, ...]


def _texto_de_celda(celda: str) -> str:
    """El valor de una celda: sin backticks ni énfasis, y con la marca de vacío colapsada a `""`."""
    limpio = celda.replace("`", "").replace("**", "").strip()
    return "" if limpio in MARCAS_DE_VACIO else limpio


def _norm_contrato(texto: str) -> str:
    """La normalización del repo —minúsculas, sin diacríticos, sin backticks, espacios colapsados—,
    reusada y no reescrita: dos normalizaciones distintas harían que un encabezado casara acá y no
    en el resolutor de anclas."""
    return primitiva_de_biyeccion().norm(texto)


def _tabla_de_seccion(texto: str, slug: str) -> Tabla | None:
    """La **primera** tabla de la sección, o `None` si la sección no existe o no tiene ninguna."""
    rangos = _rangos_de_secciones(texto)
    if slug not in rangos:
        return None
    inicio, fin = rangos[slug]
    lineas = texto.split("\n")
    fuera = _lineas_fuera_de_fence(texto)
    i = inicio
    while i < min(fin, len(fuera) - 1):
        if not (fuera[i] and lineas[i].strip().startswith("|") and _es_separadora(lineas[i + 1])):
            i += 1
            continue
        encabezados = tuple(_norm_contrato(c) for c in _celdas(lineas[i]))
        filas: list[tuple[str, ...]] = []
        numeros: list[int] = []
        j = i + 2
        while j <= fin and j < len(fuera) and fuera[j] and lineas[j].strip().startswith("|"):
            filas.append(tuple(_celdas(lineas[j])))
            numeros.append(j)
            j += 1
        return Tabla(encabezados, tuple(filas), i, tuple(numeros))
    return None


def _columnas_faltantes(tabla: Tabla, columnas: tuple[str, ...]) -> list[str]:
    return [c for c in columnas if c not in tabla.encabezados]


def _celda_de(tabla: Tabla, fila: tuple[str, ...], columna: str) -> str | None:
    """El valor de la celda, o `None` si la tabla **no tiene** esa columna. Distinguir «la columna no
    está» de «la celda está vacía» es lo que evita que una columna borrada emita un problema por
    fila en vez de uno solo."""
    if columna not in tabla.encabezados:
        return None
    indice = tabla.encabezados.index(columna)
    return _texto_de_celda(fila[indice]) if indice < len(fila) else ""


def _clave_de_fila(fila: tuple[str, ...]) -> str:
    return _texto_de_celda(fila[0]) if fila else ""


# --- Modo de correcciones, alcance y decisiones diferidas -------------------------------------

def _fuente_no_admisible(ruta_rel: str, ruta_documento: Path, raiz: Path) -> str:
    """Por qué esa fuente no puede respaldar una corrección, o `""` si puede.

    El documento no puede ser su propia fuente ni citar un artefacto de este flujo: una afirmación
    que se cita a sí misma coincide siempre consigo misma, y la corrección, su atribución y su fila
    quedan las tres verdes sin ninguna evidencia independiente. Es la misma regla que gobierna las
    procedencias de la matriz."""
    if ruta_rel.startswith("/") or ".." in Path(ruta_rel).parts:
        return "la fuente tiene que ser una ruta relativa dentro del árbol"
    candidata = (raiz / ruta_rel).resolve()
    if candidata == ruta_documento.resolve():
        return "el documento de contrato no puede ser la fuente de su propia corrección"
    if _sede_no_admisible(ruta_rel) or ruta_rel.startswith(".plans/"):
        return "la fuente es un artefacto de este flujo y no una fuente independiente"
    return ""


def _otras_fuentes(raiz: Path, ruta_documento: Path, afirmacion: str) -> list[str]:
    """Los documentos del árbol que **sí** contienen la afirmación.

    Se calcula solo cuando la atribución ya falló: recorrer el árbol por cada corrección en el
    camino sano costaría en toda corrida y no diría nada nuevo. Lo que separa es «la citaste mal» de
    «no la dijo nadie», que son dos defectos distintos y piden dos arreglos distintos."""
    buscado = _norm_contrato(afirmacion)
    if not buscado:
        return []
    ignorados = {".git", ".plans", ".specify", ".cross-model", ".superpowers", "node_modules"}
    hallados: list[str] = []
    for archivo in sorted(raiz.rglob("*.md")):
        if any(parte in ignorados for parte in archivo.relative_to(raiz).parts):
            continue
        if archivo.resolve() == ruta_documento.resolve():
            continue
        try:
            cuerpo = archivo.read_text(encoding="utf-8")
        except OSError:
            continue
        if buscado in _norm_contrato(cuerpo):
            hallados.append(archivo.relative_to(raiz).as_posix())
    return hallados


def _verificar_alcance(texto: str, problemas: list[Problema], resumen: dict) -> None:
    tabla = _tabla_de_seccion(texto, SLUG_ALCANCE)
    if tabla is None or not tabla.filas:
        problemas.append(Problema(
            "alcance_ausente", f"sección `{SLUG_ALCANCE}`",
            "el contrato tiene que declarar el alcance comprometido del programa como una tabla con "
            "al menos un tramo; sin él, las correcciones y las decisiones diferidas describen un "
            "programa cuyos límites nadie escribió"))
        return
    for falta in _columnas_faltantes(tabla, COLUMNAS_ALCANCE):
        problemas.append(Problema("columna_ausente", f"sección `{SLUG_ALCANCE}`",
                                  f"la tabla del alcance no declara la columna `{falta}`"))
    resumen["tramos"] = len(tabla.filas)


def _verificar_correcciones(texto: str, ruta_documento: Path, raiz: Path,
                            problemas: list[Problema], resumen: dict) -> None:
    tabla = _tabla_de_seccion(texto, SLUG_CORRECCIONES)
    if tabla is None or not tabla.filas:
        problemas.append(Problema(
            "correcciones_ausentes", f"sección `{SLUG_CORRECCIONES}`",
            "el contrato tiene que declarar al menos una corrección con su tabla; una sección vacía "
            "no es «no había nada que corregir», es una sección sin escribir"))
        return
    faltantes = _columnas_faltantes(tabla, COLUMNAS_CORRECCIONES)
    for falta in faltantes:
        problemas.append(Problema("columna_ausente", f"sección `{SLUG_CORRECCIONES}`",
                                  f"la tabla de correcciones no declara la columna `{falta}`"))
    resumen["correcciones"] = len(tabla.filas)

    vistos: set[str] = set()
    for fila in tabla.filas:
        ident = _clave_de_fila(fila) or "(sin id)"
        donde = f"corrección `{ident}`"
        if ident in vistos:
            problemas.append(Problema("id_duplicado", donde,
                                      "otra corrección ya usa ese identificador, y con dos filas "
                                      "homónimas ningún reporte puede nombrar cuál falló"))
        vistos.add(ident)

        anterior = _celda_de(tabla, fila, "afirmacion anterior")
        corregida = _celda_de(tabla, fila, "afirmacion corregida")
        evidencia = _celda_de(tabla, fila, "evidencia")
        supersesion = _celda_de(tabla, fila, "supersesion")
        fuente = _celda_de(tabla, fila, "documento fuente")

        if anterior == "":
            problemas.append(Problema("correccion_sin_texto_anterior", donde,
                                      "no declara el texto que reemplaza, así que no hay nada que "
                                      "atribuir ni con qué cotejar la fuente"))
        if corregida == "":
            problemas.append(Problema("correccion_sin_texto_corregido", donde,
                                      "no declara el texto corregido: dice qué estaba mal y no qué "
                                      "vale ahora"))
        if evidencia == "":
            problemas.append(Problema("correccion_sin_evidencia", donde,
                                      "no declara la evidencia que sostiene la corrección"))
        if supersesion == "":
            problemas.append(Problema("correccion_sin_supersesion", donde,
                                      "no declara la cláusula que establece que este contrato "
                                      "prevalece sobre la fuente corregida"))
        if fuente == "":
            problemas.append(Problema("correccion_sin_fuente", donde,
                                      "no declara de qué documento sale la afirmación que "
                                      "reemplaza"))
        if not fuente:
            continue

        motivo = _fuente_no_admisible(fuente, ruta_documento, raiz)
        if motivo:
            problemas.append(Problema("fuente_no_admisible", donde, f"`{fuente}`: {motivo}"))
            continue
        archivo = raiz / fuente
        if not archivo.is_file():
            problemas.append(Problema("fuente_irresoluble", donde,
                                      f"`{fuente}` no existe bajo la raíz `{raiz}`"))
            continue
        if supersesion and Path(fuente).name.lower() not in supersesion.lower():
            problemas.append(Problema(
                "supersesion_no_nombra_la_fuente", donde,
                f"la cláusula de supersesión no nombra a `{Path(fuente).name}`: «este contrato "
                "prevalece» sin decir sobre qué no supersede nada"))
        if not anterior:
            continue

        cuerpo = _norm_contrato(archivo.read_text(encoding="utf-8"))
        if _norm_contrato(anterior) in cuerpo:
            resumen["atribuciones_resueltas"] += 1
            continue
        otras = _otras_fuentes(raiz, ruta_documento, anterior)
        if otras:
            problemas.append(Problema(
                "fuente_equivocada", donde,
                f"la afirmación reemplazada no vive en `{fuente}` sino en "
                f"{', '.join('`' + o + '`' for o in otras[:3])}: la fuente declarada no es el "
                "documento donde vive el texto que se corrige"))
        else:
            problemas.append(Problema(
                "afirmacion_inexistente_en_la_fuente", donde,
                f"`{fuente}` no contiene la afirmación que se le atribuye, y ningún otro documento "
                "del árbol tampoco: la corrección le adjudica algo que no dijo"))


def _verificar_decisiones(texto: str, problemas: list[Problema], resumen: dict) -> None:
    tabla = _tabla_de_seccion(texto, SLUG_DECISIONES)
    if tabla is None or not tabla.filas:
        problemas.append(Problema(
            "decisiones_ausentes", f"sección `{SLUG_DECISIONES}`",
            "el contrato tiene que registrar las decisiones doctrinales abiertas como diferidas; "
            "una sección sin filas se lee como «no quedó ninguna abierta», que es una afirmación "
            "distinta y más fuerte que no haberlas escrito"))
        return
    for falta in _columnas_faltantes(tabla, COLUMNAS_DECISIONES):
        problemas.append(Problema("columna_ausente", f"sección `{SLUG_DECISIONES}`",
                                  f"la tabla de decisiones diferidas no declara la columna "
                                  f"`{falta}`"))
    resumen["decisiones"] = len(tabla.filas)

    vistos: set[str] = set()
    for fila in tabla.filas:
        ident = _clave_de_fila(fila) or "(sin id)"
        donde = f"decisión `{ident}`"
        if ident in vistos:
            problemas.append(Problema("id_duplicado", donde,
                                      "otra decisión diferida ya usa ese identificador"))
        vistos.add(ident)

        estado = _celda_de(tabla, fila, "estado")
        fase = _celda_de(tabla, fila, "fase de destino")
        if estado is not None and _norm_contrato(estado) != ESTADO_DIFERIDA:
            problemas.append(Problema(
                "decision_no_diferida", donde,
                f"su estado es `{estado or '(vacío)'}` y tiene que ser `{ESTADO_DIFERIDA}`: el "
                "alcance de esta fase declara que las decisiones doctrinales quedan íntegramente "
                "diferidas, así que resolver una acá la contradice"))
        if fase == "":
            problemas.append(Problema(
                "decision_sin_fase", donde,
                "no declara su fase de destino; diferir sin decir a dónde es postergar sin plazo"))
        elif fase is not None:
            resumen["decisiones_con_fase"] += 1


def verificar_contrato(texto: str, ruta_documento: Path,
                       raiz: Path) -> tuple[list[Problema], dict]:
    """Las tres mitades de AC-1 en un solo recorrido: el alcance, las correcciones con su atribución
    **resuelta contra el documento fuente**, y las decisiones diferidas con su fase.

    `atribuciones_resueltas` no es decorativo: es la evidencia de que la atribución se comprobó. Un
    oráculo de «hay fuente» pasa todas las correcciones y deja ese contador en cero."""
    problemas: list[Problema] = []
    resumen = {"tramos": 0, "correcciones": 0, "decisiones": 0, "decisiones_con_fase": 0,
               "atribuciones_resueltas": 0}
    _verificar_alcance(texto, problemas, resumen)
    _verificar_correcciones(texto, ruta_documento, raiz, problemas, resumen)
    _verificar_decisiones(texto, problemas, resumen)
    return problemas, resumen


# --- Modo de los tres ejes --------------------------------------------------------------------

class FilaDeEje(NamedTuple):
    eje: str
    indice: int
    celda: str        # el literal tal como lo escribe el documento, con su namespace
    literal: str      # el literal desnudo, con el namespace ya sacado si lo tenía
    tipo: str | None
    sede: str | None
    significado: str | None


def _partir_namespace(celda: str) -> tuple[str | None, str]:
    """(namespace, literal desnudo). El namespace es `None` cuando la celda no lo trae.

    El literal desnudo se devuelve **igual traiga o no namespace**, y eso es deliberado: si una
    celda sin namespace quedara fuera del conjunto declarado, el mutante que le saca el namespace
    emitiría además un `literal_de_menos` y su atribución dejaría de ser propia."""
    namespace, punto, resto = celda.partition(".")
    if not punto:
        return None, celda
    return namespace, resto


def _sede_fuera_de_skills(sede: str) -> str:
    """Por qué esa sede no puede respaldar un literal, o `""` si puede.

    La regla es más dura que la de las procedencias de la matriz y a propósito: no alcanza con que
    no sea un artefacto de este flujo, tiene que vivir bajo `skills/`. El documento de contrato no
    existe todavía y estos fixtures son de esta misma task; un literal que apuntara a cualquiera de
    los dos coincidiría siempre consigo mismo."""
    ruta = sede.partition("#")[0]
    if ruta.startswith("/") or ".." in Path(ruta).parts:
        return "la sede tiene que ser una ruta relativa dentro del árbol"
    if not ruta.startswith(PREFIJO_DE_SEDE_NORMATIVA):
        return (f"la sede tiene que vivir bajo `{PREFIJO_DE_SEDE_NORMATIVA}`: el vocabulario de "
                "cada eje sale de las skills que ya lo usan, y un literal que se cita a sí mismo o "
                "cita un artefacto de este flujo no aporta evidencia independiente")
    return ""


def _resolver_sede_de_eje(sede: str, literal: str, raiz: Path) -> str:
    """`""` si la sede resuelve y el literal está ahí; si no, el código del problema."""
    ruta_rel, _, fragmento = sede.partition("#")
    archivo = raiz / ruta_rel
    if not fragmento or not archivo.is_file():
        return "sede_irresoluble"
    cuerpo = archivo.read_text(encoding="utf-8")
    rango = _rangos_de_secciones(cuerpo).get(fragmento)
    if rango is None:
        return "sede_irresoluble"
    lineas = cuerpo.split("\n")[rango[0]:rango[1] + 1]
    patron = re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(literal) + r"(?![A-Za-z0-9_-])")
    return "" if any(patron.search(l) for l in lineas) else "literal_ausente_en_la_sede"


def _leer_ejes(texto: str, problemas: list[Problema]) -> dict[str, list[FilaDeEje]]:
    """Las filas declaradas por eje. Un eje sin sección o con la tabla vacía no aporta filas y su
    problema se emite acá: seguir con la comparación de conjuntos agregaría un `literal_de_menos`
    por cada literal del inventario y taparía la causa con seis síntomas."""
    declarados: dict[str, list[FilaDeEje]] = {}
    rangos = _rangos_de_secciones(texto)

    for slug in sorted(rangos):
        if slug.startswith("eje-") and slug not in SLUGS_DE_EJE.values():
            problemas.append(Problema(
                "eje_desconocido", f"sección `{slug}`",
                "el contrato declara un eje que no es ninguno de los tres; un cuarto eje con "
                "vocabulario propio es exactamente la fusión que este modo existe para impedir, "
                "solo que declarada"))

    for eje in EJES:
        slug = SLUGS_DE_EJE[eje]
        declarados[eje] = []
        if slug not in rangos:
            problemas.append(Problema("eje_ausente", f"eje `{eje}`",
                                      f"el contrato no declara la sección `{slug}`"))
            continue
        tabla = _tabla_de_seccion(texto, slug)
        if tabla is None or not tabla.filas:
            problemas.append(Problema("eje_sin_literales", f"eje `{eje}`",
                                      "la sección existe y no declara ningún literal"))
            continue
        for falta in _columnas_faltantes(tabla, COLUMNAS_EJE):
            problemas.append(Problema("columna_ausente", f"eje `{eje}`",
                                      f"la tabla del eje no declara la columna `{falta}`"))
        for i, fila in enumerate(tabla.filas):
            celda = _clave_de_fila(fila)
            _, desnudo = _partir_namespace(celda)
            declarados[eje].append(FilaDeEje(
                eje, i, celda, desnudo,
                _celda_de(tabla, fila, "tipo"),
                _celda_de(tabla, fila, "sede"),
                _celda_de(tabla, fila, "significado")))
    return declarados


def _comparar_vocabulario(eje: str, filas: list[FilaDeEje],
                          problemas: list[Problema]) -> None:
    """La igualdad exacta contra el inventario, y las tres fusiones que AC-2 nombra.

    El orden importa y no es casual: **unión primero**, porque un eje que absorbió otro entero
    también tiene sobrantes y reportarlos uno a uno describiría el síntoma en vez de la causa;
    después los **ajenos**, que se sacan del conjunto de sobrantes para que la sustitución no los
    cuente; y recién entonces alta, baja y sustitución, que son las tres que solo el inventario
    congelado puede ver."""
    esperados = {l.literal for l in INVENTARIO_DE_EJES[eje]}
    declarados = [f.literal for f in filas]
    conjunto = set(declarados)

    for literal in sorted({l for l in declarados if declarados.count(l) > 1}):
        problemas.append(Problema("literal_duplicado", f"eje `{eje}`",
                                  f"`{literal}` aparece más de una vez en el mismo eje"))

    for otro in EJES:
        if otro == eje:
            continue
        exclusivos = {l.literal for l in INVENTARIO_DE_EJES[otro]} - esperados
        if exclusivos and exclusivos <= conjunto and esperados <= conjunto:
            problemas.append(Problema(
                "enum_union", f"eje `{eje}`",
                f"declara su vocabulario **y** el de `{otro}` entero "
                f"({', '.join('`' + e + '`' for e in sorted(exclusivos))}): un enum unión responde "
                "las dos preguntas con un solo valor y deja de poder responder ninguna"))
            return

    sobrantes = conjunto - esperados
    faltantes = esperados - conjunto
    ajenos = {s for s in sobrantes
              if any(s in {l.literal for l in INVENTARIO_DE_EJES[o]} for o in EJES if o != eje)}
    for literal in sorted(ajenos):
        duenos = [o for o in EJES
                  if o != eje and literal in {l.literal for l in INVENTARIO_DE_EJES[o]}]
        problemas.append(Problema(
            "enum_ajeno", f"eje `{eje}`",
            f"`{literal}` es del vocabulario de {', '.join('`' + d + '`' for d in duenos)} y no de "
            "este: usar el enum de un eje en el lugar de otro los fusiona sin decirlo"))
    sobrantes -= ajenos

    if sobrantes and faltantes:
        problemas.append(Problema(
            "literal_sustituido", f"eje `{eje}`",
            f"cambia {', '.join('`' + f + '`' for f in sorted(faltantes))} por "
            f"{', '.join('`' + s + '`' for s in sorted(sobrantes))} conservando la cantidad: un "
            "verificador que contara literales lo dejaría pasar"))
    elif sobrantes:
        problemas.append(Problema(
            "literal_de_mas", f"eje `{eje}`",
            f"declara {', '.join('`' + s + '`' for s in sorted(sobrantes))}, que el inventario "
            "normativo no tiene"))
    elif faltantes:
        problemas.append(Problema(
            "literal_de_menos", f"eje `{eje}`",
            f"no declara {', '.join('`' + f + '`' for f in sorted(faltantes))}, que el inventario "
            "normativo sí tiene"))


def _compartidos_sin_distincion(declarados: dict[str, list[FilaDeEje]]) -> set[tuple[str, int]]:
    """Las filas de un literal que aparece en dos ejes **con el mismo tipo y la misma sede**.

    Es la fusión disfrazada de compartición: un literal repetido es legítimo mientras nombre dos
    cosas distintas, y deja de serlo cuando las dos declaraciones son la misma cosa escrita dos
    veces. Las filas que caen acá quedan exentas del cotejo de tipo y sede contra el inventario: el
    diagnóstico específico gana, y emitir además dos genéricos escondería cuál es el problema."""
    por_literal: dict[str, list[FilaDeEje]] = {}
    for filas in declarados.values():
        for fila in filas:
            por_literal.setdefault(fila.literal, []).append(fila)
    involucradas: set[tuple[str, int]] = set()
    for apariciones in por_literal.values():
        ejes_vistos = {f.eje for f in apariciones}
        if len(ejes_vistos) < 2:
            continue
        for i, una in enumerate(apariciones):
            for otra in apariciones[i + 1:]:
                if una.eje == otra.eje:
                    continue
                if una.tipo == otra.tipo and una.sede == otra.sede:
                    involucradas.add((una.eje, una.indice))
                    involucradas.add((otra.eje, otra.indice))
    return involucradas


def verificar_ejes(texto: str, raiz: Path) -> tuple[list[Problema], dict]:
    """Los tres ejes contra el inventario normativo, literal por literal y puntero por puntero.

    `sedes_resueltas` es la evidencia de que los punteros se ejercieron: un modo que comparara solo
    la forma de las columnas pasa todas las filas y deja ese contador en cero."""
    problemas: list[Problema] = []
    resumen = {"ejes": 0, "literales": 0, "sedes_resueltas": 0, "compartidos": 0}
    declarados = _leer_ejes(texto, problemas)
    resumen["ejes"] = sum(1 for eje in EJES if declarados[eje])
    resumen["literales"] = sum(len(f) for f in declarados.values())

    exentas = _compartidos_sin_distincion(declarados)
    for literal in sorted({f.literal for filas in declarados.values() for f in filas
                           if (f.eje, f.indice) in exentas}):
        problemas.append(Problema(
            "compartido_sin_distincion", f"literal `{literal}`",
            "aparece en dos ejes con el mismo tipo y la misma sede: un literal compartido es "
            "legítimo mientras nombre dos cosas distintas, y dos declaraciones idénticas son la "
            "misma cosa escrita dos veces"))

    contados: set[str] = set()
    for filas in declarados.values():
        for fila in filas:
            if len({f.eje for fs in declarados.values() for f in fs if f.literal == fila.literal}) > 1:
                contados.add(fila.literal)
    resumen["compartidos"] = len(contados)

    for eje in EJES:
        filas = declarados[eje]
        if not filas:
            continue
        _comparar_vocabulario(eje, filas, problemas)
        esperado_por_literal = {l.literal: l for l in INVENTARIO_DE_EJES[eje]}
        for fila in filas:
            donde = f"eje `{eje}`, literal `{fila.celda or '(vacío)'}`"
            namespace, _ = _partir_namespace(fila.celda)
            if namespace is None:
                problemas.append(Problema(
                    "perdida_de_namespace", donde,
                    f"el literal se declara sin su namespace; tiene que escribirse "
                    f"`{eje}.{fila.literal}`, porque el mismo token citado en otra sección no dice "
                    "de qué eje es"))
            elif namespace != eje:
                problemas.append(Problema(
                    "namespace_no_coincide", donde,
                    f"lleva el namespace `{namespace}` dentro de la sección de `{eje}`"))

            if fila.tipo == "":
                problemas.append(Problema("tipo_ausente", donde,
                                          "no declara su tipo, que es lo que distingue un literal "
                                          "compartido de una fusión"))
            if fila.significado == "":
                problemas.append(Problema("significado_ausente", donde,
                                          "no declara su significado"))
            if fila.sede is None:
                continue
            if fila.sede == "":
                problemas.append(Problema("sede_ausente", donde,
                                          "no declara la sede de la que sale el literal"))
                continue
            motivo = _sede_fuera_de_skills(fila.sede)
            if motivo:
                problemas.append(Problema("sede_fuera_de_skills", donde,
                                          f"`{fila.sede}`: {motivo}"))
                continue
            codigo = _resolver_sede_de_eje(fila.sede, fila.literal, raiz)
            if codigo == "sede_irresoluble":
                problemas.append(Problema("sede_irresoluble", donde,
                                          f"`{fila.sede}` no resuelve contra el árbol: el archivo o "
                                          "la sección no existen"))
                continue
            if codigo == "literal_ausente_en_la_sede":
                problemas.append(Problema(
                    "literal_ausente_en_la_sede", donde,
                    f"`{fila.sede}` resuelve y no contiene `{fila.literal}`: el puntero apunta a una "
                    "sección real que no dice nada de este literal"))
                continue
            resumen["sedes_resueltas"] += 1

            esperado = esperado_por_literal.get(fila.literal)
            if esperado is None or (eje, fila.indice) in exentas:
                continue
            if fila.tipo and fila.tipo != esperado.tipo:
                problemas.append(Problema(
                    "tipo_no_coincide", donde,
                    f"declara el tipo `{fila.tipo}` y el inventario normativo dice "
                    f"`{esperado.tipo}`"))
            if fila.sede != esperado.sede:
                problemas.append(Problema(
                    "sede_no_coincide", donde,
                    f"declara la sede `{fila.sede}` y el inventario normativo dice "
                    f"`{esperado.sede}`; la sede resuelve, así que solo el puntero congelado lo ve"))
    return problemas, resumen


# --- Modo de marcas de capacidad de plataforma ------------------------------------------------

def verificar_capacidades(texto: str) -> tuple[list[Problema], dict]:
    """AC-3 es un cuantificador universal —«toda afirmación»—, así que el recorrido es por fila y
    ningún problema corta el resto: con un solo defecto en un documento de afirmaciones válidas, un
    verificador que comprobara que existe *alguna* marca y *alguna* versión quedaría verde."""
    problemas: list[Problema] = []
    resumen = {"afirmaciones": 0, "marcadas": 0, "portables": 0, "dependientes": 0,
               "no_verificables": 0}
    tabla = _tabla_de_seccion(texto, SLUG_CAPACIDADES)
    if tabla is None or not tabla.filas:
        problemas.append(Problema(
            "capacidades_ausentes", f"sección `{SLUG_CAPACIDADES}`",
            "el contrato tiene que declarar sus afirmaciones de plataforma con su marca; una tabla "
            "sin filas satisface «toda afirmación está marcada» por vacuidad"))
        return problemas, resumen
    for falta in _columnas_faltantes(tabla, COLUMNAS_CAPACIDADES):
        problemas.append(Problema("columna_ausente", f"sección `{SLUG_CAPACIDADES}`",
                                  f"la tabla de capacidades no declara la columna `{falta}`"))
    resumen["afirmaciones"] = len(tabla.filas)

    for i, fila in enumerate(tabla.filas):
        afirmacion = _celda_de(tabla, fila, "afirmacion")
        etiqueta = (afirmacion or "")[:60]
        donde = f"afirmación {i + 1}" + (f" «{etiqueta}…»" if etiqueta else "")
        if afirmacion == "":
            problemas.append(Problema("afirmacion_vacia", donde,
                                      "la fila no declara ninguna afirmación"))
        marca = _celda_de(tabla, fila, "marca")
        version = _celda_de(tabla, fila, "version")
        motivo = _celda_de(tabla, fila, "motivo")
        if marca is None:
            continue
        if marca == "":
            problemas.append(Problema(
                "afirmacion_sin_marca", donde,
                "se afirma sin marca: toda afirmación de plataforma va marcada portable, "
                "dependiente o no verificable"))
            continue
        if marca not in MARCAS_DE_CAPACIDAD:
            problemas.append(Problema(
                "marca_desconocida", donde,
                f"`{marca}` no es una marca: el vocabulario es "
                f"{', '.join('`' + m + '`' for m in MARCAS_DE_CAPACIDAD)}"))
            continue
        resumen["marcadas"] += 1
        if marca == "portable":
            resumen["portables"] += 1
        elif marca == "dependiente":
            resumen["dependientes"] += 1
            if version == "":
                problemas.append(Problema(
                    "dependiente_sin_version", donde,
                    "es dependiente de plataforma y no registra la versión con la que se comprobó"))
            elif version is not None and not PATRON_VERSION_COMPROBADA.match(version):
                problemas.append(Problema(
                    "version_sin_forma", donde,
                    f"`{version}` no dice qué se comprobó y con qué número; una versión comprobada "
                    "nombra las dos cosas"))
        else:
            resumen["no_verificables"] += 1
            if motivo == "":
                problemas.append(Problema(
                    "no_verificable_sin_motivo", donde,
                    "se marca no verificable y no dice qué es lo que el runtime no expone"))
            if version:
                problemas.append(Problema(
                    "no_verificable_con_version", donde,
                    f"se marca no verificable y a la vez registra la versión `{version}` con la que "
                    "se la comprobó; si se comprobó, es dependiente"))
    return problemas, resumen


# --- Los tres modos de aplicación --------------------------------------------------------------

def _leer_documento_de_contrato(ruta: Path, etiqueta: str) -> tuple[str | None, int]:
    """El texto del documento, o `None` y el código con el que hay que terminar."""
    if _falta_la_primitiva():
        return None, 1
    if not ruta.is_file():
        print(f"AUSENTE  no existe el documento de contrato en {ruta}")
        print(f"         `--{etiqueta}` no lo lee como conforme: el documento lo escribe la task "
              "que lo materializa, y hasta entonces no hay veredicto que dar. Este modo termina "
              f"con {CODIGO_DOCUMENTO_AUSENTE}, que no es 0 ni 1.")
        return None, CODIGO_DOCUMENTO_AUSENTE
    return ruta.read_text(encoding="utf-8"), 0


def modo_contrato(ruta: Path, raiz: Path) -> int:
    texto, codigo = _leer_documento_de_contrato(ruta, "contrato")
    if texto is None:
        return codigo
    problemas, resumen = verificar_contrato(texto, ruta, raiz)
    if problemas:
        _informar(problemas, f"{ruta.name} — alcance, correcciones y decisiones diferidas")
        return 1
    print(f"OK     {ruta.name}: alcance con {resumen['tramos']} tramos, "
          f"{resumen['correcciones']} correcciones completas y {resumen['decisiones']} decisiones "
          f"diferidas con su fase")
    print(f"OK     las {resumen['atribuciones_resueltas']} atribuciones se resolvieron contra su "
          "documento fuente: el texto reemplazado vive ahí")
    print()
    print("RESULTADO: OK")
    return 0


def modo_ejes(ruta: Path, raiz: Path) -> int:
    texto, codigo = _leer_documento_de_contrato(ruta, "ejes")
    if texto is None:
        return codigo
    problemas, resumen = verificar_ejes(texto, raiz)
    if problemas:
        _informar(problemas, f"{ruta.name} — los tres ejes y sus vocabularios")
        return 1
    print(f"OK     {ruta.name}: los {resumen['ejes']} ejes declaran {resumen['literales']} literales "
          "en igualdad exacta con el inventario normativo")
    print(f"OK     las {resumen['sedes_resueltas']} sedes resuelven contra el árbol y contienen su "
          f"literal; {resumen['compartidos']} literal(es) compartido(s) conservan tipo y sede "
          "distintos")
    print()
    print("RESULTADO: OK")
    return 0


def modo_capacidades(ruta: Path) -> int:
    texto, codigo = _leer_documento_de_contrato(ruta, "capacidades")
    if texto is None:
        return codigo
    problemas, resumen = verificar_capacidades(texto)
    if problemas:
        _informar(problemas, f"{ruta.name} — marcas de capacidad de plataforma")
        return 1
    print(f"OK     {ruta.name}: las {resumen['afirmaciones']} afirmaciones de plataforma están "
          f"marcadas ({resumen['portables']} portables, {resumen['dependientes']} dependientes con "
          f"su versión, {resumen['no_verificables']} no verificables con su motivo)")
    print()
    print("RESULTADO: OK")
    return 0


# --- Autotests de los tres modos ---------------------------------------------------------------
#
# El corpus es `scripts/fixtures-contrato/conforme/`: un documento sintético y sus dos documentos
# fuente. Los mutantes **no** están guardados como archivos: se generan transformando el conforme
# celda a celda, así que la correspondencia caso ↔ defecto es por construcción y una columna que
# cambie de nombre rompe el mutante en vez de dejarlo pasando por otro motivo.
#
# **Nada de esto escribe en disco.** El documento se muta en memoria y la raíz que reciben los
# verificadores es el fixture congelado, en lectura. Mutar el árbol de trabajo dejaría el fixture
# mutado si el proceso muriera, y otro agente no distingue esa ventana de un cambio real.

class CasoDeContrato(NamedTuple):
    codigo: str | None      # el problema que el caso tiene que disparar; None = caso conforme
    descripcion: str
    mutar: Any = None       # (texto) -> texto


def _texto_conforme() -> str:
    return DOCUMENTO_CONFORME.read_text(encoding="utf-8")


def _indice_de_columna(tabla: Tabla, columna: str) -> int:
    if columna not in tabla.encabezados:
        raise ValueError(f"la tabla no tiene la columna `{columna}`")
    return tabla.encabezados.index(columna)


def _indice_de_fila(tabla: Tabla, clave: str) -> int:
    for i, fila in enumerate(tabla.filas):
        if _clave_de_fila(fila) == clave:
            return i
    raise ValueError(f"la tabla no tiene ninguna fila con la clave `{clave}`")


def _tabla_o_error(texto: str, slug: str) -> Tabla:
    tabla = _tabla_de_seccion(texto, slug)
    if tabla is None:
        raise ValueError(f"el documento no tiene tabla en la sección `{slug}`")
    return tabla


def _rendir_fila(celdas: list[str] | tuple[str, ...]) -> str:
    """La fila de vuelta a texto, **re-escapando** el `|` que `_celdas` desescapó. Sin esto, una
    celda que contiene una tubería escapada se parte en dos al mutarla y el mutante deja de probar
    lo suyo — el fixture tiene una a propósito, justo para que este camino no quede sin ejercer."""
    return "| " + " | ".join(c.replace("|", "\\|") for c in celdas) + " |"


def _mutar_celda(slug: str, clave: str, columna: str, nuevo: str) -> Any:
    """Reemplaza una celda por su coordenada (sección, clave de la fila, encabezado de la columna).
    Por coordenada y no por búsqueda de texto: dos celdas con el mismo contenido son un caso real —el
    mismo documento fuente en dos correcciones— y un reemplazo textual las tocaría a las dos."""
    def mutacion(texto: str) -> str:
        tabla = _tabla_o_error(texto, slug)
        k = _indice_de_columna(tabla, columna)
        i = _indice_de_fila(tabla, clave)
        lineas = texto.split("\n")
        celdas = list(_celdas(lineas[tabla.lineas_de_fila[i]]))
        while len(celdas) <= k:
            celdas.append("")
        celdas[k] = nuevo
        lineas[tabla.lineas_de_fila[i]] = _rendir_fila(celdas)
        return "\n".join(lineas)
    return mutacion


def _vaciar_celda(slug: str, clave: str, columna: str) -> Any:
    return _mutar_celda(slug, clave, columna, MARCAS_DE_VACIO[1])


def _borrar_fila(slug: str, clave: str) -> Any:
    def mutacion(texto: str) -> str:
        tabla = _tabla_o_error(texto, slug)
        i = _indice_de_fila(tabla, clave)
        lineas = texto.split("\n")
        del lineas[tabla.lineas_de_fila[i]]
        return "\n".join(lineas)
    return mutacion


def _vaciar_tabla(slug: str) -> Any:
    def mutacion(texto: str) -> str:
        tabla = _tabla_o_error(texto, slug)
        lineas = texto.split("\n")
        for numero in sorted(tabla.lineas_de_fila, reverse=True):
            del lineas[numero]
        return "\n".join(lineas)
    return mutacion


def _agregar_fila(slug: str, celdas: tuple[str, ...]) -> Any:
    def mutacion(texto: str) -> str:
        tabla = _tabla_o_error(texto, slug)
        if not tabla.lineas_de_fila:
            raise ValueError(f"la tabla de `{slug}` no tiene filas donde agregar")
        lineas = texto.split("\n")
        lineas.insert(tabla.lineas_de_fila[-1] + 1, _rendir_fila(celdas))
        return "\n".join(lineas)
    return mutacion


def _agregar_filas(slug: str, filas: tuple[tuple[str, ...], ...]) -> Any:
    def mutacion(texto: str) -> str:
        for fila in filas:
            texto = _agregar_fila(slug, fila)(texto)
        return texto
    return mutacion


def _borrar_columna(slug: str, columna: str) -> Any:
    def mutacion(texto: str) -> str:
        tabla = _tabla_o_error(texto, slug)
        k = _indice_de_columna(tabla, columna)
        lineas = texto.split("\n")
        for numero in (tabla.linea_encabezado, tabla.linea_encabezado + 1,
                       *tabla.lineas_de_fila):
            celdas = list(_celdas(lineas[numero]))
            if k < len(celdas):
                del celdas[k]
            lineas[numero] = _rendir_fila(celdas)
        return "\n".join(lineas)
    return mutacion


def _borrar_seccion(slug: str) -> Any:
    def mutacion(texto: str) -> str:
        rango = _rangos_de_secciones(texto).get(slug)
        if rango is None:
            raise ValueError(f"el documento no tiene la sección `{slug}`")
        lineas = texto.split("\n")
        del lineas[rango[0]:rango[1] + 1]
        return "\n".join(lineas)
    return mutacion


def _componer(*mutaciones: Any) -> Any:
    def mutacion(texto: str) -> str:
        for m in mutaciones:
            texto = m(texto)
        return texto
    return mutacion


def _agregar_heading(despues_de: str, titulo: str) -> Any:
    def mutacion(texto: str) -> str:
        rango = _rangos_de_secciones(texto).get(despues_de)
        if rango is None:
            raise ValueError(f"el documento no tiene la sección `{despues_de}`")
        lineas = texto.split("\n")
        lineas.insert(rango[1] + 1, "")
        lineas.insert(rango[1] + 2, titulo)
        return "\n".join(lineas)
    return mutacion


def _reemplazar_prosa(viejo: str, nuevo: str) -> Any:
    def mutacion(texto: str) -> str:
        if viejo not in texto:
            raise ValueError(f"el documento no contiene {viejo!r}")
        return texto.replace(viejo, nuevo)
    return mutacion


def _fila_de_eje(eje: str, literal: str, tipo: str, sede: str) -> tuple[str, ...]:
    return (f"`{eje}.{literal}`", tipo, f"`{sede}`", "significado sintético del caso")


def _correr_caso_de_contrato(caso: CasoDeContrato) -> tuple[list[Problema], dict]:
    texto = caso.mutar(_texto_conforme()) if caso.mutar else _texto_conforme()
    return verificar_contrato(texto, DOCUMENTO_CONFORME, CONFORME_CONTRATO)


def _correr_caso_de_ejes(caso: CasoDeContrato) -> tuple[list[Problema], dict]:
    """Los ejes se resuelven contra el **árbol real**, no contra el fixture: la propiedad que este
    modo ejerce es que cada literal salga de una sede que ya existe en `skills/`, y con un árbol
    sintético el modo y el dato acordarían entre sí."""
    texto = caso.mutar(_texto_conforme()) if caso.mutar else _texto_conforme()
    return verificar_ejes(texto, REPO)


def _correr_caso_de_capacidades(caso: CasoDeContrato) -> tuple[list[Problema], dict]:
    texto = caso.mutar(_texto_conforme()) if caso.mutar else _texto_conforme()
    return verificar_capacidades(texto)


# Los textos del corpus que los casos citan. Se derivan del fixture leyéndolo, no se transcriben:
# una transcripción quedaría vieja en cuanto el fixture cambiara y el mutante pasaría a fallar por
# otro motivo.
AFIRMACION_INEXISTENTE = "La familia gamma sintética nunca despacha dos intentos en paralelo."


def _casos_de_contrato() -> tuple[CasoDeContrato, ...]:
    return (
        # Los conformes. El segundo es la variante riesgosa que la task nombra: una corrección
        # atribuida a la propuesta doctrinal **cuando esa propuesta sí contiene** la afirmación
        # reemplazada. Un modo que rechazara toda atribución a la propuesta pasaría los dos mutantes
        # de atribución y caería acá.
        CasoDeContrato(None, "el documento conforme completo"),
        CasoDeContrato(
            None, "una corrección de más atribuida a la propuesta doctrinal, con una afirmación que "
                  "la propuesta sí contiene",
            _agregar_fila(SLUG_CORRECCIONES, (
                "C-04",
                "Si el arbitraje sintético lo ejerce el conductor o un tercero.",
                "El arbitraje sintético lo ejerce el conductor, y el tercero solo informa.",
                "El corpus registra al conductor como único árbitro en los cuatro escenarios.",
                "Este contrato prevalece sobre `propuesta-doctrinal.md` en este punto.",
                "fuentes/propuesta-doctrinal.md"))),
        CasoDeContrato(
            None, "una decisión diferida de más con su fase: aceptar más no es un defecto",
            _agregar_fila(SLUG_DECISIONES, (
                "D-03", "Si el corpus sintético admite un tercer documento fuente.", "diferida",
                "Fase 4"))),
        CasoDeContrato(
            None, "no-op: se reescribe prosa fuera de las tablas",
            _reemplazar_prosa("Su alcance, sus correcciones", "Su alcance declarado, sus correcciones")),

        # El alcance y las decisiones diferidas: las dos mitades de la fila que un modo que solo
        # validara correcciones nunca miraría.
        CasoDeContrato("alcance_ausente", "se retira la sección de alcance entera",
                       _borrar_seccion(SLUG_ALCANCE)),
        CasoDeContrato("decisiones_ausentes",
                       "se retiran las decisiones diferidas y la sección queda sin ninguna",
                       _vaciar_tabla(SLUG_DECISIONES)),
        CasoDeContrato("decision_sin_fase",
                       "una sola de las dos decisiones diferidas pierde su fase de destino",
                       _vaciar_celda(SLUG_DECISIONES, "D-02", "fase de destino")),
        CasoDeContrato("decision_no_diferida",
                       "una sola de las dos decisiones se declara resuelta en vez de diferida",
                       _mutar_celda(SLUG_DECISIONES, "D-01", "estado", "resuelta")),

        # Los cinco componentes de una corrección, uno por caso y **uno por fila**: el defecto vive
        # entre correcciones válidas, que es donde un verificador de «alguna» se disfraza de rigor.
        CasoDeContrato("correcciones_ausentes", "la tabla de correcciones se queda sin filas",
                       _vaciar_tabla(SLUG_CORRECCIONES)),
        CasoDeContrato("correccion_sin_texto_anterior", "una corrección pierde el texto anterior",
                       _vaciar_celda(SLUG_CORRECCIONES, "C-02", "afirmacion anterior")),
        CasoDeContrato("correccion_sin_texto_corregido", "una corrección pierde el texto corregido",
                       _vaciar_celda(SLUG_CORRECCIONES, "C-01", "afirmacion corregida")),
        CasoDeContrato("correccion_sin_evidencia", "una corrección pierde su evidencia",
                       _vaciar_celda(SLUG_CORRECCIONES, "C-03", "evidencia")),
        CasoDeContrato("correccion_sin_supersesion", "una corrección pierde la cláusula de "
                                                     "supersesión",
                       _vaciar_celda(SLUG_CORRECCIONES, "C-01", "supersesion")),
        CasoDeContrato("correccion_sin_fuente", "una corrección no dice de qué documento sale",
                       _vaciar_celda(SLUG_CORRECCIONES, "C-02", "documento fuente")),
        CasoDeContrato("columna_ausente", "la tabla de correcciones pierde la columna de evidencia",
                       _borrar_columna(SLUG_CORRECCIONES, "evidencia")),
        CasoDeContrato("id_duplicado", "dos correcciones comparten identificador",
                       _mutar_celda(SLUG_CORRECCIONES, "C-03", "id", "C-01")),

        # Los dos mutantes de atribución que un oráculo de «hay fuente» no caza. Los dos declaran
        # una fuente que existe, y los dos pasan cualquier comprobación de presencia.
        CasoDeContrato(
            "fuente_equivocada",
            "la fuente declarada no es el documento donde vive la afirmación reemplazada — y la "
            "cláusula de supersesión la acompaña, así que la corrección es impecable salvo por la "
            "atribución",
            _componer(_mutar_celda(SLUG_CORRECCIONES, "C-02", "documento fuente",
                                   "fuentes/propuesta-doctrinal.md"),
                      _mutar_celda(SLUG_CORRECCIONES, "C-02", "supersesion",
                                   "Este contrato prevalece sobre `propuesta-doctrinal.md` en este "
                                   "punto."))),
        CasoDeContrato(
            "afirmacion_inexistente_en_la_fuente",
            "se le atribuye a la propuesta doctrinal una afirmación que no contiene",
            _mutar_celda(SLUG_CORRECCIONES, "C-01", "afirmacion anterior",
                         AFIRMACION_INEXISTENTE)),
        CasoDeContrato("fuente_irresoluble", "la fuente declarada no existe",
                       _mutar_celda(SLUG_CORRECCIONES, "C-03", "documento fuente",
                                    "fuentes/no-existe.md")),
        CasoDeContrato(
            "fuente_no_admisible",
            "el documento se declara fuente de su propia corrección — y el texto sí está ahí, "
            "porque está en su tabla: solo la regla de admisibilidad lo ve",
            _mutar_celda(SLUG_CORRECCIONES, "C-01", "documento fuente", "contrato.md")),
        CasoDeContrato(
            "supersesion_no_nombra_la_fuente",
            "la cláusula prevalece sobre «la fuente corregida» sin nombrarla",
            _mutar_celda(SLUG_CORRECCIONES, "C-03", "supersesion",
                         "Este contrato prevalece sobre la fuente corregida.")),
    )


def _casos_de_ejes() -> tuple[CasoDeContrato, ...]:
    ciclo, validez, semantico = EJES
    slug_ciclo, slug_validez, slug_semantico = (SLUGS_DE_EJE[e] for e in EJES)
    sede_outcome = "skills/cross-review/corridas-en-vuelo.md#outcome-de-la-espera"
    sede_estados = "skills/co-explore/reference.md#estados-del-worker"
    sede_fin = "skills/co-explore/reference.md#senal-de-finalizacion"
    exclusivos_validez = tuple(l for l in INVENTARIO_DE_EJES[validez]
                               if l.literal not in {x.literal for x in INVENTARIO_DE_EJES[ciclo]})
    return (
        # Los conformes. El primero **es** el control positivo del literal compartido: `done` vive
        # en dos ejes con tipo, sede y significado distintos, y un modo que rechazara toda
        # repetición pasaría los mutantes de fusión y caería acá.
        CasoDeContrato(None, "el documento conforme, con `done` compartido por dos ejes"),
        CasoDeContrato(
            None, "reordenar las filas de un eje: el orden no es parte del contrato",
            _componer(_borrar_fila(slug_ciclo, f"{ciclo}.error"),
                      _agregar_fila(slug_ciclo, _fila_de_eje(ciclo, "error", "outcome_de_espera",
                                                             sede_outcome)))),
        CasoDeContrato(
            None, "no-op: se reescribe el significado, que es prosa y no está congelado",
            _mutar_celda(slug_validez, f"{validez}.READY", "significado",
                         "otro modo de decir lo mismo con otras palabras")),

        # Las tres fusiones que AC-2 nombra por su nombre.
        CasoDeContrato(
            "perdida_de_namespace", "un literal se declara sin su namespace",
            _mutar_celda(slug_validez, f"{validez}.READY", "literal", "`READY`")),
        CasoDeContrato(
            "namespace_no_coincide", "un literal lleva el namespace de otro eje",
            _mutar_celda(slug_ciclo, f"{ciclo}.done", "literal", f"`{semantico}.done`")),
        # Los dos declaran el literal ajeno con **su propio** tipo, no con el del eje de origen: con
        # el tipo copiado además serían un `compartido_sin_distincion`, y el mutante mediría dos
        # cosas a la vez en vez de la fusión que le toca.
        CasoDeContrato(
            "enum_ajeno", "el eje operativo estrena un literal del eje de validez",
            _agregar_fila(slug_ciclo, _fila_de_eje(ciclo, "READY", "outcome_de_espera",
                                                   sede_estados))),
        CasoDeContrato(
            "enum_union", "el eje operativo absorbe el vocabulario del de validez entero",
            _agregar_filas(slug_ciclo, tuple(
                _fila_de_eje(ciclo, l.literal, "outcome_de_espera", l.sede)
                for l in exclusivos_validez))),
        CasoDeContrato(
            "compartido_sin_distincion",
            "el `done` semántico copia el tipo y la sede del operativo: la misma cosa escrita dos "
            "veces, disfrazada de literal compartido",
            _componer(_mutar_celda(slug_semantico, f"{semantico}.done", "tipo",
                                   "marcador_de_cierre"),
                      _mutar_celda(slug_semantico, f"{semantico}.done", "sede", f"`{sede_fin}`"))),

        # Alta, baja y sustitución **dentro del vocabulario correcto**: los tres pasan namespace,
        # sede y resolución, y solo el inventario congelado los ve. `sigue_activo` es un literal
        # real de la misma sede que el contrato deja deliberadamente fuera del eje, así que el
        # mutante no se delata por una sede inventada.
        CasoDeContrato(
            "literal_de_mas", "el eje operativo estrena un literal que su sede sí contiene y el "
                              "inventario normativo no tiene",
            _agregar_fila(slug_ciclo, _fila_de_eje(ciclo, "sigue_activo", "outcome_de_espera",
                                                   sede_outcome))),
        CasoDeContrato("literal_de_menos", "el eje operativo pierde un literal del inventario",
                       _borrar_fila(slug_ciclo, f"{ciclo}.cancelacion")),
        CasoDeContrato(
            "literal_sustituido",
            "un literal del inventario se cambia por otro plausible conservando la cantidad",
            _mutar_celda(slug_ciclo, f"{ciclo}.cancelacion", "literal", f"`{ciclo}.sigue_activo`")),
        CasoDeContrato("literal_duplicado", "un literal se declara dos veces en el mismo eje",
                       _agregar_fila(slug_ciclo, _fila_de_eje(ciclo, "error", "outcome_de_espera",
                                                              sede_outcome))),

        # El puntero por literal: lo único que impide que el inventario sea una lista inventada.
        CasoDeContrato(
            "sede_fuera_de_skills",
            "un literal apunta a este mismo fixture — que existe y lo contiene, y por eso solo la "
            "regla de la sede normativa lo ve",
            _mutar_celda(slug_ciclo, f"{ciclo}.done", "sede",
                         "`scripts/fixtures-contrato/conforme/contrato.md#eje-ciclo-de-vida-operativo`")),
        CasoDeContrato("sede_irresoluble", "la sección de la sede no existe en el archivo",
                       _mutar_celda(slug_validez, f"{validez}.INVALID", "sede",
                                    "`skills/co-explore/reference.md#seccion-que-no-existe`")),
        CasoDeContrato(
            "literal_ausente_en_la_sede",
            "la sede resuelve a una sección real que no menciona el literal",
            _mutar_celda(slug_ciclo, f"{ciclo}.UNAVAILABLE", "sede", f"`{sede_fin}`")),
        CasoDeContrato(
            "sede_no_coincide",
            "la sede resuelve, contiene el literal y **no** es la del inventario congelado",
            _mutar_celda(slug_ciclo, f"{ciclo}.error", "sede",
                         "`skills/cross-review/corridas-en-vuelo.md#transiciones-del-sobre`")),
        CasoDeContrato("tipo_no_coincide", "el tipo declarado no es el del inventario",
                       _mutar_celda(slug_validez, f"{validez}.READY", "tipo", "otra_clase")),
        CasoDeContrato("sede_ausente", "un literal no declara sede",
                       _vaciar_celda(slug_validez, f"{validez}.INVALID", "sede")),
        CasoDeContrato("tipo_ausente", "un literal no declara tipo",
                       _vaciar_celda(slug_semantico, f"{semantico}.APPROVED", "tipo")),
        CasoDeContrato("significado_ausente", "un literal no declara significado",
                       _vaciar_celda(slug_ciclo, f"{ciclo}.error", "significado")),

        # La estructura de las tres secciones.
        CasoDeContrato("eje_ausente", "el contrato no declara el eje de validez",
                       _borrar_seccion(slug_validez)),
        CasoDeContrato("eje_sin_literales", "el eje de validez existe y no declara ningún literal",
                       _vaciar_tabla(slug_validez)),
        CasoDeContrato("eje_desconocido", "el contrato estrena un cuarto eje",
                       _agregar_heading(slug_semantico, "### Eje: transporte del intento")),
        CasoDeContrato("columna_ausente", "la tabla de un eje pierde la columna de tipo",
                       _borrar_columna(slug_semantico, "tipo")),
    )


def _casos_de_capacidades() -> tuple[CasoDeContrato, ...]:
    # Las claves son el **valor** de la primera celda: sin backticks y con la tubería ya
    # desescapada, que es lo que `_clave_de_fila` devuelve. Escribirlas como se ven en el Markdown
    # las dejaría sin casar y los mutantes no correrían.
    portable = ("El corte por | no escapado parte una fila de tabla igual en cualquier "
                "intérprete de Markdown del corpus.")
    dependiente = ("herramienta-sintetica exec acepta acotar el sandbox a solo lectura con una "
                   "bandera propia.")
    otro_dependiente = ("El intérprete sintético de la familia beta no admite redirección de "
                        "entrada por < y exige tubería.")
    no_verificable = ("El runtime sintético expone un identificador de proceso consultable para el "
                      "worker delegado.")
    return (
        # El conforme, con sus tres marcas ejercidas. La segunda es la variante que más se parece a
        # un defecto sin serlo: declarar algo **no verificable** es la forma correcta de tratarlo, y
        # un modo que exigiera versión a todo la rechazaría.
        CasoDeContrato(None, "el documento conforme: portables, dependientes con su versión "
                             "comprobada y una no verificable con su motivo"),
        CasoDeContrato(
            None, "una segunda afirmación no verificable: no afirmar lo que no se puede comprobar "
                  "no es un defecto",
            _agregar_fila(SLUG_CAPACIDADES, (
                "El runtime sintético informa cuánta memoria consumió el worker delegado.",
                "no_verificable", "—",
                "el harness del corpus no publica ninguna medición de memoria por worker"))),
        CasoDeContrato(
            None, "no-op: se reescribe prosa fuera de la tabla",
            _reemplazar_prosa("Toda afirmación de plataforma va marcada.",
                              "Toda afirmación de plataforma va marcada, sin excepciones.")),

        # Los mutantes **unitarios**: un solo defecto entre cuatro afirmaciones válidas. Con el
        # defecto global —todas sin marca, todas sin versión— un verificador que comprobara que
        # existe *alguna* marca y *alguna* versión quedaría verde.
        CasoDeContrato("afirmacion_sin_marca", "una sola afirmación se declara sin marca",
                       _vaciar_celda(SLUG_CAPACIDADES, portable, "marca")),
        CasoDeContrato("dependiente_sin_version",
                       "una sola dependiente pierde su versión; la otra la conserva",
                       _vaciar_celda(SLUG_CAPACIDADES, dependiente, "version")),
        CasoDeContrato("version_sin_forma",
                       "una versión que no dice qué se comprobó ni con qué número",
                       _mutar_celda(SLUG_CAPACIDADES, otro_dependiente, "version",
                                    "comprobado en el entorno del corpus")),
        CasoDeContrato("marca_desconocida", "una marca fuera del vocabulario",
                       _mutar_celda(SLUG_CAPACIDADES, portable, "marca", "dudosa")),
        CasoDeContrato("no_verificable_sin_motivo",
                       "una no verificable que no dice qué es lo que el runtime no expone",
                       _vaciar_celda(SLUG_CAPACIDADES, no_verificable, "motivo")),
        CasoDeContrato("no_verificable_con_version",
                       "una no verificable que registra la versión con la que se la comprobó",
                       _mutar_celda(SLUG_CAPACIDADES, no_verificable, "version",
                                    "runtime-sintetico 2.0")),
        CasoDeContrato("afirmacion_vacia", "una fila sin afirmación",
                       _vaciar_celda(SLUG_CAPACIDADES, portable, "afirmacion")),
        CasoDeContrato("capacidades_ausentes", "la tabla de capacidades se queda sin filas",
                       _vaciar_tabla(SLUG_CAPACIDADES)),
        CasoDeContrato("columna_ausente", "la tabla de capacidades pierde la columna de versión",
                       _borrar_columna(SLUG_CAPACIDADES, "version")),
    )


def _bloque_de_documento(nombre: str, casos: tuple[CasoDeContrato, ...], correr: Any,
                         catalogo: tuple[str, ...],
                         evidencia: Any) -> list[tuple[str, bool, str]]:
    """Los tres bloques que todo autotest de este archivo lleva, con el runner inyectado.

    `evidencia(resumen) -> str` es lo que distingue «no encontró problemas» de «comprobó algo»: un
    modo que devolviera siempre una lista vacía pasaría [A] sin haber mirado nada."""
    resultados: list[tuple[str, bool, str]] = []

    # [A] El control positivo, **por modo y no por task**: un modo cuyos casos son todos negativos
    # lo satisface una implementación que rechace cualquier entrada.
    conformes = [c for c in casos if c.codigo is None]
    fallas: list[str] = []
    for caso in conformes:
        try:
            problemas, resumen = correr(caso)
        except ValueError as exc:
            fallas.append(f"{caso.descripcion} — no corrió: {exc}")
            continue
        if problemas:
            fallas.append(f"{caso.descripcion} — {problemas[0]}")
            continue
        falta = evidencia(resumen)
        if falta:
            fallas.append(f"{caso.descripcion} — {falta}")
    resultados.append((
        f"A/{nombre}", not fallas,
        f"control positivo: los {len(conformes)} casos conformes de `--{nombre}` pasan y dejan "
        "evidencia de haber comprobado"
        if not fallas else "control positivo — " + " | ".join(fallas[:3])))

    # [B] Los mutantes, cada uno rechazado **por su motivo**: un rechazo ajeno que se le parece
    # reportaría una cobertura que no existe.
    mutantes = [c for c in casos if c.codigo is not None]
    sobrevivientes: list[str] = []
    desatribuidos: list[str] = []
    rotos: list[str] = []
    emitidos: set[str] = set()
    for caso in mutantes:
        try:
            problemas, _ = correr(caso)
        except ValueError as exc:
            rotos.append(f"{caso.codigo}: {caso.descripcion} — {exc}")
            continue
        codigos = {p.codigo for p in problemas}
        emitidos |= codigos
        if not codigos:
            sobrevivientes.append(f"{caso.codigo}: {caso.descripcion}")
        elif caso.codigo not in codigos:
            desatribuidos.append(f"{caso.codigo}: {caso.descripcion} — rechazado por "
                                 f"{sorted(codigos)} y no por su motivo")
    problemas_b = ([f"SOBREVIVE {s}" for s in sobrevivientes]
                   + [f"SIN ATRIBUIR {d}" for d in desatribuidos]
                   + [f"NO CORRIÓ {r}" for r in rotos])
    resultados.append((
        f"B/{nombre}", not problemas_b,
        f"{len(mutantes)} mutantes de `--{nombre}` y los {len(mutantes)} rechazados por su motivo"
        if not problemas_b else f"{len(problemas_b)} problemas: " + " | ".join(problemas_b[:5])))

    # [C] Un caso por código: un código sin caso es una restricción que nadie comprobó que pueda
    # ponerse roja, y un código emitido y no catalogado es una que nadie declaró.
    ejercidos = {c.codigo for c in mutantes}
    problemas_c = [f"`{c}` está en el catálogo y ningún caso lo ejerce"
                   for c in catalogo if c not in ejercidos]
    problemas_c += [f"`{c}` lo emite el modo y no está en el catálogo"
                    for c in sorted((emitidos | ejercidos) - set(catalogo))]
    resultados.append((
        f"C/{nombre}", not problemas_c,
        f"los {len(catalogo)} códigos de `--{nombre}` tienen su caso"
        if not problemas_c else f"{len(problemas_c)} huecos: " + " | ".join(problemas_c[:5])))
    return resultados


def _preludio_del_corpus() -> list[tuple[str, bool, str]]:
    """Lo que tiene que valer antes de correr un solo caso de cualquiera de los tres modos."""
    if not RUTA_PRIMITIVA_BIYECCION.is_file():
        return [("0.primitiva", False,
                 f"no está {RUTA_PRIMITIVA_BIYECCION.name}, del que sale la normalización que este "
                 "modo reusa")]
    faltan = [str(r) for r in (DOCUMENTO_CONFORME,
                               CONFORME_CONTRATO / "fuentes" / "propuesta-doctrinal.md",
                               CONFORME_CONTRATO / "fuentes" / "exploracion-previa.md")
              if not Path(r).is_file()]
    return [("0.corpus", not faltan,
             f"el corpus conforme está completo ({CONFORME_CONTRATO})"
             if not faltan else "faltan archivos del corpus: " + " | ".join(faltan))]


def _bloque_de_ausencia(nombre: str, correr: Any) -> list[tuple[str, bool, str]]:
    """[D] Un documento ausente **no** se lee como conforme, y uno presente sí se lee.

    Las dos direcciones, porque cada una sola admite una implementación degenerada: solo la primera
    la satisface un modo que devolviera siempre `CODIGO_DOCUMENTO_AUSENTE`, y solo la segunda, uno
    que devolviera siempre 0."""
    ausente = DIR_FIXTURES_CONTRATO / "conforme" / "documento-que-no-existe.md"
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo_ausente = correr(ausente)
        codigo_presente = correr(DOCUMENTO_CONFORME)
    return [
        (f"D1/{nombre}", codigo_ausente == CODIGO_DOCUMENTO_AUSENTE,
         f"sin documento, `--{nombre}` termina con {CODIGO_DOCUMENTO_AUSENTE} y no con 0: la "
         "ausencia no es conformidad"
         if codigo_ausente == CODIGO_DOCUMENTO_AUSENTE else
         f"sin documento terminó con {codigo_ausente}"),
        (f"D2/{nombre}", codigo_presente == 0,
         f"y con el documento conforme del corpus, `--{nombre}` termina con 0"
         if codigo_presente == 0 else
         f"el documento conforme del corpus terminó con {codigo_presente}"),
    ]


def modo_autotest_contrato() -> int:
    resultados = _preludio_del_corpus()
    if all(ok for _, ok, _ in resultados):
        resultados += _bloque_de_documento(
            "contrato", _casos_de_contrato(), _correr_caso_de_contrato, CODIGOS_CONTRATO,
            # El conteo tiene que ser positivo **y** completo. Con solo la igualdad, un modo que no
            # leyera nada dejaría los dos contadores en cero, satisfaría `0 == 0` y pasaría el
            # control positivo sin haber mirado una sola corrección.
            lambda r: (f"leyó {r['correcciones']} correcciones y {r['decisiones']} decisiones: no "
                       "recorrió el documento"
                       if not (r["correcciones"] and r["decisiones"] and r["tramos"]) else
                       f"resolvió {r['atribuciones_resueltas']} de {r['correcciones']} atribuciones "
                       "contra su documento fuente"
                       if r["atribuciones_resueltas"] != r["correcciones"] else
                       f"{r['decisiones_con_fase']} de {r['decisiones']} decisiones con fase"
                       if r["decisiones_con_fase"] != r["decisiones"] else ""))
        resultados += _bloque_de_ausencia(
            "contrato", lambda ruta: modo_contrato(ruta, CONFORME_CONTRATO))
    return _cierre("el contrato declara su alcance, cada corrección sus cinco componentes con la "
                   "atribución resuelta contra la fuente, y sus decisiones diferidas con su fase",
                   resultados)


def _preludio_de_ejes() -> list[tuple[str, bool, str]]:
    """El bloque que sostiene todo lo demás: **cada literal del inventario apunta a una sede real de
    `skills/` que ya existe hoy y que lo contiene.**

    Los mutantes impiden que el verificador sea laxo; no impiden que el inventario sea inventado.
    Esto sí: si un literal se lo hubiera inventado esta task, no habría sección donde encontrarlo."""
    resultados = _preludio_del_corpus()
    if not all(ok for _, ok, _ in resultados):
        return resultados

    fallas: list[str] = []
    for eje, literales in INVENTARIO_DE_EJES.items():
        for entrada in literales:
            motivo = _sede_fuera_de_skills(entrada.sede)
            if motivo:
                fallas.append(f"{eje}.{entrada.literal} — {motivo}")
                continue
            codigo = _resolver_sede_de_eje(entrada.sede, entrada.literal, REPO)
            if codigo:
                fallas.append(f"{eje}.{entrada.literal} — `{entrada.sede}`: {codigo}")
    total = sum(len(v) for v in INVENTARIO_DE_EJES.values())
    resultados.append((
        "0.punteros", not fallas,
        f"los {total} literales del inventario normativo resuelven contra el árbol real bajo "
        f"`{PREFIJO_DE_SEDE_NORMATIVA}` y su sede los contiene"
        if not fallas else f"{len(fallas)} punteros sin respaldo: " + " | ".join(fallas[:4])))

    # El literal compartido tiene que existir en el inventario, o el control positivo del modo no
    # ejerce nada: sin él, «no falla ante un literal compartido» es cierto por vacuidad.
    apariciones: dict[str, list[LiteralDeEje]] = {}
    for literales in INVENTARIO_DE_EJES.values():
        for entrada in literales:
            apariciones.setdefault(entrada.literal, []).append(entrada)
    compartidos = {lit: v for lit, v in apariciones.items() if len(v) > 1}
    distinguidos = {lit for lit, v in compartidos.items()
                    if len({e.tipo for e in v}) == len(v) and len({e.sede for e in v}) == len(v)}
    resultados.append((
        "0.compartido", bool(compartidos) and compartidos.keys() == distinguidos,
        f"el inventario tiene {len(compartidos)} literal(es) compartido(s) por dos ejes "
        f"({', '.join('`' + l + '`' for l in sorted(compartidos))}) y cada uno conserva tipo y sede "
        "distintos"
        if compartidos and compartidos.keys() == distinguidos else
        "el inventario no tiene ningún literal compartido con tipo y sede distintos, así que el "
        "control positivo del modo no ejercería nada"))

    # Y los ejes no pueden ser uno subconjunto de otro, o el mutante de unión sería indistinguible
    # de no hacer nada.
    solapes = [f"{a} ⊆ {b}" for a in EJES for b in EJES if a != b
               and {l.literal for l in INVENTARIO_DE_EJES[a]}
               <= {l.literal for l in INVENTARIO_DE_EJES[b]}]
    resultados.append((
        "0.disjuntos", not solapes,
        "ningún eje es subconjunto de otro, así que la unión y el enum ajeno son distinguibles"
        if not solapes else "hay ejes contenidos en otros: " + " | ".join(solapes)))

    # El fixture conforme no puede divergir del inventario: si divergiera, el control positivo del
    # modo estaría midiendo otra cosa que la que la fila declara.
    texto = _texto_conforme()
    divergencias: list[str] = []
    for eje in EJES:
        tabla = _tabla_de_seccion(texto, SLUGS_DE_EJE[eje])
        if tabla is None:
            divergencias.append(f"{eje}: el fixture no declara su sección")
            continue
        declarado = tuple(
            (_partir_namespace(_clave_de_fila(f))[1], _celda_de(tabla, f, "tipo"),
             _celda_de(tabla, f, "sede"))
            for f in tabla.filas)
        esperado = tuple((l.literal, l.tipo, l.sede) for l in INVENTARIO_DE_EJES[eje])
        if sorted(declarado) != sorted(esperado):
            divergencias.append(f"{eje}: {sorted(set(declarado) ^ set(esperado))}")
    resultados.append((
        "0.fixture", not divergencias,
        "el fixture conforme declara exactamente el inventario congelado, literal por literal"
        if not divergencias else "el fixture divergió: " + " | ".join(divergencias[:3])))
    return resultados


def _bloque_del_compartido() -> list[tuple[str, bool, str]]:
    """[E] Lo que separa «acepta un literal compartido» de «no mira las repeticiones».

    No alcanza con que el conforme pase: hay que **mostrar** que el literal está en dos ejes y que
    volver idénticas las dos declaraciones lo pone rojo. Sin la segunda dirección, el verde del
    conforme sería compatible con un modo que ignorara la dimensión entera."""
    ciclo, _, semantico = EJES
    texto = _texto_conforme()
    en_ambos = [eje for eje in (ciclo, semantico)
                if any(l.literal == "done" for l in INVENTARIO_DE_EJES[eje])]
    problemas_conforme, resumen = verificar_ejes(texto, REPO)

    fusionado = _componer(
        _mutar_celda(SLUGS_DE_EJE[semantico], f"{semantico}.done", "tipo", "marcador_de_cierre"),
        _mutar_celda(SLUGS_DE_EJE[semantico], f"{semantico}.done", "sede",
                     "`skills/co-explore/reference.md#senal-de-finalizacion`"))(texto)
    problemas_fusion, _ = verificar_ejes(fusionado, REPO)
    codigos = {p.codigo for p in problemas_fusion}

    return [
        ("E1/ejes", len(en_ambos) == 2 and resumen["compartidos"] >= 1,
         f"`done` está declarado en {' y '.join('`' + e + '`' for e in en_ambos)} y el modo lo "
         f"cuenta como compartido ({resumen['compartidos']})"
         if len(en_ambos) == 2 and resumen["compartidos"] >= 1 else
         f"el literal compartido no está en los dos ejes: {en_ambos}"),
        ("E2/ejes", not problemas_conforme,
         "y con tipo, sede y significado distintos el modo lo acepta: un literal repetido no es una "
         "fusión"
         if not problemas_conforme else
         f"el conforme con el literal compartido falló: {problemas_conforme[0]}"),
        ("E3/ejes", codigos == {"compartido_sin_distincion"},
         "y al volver idénticas las dos declaraciones se pone rojo, y solo por eso"
         if codigos == {"compartido_sin_distincion"} else
         f"la fusión del compartido emitió {sorted(codigos)}"),
    ]


def modo_autotest_ejes() -> int:
    resultados = _preludio_de_ejes()
    if all(ok for _, ok, _ in resultados):
        resultados += _bloque_de_documento(
            "ejes", _casos_de_ejes(), _correr_caso_de_ejes, CODIGOS_EJES,
            # Los tres ejes leídos, **todos** sus literales con la sede resuelta, y el compartido
            # contado. Sin el primer término, un modo que no leyera nada dejaría `0 == 0` y pasaría
            # el control positivo sin haber resuelto un solo puntero.
            lambda r: (f"leyó {r['ejes']} de {len(EJES)} ejes y {r['literales']} literales: no "
                       "recorrió el documento"
                       if r["ejes"] != len(EJES) or not r["literales"] else
                       f"resolvió {r['sedes_resueltas']} de {r['literales']} sedes contra el árbol"
                       if r["sedes_resueltas"] != r["literales"] else
                       "no contó ningún literal compartido" if not r["compartidos"] else ""))
        resultados += _bloque_del_compartido()
        resultados += _bloque_de_ausencia("ejes", lambda ruta: modo_ejes(ruta, REPO))
    return _cierre("los tres ejes se comparan por igualdad exacta contra un inventario cuyos "
                   "dieciséis literales salen de sedes reales de `skills/`", resultados)


def _preludio_de_capacidades() -> list[tuple[str, bool, str]]:
    """El fixture tiene que traer **varias afirmaciones válidas y las tres marcas**: con un fixture
    de una sola afirmación, los mutantes unitarios dejarían de serlo y un verificador que
    comprobara que existe *alguna* marca los pasaría a todos."""
    resultados = _preludio_del_corpus()
    if not all(ok for _, ok, _ in resultados):
        return resultados
    tabla = _tabla_de_seccion(_texto_conforme(), SLUG_CAPACIDADES)
    if tabla is None:
        return resultados + [("0.capacidades", False,
                              f"el fixture no declara la sección `{SLUG_CAPACIDADES}`")]
    marcas = [_celda_de(tabla, f, "marca") for f in tabla.filas]
    faltan = [m for m in MARCAS_DE_CAPACIDAD if m not in marcas]
    suficientes = len(tabla.filas) >= 4 and not faltan
    resultados.append((
        "0.capacidades", suficientes,
        f"el fixture trae {len(tabla.filas)} afirmaciones y ejerce las "
        f"{len(MARCAS_DE_CAPACIDAD)} marcas, así que un defecto en una convive con las demás válidas"
        if suficientes else
        f"el fixture no alcanza: {len(tabla.filas)} filas y sin ejercer {faltan}"))
    return resultados


def _bloque_unitario_de_capacidades(casos: tuple[CasoDeContrato, ...]) -> list[tuple[str, bool, str]]:
    """[E] Los mutantes de fila son **unitarios de verdad**, y no solo por descripción.

    Que un mutante dé rojo no alcanza para probar el cuantificador: si además rompiera las otras
    afirmaciones, el rojo sería compatible con un verificador que solo mirase si existe *alguna*
    marca. Las dos mitades: exactamente un problema, y las demás afirmaciones siguen marcadas."""
    unitarios = [c for c in casos if c.codigo in CODIGOS_UNITARIOS_DE_CAPACIDAD]
    fallas: list[str] = []
    minimo = 0
    for caso in unitarios:
        try:
            problemas, resumen = _correr_caso_de_capacidades(caso)
        except ValueError as exc:
            fallas.append(f"{caso.codigo} — no corrió: {exc}")
            continue
        sanas = resumen["afirmaciones"] - 1
        minimo = max(minimo, sanas)
        if len(problemas) != 1:
            fallas.append(f"{caso.codigo} — emitió {len(problemas)} problemas y no uno: "
                          f"{sorted({p.codigo for p in problemas})}")
        elif resumen["marcadas"] < sanas:
            fallas.append(f"{caso.codigo} — quedaron {resumen['marcadas']} afirmaciones marcadas de "
                          f"{sanas} sanas: el defecto no fue unitario")
    return [("E/capacidades", not fallas,
             f"los {len(unitarios)} mutantes de fila son unitarios: uno solo cae y las otras "
             f"{minimo} afirmaciones siguen válidas y marcadas"
             if not fallas else f"{len(fallas)} problemas: " + " | ".join(fallas[:3]))]


def modo_autotest_capacidades() -> int:
    resultados = _preludio_de_capacidades()
    if all(ok for _, ok, _ in resultados):
        resultados += _bloque_de_documento(
            "capacidades", _casos_de_capacidades(), _correr_caso_de_capacidades,
            CODIGOS_CAPACIDADES,
            lambda r: (f"leyó {r['afirmaciones']} afirmaciones: no recorrió la tabla"
                       if not r["afirmaciones"] else
                       f"marcó {r['marcadas']} de {r['afirmaciones']} afirmaciones"
                       if r["marcadas"] != r["afirmaciones"] else
                       "no ejerció las tres marcas"
                       if not (r["portables"] and r["dependientes"] and r["no_verificables"])
                       else ""))
        resultados += _bloque_unitario_de_capacidades(_casos_de_capacidades())
        resultados += _bloque_de_ausencia("capacidades", modo_capacidades)
    return _cierre("toda afirmación de plataforma va marcada portable, dependiente con su versión "
                   "comprobada o no verificable con su motivo", resultados)


# =============================================================================================
# El perfil de ejecución, las cinco familias de rol, la diversidad y los defectos.
#
# Cinco modos de aplicación y sus cinco autotests. Comparten con los tres modos de contrato el
# documento —el mismo `RUTA_CONTRATO`, el mismo corpus sintético, el mismo `CODIGO_DOCUMENTO_AUSENTE`
# cuando no existe— y el mismo esqueleto de autotest: `[A]` control positivo, `[B]` un mutante por
# defecto rechazado por su motivo, `[C]` un caso por código, `[D]` la ausencia en las dos
# direcciones.
#
# **Lo que declaran sus secciones va en bloques `json` cercados y no en tablas**, al revés que las
# tres secciones de contrato. El motivo es la forma del dato y no el gusto: un contenedor de perfiles
# es un árbol de tres niveles, una procedencia anclada tiene siete campos y un escenario de
# precedencia lleva adentro una superficie de configuración entera. Aplanar eso en celdas obligaría a
# inventar una gramática de celda —separadores, escapes, sub-claves— que ya existe y se llama JSON.
# =============================================================================================

SLUG_PERFIL_SCHEMA = "schema-del-perfil-de-ejecucion"
SLUG_PERFIL_PRECEDENCIA = "precedencia-del-perfil-de-ejecucion"
SLUG_FAMILIAS = "familias-de-rol"
SLUG_ASIGNACIONES = "asignaciones-de-despacho"
SLUG_DIVERSIDAD = "politica-de-diversidad"
SLUG_DEFECTOS = "inventario-de-defectos"

# La sede de la que salen las cinco familias de rol. **Es lo único de esta task que se deriva de una
# fuente**: el resto —el mapa punto → variante, los seis defectos— son decisiones, y su defensa es
# estar escritas, no estar apuntadas.
SEDE_DE_LAS_FAMILIAS = ("docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md"
                        "#1-que-significa-soportado-por-las-siete-skills")

FAMILIAS_DE_ROL = ("explorer", "investigator", "design-reviewer", "bounded-implementer",
                   "diff-reviewer")

CAMPOS_DE_FAMILIA = ("entrada", "salida", "scope")

# Los cuatro estados que AC-13 declara. Los dos primeros exigen ancla y valor; `ausente` exige motivo
# y **no** lleva puntero; `propuesto` exige la fase que lo va a tomar.
ESTADOS_ANCLADOS = ("vigente", "observado")
ESTADOS_DE_CAMPO = ESTADOS_ANCLADOS + ("ausente", "propuesto")

PROCEDENCIAS_DE_ASIGNACION = ("puntero", "decision")


class Asignacion(NamedTuple):
    """Una fila del mapa punto → familia → variante."""

    punto: str
    familia: str
    variante: str
    procedencia: str


# ---------------------------------------------------------------------------------------------
# EL MAPA DE LAS TRECE ASIGNACIONES
#
# **Congelar un inventario lo vuelve falso cuando el inventario es derivable; este no lo es.** Las
# cinco familias salen de la tabla del roadmap y por eso no se transcriben: se apuntan. El mapa punto
# → variante **no está en ninguna fuente**. Medido: esa tabla tiene siete filas, una por skill, con
# 13 puntos y 12 menciones de rol, y en tres skills no cuadran —`co-explore` enumera 2 puntos y 3
# roles, `sdd-flow` 4 y 3, `bitbucket-code-review` 2 y 1—. Mapea *skill → roles reusables*, no *punto
# → variante*: construirlo es decidir.
#
# La decisión está tomada y escrita, y esto es su transcripción. Cinco de las trece filas admitían
# más de una respuesta defendible con el mismo criterio, así que dejar el criterio y no el mapa no
# alcanzaba: dos agentes frescos habrían producido dos repartos distintos y los dos habrían cerrado
# su fila.
#
# Las ocho filas marcadas `puntero` llevan además la carga de la prueba: el roadmap **nombra** su
# variante, y el modo resuelve el puntero contra el árbol real y exige encontrarla ahí. Las cinco
# marcadas `decision` no tienen dónde apuntar, y por eso llevan justificación escrita.
# ---------------------------------------------------------------------------------------------

MAPA_DE_ASIGNACIONES: tuple[Asignacion, ...] = (
    Asignacion("co-explore · fan-out dual", "explorer / investigator",
               "fan-out en modos explore y counter-plan; root-cause en modo investigate",
               "decision"),
    Asignacion("co-explore · debate", "design-reviewer", "decision-debate", "puntero"),
    Asignacion("cross-review · revisor por ronda", "design-reviewer", "artifact-review", "puntero"),
    Asignacion("cross-implement · implementador inicial", "bounded-implementer", "work-order",
               "puntero"),
    Asignacion("cross-implement · fix loop", "bounded-implementer", "fix-round", "decision"),
    Asignacion("sdd-flow · analyze", "explorer", "codebase-survey", "decision"),
    Asignacion("sdd-flow · implementer por task", "bounded-implementer", "task", "puntero"),
    Asignacion("sdd-flow · reviewer por task", "diff-reviewer", "task", "decision"),
    Asignacion("sdd-flow · revisión final", "diff-reviewer", "final", "decision"),
    Asignacion("sdd-orchestrator · fan-out por repo", "bounded-implementer", "repo-runner",
               "puntero"),
    Asignacion("sdd-pr-feedback · implement delegado", "bounded-implementer", "work-order",
               "puntero"),
    Asignacion("bitbucket-code-review · panel", "diff-reviewer", "review", "puntero"),
    Asignacion("bitbucket-code-review · validador adversarial", "diff-reviewer", "refute",
               "puntero"),
)


class DefectoMinimo(NamedTuple):
    identidad: str
    descripcion: str


# ---------------------------------------------------------------------------------------------
# LOS SEIS DEFECTOS MÍNIMOS
#
# Transcritos del criterio que los enumera, uno por uno. **La comparación es por identidad y no por
# cantidad:** `len(defectos) >= 6` satisface todo lo que se declara acá y a la vez acepta un
# inventario que cambió uno de los seis por otro. Puede contener más —el mínimo no es un conjunto
# cerrado— y no menos.
#
# Su ubicación, su naturaleza y su fase **no** se congelan: adjudicar dónde vive cada defecto es de
# la task que materializa el inventario, y fijarlas acá le impondría una adjudicación que su task no
# tomó. Lo que este modo exige de esos tres campos es que estén y tengan forma.
# ---------------------------------------------------------------------------------------------

DEFECTOS_MINIMOS: tuple[DefectoMinimo, ...] = (
    DefectoMinimo("instruccion-del-repositorio-contra-guarda",
                  "la instrucción del repositorio que contradice el estado de una guarda"),
    DefectoMinimo("conteo-de-skills-del-manifest",
                  "la discrepancia entre el número declarado de skills del manifest y su tabla"),
    DefectoMinimo("frontera-que-nombra-skill-inexistente",
                  "la regla de fronteras que nombra una skill inexistente"),
    DefectoMinimo("registro-historico-rechazado-por-su-guarda",
                  "los archivos del registro histórico que su propia guarda rechaza"),
    DefectoMinimo("familia-dura-con-override-explicito",
                  "la regla de familia declarada dura que a la vez admite override explícito"),
    DefectoMinimo("sede-del-fan-out-vs-prompt",
                  "la divergencia entre la sede del fan-out por repo y el prompt con que ese "
                  "fan-out despacha"),
)

CAMPOS_DE_DEFECTO = ("ubicacion", "naturaleza", "fase")

# Una ubicación es un puntero: ruta relativa, con fragmento o sin él. No se resuelve contra el árbol
# —ver arriba—, pero «documental» o «en el README» no son ubicaciones.
PATRON_UBICACION = re.compile(r"^[A-Za-z0-9._][A-Za-z0-9._/-]*(#[A-Za-z0-9._-]+)?$")

FAMILIAS_DE_MODELO = ("claude", "codex")

RELACIONES = ("cross_family", "same_family")

# Las dos causas de ausencia legítima que AC-11 distingue. **Van por separado y las dos son
# obligatorias**: los dos resuelven al default portable, y un solo caso los confundiría — no es lo
# mismo un punto sin asignación habiendo superficie que un punto sin superficie alguna.
CAUSAS_DE_AUSENCIA_LEGITIMA = ("sin_asignacion_para_el_rol", "sin_superficie_de_configuracion")

CAUSAS_DE_INVALIDEZ = ("asignacion_a_perfil_inexistente", "referencia_rota", "perfil_sin_uso")

CLASES_DE_RESOLUCION = ("resuelto", "invalido")


CODIGOS_PERFIL_SCHEMA = (
    "asignacion_no_escalar",
    "asignaciones_vacias",
    "bloque_ilegible",
    "clave_raiz_ausente",
    "componente_ausente",
    "default_no_escalar",
    "familia_desconocida",
    "parametro_ausente",
    "parametro_no_admitido",
    "parametros_no_objeto",
    "perfil_no_objeto",
    "perfil_sin_familias",
    "perfiles_vacios",
    "schema_ausente",
)

CODIGOS_PERFIL_PRECEDENCIA = (
    "bloque_ilegible",
    "causa_desconocida",
    "clase_desconocida",
    "default_portable_ausente",
    "escenario_de_ausencia_faltante",
    "escenario_id_duplicado",
    "escenario_no_objeto",
    "escenario_sin_resolucion",
    "escenario_sin_rol",
    "escenarios_ausentes",
    "nivel_desconocido",
    "nivel_duplicado",
    "niveles_ausentes",
    "precedencia_ausente",
    "resolucion_no_coincide",
    "superficie_no_objeto",
)

CODIGOS_ROLES = (
    "asignacion_de_mas",
    "asignacion_faltante",
    "asignaciones_ausentes",
    "ausente_sin_motivo",
    "autoridad_ausente",
    "autoridad_por_familia",
    "bloque_ilegible",
    "campo_ausente",
    "campo_sin_procedencia",
    "campo_sin_valor",
    "declaracion_de_salida_ausente",
    "estado_ausente",
    "estado_desconocido",
    "familia_ausente_en_la_sede",
    "familia_de_mas",
    "familia_duplicada",
    "familia_faltante",
    "familia_no_coincide",
    "familias_ausentes",
    "forma_de_resultado_ausente",
    "justificacion_ausente",
    "procedencia_en_campo_no_anclado",
    "procedencia_no_coincide",
    "procedencia_no_resuelve",
    "propuesto_sin_fase",
    "punto_duplicado",
    "puntero_de_familia_ausente",
    "puntero_de_familia_irresoluble",
    "puntero_de_variante_ausente",
    "puntero_de_variante_irresoluble",
    "salida_compartida_entre_formas_distintas",
    "valor_no_coincide",
    "variante_ausente_en_la_sede",
    "variante_no_coincide",
)

CODIGOS_DIVERSIDAD = (
    "bloque_ilegible",
    "diversidad_ausente",
    "familia_desconocida",
    "independencia_negada",
    "independencia_omitida",
    "independiente_de_una_sola_familia",
    "independiente_de_una_sola_voz",
    "intento_id_duplicado",
    "intento_no_objeto",
    "intento_sin_identidad",
    "intentos_ausentes",
    "relacion_ausente",
    "relacion_desconocida",
    "relacion_no_coincide",
    "topologia_ausente",
    "topologia_contradice_registros",
)

CODIGOS_DEFECTOS = (
    "bloque_ilegible",
    "defecto_id_duplicado",
    "defecto_minimo_faltante",
    "defecto_no_objeto",
    "defecto_sin_campo",
    "defecto_sin_identidad",
    "defectos_ausentes",
    "ubicacion_sin_forma",
)


# --- El contenedor del perfil, derivado de la lista de nombres reservados ----------------------

class ContenedorDelPerfil(NamedTuple):
    """La forma del contenedor, **derivada** de `scripts/nombres-reservados-perfil.json`.

    Esa lista es la única fuente de los nombres del contenedor y ya declara, por entrada, a qué
    componente pertenece y en qué ruta vive. Transcribir acá `subagents`, `profiles`, `model` o
    `reasoning` daría dos listas que pueden divergir, y la que envejeciera sería justo la que decide
    qué se acepta."""

    clave_raiz: str
    rutas: dict[str, tuple[str, ...]]      # componente → rutas declaradas
    familias: tuple[str, ...]              # los nombres de familia que la lista declara
    parametros: tuple[str, ...]            # la lista blanca del objeto de parámetros
    error: str = ""

    @property
    def obligatorios(self) -> tuple[str, ...]:
        """Los cinco componentes del contenedor: todo lo que declara la lista menos el contenedor
        mismo —que es la clave raíz, no un componente adentro— y menos los parámetros de runtime,
        que son el nivel **interior** y el único con lista blanca."""
        return tuple(c for c in COMPONENTES_DEL_CONTENEDOR
                     if c not in ("contenedor", "parametro_de_runtime") and c in self.rutas)

    def rutas_exigidas(self, componente: str) -> tuple[tuple[str, ...], ...]:
        """Las rutas **más profundas** que declaran ese componente. `asignaciones_por_rol` aparece
        dos veces —`subagents.bindings` y `subagents.bindings.roles`— y la que hay que exigir es la
        de adentro, porque un `bindings` vacío satisface la de afuera. `familias` aparece dos veces
        a la misma profundidad —una por familia— y ahí son alternativas: alcanza con que una llegue.
        """
        candidatas = [tuple(r.split(".")) for r in self.rutas.get(componente, ())]
        if not candidatas:
            return ()
        hondura = max(len(r) for r in candidatas)
        return tuple(r for r in candidatas if len(r) == hondura)

    def ruta_de(self, componente: str) -> tuple[str, ...]:
        """La primera de las rutas exigidas. La consumen los recorridos que necesitan **una**:
        perfiles, asignaciones y valor por defecto tienen exactamente una a su profundidad."""
        rutas = self.rutas_exigidas(componente)
        return rutas[0] if rutas else ()


_contenedor_cache: ContenedorDelPerfil | None = None


def contenedor_del_perfil() -> ContenedorDelPerfil:
    global _contenedor_cache
    if _contenedor_cache is not None:
        return _contenedor_cache
    datos, error = _cargar_json(RUTA_NOMBRES_RESERVADOS)
    if error:
        _contenedor_cache = ContenedorDelPerfil("", {}, (), (), error)
        return _contenedor_cache
    rutas: dict[str, list[str]] = {}
    nombres: dict[str, list[str]] = {}
    for _, _, entrada in _entradas_de(datos):
        componente, ruta, nombre = (entrada.get("componente"), entrada.get("ruta"),
                                    entrada.get("nombre"))
        if not isinstance(componente, str) or not isinstance(ruta, str):
            continue
        rutas.setdefault(componente, []).append(ruta)
        if isinstance(nombre, str):
            nombres.setdefault(componente, []).append(nombre)
    _contenedor_cache = ContenedorDelPerfil(
        clave_raiz=str(datos.get("clave_raiz") or ""),
        rutas={c: tuple(v) for c, v in rutas.items()},
        familias=tuple(sorted(set(nombres.get("familias", ())))),
        parametros=tuple(sorted(set(nombres.get("parametro_de_runtime", ())))),
    )
    return _contenedor_cache


def _navegar(nodo: Any, ruta: list[str] | tuple[str, ...]) -> list[tuple[str, Any]]:
    """Todo (ruta concreta, valor) que la ruta alcanza. Un tramo `<x>` es comodín y se expande sobre
    las claves que haya: `subagents.profiles.<perfil>.<familia>.model` no nombra perfiles, los
    recorre."""
    alcanzados: list[tuple[str, Any]] = [("", nodo)]
    for tramo in ruta:
        siguiente: list[tuple[str, Any]] = []
        for camino, valor in alcanzados:
            if not isinstance(valor, dict):
                continue
            claves = list(valor) if PATRON_COMODIN.match(tramo) else (
                [tramo] if tramo in valor else [])
            for clave in claves:
                siguiente.append((f"{camino}.{clave}" if camino else clave, valor[clave]))
        alcanzados = siguiente
    return alcanzados


# --- Lectura de los bloques estructurados -----------------------------------------------------

def _bloque_json(texto: str, slug: str) -> tuple[Any, str]:
    """El primer bloque `json` cercado de la sección, ya parseado. `("", ...)` es un dato válido; el
    segundo miembro es el motivo cuando no hay dato."""
    rangos = _rangos_de_secciones(texto)
    if slug not in rangos:
        return None, f"el documento no declara la sección `{slug}`"
    inicio, fin = rangos[slug]
    for cuerpo, apertura in _bloques_cercados(texto, "json"):
        if not inicio <= apertura <= fin:
            continue
        try:
            return json.loads(cuerpo), ""
        except json.JSONDecodeError as exc:
            return None, f"el bloque `json` de `{slug}` no parsea: {exc}"
    return None, f"la sección `{slug}` no tiene ningún bloque `json` cercado"


def _rango_del_bloque(texto: str, slug: str) -> tuple[int, int] | None:
    """(primera, última) línea del **contenido** del bloque, sin sus fences. Lo consume el autotest
    para reescribirlo después de mutarlo."""
    rangos = _rangos_de_secciones(texto)
    if slug not in rangos:
        return None
    inicio, fin = rangos[slug]
    for cuerpo, apertura in _bloques_cercados(texto, "json"):
        if inicio <= apertura <= fin:
            return apertura + 1, apertura + len(cuerpo.split("\n"))
    return None


def _texto_o_vacio(valor: Any) -> str:
    return valor.strip() if isinstance(valor, str) else ""

# --- Modo `--perfil-schema` -------------------------------------------------------------------

def verificar_perfil_schema(texto: str) -> tuple[list[Problema], dict]:
    """El contenedor completo, y la lista blanca **solo** sobre el objeto de parámetros.

    Son dos niveles y confundirlos invierte el criterio. Si la lista blanca se aplicara al
    contenedor, sus cinco componentes —que no son `model` ni `reasoning`— quedarían rechazados y un
    agente fresco los omitiría para pasar. Si en cambio el objeto de parámetros enumerara lo
    prohibido en vez de cerrar lo admitido, entraría todo lo que nadie pensó en prohibir: por eso el
    tercer parámetro de runtime, que no altera herramientas ni permisos ni nada de las cinco clases,
    también tiene que caer."""
    problemas: list[Problema] = []
    resumen = {"componentes": 0, "perfiles": 0, "objetos_de_parametros": 0, "asignaciones": 0,
               "parametros": 0}
    contenedor = contenedor_del_perfil()
    if contenedor.error:
        return [Problema("bloque_ilegible", "$",
                         f"no se pudo derivar la forma del contenedor: {contenedor.error}")], resumen

    datos, motivo = _bloque_json(texto, SLUG_PERFIL_SCHEMA)
    if motivo:
        return [Problema("schema_ausente", f"sección `{SLUG_PERFIL_SCHEMA}`", motivo)], resumen
    if not isinstance(datos, dict):
        return [Problema("bloque_ilegible", f"sección `{SLUG_PERFIL_SCHEMA}`",
                         f"el bloque declara `{_nombre_tipo(datos)}` y no un objeto")], resumen
    if contenedor.clave_raiz not in datos:
        return [Problema("clave_raiz_ausente", f"sección `{SLUG_PERFIL_SCHEMA}`",
                         f"el schema no cuelga de `{contenedor.clave_raiz}`, que es la clave raíz "
                         "que la lista de nombres reservados declara")], resumen

    for componente in contenedor.obligatorios:
        rutas = contenedor.rutas_exigidas(componente)
        if any(_navegar(datos, r) for r in rutas):
            resumen["componentes"] += 1
            continue
        problemas.append(Problema(
            "componente_ausente", f"componente `{componente}`",
            f"el contenedor no declara {' ni '.join('`' + '.'.join(r) + '`' for r in rutas)}; el "
            "contenedor **completo** es obligatorio, y la lista blanca gobierna el objeto de "
            "parámetros de cada perfil, que es otro nivel"))

    perfiles = dict(_navegar(datos, contenedor.ruta_de("perfiles_nombrados")))
    mapa_de_perfiles = next(iter(perfiles.values()), None)
    if isinstance(mapa_de_perfiles, dict) and not mapa_de_perfiles:
        problemas.append(Problema(
            "perfiles_vacios", "perfiles nombrados",
            "el mapa de perfiles existe y no declara ninguno: un contenedor sin perfiles satisface "
            "«todo perfil entrega solo modelo y esfuerzo» por vacuidad"))
    if isinstance(mapa_de_perfiles, dict):
        resumen["perfiles"] = len(mapa_de_perfiles)
        for nombre, perfil in mapa_de_perfiles.items():
            if not isinstance(perfil, dict):
                problemas.append(Problema("perfil_no_objeto", f"perfil `{nombre}`",
                                          f"declara `{_nombre_tipo(perfil)}` y no un objeto de "
                                          "familias"))
                continue
            if not perfil:
                problemas.append(Problema("perfil_sin_familias", f"perfil `{nombre}`",
                                          "no declara ninguna familia, así que no entrega "
                                          "parámetros a ningún runtime"))
                continue
            for familia, parametros in perfil.items():
                donde = f"perfil `{nombre}`, familia `{familia}`"
                if familia not in contenedor.familias:
                    problemas.append(Problema(
                        "familia_desconocida", donde,
                        f"`{familia}` no es una de las familias que la lista declara "
                        f"({', '.join('`' + f + '`' for f in contenedor.familias)})"))
                    continue
                if not isinstance(parametros, dict):
                    problemas.append(Problema("parametros_no_objeto", donde,
                                              f"los parámetros llegaron como "
                                              f"`{_nombre_tipo(parametros)}`"))
                    continue
                resumen["objetos_de_parametros"] += 1
                for clave in parametros:
                    if clave in contenedor.parametros:
                        resumen["parametros"] += 1
                        continue
                    problemas.append(Problema(
                        "parametro_no_admitido", donde,
                        f"`{clave}` no está en la lista blanca del objeto de parámetros, que admite "
                        f"exclusivamente {', '.join('`' + p + '`' for p in contenedor.parametros)}. "
                        "La lista es cerrada y no una lista de prohibidos: enumerar lo prohibido "
                        "deja entrar todo lo que nadie pensó en prohibir"))
                for esperado in contenedor.parametros:
                    if esperado not in parametros:
                        problemas.append(Problema(
                            "parametro_ausente", donde,
                            f"no entrega `{esperado}`, que es uno de los dos parámetros que un "
                            "perfil sí puede entregar al runtime"))

    for camino, valor in _navegar(datos, contenedor.ruta_de("valor_por_defecto")):
        if not isinstance(valor, str) or not valor:
            problemas.append(Problema(
                "default_no_escalar", f"`{camino}`",
                f"el valor por defecto llegó como `{_nombre_tipo(valor)}`: nombra un perfil, no lo "
                "redefine"))

    asignaciones = dict(_navegar(datos, contenedor.ruta_de("asignaciones_por_rol")))
    mapa_de_roles = next(iter(asignaciones.values()), None)
    if isinstance(mapa_de_roles, dict):
        resumen["asignaciones"] = len(mapa_de_roles)
        if not mapa_de_roles:
            problemas.append(Problema(
                "asignaciones_vacias", "asignaciones por rol",
                "el mapa de rol a perfil existe y está vacío: sin ninguna asignación, la precedencia "
                "no tiene nada que resolver y el contenedor no cumple su función"))
        for rol, elegido in mapa_de_roles.items():
            if isinstance(elegido, str) and elegido:
                continue
            problemas.append(Problema(
                "asignacion_no_escalar", f"asignación del rol `{rol}`",
                f"declara `{_nombre_tipo(elegido)}` en vez del nombre de un perfil. Una asignación "
                "puede **seleccionar** qué perfil se resuelve; no transporta herramientas, "
                "aislamiento, permisos, contrato de salida ni autoridad"))
    return problemas, resumen


# --- Modo `--perfil-precedencia` --------------------------------------------------------------

def _perfiles_de(superficie: dict, contenedor: ContenedorDelPerfil) -> dict:
    mapa = next((v for _, v in _navegar(superficie, contenedor.ruta_de("perfiles_nombrados"))), {})
    return mapa if isinstance(mapa, dict) else {}


def _roles_de(superficie: dict, contenedor: ContenedorDelPerfil) -> dict:
    mapa = next((v for _, v in _navegar(superficie, contenedor.ruta_de("asignaciones_por_rol"))), {})
    return mapa if isinstance(mapa, dict) else {}


def _default_de(superficie: dict, contenedor: ContenedorDelPerfil) -> Any:
    return next((v for _, v in _navegar(superficie, contenedor.ruta_de("valor_por_defecto"))), None)


def resolver_precedencia(escenario: dict, default_portable: str,
                         contenedor: ContenedorDelPerfil) -> dict:
    """Ejecuta la precedencia sobre un escenario y devuelve la resolución **derivada**.

    Es lo que separa una precedencia declarada de una precedencia que se puede correr: el escenario
    trae la superficie de configuración entera y este resolutor la recorre nivel por nivel, en vez de
    creerle al documento lo que resolvería.

    Los tres inválidos van **antes** que cualquier nivel: un perfil sin uso, una asignación a un
    perfil inexistente y una referencia rota fallan cerrado, no se ignoran. La ausencia legítima —de
    asignación o de superficie— cae al default portable, y las dos causas se distinguen: no es lo
    mismo no tener asignación habiendo superficie que no tener superficie."""
    rol = _texto_o_vacio(escenario.get("rol"))
    override = escenario.get("override")
    superficie = escenario.get("superficie")

    if superficie is None:
        return {"clase": "resuelto", "perfil": default_portable,
                "nivel": "perfil_default_portable",
                "causa": "sin_superficie_de_configuracion"}

    perfiles = _perfiles_de(superficie, contenedor)
    roles = _roles_de(superficie, contenedor)
    defecto = _default_de(superficie, contenedor)

    huerfanos = set(perfiles)
    for elegido in roles.values():
        if isinstance(elegido, str) and elegido not in perfiles:
            return {"clase": "invalido", "causa": "asignacion_a_perfil_inexistente"}
        huerfanos.discard(elegido)
    if isinstance(defecto, str):
        if defecto not in perfiles:
            return {"clase": "invalido", "causa": "referencia_rota"}
        huerfanos.discard(defecto)
    if isinstance(override, str):
        huerfanos.discard(override)
    if huerfanos:
        return {"clase": "invalido", "causa": "perfil_sin_uso"}

    if isinstance(override, str) and override:
        if override not in perfiles:
            return {"clase": "invalido", "causa": "referencia_rota"}
        return {"clase": "resuelto", "perfil": override,
                "nivel": "override_explicito_del_usuario"}
    if rol in roles:
        return {"clase": "resuelto", "perfil": roles[rol],
                "nivel": "asignacion_por_rol_de_la_superficie"}
    if isinstance(defecto, str) and defecto:
        return {"clase": "resuelto", "perfil": defecto,
                "nivel": "valor_por_defecto_de_la_superficie"}
    return {"clase": "resuelto", "perfil": default_portable, "nivel": "perfil_default_portable",
            "causa": "sin_asignacion_para_el_rol"}


def verificar_perfil_precedencia(texto: str) -> tuple[list[Problema], dict]:
    problemas: list[Problema] = []
    resumen = {"escenarios": 0, "evaluados": 0, "invalidos": 0, "ausencias_legitimas": 0,
               "causas_de_ausencia": 0, "niveles": 0}
    contenedor = contenedor_del_perfil()
    if contenedor.error:
        return [Problema("bloque_ilegible", "$", contenedor.error)], resumen

    datos, motivo = _bloque_json(texto, SLUG_PERFIL_PRECEDENCIA)
    if motivo:
        return [Problema("precedencia_ausente", f"sección `{SLUG_PERFIL_PRECEDENCIA}`",
                         motivo)], resumen
    if not isinstance(datos, dict):
        return [Problema("bloque_ilegible", f"sección `{SLUG_PERFIL_PRECEDENCIA}`",
                         f"el bloque declara `{_nombre_tipo(datos)}` y no un objeto")], resumen

    niveles = datos.get("niveles")
    if not isinstance(niveles, list) or not niveles:
        problemas.append(Problema(
            "niveles_ausentes", "precedencia",
            "no declara sus niveles en orden; sin ellos, «resuelve por precedencia» no dice por cuál"))
        niveles = []
    resumen["niveles"] = len(niveles)
    for nivel in sorted({n for n in niveles if niveles.count(n) > 1}):
        problemas.append(Problema("nivel_duplicado", "precedencia",
                                  f"`{nivel}` aparece más de una vez en el orden"))

    default_portable = _texto_o_vacio(datos.get("default_portable"))
    if not default_portable:
        problemas.append(Problema(
            "default_portable_ausente", "precedencia",
            "no declara el perfil por defecto portable, que es a donde caen las dos ausencias "
            "legítimas"))

    escenarios = datos.get("escenarios")
    if not isinstance(escenarios, list) or not escenarios:
        problemas.append(Problema(
            "escenarios_ausentes", "precedencia",
            "no declara ningún escenario: una precedencia sin corpus contra el que correr es prosa"))
        return problemas, resumen
    resumen["escenarios"] = len(escenarios)

    vistos: set[str] = set()
    causas_vistas: set[str] = set()
    for i, escenario in enumerate(escenarios):
        if not isinstance(escenario, dict):
            problemas.append(Problema("escenario_no_objeto", f"escenario {i + 1}",
                                      f"llegó como `{_nombre_tipo(escenario)}`"))
            continue
        ident = _texto_o_vacio(escenario.get("id")) or f"(sin id, {i + 1})"
        donde = f"escenario `{ident}`"
        if ident in vistos:
            problemas.append(Problema("escenario_id_duplicado", donde,
                                      "otro escenario ya usa ese identificador"))
        vistos.add(ident)
        if not _texto_o_vacio(escenario.get("rol")):
            problemas.append(Problema("escenario_sin_rol", donde,
                                      "no dice para qué rol se resuelve el perfil"))
            continue
        superficie = escenario.get("superficie")
        if superficie is not None and not isinstance(superficie, dict):
            problemas.append(Problema("superficie_no_objeto", donde,
                                      f"la superficie llegó como `{_nombre_tipo(superficie)}`; "
                                      "`null` es «no hay superficie» y es otra cosa"))
            continue
        esperada = escenario.get("resolucion_esperada")
        if not isinstance(esperada, dict) or not esperada:
            problemas.append(Problema("escenario_sin_resolucion", donde,
                                      "no declara qué tiene que resolver, así que no hay nada que "
                                      "cotejar contra lo que la precedencia produce"))
            continue
        clase = _texto_o_vacio(esperada.get("clase"))
        if clase not in CLASES_DE_RESOLUCION:
            problemas.append(Problema(
                "clase_desconocida", donde,
                f"`{clase or '(vacía)'}` no es una clase de resolución; el vocabulario es "
                f"{', '.join('`' + c + '`' for c in CLASES_DE_RESOLUCION)}"))
            continue
        causa = _texto_o_vacio(esperada.get("causa"))
        if causa and causa not in CAUSAS_DE_AUSENCIA_LEGITIMA + CAUSAS_DE_INVALIDEZ:
            problemas.append(Problema("causa_desconocida", donde,
                                      f"`{causa}` no es ninguna de las causas declaradas"))
            continue
        nivel = _texto_o_vacio(esperada.get("nivel"))
        if nivel and niveles and nivel not in niveles:
            problemas.append(Problema("nivel_desconocido", donde,
                                      f"resuelve en el nivel `{nivel}`, que no está entre los que "
                                      "la precedencia declara"))
            continue

        derivada = resolver_precedencia(escenario, default_portable, contenedor)
        resumen["evaluados"] += 1
        if derivada["clase"] == "invalido":
            resumen["invalidos"] += 1
        if derivada.get("causa") in CAUSAS_DE_AUSENCIA_LEGITIMA:
            resumen["ausencias_legitimas"] += 1
            causas_vistas.add(derivada["causa"])
        if derivada != esperada:
            problemas.append(Problema(
                "resolucion_no_coincide", donde,
                f"la precedencia resuelve {derivada} y el documento declara {esperada}"))

    resumen["causas_de_ausencia"] = len(causas_vistas & set(CAUSAS_DE_AUSENCIA_LEGITIMA))
    for causa in CAUSAS_DE_AUSENCIA_LEGITIMA:
        if causa in causas_vistas:
            continue
        problemas.append(Problema(
            "escenario_de_ausencia_faltante", "precedencia",
            f"ningún escenario ejerce la ausencia legítima por `{causa}`. Las dos van por separado: "
            "un punto sin asignación habiendo superficie y un punto sin superficie alguna resuelven "
            "los dos al default portable por caminos distintos, y un solo caso los confunde"))
    return problemas, resumen

# --- Modo `--roles` ---------------------------------------------------------------------------

def _resolver_puntero(puntero: str, literal: str, arbol: Path) -> str:
    """`""` si el puntero resuelve y el literal aparece en la sección que señala; si no, el motivo.

    Reusa el resolutor de anclas de los ejes en vez de escribir otro: dos resoluciones distintas
    harían que un puntero valiera acá y no allá."""
    return _resolver_sede_de_eje(puntero, literal, arbol)


def _verificar_campo(campo: Any, donde: str, raiz: Path, problemas: list[Problema],
                     resumen: dict) -> None:
    """Un campo con estado: los vigentes y los observados van **anclados y resueltos**; los ausentes
    y los propuestos declaran por qué no.

    Los anclados pasan por `resolver_procedencia`, el mismo verificador semántico que las hojas de la
    matriz. No es una elección de estilo: es lo que hace que sustituir una entrada, una salida o un
    scope por otro plausible caiga. Un campo comparado contra sí mismo no puede detectar nada."""
    if not isinstance(campo, dict):
        problemas.append(Problema("estado_ausente", donde,
                                  f"el campo llegó como `{_nombre_tipo(campo)}` y no declara estado"))
        return
    estado = _texto_o_vacio(campo.get("estado"))
    if not estado:
        problemas.append(Problema("estado_ausente", donde, "no declara su estado"))
        return
    if estado not in ESTADOS_DE_CAMPO:
        problemas.append(Problema(
            "estado_desconocido", donde,
            f"`{estado}` no es un estado; el vocabulario es "
            f"{', '.join('`' + e + '`' for e in ESTADOS_DE_CAMPO)}"))
        return

    if estado not in ESTADOS_ANCLADOS:
        if "procedencia" in campo:
            problemas.append(Problema(
                "procedencia_en_campo_no_anclado", donde,
                f"se declara `{estado}` y trae procedencia: un campo que no está vigente ni "
                "observado no tiene de dónde resolverse, y anclarlo igual lo haría coincidir con "
                "una sede que no lo respalda"))
        if estado == "ausente" and not _texto_o_vacio(campo.get("motivo")):
            problemas.append(Problema("ausente_sin_motivo", donde,
                                      "se declara ausente y no dice por qué no hay sede"))
        if estado == "propuesto" and not _texto_o_vacio(campo.get("fase")):
            problemas.append(Problema("propuesto_sin_fase", donde,
                                      "se propone y no dice para qué fase; proponer sin fase es "
                                      "postergar sin plazo"))
        resumen["campos_no_anclados"] += 1
        return

    declarado = campo.get("valor")
    if not _texto_o_vacio(declarado):
        problemas.append(Problema("campo_sin_valor", donde,
                                  f"se declara `{estado}` y no dice cuál es el valor que está "
                                  "vigente"))
    procedencia = campo.get("procedencia")
    if not isinstance(procedencia, dict) or "ausencia" in procedencia or "sede" not in procedencia:
        problemas.append(Problema(
            "campo_sin_procedencia", donde,
            f"se declara `{estado}` y no trae una procedencia anclada; un campo vigente sin sede es "
            "una afirmación sin respaldo, y la marca de ausencia no es una procedencia"))
        return
    resumen["campos_anclados"] += 1
    resultado = resolver_procedencia(procedencia, raiz)
    if not resultado.ok:
        problemas.append(Problema("procedencia_no_resuelve", donde,
                                  f"{resultado.detalle} [{resultado.error}/{resultado.causa}]"))
        return
    resumen["campos_resueltos"] += 1
    if not _mismo(declarado, resultado.valor):
        problemas.append(Problema(
            "valor_no_coincide", donde,
            f"la sede dice {resultado.valor!r} y el documento declara {declarado!r}"))


def _verificar_familias(datos: Any, raiz: Path, arbol: Path, problemas: list[Problema],
                        resumen: dict) -> None:
    if not isinstance(datos, dict) or not isinstance(datos.get("familias"), list) \
            or not datos["familias"]:
        problemas.append(Problema(
            "familias_ausentes", f"sección `{SLUG_FAMILIAS}`",
            "no declara ninguna familia de rol; una sección vacía se lee como «no hay familias», que "
            "es una afirmación distinta de no haberlas escrito"))
        return
    declaradas: dict[str, dict] = {}
    for i, fila in enumerate(datos["familias"]):
        if not isinstance(fila, dict):
            problemas.append(Problema("familias_ausentes", f"familia {i + 1}",
                                      f"la entrada llegó como `{_nombre_tipo(fila)}`"))
            continue
        nombre = _texto_o_vacio(fila.get("familia"))
        if nombre in declaradas:
            problemas.append(Problema("familia_duplicada", f"familia `{nombre}`",
                                      "se declara más de una vez"))
            continue
        declaradas[nombre] = fila

    for nombre in FAMILIAS_DE_ROL:
        if nombre not in declaradas:
            problemas.append(Problema(
                "familia_faltante", f"familia `{nombre}`",
                "el contrato no declara una de las cinco familias que el roadmap nombra"))
    for nombre in sorted(set(declaradas) - set(FAMILIAS_DE_ROL)):
        problemas.append(Problema(
            "familia_de_mas", f"familia `{nombre}`",
            "no es ninguna de las cinco: las familias se derivan de la tabla del roadmap y una "
            "sexta no tendría de dónde salir"))
    resumen["familias"] = len(set(declaradas) & set(FAMILIAS_DE_ROL))

    for nombre in FAMILIAS_DE_ROL:
        fila = declaradas.get(nombre)
        if fila is None:
            continue
        donde = f"familia `{nombre}`"
        puntero = _texto_o_vacio(fila.get("puntero"))
        if not puntero:
            problemas.append(Problema(
                "puntero_de_familia_ausente", donde,
                "no declara el puntero normativo del que sale la familia. Los mutantes impiden que "
                "el verificador sea laxo; solo el puntero impide que el inventario sea inventado"))
        else:
            motivo = _resolver_puntero(puntero, nombre, arbol)
            if motivo == "sede_irresoluble":
                problemas.append(Problema("puntero_de_familia_irresoluble", donde,
                                          f"`{puntero}` no resuelve contra el árbol"))
            elif motivo:
                problemas.append(Problema(
                    "familia_ausente_en_la_sede", donde,
                    f"`{puntero}` resuelve y no nombra a `{nombre}`: el puntero apunta a una sección "
                    "real que no dice nada de esta familia"))
            else:
                resumen["punteros_de_familia"] += 1

        campos = fila.get("campos")
        if "autoridad" in (campos if isinstance(campos, dict) else {}) or "autoridad" in fila:
            problemas.append(Problema(
                "autoridad_por_familia", donde,
                "declara su autoridad final: la autoridad va **por punto y variante**, no por "
                "familia de rol, porque dos puntos de la misma familia pueden cerrarse en manos "
                "distintas"))
        if not isinstance(campos, dict):
            problemas.append(Problema("campo_ausente", donde,
                                      f"no declara sus campos ({_nombre_tipo(campos)})"))
            continue
        for campo in CAMPOS_DE_FAMILIA:
            if campo not in campos:
                problemas.append(Problema("campo_ausente", f"{donde}, campo `{campo}`",
                                          "el contrato de la familia no lo declara"))
                continue
            _verificar_campo(campos[campo], f"{donde}, campo `{campo}`", raiz, problemas, resumen)


def _verificar_asignaciones(datos: Any, raiz: Path, arbol: Path, problemas: list[Problema],
                            resumen: dict) -> None:
    if not isinstance(datos, dict) or not isinstance(datos.get("asignaciones"), list) \
            or not datos["asignaciones"]:
        problemas.append(Problema(
            "asignaciones_ausentes", f"sección `{SLUG_ASIGNACIONES}`",
            "no declara ninguna asignación de punto a familia y variante"))
        return

    esperadas = {a.punto: a for a in MAPA_DE_ASIGNACIONES}
    declaradas: dict[str, dict] = {}
    for i, fila in enumerate(datos["asignaciones"]):
        if not isinstance(fila, dict):
            problemas.append(Problema("asignaciones_ausentes", f"asignación {i + 1}",
                                      f"la entrada llegó como `{_nombre_tipo(fila)}`"))
            continue
        punto = _texto_o_vacio(fila.get("punto"))
        if punto in declaradas:
            problemas.append(Problema("punto_duplicado", f"punto `{punto}`",
                                      "otra asignación ya lo declara, y con dos filas homónimas "
                                      "ningún reporte puede nombrar cuál falló"))
            continue
        declaradas[punto] = fila
    resumen["asignaciones"] = len(declaradas)

    for punto in esperadas:
        if punto not in declaradas:
            problemas.append(Problema(
                "asignacion_faltante", f"punto `{punto}`",
                "el mapa congelado lo tiene y el documento no lo declara. La comparación es por "
                "**igualdad exacta** y no por compatibilidad: omitir una asignación deja un punto "
                "de despacho sin familia ni variante"))
    for punto in sorted(set(declaradas) - set(esperadas)):
        problemas.append(Problema(
            "asignacion_de_mas", f"punto `{punto}`",
            "el documento lo declara y el mapa congelado no lo tiene"))

    for punto, esperada in esperadas.items():
        fila = declaradas.get(punto)
        if fila is None:
            continue
        donde = f"punto `{punto}`"
        familia = _texto_o_vacio(fila.get("familia"))
        variante = _texto_o_vacio(fila.get("variante"))
        procedencia = _texto_o_vacio(fila.get("procedencia"))
        if familia != esperada.familia:
            problemas.append(Problema("familia_no_coincide", donde,
                                      f"declara `{familia}` y el mapa congelado dice "
                                      f"`{esperada.familia}`"))
        if variante != esperada.variante:
            problemas.append(Problema("variante_no_coincide", donde,
                                      f"declara `{variante}` y el mapa congelado dice "
                                      f"`{esperada.variante}`"))
        if procedencia != esperada.procedencia:
            problemas.append(Problema(
                "procedencia_no_coincide", donde,
                f"declara `{procedencia or '(vacía)'}` y el mapa congelado dice "
                f"`{esperada.procedencia}`: una fila decidida acá y una nombrada por el roadmap no "
                "llevan la misma carga de la prueba"))
            continue

        if procedencia == "decision":
            if not _texto_o_vacio(fila.get("justificacion")):
                problemas.append(Problema(
                    "justificacion_ausente", donde,
                    "la asignación se decidió acá y no dice por qué; una decisión sin argumento la "
                    "vuelve a tomar distinta el próximo que la necesite"))
            resumen["decisiones"] += 1
        else:
            puntero = _texto_o_vacio(fila.get("puntero_variante"))
            if not puntero:
                problemas.append(Problema(
                    "puntero_de_variante_ausente", donde,
                    "se declara derivada del roadmap y no dice de dónde"))
            else:
                motivo = _resolver_puntero(puntero, esperada.variante, arbol)
                if motivo == "sede_irresoluble":
                    problemas.append(Problema("puntero_de_variante_irresoluble", donde,
                                              f"`{puntero}` no resuelve contra el árbol"))
                elif motivo:
                    problemas.append(Problema(
                        "variante_ausente_en_la_sede", donde,
                        f"`{puntero}` resuelve y no nombra la variante `{esperada.variante}`: la "
                        "fila se declara derivada de una sede que no la contiene"))
                else:
                    resumen["punteros_de_variante"] += 1

        if not _texto_o_vacio(fila.get("forma_de_resultado")):
            problemas.append(Problema("forma_de_resultado_ausente", donde,
                                      "no declara qué forma tiene su resultado"))
        if not _texto_o_vacio(fila.get("declaracion_de_salida")):
            problemas.append(Problema("declaracion_de_salida_ausente", donde,
                                      "no declara cuál es su declaración de salida"))
        if "autoridad" not in fila:
            problemas.append(Problema(
                "autoridad_ausente", donde,
                "no declara su autoridad final, que va por punto y variante"))
        else:
            _verificar_campo(fila["autoridad"], f"{donde}, autoridad", raiz, problemas, resumen)

    # «Dos variantes cuyo resultado hoy tiene forma distinta no comparten declaración de salida».
    por_declaracion: dict[str, set[str]] = {}
    for punto, fila in declaradas.items():
        declaracion = _texto_o_vacio(fila.get("declaracion_de_salida"))
        forma = _texto_o_vacio(fila.get("forma_de_resultado"))
        if declaracion and forma:
            por_declaracion.setdefault(declaracion, set()).add(forma)
    for declaracion, formas in sorted(por_declaracion.items()):
        if len(formas) > 1:
            problemas.append(Problema(
                "salida_compartida_entre_formas_distintas", f"declaración `{declaracion}`",
                f"la comparten {len(formas)} formas de resultado distintas "
                f"({', '.join('`' + f + '`' for f in sorted(formas))}); un contrato de salida "
                "compartido entre resultados que hoy tienen forma distinta obliga a los dos a "
                "mentir sobre uno"))


def verificar_roles(texto: str, raiz: Path, arbol: Path) -> tuple[list[Problema], dict]:
    """Los contratos de las cinco familias y el mapa de las trece asignaciones, que se congelan de
    formas distintas y conviene no confundirlas.

    Las **familias se derivan**: salen de la tabla del roadmap y cada una lleva su puntero, que se
    resuelve contra el árbol real. El **mapa punto → variante no**: el roadmap mapea skill → roles
    reusables y construirlo fue decidir, así que se compara contra el inventario congelado y ocho de
    sus trece filas llevan además el puntero de la variante que el roadmap sí nombra."""
    problemas: list[Problema] = []
    resumen = {"familias": 0, "punteros_de_familia": 0, "campos_anclados": 0, "campos_resueltos": 0,
               "campos_no_anclados": 0, "asignaciones": 0, "punteros_de_variante": 0,
               "decisiones": 0}
    familias, motivo_f = _bloque_json(texto, SLUG_FAMILIAS)
    if motivo_f:
        problemas.append(Problema("familias_ausentes", f"sección `{SLUG_FAMILIAS}`", motivo_f)
                         if "no parsea" not in motivo_f else
                         Problema("bloque_ilegible", f"sección `{SLUG_FAMILIAS}`", motivo_f))
    else:
        _verificar_familias(familias, raiz, arbol, problemas, resumen)

    asignaciones, motivo_a = _bloque_json(texto, SLUG_ASIGNACIONES)
    if motivo_a:
        problemas.append(Problema("asignaciones_ausentes", f"sección `{SLUG_ASIGNACIONES}`",
                                  motivo_a)
                         if "no parsea" not in motivo_a else
                         Problema("bloque_ilegible", f"sección `{SLUG_ASIGNACIONES}`", motivo_a))
    else:
        _verificar_asignaciones(asignaciones, raiz, arbol, problemas, resumen)
    return problemas, resumen

# --- Modo `--diversidad` ----------------------------------------------------------------------

def _relacion(una: str, otra: str) -> str:
    return "same_family" if una == otra else "cross_family"


def _derivar_intento(intento: dict) -> dict:
    """Las relaciones y la clase de un intento, **derivadas de sus tres identidades**.

    `single_voice` no es una relación: es la propiedad de que las tres identidades sean la misma
    familia. Tratarla como una tercera relación la volvería equivalente a `same_family`, que es
    exactamente la equivalencia falsa que la política existe para impedir."""
    conductor = _texto_o_vacio(intento.get("conductor"))
    autor = _texto_o_vacio(intento.get("autor_del_artefacto"))
    worker = _texto_o_vacio(intento.get("worker"))
    return {
        "worker_vs_conductor": _relacion(worker, conductor),
        "worker_vs_autor": _relacion(worker, autor),
        "single_voice": len({conductor, autor, worker}) == 1,
    }


def _cuenta_como_independiente(derivado: dict) -> bool:
    """La regla de evidencia independiente, **ejecutable**.

    Un resultado cuenta cuando quien hizo el trabajo delegado es de otra familia que quien escribió
    el artefacto que ese trabajo juzga, y la corrida no fue de una sola voz. Un resultado de una sola
    familia respecto del autor no es evidencia independiente por más intentos que se acumulen: mide
    la misma correlación de errores dos veces."""
    return not derivado["single_voice"] and derivado["worker_vs_autor"] == "cross_family"


def verificar_diversidad(texto: str) -> tuple[list[Problema], dict]:
    problemas: list[Problema] = []
    resumen = {"intentos": 0, "relaciones_derivadas": 0, "independientes": 0, "single_voice": 0,
               "topologia_comparada": 0}
    datos, motivo = _bloque_json(texto, SLUG_DIVERSIDAD)
    if motivo:
        return [Problema("diversidad_ausente", f"sección `{SLUG_DIVERSIDAD}`", motivo)], resumen
    if not isinstance(datos, dict):
        return [Problema("bloque_ilegible", f"sección `{SLUG_DIVERSIDAD}`",
                         f"el bloque declara `{_nombre_tipo(datos)}` y no un objeto")], resumen

    intentos = datos.get("intentos")
    if not isinstance(intentos, list) or not intentos:
        problemas.append(Problema(
            "intentos_ausentes", f"sección `{SLUG_DIVERSIDAD}`",
            "la política no registra ningún intento; sin registros por intento no hay de dónde "
            "derivar la topología, y declararla suelta es lo que AC-14 prohíbe"))
        return problemas, resumen

    vistos: set[str] = set()
    derivados: list[dict] = []
    for i, intento in enumerate(intentos):
        if not isinstance(intento, dict):
            problemas.append(Problema("intento_no_objeto", f"intento {i + 1}",
                                      f"llegó como `{_nombre_tipo(intento)}`"))
            continue
        ident = _texto_o_vacio(intento.get("id")) or f"(sin id, {i + 1})"
        donde = f"intento `{ident}`"
        if ident in vistos:
            problemas.append(Problema("intento_id_duplicado", donde,
                                      "otro intento ya usa ese identificador"))
        vistos.add(ident)

        faltan = [c for c in ("conductor", "autor_del_artefacto", "worker")
                  if not _texto_o_vacio(intento.get(c))]
        if faltan:
            problemas.append(Problema(
                "intento_sin_identidad", donde,
                f"no registra {', '.join('`' + f + '`' for f in faltan)}; `cross_family` necesita "
                "un referente, y sin las tres identidades no se sabe respecto de qué se cruza"))
            continue
        desconocidas = [intento[c] for c in ("conductor", "autor_del_artefacto", "worker")
                        if intento[c] not in FAMILIAS_DE_MODELO]
        if desconocidas:
            problemas.append(Problema(
                "familia_desconocida", donde,
                f"{', '.join('`' + d + '`' for d in desconocidas)} no es una de las dos familias "
                f"({', '.join('`' + f + '`' for f in FAMILIAS_DE_MODELO)})"))
            continue

        derivado = _derivar_intento(intento)
        derivados.append(derivado)
        resumen["intentos"] += 1
        if derivado["single_voice"]:
            resumen["single_voice"] += 1

        relaciones = intento.get("relaciones")
        if not isinstance(relaciones, dict):
            problemas.append(Problema(
                "relacion_ausente", donde,
                "no registra las relaciones entre las tres identidades; con las identidades solas, "
                "el agregado se leería de una declaración en vez de derivarse"))
        else:
            for par in ("worker_vs_conductor", "worker_vs_autor"):
                declarada = _texto_o_vacio(relaciones.get(par))
                if not declarada:
                    problemas.append(Problema("relacion_ausente", f"{donde}, `{par}`",
                                              "no se registra"))
                elif declarada not in RELACIONES:
                    problemas.append(Problema(
                        "relacion_desconocida", f"{donde}, `{par}`",
                        f"`{declarada}` no es una relación; el vocabulario es "
                        f"{', '.join('`' + r + '`' for r in RELACIONES)}"))
                elif declarada != derivado[par]:
                    problemas.append(Problema(
                        "relacion_no_coincide", f"{donde}, `{par}`",
                        f"se registra `{declarada}` y las identidades dan `{derivado[par]}`"))
                else:
                    resumen["relaciones_derivadas"] += 1

        if "cuenta_como_evidencia_independiente" not in intento:
            problemas.append(Problema(
                "independencia_omitida", donde,
                "no dice si su resultado cuenta como evidencia independiente; sin eso la regla "
                "queda como prosa y cada consumidor la aplica a su manera"))
            continue
        declarada = bool(intento["cuenta_como_evidencia_independiente"])
        real = _cuenta_como_independiente(derivado)
        if declarada:
            resumen["independientes"] += 1
        if declarada and not real:
            if derivado["single_voice"]:
                problemas.append(Problema(
                    "independiente_de_una_sola_voz", donde,
                    "cuenta como evidencia independiente un resultado en el que conducen, escriben "
                    "y trabajan la misma familia: una sola voz no se confirma a sí misma"))
            else:
                problemas.append(Problema(
                    "independiente_de_una_sola_familia", donde,
                    "cuenta como evidencia independiente un resultado en el que el trabajo delegado "
                    "es de la misma familia que quien escribió el artefacto que juzga: mide la "
                    "misma correlación de errores dos veces"))
        elif real and not declarada:
            problemas.append(Problema(
                "independencia_negada", donde,
                "el trabajo delegado es de otra familia que el autor del artefacto y la corrida "
                "tiene más de una voz, y aun así no se cuenta: la regla también dice qué **sí** "
                "cuenta, y descartar evidencia válida deja la política sin poder afirmar nada"))

    if not derivados:
        return problemas, resumen

    agregada = {
        "intentos": len(derivados),
        "single_voice": sum(1 for d in derivados if d["single_voice"]),
        "cross_vs_conductor": sum(1 for d in derivados
                                  if d["worker_vs_conductor"] == "cross_family"),
        "cross_vs_autor": sum(1 for d in derivados if d["worker_vs_autor"] == "cross_family"),
        "evidencia_independiente": sum(1 for d in derivados if _cuenta_como_independiente(d)),
        "familias_presentes": sorted({f for i in intentos if isinstance(i, dict)
                                      for f in (_texto_o_vacio(i.get("conductor")),
                                                _texto_o_vacio(i.get("autor_del_artefacto")),
                                                _texto_o_vacio(i.get("worker"))) if f}),
    }
    topologia = datos.get("topologia")
    if not isinstance(topologia, dict) or not topologia:
        problemas.append(Problema(
            "topologia_ausente", f"sección `{SLUG_DIVERSIDAD}`",
            "no declara la topología agregada de la corrida. Se deriva de los registros, y por eso "
            "mismo tiene que estar escrita: si no está, no hay nada contra qué contrastar el "
            "derivado y el documento afirma un agregado que nadie puede leer"))
        return problemas, resumen
    if topologia != agregada:
        diferencias = sorted(k for k in set(topologia) | set(agregada)
                             if topologia.get(k) != agregada.get(k))
        problemas.append(Problema(
            "topologia_contradice_registros", f"sección `{SLUG_DIVERSIDAD}`",
            f"la topología declarada no es la que sus propios registros producen; difieren en "
            f"{', '.join('`' + d + '`' for d in diferencias)}: declarada "
            f"{ {k: topologia.get(k) for k in diferencias} }, derivada "
            f"{ {k: agregada.get(k) for k in diferencias} }"))
    else:
        resumen["topologia_comparada"] = 1
    return problemas, resumen


# --- Modo `--defectos` ------------------------------------------------------------------------

def verificar_defectos(texto: str) -> tuple[list[Problema], dict]:
    """Los seis mínimos **por identidad**, y de ahí para arriba.

    `len(defectos) >= 6` satisface todo lo demás que este modo pide y a la vez acepta un inventario
    que cambió uno de los seis por otro conservando el total. Acepta más y rechaza menos: el mínimo
    no es un conjunto cerrado, y un modo que exigiera exactamente esos seis rechazaría un inventario
    más completo que el exigido."""
    problemas: list[Problema] = []
    resumen = {"defectos": 0, "minimos_presentes": 0, "extra": 0}
    datos, motivo = _bloque_json(texto, SLUG_DEFECTOS)
    if motivo:
        return [Problema("defectos_ausentes", f"sección `{SLUG_DEFECTOS}`", motivo)], resumen
    if not isinstance(datos, dict):
        return [Problema("bloque_ilegible", f"sección `{SLUG_DEFECTOS}`",
                         f"el bloque declara `{_nombre_tipo(datos)}` y no un objeto")], resumen
    lista = datos.get("defectos")
    if not isinstance(lista, list) or not lista:
        return [Problema(
            "defectos_ausentes", f"sección `{SLUG_DEFECTOS}`",
            "el inventario no registra ningún defecto; una lista vacía satisface «todos los "
            "defectos registrados tienen ubicación» por vacuidad")], resumen

    vistos: set[str] = set()
    for i, defecto in enumerate(lista):
        if not isinstance(defecto, dict):
            problemas.append(Problema("defecto_no_objeto", f"defecto {i + 1}",
                                      f"llegó como `{_nombre_tipo(defecto)}`"))
            continue
        ident = _texto_o_vacio(defecto.get("id"))
        donde = f"defecto `{ident}`" if ident else f"defecto {i + 1}"
        if not ident:
            problemas.append(Problema("defecto_sin_identidad", donde,
                                      "no declara su identidad, así que no se puede comparar contra "
                                      "el mínimo ni nombrar en un reporte"))
            continue
        if ident in vistos:
            problemas.append(Problema("defecto_id_duplicado", donde,
                                      "otro defecto ya usa esa identidad"))
            continue
        vistos.add(ident)
        resumen["defectos"] += 1
        for campo in CAMPOS_DE_DEFECTO:
            if not _texto_o_vacio(defecto.get(campo)):
                problemas.append(Problema("defecto_sin_campo", donde,
                                          f"no declara su `{campo}`"))
        ubicacion = _texto_o_vacio(defecto.get("ubicacion"))
        if ubicacion and not PATRON_UBICACION.match(ubicacion):
            problemas.append(Problema(
                "ubicacion_sin_forma", donde,
                f"`{ubicacion}` no tiene forma de puntero (ruta relativa, con fragmento o sin él); "
                "«documental» o «en las instrucciones» no ubican nada"))

    identidades = {d.identidad for d in DEFECTOS_MINIMOS}
    resumen["minimos_presentes"] = len(vistos & identidades)
    resumen["extra"] = len(vistos - identidades)
    for minimo in DEFECTOS_MINIMOS:
        if minimo.identidad in vistos:
            continue
        problemas.append(Problema(
            "defecto_minimo_faltante", f"defecto `{minimo.identidad}`",
            f"el inventario no lo registra: {minimo.descripcion}. La comparación es **por "
            "identidad**; con el total intacto, un conteo no vería que uno de los seis fue "
            "reemplazado por otro"))
    return problemas, resumen


# --- Los cinco modos de aplicación ------------------------------------------------------------

def modo_perfil_schema(ruta: Path) -> int:
    texto, codigo = _leer_documento_de_contrato(ruta, "perfil-schema")
    if texto is None:
        return codigo
    problemas, resumen = verificar_perfil_schema(texto)
    if problemas:
        _informar(problemas, f"{ruta.name} — el contenedor del perfil de ejecución")
        return 1
    print(f"OK     {ruta.name}: el contenedor declara sus {resumen['componentes']} componentes y "
          f"{resumen['perfiles']} perfiles nombrados con {resumen['asignaciones']} asignaciones por "
          "rol")
    print(f"OK     los {resumen['objetos_de_parametros']} objetos de parámetros entregan al runtime "
          f"{resumen['parametros']} valores y ninguno fuera de la lista blanca")
    print()
    print("RESULTADO: OK")
    return 0


def modo_perfil_precedencia(ruta: Path) -> int:
    texto, codigo = _leer_documento_de_contrato(ruta, "perfil-precedencia")
    if texto is None:
        return codigo
    problemas, resumen = verificar_perfil_precedencia(texto)
    if problemas:
        _informar(problemas, f"{ruta.name} — la precedencia del perfil de ejecución")
        return 1
    print(f"OK     {ruta.name}: los {resumen['evaluados']} escenarios resuelven contra los "
          f"{resumen['niveles']} niveles declarados como el documento dice")
    print(f"OK     {resumen['invalidos']} resuelven inválidos y no ignorados, y las "
          f"{resumen['ausencias_legitimas']} ausencias legítimas caen al default portable por sus "
          "dos causas distintas")
    print()
    print("RESULTADO: OK")
    return 0


def modo_roles(ruta: Path, raiz: Path, arbol: Path) -> int:
    texto, codigo = _leer_documento_de_contrato(ruta, "roles")
    if texto is None:
        return codigo
    problemas, resumen = verificar_roles(texto, raiz, arbol)
    if problemas:
        _informar(problemas, f"{ruta.name} — contratos de rol y mapa de asignaciones")
        return 1
    print(f"OK     {ruta.name}: las {resumen['familias']} familias declaran sus contratos, y sus "
          f"{resumen['punteros_de_familia']} punteros resuelven contra el árbol")
    print(f"OK     {resumen['campos_resueltos']} de {resumen['campos_anclados']} campos anclados "
          f"resuelven contra su sede con el verificador semántico de la matriz; "
          f"{resumen['campos_no_anclados']} declaran por qué no lo están")
    print(f"OK     las {resumen['asignaciones']} asignaciones coinciden con el mapa congelado "
          f"({resumen['punteros_de_variante']} con puntero al roadmap, {resumen['decisiones']} "
          "decididas acá con su justificación)")
    print()
    print("RESULTADO: OK")
    return 0


def modo_diversidad(ruta: Path) -> int:
    texto, codigo = _leer_documento_de_contrato(ruta, "diversidad")
    if texto is None:
        return codigo
    problemas, resumen = verificar_diversidad(texto)
    if problemas:
        _informar(problemas, f"{ruta.name} — la política de diversidad")
        return 1
    print(f"OK     {ruta.name}: los {resumen['intentos']} intentos registran sus tres identidades y "
          f"{resumen['relaciones_derivadas']} relaciones, y las relaciones coinciden con lo que las "
          "identidades dan")
    print(f"OK     la topología agregada se derivó de esos registros y coincide con la declarada; "
          f"{resumen['independientes']} resultados cuentan como evidencia independiente y "
          f"{resumen['single_voice']} intento(s) de una sola voz no")
    print()
    print("RESULTADO: OK")
    return 0


def modo_defectos(ruta: Path) -> int:
    texto, codigo = _leer_documento_de_contrato(ruta, "defectos")
    if texto is None:
        return codigo
    problemas, resumen = verificar_defectos(texto)
    if problemas:
        _informar(problemas, f"{ruta.name} — el inventario de defectos")
        return 1
    print(f"OK     {ruta.name}: el inventario registra {resumen['defectos']} defectos con su "
          f"ubicación, su naturaleza y su fase")
    print(f"OK     los {resumen['minimos_presentes']} mínimos están, comparados por identidad, y "
          f"{resumen['extra']} más: el mínimo no es un conjunto cerrado")
    print()
    print("RESULTADO: OK")
    return 0

# --- Autotests de los cinco modos --------------------------------------------------------------
#
# Mismo corpus que los tres modos de contrato y misma regla: **nada de esto escribe en disco**. El
# documento se muta en memoria, la raíz de las procedencias sintéticas es el fixture congelado en
# lectura y los punteros normativos se resuelven contra el árbol real. Mutar el árbol de trabajo
# dejaría el fixture mutado si el proceso muriera, y otro agente no distingue esa ventana de un
# cambio real.

SEDE_DE_ROL = CONFORME_CONTRATO / "fuentes" / "contratos-de-rol.md"

# Una sección real del roadmap que **no** nombra ninguna de las cinco familias ni ninguna variante:
# es lo que separa «el puntero no resuelve» de «resuelve y no dice nada de esto».
SEDE_SIN_LOS_LITERALES = ("docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md"
                          "#2-2-identidad-de-familia-sin-ambiguedad")


def _en_json(slug: str, mutacion: Any) -> Any:
    """Reemplaza el bloque `json` de una sección por el resultado de mutar su dato.

    Por dato y no por búsqueda y reemplazo de texto: el corpus tiene veinticuatro procedencias
    ancladas casi idénticas, y un reemplazo textual tocaría la que no era."""
    def aplicar(texto: str) -> str:
        datos, motivo = _bloque_json(texto, slug)
        rango = _rango_del_bloque(texto, slug)
        if motivo or rango is None:
            raise ValueError(motivo or f"no se ubicó el bloque de `{slug}`")
        nuevo = mutacion(copy.deepcopy(datos))
        lineas = texto.split("\n")
        rendido = json.dumps(nuevo, ensure_ascii=False, indent=2).split("\n")
        return "\n".join(lineas[:rango[0]] + rendido + lineas[rango[1] + 1:])
    return aplicar


def _romper_json(slug: str) -> Any:
    """Deja el bloque sintácticamente inválido sin tocar nada más."""
    def aplicar(texto: str) -> str:
        rango = _rango_del_bloque(texto, slug)
        if rango is None:
            raise ValueError(f"no se ubicó el bloque de `{slug}`")
        lineas = texto.split("\n")
        lineas[rango[0]] = lineas[rango[0]] + " ,,"
        return "\n".join(lineas)
    return aplicar


def _de_lista(datos: dict, clave: str, campo: str, valor: str) -> dict:
    """La entrada de una lista de objetos, buscada por el valor de uno de sus campos."""
    for entrada in datos[clave]:
        if isinstance(entrada, dict) and entrada.get(campo) == valor:
            return entrada
    raise ValueError(f"el corpus no tiene ninguna entrada con {campo}={valor!r}")


def _perfil_del_bloque(datos: dict, nombre: str) -> dict:
    contenedor = contenedor_del_perfil()
    perfiles = next(v for _, v in _navegar(datos, contenedor.ruta_de("perfiles_nombrados")))
    return perfiles[nombre]


def _bindings_del_bloque(datos: dict) -> dict:
    contenedor = contenedor_del_perfil()
    ruta = contenedor.ruta_de("valor_por_defecto")[:-1]
    return next(v for _, v in _navegar(datos, ruta))


# --- Casos de `--perfil-schema` ---------------------------------------------------------------

# Las cinco clases que AC-10 nombra —herramientas, aislamiento, permisos, contrato de salida y
# autoridad— **más una sexta que no es ninguna de las cinco**: un tercer parámetro de runtime, que no
# eleva nada y aun así no está en la lista blanca. Sin ella, un modo que enumerara lo prohibido en vez
# de cerrar lo admitido pasaría las cinco y dejaría entrar todo lo que nadie pensó en prohibir.
HOJAS_QUE_NO_VAN_EN_UN_PERFIL = (
    ("tools", ["bash", "write"], "herramientas"),
    ("sandbox", "workspace-write", "aislamiento"),
    ("permissions", {"edit": "allow"}, "permisos"),
    ("output_contract", "informe-extendido", "contrato de salida"),
    ("authority", "final", "autoridad"),
    ("temperature", 0.2, "un tercer parámetro de runtime, que no es ninguna de las cinco clases"),
)


def _casos_de_perfil_schema() -> tuple[CasoDeContrato, ...]:
    contenedor = contenedor_del_perfil()
    familia = contenedor.familias[0] if contenedor.familias else "codex"
    parametro = contenedor.parametros[0] if contenedor.parametros else "model"

    def agregar_hoja(clave: str, valor: Any) -> Any:
        return _en_json(SLUG_PERFIL_SCHEMA,
                        lambda d: (_perfil_del_bloque(d, "economy")[familia].update({clave: valor})
                                   or d))

    mutantes_de_hoja = tuple(
        CasoDeContrato(
            "parametro_no_admitido",
            f"un perfil agrega `{clave}` a su objeto de parámetros: {etiqueta}",
            agregar_hoja(clave, valor))
        for clave, valor, etiqueta in HOJAS_QUE_NO_VAN_EN_UN_PERFIL)

    return (
        # Los conformes. El primero **es** la frontera que la task nombra: sus cinco componentes se
        # llaman `schema_version`, `profiles`, `bindings`, `default` y las familias, y ninguno está
        # en la lista blanca. Un modo que aplicara la lista blanca al contenedor los rechazaría a
        # todos, pasaría los seis mutantes de hoja y caería acá.
        CasoDeContrato(None, "el contenedor completo, con perfiles que entregan solo modelo y "
                             "esfuerzo de razonamiento"),
        CasoDeContrato(
            None, "un cuarto perfil con sus dos familias y sus dos parámetros: aceptar más perfiles "
                  "no es un defecto",
            _en_json(SLUG_PERFIL_SCHEMA, lambda d: (
                _navegar(d, contenedor.ruta_de("perfiles_nombrados"))[0][1].update(
                    {"exhaustivo": {f: dict(zip(contenedor.parametros,
                                                ("inherit", "high")))
                                    for f in contenedor.familias}})
                or _bindings_del_bloque(d)["roles"].update({"diff-reviewer": "exhaustivo"})
                or d))),
        CasoDeContrato(
            None, "una clave de más **en el contenedor**, fuera del objeto de parámetros: la lista "
                  "blanca gobierna el nivel de adentro y no este",
            _en_json(SLUG_PERFIL_SCHEMA,
                     lambda d: (d[contenedor.clave_raiz].update({"notas": "libre"}) or d))),
        CasoDeContrato(
            None, "no-op: se reescribe prosa fuera del bloque",
            _reemplazar_prosa("Una asignación elige qué perfil se resuelve.",
                              "Una asignación elige cuál perfil se resuelve.")),

        # El contenedor completo, componente por componente.
        CasoDeContrato("schema_ausente", "el documento no declara la sección del schema",
                       _borrar_seccion(SLUG_PERFIL_SCHEMA)),
        CasoDeContrato("bloque_ilegible", "el bloque declara una lista en vez del contenedor",
                       _en_json(SLUG_PERFIL_SCHEMA, lambda d: [d])),
        CasoDeContrato("clave_raiz_ausente", "el schema no cuelga de la clave raíz reservada",
                       _en_json(SLUG_PERFIL_SCHEMA,
                                lambda d: {"agentes": d[contenedor.clave_raiz]})),
        CasoDeContrato(
            "componente_ausente", "el contenedor pierde su versión",
            _en_json(SLUG_PERFIL_SCHEMA,
                     lambda d: (d[contenedor.clave_raiz].pop(
                         contenedor.ruta_de("version")[-1]) and d or d))),
        CasoDeContrato(
            "componente_ausente", "el contenedor pierde sus asignaciones por rol",
            _en_json(SLUG_PERFIL_SCHEMA,
                     lambda d: (_bindings_del_bloque(d).pop("roles") and d or d))),
        CasoDeContrato(
            "componente_ausente", "el contenedor pierde su valor por defecto",
            _en_json(SLUG_PERFIL_SCHEMA,
                     lambda d: (_bindings_del_bloque(d).pop("default") and d or d))),
        CasoDeContrato(
            "componente_ausente", "ningún perfil declara familias, así que el componente desaparece",
            _en_json(SLUG_PERFIL_SCHEMA, lambda d: (
                [p.clear() for _, p in _navegar(d, contenedor.ruta_de("perfiles_nombrados") + ("<p>",))]
                and d or d))),
        CasoDeContrato(
            "perfiles_vacios", "el mapa de perfiles existe y no declara ninguno",
            _en_json(SLUG_PERFIL_SCHEMA, lambda d: (
                d[contenedor.clave_raiz].update(
                    {contenedor.ruta_de("perfiles_nombrados")[-1]: {}}) or d))),
        CasoDeContrato(
            "perfil_no_objeto", "un perfil se declara como el nombre de otro",
            _en_json(SLUG_PERFIL_SCHEMA, lambda d: (
                _navegar(d, contenedor.ruta_de("perfiles_nombrados"))[0][1].update(
                    {"economy": "balanced"}) or d))),
        CasoDeContrato(
            "perfil_sin_familias", "un solo perfil se queda sin familias",
            _en_json(SLUG_PERFIL_SCHEMA,
                     lambda d: (_perfil_del_bloque(d, "economy").clear() or d))),
        CasoDeContrato(
            "familia_desconocida", "un perfil estrena una tercera familia",
            _en_json(SLUG_PERFIL_SCHEMA, lambda d: (
                _perfil_del_bloque(d, "economy").update(
                    {"familia-tercera": dict(zip(contenedor.parametros, ("inherit", "low")))})
                or d))),
        CasoDeContrato(
            "parametros_no_objeto", "los parámetros de una familia se declaran como un escalar",
            _en_json(SLUG_PERFIL_SCHEMA,
                     lambda d: (_perfil_del_bloque(d, "economy").update({familia: "inherit"})
                                or d))),
        *mutantes_de_hoja,
        CasoDeContrato(
            "parametro_ausente", f"un perfil deja de entregar `{parametro}`",
            _en_json(SLUG_PERFIL_SCHEMA,
                     lambda d: (_perfil_del_bloque(d, "economy")[familia].pop(parametro)
                                and d or d))),
        CasoDeContrato(
            "asignacion_no_escalar",
            "una asignación deja de nombrar un perfil y pasa a transportar herramientas y permisos",
            _en_json(SLUG_PERFIL_SCHEMA, lambda d: (
                _bindings_del_bloque(d)["roles"].update(
                    {"explorer": {"profile": "economy", "tools": ["bash"],
                                  "permissions": {"edit": "allow"}}}) or d))),
        CasoDeContrato(
            "asignaciones_vacias", "el mapa de rol a perfil existe y está vacío",
            _en_json(SLUG_PERFIL_SCHEMA,
                     lambda d: (_bindings_del_bloque(d).update({"roles": {}}) or d))),
        CasoDeContrato(
            "default_no_escalar", "el valor por defecto se declara como un perfil entero",
            _en_json(SLUG_PERFIL_SCHEMA, lambda d: (
                _bindings_del_bloque(d).update(
                    {"default": {f: dict(zip(contenedor.parametros, ("inherit", "low")))
                                 for f in contenedor.familias}}) or d))),
    )


def _bloque_de_los_dos_niveles() -> list[tuple[str, bool, str]]:
    """[E] La lista blanca es del **objeto de parámetros**, no del contenedor.

    Tres direcciones, porque cada una sola admite una implementación degenerada: que el conforme pase
    lo satisface un modo que no mire nada; que la hoja de adentro caiga lo satisface uno que aplique
    la lista blanca a todo nivel —y ese rechazaría el conforme—; y que la **misma clave** puesta
    afuera pase es lo único que muestra que los dos niveles no se confundieron."""
    contenedor = contenedor_del_perfil()
    texto = _texto_conforme()
    datos, _ = _bloque_json(texto, SLUG_PERFIL_SCHEMA)
    componentes = sorted({contenedor.ruta_de(c)[-1] for c in contenedor.obligatorios}
                         | set(contenedor.familias))
    fuera_de_la_lista = [c for c in componentes if c not in contenedor.parametros]

    clave = HOJAS_QUE_NO_VAN_EN_UN_PERFIL[-1][0]
    adentro = _en_json(SLUG_PERFIL_SCHEMA, lambda d: (
        _perfil_del_bloque(d, "economy")[contenedor.familias[0]].update({clave: 0.2}) or d))(texto)
    afuera = _en_json(SLUG_PERFIL_SCHEMA,
                      lambda d: (d[contenedor.clave_raiz].update({clave: 0.2}) or d))(texto)
    problemas_conforme, _ = verificar_perfil_schema(texto)
    codigos_adentro = {p.codigo for p in verificar_perfil_schema(adentro)[0]}
    problemas_afuera, _ = verificar_perfil_schema(afuera)

    return [
        ("E1/perfil-schema", not problemas_conforme and len(fuera_de_la_lista) >= 4,
         f"el contenedor declara {len(fuera_de_la_lista)} nombres que **no** están en la lista "
         f"blanca ({', '.join('`' + c + '`' for c in fuera_de_la_lista)}) y el modo los acepta: la "
         "lista no alcanza a este nivel"
         if not problemas_conforme and len(fuera_de_la_lista) >= 4 else
         f"el conforme falló ({problemas_conforme[:1]}) o el contenedor no tiene nombres fuera de "
         f"la lista blanca: {fuera_de_la_lista}"),
        ("E2/perfil-schema", codigos_adentro == {"parametro_no_admitido"},
         f"y la misma clave `{clave}` **dentro** del objeto de parámetros cae, y solo por eso"
         if codigos_adentro == {"parametro_no_admitido"} else
         f"la hoja de adentro emitió {sorted(codigos_adentro)}"),
        ("E3/perfil-schema", not problemas_afuera,
         f"y `{clave}` colgada del contenedor **no** cae: los dos niveles no se confundieron"
         if not problemas_afuera else
         f"la clave de más en el contenedor emitió {[str(p) for p in problemas_afuera[:2]]}"),
        ("E4/perfil-schema", isinstance(datos, dict) and contenedor.clave_raiz in datos
         and len(contenedor.obligatorios) == 5,
         f"y los componentes obligatorios que la lista de nombres reservados declara son "
         f"{len(contenedor.obligatorios)}: {', '.join(contenedor.obligatorios)}"
         if len(contenedor.obligatorios) == 5 else
         f"los componentes obligatorios derivados son {contenedor.obligatorios} y tendrían que ser "
         "cinco"),
    ]


def _correr_caso_de_perfil_schema(caso: CasoDeContrato) -> tuple[list[Problema], dict]:
    texto = caso.mutar(_texto_conforme()) if caso.mutar else _texto_conforme()
    return verificar_perfil_schema(texto)


def modo_autotest_perfil_schema() -> int:
    resultados = _preludio_de_t13()
    if all(ok for _, ok, _ in resultados):
        casos = _casos_de_perfil_schema()
        resultados += _bloque_de_documento(
            "perfil-schema", casos, _correr_caso_de_perfil_schema, CODIGOS_PERFIL_SCHEMA,
            lambda r: (f"leyó {r['componentes']} componentes y {r['perfiles']} perfiles: no "
                       "recorrió el contenedor"
                       if r["componentes"] != 5 or not r["perfiles"] else
                       "no miró ningún objeto de parámetros"
                       if not r["objetos_de_parametros"] else
                       "no leyó ninguna asignación por rol" if not r["asignaciones"] else ""))
        resultados += _bloque_de_los_dos_niveles()
        resultados += _bloque_de_ausencia("perfil-schema", modo_perfil_schema)
    return _cierre("el contenedor del perfil declara sus cinco componentes y el objeto de "
                   "parámetros de cada perfil entrega solo modelo y esfuerzo de razonamiento",
                   resultados)

# --- Casos de `--perfil-precedencia` ----------------------------------------------------------

def _escenario_con_causa(datos: dict, causa: str) -> dict:
    for escenario in datos["escenarios"]:
        if isinstance(escenario, dict) \
                and isinstance(escenario.get("resolucion_esperada"), dict) \
                and escenario["resolucion_esperada"].get("causa") == causa:
            return escenario
    raise ValueError(f"el corpus no tiene ningún escenario con causa {causa!r}")


def _sin_escenario_de(causa: str) -> Any:
    def mutacion(datos: dict) -> dict:
        objetivo = _escenario_con_causa(datos, causa)
        datos["escenarios"] = [e for e in datos["escenarios"] if e is not objetivo]
        return datos
    return _en_json(SLUG_PERFIL_PRECEDENCIA, mutacion)


def _intercambiar_las_dos_causas(datos: dict) -> dict:
    una, otra = (_escenario_con_causa(datos, c) for c in CAUSAS_DE_AUSENCIA_LEGITIMA)
    una["resolucion_esperada"]["causa"], otra["resolucion_esperada"]["causa"] = (
        CAUSAS_DE_AUSENCIA_LEGITIMA[1], CAUSAS_DE_AUSENCIA_LEGITIMA[0])
    return datos


def _casos_de_perfil_precedencia() -> tuple[CasoDeContrato, ...]:
    def en(mutacion: Any) -> Any:
        return _en_json(SLUG_PERFIL_PRECEDENCIA, mutacion)

    def escenario(datos: dict, ident: str) -> dict:
        return _de_lista(datos, "escenarios", "id", ident)

    return (
        # Los conformes. El corpus trae los **dos** escenarios de ausencia legítima por separado y un
        # tercero que se les parece —sin asignación para el rol, pero con valor por defecto en la
        # superficie— que resuelve por otro nivel y no es ausencia.
        CasoDeContrato(None, "los ocho escenarios resuelven como el documento declara"),
        CasoDeContrato(
            None, "un escenario de más, válido: el corpus se puede ampliar",
            en(lambda d: (d["escenarios"].append(dict(escenario(d, "E-03"), id="E-09")) or d))),
        CasoDeContrato(
            None, "no-op: se reescribe prosa fuera del bloque",
            _reemplazar_prosa("Los niveles se recorren en orden y el primero que resuelve gana.",
                              "Los niveles se recorren en orden y gana el primero que resuelve.")),

        # La estructura de la sección.
        CasoDeContrato("precedencia_ausente", "el documento no declara la sección",
                       _borrar_seccion(SLUG_PERFIL_PRECEDENCIA)),
        CasoDeContrato("bloque_ilegible", "el bloque declara una lista",
                       en(lambda d: [d])),
        CasoDeContrato("niveles_ausentes", "la precedencia no declara sus niveles",
                       en(lambda d: (d.pop("niveles") and d or d))),
        CasoDeContrato("nivel_duplicado", "un nivel aparece dos veces en el orden",
                       en(lambda d: (d["niveles"].append(d["niveles"][0]) or d))),
        CasoDeContrato("default_portable_ausente", "no declara el perfil por defecto portable",
                       en(lambda d: (d.pop("default_portable") and d or d))),
        CasoDeContrato("escenarios_ausentes", "la precedencia se queda sin escenarios",
                       en(lambda d: (d.update({"escenarios": []}) or d))),
        CasoDeContrato("escenario_no_objeto", "un escenario se declara como texto",
                       en(lambda d: (d["escenarios"].append("el caso del override") or d))),
        CasoDeContrato("escenario_id_duplicado", "dos escenarios comparten identificador",
                       en(lambda d: (escenario(d, "E-02").update({"id": "E-01"}) or d))),
        CasoDeContrato("escenario_sin_rol", "un escenario no dice para qué rol resuelve",
                       en(lambda d: (escenario(d, "E-01").pop("rol") and d or d))),
        CasoDeContrato("escenario_sin_resolucion", "un escenario no declara qué tiene que resolver",
                       en(lambda d: (escenario(d, "E-04").pop("resolucion_esperada") and d or d))),
        CasoDeContrato("superficie_no_objeto", "la superficie se declara como la ruta de un archivo",
                       en(lambda d: (escenario(d, "E-01").update(
                           {"superficie": ".specify/config.yml"}) or d))),
        CasoDeContrato("clase_desconocida", "una resolución se declara `ignorado`",
                       en(lambda d: (escenario(d, "E-04")["resolucion_esperada"].update(
                           {"clase": "ignorado"}) or d))),
        CasoDeContrato("causa_desconocida", "una causa fuera del vocabulario",
                       en(lambda d: (escenario(d, "E-04")["resolucion_esperada"].update(
                           {"causa": "quedo_afuera"}) or d))),
        CasoDeContrato("nivel_desconocido", "una resolución dice resolver en un nivel que la "
                                            "precedencia no declara",
                       en(lambda d: (escenario(d, "E-01")["resolucion_esperada"].update(
                           {"nivel": "variable_de_entorno"}) or d))),

        # Los tres inválidos que AC-11 exige que **no** se ignoren, cada uno declarado como si
        # resolviera bien: el modo ejecuta la precedencia y lo desmiente.
        CasoDeContrato(
            "resolucion_no_coincide",
            "el perfil sin uso se declara resuelto en vez de inválido",
            en(lambda d: (escenario(d, "E-04").update(
                {"resolucion_esperada": {"clase": "resuelto", "perfil": "economy",
                                         "nivel": "asignacion_por_rol_de_la_superficie"}}) or d))),
        CasoDeContrato(
            "resolucion_no_coincide",
            "la asignación a un perfil inexistente se declara ignorada y resuelta al default",
            en(lambda d: (escenario(d, "E-05").update(
                {"resolucion_esperada": {"clase": "resuelto", "perfil": "balanced",
                                         "nivel": "perfil_default_portable",
                                         "causa": "sin_asignacion_para_el_rol"}}) or d))),
        CasoDeContrato(
            "resolucion_no_coincide", "la referencia rota se declara resuelta",
            en(lambda d: (escenario(d, "E-06").update(
                {"resolucion_esperada": {"clase": "resuelto", "perfil": "economy",
                                         "nivel": "asignacion_por_rol_de_la_superficie"}}) or d))),
        CasoDeContrato(
            "resolucion_no_coincide",
            "las dos ausencias legítimas se intercambian sus causas: los dos escenarios siguen "
            "cayendo al default portable, y solo la causa derivada los separa",
            en(_intercambiar_las_dos_causas)),

        # Y las dos ausencias legítimas, cada una con su fixture: retirar una no la tapa la otra.
        CasoDeContrato(
            "escenario_de_ausencia_faltante",
            "el corpus se queda sin el escenario de punto **sin asignación** habiendo superficie",
            _sin_escenario_de(CAUSAS_DE_AUSENCIA_LEGITIMA[0])),
        CasoDeContrato(
            "escenario_de_ausencia_faltante",
            "el corpus se queda sin el escenario de punto **sin superficie** de configuración",
            _sin_escenario_de(CAUSAS_DE_AUSENCIA_LEGITIMA[1])),
    )


def _correr_caso_de_precedencia(caso: CasoDeContrato) -> tuple[list[Problema], dict]:
    texto = caso.mutar(_texto_conforme()) if caso.mutar else _texto_conforme()
    return verificar_perfil_precedencia(texto)


def _bloque_de_las_dos_ausencias() -> list[tuple[str, bool, str]]:
    """[E] Las dos ausencias legítimas van **por separado**, y un solo caso no cubre a las dos.

    Que las dos resuelvan al default portable es cierto y no alcanza: si el modo no derivara la
    causa, retirar uno de los dos escenarios dejaría al otro tapando el hueco. Las tres direcciones
    lo muestran: con los dos, verde; sin uno, rojo nombrando **ese**; sin el otro, rojo nombrando el
    otro."""
    texto = _texto_conforme()
    resultados: list[tuple[str, bool, str]] = []
    problemas, resumen = verificar_perfil_precedencia(texto)
    resultados.append((
        "E1/perfil-precedencia", not problemas and resumen["ausencias_legitimas"] == 2,
        "el corpus ejerce las dos ausencias legítimas —sin asignación habiendo superficie y sin "
        "superficie alguna— y las dos caen al default portable"
        if not problemas and resumen["ausencias_legitimas"] == 2 else
        f"el conforme dio {resumen['ausencias_legitimas']} ausencias y {len(problemas)} problemas"))

    for i, causa in enumerate(CAUSAS_DE_AUSENCIA_LEGITIMA):
        mutado = _sin_escenario_de(causa)(texto)
        faltantes = [p for p in verificar_perfil_precedencia(mutado)[0]
                     if p.codigo == "escenario_de_ausencia_faltante"]
        solo_esa = len(faltantes) == 1 and causa in faltantes[0].mensaje
        resultados.append((
            f"E{i + 2}/perfil-precedencia", solo_esa,
            f"al retirar el escenario de `{causa}` se pone rojo por **ese** y no por el otro: el "
            "que queda no lo tapa"
            if solo_esa else
            f"al retirar `{causa}` se emitieron {len(faltantes)} faltantes: "
            f"{[p.mensaje[:60] for p in faltantes]}"))
    return resultados


def modo_autotest_perfil_precedencia() -> int:
    resultados = _preludio_de_t13()
    if all(ok for _, ok, _ in resultados):
        resultados += _bloque_de_documento(
            "perfil-precedencia", _casos_de_perfil_precedencia(), _correr_caso_de_precedencia,
            CODIGOS_PERFIL_PRECEDENCIA,
            lambda r: (f"evaluó {r['evaluados']} de {r['escenarios']} escenarios"
                       if r["evaluados"] != r["escenarios"] or not r["escenarios"] else
                       "ningún escenario resolvió inválido" if not r["invalidos"] else
                       f"ejerció {r['causas_de_ausencia']} de las "
                       f"{len(CAUSAS_DE_AUSENCIA_LEGITIMA)} causas de ausencia legítima"
                       if r["causas_de_ausencia"] != len(CAUSAS_DE_AUSENCIA_LEGITIMA) else ""))
        resultados += _bloque_de_las_dos_ausencias()
        resultados += _bloque_de_ausencia("perfil-precedencia", modo_perfil_precedencia)
    return _cierre("la precedencia se ejecuta contra su corpus: los tres inválidos fallan cerrado y "
                   "las dos ausencias legítimas caen al default portable por causas distintas",
                   resultados)


# --- Casos de `--roles` -----------------------------------------------------------------------

def _campo_de_familia(datos: dict, familia: str, campo: str) -> dict:
    return _de_lista(datos, "familias", "familia", familia)["campos"][campo]


def _mutantes_de_variante() -> tuple[CasoDeContrato, ...]:
    """Un mutante **por asignación**, no uno por categoría.

    Cada uno sustituye la variante de una fila por otra del mismo vocabulario —una que el propio
    mapa usa en otra fila—, así que ninguno se delata por inventar un token. Un representante por
    categoría convive con otras doce filas mal asignadas y el modo quedaría verde."""
    vocabulario = [a.variante for a in MAPA_DE_ASIGNACIONES]
    casos: list[CasoDeContrato] = []
    for i, asignacion in enumerate(MAPA_DE_ASIGNACIONES):
        otra = next(v for v in vocabulario[i + 1:] + vocabulario[:i] if v != asignacion.variante)
        casos.append(CasoDeContrato(
            "variante_no_coincide",
            f"`{asignacion.punto}` cambia su variante por `{otra[:40]}`",
            _en_json(SLUG_ASIGNACIONES,
                     lambda d, p=asignacion.punto, v=otra: (
                         _de_lista(d, "asignaciones", "punto", p).update({"variante": v}) or d))))
    return tuple(casos)


def _casos_de_roles() -> tuple[CasoDeContrato, ...]:
    def fam(mutacion: Any) -> Any:
        return _en_json(SLUG_FAMILIAS, mutacion)

    def asig(mutacion: Any) -> Any:
        return _en_json(SLUG_ASIGNACIONES, mutacion)

    def punto(datos: dict, nombre: str) -> dict:
        return _de_lista(datos, "asignaciones", "punto", nombre)

    con_puntero = next(a for a in MAPA_DE_ASIGNACIONES if a.procedencia == "puntero")
    con_decision = next(a for a in MAPA_DE_ASIGNACIONES if a.procedencia == "decision")

    return (
        # Los conformes. El primero trae la variante riesgosa que la task nombra: `diff-reviewer`
        # declara su scope **ausente y sin puntero**. La ausencia declarada es legítima y no todo
        # campo lleva puntero; un modo que exigiera puntero a todo caería acá.
        CasoDeContrato(None, "las cinco familias con sus campos —vigentes, observados, uno ausente "
                             "sin puntero y uno propuesto— y las trece asignaciones"),
        CasoDeContrato(
            None, "reordenar las asignaciones: el orden no es parte del mapa",
            asig(lambda d: (d["asignaciones"].append(d["asignaciones"].pop(0)) or d))),
        CasoDeContrato(
            None, "no-op: se reescribe prosa fuera de los bloques",
            _reemplazar_prosa("Un campo `ausente` declara su motivo",
                              "Un campo en estado `ausente` declara su motivo")),

        # Las cinco familias y su puntero normativo.
        CasoDeContrato("familias_ausentes", "el documento no declara la sección de familias",
                       _borrar_seccion(SLUG_FAMILIAS)),
        CasoDeContrato("bloque_ilegible", "el bloque de familias no parsea",
                       _romper_json(SLUG_FAMILIAS)),
        CasoDeContrato("familia_faltante", "el contrato pierde una de las cinco familias",
                       fam(lambda d: (d["familias"].remove(
                           _de_lista(d, "familias", "familia", "investigator")) or d))),
        CasoDeContrato("familia_de_mas", "el contrato estrena una sexta familia",
                       fam(lambda d: (d["familias"].append(
                           dict(_de_lista(d, "familias", "familia", "explorer"),
                                familia="surveyor")) or d))),
        CasoDeContrato("familia_duplicada", "una familia se declara dos veces",
                       fam(lambda d: (d["familias"].append(
                           copy.deepcopy(_de_lista(d, "familias", "familia", "explorer"))) or d))),
        CasoDeContrato("puntero_de_familia_ausente", "una familia no declara su puntero normativo",
                       fam(lambda d: (_de_lista(d, "familias", "familia", "explorer").pop("puntero")
                                      and d or d))),
        CasoDeContrato("puntero_de_familia_irresoluble",
                       "el puntero de una familia señala una sección que no existe",
                       fam(lambda d: (_de_lista(d, "familias", "familia", "explorer").update(
                           {"puntero": "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#no-existe"})
                           or d))),
        CasoDeContrato(
            "familia_ausente_en_la_sede",
            "el puntero de una familia resuelve a una sección real del roadmap que no la nombra",
            fam(lambda d: (_de_lista(d, "familias", "familia", "diff-reviewer").update(
                {"puntero": SEDE_SIN_LOS_LITERALES}) or d))),

        # Los campos y sus estados.
        CasoDeContrato("campo_ausente", "una familia no declara su scope",
                       fam(lambda d: (_de_lista(d, "familias", "familia",
                                                "explorer")["campos"].pop("scope") and d or d))),
        CasoDeContrato("estado_ausente", "un campo no declara su estado",
                       fam(lambda d: (_campo_de_familia(d, "explorer", "entrada").pop("estado")
                                      and d or d))),
        CasoDeContrato("estado_desconocido", "un campo declara un estado fuera del vocabulario",
                       fam(lambda d: (_campo_de_familia(d, "explorer", "entrada").update(
                           {"estado": "en_estudio"}) or d))),
        CasoDeContrato("campo_sin_valor", "un campo vigente no dice cuál es el valor vigente",
                       fam(lambda d: (_campo_de_familia(d, "explorer", "salida").pop("valor")
                                      and d or d))),
        CasoDeContrato("campo_sin_procedencia", "un campo vigente pierde su procedencia anclada",
                       fam(lambda d: (_campo_de_familia(d, "explorer", "salida").pop("procedencia")
                                      and d or d))),
        CasoDeContrato("procedencia_no_resuelve", "la sede de un campo anclado no existe",
                       fam(lambda d: (_campo_de_familia(
                           d, "explorer", "entrada")["procedencia"].update(
                               {"sede": "fuentes/no-existe.md"}) or d))),
        CasoDeContrato("ausente_sin_motivo", "el campo ausente no dice por qué no hay sede",
                       fam(lambda d: (_campo_de_familia(d, "diff-reviewer", "scope").pop("motivo")
                                      and d or d))),
        CasoDeContrato("propuesto_sin_fase", "el campo propuesto no dice para qué fase",
                       fam(lambda d: (_campo_de_familia(d, "investigator", "scope").pop("fase")
                                      and d or d))),
        CasoDeContrato(
            "procedencia_en_campo_no_anclado",
            "el campo ausente se ancla igual, contra la sede de otro campo",
            fam(lambda d: (_campo_de_familia(d, "diff-reviewer", "scope").update(
                {"procedencia": copy.deepcopy(
                    _campo_de_familia(d, "explorer", "scope")["procedencia"])}) or d))),
        CasoDeContrato(
            "autoridad_por_familia",
            "una familia declara su autoridad final, que va por punto y variante",
            fam(lambda d: (_de_lista(d, "familias", "familia", "explorer")["campos"].update(
                {"autoridad": {"estado": "vigente", "valor": "el conductor"}}) or d))),

        # Las tres sustituciones de AC-13 que solo el resolutor semántico puede ver: los tres valores
        # son plausibles, están bien escritos y la sede dice otra cosa.
        CasoDeContrato(
            "valor_no_coincide", "se sustituye la **entrada** de una familia por otra plausible",
            fam(lambda d: (_campo_de_familia(d, "explorer", "entrada").update(
                {"valor": "el diff a revisar y el contrato que ese diff dice cumplir"}) or d))),
        CasoDeContrato(
            "valor_no_coincide", "se sustituye la **salida** de una familia por otra plausible",
            fam(lambda d: (_campo_de_familia(d, "design-reviewer", "salida").update(
                {"valor": "el diff producido y el receipt de la corrida"}) or d))),
        CasoDeContrato(
            "valor_no_coincide", "se sustituye el **scope** de una familia por otro plausible",
            fam(lambda d: (_campo_de_familia(d, "bounded-implementer", "scope").update(
                {"valor": "lectura del árbol de trabajo; ninguna escritura"}) or d))),

        # El mapa de las trece asignaciones, por igualdad exacta.
        CasoDeContrato("asignaciones_ausentes", "el documento no declara la sección de asignaciones",
                       _borrar_seccion(SLUG_ASIGNACIONES)),
        CasoDeContrato("asignacion_faltante", "el mapa pierde una asignación",
                       asig(lambda d: (d["asignaciones"].remove(
                           punto(d, "sdd-flow · analyze")) or d))),
        CasoDeContrato("asignacion_de_mas", "el mapa estrena un punto de despacho que no existe",
                       asig(lambda d: (d["asignaciones"].append(
                           dict(copy.deepcopy(punto(d, "co-explore · debate")),
                                punto="co-explore · tercera ronda")) or d))),
        CasoDeContrato("punto_duplicado", "un punto se declara dos veces",
                       asig(lambda d: (d["asignaciones"].append(
                           copy.deepcopy(punto(d, "co-explore · debate"))) or d))),
        CasoDeContrato("familia_no_coincide", "una asignación cambia de familia de rol",
                       asig(lambda d: (punto(d, "sdd-flow · analyze").update(
                           {"familia": "investigator"}) or d))),
        *_mutantes_de_variante(),
        CasoDeContrato(
            "procedencia_no_coincide",
            "una fila decidida acá se declara derivada del roadmap",
            asig(lambda d: (punto(d, con_decision.punto).update({"procedencia": "puntero"}) or d))),
        CasoDeContrato("justificacion_ausente", "una fila decidida acá no dice por qué",
                       asig(lambda d: (punto(d, con_decision.punto).pop("justificacion")
                                       and d or d))),
        CasoDeContrato("puntero_de_variante_ausente",
                       "una fila derivada del roadmap no dice de dónde",
                       asig(lambda d: (punto(d, con_puntero.punto).pop("puntero_variante")
                                       and d or d))),
        CasoDeContrato("puntero_de_variante_irresoluble",
                       "el puntero de una variante señala una sección que no existe",
                       asig(lambda d: (punto(d, con_puntero.punto).update(
                           {"puntero_variante":
                            "docs/superpowers/plans/2026-08-09-subagentes-siete-skills.md#no-existe"}) or d))),
        CasoDeContrato(
            "variante_ausente_en_la_sede",
            "el puntero de una variante resuelve a una sección real que no la nombra",
            asig(lambda d: (punto(d, con_puntero.punto).update(
                {"puntero_variante": SEDE_SIN_LOS_LITERALES}) or d))),
        CasoDeContrato("forma_de_resultado_ausente", "una asignación no declara su forma de "
                                                     "resultado",
                       asig(lambda d: (punto(d, "co-explore · debate").pop("forma_de_resultado")
                                       and d or d))),
        CasoDeContrato("declaracion_de_salida_ausente",
                       "una asignación no declara su contrato de salida",
                       asig(lambda d: (punto(d, "co-explore · debate").pop("declaracion_de_salida")
                                       and d or d))),
        CasoDeContrato("autoridad_ausente", "una asignación no declara su autoridad final",
                       asig(lambda d: (punto(d, "co-explore · debate").pop("autoridad")
                                       and d or d))),
        CasoDeContrato(
            "valor_no_coincide",
            "se sustituye la **autoridad** de un punto por la de otro, que es plausible y está "
            "anclada en la misma sede",
            asig(lambda d: (punto(d, "co-explore · debate")["autoridad"].update(
                {"valor": "el conductor arbitra entre los dos mapas y no produce uno propio"})
                or d))),
        CasoDeContrato(
            "salida_compartida_entre_formas_distintas",
            "dos variantes cuyo resultado tiene forma distinta pasan a compartir declaración de "
            "salida",
            asig(lambda d: (punto(d, "co-explore · debate").update(
                {"declaracion_de_salida": punto(
                    d, "cross-review · revisor por ronda")["declaracion_de_salida"]}) or d))),
    )


def _correr_caso_de_roles(caso: CasoDeContrato) -> tuple[list[Problema], dict]:
    """Dos raíces, y no es un descuido. Las procedencias de los campos de rol son **sintéticas** y
    viven en el corpus; los punteros de las cinco familias y de las ocho variantes son **normativos**
    y se resuelven contra el árbol real. Con un árbol sintético, el inventario probaría que el modo
    sabe leer JSON y nada más."""
    texto = caso.mutar(_texto_conforme()) if caso.mutar else _texto_conforme()
    return verificar_roles(texto, CONFORME_CONTRATO, REPO)


def _bloque_por_asignacion() -> list[tuple[str, bool, str]]:
    """[E] Los mutantes de variante son **uno por asignación** y cada uno nombra la suya.

    Que los trece den rojo no alcanza: si todos cayeran nombrando la misma fila, doce asignaciones
    estarían sin cubrir y el bloque B —que solo mira el código— no lo vería."""
    fallas: list[str] = []
    for caso in _mutantes_de_variante():
        try:
            problemas, _ = _correr_caso_de_roles(caso)
        except ValueError as exc:
            fallas.append(f"{caso.descripcion} — no corrió: {exc}")
            continue
        propios = [p for p in problemas if p.codigo == "variante_no_coincide"]
        esperado = caso.descripcion.split("`")[1]
        if len(propios) != 1 or esperado not in propios[0].donde:
            fallas.append(f"{esperado} — cayeron {[p.donde for p in propios]}")
    return [("E/roles", not fallas,
             f"los {len(MAPA_DE_ASIGNACIONES)} mutantes de variante caen de a uno y cada uno nombra "
             "su propia fila"
             if not fallas else f"{len(fallas)} problemas: " + " | ".join(fallas[:3]))]


def modo_autotest_roles() -> int:
    resultados = _preludio_de_roles()
    if all(ok for _, ok, _ in resultados):
        resultados += _bloque_de_documento(
            "roles", _casos_de_roles(), _correr_caso_de_roles, CODIGOS_ROLES,
            lambda r: (f"leyó {r['familias']} de {len(FAMILIAS_DE_ROL)} familias y "
                       f"{r['asignaciones']} de {len(MAPA_DE_ASIGNACIONES)} asignaciones: no "
                       "recorrió el documento"
                       if r["familias"] != len(FAMILIAS_DE_ROL)
                       or r["asignaciones"] != len(MAPA_DE_ASIGNACIONES) else
                       f"resolvió {r['campos_resueltos']} de {r['campos_anclados']} campos anclados"
                       if r["campos_resueltos"] != r["campos_anclados"] or not r["campos_anclados"]
                       else f"resolvió {r['punteros_de_familia']} punteros de familia"
                       if r["punteros_de_familia"] != len(FAMILIAS_DE_ROL) else
                       "no resolvió ningún puntero de variante"
                       if not r["punteros_de_variante"] else ""))
        resultados += _bloque_por_asignacion()
        resultados += _bloque_de_ausencia(
            "roles", lambda ruta: modo_roles(ruta, CONFORME_CONTRATO, REPO))
    return _cierre("las cinco familias se derivan del roadmap con puntero por literal, sus campos "
                   "vigentes resuelven con el verificador semántico de la matriz, y las trece "
                   "asignaciones coinciden por igualdad exacta con el mapa congelado", resultados)

# --- Casos de `--diversidad` ------------------------------------------------------------------

def _casos_de_diversidad() -> tuple[CasoDeContrato, ...]:
    def en(mutacion: Any) -> Any:
        return _en_json(SLUG_DIVERSIDAD, mutacion)

    def intento(datos: dict, ident: str) -> dict:
        return _de_lista(datos, "intentos", "id", ident)

    def contradecir(datos: dict) -> dict:
        """Cambia **un registro** y deja la topología declarada intacta. Es el fixture que la task
        pide: un modo que clasificara bien las relaciones pero leyera el agregado de la declaración
        pasaría igual."""
        uno = intento(datos, "I-02")
        uno["worker"] = "codex"
        uno["relaciones"]["worker_vs_conductor"] = "cross_family"
        uno["relaciones"]["worker_vs_autor"] = "same_family"
        uno["cuenta_como_evidencia_independiente"] = False
        return datos

    return (
        # Los conformes. `I-03` es la variante riesgosa: un resultado `same_family` **presente** y
        # correctamente excluido del conteo. Estar presente no es el defecto; contarlo sí.
        CasoDeContrato(None, "cuatro intentos con sus tres identidades, sus relaciones, la topología "
                             "derivada y un `same_family` presente y excluido"),
        CasoDeContrato(
            None, "reordenar los intentos: la topología no depende del orden",
            en(lambda d: (d["intentos"].append(d["intentos"].pop(0)) or d))),
        CasoDeContrato(
            None, "no-op: se reescribe prosa fuera del bloque",
            _reemplazar_prosa("La topología agregada de la corrida se",
                              "La topología agregada de toda la corrida se")),

        # La estructura de la sección.
        CasoDeContrato("diversidad_ausente", "el documento no declara la sección",
                       _borrar_seccion(SLUG_DIVERSIDAD)),
        CasoDeContrato("bloque_ilegible", "el bloque declara una lista",
                       en(lambda d: [d])),
        CasoDeContrato("intentos_ausentes", "la política no registra ningún intento",
                       en(lambda d: (d.update({"intentos": []}) or d))),
        CasoDeContrato("intento_no_objeto", "un intento se declara como texto",
                       en(lambda d: (d["intentos"].append("la corrida del jueves") or d))),
        CasoDeContrato("intento_id_duplicado", "dos intentos comparten identificador",
                       en(lambda d: (intento(d, "I-02").update({"id": "I-01"}) or d))),

        # Las tres identidades y las relaciones derivadas de ellas.
        CasoDeContrato("intento_sin_identidad",
                       "un intento no registra quién escribió el artefacto que juzga",
                       en(lambda d: (intento(d, "I-02").pop("autor_del_artefacto") and d or d))),
        CasoDeContrato("familia_desconocida", "una identidad fuera de las dos familias",
                       en(lambda d: (intento(d, "I-01").update({"worker": "familia-tercera"})
                                     or d))),
        CasoDeContrato("relacion_ausente", "un intento no registra sus relaciones",
                       en(lambda d: (intento(d, "I-01").pop("relaciones") and d or d))),
        CasoDeContrato("relacion_desconocida", "una relación fuera del vocabulario",
                       en(lambda d: (intento(d, "I-01")["relaciones"].update(
                           {"worker_vs_autor": "parcialmente_cruzada"}) or d))),
        CasoDeContrato(
            "relacion_no_coincide",
            "una relación se registra `same_family` y las identidades dicen `cross_family`",
            en(lambda d: (intento(d, "I-01")["relaciones"].update(
                {"worker_vs_autor": "same_family"}) or d))),

        # La regla de evidencia independiente, en sus tres direcciones.
        CasoDeContrato("independencia_omitida",
                       "un intento no dice si cuenta como evidencia independiente",
                       en(lambda d: (intento(d, "I-01").pop(
                           "cuenta_como_evidencia_independiente") and d or d))),
        CasoDeContrato(
            "independiente_de_una_sola_familia",
            "se cuenta como independiente un resultado cuyo trabajo delegado es de la misma familia "
            "que el autor del artefacto",
            en(lambda d: (intento(d, "I-03").update(
                {"cuenta_como_evidencia_independiente": True}) or d))),
        CasoDeContrato(
            "independiente_de_una_sola_voz",
            "se cuenta como independiente un resultado en el que conducen, escriben y trabajan la "
            "misma familia",
            en(lambda d: (intento(d, "I-04").update(
                {"cuenta_como_evidencia_independiente": True}) or d))),
        CasoDeContrato(
            "independencia_negada",
            "se descarta un resultado que sí es independiente: la regla también dice qué cuenta",
            en(lambda d: (intento(d, "I-01").update(
                {"cuenta_como_evidencia_independiente": False}) or d))),

        # La topología, en las dos direcciones.
        CasoDeContrato("topologia_ausente", "la política no declara su topología agregada",
                       en(lambda d: (d.pop("topologia") and d or d))),
        CasoDeContrato(
            "topologia_contradice_registros",
            "la topología declarada dice un cruce más de los que sus registros producen",
            en(lambda d: (d["topologia"].update(
                {"cross_vs_autor": d["topologia"]["cross_vs_autor"] + 1}) or d))),
        CasoDeContrato(
            "topologia_contradice_registros",
            "cambia **un registro** y la topología declarada queda intacta: un modo que la leyera "
            "en vez de derivarla pasaría",
            en(contradecir)),
    )


def _correr_caso_de_diversidad(caso: CasoDeContrato) -> tuple[list[Problema], dict]:
    texto = caso.mutar(_texto_conforme()) if caso.mutar else _texto_conforme()
    return verificar_diversidad(texto)


def _bloque_de_la_topologia_derivada() -> list[tuple[str, bool, str]]:
    """[E] La topología se **deriva** de los registros, y las dos direcciones lo muestran.

    Solo la primera la satisface un modo que leyera el agregado declarado; solo la segunda, uno que
    lo ignorara y nunca lo comparara. Y el corpus tiene que ser no trivial: con cuatro intentos
    idénticos, «coincide» sería cierto para cualquier derivación."""
    texto = _texto_conforme()
    datos, _ = _bloque_json(texto, SLUG_DIVERSIDAD)
    problemas, resumen = verificar_diversidad(texto)
    variado = (isinstance(datos, dict) and isinstance(datos.get("topologia"), dict)
               and 0 < datos["topologia"].get("single_voice", 0) < resumen["intentos"]
               and 0 < datos["topologia"].get("evidencia_independiente", 0) < resumen["intentos"])

    def codigos(mutacion: Any) -> set[str]:
        return {p.codigo for p in verificar_diversidad(_en_json(SLUG_DIVERSIDAD, mutacion)(texto))[0]}

    solo_declarada = codigos(lambda d: (d["topologia"].update(
        {"single_voice": d["topologia"]["single_voice"] + 1}) or d))
    solo_registro = codigos(lambda d: (
        _de_lista(d, "intentos", "id", "I-02").update({"worker": "codex"})
        or _de_lista(d, "intentos", "id", "I-02")["relaciones"].update(
            {"worker_vs_conductor": "cross_family", "worker_vs_autor": "same_family"})
        or _de_lista(d, "intentos", "id", "I-02").update(
            {"cuenta_como_evidencia_independiente": False})
        or d))

    return [
        ("E1/diversidad", not problemas and variado and resumen["topologia_comparada"] == 1,
         f"el corpus registra {resumen['intentos']} intentos con topología no trivial "
         f"({resumen['single_voice']} de una sola voz, {resumen['independientes']} independientes) y "
         "la declarada coincide con la derivada"
         if not problemas and variado else
         f"el conforme dio {len(problemas)} problemas o su topología es trivial: {variado}"),
        ("E2/diversidad", solo_declarada == {"topologia_contradice_registros"},
         "al mover un contador de la topología declarada sin tocar los registros se pone rojo, y "
         "solo por eso"
         if solo_declarada == {"topologia_contradice_registros"} else
         f"mover la declarada emitió {sorted(solo_declarada)}"),
        ("E3/diversidad", solo_registro == {"topologia_contradice_registros"},
         "y al mover **un registro** dejando la topología declarada intacta también, que es la "
         "dirección que un modo que la leyera en vez de derivarla no vería"
         if solo_registro == {"topologia_contradice_registros"} else
         f"mover un registro emitió {sorted(solo_registro)}"),
    ]


def modo_autotest_diversidad() -> int:
    resultados = _preludio_de_t13()
    if all(ok for _, ok, _ in resultados):
        resultados += _bloque_de_documento(
            "diversidad", _casos_de_diversidad(), _correr_caso_de_diversidad, CODIGOS_DIVERSIDAD,
            lambda r: (f"leyó {r['intentos']} intentos: no recorrió la política"
                       if not r["intentos"] else
                       f"derivó {r['relaciones_derivadas']} relaciones para {r['intentos']} intentos "
                       "y son dos por intento"
                       if r["relaciones_derivadas"] != 2 * r["intentos"] else
                       "no comparó la topología derivada contra la declarada"
                       if not r["topologia_comparada"] else
                       "ningún resultado contó como evidencia independiente"
                       if not r["independientes"] else
                       "ningún intento fue de una sola voz, así que esa mitad de la regla no se "
                       "ejerció" if not r["single_voice"] else ""))
        resultados += _bloque_de_la_topologia_derivada()
        resultados += _bloque_de_ausencia("diversidad", modo_diversidad)
    return _cierre("por intento se registran las tres identidades y sus relaciones, la topología se "
                   "deriva de esos registros y la evidencia independiente es una regla ejecutable",
                   resultados)


# --- Casos de `--defectos` --------------------------------------------------------------------

def _casos_de_defectos() -> tuple[CasoDeContrato, ...]:
    def en(mutacion: Any) -> Any:
        return _en_json(SLUG_DEFECTOS, mutacion)

    def defecto(datos: dict, ident: str) -> dict:
        return _de_lista(datos, "defectos", "id", ident)

    septimo = {
        "id": "presupuesto-por-defecto-sin-sede-canonica",
        "descripcion": "el presupuesto de espera por defecto que ninguna sede declara",
        "ubicacion": "sintetico/presupuestos-del-corpus.md#espera-por-defecto",
        "naturaleza": "documental: el valor aparece en tres sitios y ninguno se declara canónico",
        "fase": "Fase 1",
    }
    reemplazo = dict(septimo, id="otra-cosa-que-tambien-esta-mal")

    return (
        # Los conformes. El segundo es el que la task exige: **el mínimo de seis no es un conjunto
        # cerrado**, y un modo que exigiera exactamente esos seis rechazaría un inventario más
        # completo que el exigido.
        CasoDeContrato(None, "los seis defectos mínimos con su ubicación, naturaleza y fase"),
        CasoDeContrato(None, "un séptimo defecto bien formado: acepta más",
                       en(lambda d: (d["defectos"].append(septimo) or d))),
        CasoDeContrato(
            None, "no-op: se reescribe prosa fuera del bloque",
            _reemplazar_prosa("Puede contener más y no menos.",
                              "Puede contener más, y no menos.")),

        # El mínimo, comparado por identidad.
        CasoDeContrato("defectos_ausentes", "el documento no declara la sección",
                       _borrar_seccion(SLUG_DEFECTOS)),
        CasoDeContrato("bloque_ilegible", "el bloque declara una lista",
                       en(lambda d: [d])),
        CasoDeContrato("defectos_ausentes", "el inventario se queda sin defectos",
                       en(lambda d: (d.update({"defectos": []}) or d))),
        CasoDeContrato(
            "defecto_minimo_faltante",
            "uno de los seis se cambia por otro **conservando el total**: es lo que un "
            "`len(defectos) >= 6` no ve",
            en(lambda d: (d["defectos"].__setitem__(
                d["defectos"].index(defecto(d, DEFECTOS_MINIMOS[2].identidad)), reemplazo) or d))),
        CasoDeContrato("defecto_no_objeto", "un defecto se declara como texto",
                       en(lambda d: (d["defectos"].append("falta algo en el manifest") or d))),
        CasoDeContrato("defecto_sin_identidad", "un defecto no declara su identidad",
                       en(lambda d: (defecto(d, DEFECTOS_MINIMOS[0].identidad).pop("id")
                                     and d or d))),
        CasoDeContrato("defecto_id_duplicado", "dos defectos comparten identidad",
                       en(lambda d: (d["defectos"].append(
                           dict(septimo, id=DEFECTOS_MINIMOS[0].identidad)) or d))),
        CasoDeContrato("defecto_sin_campo", "un defecto no declara su ubicación",
                       en(lambda d: (defecto(d, DEFECTOS_MINIMOS[1].identidad).pop("ubicacion")
                                     and d or d))),
        CasoDeContrato("defecto_sin_campo", "un defecto no declara su naturaleza",
                       en(lambda d: (defecto(d, DEFECTOS_MINIMOS[3].identidad).pop("naturaleza")
                                     and d or d))),
        CasoDeContrato("defecto_sin_campo", "un defecto no declara su fase de corrección",
                       en(lambda d: (defecto(d, DEFECTOS_MINIMOS[4].identidad).pop("fase")
                                     and d or d))),
        CasoDeContrato("ubicacion_sin_forma", "una ubicación que no ubica nada",
                       en(lambda d: (defecto(d, DEFECTOS_MINIMOS[5].identidad).update(
                           {"ubicacion": "en las instrucciones del repositorio"}) or d))),
    )


def _correr_caso_de_defectos(caso: CasoDeContrato) -> tuple[list[Problema], dict]:
    texto = caso.mutar(_texto_conforme()) if caso.mutar else _texto_conforme()
    return verificar_defectos(texto)


def _bloque_del_minimo_por_identidad() -> list[tuple[str, bool, str]]:
    """[E] «Al menos seis» se comprueba por identidad y no por cantidad.

    Las tres direcciones: con los seis pasa; con siete también —el mínimo no cierra el conjunto—; y
    con seis de los cuales uno fue sustituido, se pone rojo. Solo la tercera separa la comparación
    por identidad de un `len(defectos) >= 6`, que satisface las otras dos."""
    casos = _casos_de_defectos()
    conforme = _correr_caso_de_defectos(casos[0])
    con_septimo = _correr_caso_de_defectos(casos[1])
    sustituido = next(c for c in casos if c.codigo == "defecto_minimo_faltante")
    problemas_sust, resumen_sust = _correr_caso_de_defectos(sustituido)
    codigos = {p.codigo for p in problemas_sust}
    return [
        ("E1/defectos", not conforme[0] and conforme[1]["defectos"] == len(DEFECTOS_MINIMOS),
         f"el conforme registra exactamente los {len(DEFECTOS_MINIMOS)} mínimos y pasa"
         if not conforme[0] else f"el conforme falló: {conforme[0][0]}"),
        ("E2/defectos", not con_septimo[0]
         and con_septimo[1]["defectos"] == len(DEFECTOS_MINIMOS) + 1,
         f"con un séptimo bien formado sigue pasando y cuenta {con_septimo[1]['defectos']}: el "
         "mínimo no es un conjunto cerrado"
         if not con_septimo[0] else f"el séptimo lo puso rojo: {con_septimo[0][0]}"),
        ("E3/defectos",
         codigos == {"defecto_minimo_faltante"}
         and resumen_sust["defectos"] == len(DEFECTOS_MINIMOS),
         f"y al sustituir uno de los seis por otro el total sigue en {resumen_sust['defectos']} y se "
         "pone rojo igual: un conteo lo dejaría pasar"
         if codigos == {"defecto_minimo_faltante"} else
         f"la sustitución emitió {sorted(codigos)} con total {resumen_sust['defectos']}"),
    ]


def modo_autotest_defectos() -> int:
    resultados = _preludio_de_t13()
    if all(ok for _, ok, _ in resultados):
        resultados += _bloque_de_documento(
            "defectos", _casos_de_defectos(), _correr_caso_de_defectos, CODIGOS_DEFECTOS,
            lambda r: (f"leyó {r['defectos']} defectos: no recorrió el inventario"
                       if not r["defectos"] else
                       f"encontró {r['minimos_presentes']} de los {len(DEFECTOS_MINIMOS)} mínimos"
                       if r["minimos_presentes"] != len(DEFECTOS_MINIMOS) else ""))
        resultados += _bloque_del_minimo_por_identidad()
        resultados += _bloque_de_ausencia("defectos", modo_defectos)
    return _cierre(f"el inventario registra al menos los {len(DEFECTOS_MINIMOS)} defectos mínimos "
                   "comparados por identidad, cada uno con su ubicación, su naturaleza y su fase",
                   resultados)


# --- Los dos preludios ------------------------------------------------------------------------

def _preludio_de_t13() -> list[tuple[str, bool, str]]:
    """Lo que tiene que valer antes de correr un caso de cualquiera de los cinco modos."""
    resultados = _preludio_del_corpus()
    if not all(ok for _, ok, _ in resultados):
        return resultados
    contenedor = contenedor_del_perfil()
    if contenedor.error or not contenedor.clave_raiz:
        return resultados + [("0.contenedor", False,
                              f"no se pudo derivar la forma del contenedor de perfiles de "
                              f"{RUTA_NOMBRES_RESERVADOS.name}: {contenedor.error}")]
    resultados.append((
        "0.contenedor", len(contenedor.obligatorios) == 5 and len(contenedor.parametros) == 2,
        f"la forma del contenedor sale de {RUTA_NOMBRES_RESERVADOS.name}: raíz "
        f"`{contenedor.clave_raiz}`, {len(contenedor.obligatorios)} componentes obligatorios y una "
        f"lista blanca de {len(contenedor.parametros)} parámetros "
        f"({', '.join('`' + p + '`' for p in contenedor.parametros)})"
        if len(contenedor.obligatorios) == 5 and len(contenedor.parametros) == 2 else
        f"la lista declara {len(contenedor.obligatorios)} componentes obligatorios y "
        f"{len(contenedor.parametros)} parámetros de runtime; el criterio pide cinco y dos"))
    resultados.append((
        "0.sede", SEDE_DE_ROL.is_file(),
        f"está la sede sintética de las procedencias de rol ({SEDE_DE_ROL.name})"
        if SEDE_DE_ROL.is_file() else f"falta {SEDE_DE_ROL}"))
    return resultados


def _preludio_de_roles() -> list[tuple[str, bool, str]]:
    """El bloque que sostiene el modo de roles, y que separa lo derivado de lo decidido.

    **Las cinco familias se derivan**: si una se la hubiera inventado esta task, no habría sección
    del roadmap donde encontrarla. **El mapa no**: es una decisión escrita, y lo único que se puede
    comprobar de él es que el fixture no divergió del inventario congelado y que las ocho filas que
    dicen derivar su variante del roadmap efectivamente la tienen ahí."""
    resultados = _preludio_de_t13()
    if not all(ok for _, ok, _ in resultados):
        return resultados

    fallas = [f"{f} — `{SEDE_DE_LAS_FAMILIAS}`: {_resolver_puntero(SEDE_DE_LAS_FAMILIAS, f, REPO)}"
              for f in FAMILIAS_DE_ROL if _resolver_puntero(SEDE_DE_LAS_FAMILIAS, f, REPO)]
    resultados.append((
        "0.familias", not fallas,
        f"las {len(FAMILIAS_DE_ROL)} familias de rol resuelven contra la tabla real del roadmap y "
        "aparecen ahí, así que no las inventó esta task"
        if not fallas else f"{len(fallas)} familias sin respaldo: " + " | ".join(fallas)))

    con_puntero = [a for a in MAPA_DE_ASIGNACIONES if a.procedencia == "puntero"]
    sin_respaldo = [f"{a.punto} → `{a.variante}`" for a in con_puntero
                    if _resolver_puntero(SEDE_DE_LAS_FAMILIAS, a.variante, REPO)]
    resultados.append((
        "0.variantes", not sin_respaldo and len(con_puntero) < len(MAPA_DE_ASIGNACIONES),
        f"{len(con_puntero)} de las {len(MAPA_DE_ASIGNACIONES)} asignaciones dicen derivar su "
        f"variante del roadmap y las {len(con_puntero)} aparecen ahí; las otras "
        f"{len(MAPA_DE_ASIGNACIONES) - len(con_puntero)} se marcan decisión, que es lo que son"
        if not sin_respaldo and len(con_puntero) < len(MAPA_DE_ASIGNACIONES) else
        f"{len(sin_respaldo)} variantes marcadas puntero sin respaldo: "
        + " | ".join(sin_respaldo[:4])))

    # El fixture no puede divergir del mapa congelado: si divergiera, el control positivo del modo
    # estaría midiendo otra cosa que la que la fila declara.
    texto = _texto_conforme()
    declaradas, motivo = _bloque_json(texto, SLUG_ASIGNACIONES)
    if motivo or not isinstance(declaradas, dict):
        resultados.append(("0.mapa", False, motivo or "el bloque de asignaciones no es un objeto"))
        return resultados
    del_fixture = sorted(
        (str(f.get("punto")), str(f.get("familia")), str(f.get("variante")),
         str(f.get("procedencia")))
        for f in declaradas.get("asignaciones", []) if isinstance(f, dict))
    congelado = sorted(tuple(a) for a in MAPA_DE_ASIGNACIONES)
    resultados.append((
        "0.mapa", del_fixture == congelado,
        f"el fixture declara exactamente las {len(congelado)} asignaciones congeladas, fila por fila"
        if del_fixture == congelado else
        f"el fixture divergió del mapa: {sorted(set(del_fixture) ^ set(congelado))[:2]}"))
    return resultados


# --- Modos `--guardas` y `--autotest-guardas` -------------------------------------------------
#
# La no-regresión de este flujo comparaba **listas escritas contra listas escritas**: una invocación
# podía figurar en el contrato y no ejecutarse nunca, y nada lo habría notado. Este modo cierra esa
# forma de falso verde con tres piezas que se comprueban por separado:
#
# 1. **El manifiesto contra las instrucciones, por identidad y en las dos direcciones.** El conjunto
#    documentado NO se transcribe: se deriva del texto de las instrucciones (`CLAUDE.md`) leyendo
#    sus unidades de guarda, y lo único congelado es el **criterio de extracción**. Un inventario
#    transcrito queda falso en cuanto el árbol cambia; un criterio congelado, no.
# 2. **La ejecución**, que produce un recibo con qué corrió, con qué código y qué se concluyó.
# 3. **El recibo contra el manifiesto, también por igualdad y no por inclusión.** Correr de más no
#    es correr bien: una ejecución ajena al manifiesto es tan rojo como una declarada que falta.
#    Con `declarado ⊆ ejercido` los tres mutantes del recibo no cazarían nada.

RUTA_MANIFIESTO_GUARDAS = REPO / "scripts" / "guardas-fase-0.json"
RUTA_INSTRUCCIONES = REPO / "CLAUDE.md"

CRITERIO_CODIGO = "codigo_de_salida"
CRITERIO_CUERPO = "cuerpo_del_reporte"
CRITERIOS_DE_GUARDA = (CRITERIO_CODIGO, CRITERIO_CUERPO)

ORIGEN_NEGADO = "negado_en_instrucciones"
ORIGEN_MANIFIESTO = "excluido_por_el_manifiesto"
ORIGENES_DE_EXCLUSION = (ORIGEN_NEGADO, ORIGEN_MANIFIESTO)

# El criterio de extracción, congelado; el dato que produce, derivado del texto de cada corrida.
PATRON_UNIDAD = re.compile(r"^-\s+\S")
PATRON_SPAN = re.compile(r"`([^`]+)`")
PATRON_COMANDO = re.compile(r"^python3\s+(scripts/[A-Za-z0-9._-]+\.py)\s*(.*)$")
PATRON_SOLO_BANDERAS = re.compile(r"^--[a-z0-9-]+\*?(?:\s+[^\s`]+)*$")
PATRON_MARCA = re.compile(r"\x00(\d+)\x00")
PATRON_ADD_ARGUMENT = re.compile(r"add_argument\(\s*\"(--[a-z0-9-]+)\"")

# Una negación alcanza a las banderas que la **anteceden en su oración**. La regla no es cosmética:
# hoy la oración que declara que cuatro banderas no son guardas termina nombrando `--reporte`, que
# sí lo es. Una negación por oración entera lo borraría del conjunto y el modo quedaría verde con
# una guarda menos.
FRASES_DE_NEGACION = ("cuenta como guarda", "son guardas", "es una guarda", "es guarda")
CUES_DE_NEGACION = tuple(
    re.compile(r"\bno\W+" + r"\W+".join(re.escape(p) for p in frase.split()), re.IGNORECASE)
    for frase in FRASES_DE_NEGACION)


class Invocacion(NamedTuple):
    script: str                      # ruta relativa desde la raíz del repo
    argumentos: tuple[str, ...]

    @property
    def identidad(self) -> str:
        return " ".join((self.script,) + self.argumentos)

    def comando(self) -> list[str]:
        return [sys.executable, self.script, *self.argumentos]


def _invocacion_de(datos: Any) -> Invocacion | None:
    if not isinstance(datos, dict):
        return None
    script = _texto_o_vacio(datos.get("script"))
    argumentos = datos.get("argumentos")
    if not script or not isinstance(argumentos, list):
        return None
    if any(not isinstance(a, str) for a in argumentos):
        return None
    return Invocacion(script, tuple(argumentos))


def banderas_declaradas(ruta: Path) -> tuple[frozenset[str], str]:
    """Las banderas que el parser de un verificador declara, leídas de su fuente.

    Se derivan y no se transcriben: la familia `--autotest-*` de las instrucciones se expande contra
    esto, así que un autotest nuevo en el arnés entra al conjunto solo. Un verificador sin parser
    —`verificar-vistas-config.py` no tiene ninguno— devuelve el conjunto vacío, que es la respuesta
    correcta y no un error."""
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError as e:
        return frozenset(), f"no se pudo leer {ruta}: {e}"
    return frozenset(PATRON_ADD_ARGUMENT.findall(texto)), ""


def unidades_de_guarda(texto: str) -> list[str]:
    """Cada ítem de primer nivel de las instrucciones, con lo que le cuelga indentado.

    El bloque `>` que sigue a un ítem indentado es parte del ítem: ahí viven nueve de las
    veintiuna invocaciones de hoy. Una línea que arranca en la columna 0 y no es ítem cierra la
    unidad."""
    unidades: list[str] = []
    actual: list[str] | None = None
    for linea in texto.splitlines():
        if PATRON_UNIDAD.match(linea):
            if actual is not None:
                unidades.append("\n".join(actual))
            actual = [linea]
            continue
        if actual is None:
            continue
        if not linea.strip() or linea[0].isspace():
            actual.append(linea)
            continue
        unidades.append("\n".join(actual))
        actual = None
    if actual is not None:
        unidades.append("\n".join(actual))
    return unidades


def _enmascarar(texto: str) -> tuple[str, list[str]]:
    """Sustituye cada span entre backticks por una marca de posición fija.

    Sin esto, cortar en oraciones parte `scripts/x.py` a la mitad: los puntos de las rutas y las
    extensiones son mayoría dentro de los spans y ninguno cierra una oración."""
    spans: list[str] = []

    def reemplazar(m: re.Match) -> str:
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    return PATRON_SPAN.sub(reemplazar, texto), spans


def _spans_negados(mascara: str) -> set[int]:
    oraciones: list[tuple[int, int]] = []
    inicio = 0
    for m in re.finditer(r"\.(?:\s|$)", mascara):
        oraciones.append((inicio, m.end()))
        inicio = m.end()
    if inicio < len(mascara):
        oraciones.append((inicio, len(mascara)))
    negados: set[int] = set()
    for a, b in oraciones:
        frase = mascara[a:b]
        posiciones = [m.start() for cue in CUES_DE_NEGACION for m in cue.finditer(frase)]
        if not posiciones:
            continue
        for m in PATRON_MARCA.finditer(frase[:min(posiciones)]):
            negados.add(int(m.group(1)))
    return negados


def derivar_invocaciones_documentadas(
        texto: str, raiz: Path) -> tuple[set[Invocacion], set[Invocacion], list[Problema]]:
    """El conjunto que las instrucciones documentan, y el que documentan **negándolo**.

    Cuatro reglas, todas congeladas acá y ninguna con su resultado escrito:

    - un span que empieza por `python3 scripts/<x>.py` fija el script de la unidad y, si trae
      banderas, es una invocación; un span de solo banderas hereda ese script;
    - la forma **pelada** (el script sin banderas) es invocación solo si la unidad no nombra
      ninguna bandera para ese script: en la unidad del retiro el span pelado es el prefijo de las
      siete que siguen, no una guarda más;
    - un span con marcador de posición (`<nombre>`) no es una invocación fija y por lo tanto no es
      una guarda: es una plantilla que alguien completa;
    - una familia (`--autotest-*`) se expande contra las banderas que el parser de ese script
      declara. La expansión vacía es un problema, no un conjunto vacío."""
    documentadas: set[Invocacion] = set()
    negadas: set[Invocacion] = set()
    problemas: list[Problema] = []
    for unidad in unidades_de_guarda(texto):
        mascara, spans = _enmascarar(unidad)
        script_de_la_unidad = ""
        for span in spans:
            m = PATRON_COMANDO.match(span)
            if m:
                script_de_la_unidad = m.group(1)
                break
        if not script_de_la_unidad:
            continue
        negados = _spans_negados(mascara)
        candidatos: list[tuple[int, Invocacion]] = []
        for i, span in enumerate(spans):
            if "<" in span and ">" in span:
                continue
            m = PATRON_COMANDO.match(span)
            if m:
                candidatos.append((i, Invocacion(m.group(1), tuple(m.group(2).split()))))
                continue
            if PATRON_SOLO_BANDERAS.match(span):
                candidatos.append((i, Invocacion(script_de_la_unidad, tuple(span.split()))))
        con_banderas = {inv.script for _, inv in candidatos if inv.argumentos}
        candidatos = [(i, inv) for i, inv in candidatos
                      if inv.argumentos or inv.script not in con_banderas]
        for i, inv in candidatos:
            destino = negadas if i in negados else documentadas
            if len(inv.argumentos) == 1 and inv.argumentos[0].endswith("*"):
                prefijo = inv.argumentos[0][:-1]
                declaradas, error = banderas_declaradas(raiz / inv.script)
                if error:
                    problemas.append(Problema("familia_sin_parser", f"`{inv.identidad}`", error))
                    continue
                expandida = sorted(f for f in declaradas if f.startswith(prefijo))
                if not expandida:
                    problemas.append(Problema(
                        "familia_vacia", f"`{inv.identidad}`",
                        f"el parser de `{inv.script}` no declara ninguna bandera que empiece por "
                        f"`{prefijo}`: la familia documentada no expande a nada"))
                    continue
                for bandera in expandida:
                    destino.add(Invocacion(inv.script, (bandera,)))
                continue
            destino.add(inv)
    # La misma invocación documentada **y** negada no se resuelve por unión: la unión la deja
    # documentada en silencio y borra que el texto se contradice. Medido: con la negación aplicada a
    # la oración entera en vez de a lo que la antecede, `--reporte` cae en los dos conjuntos y todo
    # lo demás sigue igual —aparece dos veces en su unidad—, así que sin este chequeo la regla de
    # alcance no tiene mutante que la ponga roja.
    for inv in sorted(documentadas & negadas):
        problemas.append(Problema(
            "invocacion_ambigua", f"`{inv.identidad}`",
            "las instrucciones la documentan como ejecutable y la niegan como guarda; el texto no "
            "decide y este modo no decide por él"))
    return documentadas, negadas, problemas


def verificar_manifiesto_de_guardas(
        manifiesto: Any, documentadas: set[Invocacion],
        negadas: set[Invocacion]) -> tuple[list[Problema], dict]:
    """El manifiesto contra las instrucciones, por identidad y en las dos direcciones.

    Nombrar **cuál** falta y **cuál** sobra no es cosmética del reporte: un booleano no distingue
    una sustitución de un empate, y una sustitución conserva el total."""
    problemas: list[Problema] = []
    resumen = {"guardas": 0, "exclusiones": 0, "documentadas": len(documentadas),
               "negadas": len(negadas), "faltantes": [], "sobrantes": []}
    if not isinstance(manifiesto, dict):
        return [Problema("manifiesto_ilegible", "el manifiesto",
                         f"declara `{_nombre_tipo(manifiesto)}` y no un objeto")], resumen

    guardas = manifiesto.get("guardas")
    if not isinstance(guardas, list) or not guardas:
        return [Problema(
            "manifiesto_sin_guardas", "`guardas`",
            "el manifiesto no declara ninguna guarda; un conjunto vacío satisface «todas las "
            "declaradas se ejercieron» por vacuidad")], resumen

    identidades: set[Invocacion] = set()
    ids_vistos: set[str] = set()
    for i, entrada in enumerate(guardas):
        donde = f"guarda {i + 1}"
        inv = _invocacion_de(entrada)
        if inv is None:
            problemas.append(Problema("guarda_mal_formada", donde,
                                      "no declara `script` y `argumentos` como texto y lista de "
                                      "textos"))
            continue
        ident = _texto_o_vacio(entrada.get("id"))
        donde = f"guarda `{ident or inv.identidad}`"
        if not ident:
            problemas.append(Problema("guarda_sin_id", donde, "no declara su `id`"))
        elif ident in ids_vistos:
            problemas.append(Problema("guarda_id_duplicado", donde, "otra guarda ya usa ese `id`"))
        else:
            ids_vistos.add(ident)
        if inv in identidades:
            problemas.append(Problema("guarda_duplicada", donde,
                                      "otra entrada declara la misma invocación"))
            continue
        identidades.add(inv)
        criterio = entrada.get("criterio")
        if not isinstance(criterio, dict):
            problemas.append(Problema("guarda_sin_criterio", donde,
                                      "no declara su `criterio` de salud; sin criterio el recibo "
                                      "diría con qué código corrió y nada de qué se concluyó"))
            continue
        tipo = _texto_o_vacio(criterio.get("tipo"))
        if tipo not in CRITERIOS_DE_GUARDA:
            problemas.append(Problema(
                "criterio_desconocido", donde,
                f"declara `{tipo or '(vacío)'}` y los criterios implementados son "
                f"{', '.join('`' + c + '`' for c in CRITERIOS_DE_GUARDA)}"))
        elif tipo == CRITERIO_CODIGO and not isinstance(criterio.get("esperado"), int):
            problemas.append(Problema("criterio_sin_esperado", donde,
                                      "el criterio por código de salida no declara qué código "
                                      "espera"))
    resumen["guardas"] = len(identidades)

    exclusiones = manifiesto.get("exclusiones")
    if not isinstance(exclusiones, list):
        exclusiones = []
    excluidas_del_manifiesto: set[Invocacion] = set()
    for i, entrada in enumerate(exclusiones):
        inv = _invocacion_de(entrada)
        donde = f"exclusión {i + 1}"
        if inv is None:
            problemas.append(Problema("exclusion_mal_formada", donde,
                                      "no declara `script` y `argumentos`"))
            continue
        donde = f"exclusión `{inv.identidad}`"
        resumen["exclusiones"] += 1
        if not _texto_o_vacio(entrada.get("motivo")):
            problemas.append(Problema("exclusion_sin_motivo", donde,
                                      "no declara por qué se excluye; una exclusión sin motivo es "
                                      "un agujero con permiso"))
        origen = _texto_o_vacio(entrada.get("origen"))
        if origen not in ORIGENES_DE_EXCLUSION:
            problemas.append(Problema(
                "exclusion_sin_origen", donde,
                f"declara `{origen or '(vacío)'}` y los orígenes son "
                f"{', '.join('`' + o + '`' for o in ORIGENES_DE_EXCLUSION)}"))
            continue
        if origen == ORIGEN_MANIFIESTO:
            excluidas_del_manifiesto.add(inv)
            if inv in negadas:
                problemas.append(Problema(
                    "exclusion_mal_atribuida", donde,
                    "el manifiesto se atribuye la exclusión y las instrucciones ya la niegan: el "
                    "motivo declarado no es el que rige"))
            continue
        if inv not in negadas:
            problemas.append(Problema(
                "exclusion_sin_respaldo", donde,
                "dice excluirse porque las instrucciones la niegan, y el texto no la niega"
                + (": la documenta como guarda" if inv in documentadas else ": ni la menciona")))

    esperadas = identidades | excluidas_del_manifiesto
    faltantes = sorted(inv.identidad for inv in documentadas - esperadas)
    sobrantes = sorted(inv.identidad for inv in esperadas - documentadas)
    resumen["faltantes"] = faltantes
    resumen["sobrantes"] = sobrantes
    for identidad in faltantes:
        problemas.append(Problema(
            "guarda_documentada_sin_declarar", f"`{identidad}`",
            "las instrucciones la documentan como ejecutable y el manifiesto no la declara ni la "
            "excluye"))
    for identidad in sobrantes:
        problemas.append(Problema(
            "guarda_sin_respaldo_en_instrucciones", f"`{identidad}`",
            "el manifiesto la declara y las instrucciones no la documentan"))
    return problemas, resumen


def _veredicto_de(criterio: dict, exit_code: int, detalle: str) -> tuple[str, str]:
    tipo = _texto_o_vacio(criterio.get("tipo"))
    if tipo == CRITERIO_CODIGO:
        esperado = criterio.get("esperado")
        if exit_code == esperado:
            return "ok", f"terminó con {exit_code}, que es el código sano"
        return "falla", f"terminó con {exit_code} y el criterio espera {esperado}"
    if tipo == CRITERIO_CUERPO:
        # El código de salida de este arnés **no** es su señal de salud: hoy devuelve 4 y ese es el
        # estado sano. Lo que decide es el cuerpo, con el mismo parser de `--parear-reporte`, y
        # `detalle` trae el motivo del rechazo o viene vacío.
        if detalle:
            return "falla", detalle
        return "ok", f"el cuerpo del reporte está sano (terminó con {exit_code}, que no se lee " \
                     "como enfermedad)"
    return "falla", f"criterio `{tipo or '(vacío)'}` sin implementación"


def verificar_recibo_de_guardas(manifiesto: Any, recibo: Any) -> tuple[list[Problema], dict]:
    """El recibo contra el manifiesto, por **igualdad** y no por inclusión.

    Tres direcciones y no una. Con `declarado ⊆ ejercido`, un recibo al que le sobra una ejecución
    ajena pasa, y uno que sustituye una declarada por otra conservando el total pasa también: la
    primera cubre a la segunda."""
    problemas: list[Problema] = []
    resumen = {"declaradas": 0, "ejercidas": 0, "no_ejercidas": [], "ajenas": [], "en_rojo": []}
    if not isinstance(recibo, dict):
        return [Problema("recibo_ilegible", "el recibo",
                         f"declara `{_nombre_tipo(recibo)}` y no un objeto")], resumen

    del_manifiesto = {inv.identidad
                      for inv in (_invocacion_de(g) for g in manifiesto.get("guardas", []))
                      if inv is not None}
    resumen["declaradas"] = len(del_manifiesto)

    declarado = recibo.get("conjunto_declarado")
    ejercido = recibo.get("conjunto_ejercido")
    if not isinstance(declarado, list) or not isinstance(ejercido, list):
        return [Problema("recibo_sin_conjuntos", "el recibo",
                         "no declara `conjunto_declarado` y `conjunto_ejercido` como listas; sin "
                         "los dos la comparación sería sobre prosa y no sobre datos")], resumen
    ejecuciones = recibo.get("ejecuciones")
    if not isinstance(ejecuciones, list):
        return [Problema("recibo_sin_ejecuciones", "el recibo",
                         "no registra `ejecuciones`")], resumen

    if set(declarado) != del_manifiesto:
        for identidad in sorted(set(declarado) - del_manifiesto):
            problemas.append(Problema("recibo_declara_de_mas", f"`{identidad}`",
                                      "el recibo la da por declarada y el manifiesto no la trae"))
        for identidad in sorted(del_manifiesto - set(declarado)):
            problemas.append(Problema("recibo_declara_de_menos", f"`{identidad}`",
                                      "el manifiesto la declara y el recibo no la registra en su "
                                      "conjunto declarado"))

    corridas: list[str] = []
    for i, ejecucion in enumerate(ejecuciones):
        donde = f"ejecución {i + 1}"
        if not isinstance(ejecucion, dict):
            problemas.append(Problema("ejecucion_mal_formada", donde,
                                      f"llegó como `{_nombre_tipo(ejecucion)}`"))
            continue
        identidad = _texto_o_vacio(ejecucion.get("invocacion"))
        donde = f"ejecución `{identidad or i + 1}`"
        if not identidad:
            problemas.append(Problema("ejecucion_sin_invocacion", donde,
                                      "no dice qué invocación ejerció"))
            continue
        corridas.append(identidad)
        if not _texto_o_vacio(ejecucion.get("comando")):
            problemas.append(Problema("ejecucion_sin_comando", donde,
                                      "no registra el `comando` con el que corrió"))
        if not isinstance(ejecucion.get("exit_code"), int):
            problemas.append(Problema("ejecucion_sin_codigo", donde,
                                      "no registra su `exit_code`"))
        criterio = ejecucion.get("criterio")
        if not isinstance(criterio, dict):
            problemas.append(Problema("ejecucion_sin_criterio", donde,
                                      "no registra contra qué criterio se la juzgó"))
            continue
        veredicto = _texto_o_vacio(ejecucion.get("veredicto"))
        if veredicto not in ("ok", "falla"):
            problemas.append(Problema("veredicto_desconocido", donde,
                                      f"declara `{veredicto or '(vacío)'}`"))
            continue
        if criterio.get("tipo") == CRITERIO_CODIGO and isinstance(ejecucion.get("exit_code"), int):
            recalculado, _ = _veredicto_de(criterio, ejecucion["exit_code"], "")
            if recalculado != veredicto:
                problemas.append(Problema(
                    "veredicto_incoherente", donde,
                    f"declara `{veredicto}` y su código {ejecucion['exit_code']} contra el criterio "
                    f"da `{recalculado}`: el recibo se contradice a sí mismo"))
                continue
        if veredicto == "falla":
            resumen["en_rojo"].append(identidad)
            problemas.append(Problema(
                "guarda_en_rojo", donde,
                _texto_o_vacio(ejecucion.get("detalle")) or "la guarda no pasó su criterio"))

    resumen["ejercidas"] = len(set(corridas))
    if sorted(set(corridas)) != sorted(set(ejercido)):
        problemas.append(Problema(
            "recibo_incoherente", "el recibo",
            f"su `conjunto_ejercido` ({len(set(ejercido))}) no es el de sus propias ejecuciones "
            f"({len(set(corridas))}): "
            f"{sorted(set(ejercido) ^ set(corridas))[:3]}"))

    no_ejercidas = sorted(del_manifiesto - set(ejercido))
    ajenas = sorted(set(ejercido) - del_manifiesto)
    resumen["no_ejercidas"] = no_ejercidas
    resumen["ajenas"] = ajenas
    for identidad in no_ejercidas:
        problemas.append(Problema(
            "guarda_no_ejercida", f"`{identidad}`",
            "el manifiesto la declara y la corrida no la ejerció; que las ejecutadas estén todas "
            "verdes no la reemplaza"))
    for identidad in ajenas:
        problemas.append(Problema(
            "ejecucion_ajena", f"`{identidad}`",
            "la corrida la ejerció y el manifiesto no la declara: correr de más no es correr bien, "
            "y la comparación es una igualdad"))
    return problemas, resumen


def _cuerpo_del_reporte_sano(salida: str) -> str:
    """El veredicto sobre `--reporte`, con el parser del modo `--parear-reporte`.

    Devuelve el motivo del rechazo, o cadena vacía si está sano. Reusar el parser en vez de escribir
    otro evita que el repo tenga dos lecturas distintas del mismo reporte."""
    precedencia, codigos, error = vocabulario_de_paridad(RUTA_ARNES_PARIDAD)
    if error:
        return f"no se pudo derivar el vocabulario del arnés: {error}"
    autorizados, error = derivar_pares_con_fallo_declarado(DIR_CASOS_PARIDAD)
    if error:
        return f"no se pudieron derivar los pares autorizados a `fallo`: {error}"
    problemas, _ = verificar_reporte_de_paridad(salida, autorizados, precedencia, codigos, None)
    if problemas:
        return f"{len(problemas)} problemas en el cuerpo; el primero: {problemas[0]}"
    return ""


def ejecutar_guardas(manifiesto: dict, raiz: Path, ruta_manifiesto: Path) -> dict:
    """Corre cada guarda declarada y arma el recibo. **Esto es lo único que ejecuta procesos.**

    El código se captura sin tubería: `$?` después de un pipe devuelve el del último comando del
    pipe y no el del verificador, y ese error ya costó lecturas falsas en este flujo."""
    ejecuciones: list[dict] = []
    for entrada in manifiesto.get("guardas", []):
        inv = _invocacion_de(entrada)
        if inv is None:
            continue
        criterio = entrada.get("criterio") if isinstance(entrada.get("criterio"), dict) else {}
        comando = inv.comando()
        corrida = subprocess.run(comando, cwd=raiz, capture_output=True, text=True)
        detalle = ""
        if _texto_o_vacio(criterio.get("tipo")) == CRITERIO_CUERPO:
            detalle = _cuerpo_del_reporte_sano(corrida.stdout)
        veredicto, explicacion = _veredicto_de(criterio, corrida.returncode, detalle)
        ejecuciones.append({
            "invocacion": inv.identidad,
            "id": _texto_o_vacio(entrada.get("id")),
            "comando": " ".join(comando),
            "exit_code": corrida.returncode,
            "criterio": criterio,
            "veredicto": veredicto,
            "detalle": explicacion,
        })
    declarado = sorted(e["invocacion"] for e in ejecuciones)
    return {
        "manifiesto": str(ruta_manifiesto),
        "instrucciones": _texto_o_vacio(manifiesto.get("instrucciones")),
        "conjunto_declarado": sorted(
            inv.identidad for inv in (_invocacion_de(g) for g in manifiesto.get("guardas", []))
            if inv is not None),
        "conjunto_ejercido": declarado,
        "ejecuciones": ejecuciones,
        "resumen": {
            "ejecutadas": len(ejecuciones),
            "en_rojo": sorted(e["invocacion"] for e in ejecuciones if e["veredicto"] != "ok"),
        },
    }


def modo_guardas(ruta_manifiesto: Path, ruta_instrucciones: Path, raiz: Path,
                 salida: Path | None) -> int:
    manifiesto, error = _cargar_json(ruta_manifiesto)
    if error:
        print(f"FALLA  guardas: {error}")
        return 1
    try:
        texto = ruta_instrucciones.read_text(encoding="utf-8")
    except OSError as e:
        print(f"FALLA  guardas: no se pudieron leer las instrucciones ({e})")
        return 1

    documentadas, negadas, problemas = derivar_invocaciones_documentadas(texto, raiz)
    de_manifiesto, resumen = verificar_manifiesto_de_guardas(manifiesto, documentadas, negadas)
    problemas += de_manifiesto
    if problemas:
        _informar(problemas, f"{ruta_manifiesto.name} contra {ruta_instrucciones.name}")
        print("       no se ejecutó ninguna guarda: un recibo contra un manifiesto que no "
              "corresponde con las instrucciones no prueba nada")
        return 1
    print(f"OK     {ruta_manifiesto.name}: las {resumen['guardas']} guardas y las "
          f"{resumen['exclusiones']} exclusiones coinciden por identidad con las "
          f"{resumen['documentadas']} invocaciones que documenta {ruta_instrucciones.name}, en las "
          "dos direcciones")

    recibo = ejecutar_guardas(manifiesto, raiz, ruta_manifiesto)
    problemas, resumen_recibo = verificar_recibo_de_guardas(manifiesto, recibo)
    if salida is not None:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(json.dumps(recibo, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print(f"OK     recibo escrito en {salida}")
    if problemas:
        _informar(problemas, f"el recibo de {ruta_manifiesto.name}")
        return 1
    print(f"OK     las {resumen_recibo['declaradas']} declaradas se ejercieron y ninguna ajena: el "
          "conjunto ejercido es igual al declarado, no un subconjunto")
    print(f"OK     las {resumen_recibo['ejercidas']} pasan su criterio de salud")
    print()
    print("RESULTADO: OK")
    return 0


# --- Autotest de `--guardas` ------------------------------------------------------------------
#
# **Nada de esto ejecuta una guarda ni escribe en el árbol.** Las instrucciones se mutan en memoria
# —una copia mutada en disco dejaría el árbol mutado si el proceso muriera, y otro agente no
# distingue esa ventana de un cambio real— y el recibo conforme se **sintetiza** del manifiesto en
# vez de cosecharse de una corrida. La fila que ejerce el conjunto sobre el árbol real es otra: si
# esta lo hiciera, la misma task que diseña manifiesto, ejecutor y recibo estaría atestiguando que
# el conjunto se ejerció.
#
# Los mutantes atacan las tres piezas por separado, que es la única forma de que ninguna se cubra
# con otra:
#
# - **sobre el manifiesto** (uno de más, uno de menos): cazan que el manifiesto haya dejado de
#   corresponder con las instrucciones;
# - **sobre el recibo** (uno de menos, uno ajeno, y la sustitución que conserva el total): los tres,
#   porque la comparación es una igualdad. Con solo el primero, una implementación que compruebe
#   `declarado ⊆ ejercido` pasa y el falso verde sobrevive;
# - **sobre las instrucciones** con el manifiesto fijo: agregar, retirar, **sustituir conservando el
#   total** y retirar la negación. Agregar y retirar solo prueban cardinalidad —un comparador de
#   conteos los pasa, y una lista escrita en el script con un hash del texto los pone rojos sin
#   extraer ninguna identidad—; la sustitución solo cae si se comparan identidades. Y el control
#   verde, que cambia prosa ajena a las guardas, impide que un verificador que rechace todo texto
#   modificado se lleve los cuatro.


class CasoDeGuardas(NamedTuple):
    codigo: str | None          # el problema que el caso tiene que disparar; None = conforme
    descripcion: str
    mutar_instrucciones: Any = None      # (texto) -> texto
    mutar_manifiesto: Any = None         # (manifiesto) -> manifiesto
    mutar_recibo: Any = None             # (recibo) -> recibo
    nombra: tuple[str, ...] = ()         # identidades que el diagnóstico tiene que nombrar


CODIGOS_DE_GUARDAS = (
    "guarda_documentada_sin_declarar", "guarda_sin_respaldo_en_instrucciones",
    "exclusion_sin_respaldo", "exclusion_mal_atribuida", "exclusion_sin_motivo",
    "exclusion_sin_origen", "manifiesto_sin_guardas", "guarda_sin_criterio",
    "criterio_desconocido", "criterio_sin_esperado", "guarda_duplicada", "guarda_id_duplicado",
    "guarda_sin_id", "familia_vacia", "invocacion_ambigua",
    "guarda_no_ejercida", "ejecucion_ajena", "recibo_incoherente", "recibo_declara_de_menos",
    "recibo_declara_de_mas", "guarda_en_rojo", "veredicto_incoherente", "recibo_sin_conjuntos",
)

INVOCACION_AJENA = "scripts/verificar-retiro-transporte.py --porcelain"
BANDERA_SUSTITUTA = "--porcelain"
BANDERA_SUSTITUIDA = "--drenaje"


def _sustituir_una_vez(texto: str, viejo: str, nuevo: str) -> str:
    """Sustituye **comprobando que había exactamente una ocurrencia**.

    Un mutante que no muta da un verde que parece cobertura. Si el texto de las instrucciones cambia
    y el patrón deja de estar —o pasa a estar dos veces—, el caso se cae acá y con el motivo, en vez
    de correr sobre un texto intacto y declararse cubierto."""
    apariciones = texto.count(viejo)
    if apariciones != 1:
        raise ValueError(f"el patrón `{viejo}` aparece {apariciones} veces y el mutante espera 1")
    return texto.replace(viejo, nuevo)


def _recibo_sintetico(manifiesto: dict) -> dict:
    """El recibo que una corrida sana produciría, **sin correr nada**."""
    ejecuciones = []
    for entrada in manifiesto.get("guardas", []):
        inv = _invocacion_de(entrada)
        if inv is None:
            continue
        criterio = entrada.get("criterio") if isinstance(entrada.get("criterio"), dict) else {}
        codigo = criterio.get("esperado") if criterio.get("tipo") == CRITERIO_CODIGO else 4
        ejecuciones.append({
            "invocacion": inv.identidad,
            "id": _texto_o_vacio(entrada.get("id")),
            "comando": " ".join(inv.comando()),
            "exit_code": codigo,
            "criterio": criterio,
            "veredicto": "ok",
            "detalle": "sintético: este autotest no ejecuta guardas",
        })
    identidades = sorted(e["invocacion"] for e in ejecuciones)
    return {"conjunto_declarado": list(identidades), "conjunto_ejercido": list(identidades),
            "ejecuciones": ejecuciones}


def _sin_ejecucion(recibo: dict, identidad: str) -> dict:
    recibo["ejecuciones"] = [e for e in recibo["ejecuciones"] if e["invocacion"] != identidad]
    recibo["conjunto_ejercido"] = [i for i in recibo["conjunto_ejercido"] if i != identidad]
    return recibo


def _con_ejecucion(recibo: dict, identidad: str) -> dict:
    recibo["ejecuciones"].append({
        "invocacion": identidad,
        "id": "ajena",
        "comando": f"{sys.executable} {identidad}",
        "exit_code": 0,
        "criterio": {"tipo": CRITERIO_CODIGO, "esperado": 0},
        "veredicto": "ok",
        "detalle": "sintético",
    })
    recibo["conjunto_ejercido"] = sorted(recibo["conjunto_ejercido"] + [identidad])
    return recibo


def _sin_clave(contenedor: dict, clave: str, raiz: dict) -> dict:
    """Quita una clave de un nodo y devuelve la **raíz** que el caso tiene que entregar.

    Dos trampas, las dos ya cobradas acá: `x.pop("esperado") and d or d` funciona por accidente y
    deja de funcionar el día que el valor quitado sea falsy —y `esperado` vale 0 en las veintiuna
    guardas—; y devolver el nodo mutado en vez de la raíz entrega media estructura, que fue lo que
    hizo el primer intento de este helper."""
    contenedor.pop(clave, None)
    return raiz


def _identidad_testigo(manifiesto: dict) -> str:
    """Una guarda real del manifiesto, elegida del dato y no escrita acá."""
    for entrada in manifiesto.get("guardas", []):
        inv = _invocacion_de(entrada)
        if inv is not None and inv.argumentos == (BANDERA_SUSTITUIDA,):
            return inv.identidad
    inv = _invocacion_de(manifiesto["guardas"][0])
    return inv.identidad if inv else ""


def _casos_de_guardas(manifiesto: dict) -> tuple[CasoDeGuardas, ...]:
    testigo = _identidad_testigo(manifiesto)

    def sin_guarda(m: dict) -> dict:
        m["guardas"] = [g for g in m["guardas"]
                        if (_invocacion_de(g) or Invocacion("", ())).identidad != testigo]
        return m

    def con_guarda_de_mas(m: dict) -> dict:
        m["guardas"].append({
            "id": "de-mas", "script": "scripts/verificar-retiro-transporte.py",
            "argumentos": [BANDERA_SUSTITUTA],
            "criterio": {"tipo": CRITERIO_CODIGO, "esperado": 0}})
        return m

    return (
        # Los conformes. Sin ellos, un verificador que rechace toda entrada satisface los once
        # mutantes y cierra en verde sin haber aceptado jamás un manifiesto sano.
        CasoDeGuardas(None, "el manifiesto real contra las instrucciones reales y un recibo "
                            "completo"),
        CasoDeGuardas(
            None, "control verde: se reescribe prosa ajena a las guardas y sigue pasando",
            mutar_instrucciones=lambda t: _sustituir_una_vez(
                t, "Editar una copia a mano es una divergencia silenciosa",
                "Editar a mano una copia es una divergencia silenciosa")),

        # Los dos del manifiesto.
        CasoDeGuardas("guarda_sin_respaldo_en_instrucciones",
                      "el manifiesto declara una invocación de más",
                      mutar_manifiesto=con_guarda_de_mas, nombra=(INVOCACION_AJENA,)),
        CasoDeGuardas("guarda_documentada_sin_declarar",
                      "el manifiesto declara una invocación de menos",
                      mutar_manifiesto=sin_guarda, nombra=(testigo,)),

        # Los tres del recibo: la comparación es una igualdad, no una inclusión.
        CasoDeGuardas("guarda_no_ejercida",
                      "al recibo le falta una ejecución declarada, y las demás están verdes",
                      mutar_recibo=lambda r: _sin_ejecucion(r, testigo), nombra=(testigo,)),
        CasoDeGuardas("ejecucion_ajena",
                      "el recibo agrega una ejecución ajena al manifiesto: correr de más no es "
                      "correr bien",
                      mutar_recibo=lambda r: _con_ejecucion(r, INVOCACION_AJENA),
                      nombra=(INVOCACION_AJENA,)),
        CasoDeGuardas("guarda_no_ejercida",
                      "el recibo sustituye una declarada por otra no declarada **conservando el "
                      "total**",
                      mutar_recibo=lambda r: _con_ejecucion(_sin_ejecucion(r, testigo),
                                                            INVOCACION_AJENA),
                      nombra=(testigo, INVOCACION_AJENA)),
        CasoDeGuardas("guarda_en_rojo", "una guarda corrió y no pasó su criterio",
                      mutar_recibo=lambda r: (r["ejecuciones"][0].update(
                          {"exit_code": 1, "veredicto": "falla",
                           "detalle": "terminó con 1 y el criterio espera 0"}) or r)),
        CasoDeGuardas("veredicto_incoherente", "el recibo declara `ok` con un código que no lo es",
                      mutar_recibo=lambda r: (r["ejecuciones"][0].update({"exit_code": 1}) or r)),

        # Los cuatro de las instrucciones, con el manifiesto fijo: si el conjunto estuviera escrito
        # dentro del script, ninguno de estos lo tocaría.
        CasoDeGuardas("guarda_documentada_sin_declarar",
                      "las instrucciones documentan una guarda más",
                      mutar_instrucciones=lambda t: _sustituir_una_vez(
                          t, "y `--autotest`. El modo",
                          f"`--autotest` y `{BANDERA_SUSTITUTA}`. El modo"),
                      nombra=(INVOCACION_AJENA,)),
        CasoDeGuardas("guarda_sin_respaldo_en_instrucciones",
                      "las instrucciones retiran una guarda",
                      mutar_instrucciones=lambda t: _sustituir_una_vez(
                          t, f"`{BANDERA_SUSTITUIDA}`, ", ""),
                      nombra=(testigo,)),
        CasoDeGuardas("guarda_sin_respaldo_en_instrucciones",
                      "las instrucciones **sustituyen** una guarda por otra conservando el total: "
                      "un conteo o un hash del texto no lo distinguen de un empate",
                      mutar_instrucciones=lambda t: _sustituir_una_vez(
                          t, f"`{BANDERA_SUSTITUIDA}`", f"`{BANDERA_SUSTITUTA}`"),
                      nombra=(testigo, INVOCACION_AJENA)),
        CasoDeGuardas("guarda_documentada_sin_declarar",
                      "las instrucciones dejan de negar la exclusión: pasa a estar documentada "
                      "como guarda",
                      mutar_instrucciones=lambda t: _sustituir_una_vez(
                          t, "aún no está implementado y no cuenta como guarda",
                          "se corre igual que las demás"),
                      nombra=("scripts/verificar-retiro-transporte.py --vias",)),
        CasoDeGuardas("exclusion_sin_respaldo",
                      "las instrucciones dejan de mencionar la invocación que el manifiesto excluye "
                      "por negada",
                      mutar_instrucciones=lambda t: _sustituir_una_vez(
                          t, " El modo `--vias` aún no está implementado y no cuenta como guarda.",
                          "")),

        # El manifiesto mal formado, que es la otra forma de que el conjunto no signifique nada.
        CasoDeGuardas("manifiesto_sin_guardas", "el manifiesto se queda sin guardas",
                      mutar_manifiesto=lambda m: (m.update({"guardas": []}) or m)),
        CasoDeGuardas("guarda_sin_criterio", "una guarda no declara su criterio de salud",
                      mutar_manifiesto=lambda m: _sin_clave(m["guardas"][0], "criterio", m)),
        CasoDeGuardas("criterio_desconocido", "una guarda declara un criterio sin implementación",
                      mutar_manifiesto=lambda m: (m["guardas"][0]["criterio"].update(
                          {"tipo": "a-ojo"}) or m)),
        CasoDeGuardas("exclusion_sin_motivo", "una exclusión no declara su motivo",
                      mutar_manifiesto=lambda m: _sin_clave(m["exclusiones"][0], "motivo", m)),
        CasoDeGuardas("exclusion_mal_atribuida",
                      "una exclusión se atribuye al manifiesto un motivo que las instrucciones ya "
                      "declaran",
                      mutar_manifiesto=lambda m: (m["exclusiones"][0].update(
                          {"origen": ORIGEN_MANIFIESTO}) or m)),
        CasoDeGuardas("exclusion_sin_origen", "una exclusión no declara de dónde sale su exclusión",
                      mutar_manifiesto=lambda m: _sin_clave(m["exclusiones"][0], "origen", m)),
        CasoDeGuardas("criterio_sin_esperado",
                      "un criterio por código de salida no dice qué código espera",
                      mutar_manifiesto=lambda m: _sin_clave(m["guardas"][0]["criterio"],
                                                            "esperado", m)),
        CasoDeGuardas("guarda_sin_id", "una guarda no declara su `id`",
                      mutar_manifiesto=lambda m: _sin_clave(m["guardas"][0], "id", m)),
        CasoDeGuardas("guarda_id_duplicado", "dos guardas comparten `id`",
                      mutar_manifiesto=lambda m: (m["guardas"][1].update(
                          {"id": m["guardas"][0]["id"]}) or m)),
        CasoDeGuardas("guarda_duplicada", "dos entradas declaran la misma invocación",
                      mutar_manifiesto=lambda m: (m["guardas"].append(
                          dict(copy.deepcopy(m["guardas"][0]), id="repetida")) or m)),
        CasoDeGuardas("familia_vacia",
                      "la familia que documentan las instrucciones no expande contra ninguna "
                      "bandera del parser",
                      mutar_instrucciones=lambda t: _sustituir_una_vez(
                          t, "`--autotest-*`", "`--no-existe-esta-familia-*`")),
        CasoDeGuardas("invocacion_ambigua",
                      "las instrucciones documentan una invocación y en otra oración la niegan: el "
                      "texto se contradice y la unión lo taparía",
                      mutar_instrucciones=lambda t: _sustituir_una_vez(
                          t, f"El modo `--vias` aún no",
                          f"El modo `{BANDERA_SUSTITUIDA}` no cuenta como guarda. El modo `--vias` "
                          "aún no"),
                      nombra=(f"scripts/verificar-retiro-transporte.py {BANDERA_SUSTITUIDA}",)),

        # El recibo mal formado: la otra manera de que la igualdad no signifique nada.
        CasoDeGuardas("recibo_sin_conjuntos", "el recibo no trae su conjunto declarado",
                      mutar_recibo=lambda r: _sin_clave(r, "conjunto_declarado", r)),
        CasoDeGuardas("recibo_declara_de_mas",
                      "el recibo da por declarada una invocación que el manifiesto no trae",
                      mutar_recibo=lambda r: (r["conjunto_declarado"].append(INVOCACION_AJENA)
                                              or r),
                      nombra=(INVOCACION_AJENA,)),
        CasoDeGuardas("recibo_declara_de_menos",
                      "el recibo deja fuera de su conjunto declarado una guarda del manifiesto",
                      mutar_recibo=lambda r: (r.update(
                          {"conjunto_declarado": [i for i in r["conjunto_declarado"]
                                                  if i != testigo]}) or r),
                      nombra=(testigo,)),
        CasoDeGuardas("recibo_incoherente",
                      "el conjunto ejercido del recibo no es el de sus propias ejecuciones",
                      mutar_recibo=lambda r: (r["conjunto_ejercido"].append(INVOCACION_AJENA)
                                              or r)),
    )


def _correr_caso_de_guardas(caso: CasoDeGuardas, manifiesto: dict,
                            instrucciones: str) -> tuple[list[Problema], dict]:
    texto = caso.mutar_instrucciones(instrucciones) if caso.mutar_instrucciones else instrucciones
    datos = copy.deepcopy(manifiesto)
    if caso.mutar_manifiesto:
        datos = caso.mutar_manifiesto(datos)
    documentadas, negadas, problemas = derivar_invocaciones_documentadas(texto, REPO)
    del_manifiesto, resumen = verificar_manifiesto_de_guardas(datos, documentadas, negadas)
    problemas = problemas + del_manifiesto
    recibo = _recibo_sintetico(datos)
    if caso.mutar_recibo:
        recibo = caso.mutar_recibo(recibo)
    del_recibo, resumen_recibo = verificar_recibo_de_guardas(datos, recibo)
    resumen = dict(resumen, **{f"recibo_{k}": v for k, v in resumen_recibo.items()})
    return problemas + del_recibo, resumen


def _preludio_de_guardas() -> tuple[list[tuple[str, bool, str]], dict, str]:
    """Lo que tiene que valer antes de correr un caso: que el manifiesto y las instrucciones estén,
    que las banderas que el manifiesto nombra existan en el parser de su script, y que la derivación
    lea de verdad el texto."""
    manifiesto, error = _cargar_json(RUTA_MANIFIESTO_GUARDAS)
    if error:
        return [("0.manifiesto", False, error)], {}, ""
    try:
        instrucciones = RUTA_INSTRUCCIONES.read_text(encoding="utf-8")
    except OSError as e:
        return [("0.instrucciones", False, str(e))], {}, ""

    resultados: list[tuple[str, bool, str]] = []
    huerfanas: list[str] = []
    for entrada in manifiesto.get("guardas", []):
        inv = _invocacion_de(entrada)
        if inv is None:
            huerfanas.append(str(entrada)[:60])
            continue
        if not (REPO / inv.script).is_file():
            huerfanas.append(f"{inv.identidad} — no existe {inv.script}")
            continue
        declaradas, _ = banderas_declaradas(REPO / inv.script)
        faltan = [a for a in inv.argumentos if a.startswith("--") and a not in declaradas]
        if faltan:
            huerfanas.append(f"{inv.identidad} — su parser no declara {faltan}")
    resultados.append((
        "0.banderas", not huerfanas,
        f"las {len(manifiesto.get('guardas', []))} guardas del manifiesto apuntan a scripts que "
        "existen y a banderas que sus parsers declaran"
        if not huerfanas else f"{len(huerfanas)} sin respaldo: " + " | ".join(huerfanas[:3])))

    documentadas, negadas, problemas = derivar_invocaciones_documentadas(instrucciones, REPO)
    scripts = {inv.script for inv in documentadas}
    resultados.append((
        "0.derivacion", bool(documentadas) and len(scripts) >= 3 and not problemas,
        f"la derivación lee {RUTA_INSTRUCCIONES.name} y saca {len(documentadas)} invocaciones "
        f"documentadas sobre {len(scripts)} scripts, más {len(negadas)} negadas en el texto"
        if bool(documentadas) and len(scripts) >= 3 and not problemas else
        f"la derivación devolvió {len(documentadas)} invocaciones y {len(problemas)} problemas: "
        + (str(problemas[0]) if problemas else "no leyó nada")))

    # El testigo de la familia: si `--autotest-*` dejara de expandir, el conjunto perdería siete
    # invocaciones **en silencio** y la igualdad con el manifiesto lo diría, pero recién en rojo.
    familia = sorted(inv.identidad for inv in documentadas
                     if "--autotest-" in " ".join(inv.argumentos))
    resultados.append((
        "0.familia", len(familia) >= 2,
        f"la familia `--autotest-*` de las instrucciones expandió contra el parser del arnés: "
        f"{len(familia)} invocaciones"
        if len(familia) >= 2 else
        f"la familia no expandió: {familia}"))
    return resultados, manifiesto, instrucciones


def modo_autotest_guardas() -> int:
    resultados, manifiesto, instrucciones = _preludio_de_guardas()
    if not all(ok for _, ok, _ in resultados):
        return _cierre("el runner de guardas y su recibo", resultados)

    casos = _casos_de_guardas(manifiesto)

    # [A] El control positivo, en sus dos formas: el manifiesto real contra las instrucciones
    # reales, y el mismo par con prosa ajena reescrita. Sin la segunda, un verificador que
    # rechazara todo texto que no fuera byte a byte el de hoy se llevaría los cuatro mutantes de
    # instrucciones en verde.
    conformes = [c for c in casos if c.codigo is None]
    fallas: list[str] = []
    for caso in conformes:
        try:
            problemas, _ = _correr_caso_de_guardas(caso, manifiesto, instrucciones)
        except ValueError as e:
            fallas.append(f"{caso.descripcion} — el mutante no muta: {e}")
            continue
        if problemas:
            fallas.append(f"{caso.descripcion} — {problemas[0]}")
    resultados.append((
        "A/guardas", not fallas,
        f"control positivo: los {len(conformes)} casos conformes pasan; el manifiesto real "
        "corresponde con las instrucciones reales y el recibo completo cierra la igualdad"
        if not fallas else "control positivo — " + " | ".join(fallas[:3])))

    # [B] Los mutantes, cada uno rechazado **por su motivo** y nombrando las identidades en juego.
    # Un booleano no distingue una sustitución de un empate: el que sustituye conservando el total
    # tiene que nombrar la que falta y la que sobra.
    mutantes = [c for c in casos if c.codigo is not None]
    sobrevivientes: list[str] = []
    desatribuidos: list[str] = []
    sin_nombrar: list[str] = []
    emitidos: set[str] = set()
    for caso in mutantes:
        try:
            problemas, _ = _correr_caso_de_guardas(caso, manifiesto, instrucciones)
        except ValueError as e:
            sobrevivientes.append(f"{caso.codigo}: {caso.descripcion} — el mutante no muta: {e}")
            continue
        codigos = {p.codigo for p in problemas}
        emitidos |= codigos
        if not codigos:
            sobrevivientes.append(f"{caso.codigo}: {caso.descripcion}")
            continue
        if caso.codigo not in codigos:
            desatribuidos.append(f"{caso.codigo}: {caso.descripcion} — rechazado por "
                                 f"{sorted(codigos)} y no por su motivo")
            continue
        texto = " ".join(f"{p.donde} {p.mensaje}" for p in problemas)
        no_nombradas = [i for i in caso.nombra if i and i not in texto]
        if no_nombradas:
            sin_nombrar.append(f"{caso.codigo}: {caso.descripcion} — el diagnóstico no nombra "
                               f"{no_nombradas}")
    resultados.append((
        "B/guardas", not sobrevivientes,
        f"los {len(mutantes)} mutantes se rechazan: {len(casos) - len(mutantes)} conformes y "
        f"{len(mutantes)} rojos sobre las tres piezas (manifiesto, recibo e instrucciones)"
        if not sobrevivientes else "SOBREVIVE " + " | ".join(sobrevivientes[:3])))
    resultados.append((
        "C/guardas", not desatribuidos,
        "cada mutante se rechaza por su propio motivo y no por otro que lo tape"
        if not desatribuidos else " | ".join(desatribuidos[:3])))
    resultados.append((
        "D/guardas", not sin_nombrar,
        "el diagnóstico nombra cuál falta y cuál sobra en los tres casos de sustitución: un "
        "booleano no distingue una sustitución de un empate"
        if not sin_nombrar else " | ".join(sin_nombrar[:3])))

    # [E] La igualdad, en las dos direcciones y sobre el recibo. Es el eje que esta task existe
    # para cerrar: con `declarado ⊆ ejercido`, el segundo y el tercero pasan.
    def caso_por(fragmento: str) -> CasoDeGuardas:
        elegidos = [c for c in mutantes if fragmento in c.descripcion]
        if len(elegidos) != 1:
            raise ValueError(f"`{fragmento}` selecciona {len(elegidos)} casos y no uno")
        return elegidos[0]

    falta = _correr_caso_de_guardas(caso_por("le falta una ejecución declarada"),
                                    manifiesto, instrucciones)
    sobra = _correr_caso_de_guardas(caso_por("agrega una ejecución ajena"),
                                    manifiesto, instrucciones)
    sustitucion = caso_por("el recibo sustituye una declarada")
    problemas_sust, resumen_sust = _correr_caso_de_guardas(sustitucion, manifiesto, instrucciones)
    codigos_sust = {p.codigo for p in problemas_sust}
    total_igual = (resumen_sust["recibo_ejercidas"] == resumen_sust["recibo_declaradas"])
    resultados.append((
        "E1/guardas", {p.codigo for p in falta[0]} == {"guarda_no_ejercida"},
        "al recibo le falta una declarada y se pone rojo aunque las demás estén verdes"
        if {p.codigo for p in falta[0]} == {"guarda_no_ejercida"} else
        f"emitió {sorted({p.codigo for p in falta[0]})}"))
    resultados.append((
        "E2/guardas", {p.codigo for p in sobra[0]} == {"ejecucion_ajena"},
        "al recibo le sobra una ajena y se pone rojo igual: la comparación es una igualdad y no "
        "una inclusión"
        if {p.codigo for p in sobra[0]} == {"ejecucion_ajena"} else
        f"emitió {sorted({p.codigo for p in sobra[0]})}"))
    resultados.append((
        "E3/guardas",
        codigos_sust == {"guarda_no_ejercida", "ejecucion_ajena"} and total_igual,
        f"y con la sustitución el total sigue en {resumen_sust['recibo_ejercidas']} y salen los dos "
        "códigos, el de la que falta y el de la que sobra"
        if codigos_sust == {"guarda_no_ejercida", "ejecucion_ajena"} and total_igual else
        f"la sustitución emitió {sorted(codigos_sust)} con "
        f"{resumen_sust['recibo_ejercidas']} ejercidas de {resumen_sust['recibo_declaradas']} "
        "declaradas"),
    )

    # [F] Que la derivación lea el texto de verdad. Los cuatro mutantes de instrucciones corren con
    # el manifiesto **intacto**: si el conjunto estuviera escrito dentro del script, ninguno lo
    # tocaría y los cuatro pasarían.
    del_texto = [c for c in mutantes if c.mutar_instrucciones]
    vivos = []
    for caso in del_texto:
        problemas, _ = _correr_caso_de_guardas(caso, manifiesto, instrucciones)
        if not problemas:
            vivos.append(caso.descripcion)
    resultados.append((
        "F/guardas", not vivos and len(del_texto) >= 4,
        f"los {len(del_texto)} mutantes de instrucciones corren con el manifiesto intacto y los "
        f"{len(del_texto)} se ponen rojos: la derivación lee el texto y no una lista escrita acá"
        if not vivos and len(del_texto) >= 4 else
        f"{len(vivos)} sobrevivieron con el manifiesto intacto: {vivos[:2]}"))

    # [G] Todo código declarado tiene mutante. Uno sin caso nace sin cobertura y nadie lo nota.
    sin_caso = sorted(set(CODIGOS_DE_GUARDAS) - emitidos)
    resultados.append((
        "G/guardas", not sin_caso,
        f"los mutantes ejercen los {len(CODIGOS_DE_GUARDAS)} códigos que el modo declara: uno sin "
        "caso nacería sin cobertura y nadie lo notaría"
        if not sin_caso else f"{len(sin_caso)} códigos sin mutante: {sin_caso}"))
    return _cierre("el manifiesto corresponde con las instrucciones en las dos direcciones y el "
                   "recibo prueba que el conjunto declarado se ejerció entero y nada más",
                   resultados)


# --- Modos `--topologia` y `--descubrimiento` -------------------------------------------------
#
# El registro canónico declara **una entrada por artefacto** —ubicación, dueño, el dato del que es
# sede y si debe estar versionado—. La **regla de descubrimiento** es una fuente distinta: se aplica
# al árbol candidato y produce un conjunto que se compara contra el del registro **en las dos
# direcciones**.
#
# Las dos direcciones no son simetría decorativa. `descubiertos ⊆ registro` caza el archivo que
# nació sin entrada; solo la inversa caza la entrada que ninguna regla alcanza, y sin ella el
# registro acumula ubicaciones canónicas de archivos que ya no existen o que nadie descubre.
#
# Y una regla **derivada del registro** vuelve la comparación una tautología: comparar un conjunto
# consigo mismo no prueba nada. Por eso el modo rechaza la regla que no es más que la lista de rutas
# del registro transcrita.

RUTA_REGISTRO_ARTEFACTOS = REPO / "scripts" / "artefactos-fase-0.json"

ESTADO_FUENTE = "fuente"
ESTADO_DERIVADO = "derivado"
ESTADO_VISTA = "vista"
ESTADOS_DE_ARTEFACTO = (ESTADO_FUENTE, ESTADO_DERIVADO, ESTADO_VISTA)

# El único tipo de excepción implementado, y el único admisible: lleva **predicado de vigencia**.
# Una excepción sin predicado es permanente, y una excepción permanente es un agujero con permiso:
# el artefacto real nace fuera del registro y nadie se entera nunca. El predicado es «la ruta no
# existe en disco», se evalúa en cada corrida, y cuando la ruta aparece el modo **falla por
# caducidad** —con ese motivo y no con el genérico de una ruta ausente del registro— en vez de
# seguir tapándola.
TIPO_INEXISTENTE = "todavia_inexistente"
TIPOS_DE_EXCEPCION = (TIPO_INEXISTENTE,)


class Artefacto(NamedTuple):
    path: str
    owner: str
    dato: str
    source_status: str
    versioned: bool


def arbol_candidato_de_git(raiz: Path) -> tuple[list[str], str]:
    """`git ls-files` − bajas efectivas + altas no ignoradas. Devuelve `(rutas, error)`.

    **`git ls-files` a secas no alcanza y está medido en este repo:** un archivo nuevo sin stage no
    aparece, y uno borrado del working tree pero aún en el índice sí. El modelo es el que
    `verificar-retiro-transporte.py` documenta; la diferencia es que allá las altas se filtran
    contra un manifiesto de rutas declaradas —correcto para un cambio con alcance fijo— y acá se
    toman de `git status`, porque una lista de altas transcrita queda falsa en cuanto el acto
    agrega un artefacto más.

    Un árbol vacío es **error y no un conjunto vacío**: sobre cero archivos, «los versionados
    aparecen» pasa por vacuidad y `git` ausente se leería como conformidad."""
    def git(*args: str) -> tuple[str, str]:
        try:
            r = subprocess.run(["git", *args], cwd=str(raiz), capture_output=True, text=True)
        except OSError as e:
            return "", f"no se pudo ejecutar `git {' '.join(args)}` en {raiz}: {e}"
        if r.returncode != 0:
            detalle = (r.stderr or r.stdout).strip().splitlines()
            return "", (f"`git {' '.join(args)}` terminó en {r.returncode} en {raiz}"
                        + (f" — {detalle[0][:160]}" if detalle else ""))
        return r.stdout, ""

    salida, error = git("ls-files", "-z")
    if error:
        return [], error
    base = [p for p in salida.split("\0") if p]
    salida, error = git("status", "--porcelain", "-z", "-uall")
    if error:
        return [], error
    campos = salida.split("\0")
    altas: set[str] = set()
    bajas: set[str] = set()
    i = 0
    while i < len(campos):
        entrada = campos[i]
        i += 1
        if not entrada or len(entrada) < 4:
            continue
        xy, rel = entrada[:2], entrada[3:]
        if xy[0] in ("R", "C"):
            origen = campos[i] if i < len(campos) else ""
            i += 1
            if origen:
                bajas.add(origen)
            altas.add(rel)
        elif xy == "??":
            altas.add(rel)
        elif "D" in xy:
            bajas.add(rel)
        elif "A" in xy:
            altas.add(rel)
    candidato = sorted((set(base) - bajas) | altas)
    if not candidato:
        return [], (f"el árbol candidato quedó vacío en {raiz}: sobre cero archivos «los "
                    "versionados aparecen en el índice» pasa por vacuidad, así que esto es un "
                    "error y no un conjunto vacío")
    return candidato, ""


def arbol_de_disco(raiz: Path) -> list[str]:
    """Todos los archivos bajo `raiz`, en rutas relativas POSIX. Para raíces que no son un repo."""
    return sorted(p.relative_to(raiz).as_posix()
                  for p in raiz.rglob("*") if p.is_file())


def _es_directorio(unidad: str) -> bool:
    return unidad.endswith("/")


def _en_el_arbol(unidad: str, arbol: set[str]) -> bool:
    """Un directorio registrado está en el árbol si **algún** archivo cuelga de él; un archivo, si
    está. Registrar el directorio y no cada archivo es lo que hace que el registro no quede falso en
    la primera ampliación del corpus."""
    if _es_directorio(unidad):
        return any(rel.startswith(unidad) for rel in arbol)
    return unidad in arbol


def _artefactos_de(datos: Any) -> tuple[list[Artefacto], list[Problema]]:
    """Las entradas bien formadas y los problemas de las que no lo están."""
    problemas: list[Problema] = []
    artefactos: list[Artefacto] = []
    if not isinstance(datos, dict):
        return [], [Problema("registro_ilegible", "el registro",
                             f"declara `{_nombre_tipo(datos)}` y no un objeto")]
    entradas = datos.get("artefactos")
    if not isinstance(entradas, list) or not entradas:
        return [], [Problema(
            "registro_sin_artefactos", "`artefactos`",
            "el registro no declara ninguna entrada; un registro vacío satisface «cada artefacto "
            "tiene dueño» por vacuidad")]
    for i, entrada in enumerate(entradas):
        donde = f"artefacto {i + 1}"
        if not isinstance(entrada, dict):
            problemas.append(Problema("artefacto_mal_formado", donde,
                                      f"llegó como `{_nombre_tipo(entrada)}`"))
            continue
        path = _texto_o_vacio(entrada.get("path"))
        donde = f"artefacto `{path or i + 1}`"
        if not path:
            problemas.append(Problema("artefacto_sin_path", donde,
                                      "no declara su ubicación canónica"))
            continue
        if path.startswith("/") or ".." in path.split("/"):
            problemas.append(Problema("path_no_canonico", donde,
                                      "la ubicación no es una ruta relativa normalizada desde la "
                                      "raíz del árbol"))
        owner = entrada.get("owner")
        if isinstance(owner, list):
            problemas.append(Problema(
                "artefacto_con_dos_duenos", donde,
                f"declara {len(owner)} dueños ({owner}) y el criterio es dueño **único**: con dos, "
                "ninguno responde"))
            owner = ""
        elif not _texto_o_vacio(owner):
            problemas.append(Problema("artefacto_sin_owner", donde, "no declara su dueño"))
            owner = ""
        else:
            owner = _texto_o_vacio(owner)
        dato = _texto_o_vacio(entrada.get("dato"))
        if not dato:
            problemas.append(Problema(
                "artefacto_sin_dato", donde,
                "no declara de qué dato es sede; sin eso, «ningún dato está declarado en dos "
                "lugares como fuente» no es comprobable: `source_status` dice el rol y no de qué"))
        estado = _texto_o_vacio(entrada.get("source_status"))
        if estado not in ESTADOS_DE_ARTEFACTO:
            problemas.append(Problema(
                "estado_desconocido", donde,
                f"declara `{estado or '(vacío)'}` y los estados implementados son "
                f"{', '.join('`' + e + '`' for e in ESTADOS_DE_ARTEFACTO)}"))
        versioned = entrada.get("versioned")
        if not isinstance(versioned, bool):
            problemas.append(Problema(
                "versioned_no_booleano", donde,
                f"declara `{_nombre_tipo(versioned)}` y la indexación es una decisión binaria; sin "
                "booleano no hay nada que cotejar contra el árbol"))
            versioned = False
        artefactos.append(Artefacto(path, owner, dato, estado, versioned))
    return artefactos, problemas


def verificar_topologia(datos: Any, arbol: list[str]) -> tuple[list[Problema], dict]:
    """Dueño único, fuente única por dato, e indexación **en las dos direcciones**.

    La segunda dirección —los `versioned: false` **fuera** del árbol— no es simetría de adorno: sin
    ella, marcar `false` sería la forma barata de que un artefacto versionado deje de comprobarse."""
    artefactos, problemas = _artefactos_de(datos)
    resumen = {"artefactos": len(artefactos), "duenos": 0, "fuentes": 0,
               "versionados": 0, "fuera_del_indice": [], "en_el_indice_sin_deber": []}
    if not artefactos:
        return problemas, resumen

    en_arbol = set(arbol)
    por_path: dict[str, list[Artefacto]] = {}
    for a in artefactos:
        por_path.setdefault(a.path, []).append(a)
    for path, entradas in sorted(por_path.items()):
        if len(entradas) == 1:
            continue
        duenos = sorted({a.owner for a in entradas if a.owner})
        if len(duenos) > 1:
            problemas.append(Problema(
                "artefacto_con_dos_duenos", f"artefacto `{path}`",
                f"lo reclaman {len(entradas)} entradas con dueños distintos ({', '.join(duenos)}) "
                "y el criterio es dueño único"))
        else:
            problemas.append(Problema(
                "artefacto_duplicado", f"artefacto `{path}`",
                f"{len(entradas)} entradas declaran la misma ubicación canónica"))

    por_dato: dict[str, list[Artefacto]] = {}
    for a in artefactos:
        if a.dato and a.source_status == ESTADO_FUENTE:
            por_dato.setdefault(a.dato, []).append(a)
    for dato, entradas in sorted(por_dato.items()):
        rutas = sorted({a.path for a in entradas})
        if len(rutas) > 1:
            problemas.append(Problema(
                "dato_con_dos_fuentes", f"dato `{dato}`",
                f"está declarado como fuente en {len(rutas)} rutas ({', '.join(rutas)}): dos sedes "
                "del mismo dato divergen y ninguna de las dos manda"))
    resumen["fuentes"] = len(por_dato)
    resumen["duenos"] = len({a.owner for a in artefactos if a.owner})

    for a in artefactos:
        if a.versioned:
            resumen["versionados"] += 1
            if not _en_el_arbol(a.path, en_arbol):
                resumen["fuera_del_indice"].append(a.path)
                problemas.append(Problema(
                    "versionado_fuera_del_indice", f"artefacto `{a.path}`",
                    "se declara versionado y no aparece en el árbol candidato: lo que no está "
                    "indexado no se commitea, y la guarda de ausencia ni siquiera lo mira"))
        elif _en_el_arbol(a.path, en_arbol):
            resumen["en_el_indice_sin_deber"].append(a.path)
            problemas.append(Problema(
                "no_versionado_en_el_indice", f"artefacto `{a.path}`",
                "se declara **no** versionado y está en el árbol candidato: o la declaración miente "
                "o el archivo se va a commitear sin que nadie lo haya decidido"))
    return problemas, resumen


def descubrir(directorios: list[str], patrones: list[str], arbol: list[str]) -> set[str]:
    """La regla aplicada al árbol: a cada archivo, el directorio registrado **más largo** que lo
    prefije; si no hay ninguno, los patrones.

    El «más largo» es lo que permite que un corpus tenga sub-corpus con dueños distintos sin que un
    archivo cuente dos veces."""
    unidades: set[str] = set()
    for rel in arbol:
        prefijos = [d for d in directorios if rel.startswith(d)]
        if prefijos:
            unidades.add(max(prefijos, key=len))
            continue
        if any(fnmatch.fnmatch(rel, p) for p in patrones):
            unidades.add(rel)
    return unidades


def verificar_descubrimiento(datos: Any, arbol: list[str],
                             raiz: Path) -> tuple[list[Problema], dict]:
    """La regla contra el registro, en las dos direcciones, con las excepciones y su vigencia."""
    artefactos, problemas = _artefactos_de(datos)
    resumen = {"descubiertos": 0, "registrados": len(artefactos), "excepciones": 0,
               "sin_entrada": [], "sin_descubrir": [], "caducas": []}
    regla = datos.get("regla_de_descubrimiento") if isinstance(datos, dict) else None
    if not isinstance(regla, dict):
        problemas.append(Problema(
            "regla_ausente", "`regla_de_descubrimiento`",
            "el registro no declara la regla; sin una segunda fuente no hay dos conjuntos que "
            "comparar y la completitud quedaría comprobada contra sí misma"))
        return problemas, resumen

    directorios = [d for d in regla.get("directorios", []) if isinstance(d, str) and d]
    patrones = [p for p in regla.get("patrones", []) if isinstance(p, str) and p]
    for d in directorios:
        if not _es_directorio(d):
            problemas.append(Problema("directorio_sin_barra", f"`{d}`",
                                      "un directorio de la regla tiene que terminar en `/`, o su "
                                      "prefijo alcanzaría a hermanos con el mismo comienzo"))
    if not directorios and not patrones:
        problemas.append(Problema("regla_vacia", "`regla_de_descubrimiento`",
                                  "no declara ni directorios ni patrones: descubre el conjunto "
                                  "vacío y la comparación pasa por vacuidad"))

    rutas_del_registro = {a.path for a in artefactos}
    if rutas_del_registro and set(directorios) | set(patrones) == rutas_del_registro:
        problemas.append(Problema(
            "regla_derivada_del_registro", "`regla_de_descubrimiento`",
            "sus directorios y patrones son exactamente las rutas del registro transcritas: así no "
            "es una fuente distinta sino una segunda vista de la misma, y comparar los dos "
            "conjuntos no prueba nada"))

    excepciones = regla.get("excepciones")
    if not isinstance(excepciones, list):
        excepciones = []
    exceptuadas: set[str] = set()
    for i, entrada in enumerate(excepciones):
        donde = f"excepción {i + 1}"
        if not isinstance(entrada, dict):
            problemas.append(Problema("excepcion_mal_formada", donde,
                                      f"llegó como `{_nombre_tipo(entrada)}`"))
            continue
        path = _texto_o_vacio(entrada.get("path"))
        donde = f"excepción `{path or i + 1}`"
        if not path:
            problemas.append(Problema("excepcion_sin_path", donde, "no dice qué ruta exceptúa"))
            continue
        resumen["excepciones"] += 1
        exceptuadas.add(path)
        if not _texto_o_vacio(entrada.get("motivo")):
            problemas.append(Problema("excepcion_sin_motivo", donde,
                                      "no declara por qué se exceptúa; una excepción sin motivo es "
                                      "un agujero con permiso"))
        tipo = _texto_o_vacio(entrada.get("tipo"))
        if tipo not in TIPOS_DE_EXCEPCION:
            problemas.append(Problema(
                "excepcion_de_tipo_desconocido", donde,
                f"declara `{tipo or '(vacío)'}` y el único tipo implementado es "
                f"`{TIPO_INEXISTENTE}`, que es el único que lleva predicado de vigencia; una "
                "excepción sin predicado no caduca nunca"))
            continue
        if path in rutas_del_registro:
            problemas.append(Problema(
                "excepcion_ya_registrada", donde,
                "el registro ya le dio entrada y la excepción sigue declarada: una de las dos "
                "sobra, y mientras las dos convivan el descubrimiento la sigue tapando"))
        # El predicado de vigencia. Se evalúa **en cada corrida** y contra el disco, no contra el
        # árbol candidato: un archivo que aparece sin indexar es exactamente el caso que la
        # excepción tapaba.
        if (raiz / path).exists():
            resumen["caducas"].append(path)
            problemas.append(Problema(
                "excepcion_caduca", donde,
                f"la excepción dice «{TIPO_INEXISTENTE}» y `{path}` ya existe en disco: el "
                "predicado de vigencia dejó de valer, así que la ruta necesita entrada propia en "
                "el registro y la excepción, retiro. Esto **no** es «archivo ausente del "
                "registro»: es la excepción que caducó"))

    descubiertos = descubrir(directorios, patrones, arbol) - exceptuadas
    resumen["descubiertos"] = len(descubiertos)
    sin_entrada = sorted(descubiertos - rutas_del_registro)
    sin_descubrir = sorted(rutas_del_registro - descubiertos - exceptuadas)
    resumen["sin_entrada"] = sin_entrada
    resumen["sin_descubrir"] = sin_descubrir
    for path in sin_entrada:
        problemas.append(Problema(
            "archivo_sin_entrada_en_el_registro", f"`{path}`",
            "la regla lo descubre en el árbol y el registro no le declara dueño ni ubicación "
            "canónica"))
    for path in sin_descubrir:
        problemas.append(Problema(
            "entrada_que_la_regla_no_descubre", f"`{path}`",
            "el registro la declara y ninguna regla la alcanza: sin esta dirección el registro "
            "acumula entradas que nada vuelve a mirar"))
    return problemas, resumen


def modo_topologia(ruta: Path, raiz: Path) -> int:
    datos, error = _cargar_json(ruta)
    if error:
        print(f"FALLA  topologia: {error}")
        return 1
    arbol, error = arbol_candidato_de_git(raiz)
    if error:
        print(f"FALLA  topologia: {error}")
        return 1
    problemas, resumen = verificar_topologia(datos, arbol)
    if problemas:
        _informar(problemas, f"{ruta.name} contra el árbol candidato ({len(arbol)} archivos)")
        return 1
    print(f"OK     {ruta.name}: los {resumen['artefactos']} artefactos tienen ubicación canónica y "
          f"dueño único ({resumen['duenos']} dueños)")
    print(f"OK     los {resumen['fuentes']} datos con sede declarada tienen una sola: ninguno está "
          "declarado como fuente en dos rutas")
    print(f"OK     los {resumen['versionados']} versionados están en el árbol candidato "
          f"({len(arbol)} archivos) y ninguno de los no versionados aparece")
    print()
    print("RESULTADO: OK")
    return 0


def modo_descubrimiento(ruta: Path, raiz: Path) -> int:
    datos, error = _cargar_json(ruta)
    if error:
        print(f"FALLA  descubrimiento: {error}")
        return 1
    arbol, error = arbol_candidato_de_git(raiz)
    if error:
        print(f"FALLA  descubrimiento: {error}")
        return 1
    problemas, resumen = verificar_descubrimiento(datos, arbol, raiz)
    if problemas:
        _informar(problemas, f"la regla de descubrimiento de {ruta.name} contra su registro")
        return 1
    print(f"OK     la regla descubre {resumen['descubiertos']} unidades en el árbol candidato y el "
          f"registro declara {resumen['registrados']}: los dos conjuntos coinciden en las dos "
          "direcciones")
    print(f"OK     las {resumen['excepciones']} excepciones siguen vigentes: ninguna de sus rutas "
          "existe todavía en disco")
    print()
    print("RESULTADO: OK")
    return 0


# --- Modo `--integracion` ----------------------------------------------------------------------
#
# AC-25: la integración del verificador nuevo en las instrucciones del repositorio tiene que estar
# **declarada** —si es script propio, cuándo corre, con qué comando, con qué código de salida se
# considera sano— y, si esa integración altera un baseline acoplado al contenido de un archivo, ese
# baseline tiene que quedar renovado. La versión anterior de esta fila comprobaba con un `grep` que
# el texto existiera; un texto presente y falso pasaba. Este modo no lee el texto como promesa: lo
# lee como afirmación y la contrasta contra el árbol real —el `--help` del propio script, no lo que
# las instrucciones dicen que declara— y contra la validación real del baseline, sin escribir nada.

CODIGO_SANO_INTEGRACION = 0

# Los cuatro scripts que las instrucciones ya documentaban antes de este disparador: si la unidad
# declarara alguno de estos como "propio", estaría mintiendo —ya son de un verificador existente.
SCRIPTS_EXISTENTES_ANTES_DE_INTEGRACION = (
    "scripts/verificar-vistas-config.py",
    "scripts/verificar-sobre-en-vuelo.py",
    "scripts/verificar-retiro-transporte.py",
    "scripts/verificar-paridad-powershell.py",
)

PATRON_CODIGO_SANO_INTEGRACION = re.compile(r"c[oó]digo de salida sano[^\d]{0,80}(\d+)")


def modo_integracion(ruta_instrucciones: Path, raiz: Path) -> int:
    problemas: list[Problema] = []
    try:
        texto = ruta_instrucciones.read_text(encoding="utf-8")
    except OSError as e:
        print(f"FALLA  integracion: no se pudo leer {ruta_instrucciones}: {e}")
        return 1

    unidad = next((u for u in unidades_de_guarda(texto)
                    if "scripts/verificar-matriz-despachos.py" in u), None)
    if unidad is None:
        _informar([Problema(
            "disparador_ausente", str(ruta_instrucciones),
            "ninguna unidad de las instrucciones documenta `scripts/verificar-matriz-despachos.py`: "
            "el verificador nuevo no tiene disparador")], "integración declarada")
        return 1

    # El comando completo que la unidad documenta para este script, el primero que aparece.
    _, spans = _enmascarar(unidad)
    script_declarado = ""
    argumentos_declarados: tuple[str, ...] = ()
    for span in spans:
        m = PATRON_COMANDO.match(span)
        if m and m.group(1) == "scripts/verificar-matriz-despachos.py":
            script_declarado = m.group(1)
            argumentos_declarados = tuple(m.group(2).split())
            break

    if script_declarado != "scripts/verificar-matriz-despachos.py":
        problemas.append(Problema(
            "comando_no_documentado", "la unidad",
            "no documenta un comando completo `python3 scripts/verificar-matriz-despachos.py "
            "<bandera>`"))
    elif argumentos_declarados != ("--integracion",):
        problemas.append(Problema(
            "comando_distinto_del_esperado",
            f"`{' '.join(argumentos_declarados) or '(sin banderas)'}`",
            "el comando documentado no es exactamente `--integracion`, el modo que este disparador "
            "describe"))

    if "script propio del repo" not in unidad:
        problemas.append(Problema(
            "no_declara_naturaleza", "la unidad",
            "no declara si el verificador es un script propio del repo o un modo de uno existente"))
    elif script_declarado in SCRIPTS_EXISTENTES_ANTES_DE_INTEGRACION:
        problemas.append(Problema(
            "no_es_script_propio", script_declarado,
            "el script declarado ya es uno de los cuatro documentados antes de este disparador: no "
            "es propio"))

    if not re.search(r"(?i)si la skill toca", unidad):
        problemas.append(Problema(
            "sin_condicion_de_disparo", "la unidad",
            "no declara cuándo debe ejecutarse (falta la condición «si la skill toca…»)"))

    m_codigo = PATRON_CODIGO_SANO_INTEGRACION.search(unidad)
    if m_codigo is None:
        problemas.append(Problema(
            "codigo_sano_no_declarado", "la unidad",
            "no declara con qué código de salida se considera sana esta invocación"))
    else:
        declarado = int(m_codigo.group(1))
        if declarado != CODIGO_SANO_INTEGRACION:
            problemas.append(Problema(
                "codigo_sano_no_coincide", f"declara {declarado}",
                "el código de salida que este modo devuelve en verde es "
                f"{CODIGO_SANO_INTEGRACION}, no el que el texto declara"))

    # El comando documentado tiene que existir y ser invocable: se comprueba contra el `--help` real
    # del script, no contra el texto de las instrucciones, que puede documentar una bandera que el
    # parser nunca declaró.
    ruta_script = raiz / "scripts" / "verificar-matriz-despachos.py"
    if not ruta_script.is_file():
        problemas.append(Problema(
            "script_ausente", str(ruta_script),
            "el script que la unidad documenta no existe en el árbol"))
    else:
        try:
            resultado = subprocess.run(
                [sys.executable, str(ruta_script), "--help"],
                capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as e:
            problemas.append(Problema("comando_no_invocable", "--help", f"no se pudo invocar: {e}"))
        else:
            if resultado.returncode != 0 or "--integracion" not in resultado.stdout:
                problemas.append(Problema(
                    "comando_no_invocable", "--integracion",
                    "la bandera documentada no aparece en el `--help` real del script, o el "
                    f"`--help` terminó con código {resultado.returncode}"))

    # El baseline acoplado al contenido de un archivo: si esta fase alteró algo que lo acopla, tiene
    # que quedar renovado. No se asume: se corre la validación real, sin escribir nada.
    ruta_sobre_en_vuelo = raiz / "scripts" / "verificar-sobre-en-vuelo.py"
    if not ruta_sobre_en_vuelo.is_file():
        problemas.append(Problema(
            "verificador_de_baseline_ausente", str(ruta_sobre_en_vuelo),
            "no se pudo comprobar el baseline: el verificador que lo valida no está en el árbol"))
    else:
        try:
            resultado = subprocess.run(
                [sys.executable, str(ruta_sobre_en_vuelo), "--validar-baseline"],
                capture_output=True, text=True, cwd=str(raiz), timeout=60)
        except (OSError, subprocess.TimeoutExpired) as e:
            problemas.append(Problema(
                "baseline_no_comprobable", "--validar-baseline", f"no se pudo invocar: {e}"))
        else:
            if resultado.returncode != 0:
                problemas.append(Problema(
                    "baseline_no_renovado", "scripts/baseline-sobre-en-vuelo.md",
                    "el baseline acoplado al contenido no está renovado: `--validar-baseline` "
                    f"terminó con código {resultado.returncode}"))

    if problemas:
        _informar(problemas, "integración declarada del verificador nuevo")
        return 1

    print(f"OK     `python3 {script_declarado} {' '.join(argumentos_declarados)}` está documentado, "
          "es invocable y su código de salida sano coincide con el declarado")
    print("OK     el baseline acoplado al contenido —scripts/baseline-sobre-en-vuelo.md— está "
          "renovado")
    print()
    print("RESULTADO: OK")
    return CODIGO_SANO_INTEGRACION


# --- Autotests de `--topologia` y de la caducidad ---------------------------------------------
#
# **Ninguno escribe en el árbol.** El de topología muta el registro y el **árbol candidato** en
# memoria; el de caducidad necesita disco —su predicado es la existencia de una ruta— y por eso
# monta una raíz sintética en un directorio temporal, que borra al terminar.
#
# El caso conforme no es un adorno: sin él, un verificador que rechace todo registro satisface los
# mutantes y cierra en verde sin haber aceptado jamás una topología sana. Y el verde del autotest de
# caducidad no lo cubre, porque es otro modo con otro registro.

CODIGOS_DE_TOPOLOGIA = (
    "registro_sin_artefactos", "artefacto_mal_formado", "artefacto_sin_path", "path_no_canonico",
    "artefacto_con_dos_duenos", "artefacto_duplicado", "artefacto_sin_owner", "artefacto_sin_dato",
    "estado_desconocido", "versioned_no_booleano", "dato_con_dos_fuentes",
    "versionado_fuera_del_indice", "no_versionado_en_el_indice",
    "regla_ausente", "regla_vacia", "regla_derivada_del_registro", "directorio_sin_barra",
    "excepcion_mal_formada", "excepcion_sin_path", "excepcion_sin_motivo",
    "excepcion_de_tipo_desconocido", "excepcion_ya_registrada",
    "archivo_sin_entrada_en_el_registro", "entrada_que_la_regla_no_descubre",
)

# Una ruta del árbol candidato que ninguna regla de este acto alcanza: sirve de entrada exclusiva
# del registro. Se elige del dato —del propio árbol— y no se escribe fija más que acá, donde el
# preludio comprueba que sigue existiendo y sin descubrir.
RUTA_AJENA_AL_ACTO = "scripts/verificar-vistas-config.py"
RUTA_INVENTADA = "scripts/inventado-fase-0.json"


class CasoDeTopologia(NamedTuple):
    codigo: str | None
    descripcion: str
    mutar_registro: Any = None     # (datos) -> datos
    mutar_arbol: Any = None        # (lista) -> lista
    nombra: tuple[str, ...] = ()


def _sin_ruta(arbol: list[str], path: str) -> list[str]:
    if _es_directorio(path):
        return [r for r in arbol if not r.startswith(path)]
    if path not in arbol:
        raise ValueError(f"`{path}` no está en el árbol candidato y el mutante espera quitarlo")
    return [r for r in arbol if r != path]


def _con_ruta(arbol: list[str], path: str) -> list[str]:
    if path in arbol:
        raise ValueError(f"`{path}` ya está en el árbol candidato y el mutante espera agregarlo")
    return sorted(arbol + [path])


def _entrada_testigo(datos: dict) -> dict:
    """Una entrada real del registro que sea un **archivo** y esté versionada."""
    for entrada in datos.get("artefactos", []):
        if isinstance(entrada, dict) and entrada.get("versioned") is True \
                and not _es_directorio(_texto_o_vacio(entrada.get("path"))):
            return entrada
    raise ValueError("el registro no trae ninguna entrada versionada de archivo")


def _casos_de_topologia(datos: dict) -> tuple[CasoDeTopologia, ...]:
    testigo = _texto_o_vacio(_entrada_testigo(datos).get("path"))

    def duplicar_con_otro_dueno(d: dict) -> dict:
        clon = copy.deepcopy(_entrada_testigo(d))
        clon["owner"] = clon["owner"] + "-bis"
        clon["dato"] = clon["dato"] + "-bis"
        d["artefactos"].append(clon)
        return d

    def entrada_exclusiva(d: dict) -> dict:
        d["artefactos"].append({
            "path": RUTA_AJENA_AL_ACTO, "owner": "otro-dominio",
            "dato": "verificador-de-vistas-de-configuracion",
            "source_status": ESTADO_FUENTE, "versioned": True})
        return d

    def regla_copiada(d: dict) -> dict:
        d["regla_de_descubrimiento"] = {
            "directorios": [], "patrones": sorted(_texto_o_vacio(e.get("path"))
                                                  for e in d["artefactos"]),
            "excepciones": []}
        return d

    def excepcion(d: dict, **campos: Any) -> dict:
        d["regla_de_descubrimiento"]["excepciones"][0].update(campos)
        return d

    return (
        # [conforme] El registro real contra el árbol candidato real.
        CasoDeTopologia(None, "el registro real contra el árbol candidato real: dueños, fuentes, "
                              "indexación y los dos conjuntos del descubrimiento"),

        # Los seis que la tarea enumera.
        CasoDeTopologia("artefacto_con_dos_duenos",
                        "dos entradas reclaman el mismo artefacto con dueños distintos",
                        mutar_registro=duplicar_con_otro_dueno, nombra=(testigo,)),
        CasoDeTopologia("dato_con_dos_fuentes",
                        "el mismo dato queda declarado como fuente en dos rutas",
                        mutar_registro=lambda d: (d["artefactos"][1].update(
                            {"dato": d["artefactos"][0]["dato"],
                             "source_status": ESTADO_FUENTE}) or d),
                        nombra=(_texto_o_vacio(datos["artefactos"][0].get("path")),)),
        CasoDeTopologia("versionado_fuera_del_indice",
                        "un artefacto versionable desaparece del árbol candidato",
                        mutar_arbol=lambda a: _sin_ruta(a, testigo), nombra=(testigo,)),
        CasoDeTopologia("no_versionado_en_el_indice",
                        "un artefacto que está en el árbol se declara no versionado: la dirección "
                        "inversa, sin la cual marcar `false` sería la forma barata de no comprobar "
                        "nada",
                        mutar_registro=lambda d: (_entrada_testigo(d).update(
                            {"versioned": False}) or d),
                        nombra=(testigo,)),
        CasoDeTopologia("archivo_sin_entrada_en_el_registro",
                        "un archivo del árbol que la regla descubre y el registro no declara",
                        mutar_arbol=lambda a: _con_ruta(a, RUTA_INVENTADA),
                        nombra=(RUTA_INVENTADA,)),
        CasoDeTopologia("regla_derivada_del_registro",
                        "la regla es la lista de rutas del registro transcrita: comparar un "
                        "conjunto consigo mismo no prueba nada",
                        mutar_registro=regla_copiada),
        CasoDeTopologia("entrada_que_la_regla_no_descubre",
                        "una entrada exclusiva del registro —con dueño, fuente e indexación "
                        "válidos— que ninguna regla alcanza",
                        mutar_registro=entrada_exclusiva, nombra=(RUTA_AJENA_AL_ACTO,)),

        # El registro mal formado: la otra manera de que la topología no signifique nada.
        CasoDeTopologia("registro_sin_artefactos", "el registro se queda sin entradas",
                        mutar_registro=lambda d: (d.update({"artefactos": []}) or d)),
        CasoDeTopologia("artefacto_mal_formado", "una entrada no es un objeto",
                        mutar_registro=lambda d: (d["artefactos"].append("scripts/x.json") or d)),
        CasoDeTopologia("artefacto_sin_path", "una entrada no declara su ubicación canónica",
                        mutar_registro=lambda d: _sin_clave(_entrada_testigo(d), "path", d)),
        CasoDeTopologia("path_no_canonico", "una ubicación sale del árbol con `..`",
                        mutar_registro=lambda d: (_entrada_testigo(d).update(
                            {"path": "scripts/../scripts/matriz-despachos.json"}) or d)),
        CasoDeTopologia("artefacto_sin_owner", "una entrada no declara dueño",
                        mutar_registro=lambda d: _sin_clave(_entrada_testigo(d), "owner", d)),
        CasoDeTopologia("artefacto_con_dos_duenos",
                        "una sola entrada declara dos dueños en una lista",
                        mutar_registro=lambda d: (_entrada_testigo(d).update(
                            {"owner": ["uno", "otro"]}) or d)),
        CasoDeTopologia("artefacto_sin_dato", "una entrada no declara de qué dato es sede",
                        mutar_registro=lambda d: _sin_clave(_entrada_testigo(d), "dato", d)),
        CasoDeTopologia("estado_desconocido", "una entrada declara un `source_status` sin "
                                              "implementación",
                        mutar_registro=lambda d: (_entrada_testigo(d).update(
                            {"source_status": "a-medias"}) or d)),
        CasoDeTopologia("versioned_no_booleano", "la indexación deja de ser una decisión binaria",
                        mutar_registro=lambda d: (_entrada_testigo(d).update(
                            {"versioned": "si"}) or d)),
        CasoDeTopologia("artefacto_duplicado", "dos entradas declaran la misma ubicación con el "
                                               "mismo dueño",
                        mutar_registro=lambda d: (d["artefactos"].append(
                            copy.deepcopy(_entrada_testigo(d))) or d),
                        nombra=(testigo,)),

        # La regla y sus excepciones.
        CasoDeTopologia("regla_ausente", "el registro se queda sin regla de descubrimiento",
                        mutar_registro=lambda d: _sin_clave(d, "regla_de_descubrimiento", d)),
        CasoDeTopologia("regla_vacia", "la regla no declara ni directorios ni patrones",
                        mutar_registro=lambda d: (d["regla_de_descubrimiento"].update(
                            {"directorios": [], "patrones": []}) or d)),
        CasoDeTopologia("directorio_sin_barra", "un directorio de la regla pierde su `/` final",
                        mutar_registro=lambda d: (d["regla_de_descubrimiento"]["directorios"].append(
                            "scripts/fixtures") or d)),
        CasoDeTopologia("excepcion_mal_formada", "una excepción no es un objeto",
                        mutar_registro=lambda d: (
                            d["regla_de_descubrimiento"]["excepciones"].append("scripts/x.py")
                            or d)),
        CasoDeTopologia("excepcion_sin_path", "una excepción no dice qué ruta exceptúa",
                        mutar_registro=lambda d: _sin_clave(
                            d["regla_de_descubrimiento"]["excepciones"][0], "path", d)),
        CasoDeTopologia("excepcion_sin_motivo", "una excepción no declara su motivo",
                        mutar_registro=lambda d: _sin_clave(
                            d["regla_de_descubrimiento"]["excepciones"][0], "motivo", d)),
        CasoDeTopologia("excepcion_de_tipo_desconocido",
                        "una excepción declara un tipo sin predicado de vigencia: sin predicado no "
                        "caduca nunca",
                        mutar_registro=lambda d: excepcion(d, tipo="permanente")),
        CasoDeTopologia("excepcion_ya_registrada",
                        "una ruta queda exceptuada y registrada a la vez",
                        mutar_registro=lambda d: excepcion(
                            d, path=_texto_o_vacio(_entrada_testigo(d).get("path"))),
                        nombra=(testigo,)),
    )


def _correr_caso_de_topologia(caso: CasoDeTopologia, datos: dict,
                              arbol: list[str]) -> tuple[list[Problema], dict]:
    registro = copy.deepcopy(datos)
    if caso.mutar_registro:
        registro = caso.mutar_registro(registro)
    candidato = list(arbol)
    if caso.mutar_arbol:
        candidato = caso.mutar_arbol(candidato)
    problemas, resumen = verificar_topologia(registro, candidato)
    del_descubrimiento, resumen_desc = verificar_descubrimiento(registro, candidato, REPO)
    resumen = dict(resumen, **{f"desc_{k}": v for k, v in resumen_desc.items()})
    return problemas + del_descubrimiento, resumen


def _preludio_de_topologia() -> tuple[list[tuple[str, bool, str]], dict, list[str]]:
    """Lo que tiene que valer antes de correr un caso: que el registro esté, que el árbol candidato
    se construya de verdad, y que las dos rutas testigo estén donde el mutante las supone.

    La segunda no es paranoia: si `git` fallara y el árbol llegara vacío, «los versionados aparecen»
    pasaría por vacuidad y el conforme cerraría en verde sin haber mirado nada."""
    datos, error = _cargar_json(RUTA_REGISTRO_ARTEFACTOS)
    if error:
        return [("0.registro", False, error)], {}, []
    arbol, error = arbol_candidato_de_git(REPO)
    if error:
        return [("0.arbol", False, error)], {}, []

    resultados: list[tuple[str, bool, str]] = []
    resultados.append((
        "0.arbol", len(arbol) > 100,
        f"el árbol candidato se construyó de git y trae {len(arbol)} archivos: sobre un árbol vacío "
        "el criterio de indexación pasaría por vacuidad"
        if len(arbol) > 100 else f"el árbol candidato trae {len(arbol)} archivos"))

    regla = datos.get("regla_de_descubrimiento", {})
    directorios = regla.get("directorios", [])
    patrones = regla.get("patrones", [])
    descubiertos = descubrir(directorios, patrones, arbol)
    resultados.append((
        "0.regla", len(descubiertos) >= 5,
        f"la regla se aplica al árbol y descubre {len(descubiertos)} unidades sobre "
        f"{len(directorios)} directorios y {len(patrones)} patrones"
        if len(descubiertos) >= 5 else f"la regla descubrió {sorted(descubiertos)}"))

    # Las dos rutas testigo: una tiene que estar en el árbol y **sin descubrir** (la entrada
    # exclusiva del registro), y la otra no puede estar (el archivo inventado). Un mutante que no
    # muta da un verde que parece cobertura.
    ajena_ok = RUTA_AJENA_AL_ACTO in arbol and RUTA_AJENA_AL_ACTO not in descubiertos
    resultados.append((
        "0.ajena", ajena_ok,
        f"`{RUTA_AJENA_AL_ACTO}` está en el árbol y ninguna regla la descubre: sirve de entrada "
        "exclusiva del registro"
        if ajena_ok else
        f"`{RUTA_AJENA_AL_ACTO}` — en el árbol: {RUTA_AJENA_AL_ACTO in arbol}; descubierta: "
        f"{RUTA_AJENA_AL_ACTO in descubiertos}"))
    inventada_ok = (RUTA_INVENTADA not in arbol
                    and any(fnmatch.fnmatch(RUTA_INVENTADA, p) for p in patrones))
    resultados.append((
        "0.inventada", inventada_ok,
        f"`{RUTA_INVENTADA}` no está en el árbol y algún patrón la alcanzaría: el mutante del "
        "archivo sin entrada muta de verdad"
        if inventada_ok else f"`{RUTA_INVENTADA}` no sirve de testigo"))

    excepciones = regla.get("excepciones", [])
    vigentes = [e for e in excepciones
                if isinstance(e, dict) and not (REPO / _texto_o_vacio(e.get("path"))).exists()]
    resultados.append((
        "0.excepciones", len(excepciones) > 0 and len(vigentes) == len(excepciones),
        f"las {len(excepciones)} excepciones declaradas siguen vigentes: ninguna de sus rutas "
        "existe en disco"
        if excepciones and len(vigentes) == len(excepciones) else
        f"{len(excepciones) - len(vigentes)} de {len(excepciones)} excepciones ya caducaron"))
    return resultados, datos, arbol


def modo_autotest_topologia() -> int:
    resultados, datos, arbol = _preludio_de_topologia()
    if not all(ok for _, ok, _ in resultados):
        return _cierre("el registro canónico, su regla y la topología", resultados)

    casos = _casos_de_topologia(datos)

    # [A] El control positivo. El registro real, el árbol real y la regla real tienen que cerrar sin
    # un solo problema; sin esta parte, un verificador que rechace todo satisface los mutantes.
    conformes = [c for c in casos if c.codigo is None]
    fallas: list[str] = []
    for caso in conformes:
        try:
            problemas, _ = _correr_caso_de_topologia(caso, datos, arbol)
        except ValueError as e:
            fallas.append(f"{caso.descripcion} — el caso no se pudo construir: {e}")
            continue
        if problemas:
            fallas.append(f"{caso.descripcion} — {problemas[0]}")
    resultados.append((
        "A/topologia", not fallas,
        f"control positivo: {len(conformes)} caso(s) conforme(s) pasan; el registro real describe "
        "el árbol real y la regla descubre exactamente lo registrado"
        if not fallas else "control positivo — " + " | ".join(fallas[:3])))

    # [B/C/D] Los mutantes, cada uno rechazado por su propio motivo y nombrando la ruta en juego.
    mutantes = [c for c in casos if c.codigo is not None]
    sobrevivientes: list[str] = []
    desatribuidos: list[str] = []
    sin_nombrar: list[str] = []
    emitidos: set[str] = set()
    for caso in mutantes:
        try:
            problemas, _ = _correr_caso_de_topologia(caso, datos, arbol)
        except ValueError as e:
            sobrevivientes.append(f"{caso.codigo}: {caso.descripcion} — no se pudo construir: {e}")
            continue
        codigos = {p.codigo for p in problemas}
        emitidos |= codigos
        if not codigos:
            sobrevivientes.append(f"{caso.codigo}: {caso.descripcion}")
            continue
        if caso.codigo not in codigos:
            desatribuidos.append(f"{caso.codigo}: {caso.descripcion} — rechazado por "
                                 f"{sorted(codigos)} y no por su motivo")
            continue
        texto = " ".join(f"{p.donde} {p.mensaje}" for p in problemas)
        no_nombradas = [r for r in caso.nombra if r and r not in texto]
        if no_nombradas:
            sin_nombrar.append(f"{caso.codigo}: {caso.descripcion} — el diagnóstico no nombra "
                               f"{no_nombradas}")
    resultados.append((
        "B/topologia", not sobrevivientes,
        f"los {len(mutantes)} mutantes se rechazan: {len(casos) - len(mutantes)} conforme y "
        f"{len(mutantes)} rojos sobre el registro, el árbol y la regla"
        if not sobrevivientes else "SOBREVIVE " + " | ".join(sobrevivientes[:3])))
    resultados.append((
        "C/topologia", not desatribuidos,
        "cada mutante se rechaza por su propio motivo y no por otro que lo tape"
        if not desatribuidos else " | ".join(desatribuidos[:3])))
    resultados.append((
        "D/topologia", not sin_nombrar,
        "el diagnóstico nombra la ruta en juego: un booleano no dice cuál artefacto perdió su dueño"
        if not sin_nombrar else " | ".join(sin_nombrar[:3])))

    # [E] Las dos direcciones de la comparación, por separado. El de disco obliga a
    # `descubiertos ⊆ registro`; **solo** el de la entrada exclusiva obliga a la inversa, y sin ella
    # el registro acumula ubicaciones canónicas que ninguna regla vuelve a mirar.
    def caso_por(fragmento: str) -> CasoDeTopologia:
        elegidos = [c for c in mutantes if fragmento in c.descripcion]
        if len(elegidos) != 1:
            raise ValueError(f"`{fragmento}` selecciona {len(elegidos)} casos y no uno")
        return elegidos[0]

    de_disco, _ = _correr_caso_de_topologia(caso_por("que la regla descubre y el registro no "
                                                     "declara"), datos, arbol)
    exclusiva, _ = _correr_caso_de_topologia(caso_por("entrada exclusiva del registro"),
                                             datos, arbol)
    codigos_disco = {p.codigo for p in de_disco}
    codigos_excl = {p.codigo for p in exclusiva}
    resultados.append((
        "E1/topologia", codigos_disco == {"archivo_sin_entrada_en_el_registro"},
        "un archivo descubierto sin entrada pone rojo la dirección `descubiertos ⊆ registro`"
        if codigos_disco == {"archivo_sin_entrada_en_el_registro"} else
        f"emitió {sorted(codigos_disco)}"))
    resultados.append((
        "E2/topologia", codigos_excl == {"entrada_que_la_regla_no_descubre"},
        "y una entrada que ninguna regla alcanza pone rojo la dirección inversa, que el caso "
        "anterior no toca"
        if codigos_excl == {"entrada_que_la_regla_no_descubre"} else
        f"emitió {sorted(codigos_excl)}"))

    # [F] La regla como fuente distinta. Si se la deriva del registro, la comparación se vuelve una
    # tautología y los dos casos de [E] pasarían con cualquier árbol.
    derivada, _ = _correr_caso_de_topologia(caso_por("la lista de rutas del registro transcrita"),
                                            datos, arbol)
    codigos_der = {p.codigo for p in derivada}
    resultados.append((
        "F/topologia", "regla_derivada_del_registro" in codigos_der,
        "una regla transcrita del registro se rechaza: es una segunda vista de la misma fuente y "
        "no una fuente distinta"
        if "regla_derivada_del_registro" in codigos_der else f"emitió {sorted(codigos_der)}"))

    # [G] Todo código declarado tiene mutante.
    sin_caso = sorted(set(CODIGOS_DE_TOPOLOGIA) - emitidos)
    resultados.append((
        "G/topologia", not sin_caso,
        f"los mutantes ejercen los {len(CODIGOS_DE_TOPOLOGIA)} códigos que los dos modos declaran"
        if not sin_caso else f"{len(sin_caso)} códigos sin mutante: {sin_caso}"))
    return _cierre("el registro tiene dueño único y ubicación canónica, ninguna fuente duplicada, "
                   "la indexación cierra en las dos direcciones y la regla es una fuente distinta "
                   "que descubre exactamente lo registrado", resultados)


# --- Autotest de la caducidad de las excepciones ----------------------------------------------

RUTA_PENDIENTE = "scripts/pendiente-fase-0.json"
RUTA_MADURA = "scripts/madura-fase-0.json"
MOTIVO_PENDIENTE = "la produce el acto siguiente y todavía no existe"


def _dir_de_trabajo() -> Path:
    """El directorio donde se materializan las rutas del autotest.

    **Nunca el árbol.** Un archivo creado en el worktree no se distingue de un cambio real mientras
    existe, y si el proceso muere queda ahí. `CLAUDE_JOB_DIR` cuando está; si no, el temporal del
    sistema."""
    base = os.environ.get("CLAUDE_JOB_DIR")
    if base:
        destino = Path(base) / "tmp"
        try:
            destino.mkdir(parents=True, exist_ok=True)
            return destino
        except OSError:
            pass
    return Path(tempfile.gettempdir())


def _registro_de_caducidad(con_excepcion: bool, con_entrada: bool) -> dict:
    artefactos = [{"path": RUTA_MADURA, "owner": "acto-en-curso", "dato": "artefacto-maduro",
                   "source_status": ESTADO_FUENTE, "versioned": True}]
    if con_entrada:
        artefactos.append({"path": RUTA_PENDIENTE, "owner": "acto-siguiente",
                           "dato": "artefacto-del-acto-siguiente",
                           "source_status": ESTADO_FUENTE, "versioned": True})
    excepciones = []
    if con_excepcion:
        excepciones.append({"path": RUTA_PENDIENTE, "tipo": TIPO_INEXISTENTE,
                            "motivo": MOTIVO_PENDIENTE})
    return {"artefactos": artefactos,
            "regla_de_descubrimiento": {"directorios": [], "patrones": ["scripts/*-fase-0.json"],
                                        "excepciones": excepciones}}


def modo_autotest_caducidad_excepcion() -> int:
    """Las **dos** direcciones del predicado de vigencia.

    Con una sola, el predicado especial puede no estar implementado y nada lo notaría: el modo que
    solo comprueba «la ruta exceptuada no aparece» da verde para siempre mientras la ruta no exista,
    que es justo el estado en que corre la fila de aplicación."""
    resultados: list[tuple[str, bool, str]] = []
    raiz = Path(tempfile.mkdtemp(prefix="caducidad-", dir=str(_dir_de_trabajo())))
    try:
        (raiz / "scripts").mkdir(parents=True)
        (raiz / RUTA_MADURA).write_text("{}\n", encoding="utf-8")

        # [0] El preludio: la raíz sintética no puede estar dentro del árbol, y la ruta exceptuada
        # no puede existir todavía.
        fuera = not raiz.is_relative_to(REPO)
        resultados.append((
            "0.raiz", fuera and not (raiz / RUTA_PENDIENTE).exists(),
            f"la raíz sintética vive fuera del árbol ({raiz}) y la ruta exceptuada todavía no "
            "existe ahí"
            if fuera and not (raiz / RUTA_PENDIENTE).exists() else
            f"la raíz sintética quedó en {raiz}"))

        # [A] **Control de que el predicado puede ponerse verde.** Excepción declarada y ruta que no
        # existe: es el estado en que corre la fila de aplicación, y sin este control un predicado
        # siempre-rojo pasaría por implementado.
        problemas, resumen = verificar_descubrimiento(
            _registro_de_caducidad(True, False), arbol_de_disco(raiz), raiz)
        resultados.append((
            "A/caducidad", not problemas and resumen["excepciones"] == 1,
            "excepción vigente y ruta ausente: verde, con la excepción contada y sin taparse nada "
            "más"
            if not problemas and resumen["excepciones"] == 1 else
            f"{len(problemas)} problemas: {problemas[0] if problemas else ''}"))

        # [B] **Primera dirección: la excepción caduca.** Se materializa la ruta exceptuada y el
        # modo tiene que ponerse rojo **por caducidad**, no por el genérico de «archivo ausente del
        # registro»: con el diagnóstico genérico, retirar la excepción parecería innecesario.
        (raiz / RUTA_PENDIENTE).write_text("{}\n", encoding="utf-8")
        problemas, _ = verificar_descubrimiento(
            _registro_de_caducidad(True, False), arbol_de_disco(raiz), raiz)
        codigos = {p.codigo for p in problemas}
        texto = " ".join(f"{p.donde} {p.mensaje}" for p in problemas)
        solo_caducidad = codigos == {"excepcion_caduca"}
        resultados.append((
            "B/caducidad", solo_caducidad and RUTA_PENDIENTE in texto,
            f"la ruta exceptuada aparece en disco y el modo se pone rojo por caducidad, nombrando "
            f"`{RUTA_PENDIENTE}`"
            if solo_caducidad and RUTA_PENDIENTE in texto else
            f"emitió {sorted(codigos)} — se esperaba solo `excepcion_caduca`"))
        resultados.append((
            "B2/caducidad", "archivo_sin_entrada_en_el_registro" not in codigos,
            "y **no** por el genérico de archivo ausente del registro: la excepción tapaba esa "
            "señal, así que confundirlas dejaría la excepción en pie"
            if "archivo_sin_entrada_en_el_registro" not in codigos else
            "se rechazó por el motivo genérico y no por la caducidad"))

        # [C] **Segunda dirección: regularizar da verde.** Se retira la excepción y la ruta entra al
        # registro. Sin esta mitad, un modo que rechazara toda excepción cerraría [B] en verde.
        problemas, resumen = verificar_descubrimiento(
            _registro_de_caducidad(False, True), arbol_de_disco(raiz), raiz)
        de_topologia, _ = verificar_topologia(_registro_de_caducidad(False, True),
                                              arbol_de_disco(raiz))
        verde = not problemas and not de_topologia
        resultados.append((
            "C/caducidad", verde,
            "al retirar la excepción y darle entrada propia en el registro, los dos modos vuelven a "
            "verde: la caducidad se regulariza registrando, no volviendo a exceptuar"
            if verde else
            f"{len(problemas) + len(de_topologia)} problemas: "
            f"{(problemas + de_topologia)[0]}"))

        # [D] Y el contra-control de la regularización a medias: si la excepción sigue declarada
        # aunque la ruta ya esté registrada, el modo lo dice en vez de dejarlo pasar.
        problemas, _ = verificar_descubrimiento(
            _registro_de_caducidad(True, True), arbol_de_disco(raiz), raiz)
        codigos = {p.codigo for p in problemas}
        esperados = {"excepcion_caduca", "excepcion_ya_registrada"}
        resultados.append((
            "D/caducidad", codigos == esperados,
            "una regularización a medias —entrada nueva y excepción sin retirar— se rechaza por las "
            "dos cosas"
            if codigos == esperados else f"emitió {sorted(codigos)} y se esperaba "
                                         f"{sorted(esperados)}"))
    finally:
        shutil.rmtree(raiz, ignore_errors=True)
    return _cierre("el predicado de vigencia está implementado y distingue su causa: rojo por "
                   "caducidad mientras la excepción sigue declarada con la ruta ya existente, y "
                   "verde una vez que la ruta entra al registro y la excepción se retira",
                   resultados)


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
        "--claves-perfil", nargs="?", const=str(RUTA_NOMBRES_RESERVADOS), metavar="RUTA",
        help="comprueba que ningún nombre reservado al contenedor de perfiles (por defecto los de "
             "scripts/nombres-reservados-perfil.json) aparezca como clave en una superficie de "
             "configuración del árbol",
    )
    parser.add_argument(
        "--autotest-claves-perfil", action="store_true",
        help="control positivo y negativo del modo anterior, con un mutante por superficie derivada",
    )
    parser.add_argument(
        "--parear-reporte", metavar="RUTA",
        help="clasifica un reporte de `verificar-paridad-powershell.py --reporte` por su cuerpo y "
             "no por su código de salida; `-` lee de stdin",
    )
    parser.add_argument(
        "--autotest-parear-reporte", action="store_true",
        help="control positivo y negativo del modo anterior sobre el corpus sintético de reportes",
    )
    parser.add_argument(
        "--identidad", nargs="?", const=str(RUTA_MATRIZ), metavar="RUTA",
        help="coteja la identidad de los puntos contra la atestación histórica: el blob de la "
             f"matriz en el commit {COMMIT_ATESTACION[:7]}. La referencia no se pasa por bandera a "
             "propósito; ver el bloque de decisiones del modo",
    )
    parser.add_argument(
        "--autotest-identidad", action="store_true",
        help="control positivo y negativo del modo anterior sobre repositorios git sintéticos",
    )
    parser.add_argument(
        "--contrato", nargs="?", const=str(RUTA_CONTRATO), metavar="RUTA",
        help="valida el alcance, las correcciones con su atribución resuelta contra el documento "
             "fuente, y las decisiones diferidas con su fase (por defecto el documento de contrato "
             "del repositorio, que todavía no existe: ahí termina con "
             f"{CODIGO_DOCUMENTO_AUSENTE})",
    )
    parser.add_argument(
        "--autotest-contrato", action="store_true",
        help="control positivo y negativo del modo --contrato sobre el corpus sintético de "
             "scripts/fixtures-contrato/",
    )
    parser.add_argument(
        "--ejes", nargs="?", const=str(RUTA_CONTRATO), metavar="RUTA",
        help="compara los tres ejes del contrato por igualdad exacta contra el inventario "
             "normativo de literales, con puntero por literal",
    )
    parser.add_argument(
        "--autotest-ejes", action="store_true",
        help="control positivo y negativo del modo --ejes, con el preludio que resuelve todos los "
             "punteros del inventario contra el árbol real",
    )
    parser.add_argument(
        "--capacidades", nargs="?", const=str(RUTA_CONTRATO), metavar="RUTA",
        help="comprueba que toda afirmación de plataforma vaya marcada portable, dependiente con su "
             "versión comprobada, o no verificable con su motivo",
    )
    parser.add_argument(
        "--autotest-capacidades", action="store_true",
        help="control positivo y negativo del modo --capacidades, con mutantes unitarios dentro de "
             "un documento de afirmaciones válidas",
    )
    parser.add_argument(
        "--perfil-schema", nargs="?", const=str(RUTA_CONTRATO), metavar="RUTA",
        help="comprueba el contenedor del perfil de ejecución: sus cinco componentes obligatorios y "
             "la lista blanca cerrada del objeto de parámetros de cada perfil",
    )
    parser.add_argument(
        "--autotest-perfil-schema", action="store_true",
        help="control positivo y negativo del modo --perfil-schema, con el bloque que separa los "
             "dos niveles de la lista blanca",
    )
    parser.add_argument(
        "--perfil-precedencia", nargs="?", const=str(RUTA_CONTRATO), metavar="RUTA",
        help="ejecuta la precedencia declarada contra el corpus de escenarios del contrato y coteja "
             "cada resolución contra la que el documento declara",
    )
    parser.add_argument(
        "--autotest-perfil-precedencia", action="store_true",
        help="control positivo y negativo del modo --perfil-precedencia, con las dos ausencias "
             "legítimas por separado",
    )
    parser.add_argument(
        "--roles", nargs="?", const=str(RUTA_CONTRATO), metavar="RUTA",
        help="los contratos de las cinco familias de rol —con sus campos resueltos por el "
             "verificador semántico de la matriz— y el mapa de las trece asignaciones por igualdad "
             "exacta",
    )
    parser.add_argument(
        "--autotest-roles", action="store_true",
        help="control positivo y negativo del modo --roles, con un mutante por asignación",
    )
    parser.add_argument(
        "--diversidad", nargs="?", const=str(RUTA_CONTRATO), metavar="RUTA",
        help="las tres identidades y las relaciones de cada intento, la topología derivada de esos "
             "registros y la regla de evidencia independiente",
    )
    parser.add_argument(
        "--autotest-diversidad", action="store_true",
        help="control positivo y negativo del modo --diversidad, con el fixture cuya topología "
             "declarada contradice sus propios registros",
    )
    parser.add_argument(
        "--defectos", nargs="?", const=str(RUTA_CONTRATO), metavar="RUTA",
        help="el inventario de defectos: los seis mínimos comparados por identidad, cada uno con su "
             "ubicación, su naturaleza y su fase",
    )
    parser.add_argument(
        "--autotest-defectos", action="store_true",
        help="control positivo y negativo del modo --defectos, con la sustitución que conserva el "
             "total",
    )
    parser.add_argument(
        "--guardas", nargs="?", const=str(RUTA_MANIFIESTO_GUARDAS), metavar="RUTA",
        help="ejecuta el conjunto cerrado de invocaciones de guarda del manifiesto (por defecto "
             "scripts/guardas-fase-0.json) y emite un recibo; falla si omite una aunque las "
             "ejecutadas estén verdes, y si el manifiesto y lo que documentan las instrucciones no "
             "coinciden en las dos direcciones",
    )
    parser.add_argument(
        "--autotest-guardas", action="store_true",
        help="control positivo y negativo del modo anterior sobre el manifiesto y las "
             "instrucciones reales, con mutantes sobre las tres piezas; no ejecuta ninguna guarda",
    )
    parser.add_argument(
        "--topologia", nargs="?", const=str(RUTA_REGISTRO_ARTEFACTOS), metavar="RUTA",
        help="el registro canónico de artefactos (por defecto scripts/artefactos-fase-0.json): "
             "dueño único y ubicación canónica por artefacto, ningún dato declarado como fuente en "
             "dos rutas, y los versionados dentro del árbol candidato y los no versionados fuera",
    )
    parser.add_argument(
        "--descubrimiento", nargs="?", const=str(RUTA_REGISTRO_ARTEFACTOS), metavar="RUTA",
        help="aplica la regla de descubrimiento —una fuente distinta del registro— al árbol "
             "candidato y compara los dos conjuntos en las dos direcciones, evaluando en cada "
             "corrida el predicado de vigencia de cada excepción",
    )
    parser.add_argument(
        "--autotest-topologia", action="store_true",
        help="control positivo y negativo de los dos modos anteriores sobre el registro y el árbol "
             "reales, con el registro y el árbol candidato mutados en memoria",
    )
    parser.add_argument(
        "--autotest-caducidad-excepcion", action="store_true",
        help="las dos direcciones del predicado de vigencia sobre una raíz sintética: rojo por "
             "caducidad al materializar una ruta exceptuada, y verde al retirar la excepción y "
             "darle entrada en el registro",
    )
    parser.add_argument(
        "--integracion", nargs="?", const=str(RUTA_INSTRUCCIONES), metavar="RUTA",
        help="la integración declarada del verificador nuevo en las instrucciones del repositorio "
             "(por defecto CLAUDE.md): que lo declarado —script propio, cuándo corre, comando y "
             "código de salida sano— sea cierto contra el árbol real, y que el baseline acoplado al "
             "contenido de un archivo alterado quede renovado",
    )
    parser.add_argument(
        "--instrucciones", metavar="RUTA", default=str(RUTA_INSTRUCCIONES),
        help="las instrucciones del repositorio de las que se deriva el conjunto documentado (por "
             "defecto CLAUDE.md); solo lo usa --guardas",
    )
    parser.add_argument(
        "--pares-con-fallo", metavar="LISTA", default=None,
        help="los pares autorizados a mostrar `fallo`, separados por comas (por defecto, los que "
             "declaran un caso `clase_esperada: fallo` en scripts/paridad-casos/); solo lo usa "
             "--parear-reporte",
    )
    parser.add_argument(
        "--codigo-de-salida", metavar="N", type=int, default=None,
        help="el código con que terminó la corrida que produjo el reporte; se coteja contra el que "
             "el reporte declara y NO entra en el veredicto (solo lo usa --parear-reporte)",
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
             "solo lo usan --correspondencia, --completitud, --claves-perfil, --topologia y "
             "--descubrimiento (para estos dos, la raíz del árbol candidato)",
    )
    parser.add_argument(
        "--raiz", metavar="RUTA", default=str(REPO),
        help="raíz contra la que se interpretan las sedes, que son rutas relativas (por defecto, "
             "este repositorio); la usan --anclas, --presupuesto-contractual, --contrato (para "
             "resolver los documentos fuente de las correcciones), --ejes (para resolver los "
             "punteros de los literales) y --integracion (para ubicar el script y el verificador "
             "del baseline)",
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
        bool(args.claves_perfil),
        args.autotest_claves_perfil,
        bool(args.parear_reporte),
        args.autotest_parear_reporte,
        bool(args.identidad),
        args.autotest_identidad,
        bool(args.contrato),
        args.autotest_contrato,
        bool(args.ejes),
        args.autotest_ejes,
        bool(args.capacidades),
        args.autotest_capacidades,
        bool(args.perfil_schema),
        args.autotest_perfil_schema,
        bool(args.perfil_precedencia),
        args.autotest_perfil_precedencia,
        bool(args.roles),
        args.autotest_roles,
        bool(args.diversidad),
        args.autotest_diversidad,
        bool(args.defectos),
        args.autotest_defectos,
        bool(args.guardas),
        args.autotest_guardas,
        bool(args.topologia),
        bool(args.descubrimiento),
        args.autotest_topologia,
        args.autotest_caducidad_excepcion,
        bool(args.integracion),
    ]
    if sum(seleccionados) != 1:
        print("Invocación inválida: exactamente uno de --schema, --autotest-schema, "
              "--nombres-reservados, --autotest-nombres-reservados, --correspondencia, "
              "--autotest-correspondencia, --completitud, --autotest-completitud, --procedencia, "
              "--autotest-procedencia, --anclas, --autotest-anclas, --presupuesto-contractual, "
              "--condiciones, --autotest-condiciones, --cobertura-condiciones, "
              "--autotest-cobertura-condiciones, --claves-perfil, --autotest-claves-perfil, "
              "--parear-reporte, --autotest-parear-reporte, --identidad, --autotest-identidad, "
              "--contrato, --autotest-contrato, --ejes, --autotest-ejes, --capacidades, "
              "--autotest-capacidades, --perfil-schema, --autotest-perfil-schema, "
              "--perfil-precedencia, --autotest-perfil-precedencia, --roles, --autotest-roles, "
              "--diversidad, --autotest-diversidad, --defectos, --autotest-defectos, --guardas, "
              "--autotest-guardas, --topologia, --descubrimiento, --autotest-topologia, "
              "--autotest-caducidad-excepcion o --integracion.",
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
    if args.claves_perfil:
        return modo_claves_perfil(Path(args.arbol), Path(args.claves_perfil))
    if args.autotest_claves_perfil:
        return modo_autotest_claves_perfil()
    if args.parear_reporte:
        autorizados = (tuple(p for p in args.pares_con_fallo.split(",") if p.strip())
                       if args.pares_con_fallo is not None else None)
        return modo_parear_reporte(args.parear_reporte, autorizados, args.codigo_de_salida)
    if args.autotest_parear_reporte:
        return modo_autotest_parear_reporte()
    if args.identidad:
        return modo_identidad(Path(args.identidad))
    if args.autotest_identidad:
        return modo_autotest_identidad()
    if args.contrato:
        return modo_contrato(Path(args.contrato), Path(args.raiz))
    if args.autotest_contrato:
        return modo_autotest_contrato()
    if args.ejes:
        return modo_ejes(Path(args.ejes), Path(args.raiz))
    if args.autotest_ejes:
        return modo_autotest_ejes()
    if args.capacidades:
        return modo_capacidades(Path(args.capacidades))
    if args.autotest_capacidades:
        return modo_autotest_capacidades()
    if args.perfil_schema:
        return modo_perfil_schema(Path(args.perfil_schema))
    if args.autotest_perfil_schema:
        return modo_autotest_perfil_schema()
    if args.perfil_precedencia:
        return modo_perfil_precedencia(Path(args.perfil_precedencia))
    if args.autotest_perfil_precedencia:
        return modo_autotest_perfil_precedencia()
    if args.roles:
        return modo_roles(Path(args.roles), Path(args.raiz), Path(args.arbol))
    if args.autotest_roles:
        return modo_autotest_roles()
    if args.diversidad:
        return modo_diversidad(Path(args.diversidad))
    if args.autotest_diversidad:
        return modo_autotest_diversidad()
    if args.defectos:
        return modo_defectos(Path(args.defectos))
    if args.autotest_defectos:
        return modo_autotest_defectos()
    if args.guardas:
        return modo_guardas(Path(args.guardas), Path(args.instrucciones), Path(args.raiz),
                            Path(args.salida) if args.salida else None)
    if args.autotest_guardas:
        return modo_autotest_guardas()
    if args.topologia:
        return modo_topologia(Path(args.topologia), Path(args.arbol))
    if args.descubrimiento:
        return modo_descubrimiento(Path(args.descubrimiento), Path(args.arbol))
    if args.autotest_topologia:
        return modo_autotest_topologia()
    if args.autotest_caducidad_excepcion:
        return modo_autotest_caducidad_excepcion()
    if args.integracion:
        return modo_integracion(Path(args.integracion), Path(args.raiz))
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
