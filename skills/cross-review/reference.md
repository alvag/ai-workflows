# cross-review — Referencia

Detalle operativo de la skill `cross-review`. El `SKILL.md` apunta acá cuando necesita el
contrato de invocación del revisor, la plantilla del prompt, el formato de salida o el foco por
tipo de artefacto.

## Tabla de contenidos

- [Portabilidad entre shells (POSIX / PowerShell)](#portabilidad-entre-shells-posix--powershell)
- [Descubrir el revisor](#descubrir-el-revisor)
- [Invocar al revisor (read-only)](#invocar-al-revisor-read-only)
- [Resume entre rondas](#resume-entre-rondas)
- [Prompt de revisión](#prompt-de-revisión)
- [Formato de salida](#formato-de-salida)
- [Foco por tipo de artefacto](#foco-por-tipo-de-artefacto)
- [Plantilla de review-log.md](#plantilla-de-review-logmd)
- [Configuración](#configuración)
- [Manifest de corrida](#manifest-de-corrida)

---

## Portabilidad entre shells (POSIX / PowerShell)

Las vías de invocación del revisor usan comandos de shell. Esos comandos se muestran en **dos
variantes**, y hay que elegir según el shell del entorno:

- **POSIX** — macOS y Linux, y también **Git Bash en Windows** (la Bash tool del agente). Es la
  forma en que están escritos los bloques `bash` de este documento; funcionan tal cual.
- **PowerShell** — Windows nativo (shell primary). PowerShell **no** soporta la redirección de
  stdin con `<` ni el subshell `(cd … && …)`, y no trae `uuidgen`: por eso cada vía incluye su
  bloque `powershell` equivalente.

**Cómo elegir la variante.** Detectar el OS/shell antes de invocar. En Claude Code el system prompt
ya indica el `Platform`; como respaldo, `uname -s` (POSIX → `Darwin`/`Linux`/`MINGW…`) o
`$IsWindows` (PowerShell → `True`). En Windows el equivalente canónico es **PowerShell**; si se
ejecuta con la **Bash tool (Git Bash)**, los bloques POSIX aplican igual y no hace falta traducir.

**Equivalencias de las primitivas** (lo único que cambia entre vías; el resto de los flags del CLI
es agnóstico del shell):

| Primitiva | POSIX (bash / Git Bash) | PowerShell (Windows) |
|---|---|---|
| ¿Existe el binario? | `command -v codex` | `Get-Command codex -ErrorAction SilentlyContinue` |
| Prompt (archivo) → stdin | `cmd … - < prompt.txt` | `Get-Content -Raw prompt.txt \| cmd … -` |
| Capturar stdout → archivo | `cmd … > out.txt` | `cmd … > out.txt` (PS7 escribe UTF-8 sin BOM) |
| Generar un UUID | `uuidgen` | `[guid]::NewGuid().ToString()` |
| Ejecutar en otro cwd | `(cd dir && cmd)` | `Push-Location dir; …; Pop-Location` (o el flag `-C dir` de `codex`) |
| Detectar el OS | `uname -s` | `$IsWindows` |

> **`uuidgen` falta en Git Bash de Windows** (solo está en macOS/Linux). Si se corre la Vía C por
> Git Bash en Windows, usar el fallback `powershell -NoProfile -Command "[guid]::NewGuid().ToString()"`,
> o que el agente genere un UUID v4 y lo pase como literal a `--session-id`.

Las reglas invariantes de "Invocar al revisor" valen en **ambos** shells: read-only siempre, y el
prompt **se escribe a archivo con la tool Write** (nunca inline ni `echo`/heredoc); solo cambia la
primitiva con que ese archivo llega a stdin (`<` en POSIX, `Get-Content -Raw | …` en PowerShell).

---

## Descubrir el revisor

Esta sección es la **fuente canónica** del descubrimiento: `co-explore` la referencia por
puntero (su fallback embebido es un resumen de esto).

Los nombres de tools/MCP/agentes cambian entre entornos. Resolver el revisor por **capacidad**
(un segundo modelo que pueda **criticar texto en read-only**) con una regla dura por delante:

> **El revisor nunca es de la misma familia de modelos que el autor.** Hay dos familias: Claude
> y GPT/Codex. Un revisor de la misma familia comparte los puntos ciegos del autor: los errores
> correlacionados que la cross-review existe para romper.

**Paso 1 — identificar la familia del autor.** Es la del agente que conduce la skill, sin
importar la superficie donde corre (CLI, app de escritorio, IDE, web): un agente Claude → autor
Claude; un agente Codex → autor GPT/Codex.

**Paso 2 — elegir el revisor de la OTRA familia** (`reviewer: auto`):

| Familia del autor | Revisor a buscar | Cómo detectarlo | Vía de invocación |
|---|---|---|---|
| Claude | Codex | ¿Existe el subagente `codex:codex-rescue` (plugin codex)? Si no, ¿`command -v codex`? | Vía A (preferida) o Vía B |
| GPT/Codex | Claude | ¿`command -v claude`? | Vía C |

> **En PowerShell** la detección de binarios es `Get-Command codex -ErrorAction SilentlyContinue`
> (ídem `claude`) en vez de `command -v` — ver "Portabilidad entre shells (POSIX / PowerShell)".

Con `reviewer: claude` o `reviewer: codex` forzados en config, ir directo a esa vía. Si la vía
forzada coincide con la familia del autor (ej. autor Claude + `reviewer: claude`) → misma
familia: avisar que se pierde el valor cross-model y continuar (el override manda).

**Prechequeos (revisor Codex, Vías A/B).** Tres chequeos baratos antes de la ronda 1:

- **Versión**: `codex --version`. CLIs viejos (< 0.130) fallan con error de modelo contra los
  defaults actuales. Ante un error de auth o de modelo, superficiarlo y degradar (`UNAVAILABLE`)
  — nunca reintentar en silencio.
- **Aislamiento disponible**: ver "Preflight de aislamiento (fail-closed)" en la Vía B. Sin él no
  se lanza el worker.
- **Modelo: leer del config y pasarlo explícito.** El worker corre con `--ignore-user-config`, que
  descarta el `model` y el `model_reasoning_effort` del usuario junto con el resto de la
  configuración. El flujo es: leer del config → aislar → pasar explícito con `-m` y
  `-c model_reasoning_effort=` → ecoar lo resuelto. Si la lectura no es inequívoca (ver Vía B), no
  se pasa `-m` y se usa el default del CLI. Un modelo pedido explícitamente por el usuario manda
  sobre lo leído. Nota histórica: los variants `gpt-5.x-codex` devuelven 400 con auth de cuenta
  ChatGPT — por eso el valor viaja tal cual está en el config, sin sustituciones.
- **Eco del modelo activo**: registrar en el `review-log.md`, junto al revisor, el modelo y el
  esfuerzo efectivos (o "CLI default" cuando no se pudieron determinar), para que la corrida quede
  auditada con el modelo real que criticó.

> **No usar `/codex:review` ni `/codex:adversarial-review`.** Esos comandos del plugin operan
> sobre git diff y su schema de salida exige `file`+`line` (código-céntrico): no sirven para
> revisar un markdown. El camino correcto para documentos es `task` / `codex exec`.

Si ninguna opción **de otra familia** está disponible → veredicto `UNAVAILABLE` y ceder al gate
humano (degradación).

## Invocar al revisor (read-only)

Dos reglas invariantes:

1. **Read-only siempre** — el revisor no escribe; Claude es quien edita el artefacto si hay que
   aplicar algo.
2. **El prompt nunca se interpola inline en un comando shell.** El prompt de revisión contiene
   markdown (backticks, asteriscos): interpolado en la línea de comandos, los backticks se
   ejecutan como command substitution y el texto se fragmenta en palabras sueltas. Escribir el
   prompt a un archivo con la **tool de escritura de archivos del agente** (Write o equivalente —
   no `echo`/heredoc, que re-introducen el mismo problema de quoting) en el `scratch_dir` junto al
   veredicto (ej: `<scratch_dir>/spec-prompt-r1.txt`) y pasarlo al CLI por **stdin**. De paso queda
   trazabilidad de qué se le pidió al revisor en cada ronda.

### Archivos de trabajo (scratch)

Las Vías B/C escriben varios archivos de trabajo por ronda (prompt, veredicto, delta del resume,
session-id, stderr). **Todos van a un subdirectorio `cross-review/` junto al artefacto**, no sueltos
en la raíz del flujo:

- **`scratch_dir` = `<dir del artefacto>/cross-review/`** — derivado del `artifact_path`
  (`dirname(artifact_path)/cross-review/`). Resuelve a `.plans/<id>/cross-review/` (sdd-flow,
  sdd-pr-feedback), `.sdd/<id>/cross-review/` (sdd-orchestrator) o
  `.cross-review/<slug>/cross-review/` (modo draft, cuyo plan vive en `.cross-review/<slug>/plan.md`),
  sin lógica especial por skill. Crearlo antes de la ronda 1.
- **Nomenclatura**: `<artifact_type>-<tipo>-r<N>.txt`. El prefijo por `artifact_type` evita
  colisiones entre los gates de `spec`/`plan`/`tasks`. Ejemplos:
  `cross-review/spec-prompt-r1.txt`, `cross-review/spec-verdict-r1.txt`,
  `cross-review/plan-delta-r2.txt`, `cross-review/plan-verdict-r2.txt`,
  `cross-review/plan-r1.err.txt`, `cross-review/spec-thread-r1.jsonl` (stream JSONL de la ronda 1,
  de donde se parsea el thread id), `cross-review/spec-session.txt` (el thread/session id capturado),
  `cross-review/spec-session-meta.json` (modelo y esfuerzo efectivos de la corrida).
- **`session-meta.json`** acompaña al `session.txt` con `{"model": "...", "effort": "..."}`. Existe
  porque cada ronda corre en un proceso shell nuevo y las variables de la ronda 1 no sobreviven;
  el resume las relee de ahí. Un campo vacío significa "default del CLI", nunca cadena vacía a
  pasar como flag.
- **`review-log.md` NO va acá.** Es el registro auditable consolidado (rondas, findings, decisiones,
  veredicto), hermano de `spec.md`/`plan.md`/`tasks.md`: queda en `<dir del artefacto>/review-log.md`
  (la raíz del flujo).
- **Scratch transitorio, sin autolimpieza.** El `cross-review/` es local y untracked (igual que el
  resto de `.plans/`/`.sdd/`). No se borra solo: el usuario puede eliminarlo cuando quiera. Una nueva
  corrida del mismo artefacto sobrescribe los archivos de las mismas rondas (no crece sin límite).

> En los bloques de comando de las Vías B y C (abajo), todas las rutas de archivo de trabajo
> —`<ruta/al/prompt-r1.txt>`, `<ruta/al/veredicto.txt>`, `<ruta/al/delta-rN.txt>`,
> `<ruta/al/….err.txt>` y sus variantes `<ruta\al\…>` de PowerShell— viven **dentro del
> `scratch_dir`** (p. ej. `<scratch_dir>/spec-prompt-r1.txt`, `<scratch_dir>/plan-r2.err.txt`).

### Vía A — subagente `codex:codex-rescue` (preferida en Claude Code)

Despachar el subagente con el prompt de revisión como task text. El forwarder lo manda a
`task` del runtime (`codex-companion.mjs`). Por contrato, el runtime corre **read-only** cuando
el pedido es "review/diagnosis/research sin edits": por eso el prompt debe decir explícitamente
que es una **revisión de solo lectura, sin modificar archivos**. No agregar `--write`.

- Ronda 1: despachar fresh.
- Rondas siguientes: incluir el token `--resume` en el pedido → el runtime lo normaliza a
  `task --resume-last`, retomando el mismo thread de Codex (ver "Resume entre rondas").

### Vía B — CLI `codex exec` (portable)

Patrón (igual que grill-me-codex). Flags verificados con `codex-cli` 0.137–0.143 (el
comportamiento del sandbox en resume y del id vacío/inválido, end-to-end en 0.143.0,
2026-07-09); pueden variar por versión, así que ante la duda confirmar con `codex exec --help`.
Descubrir por capacidad, no hardcodear ciegamente.

#### Preflight de aislamiento (fail-closed)

Antes de lanzar, comprobar que la versión instalada permite aislar al worker. Si falta cualquiera
de las tres piezas, **no se lanza**: `UNAVAILABLE` y gate humano.

```bash
codex exec --help | grep -q -- --ignore-user-config || FAIL=1
for f in hooks apps plugins; do
  codex features list 2>/dev/null | grep -qE "^$f[[:space:]]" || FAIL=1
done
```

Por qué fail-closed y no best-effort: `-s read-only` acota lo que el worker escribe **en disco**,
no los efectos remotos de una tool MCP. Un worker "read-only" con los MCP del entorno puede
alcanzar una tool de ejecución y correr comandos fuera del `working_dir`. Si no se puede
garantizar el aislamiento, la degradación correcta es no tener revisor, no tener uno sin contener.

#### Ronda 1

Prompt escrito antes a archivo (ver regla 2 de "Invocar al revisor"). Dos detalles del comando son
contraintuitivos y **no** se deben "simplificar":

- **Los argumentos se construyen incrementalmente, nunca con expansión condicional.**
  `${MODEL:+-m "$MODEL"}` no sirve: en zsh las expansiones de parámetros no hacen field splitting,
  así que `-m` y su valor viajan como un solo argumento y el modelo llega con un espacio inicial.
  La API responde `' <modelo>' model is not supported`.
- **La lectura del config valida antes de usar.** Solo vale una asignación **raíz** —anterior a la
  primera cabecera de tabla—, con comillas dobles y una sola ocurrencia. Cualquier otra cosa deja
  el valor vacío y el flag no se pasa: es preferible el default del CLI a forzar un modelo sacado
  de dentro de una tabla o de un perfil inactivo.

```bash
# POSIX
CODEX_CFG="${CODEX_HOME:-$HOME/.codex}/config.toml"
# Preámbulo raíz del TOML. awk y no `sed -n '1,/^\[/p' | sed '$d'`, que falla en tres casos
# válidos: cabecera en la primera línea (mete la tabla en la raíz), archivo sin tablas (borra la
# última asignación) y cabecera indentada (no la reconoce).
ROOT=$(awk '/^[[:space:]]*\[/{exit} {print}' "$CODEX_CFG" 2>/dev/null)
read_root_key() {   # $1 = clave; imprime el valor SOLO si hay una asignación raíz inequívoca
  n=$(printf '%s\n' "$ROOT" | grep -cE "^$1[[:space:]]*=[[:space:]]*\"[^\"]*\"[[:space:]]*$")
  [ "$n" -eq 1 ] && printf '%s\n' "$ROOT" |
    sed -n "s/^$1[[:space:]]*=[[:space:]]*\"\([^\"]*\)\".*/\1/p"
}
MODEL=$(read_root_key model)
EFFORT=$(read_root_key model_reasoning_effort)
echo "revisor: codex ${MODEL:-<default del CLI: no se pudo determinar el del config>}"

set -- exec --ignore-user-config --disable hooks --disable apps --disable plugins \
       -s read-only -C <working_dir> --skip-git-repo-check --json \
       --output-last-message <ruta/al/veredicto.txt>
[ -n "$MODEL" ]  && set -- "$@" -m "$MODEL"
[ -n "$EFFORT" ] && set -- "$@" -c "model_reasoning_effort=$EFFORT"
set -- "$@" -
codex "$@" < <ruta/al/prompt-r1.txt> > <ruta/al/thread-r1.jsonl> 2> <ruta/al/r1.err.txt>

# Persistir thread id + modelo/esfuerzo efectivos: las rondas siguientes corren en otro proceso.
grep -m1 -o '"thread_id":"[^"]*"' <ruta/al/thread-r1.jsonl> | cut -d'"' -f4 \
  > <ruta/al/session.txt>
printf '{"model":"%s","effort":"%s"}\n' "$MODEL" "$EFFORT" > <ruta/al/session-meta.json>
```

```powershell
# PowerShell
$CodexCfg = Join-Path ($env:CODEX_HOME ?? "$HOME\.codex") 'config.toml'
$Lines = @(Get-Content $CodexCfg -ErrorAction SilentlyContinue)
# Cabecera de tabla: admite indentación. Si está en la línea 1, la raíz es vacía.
$Idx = ($Lines | Select-String -Pattern '^\s*\[' | Select-Object -First 1).LineNumber
$Root = if (-not $Idx) { $Lines } elseif ($Idx -eq 1) { @() } else { $Lines[0..($Idx - 2)] }
function Read-RootKey($Key) {
  $m = @($Root | Select-String -Pattern "^$Key\s*=\s*`"([^`"]*)`"\s*$")
  if ($m.Count -eq 1) { $m[0].Matches.Groups[1].Value }
}
$Model  = Read-RootKey 'model'
$Effort = Read-RootKey 'model_reasoning_effort'

$CodexArgs = @('exec','--ignore-user-config','--disable','hooks','--disable','apps',
               '--disable','plugins','-s','read-only','-C','<working_dir>',
               '--skip-git-repo-check','--json','--output-last-message','<ruta\al\veredicto.txt>')
if ($Model)  { $CodexArgs += @('-m', $Model) }
if ($Effort) { $CodexArgs += @('-c', "model_reasoning_effort=$Effort") }
$CodexArgs += '-'
Get-Content -Raw <ruta\al\prompt-r1.txt> |
  & codex @CodexArgs > <ruta\al\thread-r1.jsonl> 2> <ruta\al\r1.err.txt>

(Select-String -Path <ruta\al\thread-r1.jsonl> -Pattern '"thread_id":"([^"]+)"' |
  Select-Object -First 1).Matches.Groups[1].Value > <ruta\al\session.txt>
@{ model = $Model; effort = $Effort } | ConvertTo-Json -Compress > <ruta\al\session-meta.json>
```

  Los cuatro flags de aislamiento —`--ignore-user-config --disable hooks --disable apps
  --disable plugins`— son el corazón del cambio: sin ellos el worker hereda los MCP del entorno,
  los hooks locales y las instrucciones de modelo del usuario. Medido en este repo: un worker sin
  aislar arrancó consultando memoria, hizo búsquedas web y no terminó en 600 s; el mismo prompt
  aislado cerró en 297 s con cero llamadas MCP. `--ignore-user-config` descarta **todo** el config,
  por eso el modelo y el esfuerzo se releen antes y se pasan explícitos.
  `-s read-only` (= `--sandbox read-only`) garantiza que no escribe; `-C` fija el working root;
  `--skip-git-repo-check` permite correr aunque la contenedora no sea repo git;
  `--output-last-message` deja el mensaje final (el veredicto + findings) en un archivo, fácil de
  parsear; el `-` como PROMPT hace que las instrucciones se lean de **stdin**; `--json` emite el
  stream de eventos JSONL por stdout — la línea `{"type":"thread.started","thread_id":"…"}` es la
  única captura **determinística** del session id, y ese id explícito es lo que usa el resume.
- Rondas siguientes (mismo thread): el subcomando `resume` **no** acepta `-s`/`--sandbox` ni
  `--color` ni `-C` — y el sandbox de la sesión original **NO es una garantía al reanudar**: un
  `-c sandbox_mode` en el resume lo redefine en cualquier dirección. Verificado 2026-07-09 con
  codex-cli 0.143.0: una sesión lanzada con `-s read-only` y reanudada con
  `-c sandbox_mode="workspace-write"` **escribió un archivo**. Sin flags, en esas pruebas (config
  sin `sandbox_mode`) el resume se comportó como la sesión original, pero ese default **no está
  garantizado** entre versiones ni configs (grill-me-codex reporta que hereda `config.toml`,
  posiblemente `danger-full-access`). Por eso el resume lleva SIEMPRE el override explícito
  `-c sandbox_mode="read-only"` — el read-only del revisor nunca depende de un default.

  **El aislamiento también se repite en cada ronda.** La configuración se lee en *cada* invocación
  de `codex`, así que un resume sin los cuatro flags vuelve a levantar los MCP, hooks y plugins del
  usuario, por más que la ronda 1 los haya apagado. Verificado contra `codex exec resume --help`
  0.145.0: acepta `--ignore-user-config`, `--disable` y `-m`.

  **Y el modelo se relee de disco, no de una variable.** Cada ronda corre en un proceso shell
  nuevo: `$MODEL`/`$EFFORT` de la ronda 1 no existen acá. Por eso la ronda 1 los persistió en
  `session-meta.json` junto al `session.txt`.

  ```bash
  SESSION_ID=$(cat <ruta/al/session.txt>)
  echo "resume → ${SESSION_ID:?vacío}"   # eco visible + corte si quedó vacío (ver nota --last)
  # Releer del scratch: las variables del proceso de la ronda 1 no sobreviven.
  MODEL=$(sed -n 's/.*"model":"\([^"]*\)".*/\1/p'  <ruta/al/session-meta.json>)
  EFFORT=$(sed -n 's/.*"effort":"\([^"]*\)".*/\1/p' <ruta/al/session-meta.json>)

  set -- exec resume "$SESSION_ID" --ignore-user-config \
         --disable hooks --disable apps --disable plugins \
         -c sandbox_mode=read-only --skip-git-repo-check \
         --output-last-message <ruta/veredicto.txt>
  [ -n "$MODEL" ]  && set -- "$@" -m "$MODEL"
  [ -n "$EFFORT" ] && set -- "$@" -c "model_reasoning_effort=$EFFORT"
  set -- "$@" -
  codex "$@" < <ruta/al/delta-rN.txt> > <ruta/al/thread-rN.jsonl> 2> <ruta/al/rN.err.txt>
  ```
  En **PowerShell**:
  ```powershell
  $SessionId = (Get-Content <ruta\al\session.txt>).Trim()
  if (-not $SessionId) { throw 'session id vacío' }; "resume → $SessionId"
  $Meta   = Get-Content -Raw <ruta\al\session-meta.json> | ConvertFrom-Json
  $Model  = $Meta.model
  $Effort = $Meta.effort

  $CodexArgs = @('exec','resume',$SessionId,'--ignore-user-config','--disable','hooks',
                 '--disable','apps','--disable','plugins','-c','sandbox_mode=read-only',
                 '--skip-git-repo-check','--output-last-message','<ruta\veredicto.txt>')
  if ($Model)  { $CodexArgs += @('-m', $Model) }
  if ($Effort) { $CodexArgs += @('-c', "model_reasoning_effort=$Effort") }
  $CodexArgs += '-'
  Get-Content -Raw <ruta\al\delta-rN.txt> |
    & codex @CodexArgs > <ruta\al\thread-rN.jsonl> 2> <ruta\al\rN.err.txt>
  ```
  Capturar el stderr no es opcional: es donde aparecen los fallos de refresh de OAuth y los
  errores de metadata de modelo, que de otro modo pasan invisibles.
  **`--last` es solo fallback** (si el thread id no se pudo capturar): filtra por cwd — elige la
  sesión más reciente *del directorio actual* (`--all` desactiva el filtro), así que correrlo
  desde el mismo `working_dir` de la ronda 1 (en PowerShell, `Push-Location <working_dir>`
  antes) — y con sesiones paralelas puede agarrar el thread equivocado. Y ojo con el id
  **vacío** (verificado 2026-07-09, codex-cli 0.143.0): un id inválido falla ruidoso ("no
  rollout found", exit 1), pero un id vacío arranca **en silencio una sesión FRESCA** — exit 0,
  parece un resume exitoso y el revisor perdió todo su contexto. Por eso el corte si el id está
  vacío (`${SESSION_ID:?}` / `throw`) y el eco visible antes de correr el comando. El id
  explícito capturado de `thread.started` es siempre el camino preferido.
- Opcional: `--output-schema <archivo.json>` fuerza el shape del mensaje final a un JSON Schema
  (útil para hacer el "Formato de salida" todavía más parseable).

### Vía C — CLI `claude -p` (Claude como revisor; cuando el autor es GPT/Codex)

`claude` no tiene un flag de sandbox equivalente a `codex -s read-only`: el read-only se
garantiza **restringiendo las tools permitidas a las de lectura**
(`--allowedTools=Read,Grep,Glob`; en modo `-p` no hay prompts interactivos, así que toda tool
fuera de esa lista queda
denegada — sin escritura ni shell). Flags verificados con Claude Code 2026-06; ante la duda
confirmar con `claude --help`.

Trampas de este CLI que la invocación debe esquivar:

- `--allowedTools` es **variadic** (acepta lista separada por espacios): cualquier argumento
  posterior se traga como "regla" más. Pasarlo siempre con **`=` y comas en un solo argumento**
  (`--allowedTools=Read,Grep,Glob`) — el `=` cierra el parseo del flag sin depender de la
  posición de los demás argumentos — y nunca poner el prompt después del flag. En **PowerShell**,
  entrecomillarlo (`'--allowedTools=Read,Grep,Glob'`) para que la coma no se interprete como
  separador de array.
- El prompt va por **stdin desde archivo** (regla 2 de "Invocar al revisor"), nunca interpolado
  inline. Síntoma de la combinación de ambas trampas: el markdown fragmentado en palabras se
  parsea como reglas de `--allowedTools` y el proceso queda sin prompt → si stdin está cerrado,
  `--print` aborta ("Input must be provided…"); si stdin está abierto y vacío (típico al invocar
  desde Python), **cuelga indefinidamente** esperando input. Una invocación que **cuelga de
  entrada, sin progreso alguno**, es señal de parseo de flags roto — distinto de una que **avanza
  pero tarda** (lentitud real del modelo con prompt grande; ver "Latencia y timeout (Claude revisor)" más abajo).
- Un `claude -p` headless **hereda los settings del usuario y del proyecto** del working_dir:
  modelo configurado (puede ser uno caro/lento), `permissions.defaultMode`, plugins, hooks y
  servidores MCP (arranque pesado). Fijar siempre los valores por flag: `--model opus`,
  `--permission-mode default`, y `--safe-mode` para no cargar plugins/hooks/MCP/CLAUDE.md del
  usuario. (`--bare` NO: solo acepta auth por ANTHROPIC_API_KEY y rompe el OAuth de suscripción;
  `--safe-mode` mantiene auth, modelo, tools y permisos normales.)
- Nunca pasar `--permission-mode plan` al revisor: entra en modo planificación y no ejecuta la
  revisión.

- Ronda 1 (fijar un session id propio para poder reanudar después; prompt escrito antes a archivo):
  ```bash
  SESSION_ID=$(uuidgen)   # Git Bash en Windows no trae uuidgen → ver "Portabilidad entre shells"
  (cd <working_dir> && claude -p --safe-mode \
      --model opus \
      --permission-mode default \
      --allowedTools=Read,Grep,Glob \
      --session-id "$SESSION_ID" \
      < <ruta/al/prompt-r1.txt>) > <ruta/al/veredicto.txt>
  ```
  En **PowerShell** (`uuidgen` → `[guid]::NewGuid()`; el subshell `(cd … && …)` →
  `Push-Location`/`Pop-Location`; `<` → pipe):
  ```powershell
  $SessionId = [guid]::NewGuid().ToString()
  Push-Location <working_dir>
  try {
    Get-Content -Raw <ruta\al\prompt-r1.txt> |
      claude -p --safe-mode --model opus --permission-mode default `
        '--allowedTools=Read,Grep,Glob' --session-id $SessionId > <ruta\al\veredicto.txt>
  } finally { Pop-Location }
  ```
  El mensaje final (veredicto + findings) sale por stdout → redirigirlo a archivo para parsear,
  igual que `--output-last-message` en la Vía B.
- Rondas siguientes (mismo thread, con memoria de lo ya discutido):
  ```bash
  (cd <working_dir> && claude -p --safe-mode \
      --model opus \
      --permission-mode default \
      --allowedTools=Read,Grep,Glob \
      --resume "$SESSION_ID" \
      < <ruta/al/delta-rN.txt>) > <ruta/al/veredicto.txt>
  ```
  En **PowerShell**:
  ```powershell
  Push-Location <working_dir>
  try {
    Get-Content -Raw <ruta\al\delta-rN.txt> |
      claude -p --safe-mode --model opus --permission-mode default `
        '--allowedTools=Read,Grep,Glob' --resume $SessionId > <ruta\al\veredicto.txt>
  } finally { Pop-Location }
  ```
- Fallback si la invocación cuelga pese a todo: agregar `--no-session-persistence` (solo `-p`).
  Deshabilita el resume → degradar a rondas independientes (ver "Resume entre rondas").
- El prompt debe decir igualmente que es una revisión de SOLO lectura: la restricción de tools
  es el cinturón; el prompt, los tiradores.

#### Handoff destilado, nunca transcript crudo

Al modelo delegado se le pasa un **contrato destilado** —objetivo, contexto necesario, límites—,
nunca el transcript literal de la sesión del conductor. El prompt por archivo que esta skill usa
**ya es** un handoff destilado: no es una convención estética, es la forma correcta, y conviene
saber por qué para que nadie la "optimice" pasándole contexto ambiente al delegado.

El porqué no es solo de diseño. Está documentado un caso real donde reproducir dentro de un modelo
un transcript construido bajo otro activó clasificadores de política de uso y **bloqueó todas las
requests de la sesión** —incluso las triviales—, mientras la misma consulta en una sesión fresca
pasaba sin problema. El diseño barato resultó ser también el seguro.

Consecuencia práctica: si el delegado necesita saber algo, ese algo se **escribe en el prompt**. No
se le reenvía la conversación para que lo deduzca.

## Latencia y timeout (Claude revisor)

La revisión con `--model opus` sobre un **prompt grande** (gate de plan/tasks: artefacto + spec/plan
de contexto + permiso de leer el repo) puede tardar **varios minutos** en producir la primera
salida. El default sigue siendo `opus` (la calidad de la crítica es el punto de la skill), pero hay
que darle tiempo. El modo lo controla `cross_review.execution` (ver "Configuración").

> **Aplica en cualquier OS:** el tope lo impone el **conductor** (p.ej. Codex, ~120s por comando),
> no el sistema operativo. La gestión es idéntica en macOS/Linux y Windows; solo cambia la sintaxis
> del shell — usa el bloque **bash** (POSIX: macOS/Linux/Git Bash) o el **PowerShell** (Windows),
> ambos abajo.

**Invariante (vale para los dos caminos): ningún camino espera indefinida.** Siempre hay un tope de
pared duro; si vence sin `VERDICT:`, es `UNAVAILABLE` (regla 6) y se degrada al gate humano.

##### Camino SYNC — preferido (conductor con timeout de exec largo)

Una **única llamada bloqueante** con tope generoso (**≥5 min `normal`, ~10 min `complex`**). El
corte lo garantiza la **primitiva de exec del conductor** — en Claude Code, `Bash` con `timeout`
hasta **600000ms** (300000 para `normal`, 600000 para `complex`). No hay loop de poll: **no existe
cuelgue posible**, porque el propio exec mata el comando al vencer el tope. Es el default en `auto`
cuando el conductor puede sostener ese timeout, y lo que fuerza `execution: sync`.

```bash
# Sync (POSIX) — el conductor fija el tope vía su exec (Claude Code: Bash timeout 300000/600000):
( cd <working_dir> && claude -p --safe-mode --model opus --permission-mode default \
    --allowedTools=Read,Grep,Glob --session-id "$SESSION_ID" \
    < <ruta/al/prompt-r1.txt> ) > <ruta/al/veredicto.txt> 2> <ruta/al/claude-r1.err.txt>
```
Si el comando excede el `timeout` del conductor → `UNAVAILABLE`. Vías A/B (Codex revisor) ya son
bloqueantes por naturaleza: mismo contrato, el tope lo da el timeout del conductor.

##### Camino BACKGROUND + poll **acotado** — fallback (conductor con exec corto, p.ej. Codex ~120s)

Solo cuando el conductor **no puede** subir su timeout de exec. Lanzar `claude -p` en segundo plano
escribiendo el veredicto a archivo; el **comando de lanzamiento retorna en <1s** (no excede el tope),
y después se **pollea el archivo en comandos cortos separados** hasta ver el `VERDICT:`. Ningún
comando único bloquea más que el límite del conductor. Lo fuerza `execution: background`.

> **El poll SIEMPRE tiene corte.** Definir un `poll_deadline` = el mismo presupuesto del modo sync
> (≥5 min `normal`, ~10 min `complex`). Como `Date.now()` puede no estar disponible, llevar un
> **contador de iteraciones** (`intentos × ~10s`) como proxy del reloj. Al alcanzar `poll_deadline`
> **sin** ver `^VERDICT:` → **abandonar, marcar `UNAVAILABLE`, degradar al gate humano** y matar el
> proceso en background si se puede (`kill <pid>`). Nunca seguir poleando indefinida.

```bash
# Lanzar en background (POSIX) — capturar el PID para poder matarlo al vencer el deadline:
( cd <working_dir> && claude -p --safe-mode --model opus --permission-mode default \
    --allowedTools=Read,Grep,Glob --session-id "$SESSION_ID" \
    < <ruta/al/prompt-r1.txt> > <ruta/al/veredicto.txt> 2> <ruta/al/claude-r1.err.txt> ) &
PID=$!
# Poll (repetir como comandos cortos separados; tope DURO: ~N intentos = poll_deadline / 10s):
#   normal  → ~30 intentos (~5 min);  complex → ~60 intentos (~10 min).
grep -q '^VERDICT:' <ruta/al/veredicto.txt> 2>/dev/null && cat <ruta/al/veredicto.txt> || echo 'corriendo…'
# Si se agotan los intentos sin VERDICT: → kill "$PID"; tratar como UNAVAILABLE.
```
```powershell
# Lanzar en background (PowerShell; Start-Process toma el prompt como archivo de stdin):
$SessionId = [guid]::NewGuid().ToString()
$proc = Start-Process -FilePath claude -WorkingDirectory <working_dir> -NoNewWindow -PassThru `
  -RedirectStandardInput  <ruta\al\prompt-r1.txt> `
  -RedirectStandardOutput <ruta\al\veredicto.txt> `
  -RedirectStandardError  <ruta\al\claude-r1.err.txt> `
  -ArgumentList '-p','--safe-mode','--model','opus','--permission-mode','default','--allowedTools=Read,Grep,Glob','--session-id',$SessionId
# Poll (repetir como comandos cortos; tope DURO de ~N intentos = poll_deadline / 10s):
if ((Test-Path <ruta\al\veredicto.txt>) -and ((Get-Content <ruta\al\veredicto.txt> -Raw) -match 'VERDICT:')) {
  Get-Content <ruta\al\veredicto.txt>      # listo → parsear
} else { 'corriendo…' }                    # volver a chequear; al agotar intentos → Stop-Process $proc; UNAVAILABLE
```

##### Diagnóstico y palancas (ambos caminos)

- **Distinguir dos fallas** (no confundirlas con la trampa de parseo de arriba):
  - *Cuelga de entrada, 0 progreso* → parseo de flags roto (`--allowedTools`/stdin).
  - *Avanza pero excede el timeout/deadline* → lentitud real del modelo → subir el tope (sync), o
    bajar de modelo.
- **Capturar stderr** (`2> claude-rN.err.txt`, ya incluido arriba): distingue un cuelgue (sin
  stderr) de un error real (auth, flag inválido, modelo no disponible). Registrarlo en el
  `review-log.md`.
- **Override de modelo:** si el prompt es muy grande o solo se valida el flujo, `--model sonnet`
  reduce latencia a cambio de profundidad. El default sigue `opus`; bajarlo es una decisión consciente.

En todas las vías, si la invocación falla (error, timeout, deadline vencido, salida vacía o no
parseable) → tratarlo como `UNAVAILABLE` en runtime (degradación, regla 6 del SKILL).

## Resume entre rondas

El loop reusa el **mismo thread del revisor** para que tenga memoria de lo ya discutido:

- No re-mandar el artefacto completo en cada ronda. Mandar solo el **delta**: qué findings se
  aplicaron, cuáles se rechazaron y por qué, y pedir una nueva pasada sobre el artefacto
  actualizado. (Si la edición fue grande, incluir el fragmento cambiado.)
- Vía A: `--resume` (→ `task --resume-last`). Vía B: `codex exec resume <thread_id>
  -c sandbox_mode="read-only"` (el override es obligatorio: resume NO hereda el sandbox de la
  sesión — ver la Vía B). Vía C:
  `claude -p --resume <session_id>`. El delta se pasa por stdin con la primitiva de cada shell
  (`<` en POSIX, `Get-Content -Raw | …` en PowerShell — ver "Portabilidad entre shells").
- Si el resume no está disponible en el entorno, degradar a rondas independientes re-enviando el
  artefacto actualizado completo (más caro, pero válido).

**Seed desde co-exploración:** con dos workers hay **dos** sesiones por modo, así que cuál se
reanuda no es una elección libre — la fija la matriz normativa de "Matriz de resume desde
co-exploración", que nunca resuelve a la familia del autor ni a un worker `INVALID`. Si el resume
falla, sesión nueva con los **índices y la síntesis** como contexto: mismo efecto, sin estado.

Con `tool: codex`, este resume es **el tercer punto** donde se reanuda una sesión Codex —junto con
las rondas de esta skill y las de `co-explore`— y necesita exactamente el mismo tratamiento que
los otros dos:

- el override `-c sandbox_mode=read-only` (resume no hereda el sandbox de la sesión original — ver
  la Vía B);
- los cuatro flags de aislamiento, porque la configuración se relee en cada invocación: sin ellos
  este resume vuelve a levantar los MCP, hooks y plugins del usuario aunque la exploración
  original los haya apagado;
- `model` y `effort` **leídos del `session.json`**, no del config: `--ignore-user-config` los
  descarta, y sin repetirlos la crítica seguiría con un modelo distinto del que exploró. Si el
  `session.json` no los trae, se usa el default del CLI y se declara en el eco.

```bash
# POSIX — resume del seed
SEED=<sesión que resuelva la matriz de resume>
SESSION_ID=$(sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$SEED")
MODEL=$(sed -n 's/.*"model"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$SEED")
EFFORT=$(sed -n 's/.*"effort"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$SEED")
echo "seed → ${SESSION_ID:?session.json sin session_id} · modelo ${MODEL:-<default del CLI>}"

set -- exec resume "$SESSION_ID" --ignore-user-config \
       --disable hooks --disable apps --disable plugins \
       -c sandbox_mode=read-only --skip-git-repo-check --json \
       --output-last-message <ruta/al/veredicto.txt>
[ -n "$MODEL" ]  && set -- "$@" -m "$MODEL"
[ -n "$EFFORT" ] && set -- "$@" -c "model_reasoning_effort=$EFFORT"
set -- "$@" -
codex "$@" < <ruta/al/prompt-r1.txt> > <ruta/al/thread-r1.jsonl> 2> <ruta/al/r1.err.txt>
```

```powershell
# PowerShell — resume del seed
$Seed = Get-Content -Raw co-explore\session.json | ConvertFrom-Json
if (-not $Seed.session_id) { throw 'session.json sin session_id' }
"seed → $($Seed.session_id) · modelo $(if ($Seed.model) { $Seed.model } else { '<default del CLI>' })"

$CodexArgs = @('exec','resume',$Seed.session_id,'--ignore-user-config','--disable','hooks',
               '--disable','apps','--disable','plugins','-c','sandbox_mode=read-only',
               '--skip-git-repo-check','--json',
               '--output-last-message','<ruta\al\veredicto.txt>')
if ($Seed.model)  { $CodexArgs += @('-m', $Seed.model) }
if ($Seed.effort) { $CodexArgs += @('-c', "model_reasoning_effort=$($Seed.effort)") }
$CodexArgs += '-'
Get-Content -Raw <ruta\al\prompt-r1.txt> |
  & codex @CodexArgs > <ruta\al\thread-r1.jsonl> 2> <ruta\al\r1.err.txt>
```

Tras el seed, persistir `session-meta.json` en el scratch de esta skill igual que en una ronda 1
normal, para que las rondas siguientes no dependan del `session.json` de otra skill.

## Prompt de revisión

Estructura XML compacta (estilo `gpt-5-4-prompting`: operador, no colaborador). Plantilla base:


El prompt vive en `assets/prompts/review.md` — es la **entrada exacta** del worker y se escribe a archivo con la tool Write. Placeholders que hay que sustituir antes de despachar: `{artifact_type}`, `{complexity}`, `{working_dir}`.


`{foco según tipo}` se completa con la fila correspondiente de "Foco por tipo de artefacto".

Sobre `<constraints>`: las tres prohibiciones evitan que el revisor se disperse —sin ellas, uno
consultó memoria y buscó en la web antes de mirar el artefacto—, pero la cuarta línea es igual de
importante y es lo que impide leerlas de más. Que el artefacto a criticar esté identificado **no**
significa que lo estén los archivos relevantes: cazar reúso ignorado, dependencias no vistas y
efectos colaterales exige leer código, y el contrato de invocación ya define `working_dir` como el
directorio desde el que el revisor puede hacerlo. Solo se reemplaza por una lista cerrada cuando
la llamadora declara explícitamente que su lista es exhaustiva.

## Formato de salida

Pedirle al revisor exactamente esta estructura (fácil de parsear y de loguear):

```
VERDICT: APPROVED | REVISE

FINDINGS:
- [high|medium|low] <título corto del problema>
  why: <por qué importa — qué se rompe / qué falta>
  suggestion: <cambio concreto propuesto>
  refs: <AC-n | sección del artefacto | path:line>
  confidence: <high|medium|low>
```

- `APPROVED` sin findings (o solo con findings `low` opcionales) → corta el loop.
- `REVISE` → hay al menos un finding `high`/`medium` que el revisor considera bloqueante.
- **`confidence` es señal de triage, no un atajo.** Es ortogonal a la severidad: la severidad `[high|medium|low]` es *qué tan grave si es real*; la confianza es *qué tan seguro está el revisor de que lo es*. El árbitro la usa para **priorizar** qué verificar primero y calibrar el escrutinio (un finding `high` con `confidence: low` es «vale la pena mirarlo, pero sin certeza»), nunca para saltarse la verificación de la regla 3 — todo finding se evalúa antes de aplicar. Si el revisor no la emite, tratarla como `medium` y seguir.
- Si la salida no respeta el formato, intentar un parseo tolerante; si no se puede, tratarlo como
  fallo de runtime (degradación).

**Árbitro (lado Claude).** Para cada finding, decidir con `superpowers:receiving-code-review`:
- *Aplicar* — el finding es correcto y relevante → editar el artefacto.
- *Rechazar* — incorrecto, fuera de alcance, o ya cubierto → no tocar, registrar el motivo.
- *Escalar* — disputa genuina o decisión de producto → anotarla para el gate humano.
Nunca aplicar sin entender; nunca descartar sin razón. Todo va al `review-log.md`.

## Foco por tipo de artefacto

| `artifact_type` | Qué debe cazar el revisor |
|---|---|
| `spec` | AC ausentes o no observables/no verificables; alcance ambiguo o contradictorio; objetivo que no se mapea a los AC; casos borde del dominio sin cubrir. |
| `plan` | El enfoque no satisface algún AC; reúso ignorado (reinventa lo que existe); riesgos/efectos colaterales no vistos; pasos de verificación que no prueban realmente el AC. |
| `tasks` | Cobertura AC↔task (AC sin task, task sin AC); tasks no atómicas o no autosuficientes; orden/dependencias mal; falta el test que prueba el AC. |
| `master-spec` | Contratos entre servicios inconsistentes o incompletos; AC `[integration]` mal definidos o no testeables; concerns cross-service faltantes; reparto que deja un AC sin dueño. |
| `reparto` | Algún AC global sin repo que lo cubra; `depends_on` incorrectos/incompletos o con ciclos en el DAG; límites por repo mal trazados; un repo cargado con AC que no le corresponden. |

## Plantilla de review-log.md

Un archivo por corrida, junto al artefacto (`.plans/<id>/review-log.md` en sdd-flow;
`.sdd/<id>/review-log.md` en sdd-orchestrator). Una sección por artefacto revisado; dentro, una
subsección por ronda. Acumulativo (no se pisa entre artefactos del mismo `<id>`).

```markdown
# Cross-review log — <id>

## <artifact_type> (<artifact_path>) — <ISO-8601>
Revisor: <codex-rescue | codex exec | claude -p | …>  ·  modelo: <model de config | CLI default | opus>  ·  max_rounds: <n>

### Ronda 1
**Veredicto del revisor:** REVISE
**Findings:**
- [high] <título>  · confidence: <high|medium|low>
  - why: <…>  · suggestion: <…>  · refs: AC-2
  - **Decisión de Claude:** APLICADO — <qué se cambió y por qué el finding era correcto>
- [medium] <título>  · confidence: <high|medium|low>
  - why: <…>  · suggestion: <…>  · refs: sección "Enfoque"
  - **Decisión de Claude:** RECHAZADO — <razón técnica del rechazo>

### Ronda 2
**Veredicto del revisor:** APPROVED
(sin findings bloqueantes)

### Resultado
Veredicto final: APPROVED en 2 rondas. 1 aplicado, 1 rechazado, 0 disputas abiertas.
Revisor: codex <modelo> (effort <esfuerzo>).

**Límite:** un revisor independiente de otra familia aporta una crítica adicional; sigue siendo
una sola revisión. No prueba correctitud y no reemplaza el gate humano.
```

Si se agotan las rondas sin `APPROVED`, el "Resultado" lista las **disputas abiertas** para que
el humano las arbitre en el gate.

El bloque **Límite** va una vez por corrida, en `Resultado` — no por ronda ni en el veredicto
crudo del revisor. Junto al modelo efectivo (ver "Prechequeos"), es lo que permite leer meses
después con cuánta cobertura se aprobó ese artefacto.

## Configuración

Claves bajo `cross_review` (en `.specify/config.yml` para sdd-flow; en `manifest.yml` para
sdd-orchestrator). Todas opcionales:

```yaml
cross_review:
  mode: auto            # auto (por complejidad) | on | off
  execution: auto       # auto (por capacidad del conductor) | sync | background
  artifacts: [spec, plan, tasks]   # tipos a revisar (orchestrator: [master-spec, reparto])
  max_rounds: 3
  reviewer: auto        # auto (descubre por capacidad; nunca la familia del autor) | claude | codex
```

- `mode: auto` → en sdd-flow: `trivial` off, `normal` opt-in (off salvo pedido), `complex` on.
  En sdd-orchestrator: **on** para `master-spec`/`reparto`, revisados como `complex`.
- `execution: auto` elige por la **capacidad de timeout de exec del conductor** (ver "Latencia y timeout (Claude revisor)"): conductor que puede fijar un tope largo (Claude Code: `Bash` con `timeout` hasta
  600000ms) → **sync** (camino preferido); conductor con exec corto no ampliable (Codex ~120s/comando)
  → **background + poll acotado**. `sync` fuerza una única llamada bloqueante; `background` fuerza el
  poll acotado. En **todos** los modos hay un tope de pared duro: vencido → `UNAVAILABLE` (regla 6),
  nunca espera indefinida.
- `reviewer: auto` aplica la regla anti-misma-familia (ver "Descubrir el revisor"). `claude` |
  `codex` fuerzan la vía; si la forzada coincide con la familia del autor, se avisa y se respeta.
- Precedencia: override conversacional de la corrida > `cross_review` de config > default por
  complejidad. Misma regla que el resto de overrides SDD.
- `max_rounds` chico (2-3) suele alcanzar: los artefactos son chicos comparados con una
  implementación; más rondas dan rendimientos decrecientes.

## Consumo de co-exploración dual

> **Sección inerte hasta el corte.** Nada de lo que sigue está referenciado desde `SKILL.md`
> todavía. Reemplaza al seed desde un `co-explore/session.json` singular, que deja de existir cuando
> `co-explore` despacha dos workers.

### Matriz de resume desde co-exploración

Con dos workers hay **dos** sesiones por modo, una por familia. Cuál se reanuda **no queda a
criterio**: elegir la de la misma familia que el autor violaría la regla 7 —el revisor nunca es de la
familia del autor—, y sería fácil de hacer sin darse cuenta, porque las dos sesiones están ahí y
las dos "funcionan".

| Artefacto a revisar | Sesión que se reanuda | Contexto que recibe |
|---|---|---|
| `spec` · `master-spec` | `explore` de la familia **opuesta al autor** | índices + síntesis |
| `plan` · `reparto` | `counter-plan` de la familia **opuesta al autor** | índices + síntesis |
| `tasks` | **ninguna** sesión de co-explore | índices + síntesis |

Reglas que acotan la matriz:

- **Un worker `INVALID` no es elegible**, aunque su sesión siga siendo reanudable: su informe no
  pasó los predicados, y reanudarlo importaría ese contexto malo a la revisión.
- **Rama 4 o `outcome: map_failure` → ningún contexto de co-explore** y revisor **fresco**. En la
  rama 4 no hubo co-exploración —es el "ninguno" de la regla, nombrado— y el análisis del conductor
  ya está embebido en el artefacto que se va a revisar; pasarlo como "contexto de co-exploración"
  sería etiquetar mal algo que no lo fue.
- **Sin sesión disponible → revisor fresco de la familia opuesta**, con índices y síntesis como
  contexto. **Salvo** que la capacidad actual sea `confirmed_wall`: ahí no hay reintento y el
  resultado es `UNAVAILABLE` terminal. Distinguirlo importa — reintentar contra una pared quema el
  deadline sin ninguna chance de éxito.

**Nunca se pasan los detalles completos.** El contrato de dos capas existe para que el conductor lea
índices y abra detalle solo por disparador; volcarle a la revisión los `detail-*` enteros
reintroduce por la puerta de atrás exactamente el costo que el cambio elimina. Si un finding de la
revisión necesita una entrada concreta, se abre esa entrada por su ID (ver `co-explore/reference.md`
→ "Apertura puntual de una entrada").

**Qué reemplaza.** Donde antes se leía `co-explore/session.json` —una sola sesión, un solo
informe—, ahora se resuelve esta matriz contra el `contributors[]` del envelope. El fallback no
cambia: si el resume falla, sesión nueva con los índices y la síntesis como contexto; mismo efecto,
sin estado.

## Manifest de corrida

Un registro por corrida de una skill cross-model, con lo mínimo para responder **"¿esto me está
sirviendo?"**. Es la sede canónica de las tres: `co-explore` y `cross-implement` apuntan acá y no
duplican el esquema.

No es un log. El log de cada skill cuenta *qué pasó en una corrida* para poder auditarla; el
manifest existe para poder mirar **cien corridas juntas** y decidir si la capacidad se gana su
costo. De ahí que sea chico, plano y uniforme: lo que no se puede comparar entre corridas no vale
la pena registrarlo acá.

### El archivo

```
<repo>/.cross-model/runs/<started_at compacto>-<skill>-<mode>.json
```

Ejemplo: `.cross-model/runs/20260731T140211Z-co-explore-explore.json`

```json
{
  "skill": "co-explore",
  "mode": "explore",
  "started_at": "2026-07-31T14:02:11Z",
  "duration_s": 412,
  "families": ["codex", "claude"],
  "transport": "cli-exec",
  "outcome": "completed",
  "degradation": "branch-3"
}
```

**Un archivo por corrida, nunca uno agregado.** Un JSON acumulado obligaría a leer-modificar-escribir,
y dos corridas concurrentes —una tanda de `sdd-orchestrator` sobre varios repos— se pisarían.
Resolverlo pide locking: exactamente la infraestructura que este manifest existe para no traer. El
timestamp va adelante del nombre para que el orden lexicográfico sea el cronológico.

**Local y untracked, sin autolimpieza**, misma clase que `.plans/` y que los scratch de las tres
skills. El usuario borra el directorio cuando quiera; ninguna skill lo hace por él. Una corrida son
~300 bytes.

**Se escribe con la tool de escritura de archivos del conductor, nunca con `echo` ni heredoc** —
misma regla que los prompts, y por el mismo motivo: el quoting. Por eso acá no hay bloque de
escritura; los bloques verificables son validar y leer.

### Los campos

Los ocho son **obligatorios**. Un campo que solo aparece a veces hace que "no hubo" y "no se supo"
sean el mismo dato ausente.

| Campo | Qué es | De dónde sale |
|---|---|---|
| `skill` | cuál de las tres corrió | fijo por skill |
| `mode` | el modo o `artifact_type` de esta corrida | contrato de invocación |
| `started_at` | ISO-8601 UTC del **despacho** | reloj al lanzar |
| `duration_s` | del despacho a la resolución del outcome | reloj |
| `families` | familias delegadas — **siempre una lista** | topología de la corrida |
| `transport` | la vía efectiva: `subagent` · `cli-exec` · `cli-resume` | vía resuelta al lanzar |
| `outcome` | el estado terminal que la skill ya devuelve | envelope / salida |
| `degradation` | qué se perdió, o `none` | escalera / causa de indisponibilidad |

**`families` es lista incluso cuando hay una sola familia.** Un campo que a veces es cadena y a
veces lista obliga a cada lector a ramificar, y el lector típico es un `grep` apurado.

**`duration_s` mide del despacho a la resolución del outcome**, no la corrida entera de la skill.
Preparar el paquete y arbitrar es trabajo del conductor, no de la capacidad delegada: incluirlo hace
que dos corridas midan cosas distintas según cuánto tardó el conductor en leer. En `co-explore`,
donde el despacho son dos lanzamientos en paralelo, es del primer lanzamiento al último outcome
resuelto — wall clock, no suma.

**`transport` es el del lanzamiento.** Una corrida que arranca con `cli-exec` y reanuda su sesión en
las rondas siguientes sigue siendo `cli-exec`; `cli-resume` es para la corrida que *entera* fue una
reanudación de una sesión ajena.

### El vocabulario es prestado, nunca propio

| Skill | `mode` | `outcome` | `degradation` (además de `none`) |
|---|---|---|---|
| `co-explore` | `explore` · `counter-plan` · `investigate` · `debate` | `completed` · `map_failure` | `branch-2` · `branch-3` · `branch-4` · `confirmed_wall` · `launch_flake` · `runtime_failure` |
| `cross-review` | `spec` · `plan` · `tasks` · `master-spec` · `reparto` · `draft` | `APPROVED` · `REVISE` · `UNAVAILABLE` | `rounds_exhausted` · `confirmed_wall` · `launch_flake` · `runtime_failure` |
| `cross-implement` | `embebido` · `directo` | `IMPLEMENTED` · `PARTIAL` · `UNAVAILABLE` | `takeover` · `confirmed_wall` · `launch_flake` · `runtime_failure` |
| `bitbucket-code-review` | `conductor` · `delegado` · `mixto` | `PUBLISHED` · `PROPOSED` · `UNAVAILABLE` | `revisor_invalido` · `panel_vacio` · `confirmed_wall` · `launch_flake` · `runtime_failure` |

Cada uno de esos términos ya existe en la skill que lo produce: el manifest los **serializa**, no
los define. Un manifest con taxonomía propia se desincroniza del envelope que dice resumir, y cuando
los dos difieren no hay forma de saber cuál miente. Si una corrida termina en un estado que no está
en su fila, lo que falta actualizar es la fila — o el estado es uno que la skill no documenta, y eso
es un hallazgo más valioso que el registro.

### Cuándo se escribe

> **En el punto donde se resuelve el outcome, y todos los caminos de salida pasan por ese punto.**

Es la única regla del manifest que no es de forma, y la que decide si sirve. Un manifest escrito al
cerrar bien una corrida registra **solo éxitos** — y entonces responde "¿esto me está sirviendo?"
con la única muestra incapaz de contestarlo. Las corridas que informan si la capacidad vale son las
que se degradaron, las que vencieron el deadline y las que nunca arrancaron. Una serie de puros
`completed` no dice que la capacidad funciona: dice que se registró cuando funcionó.

En la práctica, **cada estado terminal documentado escribe su manifest**, incluidos los que
devuelven `UNAVAILABLE` antes de despachar nada. Un preflight que choca contra una pared confirmada
es una corrida de duración corta con outcome `UNAVAILABLE`: es un dato, no una no-corrida — y es
justamente el dato que dice que la capacidad no está disponible en este entorno.

### Nunca bloquea

Si la escritura falla —directorio no creable, disco lleno—, la corrida **sigue** y se dice en una
línea: `manifest no escrito: <causa>`. Un registro que puede tumbar una corrida cuesta más de lo que
mide. El aviso no es cortesía: sin él, un directorio mal permisado produce huecos en la serie
indistinguibles de "no corrió", que es la lectura opuesta a la verdadera.

### Qué NO se registra

El recorte es la mitad del diseño. Cada línea de acá existe para que nadie la re-agregue sin
enterarse de por qué se fue:

| Recortado | Por qué |
|---|---|
| `attempts[]` con owner único | era la infraestructura del fallback entre **dos transportes**, que acá no existe: hay una vía por familia y su alternativa está documentada como degradación. El número de rondas ya vive en el log de la skill, que es donde se lo consulta. |
| schema versionado | el conjunto de campos es **fijo**. Versionarlo compra la posibilidad de expandirlo, y expandirlo es salir de "¿esto me sirve?" hacia una telemetría que nadie pidió. El día que haga falta versionar, esa es la señal de que el alcance cambió — y esa decisión se toma explícita, no se hereda de un campo que ya estaba. |
| `usage.source` | atribuía consumo entre suscripción y API. El CLI headless corre sobre la suscripción: no hay costo por corrida que atribuir. |
| parent/child runs | un flujo que corre tres co-exploraciones deja tres archivos con tres timestamps. Correlacionarlos es ordenar por nombre, no un campo más que mantener consistente. |
| `.partial` + rename atómico | protegía una escritura que podía morir a la mitad porque se hacía incremental. Acá el archivo se escribe entero, una vez, cuando ya se conoce el outcome. |

### Activación

```yaml
cross_model:
  schema_version: 1
  manifest:
    mode: "on"     # "on" (default) | "off"  (entre comillas: sin ellas YAML los parsea como booleanos)
```

Vive en `cross_model` —política del **ecosistema**, no de una skill— porque las tres escriben el
mismo registro: apagarlo para una sola produciría una serie con huecos sistemáticos, que es peor que
no tenerla. Esquema completo en `sdd-flow/reference.md` → "Esquema de `.specify/config.yml`".

Default **on**: sin datos, cualquier decisión posterior sobre expandir o recortar el ecosistema es
intuición, y el costo es un archivo de 300 bytes en un directorio untracked.

### Validar un manifest

```bash
# @bloque:manifest-valido
# Predicado: los ocho campos del núcleo presentes, ninguno de los cuatro recortados, families como
# lista, y outcome/degradation dentro del vocabulario de la fila de esa skill.
# Entradas: $manifest
rc=0
for c in skill mode started_at duration_s families transport outcome degradation; do
  grep -q "\"$c\"[[:space:]]*:" "$manifest" || {
    printf 'GUARD:manifest-valido falta el campo "%s"\n' "$c" >&2; rc=1; }
done
for c in attempts schema_version usage parent; do
  grep -q "\"$c\"[[:space:]]*:" "$manifest" && {
    printf 'GUARD:manifest-valido campo recortado presente: "%s"\n' "$c" >&2; rc=1; }
done
grep -qE '"families"[[:space:]]*:[[:space:]]*\[' "$manifest" || {
  printf 'GUARD:manifest-valido "families" no es una lista\n' >&2; rc=1; }
val() { sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" "$manifest" | head -1; }
sk=$(val skill)
comunes="none confirmed_wall launch_flake runtime_failure"
case "$sk" in
  co-explore)      outs="completed map_failure";              degs="$comunes branch-2 branch-3 branch-4" ;;
  cross-review)    outs="APPROVED REVISE UNAVAILABLE";        degs="$comunes rounds_exhausted" ;;
  cross-implement) outs="IMPLEMENTED PARTIAL UNAVAILABLE";    degs="$comunes takeover" ;;
  bitbucket-code-review)
                   outs="PUBLISHED PROPOSED UNAVAILABLE";      degs="$comunes revisor_invalido panel_vacio" ;;
  *) printf 'GUARD:manifest-valido skill fuera del ecosistema: "%s"\n' "$sk" >&2
     rc=1; outs=""; degs="" ;;
esac
for par in "outcome:$outs" "degradation:$degs"; do
  campo=${par%%:*}; permitidos=${par#*:}
  [ -n "$permitidos" ] || continue
  v=$(val "$campo")
  printf '%s\n' "$permitidos" | tr ' ' '\n' | grep -qxF "$v" || {
    printf 'GUARD:manifest-valido %s "%s" no pertenece a %s\n' "$campo" "$v" "$sk" >&2; rc=1; }
done
exit $rc
# @fin:manifest-valido
```

```powershell
# @bloque:manifest-valido-ps
# Predicado: los ocho campos del núcleo presentes, ninguno de los cuatro recortados, families como
# lista, y outcome/degradation dentro del vocabulario de la fila de esa skill.
# Entradas: $manifest
$rc = 0
$m = Get-Content -Raw $manifest
foreach ($c in 'skill','mode','started_at','duration_s','families','transport','outcome','degradation') {
  if ($m -notmatch "`"$c`"\s*:") { Write-Error "GUARD:manifest-valido falta el campo `"$c`""; $rc = 1 }
}
foreach ($c in 'attempts','schema_version','usage','parent') {
  if ($m -match "`"$c`"\s*:") { Write-Error "GUARD:manifest-valido campo recortado presente: `"$c`""; $rc = 1 }
}
if ($m -notmatch '"families"\s*:\s*\[') { Write-Error 'GUARD:manifest-valido "families" no es una lista'; $rc = 1 }
function Val($k) { if ($m -match "`"$k`"\s*:\s*`"([^`"]*)`"") { $Matches[1] } else { '' } }
$sk = Val 'skill'
$comunes = @('none','confirmed_wall','launch_flake','runtime_failure')
switch ($sk) {
  'co-explore'      { $outs = @('completed','map_failure');            $degs = $comunes + @('branch-2','branch-3','branch-4') }
  'cross-review'    { $outs = @('APPROVED','REVISE','UNAVAILABLE');    $degs = $comunes + @('rounds_exhausted') }
  'cross-implement' { $outs = @('IMPLEMENTED','PARTIAL','UNAVAILABLE'); $degs = $comunes + @('takeover') }
  'bitbucket-code-review' { $outs = @('PUBLISHED','PROPOSED','UNAVAILABLE'); $degs = $comunes + @('revisor_invalido','panel_vacio') }
  default { Write-Error "GUARD:manifest-valido skill fuera del ecosistema: `"$sk`""; $rc = 1; $outs = @(); $degs = @() }
}
foreach ($par in @(@('outcome',$outs), @('degradation',$degs))) {
  if ($par[1].Count -eq 0) { continue }
  $v = Val $par[0]
  if ($par[1] -notcontains $v) {
    Write-Error "GUARD:manifest-valido $($par[0]) `"$v`" no pertenece a $sk"; $rc = 1
  }
}
exit $rc
# @fin:manifest-valido-ps
```

### Leer la serie

La pregunta que justifica todo lo anterior. Sin una forma de mirar los datos, el manifest es un
montón de JSON que nadie abre:

```bash
# @bloque:manifest-resumen
# Predicado: por skill, cuántas corridas, cuántas degradadas y la duración mediana; más el total
# leído, para que un directorio vacío se distinga de un filtro que no matcheó.
# Entradas: $runs
n=$(find "$runs" -name '*.json' 2>/dev/null | wc -l | tr -d ' ')
printf 'corridas leídas: %s\n' "$n"
[ "$n" -eq 0 ] && exit 0
t=$(mktemp -d)
for f in "$runs"/*.json; do
  [ -f "$f" ] || continue
  campo() { sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\{0,1\}\([^\",}]*\).*/\1/p" "$f" | head -1; }
  printf '%s\t%s\t%s\n' "$(campo skill)" "$(campo degradation)" "$(campo duration_s)"
done > "$t/filas"
cut -f1 "$t/filas" | sort -u | while IFS= read -r sk; do
  [ -n "$sk" ] || continue
  tot=$(awk -F'\t' -v s="$sk" '$1==s' "$t/filas" | wc -l | tr -d ' ')
  deg=$(awk -F'\t' -v s="$sk" '$1==s && $2!="none"' "$t/filas" | wc -l | tr -d ' ')
  med=$(awk -F'\t' -v s="$sk" '$1==s{print $3}' "$t/filas" | sort -n \
        | awk '{v[NR]=$1} END{if (NR) print v[int((NR+1)/2)]; else print "-"}')
  printf '%s: %s corridas · %s degradadas · mediana %ss\n' "$sk" "$tot" "$deg" "$med"
done
rm -rf "$t"
# @fin:manifest-resumen
```

```powershell
# @bloque:manifest-resumen-ps
# Predicado: por skill, cuántas corridas, cuántas degradadas y la duración mediana; más el total
# leído, para que un directorio vacío se distinga de un filtro que no matcheó.
# Entradas: $runs
$archivos = @(Get-ChildItem -Path $runs -Filter *.json -File -ErrorAction SilentlyContinue)
Write-Output "corridas leídas: $($archivos.Count)"
if ($archivos.Count -eq 0) { exit 0 }
$filas = foreach ($f in $archivos) {
  $j = Get-Content -Raw $f.FullName
  function C($k) { if ($j -match "`"$k`"\s*:\s*`"?([^`",}]*)") { $Matches[1].Trim() } else { '' } }
  [pscustomobject]@{ skill = (C 'skill'); degradation = (C 'degradation'); duration = [int](C 'duration_s') }
}
foreach ($g in ($filas | Group-Object skill | Sort-Object Name)) {
  if (-not $g.Name) { continue }
  $deg = @($g.Group | Where-Object { $_.degradation -ne 'none' }).Count
  $ord = @($g.Group.duration | Sort-Object)
  $med = if ($ord.Count) { $ord[[int](($ord.Count + 1) / 2) - 1] } else { '-' }
  Write-Output "$($g.Name): $($g.Count) corridas · $deg degradadas · mediana $($med)s"
}
# @fin:manifest-resumen-ps
```

### Qué se hace con esto

El manifest no decide nada por sí solo; habilita tres preguntas que hoy se contestan de memoria:

- **¿La capacidad está disponible donde corro?** Una proporción alta de `confirmed_wall` dice que el
  entorno no tiene el CLI de la otra familia, no que la idea sea mala.
- **¿La diversidad se está conservando?** `branch-3` y `branch-4` frecuentes en `co-explore`
  significan que la topología dual se degrada seguido: dos mapas comparados es el supuesto del que
  cuelga todo el valor del modo.
- **¿El peldaño elegido es el más barato que alcanza?** Duraciones medianas por skill contra la
  escalera de rigor (`co-explore/reference.md` → "Escalera de rigor") muestran si se está pagando
  `cross-implement` donde alcanzaba una `cross-review`.
