# cross-implement — Ownership de fallas

Qué hacer cuando una fila del contrato falla: de quién es el problema, cuánto presupuesto tiene cada
clase, y qué reglas siguen rigiendo durante el takeover.

Vive en un archivo aparte de `reference.md` porque se lee en **un momento distinto** —después de que
una ronda falló, no antes de delegar— y porque no hace falta cargarlo en una corrida que sale bien a
la primera.

## Ownership de fallas

Cuando una fila del contrato falla, la primera pregunta no es "cómo lo arreglo" sino **de quién es el
problema**. Sin esa pregunta, toda falla se atribuye al implementador por defecto y se gasta una
ronda de fix en algo que quizá no se arregla implementando — el caso más caro es una fila mal escrita
que el implementador intenta satisfacer tres veces.

Esa pregunta es el **triage de ownership**. Siempre con apellido: "triage de ownership" o
"clasificación de ownership", nunca la palabra sola, que en este repo ya nombra otras dos cosas —el
paso que procesa comentarios de un PR y el orden en que se atacan los findings de una revisión— y un
tercer sentido a secas es ambiguo justo adentro de un fix loop.

**La unidad es el `checkId`, no la ronda ni el delta.** Se clasifica cada fila que falló, por
separado. Un presupuesto por corrida deja que una sola fila patológica consuma el de todas las demás,
y una clasificación por delta obliga a elegir una sola causa cuando dos filas fallaron por motivos
distintos.

### Las cuatro clases

| Clase | Qué falló | Cómo se reconoce |
|---|---|---|
| `IMPLEMENTATION_DEFECT` | el código no hace lo que la fila exige | la fila está bien escrita, su esperado es el correcto, y el comando mide lo que dice medir. |
| `VERIFICATION_DEFECT` | la fila está mal escrita: mide otra cosa, o no discrimina | el código hace lo pedido y la fila falla igual; o la fila pasaría igual **sin** el cambio. |
| `ENVIRONMENT_FAILURE` | la comprobación no llegó a correr | falta un binario, un servicio o una credencial. El resultado no es un veredicto sobre el código: es la ausencia de veredicto. |
| `DESIGN_GAP` | el requisito, o el resultado que se espera de él, están mal | arreglar el código o reescribir la fila no resuelve nada; lo que hay que revisar es qué se pidió. |

La frontera que más se cruza es la de las dos del medio: `ENVIRONMENT_FAILURE` es "no pude medir" y
`VERIFICATION_DEFECT` es "medí mal". Confundirlas convierte un impedimento pasajero en una reescritura
del contrato, o al revés, hace reintentar sin cambiar nada una comprobación que nunca iba a servir.

### La matriz de control de flujo

Los presupuestos son **por `checkId`**, no por corrida, y ninguna clase permite un loop sin tope:

| Clase | ¿Consume ronda? | Presupuesto propio | Al agotarlo |
|---|---|---|---|
| `IMPLEMENTATION_DEFECT` | **Sí** | `max_fix_rounds` (el que ya existe) | takeover del conductor → `PARTIAL` |
| `VERIFICATION_DEFECT` | No | 2 versiones nuevas del contrato | reclasifica a `DESIGN_GAP` |
| `ENVIRONMENT_FAILURE` | No | 2 intentos de reparación | la fila queda `BLOCKED` y el cierre **no** es exitoso |
| `DESIGN_GAP` | No | — (terminal en la primera aparición) | suspende y devuelve al diseño |

**Solo `IMPLEMENTATION_DEFECT` consume ronda**, porque es la única clase donde el trabajo pendiente
es implementar. Las otras tres gastan un presupuesto propio: si consumieran ronda, un entorno roto
agotaría `max_fix_rounds` sin que el implementador hubiera fallado nunca.

Por qué `VERIFICATION_DEFECT` tiene tope de dos, y no es un número arbitrario: **un check que no se
deja escribir bien en dos intentos es un problema de diseño**, no de redacción. Y sin tope reabre
exactamente la puerta que la invariancia de IDs cierra — se reescribe la fila una y otra vez hasta
que pasa, y el contrato queda ablandado sin que ninguna regla se haya violado.

