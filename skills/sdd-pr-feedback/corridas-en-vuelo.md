# Corridas delegadas en vuelo

**Sede canónica: `skills/cross-review/corridas-en-vuelo.md`.** Las otras seis copias —una por cada
skill que despacha— son **generadas** desde este archivo con
`python3 scripts/verificar-sobre-en-vuelo.py --sincronizar` y **no se editan a mano nunca**: una copia
editada a mano es una divergencia silenciosa, y la única defensa contra eso es que la fuente sea una
sola.

Un conductor despacha trabajo delegado, el usuario le escribe mientras ese trabajo corre, el conductor
responde a lo que se le preguntó y **deja de estar pendiente**. La continuidad de la corrida vivía en
el turno; cuando el turno se corta, no queda nada que instruya a recuperarla, y es el usuario quien
termina avisando que los workers ya terminaron. El **sobre** es lo que saca esa continuidad del turno
y la pone en disco.

**Qué es.** El sobre son los **metadatos operativos** de una corrida delegada que está ejecutándose
ahora: qué skill despachó y en qué modo, quién es el conductor propietario, qué workers salieron,
dónde escribe cada uno, por qué transporte viaja cada intento, hasta cuándo el conductor lo espera y
si la cosecha sigue pendiente. Es lo que un conductor que recupera el control necesita **releer** para
saber qué tiene en vuelo sin depender de recordarlo, y lo que una sesión que nunca vio el despacho
necesita **encontrar** para no pisarlo.

**Qué no es.** El sobre **no reconstruye el estado semántico** de la corrida. No dice en qué rama de
la escalera de degradación está, qué causa la disparó, qué decidió el árbitro, qué ronda va ganando ni
qué hallazgos se aceptaron. Todo eso vive donde ya vive —en los artefactos de cada skill, en su
registro de rondas, en su manifest— y acá no se duplica: dos definiciones del mismo hecho son dos
definiciones que pueden discrepar.

La distinción no es de estilo. **Este ecosistema rechazó por escrito el estado persistido** —máquina
de estados persistente, esquema formal, validador propio y versionado— en **una sede**, y esa
cláusula sigue vigente y sin tocar:

- `skills/co-explore/reference.md` → "El descriptor de corrida y su retiro".

Un revisor que lea esa cláusula como un bloqueo de este contrato lo estaría leyendo al revés.
Lo que rechazan es **reconstruir el avance** de una corrida leyendo un archivo; lo que el sobre
registra es **quién sigue despachado y dónde escribe**. El sobre aplica ese mecanismo
a los once puntos de despacho del ecosistema; no lo asciende a máquina de estados.

### El archivo

El sobre vive en **`.cross-model/active/<skill>/<run_id>.json`**, hermano del `runs/` donde cada
corrida deja su manifest al terminar. Los dos nombres dicen cuánto vive lo que guardan: `runs/`
acumula lo que ya pasó, y `active/` contiene únicamente lo que está en vuelo —un archivo entra cuando
el sobre nace y sale cuando se cumplen las tres condiciones del retiro—. Un solo directorio para las
dos cosas obligaría a abrir cada archivo para saber cuáles todavía importan, y el barrido dejaría de
ser barato justo cuando más falta hace: al recuperar el control, sin memoria previa.

**Un archivo por corrida, no un índice acumulado.** Es la misma razón que ya rige para el manifest:
un JSON con todas las corridas adentro obliga a leer, modificar y volver a escribir en cada
nacimiento y en cada actualización, y ese ciclo es justamente lo que la publicación por rename
atómico no puede proteger —el rename publica un archivo entero, no una entrada dentro de otro—. Con
un archivo por corrida, cada escritor único toca exactamente el suyo y nunca el de nadie más.

**La skill va en la ruta, y no como decoración.** `run_id` es un sufijo corto de corrida: dos skills
del mismo repo pueden elegir el mismo valor sin que ninguna de las dos haga nada mal. Sin `<skill>`
en la ruta, esas dos corridas comparten un único archivo físico, y la regla del escritor único no lo
evita —cada conductor es escritor único **de su sobre**, y ahí los dos sobres son el mismo archivo—.
Lo que queda son dos daños y ninguna salida buena: con el nacimiento sin reemplazo, un despacho
legítimo colisiona contra una corrida ajena y regenera su `run_id` para esquivar una ruta que estaba
ocupada por trabajo que no era suyo; con reemplazo, la segunda borra a la primera y el worker de la
primera sigue vivo sin ningún sobre que lo nombre. El segmento de skill separa los dos espacios de
nombres antes de que cualquiera de las dos cosas pueda ocurrir.

**La identidad va codificada en la ruta, no adentro del archivo.** La identidad de una corrida es la
terna `(repo, skill, run_id)`, y las tres se leen del path: el repo es aquel bajo cuyo
`.cross-model/` apareció el archivo, la skill es el directorio y el `run_id` es el nombre. Que no
haga falta abrir el JSON para saber de qué corrida se trata es lo que le permite al barrido agrupar y
desambiguar con lo que ya tiene en la mano. Deduplicar por `run_id` solo —que es la tentación, porque
es el único de los tres que parece un identificador— fundiría dos corridas reales de repos
concurrentes que eligieron el mismo sufijo, y las informaría como una.

### Los campos del sobre

Doce campos operativos en la raíz, más un par condicional de autoridades del manifest:

| campo | qué registra |
|---|---|
| `run_id` | el sufijo corto que nombra esta corrida dentro de su skill y su repo |
| `skill` | qué skill despachó, como identidad escalar |
| `mode` | el modo operativo con el que esa skill corre esta vez |
| `owner` | el conductor propietario, que es quien creó el sobre y el único que lo escribe |
| `parent` | el sobre del que este despacho es hijo, cuando el despacho es anidado; nulo si no lo es |
| `children` | los sobres que este conductor creó al despachar hacia abajo |
| `descendants_summary` | el resumen que esta corrida publica de su propia descendencia |
| `workers` | los workers **directos** de esta corrida, con sus intentos |
| `scope` | el repo y el worktree afectados por la corrida |
| `transport` | la vía por la que viaja la corrida, **derivada** de los intentos vigentes |
| `harvest_pending` | marca explícita de que la cosecha de esta corrida sigue pendiente |
| `proxima_accion` | la próxima acción que debe ejecutar el conductor cuando recupere el control |
| `manifest_seed` | seed inmutable de la proyección terminal, presente solo con manifest habilitado |
| `manifest_first_dispatch_at` | timestamp UTC write-once del primer despacho; nace en `null` |

**El par del manifest es condicional e indivisible.** La habilitación se resuelve una vez, antes de
cualquier preflight capaz de terminar la corrida. Con manifest habilitado, el sobre nace con los dos
nodos; `manifest_seed` contiene exactamente `skill`, `mode`, `preflight_started_at`, `families`,
`transport` y `selection`, mientras `manifest_first_dispatch_at` nace en `null`. El seed es inmutable.
Inmediatamente antes de la primera tool call de despacho se fija una sola vez
`manifest_first_dispatch_at`; reanudar, cosechar o cerrar no lo recalcula. Si ningún worker fue
seleccionado o no se resolvió ninguna vía de lanzamiento, permanece `null`, `workers[]` puede quedar
vacío, el `transport` operativo de la raíz es `null` y el fallback del seed para el manifest es
`none`. Si un worker seleccionado falla su preflight después de resolver la vía, no hubo despacho
pero `families` conserva ese worker y `manifest_seed.transport` conserva esa vía candidata.

