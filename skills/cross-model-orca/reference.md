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

> Las funciones que documenta este archivo (`createOwnedSession`, `createDispatch`, `awaitDone`,
> `recover`) son la **librería** del transporte; el conductor **no las cablea a mano**, sino que
> corre el entrypoint `assets/run-orca-session.mjs`, que las encadena con la degradación a `cli`
> (ver `SKILL.md` → sección 1, "Cómo se corre: UN comando", y su red flag contra improvisar
> `orca terminal create --command 'codex exec …'`).

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

**Verificación preventiva de perfiles (secundario Claude).** El install root que
`createOwnedSession` usa para armar el `--settings` de Claude (`resolveInstallRoot()` en
`platform.mjs`) se **autolocaliza**: deduce el `assets` instalado a partir de su propia ruta
(`import.meta.url`), sin depender de que nadie setee `CROSS_MODEL_ORCA` a mano; la variable queda
como **override opcional**, solo para quien corra los módulos desde una copia distinta de su
propio `assets`. Eso ya no lanza, así que el chequeo real de "instalación rota o movida" se hace
antes, como parte de decidir `orca-session` con secundario Claude: el conductor confirma que los
perfiles de lanzamiento **existen** en `<install root>/launch/` (p. ej.
`claude-readonly.settings.json`, `claude-write.settings.json`, según el rol). Si el install root
resuelto **no** contiene esos archivos, `orca-session` se trata como **no disponible → degradar a
`cli`**, en vez de lanzar una sesión con un `--settings` que apunta a un archivo inexistente. Este
chequeo reemplaza el viejo modo de falla (la excepción que `resolveInstallRoot()` lanzaba cuando
`CROSS_MODEL_ORCA` no estaba seteada).

---

## Envelope y cosecha crash-idempotente

El formato del envelope (`X-CMO: nonce=<..>` + `STATUS: done` como última línea no vacía) está en
`SKILL.md` → sección 2; esta sección documenta cómo el código lo produce, lo parsea y lo cosecha
exactamente una vez.

**Correlación vs. autoridad (`SKILL.md` y el código coinciden):** la instrucción que
`createDispatch` inyecta en el spec del dispatch (`buildEnvelopeInstructions` en
`dispatch-adapter.mjs`) le pide al secundario cerrar con **solo** `X-CMO: nonce=<nonce>` +
`STATUS: done`. Es intencional: `harvest()`/`selectAssistantByNonce` solo necesitan el `nonce` para
desambiguar dentro del transcript (token de correlación, y es texto del modelo → falsificable); la
**autoridad** es la **propiedad de la sesión** (el conductor creó la terminal y lee el transcript de
esa sesión exacta — `--session-id` propio para Claude, rollout localizado y desambiguado a 1 para
Codex), no un campo del texto ni un `worker_done`. `parseEnvelope()` sigue soportando los tres
campos (`nonce`/`taskId`/`dispatchId`, para otros transportes/skills que sí los pidan, p. ej. el
`cli` de hoy) y tolera que falten sin lanzar. Si vas a redactar el prompt de un dispatch
`orca-session` a mano, sigue lo que pide el código: alcanza con `nonce`.

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

**Detección de fin = el `nonce`+sentinel en el transcript propio, no `worker_done`.** No se
consulta `orchestration check`. `awaitDone` llama a `harvest()`, que hace poll del transcript de la
sesión propia hasta el deadline buscando el mensaje del asistente con el `nonce` esperado y su
sentinel `STATUS: done` (ver "Espera y backoff"). Ese mensaje, en el transcript de una sesión que el
conductor creó y posee, es a la vez la señal de fin y la autoridad. `harvest-from-transcript.mjs`/
`harvest()` no revalida ninguna otra autoridad: asume una entrada ya localizada (así lo documenta su
comentario de cabecera).

