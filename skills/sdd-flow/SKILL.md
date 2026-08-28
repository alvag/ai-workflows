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
   │  ├─ bitacora.md      # constancia append-only de los pasos del contrato
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

## Corridas delegadas en vuelo

Antes del primer despacho, comprobar en la raíz efectiva si existe
`.cross-model/conmutacion.lock`. Si existe, detener la corrida antes de crear o escribir el sobre e
informar `conmutación en curso`. No inferir que está huérfano por su PID ni borrarlo automáticamente.

Todo agente que este flujo despacha nace con su **sobre** en `.cross-model/active/<skill>/`, escrito
**antes** del despacho, y mientras el sobre siga activo cada turno del conductor cierra informando su
estado. Los puntos de despacho propios son dos:

- los subagentes de exploración de `analyze`, cuando el entorno los soporta y el alcance lo amerita
- el reviewer de la **revisión final de diff**, dentro del gate de revisión manual

Campos del sobre, transiciones, sonda por turno, cosecha y condiciones del retiro:
`skills/cross-review/corridas-en-vuelo.md`, la **sede única** del contrato. Es la regla normativa; acá solo se enumera dónde
aplica. Invocar `co-explore`, `cross-review` o los modos `cross` y `workers` (que delegan en
`cross-implement`) **no** suma puntos propios: cada una de esas skills escribe el sobre de su propia corrida.

## Red flags — detente y reconsidera

Las reglas de arriba dicen *qué* hacer; esta sección frena los atajos que aparecen *en el momento*. Ley fundamental:

> **NINGÚN COMMIT CON UN AC EN ROJO O SIN VERIFICAR.** Lo verde es el paso `verify` con evidencia fresca, no una corazonada.

Si reconoces alguno de estos pensamientos, es señal de detente: vuelve al paso que estás por saltar y hazlo.

| Racionalización | Realidad |
|---|---|
| "Arranco el flujo sin leer el config" | Antes de cualquier paso operativo se lee `.specify/config.yml` y se **ecoan** los valores resueltos de `tracker`, `cross_review.mode`, `domain_context.mode`, `final_diff_review.mode`, `jira_approval.mode` y `co_explore.debate`. Saltarlo es cómo se pierden cross-review, co-exploración (`co_explore`), el debate en decisiones, contexto de dominio, revisión final y `publish-spec` en silencio (se aplican los defaults sin avisar). |
| "Es trivial, salteo el gate y commiteo directo" | Trivial = 1 gate, no 0. La clasificación se **anuncia y se confirma siempre** (regla 2); no hay flujo con cero gates. |
| "Los tests pasan, seguro cumple los AC" | Tests verdes ≠ AC cumplidos. `verify` recorre `AC-1..N` con evidencia fresca **antes** de commitear (paso `verify`, regla 7). |
| "El agente delegado devolvió `STATUS: done`, marco la task `[x]`" | El reporte no es prueba. Validar `FILES` contra `git status` y revisar el diff antes de aceptar (modos `cross` y `workers`). |
| "Aprovecho y arreglo esto otro de paso, total es chico" | Si no mapea a un AC, se declara como `E-n` en `## Extras` antes de stagear — nada entra al commit sin rastro. |
| "Ya gasté 3 intentos en este fix, con uno más sale" | 3 fixes fallidos de la misma falla = problema de diseño: volver a `plan`/`specify`, no intentar un fix #4 (ver `implement`). |
| "Stageo todo lo que está dirty y después limpio" | Stage selectivo: solo `code_touched`; los archivos ajenos se confirman uno por uno (regla 8). |
| "Anuncio que despacho el subagente y cierro el turno" | Anunciar no es despachar: la tool call del subagente va en el **mismo turno** que la anuncias. Cerrar tras solo anunciar es un turno muerto que frena el flujo (vale para los dos puntos de despacho propios: la exploración de `analyze` y la revisión final de diff). |

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

`sdd-flow` es la **raíz** de sus corridas y el dueño único del aviso. Cuando construye el
carrier, escribe `root: sdd-flow`; ese campo prueba quién resolvió el inventario y quién ya
anunció la ausencia, de modo que ninguna corrida anidada vuelve a hacerlo.

#### Resolución y persistencia de la selección

Con `families` persistida se lee la declaración, se ejecuta el preflight solo para esos workers y
no se detectan otras familias ni se pregunta. Sin declaración, resolver antes de lanzar:

1. Proponer la selección.
2. Detectar las familias con CLI despachable.
3. Si hay otra presente, preguntar si se suma.
4. Presentar un STOP y persistir la respuesta.
5. Aplicar el ruteo de cada skill y recién entonces despachar: **ningún worker sale antes**.

El STOP muestra el **delta exacto** y hace un merge **no destructivo** sobre
`.specify/config.yml`: preserva las otras claves, crea `.specify/` y `cross_model` si faltan y
emite `schema_version: 1` cuando el bloque nace. Persiste `families` y `selection`; nunca escribe sin
permiso. Si solo está instalada una familia, ofrece el mismo STOP para guardar
`[<familia-del-conductor>]` con `selection: full`. En una raíz `sdd-orchestrator`, el destino
equivalente es el `manifest.yml` de la orquestación.

Una declaración vigente de `families` sin `selection` **no declara cómo se resolvió**. Antes de la
primera corrida posterior, abrir un STOP único que nombre la lista, ofrezca `full` y `user_choice` y
persista la respuesta con las mismas garantías. **No se infiere un default** ni se sondea para
elegirlo: preguntar una vez por una clave ausente no es descubrir familias. Desde esa respuesta se
lee la selección y no se vuelve a preguntar.

## Adaptación al proyecto (portabilidad)

Antes de cualquier paso operativo, descubrir el entorno **una vez** por sesión y resumirlo al usuario. Orden de resolución para cada parámetro: `config.yml` → autodetección → preguntar.

