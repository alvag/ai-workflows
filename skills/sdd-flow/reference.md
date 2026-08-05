# sdd-flow — Referencia

Detalle operativo de la skill `sdd-flow`. El `SKILL.md` apunta acá cuando necesita la matriz de detección, el esquema de configuración o las plantillas de artefactos.

## Tabla de contenidos

- [Matriz de detección por capacidad](#matriz-de-detección-por-capacidad)
- [Flujo por tracker](#flujo-por-tracker)
- [Aprobación externa de la spec (Jira)](#aprobación-externa-de-la-spec-jira)
- [Detección de stack y comandos](#detección-de-stack-y-comandos)
- [Esquema de `.specify/config.yml`](#esquema-de-specifyconfigyml)
- [Transporte de las corridas delegadas](#transporte-de-las-corridas-delegadas)
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
- [Prompt del subagente por task](#prompt-del-subagente-por-task)
- [Prompt del subagente reviewer](#prompt-del-subagente-reviewer)
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
  transport: cli                 # cli (default) | herdr — dónde se aloja cada corrida delegada: el transporte CLI vigente o un pane del multiplexor de terminales. Es la INTENCIÓN del proyecto: hace falta junto con la capacidad, nunca en su lugar. Ver "Transporte de las corridas delegadas"
  manifest:                      # registro por corrida de las skills cross-model, para decidir con datos si la capacidad rinde
    mode: "on"                   # "on" (default) | "off"  (entre comillas: sin ellas YAML los parsea como booleanos). Política del ECOSISTEMA: las tres skills escriben el mismo registro; apagarlo para una sola dejaría huecos sistemáticos. Ver `cross-review/reference.md` → "Manifest de corrida"
jira_approval:                   # aprobación externa de la spec en Jira (opcional; solo si tracker: jira)
  mode: "off"                    # "off" | "on"  (default off; entre comillas: sin ellas YAML los parsea como booleanos)
  subtask_issuetype: auto        # auto (descubrir por createmeta) | "Subtarea" | "Sub-task"
  approval_signal: ask           # ask | status:"<estado Jira que cuenta como aprobado>"
implement_mode: ask              # cómo ejecutar las tasks: ask (preguntar en el último gate) | inline | subagent | cross (delegar a la otra familia vía `cross-implement`; requiere esa skill + el CLI de la otra familia)
domain_context:
  mode: auto                     # auto | "on" | "off"; solo lectura, nunca escribe ADRs/docs
  context_paths: []              # docs de dominio/glosarios/arquitectura a leer si existen
  adr_paths: []                  # ADRs o decisiones vigentes a leer si existen
final_diff_review:
  mode: auto                     # auto (complex/high-risk inline) | "on" | "off"
```

**Este bloque es dueño de las 21 claves que `sdd-flow` gobierna.** Las 12 restantes las poseen sus
hermanas y su enum se define allá: `cross_review.*` en `cross-review/SKILL.md` → "Configuración";
`co_explore.*` en `co-explore/SKILL.md` → "Configuración"; `cross_implement.*` en
`cross-implement/SKILL.md` → "Configuración". El archivo **completo**, con las 33 juntas y listo
para copiar, está en `config-ejemplo.md`, que es una vista de todos estos dueños.

Placeholders de `branch_format`: `{type}` (prefijo efectivo), `{ticket}` (clave del tracker, se omite si no hay), `{slug}` (2-5 palabras del título en kebab, sin acentos, `[a-z0-9-]`).

**`test_scope_hint`** es una **plantilla de comando completa**, no un glob suelto: se reemplaza `{name}` por el archivo/patrón a acotar y se ejecuta tal cual (ej.: `vitest run {name}`, `ng test --include={name}`, `pytest {name}`). En Angular, `{name}` debe ser la **ruta exacta** del `.spec.ts`, **no** un glob `**/…`: el glob arrastra `.html`/`.scss` y rompe el loader.

**Prefijo efectivo (`{type}`)** = primer valor presente: (1) override conversacional de la corrida → (2) `branch_prefix` del `config.yml` → (3) prefijo semántico (tabla de abajo). Se normaliza quitando la barra final si la trae. El `branch_prefix`/override **reemplazan** el `{type}`; el mapeo semántico de abajo aplica **solo cuando no hay ninguno de los dos**.

## Transporte de las corridas delegadas

`cross_model.transport` responde **"¿debe este flujo usar panes?"**, que es una pregunta distinta de
**"¿se puede acá?"**. La primera es **intención** y la segunda **capacidad**: hacen falta las dos, la
intención no crea la capacidad —querer panes no los crea— y la capacidad no autoriza sola.

**Capacidad — tres cláusulas, cada una con lo que pasa si resuelve a falso.** Su sede es el adaptador
de cada skill delegada (`co-explore`, `cross-review`, `cross-implement` → `transporte-herdr.md` →
"Activación"); acá se resume porque el flujo es quien decide si la vía se intenta. La mecánica y la
sintaxis del multiplexor no se copian: la autoridad es su skill externa.

| Cláusula de capacidad | Falsa ⇒ qué hace el flujo |
|---|---|
| la variable de entorno del multiplexor vale `1` | el conductor no corre dentro de un pane host: delega por el transporte CLI vigente |
| el binario utilizable, comprobado en la sesión | no se infiere de la variable —que dice dónde corre el conductor, no que el binario responda—: transporte CLI vigente, sin improvisar comandos |
| la skill externa de transporte instalada | es la autoridad de la mecánica: sin ella no se improvisa de memoria, se delega por el transporte CLI vigente |

Sin **cualquiera** de las tres la vía de panes **no se intenta**: la corrida sigue por el transporte
CLI vigente con un aviso de una línea, la misma degradación que el resto del ecosistema (regla #6).

**Intención — cuatro cláusulas.**

1. **Sede:** `cross_model.transport` de `.specify/config.yml`, hermano de `manifest`, como default
   durable del proyecto. Es lo único que sobrevive a una sesión nueva.
2. **Conjunción:** hace falta **junto con** la capacidad, no en su lugar. Con `transport: herdr` y
   capacidad falsa se delega por CLI; con capacidad verdadera y `transport: cli` no se abre ningún
   pane. Ninguna de las dos alcanza sola.
3. **Precedencia** (la estándar del ecosistema, igual que `cross_review` o `implement_mode`):
   **override conversacional de la corrida > `cross_model.transport` del config > default `cli`**.
4. **Eco:** el valor resuelto se ecoa en el **checkpoint de inicio** junto al resto de los valores
   (`SKILL.md` → "Adaptación al proyecto"), de modo que el transporte nunca se aplique en silencio.

**Durabilidad del override conversacional.** Tiene exactamente la misma que `cross_review` o
`implement_mode`. Queda escrita para que el config no actúe como sustituto silencioso de un estado por
flujo que no existe:

- **Se anuncia antes de abrir el primer pane** —una línea, con la vía resuelta— y recién después se
  despacha la primera corrida.
- Rige para **todas las fases delegadas** del flujo (co-exploración, contra-enfoque, revisiones de
  gate, implementación cruzada) y **no se vuelve a pedir permiso** por fase: se resolvió una vez.
- El usuario conserva el **opt-out** en cualquier momento ("sigue por CLI"): vale desde la corrida
  siguiente, sin tocar las que ya están en vuelo.
- **Alcance: la sesión del flujo.** No es global ni por repo — muere con la sesión, como el resto de
  los overrides de la corrida.
- **Sede del override:** la clave `transport` del mapa `overrides` del `handoff.md` (`SKILL.md` →
  "`handoff.md` (retomado del flujo)"), que es lo que lo persiste cuando el flujo se pausa.
- **Cada corrida delegada lo replica** en su descriptor para que el callback lo lea: el descriptor es
  **copia, no sede**, y no se consulta para resolver la intención de la corrida siguiente.
- Un override **no persistido no sobrevive a una sesión nueva**: al retomar sin ese valor en el
  `handoff.md` manda el config. Es la conducta vigente del ecosistema, declarada en vez de asumida.

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

`.plans/<id>/tasks.md` — descomposición atómica. Una task = un cambio coherente y, en lo posible, testeable. El objetivo es que cada task sea **autosuficiente**: ejecutable en una sesión fresca sin re-deducir el diseño ni tener que elegir otro enfoque.

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
  - **Consume:** `nuevaFn` de T1 (no repetir la firma — referenciarla). *(solo si usa algo de otra task)*
  - **Pasos:** <…>
  - **Verificar:** <…>

## Self-review (antes del gate)
- **Cobertura AC ↔ task:** AC-1 → T1, T2 ✓ · AC-2 → T2 ✓ (sin AC huérfanos / sin tasks sin AC).
- **Cobertura AC ↔ fila del contrato:** AC-1 → V1 ✓ · AC-2 → V2 ✓ (bidireccional: ni AC sin fila ni fila sin AC — es lo que el gate de `cross-implement` exige para congelar).
- **Anti-placeholder:** sin `TBD`/`TODO`/"agregar X apropiado"/"similar a T-N"/"etc." en plan ni tasks.
- **Interfaces:** cada `Produce` coincide exacto (nombre + firma) con el `Consume` que lo referencia.
```

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
overrides: { branch_prefix: null, base_branch: null, cross_review: null, implement_mode: null, jira_approval: null, transport: null }
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
6. Opcional: guardar el reporte crudo del implementer/reviewer en `.plans/<id>/work/Tn-*.md` para
   auditoría o retomado tras compactación. Ese directorio es scratch local: no se commitea, no
   reemplaza `tasks.md`, no contiene `progress.md`, y nunca decide qué task está completa.

Tests+build completos, `verify` de los AC, revisión manual, staging selectivo, commit, push y PR opcional:
**siempre el conductor** (pasos 3-10 del Paso común). Los STOPs no existen dentro de un subagente.

## Prompt del subagente reviewer

Para el **reviewer por-task** del modo `subagent` (ver `SKILL.md` → "Modo de ejecución", paso 2). Un agente fresco que **solo revisa** el diff de una task contra sus artefactos — no edita ni implementa. Distinto de `cross-review`: aquel es **cross-model** y revisa *artefactos de diseño* (spec/plan/tasks); este es un agente **del mismo modelo** que revisa el *diff* de una task ya implementada. Despacharlo por capacidad, igual que el implementer (sin capacidad → degradar a la revisión liviana del conductor). El conductor **interpola la lista `FILES`** del reporte del implementer en el prompt (el reviewer es un agente fresco: sin ella no sabe qué archivos revisar). Plantilla:

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

## Revisión final de diff

En `final_diff_review.mode: auto`, solo se ofrece para flujos `complex` o high-risk ejecutados en
modo `inline`, dentro del gate de revisión manual previo al commit. No es cross-model por defecto
y no reemplaza `verify`: revisa el **diff completo** ya verificado contra dos ejes.

Usar el mismo contrato del "Prompt del subagente reviewer", ajustando el alcance:

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

Salida exacta:
SPEC: ok | fail | warn
QUALITY: ok | fail
FINDINGS: <una línea por problema; vacío si todo ok>
NOTES: <no verificable desde el diff / recomendaciones no bloqueantes>
```

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
