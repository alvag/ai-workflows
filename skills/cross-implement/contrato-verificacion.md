# cross-implement — El contrato de verificación

Cómo se escribe, se congela y se comprueba la evidencia de un work order antes de delegarlo. Es la
definición normativa **única** del ecosistema: `sdd-flow` la materializa en el `plan.md` que escribe
y `sdd-orchestrator` la hereda en los planes que reparte; ninguno de los dos mantiene una plantilla
propia.

Vive en un archivo aparte de `reference.md` porque se lee en **un momento distinto** —antes del
dispatch, cuando se arma y se aprueba el contrato— y porque juntos superaban de largo lo que se
puede pedir que un agente cargue de una vez.

## Contrato de verificación

Cómo se escribe la evidencia de un work order **antes** de despacharlo: qué prueba cada requisito,
con qué comando, qué resultado se espera, y qué daba ese comando *antes* de implementar. Es el
esquema normativo **único** del ecosistema: quien lo materialice —`sdd-flow` en el `plan.md` que
escribe, `sdd-orchestrator` en los planes que reparte— lo cita y lo llena, nunca lo reescribe con
otra forma. Un segundo dialecto haría que el gate de esta skill valide un documento y el flujo
produzca otro.

> No confundir con **"Matriz de verificación"** (más arriba): aquella registra qué flags de los CLIs
> se probaron end-to-end en esta skill. Esta define un artefacto del work order.

El contrato tiene **dos partes**, y ninguna sustituye a la otra:

1. una **tabla** — qué se va a verificar y con qué;
2. un **bloque de baseline por versión** — qué se observó al establecer el punto de partida.

La tabla dice qué exige cada fila; el baseline dice qué se vio al ejecutarla sobre el código **sin
implementar**. Sin la segunda parte, una fila que ya pasaba antes del cambio se lee como prueba del
cambio.

### La tabla

Seis columnas, en este orden exacto, sin agregar ni quitar ninguna:

| Columna | Contenido |
|---|---|
| `ID` | identificador estable de la fila — el `checkId` con el que la referencian las tasks, el log y los registros de baseline. Único dentro del contrato. |
| `Requisito` | qué requisito del work order prueba esta fila, citado por su identificador y en una línea. |
| `Evidencia` | de qué **tipo** es la comprobación. Enum cerrado (abajo). |
| `Comando/observación` | el comando literal a ejecutar, o —cuando la evidencia no es ejecutable— la observación concreta a realizar. Copiable y repetible: "correr los tests" no es un comando. |
| `Esperado` | el resultado que cuenta como cumplido. Discriminante: si la fila pasaría igual sin el cambio, no verifica nada. |
| `Baseline` | qué dio esa comprobación **antes** de implementar. Enum cerrado (abajo). |

**Enum de `Evidencia`** — cuatro valores, cerrado:

| Valor | Cuándo |
|---|---|
| `test` | un test automatizado, que se ejecuta y devuelve un veredicto. |
| `build` | compilación, typecheck o lint: el veredicto lo da la herramienta. |
| `inspección` | lectura de un artefacto contra un predicado mecánico (una búsqueda, un encabezado que debe existir, un conteo). Determinística y repetible por cualquiera. |
| `manual` | una persona ejecuta pasos y compara contra lo esperado. Es el único tipo que no reproduce una máquina, y por eso el único que hay que justificar antes que elegir. |

**Enum de `Baseline`** — cuatro valores, cerrado:

| Valor | Significa |
|---|---|
| `RED` | se ejecutó y falló, como se esperaba. La fila discrimina: distingue el código con el cambio del código sin él. |
| `GREEN_ALREADY` | se ejecutó y **ya pasaba** sin el cambio. No prueba nada del cambio hasta que se adjudique por qué (ver "Adjudicación del baseline"). |
| `NOT_APPLICABLE` | ejecutar un baseline es **semánticamente inaplicable** a ese tipo de evidencia. Nunca por falta de entorno: eso es `BLOCKED`. |
| `BLOCKED` | no se pudo establecer el punto de partida. La fila queda sin criterio de "hecho". |

### El bloque de baseline

Cada versión del contrato lleva su propio bloque, titulado `Baseline de vN`, con **un registro por
fila de la tabla de esa versión, en el mismo orden y sin duplicados**. Un registro sin fila, o una
fila sin registro, impide congelar: la asimetría significa que alguien agregó una comprobación sin
medirla, o midió algo que ya no se exige.

Los encabezados del contrato **anidan bajo el encabezado que lo contiene**: en un `plan.md` cuyo
contrato vive bajo `## Verification`, cada versión es un `### vN` y su baseline un `#### Baseline de
vN`; en un documento de contrato suelto, `## vN` y `### Baseline de vN`. Lo fijo son los nombres y
el anidamiento relativo, no el número de almohadillas.

Un registro tiene estos campos:

| Campo | Contenido |
|---|---|
| `id` | el mismo `ID` de la fila que describe. Es lo único que los liga: por eso el orden importa pero no alcanza. |
| `commit` | el SHA del código sobre el que se ejecutó la comprobación. |
| `timestamp` | cuándo se ejecutó, en ISO-8601. |
| `adjudicación` | por qué un `GREEN_ALREADY` cuenta igual. Solo en filas con ese estado. |
| `justificación` | por qué un baseline es inaplicable. Solo en filas `NOT_APPLICABLE`. |

**Los cuatro últimos no son columnas de la tabla, y no pueden serlo.** La tabla describe la
comprobación —lo que se repite en cada versión—; el registro describe una **medición concreta**, que
es de una versión y de un commit. Meter la adjudicación o el timestamp en la tabla los volvería
parte de lo que se compara entre versiones, y entonces corregir un comando obligaría a "cambiar" el
requisito. Cuándo cada uno es obligatorio se define en "Adjudicación del baseline".

### Ejemplo mínimo — `v1`

Un contrato recién derivado, antes de implementar nada. Las dos filas están en `RED` porque es lo
normal en `v1`: si algo arranca en otro estado, hay que adjudicarlo o justificarlo.

```markdown
### v1

| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |
|---|---|---|---|---|---|
| V1 | R-2 — el endpoint rechaza un token vencido | test | `npm test -- auth/token.spec.ts -t "token vencido"` | 1 test, verde | RED |
| V2 | R-5 — el README documenta la variable nueva | inspección | `grep -c '^AUTH_TTL=' README.md` | `1` | RED |

#### Baseline de v1
`hash_previo:` · `hash: 9b1c04e2…`

- `id: V1` · `commit: 4f2a9c1` · `timestamp: 2026-07-31T09:14:00-03:00`
- `id: V2` · `commit: 4f2a9c1` · `timestamp: 2026-07-31T09:14:12-03:00`
```

Dos filas, dos registros, mismo orden, mismos IDs. `hash_previo` va vacío porque `v1` no tiene
anterior (ver "Cadena de integridad"). Es el mínimo que se puede congelar.

### Adjudicación del baseline

Un `RED` se explica solo: la comprobación falla sin el cambio, así que distingue. Los otros dos
estados resueltos no, y por eso cada uno exige un campo en **su registro de baseline** —identificado
por el mismo `ID` de la fila, no en la tabla.

**`GREEN_ALREADY` exige `adjudicación`.** Que una comprobación ya pase antes de implementar admite
tres lecturas, y decidir cuál es *el* trabajo de adjudicar:

| Lectura | Qué significa | Qué se hace |
|---|---|---|
| `already_satisfied` | el requisito ya estaba cumplido por el código existente. La fila sigue valiendo como guarda de regresión. | se congela con esta adjudicación escrita. |
| `weak_check` | la comprobación no discrimina: pasaría con o sin el cambio. | **no se congela así.** Se reescribe la fila y se vuelve a medir; es un `VERIFICATION_DEFECT`. |
| `invalid_assumption` | el requisito daba por cierto algo que no lo es, y por eso no hay nada que cambiar. | **no se congela así.** Vuelve al diseño; es un `DESIGN_GAP`. |

Solo **`already_satisfied` sobrevive a una versión congelada**. Los otros dos nombran trabajo
pendiente, no un veredicto: dejarlos escritos en un contrato congelado sería registrar que se sabía
que la fila no servía y se despachó igual.

**`NOT_APPLICABLE` exige `justificación`**, en el mismo registro y por escrito: por qué ejecutar un
baseline es *semánticamente* inaplicable a esa evidencia. "No tengo el entorno" nunca es una
justificación válida — eso es `BLOCKED`, y la diferencia importa porque `BLOCKED` frena el dispatch
y `NOT_APPLICABLE` no.

**Todo registro lleva `commit` y `timestamp`**, resuelto o no el estado. El `commit` es lo que
convierte "antes" en algo verificable: sin él, un baseline leído más tarde no dice qué código midió.
El `timestamp`, en ISO-8601, ordena las mediciones y delata la copiada de una versión anterior en
vez de re-ejecutada.

```markdown
- `id: V3` · `commit: 4f2a9c1` · `timestamp: 2026-07-31T09:15:03-03:00` · `adjudicación: already_satisfied`
- `id: V4` · `commit: 4f2a9c1` · `timestamp: 2026-07-31T09:15:20-03:00` · `justificación: la fila verifica el copy de un correo que este work order no envía; no hay comando que ejecutar contra el código`
```

### Cobertura bidireccional

Para congelar, la correspondencia entre requisitos en alcance y filas tiene que cerrar **en las dos
direcciones**, y cada dirección bloquea por su cuenta:

- un **requisito en alcance sin fila** significa que algo se va a implementar sin nada que lo pruebe;
- una **fila que no referencia ningún requisito** significa que se va a exigir algo que nadie pidió,
  y que al fallar no se sabrá contra qué decidir.

Una sola dirección no alcanza: un contrato con una fila por requisito **más** tres filas huérfanas
cumple "todo requisito tiene fila" y sigue roto.

### Qué es invariante entre versiones

El contrato se puede corregir; lo que no se puede es **ablandar**. Dos invariantes lo sostienen, y
se comprueban leyendo el documento actual —no dependen de ningún registro histórico:

1. **El conjunto de `ID` es invariante.** Una versión nueva que agregue o quite un ID se rechaza.
2. **Dentro de cada fila, `Requisito` y `Esperado` también.** Se comparan **por ID**, no por
   posición.

