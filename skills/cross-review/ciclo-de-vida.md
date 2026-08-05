# Ciclo de vida del finding

Contrato del **estado de cada finding** a lo largo de una corrida de revisión: su identidad, las
transiciones que puede recorrer, dónde se registran y qué presupuesto tiene cada una. Es la sede
canónica de todo eso; `SKILL.md` y `reference.md` lo citan por puntero y no lo duplican.

> **Cuándo se lee este archivo.** Ante la **primera salida conforme que traiga al menos un finding,
> cualquiera sea el veredicto**. No al primer rechazo: identidad, dedup, ledger y
> veredicto derivado gobiernan la **ingesta**, así que hacen falta apenas hay findings que ingerir,
> aunque el conductor los aplique o escale todos y no rechace ninguno. Y no "al primer `REVISE` con
> findings": el contrato admite `APPROVED` con findings `low` opcionales, y esa corrida también
> necesita todo lo de acá. Una corrida que termina en `APPROVED` **sin** findings no paga esta
> carga, que es el ahorro que este archivo separado compra.

## Identidad

**El dueño de la identidad es el conductor, no el revisor.** El ID lo **asigna y normaliza el
conductor** al ingerir la salida; el revisor **repite** los IDs que recibió para findings ya
conocidos y solo **propone** ID (`proposed_id`) para temas genuinamente nuevos — también en la
ronda 1, donde todos lo son.

**La identidad se ancla por tema, con criterio y no por string-match.** El tema es *ubicación
semántica + problema/causa*. Un finding re-emitido con otro wording, otra severidad o incluso otro
ID conserva su identidad original. La **de-duplicación por tema ocurre antes de cualquier
arbitraje**: dos emisiones del mismo tema se unifican primero y se arbitran una sola vez, nunca al
revés.

> *Fundamento:* `bitbucket-code-review/SKILL.md:427-428` — el conductor es el filtro autoritativo y
> al revisor externo no se le confía el dedup.

**Registro de identidad — solo lo que no cambia.** Cada ID tiene un registro al que las transiciones
apuntan, y contiene **únicamente** el tema y sus anclas (ubicación semántica, problema/causa, y los
`path:line` citados). Lo que varía entre emisiones —severidad, wording, sugerencia— **no** vive acá:
va al ledger, que es append-only. Un registro con campos mutables volvería a perder la secuencia que
todo esto existe para conservar.

**Clave persistida:** `(artifact_type, run_id, finding_id)`.

`artifact_type` solo **no alcanza**: el `review-log.md` es acumulativo por `<id>` de flujo, así que
`F-01` de la `spec` y `F-01` del `plan` colisionarían — pero además **dos corridas sobre el mismo
tipo comparten namespace**. Es un caso real y no hipotético: un mismo flujo puede correr dos
revisiones sobre `spec.md`, y sus findings conviven en un solo log.

**El `run_id` es de la corrida, no de la tanda.** Una corrida que cruza un checkpoint y sigue en una
tanda nueva conserva el mismo `run_id`. Generarlo por tanda conservaría la forma de la clave y haría
que **el mismo finding cambiara de identidad al cruzar el checkpoint** — dejaría de ser deduplicable
justo donde más importa.

## Estados

Enum **cerrado** de siete valores:

| Estado | Significa |
|---|---|
| `abierto` | emitido por el revisor, sin arbitrar |
| `aplicado` | el conductor lo aplicó al artefacto |
| `rechazado` | el conductor lo rechazó, con motivo registrado |
| `defendido` | **defensa registrada, admisibilidad no evaluada** |
| `reabierto` | **defensa evaluada y hallada admisible** |
| `cerrado` | resuelto sin aplicarse: aceptado el rechazo, o defensa inadmisible |
| `en-disputa` | terminal sin resolución interna; lo arbitra el humano en el gate |

