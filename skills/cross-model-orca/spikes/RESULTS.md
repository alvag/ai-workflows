# Spikes de Fase 0 — bitácora de resultados

> Bitácora **fechada** de los spikes que fijan los contratos del transporte `orca-session`.
> Regla transversal: **sin un contrato inequívoco, la rama `orca-session` degrada a `cli`.**
> Plan: `docs/superpowers/plans/2026-07-18-cross-model-orca-transport.md`.

Entorno de referencia (registrar el real en cada corrida): Codex CLI 0.144.6 · Claude Code 2.1.214 ·
Orca 1.4.137 · `CODEX_HOME` = `~/Library/Application Support/orca/codex-runtime-home/home` (runtime de
Orca, **no** `~/.codex`).

---

## Task 0.1 — Contrato de locator de transcript/rollout

Estado: **RESUELTO (por inspección de stores existentes, 2026-07-19).** Sin lanzar sesiones nuevas: se
inspeccionaron 232 rollouts de Codex bajo `CODEX_HOME` y 23 transcripts de Claude bajo `~/.claude`.

### Codex (rollout)
- **Path:** `$CODEX_HOME/sessions/YYYY/MM/DD/rollout-<ISO-timestamp>-<session_id>.jsonl`.
  En este entorno `CODEX_HOME=~/Library/Application Support/orca/codex-runtime-home/home` (runtime de Orca).
- **`session_id`:** aparece en el **nombre del archivo** y en la 1ª línea `session_meta.payload.session_id`.
  La 1ª línea incluye además `cwd`, `source`, `originator`, `cli_version`. **Cuidado:** la 1ª línea es
  enorme (trae `base_instructions.text` = system prompt) → no parsearla entera; extraer campos del inicio.
- **Interactivo bajo Orca vs exec:** interactivo = `source:"cli"` / `originator:"codex-tui"`;
  `codex exec` = `source:"exec"` / `originator:"codex_exec"`. (Los `vscode/Claude Code` bajo `CODEX_HOME`
  son Codex invocado desde Claude, no transcripts de Claude.)
- **Locator ↔ terminal Orca:** `orca terminal list --json` **NO expone el `session_id`**, y Codex **no**
  admite fijar el session-id desde afuera. → El mapeo terminal↔rollout se hace **por creación + `cwd` +
  timestamp**: el conductor crea la sesión fresca y toma el rollout `cli/codex-tui` más reciente con ese
  `cwd` y mtime posterior a la creación. **Inequívoco en v1** (el flujo crea su sesión dedicada); ante
  ambigüedad (dos sesiones Codex naciendo en el mismo `cwd` en la misma ventana) → **fallback CLI**.
- **TIMING del rollout (verificado 2026-07-19, cierra el riesgo de secuencia del review de Task 1.5):** el
  rollout de Codex **NO existe al arrancar la terminal**; se escribe recién en el **primer turno** (tras el
  primer `dispatch --inject`). Comprobado: se creó una sesión Codex, se esperó el `tui-idle` de arranque, y
  **antes** de despachar había **0 candidatos** `cli/codex-tui` con ese `cwd`. → **El locator de Codex debe
  resolverse LAZY, después del primer dispatch** (cuando el rollout ya existe), no en `createOwnedSession`.
  Consecuencia para el adaptador (Task 1.5): `createOwnedSession` para Codex registra la sesión con
  `createdAt` (para el filtro de timestamp) pero **con `transcriptPath` pendiente**; la resolución del
  rollout ocurre en `awaitDone`/tras `createDispatch`, con retry acotado (por flush). Claude no tiene este
  problema: su locator es directo por `--session-id` desde `createOwnedSession`.
- **Parser (`parseTranscript('codex')`):** último `response_item` con `payload.role==="assistant"` →
  `payload.content[].output_text` concatenado. Verificado: el mensaje final llega íntegro (probado contra
  el rollout de la ronda 6 de review, que terminaba exacto en `VERDICT: APPROVED` / `STATUS: done`).

### Claude (transcript)
- **Path:** `${CLAUDE_CONFIG_DIR:-~/.claude}/projects/<slug>/<session-id>.jsonl`, donde `<slug>` = `cwd`
  con `/`→`-` (p. ej. `-Users-max-Personal-repos-ai-workflows`).
- **`session-id`:** **ES el nombre del archivo** y también va en cada línea (`sessionId`/`session_id`),
  junto a `cwd` y `gitBranch`. **Es FIJABLE con `--session-id <uuid>`** al lanzar → locator **directo e
  inequívoco** (mejor que Codex). No hace falta inferir por timestamp.