Es decir: una versión nueva puede cambiar **únicamente** `Evidencia` y `Comando/observación`, y solo
conservando el poder discriminante de la fila y repitiendo el baseline. Reparar cómo se mide algo es
legítimo; cambiar qué se mide o qué resultado cuenta como bueno **no es reparar una prueba, es
rediseñar el requisito**, y vuelve al gate de diseño clasificado como `DESIGN_GAP` (ver "Ownership
de fallas"). Si la fila corregida arroja `GREEN_ALREADY`, pasa por la adjudicación antes de
congelarse.

La segunda invariante es la que hace útil a la primera. Sin ella basta clasificar el problema como
`VERIFICATION_DEFECT` y emitir una versión donde la misma fila espera `HTTP 200` en vez de
`HTTP 201`, o donde el comando pasa siempre: los IDs no cambiaron, la cobertura sigue completa, la
cadena cierra — y el contrato quedó vacío.

### Versiones y vigencia

Cada versión es un **bloque completo**: su tabla entera y su bloque de baseline entero. No hay
versiones que expresen solo el delta contra la anterior; leer la vigente tiene que bastar para saber
qué se exige, sin reconstruir nada.

- Numeradas consecutivamente desde `v1`. Un salto (`v1`, `v3`) se rechaza: o falta una versión o
  alguien renumeró.
- **La de número mayor es la vigente.** Es la única contra la que se ejecuta y se cierra.
- Las anteriores se conservan como historia legible, no como fuente de obligaciones.

### Cadena de integridad

Cada versión registra dos hashes, en la cabecera de su bloque de baseline:

- `hash` — SHA-256 de los **bytes canónicos** de la versión, que son el bloque completo (tabla +
  baseline) con el **valor** del propio campo `hash` vaciado. Incluirlo sería circular: formaría
  parte de lo que se hashea para calcularlo. Se vacía el valor y se conserva la clave, para que la
  forma del bloque no dependa de si ya fue hasheado.
- `hash_previo` — el `hash` de la versión inmediatamente anterior; cadena vacía en `v1`.

**Dónde termina el bloque.** Empieza en el encabezado `#+ vN` y termina en el **primer encabezado de
nivel menor o igual** al de esa versión, o en EOF. Así `#### Baseline de vN` queda adentro —es más
profundo— y `## Tests y build` queda afuera. Los encabezados dentro de cercas ` ``` ` no cuentan: un
`# comentario` de un bloque de código no cierra nada.

Fijarlo importa tanto como fijar la normalización, y por la misma razón. Definir el hash sin definir
su frontera dejaba a la **última** versión absorbiendo todo lo que viniera después: en un plan de
`sdd-flow`, la sección "Tests y build" y el `## Verify` que el propio flujo escribe al terminar. La
cadena se rompía sola, sin que nadie hubiera tocado una fila, y el gate rechazaba un contrato intacto.

Bytes canónicos = el bloque tal cual, con finales de línea `LF`, sin espacios al final de cada línea
y sin líneas en blanco al final. Sin fijar la normalización, un editor que reescriba los finales de
línea rompe la cadena sin que nadie haya tocado el contenido.

El gate previo al dispatch recomputa la cadena entera y rechaza el contrato si no cierra.

**Lo que esto detecta:** una edición retroactiva que no recalculó la cadena.

**Lo que explícitamente NO prueba:** que una versión vieja no haya sido editada. Quien edita `v1` y
recalcula la cadena obtiene un documento válido, y no hay ancla externa que lo desmienta: el
contrato vive junto al plan, en un directorio **local y untracked**, así que el commit que cada
registro anota contiene el código evaluado, **nunca los bytes del contrato**. Cualquier redacción
que prometa inmutabilidad demostrable acá sería falsa.

Por eso la defensa real contra el ablandamiento no es esta cadena, sino las dos invariantes de
arriba. La cadena es una comprobación de integridad barata, no una garantía de historia.

### Contrato en work orders sin flujo SDD

Cuando el work order es un `.plans/<id>/` de `sdd-flow`, el contrato ya viene escrito: el flujo lo
declara en su plan y lo congela antes de delegar. Cuando **no** lo es —un `PLAN.md`, un equivalente,
o un contrato destilado de la conversación en modo directo— no hay flujo que lo produzca, y el
reparto de responsabilidades es este:

| # | Quién | Qué | Por qué no otro |
|---|---|---|---|
| 1 | el conductor | **deriva** la tabla del work order | pedirle al implementador que derive sus propias comprobaciones lo pone a calificar su propio trabajo, y borra lo único contra lo que el gate podía contrastar su entrega. |
| 2 | el conductor | **ejecuta el baseline**, sobre el código sin el cambio | delegarlo tiene el mismo defecto y además es imposible después: una vez despachado, el árbol ya contiene el diff y "antes" dejó de existir. |
| 3 | el usuario | **aprueba** la tabla, junto con el work order, en el gate de kickoff que esta skill ya tiene | no hay derivación implícita: un contrato que nadie aprobó no es un contrato, es una lista que escribió el conductor. |
| 4 | el conductor | **congela** inmediatamente después de esa aprobación y **antes** del dispatch | congelar antes de aprobar vuelve el gate un trámite sobre algo ya cerrado; despachar sin congelar deja el contrato editable mientras corre la implementación, que es justamente cuando aparece la tentación de ablandarlo. |

El **orden es parte de la regla**, no una sugerencia de redacción: derivar → medir el baseline →
aprobar → congelar → despachar. Cada paso fuera de lugar rompe una garantía distinta, así que
ninguno de los cuatro se comprueba mirando solo el resultado final.

Sin gate de kickoff no hay aprobación posible y el modo directo no despacha: la salida no es
congelar igual, es no despachar.

### `proof_cmd` frente al contrato

`proof_cmd` existía antes que este contrato y **se conserva**, con un papel acotado: es una
comprobación **agregada y opcional** —la suite completa, el build— que el conductor corre para ver
el conjunto de un vistazo tras cada ronda.

Lo que **no** es:

- no sustituye ninguna fila del contrato;
- no alcanza para dar un requisito por cumplido, ni siquiera en verde. Lo que cierra un requisito es
  **su fila**, con su esperado y su baseline. Un `proof_cmd` verde sobre un contrato con una fila en
  rojo describe una suite que no cubre ese requisito, no un requisito cumplido.

De ahí la asimetría del gate, que es la forma verificable de todo lo anterior:

- **contrato sin `proof_cmd`** → procede. El contrato es la evidencia.
- **`proof_cmd` sin contrato** → no procede. Es exactamente la situación que este contrato existe
  para eliminar: un comando agregado haciendo de prueba de todo.

### El gate previo al dispatch

> **Alcance de "contrato congelado".** «No se delega nada que no esté congelado» abarca **el work
> order y su tabla de verificación congelada**: un work order sin tabla, o con una tabla sin
> congelar, no se delega.

El conductor valida el contrato antes de lanzar. Cinco comprobaciones; cualquiera que falle **detiene
el dispatch**, con el mismo tratamiento que el clean-tree gate: no se lanza y se reporta como gate
fallido.

| # | Comprobación | Falla cuando |
|---|---|---|
| 1 | **existe un contrato** | el work order no trae tabla. |
| 2 | **versión vigente identificada** | falta la numeración, hay un salto en la serie, o la cadena de integridad no cierra. |
| 3 | **cobertura bidireccional** | queda un requisito en alcance sin fila, o una fila sin requisito. |
| 4 | **campos obligatorios presentes** | falta una columna o sobra una; un valor cae fuera de los enums; una fila no tiene registro de baseline, o el registro no tiene `commit` y `timestamp`; un `GREEN_ALREADY` sin `adjudicación` o un `NOT_APPLICABLE` sin `justificación`. |
| 5 | **baseline resuelto en toda fila** | alguna fila quedó sin estado, o en `BLOCKED`. |

Una tabla presente pero incompleta, sin congelar, o con baseline pendiente **no habilita el
dispatch**. Es la diferencia entre cumplir esto documentalmente y cumplirlo en operación: un gate que
solo comprueba que la tabla exista se satisface con una tabla vacía.

### `BLOCKED` no despacha, y no se reclasifica

Una sola fila en `BLOCKED` al momento del gate **detiene el dispatch**. `BLOCKED` significa que no se
pudo establecer el punto de partida, y despachar así es delegar un requisito sin criterio de "hecho":
cuando el implementador entregue, no habrá con qué decidir si esa fila quedó cumplida.

**Un impedimento ambiental no habilita reclasificar.** La fila conserva `BLOCKED` hasta que el
impedimento se resuelva, o se eleva a `DESIGN_GAP` si resulta irresoluble. `NOT_APPLICABLE` procede
**solo** cuando ejecutar un baseline es *semánticamente* inaplicable al tipo de evidencia — nunca por
indisponibilidad del entorno.

Sin esa restricción, "no tengo el navegador" convierte una prueba obligatoria en `NOT_APPLICABLE`: el
requisito sigue en alcance, la fila deja de exigir nada, y el contrato quedó ablandado por la vía más
barata que existe. Es el mismo ablandamiento que las invariantes entre versiones impiden, entrando
por la otra puerta.

### Bloques de validación

Los predicados de arriba, escritos como comandos. Cada bloque declara su **predicado** en una línea,
y esa línea es idéntica en las dos variantes de shell: es contra el predicado escrito que se
comparan, no comando por comando —`awk -F'|'` y `-split '\|'` no son "el mismo comando" y sí son la
misma comprobación—.

Tres de los bloques operan sobre la **versión vigente** y la extraen ellos mismos: un bloque que
dependiera de que quien lo corre haya recortado el documento antes se pondría verde sobre el recorte
equivocado.

```bash
# @bloque:contrato-esquema
# Predicado: la tabla tiene las seis columnas normativas, en ese orden, y todo valor de Evidencia y
# de Baseline cae dentro de su enum cerrado.
# Entradas: $contrato
t=$(mktemp -d); rc=0
CAB='| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |'
n=$(grep -oE '^#+ v[0-9]+$' "$contrato" | grep -oE '[0-9]+' | sort -n | tail -1)
awk -v n="$n" '
  /^`{3}/ { f = !f }
  !on && !f && $0 ~ "^#+ v" n "$" { lv = index($0, " ") - 1; on = 1; next }
  on && !f && /^#+ / { if (index($0, " ") - 1 <= lv) exit }
  on' "$contrato" > "$t/vig"
grep -E '^\|' "$t/vig" | grep -vE '^\|[[:space:]]*(ID[[:space:]]*\||[-: |]+\|)' > "$t/filas"

grep -qxF "$CAB" "$t/vig" || { echo "GUARD:esquema-tabla cabecera no normativa" >&2; rc=1; }
awk -F'|' 'NF!=8{print "  "$2": "NF-2" columnas"}' "$t/filas" > "$t/e"
[ -s "$t/e" ] && { echo "GUARD:esquema-tabla columnas fuera del esquema" >&2; cat "$t/e" >&2; rc=1; }
awk -F'|' 'NF==8{gsub(/^ +| +$/,"",$4)
  if ($4!="test"&&$4!="build"&&$4!="inspección"&&$4!="manual") print "  "$2": Evidencia="$4}' \
  "$t/filas" > "$t/e"
[ -s "$t/e" ] && { echo "GUARD:esquema-tabla enum de Evidencia" >&2; cat "$t/e" >&2; rc=1; }
awk -F'|' 'NF==8{gsub(/^ +| +$/,"",$7)
  if ($7!="RED"&&$7!="GREEN_ALREADY"&&$7!="NOT_APPLICABLE"&&$7!="BLOCKED") print "  "$2": Baseline="$7}' \
  "$t/filas" > "$t/e"
