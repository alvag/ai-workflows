# cross-review — transporte por panes (adaptador)

Adaptador **semántico** de la vía de panes para `cross-review`: qué cambia cuando el revisor se aloja
en un pane de un multiplexor de terminales en vez de lanzarse headless. Se lee **solo** cuando la
activación del flujo resolvió a esta vía; con el transporte CLI vigente nada de acá hace falta.

**El principio que ordena el archivo entero: sustituye el transporte, no la semántica.** Las siete
reglas no negociables, el loop acotado por `max_rounds`, el árbitro sin sycophancy, el foco por tipo
de artefacto, la plantilla del prompt, el formato de salida, el `review-log.md`, la matriz de resume
y la degradación al gate humano son los mismos y viven donde ya viven (`SKILL.md` y `reference.md`).
Acá está únicamente lo que cambia por el transporte.

**La sintaxis no vive acá.** Este archivo dice **qué** hay que lograr —crear el pane, despachar,
esperar, cosechar, cerrar—; los comandos que lo logran son autoridad de la skill externa `herdr` y
del binario instalado, que se consulta en la sesión. El binario **imprime su propia copia de esa
skill** (`herdr --skill`): es la vía que la entrega apareada con la versión que corre, en vez de con
la que alguien instaló alguna vez. Copiarlos acá los congelaría desactualizados.

Los dos ejercicios que pagaron estas reglas están versionados en
`docs/superpowers/experiments/2026-08-01-herdr-como-transporte.md` y
`docs/superpowers/experiments/2026-08-02-herdr-transporte-sintesis.md`; el segundo manda sobre el
primero.

## Activación

**Son dos preguntas distintas y hacen falta las dos.** La **capacidad** responde "¿se puede alojar un
revisor en un pane acá?"; la **intención** responde "¿debe esta revisión usarlos?". La intención no
sustituye a la capacidad —querer panes no los crea— y la capacidad no autoriza sola. Sin las dos en
verdadero la vía de panes **no se intenta**.

La intención es de la llamadora, no de esta skill: en modo embebido llega ya resuelta con el resto
del contrato de invocación —junto a `execution`, `complexity` y `max_rounds`—, se aplica sin volver a
decidirla y no se vuelve a pedir permiso por ronda ni por gate. Su sede durable, su precedencia y su
eco en el checkpoint de inicio son de la skill que conduce el flujo, no de este archivo. En modo
directo y en modo draft la intención es del usuario, expresada en la misma invocación.

**Capacidad: tres cláusulas, cada una con lo que pasa si resuelve a falso.**

| Cláusula de capacidad | Cómo se resuelve | Falsa ⇒ qué se hace |
|---|---|---|
| la variable de entorno `HERDR_ENV` vale `1` | se lee del entorno del propio conductor; es capacidad, no consentimiento | el conductor no corre dentro de un pane host: se cae al transporte CLI vigente |
| el binario utilizable, comprobado en la sesión | no se infiere de la variable: la variable dice dónde corre el conductor, no que el binario responda | se cae al transporte CLI vigente, sin improvisar comandos |
| la mecánica de uso, obtenible de cualquiera de sus dos fuentes | la skill de transporte instalada **o** el binario, que imprime su propia copia (`herdr --skill`): alcanza con una. No son equivalentes en todo —la instalada es además lo que hace que la vía de panes se conozca fuera de un flujo; la del binario es la única apareada con la versión que corre— pero para la mecánica de una corrida cualquiera de las dos basta | sin ninguna de las dos se cae al transporte CLI vigente, porque la mecánica no se improvisa de memoria |

**La degradación es la regla vigente del ecosistema, no una improvisación.** Sin capacidad la vía de
panes no se intenta: la revisión sigue por el transporte CLI vigente con un aviso de una línea, y el
manifest registra en `transport` la vía que efectivamente corrió más `transport_fallback` como causa
de la corrida (`SKILL.md` → "Degradación"). Una capacidad opcional nunca bloquea el flujo, y este
fallback **no toca el veredicto**: una revisión que convergió por CLI sigue devolviendo `APPROVED`.

