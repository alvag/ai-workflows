# sdd-flow

Flujo de **Spec-Driven Development (SDD)** portable y agnóstico de proyecto. Lleva una feature/fix/refactor de punta a punta partiendo de una **especificación con criterios de aceptación verificables** en lugar de prompts sueltos, y cierra comprobando que lo implementado cumple esa spec.

## Qué hace

Recorre el ciclo SDD escribiendo artefactos auditables y deteniéndose en gates de aprobación:

```
init (opcional) → constitution → gather-context → specify → clarify → publish-spec (Jira, opcional) → create-branch → analyze → plan → tasks → implement → verify
```

- **Portable:** detecta stack (Node, Go, Rust, Python, Java, .NET…), host de Git (GitHub/GitLab/Bitbucket/otro), issue tracker y rama base por convención. Nada hardcodeado. Override opcional en `.specify/config.yml`.
- **Gates escalados por complejidad:** un fix trivial usa 1 gate; un cambio complejo, 3 (spec/plan/tasks) más `clarify` obligatorio. El agente clasifica y tú confirmas.
- **Trazabilidad:** cada criterio de aceptación (`AC-n`) se mapea a tasks y se verifica al final; si un AC de comportamiento tiene test, el test debe tener dientes (`revert → FAIL`, `restore → PASS`).
- **Estado persistido / retomable:** cada flujo guarda su fase (`status`) y su rama en el `plan.md`, y un `handoff.md` con "dónde quedé, qué decidí y cómo sigo". Puedes dejarlo a medias —en cualquier fase—, atender algo urgente en otra rama y retomarlo después desde donde quedó, incluso en otra sesión, sin re-investigar.
- **Doctor read-only:** `/sdd-flow doctor <id>` revisa coherencia del flujo sin escribir: ACs huérfanos, placeholders, Produce/Consume, branch/base, verify stale y ruido del working tree.
- **Contexto de dominio opcional:** `domain_context` permite leer docs/ADRs existentes para usar términos y decisiones vigentes, sin crear ni editar documentación versionada.
- **Aprobación externa de la spec (opcional):** si tu equipo lo necesita, puedes publicar la spec como **subtarea de Jira** para que el TL/PO la aprueben antes de implementar (`jira_approval` en config; off por defecto). El flujo queda en pausa y se retoma —incluso en otra sesión— sin re-explorar el ticket, gracias al `handoff.md`.
- **Apertura de PR (opcional):** tras el push, crea el PR hacia la rama base con descripción **compacta** (Problema, Solución y los criterios de aceptación como checklist, más el link al spec de Jira si se publicó) y reviewers por defecto (de `.specify/reviewers.json` del repo, si existe). Degrada a PR manual si no hay integración del host; el agente **nunca** mergea ni aprueba, solo crea.
- **Degradación elegante:** si falta un MCP/CLI (tracker, navegador, host), avisa y continúa con lo que haya.

## Cuándo usarla

Invocación explícita (no dispara sola): `/sdd-flow`.

- `/sdd-flow init` → (opcional, una vez por repo) crea `.specify/config.yml` + `.specify/constitution.md` con valores autodetectados. Ver "Inicializar el proyecto".
- `/sdd-flow` + contexto o clave de ticket → arranca el ciclo desde `gather-context`.
- `/sdd-flow implement .plans/<id>/` → implementa en una sesión fresca, reconstruyendo el contexto desde los artefactos (Vía B).

Frases que el router entiende: "configura el proyecto", "arma la spec", "aclaremos", "analiza esto", "arma el plan", "desglosa en tareas", "implementa", "verifica", "status", "doctor", "push", "crear PR".

## Retomar y cerrar flujos

Como `.plans/` es local (no trackeado), git no lo mueve al cambiar de rama: tus flujos están visibles desde **cualquier** rama, y cada `plan.md` recuerda su `branch` y su `status`. Eso permite:

- **Listar lo pendiente:** "¿en qué quedé?" / "qué flujos tengo" → muestra `id · branch · status · primera task pendiente` de cada flujo activo.
- **Diagnosticar sin tocar nada:** `/sdd-flow doctor <id>` → valida coherencia del flujo y reporta `OK/WARN/FAIL` con evidencia; no arregla ni escribe.
- **Retomar uno puntual:** "continuemos con `<id>`" → la skill lee la rama del header, hace el `checkout` seguro (frenando si tienes código sin commitear en la rama actual) y sigue desde la fase exacta (`status`), no desde cero.
- **Pausar sin perder nada (en cualquier fase):** "pausa esto" → escribe un `handoff.md` (estado, decisiones, próximo paso) y, si hay código a medias, lo guarda como WIP commit en su propia rama (no `stash`, que se confunde entre flujos). Al retomar —incluso en otra sesión— reconstruye todo desde ahí, sin re-investigar.
- **Cerrar y archivar:** cuando confirmas que está probado y correcto, el flujo pasa a `done` y se mueve a `.plans/archived/<id>/`. Nunca automático: lo decides tú.

## Artefactos en disco

```
<repo>/                 # TODO lo de abajo es LOCAL: la skill nunca lo trackea ni commitea
├─ .specify/
│  ├─ constitution.md   # principios de PROCESO
│  ├─ config.yml        # overrides de adaptación (opcional)
│  └─ reviewers.json    # reviewers por defecto del PR (opcional; lo usa `open-pr`)
└─ .plans/
   ├─ <id>/             # un flujo en curso
   │  ├─ plan.md        # SIEMPRE: header YAML (incl. status + branch) + CÓMO + resultado de verify
   │  ├─ spec.md        # en NORMAL y COMPLEJO (en trivial va embebida en plan.md → ## Spec)
   │  ├─ tasks.md       # en NORMAL y COMPLEJO (en trivial van embebidas en plan.md → ## Tasks)
   │  ├─ handoff.md     # al pausar o en el gate de Jira: estado + decisiones para retomar
   │  └─ jira-spec.md   # copia de lo publicado en Jira (solo con el gate de aprobación)
   └─ archived/         # flujos cerrados (status: done), movidos solo tras tu confirmación
      └─ <id>/          # misma estructura, ya terminada
```

> **Artefactos por complejidad:** *trivial* genera solo `plan.md` (con `## Spec` y `## Tasks` embebidas); *normal* y *complejo* separan `spec.md` + `plan.md` + `tasks.md`. La diferencia entre normal y complejo es de **gates**, no de archivos: en *normal* las tasks se aprueban en el gate del plan; en *complejo* el gate de `tasks` es propio. La skill **siempre anuncia dónde quedaron las tasks**. La Vía B (bootstrap) y `verify` leen los archivos separados si existen, o las secciones embebidas si no.

> **Flujo personal, no del equipo:** ni `.specify/` ni `.plans/` se trackean. La skill nunca los stagea ni commitea. Como es personal, conviene ignorarlos vía `.git/info/exclude` (ignore **local** al clon, que no se versiona) en vez de `.gitignore` (que se comparte). Ese ignore local lo gestiona el usuario; la skill no lo toca.

## Instalación en otro proyecto

La skill no necesita configuración para empezar: en su primera corrida detecta el entorno y, si algo no se infiere, lo pregunta una vez (ofreciendo guardarlo).

### Inicializar el proyecto (opcional): `/sdd-flow init`

Estos archivos **no se crean solos** durante el ciclo (que usa autodetección + defaults conversacionales). Si quieres fijarlos de entrada, corre `/sdd-flow init`: detecta el stack/test/build/tracker y te guía con un **wizard** para las decisiones (tracker, estilo de commit, prefijo de rama, modo de implementación, cross-review, aprobación en Jira) mostrando cada opción con su descripción —y el valor **actual pre-seleccionado** si el config ya existe—; los comandos quedan autodetectados y editables. Al final te **muestra** el `config.yml` y la `constitution.md` y los escribe **solo tras tu confirmación**. Son locales y untracked (nunca se trackean ni commitean). Si ya existen, no los pisa: el wizard parte de lo vigente y fusiona lo que cambies. El ciclo funciona igual sin `init` — es un atajo para dejar la config explícita.

