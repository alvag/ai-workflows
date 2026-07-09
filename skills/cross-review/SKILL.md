---
name: cross-review
description: >-
  Usar cuando el usuario pida una "segunda opinión", una "revisión independiente
  o adversarial", un "cross-review", una "mirada externa", o "que otro modelo o
  Codex revise/critique/desafíe" un artefacto de Spec-Driven Development (spec,
  plan, tasks, master-spec, reparto) antes de implementar o de un gate. También
  la invocan sdd-flow y sdd-orchestrator en sus gates (modo embebido). También
  cubre el caso "tengo una idea/plan claro pero ningún artefacto": modo draft —
  redacta un plan ligero desde la conversación + el código y lo somete al mismo
  loop ("stress-test de esta idea", "arma un plan y que Codex lo critique"). NO
  es code review: no usarla sobre diffs, PRs ni código fuente — solo documentos
  de diseño. No invocarla espontáneamente: solo ante un pedido explícito del
  usuario o invocada por una skill SDD. Invocación directa:
  "/cross-review <ruta-del-artefacto>", o sin ruta para el modo draft.
---

# cross-review — segunda opinión cross-model para artefactos SDD

Helper que toma un artefacto SDD y le pide una **crítica adversarial a un modelo de otra
familia que el autor** (Codex cuando conduce Claude; Claude cuando conduce Codex) antes de que
un humano lo apruebe. El valor es romper la correlación de errores: el mismo modelo que escribe
la spec/plan/tasks es, hoy, el único que los revisa antes del gate. Un revisor de otra familia
caza huecos que ese modelo no ve — un AC faltante, un enfoque frágil, un riesgo no considerado,
un contrato inconsistente.

**No reemplaza el gate humano: lo alimenta.** La revisión corre *antes* del STOP de aprobación
y su crítica se presenta *junto* al artefacto, para que la persona decida con esa entrada ya
incorporada. Y **nunca bloquea el flujo**: si no hay revisor disponible o algo falla, se degrada
limpio al gate humano de siempre.

```
artefacto escrito ──► [cross-review] ──► artefacto (quizá revisado) + resumen de crítica ──► GATE humano
                         loop acotado, read-only,                          (lo presenta la skill
                         Claude árbitro, log auditable                      llamadora; STOP normal)
```

## Reglas no negociables

1. **Read-only.** El revisor nunca escribe en el repo. Se invoca en modo read-only (sin `--write`).
   Quien edita el artefacto —si hay algo que aplicar— es Claude, no el revisor.
2. **Loop acotado.** Máximo `max_rounds` rondas (default 3). Termina por veredicto `APPROVED` o
   por agotar las rondas. Nunca un loop abierto.
3. **Claude/el usuario son el árbitro final — sin sycophancy.** Los findings del revisor son
   *insumo*, no órdenes. Antes de aplicar cualquiera, evaluarlo con la disciplina de
   `superpowers:receiving-code-review`: verificar técnicamente, rebatir lo incorrecto o
   inaplicable, y **registrar el porqué** de cada decisión (aplicado o rechazado). Aceptar a
   ciegas es tan dañino como ignorar a ciegas.
4. **Foco, no estilo.** La revisión apunta a correctitud del enfoque, AC faltantes o
   contradictorios, riesgos, testeabilidad de los AC y gaps de contrato (en multi-repo). **No**
   a wording, formato ni preferencias cosméticas — eso es "review theater" y mete ruido.
5. **Auditable.** Cada corrida deja un `review-log.md` junto al artefacto: rondas, findings,
   veredictos, y qué decidió Claude con su rationale. La revisión tiene que poder reconstruirse. Los
   archivos de trabajo del revisor (prompts, veredictos crudos, deltas, session, stderr) van a un
   subdirectorio `cross-review/` junto al artefacto, no sueltos en la raíz del flujo (ver
   `reference.md` → "Archivos de trabajo (scratch)").
6. **Opcional y degradable.** Es una **capacidad**, no un requisito. Si falta el revisor o falla,
   avisar en una línea y devolver el control al gate humano. El flujo SDD sigue intacto (ver
   "Degradación").
7. **Descubrir por capacidad, no por nombre — y nunca de la familia del autor.** El revisor se
   busca por capacidad (un segundo modelo que pueda criticar texto en read-only), no por un
   nombre de tool fijo. Regla dura: **el revisor nunca es de la misma familia de modelos que el
   autor del artefacto**; misma familia = errores correlacionados, justo lo que esta revisión
   existe para romper. Hay **dos familias**: Claude y GPT/Codex. El autor es la familia del
   **agente que conduce la skill** — sin importar la superficie donde corre (CLI, app de
   escritorio, IDE, web) — y el revisor es siempre el de la otra. Detalle en `reference.md` →
   "Descubrir el revisor".

