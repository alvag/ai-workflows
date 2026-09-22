# sdd-flow — Referencia

Detalle operativo de la skill `sdd-flow`. El `SKILL.md` apunta acá cuando necesita la matriz de detección, el esquema de configuración o las plantillas de artefactos.

## Cómo se decide el `risk`

`risk` admite `low | high | unknown`, y el header del plan lo materializa con el valor
post-análisis. Tres reglas lo gobiernan:

- Un cambio es **sensible** si altera lógica, contratos o efectos en datos o schemas, autenticación,
  autorización, pagos, seguridad o concurrencia. **Ningún cambio sensible puede ser `low`.** Uno
  puramente cosmético o documental no se vuelve sensible por el nombre de su archivo ni por su
  dominio.
- Falta de evidencia, una dependencia incierta o un rollback no verificable producen `unknown`.
- Ni un indicio del tracker ni la frase «trátalo como hotfix» deciden el riesgo: lo decide el
  análisis vigente, con su evidencia citada.

## Tabla de contenidos

- [Matriz de detección por capacidad](#matriz-de-detección-por-capacidad)
- [Cómo se decide el `risk`](#cómo-se-decide-el-risk)
- [Flujo por tracker](#flujo-por-tracker)
- [Aprobación externa de la spec (Jira)](#aprobación-externa-de-la-spec-jira)
- [Detección de stack y comandos](#detección-de-stack-y-comandos)
- [Siembra del entorno local](#siembra-del-entorno-local)
- [Paso `resume` (retomar un flujo / cambiar de contexto)](#paso-resume-retomar-un-flujo--cambiar-de-contexto)
- [Esquema de `.specify/config.yml`](#esquema-de-specifyconfigyml)
- [Contexto de dominio](#contexto-de-dominio)
- [Qué escribe `init`](#qué-escribe-init)
- [Mapeo tipo de cambio → prefijo](#mapeo-tipo-de-cambio--prefijo)
- [Construcción del mensaje de commit](#construcción-del-mensaje-de-commit)
- [Apertura de PR (opcional, tras push)](#apertura-de-pr-opcional-tras-push)
- [Búsqueda de antecedentes](#búsqueda-de-antecedentes)
- [Plantilla de constitution](#plantilla-de-constitution)
- [Plantilla de spec](#plantilla-de-spec)
- [El contrato de verificación, en dos formas](#el-contrato-de-verificación-en-dos-formas)
- [Casos de routing al cambiar un `description`](#casos-de-routing-al-cambiar-un-description)
- [Plantilla de plan](#plantilla-de-plan)
- [Plantilla de plan combinado (profundidad corta)](#plantilla-de-plan-combinado-profundidad-corta)
- [Plantilla de `## Verify`](#plantilla-de--verify)
- [Plantilla de tasks](#plantilla-de-tasks)
- [Plantilla de `handoff.md`](#plantilla-de-handoffmd)
- [Revisión final de diff](#revisión-final-de-diff)
- [Ejemplo de criterios de aceptación](#ejemplo-de-criterios-de-aceptación)

---

## Contrato de salida del helper de frontmatter

`scripts/plan_frontmatter.py` lee el header YAML de un `plan.md`. Su único consumidor mecánico es
`sdd-orchestrator`, que lo carga por ruta y exige `PLAN_FRONTMATTER_CONTRACT_VERSION == 1` y los
símbolos públicos `parse_plan_frontmatter`, `read_plan_frontmatter` y `PlanFrontmatterError`. La
ausencia y la incompatibilidad del módulo son fallos de arnés distintos de un dato inválido, y
ninguno escapa como traceback.

El helper levanta `PlanFrontmatterError` con los códigos `header-ausente`, `header-mal-cerrado` y
`archivo-ilegible`; `clave-duplicada` lo levanta cada consumidor sobre la clave que le importa,
porque el helper **no** adjudica la semántica de los valores. Los delimitadores aceptan espacio
exterior (`--- `), como el lector histórico; el contenido sigue exigiendo `---` después de retirar
ese espacio.

---

## Persistencia y retomado del estado del plan

El plan nuevo materializa `profundidad` y `risk` en su header, y los dos se validan antes de leer el
resto de su estado. Antes de que exista el plan, el handoff conserva el snapshot y
`spec_approved_at`; después, el header del plan manda.

<!-- retomado-pre-plan:start -->
En pre-plan, una rama existente no acredita que la spec haya sido aprobada. Con
`spec_approved_at: <timestamp>`, continuar después del gate local; con `spec_approved_at: null`
explícito, volver al gate y no volver a preguntar. Para un flujo heredado con spec y rama pero sin la
clave, preguntar una vez: el sí persiste el timestamp de esa confirmación y el no persiste `null`.
Sin handoff ni plan, volver al gate aplicable. Con plan existente, `status`, `profundidad` y `risk`
del header son autoridad aunque falte el handoff.

Cambiar la profundidad o el ajuste de Jira conserva rama y base, marca `create-branch` como
consumido y restaura el gate pendiente que la profundidad nueva exija — que es el que nombra
«Profundidad del flujo» en `SKILL.md`, y no uno fijo.
<!-- retomado-pre-plan:end -->

<!-- regeneracion-upstream:start -->
Si una aclaración, revisión o decisión cambia un AC o master-spec: registrar arbitraje, cerrar la
corrida actual, invalidar los artefactos y contratos dependientes, regenerarlos, repetir la evidencia
y checks afectados y abrir una nueva revisión solo para la versión nueva. No se abre una corrida
duplicada ni se congela un dependiente cuya autoridad upstream cambió.
<!-- regeneracion-upstream:end -->

<!-- checkpoint-cross-review:start -->
Un checkpoint de cross-review conserva el mismo `run_id`. El usuario puede conceder una tanda finita
adicional, rechazar aplicaciones, seguir con un tope finito o cambiar un criterio de aceptación. Las
decisiones se registran antes de cerrar la corrida; si cambian el artefacto upstream, se aplica el
orden de regeneración anterior antes de abrir otro `run_id`.
<!-- checkpoint-cross-review:end -->

---

## Resolución del intérprete de Python

Antes de ejecutar un script Python de la skill, resolver Python 3.9 o superior mediante una prueba
ejecutable. La presencia del nombre en `PATH` no alcanza: cada candidato debe correr código con
`-c`. El wrapper resultante conserva `py -3` como dos argumentos.

<!-- resolvedor-python:inicio -->
```sh
resolve_skill_python() {
  if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' \
      >/dev/null 2>&1; then
    python_skill() { python3 "$@"; }
    PYTHON_SKILL='python3'
    return 0
  fi
  if py -3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' \
      >/dev/null 2>&1; then
    python_skill() { py -3 "$@"; }
    PYTHON_SKILL='py -3'
    return 0
  fi
  printf '%s\n' \
    'ERROR: no executable Python 3.9+; python3 -c and py -3 -c failed or reported an older version' \
    >&2
  return 1
}
resolve_skill_python || exit 1
# Run scripts as: python_skill <script> [arguments...]
```

```powershell
$script:PythonSkill = $null
$PythonCandidates = @(
  @{ Display = 'python3'; File = 'python3'; Prefix = @() },
  @{ Display = 'py -3'; File = 'py'; Prefix = @('-3') }
)
foreach ($Candidate in $PythonCandidates) {
  try {
    $Prefix = @($Candidate.Prefix)
    & $Candidate.File @Prefix -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' *> $null
    if ($LASTEXITCODE -eq 0) {
      $script:PythonSkill = $Candidate
      break
    }
  } catch {
    continue
  }
}
if ($null -eq $script:PythonSkill) {
  throw 'ERROR: no executable Python 3.9+; python3 -c and py -3 -c failed or reported an older version'
}
function Invoke-SkillPython {
  $Prefix = @($script:PythonSkill.Prefix)
  & $script:PythonSkill.File @Prefix @args
}
# Run scripts as: Invoke-SkillPython <script> [arguments...]
```
<!-- resolvedor-python:fin -->


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

Detalle del gate `publish-spec` (ver `SKILL.md` → "Paso `publish-spec`" y, al retomar, `resume` → "Gate de Jira" en este mismo documento). Solo aplica con `tracker: jira`, `jira_approval.mode: on` (u override de la corrida) y un MCP de Atlassian con escritura.

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
Contrato completo en `resume` → "Gate de Jira", en este mismo documento. En síntesis: "ya aprobaron" → confiar; "revisa el ticket"/silencio → leer estado + comentarios nuevos; **observaciones** → corregir + re-publicar (descripción) + comentar + volver a `awaiting`; **aprobado** (señal de `approval_signal`, o confirmación del usuario si es `ask`) → seguir a `create-branch`. El estado vive en el frontmatter de `handoff.md` (`gate_status: awaiting | changes-requested | approved`).

## Detección de stack y comandos

Resolver en este orden: `config.yml` → manifiesto del repo → preguntar. Comandos sugeridos por stack (ajustar al gestor real presente):

| Stack | Manifiesto | test_cmd típico | build_cmd típico | bootstrap del worktree | Acotar test a un archivo |
|---|---|---|---|---|---|
| Node | `package.json` | `npm test` / `pnpm test` / `yarn test` (leer `scripts`) | `npm run build` (si existe el script) | según el gestor de la tabla siguiente | según runner: `jest <patrón>`, `vitest run <patrón>`, `ng test --include=<ruta-exacta.spec.ts>` |
| Go | `go.mod` | `go test ./...` | `go build ./...` | `none` | `go test ./ruta/... -run <Test>` |
| Rust | `Cargo.toml` | `cargo test` | `cargo build` | `none` | `cargo test <nombre>` |
| Python | `pyproject.toml` / `pytest.ini` / `setup.cfg` | `pytest` | (suele no compilar) | sin regla; pedir comando o confirmación de `none` | `pytest path/to/test_x.py::test_y` |
| Java | `pom.xml` / `build.gradle` | `mvn test` / `gradle test` | `mvn package` / `gradle build` | `none` | `mvn -Dtest=ClassName test` |
| .NET | `*.csproj` / `*.sln` | `dotnet test` | `dotnet build` | `none` | `dotnet test --filter <expr>` |

Para Node, `packageManager` manda cuando identifica un gestor y debe ser coherente con el lockfile.
Sin ese campo, resolver en este orden; señales contradictorias exigen una decisión, nunca el primer
lockfile encontrado:

| Gestor | Señales sin `packageManager` | bootstrap |
|---|---|---|
| npm | `package-lock.json` | `npm ci` |
| pnpm | `pnpm-lock.yaml` | `pnpm install --frozen-lockfile` |
| Yarn Berry | `.yarnrc.yml`, o `yarn.lock` con `__metadata:` | `yarn install --immutable` |
| Yarn 1 | `yarn.lock` con cabecera `# yarn lockfile v1` y sin señal Berry | `yarn install --frozen-lockfile` |
| Bun | `bun.lockb` | `bun install --frozen-lockfile` |

Angular no es otro stack para esta decisión: con `package-lock.json` usa la fila npm y deriva
`npm ci`. `packageManager` fija gestor y, para Yarn, la versión mayor; una contradicción con el
lockfile detiene la derivación. Si la tabla acredita `none`, el default es `[]`; Python y `other` no
tienen regla automática, por lo que el checkpoint exige un comando o la confirmación explícita de
ninguno.

**Rama base:** precedencia = (a) **override de base de la corrida** (el usuario pidió cortar desde una rama X; ver `SKILL.md` → router y `create-branch` paso 2) → (b) `default_branch` del `config.yml` → (c) **detección**: `git symbolic-ref --short refs/remotes/origin/HEAD` devuelve `origin/<rama>`; fallback `git remote show origin | sed -n 's/.*HEAD branch: //p'`. **Normalizar a la rama local** quitando el prefijo `origin/` antes de operar (`origin/main` → `main`). En un tramo read-only, comprobar la existencia contra las refs disponibles y declarar el remoto no comprobado; en la vía heredada con efectos, ejecutar primero `git fetch origin` y recién entonces exigir `refs/heads/<rama>` o `refs/remotes/origin/<rama>`, sin inventarla. Sin una decisión congelada por la preflight, posicionarse con `git checkout <rama-local>` + `git pull --ff-only origin <rama-local>`, **nunca** `git checkout origin/<rama>` (deja *detached HEAD*). Con `origin_sha` congelado, ningún consumidor repite ese checkout/pull: usa el SHA y la rama persistidos. Nunca asumir `main`/`master`. Con override de base, X puede ser **local o estar adelantada del remoto**: hacer el `pull --ff-only` **solo si X tiene upstream** (`git rev-parse --abbrev-ref --symbolic-full-name @{u}` no falla); si no, cortar desde el HEAD local de X. El override no toca `config.yml`.

**Host de Git:** parsear `git remote get-url origin` y buscar `github.com`, `gitlab`, `bitbucket` u otro dominio; define qué CLI/MCP usar para PRs y detección de rama remota.

### Elección de rama

Si el handoff ya trae `origin_sha` y una decisión de ubicación de la preflight, `create-branch`
consume esa identidad. Consume `worktree_branch` como el nombre definitivo ya elegido —con worktree
materializado, y también con `worktree_location: current` cuando el handoff lo trae, que es lo que
se escribe antes de que exista `plan.md`—; no vuelve a
preguntar, hacer pull, checkout, stash ni rename. Si la ref avanzó, muestra ambos OID y solo cambia
el SHA congelado con autorización. El procedimiento siguiente queda para una invocación directa o un
flujo heredado sin esa identidad.

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

## Siembra del entorno local

**El flujo no crea worktrees.** Los crea el usuario —a mano con `git worktree add`, o desde la
plataforma de terminales que use— y arranca la corrida adentro. Esta skill asume que ya está donde va
a trabajar: no clasifica topología, no despacha un flujo previo y no materializa un paquete.

Lo único que hace al empezar es **comprobar si el entorno local existe**, porque un worktree hereda
las reglas de ignore del repositorio pero **no el contenido ignorado**. Sin `.specify/`, el flujo
arrancaría un `init` que nadie pidió.

**El origen se nombra, no se infiere.** Lo declara quien invoca —el usuario, o la skill que creó el
worktree—. `git rev-parse --git-common-dir` **no sirve** para deducirlo: Git no modela parentesco
entre linked worktrees, así que ese comando devuelve el `.git` compartido —el del checkout
principal— sin importar desde dónde se creó el worktree, y su `.claude/` puede estar en otra versión
que el que lo originó. **Sin origen declarado, el flujo pregunta; no copia en silencio.**

Con origen, se copia —nunca symlink, que rompería el aislamiento que el worktree compra— y se dice
en una línea: *"faltaban `.specify/` y `.claude/`, los sembré desde `<origen>`"*. Sin gate: es
reversible y obvio.

### Qué se siembra, y qué queda prohibido

El conjunto se limita a archivos existentes bajo `.specify/`, `.claude/`, `.agents/`, `.codex/` y
`.opencode/` que sean **untracked e ignorados** en el origen. `.specify/config.yml` es continuidad
obligatoria: si existe y Git no lo versiona, entra aunque `seed_paths` esté vacío; si está
versionado, el worktree ya lo tiene. Quedan prohibidos, aunque alguien los agregue:

- `.plans/`, `.cross-model/`, `.co-explore/`, `.cross-review/`, `.cross-implement/`, `.handoffs/` y
  `.superpowers/` — son artefactos de flujos, no entorno;
- `.git/`, que es metadata compartida del repositorio;
- repositorios anidados;
- `node_modules/`, `.venv/`, `venv/`, `dist/`, `build/`, `target/` y `__pycache__/`.

La prohibición es lo que impide que "copiar el entorno" arrastre un árbol de dependencias.

### Lo que el usuario sabe y la skill no

Un worktree creado por una plataforma de terminales puede nacer en `origin/<base>` en vez del
`<base>` local, y quedar un commit atrás sin que nada lo señale. La skill **no lo adivina**: quien
creó el worktree sabe desde dónde cortó. Si el flujo necesita esa base —para medir un diff contra
ella—, la pregunta va al usuario en el checkpoint de contexto, no a un clasificador.

## Paso `resume` (retomar un flujo / cambiar de contexto)

Punto de entrada para un flujo empezado. `.plans/` es visible entre ramas del mismo working tree, no entre linked worktrees: un snapshot de origen debe seguir el `worktree_path` y leer el paquete vivo antes de enrutar.

### Listar / elegir el flujo
1. Si el usuario nombró un flujo (`<id>` o ruta `.plans/<id>/`), usar ese. Si dijo algo genérico ("¿en qué quedé?", "qué flujos tengo"), **listar** los flujos activos (excluir `.plans/archived/`): para los que tienen `plan.md`, leer su header; para los **pre-`plan`** —con `spec.md` y/o `handoff.md`, en cualquier combinación— leer el `handoff.md` (`phase`, `gate_status` y la profundidad elegida). Un directorio sin ninguno de los tres es un flujo que no llegó a escribir nada: se lista como tal y se pregunta si se retoma o se descarta.
2. Si `.plans/<id>/` **no** tiene `plan.md`, el flujo quedó pre-`plan`. **Leer `handoff.md` si existe** (narrativa + snapshot de `gather-context`: complejidad, tipo de cambio, prefijo, slug, rama base, overrides) — es lo que evita re-investigar el ticket o re-clasificar. Luego bifurcar, **en este orden**:
   - Si tiene **`gate_status: awaiting`** (o `changes-requested`) → el flujo está en el **gate de Jira**; ir a "Gate de Jira (esperando aprobación externa)" abajo.
   - Si no (pausa común en `specify`/`clarify`, con `spec.md` ya escrita), usar
     `spec_approved_at`, nunca la mera existencia de rama. Timestamp → posicionarse con checkout
     seguro y continuar después del gate local; `null` explícito → volver al gate sin preguntar;
     clave ausente en un flujo heredado con spec y rama → preguntar una sola vez y persistir
     timestamp o `null`. Sin rama, retomar desde `specify`/`clarify`. Aplicar el bloque
     `retomado-pre-plan` de `reference.md` para Jira y gate pendiente. La rama creada
     por la preflight nunca prueba aprobación; solo un flujo heredado sin identidad worktree puede
     usarla como pista, y se confirma con el usuario antes de navegar o entrar a `plan`.

### Navegar a la rama correcta (solo ubicación `current` o flujo heredado)
3. Con destino worktree vivo, no navegar: la sesión debe estar allí y el origen snapshot solo muestra el launcher. En otro caso, parsear `id`, `branch`, `base_commit`, `profundidad`, `status` y `wip_commit` del plan.
4. Si la rama actual != `branch`:
   - Antes de cambiar, exigir `git -C <repo-root> status --porcelain --untracked-files=all -- . ':(exclude).plans' ':(exclude).specify'` vacío. Si hay cambios, detener y ofrecer commit o `pause`; `stash` no se ofrece en la rama worktree porque es compartido.
   - Con el árbol limpio, `git checkout <branch>`. Los `.plans/`/`.specify/` untracked no bloquean el checkout ni se pierden.
   - Si `branch` no existe (fue borrada): avisar y ofrecer recrearla desde el commit base (`git checkout -b <branch> <base_commit>`).
5. Coherencia: `git merge-base --is-ancestor <base_commit> HEAD` (si no: avisar que la rama divergió y pedir confirmación).

#### Clasificador durable ejecutado antes de decidir ubicación

En 1c, antes de decidir ubicación, capturar las seis autoridades y clasificar el estado durable con
los cinco pasos de abajo, que son su única sede. El diagnóstico es read-only y va sin checkout
previo: nunca resetea, marca tasks, publica ledger ni adquiere ownership mientras decide qué estado
observa.

1. Validar presencia, `schema_version` y forma del ledger. Inline, legacy, versión desconocida,
   documento corrupto y ledger obligatorio ausente son clases distintas; no inferir bloques desde
   commits o tasks.
2. Capturar ledger, recibo, Git, plan/tasks, proceso/sobre y owner preservando procedencia y frescura.
   El resultado entra como **hecho con procedencia**, nunca como predicado nuevo: `0` lo confirma, `1`
   mapea a `conflict` y `3` mapea a `blocked` —los dos ya declarados no mutantes—, y `2` es una
   invocación mal formada que se corrige y se repite, nunca un veredicto.
3. Clasificar exactamente un cutpoint/terminal. Cero o múltiples predicados, evidencia contradictoria,
   cese incierto u owner obsoleto sin fencing fallan cerrados y no mutan.
4. Sin secuencia aplicable o con `inline-pass-through`, permitir resolver ubicación. Este último solo
   acredita que inline no tiene un efecto externo parcial: no inventa bloques. **Después de que la ubicación permita routing**, si el header trae `wip_commit`, recuperar el trabajo según `pause`. Para un terminal, enrutar
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
   | `planned` | el gate pendiente que la profundidad del header exige: único en **corta**, de plan+tasks en **normal**, de plan en **completa** |
   | `plan-approved` | plan aprobado, tasks no (solo profundidad **completa**) → **gate de `tasks`** |
   | `tasks-ready` | `implement` (Paso común) |
   | `implementing` | `implement`, continuando desde la primera task `[ ]` (y el WIP, si hay `wip_commit`) |
   | `verified` | AC ya en verde; falta commit → `implement` desde el gate de revisión manual |
   | `committed` | falta push → sub-paso `push` |
   | `pushed` | completo en disco; ofrecer `open-pr` (si no hay `pr_url`) o `archive` |
   | `pr-open` | PR ya creado (`pr_url` en el header); no re-ofrecer `open-pr` — ofrecer `archive` si lo das por probado |
   | `done` | ya cerrado; si sigue fuera de `archived/`, ofrecer archivarlo |

   **Un `planned` con `tasks.md` presente retoma igual en el gate del plan.** Es la forma que escribía un flujo complejo antes de que existiera `plan-approved`, y también la que produce un *normal* reclasificado a complejo después de escribir las tasks: en ninguno de los dos casos el artefacto dice si el gate del plan llegó a darse. Ante esa duda se repite el gate, que es barato; inferir que ya se dio saltearía un gate que quizá nadie aprobó.

   Al retomar en `implement` (`tasks-ready`/`implementing`), **re-resolver el modo de ejecución** (override > `implement_mode` > preguntar; ver `implement` → "Modo de ejecución"). Las tasks ya marcadas `[x]` no se repiten en ningún modo.

### Guarda de retomado con bloques en vuelo

La guarda de cuatro superficies queda absorbida por el clasificador durable de arriba: HEAD y
cadena Git, recibo, marcas y ledger se evalúan junto con proceso/sobre y owner. Continúan siendo
casos críticos las tasks `[ ]` cuyo contenido ya vive en un commit y el aplastado parcialmente
transformado; ahora se distinguen los desfases legítimos C1-C12 de `conflict:<source>` y se propone
solo la reconciliación que admite «El contrato con la recuperación».

### Sub-paso `status` (alias de listado)

`/sdd-flow status` no introduce un estado nuevo: es un alias read-only de `resume` en modo listar.
Muestra los mismos datos (`id · branch · estado · siguiente paso`) y, si se pasa un `<id>`, resume
solo ese flujo. La fuente de verdad sigue siendo `plan.md` (`status` + marcas `[x]`) o `handoff.md` en la ventana pre-`plan`; los snapshots worktree se rotulan aparte y siguen el puntero solo con destino y paquete presentes.

### Gate de Jira (esperando aprobación externa)
Con `gate_status: awaiting`/`changes-requested` en `handoff.md` el flujo está parado esperando que
el TL/PO aprueben la subtarea `SPEC: …`; al aprobarse sigue normal a `create-branch` → `analyze` →
`plan`, y el `analyze` corre **después** de la aprobación a propósito. Las tres resoluciones, la
detección por MCP, el loop de observaciones y las escrituras con su STOP de write-safety:
`reference.md` → "Aprobación externa de la spec (Jira)".

### Sub-paso `pause` (dejar un flujo a medias de forma segura)
Aplica en **cualquier fase** del flujo, no solo `implement`. Al pausar:

1. **Escribir/actualizar `handoff.md`** con fase, estado, próximo paso, decisiones y snapshot pre-plan. Preservar siempre ubicación, identidad, contexto, status/etapa/evidencia worktree, y el bloque `transporte` si el flujo lo tiene. Plantilla y momentos: `reference.md` → "Plantilla de `handoff.md`".
2. **Si hay código sin commitear** en la rama del flujo (típicamente en `implement`): **WIP commit en la propia rama** (no `git stash`: el stash es global y se confunde/pierde entre flujos; un commit viaja con su rama): stagear solo `code_touched` y `git commit -m "wip(<id>): pausa sdd-flow"`. Este WIP es **inline a propósito** (no usa `/commit`): es plumbing mecánico y descartable que `resume` deshace con `git reset`, no un commit de contenido. Registrar en el header del `plan.md`: `status: implementing` + `wip_commit: <sha>`. Si además quedan archivos **ajenos** dirty (fuera de `code_touched`), avisarlo: no entran al WIP y quedan sueltos en el working tree — un checkout posterior puede arrastrarlos. (En fases sin `plan.md` ni código —`gather-context`, `specify`/`clarify`, gate de Jira— este paso no aplica: alcanza con el `handoff.md`.)
3. Avisar que quedó pausado y cómo retomarlo (`resume` con el `<id>`). Al retomar, si hubo WIP commit, `resume` lo deshace dejando los cambios en el working tree **sin** stage (`git reset <wip_commit>^`, reset mixed — así el staging selectivo del Paso común sigue valiendo), **reconstruye `code_touched`** desde los archivos del WIP (`git show --name-only --pretty=format: <wip_commit>` — el set en memoria no sobrevive a la sesión) y limpia `wip_commit` del header. **Guard previo:** solo resetear si `git rev-parse HEAD` == `wip_commit`; si no coinciden (hubo commits posteriores al WIP), no tocar la historia — avisar y dejar que el usuario decida cómo integrar el WIP.

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
worktree:
  seed_paths: []                  # qué copiar del origen si falta en este worktree; el config existente se conserva aparte
implement_mode: ask              # cómo ejecutar las tasks: ask (preguntar en el último gate) | inline | cross (delegar a la otra familia vía `cross-implement`; requiere esa skill + el CLI de la otra familia) | workers (delegar a la familia del conductor con el perfil por rol de `.specify/workers.yml`; misma capacidad, y solo en flujos no triviales)
domain_context:
  mode: auto                     # auto | "on" | "off"; solo lectura, nunca escribe ADRs/docs
  context_paths: []              # docs de dominio/glosarios/arquitectura a leer si existen
  adr_paths: []                  # ADRs o decisiones vigentes a leer si existen
vault_archive:                   # rescatar el flujo al vault al archivarlo (opcional; requiere la skill `knowledge-vault`)
  mode: auto                     # auto (default: consulta si hay destino declarado — con destino, ofrece activar la cadena sobre él; sin destino, ofrece descubrimiento y persiste la respuesta) | "on" | "off"  (entre comillas: sin ellas YAML los parsea como booleanos). Con `off` el archivado termina en el movimiento plano y no se vuelve a ofrecer. El disparador es esta clave, **no** que la skill esté instalada: instalarla no es consentir que cada archivado quede encadenado a ella
```

**Este bloque es dueño de las 23 claves que `sdd-flow` gobierna.** Las 14 restantes las poseen sus
hermanas y su enum se define allá: `cross_review.*` en `cross-review/SKILL.md` → "Configuración";
`co_explore.*` en `co-explore/SKILL.md` → "Configuración"; `cross_implement.*` en
`cross-implement/SKILL.md` → "Configuración" y `vault_archive.*` en
`knowledge-vault/reference.md` → "La capa de configuración". El archivo **completo**, con las 40 juntas
y listo para copiar, está en `config-ejemplo.md`, que es una vista de los cinco dueños.

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

## Esquema de `.specify/workers.yml`

Esta sección es la sede dueña del archivo de perfiles de workers. `schema_version` es obligatorio y
su único valor admitido es `1`. La vista enumera los ocho roles y muestra, para cada uno, las dos
familias con sus dos campos. Los valores de modelo y esfuerzo del ejemplo hacen visible la forma;
no declaran defaults.

```yaml
schema_version: 1
roles:
  explore:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-6-sol
      effort: alto
  counter-plan:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-6-sol
      effort: alto
  investigate:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-6-sol
      effort: alto
  debate:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-6-sol
      effort: alto
  design-review:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-6-sol
      effort: alto
  implement:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-6-sol
      effort: alto
  refute:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-6-sol
      effort: alto
  pr:
    claude:
      model: opus
      effort: alto
    codex:
      model: gpt-6-sol
      effort: alto
```

`model` admite un string no vacío o `heredado`. `effort` admite `heredado` o uno de los cinco
literales portables de la tabla de abajo. Ninguna otra clave se admite en ningún nivel.

### Claves admitidas

| Nivel | Claves admitidas |
|---|---|
| raíz | `schema_version` \| `roles` |
| `roles` | `explore` \| `counter-plan` \| `investigate` \| `debate` \| `design-review` \| `implement` \| `refute` \| `pr` |
| cada rol | `claude` \| `codex` |
| cada familia | `model` \| `effort` |

### Enum portable de esfuerzo

El archivo usa los mismos cinco literales para ambas familias. Cada literal se traduce al valor
nativo antes del despacho, con la misma traducción en Claude y Codex:

| Portable | Claude (`--effort`) | Codex (`model_reasoning_effort`) |
|---|---|---|
| `bajo` | `low` | `low` |
| `medio` | `medium` | `medium` |
| `alto` | `high` | `high` |
| `muy_alto` | `xhigh` | `xhigh` |
| `maximo` | `max` | `max` |

### Forma histórica descartada

Este esquema sustituye la forma histórica de perfiles nombrados con indirección por asignaciones.

No se adopta esa forma porque la lista blanca cerrada de `model` y `effort` aporta la misma
garantía: una asignación no puede transportar herramientas, permisos ni autoridad, sin la maquinaria
de la indirección. La forma directa conserva esa frontera sin perfiles intermedios ni referencias que
resolver.

### El literal de herencia

`heredado` reproduce la resolución previa de la vía. Se admite en `model` y `effort`, pero se
materializa por familia y por campo:

| Familia | Campo | Resolución |
|---|---|---|
| `claude` | `model` | el modelo cableado de esa ruta: `opus` en las doce regiones de juicio y `sonnet` en las dos de implementación |
| `claude` | `effort` | ningún flag `--effort`; rige el default del CLI |
| `codex` | `model` y `effort` | el valor de la raíz del config personal del usuario |

Definir el literal solo por familia retiraría el modelo cableado de Claude cuando `model` valiera
`heredado`. Las rutas `bbcr-viab-posix`, `bbcr-viab-ps` y `prfb-codex` tampoco son una excepción:
un `heredado` explícito en Codex toma el config personal, aunque su resolución anterior sin ninguna
autoridad sea el default del CLI.

### La cadena de resolución del perfil

Esta sección es la sede única de la precedencia. Las demás sedes remiten aquí y no copian la cadena.
Antes de recorrerla se aplica el gate de validez, con una asimetría deliberada:

| Momento | Tratamiento de un archivo presente |
|---|---|
| lanzamiento fresco | se valida siempre antes de resolver, incluso con override total; si es inválido, el flujo se detiene antes de despachar |
| sesión reanudada | no consulta ni valida el archivo; la autoridad es el perfil congelado de la sesión |

Cada campo baja por separado hasta el primer escalón que lo resuelve:

| Escalón | Autoridad | Alcance |
|---|---|---|
| 1 | perfil congelado de la sesión | solo en una reanudación; reemplaza juntos `model` y `effort` |
| 2 | override conversacional | solo los campos que nombra; declara si alcanza a un rol, una familia o toda la corrida |
| 3 | archivo de la raíz efectiva | el rol y la familia del archivo; la matriz de defaults completa lo que el archivo omite |
| 4 | resolución anterior | solo el campo que ningún escalón anterior resolvió; rige en corridas standalone y embebidas |

La resolución es por campo salvo en el escalón 1: un perfil congelado parcial rompería la continuidad
de la sesión. Los defaults son relleno del escalón 3 cuando el archivo existe; nunca son fallback de
su ausencia.

La raíz efectiva es la raíz Git del directorio de trabajo de la corrida. Rige exclusivamente su
`.specify/workers.yml`: no se consulta un árbol padre o principal y no se fusionan archivos de dos
raíces.

El valor histórico concreto del escalón 4 es el siguiente:

| Familia y rutas | `model` | `effort` |
|---|---|---|
| Claude, rutas de juicio | modelo `opus` cableado por la receta | ningún flag; default del CLI |
| Claude, rutas de implementación | modelo `sonnet` cableado por la receta | ningún flag; default del CLI |
| Codex, salvo `bbcr-viab-posix`, `bbcr-viab-ps` y `prfb-codex` | raíz del config personal | raíz del config personal |
| Codex, `bbcr-viab-posix`, `bbcr-viab-ps` y `prfb-codex` | default del CLI | default del CLI |

Sin archivo confirmado, sin override aplicable y sin perfil congelado, una ruta fresca conserva ese
valor histórico; esta regla cubre tanto invocaciones standalone como rutas embebidas en otro flujo.
Ninguna skill escribe `.specify/workers.yml`: solo el paso `init` puede crearlo tras la confirmación.
Toda resolución registra, por separado para `model` y `effort`, el número del escalón de origen.

Descontado el estado terminal del archivo inválido, los estados alcanzables colapsan en seis. La
sede no agrega estados porque solo elige el archivo del escalón 3; toda sesión reanudada colapsa en
una fila porque el congelado reemplaza ambos campos.

| Sesión | Override | Archivo | Resultado |
|---|---|---|---|
| reanudada | cualquiera | cualquiera | perfil congelado en ambos campos |
| fresca | total | cualquiera | override en ambos campos |
| fresca | parcial | sí | override en los campos nombrados y archivo, con defaults, en los demás |
| fresca | parcial | no | override en los campos nombrados y resolución anterior en los demás |
| fresca | no | sí | archivo, con defaults para lo omitido |
| fresca | no | no | resolución anterior en ambos campos |

### Matriz de defaults y delta de inicialización

El archivo nuevo contiene los dieciséis perfiles siguientes:

| Rol | `claude` | `codex` |
|---|---|---|
| `explore` | `opus` / `alto` | `gpt-6-sol` / `alto` |
| `counter-plan` | `opus` / `alto` | `gpt-6-sol` / `alto` |
| `investigate` | `opus` / `muy_alto` | `gpt-6-sol` / `muy_alto` |
| `debate` | `opus` / `alto` | `gpt-6-sol` / `alto` |
| `design-review` | `opus` / `muy_alto` | `gpt-6-sol` / `muy_alto` |
| `implement` | `sonnet` / `medio` | `gpt-5.6-terra` / `medio` |
| `refute` | `opus` / `alto` | `gpt-6-sol` / `alto` |
| `pr` | `opus` / `alto` | `gpt-6-sol` / `alto` |

`init` muestra el archivo completo con estos defaults y el delta de abajo antes de escribir. Crea
`.specify/workers.yml` solo tras una confirmación explícita. Si el archivo ya existe y es válido, lo
conserva sin sobrescribirlo.

El delta usa tres columnas y agrupa solo rutas con el mismo baseline. `indeterminado` es un valor
observado como dependiente del entorno, no un dato pendiente:

| Región, ruta y familia | Procedencia y valor anterior | Perfil nuevo y cambio conocido |
|---|---|---|
| familia `claude`; todas las rutas de la matriz salvo las regiones `ci-wc-lanzamiento` y `ci-wc-fix` | procedencia: modelo cableado por la receta y default del CLI; valor anterior: `opus` / esfuerzo `indeterminado` | perfil nuevo: `explore`, `counter-plan`, `debate`, `refute` y `pr` → `opus` / `alto`; `investigate` y `design-review` → `opus` / `muy_alto`; cambio conocido: modelo no cambia, esfuerzo indeterminado |
| familia `claude`; regiones `ci-wc-lanzamiento` y `ci-wc-fix`, ruta `implement` | procedencia: modelo cableado por la receta y default del CLI; valor anterior: `sonnet` / esfuerzo `indeterminado` | perfil nuevo: `implement` → `sonnet` / `medio`; cambio conocido: modelo no cambia, esfuerzo indeterminado |
| familia `codex`; regiones de `cross-review`, `co-explore` y `cross-implement` | procedencia: reinyección de la raíz del config personal; valor anterior: modelo y esfuerzo `indeterminado` | perfil nuevo: `explore`, `counter-plan` y `debate` → `gpt-6-sol` / `alto`; `investigate` y `design-review` → `gpt-6-sol` / `muy_alto`; `implement` → `gpt-5.6-terra` / `medio`; cambio conocido: no, depende del config personal |
| familia `codex`; regiones `bbcr-viab-posix`, `bbcr-viab-ps` y `prfb-codex` | procedencia: default del CLI porque la receta no reinyecta el config; valor anterior: modelo y esfuerzo `indeterminado` | perfil nuevo: `pr` y `refute` → `gpt-6-sol` / `alto`; `implement` → `gpt-5.6-terra` / `medio`; cambio conocido: no, depende del default efectivo del CLI |

En Claude ningún rol cambia de modelo: las catorce regiones marcadas son doce regiones `opus` y dos
regiones `sonnet`, exactamente la partición de la matriz. Todo su delta está en `effort`, que las
recetas actuales no envían.

### Matriz `(región, ruta) → rol`

`ruta` identifica el uso lógico de una receta. Por eso las regiones reutilizadas aparecen una vez
por uso: Bitbucket usa la misma receta para `pr` y `refute` según el prompt; co-exploración usa la
misma receta para `explore`, `counter-plan`, `investigate` o `debate` según el modo.

| Región | Ruta | Rol |
|---|---|---|
| `cr-ronda1-posix` | `design-review` | `design-review` |
| `cr-ronda1-ps` | `design-review` | `design-review` |
| `cr-resume-posix` | `design-review` | `design-review` |
| `cr-resume-ps` | `design-review` | `design-review` |
| `cr-viac-r1-posix` | `design-review` | `design-review` |
| `cr-viac-r1-ps` | `design-review` | `design-review` |
| `cr-viac-resume-posix` | `design-review` | `design-review` |
| `cr-viac-resume-ps` | `design-review` | `design-review` |
| `cr-latencia-sync` | `design-review` | `design-review` |
| `cr-latencia-background` | `design-review` | `design-review` |
| `cr-seed-posix` | `design-review` | `design-review` |
| `cr-seed-ps` | `design-review` | `design-review` |
| `coex-directa-posix` | `explore` | `explore` |
| `coex-directa-posix` | `counter-plan` | `counter-plan` |
| `coex-directa-posix` | `investigate` | `investigate` |
| `coex-directa-posix` | `debate` | `debate` |
| `coex-directa-ps` | `explore` | `explore` |
| `coex-directa-ps` | `counter-plan` | `counter-plan` |
| `coex-directa-ps` | `investigate` | `investigate` |
| `coex-directa-ps` | `debate` | `debate` |
| `coex-latencia-posix` | `explore` | `explore` |
| `coex-latencia-posix` | `counter-plan` | `counter-plan` |
| `coex-latencia-posix` | `investigate` | `investigate` |
| `coex-latencia-posix` | `debate` | `debate` |
| `coex-latencia-ps` | `explore` | `explore` |
| `coex-latencia-ps` | `counter-plan` | `counter-plan` |
| `coex-latencia-ps` | `investigate` | `investigate` |
| `coex-latencia-ps` | `debate` | `debate` |
| `coex-fanout-posix-codex` | `explore` | `explore` |
| `coex-fanout-posix-codex` | `counter-plan` | `counter-plan` |
| `coex-fanout-posix-codex` | `investigate` | `investigate` |
| `coex-fanout-posix-codex` | `debate` | `debate` |
| `coex-fanout-posix-claude` | `explore` | `explore` |
| `coex-fanout-posix-claude` | `counter-plan` | `counter-plan` |
| `coex-fanout-posix-claude` | `investigate` | `investigate` |
| `coex-fanout-posix-claude` | `debate` | `debate` |
| `coex-fanout-ps-codex` | `explore` | `explore` |
| `coex-fanout-ps-codex` | `counter-plan` | `counter-plan` |
| `coex-fanout-ps-codex` | `investigate` | `investigate` |
| `coex-fanout-ps-codex` | `debate` | `debate` |
| `coex-fanout-ps-claude` | `explore` | `explore` |
| `coex-fanout-ps-claude` | `counter-plan` | `counter-plan` |
| `coex-fanout-ps-claude` | `investigate` | `investigate` |
| `coex-fanout-ps-claude` | `debate` | `debate` |
| `ci-wb-posix` | `implement` | `implement` |
| `ci-wb-ps` | `implement` | `implement` |
| `ci-wb-resume` | `implement` | `implement` |
| `ci-wb-resume-ps` | `implement` | `implement` |
| `ci-wc-lanzamiento` | `implement` | `implement` |
| `ci-wc-fix` | `implement` | `implement` |
| `bbcr-viab-posix` | `pr` | `pr` |
| `bbcr-viab-posix` | `refute` | `refute` |
| `bbcr-viab-ps` | `pr` | `pr` |
| `bbcr-viab-ps` | `refute` | `refute` |
| `bbcr-viac-posix` | `pr` | `pr` |
| `bbcr-viac-posix` | `refute` | `refute` |
| `bbcr-viac-ps` | `pr` | `pr` |
| `bbcr-viac-ps` | `refute` | `refute` |
| `prfb-codex` | `implement` | `implement` |

Los ocho roles tienen al menos una ruta en la matriz; la cobertura se valida por identidad de
conjuntos, no por cardinalidad.

### Momentos de resolución y valores inválidos

Cada momento tiene un observable y una autoridad propios:

| Momento | Observable | Autoridad |
|---|---|---|
| lanzamiento | perfil vigente del rol resuelto y enviado al proceso | cadena de resolución, después del gate de validez |
| resume propio | perfil persistido por el lanzamiento de esa misma corrida | perfil congelado de la sesión; nunca el archivo vigente |
| resume de seed | perfil persistido por la sesión de origen, aunque difiera del perfil vigente del rol | perfil congelado de la sesión de origen; nunca el archivo vigente |

La forma inválida comprende: esfuerzo fuera del enum; rol o familia desconocidos; parámetro no
admitido; `schema_version` desconocida; YAML ilegible; forma histórica de perfiles; modelo nulo,
numérico, booleano o vacío; y claves duplicadas. La validación local se detiene antes de despachar,
nombra el valor inválido y la ruta del archivo, y sugiere una corrección concreta.

Si el proveedor o el CLI rechaza un modelo o esfuerzo que sí cumple la forma, el aviso incluye rol,
familia, valor solicitado y valor efectivo. Se reintenta una sola vez: se omite únicamente la opción
rechazada y se conserva el otro campo válido. El perfil del intento exitoso queda congelado para los
resume posteriores. Si el segundo intento falla, el worker queda `UNAVAILABLE`; no existe un tercer
intento. Está prohibido sustituir el campo rechazado por el valor del conductor.

El aviso distingue dos ramas. Si el diagnóstico del proveedor entrega una corrección, la incorpora
textualmente. Si no la entrega, declara expresamente que no hay una corrección fiable disponible;
nunca inventa una desde un catálogo local.

### El modo `workers` de implementación

`implement_mode: workers` delega la implementación a un worker de **la familia del conductor**, con
el perfil del rol `implement` resuelto por la cadena de arriba. Existe para que la elección de worker
deje de ser implícita: `cross` rompe la correlación de errores cambiando de familia, y `workers`
conserva la familia a propósito y declara lo que se pierde.

#### Cuándo se ofrece

`workers` se ofrece **solo fuera de la profundidad corta**, junto a `inline` y `cross`, **dentro del gate
único** que ya pregunta el modo y **sin abrir un gate nuevo**. En profundidad **corta** no se ofrece:
ahí el modo es `inline` sin pregunta, y sumar una opción abriría una decisión que ese nivel excluye a
propósito. Un **override explícito de `workers` vale igual en trivial**, como cualquier otro override
conversacional: lo que trivial suprime es la pregunta, no la elección del usuario.

La oferta está **condicionada a la capacidad**: se ofrece solo si la skill de implementación cruzada
está instalada y **el CLI de la familia del conductor está disponible**. Sin capacidad, la opción no
aparece en la pregunta.

#### A quién delega, y con qué familia

`workers` **delega en `cross-implement`** y **no suma un punto de despacho propio**: el sobre de esa
corrida lo escribe la skill delegada, igual que en `cross`, y el inventario de puntos de despacho de
`sdd-flow` no cambia.

La **familia del implementador queda fijada a la del conductor**, y no se elige ni se pregunta. Se
determina por la familia del agente que conduce, nunca por el inventario.

#### El override de familia no muta el inventario

La familia viaja como **override acotado a esa invocación** de `cross-implement`, y **tiene prohibido
mutar el inventario de familias de la corrida**: su lista, su procedencia y su selección quedan
intactas para toda otra skill. Reemplazar el inventario global por la familia del conductor es
precisamente el problema que este modo viene a evitar, y una implementación que lo haga no satisface
el contrato.

#### Cuándo no se despacha

Dos casos, y son distintos:

| Caso | Qué pasa |
|---|---|
| el `inventario no contiene` la familia del conductor | se declara la incompatibilidad y no se despacha |
| el `CLI same-family no está disponible` | se declara la incompatibilidad y no se despacha |

En ninguno de los dos se **degrada en silencio** a otra familia ni a otro modo.

#### Qué hereda

`workers` hereda el bloque `cross_implement` del config —`execution`, `max_fix_rounds` y `deadline`—
y no tiene bloque propio.

Sus rutas de **degradación** y de **takeover** valen igual que en `cross`, incluido el fallo del
writer **después** del despacho: con cese confirmado el conductor toma el trabajo restante, y con
cese incierto la secuencia se detiene.

#### La partición rige igual

La **partición en bloques y su recibo** se producen y se aprueban igual que en `cross`, y **ningún
bloque se despacha sin recibo aprobado**.

#### Qué se persiste y dónde

| Hecho | Sede |
|---|---|
| el modo lógico `workers` | el `header del plan.md` |
| su proyección | el valor `blocks` del enum `mode` del ledger |
| la familia del implementador | `congelada en el header`, junto al modo |
| el perfil resuelto del rol `implement` | `congelado en el header`, junto al modo |

**El enum del ledger no gana un valor nuevo.** `mode` sigue admitiendo `blocks | inline`, y `workers`
se proyecta a `blocks` porque su secuencia es la de bloques. El ledger no es la sede del modo lógico:
es la de su proyección.

#### La retoma

La retoma **usa la familia y el perfil congelados** en el header, y **rechaza el archivo vigente**:
un `.specify/workers.yml` que cambió entre la pausa y la retoma no reabre la resolución. Es el
escalón 1 de la cadena, y acá es la única autoridad.

La retoma **continúa en el punto correcto** y **no cae en ledger corrupto ni en versión desconocida**:
el ledger sigue siendo un `mode: blocks` válido, así que el clasificador de secuencia lo lee como
cualquier otra corrida por bloques. **El ledger de una corrida `workers` es compatible** con el de una
corrida `cross`, y esa compatibilidad es la que evita que la retoma necesite un camino propio.

#### Compatibilidad hacia atrás

Una corrida **viva iniciada antes de este modo** no se reinterpreta:

| Modo de origen | Al retomar |
|---|---|
| `cross` | su ledger sigue siendo válido y su modo se resuelve como antes |
| `inline` | su ledger sigue siendo válido y su modo se resuelve como antes |

#### El valor retirado

Un `implement_mode` **retirado** —`subagent`— sigue **deteniendo el flujo con su error de
migración**, sin fallback silencioso. Ese error ofrece los modos vigentes, que son `ask`, `inline`,
`cross` y **`workers`**.

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

## Qué escribe `init`

El paso `init` (ver `SKILL.md` → "Paso `init`") materializa `.specify/` a pedido mediante un **wizard** de selección (campos de decisión) + autodetección (comandos), creando los archivos con valores ya resueltos, no plantillas vacías:

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
   worktree:
     seed_paths: []
   jira_approval:
     mode: "off"                # elegido en el wizard junto con tracker/branch_prefix (default off)
   domain_context:
     context_paths: []
     adr_paths: []
   ```

   Los campos de decisión (`tracker`, `branch_prefix` y, solo si se acaba de elegir `tracker: jira`, `jira_approval.mode`) se eligen en el **wizard**. El resto no se pregunta: la skill lo resuelve y lo deja editable en el preview; eso incluye las tres hojas `worktree`, con bootstrap derivado del stack. Quien quiera fijar otra clave la copia de `config-ejemplo.md`. Nada se inventa. Al escribir el config, los valores `on`/`off` se emiten entre comillas.

2. **`.specify/constitution.md`** — desde "Plantilla de constitution" (abajo), con el puntero a los principios de código del repo (`CLAUDE.md`/`AGENTS.md`/`CONTRIBUTING.md`) si existen.

3. **`.specify/workers.yml`** — solo si falta, desde "Matriz de defaults y delta de
   inicialización". El preview incluye el archivo completo y el delta; un archivo válido existente
   se conserva.

Los tres son **locales y untracked** (regla #10) y solo se escriben tras confirmar el preview. Si
`config.yml` o `constitution.md` ya existen, el wizard muestra los valores vigentes
**pre-seleccionados** para mantener o cambiar y fusiona respetando lo puesto a mano. Un
`workers.yml` válido nunca se sobrescribe.

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

El `tasks_fingerprint` se calcula sobre el **modelo canónico** de cada task, y esa proyección se
declara **acá**, que es su única sede: neutraliza el estado del checkbox, normaliza los finales de
línea, recorta los espacios de cada valor y proyecta los campos que nombra la frase siguiente. Decir
«únicamente el checkbox» describe un contrato **anterior**, de cuando la entrada de la huella no
estaba definida. El título, los pasos, los archivos y las dependencias (`Produce` y
`Consume`) son contenido semántico: modificarlos invalida la aprobación. Hashear los bytes completos
de `tasks.md` sería incorrecto porque la transición esperada `[ ]` → `[x]` cambiaría el fingerprint;
hashear solamente los IDs también sería incorrecto porque no detectaría cambios en pasos, archivos o
dependencias.

**El valor de tasks_fingerprint tiene la forma** `sha256:` seguido de
**64 dígitos hexadecimales en minúscula**, con la misma precisión con que el ledger declara los
suyos. De qué bytes se calcula lo fija el párrafo anterior; esto declara su **forma**, que es lo que
el recibo tiene que poder validar sin recomputar el hash.

**El esquema del recibo, adoptado.** La raíz es **cerrada** y contiene exactamente `tasks_fingerprint`
y `blocks`. `blocks` es una lista en su orden aprobado y cada bloque contiene exactamente `block_id`
—cadena no vacía, única en el recibo—, `task_ids` —lista no vacía de cadenas— y `work_commit` —nulo
hasta que el bloque se acepta, y después el SHA completo de su commit de trabajo—. Cualquier clave no
declarada, tipo distinto o cardinalidad inválida hace que el documento **no admita cálculo**.

**El esquema legado se congela con lo que el contrato anterior sí declaraba**, no con menos. Un recibo
escrito antes de la receta sigue siendo válido comprobando **forma y no semántica**, y para eso hace
falta un validador de esa forma; aflojar de más no es compatibilidad, porque vuelve válidos recibos
que este contrato **ya rechazaba** antes de existir la receta. El legado conserva: presencia de
`tasks_fingerprint` y de `blocks`, `blocks` como lista en su orden aprobado, los tres campos por
bloque, y **la unicidad de block_id**. Relaja **solo lo que verdaderamente no estaba definido**: el
cierre de la raíz —una clave extra pasa—, los tipos no declarados, y toda semántica recomputable de la
huella. **Cuál rige lo decide el marcador** de adopción: ausente, el legado; `v1`, el adoptado.

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

Las tablas anteriores siguen siendo las autoridades de esas piezas, y **ninguna sección posterior
las concreta**: la serialización y la lectura viven en «Escritura del ledger», más arriba, y la
reconciliación la resuelve el conductor con el usuario delante. Nada de esto redefine el grafo, los
cutpoints ni los terminales.

## Búsqueda de antecedentes

Detalle del **sub-paso 5** de `gather-context`. Es una consulta al entorno, no un subsistema: dos
comandos y su lectura.

```sh
ls .plans/                                   # flujos abiertos y archivados
git log --oneline --grep '<término>' -20     # por cada término del objetivo
```

Los términos salen del objetivo: la clave del ticket si existe, el nombre del módulo o archivo que el
pedido nombra, y el verbo del cambio. Con dos o tres alcanza; no hay lista canónica que mantener.

**Qué se hace con lo que aparece**, y va en el checkpoint del paso 6, sin stop nuevo:

| Qué se encontró | Qué pasa con el flujo |
|---|---|
| un flujo o commit que **cubre el objetivo entero** | **no avanza a `specify`**: el usuario decide entre cerrar este flujo o reformular el alcance. Una reformulación es suya, no del conductor |
| lo cubre **en parte** | el alcance queda en el **residual** —la resta—, dicho explícitamente en el checkpoint |
| solo **relacionado** | entra como contexto; el alcance queda intacto |

**Es incondicional y no tiene clave que lo apague.** Una búsqueda condicional es el hueco por el que
se rehace trabajo ya hecho. Pero es barata a propósito: el subsistema que vivía acá —con raíz y HEAD
fijados, huellas, revalidación y artefacto propio— costaba 957 líneas para responder una pregunta que
dos comandos contestan, y el criterio 5 de redacción del repositorio de autoría lo dice: una consulta
barata al entorno no se cachea como prosa.

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

## Antecedentes
<solo si la búsqueda del paso 5 encontró algo: qué se encontró —**descrito**, no referenciado: "un
flujo archivado de este repositorio", "una rama con trabajo previo"—, qué parte del objetivo cubre y
qué queda en el residual. **Nunca** rutas de `.plans/`, nombres de ref o rama, SHAs ni el remoto: esta
sección puede terminar publicada en un tracker.>

## Criterios de aceptación
- **AC-1:** Given <contexto>, When <acción>, Then <resultado observable>.
- **AC-2:** <...>

## Clarifications
<Q&A registradas durante `clarify`, **numeradas**. Vacío si no hubo.>
- **Q1:** <pregunta> — **A:** <respuesta> (afecta: AC-n)
<`— **A:**` es el separador reservado: para nombrarlo dentro de una pregunta, va en un tramo de
código —`` `— **A:**` ``— o escapado. En texto plano separa, y dos veces en texto plano es ambiguo.>
```

## El contrato de verificación, en dos formas

Cada `AC-n` lleva **cómo se comprueba**, declarado **antes de implementar**. Qué tan formal sea esa
declaración depende de quién la va a leer, y son dos casos que no se mezclan.

### La forma que consume `verify` (toda corrida no delegada)

Cuatro columnas, en `## Verification` del plan:

| `AC-n` | Evidencia | Comando u observación | Esperado |
|---|---|---|---|
| AC-1 | test | `<comando literal, copiable>` | `<lo que cuenta como cumplido>` |
| AC-2 | observación | `<qué mirar, dónde>` | `<qué tiene que verse>` |

**Se declara antes de implementar, y eso es lo que la hace valer.** Elegir la evidencia después de
escribir el código es elegir la que ya pasa. `verify` **carga** la fila de cada AC, corre su comando
fresco y compara con su `Esperado`; un AC sin fila es un contrato incompleto, no un AC verificado.

**Lo que esta forma no lleva**, y es deliberado: sin identificador propio de fila —el `AC-n` ya la
identifica—, sin columna de baseline, sin estado por fila, sin versiones numeradas, sin hash y sin
token de operación entre versiones. Todo eso acredita hacia atrás **para un lector que no estuvo**, y
en una corrida no delegada el usuario aprobó la tabla en el gate y mira el diff al final.

**La evidencia se mide, no se declara.** Si el comando de una fila ya pasa antes de implementar, esa
fila no discrimina: o el AC está cumplido y sobra, o el comando está mal elegido. Comprobarlo cuesta
correrlo una vez.

### La forma que viaja a un worker (`cross-implement`)

**No se poda.** Cuando el work order se delega, la tabla es la única fuente que el implementador
tiene —arranca con cero contexto de la sesión— y su gate de despacho la verifica entera: versión
vigente con la cadena de integridad cerrada, cobertura bidireccional, campos obligatorios y
**baseline resuelto en toda fila**. Una tabla "congelada pero sin baseline" **no existe** para esa
vía: el preflight se detiene y el worker no sale.

El esquema normativo es el de `cross-implement/contrato-verificacion.md` → "La tabla" y "El bloque de
baseline". No se reescribe acá con otra forma: se llena.

**Cómo se mide un baseline `fallos-*`, que es donde más fácil se afirma de más.**
Con una ejecución directa y cuatro invocaciones aisladas de `rebaseline-worktree.py`, siempre sobre el mismo commit y
el mismo comando. El conductor conserva y compara las cinco parejas de clasificación y proyección; solo
si coinciden **y todas** son `RED` o `GREEN_ALREADY` escribe el registro. Una divergencia, un fallo de
invocación o cualquier `BLOCKED` detiene el sellado — cinco mediciones que no coinciden no son un
baseline, son un comando que no discrimina.

**Por qué la asimetría no es una inconsistencia.** Las dos formas responden a lectores distintos. El
costo del contrato completo se paga **cuando se usa la vía que lo requiere**, no en cada corrida — y
antes se pagaba siempre, incluida la corrida inline donde el único lector estaba mirando la pantalla.

### Si el flujo modifica el `description` de una skill

El contrato lleva además las filas de routing que exige "Casos de routing al cambiar un
`description`". Si no lo modifica, esa sección no aplica y no hace falta leerla.

## Casos de routing al cambiar un `description`

Aplica **solo** cuando un flujo modifica el `description` de una skill instalable; en cualquier otro
flujo esta sección no se lee. El `description` es el **router** que decide qué prompt activa qué
skill, y ningún validador de esquema mide esa conducta: un `description` puede ser estructuralmente
válido y solapar intents con otra skill.

Un flujo así agrega al contrato de verificación, como **filas propias**, los casos de routing —con
`Evidencia` dentro del enum existente, `inspección` o `manual`, sin ampliarlo—:

- **3-5 prompts que deben activar** la skill (*should-trigger*).
- **2-3 near-misses materiales** que **no** deben activarla. Un near-miss no relacionado no cumple:
  tiene que ser un prompt que plausiblemente cae en esta skill y no debe.
- **La adjudicación se hace leyendo solo el `description`**, sin el cuerpo del `SKILL.md`, sin el
  `README.md` y sin el contexto de la conversación que lo escribió. Ese es el único insumo que el
  router tiene en tiempo real; adjudicar con más es medir otra cosa.
- **Cada near-miss nombra a quién debería quedarse con ese prompt.** Si el dueño es **otra skill**,
  el prompt se adjudica **contra los dos `description` por separado** y la fila registra las dos
  lecturas: que uno gane no prueba que el otro pierda. Si el dueño es un **flujo directo** —ninguna
  skill—, se adjudica contra el `description` modificado y se escribe por qué ninguna debe
  quedárselo.
- **Una fila de longitud**, porque el margen contra el tope de 1024 del spec es estrecho y una
  edición del `description` puede cruzarlo sin que el flujo lo note. El chequeo existe fuera
  —`skills-ref validate` verifica el esquema, tope incluido—, pero corre aparte del contrato: la fila
  lo trae **adentro del flujo que edita el `description`**, que es donde el cruce se produce. Su
  oráculo entra en el esquema **sin ampliarlo**: `Comando u observación` es el
  comando que carga el frontmatter y emite la longitud del **scalar YAML ya resuelto** —no la del
  texto plegado del fuente, que cuenta saltos de línea e indentación que el scalar no tiene—, y
  `Esperado` es **≤1024**. El **conteo exacto no va en la fila**: ninguna columna lo admite. Es un
  resultado observado, así que va en la columna
  `Evidencia` de `## Verify` al ejecutarla. **No se introduce un umbral de margen** por debajo de
  1024: el margen medido —`co-explore` en 1019, `cross-implement` en 1011— es el hecho que motiva la
  fila, no un límite nuevo.

**`skills-ref validate` no sustituye a esta sección.** Sigue siendo el chequeo **estructural** —que
`name` case con el directorio, que `description` no exceda el tope, que el frontmatter tenga la
forma del spec— y se corre igual. Lo que no puede ver es la **conducta**: un `description` bien
formado que se roba los prompts de otra skill pasa su validación sin una sola advertencia.

## Plantilla de plan

`.plans/<id>/plan.md` — el **CÓMO**. Empieza con el header YAML obligatorio (fuente del bootstrap de la Vía B).

```markdown
---
id: ABC-123
branch: feature/ABC-123-slug-corto
base_commit: <SHA del HEAD al escribir el plan>
# base_branch: feature/ABC-100-otra   # solo si se cortó de una rama != default_branch (override de base); es el destino del PR
change_type: feat
profundidad: completa  # corta | normal | completa — ver "Profundidad del flujo"
# risk admite low | high | unknown y conserva el valor post-análisis
risk: low
status: planned        # planned → (plan-approved, solo completa) → tasks-ready → implementing → verified → committed → pushed → (pr-open) → done
created_at: 2026-01-01T12:00:00-03:00
# wip_commit: <sha>            # solo si el flujo quedó pausado (ver sub-paso `pause`); se borra al retomar
# jira_subtask: ABC-145       # subtarea SPEC en Jira, si se publicó (gate `publish-spec`)
# jira_subtask_url: https://<tu-site>.atlassian.net/browse/ABC-145   # la usa `open-pr` para linkear la spec
# pr_url: <url>               # PR creado por el sub-paso `open-pr`, si se abrió
---

# Plan — <título corto>

## Enfoque
<estrategia técnica elegida; no listar alternativas descartadas. La más simple que cumple los
AC: lo que esté por encima —una capa, una abstracción, una validación que ningún AC pide— baja
a Decisiones y trade-offs con su porqué, no entra acá como si fuera el default.>

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
<cómo se comprueba cada AC, declarado antes de implementar. Una fila por `AC-n`; sin fila, ese AC no
está verificado. Ver `reference.md` → "El contrato de verificación, en dos formas". Si el flujo se va
a delegar con `cross-implement`, esta tabla se llena en la forma completa que exige su gate.>

| `AC-n` | Evidencia | Comando u observación | Esperado |
|---|---|---|---|
| AC-1 | test | `<comando literal, copiable>` | <lo que cuenta como cumplido> |


## Verify
<lo completa el paso `verify` EJECUTANDO las filas de arriba; vacío hasta entonces. No elige
evidencia: ya está declarada desde antes de implementar.>
| AC | Resultado | Evidencia | Fecha |
|---|---|---|---|
| AC-1 | ✅ / ❌ | <salida observada al correr el comando de su fila> | <ISO-8601> |

## Extras (fuera de AC)
<cambios que entran al commit pero no mapean a ningún AC; vacío por default. Ver "Extras" en SKILL.md>
- E1 — <descripción corta del cambio> · `ruta/archivo.ts:200-210`
```

> **Header dinámico:** `status` lo actualiza la skill al cerrar cada paso (es la fuente de verdad de en qué fase quedó el flujo, leída por `resume`). `wip_commit` aparece solo si el flujo se pausó con cambios sin commitear; `jira_subtask`/`jira_subtask_url` solo si se publicó la spec a Jira (gate `publish-spec`); `pr_url` solo si se abrió PR (`open-pr`). Detalle del ciclo en `SKILL.md` → "Ciclo de status".

> Solo en profundidad **corta** la spec y las tasks van **embebidas** en `plan.md` (no se crean `spec.md`/`tasks.md` aparte). En *normal* la spec va en `spec.md` y las tasks en `tasks.md` (separados, aunque las tasks se aprueben en el gate del plan). Ver "Plantilla de plan combinado".

## Plantilla de plan combinado (profundidad corta)

En profundidad **corta**, un único `plan.md` con la spec y las tasks **embebidas** — es lo que la Vía B y `verify` parsean cuando no existen `spec.md`/`tasks.md`:

```markdown
---
id: none
branch: fix/cart-null-guard
base_commit: <SHA del HEAD>
change_type: fix
profundidad: corta  # corta | normal | completa — ver "Profundidad del flujo"
# risk admite low | high | unknown y conserva el valor post-análisis
risk: low
status: planned
created_at: 2026-01-01T12:00:00-03:00
---

# Plan — <título corto>

## Spec
### Problema / Objetivo
<por qué — 1-2 párrafos>
### Antecedentes
<forma sanitizada del bloque `## declaracion` — nunca rutas, refs, SHAs, el remoto ni claves de `## estado`>
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
formato — un dialecto propio para la profundidad **corta** obligaría a `verify` a entender dos.>

| `AC-n` | Evidencia | Comando u observación | Esperado |
|---|---|---|---|
| AC-1 | test | `<comando literal>` | <lo que cuenta como cumplido> |

## Verify
<lo completa el paso `verify` ejecutando las filas de arriba>
| AC | Resultado | Evidencia | Fecha |
|---|---|---|---|
| AC-1 | ✅ / ❌ | <salida observada> | <ISO-8601> |

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
| AC | Resultado | Evidencia | Fecha |
|---|---|---|---|
| AC-1 | ✅ | `vitest run cart.spec` → 12 passed, exit 0 | 2026-01-01T12:00:00-03:00 |
| AC-2 | ❌ | el botón no se deshabilita con lista vacía | 2026-01-01T12:00:00-03:00 |
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

### Test caracterizador (`change_type: refactor`)

Simétrico del revert-to-confirm, y por el mismo motivo. Un refactor declara que **no** cambia
comportamiento, así que lo que hay que fijar es el comportamiento que se va a mover, antes de
moverlo: donde un `fix` prueba que su test de regresión discrimina, un `refactor` prueba que ya
existía un test que pasaba y que sigue pasando.

**La forma de la evidencia.** Cada AC de comportamiento afectado por el refactor lleva su fila en
`## Verification`, cuyo `Esperado` es **seguir en verde** después del refactor. Como esa fila ya pasa
antes de tocar nada, el plan declara **por qué cuenta igual**: qué comportamiento fija ese test y qué
rompería el refactor si saliera mal. Sin esa frase, una fila que ya está verde no discrimina nada.

**Si ningún test cubre el comportamiento afectado**, ese test se escribe antes de tocar el código y
**no dentro del mismo flujo**: va en un flujo propio —`change_type: test`—, y el refactor se planifica
después contra una base que ya lo tiene. Un test escrito luego del refactor fija lo que el refactor
dejó, no lo que había: no caracteriza nada.

**Por qué un flujo aparte y no una task anterior del mismo**, que es lo que uno escribe primero. Un
flujo mide y congela su contrato sobre el commit base, así que la fila de un test que todavía no
existe no se puede medir ahí: su comando devuelve que falta el archivo, y eso no es el rojo que
discrimina —lo ausente es el test, no el comportamiento— ni el verde que la fila necesita. Diferirla a
una versión posterior del contrato tampoco sale, y por tres precondiciones que se acumulan:

| Precondición del flujo | Qué la rompe |
|---|---|
| la cobertura entre requisitos en alcance y filas cierra **en las dos direcciones** antes de congelar | el criterio del refactor quedaría sin fila en la primera versión |
| el flujo tiene **un** commit, y solo se llega a él con todos los criterios en verde | la task del test tendría que commitear a mitad de `implement`; el único commit intermedio previsto es el WIP de la pausa, que es plomería descartable |
| refrescar las claves congeladas durante la implementación exige ledger terminal, paquete histórico, owner y recibo | eso es la maquinaria de rotación, no un camino ordinario |

Con el test ya en la base, la fila del refactor se mide como cualquier otra y el flujo entra con una
sola versión de contrato. Cuesta un flujo más, y compra que la obligación sea ejecutable por el camino
ordinario en vez de exigir una transición que hoy no existe.

**Los tests que ya existen sirven**, si cubren el comportamiento afectado. Se declaran como la fila
del contrato con su `GREEN_ALREADY` medido, y la adjudicación nombra qué comportamiento cubre ese
test. No alcanza con que la suite esté en verde: una fila cuyo verde no depende del comportamiento
que se mueve es vacua. Lo que el refactor toque fuera de esa cobertura lleva test nuevo.

**Excepciones:** las mismas excepciones del revert-to-confirm, sin volver a enumerarlas — dos listas
sobre el mismo dominio divergen. Cuando una aplica, se documenta y la evidencia pasa a ser la
observación o el comando de `verify`.

**Lo que se descartó, y por qué.** Un revert-to-confirm invertido —mutar el comportamiento para
probar que el test discrimina— sería más fuerte y no se adopta: la mutación hay que inventarla caso
por caso, así que su costo escala con el tamaño del refactor, justo donde el refactor ya es caro.

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
  - **Verificar:** `AC-n` — el AC que esta task cubre, cuya fila en `## Verification` lo prueba.
    Solo el id: repetir acá el comando o el esperado crea una segunda fuente que se desincroniza.

- [ ] **T2 — <acción concreta>**  · cubre: AC-1, AC-2
  - **Por qué:** <…>
  - **Archivos:** <…>
  - **Consume:** `nuevaFn` de T1 (no repetir la firma — referenciarla); bloque global `interfaz-compartida`.
    *(solo si usa algo de otra task o un bloque global; un solo campo, las referencias se acumulan en él)*
  - **Pasos:** <…>
  - **Verificar:** <…>

## Self-review (antes del gate)
- **Cobertura AC ↔ task:** AC-1 → T1, T2 ✓ · AC-2 → T2 ✓ (sin AC huérfanos / sin tasks sin AC).
- **Existencia y pertinencia AC ↔ fila del contrato:** AC-1 → V1 ✓ · AC-2 → V2 ✓ (existencia bidireccional: ni AC sin fila ni fila sin AC) · contrafactual aplicado a V1 y V2 ✓ (pertinencia; ver `cross-implement/contrato-verificacion.md` → «Pertinencia: poder discriminante por fila»). Es lo que el gate de `cross-implement` exige para congelar.
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
  - **Verificar:** `AC-1`
```

## Plantilla de `handoff.md`

`.plans/<id>/handoff.md` — documento de **retomado** del flujo (ver `SKILL.md` → "`handoff.md` (retomado del flujo)"); vive en `.plans/<id>/` (local, untracked como el resto). Frontmatter YAML con los campos máquina + cuerpo narrativo legible.

```markdown
---
phase: awaiting-jira-approval   # gather-context | specify | clarify | awaiting-jira-approval | implementing | ...
# snapshot de gather-context (presente mientras NO exista plan.md; cuando existe, manda plan.md):
profundidad: normal             # corta | normal | completa
risk: low                       # low | high | unknown
change_type: feat               # feat | fix | refactor | chore | docs | test | perf
branch_prefix: feature          # el {type} ya resuelto
slug: export-csv
base_branch: master             # rama base resuelta (con override de base, la rama de la que se corta)
spec_approved_at: null          # timestamp local en normal/complex, o null si sigue pendiente; trivial siempre null
overrides:
  branch_prefix: null
  base_branch: null
  cross_review: null
  implement_mode: null
  jira_approval: null
  worktree: null                # o las tres hojas resueltas para esta corrida; no muta config
# decisión e identidad del worktree; valores permitidos se documentan debajo del bloque
worktree_location: worktree
worktree_path: /ruta/absoluta/al/destino
worktree_branch: feature/export-csv
main_worktree: /ruta/absoluta/al/arbol-principal
origin_worktree: /ruta/absoluta/al/arbol-que-inicio-el-flujo
context_root: /ruta/absoluta/donde-se-exploro
context_head: <SHA explorado>
origin_sha: <SHA usado para crear>
worktree_status: creating
worktree_stage: creating
worktree_evidence:
  - stage: creating
    operation: {kind: create-worktree, target: null}
    command: <literal o null>
    result: ok                  # ok | exit:<n> | timeout:<cota> | refused:<reason-code>
    excerpt: <salida acotada>
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

> **Precedencia:** cuando existe `plan.md`, su `status`, `profundidad`, `risk`, `wip_commit` y
> marcas `[x]` son la verdad operativa; el `handoff.md` aporta narrativa + overrides. Sin `plan.md`
> (specify/clarify/gate de Jira), el frontmatter y `spec_approved_at` son la fuente de verdad de esa
> ventana. Los campos del gate de Jira solo aparecen en pausas por aprobación externa. Detalle en
> `SKILL.md` → "Precedencia con `plan.md`".

Los campos de identidad, ubicación, contexto, status, etapa y evidencia del worktree son siempre
autoridad del handoff y todo escritor los fusiona, incluso cuando ya existe `plan.md`. El bloque
`transporte` se preserva con ellos y por el mismo motivo. Se escriben en
estos momentos: decisión `current` al cerrar el checkpoint; intención `worktree` al cerrarlo; estado
`creating` antes del primer efecto; entrada y resultado de cada etapa; todo `failed` o `abandoned`;
y el doble `ready`, primero en destino y luego en origen. `pause`, `publish-spec`, `plan` y `resume`
solo agregan su información y preservan esa identidad.
`worktree_location` admite `current | worktree`; los enums cerrados de `worktree_status` y
`worktree_stage` son los de “Estado durable y autoridad entre handoffs”. Los comentarios explicativos
de la plantilla no se anexan a esas líneas máquina.

## Resolver la plataforma de terminales

**Antes de crear nada.** La plataforma no se fija: se resuelve consultando las **dos identidades
vivas**, y el resultado gobierna cada rama de este paso. El criterio vive acá, escrito y
autocontenido: esta skill se instala como copia y corre sobre repositorios ajenos, así que no puede
depender de la ruta de ningún script de otro repositorio. **Esta es la sede del detector, y el flujo SDD la consume por lectura.** No hay ninguna dependencia
de ejecución sobre un script de otro repositorio: el criterio está escrito acá y es autocontenido,
que es lo que permite que una instalación suelta lo aplique sobre un repositorio ajeno.

### Los cuatro estados por identidad

Cada plataforma se consulta por su identidad de panel. Los estados son cuatro y no dos, porque
«presente» no es «utilizable»:

| Estado | Qué se observó |
|---|---|
| `resuelve` | la identidad existe **y** la plataforma la reconoce como panel vivo |
| `rancia` | la identidad existe y la plataforma **no** la reconoce |
| `ausente` | no hay identidad declarada |
| `inconsultable` | hay identidad y la consulta a la plataforma falló |

### La matriz, y su destino

**Las variables son las que el runtime exporta de verdad, y la salida se parsea, no se grepea.**
`HERDR_PANE_ID` contra `herdr pane list`, y `ORCA_TERMINAL_HANDLE` contra `orca terminal list
--json`: la pertenencia de la identidad al conjunto vivo **es** el predicado. Inventar un nombre de
variable o un subcomando de consulta individual tiene un modo de falla mudo — la condición queda
falsa en una sesión sana y el destino cae a `headless`, que es indistinguible de no tener plataforma.

> **Por qué el parseo y no un `grep`, con el caso que lo obligó.** Un `grep` del literal acredita
> `resuelve` sobre una salida **truncada o malformada** que apenas contenga `"handle":"term-1"`, y ahí
> la comprobación deja de fallar cerrada: medido con una salida `not-json {"handle":"term-1"` que sale
> con código 0. Y ante bytes ilegibles devuelve `rancia`, que es la lectura que el adaptador retirado dejó de
> hacer a propósito. Las dos son propiedades **estructurales** de la salida, y ningún patrón de texto
> las distingue: por eso este es el único lugar del procedimiento donde se sube de `grep` a un
> intérprete.
>
> **Y la consulta corre adentro de ese intérprete, no antes.** Una sustitución de comandos del shell
> **no conserva los bytes NUL**: medido, un CLI que emite `"handle":"term\0-1"` le entrega al parser
> `"term-1"`, que coincide con la variable y acredita `resuelve` sobre una salida corrupta. Parsear
> estricto no alcanza si los bytes ya se sanearon en el camino, así que el proceso hijo se lanza desde
> adentro y de ahí salen tanto su salida cruda como su código.

```sh
# uso: estado_identidad <herdr|orca>  → imprime resuelve|rancia|ausente|inconsultable
# la consulta corre DENTRO del intérprete: una sustitución de comandos del shell no conserva
# los bytes NUL, así que una salida corrupta llegaría saneada y se acreditaría como viva
estado_identidad() {
  estado=$(python3 -c 'import json, os, subprocess, sys
CUAL = {"herdr": ("HERDR_PANE_ID", ["herdr","pane","list"], "panes", "pane_id"),
        "orca":  ("ORCA_TERMINAL_HANDLE", ["orca","terminal","list","--json"], "terminals", "handle")}
if sys.argv[1] not in CUAL: print("inconsultable"); raise SystemExit
var, cmd, caja, clave = CUAL[sys.argv[1]]
valor = os.environ.get(var)
if not valor: print("ausente"); raise SystemExit
try: hecho = subprocess.run(cmd, capture_output=True, timeout=15)
except (OSError, subprocess.SubprocessError): print("inconsultable"); raise SystemExit
if hecho.returncode != 0: print("inconsultable"); raise SystemExit
try: texto = hecho.stdout.decode("utf-8")
except UnicodeDecodeError: print("inconsultable"); raise SystemExit
try: raiz = json.loads(texto)
except ValueError: raiz = {}
if not isinstance(raiz, dict): raiz = {}
hijos = raiz.get("result", raiz)
hijos = hijos.get(caja, []) if isinstance(hijos, dict) else []
print("resuelve" if valor in {h.get(clave) for h in hijos if isinstance(h, dict)} else "rancia")
' "$1" 2>/dev/null)
  [ -n "$estado" ] || estado=inconsultable   # sin intérprete no se acredita nada
  echo "$estado"
}
# uso: resolver_plataforma [plataforma-pedida]
#   sigue: imprime "<plataforma> <identidad>" y devuelve 0
#   para:  imprime "headless <causa>"        y devuelve 1
resolver_plataforma() {
  pedida="${1:-}"
  eh=$(estado_identidad herdr); eo=$(estado_identidad orca)
  if [ -n "$pedida" ]; then
    case "$pedida" in
      herdr) [ "$eh" = resuelve ] && { echo "herdr $HERDR_PANE_ID"; return 0; }
             echo "headless override-herdr-$eh"; return 1 ;;
      orca)  [ "$eo" = resuelve ] && { echo "orca $ORCA_TERMINAL_HANDLE"; return 0; }
             echo "headless override-orca-$eo"; return 1 ;;
      *)     echo "headless override-no-reconocido"; return 1 ;;
    esac
  fi
  case "$eh:$eo" in
    resuelve:resuelve) echo "headless ambas-resuelven"; return 1 ;;
    resuelve:*)        echo "herdr $HERDR_PANE_ID";     return 0 ;;
    *:resuelve)        echo "orca $ORCA_TERMINAL_HANDLE"; return 0 ;;
    *)                 echo "headless $eh:$eo";         return 1 ;;
  esac
}
```

**Emite dos campos, la plataforma y la identidad, y el segundo no es decorativo:** es lo que
revalida cada efecto. Un destino a secas obligaría a re-resolver, que es volver a **elegir**
plataforma en vez de **comprobar** la que ya se eligió.

> **De dónde salió esta matriz, y las dos divergencias que conserva.** Estados, variables y destinos
> se derivaron del adaptador que este ecosistema retiró, y esa derivación ya ocurrió: **la sede es
> ahora esta**, no aquel archivo, y la dirección no vuelve a invertirse. Se dejan escritas las dos
> divergencias porque son decisiones y no accidentes, no porque haya nada contra lo que cotejar.
> Cotejados en su momento caso por caso con la misma entrada —salida válida, identidad
> ausente de la lista, JSON truncado, bytes ilegibles, salida vacía y consulta fallida—, los dos
> coincidían. Difieren en dos puntos, los dos declarados:
>
> - el adaptador reservaba un código propio para las **dos** identidades inconsultables; acá ese caso
>   cae en `headless`, que es el mismo destino que su propia tabla le asigna.
> - ante un JSON **válido** cuya raíz no es un objeto, el adaptador **terminaba con una excepción** en
>   vez de emitir su sobre; este bloque comprueba el tipo antes de indexar y resuelve `rancia`. La
>   divergencia es deliberada y va hacia el lado seguro: **no se replica un fallo**.
>
> Si falta el intérprete, el estado es `inconsultable` y no `rancia`: sin con qué comprobar no se
> acredita una identidad.

**`headless` no significa lo mismo en todas sus causas, y la matriz de abajo es la que manda.** En
este flujo la vía por línea de comandos **existe y es legítima** —es la rama (b) del carrier—, así
que la ausencia de plataforma viva no detiene nada: continúa por ahí. Lo que **sí detiene** es la
causa del empate: con **las dos identidades vivas** y sin override no hay observación que diga cuál
es el anfitrión, y elegir una sería adivinar sobre qué máquina se crean recursos.

> **Una skill hermana dice lo contrario, y con razón.** En la admisión de incidentes `headless` es
> **parada** por cualquiera de sus causas, porque ahí el paso siguiente necesita un agente
> interactivo al que despachar y no hay vía por línea de comandos que lo reemplace. Acá sí la hay.
> El enunciado no es portable entre las dos, y copiarlo de una a otra deja a este flujo deteniéndose
> ante un caso que su propia matriz resuelve.

### El override del usuario dirige, no suple

Si el usuario pide una plataforma, esa petición **elige cuál se intenta**, no acredita que sirva:
viaja como **argumento** de `resolver_plataforma` —no como una decisión tomada antes de llamarlo— y
la identidad de la elegida se comprueba igual:

| Caso | Resultado |
|---|---|
| override, con su identidad `resuelve` | se usa la pedida |
| override, con su identidad `rancia`, `ausente` o `inconsultable` | **se detiene**; la petición no sustituye la comprobación |
| sin override, una sola identidad `resuelve` | se usa esa |
| sin override, las dos `resuelven` | **se detiene**: no hay observable que identifique al anfitrión |
| las dos `resuelven` **con** override comprobado | el override **desempata** — es el único caso en que lo hace |
| sin override, **ninguna** identidad `resuelve` | continúa por la **vía por línea de comandos** |

**La matriz es total sobre las dos señales, y por eso tiene seis filas y no cinco.** Las cinco
primeras cubren override y empate; la sexta cubre el caso en que **ninguna** identidad resuelve, que
no es una detención sino la parada normal del detector: sin plataforma viva, el flujo continúa por
la vía por línea de comandos, que no se retira. Sin esa fila la matriz dejaba un caso sin destino, y
un caso sin destino lo resuelve quien implementa, no quien especifica.

### La identidad se revalida antes de cada efecto

Una identidad viva al resolver puede dejar de serlo a mitad del paso, y cada efecto que dependa de
ella la vuelve a comprobar **inmediatamente antes**, con `estado_identidad "<plataforma>"` sobre la
plataforma ya resuelta — **nunca** con `resolver_plataforma`, que volvería a elegir en vez de
comprobar, y que ante una identidad caída podría devolver la **otra** plataforma a mitad del paso.
Los efectos son estos seis y la lista es
exhaustiva: **crear** el worktree por la plataforma, **adoptar** un árbol creado con Git, **abrir** el
panel, **arrancar** el agente, **rotular** el worktree y **entregar** el encargo. Si la
revalidación falla, ese efecto no se ejecuta y se aplica la fila que le corresponda en «El contrato
de fallo por fase».

---

### El carrier de transporte, y sus cuatro ramas

Un punto de despacho que va a emitir workers **no elige** su vía: la resuelve desde el **carrier de
transporte**, el objeto que viaja con la invocación y declara por dónde corre este lote. Se lo invoque
desde el flujo que resolvió la plataforma, de forma anidada, de forma autónoma o al retomar, el punto
aplica la misma máquina de **cuatro ramas exhaustivas, y ninguna otra**. **Ninguna rama se hereda por
suposición:** un carrier que no viajó es ausencia, no una autorización tácita a reusar la elección que
tomó otro punto.

> **No es el carrier del inventario de familias, y confundirlos rompe los dos.** `family_inventory`
> lleva **quiénes** pueden atender —`families` y `selection`—, y su raíz es quien ya anunció una
> ausencia; el carrier de transporte lleva **por dónde** se los despacha. Un punto puede heredar el
> primero y no tener el segundo, y al revés: son dos preguntas distintas con dos autoridades
> distintas, y lo único que comparten es la palabra «carrier».

#### Los campos

| Campo | Qué lleva |
|---|---|
| `fase` | la fase del flujo que este carrier gobierna; uno de otra fase **no es válido** |
| `transport` | `plataforma` cuando el lote corre por paneles; `transport: cli` cuando la elección registrada es la vía por línea de comandos |
| `plataforma` | `herdr` \| `orca`, presente solo con `transport: plataforma` |
| `identidad` | la identidad de panel que emitió el detector, y que se **revalida antes de cada efecto** |
| `consentimiento` | puntero al consentimiento sellado, con su `digest` |
| `alcance` | el **lote real** que ese consentimiento autoriza |
| `skills_plataforma` | el conjunto de skills de plataforma cargado; vacío con `transport: cli` |

#### Las cuatro ramas

| Rama | Qué observa el punto | Qué hace |
|---|---|---|
| **(a) carrier de plataforma válido** | `transport: plataforma`, fase igual a la activa, identidad que revalida y consentimiento cuyo digest verifica | lo **consume sin volver a ofrecer**, revalidando la identidad inmediatamente antes de cada efecto |
| **(b) `transport: cli` registrado** | la vía por línea de comandos, registrada **como elección** | corre su receta headless, **no carga ninguna skill de plataforma** y no ofrece nada |
| **(c) carrier ausente** | no viajó ninguno | resuelve la plataforma, propone y **sella** un carrier antes del primer efecto |
| **(d) carrier presente pero inválido** | rancio, de otra fase, o con consentimiento que no revalida | **nunca se usa**; su salida depende de si ya hubo efectos |

**(b) no es (c), y distinguirlas es la mitad del criterio.** Un carrier con `transport: cli` es una
elección con asiento propio: alguien resolvió que este lote corre por línea de comandos. La ausencia
de carrier es que nadie resolvió nada. Leer la segunda como la primera es exactamente cómo un punto
termina corriendo headless sin que ninguna persona lo haya elegido, y después **el registro no las
distingue**, porque las dos se ven igual: sin paneles.

**Las dos salidas de (d):**

| Estado de la vía anterior | Salida |
|---|---|
| **sin efectos previos** | pide consentimiento nuevo, igual que (c), y no reusa nada del carrier inválido |
| **con efectos o residuales** | **se detiene** hasta acreditar su cese con una señal de **cese positivo** |

**Qué cuenta como cese positivo acá, porque «no veo nada» no es una señal.** El cese de la vía
anterior se acredita **observando** que sus recursos dejaron de existir —enumerando con la propia
plataforma y no encontrando los workers de esa corrida—, nunca por la ausencia de una señal
contraria: una plataforma que dejó de responder produce exactamente la misma nada que una cuyos
paneles se cerraron, y una de las dos sigue teniendo procesos vivos escribiendo en el worktree. Lo
que no se puede acreditar se enumera como **residual**, que es lo que el punto 3 de la oferta —la
política de cierre— le prometió al usuario, y con residuales el carrier inválido no se reemplaza: se
detiene.

#### El preflight de capacidades falla cerrado antes de crear

Antes del primer recurso, el punto comprueba lo que su rama exige —identidad que revalida, digest que
verifica, alcance que cubre el lote, skills de plataforma cargadas—. Ese preflight **falla cerrado
antes de crear** cualquier recurso: ante una comprobación que no pasa no se crea nada y el punto se
detiene. El orden no es intercambiable, y por eso se escribe: comprobar después de crear deja
recursos vivos que nadie autorizó, y convierte el remedio en liquidarlos en vez de no haberlos
creado — que es la misma asimetría por la que el sellado del lote precede al primer efecto y no al
primer despacho.

Para **entregar** por plataforma, el conjunto de guías del terreno servido por su binario debe
declarar, antes de crear, cinco clases de observación: disponibilidad previa del worker; un medio
para contrastar la identidad del worker creado con el despacho activo; cadencia y cota de reconsulta
de la disponibilidad; cadencia y cota de consulta posterior al envío; y un efecto atribuible al
encargo actual que acredite ejecución comenzada o concluida. El medio de contraste se comprueba en
el preflight y su valor después de crear. Cada espera por condición solo cuenta como cadencia
dirigida por eventos si la guía especifica condición, cota y resultado al no satisfacerse. Si falta
o es ilegible cualquiera de las cinco definiciones, no se inventan estados, pausas ni plazos: la
capacidad obligatoria está incompleta y el punto falla cerrado **antes de crear**, sin degradar. La
entrada pendiente separada se comprueba únicamente cuando el conjunto la expone y aplica; no es una
sexta obligación universal.

#### El alcance es el lote real, no un tope fijo

`alcance` enumera el **lote real** de ese punto —cuántos workers, con qué rol cada uno y sobre qué
worktree—, y es exactamente lo que el consentimiento autoriza. Un reparto por repo autoriza sus N
repos, sus worktrees y sus roles, o **no se despacha**.

```json
"alcance": {
  "workers": [
    {"rol": "w1", "worktree": "/ruta/absoluta/al/worktree"},
    {"rol": "w2", "worktree": "/ruta/absoluta/al/worktree"}
  ],
  "abrir_sesion": true
}
```

**Por qué no alcanza un tope numérico.** Un máximo de paneles sirve mientras todos los puntos tengan
la forma del fan-out dual —dos workers, dos roles, un worktree—, y **once puntos no la tienen**: el
panel de revisores de `bitbucket-code-review` es uno por familia disponible, la revisión final de
diff es uno solo, y un reparto de `sdd-orchestrator` es uno por repo, cada uno sobre **su** worktree.
Con un tope, el consentimiento de un reparto de cuatro repos autoriza «cuatro paneles» sin decir
sobre qué árboles: el usuario consiente un número y recibe efectos sobre directorios que nunca vio.
Con el lote enumerado, cada worker que se crea tiene que **estar en la lista**, y eso es una
comprobación por worker en vez de una cuenta.

**Qué se comprueba contra el alcance antes de crear cada worker:** que su rol esté enumerado, que su
worktree sea uno de los declarados, y que ese worker no esté ya creado. Un worker que no figura no se
crea y la corrida se detiene — no es un exceso que se recorta, es un lote distinto del consentido.

**Un consentimiento con la forma anterior —un tope numérico y un solo worktree— sigue siendo
legible, y no cae en (d).** Es válido para el lote que sí describe, y queda corto solo ante uno que lo
exceda, que es donde el punto se detiene. Esa forma la emitía el productor que este cambio retiró, así
que **ningún productor la escribe ya**; lo que se conserva es la capacidad de leerla, porque un
consentimiento sellado bajo ella describe correctamente lo que el usuario autorizó en su momento —es
la misma razón por la que la matriz de adopción no retira los valores viejos de ningún enum.

#### Dónde se persiste, y por qué por fase

El **transporte por fase** es la regla: cada fase lleva su propio carrier y su propio consentimiento
sellado, y ninguna hereda el de otra.

`sdd-flow` persiste el carrier en el bloque `transporte` de su documento de retomado, **por fase**:
cerrada una fase, el carrier de la siguiente queda sin resolver y la retoma vuelve a ofrecer la vía,
con su propio consentimiento sellado. `sdd-orchestrator` lo persiste en el `manifest.yml` de la
orquestación, que es su sede equivalente.

**Por fase y no por flujo, porque un flujo de dos plataformas tiene dos elecciones.** Un carrier por
flujo haría que la segunda fase heredara la vía de la primera sin que nadie la eligiera, que es la
herencia por suposición que la máquina de arriba prohíbe. Y la retoma, que tiene prohibido volver a
ofrecer una vía ya consentida, no tendría con qué distinguir «esta fase no eligió» de «esta fase ya
eligió»: el mismo bloque significaría las dos cosas.

### Cómo un punto de despacho opera por la plataforma

Resuelta la rama (a) del carrier, el punto **expresa intención y consume el resultado**. Las
capacidades son seis y la lista es exhaustiva: **crear** el worker, **colocarlo** respecto del
conductor, **entregarle** su encargo, **esperar** con su presupuesto, **obtener** su resultado y
**liquidar** lo creado. En esa rama **no sobrevive ningún verbo de plataforma**: un punto que
nombra un subcomando de Orca o de Herdr está modelando la plataforma en vez de usarla, y esa prosa
envejece con cada release ajeno sin que nada la ponga roja.

Al routing entre guías se entrega la **operación con su régimen**, no las capacidades sueltas. La
lectura atomizada queda negada: sin su objeto ni su régimen, las seis capacidades caen enteras en la
guía ordinaria, cuya descripción cubre crear un agente, mandarle un prompt y esperar en una terminal.
El régimen lo da la regla de pertenencia, en
`skills/cross-review/corridas-en-vuelo.md` → «La clase de operación se sigue de la pertenencia»,
que **se carga antes del preflight**: sin ella el punto no tiene con qué expresar su intención y
el routing resuelve sin el dato que lo decide.

#### La colocación se pide como intención, y su resultado se declara

La colocación admite una lista cerrada de exactamente dos valores: `adyacente-al-conductor` e
`independiente`. Es una capacidad y no un atributo de **crear** porque su contrato contiene una
intención elegible, un costo consentido y un resultado observable; cuántas operaciones internas
requiera una plataforma no la define. La asimetría de la tabla de «El perfil viaja al crear, y se
contrasta» es evidencia del costo en una plataforma medida, no una definición universal.

Pedir `adyacente-al-conductor` puede volver **inacreditable el perfil**. En al menos una plataforma
medida las dos opciones son **excluyentes por contrato**; por ese costo, el invariante de familia se
comprueba **antes de lanzar**, en vez de acreditarse después.

**Excepción al fallo cerrado, y su destino en la matriz canónica.** Si falta la capacidad de colocar
como se pidió, esa ausencia no hace fallar cerrado el preflight: la corrida **continúa por la
plataforma**, con la colocación que esa plataforma aplique, y declara la colocación efectivamente
obtenida o su estado **incierto** con el motivo. La excepción existe porque la colocación determina
dónde se ve el worker, no si existe, trabaja o se liquida; afirmar una colocación no obtenida sigue
vedado.

**Ese destino tiene precedencia sobre la segunda fila de «Los cinco destinos del preflight de
capacidades», y la matriz lo declara de su lado.** Sin esa precedencia, la ausencia de colocación cae
en «falla antes del primer recurso y no falta ninguna capacidad obligatoria» y ordenaría **degradar a
la vía por línea de comandos**, que contradice dos cosas a la vez: esta excepción, que manda
continuar; y «La activación de la plataforma es atómica», que prohíbe que un punto se escape por
línea de comandos. Con las tres redacciones conviviendo, dos conductores igualmente conformes
ejecutaban comportamientos distintos. Degradar toda la fase por dónde queda una ventana sería además
desproporcionado: se perdería el registro que la plataforma da, para comprar una preferencia de
visibilidad.

#### El routing entre guías lo deciden las guías

Una plataforma puede publicar **más de una skill** —una que cubre la coordinación de workers y otra
la operación de terminales—. El flujo carga **todas las guías del terreno como conjunto**. Con una
sola no hay reparto que resolver; cuando hay varias, el reparto sale de sus descripciones.

Si una descripción es insuficiente, las descripciones se solapan o se contradicen, el flujo lo
declara y se detiene; no desempata.

**Por qué no un criterio propio.** Un reparto escrito acá es una copia del de la plataforma, y la
copia se desincroniza con la primera versión que reordene sus capacidades — sin que ningún
verificador de este repositorio pueda verlo, porque la fuente vive afuera.

**Que el usuario no tenga que saberlo es el criterio, no una comodidad.** La partición entre esas
skills es una decisión de quien las publica y puede cambiar en la versión siguiente: una interfaz
que obligue a elegir entre ellas traslada al usuario una distinción que no es suya y que envejece
sola.

#### Una indicación concreta del usuario no se vuelve a decidir

> **Disparador:** el usuario indica **qué skill de plataforma** usar para abrir una terminal con un
> agente y darle un encargo — típicamente un **encargo de prueba**, para ver el mecanismo funcionando
> de punta a punta.
> **Efecto:** se usa **esa**, tal como se indicó. No se vuelve a detectar la plataforma, no se vuelve
> a resolver el routing entre guías y **no se vuelve a proponer** ninguna alternativa.
> **Excepción:** ninguna. Si la skill indicada no puede servir su guía desde el binario, eso se
> declara como precondición no satisfecha y se detiene — no se sustituye por otra.

**Por qué es una regla y no una cortesía.** Las dos secciones de arriba existen para decidir cuando
**nadie decidió**: el detector resuelve la plataforma y las descripciones resuelven el reparto. Una
indicación del usuario ya cerró las dos preguntas, así que volver a correrlas no agrega información
— puede **contradecirla**, y ahí el flujo estaría discutiendo con quien lo dirige. Re-proponer tiene
además un costo propio: convierte una instrucción en una consulta, y el usuario que ya eligió tiene
que volver a elegir lo mismo.

**Lo que la indicación no dispensa.** Sigue rigiendo la carga desde el binario: una skill nombrada
por el usuario también tiene que servir su guía por el verbo que publica, porque lo que la
indicación fija es **cuál**, no que se pueda saltear la precondición. Y sigue rigiendo el
consentimiento del transporte: nombrar la skill no amplía por sí solo cuántos recursos se pueden
crear ni con qué roles.

#### El protocolo de la plataforma no se modela

Cómo la plataforma comunica sus terminales —sus mensajes, sus estados, sus latidos y su forma de
reportar el fin— **no se modela** en el flujo: no se replica, no se traduce a un vocabulario propio
y no se le agregan estados intermedios. El flujo pide una capacidad y lee lo que vuelve.

**Y hay una medición que lo obliga, no una preferencia de estilo.** El último latido de un worker
dice «vivo» **seis segundos antes de morir**, así que un modelo propio del protocolo que derive
«sigue trabajando» de un latido reciente afirma algo que la plataforma nunca dijo. Lo que se lee es
la señal que la plataforma emite para eso, y lo que no emita queda **incierto** — que es un estado
del flujo, no una traducción del protocolo ajeno.

#### La cosecha por pantalla se normaliza antes de comparar, y eso no es modelar el protocolo

Cuando la capacidad de **obtener el resultado** devuelve una lectura de la pantalla del worker, lo
que vuelve **no es el texto que el worker emitió**: es ese texto ya maquetado por el TUI del agente,
que lo envuelve y lo indenta a su ancho. Comparar un resultado esperado contra esa lectura **línea
por línea** hace que el veredicto dependa de la geometría del panel.

**Medido, en dos corridas de la misma prueba sobre la misma plataforma.** Un resultado de una línea
—una marca más un `sha256`, 90 caracteres— se verificó con un `grep` de literal exacto: **verde** en
los paneles de 146 columnas de ancho, y **rojo en los de 73**, donde el TUI lo partió en dos con dos
espacios de sangría. Las **cuatro** fuentes de lectura que la plataforma ofrece devolvieron lo mismo,
incluida la que une los saltos blandos: ese salto **no** es un salto blando del terminal, así que no
hay fuente que lo repare. El resultado estaba entero y correcto en las dos.

**Entonces el flujo normaliza antes de comparar** —junta las líneas y descarta los espacios—, o usa
el camino que la guía de la plataforma declare para recuperar una salida completa. Lo que **no** se
hace es ensanchar el panel para que el veredicto dé verde, y hay **dos** razones, la segunda medida:
ata la corrección de la verificación a una decisión de layout, y **el verbo que ensancha mueve el
foco**. Medido: un conductor delegado que topó con este mismo corte lo resolvió agrandando el panel
del worker, y el foco pasó **al panel del worker** en vez de quedarse donde la persona estaba
trabajando — un efecto sobre la pantalla de alguien, para arreglar una comparación de texto. Duró lo
que duró ese panel y volvió solo al cerrarlo, así que el costo es de la ventana, no permanente; se
escribe igual porque esa ventana es justo cuando alguien está mirando la corrida.

**Y normalizar una lectura de pantalla no es modelar el protocolo.** La sección siguiente prohíbe
replicar los mensajes, los estados y los latidos de la plataforma, y esto no toca nada de eso: no
inventa una señal de fin, no traduce estados y no deriva «sigue trabajando» de ningún indicio. Es
leer un texto que llegó maquetado. Conviene dejarlo escrito porque las dos cosas se parecen desde
lejos, y confundirlas empuja a la salida contraria: no normalizar y creerle al falso rojo.

#### El perfil viaja al crear, y se contrasta

Cuando el punto **crea** la terminal de un worker, el perfil solicitado —rol y familia— viaja en el
lanzamiento, y el flujo lo contrasta contra el **perfil efectivo** que la plataforma reporta. Si
difiere del solicitado, **se detiene antes de crear más recursos**: un worker corriendo con otro
perfil que el pedido ya es un resultado que nadie autorizó, y crear los siguientes multiplica el
error antes de que alguien lo mire.

**El discriminante es quién arranca al agente, no si la terminal preexistía.** Si lo arranca **la
plataforma**, la familia viaja en el lanzamiento y el contraste se exige; si lo arrancó **otro** —el
comando con que se creó la terminal, o un operador—, el perfil **no es solicitable ni acreditable** y
eso **se declara sin detener**. Declarar que no se pudo acreditar es información; detenerse por ello
sería detener toda reutilización.

**La primera redacción decía «terminal preexistente» y era una generalización de una sola
plataforma.** Las dos mediciones, que es lo que la corrige:

| Plataforma | Cómo se crea el worker | Perfil efectivo | Por qué |
|---|---|---|---|
| Orca | la colocación por splits obliga a crear la terminal antes y adjuntarla | `launch.effective.agent: null` | el agente lo fijó el `--command` del split, que la plataforma no interpreta; y sus dos opciones son **excluyentes por contrato** |
| Herdr | el split crea un pane **vacío** y la plataforma arranca al agente sobre él | **acreditado** | el arranque es de la plataforma, que valida la identidad del agente antes de devolver |

**Entonces la terminal preexiste en las dos y el resultado es opuesto**, entre otras cosas porque
Herdr separa el pane del agente: el pane es una ubicación y el agente se arranca aparte, así que la
colocación pedida por el usuario y el registro de familia **no compiten**. Escrito como estaba, el
flujo le atribuía al mecanismo una carencia que era de una plataforma — y la habría arrastrado a
cualquier plataforma que se integre después.

#### La entrega exige disponibilidad previa y efecto atribuible posterior

Para cada worker creado, antes de escribir se contrasta su identidad con el despacho activo por el
medio declarado en el conjunto vigente de guías. Esto no repite el contraste de rol, familia o
perfil hecho al crear. Se conserva una muestra previa **vigente**, vinculada al worker y al encargo
actual solo durante esta entrega; no se agrega un campo durable. La escritura se habilita únicamente
si esa muestra acredita disponibilidad y la guía permite distinguir después un efecto atribuible al
encargo nuevo. Un worker ya terminal sin marca monótona o única que pueda atribuirse a la ejecución
de un encargo nuevo no se reutiliza: se detiene antes de escribir, sin destruirlo.

La indisponibilidad transitoria se reconsulta con la cadencia y hasta la cota de la guía. Una
condición que requiere intervención humana o una identidad distinta detiene como **causa conocida**;
una muestra ausente, desconocida, ilegible o contradictoria detiene como **resultado incierto**. En
ambos casos se conservan los recursos y se presentan al usuario como se indica abajo. Ni una pausa
fija ni un acuse de transporte acreditan disponibilidad.

La cota efectiva de reconsulta se recorta al `wait_budget` restante, sin reiniciarlo. Si el
presupuesto vence antes o **a la vez** que la cota propia, rige `corte_presupuesto` y la corrida
permanece activa según `skills/cross-review/corridas-en-vuelo.md` → «Outcome de la espera». Solo si
vence la cota propia mientras queda presupuesto se detiene como resultado incierto, sin degradar ni
destruir, y se presentan los recursos residuales. Este mismo orden rige para la consulta posterior.

Con disponibilidad acreditada se emite una sola solicitud para ese worker. En un lote se conserva
una muestra previa por worker, se asientan los envíos previstos y se reconcilian los efectivos con
`despacho.py --corrida` **antes de esperar a cualquiera**. Después del envío se consulta, con la
cadencia y cota publicadas y el mismo `wait_budget`, un efecto posterior ligado a esa solicitud y
al worker. Acreditan el comienzo una transición desde la muestra previa hacia ejecución, o hacia
terminación con evidencia atribuible al encargo actual. La repetición de un estado terminal solo
acredita si una marca monótona o única cambió tras el envío y la guía la atribuye al encargo actual.
Sin efecto acreditado no se entra en la espera ordinaria.

No acreditan ejecución el acuse de transporte, los bytes aceptados, `assignment_digest`, un estado
ocupado estático sin muestra previa, el estado terminal repetido sin marca nueva ni la desaparición
de una entrada pendiente. Si el conjunto expone una entrada pendiente separada y esta todavía
contiene el encargo, esa lectura positiva prueba **no envío**; una superficie inexistente o vacía no
prueba que se haya enviado. La integridad del contenido se comprueba además cuando una salida
derivada permite medirla, no como precondición universal de la espera ordinaria.

Solo la prueba positiva de no envío permite corregir esa entrada en el **mismo** worker y repetir
desde la acreditación de disponibilidad. Ante silencio, cota propia agotada con presupuesto
remanente, efecto ausente, ilegible, contradictorio o no atribuible, no se reenvía, no se abre otro
intento, no se degrada ni se destruye automáticamente. El sobre, el intento asentado y los recursos
se conservan. Toda detención con recursos de esta fase, incluida la previa a escribir, presenta al
usuario identidad y último estado observable del worker, muestras disponibles según la fase,
motivo exacto, sobre, intento asentado si existe y cada residual con su acción pendiente. Una causa
comprobada se declara conocida; si falta evidencia sobre lo ocurrido con el encargo, el resultado
es incierto. La corrida queda detenida hasta que el usuario decida investigar, cerrar tras cese
acreditado o relanzar solo con cese previo confirmado y las demás guardas vigentes. No se borra ni
reemplaza un intento asentado ni se lo marca cosechado sin adjudicar una salida real.

Esta regla se adopta en el siguiente despacho nuevo o retomado **antes de crear recursos**. Una
corrida que ya envió el encargo termina por la versión que cargó, aunque aún no haya entrado en
espera; no se migra ni acredita retroactivamente. Una retoma con recursos y envío no acreditado
adopta la regla nueva solo con prueba positiva de que no se envió. Si no puede distinguirlo, se
detiene sin reentregar y presenta los residuales para decisión humana como arriba. La matriz
histórica de adopción del transporte no se altera por esta adopción de la entrega.

#### Cuándo se puede degradar a la vía por línea de comandos

Una vía por plataforma que **ya creó recursos** y falló **no degrada por su cuenta**. Para degradar
hace falta una **señal positiva de terminación emitida por la plataforma**; ante su ausencia el
resultado se declara **incierto**, la degradación queda **vedada** y los residuales se enumeran. Es
el mismo criterio de cese positivo del carrier inválido, aplicado al fallo en curso: la nada no
acredita, y aquí acredita menos todavía, porque ya hay recursos creados de los que responder.

#### El universo del transporte, y qué pasa con una capacidad ausente

El universo normativo es **todo sitio que emite workers**, no la lista que el inventario declara. El
inventario es una **proyección auditable** de ese universo: su verde acredita que lo declarado
coincide con lo inventariado, y **nunca** que estén todos —su propia frontera admite que un despacho
sin marca le es invisible—. Por eso crear un punto de despacho nuevo incorpora **marca, declaración
de invariantes y fila de inventario** como parte del acto de crearlo, y no como un trámite posterior
que alguien recuerde.

**Una capacidad que un punto necesita es obligatoria a efectos del preflight.** Si falta, el
preflight falla cerrado y eso **no habilita emitir ese worker** por línea de comandos mientras haya
plataforma resuelta. La tentación es la contraria y por eso se escribe: degradar ese worker suelto
parece el remedio barato, y lo que produce es una corrida mitad por paneles y mitad por CLI en la que
ninguna de las dos mitades tiene el registro completa de la otra.

#### El bundle se carga del binario de la plataforma, no de una copia instalada

La guía que el flujo carga **la sirve el binario de la plataforma resuelta**, por el verbo que ella
publique para eso, y es la que corresponde a **la versión instalada**. Una copia en el harness del
conductor no sirve: envejece con cada release ajeno y nada la pone roja.

**Medido en este árbol, y no es una diferencia de redacción.** La copia instalada de la guía de
Herdr —de dos meses antes— difería de la que sirve el binario en **once tramos**: un grupo de
comandos **entero ausente**, dos códigos de error que la copia no nombra (`agent_not_ready` al
arrancar, `agent_blocked` al entregar el encargo), la advertencia de que un `timeout` **no prueba**
que el encargo no se entregó, y la semántica de dos estados del ciclo de vida cambiada. Un flujo que
operara con la copia le pediría a la plataforma cosas que su versión ya no hace y leería sus estados
con el significado anterior — sin un solo error, porque los dos textos son válidos por separado.

**Cuántas guías del terreno hay lo dice el binario, no una suposición del flujo.** No es una por
plataforma: Herdr publica **una**, y Orca **ocho**, de las cuales **dos** cubren este terreno — y ahí
se cargan **las dos del terreno** como conjunto, porque una capacidad puede estar en cualquiera. Por
eso la pregunta siguiente —cuál de ellas provee cada capacidad— solo se abre cuando son varias.

**Lo que la carga acredita, y lo que no.** El binario acredita que la guía corresponde a **su**
versión; **no** a la del servidor con el que habla. La propia guía de Herdr lo declara: cliente y
servidor pueden diferir tras una actualización, y un método ausente no autoriza a detener ni a
actualizar un servidor. Cargar resuelve qué **dice** la plataforma, no qué **acepta** el proceso que
la atiende — y eso último solo lo dice el intento, con su error.

#### Cuál de las guías del terreno provee cada capacidad

Este criterio se define en «El routing entre guías lo deciden las guías».

#### Los cinco destinos del preflight de capacidades

El preflight comprueba que las skills cargadas exponen lo que el flujo necesita, y **cada fallo tiene
su destino fijado**, que depende de dos cosas: si lo que falta es obligatorio, y si ya se crearon
recursos.

| Qué se observó | Destino |
|---|---|
| falta una capacidad **obligatoria**, incluida cualquiera de las cinco definiciones observables de entrega, o alguna es ilegible en el preflight, o el **perfil efectivo** reportado difiere del solicitado al crear una terminal | **falla cerrado antes de crear** ningún recurso; no degrada |
| falla **antes del primer recurso** y no falta ninguna capacidad obligatoria | **degrada** a la vía por línea de comandos |
| la identidad del worker no coincide con el despacho o se observa una condición que exige intervención humana | **se detiene por causa conocida** antes de crear más recursos; no degrada y presenta los ya creados |
| con recursos creados, alguna evidencia necesaria falta, es desconocida, ilegible, contradictoria o no atribuible, o vence la cota propia de disponibilidad o efecto sin acreditarlos mientras queda `wait_budget` | el resultado es **incierto**: **no degrada**, no destruye y presenta sobre, intento y residuales |
| falta la capacidad de **colocar** como se pidió, y solo ella | **continúa por la plataforma** con la colocación que aplique, y **declara la obtenida** o su estado incierto |

Cuando la evidencia contradictoria es la identidad del worker, prevalece la fila de causa conocida;
la fila incierta se aplica a las demás evidencias necesarias para decidir qué ocurrió con el encargo.

**La última fila se evalúa primero, porque es la única acotada a una capacidad concreta.** La
colocación no es obligatoria, así que sin esta precedencia caería en la segunda fila y ordenaría
degradar; y degradar un punto suelto por línea de comandos es justo lo que «La activación de la
plataforma es atómica» prohíbe. Su fundamento está del lado de la capacidad, en «La colocación se
pide como intención, y su resultado se declara»: lo que se pierde al no colocar es visibilidad, no
corrección, y la corrida sigue teniendo el registro completo de la plataforma.

**Las otras filas se distinguen por la obligación y por los recursos ya creados.** La falta de una
definición obligatoria prevalece sobre el fallo genérico previo al primer recurso: degradar sería
emitir ese worker por línea de comandos, que la plataforma resuelta prohíbe. Con recursos creados,
una causa conocida se nombra como tal; evidencia ausente o inválida no permite decidir qué ocurrió
con el encargo ni empezar de nuevo por otra vía: los procesos anteriores pueden seguir vivos, y
arrancar la vía por línea de comandos sobre el mismo worktree pondría dos corridas a escribir
encima. Si `wait_budget` vence antes o a la vez que la cota
propia de disponibilidad o de efecto, prevalece `corte_presupuesto` y la corrida **sigue activa**;
solo la cota propia vencida con presupuesto remanente toma la fila incierta con recursos. El sentido
de `corte_presupuesto` y la conservación del sobre viven en
`skills/cross-review/corridas-en-vuelo.md` → «Outcome de la espera».

#### La activación de la plataforma es atómica

Resuelta una plataforma para la fase, **ningún punto se escapa por línea de comandos**. Eso es lo que
compra que el reemplazo del productor del carrier sea **un acto único** y no una migración punto por
punto: mientras conviven puntos migrados y sin migrar, una misma corrida despacha mitad por paneles y
mitad por CLI, y **ninguna de las dos mitades tiene el registro de la otra** — que es exactamente la
propiedad que el ledger existe para dar.

**Lo que se paga, dicho antes de cobrarlo:** el valor de la plataforma no se ve hasta que los once
puntos están listos. Es deliberado. La alternativa —migrar de a uno y ver el beneficio antes— entrega
el beneficio parcial y **pierde la invariante entera**, que es lo único que este trabajo compra.

**Qué sigue igual después del cutover.** La oferta conserva sus **cinco puntos** y la pregunta
**independiente** de apertura de sesión: cambiar quién produce el carrier no cambia qué se le
muestra al usuario ni qué se le pregunta. Y la vía por línea de comandos **sigue existiendo y no se
retira**: es el destino de un entorno sin plataforma, de un usuario que rechaza la propuesta y de una
skill de plataforma que no carga.

#### Los dos momentos del instrumento

Los invariantes del punto se hacen cumplir en dos momentos, con los dos modos del instrumento de
`skills/cross-review/scripts/despacho.py`:

| Momento | Invocación | Qué contrasta |
|---|---|---|
| **antes de crear ningún recurso** | `despacho.py --preflight <raíz> <skill> <punto> <composición>` | la composición **prevista** contra la cardinalidad, las familias y la relación entre encargos que ese punto declara |
| **antes de esperar a ningún worker, y al consumir cada resultado** | `despacho.py --corrida <raíz> <skill> <punto> <sobre.json>` | la composición **efectiva** contra la prevista, **en las dos direcciones**, y por worker su familia, el digest de su encargo y su deadline propio |

Ninguno de los dos reemplaza al otro, y su frontera está declarada en la matriz de invocación del
propio instrumento: los dos leen lo que el conductor **declaró** y lo que el conductor **asentó**,
así que **ninguno detecta un despacho que nunca se asentó**. Esa dirección la cubre solo la
reconciliación contra la fuente efectiva de la plataforma.

**La composición que recibe el preflight lleva su `dominio`, y sin él el punto se detiene.** Tres de
las cuatro columnas no se pueden evaluar mirando solo a los workers previstos —`1-por-repo` necesita
cuántos repos tiene el reparto, `opuesta-al-conductor` necesita la familia del conductor,
`opuesta-al-autor-del-codigo` necesita el autor real y el inventario de familias resuelto,
`delta-sobre-el-anterior` necesita el encargo anterior—, así que la composición declara ese dato al
lado de `expected_workers[]`. La ausencia de un dato necesario para comprobar la composición **falla
cerrado** con `forma-no-reconocida`. Si no existe una familia opuesta en el inventario y el worker
previsto coincide con el autor, omitir `degradacion: same-family` también falla cerrado, pero con
`familia-invalida`: la familia se puede comprobar, aunque no se autorizó su uso degradado. Los campos
y qué celda exige cada uno: `skills/cross-review/corridas-en-vuelo.md` → «El dominio contra el que se
comprueba la composición».

---

#### La matriz de adopción: qué pasa con lo que ya existe

Retirar la invocación del adaptador no ocurre sobre un repositorio vacío: hay flujos abiertos,
registros escritos y corridas en vuelo. **Cada estado preexistente tiene su destino declarado acá**,
y ninguno queda librado a que el conductor lo resuelva en el momento.

| Estado cuando el cambio llega | Su destino |
|---|---|
| **flujo nuevo** | nace **sin transporte resuelto**. No hereda nada y elige por el checkpoint, como siempre |
| **registros ya escritos** | siguen siendo **legibles**, y los valores que nombran la vía anterior **no se retiran de ningún enum**: retirarlos volvería inválido un registro que describe correctamente lo que pasó |
| **corridas vivas** | **terminan por su vía**. No se migran, no se matan y no se convierten a mitad de corrida |
| **documento de retomado con una sola plataforma fijada** | se resuelve por su matriz y **continúa por ella** si sigue utilizable |
| **el archivo del adaptador** | dejó de invocarse en la primera fase y **se eliminó al cerrar la segunda**, que es el orden que esta fila fijaba |

**El orden de cutover no sobrescribe la evidencia de ninguna fase.** Lo que una fase midió sigue
siendo suyo aunque la siguiente corra por otra plataforma.

**Y el supuesto que sostuvo la última fila no era comprobable, así que se declara en vez de
afirmarse.** Eliminar el archivo al cerrar la segunda fase asumía que para entonces no quedaba
ninguna corrida de la vía anterior — y el estado de cada flujo es **local a su árbol de trabajo**,
así que ninguna fuente disponible podía responder por todos. No se convirtió en una guarda que
mienta: quedó escrito como supuesto, que es lo que es, y **sigue abierto**: una corrida de la vía
anterior que siga viva en otro árbol no tiene ya el archivo que la operaba.

### El bloque `transporte` y la retoma

Un flujo que corre sobre una plataforma de terminales agrega al frontmatter un bloque `transporte`:
es **la sede donde `sdd-flow` persiste el carrier de transporte**, y existe para una sola cosa, que una
sesión que retoma el flujo recupere la elección de esa fase **de ahí**, sin volver a detectar ni a ofrecer.

```yaml
transporte:
  fase: orca                  # la fase que este carrier gobierna; uno de otra fase NO es válido
  transport: plataforma       # plataforma | cli — `cli` es una ELECCIÓN registrada, no una ausencia
  plataforma: orca            # herdr | orca — la registrada, y la única identidad que la retoma consulta
  esquema: 2                  # versión de ESTE bloque; una que esta instalación no interpreta degrada
                              # es 2 porque el consentimiento al que apunta trae `colocacion_pedida`;
                              # un consentimiento sin ese campo se escribe con 1 y nada cambia
  consentimiento: .plans/<id>/transporte-consentimiento.json   # PUNTERO al consentimiento que autorizó la elección
  workspace: /ruta/absoluta/al/worktree-de-los-paneles
  corrida: .plans/<id>/transporte-corrida.jsonl   # ledger de la corrida; su propietario decide la adopción
```

Con `transport: cli` sobran `plataforma`, `workspace` y `corrida`: no hay paneles que registrar. Lo
que queda es el asiento de la elección y su consentimiento, que es de lo que se trata la rama (b).

El bloque **ausente** no es un error: es la señal de que el flujo nació antes de esta vía, y su
destino está en la primera fila de la matriz. **No es lo mismo que `transport: cli`**, y por eso el
campo existe: la ausencia dice que nadie eligió, y `cli` dice que alguien eligió la vía por línea de
comandos. Hasta que el campo existió las dos se escribían igual —sin bloque—, así que el registro no
podía distinguir una elección de un flujo que nunca la enfrentó. `consentimiento` y `corrida` son
**punteros**, no copias: el consentimiento se lee en su sede.

### El consentimiento, y por qué no alcanza una marca

El archivo de **consentimiento** que apunta el bloque no guarda una señal de que alguien dijo que sí: guarda **el texto exacto que se mostró** y su `digest`, y eso es lo que liga la elección a lo que el usuario vio. Una marca suelta pasa un chequeo de existencia sin poder decir **contra qué** se consintió, así que la oferta puede cambiar después y nadie se entera.

```json
{
  "corrida": ".plans/<id>/transporte-corrida.jsonl",
  "mostrado": "<el texto literal de los cinco puntos de la oferta>",
  "digest": "<sha256 de `mostrado`>",
  "momento": "2026-01-01T00:00:00+00:00",
  "alcance": {"workers": [{"rol": "w1", "worktree": "/ruta/absoluta", "colocacion_pedida": "adyacente-al-conductor"}, {"rol": "w2", "worktree": "/ruta/absoluta", "colocacion_pedida": "adyacente-al-conductor"}], "abrir_sesion": true}
}
```

**`alcance.workers[].colocacion_pedida` registra la intención de colocación**, y su lectura
es de tres valores.
Sus valores presentes son los dos del dominio cerrado —`adyacente-al-conductor` e `independiente`—;
si el campo está **ausente**, el consentimiento es **anterior a esta capacidad**, no se infiere ningún
valor y su lectura no falla. La lectura remite a la tabla trivaluada de `alcance.abrir_sesion`: el
campo presente es una decisión expresada y la ausencia una pregunta que nunca se hizo.

**Esa lectura cubre una sola dirección, y la otra la cierra el `esquema`.** Un consumidor que conoce
el campo leyendo un consentimiento que no lo trae queda cubierto por la ausencia. La dirección
contraria —un consumidor que **no** conoce el campo leyendo un consentimiento que **sí** lo trae— no
la cubre ninguna lectura del documento nuevo, porque ese consumidor nunca lo va a leer: lo único que
mira es el `esquema` del bloque. Entonces **un bloque cuyo consentimiento lleva `colocacion_pedida`
se escribe con `esquema: 2`**, y una instalación que no interprete ese esquema **degrada**, que es la
conducta que ese campo ya declara.

**Por qué acá sube y en el puntero a la corrida no, que es la asimetría que lo decide.** Aquel campo
no sube el esquema porque **su ausencia no autoriza**: un consumidor que lo ignore no concede nada y
falla del lado seguro. La colocación no se comporta así. Ignorar un `colocacion_pedida` **presente**
no es abstenerse: es aplicar el default de la plataforma, que puede **contradecir el texto que el
usuario consintió** — exactamente el defecto que esta capacidad viene a cerrar. Un campo cuya
presencia cambia el comportamiento no se puede compatibilizar con una lectura que el otro lado no
ejecuta.

**Lo que esto cuesta, dicho antes de cobrarlo.** Una instalación anterior degrada la retoma de una
corrida con colocación consentida, en vez de continuarla. Es el precio de que no pueda aplicar un
default contra lo consentido, y se paga solo en las corridas que efectivamente piden colocación: un
consentimiento sin el campo sigue en `esquema: 1` y ningún consumidor cambia.

**`alcance.abrir_sesion` registra la respuesta al punto de apertura, y su lectura es trivaluada.**
Existe porque abrir la sesión del conductor y correr los workers como paneles son **dos efectos
distintos** sobre la máquina de quien consiente, y una autorización inferida del texto de `mostrado`
no es verificable: hay que poder señalar el campo que la concede.

| Valor | Qué significa | Qué autoriza |
|---|---|---|
| `true` | el usuario aceptó el punto de apertura | abrir la sesión en el destino |
| `false` | el usuario lo rechazó explícitamente | nada; el flujo va a la clasificación del launcher |
| **ausente** | el consentimiento es **anterior a esta capacidad** y se dio sobre un texto que prometía apertura manual | nada |

**Solo el valor verdadero autoriza.** Distinguir el falso de la ausencia importa: el primero es una
decisión que el usuario tomó, y la segunda es una pregunta que nunca se le hizo. Ninguno de los dos
concede, pero solo el segundo obliga a decirle que su consentimiento es anterior a la capacidad.

**Las combinaciones son tres, y no cuatro.** La apertura **no se ofrece sin workers**: esa
combinación es la única que no sobrevive a una retoma mientras nada publique una señal de
workers, así que no se ofrece y no hay documento que la represente. Las tres que sí existen —y las
tres tienen documento, incluida la rechazada, que antes se representaba por su ausencia:

Vía consentida **con** apertura:

```json
{
  "corrida": ".plans/<id>/transporte-corrida.jsonl",
  "mostrado": "<los cinco puntos>", "digest": "<sha256>", "momento": "<ISO-8601>",
  "alcance": {"workers": [{"rol": "w1", "worktree": "/ruta/absoluta", "colocacion_pedida": "adyacente-al-conductor"}, {"rol": "w2", "worktree": "/ruta/absoluta", "colocacion_pedida": "adyacente-al-conductor"}], "abrir_sesion": true}
}
```

Vía consentida **sin** apertura — mismos campos de workers, la clave en falso:

```json
{
  "corrida": ".plans/<id>/transporte-corrida.jsonl",
  "mostrado": "<los cinco puntos>", "digest": "<sha256>", "momento": "<ISO-8601>",
  "alcance": {"workers": [{"rol": "w1", "worktree": "/ruta/absoluta", "colocacion_pedida": "adyacente-al-conductor"}, {"rol": "w2", "worktree": "/ruta/absoluta", "colocacion_pedida": "adyacente-al-conductor"}], "abrir_sesion": false}
}
```

Vía **rechazada** — el usuario enfrentó la oferta y eligió la vía por línea de comandos. **Eso deja
asiento**, que es la rama (b) del carrier: el bloque se escribe con `transport: cli` y su
consentimiento conserva el texto que se rechazó, porque lo que hay que poder reconstruir después es
**contra qué** se decidió:

```yaml
transporte:
  fase: orca
  transport: cli              # elección registrada: este lote corre por línea de comandos
  esquema: 1
  consentimiento: .plans/<id>/transporte-consentimiento.json
```

```json
{
  "mostrado": "<los cinco puntos>", "digest": "<sha256>", "momento": "<ISO-8601>",
  "alcance": {"workers": [], "abrir_sesion": false}
}
```

**`workers` vacío no es un lote de cero: es la declaración de que no hay lote**, y por eso el
documento existe igual. Un consentimiento ausente y uno con el lote vacío responden preguntas
distintas —«nadie preguntó» y «se preguntó y la respuesta fue que no»—, y la única que autoriza algo
es ninguna de las dos. Lo que cambia es qué puede hacer la retoma: ante la primera vuelve a ofrecer,
ante la segunda **no**, porque la elección ya está tomada para esta fase.

**El `esquema` del bloque no sube por este campo, y eso es deliberado.** Subirlo haría que toda
instalación que no interprete el esquema nuevo degrade la retoma a headless, porque un
esquema que no interpreta es su señal de degradación. La compatibilidad la da la **lectura
trivaluada**: un consentimiento viejo no trae la clave, y la ausencia no autoriza. **El criterio es
la ausencia, no la novedad del campo**: vale para todo campo cuya ausencia no conceda nada, y **no**
se extiende a uno cuya presencia cambie el comportamiento de quien lo ignora — ver
`alcance.workers[].colocacion_pedida`, que por eso sí sube el esquema. Por eso el
puntero a la corrida va **siempre presente** — al no existir la combinación sin workers, no hay
caso en que falte, y ningún consumidor del bloque cambia.

`alcance` es lo que la elección autorizó, y quien crea cada panel lo hace cumplir: un `cwd` que no
figura entre los worktrees declarados, un rol no enumerado o un worker que no está en el lote salen
con `consentimiento-invalido` o `consentimiento-agotado` y **no crean nada**. Es la diferencia entre
registrar la elección y **acotarla**: sin `alcance`, consentir una vez autorizaría cualquier cantidad
de paneles en cualquier directorio. Su forma es la del **lote real** —ver «El alcance es el lote
real, no un tope fijo»—, y un consentimiento sellado con la forma anterior se sigue leyendo: por qué
se conserva esa lectura está declarado ahí, en una sola sede.

Después del consentimiento, el ledger de la corrida registra por cada worker su rol y la colocación
obtenida con su evidencia, o el estado **incierto** con su motivo. Ese registro es posterior al
consentimiento y no modifica su texto ni su `digest`.

**La retoma no detecta, y eso no es lo mismo que no mirar el entorno.** Para **resolver el destino**
consulta la identidad de la plataforma **persistida** y de ninguna otra, reusando los cuatro estados
por identidad que el detector ya declara: acá hay una sola candidata, así que no hay nada que
**elegir**. El contraste contra las dos señales del entorno sí ocurre, y ocurre **antes** —es el paso
de discrepancia de «La retoma resuelve el transporte de la fase activa»—, con otro propósito:
comprobar si el entorno **contradice** al registro, no elegir una plataforma. Los dos pasos miran
cosas distintas y el orden entre ellos está fijado: primero se contrasta, y solo con el registro no
contradicho se resuelve su destino por la matriz de abajo.

| Lo que dice el documento de retomado | Identidad de la plataforma persistida | Destino |
|---|---|---|
| el bloque **no está** | no se consulta | headless, **sin oferta**: el flujo termina como empezó |
| el bloque está con `transport: cli` | no se consulta: no hay plataforma registrada que consultar | línea de comandos, **sin oferta** — es la rama (b), una elección ya tomada para esta fase |
| el bloque está con `transport: plataforma` | `ausente` o `inconsultable` — desapareció, o no se pudo preguntar | headless, **informando la causa** |
| el bloque está con `transport: plataforma` | `rancia` — hay identidad y no resuelve: es **otra** instalación que la registrada | headless, informando la causa |
| el bloque está con `transport: plataforma` y `resuelve`, y el propietario del ledger de corrida **no está vivo** | `resuelve` | headless, informando la causa |
| el bloque está con `transport: plataforma`, `resuelve` y el propietario vive | `resuelve` | continúa por la plataforma registrada, **sin volver a ofrecer** |

**Ninguna corrida viva se adopta ni se convierte.** Una corrida que el ledger declara en vuelo y cuyo
propietario no es esta sesión exige **consentimiento explícito** antes de tocarla; sin él degrada
igual que las demás causas, y nunca se convierte de transporte a mitad de camino.

**Por qué `inconsultable` degrada acá y no detiene, al revés que en la detección.** Ahí una consulta
fallida no descarta a la otra plataforma, porque hay **dos** candidatas y queda una por evaluar. En la
retoma hay **una sola**, así que no poder preguntar por ella no deja nada que evaluar, y el destino es
el que ya rige para todo lo que no resuelve: headless.

**Quién la resuelve: el conductor, leyendo el documento de retomado.** No hay un verbo que invocar —
la resolución es **leer el bloque `transporte` y aplicar esta matriz**, más, en las filas que lo
piden, preguntarle al terreno si esa plataforma sigue utilizable con el detector que esta misma sede
declara. Se escribe así, y no como un comando, porque **lo que hay acá es una lectura y una
adjudicación**, no un cómputo: un script que envolviera las dos no agregaría determinismo y sí una
sede más que mantener sincronizada con esta matriz.

**El resultado de la resolución tiene dos formas, y las dos son consumibles.** *Continúa por la
plataforma registrada* cuando el bloque la declara y el terreno la confirma; *degrada* en los otros
cuatro casos, y entonces la **causa** se declara —no la hay solo en la primera fila, donde no hubo
nada que degradar—. **Ninguna de las dos vuelve a ofrecer**: resuelto el transporte **de una fase que
lo tiene registrado**, la retoma no ofrece. Eso no alcanza a la fase activa **sin registro propio**,
que no entra en esta matriz: ahí no hay elección que recuperar y rige el ofrecimiento con
consentimiento nuevo.

**Adoptar una corrida en vuelo de otro propietario exige consentimiento explícito del usuario**, y es
la única forma de pasar esa guarda. El conductor **nunca** la concede por su cuenta.

### La retoma resuelve el transporte de la fase activa

Antes de enrutar y **antes de todo efecto**, la retoma identifica la fase de forma read-only y
resuelve el transporte **de esa fase**. Resuelto, carga las skills de esa plataforma como
**conjunto atómico**: el routing no continúa sin el conjunto completo. Un conjunto que no carga entero **es** el
caso de una skill de plataforma que no carga, y se resuelve por los criterios que ya lo gobiernan —
no tiene destino propio ni precedencia nueva.

**El transporte de una fase ya cerrada no se recupera para la activa.** Cuando la
fase activa no tiene registro propio, rige el ofrecimiento con **consentimiento nuevo**, aunque la
anterior haya corrido por paneles y el usuario ya haya consentido una vez. Es la contracara de persistir por fase: heredar
la vía sería la herencia por suposición que el carrier prohíbe, y además haría imposible el pedido
que originó todo esto —empezar con una plataforma y continuar con otra.

**Un bloque heredado sin `fase`** —escrito antes de que el campo existiera— **se proyecta a la fase
activa de forma declarada**, diciéndolo, y **sin borrar la evidencia de la fase anterior**. No se
reescribe el bloque viejo para que parezca de esta fase: lo que se pierde ahí no es un campo, es la
única prueba de por dónde corrió lo que ya ocurrió.

#### El override al retomar: dos ramas, y el orden no es negociable

Si el usuario indica un transporte **distinto** del registrado, las dos ramas se separan:

| Lo que indica | Qué se hace |
|---|---|
| **otra plataforma** | se valida **primero** su identidad; **solo si resuelve** se inicia el cese y la adopción. Si no resuelve, **se detiene** conservando intactos el registro, su consentimiento y los recursos anteriores, **sin liquidar nada** |
| la **vía por línea de comandos** | no hay identidad de plataforma que validar, y esa rama **no exige** esa validación; conserva íntegra la obligación de acreditar el cese de la vía anterior |

**Validar antes de liquidar, y no al revés.** El orden es lo que la fila compra: liquidar primero y
descubrir después que la plataforma indicada no resuelve deja al flujo sin la vía vieja —ya
liquidada— y sin la nueva —que nunca sirvió—, con los recursos destruidos y nada a lo que volver.
Validar **antes de liquidar** cuesta una consulta y hace que el peor caso sea no haber hecho nada.

**Las dos ramas exigen el cese positivo de los recursos de la vía anterior antes de adoptar la
nueva.** Si alguno sigue vivo, o el cese no es comprobable, el flujo **conserva esa vía para
liquidarla**, declara el resultado **incierto** con sus residuales y **no ejecuta ningún efecto en el
transporte nuevo**. **Una pausa no acredita cese:** que nadie haya mirado durante horas no es una
observación sobre los procesos, y tratarla como una deja workers vivos escribiendo sobre un worktree
que el transporte nuevo cree suyo.

En las dos, la elección queda registrada con su **propio consentimiento sellado** —la vía por línea
de comandos de forma distinguible de la ausencia de bloque, y sin cargar ninguna skill—, y en la
primera son las skills del transporte **nuevo** las que se cargan.

#### Discrepancia entre el registro y el entorno

Cuando el transporte registrado **no coincide** con lo que las señales del entorno resuelven, y el
usuario no declara nada, el flujo **no continúa en silencio** por el registrado: la discrepancia
tiene un destino declarado y observable.

**Se detiene solo en las dos celdas donde la discrepancia es real**, antes de cargar ninguna skill y
antes de crear ningún recurso:

| Lo que resuelven las señales | Destino |
|---|---|
| **las dos** resuelven | **se detiene**: no hay observable que diga cuál es el anfitrión |
| **una sola** resuelve, y **difiere** del registrado | **se detiene**: el entorno contradice al registro |
| una señal **confirma** al registrado | **continúa**, aunque la otra no resuelva o sea inconsultable |
| **ninguna** resuelve | rige la precedencia ya aprobada hacia la vía por línea de comandos, salvo que la veda por recursos o residuales lo impida |

**Por qué solo esas dos, y no toda diferencia.** Una señal que no resuelve no contradice nada: no
saber si Herdr está vivo no es evidencia de que el registro de Orca sea falso. Detenerse ahí
convertiría cada retoma en un ambiente sin la otra plataforma en un checkpoint, que es el costo sin
la propiedad — la discrepancia es real cuando **hay** una observación que se opone al registro, no
cuando falta una que lo confirme.

**Al detenerse, presenta lo observado con la evidencia de cada señal, y solo una decisión del usuario
lo resuelve.** El registro previo y su consentimiento **no desempatan por sí solos**: son justamente
lo que está en duda. La identidad elegida vuelve a pasar la validación **antes de cada efecto**, y
una identidad ausente, rancia o inconsultable **no resuelve** la discrepancia.

**La respuesta obtenida se trata como declaración actual**, y se bifurca: si **confirma** al
registrado, se valida su identidad, se conservan el registro y su consentimiento y continúa la carga
del registrado; solo una plataforma **distinta** o la vía por línea de comandos entra por el criterio
del override de arriba. Una declaración explícita del usuario tiene precedencia sobre esta matriz y
se bifurca igual: confirmar no es lo mismo que elegir otra cosa, y solo lo segundo liquida algo.

## Revisión final de diff

**Corre siempre**, dentro del gate de revisión manual previo al commit. No reemplaza `verify`: revisa
el **diff completo** ya verificado. No tiene modo de apagado: el flujo que no la corre no cierra.

**Quién lo hace.** Un agente fresco de la **familia opuesta a la que escribió el código** — la del
autor real del diff, no la del conductor, que pueden no ser la misma: si implementó un worker Codex,
revisa Claude; si implementó un conductor Codex, revisa Claude igual. Se descubre por capacidad, sin
asumir el nombre de la tool (ver "Matriz de detección por capacidad").

**Degradación, cuando la opuesta no está.** `cross_model.families` admite declarar una sola familia
cuando es la única instalada, así que exigir la opuesta sin salida bloquearía el flujo antes del
commit en una configuración válida. Sin ella revisa un agente **fresco de la misma familia**, y el
conductor **lo declara en el gate**: *"revisó same-family: contexto fresco sí, diversidad de familia
no"*. La degradación se nombra siempre; un silencio acá convierte la señal débil en una fuerte.

**Qué recibe.** El **diff completo del flujo** —no el de una task—, las rutas de los artefactos, que
está autorizado a abrir, y **la lista de archivos que el plan nombró**: el contraste entre esa lista
y `git diff --name-only` es lo que hace observable un desborde de alcance.

```markdown
Trabaja en modo SOLO LECTURA sobre el repo <working_dir>. No edites nada.
Revisa el diff completo del flujo contra:
- `.plans/<id>/spec.md` o `## Spec` embebido en `plan.md`
- `.plans/<id>/plan.md`, incluida su lista de archivos previstos
- `.plans/<id>/tasks.md` si existe
- principios del repo (`AGENTS.md`/`CLAUDE.md`/`CONTRIBUTING.md`) si existen

Evalúa, EN ESTE ORDEN:
- SCOPE — ¿**sobra** algo? Código que ningún AC pide, validaciones para casos que nadie
  pidió, abstracciones de un solo uso, comentarios que repiten lo que el código dice,
  "mejoras" o refactors de código adyacente que no estaba roto, defectos preexistentes
  arreglados de paso. Y archivos tocados que el plan no nombra.
- SPEC — ¿el diff cumple los AC, y los cambios fuera de AC están declarados como Extras?
- QUALITY — ¿sigue patrones del repo, sin dead code, placeholders ni deuda obvia?

Tu mensaje final debe ser EXACTAMENTE este reporte (sin prosa extra):
SCOPE: ok | fail
SPEC: ok | fail | warn
QUALITY: ok | fail
FINDINGS: <una línea por problema; vacío si todo ok>
NOTES: <no verificable desde el diff / recomendaciones no bloqueantes>
```

**`SCOPE` va primero a propósito.** Vivía dentro de `QUALITY`, compitiendo con dead code y deuda, y
es el eje que más se pasa por alto porque un agente que hizo de más produce código que se ve
correcto: está bien escrito, funciona, y solo falla la pregunta de quién lo pidió. Como eje propio
tiene su propia línea de veredicto y no se puede cerrar sin nombrarlo.

**Cómo lee el conductor el reporte.** Los tres `ok` → el gate sigue su curso normal. `warn` no
bloquea, pero **tampoco se cierra en silencio**: el conductor resuelve lo señalado, o lo declara,
antes de commitear. Los `fail` no pesan igual, y la diferencia no es de severidad sino de qué hay
detrás de cada eje:

| | Qué obliga | Por qué |
|---|---|---|
| `SPEC: fail` | **bloquea el commit.** Se resuelve antes de seguir | contradice un `verify` en verde: dos lecturas del mismo hecho no pueden convivir. Una de las dos está mal y hay que averiguar cuál |
| `SCOPE: fail` | **no bloquea, pero cada hallazgo se resuelve:** se saca del diff, o entra como `E-n` en `## Extras` del plan con qué se dejó y por qué | es la misma puerta que ya gobierna los Extras — nada que se decida dejar pasar se cierra sin rastro— y la conducta no cambia según quién lo señale |
| `QUALITY: fail` | **no bloquea, pero no se cierra en silencio:** se arregla, o se declara como `E-n` | no toca ningún AC, así que la ley fundamental —ningún commit con un AC en rojo— no lo alcanza. Pero un finding que se descarta sin rastro convierte al revisor en decorativo |

El asimétrico es deliberado: a un revisor cuyo `ok` no acredita todo tampoco se le da veto sobre el
commit. Lo que sí se le exige es que su hallazgo deje rastro.

> **Cuánto vale ese `ok`, y por qué depende de quién revisó.** Un **hallazgo** vale igual en los dos
> casos: si encuentra un bug real, el bug es real sin importar de qué familia venga. Lo que cambia es
> el valor del **acuerdo**:
>
> | Revisor | Qué acredita su `ok` |
> |---|---|
> | familia **opuesta** | contexto fresco **y** diversidad de familia: no comparte los puntos ciegos de quien escribió el código. Es la señal más fuerte que da este paso |
> | **misma** familia (degradación) | solo contexto fresco: no vio escribirse el código, así que no arrastra las justificaciones de quien lo escribió. Dos agentes de la misma familia coinciden en los mismos puntos ciegos, y esa coincidencia produce una señal falsamente tranquilizadora |
>
> Por eso la degradación **se declara**: sin esa línea, los dos casos se leen igual en el gate.
>
> **Y los tres ejes no tienen la misma red de contención.** `SPEC` tiene una segunda: `verify`
> recorre los AC al final con evidencia fresca, así que un `SPEC: ok` equivocado se caza después.
> `SCOPE` y `QUALITY` **no tienen ninguna**, y en la rama degradada son la señal más débil del flujo:
> tratarlas como garantía es exactamente el error que este bloque existe para impedir.

Si no hay capacidad para despachar ningún reviewer fresco, el conductor hace la revisión liviana, la
declara como tal en el gate, y sigue. Si hay findings, volver a `implement` o a `plan`/`specify`
según el tipo de gap; no abrir otro gate nuevo.

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