Con manifest deshabilitado (**modo off**), **ambos nodos están ausentes** desde el nacimiento hasta el retiro: no
se escriben como `null`, no se vuelve a leer la configuración al retomar y no se inventa una mitad
del par. Cualquier estado con uno presente y el otro ausente, un seed con otra clave o un timestamp
modificado después de fijarse es un sobre inválido.

**`run_id` no identifica solo.** Los descriptores lo llaman "sufijo corto de corrida": dos repos
concurrentes pueden producir el mismo valor, y dos skills del mismo repo también. La identidad de una
corrida es la terna `(repo, skill, run_id)`, y por eso `skill` es un campo propio y no una decoración
del `run_id`.

**`skill` es identidad escalar y `mode` es campo propio.** Fundirlos en un solo valor —`co-explore
investigate`, `cross-review draft`— confunde la identidad de la skill con el modo operativo: el
barrido agrupa por skill, y el informe necesita el modo para decir qué se está esperando. Son dos
preguntas distintas y llevan dos campos.

**`children` lo escribe el padre al despachar, nunca la hija.** El padre sabe qué hijas crea, y este
contrato tiene un solo escritor por sobre: si la hija tuviera que anotarse en el sobre del padre,
estaría escribiendo un archivo ajeno. La consecuencia es que `children` puede quedar incompleto si el
padre muere entre el despacho y la escritura, y por eso el recorrido nunca depende de él.

**`descendants_summary` es un campo de la raíz, no una obligación en prosa.** Un conductor administra
solo sus corridas directas; de cada hija recibe **un resumen** de lo que cuelga más abajo. Si el
resumen no fuera un campo del esquema, quedaría exigido en la regla de agregación y ausente del sobre,
que es la peor combinación posible: obligatorio y sin lugar donde escribirlo.

**`transport` en la raíz es el único campo derivado del sobre.** Su valor no se escribe por decisión
propia: es el valor **común** a los intentos vigentes de todos los workers, o `mixto` cuando difieren.
Deriva hacia arriba y no hacia abajo, porque la vía es del intento —un mismo revisor va por
`cli-exec` en la primera ronda y por `cli-resume` en las siguientes, y una corrida multi-worker puede
tener intentos vigentes por ambas vías—. Un `transport` raíz que fuera autoridad en vez de resumen sería
directamente falso en cuanto un solo worker cambiara de vía.

**`harvest_pending` es una marca explícita de la corrida, no un derivado.** La tentación es calcularla
como "algún `attempts[].harvested` en falso", y rompe dos cosas. Primero, una marca raíz verdadera
dejaría de distinguir **qué** intento se cosechó y cuál no, que es justamente lo que la cosecha
parcial multi-worker necesita saber. Segundo, la marca es lo que garantiza que la cosecha ocurra **una
sola vez**: una condición calculada a partir de otros campos se puede recalcular distinto tras un
relanzamiento, y una garantía que depende de un cálculo no es una garantía.

**`proxima_accion` es una cadena opcional en la raíz.** `null` o la ausencia del campo significan
"sin acción declarada" y son casos válidos, no un estado inválido. El conductor propietario es el
único que la escribe en el sobre; cuando recupera el control, ese conductor la lee durante el barrido
de corridas activas. Al cerrar la corrida, transfiere el campo al registro de cierre junto con el resto
del sobre; la transición no depende de un tombstone. Por ejemplo, al recuperar una corrida por
`cli-exec`, el conductor transfiere `proxima_accion` del sobre activo al registro de cierre antes de
retirarlo.

**`scope` es un nodo estructurado, no un texto.** Escribir el repo y el worktree como una frase obliga
a cada consumidor a parsearla, y cada uno la parsea distinto.

### Los campos por worker

`workers[]` lista solo los workers **efectivamente despachados**. Una familia ausente que no generó
un despacho no tiene entrada en el sobre: no existe proceso que sondar, cosechar o relanzar.

Cuatro campos por cada entrada de `workers[]`:

| campo | qué registra |
|---|---|
| `name` | el nombre del worker despachado, único dentro de la corrida |
| `family` | la familia que lo atiende: Claude o GPT/Codex |
| `write` | si el worker es read-only o escritor |
| `attempts` | los intentos de este worker, en orden de despacho |

**`family` está por worker porque la corrida puede ser mixta.** El fan-out dual de `co-explore`
despacha uno por familia en la misma corrida; un panel de revisores puede repartirse entre las dos. Un
campo de familia en la raíz obligaría a elegir una y a mentir sobre la otra.

**`write` no es decorativo: decide qué se puede hacer con ese worker.** Un worker **escritor** deja
efectos en el árbol, y esos efectos valen como evidencia parcial de que algo pasó; un worker
**read-only** puede no dejar rastro alguno, y de él no hay nada que inferir. `write` es además lo que
permite bloquear un implementador nuevo mientras el anterior todavía pueda tocar el árbol: sin el
campo, habría que deducir el permiso del transporte, que no lo dice.

### Los campos por intento

Seis campos por cada entrada de `attempts[]`. **El intento, y no el worker, es la unidad que lleva
transporte, salida, proceso, presupuesto y cosecha:**

| campo | qué registra |
|---|---|
| `attempt_id` | la identidad de este intento dentro de su worker |
| `transport` | la vía por la que viaja **este** intento |
| `output` | la ruta exclusiva donde este intento escribe su salida |
| `process_ref` | la referencia consultable a su proceso, o `null` donde no hay proceso consultable |
| `wait_budget` | el presupuesto de espera de este intento |
| `harvested` | si este intento ya fue cosechado |

**Por qué cuelgan del intento y no del worker.** Cada relanzamiento y cada resume necesita **rutas
exclusivas**: si `output` y `process_ref` colgaran del worker, un relanzamiento pisaría los del
intento anterior y una salida tardía del worker viejo sería indistinguible de la del vigente —que es
exactamente lo que la regla de rutas exclusivas existe para impedir—. El `wait_budget` va con ellos
porque cada deadline corre desde el lanzamiento de **su** intento, no desde el inicio de la corrida; y
`transport` va con ellos porque la vía cambia entre intentos, y un intento que no puede nombrar su
propia vía tampoco puede nombrar su fuente ni aplicar la precedencia que le toca.

**`process_ref` es `null` donde no hay proceso consultable**, y eso es un valor legítimo, no un
agujero: un despacho por subagente del entorno no expone ningún proceso, y escribir ahí una referencia
inventada sería peor que dejarlo vacío.

**Ante frescura no comprobada, el proceso se clasifica incierto y nunca se cancela.** Un PID se
reutiliza y un identificador de sesión nombra un hilo resumible, no un proceso vigente: confundirlos
afirma una vida que no se comprobó, o cancela el proceso equivocado. La referencia sin frescura
comprobada informa; no autoriza a matar nada.

### Los sub-esquemas

Tres campos son nodos y no escalares. Sus formas canónicas, que ningún consumidor puede ampliar por su
cuenta:

- `wait_budget = {deadline, limite, consumidos}`
- `process_ref = {tipo, referencia, evidencia_de_frescura, autoridad}`
- `scope = {repo, worktree}`

**`wait_budget` es un nodo y no un instante.** Un `deadline` solo no alcanza: los transportes de este
repo cuentan **iteraciones** además de tiempo, así que el presupuesto necesita su `limite` y su
contador `consumidos`. Y el contador tiene que ser **durable**, porque un conductor que retoma la
corrida y lo reinicia extiende el presupuesto sin darse cuenta y sin que nada se lo señale. La
invariante es `consumidos ≤ limite`: el presupuesto que ya se gastó no se devuelve.

**`process_ref` lleva cuatro componentes porque una referencia sola no sirve.** El `tipo` dice qué
clase de referencia es —proceso o sesión—, la `referencia` es el identificador, la
`evidencia_de_frescura` es lo que permite creerle, y la `autoridad` dice qué peso tiene frente a las
otras superficies cuando discrepan. Sin los dos últimos, un identificador viejo se lee como prueba de
vida.

**`scope` fija dónde ocurre la corrida.** `repo` y `worktree` son sus dos campos y ningún consumidor
puede ampliarlos por su cuenta.

### Invariantes de recuperación

Estas cuatro reglas gobiernan cualquier recuperación, sin importar la vía del intento:

1. **Un deadline vencido no prueba que el proceso murió.** Solo termina la espera del conductor; el
   intento permanece incierto hasta que una fuente autorizada demuestre un terminal.
2. **No se relanza mientras el intento anterior pueda seguir escribiendo.** El nuevo despacho espera
   el cese confirmado del anterior para no superponer escritores.
3. **Cada intento usa una ruta de salida exclusiva.** Un reintento o una reanudación nunca reutiliza
   la salida de otro intento.
4. **El entorno fija si la recuperación usa aviso o sondeo.** La capacidad del conductor determina
   cómo recibe o consulta el resultado; el transporte no elige ese mecanismo.

### Varios workers en una corrida

Tres despachos lanzan **más de un worker directo**: el fan-out dual de `co-explore` —uno por familia—,
el panel de revisores externos de `bitbucket-code-review` y el fan-out por repo de `sdd-orchestrator`.
Los tres usan **un solo sobre por corrida**, con sus workers en `workers[]`, y no un sobre por worker.
El mecanismo que este contrato generaliza ya es *de la corrida*; la regla de agregación no tendría
dónde vivir si cada worker llevara archivo propio; y el barrido devolvería N archivos por una sola
corrida, que es exactamente el ruido que hace perder el hilo.

**Identidad por worker.** Cada entrada de `workers[]` lleva su `name`, único dentro de la corrida, y
ese nombre es la unidad con la que se informa, se cosecha y se relanza. Un informe que diga "el
delegado" cuando hay tres no dice nada: al usuario le falta saber cuál de los tres.

**Fuente y precedencia, también por worker.** La fuente consultable la fija el transporte del intento
vigente de **cada** worker, no el de la corrida: un panel donde un revisor va por `cli-exec` y otro por
`cli-resume` tiene dos fuentes distintas al mismo tiempo, y el `transport` raíz vale `mixto` para no
esconderlo. La precedencia ante una discrepancia se resuelve **por worker** y con su propia
combinación de proceso y artefacto; agregar antes de resolver mezcla un caso ya cerrado con otro
todavía incierto y produce un veredicto que no es cierto de ninguno de los dos.

**Qué se informa, y cómo se cosecha parcialmente.** Lo que se informa es el estado **de cada worker**,
nombrado, y no un agregado que oculte cuál falta. La cosecha es parcial por construcción: `harvested`
es del intento, así que cosechar la salida del worker A no marca al B, y `harvest_pending` en la raíz
sigue en verdadero mientras quede un worker directo sin cosechar. Un resultado cosechado no se vuelve
a cosechar aunque el resto siga en vuelo.

**Cuándo la corrida agregada deja de estar en vuelo.** Cuando **todos** sus workers directos llegaron
a un final comprobado y ninguna de sus salidas quedó sin adjudicar. Que el primero haya entregado no
la saca de vuelo, y que uno haya fallado tampoco: un worker en error es un final comprobado de ese
worker, no de la corrida. Mientras quede un solo worker sin final comprobado, la corrida sigue en
vuelo y el turno la sigue informando.

**Lo que un ancestro ve, y lo que no puede hacer.** Un conductor administra **solo sus corridas
directas**. De cada hija recibe su `descendants_summary` —cuántas corridas cuelgan más abajo, en qué
estado agregado y qué falta—, y con eso le alcanza para informar sin leer el árbol entero. Un
**ancestro** no cosecha ni retira sobres **indirectos**: no es su sobre, no es su escritor, y su
información de un nieto es un resumen que la hija publicó, no una observación propia. Si un nieto
necesita una decisión, sube por la hija que lo despachó.

### Transiciones del sobre

Cuatro transiciones, y el momento de cada una es parte del contrato:

| transición | cuándo ocurre | qué la habilita |
|---|---|---|
| `nace` | antes del preflight y del despacho, en el mismo paso que prepara la corrida | nada la precede: es la primera escritura de la corrida |
| `relee` | cada vez que el conductor recupera el control | que el sobre exista y siga activo; releer no cambia nada |
| `cosecha` | cuando hay un resultado que adjudicar | `harvest_pending` en verdadero, y una sola vez por intento |
| `retira` | al final de todo | las tres condiciones del retiro, cumplidas a la vez |

**El sobre nace antes del preflight y antes del despacho, nunca después.** Escribirlo después deja una
ventana —corta, pero real— donde un preflight puede terminar la corrida o un worker quedar ya lanzado
sin ningún archivo que lo registre: si el turno se corta ahí, la corrida
existe, está consumiendo tiempo y recursos, y no hay nada en disco que la nombre. Ese es exactamente
el modo de falla que este contrato existe para cerrar, así que el orden no es negociable: primero el
seed y el sobre, después el preflight; si habrá despacho, se fija el timestamp write-once y recién
después ocurre la tool call que lanza al worker. Un sobre que nace de más —porque el despacho falló
al lanzarse— se retira con un `error` comprobado, que es barato; un despacho sin sobre no se recupera.

**`harvest_pending` impide una segunda cosecha.** Cosechar es adjudicar un resultado: leerlo,
incorporarlo y darlo por consumido. Hacerlo dos veces duplica hallazgos, vuelve a contar una ronda ya
contada o reaplica un cambio ya aplicado, y ninguna de esas tres se nota al momento. La marca es lo
que lo impide, y por eso está escrita y no calculada: `harvested` es del intento y bloquea la segunda
lectura de esa salida; `harvest_pending` es de la corrida y solo dice si queda algo por cosechar.

**Un solo escritor: el creador del sobre.** El conductor que lo creó es el único que lo escribe. Una
sesión que lo encuentra y no lo creó **lee e informa**, y **nunca escribe**: ni cosecha, ni retira, ni
reclama. Encontrar un sobre ajeno es información —hay trabajo en vuelo acá, de este dueño, con estas
salidas—, no una invitación a operarlo.

