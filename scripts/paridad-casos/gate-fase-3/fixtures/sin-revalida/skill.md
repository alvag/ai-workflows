# sdd-orchestrator — recorte de la Fase 3 para el arnés de paridad

## Fase 3 — evidencia de integración

### Gate de apertura del contrato de integración

Antes de ejecutar cualquier evidencia, la Fase 3 usa el contrato congelado y
comprueba que su conjunto de IDs no cambió respecto de la versión anterior.

### Agregación

Una fila ausente o en BLOCKED deja el veredicto en no verificado: la agregación no puede dar
verde sin la evidencia de todas las filas.
