# Inventario MCP — lectura vs escritura

> Insumo de `claude-readonly.settings.json` / `claude-write.settings.json` /
> `codex-readonly.config.toml` / `codex-write.config.toml`. Verificado contra Codex CLI 0.144.6
> y Claude Code 2.1.214 el 2026-07-19 (`codex mcp list --json`, `codex mcp get <id> --json`,
> `claude mcp list`, e inspección directa de `$CODEX_HOME/config.toml`).

## Regla fail-closed (obligatoria)

**Cualquier servidor, tool, `apps.<id>` o plugin que NO aparezca en este inventario bloquea el
despacho.** No hay "modo permisivo por defecto": un secundario (Claude o Codex) lanzado por
`cross-model-orca` solo puede usar lo que esta tabla clasifica explícitamente como lectura para
el rol read-only, o lo que las tablas de escritura habilitan a propósito para el rol write. Un
servidor nuevo que aparezca en el entorno (agregado por el usuario, por un plugin, o por
`mcp add`) **no** se habilita solo porque exista: hay que agregarlo a este archivo primero,
clasificar sus tools, y recién después reflejarlo en los perfiles de `claude-*.settings.json` /
`codex-*.config.toml`.

## Namespacing real de las tools MCP en Claude (crítico para `deny`/`ask`)

**El nombre literal de una tool MCP en `permissions.deny`/`permissions.ask` de Claude Code
depende de cómo esté instalado el servidor, no solo de su nombre "de servidor" tal como aparece
en `codex mcp list` o en la documentación del MCP.** Dos convenciones reales, confirmadas en este
entorno:

- **Servidor directo** (agregado con `claude mcp add`/`.mcp.json`, sin pasar por un
  marketplace de plugins): `mcp__<servidor>__<tool>`. Ejemplo confirmado en este entorno:
  `pencil` está instalado como servidor directo → `mcp__pencil__get_editor_state`,
  `mcp__pencil__batch_design`, etc.
- **Servidor instalado como plugin de marketplace**: `mcp__plugin_<paquete>_<servidor>__<tool>`.
  Ejemplo confirmado en este entorno: `engram` aparece en `claude mcp list` como
  `plugin:engram:engram` (no como servidor directo) → el nombre real de sus tools es
  `mcp__plugin_engram_engram__mem_save`, `mcp__plugin_engram_engram__mem_update`, etc. — **no**
  `mcp__engram__mem_save`. Un nombre con el prefijo equivocado en `deny`/`ask` **no matchea
  ninguna tool real**, y la escritura que se creía bloqueada queda sin bloquear (fail-open
  silencioso, exactamente lo que la prohibición de wildcards de servidor busca evitar).

Un mismo servidor puede incluso aparecer **instalado de las dos formas a la vez** en un mismo
entorno (`context7` apareció tanto como `plugin:context7:context7` como servidor directo
`context7` en `claude mcp list` de esta sesión) — cada instalación tiene su propio namespace de
tools, y ambas necesitan su propia entrada en `deny`/`ask` si las dos están activas.

**Por eso el namespacing no puede quedar fijo en este documento como una verdad universal: es
una propiedad de CÓMO está instalado el servidor en el entorno donde se va a despachar, no del
servidor en sí.** `atlassian`, en particular, no fue verificable en el entorno donde se escribió
este inventario (no aparece en `claude mcp list` a nivel de proyecto) — sus tools quedan
enumeradas con la convención de servidor directo (`mcp__atlassian__<tool>`) **sin confirmar**;
si en el entorno real de despacho `atlassian` estuviera instalado como plugin, ese nombre no
matchea y hay que corregirlo antes de lanzar.

**Consecuencia obligatoria (preflight fail-closed):** antes de despachar un secundario Claude,
quien invoque `cross-model-orca` **debe confirmar el namespacing real de cada tool inventariada
contra el entorno de activación** (p. ej. con `claude mcp list` y, si hace falta, inspeccionando
cómo se resuelven las tools MCP disponibles en una sesión de prueba) — **no asumir** que el
nombre que aparece en este archivo matchea tal cual. Si una tool enumerada en `deny`/`ask` no
matchea ninguna tool real del entorno (porque cambió el namespacing, el servidor se reinstaló
distinto, o el nombre nunca se verificó), el preflight **bloquea el despacho** en vez de lanzar
con una regla que no surte efecto. Esto traslada la fragilidad del nombre literal — inevitable en
un archivo de config estático — a un chequeo de arranque, que es la red de seguridad correcta.

## Servidores "conocidos" — inventario a nivel de tool

