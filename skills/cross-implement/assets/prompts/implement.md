<!-- prompt `implement` · lo despacha `cross-implement` · formato: texto plano
     placeholders: (ninguno)
     ESTE ARCHIVO ES LA ENTRADA EXACTA DEL WORKER: lo que no esté acá no existe para él.
     Se escribe a archivo y nunca se arma inline; cómo llega al worker lo fija el transporte. -->

GOAL: <un párrafo — cómo se ve "terminado">
SPEC: Lee <work_order> en la raíz del repo. Es un contrato CONGELADO y ya aprobado; úsalo como
  contexto. Tu alcance ejecutable es exclusivamente el bloque <block_id>: entran <included_tasks>
  y quedan fuera <excluded_tasks>. Implementa ese bloque exactamente. Si un paso es imposible tal
  como está escrito, implementa la versión fiel más cercana y reporta la desviación — no rediseñes.
KEY PATHS: <archivos/dirs a tocar, y los que debe leer primero (reúso identificado)>
CONSTRAINTS: <"no toques X", estilo del repo, dependencias que no deben cambiar.
  Siempre incluir: no commitees, no toques .plans/ ni .specify/ ni cross-implement/>
NON-GOALS: <explícitamente fuera de alcance — del "Out of scope"/AC del work order>
PROOF: Corre `<proof_cmd>` e incluye su salida completa y exit code en tu reporte.
OUTPUT: Termina con el reporte del "Formato del reporte" (abajo), cerrando con STATUS: done.
