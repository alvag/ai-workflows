# Referencia de skill-anclada

Detalle sintético. La columna `sandbox` aparece a propósito en **dos** tablas: es la sede que ejerce
la selección múltiple legítima —dos nodos que colapsan a un único valor porque convergen al mismo
token— y que un resolutor demasiado estricto rechazaría.

## Perfil por worker

| worker | sandbox | escritura | familia | transporte |
|---|---|---|---|---|
| explorador | solo lectura | read-only | otra familia | cli-exec |
| refutador | workspace-write | workspace-write | misma familia | subagent |

## Perfil efectivo por corrida

| worker | sandbox | contrato |
|---|---|---|
| explorador | read-only | skills/skill-anclada/reference.md#contrato-de-salida |
| refutador | workspace-write | skills/skill-anclada/reference.md#contrato-de-salida |

## Anclas de invocación

| punto | ancla | autoridad | rol | variante |
|---|---|---|---|---|
| explorador | skills/skill-anclada/SKILL.md#como-se-despacha | Conductor | design-reviewer | ninguna |

## Contrato de salida

El explorador entrega un índice compacto y el detalle por hallazgo.
