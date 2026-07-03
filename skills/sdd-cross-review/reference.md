# sdd-cross-review — Referencia

Detalle operativo de la skill `sdd-cross-review`. El `SKILL.md` apunta acá cuando necesita el
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
| Sondear env (redirección) | `env \| grep -iE 'ANTHROPIC_…'` | `Get-ChildItem Env: \| Where-Object Name -match 'ANTHROPIC_…'` |
| Correr un hijo con env de redirección removida | `env -u VAR … cmd` | `powershell -NoProfile -Command { Remove-Item Env:VAR…; cmd }` (proceso hijo aislado) |

> **`uuidgen` falta en Git Bash de Windows** (solo está en macOS/Linux). Si se corre la Vía C por
> Git Bash en Windows, usar el fallback `powershell -NoProfile -Command "[guid]::NewGuid().ToString()"`,
> o que el agente genere un UUID v4 y lo pase como literal a `--session-id`.

Las reglas invariantes de "Invocar al revisor" valen en **ambos** shells: read-only siempre, y el
prompt **se escribe a archivo con la tool Write** (nunca inline ni `echo`/heredoc); solo cambia la
primitiva con que ese archivo llega a stdin (`<` en POSIX, `Get-Content -Raw | …` en PowerShell).

---

## Descubrir el revisor

Esta sección es la **fuente canónica** del descubrimiento: `sdd-co-explore` la referencia por
puntero (su fallback embebido es un resumen de esto).

Los nombres de tools/MCP/agentes cambian entre entornos. Resolver el revisor por **capacidad**
(un segundo modelo que pueda **criticar texto en read-only**) con una regla dura por delante:

> **El revisor nunca es de la misma familia de modelos que el autor.** El autor del artefacto es
> el **modelo de respaldo** que ejecuta el agente que conduce la skill, no el CLI ni el harness.
> Un revisor de la misma familia comparte los puntos ciegos del autor: los errores correlacionados
> que la cross-review existe para romper.

> **El CLI/harness ≠ la familia del modelo.** Claude Code puede estar **redirigido** a un proveedor
> Anthropic-compatible (GLM/z.ai, Kimi, DeepSeek, MiniMax…) vía `ANTHROPIC_BASE_URL` +
> `ANTHROPIC_DEFAULT_*_MODEL`. En ese caso el binario es `claude` y el harness dice "You are Claude
> Code", pero el modelo real es otro. **No confiar en esa autopercepción** — la única señal
> confiable es el entorno.

**Paso 1 — identificar el harness conductor.** Claude Code, Codex CLI u otro (lo indica el runtime).

**Paso 2 — desambiguar el modelo de respaldo (solo si el conductor es Claude Code).** Sondear el
entorno antes de decidir la familia:

```bash
# POSIX (macOS/Linux/Git Bash):
env | grep -iE 'ANTHROPIC_BASE_URL|ANTHROPIC_DEFAULT_(OPUS|SONNET|HAIKU)_MODEL|ANTHROPIC_MODEL'
```
```powershell
# PowerShell (Windows):
Get-ChildItem Env: | Where-Object Name -match 'ANTHROPIC_BASE_URL|ANTHROPIC_DEFAULT_(OPUS|SONNET|HAIKU)_MODEL|ANTHROPIC_MODEL'
```

Interpretación (genérica, no hardcodear un proveedor): si `ANTHROPIC_BASE_URL` apunta a un host
**distinto de `api.anthropic.com`/`anthropic.com`**, **o** algún `ANTHROPIC_DEFAULT_*_MODEL` /
`ANTHROPIC_MODEL` mapea a un modelo **no-`claude-*`** (`glm-*`, `kimi-*`, `deepseek-*`, `minimax-*`,
`qwen-*`, …) → la **familia del autor es ese modelo de respaldo** (ej. "GLM/z.ai"), NO Claude. Si la
sonda sale vacía o el base_url es Anthropic → autor = Claude real.

> Si el conductor es **Codex CLI** (u otro que no sea Claude Code), saltear el Paso 2: el autor es
> GPT/Codex (o el que corresponda) directo. La sonda de `ANTHROPIC_*` no define la identidad del
> autor cuando el conductor no es Claude Code.

**Paso 3 — elegir revisor de OTRA familia** (`reviewer: auto`):

