---
name: co-explore
description: >-
  Exploración paralela cross-model: un modelo de otra familia que el autor
  (Codex cuando conduce Claude; Claude cuando conduce Codex) explora el código
  en background, read-only, y devuelve un informe estructurado propio; el
  conductor explora en paralelo y sintetiza los dos mapas independientes. Cuatro
  modos: "explore" (mapear terreno antes de una spec), "counter-plan"
  (contra-enfoque antes de un plan/reparto), "investigate" (investigar un bug:
  hipótesis de causa raíz rankeadas + plan de verificación, sin arreglar) y
  "debate" (ayudar a decidir entre opciones abiertas cuando no estás seguro:
  las dos familias forman posturas independientes, se critican en rondas y el
  conductor sintetiza sin elegir).
  explore/counter-plan los invocan sdd-flow y sdd-orchestrator cuando
  co_explore está activo; investigate es standalone, fuera de todo
  flujo SDD. Invocación directa: "/co-explore <ticket|descripción|bug>", "que
  Codex explore esto en paralelo", "que Codex investigue este bug en paralelo",
  "/co-explore debate <decisión>" o "no sé si X o Y, que Codex y tú lo debatan".
  NO revisa artefactos escritos (eso es cross-review) ni arregla el bug (eso
  es systematic-debugging): produce hallazgos e hipótesis propios que compiten
  con los del conductor. No invocarla espontáneamente: solo ante un pedido
  explícito del usuario o invocada por sdd-flow/sdd-orchestrator.
---

# co-explore — dos mapas independientes que convergen

Helper que despacha a un modelo de otra familia (Codex cuando conduce Claude; Claude cuando
conduce Codex) a explorar el mismo código en background, read-only, y a devolver un informe
estructurado propio; mientras tanto el conductor hace su propia exploración — no hay espera
secuencial, ambos avanzan en paralelo — y al final el conductor **sintetiza** los dos mapas.
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
paquete de contexto ──► [co-explore: revisor explora en background, read-only]
                              │                        (el conductor explora en paralelo
                              ▼                         por su cuenta — no espera)
                    informe-<familia>.md ──► síntesis del conductor ──► spec / plan / conclusión
                    (+ session.json opcional)   (convergencias/divergencias, competencia de
                                                 enfoques o de hipótesis de causa raíz)
```

## Reglas no negociables

1. **No persiste nada en tu árbol.** El invariante de seguridad: el **revisor** nunca escribe ni
   ejecuta — se invoca read-only (sin permisos de escritura) y su salida se captura por
   redirección del conductor hacia `co-explore/scratch/`, nunca porque tenga permiso para tocar
   archivos (ver `reference.md` → "Archivos de trabajo (scratch)"). El **conductor** nunca
   persiste cambios en el working tree del usuario. En `explore`/`counter-plan` ambos son
   read-only puro. En `investigate` el conductor puede, opt-in (L1), **ejecutar** para investigar
   —reproducir, correr tests, logging efímero— pero SOLO en un **worktree descartable** que se
   tira al cerrar; el revisor sigue L0 read-only siempre y lee un checkout estable, nunca el
   worktree que el conductor está mutando (ver `reference.md` → "Capacidades y worktree
   (investigate)").
2. **Independencia (anti-anclaje).** El explorador arranca únicamente con el paquete de
   contexto: nunca recibe hallazgos, hipótesis ni borradores del conductor. Es simétrico — la
   skill llamadora tampoco lee `findings-<familia>.md` del revisor hasta haber cerrado su
   propia exploración y escrito su propio informe. El valor está en dos mapas sin contaminar,
   no en uno que copia al otro.
   En `debate` la independencia rige la **ronda 0** (ambas familias forman su postura a ciegas,
   sin verse); de la ronda 1 en adelante el **cruce** de posturas es deliberado (cada una critica
   la del otro) — es la excepción diseñada de este modo, no una violación de la independencia.
3. **Nunca se bloquea por dudas.** El explorador corre no-interactivo: no puede preguntar a
   mitad de camino ni esperar una respuesta. Toda duda se registra y se sigue explorando — una
   pregunta abierta que no pudo resolver va a `## Incógnitas`; una decisión que tomó para
   poder seguir avanzando va a `## Supuestos`, con el porqué.