`ENVIRONMENT_FAILURE` termina en `BLOCKED` y no en "seguimos igual": una fila que nunca se pudo medir
no tiene criterio de "hecho", y cerrar en verde con ella presente sería afirmar algo que nadie
comprobó.

### Razón falsable, desde la segunda falla

A partir de la **segunda falla consecutiva del mismo `checkId`**, la clasificación no vale sin una
**razón falsable**: una afirmación que una observación concreta pueda **refutar**. Es el mismo par de
conceptos —observable y refutación— con que `co-explore` mide sus hipótesis; se reusa el vocabulario
en vez de inventar otro para lo mismo.

No se exige en la primera falla: la primera es lo normal, el baseline arranca en rojo por diseño. La
segunda es donde el loop empieza a gastar presupuesto sobre una hipótesis que nadie escribió, y donde
"le erró de nuevo" deja de ser información.

| No es falsable | Sí lo es |
|---|---|
| "el fix no cubrió todos los casos" | "el handler compara sin normalizar el huso, así que falla el caso de 23:59 UTC-3 y pasa el de 12:00" |
| "faltó manejar un borde" | "el parser corta en el primer separador, así que un valor con dos separadores pierde la segunda mitad" |
| "el implementador no entendió el requisito" | "implementó el rechazo en el middleware y la fila mide el handler, así que la respuesta llega con 200 antes de pasar por ahí" |

Las de la izquierda son verdaderas de casi cualquier falla y no dicen qué mirar. Las de la derecha
nombran **qué observación las tumbaría**: si el caso de 12:00 también falla, la razón era otra.

### Una ronda por delta

Todos los `IMPLEMENTATION_DEFECT` observados en el **mismo delta** van en **una sola ronda** de fix,
juntos. Mandarlos de a uno quema `max_fix_rounds` repartiendo información que ya estaba toda
disponible: el conductor los vio en la misma revisión, y el implementador tiene la sesión abierta con
todo el contexto.

La agrupación es por delta, no por archivo ni por cercanía: dos defectos del mismo delta van juntos
aunque estén en módulos distintos.

### Cómo se registra

El log ya tiene una estructura **por ronda**; la clasificación entra ahí, sin crear ningún artefacto
nuevo. Cada ronda suma una línea por `checkId` que falló, con estos cuatro campos:

```markdown
## Ronda 2 — fix
Ownership: (una línea por checkId que falló en la ronda anterior)
- `checkId: V2` · `clase: IMPLEMENTATION_DEFECT` · `consumedRound: sí` · `evidencia: el test de 23:59 UTC-3 sigue en rojo; el de 12:00 pasa`
- `checkId: V4` · `clase: ENVIRONMENT_FAILURE` · `consumedRound: no` · `evidencia: falta el binario de migraciones; el comando no llegó a correr`
```

`consumedRound` se registra explícito y no se deduce de la clase, aunque la matriz ya lo determine:
escrito, un desacuerdo entre la clase y el consumo es visible; deducido, el conteo de rondas queda
sin nada contra qué contrastarse.

### Re-baseline en worktree aislado

Reparar un `VERIFICATION_DEFECT` obliga a emitir una versión nueva del contrato y **volver a medir el
baseline de esa fila** sobre el commit pre-dispatch. Ahí aparece el problema: el árbol activo contiene
el diff del implementador, y medir "cómo estaba antes" exige un árbol *sin* ese diff.

**No se reconstruye ese estado sobre el árbol activo.** `git checkout`, `git reset` y `git stash`
destruyen o esconden exactamente lo que se está evaluando, y si algo falla en el medio el diff
delegado —que nadie más tiene— se pierde. Se usa un worktree temporal, mismo patrón descartable que
`co-explore` usa para su ejecución opt-in:

```bash
# @bloque:rebaseline-worktree
# Predicado: el re-baseline corre sobre el commit pre-dispatch en un worktree temporal, el árbol
# activo queda intacto, el temporal se remueve y deja de figurar en git worktree list, y cualquier
# incertidumbre de creación o limpieza deja la fila en BLOCKED.
# Entradas: $sha_pre (commit pre-dispatch) · $fila (checkId) · $cmd (comando de esa fila)
set -u
git cat-file -e "$sha_pre^{commit}" 2>/dev/null || { echo "BLOCKED $fila: sha pre-dispatch inválido" >&2; exit 1; }
WT="$(git rev-parse --show-toplevel)/../.rebaseline-wt-$$"
git worktree add --detach "$WT" "$sha_pre" >/dev/null 2>&1 || { echo "BLOCKED $fila: no se pudo crear el worktree" >&2; exit 1; }

( cd "$WT" && eval "$cmd" ) > "$WT.out" 2>&1; res=$?
commit=$(git -C "$WT" rev-parse HEAD); ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf 'id: %s · resultado: %s · commit: %s · timestamp: %s\n' \
  "$fila" "$([ $res -eq 0 ] && echo GREEN_ALREADY || echo RED)" "$commit" "$ts"

git worktree remove --force "$WT" >/dev/null 2>&1
git worktree prune
# La remoción se COMPRUEBA, no se asume: un worktree que quedó registrado deja el repo con un árbol
# fantasma apuntando a un directorio que quizá ya no existe, y la próxima corrida hereda el lío.
if git worktree list --porcelain | grep -qF "$WT"; then
  echo "BLOCKED $fila: el worktree sigue registrado en git worktree list" >&2; exit 1
fi
rm -f "$WT.out"
# @fin:rebaseline-worktree
```

```powershell
# @bloque:rebaseline-worktree-ps
# Predicado: el re-baseline corre sobre el commit pre-dispatch en un worktree temporal, el árbol
# activo queda intacto, el temporal se remueve y deja de figurar en git worktree list, y cualquier
# incertidumbre de creación o limpieza deja la fila en BLOCKED.
# Entradas: $sha_pre (commit pre-dispatch) · $fila (checkId) · $cmd (comando de esa fila)
git cat-file -e "$sha_pre^{commit}" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Error "BLOCKED ${fila}: sha pre-dispatch inválido"; exit 1 }
$WT = Join-Path (Split-Path (git rev-parse --show-toplevel)) ".rebaseline-wt-$PID"
git worktree add --detach $WT $sha_pre 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Error "BLOCKED ${fila}: no se pudo crear el worktree"; exit 1 }

Push-Location $WT
$salida = & ([scriptblock]::Create($cmd)) 2>&1
$res = $LASTEXITCODE
Pop-Location
$commit = git -C $WT rev-parse HEAD
$ts = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$estado = if ($res -eq 0) { 'GREEN_ALREADY' } else { 'RED' }
"id: $fila · resultado: $estado · commit: $commit · timestamp: $ts"

git worktree remove --force $WT 2>$null | Out-Null
git worktree prune
# La remoción se COMPRUEBA, no se asume: un worktree que quedó registrado deja el repo con un árbol
# fantasma apuntando a un directorio que quizá ya no existe, y la próxima corrida hereda el lío.
if ((git worktree list --porcelain) -match [regex]::Escape($WT)) {
  Write-Error "BLOCKED ${fila}: el worktree sigue registrado en git worktree list"; exit 1
}
# @fin:rebaseline-worktree-ps
```

Los ocho pasos, en orden: **resolver y validar** el SHA pre-dispatch · **crear** el temporal ·
`git worktree add --detach` sobre ese SHA · ejecutar **solo la fila corregida**, nunca el contrato
entero · capturar resultado, commit y timestamp · **remover** el worktree · **comprobar** que ya no
figura en `git worktree list` · y ante cualquier incertidumbre de creación o de limpieza, dejar la
fila en `BLOCKED`.

