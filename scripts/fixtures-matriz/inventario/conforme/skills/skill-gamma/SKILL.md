---
name: skill-gamma
description: Skill sintética del corpus de fixtures. No existe en el árbol real y ningún cliente la carga.
---

# skill-gamma (sintética)

Skill inventada. Dos de sus puntos anclan en `reference.md` y el tercero en este mismo archivo: el
corpus ejerce que una misma skill reparta sus anclas entre dos documentos.

## Corridas delegadas en vuelo

Todo implementador que esta skill despacha nace con su **sobre** en `.cross-model/active/<skill>/`.
Los puntos de despacho propios son tres:

- el **implementador inicial**, lanzado con el prompt-contrato tras los gates previos
- cada **ronda del fix loop**, que reanuda esa misma sesión con el delta
- el **verificador de diff**, que lee el diff completo como un PR ajeno

Campos del sobre, transiciones, sonda por turno y condiciones del retiro: `corridas-en-vuelo.md`,
hermano de este archivo.

## Verificador de diff

El diff se manda a revisar con `claude -p` antes del gate humano.
