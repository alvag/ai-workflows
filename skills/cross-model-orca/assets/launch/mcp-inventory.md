# MCP y el secundario — read-only fail-closed, write con vigilancia manual

> Modelo de control de MCP para las sesiones que lanza `cross-model-orca`. No mantiene un inventario
> manual de tools: read-only cierra todo el namespace MCP y write conserva la vigilancia humana.

## Read-only: deny global en ambos modos

Claude read-only combina tres controles: `--strict-mcp-config` con config vacío evita heredar
servidores configurados; `--disallowedTools "mcp__*"` bloquea también tools aportadas por
plugins/connectors; `--permission-mode dontAsk` rechaza sin dejar la TUI esperando aprobación.

Las garantías que **sí** son cero-config y no dependen de vigilancia:

- **`--tools "Read,Grep,Glob"`** (Claude): sin Bash → read-only duro de los built-ins. Ojo: `--tools`
  acota **solo los built-ins**, no las tools MCP; por eso existe el deny separado.
- **`disableAllHooks:true` / `--disable hooks`**: ninguna automatización local se dispara.
- **Sandbox de Codex** (`-s read-only`): el proceso no escribe fuera de lectura.

## Write: el humano es el gate

El rol write conserva los MCP del entorno. En atendido, cualquier acción sensible requiere la
aprobación del humano en la TUI. En desatendido usa `dontAsk`: lo no aprobado falla en vez de dejar
la sesión colgada. Si un flujo write necesita una política MCP más estrecha, debe declararla como
parte explícita de ese work order; no se relaja el perfil read-only.

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
