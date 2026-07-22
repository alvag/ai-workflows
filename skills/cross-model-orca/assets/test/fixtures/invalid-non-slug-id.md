# Verification contract — id-invalido

schemaVersion: 1

## v1

| ID | Requirement | Evidence | Command/observation | Expected | Baseline |
|---|---|---|---|---|---|
| ID con espacios | AC-1 | test | node --test ejemplo.test.mjs | suite verde | RED |

### Baseline

- ID con espacios: revision `abc1234` · 2026-07-22T10:00:00Z · resultado: 1 fallo
