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
| V15 | AC-12 — once puntos de despacho y siete punteros locales | `--ac 12` | ok |
| V16 | AC-13 — siete copias idénticas, trigger y README | `--ac 13` | ok |
| V17 | AC-14 — tercera excepción y cita normativa | `--ac 14` | ok |
| V18 | AC-15 — claves nuevas del diff de la rama completas en dueño y vista; en la rama base no hay sujeto | `--ac 15` | ok |
| V19 | AC-16 — guardas del repo sin regresión | `--ac 16` | ok |
| V20 | AC-17 — autoridades frescas, carriers y cierre idempotente del manifest | `--ac 17` | ok |

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

### v3

Identidad: `(e179fa1, sha256 del verificador)`. **Sucede a `v2`**: el vínculo `v2 → v3` existe
porque el inventario de puntos de despacho bajó de **trece a once** al retirarse el modo de
implementación por task, y esa identidad se ata al `sha256` del propio verificador — cambiarlo
obliga a re-emitir el bloque. `v2` queda arriba como historial y no se toca.

Los diecinueve registros son **medidos**, no asumidos: se corrió cada modo con este verificador
sobre un checkout limpio de `e179fa1`.

> **`V2` nace roja y no la vuelve verde este cambio.** Su rojo es anterior y de causa ajena
> (`--ac 1b`, cláusula de rechazo del estado persistido en `co-explore/reference.md`). Se registra
> como se midió; declararla verde sería un baseline falso.

#### Baseline de v3

| ID | commit | sha256 | timestamp | estado | adjudicación |
|---|---|---|---|---|---|
| V1 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V2 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | RED | roja antes de este cambio, por causa ajena a él (cláusula de rechazo en co-explore) |
| V3 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V4 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V5 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V6 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V7 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V8 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V9 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V10 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V11 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V12 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V13 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V14 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V15 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | RED | el inventario del árbol declaraba trece puntos; la fila exige once |
| V16 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V17 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | — |
| V18 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | no regresión: pasa por construcción |
| V19 | e179fa1 | 4bb8d14bbb1872d871209f7f4828bf9a9aa8a460181c3b8d181f132044e542e4 | 2026-08-12T23:45:32-05:00 | GREEN_ALREADY | no regresión: pasa por construcción |

### v4

Identidad previa al commit: `(403dca0, sha256 del verificador en el working tree)`. **Sucede a
`v3`** porque `--ac 15` deja de prohibir toda clave nueva y pasa a comprobar que las claves nuevas
del diff de la rama estén completas en dueño y vista. Sobre la rama base no hay sujeto.

Los diecinueve modos se midieron sobre el working tree con `HEAD`
`403dca0da0331180dab92fa463293747baba85b9`; `--validar-baseline` y `--autotest` también dieron exit
`0`. La atadura posterior con `git show <commit>:scripts/verificar-sobre-en-vuelo.py` queda pendiente
del commit, que este work order prohíbe crear.

#### Baseline de v4

| ID | commit | sha256 | timestamp | estado | adjudicación |
|---|---|---|---|---|---|
| V1 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V2 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V3 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V4 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V5 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V6 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V7 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V8 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V9 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V10 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V11 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V12 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V13 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V14 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V15 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V16 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V17 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |
| V18 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN | `--ac 15` exit 0; `--autotest` exit 0; medición del working tree |
| V19 | 403dca0 | 115b1f046d0511c48ae04600f76b6ab0b483834add76bbf778030447ff08b716 | 2026-08-13T16:17:02Z | GREEN_ALREADY | — |

### v5

Identidad previa al commit: `(9c78a04, sha256 del verificador en el working tree)`. **Sucede a
`v4`** porque el caso `retiro-de-dueno` del autotest dejó de usar `cross_model.families` como sujeto
y ahora **siembra su propia clave** en dueño y vista antes de retirarla del dueño.

**Por qué el cambio.** Atar el mutante a una clave real ataba el autotest de la guarda al contenido
de un flujo concreto: sobre una rama sin `cross_model.families` el caso no se podía construir y
`--autotest` fallaba por una razón que nada tiene que ver con la guarda. Medido: sobre `main` el
autotest daba rojo con «no se encontró cross_model.families en su dueño»; con la clave sembrada da
exit `0` y el caso conserva sus dos direcciones.

Los diecinueve modos, `--validar-baseline` y `--autotest` se midieron sobre el working tree con
`HEAD` `9c78a04`; los veintiuno dieron exit `0`. La atadura posterior con
`git show <commit>:scripts/verificar-sobre-en-vuelo.py` queda pendiente del commit.

#### Baseline de v5

| ID | commit | sha256 | timestamp | estado | adjudicación |
|---|---|---|---|---|---|
| V1 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V2 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V3 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V4 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V5 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V6 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V7 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V8 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V9 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V10 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V11 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V12 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V13 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V14 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V15 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V16 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V17 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V18 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |
| V19 | 9c78a04 | 575a60acafca9f173c8bb1200c4c5291fb59d9c116ecb02a1f47285bd58805b5 | 2026-08-13T16:41:11Z | GREEN_ALREADY | — |

### v6