[ -s "$t/e" ] && { echo "GUARD:esquema-tabla enum de Baseline" >&2; cat "$t/e" >&2; rc=1; }
rm -rf "$t"; exit $rc
# @fin:contrato-esquema
```

```powershell
# @bloque:contrato-esquema-ps
# Predicado: la tabla tiene las seis columnas normativas, en ese orden, y todo valor de Evidencia y
# de Baseline cae dentro de su enum cerrado.
# Entradas: $contrato
$rc = 0
$cab = '| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |'
$doc = Get-Content -LiteralPath $contrato
$n   = ($doc | Select-String -Pattern '^#+ v(\d+)$' | ForEach-Object { [int]$_.Matches.Groups[1].Value } | Measure-Object -Maximum).Maximum
$vig = @(); $on = $false; $f = $false; $lv = 0
foreach ($l in $doc) {
  if ($l -match '^`{3}') { $f = -not $f }
  if (-not $on -and -not $f -and $l -match "^#+ v$n$") { $lv = $l.IndexOf(' '); $on = $true; continue }
  if ($on -and -not $f -and $l -match '^#+ ' -and $l.IndexOf(' ') -le $lv) { break }
  if ($on) { $vig += $l }
}
$filas = $vig | Where-Object { $_ -match '^\|' -and $_ -notmatch '^\|\s*(ID\s*\||[-: |]+\|)' }
if ($vig -notcontains $cab) { Write-Error 'GUARD:esquema-tabla cabecera no normativa'; $rc = 1 }
foreach ($f in $filas) {
  $c = $f -split '\|'
  if ($c.Count -ne 8) { Write-Error "GUARD:esquema-tabla columnas fuera del esquema: $($c[1].Trim())"; $rc = 1; continue }
  if ($c[3].Trim() -notin @('test','build','inspección','manual')) { Write-Error "GUARD:esquema-tabla enum de Evidencia: $($c[3].Trim())"; $rc = 1 }
  if ($c[6].Trim() -notin @('RED','GREEN_ALREADY','NOT_APPLICABLE','BLOCKED')) { Write-Error "GUARD:esquema-tabla enum de Baseline: $($c[6].Trim())"; $rc = 1 }
}
exit $rc
# @fin:contrato-esquema-ps
```

```bash
# @bloque:contrato-cobertura
# Predicado: todo requisito en alcance tiene al menos una fila, y toda fila referencia un requisito
# en alcance. Las dos direcciones se reportan por separado.
# Entradas: $contrato $reqs (un identificador de requisito por línea)
t=$(mktemp -d); rc=0
n=$(grep -oE '^#+ v[0-9]+$' "$contrato" | grep -oE '[0-9]+' | sort -n | tail -1)
awk -v n="$n" '
  /^`{3}/ { f = !f }
  !on && !f && $0 ~ "^#+ v" n "$" { lv = index($0, " ") - 1; on = 1; next }
  on && !f && /^#+ / { if (index($0, " ") - 1 <= lv) exit }
  on' "$contrato" > "$t/vig"
grep -E '^\|' "$t/vig" | grep -vE '^\|[[:space:]]*(ID[[:space:]]*\||[-: |]+\|)' \
  | awk -F'|' '{gsub(/^ +| +$/,"",$3); split($3,p," "); if (p[1]!="") print p[1]}' \
  | sort -u > "$t/citados"
sort -u "$reqs" > "$t/alcance"

comm -23 "$t/alcance" "$t/citados" > "$t/e"
[ -s "$t/e" ] && { printf 'GUARD:cobertura-bidireccional requisito en alcance sin fila: %s\n' \
  "$(tr '\n' ' ' < "$t/e")" >&2; rc=1; }
comm -13 "$t/alcance" "$t/citados" > "$t/e"
[ -s "$t/e" ] && { printf 'GUARD:cobertura-bidireccional fila sin requisito en alcance: %s\n' \
  "$(tr '\n' ' ' < "$t/e")" >&2; rc=1; }
rm -rf "$t"; exit $rc
# @fin:contrato-cobertura
```

```powershell
# @bloque:contrato-cobertura-ps
# Predicado: todo requisito en alcance tiene al menos una fila, y toda fila referencia un requisito
# en alcance. Las dos direcciones se reportan por separado.
# Entradas: $contrato $reqs (un identificador de requisito por línea)
$rc = 0
$doc = Get-Content -LiteralPath $contrato
$n   = ($doc | Select-String -Pattern '^#+ v(\d+)$' | ForEach-Object { [int]$_.Matches.Groups[1].Value } | Measure-Object -Maximum).Maximum
$vig = @(); $on = $false; $f = $false; $lv = 0
foreach ($l in $doc) {
  if ($l -match '^`{3}') { $f = -not $f }
  if (-not $on -and -not $f -and $l -match "^#+ v$n$") { $lv = $l.IndexOf(' '); $on = $true; continue }
  if ($on -and -not $f -and $l -match '^#+ ' -and $l.IndexOf(' ') -le $lv) { break }
  if ($on) { $vig += $l }
}
$citados = $vig | Where-Object { $_ -match '^\|' -and $_ -notmatch '^\|\s*(ID\s*\||[-: |]+\|)' } |
  ForEach-Object { ($_ -split '\|')[2].Trim() -split '\s+' | Select-Object -First 1 } |
  Where-Object { $_ } | Sort-Object -Unique
$alcance = Get-Content -LiteralPath $reqs | Where-Object { $_ } | Sort-Object -Unique

$sinFila = $alcance | Where-Object { $_ -notin $citados }
if ($sinFila) { Write-Error "GUARD:cobertura-bidireccional requisito en alcance sin fila: $($sinFila -join ' ')"; $rc = 1 }
$huerfanas = $citados | Where-Object { $_ -notin $alcance }
if ($huerfanas) { Write-Error "GUARD:cobertura-bidireccional fila sin requisito en alcance: $($huerfanas -join ' ')"; $rc = 1 }
exit $rc
# @fin:contrato-cobertura-ps
```

```bash
# @bloque:contrato-invariantes
# Predicado: entre versiones consecutivas el conjunto de ID no cambia, y para cada ID tampoco
# cambian Requisito ni Esperado. Se comparan POR ID, nunca por posición.
# Entradas: $contrato
t=$(mktemp -d); rc=0
vs=$(grep -oE '^#+ v[0-9]+$' "$contrato" | grep -oE '[0-9]+' | sort -n)
for v in $vs; do
  awk -v n="$v" '
    /^`{3}/ { f = !f }
    !on && !f && $0 ~ "^#+ v" n "$" { lv = index($0, " ") - 1; on = 1; next }
    on && !f && /^#+ / { if (index($0, " ") - 1 <= lv) exit }
    on' "$contrato" \
    | grep -E '^\|' | grep -vE '^\|[[:space:]]*(ID[[:space:]]*\||[-: |]+\|)' \
    | awk -F'|' '{gsub(/^ +| +$/,"",$2); gsub(/^ +| +$/,"",$3); gsub(/^ +| +$/,"",$6)
                  print $2"\t"$3"\t"$6}' | sort > "$t/v$v"
done
prev=''
for v in $vs; do
  [ -n "$prev" ] || { prev=$v; continue; }
  cut -f1 "$t/v$prev" > "$t/ida"; cut -f1 "$t/v$v" > "$t/idb"
  cmp -s "$t/ida" "$t/idb" || {
    printf 'GUARD:ids-invariantes el conjunto de ID cambia entre v%s y v%s\n' "$prev" "$v" >&2
    rc=1; }
  join -t"$(printf '\t')" -j1 "$t/v$prev" "$t/v$v" 2>/dev/null \
    | awk -F'\t' '$2!=$4 || $3!=$5 {print "  "$1}' > "$t/e"
  [ -s "$t/e" ] && { printf 'GUARD:requisito-esperado-invariantes cambian entre v%s y v%s:\n' \
    "$prev" "$v" >&2; cat "$t/e" >&2; rc=1; }
  prev=$v
done
rm -rf "$t"; exit $rc
# @fin:contrato-invariantes
```