4. **Informe estructurado o nada.** La salida tiene que respetar el "Formato del informe"
   (`reference.md`). Si la respuesta del revisor no parsea contra ese formato, se degrada: se
   conserva como texto libre si aporta contexto, o se descarta si es ruido — y en cualquier
   caso se registra la degradación.
5. **Loop acotado, deadline duro.** En `explore`/`counter-plan`/`investigate`, **una sola pasada
   por modo — sin rondas**. La excepción es `debate`: es el único modo con **loop acotado** de
   rondas de cruce (default 3, tope duro `max_rounds`), como `cross-review`; igual tiene deadline
   duro **por ronda** → al vencer se mata el proceso del explorador y se devuelve `UNAVAILABLE`
   con lo que haya. Nunca se espera de forma indefinida.
6. **Opcional y degradable.** Es una capacidad, no un requisito. Sin revisor de otra familia
   disponible, con un fallo en runtime, o con `mode: off`, el resultado es `UNAVAILABLE` en una
   línea y la llamadora sigue con la exploración del conductor solamente.
7. **Revisor de OTRA familia, por capacidad.** Misma regla 7 de `cross-review`: hay dos
   familias — Claude y GPT/Codex —, el autor es la del agente que conduce la skill (sin importar
   la superficie: CLI, app de escritorio, IDE, web) y el revisor es siempre el de la otra. El
   algoritmo canónico vive en
   `cross-review/reference.md` → "Descubrir el revisor"; acá solo el puntero + un fallback
   mínimo (ver `reference.md` → "Descubrir el revisor (puntero + fallback)").

## Red flags — detente y reconsidera

Las reglas de arriba dicen *qué* hacer; esta sección frena los atajos que aparecen *en el
momento*. Ley fundamental:

> **DOS MAPAS INDEPENDIENTES O NINGUNO.** El valor está en la divergencia, no en una
> coincidencia forzada. Contaminar el paquete de contexto o leer el informe antes de tiempo
> mata la señal (regla 2).

Si reconoces alguno de estos pensamientos, detente y vuelve a la regla que estás por saltear.

| Racionalización | Realidad |
|---|---|
| "Le paso al explorador mi hipótesis para que no pierda tiempo" | Rompe la independencia (regla 2): el valor está en dos mapas sin contaminar. Solo viaja el paquete de contexto. |
| "Miro su informe mientras exploro, total ya terminó" | El conductor no lee `findings-*` hasta cerrar y escribir su propio informe. |
| "El explorador no contestó, espero un poco más" | Deadline duro (regla 5): matar el proceso, `UNAVAILABLE`, seguir con lo propio. |
| "Su enfoque se ve bien, lo adopto y listo" | Los enfoques compiten en la síntesis: evaluar en méritos y registrar el porqué en `synthesis.md`; enfoques viables pero distintos = divergencia al checkpoint. |
| "Su duda la respondo yo mentalmente y sigo" | Las Incógnitas que cambiarían el diseño van a `clarify`; las respuestas quedan en `## Clarifications` de la spec. |

## Contrato de invocación (lo que pasa la skill llamadora)

Al invocarla, `sdd-flow`/`sdd-orchestrator` (o el usuario en modo directo) proveen:

- **`mode`** — `explore` (pre-spec) | `counter-plan` (pre-plan/pre-reparto) | `investigate`
  (standalone, investigar un bug fuera de todo flujo SDD) | `debate` (decisión abierta entre
  opciones).
- **`context_package`** — digest del ticket + prompt del usuario + AC preliminares si existen +
  **evidencia observada de reproducción** si la hubo (consola/red/pasos, capturada por la
  llamadora ANTES de despachar: el explorador es headless y no puede abrir URLs; ver el `<task>`
  del prompt). La evidencia viaja como hechos observados, nunca como hipótesis de la llamadora.
  En `counter-plan`: ruta de la `spec.md` (o `master-spec.md`) aprobada + ruta del propio
  `findings-<familia>.md` de la fase `explore`, con resume oportunista del thread si
  `session.json` lo permite, o sesión fresca con esos archivos si no.
  En `investigate`: síntoma reportado del bug + evidencia de reproducción observada
  (consola/red/pasos/stacktrace) si la hubo + prompt del usuario. No hay ticket ni AC
  necesariamente; la evidencia de repro viaja como hechos observados, igual que en `explore`.
  En `debate`: la **decisión a resolver** + las **opciones en juego** (si el usuario las dio;
  si no, el conductor las deriva y las declara explícitas) + el contexto de código/artefactos
  relevante. Cuando lo invoca sdd-flow: la ambigüedad de `clarify` o el trade-off contestable del
  `plan`, con `spec.md`/`plan.md` como contexto.
