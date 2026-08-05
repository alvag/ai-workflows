# cross-implement — transporte por panes (adaptador)

Adaptador **semántico** de la vía de panes para `cross-implement`: qué cambia cuando el implementador
delegado se aloja en un pane de un multiplexor de terminales en vez de lanzarse headless. Se lee
**solo** cuando la activación del flujo resolvió a esta vía; con el transporte CLI vigente nada de acá
hace falta.

**El principio que ordena el archivo entero: sustituye el transporte, no la semántica.** El work order
congelado, el clean-tree gate, la escritura acotada, el reporte advisory, el fix loop con su tope, el
triage de ownership, el commit del conductor tras el gate humano y las cuatro vías de degradación son
los mismos y viven donde ya viven (`SKILL.md`, `reference.md`, `contrato-verificacion.md` y
`ownership.md`). Acá está únicamente lo que cambia por el transporte.

**Y una asimetría propia, que ordena todas las decisiones difíciles de abajo.** De las skills
cross-model del ecosistema, esta es la única cuyo agente delegado **escribe**. Su límite de escritura
es el working tree, así que lo que en una skill read-only se resuelve descartando un informe, acá se
resuelve contestando primero **cuántos procesos pueden estar escribiendo ese árbol**. La respuesta es
siempre uno, y de ahí sale la mitad de este archivo.

**La sintaxis no vive acá.** Este archivo dice **qué** hay que lograr —crear el pane, despachar,
esperar, cosechar, cerrar—; los comandos que lo logran son autoridad de la skill externa `herdr` y del
binario instalado, que se consulta en la sesión. El binario **imprime su propia copia de esa skill**
(`herdr --skill`): es la vía que la entrega apareada con la versión que corre, en vez de con la que
alguien instaló alguna vez. Copiarlos acá los congelaría desactualizados.

Los dos ejercicios que pagaron estas reglas están versionados en
`docs/superpowers/experiments/2026-08-01-herdr-como-transporte.md` y
`docs/superpowers/experiments/2026-08-02-herdr-transporte-sintesis.md`; el segundo manda sobre el
primero.

## Activación

**Son dos preguntas distintas y hacen falta las dos.** La **capacidad** responde "¿se puede alojar un
implementador en un pane acá?"; la **intención** responde "¿debe este flujo usarlos?". La intención no
sustituye a la capacidad —querer panes no los crea— y la capacidad no autoriza sola. Sin las dos en
verdadero la vía de panes **no se intenta**.

La intención es de la llamadora, no de esta skill. En modo embebido el flujo la resuelve **una vez** y
`cross-implement` la recibe ya resuelta con el resto de los valores de la corrida; en modo directo la
resuelve el conductor en el kickoff, junto al work order y al contrato de verificación. En los dos
casos se aplica sin volver a decidirla, y no se vuelve a pedir permiso por ronda de fix. Su sede
durable, su precedencia y su eco en el checkpoint de inicio son de la skill que conduce el flujo, no
de este archivo.

**Capacidad: tres cláusulas, cada una con lo que pasa si resuelve a falso.**

| Cláusula de capacidad | Cómo se resuelve | Falsa ⇒ qué se hace |
|---|---|---|
| la variable de entorno `HERDR_ENV` vale `1` | se lee del entorno del propio conductor; es capacidad, no consentimiento | el conductor no corre dentro de un pane host: se cae al transporte CLI vigente |
| el binario utilizable, comprobado en la sesión | no se infiere de la variable: la variable dice dónde corre el conductor, no que el binario responda | se cae al transporte CLI vigente, sin improvisar comandos |
| la mecánica de uso, obtenible de cualquiera de sus dos fuentes | la skill de transporte instalada **o** el binario, que imprime su propia copia (`herdr --skill`): alcanza con una. No son equivalentes en todo —la instalada es además lo que hace que la vía de panes se conozca fuera de un flujo; la del binario es la única apareada con la versión que corre— pero para la mecánica de una corrida cualquiera de las dos basta | sin ninguna de las dos se cae al transporte CLI vigente, porque la mecánica no se improvisa de memoria |