`defendido` y `reabierto` son estados distintos a propósito: sin esa separación, "el revisor
defendió" y "el conductor aceptó que la defensa vale" quedarían colapsados, y la transición que
importa —quién decide la admisibilidad— sería inexpresable.

## Transiciones

Las **14 transiciones permitidas**, con su destino y su terminalidad fijados. Terminal = ninguna
transición sale de ese estado para ese finding.

| Estado origen | Evento | Actor | Destino | Terminal |
|---|---|---|---|---|
| `abierto` | aplica el finding | conductor | `aplicado` | sí |
| `abierto` | lo rechaza, con motivo | conductor | `rechazado` | no |
| `abierto` | escala (disputa genuina / decisión de producto) | conductor | `en-disputa` | sí |
| `rechazado` | acepta el rechazo | revisor | `cerrado` | sí |
| `rechazado` | lo defiende, **con presupuesto de defensa disponible** | revisor | `defendido` | no |
| `rechazado` | lo defiende, **con el presupuesto ya consumido** | revisor | `en-disputa` | sí |
| `defendido` | evalúa la defensa: **inadmisible** (sin argumento nuevo) | conductor | `cerrado` | sí |
| `defendido` | evalúa la defensa: **admisible** | conductor | `reabierto` | no |
| `reabierto` | **acepta** la defensa | conductor | `aplicado` | sí |
| `reabierto` | **sostiene** el rechazo | conductor | `en-disputa` | sí |
| `rechazado` sin respuesta | concede una tanda | humano | `rechazado` | no |
| `rechazado` sin respuesta | no concede | humano | `en-disputa` | sí |
| `aplicado` | re-emite el mismo tema **con evidencia** de que el artefacto sigue fallando (**primera vez**) | revisor | `abierto` | no |
| `aplicado` | re-emite el mismo tema con evidencia, **segunda vez** | revisor | `en-disputa` | sí |

Dos de ellas son **autocurvas**: `rechazado → rechazado` al conceder una tanda no cambia el valor
del estado, pero **sigue siendo una arista ejecutada** y se registra como tal (ver "Ledger").

**Por qué la tabla fija destinos y no solo cobertura.** Completitud no implica correctitud. Sin
fijar el destino, `defendido → aplicado` y `defendido → reabierto → cerrado` satisfacen ambos
"ninguna transición indefinida", pero solo el primero preserva que **aceptar la defensa corrige el
rechazo**.

### Regla de cierre del complemento

La tabla enumera las transiciones **permitidas**. Cualquier otro evento sobre un finding —re-emitir
uno `cerrado`, una segunda defensa sobre uno `cerrado` o `en-disputa`, o cualquier combinación no
listada— **no cambia el estado, no reabre arbitraje y no consume ronda**. Se registra en el ledger
como evento **descartado, con su motivo**, y se sigue.

**`aplicado` está excluido de este cierre.** Un finding aplicado cuya corrección **no resolvió el
problema** vuelve a `abierto` por la transición de la tabla, siempre que la re-emisión traiga
**evidencia** de que el artefacto sigue fallando. Sin esa evidencia cae en el complemento y se
descarta.

*Por qué la excepción:* el cierre existe para lo que ya se decidió sobre su mérito —un rechazo no
defendido—, no para blindar una edición del conductor. Sin ella, una corrección que no arregla nada
queda protegida por el ledger.

*Por qué una regla y no ampliar la tabla:* enumerar las combinaciones inválidas la haría crecer sin
agregar semántica, y dejaría el mismo hueco ante la primera combinación no prevista. La regla cerrada
cubre el complemento entero.

## Ledger

**El ledger append-only es el registro canónico y la única sede de escritura.** Ninguna fila se
sobrescribe nunca. Lo que se lee rápido es una **proyección derivada** del estado actual por finding,
que se **regenera al cierre de cada ronda** desde el fold determinista de todas las entradas hasta
esa ronda **inclusive**, y **nunca se edita a mano**.

