# sdd-co-explore — Referencia

Detalle operativo de la skill `sdd-co-explore`. El `SKILL.md` apunta aquí cuando necesita la
plantilla del prompt de exploración (por modo), el formato del informe, la plantilla de
síntesis, el algoritmo de descubrimiento del explorador, los tiempos de espera o el árbol de
archivos de trabajo.

## Tabla de contenidos

- [Portabilidad entre shells (POSIX / PowerShell)](#portabilidad-entre-shells-posix--powershell)
- [Prompt de exploración](#prompt-de-exploración)
- [Formato del informe](#formato-del-informe)
- [Plantilla de `synthesis.md`](#plantilla-de-synthesismd)
- [Descubrir el revisor (puntero + fallback)](#descubrir-el-revisor-puntero--fallback)
- [Latencia y deadlines](#latencia-y-deadlines)
- [Archivos de trabajo (scratch)](#archivos-de-trabajo-scratch)

---

## Portabilidad entre shells (POSIX / PowerShell)

Mismo criterio que `sdd-cross-review/reference.md` → "Portabilidad entre shells (POSIX /
PowerShell)": esa sección es la fuente canónica de las equivalencias de shell que también usa
esta skill (detección de OS, prompt por archivo a stdin, generar un UUID, sondear variables de
entorno, remover variables en un proceso hijo para la higiene de entorno). No se duplican aquí.

Lo único que `sdd-co-explore` necesita y que cross-review no, porque `explore` corre siempre en
background (ver "Latencia y deadlines"):

| Primitiva | POSIX (bash / Git Bash) | PowerShell (Windows) |
|---|---|---|
| Lanzar en background y capturar el PID | `cmd & PID=$!` | `$proc = Start-Process -FilePath … -PassThru; $proc.Id` |
| Matar el proceso al vencer el deadline | `kill "$PID"` | `Stop-Process -Id $proc.Id -Force` |

El resto de las equivalencias (detectar el binario, prompt por archivo, UUID, sondeo de env,
higiene de entorno) son las mismas que en `sdd-cross-review/reference.md` y se referencian por
puntero en "Descubrir el revisor (puntero + fallback)".

## Prompt de exploración

Estructura XML compacta, mismo estilo que "Prompt de revisión" de `sdd-cross-review/reference.md`
(operador, no colaborador). Una variante por `mode`; ambas comparten el `output_contract` exacto.

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
  `sdd-cross-review` — el crítico puede marcar ahí si alguno de esos supuestos resultó
  equivocado.

## Descubrir el revisor (puntero + fallback)

**Puntero.** El algoritmo canónico de descubrimiento del explorador —identificar el harness
conductor, desambiguar la familia del modelo de respaldo, elegir un explorador de otra familia,
e higiene de entorno cuando hace falta— vive en `sdd-cross-review/reference.md` → "Descubrir el
revisor". Si esa skill está instalada en el entorno, léelo de ahí: esta sección no lo duplica.

**Fallback mínimo (`sdd-co-explore` sin `sdd-cross-review` instalada).** Misma regla dura:
el explorador nunca es de la misma familia de modelos que el autor. El autor es el modelo de
respaldo que ejecuta el agente conductor, no el CLI/harness — un Claude Code redirigido a un
proveedor no-Anthropic (GLM, Kimi, DeepSeek…) tiene como autor real ese modelo de respaldo, no
Claude. Sondea el entorno antes de decidir la familia:

```bash
# POSIX (macOS/Linux/Git Bash):
env | grep -iE 'ANTHROPIC_BASE_URL|ANTHROPIC_DEFAULT_(OPUS|SONNET|HAIKU)_MODEL|ANTHROPIC_MODEL'
```
```powershell
# PowerShell (Windows):
Get-ChildItem Env: | Where-Object Name -match 'ANTHROPIC_BASE_URL|ANTHROPIC_DEFAULT_(OPUS|SONNET|HAIKU)_MODEL|ANTHROPIC_MODEL'
```

Si `ANTHROPIC_BASE_URL` apunta a un host distinto de `api.anthropic.com`/`anthropic.com`, o
algún `ANTHROPIC_DEFAULT_*_MODEL`/`ANTHROPIC_MODEL` mapea a un modelo no-`claude-*` → el autor
real es ese modelo de respaldo. Si la sonda sale vacía o el `base_url` es Anthropic → autor =
Claude real. Si el conductor es Codex CLI (u otro que no sea Claude Code), salta la sonda: el
autor es GPT/Codex directo.

| Familia del autor | Explorador a buscar | Vía |
|---|---|---|
| Claude real | Codex | `codex exec` en background, read-only |
| GPT/Codex | Claude | `claude -p` en background, restringido a tools de lectura |
| Modelo de respaldo redirigido (GLM/Kimi/…) | Codex (preferido, sin higiene de entorno) o Claude real | Codex: igual que arriba. Claude: `claude -p` con higiene de entorno — primitiva embebida más abajo ("Invocación directa — autor GPT/Codex → explorador Claude"); camino preferido si `sdd-cross-review` está instalada: su `sdd-cross-review/reference.md` → "Higiene de entorno" trae el detalle completo |

Si ninguna opción de otra familia está disponible → `UNAVAILABLE` (regla 6 del `SKILL.md`).

**Invocación directa — autor Claude → explorador Codex.** Adaptado de
`sdd-cross-review/reference.md` → Vía B, lanzado en background porque `explore` nunca bloquea
al conductor (a diferencia de cross-review, que en Claude Code prefiere el camino sync):

```bash
# POSIX — el prompt ya está escrito a archivo con la tool Write (nunca inline, ni echo/heredoc):
mkdir -p co-explore/scratch
codex exec -s read-only -C <working_dir> --skip-git-repo-check \
    --output-last-message co-explore/scratch/explorer.out \
    - < co-explore/scratch/prompt.txt \
    2> co-explore/scratch/explorer.err &
PID=$!
echo "$PID" > co-explore/scratch/explorer.pid
```
```powershell
# PowerShell:
New-Item -ItemType Directory -Force -Path co-explore\scratch | Out-Null
$proc = Start-Process -FilePath codex -NoNewWindow -PassThru `
  -RedirectStandardInput  co-explore\scratch\prompt.txt `
  -RedirectStandardError  co-explore\scratch\explorer.err `
  -ArgumentList 'exec','-s','read-only','-C','<working_dir>','--skip-git-repo-check','--output-last-message','co-explore\scratch\explorer.out'
$proc.Id | Out-File co-explore\scratch\explorer.pid
```

`-s read-only` (`--sandbox read-only`) garantiza que el explorador no escribe nada en el repo;
`--output-last-message` deja el informe final —el que debe terminar en `STATUS: done`— en
`explorer.out`, listo para el poll del punto de encuentro (ver "Latencia y deadlines"). Codex
reporta el session id en su salida; capturarlo si se quiere escribir `session.json`.

**Invocación directa — autor GPT/Codex → explorador Claude.** Adaptado de
`sdd-cross-review/reference.md` → Vía C, camino BACKGROUND (el mismo patrón que usa cross-review
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
CLAUDE.md del usuario del `working_dir`. Si la sonda de arriba detectó redirección, antepón la
higiene de entorno a este bloque para que el explorador llegue a Claude real y no al modelo de
respaldo redirigido — camino preferido si `sdd-cross-review` está instalada: su
`sdd-cross-review/reference.md` → "Higiene de entorno" trae el detalle completo (por qué no toca
la sesión en curso, cuándo aplicarla de forma condicional, degradación por auth). Primitiva
mínima, embebida aquí para que este fallback no dependa de esa skill (variables reales que limpia
`sdd-cross-review/reference.md` → "Higiene de entorno", copiadas de ahí):

```bash
# POSIX — antepuesto al `claude -p …` del bloque de arriba:
env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN \
    -u ANTHROPIC_DEFAULT_OPUS_MODEL -u ANTHROPIC_DEFAULT_SONNET_MODEL -u ANTHROPIC_DEFAULT_HAIKU_MODEL \
    -u ANTHROPIC_MODEL -u ANTHROPIC_SMALL_FAST_MODEL \
  claude -p --safe-mode --model opus --permission-mode default --allowedTools=Read,Grep,Glob …
```
```powershell
# PowerShell — proceso hijo aislado (Remove-Item Env: es a nivel de sesión: mutaría la actual sin
# restaurarla, por eso se aplica en un hijo, no en el proceso corriente):
$strip = "Remove-Item Env:ANTHROPIC_BASE_URL,Env:ANTHROPIC_AUTH_TOKEN," +
         "Env:ANTHROPIC_DEFAULT_OPUS_MODEL,Env:ANTHROPIC_DEFAULT_SONNET_MODEL," +
         "Env:ANTHROPIC_DEFAULT_HAIKU_MODEL,Env:ANTHROPIC_MODEL,Env:ANTHROPIC_SMALL_FAST_MODEL " +
         "-ErrorAction SilentlyContinue; "
powershell -NoProfile -Command ($strip + "claude -p …")
```

Caso límite: con la sesión redirigida y sin posibilidad de aplicar esta higiene (por ejemplo, un
entorno restringido que no permite anteponer `env -u` ni lanzar el proceso hijo aislado) →
preferir Codex; sin Codex disponible → `UNAVAILABLE` (regla 6 del `SKILL.md`).

`$SESSION_ID`/`$SessionId`, capturado en `explorer-session.txt`, es la base para escribir
`co-explore/session.json` (ver "Archivos de trabajo (scratch)") cuando `sdd-cross-review` está
instalada y puede reanudar ese thread.

## Latencia y deadlines

| Modo | Deadline default | Poll cada | Intentos aprox. |
|---|---|---|---|
| `explore` | 600 s | 10 s | ~60 |
| `counter-plan` | 300 s | 10 s | ~30 |

Override: `cross_review.co_explore.deadline` en la config (ver `SKILL.md` → "Configuración"); si
no está seteado, se usa el default de la tabla según `mode`. Una exploración tarda más que una
crítica de cross-review (tiene que recorrer el repo desde cero), por eso el default de `explore`
es más alto.

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
├─ synthesis.md                      # convergencias/divergencias + duelo de enfoques
│                                    #   ver "Plantilla de `synthesis.md`"
├─ session.json                      # ref. de sesión del explorador, opcional (resume oportunista)
└─ scratch/
   ├─ prompt.txt                     # prompt de exploración, escrito a archivo con Write (nunca inline)
   ├─ explorer.out                   # salida del explorador — termina en `STATUS: done`
   ├─ explorer.err                   # stderr del proceso del explorador
   ├─ explorer.pid                   # PID capturado al lanzar en background
   └─ explorer-session.txt           # session id del explorador, si la vía lo genera (Vía C)
```

En `sdd-orchestrator` la raíz es `.sdd/<id>/co-explore/`, con los mismos nombres (ver `SKILL.md`
→ "Configuración" y el diseño, sección 8).

**`session.json`.** Si el runtime del explorador expone una referencia de sesión reanudable
(Vía B: session id de `codex exec`; Vía C: `$SESSION_ID`/`$SessionId` propio), escribir:

```json
{ "tool": "codex", "session_id": "<id-o-ruta-que-permita-resume>", "mode": "explore", "created_at": "<ISO-8601>" }
```

Valores **ilustrativos**: `tool` refleja la vía realmente usada (`codex` en Vía B, `claude` en
Vía C) y `mode` el modo corrido (`explore` o `counter-plan`) — no son literales fijos.

Lo consume `sdd-cross-review` para el resume oportunista en la crítica informada del gate; si el
runtime no expone sesión, no escribir el archivo — la ausencia del archivo es la señal, no un
campo vacío dentro de él.

**Igual que en cross-review:** `co-explore/` es local, untracked (regla #10 de `sdd-flow`) y sin
autolimpieza — una corrida nueva sobre el mismo `<id>` sobrescribe `scratch/` y los archivos de
informe de su propio modo (`findings-*.md` en `explore`, `counter-plan-*.md` en `counter-plan`;
no crece sin límite); el usuario lo borra cuando quiere.
