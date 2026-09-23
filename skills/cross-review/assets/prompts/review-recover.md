<!-- prompt `review-recover` · lo despacha `cross-review` en la recuperación única tras vencer el
     tope de una ronda · formato: xml · placeholders: ninguno
     ESTE ARCHIVO ES LA ENTRADA EXACTA DEL WORKER: lo que no esté acá no existe para él.
     Se escribe a archivo con la tool de escritura del agente y nunca se arma inline; viaja por la
     receta de resume de su vía, reanudando el mismo hilo que se interrumpió.
     No repite el formato de salida a propósito: remite al que pidió el último prompt de esa sesión,
     y por eso no se desincroniza de `review.md` ni de `review-round-n.md`.
     Sede normativa: reference.md → "Recuperación tras vencer el tope". -->

<task>
Tu turno anterior en esta sesión se interrumpió: venció el tope de tiempo del conductor antes de
que emitieras tu salida. No es un error tuyo ni un pedido nuevo.

No sigas explorando. No leas más archivos ni corras más comandos: trabaja solo con lo que ya
examinaste en esta sesión. Sigue siendo una revisión de SOLO LECTURA: no modifiques archivos.

Emite ahora la salida que pidió el último prompt de esta sesión, en su formato exacto y completo,
con todos sus bloques y con la marca final que ese formato exige.

En la cobertura, toda dimensión que no llegaste a recorrer antes de la interrupción va como
`no-examinable — interrumpido antes de examinarla`. No la marques examinada si no la examinaste: un
veredicto sobre algo que no miraste es peor que declarar que no lo miraste.

La última línea no vacía de tu salida debe ser exactamente:

STATUS: done
</task>