## Perfil de permisos

**El hueco read-only está abierto y se declara antes de usarlo.** Son tres hechos, y salieron del
contraste entre los dos ejercicios:

1. Con **sandbox estricto** de solo lectura el revisor **no puede escribir** su propio veredicto en
   el repo — y en esta vía el contrato exige que lo escriba, porque el pane no devuelve el texto (ver
   "Entradas y salidas"). Es la asimetría más incómoda respecto del transporte CLI, donde el
   veredicto lo capturaba el conductor por redirección y el revisor no necesitaba escribir nada.
2. Con el perfil amplio de escritura al workspace el revisor queda habilitado a escribir **todo el
   working dir**, no solo su ruta de salida — y ese working dir es justamente el repo que la regla 1
   le da para leer y fundamentar.
3. El punto intermedio —repo de solo lectura con una única salida escribible— **no se ejercitó** en
   ninguno de los dos ejercicios. Es diseño sin validar, no práctica recomendada.

**El perfil ejercitado, nombrado como tal.** Lo que los ejercicios probaron es el **comportamiento**
read-only por contrato —el prompt prohíbe modificar archivos y el agente lo respetó—, no el
**aislamiento** por permisos. Del lado Claude fue el modo de permisos automático con lectura amplia y
escritura reservada al veredicto; del lado Codex, el perfil de escritura al workspace. Ninguna de las
dos mitades alcanza sola: el sandbox permite todo el working dir, y el contrato sin sandbox es una
promesa. Eso es lo que se documenta, y con esa etiqueta.

**Tres reglas que no se relajan.** Ningún bypass de aprobaciones y sandbox, en ninguna ronda. Ningún
perfil que habilite shell arbitrario junto a rutas acotadas: sin una allowlist igual de estrecha para
el shell, el límite por rutas se vuelve poroso. Y el aislamiento de extensiones —plugins, hooks y
servidores MCP— sigue siendo un **perfil de fase**, no un default universal: cuando se apaga, el
prompt tiene que ser autocontenido, y cuando se deja encendido es una decisión, no un descuido. El
modo de permisos manual, además, deja al revisor esperando la primera aprobación —el observable
`blocked` de "Validación del artefacto"—, así que no sirve para un revisor desatendido.

## Entradas y salidas

**El prompt llega por ruta, no por stdin.** Es la diferencia más visible con el transporte CLI: por
la línea de comando viaja una oración de texto plano que le dice al revisor **dónde** está su prompt,
y lo lee él. Dos consecuencias, las dos verificadas: no hay quoting que romper —el markdown con
backticks nunca toca la línea de comando— y la bifurcación POSIX/PowerShell para redirigir stdin
desaparece del problema. La plantilla de `assets/prompts/` lo dice en su cabecera: el prompt **se
escribe a archivo** con la tool de escritura del agente, y cómo llega al revisor lo fija el
transporte.

**Las rutas de salida no cambian.** El prompt de cada ronda, el delta del resume y el veredicto crudo
siguen en el `scratch_dir` de la skill —el subdirectorio `cross-review/` junto al artefacto, con la
nomenclatura por tipo de artefacto y número de ronda— y el `review-log.md` sigue siendo hermano del
artefacto, fuera del scratch. **La cosecha es por archivo, nunca por lectura del pane:** el archivo es
la autoridad —se publica atómicamente y pasa su validador—, y lo que devuelve el pane es la pantalla
renderizada del revisor, con el cromo de la TUI entremezclado, que no es el veredicto. Cuánto
historial alcance a devolver una lectura es un dato de la plataforma —depende de la versión del
multiplexor y del estado del agente— y por eso no se apoya un contrato ahí.

**Qué campos del descriptor de corrida escribe esta skill.** El descriptor es de la corrida y tiene
**doce** campos; `cross-review` completa los suyos **antes** del dispatch:

1. **run ID** — el sufijo corto de corrida.
2. **skill** — `cross-review`.
3. **modo** — el tipo de artefacto: `spec`, `plan`, `tasks`, `master-spec`, `reparto` o `draft`.
4. **nombre del agente** — uno solo, el del revisor, con el sufijo de corrida: un nombre fijo choca
   entre dos gates concurrentes de la misma tanda.
