---
name: skill-anclada
---

# skill-anclada (sintética)

Esta skill no existe en el árbol real. Es la **sede sintética** de los fixtures del resolutor de
anclas: ninguna de sus líneas describe a una skill del ecosistema, y por eso el resolutor no puede
heredar de acá la interpretación de la matriz real.

skill: co-explore

## Señales de detección

Refutar el plan
auditar el diff

## Dueño del despacho: el conductor de skill-anclada

El dato vive en el propio encabezado, que es lo que este tipo de sede selecciona.

## Modos y su nivel de escritura

workspace-write
solo lectura

## Cómo se despacha

| worker | sandbox | deadline |
|---|---|---|
| explorador | solo lectura | 600 |
| refutador | workspace-write | 900 |

Sin capacidad,   el conductor marca UNAVAILABLE y abre gate humano.

El binario codex se detecta con `command -v codex` antes de lanzar nada.

La configuración que enciende el punto:

```yaml
co_explore: "on"
esfuerzo: alto
```

## Gate del despacho

El punto no se despacha solo: se anuncia y se espera confirmación explícita.
