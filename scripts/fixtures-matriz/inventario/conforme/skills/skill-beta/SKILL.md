---
name: skill-beta
description: Skill sintética del corpus de fixtures. No existe en el árbol real y ningún cliente la carga.
---

# skill-beta (sintética)

Skill inventada. Sus tres puntos anclan sus sitios de invocación en `reference.md` y no en este
archivo: el ancla de invocación y la sede del inventario no tienen por qué ser el mismo documento.

## Corridas delegadas en vuelo

Todo revisor que esta skill despacha nace con su **sobre** en `.cross-model/active/<skill>/`. Los
puntos de despacho propios son tres:

- el **revisor por ronda** del loop de revisión, ronda 1 y cada ronda que reanuda el mismo hilo
- el **refutador por hallazgo**, cuando la refutación se delega en vez de resolverla el conductor
- el **sintetizador final**, que consolida los veredictos en una sola conclusión

Campos del sobre, transiciones, sonda por turno y condiciones del retiro: `corridas-en-vuelo.md`,
hermano de este archivo.
