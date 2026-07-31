# co-explore — Referencia

Detalle operativo de la skill `co-explore`. El `SKILL.md` apunta aquí cuando necesita la
plantilla del prompt de exploración (por modo), el formato del informe, la plantilla de
síntesis, el algoritmo de descubrimiento del explorador, los tiempos de espera o el árbol de
archivos de trabajo.

## Tabla de contenidos

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

```xml
<task>
Eres un asesor técnico independiente. Se debe tomar una DECISIÓN entre opciones y el usuario no
está seguro. Forma tu propia postura ANTES de ver la de nadie más. Es SOLO LECTURA: puedes leer el
código en {working_dir} para fundamentar, pero no edites ni ejecutes nada.
</task>

<decision>
{la decisión a resolver + las opciones en juego, del paquete de contexto}
</decision>

<context>
{contexto relevante: spec/plan si los hay, AC, contratos, complejidad}
</context>

{constraints}

<output_contract>
Devuelve exactamente:
POSTURA: <hacia qué opción te inclinas, o "sin preferencia" con el porqué>
POR QUÉ: <2-5 razones fundadas, ancladas al código/contexto cuando se pueda>
TRADE-OFFS: <qué compra y qué cuesta cada opción>
RIESGOS/INCÓGNITAS: <lo que no pudiste verificar o lo que cambiaría tu postura>
</output_contract>
```

**Prompt de debate — cruce (rondas 1..N):**

```xml
<task>
Continúa el debate. Abajo está la postura ACTUAL de la otra parte sobre la misma decisión.
Critícala de forma adversarial y luego da tu postura ACTUALIZADA. SOLO LECTURA.
</task>

<other_position>
{la postura actual del conductor, del delta de la ronda anterior}
</other_position>

{constraints}

<output_contract>
CRÍTICA: <qué falla, qué no consideró, qué riesgo ignora la otra postura>
POSTURA ACTUALIZADA: <tu postura tras la crítica: qué mantienes, qué concedes>
CONVERGENCIA: <en qué estás de acuerdo con la otra parte>
</output_contract>
```

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

**Puntero.** El algoritmo canónico de descubrimiento del explorador —identificar la familia
del autor y elegir el explorador de la otra familia— vive en `cross-review/reference.md` →
"Descubrir el revisor". Si esa skill está instalada en el entorno, léelo de ahí: esta sección
no lo duplica.

**Fallback mínimo (`co-explore` sin `cross-review` instalada).** Misma regla dura: el
explorador nunca es de la misma familia de modelos que el autor. Hay dos familias — Claude y
GPT/Codex — y la del autor es la del agente que conduce la skill, sin importar la superficie
donde corre (CLI, app de escritorio, IDE, web): un agente Claude → Claude; un agente Codex →
GPT/Codex.

| Familia del autor | Explorador a buscar | Vía |
|---|---|---|
| Claude | Codex | `codex exec` en background, read-only |
| GPT/Codex | Claude | `claude -p` en background, restringido a tools de lectura |

Si el explorador de la otra familia no está disponible → `UNAVAILABLE` (regla 6 del `SKILL.md`).

**Invocación directa.** En topología dual se lanzan **los dos**, y el orden y los nombres de
archivo los fija "Fan-out dual y orden de lanzamiento" — no los bloques de abajo, que quedan como
referencia del preflight y de la lectura del config. Las rutas `explorer.*` que aparecen acá son
**históricas**: el árbol vigente es "Árbol de rutas".

**Preflight de aislamiento (fail-closed).** Antes de lanzar, comprobar que la versión instalada
permite aislar al worker: que `codex exec --help` ofrezca `--ignore-user-config` y que
`codex features list` reporte `hooks`, `apps` y `plugins`. Si falta cualquiera, **no se lanza** y
se devuelve `UNAVAILABLE` (regla 6 del `SKILL.md`). Acá pesa más que en una invocación sync: el
lanzamiento es en **background**, así que un fail-open dejaría un proceso sin aislar corriendo sin
nadie mirándolo. `-s read-only` acota lo que el explorador escribe en disco, no los efectos
remotos de una tool MCP.

```bash
# POSIX — el prompt ya está escrito a archivo con la tool Write (nunca inline, ni echo/heredoc):
mkdir -p co-explore/scratch
# Modelo y esfuerzo del usuario: --ignore-user-config los descarta junto con el resto del config,
# así que se leen antes y se pasan explícitos. Solo vale una asignación RAÍZ inequívoca del TOML
# (anterior a la primera cabecera de tabla, comillas dobles, una sola ocurrencia); si no, se deja
# el default del CLI en vez de forzar un valor sacado de una tabla o de un perfil inactivo.
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

> **Sección inerte hasta el corte.** Nada de lo que sigue está referenciado desde `SKILL.md`
> todavía. Define el contrato de la topología de dos workers con conductor árbitro.

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

```xml
<task>
Eres un ingeniero explorando este repositorio para preparar un cambio. NO escribas ni
modifiques nada: solo lee, busca y razona. Trabajas SOLO: nadie va a responder preguntas
— toda duda se registra como entrada de tipo incógnita y sigues explorando. No tienes
navegador: las URLs del contexto NO son navegables para ti — nunca intentes abrirlas.
</task>