*Por qué un momento y no un adjetivo:* "derivada" no dice cuándo deja de ser cierta. "Al cierre de
cada ronda" sí.

### Cuatro clases de entrada

| `tipo` | Qué registra | `finding_id` | `ronda` |
|---|---|---|---|
| `emision` | el revisor emitió el finding, con la severidad de esa vez | sí | la de emisión |
| `transicion` | **toda arista ejecutada** de la tabla, **incluidas las autocurvas** | sí | la del arbitraje |
| `descarte` | evento del complemento: no cambia estado, se registra con motivo | sí | la de emisión |
| `control-corrida` | elección o reelección del tope, y la decisión del checkpoint | **nulo** | la de la **última ronda completada** |

Una sola autoridad, no tablas paralelas: separarlas rompería la fuente única de la que se deriva el
delta.

*Por qué cuatro y no solo transiciones:* un ledger de puras transiciones no puede alojar dos cosas
que el contrato igual exige registrar — una **emisión** que no cambia estado (varias emisiones pueden
unificarse antes de un solo arbitraje, y cada una debe quedar registrada con su severidad), y la
**elección del tope**, que es un evento de la corrida y no tiene finding que lo ancle.

### Esquema de campos

Ninguna sede posterior amplía este esquema en silencio: si hace falta un campo, se declara acá.

| Ámbito | Campos |
|---|---|
| **núcleo** (toda fila) | `ronda` (entero, **acumulado de la corrida**) · `tipo` (uno de los cuatro) · `finding_id` (**nulo solo** en `control-corrida`) · `actor` (`revisor` \| `conductor` \| `humano`) · `rationale` (texto; **obligatorio** cuando el evento es un rechazo) |
| `emision` | `severidad` (`high` \| `medium` \| `low`), **obligatoria** |
| `transicion` | `origen` y `destino` (estados del enum) · `evento` (uno de los 14) · `presupuesto_consumido` (`null` \| `defensa` \| `reapertura`) |
| `descarte` | `motivo` (texto, obligatorio) y el evento descartado |
| `control-corrida` | `evento_corrida` (`eleccion-tope` \| `reeleccion-tope` \| `checkpoint`) · `tope_efectivo` (entero; obligatorio en elección y reelección) · `decision_humana` (la opción elegida, obligatoria en el checkpoint) |

**Derivaciones.** La **severidad vigente** de un finding es la de su última fila `emision` — no la
máxima histórica, y no un campo del registro de identidad. El **tope vigente** de la corrida es el
`tope_efectivo` de la última `control-corrida`.

**El checkpoint escribe dos clases, no una.** Al conceder o no conceder una tanda se persiste una
fila `transicion` **por cada finding pendiente** —con su origen, destino, ronda, actor, decisión y
rationale— **más** una `control-corrida` con `evento_corrida: checkpoint` y su `decision_humana`. La
`control-corrida` sola lleva `finding_id` nulo, así que no deja traza de **qué** rechazos se
procesaron; las `transicion` solas pierden **qué opción** abrió o cerró la tanda. Los dos errores son
simétricos y los dos rompen la reanudación.

**El ledger sobrevive a la pausa.** Entre el checkpoint y la decisión del humano puede pasar una
sesión entera; el ledger de la corrida es lo que el descriptor durable referencia para rehidratarla
(`reference.md` → "Checkpoint durable").

## Presupuestos por finding

Los presupuestos son **por finding, nunca por corrida**: si fueran globales, una sola fila
patológica consumiría el presupuesto de todas las demás. Son dos, simétricos:

- **Una sola defensa.** Si tras la defensa admisible el conductor sostiene el rechazo, el finding
  pasa a `en-disputa`. No hay segunda defensa.
- **Una sola re-apertura.** Un finding `aplicado` puede volver a `abierto` una vez, con evidencia.
  La **segunda** re-emisión sobre el mismo tema pasa a `en-disputa` sin re-arbitrar.