**Por qué se abandonó `worker_done` (E2E de Fase 7).** El diseño previo validaba autoridad con un
`checkWorkerDoneAuthority` que leía `orchestration check` y matcheaba `payload.taskId`/`dispatchId`.
El primer E2E contra Orca real mostró que un Codex **sandboxeado** no puede enviar `worker_done` de
forma confiable: el `orca orchestration send` desde el sandbox `read-only` falla **intermitentemente**
con "Orca is not running" (el `ORCA_CLI_SOCKET` viene vacío y no alcanza el runtime). La señal que el
conductor —no sandboxeado— siempre observa es el envelope en el transcript propio. Por eso `awaitDone`
ya no consulta `orchestration check` ni pasa `--from`/coordinatorHandle; el `worker_done` que el
preamble de `--inject` le pide emitir al secundario es ruido inofensivo que no se consume.

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

**El mismo contrato aplica a un destino estable/reusable no acumulativo** (informe único que una
corrida nueva debe **reemplazar entero**, no extender — p. ej. `findings-<familia>.md` de
`co-explore`): `reportPath` sigue siendo el raw único del dispatch, nunca el path estable; la
"reconstrucción" es trivial (el raw más reciente, sin concatenar rondas anteriores) y la promoción
sobrescribe el destino con `rename` atómico en vez de negarse porque ya existe (ver
`co-explore/reference.md` → "Transporte: rama `orca-session`", punto 4).

---

## Recuperación