Para fijar el comportamiento a mano, crear `.specify/config.yml` (todos los campos opcionales):

```yaml
stack: node                      # node | go | rust | python | java | dotnet | other
test_cmd: "npm test"
build_cmd: "npm run build"       # omitir si el stack no compila
lint_cmd: "npm run lint"         # opcional
default_branch: main             # rama base; auto si se omite
branch_format: "{type}/{ticket}-{slug}"
branch_prefix: "feature/"        # opcional: fija el prefijo de rama (útil para CI/CD); reemplaza el semántico
commit_style: conventional       # conventional | plain
tracker: github                  # jira | github | gitlab | linear | none
test_scope_hint: "vitest run {name}"   # plantilla de COMANDO para acotar tests; {name} = archivo/patrón
cross_review: { mode: auto }     # segunda opinión cross-model: auto (por complejidad) | on | off
jira_approval: { mode: "off" }   # aprobación externa de la spec en Jira (solo si tracker: jira; "off"/"on" entre comillas)
implement_mode: ask              # cómo ejecutar las tasks: ask (preguntar en el gate) | inline | subagent
domain_context:
  mode: auto                     # auto | on | off; solo lectura
  context_paths: []              # docs/glosarios/arquitectura existentes
  adr_paths: []                  # ADRs existentes
final_diff_review: { mode: auto } # revisión agregada en complex/high-risk inline
```

> **Prefijo de rama:** por defecto la rama usa un prefijo **semántico** (`feature/`, `fix/`, `chore/`… — para features es siempre `feature`, nunca `feat`: ese queda para los commits). Si tu proyecto necesita un prefijo único para **todo** tipo de cambio (p. ej. siempre `feature/`, incluso en fixes, por CI/CD), fíjalo en `branch_prefix` o pásalo al vuelo: "con prefijo de rama feature/". El prefijo reemplaza el segmento semántico; el resto (`<ticket>-<slug>`) no cambia.

> **Modo de implementación:** al aprobar las tasks puedes seguir **inline** (la misma sesión implementa, con todo el contexto cargado) o despachar **subagentes frescos por task** (cada agente lee solo spec/plan/su task — contexto limpio, sin el ruido conversacional previo; la revisión por task, el commit y el push quedan siempre en tu sesión). Por defecto la skill pregunta en el mismo gate de aprobación; se fija con `implement_mode: ask | inline | subagent` en config, o al vuelo: "implementa con subagentes". En tasks de comportamiento, los pasos roja-verde se recomiendan cuando hay un seam testeable; la garantía final es `verify`.

El esquema completo y la matriz de detección están en `reference.md`.

## Ejemplos de uso

**1. Feature en un repo Node con tracker:**
```
/sdd-flow empezar PROJ-128: exportar resultados a CSV desde la tabla de reportes
```
→ trae el ticket, clasifica el cambio, escribe `spec.md` con AC, para en el gate; tras aprobar sigue con plan → tasks → implement → verify.

**2. Diagnóstico read-only de un flujo:**
```
/sdd-flow doctor PROJ-128
```
→ valida ACs, tasks, branch/base, `## Verify` y working tree sin modificar nada.

**3. Fix trivial en un repo Go sin tracker:**
```
/sdd-flow fix: typo en el mensaje de error de healthcheck
```
→ clasifica *trivial*: spec mínima embebida en el plan, 1 solo gate, implementa, corre `go test`, verifica.

