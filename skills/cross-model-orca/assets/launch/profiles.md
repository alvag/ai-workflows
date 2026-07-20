# Perfiles de lanzamiento — matriz familia × rol × modo

> Verificado contra Codex CLI 0.144.6 y Claude Code 2.1.214 el 2026-07-19, en un entorno donde
> `CODEX_HOME` apunta al runtime de Orca (`~/Library/Application Support/orca/codex-runtime-home/home`,
> **no** `~/.codex`). Los comandos usan rutas de ejemplo de ese entorno; ajusta `CODEX_HOME` /
> rutas de settings a tu checkout.

## Tres capas de control

1. **Toolset/sandbox de la CLI** (qué puede tocar el proceso): `--tools "Read,Grep,Glob"` en
   Claude (cierra Bash → read-only duro, inmune a un `allow` heredado); `-s read-only` /
   `-s workspace-write` en Codex.
2. **Approval policy** (qué necesita aprobación humana): `--permission-mode` en Claude; `-a` en
   Codex.
3. **Config de MCP + hooks** (qué tools remotas y qué automatizaciones locales están
   disponibles): en el **default atendido**, MCP se controla por **vigilancia manual** (el humano
   aprueba/rechaza en la TUI; no hay allowlist ni denylist que mantener), más `--settings <archivo>`
   (`disableAllHooks`); en Codex, `-c features.apps=false --disable hooks` inline (sin perfil que
   copiar) + vigilancia manual vía `-a untrusted`. Para el caso **desatendido**, un gate declarativo
   opcional (Claude `--strict-mcp-config`; Codex `-p <perfil>` con MCP server-scoped), ver abajo. Ver
   `mcp-inventory.md` para el modelo completo.

### MCP: vigilancia manual (default) y endurecimiento opcional

`--tools "Read,Grep,Glob"` acota **solo los built-ins** (por eso excluir Bash da read-only duro),
pero **no gobierna las tools MCP** (`claude --help`: *"from the built-in set"*). En el default
**atendido** eso no es un problema: el gate de MCP es la **vigilancia manual** (P4) — el humano que
mira la corrida aprueba o rechaza cualquier acción sensible en la TUI. No hay inventario ni
allowlist que configurar para instalar la skill.

Para una corrida **desatendida** (nadie mira la TUI, no hay gate humano), existe un gate
declarativo **opcional**: `--strict-mcp-config --mcp-config claude-readonly.mcp.json`, que da vuelta
el default de MCP a *deny-all* — la sesión ve **solo** los servidores del allowlist (vacío = cero
MCP). Verificado en vivo (2026-07-19, Claude 2.1.214): sin el flag, la sesión enumera tools MCP del
entorno; con `--strict-mcp-config` + allowlist vacío responde **`CERO-MCP`**. Detalle y el patrón
para permitir un servidor de lectura en `mcp-inventory.md`.

> **Gotcha de orden de flags:** `--tools <tools...>` y `--mcp-config <configs...>` son
> **variádicos** — se comen los tokens siguientes hasta el próximo flag. Cuando uses el flag
> opcional, ponlo **seguido de otro flag** (nunca justo antes del `<prompt>` posicional, o el
> prompt se pierde como "otra tool/config"). En la matriz de abajo el `<prompt>` va último, tras
> `--session-id` (no variádico).

## MCP en Codex: vigilancia manual (default) + perfil opcional (desatendido)

Igual que en Claude, el **default atendido** de Codex read-only no restringe MCP por config: el
secundario ve los MCP del entorno y **el humano es el gate** — con `-a untrusted`, una acción no
confiable escala a aprobación en la TUI. Las garantías cero-config que sí valen: `-s read-only`
(sandbox), `--disable hooks`, y **`-c features.apps=false`** (apaga la superficie de Apps; se setea
**inline**, sin perfil — verificado válido bajo `--strict-config`). **No hace falta copiar ningún
perfil a `$CODEX_HOME` para el default.**

