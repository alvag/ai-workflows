# `init` reducido + config de ejemplo copiable

Fecha: 2026-08-03
Estado: diseño aprobado, sin implementar
Skills afectadas: `sdd-flow`, `sdd-orchestrator`, `co-explore`, `cross-review`, `cross-implement`

## Objetivo

Que configurar un proyecto sea **mirar un ejemplo completo y decidir qué copiar**, en vez de
contestar un cuestionario que igual no cubre el esquema. Dos piezas con una frontera nítida:

> **`init` pregunta solo lo que no puede saber. El ejemplo enseña todo lo demás.**

Hoy las dos se solapan —el wizard pregunta 9 cosas que el esquema también documenta— y ninguna
sirve para copiar.

## El problema, medido

El esquema canónico (`sdd-flow/reference.md` → "Esquema de `.specify/config.yml`") tiene **33 claves
hoja**. El wizard de `init` pregunta **9**. Y las fuentes que documentan esas claves son **cuatro**:
`sdd-flow/reference.md`, `sdd-flow/SKILL.md`, `co-explore/SKILL.md` y `cross-review/SKILL.md`.

Tres defectos concretos, los tres verificados:

**1. El esquema mezcla valores de ejemplo con valores default, sin distinguirlos.**

```yaml
stack: node          # ejemplo — no hay default, se autodetecta
tracker: jira        # ejemplo — tampoco
default_branch: main # ejemplo — y la skill dice "nunca asumir main/master"
transport: cli       # default real
implement_mode: ask  # default real
```

Copiarlo tal cual en un repo Python fija `stack: node` y `tracker: jira`. Es precisamente el flujo
que este diseño quiere habilitar, y hoy falla.

**2. Dos de las cuatro fuentes enseñan la forma que YAML rompe.** Medido con el parser:

```
mode: on       ->  True      (bool)
mode: "on"     ->  'on'      (str)
```

`sdd-flow` avisa explícitamente que van entre comillas. `cross-review/SKILL.md` documenta
`auto | on | off` **sin** comillas, y `co-explore/SKILL.md` hace lo mismo con `debate.mode` una
línea después de haberlo hecho bien en `mode`. Quien copie esos ejemplos escribe un booleano donde
la skill espera un string.

**3. Nadie lo notó.** La divergencia entre cuatro copias ocurrió en silencio. Es la evidencia de que
cuatro copias sin dirección declarada ni chequeo no se mantienen sincronizadas solas.

Además, `cross_implement` (`execution`, `max_fix_rounds`, `deadline`) **no tiene bloque YAML en su
propia skill**: solo existe en prosa y dentro del esquema de `sdd-flow`.

## Clasificación de las 33 claves

El criterio que define qué se pregunta: **si tiene default, la skill decide; se pregunta solo lo que
no puede saber.**

| Grupo | N | Claves | Tratamiento |
|---|---|---|---|
| Sin default, **no** detectables | 2 | `tracker`, `branch_prefix` | Preguntas del wizard |
| Sin default, autodetectables | 6 | `stack`, `test_cmd`, `build_cmd`, `lint_cmd`, `test_scope_hint`, `default_branch` | Se detectan; editables en el preview final (como hoy) |
| Con default | 25 | el resto | No se preguntan. Viven en el ejemplo |

`tracker` no es detectable de forma determinista: con varios MCP disponibles la resolución es
ambigua, y la propia skill dice que fijarlo hace el paso determinista. `branch_prefix` es política
de CI/CD del equipo: nada en el repo la revela.

## Pieza 1 — El ejemplo copiable

**Dos archivos, uno por cada config que existe de verdad:**

- `skills/sdd-flow/config-ejemplo.md` — las 33 claves de `.specify/config.yml`
- `skills/sdd-orchestrator/manifest-ejemplo.md` — las claves de config de `manifest.yml`

Van como **hermanos de `reference.md`**, no dentro: se leen en un momento distinto —cuando se
configura un proyecto—, que es el criterio de corte de la capa de referencia que el repo ya usa.

### Las cuatro propiedades que lo hacen copiable

Ninguna fuente actual las tiene, y las cuatro son del **archivo**, no de ninguna clave:

1. **Ejemplo y default se distinguen visualmente.** Cada valor queda marcado como uno u otro. Es el
   defecto que hace fallar el flujo de copiar.
