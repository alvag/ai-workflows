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

**Dialecto restringido: ninguna celda admite barras verticales.** Cada `|` se interpreta como un
separador de columna; escribir `\|` no lo escapa para este parser y también divide la fila. Por eso
la cardinalidad no se puede preservar agregando barras invertidas.

Cuando un comando usaría esa sintaxis, debe reescribirse sin barras verticales:

- en una alternancia, **repetir el patrón sin alternancia** o repetir el flag que lo recibe;
- en un pipeline de shell, usar una opción nativa que haga innecesaria la segunda etapa, o pasar los
  datos mediante redirección a un archivo intermedio y encadenar las etapas con `&&`.

La reescritura no altera qué se mide: cambia `Comando/observación`, no `Requisito` ni `Esperado`.
Antes de congelar, se reescribe la fila y se vuelve a medir. Sobre un contrato ya congelado, ese
cambio es un `VERIFICATION_DEFECT` y exige una versión nueva.
Solo si la reparación exige cambiar `Requisito` o `Esperado` se vuelve al diseño como
`DESIGN_GAP`. Un comando que conserve una barra vertical no se puede incorporar al contrato, ni
directa ni indirectamente.

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
| `observado` | el observable de la corrida que produjo el baseline. |
| `adjudicación` | por qué un `GREEN_ALREADY` cuenta igual. Solo en filas con ese estado. |
| `justificación` | por qué un baseline es inaplicable. Solo en filas `NOT_APPLICABLE`. |

**Los cinco últimos no son columnas de la tabla, y no pueden serlo.** La tabla describe la
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

- `id: V1` · `commit: 4f2a9c1` · `timestamp: 2026-07-31T09:14:00-03:00` · `observado: exit 1; 1 failed, 0 passed`
- `id: V2` · `commit: 4f2a9c1` · `timestamp: 2026-07-31T09:14:12-03:00` · `observado: exit 1; 0`
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

**`observado` es obligatorio en `RED` y `GREEN_ALREADY`.** Ambos estados afirman que la comprobación
se ejecutó; no se exige en `NOT_APPLICABLE` ni en `BLOCKED`, porque el primero declara que no hay
medición semánticamente aplicable y el segundo que no se pudo establecerla. En evidencia `test`,
`build` o `inspección`, el valor abre con `exit <entero>;`, donde `<entero>` sigue el dominio
`-?[0-9]+`: el signo opcional conserva el código negativo de un proceso terminado por señal. En
evidencia `manual` no hay proceso del que leer un código, así que el valor es la observación en texto
y la forma ejecutable ahí se **rechaza**: copiada del marcador de la plantilla o de la fila de al
lado, sería el único cuadrante sin ninguna forma exigida.

**La forma se exige donde el campo se exige, y no más allá.** En `NOT_APPLICABLE` y `BLOCKED` un valor
presente es una nota, no una medición: pedirle un código de salida contradiría el mismo párrafo que
dice que ahí el campo no se exige.

**Lo que este campo compra, dicho sin exagerar.** El validador comprueba **presencia y forma**, y
nada más. No comprueba que el estado sea coherente con el código —una inspección puede salir con cero
y no coincidir con el valor que espera—, y tampoco comprueba que el texto provenga de la corrida que
`commit` y `timestamp` describen: quien escribe un `RED` de memoria puede escribir un observable
plausible al lado con el mismo esfuerzo. Lo que cambia es el **costo** de fabricarlo y la superficie
donde la mentira queda escrita, no la imposibilidad de mentir. Es la misma distinción que gobierna el
sellado en este documento —integridad no es contenido—, y decirla acá evita que la regla prometa una
garantía que su guarda no da.

**Un contrato congelado antes de esta regla se repara re-midiendo, no volviendo al diseño.** El
registro lleva `commit` justamente para eso: el código que se midió sigue disponible, y
`ownership.md` → «Re-baseline en worktree aislado» es el procedimiento que lo recupera —
`git worktree add --detach` sobre ese SHA, se ejecuta solo esa fila, se captura el observable—. Es
`VERIFICATION_DEFECT`, no `DESIGN_GAP`: el requisito está intacto y lo que falta es un campo de la
medición, que es exactamente lo que esa clase existe para resolver. Lo prohibido es **reconstruir el
observable de memoria**; re-ejecutar la fila sobre el commit que su propio registro declara no es
reconstruirlo, es medirlo.

**Todo registro lleva `commit` y `timestamp`**, resuelto o no el estado. El `commit` es lo que
convierte "antes" en algo verificable: sin él, un baseline leído más tarde no dice qué código midió.
El `timestamp`, en ISO-8601, ordena las mediciones y delata la copiada de una versión anterior en
vez de re-ejecutada.

