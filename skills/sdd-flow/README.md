# sdd-flow

Flujo de **Spec-Driven Development (SDD)** portable y agnóstico de proyecto. Lleva una feature/fix/refactor de punta a punta partiendo de una **especificación con criterios de aceptación verificables** en lugar de prompts sueltos, y cierra comprobando que lo implementado cumple esa spec.

## Qué hace

Recorre el ciclo SDD escribiendo artefactos auditables y deteniéndose en gates de aprobación:

```
init (opcional) → constitution → gather-context + perfil + preflight Git/worktree → specify → clarify → publish-spec (Jira, opcional) → create-branch → analyze → plan → tasks → implement → verify
```

- **Portable:** detecta stack (Node, Go, Rust, Python, Java, .NET…), host de Git (GitHub/GitLab/Bitbucket/otro), issue tracker y rama base por convención. Nada hardcodeado. Override opcional en `.specify/config.yml`.
- **Dos perfiles, la misma calidad:** `standard` conserva la secuencia habitual. `expedited` solo es elegible para cambios `trivial` o `normal` con `risk: low`; acelera la ceremonia, no elimina causa raíz, AC, pruebas, revisión de diff, rollback ni autorizaciones.
- **Gates escalados y explícitos:** trivial conserva 1 gate y complex, 3 más `clarify` obligatorio. En normal, `standard` usa 2 gates; `expedited` con Jira en `"off"` aprueba spec, plan y tasks en un único gate atómico. El agente muestra evaluación y recomendación, y tú eliges.
- **Trazabilidad:** cada criterio de aceptación (`AC-n`) se mapea a tasks y se verifica al final; si un AC de comportamiento tiene test, el test debe tener dientes (`revert → FAIL`, `restore → PASS`).
- **Estado persistido / retomable:** cada flujo guarda su fase (`status`) y su rama en el `plan.md`, y un `handoff.md` con "dónde quedé, qué decidí y cómo sigo". Puedes dejarlo a medias —en cualquier fase—, atender algo urgente en otra rama y retomarlo después desde donde quedó, incluso en otra sesión, sin re-investigar.
- **Preflight Git y worktree:** al iniciar un ciclo completo detecta HEAD, base y worktrees; comprueba el remoto, recomienda partir de la base y aislar el cambio, y espera tu decisión. Tras el escaneo propone la rama semántica y `~/worktrees/<proyecto>/<id>`, traslada el paquete del flujo, conserva el config local que lo gobierna, siembra los demás paths ignorados que aceptes, ejecuta el bootstrap y verifica todo. No mueve esta sesión: muestra el comando exacto para abrir otra en el destino.
- **Ramas heredadas o directas:** fuera del ciclo nuevo, `create-branch` conserva sus cuatro salidas seguras: seguir en la actual, cortar desde la base, cortar desde la actual o renombrar una rama solo-local cuando cumple sus precondiciones.
- **Doctor read-only:** `/sdd-flow doctor <id>` revisa coherencia del flujo sin escribir: ACs huérfanos, placeholders, Produce/Consume, branch/base, verify stale y ruido del working tree.
- **Recuperación durable:** `doctor` y `resume` clasifican el mismo snapshot de ledger, recibo, Git,
  tasks, proceso y owner. `doctor` solo informa; `resume` propone una reconciliación completa, espera
  un único gate y la ejecuta de forma idempotente únicamente si el diagnóstico sigue vigente.