> **El alcance de la prohibición, y por qué importa.** Lo prohibido es **reconstruir estado histórico
> mientras hay un diff ajeno vivo en el árbol** — no `git stash` en sí. El `revert-to-confirm` de
> `sdd-flow` usa `git stash push`/`pop` a propósito, dentro de la misma corrida, sobre cambios
> propios y con el `pop` inmediato: ahí no hay diff ajeno que perder ni estado histórico que
> reconstruir. Sin acotar la prohibición por su motivo, este texto contradiría una instrucción
> vigente de la skill más grande del repo, y quien leyera las dos tendría que elegir cuál desobedecer.

### Qué habilita reanudar la sesión

Reanudar la sesión del implementador es la respuesta a **una sola** de las cuatro clases:
`IMPLEMENTATION_DEFECT`. Las otras tres no se arreglan implementando, y por eso no abren fix round:

- `VERIFICATION_DEFECT` → versión nueva del contrato y re-baseline de esa fila. El implementador no
  tiene nada que corregir: su código ya hace lo pedido.
- `ENVIRONMENT_FAILURE` → reparar el entorno y volver a medir. No hubo veredicto que contradecir.
- `DESIGN_GAP` → suspender y volver al diseño.

Mandarle cualquiera de esas tres como "corregí esto" le pide arreglar algo que no está en su código.
El resultado más probable no es que avise: es que fuerce el síntoma hasta que la comprobación pase
—un caso especial, un mock, un valor cableado— y esa es la peor salida de todas, porque deja el
contrato en verde y el requisito sin cumplir.

### El takeover, y qué sigue rigiendo durante él

Cuando `IMPLEMENTATION_DEFECT` agota `max_fix_rounds`, el conductor deja de delegar y termina los
fixes él mismo. Eso es el **takeover**, y cierra en `PARTIAL`: parte la hizo el implementador, parte
el conductor, y el log dice qué quedó de cada lado.

Dos cosas no cambian por haber entrado en takeover:

1. **Un `DESIGN_GAP` suspende de inmediato, también durante el takeover.** No hay "ya que estoy,
   lo resuelvo yo": si el requisito o su esperado están mal, implementarlos mejor no arregla nada.
   Se suspende y vuelve al diseño. Está dicho acá, donde el takeover se define, y no solo en la
   matriz de clases: quien entra en takeover lee esta sección, no vuelve a la tabla.
2. **El contrato sigue rigiendo, y el conductor no puede ablandar filas que él mismo escribió.**
   Es la tentación específica de este momento —la única persona que puede reescribir la fila es la
   misma que está peleando con ella, y ya no hay un tercero mirando—. Las invariantes valen igual:
   `Requisito` y `Esperado` no se tocan, y un cambio de evidencia sigue siendo una versión nueva con
   su re-baseline. Que el implementador se haya ido no cambia qué prueba el contrato.

### Precedencia entre los tres topes de corte

Conviven tres reglas de corte y hay que decir en qué orden mandan, porque cuentan cosas distintas:

| Tope | Qué cuenta | Alcance |
|---|---|---|
| `max_fix_rounds` | rondas de fix consumidas | esta skill |
| presupuesto por clase | intentos por `checkId` de una clase que no consume ronda | esta skill |
| 3 fallos de la misma falla | fallos repetidos del mismo síntoma | `sdd-flow`, en modo embebido |

**El tope de `sdd-flow` manda por encima de los dos de esta skill**: es una regla de diseño del flujo
llamador, y sigue siendo el que decide volver a `plan`/`specify`.

Y la pregunta que la convivencia obliga a contestar: **una clase que no consume ronda tampoco cuenta
para los 3 fallos de `sdd-flow`.** Ese tope cuenta *intentos de arreglo que fallaron*, y un
`ENVIRONMENT_FAILURE` no es un intento de arreglo: es la ausencia de medición. Contarlo mandaría al
gate de diseño un problema que se resuelve instalando un binario. Lo que sí cuenta hacia ese tope es
`IMPLEMENTATION_DEFECT`, y `DESIGN_GAP` lo hace irrelevante porque suspende en la primera aparición.

