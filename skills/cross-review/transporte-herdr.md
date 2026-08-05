#### Cómo persiste el revisor su veredicto — el seam

El revisor no devuelve texto: deposita un archivo. Y bajo este transporte, sobre Windows, **decirle
dónde no alcanza** — hay un mecanismo de escritura que bajo el perfil vigente no persiste (ver
"Permiso y mecanismo son cosas distintas"). Por eso el prompt materializado lleva un bloque que le
dice **cómo** escribir.

**El bloque no se inyecta siempre: tiene predicado.** La familia del revisor **se resuelve por
corrida**, no está fijada globalmente —con Claude conduciendo el revisor es Codex; con Codex
conduciendo es Claude—, así que la condición es:

> **transporte panes ∧ Windows ∧ revisor efectivo Codex**

En cualquier otra combinación el bloque **no se agrega** y el mecanismo vigente del revisor no
cambia. Cuando el predicado se cumple, la familia destinataria sí está determinada y el reference
autoriza nombrar el mecanismo concreto (`co-explore/reference.md` → "Prompt de explore (dos capas)",
que prohíbe la guía por modelo en los prompts duales y la autoriza acá).

**Un único punto de materialización, y las dos entradas de esta skill lo atraviesan.** El bloque se
inserta donde el conductor arma el prompt final, justo antes del dispatch, con una sola inserción por
prompt — insertarlo dos veces es tan defectuoso como no insertarlo, y es detectable contando
ocurrencias.

| Entrada | Qué recibe | Ancla | Marca de cierre |
|---|---|---|---|
| `review` (ronda 1) | el prompt completo del lanzamiento, con el bloque | entre `</constraints>` y `<structured_output_contract>` | `STATUS: done` |
| `review-round-n` (resume) | el delta proyectado desde el ledger, con el bloque | ídem | `STATUS: done` |
| `transportAttempt` | el prompt **completo** de nuevo: se relanza, no hay sesión viva | ídem | `STATUS: done` |
| `formatRepair` | el pedido de reemisión **a la sesión viva**, con el bloque repetido top-level | no aplica: no es un prompt con secciones | `STATUS: done` |
| `semanticAttempt` | el prompt completo, sesión nueva | ídem | `STATUS: done` |

**El ancla de esta skill no es la de `co-explore`, y confundirlas rompe la inserción.** Las plantillas
de `assets/prompts/` **no tienen `<output_contract>`**: usan `<structured_output_contract>`
(`review.md`, `review-round-n.md`). La posición congelada es
`</constraints>` → `<output_persistence>` → `<structured_output_contract>`.

**Y una posición, no sólo un momento.** Un bloque que cae dentro de `<artifact>` o `<ledger>` es
**dato citado**, no una instrucción, y pasaría el conteo dando un falso verde. Por eso se verifica
ocurrencia única **y** posición top-level, en las dos entradas.

**Placeholders**, que el conductor sustituye al materializar:

- `{ruta_salida}` — la ruta desnuda del veredicto, para que el revisor la lea.
- `{ruta_salida_literal}` — la misma ruta ya serializada como literal de PowerShell: comillas simples
  incluidas y apóstrofos internos duplicados. La serializa el conductor, que es quien la conoce.
- `{marca_cierre}` — `STATUS: done` en las dos entradas de esta skill, que la definen siempre. Por
  eso acá el bloque va **completo**, con su línea condicional incluida.

El bloque, literal —**idéntico al de `co-explore`**: el canon es uno solo, y lo que cambia entre
skills es el predicado, el ancla y la marca, no el texto:

