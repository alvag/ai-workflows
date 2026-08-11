---
name: skill-delta
description: Skill sintética del corpus de fixtures. No existe en el árbol real y ningún cliente la carga.
---

# skill-delta (sintética)

Skill inventada, con dos puntos de despacho y ningún archivo de referencia.

## Corridas delegadas en vuelo

Todo agente que esta skill despacha nace con su **sobre** en `.cross-model/active/<skill>/`. Los
puntos de despacho propios son dos:

- el **fan-out por repo**, un agente por repo elegible y libre
- el **cierre por repo**, que consolida el resultado de cada repo antes del gate

Campos del sobre, transiciones, sonda por turno y condiciones del retiro: `corridas-en-vuelo.md`,
hermano de este archivo.

## Fan-out por repo

Cada repo elegible se despacha con `codex exec -s workspace-write -C <ruta-del-repo>`, todos lanzados
antes de esperar a ninguno.

## Cierre por repo

El cierre de cada repo se delega con `claude -p` y su resultado se cosecha del disco.
