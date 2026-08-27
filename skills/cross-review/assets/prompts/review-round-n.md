<!-- prompt `review-round-n` · lo despacha `cross-review` desde la ronda 2 · formato: xml
     placeholders: {artifact_type}, {complexity}, {working_dir}, {ronda}, {delta}, {rechazos},
                   {artefacto}, {dimensiones}, {self_review}, {modalidad}
     ESTE ARCHIVO ES LA ENTRADA EXACTA DEL WORKER: lo que no esté acá no existe para él.
     Se escribe a archivo y nunca se arma inline; cómo llega al worker lo fija el transporte.
     {delta} y {rechazos} se PROYECTAN desde el ledger, nunca se redactan aparte
     (ver reference.md → "Resume entre rondas").
     {artefacto} es el contenido COMPLETO del artefacto actualizado. El bloque que lo contiene se
     inserta si hay al menos una aplicación pendiente de revisión, y se OMITE ENTERO si no hay
     ninguna — nunca se deja vacío: un bloque vacío le dice al revisor que no hubo cambios, cuando
     lo que pasó es que no se los mandaron. Esa misma condición elige el evento con que se registra
     el cierre de la ronda.
     LA OMISIÓN SOLO APLICA CUANDO LA RONDA REUSA EL THREAD. En rondas independientes (resume no
     disponible) el bloque va SIEMPRE: no hay hilo que conserve la versión anterior, y sin él este
     archivo no le entrega al revisor ningún artefacto que revisar. El evento de cierre no cambia por
     eso: lo sigue decidiendo si hubo aplicaciones pendientes.
     Sede normativa: reference.md → "Resume entre rondas". -->

<task>
Ronda {ronda} de la revisión del artefacto "{artifact_type}". Sigue siendo una revisión de SOLO
LECTURA: no modifiques archivos. Puedes leer el código del repo en {working_dir} para fundamentar.

Esta ronda tiene dos trabajos distintos y los dos son obligatorios: responder por los rechazos que
recibiste, y revisar el artefacto actualizado.

Recorre estas dimensiones:

{dimensiones — lista enumerada D1..D10: las seis dimensiones del artifact_type en su orden
normativo, seguidas por los cuatro encargos de forma con su consigna literal}
</task>

<modalidad>
{modalidad — se omite entero en una ronda ordinaria. En la ronda de cierre se sustituye por este
bloque literal:

modalidad: cierre
- El artefacto está congelado.
- Se aplican todos los findings `high` que el conductor decide aplicar y la ronda termina ahí.
- Las respuestas a rechazos se arbitran igual, pero una defensa admisible no `high` no habilita
  edición.
- Los presupuestos no se recargan.
- Una salida no conforme o un timeout no arbitran nada y devuelven al checkpoint.}
</modalidad>

<delta>
{delta — proyección del ledger: por cada finding vivo, su ID, su estado actual, el evento que lo
llevó ahí y el tema con sus anclas}
</delta>

<rechazos_a_responder>
{rechazos — por cada ID rechazado sin responder: el finding, y el MOTIVO con que el conductor lo
rechazó}

Por **cada uno** de los IDs de arriba tienes que pronunciarte. Dos respuestas posibles:

- **ACEPTO** — el rechazo es correcto. Es una respuesta legítima y no cuesta nada: aceptar un
  rechazo bien fundado cierra el finding y libera presupuesto para lo que importa.
- **DEFIENDO** — el rechazo es incorrecto, y tienes un **argumento nuevo**.

La vara de admisión de una defensa es exigente, y conviene que la conozcas antes de escribirla:

| Es argumento nuevo | NO es argumento nuevo |
|---|---|
| refutar una **premisa concreta** del motivo del rechazo | el mero desacuerdo |
| aportar **evidencia del repo** que el rechazo no consideró | reformular el finding con otro wording |
| mostrar que el motivo se apoya en un hecho falsable **que es falso** | insistir sin evidencia nueva |

Una defensa sin argumento nuevo se evalúa como inadmisible y **cierra** el finding. Tienes **una
sola defensa por finding** en toda la corrida: si la gastas en un desacuerdo sin sustento, no la
tienes cuando la necesites.

Defender no te convierte en árbitro: una defensa admisible obliga a **re-arbitrar**, no a aceptar.
Quien decide sigue siendo el conductor.
</rechazos_a_responder>

<findings_cerrados>
{IDs cerrados, si los hay}

Estos findings están **cerrados**: se aceptó el rechazo, su defensa se evaluó como inadmisible, o el
humano del gate sostuvo el rechazo sobre su mérito al arbitrar una disputa.
**No los re-emitas.** Si reaparecen, se descartan por identidad sin arbitrarse y sin abrir ronda.
</findings_cerrados>

<artefacto_actualizado>
{artefacto}

Este es el artefacto **después** de aplicar lo que dice el delta. Revisalo: aplicar un finding es
una edición nueva que ningún revisor vio todavía, y puede no haber resuelto el problema, o haberlo
resuelto introduciendo otro.