Un protocolo de claim exclusivo parece la alternativa natural, y no hace falta: **el barrido pide
poder *encontrar* las corridas en vuelo sin memoria previa, no poder cosecharlas**, y la cosecha única
la garantiza la marca del sobre y no la exclusión mutua. Lo que el claim sí trae es superficie de
carrera propia —quién posee la marca, qué pasa si el que reclamó muere, con qué autoridad se declara
vivo o muerto al propietario, cómo se revierte un takeover a medio hacer—, y cada una de esas
preguntas es un caso más que puede quedar mal resuelto sin que nadie lo note hasta que ocurre.

**Un solo escritor no vuelve atómica la escritura.** Toda actualización del sobre —el nacimiento
incluido— se publica escribiendo un **temporal** en el mismo directorio y renombrándolo sobre el
destino: el **rename atómico** es lo que evita que un lector encuentre un JSON a medio escribir y que
una caída deje el archivo truncado. En el mismo directorio, porque un rename entre sistemas de
archivos deja de ser atómico y se vuelve copia. Y el barrido **ignora** los **temporales**: si los
contara, informaría corridas que todavía no existen y volvería a informar cada actualización en curso.

**El nacimiento va sin reemplazo.** El rename reemplaza el destino, que es lo correcto para actualizar
y lo incorrecto para nacer: `run_id` es un sufijo corto, y dos corridas concurrentes de la misma skill
pueden elegir el mismo valor. Con reemplazo, la segunda pisaría a la primera antes de que nadie la
hubiera leído, y el worker de la primera seguiría vivo sin ningún sobre que lo nombre. La creación usa
el modo que **falla si la ruta existe**; ante la colisión se genera otro `run_id` y se reintenta.

### Outcome de la espera

La espera del conductor termina de una de tres formas —resultado terminal, corte por presupuesto, y
error o cancelación explícita—, y cada una deja el sobre en un estado distinto. **Ninguna lo retira.**
El mejor efecto que un outcome alcanza es habilitar la *evaluación* del retiro, que se decide con las
tres condiciones de la sección siguiente y no con el outcome solo:

| outcome | condición | efecto sobre el sobre |
|---|---|---|
| `resultado_entregado` | — | `habilita_evaluar_retiro` |
| `corte_presupuesto` | — | `sigue_activo` |
| `error` | — | `habilita_evaluar_retiro` |
| `(cancelacion, cese_confirmado)` | se comprobó que el worker dejó de ejecutar | `habilita_evaluar_retiro` |
| `(cancelacion, cese_incierto)` | se pidió el cese y no se comprobó su efecto | `recovery-required` |

**Vencer el deadline nunca retira el sobre.** El presupuesto es el corte que el conductor se pone a sí
mismo para dejar de esperar: no es una señal que le llegue al worker ni una prueba de que terminó. Se
observó lo contrario —una espera que venció con los dos workers todavía produciendo, y los dos
entregaron informes válidos después—. Por eso `corte_presupuesto` deja la corrida en `sigue_activo`:
lo único que terminó es la espera, el sobre permanece y el turno lo sigue informando.

**`error` es un terminal comprobado.** Un fallo conocido —el worker devolvió error, el artefacto salió
inválido, el proceso murió con causa— no es un resultado incierto: se sabe qué pasó y se puede
adjudicar. Tratarlo como incierto haría que un fallo limpio bloquee el reintento y el fallback como si
nadie supiera qué ocurrió, que es justo lo contrario de lo que un error diagnosticado permite.

**La `cancelacion` es un terminal propio, distinto del `corte_presupuesto` y del `error`.** Abortar
por pedido del usuario no es que se haya acabado el tiempo ni que algo haya fallado: es una decisión,
y el sobre la registra como tal. Fundirla con cualquiera de los otros dos perdería el motivo, que es
lo único que explica por qué no hay resultado y si tiene sentido volver a intentarlo.

**Y necesita dos tuplas, no una.** Cancelar dice qué se pidió, no qué pasó con el proceso. Con el cese
**confirmado** no queda nada ejecutando y se puede pasar a evaluar el retiro. Con el cese **incierto**
—se mandó la señal y no se comprobó el efecto, o el transporte no ofrece con qué comprobarlo— el
estado es `recovery-required`: un proceso quizá vivo todavía puede escribir, y relanzar sobre él pone
dos escritores en las mismas rutas. Una sola tupla tendría que elegir uno de los dos caminos y
perdería el otro, y el que se perdiera sería siempre el peligroso.

**Un `recovery-required` resuelto no habilita el retiro por sí solo.** Resolverlo es averiguar qué
pasó, y esa averiguación desemboca en una de dos: la corrida **sigue activa** —el worker seguía
trabajando, el sobre permanece y la espera se replantea— o se llegó a un **terminal comprobado**, y
recién ahí se evalúan las tres condiciones. Dar por retirado un sobre porque el recovery "se atendió"
es retirarlo sin haber comprobado nada, que es la falla que el recovery existía para evitar.

### Condiciones del retiro

El retiro exige las **tres** a la vez. No hay atajo por outcome ni por antigüedad:

| condición | qué exige |
|---|---|
| **terminal comprobado** | uno de los finales de la tabla anterior, con su comprobación hecha; un deadline vencido no es uno |
| **artefacto validado o descartado** | ninguna salida del intento queda sin adjudicar: o se validó y se cosechó, o se descartó con motivo escrito |
| **sin recursos propios vivos, o transferidos a un registro de cierre** | ningún proceso, sesión ni otro recurso propio de la corrida queda en pie sin dueño |

Cuando las tres condiciones habilitan el retiro, primero se distingue el destino del carrier. Un
checkpoint intermedio transfiere el carrier y no materializa el manifest: después de escribir y
validar su descriptor, retira este sobre activo sin cerrar la corrida. Solo un outcome terminal
resuelve el manifest con las autoridades del propio sobre antes del retiro terminal. Si está
habilitado y la escritura tiene éxito, el objeto completo nuevo queda publicado antes del retiro.
Si el modo estaba deshabilitado o la escritura falla, se registra `manifest no escrito: <causa>` y
se retira igual: la telemetría nunca mantiene activa una corrida ya cerrada. Ningún camino abre
`.cross-model/runs/` para construir el objeto.

**Las tres son simultáneas porque ninguna implica a las otras.** Un terminal comprobado convive con un
artefacto sin adjudicar —el worker terminó y su salida sigue sin leerse—; un artefacto validado
convive con un recurso vivo que se conservó a propósito; y un cleanup terminado no dice nada de si el
resultado se incorporó. Retirar con dos de tres deja exactamente el hueco que la tercera cubría, y el
sobre desaparece justo cuando todavía hacía falta.

**La transferencia al registro de cierre es la alternativa a no tener recursos vivos, no un permiso
para retirar dejándolos huérfanos.** Si la corrida terminó pero queda algo propio en pie —un proceso
conservado para el cleanup, una sesión que alguien va a leer—, la propiedad de ese recurso y su próxima
acción pasan a un **registro de cierre**, y **recién entonces** se retira el sobre activo. Sin esa
transferencia solo quedan dos salidas, y las dos son malas: mantener el sobre en vuelo para siempre
por un recurso que se conservó a propósito, o retirarlo y perder al único que sabía que ese recurso
existe.