- **Contexto de dominio opcional:** `domain_context` permite leer docs/ADRs existentes para usar términos y decisiones vigentes, sin crear ni editar documentación versionada.
- **Aprobación externa de la spec (opcional):** con `jira_approval.mode: "on"`, incluso en normal `expedited`, se mantiene el gate local de spec, se publica como **subtarea de Jira** y se espera al TL/PO; solo después se materializan plan y tasks y se aprueban juntos. El gate externo no cuenta como gate de complejidad. El flujo queda en pausa y se retoma sin re-explorar el ticket gracias al `handoff.md`. El default es `"off"`.
- **Autorizaciones intactas:** elegir `expedited` no autoriza por sí solo crear o cambiar ramas, escribir en Jira, commitear, pushear, abrir PRs ni mergear.
- **Apertura de PR (opcional):** tras el push, crea el PR hacia la rama base con descripción **compacta** (Problema, Solución y los criterios de aceptación como checklist, más el link al spec de Jira si se publicó) y reviewers por defecto (de `.specify/reviewers.json` del repo, si existe). Degrada a PR manual si no hay integración del host; el agente **nunca** mergea ni aprueba, solo crea.
- **Degradación elegante:** si falta un MCP/CLI (tracker, navegador, host), avisa y continúa con lo que haya.

## Cuándo usarla

Invocación explícita (no dispara sola): `/sdd-flow`.

- `/sdd-flow init` → (opcional, una vez por repo) crea `.specify/config.yml` + `.specify/constitution.md` con valores autodetectados. Ver "Inicializar el proyecto".
- `/sdd-flow` + contexto o clave de ticket → arranca el ciclo desde `gather-context`.
- `/sdd-flow implement .plans/<id>/` → implementa en una sesión fresca, reconstruyendo el contexto desde los artefactos (Vía B).

Frases que el router entiende: "configura el proyecto", "arma la spec", "aclaremos", "analiza esto", "arma el plan", "desglosa en tareas", "implementa", "verifica", "status", "doctor", "push", "crear PR".

## Retomar y cerrar flujos

Como `.plans/` es local, está visible entre ramas del mismo working tree, pero no nace en un linked worktree. El preflight copia solo el paquete del flujo y deja punteros para distinguir el origen snapshot del destino vivo. Eso permite:

- **Listar lo pendiente:** "¿en qué quedé?" / "qué flujos tengo" → muestra `id · branch · status · primera task pendiente` de cada flujo activo.
- **Diagnosticar sin tocar nada:** `/sdd-flow doctor <id>` → valida coherencia del flujo, clasifica la
  secuencia durable y reporta `OK/WARN/FAIL` con evidencia; no arregla ni escribe.
- **Retomar uno puntual:** "continuemos con `<id>`" → la skill resuelve primero el pedido y la
  ubicación; si el flujo vive en un worktree, exige la sesión allí sin hacer checkout. Solo para una
  ubicación local o heredada lee la rama del header y hace el `checkout` seguro. Después clasifica la
  secuencia **antes** de recuperar WIP o seguir el `status`. Si es
  recuperable, muestra todos los efectos y pide un único sí; después revalida y reconcilia sin gates
  intermedios. Si cambió la evidencia, el proceso puede seguir vivo o el owner obsoleto carece de
  fencing atómico, se detiene fail-closed.
- **Pausar sin perder nada (en cualquier fase):** "pausa esto" → escribe un `handoff.md` (estado, decisiones, próximo paso) y, si hay código a medias, lo guarda como WIP commit en su propia rama (no `stash`, que se confunde entre flujos). Al retomar —incluso en otra sesión— reconstruye todo desde ahí, sin re-investigar.
- **Cerrar y archivar:** cuando confirmas que está probado y correcto, el flujo pasa a `done` y se mueve a `.plans/archived/<id>/`. Nunca automático: lo decides tú.

## Artefactos en disco

