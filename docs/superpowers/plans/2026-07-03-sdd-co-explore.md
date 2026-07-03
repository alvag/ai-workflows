# sdd-co-explore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crear la skill `sdd-co-explore` (exploración paralela cross-model) e integrarla en `sdd-flow` y `sdd-orchestrator`, según el spec `docs/superpowers/specs/2026-07-03-sdd-co-explore-design.md`.

**Architecture:** Skill nueva hermana de las SDD que despacha al revisor de otra familia a explorar el código en background (modo `explore` pre-spec, `counter-plan` pre-plan/pre-reparto) y devuelve un informe estructurado de hallazgos. `sdd-flow`/`sdd-orchestrator` orquestan: exploración propia del conductor en paralelo, síntesis con competencia de enfoques, y pasan los informes a `sdd-cross-review` como contexto (crítica informada). Todo degradable: sin revisor o vencido el deadline, el flujo sigue como hoy.

**Tech Stack:** Solo documentos Markdown de skills (SKILL.md / reference.md / README.md) — no hay código ejecutable. La "ejecución" la hace el agente que lee las skills. Verificación por `grep` de consistencia de nombres/anclas entre archivos.

## Global Constraints

Copiadas del spec y de las convenciones de las skills hermanas — **toda tarea las hereda**:

- **Fuente de verdad:** `docs/superpowers/specs/2026-07-03-sdd-co-explore-design.md`. Cada task lista qué secciones leer ANTES de escribir. Ante conflicto entre este plan y el spec, gana el spec.
- **Idioma y estilo:** español rioplatense/neutro, mismo tono y estructura que `skills/sdd-flow/SKILL.md` y `skills/sdd-cross-review/SKILL.md` (frontmatter YAML con `name`/`description`, secciones "Reglas no negociables", "Red flags", "Router de intención", "Referencias internas"). Diagramas ASCII en bloques de código.
- **Vocabulario fijo (interfaces entre archivos — usar EXACTAMENTE estos nombres):**
  - Skill: `sdd-co-explore`. Modos: `explore` | `counter-plan`.
  - Config: sub-clave `co_explore` bajo `cross_review`, campos `mode` (`auto`|`"on"`|`"off"`, on/off entre comillas) y `deadline` (segundos; defaults: 600 en `explore`, 300 en `counter-plan`).
  - Artefactos: carpeta `co-explore/` bajo `.plans/<id>/` (sdd-flow) o `.sdd/<id>/` (orchestrator), con `findings-<familia>.md` (uno por cada lado), `synthesis.md`, `session.json`, y scratch en `co-explore/scratch/`.
  - Secciones del informe (headings exactos): `## Mapa`, `## Hipótesis`, `## Puntos de reúso`, `## Riesgos`, `## Incógnitas`, `## Supuestos`, `## Enfoque sugerido`.
  - Estados de salida hacia la skill llamadora: `READY` | `UNAVAILABLE` (timeout/fallo ⇒ `UNAVAILABLE`, con lo que haya).