**Checkpoint de inicio (no salteable).** El **primer** acto operativo de toda corrida es leer `.specify/config.yml` si existe y **devolverle al usuario en una línea los valores resueltos** de al menos `tracker`, el inventario `cross_model.families`, `cross_review.mode`, `co_explore.mode`, `co_explore.debate`, `domain_context.mode`, `final_diff_review.mode` y `jira_approval.mode`, **con qué implican**. Ej.: *"config: tracker jira · families [claude] → inventario declarado y validado · cross_review on · co_explore on → exploración paralela antes de la spec · co_explore.debate auto → ofrezco debate en decisiones complejas de clarify/plan · domain_context auto → leer ADRs si existen · final_diff_review auto → revisión agregada en complex inline · jira_approval on → publico la spec en Jira tras aprobarla localmente"*. Ese eco es la prueba de que el config se leyó: sin él, es fácil aplicar los defaults (`cross_review` por complejidad, `domain_context: auto`, `final_diff_review: auto`, `jira_approval: off`) y perder cross-review, contexto de dominio, revisión final y `publish-spec` en silencio (ver red-flag "Arranco el flujo sin leer el config").

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
cross_model: {schema_version: 1, families: [codex], selection: user_choice, manifest: {mode: "on"}}  # allowlist de workers + procedencia; `schema_version` es obligatorio si el bloque existe
cross_review: {mode: auto, execution: auto}  # segunda opinión cross-model en los gates; ver "Revisión cross-model"
co_explore: {mode: auto, deadline: 600, debate: {mode: auto, max_rounds: 3}}  # exploración paralela + modo debate (decisiones); ver "Co-exploración cross-model"
domain_context: {mode: auto, context_paths: [], adr_paths: []}  # lectura de contexto/ADRs; ver "Contexto de dominio"
vault_archive: {mode: auto}  # rescatar el flujo al vault al archivarlo ("auto"|"on"|"off"); el disparador es esta clave, no que la skill esté instalada
final_diff_review: {mode: auto}  # revisión agregada de diff en cambios complex/high-risk inline
jira_approval: {mode: "off"}  # aprobación externa de la spec en Jira ("off"|"on", entre comillas: sin ellas YAML los parsea como booleanos; solo si tracker: jira); ver paso `publish-spec`
implement_mode: ask         # cómo ejecutar las tasks: ask (preguntar en el gate) | inline | cross | workers
cross_implement: {execution: auto, max_fix_rounds: 2, deadline: 1800}  # política de los modos cross y workers (solo si implement_mode es uno de esos dos); la familia del implementador la fija el conductor (sin `implementer:`); ver paso `implement` y skill cross-implement
```

Lo que no esté en `config.yml` se **autodetecta** por convención (detalle y comandos en `reference.md` → "Matriz de detección por capacidad"):

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
`co-explore` y `cross-review`, pasarlos como `context_paths` adicionales. **Nunca** crear,
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

> **Señal de dominio high-stakes.** Auth/permisos, pagos, migraciones de datos o schema,
> concurrencia y seguridad son caros de equivocar aunque toquen pocos archivos: un cambio **con
> lógica en juego** en estos dominios se trata como **complejo** aunque sus señales de tamaño
> digan *normal* — o, como mínimo, activa la revisión cross-model en *normal*. Anunciarlo en la
> clasificación: "normal por tamaño, complex por dominio (auth)". (No aplica a cambios puramente
> cosméticos en esos archivos: un typo en la UI de login sigue siendo trivial.)

> **Gates vs checkpoints.** El contador (trivial=1 / normal=2 / complejo=3) cuenta solo los **gates de artefactos SDD** (`specify`, `plan`, `tasks`): los puntos donde el flujo se detiene a aprobar un artefacto. **No** son gates de complejidad: los **checkpoints informativos** (confirmar el contexto en `gather-context`, confirmar el nombre de rama y **la elección de rama** en `create-branch`), los **setup checkpoints** de `init` y `constitution`, ni los **gates operativos** que existen siempre (revisión manual, commit, push).

## Revisión cross-model (segunda opinión, opcional)

Antes de cada gate de artefacto (`specify`, `plan`, `tasks`), si está disponible la skill
**`cross-review`**, se puede correr una **segunda opinión de un modelo de otra familia que
el autor** (Codex cuando conduce Claude; Claude cuando conduce Codex) que
critica el artefacto en read-only antes de mostrártelo. **Augmenta el gate, no lo reemplaza:** la
crítica se presenta *junto* al artefacto en el mismo STOP; tú sigues siendo el árbitro final.

- **Dependencia blanda.** Esta capacidad es opcional: si `cross-review` **no está instalada**,
  omitir la revisión y seguir con el gate humano normal. sdd-flow funciona igual sin ella (no es
  como un MCP de tracker: es un extra de calidad). Detectarla por capacidad, igual que el resto.
- **Cuándo se activa** (precedencia: override de la corrida > `cross_review` de `config.yml` >
  default por complejidad): default `trivial` off, `normal` opt-in (off salvo pedido), `complex`
  on. En *normal* el gate combina plan+tasks: se revisan juntos en ese único STOP.
- **Cómo invocarla.** Con el **Skill tool** (`cross-review`; esa skill sí es invocable por el
  modelo). Pasarle `artifact_type`, `artifact_path`, los `context_paths` relevantes (al revisar
  `tasks`, también `spec`+`plan`; sumar los paths resueltos de `domain_context` y, con
  co-exploración corrida, sumar además los informes
  los **índices** de la co-exploración y su **síntesis** (nunca los `detail-*` completos), cuando
  existan — ver "Co-exploración cross-model"),
  `working_dir`, `complexity` y `execution` (de `cross_review.execution`, que se hereda como el
  resto de la config). Devuelve el artefacto (quizá revisado) + un resumen de la crítica + la ruta
  del `review-log.md` (queda en `.plans/<id>/review-log.md`, local y untracked como el resto).
- **Degradación (nunca bloquea el flujo).** Si no hay revisor (el modelo de la otra familia no
  está disponible), si la skill
  está instalada pero la invocación falla (p. ej. error del Skill tool), si falla en
  runtime, si vence el timeout/`poll_deadline` de la revisión (la skill garantiza un tope duro: ver
  `cross-review/reference.md` → "Latencia y timeout (Claude revisor)"), o si `cross_review.mode: off` → avisar en una línea ("revisión
  cross-model no disponible — sigo con el gate humano") y continuar con el gate normal. Es la misma
  filosofía de la regla #6. **Si el retorno trae `aplicaciones_pendientes` mayor que cero, declararlo
  con sus `ids_pendientes` antes de liberar el gate:** una degradación no abre checkpoint, así que
  esta es la única oportunidad de decir que quedaron ediciones que ningún revisor observó, y
  aprobarlas sin saberlo es el mismo hueco que la revisión venía a cerrar.
- **Barrera preterminal (`review-pending`).** Mientras la revisión delegada esté pendiente, se
  apendiza `review-pending` a la línea del gate en curso —una marca, **no** un `status` nuevo de
  `plan.md`: precondición del STOP, no fase del flujo— y el STOP **no se presenta**; una aprobación
  que llegue antes del estado terminal **no se contabiliza** y se vuelve a pedir con la crítica a la
  vista. La levanta el **primer** estado terminal, veredicto o degradación: los cinco liberan el
  gate, así que no puede colgar el flujo (`cross-review/reference.md` → "Estados terminales que liberan el gate").
  **Con el modo automático activo, el fin de una tanda es una frontera interna y la barrera sigue
  marcada:** se libera en los tres cortes de ese modo, no al agotarse cada tanda.
- **El paso previo: arbitrar las disputas.** Si la revisión devuelve findings **`en-disputa`**, el
  humano los resuelve **antes** de elegir opción, dentro de este mismo STOP y sin gate extra. Dos
  destinos: **resolver a favor del finding** (pasa a `aplicado`, y el conductor aplica la corrección
  al artefacto) o **sostener el rechazo sobre el mérito** (pasa a `cerrado`). La decisión puede
  agruparse para findings que compartan motivo, pero **cada uno lleva su fila** en el ledger. Después
  de arbitrar, escribir **en este orden**: una `transicion` por finding —con `actor: humano`, su
  destino y el rationale— y luego **una** `control-corrida` con `evento_corrida: arbitraje-disputas`
  y `finding_id` nulo, **también si no se arbitró ninguna** —si no, ese caso sería indistinguible de
  que el arbitraje nunca se ofreció; y esa fila cierra **ese acto**, así que un checkpoint posterior
  abre otro con la suya—. Por finding la secuencia es **decidir → editar → registrar**: la fila hacia
  `aplicado` se escribe **después** de aplicar la corrección, nunca antes, porque una interrupción
  entre las dos dejaría el ledger afirmando una edición que no existe y una aplicación pendiente
  fantasma. Las filas llevan la **`ronda` acumulada al abrir el checkpoint**. **Y si la opción
  elegida no concede**, los rechazos sin responder que ese paso deja `en-disputa` se arbitran en el
  mismo STOP, antes de cerrar: es la única oportunidad que van a tener, porque esas dos opciones
  cierran la corrida. Mecánica completa y la cota de arbitrajes por finding en
  `cross-review/reference.md` → "El paso previo: arbitrar las disputas".
- **Tras arbitrar, ese conteo se re-deriva del ledger antes de declararlo.** El valor que vino en
  `tandas_concedibles` se calculó **antes** del arbitraje, así que queda viejo apenas el humano
  resuelve una disputa hacia `aplicado`. Se re-derivan `aplicaciones_pendientes`, sus
  `ids_pendientes`, `presupuesto`, `advertencia_bucle`, `recomendada` y los **tres inventarios**
  (disputas abiertas, rechazos sin responder,
  aplicaciones pendientes). **No** se re-derivan `causa_corte` ni `disponibles`, que son históricos;
  y `disponibles` **deja de usarse como advertencia** después de arbitrar, porque resuelta una
  disputa hacia `aplicado` una ronda sí puede converger — eso se deriva del ledger, no del campo.
- **Las cinco opciones del checkpoint, dentro del STOP existente.** Si la revisión devuelve
  `tandas_concedibles` (todo `REVISE` que abra checkpoint), el gate ofrece —sin gate extra, con el
  patrón de la pregunta de `implement_mode`— **continuar así** · **conceder una tanda** · **seguir
  hasta `APPROVED`** · **ronda de cierre con artefacto congelado** · **cerrar la revisión**. El
  presentador solo muestra el retorno, sin inferir, recalcular ni reordenar —salvo lo que el
  arbitraje de este STOP haya invalidado, que se re-deriva—: `serie` →
  `advertencia_bucle` → `aplicaciones_pendientes` con sus `ids_pendientes` → `opciones` con la
  `recomendada` marcada. Las cinco se ofrecen siempre: la recomendación advierte, no deshabilita,
  igual que `disponibles: false`. **El paso previo no las cambia:** no agrega una sexta ni
  altera sus postcondiciones. Postcondiciones de cada una —incluida la de qué hace con una
  aplicación pendiente nacida del arbitraje— en
  `cross-review/reference.md` → "Tandas y salida de rondas". **Si `aplicaciones_pendientes` es mayor
  que cero, mostrarlo con sus `ids_pendientes` *antes* de presentar las opciones**: "continuar así"
  aprueba el artefacto, y quien elige tiene que saber que hay ediciones que ninguna ronda observó.
- **Compatibilidad v1.** Si el retorno trae `contract_version: 1`, el presentador ofrece exactamente
  las cuatro de esa versión y omite serie, presupuesto y recomendación.
- **Cerrar la corrida es responsabilidad de la llamadora.** Tras el gate: si el usuario concede, se
  **reanuda la misma corrida con su `run_id`** (nunca se inicia otra); si elige una salida terminal
  —aprobar así o cerrar—, se **finaliza el único manifest** de la corrida. `cross-review` no puede
  hacerlo: al devolver todavía no sabe si habrá otra tanda.
- **`resume` consulta el descriptor antes de revisar.** Una corrida de revisión abierta —con su
  checkpoint pendiente— se **rehidrata** por `run_id`; no se duplica ni se recargan presupuestos
  (`cross-review/reference.md` → "Checkpoint durable").

> Detalle del loop, el contrato con el revisor (Codex o Claude según quién conduzca) y el formato del log: en la propia
> `cross-review`. Acá sdd-flow solo decide **cuándo** invocarla y **presenta** su salida en el
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

- **Dependencia blanda.** Igual que `cross-review`: si `co-explore` **no está instalada**,
  se omite y el flujo sigue con la exploración de siempre del conductor.
- **Cuándo se activa** (precedencia: override de la corrida > `co_explore` de
  `config.yml` > default por complejidad): default `trivial` nunca, `normal` opt-in (off salvo
  pedido), `complex` on.
- **Momento 1 — `explore` (pre-spec).** Tras confirmar el contexto y la clasificación en
  `gather-context`: (1) armar el **paquete de contexto** (digest del ticket + prompt del usuario +
  complejidad + paths resueltos de `domain_context`), que viaja **idéntico a los dos workers**.
  Suma además los **hechos crudos** del bloque declarativo de la búsqueda de antecedentes:
  los **términos buscados**, el **estado de cada fuente** con la razón de cada una no comprobada, y las
  **coincidencias crudas** con su ref, su ruta y su SHA. Viajan **también cuando el resultado es
  vacío**: sin los términos y los estados por fuente, "no se encontró nada" y "no se buscó en esa
  fuente" dejan de distinguirse para quien recibe el paquete. Lo que **no** viaja es ninguna
  clasificación ya resuelta —cobertura total o parcial, delta pendiente, impacto en el alcance—: el
  paquete tiene prohibido llevar conclusiones del conductor, y una ya tomada contamina justamente la
  independencia que la co-exploración compra. Si el prompt/ticket trae **URLs de reproducción** ("abre esta URL para ver el
  error") y hay tool de navegador, el conductor **reproduce antes de despachar** y suma al
  paquete un digest **observacional** de la evidencia (salida de consola, requests fallidos,
  pasos observados) — hechos, **sin hipótesis propias**, que contaminarían la independencia del
  explorador (que es headless: no puede navegar). Sin tool de navegador, degradación de la regla
  6: pedir capturas/pasos al usuario, o seguir sin reproducción avisando; (2) invocar
  `co-explore` (Skill tool) con `mode: explore`, `execution: background`; (3) **el conductor no
  explora**: espera el envelope y arbitra desde los índices, abriendo detalle solo por disparador
  (ver `co-explore` → "Lectura selectiva"). Solo si el envelope resuelve a una **rama degradada**
  el conductor produce su propio mapa, con el mismo contrato de índice y detalle; (4) **punto de
  encuentro:** leer el envelope — `outcome`, `branch`, `diversity`, `workers[]`, `contributors[]`—
  y declarar la rama alcanzada en una línea; (5) **síntesis**, siguiendo la guía de
  `co-explore` → "La síntesis (guía para la skill llamadora)" (no se duplica acá): compara **por
  ID**, admite `∅` en divergencias unilaterales, registra qué detalles se abrieron, y fusiona las
  incógnitas (las que cambiarían el diseño alimentan `clarify`); (6) **checkpoint informativo
  condicional** (no es un gate SDD): solo si quedaron
  divergencias sin resolver o enfoques viables materialmente distintos, presentarlos y dejar
  decidir al usuario antes de escribir la spec — si los mapas convergen, se sigue directo a
  `specify` sin stop extra.
- **Momento 2 — `counter-plan` (pre-plan).** Con la spec aprobada (y ya posicionados en la rama
  feature), antes de escribir `plan.md`: invocar `co-explore` con `mode: counter-plan`
  (contexto: **núcleo común** con la spec aprobada + paths resueltos de `domain_context`, más un
  **anexo privado** por worker con su propio índice y detalle de la fase `explore` — nunca el de la
  otra familia, nunca por ruta); contrastar los dos contra-enfoques en una adenda del cierre (mismo criterio de la síntesis: méritos, no adopción automática) y escribir
  `plan.md` con esa síntesis a la vista.
- **Los artefactos no citan la co-exploración.** `spec.md` y `plan.md` se escriben con la
  síntesis a la vista pero redactados de forma autónoma: sin referencias a la co-exploración,
  a los informes del revisor, a `co-explore/` ni al vocabulario conductor/revisor (ver
  `co-explore` → "La síntesis", paso 5). La trazabilidad queda en `.plans/<id>/co-explore/`.
  El checkpoint informativo conversacional no está alcanzado por esta regla, y tampoco lo están las
  **tres excepciones** que declara la lista cerrada de esa misma regla de `co-explore` —nota de
  límite, advertencia de una sola voz y **aviso de corridas delegadas en vuelo**—, que valen igual
  cuando `co-explore` corre standalone.
- **Efecto en `analyze`.** Con co-exploración **nominal** (rama 1), este paso **no explora**: el
  contra-enfoque de `counter-plan` ya cubrió el terreno, y `analyze` queda acotado a comprobar
  **vigencia sobre el HEAD** real de la rama (archivos movidos, código cambiado) y a las
  **verificaciones puntuales** de punteros que habilite un disparador. Solo las **ramas degradadas**
  recuperan el `analyze` completo, porque ahí el mapa del conductor sí es el insumo.
- **Crítica informada.** En los gates de `specify` y `plan`, si la revisión cross-model está
  activa, pasar a `cross-review` los paths resueltos de `domain_context` y, de la co-exploración,
  **los índices y la síntesis** — nunca los `detail-*` completos, que reintroducirían el costo que
  la lectura selectiva elimina. Qué sesión reanuda el revisor **no queda a criterio**: lo fija la
  matriz de `cross-review/reference.md` → "Matriz de resume desde co-exploración", que nunca
  resuelve a la familia del autor ni a un worker `INVALID`.
- **Degradación (nunca bloquea).** La escalera de `co-explore` tiene cuatro ramas y el envelope
  dice cuál se alcanzó; en las degradadas el conductor explora y **se declara** qué diversidad
  quedó. Skill no instalada, `outcome: map_failure`, o los dos workers caídos → avisar en una línea
  y seguir el flujo normal. Misma filosofía de la regla #6.

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
  trade-offs" del plan) y el modo lo habilita, ofrecer someter *ese* trade-off a debate (con
  `plan.md` como contexto) antes del gate del plan; la decisión resultante se refleja en el plan.
- **Umbral del ofrecimiento:** `off` nunca; `auto` solo en decisiones complejas / high-stakes
  (auth, pagos, migraciones de datos o schema, concurrencia, cambios difíciles de revertir) o si
  estás genuinamente inseguro; `on` en cualquier decisión contestable.
- **Lo que aterriza en el artefacto va limpio.** La respuesta de `clarify` en `spec.md` y el
  trade-off resuelto en `plan.md` se escriben **sin** mencionar el debate, las familias ni el
  método (fluyen a Jira/PR). La atribución por familia vive solo en `co-explore/debate.md`, local
  (ver `co-explore` → "Publicado vs local").
- **Degradación:** sin la otra familia, no hay debate: seguir al gate normal con un aviso de una
  línea (misma filosofía que el resto de co-exploración).

### Tercera pasada adversarial sobre la síntesis

Cuando una co-exploración termina con los mapas **convergiendo**, el flujo sigue derecho a escribir la
spec o el plan: el checkpoint informativo aparece **solo si quedaron divergencias sin resolver**, así
que la convergencia total pasa en silencio. Y la convergencia no es verificación — dos acuerdos
independientes se leen como si lo fueran, y por eso **pueden blindar un error**. Este paso agrega una
crítica adversarial sobre la síntesis antes de que alimente el artefacto, en los **dos momentos**:
después de la síntesis de `explore` y después de la de `counter-plan`. Lo gobierna
`co_explore.tercera_pasada.mode` y lo ejecuta `cross-review` con `artifact_type: sintesis`. En los
tres valores del modo **se ofrece y se espera un "sí"**: nunca corre sola.

**Cuándo se ofrece, y en qué orden.** Con `auto`, el predicado tiene las **dos** condiciones que abren
el checkpoint informativo: que no queden **divergencias sin resolver** ni **enfoques viables
materialmente distintos**. El orden con ese checkpoint está fijado y no se deja a criterio: primero
se **resuelve** el checkpoint, después se **reevalúa** el predicado y recién entonces se ofrece la
crítica, sobre la síntesis ya resuelta. Los dos pasos pueden aparecer **secuencialmente en la misma
corrida**, y eso es correcto: uno cierra posiciones abiertas y el otro ataca el resultado. Si el
usuario **no resuelve** las posiciones, no se inicia una crítica cuyo objeto todavía no está cerrado.

**El gobierno es independiente de `cross_review`.** El "sí" sobre `co_explore.tercera_pasada`
**autoriza esta invocación** aunque `cross_review.mode` esté en `off` o `sintesis` no figure en
`cross_review.artifacts` — esa lista gobierna los artefactos de `cross_review.mode`, no este paso. De
`cross_review` se heredan solo tres campos: `execution`, `max_rounds` y `reviewer`.

**Qué hacer con cada terminal del retorno.** Acá **no existe** el gate de artefacto donde
`cross-review` espera que su salida se presente —todavía no hay spec ni plan escritos—, así que los
tres se consumen explícitamente:

| Terminal | Qué hace `sdd-flow` |
|---|---|
| `APPROVED` | continúa, y escribe el artefacto **desde la síntesis revisada** |
| `UNAVAILABLE` | avisa en una línea y continúa con la síntesis tal como estaba |
| `REVISE` | presenta las **cinco opciones** del checkpoint según el orden normado del retorno, conserva el `run_id` para reanudar la misma corrida, y **no escribe la spec ni el plan** hasta que se resuelva |

**Qué se hace con lo que la crítica encuentre.** Cada hallazgo se arbitra por el **ledger** de
`cross-review` —aplicado, rechazado con motivo, o escalado—, y **un hallazgo adoptado corrige la
síntesis**: aceptarlo sin que cambie ningún insumo posterior es un estado inválido. La corrección se
publica de forma **atómica** y vuelve a validar el **predicado de cierre** de `co-explore` **antes**
de escribir la spec o el plan; una edición puede romper la cabecera, los IDs o una sección
obligatoria, y entonces el flujo consumiría un cierre que `co-explore` rechazaría al retomar.

**La crítica también se verifica.** Los hallazgos son insumo, no órdenes, y acá hay un dato medido:
en la corrida que originó este paso, **uno de los ocho** hallazgos era falso — y era justamente el que
acusaba de roto al comando de verificación del conductor. Se refutó con un control positivo de una
línea. Aceptar una crítica sin verificarla es el mismo error que ignorarla.

**La sesión que criticó no se reutiliza.** Para juzgar si la síntesis representó bien los informes, el
crítico los recibe completos, así que esa sesión queda **contaminada** con material que la revisión
posterior de la spec o del plan no debe ver. Esa revisión sale con **worker fresco**, y recibe los
**índices** y la **síntesis corregida** como contexto.

**Cómo se sabría que el paso paga.** Sobre las pasadas **aceptadas y completadas** —no las declinadas
ni las degradadas—, en una ventana de al menos **seis**, se registra cuántas cambiaron una
recomendación. Se revisa la consigna **salvo que `cambios / pasadas > 1/3`**: la evidencia pedía
cambiar una recomendación en *más* de una de cada tres, así que exactamente un tercio no paga. El
registro vive en una sección `### Métrica de tercera pasada` del `review-log.md`, **separada del
ledger** —cuyo esquema es cerrado y no se amplía en silencio—, con los campos `eligible`,
`recommendation_changed` y `run_id`, y la escribe `sdd-flow` **después** del terminal. El cálculo es
manual y no lleva guarda.