Orca **no cancela** un dispatch en curso (confirmado, ronda 2 #7 del plan): no hay un comando
`orchestration cancel`. Para recuperar ante un fallo del secundario hay que interrumpirlo primero.

**`recover({ session, dispatch, closeTerminal?, orcaRunner })` (`dispatch-adapter.mjs`):**

1. Envía `terminal send --terminal <terminalHandle> --interrupt --json` — no espera respuesta de
   contenido, solo dispara la interrupción.
2. Confirma que la terminal quedó idle: `terminal wait --terminal <terminalHandle> --for tui-idle
   --timeout-ms 30000 --json` (el timeout de 30s es `RECOVER_IDLE_TIMEOUT_MS`, constante del
   módulo).
3. **Rol `read-only` (default, `closeTerminal: false`):** con idle confirmado alcanza — no hay
   riesgo de doble escritor. Devuelve `{ recovered: <idle confirmado> }`; sin idle confirmado no
   se garantiza que el secundario dejó de actuar → no se habilita el redispatch.
4. **Con `closeTerminal: true` (default en rol `write`):** idle confirmado **no alcanza**. Se
   intenta el **cierre real** de la terminal (`terminal close --terminal <terminalHandle> --json`)
   — aunque idle no se haya confirmado (si la sesión se está descartando, un cierre exitoso es
   estrictamente mejor que dejarla viva). `recovered` = cierre demostrado (`ok: true` del envelope;
   el exit code no sirve: `close` sobre un handle stale devuelve `ok:false` con exit 0).
   `recovered: false` en rol write significa: **no** redespaches por CLI todavía — el llamador
   decide qué hacer (reintentar el cierre, escalar a intervención manual), nunca asumir que es
   seguro abrir un segundo escritor.

**Abandono ≠ redispatch.** Cuando el llamador va a **degradar a `cli`** (no a redespachar sobre la
sesión), debe pasar `closeTerminal: true` aunque el rol sea read-only — es lo que hace el runner
(`orca-session.mjs`): sin el cierre, la degradación deja una terminal zombie abierta "sin hacer
nada" (observado en el caso real de Windows). El runner recupera/cierra ante **cualquier** fallo
posterior al dispatch (no solo `code 4`: con `code 3` —deadline vencido— el secundario puede seguir
trabajando) y propaga el cierre demostrado como `recovered` en su JSON de salida: en rol write,
`recovered:false` = **no** redespachar por cli sin intervención manual (hallazgos del cross-review
de Codex sobre esta saga).

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

## Dispatch: esperar el boot antes de inyectar

`createDispatch` **espera `tui-idle` antes de `dispatch --inject`** (`terminal wait --for tui-idle
--timeout-ms CREATE_DISPATCH_BOOT_TIMEOUT_MS`, 120 s). Gotcha confirmado en el E2E de Fase 7: el
secundario recién creado está booteando su TUI (Codex carga MCP servers, modelo, etc., decenas de
segundos); inyectar antes de que esté listo **pierde el prompt** — el agente queda idle en su
placeholder sin trabajar y nunca aparece el envelope. Éxito de la espera = `ok:true` en el envelope
de Orca (un timeout llega como `ok:false, error.code:"timeout"`). Si no alcanza `tui-idle` en el
presupuesto, `createDispatch` **lanza** (la skill degrada a `cli`), sin despachar. No se pasa
`--from`: el `worker_done` que el preamble le pide al secundario no se consume (ver "Detección de
fin"), así que no hay coordinador que rutear.

**Nudge de sumisión tras el inject (Windows/ConPTY).** Gotcha de caso real en Windows: `dispatch
--inject` tipea el prompt en el composer del TUI pero la tecla de envío puede no llegar — el
secundario queda con el prompt pegado, sin someter, para siempre. Por eso, tras un inject exitoso,
`createDispatch` envía un **Enter explícito**: `terminal send --terminal <handle> --enter --json`
(sin `--text`; verificado en vivo: `ok:true, bytesWritten:1`). Viaja por el mismo stream del PTY
que el paste, así que llega ordenado **después** del prompt; si el inject ya lo sometió (macOS),
cae en un composer vacío y es no-op (validado en E2E: la corrida con nudge cosechó igual, 40s).
Best-effort: un fallo del nudge no aborta el dispatch.

---

## Espera y backoff

`awaitDone({ session, dispatch, reportPath, root, deadlineMs, orcaRunner, now, sleep })`
(`dispatch-adapter.mjs`) es la espera bloqueante del conductor tras un dispatch. No consulta
`orchestration check`: la detección de fin es puramente el transcript propio (ver "Detección de fin"
arriba). Solo usa `orcaRunner` para **cerrar el dispatch** tras cosechar (fase 3). Tiene, en orden,
hasta tres fases:

**0. Dedup temprano.** Si `fsm.isPromoted(dedupKey)` ya es `true` (una corrida anterior ya cosechó
este `dispatchId:nonce` — recuperación post-crash, o una segunda invocación con el mismo
dispatch+nonce), devuelve `{ code: 0, reportPath }` de inmediato **sin** tocar el filesystem de
nuevo.

**1. Locator de Codex, si sigue pendiente.** Si `session.family === 'codex'` y
`session.transcriptPath` todavía es `null` (el rollout no se resolvió en `createOwnedSession`, ver
su docstring — el rollout de Codex no existe hasta que **arranca el turno**, segundos después del
inject), se invoca `resolveCodexTranscript` reintentando hasta que el rollout **aparezca**: el
presupuesto es `min(deadline restante, CODEX_LOCATE_BUDGET_MS = 240_000 ms — 240s: la TUI puede
alcanzar tui-idle y aun así demorar el primer turno en la cola del arranque de MCP, caso real en
Windows)`, con
`CODEX_LOCATOR_RETRY_MS` (200 ms) entre intentos (`maxAttempts = budget / 200`), buscando
exactamente 1 candidato (`locateCodexRollout`, por creación+`cwd`+timestamp). Si tras el
presupuesto sigue sin resolverse (0 candidatos — no arrancó/flushó todavía — o más de uno,
ambiguo), `awaitDone` devuelve `{ code: 4, reason: '...' }` — la señal explícita de "degradar a
`cli`" para la skill llamadora. Claude no pasa por esta fase: su locator ya quedó resuelto en
`createOwnedSession` (directo, por `--session-id` fijado).

**2. Cosecha.** Marca `fsm.markReceived(dedupKey)` y llama a `harvest()` con el **tiempo restante**
del presupuesto (`remainingMs = deadlineAt - now()`, no el `deadlineMs` original) — el presupuesto
total se reparte entre la localización del rollout y la cosecha, no se duplica. `harvest()`
(`harvest-from-transcript.mjs`) es el poll que **detecta el fin**: relee el transcript propio
buscando `selectAssistantByNonce` + `hasSentinel`, con backoff exponencial acotado entre
`POLL_INITIAL_MS` (20 ms) y `POLL_MAX_MS` (200 ms). Cuando el mensaje con el `nonce` esperado y su
sentinel aparece, lo persiste (contención de `reportPath` incluida). Si nunca aparece antes del
deadline, `harvest()` devuelve `{ code: 3 }`. La rama de crash-idempotencia (destino ya existente
para el mismo dispatch+nonce ⇒ éxito idempotente `code: 0`) se documenta en el JSDoc de `awaitDone`.

**3. Cierre del dispatch (best-effort, tras cosecha `code:0`).** `completeDispatchTask` invoca
`orchestration task-update --id <dispatch.taskId> --status completed`. Sin esto el dispatch queda
"active" en Orca y un segundo dispatch a la MISMA terminal se rechaza ("already has an active
dispatch") — el **reúso de sesión** (cross-review multi-ronda) fallaría (hallazgo del E2E caso c). No
falla la cosecha si el cierre falla, y no hace nada si falta `dispatch.taskId`. Para un dispatch único
por sesión el reúso no aplica, pero el cierre es buena higiene del lifecycle de Orca.

**Presupuesto de tiempo y liberar el turno.** `deadlineMs` es siempre un **presupuesto de espera**
contado desde la invocación (`deadlineAt = now() + deadlineMs`), no un timestamp absoluto — así lo
documenta el propio JSDoc de `harvest()`. Ningún loop de esta función espera indefinidamente: la
localización del rollout y el loop interno de `harvest()` revisan el deadline en cada vuelta.
Vencido el presupuesto, la función **devuelve el turno al llamador** con `code: 3` (o `code: 4` en
la fase de locator) en vez de colgarse — es la skill llamadora quien decide degradar a `cli` con
ese resultado, nunca esta función por sí sola reintenta más allá del presupuesto dado. El CLI
standalone (`harvest-from-transcript.mjs`) expone el mismo presupuesto vía `CMO_DEADLINE_MS`.

---

## Instalación y raíz conductor-only

Ver [`install.md`](./install.md) para el contrato completo de instalación (verificación de Node
≥18 vía `assertNode(18)`/`node --version`, y cómo `resolveInstallRoot()` en
`assets/lib/platform.mjs` autolocaliza la raíz de los módulos, con `CROSS_MODEL_ORCA` como
override opcional) — no se duplica acá.

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

**MCP del secundario read-only.** En el default **atendido**, MCP se controla por **vigilancia
manual** (P4): el secundario ve los MCP del entorno del usuario y el humano aprueba/rechaza en la
TUI cualquier acción sensible — no hay allowlist ni inventario que configurar (`--tools` acota solo
los built-ins, no las tools MCP). Para una corrida **desatendida** (sin gate humano), un gate
declarativo **opcional**: `--strict-mcp-config --mcp-config assets/launch/claude-readonly.mcp.json`
deja **solo** los servidores del allowlist (viene vacío → cero MCP; verificado en vivo con Claude
2.1.214: allowlist vacío → `CERO-MCP`). El modelo completo, el patrón para permitir un servidor de
lectura y la nota de namespacing están en `assets/launch/mcp-inventory.md`.

---

## Ver también

- `SKILL.md` — protocolo completo: envelope, tres capas de control, matriz de lanzamiento, matriz
  de raíces por skill/modo, privacidad v1, P4, degradación.
- `install.md` — instalación paso a paso (Node ≥18, `CROSS_MODEL_ORCA`, `skills-ref`).
- `assets/launch/profiles.md` — matriz de lanzamiento completa (POSIX+PowerShell) por
  familia×rol×modo.
- `assets/launch/mcp-inventory.md` — modelo de MCP: vigilancia manual (default) + endurecimiento
  opcional (`--strict-mcp-config`) para desatendido, y el namespacing real de tools.
- `assets/launch/claude-readonly.mcp.json` — template opcional (vacío) del allowlist de servidores
  MCP para el caso desatendido.
- `spikes/RESULTS.md` — contratos de locator y señal con evidencia (Task 0.1/0.2/0.3).