### Destino del carrier al retirar

| destino del carrier | efecto sobre el manifest | estado de la corrida |
|---|---|---|
| checkpoint intermedio | no se materializa | abierta; el descriptor conserva las autoridades |
| outcome terminal | se resuelve antes del retiro terminal | cerrada al cumplir las demás condiciones |

### Adopción

Un sobre lo escribe su creador, y eso deja una pregunta abierta: qué pasa cuando el conductor
propietario muere. La corrida queda en `recovery-required` —resultado incierto, decisión humana—, pero
esa decisión tiene que poder materializarse en el archivo. Si nadie salvo el creador escribiera nunca,
el sobre de un propietario muerto quedaría activo para siempre y el retiro que las tres condiciones
exigen no tendría quién lo ejecutara.

**La adopción es la única transición que otra sesión puede ejecutar sobre un sobre ajeno, y ocurre
solo con autorización explícita del usuario en el momento.** Al adoptarlo, el adoptante registra en el
sobre el **sucesor** —quién pasa a ser el propietario—, la **decisión** que se tomó sobre la corrida y
el **motivo** por el que se adoptó. Desde ahí el adoptante es su escritor único, y el sobre vuelve a
tener uno solo.

**No es un takeover.** Ninguna condición automática la dispara: ni un deadline vencido, ni un
propietario que no responde, ni una heurística de liveness. Sin el sí del usuario en ese momento no
ocurre, y quien encontró el sobre se queda leyendo e informando. La diferencia importa porque una
adopción automática reintroduce de una las carreras que el escritor único elimina: dos sesiones que se
creen dueñas del mismo archivo cosechan dos veces, o una retira lo que la otra todavía necesitaba.

**La autorización es del momento, no heredada.** Haber adoptado un sobre antes no autoriza a adoptar
el siguiente, y un permiso dado para una corrida no cubre a sus hermanas ni a sus hijas: cada adopción
se pide y se concede por separado, sobre un sobre nombrado.

### El barrido de corridas activas

Encontrar lo que está en vuelo no puede depender de haber visto el despacho. Una sesión que arranca
de cero y un conductor que retoma después de que su turno se cortó llegan a la misma lista por el
mismo camino: **listar un directorio**, que es determinista —el mismo árbol devuelve el mismo
resultado, en cualquier máquina y sin nada recordado—. Eso es el barrido, y lo único que cambia entre
topologías es dónde empieza:

| topología | dónde vive | recorrido |
|---|---|---|
| repo único | `<repo>/.cross-model/active/*/` | listar los subdirectorios por skill, ignorando temporales |
| skill standalone | `<working_dir>/.cross-model/active/*/` | listar los subdirectorios por skill, ignorando temporales |
| orquestación multi-repo | el orquestador en `<contenedora>/.cross-model/active/`; cada `sdd-flow` delegado en su repo | enumerar **siempre** todos los `<contenedora>/.sdd/*/manifest.yml` —el repo admite varios `<id>` concurrentes— y listar el `.cross-model/active/` de cada repo; `children` es **optimización**, no la fuente |

**Los temporales no se cuentan.** Un temporal es un estado intermedio de la publicación por rename,
no una corrida: contarlo informaría corridas que todavía no existen y volvería a informar cada
actualización mientras está ocurriendo. Se los reconoce por su nombre y se los saltea en las tres
topologías, no solo en la que los produjo.

**El multi-repo enumera siempre, y `children` nunca decide.** La tentación es leer el sobre del
orquestador y seguir su `children`: es un archivo en vez de N listados, y viene ordenado. El problema
no es que el padre falte —eso se nota— sino que **esté presente con `children` incompleto**, que es
exactamente lo que pasa si murió entre despachar una hija y anotarla. Una lista incompleta es
indistinguible de una completa, así que un recorrido que enumerara **solo como fallback ante la
ausencia del padre** no cubriría nada: en el caso peligroso el fallback jamás se dispara y las hijas
que faltan quedan invisibles. Por eso el orden es al revés. Se enumeran **siempre** todos los
`<contenedora>/.sdd/*/manifest.yml` —todos, porque una contenedora admite varios `<id>` concurrentes
y quedarse con uno dejaría afuera orquestaciones enteras— y se lista el `.cross-model/active/` de
cada repo que esos manifests nombran. `children` se aplica **después**, sobre lo ya encontrado, para
decir qué corrida cuelga de cuál: es optimización del orden en que se presenta el resultado, y jamás
la fuente que decide qué entra en él.

**El barrido es local: el conductor y su descendencia declarada.** No sale a recorrer el disco
buscando `.cross-model/`. Su alcance es el repo o worktree donde el conductor está trabajando, más
los repos que la orquestación en curso declara en sus manifests. Las tres razones son distintas y
ninguna es de rendimiento. Un sobre de un proyecto que este conductor no está tocando no habilita
nada —quien no lo creó lee e informa, y nada más— y no es información sino ruido que compite con lo
que sí tiene en vuelo. Un recorrido por el disco deja de ser determinista: depende de dónde alguien
clonó qué, y devuelve listas distintas en dos máquinas con el mismo trabajo. Y el alcance declarado
es lo que vuelve comprobable el resultado —la lista se deriva de la topología y de los manifests, no
de una heurística de búsqueda que nadie puede reproducir para desmentirla—.

### El cierre del turno

**Mientras haya una corrida registrada, todo turno del conductor cierra informando su estado.** Esa
es la obligación, y no tiene excepción por tema: el usuario pregunta otra cosa, el conductor le
responde esa otra cosa, y el turno igual termina diciendo qué sigue en vuelo. El sobre saca la
continuidad del turno y la pone en disco; el reporte al cerrar es lo que la trae de vuelta a la
conversación. Sin él, el archivo estaría escrito, el barrido encontraría la corrida y el usuario
seguiría siendo quien avisa que los workers ya terminaron —que es exactamente el problema que este
contrato existe para cerrar—.

**Informar es la obligación; sondear es apenas cómo se cumple.** Un conductor que consulte la fuente
en cada turno, aplique la precedencia y no diga nada satisface toda la mecánica de las secciones que
siguen y deja el problema intacto: la información existe, se produjo a tiempo, y muere en el turno
que la produjo. Por eso el orden de las dos cosas no es simétrico. La sonda es reemplazable —hay
transportes donde no hay nada que sondear y el cierre igual ocurre (ver *El límite declarado*)—; el
reporte no lo es nunca.

**Qué lleva el reporte, como mínimo:**

- **qué corrida**: la skill y el modo que despacharon, con su `run_id`;
- **cada worker directo, nombrado**: un informe que diga "el delegado" cuando hay tres no dice nada;
- **qué se observó y contra qué fuente**, o el límite declarado cuando el transporte no ofrece
  ninguna;
- **qué falta para que la corrida deje de estar en vuelo**, y cuánto queda del presupuesto de espera.

**Un turno sin novedad informa igual.** Que la sonda no haya encontrado nada nuevo no autoriza a
callar: el silencio se lee como "no hay nada pendiente", que es justamente la lectura falsa que hace
que el usuario deje de esperar el resultado o lo pida de nuevo. "Sigue en vuelo, sin cambios desde el
turno anterior" es información; no decir nada no lo es.

