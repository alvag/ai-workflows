# Modo `debate` en co-explore — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar un modo `debate` a la skill `co-explore` (soporte a decisiones cross-model) y engancharlo en `sdd-flow` (`clarify`/`plan`) con config `co_explore.debate`.

**Architecture:** `debate` es un modo nuevo de `co-explore` (no una skill nueva). El conductor forma su postura y despacha a la otra familia para que forme la suya a ciegas (R0 independiente); cruzan posturas por hasta 3 rondas; el conductor produce una síntesis neutral atribuida por familia (local, solo la lee el usuario) sin elegir ganador. `sdd-flow` lo ofrece (nunca lo corre solo) en decisiones contestables de `clarify`/`plan` según `co_explore.debate.mode` (off/on/auto).

**Tech Stack:** Skills de Claude Code/Codex en Markdown (SKILL.md + reference.md + README.md). No hay código ejecutable ni tests unitarios: la "verificación" de cada task es un chequeo de consistencia (cross-references resuelven, sin contradicciones con reglas existentes, sin placeholders).

## Global Constraints

- **Español neutro, sin voseo** en toda la prosa nueva (ej.: "lee", no "leé"; "vuelve a correr", no "re-corré"). Copiado de la preferencia del usuario.
- **Los artefactos locales solo-usuario pueden nombrar familias** (`debate.md`, síntesis mostrada); **lo que aterriza en `spec.md`/`plan.md` queda limpio de método/familias** (fluye a Jira/PR). Ver spec → "Publicado vs local".
- **`debate` no auto-elige**: la síntesis presenta posturas para que el usuario decida (ethos regla 3 de cross-review).
- **Siempre ofrece, nunca corre sin un "sí"** cuando lo dispara sdd-flow.
- **Default 3 rondas de cruce**, tope duro `max_rounds` (default 3), con convergencia temprana anti-desperdicio.
- **Dos familias, no personas**: las voces son Claude y GPT/Codex.
- **Portabilidad POSIX/PowerShell** en cualquier comando nuevo (patrón ya usado en co-explore/reference.md).
- Spec de referencia: `docs/superpowers/specs/2026-07-17-co-explore-debate-mode-design.md`.

---

## Estructura de archivos

- `skills/co-explore/SKILL.md` — define el modo `debate`: descripción, lista de modos, contrato de invocación, loop, síntesis, ajuste de reglas 2 y 5, router, degradación, config. (Task 1)
- `skills/co-explore/reference.md` — plantillas: "Prompt de debate" (R0 + cruce), "Plantilla de `debate.md`", deadlines y scratch. (Task 2)
- `skills/co-explore/README.md` — mención breve del modo nuevo. (Task 3)
- `skills/sdd-flow/SKILL.md` — config `co_explore.debate`, eco del checkpoint, disparadores en `clarify` y `plan`, wizard de `init`, router. (Task 4)
- `skills/sdd-flow/reference.md` — `co_explore.debate` en el esquema de `.specify/config.yml`. (Task 5)

Orden: Task 1 y 2 definen el modo (co-explore autónomo y consistente). Task 3 es cosmético. Task 4 y 5 enganchan sdd-flow (dependen de que el modo exista en co-explore).

---

## Task 1: co-explore SKILL.md — definir el modo `debate`

**Files:**
- Modify: `skills/co-explore/SKILL.md`

**Interfaces:**
- Produces: el modo `debate` con su contrato (`mode: debate`, `context_package` = decisión + opciones + contexto), el nombre de artefacto `debate.md`, y los punteros a `reference.md` → "Prompt de debate" y "Plantilla de `debate.md`" (que crea la Task 2).

- [ ] **Step 1: Frontmatter — sumar `debate` a la descripción**

En el `description` del frontmatter (líneas 3-18), cambiar "Tres modos" por "Cuatro modos" y agregar, tras la cláusula de `investigate`:

```
"debate" (ayudar a decidir entre opciones abiertas cuando no estás seguro:
las dos familias forman posturas independientes, se critican en rondas y el
conductor sintetiza sin elegir).
```

Y en los ejemplos de invocación directa sumar: `"/co-explore debate <decisión>"`, `"no sé si X o Y, que Codex y tú lo debatan"`.