- **`working_dir`** — uno, o una lista de repos cuando llama el orquestador (exploración
  cross-repo).
- **`complexity`** — `trivial | normal | complex`; modula profundidad/esfuerzo.
- **`execution`** — `auto | sync | background`. Para `explore` e `investigate` el valor útil es
  `background`: el conductor explora/investiga mientras tanto. En `counter-plan` o si el
  conductor no puede lanzar background, se espera con tope (`sync`). En `debate` el loop es
  secuencial (rondas de cruce), como `cross-review`: se espera cada ronda con tope duro.
- **`deadline`** — opcional; defaults 600s (`explore`), 300s (`counter-plan`), 600s
  (`investigate`), ver `reference.md` → "Latencia y deadlines"; en `debate`, deadline **por
  ronda** (default 300s/ronda) más el tope `max_rounds`.

### Pasos de ejecución

1. **Resolver el revisor** (regla 7). Sin revisor de otra familia disponible → `UNAVAILABLE`.
2. **Armar el prompt** desde `reference.md` → "Prompt de exploración" (una variante por modo),
   con el paquete de contexto inline.
3. **Lanzar en background, read-only**, con el stdout redirigido a
   `co-explore/scratch/explorer.out`; guardar el PID y, si el runtime lo expone, la referencia
   de sesión en `co-explore/session.json`.
4. En `explore`, **devolver el control de inmediato** ("explorando en background") — la
   llamadora hace su propia exploración y vuelve a consultar en el punto de encuentro. En
   `counter-plan` o con `execution: sync`, esperar con tope.
5. **Punto de encuentro:** si el explorador terminó, normalizar la salida al "Formato del
   informe" y escribirla en `co-explore/findings-<familia>.md` (`explore`),
   `co-explore/counter-plan-<familia>.md` (`counter-plan`) o
   `co-explore/investigate-<familia>.md` (`investigate`) — ver `reference.md` → "Archivos de
   trabajo (scratch)". Si venció el `deadline`, matar el proceso y devolver `UNAVAILABLE`.

**Modo directo** (el usuario invoca `/co-explore <ticket|descripción|bug>` o pide en lenguaje
natural una exploración/investigación paralela):

1. **Inferir el modo desde la intención.** Un bug, error o "por qué falla X" → `investigate`;
   una decisión abierta entre opciones ("no sé si X o Y", "¿conviene X o Y?", "debatan si…") →
   `debate`; preparar un cambio/feature o mapear terreno → `explore`. (`counter-plan` no se
   invoca directo: presupone una spec aprobada.)
2. **Armar el `context_package`** desde el prompt (+ tracker si hay clave y MCP disponible; en
   `investigate`, + evidencia de reproducción que el conductor haya capturado — el explorador es
   headless y no abre URLs).
3. **Correr los pasos de arriba** y, a diferencia del modo embebido, **ejecutar la síntesis
   completa** (ver "La síntesis"): el conductor escribe su propio mapa, lee el del revisor,
   compara y **presenta la conclusión al usuario** — no un solo mapa, y redactada según el
   paso 5 de "La síntesis": los hallazgos, sin la mecánica.
4. **En `investigate`, tras presentar**, el conductor **ofrece** el handoff a la verificación:
   "¿verifico la hipótesis líder con `superpowers:systematic-debugging`?". Es una invocación de
   otra skill, opcional y a cargo del conductor en su rol normal — co-explore no verifica ni
   arregla (ver "Alcance de `investigate`").

## El loop de debate (modo `debate`)

A diferencia de los otros modos (una sola pasada), `debate` itera. El conductor participa como
una voz y la otra familia es la otra; el conductor además sintetiza (el usuario es el árbitro).