**Son de la vida entera del finding, no del tramo.** Se consumen una vez y **no se recargan al
cambiar de estado**. Un finding que recorrió `rechazado → defendido → reabierto → aplicado → abierto
→ rechazado` llega a ese segundo `rechazado` **sin** presupuesto de defensa, y una defensa ahí lo
lleva a `en-disputa` —registrada, sin re-arbitraje—, que es terminal. El consumo queda en el
`presupuesto_consumido` de la fila `transicion` que lo gastó; el grafo lo impone en la transición, no
solo en la prosa.

*Por qué terminal y no permanencia:* dejarlo en `rechazado` lo devolvería al conjunto de estados no
terminales, y entonces el veredicto derivado obligaría a seguir en `REVISE`, el prompt de ronda N
volvería a pedir respuesta por ese ID, y las postcondiciones del checkpoint no lo cubrirían —porque
sí hubo respuesta, no es un rechazo sin responder—. Además, una fila **listada** en la tabla no puede
caer a la vez bajo el complemento.

*Por qué el segundo presupuesto:* sin él, `abierto → aplicado → abierto → aplicado…` es legítimo en
cada paso y nada lo corta. La tanda finita evita el cuelgue, pero un solo finding puede consumirla
entera — el escenario que `cross-implement/ownership.md:42-53` usa para justificar presupuestos por
unidad.

## Vara de admisión de la defensa

Una defensa es admisible **solo con argumento nuevo**:

| Admisible | No admisible |
|---|---|
| refutar una **premisa concreta** del rationale del rechazo | el mero desacuerdo |
| aportar **evidencia del repo** que el rechazo no consideró | reformular el finding con otro wording |
| mostrar que el rechazo se apoya en un hecho falsable **que es falso** | insistir sin evidencia nueva |

**Al disputarse, el rechazo se eleva a razón falsable** — el vocabulario ya definido en
`cross-implement/ownership.md:64-75`, que se **cita y reusa, no se duplica**. Todo rechazo lleva
motivo desde la ronda 1; la vara falsable —nombrar qué observación lo tumbaría— se exige recién
cuando el finding se disputa, que es donde el loop empieza a gastar presupuesto sobre una hipótesis
que nadie escribió.

**La defensa es insumo, no autoridad.** Una defensa admisible obliga a **re-arbitrar**, no a
aceptar: el conductor sigue decidiendo, y el revisor no se vuelve árbitro por defender bien. Es la
regla 3 de `SKILL.md` aplicada al otro extremo del loop.

## Cierre

Un finding se cierra **solo** por aceptación explícita del revisor o por una defensa evaluada como
inadmisible. **Nunca por omisión**: la aceptación silenciosa permitiría cerrar findings por
truncamiento o pérdida de contexto en vez de por una decisión auditable.

Un finding `cerrado` **no se re-arbitra**, el revisor **tiene prohibido re-emitirlo**, y si reaparece
el conductor lo descarta por identidad —sin arbitrarlo y sin abrir ronda por él—. Y **permanece en el
ledger**: no se borra. La auditabilidad exige que la revisión pueda reconstruirse, y borrar lo cerrado
la rompería.

## Adopción de logs escritos con el formato anterior

Un `review-log.md` que ya existe con el formato previo a este contrato es **historial opaco e
inmutable**:

- **No se migra.** Inventaría identidad, ronda y presupuestos que nunca existieron.
- **No se sobrescribe.** Perdería la auditoría que ya está escrita.
- **Se excluye del fold.** Ninguna proyección de una corrida nueva lo lee ni deriva estado de él.

Cada corrida nueva **abre su propia sección**, identificada por formato y `run_id`, y ninguna
identidad se infiere de lo viejo. Una corrida legacy que quedó **no terminal** se termina con el
contrato anterior: no se convierte a mitad de camino.

*Por qué:* el primer uso de este contrato ocurre, por definición, sobre un repositorio donde ya hay
logs del formato viejo — incluido el de la corrida que lo introdujo.