## Red flags — detente y reconsidera

Las reglas de arriba dicen *qué* hacer; esta sección frena los atajos al procesar la crítica. Ley fundamental:

> **LOS FINDINGS SON INSUMO, NO ÓRDENES — VERIFICAR ANTES DE APLICAR.** Aceptar a ciegas es tan dañino como ignorar a ciegas (regla 3).

Si reconoces alguno de estos pensamientos, detente y aplica la disciplina de `superpowers:receiving-code-review`.

| Racionalización | Realidad |
|---|---|
| "El revisor lo marcó, lo aplico" | Antes de aplicar: verificar técnicamente, rebatir lo incorrecto/inaplicable y **registrar el porqué** (regla 3). |
| "Tiene razón, le agradezco y edito" | Sin sycophancy. La respuesta correcta es reformular el requisito o directamente corregir — no validación performativa. |
| "Le respondo el delta y de paso pulo el wording que sugirió" | Foco, no estilo (regla 4): wording/formato es review theater. La revisión apunta a correctitud, AC, riesgos y contratos. |
| "No hay revisor disponible, espero / reintento en loop" | Degradación: avisar en una línea y ceder al gate humano. Loop acotado a `max_rounds`, con tope duro → `UNAVAILABLE` (reglas 2, 6). |

## Contrato de invocación (lo que pasa la skill llamadora)

Al invocarla, `sdd-flow`/`sdd-orchestrator` (o el usuario) proveen:

- **`artifact_type`** — `spec | plan | tasks | master-spec | reparto`. Define el foco de la
  revisión (ver `reference.md` → "Foco por tipo de artefacto").
- **`artifact_path`** — ruta del artefacto a revisar (p. ej. `.plans/ABC-123/plan.md`).
- **`context_paths`** — artefactos relacionados para grounding (p. ej. al revisar `tasks`, pasar
  también `spec` y `plan`; al revisar `reparto`, la `master-spec`). Opcional pero recomendado. Si
  el flujo corrió **co-exploración** (`co-explore`), la llamadora pasa acá los
  `co-explore/findings-*.md` (y `co-explore/counter-plan-*.md` al revisar `plan`): la crítica sale
  informada por la exploración previa del propio revisor.
- **`working_dir`** — directorio desde donde el revisor puede leer el código en read-only.
- **`complexity`** — `trivial | normal | complex` (de `sdd-flow`); modula profundidad/esfuerzo.
- **`execution`** — `auto | sync | background` (de la config `cross_review`); cómo se espera al
  revisor. `auto` (default) elige por la capacidad de timeout del conductor; `sync` fuerza llamada
  bloqueante; `background` fuerza poll acotado. En todos hay tope duro → `UNAVAILABLE` (ver
  `reference.md` → "Latencia y timeout").
- **`ac_context`** — los `AC-n` y contratos en juego, para que la crítica los referencie.
  Opcional: si la llamadora no lo pasa, derivarlos de `context_paths` (la spec/master-spec ya
  los contiene).

**Modo de uso:**
- *Embebido* (lo llama otra skill SDD): no hace STOP propio. Devuelve el artefacto (quizá
  revisado) + un resumen de la crítica para que la llamadora lo presente en su gate.
- *Directo* (lo llama el usuario con `/cross-review <ruta>`): infiere `artifact_type` por el
  nombre/encabezado del archivo, corre el loop y **presenta** el resultado al usuario.
- *Draft* (directo **sin ruta**, con una idea/plan claro en la conversación): el conductor
  redacta primero un plan ligero y lo somete al mismo loop — ver "Modo draft" abajo.

## Modo draft (directo, sin artefacto)

Para cuando hay una idea clara pero ningún artefacto que revisar — el punto de entrada portable,
fuera de todo flujo SDD (inspirado en `codex-review` de chaseai):

1. **Una sola pregunta si falta el objetivo.** Si la conversación no deja claro qué se quiere
   construir, preguntarlo (una vez). Si escribir el plan obliga a resolver ambigüedades de diseño
   más profundas, este modo no alcanza: ofrecer `sdd-flow` (con su `clarify`) en vez de un draft
   con huecos.