Estos cuatro son los que consume el flujo `cross-model-orca` (contexto de Jira/Confluence,
documentación de librerías, memoria persistente, diseño). Confirmados presentes en este entorno
vía `codex mcp list --json` (nombre real entre paréntesis cuando difiere del genérico) y/o
`claude mcp list`.

### `atlassian` (real: `atlassian-mcp-server` en Codex; conector `claude.ai`/MCP remoto en Claude)

| Tool                       | Clasificación | Notas |
|-----------------------------|---------------|-------|
| `getJiraIssue`              | Lectura       | |
| `searchJiraIssuesUsingJql`  | Lectura       | |
| `getConfluencePage`         | Lectura       | |
| `createJiraIssue`           | **Escritura** | |
| `addCommentToJiraIssue`     | **Escritura** | |
| `transitionJiraIssue`       | **Escritura** | |
| `addWorklogToJiraIssue`     | **Escritura** | |

Presente y `enabled=true` en este `CODEX_HOME` (transporte `streamable_http`,
`url = "https://mcp.atlassian.com/v1/mcp/authv2"`, auth OAuth — sin secreto estático en el
config). Coincide con la política ya vigente en `CLAUDE.md` del usuario para Atlassian (lectura
libre, escritura solo con pedido explícito y confirmación).

### `context7`

| Tool                | Clasificación | Notas |
|---------------------|---------------|-------|
| `query-docs`        | Lectura       | |
| `resolve-library-id`| Lectura       | |

No tiene tools de escritura conocidas. Presente en este entorno (Codex: `mcp_servers.context7`,
transporte `streamable_http` con `CONTEXT7_API_KEY` en `http_headers` — **secreto real en el
config**, por eso los perfiles de esta task no reproducen su transporte: al no tener tools de
escritura, no necesita restricción y se deja fuera de los TOML de perfil para no tener que
reinyectar la API key en un archivo versionado).

### `engram` (memoria persistente)

Nombres de tool reales observados en este entorno (Codex: `mcp_servers.engram`, comando local
`engram mcp --tools=agent`; Claude: plugin `engram`).

| Tool                    | Clasificación | Notas |
|--------------------------|---------------|-------|
| `mem_search`             | Lectura       | |
| `mem_context`            | Lectura       | |
| `mem_get_observation`    | Lectura       | |
| `mem_stats`              | Lectura       | |
| `mem_timeline`           | Lectura       | |
| `mem_current_project`    | Lectura       | |
| `mem_suggest_topic_key`  | Lectura       | cómputo/sugerencia, no persiste |
| `mem_doctor`             | Lectura       | diagnóstico |
| `mem_compare`            | Lectura       | compara dos memorias, no muta |
| `mem_review`             | **Escritura** | ambiguo: puede marcar candidatos como revisados/resueltos; clasificado como escritura por precaución fail-closed |
| `mem_judge`              | **Escritura** | resuelve conflictos de memoria (persiste una decisión) |
| `mem_save`               | **Escritura** | |
| `mem_save_prompt`        | **Escritura** | |
| `mem_update`             | **Escritura** | |
| `mem_delete`             | **Escritura** | |
| `mem_pin`                | **Escritura** | |
| `mem_unpin`              | **Escritura** | |
| `mem_merge_projects`     | **Escritura** | |
| `mem_session_start`      | **Escritura** | |
| `mem_session_end`        | **Escritura** | |
| `mem_capture_passive`    | **Escritura** | |

Nota de alcance: ningún rol de `cross-model-orca` (ni read-only ni write) necesita que el
secundario escriba en la memoria personal del usuario — es un flujo de dispatch entre modelos,
no el asistente principal. Por eso **todas** las tools de escritura de `engram` están
deshabilitadas en **ambos** perfiles (`codex-readonly.config.toml` y `codex-write.config.toml`);
solo las de lectura quedan disponibles como contexto.

### `pencil` (diseño — `.pen`)

Nombres de tool reales observados en este entorno (Codex: `mcp_servers.pencil`, comando local
`.../Pencil.app/.../mcp-server-darwin-arm64 --app desktop --agent codexCLI`; Claude: MCP
`pencil`).