2. **`on`/`off` siempre entre comillas**, en el valor y en el enum del comentario.
3. **Cada bloque declara qué skill lo gobierna.** `cross_review`, `co_explore`, `cross_implement` y
   `cross_model` no son de `sdd-flow`; quien lee necesita saber a dónde ir por el detalle.
4. **Descripción corta por clave**, una línea: qué hace, no por qué.

### Qué NO hace

No se materializa en el repo del usuario. El ejemplo es documentación que vive en la skill —la
autoridad—, así que **ningún default queda pinneado**: una clave ausente del `config.yml` sigue
delegando en la skill, y si la skill cambia su default, el proyecto lo recibe. Materializar los 25
defaults en cada repo habría congelado los defaults del día de la corrida, en silencio.

## Pieza 2 — Dueño declarado y vista ensamblada

El modelo que resuelve la duplicación sin romper la autocontención.

**El punto de partida:** el bloque de una hermana y el ejemplo hacen trabajos distintos.

| | Pregunta que responde | Qué necesita ser |
|---|---|---|
| Bloque de la hermana | "¿qué puedo configurar de *esta* skill?" | Autoritativo sobre sus claves. Autocontenido. |
| El ejemplo | "¿qué pego en el config de mi proyecto?" | Completo y copiable. Un solo archivo. |

Un bloque de 4 claves no sirve para copiar; un archivo de 33 dentro de `sdd-flow` no sirve para
entender `co-explore` sola —y `co-explore` y `cross-review` **se instalan y se usan sin `sdd-flow`**
(dependencia blanda, modo directo y modo draft fuera de todo flujo SDD), así que un puntero hacia un
archivo de `sdd-flow` puede quedar colgando.

Servir los dos trabajos obliga a que el texto exista dos veces. Lo evitable no es la duplicación:
es que sea **sin dirección y sin chequeo**.

### Las reglas

1. **Cada hermana conserva su bloque** y queda declarada **dueña** del enum y la descripción de
   *sus* claves. `cross-implement` gana el bloque que hoy no tiene.
2. **El ejemplo se declara vista.** Dice explícitamente que está ensamblado de esos dueños y que
   **ante discrepancia manda el dueño**.
3. **La dirección es única: dueño → vista.** Nunca al revés. Agregar una clave se hace en el dueño y
   se refleja en la vista.
4. La vista aporta **solo lo que es del archivo**: comillas, marca ejemplo-vs-default, orden y la
   atribución de cada bloque a su skill.

### El mapa de dueños

Sin esto las guardas no son implementables: comparar "la vista contra su dueño" exige saber, por
clave, quién es el dueño. Las 33 se reparten así:

| Dueño | N | Claves |
|---|---|---|
| `sdd-flow` | 18 | `stack`, `test_cmd`, `build_cmd`, `lint_cmd`, `default_branch`, `branch_format`, `branch_prefix`, `commit_style`, `tracker`, `test_scope_hint`, `implement_mode`, `domain_context.*` (3), `final_diff_review.mode`, `jira_approval.*` (3) |
| `cross-review` | 6 | `cross_review.*` (5) + `cross_model.manifest.mode`, cuyo esquema ya es canónico en su `reference.md` → "Manifest de corrida" |
| `co-explore` | 4 | `co_explore.*` (2) + `co_explore.debate.*` (2) |
| `cross-implement` | 3 | `cross_implement.*` |
| `sdd-flow` (ecosistema) | 2 | `cross_model.schema_version`, `cross_model.transport` — los resuelve y ecoa el flujo; los adaptadores los consumen |

18 + 6 + 4 + 3 + 2 = **33**.

### Qué pasa con el esquema actual de `sdd-flow/reference.md`

Es el punto que la primera versión de este diseño dejaba ambiguo. Si el ejemplo lista las 33 y la
sección "Esquema" también, la duplicación queda **dentro de una misma skill**, que es peor que lo
que este diseño arregla.

La sección "Esquema" **se recorta a las 20 claves que `sdd-flow` posee** (sus 18 más las 2 de
ecosistema) y **apunta** a las hermanas por los 13 restantes. `config-ejemplo.md` pasa a ser el único
lugar donde las 33 aparecen juntas, y lo hace declarándose vista.