- [ ] **Step 2: Intro — sumar `debate` a la lista de modos**

Tras el bullet de `investigate` (línea 33-37), agregar:

```markdown
- **`debate`** (standalone + lo invoca SDD en decisiones): ayudar a **decidir** entre
  opciones abiertas cuando el usuario no está seguro. Las dos familias forman posturas
  independientes, se critican en varias rondas y el conductor entrega una **síntesis neutral
  atribuida** — no elige ganador, afila la decisión. Es el único modo con **loop de rondas**
  (los otros tres son una sola pasada).
```

- [ ] **Step 3: Intro — marcar la frontera mapa / veredicto / decisión**

Al final del párrafo de frontera (líneas 51-55, que hoy contrasta "mapa vs veredicto" con cross-review draft), agregar una oración:

```markdown
Y hay un tercer eje: si el terreno está abierto pero ya tienes **opciones concretas** entre las
que no sabes cuál elegir, eso no es mapa (`explore`) ni veredicto sobre un enfoque ya elegido
(`cross-review` draft) — es una **decisión** entre alternativas → `debate`.
```

- [ ] **Step 4: Regla 2 (independencia) — acotar a R0 en debate**

Al final de la regla 2 (línea 78-82), agregar:

```markdown
   En `debate` la independencia rige la **ronda 0** (ambas familias forman su postura a ciegas,
   sin verse); de la ronda 1 en adelante el **cruce** de posturas es deliberado (cada una critica
   la del otro) — es la excepción diseñada de este modo, no una violación de la independencia.
```

- [ ] **Step 5: Regla 5 (loop acotado) — carve-out para debate**

Reemplazar el texto de la regla 5 (líneas 91-93) por:

```markdown
5. **Loop acotado, deadline duro.** En `explore`/`counter-plan`/`investigate`, **una sola pasada
   por modo — sin rondas**. La excepción es `debate`: es el único modo con **loop acotado** de
   rondas de cruce (default 3, tope duro `max_rounds`), como `cross-review`; igual tiene deadline
   duro **por ronda** → al vencer se mata el proceso del explorador y se devuelve `UNAVAILABLE`
   con lo que haya. Nunca se espera de forma indefinida.
```

- [ ] **Step 6: Contrato de invocación — sumar `debate` al `mode` y su `context_package`**

En el bullet `mode` (líneas 127-128), agregar `| debate (decisión abierta entre opciones)`.
En el bullet `context_package` (líneas 129-138), agregar un párrafo:

```markdown
  En `debate`: la **decisión a resolver** + las **opciones en juego** (si el usuario las dio;
  si no, el conductor las deriva y las declara explícitas) + el contexto de código/artefactos
  relevante. Cuando lo invoca sdd-flow: la ambigüedad de `clarify` o el trade-off contestable del
  `plan`, con `spec.md`/`plan.md` como contexto.
```

- [ ] **Step 7: Contrato de invocación — `execution` y `deadline` en debate**

En el bullet `execution` (líneas 142-144), agregar: `En `debate` el loop es secuencial (rondas de cruce), como `cross-review`: se espera cada ronda con tope duro.`
En el bullet `deadline` (líneas 145-146), agregar: `en `debate`, deadline **por ronda** (default 300s/ronda) más el tope `max_rounds`.`

- [ ] **Step 8: Nueva sección "El loop de debate" (tras "Pasos de ejecución", antes de "Salida")**

Insertar antes de `## Salida` (línea 183):

```markdown
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
```

- [ ] **Step 9: Nueva sección "La síntesis del debate" (tras "El loop de debate")**

Insertar a continuación:

```markdown
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
```

- [ ] **Step 10: Modo directo — sumar la inferencia de `debate`**

En "Modo directo" paso 1 (líneas 168-170), reemplazar por:

```markdown
1. **Inferir el modo desde la intención.** Un bug, error o "por qué falla X" → `investigate`;
   una decisión abierta entre opciones ("no sé si X o Y", "¿conviene X o Y?", "debatan si…") →
   `debate`; preparar un cambio/feature o mapear terreno → `explore`. (`counter-plan` no se
   invoca directo: presupone una spec aprobada.)
```

- [ ] **Step 11: Router — sumar filas de `debate`**