```
<repo>/                         # TODO lo de abajo es LOCAL: la skill nunca lo trackea ni commitea
├─ .specify/
│  ├─ constitution.md           # principios de PROCESO
│  ├─ config.yml                # overrides de adaptación (opcional)
│  └─ reviewers.json            # reviewers por defecto del PR (opcional; lo usa `open-pr`)
└─ .plans/
   ├─ <id>/                     # un flujo en curso
   │  ├─ contrato-pedido.md     # marcador de adopción: decide si la vara del pedido aplica
   │  ├─ pedido/                # el pedido congelado: literal.jsonl (inmutable) + registro.md (append-only)
   │  ├─ plan.md                # SIEMPRE: header YAML (incl. status + branch) + CÓMO + resultado de verify
   │  ├─ spec.md                # en NORMAL y COMPLEJO (en trivial va embebida en plan.md → ## Spec)
   │  ├─ tasks.md               # en NORMAL y COMPLEJO (en trivial van embebidas en plan.md → ## Tasks)
   │  ├─ bitacora.md            # constancia append-only de los pasos del contrato
   │  ├─ sequence-ledger.yml    # versión, cursor, intenciones y efectos adjudicados
   │  ├─ sequence-ledger.owner/ # ownership exclusivo mientras un writer publica
   │  ├─ handoff.md             # siempre en `create-branch`; perfil, aprobación, worktree y retomado
   │  └─ jira-spec.md           # copia de lo publicado en Jira (solo con el gate de aprobación)
   └─ archived/                 # flujos cerrados (status: done), movidos solo tras tu confirmación
      └─ <id>/                  # misma estructura, ya terminada
```

> **Artefactos por complejidad:** *trivial* genera solo `plan.md` (con `## Spec` y `## Tasks` embebidas); *normal* y *complejo* separan `spec.md` + `plan.md` + `tasks.md`. El header del plan materializa `complexity`, `delivery_profile` y `risk`; el par de perfil es indivisible y cualquier forma parcial o desconocida falla cerrado. En `standard`, la diferencia entre normal y complejo es de **gates**, no de archivos: en *normal* las tasks se aprueban en el gate del plan; en *complejo* el gate de `tasks` es propio. `expedited` aplica la secuencia descrita arriba. La skill **siempre anuncia dónde quedaron las tasks**. La Vía B (bootstrap) y `verify` leen los archivos separados si existen, o las secciones embebidas si no.

> **Flujo personal, no del equipo:** ni `.specify/` ni `.plans/` se trackean. La skill nunca los stagea ni commitea. Como es personal, conviene ignorarlos vía `.git/info/exclude` (ignore **local** al clon, que no se versiona) en vez de `.gitignore` (que se comparte). Ese ignore local lo gestiona el usuario; la skill no lo toca.

## Instalación en otro proyecto

La skill no necesita configuración para empezar: en su primera corrida detecta el entorno y, si algo no se infiere, lo pregunta una vez (ofreciendo guardarlo).

### Inicializar el proyecto (opcional): `/sdd-flow init`

El ciclo no ejecuta `init` ni crea `constitution.md` por sí solo. Sí puede crear o fusionar `.specify/config.yml` tras tu confirmación cuando ofrece persistir una decisión de worktree. Si quieres fijar todo de entrada, corre `/sdd-flow init`: detecta el stack/test/build/tracker y te guía con un **wizard** de una sola pantalla para las decisiones que la skill no puede inferir (tracker, prefijo de rama y, solo si elegiste tracker Jira, aprobación externa de la spec) mostrando cada opción con su descripción —y el valor **actual pre-seleccionado** si el config ya existe—; los comandos quedan autodetectados y editables. El resto de las claves con default, incluidas las tres hojas `worktree`, no se pregunta: la skill las resuelve, y quien quiera fijarlas las copia de `config-ejemplo.md`, el ejemplo completo con las 40 claves del esquema. Al final te **muestra** el `config.yml` y la `constitution.md` y los escribe **solo tras tu confirmación**. Son locales y untracked (nunca se trackean ni commitean). Si ya existen, no los pisa: el wizard parte de lo vigente y fusiona lo que cambies. El ciclo funciona igual sin `init` —es un atajo para dejar la config explícita—.

Para fijar el comportamiento a mano, sin pasar por el wizard: crea `.specify/config.yml` (todos los campos opcionales) y copia ahí las claves que necesites desde `config-ejemplo.md`, la vista completa con las 40 claves marcadas `[def]`, `[ej]` u `[obl]`. Buenos candidatos para empezar: las tres que resuelve el wizard (`tracker`, `branch_prefix`, `jira_approval.mode`), los comandos (`test_cmd`/`build_cmd`/`lint_cmd`/`test_scope_hint`) y, para worktrees, la ruta base, los archivos o directorios locales a sembrar y los comandos de arranque. El default no copia entorno y deriva el bootstrap solo cuando reconoce el stack.

