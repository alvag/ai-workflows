---
name: sdd-flow
description: >-
  Spec-Driven Development (SDD) portable y agnóstico de proyecto: desarrolla una
  feature/fix/refactor con artefactos auditables (spec, plan, tasks) y gates de
  aprobación escalados por complejidad, verificando los criterios de aceptación
  antes de commitear. Detecta stack, host de Git y tracker por convención. Usar
  cuando quieras llevar un cambio de punta a punta con SDD en cualquier repo, o
  retomar un plan en una sesión fresca. Invocación explícita: "/sdd-flow" para
  empezar, o "/sdd-flow implement" con la ruta de la carpeta del plan. Opcional:
  indicar un prefijo de rama (p. ej. "con prefijo de rama feature/") que reemplaza
  el prefijo semántico.
argument-hint: "[init | <ticket|descripción> | implement .plans/<id>/ | continuemos con <id>]"
# disable-model-invocation es una clave REAL de Claude Code: bloquea la invocación
# vía Skill tool (la skill queda solo-slash: /sdd-flow). Se mantiene a propósito:
# los triggers de esta skill son genéricos ("arma el plan", "implementa") y sin el
# flag competiría por el auto-trigger. Consecuencia asumida: otras skills y
# subagentes NO pueden invocarla con el Skill tool — sdd-orchestrator delega
# leyendo estos archivos (ver su Fase 2).
disable-model-invocation: true
---

# sdd-flow — Spec-Driven Development portable

Skill **agnóstica de proyecto**: no asume lenguaje, framework, host de Git, tracker ni rama base. Todo se **descubre por convención** y se puede sobrescribir en `.specify/config.yml` (ver "Adaptación al proyecto"). La fuente de verdad es la **especificación**, no el código: cada cambio nace de un `spec.md` con criterios de aceptación verificables, y se cierra comprobándolos.

El ciclo SDD:

```
init (opcional) → constitution → gather-context → co-explore (opcional, paralela) → specify ─┐
                                                                                              ├─► clarify (condicional)
                                                                                              ▼
       publish-spec (Jira, opcional) ──► create-branch → analyze → plan ──► tasks ──► implement ──► verify
   (gates escalados por complejidad: trivial=1, normal=2, complejo=3 + clarify obligatorio)
   (publish-spec: gate externo opcional — aprobación del TL/PO en Jira; solo con jira_approval on)
   (init y constitution son setup checkpoints opcionales, no gates SDD)
   (co-explore: exploración paralela cross-model opcional — ver "Co-exploración cross-model")
```

Artefactos en disco:

```
<repo>/                   # TODO lo de abajo es LOCAL: la skill nunca lo trackea ni commitea
├─ .specify/
│  ├─ constitution.md     # principios de PROCESO
│  ├─ config.yml          # overrides de adaptación (opcional)
│  └─ reviewers.json      # reviewers por defecto del PR (opcional; lo usa `open-pr`)
└─ .plans/
   ├─ <id>/               # un flujo en curso
   │  ├─ spec.md          # QUÉ + por qué + criterios de aceptación (AC-n) + Clarifications
   │  ├─ plan.md          # header YAML (incluye status + branch) + CÓMO + resultado de verify
   │  ├─ tasks.md         # tareas atómicas [ ], cada una referencia AC-n
   │  ├─ handoff.md       # retomado del flujo: dónde quedó + decisiones + cómo sigue (pause / gate Jira)
   │  └─ jira-spec.md     # copia exacta de lo publicado en Jira (solo con el gate de aprobación)
   └─ archived/           # flujos cerrados (status: done), movidos solo tras tu confirmación
      └─ <id>/            # misma estructura, ya terminada
```

Como `.plans/` y `.specify/` son **locales (untracked)**, git no los mueve al cambiar de rama: están presentes en **todas** las ramas del working tree. Eso es deliberado — convierte a `.plans/` en un catálogo de flujos visible desde cualquier rama, y cada `plan.md` lleva en su header la `branch` a la que pertenece. Esa es la base del paso `resume` (retomar un flujo aunque estés posicionado en otra rama).

`<id>` = clave del ticket si existe (`ABC-123`), o slug del título si no hay tracker.

## Reglas no negociables

1. **La spec manda.** No se escribe `plan.md` sin un `spec.md` aprobado (salvo cambio *trivial*, ver "Clasificador de complejidad"). No se implementa sin tasks aprobadas. La verificación final chequea contra los criterios de aceptación de la spec.
2. **Gates escalados, nunca silenciosos.** El número de gates depende de la complejidad clasificada, pero el agente **siempre** anuncia qué clasificación eligió y por qué, y espera confirmación en cada gate activo. No colapsar gates sin avisar.
3. **No tocar código hasta aprobar las tasks** (en `tasks.md`, o embebidas en el plan combinado en cambios *triviales*). La skill se detiene en cada gate y solo continúa con aprobación explícita ("aprobado", "dale", "sigue", o equivalente).
4. **Trazabilidad obligatoria.** Cada criterio de aceptación lleva id `AC-n`. Cada task referencia ≥1 `AC-n`. Antes de implementar se valida que no haya AC huérfanos (sin task) ni tasks sin AC.
5. **Adaptación por descubrimiento, no por suposición.** Detectar stack, comandos de test/build, host de Git, tracker y rama base. Nunca hardcodear comandos ni nombres. Si algo no se puede inferir y no está en `config.yml`, preguntar una vez (y ofrecer persistirlo).
6. **Degradación elegante.** Si un MCP/CLI opcional (tracker, navegador, host de Git) no está disponible, avisar y continuar con lo que haya (p. ej. pedir el resumen del ticket, o analizar sin reproducción en navegador).
7. **Tests + build obligatorios tras implementar.** Con los comandos detectados/configurados. Si fallan, no commitear: mostrar el error y proponer fix.
8. **Stage selectivo.** Mantener un registro de los archivos que la skill tocó durante `implement` y compararlo contra el working tree antes de cualquier `git add`. Nunca stagear archivos ajenos sin confirmación.
9. **Commit y push siempre confirmados.** Ofrecer revisión manual antes del commit (gate que se ofrece siempre, salteable). Antes de ejecutar el commit, mostrar archivos staged + mensaje + comando exacto (salvo que el usuario haya dicho "commitea directo"). El push se ofrece y se ejecuta solo con confirmación afirmativa.
10. **Nada de lo que genera la skill se trackea.** Este es un flujo **personal**, no del equipo: `.specify/` y `.plans/` son locales. La skill **nunca** los stagea, comitea ni los agrega a un `.gitignore` compartido, y los excluye de todo `git add` y de las listas de archivos a commitear. El ignore local (p. ej. `.git/info/exclude`) lo gestiona el usuario por su cuenta; la skill no lo toca.

## Red flags — detente y reconsidera

Las reglas de arriba dicen *qué* hacer; esta sección frena los atajos que aparecen *en el momento*. Ley fundamental:

> **NINGÚN COMMIT CON UN AC EN ROJO O SIN VERIFICAR.** Lo verde es el paso `verify` con evidencia fresca, no una corazonada.

Si reconoces alguno de estos pensamientos, es señal de detente: vuelve al paso que estás por saltar y hazlo.

| Racionalización | Realidad |
|---|---|
| "Arranco el flujo sin leer el config" | Antes de cualquier paso operativo se lee `.specify/config.yml` y se **ecoan** los valores resueltos de `tracker`, `cross_review.mode`, `domain_context.mode`, `final_diff_review.mode` y `jira_approval.mode`. Saltarlo es cómo se pierden cross-review, co-exploración (`co_explore`), contexto de dominio, revisión final y `publish-spec` en silencio (se aplican los defaults sin avisar). |
| "Es trivial, salteo el gate y commiteo directo" | Trivial = 1 gate, no 0. La clasificación se **anuncia y se confirma siempre** (regla 2); no hay flujo con cero gates. |
| "Los tests pasan, seguro cumple los AC" | Tests verdes ≠ AC cumplidos. `verify` recorre `AC-1..N` con evidencia fresca **antes** de commitear (paso `verify`, regla 7). |
| "El subagente devolvió `STATUS: done`, marco la task `[x]`" | El reporte no es prueba. Validar `FILES` contra `git status` y revisar el diff antes de aceptar (modo subagent). |
| "Aprovecho y arreglo esto otro de paso, total es chico" | Si no mapea a un AC, se declara como `E-n` en `## Extras` antes de stagear — nada entra al commit sin rastro. |
| "Ya gasté 3 intentos en este fix, con uno más sale" | 3 fixes fallidos de la misma falla = problema de diseño: volver a `plan`/`specify`, no intentar un fix #4 (ver `implement`). |
| "Stageo todo lo que está dirty y después limpio" | Stage selectivo: solo `code_touched`; los archivos ajenos se confirman uno por uno (regla 8). |

## Adaptación al proyecto (portabilidad)

Antes de cualquier paso operativo, descubrir el entorno **una vez** por sesión y resumirlo al usuario. Orden de resolución para cada parámetro: `config.yml` → autodetección → preguntar.

**Checkpoint de inicio (no salteable).** El **primer** acto operativo de toda corrida es leer `.specify/config.yml` si existe y **devolverle al usuario en una línea los valores resueltos** de al menos `tracker`, `cross_review.mode`, `cross_review.co_explore.mode`, `domain_context.mode`, `final_diff_review.mode` y `jira_approval.mode`, **con qué implican**. Ej.: *"config: tracker jira · cross_review on · co_explore on → exploración paralela antes de la spec · domain_context auto → leer ADRs si existen · final_diff_review auto → revisión agregada en complex inline · jira_approval on → publico la spec en Jira tras aprobarla localmente"*. Ese eco es la prueba de que el config se leyó: sin él, es fácil aplicar los defaults (`cross_review` por complejidad, `domain_context: auto`, `final_diff_review: auto`, `jira_approval: off`) y perder cross-review, contexto de dominio, revisión final y `publish-spec` en silencio (ver red-flag "Arranco el flujo sin leer el config").

Si existe `.specify/config.yml`, leerlo primero. Esquema (todos los campos opcionales):

