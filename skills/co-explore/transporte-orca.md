# Transporte por terminales: Orca

Este adaptador opera sobre el terminal Orca que `detectar` resolvió. Adopta la capa supervisada para el ciclo de vida del worker; la capa primitiva se usa solo para iniciar el cese con `terminal close`, porque es lo único que la supervisada no inicia. El sobre de cada verbo conserva `verbo`, `resultado`, `plataforma` y evidencia.

<!-- verbos:inicio -->
| Verbo | Mecanismo | Acredita | No acredita | Modo de falla |
|---|---|---|---|---|
| `detectar` | Resuelve `ORCA_TERMINAL_HANDLE` contra `orca terminal list --json` y publica `adaptador: orca`. | Identidad viva y adaptador seleccionado. | Que una variable presente sea una identidad viva. | Una consulta fallida vuelve la identidad inconsultable; sin una única identidad resoluble, el destino es headless. |
| `crear` | `terminal split` desde el terminal propio; después relee el worktree creado. | Panel en la misma pestaña y orden de hermanos. | Geometría releíble o un `cwd` aplicado al split: hereda el worktree activo de la UI. | La geometría es derivada; modo de falla: dirección y tamaño no se pueden releer sin foco. Si el worktree difiere del consentido, se cierra y no se asienta. |
| `lanzar` | En este orden: `terminal send` arranca el agente en el panel con su perfil en las banderas del propio CLI, se espera a que `agentIdentity` alcance la familia, y recién entonces `run-create`, `task-create` y `worker-start --terminal`, que se **adjunta** a ese agente. | Readiness por `agentIdentity`, acuse de dispatch y perfil lanzado con su fuente por campo. | Perfil efectivo del agente adjunto; `launch.effective` queda en `null` en la vía adjunta, y `--model`/`--effort` no se combinan con `--terminal`, por eso el perfil viaja en el CLI del agente. | Un CLI puede normalizar o rechazar silenciosamente un valor: se registra lo invocado y un valor rechazado termina con causa. Un panel sin agente nunca alcanza readiness, y esa es la falla que un split sin `--command` produce. |
| `enviar` | La capa supervisada acusa `dispatch_input: accepted`. | Entrega inicial del encargo por ruta. | Reintento sobre dispatch activo o el mismo terminal. | Orca rechaza ambos reintentos; informa mecánica no obtenida, sin relanzar en silencio. |
| `esperar` | Ruta del artefacto, deadline y estado supervisado `{worker, terminal, liveness}`. | Liveness y estado del agente de la capa supervisada. | Que la capa primitiva describa el estado del agente. | Los estados combinados son derivados; su modo de falla se declara en la tabla de estados. |
| `cosechar` | Ejecuta el pipeline y, si corresponde, lee y acusa el buzón supervisado. | Veredicto del pipeline y acuse asentado del lote. | Que transcript o pantalla sean el informe. | Un mensaje ausente no invalida el artefacto; un lote no asentado no se acusa para permitir reentrega. |
| `renombrar` | `terminal rename` alcanza la pestaña y arrastra hermanos. | Omisión explícita, `aplicado: false` y `motivo_omision`. | Renombrar solo el panel. | No intenta renombrar: cambiaría la pestaña del conductor y los paneles hermanos. |
| `cerrar` | `terminal close` inicia el cese; la supervisada liquida con `worker-release` o cerca con `worker-abandon`, y recién `worker-list` dice si quedó `released`. | El `terminalState` de la contabilidad de la plataforma, más el código del close; los residuales se enumeran con el estado que se observó. | Que `worker-stop` inicie el cese. | El código de salida de `worker-release` **no** acredita: `retained`, `release_pending` y `already_released` salen 0, y `retained` es el worker todavía activo o una identidad que Orca no pudo probar. Sin cese acreditado no hay fallback. |
| `lanzar-conductor` | No hay mecanismo medido para transferir el conductor: ninguna superficie de Orca sostiene un acuse atribuible a la sesión nueva. | Ninguna transferencia de autoridad. | Que `worker_done` acredite origen: con `--from` se suplanta desde cualquier terminal, falseando `from_handle` y `sender_pane_key`. | Devuelve `mecanica-no-obtenida` y conserva al conductor original; no consulta la plataforma, porque ninguna respuesta puede cambiar el resultado. |
<!-- verbos:fin -->