**La degradación es la regla vigente del ecosistema, no una improvisación.** Sin capacidad la vía de
panes no se intenta: la corrida sigue por el transporte CLI vigente con un aviso de una línea, y el
manifest registra en `transport` la vía que efectivamente corrió más `transport_fallback` como
degradación. Una capacidad opcional nunca bloquea el flujo, y acá tampoco lo degrada: el implementador
sigue siendo de la otra familia, la escritura sigue acotada y el diff sigue siendo el artefacto que el
conductor revisa.

**Un orden que esta skill no puede invertir.** La vía se resuelve junto con el implementador, en los
prechequeos, y el pane **no se crea hasta el despacho** — después del clean-tree gate y del
congelamiento del contrato. Crear el pane es preparar un escritor, y un escritor preparado antes de
saber que el árbol está limpio deja un diff imposible de aislar si alguno de esos dos gates falla.

## Perfil de permisos

**El hueco read-only está abierto y se declara antes de usarlo.** Son tres hechos, y salieron del
contraste entre los dos ejercicios:

1. Con **sandbox estricto** de solo lectura el agente **no puede escribir** su propio informe —ni,
   acá, el código que se le pidió—. Para esta skill ese hecho no es una limitación a sortear: es la
   prueba de que el perfil estricto está fuera de discusión.
2. Con el perfil amplio de escritura al workspace el agente queda **habilitado** a escribir
   **todo el working dir**, no solo las rutas que el work order nombra. **Habilitado no es capaz:**
   el perfil concede el permiso, pero ejercerlo depende del **mecanismo**, y hay uno que bajo este
   mismo perfil no logra persistir (ver "Permiso y mecanismo son cosas distintas"). Este punto habla
   del permiso concedido; no dice que cualquier vía de escritura vaya a funcionar.
3. El punto intermedio —árbol de solo lectura con un conjunto acotado de rutas escribibles— **no se
   ejercitó** en ninguno de los dos ejercicios. Es diseño sin validar, no práctica recomendada.

### Permiso y mecanismo son cosas distintas

**El hecho medido.** Bajo el perfil de escritura al workspace, sobre **Windows**, la herramienta de
edición interna de Codex **no logra persistir** el archivo que escribe, y la escritura por **shell**
desde el mismo agente y la misma sesión **sí lo logra**.

**El alcance de esa evidencia, para no leerla de más.** El par controlado varió **una** variable —el
mecanismo— manteniendo constantes agente, sesión, perfil, repositorio, destino y operación. La ruta,
el carácter oculto del directorio y la preexistencia del archivo **no impidieron la escritura por
shell**, y **cambiarlas no reparó la herramienta** en las sondas realizadas; eso no descarta
interacciones fuera de las combinaciones probadas. Y **la capa causal queda indeterminada**: el
perfil se mantuvo constante en todas las sondas —probar sin él habría exigido el bypass que esta
skill prohíbe—, así que no se puede afirmar si la causa es de la herramienta, de la plataforma o de
su interacción con el sandbox.

**Y acá pega distinto que en las otras dos skills.** `co-explore` y `cross-review` remedian el
problema con una instrucción de prompt —*persistí por shell*— porque su agente deposita **un archivo
de texto**, y una escritura por shell lo produce igual de bien. **Esta skill escribe código**: un
cambio real sobre un árbol de fuentes, hecho de ediciones a archivos existentes. "Persistí por shell"
**no es trasladable** a eso, y prometer que lo sería repetiría el error de diagnóstico que este hilo
de incidentes ya cometió una vez.

**Por lo tanto, el impacto sobre esta skill se declara, no se remedia:** si la herramienta de edición
del agente no persiste sobre Windows, **escribir código por esta vía está comprometido de una forma
que este flujo no resuelve**. No hay bloque `<output_persistence>` acá.

**El transporte CLI de esta skill no está a salvo por defecto — está sin medir.** Su agente también
escribe en el working tree con el mismo perfil de escritura al workspace, y el hecho medido no
distingue transportes: aisló el mecanismo de edición, no la vía por la que se lanzó el proceso. **No
se afirma que el CLI esté exento**, porque no se comprobó. Queda como **riesgo explícitamente no
verificado**, con ese alcance: se sabe que el mecanismo falla bajo ese perfil en panes; no se sabe si
falla igual por CLI.

