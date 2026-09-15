# Transporte por terminales: Herdr

Este adaptador opera sobre el panel Herdr que `detectar` resolvió. El sobre de cada verbo conserva `verbo`, `resultado`, `plataforma` y evidencia; `detectar` publica `adaptador: herdr`. Un `0` es afirmativo, un `1` es adverso declarado, un `2` indica entrada ilegible y un `3` que la plataforma o su mecánica no es utilizable.

<!-- verbos:inicio -->
| Verbo | Mecanismo | Acredita | No acredita | Modo de falla |
|---|---|---|---|---|
| `detectar` | Resuelve `HERDR_PANE_ID` contra `herdr pane list`. | Identidad viva y adaptador seleccionado. | Que una variable presente sea una identidad viva. | Una consulta fallida vuelve la identidad inconsultable; sin una única identidad resoluble, el destino es headless. |
| `crear` | `herdr pane split --direction right,down --cwd <ruta>`, seguido de `pane layout`. | Panel, misma pestaña, `cwd` y geometría: rectángulos, dirección y ratio se releen sin foco. | Que un split aceptado haya quedado dentro del alcance sin postcondición. | Si layout contradice el pedido o el panel queda fuera del worktree consentido, se cierra y no se asienta. |
| `lanzar` | `agent start --kind` y `agent prompt` con la ruta del encargo. | Readiness nativa y síncrona; perfil lanzado e invocación. | Modelo o esfuerzo efectivo de un agente vivo. | Un CLI puede normalizar o rechazar silenciosamente un valor: se registra lo invocado y un valor rechazado termina con causa. |
| `enviar` | `agent prompt` al agente ya lanzado; correlaciona el acuse con `state_change_seq`. | Entrega por ruta y transición posterior al envío. | Que la transición provenga exclusivamente de este envío. | Una intervención concurrente o transición entre sondeos puede simular u ocultar el acuse. |
| `esperar` | Sondeo de artefacto, deadline y `pane list` o `agent_status`. | Liveness del panel y, donde se observa, estado del agente. | Validez del artefacto; la decide `cosechar`. | Los estados combinados son derivados; su modo de falla se declara en la tabla de estados. |
| `cosechar` | Ejecuta el pipeline de validación sobre el artefacto publicado. | Veredicto del pipeline y su etapa. | Que texto visible en el panel sea el informe. | Archivo ausente o pipeline adverso no se interpreta como terminado válido. |
| `renombrar` | `pane rename`, releído con `pane get`. | Nombre nativo del panel, sin arrastrar hermanos. | Que un nombre solicitado se aplicó sin relectura. | Si la relectura no coincide, el resultado es adverso y conserva evidencia. |
| `cerrar` | `pane process-info`, `pane close` y comprobación del grupo de procesos. | Cierre y, al liquidar, cese observado del árbol propio. | Cese no comprobable de cercar. | Un `ok` sin grupo observado en cero no acredita cese; declara residuales y no habilita fallback. |
| `lanzar-conductor` | No hay mecanismo medido en Herdr. | Ninguna transferencia de autoridad. | Lanzamiento, sesión y acuse del conductor. | Devuelve mecánica no obtenida; no se inventa ni implementa aquí. |
<!-- verbos:fin -->

## Resolución de plataforma

La detección consulta ambas identidades; no elige Herdr por presencia de entorno. Cada caso tiene un destino explícito. `headless` cubre todo caso que no resuelva una plataforma utilizable.

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

La autoridad de finalización es el artefacto publicado atómicamente y validado por `cosechar`, no el estado que reporte Herdr. Los cinco primeros estados son universales; los dos últimos quedan sujetos a lo que la plataforma acredita.

| Estado | Observable | Fuerza | Modo de falla |
|---|---|---|---|
| `terminado` | Artefacto publicado y panel muerto. | derivado | modo de falla: un archivo presente pero inválido no es finalización; `cosechar` lo rechaza. |
| `terminado-vivo` | Artefacto publicado y panel vivo. | derivado | modo de falla: una lectura de liveness atrasada puede conservar transitoriamente el panel como vivo. |
| `trabajando` | Sin artefacto, panel vivo y antes del deadline. | derivado | modo de falla: la ausencia de artefacto no prueba actividad interna. |
| `vencido` | Sin artefacto, panel vivo y deadline vencido. | derivado | modo de falla: un reloj incorrecto puede vencer antes o después de lo debido. |
| `muerto` | Sin artefacto y panel muerto, aun si el deadline ya venció. | derivado | modo de falla: una lista de panes atrasada puede declarar muerte prematuramente. |
| `listo` | `agent_status` informa disponibilidad para recibir el encargo. | nativo | No aplica: se omite si el estado del agente no se puede leer. |
| `bloqueado` | No se acredita: el enum existe, pero no se observó con ventana declarada. | omitido | No aplica: no se infiere una aprobación pendiente. |