### Bloques de validación del ownership

Corren sobre el `implement-log.md`, que es donde todo esto queda registrado. Cada bloque declara su
predicado, idéntico en las dos variantes de shell.

```bash
# @bloque:ownership-log
# Predicado: cada línea de ownership trae checkId, clase válida, consumedRound y evidencia;
# consumedRound es "sí" exactamente para IMPLEMENTATION_DEFECT; ningún delta se reparte entre
# rondas; y desde la segunda aparición del mismo checkId la línea trae una razón que nombre un
# observable.
# Entradas: $log
t=$(mktemp -d); rc=0
# Heurística declarada, no juez semántico: caza las formas en que se escribe una razón que no se
# puede refutar. Se lista acá para que su alcance sea auditable.
GEN='no cubrió|no cubrio|faltó manejar|falto manejar|no entendió|no entendio|algún borde|algun borde|no quedó bien|no quedo bien'
# Solo las líneas BAJO un "Ownership:". Tomar todo `- \`checkId:` del archivo arrastraría las
# entradas del takeover, que no son clasificaciones; y filtrar por "tiene clase:" dejaría pasar en
# silencio justo la línea a la que le falta el campo.
awk '/^Ownership:/{on=1;next} /^## /{on=0} on&&/^[[:space:]]*$/{on=0} on&&/^- `checkId: /{print}' \
  "$log" > "$t/lin"

while IFS= read -r l; do
  id=$(printf '%s' "$l" | sed -E 's/.*`checkId: ([^`]*)`.*/\1/')
  cl=$(printf '%s' "$l" | sed -E 's/.*`clase: ([^`]*)`.*/\1/')
  cr=$(printf '%s' "$l" | sed -E 's/.*`consumedRound: ([^`]*)`.*/\1/')
  case "$cl" in
    IMPLEMENTATION_DEFECT|VERIFICATION_DEFECT|ENVIRONMENT_FAILURE|DESIGN_GAP) ;;
    *) printf 'GUARD:log-clasificacion %s: clase inválida "%s"\n' "$id" "$cl" >&2; rc=1 ;;
  esac
  printf '%s' "$l" | grep -q '`evidencia: [^`]' || {
    printf 'GUARD:log-clasificacion %s: sin evidencia\n' "$id" >&2; rc=1; }
  esp=no; [ "$cl" = IMPLEMENTATION_DEFECT ] && esp=sí
  [ "$cr" = "$esp" ] || {
    printf 'GUARD:log-clasificacion %s: consumedRound="%s" y la clase %s exige "%s"\n' \
      "$id" "${cr:-ausente}" "$cl" "$esp" >&2; rc=1; }
done < "$t/lin"

# un delta no se reparte entre rondas: se agrupa TODO lo del mismo delta en una sola
awk '/^## Ronda /{r++} /^- `checkId: /{if (match($0,/`delta: [^`]*`/)) {
       d=substr($0,RSTART+8,RLENGTH-9); print d"\t"r }}' "$log" | sort -u \
  | awk -F'\t' '{n[$1]++} END{for (d in n) if (n[d]>1) print "  "d" en "n[d]" rondas"}' > "$t/e"
[ -s "$t/e" ] && { echo "GUARD:delta-una-ronda hay deltas repartidos entre rondas:" >&2
  cat "$t/e" >&2; rc=1; }

# desde la SEGUNDA aparición del mismo checkId hace falta razón falsable
sed -E 's/.*`checkId: ([^`]*)`.*/\1/' "$t/lin" | awk '{n[$0]++; print $0"\t"n[$0]}' > "$t/ord"
paste "$t/ord" "$t/lin" | while IFS="$(printf '\t')" read -r id nth linea; do
  [ "${nth:-1}" -ge 2 ] || continue
  if ! printf '%s' "$linea" | grep -q '`razón: [^`]'; then
    printf 'GUARD:razon-falsable %s: aparición %s sin razón registrada\n' "$id" "$nth" >&2
    echo x >> "$t/rf"
  elif printf '%s' "$linea" | grep -qiE "\`razón: [^\`]*($GEN)"; then
    printf 'GUARD:razon-falsable %s: la razón no nombra un observable que la refute\n' "$id" >&2
    echo x >> "$t/rf"
  fi