5. **panes propios** — los que **esta** corrida creó, y solo esos: es la lista que autoriza el
   cierre. El pane que se toma prestado **no entra acá** (ver "Continuidad entre rondas").
6. **prompt esperado** — la ruta exclusiva de la ronda.
7. **outputs esperados** — el veredicto crudo de la ronda.
8. **deadline** — el presupuesto de pared de la fase, corriendo desde el propio lanzamiento.
9. **estados terminales** — los tres veredictos que la skill ya devuelve.
10. **gate pendiente** — el de la llamadora, marcado mientras la corrida no cosechó y validó.
11. **próxima acción** — qué hace el conductor al despertar: parsear, arbitrar, abrir otra ronda o
    presentar la degradación.
12. **transporte** — la vía resuelta, **replicada** de la intención de la llamadora para que el
    callback la lea. El descriptor es copia, no sede.

**Descriptor y tombstone son cosas distintas y no se mezclan.** El descriptor de arriba es el sobre de
una corrida activa, tiene los doce campos de la lista y muere con ella. El **tombstone** es el sobre
reducido que sobrevive cuando la corrida terminó y todavía queda un pane propio vivo, y guarda
exactamente dos piezas: la lista de panes propios y la próxima acción. El del pane prestado pertenece
a `co-explore`, que lo creó, y esta skill no le escribe nada. El transporte **no** va al tombstone: es
un dato de la corrida que ya cerró, y quien lo necesite lo resuelve de nuevo por activación.

**Cuándo se retira el descriptor, en las dos direcciones.** No se retira mientras quede un pane propio
vivo —alcanzar un veredicto terminal no basta: una degradación terminal libera el gate y conserva el
pane, y retirarlo ahí borraría la única lista de panes propios que existe—. Y se retira **cuando todos
sus panes propios están confirmados cerrados**, que en esta versión es la única salida, porque la
transferencia de ownership quedó fuera. El pane prestado no entra en esa cuenta: no es propio. Para los
dos vale el mismo límite del ecosistema: no hay máquina de estados persistente, ni esquema formal, ni validador propio, ni versionado.
Ese nivel de estado persistido ya se rechazó por escrito, y este ítem nunca se ejercitó.

## Independencia

**El invariante propio de esta skill es la regla 7 y el transporte no lo cambia: el revisor nunca es
de la misma familia que el autor del artefacto.** El autor es la familia del agente que conduce la
skill —sin importar la superficie donde corre— y el revisor es siempre el de la otra; misma familia
son errores correlacionados, que es justo lo que esta revisión existe para romper. Alojar al revisor
en un pane no cambia quién es: el pane es **dónde** vive el proceso, no de qué familia es el modelo
que corre adentro. Si en panes solo hubiera disponible la familia del autor, la respuesta no es usarla
igual: es caer al transporte CLI vigente cuando ahí sí hay revisor de la otra familia y, si no hay
ninguno, devolver `UNAVAILABLE` y ceder al gate humano.

**Dos agentes en panes distintos no comparten estado por estar en el mismo workspace.** Cada uno es un
proceso propio, con su sesión, su historial y su prompt; la vecindad visual —dos panes en la misma
tab— no es un canal, y el multiplexor no propaga contexto entre agentes. Acá pesa más que en la vía
CLI, porque el conductor y el revisor pasan a ser vecinos **visibles**: que el autor esté en el pane
de al lado no le filtra su razonamiento al revisor, y tampoco lo autoriza a mirarlo. Lo que sí
comparten es el filesystem, así que la independencia se sostiene con lo que ya la sostenía: el prompt
como **handoff destilado** —objetivo, artefacto inline, contexto necesario, límites—, nunca el
transcript de la sesión del conductor.

## Deadline