| Familia del autor (modelo de respaldo) | Revisor a buscar | Cómo detectarlo | Vía de invocación |
|---|---|---|---|
| Claude real (Claude Code, sin redirección) | Codex | ¿Existe el subagente `codex:codex-rescue` (plugin codex)? Si no, ¿`command -v codex`? | Vía A (preferida) o Vía B |
| GPT/Codex (Codex CLI) | Claude | ¿`command -v claude`? | Vía C |
| **Modelo de respaldo en Claude Code redirigido** (GLM/Kimi/…) | Codex **o** Claude real (ambos ≠ familia del autor) | Codex: subagente/`command -v codex`. Claude real: `command -v claude` **+ Vía C con env limpio** | `auto`→ Codex (Vías A/B, sin líos de env); `reviewer: claude`→ Vía C **con higiene de env** |
| Otra | El primero de familia distinta | `command -v codex`, `command -v claude`, u otro subagente/CLI disponible | B, C o adaptada |

> **En PowerShell** la detección de binarios es `Get-Command codex -ErrorAction SilentlyContinue`
> (ídem `claude`) en vez de `command -v` — ver "Portabilidad entre shells (POSIX / PowerShell)".

Con `reviewer: claude` o `reviewer: codex` forzados en config, ir directo a esa vía. **El aviso de
"misma familia / se pierde el valor cross-model" se dispara solo si la vía forzada coincide con el
modelo de respaldo real**, no con el CLI. Ejemplos:
- Claude Code redirigido a GLM + `reviewer: claude` → la Vía C con env limpio llega a Claude real,
  que **sí** es otra familia que GLM: cross-model legítimo, **sin** aviso.
- Claude Code redirigido a GLM + `reviewer: codex` → Codex es otra familia: válido, sin aviso.
- Claude real + `reviewer: claude` → misma familia → avisar y continuar (el override manda).

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
  sdd-pr-feedback) o `.sdd/<id>/cross-review/` (sdd-orchestrator), sin lógica especial por skill.
  Crearlo antes de la ronda 1.
- **Nomenclatura**: `<artifact_type>-<tipo>-r<N>.txt`. El prefijo por `artifact_type` evita
  colisiones entre los gates de `spec`/`plan`/`tasks`. Ejemplos:
  `cross-review/spec-prompt-r1.txt`, `cross-review/spec-verdict-r1.txt`,
  `cross-review/plan-delta-r2.txt`, `cross-review/plan-verdict-r2.txt`,
  `cross-review/plan-r1.err.txt`, `cross-review/spec-session.txt`.
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

Patrón (igual que grill-me-codex). Flags verificados con `codex-cli` 0.137–0.139; pueden variar
por versión, así que ante la duda confirmar con `codex exec --help`. Descubrir por capacidad, no
hardcodear ciegamente.