done
[ -s "$t/rf" ] && rc=1
rm -rf "$t"; exit $rc
# @fin:ownership-log
```

```powershell
# @bloque:ownership-log-ps
# Predicado: cada línea de ownership trae checkId, clase válida, consumedRound y evidencia;
# consumedRound es "sí" exactamente para IMPLEMENTATION_DEFECT; ningún delta se reparte entre
# rondas; y desde la segunda aparición del mismo checkId la línea trae una razón que nombre un
# observable.
# Entradas: $log
$rc = 0
# Heurística declarada, no juez semántico: caza las formas en que se escribe una razón que no se
# puede refutar.
$gen = 'no cubrió|no cubrio|faltó manejar|falto manejar|no entendió|no entendio|algún borde|algun borde|no quedó bien|no quedo bien'
$doc = Get-Content -LiteralPath $log
# Los dos acumuladores son `Dictionary` con `[StringComparer]::Ordinal` y NO hashtables: las
# hashtables de PowerShell comparan sus claves sin distinguir mayúsculas, así que fundirían dos
# checkId `V1`/`v1` en uno —cobrándole al segundo una razón que no debe— y dos delta `D1`/`d1` en
# uno solo repartido entre rondas. El par POSIX los separa con `awk n[$0]++` y con `sort -u`.
$vistos = [System.Collections.Generic.Dictionary[string,int]]::new([StringComparer]::Ordinal)
$deltas = [System.Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
$ronda = 0; $on = $false
# Solo las líneas BAJO un "Ownership:". Tomar todo `- `checkId:` del archivo arrastraría las
# entradas del takeover, que no son clasificaciones; y filtrar por "tiene clase:" dejaría pasar en
# silencio justo la línea a la que le falta el campo.
foreach ($l in $doc) {
  if ($l -cmatch '^Ownership:') { $on = $true; continue }
  if ($l -cmatch '^## ' -or $l -match '^\s*$') { if ($l -cmatch '^## Ronda ') { $ronda++ }; $on = $false; continue }
  if (-not $on -or $l -cnotmatch '^- `checkId: ') { continue }
  $id = [regex]::Match($l, '`checkId: ([^`]*)`').Groups[1].Value
  $cl = [regex]::Match($l, '`clase: ([^`]*)`').Groups[1].Value
  $cr = [regex]::Match($l, '`consumedRound: ([^`]*)`').Groups[1].Value
  # Operadores case-sensitive: el par POSIX decide con `case`, `[ = ]` y `grep -q`, que distinguen
  # mayúsculas. Con los de .NET, `implementation_defect` sería una clase válida.
  if ($cl -cnotin @('IMPLEMENTATION_DEFECT','VERIFICATION_DEFECT','ENVIRONMENT_FAILURE','DESIGN_GAP')) {
    Write-Error "GUARD:log-clasificacion ${id}: clase inválida `"$cl`""; $rc = 1
  }
  if ($l -cnotmatch '`evidencia: [^`]') { Write-Error "GUARD:log-clasificacion ${id}: sin evidencia"; $rc = 1 }
  $esp = if ($cl -ceq 'IMPLEMENTATION_DEFECT') { 'sí' } else { 'no' }
  if ($cr -cne $esp) { Write-Error "GUARD:log-clasificacion ${id}: consumedRound=`"$cr`" y la clase $cl exige `"$esp`""; $rc = 1 }
  if ($l -cmatch '`delta: ([^`]*)`') {
    $d = $Matches[1]
    if (-not $deltas.ContainsKey($d)) { $deltas[$d] = @() }
    if ($ronda -notin $deltas[$d]) { $deltas[$d] += $ronda }
  }
  $n = 1 + $(if ($vistos.ContainsKey($id)) { $vistos[$id] } else { 0 }); $vistos[$id] = $n
  if ($n -ge 2) {
    if ($l -cnotmatch '`razón: [^`]') {
      Write-Error "GUARD:razon-falsable ${id}: aparición $n sin razón registrada"; $rc = 1
      # El `-match` de acá abajo es el ÚNICO que se deja insensible a propósito: su par POSIX busca
      # la heurística con `grep -qiE`, y una razón irrefutable lo sigue siendo en mayúsculas.
    } elseif ($l -match "``razón: [^``]*($gen)") {
      Write-Error "GUARD:razon-falsable ${id}: la razón no nombra un observable que la refute"; $rc = 1
    }
  }
}
foreach ($d in $deltas.Keys) {
  if ($deltas[$d].Count -gt 1) { Write-Error "GUARD:delta-una-ronda $d en $($deltas[$d].Count) rondas"; $rc = 1 }
}
exit $rc
# @fin:ownership-log-ps
```

```bash
# @bloque:ownership-presupuesto
# Predicado: ningún checkId excede el presupuesto de su clase — IMPLEMENTATION_DEFECT hasta
# max_fix_rounds, VERIFICATION_DEFECT y ENVIRONMENT_FAILURE hasta 2, DESIGN_GAP una sola vez.
# Entradas: $log $max_fix_rounds
t=$(mktemp -d); rc=0
# Mismo recorte que el bloque de log: solo las líneas bajo un "Ownership:".
awk '/^Ownership:/{on=1;next} /^## /{on=0} on&&/^[[:space:]]*$/{on=0} on{print}' "$log" \
  | sed -nE 's/^- `checkId: ([^`]*)`.*`clase: ([^`]*)`.*/\1\t\2/p' | sort | uniq -c \
  | awk -v mfr="$max_fix_rounds" '{n=$1; id=$2; cl=$3
      tope = (cl=="IMPLEMENTATION_DEFECT") ? mfr : ((cl=="DESIGN_GAP") ? 1 : 2)
      if (n > tope) print "  "id" · "cl" · "n" > "tope }' > "$t/e"
[ -s "$t/e" ] && { echo "GUARD:presupuesto-por-check presupuesto excedido:" >&2; cat "$t/e" >&2; rc=1; }
rm -rf "$t"; exit $rc
# @fin:ownership-presupuesto
```

```powershell
# @bloque:ownership-presupuesto-ps
# Predicado: ningún checkId excede el presupuesto de su clase — IMPLEMENTATION_DEFECT hasta
# max_fix_rounds, VERIFICATION_DEFECT y ENVIRONMENT_FAILURE hasta 2, DESIGN_GAP una sola vez.
# Entradas: $log $max_fix_rounds
$rc = 0
# Mismo recorte que el bloque de log: solo las líneas bajo un "Ownership:".
$on = $false
$pares = @(foreach ($l in (Get-Content -LiteralPath $log)) {
  if ($l -cmatch '^Ownership:') { $on = $true; continue }
  if ($l -cmatch '^## ' -or $l -match '^\s*$') { $on = $false; continue }
  if ($on -and $l -cmatch '^- `checkId: ' -and $l -cmatch '`clase: ') {
    "$([regex]::Match($l, '`checkId: ([^`]*)`').Groups[1].Value)`t$([regex]::Match($l, '`clase: ([^`]*)`').Groups[1].Value)"
  }
})
# `-CaseSensitive` y `-ceq` porque el par POSIX cuenta con `sort | uniq -c` y compara en `awk`, que
# distinguen mayúsculas: sin eso, un `design_gap` se sumaría al conteo de `DESIGN_GAP` y le gastaría
# un presupuesto que no es el suyo.
foreach ($g in ($pares | Group-Object -CaseSensitive)) {
  $id, $cl = $g.Name -split "`t"
  $tope = if ($cl -ceq 'IMPLEMENTATION_DEFECT') { [int]$max_fix_rounds } elseif ($cl -ceq 'DESIGN_GAP') { 1 } else { 2 }
  if ($g.Count -gt $tope) { Write-Error "GUARD:presupuesto-por-check $id · $cl · $($g.Count) > $tope"; $rc = 1 }
}
exit $rc
# @fin:ownership-presupuesto-ps
```

```bash
# @bloque:takeover-reglas
# Predicado: después de un DESIGN_GAP no hay ninguna ronda ni takeover posterior, y durante el
# takeover la versión vigente del contrato no cambia.
# Entradas: $log
rc=0
gap=$(grep -n 'DESIGN_GAP' "$log" | head -1 | cut -d: -f1)
if [ -n "$gap" ]; then
  post=$(awk -v g="$gap" 'NR>g && (/^## Ronda /||/^## Takeover/) {print NR": "$0}' "$log")
  [ -z "$post" ] || { printf 'GUARD:design-gap-corta-takeover hay trabajo después del DESIGN_GAP:\n%s\n' \
    "$post" >&2; rc=1; }
fi
# El conductor no puede ablandar filas que él escribió: durante el takeover la versión del contrato
# se congela. Una versión nueva ahí es el conductor reescribiendo su propia vara sin nadie mirando.
antes=$(awk '/^## Takeover/{exit} match($0,/`contrato: v[0-9]+`/){print substr($0,RSTART+11,RLENGTH-12)}' "$log" | tail -1)
durante=$(awk '/^## Takeover/{on=1} on && match($0,/`contrato: v[0-9]+`/){print substr($0,RSTART+11,RLENGTH-12)}' "$log" | tail -1)
if [ -n "$durante" ] && [ -n "$antes" ] && [ "$durante" != "$antes" ]; then
  printf 'GUARD:takeover-no-ablanda el contrato pasó de %s a %s durante el takeover\n' \
    "$antes" "$durante" >&2; rc=1
fi
exit $rc
# @fin:takeover-reglas
```

```powershell
# @bloque:takeover-reglas-ps
# Predicado: después de un DESIGN_GAP no hay ninguna ronda ni takeover posterior, y durante el
# takeover la versión vigente del contrato no cambia.
# Entradas: $log
$rc  = 0
$doc = Get-Content -LiteralPath $log
$gap = -1
# Operadores case-sensitive: el par POSIX busca con `grep` y `awk`, que distinguen mayúsculas. Con
# los de .NET, un `design_gap` cortaría el takeover y un `contrato: V2` contaría como versión.
for ($i = 0; $i -lt $doc.Count; $i++) { if ($doc[$i] -cmatch 'DESIGN_GAP') { $gap = $i; break } }
if ($gap -ge 0) {
  # Con el número de línea y un evento agregado, como el `awk` del par: sin la línea el lector no
  # sabe a qué altura del log está el trabajo que no debería existir.
  $post = @(for ($i = $gap + 1; $i -lt $doc.Count; $i++) { if ($doc[$i] -cmatch '^## (Ronda |Takeover)') { "$($i + 1): $($doc[$i])" } })
  if ($post.Count -gt 0) { Write-Error "GUARD:design-gap-corta-takeover hay trabajo después del DESIGN_GAP:`n$($post -join "`n")"; $rc = 1 }
}
# El conductor no puede ablandar filas que él escribió: durante el takeover la versión del contrato
# se congela. Una versión nueva ahí es el conductor reescribiendo su propia vara sin nadie mirando.
$antes = $null; $durante = $null; $on = $false
foreach ($l in $doc) {
  if ($l -cmatch '^## Takeover') { $on = $true }
  if ($l -cmatch '`contrato: (v\d+)`') { if ($on) { $durante = $Matches[1] } else { $antes = $Matches[1] } }
}
if ($durante -and $antes -and ($durante -cne $antes)) {
  Write-Error "GUARD:takeover-no-ablanda el contrato pasó de $antes a $durante durante el takeover"; $rc = 1
}
exit $rc
# @fin:takeover-reglas-ps
```
