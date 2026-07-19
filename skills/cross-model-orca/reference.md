# cross-model-orca — Referencia

Detalle operativo del transporte `orca-session`. El `SKILL.md` apunta aquí cuando necesita el
resolver que decide `orca-session` vs `cli`, el parseo del envelope y la cosecha
crash-idempotente, la contención robusta del `reportPath`, la recuperación ante fallas del
secundario, la espera bloqueante con backoff, y la raíz de instalación/estado conductor-only. El
artefacto Node de `assets/*.mjs` ya implementa toda esta mecánica; este archivo la documenta
citando funciones y contratos reales — no reimplementa nada.

## Tabla de contenidos

- [Portabilidad entre shells (POSIX / PowerShell)](#portabilidad-entre-shells-posix--powershell)
- [Resolver de transporte](#resolver-de-transporte)
- [Envelope y cosecha crash-idempotente](#envelope-y-cosecha-crash-idempotente)
- [Contención robusta y promoción atómica](#contención-robusta-y-promoción-atómica)
- [Recuperación](#recuperación)
- [Espera y backoff](#espera-y-backoff)
- [Instalación y raíz conductor-only](#instalación-y-raíz-conductor-only)

---

## Portabilidad entre shells (POSIX / PowerShell)

Regla transversal del repo (ver `CLAUDE.md`): cada comando nuevo va en bloque **POSIX** y
**PowerShell** completos, nunca con `...` de relleno. PowerShell no soporta `<` para redirigir
un archivo a stdin: donde una CLI necesite el prompt/spec por archivo, la forma PowerShell es
`Get-Content -Raw archivo | <cli> ... -`.

En este artefacto en particular esa restricción rara vez aplica: `dispatch-adapter.mjs` nunca arma
un string de shell para invocar `orca` — su `orcaRunner` por default llama
`spawnSync('orca', args, { encoding: 'utf8' })` con `args` como **arreglo de argv**, sin `shell:
true`. Eso evita de raíz el problema de quoting que sí afecta a `codex exec`/`claude -p` con un
prompt en markdown (backticks, comillas). Los bloques POSIX/PowerShell de las secciones de abajo
documentan igual ambas variantes porque son comandos `orca` que alguien puede necesitar correr a
mano (debug, recuperación manual) fuera del adaptador — en la mayoría de los casos la sintaxis de
`orca <subcomando> ...` es **idéntica** en los dos shells (no hay prefijo de variables de entorno
que traducir, mismo patrón que usa `buildLaunchCommand` para el comando Codex en
`dispatch-adapter.mjs`); se marca explícitamente cuando así es, para no sugerir que hace falta una
traducción que no existe.

Detección de binario, si hace falta confirmarlo antes de invocar `orca` a mano:

**POSIX (bash/zsh):**
```bash
command -v orca || command -v orca-ide
```

**PowerShell:**
```powershell
Get-Command orca -ErrorAction SilentlyContinue
```

---

## Resolver de transporte

Algoritmo: `override ?? config ?? auto`. Se evalúa en ese orden; el primer valor no-nulo gana.

1. **`override`** — lo que pasa explícito la skill llamadora (`co-explore`, `cross-review`,
   `cross-implement`) en su propio paso "resolver transporte", o lo que le llega ya resuelto desde
   `sdd-flow`/`sdd-orchestrator`. Punto fino, confirmado en el plan (Tasks 6.1/6.2): cuando
   `sdd-flow`/`sdd-orchestrator` delegan, **propagan solo el `cross_model.transport.desired`** (el
   valor configurado) al agente/skill delegada — **nunca su propio `effective`** (el transporte ya
   resuelto en el proceso del padre). La razón: el proceso hijo (un subagente delegado, por
   ejemplo) puede ver el runtime de Orca como `stale_bootstrap` aunque el padre lo haya alcanzado
   sin problema — son procesos distintos con distinta vista de reachability. Cada skill/proceso
   **reevalúa su propio `effective`** a partir del `desired` heredado; nunca hereda un `effective`
   ya resuelto por otro proceso.
2. **`config`** — la clave `cross_model.transport` en `.specify/config.yml` del repo (default
   `auto` cuando la clave no está). Mismo patrón de lectura que `co_explore`/`cross_review` en ese
   archivo (ver `sdd-flow/reference.md` → "Esquema de `.specify/config.yml`").
3. **`auto`** — se resuelve por **disponibilidad**: ¿el runtime de Orca es alcanzable **desde el
   proceso del conductor** en este momento? Un runtime que el conductor ve en estado
   `stale_bootstrap` se trata igual que "no alcanzable" → **degradar a `cli`** (salvo un broker
   host-side explícito que reenvíe a un runtime sano, que queda **fuera de v1** — no hay tal
   mecanismo implementado). **Marca de contrato, no inventado:** el comando exacto de sondeo y el
   shape preciso de su respuesta (¿un campo `state`/`status` con el valor literal
   `stale_bootstrap`?) no están confirmados en `dispatch-adapter.mjs`, `RESULTS.md` ni
   `profiles.md` — ninguno de los tres invoca ni parsea un chequeo de reachability standalone hoy
   (`createOwnedSession` intenta crear la terminal directamente y trata un `terminalHandle` nulo
   como fallo de creación, no como resultado de un sondeo previo). Hasta que exista ese contrato
   verificado, descríbelo en el nivel de detalle que sostienen las fuentes: "el conductor sondea
   la reachability del runtime de Orca antes de despachar, y un resultado no sano degrada a
   `cli`". Quien implemente el resolver de una skill concreta (Task 3.1/4.x/5.x) debe confirmar el
   comando real contra el `orca` instalado en ese momento antes de codificarlo — no asumir el de
   arriba.

**Runtime de sesión vs runtime del flujo.** El resolver no solo decide `orca-session` vs `cli`:
también decide si la sesión que se va a usar es nueva o reutilizada.

- Por default, `createOwnedSession` crea una sesión **fresca** por dispatch/rama.
- **Reutilización:** solo de **sesiones propias** — una sesión que el propio flujo ya creó en una
  ronda anterior (el caso de `cross-review` reutilizando la sesión del secundario entre rondas de
  debate). El registro de esa sesión vive en el `stateDir` del conductor (ver "Instalación y raíz
  conductor-only"), así que "propia" es verificable: está en `sessions.json` bajo el `uid` que
  `createOwnedSession` generó.
- **Sesión ajena:** una sesión abierta por el usuario o por otro flujo, no registrada como propia.
  **Nunca se cosecha en v1** — no existe una rama de consentimiento que lo habilite (alineado con
  SKILL.md → sección 6, "Privacidad (v1)"). Si no se puede garantizar que la sesión es propia y
  fresca, el transporte fuerza **crear una sesión nueva**, o si eso tampoco es viable, **degrada a
  `cli`**. Sin excepciones.

**Resultado del resolver:** `orca-session` o `cli`. Ante **cualquier** duda — reachability
incierta, sesión no verificable como propia, locator ambiguo — el resultado es `cli`. El transporte
`cli` nunca requiere justificar por qué se eligió; `orca-session` sí requiere que las tres
condiciones (Orca alcanzable, sesión propia/fresca, perfiles de las tres capas de control
instalados) se cumplan explícitamente.

---

## Envelope y cosecha crash-idempotente

El formato general del envelope (`X-CMO: taskId=<..> dispatchId=<..> nonce=<..>` + `STATUS: done`
como última línea no vacía) está en `SKILL.md` → sección 2; esta sección documenta cómo el código
lo produce, lo parsea y lo cosecha exactamente una vez.

**Discrepancia código vs. `SKILL.md` (el código gana):** `SKILL.md` describe el envelope completo
con `taskId`+`dispatchId`+`nonce`. La instrucción real que `createDispatch` inyecta en el spec del
dispatch (`buildEnvelopeInstructions` en `dispatch-adapter.mjs`) le pide al secundario cerrar con
**solo** `X-CMO: nonce=<nonce>` + `STATUS: done` — sin `taskId`/`dispatchId`. Es intencional, no un
bug: el comentario del propio código lo explica — `harvest()`/`selectAssistantByNonce` solo
necesitan el `nonce` para desambiguar dentro del transcript; `taskId`/`dispatchId` viajan por el
canal de `worker_done` (el `payload` de la orquestación de Orca), no por el texto del envelope.
`parseEnvelope()` sigue soportando los tres campos (para otros transportes/skills que sí los
pidan en su prompt, p. ej. el `cli` de hoy), y tolera que falten sin lanzar. Si vas a redactar el
prompt de un dispatch `orca-session` a mano, sigue lo que pide el código: alcanza con `nonce`.

**Parseo del envelope (`harvest-core.mjs`):**
- `parseEnvelope(msg)` busca la **última** línea que empieza con `X-CMO:` y extrae los pares
  `clave=valor` de `nonce`/`taskId`/`dispatchId` presentes; nunca lanza, un campo ausente queda
  `null`.
- `hasSentinel(msg)` es `true` solo si la **última línea no vacía** de `msg` es exactamente
  `STATUS: done` (un `STATUS: done` citado en medio del cuerpo, con más texto después, no cuenta).
- `stripSentinel(msg)` devuelve el mensaje sin esa línea final, preservando el resto (cuerpo +
  línea `X-CMO:` si la hubiera).

**Desambiguación por `nonce` (sesión reutilizada):** `selectAssistantByNonce(family, filePath,
nonce)` recorre los mensajes del asistente del transcript/rollout **de atrás hacia adelante** y
devuelve el primero cuyo `parseEnvelope(...).nonce` coincida con el `nonce` del dispatch en curso.
Una sesión reutilizada (caso `cross-review` entre rondas) puede tener mensajes de dispatches
anteriores con `nonce` viejo — esos se ignoran automáticamente porque no matchean. Esta es la
función que usa `harvest()`, no la más simple `parseTranscript(family, filePath)` (que solo trae
el último mensaje del asistente sin filtrar por nonce — esa queda para casos donde no hace falta
desambiguar).

**`worker_done` es solo wake-up, no evidencia de escritura.** La señal por comando (`Codex`
únicamente — Claude nunca la emite, ver SKILL.md → sección 3) dispara que el conductor **empiece**
a mirar, pero el mensaje final con el envelope puede tardar en aparecer en el transcript. El
conductor nunca cosecha directo del `worker_done`: siempre relee el transcript y busca el mensaje
con el `nonce` esperado (ver "Espera y backoff" para el detalle del poll).

**Autoridad ANTES de cosechar (`dispatch-adapter.mjs`):** `checkWorkerDoneAuthority({ orcaRunner,
coordinatorHandle, dispatch })` consulta `orchestration check --terminal <coordinatorHandle> --all
--json`, filtra los mensajes `type: 'worker_done'` cuyo `payload.taskId`/`payload.dispatchId`
coincidan con el `dispatch` activo, y si el mensaje además expone un `sender` (`msg.from` /
`msg.sender` / `msg.senderHandle`, mejor esfuerzo — el campo exacto no está garantizado en el
shape de Orca) lo compara contra el `expectedAssignee` capturado en `createDispatch` (el
`terminalHandle` al que se despachó). Solo si todo coincide, `awaitDone` avanza a invocar el
harvester — `harvest-from-transcript.mjs`/`harvest()` **no revalida** esta autoridad: asume una
entrada ya autorizada (así lo documenta su propio comentario de cabecera).

**FSM durable crash-idempotente (`makeDedupFsm`, `harvest-core.mjs`):** clave durable
`${dispatchId}:${nonce}` (la misma que arma `awaitDone`). Estados `received → harvested →
promoted`, con `markReceived`/`markHarvested`/`markPromoted`/`isPromoted`/`state`. Cada avance es
monotónico (`advance()` no retrocede un estado ya alcanzado) y se persiste con `writeFsmState`:
escritura a un temporal `<statePath>.<pid>.<timestamp>.tmp` + `fs.renameSync` atómico sobre el
archivo final — un crash a mitad de escritura nunca deja el JSON de estado corrupto.
`markPromoted(key, canonicalHash)` guarda `desiredCanonicalHash`; si `key` ya está `promoted` con
ese mismo hash, no reaplica nada (idempotente ante reintentos post-crash).

**El hueco post-rename/pre-promoted (manejado en `awaitDone`):** si el proceso cae después de que
`harvest()` ya escribió el reporte (`writeExclusive`) pero antes de `fsm.markPromoted`, un retry
posterior encuentra `isPromoted(dedupKey) === false` (sigue en received/harvested), vuelve a
invocar `harvest()`, y este ve el destino ya existente → `checkContainment` lo rechaza con
`REPORT_ALREADY_EXISTS_REASON` (`code: 2`). `awaitDone` distingue explícitamente ese `reason` de un
rechazo real de contención (path fuera de root, symlink, etc. — esos tienen un `reason` distinto) y
lo trata como **éxito idempotente**: recalcula el path resuelto, marca `harvested`+`promoted` con
el hash del archivo ya en disco, y devuelve `code: 0`. Esto también autorrepara una FSM corrupta o
perdida.

**CLI standalone de cosecha (`harvest-from-transcript.mjs`, wrapper por variables de entorno):**
lee `CMO_FAMILY` / `CMO_TRANSCRIPT` / `CMO_NONCE` / `CMO_REPORT_PATH` / `CMO_ROOT` /
`CMO_DEADLINE_MS`, invoca `harvest(params)` y sale con su código. Exit codes de este wrapper: **0**
cosechado y persistido; **2** contención rechazada (incluye el caso idempotente de arriba, que
`awaitDone` reinterpreta cuando lo llama como función, no como subproceso); **3** venció
`CMO_DEADLINE_MS` sin un mensaje válido con ese nonce+sentinel; **1** input inválido (falta una
variable requerida, o `CMO_DEADLINE_MS` no es un número `>= 0`) o un error inesperado — nunca deja
un stack trace sin manejar. **Nota de capa:** el `code: 4` que puede devolver `awaitDone` (locator
de Codex sin resolver, ver "Espera y backoff") es un código del **contrato de la función**
`awaitDone`, no un exit code de este wrapper de CLI — `harvest()` en sí (la función pura que
invoca el wrapper) solo devuelve `0`/`2`/`3`.

**Invocar el wrapper a mano (debug):**

**POSIX (bash/zsh):**
```bash
CMO_FAMILY=codex \
CMO_TRANSCRIPT="$CODEX_HOME/sessions/2026/07/19/rollout-2026-07-19T10-00-00-<session_id>.jsonl" \
CMO_NONCE="<nonce-del-dispatch>" \
CMO_REPORT_PATH="report.md" \
CMO_ROOT="/ruta/absoluta/del/destino" \
CMO_DEADLINE_MS=30000 \
node "$CROSS_MODEL_ORCA/harvest-from-transcript.mjs"
```

**PowerShell:**
```powershell
$env:CMO_FAMILY = "codex"
$env:CMO_TRANSCRIPT = "$env:CODEX_HOME\sessions\2026\07\19\rollout-2026-07-19T10-00-00-<session_id>.jsonl"
$env:CMO_NONCE = "<nonce-del-dispatch>"
$env:CMO_REPORT_PATH = "report.md"
$env:CMO_ROOT = "C:\ruta\absoluta\del\destino"
$env:CMO_DEADLINE_MS = "30000"
node "$env:CROSS_MODEL_ORCA\harvest-from-transcript.mjs"
```

---

## Contención robusta y promoción atómica

Contrato de `reportPath`: **ruta destino inexistente**, canonicalizada y contenida dentro de una
raíz autorizada. Implementado en `checkContainment(reportPath, root)` (`harvest-core.mjs`), en
este orden:

1. Rechaza `reportPath` vacío, absoluto (`path.isAbsolute`), o con algún segmento `".."`.
2. Canonicaliza la raíz autorizada con `fs.realpathSync(root)` — si `root` en sí es un symlink, se
   resuelve a su destino real antes de comparar cualquier cosa contra ella.
3. Resuelve el destino propuesto (`path.resolve(rootReal, reportPath)`) y **canonicaliza el
   directorio padre** del destino (`fs.realpathSync(path.dirname(target))`): si ese padre real no
   cae dentro de `rootReal` (con separador de path incluido, para no confundir un prefijo parcial
   con un directorio hermano), rechaza — esto bloquea un symlink intermedio que reapunte fuera de
   la raíz.
4. Exige que el destino **no exista**: `fs.lstatSync(target)` (contra el symlink final, sin
   seguirlo) debe fallar con `ENOENT`. Si el `lstat` tiene éxito, el destino ya existe → rechaza con
   el motivo exacto `REPORT_ALREADY_EXISTS_REASON` (`"El destino ya existe."`, exportado como
   constante para que `dispatch-adapter.mjs` lo distinga de un rechazo real de contención, ver
   sección anterior). Cualquier otro error de `lstat` que no sea `ENOENT` también rechaza.
5. Si las cuatro condiciones pasan, devuelve `{ ok: true, resolved: target }`.

**Escritura exclusiva:** `writeExclusive(resolvedPath, data)` escribe con
`fs.writeFileSync(resolvedPath, data, { flag: 'wx' })` — falla si el archivo aparece **entre** el
check de `checkContainment` y esta escritura, cerrando la carrera TOCTOU. `harvest()` en
`harvest-from-transcript.mjs` llama `checkContainment` y, solo si `ok`, `writeExclusive` sobre
`contained.resolved`.

**Destinos acumulativos (p. ej. `review-log.md` de `cross-review`, que crece ronda a ronda):** el
contrato — fijado en las Global Constraints del plan y en la matriz de raíces de `SKILL.md` →
sección 5 — es que la cosecha **nunca** sobrescribe el archivo canónico directo con `wx` (eso
rompería en la segunda ronda, porque el canónico ya existiría). En cambio: (a) cada ronda/dispatch
escribe un **raw único e inmutable** (un nombre de archivo distinto por dispatch, p. ej. algo
derivado de `dispatchId`/`nonce` — un target nuevo, así que `wx` es válido); (b) se **reconstruye
por completo** el contenido canónico a partir de **todos** los raws inmutables acumulados hasta
ese momento, se escribe a un temporal y se **promueve con `rename` atómico** sobre el canónico; (c)
recién ahí se marca `promoted` en la FSM, con `desiredCanonicalHash` = hash del canónico resultante
— si el proceso cae después del `rename` pero antes de `markPromoted`, un retry reconstruye desde
los mismos raws inmutables y llega al mismo hash, así que la promoción es idempotente sin doble
incorporación (mismo mecanismo genérico documentado arriba en "El hueco post-rename/pre-promoted",
aplicado acá a un canónico multi-raw en vez de uno solo).

**Precisión sobre qué existe hoy vs. qué es contrato para más adelante:** `checkContainment`,
`writeExclusive` y la FSM con `desiredCanonicalHash` (genéricos, en `harvest-core.mjs`) ya cubren
la mitad del mecanismo — la escritura exclusiva del raw y el marcado de promoción por hash. Lo que
**no** existe todavía como función reutilizable en `assets/` es la reconstrucción-desde-raws en sí
(leer N archivos raw y producir el contenido canónico, p. ej. concatenar rondas de
`review-log.md`) — esa lógica es específica de cada skill acumulativa y queda para su propia task
de enganche (`cross-review/reference.md`, Task 4.2 del plan: "reutiliza sesión + cosecha
raw→promote"). Esta sección documenta el contrato que esa task debe cumplir, no una función ya
codificada acá.

---

## Recuperación

Orca **no cancela** un dispatch en curso (confirmado, ronda 2 #7 del plan): no hay un comando
`orchestration cancel`. Para recuperar ante un fallo del secundario hay que interrumpirlo primero.

**`recover({ session, dispatch, orcaRunner })` (`dispatch-adapter.mjs`):**

1. Envía `terminal send --terminal <terminalHandle> --interrupt --json` — no espera respuesta de
   contenido, solo dispara la interrupción.
2. Confirma que la terminal quedó idle: `terminal wait --terminal <terminalHandle> --for tui-idle
   --timeout-ms 30000 --json` (el timeout de 30s es `RECOVER_IDLE_TIMEOUT_MS`, constante del
   módulo). Si `satisfied !== true`, devuelve `{ recovered: false }` de inmediato — sin idle
   confirmado no se garantiza que el secundario dejó de escribir/actuar, así que **no** se habilita
   ningún redispatch.
3. **Rol `read-only`:** con idle confirmado alcanza — no hay riesgo de doble escritor. Devuelve
   `{ recovered: true }`.
4. **Rol `write`:** idle confirmado **no alcanza**. Antes de habilitar el redispatch hace falta
   demostrar el **cierre real** de la terminal: `terminal close --terminal <terminalHandle>
   --json`. Solo si ese cierre tiene éxito (`code === 0` y sin `error` en el JSON de respuesta)
   devuelve `{ recovered: true }`; si no, `{ recovered: false }`. `recovered: false` en rol write
   significa: **no** redespaches por CLI todavía — el llamador decide qué hacer (reintentar el
   cierre, escalar a intervención manual), nunca asumir que es seguro abrir un segundo escritor.

El parámetro `dispatch` no participa en la decisión de recuperación en sí (se acepta solo por
simetría de interfaz con `awaitDone`/`createDispatch`, y por si el llamador quiere loguear qué
dispatch se está recuperando).

**Comandos equivalentes a mano** (misma sintaxis en POSIX y PowerShell — no hay prefijo de
variables de entorno que traducir en ninguno de los dos):

**POSIX (bash/zsh):**
```bash
orca terminal send --terminal "$TERMINAL_HANDLE" --interrupt --json
orca terminal wait --terminal "$TERMINAL_HANDLE" --for tui-idle --timeout-ms 30000 --json
# Solo si el rol es "write" y el idle de arriba confirmó satisfied:true:
orca terminal close --terminal "$TERMINAL_HANDLE" --json
```

**PowerShell:**
```powershell
orca terminal send --terminal $TerminalHandle --interrupt --json
orca terminal wait --terminal $TerminalHandle --for tui-idle --timeout-ms 30000 --json
# Solo si el rol es "write" y el idle de arriba confirmó satisfied:true:
orca terminal close --terminal $TerminalHandle --json
```

Recién con `{ recovered: true }` el llamador puede habilitar un redispatch por el transporte `cli`
(nunca por `orca-session` sobre la misma sesión ya comprometida — esa sesión queda descartada).

---

## Espera y backoff

`awaitDone({ session, dispatch, coordinatorHandle, reportPath, root, deadlineMs, ... })`
(`dispatch-adapter.mjs`) es la espera bloqueante del conductor tras un dispatch. Tiene, en orden,
hasta cuatro fases:

**0. Dedup temprano.** Si `fsm.isPromoted(dedupKey)` ya es `true` (una corrida anterior ya cosechó
este `dispatchId:nonce` — recuperación post-crash, o un segundo `worker_done` idéntico llegando
tarde), devuelve `{ code: 0, reportPath }` de inmediato **sin** tocar Orca ni el filesystem de
nuevo.

**1. Locator de Codex, si sigue pendiente.** Si `session.family === 'codex'` y
`session.transcriptPath` todavía es `null` (el rollout no se resolvió en `createOwnedSession`,
ver su docstring — el rollout de Codex no existe hasta el primer turno), se invoca
`resolveCodexTranscript`: hasta `CODEX_LOCATOR_MAX_ATTEMPTS` (3) intentos con
`CODEX_LOCATOR_RETRY_MS` (200 ms) de espera fija entre intentos, buscando exactamente 1 candidato
(`locateCodexRollout`, por creación+`cwd`+timestamp). Si tras los reintentos sigue sin resolverse
(0 candidatos — no flushó todavía — o más de uno, ambiguo), `awaitDone` devuelve `{ code: 4,
reason: '...' }` **sin** haber consultado `orchestration check` ni tocado la FSM — es la señal
explícita de "degradar a `cli`" para la skill llamadora. Claude no pasa por esta fase: su locator ya
quedó resuelto en `createOwnedSession` (directo, por `--session-id` fijado).

**2. Loop de autoridad + backoff exponencial.** Mientras no haya autoridad confirmada:
   - Consulta `checkWorkerDoneAuthority` (`orchestration check --terminal <coordinatorHandle> --all
     --json`, filtrado por `taskId`/`dispatchId`/`sender` — ver sección anterior). Si matchea,
     autorizado.
   - Si la familia es `claude` (que nunca emite `worker_done`), además consulta en la misma
     iteración `terminal wait --terminal <terminalHandle> --for tui-idle --timeout-ms 0 --json`
     (timeout 0 = no bloqueante, solo pregunta el estado actual). `satisfied: true` ahí es
     autoridad suficiente para Claude — es la transición **busy→idle posterior al dispatch**, nunca
     un idle aislado de antes de despachar (la sesión se creó y se le inyectó la tarea en el mismo
     flujo, así que cualquier idle detectado acá es posterior al dispatch por construcción). Para
     Codex, `tui-idle` **no** sustituye la validación de `worker_done`: esta rama no se consulta
     para esa familia.
   - Si ninguna de las dos autorizó y `now() >= deadlineAt`, devuelve `{ code: 3, reason: 'timeout
     esperando fin de turno autorizado (worker_done/tui-idle)' }`.
   - Si no, duerme `Math.min(waitMs, tiempo restante hasta el deadline)` y dobla `waitMs`
     (arranca en `AWAIT_POLL_INITIAL_MS` = 50 ms, tope `AWAIT_POLL_MAX_MS` = 1000 ms) — backoff
     exponencial acotado, nunca un poll a intervalo fijo ni una espera sin techo.

**3. Cosecha.** Con autoridad confirmada, marca `fsm.markReceived(dedupKey)` y llama a `harvest()`
   con el **tiempo restante** del presupuesto (`remainingMs = deadlineAt - now()`, no el
   `deadlineMs` original) — el presupuesto total se reparte entre la espera de autoridad y la
   cosecha, no se duplica. `harvest()` (`harvest-from-transcript.mjs`) hace su **propio** poll
   interno, más fino: relee el transcript buscando `selectAssistantByNonce` + `hasSentinel`, con
   backoff exponencial acotado entre `POLL_INITIAL_MS` (20 ms) y `POLL_MAX_MS` (200 ms) — un
   segundo loop de espera, anidado, con su propia escala de tiempo más corta que la del loop de
   autoridad (tiene sentido: una vez que ya sabemos que el turno terminó, el mensaje con el
   sentinel debería aparecer pronto).

**Presupuesto de tiempo y liberar el turno.** `deadlineMs` es siempre un **presupuesto de espera**
contado desde la invocación (`deadlineAt = now() + deadlineMs`), no un timestamp absoluto — así lo
documenta el propio JSDoc de `harvest()`. Ningún loop de esta función espera indefinidamente: el
loop de autoridad revisa el deadline en cada vuelta y el loop interno de `harvest()` hace lo mismo.
Vencido el presupuesto, la función **devuelve el turno al llamador** con `code: 3` (o `code: 4` en
la fase de locator) en vez de colgarse — es la skill llamadora quien decide degradar a `cli` con
ese resultado, nunca esta función por sí sola reintenta más allá del presupuesto dado. El CLI
standalone (`harvest-from-transcript.mjs`) expone el mismo presupuesto vía `CMO_DEADLINE_MS`.

---

## Instalación y raíz conductor-only

Ver [`install.md`](./install.md) para el contrato completo de instalación (verificación de Node
≥18 vía `assertNode(18)`/`node --version`, y la variable de entorno `CROSS_MODEL_ORCA` que
resuelve la raíz de los módulos vía `resolveInstallRoot()` en `assets/lib/platform.mjs`) — no se
duplica acá.

**Raíz conductor-only (`stateDir`).** El registro de sesiones propias y la FSM durable de dedup
viven en un directorio **exclusivo del conductor**, fuera de cualquier worktree que el secundario
pueda escribir — un secundario `workspace-write` no debe poder alterar autoridad ni dedup. Default
de `dispatch-adapter.mjs` (`defaultStateDir()`): `path.join(os.homedir(), '.cross-model-orca-state')`
— bajo el home del conductor, nunca dentro de un worktree. `createOwnedSession` acepta `stateDir`
como parámetro (con ese default) para quien necesite otra raíz, siempre que se mantenga fuera del
alcance de escritura del secundario.

Archivos que persisten ahí, todos con updates atómicos (escribir a un temporal
`<path>.<pid>.<timestamp>.tmp` seguido de `fs.renameSync`, nunca una escritura in-place):

- **`sessions.json`** — `persistSessionRecord`: un registro por `session.uid` con
  `terminalHandle`/`family`/`role`/`mode`/`sessionId`/`transcriptPath`/`createdAt`. Es la fuente de
  verdad de "sesión propia" que usa el resolver (ver "Runtime de sesión vs runtime del flujo").
- **`dispatches.json`** — `persistDispatchRecord`: un registro por `dispatchId`, con
  `taskId`/`expectedAssignee`/`nonce`/`sessionRef`/`root`.
- **`dedup-fsm.json`** — el estado de `makeDedupFsm`, con clave `${dispatchId}:${nonce}` (ver
  "Envelope y cosecha crash-idempotente").

También `resolveCodexTranscript` reescribe el registro de sesión en `sessions.json` cuando resuelve
el locator diferido de Codex (`transcriptPath`/`sessionId`), siempre vía el mismo
`persistSessionRecord` atómico.

---

## Ver también

- `SKILL.md` — protocolo completo: envelope, tres capas de control, matriz de lanzamiento, matriz
  de raíces por skill/modo, privacidad v1, P4, degradación.
- `install.md` — instalación paso a paso (Node ≥18, `CROSS_MODEL_ORCA`, `skills-ref`).
- `assets/launch/profiles.md` — matriz de lanzamiento completa (POSIX+PowerShell) por
  familia×rol×modo.
- `assets/launch/mcp-inventory.md` — inventario MCP y namespacing real de tools.
- `spikes/RESULTS.md` — contratos de locator y señal con evidencia (Task 0.1/0.2/0.3).