- **Parser (`parseTranscript('claude')`):** último objeto `type==="assistant"` con
  `message.content[].type==="text"` → `.text` concatenado.

### Fixtures capturados
- `assets/test/fixtures/codex-rollout.jsonl` y `assets/test/fixtures/claude-transcript.jsonl` — **sintéticos**
  que replican el shape real (no se copió contenido de conversaciones reales, por privacidad). Cada uno
  trae un mensaje de dispatch **anterior** (nonce viejo) + el **actual**, para testear la desambiguación por
  `nonce` (ronda 2 #17). El envelope de ejemplo es `X-CMO: taskId=.. dispatchId=.. nonce=..` + `STATUS: done`.

## Task 0.2 — Contrato de señal + estabilización

Estado: **PARCIAL** — la parte inspeccionable (orden en el transcript) quedó resuelta; el flush-timing
exacto y `tui-idle` requieren una **corrida live** (pendiente, coordinada con el usuario).

### Resuelto por inspección (rollouts interactivos con `worker_done`, 2026-07-19)
- **El mensaje final del turno NO es garantizadamente la última línea del transcript.** En un rollout real
  hay `function_call`/`function_call_output` (incluida la propia llamada a `orchestration send worker_done`)
  **después** del último `response_item` de texto del asistente. → El conductor **no** debe leer "la última
  línea"; debe buscar **la última entrada `assistant` de texto cuyo envelope cumpla `STATUS: done` + el
  `nonce`/IDs esperados**. Confirma el hallazgo de review r2 #15/#17.
- **Contrato de poll (fijado):** la señal `worker_done` es **solo wake-up**; la evidencia es el **envelope
  con `nonce`**. El conductor poll-ea el transcript hasta una entrada JSON **completa y parseable** (línea
  terminada en `\n`) con el envelope del dispatch en curso; ignora entradas de dispatches previos (nonce
  viejo) y líneas a medio escribir.

### Resuelto por corrida live (2026-07-19, sesión Codex fresca `term_debdf0e6`)
- **`nonce` en el envelope — ✅.** Se inyectó `nonce=NONCE-FASE0-7788` en el spec; el mensaje final del
  secundario en el rollout terminó exacto en `Hay 2 archivos .md.\nX-CMO: nonce=NONCE-FASE0-7788\nSTATUS: done`.
  El secundario copia el nonce → desambiguación viable.
- **`terminal wait --for tui-idle` — ✅** reportó `satisfied:true` tras el dispatch (fin del turno detectado).
- **Flush-timing — ✅ favorable:** al momento de consultar, el **mensaje final ya estaba escrito en el
  rollout** aun cuando el `worker_done` todavía no figuraba en el inbox del coordinador → la cosecha del
  transcript no depende de que la señal haya completado. El poll estabilizado con nonce es robusto ante el
  orden.
- **Body del `worker_done` ≠ envelope (hallazgo).** El `--body` que compuso el modelo fue un **resumen**
  ("Conté... 2 archivos .md..."), NO el envelope. El envelope con `nonce`+`STATUS: done` vive en el
  **mensaje final del transcript**. → Confirma que el informe se cosecha del transcript, no del body.
- **Locator live — ✅.** El rollout de la sesión se ubicó por creación+`cwd`+timestamp con **1 solo
  candidato** (`cli/codex-tui`, ai-workflows) — locator inequívoco en la práctica.

### Matiz para el adaptador (r4 #1 — autoridad)
El `worker_done` trae `payload={taskId,dispatchId}` (autoridad de tarea). El **sender** no vino en un campo
`from` obvio del mensaje parseado; a nivel protocolo Orca garantiza que un `worker_done` con el task/dispatch
activos **sólo** completa desde el pane asignado (CLI Notes: «the sender handle must exactly match the
dispatch assignee»). → La validación `expectedAssignee` vs `actualSender` puede apoyarse en esa garantía de
Orca + verificación de `taskId`/`dispatchId`; **localizar el campo exacto del sender** queda como detalle de
implementación del `dispatch-adapter`.

## Task 0.3 — Señal por comando (solo Codex) con hooks apagados

Estado: **RESUELTO (corrida live 2026-07-19).**

- **Codex read-only `--disable hooks -s read-only -a untrusted` emite `worker_done` por comando — ✅.**
  El modelo compuso y ejecutó, **sin prompt de aprobación** (confirmado por el usuario mirando la TUI):
  `orca orchestration send --to <coord> --from <sec> --type worker_done --subject "..." --body "<resumen>"`.
  Llegó al inbox del coordinador con `payload={taskId,dispatchId}`. Los hooks apagados (`--disable hooks`)
  no impidieron la señal (el modelo la emite por comando, no por hook).
- **Claude no señaliza (por diseño):** no se ejercitó en esta corrida; con toolset cerrado
  (`--tools "Read,Grep,Glob"`) no tiene Bash → su fin se detecta por `tui-idle` (validado en 0.2). Queda un
  checkpoint menor: confirmar `tui-idle` con un Claude secundario real (pendiente, no bloqueante — el
  mecanismo `tui-idle` ya se validó con Codex).
- **Mecanismo por familia:** Codex = señal `worker_done` por comando (wake-up + `{taskId,dispatchId}`);
  Claude = sin señal → `tui-idle`. **Ambos** cosechan del transcript.
- **Nota `-a` (atendido):** con `-a untrusted` el `send` corrió sin gate en este entorno. Si en otro perfil
  el `send` escalara a aprobación, aplica P4 (vigilancia manual / aprobar en la TUI).

---

## Fase 7 (2026-07-20) — validación y checkpoints

Estado: **PARCIAL** — lo ejecutable sin un entorno especial (Orca real, Windows, MCP Atlassian vivo)
quedó verificado en esta task; el resto se deja **honestamente marcado como pendiente**, sin declarar
verificado lo que no se corrió. Plan: sección "Fase 7" de
`docs/superpowers/plans/2026-07-18-cross-model-orca-transport.md`.

### Verificado

- **Test de parser >1 MB (lee del archivo, nunca de argv).** `assets/test/harvest-large.test.mjs`:
  genera, por cada familia (`claude`/`codex`), un fixture JSONL **en runtime** (`os.tmpdir()` +
  `fs.mkdtempSync`, nunca commiteado) con un mensaje del asistente anterior (nonce viejo, chico) y uno
  actual cuyo texto supera 1.1 MB, cerrado con el envelope real (`X-CMO: ... nonce=NONCE-ACTUAL` +
  `STATUS: done`). Confirma que `selectAssistantByNonce`/`parseTranscript` cosechan el mensaje grande
  leyendo el archivo (no `argv`, que jamás lo admitiría por `ARG_MAX`) y que la desambiguación por
  `nonce` sigue siendo correcta con un archivo grande (no devuelve el mensaje viejo por casualidad).
  También se corrió `harvest()` completo contra ese fixture (`reportPath` dentro de un `root` propio,
  respetando la contención) y se confirmó exit 0 con el informe persistido íntegro (>1 MB). Suite
  completa: **82 tests, 0 fail** (78 previos de las Fases 1–6 + 4 nuevos de esta task).
- **`CERO-MCP` con `--strict-mcp-config` + allowlist vacío (Claude 2.1.214).** Verificado headless en
  una task anterior de endurecimiento (commits `36afa6f`/`3f40c2e`); ver
  `assets/launch/mcp-inventory.md` y `assets/launch/profiles.md`.
- **`-c features.apps=false` válido inline (Codex, bajo `--strict-config`).** Confirmado sin
  "unknown field" contra los TOML instalados (`assets/launch/profiles.md`, tabla "Validación real", #7).
- **Mecanismo cross-model (locator + señal + cosecha) validado en vivo en Fase 0.** Locator de
  transcript/rollout por inspección de stores reales (Task 0.1); orden señal-vs-mensaje-final y `nonce`
  de desambiguación con una sesión Codex fresca real (Task 0.2); señal `worker_done` por comando con
  hooks apagados, confirmada en una corrida live (Task 0.3). Es la base empírica sobre la que se apoya
  el resto del transporte, aunque la matriz E2E completa de Task 7.1(a)(b)(c) no se repitió en esta task.
- **Windows — checkpoint completo (`[x]`), las 7 pruebas pasan.** Corrido en una máquina
  Windows real (Node 22.14.0, Windows 10.0.26200) con un runbook de 7 pruebas.
  **Pasan las pruebas 2–5 y la 3**, que ejercitan el
  artefacto directamente: `platform.mjs` resuelve rutas con backslashes bajo `%USERPROFILE%`, respeta
  `CODEX_HOME`/`CLAUDE_CONFIG_DIR`, y la **autolocalización** (`resolveInstallRoot` vía `fileURLToPath`)
  devuelve un `install` `C:\...` bien formado (sin el `/C:/` con barra inicial); `assertNode` da un
  mensaje legible; los JSON de settings parsean. **Foco real del checkpoint, verificado:** el **slug del
  transcript de Claude** (`slugifyCwd`) calcula `C--Users-MaxAlva-ai-workflows`, que coincide con el
  directorio que Claude crea bajo `~/.claude/projects/` (validado contra la sesión real actual, sin
  lanzar una sesión nueva). **Suite de tests en Windows — verde tras fix.** La corrida inicial dio
  `82 / 63 pass / 19 fail`; los 19 fallos eran de la suite, no de la lógica: (H1) `new
  URL(import.meta.url).pathname` deja `/C:/...` en 3 archivos de test (`dispatch-adapter.test.mjs`,
  `harvest-core.test.mjs`, `harvest-entry.test.mjs`) → fixtures no se leen (`ENOENT`) → 16 fallos; (H2)
  `fs.symlinkSync` da `EPERM` sin modo desarrollador → 2 fallos; (H3) un test de `configDir` hardcodea
  `/tmp/...` y compara igualdad exacta → 1 fallo. **Resueltos por el commit `f27e119`**
  (`test(cross-model-orca): portabilidad del suite a Windows` — `fileURLToPath`, skip de symlinks,
  `path.resolve`): tras él, `node --test` da `82 / 80 pass / 0 fail / 2 skip` (los 2 skip son los tests
  de symlink, inejecutables sin modo desarrollador). **Pruebas 6 y 7 (CLIs de IA reales) — pasan:** Claude respondió `CERO-MCP` (exit 0) con
  `--strict-mcp-config` + allowlist vacío (requiere `-p` para modo headless; sin él abre la TUI), y
  Codex respondió `OK` (exit 0) con `-c features.apps=false --strict-config` aceptado inline sin
  "unknown field". Con esto el checkpoint Windows queda **completo**.

### E2E live — caso (a) Claude→Codex explore: VERDE (2026-07-20)

Primer contacto del adaptador con Orca real. Corrido punta a punta contra el runtime vivo:
`createOwnedSession` → `createDispatch` (boot-wait + `dispatch --inject`) → Codex read-only leyó los
4 módulos de `assets/` → `awaitDone` **cosechó el informe por nonce** (`code 0`, 518 bytes con el
envelope correcto). El E2E destapó y corrigió cuatro capas de bugs, todas en `dispatch-adapter.mjs`:

1. **Envelope JSON de Orca.** Todo comando `orca --json` envuelve en `{ id, ok, result|error, _meta }`;
   el adaptador leía campos planos → `null` siempre → degradaba a `cli` siempre. Regla: éxito =
   `ok===true` (nunca el exit code — `terminal close` sobre handle stale da `ok:false` pero exit 0).
   Formas reales: `terminal create`→`result.terminal.handle`, `task-create`→`result.task.id`,
   `dispatch`→`result.dispatch.id`, `check`→`result.messages` (con `payload` **string JSON** y emisor
   en `from_handle`).
2. **Boot-wait.** `createDispatch` espera `tui-idle` antes de `dispatch --inject`, si no el prompt se
   pierde (ver "Dispatch: esperar el boot antes de inyectar" en `reference.md`).
3. **Detección de fin migrada a nonce en el transcript propio.** Se **abandonó `worker_done`**: un Codex
   sandboxeado no lo envía de forma confiable (falla **intermitente** con "Orca is not running", el
   `ORCA_CLI_SOCKET` viene vacío en el sandbox `read-only`). Se eliminó `checkWorkerDoneAuthority`, el
   poll de `orchestration check`, el poll de `tui-idle` como autoridad y `--from`/coordinatorHandle.
   `awaitDone` ahora localiza el rollout y deja que `harvest()` sondee el transcript por `nonce`+sentinel
   — señal que el conductor (no sandboxeado) siempre observa. Mismo modelo para ambas familias.
4. **Contención de `reportPath`.** Confirmada: un `reportPath` **absoluto** se rechaza (`code 2`); debe
   ser relativo a `root`.

Actualiza CONTRATO-CROSS-VENDOR-Fase0: el mecanismo por familia de Task 0.2/0.3 (Codex = `worker_done`
por comando) queda **superado** — la señal confiable es el envelope en el transcript propio, no
`worker_done` (que ahora es ruido inofensivo del preamble de `--inject`).

### E2E live — caso (b) Codex→Claude explore: VERDE (2026-07-20)

Secundario = Claude read-only. `createOwnedSession` → boot-wait → `dispatch --inject` → Claude leyó
los 4 módulos → `awaitDone` cosechó por nonce (`code 0`, ~40 s). El Claude lanzado por Orca escribe
su transcript en el DEFAULT `~/.claude/projects/<slug>/<session-id>.jsonl` (Orca NO sobreescribe
`CLAUDE_CONFIG_DIR`, a diferencia de `CODEX_HOME`) → coincide exacto con lo que computa el adaptador.

**Hallazgo de contención (y su fix).** En una primera corrida, Claude read-only —al que el preamble
de `dispatch --inject` le pide un `worker_done`— no tenía Bash (toolset cerrado) pero **sí** los MCP
del entorno, así que usó `mcp__idea__execute_terminal_command` (la terminal del IDE del usuario) para
correr el `orca orchestration send`: un comando **fuera del worktree, en otro proyecto**, gateado por
aprobación manual pero fuera de lo esperado para un read-only. `--tools` cierra los built-ins, NO las
tools MCP. **Fix:** el read-only de Claude ahora se lanza con **MCP off** (`--strict-mcp-config
--mcp-config claude-readonly.mcp.json` vacío). Re-validado en vivo: Claude intentó el `worker_done`
por Bash → **denegado** (`No such tool available: Bash`), sin MCP no tuvo ruta al IDE, y cerró con el
envelope. Read-only = sin superficie de ejecución (solo Read/Grep/Glob). Ver `SKILL.md` §3.2 y
`profiles.md`.

**Descartado: `terminal send` en vez de `dispatch --inject`.** Se evaluó entregar la tarea por
`terminal send` (prompt plano, sin preamble → sin `worker_done`) para eliminar ese ruido. Entrega
limpia y multilínea en la TUI de **Claude** (validado, cosecha en ~9 s), pero en la TUI de **Codex**
**duplica el prompt** (llega dos veces) y no completó en 240 s. No es un reemplazo robusto y
universal de `dispatch --inject` (que sí funciona para ambas familias), así que se mantiene
`dispatch --inject` y el ruido del `worker_done` se neutraliza por rol: read-only con MCP off (no
puede ejecutarlo), Codex lo corre en su sandbox shell (inofensivo, contenido).

### E2E live — caso (c) cross-review, 2 rondas / reúso de sesión: VERDE (2026-07-20)

Secundario = Claude read-only (MCP off). Review adversarial de un spec real
(`docs/superpowers/specs/2026-07-17-co-explore-debate-mode-design.md`), **dos rondas sobre la MISMA
sesión**. Ambas cosecharon `code 0` (5191 y 4855 bytes — reviews reales y estructurados, leídos del
transcript, no del preview). Verificado: r1 contiene **solo** su nonce (no el de r2) y viceversa
(desambiguación por nonce en sesión reutilizada), y r1 ≠ r2 (reúso real, no re-cosecha del mismo
mensaje). Sin tocar el IDE (MCP off). ~2.5 min total.

**Hallazgo de reúso (y su fix).** La primera corrida falló en la ronda 2: `dispatch --inject` a la
misma terminal devolvió `ok:false` con `"Terminal ... already has an active dispatch"`. Causa: como
NO usamos `worker_done` (que completa el dispatch automáticamente en Orca), el dispatch de la ronda 1
queda **"active"** y Orca rechaza un segundo dispatch a esa terminal. **Fix:** `awaitDone`, tras una
cosecha exitosa, cierra el dispatch con `orchestration task-update --id <taskId> --status completed`
(best-effort, requiere `dispatch.taskId`). Re-validado: las dos rondas verdes. Nota: para un dispatch
único por sesión (co-explore, cross-implement) el reúso no aplica, pero el cierre es buena higiene.

> Nota de tarea (no de transporte): un Codex a **xhigh** con un prompt "exhaustivo, listá TODOS los
> hallazgos" razona sin cerrar el turno y puede exceder un deadline de 5 min. El review acotado
> ("los 6-8 hallazgos más importantes") cierra rápido. El mecanismo de cosecha es indiferente a esto.

### Pendiente (checkpoints, requieren entorno real)
- **Atlassian (gate de escritura real con MCP vivo).** Bajo vigilancia manual: confirmar que una tool de
  escritura de Atlassian invocada por el secundario efectivamente escala a aprobación en la TUI (cierra
  también el punto de P4 que quedó pendiente en Task 7.1: "el prompt en la TUI ante una acción sensible"
  no se disparó en la corrida live de Task 0.3, porque el comando ejecutado no escaló). Qué correr:
  sesión secundaria con el MCP de Atlassian configurado, dispatch que la induzca a intentar una
  operación de escritura (`create*`/`update*`/etc.). Qué se espera: el prompt de aprobación aparece en
  la TUI antes de que la operación se ejecute; sin aprobación, no se escribe nada.