```
<output_persistence>
Escribe tu informe completo en este archivo:

  {ruta_salida}

PASO 1 — intentá con tu herramienta habitual de edición de archivos. Si el archivo queda
escrito, terminaste: no sigas al paso 2.

PASO 2 — SÓLO si el paso 1 falló al persistir, o si te ofreció reintentar fuera del sandbox
—cosa que no debés aceptar, está prohibido en esta corrida—, caé a la primitiva de abajo.
No la uses preventivamente: es el plan B de un fallo observado, no el camino por defecto.
Si tu herramienta funcionó, este bloque no cambia nada de lo que ya hacés.

LA PRIMITIVA. Se escribe por LOTES, en varios comandos cortos, nunca en uno solo: un comando
que lleve el informe entero supera el largo que el sistema de permisos puede analizar, y ahí
el intento queda esperando una aprobación que nadie va a dar. Mantené cada comando por debajo
de unos 800 caracteres, y contá los lotes: perder uno produce un texto coherente consigo mismo
que ninguna comprobación de abajo detecta.

Cada comando es autocontenido: el estado no sobrevive de uno al siguiente, así que las
variables se redeclaran en cada uno.

Comando 1 — crea el temporal con el primer lote:

$e=[System.Text.UTF8Encoding]::new($false); [System.IO.File]::WriteAllText({ruta_salida_literal}+'.tmp','primera linea'+[char]10+'segunda linea'+[char]10,$e)

Comandos 2..N-1 — uno por lote, agregando al final:

$e=[System.Text.UTF8Encoding]::new($false); [System.IO.File]::AppendAllText({ruta_salida_literal}+'.tmp','linea con '' comilla simple'+[char]10+'otra linea'+[char]10,$e)

Comando final — valida y publica:

$e=[System.Text.UTF8Encoding]::new($false); $p={ruta_salida_literal}; $t=[System.IO.File]::ReadAllText($p+'.tmp',$e); $b=[System.IO.File]::ReadAllBytes($p+'.tmp'); if($b.Length -ge 3 -and $b[0] -eq 0xEF){throw 'BOM presente: no se publica'}; $l=@($t.Split([char]10)|Where-Object{$_.Trim() -ne ''}); if($l.Count -eq 0 -or -not [string]::Equals($l[-1].Trim(),'{marca_cierre}',[System.StringComparison]::Ordinal)){throw 'la ultima linea no vacia no es la marca de cierre: no se publica'}; Move-Item -LiteralPath ($p+'.tmp') -Destination $p -Force    # (*)

Las tres reglas del contenido:
- Escape: cada lote es un literal entre comillas simples. El único carácter que necesita
  escape es la comilla simple, y se escapa duplicándola. Ni $, ni backtick, ni @ se
  interpretan, así que una línea que sea exactamente '@ viaja como cualquier otra.
- Saltos: se agregan con +[char]10+ entre líneas y al final de cada lote. No uses "`n".
- Corte: partí donde quieras mientras cada comando quede corto; el corte no cambia el
  resultado. Lo que sí importa es no perder un lote.

Qué valida el comando final, y qué no. Verifica que no haya BOM y que la última línea no
vacía sea la marca de cierre — eso atrapa el caso más común, perder el último lote. NO
detecta un lote intermedio omitido: el resultado queda coherente consigo mismo. La validación
de formato que hace el conductor al cosechar sólo lo atrapa si esa omisión rompe el contrato
estructural; si no lo rompe, la pérdida es INDETECTABLE sin un esperado independiente. Contar
los lotes es la única defensa real, y por eso está en las reglas.

Si algo falla. Conservá el .tmp para inspección y reportá el intento como no entregado. Nunca
escribas directo sobre el destino: eso deja un archivo parcial visible, que es justamente lo
que el temporal más el rename evitan. Que la ruta final quede ausente ES la señal de "no
entregado", y es distinta de un artefacto entregado con formato inválido, que se repara sin
volver a transportar.
</output_persistence>
```

 cross-review — transporte por panes (adaptador)

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
2. Con el perfil amplio de escritura al workspace el revisor queda **habilitado** a escribir **todo el
   working dir**, no solo su ruta de salida — y ese working dir es justamente el repo que la regla 1
   le da para leer y fundamentar. **Habilitado no es capaz:** el perfil concede el permiso, pero
   ejercerlo depende del **mecanismo** con que se escriba, y hay uno que bajo este mismo perfil no
   logra persistir (ver "Permiso y mecanismo son cosas distintas"). Este punto habla del permiso
   concedido; no dice que cualquier vía de escritura vaya a funcionar.
3. El punto intermedio —repo de solo lectura con una única salida escribible— **no se ejercitó** en
   ninguno de los dos ejercicios. Es diseño sin validar, no práctica recomendada.

### Permiso y mecanismo son cosas distintas

**El hecho medido.** Bajo el perfil de escritura al workspace, sobre **Windows**, la herramienta de
edición interna de Codex **no logra persistir** el veredicto, y la escritura por **shell** desde el
mismo agente y la misma sesión **sí lo logra**.

**El alcance de esa evidencia, para no leerla de más.** El par controlado varió **una** variable —el
mecanismo— manteniendo constantes agente, sesión, perfil, repositorio, destino y operación. La ruta,
el carácter oculto del directorio y la preexistencia del archivo **no impidieron la escritura por
shell**, y **cambiarlas no reparó la herramienta** en las sondas realizadas; eso no descarta
interacciones mecanismo × ruta o mecanismo × preexistencia fuera de las combinaciones probadas.

**La capa causal queda indeterminada, y se declara así.** El perfil se mantuvo constante en todas las
sondas —probar sin él habría exigido el bypass que la regla de abajo prohíbe—, así que **no** se
puede afirmar si la causa es un defecto propio de la herramienta, de la plataforma, o una interacción
con el sandbox. Lo medido es el hecho operacional, no su explicación.

**Consecuencia para esta skill.** El revisor que deposita su veredicto necesita que el prompt le diga
**cómo** escribir, no sólo dónde. A diferencia de `co-explore`, acá la familia del destinatario está
determinada cuando el predicado se cumple, así que el bloque puede nombrar el mecanismo concreto —el
reference lo autoriza en esta skill—. Ver "Cómo persiste el revisor su veredicto".

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