```markdown
- `id: V3` · `commit: 4f2a9c1` · `timestamp: 2026-07-31T09:15:03-03:00` · `adjudicación: already_satisfied` · `observado: exit 0; 1 passed`
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

### Pertinencia: poder discriminante por fila

La **pertinencia** exige que la observación de cada fila distinga la afirmación de su requisito de
su negación. Ese es el poder discriminante de la fila; la existencia del mapeo entre requisito y
fila no lo garantiza.

Compartir sujeto es necesario y no suficiente. Si el requisito afirma que *la emisión lleva el
identificador normalizado*, una fila que solo observa que se invoca la emisión comparte el sujeto,
pero su resultado puede cumplirse sin que la emisión lleve ese identificador.

La unidad de comparación es la **subafirmación declarada** por la fila. Cada fila declara qué parte
del requisito discrimina y se evalúa contra esa subafirmación; el conjunto cierra cuando la unión de
las subafirmaciones declaradas cubre la afirmación entera. Así, ante un requisito `A ∧ B`, una fila
puede discriminar `A` sin pretender discriminar por sí sola el requisito completo.

Al evaluar la pertinencia hay **dos cosas que establecer y un solo test**:

1. cargar el requisito **autoritativo** desde su sede, no la paráfrasis de la columna `Requisito`;
2. identificar qué observa la combinación de `Comando/observación` **más** `Esperado`.

Con esos dos insumos se aplica un único contrafactual: *¿puede cumplirse el `Esperado` mientras la
afirmación del requisito es falsa?* Si la respuesta es sí, la fila no es pertinente. El mismo test
se aplica cuando `Comando/observación` contiene una observación sin comando.

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

#### Reparación de una fila no pertinente

Si el gate de «Pertinencia: poder discriminante por fila» encuentra una fila no pertinente, la
reparación depende del momento y de los campos que sea necesario cambiar:

| Momento o cambio necesario | Clasificación y salida |
|---|---|
| Antes de congelar | Reescribir la fila y volver a medirla. |
| Ya congelada; alcanza con cambiar `Comando/observación` **o** `Evidencia` | `VERIFICATION_DEFECT`: emitir una versión nueva. Son exactamente los campos que las invariantes autorizan a cambiar. |
| Ya congelada; hay que cambiar `Requisito` o `Esperado` | `DESIGN_GAP`: volver al diseño. |
| Ya congelada; hay que agregar o quitar un `ID` | `DESIGN_GAP`: volver al gate de diseño, porque el conjunto de `ID` es invariante entre versiones. |

Un contrato congelado antes de esta regla no necesita discriminador: si su gate encuentra una fila
no pertinente, la reparación entra por esta misma matriz.

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

**Nada de esto se implementa a mano.** Ejecutar
`python_skill <skill_dir>/scripts/contrato-cadena.py <contrato>`: el script recorta cada versión por
la frontera de arriba, canoniza y compara los dos hashes. Sus tests durables calculan los hashes
esperados con una implementación independiente. **Ante cualquier discrepancia entre esta descripción
y el script, manda el script:** la descripción existe para explicar su efecto, no para reescribirlo.

**Lo que esto detecta:** una edición retroactiva que no recalculó la cadena.

**Lo que explícitamente NO prueba:** que una versión vieja no haya sido editada. Quien edita `v1` y
recalcula la cadena obtiene un documento válido, y no hay ancla externa que lo desmienta: el
contrato vive junto al plan, en un directorio **local y untracked**, así que el commit que cada
registro anota contiene el código evaluado, **nunca los bytes del contrato**. Cualquier redacción
que prometa inmutabilidad demostrable acá sería falsa.

Por eso la defensa real contra el ablandamiento no es esta cadena, sino las dos invariantes de
arriba. La cadena es una comprobación de integridad barata, no una garantía de historia.

### Contrato en work orders sin flujo SDD

Cuando el work order es un `.plans/<id>/` de `sdd-flow`, el contrato ya viene escrito y congelado por
`sdd-flow/reference.md` → "Producción del contrato de verificación". Cuando **no** lo es —un
`PLAN.md`, un equivalente, o un contrato destilado de la conversación en modo directo— no hay flujo
que lo produzca, y el reparto de responsabilidades es este:

| # | Quién | Qué | Por qué no otro |
|---|---|---|---|
| 1 | el conductor | **deriva** la tabla del work order según «Pertinencia: poder discriminante por fila» | pedirle al implementador que derive sus propias comprobaciones lo pone a calificar su propio trabajo, y borra lo único contra lo que el gate podía contrastar su entrega. |
| 2 | el conductor | **ejecuta el baseline**, sobre el código sin el cambio | delegarlo tiene el mismo defecto y además es imposible después: una vez despachado, el árbol ya contiene el diff y "antes" dejó de existir. |
| 3 | el usuario | **aprueba** la tabla, junto con el work order, en el gate de kickoff que esta skill ya tiene | no hay derivación implícita: un contrato que nadie aprobó no es un contrato, es una lista que escribió el conductor. |
| 4 | el conductor | **congela** inmediatamente después de esa aprobación y **antes** del dispatch | congelar antes de aprobar vuelve el gate un trámite sobre algo ya cerrado; despachar sin congelar deja el contrato editable mientras corre la implementación, que es justamente cuando aparece la tentación de ablandarlo. |

El **orden es parte de la regla**, no una sugerencia de redacción: derivar → medir el baseline →
aprobar → congelar → despachar. Cada paso fuera de lugar rompe una garantía distinta, así que
ninguno de los cuatro se comprueba mirando solo el resultado final.

Al **derivar** cada fila se aplica el test de «Pertinencia: poder discriminante por fila».

Sin gate de kickoff no hay aprobación posible y el modo directo no despacha: la salida no es
congelar igual, es no despachar.

### `proof_cmd` frente al contrato

`proof_cmd` existía antes que este contrato y **se conserva**, con un papel acotado: es la **lista
ordenada** de comprobaciones **agregadas y opcionales** —la suite completa, el build, el linter— que
el conductor corre para ver el conjunto de un vistazo tras cada ronda.

Lo que **no** son:

- **Ninguna de las comprobaciones agregadas** sustituye una fila del contrato. Vale para cada una y
  para todas juntas: que sean varias no cambia su rango, solo su cardinalidad.
- Ninguna alcanza para dar un requisito por cumplido, ni siquiera en verde. Lo que cierra un
  requisito es **su fila**, con su esperado y su baseline. Un `proof_cmd` entero en verde sobre un
  contrato con una fila en rojo describe una suite que no cubre ese requisito, no un requisito
  cumplido.

De ahí la asimetría del gate, que es la forma verificable de todo lo anterior:

- **contrato sin `proof_cmd`** → procede. El contrato es la evidencia.
- **`proof_cmd` sin contrato** → no procede. Es exactamente la situación que este contrato existe
  para eliminar: un comando agregado haciendo de prueba de todo.

### El gate previo al dispatch

> **Alcance de "contrato congelado".** «No se delega nada que no esté congelado» abarca **el work
> order y su tabla de verificación congelada**: un work order sin tabla, o con una tabla sin
> congelar, no se delega.

El conductor valida el contrato antes de lanzar. Seis comprobaciones; cualquiera que falle **detiene
el dispatch**, con el mismo tratamiento que el clean-tree gate: no se lanza y se reporta como gate
fallido.

| # | Comprobación | Falla cuando |
|---|---|---|
| 1 | **existe un contrato** | el work order no trae tabla. |
| 2 | **versión vigente identificada** | falta la numeración, hay un salto en la serie, o la cadena de integridad no cierra. |
| 3 | **cobertura bidireccional** | queda un requisito en alcance sin fila, o una fila sin requisito. |
| 4 | **campos obligatorios presentes** | falta una columna o sobra una; un valor cae fuera de los enums; una fila no tiene registro de baseline, o el registro no tiene `commit` y `timestamp`; una `Evidencia` cae fuera de su enum; falta `observado` en `RED` o `GREEN_ALREADY`, o el que hay no cumple la forma que su evidencia exige; un `GREEN_ALREADY` sin `adjudicación` o un `NOT_APPLICABLE` sin `justificación`. |
| 5 | **baseline resuelto en toda fila** | alguna fila quedó sin estado, o en `BLOCKED`. |
| 6 | **pertinencia** | una fila no establece los dos insumos exigidos en «Pertinencia: poder discriminante por fila»; el contrafactual responde que sí; o la unión de las subafirmaciones declaradas no cubre la afirmación entera. |

Como parte de la cuarta comprobación, ejecutar
`python_skill <skill_dir>/scripts/contrato-esquema.py <contrato>` y leer su código de salida y stderr.
La guarda valida la cabecera normativa, que cada fila tenga seis columnas y que `Evidencia` y
`Baseline` usen sus enums cerrados; su éxito no sustituye las demás validaciones de esa
comprobación. Contar columnas a ojo tampoco la sustituye: una barra dentro de una celda puede
renderizar una tabla plausible aunque la fila ya no tenga seis columnas.

En la misma comprobación, ejecutar
`python_skill <skill_dir>/scripts/contrato-baseline.py <contrato>` y leer su código de salida y stderr.
La guarda valida la paridad entre tabla y registros, y los campos que corresponden a cada estado;
su éxito tampoco sustituye las demás validaciones de esta comprobación.

La comprobación de pertinencia **no está mecanizada**. La guarda
`python_skill <skill_dir>/scripts/contrato-cobertura.py <contrato> <requisitos>` implementa la
existencia del mapeo y nada más; que pase no acredita el poder discriminante de las filas.

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