- Ronda 1 (prompt escrito antes a archivo — ver regla 2 de "Invocar al revisor"):
  ```bash
  codex exec -s read-only -C <working_dir> --skip-git-repo-check \
    --output-last-message <ruta/al/veredicto.txt> - < <ruta/al/prompt-r1.txt>
  ```
  En **PowerShell** (el prompt llega por un pipe en vez de `<`):
  ```powershell
  Get-Content -Raw <ruta\al\prompt-r1.txt> |
    codex exec -s read-only -C <working_dir> --skip-git-repo-check `
      --output-last-message <ruta\al\veredicto.txt> -
  ```
  `-s read-only` (= `--sandbox read-only`) garantiza que no escribe; `-C` fija el working root;
  `--skip-git-repo-check` permite correr aunque la contenedora no sea repo git;
  `--output-last-message` deja el mensaje final (el veredicto + findings) en un archivo, fácil de
  parsear; el `-` como PROMPT hace que las instrucciones se lean de **stdin** (verificado en
  `codex exec --help`). Codex reporta el **session id** en su salida — capturarlo (o usar
  `--last` en el resume).
- Rondas siguientes (mismo thread): el subcomando `resume` **no** acepta `-s`/`--sandbox` ni
  `--color` ni `-C` (hereda el sandbox read-only y el cwd de la sesión original):
  ```bash
  codex exec resume --last --skip-git-repo-check \
    --output-last-message <ruta/veredicto.txt> - < <ruta/al/delta-rN.txt>
  # o con id explícito: codex exec resume <SESSION_ID> --skip-git-repo-check ... - < <delta>
  ```
  En **PowerShell**:
  ```powershell
  Get-Content -Raw <ruta\al\delta-rN.txt> |
    codex exec resume --last --skip-git-repo-check --output-last-message <ruta\veredicto.txt> -
  # o con id explícito: … | codex exec resume <SESSION_ID> --skip-git-repo-check … -
  ```
  **`--last` filtra por cwd:** elige la sesión más reciente *del directorio actual* (el `--all`
  desactiva ese filtro). Correr el resume desde el mismo `working_dir` de la ronda 1 (en
  PowerShell, `Push-Location <working_dir>` antes), **o** usar el `<SESSION_ID>` explícito (más
  robusto: no depende del cwd ni de cuál fue la última sesión global). Verificado end-to-end en
  codex-cli 0.139.
- Opcional: `--output-schema <archivo.json>` fuerza el shape del mensaje final a un JSON Schema
  (útil para hacer el "Formato de salida" todavía más parseable).

### Vía C — CLI `claude -p` (Claude como revisor; cuando el autor es GPT/Codex, otra familia, o un modelo de respaldo en Claude Code redirigido)

`claude` no tiene un flag de sandbox equivalente a `codex -s read-only`: el read-only se
garantiza **restringiendo las tools permitidas a las de lectura**
(`--allowedTools=Read,Grep,Glob`; en modo `-p` no hay prompts interactivos, así que toda tool
fuera de esa lista queda
denegada — sin escritura ni shell). Flags verificados con Claude Code 2026-06; ante la duda
confirmar con `claude --help`.

#### Higiene de entorno (cuando la sesión está redirigida a un proveedor no-Anthropic)

Si la sonda del Paso 2 ("Descubrir el revisor") detectó una **redirección** (`ANTHROPIC_BASE_URL`
no-Anthropic o `ANTHROPIC_DEFAULT_*_MODEL` no-`claude-*`), un `claude -p` lanzado tal cual
**heredaría esas variables** y el "revisor Claude" volvería a ser el modelo de respaldo (GLM/Kimi/…)
— autor revisándose a sí mismo. Para garantizar que la Vía C llegue a **Claude real**, lanzar el
revisor en un **proceso hijo con las vars de redirección removidas**, que cae a la suscripción
Anthropic (OAuth) o a la `ANTHROPIC_API_KEY` real:

- **POSIX** — anteponer `env -u …` al `claude` (construye el entorno del hijo sin esas vars):
  ```bash
  env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN \
      -u ANTHROPIC_DEFAULT_OPUS_MODEL -u ANTHROPIC_DEFAULT_SONNET_MODEL -u ANTHROPIC_DEFAULT_HAIKU_MODEL \
      -u ANTHROPIC_MODEL -u ANTHROPIC_SMALL_FAST_MODEL \
    claude -p …
  ```
- **PowerShell** — `powershell` no tiene `env -u` y las `$env:` son **a nivel de proceso** (un
  `Remove-Item Env:` mutaría la sesión actual sin restaurarla). El análogo exacto y a prueba de
  fugas es un **proceso hijo aislado** que primero borra las vars y después corre `claude`. El
  comando del hijo se arma como **string** (un scriptblock literal `{…}` pasado a `-Command` no
  capturaría variables del padre como `$SessionId`; interpolarlas en el string sí):
  ```powershell
  $strip = "Remove-Item Env:ANTHROPIC_BASE_URL,Env:ANTHROPIC_AUTH_TOKEN," +
           "Env:ANTHROPIC_DEFAULT_OPUS_MODEL,Env:ANTHROPIC_DEFAULT_SONNET_MODEL," +
           "Env:ANTHROPIC_DEFAULT_HAIKU_MODEL,Env:ANTHROPIC_MODEL,Env:ANTHROPIC_SMALL_FAST_MODEL " +
           "-ErrorAction SilentlyContinue; "
  powershell -NoProfile -Command ($strip + "claude -p …")
  ```
  (Git Bash en Windows usa el bloque POSIX `env -u`.)

**Por qué no toca la sesión en curso:** el entorno fluye padre→hijo, nunca al revés. El `claude`
conductor (GLM) ya leyó su env al arrancar; el wrapper solo afecta al subproceso revisor.

**Condicional, no incondicional:** aplicar el wrapper **solo** si la sonda detectó redirección. Si
`ANTHROPIC_BASE_URL` está sin setear o es Anthropic, **no** stripear `ANTHROPIC_AUTH_TOKEN` (podría
ser la API key real de Anthropic de alguien sin OAuth) — correr la Vía C tal cual.

**Degradación por auth:** si el `claude -p` con env limpio falla por autenticación (no hay
credencial Anthropic real, solo el token redirigido) → registrar el error, tratarlo como
`UNAVAILABLE` y ceder a Codex o al gate humano (regla 6 del SKILL). Nunca caer de vuelta al modelo
de respaldo en silencio.

Los bloques de invocación de abajo muestran el `claude -p` **base**; cuando la sonda detectó
redirección, anteponer el wrapper de higiene (POSIX `env -u …` / PowerShell hijo aislado) tal como
arriba. El camino SYNC/BACKGROUND y el `--resume` también lo llevan.

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
  # Si la sonda detectó redirección: anteponer `env -u ANTHROPIC_BASE_URL -u … ` al `claude`
  # (ver "Higiene de entorno"). Sin redirección, correr el `claude` tal cual:
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
    # Si la sonda detectó redirección: reemplazar el `claude …` por el hijo aislado
    #   powershell -NoProfile -Command ($strip + "claude …")   (ver "Higiene de entorno").
    Get-Content -Raw <ruta\al\prompt-r1.txt> |
      claude -p --safe-mode --model opus --permission-mode default `
        '--allowedTools=Read,Grep,Glob' --session-id $SessionId > <ruta\al\veredicto.txt>
  } finally { Pop-Location }
  ```
  El mensaje final (veredicto + findings) sale por stdout → redirigirlo a archivo para parsear,
  igual que `--output-last-message` en la Vía B.
- Rondas siguientes (mismo thread, con memoria de lo ya discutido):
  ```bash
  # Si hay redirección: anteponer el mismo `env -u …` al `claude` (ver "Higiene de entorno"):
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
    # Si hay redirección: reemplazar el `claude …` por el hijo aislado (ver "Higiene de entorno").
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
# Si la sonda detectó redirección: anteponer `env -u ANTHROPIC_BASE_URL -u … ` al `claude`
# (ver "Higiene de entorno") para que el revisor sea Claude real y no el modelo de respaldo.
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
# Si hay redirección: anteponer el mismo `env -u …` al `claude` (ver "Higiene de entorno").
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
# Sin redirección, FilePath = claude directo. CON redirección, Start-Process heredaría las env
# del proceso actual → lanzar en cambio un `powershell` hijo que limpia el env y después corre
# claude (el env limpio queda contenido en el hijo, sin tocar la sesión actual): ver la variante
# comentada debajo del bloque.
$SessionId = [guid]::NewGuid().ToString()
$proc = Start-Process -FilePath claude -WorkingDirectory <working_dir> -NoNewWindow -PassThru `
  -RedirectStandardInput  <ruta\al\prompt-r1.txt> `
  -RedirectStandardOutput <ruta\al\veredicto.txt> `
  -RedirectStandardError  <ruta\al\claude-r1.err.txt> `
  -ArgumentList '-p','--safe-mode','--model','opus','--permission-mode','default','--allowedTools=Read,Grep,Glob','--session-id',$SessionId