| Tool                            | Clasificación | Notas |
|-----------------------------------|---------------|-------|
| `get_editor_state`                | Lectura       | |
| `get_guidelines`                  | Lectura       | |
| `batch_get`                       | Lectura       | |
| `snapshot_layout`                 | Lectura       | |
| `get_screenshot`                  | Lectura       | |
| `get_variables`                   | Lectura       | |
| `find_empty_space_on_canvas`      | Lectura       | |
| `search_all_unique_properties`    | Lectura       | |
| `open_document`                   | **Escritura** | abre/carga un documento para edición: cambia el estado del editor activo; tratado como escritura por precaución |
| `batch_design`                    | **Escritura** | |
| `set_variables`                   | **Escritura** | operación batch de alto riesgo — ver advertencia en `CLAUDE.md` del usuario |
| `replace_all_matching_properties` | **Escritura** | operación batch de alto riesgo — ver advertencia en `CLAUDE.md` del usuario |
| `export_nodes`                    | **Escritura** | efecto lateral de escritura en filesystem |

Nota de alcance: igual que `engram`, ningún rol de `cross-model-orca` necesita que el secundario
edite diseños de Pencil. Ambos perfiles deshabilitan el servidor completo
(`mcp_servers.pencil.enabled = false` / omitido de `permissions.allow` del lado Claude) en vez de
abrir solo las tools de lectura — simplifica el perfil y evita cargar un servidor sin necesidad
real en este flujo.

## Otros servidores detectados en el entorno (`codex mcp list --json`, 2026-07-19)

Servidores presentes en este `CODEX_HOME` que **no** son parte del set "conocido" de
`cross-model-orca`. Para los dos primeros (`chrome-devtools`, `playwright`) sí se pudo verificar
el nombre real de cada tool (coincide con el listado de tools MCP disponibles en esta misma
sesión); para el resto **no se verificó a nivel de tool en esta task** — quedan inventariados
solo a nivel de servidor, con clasificación de propósito general, y **bloqueados por la regla
fail-closed** en ambos perfiles hasta que alguien complete su inventario de tools.

### `chrome-devtools` — inventariado a nivel de tool, pero **fuera de alcance** de este flujo

Tools reales: `click`, `close_page`, `drag`, `emulate`, `evaluate_script`, `fill`, `fill_form`,
`get_console_message`, `get_network_request`, `handle_dialog`, `hover`, `lighthouse_audit`,
`list_console_messages`, `list_network_requests`, `list_pages`, `navigate_page`, `new_page`,
`performance_analyze_insight`, `performance_start_trace`, `performance_stop_trace`, `press_key`,
`resize_page`, `select_page`, `take_heapsnapshot`, `take_screenshot`, `take_snapshot`,
`type_text`, `upload_file`, `wait_for`. La mayoría son lectura (inspección/lectura de la página),
pero `click`, `fill`, `fill_form`, `drag`, `press_key`, `type_text`, `handle_dialog`,
`upload_file`, `navigate_page`, `emulate` y `evaluate_script` mutan el estado de la página o
ejecutan JS arbitrario → escritura. Como `cross-model-orca` no necesita automatizar navegador,
el servidor completo queda **deshabilitado** en ambos perfiles.

### `playwright` — mismo caso que `chrome-devtools`

Tools reales: `browser_click`, `browser_close`, `browser_console_messages`, `browser_drag`,
`browser_drop`, `browser_evaluate`, `browser_file_upload`, `browser_fill_form`, `browser_find`,
`browser_handle_dialog`, `browser_hover`, `browser_navigate`, `browser_navigate_back`,
`browser_network_request`, `browser_network_requests`, `browser_press_key`, `browser_resize`,
`browser_run_code_unsafe`, `browser_select_option`, `browser_snapshot`, `browser_tabs`,
`browser_take_screenshot`, `browser_type`, `browser_wait_for`. Mismo criterio: servidor completo
**deshabilitado** en ambos perfiles (fuera de alcance, no vale la pena diferenciar tool por tool).

### Servidores sin inventario de tools verificado en esta task (bloqueados por fail-closed)

| Servidor           | Estado en este entorno | Propósito aparente (sin verificar tools) | Perfiles |
|---------------------|------------------------|-------------------------------------------|----------|
| `bitbucket`         | `enabled=true`         | MCP de Bitbucket (`@aashari/mcp-server-atlassian-bitbucket`); expone lectura/escritura de PRs y repos | deshabilitado en ambos |
| `angular-cli`       | `enabled=true`         | MCP oficial de `@angular/cli`; puede generar/modificar código | deshabilitado en ambos |
| `node_repl`         | `enabled=true`         | REPL de Node con acceso a control de navegador/escritorio (bundle de ChatGPT desktop) | deshabilitado en ambos |
| `sites-design-picker` | `enabled=true`       | MCP bundleado por el plugin `sites@openai-bundled` | deshabilitado en ambos |
| `api-mcp-front`     | `enabled=false` (ya deshabilitado en la config base) | Proxy HTTP local con header de Figma | deshabilitado en ambos |
| `sonarqube`         | `enabled=false` (ya deshabilitado en la config base) | MCP de SonarQube (calidad de código) | deshabilitado en ambos |
| `figma`             | `enabled=false` (ya deshabilitado en la config base) | MCP de Figma | deshabilitado en ambos |
| `computer-use`      | `enabled=false` (ya deshabilitado en la config base) | Control de UI de escritorio | deshabilitado en ambos |