**Cerrar informando no es quedarse esperando.** El cierre no bloquea, no reintenta y no convierte al
conductor en un proceso de espera: dice lo que sabe con el costo de una sola consulta no bloqueante y
devuelve el control. Un conductor que se quedara esperando para poder informar algo mejor estaría
reintroduciendo la espera dentro del turno, que es de donde este contrato la sacó.

### La sonda por turno

La consulta que sostiene ese reporte tiene **cuatro propiedades**, y las cuatro son restricciones:

| propiedad | qué significa |
|---|---|
| **no bloqueante** | lee lo que ya está disponible y vuelve; no duerme ni espera a que aparezca nada |
| **una por turno** | una sola consulta por turno, sin importar cuántas veces escriba el usuario |
| **sin retry** | si no resuelve, se informa que no resolvió; no se reintenta dentro del mismo turno |
| **no modifica el deadline ni el contador** | el `wait_budget` del intento entra y sale del turno igual |

**Solo un poll real incrementa `consumidos`.** El presupuesto cuenta los intentos de espera que el
conductor decidió gastar esperando un resultado, no las veces que alguien le habló. Si la sonda los
gastara, una conversación activa consumiría el presupuesto de una corrida que nadie tocó: diez
mensajes del usuario y el conductor cortaría por presupuesto sin haber esperado ni una vez. El
contador es durable justamente para que esa diferencia sobreviva a un turno cortado, y la sonda es la
única lectura del sobre que no lo mueve.

**La sonda no es autoridad de corte.** Quien decide el **corte por presupuesto** siguen siendo el
`deadline` y el contador, que solo avanza un poll real; la sonda observa y reporta, y jamás declara
vencida una espera que el presupuesto no declaró vencida. El corte por presupuesto es una de las tres
formas de terminar: las otras dos —resultado terminal, y error o cancelación explícita— se reconocen
por separado y cada una tiene su propia fila en *Outcome de la espera*. Confundirlas en la sonda haría
que una consulta sin respuesta se informara como un final, cuando el `corte_presupuesto` deja la
corrida en `sigue_activo`.

**Una por turno, y del turno entero.** El límite es por turno del conductor, no por corrida: si hay
tres corridas en vuelo, cada una recibe su sonda en ese turno, porque cada una tiene su propia fuente
y su propio presupuesto. Lo que la propiedad prohíbe es sondear la **misma** corrida dos veces en el
mismo turno para ver si cambió, que es un retry con otro nombre.

### Fuente por transporte

**La fuente la fija el transporte del intento vigente**, no la skill ni la corrida: el mismo worker
puede tener una fuente distinta en su segundo intento que en el primero. Estos son los tres
transportes y lo que cada uno ofrece:

| transporte | fuente | qué se consulta, y con qué autoridad |
|---|---|---|
| `subagent` | `ninguna` | nada a mitad de vuelo: ni proceso propio, ni salida en disco por contrato |
| `cli-exec` | `archivo+proceso` | la salida del intento en su ruta exclusiva y el proceso hijo; manda el archivo |
| `cli-resume` | `archivo+proceso` | la salida de **este** intento y el proceso del resume; manda el archivo |

**Para `subagent` no hay fuente consultable a mitad de vuelo, y eso es el hecho, no una omisión.** Un
subagente del entorno no expone ningún proceso que se pueda interrogar y no está obligado por su
contrato de despacho a escribir a un archivo: mientras corre, no hay superficie donde mirar. Obligarlo
a escribir su reporte a disco cambiaría el contrato de despacho de cuatro skills, y por eso se
descartó: el límite se declara (ver *El límite declarado*), no se disimula.

**Los efectos en el árbol son evidencia parcial, nunca terminal.** Para un subagente **escritor**, un
archivo modificado dice que algo pasó; no dice que el worker terminó, ni que terminó bien, ni que lo
que falta no vaya a llegar. Y hay una trampa peor: buena parte de las marcas que parecen del worker
—el estado de una task, el registro de una ronda— las escribe el **conductor al volver**, así que
leerlas como señal del worker es leer la propia letra y creerle. Ninguna observación del árbol
habilita cosechar, retirar ni dar por terminada la corrida.

**Para un worker read-only no hay evidencia alguna.** Un explorador o un revisor que no escribe en el
árbol puede no dejar rastro **ninguno** hasta que entrega: la ausencia de efectos no distingue un
worker que está trabajando de uno que murió al arrancar. Ahí ni siquiera queda la evidencia parcial, y
la única salida honesta es el límite declarado.

**Donde no hay fuente, el sobre releído más el límite declarado cierran el turno.** El cierre no exige
haber consultado algo: exige informar. Releer el sobre —que es determinista, y no depende de nada
recordado— da la corrida, sus workers y su presupuesto; declarar el límite dice qué no se pudo
comprobar. Las dos cosas juntas son un reporte verdadero; inventar una consulta que el transporte no
ofrece sería un reporte falso.

### Precedencia ante discrepancia

Las dos superficies que se pueden consultar —el artefacto y el proceso— discrepan, y ninguna de las
dos gana siempre. **Un artefacto completo prueba entrega, no muerte del proceso**: el worker puede
haber escrito su salida y seguir vivo cerrando cosas. **Un proceso terminado no prueba que haya
resultado válido**: se sabe que dejó de correr, no que haya dejado algo utilizable. Por eso la
resolución no se improvisa por caso, sino que está escrita:

| caso | combinación observada | resolución |
|---|---|---|
| `D1` | proceso activo + artefacto completo | `cosechar` |
| `D2` | proceso terminado + artefacto ausente o inválido | `clasificar_error` |
| `D3` | deadline vencido + proceso incierto | `informar_activo` |
| `D4` | artefacto completo + cleanup pendiente | `esperar_cleanup` |

**`D1` cosecha aunque el proceso siga vivo.** La entrega es del artefacto: esperar a que además el
proceso muera retrasaría la cosecha por un hecho que no agrega nada —el resultado ya está completo y
ya se puede adjudicar—. Lo que el proceso vivo sí obliga es a no dar la corrida por retirada: eso lo
deciden las tres condiciones, y una de ellas es justamente que no queden recursos propios en pie.

**`D2` resuelve en `clasificar_error`, no en `recovery-required`.** Un proceso terminado con el
artefacto ausente o inválido es un fallo **conocido**: se sabe qué pasó —el worker corrió y no dejó
salida utilizable— y se puede adjudicar como error, que es un terminal comprobado. Tratarlo como
resultado incierto lo mandaría a `recovery-required`, que bloquea el reintento y el fallback hasta que
una persona decida: exactamente al revés de lo que un fallo diagnosticado permite. `recovery-required`
es para cuando **no se sabe** qué pasó, no para cuando lo que pasó fue malo.

**`D3` informa activo y no retira nada.** Un deadline vencido con el proceso incierto es la
combinación que más invita a concluir de más, y es donde ya se observó lo contrario: dos workers
seguían produciendo después de vencida la espera, y los dos entregaron informes válidos. Lo único que
venció es la espera del conductor; la corrida sigue en vuelo, el sobre permanece y el turno la sigue
informando.