<context_package>
{digest del ticket + prompt del usuario + AC preliminares si existen + complejidad declarada
+ evidencia observada de reproducción si la hubo (consola/red/pasos, capturada por la llamadora)}
</context_package>

<focus>
Mapea el terreno para este cambio: dónde vive lo que hay que tocar, qué existe para reusar,
qué puede romperse, y qué enfoque seguirías. Referencia todo con path:line.
</focus>

{constraints}

<output_contract>
Tu ÚLTIMA salida debe ser EXACTAMENTE esta estructura, con estos headings literales:

## Índice
Una tabla con una fila POR CADA entrada de tu detalle. Cinco columnas, en este orden:
ID | tipo · qué | severidad | confianza | punteros
- ID: {PREFIJO}-001, {PREFIJO}-002, … correlativo, tres dígitos.
- tipo: uno de ubicación · relación · hipótesis · reúso · riesgo · incógnita · supuesto.
- qué: una frase. La fila entera ocupa UNA sola línea.
- severidad y confianza: exactamente high, medium o low.
- punteros: {FORMATO_PUNTERO}, o "N/A: <motivo>" si no hay ninguno posible.

## Detalle
Un heading "### <ID>" por CADA fila del índice, con el desarrollo completo debajo.
Ningún contenido fuera de un "### <ID>".

Los IDs del índice y los del detalle deben ser EXACTAMENTE el mismo conjunto.
Cierra con la línea: STATUS: done
</output_contract>
```

`{PREFIJO}` se sustituye por `CDX-W-EXP` o `CLD-W-EXP` según el worker. `{FORMATO_PUNTERO}` es
`path:line` con un solo `working_dir`, o `repo/path:line` con varios.

### Prompt de counter-plan (dos capas)

Mismo `output_contract` que `explore`, con `{PREFIJO}` = `<FAM>-W-CTR`. Cambian `<task>`, el
paquete y el foco:

```xml
<task>
Eres un ingeniero proponiendo tu propio enfoque técnico para el cambio descrito en la spec
aprobada. NO escribas ni modifiques nada: solo lee, busca y razona. Trabajas SOLO: nadie va
a responder preguntas — toda duda se registra como entrada de tipo incógnita.
</task>

<context_package>
NÚCLEO COMÚN (idéntico para ambos workers):
{ruta y contenido de la spec.md o master-spec.md aprobada + paths de domain_context}

ANEXO (solo si este worker quedó READY en la fase explore):
{contenido concatenado de su PROPIO index-explore-<familia>-worker.md y
 detail-explore-<familia>-worker.md}
</context_package>

<focus>
Propón tu propio contra-enfoque: qué tocarías, qué reusarías, en qué orden, y qué riesgos ves.
Las entradas de tipo "hipótesis" llevan acá el peso del informe: ahí va tu enfoque, paso por
paso. Referencia todo con path:line.
</focus>
```

El anexo **viaja concatenado dentro del prompt**, nunca como una ruta a abrir: en `sdd-orchestrator`
los artefactos viven en la carpeta contenedora, fuera del `working_dir`, y el bloque `{constraints}`
prohíbe salir de ahí. Concatenarlo lo resuelve sin ensanchar el perímetro de lectura de ningún
worker, y sin que el conductor cargue el anexo en su ventana: lo escribe el shell.

**Nunca** el artefacto de la otra familia — eso rompería el anti-anclaje que el modo existe para
preservar.

### Prompt de investigate (dos capas)

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

# 3) lanzar los dos, sin esperar entre medio
codex exec --ignore-user-config --disable hooks --disable apps --disable plugins \
      -s read-only -C <working_dir> --skip-git-repo-check --json \
      --output-last-message "$S/raw-$M-codex-worker.md" \
      ${MODEL:+-m} ${MODEL:+"$MODEL"} - \
    < "$S/prompt-$M-codex-worker.txt" \
    > "$S/thread-$M-codex-worker.jsonl" 2> "$S/stderr-$M-codex-worker.txt" &
echo $! > "$S/pid-$M-codex-worker.txt"
T0_CODEX=$(date +%s)

( cd <working_dir> && claude -p --safe-mode --model opus --permission-mode default \
    --allowedTools=Read,Grep,Glob --session-id "$SID_CLAUDE" \
    < "$S/prompt-$M-claude-worker.txt" ) \
    > "$S/raw-$M-claude-worker.md" 2> "$S/stderr-$M-claude-worker.txt" &
echo $! > "$S/pid-$M-claude-worker.txt"
T0_CLAUDE=$(date +%s)

# 4) recién ahora, poll de ambos — cada uno contra SU T0
```

