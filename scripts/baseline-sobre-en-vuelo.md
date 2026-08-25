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

### v11

Identidad comprobable: `(9b58ce6, 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36)`.
**Sucede a `v5`** y consolida los baselines transitorios v6–v10, retirados porque nunca
quedaron ligados a bytes commiteados. El validador ahora comprueba con `git show` que el commit
registrado contiene exactamente el verificador identificado por el `sha256`; además incorpora las
correcciones de portabilidad y contención surgidas de la revisión del PR.

Los veinte modos y `--autotest` se midieron sobre el commit `9b58ce6`; todos dieron exit `0`.

#### Baseline de v11

| ID | commit | sha256 | timestamp | estado | adjudicación |
|---|---|---|---|---|---|
| V1 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V2 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V3 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V4 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V5 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V6 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V7 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V8 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V9 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V10 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V11 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V12 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V13 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V14 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V15 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V16 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V17 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | — |
| V18 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V19 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V20 | 9b58ce6 | 35b04523f65390f20cc157d8dd1184177b4f1bb9de53925683be84910a63ff36 | 2026-08-17T23:01:30Z | GREEN_ALREADY | `--ac 17` y sus 43 mutantes estructurales dieron exit 0 |

La migración de `scripts-en-skills` retiró el arnés de paridad y su corpus. `GUARDAS` pasó a invocar
el entrypoint durable `python3 -m tests`, conservando `verificar-vistas-config.py`, que no pertenecía
al arnés y cuya entrada casi se arrastra con el retiro. Ese cambio altera los bytes del verificador,
así que su identidad `(commit, sha256)` se re-emite.

Los veinte modos y `--autotest` se midieron sobre el commit `8057282`, **una invocación por línea**;
los veintiuno dieron exit `0`.

#### Baseline de v12

| ID | commit | sha256 | timestamp | estado | adjudicación |
|---|---|---|---|---|---|
| V1 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V2 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V3 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V4 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V5 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V6 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V7 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V8 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V9 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V10 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V11 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V12 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V13 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V14 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V15 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V16 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V17 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
| V18 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V19 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | no regresión: pasa por construcción |
| V20 | 8057282 | 64d62d226b92d339f4856455b04e551397de4501fe4659ef6969bba3ecbe7077 | 2026-08-25T12:22:22Z | GREEN_ALREADY | — |