`delivery_profile`, `risk` y su evaluación son estado de la corrida, no configuración persistente:
se eligen con evidencia al iniciar y viajan en los artefactos de retomado.

> El esquema **completo** —las 40 claves de sus cinco dueños, cada una marcada `[def]`, `[ej]` u `[obl]` y lista para copiar— está en `config-ejemplo.md`. Cada skill dueña documenta las suyas en su propio `SKILL.md` o `reference.md`; las de `sdd-flow` están en `reference.md` → "Esquema de `.specify/config.yml`".

> **Prefijo de rama:** por defecto la rama usa un prefijo **semántico** (`feature/`, `fix/`, `chore/`… — para features es siempre `feature`, nunca `feat`: ese queda para los commits). Si tu proyecto necesita un prefijo único para **todo** tipo de cambio (p. ej. siempre `feature/`, incluso en fixes, por CI/CD), fíjalo en `branch_prefix` o pásalo al vuelo: "con prefijo de rama feature/". El prefijo reemplaza el segmento semántico; el resto (`<ticket>-<slug>`) no cambia.

> **Modo de implementación:** al aprobar las tasks puedes seguir **inline** (la misma sesión implementa, con todo el contexto cargado) o delegar. Por defecto la skill pregunta en el mismo gate de aprobación; se fija con `implement_mode: ask | inline | cross` en config, o al vuelo: "implementa con Codex". El modo **`cross`** delega la implementación a la skill `cross-implement` (un modelo de otra familia implementa; tu sesión revisa el diff como un PR ajeno, y el commit y el push quedan siempre en tu sesión) y solo se ofrece si esa skill y el CLI de la otra familia están disponibles; su política (`execution`/`max_fix_rounds`/`deadline`) se fija en el bloque `cross_implement` del config. En tasks de comportamiento, los pasos roja-verde se recomiendan cuando hay un seam testeable; la garantía final es `verify`.

El esquema completo está en `config-ejemplo.md`; la matriz de detección, en `reference.md`.

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

**6. Delegar la implementación a la otra familia:**
```
/sdd-flow empezar PROJ-130: refactor del módulo de pagos, implementa con Codex
```
→ tras aprobar las tasks, el propio flujo congela el contrato y `cross-implement` lo recibe congelado para que lo implemente un modelo de la otra familia; tu sesión revisa el diff como un PR ajeno, marca el progreso y conserva la revisión manual, el commit y el push.

**7. Cambio normal, de riesgo bajo y urgente:**
```
/sdd-flow fix PROJ-131: corregir serialización del header de trazas
```
→ tras evaluar evidencia propone `expedited`; con Jira en `"off"`, ejecuta co-explore, debate cuando
corresponda y cross-review, materializa spec, plan y tasks, y presenta los tres en un único gate.

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

## El contrato de verificación en el plan

La sección `## Verification` del `plan.md` dejó de ser prosa: es un **contrato** con una fila por
criterio de aceptación —evidencia, comando, resultado esperado y baseline—, escrito **antes** de
implementar, con todas las filas arrancando en rojo. Cada task referencia el ID de su fila, y el
self-review comprueba que la cobertura cierre en las dos direcciones: ni un AC sin fila ni una fila
sin AC.

El paso `verify` ya no elige qué evidencia usar: **carga la fila declarada y la ejecuta**. Es el
mismo rigor de antes movido de momento — y el momento era el problema, porque evidencia elegida
después de implementar es evidencia elegida para pasar.

Aplica en los tres niveles de complejidad, incluido *trivial*: lo que escala con la complejidad es
la cantidad de filas, no el formato.

## Dependencias

No tiene dependencias externas obligatorias. El helper interno
`scripts/delivery_profile.py` forma parte del paquete y es obligatorio para sus consumidores: si
falta o no expone el contrato compatible, promoción y huellas se detienen con un diagnóstico de
arnés, sin traceback ni fallback permisivo. Aprovecha, si están disponibles:

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
