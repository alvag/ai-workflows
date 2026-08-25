# cross-review — Referencia

Detalle operativo de la skill `cross-review`. El `SKILL.md` apunta acá cuando necesita el
contrato de invocación del revisor, la plantilla del prompt, el formato de salida o las dimensiones
de inspección.

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
- [Dimensiones de inspección](#dimensiones-de-inspección)
- [Plantilla de review-log.md](#plantilla-de-review-logmd)
- [Configuración](#configuración)
- [Manifest de corrida](#manifest-de-corrida)

---

## Resolución del intérprete de Python

Antes de ejecutar un script Python de la skill, resolver Python 3.9 o superior mediante una prueba
ejecutable. La presencia del nombre en `PATH` no alcanza: cada candidato debe correr código con
`-c`. El wrapper resultante conserva `py -3` como dos argumentos.

<!-- resolvedor-python:inicio -->
```sh
resolve_skill_python() {
  if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' \
      >/dev/null 2>&1; then
    python_skill() { python3 "$@"; }
    PYTHON_SKILL='python3'
    return 0
  fi
  if py -3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' \
      >/dev/null 2>&1; then
    python_skill() { py -3 "$@"; }
    PYTHON_SKILL='py -3'
    return 0
  fi
  printf '%s\n' \
    'ERROR: no executable Python 3.9+; python3 -c and py -3 -c failed or reported an older version' \
    >&2
  return 1
}
resolve_skill_python || exit 1
# Run scripts as: python_skill <script> [arguments...]
```

```powershell
$script:PythonSkill = $null
$PythonCandidates = @(
  @{ Display = 'python3'; File = 'python3'; Prefix = @() },
  @{ Display = 'py -3'; File = 'py'; Prefix = @('-3') }
)
foreach ($Candidate in $PythonCandidates) {
  try {
    $Prefix = @($Candidate.Prefix)
    & $Candidate.File @Prefix -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' *> $null
    if ($LASTEXITCODE -eq 0) {
      $script:PythonSkill = $Candidate
      break
    }
  } catch {
    continue
  }
}
if ($null -eq $script:PythonSkill) {
  throw 'ERROR: no executable Python 3.9+; python3 -c and py -3 -c failed or reported an older version'
}
function Invoke-SkillPython {
  $Prefix = @($script:PythonSkill.Prefix)
  & $script:PythonSkill.File @Prefix @args
}
# Run scripts as: Invoke-SkillPython <script> [arguments...]
```
<!-- resolvedor-python:fin -->


## Documentos de esta referencia

La referencia de esta skill son **dos** archivos, partidos por el momento en que se los lee, no por
tamaño. Cargar el segundo en toda corrida gastaría contexto en las corridas que no lo usan:

| Archivo | Qué trae | Cuándo se lee |
|---|---|---|
| `reference.md` (este) | portabilidad entre shells, descubrimiento e invocación del revisor, resume entre rondas, prompt, formato de salida, dimensiones de inspección, latencia y topes, matriz de resume y manifest | en toda corrida |
| `ciclo-de-vida.md` | identidad del finding, estados y transiciones, ledger append-only y su esquema, presupuestos, **aplicación pendiente de revisión**, vara de admisión de la defensa, cierre y adopción de logs legacy | ante la **primera salida conforme que traiga al menos un finding**, cualquiera sea el veredicto |

**El predicado de `ciclo-de-vida.md` es literal y no se parafrasea.** No es "al primer rechazo": la
ingesta —identidad, dedup, ledger y veredicto derivado— ya está gobernada por ese contrato, así que
hace falta aunque el conductor aplique o escale todo y no rechace nada. Y no es "al primer `REVISE`
con findings": este contrato admite `APPROVED` con findings `low` opcionales, y esa corrida también
lo necesita. Una corrida que termina en `APPROVED` **sin** findings no lo carga.

**Esa corrida igual escribe en el ledger, y no es una contradicción.** Toda salida conforme apendiza
su fila de cierre de ronda, incluida la limpia. Lo que la exime de cargar este archivo es que la
instrucción del loop es **autosuficiente para ese caso**: nombra la clase de entrada, el campo y sus
dos valores posibles, que es todo lo que hace falta para apendizar esa fila. Lo que se carga ante la
primera salida con findings es el **resto** —identidad, transiciones, presupuestos, cierre—, que solo
hace falta cuando hay findings que gobernar. El ahorro sigue siendo real; lo que no vale es fundarlo
en que sin findings no se escribe nada.

## Portabilidad entre shells (POSIX / PowerShell)

Las vías de invocación del revisor usan comandos de shell. Esos comandos se muestran en **dos
variantes**, y hay que elegir según el shell del entorno:

- **POSIX** — macOS y Linux, y también **Git Bash en Windows** (la Bash tool del agente). Es la
  forma en que están escritos los bloques `bash` de este documento; funcionan tal cual. Para las
  guardas Python, resolver un intérprete ejecutable 3.9+ con la receta de «Resolución del intérprete
  de Python» y ejecutar el mismo script en cualquier shell.
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
| Ejecutar en otro cwd | `(cd dir && cmd)` | `Push-Location dir; …; Pop-Location` (o el flag `-C dir` de `codex exec` — **`codex exec resume` no lo acepta**: ver "Asimetría de flags entre `exec` y `exec resume`") |
| Detectar el OS | `uname -s` | `$IsWindows` |

> **`uuidgen` falta en Git Bash de Windows** (solo está en macOS/Linux). Si se corre la Vía C por
> Git Bash en Windows, usar el fallback `powershell -NoProfile -Command "[guid]::NewGuid().ToString()"`,
> o que el agente genere un UUID v4 y lo pase como literal a `--session-id`.

Las reglas invariantes de "Invocar al revisor" valen en **ambos** shells: read-only siempre, y el
prompt **se escribe a archivo con la tool Write** (nunca inline ni `echo`/heredoc); solo cambia la
primitiva con que ese archivo llega a stdin (`<` en POSIX, `Get-Content -Raw | …` en PowerShell).

---

## Descubrir el revisor

<!-- inventario-familias:inicio -->
### Inventario de familias

Antes de cualquier preflight, la **raíz** de la corrida resuelve una vez la selección de workers
despachables. El conductor conduce y no entra en `families`; cada worker es un proceso aparte en
sesión fresca. Si el contrato de invocación trae `family_inventory`, **no se resuelve nada**: se
heredan `families` y `selection`, no se relee config y no se vuelve a avisar.

| Paso | Regla |
|---|---|
| 1 — workers **declarados** | comprobar el CLI en PATH de cada familia de `families`, **la del conductor incluida**. Que el conductor esté corriendo por construcción no exime del preflight de su worker |
| 2 — **sin declaración** | solo si no hay declaración, detectar qué CLIs están en PATH para proponer la selección. POSIX: `command -v codex` / `command -v claude`. PowerShell: `Get-Command codex -ErrorAction SilentlyContinue`. Nada más cuenta |

Los dos pasos miden el CLI porque es **condición necesaria de todas las vías**: el runtime del subagente
resuelve su disponibilidad corriendo `codex --version` y `codex app-server --help`, así que exige el
CLI y algo más. No es la intersección restrictiva, es el piso común.

La auditoría **no comprueba versión, auth, aislamiento ni lanzamiento**, y **no afirma capacidad
operativa**: una familia presente puede fallar igual su preflight, y eso sigue siendo un fallo real.

`selection` conserva cómo se resolvió la lista: `full` abarca todas las familias presentes y
`user_choice` declara menos. Se persiste con `families`, se hereda y nunca se reconstruye sondeando.

**Declarado ↔ disponible:**

| Caso | Resultado |
|---|---|
| no declara una familia presente | preferencia válida; no se sondea ni se despacha ese worker |
| declara una familia cuyo CLI está ausente | **error**: nombra la familia y que la auditoría no la encuentra |

`families: []` sigue siendo error. La allowlist admite solo `claude | codex`, sin duplicados y
canonizada a minúsculas.
<!-- inventario-familias:fin -->

Esta sección es la **fuente canónica** del descubrimiento: `co-explore` la referencia por
puntero (su fallback embebido es un resumen de esto).

Los nombres de tools/MCP/agentes cambian entre entornos. Resolver el revisor por **capacidad**
(un segundo modelo que pueda **criticar texto en read-only**) dentro de la allowlist heredada.
<!-- corpus-invariante:inicio:cross-review.reference.md.ba3c7e0a3716 -->
La familia opuesta sigue siendo el **default y la recomendación**, porque rompe la correlación de
<!-- corpus-invariante:fin:cross-review.reference.md.ba3c7e0a3716 -->
errores; una elección explícita puede obligar a un worker fresco de la familia del autor.

**Paso 1 — identificar la familia del autor.** Es la del agente que conduce la skill, sin
importar la superficie donde corre (CLI, app de escritorio, IDE, web): un agente Claude → autor
Claude; un agente Codex → autor GPT/Codex.

**Paso 2 — elegir el revisor dentro de `cross_model.families`** (`reviewer: auto`):

| Familia del autor | Revisor a buscar | Cómo detectarlo | Vía de invocación |
|---|---|---|---|
| Claude | Codex | ¿Existe el subagente `codex:codex-rescue` (plugin codex)? Si no, ¿`command -v codex`? | Vía A (preferida) o Vía B |
| GPT/Codex | Claude | ¿`command -v claude`? | Vía C |

Con solo la familia del autor seleccionada, la tabla se invierte sin reutilizar contexto: conductor
Claude → worker Claude fresco por la Vía C; conductor Codex → worker Codex fresco por las Vías A/B.
La salida recomienda revisión humana y nombra el costo:

> <!-- corpus-invariante:inicio:cross-review.reference.md.a4df8927e829 -->

> `Se recomienda revisión humana adicional: el worker ya no es de otra familia que el autor, por lo

> <!-- corpus-invariante:fin:cross-review.reference.md.a4df8927e829 -->
> que no rompe la correlación de errores.`

> **En PowerShell** la detección de binarios es `Get-Command codex -ErrorAction SilentlyContinue`
> (ídem `claude`) en vez de `command -v` — ver "Portabilidad entre shells (POSIX / PowerShell)".

**Precedencia canónica entre `families` y `reviewer`.** `families` es una allowlist infranqueable;
`reviewer` solo elige dentro de ella. Las demás sedes son vistas de esta matriz:

| `families` | `reviewer` | Resultado |
|---|---|---|
| `[claude, codex]` | `auto` | revisor de la familia opuesta al autor |
| `[codex]` (autor Claude) | `auto` | Codex |
| `[claude]` (autor Claude) | `auto` | worker Claude fresco + recomendación de revisión humana |
| `[claude]` | `codex` | **error**, no se despacha: `reviewer: codex está fuera de cross_model.families: [claude]` |
| `[claude, codex]` | `claude` (autor Claude) | corre con la recomendación same-family; se pierde el valor cross-model |

El caso simétrico para un conductor Codex aplica las mismas reglas. El override no amplía la
allowlist y un error de precedencia ocurre antes de cualquier preflight o despacho.

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

Si el CLI de la familia seleccionada no está disponible → veredicto `UNAVAILABLE` y ceder al gate
humano (degradación).

### Corpus del invariante

Este inventario clasifica el barrido base y cada candidato vigente. Las entradas `normativa`
corresponden uno a uno con marcas en el árbol; las `excluida` explican por qué el candidato no fija
la política de selección.

- `cross-review.README.md.b675b2c654b2` · excluida · README fuera del alcance normativo
- `cross-review.README.md.5f9466019af3` · excluida · README fuera del alcance normativo
- `cross-review.README.md.355c3639c7be` · excluida · README fuera del alcance normativo
- `cross-review.SKILL.md.ecc42237f1e7` · normativa · regla vigente
- `cross-review.SKILL.md.e87e2beaa014` · excluida · reescrita; resuelta por un ID vigente
- `cross-review.SKILL.md.3c200bf24d03` · excluida · reescrita; resuelta por un ID vigente
- `cross-review.SKILL.md.204178395747` · excluida · reescrita; resuelta por un ID vigente
- `cross-review.SKILL.md.2d888ab3fdcf` · normativa · regla vigente
- `cross-review.SKILL.md.d5edf6f83fc8` · excluida · reescrita; resuelta por un ID vigente
- `cross-review.reference.md.8d5aaa629b3f` · excluida · reescrita; resuelta por un ID vigente
- `cross-review.reference.md.d1fc854eb67a` · excluida · reescrita; resuelta por un ID vigente
- `cross-review.reference.md.5790967361b2` · excluida · reescrita; resuelta por un ID vigente
- `cross-review.reference.md.2fbdb7bf6dbf` · normativa · regla vigente
- `cross-review.reference.md.5a03619317fd` · excluida · reescrita; resuelta por un ID vigente
- `cross-review.reference.md.bb10b52eb68e` · excluida · reescrita; resuelta por un ID vigente
- `cross-review.reference.md.f954aa47fbf0` · excluida · reescrita; resuelta por un ID vigente
- `cross-implement.README.md.1fd1caaf7c1c` · excluida · README fuera del alcance normativo
- `cross-implement.README.md.ef0bcfe6b925` · excluida · README fuera del alcance normativo
- `cross-implement.README.md.40e253acf453` · excluida · README fuera del alcance normativo
- `cross-implement.README.md.46055988f932` · excluida · README fuera del alcance normativo
- `cross-implement.SKILL.md.e1b8d92f02b6` · excluida · reescrita; resuelta por un ID vigente
- `cross-implement.SKILL.md.054d95efc251` · excluida · reescrita; resuelta por un ID vigente
- `cross-implement.SKILL.md.24591100537b` · excluida · reescrita; resuelta por un ID vigente
- `cross-implement.SKILL.md.54be350db410` · excluida · reescrita; resuelta por un ID vigente
- `cross-implement.SKILL.md.fb32dce70dac` · excluida · reescrita; resuelta por un ID vigente
- `cross-implement.SKILL.md.abc982293528` · excluida · reescrita; resuelta por un ID vigente
- `cross-implement.reference.md.f149c2a01721` · excluida · reescrita; resuelta por un ID vigente
- `cross-implement.reference.md.b366f06b16aa` · excluida · reescrita; resuelta por un ID vigente
- `cross-implement.reference.md.b95da3b4ded1` · normativa · regla vigente
- `cross-implement.reference.md.98f3d648afda` · excluida · reescrita; resuelta por un ID vigente
- `co-explore.README.md.b2ace57744f3` · excluida · README fuera del alcance normativo
- `co-explore.README.md.598cd38e9809` · excluida · README fuera del alcance normativo
- `co-explore.SKILL.md.93289f9c0493` · excluida · reescrita; resuelta por un ID vigente
- `co-explore.SKILL.md.ab989f15a702` · excluida · reescrita; resuelta por un ID vigente
- `co-explore.SKILL.md.d20466e9d823` · excluida · reescrita; resuelta por un ID vigente
- `co-explore.SKILL.md.21c0d964aa00` · excluida · anti-anclaje de artefactos, no selección
- `co-explore.SKILL.md.f7b0d6f15016` · excluida · reescrita; resuelta por un ID vigente
- `co-explore.reference.md.016809096e5f` · excluida · reescrita; resuelta por un ID vigente
- `co-explore.reference.md.6eaa297dddb0` · excluida · reescrita; resuelta por un ID vigente
- `co-explore.reference.md.36ca1d70e0f1` · excluida · reescrita; resuelta por un ID vigente
- `co-explore.reference.md.0f08927e59bb` · excluida · gramática de IDs, no selección
- `co-explore.reference.md.e75121d70002` · excluida · anti-anclaje de artefactos, no selección
- `co-explore.reference.md.38042a6ad5b4` · excluida · armado de anexos, no selección
- `co-explore.reference.md.6d80ff6ecce1` · excluida · reescrita; resuelta por un ID vigente
- `co-explore.reference.md.b9ef85a664ff` · normativa · regla vigente
- `co-explore.reference.md.2c3a0eb6bb63` · excluida · reescrita; resuelta por un ID vigente
- `co-explore.reference.md.cafdbea24250` · excluida · reescrita; resuelta por un ID vigente
- `cross-review.SKILL.md.be17f0869bbc` · normativa · regla vigente
- `cross-review.SKILL.md.34fb3b023a63` · normativa · regla vigente
- `cross-review.SKILL.md.07028569a2d1` · normativa · regla vigente
- `cross-review.SKILL.md.248755b760dd` · normativa · regla vigente
- `cross-review.SKILL.md.bc0af365fd1c` · excluida · vista YAML; regla canónica aquí
- `cross-review.reference.md.ba3c7e0a3716` · normativa · regla vigente
- `cross-review.reference.md.a4df8927e829` · normativa · regla vigente
- `cross-review.reference.md.36a75d4a68ed` · excluida · fila de vista; regla canónica arriba
- `cross-review.reference.md.275b7f8886d1` · normativa · regla vigente
- `cross-implement.SKILL.md.650760997385` · normativa · regla vigente
- `cross-implement.SKILL.md.8aaf4f376d55` · normativa · regla vigente
- `cross-implement.SKILL.md.93fbb2190f20` · normativa · regla vigente
- `cross-implement.reference.md.7cce0044363c` · normativa · regla vigente
- `cross-implement.reference.md.f0d5e0198799` · normativa · regla vigente
- `cross-implement.reference.md.919a8d9922f4` · normativa · regla vigente
- `co-explore.SKILL.md.ada44733310a` · normativa · regla vigente
- `co-explore.SKILL.md.47d290a6ecc7` · normativa · regla vigente
- `co-explore.SKILL.md.3c9f87861874` · normativa · regla vigente
- `co-explore.reference.md.682df987638d` · normativa · regla vigente
- `co-explore.reference.md.7b096da38083` · normativa · regla vigente
- `co-explore.reference.md.5f58c89c7e0d` · normativa · regla vigente
- `co-explore.reference.md.5b072de65f96` · normativa · regla vigente

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
- **`sintesis` es el único tipo cuyo artefacto vive anidado**, bajo `.plans/<id>/co-explore/`, y por
  eso lleva su propia regla: **solo `artifact_path` apunta a ese subdirectorio**. El `ledger`, el
  `scratch` y el `checkpoint` se quedan en la raíz `.plans/<id>/`, con `sintesis` en los nombres para
  no colisionar con los de `spec`/`plan`/`tasks`. Sin la regla, el ledger se fragmentaría dentro de
  `co-explore/` y el checkpoint se rehidrataría desde un lugar distinto del que consulta `sdd-flow`.
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

**Sede única del ecosistema.** Toda skill que despache un worker por CLI cita esta sección en vez de
parafrasearla: `co-explore`, `cross-implement`, `bitbucket-code-review` y `sdd-pr-feedback`. Dos
copias del mismo argumento divergen sin que nadie lo note, y ya divergieron: una cubría una familia
y la otra no.

Antes de lanzar, comprobar que la versión instalada permite aislar al worker **de la familia que se
va a despachar**. Si falta el mecanismo, **no se lanza**: `UNAVAILABLE` y gate humano.

**Por qué fail-closed y no best-effort.** El sandbox del CLI acota lo que el worker escribe **en
disco dentro del working dir** —`-s read-only` en un revisor, `-s workspace-write` en un
implementador—, y **no acota los efectos de una tool MCP**. Un worker con los MCP del entorno puede
alcanzar una tool de ejecución y operar fuera del `working_dir`, con el sandbox intacto. Si no se
puede garantizar el aislamiento, la degradación correcta es no tener worker, no tener uno sin
contener. **Vale igual —o más— para un worker con permiso de escritura:** que su sandbox sea más
laxo no ablanda este preflight, lo hace más necesario.

##### La política, por familia

Cada familia tiene su mecanismo y no son intercambiables: los flags de Codex no existen en el CLI de
Claude, así que buscarlos ahí reporta "sin aislar" siempre.

<!-- politica-aislamiento:inicio -->

| Familia | Mecanismo requerido |
|---|---|
| `codex` | `--ignore-user-config` `--disable hooks` `--disable apps` `--disable plugins` |
| `claude` | `--safe-mode` |

<!-- politica-aislamiento:fin -->

`--safe-mode` alcanza para la familia Claude porque desactiva de una vez lo mismo que los cuatro
flags de Codex: su ayuda declara que arranca con *"CLAUDE.md, skills, plugins, hooks, **MCP
servers**, custom commands and agents, output styles, workflows…"* deshabilitados. En esa lista, lo
que este preflight persigue es **MCP servers**; el resto viene de arrastre y no molesta.

**Esta tabla es lo único congelado del criterio, y no enumera recetas.** Un inventario de recetas
transcrito a mano se desactualiza solo y pasa a mentir con apariencia de norma; el inventario se
deriva de las marcas `despacho:` del árbol.

##### El bloque, con una entrada por familia

Devuelve **0** si la familia pedida se puede aislar y **≠ 0** si no. Es una entrada por familia y no
un bloque que comprueba las dos: comprobar ambas marcaría `UNAVAILABLE` cuando falta el CLI de la
familia **que no se va a despachar**, que es el caso corriente de una allowlist con una sola familia.

**`exec` y `exec resume` se comprueban por separado, y `--disable` no se da por comprobado.** Son dos
afirmaciones distintas y ninguna implica la otra:

- Que el flag exista en `exec` **no** dice que la reanudación lo acepte. `exec resume` ya rechaza
  `-C`, `-s` y seis flags más (ver "Asimetría de flags entre `exec` y `exec resume`"), así que la
  suposición tiene precedente. Comprobar solo el lanzamiento deja pasar el primer dispatch y descubre
  el problema en el **fix round**, cuando ya hay un writer despachado y el árbol tocado.
- Que `features list` enumere `hooks`/`apps`/`plugins` dice que **existen**, no que el subcomando
  acepte `--disable` para apagarlas.

El bloque **no itera sobre nombres de subcomando** guardados en una variable, y eso es deliberado:
`for sub in "exec" "exec resume"; do codex $sub --help; done` **no funciona bajo zsh**, que no divide
expansiones sin comillas. La segunda vuelta invoca `codex "exec resume"`, un subcomando inexistente
que imprime la ayuda de nivel superior **con exit 0**; el `grep` no encuentra el flag y el preflight
devuelve `UNAVAILABLE` en **toda** corrida sin despachar nunca. Medido acá con `codex-cli` 0.147.0.
Dos llamadas explícitas no tienen esa forma y no la pueden recuperar en una edición futura.

```bash
# POSIX
comprobar_flags_codex() {   # $1 = la ayuda COMPLETA de un subcomando, ya capturada
  printf '%s\n' "$1" | grep -q -- --ignore-user-config || return 1
  printf '%s\n' "$1" | grep -q -- --disable            || return 1
}
preflight_aislamiento() {
  fam="$1"
  case "$fam" in
    codex)
      comprobar_flags_codex "$(codex exec --help 2>/dev/null)"        || return 1
      comprobar_flags_codex "$(codex exec resume --help 2>/dev/null)" || return 1
      for f in hooks apps plugins; do
        codex features list 2>/dev/null | grep -qE "^${f}[[:space:]]" || return 1
      done
      return 0 ;;
    claude)
      claude --help 2>/dev/null | grep -q -- --safe-mode || return 1
      return 0 ;;
    *) return 2 ;;   # familia no declarada en la política
  esac
}

preflight_aislamiento codex || { echo "UNAVAILABLE: aislamiento no garantizado (codex)"; }
```

```powershell
# PowerShell
function Test-FlagsCodex {
  # una ayuda por llamada, no un loop sobre las dos: `--help` devuelve un array de líneas y
  # @($exec, $resume) las aplanaría en una sola lista, donde un flag presente en uno solo pasaría.
  param([string[]]$Ayuda)
  if (-not ($Ayuda -match '--ignore-user-config')) { return $false }
  if (-not ($Ayuda -match '--disable'))            { return $false }
  return $true
}
function Preflight-Aislamiento {
  param([string]$Familia)
  switch ($Familia) {
    'codex' {
      if (-not (Test-FlagsCodex (codex exec --help 2>$null)))        { return 1 }
      if (-not (Test-FlagsCodex (codex exec resume --help 2>$null))) { return 1 }
      $feats = codex features list 2>$null
      foreach ($f in 'hooks','apps','plugins') {
        if (-not ($feats -match "^$f\s")) { return 1 }
      }
      return 0
    }
    'claude' {
      if (-not ((claude --help 2>$null) -match '--safe-mode')) { return 1 }
      return 0
    }
    default { return 2 }
  }
}
```

**El código de salida es el punto, y antes no lo era.** La versión anterior de este bloque asignaba
`FAIL=1` en sus ramas y **nunca inicializaba esa variable, nunca la consumía y no devolvía nada**:
medido con un CLI que no ofrecía ninguno de los mecanismos, el bloque completo devolvía `0`. Una
doctrina fail-closed cuya comprobación no puede cortar es una comprobación que no existe. Quien la
consuma tiene que **ramificar sobre el código**, no correr el bloque y seguir.

**Un mecanismo ausente ya hace fallar el lanzamiento por su cuenta** —un flag que el CLI no conoce es
un error de invocación—, así que el preflight no agrega seguridad: agrega **diagnóstico**. Convierte
un fallo de arranque confuso, a mitad de una corrida, en un `UNAVAILABLE` limpio antes de despachar.

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

<!-- despacho:inicio:cr-ronda1-posix:codex -->
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
<!-- despacho:fin:cr-ronda1-posix -->

<!-- despacho:inicio:cr-ronda1-ps:codex -->
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
<!-- despacho:fin:cr-ronda1-ps -->

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
- Rondas siguientes (mismo thread): el subcomando `resume` **rechaza nueve flags de `exec`** (ver
  "Asimetría de flags entre `exec` y `exec resume`", abajo) — entre ellas `-s`/`--sandbox` y `-C` —
  y el sandbox de la sesión original **NO es una garantía al reanudar**: un
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

  <!-- despacho:inicio:cr-resume-posix:codex -->
  ```bash
  SESSION_ID=$(cat <ruta/al/session.txt>)
  echo "resume → ${SESSION_ID:?vacío}"   # eco visible + corte si quedó vacío (ver nota --last)
  # Releer del scratch: las variables del proceso de la ronda 1 no sobreviven.
  MODEL=$(sed -n 's/.*"model":"\([^"]*\)".*/\1/p'  <ruta/al/session-meta.json>)
  EFFORT=$(sed -n 's/.*"effort":"\([^"]*\)".*/\1/p' <ruta/al/session-meta.json>)

  set -- exec resume "$SESSION_ID" --ignore-user-config \
         --disable hooks --disable apps --disable plugins \
         -c sandbox_mode=read-only --skip-git-repo-check --json \
         --output-last-message <ruta/veredicto.txt>
  [ -n "$MODEL" ]  && set -- "$@" -m "$MODEL"
  [ -n "$EFFORT" ] && set -- "$@" -c "model_reasoning_effort=$EFFORT"
  set -- "$@" -
  codex "$@" < <ruta/al/delta-rN.txt> > <ruta/al/thread-rN.jsonl> 2> <ruta/al/rN.err.txt>
  ```
  <!-- despacho:fin:cr-resume-posix -->
  En **PowerShell**:
  <!-- despacho:inicio:cr-resume-ps:codex -->
  ```powershell
  $SessionId = (Get-Content <ruta\al\session.txt>).Trim()
  if (-not $SessionId) { throw 'session id vacío' }; "resume → $SessionId"
  $Meta   = Get-Content -Raw <ruta\al\session-meta.json> | ConvertFrom-Json
  $Model  = $Meta.model
  $Effort = $Meta.effort

  $CodexArgs = @('exec','resume',$SessionId,'--ignore-user-config','--disable','hooks',
                 '--disable','apps','--disable','plugins','-c','sandbox_mode=read-only',
                 '--skip-git-repo-check','--json',
                 '--output-last-message','<ruta\veredicto.txt>')
  if ($Model)  { $CodexArgs += @('-m', $Model) }
  if ($Effort) { $CodexArgs += @('-c', "model_reasoning_effort=$Effort") }
  $CodexArgs += '-'
  Get-Content -Raw <ruta\al\delta-rN.txt> |
    & codex @CodexArgs > <ruta\al\thread-rN.jsonl> 2> <ruta\al\rN.err.txt>
  ```
  <!-- despacho:fin:cr-resume-ps -->
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
  <!-- despacho:inicio:cr-viac-r1-posix:claude -->
  ```bash
  SESSION_ID=$(uuidgen)   # Git Bash en Windows no trae uuidgen → ver "Portabilidad entre shells"
  (cd <working_dir> && claude -p --safe-mode \
      --model opus \
      --permission-mode default \
      --allowedTools=Read,Grep,Glob \
      --session-id "$SESSION_ID" \
      < <ruta/al/prompt-r1.txt>) > <ruta/al/veredicto.txt>
  ```
  <!-- despacho:fin:cr-viac-r1-posix -->
  En **PowerShell** (`uuidgen` → `[guid]::NewGuid()`; el subshell `(cd … && …)` →
  `Push-Location`/`Pop-Location`; `<` → pipe):
  <!-- despacho:inicio:cr-viac-r1-ps:claude -->
  ```powershell
  $SessionId = [guid]::NewGuid().ToString()
  Push-Location <working_dir>
  try {
    Get-Content -Raw <ruta\al\prompt-r1.txt> |
      claude -p --safe-mode --model opus --permission-mode default `
        '--allowedTools=Read,Grep,Glob' --session-id $SessionId > <ruta\al\veredicto.txt>
  } finally { Pop-Location }
  ```
  <!-- despacho:fin:cr-viac-r1-ps -->
  El mensaje final (veredicto + findings) sale por stdout → redirigirlo a archivo para parsear,
  igual que `--output-last-message` en la Vía B.
- Rondas siguientes (mismo thread, con memoria de lo ya discutido):
  <!-- despacho:inicio:cr-viac-resume-posix:claude -->
  ```bash
  (cd <working_dir> && claude -p --safe-mode \
      --model opus \
      --permission-mode default \
      --allowedTools=Read,Grep,Glob \
      --resume "$SESSION_ID" \
      < <ruta/al/delta-rN.txt>) > <ruta/al/veredicto.txt>
  ```
  <!-- despacho:fin:cr-viac-resume-posix -->
  En **PowerShell**:
  <!-- despacho:inicio:cr-viac-resume-ps:claude -->
  ```powershell
  Push-Location <working_dir>
  try {
    Get-Content -Raw <ruta\al\delta-rN.txt> |
      claude -p --safe-mode --model opus --permission-mode default `
        '--allowedTools=Read,Grep,Glob' --resume $SessionId > <ruta\al\veredicto.txt>
  } finally { Pop-Location }
  ```
  <!-- despacho:fin:cr-viac-resume-ps -->
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

Al resolver latencia, timeout o continuidad entre rondas, leer primero
`skills/cross-review/corridas-en-vuelo.md` → "Invariantes de recuperación". También rigen la sección
"Resume entre rondas": un corte de espera no decide por sí mismo si se puede reanudar o relanzar.

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

<!-- despacho:inicio:cr-latencia-sync:claude -->
```bash
# Sync (POSIX) — el conductor fija el tope vía su exec (Claude Code: Bash timeout 300000/600000):
( cd <working_dir> && claude -p --safe-mode --model opus --permission-mode default \
    --allowedTools=Read,Grep,Glob --session-id "$SESSION_ID" \
    < <ruta/al/prompt-r1.txt> ) > <ruta/al/veredicto.txt> 2> <ruta/al/claude-r1.err.txt>
```
<!-- despacho:fin:cr-latencia-sync -->
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

<!-- despacho:inicio:cr-latencia-background:claude -->
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
<!-- despacho:fin:cr-latencia-background -->
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
otro transporte hasta cerrar el recovery.

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

**Lo que libera el gate es el estado terminal, no haber concluido el cleanup.** Conservar recursos
propios para inspección —ante un bloqueo, un deadline vencido o una salida ilegible— es compatible con
presentar el gate: son dos decisiones independientes y ninguna espera a la otra. Un recurso propio en
pie no es un observable pendiente; esperar a retirarlo antes de presentar reintroduciría exactamente
el cuelgue que esta tabla elimina.

## Asimetría de flags entre `exec` y `exec resume`

**`codex exec resume` no acepta el mismo conjunto de flags que `codex exec`.** Armar el comando de
resume copiando el de la ronda 1 y cambiándole el subcomando **falla**, y es el error natural: el de
ronda 1 está a la vista dos secciones más arriba y las flags parecen genéricas del binario.

Derivado de `codex exec --help` y `codex exec resume --help` (codex-cli **0.147.0**, 2026-08-12).
Las nueve que `resume` **rechaza**:

| Flag | Qué hace en `exec` | Qué hacer en `resume` |
|---|---|---|
| `-C` | fija el working root | **posicionarse antes** con `cd`/`Push-Location`: el resume usa el **cwd del proceso** |
| `-s` / `--sandbox` | fija el modo de sandbox | pasarlo como `-c sandbox_mode="…"`, que además es **obligatorio** (no hereda el de la sesión) |
| `--add-dir` | agrega un directorio accesible | no hay equivalente; si hace falta, el resume no es la vía |
| `--approve-for-me`, `--color`, `--local-provider`, `--oss`, `-p`, `-V` | — | no aplican a una sesión ya creada |

`resume` agrega dos propias: `--last` y `--all`. Las **16 restantes** son comunes, incluidas las que
sostienen el aislamiento (`--ignore-user-config`, `--disable`) y las que fijan modelo y salida
(`-m`, `-c`, `-o`/`--output-last-message`, `--json`, `--skip-git-repo-check`).

> **La flag rechazada no es el riesgo grave.** `-C` en un resume corta con
> `error: unexpected argument '-C' found` — ruidoso, imposible de ignorar. Lo peligroso es su
> ausencia **no advertida**: sin `-C`, el working dir es el **cwd del proceso**, y un resume lanzado
> desde otro directorio opera sobre el repo equivocado **sin error, sin aviso y con exit 0**. Por eso
> todo bloque de resume de estas skills asume que el conductor ya está posicionado en el
> `working_dir`; si no puede garantizarlo, `cd` explícito antes de invocar.

Vale igual para los otros dos puntos donde se reanuda una sesión Codex —el fix round de
`cross-implement` y el seed desde co-exploración—: es una asimetría del CLI, no de esta skill.

## Resume entre rondas

El loop reusa el **mismo thread del revisor** para que tenga memoria de lo ya discutido:

- **Con al menos una aplicación pendiente de revisión, el artefacto actualizado viaja completo, sin
  excepción.** Va en el bloque `<artefacto_actualizado>` del asset de ronda, junto al delta. No
  alcanza con pedir "una nueva pasada sobre el artefacto actualizado": el revisor corre en un hilo
  que conserva la versión **anterior**, así que sin el texto nuevo delante puede completar la ronda
  entera sobre lo que ya tenía. Y entonces esa ronda no probaría nada sobre la edición, que es
  justamente lo que hay que probar.
- **Sin aplicaciones pendientes, se omite el bloque entero** y viaja solo el delta — el ahorro se
  conserva donde no hay nada nuevo que mirar. Omitido, no vacío: un bloque vacío le dice al revisor
  que no hubo cambios, cuando lo que pasó es que no se los mandaron. La misma condición que decide
  esto elige con qué evento se registra el cierre de la ronda (`ciclo-de-vida.md` → "Aplicación
  pendiente de revisión").

> **La omisión se apoya en el resume, y sin él se vuelve un agujero.** La premisa que la sostiene es
> la del primer punto: el revisor corre en el **mismo hilo** y ya tiene delante la versión que se le
> mandó antes, así que omitir el bloque solo le quita algo que ya tenía. En **rondas independientes**
> —la degradación de abajo— esa premisa no existe: la sesión es nueva y el asset declara que *lo que
> no esté acá no existe para él*.
>
> **Precedencia, para que no queden dos reglas ciertas y contradictorias:** con el transporte
> degradado a rondas independientes, **el artefacto viaja siempre**, haya o no aplicaciones
> pendientes; la condición de omisión se evalúa **solo** cuando la ronda reusa el thread.
>
> Lo que **no** cambia es el evento de cierre: sigue dependiendo de si hubo aplicaciones pendientes, y
> no de si el artefacto viajó por una razón de transporte. Una ronda independiente sin aplicaciones
> pendientes **recibe el artefacto y cierra como `ronda-completada`** — separar las dos cosas es lo
> que impide que el modo degradado libere aplicaciones que nadie observó.
>
> Sin esta precedencia el camino era concreto: resume no disponible, la ronda 1 rechaza todo, y la
> ronda 2 se despacha a una sesión fresca **sin ningún artefacto que revisar** — y cierra conforme.

**Las dos reglas que siguen valen en los dos casos, con artefacto o sin él.**

- **El delta se proyecta exclusivamente desde el ledger; no se redacta por separado.** Es una
  proyección, no un resumen escrito a mano: una sola fuente hace imposible que lo registrado y lo
  comunicado difieran. El registro de identidad de cada finding provee además el contenido con que
  el revisor evalúa el rechazo — sin el tema y sus anclas, las filas del ledger le dan el evento
  pero no con qué juzgarlo.

  Lo que el delta lleva por cada finding vivo: su ID, su estado actual, el evento que lo llevó ahí,
  el rationale del rechazo si lo hubo, y el tema con sus anclas. Y **la lista explícita de IDs
  rechazados sobre los que se espera respuesta** — es lo que el prompt de ronda N convierte en su
  bloque de respuestas obligatorias.
- Vía A: `--resume` (→ `task --resume-last`). Vía B: `codex exec resume`, **con la forma completa de
  la receta de la Vía B y no una abreviada** — lleva los cuatro flags de aislamiento, el override
  `-c sandbox_mode="read-only"` (obligatorio: resume NO hereda el sandbox de la sesión) y `--json`.
  Acá no se transcribe el comando a propósito: una invocación recortada en una enumeración es
  copiable, y copiarla sin los flags relevanta los MCP del usuario, que es exactamente lo que la Vía
  B advierte cuatro párrafos más arriba. Vía C:
  `claude -p --resume <session_id>`. El delta se pasa por stdin con la primitiva de cada shell
  (`<` en POSIX, `Get-Content -Raw | …` en PowerShell — ver "Portabilidad entre shells").
- Si el resume no está disponible en el entorno, degradar a rondas independientes re-enviando el
  artefacto actualizado completo (más caro, pero válido). **Siempre**, incluso sin aplicaciones
  pendientes: acá no hay hilo que conserve la versión anterior, así que la omisión de arriba no
  aplica — ver la precedencia declarada junto a esa regla.

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

<!-- despacho:inicio:cr-seed-posix:codex -->
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
<!-- despacho:fin:cr-seed-posix -->

<!-- despacho:inicio:cr-seed-ps:codex -->
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
<!-- despacho:fin:cr-seed-ps -->

Tras el seed, persistir `session-meta.json` en el scratch de esta skill igual que en una ronda 1
normal, para que las rondas siguientes no dependan del `session.json` de otra skill.

### El bloque de self-review

Viaja al revisor como tabla cerrada: `comprobación · resultado · evidencia`, con resultado en
`sin-hallazgos` · `con-hallazgos` · **`no-corrida`**. La ausencia de una fila **no** significa nada:
`no-corrida` se representa explícitamente.

Qué produce cada llamadora, medido en el árbol:

| Llamadora | Comprobaciones que aporta | Sede |
|---|---|---|
| `sdd-flow` | cobertura de spec (AC↔task) · scan anti-placeholder · consistencia de interfaces Produce/Consume · existencia y pertinencia AC↔fila del contrato | `sdd-flow/SKILL.md` → paso `tasks`, punto 3 "Self-review antes del gate" |
| `sdd-orchestrator` | cobertura AC por repo y por tarea · ubicación en los dos sentidos · cardinalidad tarea↔fila · invariantes del grafo · participación | `sdd-orchestrator/SKILL.md` → "Cross-artifact check (regla 5)", los cinco grupos |
| `sdd-pr-feedback` | **ninguna**: lo que tiene en `reference.md:164` es un *foco por gate*, no un self-review. Su bloque va **ausente**, igual que directo/draft | `sdd-pr-feedback/reference.md:164` |
| `cross-review` directo/draft | ninguna: no hay llamadora que las produzca. Bloque **ausente**, no vacío | — |

**`no-corrida` se aplica por fila, no por bloque.** Sirve cuando una llamadora que **sí** tiene
catálogo omitió una de sus comprobaciones — el caso de `sdd-flow` que salta una de sus cuatro. Una
llamadora **sin** catálogo no emite bloque: "todas las filas" no tiene referente y un implementador
podría inventar las cuatro de `sdd-flow`, las cinco del orquestador, o convertir el foco por gate en
comprobaciones. **Bloque ausente y bloque con filas `no-corrida` son estados distintos y ambos
válidos**, y el prompt los distingue.

## Prompt de revisión

Estructura XML compacta (estilo `gpt-5-4-prompting`: operador, no colaborador). Plantilla base:


El prompt vive en `assets/prompts/review.md` — es la **entrada exacta** del worker y se escribe a archivo con la tool Write. Placeholders que hay que sustituir antes de despachar: `{artifact_type}`, `{complexity}`, `{working_dir}`.


`{dimensiones}` se sustituye por la fila completa del `artifact_type` de "Dimensiones de
inspección" más los cuatro encargos de forma, como lista enumerada `D1..D10`. `D1..D6` siguen el
orden de la fila; `D7..D10`, el orden de los encargos de forma.

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
5. **Registrar el cierre de la ronda**: apendizar una fila `control-corrida` con
   `ronda-completada-valida` si esta ronda recibió el artefacto actualizado, o `ronda-completada` si
   no. Va acá —después de arbitrar, antes de derivar— para que la ronda no libere lo que ella misma
   aplicó y para que una ronda limpia quede registrada aunque el veredicto cierre el loop enseguida.
6. **Derivar** el veredicto del estado del ledger.

**Árbitro (lado Claude).** Para cada finding, decidir con `superpowers:receiving-code-review`:
- *Aplicar* — el finding es correcto y relevante → editar el artefacto → `aplicado`.
- *Rechazar* — incorrecto, fuera de alcance, o ya cubierto → no tocar, **registrar el motivo** →
  `rechazado`. Un rechazo sin motivo es un estado inválido, no un default.
- *Escalar* — disputa genuina o decisión de producto → `en-disputa`, para el gate humano.

Y para cada defensa recibida: *admisible* → `reabierto` y **se re-arbitra**; *inadmisible* →
`cerrado`. Una defensa admisible obliga a re-arbitrar, **no** a aceptar.

Nunca aplicar sin entender; nunca descartar sin razón. Todo va al ledger del `review-log.md`.

### La serie de convergencia

Una fila por ronda completada. Cada columna con selección, agrupación, reducción, unidad, corte y
valor vacío:

| Columna | Selección | Reducción | Unidad | Corte | Valor con ronda vacía |
|---|---|---|---|---|---|
| `emisiones` | filas `tipo=emision` con `ronda=r` | conteo | **emisión**, no identidad: una re-emisión cuenta, y es la señal | tras el arbitraje | `0` |
| `severidad_max` | las mismas | máximo del orden `low<medium<high` | nivel | tras el arbitraje | **`no evaluable`** |
| `procedencia` | las mismas, con `procedencia` presente | conteo por valor; denominador = emisiones con el campo | conteo absoluto **y** proporción | tras el arbitraje | **`no evaluable`**, nunca `0/0` |
| `descartes` | filas `tipo=descarte` con `ronda=r` | conteo | evento | tras el arbitraje | `0` |
| `pendientes` | findings cuya última transición a `aplicado` tiene `ronda ≤ r` sin `control-corrida` de cierre **válida** con ronda mayor | conteo | finding | **tras el cierre** de la ronda | `0` |
| `aplico` | existe `tipo=transicion` con evento de aplicación y `ronda=r` | booleano | — | tras el arbitraje | `false` |
| `tamano` | campo nuevo de la fila de cierre | valor registrado | **líneas del artefacto** | **al cierre, sobre el artefacto resultante tras arbitrar** | el valor de la ronda anterior |

**La severidad vigente de un finding sigue siendo la de su última `emision`**, como ya define la sede
de derivaciones: la serie no introduce una segunda definición.

**El tamaño es la única columna no derivable**, y se declara como campo `tamano_artefacto` en el
ámbito `control-corrida`, válido en los dos eventos de cierre de ronda. Unidad: **líneas**. Momento:
**el artefacto resultante tras arbitrar esa ronda** — no el recibido, porque lo que la señal de
crecimiento mide es el efecto de las aplicaciones de esa ronda. En una ronda **no conforme o con
timeout** no hay cierre y por lo tanto no hay fila de serie: la ronda no aparece.

#### Ledger de ejemplo para ejercer S4

Trae los seis casos que el fold tiene que resolver: ronda con emisiones, **ronda vacía**, descarte,
re-emisión, aplicación y una ronda que no aplica nada.

| Ronda | ID | tipo | evento | severidad | procedencia |
|---|---|---|---|---|---|
| 1 | F-01 | emision | — | high | *(ausente: ronda 1)* |
| 1 | F-02 | emision | — | medium | *(ausente)* |
| 1 | F-01 | transicion | aplica | — | — |
| 1 | — | control-corrida | ronda-completada-valida · `tamano_artefacto: 100` | — | — |
| 2 | F-01 | emision | re-emite (1ª) | high | `reemision` |
| 2 | F-03 | emision | — | low | `regresion` |
| 2 | F-04 | descarte | re-emite uno cerrado | — | — |
| 2 | F-01 | transicion | aplica | — | — |
| 2 | — | control-corrida | ronda-completada-valida · `tamano_artefacto: 130` | — | — |
| 3 | — | control-corrida | ronda-completada-valida · `tamano_artefacto: 130` | — | — |

**Serie esperada:**

| ronda | emisiones | severidad_max | procedencia | descartes | pendientes | aplico | tamano |
|---|---|---|---|---|---|---|---|
| 1 | 2 | `high` | **no evaluable** (campo ausente en ronda 1) | 0 | 1 | sí | 100 |
| 2 | 2 | `high` | `reemision` 1/2 · `regresion` 1/2 · `original` 0/2 | 1 | 1 | sí | 130 |
| 3 | **0** | **no evaluable** | **no evaluable** (sin emisiones) | 0 | **0** | no | 130 |

Tres cosas que este ejemplo fija y que el texto solo enuncia: la ronda 1 da `no evaluable` y **no**
`original 2/2`, porque el campo está ausente por contrato y no vacío; la ronda 3 vacía da
`no evaluable` y **no** `0/0`; y las pendientes de la ronda 2 bajan a cero recién en la 3, porque el
cierre de la 2 lleva `ronda: 2` y `2 > 2` es falso — que es el mecanismo entero de este cambio,
visible en una tabla.

### Veredicto derivado

**El veredicto de la corrida se deriva del ledger, no del bloque del revisor.** Con dos bloques, un
revisor puede emitir `DEFIENDO F-01`, cero findings nuevos y `APPROVED` porque el bloque de findings
quedó vacío — y un loop que corte ahí no arbitraría nunca esa defensa.

Las ramas se evalúan **en este orden** y la primera que aplica decide. Son exhaustivas: ningún ledger
cae fuera, y ninguna se solapa con otra.

| # | Estado del ledger tras arbitrar | Veredicto | Efecto sobre la tanda |
|---|---|---|---|
| 1 | existe ≥1 **aplicación pendiente de revisión** | `REVISE` | sigue: una ronda más puede resolverlo |
| 2 | sin pendientes, pero con ≥1 finding en estado **no terminal** | `REVISE` | sigue: hay margen de resolución |
| 3 | sin pendientes, solo terminales, con ≥1 `en-disputa` | `REVISE` | **corta la tanda** y abre el gate humano |
| 4 | sin pendientes y todo en `aplicado` o `cerrado` | `APPROVED` | corta: convergió |

El predicado no admite dos lecturas para un mismo ledger. El `APPROVED` del revisor **no corta el
loop por sí solo** si quedan defensas sin evaluar; y a la inversa, tras un arbitraje que no deja nada
abierto ni pendiente, la corrida converge **sin** gastar otra ronda para confirmarlo.

*Por qué la primera rama existe:* `aplicado` y `cerrado` no son terminales equivalentes. `cerrado` lo
resolvió una **decisión sobre su mérito** —el revisor aceptó el rechazo, o su defensa resultó
inadmisible—; `aplicado` es una **edición del conductor que ningún revisor vio**. Contarlos igual
permitía que una corrida convergiera sobre correcciones no revisadas, y aplicar un finding puede
introducir un defecto propio: es el caso que el presupuesto de re-apertura ya contempla, pero que
nadie podía ejercer si el loop cortaba antes. Definiciones en `ciclo-de-vida.md` → "Aplicación
pendiente de revisión".

*La re-aplicación no es una rama, es un caso de la primera.* Un finding `aplicado` en la ronda en
curso vuelve a estar pendiente aunque una ronda anterior hubiera observado su edición previa: la
condición mira la transición **más reciente** a `aplicado`, y esa ronda anterior vio otro texto.

*Por qué la tercera rama corta:* una disputa es terminal por definición — ninguna ronda adicional
puede resolverla, porque su destino es el arbitraje humano. Pero corta **solo cuando no quedan
aplicaciones pendientes**: con ellas todavía hay trabajo que una ronda sí resuelve, y cortar ahí
sería abandonarlo.

*Por qué `aplicado` sigue siendo terminal para el finding:* son dos terminalidades distintas. El
estado del finding no cambia —ninguna transición sale de `aplicado` salvo la re-apertura con
evidencia, que ya existe—; lo que deja de alcanzar es su contribución al veredicto **de la corrida**.

## Tandas y salida de rondas

Agotar el presupuesto **no cierra la revisión**: abre un **checkpoint** donde decide el humano. Una
**tanda** son `max_rounds` rondas (default 3); las tandas son **sucesivas y finitas**, y **ninguna se
concede sin autorización explícita**. No existe un modo que corra hasta `APPROVED` sin tope.

### Qué consume ronda

La ronda que obtiene del revisor su `ACEPTO | DEFIENDO` **sí** cuenta dentro de la tanda: es trabajo
del revisor y arbitraje del conductor. Lo que **no** consume ronda es el finding ya `cerrado` — no
genera arbitraje ni obliga a abrir una ronda por él. Tampoco los eventos del complemento, que se
descartan con motivo.

### Suficiencia de presupuesto

```
alcanza = rondas_disponibles >= 1 + (aplicacion_esperada ? 1 : 0)
```

`aplicacion_esperada` es verdadera si al corte existe **alguna** de tres condiciones de estado —no se
cuentan findings, porque todos pueden arbitrarse en una sola ronda:

1. un rechazo pendiente con defensa disponible,
2. un finding no terminal que todavía puede terminar aplicado,
3. una aplicación pendiente con re-apertura disponible.

`rondas_disponibles` se evalúa sobre **la modalidad que la opción autorizaría**, nunca sobre la tanda
agotada —que en el checkpoint vale cero y volvería inalcanzable toda otra fila:

| Modalidad | `rondas_disponibles` |
|---|---|
| conceder una tanda | `max_rounds` |
| seguir hasta `APPROVED` | `tope_efectivo − consumidas` |
| continuación dentro de una tanda activa | las no consumidas de esa tanda |
| ronda de cierre | `1`, y **no** se presenta como presupuesto para una validación posterior |

El checkpoint muestra `rondas_disponibles`, `aplicacion_esperada`, `rondas_minimas_requeridas` y
`alcanza` — **los cuatro, no un booleano**: esconder la fórmula obliga a confiar en ella. Es una
estimación conservadora, no una promesa: una ronda posterior puede descubrir otro finding.

### Retorno v2 y orden de presentación

Esquema único, dentro de `tandas_concedibles`. Los cuatro presentadores **solo muestran**: no
infieren, no recalculan, no reordenan.

| Campo | Tipo | Obligatorio | Autoridad |
|---|---|---|---|
| `contract_version` | `1 \| 2` | sí | la corrida |
| `serie` | lista de filas, una por ronda completada, con las siete columnas de la decisión 4 | sí en v2 | derivada del ledger |
| `presupuesto` | objeto con `rondas_disponibles`, `aplicacion_esperada`, `rondas_minimas_requeridas`, `alcanza` | sí en v2 | derivado |
| `opciones` | lista de 5 en v2, de 4 en v1 | sí | fija por versión |
| `recomendada` | id de opción, y `regla` con el número de fila de la tabla que la produjo | sí en v2 | derivada de `serie` |
| `advertencia_bucle` | texto o `null` | sí en v2 | derivada de `pendientes` y `presupuesto` |
| `aplicaciones_pendientes` · `ids_pendientes` | entero · lista | sí en las dos versiones | ya existen |

**Orden de presentación, normado y no a criterio:** `serie` → `advertencia_bucle` →
`aplicaciones_pendientes` con sus ids → `opciones` con la `recomendada` marcada. El presentador no
elige el orden.

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

### Las cinco opciones del checkpoint

Sin solapamiento, cada una con postcondición fijada sobre **tres ejes**:

| Opción | Artefacto | Revisión | Pendientes sin respuesta |
|---|---|---|---|
| **continuar así** (aprobar pese al `REVISE`) | aprobado, el flujo sigue | cerrada | → `en-disputa`, registrados |
| **conceder una tanda** | sin resolver, el gate no se cierra | continúa una tanda, y vuelve a preguntar | siguen `rechazado`, esperan respuesta |
| **seguir hasta `APPROVED`** | sin resolver, el gate no se cierra | continúa **sin volver a preguntar** hasta `APPROVED` o hasta el tope total | siguen `rechazado`, esperan respuesta |
| **ronda de cierre con artefacto congelado** | **congelado**, salvo la fase 6 | **exactamente una** ronda, y vuelve al checkpoint; no es terminal por sí misma | a `en-disputa` **al cerrar**, no al elegir |
| **cerrar la revisión** | **sin aprobar**, el flujo no sigue | cerrada | → `en-disputa`, registrados |

Ningún par comparte los tres ejes: "continuar así" y "cerrar" difieren en el artefacto (una lo
aprueba, la otra no); "conceder una tanda" y "seguir hasta `APPROVED`" difieren en si el humano
vuelve a decidir. **"Cerrar la revisión" es una salida adicional** —para cuando la revisión dejó de
rendir pero el artefacto no convence—, nunca un reemplazo de "seguir hasta `APPROVED`".

**Las cinco se ofrecen siempre**, incluso cuando el dato de retorno avisa que conceder no puede
converger: ese dato **advierte, no deshabilita** (ver `SKILL.md` → "Salida").

### La ronda de cierre: modalidad y máquina de procesamiento

#### Dónde vive

`modalidad: cierre` se persiste en **el descriptor de checkpoint**, que es la autoridad durable que
rehidrata la corrida, y se **refleja** en el prompt de esa ronda. El prompt no puede ser la
autoridad: no sobrevive a una pausa. Se usa `review-round-n.md` con el marcador; **no** hay asset
nuevo, porque un tercer prompt se desincroniza de los otros dos.

#### Orden exacto del procesamiento

Conserva el del loop, y solo cambia qué decisiones editan:

1. validar conformidad de la salida; no conforme o timeout → **no se arbitra nada**, el artefacto
   sigue congelado y se vuelve al checkpoint (degradación vigente, sin causa nueva);
2. deduplicar por tema y normalizar identidad y `procedencia`;
3. arbitrar **las respuestas a rechazos**: `ACEPTO` cierra; defensa se evalúa por admisibilidad;
4. arbitrar **los findings nuevos**, con el procedimiento normal —verificar, y decidir aplicar,
   rechazar o escalar—;
5. **lote de transiciones sin edición**, con el evento nuevo de la decisión 6.b: todo lo que el
   conductor decidiría aplicar y no es `high` pasa a `en-disputa` por **diferimiento por
   congelamiento**; toda defensa admisible no `high` pasa a `reabierto` y de ahí a `en-disputa` por
   el mismo evento; rechazo y escalamiento siguen el grafo con sus eventos de siempre; segunda
   re-emisión y presupuestos consumidos mantienen su comportamiento;
6. **fase atómica de edición**: se aplican **todos** los `high` que el conductor verificó y decidió
   aplicar —no el primero—, y después se registran todas sus transiciones a `aplicado`;
7. los rechazos que **sigan** sin respuesta pasan a `en-disputa`. **Nunca antes**: transicionarlos al
   elegir la opción los volvería terminales y su `ACEPTO`/`DEFIENDO` sería inalcanzable;
8. registrar el cierre de ronda con su `tamano_artefacto`;
9. derivar el veredicto con **el mismo predicado de cuatro ramas**, sin excepción. Si se aplicó algún
   `high`, esas aplicaciones quedan pendientes porque el número de cierre iguala al de aplicación;
10. volver al checkpoint.

#### 6.b — Dos eventos nuevos en el grafo, y por qué no alcanzaba con los existentes

Los catorce eventos que el grafo tenía antes de esta modalidad no expresaban *"el finding es
válido, pero esta modalidad prohíbe editar"*. Desde `abierto`, el único evento hacia `en-disputa`
era **escala (disputa genuina / decisión de producto)**; desde `reabierto`, **sostiene el rechazo**.
Registrar cualquiera de los dos falsearía el evento y el rationale del ledger, que es un registro
auditable: diría que el conductor rechazó algo que en realidad aceptaba.

Por eso el grafo lleva **dos transiciones más**, y su conteo cerrado —que `ciclo-de-vida.md` declara
literalmente en su sección "Transiciones"— es **16**:

| Estado origen | Evento | Actor | Destino | Terminal |
|---|---|---|---|---|
| `abierto` | **difiere por congelamiento** (la modalidad de cierre prohíbe editar) | conductor | `en-disputa` | sí |
| `reabierto` | **difiere por congelamiento** | conductor | `en-disputa` | sí |

Los dos son **exclusivos de la modalidad de cierre**: fuera de ella, un conductor que quiere aplicar
aplica. El rationale de estas filas registra qué se habría aplicado, de modo que el humano del gate
arbitre con esa información y no con un rechazo que nunca ocurrió.

#### Postcondición sobre los tres ejes

| Eje | Postcondición |
|---|---|
| artefacto | **congelado**, salvo la fase 6 |
| revisión | **exactamente una** ronda, y vuelve al checkpoint; no es terminal por sí misma |
| pendientes sin respuesta | a `en-disputa` **al cerrar**, no al elegir |

### Recomendación: tabla, ventana y caducidad

| # | Condición (primera que aplica) | Recomendada |
|---|---|---|
| 1 | las dos rondas de la ventana, **ambas con `emisiones > 0`**, con `regresion` ≥ la mitad de las emisiones de cada una | ronda de cierre |
| 2 | las dos de la ventana, **ambas con `emisiones > 0`**, sin caída de `severidad_max` **y** con `tamano` creciendo | ronda de cierre |
| 3 | `pendientes > 0` **y** `alcanza` | conceder una tanda |
| 4 | `pendientes > 0` **y** no `alcanza` | ronda de cierre |
| 5 | `pendientes = 0`, solo disputas, alguna `high` | cerrar la revisión |
| 6 | `pendientes = 0`, solo disputas, ninguna `high` | continuar así |
| 7 | *(fallback)* | conceder una tanda |

**Ventana:** las **dos rondas completadas inmediatamente anteriores** al checkpoint. Cualquier par
histórico deja la señal clavada y eclipsa las filas 3-7.

**Caducidad:** las filas 1 y 2 **no se evalúan si la ronda inmediatamente anterior fue una ronda de
cierre**. Sin esta condición la recomendación se repite aunque el cierre haya funcionado — observado
en el dry run de la corrida que produjo esta spec.

**Por qué 1 y 2 van antes de 3:** una corrida que arrastra regresiones casi siempre tiene
aplicaciones pendientes, así que con el cálculo de presupuesto arriba caería en la fila 3 y se le
recomendaría seguir, que es la conducta equivocada en el caso exacto que este cambio detecta.

**Las cinco opciones se ofrecen siempre.** La recomendación advierte, no deshabilita.

### "Seguir hasta `APPROVED`" y su tope total

Concede tandas **automáticamente**, sin volver a preguntar, hasta que ocurra **uno** de tres cortes:

| Corte | Qué pasa |
|---|---|
| el veredicto derivado es `APPROVED` | la revisión converge y cierra |
| se alcanza el **tope total** | vuelve al checkpoint con las cinco opciones |
| el predicado derivado da `REVISE` con **solo disputas y sin aplicaciones pendientes** | **corte anticipado obligatorio**: vuelve al checkpoint aunque falten rondas |

El tercero no es opcional: ninguna ronda puede resolver una disputa, así que seguir sería gastar el
tope sin posibilidad de converger. **Pero exige las dos condiciones a la vez.** Un ledger puede tener
disputas *y además* aplicaciones pendientes de revisión, y ahí cortar sería abandonar trabajo que una
ronda sí resuelve: las disputas no se van a resolver, las ediciones sin revisar sí se pueden mirar.
Mientras quede una pendiente, este corte no dispara y el modo sigue hasta uno de los otros dos.

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

## No-regresión y límite de medición

Los once invariantes se conservan. La evidencia de los diez textuales y el juicio explícito del
quinto son:

1. **Tope finito del loop.** “El loop nunca corre sin tope” permanece en la regla de `max_rounds`;
   “No existe un modo que corra hasta `APPROVED` sin tope” permanece en “Tandas y salida de rondas”.
2. **Gate humano en toda salida.** “Agotar el presupuesto no cierra la revisión: abre un checkpoint
   donde decide el humano” permanece en “Tandas y salida de rondas”; donde no puede presentarse, la
   corrida “se cierra en `REVISE` con las disputas abiertas y se escala”.
3. **Ledger append-only.** La plantilla conserva “Ledger (append-only — ninguna fila se
   sobrescribe)” y la proyección sigue siendo derivada: “se regenera al cierre de cada ronda, nunca
   se edita”.
4. **Dos presupuestos por finding, no recargables.** `ciclo-de-vida.md` conserva: “Los presupuestos
   son por finding, nunca por corrida”, “Una sola defensa” y “Una sola re-apertura”; la matriz de
   coexistencia conserva que la rehidratación no los recalcula ni recarga.
5. **Arbitraje del conductor — juicio, no comprobación.** Se juzga preservado porque el orden
   normativo todavía exige deduplicar antes de arbitrar, luego arbitrar respuestas y findings, y
   solo después derivar el veredicto. Esto es una evaluación semántica de autoridad y orden; ninguna
   cita ni verificación mecánica puede demostrar que el conductor conserve el arbitraje.
6. **Identidad por tema y deduplicación previa.** “Asignar identidad y deduplicar por tema los
   findings nuevos — antes de cualquier arbitraje” permanece en “Ingesta y arbitraje”.
7. **Revisor read-only.** “Las reglas invariantes de ‘Invocar al revisor’ valen en ambos shells:
   read-only siempre” permanece en “Vías de invocación”.
8. **Degradación que nunca bloquea.** Los fallos y vencimientos conservan la salida
   “`UNAVAILABLE`, degradar al gate humano”; el tope de pared sigue evitando una espera indefinida.
9. **Predicado y cuatro ramas.** “Las ramas se evalúan en este orden y la primera que aplica decide”
   permanece junto a la tabla byte-invariante de cuatro ramas en “Veredicto derivado”.
10. **Finding tardío esperado, sin cuota.** “Un finding genuinamente nuevo en una ronda tardía es
    comportamiento esperado del loop, no una anomalía” permanece en “Formato de salida”; el bloque
    de findings nuevos sigue admitiendo un `proposed_id` desconocido sin imponer cuota.
11. **La omisión no cierra findings.** “La omisión nunca cierra nada” permanece en “Validación por
    bloque”; el cierre todavía exige aceptación explícita o una defensa evaluada como inadmisible.

**Límite declarado.** Sin una corrida prospectiva instrumentada no puede afirmarse una mejora
cuantitativa de la convergencia. La serie de convergencia hace posible medirla más adelante: conserva
por ronda las siete columnas necesarias para comparar emisiones, regresiones, severidad, tamaño y
estado, pero por sí sola no demuestra que el nuevo contrato mejore esos valores.

## Checkpoint durable

Una corrida con checkpoint humano puede abarcar días y varias sesiones. Para que una **sesión nueva**
descubra que hay una revisión abierta y la rehidrate en vez de arrancar otra, el checkpoint persiste
un **descriptor por `run_id`**:

| Campo | Qué guarda |
|---|---|
| `contract_version` | versión del contrato (`1` \| `2`); autoridad de rehidratación frente a la cabecera de la sección del `review-log.md` |
| `run_id` | el de la corrida, estable entre tandas |
| `ledger` | la ruta del `review-log.md` y la sección de esta corrida |
| `ronda_acumulada` | la última ronda completada |
| `tope_vigente` | el `tope_efectivo` de la última `control-corrida` **cuyo evento fije tope** —`eleccion-tope` o `reeleccion-tope`—, si el modo automático está activo. Las filas de checkpoint y de cierre de ronda no llevan tope: tomar la última de la clase leería una fila vacía y dejaría el tope indeterminado justo al rehidratar |
| `modalidad` | `cierre` cuando el checkpoint autorizó una ronda de cierre; autoridad durable que rehidrata la modalidad |
| `causa_corte` | `tanda_agotada` \| `solo_disputas` |
| `gate_pendiente` | qué STOP quedó esperando decisión |
| `revisor` | la referencia de sesión con que reanudar |
| `manifest_seed` | copia estructuralmente idéntica del seed inmutable del sobre, si el manifest está habilitado |
| `manifest_first_dispatch_at` | el mismo timestamp write-once del sobre; puede seguir en `null` sin despacho |

Si el descriptor está ausente, la corrida se lee como `contract_version: 1`. Una versión desconocida
produce un error explícito: la corrida se detiene y se escala; nunca se elige una versión por
default. Si el descriptor y la cabecera de la sección del `review-log.md` discrepan, prevalece el
descriptor y se registra la discordancia. La rehidratación conserva los presupuestos consumidos: no
hay migración que los recalcule o recargue.

Matriz de resolución:

| Corrida | Descriptor | Sección del log | Resultado |
|---|---|---|---|
| iniciada bajo v1 | v1 o ausente | v1 | **termina bajo v1**: cuatro opciones, sin serie, sin `procedencia` |
| iniciada bajo v2 | v2 | v2 | v2 completo |
| cualquiera | **ausente** | cualquiera | se lee **v1** |
| cualquiera | **versión desconocida** | cualquiera | **error explícito**, no default: la corrida se detiene y se escala. Adivinar la versión es peor que fallar |
| v2 | v2 | `emision` sin `procedencia` | esa fila queda `no disponible`; **nunca se infiere** |
| v2 | v2 | descriptor y sección **discordantes** | gana el **descriptor**, que es la autoridad de rehidratación, y se registra la discordancia |

Un presentador actualizado que reciba `contract_version: 1` ofrece **exactamente cuatro opciones** y
omite serie, presupuesto y recomendación. Los presupuestos **no se recargan**: no hay migración que
los recalcule. La regla de adopción de logs anteriores no se toca ni se extiende — cubre otra
frontera, y mezclarlas haría parecer migrable una corrida legacy.

El descriptor se construye y valida **antes** de retirar el sobre activo y transferir el carrier al
checkpoint. Con manifest
deshabilitado, los dos nodos permanecen ausentes; no se serializan como `null`. Con manifest
habilitado, ambos son obligatorios y `manifest_seed` conserva exactamente `skill`, `mode`,
`preflight_started_at`, `families`, `transport` y `selection`: una clave de más, una de menos o una
diferencia de valor frente al sobre invalida el checkpoint. `manifest_first_dispatch_at` solo admite
el `null` original o el timestamp ya fijado; nunca un reloj de rehidratación.

El checkpoint se **escribe al abrirlo** y se **retira al terminal** de la corrida. Si una interrupción
deja sobre y checkpoint coexistiendo, el checkpoint válido tiene precedencia únicamente para
rehidratar la revisión y estas dos autoridades del manifest. El sobre sigue siendo autoridad de
intentos, cosecha, recursos y retiro: el checkpoint no permite declarar cese ni consumir una salida.

**Quién lo consulta, por modo:** en **embebido**, el `resume` de la llamadora, **antes** de iniciar
otra revisión; en **directo** y **draft**, `cross-review` misma, que es quien presenta. En los tres,
una corrida abierta se **rehidrata** con estas autoridades: no se inicia otra, no se recargan
presupuestos y no se toma el scratch de otra corrida.

**Frontera declarada:** es local y untracked como el resto de `.plans/`, así que sobrevive entre
sesiones **en la misma copia del directorio**, no entre máquinas ni entre checkouts.

## Dimensiones de inspección

### Capa específica — seis dimensiones por `artifact_type`

| Tipo | Dimensiones verificables |
|---|---|
| `spec` | **cobertura del objetivo:** cada resultado declarado tiene ≥1 AC; **observabilidad:** cada AC tiene resultado distinguible de su negación; **consistencia de alcance:** ningún AC exige algo excluido ni contradice a otro; **bordes del dominio:** precondiciones, límites y fallos tienen comportamiento decidido; **autoridad y actores:** cada decisión o escritura tiene responsable y gate; **adopción:** estados preexistentes o corridas vivas tienen resultado definido |
| `plan` | **satisfacción AC→mecanismo:** cada AC tiene un mecanismo causal concreto; **reúso:** ninguna pieza existente aplicable se reinventa; **orden y dependencias:** cada paso consume artefactos ya producidos; **contratos entre componentes:** productor y consumidor coinciden en forma y autoridad; **efectos colaterales:** mutaciones, compatibilidad y rollback tratados; **verificación:** cada prueba distingue cumplimiento de incumplimiento |
| `tasks` | **cobertura bidireccional AC↔task:** sin huérfanos en ningún sentido; **autosuficiencia:** cada task tiene rutas, entradas y decisiones; **atomicidad:** no mezcla cambios separables con finalizaciones distintas; **orden ejecutable:** productos antes que consumidores; **interfaces Produce/Consume:** nombres y firmas coinciden; **evidencia:** cada task referencia una verificación capaz de probar su resultado |
| `master-spec` | **contrato extremo a extremo:** toda interacción cross-service fija entradas, salidas y errores; **propiedad del AC de integración:** cada uno tiene un único responsable de cierre; **compatibilidad temporal:** despliegues y versiones parciales con comportamiento definido; **consistencia semántica:** significado compartido de estados e identificadores; **fallos distribuidos:** timeout, reintento, duplicado y parcialidad con dueño; **verificabilidad integrada:** cada AC se ejerce atravesando límites reales |
| `reparto` | **cobertura AC→repo:** cada AC global tiene dueño permitido; **límites de responsabilidad:** ningún repo recibe trabajo fuera de su contrato; **DAG válido:** dependencias existentes, completas y sin ciclos; **contratos de enlace:** cada dependencia declara artefacto producido y consumido; **cardinalidad:** propietarios únicos y participantes múltiples; **secuencia de integración:** gates y cierre con prerequisitos ya existentes |
| `sintesis` | **fidelidad:** cada postura con sus condiciones y evidencia; **recálculo independiente:** cada acuerdo importante verificado contra fuentes, no por consenso; **sesgo de orden:** la conclusión no depende de cuál enfoque se presentó primero; **auditoría del arbitraje:** cada descarte del conductor con fundamento contrastable; **concesión adversarial:** toda objeción válida cambia explícitamente la síntesis; **divergencias residuales:** incógnitas y desacuerdos no aparecen falsamente resueltos |

**Por qué la fila de `sintesis` autoriza atacar al conductor.** `auditoría del arbitraje` y
`sesgo de orden` apuntan a quien encarga la revisión, y eso es deliberado: en la rama 2 de
`co-explore` el conductor es **autor de la mitad del insumo y árbitro a la vez**, así que sin esa
autorización explícita el paso dejaría fuera lo único que nadie más mira.

### Capa transversal — cuatro encargos de forma

Se entregan **además** de la fila del tipo, en todos los tipos. Ninguna dimensión específica los
cubre, y las dos primeras destaparon en la corrida que produjo esta spec los defectos que ninguna
lectura había cuestionado:

| Encargo | Consigna literal al revisor |
|---|---|
| dry run | "no lo revises: **ejecutalo**. Empezá a escribir lo que este artefacto ordena y decime dónde te trabás por algo que no decidió" |
| implementación más floja | "¿cuál es la implementación más floja que satisface **todo** lo que pide y **no** resuelve el problema? Nombrala concretamente" |
| malentendido de buena fe | "¿qué malentendería un implementador de buena fe que no estuvo en la conversación que produjo esto?" |
| ausencia no pedida | "¿qué falta que nadie pidió? Despliegue, migración, interacción con lo que ya existe" |

### Invariantes de la sede

Toda dimensión describe una prueba que puede fallar, y ninguna equivale a "correctitud general".
Fusionar dos exige demostrar que dejaron de producir contraejemplos distintos.

### Proyección al prompt

`{dimensiones}` se sustituye por la fila completa del `artifact_type` más los cuatro encargos de
forma, como lista enumerada `D1..D10` — no como frase interpolada. La rendición se pide sobre **esos
mismos** IDs.

**La correspondencia ID→dimensión es normativa y fija**, porque la rendición se emite por ID y dos
productores que intercambien dos IDs producirían rendiciones incomparables sin que nada lo señale:

| ID | Dimensión |
|---|---|
| D1..D6 | las seis de la fila del `artifact_type`, **en el orden en que la tabla las escribe** |
| D7 | dry run |
| D8 | implementación más floja |
| D9 | malentendido de buena fe |
| D10 | ausencia no pedida |

## Plantilla de review-log.md

Un archivo por corrida, junto al artefacto (`.plans/<id>/review-log.md` en sdd-flow;
`.sdd/<id>/review-log.md` en sdd-orchestrator). Una sección por artefacto revisado; dentro, una
subsección por ronda. Acumulativo (no se pisa entre artefactos del mismo `<id>`).

```markdown
# Cross-review log — <id>

## <artifact_type> (<artifact_path>) — <ISO-8601>
Revisor: <codex-rescue | codex exec | claude -p | …>  ·  modelo: <model de config | CLI default | opus>
run_id: <estable en toda la corrida, incluidas las tandas siguientes>  ·  contract_version: <1 | 2>  ·  max_rounds: <n> (por tanda)

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
| 1 | — | control-corrida | ronda-completada | conductor | — | no se aplicó nada: la ronda 2 no recibirá artefacto |
| 2 | F-01 | transicion | defiende, con presupuesto | revisor | rechazado → defendido · presupuesto: defensa | <argumento> |
| 2 | F-01 | transicion | evalúa: admisible | conductor | defendido → reabierto · presupuesto: null | <por qué el argumento es nuevo> |
| 2 | F-02 | descarte | re-emite uno cerrado | revisor | — | <motivo del descarte> |
| 2 | — | control-corrida | ronda-completada | conductor | — | al cerrar la 1 no había aplicaciones: esta ronda no recibió artefacto |
| 3 | F-01 | transicion | aplica | conductor | reabierto → aplicado · presupuesto: null | <qué se editó> |
| 3 | — | control-corrida | ronda-completada | conductor | — | al cerrar la 2 no había aplicaciones: esta ronda no recibió artefacto |
| 3 | — | control-corrida | checkpoint | humano | decision_humana: conceder una tanda | queda 1 aplicación sin revisar (F-01) |
| 4 | — | control-corrida | ronda-completada-valida | conductor | — | recibió el artefacto con la aplicación de F-01 |

### Proyección (derivada — se regenera al cierre de cada ronda, nunca se edita)

| ID | Estado | Severidad vigente | Defensa | Re-apertura |
|---|---|---|---|---|
| F-01 | aplicado | high | consumida | disponible |
| F-02 | cerrado | medium | consumida | disponible |

> **Cómo se lee el cierre de cada ronda, que es lo que el ejemplo enseña.** El evento lo decide **qué
> recibió esa ronda al despacharse**, no qué pasó durante ella. Por eso las rondas 1, 2 y 3 cierran
> como `ronda-completada` —ninguna recibió artefacto, porque al cerrar la anterior no había
> aplicaciones pendientes— aunque en la 3 el conductor **sí** aplica F-01. Esa aplicación es la que
> hace que la ronda 4 reciba el artefacto y cierre como `ronda-completada-valida`.
>
> **La ronda 1 también deja fila.** Una ronda conforme que no aplicó nada y no cerró ningún finding no
> produciría ninguna entrada, y entonces "la ronda 1 ocurrió" sería indistinguible de "la ronda 1 nunca
> corrió". Es la razón por la que el evento existe.
>
> **Y el checkpoint de la ronda 3 no puede converger:** F-01 quedó `aplicado` y ninguna ronda posterior
> válida lo observó todavía. Por eso el presentador declara `aplicaciones_pendientes: 1` antes de
> ofrecer las opciones, y por eso la tanda concedida sirve para algo: la ronda 4 es la que cierra el
> ciclo.

### Resultado

**Eventos de arbitraje** (qué escrutinio hubo): aplicados <n> · rechazados <n> ·
defensas recibidas <n> · defensas admisibles <n>.
**Estados terminales** (dónde quedó cada finding): aplicado <n> · cerrado <n> · en-disputa <n>.
**Aplicaciones pendientes de revisión**: <n> — <IDs>. Ediciones que ninguna ronda posterior válida
observó; vacío si no quedó ninguna.

Veredicto final: <APPROVED | REVISE (…, <n> aplicaciones pendientes de revisión)> en <n> rondas y
<n> tanda(s).
Revisor: codex <modelo> (effort <esfuerzo>).

<!-- corpus-invariante:inicio:cross-review.reference.md.2fbdb7bf6dbf -->

**Límite:** un revisor independiente de otra familia aporta una crítica adicional; sigue siendo

<!-- corpus-invariante:fin:cross-review.reference.md.2fbdb7bf6dbf -->
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

Si se agota una tanda sin `APPROVED`, el "Resultado" lista las **disputas abiertas**, los **rechazos
sin responder** y las **aplicaciones pendientes de revisión** para que el humano decida en el gate
(ver "Tandas y salida de rondas"). Las tres, no dos: un cierre con cero disputas y cero rechazos sin
responder se lee como limpio, y puede estar tapando ediciones que ningún revisor miró.

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
- **`max_rounds` fija la cadencia del checkpoint, no una cantidad esperada para converger.** Una
  tanda chica acota cuánto trabajo consecutivo queda autorizado antes de devolver el control al
  humano; no predice en cuántas rondas se llega a `APPROVED`. La convergencia no la decide este
  número sino el predicado derivado: mientras queden aplicaciones pendientes de revisión no hay
  `APPROVED`, así que una aplicación en la última ronda de una tanda deja `REVISE` y continuar exige
  una autorización nueva. Ese es el efecto buscado del tope: que la decisión de seguir sea de una
  persona, con lo que falta a la vista.

## Consumo de co-exploración dual

Reemplaza al seed desde un `co-explore/session.json` singular, que deja de existir cuando
`co-explore` despacha dos workers.

### Matriz de resume desde co-exploración

Con dos workers hay **dos** sesiones por modo, una por familia. Cuál se reanuda **no queda a
<!-- corpus-invariante:inicio:cross-review.reference.md.275b7f8886d1 -->
criterio**: en la ruta recomendada se elige la sesión de la familia opuesta al autor. Cuando la
<!-- corpus-invariante:fin:cross-review.reference.md.275b7f8886d1 -->
selección obliga a la familia del autor, la regla de frescura de abajo gana y no se reanuda ninguna.

| Artefacto a revisar | Sesión que se reanuda | Contexto que recibe |
|---|---|---|
| `spec` · `master-spec` | `explore` de la familia **opuesta al autor** | índices + síntesis |
| `plan` · `reparto` | `counter-plan` de la familia **opuesta al autor** | índices + síntesis |
| `tasks` | **ninguna** sesión de co-explore | índices + síntesis |
| `sintesis` de `explore` | **ninguna** sesión de co-explore | índices + síntesis + **los informes fuente** |
| `sintesis` de `counter-plan` | **ninguna** sesión de co-explore | índices + síntesis + **los informes fuente** |

**Las dos filas de `sintesis` no reanudan ninguna sesión, y eso resuelve sus tres ramas de una vez.**
El crítico de una síntesis tiene que poder decir que está mal, y una sesión que la produjo —o que
produjo la mitad de su insumo— no es fresca para eso. De ahí se sigue el resto sin caso especial: un
worker `INVALID` no cambia nada porque no había sesión que reanudar; una selección **same-family**
tampoco, y arrastra el contrapeso de revisión humana que ya rige para todo worker de la familia del
autor; y en las **ramas degradadas** —donde el conductor exploró— la fila vale igual, con el
agravante de que ahí el conductor es autor de un mapa además de árbitro, que es justamente lo que el
foco de este tipo manda atacar.

Si la selección obliga a un revisor de la familia del autor, esta matriz **no reanuda** ninguna
sesión de `explore` o `counter-plan`: esas sesiones ya traen un mapa y no son frescas. Se lanza un
worker nuevo con índices y síntesis. El resume **entre rondas sigue** permitido, porque reanuda el
lanzamiento inicial fresco de esta misma revisión.

Reglas que acotan la matriz:

- **Un worker `INVALID` no es elegible**, aunque su sesión siga siendo reanudable: su informe no
  pasó los predicados, y reanudarlo importaría ese contexto malo a la revisión.
- **Rama 4 o `outcome: map_failure` → ningún contexto de co-explore** y revisor **fresco**. En la
  rama 4 no hubo co-exploración —es el "ninguno" de la regla, nombrado— y el análisis del conductor
  ya está embebido en el artefacto que se va a revisar; pasarlo como "contexto de co-exploración"
  sería etiquetar mal algo que no lo fue.
- **Sin sesión disponible → revisor fresco de la familia seleccionada**, con índices y síntesis como
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
sirviendo?"**. Es la sede canónica de los cuatro productores: `co-explore`, `cross-review`,
`cross-implement` y `bitbucket-code-review` apuntan acá y no duplican el esquema.

No es un log. El log de cada skill cuenta *qué pasó en una corrida* para poder auditarla; el
manifest existe para poder mirar **cien corridas juntas** y decidir si la capacidad se gana su
costo. De ahí que sea chico, plano y uniforme: lo que no se puede comparar entre corridas no vale
la pena registrarlo acá.

**Su hermano en vuelo es el sobre de corrida delegada, definido en `corridas-en-vuelo.md`.** El
manifest vive en `.cross-model/runs/` y registra corridas **terminadas**; el sobre vive en
`.cross-model/active/` y registra las que se están **ejecutando ahora**. Un checkpoint intermedio
transfiere el carrier y no materializa el manifest. Solo la posta terminal escribe el objeto
completo nuevo antes de retirar el último carrier activo.

| Transición | Manifest | Retiro del sobre |
|---|---|---|
| checkpoint intermedio | no se escribe | después de validar el descriptor y cumplir las condiciones operativas; la corrida sigue abierta en el checkpoint |
| outcome terminal | se escribe si está habilitado | después del manifest; si está deshabilitado o falla, la telemetría no bloquea las demás condiciones |

Si el terminal deja algo pendiente —una salida sin adjudicar, un recurso propio en pie—, lo que se
demora es el retiro terminal y nunca la escritura del manifest. El sobre además es **obligatorio** y
no lo apaga `mode: "off"`: esa clave apaga la telemetría, no la continuidad del trabajo en vuelo.

### El archivo

```
<repo>/.cross-model/runs/<started_at compacto>-<skill>-<mode>-<run_id>.json
```

Ejemplo: `.cross-model/runs/20260731T140211Z-co-explore-explore-95b6d861.json`

```json
{
  "skill": "co-explore",
  "mode": "explore",
  "started_at": "2026-07-31T14:02:11Z",
  "duration_s": 412,
  "families": ["codex", "claude"],
  "transport": "cli-exec",
  "outcome": "completed",
  "degradation": "branch-3",
  "selection": "user_choice"
}
```

**Un archivo por corrida, nunca uno agregado.** Un JSON acumulado obligaría a leer-modificar-escribir,
y dos corridas concurrentes —una tanda de `sdd-orchestrator` sobre varios repos— se pisarían.
Resolverlo pide locking: exactamente la infraestructura que este manifest existe para no traer. El
timestamp va adelante del nombre para que el orden lexicográfico sea el cronológico.

La ruta se deriva solo de `started_at`, `skill`, `mode` y el `run_id` estable de la corrida, y se
crea **sin reemplazo**. Dos corridas que empiezan en el mismo segundo no colisionan porque tienen
`run_id` distintos. Un retry del mismo `run_id` consulta únicamente si esa ruta existe. Si la ruta
existe, el cierre ya está materializado y termina sin abrir, validar, recalcular ni reescribir sus
bytes. Si la ruta falta, se intenta la creación exclusiva; si pierde esa carrera con `EEXIST`, el
cierre también termina sin abrir, validar, recalcular ni reescribir. La consulta de existencia no
convierte al archivo en autoridad; primero se deriva la ruta desde las autoridades persistidas. Un
segundo cierre conserva bytes idénticos. Que cualquier manifest anterior sea ilegible es
irrelevante: nunca participa en la derivación de la ruta ni del objeto actual.

Con una selección de una entrada, el manifest **se escribe igual**: `families` enumera la familia
delegada, `selection` distingue `full` de `user_choice`, `outcome` conserva el resultado terminal y
`degradation` registra la rama alcanzada. La elección no suprime el registro ni pisa la rama.

**Local y untracked, sin autolimpieza**, misma clase que `.plans/` y que los scratch de las tres
skills. El usuario borra el directorio cuando quiera; ninguna skill lo hace por él. Una corrida son
~300 bytes.

**Se construye como un objeto completo y nuevo y se escribe con la tool de escritura de archivos
del conductor, nunca con `echo` ni heredoc** —misma regla que los prompts, y por el mismo motivo: el
quoting. La tool escribe primero un candidato con UUID fresco en el mismo directorio
`.cross-model/runs/`; ese candidato tampoco se deriva de un manifest anterior. Luego el shell solo
lo promueve de forma exclusiva a la ruta final: no serializa contenido. En POSIX se usa un hard
link, cuya creación falla si el destino ya existe:

```bash
if ln "$manifest_tmp" "$manifest" 2>/dev/null; then
  rm -f "$manifest_tmp"
  manifest_creado=1
elif [ -e "$manifest" ]; then
  rm -f "$manifest_tmp"
  manifest_creado=0  # otro cierre ganó la carrera: no abrir ni validar el destino
else
  rm -f "$manifest_tmp"
  printf 'ERROR: no se pudo publicar el manifest de corrida\n' >&2
  manifest_creado=0
fi
```

En PowerShell 5.1 y posteriores, `File.Move` aporta la misma exclusión porque no reemplaza un
destino existente:

```powershell
try {
  [System.IO.File]::Move($manifestTmp, $manifest)
  $manifestCreado = $true
} catch [System.IO.IOException] {
  if (Test-Path -LiteralPath $manifest) {
    Remove-Item -LiteralPath $manifestTmp -Force -ErrorAction SilentlyContinue
    $manifestCreado = $false # otro cierre ganó la carrera: no abrir ni validar el destino
  } else {
    Remove-Item -LiteralPath $manifestTmp -Force -ErrorAction SilentlyContinue
    Write-Error 'No se pudo publicar el manifest de corrida'
    $manifestCreado = $false
  }
}
```

El candidato se elimina tanto al publicar como al perder la carrera. `.cross-model/runs/` no se lee
ni se copia como plantilla; ningún manifest anterior aporta valores. La única operación permitida
sobre un cierre previo es la consulta de existencia de la ruta ya derivada.
El objeto nuevo queda escrito antes del retiro terminal del último carrier activo. Esta regla no
aplica al retiro no terminal del sobre cuando el carrier pasa a un checkpoint. Después de una
creación exitosa se retira el sobre terminal; si la escritura está deshabilitada o falla, se informa
la causa y el sobre se retira al cumplir las demás condiciones operativas, sin quedar activo por la
telemetría. Los bloques anteriores solo materializan el objeto ya construido; los bloques de abajo
validan y leen sus bytes.

**Una corrida de `cross-review` con varias tandas escribe UN solo manifest.** Se escribe **una vez,
al outcome terminal de la corrida**, tal como ya lo define este contrato — y con tandas el terminal
es el **último**: un checkpoint intermedio **no** escribe manifest, ni parcial ni provisorio (este
esquema no admite estados intermedios ni `.partial + rename`).

**Quién lo finaliza es la llamadora, no `cross-review`:** al devolver el control en un checkpoint,
`cross-review` todavía no sabe si habrá otra tanda. La llamadora sí lo sabe apenas el humano decide,
así que es ella quien cierra el manifest tras el gate cuando la opción elegida es terminal.
El retorno que cruza esa frontera es
`manifest_authorities = {run_id, manifest_seed, manifest_first_dispatch_at}`. Con manifest en modo
off contiene solo `{run_id}`; no inventa los dos nodos ausentes. En modo directo o draft,
`cross-review` consume localmente el mismo retorno y conserva el mismo algoritmo canónico.

`started_at` es el del **primer** despacho de la corrida y, cuando no hubo ninguno, el inicio del
preflight; `duration_s` es **wall clock hasta el outcome terminal** —lo que con tandas incluye la
espera en el gate humano. Se acepta a propósito: lo que este campo mide es cuánto tarda la capacidad
en devolver un resultado utilizable, espera humana incluida.

### Autoridades y proyección fresca

La habilitación se resuelve una vez antes del preflight. Con telemetría activa, el sobre nace con
un `manifest_seed` inmutable y `manifest_first_dispatch_at: null`; con **modo off** los dos nodos
permanecen ausentes durante toda la corrida y el terminal informa `manifest no escrito: modo off`.
El seed contiene exactamente `skill`, `mode`, `preflight_started_at`, `families`, `transport` y
`selection`. `manifest_first_dispatch_at` es write-once: se fija inmediatamente antes de la primera
tool call de despacho y nunca se recalcula al reanudar.

| Campo final | Autoridad de la corrida |
|---|---|
| `skill` · `mode` · `families` · `selection` | `manifest_seed` |
| `started_at` | `manifest_first_dispatch_at`; sin despacho, fallback a `manifest_seed.preflight_started_at` |
| `duration_s` | entero no negativo entre `started_at` y el único reloj capturado al terminal |
| `transport` | vía candidata inicial resuelta según el orden operativo; `none` si no se resolvió ninguna |
| `outcome` · `degradation` | terminal adjudicado por el productor, dentro de su fila de vocabulario |

Con varias vías planificadas, el orden operativo del productor decide el escalar histórico:
`bitbucket-code-review` ordena `codex` antes de `claude`; los demás conservan el orden ya declarado
por su selector. Ese orden gobierna `families`, `transport`, el timestamp write-once y las tool calls.

**Centinelas de no-herencia.** La corrida A puede cerrar con
`started_at: 2026-07-31T14:02:11Z` y `duration_s: 412`; la corrida B, nacida de otro seed y otro
reloj terminal, cierra con `started_at: 2026-08-01T09:00:03Z` y `duration_s: 7`. El objeto B se
proyecta exclusivamente desde sus autoridades: no se lee A, y copiar `412` o el timestamp de A
violaría la comparabilidad que justifica el manifest aunque el JSON siguiera pareciendo válido.

### Los campos

Los nueve son **obligatorios**. Un campo que solo aparece a veces hace que "no hubo" y "no se supo"
sean el mismo dato ausente.

| Campo | Qué es | De dónde sale |
|---|---|---|
| `skill` | cuál de las cuatro corrió | fijo por skill |
| `mode` | el modo o `artifact_type` de esta corrida | contrato de invocación |
| `started_at` | ISO-8601 UTC del primer despacho o del preflight sin despacho | `manifest_first_dispatch_at` o fallback del seed |
| `duration_s` | entero no negativo hasta la resolución del outcome | reloj terminal menos `started_at` |
| `families` | familias delegadas — **siempre una lista** | topología de la corrida |
| `transport` | la vía candidata inicial o `none` si ninguna se resolvió | `manifest_seed` + frontera write-once |
| `outcome` | el estado terminal que la skill ya devuelve | envelope / salida |
| `degradation` | qué se perdió, o `none` | escalera / causa de indisponibilidad |
| `selection` | `full | user_choice`: cómo se resolvió la allowlist | `family_inventory` persistido |

`selection` no es opcional y no se reconstruye desde `families`: una lista de una entrada no dice
si era la única presente o si el usuario excluyó otra. Los cuatro productores —`co-explore`,
`cross-review`, `cross-implement` y `bitbucket-code-review`— lo emiten. Una corrida con
`selection: user_choice` y `degradation: none` no cuenta como degradada: la elección es causa de una
topología, no una degradación que pise la rama alcanzada.

**`families` es lista incluso cuando hay una sola familia.** Un campo que a veces es cadena y a
veces lista obliga a cada lector a ramificar, y el lector típico es un `grep` apurado.

**`duration_s` mide del inicio proyectado a la resolución del outcome**, no la corrida entera de la skill.
Preparar el paquete y arbitrar es trabajo del conductor, no de la capacidad delegada: incluirlo hace
que dos corridas midan cosas distintas según cuánto tardó el conductor en leer. En `co-explore`,
donde el despacho son dos lanzamientos en paralelo, es del primer lanzamiento al último outcome
resuelto — wall clock, no suma.

**`transport` es el del primer lanzamiento.** Una corrida que arranca con `cli-exec` y reanuda su sesión en
las rondas siguientes sigue siendo `cli-exec`; `cli-resume` es para la corrida que *entera* fue una
reanudación de una sesión ajena. Un terminal de preflight sin worker ni tool call usa `none`.

### El vocabulario es prestado, nunca propio

| Skill | `mode` | `outcome` | `degradation` (además de `none`) |
|---|---|---|---|
| `co-explore` | `explore` · `counter-plan` · `investigate` · `debate` | `completed` · `map_failure` | `branch-2` · `branch-3` · `branch-4` · `confirmed_wall` · `launch_flake` · `runtime_failure` · `deadline_exceeded` |
| `cross-review` | `spec` · `plan` · `tasks` · `master-spec` · `reparto` · `sintesis` · `draft` | `APPROVED` · `REVISE` · `UNAVAILABLE` | `rounds_exhausted` · `confirmed_wall` · `launch_flake` · `runtime_failure` · `deadline_exceeded` |
| `cross-implement` | `embebido` · `directo` | `IMPLEMENTED` · `PARTIAL` · `UNAVAILABLE` | `takeover` · `confirmed_wall` · `launch_flake` · `runtime_failure` · `deadline_exceeded` |
| `bitbucket-code-review` | `conductor` · `delegado` · `mixto` | `PUBLISHED` · `PROPOSED` · `UNAVAILABLE` | `revisor_invalido` · `panel_vacio` · `confirmed_wall` · `launch_flake` · `runtime_failure` |

Cada uno de esos términos ya existe en la skill que lo produce: el manifest los **serializa**, no
los define. Un manifest con taxonomía propia se desincroniza del envelope que dice resumir, y cuando
los dos difieren no hay forma de saber cuál miente. Si una corrida termina en un estado que no está
en su fila, lo que falta actualizar es la fila — o el estado es uno que la skill no documenta, y eso
es un hallazgo más valioso que el registro.

**También el vocabulario del transporte es prestado.** Cada skill emite únicamente los valores de
lanzamiento que documenta; el campo registra cómo se lanzó la corrida sin redefinir sus modos,
outcomes ni matriz de resume. `bitbucket-code-review` no amplía su vocabulario con valores que no
produce. La sintaxis de cada lanzamiento vive en la vía que lo ejecuta, no en este manifest.

### Cuándo se escribe

> **En el punto donde se resuelve el outcome, y todos los caminos de salida pasan por ese punto.**

Es la única regla del manifest que no es de forma, y la que decide si sirve. **Cada estado terminal
documentado proyecta su objeto nuevo**, incluidos los que devuelven `UNAVAILABLE` antes de despachar
nada. Esos terminales comparten los nueve ejes comparables de la serie; omitirlos o redactarlos desde
otro cierre rompería justamente la comparación entre corridas para la que existe este registro.

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

Vive en `cross_model` —política del **ecosistema**, no de una skill— porque las cuatro escriben el
mismo registro: apagarlo para una sola produciría una serie con huecos sistemáticos, que es peor que
no tenerla. Esquema completo en `sdd-flow/reference.md` → "Esquema de `.specify/config.yml`".

Default **on**: sin datos, cualquier decisión posterior sobre expandir o recortar el ecosistema es
intuición, y el costo es un archivo de 300 bytes en un directorio untracked.

### Qué se hace con esto

El manifest no decide nada por sí solo; habilita tres preguntas que hoy se contestan de memoria:

- **¿La capacidad está disponible donde corro?** Una proporción alta de `confirmed_wall` dice que el
  entorno no tiene el CLI seleccionado, no que la idea sea mala.
- **¿La diversidad se está conservando?** `branch-3` y `branch-4` frecuentes en `co-explore`
  significan que la topología dual se degrada seguido: dos mapas comparados es el supuesto del que
  cuelga todo el valor del modo.
- **¿El peldaño elegido es el más barato que alcanza?** Duraciones medianas por skill contra la
  escalera de rigor (`co-explore/reference.md` → "Escalera de rigor") muestran si se está pagando
  `cross-implement` donde alcanzaba una `cross-review`.
