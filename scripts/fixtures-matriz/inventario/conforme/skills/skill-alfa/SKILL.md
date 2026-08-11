---
name: skill-alfa
description: Skill sintética del corpus de fixtures. No existe en el árbol real y ningún cliente la carga.
---

# skill-alfa (sintética)

Skill inventada para ejercer el criterio de correspondencia y completitud. Sus puntos de despacho no
describen ninguna skill real: si alguno se pareciera a uno real, el modo estaría midiéndose contra el
dato que tiene que auditar.

## Corridas delegadas en vuelo

Todo worker que esta skill despacha nace con su **sobre** en `.cross-model/active/<skill>/`, escrito
**antes** del despacho. Los puntos de despacho propios son cuatro:

- el **explorador inicial**, lanzado antes del primer gate y siempre en solitario
- el **contraste por ronda**, que reanuda la misma sesión con el delta de la ronda anterior
- el **auditor de cierre**, dentro del gate de revisión manual
- los **subagentes de muestreo**, cuando el entorno los soporta y el alcance lo amerita

Campos del sobre, transiciones, sonda por turno y condiciones del retiro: `corridas-en-vuelo.md`,
hermano de este archivo. Es la regla normativa; acá solo se enumera dónde aplica.

## Explorador inicial

El conductor lo lanza con `codex exec -s read-only -C <working_dir>` y espera su sobre antes de
seguir con el resto del paso.

## Contraste por ronda

Cada ronda reanuda la sesión anterior con `codex exec resume "$SESSION_ID"` y le entrega el delta.

## Auditor de cierre

La revisión del cierre se delega con `claude -p` sobre el diff completo del paso.

## Subagentes de muestreo

El muestreo se despacha con `codex exec -s read-only` cuando el entorno lo soporta.