2. **Planificar de verdad.** Leer el código relevante del repo (no planear en el aire) y escribir
   el plan a `.cross-review/<slug>/plan.md` — dir local untracked, mismo criterio que el modo
   directo de `co-explore` — con la estructura: `## Objetivo`, `## Enfoque` (pasos concretos),
   `## Decisiones y trade-offs` (las apuestas contestables, nombradas — los blancos del revisor),
   `## Riesgos y preguntas abiertas`, `## Fuera de alcance`.
3. **Correr el loop normal** con `artifact_type: plan`, `artifact_path` ese archivo,
   `working_dir` el repo y `complexity` estimada (anunciarla). El `review-log.md` y el scratch
   `cross-review/` quedan junto al plan draft.
4. **Presentar** el plan convergido (o el deadlock con sus disputas, regla 2) y **ofrecer el
   handoff**: implementarlo el conductor, o —si la skill `cross-implement` y el CLI de la otra
   familia están disponibles— delegar la implementación cruzada con este plan como `work_order`
   (el conductor revisa el diff). El código se escribe solo tras ese sign-off del usuario.

El draft **no es** un `plan.md` de sdd-flow (sin header YAML, sin ciclo de status, sin rama): si
el usuario quiere el ciclo completo con gates y verify, el camino es `sdd-flow` — este modo es el
stress-test portable de una idea, no un flujo de desarrollo.

## Paso 0 — descubrir el revisor

Antes de nada, resolver si hay un segundo modelo disponible (algoritmo y opciones en
`reference.md` → "Descubrir el revisor"):

1. **Identificar la familia del autor.** Es la del agente que conduce la skill, sin importar la
   superficie donde corre (CLI, app de escritorio, IDE, web): un agente **Claude** → autor
   Claude; un agente **Codex** → autor GPT/Codex.
2. **Elegir el revisor de la OTRA familia** (regla 7 — el revisor nunca es de la familia del
   autor):
   - Autor **Claude** → revisor **Codex**: el subagente `codex:codex-rescue` si existe en el
     entorno; si no, el CLI `codex exec` en read-only.
   - Autor **GPT/Codex** → revisor **Claude**: el CLI `claude -p` restringido a tools de lectura.
3. Si `cross_review.reviewer` fuerza una vía (`claude` | `codex`), usarla directo; si la vía
   forzada coincide con la familia del autor, **avisar que se pierde el valor cross-model** y
   continuar. El override explícito manda.
4. Si **no hay revisor** de la otra familia disponible → no romper: devolver veredicto
   `UNAVAILABLE` con el aviso estándar y ceder al gate humano (ver "Degradación").
5. Si hay revisor → seguir con el loop.

> **Portabilidad.** Los comandos para descubrir e invocar al revisor tienen variante **POSIX**
> (macOS/Linux/Git Bash) y **PowerShell** (Windows). Elegir según el shell del entorno — detalle y
> bloques listos para ejecutar en `reference.md` → "Portabilidad entre shells (POSIX / PowerShell)".

## El loop de revisión

1. **Ronda 1.** Armar el prompt de revisión (plantilla XML en `reference.md` → "Prompt de
   revisión": `<task>`, `<artifact>`, `<context>`, `<grounding_rules>`,
   `<structured_output_contract>`, `<dig_deeper_nudge>`), incluyendo el **contenido** del
   artefacto inline (grounding) y el foco según `artifact_type`. Invocar al revisor en
   **read-only**. Guardar referencia del thread para poder reanudarlo en rondas siguientes.
2. **Parsear la respuesta** al formato estructurado (`reference.md` → "Formato de salida"):
   lista de `findings` `[severidad, qué, por qué, cambio sugerido, AC/sección]` + un veredicto
   `APPROVED | REVISE`.
3. **Si `APPROVED`** → cortar el loop. Ir a "Salida".
4. **Si `REVISE`** → para cada finding, **decidir como árbitro** (regla 3, vía
   `receiving-code-review`): aplicar / rechazar / escalar. Aplicar los aceptados editando el
   artefacto (Claude edita, no el revisor). Registrar todo en `review-log.md` con el rationale,
   incluidos los rechazos.
5. **Siguiente ronda** reanudando el mismo thread del revisor (resume; mandar solo el delta:
   "apliqué X e Y; rechacé Z porque…; revisa de nuevo"). Repetir desde el paso 2.
6. **Corte por `max_rounds`.** Si se agotan las rondas sin `APPROVED`, parar y escalar al humano
   las disputas abiertas (findings no resueltos), con el estado en `review-log.md`.

## Salida

Devolver a la skill llamadora (o presentar, en modo directo):

