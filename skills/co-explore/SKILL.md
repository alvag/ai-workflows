---
name: co-explore
description: >-
  Exploración paralela cross-model con dos workers frescos: uno por familia
  (Codex y Claude) explora el mismo código read-only, con el mismo paquete de
  contexto y sin verse entre sí. El conductor NO explora — arbitra: lee el
  índice compacto de cada uno y abre el detalle solo ante divergencia, alto
  riesgo, baja confianza o una decisión a arbitrar. Cuatro modos: "explore"
  (mapear terreno antes de una spec), "counter-plan" (contra-enfoque antes de un
  plan/reparto), "investigate" (causas raíz rankeadas + plan de verificación,
  sin arreglar) y "debate" (decidir entre opciones abiertas; único modo donde el
  conductor es voz). explore/counter-plan los invocan sdd-flow y
  sdd-orchestrator; investigate y debate son standalone. Invocación directa:
  "/co-explore <ticket|bug>" o "que Codex explore esto en paralelo". NO revisa
  artefactos escritos (eso es cross-review) ni arregla bugs (eso es
  systematic-debugging). No invocarla espontáneamente: solo ante pedido
  explícito del usuario o invocada por sdd-flow/sdd-orchestrator.
---

# co-explore — dos mapas independientes que convergen

Helper que despacha **dos workers frescos en paralelo** —uno por familia, Codex y Claude— a
explorar el mismo código read-only con el mismo paquete de contexto y sin verse entre sí. El
conductor **no explora**: arbitra. Lee siempre el **índice** de cada worker y abre el **detalle**
solo ante un disparador, y al final escribe el artefacto de cierre.
Sirve para cuatro cosas, según `mode`:

- **`explore`** (pre-spec, lo invoca SDD): mapear el terreno antes de escribir una `spec.md` —
  archivos relevantes, puntos de reúso, riesgos, enfoque sugerido.
- **`counter-plan`** (pre-plan/pre-reparto, lo invoca SDD): proponer un contra-enfoque propio
  para una spec ya aprobada.
- **`investigate`** (standalone, fuera de todo flujo SDD): investigar un bug — dos modelos
  forman hipótesis de causa raíz por su lado y el conductor las sintetiza en hipótesis
  rankeadas + plan de verificación. **No arregla ni verifica ejecutando como parte de la
  skill**: el valor cross-model vive en el espacio de hipótesis (dos lentes con puntos ciegos
  distintos); verificar es determinístico y lo hace después otra skill.
- **`debate`** (standalone + lo invoca SDD en decisiones): ayudar a **decidir** entre
  opciones abiertas cuando el usuario no está seguro. Las dos familias forman posturas
  independientes, se critican en varias rondas y el conductor entrega una **síntesis neutral
  atribuida** — no elige ganador, afila la decisión. Es el único modo con **loop de rondas**
  (los otros tres son una sola pasada).

El valor no es que el revisor "ayude" al conductor: es que produce un mapa **independiente**,
sin ver nada de lo que el conductor ya pensó, para que las diferencias entre los dos mapas
salgan a la luz antes de que las decisiones queden tomadas. Dos exploraciones convergen
fácil (son hechos + hipótesis); dos specs no (son decisiones ya tomadas) — por eso el punto
de encuentro es temprano, en los hallazgos, no al final.

El informe alimenta la **síntesis del conductor** (que compara los dos mapas, hace competir
los enfoques —o las hipótesis de causa raíz, en `investigate`— en méritos y decide con
rationale auditable) y, en los modos SDD, más adelante la **crítica informada** de
`cross-review`, que recibe ese informe como contexto persistente en el gate. Esta skill
**no revisa artefactos escritos** — eso lo hace `cross-review`: `co-explore` produce
hallazgos e hipótesis propios que compiten con los del conductor, no una crítica de lo que el
conductor ya escribió. La frontera con el **modo draft** de `cross-review` es la misma, en clave
**mapa vs veredicto**: co-explore corre cuando el terreno sigue abierto (aún no hay enfoque
elegido — el valor está en dos mapas independientes); si el conductor ya eligió un enfoque y
quiere que lo ataquen, eso es un veredicto sobre una decisión tomada → `cross-review` draft, no
una co-exploración. Y hay un tercer eje: si el terreno está abierto pero ya tienes **opciones
concretas** entre las que no sabes cuál elegir, eso no es mapa (`explore`) ni veredicto sobre un
enfoque ya elegido (`cross-review` draft) — es una **decisión** entre alternativas → `debate`.

```
                        ┌──► worker Codex  ──► índice + detalle ──┐
paquete de contexto ────┤    (read-only, aislado)                 ├──► conductor: ÁRBITRO
   (idéntico, sin       └──► worker Claude ──► índice + detalle ──┘     · lee los dos ÍNDICES
    hipótesis de nadie)                                                 · abre DETALLE solo por
                                                                          disparador
                                                                        · cierre + envelope
```

