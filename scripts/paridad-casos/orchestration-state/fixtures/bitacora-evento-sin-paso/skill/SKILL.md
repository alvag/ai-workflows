# sdd-orchestrator

## Fase 3 · Cierre (centralizada, el usuario al mando)

- Gate de apertura del contrato de integración: el contrato pasa su gate antes de la primera evidencia.
- La Fase 3 revalida la versión vigente del contrato antes de ejecutar evidencia.
- Una tabla de precedencia produce el estado agregado como `ESTADO:<valor>` y nunca oculta el más grave.
- Cada ejecución de evidencia y cada cierre de tarea registra su intento en la bitácora antes de materializarse.

| # | Estado agregado | Cuándo |
|---|---|---|
| 1 | `ESTADO:no-verificado:repo-failed` | algún repo quedó en `failed` |
| 2 | `ESTADO:no-verificado:repo-blocked` | algún repo quedó en `blocked` |
| 3 | `ESTADO:no-verificado:gate-blocked` | alguna tarea `gate` quedó en `blocked` |
| 4 | `ESTADO:en-curso` | algún repo sigue en marcha |
| 5 | `ESTADO:no-verificado:integracion-pendiente` | queda una tarea de orquestación sin cerrar |
| 6 | `ESTADO:done` | todo cerrado |

Una fila ausente, `BLOCKED` o `manual` pendiente produce no verificado.