Para el caso **desatendido** (nadie aprueba en la TUI) existe un perfil **opcional** con
restricciones MCP server-scoped (`codex-readonly.config.toml`). `-p <nombre>` **no** acepta una
ruta: busca `$CODEX_HOME/<nombre>.config.toml`, así que hay que copiarlo primero. El perfil de
**write** (cross-implement, Fase 5) sí se instala del mismo modo.

**POSIX (bash/zsh):**
```bash
cp skills/cross-model-orca/assets/launch/codex-readonly.config.toml \
   "$CODEX_HOME/cmo-readonly.config.toml"   # solo para el endurecimiento desatendido
cp skills/cross-model-orca/assets/launch/codex-write.config.toml \
   "$CODEX_HOME/cmo-write.config.toml"      # rol write (Fase 5)
```

**PowerShell:**
```powershell
Copy-Item skills/cross-model-orca/assets/launch/codex-readonly.config.toml `
  "$env:CODEX_HOME/cmo-readonly.config.toml"   # solo para el endurecimiento desatendido
Copy-Item skills/cross-model-orca/assets/launch/codex-write.config.toml `
  "$env:CODEX_HOME/cmo-write.config.toml"      # rol write (Fase 5)
```

> Un perfil inexistente en `$CODEX_HOME` se **ignora silenciosamente** (confirmado: `-p
> <nombre-inexistente>` no produce error, corre con la config base tal cual) — si usas el perfil
> opcional, verifica que el `cp`/`Copy-Item` haya corrido antes de asumir que las restricciones
> están activas.

Del lado Claude, `--settings <archivo>` sí acepta una ruta directa — no hace falta instalar nada
primero.

## Domesticación del arranque

- **Auto-update — Claude:** configura `DISABLE_AUTOUPDATER=1` en el entorno del proceso (variable
  real, confirmada en el binario de Claude Code 2.1.214) para que no intente actualizarse solo
  en medio de una sesión desatendida.
- **Auto-update — Codex:** `codex update` es un subcomando manual (no se dispara solo al
  invocar `codex`/`codex exec`); no encontramos una bandera ni variable de entorno de
  "no actualizar" propia de la CLI porque no hace falta — no hay nada que domesticar aquí.
- **MCP con auth pendiente:** en este entorno, `context7` (y cualquier servidor OAuth sin sesión
  vigente) emite `ERROR rmcp::transport::worker: ... Auth(AuthorizationRequired)` al arrancar,
  pero **no cuelga la ejecución** (confirmado en las corridas de validación de abajo: el proceso
  sigue y responde igual). No hace falta una bandera para "saltear" esto — es autocontenido. Si
  en tu entorno un MCP con auth pendiente sí bloquea el arranque, agrégalo a
  `mcp-inventory.md`/al perfil con `enabled = false`.
- **`-a`/`--permission-mode` para no colgar sin nadie mirando (rol "desatendido"):** ver la
  columna "desatendido" de la matriz — Codex usa `-a never` (nunca escala a aprobación: los
  comandos no confiables fallan en vez de preguntar) y Claude usa `--permission-mode dontAsk`
  para el rol write (en vez de `manual`, que se quedaría esperando una aprobación que nadie va a
  dar). El rol read-only de Claude no necesita esta distinción: el toolset cerrado
  (`--tools "Read,Grep,Glob"`, sin Bash) ya garantiza que nunca surge un prompt, atendido o no.
- **`--disable hooks` en Codex, `disableAllHooks:true` en Claude:** en ambas familias, siempre —
  no solo en el modo desatendido — para que ninguna automatización local (hook de usuario o de
  proyecto) se dispare durante la sesión del secundario.

## Matriz de lanzamiento

`<uuid>` = generar un UUID v4 nuevo por sesión (locator directo de Claude, ver
`spikes/RESULTS.md` Task 0.1). Codex no tiene equivalente — su locator es
creación+`cwd`+timestamp, no hay bandera para fijar el `session_id` desde afuera.

### Claude · read-only

**Atendido y desatendido usan el mismo comando** — el toolset cerrado (`Read,Grep,Glob`, sin
Bash) hace que no exista ningún prompt de aprobación posible, con o sin alguien mirando.