Si una de las aplicaciones **no resolvió** el finding que reportaste, re-emitilo con su **ID
original** y con la evidencia de que el artefacto sigue fallando. Tenés **una sola** re-apertura por
finding: la segunda re-emisión del mismo tema pasa a disputa, y el conductor ya no la re-arbitra —
su resolución queda para el humano del gate.
</artefacto_actualizado>

<self_review>
{self_review — bloque cerrado aportado por la llamadora; se omite entero cuando la llamadora no
tiene catálogo. Tabla exhaustiva con columnas cerradas: comprobación · resultado · evidencia.
Resultado:
sin-hallazgos | con-hallazgos | no-corrida}
</self_review>

<grounding_rules>
- Ancla cada finding a una sección/AC/línea concreta del artefacto o del código. No inventes.
- Si algo es hipótesis (no lo pudiste verificar en el repo), dilo explícitamente.
- No comentes estilo, wording ni formato. Foco en correctitud, completitud y riesgo.
- Repite los IDs que recibiste para los temas ya conocidos; propón ID solo para temas nuevos.
- Escribe `why`, `suggestion` y `argumento` con lo que hace falta para entender el problema y
  actuar: sin preámbulos, sin repetir el artefacto y sin boilerplate. Esto calibra cuánto escribes
  POR finding y NO cuántos emites: reporta todos los que encuentres — quien filtra es el conductor.
</grounding_rules>

<constraints>
Todo el contexto que necesitas está en este prompt y en el repositorio del working dir.
- NO consultes memoria ni herramientas MCP de ningún tipo.
- NO busques en la web.
- NO accedas a nada fuera del working dir.
- DENTRO del working dir, lee el código con libertad: fundamentar los findings es tu tarea.
Emite tu veredicto en el formato pedido y termina el turno.
</constraints>

<structured_output_contract>
VERDICT: APPROVED | REVISE

RESPUESTAS A RECHAZOS:
- <ID>: ACEPTO | DEFIENDO
  argumento: <si defiendes, el argumento nuevo; si aceptas, una línea>

FINDINGS NUEVOS:
- [high|medium|low] <título corto del problema>
  proposed_id: <ID que propones para este tema>
  procedencia: reemision | regresion | original
  why: <por qué importa — qué se rompe / qué falta>
  suggestion: <cambio concreto propuesto>
  refs: <AC-n | sección del artefacto | path:line>
  confidence: <high|medium|low>

Si no tienes findings nuevos, escribe "FINDINGS NUEVOS: (ninguno)".

Reglas de validación, distintas por bloque:

- En **RESPUESTAS A RECHAZOS** el bloque es exhaustivo sobre los IDs que recibiste. Omitir un ID,
  duplicarlo, o responder por un ID que no está en la lista hace la salida **no conforme**, y
  entonces no se arbitra ningún bloque de esta salida — ni siquiera los findings nuevos.
- En **FINDINGS NUEVOS** un ID que el conductor no conoce es lo normal: para eso es `proposed_id`.
  Descubrir algo nuevo en una ronda tardía es comportamiento esperado, no una anomalía. No inventes
  hallazgos para llenar el bloque, pero tampoco te calles uno real por ser tarde.

`procedencia` es obligatorio para cada finding y se determina con estos predicados literales, en
orden de precedencia:

- `reemision` — el tema ya tiene identidad en el ledger de esta corrida;
- `regresion` — tema sin identidad previa cuya causa el revisor ancla a una edición aplicada en una
  ronda anterior de esta corrida;
- `original` — todo lo demás.

COBERTURA:
- D1: examinada-sin-hallazgos | examinada-con-hallazgos | no-examinable — <motivo>
- ...
- D10: examinada-sin-hallazgos | examinada-con-hallazgos | no-examinable — <motivo>

Emite una línea por cada dimensión entregada en `{dimensiones}`, con exactamente uno de los tres
estados. `no-examinable` exige motivo. La rendición es exhaustiva: omitir una dimensión hace la
salida no conforme. La cobertura calibra qué se recorre y no cuántos findings se emiten. Enumerar
una dimensión sin hallazgos no autoriza a omitir uno real ni convierte la ausencia en prueba de
correctitud. "no queda ninguno" es una respuesta legítima.

Debes emitir REVISE si defiendes algún rechazo: una defensa sin evaluar es, por definición, algo
sin resolver.

La última línea no vacía de tu salida debe ser exactamente:

STATUS: done

Esa marca va una sola vez y al final. Es lo que distingue "terminé" de "me cortaron a mitad": sin
ella tu salida se trata como incompleta, aunque el contenido parezca entero.
</structured_output_contract>

<dig_deeper_nudge>
No te quedes en lo superficial. Busca el AC que falta, el caso borde no cubierto, el supuesto no
declarado, la dependencia no vista, el contrato que no cierra. Reporta todo lo que encuentres con su
severidad y su confianza: el filtrado lo hace el conductor después, no vos. Lo único que no debe
aparecer es un finding que no puedas anclar — no inventes para parecer productivo.
</dig_deeper_nudge>
