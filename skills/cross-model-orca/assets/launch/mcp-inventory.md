# MCP y el secundario — política por familia y rol

> Modelo de control de MCP para las sesiones que lanza `cross-model-orca`. No mantiene un inventario
> manual de tools: Claude read-only cierra el namespace MCP; Codex apaga por override dinámico los
> MCP de su `config.toml` (enumeración al lanzar, nunca una lista fija).

## Claude read-only: deny global en ambos modos

Claude read-only combina tres controles: `--strict-mcp-config` con config vacío evita heredar
servidores configurados; `--disallowedTools "mcp__*"` bloquea también tools aportadas por
plugins/connectors; `--permission-mode dontAsk` rechaza sin dejar la TUI esperando aprobación.

Las garantías que **sí** son cero-config y no dependen de vigilancia:

- **`--tools "Read,Grep,Glob"`** (Claude): sin Bash → read-only duro de los built-ins. Ojo: `--tools`
  acota **solo los built-ins**, no las tools MCP; por eso existe el deny separado.
- **`disableAllHooks:true` / `--disable hooks`**: ninguna automatización local se dispara.
- **Sandbox de Codex** (`-s read-only`): el proceso no escribe fuera de lectura.

## Codex: MCP off por override dinámico en ambos roles

El adaptador enumera las secciones `[mcp_servers.*]` del `config.toml` vigente al momento de
lanzar y agrega un `-c mcp_servers.<name>.enabled=false` por server (`listCodexConfigMcpServers`).
Altas y bajas en el config quedan cubiertas en el próximo lanzamiento sin mantenimiento; config
ilegible → sin overrides (fail-open). Motivo: latencia de boot (los MCP la dominan) y que el
secundario no los necesita — su contexto viaja en el prompt. Cobertura parcial: MCP de plugins y
servers con nombre quoted no son overrideables y arrancan igual. `-s read-only` limita las
escrituras de shell/filesystem, pero no garantiza que una herramienta MCP externa sea read-only —
apagar los MCP también reduce esa superficie. Los perfiles server-scoped de `profiles.md` siguen
siendo un endurecimiento opcional, no parte del lanzamiento default.

## Write: el humano es el gate

Claude write conserva los MCP del entorno. En atendido, cualquier acción sensible requiere la
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