```yaml
stack: node                 # node | go | rust | python | java | dotnet | other
test_cmd: "npm test"        # comando de tests
build_cmd: "npm run build"  # comando de build (omitir si el stack no compila)
lint_cmd: "npm run lint"    # opcional
default_branch: main        # rama base
branch_format: "{type}/{ticket}-{slug}"
branch_prefix: ""           # opcional; reemplaza {type} (p. ej. "feature/"); vacío → prefijo semántico
commit_style: conventional  # conventional | plain
tracker: jira               # jira | github | gitlab | linear | none
test_scope_hint: "vitest run {name}"  # plantilla de COMANDO para acotar tests; {name} = archivo/patrón
cross_review: {mode: auto, execution: auto, co_explore: {mode: auto, deadline: 600}}  # segunda opinión + co-exploración; ver "Revisión cross-model" y "Co-exploración cross-model"
domain_context: {mode: auto, context_paths: [], adr_paths: []}  # lectura de contexto/ADRs; ver "Contexto de dominio"
final_diff_review: {mode: auto}  # revisión agregada de diff en cambios complex/high-risk inline
jira_approval: {mode: "off"}  # aprobación externa de la spec en Jira ("off"|"on", entre comillas: sin ellas YAML los parsea como booleanos; solo si tracker: jira); ver paso `publish-spec`
implement_mode: ask         # cómo ejecutar las tasks: ask (preguntar en el gate) | inline | subagent
```

Lo que no esté en `config.yml` se **autodetecta** por convención (detalle y comandos en `reference.md` → "Matriz de detección"):

| Parámetro | Cómo se descubre (resumen) |
|---|---|
| Stack + test/build | Archivo de manifiesto: `package.json` (scripts), `go.mod`, `Cargo.toml`, `pyproject.toml`/`pytest.ini`, `pom.xml`/`build.gradle`, `*.csproj`. |
| Rama base | `git symbolic-ref refs/remotes/origin/HEAD`; fallback `git remote show origin`. Nunca asumir `main`/`master`. |
| Host de Git | `git remote get-url origin` → github/gitlab/bitbucket/otro. Define cómo se detecta la rama remota y se referencian PRs. |
| Tracker | Patrón de clave `[A-Z][A-Z0-9]+-\d+` en el prompt + MCP/CLI disponibles (Jira/GitHub/GitLab/Linear). Si nada aplica → `none`, usar contexto del prompt. |
| Commit | **Inline, sin dependencias externas**: `type` desde `change_type`, scope = ticket de la rama, formato convencional en español. Con `commit_style: plain`, mensaje plano sin `type(scope)`. Detalle en `reference.md` → "Construcción del mensaje de commit". |

> **Descubrir por capacidad, no por nombre.** Los nombres de tools/MCP cambian entre entornos (Claude Code, Codex, etc.). Buscar por capacidad (tracker, navegador, búsqueda en código, host de Git) y, antes de fallar por "tool X no existe", listar las disponibles y buscar coincidencias. Solo entonces degradar o preguntar. Tabla completa en `reference.md`.

Si tras detectar quedan huecos (p. ej. no se infiere el comando de build), preguntarlos en una sola tanda y ofrecer guardarlos en `.specify/config.yml` para próximas corridas.

### Contexto de dominio (solo lectura)

`domain_context` agrega conocimiento de dominio o decisiones existentes al flujo sin convertir
`sdd-flow` en una skill de documentación. Se usa solo como **input de lectura**:

- `context_paths`: documentos de dominio, glosarios o guías funcionales.
- `adr_paths`: ADRs o decisiones técnicas ya existentes.

Resolución: override conversacional de la corrida > `domain_context` del `config.yml` > default
`auto` (leer documentos obvios si existen, como `CONTEXT.md`, `docs/adr/`, `docs/architecture*`,
sin inventar rutas). Si un path configurado no existe, avisar y seguir sin bloquear. En
`analyze`/`plan`, leer estos paths para usar nombres canónicos y decisiones vigentes; en
`co-explore` y `sdd-cross-review`, pasarlos como `context_paths` adicionales. **Nunca** crear,
editar ni "mantener" ADRs/docs versionados como parte de este campo: si hace falta documentar una
decisión nueva, pedir un flujo aparte o confirmación explícita.

## Clasificador de complejidad (escalado de gates)

Tras `gather-context`, clasificar el cambio, **anunciar la clasificación con su justificación** y dejar que el usuario la ajuste. La clasificación define cuántos gates y artefactos:

| Nivel | Señales típicas | Artefactos / gates | Clarify |
|---|---|---|---|
| **Trivial** | 1 archivo, sin lógica nueva (typo, copy, bump de versión, config simple). | Spec mínima embebida en `plan.md` + tasks inline. **1 gate**. | Se saltea. |
| **Normal** | Pocos archivos / un módulo, lógica conocida, requisitos claros. | `spec.md` + `plan.md` + `tasks.md` separado (las tasks se aprueban **en el gate del `plan`**, sin STOP extra). **2 gates**. | Solo si hay ambigüedad. |
| **Complejo** | Varios módulos/subsistemas, lógica nueva, integraciones, o ambigüedad real en requisitos. | `spec.md` + `plan.md` + `tasks.md` separados, con **gate de `tasks` propio**. **3 gates** + cross-artifact check. | **Obligatorio**. |

En la duda, subir un nivel: es más barato un gate de más que retrabajo.

> **Gates vs checkpoints.** El contador (trivial=1 / normal=2 / complejo=3) cuenta solo los **gates de artefactos SDD** (`specify`, `plan`, `tasks`): los puntos donde el flujo se detiene a aprobar un artefacto. **No** son gates de complejidad: los **checkpoints informativos** (confirmar el contexto en `gather-context`, confirmar el nombre de rama en `create-branch`), los **setup checkpoints** de `init` y `constitution`, ni los **gates operativos** que existen siempre (revisión manual, commit, push).

## Revisión cross-model (segunda opinión, opcional)

Antes de cada gate de artefacto (`specify`, `plan`, `tasks`), si está disponible la skill
**`sdd-cross-review`**, se puede correr una **segunda opinión de un modelo de otra familia que
el autor** (Codex cuando conduce Claude; Claude cuando conduce Codex) que
critica el artefacto en read-only antes de mostrártelo. **Augmenta el gate, no lo reemplaza:** la
crítica se presenta *junto* al artefacto en el mismo STOP; tú sigues siendo el árbitro final.

- **Dependencia blanda.** Esta capacidad es opcional: si `sdd-cross-review` **no está instalada**,
  omitir la revisión y seguir con el gate humano normal. sdd-flow funciona igual sin ella (no es
  como un MCP de tracker: es un extra de calidad). Detectarla por capacidad, igual que el resto.
- **Cuándo se activa** (precedencia: override de la corrida > `cross_review` de `config.yml` >
  default por complejidad): default `trivial` off, `normal` opt-in (off salvo pedido), `complex`
  on. En *normal* el gate combina plan+tasks: se revisan juntos en ese único STOP.
- **Cómo invocarla.** Con el **Skill tool** (`sdd-cross-review`; esa skill sí es invocable por el
  modelo). Pasarle `artifact_type`, `artifact_path`, los `context_paths` relevantes (al revisar
  `tasks`, también `spec`+`plan`; sumar los paths resueltos de `domain_context` y, con
  co-exploración corrida, sumar además los informes
  `co-explore/findings-<familia>.md` y, en el gate del plan,
  `co-explore/counter-plan-<familia>.md`, cuando existan — ver "Co-exploración cross-model"),
  `working_dir`, `complexity` y `execution` (de `cross_review.execution`, que se hereda como el
  resto de la config). Devuelve el artefacto (quizá revisado) + un resumen de la crítica + la ruta
  del `review-log.md` (queda en `.plans/<id>/review-log.md`, local y untracked como el resto).