Tras la fila de `investigate` en el router (línea 295), agregar:

```markdown
| "/co-explore debate `<decisión>`", "no sé si X o Y, que lo debatan", "somete esto a debate" | modo directo: `mode: debate`, corre el loop de rondas + síntesis neutral atribuida, y presenta las posturas para que decidas |
| "con debate" / "sin debate" (en un flujo SDD) | override `on`/`off` del ofrecimiento de debate para la corrida — lo registra la llamadora |
```

- [ ] **Step 12: Degradación — sumar el caso `debate`**

Al final de la sección "Degradación" (tras el punto 4, línea 287), agregar:

```markdown
En `debate`, si la otra familia no está disponible (misma distinción pared confirmada vs flake del
punto 2), el debate no corre: el conductor presenta su **análisis de una sola voz** y avisa en una
línea que el debate no estuvo disponible. Nunca bloquea; en sdd-flow el flujo sigue al gate normal
de `clarify`/`plan`.
```

- [ ] **Step 13: Config — sumar el sub-bloque `debate`**

En el bloque YAML de "Configuración" (líneas 256-260), reemplazar por:

```yaml
co_explore:
  mode: auto        # auto (por complejidad: complejo on, normal opt-in, trivial nunca) | "on" | "off"
  deadline: 600     # segundos (explore; counter-plan usa 300 salvo override)
  debate:           # modo debate — soporte a decisiones (independiente de mode; lo ofrece sdd-flow)
    mode: auto      # off | on | auto  — cuándo se OFRECE el debate (nunca corre sin confirmación)
    max_rounds: 3   # tope de rondas de cruce
```

Y tras el párrafo de precedencia (línea 262-266), agregar:

```markdown
El sub-bloque `debate` es **independiente** de `co_explore.mode` (se puede querer debate sin haber
corrido la exploración pre-spec). `debate.mode`: `off` nunca ofrece; `auto` ofrece solo en
decisiones complejas / high-stakes (auth, pagos, migraciones de datos o schema, concurrencia,
cambios difíciles de revertir) o cuando el conductor está genuinamente inseguro; `on` ofrece en
cualquier decisión contestable de `clarify`/`plan`. En **todos** los casos **ofrece y espera un
"sí"** — nunca corre el debate solo. `investigate` sigue sin leer config; `debate` standalone
tampoco.
```

- [ ] **Step 14: Referencias internas — sumar los punteros de debate**

En "Referencias internas" (líneas 303-306), sumar a la lista de secciones de `reference.md`:
`"Prompt de debate" (ronda 0 + cruce)`, `"Plantilla de `debate.md`"`.

- [ ] **Step 15: Verificación de consistencia**

Leer `skills/co-explore/SKILL.md` completa de corrido. Confirmar:
- No quedan contradicciones: regla 5 ya contempla `debate` con rondas; regla 2 acota independencia a R0.
- Todos los punteros a `reference.md` que agregaste ("Prompt de debate", "Plantilla de `debate.md`") existen o quedan pendientes para Task 2 (anotarlo).
- `mode: debate` aparece en: frontmatter, intro, contrato de invocación, modo directo, router, config.
- Correr: `grep -n "debate" skills/co-explore/SKILL.md` y revisar que cada aparición sea coherente.
- Escaneo anti-voseo: `grep -nE "(corré|leé|mirá|poné|hacé|fijate|tenés|querés|debés|elegí|ordená)" skills/co-explore/SKILL.md` → sin matches en las líneas nuevas.

- [ ] **Step 16: Commit**

```bash
git add skills/co-explore/SKILL.md
git commit -m "feat(co-explore): agrega el modo debate (soporte a decisiones cross-model)"
```

---

## Task 2: co-explore reference.md — plantillas del debate

**Files:**
- Modify: `skills/co-explore/reference.md`

**Interfaces:**
- Consumes: los punteros que Task 1 dejó ("Prompt de debate", "Plantilla de `debate.md`").
- Produces: las plantillas concretas que el loop de debate usa.

- [ ] **Step 1: Sección "Prompt de debate" (tras "Modo `investigate`", antes de "Formato del informe", ~línea 152)**

Insertar:

````markdown
### Modo `debate` (decisión abierta)

