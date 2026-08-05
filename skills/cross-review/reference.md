# cross-review — Referencia

Detalle operativo de la skill `cross-review`. El `SKILL.md` apunta acá cuando necesita el
contrato de invocación del revisor, la plantilla del prompt, el formato de salida o el foco por
tipo de artefacto.

## Tabla de contenidos

- [Documentos de esta referencia](#documentos-de-esta-referencia)
- [Portabilidad entre shells (POSIX / PowerShell)](#portabilidad-entre-shells-posix--powershell)
- [Descubrir el revisor](#descubrir-el-revisor)
- [Invocar al revisor (read-only)](#invocar-al-revisor-read-only)
- [Resume entre rondas](#resume-entre-rondas)
- [Prompt de revisión](#prompt-de-revisión)
- [Formato de salida](#formato-de-salida)
- [Ingesta y arbitraje](#ingesta-y-arbitraje)
- [Tandas y salida de rondas](#tandas-y-salida-de-rondas)
- [Checkpoint durable](#checkpoint-durable)
- [Foco por tipo de artefacto](#foco-por-tipo-de-artefacto)
- [Plantilla de review-log.md](#plantilla-de-review-logmd)
- [Configuración](#configuración)
- [Manifest de corrida](#manifest-de-corrida)

---

## Documentos de esta referencia

La referencia de esta skill son **tres** archivos, partidos por el momento en que se los lee, no por
tamaño. Cargar los otros dos en toda corrida gastaría contexto en las corridas que no los usan:

| Archivo | Qué trae | Cuándo se lee |
|---|---|---|
| `reference.md` (este) | portabilidad entre shells, descubrimiento e invocación del revisor, resume entre rondas, prompt, formato de salida, foco por tipo de artefacto, latencia y topes, matriz de resume y manifest | en toda corrida |
| `ciclo-de-vida.md` | identidad del finding, estados y transiciones, ledger append-only y su esquema, presupuestos, vara de admisión de la defensa, cierre y adopción de logs legacy | ante la **primera salida conforme que traiga al menos un finding**, cualquiera sea el veredicto |
| `transporte-herdr.md` | el adaptador del transporte por panes: activación, perfil de permisos, entradas y salidas, independencia, deadline, continuidad entre rondas, validación del artefacto y cleanup | **solo** cuando la activación del flujo resolvió a la vía de panes |

**El predicado de `ciclo-de-vida.md` es literal y no se parafrasea.** No es "al primer rechazo": la
ingesta —identidad, dedup, ledger y veredicto derivado— ya está gobernada por ese contrato, así que
hace falta aunque el conductor aplique o escale todo y no rechace nada. Y no es "al primer `REVISE`
con findings": este contrato admite `APPROVED` con findings `low` opcionales, y esa corrida también
lo necesita. Una corrida que termina en `APPROVED` **sin** findings no lo carga.

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
  de dentro de una tabla, que aplica a otro contexto y no a la raíz.

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

##### Las causas de la indisponibilidad, y la que no lo es

`UNAVAILABLE` no viaja solo: lleva una **causa** de un enum cerrado, compartido con las skills
hermanas, porque de ella depende qué se hace después. Son cuatro, y ninguna es un estado terminal
nuevo — todas acompañan al que la skill ya devuelve:

| Causa | Qué la produce | Qué habilita |
|---|---|---|
| `confirmed_wall` | binario ausente, auth rechazada, versión incompatible | nada: terminal para la corrida |
| `launch_flake` | el binario existe pero el lanzamiento flaqueó | 2-3 reintentos con backoff corto |
| `runtime_failure` | arrancó bien y falló ejecutando: error, salida no parseable | reintento por-intento |
| `deadline_exceeded` | arrancó bien y venció el tope de pared —`poll_deadline` o `timeout` del exec— sin `VERDICT:` | subir el presupuesto, no reintentar igual |

**`deadline_exceeded` es una causa, no un estado.** Hasta acá el deadline vencido se registraba como
`runtime_failure`, que sugiere una falla de infraestructura que no ocurrió: el revisor arrancó bien y
el corte lo puso el conductor al fijar el tope. La palanca que corresponde es distinta —subir el tope
o bajar de modelo, como dice "Diagnóstico y palancas"—, y con un solo literal para las dos no había
cómo elegirla leyendo la serie de manifests.

**`transport_fallback` es la quinta causa y no es causa de `UNAVAILABLE`.** Registra que la corrida se
despachó por un transporte que no era el que se había resuelto, y la corrida puede terminar
`APPROVED`: es una causa de la **corrida**, no de una indisponibilidad. Sus cinco reglas son
normativas para las tres skills que la emiten:

1. **El literal es `transport_fallback`, y no otro.** Es un valor de enum compartido por tres
   productores: dejarlo como "una causa propia de cada skill" habilita literales incompatibles que
   igual cumplirían la intención. Se nombra por el **mecanismo** y no por el producto —no
   `herdr_unavailable`— para que un transporte futuro no obligue a agregar un valor más.
2. **El disparador se define por resultado, no por dónde falló.** Intención resuelta a la vía de
   panes **+** transporte efectivo CLI despachado ⇒ `transport_fallback`, sin importar si la vía cayó
   en el preflight de capacidad o en el lanzamiento. Sin esa regla, una implementación lo registraría
   desde el preflight y otra solo tras un lanzamiento fallido, y las dos se creerían correctas.
3. **`transport` guarda la vía que efectivamente corrió**, no la que se intentó: en un fallback es la
   del CLI. Las dos juntas son el par que hace legible la serie — el transporte real más el hecho de
   que hubo fallback. Sin la causa, esa corrida sería indistinguible de una CLI intencional.
4. **La causa raíz concreta —pared confirmada, flake de lanzamiento— queda en el log de la skill**, no
   en el manifest. El manifest guarda el hecho comparable entre corridas; el diagnóstico se consulta
   en el log, que es donde ya se lo busca.
5. **Excepción — resultado incierto: no hay fallback.** Si el intento por la vía de panes quedó en
   estado incierto (no se sabe si el agente sigue vivo), **no hay fallback** hasta resolver el
   recovery. Despachar por CLI sobre un intento que quizá siga corriendo produce dos escritores sobre
   las mismas rutas de salida, que es peor que no tener revisión.

##### `recovery-required` bloquea retry y fallback

La excepción de arriba nombra el estado; esta subsección lo define, porque es acá —donde se fija el
deadline— donde se toma la decisión que lo produce.

Un intento de revisión cuyo resultado es **incierto** —no se sabe si el revisor dejó salida, si la
dejó a medias, si su proceso sigue vivo— no cae en `UNAVAILABLE` ni en ningún veredicto: queda en
`recovery-required`, que es estado del **intento de transporte**, no un veredicto. Mientras no se
resuelva **no habilita ni retry ni fallback**: ni otra ronda contra el mismo revisor, ni el despacho
de la misma revisión por el otro transporte.

**Vencer el deadline no prueba que el proceso dejó de trabajar.** No es una precaución teórica: se
observó lo contrario — una espera venció con los agentes todavía produciendo y los informes llegaron
válidos **después** de que la corrida ya se había degradado. El deadline es el corte que el conductor
se pone a sí mismo para dejar de esperar, y `deadline_exceeded` registra esa decisión suya: ninguno de
los dos es una señal que le llegue al revisor ni una prueba de que terminó.

**Las rutas de salida fijas no protegen contra un revisor tardío.** Completa el veredicto de una
corrida ya degradada sobre la ruta que la ronda siguiente va a leer, y una crítica de la ronda 1 pasa
por crítica de la ronda 2 sin que nada la delate: el formato es el correcto y el archivo está entero.
De ahí las dos consecuencias — cada intento escribe en **rutas exclusivas**, y no se despacha por el
otro transporte hasta cerrar el recovery, que es la excepción de `transport_fallback`.

**Esto no bloquea el gate.** Al gate lo libera el estado terminal con su aviso de degradación, como
fija "Estados terminales que liberan el gate". `recovery-required` bloquea el reintento y el fallback;
no agrega una casilla de espera antes de presentar.

##### Callback o poll: el segundo predicado, una vez en `background`

`execution` sigue siendo un enum **cerrado de tres valores** (`auto | sync | background`), y los
defaults de las tres skills cross-model están en un solo lugar: `co-explore/reference.md` →
"Latencia y deadlines". El de `cross-review` es `auto` en todos sus modos. Lo que se agrega acá no es
un valor más sino la mitad que faltaba de la decisión.

**Elegir `background` no dice cómo se espera.** Hacen falta **dos** predicados distintos: que el
conductor pueda fijar un timeout de exec largo **no demuestra** que el host lo vuelva a invocar
cuando el comando en background termina. La secuencia completa es, en este orden: `execution: auto`
elige `sync` o `background` por el predicado de timeout de exec de los dos caminos de arriba
—auto → sync con tope largo disponible, auto → background sin él—; y **ya dentro de `background`**,
un segundo predicado, el de **re-invocación durable**, elige entre **callback** y el **poll acotado**
de "Camino BACKGROUND". Un `background` pedido a mano saltea el primer paso, no el segundo.

**Condición de verdad, positiva.** El predicado de re-invocación durable es verdadero **solo** cuando
el contrato documentado del host **garantiza** volver a invocar al conductor al completar un comando
en background. La **ausencia de garantía —no solo una garantía en contra— lo vuelve falso**; un host
que no documenta el comportamiento cuenta como falso.

**La continuidad la aporta el harness, no el transporte.** El multiplexor de terminales aloja el
proceso; despertar al conductor cuando el comando termina es del **host** que lo corre. Alojar
procesos bien no vuelve verdadero el predicado.

**Falla cerrado.** Con el predicado en falso, `background` **falla cerrado al poll acotado de hoy**:
el `poll_deadline`, el contador de iteraciones y el `UNAVAILABLE` con causa `deadline_exceeded` al
vencer, tal como quedan definidos arriba. El invariante no se toca: ningún camino espera indefinida.

##### Estados terminales que liberan el gate

La revisión corre **antes** del gate humano de la llamadora y, en `background`, puede seguir corriendo
cuando el artefacto ya está listo para presentar. De ahí dos fallas simétricas: presentar el gate
antes de que la crítica vuelva —y contar una aprobación dada sin ella— o **no presentarlo nunca**
porque la revisión falló de un modo que nadie previó. La primera la cierra la llamadora marcando el
gate mientras la revisión está pendiente (`sdd-flow/SKILL.md` → "Revisión cross-model"); la segunda la
cierra esta tabla: hay **cinco observables terminales y los cinco liberan el gate**, sin una sexta
casilla en la que quedarse esperando.

| Observable | Qué se presenta |
|---|---|
| **veredicto cosechado y validado** — parseado al formato estructurado y triado | el gate **con** la crítica incorporada: es el único que aporta findings |
| **deadline vencido** sin el marcador de cierre | el gate **igual**, con el aviso de degradación de una línea (`UNAVAILABLE` · `deadline_exceeded`) |
| **bloqueo no resuelto** — esperó una aprobación interactiva y no se destrabó dentro de su deadline | el gate **igual**, con el aviso de degradación (`UNAVAILABLE` · `deadline_exceeded`, que es lo que ocurrió) |
| **artefacto ausente** — terminó sin dejar salida en la ruta acordada, o dejó una que no se puede parsear ni con parseo tolerante | el gate **igual**, con el aviso de degradación (`UNAVAILABLE` · `runtime_failure`) |
| **indisponibilidad** — no se pudo lanzar, o arrancó y falló ejecutando, con cualquiera de sus causas | el gate **igual**, con el aviso de degradación |

**No son estados nuevos: son observables de estados que ya existen.** La tabla no agrega un veredicto
ni una causa —los enums siguen cerrados y son los de arriba—; nombra **qué se ve** y a qué casilla ya
definida cae, que es lo que faltaba para poder afirmar que la cobertura es total. Un bloqueo **vivo**
no figura acá porque no es terminal: es la *ausencia* de observable, y es justo el caso que cubre la
marca del gate. Y el `recovery-required` de un intento de transporte con resultado incierto tampoco es
una sexta casilla de espera: bloquea el retry y el fallback, no el gate, que se presenta con el aviso.

**Lo que libera el gate es el estado terminal, no haber cerrado el pane.** Conservar un pane para
inspección —lo que ya se hace con un bloqueo, un deadline vencido o una salida ilegible— es compatible
con presentar el gate: son dos decisiones independientes y ninguna espera a la otra. Un pane vivo no
es un observable pendiente; esperar a cerrarlo antes de presentar reintroduciría exactamente el
cuelgue que esta tabla elimina.

## Resume entre rondas

El loop reusa el **mismo thread del revisor** para que tenga memoria de lo ya discutido:

- No re-mandar el artefacto completo en cada ronda. Mandar solo el **delta**, y pedir una nueva
  pasada sobre el artefacto actualizado. (Si la edición fue grande, incluir el fragmento cambiado.)

  **El delta se proyecta exclusivamente desde el ledger; no se redacta por separado.** Es una
  proyección, no un resumen escrito a mano: una sola fuente hace imposible que lo registrado y lo
  comunicado difieran. El registro de identidad de cada finding provee además el contenido con que
  el revisor evalúa el rechazo — sin el tema y sus anclas, las filas del ledger le dan el evento
  pero no con qué juzgarlo.

  Lo que el delta lleva por cada finding vivo: su ID, su estado actual, el evento que lo llevó ahí,
  el rationale del rechazo si lo hubo, y el tema con sus anclas. Y **la lista explícita de IDs
  rechazados sobre los que se espera respuesta** — es lo que el prompt de ronda N convierte en su
  bloque de respuestas obligatorias.
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

Sobre la calibración de longitud en `<grounding_rules>`: acota la prosa de `why`/`suggestion`
—que se persiste en el `review-log.md` y se relee en cada ronda—, y lleva pegada la salvaguarda de
que **no** toca el número de findings. La salvaguarda no es adorno: pedirle brevedad a un revisor
es indistinguible de pedirle que sea conservador, y un revisor conservador reporta menos, que es
justo lo contrario de lo que compra esta skill. El diseño ya separa las dos cosas —el revisor emite
todo con `severidad` y `confidence`, y el filtrado ocurre en un pase aparte, el triage del
conductor—, así que la línea solo tiene que no romper esa separación.

Por el mismo motivo, el `<dig_deeper_nudge>` **no** le dice al revisor cuándo aprobar. Antes cerraba
con "si no encuentras nada serio, APRUEBA", que eran dos instrucciones pegadas: una anti-alucinación
—legítima— y un empujón a reportar menos. El empujón además era **redundante**: el criterio de
aprobación ya está normado en "Formato de salida" (`APPROVED` sin findings, o solo con `low`
opcionales, corta el loop), que es donde vive. Repetirlo en el nudge no agregaba una regla, agregaba
un sesgo — y un revisor al que se le pide moderación reporta menos, que es lo contrario de lo que
esta skill compra. Queda la mitad que sí hace falta: un finding que no se puede anclar no se emite.

## Formato de salida

Pedirle al revisor exactamente esta estructura (fácil de parsear y de loguear). **Ronda 1:**

```
VERDICT: APPROVED | REVISE

FINDINGS:
- [high|medium|low] <título corto del problema>
  proposed_id: <ID propuesto por el revisor para este tema>
  why: <por qué importa — qué se rompe / qué falta>
  suggestion: <cambio concreto propuesto>
  refs: <AC-n | sección del artefacto | path:line>
  confidence: <high|medium|low>

STATUS: done
```

**Ronda N (con rechazos que responder): dos bloques separados**, con reglas de validación distintas:

```
VERDICT: APPROVED | REVISE

RESPUESTAS A RECHAZOS:
- <ID>: ACEPTO | DEFIENDO
  argumento: <si defiende, el argumento nuevo; si acepta, una línea>

FINDINGS NUEVOS:
- [high|medium|low] <título corto del problema>
  proposed_id: <ID propuesto>
  why: … · suggestion: … · refs: … · confidence: …

STATUS: done
```

- **`proposed_id` va en todo finding nuevo, con la ronda 1 incluida** — ahí todos lo son. El
  conductor lo valida, normaliza y deduplica: propone el revisor, asigna el conductor
  (`ciclo-de-vida.md` → "Identidad").
- **Un finding genuinamente nuevo en una ronda tardía es comportamiento esperado del loop, no una
  anomalía.** En corridas reales el valor escaló con las rondas en vez de agotarse. Una regla que
  invalide la salida por traer un ID desconocido mataría esa propiedad.
- `APPROVED` sin findings (o solo con findings `low` opcionales) → corta el loop.
- `REVISE` → hay al menos un finding `high`/`medium` que el revisor considera bloqueante.
- **El revisor debe emitir `REVISE` si defiende algún rechazo:** una defensa sin evaluar es, por
  definición, algo sin resolver.

### Señal de cierre

La salida termina con una **marca final**, y el predicado es el mismo que valida `co-explore` para
sus informes —**aparece exactamente una vez y como última línea no vacía**—: se cita por puntero
(`co-explore/reference.md` → "Formato de dos capas"), no se reescribe.

**La conformidad se juzga solo sobre salida completa.** El marcador de apertura del bloque no
alcanza: con dos bloques, distinguir "omitió una respuesta" de "no llegó a escribirla" es imposible
sin una marca final.

**La causa se asigna por lo que efectivamente pasó, no por la ausencia de marca:**

| Qué se observó | Causa |
|---|---|
| venció el tope de pared y no hay marca | `deadline_exceeded` |
| el proceso **terminó** y entregó salida ausente, incompleta o sin marca válida | `runtime_failure` |

Confundirlas elige la palanca de recuperación equivocada: subir el tope no arregla un revisor que
entrega mal.

### Validación por bloque

La regla **no** es global — es distinta en cada bloque, y confundirlas rompe una de las dos
propiedades:

| Bloque | Qué invalida | Qué es normal |
|---|---|---|
| **respuestas a rechazos** | un ID esperado **omitido**, **duplicado**, o un ID **desconocido** | — |
| **findings nuevos** | — | un `proposed_id` que el conductor no conoce: pasa por asignación, unicidad y dedup |

Una salida no conforme entra en la degradación vigente: **parseo tolerante** y, si no recupera el
bloque exacto, **`runtime_failure`**. Y entonces **ningún bloque de esa salida se arbitra** —
descartar el bloque roto y seguir con los findings nuevos arbitraría una salida cuya integridad ya
falló.

**La omisión nunca cierra nada.** Un finding se cierra solo por aceptación explícita del revisor o
por una defensa evaluada como inadmisible (`ciclo-de-vida.md` → "Cierre"). La aceptación silenciosa
permitiría cerrar findings por truncamiento en vez de por una decisión auditable.
- **`confidence` es señal de triage, no un atajo.** Es ortogonal a la severidad: la severidad `[high|medium|low]` es *qué tan grave si es real*; la confianza es *qué tan seguro está el revisor de que lo es*. El árbitro la usa para **priorizar** qué verificar primero y calibrar el escrutinio (un finding `high` con `confidence: low` es «vale la pena mirarlo, pero sin certeza»), nunca para saltarse la verificación de la regla 3 — todo finding se evalúa antes de aplicar. Si el revisor no la emite, tratarla como `medium` y seguir.
- Si la salida no respeta el formato, intentar un parseo tolerante; si no se puede, tratarlo como
  fallo de runtime (degradación).

## Ingesta y arbitraje

**El orden de procesamiento es normativo**, no una sugerencia:

1. **Validar** los dos bloques (ver "Validación por bloque"). Si la salida no es conforme, no se
   arbitra nada.
2. **Asignar identidad y deduplicar por tema** los findings nuevos — antes de cualquier arbitraje
   (`ciclo-de-vida.md` → "Identidad").
3. **Arbitrar** las respuestas a rechazos: evaluar cada defensa contra la vara de admisión.
4. **Arbitrar** los findings nuevos.
5. **Derivar** el veredicto del estado del ledger.

**Árbitro (lado Claude).** Para cada finding, decidir con `superpowers:receiving-code-review`:
- *Aplicar* — el finding es correcto y relevante → editar el artefacto → `aplicado`.
- *Rechazar* — incorrecto, fuera de alcance, o ya cubierto → no tocar, **registrar el motivo** →
  `rechazado`. Un rechazo sin motivo es un estado inválido, no un default.
- *Escalar* — disputa genuina o decisión de producto → `en-disputa`, para el gate humano.

Y para cada defensa recibida: *admisible* → `reabierto` y **se re-arbitra**; *inadmisible* →
`cerrado`. Una defensa admisible obliga a re-arbitrar, **no** a aceptar.

Nunca aplicar sin entender; nunca descartar sin razón. Todo va al ledger del `review-log.md`.

### Veredicto derivado

**El veredicto de la corrida se deriva del ledger, no del bloque del revisor.** Con dos bloques, un
revisor puede emitir `DEFIENDO F-01`, cero findings nuevos y `APPROVED` porque el bloque de findings
quedó vacío — y un loop que corte ahí no arbitraría nunca esa defensa.

| Estado del ledger tras arbitrar | Veredicto | Efecto sobre la tanda |
|---|---|---|
| todos los findings en `aplicado` o `cerrado` | `APPROVED` | corta: convergió |
| existe al menos uno en estado **no terminal** | `REVISE` | sigue: hay margen de resolución |
| solo terminales, pero con ≥1 `en-disputa` | `REVISE` | **corta la tanda** y abre el gate humano |

El predicado no admite dos lecturas para un mismo ledger. El `APPROVED` del revisor **no corta el
loop por sí solo** si quedan defensas sin evaluar; y a la inversa, tras un arbitraje que no deja nada
abierto la corrida converge **sin** gastar otra ronda para confirmarlo.

*Por qué la tercera fila corta:* una disputa es terminal por definición — ninguna ronda adicional
puede resolverla, porque su destino es el arbitraje humano. Seguir gastando la tanda sobre un ledger
que solo tiene disputas es desperdicio puro.

## Tandas y salida de rondas

Agotar el presupuesto **no cierra la revisión**: abre un **checkpoint** donde decide el humano. Una
**tanda** son `max_rounds` rondas (default 3); las tandas son **sucesivas y finitas**, y **ninguna se
concede sin autorización explícita**. No existe un modo que corra hasta `APPROVED` sin tope.

### Qué consume ronda

La ronda que obtiene del revisor su `ACEPTO | DEFIENDO` **sí** cuenta dentro de la tanda: es trabajo
del revisor y arbitraje del conductor. Lo que **no** consume ronda es el finding ya `cerrado` — no
genera arbitraje ni obliga a abrir una ronda por él. Tampoco los eventos del complemento, que se
descartan con motivo.

### Rechazos sin responder al agotarse la tanda

Un finding rechazado en la **última ronda** de una tanda no alcanzó a tener su oportunidad de
defensa. Su destino está **fijado, no es elegible**:

| Salida del checkpoint | Destino de los pendientes |
|---|---|
| el humano **concede** una tanda | siguen `rechazado`, esperando respuesta en la tanda nueva |
| el humano **no concede** | pasan a **`en-disputa`** — nunca a `cerrado` |

*Por qué `en-disputa` y no `cerrado`:* cerrarlo sería cerrarlo por agotamiento del presupuesto y no
por una decisión sobre su mérito — el revisor nunca pudo responder. `en-disputa` lo deja donde el
humano del gate puede arbitrarlo.

**En las dos salidas el checkpoint escribe dos clases de fila en el ledger, no una:** una
`transicion` **por cada finding pendiente** —con su origen, destino, ronda, actor, decisión y
rationale— **más** una `control-corrida` con `evento_corrida: checkpoint`, `finding_id` nulo y la
`decision_humana` elegida. Los dos errores simétricos rompen la auditoría: registrar solo la
`control-corrida` no deja traza de **qué** rechazos se procesaron; registrar solo las `transicion`
pierde **qué opción** abrió o cerró la tanda.

### Las cuatro opciones del checkpoint

Sin solapamiento, cada una con postcondición fijada sobre **tres ejes**:

| Opción | Artefacto | Revisión | Pendientes sin respuesta |
|---|---|---|---|
| **continuar así** (aprobar pese al `REVISE`) | aprobado, el flujo sigue | cerrada | → `en-disputa`, registrados |
| **conceder una tanda** | sin resolver, el gate no se cierra | continúa una tanda, y vuelve a preguntar | siguen `rechazado`, esperan respuesta |
| **seguir hasta `APPROVED`** | sin resolver, el gate no se cierra | continúa **sin volver a preguntar** hasta `APPROVED` o hasta el tope total | siguen `rechazado`, esperan respuesta |
| **cerrar la revisión** | **sin aprobar**, el flujo no sigue | cerrada | → `en-disputa`, registrados |

Ningún par comparte los tres ejes: "continuar así" y "cerrar" difieren en el artefacto (una lo
aprueba, la otra no); "conceder una tanda" y "seguir hasta `APPROVED`" difieren en si el humano
vuelve a decidir. **"Cerrar la revisión" es una salida adicional** —para cuando la revisión dejó de
rendir pero el artefacto no convence—, nunca un reemplazo de "seguir hasta `APPROVED`".

**Las cuatro se ofrecen siempre**, incluso cuando el dato de retorno avisa que conceder no puede
converger: ese dato **advierte, no deshabilita** (ver `SKILL.md` → "Salida").

### "Seguir hasta `APPROVED`" y su tope total

Concede tandas **automáticamente**, sin volver a preguntar, hasta que ocurra **uno** de tres cortes:

| Corte | Qué pasa |
|---|---|
| el veredicto derivado es `APPROVED` | la revisión converge y cierra |
| se alcanza el **tope total** | vuelve al checkpoint con las cuatro opciones |
| el predicado derivado da `REVISE` con **solo disputas** | **corte anticipado obligatorio**: vuelve al checkpoint aunque falten rondas |

El tercero no es opcional: ninguna ronda puede resolver una disputa, así que seguir sería gastar el
tope sin posibilidad de converger.

**Mientras el modo esté activo y queden rondas hasta el tope, el límite de tanda es una frontera
interna:** la barrera del gate **permanece marcada** y el fin de tanda **no** abre checkpoint. Se
libera en los tres cortes de la tabla, y solo ahí. Sin esa frontera, el modo automático preguntaría
en cada agotamiento y sería idéntico a "conceder una tanda".

**El tope se captura en la opción, no en el config.** Al elegir este modo el humano fija el límite
**acumulado** de rondas de la corrida; el **default sugerido es determinista**: `consumido + 2 ×
max_rounds` (con `max_rounds` en 3, seis rondas más). Una **reelección** tras alcanzarlo aplica la
misma fórmula sobre lo consumido hasta ese momento, de modo que siempre resulta **absoluto y mayor**;
un valor ≤ consumido se rechaza, porque volvería al checkpoint de inmediato.

Cada elección o reelección deja una fila `control-corrida` con su `tope_efectivo`, para que el corte
sea auditable: un tope que vive solo en memoria no se puede reconstruir después. **No se agrega clave
al bloque `cross_review`**: fuera de este modo no gobernaría nada.

*La regla 2 se conserva:* sigue sin existir un loop sin límite. Lo que cambia es **quién** autoriza
cada tramo — una vez al inicio en vez de tanda a tanda.

### Dónde no se pregunta

Donde **no hay forma de presentar un gate humano**, no se pregunta: se agota, se cierra en `REVISE`
con las disputas abiertas y se escala. La excepción se funda en la **capacidad de presentar un
gate**, y **no** en `execution` ni en el transporte — `execution: background` solo decide cómo se
espera al revisor, y su gate humano sigue existiendo — ni en el fan-out de Fase 2 del orquestador,
que corre con `cross_review.mode: off` y por lo tanto no tiene revisión que gobernar. Los gates de
Fase 1 del orquestador **sí** son interactivos.

## Checkpoint durable

Una corrida con checkpoint humano puede abarcar días y varias sesiones. Para que una **sesión nueva**
descubra que hay una revisión abierta y la rehidrate en vez de arrancar otra, el checkpoint persiste
un **descriptor por `run_id`**:

| Campo | Qué guarda |
|---|---|
| `run_id` | el de la corrida, estable entre tandas |
| `ledger` | la ruta del `review-log.md` y la sección de esta corrida |
| `ronda_acumulada` | la última ronda completada |
| `tope_vigente` | el `tope_efectivo` de la última `control-corrida`, si el modo automático está activo |
| `causa_corte` | `tanda_agotada` \| `solo_disputas` |
| `gate_pendiente` | qué STOP quedó esperando decisión |
| `revisor` | la referencia de sesión o pane con que reanudar |

Se **escribe al abrir el checkpoint** y se **retira al terminal** de la corrida.

**Quién lo consulta, por modo:** en **embebido**, el `resume` de la llamadora, **antes** de iniciar
otra revisión; en **directo** y **draft**, `cross-review` misma, que es quien presenta. En los tres,
una corrida abierta se **rehidrata**: no se inicia otra, no se recargan presupuestos y no se toma el
scratch de otra corrida.

**Frontera declarada:** es local y untracked como el resto de `.plans/`, así que sobrevive entre
sesiones **en la misma copia del directorio**, no entre máquinas ni entre checkouts.

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
Revisor: <codex-rescue | codex exec | claude -p | …>  ·  modelo: <model de config | CLI default | opus>
run_id: <estable en toda la corrida, incluidas las tandas siguientes>  ·  max_rounds: <n> (por tanda)

### Registro de identidad
Solo lo que no cambia. Las transiciones apuntan acá.

| ID | Tema (ubicación semántica + problema/causa) | Anclas |
|---|---|---|
| F-01 | plantilla del log · el ledger no distingue emisión de transición | `reference.md:794` |

### Ledger (append-only — ninguna fila se sobrescribe)

| Ronda | ID | tipo | evento | actor | decisión / campos | rationale |
|---|---|---|---|---|---|---|
| 1 | F-01 | emision | — | revisor | severidad: high | — |
| 1 | F-01 | transicion | rechaza con motivo | conductor | abierto → rechazado · presupuesto: null | <razón> |
| 2 | F-01 | transicion | defiende, con presupuesto | revisor | rechazado → defendido · presupuesto: defensa | <argumento> |
| 2 | F-01 | transicion | evalúa: admisible | conductor | defendido → reabierto · presupuesto: null | <por qué el argumento es nuevo> |
| 2 | F-02 | descarte | re-emite uno cerrado | revisor | — | <motivo del descarte> |
| 3 | — | control-corrida | checkpoint | humano | decision_humana: conceder una tanda | <lo que dijo> |

### Proyección (derivada — se regenera al cierre de cada ronda, nunca se edita)

| ID | Estado | Severidad vigente | Defensa | Re-apertura |
|---|---|---|---|---|
| F-01 | reabierto | high | consumida | disponible |
| F-02 | cerrado | medium | consumida | disponible |

### Resultado

**Eventos de arbitraje** (qué escrutinio hubo): aplicados <n> · rechazados <n> ·
defensas recibidas <n> · defensas admisibles <n>.
**Estados terminales** (dónde quedó cada finding): aplicado <n> · cerrado <n> · en-disputa <n>.

Veredicto final: <APPROVED | REVISE> en <n> rondas y <n> tanda(s).
Revisor: codex <modelo> (effort <esfuerzo>).

**Límite:** un revisor independiente de otra familia aporta una crítica adicional; sigue siendo
una sola revisión. No prueba correctitud y no reemplaza el gate humano.
```

**Las dos familias de conteo del `Resultado` van separadas, y las dos son obligatorias.** Los
**eventos** miden el escrutinio; los **estados terminales**, el desenlace. Un rechazo que después se
corrigió cuenta como evento y no desaparece del conteo — si solo se listaran los estados finales, una
corrida de "18 hallazgos, 0 rechazos" sería indistinguible de una con escrutinio real, que es
exactamente lo que este bloque existe para hacer legible de un vistazo.

**Ledger y proyección no son dos vistas intercambiables.** El ledger es la única sede de escritura;
la proyección se **regenera** al cierre de cada ronda desde el fold de todas las entradas hasta esa
ronda **inclusive** —la última transición incluida— y nunca se edita a mano. Una proyección que se
regenera solo al final de la tanda, o que excluye la última transición, deja el log una transición
atrás justo cuando se lo consulta para armar el delta.

Esquema completo de las cuatro clases de fila y sus campos: `ciclo-de-vida.md` → "Ledger".

Si se agota una tanda sin `APPROVED`, el "Resultado" lista las **disputas abiertas** y los
**rechazos sin responder** para que el humano decida en el gate (ver "Tandas y salida de rondas").

**Logs escritos con el formato anterior.** Un `review-log.md` que ya existe sin ledger ni IDs es
**historial opaco e inmutable**: no se migra, no se sobrescribe y **se excluye del fold**. La corrida
nueva abre su propia sección identificada por formato y `run_id`, y ninguna identidad se infiere de
lo viejo. Una corrida legacy no terminal se termina con el contrato anterior. Detalle y fundamento en
`ciclo-de-vida.md` → "Adopción de logs escritos con el formato anterior".

El bloque **Límite** va una vez por corrida, en `Resultado` — no por ronda ni en el veredicto
crudo del revisor. Junto al modelo efectivo (ver "Prechequeos"), es lo que permite leer meses
después con cuánta cobertura se aprobó ese artefacto.

## Configuración

Claves bajo `cross_review` (en `.specify/config.yml` para sdd-flow; en `manifest.yml` para
sdd-orchestrator). Todas opcionales:

```yaml
cross_review:
  mode: auto            # auto (por complejidad) | "on" | "off"  (entre comillas: sin ellas YAML los parsea como booleanos)
  execution: auto       # auto (por capacidad del conductor) | sync | background
  artifacts: [spec, plan, tasks]   # tipos a revisar (orchestrator: [master-spec, reparto])
  max_rounds: 3         # rondas POR TANDA, no de la corrida entera; al agotarse se abre el checkpoint
  reviewer: auto        # auto (descubre por capacidad; nunca la familia del autor) | claude | codex
```

- `mode: auto` → en sdd-flow: `trivial` off, `normal` opt-in (off salvo pedido), `complex` on.
  En sdd-orchestrator: **on** para `master-spec`/`reparto`, revisados como `complex`.
- `execution: auto` elige por la **capacidad de timeout de exec del conductor** (ver "Latencia y timeout (Claude revisor)"): conductor que puede fijar un tope largo (Claude Code: `Bash` con `timeout` hasta
  600000ms) → **sync** (camino preferido); conductor con exec corto no ampliable (Codex ~120s/comando)
  → **background + poll acotado**. `sync` fuerza una única llamada bloqueante; `background` fuerza el
  poll acotado. En **todos** los modos hay un tope de pared duro: vencido → `UNAVAILABLE` (regla 6),
  nunca espera indefinida. Ese predicado resuelve **solo** entre `sync` y `background`; una vez en
  `background`, callback o poll lo decide un segundo predicado (ver "Callback o poll: el segundo
  predicado, una vez en `background`"). Los defaults de las tres skills viven en
  `co-explore/reference.md` → "Latencia y deadlines"; el de `cross-review` es `auto`.
- `reviewer: auto` aplica la regla anti-misma-familia (ver "Descubrir el revisor"). `claude` |
  `codex` fuerzan la vía; si la forzada coincide con la familia del autor, se avisa y se respeta.
- Precedencia: override conversacional de la corrida > `cross_review` de config > default por
  complejidad. Misma regla que el resto de overrides SDD.
- **`max_rounds` es el presupuesto de una tanda, no el tope de la corrida.** Al agotarse se le
  pregunta al humano, y si concede, la corrida sigue con otra tanda de `max_rounds` rondas. La
  **numeración del ledger acumula a lo largo de toda la corrida**: una segunda tanda arranca en la
  ronda 4, no en la 1. Lo que la regla 2 garantiza es que **el loop nunca corre sin tope**, no que la
  corrida entera tenga ≤ `max_rounds` rondas (ver "Tandas y salida de rondas").
- `max_rounds` chico (2-3) suele alcanzar por tanda: los artefactos son chicos comparados con una
  implementación; más rondas seguidas dan rendimientos decrecientes, y si hacen falta, se conceden.

## Consumo de co-exploración dual

Reemplaza al seed desde un `co-explore/session.json` singular, que deja de existir cuando
`co-explore` despacha dos workers.

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

**Su hermano en vuelo es el sobre de corrida delegada, definido en `corridas-en-vuelo.md`.** El
manifest vive en `.cross-model/runs/` y registra corridas **terminadas**; el sobre vive en
`.cross-model/active/` y registra las que se están **ejecutando ahora**. La relación entre los dos es
de posta, y en un solo punto del tiempo: **el sobre se retira cuando el manifest se escribe**. Si el
terminal deja algo pendiente —una salida sin adjudicar, un recurso propio en pie—, lo que se demora
es el retiro del sobre y nunca la escritura del manifest. El sobre además es **obligatorio** y no lo
apaga `mode: "off"`: esa clave apaga la telemetría, no la continuidad del trabajo en vuelo.

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

**Una corrida de `cross-review` con varias tandas escribe UN solo manifest.** Se escribe **una vez,
al outcome terminal de la corrida**, tal como ya lo define este contrato — y con tandas el terminal
es el **último**: un checkpoint intermedio **no** escribe manifest, ni parcial ni provisorio (este
esquema no admite estados intermedios ni `.partial + rename`).

**Quién lo finaliza es la llamadora, no `cross-review`:** al devolver el control en un checkpoint,
`cross-review` todavía no sabe si habrá otra tanda. La llamadora sí lo sabe apenas el humano decide,
así que es ella quien cierra el manifest tras el gate cuando la opción elegida es terminal.

`started_at` es el del **primer** despacho de la corrida, y `duration_s` sigue siendo **wall clock
hasta el outcome terminal**, tal como lo fija este contrato para las tres skills — lo que con tandas
**incluye la espera en el gate humano**. Se acepta a propósito: excluirla obligaría a cambiar la
definición canónica de `duration_s` de las tres, y lo que este campo mide es cuánto tarda la
capacidad en devolver un resultado utilizable, espera humana incluida.

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
| `transport` | la vía efectiva: `subagent` · `cli-exec` · `cli-resume` · `herdr` | vía resuelta al lanzar |
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
| `co-explore` | `explore` · `counter-plan` · `investigate` · `debate` | `completed` · `map_failure` | `branch-2` · `branch-3` · `branch-4` · `confirmed_wall` · `launch_flake` · `runtime_failure` · `deadline_exceeded` · `transport_fallback` |
| `cross-review` | `spec` · `plan` · `tasks` · `master-spec` · `reparto` · `draft` | `APPROVED` · `REVISE` · `UNAVAILABLE` | `rounds_exhausted` · `confirmed_wall` · `launch_flake` · `runtime_failure` · `deadline_exceeded` · `transport_fallback` |
| `cross-implement` | `embebido` · `directo` | `IMPLEMENTED` · `PARTIAL` · `UNAVAILABLE` | `takeover` · `confirmed_wall` · `launch_flake` · `runtime_failure` · `deadline_exceeded` · `transport_fallback` |
| `bitbucket-code-review` | `conductor` · `delegado` · `mixto` | `PUBLISHED` · `PROPOSED` · `UNAVAILABLE` | `revisor_invalido` · `panel_vacio` · `confirmed_wall` · `launch_flake` · `runtime_failure` |

Cada uno de esos términos ya existe en la skill que lo produce: el manifest los **serializa**, no
los define. Un manifest con taxonomía propia se desincroniza del envelope que dice resumir, y cuando
los dos difieren no hay forma de saber cuál miente. Si una corrida termina en un estado que no está
en su fila, lo que falta actualizar es la fila — o el estado es uno que la skill no documenta, y eso
es un hallazgo más valioso que el registro.

**La vía de panes es vocabulario prestado como cualquier otro.** Cuando `cross-review` despacha su
revisor en un pane de un multiplexor de terminales en vez de por CLI headless, el valor que emite es
`transport: herdr`; la semántica no se mueve —mismos modos, mismos outcomes, misma matriz de
resume—, solo cambia por dónde viaja el prompt. `bitbucket-code-review` **no** emite ese valor: no
delega a través de las tres skills que lo producen, y su fila no se amplía. La sintaxis del
multiplexor no es asunto de esta skill: la autoridad es la skill externa `herdr` y el binario
instalado.

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
# lista, y outcome, degradation y transport dentro del vocabulario de la fila de esa skill.
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
# `deadline_exceeded` y `transport_fallback` NO van en "comunes": ese conjunto lo comparten las
# cuatro filas, y meterlas ahí las filtraría a bitbucket-code-review, que no delega a través de las
# tres skills que las producen. Se suman fila por fila, solo en esas tres.
case "$sk" in
  co-explore)      outs="completed map_failure"
                   degs="$comunes branch-2 branch-3 branch-4 deadline_exceeded transport_fallback"
                   trans="subagent cli-exec cli-resume herdr" ;;
  cross-review)    outs="APPROVED REVISE UNAVAILABLE"
                   degs="$comunes rounds_exhausted deadline_exceeded transport_fallback"
                   trans="subagent cli-exec cli-resume herdr" ;;
  cross-implement) outs="IMPLEMENTED PARTIAL UNAVAILABLE"
                   degs="$comunes takeover deadline_exceeded transport_fallback"
                   trans="subagent cli-exec cli-resume herdr" ;;
  bitbucket-code-review)
                   outs="PUBLISHED PROPOSED UNAVAILABLE";      degs="$comunes revisor_invalido panel_vacio"
                   trans="subagent cli-exec cli-resume" ;;
  *) printf 'GUARD:manifest-valido skill fuera del ecosistema: "%s"\n' "$sk" >&2
     rc=1; outs=""; degs=""; trans="" ;;
esac
for par in "outcome:$outs" "degradation:$degs" "transport:$trans"; do
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
# lista, y outcome, degradation y transport dentro del vocabulario de la fila de esa skill.
# Entradas: $manifest
$rc = 0
$m = Get-Content -Raw $manifest
# Los operadores van en su variante case-sensitive (`-cmatch`, `-cnotmatch`, `-cnotcontains`,
# `switch -CaseSensitive`) porque el par POSIX compara con `grep`/`case`/`grep -qxF`, que distinguen
# mayúsculas. Con los operadores por defecto de .NET, `Started_at` cuenta como el campo `started_at`
# y `HERDR` como el transporte `herdr`.
foreach ($c in 'skill','mode','started_at','duration_s','families','transport','outcome','degradation') {
  if ($m -cnotmatch "`"$c`"\s*:") { Write-Error "GUARD:manifest-valido falta el campo `"$c`""; $rc = 1 }
}
foreach ($c in 'attempts','schema_version','usage','parent') {
  if ($m -cmatch "`"$c`"\s*:") { Write-Error "GUARD:manifest-valido campo recortado presente: `"$c`""; $rc = 1 }
}
if ($m -cnotmatch '"families"\s*:\s*\[') { Write-Error 'GUARD:manifest-valido "families" no es una lista'; $rc = 1 }
function Val($k) { if ($m -cmatch "`"$k`"\s*:\s*`"([^`"]*)`"") { $Matches[1] } else { '' } }
$sk = Val 'skill'
$comunes = @('none','confirmed_wall','launch_flake','runtime_failure')
# 'deadline_exceeded' y 'transport_fallback' NO van en $comunes: ese conjunto lo comparten las cuatro
# filas, y meterlas ahí las filtraría a bitbucket-code-review, que no delega a través de las tres
# skills que las producen. Se suman fila por fila, solo en esas tres.
switch -CaseSensitive ($sk) {
  'co-explore'      { $outs = @('completed','map_failure')
                      $degs = $comunes + @('branch-2','branch-3','branch-4','deadline_exceeded','transport_fallback')
                      $trans = @('subagent','cli-exec','cli-resume','herdr') }
  'cross-review'    { $outs = @('APPROVED','REVISE','UNAVAILABLE')
                      $degs = $comunes + @('rounds_exhausted','deadline_exceeded','transport_fallback')
                      $trans = @('subagent','cli-exec','cli-resume','herdr') }
  'cross-implement' { $outs = @('IMPLEMENTED','PARTIAL','UNAVAILABLE')
                      $degs = $comunes + @('takeover','deadline_exceeded','transport_fallback')
                      $trans = @('subagent','cli-exec','cli-resume','herdr') }
  'bitbucket-code-review' { $outs = @('PUBLISHED','PROPOSED','UNAVAILABLE'); $degs = $comunes + @('revisor_invalido','panel_vacio')
                      $trans = @('subagent','cli-exec','cli-resume') }
  default { Write-Error "GUARD:manifest-valido skill fuera del ecosistema: `"$sk`""
            $rc = 1; $outs = @(); $degs = @(); $trans = @() }
}
foreach ($par in @(@('outcome',$outs), @('degradation',$degs), @('transport',$trans))) {
  if ($par[1].Count -eq 0) { continue }
  $v = Val $par[0]
  if ($par[1] -cnotcontains $v) {
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
  function C($k) { if ($j -cmatch "`"$k`"\s*:\s*`"?([^`",}]*)") { $Matches[1].Trim() } else { '' } }
  [pscustomobject]@{ skill = (C 'skill'); degradation = (C 'degradation'); duration = [int](C 'duration_s') }
}
$grupos = @($filas | Group-Object skill -CaseSensitive)
# El orden lo fija `[StringComparer]::Ordinal` y no `Sort-Object`: el par POSIX ordena con `sort`
# bajo colación por bytes, donde `Cross-Review` precede a `cross-review`. `Sort-Object` compara por
# cultura y devuelve el orden inverso para ese par — también con `-CaseSensitive`, que decide qué
# strings son iguales pero no con qué comparador se ordenan.
$nombres = [string[]]@($grupos.Name)
[array]::Sort($nombres, [StringComparer]::Ordinal)
foreach ($nombre in $nombres) {
  if (-not $nombre) { continue }
  $g = @($grupos | Where-Object { $_.Name -ceq $nombre })[0]
  $deg = @($g.Group | Where-Object { $_.degradation -cne 'none' }).Count
  $ord = @($g.Group.duration | Sort-Object)
  # `[Math]::Floor` y no `[int]`: con cardinalidad par el índice medio cae en .5, y `[int]` aplica
  # redondeo bancario —`[int]1.5` es 2— así que devolvía el MAYOR de los dos centrales donde el
  # `int()` de awk trunca y devuelve el menor. La mediana definida es el menor.
  $med = if ($ord.Count) { $ord[[int][Math]::Floor(($ord.Count + 1) / 2) - 1] } else { '-' }
  Write-Output "$($nombre): $($g.Count) corridas · $deg degradadas · mediana $($med)s"
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
