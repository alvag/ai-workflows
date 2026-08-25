# cross-implement — Ownership de fallas

Qué hacer cuando una fila del contrato falla: de quién es el problema, cuánto presupuesto tiene cada
clase, y qué reglas siguen rigiendo durante el takeover.

Vive en un archivo aparte de `reference.md` porque se lee en **un momento distinto**: al cerrar
cualquier bloque, no antes de delegar. La matriz de cierre aplica también a un bloque que sale bien a
la primera; las secciones de reparación se consultan solo si hubo una falla.

Al leer este archivo después de una falla, aplicar primero
`skills/cross-review/corridas-en-vuelo.md` → "Invariantes de recuperación". Esta referencia cita esa
autoridad y no duplica sus cuatro reglas.

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

### Matriz de cierre por bloque

Los tres ejes se leen por separado: `Estado` es el outcome terminal de `cross-implement`, `Causa`
solo explica un `UNAVAILABLE`, y `Clase` pertenece al `checkId` del triage de ownership. Ninguna causa
ni clase amplía el enum de estados. Las cuatro últimas columnas determinan la transición del bloque.

| Estado | Causa | Clase | Cierra | Marca tasks | Commitea | Continúa |
|---|---|---|---|---|---|---|
| `IMPLEMENTED` | — | — | Sí, si satisface la aceptación. | Sí. | Sí, commit de trabajo. | Sí. |
| `PARTIAL` | — | `IMPLEMENTATION_DEFECT` resuelto por takeover | Sí, solo si el delta final satisface la aceptación. | Sí, solo las cubiertas. | Sí, commit de trabajo. | Sí. |
| `UNAVAILABLE` | `confirmed_wall` | `ENVIRONMENT_FAILURE` | No. | No. | No. | No; se resuelve el bloque actual tras confirmar el cese. |
| `UNAVAILABLE` | `launch_flake` | `ENVIRONMENT_FAILURE` | No. | No. | No. | No; se reintenta el bloque actual dentro de su presupuesto. |
| `UNAVAILABLE` | `runtime_failure` | `IMPLEMENTATION_DEFECT` | No. | No. | No. | No; primero se clasifica y cosecha el delta. |
| `UNAVAILABLE` | `deadline_exceeded` | `ENVIRONMENT_FAILURE`; worker todavía activo o escribiendo | No. | No. | No. | No; cese incierto, la secuencia se detiene. |
| `UNAVAILABLE` | `deadline_exceeded` | `ENVIRONMENT_FAILURE`; cese confirmado | No. | No. | No. | No; se resuelve el bloque actual, no se salta al siguiente. |
| `UNAVAILABLE` | — | `DESIGN_GAP` | No. | No. | No. | No; vuelve al diseño. |

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

### Presupuestos a través de bloques

La identidad presupuestaria sigue siendo el `checkId` congelado. El conductor persiste por
`checkId` la clase, los intentos y las rondas consumidas en cada registro de invocación, y al abrir el
bloque siguiente carga el acumulado anterior; cambiar de bloque no reinicia la misma falla.

El tope de `sdd-flow` conserva su significado: **3 fallos** de la misma falla obligan a volver a
`plan`/`specify`, y ese conteo opera a través de bloques. Los presupuestos propios por clase también
persisten entre bloques según la matriz de control de flujo.

**tope de secuencia: 6 incidencias que consumen presupuesto.** Es un límite global por work order y
no crece sin cota con la cantidad de bloques. No se multiplica por el número de bloques ni abre un
presupuesto nuevo para cada dispatch; al agotarse, la secuencia se corta y aplica la matriz de cierre.

### Rollback de una secuencia

El rollback se ejecuta solo después de confirmar el cese de todo writer. Para los cortes normales,
restaura la frontera previa a los bloques y deja un registro explícito del descarte; los estados de
crash se diagnostican y recuperan mediante `skills/sdd-flow/reference.md` → “Recuperación de la
secuencia”, sin inferencias locales en esta skill.

| Corte | HEAD | Working tree | Marcas | Registros |
|---|---|---|---|---|
| Cancelación humana tras K bloques aceptados | Vuelve al ancla previa a los bloques. | Queda sin el delta de la secuencia y preserva cualquier cambio ajeno preexistente. | Las tasks de los K bloques vuelven a `[ ]`. | El recibo y los logs registran `rolled_back` y los SHAs descartados. |
| `UNAVAILABLE` o `PARTIAL` no aceptado, con cese confirmado | Vuelve al ancla y elimina los commits de trabajo locales. | Descarta el delta propio incompleto; no toca archivos ajenos. | Ninguna task del bloque cortado queda `[x]`; se restauran también las de bloques revertidos. | El outcome, la causa y la cosecha quedan registrados antes del retiro. |
| `DESIGN_GAP` o `ENVIRONMENT_FAILURE` terminal | Vuelve al ancla si hubo commits de trabajo locales. | Queda igual al estado previo a la secuencia, salvo dirty ajeno identificado. | Todas las marcas de la secuencia vuelven a su valor previo. | El corte y el presupuesto agotado permanecen auditables en recibo y logs. |
| Crash entre transiciones o durante el aplastado | HEAD queda inmóvil hasta que el clasificador identifique un cutpoint recuperable. | Solo cambia tras propuesta aprobada, cese, ownership y revalidación. | Solo las marcas correlacionadas que declare la reconciliación. | Se conserva diagnóstico, digest, intención y adjudicación según “Recuperación de la secuencia”. |

Estas postcondiciones se prometen solo para cortes normales alcanzados por la matriz. En crash,
`sdd-flow` distingue cutpoint recuperable, conflicto y bloqueo. Un owner obsoleto sin una primitiva
atómica que invalide su derecho anterior queda `blocked-manual-remediation`: no se borra el token, no
se reclama automáticamente y no se ejecuta rollback.

### Terminales de secuencia

| Terminal | Intención | Resultado | Continuable |
|---|---|---|---|
| `completed` | cerrar la secuencia con commit final | commit final creado y cierre persistido | no |
| `rolled_back` | descartar el delta de la secuencia | ancla restaurada y SHAs de trabajo descartados | no |
| `abandoned` | abandonar sin rollback tras cese confirmado | ledger retenido sin cierre persistido | no |
| `suspended` | suspender por gap de diseño | secuencia detenida con ledger vigente | sí |

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