**POSIX:**
```bash
DISABLE_AUTOUPDATER=1 claude \
  --tools "Read,Grep,Glob" \
  --settings "$CROSS_MODEL_ORCA/launch/claude-readonly.settings.json" \
  --session-id "<uuid>" \
  "<prompt>"
```

**PowerShell:**
```powershell
$env:DISABLE_AUTOUPDATER = "1"
claude `
  --tools "Read,Grep,Glob" `
  --settings "$env:CROSS_MODEL_ORCA\launch\claude-readonly.settings.json" `
  --session-id "<uuid>" `
  "<prompt>"
```

> **`$CROSS_MODEL_ORCA`/`$env:CROSS_MODEL_ORCA`:** el comando real lo arma
> `dispatch-adapter.mjs` (`buildLaunchCommand`) desde el install root resuelto por
> `resolveInstallRoot()`; por defecto se **autolocaliza** al `assets` instalado (no hace falta
> setear nada), y `CROSS_MODEL_ORCA` queda como override opcional (ver `install.md`). Si corres
> este comando a mano y no seteaste el override, reemplaza la variable por la ruta real de tu
> checkout (p. ej. `skills/cross-model-orca/assets/launch/claude-readonly.settings.json`).

> **Desatendido (opcional):** para una corrida sin nadie mirando la TUI, agrega
> `--strict-mcp-config --mcp-config "$CROSS_MODEL_ORCA/launch/claude-readonly.mcp.json"`
> **antes** de `--settings` para acotar MCP a cero (o a un allowlist de lectura). En el default
> atendido no hace falta: el gate es la vigilancia manual (ver `mcp-inventory.md`). Ambos flags son
> variádicos — mantén el `<prompt>` al final, tras `--session-id`.

### Claude · write (cross-implement)

**Atendido** (hay alguien que puede aprobar en la TUI) — `--permission-mode manual`:

**POSIX:**
```bash
DISABLE_AUTOUPDATER=1 claude \
  --settings "$CROSS_MODEL_ORCA/launch/claude-write.settings.json" \
  --permission-mode manual \
  --session-id "<uuid>" \
  "<work order>"
```

**PowerShell:**
```powershell
$env:DISABLE_AUTOUPDATER = "1"
claude `
  --settings "$env:CROSS_MODEL_ORCA\launch\claude-write.settings.json" `
  --permission-mode manual `
  --session-id "<uuid>" `
  "<work order>"
```

> **`$CROSS_MODEL_ORCA`/`$env:CROSS_MODEL_ORCA`:** igual que en el perfil read-only, el comando
> real lo arma `buildLaunchCommand` desde el install root autolocalizado por
> `resolveInstallRoot()`; setea el override solo si corres los módulos desde otra ubicación (ver
> `install.md`).

**Desatendido** (nadie mirando; `manual` se colgaría esperando aprobación) —
`--permission-mode dontAsk`:

**POSIX:**
```bash
DISABLE_AUTOUPDATER=1 claude \
  --settings "$CROSS_MODEL_ORCA/launch/claude-write.settings.json" \
  --permission-mode dontAsk \
  --session-id "<uuid>" \
  "<work order>"
```

**PowerShell:**
```powershell
$env:DISABLE_AUTOUPDATER = "1"
claude `
  --settings "$env:CROSS_MODEL_ORCA\launch\claude-write.settings.json" `
  --permission-mode dontAsk `
  --session-id "<uuid>" `
  "<work order>"
```

> **`acceptEdits` — excepción, no default:** solo si el work order corre en un **worktree
> hermano aislado** (nunca el worktree principal del usuario) puede reemplazarse `dontAsk` por
> `--permission-mode acceptEdits` para que las ediciones se apliquen sin fricción. Es una
> decisión explícita por sesión, documentada aquí, **no** el modo por defecto de este perfil.

### Codex · read-only

**Atendido (default, vigilancia manual)** — sin perfil que copiar; `-a untrusted` manda cualquier
comando no confiable a aprobación en la TUI (el humano es el gate), y `-c features.apps=false` apaga
Apps inline:

**POSIX:**
```bash
codex -c features.apps=false -s read-only -a untrusted --disable hooks "<prompt>"
```

**PowerShell:**
```powershell
codex -c features.apps=false -s read-only -a untrusted --disable hooks "<prompt>"
```

**Desatendido** (nadie mirando; `untrusted` podría escalar y colgarse esperando aprobación) —
`-a never`, y **opcionalmente** el perfil `-p cmo-readonly` para restringir MCP server-scoped (hay
que copiarlo antes a `$CODEX_HOME`, ver arriba):

**POSIX:**
```bash
codex -p cmo-readonly -c features.apps=false -s read-only -a never --disable hooks "<prompt>"
```

**PowerShell:**
```powershell
codex -p cmo-readonly -c features.apps=false -s read-only -a never --disable hooks "<prompt>"
```

### Codex · write (cross-implement)

**Atendido (default, vigilancia manual)** — `-a on-request` (el modelo decide cuándo pedir
aprobación; el humano responde en la TUI), sin perfil que copiar, `features.apps=false` inline:

**POSIX:**
```bash
codex -c features.apps=false -s workspace-write -a on-request --disable hooks "<work order>"
```

**PowerShell:**
```powershell
codex -c features.apps=false -s workspace-write -a on-request --disable hooks "<work order>"
```

**Desatendido** — `-a never` (cualquier comando fuera del sandbox falla en vez de preguntar; el
secundario debe resolverlo solo o terminar en error, nunca colgado), y **opcionalmente** el perfil
`-p cmo-write` para restringir MCP server-scoped (hay que copiarlo antes a `$CODEX_HOME`):

**POSIX:**
```bash
codex -p cmo-write -c features.apps=false -s workspace-write -a never --disable hooks "<work order>"
```

**PowerShell:**
```powershell
codex -p cmo-write -c features.apps=false -s workspace-write -a never --disable hooks "<work order>"
```

## Validación real

Entorno: Codex CLI 0.144.6, Claude Code 2.1.214, `CODEX_HOME` = runtime de Orca, 2026-07-19.
Todos los perfiles de prueba (`zz-cmo-*.config.toml`) se instalaron y **se borraron** de
`$CODEX_HOME` al terminar; no se modificó `config.toml` del usuario (confirmado: mismo `wc -l`
antes y después, 342 líneas).