```powershell
# @bloque:contrato-invariantes-ps
# Predicado: entre versiones consecutivas el conjunto de ID no cambia, y para cada ID tampoco
# cambian Requisito ni Esperado. Se comparan POR ID, nunca por posición.
# Entradas: $contrato
$rc = 0
$doc = Get-Content -LiteralPath $contrato
$vs  = $doc | Select-String -Pattern '^#+ v(\d+)$' | ForEach-Object { [int]$_.Matches.Groups[1].Value } | Sort-Object
function Get-Filas($doc, $n) {
  $vig = @(); $on = $false; $f = $false; $lv = 0
  foreach ($l in $doc) {
    if ($l -match '^`{3}') { $f = -not $f }
    if (-not $on -and -not $f -and $l -match "^#+ v$n$") { $lv = $l.IndexOf(' '); $on = $true; continue }
    if ($on -and -not $f -and $l -match '^#+ ' -and $l.IndexOf(' ') -le $lv) { break }
    if ($on) { $vig += $l }
  }
  $h = @{}
  $vig | Where-Object { $_ -match '^\|' -and $_ -notmatch '^\|\s*(ID\s*\||[-: |]+\|)' } | ForEach-Object {
    $c = $_ -split '\|'; $h[$c[1].Trim()] = @($c[2].Trim(), $c[5].Trim())
  }
  $h
}
$prev = $null
foreach ($v in $vs) {
  if ($null -eq $prev) { $prev = $v; continue }
  $a = Get-Filas $doc $prev; $b = Get-Filas $doc $v
  if (Compare-Object ($a.Keys | Sort-Object) ($b.Keys | Sort-Object)) {
    Write-Error "GUARD:ids-invariantes el conjunto de ID cambia entre v$prev y v$v"; $rc = 1
  }
  foreach ($k in $a.Keys) {
    if ($b.ContainsKey($k) -and (($a[$k][0] -ne $b[$k][0]) -or ($a[$k][1] -ne $b[$k][1]))) {
      Write-Error "GUARD:requisito-esperado-invariantes cambian entre v$prev y v${v}: $k"; $rc = 1
    }
  }
  $prev = $v
}
exit $rc
# @fin:contrato-invariantes-ps
```

```bash
# @bloque:contrato-cadena
# Predicado: las versiones son consecutivas desde v1, y para cada una hash_previo es el hash de la
# anterior (vacío en v1) y hash es el SHA-256 de sus bytes canónicos.
# Entradas: $contrato
t=$(mktemp -d); rc=0
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum | cut -d' ' -f1
        else shasum -a 256 | cut -d' ' -f1; fi; }
vs=$(grep -oE '^#+ v[0-9]+$' "$contrato" | grep -oE '[0-9]+' | sort -n)

esp=1
for v in $vs; do
  [ "$v" = "$esp" ] || { printf 'GUARD:versiones-consecutivas se esperaba v%s y vino v%s\n' \
    "$esp" "$v" >&2; rc=1; }
  esp=$((v + 1))
done