Identidad previa al commit: `(34d7c41, sha256 del verificador en el working tree)`. **Sucede a
`v5`** porque incorpora `--ac 17`/V20 para verificar estructuralmente las autoridades frescas del
manifest, su transferencia entre carriers y el cierre idempotente de los cuatro productores.

Los veinte modos y `--autotest` se midieron sobre el working tree con `HEAD` `34d7c41`; todos dieron
exit `0`. V1–V19 conservan el verde de la línea base y V20 pasa con sus mutantes nuevos. La atadura
posterior con `git show <commit>:scripts/verificar-sobre-en-vuelo.py` queda pendiente del commit.

#### Baseline de v6

| ID | commit | sha256 | timestamp | estado | adjudicación |
|---|---|---|---|---|---|
| V1 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V2 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V3 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V4 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V5 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V6 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V7 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V8 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V9 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V10 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V11 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V12 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V13 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V14 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V15 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V16 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V17 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | — |
| V18 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V19 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V20 | 34d7c41 | bb704780ec6e401b0db6e575e3a1b829ba5fff91f41939bdb2ecf71640405a8a | 2026-08-15T16:13:10Z | GREEN | `--ac 17` y sus mutantes estructurales dieron exit 0 |

### v7

Identidad previa al commit: `(34d7c41, sha256 del verificador en el working tree)`. **Sucede a
`v6`** tras la revisión final: AC-17 liga retry y `EEXIST` a sus cláusulas de no lectura dentro de
la misma oración, exige `ni se copia`, y distingue ausencia de vía de un preflight fallido con vía
ya resuelta.

Los veinte modos y `--autotest` se midieron sobre el working tree con `HEAD` `34d7c41`; todos dieron
exit `0`. V1–V19 conservan el verde de la línea base y V20 pasa con 41 mutantes estructurales. La
atadura posterior con `git show <commit>:scripts/verificar-sobre-en-vuelo.py` queda pendiente del
commit.

#### Baseline de v7

| ID | commit | sha256 | timestamp | estado | adjudicación |
|---|---|---|---|---|---|
| V1 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V2 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V3 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V4 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V5 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V6 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V7 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V8 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V9 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V10 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V11 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V12 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V13 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V14 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V15 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V16 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V17 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | — |
| V18 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V19 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V20 | 34d7c41 | 35cf7cbd6c5787fd4fd9d1d709c15cb95ab9e4c946f4d70ca0f9189f9bff6341 | 2026-08-15T16:33:57Z | GREEN | `--ac 17` y sus 41 mutantes estructurales dieron exit 0 |

### v8

Identidad previa al commit: `(34d7c41, sha256 del verificador en el working tree)`. **Sucede a `v7`** porque separa las pruebas de retry y `EEXIST` por oración y conserva un corpus auditable. Los veinte modos y 41 mutantes dieron exit `0`; la atadura con `git show` queda pendiente del commit.

#### Baseline de v8

| ID | commit | sha256 | timestamp | estado | adjudicación |
|---|---|---|---|---|---|
| V1 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V2 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V3 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V4 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V5 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V6 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V7 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V8 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V9 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V10 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V11 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V12 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V13 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V14 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V15 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V16 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V17 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | — |
| V18 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V19 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V20 | 34d7c41 | 5c33afdb0830aa5a165d1626eda488d51e914266c7118bfb75532a49f0d74f8a | 2026-08-15T16:52:56Z | GREEN | `--ac 17` y sus 41 mutantes estructurales dieron exit 0 |

### v9
Identidad previa al commit: `(34d7c41, sha256 del verificador en el working tree)`. **Sucede a `v8`** porque distingue la transferencia no terminal al checkpoint del retiro terminal. Los veinte modos y 42 mutantes dieron exit `0`; la atadura con `git show` queda pendiente del commit.
#### Baseline de v9
| ID | commit | sha256 | timestamp | estado | adjudicación |
|---|---|---|---|---|---|
| V1 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V2 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V3 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V4 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V5 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V6 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V7 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V8 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V9 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V10 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V11 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V12 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V13 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V14 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V15 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V16 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V17 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | — |
| V18 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V19 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V20 | 34d7c41 | 1be28fb3afe74f2fd2aa476705463ddc6e3949811e80fb4870d7955bfdc6829c | 2026-08-15T17:46:20Z | GREEN | `--ac 17` y sus 42 mutantes estructurales dieron exit 0 |

### v10
Identidad previa al commit: `(34d7c41, sha256 del verificador en el working tree)`. **Sucede a `v9`** porque la sede canónica del carrier también distingue checkpoint y cierre terminal. Los veinte modos y 43 mutantes dieron exit `0`; la atadura con `git show` queda pendiente del commit.
#### Baseline de v10
| ID | commit | sha256 | timestamp | estado | adjudicación |
|---|---|---|---|---|---|
| V1 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V2 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V3 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V4 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V5 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V6 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V7 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V8 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V9 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V10 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V11 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V12 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V13 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V14 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V15 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V16 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V17 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | — |
| V18 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V19 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V20 | 34d7c41 | d6f05945149cc3aaa89b13717582b40c4429c6817cedf8b1dde808032d06a64d | 2026-08-15T17:56:07Z | GREEN | `--ac 17` y sus 43 mutantes estructurales dieron exit 0 |
