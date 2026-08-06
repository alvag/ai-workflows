# Baseline normativo del sobre en vuelo

## Verification

| ID | Requisito | Comando | Esperado |
|---|---|---|---|
| V1 | AC-1 — campos raíz, por worker y por intento, más sub-esquemas exactos | `--ac 1` | ok |
| V2 | AC-1 — no-estado semántico, sede de rechazo y frontera entre registros | `--ac 1b` | ok |
| V3 | AC-2 — transiciones, outcomes y orden del orquestador | `--ac 2` | ok |
| V4 | AC-2 — retiro, escritor único, nacimiento y adopción | `--ac 2b` | ok |
| V5 | AC-3 — agregación multi-worker y resumen de descendencia | `--ac 3` | ok |
| V6 | AC-3 — un ancestro no cosecha ni retira sobres indirectos | `--ac 3b` | ok |
| V7 | AC-4 — archivo, identidad y barrido por topología | `--ac 4` | ok |
| V8 | AC-5 — cierre de turno, sonda y presupuesto de espera | `--ac 5` | ok |
| V9 | AC-6 — fuentes vigentes, referencia de proceso y continuidad operativa | `--ac 6` | ok |
| V10 | AC-7 — precedencia ante discrepancias | `--ac 7` | ok |
| V11 | AC-8 — límite declarado sin afirmar ejecución | `--ac 8` | ok |
| V12 | AC-9 — sidecar append-only para datos nuevos | `--ac 9` | ok |
| V13 | AC-10 — relanzamiento seguro y rutas exclusivas | `--ac 10` | ok |
| V14 | AC-11 — error y cancelación como terminales propios | `--ac 11` | ok |
| V15 | AC-12 — trece puntos de despacho y siete punteros locales | `--ac 12` | ok |
| V16 | AC-13 — siete copias idénticas, trigger y README | `--ac 13` | ok |
| V17 | AC-14 — tercera excepción y cita normativa | `--ac 14` | ok |
| V18 | AC-15 — ninguna clave de configuración nueva | `--ac 15` | ok |
| V19 | AC-16 — guardas del repo sin regresión | `--ac 16` | ok |

### v2

Identidad: `(2ed62dd, sha256 del verificador)`.

#### Baseline de v2

| ID | commit | sha256 | timestamp | estado | adjudicación |
|---|---|---|---|---|---|
| V1 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V2 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V3 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V4 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V5 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V6 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V7 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V8 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V9 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V10 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V11 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V12 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V13 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V14 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V15 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V16 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V17 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | RED | — |
| V18 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | GREEN_ALREADY | no regresión: pasa por construcción |
| V19 | 2ed62dd | 6727a31408f4312ac7c3147e231045b6a07a723eb60cf63f8205a9d3e5969c5d | 2026-08-06T15:08:26-05:00 | GREEN_ALREADY | no regresión: pasa por construcción |