- **Degradación (nunca bloquea el flujo).** Si no hay revisor (el modelo de la otra familia no
  está disponible), si la skill
  está instalada pero la invocación falla (p. ej. error del Skill tool), si falla en
  runtime, si vence el timeout/`poll_deadline` de la revisión (la skill garantiza un tope duro: ver
  su "Latencia y timeout"), o si `cross_review.mode: off` → avisar en una línea ("revisión
  cross-model no disponible — sigo con el gate humano") y continuar con el gate normal. Es la misma
  filosofía de la regla #6.

> Detalle del loop, el contrato con el revisor (Codex o Claude según quién conduzca) y el formato del log: en la propia
> `sdd-cross-review`. Acá sdd-flow solo decide **cuándo** invocarla y **presenta** su salida en el
> gate.

## Co-exploración cross-model (opcional)

Antes de escribir la spec (`explore`) y antes de escribir el plan (`counter-plan`), si está
disponible la skill **`co-explore`**, un modelo de otra familia que el autor (Codex cuando
conduce Claude; Claude cuando conduce Codex) explora el mismo código en background, read-only, y
devuelve un mapa independiente — sin ver nada de lo que el conductor ya pensó. El valor no es que
el revisor "ayude": es que produce un mapa independiente, y las divergencias entre los dos mapas
salen a la luz temprano (en los hallazgos), antes de que las decisiones de la spec/plan queden
tomadas. Es **ortogonal** a `cross_review.mode`: esta capacidad gobierna la exploración paralela
y el contra-enfoque; `cross_review.mode` gobierna las críticas en los gates de artefactos.

- **Dependencia blanda.** Igual que `sdd-cross-review`: si `co-explore` **no está instalada**,
  se omite y el flujo sigue con la exploración de siempre del conductor.
- **Cuándo se activa** (precedencia: override de la corrida > `cross_review.co_explore` de
  `config.yml` > default por complejidad): default `trivial` nunca, `normal` opt-in (off salvo
  pedido), `complex` on.
- **Momento 1 — `explore` (pre-spec).** Tras confirmar el contexto y la clasificación en
  `gather-context`: (1) armar el **paquete de contexto** (digest del ticket + prompt del usuario +
  complejidad + paths resueltos de `domain_context`). Si el prompt/ticket trae **URLs de reproducción** ("abre esta URL para ver el
  error") y hay tool de navegador, el conductor **reproduce antes de despachar** y suma al
  paquete un digest **observacional** de la evidencia (salida de consola, requests fallidos,
  pasos observados) — hechos, **sin hipótesis propias**, que contaminarían la independencia del
  explorador (que es headless: no puede navegar). Sin tool de navegador, degradación de la regla
  6: pedir capturas/pasos al usuario, o seguir sin reproducción avisando; (2) invocar
  `co-explore` (Skill tool) con `mode: explore`,
  `execution: background`; (3) hacer la **exploración propia** de siempre, sin leer nada del
  revisor, y escribir el propio `findings-<familia-conductor>.md` (mismo formato) antes de leer
  el del revisor; (4) **punto de encuentro:** recoger el informe si terminó (`READY`) o seguir
  sin él (`UNAVAILABLE`, aviso de una línea); (5) **síntesis**, siguiendo la guía de
  `co-explore` → "La síntesis (guía para la skill llamadora)" (no se duplica acá): produce
  `synthesis.md` con la tabla de convergencias/divergencias, el duelo de enfoques con su
  rationale, y las incógnitas fusionadas de ambos mapas (las que cambiarían el diseño alimentan
  `clarify`); (6) **checkpoint informativo condicional** (no es un gate SDD): solo si quedaron
  divergencias sin resolver o enfoques viables materialmente distintos, presentarlos y dejar
  decidir al usuario antes de escribir la spec — si los mapas convergen, se sigue directo a
  `specify` sin stop extra.
- **Momento 2 — `counter-plan` (pre-plan).** Con la spec aprobada (y ya posicionados en la rama
  feature), antes de escribir `plan.md`: invocar `co-explore` con `mode: counter-plan`
  (contexto: la spec aprobada + paths resueltos de `domain_context` + el propio `findings-<familia>.md` del revisor de la fase
  `explore`); contrastar el contra-enfoque devuelto con el propio en una adenda de
  `synthesis.md` (mismo criterio de la síntesis: méritos, no adopción automática) y escribir
  `plan.md` con esa síntesis a la vista.
- **Los artefactos no citan la co-exploración.** `spec.md` y `plan.md` se escriben con la
  síntesis a la vista pero redactados de forma autónoma: sin referencias a la co-exploración,
  a los informes del revisor, a `co-explore/` ni al vocabulario conductor/revisor (ver
  `co-explore` → "La síntesis", paso 5). La trazabilidad queda en `.plans/<id>/co-explore/`.
  El checkpoint informativo conversacional no está alcanzado por esta regla.
- **Efecto en `analyze`.** Con co-exploración corrida, este paso **no re-explora**: es un
  **refresco incremental** sobre el mapa ya construido — validar que sigue vigente sobre el HEAD
  real de la rama (archivos movidos, código cambiado desde entonces) y anotar los deltas.
- **Crítica informada.** En los gates de `specify` y `plan`, si la revisión cross-model está
  activa, pasar a `sdd-cross-review` los paths resueltos de `domain_context` y los informes de
  co-exploración como `context_paths` adicionales: `findings-<familia>.md` (y, en el gate del plan, también
  `co-explore/counter-plan-<familia>.md`). Si existe `co-explore/session.json`, mencionarlo para
  el resume oportunista del revisor.
- **Degradación (nunca bloquea).** Skill no instalada, informe `UNAVAILABLE`, o deadline vencido
  → avisar en una línea ("co-exploración no disponible — sigo con mi exploración") y seguir el
  flujo normal. Misma filosofía de la regla #6.

## Compatibilidad con Plan Mode / modos no mutantes

Si el entorno prohíbe mutaciones (Plan Mode, modo solo-lectura, etc.):

1. No crear rama, no escribir `.specify/` ni `.plans/`, no modificar código, no ejecutar `implement`, **ni `publish-spec`** (es una escritura externa a Jira: doblemente vedada en estos modos).
2. Ejecutar solo pasos read-only: detección de entorno, `gather-context`, `analyze` estático, lectura de tracker, búsqueda en código y una propuesta de spec **conversacional**.
3. Avisar explícitamente que el flujo real queda bloqueado por el modo, y que al salir se retoma desde escribir `spec.md` (y crear la rama si falta).
4. No presentar la propuesta conversacional como equivalente a los artefactos en disco, ni preguntar "¿implemento? sí/no" como si el flujo estuviera completo.

## Router de intención (alias coloquiales → pasos SDD)

Internamente los pasos se llaman como el ciclo SDD; el router acepta frases naturales como disparadores.

| El usuario dice (ej.) | Paso SDD |
|---|---|
| "empezar ticket X", pega clave del tracker + descripción, "nuevo feature" | ciclo completo desde `gather-context` (gates según complejidad) → **STOP en cada gate** |
| "/sdd-flow init", "configura el proyecto", "inicializa sdd", "crea el `.specify/`" | `init` |
| "principios del proyecto", "define el constitution" | `constitution` |
| "dame el contexto", "qué pide X" | `gather-context` |
| "qué hay que hacer", "arma la spec", "define el alcance" | `specify` → **GATE** |
| "aclaremos", "pregúntame lo que falte" | `clarify` |
| "sube/publica la spec al ticket", "crea la subtarea de spec", "manda la spec a revisión del PO/TL" | `publish-spec` → **GATE externo** (si `jira_approval` aplica) |
| "crea la rama", "branch para esto" | `create-branch` |
| "con prefijo de rama X", "prefijo de rama: X", "usa el prefijo X para la rama" | registra el **override de prefijo** de la corrida (reemplaza `{type}` en `create-branch`; ver "Paso `create-branch`") |
| "parte desde la rama X", "base: rama X", "esto depende de X", "corta desde X" (X = una rama, no la base habitual) | registra el **override de base** de la corrida (`create-branch` corta desde X en vez de `default_branch`, sin tocar el config; ver "Paso `create-branch`") |
| "sin cross-review", "salta la segunda opinión" / "con cross-review", "pide segunda opinión" | registra el **override de revisión cross-model** de la corrida (off/on; ver "Revisión cross-model") |
| "con co-exploración", "que Codex explore en paralelo" / "sin co-exploración" | registra el **override de co-exploración** de la corrida (on/off; ver "Co-exploración cross-model") |
| "sin aprobación de jira", "no subas la spec" / "con aprobación de jira", "sube la spec a revisión" | registra el **override de aprobación externa** de la corrida (off/on; ver `publish-spec`) |
| "implementa con subagentes (frescos)" / "implementa acá mismo", "inline" | registra el **override del modo de implementación** de la corrida (subagent/inline; ver `implement` → "Modo de ejecución") |
| "analiza esto", "reproduce el bug", "dónde toco" | `analyze` |
| "cómo lo hacemos", "arma el plan técnico" | `plan` → **GATE** |
| "desglosa en tareas", "arma las tasks" | `tasks` → **GATE** |
| "aprobado", "dale", "implementa", "vamos" (con tasks/plan aprobados en esta sesión) | `implement` — Vía A |
| `/sdd-flow implement <ruta-carpeta>`, "implementa `.plans/X/`" (sesión fresca) | `resume` → `implement` Vía B (bootstrap) |
| "qué flujos tengo", "lista los planes", "¿en qué quedé?", `/sdd-flow status` | `resume` (listar; `status` es alias, no estado paralelo) |
| "continuemos con `<id>`", "retoma el flujo a", "sigue `.plans/X/`" | `resume` (retomar el flujo nombrado) |
| `/sdd-flow doctor <id>`, "valida el plan", "revisa coherencia del flujo" | `doctor` (read-only; no arregla ni escribe) |
| "ya aprobaron la spec", "revisa si aprobaron", "fíjate las observaciones del ticket" | `resume` → "Gate de Jira" (detección de aprobación / observaciones) |
| "pausa esto", "lo dejo por ahora", "guarda y sigo después" | sub-paso `pause` (escribe `handoff.md`) |
| "verifica", "¿cumple lo pedido?" | `verify` |
| "push", "publica la rama" (commit ya hecho) | sub-paso `push` aislado |
| "crear PR", "abre el PR", "pull request" (rama ya pusheada) | paso `open-pr` de `implement` (opcional; ver "Paso común", paso 9) |
| "archiva `<id>`", "esto ya está probado, ciérralo" | sub-paso `archive` |

---

## Paso `init` (opcional, explícito, con wizard)

**Objetivo:** materializar `.specify/` de forma **deliberada** — crear/actualizar `config.yml` y `constitution.md` mediante un **wizard** de selección, partiendo de valores autodetectados. No se generan solos en el ciclo (que usa defaults conversacionales); se crean acá, a pedido.

1. Es un **setup checkpoint** (no un gate SDD): a pedido (`/sdd-flow init` o equivalente), una vez por repo. No cuenta en el escalado de complejidad.
2. **Leer la selección actual si existe.** Si ya hay `.specify/config.yml`, leerlo: sus valores son la **selección vigente** que el wizard mostrará **pre-seleccionada** — re-correr `init` no arranca de cero, muestra lo que está fijado hoy para mantener o cambiar. Respetar overrides puestos a mano.
3. **Detectar el entorno** (rutina de "Adaptación al proyecto"): stack, `test_cmd`/`build_cmd`/`lint_cmd`/`test_scope_hint`, rama base, host de Git y tracker. El valor **leído del config existente** (paso 2) o, si no hay, el **detectado**, es el default de cada campo; lo que no se infiera queda como hueco a preguntar, nunca inventado.
4. **Wizard de decisiones.** Si hay una herramienta de **selección interactiva** (p. ej. `AskUserQuestion` en Claude Code — descubrir por capacidad, no por nombre), presentar las opciones **con descripción**, marcando el valor **actual/detectado como recomendado** (etiqueta "(actual)"). Dos pantallas:
   - **Pantalla 1:** `tracker` (jira · github · gitlab · none) · `commit_style` (conventional · plain) · `branch_prefix` (semántico `feature`/`fix`/… · fijo `feature/`) · `implement_mode` (ask · inline · subagent).
   - **Pantalla 2:** `cross_review` (auto por complejidad · on · off) · `domain_context` (auto · on · off) · `final_diff_review` (auto · on · off) · `jira_approval` (off · on; solo si `tracker: jira`).
   - **Sin** herramienta de selección → **degradar** al modo conversacional: proponer los valores y confirmar (regla 6).
5. **Comandos y paths autodetectados.** `test_cmd`/`build_cmd`/`lint_cmd`/`test_scope_hint` y los `domain_context.context_paths`/`adr_paths` **no** van al wizard (son texto libre/listas, no elecciones): se autodetectan y se muestran en el preview final (paso 6), donde el usuario puede **editarlos**.
6. **Armar y mostrar** el contenido completo de ambos archivos antes de escribir:
   - `.specify/config.yml` — con las selecciones del wizard + comandos/paths detectados. Esquema en `reference.md` → "Esquema de `.specify/config.yml`". Al escribirlo, emitir `cross_review.mode`, `domain_context.mode`, `final_diff_review.mode` y `jira_approval.mode` con los valores `on`/`off` **entre comillas** (`"on"`/`"off"`): sin ellas YAML los parsea como booleanos.
   - `.specify/constitution.md` — desde `reference.md` → "Plantilla de constitution" (definición de *Done*, formato de AC, regla de trazabilidad, y un **puntero** a los principios de código del repo —`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`— si existen).
7. **STOP** — escribir ambos **solo tras confirmación**. Son locales y untracked (regla #10): nunca se trackean, comitean ni se agregan a un `.gitignore` compartido.
8. **Re-corrida:** si ya existían, no pisar a ciegas — el wizard mostró los valores vigentes pre-seleccionados; al confirmar, **fusionar** los cambios respetando lo que el usuario mantuvo. Si prefiere no fijar config, puede saltar `init`: el ciclo sigue con autodetección + defaults conversacionales (ver `constitution`).

## Paso `constitution`

**Objetivo:** asegurar que existen los principios de **proceso** que el flujo respeta. No duplica principios de código.

1. Es un **setup checkpoint** (no un gate SDD): ocurre una vez por repo y no cuenta en el escalado de complejidad. Si no existe `.specify/constitution.md`: armar el contenido desde la plantilla de `reference.md` → "Plantilla de constitution" (definición de *Done*, formato de AC, regla de trazabilidad, y un **puntero** a los principios de código del repo —`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`— si existen). En cambios *triviales*, o si el usuario prefiere no detenerse, usar **defaults conversacionales sin escribir el archivo** hasta que haga falta; en el resto, mostrarlo y crearlo solo tras confirmación. Nunca escribir el archivo sin permiso.
2. Si ya existe, leerlo y tratarlo como invariante para spec/plan/tasks/verify.
3. Este paso es ambiente: se ejecuta una vez y se reusa. No bloquea el flujo si el usuario prefiere defaults.

## Paso `gather-context`

**Objetivo:** consolidar lo que pide el ticket + lo que dijo el usuario en una descripción operable, y clasificar la complejidad.

1. Buscar una clave de tracker (`[A-Z][A-Z0-9]+-\d+`) en el último mensaje.
2. Si hay clave **y** el tracker detectado tiene MCP/CLI: traer el issue (resumen, tipo, descripción, prioridad, labels, estado, links). El flujo concreto por tracker —p. ej. el de Jira/Atlassian con `cloudId`— está en `reference.md` → "Flujo por tracker". Si no hay integración: pedir al usuario que pegue el resumen, o seguir solo con el prompt.
3. Si no hay clave: usar el prompt. Si es vago, preguntar lo mínimo: **(a)** tipo de cambio, **(b)** título corto, **(c)** problema/objetivo.
4. **Fusionar** tracker + prompt; en conflicto gana el prompt.
5. **Clasificar complejidad** (sección de arriba), anunciarla con justificación y confirmar el contexto en 5-8 bullets antes de avanzar.

## Paso `specify` → GATE

**Objetivo:** escribir el **QUÉ** y el **por qué**, con criterios de aceptación verificables — sin detalles de implementación.

1. Crear `.plans/<id>/` (POSIX: `mkdir -p`; PowerShell: `New-Item -ItemType Directory -Force`).
2. Escribir `spec.md` con la plantilla de `reference.md` → "Plantilla de spec". Mínimo: problema/objetivo, alcance (in/out), y **criterios de aceptación numerados `AC-1..N`** en formato verificable (Given/When/Then o checklist observable).
3. Para cambios *triviales*, la spec puede ser un bloque breve dentro de `plan.md` en lugar de archivo aparte.
4. **STOP** — si la **revisión cross-model** está activa para `spec` (ver "Revisión cross-model"), ejecutar `sdd-cross-review` sobre `spec.md` antes de presentar (sumar `domain_context` resuelto y, con co-exploración, `co-explore/findings-<familia>.md` como contexto — ver "Co-exploración cross-model"). Presentar la spec (con el resumen de crítica, si lo hubo) y pedir aprobación. No avanzar sin ella. Si el usuario corrige, actualizar y volver a ofrecer.

## Paso `clarify` (condicional)

Obligatorio en cambios *complejos*; en *normales* solo si hay ambigüedad; se saltea en *triviales*.

1. Hacer preguntas de cobertura, **una a una**, enfocadas en cerrar ambigüedades que cambiarían el diseño (no detalles cosméticos).
2. Registrar cada Q&A en la sección `## Clarifications` de `spec.md` (queda auditable, no solo en el chat).
3. Si una respuesta altera los criterios de aceptación, actualizar los `AC-n` y volver al gate de `specify`.

## Paso `publish-spec` (aprobación externa de la spec — Jira, opcional)

**Objetivo:** publicar la spec aprobada localmente en una **subtarea de Jira** para que el TL/PO la revisen y aprueben **antes** de implementar, y dejar el flujo en pausa hasta esa aprobación. Es un **gate externo y asíncrono**: aumenta el gate local de `specify`, no lo reemplaza.

**Cuándo se activa** (precedencia: override de la corrida > `jira_approval` de `config.yml` > default **off**). Requiere además: `tracker: jira`, que `<id>` sea una clave de ticket real (el **padre**), y un MCP/CLI de Atlassian con **capacidad de escritura**. Si falta cualquiera → el paso no aplica (degradación, abajo). Tampoco aplica en cambios **triviales** (no hay `spec.md` separada ni gate de `specify` que publicar): si `jira_approval` está `on` y el equipo requiere la aprobación externa, avisar y ofrecer reclasificar a *normal*. Corre **después** del gate local de `specify` (y de `clarify` si aplica, con la spec ya estable) y **antes** de `create-branch`: no se crea rama ni plan sobre una spec que el TL/PO aún no aprobaron.

1. **Construir el payload** de la subtarea (plantilla y reglas en `reference.md` → "Aprobación externa de la spec (Jira)"): título `SPEC: <título corto>`; descripción con **primero un resumen ejecutivo no técnico** (problema, objetivo, alcance, fuera de alcance, criterios de aceptación en lenguaje de negocio) y **debajo la definición técnica** (cuerpo de `spec.md`, prácticamente literal). **Sanitizar** (acotado: todo lo técnico —`AC-n`, métodos, código y paths de código fuente del proyecto— se publica sin abstraer): nunca publicar menciones a cross-review / co-exploración / segunda opinión / modelos, URLs o entornos locales o de prueba (`localhost`, `127.0.0.1`, hosts de desarrollo como `local.<proyecto>.dev:4200`, `file://`), ni artefactos/mecánica del flujo SDD (`.plans/`, `.specify/`, paths absolutos locales, archivos del propio flujo, `status`, prefijos de rama, comandos de test/build, nombres de fases del flujo). Guardar la copia exacta de lo que se va a publicar en `.plans/<id>/jira-spec.md`.
2. **STOP (write-safety).** Mostrar (1) el **recurso** exacto (proyecto + issue padre `<id>`) y (2) el **contenido** exacto a publicar, y pedir confirmación. Recién entonces crear la subtarea (`createJiraIssue` con `parent` + issuetype de subtarea; ver `reference.md` → "Flujo por tracker"). Misma disciplina para toda escritura posterior (actualizar descripción, comentar, transicionar): siempre recurso + contenido a la vista antes de ejecutar.
3. **Escribir `handoff.md`** con `gate_status: awaiting`, `parent_key`, `subtask_key` (la subtarea creada), `jira_subtask_url` (`<site_url>/browse/<subtask_key>`, con `<site_url>` = la URL del site Atlassian resuelta por el MCP —p. ej. vía `getAccessibleAtlassianResources`—, para que `open-pr` pueda linkear la spec), `cloud_id`, y el snapshot de `gather-context` (ver "`handoff.md` (retomado del flujo)"). Avisar que el flujo queda **en espera de aprobación** y cómo retomarlo (`resume` con `<id>`; o decir "ya aprobaron" / "revisa el ticket"). **No** seguir a `create-branch` hasta la aprobación.
4. **Al retomar**, la detección de aprobación y el loop de observaciones los maneja `resume` (ver `resume` → "Gate de Jira (esperando aprobación externa)").

**Degradación (regla 6, nunca bloquea).** Si `tracker != jira`, no hay clave de padre, el feature está `off`, o el MCP de Atlassian es solo-lectura / falla la escritura → avisar en una línea y, si igual quieres el gate, ofrecer que crees la subtarea a mano y pegues su clave (se registra en `handoff.md` y se sigue el mismo loop). Si nada de eso aplica, continuar el flujo normal sin gate externo.

## Paso `create-branch`

**Objetivo:** crear la rama de trabajo desde la rama base resuelta (por defecto la detectada/`default_branch`; opcionalmente otra rama, vía override de base de la corrida — útil para features dependientes), con la nomenclatura acordada. Se ejecuta una vez aprobado el **qué** (tras `specify`/`clarify`); en cambios *triviales* —sin spec separada— se hace al inicio, antes de `plan`.

1. Verificar que no haya **cambios en archivos versionados** pendientes: `git status --porcelain -- ':(exclude).plans' ':(exclude).specify'`. Los artefactos locales del flujo (`.plans/`, `.specify/`) y los generados que el repo ya ignora **no cuentan**: "limpio" significa sin código sin commitear, no sin estos artefactos (que `specify`/`constitution` pudieron crear antes). Si hay cambios de código, detener y avisar.
2. **Resolver la rama base** (`base_branch` efectiva) por precedencia: (a) **override de base de la corrida** si el usuario lo indicó (ver router → "override de base"; p. ej. una feature dependiente que corta desde otra rama en QA/revisión, no desde la base habitual) → (b) `default_branch` del `config.yml` → (c) rama base **detectada** (`git symbolic-ref refs/remotes/origin/HEAD`). El override **no** toca el `config.yml`: vale solo para esta corrida. Registrar la `base_branch` resuelta para el header del `plan.md` y el snapshot del `handoff.md`.
3. **Normalizar la rama base** y posicionarse en ella. La detección suele devolver `origin/<rama>` (un ref remoto): quitarle el prefijo `origin/` para obtener la **rama local** (`origin/main` → `main`). Luego: `git fetch origin` → `git checkout <rama-local>` → `git pull --ff-only origin <rama-local>`. **Con override de base**, la rama X puede ser **puramente local o estar adelantada del remoto** (típico de una feature aún en revisión): hacer el `git pull --ff-only` **solo si X tiene upstream** (`git rev-parse --abbrev-ref --symbolic-full-name @{u}` no falla); si no lo tiene, saltear el pull y cortar desde el HEAD local de X. Si la rama base no existe local ni remotamente, detener y avisar (no inventar una base). Nunca hacer `git checkout origin/<rama>` (deja *detached HEAD*) ni asumir `main`/`master`.
4. **Determinar el prefijo efectivo** (`{type}`), tomando el primer valor presente en este orden: (a) **override de la corrida** si el usuario lo indicó (ver router → "prefijo de rama"); (b) **`branch_prefix`** del `config.yml`; (c) **prefijo semántico** derivado del tipo de issue/contexto (mapeo en `reference.md` → "Mapeo tipo de cambio → prefijo"; para features es **siempre `feature`, nunca `feat`** — `feat` es solo para commits/`change_type`; ante la duda, preguntar). Normalizar el prefijo quitándole la barra final si la trae (`feature/` y `feature` dan lo mismo, porque el `/` ya está en `branch_format`). Si `branch_format` fue customizado sin `{type}`, `branch_prefix`/override no aplican: respetar el `branch_format` tal cual.
5. **Construir el nombre** con `branch_format` (default `{type}/{ticket}-{slug}`): `{ticket}` = clave del tracker (si no hay, se omite **junto con su separador**: `fix/cart-null-guard`, nunca `fix/-cart-null-guard`); `{slug}` = 2-5 palabras del título en kebab, sin acentos, `[a-z0-9-]`. Ejemplos: `feature/ABC-123-export-csv`, `fix/cart-null-guard` (sin ticket); con `branch_prefix: feature/` fijo, hasta un fix queda `feature/PROJ-9-null-cart`.
6. **Mostrar el nombre propuesto** y pedir confirmación; aceptar correcciones o un nombre exacto del usuario. Si hubo override de base, incluir en la propuesta la **rama base** (`corta desde <base_branch>`) para que quede explícito.
7. `git checkout -b <branch>`. Guardar `branch` y `base_branch` para el header del `plan.md` y los pasos siguientes.

## Paso `analyze`

**Objetivo:** entender el código lo suficiente para planear bien.

- **Contexto de dominio.** Leer los paths resueltos de `domain_context` antes de decidir nombres,
  alcance técnico o contratos. Usar ese contexto para adoptar términos canónicos, respetar ADRs
  vigentes y marcar conflictos como incógnitas; no escribir ni actualizar esos documentos.
- **Si es bug:** seguir un método de debugging sistemático (hipótesis → prueba → refutar). Si hay una skill de debugging sistemático disponible, usarla. Si es reproducible en navegador y hay tool de navegador, capturar consola/network; si no, pedir captura/pasos. El mismo método aplica si un test o un AC falla durante `implement`/`verify` (ver `implement`, pasos 3-4).
- **Si es feature/refactor:** mapear archivos/módulos/utilidades existentes a reutilizar. Preferir reúso sobre código nuevo.
- Localizar el código con búsqueda en el repo (subagentes de exploración si el entorno los soporta y el alcance lo amerita; si no, `grep`/`ripgrep`/`find` locales).

**Output:** hipótesis (bug) o lista de puntos de reúso (feature) con referencias `path:line`.

**Con co-exploración corrida** (ver "Co-exploración cross-model"), este paso es un refresco incremental del mapa, no una re-exploración.

## Paso `plan` → GATE

**Objetivo:** dejar el **CÓMO** técnico en `plan.md`, con header YAML para bootstrap.

1. Estando ya en la rama feature (creada en `create-branch`), obtener `base_commit` = `git rev-parse HEAD` y la fecha ISO-8601 actual. Si en `create-branch` se resolvió una `base_branch` **distinta de `default_branch`** (override de base), conservarla para el header (define el destino del PR); si coincide con `default_branch`, se omite del header.
2. Escribir `plan.md` con el header YAML obligatorio + secciones de enfoque, contexto de dominio aplicado (si hubo `domain_context`), archivos a tocar, tests/build y verificación. Plantilla en `reference.md` → "Plantilla de plan". **Sin placeholders:** nada de `TBD`, `TODO`, "agregar manejo de errores apropiado" o "etc." colgados — cada sección con contenido real (ruta, comando, enfoque). Si algo no se puede precisar todavía, falta `clarify`; no es un placeholder.
3. El header YAML es la fuente del bootstrap y del retomado (paso `resume`):

   ```yaml
   ---
   id: ABC-123
   branch: feature/ABC-123-slug-corto   # prefijo de rama: feature, nunca feat
   base_commit: <SHA del HEAD>
   # base_branch: feature/ABC-100-otra  # solo si se cortó de una rama distinta a default_branch (override de base); destino del PR
   change_type: feat        # feat | fix | refactor | chore | docs | test | perf (vocabulario de commits: acá sí feat)
   complexity: complex      # trivial | normal | complex
   status: planned          # ver "Ciclo de status" abajo
   created_at: 2026-01-01T12:00:00-03:00
   ---
   ```

   Al crear el `plan.md`, escribir `status: planned`.
4. **STOP** — si la **revisión cross-model** está activa (ver "Revisión cross-model"), ejecutar `sdd-cross-review` sobre `plan.md` con `spec` + `domain_context` resuelto como contexto (con co-exploración: sumar `co-explore/findings-<familia>.md` y `co-explore/counter-plan-<familia>.md` como contexto — ver "Co-exploración cross-model") antes de presentar (en *normal*, sobre plan + tasks juntos). Presentar el plan (con el resumen de crítica, si lo hubo) y pedir aprobación. En *trivial* este es el último gate antes de implementar (tasks inline en `## Tasks`). En *normal*, **antes del STOP se ejecuta el paso `tasks`** (se escribe `tasks.md`) y este gate presenta **plan + tasks juntos** (un solo STOP, sin gate extra). En *complejo*, el plan se aprueba acá y el gate de `tasks` es independiente y posterior (ver paso `tasks`). En todos, al aprobar el último gate aplicable, pasar `status` a `tasks-ready`. Si este es el **último gate antes de implementar** (*normal*) y el modo de implementación resuelto es `ask`, incluir en el **mismo STOP** la pregunta del modo: ¿implemento acá (inline) o despacho subagentes frescos por task? (ver `implement` → "Modo de ejecución"; sin gate extra; en *trivial* no se pregunta: default `inline`).

### Ciclo de `status` (estado persistido del flujo)

`status` vive en el header del `plan.md` y es la **fuente de verdad de en qué fase quedó el flujo**. La skill lo actualiza al cerrar cada paso, y `resume` lo lee para saber dónde retomar:

```
planned → tasks-ready → implementing → verified → committed → pushed → done
(open-pr opcional: pushed → pr-open → done)
```

- `planned` — `plan.md` escrito, con aprobación pendiente.
- `tasks-ready` — plan aprobado; en *normal*/*complejo*, tasks aprobadas. Listo para implementar.
- `implementing` — implementación en curso (ver tasks marcadas para el detalle fino).
- `verified` — todos los AC en verde (resultado persistido, ver `verify`).
- `committed` / `pushed` — commit hecho / rama publicada.
- `pr-open` — (opcional) PR creado por `open-pr`; la URL queda en `pr_url`. Solo aparece si se abrió el PR desde el flujo.
- `done` — confirmado por el usuario como probado y correcto; dispara `archive`.

Antes de que exista `plan.md` (fase `specify`/`clarify`, o el gate de Jira), no hay `status` en `plan.md`: la fase se infiere de los archivos presentes (`spec.md` sin `plan.md` → todavía en `specify`/`clarify`) y, si hubo una pausa, del frontmatter del `handoff.md` (`phase`/`gate_status`; ver "`handoff.md` (retomado del flujo)"). Una vez que existe `plan.md`, `status` manda.

## Paso `tasks` → GATE (propio en *complejo*; junto al plan en *normal*)

**Objetivo:** descomponer el plan en tareas atómicas, ordenadas, verificables y **autosuficientes** — ejecutables en una sesión fresca sin tener que re-deducir el diseño ni elegir otro enfoque. El modo `subagent` de `implement` **depende** de esta autosuficiencia: cada task debe poder ejecutarla un agente fresco que solo ve spec/plan/su task; si no podría, la task está mal escrita.

1. **Dónde se escriben** (según complejidad): en *normal* y *complejo*, en `tasks.md` separado; en *trivial*, inline en la sección `## Tasks` del `plan.md`. **Siempre anunciar la ruta exacta** donde quedaron ("Tasks en `.plans/<id>/tasks.md`" o "en `plan.md` → sección `## Tasks`"). Nunca dejar al usuario adivinando si hay tasks o dónde están.
2. **Formato detallado** (plantilla en `reference.md` → "Plantilla de tasks"): cada task lleva checkbox `- [ ]`, acción concreta, y los campos **Por qué** (qué AC habilita / intención), **Archivos** (rutas a tocar, con `path:line` de reúso identificado en `analyze`), **Pasos** (para cambios de comportamiento, recomendar el punto testeable o **Seam** + test que debería fallar primero + comandos acotados; para tareas mecánicas, pasos directos), **Verificar** (comando o paso manual ligado al AC), y la(s) referencia(s) `AC-n`. Los snippets de los Pasos son **ilustrativos** del enfoque —firma, estructura, casos a cubrir—, **no** la implementación final completa. Cuando una task crea o usa una interfaz (función, endpoint, contrato) que otra task necesita, agregar **Produce** / **Consume**: declarar la **firma exacta** en la task que la *produce* y referenciarla desde la que la *consume* (DRY: no repetir la firma en cada task). Es lo que vuelve la task autosuficiente para el modo `subagent`. Cada task sigue siendo **atómica** (un cambio coherente). En tasks puramente mecánicas (config, copy, wiring sin seam testeable) los Pasos pueden colapsarse a 1‑2 líneas y declarar que la evidencia vendrá de `verify`.
3. **Self-review antes del gate** (el conductor lo corre y reporta en una línea):
   - **Cobertura de spec** (cross-artifact check): cada `AC-n` tiene ≥1 task y ninguna task carece de AC. Reportar huérfanos antes del gate.
   - **Scan anti-placeholder:** ni plan ni tasks tienen `TBD`, `TODO`, "agregar X apropiado", "similar a la Task N" o "etc." colgados; cada paso con contenido real (ruta, comando, firma). Un hueco que no se puede precisar es señal de que falta `clarify`.
   - **Consistencia de interfaces:** lo declarado en **Produce** coincide exacto con quien lo **Consume** (mismo nombre, misma firma) — el desajuste rompe el modo subagent.
4. **STOP** — en *complejo* (gate propio), si la **revisión cross-model** está activa para `tasks` (ver "Revisión cross-model"), ejecutar `sdd-cross-review` sobre `tasks.md` con `spec`+`plan`+`domain_context` resuelto como contexto antes de presentar. Presentar las tasks (con el resumen de crítica, si lo hubo) y pedir aprobación. En *complejo* es un gate **propio** (STOP independiente tras el plan). En *normal* las tasks se presentan **junto al plan** en el gate de `plan` (sin STOP adicional; la revisión, si aplica, ya cubrió plan+tasks ahí). Al aprobarlas, pasar `status` a `tasks-ready`. En *complejo*, si el modo de implementación resuelto es `ask`, incluir en este **mismo STOP** la pregunta del modo: ¿inline o subagentes frescos por task? (ver `implement` → "Modo de ejecución"; sin gate extra).

## `handoff.md` (retomado del flujo)

Documento de **retomado** del flujo —"dónde quedé, qué decidí y cómo sigo"— en `.plans/<id>/handoff.md` (frontmatter + narrativa): todo el estado del flujo queda junto en `.plans/<id>/` —donde `resume` ya escanea—, sin partirlo en carpetas aparte ni acoplar `sdd-flow` a otra skill. Es local y untracked como el resto (regla #10).

**Se escribe/actualiza en dos situaciones:**
- **Sub-paso `pause`** — al dejar un flujo a medias para seguir después o en otra sesión (cualquier fase, no solo `implement`).
- **Paso `publish-spec`** — el gate de aprobación en Jira es una pausa esperando a un tercero; agrega los campos del gate (ver su paso).

**Estructura:** frontmatter YAML con los campos máquina + cuerpo narrativo legible. Plantilla completa en `reference.md` → "Plantilla de `handoff.md`".

```yaml
---
phase: awaiting-jira-approval   # specify | clarify | awaiting-jira-approval | implementing | ...
# snapshot de gather-context (presente mientras NO exista plan.md):
complexity: normal              # trivial | normal | complex
change_type: feat               # feat | fix | refactor | ...
branch_prefix: feature          # el {type} ya resuelto
slug: export-csv
base_branch: master             # rama base resuelta (con override de base, la rama de la que se corta)
overrides: { branch_prefix: null, base_branch: null, cross_review: null, implement_mode: null, jira_approval: null }
# campos del gate de Jira (solo si es una pausa por aprobación externa):
# gate_status: awaiting         # awaiting | changes-requested | approved
# parent_key: ABC-123 · subtask_key: ABC-145 · cloud_id: <uuid>
# jira_subtask_url: https://<tu-site>.atlassian.net/browse/ABC-145   # la usa `open-pr` para linkear la spec
---
```

### Precedencia con `plan.md` (sin doble fuente de verdad)
- **`plan.md` existe** → su `status` / `wip_commit` / marcas `[x]` son la **verdad operativa** (lo que `resume` ya usa hoy). `handoff.md` solo aporta la **narrativa** (estado, decisiones, próximos pasos) y los **overrides de la corrida** (que de otro modo no se persisten).
- **`plan.md` NO existe** (fase `specify`/`clarify`, o el gate de Jira) → el **frontmatter del `handoff.md`** lleva el snapshot operativo (complejidad, tipo de cambio, prefijo) y es la fuente de verdad de esa ventana pre-`plan`.

`handoff.md` **nunca contradice** a `plan.md`: lo complementa y cubre la ventana donde antes no había nada persistido (hoy, pausar en `specify`/`clarify` pierde la narrativa). Al retomar, `resume` lo lee respetando esta precedencia.

## Paso `resume` (retomar un flujo / cambiar de contexto)

Punto de entrada cuando vuelves a un flujo ya empezado — en una sesión nueva, o tras haber saltado a otra cosa. Funciona **aunque estés posicionado en otra rama**, porque `.plans/` es local y visible desde cualquier rama, y cada `plan.md` sabe a qué `branch` pertenece y en qué `status` quedó.

### Listar / elegir el flujo
1. Si el usuario nombró un flujo (`<id>` o ruta `.plans/<id>/`), usar ese. Si dijo algo genérico ("¿en qué quedé?", "qué flujos tengo"), **listar** los flujos activos (excluir `.plans/archived/`): para los que tienen `plan.md`, leer su header; para los **pre-`plan`** (solo `spec.md`/`handoff.md`), leer el `handoff.md` (`phase`/`gate_status`). Mostrar tabla `id · branch · estado · siguiente paso` —donde "estado" es el `status` del plan o, si no hay plan, la `phase`/`gate_status` del handoff (p. ej. "esperando aprobación Jira")—. Que el usuario elija.
2. Si `.plans/<id>/` tiene `spec.md` pero **no** `plan.md`, el flujo quedó pre-`plan`. **Leer `handoff.md` si existe** (narrativa + snapshot de `gather-context`: complejidad, tipo de cambio, prefijo, slug, rama base, overrides) — es lo que evita re-investigar el ticket o re-clasificar. Luego:
   - Si el `handoff.md` tiene **`gate_status: awaiting`** (o `changes-requested`) → el flujo está en el **gate de Jira**; ir a "Gate de Jira (esperando aprobación externa)" abajo.
   - Si no (pausa común en `specify`/`clarify`) → chequear si ya existe una rama del flujo (`git branch --list "*<id>*"`): si existe, la spec ya fue aprobada y `create-branch` ya corrió → confirmarlo con el usuario, posicionarse en esa rama (checkout seguro, como abajo) y retomar en `plan` (así `base_commit` se toma del HEAD correcto, no de la rama en la que estés posicionado). Si no hay rama, retomar desde `specify`/`clarify`, sin navegación de rama.

### Navegar a la rama correcta (checkout seguro)
3. Parsear el header del `plan.md` elegido: `id`, `branch`, `base_commit`, `complexity`, `status` (y `wip_commit` si está).
4. Si la rama actual != `branch` del header:
   - Antes de cambiar, exigir working tree **sin código sin commitear** en la rama actual: `git status --porcelain -- ':(exclude).plans' ':(exclude).specify'` vacío. Si hay cambios de código (p. ej. otro flujo a medias), **detener**: ofrecer commitearlos, el sub-paso `pause`, o `git stash` — nunca pisar ni arrastrar trabajo ajeno a otra rama.
   - Con el árbol limpio, `git checkout <branch>`. Los `.plans/`/`.specify/` untracked no bloquean el checkout ni se pierden.
   - Si `branch` no existe (fue borrada): avisar y ofrecer recrearla desde el commit base (`git checkout -b <branch> <base_commit>`).
5. Coherencia: `git merge-base --is-ancestor <base_commit> HEAD` (si no: avisar que la rama divergió y pedir confirmación). Si el header trae `wip_commit`, recuperar el trabajo pausado (ver `pause`).

### Saltar al paso según `status`
6. Leer `status` y retomar en el punto exacto, **confirmando el resumen extraído** antes de actuar:

   | `status` | Dónde retoma |
   |---|---|
   | `planned` | falta `tasks` (complejo) o aprobar el plan → seguir el gate pendiente |
   | `tasks-ready` | `implement` (Paso común) |
   | `implementing` | `implement`, continuando desde la primera task `[ ]` (y el WIP, si hay `wip_commit`) |
   | `verified` | AC ya en verde; falta commit → `implement` desde el gate de revisión manual |
   | `committed` | falta push → sub-paso `push` |
   | `pushed` | completo en disco; ofrecer `open-pr` (si no hay `pr_url`) o `archive` |
   | `pr-open` | PR ya creado (`pr_url` en el header); no re-ofrecer `open-pr` — ofrecer `archive` si lo das por probado |
   | `done` | ya cerrado; si sigue fuera de `archived/`, ofrecer archivarlo |

   Al retomar en `implement` (`tasks-ready`/`implementing`), **re-resolver el modo de ejecución** (override > `implement_mode` > preguntar; ver `implement` → "Modo de ejecución"). Las tasks ya marcadas `[x]` no se repiten en ningún modo.

### Sub-paso `status` (alias de listado)

`/sdd-flow status` no introduce un estado nuevo: es un alias read-only de `resume` en modo listar.
Muestra los mismos datos (`id · branch · estado · siguiente paso`) y, si se pasa un `<id>`, resume
solo ese flujo. La fuente de verdad sigue siendo `plan.md` (`status` + marcas `[x]`) o
`handoff.md` en la ventana pre-`plan`.

### Sub-paso `doctor` (diagnóstico read-only)

**Objetivo:** validar la coherencia de un flujo sin arreglar nada ni escribir archivos. Aplica a
`/sdd-flow doctor <id>` o cuando el usuario pida "valida/revisa coherencia del flujo".

1. Resolver el flujo igual que `resume`: si hay `plan.md`, leer su header; si no, leer
   `handoff.md`/`spec.md`.
2. Ejecutar los mismos checks del self-review de `tasks`: cobertura `AC-n` ↔ tasks, tasks sin AC,
   anti-placeholder y consistencia exacta `Produce`/`Consume`.
3. Validar bootstrap: `branch` del header existe, `base_commit` es ancestro de `HEAD` si la rama
   está disponible, y `base_branch`/`default_branch` no dejan el flujo en detached HEAD.
4. Validar `## Verify`: los AC salen de `spec.md` o de `## Spec` embebido en `plan.md`; si el
   flujo tiene commits o cambios posteriores a la fecha/evidencia de `## Verify`, marcar
   **verify stale**. No re-verifica: solo detecta que la evidencia ya no es fresca.
5. Clasificar ruido del working tree: `.plans/`/`.specify/` son locales; generados/cache ignorados
   no bloquean; archivos de código dirty fuera de `code_touched` se reportan como ajenos. Si hay
   `.plans/<id>/work/`, tratarlo como scratch/auditoría, nunca como fuente de progreso.
6. Reportar `OK` / `WARN` / `FAIL` con evidencia concreta (`path:line`, comando leído, estado de
   git). **No** crear ramas, no editar artefactos, no marcar tasks, no limpiar archivos.

### Gate de Jira (esperando aprobación externa)

Cuando `handoff.md` tiene `gate_status: awaiting`/`changes-requested`, el flujo está parado esperando que el TL/PO aprueben la subtarea `SPEC: …`. Confirmar el resumen del `handoff.md` (objetivo, complejidad, subtarea) y resolver según lo que diga el usuario:

- **"ya aprobaron"** → confiar: poner `gate_status: approved` en `handoff.md` y seguir a `create-branch` usando el `branch_prefix`/`slug`/`base_branch` del snapshot.
- **"revisa el ticket" o nada** → leer la subtarea por MCP (estado + comentarios nuevos desde la publicación):
  - **Hay observaciones** (comentarios pidiendo cambios) → ajustar la `spec.md` localmente; **actualizar la descripción de la subtarea** con la spec corregida (sanitizada) **+ un comentario consolidado que @menciona al/los autor(es) de las observaciones** (un bullet por observación; ver `reference.md` → "Comentario de ajuste") resumiendo qué cambió y que vuelve a revisión (cada escritura con el STOP de write-safety del paso `publish-spec`); dejar `gate_status: awaiting` y volver a esperar.
  - **Aprobada** (la señal de `jira_approval.approval_signal` —un estado de Jira— o, si es `ask`, confirmándolo con el usuario) → `gate_status: approved` y seguir a `create-branch`.

Al aprobar, el flujo sigue normal: `create-branch` → `analyze` → `plan` (recién ahí se crea `plan.md`, sembrando `complexity`/`change_type` desde el snapshot; opcional `jira_subtask: <subtask_key>` + `jira_subtask_url: <url>` en el header para trazabilidad —los usa `open-pr` para linkear la spec en el PR). El análisis del código (`analyze`) corre fresco a propósito: va **después** de la aprobación.

### Sub-paso `pause` (dejar un flujo a medias de forma segura)
Aplica en **cualquier fase** del flujo, no solo `implement`. Al pausar:

1. **Escribir/actualizar `handoff.md`** (ver "`handoff.md` (retomado del flujo)"): estado actual, próximo paso, decisiones/criterio asumido y —si `plan.md` aún no existe— el snapshot de `gather-context` (complejidad, tipo de cambio, prefijo, slug, rama base, overrides de la corrida). Es lo que permite retomar en una sesión nueva sin re-investigar el ticket.
2. **Si hay código sin commitear** en la rama del flujo (típicamente en `implement`): **WIP commit en la propia rama** (no `git stash`: el stash es global y se confunde/pierde entre flujos; un commit viaja con su rama): stagear solo `code_touched` y `git commit -m "wip(<id>): pausa sdd-flow"`. Este WIP es **inline a propósito** (no usa `/commit`): es plumbing mecánico y descartable que `resume` deshace con `git reset`, no un commit de contenido. Registrar en el header del `plan.md`: `status: implementing` + `wip_commit: <sha>`. Si además quedan archivos **ajenos** dirty (fuera de `code_touched`), avisarlo: no entran al WIP y quedan sueltos en el working tree — un checkout posterior puede arrastrarlos. (En fases sin `plan.md` ni código —`specify`/`clarify`, gate de Jira— este paso no aplica: alcanza con el `handoff.md`.)
3. Avisar que quedó pausado y cómo retomarlo (`resume` con el `<id>`). Al retomar, si hubo WIP commit, `resume` lo deshace dejando los cambios en el working tree **sin** stage (`git reset <wip_commit>^`, reset mixed — así el staging selectivo del Paso común sigue valiendo), **reconstruye `code_touched`** desde los archivos del WIP (`git show --name-only --pretty=format: <wip_commit>` — el set en memoria no sobrevive a la sesión) y limpia `wip_commit` del header. **Guard previo:** solo resetear si `git rev-parse HEAD` == `wip_commit`; si no coinciden (hubo commits posteriores al WIP), no tocar la historia — avisar y dejar que el usuario decida cómo integrar el WIP.

## Paso `implement`

### Vía A — sesión actual
El usuario aprobó el último gate activo. Ir al "Paso común".

### Vía B — sesión fresca / bootstrap
Disparador: `/sdd-flow implement <ruta-carpeta>` (p. ej. `.plans/ABC-123/`), o llegada desde `resume` con `status` `tasks-ready`/`implementing`. La carga de contexto, la navegación a la rama y la validación de coherencia git las realiza el paso `resume` (arriba); además, cargar la spec y las tasks:

1. Leer `plan.md` (**obligatorio**: contiene el header YAML). Leer `spec.md` y `tasks.md` **solo si existen**; si no, tomar la spec y/o las tasks de las secciones embebidas `## Spec` / `## Tasks` del propio `plan.md`. La `complexity` del header indica qué esperar: `trivial` → todo embebido en `plan.md`; `normal` → `spec.md` + `tasks.md` separados; `complex` → `spec.md` + `tasks.md` separados (con gate de tasks propio).
2. Confirmar el resumen extraído (incluido el `status` y las tasks pendientes) antes de avanzar al "Paso común".

### Modo de ejecución (`inline` | `subagent`)

Ortogonal a las Vías A/B: se llegue por la sesión actual o por bootstrap, las tasks se ejecutan en uno de dos modos.

- **`inline`** — la propia sesión implementa cada task (el comportamiento de siempre). El contexto acumulado ayuda, pero arrastra el ruido de specify/plan/cross-review.
- **`subagent`** — cada task la implementa un **agente fresco** que solo lee los artefactos (spec/plan/su task), con contexto limpio. El conductor revisa entre tasks y conserva todos los STOPs.

Resolución (misma precedencia que el resto de overrides SDD): **override conversacional de la corrida** ("implementa con subagentes" / "implementa acá") > **`implement_mode`** del `config.yml` > default `ask` (preguntar en el último gate antes de implementar, dentro del mismo STOP — nunca un gate extra). Excepción: en *trivial* el default efectivo es `inline` sin pregunta (1-2 tasks mecánicas no ameritan despacho); el override conversacional sigue valiendo. Si el entorno **no tiene capacidad** de despachar agentes frescos (descubrirla por capacidad, no por nombre — ver `reference.md` → "Prompt del subagente por task"), avisar en una línea y seguir `inline` (degradación estándar, regla 6).

### Paso común — Implementación

1. **Tracking de archivos (por capacidad, no por nombre de tool).** Alimentado por **cualquier** herramienta o comando que cree/modifique/borre archivos (las tools de edición del entorno —cambian entre Claude Code, Codex, etc.— o `mv`/`rm`/`cp` en shell), mantener tres sets de rutas:
   - `code_touched` — código/producto que tocó la skill (candidatos a commit).
   - `sdd_local` — `.plans/`, `.specify/` (locales, nunca se commitean).
   - `generated` — artefactos de tests/build (caches, `dist/`, `__pycache__/`, …; nunca se commitean).
2. **Aplicar cambios** task por task según el **modo de ejecución** resuelto (ver arriba). Al iniciar este paso, poner `status: implementing` en el header del `plan.md`. En ambos modos: marcar cada task `- [x]` al completarla (es el detalle fino del progreso que `resume` usa para saber por dónde seguir) y reutilizar lo identificado en `analyze`.
   - **Modo `inline`:** la propia sesión implementa cada task. Para tasks de comportamiento con un
     seam testeable, seguir los Pasos roja-verde propuestos en `tasks.md` (test que debería fallar
     → implementación mínima → test verde). Si la task es mecánica o no tiene seam razonable, no
     inflar el plan: la garantía vive en `verify`, que exige evidencia fresca y, cuando haya test
     ligado al AC, test con dientes vía revert-to-confirm.
   - **Modo `subagent`** (loop por task, **siempre secuencial** — un solo working tree; despachar en paralelo garantiza colisiones):
     0. **Pre-flight scan** (una vez, antes de la primera task): revisar el conjunto de tasks buscando conflictos entre sí o con constraints globales (dos tasks tocando el mismo archivo de forma incompatible, orden de `Produce`/`Consume` mal resuelto). Si aparece algo, presentarlo al usuario en **una sola tanda** (batched) antes de arrancar — no interrumpir el loop a mitad de camino.
     1. Por cada task `[ ]` en orden, despachar un **agente fresco** con la plantilla de `reference.md` → "Prompt del subagente por task" (ahí también: cómo despachar según el entorno). El agente implementa **solo esa task**, corre su comando de Verificar, y devuelve el reporte estructurado (`STATUS`/`FILES`/`VERIFY`/`NOTES`). No commitea ni toca `.plans/`/`.specify/`.
     2. Al volver: validar `FILES` contra `git status --porcelain` y sumarlos a `code_touched` (regla 8). **Revisar el diff de la task** antes de aceptarlo (disciplina de `receiving-code-review`). Si el entorno puede despachar otro agente fresco, hacerlo con un **reviewer por-task** (plantilla en `reference.md` → "Prompt del subagente reviewer"): recibe el diff + spec + plan + la task y reporta **spec ✅** (¿cumple los AC que la task habilita?) y **calidad ✅** (¿sin code smells, sigue los patrones del repo?). **Ambos** verdes para marcar la task `- [x]`. Si el reviewer marca ⚠️ "no verificable desde el diff" (un requisito que vive en código no tocado), **no bloquea**: lo resuelve el conductor antes de marcar. Sin capacidad de despachar el reviewer → caer a la **revisión liviana del diff** por el propio conductor, con un aviso de una línea (degradación, regla 6).
     3. Si `STATUS: failed`, o el reviewer reprueba spec/calidad: **máximo 1 reintento**, re-despachando al implementer con el feedback concreto de qué corregir. Si vuelve a fallar, parar y escalar al usuario con el estado — nunca un loop abierto.
     4. Red de seguridad: si el reporte falta o no parsea, clasificar por `git status` + diff; las marcas `[x]` y el `status` del header siguen siendo la fuente de verdad del progreso. **Ante una compactación de contexto**, confiar en esa fuente persistida (`status` + marcas `[x]` + `git log`), no en la memoria de la sesión.
     5. Scratch opcional: si el reporte del implementer/reviewer aporta valor para auditoría o retomado, guardarlo en `.plans/<id>/work/Tn-*.md`. Ese directorio es **scratch local**: no se commitea, no reemplaza `tasks.md`, no contiene `progress.md`, y nunca decide qué task está completa.
   Los pasos 3-10 de abajo (tests+build completos, `verify` de AC, revisión manual, staging, commit, push, PR opcional) los ejecuta **siempre el conductor en esta sesión**, en ambos modos: los STOPs no funcionan dentro de un subagente.
3. **Tests + build** con los comandos detectados/configurados (+ `lint_cmd` si está configurado). Acotar tests al código tocado si el runner lo permite (`test_scope_hint`). Si algo falla: **no commitear**; antes de parchar, aplicar **debugging sistemático** — formular **una** hipótesis ("creo que la causa raíz es X porque Y") y probarla mínimamente, en vez de prueba y error (skill de debugging sistemático si está disponible, o el método inline; ver `analyze` y `reference.md` → "Matriz de detección"). Mostrar el error + la hipótesis, aplicar el fix y volver al paso 2. **Tope: 3 fixes fallidos de la misma falla = problema de diseño** — parar y volver a `plan`/`specify`, no intentar un fix #4.
4. **`verify` de los AC** (ver paso `verify`): recorrer `AC-1..N` con la gate function y marcar cumplido/no cumplido con evidencia fresca. Si alguno falla: **no commitear**, reportar y volver al paso 2 (con el mismo debugging sistemático del paso 3; mismo tope de 3 intentos), o a `plan`/`specify` si el gap es de diseño. Solo se commitea con **todos los AC en verde**; cuando lo estén, `verify` persiste el resultado y deja `status: verified`. Verificar antes del commit evita commits/push que después no cumplen lo pedido.
5. **Gate de revisión manual (STOP):** con tests+build OK y AC verificados, ofrecer revisar (levantar la app, `git diff`, repasar la sección Verification del plan) antes de commitear. Salteable con "commitea directo". Si `final_diff_review.mode` está `on`, o está `auto` y el flujo es `complex`/high-risk ejecutado `inline`, ofrecer en este mismo gate una revisión agregada del diff completo contra spec + estándares del repo: usar un reviewer fresco por capacidad (mismo contrato que el reviewer por-task: **SPEC** y **QUALITY**) o, sin esa capacidad, revisión liviana del conductor. Es una revisión de diff **same-model/de capacidad**, no conformance cross-model; el gate cross-model pre-commit sigue diferido salvo dolor concreto.
6. **Clasificar el working tree antes de stagear.** `git status --porcelain` y repartir cada ruta dirty:
   - **SDD local** (`.plans/`, `.specify/`) y **generados/cache** (lo que el repo ya ignora, más caches obvios como `dist/`, `__pycache__/`, `coverage/`): **nunca** se stagean ni cuentan como "código sin commitear". La fuente de verdad de qué es generado es el `.gitignore` del repo.
   - **Código:** `propios = code_touched ∩ (código dirty)`; `ajenos = (código dirty) − code_touched`. Sin ajenos → stagear `propios`. Con ajenos → listar ambos grupos y pedir elección (solo míos / incluir todos / cancelar). Nunca stagear ajenos sin confirmación.
   - **Extras (cambios sin AC).** Todo cambio que se decide incluir en el commit y **no mapea a ningún AC** se registra como `E-n` en la sección `## Extras (fuera de AC)` del `plan.md` antes de stagear — para que nada entre sin rastro (ver "Extras" abajo). Aplica a los `ajenos` que se eligen incluir y a cualquier ajuste oportunista que el conductor sepa que no corresponde a un AC (incluso dentro de un archivo `propio`). **No** aplica a corregir lo recién escrito por la skill (typo/ajuste dentro del código del feature): eso es parte de implementar bien el AC.
7. **Commit (transparente, confirmado, inline).** Con el staging armado (paso 6: solo `code_touched`; nunca `git add` adicional), **construir el mensaje inline** —sin depender de ninguna skill externa— siguiendo `reference.md` → "Construcción del mensaje de commit" (`type` desde `change_type`; scope = ticket resuelto del `id`/rama, u omitido si no hay; subject imperativo **en español** < 72 chars; **sin firmas ni `Co-Authored-By`**; con `commit_style: plain`, mensaje plano sin `type(scope)`). **Mostrar antes de ejecutar**: archivos staged + mensaje exacto + comando exacto. Si el usuario ya dijo "commitea directo" en el paso 5, proceder sin re-preguntar; si no, esperar su OK. **Ejecutar con heredoc** para que un body multilínea sobreviva intacto (plantilla en `reference.md`). Si hay `E-n` declarados en `## Extras`, listarlos como bullets en el **body** (el commit sigue siendo atómico del flujo). **Si el commit falla** (p. ej. hook de pre-commit): mostrar el error y **parar** — nunca reintentar con `--no-verify` salvo pedido explícito. Hecho el commit, poner `status: committed`.
8. **Push opcional (STOP):** detectar si la rama existe en remoto (host de Git si hay tool, o `git ls-remote --heads origin <branch>`). Ofrecer `git push -u origin <branch>` (primera vez) o `git push origin <branch>`. Ejecutar solo con confirmación afirmativa; tras el push, poner `status: pushed`.
9. **PR opcional (STOP).** Tras el push, ofrecer crear el PR hacia la **rama base del flujo**: `base_branch` del header si está (feature dependiente cortada de otra rama), si no `default_branch` (detalle en `reference.md` → "Apertura de PR"). Si el destino es un `base_branch` que aún no se mergeó, avisarlo en el preview (el PR queda **stacked** sobre esa rama; conviene mergear la base primero o re-apuntar a `default_branch` cuando la base entre): probar el MCP de Bitbucket (sin él, degradar a PR manual — regla 6); evitar duplicados (si ya hay un PR abierto para la rama, ofrecer actualizarlo); redactar una descripción **compacta** desde `spec.md`/`plan.md` (`## Ticket` con link a la subtarea SPEC si `jira_subtask_url` está en el header; `## Problema` ≤2 bullets; `## Solución` ≤3; `## Criterios de aceptación` = `AC-n` como checklist observable, que hacen de plan de pruebas); cargar reviewers por defecto de `.specify/reviewers.json` del repo (si existe; excluir al autor; sin archivo → PR sin reviewers por defecto, ofrecer indicarlos). **Preview + confirmación obligatoria** antes de `bb_post`. Crear, reportar URL/ID/reviewers, guardar `pr_url` en el header y poner `status: pr-open`. **Nunca** aprobar ni mergear — solo crear. Salteable.
10. **Reporte final** (abajo). Ofrecer el sub-paso `archive`: si el usuario confirma que está probado y correcto, cerrar el flujo (ver `archive`).

### Extras (cambios fuera de AC)

Durante la implementación es normal toparse con un typo o un ajuste oportunista que no estaba planificado y querer aprovecharlo en el mismo commit. La regla de la skill es que **todo lo que entra al commit o mapea a un AC, o queda declarado como Extra** — nada entra sin rastro. Distinción:

- **Corregir lo que la skill acaba de escribir** (typo/ajuste dentro del código del feature, en `code_touched`): es parte de implementar bien el AC. **No** se declara.
- **Cambio sin relación con ningún AC** (otro archivo, o un hunk no relacionado dentro de un archivo `propio`): se declara como `E-n` en `## Extras (fuera de AC)` del `plan.md` (`- E1 — <descripción> · path:line`) antes de stagear, y se refleja como bullet en el body del commit (paso 7).

La detección es por **disciplina del conductor** al revisar el diff (paso 5/6), no automática a nivel hunk. Si un Extra crece o se vuelve riesgoso, tratarlo como cambio aparte: su propio flujo/commit, no colgarlo de este. `## Extras` es local (vive en `.plans/`, nunca se commitea); su único efecto en el repo es el body del commit.

> **Opción futura (no implementada): conformance cross-model.** Un gate pre-commit donde un modelo de otra familia (vía `sdd-cross-review`) verifica el diff contra el plan/AC — cazando AC sin implementar y *drift* a nivel hunk, usando `## Extras` como allowlist. Se descartó para el caso común (el paso `verify` + la revisión manual del diff ya lo cubren; agrega minutos de latencia y mantenimiento). Reconsiderar solo ante el dolor concreto de drift no detectado en cambios grandes/multi-repo (`sdd-orchestrator`).

## Paso `verify`

**Objetivo:** comprobar que lo implementado cumple la spec — con evidencia fresca, no con una corazonada.

1. **Fuente de los AC:** `spec.md` si existe; si no (triviales con spec embebida), la sección `## Spec` del `plan.md`.
2. **Gate function por cada AC** — saltarse un paso es afirmar sin verificar:
   - **IDENTIFICAR** — qué comando u observación prueba *este* AC.
   - **CORRER** — ejecutarlo *fresco y completo* (no reusar una salida anterior ni "los tests de recién").
   - **LEER** — la salida entera + el exit code; contar fallos.
   - **VERIFICAR** — que esa salida confirma el AC puntual (no que "compila" o "pasan los tests" en general).
   - Recién entonces marcar el AC **cumplido / no cumplido**, con la evidencia (salida observada / test que lo cubre / paso manual).

   | Afirmación | Requiere | No alcanza |
   |---|---|---|
   | "AC-n cumplido" | salida del comando/observación que prueba *ese* AC | "los tests pasan", "el código cambió", "debería andar" |
   | "tests en verde" | salida fresca del runner: 0 fallos | una corrida previa, el linter en verde |
   | "build OK" | comando de build: exit 0 | "los logs se ven bien" |
3. **Revert-to-confirm para AC de comportamiento con test.** Un test que pasa no prueba que
   discrimine el comportamiento. Cuando un `AC-n` de comportamiento está cubierto por un test:
   con el test en verde, revertir **solo el hunk de implementación que habilita ese AC** → el test
   **debe fallar** → restaurar el hunk → vuelve a verde. Si al revertir el test sigue pasando, el
   test no tiene dientes: rehacerlo o cambiar la evidencia del AC. En `change_type: fix`, este
   paso es obligatorio para el test de regresión; en features/refactors aplica a los AC testeados.
   Excepción: tasks mecánicas, copy/config o wiring sin seam razonable; documentar la excepción y
   usar la observación/comando de `verify` como evidencia. Comandos POSIX/PowerShell en
   `reference.md` → "Plantilla de `## Verify`".
4. Contrastar contra la definición de *Done* del constitution.
5. **Persistir el resultado** en una sección `## Verify` del `plan.md` (tabla `AC-n · cumplido/no · evidencia · fecha`; cuando aplique, anotar `revert → FAIL / restore → PASS` como evidencia del AC). Así sobrevive a la sesión: al retomar con `status: verified` no se re-verifica de gusto, y queda auditable. Plantilla en `reference.md`.
6. Si **todos** los AC se cumplen: poner `status: verified`. Si alguno falla: poner `status: implementing` (también si el flujo venía de `verified` — un AC en rojo desactualiza esa marca), reportarlo y volver a `implement` (o a `plan`/`specify` si el gap es de diseño).

## Sub-paso `archive` (cerrar un flujo terminado)

Solo cuando el usuario confirma explícitamente que el cambio está **probado y correcto como se espera** — esta decisión es del usuario, nunca automática. Requiere que el flujo esté completo en disco (`status` en `committed`, `pushed` o `pr-open`).

1. Poner `status: done` en el header del `plan.md`.
2. Mover la carpeta del flujo a archivados (POSIX: `mkdir -p .plans/archived` y `mv .plans/<id> .plans/archived/<id>`; PowerShell: `New-Item -ItemType Directory -Force .plans/archived` y `Move-Item .plans/<id> .plans/archived/<id>`). Movimiento plano, **no** `git mv`: sigue siendo local, no se trackea ni commitea — regla #10.
3. Confirmar que quedó en `.plans/archived/<id>/` y que sale del listado de flujos activos de `resume`.

## Reporte final

- Clasificación de complejidad y gates recorridos.
- Archivos commiteados (propios vs otros, si aplica).
- Resultado de tests + build.
- Tabla `AC-n → cumplido/no`.
- SHA del commit y estado del push.
- `status` final del flujo (y si quedó archivado).

## Referencias internas

- `reference.md` — matriz de detección por stack/host/tracker, esquema de `config.yml`, plantillas de `constitution.md`/`spec.md`/`plan.md`/`tasks.md`, y ejemplos.
- `README.md` — qué es, cuándo usarla, instalación en otro proyecto y ejemplos de uso.