**Cómo se detecta si ocurre.** El síntoma es el mismo que en las otras skills: la edición no
persiste, o el agente ofrece reintentar fuera del sandbox. Lo segundo **no se acepta nunca** —es el
bypass que la regla de abajo prohíbe—, y lo primero se manifiesta como un diff vacío o incompleto
frente a un agente que reporta haber terminado. La defensa vigente es la que ya existe: **el
conductor revisa el diff completo** y no acepta el reporte del agente como prueba.

**Acá el perfil amplio no es una concesión: es el modo normal de la skill.** Donde el worker delegado
solo deposita un informe, la escritura al workspace es una holgura que se tolera. Esta skill
**necesita** escribir el código, así que la escritura acotada al working dir es su contrato y no su
desvío (regla 3 del `SKILL.md`). Lo que el transporte cambia no es el borde: es que el pane nace con
ese perfil y lo conserva mientras viva.

**Qué queda sin acotar por eso, dicho sin adorno.** El borde efectivo es el working dir entero, no las
`KEY PATHS` del work order: el sandbox no distingue un archivo del contrato de uno que el work order
excluyó explícitamente. Dentro de ese borde nada impide un hunk fuera de alcance, y **lo único que lo
caza es la revisión del diff completo por el conductor** —el drift de la regla 4—, no el perfil. Se
suma el caveat que la vía CLI ya documenta: en el sandbox de escritura al workspace `/tmp` también es
escribible por diseño, así que un árbol objetivo que viva bajo `/tmp` tiene un borde más laxo que el
que su nombre sugiere.

