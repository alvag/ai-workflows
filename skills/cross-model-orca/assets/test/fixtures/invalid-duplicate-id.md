# Verification contract — id-duplicado

schemaVersion: 1

## v1

| ID | Requirement | Evidence | Command/observation | Expected | Baseline |
|---|---|---|---|---|---|
| v1 | AC-1 | test | node --test uno.test.mjs | suite verde | RED |
| v1 | AC-2 | test | node --test dos.test.mjs | suite verde | RED |

### Baseline

- v1: revision `abc1234` · 2026-07-22T10:00:00Z · resultado: 1 fallo