Dos prompts: uno para la **ronda 0** (postura independiente) y otro para cada **ronda de cruce**.
Ambos read-only. Estructura XML compacta (operador, no colaborador), escritos a archivo con Write
(nunca inline).

**Prompt de debate — ronda 0 (postura independiente):**

```xml
<task>
Eres un asesor técnico independiente. Se debe tomar una DECISIÓN entre opciones y el usuario no
está seguro. Forma tu propia postura ANTES de ver la de nadie más. Es SOLO LECTURA: puedes leer el
código en {working_dir} para fundamentar, pero no edites ni ejecutes nada.
</task>

<decision>
{la decisión a resolver + las opciones en juego, del paquete de contexto}
</decision>

<context>
{contexto relevante: spec/plan si los hay, AC, contratos, complejidad}
</context>

<output_contract>
Devuelve exactamente:
POSTURA: <hacia qué opción te inclinas, o "sin preferencia" con el porqué>
POR QUÉ: <2-5 razones fundadas, ancladas al código/contexto cuando se pueda>
TRADE-OFFS: <qué compra y qué cuesta cada opción>
RIESGOS/INCÓGNITAS: <lo que no pudiste verificar o lo que cambiaría tu postura>
</output_contract>
```

**Prompt de debate — cruce (rondas 1..N):**

```xml
<task>
Continúa el debate. Abajo está la postura ACTUAL de la otra parte sobre la misma decisión.
Critícala de forma adversarial y luego da tu postura ACTUALIZADA. SOLO LECTURA.
</task>

<other_position>
{la postura actual del conductor, del delta de la ronda anterior}
</other_position>

<output_contract>
CRÍTICA: <qué falla, qué no consideró, qué riesgo ignora la otra postura>
POSTURA ACTUALIZADA: <tu postura tras la crítica: qué mantienes, qué concedes>
CONVERGENCIA: <en qué estás de acuerdo con la otra parte>
</output_contract>
```
````

- [ ] **Step 2: Sección "Plantilla de `debate.md`" (tras "Plantilla de síntesis — `investigate`", ~línea 297)**

Insertar:

````markdown
## Plantilla de `debate.md`

Local/untracked, en `co-explore/debate.md`. Nombra a las familias (es local, solo lo lee el
usuario). Los deltas crudos por ronda quedan en el scratch.

```markdown
# Debate co-explore — <decisión> (<ISO-8601>)

## Opciones en juego
- <Opción X>
- <Opción Y>

## Posturas finales
### 🟠 Claude
<postura final del conductor: hacia qué opción, por qué, qué concedió en el cruce>
### 🔵 Codex
<postura final del revisor: ídem>
(Ajustar los nombres a las familias reales: si conduce Codex, el conductor es 🔵 Codex y el
revisor 🟠 Claude.)

## Convergencias
<en qué coincidieron las dos posturas>

## En disputa (sin resolver)
<dónde siguen en desacuerdo, con la evidencia de cada lado>

## Trade-offs afilados
| Opción | Compra | Cuesta |
|---|---|---|
| X | … | … |
| Y | … | … |

## Rondas
Convergió en <n> rondas (de max_rounds <m>). <nota si convergió temprano por falta de movimiento>.

> El debate NO elige: la decisión es del usuario. Lo que se registre luego en spec.md/plan.md va
> limpio de método/familias (ver SKILL.md → "Publicado vs local").
```
````

- [ ] **Step 3: "Latencia y deadlines" — sumar `debate`**

En la sección "Latencia y deadlines" (~línea 426), agregar una línea:
`En `debate`: deadline **por ronda** (default 300s) + tope `max_rounds` (default 3). Al vencer una ronda, cortar y sintetizar con lo que haya (regla 5).`

- [ ] **Step 4: "Archivos de trabajo (scratch)" — sumar los de debate**

En la sección "Archivos de trabajo (scratch)" (~línea 473), agregar:
`En `debate`: `co-explore/debate.md` (la síntesis, hermana de `synthesis.md`) + los deltas crudos por ronda en `co-explore/scratch/debate-r<n>.out`.`

- [ ] **Step 5: Verificación de consistencia**