**Degradación:** sin la otra familia, o sin `cross-review` instalada, no hay tercera pasada: avisar en
una línea y seguir. Misma filosofía que el resto de la co-exploración.

## Compatibilidad con Plan Mode / modos no mutantes

Si el entorno prohíbe mutaciones (Plan Mode, modo solo-lectura, etc.):

1. No crear rama, no escribir `.specify/` ni `.plans/`, no modificar código, no ejecutar `implement`, **ni `publish-spec`** (es una escritura externa a Jira: doblemente vedada en estos modos).
2. Ejecutar solo pasos read-only: detección de entorno, `gather-context`, `analyze` estático, lectura de tracker, búsqueda en código y una propuesta de spec **conversacional**.
3. Avisar explícitamente que el flujo real queda bloqueado por el modo, y que al salir se retoma **re-corriendo el sub-paso 5 de `gather-context`** —que es el que escribe `.plans/<id>/antecedentes.md`, imposible en este modo— y recién después desde escribir `spec.md` (y crear la rama si falta). Saltar directo a `specify` deja un camino completo hasta el commit sin ledger de búsqueda, y ninguna guarda lo ve: la de flujos heredados solo se evalúa al retomar con `resume`.
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
| "seguí en esta rama", "trabajá sobre la rama actual" | elige sin preguntar la salida **seguir en la rama actual** de la elección de rama (ver "Paso `create-branch`" y `reference.md` → "Elección de rama") |
| "rama nueva", "cortá desde main" | elige sin preguntar la salida **rama nueva desde la base** de la elección de rama (ídem) |
| "con prefijo de rama X", "prefijo de rama: X", "usa el prefijo X para la rama" | registra el **override de prefijo** de la corrida (reemplaza `{type}` en `create-branch`; ver "Paso `create-branch`") |
| "parte desde la rama X", "base: rama X", "esto depende de X", "corta desde X" (X = una rama, no la base habitual) | registra el **override de base** de la corrida (`create-branch` corta desde X en vez de `default_branch`, sin tocar el config; ver "Paso `create-branch`") |
| "sin cross-review", "salta la segunda opinión" / "con cross-review", "pide segunda opinión" | registra el **override de revisión cross-model** de la corrida (off/on; ver "Revisión cross-model") |
| "con co-exploración", "que Codex explore en paralelo" / "sin co-exploración" | registra el **override de co-exploración** de la corrida (on/off; ver "Co-exploración cross-model") |
| "con debate", "somételo a debate" / "sin debate" | registra el **override de debate** de la corrida (on/off; ver "Debate en decisiones") |
| "con tercera pasada", "que critiquen la síntesis" / "sin tercera pasada" | registra el **override de la tercera pasada** de la corrida (on/off; ver "Tercera pasada adversarial sobre la síntesis") |
| "sin aprobación de jira", "no subas la spec" / "con aprobación de jira", "sube la spec a revisión" | registra el **override de aprobación externa** de la corrida (off/on; ver `publish-spec`) |
| "implementa acá mismo", "inline" / "implementa con Codex", "delega la implementación" / "delega con mi familia" | registra el **override del modo de implementación** de la corrida (inline/cross/workers; ver `implement` → "Modo de ejecución") |
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
4. **Wizard de decisiones — una sola pantalla, tres preguntas.** Se pregunta lo que la skill no puede saber, por dos motivos: no hay default, o hay default pero la política del equipo puede diferir y nada en el repo la revela. Con una herramienta de **selección interactiva** (descubrir por capacidad, no por nombre) mostrar cada opción con descripción y el valor actual/detectado como "(actual)"; sin ella, degradar al modo conversacional: proponer los valores y confirmar (regla 6).
   - **Sin default** — **`tracker`** (jira · github · gitlab · linear · none): con varios MCP disponibles a la vez la autodetección es ambigua, y fijarlo hace el paso determinista.
   - **Con default, pero política del equipo** — **`branch_prefix`** (default `""` → prefijo semántico; alternativa fija, p. ej. `feature/`) y **`jira_approval.mode`** (default `"off"`; alternativa `"on"`) — este último **solo si se acaba de elegir `tracker: jira`**, con otro tracker la clave no aplica y no se pregunta. Ninguna skill puede detectar cuál prefiere el equipo, y la elección cambia el flujo: `jira_approval` decide si la spec se publica en Jira y espera aprobación.
5. **Todo lo demás no se pregunta.** Los comandos y paths (`test_cmd`/`build_cmd`/`lint_cmd`/`test_scope_hint`, `default_branch`, `stack`, y los `context_paths`/`adr_paths` de `domain_context`) se **autodetectan** y quedan editables en el preview del paso 6. Las claves con default —entre ellas `commit_style`, `implement_mode`, `cross_review`, `domain_context`, `final_diff_review` y el `debate` de `co_explore`— no van al wizard: la skill las resuelve, y quien quiera fijarlas las copia del ejemplo (paso 8).
6. **Armar y mostrar** el contenido completo de los archivos antes de escribir:
   - `.specify/config.yml` — con las selecciones del wizard + comandos/paths detectados. Esquema en `reference.md` → "Esquema de `.specify/config.yml`". Al escribirlo, emitir `cross_review.mode`, `domain_context.mode`, `final_diff_review.mode`, `jira_approval.mode` y `co_explore.debate.mode` con los valores `on`/`off` **entre comillas** (`"on"`/`"off"`; `auto` sin comillas es válido): sin ellas YAML los parsea como booleanos.
   - `.specify/constitution.md` — desde `reference.md` → "Plantilla de constitution" (definición de *Done*, formato de AC, regla de trazabilidad, y un **puntero** a los principios de código del repo —`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`— si existen).
   - `.specify/workers.yml` — solo si no existe: mostrar los dieciséis defaults y el delta contra
     las rutas vigentes desde `reference.md` → "Matriz de defaults y delta de inicialización". Un
     archivo existente y válido se conserva sin sobrescribirlo.