- **Reglas heredadas del ecosistema:** revisor read-only y de **otra familia que el autor** (regla 7 de cross-review); degradación en una línea sin bloquear jamás; descubrir por capacidad, no por nombre; artefactos locales y untracked (regla #10 de sdd-flow); overrides con precedencia `override de la corrida > config > default por complejidad`.
- **Sin placeholders** en las skills: nada de `TBD`/`TODO`/"etc." colgados.
- **Commits:** convencionales en inglés, sin firmas ni `Co-Authored-By`, uno por task (mensaje exacto en cada task).
- **No tocar** nada fuera de los archivos listados en cada task. `sdd-cross-review` solo recibe documentación (spec: "sin cambios estructurales").

---

### Task 1: `skills/sdd-co-explore/SKILL.md`

**Files:**
- Create: `skills/sdd-co-explore/SKILL.md`

**Interfaces:**
- Consumes: spec completo (secciones 1-5, 7, 8 y "Dudas del explorador en background").
- Produces: el contrato que Tasks 4 y 5 invocan — nombre `sdd-co-explore`, modos `explore`/`counter-plan`, inputs `mode`, `context_package`, `working_dir`, `complexity`, `execution`, `deadline`; salida `READY`/`UNAVAILABLE` + ruta del `findings-<familia>.md` + resumen. Punteros a secciones de `reference.md` que Task 2 debe crear con estos títulos exactos: "Prompt de exploración", "Formato del informe", "Plantilla de `synthesis.md`", "Descubrir el revisor (puntero + fallback)", "Latencia y deadlines", "Archivos de trabajo (scratch)".

- [ ] **Step 1: Leer las fuentes**

Leer: el spec completo (`docs/superpowers/specs/2026-07-03-sdd-co-explore-design.md`), `skills/sdd-cross-review/SKILL.md` entero (es el modelo de estructura y tono) y `skills/sdd-flow/SKILL.md` → secciones "Revisión cross-model" y "Reglas no negociables".

- [ ] **Step 2: Escribir el frontmatter y la cabecera**

Frontmatter sin `disable-model-invocation` (la invocan `sdd-flow`/`sdd-orchestrator` vía Skill tool, igual que `sdd-cross-review`):

```yaml
---
name: sdd-co-explore
description: >-
  Exploración paralela cross-model para flujos SDD: un modelo de otra familia
  que el autor (Codex cuando conduce Claude; Claude cuando conduce Codex)
  explora el código en background y devuelve un informe estructurado de
  hallazgos, ANTES de escribir la spec (modo explore) o como contra-enfoque
  antes del plan/reparto (modo counter-plan). La invocan sdd-flow y
  sdd-orchestrator cuando cross_review.co_explore está activo; también se puede
  invocar directo: "/sdd-co-explore <ticket|descripción>" o "que Codex explore
  esto en paralelo". NO revisa artefactos escritos (eso es sdd-cross-review):
  produce hallazgos e hipótesis propios para que compitan con los del conductor.
---
```

Debajo, cabecera con: qué es (2-3 párrafos: romper el anclaje — dos mapas independientes; el informe alimenta la síntesis del conductor y después la crítica informada de cross-review), y este diagrama:

```
paquete de contexto ──► [sdd-co-explore: revisor explora en background, read-only]
                              │                        (el conductor explora en paralelo
                              ▼                         por su cuenta — no espera)
                    findings-<familia>.md ──► síntesis del conductor ──► spec/plan
                    (+ session.json opcional)   (convergencias/divergencias,
                                                 competencia de enfoques)
```

- [ ] **Step 3: Escribir "Reglas no negociables"**

Siete reglas, cada una con su párrafo (contenido normativo del spec, secciones 2, 3 y "Dudas del explorador"):

1. **Read-only.** El explorador nunca escribe en el repo; su salida se captura por redirección del conductor (a `co-explore/scratch/`), nunca con permisos de escritura.
2. **Independencia (anti-anclaje).** El explorador solo recibe el paquete de contexto — nunca hallazgos, hipótesis ni borradores del conductor. Y simétrico: la skill llamadora no lee el informe hasta cerrar su propia exploración.
3. **Nunca se bloquea por dudas.** No es interactivo: toda duda se registra en el informe (pregunta abierta → `## Incógnitas`; decisión tomada para avanzar → `## Supuestos`, con el porqué) y se sigue explorando.
4. **Informe estructurado o nada.** La salida respeta el "Formato del informe" (`reference.md`); si no parsea, se degrada (texto libre como contexto, o descarte si es ruido) y se registra.
5. **Loop acotado, deadline duro.** Una sola pasada por modo (sin rondas); al vencer `deadline` se mata el proceso y se devuelve `UNAVAILABLE` con lo que haya. Nunca espera indefinida.
6. **Opcional y degradable.** Sin revisor de otra familia, fallo en runtime o `mode: off` → `UNAVAILABLE` en una línea; la llamadora sigue con la exploración del conductor solamente.
7. **Revisor de OTRA familia, por capacidad.** Misma regla 7 de `sdd-cross-review` (familia = modelo de respaldo, no el CLI; sondear el entorno; higiene de entorno si aplica). El algoritmo canónico vive en `sdd-cross-review/reference.md` → "Descubrir el revisor"; acá solo el puntero + fallback mínimo (ver `reference.md` → "Descubrir el revisor (puntero + fallback)").

- [ ] **Step 4: Escribir "Red flags — pará y reconsiderá"**

Tabla estilo cross-review con al menos estas filas (racionalización → realidad):

| Racionalización | Realidad |
|---|---|
| "Le paso al explorador mi hipótesis para que no pierda tiempo" | Rompe la independencia (regla 2): el valor está en dos mapas sin contaminar. Solo viaja el paquete de contexto. |
| "Miro su informe mientras exploro, total ya terminó" | El conductor no lee `findings-*` hasta cerrar y escribir su propio informe. |
| "El explorador no contestó, espero un poco más" | Deadline duro (regla 5): matar el proceso, `UNAVAILABLE`, seguir con lo propio. |
| "Su enfoque se ve bien, lo adopto y listo" | Los enfoques compiten en la síntesis: evaluar en méritos y registrar el porqué en `synthesis.md`; enfoques viables pero distintos = divergencia al checkpoint. |
| "Su duda la respondo yo mentalmente y sigo" | Las Incógnitas que cambiarían el diseño van a `clarify`; las respuestas quedan en `## Clarifications` de la spec. |

- [ ] **Step 5: Escribir "Contrato de invocación" y "Salida"**

**Inputs** (los pasa la skill llamadora, o se infieren en modo directo): `mode` (`explore` | `counter-plan`), `context_package` (digest del ticket + prompt + AC preliminares si existen; en `counter-plan`: ruta de la `spec.md` aprobada + ruta del propio `findings-<familia>.md` de la fase explore), `working_dir` (uno, o lista de repos cuando llama el orquestador), `complexity`, `execution` (`auto`|`sync`|`background`; para `explore` el valor útil es `background` — el conductor explora mientras tanto), `deadline` (opcional; defaults 600/300).

**Pasos de ejecución** (numerados en la skill):
1. Resolver el revisor (regla 7). Sin revisor → `UNAVAILABLE`.
2. Armar el prompt desde `reference.md` → "Prompt de exploración" (por modo) con el paquete de contexto inline.
3. Lanzar en background read-only, stdout redirigido a `co-explore/scratch/explorer.out`; guardar PID y, si el runtime lo expone, la referencia de sesión en `co-explore/session.json`.
4. En `explore`, devolver el control de inmediato ("explorando en background") — la llamadora hace su propia exploración y vuelve a consultar en el punto de encuentro. En `counter-plan` o `execution: sync`, esperar con tope.
5. Punto de encuentro: si terminó, normalizar la salida al "Formato del informe" y escribirla en `co-explore/findings-<familia>.md`; si venció el deadline, matar el proceso y `UNAVAILABLE`.

**Salida a la llamadora:** estado `READY` | `UNAVAILABLE` · ruta del `findings-<familia>.md` (si hay) · resumen de 3-5 líneas (hallazgos top + enfoque sugerido) · ruta de `session.json` si existe.

**Modo directo** (el usuario invoca `/sdd-co-explore <ticket|descripción>`): inferir `mode: explore`, armar el `context_package` desde el prompt (+ tracker si hay clave y MCP), correr y **presentar** el informe al usuario.

- [ ] **Step 6: Escribir "La síntesis (guía para la skill llamadora)" + "Configuración" + "Degradación" + "Router de intención" + "Referencias internas"**

**Síntesis** (el conductor la ejecuta; acá vive la guía para que ambas llamadoras no la dupliquen): escribir su propio `findings-<familia>.md` ANTES de leer el del revisor; comparar sección por sección; producir `synthesis.md` (plantilla en `reference.md`) con tabla de convergencias/divergencias, el **duelo de enfoques** (evaluación en méritos: reúso, riesgo, simplicidad, encaje con el repo; elección o híbrido + rationale), e Incógnitas fusionadas (las que cambiarían el diseño → `clarify`). Divergencias no resueltas → checkpoint informativo de la llamadora.

**Configuración** (bloque YAML — clave completa, la llamadora la hereda):

```yaml
cross_review:
  co_explore:
    mode: auto        # auto (por complejidad: complejo on, normal opt-in, trivial nunca) | "on" | "off"
    deadline: 600     # segundos (explore; counter-plan usa 300 salvo override)
```

**Degradación:** las 4 vías del spec (sección 7), cada una en una línea, todas terminando en "la llamadora sigue con la exploración del conductor".

**Router de intención:** filas para "/sdd-co-explore X" (directo), "que Codex explore esto en paralelo" (directo), "con co-exploración"/"sin co-exploración" (override de la corrida — lo registra la llamadora), invocación embebida por sdd-flow/sdd-orchestrator.

**Referencias internas:** `reference.md` (con los 6 títulos exactos listados en Interfaces) y `README.md`.

- [ ] **Step 7: Verificar consistencia**

```bash
cd /Users/max/Personal/repos/ai-workflows
grep -c 'co_explore' skills/sdd-co-explore/SKILL.md          # esperado: >= 3
grep -n 'counter-plan\|## Mapa\|## Supuestos\|READY\|UNAVAILABLE' skills/sdd-co-explore/SKILL.md | head -20
grep -n 'disable-model-invocation' skills/sdd-co-explore/SKILL.md   # esperado: SIN matches (exit 1)
grep -rn 'TBD\|TODO' skills/sdd-co-explore/SKILL.md           # esperado: SIN matches (exit 1)
```

- [ ] **Step 8: Commit**

```bash
git add skills/sdd-co-explore/SKILL.md
git commit -m "feat: add sdd-co-explore skill contract (SKILL.md)"
```

---

### Task 2: `skills/sdd-co-explore/reference.md`

**Files:**
- Create: `skills/sdd-co-explore/reference.md`

**Interfaces:**
- Consumes: los 6 títulos de sección prometidos por Task 1 (deben existir EXACTOS): "Prompt de exploración", "Formato del informe", "Plantilla de `synthesis.md`", "Descubrir el revisor (puntero + fallback)", "Latencia y deadlines", "Archivos de trabajo (scratch)".
- Produces: formato del informe y plantilla de síntesis que Tasks 4 y 5 referencian; esquema de `session.json` que Task 6 documenta en cross-review.

- [ ] **Step 1: Leer las fuentes**

Leer `skills/sdd-cross-review/reference.md` → secciones "Invocar al revisor (read-only)" (con sus Vías A/B/C), "Descubrir el revisor", "Latencia y timeout", "Resume entre rondas", "Prompt de revisión", "Archivos de trabajo (scratch)" — se reusa su estructura y estilo, adaptando de "criticar un artefacto" a "explorar el código".

- [ ] **Step 2: Escribir "Tabla de contenidos" + "Prompt de exploración"**

Prompt XML por modo, siguiendo el estilo del "Prompt de revisión" de cross-review. Plantilla `explore`:

```xml
<task>
Sos un ingeniero explorando este repo para preparar un cambio. NO escribas ni
modifiques nada: solo leé, buscá y razoná. Trabajás SOLO: nadie va a responder
preguntas — toda duda se registra (ver output_contract) y seguís explorando.
</task>
<context_package>
{digest del ticket + prompt del usuario + AC preliminares si existen + complejidad}
</context_package>
<focus>
Mapear el terreno para este cambio: dónde vive lo que hay que tocar, qué existe
para reusar, qué puede romperse, y qué enfoque seguirías vos. Referenciá todo
con path:line.
</focus>
<output_contract>
Tu ÚLTIMA salida debe ser EXACTAMENTE este markdown (headings literales):
## Mapa\n## Hipótesis\n## Puntos de reúso\n## Riesgos\n## Incógnitas\n## Supuestos\n## Enfoque sugerido
- Incógnitas: preguntas abiertas que no pudiste resolver leyendo el código.
- Supuestos: qué asumiste para poder seguir, y por qué.
- Enfoque sugerido: 3-5 bullets, tu solución preferida.
Cerrá con la línea: STATUS: done
</output_contract>
```

Variante `counter-plan` (misma estructura): `<task>` pide proponer el enfoque técnico propio para la spec dada; `<context_package>` = spec.md aprobada + tu findings previo; `<focus>` = qué tocarías, qué reusarías, en qué orden, riesgos — "## Enfoque sugerido es el cuerpo principal; en orquestación, proponé el reparto tentativo (repo → AC, depends_on)". Mismo `<output_contract>`.

- [ ] **Step 3: Escribir "Formato del informe" + "Plantilla de `synthesis.md`"**

**Formato del informe:** los 7 headings exactos con 1-2 líneas de qué va en cada uno (copiar las descripciones de la sección 2 del spec, incluida la nota de que en `counter-plan` el cuerpo principal es `## Enfoque sugerido`).

**Plantilla de `synthesis.md`:**

```markdown
# Síntesis co-explore — <id> (<ISO-8601>)

## Convergencias
- <hecho/hipótesis en que ambos mapas coinciden>

## Divergencias
| # | Tema | Conductor dice | Revisor dice | Resolución (o "abierta → checkpoint") |
|---|---|---|---|---|

## Duelo de enfoques
- **Enfoque del conductor:** <bullets>
- **Enfoque del revisor:** <bullets>
- **Elección:** <uno / híbrido> — **Rationale:** <reúso, riesgo, simplicidad, encaje>

## Incógnitas fusionadas
- [ ] <pregunta> — origen: <conductor|revisor> — ¿cambia el diseño? <sí → clarify | no>

## Supuestos del revisor a vigilar
- <supuesto> (verificar en la crítica de la spec)
```

- [ ] **Step 4: Escribir "Descubrir el revisor (puntero + fallback)" + "Latencia y deadlines" + "Archivos de trabajo (scratch)" + "Portabilidad entre shells"**

**Descubrir el revisor:** párrafo puntero — "el algoritmo canónico vive en `sdd-cross-review/reference.md` → 'Descubrir el revisor'; si esa skill está instalada, leerlo de ahí" — más el **fallback mínimo embebido** (para co-explore sin cross-review): regla de familia (autor = modelo de respaldo, no CLI; sondear `ANTHROPIC_BASE_URL`/`ANTHROPIC_DEFAULT_*_MODEL`), y la invocación directa portable: autor Claude → `codex exec` read-only en background; autor GPT/Codex → `claude -p` restringido a tools de lectura. Comandos POSIX y PowerShell concretos (adaptar los bloques de la Vía B/C de cross-review: mismo binario y flags, prompt de exploración por stdin/archivo, stdout a `co-explore/scratch/explorer.out`, capturar PID).

**Latencia y deadlines:** tabla — `explore`: default 600 s (poll cada 10 s ⇒ ~60 intentos); `counter-plan`: 300 s (~30 intentos); override por `co_explore.deadline`. Tope duro: matar PID + `UNAVAILABLE`. Señal de fin: línea `STATUS: done` en la salida. Nota: en `explore` el conductor NO espera en loop — lanza, explora lo suyo, y recién en el punto de encuentro hace el poll restante.

**Archivos de trabajo:** árbol de `co-explore/` (findings-*.md, synthesis.md, session.json, scratch/ con explorer.out, prompt.txt, stderr). Esquema de `session.json`:

```json
{ "tool": "codex", "session_id": "<id-o-ruta-que-permita-resume>", "mode": "explore", "created_at": "<ISO-8601>" }
```

con la nota: "lo consume `sdd-cross-review` para el resume oportunista; si el runtime no expone sesión, no escribir el archivo".

- [ ] **Step 5: Verificar consistencia**

```bash
cd /Users/max/Personal/repos/ai-workflows
# Los 6 títulos prometidos por SKILL.md existen:
grep -n '^## Prompt de exploración\|^## Formato del informe\|^## Plantilla de `synthesis.md`\|^## Descubrir el revisor (puntero + fallback)\|^## Latencia y deadlines\|^## Archivos de trabajo (scratch)' skills/sdd-co-explore/reference.md
# esperado: 6 líneas
grep -c 'STATUS: done' skills/sdd-co-explore/reference.md    # esperado: >= 2 (prompt + latencia)
grep -n 'session.json' skills/sdd-co-explore/reference.md | head -5
```

- [ ] **Step 6: Commit**

```bash
git add skills/sdd-co-explore/reference.md
git commit -m "feat: add sdd-co-explore reference (prompts, report format, synthesis)"
```

---

### Task 3: `skills/sdd-co-explore/README.md`

**Files:**
- Create: `skills/sdd-co-explore/README.md`

**Interfaces:**
- Consumes: contrato de Task 1.
- Produces: nada que otras tasks referencien.

- [ ] **Step 1: Escribir el README**

Siguiendo la estructura del `skills/sdd-cross-review/README.md` (leerlo primero): qué es (2 párrafos: dos mapas independientes + crítica informada), cuándo usarla / cuándo NO (no revisa artefactos — eso es cross-review), requisitos (un segundo modelo de otra familia: Codex CLI o Claude CLI; `sdd-cross-review` recomendado para el algoritmo canónico de descubrimiento y la crítica informada), instalación (copiar/symlinkear `skills/sdd-co-explore/` al directorio de skills del entorno), configuración (el bloque YAML `cross_review.co_explore` de Task 1), y 3 ejemplos de uso: embebida por sdd-flow (complejo, auto), override conversacional ("con co-exploración"), modo directo (`/sdd-co-explore PROJ-123`).

- [ ] **Step 2: Verificar y commitear**

```bash
cd /Users/max/Personal/repos/ai-workflows
grep -n 'co_explore\|counter-plan' skills/sdd-co-explore/README.md | head -5   # esperado: matches
git add skills/sdd-co-explore/README.md
git commit -m "docs: add sdd-co-explore README"
```

---

### Task 4: Integración en `sdd-flow`

**Files:**
- Modify: `skills/sdd-flow/SKILL.md` (ciclo, checkpoint de inicio, sección nueva, `analyze`, `plan`, router, "Revisión cross-model")
- Modify: `skills/sdd-flow/reference.md` (sección "Esquema de `.specify/config.yml`", línea ~129)

**Interfaces:**
- Consumes: contrato de Task 1 (invocación con `mode`/`context_package`/…; salida `READY`/`UNAVAILABLE`); guía de síntesis de Task 1; plantilla de `synthesis.md` de Task 2.
- Produces: el patrón de orquestación (despacho → exploración propia → punto de encuentro → síntesis → checkpoint condicional) que Task 5 replica a nivel multi-repo.

- [ ] **Step 1: Leer las fuentes**

Releer spec secciones 1, 3, 4, 6 y `skills/sdd-flow/SKILL.md` → "Adaptación al proyecto" (checkpoint de inicio), "Revisión cross-model", pasos `gather-context`, `analyze`, `specify`, `plan`, "Router de intención", "Red flags".

- [ ] **Step 2: Actualizar el diagrama del ciclo y el checkpoint de inicio**

En el diagrama del ciclo (línea ~30), insertar `co-explore` entre `gather-context` y `specify`:

```
init (opcional) → constitution → gather-context → co-explore (opcional, paralela) → specify ─┐
```

y agregar debajo la línea aclaratoria: `(co-explore: exploración paralela cross-model opcional — ver "Co-exploración cross-model")`.

En el **Checkpoint de inicio** (sección "Adaptación al proyecto"): sumar `cross_review.co_explore.mode` a los valores que se ecoan, y actualizar el ejemplo: *"config: tracker jira · cross_review on · co_explore on → exploración paralela antes de la spec · jira_approval on → …"*. En la tabla de **Red flags**, fila "Arranco el flujo sin leer el config": agregar `co_explore` a la lista de valores que se pierden en silencio.

En el bloque YAML del esquema de config (sección "Adaptación al proyecto", línea ~112), reemplazar la línea de `cross_review` por:

```yaml
cross_review: {mode: auto, execution: auto, co_explore: {mode: auto, deadline: 600}}  # segunda opinión + co-exploración; ver "Revisión cross-model" y "Co-exploración cross-model"
```

- [ ] **Step 3: Escribir la sección nueva "Co-exploración cross-model (opcional)"**

Ubicarla inmediatamente después de la sección "Revisión cross-model". Contenido (espejo estructural de esa sección, ~40-60 líneas):

- **Qué es** (2 líneas) + cuándo se activa: precedencia `override de la corrida > cross_review.co_explore de config.yml > default por complejidad (complejo on, normal opt-in, trivial nunca)`. Ortogonal a `cross_review.mode`.
- **Momento 1 — `explore` (pre-spec):** tras confirmar el contexto y la clasificación en `gather-context`: (1) armar el paquete de contexto (digest + prompt + complejidad); (2) invocar `sdd-co-explore` (Skill tool) con `mode: explore`, `execution: background`; (3) hacer la **exploración propia** sin leer nada del revisor y escribir `findings-<familia-conductor>.md` (mismo formato); (4) punto de encuentro: recoger el informe (`READY`) o seguir sin él (`UNAVAILABLE`, aviso de una línea); (5) **síntesis** según la guía de `sdd-co-explore` → `synthesis.md` (convergencias/divergencias, duelo de enfoques con rationale, incógnitas fusionadas → alimentan `clarify`); (6) **checkpoint informativo condicional**: solo si quedaron divergencias abiertas o enfoques viables materialmente distintos — presentarlos y dejar decidir; si converge, seguir directo a `specify`.
- **Momento 2 — `counter-plan` (pre-plan):** con la spec aprobada (y ya en la rama), antes de escribir `plan.md`: invocar `sdd-co-explore` con `mode: counter-plan` (contexto: spec + findings previo del revisor); contrastar el contra-enfoque con el propio en una adenda de `synthesis.md`; escribir el plan con esa síntesis a la vista.
- **Efecto en `analyze`:** con co-exploración corrida, `analyze` NO re-explora: es un **refresco incremental** — validar que el mapa pre-spec sigue vigente sobre el HEAD real de la rama (archivos movidos, código cambiado desde entonces) y anotar deltas.
- **Crítica informada:** en los gates de `specify` y `plan`, pasar a `sdd-cross-review` los informes como `context_paths` adicionales (`findings-<familia>.md`; en el plan, también el counter-plan) — y si existe `co-explore/session.json`, mencionarlo para el resume oportunista.
- **Degradación:** skill no instalada / `UNAVAILABLE` / deadline → una línea ("co-exploración no disponible — sigo con mi exploración") y flujo normal. Nunca bloquea.

- [ ] **Step 4: Retocar `analyze`, `plan`, y el Router**

- Paso `analyze`: agregar al final la línea: "**Con co-exploración corrida** (ver 'Co-exploración cross-model'), este paso es un refresco incremental del mapa, no una re-exploración."
- Paso `plan`, punto 4 (STOP): donde dice que se ejecuta cross-review sobre `plan.md` con `spec` como contexto, agregar: "(con co-exploración: sumar `co-explore/findings-<familia>.md` y el counter-plan como contexto — ver 'Co-exploración cross-model')". Análogo en el paso `specify` punto 4.
- Router de intención: agregar la fila `| "con co-exploración", "que Codex explore en paralelo" / "sin co-exploración" | registra el **override de co-exploración** de la corrida (on/off; ver "Co-exploración cross-model") |`.
- Sección "Revisión cross-model", bullet "Cómo invocarla": agregar `context_paths` de co-explore a la lista de lo que se pasa cuando existan.

- [ ] **Step 5: Actualizar `skills/sdd-flow/reference.md`**

En "Esquema de `.specify/config.yml`" (bloque YAML, línea ~134): reemplazar la línea `cross_review:` existente por la versión con `co_explore` anidado (mismo bloque del Step 2) y una línea de comentario explicando `deadline`.

- [ ] **Step 6: Verificar consistencia**

```bash
cd /Users/max/Personal/repos/ai-workflows
grep -n 'Co-exploración cross-model' skills/sdd-flow/SKILL.md        # esperado: >= 4 (sección + referencias cruzadas)
grep -n 'co_explore' skills/sdd-flow/SKILL.md skills/sdd-flow/reference.md   # esperado: >= 4
grep -n 'sdd-co-explore' skills/sdd-flow/SKILL.md                    # esperado: >= 2 (explore y counter-plan)
grep -n 'refresco incremental' skills/sdd-flow/SKILL.md              # esperado: >= 1
```

- [ ] **Step 7: Commit**

```bash
git add skills/sdd-flow/SKILL.md skills/sdd-flow/reference.md
git commit -m "feat(sdd-flow): integrate co-explore (parallel cross-model exploration)"
```

---

### Task 5: Integración en `sdd-orchestrator`

**Files:**
- Modify: `skills/sdd-orchestrator/SKILL.md` (sección "Revisión cross-model", Fase 1, Fase 2 paso 3, router)
- Modify: `skills/sdd-orchestrator/reference.md` (sección "Esquema de `manifest.yml`", línea ~32)

**Interfaces:**
- Consumes: contrato de Task 1; patrón de orquestación de Task 4 (replicado a nivel sistema).
- Produces: nada que otras tasks consuman.

- [ ] **Step 1: Leer las fuentes**

Releer spec sección 8 y `skills/sdd-orchestrator/SKILL.md` → Fase 1 completa (1.1-1.4), Fase 2 paso 3 (fan-out con `cross_review.mode: off`), "Revisión cross-model", "Router de intención".

- [ ] **Step 2: Escribir la subsección "Co-exploración cross-model (opcional)" del orquestador**

Ubicarla después de la sección "Revisión cross-model". Contenido (~25-35 líneas):

- **`explore` (pre-`master-spec`):** corre **después de 1.2 (selección de repos confirmada)** — el revisor necesita saber dónde mirar — y antes de 1.3. Paquete de contexto global + lista de repos confirmados como `working_dir`s. Foco a nivel sistema: contratos entre servicios existentes, superficies de integración, riesgos `[integration]`. El conductor explora en paralelo y sintetiza igual que `sdd-flow` (guía en `sdd-co-explore`). **Si el informe sugiere que un repo no confirmado está involucrado** (en Riesgos/Incógnitas), re-abrir la selección de repos con el usuario antes de escribir la master-spec.
- **`counter-plan` (pre-reparto):** con la `master-spec.md` aprobada, antes de 1.4: el revisor propone su **reparto tentativo** (repo → AC cubiertos, `depends_on`, orden); el conductor lo contrasta antes de escribir el reparto real. Errores de DAG y cobertura AC↔repo son el objetivo.
- **Artefactos:** `.sdd/<id>/co-explore/` (mismos nombres que en sdd-flow; local, untracked — regla 7).
- **Config:** `cross_review.co_explore` en el `manifest.yml`; default `auto` = **on** (los artefactos de orquestación son el caso complejo por definición, igual que su cross-review). Deadlines: usar los de `complexity: complex` (600 s) como piso.
- **Crítica informada:** pasar los informes como `context_paths` en las revisiones de `master-spec` (gate 1.3) y `reparto` (gate 1.4).
- **Sin doble co-exploración:** la Fase 2 ya delega con `cross_review.mode: off`; dejar explícito que eso **también apaga `co_explore`** en los `sdd-flow` por-repo.

- [ ] **Step 3: Retocar Fase 1, Fase 2 y Router**

- 1.2, tras el punto 3 (confirmación): agregar "Con co-exploración activa, acá se despacha el `explore` global (ver 'Co-exploración cross-model')."
- 1.3, punto 3 (STOP): agregar los `context_paths` de co-explore a la revisión de `master-spec`.
- 1.4: antes del punto 1, línea del `counter-plan`; en el punto 4 (STOP), sumar el reparto tentativo como contexto de la revisión del `reparto`.
- Fase 2 paso 3: donde dice `cross_review.mode: off`, cambiar a "… con la corrida en `cross_review.mode: off` (que apaga también `co_explore`): los `plan.md`/`tasks.md` por repo ya quedaron cubiertos por la revisión del reparto y la exploración global ya cubrió ese terreno".
- Router: fila `| "con co-exploración" / "sin co-exploración" | override de co-exploración de la orquestación (on/off; ver "Co-exploración cross-model") |`.

- [ ] **Step 4: Actualizar `skills/sdd-orchestrator/reference.md`**

En "Esquema de `manifest.yml`": dentro del bloque de ejemplo, bajo la clave `cross_review` existente (o creándola si el esquema la muestra suelta), anidar `co_explore: {mode: auto, deadline: 600}` con comentario de una línea ("co-exploración: default on en orquestación; ver SKILL.md → Co-exploración cross-model").

- [ ] **Step 5: Verificar consistencia**

```bash
cd /Users/max/Personal/repos/ai-workflows
grep -n 'Co-exploración cross-model' skills/sdd-orchestrator/SKILL.md   # esperado: >= 3
grep -n 'co_explore' skills/sdd-orchestrator/SKILL.md skills/sdd-orchestrator/reference.md  # esperado: >= 3
grep -n 'reparto tentativo' skills/sdd-orchestrator/SKILL.md            # esperado: >= 1
grep -n 'apaga también' skills/sdd-orchestrator/SKILL.md                # esperado: 1 (Fase 2)
```

- [ ] **Step 6: Commit**

```bash
git add skills/sdd-orchestrator/SKILL.md skills/sdd-orchestrator/reference.md
git commit -m "feat(sdd-orchestrator): integrate co-explore for master-spec and reparto"
```

---

### Task 6: Documentación en `sdd-cross-review`

**Files:**
- Modify: `skills/sdd-cross-review/SKILL.md` (sección "Contrato de invocación")
- Modify: `skills/sdd-cross-review/reference.md` (secciones "Resume entre rondas" y "Descubrir el revisor")

**Interfaces:**
- Consumes: esquema de `session.json` de Task 2.
- Produces: nada. **Restricción del spec: sin cambios estructurales** — solo documentar lo que ya soporta.

- [ ] **Step 1: SKILL.md — nota en "Contrato de invocación"**

En el bullet de `context_paths`, agregar al final: "Si el flujo corrió **co-exploración** (`sdd-co-explore`), la llamadora pasa acá los `co-explore/findings-*.md` (y el counter-plan al revisar `plan`): la crítica sale informada por la exploración previa del propio revisor."

- [ ] **Step 2: reference.md — resume oportunista + nota de fuente canónica**

- En "Resume entre rondas" (línea ~453), agregar párrafo final: "**Seed desde co-exploración:** si existe `co-explore/session.json` (escrito por `sdd-co-explore`; esquema: `{tool, session_id, mode, created_at}`), la Ronda 1 puede **reanudar esa sesión** en lugar de abrir una nueva — el crítico es el mismo agente que exploró. Si el resume falla, abrir sesión nueva con los `findings-*.md` como contexto: mismo efecto, sin estado."
- En "Descubrir el revisor" (línea ~61), agregar al inicio la nota: "Esta sección es la **fuente canónica** del descubrimiento: `sdd-co-explore` la referencia por puntero (su fallback embebido es un resumen de esto)."

- [ ] **Step 3: Verificar y commitear**

```bash
cd /Users/max/Personal/repos/ai-workflows
grep -n 'co-explore\|sdd-co-explore' skills/sdd-cross-review/SKILL.md skills/sdd-cross-review/reference.md
# esperado: >= 3 matches (contrato, resume, fuente canónica)
git add skills/sdd-cross-review/SKILL.md skills/sdd-cross-review/reference.md
git commit -m "docs(sdd-cross-review): document co-explore context and session seed"
```

---

### Task 7: Coherencia global y cierre

**Files:**
- Modify: `docs/superpowers/specs/2026-07-03-sdd-co-explore-design.md` (línea de estado)

**Interfaces:**
- Consumes: todo lo anterior.

- [ ] **Step 1: Barrido de consistencia cross-archivo**

```bash
cd /Users/max/Personal/repos/ai-workflows
# El vocabulario fijo aparece consistente en todas las skills tocadas:
grep -rn 'co_explore' skills/ | grep -v 'co-explore/' | cut -d: -f1 | sort -u
# esperado: SKILL.md/reference.md de sdd-co-explore, sdd-flow, sdd-orchestrator (6 archivos)
grep -rn 'counterplan\|counter_plan\|co-explorar\|coexplore' skills/   # esperado: SIN matches (typos de vocabulario)
# Los títulos referenciados entre archivos existen:
grep -n '^## Descubrir el revisor' skills/sdd-cross-review/reference.md   # esperado: 1
grep -rn 'findings-<familia>' skills/ | cut -d: -f1 | sort -u             # esperado: los 3+ archivos que lo citan
grep -rn 'TBD\|TODO' skills/sdd-co-explore/                               # esperado: SIN matches
```

Si algún grep no da lo esperado, corregir el archivo correspondiente antes de seguir.

- [ ] **Step 2: Lectura de humo del flujo completo**

Releer en orden: `sdd-flow/SKILL.md` → "Co-exploración cross-model" → seguir mentalmente un flujo *complejo* de punta a punta (gather-context → explore → síntesis → specify+crítica informada → counter-plan → plan+crítica) verificando que cada paso nombra el archivo/sección correcta y que ningún paso quedó contradictorio con los gates existentes (el conteo de gates trivial=1/normal=2/complejo=3 NO cambia: co-explore agrega solo un checkpoint informativo condicional). Repetir para `sdd-orchestrator` (Fase 1). Anotar y corregir cualquier inconsistencia.

- [ ] **Step 3: Actualizar el estado del spec y commit final**

En `docs/superpowers/specs/2026-07-03-sdd-co-explore-design.md`, cambiar la línea `**Estado:** diseño aprobado en conversación; pendiente de plan de implementación.` por `**Estado:** implementado (ver docs/superpowers/plans/2026-07-03-sdd-co-explore.md).`

```bash
git add docs/superpowers/specs/2026-07-03-sdd-co-explore-design.md
git commit -m "docs: mark sdd-co-explore design as implemented"
```

---

## Self-review del plan (ya corrido)

- **Cobertura del spec:** secciones 1-3 → Tasks 1-2 y 4; sección 4 → Tasks 4 y 6; sección 5 → Tasks 2 y 6; sección 6 → Tasks 1, 4 y 5; sección 7 → Tasks 1-2; sección 8 → Task 5; "Cambios requeridos" → mapeo 1:1 con Tasks 1-6; "Criterios de éxito" → verificables tras Task 7.
- **Consistencia de nombres:** vocabulario fijo centralizado en Global Constraints; verificado por los greps de Task 7.
- **Sin placeholders:** cada step tiene contenido o comando concreto; los puntos que delegan redacción citan la sección exacta del spec o de una skill hermana como fuente.