1. **R0 — posturas independientes.** El conductor escribe su propia postura sobre la decisión
   (opciones, análisis, hacia dónde se inclina y por qué) **antes** de ver nada de la otra
   familia. En paralelo despacha al revisor con el **mismo** paquete de decisión (sin la postura
   del conductor; prompt en `reference.md` → "Prompt de debate — ronda 0") para que forme la suya
   a ciegas. Regla 2 (independencia) aplica acá.
2. **R1..N — crítica cruzada.** Cada ronda cruza las posturas: se le pasa al revisor la postura
   del conductor para que la critique y actualice la suya (prompt en `reference.md` → "Prompt de
   debate — cruce"), y el conductor lee la del revisor, la critica y actualiza la propia.
   Registrar el **delta** de cada ronda (qué concedió, qué sostuvo cada uno) en el scratch.
3. **Convergencia + anti-desperdicio.** Default **3 rondas** de cruce; tope duro `max_rounds`
   (default 3). Si una ronda no mueve nada (ninguna familia concede ni refina su postura),
   **converger temprano** y decirlo — no quemar rondas. Cada ronda tiene deadline duro
   (regla 5): al vencer, cortar y sintetizar con lo que haya.
4. **Síntesis** (ver "La síntesis del debate").

## La síntesis del debate

El conductor cierra con una síntesis que **no elige ganador** — presenta las posturas para que
el usuario decida (ethos de árbitro humano, regla 3 de `cross-review`). La escribe en
`co-explore/debate.md` (plantilla en `reference.md` → "Plantilla de `debate.md`") y la presenta:

- **Postura final de cada familia**, atribuida por familia (🟠 Claude / 🔵 Codex) y **sin
  fusionar** en una sola voz. La atribución vale acá porque `debate.md` y la síntesis presentada
  son **locales y solo las lee el usuario** (ver "Publicado vs local"); nombrar a las familias es
  parte del valor del debate.
- **Dónde convergieron** y **qué queda en disputa**.
- **Los trade-offs afilados**: qué compra y qué cuesta cada opción, según salió del cruce.
- **No elige ganador**: la decisión es del usuario.

### Publicado vs local

La regla de co-explore "los entregables hablan del objeto, no del método" protege lo que se
**publica** donde lo leen otras personas (spec en Jira vía `publish-spec`, descripciones o
comentarios de PR en Bitbucket, cualquier superficie compartida). **No** aplica a archivos
**locales que solo lee el usuario**: `debate.md` y la síntesis presentada **sí** nombran a las
familias. El guardrail que se mantiene: lo que el debate haga aterrizar en `spec.md`
(`## Clarifications`) o `plan.md` (un trade-off) queda **limpio de método/familias**, porque eso
sí fluye a superficies publicadas. La skill llamadora (sdd-flow) escribe esos artefactos de forma
autónoma, con la decisión ya tomada, sin citar el debate.

## Salida

**Salida a la llamadora:** estado `READY` | `UNAVAILABLE` · ruta del informe
(`findings-<familia>.md` en `explore`, `counter-plan-<familia>.md` en `counter-plan`,
`investigate-<familia>.md` en `investigate`, `debate.md` en `debate`; si hay) · resumen de 3-5 líneas (hallazgos top +
enfoque sugerido, o en `investigate` hipótesis líder) · ruta de `session.json` si existe.

## La síntesis (guía para la skill llamadora)

La síntesis la ejecuta **el conductor** en todos los casos: los callers SDD (`sdd-flow`,
`sdd-orchestrator`) en modo embebido, y el propio conductor en modo directo (incluido
`investigate`). La guía vive acá una sola vez para que nadie la duplique:

1. Escribir el propio `findings-<familia>.md` del conductor **antes** de leer el del revisor
   (regla 2 — independencia hasta el final).
2. Comparar los dos informes sección por sección.
3. Producir `synthesis.md` (plantilla en `reference.md` → "Plantilla de `synthesis.md`") con:
   - una tabla de **convergencias / divergencias**;
   - el **duelo de enfoques**: evaluar los dos "Enfoque sugerido" en méritos (reúso, riesgo,
     simplicidad, encaje con el repo), elegir uno o hibridar, y registrar el **porqué** —
     auditable, no implícito;
   - las **Incógnitas fusionadas** de ambos mapas: las que cambiarían el diseño alimentan
     `clarify` (obligatorio en complejos).
4. Las **divergencias no resueltas** se presentan en un checkpoint informativo de la llamadora
   antes de escribir la spec/plan (no es un gate SDD, y solo ocurre si hay divergencias sin
   resolver; si los mapas convergen, se sigue directo sin stop extra).
5. **Los entregables hablan del objeto, no del método.** La conclusión presentada al usuario
   en modo directo y los artefactos que la llamadora escriba después (spec/plan/reparto) se
   redactan en términos de los hallazgos —mapa, riesgos, enfoque, hipótesis, plan de
   verificación— **sin mencionar la mecánica de co-exploración**: ni "conductor/revisor", ni
   nombres de modelos, ni "dos mapas"/"duelo", ni rutas de `co-explore/`. Esa trazabilidad ya
   vive en `synthesis.md` y los informes del directorio de trabajo. En el entregable, las
   divergencias no resueltas se presentan como **posiciones alternativas con su evidencia**,
   sin atribuirlas a quién las produjo. (El checkpoint conversacional del paso 4 es proceso,
   no entregable: ahí sí se puede nombrar fuentes.)

**En `investigate`** la síntesis es *bug-shaped*: en vez del "duelo de enfoques" se hace un
**duelo de hipótesis de causa raíz** (evaluar las candidatas en méritos: evidencia, encaje con
el repro; elegir la líder con rationale auditable) y el cierre es **hipótesis líder + plan de
verificación**, no una spec. Si los dos mapas divergen en la causa raíz y no se resuelve, se
presentan **ambas posiciones** al usuario como hipótesis alternativas con su evidencia, sin
atribuirlas a conductor/revisor (paso 5; mismo principio: no forzar consenso). Plantilla en
`reference.md` → "Plantilla de síntesis — `investigate`".

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
  con el sanitizer y verifica). Mecánica del worktree en `reference.md` → "Capacidades y
  worktree (investigate)".
