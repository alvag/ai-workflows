# Bitácora de transiciones — notificaciones-v2

- `id: 1` · `paso: promover-repo` · `actor: orquestador` · `objeto: servicio-a` · `resultado: consumado` · `timestamp: 2026-06-03T10:01:00-03:00`
- `id: 2` · `paso: promover-repo` · `actor: orquestador` · `objeto: servicio-b` · `resultado: consumado` · `timestamp: 2026-06-03T10:02:00-03:00`
- `id: 3` · `paso: despachar-repo` · `actor: orquestador` · `objeto: servicio-a` · `resultado: rechazado` · `timestamp: 2026-06-03T10:03:00-03:00`
- `id: 4` · `paso: despachar-repo` · `actor: orquestador` · `objeto: servicio-b` · `resultado: consumado` · `timestamp: 2026-06-03T10:04:00-03:00`
- `id: 5` · `paso: ejecutar-evidencia` · `actor: equipo-arquitectura` · `objeto: G1` · `resultado: consumado` · `timestamp: 2026-06-03T10:05:00-03:00` · `fila: V-G1` · `contrato: v1` · `ancla: acuerdo-evento=v3` · `observado: el acuerdo declara el esquema del evento`
- `id: 6` · `paso: cerrar-tarea` · `actor: orquestador` · `objeto: G1` · `resultado: consumado` · `timestamp: 2026-06-03T10:06:00-03:00`