# Variante con higiene de env (redirección detectada): FilePath = powershell hijo aislado.
#   $cmd = $strip + "claude -p --safe-mode --model opus --permission-mode default " +
#          "'--allowedTools=Read,Grep,Glob' --session-id $SessionId"   # $strip: ver "Higiene de entorno"
#   $proc = Start-Process -FilePath powershell -WorkingDirectory <working_dir> -NoNewWindow -PassThru `
#     -RedirectStandardInput <ruta\al\prompt-r1.txt> -RedirectStandardOutput <ruta\al\veredicto.txt> `
#     -RedirectStandardError <ruta\al\claude-r1.err.txt> -ArgumentList '-NoProfile','-Command',$cmd
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
- Vía A: `--resume` (→ `task --resume-last`). Vía B: `codex exec resume <thread_id>`. Vía C:
  `claude -p --resume <session_id>`. El delta se pasa por stdin con la primitiva de cada shell
  (`<` en POSIX, `Get-Content -Raw | …` en PowerShell — ver "Portabilidad entre shells").
- Si el resume no está disponible en el entorno, degradar a rondas independientes re-enviando el
  artefacto actualizado completo (más caro, pero válido).

**Seed desde co-exploración:** si existe `co-explore/session.json` (escrito por `sdd-co-explore`;
esquema: `{tool, session_id, mode, created_at}`), la Ronda 1 puede **reanudar esa sesión** en
lugar de abrir una nueva — el crítico es el mismo agente que exploró. Si el resume falla, abrir
sesión nueva con los `findings-*.md` como contexto: mismo efecto, sin estado.

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
```

- `APPROVED` sin findings (o solo con findings `low` opcionales) → corta el loop.
- `REVISE` → hay al menos un finding `high`/`medium` que el revisor considera bloqueante.
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
Revisor: <codex-rescue | codex exec | claude -p | …>  ·  max_rounds: <n>

### Ronda 1
**Veredicto del revisor:** REVISE
**Findings:**
- [high] <título>
  - why: <…>  · suggestion: <…>  · refs: AC-2
  - **Decisión de Claude:** APLICADO — <qué se cambió y por qué el finding era correcto>
- [medium] <título>
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