- **Handoff:** verificar/arreglar de verdad es el paso siguiente y es de **otra skill**
  (`superpowers:systematic-debugging`), que el conductor ofrece en su rol normal. Las hipótesis
  rankeadas + plan de verificación son su input directo. Editar/proponer parches en paralelo
  (una "carrera de fixes cross-model") sería otra skill distinta — **no** está en co-explore.

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
    mode: auto      # off | on | auto  — cuándo se OFRECE el debate (nunca corre sin confirmación)
    max_rounds: 3   # tope de rondas de cruce
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

Nunca bloquea el flujo SDD. Cuatro vías de falla, todas con el mismo final:

1. Skill no instalada → la llamadora la omite y sigue con la exploración del
   conductor.
2. Sin revisor de otra familia disponible → `UNAVAILABLE`; la llamadora sigue con la
   exploración del conductor. Distinguir según el preflight de capacidad: una **pared confirmada**
   (binario ausente, auth rechazada, versión incompatible) es **terminal para la corrida** —no
   reintentar en despachos siguientes de la misma tanda—; un **flake transitorio de lanzamiento**
   (el binario existe pero flaqueó el arranque) admite 2-3 reintentos con backoff corto antes de
   rendirse. (El deadline del punto 3, ya arrancado, es por-intento.)
3. Deadline vencido → se mata el proceso y se registra; la llamadora sigue con la exploración
   del conductor.
4. Informe no parseable → se degrada (texto libre como contexto, o descarte si es ruido) y se
   registra; la llamadora sigue con la exploración del conductor.

En `debate`, si la otra familia no está disponible (misma distinción pared confirmada vs flake del
punto 2), el debate no corre: el conductor presenta su **análisis de una sola voz** y avisa en una
línea que el debate no estuvo disponible. Nunca bloquea; en sdd-flow el flujo sigue al gate normal
de `clarify`/`plan`.

## Router de intención

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
  fallback)", "Latencia y deadlines", "Archivos de trabajo (scratch)", "Prompt de debate" (ronda
  0 + cruce), "Plantilla de `debate.md`".
- `README.md` — qué es, cuándo usarla, requisitos e instalación.