- **Veredicto final:** `APPROVED` | `REVISE (rondas agotadas, N disputas abiertas)` | `UNAVAILABLE`.
- **Resumen de la crítica:** qué marcó el revisor, qué aplicó Claude y qué rechazó (con el porqué).
- **Diff del artefacto** si hubo cambios.
- **Ruta del `review-log.md`.**

La llamadora presenta este resumen **junto al artefacto** en su gate humano (mismo STOP, sin gate
extra). El humano aprueba con la segunda opinión ya a la vista.

## Degradación (nunca bloquea el flujo SDD)

Tres modos de falla, todos terminan en el gate humano de siempre con un aviso de una línea
("revisión cross-model no disponible — sigo con el gate humano"):

1. **El revisor no existe** (el subagente/CLI de la otra familia no está disponible) → Paso 0
   devuelve `UNAVAILABLE`.
2. **El revisor falla en runtime** (error, timeout de exec, `poll_deadline` vencido sin `VERDICT:`,
   o respuesta no parseable) → registrar el fallo en `review-log.md`, cortar el loop (y matar el
   proceso en background si lo hubo) y devolver `UNAVAILABLE` con lo que haya. **Nunca quedar
   esperando indefinida** — todos los caminos tienen tope duro (ver `reference.md` → "Latencia y
   timeout").
3. **Config la desactiva** (`cross_review.mode: off`, o complejidad por debajo del umbral) → ni
   se intenta; la llamadora va directo al gate.

> La cuarta forma de degradación —**que esta skill ni siquiera esté instalada**— la maneja la
> skill llamadora: `sdd-flow`/`sdd-orchestrator` chequean si `cross-review` está disponible
> y, si no, omiten la revisión. Por eso la dependencia es **blanda**: las skills SDD funcionan
> igual sin este helper.

## Configuración

Claves bajo `cross_review` en `.specify/config.yml` (sdd-flow) o en el `manifest.yml` de la
orquestación (sdd-orchestrator). Todas opcionales:

```yaml
cross_review:
  mode: auto            # auto (por complejidad) | on | off
  execution: auto       # auto (por capacidad del conductor) | sync | background
  artifacts: [spec, plan, tasks]   # qué tipos revisar (sdd-orchestrator: [master-spec, reparto])
  max_rounds: 3
  reviewer: auto        # auto (descubre por capacidad; nunca la familia del autor) | claude | codex
```

Precedencia (igual que el resto de overrides SDD): **override conversacional de la corrida >
config > default por complejidad**. Default por complejidad en `sdd-flow`: `trivial` off,
`normal` opt-in (off salvo pedido), `complex` on. En `sdd-orchestrator`, `auto` = **on** para
`master-spec`/`reparto`, que se revisan como `complex`. `execution: auto` (default) corre **sync** cuando
el conductor puede fijar un timeout largo (Claude Code: `Bash` hasta 600000ms) y **background+poll
acotado** cuando su exec es corto (Codex ~120s); en todos los modos hay tope duro → `UNAVAILABLE`,
nunca espera indefinida (ver `reference.md` → "Latencia y timeout").

## Router de intención

| El usuario dice (ej.) | Acción |
|---|---|
| "/cross-review `.plans/X/plan.md`", "revisa este plan con otra opinión" | revisar el artefacto nombrado (modo directo) |
| "pídele a Codex que critique la spec", "segunda opinión del plan" | revisar el artefacto (modo directo) |
| "/cross-review" sin ruta, "stress-test de esta idea", "arma un plan y que Codex lo critique" | **modo draft**: redactar el plan ligero + loop + ofrecer handoff (ver "Modo draft") |
| (invocada por `sdd-flow`/`sdd-orchestrator` en un gate) | modo embebido: revisar y devolver resumen |
| "sin cross-review", "salta la segunda opinión" | desactivar para la corrida (`mode: off`) |

## Referencias internas

- `reference.md` — cómo descubrir e invocar el revisor (subagente codex / `codex exec`
  read-only / resume entre rondas), **portabilidad entre shells (POSIX / PowerShell)**, plantilla
  del prompt, formato de salida, plantilla del `review-log.md`, y el foco de revisión por tipo de
  artefacto.
- `README.md` — qué es, cuándo usarla, requisitos e instalación.

## Atribución

El patrón de "revisión adversarial de otro modelo antes de implementar" está inspirado en la
skill `grill-me-codex` de chaseai (su "Acto 2") y, más atrás, en `grill-me` de Matt Pocock
(MIT); el **modo draft** ("redactar el plan primero y someterlo al loop") viene de su variante
standalone `codex-review`. Acá se toma la **idea**, no el código: la implementación, el contrato
con el runtime de Codex y la integración con el ciclo SDD son propios.