El conductor no es una tercera voz: no produce mapa. Por eso los dos workers pueden ser uno de cada
familia aunque uno comparta la del conductor — la diversidad vive entre **los dos mapas que se
comparan**.

## Reglas no negociables

1. **No persiste nada en tu árbol.** El invariante de seguridad tiene dos mitades, ambas garantizadas
   en los despachos vigentes. Primero, el **comportamiento read-only por contrato**: el prompt del
   **revisor** le prohíbe escribir y modificar, y su única salida permitida es su propio informe bajo
   `co-explore/scratch/` (ver `reference.md` → "Árbol de rutas"); nada más del árbol. Segundo, el
   **aislamiento por permisos**: por CLI se lo invoca sin permiso de escritura y su salida la captura
   el conductor por redirección. El **conductor** nunca persiste cambios en el
   working tree del usuario — el único archivo que escribe fuera del scratch es el **manifest de
   corrida**, un registro local untracked de la misma clase que `.plans/`
   (`cross-review/reference.md` → "Manifest de corrida"). En `explore`/`counter-plan` el contrato de
   ambos es read-only. En `investigate` el conductor puede, opt-in (L1), **ejecutar** para investigar
   —reproducir, correr tests, logging efímero— pero SOLO en un **worktree descartable** que se
   tira al cerrar; el revisor sigue en L0 —no ejecuta— y lee un checkout estable, nunca el
   worktree que el conductor está mutando (ver `reference.md` → "Capacidades y worktree
   (`investigate`)").
2. **Independencia (anti-anclaje), por modo.** En `explore`, `counter-plan` e `investigate` la
   independencia rige **entre los dos workers**: ninguno ve la salida del otro, ni ahora ni en
   fases posteriores, y ambos arrancan solo con el paquete de contexto — nunca con hallazgos,
   hipótesis ni borradores de nadie. En `debate` rige **conductor ↔ worker en la ronda 0**, porque
   ahí el conductor sí es una de las dos voces; del cruce en adelante el intercambio es deliberado.
   El valor está en dos mapas sin contaminar, no en uno que copia al otro.
   Ver `reference.md` → "Independencia por modo (regla 2 en topología dual)".

3. **Nunca se bloquea por dudas.** El explorador corre no-interactivo: no puede preguntar a
   mitad de camino ni esperar una respuesta. Toda duda se registra y se sigue explorando — una
   pregunta abierta que no pudo resolver va a `## Incógnitas`; una decisión que tomó para
   poder seguir avanzando va a `## Supuestos`, con el porqué.
4. **Informe estructurado o nada.** La salida tiene que respetar el "Formato de dos capas"
   (`reference.md`). Si la respuesta del revisor no parsea contra ese formato, se degrada: se
   conserva como texto libre si aporta contexto, o se descarta si es ruido — y en cualquier
   caso se registra la degradación.
5. **Loop acotado, deadline duro.** En `explore`/`counter-plan`/`investigate`, **una sola pasada
   por modo — sin rondas**. La excepción es `debate`: es el único modo con **loop acotado** de
   rondas de cruce (default 3, tope duro `max_rounds`), como `cross-review`; igual tiene deadline
   duro **por ronda** → al vencer se mata el proceso del explorador y se devuelve `UNAVAILABLE`
   con lo que haya. Nunca se espera de forma indefinida.
6. **Opcional y degradable.** Es una capacidad, no un requisito. Sin CLI para un worker declarado,
   con un fallo en runtime, o con `mode: off`, el resultado es `UNAVAILABLE` en una
   línea y la llamadora sigue con la exploración del conductor solamente.
7. **Allowlist de workers y diversidad declarada.** Hay **dos** familias —Claude y GPT/Codex— y el
   conductor no entra en `families`. En los tres modos duales se despacha un worker por cada familia
   seleccionada: con dos, se comparan dos mapas cross-family; con una, corre un proceso aparte y la
   <!-- corpus-invariante:inicio:co-explore.SKILL.md.ada44733310a -->
   escalera declara si es de la misma familia o de la opuesta al conductor. Descubrimiento por
   <!-- corpus-invariante:fin:co-explore.SKILL.md.ada44733310a -->
   capacidad, nunca por nombre de tool: algoritmo canónico en
   `cross-review/reference.md` → "Descubrir el revisor"; fundamento de la excepción en
   `reference.md` → "Excepción de familia (topología dual)".
8. **El conductor arbitra, no explora.** En la rama nominal no construye un mapa propio del
   repositorio: lee siempre el índice completo de cada worker y abre detalle **solo** por
   disparador. Cuatro cosas no son explorar y siguen vigentes — ver "Lectura selectiva" y
   `reference.md` → "Carve-outs de la regla del conductor".

## Corridas delegadas en vuelo

Todo worker que esta skill despacha nace con su **sobre** en `.cross-model/active/<skill>/`, escrito
**antes del preflight**, y mientras el sobre siga activo cada turno del conductor cierra informando
su estado. Con manifest habilitado, la selección fija `families`/`selection`, el sobre nace con
`manifest_seed` inmutable y `manifest_first_dispatch_at: null`, y el orden de `families` gobierna el
fan-out. Inmediatamente antes de la primera tool call se fija el timestamp una sola vez; los
despachos posteriores no cambian el transporte ni el inicio históricos. Los puntos propios son dos:

- **fan-out dual** — un worker por familia en `explore`, `counter-plan` e `investigate`, los dos
  lanzados antes de esperar a ninguno
- un worker por ronda del modo `debate`, incluida la ronda 0

Campos del sobre, transiciones, sonda por turno, cosecha y condiciones del retiro:
`corridas-en-vuelo.md`, hermano de este archivo. Es la regla normativa; acá solo se enumera dónde
aplica.

## Red flags — detente y reconsidera

Las reglas de arriba dicen *qué* hacer; esta sección frena los atajos que aparecen *en el
momento*. Ley fundamental:

> **DOS MAPAS INDEPENDIENTES O NINGUNO.** El valor está en la divergencia, no en una
> coincidencia forzada. Contaminar el paquete de contexto o leer el informe antes de tiempo
> mata la señal (regla 2).

Si reconoces alguno de estos pensamientos, detente y vuelve a la regla que estás por saltear.

| Racionalización | Realidad |
|---|---|
| "Le paso a un worker mi hipótesis para que no pierda tiempo" | Rompe la independencia (regla 2): los dos arrancan solo con el paquete de contexto, idéntico. |
| "Abro el detalle completo, total ya lo tengo en disco" | `cat detail-*` anula el ahorro que este contrato compra. Índice siempre; detalle solo por disparador y solo por ID. |
| "Un worker no contestó, espero un poco más" | Deadline duro (regla 5) y **por worker**, desde su propio lanzamiento: matarlo, clasificarlo y resolver la rama con lo que haya. |
| "Su enfoque se ve bien, lo adopto y listo" | Los enfoques compiten en el cierre: evaluar en méritos y registrar el porqué; viables pero distintos = divergencia al checkpoint. |
| "Su duda la respondo yo mentalmente y sigo" | Las Incógnitas que cambiarían el diseño van a `clarify`; las respuestas quedan en `## Clarifications` de la spec. |
| "Acá el problema es el test, no el código" (en `investigate`) | Puede serlo, y por eso está en el espacio de hipótesis — con la misma vara que las demás: observable, autoridad y refutación. Sin evidencia de respaldo va como **incógnita**, nunca como hipótesis líder. |
| "El worker con MCP explora mejor, le dejo el entorno" | El aislamiento no es opcional: sin él hereda memoria, hooks y tools que pueden alcanzar cosas fuera del working dir. Sin garantía, `UNAVAILABLE`. |
| "Lanzo uno, veo qué devuelve, y después lanzo el otro" | Duplica la latencia cumpliendo la letra. El orden es preparar · truncar · lanzar A · lanzar B · esperar; `execution` decide cuándo vuelve el control, no la concurrencia. |
| "Trunco al entrar al modo, así arranco limpio" | Truncar antes de decidir destruye el artefacto de cierre que la retoma necesita leer, y convierte cada retoma en un redespacho. Primero decidir, después truncar. |
| "El índice ya me dice bastante, no hace falta el detalle" | Al revés del anterior, y también un error: divergencia, `high`, `low` o una decisión a arbitrar **obligan** a abrir esa entrada. |

<!-- inventario-familias:inicio -->
### Inventario de familias

Antes de cualquier preflight, la **raíz** de la corrida resuelve una vez la selección de workers
despachables. El conductor conduce y no entra en `families`; cada worker es un proceso aparte en
sesión fresca. Si el contrato de invocación trae `family_inventory`, **no se resuelve nada**: se
heredan `families` y `selection`, no se relee config y no se vuelve a avisar.

| Paso | Regla |
|---|---|
| 1 — workers **declarados** | comprobar el CLI en PATH de cada familia de `families`, **la del conductor incluida**. Que el conductor esté corriendo por construcción no exime del preflight de su worker |
| 2 — **sin declaración** | solo si no hay declaración, detectar qué CLIs están en PATH para proponer la selección. POSIX: `command -v codex` / `command -v claude`. PowerShell: `Get-Command codex -ErrorAction SilentlyContinue`. Nada más cuenta |

Los dos pasos miden el CLI porque es **condición necesaria de todas las vías**: el runtime del subagente
resuelve su disponibilidad corriendo `codex --version` y `codex app-server --help`, así que exige el
CLI y algo más. No es la intersección restrictiva, es el piso común.

La auditoría **no comprueba versión, auth, aislamiento ni lanzamiento**, y **no afirma capacidad
operativa**: una familia presente puede fallar igual su preflight, y eso sigue siendo un fallo real.

`selection` conserva cómo se resolvió la lista: `full` abarca todas las familias presentes y
`user_choice` declara menos. Se persiste con `families`, se hereda y nunca se reconstruye sondeando.

**Declarado ↔ disponible:**

| Caso | Resultado |
|---|---|
| no declara una familia presente | preferencia válida; no se sondea ni se despacha ese worker |
| declara una familia cuyo CLI está ausente | **error**: nombra la familia y que la auditoría no la encuentra |

`families: []` sigue siendo error. La allowlist admite solo `claude | codex`, sin duplicados y
canonizada a minúsculas.
<!-- inventario-familias:fin -->

<!-- corpus-invariante:inicio:co-explore.SKILL.md.47d290a6ecc7 -->

En `debate`, la familia opuesta sigue siendo el default y la recomendación. Si la selección obliga

<!-- corpus-invariante:fin:co-explore.SKILL.md.47d290a6ecc7 -->
a la familia del conductor, se lanza un worker fresco de esa familia y se declara que se perdió la
ruptura de correlación cross-family; el conductor no debate consigo mismo. El modo hereda la
selección sin repetir el preflight ni el aviso de la raíz.

## Contrato de invocación (lo que pasa la skill llamadora)

Al invocarla, `sdd-flow`/`sdd-orchestrator` (o el usuario en modo directo) proveen:

- **`mode`** — `explore` (pre-spec) | `counter-plan` (pre-plan/pre-reparto) | `investigate`
  (standalone, investigar un bug fuera de todo flujo SDD) | `debate` (decisión abierta entre
  opciones).
- **`context_package`** — digest del ticket + prompt del usuario + AC preliminares si existen +
  **evidencia observada de reproducción** si la hubo (consola/red/pasos, capturada por la
  llamadora ANTES de despachar: el explorador es headless y no puede abrir URLs; ver el `<task>`
  del prompt). La evidencia viaja como hechos observados, nunca como hipótesis de la llamadora.
  En `counter-plan`: **núcleo común byte-idéntico** para ambos workers (la `spec.md` o
  `master-spec.md` aprobada + los paths de `domain_context`) **+ un anexo privado** con el índice y
  el detalle **de la propia familia** en la fase `explore`, y solo si ese worker quedó `READY`. El
  anexo viaja **concatenado dentro del prompt**, nunca como una ruta: en multi-repo cae fuera del
  `working_dir`. El artefacto de la otra familia está prohibido, y "fresco" significa **sesión
  nueva, sin resume**.
  En `investigate`: síntoma reportado del bug + evidencia de reproducción observada
  (consola/red/pasos/stacktrace) si la hubo + prompt del usuario + **el criterio de éxito y su
  procedencia**, cuando existan. No hay ticket ni AC necesariamente; la evidencia de repro viaja
  como hechos observados, igual que en `explore`.
  El **criterio de éxito** es lo que define que el bug está resuelto: el test que falla, el
  requisito, o la expectativa del usuario. Su **procedencia** es de dónde sale esa autoridad (un
  AC, una decisión de producto, el juicio de quien reporta). Va en el paquete porque sin él la
  hipótesis de que el criterio sea el defectuoso no se puede sostener ni descartar — ver "Alcance
  de `investigate`".
  En `debate`: la **decisión a resolver** + las **opciones en juego** (si el usuario las dio;
  si no, el conductor las deriva y las declara explícitas) + el contexto de código/artefactos
  relevante. Cuando lo invoca sdd-flow: la ambigüedad de `clarify` o el trade-off contestable del
  `plan`, con `spec.md`/`plan.md` como contexto.
- **`working_dir`** — uno, o una lista de repos cuando llama el orquestador (exploración
  cross-repo).
- **`family_inventory`** — selección declarada y resuelta por la raíz, con `families`, `source`,
  `selection` y `root`. La skill **hereda la elección** sin releer config, repetir la auditoría ni
  reanunciar; si falta, esta invocación resuelve antes de despachar.
- **`complexity`** — `trivial | normal | complex`; modula profundidad/esfuerzo.
- **`execution`** — `auto | sync | background`. Para `explore` e `investigate` el valor útil es
  `background`: el conductor explora/investiga mientras tanto. En `counter-plan` o si el
  conductor no puede lanzar background, se espera con tope (`sync`). En `debate` el loop es
  secuencial (rondas de cruce), como `cross-review`: se espera cada ronda con tope duro.
- **`deadline`** — opcional; defaults 600s (`explore`), 300s (`counter-plan`), 600s
  (`investigate`), ver `reference.md` → "Latencia y deadlines"; en `debate`, deadline **por
  ronda** (default 300s/ronda) más el tope `max_rounds`.

### Pasos de ejecución

1. **Preflight de aislamiento** (fail-closed) y de cada CLI declarado. Con `family_inventory`, no
   sondear familias fuera de la allowlist; sin selección heredada, resolverla antes. Sin CLI para un
   worker declarado → `UNAVAILABLE`; con una sola familia seleccionada → la escalera decide la rama.
2. **Armar uno o dos prompts** desde `reference.md` → "Prompt de explore (dos capas)", con el mismo
   paquete de contexto. En `counter-plan`, núcleo común byte-idéntico + anexo privado de la propia
   familia, concatenado por el shell.
3. **Decidir retoma antes de truncar** (ver "Retoma"), y solo si corresponde redespachar, truncar
   las rutas exactas del modo.
4. **Lanzar los dos, y recién entonces esperar.** El orden es fijo: preparar · truncar · lanzar A ·
   lanzar B · esperar. `execution: sync | background` gobierna **cuándo vuelve el control a la
   llamadora**, nunca la concurrencia: lanzar uno, esperarlo y después lanzar el otro duplica la
   latencia cumpliendo la letra. Cada deadline corre desde **su** lanzamiento.
5. **Punto de encuentro:** por cada worker, validar y clasificar en `READY` / `INVALID` /
   `UNAVAILABLE` (`reference.md` → "Estados del worker"), partir su salida en índice y detalle, y
   resolver la rama de la escalera.
6. **Arbitrar** con la lectura selectiva y escribir el artefacto de cierre con publicación atómica.

Receta completa en `reference.md` → "Fan-out dual y orden de lanzamiento".

## Lectura selectiva

El conductor lee **siempre** el índice completo de cada contribuyente. Abre una entrada del detalle
**solo** ante uno de estos cuatro disparadores, todos decidibles leyendo la fila del índice:

| Disparador | Cómo se reconoce |
|---|---|
| divergencia entre contribuyentes | dos entradas sobre lo mismo que no coinciden, **o una sola** cuando el otro no vio nada |
| alto riesgo | `severidad = high` |
| baja confianza | `confianza = low` |
| decisión que arbitrar | dos enfoques viables y distintos |

**Abrir el archivo de detalle completo está prohibido.** `cat detail-*` anula el ahorro que este
contrato compra: la única forma de abrir una entrada es por su ID, cortando en el siguiente heading
(`reference.md` → "Apertura puntual de una entrada").

**El árbitro sí puede verificar la evidencia.** Ante un disparador puede leer los `path:line` que
cita **esa** entrada, y registra qué IDs verificó. Sin eso, ante una divergencia factual solo podría
elegir entre dos narraciones y los punteros del índice serían decorativos. Es acotado: lecturas
puntuales de entradas disparadas, **nunca** búsquedas amplias ni un mapa propio.

## Retoma

Un flujo SDD puede pausarse y retomarse en una sesión nueva. La regla es binaria:

- **Existe el artefacto de cierre del modo y valida** → la corrida terminó: se usa lo que hay, sin
  recalcular rama ni diversidad (el cierre las lleva como campos cerrados). Vale en sus **dos**
  formas: síntesis en las ramas 1-3, cierre conductor-only en la rama 4.
- **No existe o no valida, y el consumidor tampoco** → se **redespacha** el modo completo. Los
  workers son baratos y no consumen contexto del conductor: redespachar sale más barato que
  reconstruir un estado parcial.
- **No existe o no valida, pero el consumidor ya está escrito** → **falla cerrado**: sin anexo, sin
  seed, sin contexto de co-explore, declarado en una línea. Redespachar acá podría traer un riesgo
  `high` que ese artefacto —quizá ya aprobado en su gate— nunca arbitró.

El orden importa: **primero decidir, después truncar**. Detalle, matriz de consumidores y los dos
ejes (artefacto vs capacidad actual) en `reference.md` → "Decisión de retoma".

## El loop de debate (modo `debate`)

A diferencia de los otros modos (una sola pasada), `debate` itera: el conductor participa como una
<!-- corpus-invariante:inicio:co-explore.SKILL.md.3c9f87861874 -->
voz y el worker seleccionado forma la otra. La familia opuesta es el default; con selección
<!-- corpus-invariante:fin:co-explore.SKILL.md.3c9f87861874 -->
same-family se conserva una sesión fresca, se declara el costo y se recomienda revisión humana. El
conductor sintetiza y el usuario arbitra. R0 son posturas independientes (regla 2), R1..N cruzan y
critican con tope duro `max_rounds`, y la síntesis **no elige ganador**.

La mecánica completa —las cuatro etapas del loop, la síntesis atribuida por familia, y la frontera
publicado vs local que decide qué puede nombrar a las familias y qué no— vive en `reference.md` →
"Mecánica del modo `debate`".

## Salida — el envelope

`co-explore` devuelve un **envelope agregado**, no un estado singular. La llamadora decide con él
sin abrir ningún informe: `outcome` (`completed` | `map_failure`) · `branch` · `diversity` ·
`workers[]` (familia, **estado** —`READY` · `INVALID` · `clarification-needed` · `UNAVAILABLE`—,
**causa** —`confirmed_wall` · `launch_flake` · `runtime_failure` · `deadline_exceeded` ·
`host_sandbox_wall`—, paridad,
rutas de índice y detalle, sesión) ·
`contributors[]` (todo mapa aceptado, incluido el del conductor en ramas degradadas, con `session`
nullable). Esquema campo por campo en `reference.md` → "Envelope de retorno".

`contributors[]` existe porque en las ramas 2, 3 y 4 aparece un mapa que **ningún worker produjo**
y que `workers[]` no puede describir.

**El envelope proyecta además el manifest de corrida.** La secuencia es selección → seed/sobre →
preflight → timestamp write-once → primera tool call → terminal. `completed`, `map_failure`, las
ramas 1–4 y las causas `confirmed_wall`, `launch_flake`, `runtime_failure` y `deadline_exceeded`
cierran desde esas autoridades; un preflight sin worker seleccionado o sin vía resuelta conserva
`manifest_first_dispatch_at: null` y usa `preflight_started_at`/`transport: none`. Si la vía ya
estaba resuelta y su preflight falla, el seed conserva esa vía aunque no haya despacho. El objeto nuevo nunca toma `.cross-model/runs/` como
fuente. Esquema, comparabilidad y creación sin reemplazo en `cross-review/reference.md` → "Manifest
de corrida".

**Nota de límite (obligatoria, una vez por corrida).** Toda salida presentada al usuario cierra
declarando el techo del método:

> Dos exploraciones independientes aumentan la cobertura; no garantizan correctitud. Un punto
> ciego compartido por ambas familias queda sin detectar.

Va **una sola vez**, al final de la conclusión presentada, no repetida por sección ni por ronda.
Cuando la corrida fue de una sola voz (rama 4), esta es la línea donde se declara. Es local y
conversacional: **no** viaja a `spec.md` ni a `plan.md`, que siguen limpios de método.

## La síntesis (guía para la skill llamadora)

La ejecuta **el conductor** en todos los casos: los callers SDD en modo embebido y el propio
conductor en modo directo. Vive acá una sola vez para que nadie la duplique.

1. **Comparar por ID, no informes completos.** Cada convergencia y cada divergencia se ancla a los
   IDs concretos de los contribuyentes. Comparar "sección por sección" dos informes enteros anula
   el ahorro que la lectura selectiva compra.
2. **La ausencia es una divergencia de primera clase.** Si un contribuyente vio algo que el otro no,
   la fila lleva `∅` en el lado ausente y al menos un ID real. Exigir IDs de ambos lados obligaría a
   descartar el hallazgo o a fabricar una correspondencia — y esa asimetría es justamente donde vive
   el valor cross-model, así que **dispara** la lectura del detalle existente.
3. **Registrar qué se abrió y qué se verificó.** `## Detalles abiertos` deja la traza de la lectura
   selectiva: sin ella no hay forma de auditar si el conductor leyó de más o de menos.
4. **Duelo de enfoques con rationale auditable**, y las **incógnitas fusionadas** de todos los
   mapas: las que cambiarían el diseño alimentan `clarify`.
5. **Publicación atómica**: temporal → validar el predicado completo → renombrar. Un archivo escrito
   a medias puede contener solo IDs válidos y satisfacer un predicado flojo.
6. **Las divergencias no resueltas** se presentan en un checkpoint informativo de la llamadora antes
   de escribir la spec/plan — solo si quedaron sin resolver.
7. **Los entregables hablan del objeto, no del método.** Los artefactos que la llamadora escriba
   después se redactan en términos de los hallazgos, **sin** mencionar la mecánica: ni
   "conductor/worker", ni nombres de modelos, ni rutas de `co-explore/`. Esa trazabilidad ya vive en
   el artefacto de cierre. Las divergencias no resueltas se presentan como **posiciones alternativas
   con su evidencia**, sin atribuirlas.

   **Tres excepciones acotadas, todas conversacionales.** La **nota de límite**, la **advertencia de
   una sola voz** y el **aviso de corridas delegadas en vuelo** sí hablan del método, y deben
   hacerlo: sin ellas el usuario no sabe con qué cobertura está decidiendo, ni qué trabajo delegado
   sigue corriendo cuando cierra el turno. La lista es **cerrada**: nada más del método sale del
   artefacto de cierre.

Plantillas, cabecera de campos cerrados y el predicado completo del cierre: `reference.md` →
"Plantillas de cierre" y "Predicado del artefacto de cierre".

**En `investigate`** la síntesis es *bug-shaped*: en vez del duelo de enfoques va un **duelo de
hipótesis de causa raíz** y el cierre es **hipótesis líder + plan de verificación**. Si los mapas
divergen en la causa y no se resuelve, se presentan ambas posiciones con su evidencia, sin
atribuirlas.

## Alcance de `investigate`

`investigate` **termina en la conclusión sintetizada**: hipótesis de causa raíz rankeadas +
plan de verificación. NO verifica ejecutando como parte de la skill y NO arregla. La razón es
de diseño, no de purismo: el valor cross-model vive en el **espacio de hipótesis** (dos modelos
tienen puntos ciegos distintos y proponen causas raíz distintas — esa divergencia es la señal);
**verificar es determinístico** (corrés el repro y confirma o no) y lo hace un solo modelo, sin
valor en duplicarlo.

- **Revisor: L0 read-only siempre.** Su aporte es la lente independiente al leer; ejecución en
  un proceso headless es frágil y no suma.
- **Conductor: L0 por defecto, L1 opt-in.** Para bugs de runtime puede ejecutar (reproducir,
  correr tests, logging efímero) en un worktree descartable, sin persistir en tu árbol (regla
  1). L1 rinde sobre todo **en la síntesis, para adjudicar divergencias**: correr algo que
  desempate entre las dos hipótesis (p. ej. el revisor sospecha una race → el conductor corre
  con el sanitizer y verifica). Mecánica del worktree en `reference.md` → "Capacidades y worktree (`investigate`)".
- **Handoff:** verificar/arreglar de verdad es el paso siguiente y es de **otra skill**
  (`superpowers:systematic-debugging`), que el conductor ofrece en su rol normal. Las hipótesis
  rankeadas + plan de verificación son su input directo. Editar/proponer parches en paralelo
  (una "carrera de fixes cross-model") sería otra skill distinta — **no** está en co-explore.

### El criterio de éxito también es una hipótesis

El espacio de hipótesis no se agota en el código: un bug que resiste puede ser un **criterio de éxito
defectuoso**, y esa hipótesis compite con las demás desde la primera pasada. Como cualquier otra,
declara **observable · autoridad · refutación** antes de rankearse; sin evidencia de respaldo va como
**incógnita**, nunca como hipótesis líder — es la salida cómoda de este modo y lleva la misma vara,
no una más baja.

La tabla de las tres columnas y su fundamento: `reference.md` → "El criterio de éxito también es una
hipótesis (`investigate`)".
## Configuración

Clave **top-level** `co_explore` (hermana de `cross_review`, **no** anidada — son ortogonales) en
`.specify/config.yml` (sdd-flow) o en el `manifest.yml` de la orquestación (sdd-orchestrator).
**Gobierna solo los modos `explore`/`counter-plan` (callers SDD); `investigate` es standalone y
no lee config:**

```yaml
co_explore:
  mode: auto        # auto (por complejidad: complejo on, normal opt-in, trivial nunca) | "on" | "off"
  deadline: 600     # segundos (explore; counter-plan usa 300 salvo override)
  debate:           # modo debate — soporte a decisiones (independiente de mode; lo ofrece sdd-flow)
    mode: auto      # "off" | "on" | auto  — cuándo se OFRECE el debate (nunca corre sin confirmación)
    max_rounds: 3   # tope de rondas de cruce
                     # NO hay bloque `workers`: cuántos se despachan y de qué familia lo fija la topología dual (regla 7), no el config
```

Precedencia (igual que el resto de overrides SDD): **override conversacional de la corrida >
config > default por complejidad**. Default por complejidad: `complex` on, `normal` opt-in
(off salvo pedido), `trivial` nunca. `deadline` por defecto: 600s en `explore` (una
exploración tarda más que una crítica), 300s en `counter-plan`, ver `reference.md` → "Latencia
y deadlines".

El sub-bloque `debate` es **independiente** de `co_explore.mode` (se puede querer debate sin haber
corrido la exploración pre-spec). `debate.mode`: `off` nunca ofrece; `auto` ofrece solo en
decisiones complejas / high-stakes (auth, pagos, migraciones de datos o schema, concurrencia,
cambios difíciles de revertir) o cuando el conductor está genuinamente inseguro; `on` ofrece en
cualquier decisión contestable de `clarify`/`plan`. En **todos** los casos **ofrece y espera un
"sí"** — nunca corre el debate solo. `investigate` sigue sin leer config; `debate` standalone
tampoco.

`co_explore` es **ortogonal** a `cross_review.mode`: esta clave gobierna la exploración
paralela y el contra-enfoque; `cross_review.mode` gobierna las críticas en los gates. Quien
lee ambas y orquesta es la skill llamadora (`sdd-flow`/`sdd-orchestrator`), nunca esta skill.

## Degradación

Ninguna rama bloquea el flujo. La escalera está ordenada por **diversidad conservada**, y "válido"
significa `READY` (ver `reference.md` → "Estados del worker"):

| Rama | Situación | Qué hace el conductor | Qué se declara |
|---|---|---|---|
| **1** | dos workers válidos | arbitra, no explora | nominal · `cross_family` |
| **2** | sobrevive el de la **otra** familia | **explora** (topología anterior) | diversidad conservada, ahorro perdido |
| **3** | sobrevive el de la **misma** familia | **explora** | **diversidad reducida** · `same_family` |
| **4** | cero workers válidos | **explora**; cierre conductor-only | una sola voz · `single_voice` |

Un worker en **`clarification-needed`** frenó ante una ambigüedad que le impide seguir, pero
**entregó lo que alcanzó a mapear**. El conductor intenta resolver la pregunta desde el paquete o el
repo antes de escalarla; si la resuelve, redespacha ese worker y la escalera se evalúa de nuevo. Si
no, el worker baja a la rama que corresponda y su entrega parcial se conserva como contribuyente
(`reference.md` → "`clarification-needed` — el cuarto estado").

Fuera de la escalera: **`FALLO_DE_MAPA`** — el conductor no logró escribir un mapa válido en dos
intentos. Es terminal, no pasa contexto de co-explore y va directo al gate humano. No es la rama 4:
esa exige cero workers válidos, y acá puede haber uno `READY`.

**La rama 4 es el "ninguno" de la regla, nombrado.** El conductor presenta igual su análisis con una
advertencia de una línea —corrió con una sola voz, sin contraste cross-model—, **no escribe
`synthesis.md`** (las plantillas presuponen dos mapas; una síntesis de una voz obligaría a fabricar
el segundo) y persiste su cierre en un archivo inequívocamente distinto. La regla "DOS MAPAS
INDEPENDIENTES O NINGUNO" no se relaja: esta rama *es* el ninguno.

**Una causa que no agrega una rama.** Es **causa de degradación**, no estado: acompaña al terminal
que la escalera ya resolvió.

- **`deadline_exceeded`** — un worker venció su deadline sin marcador de cierre. Antes se registraba
  como `runtime_failure`, que sugiere una falla de infraestructura que no ocurrió: arrancó bien y el
  corte lo puso el conductor. Baja a la rama que corresponda igual que cualquier worker no válido.
**Causas de indisponibilidad** (`confirmed_wall` · `launch_flake` · `runtime_failure` ·
`deadline_exceeded` · `host_sandbox_wall`) y su política
de reintento: `reference.md` → "Estados del worker". Una pared confirmada no se reintenta.

## Router de intención

> **¿Es este el peldaño que hace falta?** La escalera de rigor —respuesta local → `co-explore` →
> `cross-review` → `cross-implement` → `verify`— dice cuál es la opción **más barata que
> alcanza**, que casi nunca es la más completa: `co-explore/reference.md` → "Escalera de rigor".

| El usuario dice (ej.) | Acción |
|---|---|
| "/co-explore `<ticket|descripción>`" | modo directo: `mode: explore`, corre la síntesis y presenta la conclusión |
| "que Codex explore esto en paralelo" | modo directo `explore`, mismo flujo que arriba |
| "/co-explore `<bug>`", "por qué falla X", "que Codex investigue este bug en paralelo" | modo directo: `mode: investigate`, corre la síntesis, presenta hipótesis rankeadas + plan de verificación, y ofrece el handoff a `systematic-debugging` |
| "/co-explore debate `<decisión>`", "no sé si X o Y, que lo debatan", "somete esto a debate" | modo directo: `mode: debate`, corre el loop de rondas + síntesis neutral atribuida, y presenta las posturas para que decidas |
| "con debate" / "sin debate" (en un flujo SDD) | override `on`/`off` del ofrecimiento de debate para la corrida — lo registra la llamadora |
| "stress-test de este plan/idea" (enfoque ya elegido) | **no es co-explore**: es `cross-review` (modo draft) — crítica adversarial de una decisión ya tomada. co-explore aplica cuando el terreno está abierto: **mapa antes que veredicto** |
| "con co-exploración" | override `on` para la corrida — lo registra la llamadora |
| "sin co-exploración" | override `off` para la corrida — lo registra la llamadora |
| (invocada por `sdd-flow`/`sdd-orchestrator` post-`gather-context` o pre-`plan`/reparto) | modo embebido (`explore`/`counter-plan`): explorar y devolver informe + resumen, sin STOP propio |

## Referencias internas

- `reference.md` — "Prompt de exploración" (por modo, incluido `investigate`), "Formato del
  informe" (+ variante bug-shaped), "Plantilla de `synthesis.md`", "Plantilla de síntesis —
  `investigate`", "Capacidades y worktree (`investigate`)", "Descubrir el revisor (puntero +
  fallback)", "Latencia y deadlines", "Árbol de rutas", "Prompt de debate" (ronda
  0 + cruce), "Plantilla de `debate.md`".
- `README.md` — qué es, cuándo usarla, requisitos e instalación.
