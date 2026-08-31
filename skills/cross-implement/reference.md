# cross-implement — Referencia

Detalle operativo de la skill `cross-implement`. El `SKILL.md` apunta acá para el descubrimiento
del implementador, las vías de invocación por familia, el prompt-contrato, la revisión del
conductor, el fix loop, los tiempos y los archivos de trabajo.

## Tabla de contenidos

- [Documentos de esta referencia](#documentos-de-esta-referencia)
- [Portabilidad entre shells (POSIX / PowerShell)](#portabilidad-entre-shells-posix--powershell)
- [Descubrir el implementador](#descubrir-el-implementador)
- [Vías de invocación](#vías-de-invocación)
- [Matriz de verificación](#matriz-de-verificación)
- [Prompt del implementador](#prompt-del-implementador)
- [Formato del reporte](#formato-del-reporte)
- [Medición de base y adjudicación](#medición-de-base-y-adjudicación)
- [Revisión del conductor](#revisión-del-conductor)
- [Fix loop](#fix-loop)
- [El delta revisable de un bloque](#el-delta-revisable-de-un-bloque)
- [Secuencia Git entre bloques](#secuencia-git-entre-bloques)
- [Orden de cierre de la secuencia](#orden-de-cierre-de-la-secuencia)
- [Latencia, deadlines y banner](#latencia-deadlines-y-banner)
- [Rutas por invocación](#rutas-por-invocación)
- [Archivos de trabajo (scratch)](#archivos-de-trabajo-scratch)
- [Log de implementación](#log-de-implementación)
- [Cuándo un reporte ilegible no invalida la revisión](#cuándo-un-reporte-ilegible-no-invalida-la-revisión)

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

La referencia de esta skill son **tres** archivos, partidos por el momento en que se los lee, no por
tamaño. Cargar los tres siempre desperdicia contexto en una corrida que sale bien a la primera:

| Archivo | Qué trae | Cuándo se lee |
|---|---|---|
| `reference.md` (este) | descubrimiento, vías de invocación, prompt, reporte, revisión, fix loop, tiempos y scratch | en toda corrida |
| `contrato-verificacion.md` | esquema del contrato, reglas de congelamiento, adjudicación, gate previo al dispatch y sus bloques de validación | al armar y aprobar el contrato, antes de delegar |
| `ownership.md` | las cuatro clases de falla, matriz de cierre por bloque, presupuestos, rollback, re-baseline aislado, takeover, `### Terminales de secuencia` y precedencia de topes | al cerrar cualquier bloque, haya fallado o no |

En toda corrida, antes del primer despacho, leer también
`skills/cross-review/corridas-en-vuelo.md` → "Invariantes de recuperación". Ese contrato gobierna el
deadline, el relanzamiento, las rutas de salida y la elección entre aviso y sondeo.

## Portabilidad entre shells (POSIX / PowerShell)

Mismo criterio que `cross-review/reference.md` → "Portabilidad entre shells (POSIX / PowerShell)":
esa sección es
la fuente canónica de las equivalencias (detección de binarios, prompt por archivo a stdin, UUID,
background y kill). No se duplican acá. Regla invariante idéntica: el prompt **se escribe a
archivo con la tool Write** (nunca inline ni `echo`/heredoc) y llega por stdin.

## Descubrir el implementador

El algoritmo canónico de identificación de familia vive en `cross-review/reference.md` →
"Descubrir el revisor" (autor = la familia del agente que conduce, sin importar la superficie).
Acá cambia el rol buscado: no un crítico read-only sino un **implementador con escritura acotada**.

| Familia del autor | Implementador por default | Cómo detectarlo | Vía |
|---|---|---|---|
| Claude | Codex | `command -v codex` (PowerShell: `Get-Command codex -ErrorAction SilentlyContinue`) | Vía W-B (workspace-write) |
| GPT/Codex | Claude | `command -v claude` | Vía W-C (permisos path-scoped) |

<!-- corpus-invariante:inicio:cross-implement.reference.md.7cce0044363c -->

La familia opuesta es el default y la recomendación. `cross_model.families` es la autoridad: si la

<!-- corpus-invariante:fin:cross-implement.reference.md.7cce0044363c -->
allowlist contiene solo la familia del autor, **corre** un implementador fresco de esa familia —
conductor Claude → worker Claude por la Vía W-C; conductor Codex → worker Codex por la Vía W-B—.
La salida debe incluir, en las dos direcciones:

> <!-- corpus-invariante:inicio:cross-implement.reference.md.f0d5e0198799 -->

> `Se recomienda revisión humana adicional: el worker ya no es de otra familia que el autor, por lo

> <!-- corpus-invariante:fin:cross-implement.reference.md.f0d5e0198799 -->
> que no rompe la correlación de errores.`

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

**Prechequeos** — los mismos de `cross-review/reference.md` → "Descubrir el revisor" →
"Prechequeos" (versión del CLI, no pinear `-m`, eco del modelo activo), registrando el modelo en
el `implement-log.md`.

> **Vía A (subagente `codex:codex-rescue`) no aplica acá**: el contrato de ese runtime corre
> read-only para pedidos de review/diagnosis. Para implementar se usa el CLI directo (Vía W-B).

Sin CLI para el implementador seleccionado → `UNAVAILABLE` (regla 7 del `SKILL.md`).

## Vías de invocación

Tres reglas invariantes (además de las del `SKILL.md`):

1. **Escritura acotada por construcción, nunca por confianza**: sandbox `workspace-write` en
   Codex, permisos path-scoped en Claude. **Nunca** `--yolo` /
   `--dangerously-bypass-approvals-and-sandbox` / `--dangerously-skip-permissions` /
   `acceptEdits` sin scoping — ver la matriz de verificación: `acceptEdits` escribe fuera del
   working dir.
2. **Aislamiento fail-closed antes de lanzar**, con el preflight de la sede única:
   `cross-review/reference.md` → "Preflight de aislamiento (fail-closed)". Se ejecuta
   `preflight_aislamiento <familia>` para la familia del implementador seleccionado y **se ramifica
   sobre su código de salida**: distinto de 0 → `UNAVAILABLE`, y no se despacha.

   > **Acá pesa más que en una skill de revisión, no menos.** El sandbox `workspace-write` acota lo
   > que el implementador escribe **en disco dentro del working dir**, y no acota los efectos de una
   > tool MCP: un implementador con los MCP del entorno puede alcanzar una tool de ejecución y operar
   > **fuera** de ese borde, con el sandbox intacto. Este es el único worker del ecosistema con
   > permiso de escritura, así que un sandbox más laxo no ablanda el preflight — lo vuelve más
   > necesario. La degradación correcta es no tener implementador, no tener uno sin contener; para
   > `sdd-flow`, eso es el modo `cross` cayendo a `inline`.
3. El prompt va por **stdin desde archivo** (tool Write), igual que en las skills hermanas.

Las tres se mantienen en cada intento y reanudación: cambia la ejecución concreta, no qué se le exige.
El manifest de corrida registra la vía efectiva (esquema en `cross-review/reference.md` → "Manifest
de corrida"). Los comandos concretos aparecen en cada vía documentada debajo.

### Vía W-B — Codex implementador (autor Claude)

- **Lanzamiento** (sesión fresca; captura del thread id igual que la Vía B de cross-review). `$MODEL`
  y `$EFFORT` salen de la lectura previa del config — ver "Modelo y esfuerzo bajo aislamiento":
  <!-- despacho:inicio:ci-wb-posix:codex -->
  ```bash
  # Perfil del rol `implement`, familia `codex`, resuelto por la cadena de
  # `sdd-flow/reference.md` → "La cadena de resolución del perfil". La asignación va ACÁ y no en otra
  # sección: una región que toma sus valores de fuera no se puede ejercer sola, y el modo `--ac 8`
  # del verificador ejecuta cada región y lee su `argv`.
  MODEL="$PERFIL_MODEL"
  EFFORT="$PERFIL_EFFORT"
  # Escalón 4 por campo — la raíz del config personal, que "Modelo y esfuerzo bajo aislamiento" lee.
  [ -z "$MODEL" ]  && MODEL=$(read_root_key model)
  [ -z "$EFFORT" ] && EFFORT=$(read_root_key model_reasoning_effort)
  codex exec --ignore-user-config --disable hooks --disable apps --disable plugins \
    -s workspace-write -C <working_dir> --skip-git-repo-check --json \
    ${MODEL:+-m} ${MODEL:+"$MODEL"} ${EFFORT:+-c} ${EFFORT:+"model_reasoning_effort=$EFFORT"} \
    --output-last-message <scratch>/report.txt - < <scratch>/prompt.txt \
    > <scratch>/thread.jsonl 2> <scratch>/impl.err.txt
  grep -m1 -o '"thread_id":"[^"]*"' <scratch>/thread.jsonl | cut -d'"' -f4 > <scratch>/session.txt
  ```
  <!-- despacho:fin:ci-wb-posix -->
  En **PowerShell**:
  <!-- despacho:inicio:ci-wb-ps:codex -->
  ```powershell
  # Perfil del rol `implement`, familia `codex`, por la cadena de `sdd-flow/reference.md` →
  # "La cadena de resolución del perfil". La asignación va ACÁ: una región que toma sus valores de
  # fuera no se puede ejercer sola, y `--ac 8` ejecuta cada región y lee su `argv`.
  # Escalón 4 por campo: la raíz del config personal (Read-RootKey).
  $Model  = if ($PerfilModel)  { $PerfilModel }  else { Read-RootKey 'model' }
  $Effort = if ($PerfilEffort) { $PerfilEffort } else { Read-RootKey 'model_reasoning_effort' }
  $CodexArgs = @('exec','--ignore-user-config','--disable','hooks','--disable','apps',
                 '--disable','plugins','-s','workspace-write','-C','<working_dir>',
                 '--skip-git-repo-check','--json',
                 '--output-last-message','<scratch>\report.txt')
  if ($Model)  { $CodexArgs += @('-m', $Model) }
  if ($Effort) { $CodexArgs += @('-c', "model_reasoning_effort=$Effort") }
  $CodexArgs += '-'          # el posicional de stdin va ÚLTIMO, como en POSIX
  Get-Content -Raw <scratch>\prompt.txt |
    codex @CodexArgs > <scratch>\thread.jsonl 2> <scratch>\impl.err.txt
  (Select-String -Path <scratch>\thread.jsonl -Pattern '"thread_id":"([^"]+)"' |
    Select-Object -First 1).Matches.Groups[1].Value > <scratch>\session.txt
  ```
  <!-- despacho:fin:ci-wb-ps -->
- `-s workspace-write` limita las escrituras al `working_dir` **más `/tmp`** (por diseño del
  sandbox). Caveat: si el repo objetivo vive bajo `/tmp`, el borde efectivo es más laxo. Por eso la
  regla 3 del `SKILL.md` enuncia la superficie —salida durable y autoritativa— y no solo el
  mecanismo: `/tmp` sirve para scratch efímero y nunca para lo que el conductor deba leer.
- **Fix round** (resume del MISMO thread). **Tres** cosas que **no** se heredan del comando de
  lanzamiento y que hay que mirar antes de copiarlo (detalle en `cross-review/reference.md` →
  "Asimetría de flags entre `exec` y `exec resume`"):
  - el **override de sandbox es obligatorio**: el modo de la sesión original no es garantía al
    reanudar, y por eso va `-c sandbox_mode="workspace-write"` y no `-s`, que `resume` **rechaza**;
  - **`-C` tampoco existe en `resume`**: el working dir es el **cwd del proceso**. Lanzar el fix
    round desde otro directorio escribe en el repo equivocado **sin error**. Posicionarse antes.
  - **el aislamiento tampoco se hereda, y esta es la que más fácil se olvida**: la configuración se
    relee en **cada** invocación de `codex`, así que un resume sin los cuatro flags vuelve a levantar
    los MCP, hooks y plugins del usuario por más que el lanzamiento los haya apagado. `exec resume`
    **sí** los acepta —a diferencia de `-s` y `-C`—, así que van repetidos enteros. Lo mismo vale
    para `-m` / `model_reasoning_effort`: los recarga de `session-meta.json`, no de la sesión.
  <!-- despacho:inicio:ci-wb-resume:codex -->
  ```bash
  # Escalón 1 de la cadena de resolución del perfil
  # (`sdd-flow/reference.md` → "La cadena de resolución del perfil"): en una reanudación la autoridad es el perfil CONGELADO de la sesión, que reemplaza
  # `model` y `effort` juntos; no se consulta ni se valida `.specify/workers.yml`.
  SESSION_ID=$(cat <scratch>/session.txt)
  echo "resume → ${SESSION_ID:?vacío}"   # id vacío = sesión fresca silenciosa; cortar acá
  ( cd <working_dir> &&                  # `resume` no acepta -C: el working dir es el cwd
    codex exec resume "$SESSION_ID" --ignore-user-config \
      --disable hooks --disable apps --disable plugins \
      -c sandbox_mode="workspace-write" --skip-git-repo-check --json \
      ${MODEL:+-m} ${MODEL:+"$MODEL"} ${EFFORT:+-c} ${EFFORT:+"model_reasoning_effort=$EFFORT"} \
      --output-last-message <scratch>/report.txt - < <scratch>/fix-rN.txt ) \
    > <scratch>/thread-fix-rN.jsonl 2> <scratch>/impl.err.txt
  ```
  <!-- despacho:fin:ci-wb-resume -->
  El `cd` va en **subshell**: fuera de él cambiaría el cwd del conductor para todo lo que siga, y el
  siguiente comando —medir el baseline, leer el diff— operaría sobre el directorio equivocado sin
  error. Misma razón por la que la Vía W-C usa `( cd … )` y PowerShell usa `Push-Location`.
  En **PowerS
  <!-- despacho:inicio:ci-wb-resume-ps:codex -->
  ```powershell
  # Escalón 1 de la cadena de resolución del perfil
  # (`sdd-flow/reference.md` → "La cadena de resolución del perfil"): la autoridad es el perfil CONGELADO de la sesión —los dos campos juntos—; no se
  # consulta el archivo. $Model y $Effort se recargan de session-meta.json, que lo transporta.
  $SessionId = (Get-Content <scratch>\session.txt -Raw).Trim()
  if (-not $SessionId) { throw 'session id vacío: sería una sesión fresca silenciosa' }
  $ResumeArgs = @('exec','resume',$SessionId,'--ignore-user-config','--disable','hooks',
                  '--disable','apps','--disable','plugins',
                  '-c','sandbox_mode=workspace-write','--skip-git-repo-check','--json',
                  '--output-last-message','<scratch>\report.txt')
  if ($Model)  { $ResumeArgs += @('-m', $Model) }
  if ($Effort) { $ResumeArgs += @('-c', "model_reasoning_effort=$Effort") }
  $ResumeArgs += '-'         # el posicional de stdin va ÚLTIMO, como en POSIX
  Push-Location <working_dir>
  try {
    Get-Content -Raw <scratch>\fix-rN.txt |
      codex @ResumeArgs > <scratch>\thread-fix-rN.jsonl 2> <scratch>\impl.err.txt
  } finally { Pop-Location }
  ```
<!-- despacho:fin:ci-wb-resume-ps -->
  El `try/finally` no es cosmético: sin él, un throw del pipe deja al conductor parado en el working
  dir del worker, que es el mismo modo de falla que el subshell evita en POSIX.

#### Modelo y esfuerzo bajo aislamiento

`--ignore-user-config` descarta el config del usuario **entero**, y ahí viven `model` y
`model_reasoning_effort`. Cerrar el canal sin compensarlo cambia en silencio con qué modelo corre el
worker, que es un efecto que nadie pidió y que no se nota hasta comparar salidas.

El orden es: **leer del config → aislar → pasar explícito → ecoar lo resuelto**. Solo vale una
asignación **raíz** inequívoca del TOML (anterior a la primera cabecera de tabla, comillas dobles,
una sola ocurrencia).

```bash
CODEX_CFG="${CODEX_HOME:-$HOME/.codex}/config.toml"
ROOT=$(awk '/^[[:space:]]*\[/{exit} {print}' "$CODEX_CFG" 2>/dev/null)
read_root_key() {
  n=$(printf '%s\n' "$ROOT" | grep -cE "^$1[[:space:]]*=[[:space:]]*\"[^\"]*\"[[:space:]]*$")
  [ "$n" -eq 1 ] && printf '%s\n' "$ROOT" | sed -n "s/^$1[[:space:]]*=[[:space:]]*\"\([^\"]*\)\".*/\1/p"
}
MODEL=$(read_root_key model); EFFORT=$(read_root_key model_reasoning_effort)
```
```powershell
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
$Root = @()
foreach ($l in (Get-Content (Join-Path $CodexHome 'config.toml') -ErrorAction SilentlyContinue)) {
  if ($l -match '^\s*\[') { break }
  $Root += $l
}
function Read-RootKey([string]$K) {
  $m = @($Root | Where-Object { $_ -match "^$K\s*=\s*""[^""]*""\s*$" })
  if ($m.Count -eq 1) { $m[0] -replace "^$K\s*=\s*""([^""]*)""\s*$", '$1' }
}
$Model = Read-RootKey 'model'; $Effort = Read-RootKey 'model_reasoning_effort'
```

**Las dos variantes existen porque el efecto es el mismo en los dos shells.** Documentar solo el
lector POSIX deja a Windows con `$Model`/`$Effort` **sin asignar nunca**: los `if ($Model)` de las
recetas dan falso, no se pasa ningún flag y `--ignore-user-config` descarta modelo y esfuerzo en
silencio — exactamente el efecto que esta sección existe para evitar, y sin nada que lo señale.

**Reproducir el modelo del usuario no es "pinear".** El prechequeo que prohíbe pinear prohíbe que la
skill **elija** un modelo por su cuenta; preservar el que el aislamiento acaba de descartar es lo
contrario de elegir. **Fallback fijado:** si la lectura no es inequívoca, no se pasa el flag y se usa
el **default del CLI**, registrado como tal en el `implement-log.md`. No se aborta ni se fuerza un
modelo canónico.

Los dos valores se **persisten en disco**, no solo en variables del proceso: el resume puede correr
en otro proceso —o en otro turno— y ahí una variable de shell ya no existe. Van a
`<scratch>/session-meta.json`, hermano de `session.txt`, y **se recargan** antes de cada resume:

```bash
printf '{"model":"%s","effort":"%s"}\n' "$MODEL" "$EFFORT" > <scratch>/session-meta.json
# antes de cada resume:
MODEL=$(sed -n 's/.*"model":"\([^"]*\)".*/\1/p'  <scratch>/session-meta.json)
EFFORT=$(sed -n 's/.*"effort":"\([^"]*\)".*/\1/p' <scratch>/session-meta.json)
```
```powershell
@{model=$Model; effort=$Effort} | ConvertTo-Json | Set-Content <scratch>\session-meta.json
# antes de cada resume:
$m = Get-Content <scratch>\session-meta.json | ConvertFrom-Json
$Model = $m.model; $Effort = $m.effort
```

Sin esto, la afirmación "se persisten" es falsa y el fix round corre con el default del CLI sin que
nada lo señale — que es exactamente el efecto silencioso que el aislamiento vino a evitar.

### Vía W-C — Claude implementador (autor GPT/Codex)

La forma canónica acota la escritura con **permisos path-scoped** — `--permission-mode default`
deniega en headless toda tool fuera de `--allowedTools`, y las reglas `Edit(./**)`/`Write(./**)`
limitan la escritura al working dir:

- **Lanzamiento** (sesión fresca, con session id propio para el resume):
  <!-- despacho:inicio:ci-wc-lanzamiento:claude -->
  ```bash
  SESSION_ID=$(uuidgen)   # Git Bash en Windows: ver "Portabilidad" de cross-review
  # Perfil del rol `implement`, familia `claude`, resuelto por la cadena de
  # `sdd-flow/reference.md` → "La cadena de resolución del perfil". Escalón 4 por campo: `sonnet`,
  # el modelo cableado de esta ruta de implementación, y ningún flag de esfuerzo.
  MODEL="${PERFIL_MODEL:-sonnet}"
  EFFORT="$PERFIL_EFFORT"
  set -- -p --safe-mode --model "$MODEL" --permission-mode default \
         '--allowedTools=Read,Grep,Glob,Edit(./**),Write(./**),Bash(<proof_bin>:*)' \
         --session-id "$SESSION_ID"
  [ -n "$EFFORT" ] && set -- "$@" --effort "$EFFORT"
  ( cd <working_dir> && claude "$@" \
      < <scratch>/prompt.txt ) > <scratch>/report.txt 2> <scratch>/impl.err.txt
  echo "$SESSION_ID" > <scratch>/session.txt
  ```
  <!-- despacho:fin:ci-wc-lanzamiento -->
  En **PowerShell** (mismo patrón `Start-Process`/pipe que la Vía C de cross-review, con estas
  tools; entrecomillar el `--allowedTools=…` completo para que las comas no se parseen como array).
- **`Bash(<proof_bin>:*)`**: derivar un patrón por **cada comando** de la lista `proof_cmd`, del
  primer token de cada uno (p. ej. `["node check.js", "npm run lint"]` → `Bash(node:*)` y
  `Bash(npm:*)`). La lista mínima que el contrato necesita, nunca `Bash` a secas.

  **Cuál es la forma admitida, y qué pasa si un comando no la tiene.** Un elemento es
  representable cuando es un comando
  simple con su ejecutable en el **primer token**. Un comando compuesto (`cd app && npm run lint`),
  con wrapper o con asignaciones de entorno delante **no** es representable: su ejecutable real no
  está en el primer token, y autorizar solo ese token bloquea la comprobación. Ante una forma no
  representable **se detiene el dispatch** y se arregla el comando — nunca se relaja a `Bash` entero
  para acomodarlo, que es cambiar el mínimo privilegio por comodidad.

  **Con la lista vacía no se emite ningún `Bash(...)`**, y `--allowedTools` queda en
  `'Read,Grep,Glob,Edit(./**),Write(./**)'`. No hay comprobación que correr, así que autorizar un
  binario "por las dudas" sería conceder ejecución sin nadie que la pida. Es el caso coherente con
  la ranura `PROOF` que tampoco se emite.
- **NUNCA `--permission-mode acceptEdits`** como forma canónica: verificado que escribe **fuera**
  del working dir sin restricción (ver matriz). Tampoco `--dangerously-skip-permissions`.
- Las reglas `Edit(./**)`/`Write(./**)` son relativas al cwd: por eso el `cd <working_dir>`
  previo (o `Push-Location`) es parte del contrato, no cosmético.
- **Modelo**: default `sonnet` para implementación (velocidad; la calidad la garantiza e
  <!-- despacho:inicio:ci-wc-fix:claude -->
# Resuelto por la cadena de `sdd-flow/reference.md` → "La cadena de resolución del perfil".
  ```bash
  # Reanudación: la autoridad es el perfil CONGELADO de la sesión (escalón 1), que reemplaza los dos
  # campos juntos; no se consulta el archivo. Escalón 4: `sonnet` cableado y ningún flag.
  MODEL="${PERFIL_CONGELADO_MODEL:-sonnet}"
  EFFORT="$PERFIL_CONGELADO_EFFORT"
  set -- -p --safe-mode --model "$MODEL" --permission-mode default \
         '--allowedTools=Read,Grep,Glob,Edit(./**),Write(./**),Bash(<proof_bin>:*)' \
         --resume "$SESSION_ID"
  [ -n "$EFFORT" ] && set -- "$@" --effort "$EFFORT"
  ( cd <working_dir> && claude "$@" \
      < <scratch>/fix-rN.txt ) > <scratch>/report.txt 2> <scratch>/impl.err.txt
  ```
<!-- despacho:fin:ci-wc-fix -->
- Con conductor de exec corto (Codex ~120s): lanzar en background y pollear el `report.txt`
  buscando `STATUS: done` — mismo patrón BACKGROUND de `cross-review/reference.md` → "Latencia
  y timeout (Claude revisor)", con el deadline de esta skill.

## Matriz de verificación

Verificado end-to-end el 2026-07-09 (codex-cli 0.143.0; Claude Code local, `claude -p`):

| Prueba | Resultado |
|---|---|
| Codex `exec -s workspace-write`: implementa fix real, proof en verde, thread id capturado vía `--json` | OK |
| Codex workspace-write, borde (cwd fuera de `/tmp`): escribe adentro / deniega afuera | INSIDE OK · ESCAPE DENIED |
| Codex workspace-write con cwd bajo `/tmp`: `/tmp` entero es escribible (diseño del sandbox) | caveat documentado |
| Codex resume sin flag (config sin `sandbox_mode`): se comportó como la sesión original | OK pero **no garantizado** → override siempre |
| Codex resume + `-c sandbox_mode="workspace-write"` (fix round canónico) | escribe OK |
| Codex resume + `-c sandbox_mode="read-only"` (dirección restrictiva) | deniega OK |
| Claude `-p --permission-mode acceptEdits`: implementa, pero **escribe fuera del cwd** | descartada como forma canónica |
| Claude `-p --permission-mode default` + `Edit(./**),Write(./**),Bash(node:*)` (fresh): escribe adentro / deniega afuera / proof OK | OK |
| Ídem con `--resume` (fix round) | FIX OK · ESCAPE DENIED |
| Ambas vías lanzadas en background con redirección + poll | OK |

Flags pueden variar por versión: ante la duda, `codex exec --help` / `claude --help`.

## Prompt del implementador

Contrato completo — el implementador arranca sin contexto de sesión; lo que no esté acá no
existe para él. Escrito a archivo con Write:


El prompt vive en `assets/prompts/implement.md` — es la **entrada exacta** del worker y se escribe a archivo con la tool Write.


Cuando el work order es SDD (`.plans/<id>/`), de dónde sale cada ranura lo fija la tabla de
"Derivación acotada por ranura", más abajo. Acá no se repite: era una segunda enumeración del mismo
hecho, y quedó con alcance distinto en cuanto la tabla se endureció.

**Render de la ranura `PROOF`:** **una línea por comando**, en el orden de la lista, y cada comando
va literal y entero, sin abreviar ni resumir: el worker no puede reconstruir uno truncado, y un comando
a medias falla de un modo que parece un defecto del código.

Con la **lista vacía** la ranura **no se emite** —ni el encabezado—, en vez de emitirse con un
hueco: una ranura presente y vacía le dice al worker que se esperaba algo que no llegó, y eso es
peor que no pedir nada. **Y arrastra a todo lo que la referencia:** con la lista vacía tampoco se
emiten las dos cláusulas de `CONSTRAINTS` que hablan de los comandos de PROOF, ni el bloque `PROOF`
del reporte — quedarían apuntando a una ranura ausente, que es el mismo defecto con otra forma. La
línea de **canales heredados** de `CONSTRAINTS` sí se emite siempre: no depende de que haya
comandos, y es la que cierra la superficie de escritura.

### Alcance escrito del implementador

Todo lo de esta sección rige **si y solo si el asset instalado declara el marcador
`SCOPE-CAPABILITY: v1`** en su cabecera. Sin ese marcador la ranura `SCOPE` no existe, y un prompt
que no la emite no puede quedar gobernado por reglas que hablan de ella.

El prompt es la entrada exacta del worker, y hasta este cambio su **alcance ejecutable** no viajaba:
llegaba como una lista de identificadores más la orden de leer un directorio. Con `SCOPE`, el alcance
viaja **escrito**, con sus referencias declaradas ya resueltas, y leer el work order deja de ser
precondición para empezar.

#### Clasificación: cuándo se emite `SCOPE`

El predicado es **observable, con precedencia declarada, y su resultado es ternario**. Las cuatro
señales se evalúan **en este orden**, y el orden es parte de la regla:

| Orden | Señal | Resultado |
|---|---|---|
| 1 | ¿el portador **declara un flujo SDD**? — una ruta `.plans/<id>/`, o un directorio con `plan.md` | si **no** declara: **(a) contrato directo**, y ahí termina |
| 2 | ¿el `plan.md` existe, se lee, y su header trae `complexity` válida? | si falta, no se interpreta, o el valor cae fuera del enum: **(c) bloquea** |
| 3 | fuente autoritativa: con `normal` o `complex`, el `tasks.md` hermano; con `trivial`, la sección `## Tasks` del plan | ausente o ilegible: **(c) bloquea** |
| 4 | contar encabezados de task en la fuente elegida | cero: **(c) bloquea** nombrando la fuente; uno o más: **(b)** |

**(a) queda reservado a portadores que no declaran flujo** — un plan suelto, un contrato destilado, el
plan draft que por escrito no tiene header. **Un flujo declarado y roto nunca cae en (a):** degradarlo
a contrato directo convertiría un error en un despacho silencioso con el prompt equivocado, que es
exactamente lo que la rama (c) existe para impedir.

**Cómo se lee el header, y hasta dónde.** Como lo lee la función `leer_header` de
`sdd-flow/scripts/promocion-tasks-ready.py`, y **solo ese subconjunto**: delimitadores de apertura y
cierre, unicidad de la clave, y enum cerrado de `complexity`. El resto de ese script —`status`,
`contract_procedure`, bitácora, estado de promoción— **no se aplica acá**: es el gate de promoción, y
arrastrarlo al clasificador bloquearía flujos válidos por precondiciones que este criterio no pide.

#### Diagnósticos, literales

| Rama | Texto |
|---|---|
| (c) fuente ausente o ilegible | `fuente de tasks esperada y ausente o no interpretable: <ruta>` |
| alcance seleccionado vacío | `no hay trabajo que delegar: cero tasks pendientes` |
| referencia que no resuelve a exactamente una fuente | `no resuelve a exactamente una fuente: <clase> <id>` |
| (a) contrato directo | **no emite diagnóstico**: no es un error |

**Y los de la precondición de capacidad**, que emite la skill que despacha cuando el asset instalado
no soporta la ranura. La comprobación es de ella —es la que decide si ofrece los modos delegados—
pero la estructura que comprueba es de acá, así que los textos viven acá y esa skill los referencia:

| Qué falta en el asset | Texto |
|---|---|
| el marcador | `capacidad ausente: el asset instalado no declara SCOPE-CAPABILITY: v1` |
| el conjunto de ranuras no es el esperado | `capacidad incompleta: el conjunto de ranuras del asset no es el esperado` |
| una de las cinco marcas de la ranura | `capacidad incompleta: falta la marca <MARCA> en la ranura SCOPE` |
| el terminador de la ranura | `capacidad incompleta: falta el terminador de la ranura SCOPE` |

**Se lee todo en una sola pasada.** Comprobar solo el marcador dejaría pasar un asset **a medias**
—marcador presente y ranura incompleta—, que es justamente el estado que la publicación atómica del
asset existe para que nadie vea.

**Contra qué se comprueba, y por qué se escribe acá.** Los cuatro diagnósticos exigen nombrar **qué**
falta, y eso obliga a que la estructura esperada exista **fuera del artefacto que se valida**. Sin
esta enumeración, la precondición compara el asset consigo mismo: prueba consistencia interna y no
conformidad, un `--- TASKZ ---` cuenta cinco marcas y pasa, y `falta la marca <MARCA>` no tiene de
dónde sacar el nombre. Que haya dos representaciones es deliberado y es lo que vuelve comparable la
comprobación, el mismo recurso que el repositorio usa para la banda del techo y el dominio de
generados.

| Qué | Valor esperado | Se compara como |
|---|---|---|
| conjunto de ranuras | `GOAL` · `SPEC` · `SCOPE` · `KEY PATHS` · `CONSTRAINTS` · `NON-GOALS` · `PROOF` · `OUTPUT` | **conjunto**, no secuencia |
| marcas de la ranura `SCOPE` | `--- TASKS ---` · `--- CRITERIOS ---` · `--- VERIFIC ---` · `--- INTERFACES ---` · `--- CLAUSULA ---` | secuencia, en ese orden |
| terminador de la ranura | `--- FIN ---` | presencia |
| marcador de capacidad | `SCOPE-CAPABILITY: v1`, indentado dentro del comentario de cabecera | presencia |

**El extractor de ranuras, completo: patrón, frontera y deduplicación.** Los tres, porque el patrón
solo no alcanza y su ausencia no falla en silencio: falla **cerrando sobre el asset correcto**.

1. **Patrón.** Una ranura es una línea que case `^[A-Z][A-Z -]*:`; su nombre es lo que precede a los
   dos puntos.
2. **Frontera.** La enumeración **termina en `OUTPUT`**, inclusive. Lo que sigue es el **cuerpo del
   reporte**, no ranuras: `FILES`, `PROOF`, `DEVIATIONS` y `STATUS` casan el patrón y están a columna
   cero **por obligación del propio asset** —el reporte se busca anclado al margen y `STATUS: done`
   es su última línea—, así que indentarlos rompería la cosecha y **no se los puede sacar del alcance
   del patrón moviéndolos**. Sin esta frontera la extracción devuelve **once** nombres contra los
   ocho declarados, la precondición de capacidad rechaza un asset sano y los modos delegados quedan
   apagados sobre un árbol correcto.
3. **Deduplicación.** El resultado se compara **como conjunto**: `SPEC` aparece dos veces —sus dos
   ramas excluyentes— y `PROOF` una por comando, así que en crudo son **catorce** entradas para ocho
   ranuras. Un comparador de secuencias falla aun con la frontera puesta.

Y de la misma causa se sigue dónde va el marcador de capacidad: **indentado** dentro del comentario
de cabecera, porque a columna cero casaría el patrón, caería antes de la frontera y entraría al
conjunto como una novena ranura.

#### Gramática de identificadores y de encabezados

- **Identificador de task:** el árbol admite `T2`, `T16b` y `T15A`, con o sin backticks. Un
  reconocedor de `Tn` a secas rechaza referencias válidas que ya existen.
- **Encabezado de task:** las **dos** formas normativas, la compacta de un flujo trivial y la
  completa. En la compacta, `cubre` viaja **inline** y se parsea de ahí.

#### Tabla cerrada de resolución

Cada pieza tiene **una** fuente autoritativa, un patrón de apertura y una frontera. Fuera de esta
tabla no se resuelve nada: lo que no encaje **bloquea**, y no se repara con patrones tolerantes.

| Pieza | Fuente autoritativa | Apertura | Frontera |
|---|---|---|---|
| task | la fuente elegida por la clasificación | las dos formas de encabezado | siguiente encabezado de task o de sección |
| criterio | la `spec.md`, o la sección `## Spec` del plan en `trivial` | su ítem definitorio `AC-n` | siguiente ítem `AC-` o encabezado, con sus continuaciones indentadas |
| fila | la versión **vigente** de `## Verification`, la de número mayor | la fila cuyo identificador coincide | la fila entera, con sus seis columnas |
| productor | la task que declara `Produce` | el encabezado de esa task | su línea `Produce` |
| sección compartida | el bloque global que el `Consume` nombra | su encabezado | el siguiente encabezado de igual o menor nivel |

#### Cierre de referencias

La **raíz** son las tasks del alcance, verbatim y **con sus referencias conservadas**. A eso se
**adjunta** el payload resuelto de cada una. Conservar la referencia y adjuntar su contenido son las
dos cosas, no una en lugar de la otra: el identificador es lo que ata la pieza a su fuente.

Las cuatro clases de hoja —criterio, fila, productor, sección compartida— son **terminales**. Un
`Consume` estructurado dentro de una sección compartida **bloquea nombrando la pieza** en vez de
abrir otro nivel. Una fila citada por dos tasks del alcance viaja **una sola vez**.

#### Cardinalidad

Toda referencia requerida resuelve a **exactamente una** fuente autoritativa. Cero coincidencias, más
de una, o una estructura que no se puede interpretar **bloquean la invocación** nombrando la pieza que
falló, con el texto de la tabla de diagnósticos. Está prohibido omitir la pieza, elegir una de varias,
reinterpretarla, o volver al work order como sustituto.

**Una línea copiada que colisione con la gramática de secciones también bloquea.** Es el mismo caso:
si un extent contiene una línea que abre o cierra una sección de la ranura, el prompt resultante es
correcto en bytes e imposible de verificar, así que se trata como estructura no interpretable.

#### Derivación acotada por ranura

Cada ranura tiene **una** fuente permitida. La tabla es cerrada —cubre **las ocho** ranuras que el
asset emite— y su función es impedir que el armazón del prompt se use para readjuntar el corpus que
la ranura acota. Es la **sede única** de la derivación por ranura: no hay una segunda enumeración en
este documento, porque dos enunciados del mismo hecho se desincronizan en cuanto alguien edita uno.

| Ranura | Fuente permitida |
|---|---|
| `GOAL` | el objetivo de la spec, sin la spec |
| `SPEC` | en la rama (a), el work order y los identificadores del alcance —portador, tasks incluidas y excluidas—; en la rama (b), texto fijo, sin derivación. Las dos ramas son excluyentes |
| `SCOPE` | las tasks del alcance más sus referencias transitivas declaradas |
| `KEY PATHS` | **únicamente** los campos `Archivos` de las tasks **incluidas**. Sin excepción de reúso: si una task necesita señalar reúso, lo declara en su campo `Archivos` y viaja por ahí |
| `CONSTRAINTS` | restricciones vigentes aplicables, sin narrativa de decisiones |
| `NON-GOALS` | no-objetivos concretos, sin criterios que ninguna task del alcance cita |
| `PROOF` | solo los comandos recibidos, y **el conjunto entero** —tests, build y lint, los que estén configurados—, no solo el de tests |
| `OUTPUT` | el asset literal |

Y la cláusula normativa de la ranura declara que **ante discrepancia manda `SCOPE`**.

#### Secuencia de composición, y por qué existe el candidato

Dentro del **mismo intento**, en este orden:

1. validar la selección según el camino;
2. extraer los extents lógicos exactos, **incluyendo la representación del checkbox**;
3. capturar su huella;
4. componer y escribir un **candidato temporal**;
5. volver a extraer y comparar contra la huella;
6. **solo si coincide**, promover el candidato a `prompt.txt`;
7. lanzar.

**El candidato es lo que evita un congelado obsoleto.** Escribir `prompt.txt` antes de recomprobar
deja, ante un bloqueo, un prompt nunca lanzado que la regla de congelamiento obliga a reutilizar y
prohíbe corregir. El candidato se **descarta** al fallar, y no deja rastro que otro intento tenga que
respetar.

#### Precondiciones por camino, y el snapshot

| Camino | Qué se revalida antes de componer |
|---|---|
| con partición aprobada | el recibo, su fingerprint y el orden de los bloques restantes |
| sin partición aprobada | la selección de tasks pendientes contra su fuente vigente |

En los dos casos se toma un **snapshot local único** de las **fuentes lógicas efectivamente
presentes** —el enunciado de los criterios, el contrato de verificación y las tasks— inmediatamente
después de validar, y se comprueba que ninguna cambió hasta escribir y lanzar el prompt. Cualquier
discrepancia bloquea.

Son fuentes **lógicas y no archivos**: en un flujo trivial las tres viven en un solo documento, y
exigir tres archivos ahí bloquearía un caso válido.

**No se reutiliza el fingerprint del recibo**, por dos razones independientes: normaliza el checkbox
—y sin partición el checkbox **es** la selección—, y no existe cuando no hay recibo aprobado. El
snapshot es **local al intento** y no amplía el esquema del recibo.

**Diagnósticos literales de esta sede:**

| Situación | Texto |
|---|---|
| una fuente cambió entre la captura y el lanzamiento | `snapshot invalidado: <ruta> cambió entre la captura y el lanzamiento` |
| la revalidación del recibo no cierra | `precondición de recibo fallida: <campo> no coincide con el recibo aprobado` |

**Riesgo residual, declarado.** Entre la recomprobación y el lanzamiento queda una ventana que, sin un
lock que cubra comparación, promoción y lanzamiento, no se cierra. Se declara en vez de negarla con un
«cualquier diferencia bloquea» que no se sostiene ante una escritura concurrente no cooperativa.

#### Alcance vacío

Una fuente de tasks válida cuyo alcance seleccionado resulta **vacío** —cero tasks que despachar—
**no compone ningún prompt y no crea invocación**, con su diagnóstico propio. Es un resultado distinto
del contrato directo y del bloqueo por fuente ausente, y los tres se distinguen en el diagnóstico.

#### Ciclo de vida del prompt

El congelamiento aplica **solo con evidencia de que la invocación se lanzó**. Con esa evidencia, las
rondas de corrección reutilizan ese prompt y **reescribirlo está prohibido**. Sin ella, el intento
siguiente es un intento nuevo, no una retoma.

| Situación | Qué se usa |
|---|---|
| invocación anterior a este cambio | su contrato original, sin la ranura |
| retoma de una invocación lanzada | el prompt congelado de esa invocación |
| redespacho posterior | identificador nuevo, y se compone con las fuentes vigentes |

#### El portador del camino monolítico

Sin partición aprobada no hay bloque, y el prompt exige tres campos. Se fijan **sin tocar la
proyección al ledger**:

| Campo | Valor |
|---|---|
| identidad | la etiqueta literal `alcance monolítico` |
| `included_tasks` | las pendientes de la fuente vigente |
| `excluded_tasks` | las ya completadas, enumeradas por identificador igual que en el camino con partición |

Son campos **del prompt, no del ledger**: fijarlos no crea ningún artefacto durable que el recibo o el
contrato de recuperación tuvieran que observar.

## Handoff destilado, nunca transcript crudo

Al modelo delegado se le pasa un **contrato destilado** —objetivo, contexto necesario, límites—,
nunca el transcript literal de la sesión del conductor. El prompt por archivo que esta skill usa
destila el contexto, pero **no destilaba el alcance ejecutable**: hasta la ranura `SCOPE`
viajaba como una lista de identificadores. Que ahora destile las dos cosas no es una convención
estética, es la forma correcta, y conviene
saber por qué para que nadie la "optimice" pasándole contexto ambiente al delegado.

El porqué no es solo de diseño. Está documentado un caso real donde reproducir dentro de un modelo
un transcript construido bajo otro activó clasificadores de política de uso y **bloqueó todas las
requests de la sesión** —incluso las triviales—, mientras la misma consulta en una sesión fresca
pasaba sin problema. El diseño barato resultó ser también el seguro.

Consecuencia práctica: si el delegado necesita saber algo, ese algo se **escribe en el prompt**. No
se le reenvía la conversación para que lo deduzca.

## Formato del reporte

**El bloque literal vive en `assets/prompts/implement.md`, ranura `OUTPUT`, y esa es su única
sede.** Acá va lo que el conductor **consume**, no una segunda copia: el worker solo ve el prompt,
así que una transcripción de este lado no gobierna nada y diverge sin que nada la ponga roja —
ya divergió una vez, en el texto del placeholder del comando.

Lo que el conductor puede dar por contratado:

- **`STATUS: done` en la columna 0** es la señal de fin del poll en background, y el prompt pide el
  reporte sin sangría justamente porque el predicado está anclado al margen. Un reporte indentado
  haría que el conductor matara por deadline a un worker que ya cerró.
- **Un bloque `COMMAND` / `EXIT_CODE` / `OUTPUT` por comando**, en el mismo orden en que se pidieron
  — es lo que vuelve comparable la medición de base contra el resultado del bloque.
- Reporte no parseable → el diff sigue siendo la verdad (regla 4): revisarlo igual; se pierde solo
  la narrativa.

## Medición de base y adjudicación

La aceptación de un bloque se juzga por **no empeoró**, no por verde absoluto (`SKILL.md` →
"Aceptación de un bloque"). Eso exige saber qué daba cada comando **antes**, y ese "antes" deja de
existir en cuanto el implementador escribe: la medición va **antes del dispatch**, no después.

Orden, y cada paso está donde está por una razón:

1. **Normalizar y validar** la lista de `proof_cmd`: escalar → lista de un elemento; rechazar toda
   forma no representable (ver "Vía W-C" → forma admitida).
2. **Resolver `block_base`** — el commit base **del bloque**, no el ancla de la secuencia. Con el
   ancla, un diagnóstico que introdujo el bloque N-1 se le atribuye al N. En un despacho monolítico
   coinciden; en una secuencia particionada, no.
3. **Medir cada comando por separado** en un **worktree** **detached** sobre `block_base`. Se reusa
   el ciclo de vida del re-baseline aislado de `ownership.md` → "Re-baseline en worktree aislado"
   (crear detached, ejecutar, remover, comprobar la desaparición) **sin editar ese bloque**. Lo que
   se agrega acá es la **captura**: aquel reduce el resultado a verde/rojo y borra la salida; esto
   conserva, por comando, **el comando exacto, su salida completa y su exit code**.

   > **Un worktree detached no trae el entorno, y sin él la medición miente en la dirección
   > peligrosa.** El bloque reusado se diseñó para **filas de contrato** —comprobaciones acotadas—,
   > pero `proof_cmd` es la suite completa, el build y el linter. Un worktree recién creado no tiene
   > `node_modules`, `.venv`, `target/` ni el equivalente del stack, así que en cualquier proyecto con
   > dependencias instaladas **todos** los comandos salen distinto de cero en la base. Y un baseline
   > todo en rojo hace que cualquier fallo posterior "no empeore": la condición de aceptación queda
   > satisfecha siempre, que es exactamente el fallo que no se nota.
   >
   > **Antes de medir, el worktree tiene que poder ejecutar el comando.** Lo barato y suficiente es
   > **compartir el directorio de dependencias** del árbol activo —que ya está instalado y ya
   > corresponde a este repo— en vez de reinstalarlo:
   >
   > ```sh
   > # ejemplo para Node; el equivalente según el stack (.venv, vendor/, target/…)
   > ln -s "$(git rev-parse --show-toplevel)/node_modules" "$WT/node_modules"
   > ```
   >
   > **Y hay una comprobación que no cuesta nada y caza el resto: si al medir la base salen rojos
   > TODOS los comandos, sospechar del entorno antes que de la deuda del repo.** Un repo con linter
   > rojo es común; uno donde además fallan la suite y el build a la vez es raro. Ante ese caso, la
   > base **no se da por válida**: se comprueba a mano un comando en el árbol activo —que está en
   > `block_base` y sí tiene entorno— y, si ahí pasa, el worktree es el problema.
   >
   > **Si un comando no se puede medir en la base, no se puede adjudicar por "no empeoró".** Ese
   > comando queda **fuera del criterio de aceptación** y se declara así en `proof-baseline.md`, con
   > el motivo. Contarlo como rojo es lo que produce la aceptación vacua; excluirlo es honesto y deja
   > el hueco a la vista. Lo que **no** cambia por eso es la tercera condición de la aceptación: las
   > filas del contrato se siguen exigiendo en verde, y no dependen de esta medición.
4. **Descartar el worktree** y comprobar que se fue. Correr los comandos sobre el árbol activo no es
   una alternativa: un linter con autofix o un build que deja artefactos ensucian el árbol justo
   antes de un despacho cuyo clean-tree gate exige lo contrario.
5. Recién entonces, el clean-tree gate y el dispatch.

**Dónde se guarda.** En `<scratch>/proof-baseline.md`, un artefacto por invocación, con una entrada
por comando: el comando exacto, su exit code y su salida completa, más el `block_base` sobre el que
se midió. Sin sede declarada, "conservar la salida" es una intención que nadie puede auditar después.

> **Ese archivo está al alcance del worker, y prohibírselo en el prompt no lo protege.** El scratch
> vive bajo el `working_dir`, que es justo lo que `-s workspace-write` concede; `session-meta.json`
> está en la misma situación. Sacarlos de ahí no resuelve nada —el sandbox concede `/tmp` también—,
> así que la garantía disponible no es prevención sino **detección**, y hay que decirlo con ese
> nombre: es la única superficie donde esta skill depende de que el worker obedezca.
>
> Los dos son **load-bearing y untracked**: `proof-baseline.md` es el "antes" contra el que se juzga
> `no empeoró`, `session-meta.json` fija con qué modelo corre cada resume, y una escritura del worker
> en cualquiera de los dos **no aparece en el diff**. Por eso, antes del dispatch se registra el
> `sha256` de ambos y se recomprueba **al cosechar, antes de leerlos**.
>
> **Dónde vive el testigo decide qué prueba, y es fácil escribirlo mal.** Si el `sha256` se guarda en
> el mismo `<scratch>`, queda en la superficie que vigila: un worker que reescriba `proof-baseline.md`
> reescribe el testigo en el mismo movimiento y la recomprobación pasa. Entonces:
>
> - **El testigo es el par de digests que el conductor acaba de calcular**, y los conserva **él**,
>   fuera de `working_dir`, junto al resto de su estado de la corrida. Contra eso se compara.
> - Si por reanudación entre sesiones hace falta una copia en disco dentro del scratch, esa copia
>   **degrada la garantía a detección de accidente**, no de manipulación, y hay que declararlo con ese
>   nombre en el log. No es lo mismo cazar un proceso que truncó un archivo que cazar a un worker que
>   decidió reescribirlo.
>
> ```bash
> # POSIX (`sha256sum` en Linux, `shasum -a 256` en macOS: elegir el que exista)
> # al despachar — el digest queda en el estado del conductor, NO bajo <scratch>:
> shasum -a 256 <scratch>/proof-baseline.md <scratch>/session-meta.json > <estado-conductor>/scratch.sha256
> # al cosechar, antes de leer el baseline o de reanudar:
> if ! shasum -a 256 -c <estado-conductor>/scratch.sha256 >/dev/null 2>&1; then
>   printf 'ENVIRONMENT_FAILURE: scratch alterado\n' >&2
>   exit 1
> fi
> ```
> ```powershell
> # al despachar:
> Get-FileHash <scratch>\proof-baseline.md, <scratch>\session-meta.json -Algorithm SHA256 |
>   Export-Csv <estado-conductor>\scratch.sha256 -NoTypeInformation
> # al cosechar, antes de leer el baseline o de reanudar:
> $alterado = $false
> foreach ($e in (Import-Csv <estado-conductor>\scratch.sha256)) {
>   if (-not (Test-Path $e.Path) -or (Get-FileHash $e.Path -Algorithm SHA256).Hash -ne $e.Hash) {
>     Write-Error "ENVIRONMENT_FAILURE: scratch alterado ($($e.Path))"; $alterado = $true
>   }
> }
> if ($alterado) { exit 1 }
> ```
>
> **El código de salida es la señal, y por eso el `|| echo` no sirve:** `echo` devuelve 0, así que
> `shasum -c … || echo …` **sale 0 ante un mismatch** y quien ramifique por exit code lee un scratch
> alterado como limpio. Las dos variantes cortan con `exit 1`. La de PowerShell comprueba además que
> el archivo exista, en vez de reventar por una ruta ausente.
>
> Un `sha256` que no cierra **no es un fallo de implementación**: es `ENVIRONMENT_FAILURE` —la
> comprobación no llegó a tener veredicto, porque el comparador perdió su base— y se clasifica con
> esa clase, sin inventar una quinta (`ownership.md` → "Las cuatro clases"). **No consume ronda.**
>
> Las otras consecuencias de esa clase están indexadas por `checkId`, y acá no hay fila: la unidad de
> identidad de un agregado es **el string exacto del comando**, como en el resto de esta sección. Los
> dos intentos de reparación se cargan a esa unidad, y la reparación es distinta para cada archivo:
> `proof-baseline.md` se regenera volviendo a medir sobre `block_base`, que sigue disponible porque
> es un commit; `session-meta.json` **no se repara midiendo** — se reescribe releyendo modelo y
> esfuerzo del config, que es de donde salieron. Agotados los dos intentos, ese comando **queda fuera
> del criterio de aceptación** —la misma salida que un comando que no se pudo medir en la base— y se
> declara con su motivo. Las filas del contrato no se ven afectadas: son la tercera condición de la
> aceptación y no dependen de esta medición.

Tras la ronda, se repiten los mismos comandos sobre el árbol con el delta y se compara contra ese
archivo.

**Comparar exige un comparador, y no siempre hay uno.** Los elementos de `proof_cmd` son **opacos**:
dos corridas pueden devolver el mismo exit code distinto de cero con más diagnósticos, y comparar la
salida literal no es fiable (timestamps, rutas, orden no determinista). Entonces:

| Situación | Qué se hace |
|---|---|
| el comando tiene un **comparador** explícito y auditable (p. ej. un conteo de diagnósticos que él mismo reporta) | se compara y se registra el resultado como medición, con el comparador usado |
| no hay comparador representable | **adjudicación humana**: el conductor muestra el estado de la base y el del bloque, y el humano decide. Se registra **como decisión, no como medición**, con la evidencia de base, la del bloque y quién decidió |

Nunca se afirma "no empeoró" sobre una comparación que nadie puede hacer. Y no se detiene el
dispatch por esto: un repo con deuda preexistente es el caso común, y es donde más se delega.

> **No hay sede para transportar comparadores reutilizables**, y es deliberado: el contrato de
> invocación no tiene dónde, y convertir la lista en objetos `{comando, comparador}` dejaría de ser
> una lista de comandos opacos. Si alguna vez hace falta, es un cambio de contrato con su propio
> gate, no una clave agregada de paso.

## Revisión del conductor

Checklist tras cada ronda (regla 4 del `SKILL.md`) — como PR de un contribuidor externo:

1. **FILES vs realidad**: contrastar lo declarado contra `git status --porcelain`. Archivos
   tocados no declarados o declarados no tocados → sospecha, va al fix round.
2. **Diff completo** (`git diff`): correctitud, fidelidad al work order, estilo del repo,
   nada fuera de alcance. **Drift** (hunks que no mapean al work order) → pedir reversión en el
   fix round o declararlo explícitamente (en SDD: `## Extras` de sdd-flow).
3. **Prueba propia**: correr **cada comando** de `proof_cmd` fresco —todos, no solo el primero— y
   leer salida completa y exit code de cada uno. La del reporte no cuenta. Comparar cada resultado
   contra su medición de base: la condición es **no empeoró**, no verde
   (ver "Medición de base y adjudicación").
4. **En SDD**: atribuir hunks a tasks y marcar `- [x]` solo las efectivamente cubiertas; los AC
   los verifica después el `verify` de sdd-flow (esta revisión no lo reemplaza).
5. Registrar el veredicto de la ronda en el log (qué pasó, qué va al fix round).

## Cuándo un reporte ilegible no invalida la revisión

El principio: **un reporte que no parsea no invalida la revisión**. Se revisa el artefacto igual y lo
único que se pierde es la narrativa del implementador.

**Condición de aplicación — el principio es falso sin ella:** vale donde el **artefacto es el diff**,
no donde el artefacto **es** el informe.

- Acá el entregable es el diff; el reporte solo lo describe. Si el reporte no parsea, el diff sigue
  estando y se revisa igual: leerlo no depende del formato del texto que lo acompaña.
- En `co-explore` el entregable **es** el informe. Uno que no parsea no deja nada que revisar, y por
  eso esa skill exige informe estructurado o nada: degrada a texto libre si aporta contexto, o
  descarta, y registra la degradación.

Enunciarlo como principio general **sin** su condición contradiría de frente esa regla no negociable,
y dejaría a quien lea las dos eligiendo cuál desobedecer.

La prueba de si aplica es una sola pregunta: **si borro el reporte, ¿queda algo que revisar?** Si sí,
el principio aplica. Si no, el reporte era el artefacto y su formato no es narrativa: es el
entregable.

## Fix loop

> **El delta de fix no tiene asset propio.** No es un prompt con estructura fija sino el contenido
> mínimo de abajo, distinto en cada ronda; congelarlo en una plantilla invitaría a rellenarla en vez
> de escribir lo que esa ronda necesita.

- El delta de cada ronda es concreto: **qué está mal · en qué archivo · qué prueba debe pasar** —
  no re-mandar el work order completo (la sesión lo recuerda).
- Reanudar la MISMA sesión por la vía que corresponda (comandos arriba; en Codex, el override
  `-c sandbox_mode="workspace-write"` es obligatorio; guard de id vacío siempre).
- Tope `max_fix_rounds` (default 2) → **takeover**: el conductor termina directamente, registrado
  en el log con qué quedó de cada lado (`PARTIAL`).
- En modo embebido sdd-flow, su tope de diseño manda: 3 fallos de la MISMA falla (aunque queden
  fix rounds) = problema de diseño → volver a `plan`/`specify`, no seguir delegando.

### El delta revisable de un bloque

La revisión del bloque compara su **commit base del bloque** contra el estado conjunto del index y
el working tree. Para los paths trackeados, el comando base es `git diff "$block_base" --
<pathspec...>`: incluye staged y unstaged respecto de ese commit y no es un rango entre dos commits,
porque el commit de trabajo del bloque todavía no existe.

`git diff` no incorpora archivos untracked. El conductor obtiene su lista con `git status
--porcelain` y `git ls-files --others --exclude-standard -- <pathspec...>`, y revisa además el
contenido completo de cada archivo listado. El conjunto resultante debe coincidir exactamente con el
mismo set `code_dirty` que clasifica `sdd-flow`: excluye `.plans/`, `.specify/` y los
generados reconocidos por el repo. Una diferencia entre ambos conjuntos detiene la aceptación.

### Secuencia Git entre bloques

Antes del primer dispatch, el conductor fija el ancla con `anchor=$(git rev-parse HEAD)` y conserva
ese SHA en el recibo. Cada commit de trabajo lleva los trailers `Cross-Implement-Block: <block_id>` y
`Cross-Implement-Receipt: <fingerprint>`. Para distinguir sus commits de trabajo de commits ajenos,
ejecuta `git rev-list --reverse "$anchor..HEAD"` y, por cada SHA, `git log -1
--format='%(trailers:key=Cross-Implement-Block,valueonly)' <sha>`; un commit sin marca o con una
identidad ajena detiene la secuencia.

El staging se reconstruye para cada bloque con pathspec explícito: `git add -- <pathspec...>`. Antes
del commit, `git diff --cached --name-only` debe coincidir con los paths aceptados del delta; nada que
estuviera staged previamente entra por arrastre. Si un hook falla, el conductor muestra el error y se
detiene sin `--no-verify`. Si un hook modifica el árbol, invalida el delta revisado: se vuelve a
clasificar y revisar el cambio antes de decidir si el bloque todavía puede aceptarse.

Antes de reset, aplastado o rollback, cada SHA marcado se consulta con `git branch -r --contains
<sha>`. Si algún commit de trabajo aparece en un upstream, la guarda detiene sin reescribir la
historia; esos commits solo pueden aplastarse mientras sigan siendo locales.

### Orden de cierre de la secuencia

Esta skill consume el ledger y no lo produce. La autoridad de sus estados está en
`sdd-flow/reference.md` → `### La submáquina de cierre`, y su mecánica en
`sdd-flow/reference.md` → `### Escritura del ledger`. Si una caída interrumpe estas operaciones,
véase “Recuperación de la secuencia” en esa referencia: ahí viven diagnóstico, gate y reconciliación;
esta sección conserva únicamente la mecánica Git y no duplica el clasificador.

Tras aceptar el último bloque y confirmar el cese, el orden obligatorio es **delta acumulado →
verificación final → gate → commit final**. Primero se valida la cadena marcada y se ejecuta `git
reset --soft "$anchor"`; así el aplastado reconstruye en el index el delta acumulado de todos los
commits de trabajo. Los extremos del diff presentado son el ancla previa a los bloques y el index más
working tree resultante, inspeccionados con `git diff "$anchor"` y `git diff --cached "$anchor"` e
incluyendo por separado cualquier untracked aceptado.

Sobre ese delta se corre la verificación final. Después se presenta el mismo delta y la evidencia en
el gate humano, y solo tras su aprobación se crea el commit final de contenido. No se aplaza el
aplastado hasta después del gate: hacerlo dejaría el árbol limpio y mostraría un diff vacío al humano.

## Latencia, deadlines y banner

Una implementación tarda mucho más que una crítica: presupuestos por encima de cross-review.

| Contexto | Modo | Tope |
|---|---|---|
| Work order chico (≤ ~3 tasks), conductor con exec largo | sync (Bash `timeout: 600000`) | 10 min |
| Work order mediano/grande, o cualquier conductor | background + poll de `STATUS: done` en `report.txt` | deadline 1800 s (override conversacional) |
| Conductor de exec corto (Codex ~120s) | background + poll acotado (patrón de cross-review Vía C) | ídem |

- **Tope duro siempre**: al vencer sin `STATUS: done`, matar el proceso (`kill $PID` /
  `Stop-Process`), revisar el diff parcial (degradación 3 del `SKILL.md`) y devolver `UNAVAILABLE`.
  La **causa** de ese `UNAVAILABLE` es `deadline_exceeded`, no `runtime_failure`: el implementador
  arrancó bien y el corte lo puso el conductor al fijar el tope de esta tabla. La distinción no es
  cosmética — decide la palanca: ante `runtime_failure` se mira el error, ante `deadline_exceeded` se
  mira el presupuesto (y acá el override conversacional del deadline es justamente esa palanca).
  Enum completo de causas en `cross-review/reference.md` → "Latencia y timeout (Claude revisor)".
- **Banner al terminar un run en background** (obligatorio): la PRIMERA línea del siguiente
  mensaje al usuario es un aviso destacado — `🔔 Implementación cruzada terminada — <work order>
  (ok/fallo) — reviso el diff ahora` — antes de cualquier salida de verificación. El usuario no
  mira las tools; un build terminado nunca se desliza en silencio a la fase de revisión.
- No matar un run background silencioso antes del deadline: las implementaciones legítimamente
  tardan.

### `recovery-required` bloquea retry y fallback

Matar el proceso al vencer el deadline es lo que la tabla manda hacer; esta subsección dice qué pasa
cuando **no** se puede afirmar que quedó muerto.

Un intento cuyo resultado sobre el árbol es **incierto** —no se sabe qué quedó escrito ni si hay un
proceso que siga escribiéndolo— no queda en `UNAVAILABLE` ni en `PARTIAL`: queda en
`recovery-required`, que es estado del **intento**, no un resultado de la corrida. Mientras no se
resuelva **no habilita ni retry ni fallback**: ni una ronda de fix más, ni el despacho del mismo work
order por el otro transporte, ni un implementador nuevo sobre ese árbol.

**Vencer el deadline no prueba que el proceso dejó de trabajar.** No es una precaución teórica: se
observó lo contrario — una espera venció con los agentes todavía produciendo y entregaron **después**
de que la corrida ya se había degradado. El deadline de la tabla es el corte que el conductor se pone
a sí mismo, y `deadline_exceeded` registra esa decisión suya; ninguno de los dos prueba nada sobre el
proceso. Lo único que sirve como prueba es evidencia positiva de que ya no está vivo.

**Y acá las rutas de salida fijas no protegen nada, porque la salida no es una ruta.** Contra un
worker tardío que completa el archivo de una corrida ya degradada, dar a cada intento rutas exclusivas
alcanza; contra un implementador tardío no, porque lo que sigue tocando es el **working tree entero**.
Dos escritores sobre el mismo árbol dejan un diff que no es de ninguno de los dos y un estado del repo
que ninguno explica. Por eso el recovery acá es una pregunta concreta y contestable —qué quedó escrito,
y si hay algo que siga escribiéndolo—, y hasta contestarla no se despacha nada sobre ese árbol. El
contrato general que bloquea el relanzamiento mientras el proceso anterior pueda seguir escribiendo
vive en `skills/cross-review/corridas-en-vuelo.md` → "Invariantes de recuperación"; acá se aplica al
working tree y no se repite.

### Callback o poll: el segundo predicado, una vez en `background`

`execution` es un enum **cerrado de tres valores** (`auto | sync | background`) y el default de esta
skill es `auto`, tanto en modo embebido como directo. Los defaults de las tres skills cross-model
están en un solo lugar, sin copias: `co-explore/reference.md` → "Latencia y deadlines".

**Elegir `background` no dice cómo se espera.** Hacen falta **dos** predicados distintos, y el error
que hay que evitar es tratarlos como uno: que el conductor pueda fijar un timeout de exec largo **no
demuestra** que el host lo vuelva a invocar cuando el comando en background termina. La secuencia
completa, en este orden: `execution: auto` elige `sync` o `background` por el predicado de timeout de
exec y el tamaño del work order de la tabla de arriba —auto → sync con tope largo disponible y work
order chico, auto → background si no—; y **ya dentro de `background`**, un segundo predicado, el de
**re-invocación durable**, elige entre **callback** y el **poll de `STATUS: done`** de esa misma
tabla. Un `background` pedido a mano saltea el primer paso, no el segundo.

**Condición de verdad, positiva.** El predicado de re-invocación durable es verdadero **solo** cuando
el contrato documentado del host **garantiza** volver a invocar al conductor al completar un comando
en background. La **ausencia de garantía —no solo una garantía en contra— lo vuelve falso**; un host
que no documenta el comportamiento cuenta como falso.

**La continuidad la aporta el harness, no el transporte.** El multiplexor de terminales aloja el
proceso del implementador mientras el conductor no está mirando; despertar al conductor cuando el
comando termina es del **host** que lo corre. Alojar procesos bien no vuelve verdadero el predicado.

**Falla cerrado.** Con el predicado en falso, `background` **falla cerrado al poll acotado de hoy**:
el deadline de la tabla, el `kill` al vencer y el `UNAVAILABLE` con causa `deadline_exceeded`. El
banner obligatorio no cambia en ninguno de los dos casos — con callback es lo primero que se escribe
al despertar; con poll, lo primero después de ver `STATUS: done`.

### Rutas por invocación

Cada despacho obtiene un `invocation_id` estable, distinto del `block_id` y de la ronda. Todos sus
artefactos se escriben bajo una ruta exclusiva; una reanudación conserva el mismo identificador y un
nuevo bloque recibe otro.

| Artefacto | Plantilla de ruta |
|---|---|
| prompt | `<dir-del-work-order>/cross-implement/<invocation_id>/prompt.txt` |
| report | `<dir-del-work-order>/cross-implement/<invocation_id>/report.txt` |
| sesión | `<dir-del-work-order>/cross-implement/<invocation_id>/session.txt` |
| registro | `<dir-del-work-order>/implement-log-<invocation_id>.md` |

## Archivos de trabajo (scratch)

Junto al work order, el subdirectorio `cross-implement/<invocation_id>/` conserva el scratch de una
sola invocación (mismo criterio que `cross-review/`):

```
<dir del work order>/cross-implement/<invocation_id>/
├─ work-order.md          # solo en modo directo sin archivo: contrato destilado de esta invocación
├─ prompt.txt             # prompt-contrato (Write, nunca inline)
├─ fix-r1.txt, fix-r2.txt # deltas del fix loop de la misma sesión
├─ report.txt             # reporte vigente de esta invocación
├─ thread.jsonl           # stream JSONL del lanzamiento (Vía W-B) — fuente del thread id
├─ session.txt            # thread/session id capturado
├─ session-meta.json      # modelo y esfuerzo resueltos; se recargan antes de cada resume
├─ proof-baseline.md      # medición de cada comando sobre block_base, antes del dispatch
└─ impl.err.txt           # stderr del implementador
```

En SDD resuelve a `.plans/<id>/cross-implement/<invocation_id>/`. Local y untracked, sin
autolimpieza — igual que `cross-review/` y `co-explore/`.

## Log de implementación

`implement-log-<invocation_id>.md` junto al work order
(`.plans/<id>/implement-log-<invocation_id>.md` en SDD). Registro auditable de una delegación que no
sobrescribe las anteriores:

```markdown
# Cross-implement log — <id|work order> (<ISO-8601>)
Implementador: <codex exec | claude -p>  ·  modelo: <model | CLI default>  ·  max_fix_rounds: <n>
Proof (lista): `<comando 1>`, `<comando 2>`, …   ·   salida y exit code por comando, cada ronda

## Ronda 1 — implementación
FILES declarados: <n> · coinciden con git status: <sí/no>
Proof por comando (corridos por el conductor):
  - `<comando exacto>` → exit <n> · <PASS / REGRESIÓN vs base / falla preexistente adjudicada>
  (una línea por comando; el **comando exacto** es su identidad — es lo que nombra una regresión
  en el triage, porque una comprobación agregada no tiene `checkId`)
Veredicto del conductor: <aceptado | fix round: qué corregir>
Drift detectado: <ninguno | lista → revertido/declarado>
Clase de cada falla (`ownership.md`): <IMPLEMENTATION_DEFECT | VERIFICATION_DEFECT | ENVIRONMENT_FAILURE | DESIGN_GAP, una por falla — omitir la línea si el proof pasó>
Regresiones de comprobación agregada (una línea por comando, si las hubo):
  - comando: `<el comando exacto — es su identidad, no tiene checkId>`
    clase: IMPLEMENTATION_DEFECT · ronda consumida: <sí/no, contra max_fix_rounds>
    evidencia base: <exit code + resumen, de proof-baseline.md> · evidencia del bloque: <ídem>
    decisión: <regresión confirmada | falla preexistente adjudicada por <quién>, con su motivo>
  (sin estas cuatro líneas, decir que la regresión "consume una ronda" no deja nada auditable:
   `ownership.md` presupuesta por `checkId` y una comprobación agregada no tiene uno)
¿El work order admitía otra lectura?: <no | sí: qué se entendió y qué se quiso decir — solo si hubo falla>

## Ronda 2 — fix
<ídem>

## Resultado
<IMPLEMENTED | PARTIAL (takeover: qué terminó el conductor) | UNAVAILABLE> en <n> rondas.
Desviaciones del work order: <lista o "ninguna">.
```

> **Las dos últimas líneas de cada ronda no piden trabajo nuevo: piden no tirar el que ya se hizo.**
> La clase **ya se decide en toda corrida** —`ownership.md` la exige antes del fix loop, porque de
> ella depende si la falla consume ronda—, pero hasta ahora se decidía y se evaporaba. Escribirla es
> lo que deja un rastro comparable entre corridas.
>
> <!-- corpus-invariante:inicio:cross-implement.reference.md.919a8d9922f4 -->
> **Qué pregunta contestan.** En la ruta recomendada la regla 8 manda a la familia opuesta, y su justificación es
> <!-- corpus-invariante:fin:cross-implement.reference.md.919a8d9922f4 -->
> que un implementador que no comparte los supuestos del autor **detecta la ambigüedad del contrato**
> — un work order que admite dos lecturas se delata cuando alguien elige la otra. Eso es una
> hipótesis, no un hecho medido. Si a lo largo de varias corridas casi todas las fallas son
> `IMPLEMENTATION_DEFECT` con "otra lectura: no", la regla 8 no está comprando ese detector y su
> costo hay que defenderlo por otro lado. La clase sola no alcanza para saberlo: dice **por qué
> falló la prueba**, no **si el contrato era ambiguo**; por eso van las dos.
>
> Es un registro, no un gate: no bloquea la ronda, no cambia la clasificación y no le agrega nada al
> implementador, que ni se entera.

### Qué hacer cuando el registro muestre algo

El hueco que este registro vigila es **estrecho y de una sola clase**: el par *autor del work order
<!-- corpus-invariante:inicio:cross-implement.reference.md.b95da3b4ded1 -->
↔ revisor del diff* es la misma familia, así que un contrato ambiguo lo transcribe fielmente el
<!-- corpus-invariante:fin:cross-implement.reference.md.b95da3b4ded1 -->
implementador y el revisor comparte el punto ciego que lo produjo. Todo lo demás ya cruza familia
(ver `CLAUDE.md` → regla de fronteras). **Hoy no se escribe nada para cubrirlo**, y el motivo es que
está medido en vez de discutido.

**Qué cuenta como señal:** una falla clasificada `VERIFICATION_DEFECT` o `DESIGN_GAP` **con
"¿el work order admitía otra lectura?: sí"**. Un `IMPLEMENTATION_DEFECT` con "otra lectura: no" es lo
contrario de una señal: en una corrida cross-family, es el pipeline funcionando — el implementador hizo algo
distinto de lo pedido y el conductor lo cazó.

> **El campo lo contesta el autor del work order, y eso lo vuelve asimétrico.** El conductor de esta
> skill **es** quien escribió el contrato, así que se le está pidiendo que dictamine si lo escribió
> ambiguo — que es exactamente quien peor puede verlo. No invalida el registro, pero decide cómo se
> lee:
>
> | Lo que dice el log | Cuánto vale |
> |---|---|
> | **"otra lectura: sí"** | **mucho.** Es una admisión contra el propio interés: el autor reconociendo que escribió mal. Cuando aparece, es señal real |
> | **"otra lectura: no"** | **poco.** Es el autor absolviéndose. Puede ser cierto, o puede ser el punto ciego funcionando |
>
> Consecuencia práctica sobre el conteo: **los "sí" se cuentan, los "no" no prueban nada.** Un log
> lleno de "no" no acredita que no haya hueco — es lo que el hueco predice. Por eso la condición de
> abajo cuenta apariciones de la firma y **nunca** su ausencia.
>
> La salida obvia sería que lo conteste otro. No la hay hoy: el único que ve el diff junto al
> contrato es el conductor. Se registra con el sesgo declarado, que es mejor que no registrar o que
> registrar creyéndolo neutral.

**Cuándo se reabre.** A la **primera** aparición se mira el caso; a la **segunda**, se abre flujo
propio. Las dos condiciones van juntas:

1. dos fallas con esa firma, y
2. el proyecto **no** tiene por delante una revisión de PR cross-family (`bitbucket-code-review` o
   equivalente), que cubriría el mismo punto ciego un paso después.

> **El dos es un juicio, no un umbral medido, y conviene que se sepa.** Con cero corridas
> registradas cualquier número es inventado; lo que lo fija en dos y no en diez es que las corridas
> de esta skill son pocas, así que esperar significancia estadística es esperar para siempre. Uno
> puede ser mala suerte; dos ya es un patrón que vale un flujo.

**Qué se abre, si se abre:** sede `cross-implement`, **sin skill nueva**, y con
`final_diff_review.mode` como dueño de configuración. Eso ya está decidido y no se re-litiga: lo
único que faltaba era saber si hace falta.

En modo embebido, sdd-flow referencia este log desde su flujo; el commit y el `verify` siguen
siendo de sdd-flow.