## Resolución de plataforma

La detección consulta ambas identidades; no elige Orca por presencia de entorno. Cada caso tiene un destino explícito. `headless` cubre todo caso que no resuelva una plataforma utilizable.

<!-- casos:inicio -->
| Caso | Destino | Regla |
|---|---|---|
| `sin-plataforma` | `headless` | Ninguna identidad está presente. |
| `orca-rancia` | `headless` | Orca no resuelve y Herdr está ausente. |
| `solo-orca` | `orca` | Solo Orca resuelve, incluso si Herdr es rancia o inconsultable. |
| `orca-inconsultable` | `headless` | Orca no se puede consultar y Herdr está ausente. |
| `herdr-rancia` | `headless` | Herdr no resuelve, sin Orca resoluble. |
| `identidades-rancias` | `headless` | Ninguna identidad viva resuelve. |
| `solo-herdr` | `herdr` | Solo Herdr resuelve, incluso si Orca es rancia o inconsultable. |
| `herdr-inconsultable` | `headless` | Herdr no se puede consultar y Orca está ausente o rancia. |
| `ambas-resuelven` | `headless` | No hay observable que identifique al anfitrión. |
| `mecanica-ilegible` | `headless` | Las dos consultas son inconsultables; la ejecución informa mecánica no obtenible. |
<!-- casos:fin -->

## Perfil y permisos

El worker toma modelo y esfuerzo de su perfil de rol; el conductor hereda la sesión que lo lanza, salvo indicación contraria. Quien lanza persiste `perfil_lanzado`, con valor y fuente por campo, y la invocación construida. El valor efectivo de un agente vivo no es observable en ninguna plataforma soportada: una normalización o rechazo silencioso del CLI no se detecta.

El invariante de aislamiento no cambia: se acota. En la vía headless siguen íntegros el comportamiento read-only por contrato, el aislamiento por permisos y la regla de que el conductor no persiste cambios en el working tree del usuario. En esta vía los workers no están aislados y cargan la configuración personal del usuario. El riesgo asumido se mide en tres consecuencias: esa configuración amplía la superficie de permisos; consume presupuesto de contexto antes de leer el encargo; y el flag de sandbox del agente no acota la escritura. El último hecho se midió en Herdr y Orca, con Codex y Claude.

## Estados al esperar

La autoridad de finalización es el artefacto publicado atómicamente y validado por `cosechar`, no el estado de Orca. Los cinco primeros estados son universales; los dos últimos quedan sujetos a lo que la capa supervisada acredita.

| Estado | Observable | Fuerza | Modo de falla |
|---|---|---|---|
| `terminado` | Artefacto publicado y liveness supervisada muerta. | derivado | modo de falla: un archivo presente pero inválido no es finalización; `cosechar` lo rechaza. |
| `terminado-vivo` | Artefacto publicado y terminal vivo. | derivado | modo de falla: una lectura de liveness atrasada puede conservar transitoriamente el terminal como vivo. |
| `trabajando` | Sin artefacto, terminal vivo y antes del deadline. Es el destino de toda espera no terminal en esta plataforma, porque el estado del agente no se consulta. | derivado | modo de falla: la ausencia de artefacto no prueba actividad interna. |
| `vencido` | Sin artefacto, terminal vivo y deadline vencido. | derivado | modo de falla: un reloj incorrecto puede vencer antes o después de lo debido. |
| `muerto` | Sin artefacto y terminal muerto, aun si el deadline ya venció. | derivado | modo de falla: `orphaned` o `connected` atrasados pueden declarar muerte prematuramente. |
| `listo` | **No se emite al esperar.** El verbo no consulta estado de agente en esta plataforma, así que los estados derivados de él —`listo`, `bloqueado`, `detenido-sin-cierre`, `desconocido`, `no-reconocido` y `estado-no-obtenible`— no aparecen acá. La capa supervisada informa `state` y `stage`, pero el sondeo no los lee. | omitido | No aplica: su ausencia es una omisión declarada del transporte, no una lectura fallida, y por eso no se clasifica como estado ilegible. |
| `bloqueado` | Ídem: Orca no acredita espera de aprobación en ninguna capa y el verbo no la consulta. | omitido | No aplica: no se infiere desde fotogramas ni TUI. |
