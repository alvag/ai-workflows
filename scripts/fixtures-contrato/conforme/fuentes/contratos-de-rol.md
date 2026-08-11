# Contratos sintéticos de rol y autoridad por punto

**Este archivo no describe el ecosistema real.** Es la **sede sintética** de las procedencias
ancladas de la sección de familias de rol y de la de asignaciones de despacho del contrato
sintético que vive al lado. Su función es que los campos declarados vigentes u observados se
resuelvan con el **mismo** verificador semántico que las hojas de la matriz, en vez de leerse como
texto libre.

Es sintético a propósito: la propiedad que la sección de roles ejerce es que el resolutor corra y
coteje, no que estas frases sean las del ecosistema. Lo que **sí** es normativo son los cinco
literales de familia y las trece asignaciones, y su defensa es otra: el puntero al roadmap, que
resuelve contra el árbol real.

## Contratos por familia de rol

| rol | entrada | salida | scope |
|---|---|---|---|
| explorer | paquete de contexto congelado y objetivo de mapeo, sin acceso a los mapas de los demás | índice compacto de hallazgos, con el detalle disponible bajo demanda | lectura del árbol de trabajo; ninguna escritura |
| investigator | síntoma reproducible y las corridas previas que ya fallaron | causas raíz rankeadas con su plan de verificación | — |
| design-reviewer | el artefacto de diseño en revisión y el criterio contra el que se lo juzga | findings con severidad y el veredicto derivado del ledger | lectura del artefacto y del árbol que lo respalda |
| bounded-implementer | un work order congelado, con su criterio de hecho y su alcance de archivos | el diff producido y el receipt de la corrida | escritura acotada al working dir declarado por el work order |
| diff-reviewer | el diff a revisar y el contrato que ese diff dice cumplir | findings sobre el diff, cada uno con su ubicación | — |

## Autoridad final por punto de despacho

La autoridad se declara **por punto y variante**, no por familia de rol: dos puntos de la misma
familia pueden cerrarse en manos distintas.

| punto de despacho | autoridad final |
|---|---|
| co-explore · fan-out dual | el conductor arbitra entre los dos mapas y no produce uno propio |
| co-explore · debate | el conductor es voz y decide tras leer la postura |
| cross-review · revisor por ronda | el conductor adjudica cada finding y el gate humano cierra |
| cross-implement · implementador inicial | el conductor revisa el diff como un PR ajeno y es quien commitea |
| cross-implement · fix loop | el conductor corre la prueba él mismo y decide si hay otra ronda |
| sdd-flow · analyze | el conductor escribe el plan con lo que el survey haya encontrado |
| sdd-flow · implementer por task | el conductor cierra la task tras leer su reporte y su diff |
| sdd-flow · reviewer por task | el conductor adjudica los findings de la task |
| sdd-flow · revisión final | el gate humano cierra el flujo con los findings agregados a la vista |
| sdd-orchestrator · fan-out por repo | el orquestador consolida y ningún worker cierra el objetivo madre |
| sdd-pr-feedback · implement delegado | el conductor responde el comentario del PR y decide si se resuelve |
| bitbucket-code-review · panel | el conductor consolida el panel en una sola conclusión |
| bitbucket-code-review · validador adversarial | el conductor decide si la refutación tumba el finding |
