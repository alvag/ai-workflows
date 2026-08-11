---
name: skill-epsilon
description: Skill sintética del corpus de fixtures. No existe en el árbol real y ningún cliente la carga.
---

# skill-epsilon (sintética)

Skill inventada, con un único punto de despacho: el corpus ejerce también la skill de cardinalidad
uno, donde una baja deja el inventario en cero y no en "uno menos".

## Corridas delegadas en vuelo

Todo subagente que esta skill despacha nace con su **sobre** en `.cross-model/active/<skill>/`. El
punto de despacho propio es uno:

- el **implement delegado** del último paso, que frena antes de commitear

Campos del sobre, transiciones, sonda por turno y condiciones del retiro: `corridas-en-vuelo.md`,
hermano de este archivo.

## Implement delegado

El subagente se lanza con `codex exec -s workspace-write -C <working_dir>` y su salida se cosecha del
disco.