**4. Implementar en sesión fresca:**
```
/sdd-flow implement .plans/PROJ-128/
```
→ reconstruye contexto desde los artefactos, valida coherencia con el repo (working tree limpio, rama, base_commit) y procede.

**5. Con prefijo de rama fijo (override al vuelo):**
```
/sdd-flow fix PROJ-129: null en el carrito, con prefijo de rama feature/
```
→ la rama queda `feature/PROJ-129-null-carrito` en vez del semántico `fix/…`. (También se puede fijar en `.specify/config.yml` con `branch_prefix`.)

**6. Implementar con subagentes frescos:**
```
/sdd-flow empezar PROJ-130: refactor del módulo de pagos, implementa con subagentes
```
→ tras aprobar las tasks, cada task la implementa un agente fresco que lee solo los artefactos; tu sesión revisa cada diff, marca el progreso y conserva la revisión manual, el commit y el push.

## Verificación: más que "tests en verde"

La garantía de la skill **no** es que pasen los tests, sino que **cada criterio de aceptación (`AC-n`) se cumpla por su medio declarado** — un test, un paso manual o una **observación de comportamiento**. El paso `verify` recorre los AC antes de commitear; si uno falla, no commitea (aunque los tests estén en verde). Si el AC de comportamiento está cubierto por test, el test debe discriminar: revertir el hunk de implementación debe hacerlo fallar y restaurarlo debe volverlo verde.

Para que esto funcione, el AC debe redactarse como **comportamiento observable**, no como "el test pasa". Ejemplo (bug de ordenamiento en UI):

> **AC-1:** Given la grilla de productos, When selecciono "precio ascendente", Then los precios quedan de menor a mayor (el primer ítem tiene el precio más bajo).
>
> **Verificación:** abrir la grilla en el navegador, aplicar el orden y confirmar que los primeros precios son crecientes.

### Verificación en el navegador (UI)

Para bugs o cambios de UI, si hay una tool de navegador disponible (Chrome MCP, Playwright, DevTools), el agente puede **reproducir** el problema en `analyze` y **validar** el AC en `verify` levantando la página — no solo corriendo unit tests. El método concreto se propone en la sección `## Verification` del plan y se aprueba en el gate de `plan`.

### Cómo asegurar que la verificación sea la correcta

- **Por cambio:** al iniciar, indica el método ("es un bug de UI, valídalo en el navegador"); o revisa/ajusta el AC y la sección `## Verification` en los gates de `specify`/`plan`.
- **Por repo (recomendado para consistencia):** fíjalo en `.specify/constitution.md` como estándar de *Done*, p. ej.: *"los AC de UI se validan reproduciéndolos en el navegador, no solo con unit tests"*. Así todos los cambios de UI heredan esa exigencia sin repetirla cada vez.

> Límite: la validación en navegador requiere que la tool esté disponible en la sesión. Si no la hay, la skill degrada y pide captura/pasos de reproducción.

## Dependencias

Ninguna obligatoria. Aprovecha, si están disponibles:

- CLI/MCP del issue tracker (Jira, GitHub, GitLab, Linear) para traer issues.
- CLI/MCP del host de Git (`gh`, `glab`) para PRs y detección de rama remota.
- Tool de navegador (Chrome/Playwright/DevTools) para reproducir bugs de UI.
- Skill de debugging sistemático, si existe en el entorno. (El commit es **inline**, sin depender de ninguna skill externa: la lógica de construcción del mensaje vive en `reference.md` → "Construcción del mensaje de commit".)
- MCP de Bitbucket (`mcp__bitbucket__*`), **solo** para el sub-paso opcional `open-pr` (crear el PR tras el push). Sin él, el paso se degrada a PR manual.

Sin ellas, degrada con fallbacks (`git` directo, búsqueda local, preguntar al usuario).

## Archivos

- `SKILL.md` — el flujo y las reglas.
- `reference.md` — matriz de detección, esquema de `config.yml`, plantillas de artefactos, ejemplos.
- `README.md` — este archivo.
