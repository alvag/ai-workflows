# Contrato de integración — notificaciones-v2

## v1

| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |
|---|---|---|---|---|---|
| V-G1 | G1 — acordar el esquema del evento entre los dos equipos [—] | inspección | `grep -c "^evento:" acuerdo.md` | el acuerdo declara el esquema del evento | NOT_APPLICABLE |
| V-C1 | C1 — correr el flujo end-to-end con los dos servicios desplegados [AC-3, AC-4] | manual | desplegar los dos servicios y publicar una notificación | el receptor procesa el evento y responde 200 | RED |
| V-X1 | X1 — archivar el acuerdo del evento en la wiki del equipo [—] | inspección | `grep -c acuerdo wiki.md` | el acuerdo quedó archivado en la wiki | NOT_APPLICABLE |
| V-X1-bis | X1 — archivar el acuerdo del evento en la wiki del equipo [—] | inspección | `grep -c acuerdo wiki.md` | `1` | NOT_APPLICABLE |

### Baseline de v1
`hash_previo:` · `hash: 9b1c04e2`

- `id: V-G1` · `commit: 4f2a9c1` · `timestamp: 2026-06-03T09:10:00-03:00` · `justificación: la evidencia es un acuerdo entre equipos; no hay comando que ejecutar contra el código`
- `id: V-C1` · `commit: 4f2a9c1` · `timestamp: 2026-06-03T09:10:00-03:00`
- `id: V-X1` · `commit: 4f2a9c1` · `timestamp: 2026-06-03T09:10:00-03:00` · `justificación: la evidencia es un acuerdo entre equipos; no hay comando que ejecutar contra el código`
- `id: V-X1-bis` · `commit: 4f2a9c1` · `timestamp: 2026-06-03T09:10:00-03:00` · `justificación: la evidencia es un acuerdo entre equipos; no hay comando que ejecutar contra el código`
