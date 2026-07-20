# MCP y el secundario — vigilancia manual (default) + endurecimiento opcional

> Modelo de control de MCP para las sesiones que lanza `cross-model-orca`. Reemplaza al inventario
> fail-closed de rondas anteriores: un inventario de tools clasificadas a mano envejece cada vez
> que aparece o desaparece un MCP, y empujaba configuración al usuario. El default ahora es
> **vigilancia manual** (P4), coherente con "copiar la skill y listo".

## Default: el humano es el gate (P4, atendido)

El secundario ve los **MCP del entorno del usuario tal cual** — no hay allowlist ni denylist que
mantener. Si el modelo intenta una acción sensible (una escritura MCP, un `send`, etc.), el prompt
de aprobación aparece en la **TUI de esa sesión** y **el humano que mira la corrida aprueba o
rechaza**. Ese es el gate. No hace falta configurar nada de MCP para instalar la skill.

Las garantías que **sí** son cero-config y no dependen de vigilancia:

- **`--tools "Read,Grep,Glob"`** (Claude): sin Bash → read-only duro de los built-ins. Ojo: `--tools`
  acota **solo los built-ins** (`claude --help`: *"from the built-in set"*), **no** gobierna las
  tools MCP — por eso el gate de MCP en el default es la vigilancia manual, no el toolset.
- **`disableAllHooks:true` / `--disable hooks`**: ninguna automatización local se dispara.
- **Sandbox de Codex** (`-s read-only`): el proceso no escribe fuera de lectura.

## Endurecimiento opcional: caso desatendido

Cuando **nadie mira la TUI** (corrida desatendida), la vigilancia manual no aplica: no hay quién
apruebe. Para ese caso, y solo para ese caso, existe un gate declarativo opcional:
**`--strict-mcp-config --mcp-config claude-readonly.mcp.json`**. Da vuelta el default de MCP de
*allow-all* a *deny-all*: la sesión ve **solo** los servidores declarados en ese archivo; todo MCP
del entorno queda invisible. Verificado en vivo (Claude 2.1.214, 2026-07-19): allowlist vacío → la
sesión responde `CERO-MCP`.

`claude-readonly.mcp.json` viene **vacío** (`{"mcpServers": {}}` → cero MCP, el máximo fail-closed).
Si un caso desatendido necesita un servidor de **lectura**, se declara entero ahí (con
`--strict-mcp-config` no se hereda ninguna definición de otras configs). No es un inventario que
haya que mantener sincronizado con el entorno: es una lista corta y explícita que solo crece si el
usuario la hace crecer.

> **Rol write (cross-implement, Fase 5):** su propio gate lo define Fase 5. En desatendido, mismo
> criterio: si no hay humano que apruebe, acota con `--strict-mcp-config` + un allowlist propio.

## Referencia: namespacing real de las tools MCP en Claude

Solo relevante si escribes reglas `permissions.allow`/`deny` (endurecimiento opcional o una cinta
puntual, p. ej. bloquear escrituras de un servidor concreto). **El nombre literal de una tool MCP
depende de cómo esté instalado el servidor**, no solo de su nombre "de servidor":

- **Servidor directo** (`claude mcp add`/`.mcp.json`): `mcp__<servidor>__<tool>`. Ej.: `pencil` →
  `mcp__pencil__get_editor_state`.
- **Servidor de un plugin de marketplace**: `mcp__plugin_<paquete>_<servidor>__<tool>`. Ej.:
  `engram` aparece como `plugin:engram:engram` → `mcp__plugin_engram_engram__mem_save` (**no**
  `mcp__engram__mem_save`). Un prefijo equivocado **no matchea ninguna tool real** y la regla no
  surte efecto (fail-open silencioso).

Un mismo servidor puede estar instalado de las dos formas a la vez (`context7` apareció como
`plugin:context7:context7` y como directo `context7`), cada una con su propio namespace. Por eso,
si vas a depender de una regla `allow`/`deny`, confirma el nombre real contra el entorno de
activación (`claude mcp list`, o una sesión de prueba enumerando las tools) antes de asumir que
matchea.