| # | Validación | Comando | Resultado |
|---|------------|---------|-----------|
| 1 | Perfil inexistente se ignora | `codex -p <nombre-inexistente-xyz> mcp list --json` | **Confirmado.** Salida idéntica a la config base, sin error. |
| 2 | `codex mcp list --json` refleja el perfil activo | `codex -p <perfil> mcp list --json` / `mcp get <id>` | **Discrepancia encontrada, no lo que se esperaba.** Se probó en ambas direcciones (perfil que pone `enabled=false` sobre un server base `enabled=true`, y viceversa): en los dos casos `mcp get`/`mcp list` siguieron mostrando el valor de la **config base**, sin reflejar el override del perfil. La CLI sí acepta `-p` para `codex mcp` sin error (mensaje de error de `codex --help` dice explícitamente que `--profile` aplica a `codex mcp`), pero la introspección no lo muestra. **No usar `mcp list`/`mcp get` para verificar qué hace un perfil** — no son confiables para esto en 0.144.6. |
| 3 | `mcp get <servidor>` por servidor inventariado | `codex mcp get atlassian-mcp-server --json`, `codex mcp get engram --json` | **Corrido.** Confirma que `enabled_tools`/`disabled_tools` son campos reales del schema (null cuando no se configuran) — consistente con el "Contexto verificado" del brief. No sirve para validar el efecto del perfil (ver #2). |
| 4 | `features.apps=false` es fail-closed a nivel de feature | `codex features list` (base) vs. intento con perfil | **Parcial.** `codex features list` confirma que `apps` es `stable`/`true` por defecto en este entorno (hay que apagarlo a propósito). No se pudo confirmar el efecto de un perfil sobre `features.apps` vía `features list`, porque ese subcomando **no** admite `-p` (`--profile` solo aplica a `codex`, `codex exec`, `codex review`, `codex resume`, `codex archive`, `codex delete`, `codex unarchive`, `codex fork`, `codex mcp`, `codex sandbox`, `codex debug prompt-input` — mensaje de error real de la CLI). El efecto de `features.apps=false` sobre `codex exec`/`codex` sí se validó indirectamente vía `--strict-config` (ver #7): el campo es válido y se carga sin error. |
| 5 | `approval_mode` no se valida con `mcp get` (necesita chequeo aparte) | — | **Confirmado como limitación esperada** (así lo anticipaba el brief): ni `mcp get` ni `mcp list` muestran `default_tools_approval_mode` ni `tools.<tool>.approval_mode`. Combinado con el hallazgo #2, la única validación confiable de estos campos en 0.144.6 es `--strict-config` (esquema) + una corrida real intentando invocar la tool restringida (comportamiento) — esto último queda como **checkpoint**, no se ejecutó en esta task (hubiera requerido una sesión con tools reales invocadas por el modelo, fuera del alcance de "archivos de config"). |
| 6 | `JSON.parse` sobre los settings de Claude | `node -e "JSON.parse(require('fs').readFileSync('claude-readonly.settings.json','utf8'))"` y lo mismo con `claude-write.settings.json` | **Pasa, sin error**, para ambos archivos. |
| 7 | `--strict-config` sobre cada TOML instalado | `codex exec -p <perfil> --strict-config --ephemeral --skip-git-repo-check -s read-only\|workspace-write --disable hooks "responde OK"` | **Pasa, sin "unknown field"**, para la sección `[features]` + todos los bloques `mcp_servers.*` de `codex-readonly.config.toml` y `codex-write.config.toml` (se validó una copia sin los bloques `[plugins.*]`, ver nota de scope abajo). Sanity check inverso: un campo inventado (`totally_bogus_field`) sí produce `unknown configuration field` — confirma que la validación es real, no un no-op. |
| — | Hallazgo no pedido por el brief, relevante para el diseño | — | **`--strict-config` exige transporte completo (`command`/`args` o `url`) en cualquier `mcp_servers.<id>` que el perfil toque — incluso para un `enabled=false` aislado —, aunque el servidor ya exista en la config base.** Sin `--strict-config` el merge es laxo (hereda transporte de la base); con `--strict-config` cada tabla se valida como si fuera autocontenida. Por eso los cuatro archivos de perfil redeclaran `command`/`args`/`url` de cada servidor que tocan, en vez de solo `enabled = false` o `disabled_tools = [...]`. |
| — | Checkpoint no resuelto | — | **`[plugins."<id>@<marketplace>"] enabled = false` bajo `--strict-config` (con o sin `--ignore-user-config`) colgó el proceso indefinidamente** en dos intentos (probablemente una resincronización de marketplace por red, no un error de esquema — la misma sintaxis ya vive sin problemas en la config base real del usuario, cargada a diario). Los procesos quedaron corriendo en background sin poder matarlos (bloqueado por el clasificador de permisos de la sesión que hizo esta task); no tocan `$CODEX_HOME` (`--ephemeral`) y no dejan estado persistente. **No se confirmó el efecto de los bloques `[plugins.*]` de `codex-readonly.config.toml`/`codex-write.config.toml` con `--strict-config`** — queda como checkpoint para quien retome esta rama: repetir el intento con más margen de tiempo, o validar sin `--strict-config` (carga no estricta, ya usada con éxito en otras pruebas de esta task). |

### Scope de la validación #7

`--strict-config` se corrió sobre una copia de cada perfil **sin** los bloques `[plugins.*]`
(120 líneas de `codex-readonly.config.toml`, misma cantidad menos plugins en
`codex-write.config.toml`), por el hallazgo de arriba. La sección `[features]` +
`mcp_servers.*` — que es el 100% de lo que controla la clasificación lectura/escritura de
`mcp-inventory.md` — sí quedó validada completa contra el CLI real, en ambos sandbox
(`read-only` y `workspace-write`).