La política de deadline es de la skill, no del transporte: el presupuesto de pared por complejidad y
su override siguen en `reference.md` → "Latencia y timeout (Claude revisor)", y `execution` sigue
decidiendo la forma de la llamada. Lo que cambia es **la forma de esperar**, y son cuatro reglas que
los dos ejercicios pagaron por descubrir.

**(a) Se despachan todos antes de esperar a ninguno.** El orden es fijo: preparar el prompt · crear el
pane · despachar · **y recién entonces** esperar. Crear el pane y arrancar al agente son además **dos
pasos**: encadenarlos falla por una carrera de readiness observada, y el reintento es recuperación de
transporte, no una ronda de revisión nueva. Una corrida de esta skill despacha **un** revisor, así que
el ahorro de reloj no es el punto; lo que la regla prohíbe es el despacho que lleva su propia espera
adentro. Medido: dos despachos que incluyen su espera se ejecutan en serie, porque el harness espera
el primero antes de ejecutar el segundo. Si una llamadora somete varios artefactos en la misma tanda,
eso multiplica el reloj de pared por artefacto; y en cualquier caso un despacho bloqueante le saca al
conductor la posibilidad de aplicar su propio deadline, que es su única garantía de no colgarse.

**(b) La espera de "avisame cuando termine" no pasa la opción que restringe estados.** El default de
esa espera ya cubre los **tres** estados asentados del lifecycle —`idle`, `blocked` y `done`— y un
revisor de fondo que nadie observa termina en el tercero, `done`: `idle` significa listo para input
**y** con su tab vista en la interfaz, y las lecturas por CLI no marcan como visto. Restringir la
espera a estados elegidos no agrega `blocked` —ya estaba en el default— y **quita** `done`, con lo
cual la espera no puede cumplirse: medido, un agente terminó con su archivo en disco y la espera
quedó colgada 24 minutos más. Restringir se reserva para vigilar un estado a propósito.

**(c) El comando en background es un verificador, no un disparador.** Distingue **tres** desenlaces
—la espera falló · terminó sin artefacto · terminó bien— y los tres llegan al conductor con su
diagnóstico. Un aviso encadenado a la espera con un separador de comandos, y con el error descartado,
reporta verde sin comprobar nada: eso ya notificó un trabajo terminado que no había terminado.
Declarar éxito exige el veredicto publicado de forma atómica o validado completo; despertarse no es
declarar éxito, y una comprobación de existencia suelta puede estar mirando una escritura a medias.
Acá esa trampa es más filosa que en las skills hermanas: el marcador de esta skill **abre** la salida
en vez de cerrarla, así que verlo no prueba que el bloque de findings esté entero — el criterio es el
veredicto parseado completo, no la primera línea que aparece.

**(d) El lifecycle es señal de conveniencia, la autoridad es el archivo, y vale en las dos
direcciones.** Un agente asentado **no prueba** que el veredicto exista, y la ausencia de un estado
asentado **no prueba** que no exista: las dos se observaron, una en cada ejercicio. El conductor
clasifica por el archivo y su parseo, y usa el lifecycle solo para dejar de esperar.

**Los dos cierres se llaman igual y son cosas distintas.** El **marcador** que cierra el contrato de
salida del revisor es su veredicto emitido en el formato pedido, con el bloque de findings parseable
(`reference.md` → "Formato de salida"); el **estado terminal** del lifecycle del pane se llama `done`.
La prosa llama a los dos "el revisor terminó", y ahí está la trampa: el marcador dice que el revisor
**entregó** lo que se le pidió, el estado dice que su proceso **dejó de trabajar**. El bug de (b) se
explica por el estado, no por el marcador; y la distinción entre "entregó mal" y "no llegó a entregar"
—la que separa `runtime_failure` de `deadline_exceeded`— se decide por el marcador, no por el estado.
Convención de escritura: al marcador se lo nombra siempre como el veredicto parseado, y al estado
siempre como el estado del lifecycle.

## Continuidad entre rondas

