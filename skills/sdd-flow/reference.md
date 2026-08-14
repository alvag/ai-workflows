# sdd-flow — Referencia

Detalle operativo de la skill `sdd-flow`. El `SKILL.md` apunta acá cuando necesita la matriz de detección, el esquema de configuración o las plantillas de artefactos.

## Tabla de contenidos

- [Matriz de detección por capacidad](#matriz-de-detección-por-capacidad)
- [Flujo por tracker](#flujo-por-tracker)
- [Aprobación externa de la spec (Jira)](#aprobación-externa-de-la-spec-jira)
- [Detección de stack y comandos](#detección-de-stack-y-comandos)
- [Esquema de `.specify/config.yml`](#esquema-de-specifyconfigyml)
- [Contexto de dominio](#contexto-de-dominio)
- [Doctor read-only](#doctor-read-only)
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
- [Revisión final de diff](#revisión-final-de-diff)
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
| Segunda opinión cross-model | Skill `cross-review` instalada + un segundo modelo de **otra familia que el autor** (subagente `codex:codex-rescue` o CLI `codex exec` si conduce Claude; CLI `claude -p` si conduce Codex). | Omitir la revisión y seguir con el gate humano (dependencia blanda; ver `SKILL.md` → "Revisión cross-model"). |

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

### Elección de rama

Qué hace `create-branch` cuando el HEAD **no** está parado en la base resuelta. El paso dispara la
decisión; el procedimiento vive acá. Nada mueve el HEAD hasta que la elección está tomada.

**Antes de ofrecer nada, clasificar el HEAD.** Dos estados no admiten ninguna salida y obligan a
**parar con diagnóstico**, porque cualquier resultado sería inválido:

- **detached** — `git symbolic-ref -q HEAD` falla: no hay rama que seguir ni que renombrar.
- **sin commits** — `git rev-parse HEAD` falla: el `base_commit` que exige el header del `plan.md` no
  existiría.

Si el nombre que el flujo construyó **es** el de la rama actual, no hay nada que elegir:

| Condición | Resultado | Motivo |
|---|---|---|
| el nombre construido coincide con la rama actual | seguir en la rama actual | las dos salidas de rama nueva chocarían contra la comprobación de existencia y el rename no tendría destino distinto |

**Cómo se pregunta** — descubrimiento por capacidad, como el resto de la skill. La opción recomendada
se marca, y la señal que la decide es si el `<id>` del flujo aparece en el nombre de la rama actual:
si aparece, esa rama ya es de este flujo; si no, es una iniciativa multi-fase y lo natural es quedarse.

| Condición | Medio | Recomendación |
|---|---|---|
| capacidad de selección presente | selección interactiva | (según `<id>`) |
| capacidad ausente | pregunta conversacional | (según `<id>`) |
| `<id>` en el nombre de la rama actual | — | rama nueva desde la base |
| `<id>` ausente del nombre | — | seguir en la rama actual |

**Las cuatro salidas.** En todas, `base_branch` —el destino del PR— sigue siendo la base resuelta,
salvo en la salida 3, que es la única que lo cambia a propósito: varios flujos sobre una rama
compartida se mergean una sola vez contra la base, no uno contra otro. Si el nombre construido **ya
existe** como rama, las salidas 2 y 3 **paran y avisan** con el nombre a la vista y vuelven a
**reofrecer las mismas salidas**: nunca un `checkout` sin `-b` a una rama ajena, nunca un sufijo
inventado.

1. **seguir en la rama actual** — no se ejecuta ningún comando que mueva el HEAD. `branch` = la rama
   actual, `base_commit` = `git rev-parse HEAD`, `base_branch` = la base resuelta.
2. **rama nueva desde la base** — el procedimiento de siempre: posicionarse en la base
   (`git checkout <base-local>` + `git pull --ff-only origin <base-local>`) y recién ahí
   `git checkout -b <nuevo>`.
3. **rama nueva desde la actual** — feature dependiente. Equivale al override de base con la rama
   actual como base: se corta desde el HEAD local sin pull, y `base_branch` pasa a ser la rama actual.
4. **renombrar la actual** — la salida 1 más un `git branch -m <nuevo>`: no crea rama ni mueve el
   HEAD. Sólo aparece cuando la rama actual es **sólo local** y el nombre construido difiere del
   actual — el caso de la rama abierta a mano antes de saber de qué se trataba la tarea. Tres
   precondiciones, las tres obligatorias:

   - **sólo local, con dos comprobaciones**: `git ls-remote --heads origin <rama>` devuelve vacío
     **y** `git rev-parse --abbrev-ref --symbolic-full-name @{u}` falla. La segunda sola no alcanza:
     una rama pusheada sin tracking la satisface igual.
   - **destino libre**: `git show-ref --verify --quiet refs/heads/<nuevo>` debe fallar.
   - **árbol limpio**: `git status --porcelain` vacío, la misma exigencia del paso 1.

   Cuándo **no** aparece la opción, y qué se dice en su lugar:

   | Estado | Decisión | Motivo |
   |---|---|---|
   | rama publicada (`ls-remote` con resultado o `@{u}` resuelve) | el rename no se ofrece | renombrarla exige push del nombre nuevo y borrado del viejo en el remoto |
   | `ls-remote` no ejecutable | el rename no se ofrece | no se puede descartar publicación; ante la duda no aparece |

   **Reparación, y por qué bloquea.** `.plans/` es local a cada worktree y el rename cambia una
   referencia que todos comparten. Recorrer los worktrees con `git worktree list --porcelain`,
   actualizar el header `branch:` de los `plan.md` cuyo valor sea el **nombre viejo** —sólo esos— e
   **informar cuántos** se tocaron. Si algún worktree no es accesible el rename se **bloquea** antes
   de ejecutarse: reparar a medias deja parte de los flujos apuntando a una rama que ya no existe, y
   entonces su `resume` ofrece recrearla desde su `base_commit`, que parte la historia en dos justo
   cuando creías estar retomando.

   POSIX:

   ```sh
   rama=$(git symbolic-ref --short -q HEAD) || exit 1
   nuevo=<nombre construido>
   # `ls-remote` que no se puede ejecutar NO es "vacío": sin poder descartar publicación, no se ofrece
   pub=$(git ls-remote --heads origin "$rama") || exit 1
   [ -z "$pub" ] || exit 1
   git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1 && exit 1
   git show-ref --verify --quiet "refs/heads/$nuevo" && exit 1
   [ -z "$(git status --porcelain)" ] || exit 1
   git branch -m "$nuevo"
   ```

   PowerShell:

   ```powershell
   $rama = git symbolic-ref --short -q HEAD
   if ($LASTEXITCODE -ne 0) { return }
   $nuevo = '<nombre construido>'
   $pub = git ls-remote --heads origin $rama 2>$null
   if ($LASTEXITCODE -ne 0 -or $pub) { return }
   git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null | Out-Null
   if ($LASTEXITCODE -eq 0) { return }
   git show-ref --verify --quiet "refs/heads/$nuevo"
   if ($LASTEXITCODE -eq 0) { return }
   if (git status --porcelain) { return }
   git branch -m $nuevo
   ```

## Esquema de `.specify/config.yml`

Todos los campos son opcionales salvo una excepción (`cross_model.schema_version`, obligatorio si el bloque `cross_model` existe); lo que falte se autodetecta. **No se trackea**: igual que el resto de `.specify/` y `.plans/`, es local (el ignore local lo gestiona el usuario, p. ej. vía `.git/info/exclude`).

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
cross_model:                     # políticas comunes a las skills cross-model (opcional)
  schema_version: 1              # obligatorio si el bloque existe; una versión desconocida se ignora entera con aviso, nunca se interpreta a medias
  families: [claude, codex]      # claude | codex — allowlist de workers; el conductor no entra
  selection: full                # full | user_choice — obligatorio con families; sin default
  manifest:                      # registro por corrida de las skills cross-model, para decidir con datos si la capacidad rinde
    mode: "on"                   # "on" (default) | "off"  (entre comillas: sin ellas YAML los parsea como booleanos). Política del ECOSISTEMA: las tres skills escriben el mismo registro; apagarlo para una sola dejaría huecos sistemáticos. Ver `cross-review/reference.md` → "Manifest de corrida"
jira_approval:                   # aprobación externa de la spec en Jira (opcional; solo si tracker: jira)
  mode: "off"                    # "off" | "on"  (default off; entre comillas: sin ellas YAML los parsea como booleanos)
  subtask_issuetype: auto        # auto (descubrir por createmeta) | "Subtarea" | "Sub-task"
  approval_signal: ask           # ask | status:"<estado Jira que cuenta como aprobado>"
implement_mode: ask              # cómo ejecutar las tasks: ask (preguntar en el último gate) | inline | cross (delegar a la otra familia vía `cross-implement`; requiere esa skill + el CLI de la otra familia)
domain_context:
  mode: auto                     # auto | "on" | "off"; solo lectura, nunca escribe ADRs/docs
  context_paths: []              # docs de dominio/glosarios/arquitectura a leer si existen
  adr_paths: []                  # ADRs o decisiones vigentes a leer si existen
final_diff_review:
  mode: auto                     # auto (complex/high-risk inline) | "on" | "off"
```

**Este bloque es dueño de las 22 claves que `sdd-flow` gobierna.** Las 12 restantes las poseen sus
hermanas y su enum se define allá: `cross_review.*` en `cross-review/SKILL.md` → "Configuración";
`co_explore.*` en `co-explore/SKILL.md` → "Configuración"; `cross_implement.*` en
`cross-implement/SKILL.md` → "Configuración". El archivo **completo**, con las 34 juntas y listo
para copiar, está en `config-ejemplo.md`, que es una vista de todos estos dueños.

Placeholders de `branch_format`: `{type}` (prefijo efectivo), `{ticket}` (clave del tracker, se omite si no hay), `{slug}` (2-5 palabras del título en kebab, sin acentos, `[a-z0-9-]`).

**`test_scope_hint`** es una **plantilla de comando completa**, no un glob suelto: se reemplaza `{name}` por el archivo/patrón a acotar y se ejecuta tal cual (ej.: `vitest run {name}`, `ng test --include={name}`, `pytest {name}`). En Angular, `{name}` debe ser la **ruta exacta** del `.spec.ts`, **no** un glob `**/…`: el glob arrastra `.html`/`.scss` y rompe el loader.

**Prefijo efectivo (`{type}`)** = primer valor presente: (1) override conversacional de la corrida → (2) `branch_prefix` del `config.yml` → (3) prefijo semántico (tabla de abajo). Se normaliza quitando la barra final si la trae. El `branch_prefix`/override **reemplazan** el `{type}`; el mapeo semántico de abajo aplica **solo cuando no hay ninguno de los dos**.

### Dominio de `families`

| Aspecto | Decisión |
|---|---|
| Tokens | enum cerrado `claude` · `codex`. Cualquier otro → **error** |
| Forma | lista. Escalar → **error**. Lista vacía → **error** |
| Duplicados | → **error**; no se deduplica en silencio |
| Case | se acepta cualquier case y se **canoniza a minúsculas** en el eco |
| Orden | **no semántico**: es un conjunto. `[claude, codex]` ≡ `[codex, claude]` |
| Semántica | allowlist de **workers despachables**; el **conductor no entra en ella** |
| Proceso | cada worker corre como proceso aparte en **sesión fresca**, incluso si comparte la familia del conductor |
| Declarar menos | es una preferencia válida: solo se despacha a las familias declaradas |
| Preflight | comprobar el CLI en PATH de cada familia declarada, **la del conductor incluida**; que el conductor esté corriendo por construcción **no exime del preflight** de su worker |
| Clave ausente | → resolver, preguntar y persistir antes de cualquier despacho; ver "Resolución de la selección" |
| `selection` | obligatorio con `families`; enum `full | user_choice`, sin default |
| schema_version en .specify/config.yml | **no sube**: el bloque ya existe con `schema_version: 1`; al crearlo se emite ese valor |
| schema_version en manifest.yml | **se introduce en este cambio, con valor `1`**; es obligatorio si el bloque nuevo existe y la obligación nace en esa superficie |

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

El inventario declarado viaja en el contrato de invocación con este carrier:

```yaml
family_inventory:                # ausente = resuélvelo tú, eres la raíz
  families: [claude]             # conjunto resuelto y canonizado a minúsculas
  source: declared               # ÚNICO valor: sin declaración no se construye el carrier
  selection: user_choice         # elección heredada; no se recalcula
  root: sdd-flow                 # quién lo resolvió y, por lo tanto, quién ya avisó
```

Sus cuatro reglas son obligatorias:

1. **Presente implica heredado:** el receptor no relee config, no vuelve a auditar y no vuelve a
   anunciar la ausencia.
2. **La skill anidada hereda la elección:** recibe `selection` junto a `families`; no sondea ni
   reconstruye si el usuario declaró menos workers que los presentes.
3. **Sin declaración no hay carrier:** solo se construye desde una declaración válida en
   `config.yml`, `manifest.yml` o un override conversacional. La autodetección nunca se propaga como
   `source: detected`.
4. **`root` identifica al dueño único del aviso:** no es un dato decorativo.

El conjunto cerrado de consumidores es `sdd-flow`, `sdd-orchestrator`, `cross-review` —incluido
draft—, `cross-implement` y `co-explore` —sus cuatro modos—. `bitbucket-code-review` queda
explícitamente excluido.

En una invocación directa, la fuente es `<working_dir>/.specify/config.yml` y la precedencia es
override conversacional > config > autodetección. La raíz se deriva del artefacto o work order
recibido. Si no existe una raíz única, se falla pidiendo `working_dir` explícito; nunca se busca
config hacia arriba ni fuera del directorio nombrado.

### Resolución de la selección

Si `families` ya está persistida, **se lee la declaración** y no se descubren familias fuera de
ella. El preflight sí corre, pero mira solo los workers declarados. El descubrimiento queda
**condicionado a la ausencia** de `families`; solo si no hay declaración se ejecutan estos pasos,
en orden y antes de invocar cualquier skill cross-model:

1. Proponer una selección inicial de workers.
2. Detectar qué familias tienen un CLI despachable.
3. Si hay otra familia presente, preguntar si se suma a la selección.
4. Presentar un STOP con el **delta exacto** y persistir la selección confirmada.
5. Aplicar el ruteo de cada skill y recién entonces despachar: **ningún worker sale antes**.

El STOP hace un merge **no destructivo**: preserva el resto del archivo, crea `.specify/` y el
bloque `cross_model` si faltan y emite `schema_version: 1` cuando el bloque nace. Persiste
`families` y `selection` en `.specify/config.yml`; en una raíz `sdd-orchestrator`, el destino es el
`manifest.yml` de la orquestación. Una sola familia instalada recibe el mismo STOP para persistir
`[<familia-del-conductor>]` con `selection: full`. Ninguno de los dos destinos se escribe sin
permiso explícito tras mostrar el delta.

### Migración de declaraciones sin `selection`

Si una declaración vigente de `families` **no declara cómo se resolvió**, abrir un único STOP que
muestre esa lista y ofrezca `full` o `user_choice`. Se persiste con el mismo merge no destructivo y
el mismo delta exacto de la resolución inicial. En este STOP **no se infiere un default** ni se
sondea el entorno para decidirlo: preguntar una vez por la clave ausente no es descubrir familias.
Desde la respuesta rige la lectura declarada y no se vuelve a preguntar.

## Contexto de dominio

`domain_context` es una lista de entradas **read-only** que el flujo usa para aterrizar términos,
decisiones y restricciones existentes:

- `context_paths`: documentos de dominio, glosarios, arquitectura o guías funcionales.
- `adr_paths`: ADRs o decisiones técnicas ya aceptadas.

Resolución:
1. `mode: "off"` → no leer nada.
2. `mode: "on"` → leer los paths configurados; si faltan, avisar y continuar.
3. `mode: auto` → leer paths configurados y, si no hay, detectar candidatos obvios (`CONTEXT.md`,
   `docs/adr/`, `docs/architecture*`, `docs/domain*`) sin inventar rutas.

Uso:
- `analyze`/`plan`: usar nombres canónicos y decisiones vigentes; si contradicen el ticket, llevar
  la duda a `clarify`.
- `co-explore`/`cross-review`: pasar los paths resueltos como `context_paths` adicionales.
- Nunca crear, actualizar ni normalizar esos documentos desde `domain_context`; si hace falta un
  ADR nuevo, es otro flujo o requiere confirmación explícita.

## Doctor read-only

`/sdd-flow doctor <id>` valida coherencia sin escribir. Salida sugerida:

```markdown
## Doctor — <id>
| Check | Resultado | Evidencia |
|---|---|---|
| AC coverage | OK/WARN/FAIL | AC-1 → T1; AC-2 huérfano |
| Placeholders | OK/WARN/FAIL | sin TBD/TODO/etc. |
| Interfaces | OK/WARN/FAIL | Produce `foo()` no coincide con Consume |
| Git coherence | OK/WARN/FAIL | branch/base_commit/HEAD |
| Verify freshness | OK/WARN/FAIL | Verify anterior a <sha> |
| Working tree | OK/WARN/FAIL | código ajeno / generado / SDD local |
```

Checks:
- Reusar el self-review de `tasks`: cobertura AC↔task, anti-placeholder y Produce/Consume.
- Leer ACs desde `spec.md` o desde `## Spec` embebido en `plan.md`.
- Marcar **verify stale** si `## Verify` existe pero hay commits/cambios posteriores a su fecha o
  evidencia.
- Tratar `.plans/`, `.specify/` y `.plans/<id>/work/` como locales; `work/` es scratch/auditoría,
  nunca fuente de progreso.
- Reportar evidencia concreta; no arreglar ni tocar archivos.

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
   branch_prefix: ""            # vacío → prefijo semántico
   tracker: jira
   test_scope_hint: "ng test --include={name}"   # {name} = ruta exacta del .spec.ts (no glob **/…: rompe el loader)
   jira_approval:
     mode: "off"                # elegido en el wizard junto con tracker/branch_prefix (default off)
   domain_context:
     context_paths: []
     adr_paths: []
   ```

   Los campos de decisión (`tracker`, `branch_prefix` y, solo si se acaba de elegir `tracker: jira`, `jira_approval.mode`) se eligen en el **wizard** (una sola pantalla, con el valor actual/detectado pre-seleccionado). El resto de las claves con default (`commit_style`, `implement_mode`, `cross_review`, `domain_context.mode`, `final_diff_review`, `co_explore.debate.mode`, entre otras) no se pregunta: la skill las resuelve, y quien quiera fijarlas las copia de `config-ejemplo.md`. Los comandos (`test_cmd`/`build_cmd`/`lint_cmd`/`test_scope_hint`) y los paths de `domain_context` se autodetectan y quedan editables en la confirmación final. Nada se inventa. Al escribir el `config.yml`, `cross_review.mode`, `co_explore.mode`, `domain_context.mode`, `final_diff_review.mode`, `jira_approval.mode` y `co_explore.debate.mode` se emiten con `on`/`off` **entre comillas** (`"on"`/`"off"`; `auto` sin comillas es válido): sin ellas YAML los parsea como booleanos.

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

### Transición entre bloques

Esta tabla es la autoridad canónica de la secuencia. Cada paso opera sobre el bloque aprobado y
solo avanza cuando su precondición es observable; las skills consumidoras la referencian en vez de
inventar otro orden.

| # | Paso | Precondición | Postcondición |
|---|---|---|---|
| 1 | revisión del delta | `cese_confirmado` + `cosecha_terminada` + `delta_completo` | `delta_revisado` + `drift_resuelto` |
| 2 | comprobación del bloque | `delta_revisado` + `drift_resuelto` + `sin_hallazgos_abiertos` + `fila_elegible_presente` | `bloque_aceptado` |
| 3 | commit de trabajo | `bloque_aceptado` + `writer_unico` | `commit_de_trabajo_local` |
| 4 | vínculo en el recibo | `commit_de_trabajo_local` + `intencion_registrada` | `vinculo_persistido` + `ledger_publicado` |
| 5 | marcas `[x]` | `vinculo_persistido` + `ledger_publicado` | `marcas_actualizadas` |
| 6 | revalidación del recibo | `marcas_actualizadas` | `recibo_revalidado` |
| 7 | siguiente dispatch | `recibo_revalidado` + `cese_confirmado` | `bloque_restante` + `writer_unico` |

### Formato del recibo de partición

El recibo vive en la ruta persistente `.plans/<id>/partition-receipt.yml`. No es un ledger de
avance: conserva exactamente qué partición aprobó el humano y permite comprobar que cada dispatch
transporta ese mismo alcance. Su esquema mínimo contiene `tasks_fingerprint`, la lista `blocks` en
su orden aprobado y, para cada bloque, `block_id`, `task_ids` y `work_commit`.

El `tasks_fingerprint` se calcula sobre el contenido canónico de cada task, **normalizando únicamente
el estado del checkbox**. El título, los pasos, los archivos y las dependencias (`Produce` y
`Consume`) son contenido semántico: modificarlos invalida la aprobación. Hashear los bytes completos
de `tasks.md` sería incorrecto porque la transición esperada `[ ]` → `[x]` cambiaría el fingerprint;
hashear solamente los IDs también sería incorrecto porque no detectaría cambios en pasos, archivos o
dependencias.

Cada `block_id` es una identidad por bloque estable y única dentro del recibo. Tras aceptar el
bloque, esa identidad se vincula al SHA de su commit de trabajo en `work_commit`; una identidad sin
ese vínculo no autoriza marcar tasks ni avanzar. Antes de cada dispatch, el conductor revalida el
fingerprint y el orden de los bloques restantes. El conjunto de tasks pendientes se valida por
separado contra la unión de esos bloques: cualquier diferencia invalida el dispatch y detiene la
secuencia.

### Vocabulario de condiciones

Este vocabulario es un conjunto cerrado. Las claves se combinan con `+`; cualquier clave ausente
invalida el artefacto.

| Clave | Significado |
|---|---|
| `cese_confirmado` | Todo writer del bloque anterior dejó de escribir y el cese es observable. |
| `cosecha_terminada` | La salida del worker fue cosechada por completo. |
| `delta_completo` | El delta del bloque está completo contra su commit base. |
| `delta_revisado` | El conductor revisó todo el delta, incluidos los archivos nuevos. |
| `drift_resuelto` | Todo cambio fuera del work order fue revertido o declarado. |
| `sin_hallazgos_abiertos` | La revisión del delta terminó sin hallazgos pendientes. |
| `fila_elegible_presente` | Existe al menos una fila del contrato elegible en el bloque. |
| `bloque_aceptado` | El bloque satisface el predicado de aceptación. |
| `writer_unico` | Hay exactamente un escritor activo sobre el árbol. |
| `commit_de_trabajo_local` | Existe el commit de trabajo del bloque y no alcanzó el upstream. |
| `intencion_registrada` | La intención durable de la transición quedó escrita antes del efecto. |
| `vinculo_persistido` | La identidad del bloque quedó vinculada al SHA de su commit de trabajo. |
| `ledger_publicado` | La entrada del ledger de este paso quedó publicada por rename. |
| `marcas_actualizadas` | Las tasks cubiertas por el bloque quedaron marcadas. |
| `recibo_revalidado` | El fingerprint y el orden de los bloques restantes se revalidaron. |
| `bloque_restante` | El recibo revalidado identifica un bloque pendiente. |
| `sin_bloque_restante` | No queda ningún bloque aprobado sin ejecutar. |
| `reset_aplicado` | El `git reset --soft` sobre el ancla ya se ejecutó. |
| `verificacion_final_en_verde` | La verificación final sobre el delta acumulado dio verde. |
| `gate_aprobado` | El gate humano aprobó el delta acumulado y su evidencia. |
| `commit_final_creado` | El commit final de contenido existe. |
| `cierre_persistido` | El resultado quedó registrado en el ledger y `plan.status` refleja el commit final. |

### Aristas de la transición

El grafo se declara en esta tabla y no se infiere de filas contiguas. Cada arista exige avance no
vacío: cambian la identidad y el ordinal del bloque, o progresa el cursor.

| From | To | Condición |
|---|---|---|
| 1 | 2 | `delta_revisado` + `drift_resuelto` |
| 2 | 3 | `bloque_aceptado` |
| 3 | 4 | `commit_de_trabajo_local` |
| 4 | 5 | `vinculo_persistido` + `ledger_publicado` |
| 5 | 6 | `marcas_actualizadas` |
| 6 | 7 | `recibo_revalidado` |
| 7 | 1 | `bloque_restante` + `writer_unico` |
| 7 | cierre | `sin_bloque_restante` + `cese_confirmado` |

### El ledger de secuencia

La autoridad cambia por fase en el handoff. Mientras los commits de trabajo viven, Git es la
autoridad. Antes de destruirlos durante el aplastado, el conductor persiste una proyección validada;
cuando esa validación termina ocurre el handoff y después el ledger pasa a ser la autoridad
archivística. Prohibir toda copia sería incumplible, porque la proyección exige una superposición
temporal antes de destruir los objetos de Git.

El ledger referencia el recibo y no lo duplica. El recibo sigue siendo la autoridad del SHA; el
ledger es la autoridad del contenido del delta y del avance de la secuencia.

| Campo | Autoridad | Fase | Obligatorio |
|---|---|---|---|
| `identidad_del_bloque` | ledger | siempre | por-bloques |
| `ordinal_del_bloque` | ledger | siempre | por-bloques |
| `referencia_al_recibo` | recibo | siempre | por-bloques |
| `cursor_de_transición` | ledger | siempre | por-bloques |
| `ancla_base` | git | pre-handoff | sí |
| `delta_material` | ledger | handoff | sí |
| `resultado` | ledger | post-handoff | sí |
| `estado_del_join` | ledger | siempre | no |
| `schema_version` | ledger | siempre | sí |

Los campos `por-bloques` están ausentes en `inline`, porque no hay partición ni recibo; esa ausencia
es válida y permite que ambos caminos produzcan un ledger completo. `delta_material` persiste el
delta independientemente de la recolección de Git: un SHA que deje de ser alcanzable no constituye
durabilidad. `estado_del_join` es un dato opaco que se persiste sin interpretarlo.

El ledger vive en la ruta `.plans/<id>/sequence-ledger.yml`, hermana del recibo. Al entrar a
`implement`, el flujo persiste `sequence_contract_version`, crea el ledger y después establece
`status: implementing`. Su retención es indefinida después
del cierre y también tras un rollback. Al archivarse `.plans/`, viaja con la carpeta sin
transformarse. El límite de su durabilidad es la misma copia del repositorio, no entre máquinas.

Ambos caminos producen ledger. Su proyección canónica debe coincidir exactamente en cinco piezas:
misma base, digest agregado del delta, estado terminal, cobertura y resultado del cierre. La
cobertura es el fingerprint del alcance aprobado del work order, independiente de la partición;
solo pueden diferir la cantidad de bloques, sus identidades y los cursores intermedios.

Ningún campo del ledger duplica lo que registra el sobre. La separación es comprobable comparando
ambos conjuntos de campos: su intersección debe estar vacía.

### Escritura del ledger

La atomicidad es por artefacto: cada superficie se escribe en un temporal del mismo directorio y se
publica con `rename`. Un `rename` publica un archivo; no hace atómica una transición que también
modifica el ledger, una referencia de Git, `tasks.md` y el sobre. Entre esas superficies rige un
protocolo distinto: se registra una intención durable antes del efecto y luego se ejecuta una
reconciliación idempotente.

Un intento no equivale a una transición consumada. La reconciliación puede hacer replay del intento,
pero adjudica el efecto durable una sola vez. La exigencia de avance no vacío rige sobre el grafo
nominal; no convierte una repetición idempotente de la reconciliación en otra transición.

La creación y cada actualización del ledger pertenecen a un escritor único. Para una adopción, el
token de propietario vive en `.plans/<id>/sequence-ledger.owner/`, un directorio hermano del ledger,
y la identidad se guarda en `owner/token`. La operación que decide la propiedad es `mkdir`: es
atómica en los shells soportados y falla si ya existe. Quien crea el directorio adopta; quien pierde
la carrera no adopta y se detiene, sin esperar ni reintentar.

Antes de cada publicación, el escritor relee `owner/token` y comprueba que conserva su propia
identidad; verificarlo solo al adoptar dejaría una ventana hasta el último `rename`. Si dos sesiones
intentan adoptar el mismo ledger, solo una obtiene el directorio, y el propietario ganador queda
observable en el contenido del token.

El abandono elimina el directorio únicamente tras cese confirmado. Un owner obsoleto **no** se
reclama borrando y recreando el directorio: `mkdir` excluye adoptantes nuevos, pero no impide que el
owner anterior publique después de releer su token. Solo una primitiva atómica existente que invalide
al propietario anterior antes de instalar al sucesor habilita el reclamo. Sin esa garantía, el estado
es `blocked-manual-remediation`; se ignoran sus temporales huérfanos, pero no se adopta ni se muta el
ledger.

### La submáquina de cierre

La entrada al cierre termina la transición entre bloques, pero no la secuencia. El aplastado y sus
controles avanzan por estos estados propios; la precondición de cada estado posterior sale de la
postcondición del anterior.

| # | Estado | Precondición | Postcondición |
|---|---|---|---|
| 1 | intención de aplastado | `sin_bloque_restante` + `cese_confirmado` | `intencion_registrada` |
| 2 | reset aplicado | `intencion_registrada` | `reset_aplicado` |
| 3 | verificación final | `reset_aplicado` | `verificacion_final_en_verde` |
| 4 | decisión del gate | `verificacion_final_en_verde` | `gate_aprobado` |
| 5 | commit final | `gate_aprobado` | `commit_final_creado` |
| 6 | cierre persistido | `commit_final_creado` | `cierre_persistido` en ledger y fase del plan |

### Cutpoints de la secuencia

Cada cutpoint deriva de una escritura o un efecto concreto, no de contar pasos. Los IDs son estables
y nombran tanto estados entre pasos como estados internos de una transición y de la submáquina de
cierre. En una cadena contigua, después de un paso y antes del siguiente describen el mismo límite;
cuando no existe esa equivalencia, la tabla declara `ninguno`.

| ID | Ocurre en | Estado observable | Equivale a |
|---|---|---|---|
| `C1` | antes de la revisión del delta | bloque despachado, nada escrito | inicio de bloque |
| `C2` | dentro del commit de trabajo | commit creado, ledger pendiente de publicar | ninguno |
| `C3` | dentro del vínculo en el recibo | efecto aplicado con ledger pendiente | ninguno |
| `C4` | dentro de las marcas | ledger publicado con marcas parciales | ninguno |
| `C5` | tras las marcas | marcas completas sin revalidar | antes del paso 6 |
| `C6` | tras la revalidación | recibo revalidado | antes del paso 7 |
| `C7` | dentro del siguiente dispatch | sobre creado con la llamada no consumada | ninguno |
| `C8` | entrada al cierre | sin bloque restante | después del paso 7 |
| `C9` | tras el reset | reset aplicado sin verificación | ninguno |
| `C10` | tras la verificación final | verificación en verde sin gate | ninguno |
| `C11` | tras el gate | gate aprobado sin commit final | ninguno |
| `C12` | tras el commit final | commit final sin cierre persistido | ninguno |

### El contrato con la recuperación

La recuperación consume un contrato compuesto por seis piezas:

1. la lista de cutpoints legítimos con sus equivalencias;
2. el esquema versionado y su versión;
3. los terminales, incluidos `rolled_back` y `abandoned`;
4. la distinción entre intento y transición consumada;
5. el grafo declarado en la tabla de aristas; y
6. el protocolo de adopción con su ganador observable.

Las tablas anteriores siguen siendo las autoridades de esas piezas. La sección siguiente concreta
su serialización, lectura y reconciliación; no redefine el grafo, los cutpoints ni los terminales.

## Recuperación de la secuencia

### Schema v1 del ledger de secuencia

La tabla de campos de “El ledger de secuencia” describe semántica; esta es la serialización canónica.
La raíz y sus objetos son **cerrados**: cualquier clave no declarada, tipo distinto, cardinalidad
inválida o condición de presencia incumplida produce `corrupt-ledger`. La única excepción es el valor
de `join_state`, declarado opaco: el ledger valida que sea un nodo compatible con JSON, lo conserva y
no interpreta sus claves internas. Una versión distinta de `schema_version: 1` produce
`unsupported-version` y no se interpreta parcialmente.

```yaml
schema_version: 1
sequence:
  sequence_id: <string no vacío>
  mode: blocks                 # blocks | inline
  base_anchor: <sha completo>
  coverage_fingerprint: sha256:<64 hex>
  join_state: null             # opcional; nodo JSON opaco, preservado sin interpretación
  receipt_ref: partition-receipt.yml  # obligatorio en blocks; se omite en inline
  delta:
    algorithm: sha256
    digest: sha256:<64 hex>
    material: |-
      <patch durable desde base_anchor>
  cursor:
    machine: block-machine     # block-machine | closure-machine | inline-machine
    cutpoint: C1               # C1..C12 | inline-active | inline-ready-to-close | inline-terminal
  terminal: active             # active | suspended | completed | rolled_back | abandoned
transitions:
  - transition_id: <sequence_id>:<ordinal>:<from>:<to>
    from_cursor: {machine: block-machine, cutpoint: C1}
    to_cursor: {machine: block-machine, cutpoint: C2}
    block: {id: B1, ordinal: 1}       # se omite en inline y en pasos de cierre
    intent:
      intent_id: <transition_id>:intent
    effects:
      - effect_id: <intent_id>:git-commit
        kind: external-effect          # enum de primitivas, abajo
        expected_effect_digest: sha256:<64 hex>
effect_events:
  - event_id: <effect_id>:observed
    effect_id: <intent_id>:git-commit
    state: observed                     # observed | adjudicated
    observed_digest: sha256:<64 hex>
result:
  status: active                       # mismo enum que sequence.terminal
  closed_at: null                      # ISO-8601 solo en terminal no continuable
```

`transitions` y `effect_events` conservan orden de publicación y son append-only: una identidad
existente no se edita ni se reutiliza. El estado lógico de un efecto se deriva de sus eventos: sin
evento está `pending`; un evento `observed` lo deja observado; un evento posterior `adjudicated` lo
adjudica. El archivo completo se publica con temporal + `rename`; “append-only” describe la historia
lógica, no una escritura por append de bytes. `transition_id`, `intent_id`, `effect_id`, `event_id` y
`expected_effect_digest` de cada efecto correlacionan intención, efecto externo y consumo sin duplicar el SHA cuya
autoridad permanece en el recibo.

Cardinalidades:

| Nodo | Cardinalidad e identidad |
|---|---|
| raíz | exactamente un `schema_version`, un `sequence`, una lista `transitions`, una lista `effect_events` y un `result` |
| `sequence` / `result` | exactamente un objeto de cada uno; sus estados deben coincidir al cerrar |
| `join_state` | 0..1; ausente, `null` o cualquier nodo compatible con JSON; se preserva sin interpretarlo |
| `transitions` | 0..N, orden estricto de publicación y `transition_id` único dentro de la secuencia |
| `intent` | exactamente una por transición; `intent_id` único y derivado de `transition_id` |
| `effects` | 1..5 por transición, `effect_id` único; cada entrada usa un `kind` cerrado y su propio `expected_effect_digest` |
| `effect_events` | 0..2 por efecto; `event_id` único, referencia válida y orden `observed` → `adjudicated` |
| `block` | exactamente uno en transiciones C1-C7 de `blocks`; ausente en cierre e inline |

Los objetos internos también son cerrados. `sequence` exige siempre `sequence_id`, `mode`,
`base_anchor`, `coverage_fingerprint`, `delta`, `cursor` y `terminal`; admite `join_state` y
`receipt_ref` solo bajo las condiciones siguientes. `delta` contiene exactamente `algorithm`,
`digest` y `material`; pre-handoff `material` puede ser la cadena vacía con el digest correspondiente,
y desde el handoff contiene el patch durable. `cursor` contiene exactamente `machine` y `cutpoint`.
`result` existe siempre con exactamente `status` y `closed_at`: mientras está activo usa
`status: active`/`closed_at: null`; al cerrar adopta el terminal y la fecha exigida. Cada transición,
intención, efecto, evento y bloque contiene exclusivamente los campos mostrados en el ejemplo y
declarados por sus cardinalidades.

`from_cursor` y `to_cursor` contienen exactamente `machine` y `cutpoint`, son distintos y usan la
máquina compatible con el modo. En bloques, C1-C8 pertenecen a `block-machine`, C8-C12 a
`closure-machine` y solo C8 permite el handoff; inline admite únicamente sus tres cutpoints.
`sequence.cursor` coincide con el último `to_cursor` publicado o, mientras esa transición está
pendiente, con su `from_cursor`. Otra combinación es `corrupt-ledger`.

Condiciones de presencia:

| Condición | Obligatorio | Prohibido |
|---|---|---|
| `mode: blocks` | `receipt_ref`, `block.id`, `block.ordinal` en transiciones de bloque | bloque nulo durante C1-C7 |
| `mode: inline` | `inline-machine` con `inline-active`, `inline-ready-to-close` o `inline-terminal` | `receipt_ref`, `block`, identidad/ordinal de bloque y cutpoints C1-C12 |
| pre-handoff | `base_anchor` alcanzable y delta contrastable con Git | terminal post-handoff inventado |
| post-handoff | `delta.material`, digest y `result` coherentes | depender de que los commits sigan alcanzables |
| terminal no continuable | `result.status == sequence.terminal`, `closed_at` no nulo | nuevas transiciones |

Fixtures mínimos embebidos:

- **`valid-blocks-v1`:** versión 1, `mode: blocks`, recibo correlacionado, una transición C1→C2 con
  intención y efecto sin eventos —estado derivado `pending`—; valida y entra al clasificador.
- **`valid-inline-v1`:** versión 1, `mode: inline`, `receipt_ref` y `block` ausentes, sin efecto
  externo parcial; valida y se clasifica `inline-pass-through`, no corrupto.
- **`partial-inline-v1`:** misma forma inline, con una intención externa pendiente o un efecto
  parcialmente observado; se clasifica `inline-unsupported` y no intenta reconstruir bloques.
- **`unsupported-version`:** `schema_version: 2`; se rechaza sin leer `transitions`.
- **`corrupt-ledger`:** versión 1 con dos `transition_id` iguales o digest mal formado; se rechaza por
  estructura/correlación.
- **`missing-required-ledger`:** el header del plan contiene `sequence_contract_version: 1` y no
  existe ledger; se distingue de una corrida legacy porque esta carece de ese marcador externo.

`sequence_contract_version: 1` se persiste en `plan.md` **antes** de crear el ledger y antes de cambiar
el flujo a `status: implementing`. Es el marcador externo de obligatoriedad: si existe y el ledger no,
la inicialización fue interrumpida y el diagnóstico es `missing-required-ledger`; si ambos faltan, la
corrida es legacy. `status` nunca sustituye este marcador porque también existe en planes anteriores.

### Snapshot y clasificación de recuperación

`capture_sequence_snapshot(ledger, receipt, git, tasks, process, owner) -> SequenceSnapshot` es
read-only. Conserva cada hecho con procedencia y frescura; nunca fusiona dos fuentes discrepantes en
un “estado verdadero”.

| Sección | Autoridad observada | No demuestra |
|---|---|---|
| plan/tasks | fase SDD, `wip_commit`, marcas y cobertura | que el efecto Git ocurrió |
| recibo | fingerprint, orden, bloque y `work_commit` | contenido durable del delta |
| Git | HEAD, ancla, cadena, trailers, localidad y dirty | intención o consumo |
| ledger | versión, cursor, intención, adjudicación, delta y terminal | actividad/cese del proceso |
| proceso/sobre | intento, transporte, `process_ref`, cosecha y terminalidad | ownership del ledger |
| owner | exclusión y token observable | progreso, cese o fencing del owner anterior |

`classify_sequence(snapshot: SequenceSnapshot) -> SequenceDiagnosis` evalúa predicados disjuntos.
Cada predicado declara hechos obligatorios, hechos prohibidos, evidencia de cese, cutpoint/terminal,
acción permitida y fuente de rechazo. Con **cero coincidencias** produce `conflict:<source>`; con
**más de una coincidencia** demuestra ambigüedad del contrato y produce `conflict:classifier`.
Ninguna de las dos salidas muta.

Resultados cerrados:

| Resultado | Significado | ¿Puede mutar? |
|---|---|---|
| `recoverable` | un único cutpoint y una composición idempotente demostrados | solo tras propuesta, gate y revalidación |
| `terminal` | `completed`, `rolled_back`, `abandoned` o `suspended` coherente | no; solo `completed` habilita routing normal; rollback/abandono detienen y `suspended` vuelve a diseño |
| `blocked` | cutpoint reconocido sin capacidad/evidencia suficiente | no |
| `inline-pass-through` | ledger v1 inline válido sin efecto externo parcial | sí; solo permite el `resume` normal de WIP/fase, nunca reconstruye bloques |
| `inline-unsupported` | inline válido con intención/efecto parcial cuya reconciliación no está soportada | no |
| `legacy-unsupported` | ejecución anterior al contrato sin ledger obligatorio | no |
| `unsupported-version` | versión no soportada | no |
| `corrupt-ledger` | documento v1 inválido | no |
| `missing-required-ledger` | la corrida debía producir ledger y no existe | no |
| `conflict:<source>` | autoridades incompatibles o clasificador ambiguo | no |

`terminal:completed` exige además que `plan.status` sea coherente con el commit final (`committed` o
una fase posterior). Si el commit final existe pero el ledger o la fase del plan quedaron a medio
publicar, el estado continúa siendo C12 y `closure-step` completa ambas superficies de forma
idempotente. Cualquier otra combinación entre terminal y fase produce `conflict:plan`; nunca se
reenvía un `plan.status: implementing` por debajo de un ledger ya cerrado.

La máquina `block-machine` clasifica C1-C8; `closure-machine` clasifica C8-C12. **C8 es la frontera compartida**,
no otro bloque. Los nombres y observables se toman de “Cutpoints de la secuencia”:

| Cutpoint | Máquina | Evidencia pendiente que puede reconciliarse | Bloqueo obligatorio |
|---|---|---|---|
| C1 | block-machine | intención/dispatch todavía sin efecto material | proceso potencialmente vivo o cese no demostrable |
| C2 | block-machine | adjudicar commit compatible y publicar cursor | commit sin identidad, trailer, ancla o árbol esperado |
| C3 | block-machine | adjudicar vínculo compatible del recibo | recibo/fingerprint/bloque contradictorio |
| C4 | block-machine | completar solo marcas del bloque vinculado | marcas ajenas o cobertura no correlacionada |
| C5 | block-machine | revalidar partición | orden/fingerprint cambió |
| C6 | block-machine | adjudicar revalidación y preparar siguiente paso | evidencia de recibo no fresca |
| C7 | block-machine | resolver intento anterior antes de redispatch | llamada no consumada o writer posible |
| C8 | ambas | entrar al cierre con `sin_bloque_restante` | bloque restante o cese no confirmado |
| C9 | closure-machine | verificar delta después del reset | reset no ligado a intención/ancla |
| C10 | closure-machine | adjudicar verificación fresca | evidencia no correlacionada o vencida |
| C11 | closure-machine | crear commit final ligado al gate | gate ausente o digest distinto |
| C12 | closure-machine | adjudicar commit, persistir cierre y sincronizar fase | commit final sin identidad/ancla/árbol esperado |

`suspended` es terminal continuable solo por una ruta explícita de vuelta a diseño; nunca salta al
siguiente bloque. `plan.status` permanece `implementing` durante una secuencia activa: decide la fase
SDD únicamente cuando la clasificación es `terminal` o no aplica.

### Propuesta y reconciliación autorizada

`build_recovery_proposal(diagnosis: SequenceDiagnosis) -> RecoveryProposal` produce una lista cerrada
y ordenada con clasificación, evidencias relevantes, **digest de evidencia**, efectos pendientes,
precondiciones y terminal esperado. El único gate humano aprueba ese conjunto completo, no un permiso
abierto para “seguir recuperando”.

Después del gate y antes de mutar:

1. obtener **evidencia positiva de cese** según el transporte: identidad coincidente de corrida o
   proceso más estado terminal verificable, o ausencia comprobada por la primitiva oficial;
2. adquirir ownership exclusivo sin borrar un token ajeno;
3. capturar otra vez las seis autoridades, reclasificar y recalcular el digest;
4. continuar solo si diagnóstico, propuesta y digest coinciden exactamente con lo autorizado.

Timeout, silencio, salida completa, PID no correlacionado o confirmación humana por sí solos no
prueban cese. Un owner obsoleto sin fencing/CAS atómico existente produce
`blocked-manual-remediation`. Cualquier drift invalida el gate y exige **nueva confirmación**.

`reconcile_authorized_proposal(proposal: RecoveryProposal) -> RecoveryOutcome` compone únicamente
estas primitivas:

| `kind` | Precondición | Efecto idempotente | Adjudicación |
|---|---|---|---|
| `external-effect` | intención durable e identidad correlacionada | observar el efecto; crearlo solo si falta | digest observado compatible |
| `ledger-cursor` | transición válida y efecto anterior adjudicado | publicar transición/cursor con temporal + rename | cursor objetivo visible una vez |
| `task-marks` | bloque y cobertura correlacionados | completar solo marcas pendientes del bloque | fingerprint de marcas esperado |
| `partition-revalidation` | recibo y orden vigentes | volver a validar sin reinterpretar tasks | evidencia fresca ligada al intento |
| `closure-step` | precondición de la submáquina satisfecha | ejecutar un estado de cierre con la mecánica Git canónica | postcondición observada y ligada; en C12 incluye `plan.status: committed` |

Cada efecto avanza lógicamente `pending` → `observed` → `adjudicated` publicando eventos nuevos, sin
editar la transición ni eventos anteriores:

- `pending` y efecto ausente: aplicar una vez, publicar `observed` y luego `adjudicated`;
- `pending` y efecto presente con el digest esperado: no repetir, publicar `observed` y luego `adjudicated`;
- efecto presente con digest distinto: `conflict:<source>` sin adjudicar;
- `adjudicated`: no-op aunque se repita la reconciliación.

El caso **`idempotent-retry`** ejecuta la misma retoma después del terminal y exige el mismo resultado,
**sin commits, marcas ni cursores nuevos**. La propuesta declara también la clase sucesora esperada
después de cada primitiva. Se reclasifica en cada frontera y solo se continúa cuando coincide con esa
cadena autorizada —incluido el terminal—; una clase o plan no previsto detiene y exige otra propuesta.

### Matriz normativa de recuperación

La matriz declara su universo antes de afirmar cobertura: cutpoint/terminal, modo, transporte,
estado de proceso/cese, owner, frescura de sesión, fase pre/post-handoff, evidencia
completa/ausente/conflictiva y primera/segunda retoma. No materializa un producto cartesiano con
combinaciones imposibles; cubre cada C1-C12, cada terminal y al menos un representante mínimo de cada
clase de bloqueo/conflicto.

| Partición | Casos mínimos | Resultado exigido |
|---|---|---|
| bloques recuperables | C2-C6, C9-C12 con intención/efecto en cada frontera válida | terminal esperado; `idempotent-retry` sin efecto nuevo |
| bloques condicionados | C1, C7 y C8 con cese positivo y con writer posible | `recoverable` solo con cese; de otro modo `blocked` |
| terminales | `completed`, `rolled_back`, `abandoned`, `suspended` | tres no continuables; `suspended` vuelve a diseño |
| compatibilidad | `valid-inline-v1`, legacy sin ledger, versión desconocida | clases explícitas, ninguna mutación |
| integridad | ledger truncado, digest/identidad duplicada, recibo/Git/tasks contradictorios | `corrupt-ledger` o `conflict:<source>` |
| ownership | libre, adoptante ganador, owner obsoleto sin fencing | solo los dos primeros avanzan; el tercero queda `blocked-manual-remediation` |
| transporte | terminal consultable, ausencia comprobada, timeout/silencio | los dos primeros prueban cese; el último bloquea |

En la tabla, `P/L/R/G/X/O` resume las seis autoridades: plan+tasks, ledger, recibo, Git,
proceso/sobre y owner. “Seis coherentes” significa que cada una aporta los hechos obligatorios y ninguna
aporta un hecho prohibido; la columna predicado nombra el observable que distingue el caso.

| Caso | P/L/R/G/X/O | Predicado distintivo | Propuesta o bloqueo | Salida | Segunda retoma |
|---|---|---|---|---|---|
| C1 | seis coherentes; X cesado; O libre | dispatch identificado, sin efecto | observar/aplicar efecto → cursor | sucesor autorizado | no repite efecto/cursor |
| C2 | seis coherentes; G con commit local | commit identificado, ledger pendiente | adjudicar commit → cursor | C3 | no crea commit |
| C3 | seis coherentes; R aún sin vínculo | commit compatible, vínculo pendiente | persistir vínculo → cursor | C4 | no duplica vínculo |
| C4 | seis coherentes; T parcial | ledger publicado, marcas incompletas | completar solo marcas correlacionadas | C5 | no agrega marcas |
| C5 | seis coherentes; T completo | recibo todavía no revalidado | revalidar partición | C6 | no revalida dos veces |
| C6 | seis coherentes; R fresco | revalidación adjudicable | publicar adjudicación/cursor | C7 o C8 | cursor único |
| C7 | seis coherentes; X cesado; O libre | llamada previa no consumada | resolver intento; redispatch solo si corresponde | C1 o C8 | no duplica dispatch |
| C8 | seis coherentes; sin bloque; X cesado | frontera compartida de cierre | iniciar cierre | C9 | no reinicia cierre |
| C9 | seis coherentes; G con reset ligado | reset aplicado, verificación ausente | verificar delta | C10 | no repite reset |
| C10 | seis coherentes; evidencia fresca | verificación verde, gate ausente | adjudicar verificación | C11 | no inventa gate |
| C11 | seis coherentes; gate/digest iguales | aprobación persistida, commit ausente | crear commit final | C12 | no duplica commit |
| C12 | seis coherentes; G con commit final | cierre/fase parcialmente persistidos | adjudicar commit, cerrar y sincronizar fase | completed | terminal estable |
| terminal | seis autoridades coherentes | completed/rolled_back/abandoned/suspended | routing, STOP o diseño según subtipo | mismo terminal | cero mutaciones |
| inline limpio | P/L/G/X/O coherentes; R ausente | sin efecto externo parcial | pass-through de WIP/fase | routing normal | no inventa bloques |
| inline parcial | P/L/G/X/O coherentes; R ausente | intención/efecto parcial | `inline-unsupported` | bloqueo | cero mutaciones |
| legacy | P sin marcador; L/R ausentes; G/X/O coherentes | contrato v1 no obligatorio | `legacy-unsupported` | bloqueo | cero mutaciones |
| ledger ausente | P con marcador; L ausente; R/G/X/O observados | inicialización v1 interrumpida | `missing-required-ledger` | bloqueo | cero mutaciones |
| versión/corrupción | documento presente inválido | versión desconocida o forma/digest inválido | rechazo tipado | bloqueo | cero mutaciones |
| conflicto | dos autoridades discrepan | fuente concreta incompatible | `conflict:<source>` | bloqueo | cero mutaciones |
| owner obsoleto | O stale sin fencing | exclusión no reclamable | `blocked-manual-remediation` | bloqueo | cero mutaciones |
| cese incierto | X live/timeout/silencio | cese no demostrable | `blocked` | bloqueo | cero mutaciones |

Para C1-C12, “Salida” es el sucesor inmediato y el terminal final es `completed`. La propuesta
materializa la cadena completa desde la fila actual, enumerando cada primitiva y su sucesor esperado
hasta ese terminal; en C6/C7 fija además cuál rama autorizó. No basta con aprobar “seguir”. Las filas
de bloqueo y los otros terminales terminan donde indica su salida y no tienen primitivas posteriores.

La matriz es un **contrato normativo**, no evidencia de que exista un runtime ejecutable. Cada caso
debe declarar las seis autoridades, el predicado esperado, la propuesta permitida, la salida terminal
y la condición de no mutación o idempotencia. Un arnés futuro solo podrá marcar una fila como
ejecutada si materializa esas autoridades y usa el clasificador/reconciliador de producción; un modelo
embebido en Markdown no cuenta como prueba end-to-end.

Procedimiento por caso, siempre en un repositorio desechable:

1. crear el repo temporal, commit base, artefactos y estado Git exacto del fixture;
2. ejecutar el diagnóstico read-only y contrastar clase, fuente y digest;
3. para `recoverable`, presentar/registrar la confirmación, adquirir ownership, revalidar y ejecutar
   hasta el terminal declarado;
4. registrar HEAD, diff, marcas, cursor, adjudicaciones y terminal;
5. ejecutar una segunda retoma y exigir identidad de resultado y conteo cero de efectos nuevos;
6. destruir el repo temporal y comprobar que el working tree real nunca cambió.

Los negativos terminan después del diagnóstico y verifican cero mutaciones. Un transporte sin
primitiva de cese comprobable se registra como `blocked`, nunca como caso verde inferido.

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
status: planned        # planned → (plan-approved, solo complejo) → tasks-ready → implementing → verified → committed → pushed → (pr-open) → done
created_at: 2026-01-01T12:00:00-03:00
# wip_commit: <sha>            # solo si el flujo quedó pausado (ver sub-paso `pause`); se borra al retomar
# jira_subtask: ABC-145       # subtarea SPEC en Jira, si se publicó (gate `publish-spec`)
# jira_subtask_url: https://<tu-site>.atlassian.net/browse/ABC-145   # la usa `open-pr` para linkear la spec
# pr_url: <url>               # PR creado por el sub-paso `open-pr`, si se abrió
---

# Plan — <título corto>

## Enfoque
<estrategia técnica elegida; no listar alternativas descartadas>

## Decisiones y trade-offs
<las elecciones contestables del plan, nombradas explícitamente: qué se eligió y qué costo/riesgo
se acepta a cambio. Son los blancos concretos de la revisión (cross-model o humana) — una decisión
que no está acá no puede ser desafiada en el gate. No repite el Enfoque: lo descompone en sus
apuestas.>
- <decisión> — trade-off aceptado: <…>

## Contexto de dominio
<paths de `domain_context` leídos + términos/ADRs aplicados. Omitir si no aplica.>

## Archivos a tocar
- `ruta/al/archivo` — <qué cambia; reúso de `path:line` si aplica>

## Tests / build
- test: `<comando detectado/acotado>`
- build: `<comando detectado>`

## Verification
<el contrato de verificación. Mismo esquema normativo que
`cross-implement/contrato-verificacion.md` → "La tabla" y "El bloque de baseline": no se reescribe
acá con otra forma, se llena. Todas las filas arrancan en `RED` porque todavía no se implementó
nada; un baseline que no arranca en `RED` se adjudica o se justifica antes de congelar.>

### v1

| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |
|---|---|---|---|---|---|
| V1 | AC-1 — <requisito, en una línea> | test | `<comando literal, copiable>` | <lo que cuenta como cumplido> | RED |

#### Baseline de v1
`hash_previo:` · `hash: <sha256 de los bytes canónicos de esta versión>`

- `id: V1` · `commit: <SHA evaluado>` · `timestamp: <ISO-8601>`

## Verify
<lo completa el paso `verify` EJECUTANDO las filas de arriba; vacío hasta entonces. No elige
evidencia: la evidencia ya está declarada y congelada.>
| AC | Fila | Resultado | Evidencia | Fecha |
|---|---|---|---|---|
| AC-1 | V1 | ✅ / ❌ | <salida observada al correr el comando de la fila> | <ISO-8601> |

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
<el MISMO esquema normativo que el plan completo, sin excepción por complejidad: un contrato con
una fila es igual de contrato. Lo que escala con la complejidad es la cantidad de filas, no el
formato — un dialecto propio para *trivial* obligaría a `verify` y al gate de `cross-implement` a
entender dos.>

### v1

| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |
|---|---|---|---|---|---|
| V1 | AC-1 — <requisito> | test | `<comando literal>` | <lo que cuenta como cumplido> | RED |

#### Baseline de v1
`hash_previo:` · `hash: <sha256 de los bytes canónicos>`

- `id: V1` · `commit: <SHA evaluado>` · `timestamp: <ISO-8601>`

## Verify
<lo completa el paso `verify` ejecutando las filas de arriba>
| AC | Fila | Resultado | Evidencia | Fecha |
|---|---|---|---|---|
| AC-1 | V1 | ✅ / ❌ | <salida observada> | <ISO-8601> |

## Extras (fuera de AC)
<cambios sin AC que entran al commit; vacío por default. Ver "Extras" en SKILL.md>
- E1 — <descripción corta> · `ruta/archivo.ts:200-210`
```

## Plantilla de `## Verify`

El paso `verify` (ver `SKILL.md` → "Paso `verify`") completa la sección `## Verify` del `plan.md`
**ejecutando las filas del contrato de `## Verification`**. Una fila por AC, con la fila del contrato
que lo prueba:

```markdown
## Verify
| AC | Fila | Resultado | Evidencia | Fecha |
|---|---|---|---|---|
| AC-1 | V1 | ✅ | `vitest run cart.spec` → 12 passed, exit 0 | 2026-01-01T12:00:00-03:00 |
| AC-2 | V2 | ❌ | el botón no se deshabilita con lista vacía | 2026-01-01T12:00:00-03:00 |
```

La **evidencia** es la salida fresca del comando **que la fila ya declaraba**, no uno elegido en este
momento. La columna `Fila` es lo que hace comprobable esa diferencia: sin ella, "corrí lo que
correspondía" no se puede contrastar contra nada.

Un AC sin fila, o una fila sin AC, es un contrato que no cerró y no debería haber llegado hasta acá
(lo comprueba el self-review del paso `tasks`).

### Revert-to-confirm (AC de comportamiento con test)

Confirma que el test realmente discrimina el comportamiento del AC: debe **fallar sin el hunk de
implementación que habilita el AC**. En `change_type: fix`, aplica siempre al test de regresión.
En features/refactors, aplica a cada AC de comportamiento cubierto por test. Con el test en verde
y el hunk de implementación aislado:

**POSIX** (macOS/Linux/Git Bash):
```bash
git stash push -- <archivo-del-cambio> # quita solo el hunk/archivo de implementación (deja el test)
<test_cmd acotado>                     # DEBE fallar — si pasa, el test no cubre el AC
git stash pop                          # restaura la implementación
<test_cmd acotado>                     # vuelve a verde
```

**PowerShell** (Windows): mismos comandos git (`git stash push -- <archivo-del-cambio>` / `git stash pop`); el runner de tests según el stack.

Si el test y la implementación viven en el mismo archivo, revertir por hunk (`git stash -p` en
POSIX) o aislar el cambio de implementación antes del revert. Si el AC es mecánico, copy/config o
wiring sin seam razonable, documentar la excepción en la evidencia y usar el comando/observación
del `verify`. Anotar el resultado (`revert → FAIL, restore → PASS`) como evidencia del AC en la
tabla.

## Plantilla de tasks

`.plans/<id>/tasks.md` — descomposición atómica. Una task = un cambio coherente y, en lo posible, testeable. El objetivo es que cada task sea **autosuficiente**: ejecutable en una sesión fresca que solo ve **esa task y los artefactos del flujo**, sin re-deducir el diseño ni tener que elegir otro enfoque.

Cada task es un **bloque** con estos campos:

```markdown
# Tasks — <título corto>

- [ ] **T1 — <acción concreta>**  · cubre: AC-1
  - **Por qué:** <qué AC habilita / la intención — 1 línea>
  - **Archivos:** `ruta/archivo.ts` (reúso de `fn()` en `path:line`); `ruta/archivo.spec.ts`
  - **Seam:** <punto testeable del comportamiento; omitir en tareas mecánicas/sin seam razonable>
  - **Produce:** `nuevaFn(arg: Tipo): Resultado` — firma exacta que consume T2. *(solo si otra task la necesita)*
  - **Pasos:**
    1. (si hay seam) <caso de test que debería fallar y por qué>
    2. (si hay seam) `<comando de test acotado>` → FAIL esperado
    3. <enfoque + snippet ILUSTRATIVO de la firma/estructura clave>
    4. `<comando de test acotado>` o verificación acotada → PASS/OK
  - **Verificar:** `Vn` — la fila del contrato de `## Verification` que prueba este AC. Solo el
    ID: repetir acá el comando o el esperado crea una segunda fuente que se desincroniza.

- [ ] **T2 — <acción concreta>**  · cubre: AC-1, AC-2
  - **Por qué:** <…>
  - **Archivos:** <…>
  - **Consume:** `nuevaFn` de T1 (no repetir la firma — referenciarla); bloque global `interfaz-compartida`.
    *(solo si usa algo de otra task o un bloque global; un solo campo, las referencias se acumulan en él)*
  - **Pasos:** <…>
  - **Verificar:** <…>

## Self-review (antes del gate)
- **Cobertura AC ↔ task:** AC-1 → T1, T2 ✓ · AC-2 → T2 ✓ (sin AC huérfanos / sin tasks sin AC).
- **Cobertura AC ↔ fila del contrato:** AC-1 → V1 ✓ · AC-2 → V2 ✓ (bidireccional: ni AC sin fila ni fila sin AC — es lo que el gate de `cross-implement` exige para congelar).
- **Anti-placeholder:** sin `TBD`/`TODO`/"agregar X apropiado"/"similar a T-N"/"etc." en plan ni tasks.
- **Interfaces:** cada `Produce` coincide exacto (nombre + firma) con el `Consume` que lo referencia.
```

> **Las dos formas de `Consume`, y cómo se declara un bloque global.** `Consume` apunta a **una
> task** —basta el id (`T2`, `T16b`, `T15A`), con o **sin** backticks— o a un **bloque global**: una
> sección de este mismo `tasks.md` que **ninguna task produce** y que varias consumen (una interfaz
> compartida, un contrato transversal). Se declara escribiéndola con un heading `##` que **no** sea
> encabezado de task; su **id es el slug de ese heading** —`## Interfaz compartida — el contrato de
> los tres adaptadores` da `interfaz-compartida-el-contrato-de-los-tres-adaptadores`— y se cita con
> las palabras literales `bloque global` seguidas del slug **entre backticks**. Los backticks son
> obligatorios **solo** ahí: un id de task tiene forma propia y se reconoce solo; un título en prosa
> no.
>
> No es cosmética: `Produce`, `Consume` y el bloque global son lo que vuelve **legible sin
> arqueología** de dónde sale cada interfaz, y lo que `cross-implement` lee para congelar un work
> order. Lo que la task no declara, nadie lo reconstruye por adivinanza.

> **Regla anti-sobre-especificación.** Los snippets de los Pasos son **ilustrativos**: muestran la *firma*, la *estructura* y los *casos a cubrir*, no la implementación final completa de cada archivo. El plan orienta la ejecución; el código exhaustivo se escribe en `implement`, no acá. En tasks puramente mecánicas (config, copy, bump, wiring sin seam razonable) los Pasos pueden colapsarse a 1‑2 líneas y la evidencia se cierra en `verify` — no inflar artificialmente.

Ejemplo concreto de una task:

```markdown
- [ ] **T1 — Persistir el borrador del formulario al recargar**  · cubre: AC-1
  - **Por qué:** AC-1 pide conservar lo que el usuario cargó cuando recarga la página.
  - **Archivos:** `src/app/shared/services/draft/draft-form.service.ts` (reúso de `this.form`); `draft-form.service.spec.ts`
  - **Seam:** `persistDraftOnReload()` observable mediante `globalThis.sessionStorage`.
  - **Pasos:**
    1. (test rojo) spec que mockea `globalThis.sessionStorage` y espera que al restaurar se lea la clave y se limpie.
    2. `ng test --include=src/app/shared/services/draft/draft-form.service.spec.ts` → FAIL (método no existe)
    3. (impl) `persistDraftOnReload()` serializa `this.form` a `sessionStorage` con guard `try/catch`.
    4. `ng test --include=src/app/shared/services/draft/draft-form.service.spec.ts` → PASS
  - **Verificar:** `V1`
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

## Revisión final de diff

En `final_diff_review.mode: auto`, solo se ofrece para flujos `complex` o high-risk ejecutados en
modo `inline`, dentro del gate de revisión manual previo al commit. No es cross-model por defecto
y no reemplaza `verify`: revisa el **diff completo** ya verificado contra dos ejes.

**Quién lo hace.** Un agente fresco despachado **por capacidad** (descubrirla, no asumir el nombre
de la tool — ver "Matriz de detección por capacidad"). Es un revisor **del mismo modelo**, no
cross-model: lo que compra es contexto limpio sobre el diff, no diversidad de familia (eso es
`cross-review`, y revisa artefactos de diseño, no diffs).

**Qué recibe.** El **diff completo del flujo** —no el de una task— y las rutas de los artefactos,
que **está autorizado a abrir**: a diferencia de un despacho por task, acá no hay contexto extraído
de antemano, así que el revisor lee `.plans/<id>/` él mismo.

```markdown
Trabaja en modo SOLO LECTURA sobre el repo <working_dir>. No edites nada.
Revisa el diff completo del flujo contra:
- `.plans/<id>/spec.md` o `## Spec` embebido en `plan.md`
- `.plans/<id>/plan.md`
- `.plans/<id>/tasks.md` si existe
- principios del repo (`AGENTS.md`/`CLAUDE.md`/`CONTRIBUTING.md`) si existen

Evalúa:
- SPEC: ¿el diff cumple los AC y no agrega cambios fuera de AC sin estar declarados como Extras?
- QUALITY: ¿sigue patrones del repo, sin dead code, placeholders ni deuda obvia?

Tu mensaje final debe ser EXACTAMENTE este reporte (sin prosa extra):
SPEC: ok | fail | warn
QUALITY: ok | fail
FINDINGS: <una línea por problema; vacío si todo ok>
NOTES: <no verificable desde el diff / recomendaciones no bloqueantes>
```

**Cómo lee el conductor el reporte.** `SPEC: ok` + `QUALITY: ok` → el gate sigue su curso normal.
`warn` no bloquea el gate, pero **tampoco lo cierra en silencio**: el conductor resuelve lo señalado
—o lo declara— antes de commitear. Los dos `fail` **no pesan igual**, y la diferencia no es de
severidad sino de qué hay detrás de cada eje:

| | Qué obliga | Por qué |
|---|---|---|
| `SPEC: fail` | **bloquea el commit.** Se resuelve antes de seguir | contradice un `verify` en verde: dos lecturas del mismo hecho no pueden convivir. Una de las dos está mal y hay que averiguar cuál |
| `QUALITY: fail` | **no bloquea, pero no se cierra en silencio:** se arregla, o se declara como `E-n` en `## Extras` del plan con qué se dejó pasar y por qué | no toca ningún AC, así que la ley fundamental —ningún commit con un AC en rojo— no lo alcanza. Pero un finding que se descarta sin rastro convierte al revisor en decorativo, y este es el eje **sin segunda red** |

El asimétrico es deliberado: a un revisor cuyo `ok` no acredita nada tampoco se le da poder de veto
sobre el commit. Lo que sí se le exige es que su hallazgo deje rastro.

> **Cuánto vale ese `ok`, y por qué no es simétrico.** El revisor es del **mismo modelo**, así que
> su acuerdo no acredita nada: dos agentes de la misma familia coinciden en los mismos puntos
> ciegos, y esa coincidencia produce una señal falsamente tranquilizadora. Un **hallazgo**, en
> cambio, sigue siendo un hallazgo — si encuentra un bug real, el bug es real sin importar de qué
> familia venga. La regla es asimétrica a propósito, y por eso es verificable: distingue dos cosas
> observables, *findings emitidos* contra *veredicto de aprobación*.
>
> Lo que sí compra —y conviene nombrarlo sin exagerarlo— es **contexto fresco**: el revisor no vio
> escribirse el código, así que no arrastra las justificaciones de quien lo escribió. Eso es real y
> **no** es diversidad de familia; llamarlo diversidad sería el error.
>
> **Los dos ejes no tienen la misma red de contención.** `SPEC` tiene una segunda: `verify` recorre
> los AC al final con evidencia fresca, así que un `SPEC: ok` equivocado se caza después. `QUALITY`
> **no tiene ninguna**. Un `QUALITY: ok` de un revisor same-model es la señal más débil de todo el
> flujo, y la única que no tiene nada detrás: tratarla como garantía es exactamente el error que
> este bloque existe para impedir.

Si no hay capacidad para despachar un reviewer fresco, el conductor hace la revisión liviana y lo
avisa. Si hay findings, volver a `implement` o a `plan`/`specify` según el tipo de gap; no abrir
otro gate nuevo.

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

## Bloques de validación del contrato en el plan

Predicados sobre los artefactos que este flujo produce. Cada bloque declara su **predicado**, y esa
línea es idéntica en las dos variantes de shell.

```bash
# @bloque:materializacion-contrato
# Predicado: toda materialización del contrato usa la MISMA cabecera normativa de seis columnas;
# no existe una segunda forma de tabla haciéndose pasar por contrato.
# Entradas: $plan
CAB='| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |'
rc=0
grep -qxF "$CAB" "$plan" || {
  echo "GUARD:materializacion-unica el plan no materializa la cabecera normativa" >&2; rc=1; }
# Una tabla que arranca en `| ID |` y NO es la cabecera normativa es un dialecto propio: es la forma
# en que "no dupliquen la norma" deja de cumplirse sin que nada se rompa a la vista.
grep -E '^\|[[:space:]]*ID[[:space:]]*\|' "$plan" | grep -vxF "$CAB" > /tmp/mu.$$ 2>/dev/null
[ -s /tmp/mu.$$ ] && { echo "GUARD:materializacion-unica hay una tabla de contrato con otro esquema:" >&2
  cat /tmp/mu.$$ >&2; rc=1; }
rm -f /tmp/mu.$$
exit $rc
# @fin:materializacion-contrato
```

```powershell
# @bloque:materializacion-contrato-ps
# Predicado: toda materialización del contrato usa la MISMA cabecera normativa de seis columnas;
# no existe una segunda forma de tabla haciéndose pasar por contrato.
# Entradas: $plan
$cab = '| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |'
$rc = 0
$doc = Get-Content -LiteralPath $plan
if ($doc -cnotcontains $cab) { Write-Error 'GUARD:materializacion-unica el plan no materializa la cabecera normativa'; $rc = 1 }
$otras = @($doc | Where-Object { $_ -cmatch '^\|\s*ID\s*\|' -and $_ -cne $cab })
if ($otras.Count -gt 0) { Write-Error "GUARD:materializacion-unica hay una tabla de contrato con otro esquema: $($otras -join ' | ')"; $rc = 1 }
exit $rc
# @fin:materializacion-contrato-ps
```

```bash
# @bloque:cobertura-ac-fila
# Predicado: todo AC declarado en el plan tiene al menos una fila del contrato que lo cita, y toda
# fila cita un AC declarado. Las dos direcciones se reportan por separado.
# Entradas: $plan
t=$(mktemp -d); rc=0
grep -oE '^- \*\*AC-[0-9a-z]+' "$plan" | sed 's/^- \*\*//' | sort -u > "$t/ac"
grep -E '^\|' "$plan" | grep -vE '^\|[[:space:]]*(ID[[:space:]]*\||[-: |]+\|)' \
  | awk -F'|' '{gsub(/^ +| +$/,"",$3); split($3,p," "); if (p[1]!="") print p[1]}' | sort -u > "$t/citados"
comm -23 "$t/ac" "$t/citados" > "$t/e"
[ -s "$t/e" ] && { printf 'GUARD:cobertura-ac-fila AC sin fila: %s\n' "$(tr '\n' ' ' < "$t/e")" >&2; rc=1; }
comm -13 "$t/ac" "$t/citados" > "$t/e"
[ -s "$t/e" ] && { printf 'GUARD:cobertura-ac-fila fila sin AC declarado: %s\n' "$(tr '\n' ' ' < "$t/e")" >&2; rc=1; }
rm -rf "$t"; exit $rc
# @fin:cobertura-ac-fila
```

```powershell
# @bloque:cobertura-ac-fila-ps
# Predicado: todo AC declarado en el plan tiene al menos una fila del contrato que lo cita, y toda
# fila cita un AC declarado. Las dos direcciones se reportan por separado.
# Entradas: $plan
$rc = 0
$doc = Get-Content -LiteralPath $plan
$ac = @($doc | Where-Object { $_ -cmatch '^- \*\*(AC-[0-9a-z]+)' } | ForEach-Object { [regex]::Match($_, '^- \*\*(AC-[0-9a-z]+)').Groups[1].Value } | Sort-Object -Unique -CaseSensitive)
$citados = @($doc | Where-Object { $_ -cmatch '^\|' -and $_ -cnotmatch '^\|\s*(ID\s*\||[-: |]+\|)' } |
  ForEach-Object { ($_ -split '\|')[2].Trim() -split '\s+' | Select-Object -First 1 } |
  Where-Object { $_ } | Sort-Object -Unique -CaseSensitive)
$sinFila = $ac | Where-Object { $_ -cnotin $citados }
if ($sinFila) { Write-Error "GUARD:cobertura-ac-fila AC sin fila: $($sinFila -join ' ')"; $rc = 1 }
$sinAc = $citados | Where-Object { $_ -cnotin $ac }
if ($sinAc) { Write-Error "GUARD:cobertura-ac-fila fila sin AC declarado: $($sinAc -join ' ')"; $rc = 1 }
exit $rc
# @fin:cobertura-ac-fila-ps
```

```bash
# @bloque:verify-ejecuta
# Predicado: el paso verify CARGA la fila declarada en vez de identificar evidencia en ese momento,
# y revert-to-confirm sigue alcanzable.
# Entradas: $skill (el SKILL.md de sdd-flow)
rc=0
grep -q '\*\*CARGAR\*\*' "$skill" || {
  echo "GUARD:verify-solo-ejecuta el paso verify no carga la fila del contrato" >&2; rc=1; }
# `IDENTIFICAR` era el paso que ELEGÍA la evidencia después de implementar, que es elegir la que ya
# pasa. Se comprueba su ausencia como paso de la gate function, no la de la palabra en el documento.
grep -q '\*\*IDENTIFICAR\*\*' "$skill" && {
  echo "GUARD:verify-solo-ejecuta el paso verify sigue eligiendo evidencia (IDENTIFICAR)" >&2; rc=1; }
# Control POSITIVO: el cambio es sustitutivo, no una poda. revert-to-confirm tiene que seguir ahí.
grep -qi 'revert-to-confirm' "$skill" || {
  echo "GUARD:verify-solo-ejecuta se perdió revert-to-confirm" >&2; rc=1; }
exit $rc
# @fin:verify-ejecuta
```

```powershell
# @bloque:verify-ejecuta-ps
# Predicado: el paso verify CARGA la fila declarada en vez de identificar evidencia en ese momento,
# y revert-to-confirm sigue alcanzable.
# Entradas: $skill (el SKILL.md de sdd-flow)
$rc = 0
$doc = (Get-Content -LiteralPath $skill) -join "`n"
if ($doc -cnotmatch '\*\*CARGAR\*\*') { Write-Error 'GUARD:verify-solo-ejecuta el paso verify no carga la fila del contrato'; $rc = 1 }
if ($doc -cmatch '\*\*IDENTIFICAR\*\*') { Write-Error 'GUARD:verify-solo-ejecuta el paso verify sigue eligiendo evidencia (IDENTIFICAR)'; $rc = 1 }
if ($doc -notmatch '(?i)revert-to-confirm') { Write-Error 'GUARD:verify-solo-ejecuta se perdió revert-to-confirm'; $rc = 1 }
exit $rc
# @fin:verify-ejecuta-ps
```