- `grep -n "debate" skills/co-explore/reference.md` → las 4 inserciones presentes y coherentes.
- Confirmar que los nombres de sección coinciden EXACTO con los punteros de SKILL.md ("Prompt de debate", "Plantilla de `debate.md`").
- Escaneo anti-voseo en las líneas nuevas.

- [ ] **Step 6: Commit**

```bash
git add skills/co-explore/reference.md
git commit -m "feat(co-explore): plantillas del modo debate (prompts ronda 0/cruce + debate.md)"
```

---

## Task 3: co-explore README.md — mención del modo

**Files:**
- Modify: `skills/co-explore/README.md`

- [ ] **Step 1: Leer el README y ubicar la enumeración de modos**

Run: `grep -nE "explore|counter-plan|investigate|modo" skills/co-explore/README.md`
Identificar dónde lista los tres modos actuales.

- [ ] **Step 2: Sumar `debate` a esa enumeración**

Agregar, en el mismo estilo y lugar que los otros tres, una línea equivalente a:
`- **debate** — ayuda a decidir entre opciones abiertas cuando no estás seguro: dos familias forman posturas, se critican en rondas y el conductor sintetiza sin elegir.`
(Ajustar la redacción exacta al formato que use el README.)

- [ ] **Step 3: Verificación + commit**

Confirmar que el README ahora menciona los cuatro modos.

```bash
git add skills/co-explore/README.md
git commit -m "docs(co-explore): menciona el modo debate en el README"
```

---

## Task 4: sdd-flow SKILL.md — config + disparadores en clarify/plan

**Files:**
- Modify: `skills/sdd-flow/SKILL.md`

**Interfaces:**
- Consumes: el modo `debate` de co-explore (Task 1) y su config `co_explore.debate`.

- [ ] **Step 1: Esquema de config — sumar `co_explore.debate`**

En el bloque YAML del esquema de `config.yml` (línea 114), reemplazar la línea de `co_explore` por:

```yaml
co_explore: {mode: auto, deadline: 600, debate: {mode: auto, max_rounds: 3}}  # exploración paralela + modo debate (decisiones); ver "Co-exploración cross-model"
```

- [ ] **Step 2: Checkpoint de inicio — sumar `co_explore.debate` al eco**

En el "Checkpoint de inicio" (líneas 97-98) y en la red-flag "Arranco el flujo sin leer el config" (línea 86), sumar `co_explore.debate` a la lista de valores que se ecoan. Ejemplo de eco a agregar en la oración de ejemplo:
`… co_explore.debate auto → ofrezco debate en decisiones complejas de clarify/plan …`

- [ ] **Step 3: Nueva subsección en "Co-exploración cross-model" — el disparador de debate**

Al final de la sección "Co-exploración cross-model" (antes de "Compatibilidad con Plan Mode", línea 267), agregar:

```markdown
### Debate en decisiones (`clarify` y `plan`)

Además de `explore`/`counter-plan`, `co-explore` tiene el modo **`debate`** para **ayudarte a
decidir** cuando una decisión abierta te deja inseguro. Se gobierna con `co_explore.debate`
(independiente de `co_explore.mode`) y **siempre se ofrece, nunca corre sin tu "sí"**.

- **En `clarify`:** cuando una pregunta es una decisión abierta real (no algo que el código
  responde) y `co_explore.debate.mode` es `on`/`auto`, ofrecer: *"esta decisión (X vs Y) es
  contestable — ¿la someto a debate cross-model antes de que decidas?"*. Si aceptas → invocar
  `co-explore` con `mode: debate` (la pregunta + las opciones + `spec.md` como contexto) → presentar
  la síntesis → decides → registrar la respuesta en `## Clarifications`. Si no → clarify normal.