**El resume es gratis, y ahí el andamiaje se cae solo.** El revisor sigue vivo en su pane entre
rondas: reanudarlo es mandarle el delta al mismo agente —**proyectado desde el ledger, nunca
redactado aparte** (`reference.md` → "Resume entre rondas")— y el pedido de una pasada nueva sobre el
artefacto actualizado. No hay
identificador de sesión del proveedor que capturar, persistir ni recuperar: el handle es el nombre del
agente. Con él desaparece también la relectura del modelo y del esfuerzo efectivos desde el scratch,
que el transporte CLI necesitaba porque cada ronda corría en un proceso nuevo; acá el proceso es el
mismo y no se relanza. **El pane no se recrea entre rondas:** recrearlo sería una sesión fresca
disfrazada de resume, y el revisor perdería la memoria de lo ya discutido, que es exactamente para lo
que el loop reusa su thread. Si la ronda no se puede reanudar, la degradación vigente sigue siendo
rondas independientes con el artefacto actualizado completo — más caro, pero válido.

**El paquete degradado lleva el ledger y el registro de identidad, en las tres vías.** Cuando la
ronda va a un revisor que no vio las anteriores —resume caído, sesión fresca, o un pane nuevo—, viaja
**el ledger** de la corrida **más el registro de identidad** de cada finding: su tema y sus anclas.
Solo las filas del ledger —ID, evento, decisión, rationale— lo dejarían sin **con qué** evaluar el
rechazo: sabría que algo se rechazó, no sobre qué. La equivalencia entre las tres vías es requisito
del contrato, no una propiedad del transporte: un revisor fresco tiene que poder aceptar o defender
cada rechazo igual que el que estuvo desde la ronda 1.

**El pane del seed se toma prestado y nunca se cierra.** Cuando la matriz de resume resuelve que esta
revisión arranca reanudando una sesión de la co-exploración, en esta vía esa sesión *es* un agente
vivo en un pane que **esta corrida no creó**. Las reglas del pane prestado, todas juntas:

- **No entra a la lista de panes propios del descriptor**, que es la única autorización de cierre que
  existe. Prestado no es propio.
- **No se cierra**, ni al terminar la revisión, ni al pasar el gate, ni por prolijidad. Cerrarlo es
  decisión del adaptador que lo creó y solo tras recomprobar **sus** precondiciones de cierre en el
  momento del cierre.
- **El ownership no se transfiere.** Tomarlo prestado no lo vuelve de esta skill; la transferencia de
  ownership queda fuera de esta versión, porque no existe rama que la produzca.
- **Su outcome, su recovery y su gate son de esta corrida y viven en su propio descriptor.** No se
  copian al tombstone de la skill que creó el pane: ese tombstone guarda dos piezas —la lista de
  panes propios de esa otra corrida y su próxima acción—, y meterle el estado de esta revisión lo
  convertiría en un canal de coordinación entre skills que no existe.
- **Si el préstamo falla, no se improvisa.** Un pane prestado que ya no está, o cuyo agente no
  responde, no se recrea ni se sustituye por un pane propio con la misma sesión: se cae por la regla
  vigente de la matriz, abajo.

**"Sin sesión disponible → revisor fresco de la familia opuesta" sigue siendo indisponibilidad
genuina.** Es la regla vigente de la matriz de resume y no cambia: el revisor fresco recibe los
índices y la síntesis como contexto. Lo que este archivo prohíbe es volverla una **consecuencia normal
de haber elegido este transporte**. Si el pane del seed se cerrara al terminar la co-exploración, o si
esta skill lo cerrara al terminar su revisión, cada corrida en panes arrancaría con revisor fresco por
diseño, y el transporte habría degradado la matriz — o sea, habría cambiado la semántica en vez de
solo el transporte. El revisor fresco queda reservado para lo que la matriz ya contempla: que no haya
sesión, que su worker haya quedado inválido, o que no haya habido co-exploración.

*Confianza media, declarada:* que un agente sobreviva un gate humano largo **no está probado**. Si el
pane prestado no sobrevivió, esta skill cae por esa regla vigente, que es indisponibilidad genuina; y
si la capacidad actual es una pared confirmada, no hay reintento y el resultado es `UNAVAILABLE`
terminal — reintentar contra una pared quema el deadline sin ninguna chance de éxito.

