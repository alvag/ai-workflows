# Verification contract — ejemplo-multiversion

schemaVersion: 1

## v1

| ID | Requirement | Evidence | Command/observation | Expected | Baseline |
|---|---|---|---|---|---|
| pruebas | AC-1 | test | node --test ejemplo.test.mjs | suite verde | RED |
| formato | AC-2 | inspección | leer reference.md | plantilla publicada | GREEN_ALREADY |
| manual | AC-3 | manual | observar la salida | no aplica en este entorno | NOT_APPLICABLE |
| entorno | AC-4 | build | node build.mjs | build disponible | BLOCKED |

### Baseline

- pruebas: revision `abc1234` · 2026-07-22T10:00:00Z · resultado: 1 fallo
- formato: revision `abc1234` · 2026-07-22T10:00:00Z · resultado: plantilla ya presente · adjudicación: already_satisfied — se conserva como chequeo de no-regresión
- manual: revision `abc1234` · 2026-07-22T10:00:00Z · resultado: observación no aplicable · justificación: el entorno no expone interfaz gráfica
- entorno: revision `abc1234` · 2026-07-22T10:00:00Z · resultado: dependencia ausente

## v2

| ID | Requirement | Evidence | Command/observation | Expected | Baseline |
|---|---|---|---|---|---|
| pruebas | AC-1 | test | node --test ejemplo.test.mjs | suite verde | RED |
| formato | AC-2 | inspección | leer reference.md | plantilla publicada | GREEN_ALREADY |
| manual | AC-3 | manual | observar la salida | no aplica en este entorno | NOT_APPLICABLE |
| entorno | AC-4 | build | node build.mjs | build disponible | BLOCKED |

### Baseline

- pruebas: revision `def5678` · 2026-07-22T11:00:00-05:00 · resultado: 1 fallo reproducido
- formato: revision `def5678` · 2026-07-22T11:00:00-05:00 · resultado: plantilla ya presente · adjudicación: already_satisfied — se mantiene como no-regresión
- manual: revision `def5678` · 2026-07-22T11:00:00-05:00 · resultado: observación no aplicable · justificación: el entorno continúa sin interfaz gráfica
- entorno: revision `def5678` · 2026-07-22T11:00:00-05:00 · resultado: dependencia ausente
