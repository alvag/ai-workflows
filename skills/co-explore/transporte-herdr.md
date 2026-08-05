# co-explore — transporte por panes (adaptador)

Adaptador **semántico** de la vía de panes para `co-explore`: qué cambia cuando cada worker se aloja
en un pane de un multiplexor de terminales en vez de lanzarse headless. Se lee **solo** cuando la
activación del flujo resolvió a esta vía; con el transporte CLI vigente nada de acá hace falta.

**El principio que ordena el archivo entero: sustituye el transporte, no la semántica.** Los cuatro
modos, la topología dual, los estados del worker por predicado, la escalera de degradación, los
artefactos, la retoma y la síntesis son los mismos y viven donde ya viven (`SKILL.md` y
`reference.md`). Acá está únicamente lo que cambia por el transporte.

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
worker en un pane acá?"; la **intención** responde "¿debe este flujo usarlos?". La intención no
sustituye a la capacidad —querer panes no los crea— y la capacidad no autoriza sola. Sin las dos en
verdadero la vía de panes **no se intenta**.

La intención es de la llamadora, no de esta skill: el flujo la resuelve **una vez** y `co-explore` la
recibe ya resuelta con el resto de los valores de la corrida, la aplica sin volver a decidirla y no
vuelve a pedir permiso por fase. Su sede durable, su precedencia y su eco en el checkpoint de inicio
son de la skill que conduce el flujo, no de este archivo.

**Capacidad: tres cláusulas, cada una con lo que pasa si resuelve a falso.**

| Cláusula de capacidad | Cómo se resuelve | Falsa ⇒ qué se hace |
|---|---|---|
| la variable de entorno `HERDR_ENV` vale `1` | se lee del entorno del propio conductor; es capacidad, no consentimiento | el conductor no corre dentro de un pane host: se cae al transporte CLI vigente |
| el binario utilizable, comprobado en la sesión | no se infiere de la variable: la variable dice dónde corre el conductor, no que el binario responda | se cae al transporte CLI vigente, sin improvisar comandos |
| la mecánica de uso, obtenible de cualquiera de sus dos fuentes | la skill de transporte instalada **o** el binario, que imprime su propia copia (`herdr --skill`): alcanza con una. No son equivalentes en todo —la instalada es además lo que hace que la vía de panes se conozca fuera de un flujo; la del binario es la única apareada con la versión que corre— pero para la mecánica de una corrida cualquiera de las dos basta | sin ninguna de las dos se cae al transporte CLI vigente, porque la mecánica no se improvisa de memoria |

**La degradación es la regla vigente del ecosistema, no una improvisación.** Sin capacidad la vía de
panes no se intenta: la corrida sigue por el transporte CLI vigente con un aviso de una línea, y el
manifest registra en `transport` la vía que efectivamente corrió más `transport_fallback` como
degradación (`SKILL.md` → "Degradación"). Una capacidad opcional nunca bloquea el flujo.

## Perfil de permisos

**El hueco read-only está abierto y se declara antes de usarlo.** Son tres hechos, y salieron del
contraste entre los dos ejercicios:

1. Con **sandbox estricto** de solo lectura el worker **no puede escribir** su propio informe en el
   repo — y este contrato exige que lo escriba, porque el pane no devuelve el texto (ver "Entradas y
   salidas").
2. Con el perfil amplio de escritura al workspace el worker queda habilitado a escribir **todo el
   working dir**, no solo su ruta de salida.
3. El punto intermedio —repo de solo lectura con una única salida escribible— **no se ejercitó** en
   ninguno de los dos ejercicios. Es diseño sin validar, no práctica recomendada.

**El perfil ejercitado, nombrado como tal.** Lo que los ejercicios probaron es el **comportamiento**
read-only por contrato —el prompt prohíbe escribir y modificar, y los dos workers lo respetaron—, no
el **aislamiento** por permisos. En Claude fue el modo de permisos automático con lectura amplia y
escritura reservada al informe; en Codex, el perfil de escritura al workspace. Ninguna de las dos
mitades alcanza sola: el sandbox permite todo el working dir, y el contrato sin sandbox es una
promesa. Eso es lo que se documenta, y con esa etiqueta.

**Dos reglas que no se relajan.** Ningún bypass de aprobaciones y sandbox, en ninguna fase. Y ningún
perfil que habilite shell arbitrario junto a rutas acotadas: sin una allowlist igual de estrecha para
el shell, el límite por rutas se vuelve poroso. El modo de permisos manual, además, deja al worker
esperando la primera aprobación —el observable `blocked` de "Validación del artefacto"—, así que no
sirve para un worker desatendido.

## Entradas y salidas

**El prompt llega por ruta, no por stdin.** Es la diferencia más visible con el transporte CLI: por
la línea de comando viaja una oración de texto plano que le dice al worker **dónde** está su prompt,
y lo lee él. Dos consecuencias, las dos verificadas: no hay quoting que romper —el markdown con
backticks nunca toca la línea de comando— y la bifurcación POSIX/PowerShell para redirigir stdin
desaparece del problema. Las plantillas de `assets/prompts/` lo dicen en su cabecera: el prompt **se
escribe a archivo** y cómo llega al worker lo fija el transporte.

**Las rutas de salida no cambian.** Son las del árbol de `reference.md` → "Árbol de rutas", con su
modo, familia y rol: el prompt en `co-explore/scratch/prompt-<modo>-<familia>-worker.txt` y el
artefacto del worker en `co-explore/scratch/raw-<modo>-<familia>-worker.md`, de donde sale el split a
índice y detalle. **La cosecha es por archivo, nunca por lectura del pane:** el archivo es la autoridad
—se publica atómicamente y pasa su validador—, y lo que devuelve el pane es la pantalla renderizada
del agente, con el cromo de la TUI entremezclado, que no es el informe. Cuánto historial alcance a
devolver una lectura es un dato de la plataforma —depende de la versión del multiplexor y del estado
del agente— y por eso no se apoya un contrato ahí.

**Qué escribe esta skill en el sobre de la corrida.** El sobre es de la corrida y `co-explore`
completa lo suyo **antes** del dispatch. **Los campos no se enumeran acá:** la lista y la
correspondencia con cada dato que este adaptador escribía viven en `corridas-en-vuelo.md` → "Mapeo del
descriptor Herdr". Una enumeración local sobrevive a los cambios del esquema y empieza a describir un
sobre que ya no existe, y ahí un adaptador termina implementado contra un campo que el esquema ya no
tiene. Lo que sí decide esta skill, y no se lee de esa tabla:

- **un worker por familia**, cada uno con el sufijo de corrida en su nombre: los nombres fijos chocan
  entre dos flujos concurrentes;
- **los panes que esta corrida creó**, y solo esos: es la lista que autoriza el cierre;
- **las rutas exclusivas del intento** —el prompt, el crudo del worker, y el índice y el detalle que
  salen del split— y el deadline de la fase, por worker, corriendo desde su propio lanzamiento;
- **la vía resuelta**, replicada de la intención de la llamadora para que el callback la lea: el sobre
  es copia, no sede.

**Sobre activo y tombstone son cosas distintas y no se mezclan.** El sobre de arriba es el de una
corrida activa y muere con ella. El **tombstone** es lo que sobrevive cuando la corrida terminó y
todavía queda un pane propio vivo, y guarda exactamente **dos piezas**: la lista de panes propios y la
próxima acción. El transporte **no** va al tombstone — es un dato de la corrida que ya cerró, y quien
lo necesite lo resuelve de nuevo por activación.

**Cuándo se retira: las tres condiciones del contrato, con el pane como recurso propio.** El retiro lo
fijan las condiciones de `corridas-en-vuelo.md` y este adaptador no agrega ninguna regla suya; lo
único que aporta es qué cuenta acá como recurso en pie. Un **pane propio vivo** lo es, así que llegar
a un final comprobado no alcanza: una degradación terminal libera el gate y conserva el pane, y
retirar ahí borraría la lista que autoriza cerrarlo. Cuando la corrida termina con un pane propio en
pie, la lista y la próxima acción pasan al tombstone —el registro de cierre de esta vía— y recién
entonces se retira el sobre activo. Para el sobre y para el tombstone vale el mismo límite del
ecosistema:
no hay máquina de estados persistente, ni esquema formal, ni validador propio, ni versionado.
Ese nivel de estado persistido ya se rechazó por escrito, y este ítem nunca se ejercitó.

## Independencia

**El invariante propio de esta skill es el de siempre y el transporte no lo cambia:** los dos workers
**no ven la salida del otro**. Ni el prompt de uno lo menciona, ni el crudo de uno le es legible al
otro dentro de la corrida, y "DOS MAPAS INDEPENDIENTES O NINGUNO" sigue siendo la condición de la
topología dual (`reference.md` → "Independencia por modo (regla 2 en topología dual)").

**Dos agentes en panes distintos no comparten estado por estar en el mismo workspace.** Cada uno es un
proceso propio, con su sesión, su historial y su prompt; la vecindad visual —dos panes en la misma
tab— no es un canal, y el multiplexor no propaga contexto entre agentes. Lo que sí comparten es el
filesystem, así que la independencia se sostiene con lo que ya la sostenía: rutas exclusivas por modo,
familia y rol, y prompts que no citan el artefacto del otro.

**Lo que este transporte hace más fácil de violar es el orden, no el aislamiento.** Si el conductor
espera al primer worker antes de despachar al segundo, el segundo arranca cuando el artefacto del
primero ya existe en disco: independencia perdida con el transporte como excusa. Lo cierra la regla
(a) de "Deadline".

## Deadline

La política de deadline es de la skill, no del transporte: los defaults por modo y su override siguen
en `reference.md` → "Latencia y deadlines". Lo que cambia es **la forma de esperar**, y son cuatro
reglas que los dos ejercicios pagaron por descubrir.

**(a) Se despachan todos antes de esperar a ninguno.** El orden es fijo: preparar · truncar · crear
los panes · despachar A · despachar B · **y recién entonces** esperar. Medido: dos despachos que
incluyen su propia espera se ejecutan en serie —el harness espera el primero antes de ejecutar el
segundo— y el ahorro de reloj es lo de menos, porque serializados el segundo worker arranca con el
artefacto del primero ya en disco. Crear el pane y arrancar al agente son además **dos pasos**:
encadenarlos falla por una carrera de readiness observada, y el reintento es recuperación de
transporte, no una corrida semántica nueva.

**(b) La espera de "avisame cuando termine" no pasa la opción que restringe estados.** El default de
esa espera ya cubre los **tres** estados asentados del lifecycle —`idle`, `blocked` y `done`— y un
worker de fondo que nadie observa termina en el tercero, `done`: `idle` significa listo para input
**y** con su tab vista en la interfaz, y las lecturas por CLI no marcan como visto. Restringir la
espera a estados elegidos no agrega `blocked` —ya estaba en el default— y **quita** `done`, con lo
cual la espera no puede cumplirse: medido, un worker terminó con su artefacto en disco y la espera
quedó colgada 24 minutos más. Restringir se reserva para vigilar un estado a propósito.

**(c) El comando en background es un verificador, no un disparador.** Distingue **tres** desenlaces
—la espera falló · terminó sin artefacto · terminó bien— y los tres llegan al conductor con su
diagnóstico. Un aviso encadenado a la espera con `;`, y con el error descartado, reporta verde sin
comprobar nada: eso ya notificó un trabajo terminado que no había terminado. Declarar éxito exige el
artefacto publicado de forma atómica o validado completo; despertarse no es declarar éxito, y una
comprobación de existencia suelta puede estar mirando una escritura a medias.

**(d) El lifecycle es señal de conveniencia, la autoridad es el archivo, y vale en las dos
direcciones.** Un agente asentado **no prueba** que el artefacto exista, y la ausencia de un estado
asentado **no prueba** que no exista: las dos se observaron, una en cada ejercicio. El conductor
clasifica por el archivo y sus predicados (`reference.md` → "Estados del worker") y usa el lifecycle
solo para dejar de esperar.

**Los dos `done` se llaman igual y son cosas distintas.** El **marcador** de cierre del contrato de
salida del worker es la línea `STATUS: done` como última línea no vacía del crudo (`reference.md` →
"Señal de finalización"); el **estado terminal** del lifecycle del pane también se llama `done`. No es
el mismo hecho: el marcador dice que el worker **entregó** lo que se le pidió, el estado dice que su
proceso **dejó de trabajar**. El bug de (b) se explica por el estado, no por el marcador; y la
distinción entre "entregó mal" y "no llegó a terminar" —la que separa `INVALID` de
`deadline_exceeded`— se decide por el marcador, no por el estado. Convención de escritura: el marcador
se nombra siempre como la línea `STATUS: done`, y el estado siempre como el estado del lifecycle.

## Continuidad entre rondas

**El resume es gratis, y ahí el andamiaje se cae solo.** El agente sigue vivo en su pane: reanudarlo
es mandarle otro prompt. No hay identificador de sesión del proveedor que capturar, persistir ni
recuperar —el handle es el nombre del agente—, y el loop de rondas de `debate` y el seed que
`cross-review` consume son **el mismo agente**, no una sesión reconstruida.

**El pane del seed se conserva, en `cleanup: keep`.** Al cerrar la corrida, el pane cuyo agente puede
ser consumido por una fase posterior **no se cierra**: la matriz de resume de esa fase es normativa y
en esta vía la sesión reanudable *es* el agente vivo en su pane. Cerrarlo por prolijidad degradaría
esa matriz por diseño —revisor fresco como consecuencia normal de haber elegido el transporte—, y eso
sería cambiar la semántica en vez de solo el transporte.

Las reglas del pane conservado, todas juntas:

- **El ownership no se transfiere.** `co-explore` conserva el ownership del pane que creó, en todas
  las ramas. La transferencia de ownership queda fuera de esta versión: no existe rama que la
  produzca, y documentarla como posible sería normar lo que nadie corrió.
- **La fase consumidora lo toma prestado y nunca lo cierra**, porque no lo creó. Su outcome, su
  recovery y su gate viven en **su propio descriptor**, y no se copian al tombstone de esta skill.
- **El tombstone guarda dos piezas** —la lista de panes propios y la próxima acción— y sigue vivo
  mientras viva el pane. Retirarlo antes borraría la única lista de panes propios que existe.
- **No hay reclamación automática entre skills en esta versión.** Cuando deja de haber un consumidor
  elegible, el conductor lo **anuncia** en una línea: queda un pane conservado y cerrarlo es una
  decisión, no un automatismo.
- **Cerrarlo exige recomprobar las cuatro precondiciones de "Cleanup"** en el momento del cierre, no
  en el momento en que se conservó. Solo el adaptador propietario del pane puede hacerlo.
- **Si el usuario pide conservarlo, no se cierra.** Permanece en `cleanup: keep`, con su ownership y su
  tombstone intactos, hasta que él decida otra cosa.

*Confianza media, declarada:* que un agente sobreviva un gate humano largo **no está probado**. Si el
pane no sobrevivió, la fase consumidora cae por su propia regla vigente —sin sesión disponible,
revisor fresco—, que es indisponibilidad genuina y no una degradación causada por el transporte. El
costo asumido también es real: sin reclamación automática un pane conservado puede quedar en pantalla
hasta que alguien lo cierre, y el anuncio es lo que evita que quede olvidado en silencio.

## Validación del artefacto

La validación es la de siempre: los cuatro estados por predicado, el split, la paridad y el marcador
de cierre (`reference.md` → "Estados del worker"). Lo que este archivo cierra es la correspondencia
de los observables que el transporte vuelve visibles, para que ninguna fase los interprete a su
manera.

| Observable | Estado del worker | Outcome | Degradation | Retry / fallback | Cleanup y efecto sobre el gate |
|---|---|---|---|---|---|
| `blocked` — el agente quedó esperando una aprobación interactiva | ninguno todavía: sigue vivo, y no es terminal por sí solo | sin resolver mientras corra su deadline | ninguna todavía | destrabar la aprobación o dejarlo correr hasta el vencimiento; ningún fallback que escriba | pane en `cleanup: keep`; el gate queda marcado, no se presenta y no cuenta una aprobación prematura |
| artefacto inválido — respondió y falla alguno de los predicados | `INVALID` | el que resuelva la escalera de degradación | la rama declarada (`branch-2`, `branch-3` o `branch-4`) | ninguno: respondió mal, y una reemisión de formato no es un intento semántico nuevo | pane en `cleanup: keep` para inspección; el gate se presenta con el aviso de degradación |
| deadline vencido sin marcador de cierre | `UNAVAILABLE` | el que resuelva la escalera, `map_failure` si no sobrevive ningún mapa | `deadline_exceeded` | la palanca es subir el tope, no reintentar con el mismo; nunca un loop abierto | pane en `cleanup: keep` hasta confirmar que el proceso dejó de escribir; el gate se presenta con el aviso |
| resultado incierto — no se sabe qué quedó escrito ni si el proceso sigue vivo | `recovery-required` | sin resolver hasta cerrar el recovery | la que registre el recovery al resolverse | los dos bloqueados: ni retry ni fallback hasta saber qué pasó con el recurso | pane en `cleanup: keep`; el gate se presenta con el aviso, y no se redespacha sobre esas rutas |

**Las tres decisiones que la matriz no reabre.**

1. **`blocked` no es terminal por sí solo.** Un agente esperando aprobación sigue vivo y puede
   destrabarse; cerrarlo al instante tiraría trabajo recuperable. Se le aplica el **deadline vigente
   de la fase** y recién su vencimiento lo vuelve terminal: ahí cae en el estado de indisponibilidad
   que ya existe, con la causa `deadline_exceeded`, que es lo que efectivamente ocurrió.
2. **No crea outcome ni causa nuevos.** No hay un quinto estado del worker, ni un outcome extra en el
   envelope, ni una causa `blocked` por skill. Por eso `blocked` **no** figura entre los estados del
   worker, ni en el envelope, ni en la escalera de degradación: esas tres sedes consumen estados
   **terminales**, y publicarlo ahí permitiría resolver una rama mientras el agente todavía espera una
   aprobación. Vive en esta matriz y en el lifecycle del descriptor, y en ningún otro lado.
3. **Ningún fallback que escriba se habilita sin evidencia positiva de que el proceso del agente ya no
   está vivo.** Ni un estado asentado, ni un deadline vencido, ni un pane conservado son esa
   evidencia: son señales de lifecycle, y la regla (d) de "Deadline" ya dijo que el lifecycle no prueba
   nada sobre lo que el worker hizo o sigue haciendo. Mientras falte, el resultado es **incierto** y el
   fallback no se habilita. Conservar el pane para inspección es compatible: lo que se confirma es que
   el proceso dejó de escribir, no que el pane se cerró.

**Vencer el deadline no prueba que el proceso dejó de trabajar.** Se observó lo contrario: una espera
venció con los dos workers todavía produciendo y los dos entregaron informes válidos después. Las
rutas de salida fijas **no** protegen contra un worker tardío que completa el archivo de una corrida
ya degradada, así que cada intento necesita rutas exclusivas y el estado incierto se clasifica como
`recovery-required`, que bloquea retry y fallback hasta resolverse (`reference.md` →
"`recovery-required` bloquea retry y fallback").

**La dirección negativa importa igual.** Un pane propio conservado y con salud no dispara nada: el
recovery lo dispara una **causa registrada** por el descriptor de la skill que produce o consume ese
pane, nunca la vitalidad del pane. Sin esa dirección, el pane que "Continuidad entre rondas" conserva
a propósito quedaría clasificado como resultado incierto.

**`blocked` no es ninguno de los cuatro estados que ya existen, y por eso necesita casilla propia.**
No es `UNAVAILABLE`: ese es el worker que **no respondió** o no se pudo lanzar, y este respondió —
está esperando. No es `INVALID`: ese **entregó** algo que falla los predicados, y este no entregó
nada todavía. Y no es `clarification-needed`: ese frenó ante una **ambigüedad semántica** del paquete
de contexto y entregó lo que alcanzó a mapear, mientras el bloqueado frenó ante una **aprobación
interactiva del entorno** y no entregó nada. La diferencia es operativa, no de matiz: a
`clarification-needed` se lo destraba respondiendo la ambigüedad en el paquete y redespachando; al
bloqueado se lo destraba aprobando en su pane, sin redespachar nada. Confundirlos manda a rehacer una
exploración que estaba a un paso de completarse.

## Cleanup

**El pane se cierra por artefacto validado, nunca por lifecycle.** Las cuatro precondiciones de cierre
son **conjuntivas**: hacen falta **todas a la vez**, y ninguna se deja inferir de otra.

1. El artefacto **cosechado y validado** contra los predicados de su estado.
2. Un **outcome terminal** de la corrida, resuelto por la escalera de degradación.
3. El **manifest escrito**, o su intento fallido reportado — que falle al escribirse nunca bloquea la
   corrida, pero tampoco se calla.
4. **Sin rondas ni recovery pendientes**: mientras quede una ronda de `debate`, un consumidor elegible
   o un `recovery-required` sin resolver, el pane vive.

**Un agente asentado no es condición suficiente de ninguna de las cuatro.** Que el agente esté en
`idle` o en `done` no dice nada sobre el artefacto, el outcome, el manifest ni las rondas pendientes:
es lifecycle, y el lifecycle no cierra panes.

**Un pane que la corrida no creó nunca se cierra.** La lista de panes propios del descriptor es la
única autorización de cierre que existe, y con el patrón de reutilizar panes un pane ajeno puede
alojar hoy a otra corrida. Tampoco se construye un recolector automático global.

**Con las cuatro en verdadero rige `cleanup: auto`:** el conductor cierra los panes propios y anuncia
el cierre en una línea, sin pedir permiso. Con cualquier precondición en falso rige `cleanup: keep`: el
pane queda anunciado y esperando decisión, que es lo que hacen los cuatro observables de "Validación
del artefacto". El pane del seed es el caso de "Continuidad entre rondas": queda en `cleanup: keep` y
su cierre vuelve a pasar por estas cuatro precondiciones.