anterior=''
for v in $vs; do
  # El bloque termina en el primer encabezado de nivel MENOR O IGUAL al de la versión, o en EOF.
  # Cortar solo en la próxima `#+ vN` hacía que la última versión se comiera todo lo que viniera
  # después —en un plan de sdd-flow, "Tests y build" y el "## Verify" que escribe el propio flujo—,
  # y entonces la cadena se rompía sin que nadie hubiera tocado una fila. Las cercas ``` se
  # respetan: un `# comentario` dentro de un bloque de código no es un encabezado.
  awk -v n="$v" '
    /^`{3}/ { f = !f }
    !on && !f && $0 ~ "^#+ v" n "$" { lv = index($0, " ") - 1; on = 1; print; next }
    on && !f && /^#+ / { if (index($0, " ") - 1 <= lv) exit }
    on' "$contrato" > "$t/b"
  # bytes canónicos: se vacía el VALOR de hash, se recortan espacios finales y líneas en blanco
  # del final. Sin normalizar, un editor que reescriba finales de línea rompe la cadena sin que
  # nadie haya tocado el contenido.
  sed -e 's/`hash: [^`]*`/`hash: `/' -e 's/[[:space:]]*$//' "$t/b" \
    | awk 'BEGIN{b=0} {if ($0=="") {b++} else {while (b--) print ""; b=0; print}}' > "$t/canon"
  calc=$(sha < "$t/canon")
  decl=$(grep -oE '`hash: [0-9a-f]*`' "$t/b" | head -1 | sed 's/`hash: //; s/`//')
  prev=$(grep -oE '`hash_previo: ?[0-9a-f]*`' "$t/b" | head -1 | sed 's/`hash_previo: *//; s/`//')
  [ "$decl" = "$calc" ] || { printf 'GUARD:cadena-hash v%s: hash declarado %s, recalculado %s\n' \
    "$v" "${decl:-vacío}" "$calc" >&2; rc=1; }
  [ "$prev" = "$anterior" ] || { printf 'GUARD:cadena-hash v%s: hash_previo %s, se esperaba %s\n' \
    "$v" "${prev:-vacío}" "${anterior:-vacío}" >&2; rc=1; }
  anterior=$calc
done
rm -rf "$t"; exit $rc
# @fin:contrato-cadena
```

```powershell
# @bloque:contrato-cadena-ps
# Predicado: las versiones son consecutivas desde v1, y para cada una hash_previo es el hash de la
# anterior (vacío en v1) y hash es el SHA-256 de sus bytes canónicos.
# Entradas: $contrato
$rc = 0
$doc = Get-Content -LiteralPath $contrato
$vs  = $doc | Select-String -Pattern '^#+ v(\d+)$' | ForEach-Object { [int]$_.Matches.Groups[1].Value } | Sort-Object
$esp = 1
foreach ($v in $vs) {
  if ($v -ne $esp) { Write-Error "GUARD:versiones-consecutivas se esperaba v$esp y vino v$v"; $rc = 1 }
  $esp = $v + 1
}
$anterior = ''
foreach ($v in $vs) {
  # El bloque termina en el primer encabezado de nivel MENOR O IGUAL al de la versión, o en EOF.
  # Cortar solo en la próxima `#+ vN` hacía que la última versión se comiera todo lo que viniera
  # después —en un plan de sdd-flow, "Tests y build" y el "## Verify" que escribe el propio flujo—,
  # y entonces la cadena se rompía sin que nadie hubiera tocado una fila. Las cercas ``` se
  # respetan: un `# comentario` dentro de un bloque de código no es un encabezado.
  $b = @(); $on = $false; $f = $false; $lv = 0
  foreach ($l in $doc) {
    if ($l -match '^`{3}') { $f = -not $f }
    if (-not $on -and -not $f -and $l -match "^#+ v$v$") {
      $lv = $l.IndexOf(' '); $on = $true; $b += $l; continue
    }
    if ($on -and -not $f -and $l -match '^#+ ' -and $l.IndexOf(' ') -le $lv) { break }
    if ($on) { $b += $l }
  }
  # bytes canónicos: se vacía el VALOR de hash, se recortan espacios finales y líneas en blanco
  # del final. Sin normalizar, un editor que reescriba finales de línea rompe la cadena sin que
  # nadie haya tocado el contenido.
  $canon = $b | ForEach-Object { ($_ -replace '`hash: [^`]*`', '`hash: `') -replace '\s+$', '' }
  while ($canon.Count -gt 0 -and $canon[-1] -eq '') { $canon = $canon[0..($canon.Count - 2)] }
  $bytes = [Text.Encoding]::UTF8.GetBytes(($canon -join "`n") + "`n")
  $calc  = -join ([Security.Cryptography.SHA256]::Create().ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') })
  $decl  = if ($b -join "`n" -match '`hash: ([0-9a-f]*)`')        { $Matches[1] } else { '' }
  $prev  = if ($b -join "`n" -match '`hash_previo: ?([0-9a-f]*)`') { $Matches[1] } else { '' }
  if ($decl -ne $calc)     { Write-Error "GUARD:cadena-hash v${v}: hash declarado $decl, recalculado $calc"; $rc = 1 }
  if ($prev -ne $anterior) { Write-Error "GUARD:cadena-hash v${v}: hash_previo $prev, se esperaba $anterior"; $rc = 1 }
  $anterior = $calc
}
exit $rc
# @fin:contrato-cadena-ps
```

```bash
# @bloque:contrato-baseline
# Predicado: un registro por fila, en el mismo orden y sin duplicados; todo registro con commit y
# timestamp ISO-8601; adjudicación already_satisfied en cada GREEN_ALREADY y justificación en cada
# NOT_APPLICABLE; y ninguno de esos cuatro campos aparece como columna de la tabla.
# Entradas: $contrato
t=$(mktemp -d); rc=0
n=$(grep -oE '^#+ v[0-9]+$' "$contrato" | grep -oE '[0-9]+' | sort -n | tail -1)
awk -v n="$n" '
  /^`{3}/ { f = !f }
  !on && !f && $0 ~ "^#+ v" n "$" { lv = index($0, " ") - 1; on = 1; next }
  on && !f && /^#+ / { if (index($0, " ") - 1 <= lv) exit }
  on' "$contrato" > "$t/vig"
grep -E '^\|' "$t/vig" | grep -vE '^\|[[:space:]]*(ID[[:space:]]*\||[-: |]+\|)' > "$t/filas"
grep -E '^- `id: ' "$t/vig" > "$t/regs"

# ubicación: los cuatro campos del registro no pueden ser columnas de la tabla
grep -m1 -E '^\|[[:space:]]*ID[[:space:]]*\|' "$t/vig" \
  | grep -qiE 'adjudicaci|justificaci|commit|timestamp' && {
    echo "GUARD:ubicacion-baseline un campo del registro está puesto como columna" >&2; rc=1; }

# paridad: mismo orden, misma cantidad, sin duplicados
awk -F'|' '{gsub(/^ +| +$/,"",$2); print $2}' "$t/filas" > "$t/ids-tabla"
sed -E 's/^- `id: ([^`]*)`.*/\1/' "$t/regs" > "$t/ids-reg"
if ! cmp -s "$t/ids-tabla" "$t/ids-reg"; then
  printf 'GUARD:baseline-record-parity tabla=[%s] registros=[%s]\n' \
    "$(tr '\n' ' ' < "$t/ids-tabla")" "$(tr '\n' ' ' < "$t/ids-reg")" >&2; rc=1
fi
sort "$t/ids-reg" | uniq -d > "$t/e"
[ -s "$t/e" ] && { printf 'GUARD:baseline-record-parity registro duplicado: %s\n' \
  "$(tr '\n' ' ' < "$t/e")" >&2; rc=1; }

# commit y timestamp en todo registro; adjudicación y justificación según el estado
while IFS= read -r r; do
  id=$(printf '%s' "$r" | sed -E 's/^- `id: ([^`]*)`.*/\1/')
  printf '%s' "$r" | grep -q '`commit: [0-9a-f][0-9a-f]*`' || {
    printf 'GUARD:adjudicacion-obligatoria %s: sin commit\n' "$id" >&2; rc=1; }
  printf '%s' "$r" | grep -qE '`timestamp: [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}([+-][0-9]{2}:[0-9]{2}|Z)`' || {
    printf 'GUARD:adjudicacion-obligatoria %s: timestamp no ISO-8601\n' "$id" >&2; rc=1; }
  est=$(awk -F'|' -v k="$id" 'NF==8{gsub(/^ +| +$/,"",$2); gsub(/^ +| +$/,"",$7); if ($2==k) print $7}' "$t/filas")
  case "$est" in
    GREEN_ALREADY)
      printf '%s' "$r" | grep -q '`adjudicación: already_satisfied`' || {
        printf 'GUARD:adjudicacion-obligatoria %s: GREEN_ALREADY sin adjudicación already_satisfied\n' \
          "$id" >&2; rc=1; } ;;
    NOT_APPLICABLE)
      printf '%s' "$r" | grep -q '`justificación: [^`]' || {
        printf 'GUARD:adjudicacion-obligatoria %s: NOT_APPLICABLE sin justificación\n' "$id" >&2; rc=1; } ;;
  esac
