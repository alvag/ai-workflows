# bitbucket-code-review — referencia

Material de apoyo para el `SKILL.md`. Cargar bajo demanda.

## Tabla de contenidos

- [Rúbrica de confianza 0-100 (verbatim)](#rúbrica-de-confianza-0-100-verbatim-de-la-skill-oficial)
- [Deduplicación contra comentarios de terceros](#deduplicación-contra-comentarios-de-terceros)
- [Falsos positivos (verbatim)](#falsos-positivos-verbatim-de-la-skill-oficial)
- [Arquitectura-target de results (checklist de review)](#arquitectura-target-de-results-checklist-de-review)
- [Criterios de aceptación de Jira](#criterios-de-aceptación-de-jira)
- [Parseo del diff a números de línea](#parseo-del-diff-a-números-de-línea)
- [Endpoints `bb_*` de lectura](#endpoints-bb_-de-lectura)
- [Endpoints de escritura (con gate)](#endpoints-de-escritura-con-gate)
- [Preview de publicación](#preview-de-publicación)
- [Descubrir e invocar revisores (cross-model)](#descubrir-e-invocar-revisores-cross-model)
- [Prompt al revisor + contrato de salida](#prompt-al-revisor--contrato-de-salida)
- [Materializar el contexto del PR](#materializar-el-contexto-del-pr)
- [Seguimiento: `.pr-review/` y `review-log.md`](#seguimiento-pr-review-y-review-logmd)
- [Template y ejemplos de comentario publicado](#template-y-ejemplos-de-comentario-publicado)
- [Link a Bitbucket](#link-opcional-a-bitbucket-referencia-para-el-usuario)
- [Troubleshooting](#troubleshooting)

---

## Rúbrica de confianza 0-100 (verbatim de la skill oficial)

Para cada hallazgo, dar un score 0-100 que indique el nivel de confianza de que es un problema real
(vs. falso positivo). Para hallazgos marcados por instrucciones de CLAUDE.md, **verificar que el
CLAUDE.md realmente menciona ese problema específicamente**. La escala (usar este rubro tal cual):

- **0**: Nada de confianza. Es un falso positivo que no resiste un escrutinio leve, o es un problema
  pre-existente.
- **25**: Algo de confianza. Podría ser un problema real, pero también podría ser falso positivo. No
  se pudo verificar que sea real. Si es estilístico, no está explícitamente señalado en el CLAUDE.md
  relevante.
- **50**: Confianza moderada. Se verificó que es un problema real, pero podría ser un nitpick o no
  ocurrir muy seguido en la práctica. Relativo al resto del PR, no es muy importante.
- **75**: Alta confianza. Se revisó dos veces y se verificó que es muy probable que sea un problema
  real que se dará en la práctica. El enfoque actual del PR es insuficiente. Es muy importante e
  impacta directamente la funcionalidad, o está directamente mencionado en el CLAUDE.md relevante.
- **100**: Certeza absoluta. Se revisó dos veces y se confirmó que es definitivamente un problema
  real, que ocurrirá frecuentemente en la práctica. La evidencia lo confirma directamente.

**Filtro:** descartar todo hallazgo con score **< 80**. Si no queda ninguno, la decisión es
🟢 Aprobado (no inventar findings).

**Al consolidar varios revisores:** aplicar esta misma rúbrica a *cada* hallazgo (propio o de un
externo) antes de incorporarlo. Un finding de un externo no entra a la conclusión solo porque lo dijo:
verificarlo técnicamente contra el diff y los CLAUDE.md (ver "Consolidación — disciplina" en SKILL.md).

## Niveles de riesgo (semáforo) — distinto de la confianza

La **confianza** (rúbrica de arriba) responde "¿el hallazgo es real?". El **riesgo** responde "¿qué
tan grave es si es real?". Son ejes distintos: primero filtrar por confianza ≥80; a lo que sobrevive,
asignarle un nivel de riesgo con su icono:

- 🔴 **crítico**: rompe funcionalidad, corrompe datos, falla de seguridad, o viola gravemente un
  CLAUDE.md aplicable. **Bloquea** → solicitar cambios.
- 🟡 **medio**: bug real de menor impacto o caso de borde no contemplado. No bloquea por sí solo.
- 🟢 **bajo**: problema menor o de robustez. No bloquea.
- 💡 **sugerencia** (opcional): mejora nice-to-have, no es un bug. **No cuenta** para la decisión.

## Regla de decisión (riesgo → acción)

| Observaciones (tras confianza ≥80) | Decisión | Acción propuesta | Gate |
|---|---|---|---|
| ≥1 🔴 crítica | 🔴 Cambios solicitados | `request-changes` | confirmar antes de votar |
| 0 críticas, hay 🟡/🟢 | 🟢 Aprobado | `approve` | confirmar; señalar 🟡/🟢 como no bloqueantes |
| 0 observaciones (limpio) | 🟢 Aprobado | `approve` | confirmar igual (approve nunca automático) |

- Las 💡 sugerencias **no** alteran la decisión.
- El `POST /approve` **siempre** se confirma aparte (regla 3 del SKILL): la regla define la *propuesta*,
  no emite el voto. Si el usuario declina el approve, se publica solo el comentario.

## Deduplicación contra comentarios de terceros

Paso del conductor en el Paso 8, tras clasificar el riesgo y antes de derivar la decisión. Cruza
cada observación sobreviviente contra el **inventario** de comentarios existentes (Paso 5), para
**no re-pedir** lo que otro revisor (humano o bot) ya señaló.

**Match:** archivo + línea + **tema/causa**, con criterio. No es string-match: dos bugs distintos
pueden caer en la misma línea, y el mismo bug puede describirse con otras palabras. Comparar el
síntoma/causa, no el texto literal.

| Comentario de tercero | Acción |
|---|---|
| **Abierto** y coincide | **Eco**: atribuir (`Ya observado por @autor` + ref/url) y mantener su icono de riesgo. **Cuenta** para la decisión. No re-escribir como pedido. |
| **Resuelto** y coincide | Re-evaluar contra el sha actual: **atendido** → descartar; **sigue presente** → **eco re-abierto** ("marcado resuelto pero sigue presente en `<sha>`"). |
| Sin coincidencia | Hallazgo **nuevo**: se reporta normal. |

- El cruce es del **conductor**, sobre todos los hallazgos (propios + de los externos): filtro
  autoritativo. El revisor externo solo intenta no repetir (ver su prompt); no se le confía.
- **No tocar el thread del tercero.** La referencia es textual en el propio comentario de decisión;
  nunca `reply` ni `resolve` sobre comentarios ajenos (regla 2 del SKILL).
- **Si todos los hallazgos son ecos** (nada nuevo): comentario breve de adhesión + decisión; no
  re-listar cada punto (ver Paso 9).

## Falsos positivos (verbatim de la skill oficial)

Ejemplos de falsos positivos a **descartar** durante el análisis y el scoring:

- Problemas pre-existentes (no introducidos por este PR).
- Algo que parece un bug pero no lo es.
- Nitpicks pedantes que un ingeniero senior no marcaría.
- Problemas que un linter, typechecker o compilador atraparía (p. ej. imports faltantes o
  incorrectos, errores de tipo, tests rotos, formato). No correr esos pasos: se asume que CI los corre
  por separado.
- Problemas generales de calidad (falta de cobertura de tests, seguridad genérica, documentación
  pobre), salvo que CLAUDE.md lo exija explícitamente.
- Problemas señalados en CLAUDE.md pero explícitamente silenciados en el código (p. ej. con un
  comentario que desactiva el lint).
- Cambios de funcionalidad que probablemente son intencionales o están directamente relacionados con
  el cambio mayor.
- Problemas reales, pero en **líneas que el PR no modificó**.

## Arquitectura-target de results (checklist de review)

Solo para **código nuevo** en el diff. Fuentes: `docs/architecture-target.md` y
`.cursor/rules/results-feature-work.mdc`. Señalar violaciones como hallazgo (riesgo según impacto);
**no exigir migración de legacy** en archivos tocados salvo que el PR la proponga — sí verificar que el
cambio **no extienda** patrones deprecated.

| Señal de alerta en código **nuevo** | Esperado |
|---|---|
| Inyectar un `*FluxService` en `pages/` o `shared/components/` | Ir por `FluxService.progress()` |
| HTTP/GraphQL fuera de un `*.adapter.service.ts` | Adapter + `core/querys/` |
| Lógica de funnel dentro de componentes | `*.flux.service.ts` |
| Nuevo `BehaviorSubject` / `subscribe()` manual en UI | Signals (`signal`/`computed`) |
| Filtrado de listas vía `progress()` | `FlightFilterService` / `HotelFilterService` `.multiFilter()` |
| Journey (`hf`, `hotelId`, …) vía `ParameterService` | `FluxSessionService` |
| Refactor amplio no relacionado al ticket | Rechazar o pedir split |

**Regresión por vertical** (si toca funnel compartido): `packages` (legacy) vs `packagesFlex` vs
`accommodations` vs `air`; mobile/desktop si el diff ramifica por `isMobile`; B2B/B2C si ramifica por
`channel` / `isB2b()`. **Tests frágiles:** si toca searchbox/research, mirar regresión en
`**/research/*.spec.ts` y `**/*.integration.spec.ts` (no correrlos — regla 5; señalar si el PR no los
actualizó).

## Criterios de aceptación de Jira

Opcional y **no bloqueante** (Paso 4). Objetivo: verificar que el PR cumple lo que el ticket pide.

1. **Extraer claves** `[A-Z][A-Z0-9]+-\d+` del título, la descripción y la rama del PR.
2. Si hay claves **y** un MCP de Atlassian disponible (por capacidad, no por nombre): traer el issue
   por clave — p. ej. `getJiraIssue` con `cloudId` de `descocha.atlassian.net` y formato markdown.
3. **Cruzar AC vs diff:** ¿el cambio aborda summary/description y **cada criterio de aceptación**
   explícito? ¿El plan de pruebas del PR cubre lo pedido?
   - AC central sin cubrir y el PR dice resolver el ticket → 🔴.
   - AC secundario o ambiguo sin cubrir → 🟡 (pregunta al autor).
4. **Degradar sin bloquear:** sin claves, sin MCP o si falla → anotarlo en el resumen y validar contra
   la descripción del PR. **Nunca** cambiar el veredicto solo porque Jira/MCP no respondió (regla
   heredada del review). **No** transicionar ni comentar en Jira automáticamente (fuera de scope).

## Parseo del diff a números de línea

El endpoint `/diff` devuelve un diff unificado. Cada archivo trae uno o más hunks con encabezado:

```
@@ -<oldStart>,<oldCount> +<newStart>,<newCount> @@ <contexto opcional>
```

Algoritmo para asignar números de línea:

1. Al leer un encabezado de hunk, inicializar `oldLn = oldStart` y `newLn = newStart`.
2. Recorrer las líneas del hunk:
   - Línea que empieza con `' '` (contexto): pertenece a `oldLn` **y** `newLn`; incrementar **ambos**.
   - Línea que empieza con `'+'` (añadida): número en el archivo **nuevo** = `newLn`; incrementar
     `newLn`. (Este es el número que se cita y el que corresponde a `inline.to`.)
   - Línea que empieza con `'-'` (eliminada): número en el archivo **viejo** = `oldLn`; incrementar
     `oldLn`. (Corresponde a `inline.from`.)
3. Las líneas `\ No newline at end of file` se ignoran para el conteo.

El comentario se ancla en la línea **nueva** de la primera línea relevante del hallazgo. Para un
hallazgo sobre código eliminado, citar la línea del archivo viejo (`inline.from`) y aclararlo.

### Ejemplo

```diff
@@ -10,6 +10,7 @@ export function foo() {
   const a = 1;       // contexto  -> old 10, new 10
   const b = 2;       // contexto  -> old 11, new 11
-  return a + b;      // eliminada -> old 12
+  const c = 3;       // añadida   -> new 12
+  return a + b + c;  // añadida   -> new 13
   // fin             // contexto  -> old 13, new 14
```

Un comentario sobre `return a + b + c;` se ancla en la **línea nueva 13** (`inline.to: 13`).

---

## Endpoints `bb_*` de lectura

`<ws>` = workspace, `<repo>` = repo, `<id>` = número de PR. El MCP agrega el `/2.0` y maneja la auth.

| Propósito | path | notas |
|---|---|---|
| Detectar PR OPEN por rama | `/repositories/<ws>/<repo>/pullrequests` | `q: state="OPEN" AND source.branch.name="<rama>"` |
| Metadata del PR (incl. autor) | `/repositories/<ws>/<repo>/pullrequests/<id>` | `jq: "{id, title, state, draft, author: author.display_name, account: author.account_id, src: source.branch.name, dst: destination.branch.name, sha: source.commit.hash}"` |
| Archivos cambiados | `/repositories/<ws>/<repo>/pullrequests/<id>/diffstat` | `pagelen: 100` |
| Diff unificado | `/repositories/<ws>/<repo>/pullrequests/<id>/diff` | texto plano |
| Comentarios existentes | `/repositories/<ws>/<repo>/pullrequests/<id>/comments` | `q: deleted=false`; arma el **inventario** (propio / terceros abiertos / terceros resueltos) para dedup y para hallar el propio |

Listar comentarios con ubicación, autor, estado y link (para el inventario del Paso 5):

```json
{ "tool": "mcp__bitbucket__bb_get",
  "args": {
    "path": "/repositories/<ws>/<repo>/pullrequests/<id>/comments",
    "queryParams": { "pagelen": "100", "q": "deleted=false" },
    "jq": "values[*].{id: id, raw: content.raw, user: user.display_name, file: inline.path, line: inline.to, resolved: (resolution != null), parent: parent.id, url: links.html.href, created: created_on}" } }
```

Clasificar la lista en tres grupos: (a) **el propio** — match por `comment-id` registrado en
`.pr-review/<pr-id>/review-log.md` (respaldo: `user.display_name` == cuenta propia + estructura
reconocible "Hola @… / Decisión:"); (b) **terceros abiertos** (`resolved=false`); (c) **terceros
resueltos** (`resolved=true`). El cruce de (b)/(c) contra los hallazgos se hace en el Paso 8 (ver
"Deduplicación contra comentarios de terceros").

## Endpoints de escritura (con gate)

**Nunca** invocar estos sin el preview confirmado (ver "Preview de publicación"). Patrón API REST 2.0;
el MCP maneja la auth (no se requieren `BITBUCKET_*`).

### Comentario general (la decisión por defecto)

```json
{ "tool": "mcp__bitbucket__bb_post",
  "args": {
    "path": "/repositories/<ws>/<repo>/pullrequests/<id>/comments",
    "body": { "content": { "raw": "<markdown del comentario, ya confirmado>" } },
    "jq": "{id: id, url: links.html.href}" } }
```

### Comentario inline (anclado a archivo/línea — solo cuando aporta)

```json
{ "tool": "mcp__bitbucket__bb_post",
  "args": {
    "path": "/repositories/<ws>/<repo>/pullrequests/<id>/comments",
    "body": { "content": { "raw": "<texto>" },
              "inline": { "path": "<archivo>", "to": <línea-nueva> } },
    "jq": "{id: id, file: inline.path, line: inline.to}" } }
```

- Para una línea **eliminada**, usar `"from": <línea-vieja>` en vez de `"to"`.

### Responder un comentario (reply en thread)

```json
{ "tool": "mcp__bitbucket__bb_post",
  "args": {
    "path": "/repositories/<ws>/<repo>/pullrequests/<id>/comments",
    "body": { "content": { "raw": "<texto>" },
              "parent": { "id": <comment-id> } },
    "jq": "{id: id, parent: parent.id}" } }
```

### Resolver el propio comentario (solo en re-pasada)

```json
{ "tool": "mcp__bitbucket__bb_post",
  "args": { "path": "/repositories/<ws>/<repo>/pullrequests/<id>/comments/<comment-id>/resolve" } }
```

- `bb_post` a `.../resolve` marca el thread como resuelto; `bb_delete` al mismo path lo reabre.
- **Solo** sobre el `<comment-id>` del propio comentario de decisión de la skill — nunca threads de
  terceros (eso es de `sdd-pr-feedback`).

### Aprobar / solicitar cambios (estado del PR)

```json
{ "tool": "mcp__bitbucket__bb_post",
  "args": { "path": "/repositories/<ws>/<repo>/pullrequests/<id>/approve" } }
```

```json
{ "tool": "mcp__bitbucket__bb_post",
  "args": { "path": "/repositories/<ws>/<repo>/pullrequests/<id>/request-changes" } }
```

- `approve` se confirma **por separado** del comentario (regla 3 del SKILL): es outward-facing de alto
  impacto. `bb_delete` al mismo path retira el voto.
- Si el token no tiene scope de escritura, el POST falla → degradar a solo proponer el texto.

> **Prohibido:** `POST .../merge`. Esta skill nunca mergea.

## Preview de publicación

Antes de cualquier escritura, mostrar y esperar confirmación afirmativa. Formato:

```
Voy a publicar en el PR #<id> (cocha-digital/results):

  Acción(es):            comentario general · [+ approve | + request-changes | + resolve]
  Ancla (si inline):     <archivo>:<línea>

  ─── Comentario (markdown exacto a enviar) ───
  <texto completo del comentario>
  ─────────────────────────────────────────────

¿Confirmas la publicación?
```

- **`approve` se confirma aparte**: "Además, ¿marco el PR como Aprobado? (sí/no)".
- Sin confirmación, no se invoca ningún `bb_post`/`bb_delete`. Si el usuario pide cambios, aplicarlos y
  volver a mostrar el preview.
- Override "solo proponer / no publicar": mostrar el comentario y terminar sin escribir.

---

## Descubrir e invocar revisores (cross-model)

Replicado de `sdd-cross-review`. Acá el "artefacto" a revisar es el **PR materializado** (ver
"Materializar el contexto del PR"); el revisor lo lee desde disco y puede leer el código del repo en
read-only. **El revisor nunca escribe en Bitbucket ni en el repo**: solo emite hallazgos + veredicto.
Quien publica es el conductor.

**Dos directorios distintos en los comandos de abajo** (definidos en SKILL.md → Paso 1):

- **`<dir-código>`** = dónde está el código del PR en disco; es el `working_dir` (`-C`/`cd`) del
  revisor. Raíz del repo si se eligió (a)/(b) en el Paso 1; el **worktree** si se eligió (c). Ahí el
  código en disco refleja el PR.
- **`<raíz-repo>`** = raíz del repo principal, donde vive **siempre** `.pr-review/`. El prompt, el
  `context/` y el archivo de veredicto se direccionan con **rutas absolutas** a `<raíz-repo>/.pr-review/<id>/`,
  porque cuando `<dir-código>` es un worktree una ruta relativa apuntaría adentro del worktree (donde
  `.pr-review/` no existe). Si no hubo worktree, `<dir-código>` y `<raíz-repo>` coinciden.

### Descubrir (familia del conductor + anti-misma-familia)

Regla dura: **el revisor externo nunca es de la misma familia que el conductor.** La familia es la del
**modelo de respaldo, no la del CLI**.

**Paso 1 — harness conductor.** Claude Code, Codex CLI u otro (lo indica el runtime).

**Paso 2 — modelo de respaldo (solo si conduce Claude Code).** Sondear el entorno:

```bash
# POSIX:
env | grep -iE 'ANTHROPIC_BASE_URL|ANTHROPIC_DEFAULT_(OPUS|SONNET|HAIKU)_MODEL|ANTHROPIC_MODEL'
```
```powershell
# PowerShell:
Get-ChildItem Env: | Where-Object Name -match 'ANTHROPIC_BASE_URL|ANTHROPIC_DEFAULT_(OPUS|SONNET|HAIKU)_MODEL|ANTHROPIC_MODEL'
```

Si `ANTHROPIC_BASE_URL` apunta a un host distinto de `api.anthropic.com`/`anthropic.com`, **o** algún
`ANTHROPIC_DEFAULT_*_MODEL`/`ANTHROPIC_MODEL` es no-`claude-*` (`glm-*`, `kimi-*`, `deepseek-*`, …) →
la familia del conductor es ese modelo de respaldo, no Claude. Sonda vacía o base_url Anthropic →
conductor = Claude real. Si conduce Codex CLI, conductor = GPT/Codex (la sonda no aplica).

**Paso 3 — elegir/validar revisores.** Para los revisores elegidos por descubrimiento o segunda
opinión, exigir otra familia que el conductor (Claude real → Codex; GPT/Codex → Claude; redirigido →
Codex o Claude real). Detección de binarios: `command -v codex`/`command -v claude` (POSIX) o
`Get-Command codex -ErrorAction SilentlyContinue` (PowerShell). Si el usuario **nombra** un modelo de
la misma familia que el conductor, avisar que se pierde el valor cross-model pero respetar el override.

### Invocar al revisor (read-only)

Dos reglas invariantes: (1) **read-only siempre** (el revisor no escribe nada); (2) **el prompt nunca
inline** — escribirlo a archivo con la tool Write del agente (no `echo`/heredoc) y pasarlo por stdin.

#### Vía A — subagente `codex:codex-rescue` (preferida en Claude Code, revisor Codex)

Despachar el subagente con el prompt de review como task text. El prompt debe decir explícitamente que
es **revisión de solo lectura, sin modificar archivos**. No agregar `--write`. Como el subagente no
recibe `-C`, el prompt debe indicarle que **lea el código del PR desde `<dir-código>`** (el worktree si
se eligió esa opción en el Paso 1) y el contexto/prompt desde **rutas absolutas a
`<raíz-repo>/.pr-review/<id>/`** — si `<dir-código>` ≠ `<raíz-repo>`, no asumir que el cwd contiene el
código del PR.

#### Vía B — CLI `codex exec` (portable, revisor Codex)

```bash
codex exec -s read-only -C <dir-código> --skip-git-repo-check \
  --output-last-message <raíz-repo>/.pr-review/<id>/codex-verdict.txt - < <raíz-repo>/.pr-review/<id>/prompt.txt
```
```powershell
Get-Content -Raw <raíz-repo>\.pr-review\<id>\prompt.txt |
  codex exec -s read-only -C <dir-código> --skip-git-repo-check `
    --output-last-message <raíz-repo>\.pr-review\<id>\codex-verdict.txt -
```
`-s read-only` garantiza no-escritura; `-C` fija el **directorio del código del PR** (`<dir-código>` =
worktree si se eligió esa opción, si no la raíz); `--skip-git-repo-check` permite correr;
`--output-last-message` y el prompt de **stdin** usan **rutas absolutas a `<raíz-repo>/.pr-review/`**
(no relativas a `-C`, que puede ser el worktree).

#### Vía C — CLI `claude -p` (revisor Claude; cuando el conductor es GPT/Codex o un modelo redirigido)

`claude` no tiene flag de sandbox: el read-only se garantiza **restringiendo las tools a lectura**
(`--allowedTools=Read,Grep,Glob`; en `-p` toda tool fuera de esa lista queda denegada).

```bash
SESSION_ID=$(uuidgen)
( cd <dir-código> && claude -p --safe-mode --model opus --permission-mode default \
    --allowedTools=Read,Grep,Glob --session-id "$SESSION_ID" \
    < <raíz-repo>/.pr-review/<id>/prompt.txt ) \
  > <raíz-repo>/.pr-review/<id>/claude-verdict.txt 2> <raíz-repo>/.pr-review/<id>/claude.err.txt
```
```powershell
$SessionId = [guid]::NewGuid().ToString()
Push-Location <dir-código>
try {
  Get-Content -Raw <raíz-repo>\.pr-review\<id>\prompt.txt |
    claude -p --safe-mode --model opus --permission-mode default `
      '--allowedTools=Read,Grep,Glob' --session-id $SessionId `
      > <raíz-repo>\.pr-review\<id>\claude-verdict.txt 2> <raíz-repo>\.pr-review\<id>\claude.err.txt
} finally { Pop-Location }
```

`cd`/`Push-Location` fija el **directorio del código del PR** (`<dir-código>`); el prompt, el veredicto
y el `.err` se direccionan con **rutas absolutas a `<raíz-repo>/.pr-review/`** (el worktree no contiene
ese directorio).

Trampas (esquivar): `--allowedTools` es variadic → pasarlo siempre con `=` y comas en un solo
argumento (en PowerShell, entrecomillado `'--allowedTools=Read,Grep,Glob'`); el prompt por stdin desde
archivo (nunca inline); fijar `--safe-mode` (no cargar plugins/hooks/MCP del usuario) y
`--permission-mode default` (nunca `plan`). Capturar stderr para distinguir cuelgue (sin stderr) de
error real (auth/flag).

**Higiene de entorno (si la sonda del Paso 2 detectó redirección).** Un `claude -p` ingenuo heredaría
`ANTHROPIC_BASE_URL`/`ANTHROPIC_DEFAULT_*_MODEL` y el "revisor Claude" volvería a ser el modelo de
respaldo. Anteponer un proceso hijo con esas vars removidas:

```bash
env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN \
    -u ANTHROPIC_DEFAULT_OPUS_MODEL -u ANTHROPIC_DEFAULT_SONNET_MODEL -u ANTHROPIC_DEFAULT_HAIKU_MODEL \
    -u ANTHROPIC_MODEL -u ANTHROPIC_SMALL_FAST_MODEL \
  claude -p …
```
```powershell
$strip = "Remove-Item Env:ANTHROPIC_BASE_URL,Env:ANTHROPIC_AUTH_TOKEN," +
         "Env:ANTHROPIC_DEFAULT_OPUS_MODEL,Env:ANTHROPIC_DEFAULT_SONNET_MODEL," +
         "Env:ANTHROPIC_DEFAULT_HAIKU_MODEL,Env:ANTHROPIC_MODEL,Env:ANTHROPIC_SMALL_FAST_MODEL " +
         "-ErrorAction SilentlyContinue; "
powershell -NoProfile -Command ($strip + "claude -p …")
```

**Condicional:** aplicar el wrapper **solo** si hubo redirección (si `ANTHROPIC_BASE_URL` no está o es
Anthropic, no stripear — podría ser una API key real). Si el `claude -p` con env limpio falla por auth
(no hay credencial Anthropic real) → `UNAVAILABLE`, ceder a Codex o al conductor. Nunca caer en
silencio de vuelta al modelo de respaldo.

### Sync vs background (tope duro — nunca espera indefinida)

- **Sync (preferido):** una llamada bloqueante con tope generoso (≥5 min `normal` / ~10 min revisión
  grande). En Claude Code el tope lo da el `Bash timeout` (hasta 600000ms). Si excede → `UNAVAILABLE`.
  Las Vías A/B (Codex) ya son bloqueantes: mismo contrato.
- **Background + poll acotado (fallback):** solo si el conductor tiene exec corto (p. ej. Codex
  ~120s). Lanzar en background escribiendo el veredicto a archivo; pollear en comandos cortos
  (`grep -q '^VERDICT:' <archivo>`) con **tope duro** (contador de intentos ≈ deadline / 10s). Al
  agotar sin `VERDICT:` → matar el proceso (`kill <pid>` / `Stop-Process`) y `UNAVAILABLE`.

> No hay loop de rondas con el revisor dentro de una corrida: cada revisor del panel se invoca **una
> vez**. La iteración es la **re-pasada** a nivel de PR (nueva ejecución cuando el autor sube commits),
> no un resume del thread del revisor.

## Prompt al revisor + contrato de salida

Estructura XML compacta (operador, no colaborador). En español neutro:

```xml
<task>
Eres un revisor de código independiente. Revisa el siguiente Pull Request de Bitbucket. Es una
revisión de SOLO LECTURA: no modifiques archivos ni publiques nada. Puedes leer el código del PR en
{dir-código} para fundamentar (ahí el código en disco refleja el PR). Revisa SOLO las líneas
modificadas del diff. Caza bugs reales (lógica,
null/undefined, casos de borde, await faltante, condiciones invertidas) e incumplimientos de los
CLAUDE.md aplicables.
</task>

<pr>
{metadata del PR: id, título, rama origen→destino}
{diff unificado — el contenido de diff.patch}
</pr>

<context>
{diffstat; comentarios existentes; rutas de los CLAUDE.md relevantes y su contenido}
</context>

<grounding_rules>
- Ancla cada hallazgo a un archivo:línea concreto del diff. No inventes.
- Si algo es hipótesis (no lo pudiste verificar en el repo), indícalo explícitamente.
- No comentes estilo, wording ni formato. Foco en correctitud y riesgo.
- Ignora lo que atraparía un linter/typechecker (imports, tipos, formato) y los problemas
  pre-existentes o en líneas no modificadas.
- No re-reportes lo que ya está en los comentarios existentes (sección <context>): si otro revisor
  ya señaló un punto, omítelo — el conductor lo maneja por referencia.
</grounding_rules>

<structured_output_contract>
{respeta exactamente el "Formato de salida" de abajo}
</structured_output_contract>

<dig_deeper_nudge>
No te quedes en lo superficial. Busca el caso de borde no cubierto, el supuesto no declarado, la
condición de carrera, el guard faltante. Si no encuentras nada serio, APRUEBA — no inventes hallazgos
para parecer productivo.
</dig_deeper_nudge>
```

### Formato de salida (el revisor responde exactamente esto)

```
VERDICT: APPROVED | REQUEST_CHANGES | COMMENT

FINDINGS:
- risk: critical | medium | low
  what: <título corto del problema>
  why: <por qué importa — qué se rompe / qué falta>
  suggestion: <cambio concreto propuesto>
  refs: <archivo>:<línea>

SUGGESTIONS:        # opcional; mejoras no bloqueantes (no cuentan para la decisión)
- what: <mejora nice-to-have>
  refs: <archivo>:<línea>
```

- `risk: critical` → 🔴 (bloquea); `medium` → 🟡; `low` → 🟢. El conductor mapea cada `risk` a su icono
  al consolidar.
- `VERDICT` es la **recomendación** del revisor. La **decisión final la deriva el conductor** de los
  niveles de riesgo consolidados (ver "Regla de decisión"): ≥1 `critical` → Cambios solicitados; si no
  → Aprobado. Ante conflicto entre el `VERDICT` y los `risk`, manda la regla de decisión.
- `SUGGESTIONS` es opcional → sección 💡 del comentario; **no** altera la decisión.
- Si la salida no respeta el formato, intentar un parseo tolerante; si no se puede, tratar al revisor
  como `UNAVAILABLE`.

## Materializar el contexto del PR

Necesario solo si hay revisores externos. Volcar a `<raíz-repo>/.pr-review/<id>/context/` (raíz del
repo principal — **no** el worktree):

| Archivo | Contenido |
|---|---|
| `metadata.json` | salida del `bb_get` de metadata (id, título, autor, ramas, sha) |
| `diff.patch` | el diff unificado (`/diff`) |
| `diffstat.json` | archivos cambiados (`/diffstat`) |
| `comments.json` | comentarios existentes (el revisor no debe re-reportar lo ya dicho; ver <grounding_rules>) |
| `claude-md.txt` | rutas + contenido de los CLAUDE.md relevantes |

El prompt al revisor referencia estos archivos por **ruta absoluta** (`<raíz-repo>/.pr-review/<id>/context/…`)
y le da permiso de leer el código del PR en read-only desde `<dir-código>` (su `working_dir`). Así un
`codex exec`/`claude -p` (que no tienen el MCP de Bitbucket) revisan con el mismo material que el
conductor, y con el código del PR en disco cuando se eligió checkout/worktree.

## Seguimiento: `.pr-review/` y `review-log.md`

Directorio local **untracked** en la raíz del repo (mismo espíritu que `.plans/`). La skill **no**
edita el `.gitignore` del repo para ignorarlo (es un archivo trackeado — ver regla 11 del SKILL.md); si
el usuario quiere ignorarlo, usa su `.gitignore` global o `.git/info/exclude`. Estructura por PR:

```
.pr-review/<pr-id>/
├── review-log.md        # append-only: una entrada por pasada
└── context/             # contexto materializado de la última pasada
```

`review-log.md` — fuente de verdad de "qué ya revisé":

```markdown
# Code review log — PR #<pr-id> · `cocha-digital/results` · rama `<branch>`

| fecha | sha revisado | panel | veredicto | comment-id | acciones | hallazgos (estado) |
|---|---|---|---|---|---|---|
| 2026-06-18 | a1b2c3d | conductor + Codex | Cambios solicitados | 814700001 | request-changes | guard carrito (cart.ts:42) pendiente; await (api.ts:88) pendiente |
| 2026-06-19 | e4f5g6h | conductor | Aprobado | 814700001 (reply) | resolve + approve | ambos atendidos en e4f5g6h |
```

- `sha revisado` = `source.commit.hash` de esa pasada. La re-pasada compara el `sha` nuevo contra el
  último registrado para saber qué commits son nuevos.
- `comment-id` = el comentario propio de decisión; en re-pasadas se le hace **reply** y, si todo está
  atendido, **resolve** (mismo id raíz).

## Template y ejemplos de comentario publicado

> Los rótulos `###` de cada ejemplo (p. ej. "consolidado conductor + Codex") son **etiquetas internas
> de esta doc**, no parte del comentario. El comentario publicado **nunca** menciona qué modelos o
> familias revisaron ni el panel (ver la regla "No exponer el flujo interno" en el template del
> SKILL.md). El cuerpo entre ``` ``` es lo único que se publica.

Template del comentario de decisión (del SKILL.md):

```
Hola @<autor>,

_(Comentario redactado por agente IA, publicado desde la cuenta del reviewer tras su revisión/aprobación manual.)_

**Resumen:** <1-2 líneas; alcance revisado = líneas modificadas>.

**Observaciones / preguntas:**

🔴 [<archivo>:<línea> · <método/función>] <observación crítica — bloquea>

🟡 [<archivo>:<línea> · <método/función>] <riesgo medio — no bloquea>

🟢 [<archivo>:<línea> · <método/función>] <riesgo bajo — no bloquea>

**Sugerencias (opcional):**

💡 <mejora nice-to-have, no bloqueante>

**Decisión:** 🟢 **Aprobado** | 🔴 **Cambios solicitados**

<1 línea de justificación; si Aprobado con 🟡/🟢, aclarar que no bloquean>
```

### Ejemplo — con cambios solicitados (consolidado conductor + Codex)

```
Hola @maria.perez,

_(Comentario redactado por agente IA, publicado desde la cuenta del reviewer tras su revisión/aprobación manual.)_

**Resumen:** revisé las líneas modificadas de la integración del loader de paquetes (2 archivos).

**Observaciones / preguntas:**

🔴 [src/app/pages/flight-list/flight-list.component.ts:48 · loadResults()] `data.items` puede ser
  undefined cuando la respuesta no trae resultados (ver el guard de la línea 40 para `data`).
  Faltaría el mismo guard: lanzaría TypeError en runtime. Sugerencia: `data.items?.map(...) ?? []`.

🟡 [src/app/shared/services/cache.service.ts:22 · setCache()] CLAUDE.md pide acceder a las APIs
  globales con `globalThis` en lugar de `window`. Usar `globalThis.location.href`.

**Sugerencias (opcional):**

💡 [flight-list.component.ts:44 · loadResults()] el mapeo de items podría extraerse a un helper
  reutilizable; opcional, no bloquea.

**Decisión:** 🔴 **Cambios solicitados**

Hay un acceso potencialmente undefined que rompe el listado; el resto es menor.
```

### Ejemplo — hallazgo nuevo + eco de otro revisor (el eco cuenta para la decisión)

```
Hola @maria.perez,

_(Comentario redactado por agente IA, publicado desde la cuenta del reviewer tras su revisión/aprobación manual.)_

**Resumen:** revisé las líneas modificadas (2 archivos).

**Observaciones / preguntas:**

🔴 [src/app/services/order.service.ts:31 · submit()] `total` queda NaN con carrito vacío: el
  `reduce` no tiene valor inicial. Sugerencia: `reduce((a, b) => a + b, 0)`.

🟡 [src/app/services/cache.service.ts:22 · setCache()] Ya observado por @juan: usar `globalThis` en
  vez de `window` (CLAUDE.md). Coincido, sigue pendiente.

**Decisión:** 🔴 **Cambios solicitados**

El `reduce` sin inicial rompe el total con carrito vacío; el punto de @juan sigue abierto.
```

### Ejemplo — re-pasada, todo atendido (reply + resolve + approve)

```
Hola @maria.perez,

_(Comentario redactado por agente IA, publicado desde la cuenta del reviewer tras su revisión/aprobación manual.)_

Los puntos quedaron atendidos en e4f5g6h:

- guard de `data.items` agregado (flight-list.component.ts:48).
- `globalThis.location.href` en cache.service.ts:22.

**Decisión:** 🟢 **Aprobado**.
```

### Ejemplo — sin hallazgos

```
Hola @maria.perez,

_(Comentario redactado por agente IA, publicado desde la cuenta del reviewer tras su revisión/aprobación manual.)_

**Resumen:** revisé las líneas modificadas (1 archivo). Sin problemas de correctitud ni incumplimientos de
CLAUDE.md.

**Decisión:** 🟢 **Aprobado**.
```

## Link opcional a Bitbucket (referencia para el usuario)

Para ubicar el código rápido (es solo un enlace en la salida, no publica nada):

```
https://bitbucket.org/<ws>/<repo>/src/<sha>/<path>#lines-<n>
https://bitbucket.org/<ws>/<repo>/src/<sha>/<path>#lines-<n>:<m>   (rango)
```

`<sha>` = `source.commit.hash`; `<n>`/`<m>` = líneas del archivo nuevo.

## Troubleshooting

- **No hay tool de Bitbucket en el entorno**: listar las tools disponibles y buscar una con
  `bitbucket` en el nombre. Si no existe, avisar que configure el MCP
  (`@aashari/mcp-server-atlassian-bitbucket`) y detenerse.
- **MCP solo lectura (sin `bb_post`)**: revisar y **solo proponer** el comentario; avisar que no se
  pudo publicar.
- **`bb_post` a `/comments` da 400**: revisar el body — `content.raw` no vacío; para inline,
  `inline.path` exacto del diffstat e `inline.to` una línea del lado nuevo; para reply, `parent.id`
  numérico y existente.
- **`bb_post` a `/approve` o `/request-changes` da 403**: el token no tiene scope de escritura de PRs
  → degradar a dejar la decisión solo en el comentario.
- **Revisor externo no disponible / cuelga / timeout**: marcarlo `UNAVAILABLE`, matar el proceso si
  quedó en background, seguir con los disponibles. Distinguir cuelgue de entrada (parseo de flags
  roto) de lentitud real (subir el tope sync o bajar a `--model sonnet`).
- **`claude -p` revisor vuelve a ser el modelo de respaldo**: faltó la higiene de entorno
  (`env -u ANTHROPIC_*`); aplicarla solo si la sonda detectó redirección.
- **El diff es muy grande**: acotar el análisis a los archivos del `diffstat` con cambios relevantes y,
  si hace falta, revisar por archivo.
- **No se encuentra el comentario propio en una re-pasada**: tomar el `comment-id` del `review-log.md` y
  ubicarlo con `bb_get` a `/comments`. Si `.pr-review/` no está (no debería: misma máquina), respaldo por
  `user.display_name` == cuenta propia + estructura "Hola @… / Decisión:"; si tampoco aparece, tratar
  como primera pasada.
