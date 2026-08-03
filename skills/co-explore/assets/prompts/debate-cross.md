<!-- prompt `debate-cross` · lo despacha `co-explore` · formato: xml
     placeholders: {constraints}
     ESTE ARCHIVO ES LA ENTRADA EXACTA DEL WORKER: lo que no esté acá no existe para él.
     Se escribe a archivo y nunca se arma inline; cómo llega al worker lo fija el transporte. -->

<task>
Continúa el debate. Abajo está la postura ACTUAL de la otra parte sobre la misma decisión.
Critícala de forma adversarial y luego da tu postura ACTUALIZADA. SOLO LECTURA.
</task>

<other_position>
{la postura actual del conductor, del delta de la ronda anterior}
</other_position>

{constraints}

<output_contract>
CRÍTICA: <qué falla, qué no consideró, qué riesgo ignora la otra postura>
POSTURA ACTUALIZADA: <tu postura tras la crítica: qué mantienes, qué concedes>
CONVERGENCIA: <en qué estás de acuerdo con la otra parte>
</output_contract>
