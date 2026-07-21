# cross-review — Referencia

Detalle operativo de la skill `cross-review`. El `SKILL.md` apunta acá cuando necesita el
contrato de invocación del revisor, la plantilla del prompt, el formato de salida o el foco por
tipo de artefacto.

## Tabla de contenidos

- [Portabilidad entre shells (POSIX / PowerShell)](#portabilidad-entre-shells-posix--powershell)
- [Descubrir el revisor](#descubrir-el-revisor)
- [Invocar al revisor (read-only)](#invocar-al-revisor-read-only)
- [Resume entre rondas](#resume-entre-rondas)
- [Transporte: rama `orca-session` (sesión reutilizada entre rondas)](#transporte-rama-orca-session-sesión-reutilizada-entre-rondas)
- [Prompt de revisión](#prompt-de-revisión)
- [Formato de salida](#formato-de-salida)
- [Foco por tipo de artefacto](#foco-por-tipo-de-artefacto)
- [Plantilla de review-log.md](#plantilla-de-review-logmd)
- [Configuración](#configuración)

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
- **Modelo: no pinear `-m`.** Usar el default de la config: los variants `gpt-5.x-codex`
  devuelven 400 con auth de cuenta ChatGPT. Si el usuario pide un modelo explícito, ese override
  manda.
- **Eco del modelo activo**: leer la línea `model` de `~/.codex/config.toml` (ausente = "CLI
  default") y registrarla en el `review-log.md` junto al revisor, para que la corrida quede
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
  de donde se parsea el thread id), `cross-review/spec-session.txt` (el thread/session id capturado).
- **`review-log.md` NO va acá.** Es el registro auditable consolidado (rondas, findings, decisiones,
  veredicto), hermano de `spec.md`/`plan.md`/`tasks.md`: queda en `<dir del artefacto>/review-log.md`
  (la raíz del flujo).
- **Scratch transitorio, sin autolimpieza.** El `cross-review/` es local y untracked (igual que el
  resto de `.plans/`/`.sdd/`). No se borra solo: el usuario puede eliminarlo cuando quiera. Una nueva
  corrida del mismo artefacto sobrescribe los archivos de las mismas rondas (no crece sin límite).

En la rama `orca-session` ("Transporte: rama `orca-session` (sesión reutilizada entre rondas)" más
abajo) no hay subproceso propio, así que no aplican `-session.txt`/`-thread.jsonl`/`.err.txt`: en su
lugar, `<scratch_dir>/session.json` guarda el objeto `session` reutilizable entre rondas,
`<scratch_dir>/<artifact_type>-raw-r<N>-<nonce>.raw` es el destino único por ronda de `harvest()` y
`<scratch_dir>/<artifact_type>-decisions-r<N>.md` el triage del árbitro de esa ronda. El conductor
combina ambos y promueve (sobrescribiendo) al `review-log.md` estable — nunca se cosecha directo al
acumulativo.

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

- Ronda 1 (prompt escrito antes a archivo — ver regla 2 de "Invocar al revisor"). El prelude
  `MCP_OFF` apaga por override dinámico los MCP del `config.toml` vigente — el revisor no los
  necesita (su contexto viaja en el prompt) y apagarlos ahorra ~la mitad del boot; config
  ausente/ilegible → sin overrides, boot completo (fail-open):
  ```bash
  CODEX_CFG="${CODEX_HOME:-$HOME/.codex}/config.toml"
  # ARRAY, no string: zsh no splitea una variable sin comillas (el string entero llegaba como UN
  # argumento y Codex abortaba); la asignación de array splitea el $() en bash Y zsh:
  MCP_OFF=( $(sed -n 's/^[[:space:]]*\[mcp_servers\.\([A-Za-z0-9_-]*\)[].].*/\1/p' "$CODEX_CFG" 2>/dev/null \
    | sort -u | sed 's/.*/-c mcp_servers.&.enabled=false/') )
  codex exec "${MCP_OFF[@]}" -s read-only -C <working_dir> --skip-git-repo-check --json \
    --output-last-message <ruta/al/veredicto.txt> - < <ruta/al/prompt-r1.txt> \
    > <ruta/al/thread-r1.jsonl>
  # Capturar el thread id del evento thread.started (determinístico, no "buscarlo en la salida"):
  grep -m1 -o '"thread_id":"[^"]*"' <ruta/al/thread-r1.jsonl> | cut -d'"' -f4 \
    > <ruta/al/session.txt>
  ```
  En **PowerShell** (el prompt llega por un pipe en vez de `<`):
  ```powershell
  $CodexCfg = Join-Path $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { "$HOME\.codex" }) 'config.toml'
  $McpOff = @()
  if (Test-Path $CodexCfg) {
    Select-String -Path $CodexCfg -Pattern '^\s*\[mcp_servers\.([A-Za-z0-9_-]+)[\].]' |
      ForEach-Object { $_.Matches[0].Groups[1].Value } | Sort-Object -Unique |
      ForEach-Object { $McpOff += @('-c', "mcp_servers.$_.enabled=false") }
  }
  Get-Content -Raw <ruta\al\prompt-r1.txt> |
    codex exec @McpOff -s read-only -C <working_dir> --skip-git-repo-check --json `
      --output-last-message <ruta\al\veredicto.txt> - > <ruta\al\thread-r1.jsonl>
  (Select-String -Path <ruta\al\thread-r1.jsonl> -Pattern '"thread_id":"([^"]+)"' |
    Select-Object -First 1).Matches.Groups[1].Value > <ruta\al\session.txt>
  ```
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
  `-c sandbox_mode="read-only"` — el read-only del revisor nunca depende de un default:
  El resume arranca un proceso nuevo (vuelve a bootear MCPs): lleva el mismo prelude `MCP_OFF`
  de la ronda 1.
  ```bash
  SESSION_ID=$(cat <ruta/al/session.txt>)
  echo "resume → ${SESSION_ID:?vacío}"   # eco visible + corte si quedó vacío (ver nota --last)
  codex exec resume "$SESSION_ID" "${MCP_OFF[@]}" -c sandbox_mode="read-only" --skip-git-repo-check \
    --output-last-message <ruta/veredicto.txt> - < <ruta/al/delta-rN.txt>
  ```
  En **PowerShell**:
  ```powershell
  $SessionId = (Get-Content <ruta\al\session.txt>).Trim()
  if (-not $SessionId) { throw 'session id vacío' }; "resume → $SessionId"
  Get-Content -Raw <ruta\al\delta-rN.txt> |
    codex exec resume $SessionId @McpOff -c sandbox_mode="read-only" --skip-git-repo-check `
      --output-last-message <ruta\veredicto.txt> -
  ```
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
  pero tarda** (lentitud real del modelo con prompt grande; ver "Latencia y timeout" más abajo).
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

#### Latencia y timeout (Claude revisor)

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

**Seed desde co-exploración:** si existe `co-explore/session.json` (escrito por `co-explore`;
esquema: `{tool, session_id, mode, created_at}`), la Ronda 1 puede **reanudar esa sesión** en
lugar de abrir una nueva — el crítico es el mismo agente que exploró. Con `tool: codex`, ese
resume lleva igualmente el override `-c sandbox_mode="read-only"` (resume no hereda el sandbox
de la sesión original — ver la Vía B). Si el resume falla, abrir
sesión nueva con los `findings-*.md` como contexto: mismo efecto, sin estado.

## Transporte: rama `orca-session` (sesión reutilizada entre rondas)

Alternativa a las Vías A/B/C de arriba ("Invocar al revisor (read-only)"): en vez de un subproceso
headless por ronda, el conductor abre, con la skill-librería `cross-model-orca`, una **sesión
interactiva propia** y la **reutiliza entre rondas** — el equivalente `orca-session` al resume de
la cli — cosechando el transcript de cada ronda. Es **aditiva**: las Vías A/B/C y su mecánica de
rondas/resume/scratch/`VERDICT:` no cambian y siguen siendo el transporte por defecto en cuanto
algo de lo de abajo no se pueda garantizar.

### Resolver transporte (antes de la Ronda 1)

Antes de invocar al revisor (paso 1 de "El loop de revisión" del `SKILL.md`), resolver qué
transporte usar: `override ?? config ?? auto` — algoritmo canónico, no se reimplementa acá, ver
`cross-model-orca/reference.md` → "Resolver de transporte":

- **`override`** — lo que pasa explícito la skill llamadora. `sdd-flow`/`sdd-orchestrator`
  propagan solo su `cross_model.transport.desired` configurado (nunca su propio `effective` ya
  resuelto: cada proceso reevalúa su propia reachability de Orca).
- **`config`** — la clave `cross_model.transport` en `.specify/config.yml` (default `auto` cuando
  la clave no está).
- **`auto`** — `orca-session` si el runtime de Orca es alcanzable **desde el proceso del
  conductor** en este momento y se puede crear o reutilizar una sesión propia; si no, `cli`.

Ante **cualquier** duda — reachability incierta, sesión no verificable como propia, locator
ambiguo — el resultado es `cli`, igual que documenta `co-explore/reference.md` → "Transporte: rama
`orca-session`" para su propio resolver. `cross-review` no necesita justificar `cli`; sí necesita
que las tres condiciones de `orca-session` (Orca alcanzable, sesión propia/reutilizable, perfiles
de las tres capas de control instalados) se cumplan explícitamente.

### Rama `orca-session`

Sustituye, ronda a ronda, la invocación de las Vías A/B/C y su resume. El revisor sigue tan
read-only como en `cli`: solo cambia el transporte, no la regla 1 del `SKILL.md`.

1. **Ronda 1 — crear la sesión propia dedicada.** `createOwnedSession({ family, role:
   'read-only', mode, worktree, ... })` (`cross-model-orca/assets/dispatch-adapter.mjs`), con el
   mismo perfil read-only que usa `co-explore` según la familia del revisor (Codex o Claude — ver
   "Descubrir el revisor" arriba; perfiles completos en
   `cross-model-orca/assets/launch/profiles.md`). A diferencia de `co-explore` (sesión fresca por
   dispatch), `cross-review` **reutiliza esta misma sesión en las rondas siguientes** — el diseño
   de la librería para sesiones propias (`cross-model-orca/reference.md` → "Runtime de sesión vs
   runtime del flujo"). Persistir el objeto `session` devuelto (`uid`, `family`, `role`, `mode`,
   `worktree`, `terminalHandle`, `sessionId`, `transcriptPath`, `createdAt`, `stateDir`) en
   `<scratch_dir>/session.json` (`<scratch_dir>` = `<dir del artefacto>/cross-review/`, la misma
   raíz que ya documenta "Archivos de trabajo (scratch)"). Ese archivo es bookkeeping propio de
   `cross-review`, distinto del registro conductor-only `sessions.json` bajo el `stateDir` de la
   librería (la fuente de verdad de "propia", verificable por `uid`): la copia local es lo que le
   permite a una ronda posterior — corrida como una invocación separada — reconstruir el objeto
   `session` sin volver a preguntarle a Orca.
2. **Armar y despachar el mismo prompt de la ronda, con un `nonce` nuevo.** El prompt es el mismo
   "Prompt de revisión" de abajo — ronda 1 completo, rondas siguientes el delta, ver "Resume entre
   rondas" arriba —, sin cambios. Se despacha con `createDispatch({ session, spec, root })`, que
   genera un `nonce` **nuevo por ronda** (cada ronda necesita el suyo para que el conductor pueda
   cosechar el mensaje de *esta* ronda y descartar los de rondas previas en la misma sesión
   reutilizada) e inyecta por su cuenta la instrucción de cierre (`buildEnvelopeInstructions`).
3. **Sentinel universal de esta rama.** El revisor cierra su turno con su salida normal —"Formato
   de salida" de abajo: `VERDICT: APPROVED | REVISE` + `FINDINGS:` — seguida, como **últimas
   líneas**, del envelope que `createDispatch` ya inyectó:
   ```
   VERDICT: REVISE

   FINDINGS:
   - [high] <título>
     why: <...>
     suggestion: <...>
     refs: AC-2
     confidence: high

   X-CMO: nonce=<..>
   STATUS: done
   ```
   Esto es **solo** en esta rama: las Vías A/B/C siguen cerrando cada ronda solo con `VERDICT:`
   (sin envelope) — el poll de la cli sigue buscando `^VERDICT:`, sin cambios. La razón es la
   cosecha del conductor: `harvest()` necesita el `nonce` para desambiguar la ronda en curso
   dentro de una sesión reutilizada, que a partir de la ronda 2 tiene mensajes de rondas
   anteriores con `nonce` viejo. El `nonce` es solo un token de correlación (texto del modelo,
   falsificable); la autoridad va por el `payload` del `worker_done` (Codex) o por la propiedad de
   la sesión (Claude) — ver `cross-model-orca/SKILL.md` → sección 2 ("Envelope con autoridad") y
   `reference.md` → "Envelope y cosecha crash-idempotente" (párrafo "Correlación vs. autoridad").
   No agregar `taskId`/`dispatchId` al texto.
4. **El revisor no escribe su propio `review-log.md`.** El conductor espera el fin del turno con
   `awaitDone({ session, dispatch, coordinatorHandle, reportPath, root, deadlineMs })`: Codex
   señaliza por `worker_done` (autoridad validada contra el dispatch activo); Claude no lo
   emite — su fin de turno se detecta por la transición `tui-idle` posterior al dispatch. Con
   autoridad confirmada, `awaitDone` llama a `harvest()`
   (`cross-model-orca/assets/harvest-from-transcript.mjs`), que relee el transcript, desambigua
   por `nonce` (`selectAssistantByNonce`, descartando los mensajes de rondas previas) y valida el
   sentinel (`hasSentinel`) antes de persistir — al raw único de esta ronda, no al `review-log.md`
   (ver el punto siguiente). `deadlineMs` usa el mismo presupuesto que ya define "Latencia y
   timeout" para la vía cli (≥5 min `normal`, ~10 min `complex`); si el conductor solo puede
   sostener un exec corto, lanzar la espera en background y pollear, igual que hoy hace el camino
   BACKGROUND de esa sección — la distinción `execution: sync | background` es ortogonal al
   transporte.
5. **Cosecha a un raw único por ronda, luego reconstruir y promover el `review-log.md`
   (CRÍTICO).** `harvest()` exige que `reportPath` sea un destino **inexistente**
   (`checkContainment` + `writeExclusive` con `wx`, ver `cross-model-orca/reference.md` →
   "Contención robusta y promoción atómica"). El `review-log.md` es, en cambio, un destino
   **acumulativo estable** — crece ronda a ronda e incluye también las decisiones del árbitro —,
   así que **nunca** es el `reportPath` que recibe `awaitDone`: un `wx` sobre un archivo que ya
   existe (a partir de la ronda 2) fallaría siempre. En cambio:
   a. `harvest()` cosecha al raw único de esta ronda, dentro de `<scratch_dir>`, con un nombre que
      combina el número de ronda y el `nonce` para que nunca colisione ni entre rondas ni entre
      reintentos de la misma corrida:
      `<scratch_dir>/<artifact_type>-raw-r<N>-<nonce>.raw` (p. ej.
      `cross-review/plan-raw-r2-3f9a1c...raw`). El número de ronda solo no alcanza: una corrida
      repetida sobre el mismo artefacto reutilizaría el mismo `r<N>` y el `wx` fallaría contra el
      raw de la corrida anterior.
   b. El árbitro (Claude) registra su triage de esa ronda — aplicado/rechazado/escalado por
      finding, con el rationale (regla 3 del `SKILL.md`) — en
      `<scratch_dir>/<artifact_type>-decisions-r<N>.md`: el mismo contenido que, en la vía cli, hoy
      se escribe directo dentro de `review-log.md`.
   c. El **conductor** reconstruye el `review-log.md` completo: por cada ronda ya cosechada
      (1..N), combina su raw (veredicto + findings del revisor) con su archivo de decisiones,
      siguiendo la estructura de "Plantilla de review-log.md" abajo; escribe el resultado a un
      temporal en `<dir del artefacto>/` y lo **promueve con `rename` atómico** sobre
      `review-log.md`, sobrescribiendo cualquier versión previa — mismo patrón que documenta
      `cross-model-orca/reference.md` para destinos acumulativos. El `review-log.md` sigue
      viviendo donde ya lo documenta "Archivos de trabajo (scratch)" arriba: hermano del
      artefacto, nunca dentro de `cross-review/`.
   d. Son dos eventos de promoción distintos, no uno. La FSM con `dedupKey =
      ${dispatchId}:${nonce}` ya quedó en `promoted` en el paso 4, dentro de `awaitDone`,
      apenas `harvest()` escribió el raw de esta ronda (con el hash del raw, no del
      review-log) — esa marca es el dedup de la **cosecha del raw**, automática, y ya sucedió
      antes de que el conductor empiece la reconstrucción de acá. La promoción del
      `review-log.md` es un evento **separado y posterior**, a cargo del conductor: no reusa
      esa FSM ni tiene una propia (`cross-model-orca/reference.md` → "Contención robusta y
      promoción atómica" documenta esto como contrato pendiente para cada skill acumulativa,
      no como función ya codificada). Su idempotencia viene enteramente de que el `rename` es
      atómico y de que el contenido se reconstruye por completo desde los raws inmutables: si
      el proceso cae después del `rename`, un retry vuelve a reconstruir desde los mismos raws
      y llega al mismo contenido — sin duplicar rondas, sin necesitar un `markPromoted` propio
      (mecanismo genérico descrito en "El hueco post-rename/pre-promoted" de
      `cross-model-orca/reference.md`, aplicado acá a un canónico multi-raw).
6. **Rondas siguientes — reutilizar la sesión.** En vez de `createOwnedSession`, releer
   `<scratch_dir>/session.json`, confirmar que el `uid` sigue registrado como propio en el
   `stateDir` del conductor (`cross-model-orca/reference.md` → "Runtime de sesión vs runtime del
   flujo") y pasar ese mismo objeto `session` a un nuevo `createDispatch` (paso 2, con su propio
   `nonce`). **Nunca** se reutiliza una sesión ajena — una abierta por el usuario o por otro
   flujo (privacidad v1, `cross-model-orca/SKILL.md` → sección 6): si el `uid` no está registrado,
   o el registro no confirma que sigue siendo la misma sesión (mismo `terminalHandle`), crear una
   sesión fresca (volviendo al paso 1) o degradar a `cli`.
7. **Ante falla del revisor, `recover`.** `recover({ session, dispatch })` interrumpe (`terminal
   send --interrupt`) y confirma idle (`terminal wait --for tui-idle`) antes de dar la sesión por
   recuperable. Rol `read-only`: idle confirmado alcanza — no hay riesgo de doble escritor. Si
   `recover` no confirma, o el locator del transcript resulta ambiguo, o la sesión no se puede
   garantizar propia → **degradar a `cli`** para el resto del loop (nunca redespachar por
   `orca-session` sobre una sesión ya comprometida).

### Degradación a `cli`

Explícita, sin cambio de comportamiento observable: si el resolver da `cli`, o si algo de la rama
de arriba falla — Orca no alcanzable, runtime `stale_bootstrap`, locator del transcript ambiguo,
sesión no verificable como propia (fresca o reutilizada), falta el binario de Orca/de la otra
familia, o un MCP requerido por el perfil —, se corre la vía cli de siempre (Vía A/B/C, "Invocar
al revisor (read-only)" arriba): mismo prompt, mismo "Formato de salida", mismo `review-log.md`.
La llamadora nunca queda bloqueada por la ausencia de Orca — degrada y sigue, igual que hoy
degrada ante la ausencia de un binario o MCP (regla 6 del `SKILL.md`, "Degradación").

### Portabilidad

Los comandos de lanzamiento (POSIX + PowerShell, por familia, rol y modo atendido/desatendido)
están completos en `cross-model-orca/assets/launch/profiles.md` — no se copian acá.
`dispatch-adapter.mjs` invoca `orca` con `spawnSync('orca', args, { encoding: 'utf8' })` (arreglo
de argv, sin `shell: true`): no hereda el problema de quoting de un prompt en markdown que sí
afecta a `codex exec`/`claude -p` en la vía cli (ver "Portabilidad entre shells (POSIX /
PowerShell)" arriba).

### Read-only preservado

La rama `orca-session` es tan read-only como la cli: el revisor lee el artefacto y el código del
`working_dir`, critica, pero no edita nada (regla 1 del `SKILL.md`) — la garantía cambia de
mecanismo (sandbox/toolset cerrado de la sesión Orca en vez de `-s read-only`/`--allowedTools` del
subproceso), no de invariante. Quien aplica los findings sigue siendo Claude, editando el
artefacto fuera de esta sesión.

## Prompt de revisión

Estructura XML compacta (estilo `gpt-5-4-prompting`: operador, no colaborador). Plantilla base:

```xml
<task>
Eres un revisor adversarial independiente. Critica el siguiente artefacto de Spec-Driven
Development de tipo "{artifact_type}" ANTES de que se implemente. Es una revisión de SOLO
LECTURA: no modifiques archivos. Puedes leer el código del repo en {working_dir} para fundamentar,
pero no edites nada. Tu objetivo es cazar problemas que cuesten caro después: {foco según tipo}.
</task>

<artifact>
{contenido inline del artefacto}
</artifact>

<context>
{contenido de los context_paths relevantes: spec/plan relacionados, master-spec, AC y contratos}
Complejidad declarada: {complexity}.
</context>

<grounding_rules>
- Ancla cada finding a una sección/AC/línea concreta del artefacto o del código. No inventes.
- Si algo es hipótesis (no lo pudiste verificar en el repo), dilo explícitamente.
- No comentes estilo, wording ni formato. Foco en correctitud, completitud y riesgo.
</grounding_rules>

<structured_output_contract>
{ver "Formato de salida" — respetar ese formato exacto}
</structured_output_contract>

<dig_deeper_nudge>
No te quedes en lo superficial. Busca el AC que falta, el caso borde no cubierto, el supuesto
no declarado, la dependencia no vista, el contrato que no cierra. Si no encuentras nada serio,
APRUEBA — no inventes findings para parecer productivo.
</dig_deeper_nudge>
```

`{foco según tipo}` se completa con la fila correspondiente de "Foco por tipo de artefacto".

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
```

Si se agotan las rondas sin `APPROVED`, el "Resultado" lista las **disputas abiertas** para que
el humano las arbitre en el gate.

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
- `execution: auto` elige por la **capacidad de timeout de exec del conductor** (ver "Latencia y
  timeout"): conductor que puede fijar un tope largo (Claude Code: `Bash` con `timeout` hasta
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