done < "$t/regs"
rm -rf "$t"; exit $rc
# @fin:contrato-baseline
```

```powershell
# @bloque:contrato-baseline-ps
# Predicado: un registro por fila, en el mismo orden y sin duplicados; todo registro con commit y
# timestamp ISO-8601; adjudicación already_satisfied en cada GREEN_ALREADY y justificación en cada
# NOT_APPLICABLE; y ninguno de esos cuatro campos aparece como columna de la tabla.
# Entradas: $contrato
$rc = 0
$doc = Get-Content -LiteralPath $contrato
$n   = ($doc | Select-String -Pattern '^#+ v(\d+)$' | ForEach-Object { [int]$_.Matches.Groups[1].Value } | Measure-Object -Maximum).Maximum
$vig = @(); $on = $false; $f = $false; $lv = 0
foreach ($l in $doc) {
  if ($l -match '^`{3}') { $f = -not $f }
  if (-not $on -and -not $f -and $l -match "^#+ v$n$") { $lv = $l.IndexOf(' '); $on = $true; continue }
  if ($on -and -not $f -and $l -match '^#+ ' -and $l.IndexOf(' ') -le $lv) { break }
  if ($on) { $vig += $l }
}
$filas = $vig | Where-Object { $_ -match '^\|' -and $_ -notmatch '^\|\s*(ID\s*\||[-: |]+\|)' }
$regs  = $vig | Where-Object { $_ -match '^- `id: ' }
$cab   = $vig | Where-Object { $_ -match '^\|\s*ID\s*\|' } | Select-Object -First 1
if ($cab -match '(?i)adjudicaci|justificaci|commit|timestamp') {
  Write-Error 'GUARD:ubicacion-baseline un campo del registro está puesto como columna'; $rc = 1
}
# El `@()` no es cosmético: una proyección sin resultados es `$null`, y `Compare-Object` lanza si
# recibe null en cualquiera de sus dos parámetros. Sin envolver, un contrato con tabla y CERO
# registros —o al revés— hacía que el bloque lanzara, siguiera, nunca tocara $rc y saliera 0: daba
# por bueno justo lo que este predicado existe para impedir.
$idsTabla = @($filas | ForEach-Object { ($_ -split '\|')[1].Trim() })
$idsReg   = @($regs  | ForEach-Object { [regex]::Match($_, '^- `id: ([^`]*)`').Groups[1].Value })
if (Compare-Object $idsTabla $idsReg -SyncWindow 0) {
  Write-Error "GUARD:baseline-record-parity tabla=[$($idsTabla -join ' ')] registros=[$($idsReg -join ' ')]"; $rc = 1
}
$dup = $idsReg | Group-Object | Where-Object Count -gt 1
if ($dup) { Write-Error "GUARD:baseline-record-parity registro duplicado: $($dup.Name -join ' ')"; $rc = 1 }
foreach ($r in $regs) {
  $id = [regex]::Match($r, '^- `id: ([^`]*)`').Groups[1].Value
  if ($r -notmatch '`commit: [0-9a-f]+`') { Write-Error "GUARD:adjudicacion-obligatoria ${id}: sin commit"; $rc = 1 }
  if ($r -notmatch '`timestamp: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)`') {
    Write-Error "GUARD:adjudicacion-obligatoria ${id}: timestamp no ISO-8601"; $rc = 1
  }
  $fila = $filas | Where-Object { ($_ -split '\|')[1].Trim() -eq $id } | Select-Object -First 1
  $est  = if ($fila) { ($fila -split '\|')[6].Trim() } else { '' }
  if ($est -eq 'GREEN_ALREADY' -and $r -notmatch '`adjudicación: already_satisfied`') {
    Write-Error "GUARD:adjudicacion-obligatoria ${id}: GREEN_ALREADY sin adjudicación already_satisfied"; $rc = 1
  }
  if ($est -eq 'NOT_APPLICABLE' -and $r -notmatch '`justificación: [^`]') {
    Write-Error "GUARD:adjudicacion-obligatoria ${id}: NOT_APPLICABLE sin justificación"; $rc = 1
  }
}
exit $rc
# @fin:contrato-baseline-ps
```

Los tres que siguen no miran el contrato sino la **bitácora del despacho**: una línea por paso, con
su actor y su timestamp. Sin ella, "el conductor derivó la tabla" y "se congeló después de aprobar"
no son comprobables — solo se vería el estado final, que es idéntico haga quien haga cada paso y en
el orden que sea.

```bash
# @bloque:gate-congelado
# Predicado: hay contrato, su tabla no tiene ninguna fila con baseline sin resolver, y la bitácora
# registra el congelamiento antes del despacho.
# Entradas: $contrato $bitacora
t=$(mktemp -d); rc=0
n=$(grep -oE '^#+ v[0-9]+$' "$contrato" 2>/dev/null | grep -oE '[0-9]+' | sort -n | tail -1)
awk -v n="$n" '
  /^`{3}/ { f = !f }
  !on && !f && $0 ~ "^#+ v" n "$" { lv = index($0, " ") - 1; on = 1; next }
  on && !f && /^#+ / { if (index($0, " ") - 1 <= lv) exit }
  on' "$contrato" 2>/dev/null > "$t/vig"
grep -E '^\|' "$t/vig" | grep -vE '^\|[[:space:]]*(ID[[:space:]]*\||[-: |]+\|)' > "$t/filas"

[ -s "$t/filas" ] || { echo "GUARD:gate-contrato-congelado el work order no trae tabla" >&2; rc=1; }
awk -F'|' 'NF==8{gsub(/^ +| +$/,"",$7); if ($7=="") print "  "$2}' "$t/filas" > "$t/e"
[ -s "$t/e" ] && { echo "GUARD:gate-contrato-congelado baseline sin resolver:" >&2; cat "$t/e" >&2; rc=1; }
grep -q '`paso: congelar`' "$bitacora" || {
  echo "GUARD:gate-contrato-congelado la bitácora no registra el congelamiento" >&2; rc=1; }
rm -rf "$t"; exit $rc
# @fin:gate-congelado
```

```powershell
# @bloque:gate-congelado-ps
# Predicado: hay contrato, su tabla no tiene ninguna fila con baseline sin resolver, y la bitácora
# registra el congelamiento antes del despacho.
# Entradas: $contrato $bitacora
$rc = 0
$doc = Get-Content -LiteralPath $contrato
$n   = ($doc | Select-String -Pattern '^#+ v(\d+)$' | ForEach-Object { [int]$_.Matches.Groups[1].Value } | Measure-Object -Maximum).Maximum
$vig = @(); $on = $false; $f = $false; $lv = 0
foreach ($l in $doc) {
  if ($l -match '^`{3}') { $f = -not $f }
  if (-not $on -and -not $f -and $l -match "^#+ v$n$") { $lv = $l.IndexOf(' '); $on = $true; continue }
  if ($on -and -not $f -and $l -match '^#+ ' -and $l.IndexOf(' ') -le $lv) { break }
  if ($on) { $vig += $l }
}
$filas = @($vig | Where-Object { $_ -match '^\|' -and $_ -notmatch '^\|\s*(ID\s*\||[-: |]+\|)' })
if ($filas.Count -eq 0) { Write-Error 'GUARD:gate-contrato-congelado el work order no trae tabla'; $rc = 1 }
foreach ($f in $filas) {
  $c = $f -split '\|'
  if ($c.Count -eq 8 -and $c[6].Trim() -eq '') { Write-Error "GUARD:gate-contrato-congelado baseline sin resolver: $($c[1].Trim())"; $rc = 1 }
}
if ((Get-Content -LiteralPath $bitacora) -notmatch '`paso: congelar`') {
  Write-Error 'GUARD:gate-contrato-congelado la bitácora no registra el congelamiento'; $rc = 1
}
exit $rc
# @fin:gate-congelado-ps
```

```bash
# @bloque:gate-blocked
# Predicado: ninguna fila queda en BLOCKED al despachar, y ninguna justificación de NOT_APPLICABLE
# alega indisponibilidad del entorno.
# Entradas: $contrato $bitacora
t=$(mktemp -d); rc=0
# Lista cerrada de marcas de indisponibilidad. Es una heurística sobre el texto, no un juez
# semántico: caza la forma en que esta excusa se escribe, no toda excusa posible. Se declara acá
# para que su alcance sea auditable en vez de quedar implícito en un regex suelto.
AMB='no hay entorno|no disponible|sin acceso|no tengo|falta el|no está instalad|no se pudo instalar'
n=$(grep -oE '^#+ v[0-9]+$' "$contrato" | grep -oE '[0-9]+' | sort -n | tail -1)
awk -v n="$n" '
  /^`{3}/ { f = !f }
  !on && !f && $0 ~ "^#+ v" n "$" { lv = index($0, " ") - 1; on = 1; next }
  on && !f && /^#+ / { if (index($0, " ") - 1 <= lv) exit }
  on' "$contrato" > "$t/vig"
grep -E '^\|' "$t/vig" | grep -vE '^\|[[:space:]]*(ID[[:space:]]*\||[-: |]+\|)' > "$t/filas"

awk -F'|' 'NF==8{gsub(/^ +| +$/,"",$7); if ($7=="BLOCKED") print "  "$2}' "$t/filas" > "$t/e"
if [ -s "$t/e" ] && grep -q '`paso: despachar`' "$bitacora"; then
  echo "GUARD:blocked-no-despacha hay filas BLOCKED y la bitácora despacha igual:" >&2
  cat "$t/e" >&2; rc=1
fi
grep -E '^- `id: ' "$t/vig" | grep -iE "\`justificación: [^\`]*($AMB)" > "$t/e"
[ -s "$t/e" ] && { echo "GUARD:blocked-no-despacha NOT_APPLICABLE justificado por el entorno:" >&2
  cat "$t/e" >&2; rc=1; }