- **En `plan`:** cuando hay un trade-off contestable (los que ya se nombran en "Decisiones y
  trade-offs" del plan) y el modo lo habilita, ofrecer someter *ese* trade-off a debate antes del
  gate del plan; la decisión resultante se refleja en el plan.
- **Umbral del ofrecimiento:** `off` nunca; `auto` solo en decisiones complejas / high-stakes
  (auth, pagos, migraciones de datos o schema, concurrencia, cambios difíciles de revertir) o si
  estás genuinamente inseguro; `on` en cualquier decisión contestable.
- **Lo que aterriza en el artefacto va limpio.** La respuesta de `clarify` en `spec.md` y el
  trade-off resuelto en `plan.md` se escriben **sin** mencionar el debate, las familias ni el
  método (fluyen a Jira/PR). La atribución por familia vive solo en `co-explore/debate.md`, local
  (ver `co-explore` → "Publicado vs local").
- **Degradación:** sin la otra familia, no hay debate: seguir al gate normal con un aviso de una
  línea (misma filosofía que el resto de co-exploración).
```

- [ ] **Step 4: Router de intención — sumar el override de debate**

Tras la fila "con co-exploración / sin co-exploración" (línea 293), agregar:

```markdown
| "con debate", "somételo a debate" / "sin debate" | registra el **override de debate** de la corrida (on/off; ver "Debate en decisiones") |
```

- [ ] **Step 5: init wizard — sumar `debate` a la Pantalla 2**

En el paso `init`, Pantalla 2 del wizard (línea 322), sumar `debate` (off · auto · on) a la lista de decisiones de esa pantalla, junto a `cross_review`/`domain_context`/`final_diff_review`/`jira_approval`. Al escribir el config (paso 6, línea 326), incluir `co_explore.debate.mode` entre los valores emitidos con comillas (`"on"`/`"off"`; `auto` sin comillas es válido).

- [ ] **Step 6: Verificación de consistencia**

- `grep -n "debate" skills/sdd-flow/SKILL.md` → esquema, eco, sección nueva, router, wizard.
- Confirmar que la invocación descrita (`mode: debate` + contexto) coincide con el contrato de Task 1.
- Confirmar el guardrail "artefacto limpio" en la subsección nueva.
- Escaneo anti-voseo en líneas nuevas.

- [ ] **Step 7: Commit**

```bash
git add skills/sdd-flow/SKILL.md
git commit -m "feat(sdd-flow): ofrece debate cross-model en clarify/plan (config co_explore.debate)"
```

---

## Task 5: sdd-flow reference.md — esquema de config

**Files:**
- Modify: `skills/sdd-flow/reference.md`

- [ ] **Step 1: Ubicar el esquema de `.specify/config.yml`**

Run: `grep -n "co_explore\|Esquema de .specify/config" skills/sdd-flow/reference.md`

- [ ] **Step 2: Sumar `co_explore.debate` al esquema**

Donde el reference documente el bloque `co_explore`, sumar el sub-bloque `debate: {mode, max_rounds}` con el mismo comentario que en SKILL.md (independiente de `mode`; off/on/auto = umbral del ofrecimiento; siempre ofrece, nunca corre solo). Si el reference no tiene una entrada dedicada de `co_explore`, agregar una línea consistente con cómo documenta las otras claves.

- [ ] **Step 3: Verificación + commit**

- `grep -n "debate" skills/sdd-flow/reference.md` → presente y coherente con SKILL.md.

```bash
git add skills/sdd-flow/reference.md
git commit -m "docs(sdd-flow): co_explore.debate en el esquema de config"
```

---

## Self-review del plan (cobertura de la spec)

- **Modo `debate` en co-explore** → Task 1 (surface) + Task 2 (plantillas). ✓
- **Loop R0/R1..N + convergencia + 3 rondas** → Task 1 Step 8. ✓
- **Síntesis neutral atribuida + no auto-elige** → Task 1 Step 9. ✓
- **Publicado vs local (atribución local, artefacto limpio)** → Task 1 Step 9 + Task 4 Step 3. ✓
- **Regla 5 sin rondas → carve-out debate** → Task 1 Step 5. ✓
- **Regla 2 independencia R0** → Task 1 Step 4. ✓
- **Config `co_explore.debate` (off/on/auto, max_rounds)** → Task 1 Step 13 + Task 4 Step 1 + Task 5. ✓
- **Disparadores clarify/plan + siempre ofrece** → Task 4 Step 3. ✓
- **Standalone + router + inferencia de modo** → Task 1 Steps 10-11. ✓
- **Degradación blanda** → Task 1 Step 12 + Task 4 Step 3. ✓
- **Eco del checkpoint + wizard** → Task 4 Steps 2, 5. ✓
- **Fuera de v1** (Model 2, on auto-run, sdd-orchestrator): no se implementa, correcto. ✓