**`D4` no espera indefinidamente: `esperar_cleanup` ejecuta la transferencia.** Un artefacto completo
con cleanup pendiente significa que el resultado está y que quedó algo propio en pie —un proceso
conservado, una sesión que alguien va a leer—. La resolución es transferir la propiedad de ese recurso y
su próxima acción al **registro de cierre**, y recién entonces habilitar la evaluación del retiro. Sin
la transferencia solo quedan dos salidas malas: mantener el sobre en vuelo para siempre por un recurso
que se conservó a propósito, o retirarlo y perder al único que sabía que ese recurso existe.

**La precedencia se resuelve por worker, y después se agrega.** Cada worker directo tiene su propia
combinación de proceso y artefacto en su intento vigente, así que aplicar una sola resolución a la
corrida entera mezclaría un caso ya cerrado con otro todavía incierto.

### El límite declarado

**Cuando el transporte no ofrece nada consultable, el límite se declara en una línea en vez de simular
una verificación.** Una línea alcanza porque no hay nada más que decir con verdad, y es
obligatoria porque la alternativa —callar— deja al lector suponiendo que hubo consulta. Simular es
peor que no consultar: un "verificado, sigue trabajando" sin fuente detrás es una afirmación que nadie
comprobó, indistinguible de una comprobada, y que se seguirá arrastrando en los turnos siguientes como
si fuera un hecho.

**La salida no afirma que el worker sigue ejecutándose.** Eso es lo que no se sabe, y es lo que la
declaración existe para no decir. Lo que sí se afirma son dos hechos comprobables: que la corrida
**sigue registrada** en su sobre, con sus workers y su presupuesto, y que **no hay observable terminal
consultable** por este transporte. Ninguno de los dos habla del proceso del worker, que es
precisamente el punto.

> `co-explore/investigate` · run `7f3a`: dos workers por `subagent` (`claude-a`, `codex-b`), ambos
> read-only. Sin fuente consultable a mitad de vuelo: no hay observable terminal por este transporte.
> La corrida sigue registrada; el presupuesto vence a las 14:20.

**Declarar el límite no es un final.** La corrida no pasa a `error`, no queda en `recovery-required` y
no se acerca al retiro por haberse declarado: sigue exactamente donde estaba. Lo que la declaración
cambia es el reporte, no el sobre.

### El dato nuevo del usuario

El usuario aporta un dato mientras el trabajo está en vuelo —el ticket también toca otro módulo, la
rama base cambió, ese archivo ya no existe— y el conductor tiene dos reflejos, los dos prohibidos.
**Pasárselo al worker en vuelo** rompe la independencia con la que se lo despachó, y en varios
transportes ni siquiera hay por dónde. **Reescribir el insumo que el intento vigente ya consumió** es
peor, porque no se nota: el worker sigue trabajando contra la versión que leyó, el archivo en disco
dice otra cosa, y su resultado se termina adjudicando contra un insumo que nadie usó. Ninguna de las
dos es una opción que este contrato habilite por algún camino.

Lo que sí tiene destino es el **registro**. El dato aterriza en un sidecar propio, hermano del sobre y
con su mismo nombre de corrida: **`.cross-model/active/<skill>/<run_id>.datos.jsonl`**, una línea por
dato y **append-only**. Su forma es

`<run_id>.datos.jsonl = {origen, destinos[], recibido_en, disposicion}`

y el despacho siguiente lo lee **antes** de armar su paquete de contexto, incorpora lo que le
corresponde y escribe la `disposicion` de cada línea que consumió.

**Append-only no es una preferencia de formato: es lo que vuelve imposible el fuera de alcance.** Un
archivo al que solo se agregan líneas no puede pisar el insumo del intento vigente, porque no puede
pisar nada. Con un destino a discreción —"una cola, o una versión nueva del artefacto"— cada agente
elegiría un lugar distinto y alguno elegiría el propio artefacto; con una ruta y un esquema fijos, la
única operación disponible es agregar. La garantía la da la construcción del archivo, no la
disciplina de quien escribe.

**Un dato registrado no es un dato consumido.** El sidecar guarda lo que llegó y a quién le toca; que
efectivamente entre en un paquete de contexto lo decide el despacho siguiente, y la `disposicion` es
la que dice cuál de las dos cosas pasó. Confundirlas es lo que hace que el usuario crea que su
aclaración ya está incorporada mientras el resultado se arma sin ella.

Las **siete obligaciones** del dato nuevo:

| obligación | qué exige |
|---|---|
| **ronda siguiente**, y es el **por defecto** | el dato entra en el paquete del despacho que todavía no salió; el que ya está corriendo no se toca |
| **abortar y relanzar** solo por pedido **explícito** del usuario | no lo decide el conductor porque el dato le parezca importante: cortar tira trabajo hecho y abre un relanzamiento con sus propias tres condiciones |
| un conjunto de `destinos` **explícito**, que puede ser **vacío** | qué worker y qué ronda lo van a consumir, escrito y no supuesto; el conjunto **vacío** es una respuesta legítima, no un campo sin llenar |
| el **sidecar** registra el `origen` de cada dato | de dónde vino y con qué autoridad, para que el despacho siguiente sepa qué está incorporando y a pedido de quién |
| **nunca** sobre el artefacto que el intento vigente **ya consumió** | ese insumo quedó congelado cuando salió el despacho; lo que llega después se agrega al registro, y ahí se queda |
| en un despacho de **una sola pasada** no hay ronda siguiente | el dato se registra con `destinos: []` y se informa que no habrá consumo dentro de esta corrida |
| si la corrida termina antes, la `disposicion` queda `no_consumido` y el sidecar **sobrevive** al retiro del sobre | el próximo despacho del mismo flujo lo encuentra donde quedó |

Las dos últimas son los casos borde, y son los que se olvidan.

**Una sola pasada: el dato se registra igual, con el conjunto de destinos vacío.** Hay despachos que
no tienen ronda siguiente —un explorador que sale una vez, un revisor sin fix loop, un implementador
cuyo work order está congelado—, y ahí "ronda siguiente por defecto" no tiene dónde apoyarse. La
salida no es descartar el dato ni inventarle un consumidor: se escribe con `destinos: []` y **se
informa al usuario, en el turno**, que no habrá consumo dentro de esta corrida. Registrarlo sin
avisar es peor que no registrarlo, porque deja al usuario creyendo que lo que dijo va a llegar a
alguna parte de este trabajo.

**Si la corrida termina antes de consumirlo, el sidecar sobrevive al retiro del sobre.** El sobre se
retira cuando se cumplen sus tres condiciones —*Condiciones del retiro*—, y ninguna de las tres habla
del sidecar: son sobre el terminal, sobre las salidas de los workers y sobre los recursos propios que
puedan seguir en pie. Un dato sin consumir no es ninguna de esas cosas. Su línea queda con
`disposicion` en `no_consumido` y el archivo se queda donde está, para que el próximo despacho del
mismo flujo lo lea al armar su paquete. Borrarlo junto con el sobre haría que el trabajo de mañana
arranque sin lo que el usuario ya dijo ayer, sin que nada lo señale: exactamente la pérdida que el
registro existía para impedir.

### Relanzamiento seguro