**El perfil ejercitado, nombrado como tal.** Lo que los ejercicios probaron es alojar un agente en un
pane con **lectura amplia y escritura al workspace**, respetando el contrato del prompt sobre qué no
tocar. Es el mismo par de mitades que la vía CLI: el **comportamiento** acotado lo pone el contrato y
el **aislamiento** lo pone el sandbox, y ninguna de las dos alcanza sola —el sandbox permite todo el
working dir, y el contrato sin sandbox es una promesa—. Lo que **no** se ejercitó en panes es el
resume con override de sandbox, y no por olvido: en esta vía no hay resume (ver "Continuidad entre
rondas").

**Dos reglas que no se relajan.** Ningún bypass de aprobaciones y sandbox, en ninguna ronda: un pane
es una terminal abierta, y abrirla del todo "para que no falle por permisos" es la misma red flag que
la vía CLI ya rechaza. Y ningún perfil que habilite shell arbitrario junto a rutas acotadas: el shell
del agente sigue acotado a los binarios que la prueba del contrato necesita, porque sin una allowlist
igual de estrecha el límite por rutas se vuelve poroso. El modo de permisos manual, además, deja al
agente esperando la primera aprobación —el observable `blocked` de "Validación del artefacto"—, así
que no sirve para un implementador desatendido.

## Entradas y salidas

**El prompt llega por ruta, no por stdin.** Es la diferencia más visible con el transporte CLI: por la
línea de comando viaja una oración de texto plano que le dice al agente **dónde** está su
prompt-contrato, y lo lee él. Dos consecuencias, las dos verificadas: no hay quoting que romper —el
markdown con backticks nunca toca la línea de comando— y la bifurcación POSIX/PowerShell para
redirigir stdin desaparece del problema. La plantilla de `assets/prompts/implement.md` lo dice en su
cabecera: el prompt **se escribe a archivo** con la tool Write, y cómo llega al agente lo fija el
transporte. El contenido del prompt-contrato no cambia una palabra.

**Las rutas de salida no cambian, y el artefacto principal no es un archivo del agente.** El reporte
del implementador se cosecha del `report.txt` del subdirectorio `cross-implement/` que vive junto al
work order, con los deltas de fix y el `implement-log.md` donde ya viven. Pero el entregable de esta
skill es el **diff del working tree**, y se cosecha con las herramientas de git del conductor —`git
status --porcelain` y `git diff`—, nunca leyendo el pane. El transporte no cambia cuál manda: el diff
es la verdad y el reporte es advisory.

**Y la cosecha por pantalla no es una opción, ni siquiera para el reporte.** Lo que devuelve el pane es
la pantalla renderizada del implementador, con el cromo de la TUI entremezclado, y cuánto historial
alcance es un dato de la plataforma: depende de la versión del multiplexor y del estado del agente. Y
la lectura **entrega el texto sin decir si quedó recortada** —el aviso de recorte vive en la API por
socket, no en la salida que se lee acá—, así que un reporte leído de la pantalla queda truncado en
silencio, y un reporte truncado se confunde con un reporte que no parsea —que en esta skill tiene una
regla propia y benigna: el diff sigue estando—. Cosechar del archivo es lo que mantiene esa regla
honesta en vez de convertirla en una excusa.

**Qué campos del descriptor de corrida escribe esta skill.** El descriptor es de la corrida y tiene
**doce** campos; `cross-implement` completa los suyos **antes** del dispatch:

1. **run ID** — el sufijo corto de corrida.
2. **skill** — `cross-implement`.
3. **modo** — `directo` o `embebido`.
4. **nombres de agentes** — uno solo, el implementador, con el sufijo de corrida: un nombre fijo choca
   entre dos flujos concurrentes, y acá un choque de nombres es un choque de escritores.
5. **panes propios** — los que **esta** corrida creó, y solo esos: es la lista que autoriza el cierre.
6. **prompt esperado** — la ruta exclusiva del intento.
7. **outputs esperados** — el reporte del implementador, más el working tree como artefacto que no es
   un archivo y por eso se declara aparte.
8. **deadline** — el de la corrida, corriendo desde el lanzamiento.
9. **estados terminales** — los de la salida de esta skill, que son los de siempre.
10. **gate pendiente** — el gate humano del diff, marcado mientras la corrida no cosechó.
11. **próxima acción** — qué hace el conductor al despertar: revisar el diff y correr la prueba, no
    aceptar el reporte.
12. **transporte** — la vía resuelta, **replicada** de la intención de la llamadora para que el
    callback la lea. El descriptor es copia, no sede.

**Descriptor y tombstone son cosas distintas y no se mezclan.** El descriptor de arriba es el sobre de
una corrida activa, con sus doce campos, y muere con ella. El **tombstone** es otro mecanismo, de
`co-explore`: existe porque esa skill reserva un pane para una fase posterior y necesita algo que
sobreviva a la corrida, y guarda exactamente **dos piezas**, la lista de panes propios y la próxima
acción. `cross-implement` **no reserva ningún pane** (ver "Continuidad entre rondas"), así que no
produce tombstones. Cuando le sobrevive un pane propio es por una degradación y no por una reserva, y
lo que sobrevive entonces es el **descriptor**, que no se retira mientras quede un pane propio vivo:
retirarlo ahí borraría la única lista de panes propios que existe. Y se retira **cuando todos sus panes
propios están confirmados cerrados** —la única salida de esta versión, porque la transferencia de
ownership quedó fuera—; sin esa mitad, conservarlo para siempre cumpliría igual la otra. Para los dos
vale el mismo límite del ecosistema:
no hay máquina de estados persistente, ni esquema formal, ni validador propio, ni versionado.
Ese nivel de estado persistido ya se rechazó por escrito, y este ítem nunca se ejercitó.

## Independencia

**El invariante propio de esta skill es el de siempre y el transporte no lo cambia:** el implementador
es de la **familia opuesta** al conductor —Codex cuando conduce Claude, Claude cuando conduce Codex— y
el conductor **revisa el diff como un PR ajeno**, corriendo la prueba él mismo. Eso es lo que rompe la
correlación de errores, y alojar al implementador en un pane no lo toca: cambia por dónde viaja el
prompt, no quién escribe ni quién revisa. Un pane que aloje a un agente de la familia del conductor no
es esta skill corriendo por otro transporte: es esta skill sin su invariante.

**Dos agentes en panes distintos no comparten estado por estar en el mismo workspace.** Cada uno es un
proceso propio, con su sesión, su historial y su prompt; la vecindad visual —dos panes en la misma
tab— no es un canal, y el multiplexor no propaga contexto entre agentes. Nada de lo que uno lee o
escribe en su pane llega al otro por el hecho de estar al lado.

**Lo que sí comparten es el filesystem, y acá el filesystem es el artefacto.** Donde el worker
delegado solo lee, la independencia se sostiene con rutas exclusivas por rol; acá el escritor no está
acotado a una ruta sino al working tree entero, así que entre dos agentes vecinos la independencia
**no** se puede sostener por convención de rutas. Se sostiene por conteo: **un solo escritor sobre un
árbol**. De ahí salen las dos reglas duras de este archivo — el conductor no implementa inline
mientras el implementador pueda estar vivo ("Validación del artefacto", decisión 3), y ninguna corrida
reusa ni cierra un pane que no creó ("Cleanup").

**El aislamiento del conductor tampoco lo da el transporte.** El conductor se forma opinión leyendo el
diff con git, no mirando trabajar al agente en su pane. Tener el trabajo a la vista es cómodo y es
justamente la tentación que hay que resistir: un revisor que siguió cada paso deja de ser externo y se
vuelve un supervisor, que es el rol que este patrón no quiere.

## Deadline

La política de deadline es de la skill, no del transporte: los topes por tamaño de work order y su
override siguen en `reference.md` → "Latencia, deadlines y banner". Lo que cambia es **la forma de
esperar**, y son cuatro reglas que los dos ejercicios pagaron por descubrir.

**(a) Se despachan todos antes de esperar a ninguno.** El orden es fijo: preparar · crear el pane ·
despachar · **y recién entonces** esperar. Crear el pane y arrancar al agente son **dos pasos**:
encadenarlos falla por una carrera de readiness observada, y el reintento de ese arranque es
recuperación de transporte, no una corrida semántica nueva. Esta skill despacha normalmente **un** solo
implementador, y aun así la regla manda por un motivo que le es propio: si alguna vez se despacha más
de uno, intercalar la espera del primero no cuesta reloj, cuesta solapar dos escritores sobre el mismo
árbol — el peor caso de todo este archivo.

**(b) La espera de "avisame cuando termine" no pasa la opción que restringe estados.** El default de
esa espera ya cubre los **tres** estados asentados del lifecycle —`idle`, `blocked` y `done`— y un
implementador de fondo que nadie observa termina en el tercero, `done`: `idle` significa listo para
input **y** con su tab vista en la interfaz, y las lecturas por CLI no marcan como visto. Restringir la
espera a estados elegidos no agrega `blocked` —ya estaba en el default— y **quita** `done`, con lo cual
la espera no puede cumplirse: medido, un agente terminó con su trabajo en disco y la espera quedó
colgada 24 minutos más. Restringir se reserva para vigilar un estado a propósito.

**(c) El comando en background es un verificador, no un disparador.** Distingue **tres** desenlaces —la
espera falló · terminó sin artefacto · terminó bien— y los tres llegan al conductor con su
diagnóstico. Un aviso encadenado a la espera con `;`, y con el error descartado, reporta verde sin
comprobar nada. Acá "terminó bien" tiene la barra más alta de las tres skills: no alcanza con que
exista el reporte, porque el reporte es advisory. El verificador declara "terminó bien" cuando hay un
reporte completo **y** un árbol con cambios que el conductor pueda leer; el veredicto propiamente
dicho lo da él después, leyendo el diff y corriendo la prueba. El banner obligatorio al terminar un run
en background no cambia.

**(d) El lifecycle es señal de conveniencia, la autoridad es el archivo, y vale en las dos
direcciones.** Un agente asentado **no prueba** que haya escrito nada, y la ausencia de un estado
asentado **no prueba** que no haya escrito: las dos se observaron, una en cada ejercicio. Acá la
autoridad son el árbol y el reporte —`git status --porcelain`, `git diff` y el `report.txt`—, y el
lifecycle sirve solo para dejar de esperar. La dirección que más cuesta en esta skill es la primera: un
pane en `done` invita a suponer que el agente dejó de escribir el árbol, y no lo prueba.

**Los dos `done` se llaman igual y son cosas distintas.** El **marcador** de cierre del contrato de
salida del implementador es la línea `STATUS: done` como cierre de su reporte; el **estado terminal**
del lifecycle del pane también se llama `done`. No es el mismo hecho: el marcador dice que el
implementador **entregó** lo que se le pidió, el estado dice que su proceso **dejó de trabajar**. El
bug de (b) se explica por el estado, no por el marcador; y la distinción entre "entregó y falla una
fila" —que abre fix round— y "no llegó a terminar" —que es `deadline_exceeded`— se decide por el
marcador, no por el estado. Convención de escritura: el marcador se nombra siempre como la línea
`STATUS: done`, y el estado siempre como el estado del lifecycle.

## Continuidad entre rondas

**El resume es gratis, y ahí el andamiaje se cae solo.** El implementador sigue vivo en su pane:
reanudarlo para un fix round es mandarle otro prompt al mismo agente. No hay identificador de sesión
del proveedor que capturar, persistir ni recuperar —el handle es el nombre del agente—, y con él
desaparece el guard del id vacío. Desaparece también el **override de sandbox obligatorio al
reanudar**: ese override existe porque un resume por CLI no garantiza el modo de la sesión original, y
acá no hay resume, porque el proceso nunca murió y conserva el perfil con que nació. La contracara es
real: ese perfil hay que acertarlo al crear el pane, porque no hay un segundo momento donde corregirlo.

**Esta skill no reserva ningún pane para una fase posterior.** No existe una fase que consuma la sesión
del implementador después de que la corrida cierra: el fix loop y la revisión son del conductor y
ocurren dentro de la misma corrida. El fix loop **reusa el pane propio entre rondas** —es el mismo
agente, con el work order todavía en su contexto, que es justamente lo que hace baratos los deltas de
fix— y al terminar la corrida ese pane **se cierra**, con las cuatro precondiciones de "Cleanup"
recomprobadas en el momento del cierre y no en el momento en que se creó.

**Quién es el dueño, y quién no puede cerrarlo.** El pane es de la corrida que lo creó: mientras queden
rondas, `cross-implement` es su único dueño y el único que puede cerrarlo. El ownership **no se
transfiere** a nadie. Y a la inversa: si el work order llegó en un flujo que ya tenía panes abiertos,
esta corrida **no** los reusa ni los cierra. No los creó, la lista de panes propios de su descriptor no
los incluye, y un pane ajeno puede alojar hoy a otro agente — reusar un pane ajeno para implementar es
la forma más silenciosa de poner dos escritores en el mismo árbol.

**El takeover no reabre nada.** Al agotarse `max_fix_rounds` el conductor termina el trabajo él mismo,
y eso ocurre **después** de que el pane cumplió sus precondiciones de cierre o quedó conservado por una
degradación — nunca en paralelo con el agente. Es la aplicación directa de la decisión 3 de "Validación
del artefacto": un takeover es un fallback que escribe.

*Confianza media, declarada:* que un agente sobreviva un gate humano largo **no está probado**. Acá
pesa menos que en una skill que reserva su pane, porque el fix loop entero ocurre antes del gate
humano. Pero si el pane no sobrevivió a mitad del fix loop, la corrida no redespacha a ciegas: sin
agente vivo, lo que hay es el árbol en el estado en que quedó, y eso se clasifica primero (ver
"Validación del artefacto") y recién después se decide.

## Validación del artefacto

La validación es la de siempre: el diff completo leído como un PR ajeno, `FILES` contra `git status`,
el drift fuera del work order, la prueba corrida por el conductor y el triage de ownership de cada fila
que falla. Lo que este archivo cierra es la correspondencia de los observables que el transporte vuelve
visibles, para que ninguna ronda los interprete a su manera.

| Observable | Estado del implementador | Outcome | Degradation | Retry / fallback | Cleanup y efecto sobre el gate |
|---|---|---|---|---|---|
| `blocked` — quedó esperando una aprobación interactiva en su pane | ninguno todavía: sigue vivo y no es terminal por sí solo; en el triage es `ENVIRONMENT_FAILURE`, ausencia de veredicto | sin resolver mientras corra su deadline | ninguna todavía | destrabar la aprobación en su pane, o dejarlo correr hasta el vencimiento; **ningún fallback que escriba**, y no consume ronda de fix | su pane **se conserva**; el gate humano del diff queda marcado, no se presenta y no cuenta una aprobación prematura |
| artefacto inválido — entregó, y el diff falla una fila del contrato o trae drift | `IMPLEMENTATION_DEFECT` en el triage; un reporte ilegible no entra acá, porque el diff sigue siendo la verdad | el que resuelva el fix loop: `IMPLEMENTED` si la ronda lo corrige, `PARTIAL` en takeover | ninguna causa nueva: el takeover se registra en el outcome, no en la degradación | fix round en el mismo pane, consumiendo ronda, hasta `max_fix_rounds`; agotado el tope, takeover | el pane vive mientras queden rondas; el gate se presenta con el diff que haya y con las rondas usadas |
| deadline vencido sin la línea `STATUS: done` | `UNAVAILABLE`; en el triage es `ENVIRONMENT_FAILURE`: no hubo veredicto sobre el código | `UNAVAILABLE` | `deadline_exceeded`, no `runtime_failure`: arrancó bien y el corte lo puso el conductor | la palanca es subir el tope, no reintentar con el mismo; el takeover inline **solo** con el proceso confirmado muerto | el pane **se conserva** hasta confirmar que el proceso dejó de escribir; el gate se presenta con el aviso de degradación |
| resultado incierto — no se sabe qué quedó escrito en el árbol ni si el proceso sigue vivo | `recovery-required`; en el triage es `ENVIRONMENT_FAILURE` mientras el recovery no cierre | sin resolver hasta cerrar el recovery | la que registre el recovery al resolverse | los dos bloqueados: ni retry ni fallback hasta saber qué pasó con el árbol | el pane **se conserva**; el gate se presenta con el aviso, y no se despacha ningún escritor nuevo sobre ese árbol |

**La matriz mapea sobre las cuatro clases del triage de ownership y no agrega una quinta.** Las clases
siguen siendo `IMPLEMENTATION_DEFECT`, `VERIFICATION_DEFECT`, `ENVIRONMENT_FAILURE` y `DESIGN_GAP`, con
los presupuestos y la precedencia que ya tienen; un observable de transporte no las modifica ni pide
una nueva. Dos de ellas son inalcanzables desde un observable de este archivo, y decirlo es parte del
mapeo: `VERIFICATION_DEFECT` y `DESIGN_GAP` salen de leer una fila del contrato, no de mirar un pane,
así que ningún estado del transporte reclasifica una fila hacia ellas. El reparto del presupuesto cae
solo del lado correcto: `blocked`, el deadline vencido y el resultado incierto son
`ENVIRONMENT_FAILURE` —"no pude medir", que no consume ronda de fix—, y solo el diff que falla una fila
es `IMPLEMENTATION_DEFECT`, la única clase que la consume. Un `blocked` que gastara ronda le cobraría
al implementador una aprobación que nunca le pidieron.

**Las tres decisiones que la matriz no reabre.**

1. **`blocked` no es terminal por sí solo.** Un agente esperando aprobación sigue vivo y puede
   destrabarse; cerrarlo al instante tiraría trabajo recuperable —y acá el trabajo recuperable ya está
   a medio escribir en el árbol—. Se le aplica el **deadline vigente de la corrida** y recién su
   vencimiento lo vuelve terminal: ahí cae en el estado de indisponibilidad que ya existe, con la causa
   `deadline_exceeded`, que es lo que efectivamente ocurrió.
2. **No crea outcome ni causa nuevos.** El enum de resultado de esta skill sigue siendo
   `IMPLEMENTED | PARTIAL | UNAVAILABLE` y `blocked` **no** entra ahí: ese enum lo consume la llamadora
   como estado **terminal**, y publicar en él a un agente que todavía espera una aprobación permitiría
   cerrar una fase mientras el implementador sigue vivo sobre el árbol. Tampoco hay una causa `blocked`
   en el enum de degradación, ni una quinta clase de ownership. `blocked` vive en esta matriz y en el
   lifecycle del descriptor, y en ningún otro lado.
3. **Antes de cualquier fallback que escriba, el agente delegado tiene que estar confirmado muerto, con
   evidencia positiva.** Es la decisión crítica de este archivo, porque los fallbacks de esta skill —el
   conductor implementa inline, el takeover, un redespacho por la vía CLI— **escriben el mismo árbol**
   que el implementador. Degradar a implementación inline con el agente bloqueado todavía vivo produce
   **dos escritores concurrentes** sobre el mismo working tree: dos procesos editando los mismos
   archivos, un diff que no es de ninguno de los dos, y un `git status` que ninguno de los dos explica.
   La confirmación exige comprobar que **el proceso del agente ya no está vivo**. Ni `idle`, ni `done`,
   ni un deadline vencido, ni un pane conservado alcanzan: son estados de lifecycle, y la regla (d) de
   "Deadline" ya dijo que el lifecycle no prueba nada sobre lo que el worker hizo o sigue haciendo.
   Mientras falte esa evidencia el resultado es **incierto** y el fallback **no** se habilita — ninguno
   de los tres. Conservar el pane para inspección es compatible: lo que se confirma es que el proceso
   dejó de escribir, no que el pane se cerró.

**Vencer el deadline no prueba que el proceso dejó de trabajar.** Se observó lo contrario: una espera
venció con los agentes todavía produciendo, y entregaron después. Acá la consecuencia es peor que un
archivo tardío: un implementador tardío sigue **editando el árbol** de una corrida ya degradada, y las
rutas de salida exclusivas por intento no protegen nada, porque su salida no es una ruta — es el
working tree entero. Ese estado se clasifica como `recovery-required`, que bloquea retry y fallback
hasta resolverse, y el recovery acá es una pregunta concreta y contestable: qué quedó escrito, y si hay
un proceso que siga escribiéndolo.

**La dirección negativa importa igual.** Un pane propio conservado y con salud no dispara nada por sí
mismo: el recovery lo dispara una **causa registrada** por el descriptor de la corrida, nunca la
vitalidad del pane. Sin esa dirección, cualquier pane que una degradación conserva a propósito quedaría
clasificado como resultado incierto y la corrida no podría cerrar nunca.

**`blocked` necesita casilla propia, y no es ninguna de las otras tres.** No es el implementador que
**no respondió** —el `UNAVAILABLE` por pared confirmada, flake de lanzamiento o deadline vencido—:
este respondió, está esperando. No es el que **entregó algo inválido**: ese produjo un diff que falla
una fila o trae drift, y este no entregó nada todavía. Y no es una **aclaración semántica** sobre el
work order: esa es un hueco de diseño que se resuelve antes de delegar y vuelve al diseño
(`DESIGN_GAP`), mientras al bloqueado no le falta ningún dato del contrato — frenó ante una
**aprobación interactiva del entorno**. La diferencia es operativa, no de matiz: la aclaración se
resuelve corrigiendo el work order y volviéndolo a congelar; al bloqueado se lo destraba aprobando en
su pane, sin tocar el contrato ni gastar una ronda. Confundirlos manda a rediseñar un work order que
estaba bien escrito, o gasta presupuesto de fix en algo que se resolvía con una tecla.

## Cleanup

**El pane se cierra por artefacto validado, nunca por lifecycle.** Las cuatro precondiciones de cierre
son **conjuntivas**: hacen falta **todas a la vez**, y ninguna se deja inferir de otra.

1. El artefacto **cosechado y validado**: el diff leído completo por el conductor y la prueba corrida
   por él, no la salida pegada en el reporte del implementador.
2. Un **outcome terminal** de la corrida — `IMPLEMENTED`, `PARTIAL` o `UNAVAILABLE`.
3. El **manifest escrito**, o su intento fallido reportado — que falle al escribirse nunca bloquea la
   corrida, pero tampoco se calla.
4. **Sin rondas ni recovery pendientes**: mientras quede un fix round por despachar o un
   `recovery-required` sin resolver, el pane vive.

**Un agente asentado no es condición suficiente de ninguna de las cuatro.** Que el agente esté en
`idle` o en `done` no dice nada sobre el diff, el outcome, el manifest ni las rondas pendientes: es
lifecycle, y el lifecycle no cierra panes. Acá el punto muerde más fuerte que donde el delegado solo
lee: un pane en `done` tampoco prueba que el proceso dejó de escribir el árbol, y esa prueba es la que
la decisión 3 de "Validación del artefacto" exige antes de que el conductor toque un solo archivo.

**Un pane que la corrida no creó nunca se cierra.** La lista de panes propios del descriptor es la única
autorización de cierre que existe. Tampoco se construye un recolector automático global, ni se cierra
un pane ajeno "porque quedó suelto": con el patrón de reutilizar panes, ese pane puede alojar hoy a
otro agente, y acá alojar a otro agente significa tener otro escritor.

**Con las cuatro en verdadero rige `cleanup: auto`:** el conductor cierra los panes propios y anuncia
el cierre en una línea, sin pedir permiso. Con cualquier precondición en falso rige `cleanup: keep`: el
pane queda anunciado y esperando decisión, que es lo que hacen los cuatro observables de "Validación
del artefacto". El commit del conductor tras el gate humano es posterior y no condiciona nada en las
dos direcciones: cerrar el pane no aprueba el diff, y aprobar el diff no cierra el pane.