7. **STOP** — escribirlos **solo tras confirmación**. Son locales y untracked (regla #10): nunca se trackean, comitean ni se agregan a un `.gitignore` compartido.
8. **Cierre — apuntar al resto.** Al confirmar, decir en una línea que el config admite **35 claves**, que el wizard solo preguntó lo que la skill no puede saber, y que el resto vive en `config-ejemplo.md`, listo para copiar por bloques con cada valor marcado `[def]`, `[ej]` u `[obl]`; sin este cierre, reducir el wizard convierte "no te lo pregunto" en "no existe": las seis preguntas que salieron —`commit_style`, `implement_mode`, `cross_review`, `domain_context`, `final_diff_review` y `debate`— tienen que quedar descubribles.
9. **Re-corrida:** si `config.yml` y `constitution.md` ya existían, no pisar a ciegas — el wizard mostró los valores vigentes pre-seleccionados; al confirmar, **fusionar** los cambios respetando lo que el usuario mantuvo. Si `workers.yml` ya existía y es válido, **no se pisa**. Si prefiere no fijar config, puede saltar `init`: el ciclo sigue con autodetección + defaults conversacionales (ver `constitution`).

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
5. **Buscar antecedentes en el repositorio.** Antes de clasificar, recorrer el árbol y su historia para saber si el objetivo ya se hizo, se está haciendo, o se descartó con motivo. El procedimiento —las seis fuentes, el algoritmo de términos, las señales que acreditan un candidato y el esquema de `.plans/<id>/antecedentes.md`, donde queda el resultado— vive en `reference.md` → "Búsqueda de antecedentes".
   - **Es incondicional.** No hay clave que lo apague, no es una dependencia blanda y no despacha ningún agente: una búsqueda condicional es exactamente el hueco por el que un flujo aprueba una spec y corta una rama sobre la premisa de que no había nada previo. El molde es el sub-paso 1 de `clarify` —"el código responde primero"—, que ya es un acto de lectura del árbol obligatorio dentro de esta misma skill.
   - **Crea `.plans/<id>/` acá**, adelantando la creación que de otro modo ocurre en `specify`: el recorrido termina **antes** de que exista `spec.md`, así que su resultado necesita una sede propia, que es la autoridad durante toda esa ventana.
   - **En un modo no mutante** —Plan Mode, solo-lectura— el sub-paso **corre igual, en memoria, y no escribe nada**: ni `.plans/<id>/` ni el ledger. Su resultado va al checkpoint del paso 6 de forma conversacional. Lo único que queda `no comprobado` son las **refs remotas** —la rama (a) de la actualización de refs—, **no** una fuente entera: las seis se leen perfectamente en local. Es la única forma de que "incondicional" y la garantía read-only —por la que `gather-context` está permitido en esos modos— se sostengan a la vez; al salir del modo, el sub-paso se re-corre y recién entonces persiste.
   - **Las transiciones, según la celda** que resuelva la matriz de salidas de `reference.md` —que cruza cobertura con **cinco** estados de vigencia, así que estas cuatro filas son las salidas frecuentes y no el conjunto completo:

     | Qué se encontró | Qué pasa con el flujo |
     |---|---|
     | cubierto **entero y vigente** | **no avanza a `specify`**: se ofrece cerrar el flujo o reformular el objetivo, y **una reformulación requiere confirmación humana** |
     | cubierto **en parte**, acreditado | se escribe la matriz parte/evidencia/delta y el alcance queda en el **residual** —la resta exacta—, con la modulación anunciada |
     | meramente **relacionado** | entra como **contexto**; el alcance queda **intacto** |
     | **falso positivo** | descartado, con su descarte registrado |

   - Dos celdas **no** están en esa tabla y cambian lo que el flujo hace: un hallazgo **total y recuperable sin conflictos** *obliga* a reformular —no lo ofrece—, y uno **recuperable con costo** va al **checkpoint con el número de conflictos declarado**, sin recortar por su cuenta. Ante una celda que no sea una de las cuatro de arriba, manda la matriz.
   - **El resultado entra en el checkpoint del paso 6**, que ya existe: no se abre un stop nuevo ni se agrega un gate. Quien confirma el contexto lo hace con los hallazgos a la vista.
6. **Clasificar complejidad** (sección de arriba), anunciarla con justificación y confirmar el contexto en 5-8 bullets antes de avanzar. El resumen del paso 5 —qué se buscó, qué fuentes quedaron sin comprobar y con qué impacto en el alcance— se presenta en este mismo checkpoint.

## Paso `specify` → GATE

**Objetivo:** escribir el **QUÉ** y el **por qué**, con criterios de aceptación verificables — sin detalles de implementación.

1. `.plans/<id>/` **ya existe**: lo creó el sub-paso 5 de `gather-context` junto con su ledger de búsqueda. Si faltara —un flujo heredado, anterior a ese paso—, crearlo (POSIX: `mkdir -p`; PowerShell: `New-Item -ItemType Directory -Force`).
2. Escribir `spec.md` con la plantilla de `reference.md` → "Plantilla de spec". Mínimo: problema/objetivo, alcance (in/out), y **criterios de aceptación numerados `AC-1..N`** en formato verificable (Given/When/Then o checklist observable).
3. **Promover el resultado de la búsqueda de antecedentes.** Proyectar **únicamente el bloque `## declaracion`** de `.plans/<id>/antecedentes.md` a una sección `## Antecedentes` de `spec.md` —o al `### Antecedentes` del bloque `## Spec` en trivial—. **Nunca se copia el archivo entero:** `## estado` es el ledger máquina, y publicarlo filtra fingerprints y estado interno a un artefacto que puede terminar en un tracker.
   - `antecedentes.md` **sobrevive** a la promoción con su `## estado` intacto. Desde acá la spec manda sobre el **QUÉ**, y el ledger sigue mandando sobre **qué se corrió y qué hay que re-correr**: una sola autoridad por pregunta, en cada momento.
   - **La marca de promoción no es un campo nuevo.** Es la condición derivada `busqueda: complete` **y** la existencia de la sección de destino en su sede. Un quinto campo en `## estado` duplicaría una autoridad que ya vive en el destino.
4. Para cambios *triviales*, la spec puede ser un bloque breve dentro de `plan.md` en lugar de archivo aparte.
5. **STOP** — si la **revisión cross-model** está activa para `spec` (ver "Revisión cross-model"), ejecutar `cross-review` sobre `spec.md` antes de presentar (sumar `domain_context` resuelto y, con co-exploración, los **índices + la síntesis** de `explore` — nunca los `detail-*` — ver "Co-exploración cross-model"). Presentar la spec (con el resumen de crítica, si lo hubo) y pedir aprobación. No avanzar sin ella. Si el usuario corrige, actualizar y volver a ofrecer.

## Paso `clarify` (condicional)

Obligatorio en cambios *complejos*; en *normales* solo si hay ambigüedad; se saltea en *triviales*.

1. **El código responde primero.** Antes de preguntar algo al usuario, chequear si el repo lo responde (grep/lectura puntual): una pregunta cuya respuesta vive en el código es ruido en el gate. Al usuario solo llegan las que requieren una decisión o conocimiento que el código no tiene.
2. Hacer las preguntas de cobertura **una a una**, recorriendo el árbol de decisiones **en orden de dependencia** — primero las que condicionan a las demás; cada respuesta abre o cierra ramas —, enfocadas en cerrar ambigüedades que cambiarían el diseño (no detalles cosméticos).
3. **Cada pregunta lleva una respuesta recomendada** con su porqué. Con herramienta de selección interactiva (p. ej. `AskUserQuestion` — descubrir por capacidad), la recomendada va primera y marcada "(Recomendada)"; sin ella, proponerla conversacionalmente. El usuario decide; la recomendación solo baja el costo de decidir.
4. Registrar cada Q&A en la sección `## Clarifications` de `spec.md` (queda auditable, no solo en el chat).
5. Si una respuesta altera los criterios de aceptación, actualizar los `AC-n` y volver al gate de `specify`.

## Paso `publish-spec` (aprobación externa de la spec — Jira, opcional)

**Objetivo:** publicar la spec aprobada localmente en una **subtarea de Jira** para que el TL/PO la revisen y aprueben **antes** de implementar, y dejar el flujo en pausa hasta esa aprobación. Es un **gate externo y asíncrono**: aumenta el gate local de `specify`, no lo reemplaza.

**Cuándo se activa** (precedencia: override de la corrida > `jira_approval` de `config.yml` > default **off**). Requiere además: `tracker: jira`, que `<id>` sea una clave de ticket real (el **padre**), y un MCP/CLI de Atlassian con **capacidad de escritura**. Si falta cualquiera → el paso no aplica (degradación, abajo). Tampoco aplica en cambios **triviales** (no hay `spec.md` separada ni gate de `specify` que publicar): si `jira_approval` está `on` y el equipo requiere la aprobación externa, avisar y ofrecer reclasificar a *normal*. Corre **después** del gate local de `specify` (y de `clarify` si aplica, con la spec ya estable) y **antes** de `create-branch`: no se crea rama ni plan sobre una spec que el TL/PO aún no aprobaron.

1. **Construir el payload** de la subtarea (plantilla y reglas en `reference.md` → "Aprobación externa de la spec (Jira)"): título `SPEC: <título corto>`; descripción con **primero un resumen ejecutivo no técnico** (problema, objetivo, alcance, fuera de alcance, criterios de aceptación en lenguaje de negocio) y **debajo la definición técnica** (cuerpo de `spec.md`, prácticamente literal). **Sanitizar** (acotado: todo lo técnico —`AC-n`, métodos, código y paths de código fuente del proyecto— se publica sin abstraer): nunca publicar menciones a cross-review / co-exploración / segunda opinión / modelos, URLs o entornos locales o de prueba (`localhost`, `127.0.0.1`, hosts de desarrollo como `local.<proyecto>.dev:4200`, `file://`), ni artefactos/mecánica del flujo SDD (`.plans/`, `.specify/`, paths absolutos locales, archivos del propio flujo, `status`, prefijos de rama, comandos de test/build, nombres de fases del flujo). Guardar la copia exacta de lo que se va a publicar en `.plans/<id>/jira-spec.md`.
2. **STOP (write-safety).** Mostrar (1) el **recurso** exacto (proyecto + issue padre `<id>`) y (2) el **contenido** exacto a publicar, y pedir confirmación. Recién entonces crear la subtarea (`createJiraIssue` con `parent` + issuetype de subtarea; ver `reference.md` → "Flujo por tracker"). Misma disciplina para toda escritura posterior (actualizar descripción, comentar, transicionar): siempre recurso + contenido a la vista antes de ejecutar.
3. **Escribir `handoff.md`** con `gate_status: awaiting`, `parent_key`, `subtask_key` (la subtarea creada), `jira_subtask_url` (`<site_url>/browse/<subtask_key>`, con `<site_url>` = la URL del site Atlassian resuelta por el MCP —p. ej. vía `getAccessibleAtlassianResources`—, para que `open-pr` pueda linkear la spec), `cloud_id`, y el snapshot de `gather-context` (ver "`handoff.md` (retomado del flujo)"). Avisar que el flujo queda **en espera de aprobación** y cómo retomarlo (`resume` con `<id>`; o decir "ya aprobaron" / "revisa el ticket"). **No** seguir a `create-branch` hasta la aprobación.
4. **Al retomar**, la detección de aprobación y el loop de observaciones los maneja `resume` (ver `resume` → "Gate de Jira (esperando aprobación externa)").

**Degradación (regla 6, nunca bloquea).** Si `tracker != jira`, no hay clave de padre, el feature está `off`, o el MCP de Atlassian es solo-lectura / falla la escritura → avisar en una línea y, si igual quieres el gate, ofrecer que crees la subtarea a mano y pegues su clave (se registra en `handoff.md` y se sigue el mismo loop). Si nada de eso aplica, continuar el flujo normal sin gate externo.

## Paso `create-branch`

**Objetivo:** dejar el flujo parado en la rama correcta —creándola desde la base resuelta, reutilizando la rama actual o renombrándola— con la nomenclatura acordada. Se ejecuta una vez aprobado el **qué** (tras `specify`/`clarify`); en cambios *triviales* —sin spec separada— se hace al inicio, antes de `plan`.

1. Verificar que no haya **cambios en archivos versionados** pendientes: `git status --porcelain -- ':(exclude).plans' ':(exclude).specify'`. Los artefactos locales del flujo (`.plans/`, `.specify/`) y los generados que el repo ya ignora **no cuentan**: "limpio" significa sin código sin commitear, no sin estos artefactos (que `specify`/`constitution` pudieron crear antes). Si hay cambios de código, detener y avisar.
2. **Resolver y normalizar la rama base — sin mover el HEAD todavía.** Precedencia de la `base_branch` efectiva: (a) **override de base de la corrida** si el usuario lo indicó (ver router → "override de base"; p. ej. una feature dependiente que corta desde otra rama en QA/revisión, no desde la base habitual) → (b) `default_branch` del `config.yml` → (c) rama base **detectada** (`git symbolic-ref refs/remotes/origin/HEAD`). El override **no** toca el `config.yml`: vale solo para esta corrida. La detección suele devolver `origin/<rama>` (un ref remoto): quitarle el prefijo `origin/` para obtener la **rama local** (`origin/main` → `main`) y `git fetch origin`. **Posicionarse en ella todavía no**: eso movería el HEAD antes de que haya decisión, y se hace en el paso 5 sólo si la salida elegida lo pide. Si la rama base no existe local ni remotamente, detener y avisar (no inventar una base). Nunca hacer `git checkout origin/<rama>` (deja *detached HEAD*) ni asumir `main`/`master`. Registrar la `base_branch` resuelta para el header del `plan.md` y el snapshot del `handoff.md`.
3. **Determinar el prefijo efectivo** (`{type}`) y **construir el nombre**. Prefijo, primer valor presente: (a) **override de la corrida** si el usuario lo indicó (ver router → "prefijo de rama"); (b) **`branch_prefix`** del `config.yml`; (c) **prefijo semántico** derivado del tipo de issue/contexto (mapeo en `reference.md` → "Mapeo tipo de cambio → prefijo"; para features es **siempre `feature`, nunca `feat`** — `feat` es solo para commits/`change_type`; ante la duda, preguntar), normalizado sin la barra final (`feature/` y `feature` dan lo mismo, porque el `/` ya está en `branch_format`); si `branch_format` fue customizado sin `{type}`, `branch_prefix`/override no aplican. Nombre con `branch_format` (default `{type}/{ticket}-{slug}`): `{ticket}` = clave del tracker (si no hay, se omite **junto con su separador**: `fix/cart-null-guard`, nunca `fix/-cart-null-guard`); `{slug}` = 2-5 palabras del título en kebab, sin acentos, `[a-z0-9-]`. Ejemplos: `feature/ABC-123-export-csv`, `fix/cart-null-guard` (sin ticket); con `branch_prefix: feature/` fijo, hasta un fix queda `feature/PROJ-9-null-cart`.
4. **Clasificar el HEAD y decidir.** Comparar `git rev-parse --abbrev-ref HEAD` contra la `base_branch` normalizada. Si **coinciden**, mostrar el nombre propuesto y pedir confirmación —aceptando correcciones o un nombre exacto del usuario—, como siempre. Si **no** coinciden, el paso **se detiene y presenta la elección**: seguir en la rama actual, rama nueva desde la base, rama nueva cortada desde la actual, y renombrar la actual cuando es sólo local. Sus precondiciones, las tablas que fijan la recomendación y el aviso, la reparación posterior al rename y los estados **detached** y **sin commits** —donde el paso para con diagnóstico en vez de ofrecer salidas— están en `reference.md` → "Elección de rama". Con **override de base** de la corrida, **no se pregunta**: el usuario ya eligió y un override explícito no se re-consulta.
5. **Ejecutar la salida elegida, y recién ahí mover el HEAD.** Seguir en la rama actual **no mueve el HEAD** ni ejecuta comando alguno: `branch` = la rama actual, `base_commit` = `git rev-parse HEAD`, y `base_branch` sigue siendo la base resuelta (el destino del PR, que se anuncia junto con la elección). Para una rama nueva, posicionarse primero en la base (`git checkout <rama-local>` + `git pull --ff-only origin <rama-local>`; con override de base, la rama X puede ser **puramente local o estar adelantada del remoto**, así que el pull va **solo si X tiene upstream** —`git rev-parse --abbrev-ref --symbolic-full-name @{u}` no falla— y si no, se corta desde el HEAD local de X) y después `git checkout -b <branch>`. **El `checkout -b` no es incondicional:** si el nombre ya existe, detener mostrando el nombre y reofrecer las mismas salidas; nunca `checkout` sin `-b` a una rama ajena, nunca un sufijo inventado. Guardar `branch` y `base_branch` para el header del `plan.md` y los pasos siguientes.

## Paso `analyze`

**Objetivo:** entender el código lo suficiente para planear bien.

- **Contexto de dominio.** Leer los paths resueltos de `domain_context` antes de decidir nombres,
  alcance técnico o contratos. Usar ese contexto para adoptar términos canónicos, respetar ADRs
  vigentes y marcar conflictos como incógnitas; no escribir ni actualizar esos documentos.
- **Si es bug:** seguir un método de debugging sistemático (hipótesis → prueba → refutar). Si hay una skill de debugging sistemático disponible, usarla. Si es reproducible en navegador y hay tool de navegador, capturar consola/network; si no, pedir captura/pasos. El mismo método aplica si un test o un AC falla durante `implement`/`verify` (ver `implement`, pasos 3-4).
- **Si es feature/refactor:** mapear archivos/módulos/utilidades existentes a reutilizar. Preferir reúso sobre código nuevo.
- Localizar el código con búsqueda en el repo (subagentes de exploración si el entorno los soporta y el alcance lo amerita; si no, `grep`/`ripgrep`/`find` locales). **Con co-exploración nominal esto no se hace**: el terreno ya está mapeado y `analyze` solo comprueba vigencia sobre el HEAD (ver "Co-exploración cross-model" → "Efecto en `analyze`").

**Output:** hipótesis (bug) o lista de puntos de reúso (feature) con referencias `path:line`.

**Con co-exploración nominal** (ver "Co-exploración cross-model"), este paso **no re-explora ni construye mapa**: comprueba vigencia sobre el HEAD y hace las verificaciones puntuales que habilite un disparador. Las ramas degradadas recuperan el `analyze` completo.

## Paso `plan` → GATE

**Objetivo:** dejar el **CÓMO** técnico en `plan.md`, con header YAML para bootstrap.

1. Estando ya en la rama feature (creada en `create-branch`), obtener `base_commit` = `git rev-parse HEAD` y la fecha ISO-8601 actual. Si en `create-branch` se resolvió una `base_branch` **distinta de `default_branch`** (override de base), conservarla para el header (define el destino del PR); si coincide con `default_branch`, se omite del header.
2. Escribir `plan.md` con el header YAML obligatorio + secciones de enfoque, decisiones y trade-offs (las elecciones contestables, nombradas explícitamente — blancos para la revisión del gate), contexto de dominio aplicado (si hubo `domain_context`), archivos a tocar, tests/build y el **contrato de verificación** en `## Verification`, siguiendo `reference.md` → "Producción del contrato de verificación". Para cada fila, el paso ejecuta el comando o realiza la observación sobre el commit base, escribe el estado observado y **nunca lo asume**. El esquema de la tabla sigue en `cross-implement/contrato-verificacion.md` → "La tabla"; la plantilla, en `reference.md` → "Plantilla de plan". El paso escribe `contract_procedure` en el header después de registrar el congelamiento, en el orden que fija la sede. **Sin placeholders:** nada de `TBD`, `TODO`, "agregar manejo de errores apropiado" o "etc." colgados — cada sección con contenido real (ruta, comando, enfoque). Si algo no se puede precisar todavía, falta `clarify`; no es un placeholder.
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
   # sequence_contract_version: 1  # se agrega al iniciar implement, antes de crear el ledger
   # implement_mode: workers        # solo en `workers`: el modo lógico, que el ledger proyecta a `blocks`
   # implementer_family: claude     # solo en `workers`: la familia congelada del implementador
   # implementer_profile: { model: sonnet, effort: medio }  # solo en `workers`: el perfil congelado del rol `implement`
   created_at: 2026-01-01T12:00:00-03:00
   ---
   ```

   Al crear el `plan.md`, escribir `status: planned`.
4. **STOP** — si la **revisión cross-model** está activa (ver "Revisión cross-model"), ejecutar `cross-review` sobre `plan.md` con `spec` + `domain_context` resuelto como contexto (con co-exploración: sumar los **índices + la síntesis** de `explore` y de `counter-plan` — nunca los `detail-*` — ver "Co-exploración cross-model") antes de presentar (en *normal*, sobre plan + tasks juntos). En *trivial* y *normal*, antes de presentar este STOP, ejecutar el "Procedimiento previo al último gate". Presentar el plan (con el resumen de crítica, si lo hubo) y pedir aprobación. En *trivial* este es el último gate antes de implementar (tasks inline en `## Tasks`). En *normal*, **antes del STOP se ejecuta el paso `tasks`** (se escribe `tasks.md`) y este gate presenta **plan + tasks juntos** (un solo STOP, sin gate extra). En *complejo*, el plan se aprueba acá y el gate de `tasks` es independiente y posterior (ver paso `tasks`). En *trivial* y *normal* este es el último gate aplicable: al aprobarlo, pasar `status` a `tasks-ready`. En *complejo* todavía falta el gate de `tasks`: al aprobar el plan, pasar `status` a `plan-approved`. Si este es el **último gate antes de implementar** (*normal*) y el modo de implementación resuelto es `ask`, incluir en el **mismo STOP** la pregunta del modo: ¿implemento acá (inline), delego a la otra familia y yo reviso el diff (`cross`), o delego a la familia del conductor con su perfil por rol (`workers`)? Las dos delegaciones se ofrecen solo si su capacidad está disponible (ver `implement` → "Modo de ejecución"; sin gate extra; en *trivial* no se pregunta: default `inline`, y `workers` ni siquiera se ofrece).

### Procedimiento previo al último gate

| Complejidad | Gate que lo ejecuta |
|---|---|
| trivial | gate del plan |
| normal | gate conjunto de plan y tasks |
| complex | gate propio de tasks |

Antes del STOP indicado, aplicar la vigencia frente al HEAD y ejecutar el conjunto canónico de
predicados de `cross-implement/contrato-verificacion.md` → "El gate previo al dispatch" sobre la
versión vigente. La referencia es al conjunto, no a una cantidad fija de comprobaciones; incluye
las invariantes que impiden ablandar una versión y la proyección solo-lectura del multi-repo.

La aprobación del último gate aplicable completa el orden normativo de `reference.md` → "Producción
del contrato de verificación": el conductor registra `aprobar`, registra `congelar` en la bitácora,
escribe el marcador y recién entonces ejecuta
`python_skill <skill_dir>/scripts/promocion-tasks-ready.py <plan> <bitácora>`. El script muta el plan
y promueve el estado; un veredicto distinto de cero impide promover. Es un cambio de naturaleza
respecto de las demás guardas del repositorio, que solo verifican. Antes de
despachar, volver a ejecutar el conjunto completo con esa constancia.

### Ciclo de `status` (estado persistido del flujo)

`status` vive en el header del `plan.md` y es la **fuente de verdad de en qué fase quedó el flujo**. La skill lo actualiza al cerrar cada paso, y `resume` lo lee para saber dónde retomar:

```
planned → plan-approved → tasks-ready → implementing → verified → committed → pushed → done
          (solo complejo)
(open-pr opcional: pushed → pr-open → done)
```

- `planned` — `plan.md` escrito, con aprobación pendiente.
- `plan-approved` — el plan de un flujo complejo fue aprobado; las tasks todavía no. **Se escribe si y solo si `complexity: complex`**: en *trivial* y *normal* el gate del plan es el último aplicable, así que el ciclo pasa de `planned` a `tasks-ready` sin escala.
- `tasks-ready` — plan aprobado; en *normal*/*complejo*, tasks aprobadas. Listo para implementar.
- `implementing` — implementación en curso (ver tasks marcadas para el detalle fino).
- `verified` — todos los AC en verde (resultado persistido, ver `verify`).
- `committed` / `pushed` — commit hecho / rama publicada.
- `pr-open` — (opcional) PR creado por `open-pr`; la URL queda en `pr_url`. Solo aparece si se abrió el PR desde el flujo.
- `done` — confirmado por el usuario como probado y correcto; dispara `archive`.

Antes de que exista `plan.md` (fase `specify`/`clarify`, o el gate de Jira), no hay `status` en `plan.md`: la fase se infiere de los archivos presentes (`spec.md` sin `plan.md` → todavía en `specify`/`clarify`) y, si hubo una pausa, del frontmatter del `handoff.md` (`phase`/`gate_status`; ver "`handoff.md` (retomado del flujo)"). Una vez que existe `plan.md`, `status` manda.

## Paso `tasks` → GATE (propio en *complejo*; junto al plan en *normal*)

**Objetivo:** descomponer el plan en tareas atómicas, ordenadas, verificables y **autosuficientes** — ejecutables en una sesión fresca sin tener que re-deducir el diseño ni elegir otro enfoque. Dos consumidores **dependen** de esa autosuficiencia: la **Vía B** de `implement` (bootstrap en sesión fresca, también la que corre el agente delegado de `sdd-orchestrator`) y el modo **`cross`**, donde el propio flujo congela las tasks como work order y `cross-implement` las recibe congeladas para mandarlas a otra familia. En ambos, quien ejecuta no estuvo en la conversación que produjo el plan: una task que solo se entiende con ese contexto está mal escrita.

1. **Dónde se escriben** (según complejidad): en *normal* y *complejo*, en `tasks.md` separado; en *trivial*, inline en la sección `## Tasks` del `plan.md`. **Siempre anunciar la ruta exacta** donde quedaron ("Tasks en `.plans/<id>/tasks.md`" o "en `plan.md` → sección `## Tasks`"). Nunca dejar al usuario adivinando si hay tasks o dónde están.
2. **Formato detallado** (plantilla en `reference.md` → "Plantilla de tasks"): cada task lleva checkbox `- [ ]`, acción concreta, y los campos **Por qué** (qué AC habilita / intención), **Archivos** (rutas a tocar, con `path:line` de reúso identificado en `analyze`), **Pasos** (para cambios de comportamiento, recomendar el punto testeable o **Seam** + test que debería fallar primero + comandos acotados; para tareas mecánicas, pasos directos), **Verificar** (el `Vn` de la fila del contrato que prueba el AC — solo el ID, sin repetir comando ni esperado), y la(s) referencia(s) `AC-n`. Los snippets de los Pasos son **ilustrativos** del enfoque —firma, estructura, casos a cubrir—, **no** la implementación final completa. Cuando una task crea o usa una interfaz (función, endpoint, contrato) que otra task necesita, agregar **Produce** / **Consume**: declarar la **firma exacta** en la task que la *produce* y referenciarla desde la que la *consume* (DRY: no repetir la firma en cada task). Es lo que vuelve la task autosuficiente: **una interfaz que ninguna task declara, nadie la reconstruye por adivinanza**. `Consume` también apunta a un **bloque global** —una sección de `tasks.md` que ninguna task produce— con las palabras literales `bloque global` seguidas de su slug entre backticks (`reference.md` → "Plantilla de tasks"). Cada task sigue siendo **atómica** (un cambio coherente). En tasks puramente mecánicas (config, copy, wiring sin seam testeable) los Pasos pueden colapsarse a 1‑2 líneas y declarar que la evidencia vendrá de `verify`.
3. **Self-review antes del gate** (el conductor lo corre y reporta en una línea):
   - **Cobertura de spec** (cross-artifact check): cada `AC-n` tiene ≥1 task y ninguna task carece de AC. Reportar huérfanos antes del gate.
   - **Scan anti-placeholder:** ni plan ni tasks tienen `TBD`, `TODO`, "agregar X apropiado", "similar a la Task N" o "etc." colgados; cada paso con contenido real (ruta, comando, firma). Un hueco que no se puede precisar es señal de que falta `clarify`.
   - **Consistencia de interfaces:** lo declarado en **Produce** coincide exacto con quien lo **Consume** (mismo nombre, misma firma) — el desajuste rompe a quien implemente sin el contexto de esta conversación.
   - **Existencia y pertinencia AC ↔ fila del contrato:** comprobar la existencia bidireccional —ni AC sin fila ni fila sin AC— y la pertinencia; aplicar ambas según `cross-implement/contrato-verificacion.md` → «El gate previo al dispatch», incluida «Pertinencia: poder discriminante por fila», antes de llegar al dispatch.
4. **STOP** — en *complejo* (gate propio), si la **revisión cross-model** está activa para `tasks` (ver "Revisión cross-model"), ejecutar `cross-review` sobre `tasks.md` con `spec`+`plan`+`domain_context` resuelto como contexto antes de presentar. En *complejo*, antes de presentar este STOP, ejecutar el "Procedimiento previo al último gate". Presentar las tasks (con el resumen de crítica, si lo hubo) y pedir aprobación. En *complejo* es un gate **propio** (STOP independiente tras el plan). En *normal* las tasks se presentan **junto al plan** en el gate de `plan` (sin STOP adicional; la revisión, si aplica, ya cubrió plan+tasks ahí). Al aprobarlas, pasar `status` a `tasks-ready` — en *complejo* se entra a este gate desde `plan-approved`, y es el paso que lo cierra. En *complejo*, si el modo de implementación resuelto es `ask`, incluir en este **mismo STOP** la pregunta del modo: ¿inline, delegación cross-model con revisión del conductor (`cross`), o delegación same-family con perfil por rol (`workers`)? Las dos delegaciones, solo si su capacidad está disponible (ver `implement` → "Modo de ejecución"; sin gate extra).

## `handoff.md` (retomado del flujo)

Documento de **retomado** del flujo —"dónde quedé, qué decidí y cómo sigo"— en `.plans/<id>/handoff.md` (frontmatter + narrativa): todo el estado del flujo queda junto en `.plans/<id>/` —donde `resume` ya escanea—, sin partirlo en carpetas aparte ni acoplar `sdd-flow` a otra skill. Es local y untracked como el resto (regla #10).

**Se escribe/actualiza en dos situaciones:**
- **Sub-paso `pause`** — al dejar un flujo a medias para seguir después o en otra sesión (cualquier fase, no solo `implement`).
- **Paso `publish-spec`** — el gate de aprobación en Jira es una pausa esperando a un tercero; agrega los campos del gate (ver su paso).

**Estructura:** frontmatter YAML con los campos máquina + cuerpo narrativo legible. Plantilla completa en `reference.md` → "Plantilla de `handoff.md`".

```yaml
---
phase: awaiting-jira-approval   # gather-context | specify | clarify | awaiting-jira-approval | implementing | ...
# snapshot de gather-context (presente mientras NO exista plan.md):
complexity: normal              # trivial | normal | complex
change_type: feat               # feat | fix | refactor | ...
branch_prefix: feature          # el {type} ya resuelto
slug: export-csv
base_branch: master             # rama base resuelta (con override de base, la rama de la que se corta)
overrides: { branch_prefix: null, base_branch: null, cross_review: null, implement_mode: null, jira_approval: null }
# puntero al ledger de la búsqueda (solo en una pausa durante `gather-context`):
# antecedentes: .plans/<id>/antecedentes.md   # PUNTERO, no copia: términos, fuentes y fingerprints viven solo ahí
# campos del gate de Jira (solo si es una pausa por aprobación externa):
# gate_status: awaiting         # awaiting | changes-requested | approved
# parent_key: ABC-123 · subtask_key: ABC-145 · cloud_id: <uuid>
# jira_subtask_url: https://<tu-site>.atlassian.net/browse/ABC-145   # la usa `open-pr` para linkear la spec
---
```

### Precedencia con `plan.md` (sin doble fuente de verdad)
- **`plan.md` existe** → su `status` / `wip_commit` / marcas `[x]` son la **verdad de fase**. Durante
  una secuencia durable activa, el clasificador canónico de secuencia decide primero si esa fase puede
  continuar: `status` solo enruta cuando el diagnóstico es terminal o no aplica. `handoff.md` solo
  aporta la **narrativa** (estado, decisiones, próximos pasos) y los **overrides de la corrida** (que
  de otro modo no se persisten).
- **`plan.md` NO existe** (fase `specify`/`clarify`, o el gate de Jira) → el **frontmatter del `handoff.md`** lleva el snapshot operativo (complejidad, tipo de cambio, prefijo) y es la fuente de verdad de esa ventana pre-`plan`.

`handoff.md` **nunca contradice** a `plan.md`: lo complementa y cubre la ventana donde antes no había nada persistido (hoy, pausar en `specify`/`clarify` pierde la narrativa). Al retomar, `resume` lo lee respetando esta precedencia.

## Paso `resume` (retomar un flujo / cambiar de contexto)

Punto de entrada cuando vuelves a un flujo ya empezado — en una sesión nueva, o tras haber saltado a otra cosa. Funciona **aunque estés posicionado en otra rama**, porque `.plans/` es local y visible desde cualquier rama, y cada `plan.md` sabe a qué `branch` pertenece y en qué `status` quedó.

### Listar / elegir el flujo
1. Si el usuario nombró un flujo (`<id>` o ruta `.plans/<id>/`), usar ese. Si dijo algo genérico ("¿en qué quedé?", "qué flujos tengo"), **listar** los flujos activos (excluir `.plans/archived/`): para los que tienen `plan.md`, leer su header; para los **pre-`plan`** (sin `plan.md`: `antecedentes.md`, `spec.md` y/o `handoff.md`, en cualquier combinación), leer el `handoff.md` (`phase`/`gate_status`) **y también `antecedentes.md` si está**, de donde sale el estado de la búsqueda. Un flujo pausado durante la búsqueda puede tener **solo** ese archivo, y un cierre pre-spec deja ahí su `busqueda: terminal`: sin abrirlo no hay con qué mostrar ese estado ni cómo distinguir un cierre deliberado de un flujo abandonado. Mostrar tabla `id · branch · estado · siguiente paso` —donde "estado" es el `status` del plan o, si no hay plan, la `phase`/`gate_status` del handoff (p. ej. "esperando aprobación Jira")—. Que el usuario elija.
2. Si `.plans/<id>/` **no** tiene `plan.md`, el flujo quedó pre-`plan`. **Leer `handoff.md` si existe** (narrativa + snapshot de `gather-context`: complejidad, tipo de cambio, prefijo, slug, rama base, overrides) — es lo que evita re-investigar el ticket o re-clasificar. Luego bifurcar, **en este orden**:
   - Si hay **`antecedentes.md` con `busqueda: in-progress`** —haya handoff o no— → la pausa ocurrió **durante la búsqueda de antecedentes**. La condición arranca por el **artefacto** y no por un campo del handoff a propósito: `pause` escribe el handoff solo cuando la pausa es **ordenada**, y una sesión que muere, un `Ctrl-C` o un cierre de terminal dejan el ledger a medio correr sin handoff ninguno. Retomar así:
     - **Recomputar los fingerprints** —los que declare `reference.md` → "Búsqueda de antecedentes", que es su única sede: enumerarlos acá crea una segunda que se desincroniza— y compararlos con los persistidos. Se re-corre **solo la unión** de las filas que indique la matriz de invalidación de `reference.md` → "Búsqueda de antecedentes"; las fuentes ya terminadas que ningún fingerprint invalidó **no se vuelven a correr**.
     - **Un parcial no es un resultado.** Con fuentes pendientes, el estado se completa antes de clasificar: leerlo como "no había nada" es el mismo error que la búsqueda viene a evitar.
     - **Un cierre pre-spec deja `busqueda: terminal` y no se ofrece como reanudable.** Es una decisión deliberada —el objetivo ya estaba cubierto—, y su ledger sobrevive como registro de qué se buscó y qué se encontró: sigue visible en el listado con ese estado, pero sin "siguiente paso".
   - Si tiene **`gate_status: awaiting`** (o `changes-requested`) → el flujo está en el **gate de Jira**; ir a "Gate de Jira (esperando aprobación externa)" abajo.
   - Si no (pausa común en `specify`/`clarify`, con `spec.md` ya escrita) → chequear si ya existe una rama del flujo (`git branch --list "*<id>*"`): si existe, la spec ya fue aprobada y `create-branch` ya corrió → confirmarlo con el usuario, posicionarse en esa rama (checkout seguro, como abajo) y retomar en `plan` (así `base_commit` se toma del HEAD correcto, no de la rama en la que estés posicionado). Si no hay rama, retomar desde `specify`/`clarify`, sin navegación de rama.

### Navegar a la rama correcta (checkout seguro)
3. Parsear el header del `plan.md` elegido: `id`, `branch`, `base_commit`, `complexity`, `status` (y `wip_commit` si está).
4. Si la rama actual != `branch` del header:
   - Antes de cambiar, exigir working tree **sin código sin commitear** en la rama actual: `git status --porcelain -- ':(exclude).plans' ':(exclude).specify'` vacío. Si hay cambios de código (p. ej. otro flujo a medias), **detener**: ofrecer commitearlos, el sub-paso `pause`, o `git stash` — nunca pisar ni arrastrar trabajo ajeno a otra rama.
   - Con el árbol limpio, `git checkout <branch>`. Los `.plans/`/`.specify/` untracked no bloquean el checkout ni se pierden.
   - Si `branch` no existe (fue borrada): avisar y ofrecer recrearla desde el commit base (`git checkout -b <branch> <base_commit>`).
5. Coherencia: `git merge-base --is-ancestor <base_commit> HEAD` (si no: avisar que la rama divergió y pedir confirmación).

#### Retoma durable antes del routing

Antes de recuperar WIP o enrutar por fase, capturar las seis autoridades y ejecutar el **clasificador
canónico de secuencia** de `reference.md` → “Recuperación de la secuencia”. Este diagnóstico es
read-only y ocurre después del checkout/header seguro: nunca resetea, marca tasks, publica ledger ni
adquiere ownership mientras decide qué estado observa.

1. Validar presencia, `schema_version` y forma del ledger. Inline, legacy, versión desconocida,
   documento corrupto y ledger obligatorio ausente son clases distintas; no inferir bloques desde
   commits o tasks.
2. Capturar ledger, recibo, Git, plan/tasks, proceso/sobre y owner preservando procedencia y frescura.
3. Clasificar exactamente un cutpoint/terminal. Cero o múltiples predicados, evidencia contradictoria,
   cese incierto u owner obsoleto sin fencing fallan cerrados y no mutan.
4. Sin secuencia aplicable o con `inline-pass-through`, permitir la retoma normal. Este último solo
   acredita que inline no tiene un efecto externo parcial: no inventa bloques. **Si el header trae `wip_commit`,**
   recién ahora recuperar el trabajo pausado según `pause`. Para un terminal, enrutar
   por su subtipo, no por `plan.status`: `completed` habilita la retoma normal solo con una fase coherente con el commit
   final; si la fase quedó atrás, continúa como C12 para sincronizarla idempotentemente. `rolled_back`
   y `abandoned` se detienen y requieren una decisión humana explícita para iniciar otra secuencia;
   `suspended` vuelve a diseño.
   Ninguno recupera WIP ni continúa automáticamente una implementación anterior.
5. Con `recoverable`, `resume agrega la propuesta` completa —digest de evidencia, efectos ordenados y
   terminal esperado— y hace STOP en el único gate humano. Tras el sí: demostrar cese, adquirir
   ownership, reclasificar, exigir el mismo digest y ejecutar reconciliaciones idempotentes. Si algo
   cambió, detener y pedir nueva confirmación.
6. Con `blocked`, `inline-unsupported`, `legacy-unsupported`, `unsupported-version`,
   `corrupt-ledger`, `missing-required-ledger` o `conflict:<source>`, mostrar clase + evidencia y
   detener sin recuperar WIP ni enrutar por `status`.

### Routing por `status`
6. Leer `status` y retomar en el punto exacto, **confirmando el resumen extraído** antes de actuar:

   | `status` | Dónde retoma |
   |---|---|
   | `planned` | el plan no está aprobado → **gate del plan**, sea cual sea la complejidad |
   | `plan-approved` | plan aprobado, tasks no (solo *complejo*) → **gate de `tasks`** |
   | `tasks-ready` | `implement` (Paso común) |
   | `implementing` | `implement`, continuando desde la primera task `[ ]` (y el WIP, si hay `wip_commit`) |
   | `verified` | AC ya en verde; falta commit → `implement` desde el gate de revisión manual |
   | `committed` | falta push → sub-paso `push` |
   | `pushed` | completo en disco; ofrecer `open-pr` (si no hay `pr_url`) o `archive` |
   | `pr-open` | PR ya creado (`pr_url` en el header); no re-ofrecer `open-pr` — ofrecer `archive` si lo das por probado |
   | `done` | ya cerrado; si sigue fuera de `archived/`, ofrecer archivarlo |

   **Un `planned` con `tasks.md` presente retoma igual en el gate del plan.** Es la forma que escribía un flujo complejo antes de que existiera `plan-approved`, y también la que produce un *normal* reclasificado a complejo después de escribir las tasks: en ninguno de los dos casos el artefacto dice si el gate del plan llegó a darse. Ante esa duda se repite el gate, que es barato; inferir que ya se dio saltearía un gate que quizá nadie aprobó.

   Al retomar en `implement` (`tasks-ready`/`implementing`), **re-resolver el modo de ejecución** (override > `implement_mode` > preguntar; ver `implement` → "Modo de ejecución"). Las tasks ya marcadas `[x]` no se repiten en ningún modo.

#### Flujos heredados: los que nacieron antes de la búsqueda de antecedentes

Un flujo abierto **antes** de que `gather-context` buscara antecedentes llegaría a implementar sin que
nadie haya mirado si el trabajo ya existía. La adopción es por estado, y su alcance es cerrado:

| `status` al retomar | Qué pasa |
|---|---|
| `planned` · `plan-approved` · `tasks-ready` · `implementing`, **sin** ledger de búsqueda | **ningún commit** hasta que la búsqueda haya corrido y su salida esté reconciliada |
| `verified` o posterior | **explícitamente excluido.** El trabajo ya está hecho y verificado; bloquearlo no evita nada y solo frena un flujo terminado |

**Arranca en `planned`, y no en `tasks-ready`, porque `resume` corre una sola vez.** Un flujo heredado retomado en `planned` entra al gate del plan y sigue **en esa misma sesión** a `tasks` → `implement` → commit sin volver a pasar por acá: una guarda que empezara en `tasks-ready` nunca llegaría a evaluarse, y el commit saldría sin que nadie hubiera buscado.

**Qué significa reconciliar, y no queda a criterio de quien implementa.** Por salida de la matriz:

| Salida de la búsqueda | Qué se reconcilia |
|---|---|
| **sin hallazgo** | desbloquea sin tocar ningún artefacto |
| **relacionado** | se anota en el bloque declarativo y desbloquea; el alcance queda intacto |
| **parcial acreditado** | **reabre el gate de la spec** con el objetivo **residual**, y las tasks que cubrían la parte ya hecha **se retiran** |
| **total vigente** | **detiene el flujo** y ofrece cerrarlo; reformular exige confirmación humana |
| **reformular** | el trabajo previo es recuperable sin conflictos: **obliga** a reformular el objetivo, con confirmación humana, y desbloquea sobre el objetivo nuevo |
| **checkpoint** | hay una ref recuperable **con conflictos declarados**: va al checkpoint del paso 6 con el número a la vista, y desbloquea con la decisión humana registrada — nunca recorta por su cuenta |
| **incognita** | un candidato quedó `no verificado`: entra como contexto, el alcance queda intacto y desbloquea |

**La condición de desbloqueo es observable, no una declaración de buena fe:** `busqueda: complete`,
**más** la salida registrada en el bloque declarativo, **más** —si hubo reapertura— la aprobación del
gate correspondiente. Una marca de "reconciliado" no alcanza: es exactamente la forma que permite
marcarlo hecho y seguir, que es el no-op más barato y deja el problema intacto.

### Guarda de retomado con bloques en vuelo

La guarda de cuatro superficies queda absorbida por el clasificador canónico de secuencia: HEAD y
cadena Git, recibo, marcas y ledger se evalúan junto con proceso/sobre y owner. Continúan siendo
casos críticos las tasks `[ ]` cuyo contenido ya vive en un commit y el aplastado parcialmente
transformado; ahora se distinguen los desfases legítimos C1-C12 de `conflict:<source>` y se propone
solo la reconciliación declarada por `reference.md` → “Recuperación de la secuencia”.

### Sub-paso `status` (alias de listado)

`/sdd-flow status` no introduce un estado nuevo: es un alias read-only de `resume` en modo listar.
Muestra los mismos datos (`id · branch · estado · siguiente paso`) y, si se pasa un `<id>`, resume
solo ese flujo. La fuente de verdad sigue siendo `plan.md` (`status` + marcas `[x]`) o
`handoff.md` en la ventana pre-`plan`.

### Sub-paso `doctor` (diagnóstico read-only)
Valida la coherencia de un flujo **sin arreglar nada ni escribir archivos**: resuelve el flujo igual
que `resume`, consume el **clasificador canónico de secuencia** y reporta clase, fuentes y conflictos.
`doctor solo reporta`; `resume agrega la propuesta`, el gate y la ejecución. `OK`/`WARN`/`FAIL` sigue
siendo la severidad exterior, no una segunda clasificación. Los demás checks, el formato de salida y
qué cuenta como ruido del working tree: `reference.md` → "Doctor read-only".

### Gate de Jira (esperando aprobación externa)
Con `gate_status: awaiting`/`changes-requested` en `handoff.md` el flujo está parado esperando que
el TL/PO aprueben la subtarea `SPEC: …`; al aprobarse sigue normal a `create-branch` → `analyze` →
`plan`, y el `analyze` corre **después** de la aprobación a propósito. Las tres resoluciones, la
detección por MCP, el loop de observaciones y las escrituras con su STOP de write-safety:
`reference.md` → "Aprobación externa de la spec (Jira)".

### Sub-paso `pause` (dejar un flujo a medias de forma segura)
Aplica en **cualquier fase** del flujo, no solo `implement`. Al pausar:

1. **Escribir/actualizar `handoff.md`** (ver "`handoff.md` (retomado del flujo)"): **la `phase` en la que se pausó**, estado actual, próximo paso, decisiones/criterio asumido y —si `plan.md` aún no existe— el snapshot de `gather-context` (complejidad, tipo de cambio, prefijo, slug, rama base, overrides de la corrida). Es lo que permite retomar en una sesión nueva sin re-investigar el ticket. **Si la pausa ocurre durante la búsqueda de antecedentes**, la `phase` es `gather-context` y el frontmatter lleva además el **puntero** `antecedentes:` a su ledger: son los dos campos con los que el retomado reconoce esa rama, y sin ellos el flujo cae en la de `specify`/`clarify` —que da por escrita una spec que no existe— dejando huérfano el ledger a medio correr.
2. **Si hay código sin commitear** en la rama del flujo (típicamente en `implement`): **WIP commit en la propia rama** (no `git stash`: el stash es global y se confunde/pierde entre flujos; un commit viaja con su rama): stagear solo `code_touched` y `git commit -m "wip(<id>): pausa sdd-flow"`. Este WIP es **inline a propósito** (no usa `/commit`): es plumbing mecánico y descartable que `resume` deshace con `git reset`, no un commit de contenido. Registrar en el header del `plan.md`: `status: implementing` + `wip_commit: <sha>`. Si además quedan archivos **ajenos** dirty (fuera de `code_touched`), avisarlo: no entran al WIP y quedan sueltos en el working tree — un checkout posterior puede arrastrarlos. (En fases sin `plan.md` ni código —`gather-context`, `specify`/`clarify`, gate de Jira— este paso no aplica: alcanza con el `handoff.md`.)
3. Avisar que quedó pausado y cómo retomarlo (`resume` con el `<id>`). Al retomar, si hubo WIP commit, `resume` lo deshace dejando los cambios en el working tree **sin** stage (`git reset <wip_commit>^`, reset mixed — así el staging selectivo del Paso común sigue valiendo), **reconstruye `code_touched`** desde los archivos del WIP (`git show --name-only --pretty=format: <wip_commit>` — el set en memoria no sobrevive a la sesión) y limpia `wip_commit` del header. **Guard previo:** solo resetear si `git rev-parse HEAD` == `wip_commit`; si no coinciden (hubo commits posteriores al WIP), no tocar la historia — avisar y dejar que el usuario decida cómo integrar el WIP.

## Paso `implement`

### Vía A — sesión actual
El usuario aprobó el último gate activo. Ir al "Paso común".

### Vía B — sesión fresca / bootstrap
Disparador: `/sdd-flow implement <ruta-carpeta>` (p. ej. `.plans/ABC-123/`), o llegada desde `resume` con `status` `tasks-ready`/`implementing`. La carga de contexto, la navegación a la rama y la validación de coherencia git las realiza el paso `resume` (arriba); además, cargar la spec y las tasks:

1. Leer `plan.md` (**obligatorio**: contiene el header YAML). Leer `spec.md` y `tasks.md` **solo si existen**; si no, tomar la spec y/o las tasks de las secciones embebidas `## Spec` / `## Tasks` del propio `plan.md`. La `complexity` del header indica qué esperar: `trivial` → todo embebido en `plan.md`; `normal` → `spec.md` + `tasks.md` separados; `complex` → `spec.md` + `tasks.md` separados (con gate de tasks propio).
2. Confirmar el resumen extraído (incluido el `status` y las tasks pendientes) antes de avanzar al "Paso común".

### Modo de ejecución (`inline` | `cross` | `workers`)

Ortogonal a las Vías A/B: se llegue por la sesión actual o por bootstrap, las tasks se ejecutan en uno de tres modos.

- **`inline`** — la propia sesión implementa cada task (el comportamiento de siempre). El contexto acumulado ayuda, pero arrastra el ruido de specify/plan/cross-review.
- **`cross`** — la implementación se delega por la partición aprobada a la skill **`cross-implement`**, un bloque por invocación, con un implementador seleccionado y escritura acotada al repo; el conductor revisa cada delta como un PR ajeno y corre la prueba él mismo. Con selección cross-family, implementador y revisor del código son de familias distintas; con selección same-family se conserva independencia de proceso y se declara el costo. Requiere la skill `cross-implement` instalada **y** el CLI de la familia elegida disponible — descubrir ambas capacidades; si falta alguna, el modo no se ofrece.
- **`workers`** — como `cross`, pero con la familia del implementador **fijada a la del conductor** y su perfil resuelto por la cadena de `reference.md` → "La cadena de resolución del perfil". Delega en `cross-implement` sin sumar un punto de despacho propio, y la familia viaja como override **acotado a esa invocación**: el inventario de la corrida no se toca. Se ofrece solo en flujos **no triviales** y solo con la capacidad presente; un override explícito vale igual en trivial. Contrato completo —herencia, partición, congelado, retoma y compatibilidad— en `reference.md` → "El modo `workers` de implementación". **Conserva la familia a propósito y por eso no rompe la correlación de errores:** el contrapeso same-family de `cross-implement` es obligatorio en su salida.

Resolución (misma precedencia que el resto de overrides SDD): **override conversacional de la corrida** ("implementa acá" / "implementa con Codex") > **`implement_mode`** del `config.yml` > default `ask` (preguntar en el último gate antes de implementar, dentro del mismo STOP — nunca un gate extra; la opción `cross` se incluye en la pregunta solo si su capacidad está disponible). Excepción: en *trivial* el default efectivo es `inline` sin pregunta (1-2 tasks mecánicas no ameritan delegar — delegar ~<20 líneas cuesta más que hacerlas); el override conversacional sigue valiendo. Si falta la capacidad de `cross`, avisar en una línea y seguir `inline` (degradación estándar, regla 6).

> **Config heredada con `implement_mode: subagent`.** Ese modo **se retiró**. Al resolver el modo,
> un `config.yml` que todavía lo declare **detiene el flujo con un error de migración** que nombra el
> valor retirado y pide elegir entre `ask`, `inline`, `cross` o `workers`. **No hay fallback silencioso:** no se
> degrada a `inline` ni se ignora la clave — un valor inexistente que el flujo acepta calladamente es
> una corrida ejecutándose en un modo que nadie eligió.

### La partición en bloques y su aprobación

Cuando el modo resuelto antes del último gate es `cross` o `workers`, el conductor prepara una
**propuesta de partición** y la presenta en el gate ya existente, sin gate nuevo. En complejidad `complex`, se
presenta en el gate propio de `tasks`; en `normal`, acompaña plan y tasks en el gate conjunto. Las
tasks y la partición se aprueban de forma atómica en el mismo STOP, y el flujo no despacha ningún
bloque antes de esa aprobación.

El grafo declarado es insumo, no autoridad para derivar la partición: el humano decide el corte. La
propuesta declara, por bloque, las tasks que lo componen, por qué se cortó ahí y qué no pudo verificar
del grafo. En particular, enumera las tasks que no declaran dependencias, sin afirmar que por eso no
las tengan. La propuesta puede contener un solo bloque cuando su justificación explica por qué no
conviene partirlo.

El conductor, antes de presentar, comprueba mecánicamente que la unión de los bloques es igual al
conjunto de tasks pendientes, que los bloques son disjuntos, que todos los IDs existen en `tasks.md`
y que ninguna task ya `[x]` está incluida. También rechaza una propuesta con un bloque sin ninguna
fila elegible; ese bloque se fusiona con el siguiente. Si falla cualquiera de estas invariantes, la
propuesta no se presenta.

Las referencias declaradas siguen siendo hechos: se rechaza mecánicamente toda referencia
`Produce`/`Consume` inválida y toda arista `Consume` dirigida a un bloque posterior. Que el grafo sea
incompleto no vuelve opcional lo que declara. La aprobación humana cubre solo lo que el grafo no
permite comprobar, nunca una contradicción observable.

`resume` re-resuelve el modo de ejecución —salvo en `workers`, donde la familia y el perfil salen del
congelado del header y no de una re-resolución (`reference.md` → "El modo `workers` de
implementación")—. Si el flujo llegó a `tasks-ready` sin partición aprobada y después elige `cross` o
`workers`, solo hay dos salidas válidas: fallback monolítico sobre el work order completo,
o reapertura explícita del gate existente para aprobar una propuesta. La ausencia de una partición no
autoriza despachos por bloques ni convierte la capacidad `cross` en un error.

### Paso común — Implementación

1. **Tracking de archivos (por capacidad, no por nombre de tool).** Alimentado por **cualquier** herramienta o comando que cree/modifique/borre archivos (las tools de edición del entorno —cambian entre Claude Code, Codex, etc.— o `mv`/`rm`/`cp` en shell), mantener tres sets de rutas:
   - `code_touched` — código/producto que tocó la skill (candidatos a commit).
   - `sdd_local` — `.plans/`, `.specify/` (locales, nunca se commitean).
   - `generated` — lo que **el ignore del repo** marca como generado (mismo criterio del paso 6, y ahí está su definición: no se repite acá para que no puedan divergir); nunca se commitean.
2. **Aplicar cambios** según el **modo de ejecución** resuelto (ver arriba). Antes de crear el ledger,
   persistir `sequence_contract_version: 1` en el header del `plan.md`; después crear el ledger y solo
   entonces poner `status: implementing`. Ese orden permite distinguir una inicialización v1
   interrumpida de una corrida legacy aunque el ledger falte. En todos los modos: marcar cada task
   `- [x]` al completarla (es el detalle fino del progreso que `resume` usa para saber por dónde seguir)
   y reutilizar lo identificado en `analyze`.
   El productor del ledger es `sdd-flow` en los dos modos. Antes de escribirlo, cargar
   `reference.md` → "El ledger de secuencia" y "Vocabulario de condiciones", y
   `cross-implement/ownership.md` → "Terminales de secuencia".
   - **Modo `inline`:** la propia sesión implementa cada task. Para tasks de comportamiento con un
     seam testeable, seguir los Pasos roja-verde propuestos en `tasks.md` (test que debería fallar
     → implementación mínima → test verde). Si la task es mecánica o no tiene seam razonable, no
     inflar el plan: la garantía vive en `verify`, que exige evidencia fresca y, cuando haya test
     ligado al AC, test con dientes vía revert-to-confirm.
     Antes de escribir el ledger, leer `reference.md` → "Escritura del ledger".
   - **Modos `cross` y `workers`:** invocar la skill **`cross-implement`** (Skill tool) con `work_order: .plans/<id>/` y el bloque aprobado como alcance parcial (en retomados, las tasks ya `[x]` quedan fuera), `working_dir` = raíz del repo, `proof_cmd` como **lista ordenada** con los mismos comandos que el paso 3 corre —`test_cmd` (acotado con `test_scope_hint` si aplica), `build_cmd` y `lint_cmd`—, **en ese orden y omitiendo los que no estén configurados**; el render de esa lista, y qué pasa cuando va vacía, los fija `cross-implement/reference.md`, y `execution` / `max_fix_rounds` / `deadline` **resueltos del bloque `cross_implement` del `config.yml`** (con los defaults de la skill como fallback: `execution: auto` → por tamaño del bloque, `max_fix_rounds: 2`, `deadline: 1800`). La skill delega ese bloque al implementador seleccionado (escritura acotada, nunca commitea) y guía la revisión del conductor: diff completo como PR ajeno, archivos declarados vs `git status` (alimenta `code_touched`, regla 8), prueba corrida por el conductor, y fix loop acotado reanudando la misma sesión. Al aceptar el bloque, el conductor atribuye hunks a tasks y aplica la secuencia canónica de `reference.md` → "Transición entre bloques" y "Formato del recibo de partición"; el drift fuera del work order se revierte o se declara en `## Extras`. **El tope de diseño de esta skill manda:** 3 fallos de la misma falla = volver a `plan`/`specify`, aunque queden fix rounds (ver paso 3). Si la skill devuelve `UNAVAILABLE` o `PARTIAL`, el conductor solo toma el trabajo restante cuando el cese está confirmado y la cosecha terminó; con cese incierto, detiene la secuencia. **Precondición fail-closed:** si el asset instalado no declara `SCOPE-CAPABILITY: v1` con su ranura completa, estos modos no se ofrecen. El detalle del contrato vive en `cross-implement` (dependencia blanda: sin ella, este modo no existe). **En `workers`** se agrega una sola cosa a esa invocación: la familia del implementador se fija a la del conductor como **override acotado a esa invocación** —el `family_inventory` de la corrida no se toca— y su perfil sale de la cadena del rol `implement`. El modo lógico, la familia y ese perfil quedan congelados en el header del `plan.md`, y el ledger sigue siendo `mode: blocks` (`reference.md` → "El modo `workers` de implementación").
     Antes de escribir el ledger, leer `reference.md` → "Escritura del ledger".
   Los pasos 3-10 de abajo (tests+build completos, `verify` de AC, revisión manual, staging, commit, push, PR opcional) los ejecuta **siempre el conductor en esta sesión**, en todos los modos: los STOPs no funcionan dentro de un subagente ni de un implementador delegado.
3. **Tests + build** con los comandos detectados/configurados (+ `lint_cmd` si está configurado). Acotar tests al código tocado si el runner lo permite (`test_scope_hint`). **Un fallo que ya estaba en `base_commit` no es un fallo de este flujo**, y confundirlos traba el paso: en modo `cross` el bloque se acepta por "no empeoró" contra su base, así que un linter que venía rojo cruza la aceptación y llegaría acá a bloquear por algo que el flujo no causó. Ante un fallo, primero comprobarlo sobre `base_commit` —el mismo comando, en un worktree detached que se descarta— y **solo el fallo nuevo bloquea**. Esa comparación exige dos condiciones, y sin ellas clasifica al revés justo en el caso peligroso. **Una: el comando tiene que ser aplicable en la base.** Si viene acotado por `test_scope_hint` a un archivo que este flujo creó, en `base_commit` ese archivo **no existe** y el runner sale distinto de cero por "no tests found" o por un error de carga — no porque el test fallara. Leerlo como "ya fallaba" deja pasar hasta el commit un test nuevo genuinamente en rojo. Cuando el alcance incluye rutas que no existen en `base_commit`, se compara con el comando **sin acotar**, o el fallo se trata como **nuevo**. **Dos: tiene que fallar por la misma causa.** Un exit code distinto de cero no distingue "el mismo fallo" de "otro fallo" ni de "el comando no llegó a correr": lo que se compara es el fallo concreto —el test que falla, la regla del linter, el error del build—, no el código de salida. El preexistente no se arregla de callado ni se declara como `E-n`: `## Extras` es para **cambios** que entran al commit, y un fallo que ya estaba no es un cambio de este flujo. Va al reporte final (paso 10), nombrando el comando y la evidencia de que ya fallaba en `base_commit`. Si es nuevo: **no commitear**; antes de parchar, aplicar **debugging sistemático** — formular **una** hipótesis ("creo que la causa raíz es X porque Y") y probarla mínimamente, en vez de prueba y error (skill de debugging sistemático si está disponible, o el método inline; ver `analyze` y `reference.md` → "Matriz de detección por capacidad"). Mostrar el error + la hipótesis, aplicar el fix y volver al paso 2. **Tope: 3 fixes fallidos de la misma falla = problema de diseño** — parar y volver a `plan`/`specify`, no intentar un fix #4.
4. **`verify` de los AC** (ver paso `verify`): recorrer `AC-1..N` con la gate function y marcar cumplido/no cumplido con evidencia fresca. Si alguno falla: **no commitear**, reportar y volver al paso 2 (con el mismo debugging sistemático del paso 3; mismo tope de 3 intentos), o a `plan`/`specify` si el gap es de diseño. Solo se commitea con **todos los AC en verde**; cuando lo estén, `verify` persiste el resultado y deja `status: verified`. Verificar antes del commit evita commits/push que después no cumplen lo pedido.
5. **Gate de revisión manual (STOP):** con tests+build OK y AC verificados, ofrecer revisar (levantar la app, `git diff`, repasar la sección Verification del plan) antes de commitear. Salteable con "commitea directo". Si `final_diff_review.mode` está `on`, o está `auto` y el flujo es `complex`/high-risk ejecutado `inline`, ofrecer en este mismo gate una revisión agregada del diff completo contra spec + estándares del repo: usar un reviewer fresco por capacidad (contrato completo —qué recibe, los ejes **SPEC** y **QUALITY**, y su formato de salida— en `reference.md` → "Revisión final de diff") o, sin esa capacidad, revisión liviana del conductor. Es una revisión de diff **same-model/de capacidad**, no conformance cross-model; el gate cross-model pre-commit sigue diferido salvo dolor concreto.
6. **Clasificar el working tree antes de stagear.** `git status --porcelain` y repartir cada ruta dirty:
   - **SDD local** (`.plans/`, `.specify/`) y **generados**: **nunca** se stagean ni cuentan como "código sin commitear". **La autoridad de qué es generado es el ignore del repo, y es la única**: una ruta que el ignore no excluye **no** es generada para este paso, por más que su nombre lo sugiera. Se decide con `git check-ignore`, no por inspección del nombre.
     - **Si el repo no tiene ignore versionado**, el conjunto de generados es **vacío**: todo lo dirty que no sea SDD local se trata como **código** y entra a la clasificación de abajo —o sea, se lista como ajeno y se pregunta—. No se infiere por tipo ni por nombre. Es más ruidoso y es deliberado: inferir "esto parece un cache" es lo que hacía que dos corridas del mismo paso sobre el mismo árbol clasificaran distinto la misma ruta. Si el ruido molesta, la salida es que el usuario cree su ignore; la skill no lo toca (regla 10).
     - Este paso decide **qué se stagea** y `no gobierna la medición del techo` de ningún repositorio: un proyecto puede tener su propio criterio para eso, con su propia sede y su propia lista. Son dos dominios disjuntos, y decirlo es lo que impide que se lean como discrepantes.
   - **Código:** `propios = code_touched ∩ (código dirty)`; `ajenos = (código dirty) − code_touched`. Sin ajenos → stagear `propios`. Con ajenos → listar ambos grupos y pedir elección (solo míos / incluir todos / cancelar). Nunca stagear ajenos sin confirmación.
   - **Extras (cambios sin AC).** Todo cambio que se decide incluir en el commit y **no mapea a ningún AC** se registra como `E-n` en la sección `## Extras (fuera de AC)` del `plan.md` antes de stagear — para que nada entre sin rastro (ver "Extras" abajo). Aplica a los `ajenos` que se eligen incluir y a cualquier ajuste oportunista que el conductor sepa que no corresponde a un AC (incluso dentro de un archivo `propio`). **No** aplica a corregir lo recién escrito por la skill (typo/ajuste dentro del código del feature): eso es parte de implementar bien el AC.
7. **Commit (transparente, confirmado, inline).** Con el staging armado (paso 6: solo `code_touched`; nunca `git add` adicional), **construir el mensaje inline** —sin depender de ninguna skill externa— siguiendo `reference.md` → "Construcción del mensaje de commit" (`type` desde `change_type`; scope = ticket resuelto del `id`/rama, u omitido si no hay; subject imperativo **en español** < 72 chars; **sin firmas ni `Co-Authored-By`**; con `commit_style: plain`, mensaje plano sin `type(scope)`). **Mostrar antes de ejecutar**: archivos staged + mensaje exacto + comando exacto. Si el usuario ya dijo "commitea directo" en el paso 5, proceder sin re-preguntar; si no, esperar su OK. **Ejecutar con heredoc** para que un body multilínea sobreviva intacto (plantilla en `reference.md`). Si hay `E-n` declarados en `## Extras`, listarlos como bullets en el **body** (el commit sigue siendo atómico del flujo). **Si el commit falla** (p. ej. hook de pre-commit): mostrar el error y **parar** — nunca reintentar con `--no-verify` salvo pedido explícito. Hecho el commit, poner `status: committed`.
8. **Push opcional (STOP):** detectar si la rama existe en remoto (host de Git si hay tool, o `git ls-remote --heads origin <branch>`). Ofrecer `git push -u origin <branch>` (primera vez) o `git push origin <branch>`. Ejecutar solo con confirmación afirmativa; tras el push, poner `status: pushed`.
9. **PR opcional (STOP).** Tras el push, ofrecer crear el PR hacia la **rama base del flujo**: `base_branch` del header si está (feature dependiente cortada de otra rama), si no `default_branch` (detalle en `reference.md` → "Apertura de PR (opcional, tras push)"). Si el destino es un `base_branch` que aún no se mergeó, avisarlo en el preview (el PR queda **stacked** sobre esa rama; conviene mergear la base primero o re-apuntar a `default_branch` cuando la base entre): probar el MCP de Bitbucket (sin él, degradar a PR manual — regla 6); evitar duplicados (si ya hay un PR abierto para la rama, ofrecer actualizarlo); redactar una descripción **compacta** desde `spec.md`/`plan.md` (`## Ticket` con link a la subtarea SPEC si `jira_subtask_url` está en el header; `## Problema` ≤2 bullets; `## Solución` ≤3; `## Criterios de aceptación` = `AC-n` como checklist observable, que hacen de plan de pruebas); cargar reviewers por defecto de `.specify/reviewers.json` del repo (si existe; excluir al autor; sin archivo → PR sin reviewers por defecto, ofrecer indicarlos). **Preview + confirmación obligatoria** antes de `bb_post`. Crear, reportar URL/ID/reviewers, guardar `pr_url` en el header y poner `status: pr-open`. **Nunca** aprobar ni mergear — solo crear. Salteable.
10. **Reporte final** (abajo). Ofrecer el sub-paso `archive`: si el usuario confirma que está probado y correcto, cerrar el flujo (ver `archive`).

### Extras (cambios fuera de AC)

Durante la implementación es normal toparse con un typo o un ajuste oportunista que no estaba planificado y querer aprovecharlo en el mismo commit. La regla de la skill es que **todo lo que entra al commit o mapea a un AC, o queda declarado como Extra** — nada entra sin rastro. Distinción:

- **Corregir lo que la skill acaba de escribir** (typo/ajuste dentro del código del feature, en `code_touched`): es parte de implementar bien el AC. **No** se declara.
- **Cambio sin relación con ningún AC** (otro archivo, o un hunk no relacionado dentro de un archivo `propio`): se declara como `E-n` en `## Extras (fuera de AC)` del `plan.md` (`- E1 — <descripción> · path:line`) antes de stagear, y se refleja como bullet en el body del commit (paso 7).
- **Un `QUALITY: fail` de la revisión final de diff que se decide no arreglar** (ver `reference.md` → "Revisión final de diff"): mismo `E-n`, misma sede, mismo bullet en el body. No es un cambio extra sino **deuda aceptada**, pero entra al commit por la misma puerta y por el mismo motivo — nada que se decida dejar pasar se cierra sin rastro. Se escribe qué señaló el revisor y por qué se aceptó; "lo vemos después" no es un motivo.

La detección es por **disciplina del conductor** al revisar el diff (paso 5/6), no automática a nivel hunk. Si un Extra crece o se vuelve riesgoso, tratarlo como cambio aparte: su propio flujo/commit, no colgarlo de este. `## Extras` es local (vive en `.plans/`, nunca se commitea); su único efecto en el repo es el body del commit.

> **Opción futura (no implementada): conformance cross-model.** Un gate pre-commit donde un modelo de otra familia (vía `cross-review`) verifica el diff contra el plan/AC — cazando AC sin implementar y *drift* a nivel hunk, usando `## Extras` como allowlist. Se descartó para el caso común (el paso `verify` + la revisión manual del diff ya lo cubren; agrega minutos de latencia y mantenimiento). Reconsiderar solo ante el dolor concreto de drift no detectado en cambios grandes/multi-repo (`sdd-orchestrator`).

## Paso `verify`

**Objetivo:** comprobar que lo implementado cumple la spec — con evidencia fresca, no con una corazonada.

1. **Fuente de los AC:** `spec.md` si existe; si no (triviales con spec embebida), la sección `## Spec` del `plan.md`.
2. **Gate function por cada AC** — saltarse un paso es afirmar sin verificar:
   - **CARGAR** — la versión vigente del contrato de `## Verification` y la fila que prueba *este* AC. Acá **no se elige** evidencia: elegirla después de implementar es elegir la que ya pasa. Un AC sin fila es un contrato que no cerró, y se vuelve a `plan`.
   - **CORRER** — ejecutar el comando **de la fila**, *fresco y completo* (no reusar una salida anterior ni "los tests de recién").
   - **LEER** — la salida entera + el exit code; contar fallos.
   - **VERIFICAR** — que esa salida coincide con el `Esperado` de la fila (no que "compila" o "pasan los tests" en general).
   - Recién entonces marcar el AC **cumplido / no cumplido**, citando la fila y la salida observada.

   | Afirmación | Requiere | No alcanza |
   |---|---|---|
   | "tests en verde" | salida fresca del runner: 0 fallos | una corrida previa, el linter en verde |
   | "build OK" | comando de build: exit 0 | "los logs se ven bien" |

   > **Conteo de tests: la verdad son los casos colectados, no las funciones.** Cuando la evidencia de un AC es un número de tests, lee el conteo que reporta el **propio runner** al correr el comando fresco; no lo deduzcas contando funciones a mano (`grep -c 'def test_'`, o contar `it(`/`test(`): un test parametrizado o table-driven explota en varios casos colectados, así que contar funciones sub-cuenta. Y si un reporte externo trae un conteo (el implementador delegado del modo `cross`, o un agente delegado por `sdd-orchestrator`), vuelve a correr el **mismo comando sobre el mismo set de archivos y el mismo commit** antes de darlo por bueno o por discrepante — comparar comandos o file-sets distintos fabrica discrepancias falsas.
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
5. **Persistir el resultado** en una sección `## Verify` del `plan.md` (tabla `AC-n · fila · cumplido/no · evidencia · fecha`; cuando aplique, anotar `revert → FAIL / restore → PASS`). Así sobrevive a la sesión: al retomar con `status: verified` no se re-verifica de gusto, y queda auditable. Plantilla en `reference.md`.
6. Si **todos** los AC se cumplen: poner `status: verified`. Si alguno falla: poner `status: implementing` (también si el flujo venía de `verified` — un AC en rojo desactualiza esa marca), reportarlo y volver a `implement` (o a `plan`/`specify` si el gap es de diseño).

## Sub-paso `archive` (cerrar un flujo terminado)

Solo cuando el usuario confirma explícitamente que el cambio está **probado y correcto como se espera** — esta decisión es del usuario, nunca automática. Requiere que el flujo esté completo en disco (`status` en `committed`, `pushed` o `pr-open`).

1. Poner `status: done` en el header del `plan.md`.
2. Mover la carpeta del flujo a archivados (POSIX: `mkdir -p .plans/archived` y `mv .plans/<id> .plans/archived/<id>`; PowerShell: `New-Item -ItemType Directory -Force .plans/archived` y `Move-Item .plans/<id> .plans/archived/<id>`). Movimiento plano, **no** `git mv`: sigue siendo local, no se trackea ni commitea — regla #10.
3. Confirmar que quedó en `.plans/archived/<id>/` y que sale del listado de flujos activos de `resume`.

### Rescatar el flujo antes de retirarlo (opcional, dependencia blanda)

**El disparador es `vault_archive.mode`, no que la skill esté instalada.** Instalar una skill —a veces porque vino en un paquete, a veces para otro flujo— no es consentir que cada archivado quede encadenado a ella, y medir el CLI mide una propiedad del entorno, no una decisión. Es la misma forma que ya tiene `cross_review`, y la asimetría anterior era un hueco, no doctrina.

| `mode` | Qué hace el sub-paso |
|---|---|
| `"off"` | el archivado **termina en el movimiento plano**. No se sondea el CLI, no se ofrece, no se vuelve a preguntar |
| `"on"` | corre la cadena; si falta el CLI o el vault, el fallo es cerrado (ver abajo) |
| `auto` (default) | con la skill instalada, consulta si hay **destino declarado** (`knowledge-vault.path_vault`) — **no** resuelve por la ausencia de su propia clave. Con destino declarado, **ofrece activar la cadena sobre ese destino** y no abre descubrimiento; sin destino declarado, abre descubrimiento —mostrando qué vaults hay con `kv config --discover`— y **persiste la respuesta** en la clave. Sin declaración previa no se corre la cadena en silencio |

Que falte `.specify/config.yml`, o que falte la clave `vault_archive` dentro de él, resuelve `auto` —su default— y **no** es un fallo: el config es opcional y todos sus campos lo son, así que la ausencia es el estado normal de un proyecto nuevo, no un error que detenga el archivado.

Con la cadena activa el archivado deja de ser el final del camino: `.plans/archived/` es local, untracked e invisible, así que lo que ese flujo decidió muere ahí. La cadena es **archivar, verificar y recién entonces retirar**, y su orden no es negociable.

| Paso | Qué | Ubicación observable si se corta acá |
|---|---|---|
| 1 | `kv archive --from .plans/archived/<id> --summary "<una línea>"` | el flujo está en `.plans/archived/<id>` y **no** en el vault |
| 2 | `kv retire --root .plans/archived --from .plans/archived/<id> --dry-run` | el flujo está en las dos partes; el vault ya lo tiene verificado |
| 3 | una persona lee el ensayo y **aprueba su digest** | ídem; no hay manifiesto en el vault |
| 4 | `kv retire --root .plans/archived --from .plans/archived/<id> --approve-digest <el aprobado>` | remanente `.kv-retirando-<id>` y manifiesto commiteado: destrucción autorizada, se **termina** reintentando |

Cada fila nombra dónde queda el flujo si la cadena se corta ahí, que es lo que permite reconocer el estado al reanudar — incluido el caso en que el flujo ya salió del listado de activos y todavía no llegó a destino.

**El paso 3 es un gate humano y no se automatiza.** El cierre **no puede correr el ensayo y pasar su digest** al retiro en la misma corrida: un guion que copia el digest de una salida a la siguiente satisface la letra del contrato y elimina el gate, que es lo único que separa un borrado irreversible de un efecto secundario.

**`NO_VAULT` no es un fallo: es la ausencia de configuración, y ahí el movimiento plano ya es el resultado completo.** La distinción importa porque las dos situaciones se parecen y no son la misma. Que el vault esté corrupto, o que el CLI falle a mitad de camino, merece un fallo cerrado: algo salió mal y seguir en silencio dejaría material fuera sin que nada lo señale. Que **no haya vault declarado** significa que el usuario todavía no eligió uno —o no quiere ninguno—, y tratarlo como error produce fricción en cada archivado sin ningún riesgo que la justifique. La propia skill del vault lo dice de su estado: es el que *habilita a preguntar y configurar*, no un archivo roto. Con `mode: auto` ese estado abre el ofrecimiento una vez; con `"off"` ni siquiera se llega a él.

**Ante cualquier OTRO fallo anterior al punto de no retorno el fallo es cerrado, y nunca se degrada al movimiento plano.** Vale también para la instalación del CLI que existe pero **no tiene el verbo** —una versión anterior a que se agregara—: ahí el archivado ya ocurrió y el retiro no puede, así que el flujo queda **intacto y reintentable** en `.plans/archived/<id>`. Degradar al movimiento de siempre dejaría material fuera del vault sin que nada lo señale, que es exactamente el estado que esta cadena viene a eliminar. Un fallo **posterior** a ese punto no deja un origen intacto sino un **remanente parcial, verificable y reintentable**.

**Reanudar no escribe para decidir.** El estado se lee de dos señales —el remanente y el manifiesto— y de la frontera publicada en el vault. En particular, **no se rearchiva para averiguar si ya estaba archivado**: `kv archive` con un `--summary` distinto reescribe el nodo y crea un commit, así que usarlo como sonda fabrica el commit espurio que se quería evitar.

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