## Validación del artefacto

La validación es la de siempre: el veredicto parseado al formato estructurado, el triage por
severidad×confianza y el árbitro que verifica cada finding antes de aplicarlo. Lo que este archivo
cierra es la correspondencia de los observables que el transporte vuelve visibles, para que ninguna
fase los interprete a su manera.

| Observable | Estado del revisor | Outcome | Degradation | Retry / fallback | Cleanup y efecto sobre el gate |
|---|---|---|---|---|---|
| `blocked` — el revisor quedó esperando una aprobación interactiva de su entorno | ninguno todavía: sigue vivo, y no es terminal por sí solo | sin resolver mientras corra su deadline | ninguna todavía | destrabar la aprobación en su pane o dejarlo correr hasta el vencimiento; ningún fallback que escriba | pane en `cleanup: keep`; el gate queda marcado, no se presenta y no cuenta una aprobación prematura |
| veredicto inválido — respondió y su salida no se puede parsear ni con parseo tolerante | `UNAVAILABLE` | `UNAVAILABLE` con lo que haya | `runtime_failure` | ninguno: respondió mal, y una reemisión de formato no es una revisión nueva | pane en `cleanup: keep` para inspección; el gate se presenta con el aviso de degradación |
| deadline vencido sin el marcador de cierre | `UNAVAILABLE` | `UNAVAILABLE` con lo que haya | `deadline_exceeded` | la palanca es subir el presupuesto o bajar de modelo, no reintentar igual; nunca un poll abierto | pane en `cleanup: keep` hasta confirmar que el proceso dejó de escribir; el gate se presenta con el aviso |
| resultado incierto — no se sabe qué quedó escrito ni si el proceso sigue vivo | `recovery-required`: bloquea retry y fallback hasta resolverse | sin resolver hasta cerrar el recovery | la que registre el recovery al resolverse | los dos bloqueados: ni retry ni fallback hasta saber qué pasó con el recurso | pane en `cleanup: keep`; el gate se presenta con el aviso, y no se redespacha sobre esas rutas |

**Las tres decisiones que la matriz no reabre.**

1. **`blocked` no es terminal por sí solo.** Un revisor esperando aprobación sigue vivo y puede
   destrabarse; cerrarlo al instante tiraría una crítica recuperable. Se le aplica el **deadline
   vigente de la fase** y recién su vencimiento lo vuelve terminal: ahí cae en el estado de
   indisponibilidad que ya existe, como `UNAVAILABLE` con la causa `deadline_exceeded`, que es lo que
   efectivamente ocurrió.
2. **No crea outcome ni causa nuevos.** No hay un cuarto veredicto, ni una causa `blocked` por skill.
   Por eso `blocked` **no** figura en el enum de veredicto de la skill, ni en su tabla de causas, ni
   en la degradación: esas sedes consumen estados **terminales** —el veredicto es lo que libera el
   gate—, y publicarlo ahí permitiría cerrar el gate mientras el revisor todavía espera una
   aprobación. Vive en esta matriz y en el lifecycle del descriptor, y en ningún otro lado. Lo mismo
   vale para `recovery-required`: es estado del **intento de transporte**, no un veredicto.
3. **Ningún fallback que escriba se habilita sin evidencia positiva de que el proceso del revisor ya
   no está vivo.** Ni un estado asentado, ni un deadline vencido, ni un pane conservado son esa
   evidencia: son señales de lifecycle, y la regla (d) de "Deadline" ya dijo que el lifecycle no
   prueba nada sobre lo que el revisor hizo o sigue haciendo. Mientras falte, el resultado es
   **incierto** y el fallback no se habilita — incluido el fallback al transporte CLI, que sobre un
   intento quizá vivo pondría dos revisores escribiendo las mismas rutas de salida. Conservar el pane
   para inspección es compatible: lo que se confirma es que el proceso dejó de escribir, no que el
   pane se cerró.