## `apps.*`

No se encontraron entradas `[apps.<id>]` en `$CODEX_HOME/config.toml` de este entorno (solo el
flag maestro `features.apps`, que en este entorno está en `true`). La regla fail-closed de esta
task se aplica igual: **`features.apps = false` en ambos perfiles**, sin depender de
`apps._default.enabled` ni de negar apps una por una — un `apps.<id>.enabled = true` heredado del
usuario sobrescribiría un `apps._default.enabled=false`, por eso el corte tiene que ser el flag
de feature completo. Si en el futuro aparece una `[apps.<id>]` real, queda bloqueada igual por
esta regla mientras no se agregue a este inventario.

## `plugins.*` y `plugins.*.mcp_servers.*`

En este entorno, los plugins de Codex (`documents@openai-primary-runtime`,
`spreadsheets@openai-primary-runtime`, `presentations@openai-primary-runtime`,
`superpowers@openai-curated`, `atlassian-rovo@openai-curated`, `figma@openai-curated`,
`pdf@openai-primary-runtime`, `chrome@openai-bundled`, `template-creator@openai-primary-runtime`,
`sites@openai-bundled`, `visualize@openai-bundled`, `browser@openai-bundled`) están todos
`enabled = true` en la config base. **Hallazgo:** no existe un namespace separado
`plugins.<id>.mcp_servers.<name>` en la práctica — el único MCP server que trae un plugin
(`sites-design-picker`, del plugin `sites@openai-bundled`) aparece como una entrada plana más en
`mcp_servers.<id>` (confirmado por `cwd` apuntando al directorio de caché del plugin), no anidado
bajo `plugins.sites.mcp_servers.sites-design-picker`. Si una versión futura de Codex introdujera
ese namespace anidado, la misma regla fail-closed aplica.

Ninguno de estos plugins es necesario para el rol del secundario en `cross-model-orca` (no
interactúa con documentos de oficina, PDFs, ni automatiza navegador). Los dos perfiles
(`codex-readonly.config.toml` / `codex-write.config.toml`) los deshabilitan explícitamente uno
por uno (`[plugins."<id>@<marketplace>"] enabled = false`) en vez de confiar en que queden
implícitamente fuera — así un cambio futuro en la config base (un plugin nuevo habilitado por el
usuario) no se filtra silenciosamente al secundario.

## Validación de este inventario contra el CLI real

- `codex mcp list --json` (2026-07-19): confirma presencia/`enabled` de `atlassian-mcp-server`,
  `context7`, `engram`, `pencil`, `chrome-devtools`, `playwright`, `bitbucket`, `angular-cli`,
  `node_repl`, `sites-design-picker`, y los deshabilitados `figma`, `sonarqube`, `api-mcp-front`,
  `computer-use`.
- `codex mcp get <id> --json` (para `atlassian-mcp-server`, `engram`): confirma que
  `enabled_tools`/`disabled_tools` son campos reales del schema (aparecen como `null` cuando no
  se configuran), consistente con el "Contexto verificado" del brief.
- `codex features list` (2026-07-19): confirma que `apps` es un feature real, stage `stable`,
  efectivo `true` en este entorno — habilitado por defecto, hay que apagarlo a propósito.
- `claude mcp list`: confirma el set de servidores configurados del lado Claude en este entorno
  (`context7` ×2, Gmail, Google Calendar, Google Drive, `chrome-devtools`, `engram`, `pencil`,
  `idea` [sin conectar], `playwright`) — no expone `atlassian`/`bitbucket` a nivel global en este
  checkout (puede estar scopeado a nivel de proyecto/organización; no bloquea esta task porque la
  clasificación de tools ya viene verificada del brief).
- Nombres de tool de `engram`/`pencil`/`chrome-devtools`/`playwright`: verificados contra el
  listado real de tools MCP disponibles en la sesión que ejecutó esta task (mismo binario de
  cada servidor, independientemente de si lo consume Claude o Codex).
- Nombres de tool de `atlassian` (Jira/Confluence): tomados tal cual del "Contexto verificado"
  del brief (ya confirmados en una fase de spikes previa); no se re-verificaron en esta task
  porque el conector no está accesible a nivel de proyecto en esta sesión (ver punto anterior).
