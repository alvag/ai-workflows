# co-explore — Referencia

Detalle operativo de la skill `co-explore`. El `SKILL.md` apunta aquí cuando necesita la
plantilla del prompt de exploración (por modo), el formato del informe, la plantilla de
síntesis, el algoritmo de descubrimiento del explorador, los tiempos de espera o el árbol de
archivos de trabajo.

## Tabla de contenidos

- [Documentos de esta referencia](#documentos-de-esta-referencia)
- [Portabilidad entre shells (POSIX / PowerShell)](#portabilidad-entre-shells-posix-powershell)
- [Prompt de exploración](#prompt-de-exploración)
- [Plantilla de `debate.md`](#plantilla-de-debatemd)
- [Capacidades y worktree (`investigate`)](#capacidades-y-worktree-investigate)
- [Descubrir el revisor (puntero + fallback)](#descubrir-el-revisor-puntero-+-fallback)
- [Latencia y deadlines](#latencia-y-deadlines)
- [Topología dual (contrato nuevo)](#topología-dual-contrato-nuevo)
- [Mecánica del modo `debate`](#mecánica-del-modo-debate)
- [El criterio de éxito también es una hipótesis (`investigate`)](#el-criterio-de-éxito-también-es-una-hipótesis-investigate)

---

## Documentos de esta referencia

La referencia de esta skill vive en este archivo y se lee en toda corrida:

| Archivo | Qué trae | Cuándo se lee |
|---|---|---|
| `reference.md` (este) | prompts por modo, topología dual, envelope, árbol de rutas, retoma, estados del worker, latencia, `debate` e índice paginado | en toda corrida |

## Portabilidad entre shells (POSIX / PowerShell)

Mismo criterio que `cross-review/reference.md` → "Portabilidad entre shells (POSIX /
PowerShell)": esa sección es la fuente canónica de las equivalencias de shell que también usa
esta skill (detección de OS, prompt por archivo a stdin, generar un UUID). No se duplican aquí.

Lo único que `co-explore` necesita y que cross-review no, porque `explore` corre siempre en
background (ver "Latencia y deadlines"):

| Primitiva | POSIX (bash / Git Bash) | PowerShell (Windows) |
|---|---|---|
| Lanzar en background y capturar el PID | `cmd & PID=$!` | `$proc = Start-Process -FilePath … -PassThru; $proc.Id` |
| Matar el proceso al vencer el deadline | `kill "$PID"` | `Stop-Process -Id $proc.Id -Force` |

El resto de las equivalencias (detectar el binario, prompt por archivo, UUID) son las mismas
que en `cross-review/reference.md` y se referencian por puntero en "Descubrir el revisor
(puntero + fallback)".

## Prompt de exploración

Estructura XML compacta, mismo estilo que "Prompt de revisión" de `cross-review/reference.md`
(operador, no colaborador). Una variante por `mode`: `explore` y `counter-plan` comparten el
`output_contract` exacto; `investigate` usa uno propio (bug-shaped).

### `{constraints}` — el bloque común de todas las plantillas

Las cinco plantillas de este archivo —`explore`, `counter-plan`, `investigate` y las dos rondas de
`debate`— llevan el mismo bloque. Se define una vez acá y cada plantilla lo referencia con el
marcador `{constraints}`, en la posición indicada (entre `<focus>` y `<output_contract>`).

```xml
<constraints>
Todo el contexto que necesitas está en este prompt y en el repositorio del working dir.
- NO consultes memoria ni herramientas MCP de ningún tipo.
- NO busques en la web.
- NO accedas a nada fuera del working dir.
- DENTRO del working dir, busca y lee con libertad: mapear el terreno es tu tarea.
Emite tu salida en el formato pedido y termina el turno.
</constraints>
```

Las tres primeras líneas son prohibiciones; la cuarta es igual de importante y es lo que impide
leerlas de más. **Aislar la configuración no reemplaza este bloque**: los flags evitan que el
worker *pueda* alcanzar MCP y hooks, pero no que decida buscar en la web ni que se vaya por las
ramas. Medido acá: un worker sin estas restricciones hizo dos búsquedas web y 44 comandos antes de
mirar el artefacto.

**El perímetro no se cierra a una lista de archivos.** `explore` e `investigate` reciben un síntoma
o un ticket, no un inventario: descubrir dónde vive el cambio y cuál es la cadena causal *es* el
objetivo, y una lista cerrada esconde justamente las dependencias que nadie conocía. Solo cuando
la skill llamadora declara **explícitamente** que su lista de archivos es exhaustiva, la cuarta
línea se reemplaza por esa lista.

### Modo `debate` (decisión abierta)

Dos prompts: uno para la **ronda 0** (postura independiente) y otro para cada **ronda de cruce**.
Ambos read-only. Estructura XML compacta (operador, no colaborador), escritos a archivo con Write
(nunca inline).

**Prompt de debate — ronda 0 (postura independiente):**


El prompt vive en `assets/prompts/debate-round-0.md` — es la **entrada exacta** del worker y se escribe a archivo con la tool Write. Placeholders que hay que sustituir antes de despachar: `{constraints}`, `{working_dir}`.


**Prompt de debate — cruce (rondas 1..N):**


El prompt vive en `assets/prompts/debate-cross.md` — es la **entrada exacta** del worker y se escribe a archivo con la tool Write. Placeholders que hay que sustituir antes de despachar: `{constraints}`.


## Plantilla de `debate.md`

Local/untracked, en `co-explore/debate.md`. Nombra a las familias (es local, solo lo lee el
usuario). Los deltas crudos por ronda quedan en el scratch.

```markdown
# Debate co-explore — <decisión> (<ISO-8601>)

## Opciones en juego
- <Opción X>
- <Opción Y>

## Posturas finales
### 🟠 Claude
<postura final del conductor: hacia qué opción, por qué, qué concedió en el cruce>
### 🔵 Codex
<postura final del revisor: ídem>
(Ajustar los nombres a las familias reales: si conduce Codex, el conductor es 🔵 Codex y el
revisor 🟠 Claude.)

## Convergencias
<en qué coincidieron las dos posturas>

## En disputa (sin resolver)
<dónde siguen en desacuerdo, con la evidencia de cada lado>

## Trade-offs afilados
| Opción | Compra | Cuesta |
|---|---|---|
| X | … | … |
| Y | … | … |

## Rondas
Convergió en <n> rondas (de max_rounds <m>). <nota si convergió temprano por falta de movimiento>.

## Límite de este debate
- Dos posturas independientes afilan la decisión; no garantizan que la opción correcta esté entre
  las que se debatieron. Un punto ciego compartido por ambas familias queda sin detectar.

> El debate NO elige: la decisión es del usuario. Lo que se registre luego en spec.md/plan.md va
> limpio de método/familias (ver SKILL.md → "Publicado vs local").
```

## Capacidades y worktree (`investigate`)

Recap del modelo de capacidades (regla 1 del `SKILL.md`) y su mecánica:

- **Revisor: L0 read-only siempre.** Se lanza igual que en `explore` (`-s read-only` en Codex,
  `--allowedTools=Read,Grep,Glob` en Claude; ver "Descubrir el revisor"). Lee un checkout
  **estable** — nunca el worktree que el conductor pueda estar mutando.
- **Conductor: L0 por defecto; L1 opt-in.** Si el bug es de runtime y el conductor decide
  ejecutar (reproducir, correr tests, logging efímero), lo hace en un **worktree descartable**,
  no en el árbol del usuario:

```bash
# Worktree throwaway para la ejecución L1 del conductor (POSIX):
WT="$(git rev-parse --show-toplevel)/../.co-explore-wt-$$"
git worktree add --detach "$WT" HEAD
# … el conductor reproduce/corre dentro de "$WT" …
git worktree remove --force "$WT"    # se descarta al cerrar; el árbol del usuario queda intacto
```

El invariante es "no persiste cambios en tu árbol": el worktree se crea, se usa para observar, y
se remueve. L1 rinde sobre todo en la síntesis, para **adjudicar divergencias** entre las dos
hipótesis. Editar/proponer parches (persistir cambios) queda fuera de co-explore (sería una
skill aparte, tipo carrera de fixes cross-model).

## Descubrir el revisor (puntero + fallback)

**Puntero.** El algoritmo canónico de descubrimiento del explorador —identificar al conductor y
elegir workers dentro de la allowlist— vive en `cross-review/reference.md` →
"Descubrir el revisor". Si esa skill está instalada en el entorno, léelo de ahí: esta sección
no lo duplica.

**Fallback mínimo (`co-explore` sin `cross-review` instalada).** Hay dos familias —Claude y
GPT/Codex— y la del conductor es la del agente que conduce la skill. La allowlist elige uno o dos
<!-- corpus-invariante:inicio:co-explore.reference.md.682df987638d -->
workers; la familia opuesta es la recomendada cuando hay una sola entrada.
<!-- corpus-invariante:fin:co-explore.reference.md.682df987638d -->

| Familia del autor | Explorador a buscar | Vía |
|---|---|---|
| Claude | Codex | `codex exec` en background, read-only |
| GPT/Codex | Claude | `claude -p` en background, restringido a tools de lectura |

Si el CLI de un explorador seleccionado no está disponible → `UNAVAILABLE` (regla 6 del `SKILL.md`).

**Invocación directa.** En topología dual se lanzan **los dos**, y el orden y los nombres de
archivo los fija "Fan-out dual y orden de lanzamiento" — no los bloques de abajo, que quedan como
referencia del preflight y de la lectura del config. Las rutas `explorer.*` que aparecen acá son
**históricas**: el árbol vigente es "Árbol de rutas".

**Preflight de aislamiento (fail-closed).** Antes de lanzar, correr `preflight_aislamiento <familia>`
por cada worker a despachar y **ramificar sobre su código de salida**: distinto de 0 → no se lanza y
se devuelve `UNAVAILABLE` (regla 6 del `SKILL.md`). El bloque, la política por familia y el
fundamento viven en la sede única: `cross-review/reference.md` → "Preflight de aislamiento
(fail-closed)".

> **Lo propio de esta skill, que la sede no dice:** acá pesa más que en una invocación sync, porque
> el lanzamiento es en **background**. Un fail-open dejaría un proceso sin aislar corriendo sin nadie
> mirándolo, y en topología dual serían dos.

<!-- despacho:inicio:coex-directa-posix:codex -->
```bash
# POSIX — el prompt ya está escrito a archivo con la tool Write (nunca inline, ni echo/heredoc):
mkdir -p co-explore/scratch
# Modelo y esfuerzo del usuario: --ignore-user-config los descarta junto con el resto del config,
# así que se leen antes y se pasan explícitos. Solo vale una asignación RAÍZ inequívoca del TOML
# (anterior a la primera cabecera de tabla, comillas dobles, una sola ocurrencia); si no, se deja
# el default del CLI en vez de forzar un valor sacado de una tabla, que aplica a otro contexto.
CODEX_CFG="${CODEX_HOME:-$HOME/.codex}/config.toml"
ROOT=$(awk '/^[[:space:]]*\[/{exit} {print}' "$CODEX_CFG" 2>/dev/null)
read_root_key() {
  n=$(printf '%s\n' "$ROOT" | grep -cE "^$1[[:space:]]*=[[:space:]]*\"[^\"]*\"[[:space:]]*$")
  [ "$n" -eq 1 ] && printf '%s\n' "$ROOT" |
    sed -n "s/^$1[[:space:]]*=[[:space:]]*\"\([^\"]*\)\".*/\1/p"
}
MODEL=$(read_root_key model)
EFFORT=$(read_root_key model_reasoning_effort)

# Argumentos incrementales, NUNCA ${MODEL:+-m "$MODEL"}: en zsh esa expansión no hace field
# splitting y `-m` viaja pegado a su valor, con lo que el modelo llega con un espacio inicial y
# la API lo rechaza.
set -- exec --ignore-user-config --disable hooks --disable apps --disable plugins \
       -s read-only -C <working_dir> --skip-git-repo-check --json \
       --output-last-message co-explore/scratch/explorer.out
[ -n "$MODEL" ]  && set -- "$@" -m "$MODEL"
[ -n "$EFFORT" ] && set -- "$@" -c "model_reasoning_effort=$EFFORT"
set -- "$@" -
codex "$@" < co-explore/scratch/prompt.txt \
    > co-explore/scratch/explorer-thread.jsonl \
    2> co-explore/scratch/explorer.err &
PID=$!
echo "$PID" > co-explore/scratch/explorer.pid
```
<!-- despacho:fin:coex-directa-posix -->
<!-- despacho:inicio:coex-directa-ps:codex -->
```powershell
# PowerShell:
New-Item -ItemType Directory -Force -Path co-explore\scratch | Out-Null
$CodexCfg = Join-Path ($env:CODEX_HOME ?? "$HOME\.codex") 'config.toml'
$Lines = @(Get-Content $CodexCfg -ErrorAction SilentlyContinue)
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
               '--skip-git-repo-check','--json',
               '--output-last-message','co-explore\scratch\explorer.out')
if ($Model)  { $CodexArgs += @('-m', $Model) }
if ($Effort) { $CodexArgs += @('-c', "model_reasoning_effort=$Effort") }
$proc = Start-Process -FilePath codex -NoNewWindow -PassThru `
  -RedirectStandardInput  co-explore\scratch\prompt.txt `
  -RedirectStandardOutput co-explore\scratch\explorer-thread.jsonl `
  -RedirectStandardError  co-explore\scratch\explorer.err `
  -ArgumentList $CodexArgs
$proc.Id | Out-File co-explore\scratch\explorer.pid
```
<!-- despacho:fin:coex-directa-ps -->

Los cuatro flags de aislamiento son lo que evita que el explorador herede los MCP del entorno, los
hooks locales y las instrucciones de modelo del usuario. Medido en este repo: un worker sin aislar
arrancó consultando memoria y haciendo búsquedas web, y no terminó en 600 s; el mismo prompt
aislado cerró en 297 s con cero llamadas MCP. Todo el contexto que el explorador necesita viaja en
el prompt, así que no pierde nada.

`-s read-only` (`--sandbox read-only`) garantiza que el explorador no escribe nada en el repo;
`--output-last-message` deja el informe final —el que debe terminar en `STATUS: done`— en
`explorer.out`, listo para el poll del punto de encuentro (ver "Latencia y deadlines"). `--json`
emite el stream de eventos JSONL por stdout (redirigido a `explorer-thread.jsonl`): la línea
`{"type":"thread.started","thread_id":"…"}` aparece apenas arranca la sesión, y es la captura
**determinística** del thread id para `session.json` — no "buscarlo en la salida humana":

```bash
# En cuanto interese el id (para explorer-session.txt / session.json):
grep -m1 -o '"thread_id":"[^"]*"' co-explore/scratch/explorer-thread.jsonl | cut -d'"' -f4 \
  > co-explore/scratch/explorer-session.txt
```
```powershell
(Select-String -Path co-explore\scratch\explorer-thread.jsonl -Pattern '"thread_id":"([^"]+)"' |
  Select-Object -First 1).Matches.Groups[1].Value > co-explore\scratch\explorer-session.txt
```

> **Prechequeos**: aplican los mismos de `cross-review/reference.md` → "Descubrir el revisor"
> (versión del CLI, no pinear `-m`, eco del modelo activo de `~/.codex/config.toml`).

**Invocación directa — autor GPT/Codex → explorador Claude.** Adaptado de
`cross-review/reference.md` → Vía C, camino BACKGROUND (el mismo patrón que usa cross-review
cuando el conductor tiene un exec corto, p. ej. Codex ~120s):

<!-- despacho:inicio:coex-latencia-posix:claude -->
```bash
# POSIX:
SESSION_ID=$(uuidgen)   # Git Bash en Windows sin uuidgen: ver "Portabilidad entre shells" de cross-review
mkdir -p co-explore/scratch
( cd <working_dir> && claude -p --safe-mode --model opus --permission-mode default \
    --allowedTools=Read,Grep,Glob \
    --session-id "$SESSION_ID" \
    < co-explore/scratch/prompt.txt \
  > co-explore/scratch/explorer.out 2> co-explore/scratch/explorer.err ) &
PID=$!
echo "$PID" > co-explore/scratch/explorer.pid
echo "$SESSION_ID" > co-explore/scratch/explorer-session.txt
```
<!-- despacho:fin:coex-latencia-posix -->
<!-- despacho:inicio:coex-latencia-ps:claude -->
```powershell
# PowerShell:
$SessionId = [guid]::NewGuid().ToString()
$proc = Start-Process -FilePath claude -WorkingDirectory <working_dir> -NoNewWindow -PassThru `
  -RedirectStandardInput  co-explore\scratch\prompt.txt `
  -RedirectStandardOutput co-explore\scratch\explorer.out `
  -RedirectStandardError  co-explore\scratch\explorer.err `
  -ArgumentList '-p','--safe-mode','--model','opus','--permission-mode','default','--allowedTools=Read,Grep,Glob','--session-id',$SessionId
$proc.Id | Out-File co-explore\scratch\explorer.pid
$SessionId | Out-File co-explore\scratch\explorer-session.txt
```
<!-- despacho:fin:coex-latencia-ps -->

`--allowedTools=Read,Grep,Glob` es lo único que garantiza read-only en `claude -p` (no existe un
flag de sandbox equivalente a `-s read-only`); `--safe-mode` evita cargar plugins/hooks/MCP/
CLAUDE.md del usuario del `working_dir`.

`$SESSION_ID`/`$SessionId`, capturado en `explorer-session.txt`, es la base para escribir
`co-explore/session.json` (ver "Archivos de trabajo (scratch)") cuando `cross-review` está
instalada y puede reanudar ese thread.

## Latencia y deadlines

| Modo | Deadline default | Poll cada | Intentos aprox. |
|---|---|---|---|
| `explore` | 600 s | 10 s | ~60 |
| `counter-plan` | 300 s | 10 s | ~30 |
| `investigate` | 600 s | 10 s | ~60 |

En `debate`: deadline **por ronda** (default 300 s) + tope `max_rounds` (default 3). Al vencer una
ronda, cortar y sintetizar con lo que haya (regla 5).

Override: `co_explore.deadline` en la config (ver `SKILL.md` → "Configuración"); si
no está seteado, se usa el default de la tabla según `mode`. Una exploración tarda más que una
crítica de cross-review (tiene que recorrer el repo desde cero), por eso el default de `explore`
es más alto. En `investigate` no hay config (es standalone): el override, si lo hay, es
conversacional; si no, el default de la tabla.

### Default de `execution` por skill y modo

`execution` es un enum **cerrado de tres valores** —`auto | sync | background`— y estos son los
defaults efectivos de las tres skills cross-model. Viven acá una sola vez: `cross-review` y
`cross-implement` los referencian por el nombre de esta sección en lugar de copiarlos, porque tres
copias de una tabla de defaults son tres oportunidades de divergir.

| Skill · modo | Default de `execution` |
|---|---|
| `co-explore` · `explore` (embebido) | `background` |
| `co-explore` · `counter-plan` (embebido) | `sync` |
| `co-explore` · `investigate` (directo) | `background` |
| `co-explore` · `debate` (directo) | `sync` por ronda — el loop de cruce es secuencial |
| `cross-review` · todos los modos | `auto` |
| `cross-implement` · `embebido` y `directo` | `auto` |

**Estos defaults no tienen perilla de config, y es deliberado.** No existe un campo `execution` bajo
`co_explore`: cómo se espera en cada modo es parte de la **definición del modo**, no un parámetro de
la corrida. Tres razones, cualquiera suficiente por sí sola: `SKILL.md` → "Configuración" ya fija la
doctrina para el campo hermano —"NO hay bloque `workers`: … lo fija la topología dual, no el
config"—; el repo tiene un precedente reciente y explícito de revertir configuración sin consumidor;
y un escalar no puede expresar defaults que **varían por modo**, que es exactamente lo que muestran
las seis filas de arriba. *El costo, declarado:* quien quiera forzar `sync` en `explore` no tiene
dónde pedirlo. `cross_review` y `cross_implement` sí exponen la clave porque su default es `auto` —un
único valor por skill, no uno por modo.

### Re-invocación durable: el segundo predicado

Haber elegido `background` no dice todavía **cómo** se espera. Hacen falta **dos** predicados
distintos, y confundirlos es el error que esta sección existe para cerrar: que el conductor pueda
fijar un timeout de exec largo **no demuestra** que el host lo vuelva a invocar cuando un comando en
background termina. Son capacidades de piezas distintas y se miden aparte.

**La secuencia completa, en dos pasos y en este orden.** Primero, `execution: auto` elige entre
`sync` y `background` por el predicado de **timeout de exec** que ya existe: auto → sync cuando el
conductor puede sostener un tope largo (Claude Code, `Bash` con `timeout` hasta 600000 ms), auto →
background cuando no (conductor de exec corto, ~120 s por comando). Después, **ya dentro de
`background`**, decide un segundo predicado —el de **re-invocación durable**— entre **callback** y
**poll acotado**. Pedir `sync` o `background` a mano saltea el primer paso, nunca el segundo: un
`background` explícito también pasa por el predicado de re-invocación durable.

**Condición de verdad, positiva.** El predicado de re-invocación durable es verdadero **solo** cuando
el contrato documentado del host **garantiza** volver a invocar al conductor al completar un comando
en background. La **ausencia de garantía —no solo una garantía en contra— lo vuelve falso**: un host
que no documenta el comportamiento, o que lo documenta como algo que "puede" ocurrir, cuenta como
falso. Redactado al revés —verdadero salvo garantía en contra— sería verdadero por defecto en
cualquier host desconocido, que es justo donde una espera sin poll se cuelga para siempre.

**La continuidad la aporta el harness, no el transporte.** El multiplexor de terminales aloja el
proceso y lo mantiene vivo mientras el conductor no está mirando; eso no es lo mismo que despertar al
conductor. Volver a invocarlo cuando el comando termina es una capacidad del **host** que corre al
conductor, y se mide en su contrato, no en el del transporte. Un transporte que aloje procesos
impecablemente no vuelve verdadero este predicado.

**Falla cerrado.** Con el predicado en falso, `background` **falla cerrado al poll acotado de hoy**:
la tabla de deadlines de arriba y el tope duro por worker de acá abajo, con su `kill` y su
`UNAVAILABLE` al vencer. Sin comportamiento nuevo y sin nada nuevo que configurar.

**El enum no crece.** No hay un cuarto valor para esto, ni sinónimo suyo. El desacople
**reinterpreta** `background`: con el predicado en verdadero, `background` no consume turnos del
conductor poleando —el host lo despierta al terminar—; con el predicado en falso, `background` es el
poll de siempre. Un cuarto valor obligaría además a definir qué hace el conductor cuando alguien lo
pide en un host sin la capacidad, y la única respuesta sensata sería degradar a `background`: el
mismo comportamiento con un nombre más en tres skills.

### Tope duro, señal de fin y espera por modo

**Tope duro, por worker.** Cada deadline corre desde **su propio** lanzamiento, no desde el
primero. Al vencer sin ver `STATUS: done` en el crudo de ese worker
(`scratch/raw-<modo>-<familia>-worker.md`):
matar el proceso (`kill "$PID"` en POSIX, `Stop-Process -Id $proc.Id -Force` en PowerShell) y
devolver `UNAVAILABLE` — con lo que el explorador haya alcanzado a escribir hasta ese momento, si
algo, degradado a texto libre según la regla 4 del `SKILL.md`. Nunca se espera de forma
indefinida (regla 5 del `SKILL.md`).

**Señal de fin.** La única señal de que el explorador terminó es la línea `STATUS: done` al final
de su salida (ver "Prompt de exploración" → `output_contract`). El poll busca exactamente esa
línea:

```bash
# En el punto de encuentro (después de la propia exploración del conductor):
if grep -q '^STATUS: done$' co-explore/scratch/explorer.out 2>/dev/null; then
  cat co-explore/scratch/explorer.out    # listo → normalizar contra "Formato del informe"
else
  echo 'corriendo…'   # repetir en intentos cortos; tope DURO: ~60 (explore) / ~30 (counter-plan)
fi
# Al agotar los intentos sin STATUS: done → kill "$PID"; tratar como UNAVAILABLE.
```
```powershell
if ((Test-Path co-explore\scratch\explorer.out) -and
    ((Get-Content co-explore\scratch\explorer.out -Raw) -match '(?m)^STATUS: done$')) {
  Get-Content co-explore\scratch\explorer.out   # listo → normalizar contra "Formato del informe"
} else { 'corriendo…' }   # repetir; al agotar intentos → Stop-Process -Id $proc.Id -Force; UNAVAILABLE
```

**`explore` no espera en loop.** A diferencia de `counter-plan` (que sí espera con tope, porque
el conductor necesita el contra-enfoque del revisor antes de seguir a `plan.md`), en `explore` el
conductor lanza el explorador en background y devuelve el control de inmediato: hace su propia
exploración de siempre, sin pollear en paralelo. Recién en el punto de encuentro —antes de
escribir `spec.md`— consume el deadline restante con el poll de arriba. El reloj del deadline
corre desde el lanzamiento, no desde que el conductor vuelve a mirar.

## Topología dual (contrato nuevo)

Define el contrato de la topología de dos workers con conductor árbitro.

### Formato de dos capas

El worker corre read-only y no puede escribir archivos: **las dos capas viajan en el mismo mensaje
final**, y el conductor las parte después (ver "Split a dos archivos").

```
## Índice
| ID | tipo · qué | sev | conf | punteros |
|---|---|---|---|---|
| CDX-W-EXP-001 | ubicación · el poll del explorador vive acá | high | high | skills/co-explore/reference.md:663 |
| CDX-W-EXP-002 | riesgo · dos procesos pisan el mismo scratch | high | medium | skills/co-explore/reference.md:690 |

## Detalle

### CDX-W-EXP-001
<desarrollo completo de esa entrada>

### CDX-W-EXP-002
<desarrollo completo de esa entrada>

STATUS: done
```

Reglas del índice:

- **Una fila física por entrada.** Una fila que ocupa dos líneas rompe el parseo y, sobre todo,
  rompe el propósito: si la fila puede extenderse, el índice deja de comprimir y pasa a ser una
  copia del detalle con costo agregado.
- **Cinco campos, siempre**: `ID`, `tipo · qué`, severidad/impacto, confianza, punteros.
- **Punteros**: `path:line` con un solo `working_dir`; **`repo/path:line`** cuando el `working_dir`
  es una lista (exploración cross-repo del orquestador). Una entrada sin puntero posible escribe
  `N/A: <motivo>` — nunca se deja vacío, porque un campo vacío no distingue "no aplica" de "me
  olvidé".
- **El índice enumera TODAS las entradas del detalle.** No es un resumen ejecutivo ni un top-N: es
  una capa de navegación completa. La paridad de IDs lo verifica mecánicamente.

Reglas del detalle:

- Arranca en `## Detalle` y **todo** contenido posterior vive bajo un `### <ID>`. Prosa suelta entre
  entradas es contenido no indexado: invisible para el conductor, que solo abre por ID.
- El orden de las entradas del detalle no tiene que coincidir con el del índice.

`STATUS: done` va **fuera** de ambas capas, como última línea no vacía del crudo — ver "Señal de
finalización".

### Gramática de ID (dos capas)

```
<FAM>-<ROL>-<MODO>-<NNN>
```

| Campo | Valores | Qué distingue |
|---|---|---|
| `FAM` | `CLD` \| `CDX` | familia del autor de la entrada |
| `ROL` | `W` (worker) \| `C` (conductor) | quién la produjo |
| `MODO` | `EXP` \| `CTR` \| `INV` | `explore` \| `counter-plan` \| `investigate` |
| `NNN` | tres dígitos, `001`… | correlativo dentro de la entrega |

Ejemplo: `CLD-W-EXP-001`.

**Los tres discriminantes son necesarios, no decorativos:**

- Sin `FAM`, los dos workers colisionan en la síntesis.
- Sin `ROL`, la **rama 3** de la escalera colisiona: ahí el conductor vuelve a producir un mapa y
  puede ser de la misma familia que el worker superviviente.
- Sin `MODO`, un flujo SDD que corre `explore` y después `counter-plan` sobre el mismo `<id>` pisa
  los IDs de la primera fase.

La unicidad rige **dentro de una entrega**; entre fases, el discriminante de modo la garantiza.

### Unidad indexable por modo

Qué genera una fila de índice, y cuál es la unidad atómica de una entrada. Sin esto, "el índice
enumera todas las entradas" no tiene referente cerrado y cada worker decide su propia granularidad.

**`explore` y `counter-plan`** — siete tipos:

| Tipo | Unidad atómica |
|---|---|
| `ubicación` | un archivo o módulo relevante, con su puntero |
| `relación` | una dependencia o acoplamiento entre dos lugares |
| `hipótesis` | una afirmación falsable sobre cómo encaja el cambio |
| `reúso` | una pieza existente que evita escribir código nuevo |
| `riesgo` | una forma concreta en que algo se rompe |
| `incógnita` | una pregunta abierta que no se pudo resolver leyendo |
| `supuesto` | una decisión tomada para poder seguir, con su porqué |

**`investigate`** — seis tipos:

| Tipo | Unidad atómica |
|---|---|
| `síntoma` | un comportamiento observado, con su evidencia |
| `eslabón` | un paso de la cadena causal, con su puntero |
| `hipótesis` | una causa raíz candidata, con observable y refutación |
| `incógnita` | lo que no se pudo determinar leyendo |
| `supuesto` | qué se asumió para seguir, y por qué |
| `verificación` | un paso concreto de confirmación |

**Regla de granularidad:** una entrada es atómica si su desarrollo puede leerse solo y seguir
teniendo sentido. Dos riesgos que comparten causa son **una** entrada; dos riesgos independientes
en el mismo archivo son **dos**.

En los dos conjuntos, `incógnita` y `supuesto` **sí** se indexan. Su severidad se lee como el costo
de dejarlo sin resolver, o de haberlo asumido mal: una incógnita `high` es la que puede invalidar el
enfoque.

### Ejes: severidad y confianza

Enum **cerrado** en ambos: `high` | `medium` | `low`. No admiten prosa.

- **severidad/impacto** — qué tan grave si la entrada es correcta.
- **confianza** — qué tan seguro está el autor de que lo es.

Son **ortogonales** (misma distinción que `cross-review` → "Formato de salida"). El enum cerrado no
es cosmética: los disparadores de la lectura selectiva se definen **sobre estos valores**
—"alto riesgo" es `sev = high`, "baja confianza" es `conf = low`—, de modo que abrir o no una
entrada se decide leyendo la fila, sin juicio del conductor. Con prosa libre, el disparador
volvería a depender de interpretación y la regla dejaría de ser mecánica.

Un valor fuera del enum es detectable, y su consecuencia está fijada en "Estados del worker".

### Señal de finalización

El informe cierra con `STATUS: done` como **última línea no vacía del crudo**, exactamente una vez.

Es la única señal que el poll usa para dar por terminado a un worker: un informe conforme al formato
de dos capas que la omitiera moriría por timeout **con contenido válido**.

Tras el split, `STATUS: done` **no queda en ninguno de los dos archivos**: pertenece al transporte,
no al contenido, y su lugar es el crudo. Un `index-*` o un `detail-*` que lo contenga indica un
split mal hecho.

Consecuencias de cada anomalía en "Estados del worker": ausente, duplicada o fuera de posición.

### Contrato del mapa del conductor

En las ramas degradadas el conductor vuelve a producir un mapa, y ese mapa entra en
`contributors[]`. Necesita su propio contrato, porque el resto está escrito para workers.

**Cumple:** el formato de dos capas, la gramática de ID con `ROL = C`, la unidad indexable de su
modo, los enums y la paridad.

**No cumple, por construcción:** `STATUS: done` (no hay proceso que terminar) ni referencia de
sesión (`session` es `null` en `contributors[]`). Ambos son artefactos del transporte.

**Se produce siempre dentro de la corrida, nunca se toma de disco.** Si no valida, el conductor lo
regenera: es su propia salida. La regeneración es **acotada a 2 intentos**; si la segunda tampoco
valida, la salida es `FALLO_DE_MAPA`, terminal y **fuera** de las cuatro ramas de la escalera, sin
contexto de co-explore y directo al gate humano.

`FALLO_DE_MAPA` no es la rama 4: esa exige cero workers válidos y una voz válida del conductor, y
acá puede haber un worker `READY` y el conductor sin mapa. Tampoco tiene rama propia: que el
conductor no logre escribir dos veces su propio formato documentado es un defecto, no un modo de
operación.

### Prompt de explore (dos capas)

Reemplaza a "Modo `explore` (pre-spec)" en la topología dual. Los dos workers reciben este prompt
**idéntico**; solo cambia el prefijo de familia de sus IDs.


El prompt vive en `assets/prompts/explore.md` — es la **entrada exacta** del worker y se escribe a archivo con la tool Write. Placeholders que hay que sustituir antes de despachar: `{FORMATO_PUNTERO}`, `{PREFIJO}`, `{constraints}`.


`{PREFIJO}` se sustituye por `CDX-W-EXP` o `CLD-W-EXP` según el worker. `{FORMATO_PUNTERO}` es
`path:line` con un solo `working_dir`, o `repo/path:line` con varios.

> **La calibración de longitud del detalle y por qué está redactada así.** El contrato acota la
> *estructura* del informe pero no cuánto se escribe bajo cada `### <ID>`, y esa prosa es la que
> paga el costo: el detalle se persiste en disco y el árbitro abre entradas por disparador. De ahí
> la línea que pide desarrollar lo que aporta y no rellenar. Va con una salvaguarda explícita —
> **calibra cuánto se escribe por entrada, no cuántas se emiten**— porque una instrucción de
> brevedad a secas se cumple al pie de la letra recortando **hallazgos**, que es exactamente lo que
> este modo existe para producir.
>
> **Todo cambio acá tiene que ser neutro entre familias.** Los dos workers reciben este prompt
> byte-idéntico (regla 2), así que una redacción afinada para una familia desoptimiza a la otra y,
> peor, vuelve incomparables los dos mapas. Una guía de estilo específica de un modelo entra en el
> prompt del **revisor** de `cross-review` o del **implementador** de `cross-implement`, donde la
> familia destinataria está fijada — nunca en los prompts duales.

### Prompt de counter-plan (dos capas)

Mismo `output_contract` que `explore`, con `{PREFIJO}` = `<FAM>-W-CTR`. Cambian `<task>`, el
paquete y el foco:


El prompt vive en `assets/prompts/counter-plan.md` — es la **entrada exacta** del worker y se escribe a archivo con la tool Write.


El anexo **viaja concatenado dentro del prompt**, nunca como una ruta a abrir: en `sdd-orchestrator`
los artefactos viven en la carpeta contenedora, fuera del `working_dir`, y el bloque `{constraints}`
prohíbe salir de ahí. Concatenarlo lo resuelve sin ensanchar el perímetro de lectura de ningún
worker, y sin que el conductor cargue el anexo en su ventana: lo escribe el shell.

**Nunca** el artefacto de la otra familia — eso rompería el anti-anclaje que el modo existe para
preservar.

### Prompt de investigate (dos capas)

> **No tiene asset propio, a diferencia de los otros cuatro.** Está definido **por delta** sobre
> `assets/prompts/explore.md`, y materializarlo sería escribir un prompt que hoy no existe — un
> cambio de contenido disfrazado de mudanza de archivo. Se deja como delta hasta que haya una razón
> concreta para congelarlo aparte.

Mismo formato de dos capas, con `{PREFIJO}` = `<FAM>-W-INV` y los **seis** tipos de la tabla de
`investigate`. El `<task>` y el `<focus>` son los de "Modo `investigate` (standalone, bug)", con la
disciplina de observable / autoridad / refutación intacta: cada entrada de tipo `hipótesis`
desarrolla en su `### <ID>` la hipótesis, qué afirma, qué fuente la respalda, qué evidencia la
tumbaría y cómo confirmarla.

El **criterio de éxito** sigue entrando como una hipótesis más, con la misma vara: con evidencia de
respaldo va como entrada `hipótesis`; sin ella, baja a entrada `incógnita`.

### Fan-out dual y orden de lanzamiento

Los dos workers salen del mismo paquete de contexto y ninguno ve la salida del otro. El orden es
**fijo** y no lo negocia `execution`:

```
preparar prompt A  →  preparar prompt B  →  truncar rutas  →  lanzar A  →  lanzar B  →  esperar
```

**`execution: sync | background` gobierna cuándo vuelve el control a la llamadora, nunca la
concurrencia interna.** Una implementación que lance A, espere A y después lance B cumple la letra
de "despacha dos workers" y duplica la latencia: es el modo de fallo que esta regla existe para
cerrar. Cada deadline corre **desde su propio lanzamiento**, no desde el primero. El fallo de uno no
descarta al otro si quedó `READY`.

**POSIX** — el preflight de aislamiento y la lectura del config son los de "Descubrir el revisor
(puntero + fallback)"; acá solo cambia que se lanzan dos:

```bash
S=<dir>/co-explore/scratch
M=<modo>            # explore | counter-plan | investigate

# 1) los DOS prompts, antes de cualquier lanzamiento
#    (escritos con la tool Write, nunca inline: el markdown con backticks rompe el quoting)

# 2) truncar — ver "Truncado previo al dispatch"

# 3) lanzar los dos, sin esperar entre medio — ver los dos bloques de abajo
```

> **El paso 3 va partido en un bloque por familia**, para que cada receta lleve su mecanismo de
> aislamiento a la vista y se pueda comprobar leyendo el despacho. **La partición no cambia el
> orden:** los dos se lanzan en background, uno detrás del otro, y el poll del paso 4 viene después
> de ambos. Esperar al primero antes de lanzar el segundo duplica la latencia cumpliendo la letra.

<!-- despacho:inicio:coex-fanout-posix-codex:codex -->

```bash
# 3a) worker Codex
codex exec --ignore-user-config --disable hooks --disable apps --disable plugins \
      -s read-only -C <working_dir> --skip-git-repo-check --json \
      --output-last-message "$S/raw-$M-codex-worker.md" \
      ${MODEL:+-m} ${MODEL:+"$MODEL"} - \
    < "$S/prompt-$M-codex-worker.txt" \
    > "$S/thread-$M-codex-worker.jsonl" 2> "$S/stderr-$M-codex-worker.txt" &
echo $! > "$S/pid-$M-codex-worker.txt"
T0_CODEX=$(date +%s)
```

<!-- despacho:fin:coex-fanout-posix-codex -->

<!-- despacho:inicio:coex-fanout-posix-claude:claude -->

```bash
# 3b) worker Claude — sin esperar al anterior
( cd <working_dir> && claude -p --safe-mode --model opus --permission-mode default \
    --allowedTools=Read,Grep,Glob --session-id "$SID_CLAUDE" \
    < "$S/prompt-$M-claude-worker.txt" ) \
    > "$S/raw-$M-claude-worker.md" 2> "$S/stderr-$M-claude-worker.txt" &
echo $! > "$S/pid-$M-claude-worker.txt"
T0_CLAUDE=$(date +%s)
```

<!-- despacho:fin:coex-fanout-posix-claude -->

```bash
# 4) recién ahora, poll de ambos — cada uno contra SU T0
```

> **Nota sobre `${MODEL:+-m}`**: acá funciona porque son **dos** expansiones separadas, una por
> argumento. La forma `${MODEL:+-m "$MODEL"}` **no** funciona en zsh: no hace field splitting y
> manda `-m` pegado a su valor. Ante la duda, la construcción incremental con `set -- "$@" -m
> "$MODEL"` de "Descubrir el revisor" es la segura.

**PowerShell:**

```powershell
$S = "<dir>\co-explore\scratch"; $M = "<modo>"
```

> **Los dos `Start-Process` van ANTES de cualquier `Wait-Process`.** Los bloques están partidos por
> familia para que cada uno lleve su aislamiento a la vista, y esa partición **no** cambia el orden:
> se lanza el de Codex, se lanza el de Claude, y recién después se espera. Poner el `Wait` al final
> del primer bloque serializa los workers y duplica la latencia cumpliendo la letra.

<!-- despacho:inicio:coex-fanout-ps-codex:codex -->

```powershell
# Los argumentos se construyen ACÁ, en el punto de despacho: si viven lejos, la receta no muestra
# su propio aislamiento y nadie puede comprobarlo leyendo el lanzamiento.
$CodexArgs = @('exec','--ignore-user-config','--disable','hooks','--disable','apps',
               '--disable','plugins','-s','read-only','-C','<working_dir>',
               '--skip-git-repo-check','--json',
               '--output-last-message',"$S\raw-$M-codex-worker.md")
if ($Model)  { $CodexArgs += @('-m', $Model) }
if ($Effort) { $CodexArgs += @('-c', "model_reasoning_effort=$Effort") }
$CodexArgs += '-'
$pCodex = Start-Process -FilePath codex -NoNewWindow -PassThru `
  -RedirectStandardInput  "$S\prompt-$M-codex-worker.txt" `
  -RedirectStandardOutput "$S\thread-$M-codex-worker.jsonl" `
  -RedirectStandardError  "$S\stderr-$M-codex-worker.txt" -ArgumentList $CodexArgs
```

<!-- despacho:fin:coex-fanout-ps-codex -->

<!-- despacho:inicio:coex-fanout-ps-claude:claude -->

```powershell
# `--safe-mode` es el mecanismo de aislamiento de esta familia: apaga CLAUDE.md, skills, plugins,
# hooks y MCP del usuario. `--allowedTools` entrecomillado entero, o PowerShell parsea las comas.
$SidClaude   = [guid]::NewGuid().ToString()
$ClaudeArgs  = @('-p','--safe-mode','--model','opus','--permission-mode','default',
                 '--allowedTools=Read,Grep,Glob','--session-id',$SidClaude)
$pClaude = Start-Process -FilePath claude -WorkingDirectory <working_dir> -NoNewWindow -PassThru `
  -RedirectStandardInput  "$S\prompt-$M-claude-worker.txt" `
  -RedirectStandardOutput "$S\raw-$M-claude-worker.md" `
  -RedirectStandardError  "$S\stderr-$M-claude-worker.txt" -ArgumentList $ClaudeArgs
$SidClaude | Out-File "$S\session-$M-claude-worker.json"
```

<!-- despacho:fin:coex-fanout-ps-claude -->

```powershell
# recién acá: Wait/poll de los dos
```

**En `counter-plan`**, el prompt de cada worker se arma como **núcleo común byte-idéntico + anexo
privado**, concatenado por el shell:

```bash
for F in codex claude; do
  cat "$S/nucleo-$M.txt" > "$S/prompt-$M-$F-worker.txt"
  # el anexo SOLO si ese worker quedó READY en explore — nunca el de la otra familia
  if [ "$(estado_worker explore "$F")" = READY ]; then
    printf '\n<anexo_privado>\n' >> "$S/prompt-$M-$F-worker.txt"
    cat <dir>/co-explore/index-explore-$F-worker.md \
        <dir>/co-explore/detail-explore-$F-worker.md >> "$S/prompt-$M-$F-worker.txt"
    printf '</anexo_privado>\n' >> "$S/prompt-$M-$F-worker.txt"
  fi
done
```

Sin anexo disponible, el worker corre solo con el núcleo y su informe vale igual: pierde su propia
memoria de la fase anterior, no la validez.

### Independencia por modo (regla 2 en topología dual)

La independencia sigue siendo el invariante, pero **cambia de eje según el modo**:

| Modo | Entre quiénes rige |
|---|---|
| `explore`, `counter-plan`, `investigate` | **worker ↔ worker**: ninguno ve la salida del otro, ni ahora ni en fases posteriores |
| `debate` | **conductor ↔ worker en la ronda 0**, como siempre: ahí el conductor *es* una de las dos voces |

Reescribir la regla como worker↔worker a secas dejaría a `debate` sin anclaje. El conductor deja de
ser voz **solo** en los tres modos duales.

Lo que no cambia en ningún modo: el paquete de contexto nunca lleva hallazgos, hipótesis ni
borradores de nadie.

### Excepción de familia (topología dual)

En topología dual se lanzan un worker Codex **y** un worker Claude. Cuando conduce Claude, eso pone
<!-- corpus-invariante:inicio:co-explore.reference.md.7b096da38083 -->
un worker de **la misma familia que el conductor**; la allowlist también puede elegir esa topología
<!-- corpus-invariante:fin:co-explore.reference.md.7b096da38083 -->
con un solo worker.

**Por qué es aceptable acá, y solo acá:** el valor cross-model vive en que los **dos mapas que se
comparan** vengan de familias distintas. En la topología anterior esos dos mapas eran el del
<!-- corpus-invariante:inicio:co-explore.reference.md.b9ef85a664ff -->
conductor y el del worker, así que el worker tenía que ser de la otra familia. En la topología dual
<!-- corpus-invariante:fin:co-explore.reference.md.b9ef85a664ff -->
el conductor **no produce mapa**: arbitra. Los dos mapas comparados son los de los dos workers, uno
por familia, y la diversidad se conserva íntegra.

**Costo:** en los tres modos duales la diversidad vive entre workers. En `cross-review`,
<!-- corpus-invariante:inicio:co-explore.reference.md.5f58c89c7e0d -->
`cross-implement` y `debate`, la familia opuesta sigue siendo el default; elegir la misma familia es
<!-- corpus-invariante:fin:co-explore.reference.md.5f58c89c7e0d -->
una salida consciente que conserva un proceso aparte, pero no rompe la correlación de errores.

### Carve-outs de la regla del conductor

Cuatro cosas **no** son construir un mapa propio, y siguen vigentes:

1. **Confirmar qué repos entran**, en `sdd-orchestrator`, antes de despachar. Es acotar el
   `working_dir`, no explorar: sin eso el fan-out no sabe dónde mirar.
2. **La ejecución L1 opt-in en `investigate`** (worktree descartable): es **arbitraje dirigido** de
   una hipótesis concreta —reproducir, correr un test, logging efímero—, no la construcción de un
   mapa.
3. **La verificación puntual de punteros** ante un disparador: leer los `path:line` que cita una
   entrada abierta, para decidir cuál relato coincide con el repositorio. Sin esto los punteros del
   índice serían decorativos y el árbitro solo podría elegir entre dos narraciones.
4. **El mapa de fallback** de las ramas 2, 3 y 4 — permitido **únicamente después** de que el
   envelope resuelva a una rama degradada, nunca como atajo antes de esperar a los workers.

Los tres primeros conviven con la rama nominal; el cuarto la presupone descartada.

### Escalera de degradación

"Válido" = `READY` (ver "Estados del worker"). Ordenada por diversidad conservada:

| Rama | Situación | Qué hace el conductor | Qué se declara |
|---|---|---|---|
| **1** | dos workers válidos | arbitra, no explora | nominal — `diversity: cross_family` |
| **2** | sobrevive el de la **otra** familia | **explora** (topología anterior) | diversidad conservada, ahorro perdido |
| **3** | sobrevive el de la **misma** familia | **explora** | **diversidad reducida** — `same_family` |
| **4** | cero workers válidos | **explora**; cierre conductor-only, **sin síntesis** | una sola voz — `single_voice` |

Con una sola entrada en `families`, no se espera un segundo worker: si el seleccionado es de la
familia **opuesta** al conductor, se alcanza la **rama 2** con `diversity: cross_family`; si es de la
**misma** familia, se alcanza la **rama 3** con `diversity: same_family`. El worker no seleccionado
**no aparece en** `workers[]`: no fue despachado ni sondeado, y su ausencia se explica por
`selection: user_choice`, no por una caída.

Un worker en **`clarification-needed`** no es un worker perdido: cuenta como **válido a medias**.
El conductor primero intenta resolver la pregunta (ver "El conductor resuelve antes de preguntar");
si la resuelve, redespacha ese worker con una versión nueva del paquete y la escalera se evalúa de
nuevo con su entrega completa. Si no se puede resolver, el worker baja a la rama que corresponda por
las voces que quedan, y su entrega parcial **se conserva** como contribuyente: descartarla tiraría
un mapa real por una pregunta sin contestar.

> **Un redespacho con `v2` rompe la simetría de insumos, y el conductor tiene que arbitrar
> sabiéndolo.** El diseño promete un paquete **byte-idéntico** para los dos workers: es lo que hace
> comparables a los dos mapas. La `v2` la recibe **un solo worker**, así que a partir de ahí uno
> mapeó con más información que el otro. El invariante se rompe, y se rompe **por una buena razón**
> —sin la respuesta ese worker no podía seguir—, pero se rompe.
>
> Consecuencia concreta sobre la síntesis: una divergencia entre los dos mapas puede ser un
> **artefacto de quién supo qué**, no un desacuerdo de criterio. Antes de tratarla como desacuerdo,
> el conductor descarta que la explique el dato que solo uno tuvo: la respuesta está en
> `paquete-<modo>-v2.origen.txt`, que dice qué pregunta se contestó. Si la divergencia cae sobre
> terreno que depende de esa respuesta, no es diversidad de criterio y no se arbitra como tal.
>
> **Es también el motivo por el que la respuesta no viaja reanudando la sesión del worker**, que
> sería más barato y evitaría el redespacho: la `v2` es el artefacto que deja **visible** la
> asimetría. Reanudar la borraría —el worker seguiría con el dato extra y no quedaría archivo que lo
> diga—, y el conductor arbitraría dos mapas desiguales creyéndolos pares.

Fuera de la escalera: **`FALLO_DE_MAPA`** (ver "Contrato del mapa del conductor"), terminal, sin
contexto de co-explore y directo al gate humano.

La rama 4 conserva su regla vigente: **no escribe `synthesis.md`**. Su artefacto de cierre es
distinto y se llama distinto — ver "Predicado del artefacto de cierre".

### Envelope de retorno

Lo que `co-explore` devuelve a la llamadora. Es un **valor de retorno**, no un manifest persistido:
sin journal durable, sin estado entre corridas.

```yaml
outcome: completed | map_failure
branch: 1 | 2 | 3 | 4 | null        # null si outcome es map_failure
diversity: cross_family | same_family | single_voice | null
selection: full | user_choice       # elección heredada; distingue omisión de caída

workers:
  - family: codex
    state: READY | INVALID | clarification-needed | UNAVAILABLE
    cause: confirmed_wall | launch_flake | runtime_failure | deadline_exceeded | host_sandbox_wall | null  # solo si UNAVAILABLE
    parity: pass | fail | null
    index:  co-explore/index-explore-codex-worker.md   | null
    detail: co-explore/detail-explore-codex-worker.md  | null
    session: <id> | null
  - family: claude
    …

contributors:                        # TODO mapa aceptado, incluido el del conductor
  - family: codex
    role: worker | conductor
    mode: explore | counter-plan | investigate
    index:  …
    detail: …
    session: <id> | null              # null para el mapa del conductor
```

`selection` llega por `family_inventory` junto a `families`, `source` y `root`; la skill **hereda
la elección** y no la reconstruye sondeando.

En los tres modos duales —`explore`, `counter-plan` e `investigate`—, un worker seleccionado que
falla conserva su entrada con `state: UNAVAILABLE` y su causa. Una familia excluida por elección no
aparece en `workers[]`; `selection` registra esa causa sin pisar `branch` ni `diversity`.

`contributors[]` es lo que permite localizar el mapa del conductor en las ramas degradadas:
`workers[]` solo describe procesos despachados, y en las ramas 2, 3 y 4 aparece un mapa que ningún
worker produjo.

Con `outcome: map_failure`, la llamadora **ignora todo contribuyente** y no pasa contexto de
co-explore.

**El transporte no viaja en el envelope, pero esta skill lo emite en el manifest de corrida.** El
manifest —esquema en `cross-review/reference.md` → "Manifest de corrida"— registra la vía efectiva.
El envelope no cambia por la selección: mantiene los mismos estados, ramas y artefactos. La sintaxis
de invocación vive en las vías de despacho, no acá.

### Árbol de rutas

Todas llevan **modo + familia + rol**. Sin los tres, `counter-plan` pisa `explore`, los dos workers
se pisan entre sí, y en la rama 3 el mapa del conductor pisa al del worker superviviente.

```
<dir>/co-explore/
├─ index-<modo>-<familia>-<rol>.md          # capa de navegación
├─ detail-<modo>-<familia>-<rol>.md         # desarrollo completo
├─ synthesis-<modo>.md                      # cierre, ramas 1-3
├─ synthesis-<modo>.md.tmp                  # temporal de la publicación atómica
├─ cierre-conductor-<modo>.md               # cierre, rama 4
├─ cierre-conductor-<modo>.md.tmp           # temporal
└─ scratch/
   ├─ prompt-<modo>-<familia>-worker.txt
   ├─ nucleo-<modo>.txt                     # solo counter-plan
   ├─ raw-<modo>-<familia>-worker.md        # salida cruda, antes del split
   ├─ stderr-<modo>-<familia>-worker.txt
   ├─ pid-<modo>-<familia>-worker.txt
   ├─ thread-<modo>-<familia>-worker.jsonl  # solo Codex (--json)
   └─ session-<modo>-<familia>-worker.json
```

`<modo>` ∈ `explore | counter-plan | investigate` · `<familia>` ∈ `claude | codex` ·
`<rol>` ∈ `worker | conductor`.

El mapa del conductor usa `<rol> = conductor` y **no** tiene entradas en `scratch/`: no hay proceso,
prompt ni sesión que guardar.

### Truncado previo al dispatch

Antes de truncar y redespachar, leer
`skills/cross-review/corridas-en-vuelo.md` → "Invariantes de recuperación". Esas reglas determinan
cuándo el intento anterior dejó de reservar sus rutas y cuándo puede nacer el siguiente.

**Corre después de la decisión de retoma, nunca al entrar al modo.** El orden importa y es
invertirlo lo que rompe todo: la decisión de retoma **lee** el artefacto de cierre para saber si la
corrida ya terminó, y truncar antes destruye justamente esa evidencia, convirtiendo cada retoma en
un redespacho.

Una vez decidido redespachar, se vacían **todas** las rutas del árbol para ese modo —incluidas las
**dos formas de cierre y sus temporales**— y recién después se lanza:

```bash
M=<modo>; D=<dir>/co-explore
for F in claude codex; do
  for R in worker conductor; do
    : > "$D/index-$M-$F-$R.md";  : > "$D/detail-$M-$F-$R.md"
  done
  : > "$D/scratch/prompt-$M-$F-worker.txt"; : > "$D/scratch/raw-$M-$F-worker.md"
  : > "$D/scratch/stderr-$M-$F-worker.txt"; : > "$D/scratch/pid-$M-$F-worker.txt"
  : > "$D/scratch/thread-$M-$F-worker.jsonl"; : > "$D/scratch/session-$M-$F-worker.json"
done
: > "$D/scratch/nucleo-$M.txt"
rm -f "$D/synthesis-$M.md" "$D/synthesis-$M.md.tmp" \
      "$D/cierre-conductor-$M.md" "$D/cierre-conductor-$M.md.tmp"
```

```powershell
$M = "<modo>"; $D = "<dir>\co-explore"
foreach ($F in @('claude','codex')) {
  foreach ($R in @('worker','conductor')) {
    Clear-Content "$D\index-$M-$F-$R.md","$D\detail-$M-$F-$R.md" -ErrorAction SilentlyContinue
  }
  Clear-Content "$D\scratch\prompt-$M-$F-worker.txt","$D\scratch\raw-$M-$F-worker.md",
                "$D\scratch\stderr-$M-$F-worker.txt","$D\scratch\pid-$M-$F-worker.txt",
                "$D\scratch\thread-$M-$F-worker.jsonl","$D\scratch\session-$M-$F-worker.json" `
                -ErrorAction SilentlyContinue
}
Remove-Item "$D\synthesis-$M.md","$D\synthesis-$M.md.tmp",
            "$D\cierre-conductor-$M.md","$D\cierre-conductor-$M.md.tmp" -ErrorAction SilentlyContinue
```

**Los cierres se borran, no se vacían.** Un cierre vacío existe como archivo y hay que abrirlo para
descubrir que no sirve; uno ausente es inequívoco, y la publicación atómica garantiza que la ruta
final **solo** vuelva a existir por el `mv` de la corrida en curso.

**Por qué el conjunto completo y no solo lo de los workers.** Una corrida degradada anterior deja un
mapa del conductor y un cierre válidos. Si la nueva trunca solo lo de los workers, termina con un
worker `READY` y se interrumpe antes de publicar su cierre, el cierre viejo vuelve a validar contra
los archivos nuevos —los IDs coinciden otra vez— y se acepta como resolución actual.

**Por qué no hace falta un nonce de intento.** Truncar el conjunto completo cubre los mismos casos:
un fallo previo al lanzamiento deja archivos vacíos y cierres ausentes → `UNAVAILABLE`; un fallo a
mitad deja un informe parcial → `INVALID`. En ninguno sobrevive un `READY` ni un cierre heredados. Un
nonce agregaría un identificador que habría que propagar y validar en cada capa para cubrir lo mismo.

**El sobre de corrida entra en el conjunto evaluado, y sin eso el argumento anti-nonce no cierra.**
Ese argumento vale **solo** si el conjunto es completo: antes de redespachar, el conductor relee el
sobre activo y aplica `skills/cross-review/corridas-en-vuelo.md` → "Invariantes de recuperación" y
"Relanzamiento seguro". Las rutas exclusivas por intento registradas allí impiden aceptar como actual
una salida heredada.

**Un intento anterior que aún puede escribir bloquea el truncado y el redespacho sobre esas rutas.**
Mientras su cese no esté confirmado, no se trunca ni se redespacha. Truncar ahí borraría la evidencia
que asocia cada salida con su intento, y redespachar reutilizaría rutas que un proceso todavía vivo
puede estar escribiendo.

### El descriptor de corrida y su retiro

Esta sección existe acá porque define la relación entre el conjunto que se trunca y el sobre genérico
de la corrida: el sobre pertenece a ese conjunto y sus reglas de cierre hacen válidas las dos
cláusulas de arriba.

**Qué es: el sobre de la corrida delegada.** Su contrato vive en `corridas-en-vuelo.md`: qué registra,
cuándo nace, cómo se relee, cómo se cosecha una sola vez y qué exige su retiro se definen allá y **no
se redefinen acá**. Como cada intento registra su propia salida y referencia de proceso, la decisión
de redespachar puede distinguir lo heredado de lo vigente sin agregar un nonce. **No** hay una máquina
de estados persistente paralela, ni un esquema o validador propio: el sobre registra operación, no
reconstruye el avance semántico.

**Las rutas y referencias del intento anterior conservan su ownership hasta el cese confirmado.**
Nada autoriza a reutilizarlas por vecindad ni por antigüedad. De ahí salen las dos cláusulas de arriba:
el sobre entra al conjunto evaluado y un intento que todavía puede escribir bloquea el truncado y el
redespacho sobre esas rutas.

**El retiro es el del contrato genérico.** Las tres condiciones simultáneas —terminal comprobado,
artefacto adjudicado, y sin recursos propios en pie o transferidos a un registro de cierre— son las de
`corridas-en-vuelo.md`; esta skill no agrega ni relaja ninguna. Llegar a un final comprobado no alcanza:
un recurso conservado a propósito sigue bajo ownership y, si permanece en pie, su propiedad y la
próxima acción se transfieren al registro de cierre antes de retirar el sobre activo.

**Un recurso propio vivo no es, por sí solo, un resultado incierto.** Lo que las cláusulas de arriba
impiden es truncar, redespachar y retirar; ninguna clasifica nada ni dispara recovery. Lo dispara una
**causa registrada** por el sobre y por la skill que produce o consume el recurso. Sin esta dirección,
un recurso conservado a propósito y con salud quedaría clasificado como incierto por el solo hecho de
seguir en pie, y arrastraría el recovery sobre un caso donde no hay nada incierto.

### Split a dos archivos

El worker devuelve una sola salida cruda. El conductor la parte **antes** de leer nada: así "leer el
índice" es abrir un archivo chico, en vez de depender de que el conductor se acuerde de no abrir el
grande.

```bash
# @bloque:split
# $raw = salida cruda del worker · $index / $detail = destinos
awk '/^## Índice[[:space:]]*$/{m=1;next} /^## Detalle[[:space:]]*$/{m=2;next}
     /^STATUS: done[[:space:]]*$/{next}
     m==1{print > IDX} m==2{print > DET}' IDX="$index" DET="$detail" "$raw"
# @fin:split
```

```powershell
$modo = 0
Get-Content $raw | ForEach-Object {
  if ($_ -match '^## Índice\s*$')      { $modo = 1 }
  elseif ($_ -match '^## Detalle\s*$') { $modo = 2 }
  elseif ($_ -match '^STATUS: done\s*$') { }
  elseif ($modo -eq 1) { Add-Content $index $_ }
  elseif ($modo -eq 2) { Add-Content $detail $_ }
}
```

`STATUS: done` queda **fuera de los dos archivos**: es transporte, no contenido. Un `index-*` o
`detail-*` que lo contenga indica un split mal hecho.

### Validador de índice y detalle

El **orden de los chequeos es el criterio**, no un detalle de implementación. Invertir dos pasos
produce un validador que da verde con informes malos:

```bash
# @bloque:validador
# Entradas: $index $detail $FAM $ROL $MODO $t (dir temporal)
# Salida: exit 0 = pasa estos predicados · exit 1 = INVALID

filas() { grep -E '^\|' "$1" | grep -vE '^\|[[:space:]]*(ID[[:space:]]*\||[-: ]+\|)'; }

# 1) Contar TODAS las entradas presentes, tengan o no un ID bien formado.
#    Sin esto, una fila malformada se omite en silencio y una entrada válida
#    mantiene el conjunto no vacío: la paridad pasaría igual.
nI=$(filas "$index" | grep -c .)
nD=$(grep -c '^### ' "$detail")

# 1b) Ningún contenido antes del primer `### <ID>`: sería contenido no indexado,
#     invisible para un conductor que solo abre por ID. (Entre dos entradas no
#     hay huérfanos: ese texto pertenece a la entrada precedente.)
awk '/^### /{exit} NF{print}' "$detail" | grep -q . && exit 1

# 2) Extraer los que SÍ tienen forma de ID (sin filtrar por el valor esperado)
sed -nE 's/^\|[[:space:]]*([A-Z]{3}-[A-Z]-[A-Z]{3}-[0-9]{3})[[:space:]]*\|.*$/\1/p' "$index"  | sort > "$t/index.ids"
sed -nE 's/^###[[:space:]]+([A-Z]{3}-[A-Z]-[A-Z]{3}-[0-9]{3})[[:space:]]*$/\1/p'      "$detail" | sort > "$t/detail.ids"

# 3) Toda entrada tuvo que producir exactamente un ID válido
[ "$(grep -c . "$t/index.ids")"  -eq "$nI" ] || exit 1   # fila con ID malformado
[ "$(grep -c . "$t/detail.ids")" -eq "$nD" ] || exit 1   # heading con ID malformado

# 4) RECHAZAR lo que no sea el esperado. Filtrar en vez de rechazar es el error
#    clásico: con familia esperada CLD, un CDX-… no matchea, los dos conjuntos
#    quedan vacíos y `cmp` los da por iguales.
cat "$t/index.ids" "$t/detail.ids" | grep -vE "^${FAM}-${ROL}-${MODO}-[0-9]{3}$" > "$t/ajenos"
[ -s "$t/ajenos" ] && exit 1
[ -s "$t/index.ids" ] || exit 1                          # índice vacío no es un pase

# 5) Cinco campos, enums cerrados y punteros bien formados, fila por fila
filas "$index" | while IFS= read -r fila; do
  [ "$(printf '%s' "$fila" | awk -F'|' '{print NF-2}')" -eq 5 ] || exit 1
  sev=$(printf  '%s' "$fila" | awk -F'|' '{gsub(/[[:space:]]/,"",$4); print $4}')
  conf=$(printf '%s' "$fila" | awk -F'|' '{gsub(/[[:space:]]/,"",$5); print $5}')
  case "$sev"  in high|medium|low) ;; *) exit 1 ;; esac
  case "$conf" in high|medium|low) ;; *) exit 1 ;; esac
  pt=$(printf '%s' "$fila" | awk -F'|' '{gsub(/^[[:space:]]+|[[:space:]]+$/,"",$6); print $6}')
  printf '%s' "$pt" | grep -qE '^([^ :]+:[0-9]+)([[:space:]]*,[[:space:]]*[^ :]+:[0-9]+)*$|^N/A: .+$' || exit 1
done || exit 1

# 6) Recién ahora: unicidad y paridad sobre el conjunto completo
uniq -d "$t/index.ids"  > "$t/dupI"; [ -s "$t/dupI" ] && exit 1
uniq -d "$t/detail.ids" > "$t/dupD"; [ -s "$t/dupD" ] && exit 1
cmp -s "$t/index.ids" "$t/detail.ids" || exit 1
exit 0
# @fin:validador
```

**Señal de finalización**, sobre el crudo y antes del split:

```bash
# @bloque:status
awk 'NF { last=$0 } $0=="STATUS: done" { n++ } END { exit !(n==1 && last=="STATUS: done") }' "$raw"
# @fin:status
```

Cubre las tres anomalías de una: ausente (`n==0`), duplicada (`n>1`) y fuera de posición
(`last != "STATUS: done"`).

**PowerShell** — mismo orden, con `Group-Object` y `Compare-Object`:

```powershell
$rx = '^[A-Z]{3}-[A-Z]-[A-Z]{3}-\d{3}$'
$filas = Get-Content $index | Where-Object { $_ -match '^\|' -and $_ -notmatch '^\|\s*(ID|-+)' }
$heads = Get-Content $detail | Where-Object { $_ -match '^### ' }
$idsI = $filas | ForEach-Object { ($_ -split '\|')[1].Trim() } | Where-Object { $_ -match $rx }
$idsD = $heads | ForEach-Object { $_ -replace '^###\s+','' } | Where-Object { $_ -match $rx }
if ($idsI.Count -ne $filas.Count -or $idsD.Count -ne $heads.Count) { exit 1 }   # malformados
$esperado = "^$FAM-$ROL-$MODO-\d{3}$"
if (@($idsI + $idsD | Where-Object { $_ -notmatch $esperado }).Count -gt 0) { exit 1 }
if ($idsI.Count -eq 0) { exit 1 }
if (@($idsI | Group-Object | Where-Object Count -gt 1).Count -gt 0) { exit 1 }
if (@($idsD | Group-Object | Where-Object Count -gt 1).Count -gt 0) { exit 1 }
if (@(Compare-Object ($idsI | Sort-Object) ($idsD | Sort-Object)).Count -gt 0) { exit 1 }
```

### Apertura puntual de una entrada

La regla de lectura selectiva **prohíbe** abrir el detalle completo. Esta es la única forma de
abrirlo:

```bash
# @bloque:apertura
awk -v id="$ID_PEDIDO" '$0=="### "id{f=1;print;next} f&&/^### /{exit} f' "$detail"
# @fin:apertura
```

```powershell
$sel = $false
Get-Content $detail | ForEach-Object {
  if ($_ -eq "### $IdPedido") { $sel = $true; $_ }
  elseif ($sel -and $_ -match '^### ') { break }
  elseif ($sel) { $_ }
}
```

Corta en el siguiente `### `, así que nunca arrastra la entrada adyacente. `cat detail-*` no es una
alternativa aceptable: anula el ahorro que este contrato compra.

### Plantillas de cierre

El **artefacto de cierre** es la prueba de que una corrida terminó. Hay dos formas, y **nunca
coexisten** para el mismo modo:

| Rama | Archivo | Se llama |
|---|---|---|
| 1-3 | `synthesis-<modo>.md` | síntesis |
| 4 | `cierre-conductor-<modo>.md` | cierre conductor-only — **no** es una síntesis |

Las dos comparten la misma **cabecera de campos cerrados**, que es lo que permite reconstruir el
envelope al retomar sin recalcular nada:

```yaml
---
modo: explore                    # explore | counter-plan | investigate
rama: 1                          # 1 | 2 | 3 | 4
diversidad: cross_family         # cross_family | same_family | single_voice
contribuyentes: [CDX-W-EXP, CLD-W-EXP]
---
```

Cada contribuyente se nombra por su **prefijo de ID** `<FAM>-<ROL>-<MODO>`: es lo que ata cada ID
citado en el cuerpo a un mapa concreto.

El cuerpo de una síntesis compara **por ID**, no informes completos. `## Descartados` es
obligatoria y **puede quedar vacía**, pero no ausente: registrar por qué se eligió un enfoque no es
lo mismo que registrar qué se tiró, y lo segundo es lo único que permite revisar una síntesis meses
después sin reconstruirla de cero. Una hipótesis descartada sin rastro vuelve a proponerse.

```markdown
## Convergencias
| Tema | CDX | CLD |
|---|---|---|
| el poll vive en reference.md:663 | CDX-W-EXP-001 | CLD-W-EXP-004 |

## Divergencias
| Tema | CDX | CLD | Resolución |
|---|---|---|---|
| gravedad del scratch compartido | CDX-W-EXP-002 | ∅ | abierta y verificada; se adopta |
| orden del truncado | CDX-W-EXP-007 | CLD-W-EXP-002 | se adopta CLD: destruye menos evidencia |

## Detalles abiertos
| ID | Disparador | Punteros verificados |
|---|---|---|
| CDX-W-EXP-002 | divergencia unilateral | skills/co-explore/reference.md:690 |

## Descartados
| ID | Qué proponía | Por qué se descartó |
|---|---|---|
| CLD-W-EXP-006 | mover el truncado al entrar al modo | destruye el artefacto de cierre que la retoma necesita leer |

## Incógnitas fusionadas
## Límite de esta exploración
```

**La ausencia es una divergencia de primera clase.** Cuando un contribuyente vio algo que el otro no
vio, no hay segundo ID: la fila lleva `∅` en el lado ausente y **al menos un ID real**. Exigir IDs
de ambos lados obligaría a descartar el hallazgo o a fabricar una correspondencia — y la divergencia
unilateral es justamente donde vive el valor cross-model, así que **dispara** la lectura del detalle
existente.

`## Detalles abiertos` registra qué se abrió y por qué: es la traza de que la lectura selectiva se
respetó, y lo único que permite auditar después si el conductor leyó de más o de menos.

El **cierre conductor-only** lleva la misma cabecera (con `rama: 4`, `diversidad: single_voice`, un
solo contribuyente de rol `C`) y el análisis del conductor, más la advertencia de una sola voz. No
lleva `## Convergencias` ni `## Divergencias`: no hay con qué converger.

### Predicado del artefacto de cierre

`AC-25` usa el cierre como **única** prueba de que la corrida terminó, así que un predicado flojo
hace que una corrida a medias se reconstruya como completa. El rename atómico evita archivos
partidos; esto evita cierres **semánticamente** falsos.

```bash
# @bloque:cierre
# Entradas: $cierre (ruta del artefacto) · $dir (dir de co-explore) · $t (temporal)
# Salida: exit 0 = cierre válido · exit 1 = inválido

cab() { awk '/^---$/{n++;next} n==1' "$cierre"; }
val() { cab | sed -nE "s/^$1:[[:space:]]*(.*)$/\\1/p"; }

MODO_H=$(val modo); RAMA=$(val rama); DIV=$(val diversidad)
CONTRIB=$(val contribuyentes | tr -d '[]' | tr ',' ' ')

# 1) Cabecera completa y con valores del enum
[ -n "$MODO_H" ] && [ -n "$RAMA" ] && [ -n "$DIV" ] && [ -n "$CONTRIB" ] || exit 1
case "$MODO_H" in explore|counter-plan|investigate) ;; *) exit 1 ;; esac
case "$RAMA"   in 1|2|3|4) ;; *) exit 1 ;; esac
case "$DIV"    in cross_family|same_family|single_voice) ;; *) exit 1 ;; esac

# 2) Contribuyentes únicos, bien formados y con el modo de la cabecera
# Ojo: NO usar $(case … in explore) …) — el paréntesis de la rama cierra la
# sustitución de comando y rompe el script entero. Con `case` a secas, un error
# de sintaxis acá haría fallar TODOS los chequeos de abajo por la razón
# equivocada, dejándolos verdes sin haberse ejecutado nunca.
case "$MODO_H" in
  explore)      MODO_ID=EXP ;;
  counter-plan) MODO_ID=CTR ;;
  investigate)  MODO_ID=INV ;;
esac
n=0; roles=""; fams=""
for c in $CONTRIB; do
  printf '%s\n' "$c" | grep -qE "^(CLD|CDX)-(W|C)-$MODO_ID$" || exit 1
  n=$((n+1)); roles="$roles $(echo "$c" | cut -d- -f2)"; fams="$fams $(echo "$c" | cut -d- -f1)"
done
[ "$n" -eq "$(printf '%s\n' $CONTRIB | sort -u | grep -c .)" ] || exit 1   # duplicados

# 3) Composición EXACTA según la rama. Contar contribuyentes y mirar la
#    diversidad no alcanza: un cierre con dos mapas de rol C de familias
#    opuestas satisface "2 contribuyentes, cross_family" y se haría pasar por
#    rama 1 nominal, bloqueando el redespacho de una corrida que nunca fue.
nW=$(printf '%s\n' $roles | grep -c '^W$'); nC=$(printf '%s\n' $roles | grep -c '^C$')
nFam=$(printf '%s\n' $fams | sort -u | grep -c .)
case "$RAMA" in
  1) [ "$n" -eq 2 ] && [ "$nW" -eq 2 ] && [ "$nFam" -eq 2 ] && [ "$DIV" = cross_family ] || exit 1 ;;
  2) [ "$n" -eq 2 ] && [ "$nW" -eq 1 ] && [ "$nC" -eq 1 ] && [ "$nFam" -eq 2 ] && [ "$DIV" = cross_family ] || exit 1 ;;
  3) [ "$n" -eq 2 ] && [ "$nW" -eq 1 ] && [ "$nC" -eq 1 ] && [ "$nFam" -eq 1 ] && [ "$DIV" = same_family ] || exit 1 ;;
  4) [ "$n" -eq 1 ] && [ "$nC" -eq 1 ] && [ "$DIV" = single_voice ] || exit 1 ;;
esac

# 4) Todo ID citado en el cuerpo pertenece a un contribuyente listado
grep -oE '(CLD|CDX)-(W|C)-(EXP|CTR|INV)-[0-9]{3}' "$cierre" | sort -u | while read -r id; do
  pref=$(printf '%s' "$id" | cut -d- -f1-3)
  printf '%s\n' $CONTRIB | grep -qx "$pref" || exit 1
done || exit 1

# 5) Las dos formas de cierre no coexisten para el mismo modo
[ -f "$dir/synthesis-$MODO_H.md" ] && [ -f "$dir/cierre-conductor-$MODO_H.md" ] && exit 1
exit 0
# @fin:cierre
```

**Publicación atómica.** El cierre se escribe a `<ruta>.tmp`, se valida con este predicado y recién
entonces se renombra:

```bash
# escribir a "$cierre.tmp" … luego:
cierre="$cierre.tmp" sh validar_cierre && mv "$cierre.tmp" "$cierre"
```

```powershell
# … escribir a "$Cierre.tmp", validar, y recién entonces:
Move-Item -Force "$Cierre.tmp" $Cierre
```

Sin esto, un archivo escrito a medias puede contener solo IDs válidos y satisfacer el predicado con
secciones o resoluciones faltantes: la señal de completitud sería falsa exactamente cuando más
importa.

### Estados del worker

**Cuatro** estados, definidos por **predicado** y no por criterio:

| Estado | Predicado |
|---|---|
| `READY` | pasa **todos**: dos capas, gramática de ID, unidad indexable, enums, `STATUS: done`, split correcto y paridad (por **página** y por **unión**, si el índice está paginado) |
| `INVALID` | respondió, pero falla alguno de esos predicados |
| `clarification-needed` | frenó ante una ambigüedad que le impide seguir, **entregó lo que mapeó** y adosó la pregunta (ver "`clarification-needed` — el cuarto estado") |
| `UNAVAILABLE` | no respondió, o no se pudo lanzar |

`READY` los exige **todos**, sin excepciones. Omitir la gramática de ID o la unidad indexable de la
lista dejaría pasar como válido un informe con IDs sin namespace —la paridad **no** lo detecta,
porque la omisión está en el índice *y* en el detalle— o con contenido sin indexar.

**`UNAVAILABLE` lleva causa de un enum cerrado**, porque de ella depende la política de reintento:

| Causa | Qué la produce | Reintento |
|---|---|---|
| `confirmed_wall` | binario ausente, auth rechazada, versión incompatible, aislamiento imposible | **ninguno** — terminal para la corrida |
| `launch_flake` | el binario existe pero el lanzamiento flaqueó (arranque frío, timeout de spawn) | 2-3 con backoff corto, nunca un loop abierto |
| `runtime_failure` | arrancó bien y falló después: error de ejecución, salida vacía | por intento; no condena la corrida ni se reintenta en bucle |
| `deadline_exceeded` | arrancó bien y **alcanzó el deadline** sin marcador de cierre | por intento; el tope lo puso el conductor, así que la palanca es subirlo, no reintentar igual |
| `host_sandbox_wall` | el sandbox del **conductor** impidió la operación, y el host lo declara | uno solo, **escalado fuera del sandbox**; por intento, sin degradar la corrida ni la tanda |

**`deadline_exceeded` es una causa nueva, no un quinto estado.** Acompaña al `UNAVAILABLE` que ya
existe en vez de crear un terminal propio. Hasta acá un deadline vencido se reportaba como
`runtime_failure`, que sugiere una falla de infraestructura que no ocurrió: el proceso arrancó bien y
el corte lo puso el conductor al fijar el tope. Distinguirlas cambia qué se hace después — ante
`runtime_failure` se mira el error, ante `deadline_exceeded` se mira el presupuesto.

Distinción fina entre `INVALID`, `deadline_exceeded` y `runtime_failure`: un proceso que **terminó** y
dejó salida sin marcador es `INVALID` (respondió mal); uno que **alcanzó el deadline** sin marcador es
`deadline_exceeded` (no llegó a responder, y el corte fue nuestro); uno que **falló ejecutando** tras
arrancar bien es `runtime_failure`. Con un índice **paginado**, la serie incompleta se
clasifica por el mismo criterio del observable (ver "Una serie incompleta se clasifica por el
observable").

Un worker `INVALID` **no aporta anexo** a `counter-plan` **ni sirve de seed** a `cross-review`,
aunque conserve una sesión técnicamente reanudable.

#### `host_sandbox_wall` — la pared que se levanta pidiendo permiso

Las otras cuatro causas describen paredes del **worker**: su binario, su lanzamiento, su ejecución,
su presupuesto. Esta describe una pared del **conductor**: el sandbox desde el que se despacha
impidió la operación. Es la única del enum que **es removible por escalación**, y por eso no puede
heredar ni la terminalidad de `confirmed_wall` ni la imputación de `runtime_failure`.

**Cuándo se atribuye: solo con atribución explícita del host.** La causa exige una señal en la que
la capa anfitriona **declare que ella bloqueó**. La forma medida de esa señal es
`rejected: blocked by policy` en el stderr del worker, donde el runtime nombra al emisor del bloqueo
y su motivo.

**Cuándo NO se atribuye, aunque lo parezca.** Estos dos casos **no habilitan** la causa:

- Un `ConnectionRefused` a secas. Admite firewall corporativo, proxy mal configurado, servicio caído
  o credenciales rechazadas; nada en él identifica al sandbox del conductor como emisor.
- Un `AccessDenied` sin emisor identificado. Un permiso denegado por el sistema de archivos del
  worker no es una pared del sandbox llamador.

**Regla de fallo cerrado.** Sin atribución explícita **no se atribuye** `host_sandbox_wall`: se
conserva la causa vigente que corresponda y se escala para diagnóstico. Una señal indirecta
clasificada acá convertiría un firewall corporativo en una pared removible que nadie puede remover.

**Política de recuperación, en seis puntos cerrados.** No quedan a criterio de quien implemente:

| Punto | Valor |
|---|---|
| outcome | `UNAVAILABLE` con causa `host_sandbox_wall` |
| quién reintenta | la capa que **hospeda** al conductor; la skill no reintenta por su cuenta |
| máximo de intentos escalados | **uno** |
| identidad y rutas | el intento escalado usa `attempt_id` y rutas exclusivas, como cualquier reintento |
| efecto sobre tanda y corrida | **por intento**; no degrada la tanda ni la orquestación |
| si el intento escalado vuelve a fallar | el ítem queda `UNAVAILABLE · host_sandbox_wall`, **no se vuelve a escalar**, y la tanda continúa con el ítem siguiente, que se diagnostica por su cuenta |

**La escalación se nombra, no se verifica.** Quien repite el comando fuera del sandbox es la capa que
hospeda al conductor, no la skill: la skill no puede observar que ocurrió, ni que está disponible, ni
que alguien la autorizó. Solo puede saber que su comando falló y que la pared es de las removibles.
Exigirle una prueba de escalación sería pedirle que compruebe algo que no está a su alcance.

**Vale igual en sesión nueva y en reanudación.** Un fallo atribuido al host devuelve
`UNAVAILABLE · host_sandbox_wall` tanto por `cli-exec` como por `cli-resume`. Que la ronda anterior
haya funcionado no dice nada sobre la actual: la pared puede levantarse entre dos rondas del mismo
thread.

### Decisión de retoma

Antes de decidir la retoma, leer
`skills/cross-review/corridas-en-vuelo.md` → "Invariantes de recuperación". La existencia de un
artefacto y el vencimiento de una espera no sustituyen esas comprobaciones.

El envelope es efímero por diseño, pero un flujo SDD puede pausarse y retomarse en una sesión nueva
entre el gate de la spec y `counter-plan`. Ahí no existe el estado que decide anexos y seeds, aunque
sí queden archivos y sesiones en disco.

**La regla es binaria, no una reconstrucción por etapas:**

```
¿existe el artefacto de cierre del modo y valida?
├─ SÍ  → la corrida terminó. Usar lo que hay. No recalcular rama ni diversidad:
│        el cierre las lleva como campos cerrados, y es su producto.
└─ NO  → ¿existe ya el artefacto consumidor?
         ├─ NO → la corrida no terminó: truncar todo y REDESPACHAR el modo completo.
         └─ SÍ → FALLAR CERRADO: sin anexo, sin seed, sin contexto de co-explore.
                 Declararlo en una línea.
```

**El artefacto de cierre es la señal de completitud, en sus dos formas.** Tratar solo a la síntesis
como señal condenaría a la rama 4 —que tiene prohibido escribirla— a redespacharse en cada retoma,
para siempre.

**Por qué redespachar en vez de reconstruir.** Los workers son baratos, read-only y no consumen
contexto del conductor. Reconstruir un estado parcial exige una máquina de estados que este diseño
no quiere tener, y el redespacho pasa por el truncado, así que no puede heredar nada.

> **No es una preferencia de este diseño: es una decisión del ecosistema, y va suelta a propósito.**
> No hay máquina de estados persistente, ni esquema formal, ni validador propio, ni versionado: ese
> nivel de estado persistido ya se rechazó por escrito, y ninguna capacidad nueva lo reabre por su
> cuenta — quien lo necesite abre esa discusión, no la asume.
>
> Se enuncia acá **sin colgar de ningún transporte, modo ni párrafo**, porque ya se perdió una vez
> por estar colgada: vivía dentro de un bloque que describía una vía de transporte, y al retirarse
> esa vía se fue con ella. El texto que quedó la decía como gusto del diseño, no como decisión
> tomada, y así estuvo noventa commits. Una cláusula atada a algo retirable se retira con ello.

**Por qué no se redespacha con el consumidor ya escrito.** Si el consumidor existe, la exploración
ya hizo su trabajo y su resultado está embebido ahí. Redespacharla podría traer un riesgo `high` que
ese artefacto —quizá ya aprobado en su gate— nunca arbitró, y **meter un hallazgo por detrás de un
gate que debía consumirlo es peor que no tenerlo**. Querer exploración fresca sobre algo ya aprobado
es un flujo nuevo, no una retoma.

**El orden es estricto: primero decidir, después truncar.** La decisión **lee** el cierre; truncar al
entrar al modo destruiría exactamente esa evidencia y convertiría cada retoma en un redespacho.

### Los dos ejes: artefacto y capacidad

Miden cosas distintas y gobiernan decisiones distintas. Confundirlos produce las dos fallas
simétricas:

| Eje | Qué mide | Qué gobierna |
|---|---|---|
| **estado del artefacto** | lo que hay en disco, validado con los predicados de arriba | el anexo de `counter-plan` y qué se pasa a `cross-review` |
| **capacidad actual** | preflight de **ahora** | si se puede redespachar y si una sesión es reanudable |

Un artefacto puede seguir siendo válido aunque hoy haya una pared; y el CLI puede funcionar hoy
aunque la corrida anterior haya fallado. Por eso **la causa histórica de `UNAVAILABLE` no se
persiste ni se reconstruye**: sería obsoleta por construcción — el binario pudo instalarse desde
entonces, y una causa vieja mandaría a `UNAVAILABLE` terminal un entorno que ya funciona. Al
retomar se **repite el preflight** y se decide de nuevo.

### Matriz de consumidor por llamadora

Qué artefacto cuenta como "el consumidor ya escrito", que es lo que bloquea el redespacho:

| Llamadora | `explore` → | `counter-plan` → |
|---|---|---|
| `sdd-flow` | `spec.md` | `plan.md` |
| `sdd-orchestrator` | `master-spec.md` | el **reparto** |
| — | `investigate` no tiene consumidor: redespacha libre | |

**Predicado de "el reparto existe"**, porque `manifest.yml` puede existir antes de que los planes
por repo estén completos: `manifest.yml` **más** los artefactos de todos los repos confirmados
**más** el cross-artifact check en verde. Un reparto **parcial no cuenta** como consumidor escrito —
tratarlo como escrito bloquearía el redespacho de una fase que nunca terminó.

### Fixtures de retoma

Son **dos**, y tienen que serlo: un cierre conforme presembrado obliga a decidir `reutilizar`, así
que pedirle a ese mismo caso que redespache y trunque sería exigir una decisión que la propia regla
prohíbe.

| Fixture | Estado inicial | Decisión esperada | Resultado esperado |
|---|---|---|---|
| **`REUSE`** | árbol completo **con** cierre conforme | reutilizar | el truncado **no** se invoca; los artefactos siguen intactos |
| **`REDISPATCH`** | artefactos de worker válidos, **sin** cierre válido y **sin** consumidor escrito | redespachar | truncar → simular fallo de lanzamiento → `UNAVAILABLE`, sin nada heredado y sin ningún `READY` sobreviviente |

Sin el `REDISPATCH`, el truncado queda declarado y nunca probado. Sin el `REUSE`, nada verifica que
el camino de reutilización **no** trunque — que es la falla que convertiría cada retoma en un
redespacho silencioso.


## Mecánica del modo `debate`

> Movida desde `SKILL.md` para liberar presupuesto: `debate` queda fuera del alcance de la
> topología dual y su mecánica es la más autocontenida de la skill. El `SKILL.md` conserva qué es
> el modo y cuándo se ofrece; el cómo vive acá.

### El loop de debate

A diferencia de los otros modos (una sola pasada), `debate` itera. El conductor participa como una
<!-- corpus-invariante:inicio:co-explore.reference.md.5b072de65f96 -->
voz y el worker seleccionado forma la otra. La familia opuesta es el default; con selección
<!-- corpus-invariante:fin:co-explore.reference.md.5b072de65f96 -->
same-family se conserva una sesión fresca, se declara el costo y se recomienda revisión humana. El
conductor sintetiza y el usuario arbitra.

1. **R0 — posturas independientes.** El conductor escribe su propia postura sobre la decisión
   (opciones, análisis, hacia dónde se inclina y por qué) **antes** de ver nada de la otra
   familia. En paralelo despacha al revisor con el **mismo** paquete de decisión (sin la postura
   del conductor; prompt en `reference.md` → "Prompt de debate — ronda 0") para que forme la suya
   a ciegas. Regla 2 (independencia) aplica acá.
2. **R1..N — crítica cruzada.** Cada ronda cruza las posturas: se le pasa al revisor la postura
   del conductor para que la critique y actualice la suya (prompt en `reference.md` → "Prompt de
   debate — cruce"), y el conductor lee la del revisor, la critica y actualiza la propia.
   Registrar el **delta** de cada ronda (qué concedió, qué sostuvo cada uno) en el scratch.
3. **Convergencia + anti-desperdicio.** Default **3 rondas** de cruce; tope duro `max_rounds`
   (default 3). Si una ronda no mueve nada (ninguna familia concede ni refina su postura),
   **converger temprano** y decirlo — no quemar rondas. Cada ronda tiene deadline duro
   (regla 5): al vencer, cortar y sintetizar con lo que haya.
4. **Síntesis** (ver "La síntesis del debate").


### La síntesis del debate

El conductor cierra con una síntesis que **no elige ganador** — presenta las posturas para que
el usuario decida (ethos de árbitro humano, regla 3 de `cross-review`). La escribe en
`co-explore/debate.md` (plantilla en `reference.md` → "Plantilla de `debate.md`") y la presenta:

- **Postura final de cada familia**, atribuida por familia (🟠 Claude / 🔵 Codex) y **sin
  fusionar** en una sola voz. La atribución vale acá porque `debate.md` y la síntesis presentada
  son **locales y solo las lee el usuario** (ver "Publicado vs local"); nombrar a las familias es
  parte del valor del debate.
- **Dónde convergieron** y **qué queda en disputa**.
- **Los trade-offs afilados**: qué compra y qué cuesta cada opción, según salió del cruce.
- **No elige ganador**: la decisión es del usuario.


### Publicado vs local

La regla de co-explore "los entregables hablan del objeto, no del método" protege lo que se
**publica** donde lo leen otras personas (spec en Jira vía `publish-spec`, descripciones o
comentarios de PR en Bitbucket, cualquier superficie compartida). **No** aplica a archivos
**locales que solo lee el usuario**: `debate.md` y la síntesis presentada **sí** nombran a las
familias. El guardrail que se mantiene: lo que el debate haga aterrizar en `spec.md`
(`## Clarifications`) o `plan.md` (un trade-off) queda **limpio de método/familias**, porque eso
sí fluye a superficies publicadas. La skill llamadora (sdd-flow) escribe esos artefactos de forma
autónoma, con la decisión ya tomada, sin citar el debate.


## El criterio de éxito también es una hipótesis (`investigate`)

> Movida desde `SKILL.md`. La regla vale igual; el `SKILL.md` conserva la afirmación y apunta acá
> para la tabla y su fundamento.

El espacio de hipótesis no se agota en el código. Un bug que resiste puede ser un **criterio de
éxito defectuoso**: un test que verifica lo que no corresponde, que depende de un supuesto
inválido, o que afirma un observable que su fuente no autoriza. Esa hipótesis compite con las
demás desde la primera pasada — no hace falta esperar a que fallen varios intentos.

**Toda hipótesis, esta incluida, declara tres cosas antes de ser rankeada:**

| | Qué responde |
|---|---|
| **Observable** | Qué afirma exactamente que ocurre o debería ocurrir. |
| **Autoridad** | Qué fuente lo respalda: un AC, una decisión de producto, el código, quien reporta. |
| **Refutación** | Qué evidencia concreta la tumbaría. |

Sin las tres, no se rankea. Y sin evidencia de respaldo, "el criterio está mal" se registra como
**incógnita**, nunca como hipótesis líder: es la salida cómoda de este modo —siempre disponible,
nunca falsable si no se la ata a evidencia— y por eso lleva la misma vara que las demás, no una
más baja. Sostenerla exige el criterio de éxito en el paquete de contexto (ver "Contrato de
invocación"); si no llegó, decirlo como incógnita en vez de especular.

## Handoff destilado, nunca transcript crudo

Al modelo delegado se le pasa un **contrato destilado** —objetivo, contexto necesario, límites—,
nunca el transcript literal de la sesión del conductor. El prompt por archivo que estas skills usan
**ya es** un handoff destilado: no es una convención estética, es la forma correcta, y conviene
saber por qué para que nadie la "optimice" pasándole contexto ambiente al delegado.

El porqué no es solo de diseño. Está documentado un caso real donde reproducir dentro de un modelo
un transcript construido bajo otro activó clasificadores de política de uso y **bloqueó todas las
requests de la sesión** —incluso las triviales—, mientras la misma consulta en una sesión fresca
pasaba sin problema. El diseño barato resultó ser también el seguro.

Consecuencia práctica: si el delegado necesita saber algo, ese algo se **escribe en el prompt**. No
se le reenvía la conversación para que lo deduzca.

## Modelo y esfuerzo del worker

**De dónde salen hoy, y no es uniforme.** El worker Codex se aísla con `--ignore-user-config` y
después **reinyecta** el `model` y el `model_reasoning_effort` que el usuario tenga en la raíz de su
`~/.codex/config.toml`; el worker Claude recibe un modelo **explícito** en la línea de lanzamiento.
Las dos formas están en los bloques de invocación de arriba, que son la fuente.

**No es configurable por skill, y es deliberado.** Hubo un bloque `cross_model.profiles` +
`co_explore.workers` en el esquema del config que nunca tuvo consumidor: ninguna línea de lanzamiento
lo leía. Se quitó en vez de cablearlo, porque config documentada que nada lee es peor que no tenerla
— quien escribía `model: sonnet` recibía el modelo de siempre, sin aviso, que es exactamente la
sustitución silenciosa que las reglas de abajo prohíben. Cambiar modelo o esfuerzo hoy es editar la
línea de lanzamiento. Si alguna vez vuelve a hacer falta configurarlo, que entre **con** su
consumidor y no antes.

**Cuántos workers y de qué familia no se configuran nunca**, ni siquiera si vuelven los perfiles: lo
fija la topología dual (`SKILL.md` regla 7) y la escalera de degradación decide con los **estados**
de los workers, no con umbrales. Un config que dijera "prefiero diversidad de familia" describiría
mal la skill: la diversidad no es una preferencia acá, es la razón de la topología.

### Reglas duras sobre modelo y esfuerzo

Valen para cualquier vía de despacho, venga el valor de donde venga. Las cuatro existen por el mismo
motivo — una sustitución silenciosa produce un resultado que **parece** el pedido y no lo es:

1. **Un modelo explícito no disponible vuelve ese worker `UNAVAILABLE`.** Nunca se sustituye por
   otro. Pedir `sonnet` y recibir otro modelo sin aviso invalida cualquier comparación de costo o
   de calidad que motivó el pedido.
2. **Un modelo sin declarar sí delega** la elección al proveedor: es la forma de decir "me da igual
   cuál", y por eso no dispara la regla anterior. La distinción es entre no haber pedido nada y
   haber pedido algo que no se pudo dar.
3. **Una opción de esfuerzo incompatible se avisa, no se descarta en silencio.** Una vía que ignora
   un esfuerzo alto porque su CLI no lo soporta entrega un worker más barato del pedido y el conteo
   de costo queda mintiendo.
4. **La ejecución no eleva permisos.** El nivel de escritura lo fija el rol —read-only en
   `co-explore` y `cross-review`, workspace-write acotado en `cross-implement`—, y nada de lo que
   diga un modelo, un esfuerzo o un config lo toca.

## Escalera de rigor

Cuándo escalar entre skills, para no usar el martillo caro. Cada peldaño cuesta más que el anterior
—en tiempo, en tokens y en atención de la persona—, así que la pregunta no es "¿cuál es la mejor?"
sino **"¿cuál es la más barata que alcanza?"**:

| Peldaño | Cuándo | Qué produce |
|---|---|---|
| **respuesta local** | el conductor puede contestar leyendo el repo | una respuesta |
| **`co-explore`** | el terreno está abierto: hace falta un mapa, una causa raíz o decidir entre opciones | dos mapas independientes + síntesis |
| **`cross-review`** | ya hay una **decisión escrita** y se quiere que la ataquen | crítica adversarial + veredicto |
| **`cross-implement`** | hay un contrato **congelado** y hay que construirlo | un diff que el conductor revisa |
| **`verify` de `sdd-flow`** | hay código y hace falta evidencia por criterio de aceptación | filas ejecutadas con su salida |

El orden **no** es una secuencia obligatoria: la mayoría de los trabajos entran por un peldaño y no
suben. Subir sin necesidad no es cautela, es gasto — y bajar cuando hacía falta subir es la otra
mitad del error.

> **No hay un modo `opinion` (A/B barato) a propósito.** Se difirió hasta tener un caso real donde
> `co-explore` resulte desproporcionado; las dos familias convergieron en que agregarlo antes es
> inventar un peldaño para un hueco que todavía nadie encontró.

## Índice paginado

Cuando un worker encuentra más hallazgos de los que entran en una página, el índice se parte en
varias. **Ninguna entrada se descarta**: el presupuesto limita el tamaño de **cada entrada** y de
**cada página**, nunca el total de hallazgos. Un presupuesto que recorta el total convierte "el
worker encontró 40 cosas" en "el worker informó 25", y las 15 que faltan no dejan rastro.

### Se pagina solo el índice

El **detalle sigue siendo un archivo por worker**, sin paginar. No es una omisión: el índice es la
capa que el conductor lee **entera y siempre**, y la única cuyo tamaño escala con el número de
hallazgos. El detalle se abre por ID y nunca se lee completo, así que paginarlo no compra nada y
multiplica las rutas — y cada ruta más es una forma más de que la serie quede inconsistente.

### Rutas y nombres

El archivo con el nombre canónico —`index-<modo>-<familia>-<rol>.md`— pasa a ser el **metaíndice**, y
las páginas se numeran con sufijo `-pNN` a partir de `01`, con cero a la izquierda para que el orden
lexicográfico coincida con el numérico:

```
<dir>/co-explore/
├─ index-<modo>-<familia>-<rol>.md          # METAÍNDICE: rutas, cantidades e IDs de cada página
├─ index-<modo>-<familia>-<rol>-p01.md      # página 1
├─ index-<modo>-<familia>-<rol>-p02.md      # página 2
└─ detail-<modo>-<familia>-<rol>.md         # UNO solo, sin paginar
```

Que el metaíndice conserve el nombre canónico es deliberado: todo consumidor que hoy busca
`index-<modo>-<familia>-<rol>.md` sigue encontrando un archivo, y lo que encuentra le dice dónde está
el resto. Si el nombre canónico pasara a ser la página 1, un consumidor viejo leería un tercio del
índice creyendo que lo leyó entero — la peor forma de fallar, porque es silenciosa.

**Presupuestos**, ajustables por la skill: **240 caracteres** por resumen de entrada y **25 entradas**
por página. Un informe con una sola página **también** lleva metaíndice: un formato que cambia según
la cantidad obliga a cada consumidor a implementar los dos.

### El metaíndice

```markdown
## Páginas
| Página | Ruta | Entradas | IDs |
|---|---|---|---|
| 01 | index-explore-codex-worker-p01.md | 3 | CDX-W-EXP-001 CDX-W-EXP-002 CDX-W-EXP-003 |
| 02 | index-explore-codex-worker-p02.md | 2 | CDX-W-EXP-004 CDX-W-EXP-005 |
```

Los IDs van **enumerados, no como rango**: un rango (`001..003`) se cumple con cualquier serie que
empiece y termine ahí, y deja de detectar exactamente el caso que importa —una entrada que se perdió
en el medio—.

### Interacción con el resto del contrato

- **Split:** el split parte la salida cruda en índice y detalle; la paginación es un paso más, sobre
  el índice ya partido. El detalle no se toca.
- **Truncado previo al dispatch:** alcanza a **todas** las páginas y al metaíndice. Una página vieja
  que sobreviva a un redespacho es un índice fantasma que apunta a un detalle que ya no existe.
- **Decisión de retoma:** una serie de páginas incompleta **no** es un artefacto de cierre válido, así
  que la retoma la trata como ausente y redespacha (o falla cerrado si el consumidor ya está escrito).
- **Publicación atómica:** se escriben primero todas las páginas y **el metaíndice al final**. Al
  revés, un metaíndice publicado antes que sus páginas declara rutas que todavía no existen, y
  cualquier lector concurrente ve una serie rota que en realidad iba a estar completa.

### Una serie incompleta se clasifica por el observable

Falta una página que el metaíndice declara, hay una duplicada, o hay una huérfana que el metaíndice
no lista. Es el estado en que queda un worker cuyo deadline venció a mitad de la emisión, así que
"ninguna entrada se descarta" **no** obliga a aceptar una entrega truncada: obliga a rechazarla como
incompleta en vez de tomarla por buena.

Ninguna resuelve `READY`, pero **no todas resuelven lo mismo**, y "no resuelve `READY`" a secas
dejaría el mismo caso clasificable de cuatro formas — de esa clasificación dependen el retry, el
fallback y la recuperación:

| Observable | Estado |
|---|---|
| el proceso terminó normalmente y la serie es inconsistente | `INVALID` — entregó, y lo que entregó no cumple el contrato |
| el deadline venció sin señal de finalización | `UNAVAILABLE`, causa `deadline_exceeded` — no llegó a terminar, y el corte lo puso el conductor |
| el resultado sobre el recurso original es incierto | `recovery-required` — no se sabe qué quedó escrito |

Se decide por lo que se **observa** —estado del proceso, señal de finalización, integridad de la
serie—, nunca por criterio de quien mira.

### Bloques del índice paginado

```bash
# @bloque:split-paginado
# Predicado: la salida cruda se parte en detalle único y páginas de índice de a lo sumo
# $por_pagina entradas, sin perder ninguna, y el metaíndice se publica al final.
# Entradas: $raw $base (prefijo de ruta sin extensión) $por_pagina
set -u
t=$(mktemp -d)
# Sin `## Detalle` no hay nada que partir, y hay que DECIRLO. Antes esto moría en el `mv` de abajo
# con un "No such file or directory" sobre un temporal que el awk nunca llegó a crear: un mensaje
# que no menciona la sección faltante y que deja al lector buscando un problema de permisos.
grep -qE '^## Detalle[[:space:]]*$' "$raw" || {
  printf 'GUARD:split-sin-detalle el informe no trae la sección `## Detalle`\n' >&2
  rm -rf "$t"; exit 1; }
awk '/^## Índice[[:space:]]*$/{m=1;next} /^## Detalle[[:space:]]*$/{m=2;next}
     /^STATUS: done[[:space:]]*$/{next}
     m==1{print > IDX} m==2{print > DET}' IDX="$t/idx" DET="${base}-detalle.tmp" "$raw"
mv "${base}-detalle.tmp" "$(dirname "$base")/detail-$(basename "$base").md"

cab=$(grep -m1 -E '^\|[[:space:]]*ID[[:space:]]*\|' "$t/idx")
sep=$(grep -m1 -E '^\|[-: |]+\|$' "$t/idx")
grep -E '^\|' "$t/idx" | grep -vE '^\|[[:space:]]*(ID[[:space:]]*\||[-: |]+\|)' > "$t/filas"

n=0; pag=0; meta="$t/meta"; : > "$meta"
while IFS= read -r fila; do
  [ -n "$fila" ] || continue
  if [ "$((n % por_pagina))" -eq 0 ]; then
    pag=$((pag + 1)); p=$(printf '%02d' "$pag"); arch="${base}-p${p}.md"
    printf '%s\n%s\n' "$cab" "$sep" > "$arch"
    printf '%s\t%s\t' "$p" "$(basename "$arch")" >> "$meta"
  fi
  printf '%s\n' "$fila" >> "${base}-p$(printf '%02d' "$pag").md"
  printf '%s ' "$(printf '%s' "$fila" | awk -F'|' '{gsub(/^ +| +$/,"",$2); print $2}')" >> "$meta"
  n=$((n + 1))
  [ "$((n % por_pagina))" -eq 0 ] && printf '\n' >> "$meta"
done < "$t/filas"
printf '\n' >> "$meta"

# El metaíndice va ÚLTIMO: publicado antes que sus páginas declara rutas que aún no existen, y
# cualquier lector concurrente ve una serie rota que en realidad iba a estar completa.
{ echo "## Páginas"; echo "| Página | Ruta | Entradas | IDs |"; echo "|---|---|---|---|"
  while IFS="$(printf '\t')" read -r p ruta ids; do
    [ -n "${p:-}" ] || continue
    # `${ids% }` recorta el espacio que deja la acumulación de arriba (`printf '%s '` por ID).
    # Sin eso la celda queda `E1 E2  |` acá y `E1 E2 |` en la variante PowerShell, que une con
    # `-join ' '`: misma tabla, distinto byte.
    printf '| %s | %s | %s | %s |\n' "$p" "$ruta" "$(printf '%s' "$ids" | wc -w | tr -d ' ')" "${ids% }"
  done < "$meta"
} > "${base}.md.tmp"
mv "${base}.md.tmp" "${base}.md"
rm -rf "$t"
# @fin:split-paginado
```

```powershell
# @bloque:split-paginado-ps
# Predicado: la salida cruda se parte en detalle único y páginas de índice de a lo sumo
# $por_pagina entradas, sin perder ninguna, y el metaíndice se publica al final.
# Entradas: $raw $base (prefijo de ruta sin extensión) $por_pagina
$crudo = @(Get-Content -LiteralPath $raw)
# Sin `## Detalle` no hay nada que partir, y hay que DECIRLO. Antes esto escribía un archivo de
# detalle VACÍO y salía 0: daba por buena una publicación que perdió todo el desarrollo.
if (-not ($crudo | Where-Object { $_ -cmatch '^## Detalle\s*$' })) {
  Write-Error 'GUARD:split-sin-detalle el informe no trae la sección `## Detalle`'
  exit 1
}
$modo = 0; $idx = @(); $det = @()
foreach ($l in $crudo) {
  if ($l -cmatch '^## Índice\s*$')       { $modo = 1; continue }
  if ($l -cmatch '^## Detalle\s*$')      { $modo = 2; continue }
  if ($l -cmatch '^STATUS: done\s*$')    { continue }
  if ($modo -eq 1) { $idx += $l } elseif ($modo -eq 2) { $det += $l }
}
$det | Set-Content -LiteralPath (Join-Path (Split-Path $base) ("detail-" + (Split-Path $base -Leaf) + ".md"))
$cab = $idx | Where-Object { $_ -cmatch '^\|\s*ID\s*\|' } | Select-Object -First 1
$sep = $idx | Where-Object { $_ -cmatch '^\|[-: |]+\|$' } | Select-Object -First 1
$filas = @($idx | Where-Object { $_ -cmatch '^\|' -and $_ -cnotmatch '^\|\s*(ID\s*\||[-: |]+\|)' })
$meta = @()
for ($i = 0; $i -lt $filas.Count; $i += [int]$por_pagina) {
  $p = '{0:d2}' -f ([int]($i / [int]$por_pagina) + 1)
  $arch = "$base-p$p.md"
  $trozo = $filas[$i..([Math]::Min($i + [int]$por_pagina - 1, $filas.Count - 1))]
  (@($cab, $sep) + $trozo) | Set-Content -LiteralPath $arch
  $ids = ($trozo | ForEach-Object { ($_ -split '\|')[1].Trim() }) -join ' '
  $meta += "| $p | $(Split-Path $arch -Leaf) | $($trozo.Count) | $ids |"
}
# El metaíndice va ÚLTIMO: publicado antes que sus páginas declara rutas que aún no existen.
(@('## Páginas', '| Página | Ruta | Entradas | IDs |', '|---|---|---|---|') + $meta) |
  Set-Content -LiteralPath "$base.md"
# @fin:split-paginado-ps
```

```bash
# @bloque:metaindice
# Predicado: toda página que el metaíndice declara existe, no hay páginas huérfanas ni duplicadas,
# y el conjunto de IDs que el metaíndice lista coincide exactamente con el de las páginas.
# Entradas: $base (prefijo de ruta sin extensión)
set -u
t=$(mktemp -d); rc=0
[ -f "${base}.md" ] || { echo "GUARD:metaindice-completo no existe el metaíndice" >&2; rm -rf "$t"; exit 1; }
grep -E '^\|' "${base}.md" | grep -vE '^\|[[:space:]]*(Página[[:space:]]*\||[-: |]+\|)' > "$t/decl"

# 1) toda ruta declarada existe; ninguna se declara dos veces
awk -F'|' '{gsub(/^ +| +$/,"",$3); print $3}' "$t/decl" | sort > "$t/rutas"
while IFS= read -r r; do
  [ -n "$r" ] || continue
  [ -f "$(dirname "$base")/$r" ] || {
    printf 'GUARD:pagina-declarada-existe el metaíndice declara %s y no existe\n' "$r" >&2; rc=1; }
done < "$t/rutas"
uniq -d "$t/rutas" > "$t/dup"
[ -s "$t/dup" ] && { printf 'GUARD:pagina-declarada-existe página declarada dos veces: %s\n' \
  "$(tr '\n' ' ' < "$t/dup")" >&2; rc=1; }

# 2) ninguna página huérfana: un archivo -pNN que el metaíndice no lista es un índice invisible
ls "$(dirname "$base")" 2>/dev/null | grep -E "^$(basename "$base")-p[0-9]{2}\.md$" | sort > "$t/enDisco"
comm -13 "$t/rutas" "$t/enDisco" > "$t/huerf"
[ -s "$t/huerf" ] && { printf 'GUARD:pagina-declarada-existe página huérfana, no listada: %s\n' \
  "$(tr '\n' ' ' < "$t/huerf")" >&2; rc=1; }

# 3) los IDs del metaíndice coinciden EXACTAMENTE con los de las páginas. Enumerados, no en rango:
#    un rango se cumple con cualquier serie que empiece y termine ahí, y deja de detectar la
#    entrada que se perdió en el medio.
awk -F'|' '{gsub(/^ +| +$/,"",$5); print $5}' "$t/decl" | tr ' ' '\n' | grep -v '^$' | sort > "$t/idsMeta"
: > "$t/idsPag"
while IFS= read -r r; do
  f="$(dirname "$base")/$r"; [ -f "$f" ] || continue
  grep -E '^\|' "$f" | grep -vE '^\|[[:space:]]*(ID[[:space:]]*\||[-: |]+\|)' \
    | awk -F'|' '{gsub(/^ +| +$/,"",$2); print $2}' >> "$t/idsPag"
done < "$t/rutas"
sort -o "$t/idsPag" "$t/idsPag"
cmp -s "$t/idsMeta" "$t/idsPag" || {
  printf 'GUARD:metaindice-completo meta=[%s] paginas=[%s]\n' \
    "$(tr '\n' ' ' < "$t/idsMeta")" "$(tr '\n' ' ' < "$t/idsPag")" >&2; rc=1; }
# la cantidad declarada por pagina tiene que ser la real
while IFS= read -r fila; do
  r=$(printf '%s' "$fila" | awk -F'|' '{gsub(/^ +| +$/,"",$3); print $3}')
  n=$(printf '%s' "$fila" | awk -F'|' '{gsub(/^ +| +$/,"",$4); print $4}')
  f="$(dirname "$base")/$r"; [ -f "$f" ] || continue
  real=$(grep -E '^\|' "$f" | grep -vcE '^\|[[:space:]]*(ID[[:space:]]*\||[-: |]+\|)')
  [ "$n" = "$real" ] || { printf 'GUARD:paridad-por-pagina %s declara %s entradas y tiene %s\n' \
    "$r" "$n" "$real" >&2; rc=1; }
done < "$t/decl"
rm -rf "$t"; exit $rc
# @fin:metaindice
```

```powershell
# @bloque:metaindice-ps
# Predicado: toda página que el metaíndice declara existe, no hay páginas huérfanas ni duplicadas,
# y el conjunto de IDs que el metaíndice lista coincide exactamente con el de las páginas.
# Entradas: $base (prefijo de ruta sin extensión)
$rc = 0
if (-not (Test-Path -LiteralPath "$base.md")) { Write-Error 'GUARD:metaindice-completo no existe el metaíndice'; exit 1 }
$dir = Split-Path $base
# Todo comparador va en su variante case-sensitive: el par POSIX filtra con `grep`, agrupa con
# `sort`/`uniq -d`, resta con `comm` y compara los IDs con `cmp`, y los cuatro distinguen mayúsculas.
# Con los de .NET, dos rutas `p01.md`/`P01.md` contarían como duplicadas, una página huérfana con el
# casing cambiado pasaría por listada, y `ABC-A-XYZ-001` cerraría contra `abc-a-xyz-001`.
$decl = Get-Content -LiteralPath "$base.md" | Where-Object { $_ -cmatch '^\|' -and $_ -cnotmatch '^\|\s*(Página\s*\||[-: |]+\|)' }
$rutas = @($decl | ForEach-Object { ($_ -split '\|')[2].Trim() })
foreach ($r in $rutas) {
  if (-not (Test-Path -LiteralPath (Join-Path $dir $r))) { Write-Error "GUARD:pagina-declarada-existe el metaíndice declara $r y no existe"; $rc = 1 }
}
$dup = $rutas | Group-Object -CaseSensitive | Where-Object Count -gt 1
if ($dup) { Write-Error "GUARD:pagina-declarada-existe página declarada dos veces: $($dup.Name -join ' ')"; $rc = 1 }
$enDisco = @(Get-ChildItem -LiteralPath $dir -Filter "$(Split-Path $base -Leaf)-p??.md" | ForEach-Object { $_.Name })
$huerf = $enDisco | Where-Object { $_ -cnotin $rutas }
if ($huerf) { Write-Error "GUARD:pagina-declarada-existe página huérfana, no listada: $($huerf -join ' ')"; $rc = 1 }
$idsMeta = @($decl | ForEach-Object { ($_ -split '\|')[4].Trim() -split '\s+' } | Where-Object { $_ })
$idsPag = @()
foreach ($r in $rutas) {
  $f = Join-Path $dir $r; if (-not (Test-Path -LiteralPath $f)) { continue }
  $idsPag += Get-Content -LiteralPath $f | Where-Object { $_ -cmatch '^\|' -and $_ -cnotmatch '^\|\s*(ID\s*\||[-: |]+\|)' } | ForEach-Object { ($_ -split '\|')[1].Trim() }
}
# El orden lo fija `[StringComparer]::Ordinal` y no `Sort-Object`, que compara por cultura y produce
# una secuencia distinta de la de `sort`: los dos lados van al mensaje del evento, así que un orden
# ajeno divergiría en el payload aunque los conjuntos coincidan.
$idsMeta = [string[]]@($idsMeta); [array]::Sort($idsMeta, [StringComparer]::Ordinal)
$idsPag  = [string[]]@($idsPag);  [array]::Sort($idsPag,  [StringComparer]::Ordinal)
if (Compare-Object $idsMeta $idsPag -CaseSensitive) { Write-Error "GUARD:metaindice-completo meta=[$($idsMeta -join ' ')] paginas=[$($idsPag -join ' ')]"; $rc = 1 }
foreach ($fila in $decl) {
  $c = $fila -split '\|'; $r = $c[2].Trim(); $n = $c[3].Trim()
  $f = Join-Path $dir $r; if (-not (Test-Path -LiteralPath $f)) { continue }
  $real = @(Get-Content -LiteralPath $f | Where-Object { $_ -cmatch '^\|' -and $_ -cnotmatch '^\|\s*(ID\s*\||[-: |]+\|)' }).Count
  if ("$n" -ne "$real") { Write-Error "GUARD:paridad-por-pagina $r declara $n entradas y tiene $real"; $rc = 1 }
}
exit $rc
# @fin:metaindice-ps
```

```bash
# @bloque:validador-paginado
# Predicado: la UNIÓN de las páginas tiene paridad exacta con el detalle — ni una entrada indexada
# sin desarrollo, ni un desarrollo sin entrada en ninguna página.
# Entradas: $base (prefijo de ruta sin extensión) $detail
set -u
t=$(mktemp -d); rc=0
grep -E '^\|' "${base}.md" | grep -vE '^\|[[:space:]]*(Página[[:space:]]*\||[-: |]+\|)' \
  | awk -F'|' '{gsub(/^ +| +$/,"",$3); print $3}' > "$t/rutas"
: > "$t/union"
while IFS= read -r r; do
  f="$(dirname "$base")/$r"; [ -f "$f" ] || continue
  grep -E '^\|' "$f" | grep -vE '^\|[[:space:]]*(ID[[:space:]]*\||[-: |]+\|)' \
    | awk -F'|' '{gsub(/^ +| +$/,"",$2); print $2}' >> "$t/union"
done < "$t/rutas"
sort -o "$t/union" "$t/union"
sed -nE 's/^###[[:space:]]+([A-Z]{3}-[A-Z]-[A-Z]{3}-[0-9]{3})[[:space:]]*$/\1/p' "$detail" | sort > "$t/det"

# La paridad se comprueba contra la UNIÓN, no página por página: por página, una entrada que migró
# de la página 2 a la 3 rompería la paridad sin que se haya perdido nada.
comm -23 "$t/union" "$t/det" > "$t/e"
[ -s "$t/e" ] && { printf 'GUARD:paridad-union indexado sin desarrollo: %s\n' "$(tr '\n' ' ' < "$t/e")" >&2; rc=1; }
comm -13 "$t/union" "$t/det" > "$t/e"
[ -s "$t/e" ] && { printf 'GUARD:paridad-union desarrollo sin entrada: %s\n' "$(tr '\n' ' ' < "$t/e")" >&2; rc=1; }
[ -s "$t/union" ] || { echo "GUARD:paridad-union la unión de las páginas está vacía" >&2; rc=1; }
rm -rf "$t"; exit $rc
# @fin:validador-paginado
```

```powershell
# @bloque:validador-paginado-ps
# Predicado: la UNIÓN de las páginas tiene paridad exacta con el detalle — ni una entrada indexada
# sin desarrollo, ni un desarrollo sin entrada en ninguna página.
# Entradas: $base (prefijo de ruta sin extensión) $detail
$rc = 0; $dir = Split-Path $base
# Case-sensitive en todo: el par POSIX filtra con `grep`, extrae los IDs del detalle con un `sed -E`
# cuyo `[A-Z]{3}-[A-Z]-[A-Z]{3}-[0-9]{3}` no admite minúsculas, y resta con `comm`. Con los
# operadores de .NET, un `### abc-a-xyz-001` contaría como desarrollo y cerraría contra el ID
# indexado en mayúsculas, que es justo la pérdida que esta paridad existe para detectar.
$rutas = @(Get-Content -LiteralPath "$base.md" | Where-Object { $_ -cmatch '^\|' -and $_ -cnotmatch '^\|\s*(Página\s*\||[-: |]+\|)' } | ForEach-Object { ($_ -split '\|')[2].Trim() })
$union = @()
foreach ($r in $rutas) {
  $f = Join-Path $dir $r; if (-not (Test-Path -LiteralPath $f)) { continue }
  $union += Get-Content -LiteralPath $f | Where-Object { $_ -cmatch '^\|' -and $_ -cnotmatch '^\|\s*(ID\s*\||[-: |]+\|)' } | ForEach-Object { ($_ -split '\|')[1].Trim() }
}
# Orden ordinal y no `Sort-Object`, que compara por cultura: los dos conjuntos van al mensaje del
# evento, así que el orden es parte de lo observable.
$union = [string[]]@($union); [array]::Sort($union, [StringComparer]::Ordinal)
$det = [string[]]@(Get-Content -LiteralPath $detail | Where-Object { $_ -cmatch '^###\s+[A-Z]{3}-[A-Z]-[A-Z]{3}-\d{3}\s*$' } | ForEach-Object { ($_ -creplace '^###\s+', '').Trim() })
[array]::Sort($det, [StringComparer]::Ordinal)
# La paridad se comprueba contra la UNIÓN, no página por página.
$sinDet = $union | Where-Object { $_ -cnotin $det }
if ($sinDet) { Write-Error "GUARD:paridad-union indexado sin desarrollo: $($sinDet -join ' ')"; $rc = 1 }
$sinIdx = $det | Where-Object { $_ -cnotin $union }
if ($sinIdx) { Write-Error "GUARD:paridad-union desarrollo sin entrada: $($sinIdx -join ' ')"; $rc = 1 }
if ($union.Count -eq 0) { Write-Error 'GUARD:paridad-union la unión de las páginas está vacía'; $rc = 1 }
exit $rc
# @fin:validador-paginado-ps
```

## `clarification-needed` — el cuarto estado

Un worker que se topa con una ambigüedad que **le impide seguir mapeando** emite
`clarification-needed`: la pregunta concreta, su impacto, el supuesto seguro si existe, y **entrega
igual** el índice y el detalle de todo lo que alcanzó a mapear. No es un abandono: es una entrega
parcial con una pregunta adosada.

### La excepción a la regla 3, y su predicado

La regla 3 no negociable dice que el explorador **nunca se bloquea por dudas**: toda duda se
registra y se sigue explorando. Este estado es una **excepción nombrada**, no un agregado silencioso,
y está acotada por un predicado que se puede evaluar sin juicio:

> Emite `clarification-needed` **solo** cuando la duda hace que **el resto del mapa dependa de la
> respuesta**: sin resolverla, lo que siga sería exploración de un terreno que quizá no existe.

Si la duda deja seguir mapeando —aunque sea con menos certeza— **no** es este estado: va a
`## Incógnitas` y la exploración continúa. La regla 3 sigue siendo la norma; esto es su borde.

### Distinguirlo de una `incógnita high`

Se parecen en que las dos nombran algo sin resolver, y por eso hay que decir en qué se diferencian —
la misma distinción que separa `INVALID` de `runtime_failure`:

| | `incógnita high` | `clarification-needed` |
|---|---|---|
| Qué pasó con el mapa | está **completo**; la incógnita es un hallazgo más | está **truncado**: lo que falta depende de la respuesta |
| Quién puede resolverla | nadie todavía; queda para `clarify` | el conductor, el paquete de contexto o el usuario, **ahora** |
| Qué habilita | nada: el flujo sigue | reanudar el mapeo con una versión nueva del paquete |
| Si se ignora | el flujo avanza con un riesgo declarado | el mapa queda incompleto **y nadie lo sabe** |

La última fila es la razón de que exista el estado: una incógnita ignorada deja un riesgo visible;
una aclaración ignorada deja un mapa que parece completo y no lo está.

### El conductor resuelve antes de preguntar

Recibido un `clarification-needed`, el conductor **busca la respuesta antes de escalarla**: primero
en el paquete de contexto que él mismo armó, después en el repositorio. Solo si no está en ninguno de
los dos le pregunta al usuario.

No es cortesía: la mayoría de estas preguntas se contestan con algo que ya estaba en el paquete y el
worker no relacionó, o con un archivo que el worker no llegó a abrir. Escalar sin buscar convierte
cada ambigüedad del explorador en una interrupción, y el costo lo paga la persona.

### Paquete de contexto versionado

La respuesta **no se aplica sobre el paquete que el worker ya recibió**: se crea una **versión
nueva**. El paquete entregado es inmutable.

```
<dir>/co-explore/scratch/
├─ paquete-<modo>-v1.txt          # el que se despachó
├─ paquete-<modo>-v2.txt          # v1 + la aclaración respondida
└─ paquete-<modo>-v2.origen.txt   # qué pregunta contestó, y quién
```

Mutar el paquete entregado rompe lo único que hace auditable una exploración: saber **con qué
información** se produjo cada mapa. Con el paquete mutado, el índice del worker parece responder a
una pregunta que en el momento de escribirlo no existía.

**El truncado previo al dispatch alcanza a todas las versiones.** Una `v1` que sobreviva a un
redespacho es contexto fantasma: el worker nuevo puede leerla y contestar a partir de un paquete que
ya nadie considera vigente, sin que nada lo delate.

### Cómo deben quedar los consumidores

El estado no vale solo en este documento: si el `reference.md` lo define y el `SKILL.md` no lo
nombra, la skill queda mintiendo sobre sus propios estados. Los **cuatro** consumidores normativos
tienen que reflejarlo, y cada uno es una omisión posible por separado:

1. **el envelope de retorno** — `workers[].estado` admite `clarification-needed`;
2. **la escalera de degradación** — qué rama resuelve cuando un worker queda en ese estado;
3. **la vista "Degradación" del `SKILL.md`**;
4. **la vista "Salida — el envelope" del `SKILL.md`**.

### Bloques del cuarto estado

```bash
# @bloque:clarificacion-completa
# Predicado: un clarification-needed trae pregunta, impacto y el índice y detalle de lo que alcanzó
# a mapear; el supuesto seguro es opcional pero, si falta, se declara que no hay.
# Entradas: $informe
set -u
rc=0
for campo in 'pregunta:' 'impacto:' 'supuesto-seguro:'; do
  grep -qE "^${campo}[[:space:]]*[^[:space:]]" "$informe" || {
    printf 'GUARD:clarification-completa falta o está vacío el campo "%s"\n' "$campo" >&2; rc=1; }
done
# La entrega parcial es obligatoria: sin ella el estado sería indistinguible de un abandono, y se
# perdería todo lo que el worker sí llegó a mapear.
grep -q '^## Índice' "$informe" || {
  echo "GUARD:clarification-completa no entrega el índice de lo mapeado" >&2; rc=1; }
grep -q '^## Detalle' "$informe" || {
  echo "GUARD:clarification-completa no entrega el detalle de lo mapeado" >&2; rc=1; }
exit $rc
# @fin:clarificacion-completa
```

```powershell
# @bloque:clarificacion-completa-ps
# Predicado: un clarification-needed trae pregunta, impacto y el índice y detalle de lo que alcanzó
# a mapear; el supuesto seguro es opcional pero, si falta, se declara que no hay.
# Entradas: $informe
$rc = 0
$doc = Get-Content -LiteralPath $informe
# `-cmatch` y no `-match`: el par POSIX busca con `grep`, que distingue mayúsculas, así que un
# `Pregunta:` o un `## índice` no cumplen el contrato de campos ni el de entrega parcial.
foreach ($campo in @('pregunta:', 'impacto:', 'supuesto-seguro:')) {
  if (-not ($doc | Where-Object { $_ -cmatch "^$campo\s*\S" })) {
    Write-Error "GUARD:clarification-completa falta o está vacío el campo `"$campo`""; $rc = 1
  }
}
if (-not ($doc | Where-Object { $_ -cmatch '^## Índice' }))  { Write-Error 'GUARD:clarification-completa no entrega el índice de lo mapeado'; $rc = 1 }
if (-not ($doc | Where-Object { $_ -cmatch '^## Detalle' })) { Write-Error 'GUARD:clarification-completa no entrega el detalle de lo mapeado'; $rc = 1 }
exit $rc
# @fin:clarificacion-completa-ps
```

```bash
# @bloque:resolver-antes-de-preguntar
# Predicado: el conductor registra haber buscado la respuesta en el paquete y en el repositorio
# antes de escalar la pregunta al usuario.
# Entradas: $bitacora
set -u
rc=0
esc=$(grep -n '`paso: preguntar-al-usuario`' "$bitacora" | head -1 | cut -d: -f1)
[ -n "$esc" ] || exit 0   # no escaló: nada que exigir
for p in buscar-en-paquete buscar-en-repo; do
  n=$(grep -n "\`paso: $p\`" "$bitacora" | head -1 | cut -d: -f1)
  if [ -z "$n" ]; then
    printf 'GUARD:resolver-antes-de-preguntar escaló sin registrar "%s"\n' "$p" >&2; rc=1
  elif [ "$n" -gt "$esc" ]; then
    printf 'GUARD:resolver-antes-de-preguntar "%s" quedó DESPUÉS de escalar\n' "$p" >&2; rc=1
  fi
done
exit $rc
# @fin:resolver-antes-de-preguntar
```

```powershell
# @bloque:resolver-antes-de-preguntar-ps
# Predicado: el conductor registra haber buscado la respuesta en el paquete y en el repositorio
# antes de escalar la pregunta al usuario.
# Entradas: $bitacora
$rc = 0
$doc = Get-Content -LiteralPath $bitacora
# `-cmatch`: el par POSIX localiza los pasos con `grep -n`, que distingue mayúsculas.
function Idx($p) { for ($i = 0; $i -lt $doc.Count; $i++) { if ($doc[$i] -cmatch "``paso: $p``") { return $i + 1 } }; return 0 }
$esc = Idx 'preguntar-al-usuario'
if ($esc -eq 0) { exit 0 }
foreach ($p in @('buscar-en-paquete', 'buscar-en-repo')) {
  $n = Idx $p
  if ($n -eq 0) { Write-Error "GUARD:resolver-antes-de-preguntar escaló sin registrar `"$p`""; $rc = 1 }
  elseif ($n -gt $esc) { Write-Error "GUARD:resolver-antes-de-preguntar `"$p`" quedó DESPUÉS de escalar"; $rc = 1 }
}
exit $rc
# @fin:resolver-antes-de-preguntar-ps
```

```bash
# @bloque:paquete-versionado
# Predicado: el paquete entregado no se modifica —la respuesta crea una versión nueva— y el
# truncado previo al dispatch alcanza a TODAS las versiones.
# Entradas: $scratch (directorio) $hash_v1 (checksum del paquete entregado)
set -u
rc=0
# SHA-256 hex en minúsculas, el mismo algoritmo y la misma forma que la cadena de `cross-implement`.
# Antes acá había un CRC decimal de `cksum` contra el que ningún hash de PowerShell podía cerrar:
# el predicado era incomparable entre sabores, no solo divergente. `sha256sum` no existe en macOS,
# de ahí el fallback.
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum | cut -d' ' -f1
        else shasum -a 256 | cut -d' ' -f1; fi; }
v1=$(ls "$scratch" 2>/dev/null | grep -E '^paquete-.*-v1\.txt$' | head -1)
if [ -n "$v1" ]; then
  actual=$(sha < "$scratch/$v1")
  [ "$actual" = "$hash_v1" ] || {
    printf 'GUARD:paquete-inmutable el paquete entregado cambió (%s ≠ %s)\n' "$actual" "$hash_v1" >&2
    rc=1; }
fi
# Tras un redespacho no puede sobrevivir NINGUNA version: una v1 viva es contexto fantasma que el
# worker nuevo puede leer sin que nada lo delate.
if [ "${redespachado:-0}" = "1" ]; then
  quedan=$(ls "$scratch" 2>/dev/null | grep -cE '^paquete-.*-v[0-9]+\.txt$')
  [ "$quedan" -eq 0 ] || {
    printf 'GUARD:truncado-alcanza-versiones sobrevivieron %s versiones al redespacho\n' "$quedan" >&2
    rc=1; }
fi
exit $rc
# @fin:paquete-versionado
```

```powershell
# @bloque:paquete-versionado-ps
# Predicado: el paquete entregado no se modifica —la respuesta crea una versión nueva— y el
# truncado previo al dispatch alcanza a TODAS las versiones.
# Entradas: $scratch (directorio) $hash_v1 (checksum del paquete entregado)
$rc = 0
$v1 = Get-ChildItem -LiteralPath $scratch -Filter 'paquete-*-v1.txt' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($v1) {
  # SHA-256 y no MD5, y en minúsculas: `Get-FileHash` devuelve el hex en MAYÚSCULAS y el par POSIX
  # lo produce en minúsculas. `-cne` porque, unificado el algoritmo, un `hash_v1` con otro casing es
  # un valor que ningún productor escribe.
  $actual = (Get-FileHash -LiteralPath $v1.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($actual -cne $hash_v1) { Write-Error "GUARD:paquete-inmutable el paquete entregado cambió ($actual ≠ $hash_v1)"; $rc = 1 }
}
if ($env:redespachado -eq '1') {
  $quedan = @(Get-ChildItem -LiteralPath $scratch -Filter 'paquete-*-v*.txt' -ErrorAction SilentlyContinue).Count
  if ($quedan -ne 0) { Write-Error "GUARD:truncado-alcanza-versiones sobrevivieron $quedan versiones al redespacho"; $rc = 1 }
}
exit $rc
# @fin:paquete-versionado-ps
```

```bash
# @bloque:cuarto-estado-consumidores
# Predicado: los cuatro consumidores normativos nombran clarification-needed — el envelope, la
# escalera de degradación, y las dos vistas del SKILL.md.
# Entradas: $ref (reference.md de co-explore) $skill (su SKILL.md)
set -u
rc=0
# Se descuentan los PUNTEROS antes de buscar: `reference.md` → "…el cuarto estado" contiene el
# nombre del estado, y una seccion que solo lo cita de paso no le dice al lector qué pasa con él.
# La primera version contaba esa mencion y daba verde con el párrafo borrado.
seccion() {  # seccion <archivo> <heading>
  awk -v h="$2" '$0 ~ "^#+ " h "$" {on=1;next} on && /^#{2,3} /{exit} on' "$1" \
    | sed -E 's/`[a-z0-9-]+\.md` → "[^"]*"//g'
}
seccion "$ref" "Envelope de retorno" | grep -q 'clarification-needed' || {
  echo "GUARD:cuarto-estado-en-consumidores el envelope no admite clarification-needed" >&2; rc=1; }
seccion "$ref" "Escalera de degradación" | grep -q 'clarification-needed' || {
  echo "GUARD:cuarto-estado-en-consumidores la escalera de degradación lo ignora" >&2; rc=1; }
seccion "$skill" "Degradación" | grep -q 'clarification-needed' || {
  echo "GUARD:cuarto-estado-en-consumidores la vista Degradación del SKILL.md lo ignora" >&2; rc=1; }
seccion "$skill" "Salida — el envelope" | grep -q 'clarification-needed' || {
  echo "GUARD:cuarto-estado-en-consumidores la vista del envelope del SKILL.md lo ignora" >&2; rc=1; }
exit $rc
# @fin:cuarto-estado-consumidores
```

```powershell
# @bloque:cuarto-estado-consumidores-ps
# Predicado: los cuatro consumidores normativos nombran clarification-needed — el envelope, la
# escalera de degradación, y las dos vistas del SKILL.md.
# Entradas: $ref (reference.md de co-explore) $skill (su SKILL.md)
$rc = 0
# Se descuentan los PUNTEROS antes de buscar: una sección que solo cita el estado de paso no le
# dice al lector qué pasa con él.
# Todo va en variante case-sensitive, `-creplace` incluido: el par POSIX recorta con `awk`, descuenta
# los punteros con `sed -E` y busca con `grep -q`, y los tres distinguen mayúsculas. El `-replace`
# por defecto de .NET borraría un puntero escrito `Reference.md`, que el `sed` deja en pie.
function Seccion($archivo, $h) {
  $out = @(); $on = $false
  foreach ($l in (Get-Content -LiteralPath $archivo)) {
    if ($l -cmatch "^#+ $([regex]::Escape($h))$") { $on = $true; continue }
    if ($on -and $l -cmatch '^#{2,3} ') { break }
    if ($on) { $out += ($l -creplace '`[a-z0-9-]+\.md` → "[^"]*"', '') }
  }
  $out -join "`n"
}
if ((Seccion $ref 'Envelope de retorno') -cnotmatch 'clarification-needed')      { Write-Error 'GUARD:cuarto-estado-en-consumidores el envelope no admite clarification-needed'; $rc = 1 }
if ((Seccion $ref 'Escalera de degradación') -cnotmatch 'clarification-needed')  { Write-Error 'GUARD:cuarto-estado-en-consumidores la escalera de degradación lo ignora'; $rc = 1 }
if ((Seccion $skill 'Degradación') -cnotmatch 'clarification-needed')            { Write-Error 'GUARD:cuarto-estado-en-consumidores la vista Degradación del SKILL.md lo ignora'; $rc = 1 }
if ((Seccion $skill 'Salida — el envelope') -cnotmatch 'clarification-needed')   { Write-Error 'GUARD:cuarto-estado-en-consumidores la vista del envelope del SKILL.md lo ignora'; $rc = 1 }
exit $rc
# @fin:cuarto-estado-consumidores-ps
```

## Tres identidades de reintento, y ninguna es la otra

Cuando algo sale mal con un worker hay **tres** operaciones distintas, y hoy se confunden con
facilidad porque las tres se ven como "volver a intentar". Se registran por separado, con nombre
propio y contador propio:

| Identidad | Qué se rehace | Qué NO se rehace | Cuándo |
|---|---|---|---|
| `transportAttempt` | el **lanzamiento** | nada: no llegó a explorar | el proceso no arrancó, o murió antes de emitir |
| `formatRepair` | la **emisión** del informe, en la misma sesión viva | la exploración | exploró y entregó, pero lo entregado no valida |
| `semanticAttempt` | la **exploración entera**, sesión nueva | — | lo entregado valida y no sirve |

Confundirlas tiene un costo concreto en cada dirección: contar una reparación de formato como
intento semántico agota el presupuesto sin haber explorado dos veces; y contar un intento semántico
como reparación de formato hace creer que hay dos mapas independientes cuando hay uno.

### Una ronda de reparación de formato, y por qué no viola la regla 5

Un worker que **terminó su trabajo** pero cuyo informe no cumple el contrato hoy queda `INVALID` y
muere. Ese es trabajo real tirado: la exploración está hecha, lo que falló es el formato de salida.
Se permite **una** ronda de reparación —en la **misma sesión viva**, pidiendo solo que reemita con el
formato correcto—, sin volver a explorar.

La regla 5 dice "una sola pasada, sin rondas" y **sigue intacta**: lo que prohíbe son rondas de
**contenido**, donde el worker vuelve a mirar el código y puede cambiar de opinión. Una reemisión no
toca el espacio de hipótesis; es una ronda de **transporte**. La prueba de que la distinción es real:
si la reparación cambiara un solo hallazgo, dejaría de ser reparación y sería un intento semántico —
y por eso la reparación se valida contra los **mismos IDs** que el intento original.

### `recovery-required` bloquea retry y fallback

Un intento cuyo resultado sobre el recurso original es **incierto** —no se sabe si escribió, si dejó
el proceso vivo, si el archivo quedó a medias— no queda en `INVALID` ni en `UNAVAILABLE`: queda en
`recovery-required`, y **no habilita ni retry ni fallback** hasta resolver qué pasó con ese recurso.

Reintentar sobre un estado incierto es cómo se duplica trabajo o se corrompe una entrega a medio
escribir: el segundo intento no sabe qué encontró del primero, y el resultado combinado no es el de
ninguno de los dos.

**Vencer el deadline no prueba que el proceso dejó de trabajar.** No es una precaución teórica: se
observó lo contrario — una espera venció con los dos workers **todavía produciendo**, y los dos
entregaron informes válidos **después** de que la corrida ya se había degradado. El deadline es el
corte que el conductor se pone a sí mismo para dejar de esperar; no es una señal que le llegue al
proceso ni una prueba de que terminó. `UNAVAILABLE` con causa `deadline_exceeded` describe lo que
hizo el conductor, no lo que hizo el worker.

**Las rutas de salida fijas no protegen contra un worker tardío.** Si dos intentos del mismo modo
escriben en la misma ruta, el tardío completa el archivo de una corrida **ya degradada** y el
conductor lee un artefacto que pasa los predicados sin poder saber de qué intento salió. Por eso cada
intento necesita **rutas exclusivas**: no para ordenar el scratch, sino para que un escritor tardío no
pueda hacerse pasar por el actual. Y por eso, mientras no se sepa qué quedó escrito ni si el proceso
sigue vivo, el estado es `recovery-required` y no hay retry ni fallback que valga — tampoco el
fallback al otro transporte, que sobre un intento quizá vivo pone dos escritores en las mismas rutas.

### Bloques de las identidades

```bash
# @bloque:identidades-reintento
# Predicado: las tres identidades se registran por separado, ninguna reparación de formato cuenta
# como intento semántico, y hay a lo sumo una reparación por worker.
# Entradas: $log
set -u
t=$(mktemp -d); rc=0
grep -oE '^- `(transportAttempt|formatRepair|semanticAttempt): [^`]*`' "$log" \
  | sed -E 's/^- `([a-zA-Z]+): .*/\1/' > "$t/ids"
# Ninguna identidad desconocida: un cuarto nombre es una identidad inventada, y el punto de esta
# seccion es que hay exactamente tres.
grep -oE '^- `[a-zA-Z]+:' "$log" | sed -E 's/^- `//; s/:$//' | sort -u > "$t/vistas"
grep -vE '^(transportAttempt|formatRepair|semanticAttempt)$' "$t/vistas" > "$t/raras"
[ -s "$t/raras" ] && { printf 'GUARD:identidades-reintento identidad desconocida: %s\n' \
  "$(tr '\n' ' ' < "$t/raras")" >&2; rc=1; }
# A lo sumo UNA reparación de formato: la segunda ya no es transporte, es contenido.
n=$(grep -c '^formatRepair$' "$t/ids")
[ "$n" -le 1 ] || { printf 'GUARD:identidades-reintento %s reparaciones de formato (el tope es 1)\n' \
  "$n" >&2; rc=1; }
# Una reparación tiene que conservar los MISMOS IDs: si cambia un hallazgo dejó de ser transporte.
if grep -q '^- `formatRepair:' "$log"; then
  grep -q '`mismos_ids: sí`' "$log" || {
    echo "GUARD:identidades-reintento la reparación no declara haber conservado los IDs" >&2; rc=1; }
fi
rm -rf "$t"; exit $rc
# @fin:identidades-reintento
```

```powershell
# @bloque:identidades-reintento-ps
# Predicado: las tres identidades se registran por separado, ninguna reparación de formato cuenta
# como intento semántico, y hay a lo sumo una reparación por worker.
# Entradas: $log
$rc = 0
$doc = Get-Content -LiteralPath $log
# Case-sensitive en todo: el par POSIX extrae con `grep -oE`, unifica con `sort -u` y descarta las
# tres conocidas con `grep -vE`. Con los operadores por defecto de .NET, `FormatRepair` pasaría por
# una identidad conocida en vez de delatarse como la cuarta que esta sección existe para impedir.
$vistas = @($doc | Where-Object { $_ -cmatch '^- `[a-zA-Z]+:' } | ForEach-Object { [regex]::Match($_, '^- `([a-zA-Z]+):').Groups[1].Value } | Sort-Object -Unique -CaseSensitive)
$raras = $vistas | Where-Object { $_ -cnotin @('transportAttempt', 'formatRepair', 'semanticAttempt') }
if ($raras) { Write-Error "GUARD:identidades-reintento identidad desconocida: $($raras -join ' ')"; $rc = 1 }
$n = @($doc | Where-Object { $_ -cmatch '^- `formatRepair:' }).Count
if ($n -gt 1) { Write-Error "GUARD:identidades-reintento $n reparaciones de formato (el tope es 1)"; $rc = 1 }
if ($n -ge 1 -and -not ($doc | Where-Object { $_ -cmatch '`mismos_ids: sí`' })) {
  Write-Error 'GUARD:identidades-reintento la reparación no declara haber conservado los IDs'; $rc = 1
}
exit $rc
# @fin:identidades-reintento-ps
```

```bash
# @bloque:recovery-bloquea
# Predicado: tras un recovery-required no hay ningún retry ni fallback registrado hasta que el
# recurso original se resuelve.
# Entradas: $log
set -u
rc=0
rec=$(grep -n 'recovery-required' "$log" | head -1 | cut -d: -f1)
[ -n "$rec" ] || exit 0
res=$(grep -n '`recurso: resuelto`' "$log" | head -1 | cut -d: -f1)
lim=${res:-999999}
post=$(awk -v a="$rec" -v b="$lim" 'NR>a && NR<b && (/`semanticAttempt:/ || /`transportAttempt:/) {print NR": "$0}' "$log")
[ -z "$post" ] || {
  printf 'GUARD:recovery-bloquea hubo reintento con el recurso sin resolver:\n%s\n' "$post" >&2
  rc=1; }
exit $rc
# @fin:recovery-bloquea
```

```powershell
# @bloque:recovery-bloquea-ps
# Predicado: tras un recovery-required no hay ningún retry ni fallback registrado hasta que el
# recurso original se resuelve.
# Entradas: $log
$rc = 0
$doc = Get-Content -LiteralPath $log
$rec = -1; $res = $doc.Count
# `-cmatch`: el par POSIX localiza los tres literales con `grep -n` y `awk`, que distinguen
# mayúsculas. Con `-match`, un `Recovery-Required` bloquearía reintentos que POSIX deja pasar.
for ($i = 0; $i -lt $doc.Count; $i++) {
  if ($rec -lt 0 -and $doc[$i] -cmatch 'recovery-required') { $rec = $i }
  if ($doc[$i] -cmatch '`recurso: resuelto`') { $res = $i; break }
}
if ($rec -lt 0) { exit 0 }
# Un solo evento con TODOS los reintentos y su número de línea, como el `awk` del par: emitir uno
# por ítem obligaba a reconstruir el conjunto desde varios mensajes, y sin el número de línea el
# lector no sabe a qué altura del log mirar.
$post = @(for ($i = $rec + 1; $i -lt $res; $i++) {
  if ($doc[$i] -cmatch '`(semanticAttempt|transportAttempt):') { "$($i + 1): $($doc[$i])" }
})
if ($post.Count -gt 0) {
  Write-Error "GUARD:recovery-bloquea hubo reintento con el recurso sin resolver:`n$($post -join "`n")"
  $rc = 1
}
exit $rc
# @fin:recovery-bloquea-ps
```