**`blocked` no es ninguna de las otras tres casillas, y por eso necesita la suya.** No es
`UNAVAILABLE`: ese es el revisor que **no respondió** o no se pudo lanzar, y este respondió — está
esperando. No es un **veredicto inválido**: ese **entregó** algo que falla los predicados de parseo, y
este no entregó nada todavía. Y no es una **aclaración semántica**: esa es la crítica que frenó ante
una ambigüedad del paquete —un AC que admite dos lecturas, un contexto que falta— y **entregó lo que
alcanzó**, nombrando la ambigüedad en un finding; el bloqueado frenó ante una **aprobación interactiva
del entorno** y no entregó nada. La diferencia es operativa, no de matiz: a la aclaración se la
destraba respondiendo la ambigüedad en el paquete y abriendo otra ronda; al bloqueado se lo destraba
aprobando en su pane, sin redespachar nada. Confundirlos manda a rehacer una revisión que estaba a un
paso de completarse. En las cuatro casillas **su pane se conserva**.

**Vencer el deadline no prueba que el proceso dejó de trabajar.** Se observó lo contrario: una espera
venció con el agente todavía produciendo y el informe llegó válido después. Las rutas de salida fijas
**no** protegen contra un revisor tardío que completa el veredicto de una corrida ya degradada, así
que cada intento necesita rutas exclusivas y el estado incierto se clasifica como
`recovery-required`, que bloquea retry y fallback hasta resolverse.

**La dirección negativa importa igual.** Un pane propio conservado y con salud no dispara nada: el
recovery lo dispara una **causa registrada** por el descriptor de la corrida que produce o consume ese
pane, nunca la vitalidad del pane. Sin esa dirección, el pane que "Continuidad entre rondas" conserva
a propósito quedaría clasificado como resultado incierto.

## Cleanup

**El pane se cierra por artefacto validado, nunca por lifecycle.** Las cinco precondiciones de cierre
son **conjuntivas**: hacen falta **todas a la vez**, y ninguna se deja inferir de otra.

1. El veredicto **cosechado y validado** contra el formato estructurado, con sus findings parseados.
2. Un **outcome terminal** de la corrida: uno de los tres veredictos que la skill devuelve.
3. El **manifest escrito**, o su intento fallido reportado — que falle al escribirse nunca bloquea la
   corrida, pero tampoco se calla.
4. **Sin rondas ni recovery pendientes**: mientras quede una ronda del loop por delante, un consumidor
   elegible del pane o un `recovery-required` sin resolver, el pane vive.
5. **Sin tandas concedibles pendientes de decisión**: mientras el checkpoint esté abierto —el humano
   todavía no eligió entre las cuatro opciones—, el pane vive en `cleanup: keep`. Que la tanda se
   haya agotado **no** es un outcome terminal de la corrida: si el humano concede, la ronda siguiente
   reanuda **este** revisor, y cerrarlo antes convertiría la continuación en una sesión fresca
   disfrazada de resume — el mismo error que "Continuidad entre rondas" ya prohíbe entre rondas de
   una misma tanda.

**Un agente asentado no es condición suficiente de ninguna de las cuatro.** Que el revisor esté en
`idle` o en `done` no dice nada sobre el veredicto, el outcome, el manifest ni las rondas pendientes:
es lifecycle, y el lifecycle no cierra panes.

**Un pane que la corrida no creó nunca se cierra.** La lista de panes propios del descriptor es la
única autorización de cierre que existe, y con el patrón de reutilizar panes un pane ajeno puede
alojar hoy a otra corrida. Es la prohibición que cubre el pane prestado de "Continuidad entre rondas",
y no se compensa con un recolector automático global, que tampoco se construye.

**Con las cuatro en verdadero rige `cleanup: auto`:** el conductor cierra los panes propios y anuncia
el cierre en una línea, sin pedir permiso. Con cualquier precondición en falso rige `cleanup: keep`: el
pane queda anunciado y esperando decisión, que es lo que hacen los cuatro observables de "Validación
del artefacto". Si el usuario pide conservarlo, tampoco se cierra: permanece en `cleanup: keep`, con su
ownership y su descriptor intactos, hasta que él decida otra cosa.
