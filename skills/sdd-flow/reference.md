# sdd-flow — Referencia

Detalle operativo de la skill `sdd-flow`. El `SKILL.md` apunta acá cuando necesita la matriz de detección, el esquema de configuración o las plantillas de artefactos.

## Tabla de contenidos

- [Matriz de detección por capacidad](#matriz-de-detección-por-capacidad)
- [Flujo por tracker](#flujo-por-tracker)
- [Aprobación externa de la spec (Jira)](#aprobación-externa-de-la-spec-jira)
- [Detección de stack y comandos](#detección-de-stack-y-comandos)
- [Esquema de `.specify/config.yml`](#esquema-de-specifyconfigyml)
- [Qué escribe `init`](#qué-escribe-init)
- [Mapeo tipo de cambio → prefijo](#mapeo-tipo-de-cambio--prefijo)
- [Construcción del mensaje de commit](#construcción-del-mensaje-de-commit)
- [Apertura de PR (opcional, tras push)](#apertura-de-pr-opcional-tras-push)
- [Plantilla de constitution](#plantilla-de-constitution)
- [Plantilla de spec](#plantilla-de-spec)
- [Plantilla de plan](#plantilla-de-plan)
- [Plantilla de plan combinado (trivial)](#plantilla-de-plan-combinado-trivial)
- [Plantilla de `## Verify`](#plantilla-de--verify)
- [Plantilla de tasks](#plantilla-de-tasks)
- [Plantilla de `handoff.md`](#plantilla-de-handoffmd)
- [Prompt del subagente por task](#prompt-del-subagente-por-task)
- [Prompt del subagente reviewer](#prompt-del-subagente-reviewer)
- [Ejemplo de criterios de aceptación](#ejemplo-de-criterios-de-aceptación)

---

## Matriz de detección por capacidad

Los nombres de tools/MCP cambian entre entornos. Resolver por **capacidad**: probar la tool canónica, y si no existe, buscar variantes por keyword antes de degradar.

| Capacidad | Cómo intentarlo | Fallback / degradación |
|---|---|---|
| Lectura de tracker | Buscar MCP/CLI cuyo nombre contenga el tracker detectado (`jira`/`atlassian`, `github`/`gh`, `gitlab`/`glab`, `linear`). | Pedir al usuario que pegue el resumen del issue; o trabajar solo con el prompt. |
| Host de Git (rama remota, PRs) | CLI del host (`gh`, `glab`) o MCP equivalente. | `git ls-remote --heads origin <branch>` para existencia; abrir PR manualmente. |
| Reproducción en navegador | Cualquier tool con `chrome`/`browser`/`playwright`/`devtools`. | Analizar sin repro; pedir al usuario captura/video/pasos. |
| Búsqueda en código | Subagente de exploración si el entorno lo soporta y el alcance lo amerita. | `grep`/`ripgrep`/`find` locales desde shell. |
| Debugging sistemático | Skill de debugging sistemático si está disponible. | Seguir el método manualmente: hipótesis → prueba mínima → refutar → repetir. |
| Commit convencional | **Construcción inline** (sin dependencia externa): ver "Construcción del mensaje de commit"; scope del ticket de la rama. | — (es inline: no hay skill de commit que descubrir). |
| Segunda opinión cross-model | Skill `sdd-cross-review` instalada + un segundo modelo de **otra familia que el autor** (subagente `codex:codex-rescue` o CLI `codex exec` si conduce Claude; CLI `claude -p` si conduce Codex). | Omitir la revisión y seguir con el gate humano (dependencia blanda; ver `SKILL.md` → "Revisión cross-model"). |

> Regla: antes de fallar por "tool X no existe", listar las tools disponibles y buscar coincidencias por capacidad/keyword. Solo entonces avisar y degradar.

## Flujo por tracker

Cómo traer el issue una vez detectado el tracker. La clave `[A-Z][A-Z0-9]+-\d+` sola no dice el tracker: resolverlo por `config.yml` (`tracker:`) o por el MCP/CLI disponible. Fijar `tracker:` en `config.yml` hace este paso **determinista** (evita ambigüedad cuando hay varios trackers).

Estos son ejemplos por tracker; los nombres de tools cambian entre entornos, así que descubrir por capacidad (ver matriz).

- **Jira / Atlassian** (MCP típico): el `getJiraIssue` necesita un `cloudId`, no solo la clave. Flujo:
  1. `getAccessibleAtlassianResources` → obtener el `cloudId` del sitio (cachearlo para la sesión).
  2. `getJiraIssue` con `{ cloudId, issueIdOrKey: "<CLAVE>" }`.
  3. Extraer `summary`, `issuetype.name` (→ prefijo, ver "Mapeo tipo de cambio → prefijo"), `description` (renderizar ADF a texto), `priority`, `labels`, `status`, links.
  4. **Escritura (solo para el gate `publish-spec`; ver "Aprobación externa de la spec (Jira)").** Descubrir por capacidad que el MCP/CLI permite **escribir** (si es solo-lectura → degradar, no bloquear). Operaciones: crear subtarea con `createJiraIssue` (`{ cloudId, fields: { project, parent: { key: "<padre>" }, issuetype: { name: "<subtask>" }, summary, description } }`); el **nombre del issuetype de subtarea** varía ("Subtarea"/"Sub-task") → tomarlo de `jira_approval.subtask_issuetype` o descubrirlo con `createmeta` (el issuetype con `subtask: true`). Actualizar descripción con `editJiraIssue`; comentar con `addCommentToJiraIssue` (el cuerpo va en ADF y admite nodos `mention` con `accountId` para etiquetar al autor de una observación; ver "Comentario de ajuste"); transicionar con la operación de transición del MCP. **Toda** escritura va con el STOP de write-safety (recurso + contenido a la vista antes de ejecutar).
- **GitHub** (`gh` o MCP): `gh issue view <n> --json title,body,labels,state` (o la API del MCP). El "tipo" sale de labels (`bug`, `enhancement`, …).
- **GitLab** (`glab` o MCP): `glab issue view <n>`; tipo desde labels.
- **Linear** (MCP): traer el issue por identificador; el estado/etiquetas mapean al prefijo.
- **`none`**: sin tracker; usar el contexto del prompt y, si falta, preguntar tipo/título/objetivo.

## Aprobación externa de la spec (Jira)

Detalle del gate `publish-spec` (ver `SKILL.md` → "Paso `publish-spec`" y, al retomar, `resume` → "Gate de Jira"). Solo aplica con `tracker: jira`, `jira_approval.mode: on` (u override de la corrida) y un MCP de Atlassian con escritura.

### Payload de la subtarea
- **Tipo:** subtarea (`issuetype` subtask) con el ticket `<id>` como **padre**.
- **Título:** `SPEC: <título corto>`.
- **Descripción (ADF)**, en este orden — primero el resumen no técnico, luego la definición técnica:

```markdown
## Resumen
**Problema / Objetivo:** <en lenguaje de negocio, sin jerga técnica>
**Alcance:** <qué entra>
**Fuera de alcance:** <qué queda afuera, explícito>
**Criterios de aceptación:**
1. <AC-1 reexpresado como resultado observable para el PO/TL>
2. <AC-2 ...>

---

## Definición técnica
<cuerpo de spec.md (Problema/Objetivo, Alcance, Criterios de aceptación AC-n,
Clarifications) **prácticamente literal** — solo se le aplica la sanitización acotada
de abajo; no se abstrae ni se reescribe el contenido técnico>
```

### Sanitización (qué NUNCA se publica)
Es **acotada**: solo se quitan las tres cosas de abajo. **Todo lo demás se publica tal cual, sin abstraer ni resumir** — incluidos los `AC-n`, las referencias a métodos/funciones, fragmentos de código y los **paths de código fuente del proyecto** (p. ej. `src/app/.../foo.service.ts`): son parte legítima del diseño técnico.
- Menciones a **cross-review** / **co-exploración** / segunda opinión / modelos / `review-log`.
- **URLs y entornos locales o de prueba:** `localhost`, `127.0.0.1`, hosts de desarrollo (p. ej. `http://local.<proyecto>.dev:4200`), `file://`, y cualquier indicación de "dónde/cómo probar" local.
- **Artefactos y mecánica del flujo SDD:** `.plans/`, `.specify/`, paths absolutos de la máquina local, los archivos del propio flujo (`spec.md`/`plan.md`/`tasks.md`/`handoff.md`), `status`, prefijos de rama, comandos de test/build, y nombres de fases del flujo (`analyze`, `clarify`, `tasks`, …).
- Los `AC-n` **se mantienen con su etiqueta** en la definición técnica; en el bloque "Resumen" además se reexpresan en lenguaje de negocio.

### Comentario de ajuste (tras observaciones)
Cuando el TL/PO dejan observaciones y se corrige la `spec.md`: actualizar la descripción de la subtarea con la spec corregida (sanitizada) y agregar **un único comentario consolidado que @menciona al/los autor(es) de las observaciones** (un bullet por observación atendida; cada escritura con su STOP de write-safety):

```markdown
@<autor-de-la-observación> — ajustes tras la revisión:
- <qué cambió — un bullet por observación atendida>

La descripción quedó actualizada con la versión vigente. Vuelve a revisión.
```

- **Cómo se etiqueta:** el cuerpo va en ADF con un nodo `mention` (`{ type: "mention", attrs: { id: "<accountId>" } }`); el `accountId` sale del autor de cada comentario leído por MCP. Si hay varios autores, mencionarlos a todos en la misma línea.
- **Degradación:** si el MCP no acepta menciones ADF o no se pudo resolver el `accountId` → publicar el mismo comentario consolidado **sin** la @mención (no bloquear). Nunca se responde en el hilo de cada comentario: los comentarios de Jira son planos en la API.

### Detección de aprobación (loop, resumen)
Contrato completo en `SKILL.md` → `resume` → "Gate de Jira". En síntesis: "ya aprobaron" → confiar; "revisa el ticket"/silencio → leer estado + comentarios nuevos; **observaciones** → corregir + re-publicar (descripción) + comentar + volver a `awaiting`; **aprobado** (señal de `approval_signal`, o confirmación del usuario si es `ask`) → seguir a `create-branch`. El estado vive en el frontmatter de `handoff.md` (`gate_status: awaiting | changes-requested | approved`).

## Detección de stack y comandos

Resolver en este orden: `config.yml` → manifiesto del repo → preguntar. Comandos sugeridos por stack (ajustar al gestor real presente):

| Stack | Manifiesto | test_cmd típico | build_cmd típico | Acotar test a un archivo |
|---|---|---|---|---|
| Node | `package.json` | `npm test` / `pnpm test` / `yarn test` (leer `scripts`) | `npm run build` (si existe el script) | según runner: `jest <patrón>`, `vitest run <patrón>`, `ng test --include=<ruta-exacta.spec.ts>` |
| Go | `go.mod` | `go test ./...` | `go build ./...` | `go test ./ruta/... -run <Test>` |
| Rust | `Cargo.toml` | `cargo test` | `cargo build` | `cargo test <nombre>` |
| Python | `pyproject.toml` / `pytest.ini` / `setup.cfg` | `pytest` | (suele no compilar) | `pytest path/to/test_x.py::test_y` |
| Java | `pom.xml` / `build.gradle` | `mvn test` / `gradle test` | `mvn package` / `gradle build` | `mvn -Dtest=ClassName test` |
| .NET | `*.csproj` / `*.sln` | `dotnet test` | `dotnet build` | `dotnet test --filter <expr>` |

Determinar el **gestor de paquetes** en Node por lockfile: `package-lock.json` → npm, `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn, `bun.lockb` → bun.

**Rama base:** precedencia = (a) **override de base de la corrida** (el usuario pidió cortar desde una rama X; ver `SKILL.md` → router y `create-branch` paso 2) → (b) `default_branch` del `config.yml` → (c) **detección**: `git symbolic-ref --short refs/remotes/origin/HEAD` devuelve `origin/<rama>`; fallback `git remote show origin | sed -n 's/.*HEAD branch: //p'`. **Normalizar a la rama local** quitando el prefijo `origin/` antes de operar (`origin/main` → `main`): posicionarse con `git checkout <rama-local>` + `git pull --ff-only origin <rama-local>`, **nunca** `git checkout origin/<rama>` (deja *detached HEAD*). Nunca asumir `main`/`master`. Con override de base, X puede ser **local o estar adelantada del remoto**: hacer el `pull --ff-only` **solo si X tiene upstream** (`git rev-parse --abbrev-ref --symbolic-full-name @{u}` no falla); si no, cortar desde el HEAD local de X. El override no toca `config.yml`.

**Host de Git:** parsear `git remote get-url origin` y buscar `github.com`, `gitlab`, `bitbucket` u otro dominio; define qué CLI/MCP usar para PRs y detección de rama remota.

## Esquema de `.specify/config.yml`

Todos los campos son opcionales; lo que falte se autodetecta. **No se trackea**: igual que el resto de `.specify/` y `.plans/`, es local (el ignore local lo gestiona el usuario, p. ej. vía `.git/info/exclude`).

```yaml
# .specify/config.yml — overrides de adaptación para sdd-flow
stack: node                      # node | go | rust | python | java | dotnet | other
test_cmd: "npm test"
build_cmd: "npm run build"       # omitir si el stack no compila
lint_cmd: "npm run lint"         # opcional
default_branch: main             # rama base; auto si se omite
branch_format: "{type}/{ticket}-{slug}"   # {type} {ticket} {slug}
branch_prefix: ""                # opcional; reemplaza {type} (p. ej. "feature/"); vacío → prefijo semántico
commit_style: conventional       # conventional | plain
tracker: jira                    # jira | github | gitlab | linear | none
test_scope_hint: "vitest run {name}"      # plantilla de COMANDO para acotar tests; {name} = archivo/patrón
cross_review:                    # segunda opinión cross-model (opcional; ver skill sdd-cross-review)
  mode: auto                     # auto (por complejidad) | "on" | "off"  (on/off entre comillas: sin ellas YAML los parsea como booleanos)
  execution: auto                # auto | sync | background — cómo corre la revisión (se hereda a sdd-cross-review)
  artifacts: [spec, plan, tasks] # qué artefactos revisar
  max_rounds: 3
  reviewer: auto                 # auto (descubre por capacidad; nunca la familia del autor) | claude | codex
  co_explore:                    # exploración paralela cross-model (opcional; ver skill co-explore)
    mode: auto                   # auto (por complejidad: complejo on, normal opt-in, trivial nunca) | "on" | "off"
    deadline: 600                # segundos; default 600 en `explore` (pre-spec), 300 en `counter-plan` (pre-plan) salvo override
jira_approval:                   # aprobación externa de la spec en Jira (opcional; solo si tracker: jira)
  mode: "off"                    # "off" | "on"  (default off; entre comillas: sin ellas YAML los parsea como booleanos)
  subtask_issuetype: auto        # auto (descubrir por createmeta) | "Subtarea" | "Sub-task"
  approval_signal: ask           # ask | status:"<estado Jira que cuenta como aprobado>"
implement_mode: ask              # cómo ejecutar las tasks: ask (preguntar en el último gate) | inline | subagent
```

Placeholders de `branch_format`: `{type}` (prefijo efectivo), `{ticket}` (clave del tracker, se omite si no hay), `{slug}` (2-5 palabras del título en kebab, sin acentos, `[a-z0-9-]`).

**`test_scope_hint`** es una **plantilla de comando completa**, no un glob suelto: se reemplaza `{name}` por el archivo/patrón a acotar y se ejecuta tal cual (ej.: `vitest run {name}`, `ng test --include={name}`, `pytest {name}`). En Angular, `{name}` debe ser la **ruta exacta** del `.spec.ts`, **no** un glob `**/…`: el glob arrastra `.html`/`.scss` y rompe el loader.

**Prefijo efectivo (`{type}`)** = primer valor presente: (1) override conversacional de la corrida → (2) `branch_prefix` del `config.yml` → (3) prefijo semántico (tabla de abajo). Se normaliza quitando la barra final si la trae. El `branch_prefix`/override **reemplazan** el `{type}`; el mapeo semántico de abajo aplica **solo cuando no hay ninguno de los dos**.

## Qué escribe `init`

El paso `init` (ver `SKILL.md` → "Paso `init`") materializa `.specify/` a pedido mediante un **wizard** de selección (campos de decisión) + autodetección (comandos), creando **ambos** archivos con valores ya resueltos, no plantillas vacías:

1. **`.specify/config.yml`** — relleno con lo que la autodetección encontró (no se deja en blanco). Ejemplo de un repo Node con Angular detectado:

   ```yaml
   # .specify/config.yml — generado por `/sdd-flow init` (editable a mano)
   stack: node
   test_cmd: "npx ng test"
   build_cmd: "npm run build"
   lint_cmd: "npm run lint"
   default_branch: master
   branch_format: "{type}/{ticket}-{slug}"
   branch_prefix: ""            # vacío → prefijo semántico
   commit_style: conventional
   tracker: jira
   test_scope_hint: "ng test --include={name}"   # {name} = ruta exacta del .spec.ts (no glob **/…: rompe el loader)
   ```

   Los campos de decisión (`tracker`, `commit_style`, `branch_prefix`, `implement_mode`, `cross_review`, `jira_approval`) se eligen en el **wizard** (2 pantallas, con el valor actual/detectado pre-seleccionado); los comandos (`test_cmd`/`build_cmd`/`lint_cmd`/`test_scope_hint`) se autodetectan y quedan editables en la confirmación final. Nada se inventa. Al escribir el `config.yml`, `cross_review.mode`, `co_explore.mode` y `jira_approval.mode` se emiten con `on`/`off` **entre comillas** (`"on"`/`"off"`): sin ellas YAML los parsea como booleanos.

2. **`.specify/constitution.md`** — desde "Plantilla de constitution" (abajo), con el puntero a los principios de código del repo (`CLAUDE.md`/`AGENTS.md`/`CONTRIBUTING.md`) si existen.

Ambos son **locales y untracked** (regla #10). Si ya existen, `init` no los pisa: el wizard muestra los valores vigentes **pre-seleccionados** para mantener o cambiar, y al confirmar fusiona respetando lo puesto a mano.

## Mapeo tipo de cambio → prefijo

Aplica solo cuando no hay `branch_prefix` ni override de prefijo. Derivar de la metadata del tracker (si la hay) o del contexto:

| Tipo de issue / contexto | Prefijo |
|---|---|
| Story, New Feature, Feature | `feature` |
| Bug, Defect | `fix` |
| Task, Improvement, Tech Debt | `refactor` (o `chore` si es build/CI/deps/config) |
| Test, QA | `test` |
| Documentation | `docs` |
| No encaja | preguntar |

> **Para features, el prefijo de rama es siempre `feature`, nunca `feat`.** No confundir con el
> `change_type` del header del plan ni con el tipo del conventional commit, que siguen siendo
> `feat` (`feat(ABC-123): …`): `feat` es vocabulario de commits; en nombres de rama va la
> palabra completa.

Ejemplos de rama: `feature/ABC-123-export-csv`, `fix/PROJ-9-null-cart`, `chore/bump-deps` (sin ticket).

## Construcción del mensaje de commit

El paso 7 de `implement` (ver `SKILL.md` → "Paso común", paso 7) construye y ejecuta el commit **inline, sin depender de ninguna skill externa**. Reglas (patrón de commits convencionales, internalizadas):

### Resolución del scope (ticket) — primer match gana
1. **Ticket del flujo:** el `id` del header del `plan.md`, si matchea `[A-Z][A-Z0-9]+-\d+`.
2. **Extracción de la rama:** primer `[A-Z][A-Z0-9]+-\d+` en el nombre de rama (`feature/ABC-123-slug` → `ABC-123`).
3. **Sin ticket:** omitir el scope (no inventarlo): `type: subject`.

### Formato

```
type(TICKET): subject

<body opcional>
```

- **`type`:** el `change_type` del header (`feat` | `fix` | `refactor` | `chore` | `docs` | `test` | `perf`). Es vocabulario de commits: acá va `feat`, **no** `feature` (esa palabra es solo para el prefijo de rama).
- **`subject`:** imperativo presente, **en español por defecto** (salvo que el usuario indique otro idioma), minúscula inicial, línea total (`type(scope): subject`) **< 72 chars**.
- **`body`:** solo cuando el cambio abarca varios temas; lista de bullets. Los `E-n` de `## Extras` van como bullets del body.
- **Sin firmas:** **nunca** `Co-Authored-By` ni líneas de firma al pie.
- **`commit_style: plain`:** mensaje plano, sin `type(scope)`.

### Staging
Respetar el staging ya armado por el paso 6 (`code_touched`). **Nunca** `git add -A` / `git add .` por cuenta propia.

### Ejecución (heredoc)
Commitear siempre con heredoc, para que un body multilínea sobreviva intacto:

```bash
git commit -m "$(cat <<'EOF'
fix(ABC-123): corrige el cálculo del total al aplicar el descuento

- <cambio 1>
- <cambio 2>
EOF
)"
```

Ejemplo de una sola línea: `fix(ABC-124): valida el rango de fechas en el buscador`.

### Si el commit falla
Ante un fallo (p. ej. hook de pre-commit que corre la suite): **mostrar el error y parar**. Nunca reintentar con `--no-verify` salvo pedido explícito del usuario.

## Apertura de PR (opcional, tras push)

Paso `open-pr` (paso 9 de `implement`; ver `SKILL.md` → "Paso común"). Se ofrece tras el push (`status: pushed`) y **solo crea el PR** — sin squash, sin rebase, sin force-push (sdd-flow ya dejó un commit atómico pusheado). Aplica cuando el host de Git es **Bitbucket** (ver "Detección de stack y comandos" → Host de Git). El `<workspace>/<repo>` se **derivan del remote** (`git remote get-url origin` → parsear; p. ej. `git@bitbucket.org:acme/webapp.git` → `acme/webapp`); destino = `base_branch` del header del `plan.md` si está (feature dependiente cortada de otra rama; PR **stacked**), si no `default_branch`.

### 1. MCP de Bitbucket (degradación elegante)
Probar `mcp__bitbucket__bb_get` a `/repositories/<workspace>/<repo>` (`jq: "name"`). Si no hay MCP o falla → **no bloquear**: mostrar título + descripción + rama para que el usuario cree el PR a mano, y seguir (regla 6).

### 2. Evitar duplicados
`bb_get` a `/repositories/<workspace>/<repo>/pullrequests` con `queryParams: { "q": "state=\"OPEN\" AND source.branch.name=\"<branch>\"", "pagelen": "5" }`. Si ya hay uno abierto, avisar y ofrecer actualizarlo en vez de crear otro.

### 3. Título
Primera línea del commit del flujo: `git log -1 --pretty=%s` (p. ej. `fix(ABC-123): corrige el cálculo del total…`).

### 4. Descripción (compacta — no volcar spec/plan literal)
Auto-rellenada desde los artefactos y **condensada**. Secciones:

```markdown
## Ticket
[<TICKET>](<site_url>/browse/<TICKET>)   <!-- <site_url> = URL del site del tracker (Jira: la resuelta por el MCP de Atlassian) -->
Spec: [<SUBTASK_KEY>](<jira_subtask_url>)   <!-- solo si se publicó la spec a Jira -->

## Problema
- <1-2 bullets del spec Problema/Objetivo, condensado>

## Solución
- <1-3 bullets del plan Enfoque + archivos clave (no listar todos)>

## Criterios de aceptación
- [ ] **AC-1** — <resultado observable, una línea>
- [ ] **AC-2** — <…>
```

- Los **AC** salen de `spec.md` (o `## Spec` del plan en triviales), una línea observable cada uno — hacen de checklist de verificación para el reviewer (absorben el "plan de pruebas": en sdd-flow son lo mismo).
- La línea **Spec** aparece **solo** si el flujo publicó la spec a Jira (`jira_subtask_url` en el header del `plan.md`). Si no, se omite.
- Mantener breve: sin Given/When/Then completos si son largos (viven en la spec), sin listados de archivos exhaustivos, sin copiar el plan.

### 5. Reviewers
Cargar los `account_id` de **`.specify/reviewers.json` del repo** (config personal por-repo; local y untracked como el resto de `.specify/` — regla #10). Esquema:

```json
{ "reviewers": [ { "display_name": "…", "account_id": "…", "username": "…" } ] }
```

Solo `account_id` viaja en el payload (`display_name`/`username` son informativos). **Excluir al autor** del PR (Bitbucket rechaza un PR con el autor como reviewer). Si un `account_id` da error 400, quitarlo del payload, reintentar y avisar para corregir el JSON. **Sin el archivo** → degradar sin bloquear (regla 6): crear el PR sin reviewers por defecto (u ofrecer que el usuario los indique) y sugerir crear `.specify/reviewers.json` para próximas corridas.

### 6. Preview + confirmación (write-safety, obligatorio)
Antes del `bb_post`, mostrar: workspace/repo, título, source, destination, `close_source_branch: true`, reviewers y la descripción completa. **Sin confirmación afirmativa, no crear.** Si el usuario pide cambios, aplicarlos y volver a mostrar el preview.

### 7. Crear
`mcp__bitbucket__bb_post`:

```json
{
  "path": "/repositories/<workspace>/<repo>/pullrequests",
  "body": {
    "title": "<título>",
    "source": { "branch": { "name": "<branch>" } },
    "destination": { "branch": { "name": "<base_branch del header, si está; si no default_branch>" } },
    "description": "<markdown>",
    "reviewers": [ { "account_id": "…" } ],
    "close_source_branch": true
  },
  "jq": "{id: id, title: title, url: links.html.href, reviewers: reviewers[*].display_name}"
}
```

### 8. Reportar y guardar
Reportar URL / ID / reviewers. Guardar `pr_url: <url>` en el header del `plan.md` y poner `status: pr-open` (trazabilidad, local).

> **Nunca** el agente aprueba (`.../approve`) ni mergea (`.../merge`) el PR: solo lo crea. El merge lo hace una persona en Bitbucket.

## Plantilla de constitution

`.specify/constitution.md` — principios de **proceso/calidad**, no de código.

```markdown
# Constitution — <proyecto>

## Definición de Done
Un cambio está "Done" cuando:
- Todos los criterios de aceptación de la spec están verificados.
- Tests del código tocado en verde.
- Build en verde (si el stack compila).
- Sin violar los principios de código del repo (ver Principios de código).

## Criterios de aceptación
- Numerados `AC-1..N`, observables y verificables.
- Formato preferido: Given/When/Then, o checklist de resultado observable.

## Trazabilidad
- Cada criterio de aceptación tiene ≥1 task que lo implementa.
- Cada task referencia el/los `AC-n` que cubre.

## Principios de código (puntero)
Los principios de código de este repo viven en: <CLAUDE.md | AGENTS.md | CONTRIBUTING.md | guía de estilo>.
spec/plan/tasks deben respetarlos; este constitution NO los duplica.
```

## Plantilla de spec

`.plans/<id>/spec.md` — el **QUÉ** y el **por qué**. Sin detalles de implementación.

```markdown
# Spec — <título corto>

## Problema / Objetivo
<por qué existe este cambio — del ticket + prompt, 1-3 párrafos>

## Alcance
- **Incluye:** <qué entra>
- **No incluye:** <qué queda explícitamente afuera>

## Criterios de aceptación
- **AC-1:** Given <contexto>, When <acción>, Then <resultado observable>.
- **AC-2:** <...>

## Clarifications
<Q&A registradas durante `clarify`. Vacío si no hubo.>
- **Q:** <pregunta> — **A:** <respuesta> (afecta: AC-n)
```

## Plantilla de plan

`.plans/<id>/plan.md` — el **CÓMO**. Empieza con el header YAML obligatorio (fuente del bootstrap de la Vía B).

```markdown
---
id: ABC-123
branch: feature/ABC-123-slug-corto
base_commit: <SHA del HEAD al escribir el plan>
# base_branch: feature/ABC-100-otra   # solo si se cortó de una rama != default_branch (override de base); es el destino del PR
change_type: feat
complexity: complex
status: planned        # planned → tasks-ready → implementing → verified → committed → pushed → (pr-open) → done
created_at: 2026-01-01T12:00:00-03:00
# wip_commit: <sha>            # solo si el flujo quedó pausado (ver sub-paso `pause`); se borra al retomar
# jira_subtask: ABC-145       # subtarea SPEC en Jira, si se publicó (gate `publish-spec`)
# jira_subtask_url: https://<tu-site>.atlassian.net/browse/ABC-145   # la usa `open-pr` para linkear la spec
# pr_url: <url>               # PR creado por el sub-paso `open-pr`, si se abrió
---

# Plan — <título corto>

## Enfoque
<estrategia técnica elegida; no listar alternativas descartadas>

## Archivos a tocar
- `ruta/al/archivo` — <qué cambia; reúso de `path:line` si aplica>

## Tests / build
- test: `<comando detectado/acotado>`
- build: `<comando detectado>`

## Verification
<pasos manuales/observables para validar end-to-end, ligados a los AC>

## Verify
<lo completa el paso `verify`; vacío hasta entonces>
| AC | Resultado | Evidencia | Fecha |
|---|---|---|---|
| AC-1 | ✅ / ❌ | <test / paso manual / salida observada> | <ISO-8601> |

## Extras (fuera de AC)
<cambios que entran al commit pero no mapean a ningún AC; vacío por default. Ver "Extras" en SKILL.md>
- E1 — <descripción corta del cambio> · `ruta/archivo.ts:200-210`
```

> **Header dinámico:** `status` lo actualiza la skill al cerrar cada paso (es la fuente de verdad de en qué fase quedó el flujo, leída por `resume`). `wip_commit` aparece solo si el flujo se pausó con cambios sin commitear; `jira_subtask`/`jira_subtask_url` solo si se publicó la spec a Jira (gate `publish-spec`); `pr_url` solo si se abrió PR (`open-pr`). Detalle del ciclo en `SKILL.md` → "Ciclo de status".

> Solo en cambios *triviales* la spec y las tasks van **embebidas** en `plan.md` (no se crean `spec.md`/`tasks.md` aparte). En *normal* la spec va en `spec.md` y las tasks en `tasks.md` (separados, aunque las tasks se aprueben en el gate del plan). Ver "Plantilla de plan combinado".

## Plantilla de plan combinado (trivial)

Para *trivial*, un único `plan.md` con la spec y las tasks **embebidas** — es lo que la Vía B y `verify` parsean cuando no existen `spec.md`/`tasks.md`:

```markdown
---
id: none
branch: fix/cart-null-guard
base_commit: <SHA del HEAD>
change_type: fix
complexity: trivial
status: planned
created_at: 2026-01-01T12:00:00-03:00
---

# Plan — <título corto>

## Spec
### Problema / Objetivo
<por qué — 1-2 párrafos>
### Criterios de aceptación
- **AC-1:** <observable y verificable>

## Enfoque
<cómo, breve>

## Archivos a tocar
- `ruta/al/archivo` — <qué cambia>

## Tasks
- [ ] T1 — <acción> · cubre: AC-1

## Verification
- <cómo se comprueba cada AC>

## Verify
<lo completa el paso `verify`>
| AC | Resultado | Evidencia | Fecha |
|---|---|---|---|
| AC-1 | ✅ / ❌ | <evidencia> | <ISO-8601> |

## Extras (fuera de AC)
<cambios sin AC que entran al commit; vacío por default. Ver "Extras" en SKILL.md>
- E1 — <descripción corta> · `ruta/archivo.ts:200-210`
```

## Plantilla de `## Verify`

El paso `verify` (ver `SKILL.md` → "Paso `verify`") completa la sección `## Verify` del `plan.md`. Tabla base — una fila por AC:

```markdown
## Verify
| AC | Resultado | Evidencia | Fecha |
|---|---|---|---|
| AC-1 | ✅ | `vitest run cart.spec` → 12 passed, exit 0 | 2026-01-01T12:00:00-03:00 |
| AC-2 | ❌ | el botón no se deshabilita con lista vacía | 2026-01-01T12:00:00-03:00 |
```

La **evidencia** es la salida fresca del comando que prueba *ese* AC (gate function del paso `verify`), no "los tests pasan" en general.

### Revert-to-confirm (solo `change_type: fix`)

Confirma que el test de regresión realmente cubre el bug: debe **fallar sin el fix**. Con el test en verde y el fix aislado en un archivo/hunk:

**POSIX** (macOS/Linux/Git Bash):
```bash
git stash push -- <archivo-del-fix>   # quita solo el fix (deja el test en el árbol)
<test_cmd acotado>                     # DEBE fallar — si pasa, el test no cubre el bug
git stash pop                          # restaura el fix
<test_cmd acotado>                     # vuelve a verde
```

**PowerShell** (Windows): mismos comandos git (`git stash push -- <archivo-del-fix>` / `git stash pop`); el runner de tests según el stack.

Si el fix y el test viven en el mismo archivo, revertir por hunk (`git stash -p` en POSIX) o aislar el cambio del fix antes del revert. Anotar el resultado (`revert → FAIL, restore → PASS`) como evidencia del AC en la tabla.

## Plantilla de tasks

`.plans/<id>/tasks.md` — descomposición atómica. Una task = un cambio coherente y, en lo posible, testeable. El objetivo es que cada task sea **autosuficiente**: ejecutable en una sesión fresca sin re-deducir el diseño ni tener que elegir otro enfoque.

Cada task es un **bloque** con estos campos:

```markdown
# Tasks — <título corto>

- [ ] **T1 — <acción concreta>**  · cubre: AC-1
  - **Por qué:** <qué AC habilita / la intención — 1 línea>
  - **Archivos:** `ruta/archivo.ts` (reúso de `fn()` en `path:line`); `ruta/archivo.spec.ts`
  - **Produce:** `nuevaFn(arg: Tipo): Resultado` — firma exacta que consume T2. *(solo si otra task la necesita)*
  - **Pasos:**
    1. (test rojo) <caso a agregar — qué debe fallar y por qué>
    2. `<comando de test acotado>` → FAIL esperado
    3. (impl) <enfoque + snippet ILUSTRATIVO de la firma/estructura clave>
    4. `<comando de test acotado>` → PASS
  - **Verificar:** <comando o paso manual ligado al AC>

- [ ] **T2 — <acción concreta>**  · cubre: AC-1, AC-2
  - **Por qué:** <…>
  - **Archivos:** <…>
  - **Consume:** `nuevaFn` de T1 (no repetir la firma — referenciarla). *(solo si usa algo de otra task)*
  - **Pasos:** <…>
  - **Verificar:** <…>

## Self-review (antes del gate)
- **Cobertura:** AC-1 → T1, T2 ✓ · AC-2 → T2 ✓ (sin AC huérfanos / sin tasks sin AC).
- **Anti-placeholder:** sin `TBD`/`TODO`/"agregar X apropiado"/"similar a T-N"/"etc." en plan ni tasks.
- **Interfaces:** cada `Produce` coincide exacto (nombre + firma) con el `Consume` que lo referencia.
```

> **Regla anti-sobre-especificación.** Los snippets de los Pasos son **ilustrativos**: muestran la *firma*, la *estructura* y los *casos a cubrir*, no la implementación final completa de cada archivo. El plan orienta la ejecución; el código exhaustivo se escribe en `implement`, no acá. En tasks puramente mecánicas (config, copy, bump) los Pasos pueden colapsarse a 1‑2 líneas — no inflar artificialmente.

Ejemplo concreto de una task:

```markdown
- [ ] **T1 — Persistir el borrador del formulario al recargar**  · cubre: AC-1
  - **Por qué:** AC-1 pide conservar lo que el usuario cargó cuando recarga la página.
  - **Archivos:** `src/app/shared/services/draft/draft-form.service.ts` (reúso de `this.form`); `draft-form.service.spec.ts`
  - **Pasos:**
    1. (test rojo) spec que mockea `globalThis.sessionStorage` y espera que al restaurar se lea la clave y se limpie.
    2. `ng test --include=src/app/shared/services/draft/draft-form.service.spec.ts` → FAIL (método no existe)
    3. (impl) `persistDraftOnReload()` serializa `this.form` a `sessionStorage` con guard `try/catch`.
    4. `ng test --include=src/app/shared/services/draft/draft-form.service.spec.ts` → PASS
  - **Verificar:** recargar la página en el navegador y confirmar que el borrador persiste.
```

## Plantilla de `handoff.md`

`.plans/<id>/handoff.md` — documento de **retomado** del flujo (ver `SKILL.md` → "`handoff.md` (retomado del flujo)"); vive en `.plans/<id>/` (local, untracked como el resto). Frontmatter YAML con los campos máquina + cuerpo narrativo legible.

```markdown
---
phase: awaiting-jira-approval   # specify | clarify | awaiting-jira-approval | implementing | ...
# snapshot de gather-context (presente mientras NO exista plan.md; cuando existe, manda plan.md):
complexity: normal              # trivial | normal | complex
change_type: feat               # feat | fix | refactor | chore | docs | test | perf
branch_prefix: feature          # el {type} ya resuelto
slug: export-csv
base_branch: master             # rama base resuelta (con override de base, la rama de la que se corta)
overrides: { branch_prefix: null, base_branch: null, cross_review: null, implement_mode: null, jira_approval: null }
# campos del gate de Jira (solo si es una pausa por aprobación externa):
gate_status: awaiting           # awaiting | changes-requested | approved
parent_key: ABC-123
subtask_key: ABC-145            # la subtarea "SPEC: ..." creada
jira_subtask_url: https://<tu-site>.atlassian.net/browse/ABC-145   # la usa `open-pr` para linkear la spec
cloud_id: <uuid del sitio>
---

# Handoff — <título corto> (<id>)

## Estado actual
<dónde quedó y por qué; próximo paso concreto>

## Objetivo / Alcance
<espejo breve del QUÉ e in/out — para leer sin abrir otro archivo>

## Decisiones / criterio asumido
<lo decidido por criterio propio que conviene validar; qué motivó la pausa/gate>

## Archivos del flujo
- spec.md — el QUÉ completo + Clarifications
- jira-spec.md — exactamente lo publicado en la subtarea (solo si hubo gate de Jira)
```

> **Precedencia:** cuando existe `plan.md`, su `status`/`wip_commit`/marcas `[x]` son la verdad operativa; el `handoff.md` aporta narrativa + overrides. Sin `plan.md` (specify/clarify/gate de Jira), el frontmatter es la fuente de verdad de esa ventana. Los campos del gate de Jira solo aparecen en pausas por aprobación externa. Detalle en `SKILL.md` → "Precedencia con `plan.md`".

## Prompt del subagente por task

Para el modo `subagent` de `implement` (ver `SKILL.md` → "Modo de ejecución"). El conductor
despacha **un agente fresco por task, secuencial**. El agente no puede invocar `sdd-flow` con el
Skill tool (la skill es solo-slash): el prompt le pasa el contrato directo. Plantilla:

```
Trabaja ÚNICAMENTE en el repo <ruta-absoluta-al-working-dir> (todo comando y ruta, relativos a él).
Contexto: lee .plans/<id>/plan.md (header + enfoque), .plans/<id>/spec.md (criterios de
aceptación) y la task "<n>. <título>" en .plans/<id>/tasks.md. (Si la complejidad es trivial,
spec y tasks están embebidas en el propio plan.md.) Implementa SOLO esa task, siguiendo sus
campos (Archivos / Pasos / Verificar) al pie de la letra.
Reglas duras:
- No re-diseñes: si la task no se puede ejecutar como está escrita, devuelve STATUS: failed con la
  razón — no improvises otro enfoque.
- Nada de git add/commit/push. No toques .plans/ ni .specify/ (las marcas [x] las pone el conductor).
- Ejecuta el comando del campo "Verificar" de la task (tests acotados con <test_scope_hint> si aplica).

Tu mensaje final debe ser EXACTAMENTE este reporte (sin prosa extra):
STATUS: done | failed
FAILURE_REASON: <1-3 líneas si failed; omitir si done>
FILES: <una línea por archivo tocado>
VERIFY: <comando ejecutado y resultado, en una línea>
NOTES: <decisiones/supuestos en 1-3 líneas; omitir si no hay>
```

### Cómo despachar según el entorno (por capacidad, no por nombre)

| Entorno conductor | Mecanismo |
|---|---|
| Claude Code | Subagente del entorno (Agent/Task tool), un despacho por task. |
| Codex CLI | Proceso hijo: escribir el prompt a un archivo con la tool de escritura (nunca interpolarlo inline en el shell — el markdown con backticks rompe el quoting); el `-` lee las instrucciones de stdin. **POSIX** (macOS/Linux/Git Bash): `codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --output-last-message <reporte.txt> - < <prompt.txt>`. **PowerShell** (Windows; no soporta `<`, el prompt va por el pipe): `Get-Content -Raw <prompt.txt> \| codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --output-last-message <reporte.txt> -`. Parsear el reporte del archivo. (Sin subagentes nativos: cada `codex exec` ES la sesión fresca.) |
| Otro | Cualquier mecanismo que corra un agente fresco con un prompt y devuelva su mensaje final. Sin ninguno → avisar en una línea y degradar a modo `inline` (regla 6). |

### Lado conductor (al volver cada subagente)

1. Validar `FILES` contra `git status --porcelain` → sumar a `code_touched` (regla 8). Si el
   agente tocó archivos fuera de `FILES`, el diff lo revela: son de esta corrida igualmente, pero
   anotar la discrepancia.
2. **Revisar el diff** de la task (disciplina de `receiving-code-review`): entender el cambio antes
   de aceptarlo. Si hay capacidad de despachar otro agente fresco, usar el **reviewer por-task**
   (ver "Prompt del subagente reviewer"): exige **spec ✅ + calidad ✅** para marcar `[x]`. Sin esa
   capacidad, revisión liviana del propio conductor (degradación, regla 6).
3. Marcar la task `- [x]` en `tasks.md`.
4. `STATUS: failed` o revisión con problemas → **máximo 1 reintento** re-despachando con el
   feedback concreto. Si falla de nuevo: parar y escalar al usuario.
5. Reporte ausente o no parseable → clasificar por `git status` + diff; las marcas `[x]` y el
   `status` del header siguen siendo la fuente de verdad del progreso.

Tests+build completos, `verify` de los AC, revisión manual, staging selectivo, commit, push y PR opcional:
**siempre el conductor** (pasos 3-10 del Paso común). Los STOPs no existen dentro de un subagente.

## Prompt del subagente reviewer

Para el **reviewer por-task** del modo `subagent` (ver `SKILL.md` → "Modo de ejecución", paso 2). Un agente fresco que **solo revisa** el diff de una task contra sus artefactos — no edita ni implementa. Distinto de `sdd-cross-review`: aquel es **cross-model** y revisa *artefactos de diseño* (spec/plan/tasks); este es un agente **del mismo modelo** que revisa el *diff* de una task ya implementada. Despacharlo por capacidad, igual que el implementer (sin capacidad → degradar a la revisión liviana del conductor). El conductor **interpola la lista `FILES`** del reporte del implementer en el prompt (el reviewer es un agente fresco: sin ella no sabe qué archivos revisar). Plantilla:

```
Trabaja en modo SOLO LECTURA sobre el repo <ruta-absoluta-al-working-dir>. No edites nada.
Revisa el diff de la task "<n>. <título>" contra sus artefactos:
- Archivos de la task (FILES del implementer): <lista de archivos, uno por línea>
- Diff de la task: `git diff -- <esos archivos>`. El working tree acumula los cambios de las
  tasks previas (el staging ocurre después): limita el diff a esos paths, y si otra task ya
  tocó el mismo archivo puede haber hunks ajenos — evalúa solo lo que corresponde a esta task.
- Contexto: .plans/<id>/spec.md (AC que la task habilita), .plans/<id>/plan.md (enfoque),
  y la task en .plans/<id>/tasks.md. (Si la complejidad es trivial, están embebidos en plan.md.)
Evalúa dos ejes:
- SPEC: ¿el diff cumple los AC que la task dice cubrir? (solo los suyos, no otros)
- CALIDAD: ¿sin code smells, sigue los patrones/estilo del repo, sin dead code ni placeholders?

Tu mensaje final debe ser EXACTAMENTE este reporte (sin prosa extra):
SPEC: ok | fail | warn
QUALITY: ok | fail
FINDINGS: <una línea por problema; vacío si todo ok>
NOTES: <"no verificable desde el diff" si un requisito vive en código no tocado; omitir si no aplica>
```

El conductor: **SPEC ok + QUALITY ok** → marcar la task `[x]`. `fail` en cualquiera → 1 reintento al implementer con `FINDINGS` como feedback (paso 3 del modo subagent). `warn` (no verificable desde el diff) no bloquea: el conductor lo resuelve antes de marcar.

## Ejemplo de criterios de aceptación

Contexto: feature "exportar resultados a CSV".

```markdown
- **AC-1:** Given una lista con resultados, When el usuario hace click en "Exportar CSV",
  Then se descarga un archivo `.csv` con una fila por resultado y encabezados de columna.
- **AC-2:** Given una lista vacía, When el usuario hace click en "Exportar CSV",
  Then el botón está deshabilitado y no se descarga nada.
- **AC-3:** Given valores con comas o comillas, When se genera el CSV,
  Then esos campos quedan correctamente escapados (RFC 4180).
```

Cada uno es observable y se puede mapear a un test o a un paso manual de verificación.