> **Nota sobre `${MODEL:+-m}`**: acá funciona porque son **dos** expansiones separadas, una por
> argumento. La forma `${MODEL:+-m "$MODEL"}` **no** funciona en zsh: no hace field splitting y
> manda `-m` pegado a su valor. Ante la duda, la construcción incremental con `set -- "$@" -m
> "$MODEL"` de "Descubrir el revisor" es la segura.

**PowerShell:**

```powershell
$S = "<dir>\co-explore\scratch"; $M = "<modo>"
# ambos Start-Process ANTES de cualquier Wait-Process
$pCodex = Start-Process -FilePath codex -NoNewWindow -PassThru `
  -RedirectStandardInput  "$S\prompt-$M-codex-worker.txt" `
  -RedirectStandardOutput "$S\thread-$M-codex-worker.jsonl" `
  -RedirectStandardError  "$S\stderr-$M-codex-worker.txt" -ArgumentList $CodexArgs
$pClaude = Start-Process -FilePath claude -WorkingDirectory <working_dir> -NoNewWindow -PassThru `
  -RedirectStandardInput  "$S\prompt-$M-claude-worker.txt" `
  -RedirectStandardOutput "$S\raw-$M-claude-worker.md" `
  -RedirectStandardError  "$S\stderr-$M-claude-worker.txt" -ArgumentList $ClaudeArgs
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
un worker de **la misma familia que el conductor** — algo que el resto del ecosistema prohíbe.

**Por qué es aceptable acá, y solo acá:** el valor cross-model vive en que los **dos mapas que se
comparan** vengan de familias distintas. En la topología anterior esos dos mapas eran el del
conductor y el del worker, así que el worker tenía que ser de la otra familia. En la topología dual
el conductor **no produce mapa**: arbitra. Los dos mapas comparados son los de los dos workers, uno
por familia, y la diversidad se conserva íntegra.

**Alcance de la excepción:** los tres modos duales de `co-explore`. **No** alcanza al rol de revisor
de `cross-review` ni al de implementador de `cross-implement`, donde sigue habiendo una sola salida
delegada y la familia opuesta es lo único que rompe la correlación de errores.

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

workers:
  - family: codex
    state: READY | INVALID | UNAVAILABLE
    cause: confirmed_wall | launch_flake | runtime_failure | null   # solo si UNAVAILABLE
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

`contributors[]` es lo que permite localizar el mapa del conductor en las ramas degradadas:
`workers[]` solo describe procesos despachados, y en las ramas 2, 3 y 4 aparece un mapa que ningún
worker produjo.

Con `outcome: map_failure`, la llamadora **ignora todo contribuyente** y no pasa contexto de
co-explore.

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

El cuerpo de una síntesis compara **por ID**, no informes completos:

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

Tres estados, definidos por **predicado** y no por criterio:

| Estado | Predicado |
|---|---|
| `READY` | pasa **todos**: dos capas, gramática de ID, unidad indexable, enums, `STATUS: done`, split correcto y paridad |
| `INVALID` | respondió, pero falla alguno de esos predicados |
| `UNAVAILABLE` | no respondió, o no se pudo lanzar |

`READY` los exige **todos**, sin excepciones. Omitir la gramática de ID o la unidad indexable de la
lista dejaría pasar como válido un informe con IDs sin namespace —la paridad **no** lo detecta,
porque la omisión está en el índice *y* en el detalle— o con contenido sin indexar.

**`UNAVAILABLE` lleva causa de un enum cerrado**, porque de ella depende la política de reintento:

| Causa | Qué la produce | Reintento |
|---|---|---|
| `confirmed_wall` | binario ausente, auth rechazada, versión incompatible, aislamiento imposible | **ninguno** — terminal para la corrida |
| `launch_flake` | el binario existe pero el lanzamiento flaqueó (arranque frío, timeout de spawn) | 2-3 con backoff corto, nunca un loop abierto |
| `runtime_failure` | arrancó bien y falló después: error de ejecución, deadline vencido sin marcador, salida vacía | por intento; no condena la corrida ni se reintenta en bucle |

Distinción fina entre `INVALID` y `runtime_failure`: un proceso que **terminó** y dejó salida sin
marcador es `INVALID` (respondió mal); uno que **alcanzó el deadline** sin marcador es
`runtime_failure` (no llegó a responder).

Un worker `INVALID` **no aporta anexo** a `counter-plan` **ni sirve de seed** a `cross-review`,
aunque conserve una sesión técnicamente reanudable.

### Decisión de retoma

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

A diferencia de los otros modos (una sola pasada), `debate` itera. El conductor participa como
una voz y la otra familia es la otra; el conductor además sintetiza (el usuario es el árbitro).

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
