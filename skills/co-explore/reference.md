# co-explore — Referencia

Detalle operativo de la skill `co-explore`. El `SKILL.md` apunta aquí cuando necesita la
plantilla del prompt de exploración (por modo), el formato del informe, la plantilla de
síntesis, el algoritmo de descubrimiento del explorador, los tiempos de espera o el árbol de
archivos de trabajo.

## Tabla de contenidos

- [Portabilidad entre shells (POSIX / PowerShell)](#portabilidad-entre-shells-posix--powershell)
- [Prompt de exploración](#prompt-de-exploración)
- [Formato del informe](#formato-del-informe)
- [Plantilla de `synthesis.md`](#plantilla-de-synthesismd)
- [Plantilla de síntesis — `investigate`](#plantilla-de-síntesis--investigate)
- [Plantilla de `debate.md`](#plantilla-de-debatemd)
- [Capacidades y worktree (`investigate`)](#capacidades-y-worktree-investigate)
- [Descubrir el revisor (puntero + fallback)](#descubrir-el-revisor-puntero--fallback)
- [Transporte: rama `orca-session` (sesión fresca read-only)](#transporte-rama-orca-session-sesión-fresca-read-only)
- [Latencia y deadlines](#latencia-y-deadlines)
- [Archivos de trabajo (scratch)](#archivos-de-trabajo-scratch)

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

### Modo `explore` (pre-spec)

```xml
<task>
Eres un ingeniero explorando este repositorio para preparar un cambio. NO escribas ni
modifiques nada: solo lee, busca y razona. Trabajas SOLO: nadie va a responder preguntas
— toda duda se registra (ver output_contract) y sigues explorando. No tienes navegador:
las URLs del contexto NO son navegables para ti — nunca intentes abrirlas; extrae señal de
la evidencia observada que te den (consola, red, pasos) y registra en Incógnitas/Supuestos
lo que requeriría ver la aplicación corriendo.
</task>

<context_package>
{digest del ticket + prompt del usuario + AC preliminares si existen + complejidad declarada
+ evidencia observada de reproducción si la hubo (consola/red/pasos, capturada por la llamadora)}
</context_package>

<focus>
Mapea el terreno para este cambio: dónde vive lo que hay que tocar, qué existe para reusar,
qué puede romperse, y qué enfoque seguirías. Referencia todo con path:line.
</focus>

<output_contract>
Tu ÚLTIMA salida debe ser EXACTAMENTE este markdown (headings literales):
## Mapa\n## Hipótesis\n## Puntos de reúso\n## Riesgos\n## Incógnitas\n## Supuestos\n## Enfoque sugerido
- Incógnitas: preguntas abiertas que no pudiste resolver leyendo el código.
- Supuestos: qué asumiste para poder seguir, y por qué.
- Enfoque sugerido: 3-5 bullets, tu solución preferida.
Cierra con la línea: STATUS: done
</output_contract>
```

### Modo `counter-plan` (pre-plan / pre-reparto)

Misma estructura; cambia el objetivo (proponer el enfoque propio para una spec ya aprobada, no
mapear terreno virgen) y el contexto que recibe (la spec, no el ticket crudo):

```xml
<task>
Eres un ingeniero proponiendo tu propio enfoque técnico para el cambio descrito en la spec
aprobada. NO escribas ni modifiques nada: solo lee, busca y razona. Trabajas SOLO: nadie va
a responder preguntas — toda duda se registra (ver output_contract) y sigues explorando.
</task>

<context_package>
{ruta de spec.md o master-spec.md aprobada + ruta de tu propio findings-<familia>.md de la
fase explore, con resume oportunista del thread si session.json lo permite}
</context_package>

<focus>
Propón tu propio contra-enfoque para implementar la spec: qué tocarías, qué reusarías, en qué
orden, y qué riesgos ves. "## Enfoque sugerido" es el cuerpo principal de este informe: en
este modo va con más detalle que en la fase explore. En una orquestación multi-repo, incluye
ahí el reparto tentativo — qué repo cubre qué AC y sus depends_on. Referencia todo con
path:line.
</focus>

<output_contract>
Tu ÚLTIMA salida debe ser EXACTAMENTE este markdown (headings literales):
## Mapa\n## Hipótesis\n## Puntos de reúso\n## Riesgos\n## Incógnitas\n## Supuestos\n## Enfoque sugerido
- Incógnitas: preguntas abiertas que no pudiste resolver leyendo el código.
- Supuestos: qué asumiste para poder seguir, y por qué.
- Enfoque sugerido: cuerpo principal del informe — tu contra-enfoque completo y, si aplica,
  el reparto tentativo repo → AC con depends_on.
Cierra con la línea: STATUS: done
</output_contract>
```

### Modo `investigate` (standalone, bug)

Cambia el objetivo (encontrar la causa raíz de un bug, no preparar un cambio) y el
`output_contract` (bug-shaped). El revisor sigue read-only: forma hipótesis leyendo, no
ejecuta:

```xml
<task>
Eres un ingeniero investigando un bug en este repositorio. NO escribas, ejecutes ni
modifiques nada: solo lee, busca y razona sobre la causa raíz. Trabajas SOLO: nadie va a
responder preguntas — toda duda se registra (ver output_contract) y sigues investigando. No
tienes navegador ni puedes correr el código: extrae señal de la evidencia observada que te
den (consola, red, stacktrace, pasos de reproducción) y registra en Incógnitas/Supuestos lo
que solo podrías confirmar ejecutando.
</task>

<context_package>
{síntoma reportado del bug + evidencia de reproducción observada (consola/red/stacktrace/pasos)
si la hubo + prompt del usuario}
</context_package>

<focus>
Rastrea la causa raíz: dónde vive el problema, qué cadena de código lo produce, y qué
hipótesis explican el síntoma. Rankea tus hipótesis por probabilidad y, para cada una, di qué
evidencia la confirmaría. Referencia todo con path:line. No propongas el arreglo: el objetivo
es entender la causa, no resolverla.
</focus>

<output_contract>
Tu ÚLTIMA salida debe ser EXACTAMENTE este markdown (headings literales):
## Síntoma\n## Mapa de código\n## Hipótesis de causa raíz\n## Incógnitas\n## Supuestos\n## Plan de verificación
- Hipótesis de causa raíz: rankeadas; cada una con evidencia de respaldo, confianza (alta/media/
  baja) y cómo confirmarla (qué correr u observar).
- Incógnitas: lo que no pudiste determinar leyendo; Supuestos: qué asumiste para seguir, y por qué.
- Plan de verificación: qué verificar primero y con qué, para el handoff a systematic-debugging.
Cierra con la línea: STATUS: done
</output_contract>
```

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

<output_contract>
CRÍTICA: <qué falla, qué no consideró, qué riesgo ignora la otra postura>
POSTURA ACTUALIZADA: <tu postura tras la crítica: qué mantienes, qué concedes>
CONVERGENCIA: <en qué estás de acuerdo con la otra parte>
</output_contract>
```

## Formato del informe

El explorador (y, con el mismo formato, el propio conductor — ver regla 2 del `SKILL.md`) debe
cerrar su salida con exactamente estos 7 headings, en este orden:

```
## Mapa
<archivos/módulos relevantes para este cambio, referenciados con path:line>

## Hipótesis
<qué está pasando en el código / cómo encaja el cambio propuesto>

## Puntos de reúso
<qué ya existe en el repo y se puede aprovechar en vez de reescribir>

## Riesgos
<qué puede romperse, deuda técnica que estorba al cambio>

## Incógnitas
<preguntas abiertas que no pudo determinar leyendo el código — candidatas a `clarify`>

## Supuestos
<qué asumió para poder seguir explorando sin bloquearse, y por qué>

## Enfoque sugerido
<3-5 bullets: el enfoque preferido de este explorador para el cambio>
```

En modo `counter-plan`, `## Enfoque sugerido` deja de ser un resumen de cierre y pasa a ser el
**cuerpo principal** del informe: ahí va el contra-enfoque completo (qué tocar, qué reusar, en
qué orden, riesgos) y, en una orquestación multi-repo, el reparto tentativo repo → AC con
`depends_on` (ver "Prompt de exploración" → variante `counter-plan`).

Este formato fijo es lo que hace barata la síntesis (comparar dos informes sección por sección
en vez de dos textos libres). Se escribe en `co-explore/findings-<familia>.md` en modo `explore`,
o en `co-explore/counter-plan-<familia>.md` en modo `counter-plan` (nunca pisa el findings de la
fase `explore` — ver "Archivos de trabajo (scratch)"); si la salida del explorador no respeta
este formato, se degrada según la regla 4 del `SKILL.md` (texto libre como contexto, o descarte
si es ruido — registrando la degradación).

### Formato del informe — `investigate` (bug-shaped)

En `investigate` los 7 headings de arriba se reemplazan por estos 6, en este orden:

```
## Síntoma
<comportamiento reportado + evidencia observada (consola/red/stacktrace/pasos)>

## Mapa de código
<archivos/módulos en la cadena del bug, referenciados con path:line>

## Hipótesis de causa raíz
<rankeadas; cada una: hipótesis · evidencia de respaldo · confianza (alta/media/baja) ·
 cómo confirmarla (qué correr u observar)>

## Incógnitas
<lo que no se pudo determinar leyendo — candidato a confirmar ejecutando>

## Supuestos
<qué se asumió para seguir investigando sin bloquearse, y por qué>

## Plan de verificación
<qué verificar primero y con qué — input directo para el handoff a systematic-debugging>
```

Se escribe en `co-explore/investigate-<familia>.md`. Misma degradación que los otros modos
(regla 4 del `SKILL.md`) si la salida no respeta el formato.

## Plantilla de `synthesis.md`

La escribe el conductor (no el explorador) al comparar su propio informe con el del explorador,
después de que ambos cerraron su exploración:

```markdown
# Síntesis co-explore — <id> (<ISO-8601>)

## Convergencias
- <hecho/hipótesis en que ambos mapas coinciden>

## Divergencias
| # | Tema | Conductor dice | Revisor dice | Resolución (o "abierta → checkpoint") |
|---|---|---|---|---|

## Duelo de enfoques
- **Enfoque del conductor:** <bullets>
- **Enfoque del revisor:** <bullets>
- **Elección:** <uno / híbrido> — **Rationale:** <reúso, riesgo, simplicidad, encaje>

## Incógnitas fusionadas
- [ ] <pregunta> — origen: <conductor|revisor> — ¿cambia el diseño? <sí → clarify | no>

## Supuestos del revisor a vigilar
- <supuesto> (verificar en la crítica de la spec)
```

- **Convergencias / Divergencias:** tabla corta, no un volcado completo de ambos informes —
  solo lo que coincide o difiere en sustancia. Las divergencias sin resolver se presentan en el
  checkpoint informativo previo a escribir la spec/plan (ver `SKILL.md` → "La síntesis").
- **Duelo de enfoques:** evaluación explícita en méritos, no adopción automática de uno — el
  "Rationale" es lo auditable, no la elección en sí.
- **Incógnitas fusionadas:** las que cambiarían el diseño alimentan `clarify` (obligatorio en
  complejos); las respuestas quedan después en `## Clarifications` de la spec.
- **Supuestos del revisor a vigilar:** input directo para la crítica informada de
  `cross-review` — el crítico puede marcar ahí si alguno de esos supuestos resultó
  equivocado.
- **Material interno:** `synthesis.md` (como los informes) es material de trabajo del
  directorio `co-explore/` — su vocabulario (conductor/revisor, duelo, dos mapas) **no se
  traslada** a la conclusión presentada al usuario ni a los artefactos SDD (ver `SKILL.md` →
  "La síntesis", paso 5).

## Plantilla de síntesis — `investigate`

Variante bug-shaped de `synthesis.md`, escrita por el conductor tras cerrar ambas
investigaciones. Se escribe en `co-explore/synthesis.md` (mismo archivo, contenido según modo):

```markdown
# Síntesis co-explore investigate — <id> (<ISO-8601>)

## Convergencias
- <hipótesis/hecho en que ambos mapas coinciden>

## Divergencias
| # | Tema | Conductor dice | Revisor dice | Resolución (o "abierta → presentar ambas") |
|---|---|---|---|---|

## Duelo de hipótesis de causa raíz
- **Hipótesis del conductor:** <bullets + evidencia>
- **Hipótesis del revisor:** <bullets + evidencia>
- **Líder:** <cuál> — **Rationale:** <evidencia, encaje con el repro, qué la distingue>

## Hipótesis líder + plan de verificación
- Causa raíz probable: <...>
- Verificar con: <qué correr/observar primero — input para systematic-debugging>

## Divergencia no resuelta (si la hay)
- <ambas posiciones, con su evidencia; se presentan al usuario, no se fuerza consenso>
```

- **Duelo de hipótesis:** evaluar las causas raíz candidatas en méritos (evidencia, encaje con
  el repro), no adoptar la primera; el "Rationale" es lo auditable. Acá es donde el conductor L1
  puede **ejecutar para desempatar** (ver "Capacidades y worktree (`investigate`)").
- **Divergencia no resuelta:** si los dos mapas no convergen en la causa raíz, se presentan
  ambas posiciones — mismo principio que en `explore` (no forzar consenso).
- **Material interno:** misma regla que la `synthesis.md` de `explore` — este vocabulario no
  se traslada a la conclusión presentada al usuario (paso 5 de "La síntesis").

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

**Invocación directa — autor Claude → explorador Codex.** Adaptado de
`cross-review/reference.md` → Vía B, lanzado en background porque `explore` nunca bloquea
al conductor (a diferencia de cross-review, que en Claude Code prefiere el camino sync):

```bash
# POSIX — el prompt ya está escrito a archivo con la tool Write (nunca inline, ni echo/heredoc):
mkdir -p co-explore/scratch
codex exec -s read-only -C <working_dir> --skip-git-repo-check --json \
    --output-last-message co-explore/scratch/explorer.out \
    - < co-explore/scratch/prompt.txt \
    > co-explore/scratch/explorer-thread.jsonl \
    2> co-explore/scratch/explorer.err &
PID=$!
echo "$PID" > co-explore/scratch/explorer.pid
```
```powershell
# PowerShell:
New-Item -ItemType Directory -Force -Path co-explore\scratch | Out-Null
$proc = Start-Process -FilePath codex -NoNewWindow -PassThru `
  -RedirectStandardInput  co-explore\scratch\prompt.txt `
  -RedirectStandardOutput co-explore\scratch\explorer-thread.jsonl `
  -RedirectStandardError  co-explore\scratch\explorer.err `
  -ArgumentList 'exec','-s','read-only','-C','<working_dir>','--skip-git-repo-check','--json','--output-last-message','co-explore\scratch\explorer.out'
$proc.Id | Out-File co-explore\scratch\explorer.pid
```

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

## Transporte: rama `orca-session` (sesión fresca read-only)

Alternativa a la rama `cli` de arriba ("Descubrir el revisor (puntero + fallback)"): en vez de un
subproceso headless efímero, el conductor abre, con la skill-librería `cross-model-orca`, una
**sesión interactiva fresca** de la otra familia vía Orca, la deja explorar y **cosecha su
transcript**. Es **aditiva**: la rama `cli` de arriba no cambia y sigue siendo el transporte por
defecto en cuanto algo de lo de abajo no se pueda garantizar.

### Resolver transporte (antes del paso 3 de `SKILL.md`)

Antes de lanzar (paso 3 de "Pasos de ejecución"), resolver qué transporte usar:
`override ?? config ?? auto`. Algoritmo canónico — no se reimplementa acá, ver
`cross-model-orca/reference.md` → "Resolver de transporte":

- **`override`** — lo que pasa explícito la skill llamadora. Cuando invoca `sdd-flow`/
  `sdd-orchestrator`, propagan solo el `cross_model.transport.desired` configurado (nunca su
  propio `effective` ya resuelto: cada proceso reevalúa su propia reachability de Orca, porque un
  subproceso delegado puede ver el runtime `stale_bootstrap` aunque el padre lo haya alcanzado
  sin problema).
- **`config`** — la clave `cross_model.transport` en `.specify/config.yml` (default `auto` cuando
  la clave no está).
- **`auto`** — `orca-session` si el runtime de Orca es alcanzable **desde el proceso del
  conductor** en este momento y se puede crear una sesión fresca propia; si no, `cli`.

Ante **cualquier** duda —reachability incierta, locator ambiguo, sesión no verificable como
propia y fresca— el resultado es `cli`. `co-explore` no necesita justificar `cli`; sí necesita
que las tres condiciones de `orca-session` (Orca alcanzable, sesión propia/fresca, perfiles de
las tres capas de control instalados) se cumplan explícitamente antes de tomar esa rama.

### Rama `orca-session`

Sustituye los pasos 3-5 de "Pasos de ejecución" (lanzar / punto de encuentro / normalizar)
cuando el resolver da `orca-session`. El explorador sigue tan read-only como en la rama `cli`:
solo cambia el transporte, no el invariante de la regla 1 del `SKILL.md`.

> **Se corre con UN comando, no a mano.** Los pasos 1-4 de abajo son lo que hace el entrypoint
> `cross-model-orca/assets/run-orca-session.mjs` (`createOwnedSession → createDispatch → awaitDone`,
> con degradación a `cli`); el conductor lo invoca como un solo comando —
> `node <cross-model-orca>/assets/run-orca-session.mjs --family codex --role read-only --mode
> <attended|unattended> --worktree <abspath> --spec-file <prompt.txt> --report <relpath> --root
> <dir>` — y lee la línea JSON de stdout (`code:0` → usar `reportPath`; `code!=0` → degradar a
> `cli`). **NUNCA improvisar `orca terminal create --command 'codex exec … < prompt > out'`:** eso
> es la rama `cli` metida a mano en una terminal Orca, sin el boot-wait (`tui-idle`) que evita
> perder el prompt en la carrera de boot ni la cosecha por `nonce`. El transporte se llama
> **`orca-session`** (sesión interactiva propia), no "orca-cli": "usar la CLI de Orca" = correr ese
> entrypoint, no teclear comandos `orca …` sueltos. Detalle del contrato en
> `cross-model-orca/SKILL.md` → sección 1 ("Cómo se corre: UN comando").

1. **Crear la sesión fresca dedicada.** `createOwnedSession({ family, role: 'read-only', mode,
   worktree, ... })` (`cross-model-orca/assets/dispatch-adapter.mjs`), con el perfil read-only de
   `cross-model-orca/assets/launch/profiles.md` según familia:
   - Codex: `codex -c features.apps=false -s read-only -a untrusted --disable hooks`
     (atendido) — la garantía read-only es el sandbox `-s read-only`, no un toolset acotado.
   - Claude: `--tools "Read,Grep,Glob"` + `--settings
     cross-model-orca/assets/launch/claude-readonly.settings.json` (`disableAllHooks: true`) +
     `--session-id <uuid>` — el toolset cerrado (sin Bash) es lo que da read-only duro; Claude no
     tiene una bandera de sandbox equivalente a `-s read-only`.

   MCP no se restringe por config en el default atendido: es **vigilancia manual** (el humano
   aprueba/rechaza en la TUI cualquier acción sensible del explorador durante su turno) — no hay
   inventario ni allowlist que instalar para esta rama. Para una corrida **desatendida**, el
   endurecimiento `--strict-mcp-config` (Claude) o el perfil `-p cmo-readonly` (Codex) es
   **opcional**, no un requisito — ver `profiles.md`.

2. **Armar y despachar el mismo prompt.** El prompt de exploración es el mismo que usa la rama
   `cli` — "Prompt de exploración" arriba, una variante por `mode`
   (`explore`/`counter-plan`/`investigate`), sin cambios: el explorador sigue leyendo, buscando y
   razonando, nunca editando ni ejecutando. Se despacha con `createDispatch({ session, spec, root
   })`, que genera el `nonce` e inyecta por su cuenta la instrucción de cierre
   (`buildEnvelopeInstructions`): el explorador termina su turno con el `output_contract` de su
   modo (headings del "Formato del informe") seguido de
   ```
   X-CMO: nonce=<..>
   STATUS: done
   ```
   Sin `taskId`/`dispatchId` en el texto: esos viajan por el `payload` del `worker_done` (Codex)
   o por la propiedad de la sesión (Claude), y el conductor los valida **antes** de cosechar —
   ver `cross-model-orca/reference.md` → "Envelope y cosecha crash-idempotente" (párrafo
   "Correlación vs. autoridad"; mismo contenido en `SKILL.md` sección 2, "Envelope con
   autoridad").

3. **El explorador no escribe su propio informe.** A diferencia de la rama `cli` (donde el
   stdout se redirige a `co-explore/scratch/explorer.out`), acá el informe solo vive en el
   transcript de la sesión. El **conductor** espera el fin del turno con `awaitDone({ session,
   dispatch, coordinatorHandle, reportPath, root, deadlineMs })`: Codex señaliza por comando
   (`worker_done`, con autoridad validada contra `taskId`/`dispatchId`/`sender`); Claude no emite
   `worker_done` — su fin de turno se detecta por la transición `tui-idle` posterior al dispatch.
   Con autoridad confirmada, `awaitDone` llama a `harvest()`
   (`cross-model-orca/assets/harvest-from-transcript.mjs`), que relee el transcript, desambigua
   por `nonce` (`selectAssistantByNonce`, para el caso de una sesión reutilizada con mensajes de
   dispatches previos) y valida el sentinel (`hasSentinel`) antes de persistir — al raw único de
   este dispatch, no al path de informe estable (ver punto 4).

4. **Cosechar a un raw único por dispatch, luego promover (sobrescribiendo) al path estable.**
   `harvest()` exige que `reportPath` sea un destino **inexistente** (`checkContainment` +
   `writeExclusive` con `wx`, ver `cross-model-orca/reference.md` → "Contención robusta y
   promoción atómica"): por eso el `reportPath` que recibe `awaitDone` en esta rama **nunca** es
   el path de informe estable y reusable del modo — pasarle ese path rompería en el segundo rerun
   sobre el mismo `<id>`, porque el destino ya existiría y la cosecha lo trataría como éxito
   idempotente sin reescribir (contrato pensado para un raw que nunca preexiste, no para un
   informe que debe poder sobrescribirse). En cambio:
   a. `harvest()` cosecha al raw único de este dispatch, en `co-explore/scratch/`, con un nombre
      derivado del `nonce` (p. ej. `scratch/explorer-<nonce>.raw`) — nunca colisiona entre
      corridas, así que `wx` es válido sin condiciones especiales.
   b. El **conductor** promueve ese raw al path de informe que le corresponde al modo — sin
      cambios respecto de hoy en cuanto a destino final:
      - `co-explore/findings-<familia>.md` (`explore`)
      - `co-explore/counter-plan-<familia>.md` (`counter-plan`)
      - `co-explore/investigate-<familia>.md` (`investigate`, standalone)

      con la raíz según el contexto: `.plans/<id>/co-explore/` o `.sdd/<id>/co-explore/` dentro
      de un flujo SDD, `.co-explore/<slug>/` en modo directo standalone — mismas raíces que
      documenta "Archivos de trabajo (scratch)" abajo y la matriz de `cross-model-orca/SKILL.md`
      → sección 5 ("Matriz de raíces por skill/modo"). La promoción escribe el contenido del raw
      contra el mismo "Formato del informe" (los headings fijos de arriba) a un temporal en el
      mismo directorio y lo renombra (`rename` atómico) sobre el destino, **sobrescribiendo**
      cualquier informe previo de su propio modo — exactamente igual que la rama `cli` normaliza
      `scratch/explorer.out` → `findings-<familia>.md`, y preservando la semántica de "Archivos
      de trabajo (scratch)" abajo: una corrida nueva sobre el mismo `<id>` sobrescribe los
      archivos de informe de su propio modo.
   c. Recién después de la promoción exitosa se marca la FSM `promoted` (dentro de `awaitDone`,
      con `dedupKey = ${dispatchId}:${nonce}`); si el proceso cae entre la escritura del raw y el
      `markPromoted`, el retry ve el raw ya existente (mismo `dispatchId`/`nonce`, contención por
      "ya existe") y lo trata como éxito idempotente — la contención `wx` sigue aplicando al raw,
      nunca al path estable.

5. **Ante falla del secundario, `recover`.** Si el explorador se cuelga o hay que abortar el
   turno, `recover({ session, dispatch })` interrumpe (`terminal send --interrupt`) y confirma
   idle (`terminal wait --for tui-idle`) antes de dar la sesión por recuperable — en rol
   read-only, idle confirmado alcanza (no hay riesgo de doble escritor, a diferencia del rol
   write de `cross-implement`). Si `recover` no confirma, o si el locator del transcript resulta
   ambiguo, o si la sesión no se puede garantizar propia y fresca, **degradar a `cli`** (ver
   abajo) — nunca redespachar por `orca-session` sobre una sesión ya comprometida.

### Degradación a `cli`

Explícita, sin cambio de comportamiento observable: si el resolver da `cli`, o si algo de la rama
de arriba falla —Orca no alcanzable, runtime `stale_bootstrap`, locator del transcript ambiguo,
sesión no verificable como propia y fresca, falta el binario de Orca/de la otra familia, o un MCP
requerido por el perfil—, se corre la rama `cli` de siempre ("Descubrir el revisor (puntero +
fallback)", arriba): mismo prompt, mismo "Formato del informe", misma ruta de informe. La
llamadora nunca queda bloqueada por la ausencia de Orca — degrada y sigue, igual que hoy degrada
ante la ausencia de un binario o MCP (regla 6 del `SKILL.md`, "Degradación").

### Portabilidad

Los comandos de lanzamiento (POSIX + PowerShell, por familia, rol y modo atendido/desatendido)
están completos en `cross-model-orca/assets/launch/profiles.md` — no se copian acá. La única
particularidad de esta rama, documentada en `cross-model-orca/reference.md` → "Portabilidad entre
shells": `dispatch-adapter.mjs` invoca `orca` con `spawnSync('orca', args, { encoding: 'utf8' })`
(arreglo de argv, sin `shell: true`), así que no hereda el problema de quoting de un prompt en
markdown que sí afecta a `codex exec`/`claude -p` en la rama `cli`; los comandos `orca
<subcomando> ...` de recuperación manual son idénticos en los dos shells.

### Read-only preservado

La rama `orca-session` es tan read-only como la `cli`: el explorador lee, busca y razona, nunca
edita ni ejecuta (regla 1 del `SKILL.md`) — la garantía cambia de mecanismo (sandbox/toolset
cerrado de la sesión Orca en vez de `-s read-only`/`--allowedTools` del subproceso), no de
invariante.

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

**Tope duro.** Al vencer el deadline sin ver `STATUS: done` en `co-explore/scratch/explorer.out`:
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

## Archivos de trabajo (scratch)

```
.plans/<id>/co-explore/
├─ findings-<familia-revisor>.md     # informe del explorador en modo `explore` — ver "Formato
│                                    #   del informe"
├─ findings-<familia-conductor>.md   # informe del conductor, mismo formato — escrito ANTES
│                                    #   de leer el del explorador (regla 2 del SKILL.md)
├─ counter-plan-<familia-revisor>.md # informe del explorador en modo `counter-plan`, mismo
│                                    #   formato — nunca pisa el findings de la fase `explore`
├─ investigate-<familia-revisor>.md  # informe del explorador en modo `investigate` (bug-shaped)
├─ investigate-<familia-conductor>.md# informe del conductor, mismo formato — escrito ANTES de
│                                    #   leer el del revisor (regla 2 del SKILL.md)
├─ synthesis.md                      # convergencias/divergencias + duelo de enfoques (o de
│                                    #   hipótesis en `investigate`) — ver plantillas de síntesis
├─ session.json                      # ref. de sesión del explorador, opcional (resume oportunista)
└─ scratch/
   ├─ prompt.txt                     # prompt de exploración, escrito a archivo con Write (nunca inline)
   ├─ explorer.out                   # salida del explorador — termina en `STATUS: done`
   ├─ explorer.err                   # stderr del proceso del explorador
   ├─ explorer.pid                   # PID capturado al lanzar en background
   ├─ explorer-thread.jsonl          # stream JSONL de `codex exec --json` (Vía B) — de acá se
   │                                 #   parsea el thread id (evento `thread.started`)
   └─ explorer-session.txt           # session/thread id del explorador (Vía B: parseado del
                                     #   jsonl; Vía C: generado con uuidgen)
```

En la rama `orca-session` ("Transporte: rama `orca-session`" arriba), `explorer.out`/`.err`/`.pid` no
aplican (no hay subproceso propio): en su lugar, `scratch/explorer-<nonce>.raw` es el destino
único por dispatch de `harvest()`, que el conductor promueve (sobrescribiendo) al informe estable
del modo — nunca se cosecha directo a `findings-<familia>.md` ni equivalentes.

En `debate`: `co-explore/debate.md` (la síntesis, hermana de `synthesis.md`) + los deltas crudos
por ronda en `co-explore/scratch/debate-r<n>.out`.

En `sdd-orchestrator` la raíz es `.sdd/<id>/co-explore/`, con los mismos nombres (ver `SKILL.md`
→ "Configuración" y el diseño, sección 8). En modo directo `investigate` no hay `.plans/<id>/`:
la raíz es un dir local untracked `.co-explore/<slug>/` en el repo (o un temp dir si el repo no
debe tocarse), con los mismos nombres.

**`session.json`.** Si el runtime del explorador expone una referencia de sesión reanudable
(Vía B: el thread id parseado del evento `thread.started` de `explorer-thread.jsonl`; Vía C:
`$SESSION_ID`/`$SessionId` propio), escribir:

```json
{ "tool": "codex", "session_id": "<id-o-ruta-que-permita-resume>", "mode": "explore", "created_at": "<ISO-8601>" }
```

Valores **ilustrativos**: `tool` refleja la vía realmente usada (`codex` en Vía B, `claude` en
Vía C) y `mode` el modo corrido (`explore` o `counter-plan`) — no son literales fijos.

Lo consume `cross-review` para el resume oportunista en la crítica informada del gate; si el
runtime no expone sesión, no escribir el archivo — la ausencia del archivo es la señal, no un
campo vacío dentro de él.

**Igual que en cross-review:** `co-explore/` es local, untracked (regla #10 de `sdd-flow`) y sin
autolimpieza — una corrida nueva sobre el mismo `<id>` sobrescribe `scratch/` y los archivos de
informe de su propio modo (`findings-*.md` en `explore`, `counter-plan-*.md` en `counter-plan`;
no crece sin límite); el usuario lo borra cuando quiere.