rm -rf "$t"; exit $rc
# @fin:gate-blocked
```

```powershell
# @bloque:gate-blocked-ps
# Predicado: ninguna fila queda en BLOCKED al despachar, y ninguna justificación de NOT_APPLICABLE
# alega indisponibilidad del entorno.
# Entradas: $contrato $bitacora
$rc = 0
# Lista cerrada de marcas de indisponibilidad. Es una heurística sobre el texto, no un juez
# semántico: caza la forma en que esta excusa se escribe, no toda excusa posible.
$amb = 'no hay entorno|no disponible|sin acceso|no tengo|falta el|no está instalad|no se pudo instalar'
$doc = Get-Content -LiteralPath $contrato
$n   = ($doc | Select-String -Pattern '^#+ v(\d+)$' | ForEach-Object { [int]$_.Matches.Groups[1].Value } | Measure-Object -Maximum).Maximum
$vig = @(); $on = $false; $f = $false; $lv = 0
foreach ($l in $doc) {
  if ($l -match '^`{3}') { $f = -not $f }
  if (-not $on -and -not $f -and $l -match "^#+ v$n$") { $lv = $l.IndexOf(' '); $on = $true; continue }
  if ($on -and -not $f -and $l -match '^#+ ' -and $l.IndexOf(' ') -le $lv) { break }
  if ($on) { $vig += $l }
}
$filas    = @($vig | Where-Object { $_ -match '^\|' -and $_ -notmatch '^\|\s*(ID\s*\||[-: |]+\|)' })
$bloqueadas = @($filas | Where-Object { ($_ -split '\|')[6].Trim() -eq 'BLOCKED' })
$bit = Get-Content -LiteralPath $bitacora
if ($bloqueadas.Count -gt 0 -and ($bit -match '`paso: despachar`')) {
  Write-Error "GUARD:blocked-no-despacha hay filas BLOCKED y la bitácora despacha igual: $((($bloqueadas | ForEach-Object { ($_ -split '\|')[1].Trim() })) -join ' ')"
  $rc = 1
}
$malJustificadas = @($vig | Where-Object { $_ -match '^- `id: ' -and $_ -match "``justificación: [^``]*($amb)" })
if ($malJustificadas.Count -gt 0) {
  Write-Error 'GUARD:blocked-no-despacha NOT_APPLICABLE justificado por el entorno'; $rc = 1
}
exit $rc
# @fin:gate-blocked-ps
```

```bash
# @bloque:gate-modo-directo
# Predicado: el conductor deriva la tabla y ejecuta el baseline, el usuario aprueba en el kickoff
# antes de que se congele, el congelamiento precede al despacho, y el orden de los timestamps
# coincide con el orden en que la bitácora los lista.
# Entradas: $bitacora
rc=0
# El orden se decide por TIMESTAMP, no por posición: la posición es fácil de conservar mientras se
# reescribe cuándo pasó cada cosa. Y se exige que las dos coincidan, porque una bitácora cuyo orden
# de líneas contradice sus propios timestamps no es evidencia de ningún orden.
# Comparación léxica de ISO-8601: vale porque una bitácora usa un solo huso.
ts() { grep "\`paso: $1\`" "$bitacora" | head -1 | sed -E 's/.*`timestamp: ([^`]*)`.*/\1/'; }
actor() { grep "\`paso: $1\`" "$bitacora" | head -1 | sed -E 's/.*`actor: ([^`]*)`.*/\1/'; }

for p in derivar-tabla ejecutar-baseline; do
  a=$(actor "$p")
  [ "$a" = conductor ] || { printf 'GUARD:conductor-deriva-y-baseline "%s" lo hizo "%s"\n' \
    "$p" "${a:-nadie}" >&2; rc=1; }
done

sed -n 's/.*`timestamp: \([^`]*\)`.*/\1/p' "$bitacora" > "$$.ord"
sort "$$.ord" | cmp -s - "$$.ord" || {
  echo "GUARD:kickoff-antes-de-congelar la bitácora lista los pasos fuera del orden de sus timestamps" >&2
  rc=1; }
rm -f "$$.ord"

kick=$(ts aprobar-kickoff); cong=$(ts congelar); desp=$(ts despachar)
if [ -z "$kick" ] || [ -z "$cong" ] || [ "$kick" \> "$cong" ]; then
  echo "GUARD:kickoff-antes-de-congelar el kickoff no aprobó antes de congelar" >&2; rc=1
fi
if [ -n "$desp" ] && { [ -z "$cong" ] || [ "$cong" \> "$desp" ]; }; then
  echo "GUARD:congelar-antes-de-despachar se despachó sin congelar antes" >&2; rc=1
fi
exit $rc
# @fin:gate-modo-directo
```

```powershell
# @bloque:gate-modo-directo-ps
# Predicado: el conductor deriva la tabla y ejecuta el baseline, el usuario aprueba en el kickoff
# antes de que se congele, el congelamiento precede al despacho, y el orden de los timestamps
# coincide con el orden en que la bitácora los lista.
# Entradas: $bitacora
$rc  = 0
$bit = Get-Content -LiteralPath $bitacora
# El orden se decide por TIMESTAMP, no por posición: la posición es fácil de conservar mientras se
# reescribe cuándo pasó cada cosa. Y se exige que las dos coincidan, porque una bitácora cuyo orden
# de líneas contradice sus propios timestamps no es evidencia de ningún orden.
# Comparación léxica de ISO-8601: vale porque una bitácora usa un solo huso.
function Ts($p)  { foreach ($l in $bit) { if ($l -match "``paso: $p``" -and $l -match '`timestamp: ([^`]*)`') { return $Matches[1] } }; return '' }
function Act($p) { foreach ($l in $bit) { if ($l -match "``paso: $p``" -and $l -match '`actor: ([^`]*)`')     { return $Matches[1] } }; return '' }

foreach ($p in @('derivar-tabla', 'ejecutar-baseline')) {
  $a = Act $p
  if ($a -ne 'conductor') { Write-Error "GUARD:conductor-deriva-y-baseline `"$p`" lo hizo `"$a`""; $rc = 1 }
}
$ord = @($bit | ForEach-Object { if ($_ -match '`timestamp: ([^`]*)`') { $Matches[1] } })
if (Compare-Object $ord ($ord | Sort-Object) -SyncWindow 0) {
  Write-Error 'GUARD:kickoff-antes-de-congelar la bitácora lista los pasos fuera del orden de sus timestamps'
  $rc = 1
}
$kick = Ts 'aprobar-kickoff'; $cong = Ts 'congelar'; $desp = Ts 'despachar'
if ($kick -eq '' -or $cong -eq '' -or ([string]::Compare($kick, $cong) -gt 0)) {
  Write-Error 'GUARD:kickoff-antes-de-congelar el kickoff no aprobó antes de congelar'; $rc = 1
}
if ($desp -ne '' -and ($cong -eq '' -or ([string]::Compare($cong, $desp) -gt 0))) {
  Write-Error 'GUARD:congelar-antes-de-despachar se despachó sin congelar antes'; $rc = 1
}
exit $rc
# @fin:gate-modo-directo-ps
```
