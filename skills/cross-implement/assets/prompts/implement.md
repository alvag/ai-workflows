<!-- prompt `implement` · lo despacha `cross-implement` · formato: texto plano
     placeholders: la ranura PROOF se repite una línea por comando de `proof_cmd`, en su orden;
     con la lista vacía NO se emiten ni la ranura PROOF, ni las dos cláusulas de CONSTRAINTS que
     la referencian, ni el bloque PROOF del reporte — quedarían apuntando a una ranura ausente.
     La línea de canales heredados de CONSTRAINTS se emite SIEMPRE, haya comandos o no.
     ESTE ARCHIVO ES LA ENTRADA EXACTA DEL WORKER: lo que no esté acá no existe para él, y es la
     ÚNICA sede del formato del reporte — `reference.md` describe qué se consume, no lo transcribe.
     Se escribe a archivo y nunca se arma inline; cómo llega al worker lo fija el transporte. -->

GOAL: <un párrafo — cómo se ve "terminado">
SPEC: Lee <work_order> en la raíz del repo. Es un contrato CONGELADO y ya aprobado; úsalo como
  contexto. Tu alcance ejecutable es exclusivamente el bloque <block_id>: entran <included_tasks>
  y quedan fuera <excluded_tasks>. Implementa ese bloque exactamente. Si un paso es imposible tal
  como está escrito, implementa la versión fiel más cercana y reporta la desviación — no rediseñes.
KEY PATHS: <archivos/dirs a tocar, y los que debe leer primero (reúso identificado)>
CONSTRAINTS: <"no toques X", estilo del repo, dependencias que no deben cambiar.
  Siempre incluir: no commitees, no toques .plans/ ni .specify/ ni cross-implement/>
  No uses servidores MCP, hooks, apps ni plugins de tu entorno: ni memoria persistente, ni notas
  de sesión, ni ningún canal que no sea este turno. Tu única salida durable son el diff en el
  directorio de trabajo y el reporte final.
  (solo si hay comandos de PROOF) Esto NO limita los comandos de PROOF: esos están autorizados por
  el contrato y se corren aunque toquen la red o un servicio.
  (solo si hay comandos de PROOF) Si un comando de PROOF reporta problemas en archivos que tu
  bloque no toca, repórtalos sin corregir: arreglar lo que está fuera de los archivos de tu bloque
  es desviarse del alcance.
NON-GOALS: <explícitamente fuera de alcance — del "Out of scope"/AC del work order>
PROOF: Corre `<comando 1>` e incluye su salida completa y exit code en tu reporte.
PROOF: Corre `<comando 2>` e incluye su salida completa y exit code en tu reporte.
  Corre cada comando de forma independiente: si uno falla, no saltes los siguientes — córrelos
  todos y reporta cada salida y cada exit code por separado.
OUTPUT: Termina con este reporte exacto. Empieza cada línea del reporte en la COLUMNA 0, sin
  sangría: la última línea se busca anclada al margen (`STATUS: done`), así que un reporte
  correcto pero indentado no se reconoce y te dan por colgado cuando ya terminaste.

FILES:
- <path> — <qué cambió y por qué, una línea>
PROOF:   (un bloque por comando, en el orden en que se pidieron; se omite con lista vacía)
- COMMAND: <el comando exacto, tal como se pidió>
  EXIT_CODE: <n>
  OUTPUT:
  <salida verbatim de ese comando>
DEVIATIONS:
- <desviación del work order + razón>   (o "ninguna")
STATUS: done