### Las dos guardas

- **G1 — conjunto de claves.** El conjunto de claves de la vista es igual a la unión de los
  conjuntos de los dueños. Caza que alguien agregue o quite una clave en un solo lado.
- **G2 — tokens del enum.** Por cada clave, los valores admitidos que declara la vista coinciden con
  los que declara su dueño. Caza el defecto de comillas y cualquier divergencia de valores.

G1 sola dejaría pasar exactamente el defecto que motivó este diseño: el conjunto de claves de
`cross-review` y el de `sdd-flow` **ya coincide**, y aun así uno enseña `on` y el otro `"on"`. Por
eso G2 no es opcional.

Las dos guardas se prueban **por mutación en las dos direcciones** antes de congelarse: una guarda
que nace verde y nunca se vio roja no discrimina.

## Pieza 3 — El `init` reducido

De **2 pantallas y 9 preguntas** a **1 pantalla y 3**:

| Pregunta | Por qué se pregunta |
|---|---|
| `tracker` | Sin default; autodetección ambigua con varios MCP |
| `branch_prefix` | Sin default; política de CI/CD que nada en el repo revela |
| `jira_approval.mode` | **Condicional:** solo si se eligió `tracker: jira`. Tiene default (`"off"`), pero es un hecho de proceso del equipo que ninguna skill puede detectar y cambia el flujo de verdad (publica la spec en Jira y espera aprobación). Con otro tracker no se pregunta: la clave no aplica |

**Lo que no cambia:** leer la selección vigente y pre-seleccionarla, autodetectar los 6
comandos/paths, mostrar el preview completo editable, el STOP antes de escribir, y la fusión en la
re-corrida.

**Lo que se agrega — el cierre.** Al confirmar, `init` nombra cuántas opciones más existen y apunta
al ejemplo. Sin eso, reducir el wizard convertiría *"no te lo pregunto"* en *"no existe"*: las **6**
preguntas que se van —`commit_style`, `implement_mode`, `cross_review`, `domain_context`,
`final_diff_review` y `debate`— tienen que dejar un rastro descubrible.

## Pieza 4 — El orquestador

**`sdd-orchestrator` no tiene `init`, y este diseño no se lo agrega.** Su config vive en
`manifest.yml`, que se escribe en el paso `reparto` y es **estado de corrida**, no setup de repo. Su
única clave sin default —`branch_prefix`— ya la captura en `gather-context`.

Por el criterio de este diseño, el orquestador necesita **cero preguntas nuevas**. Lo que le falta
es el ejemplo: `manifest-ejemplo.md`, con las mismas cuatro propiedades de copiabilidad y bajo las
mismas reglas de dueño → vista.

## Fuera de alcance

- **Validar el `config.yml` de un proyecto contra el esquema.** Detectar claves o valores
  inexistentes en el config del usuario es trabajo de `doctor`, que hoy no lo hace. Es un cambio
  distinto, con su propio criterio de éxito, y se decide aparte.
- **Cambiar cualquier default.** Este diseño documenta y reduce preguntas; no toca el valor que la
  skill aplica cuando una clave está ausente.
- **Agregar claves nuevas al esquema.** Vale la regla del repo: una capacidad entra con su
  consumidor o no entra.
- **Materializar el config completo en el repo del usuario.** Descartado explícitamente por el
  pinneo de defaults.

## Verificación

| Qué | Cómo se comprueba |
|---|---|
| La vista está completa | G1: conjunto de claves de la vista == unión de los dueños |
| La vista no contradice a su dueño | G2: tokens del enum por clave, vista vs dueño |
| El ejemplo es copiable sin romperse | Parsear el bloque YAML del ejemplo y comprobar que ningún valor de un campo `mode` resuelve a booleano |
| Ejemplo y default están distinguidos | Toda clave del ejemplo lleva una de las dos marcas, ninguna las dos |
| El wizard pregunta 3 y no 9 | Inspección del paso `init`; y que las 7 que salieron estén nombradas en el cierre |
| `cross-implement` tiene su bloque | Existe y G1/G2 lo incluyen |
| Las guardas discriminan | Mutación en las dos direcciones sobre una copia, verificando que el mutante se aplicó |