Relanzar es despachar de nuevo sobre una corrida que ya tenía un worker en vuelo, y el peligro no es
el intento nuevo sino el viejo. Un proceso del que se dejó de esperar respuesta no es un proceso que
haya dejado de trabajar: **vencer el deadline no prueba nada sobre el worker**, solo sobre la espera
del conductor. Por eso la intención de relanzar entra primero en **recovery** y no en la tool call:
hasta saber qué pasó con el anterior, no se despacha. Las tres condiciones son previas al
relanzamiento, y las tres a la vez:

| condición | qué exige |
|---|---|
| **cese confirmado** del worker anterior | se comprobó que dejó de ejecutar; sin esa comprobación el estado es `recovery-required`, que bloquea el reintento y el fallback |
| **rutas exclusivas** por intento | el intento nuevo escribe en rutas que ningún intento anterior podía tocar |
| el escritor nuevo queda **bloqueado** mientras el anterior pueda tocar el **árbol** | un implementador no se despacha si otro implementador de la misma corrida todavía tiene escritura viva |

**El cese confirmado es una comprobación, no una suposición.** Haber pedido el cese dice lo que se
pidió, no lo que ocurrió: esa es exactamente la diferencia entre las dos tuplas de la cancelación en
*Outcome de la espera*. Con el cese comprobado se relanza; con el cese incierto la corrida está en
`recovery-required` y ahí no hay retry ni fallback que valgan, porque un proceso quizá vivo todavía
puede escribir y el relanzamiento pondría dos escritores sobre el mismo trabajo.

**Rutas exclusivas por intento, para que una salida tardía no se pueda hacer pasar por la vigente.**
Si los dos intentos escribieran en la misma ruta, el worker viejo —que puede seguir vivo justamente
porque su cese no se comprobó— entregaría encima de la salida del nuevo, y el conductor cosecharía un
resultado creyendo que es del intento que despachó. No hay forma de detectarlo después: el archivo se
ve igual. La exclusividad es lo que hace que esa confusión no pueda ocurrir, y por eso `output` y
`process_ref` cuelgan del intento y no del worker.

**El escritor nuevo se bloquea mientras el anterior pueda tocar el árbol.** Aquí no alcanza con
rutas separadas: dos implementadores con escritura viva sobre el mismo worktree se pisan en archivos
que ninguno de los dos declaró, y el diff que el conductor revisa deja de ser el de nadie. El campo
`write` del worker es lo que permite reconocer el caso sin deducirlo del transporte: un worker
read-only relanzado no bloquea nada, y un escritor bloquea hasta que su cese esté comprobado.

**Cada intento es una entrada nueva de `attempts[]`, nunca una sobrescritura.** El relanzamiento
agrega su intento con su transporte, su salida, su proceso, su presupuesto y su cosecha; el intento
anterior se queda escrito con los suyos. Sobrescribir la entrada ahorraría un renglón y perdería la
única prueba de qué ruta le pertenecía a quién: sin el intento viejo en el sobre, una salida tardía
aparece en una ruta que ya nada explica, y el conductor no tiene con qué distinguirla de la del
intento vigente. El historial de intentos es lo que sostiene la exclusividad, no una decoración de
auditoría.

### La frontera con los otros registros activos

El sobre no es el único archivo que este ecosistema deja abierto mientras algo sigue pendiente. Ya
había otros dos registros activos antes que él, y los tres conviven: cada uno responde una pregunta
distinta y deja de existir en un momento distinto.

| registro | qué registra | vive mientras |
|---|---|---|
| sobre de corrida en vuelo | el trabajo delegado que está **ejecutándose ahora** | no se cumplen las tres condiciones del retiro |
| checkpoint durable | una revisión **esperando decisión humana** | el gate no se resolvió |
| bitácora del orquestador | el **intento** de cada transición | siempre: es append-only y se archiva con la orquestación |

**El checkpoint durable registra una espera humana, no un worker.** Es el descriptor por `run_id` que
`cross-review` escribe al abrir un checkpoint —el ledger, la ronda acumulada, el tope vigente, la
causa del corte, el gate pendiente y con qué reanudar al revisor— para que una sesión nueva rehidrate
la revisión abierta en vez de arrancar otra, y se retira al terminal de la corrida. Sus dos campos
más parecidos a los del sobre son justamente los que muestran la diferencia: `gate_pendiente` dice
qué STOP espera a que **una persona** decida, y `harvest_pending` dice que hay un resultado esperando
a que **el conductor** lo adjudique; el `revisor` con que se reanuda nombra una sesión resumible, no
un proceso del que haya algo que consultar ahora. Los dos registros pueden estar vivos a la vez —una
corrida cuya ronda siguiente todavía no se despachó tiene checkpoint abierto y ningún worker en
vuelo—, así que ninguno de los dos se deduce del otro.

**La bitácora no sustituye el nacimiento del sobre.** Registra un evento por intento de transición,
con `id`, `paso`, `actor`, `objeto`, `resultado` y `timestamp`: quién intentó mover qué, y si el
intento se consumó o se rechazó. **No lleva** el `run_id` de la corrida delegada, ni los workers, ni
dónde escribe cada uno, ni el presupuesto de espera, ni la marca de cosecha. Un `despachar-repo`
consumado prueba que el orquestador despachó ese repo; no dice a quién despachó, por qué transporte
viaja, hasta cuándo lo espera ni si su salida ya se cosechó —que es todo lo que hace falta para
recuperar el hilo—. Y ni siquiera viven igual: la bitácora es **append-only** y se archiva entera con
la orquestación, porque perder sus eventos borraría la prueba del progreso ya hecho; el sobre **se
retira** en cuanto se cumplen las tres condiciones, porque lo que registraba dejó de estar en vuelo.
Dar por cubierta la mitad de este contrato "porque el orquestador ya lleva bitácora" es leer un
registro de intentos como si fuera un registro de trabajo vivo.

**Donde ambos existen, el orden es fijo: evento de intento → sobre → tool call del despacho.** Los
dos primeros preceden al despacho por razones propias, y son simétricas. La bitácora registra el
**intento** antes de materializarlo porque un intento rechazado no materializa nada y no dejaría
rastro si se registrara después. El sobre nace antes de la tool call porque un worker lanzado sin
sobre no se recupera. Invertir cualquiera de los dos abre la misma clase de ventana: un tramo —corto,
pero real— donde algo ya ocurrió y ningún archivo lo dice.

**El sobre es obligatorio, y es independiente de `cross_model.manifest.mode`.** Esa clave apaga el
**manifest**, que es telemetría: un registro por corrida ya **terminada**, escrito para poder mirar
cien juntas y decidir si la capacidad se gana su costo. El sobre no es telemetría —es lo que permite
recuperar el hilo de una corrida **en vuelo**—, y apagarlo con la misma palanca dejaría al conductor
sin continuidad para ahorrar una métrica: un proyecto que decidió no medir sus corridas sigue
necesitando saber qué tiene despachado. Tampoco hay una palanca propia que lo apague: **este contrato
no agrega ninguna clave de configuración**. Una capacidad sin consumidor no entra en el config de
este repo, y lo único que un interruptor del sobre habilitaría es exactamente el modo de falla que el
sobre existe para cerrar.
