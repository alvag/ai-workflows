# Transporte `orca-session` cross-model — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que `co-explore`, `cross-review`, `cross-implement`, `sdd-flow` y `sdd-orchestrator` puedan delegar en una **sesión interactiva real** de la otra familia vía **Orca** (transporte `orca-session`), con **degradación transparente al CLI headless de hoy** y **tres capas de control** de efectos laterales, sin cambiar el comportamiento de las skills cuando Orca no está.

**Architecture:** Una **skill-librería `cross-model-orca`** aloja el protocolo común y **el único artefacto ejecutable del repo**: un módulo Node **del lado del conductor** que, tras detectar el fin del turno del secundario, **lee el transcript/rollout** de la **sesión fresca que el propio flujo creó**, valida un **envelope con autoridad** (`taskId`/`dispatchId`/`nonce` + `STATUS: done`) y persiste el informe. Decisión de raíz: **el secundario read-only no cosecha ni escribe** — el conductor cosecha. Sobre esto la ronda 2 de review impuso cuatro correcciones: (1) la señal `worker_done` es solo **wake-up**, no evidencia de que el transcript esté escrito → el conductor detecta el fin por la transición **busy→idle posterior al dispatch** y **poll acotado y estabilizado** del transcript; (2) el mensaje cosechado se **liga al dispatch** por `nonce`+IDs (una sesión reutilizada tiene mensajes de dispatches previos); (3) el **locator** del transcript/rollout (path exacto, respetando `CODEX_HOME`/`CLAUDE_CONFIG_DIR`, y captura del session/thread-id) es un **contrato que fija el Gate 0** — sin locator inequívoco, **fallback CLI**; (4) v1 cosecha **solo sesiones frescas del flujo** (nunca abre el transcript de una sesión ajena — privacidad). Cada skill gana un paso "resolver transporte"; el resto no cambia. `sdd-flow`/`sdd-orchestrator` suman `cross_model.transport` y **propagan el override al agente delegado**.

**Tech Stack:** Markdown (skills), **Node.js** (dependencia **externa** a los CLIs, verificada en preflight; nunca `python3`), Orca CLI, Codex CLI (config **server-scoped** `mcp_servers.<id>.*`, `--disable hooks`, `-s`/`-a`), Claude CLI (`--settings`/`disableAllHooks`/`--permission-mode manual` — **no existe `default`**). Validación: `skills-ref validate` (con **instalación reproducible**, ver 1.1) + `node --test` (funciones puras **y** entry points como subproceso contra un Orca falso).

## Global Constraints

- **Idioma:** español neutro en todo artefacto y commit. Sin voseo ni modismos.
- **Doble variante de CLI:** cada comando nuevo (setup, launch, dispatch, espera, recuperación, validación) con bloque **POSIX** y **PowerShell** completos — nada de `...`. PowerShell no soporta `<`: `Get-Content -Raw f | <cli> ... -`.
- **Degradación sin Orca intacta:** el transporte `cli` (`codex exec`/`claude -p`) es el status quo y el **fallback por defecto** ante cualquier incertidumbre (runtime `stale_bootstrap` desde el conductor, locator ambiguo, sesión no propia). Sin cambios de comportamiento observables.
- **Artefacto Node cross-runtime:** rutas por plataforma **respetando `CODEX_HOME`/`CLAUDE_CONFIG_DIR`** cuando están seteadas (en este entorno `CODEX_HOME` apunta al runtime de Orca, no `~/.codex`); ruta instalada estable vía `CROSS_MODEL_ORCA` (task de instalación).
- **Tres capas de control, válidas y verificadas:** (1) **sandbox/toolset**: Codex `-s read-only`; **Claude SIEMPRE con toolset cerrado** `--tools "Read,Grep,Glob"` (Bash fuera del toolset → read-only duro, **inmune a un `allow:["Bash"]` heredado** de otro scope, ronda 3 #7) → **Claude no señaliza por comando**; su fin lo detecta el conductor por `tui-idle`. La señal por comando queda **solo para Codex** (sandbox de kernel + `-a untrusted`); (2) **MCP**: Codex por **perfil instalado** `$CODEX_HOME/<nombre>.config.toml` invocado con **`-p <nombre>`** (no `-c`, que solo toma `key=value`) — claves **server-scoped** `mcp_servers.<id>.{enabled,enabled_tools,disabled_tools,default_tools_approval_mode}` + `mcp_servers.<id>.tools.<t>.approval_mode` (modos `auto|prompt|writes|approve`) **y** overrides por ID para `apps.*` y `plugins.*.mcp_servers.*`; Claude `allow`/`ask`/`deny` por tool enumerada **con preflight de reglas efectivas** que bloquea si hay un `allow` amplio de Bash/escritura heredado; **preflight que falla cerrado** ante servidor/tool/app/plugin no inventariado; nunca wildcards; (3) **hooks**: `disableAllHooks:true` (Claude) / `--disable hooks` (Codex). Sin las tres, no se despacha.
- **Señal vs cosecha (arquitectura v2, endurecida en rondas 2–4):** el secundario **Codex** señaliza `worker_done` por comando (wake-up temprano); **Claude no señaliza** → el conductor detecta su fin por `tui-idle`. **La validación de autoridad ocurre en el conductor ANTES de cosechar** (ronda 4 #1): al llegar el `worker_done`, el adaptador compara su `sender` (`actualSender`) con el `expectedAssignee` capturado del `dispatch`, más `taskId`/`dispatchId`/`sessionId`; **solo si todo coincide** invoca el harvester, que recibe la entrada **ya autorizada** (no revalida el sender, que no aparece en el transcript). Pasos: (a) transición **busy→idle posterior al dispatch** (`tui-idle`, nunca un idle aislado); (b) **poll acotado y estabilizado** del transcript hasta una entrada JSON **completa** con el **`nonce` + `taskId`/`dispatchId`** esperados; (c) persiste. **Exactly-once = FSM persistente y crash-idempotent** con clave durable `dispatchId+nonce`: estados `received → harvested → promoted`. La promoción es **determinística e idempotente**: el canónico se **reconstruye por completo desde los raws inmutables** (uno por dispatch/ronda) hacia un temporal + **`rename` atómico**; se persiste `desiredCanonicalHash` y `promoted` se marca solo cuando el canónico ya tiene ese hash → una caída **post-rename/pre-promoted** (ronda 4 #2) re-ejecuta la reconstrucción y produce el mismo resultado, sin doble incorporación.
- **Raíz conductor-only (ronda 4 #7):** el **registro de sesiones propias** y la **FSM durable** viven en un directorio **exclusivo del conductor, fuera de todo worktree que el secundario pueda escribir** — un secundario `workspace-write` no debe poder alterar autoridad ni dedup —, con permisos restrictivos y updates atómicos.
- **Envelope con autoridad:** salida del modo + una línea `X-CMO: taskId=<..> dispatchId=<..> nonce=<..>` + `STATUS: done` como última línea no vacía. El conductor cosecha **solo** el mensaje que trae el `nonce` del dispatch en curso.
- **`reportPath` = ruta destino inexistente**, contención canónica robusta: **canonicalizar la raíz autorizada** (`realpath`) antes de comparar; rechazar absolutas/`..`; `realpath` del padre dentro de la raíz; **destino inexistente** (`lstat`, contra symlink final); escritura **exclusiva** (`wx`). Para destinos **acumulativos** (p. ej. el `review-log.md` de cross-review, que se actualiza cada ronda) la cosecha escribe un **raw único por dispatch/ronda** (`wx` válido) y luego **promueve/actualiza atómicamente** el archivo canónico. Matriz de raíces por skill/modo (incluye `.plans/<id>/…`, `.sdd/<id>/…`, y standalone `.co-explore/<slug>/`, `.cross-review/<slug>/`, scratch de cross-implement) en la skill-librería.
- **Privacidad (v1) — sin excepciones (rondas 3–4 #4/#19):** el conductor cosecha **exclusivamente transcripts de sesiones frescas que el propio flujo creó**. Una sesión **ajena** nunca se cosecha en v1 — **ninguna rama de consentimiento** —: fuerza crear una sesión fresca, o degrada a `cli`. La apropiación de sesiones ajenas para cosecha queda fuera de v1 (aplica también a la Task 2.2 del resolver).
- **P4 = vigilancia manual declarada** (atendido). Sin surfacing del `PermissionRequest` en v1.
- **Alcance:** solo `skills/**` y `docs/**`. **Git:** conventional commits, scope = skill; sin firmas.

---

## Estructura de archivos

```
skills/cross-model-orca/
  SKILL.md · reference.md · README.md · install.md
  assets/
    harvest-from-transcript.mjs    # ENTRY conductor: espera idle, poll estabilizado, valida autoridad+nonce, persiste
    harvest-core.mjs               # puro: sentinel, envelope+nonce, contención robusta, parseTranscript(family), dedup-fsm
    dispatch-adapter.mjs           # ENTRY conductor: IDs/handles de --json, nonce, espera busy→idle, recover(interrupt/close)
    lib/platform.mjs               # rutas (CODEX_HOME/CLAUDE_CONFIG_DIR), Node preflight, CROSS_MODEL_ORCA
    launch/  profiles.md  claude-readonly.settings.json  claude-write.settings.json
             codex-readonly.config.toml  codex-write.config.toml  mcp-inventory.md
    test/  harvest-core.test.mjs  harvest-entry.test.mjs  platform.test.mjs  fixtures/
  spikes/RESULTS.md
```
Skills modificadas: `co-explore` · `cross-review` · `cross-implement` · `sdd-flow` · `sdd-orchestrator` (solo se agrega rama `orca-session`; `cli` intacta).

---

## Fase 0 — Reconciliación del diseño + spikes que fijan contratos (sin ellos → fallback CLI)

### Task 0.0: Reconciliar el diseño con la arquitectura de cosecha (ronda 3 #9)

**Por qué:** el plan supersede al diseño (`revision-y-refinamientos.md`), que aún declara normativo que el **notifier/Stop hook escribe `reportPath` antes de `worker_done`**. El plan usa **cosecha del conductor desde el transcript** (sin notifier, sin `reportPath` escrito por el secundario, sin `ARG_MAX`). Dos contratos incompatibles no pueden coexistir como fuente de verdad.

- [ ] **Step 1:** agregar a `docs/research/cross-model-real-sessions/revision-y-refinamientos.md` una entrada de **Procedencia (duodécima ronda)** y una nota de **decisión superseding** en §9.8: la cosecha v1 es **del conductor leyendo el transcript/rollout de la sesión fresca**; el notifier/`reportPath`-antes-de-`worker_done` queda **superseded** (se conserva por trazabilidad). Actualizar el encabezado de estado.
- [ ] **Step 2:** validar que no queden en el diseño afirmaciones normativas que contradigan la cosecha del conductor (tabla de precedencia, §5, §7).
- [ ] **Step 3: Commit.** `git commit -m "docs(cross-model): decisión superseding — cosecha del conductor desde transcript (round 12)"`

### Task 0.1: Contrato de **locator** de transcript/rollout (bloquea la cosecha Orca)

**Por qué:** sin un locator inequívoco del transcript de la sesión fresca, la cosecha no es confiable (ronda 2 #16). Debe respetar `CODEX_HOME`/`CLAUDE_CONFIG_DIR`.

- [ ] **Step 1: Claude.** Lanzar secundario con `--session-id <fijo>` bajo el `CLAUDE_CONFIG_DIR` efectivo; localizar `<config>/projects/<slug>/<session>.jsonl`; confirmar que el session-id fijado permite ubicarlo sin ambigüedad. Fixture → `test/fixtures/claude-transcript.jsonl`.
- [ ] **Step 2: Codex.** Lanzar Codex interactivo bajo Orca; **capturar el thread/session-id** (registrar CÓMO: preámbulo, evento, o archivo) y localizar el rollout bajo `CODEX_HOME` (aquí `…/orca/codex-runtime-home/home/sessions/**`); confirmar formato real (`response_item.payload.content[].output_text`). Fixture → `test/fixtures/codex-rollout.jsonl`.
- [ ] **Step 3:** documentar en `RESULTS.md` el **contrato**: cómo se captura el id y el path exacto por plataforma/entorno. **Si el id o el path no son inequívocos → la skill degrada a CLI.** **Commit.**

### Task 0.2: Contrato de **señal + estabilización** (bloquea la detección de fin)

**Por qué:** la señal puede preceder al mensaje final; leer temprano da contenido incompleto (ronda 2 #15/#17).

- [ ] **Step 1:** despachar y observar el orden real: ¿el `worker_done` (tool-call) se persiste antes que el mensaje final del asistente en el transcript? Medir la ventana.
- [ ] **Step 2:** validar `terminal wait --for tui-idle` como señal de **transición busy→idle posterior al dispatch**; confirmar que distingue un idle nuevo de uno preexistente.
- [ ] **Step 3:** validar que un **`nonce`** inyectado en el prompt aparece en el envelope del mensaje final y permite descartar mensajes de dispatches previos en una sesión reutilizada. Registrar el contrato de poll estabilizado (entrada JSON completa + nonce + IDs). **Commit.**

### Task 0.3: Contrato de **señal por comando** (solo Codex) con hooks apagados

- [ ] **Step 1: Codex read-only** `--disable hooks -s read-only -a untrusted`: confirmar que emite `worker_done` por comando con `--subject`.
- [ ] **Step 2: Claude read-only** con **toolset cerrado** `--tools "Read,Grep,Glob"` (sin Bash): confirmar que **no** señaliza → la detección de fin recae por completo en `tui-idle` (0.2). **No hay rama Claude+Bash** (ronda 4 #6): el toolset cerrado es la garantía read-only, inmune a un `allow` heredado. Registrar el mecanismo por familia. **Commit.**

---

## Fase 1 — Artefacto ejecutable (lado conductor)

### Task 1.1: `platform.mjs` + `install.md` + preflight de `skills-ref`
**Files:** Create `assets/lib/platform.mjs`, `install.md`; Test `assets/test/platform.test.mjs`
**Produces:** `configDir(family)` (respeta `CODEX_HOME`/`CLAUDE_CONFIG_DIR`, cae a `~/.codex`/`~/.claude`); `isWindows()`; `assertNode(min)`; `resolveInstallRoot()` (lee `CROSS_MODEL_ORCA`).
- [ ] Test que falla → implementar → pasar.
- [ ] `install.md`: verificar Node ≥18; exportar `CROSS_MODEL_ORCA` (POSIX+PowerShell); **instalación reproducible de `skills-ref`** (comando concreto del paquete de agentskills, o ruta a un validador incluido en el repo) y su fallback si no puede instalarse.
- [ ] **Commit.**

### Task 1.2: `harvest-core.mjs` — sentinel, envelope+nonce, contención, parser, dedup-FSM
**Files:** Create `assets/harvest-core.mjs`; Test `assets/test/harvest-core.test.mjs`
**Produces:** `hasSentinel`; `parseEnvelope(msg)→{taskId,dispatchId,nonce,body}`; `checkContainment(reportPath,root)` (**canonicaliza root**, `lstat` destino, symlink final); `writeExclusive(path,data)` (`wx`); `parseTranscript(family,file)→lastAssistantMsg` (matcher del spike 0.1); `dedupFsm` **crash-idempotent** con clave durable `dispatchId+nonce`, estados persistidos `received→harvested→promoted`, raw reutilizable por **hash**, y promoción por reconstrucción en temporal + **`rename` atómico** (marca `promoted` solo tras el rename).
- [ ] Tests que fallan: sentinel (citado en cuerpo → false); `parseEnvelope` extrae nonce/IDs y rechaza si faltan; `checkContainment` con **symlinks reales** en padre **y** componente final + destino existente rechazado + root canonicalizada; `parseTranscript` sobre fixtures reales; `dedupFsm` reprocesa tras fallo pero no tras `promoted`.
- [ ] Implementar → pasar → **commit.**

### Task 1.3: `harvest-from-transcript.mjs` — entry conductor (espera + estabilización + autoridad)
**Files:** Create `assets/harvest-from-transcript.mjs`; Test `assets/test/harvest-entry.test.mjs`
**Consumes:** `harvest-core`, `platform`. **Produces:** dado `{family, sessionLocator, taskId, dispatchId, nonce, reportPath, root, deadline}` **ya autorizado por el adaptador** (la comparación `actualSender` vs `expectedAssignee` + IDs ocurre en `dispatch-adapter.awaitDone` **antes** de invocar, ronda 4 #1; el harvester no revalida el sender, ausente del transcript): poll estabilizado del transcript hasta entrada completa con nonce+IDs; persiste (raw→promote si acumulativo, crash-idempotent con reconstrucción determinística); exit 0/2(contención)/3(timeout sin envelope válido).
- [ ] Test como subproceso: fixture con mensaje de dispatch **previo** (nonce viejo) + mensaje actual → cosecha **solo** el actual; timeout → exit 3; `..` → exit 2; **crash-idempotencia**: correr dos veces (simulando caída tras el `wx` del raw) → una sola promoción, sin `EEXIST` fatal.
- [ ] Implementar → pasar → **commit.**

### Task 1.4: Perfiles de seguridad **válidos** (verificados) + inventario MCP con apps/plugins
**Files:** `assets/launch/{profiles.md,claude-readonly.settings.json,claude-write.settings.json,codex-readonly.config.toml,codex-write.config.toml,mcp-inventory.md}`
- [ ] `mcp-inventory.md`: tools por nombre (lectura/escritura) **+ `apps.*` + `plugins.*.mcp_servers.*`**; regla: no inventariado → bloquea.
- [ ] `claude-readonly.settings.json`: `disableAllHooks:true` + **toolset cerrado** `--tools "Read,Grep,Glob"` (sin Bash → read-only duro **inmune a un `allow` heredado**, confirmado en ronda 4; Claude no señaliza, el fin lo detecta el conductor por `tui-idle`) + `ask`/`deny` por tool MCP de **escritura enumerada**. (No se usa dump de permisos efectivos: `claude --print-permissions` **no existe** en 2.1.214, ronda 4 #6; el toolset cerrado **es** la garantía.) `claude-write.settings.json`: mismo worktree = `--permission-mode manual` + `Edit(./**)`/`Write(./**)`/`Bash(<proof>:*)`; `acceptEdits` **solo** worktree hermano aislado.
- [ ] `codex-readonly.config.toml`/`codex-write.config.toml`: **server-scoped** `mcp_servers.<id>.{enabled,enabled_tools,disabled_tools,default_tools_approval_mode}` + `mcp_servers.<id>.tools.<t>.approval_mode` (modos `auto|prompt|writes|approve`); **apps fail-closed con `features.apps=false`** (ronda 5 #5: `apps._default.enabled=false` **no** neutraliza un `apps.<id>.enabled=true` heredado, y `mcp list` no enumera apps → se apaga toda la superficie); MCP de plugins enumerados/deshabilitados por ID; `-s`/`-a`/`--disable hooks`. Se **instalan** como `$CODEX_HOME/<nombre>.config.toml` y se invocan con **`-p <nombre>`** (no `-c`, que solo toma `key=value`).
- [ ] `profiles.md`: matriz familia×rol×modo con comando **POSIX+PowerShell** por celda + domesticación del arranque (hallazgo A).
- [ ] **Validación real (rondas 3–5 #4/#5):** (a) existencia del perfil con `test -f`/`Test-Path` — un perfil inexistente se **ignora silenciosamente**; (b) enumerar servidores efectivos con `codex -p <nombre> mcp list --json` y **compararlos contra el inventario** → cualquier diferencia **bloquea**; (c) `codex -p <nombre> mcp get <servidor>` por cada servidor inventariado; (d) **apps fail-closed con `features.apps=false`** (no per-app, que un override heredado burla y `mcp list` no enumera); (e) validación **separada** de los `approval_mode` (no los muestra `mcp get`); (f) `node -e JSON.parse` para los settings de Claude. **Commit.**

### Task 1.5: `dispatch-adapter.mjs` — contexto, nonce, espera, recuperación con interrupt/close
**Files:** Create `assets/dispatch-adapter.mjs`; Test `assets/test/harvest-entry.test.mjs`
**Produces:**
- `createOwnedSession({family,role,mode,worktree})` (ronda 3 #2) → crea la terminal fresca (`terminal create` con el perfil de 1.4), **captura el locator** (`sessionId/threadId`+`transcriptPath` según el contrato del spike 0.1, respetando `CODEX_HOME`/`CLAUDE_CONFIG_DIR`) y registra `{terminalHandle,family,sessionId/threadId,transcriptPath,createdAt,uid}` en un **registro de sesión propia** del conductor. Si el locator no es inequívoco → devuelve `null` (la skill degrada a `cli`).
- `createDispatch({session, spec, root})` → captura `taskId`/`dispatchId`/**`expectedAssignee`** de `task-create --json`+`dispatch --inject --json`, **genera `nonce`**, y persiste el registro del dispatch `{expectedAssignee, taskId, dispatchId, nonce, sessionRef}` (el `actualSender` se agrega al llegar el `worker_done`).
- `awaitDone` → al llegar el `worker_done`, **valida autoridad** (`actualSender` vs `expectedAssignee` + IDs) y solo entonces invoca el harvester (ronda 4 #1); busy→idle + wake-up + poll estabilizado (vía 1.3, ya autorizado) + dedup-FSM crash-idempotent. **El registro de sesión y la FSM viven en la raíz conductor-only** (fuera de worktrees del secundario, ronda 4 #7).
- `recover` → **`terminal send --interrupt` o `terminal close`** (Orca **no** cancela un dispatch, ronda 2 #7), **confirmar idle** y recién redispatch por CLI; **write:** prohibido el redispatch sin cierre demostrado del escritor.
- [ ] Tests: `createOwnedSession` registra el locator o devuelve `null`; parseo de IDs y `expectedAssignee` de `--json`; `awaitDone` deduplica y compara `expectedAssignee` vs `actualSender`; `recover` interrumpe+confirma-idle y no redispacha write sin cierre.
- [ ] Implementar → pasar → **commit.**

---

## Fase 2 — Skill-librería (protocolo + resolver)

### Task 2.1: `SKILL.md` + `README.md`
- [ ] `SKILL.md` (`name`, `description` tercera persona "no se invoca sola", `disable-model-invocation:true`): envelope+autoridad, tres capas, matriz de lanzamiento, **matriz de raíces por skill/modo** (incluye `.sdd/<id>/co-explore/` y standalones), **privacidad v1**, P4, degradación. `README.md` humano. Validar; **commit.**

### Task 2.2: `reference.md` — resolver + disponibilidad + recuperación + espera
- [ ] Resolver: `override ?? config ?? auto`; **disponibilidad = runtime alcanzable desde el proceso conductor** — `stale_bootstrap` desde el conductor → **degradar a CLI** (salvo broker host-side explícito). Separar runtime de sesión del flujo (crear fresca; reutilizar solo propias; **una sesión ajena nunca se cosecha en v1 → fuerza sesión fresca o `cli`**, sin rama de consentimiento — ronda 4 #3).
- [ ] Recuperación con interrupt/close+confirmar-idle; espera bloqueante/backoff/presupuesto/liberar turno; contención+envelope+instalación. POSIX+PowerShell. Validar; **commit.**

---

## Fases 3–6 — Enganche por skill (rama `orca-session`; `cli` intacta)

### Task 3.1: `co-explore/reference.md`
- [ ] Paso resolver; rama orca-session crea sesión **fresca** dedicada read-only, dispatch con **nonce+IDs** (1.5), cosecha del conductor (1.3) a `.plans/<id>/co-explore/` (o `.sdd/<id>/…`, `.co-explore/<slug>/`). Diff aditivo. Validar; **commit.**

### Task 4.1: `cross-review/reference.md` — sentinel universal
- [ ] Agregar la línea `X-CMO:` + `STATUS: done` tras `VERDICT:`/`FINDINGS:` **solo** en orca-session (`cli` igual). Validar; **commit.**

### Task 4.2: `cross-review/reference.md` — reutiliza sesión + cosecha raw→promote
- [ ] Rama orca-session reutiliza la sesión del flujo (reutilización de sesión, **diseño §2.3**), nonce por ronda para desambiguar; **cosecha a raw único e inmutable por ronda, luego reconstruye y promueve atómicamente `review-log.md`** (que incluye también las decisiones del árbitro; no `wx` sobre el acumulativo — ronda 3 #3). Validar; **commit.**

### Task 5.1: `cross-implement/reference.md` — write-capable + worktree correcto
- [ ] Sesión write propia; mismo worktree = `--permission-mode manual` + `Edit/Write(./**)` + `Bash(<proof>:*)`; **`acceptEdits` solo worktree hermano aislado**; escritor único; clean-tree gate; MCP escritura sensible = `ask`; cosecha del conductor; `git diff` como PR ajeno. Validar; **commit.**

### Task 6.1: `sdd-flow` — `cross_model.transport`
- [ ] Clave `cross_model.transport` en `.specify/config.yml` (default `auto`); propagar **solo `desired`** como override a las skills delegadas. **Cada skill reevalúa `effective`** (reachability desde su propio proceso) — no se propaga el transporte ya resuelto. Validar; **commit.**

### Task 6.2: `sdd-orchestrator` — clave + propagación del `desired` al prompt delegado
- [ ] Clave en `manifest.yml`; **modificar la plantilla del prompt del agente delegado** para pasar **`cross_model.transport.desired`** (ronda 3 #8: no el `effective` del padre — el delegado corre en otro proceso que puede ver `stale_bootstrap` aunque el padre alcance Orca; el hijo resuelve su propio `effective` y reporta fallback). Validar; **commit.**

---

## Fase 7 — Validación E2E + checkpoints + P4

### Task 7.1: Matriz E2E + parser grande + seguridad
- [ ] (a) Claude→Codex explore; (b) Codex→Claude explore; (c) cross-review (envelope+`STATUS: done`), **con las tres capas configuradas** y validadas.
- [ ] **P3-largo (ronda 2 #20): separar** — (i) **test de parser** con fixture JSONL fabricado **>1 MB** (prueba que la cosecha lee del archivo, nunca argv); (ii) **E2E real** con el **máximo output alcanzable** por el modelo, confirmando cosecha del rollout bajo `CODEX_HOME`.
- [ ] Confirmar que una tool MCP de **escritura** (`deny`/`ask`) no corre sin gate; y que el **preflight** bloquea MCP/app/plugin no inventariado. **Commit.**

### Task 7.2: Checkpoints (Windows, Atlassian) · Task 7.3: P4 vigilancia manual
- [ ] Windows: `disableAllHooks`/`--disable hooks`, auth Credential Manager/DPAPI, entry Node con `%USERPROFILE%\…`/`CODEX_HOME`, rutas de transcript por plataforma. Atlassian: gate con tool de escritura real en repo con MCP vivo. P4: documentar vigilancia manual en la librería + cada skill. Validar todas; **commit.**

---

## Self-Review (cobertura + cierre de rondas 1–2)

Ronda 1 (#1–#14) y ronda 2 (#1–#20) mapeados a tasks:
- Perfiles válidos server-scoped/manual/apps/plugins + `--strict-config`: 1.4 (#2,#3). ✅
- Cosecha del conductor sin hooks/ARG_MAX: Global + 0.x/1.x (#2,#4,#6). ✅
- Adaptador+autoridad(`sender==assignee`)+`--subject`: 1.5 (#1). ✅
- Contención robusta + root canonicalizada: 1.2 (#5). ✅
- Dedup-FSM persistente received→harvested→promoted: 1.2/1.5 (#6). ✅
- Recuperación con interrupt/close (Orca no cancela): 1.5/2.2 (#7). ✅
- Disponibilidad = alcanzable desde el conductor; stale_bootstrap→CLI: 2.2 (#8). ✅
- Node externo + install + skills-ref reproducible: 1.1 (#9,#12). ✅
- acceptEdits solo aislado; `manual` no `default`: 1.4/5.1 (#10). ✅
- Matriz de raíces (incl. `.sdd/…` y standalone) + override en prompt delegado: Global/2.1/6.2 (#11). ✅
- Señal=wake-up + busy→idle + poll estabilizado: Global/0.2/1.3 (#15). ✅
- Locator contratado (CODEX_HOME/session-id) o CLI: 0.1 (#16). ✅
- Contenido ligado al dispatch (nonce+IDs): Global/0.2/1.2/1.3 (#17). ✅
- raw→promote para acumulativos (review-log): Global/4.2 (#18). ✅
- Privacidad: solo sesiones frescas del flujo: Global/2.2 (#19). ✅
- E2E parser>1MB separado de E2E max-output: 7.1 (#20). ✅
- POSIX/PowerShell dual + espera/backoff: Global/1.4/2.2 (#13,#14). ✅

Ronda 3 (9 hallazgos):
- Autoridad con flujo de datos real (`expectedAssignee` del dispatch vs `actualSender` del worker_done): Global/1.3/1.5 (r3 #1). ✅
- `createOwnedSession` + registro de sesión que conecta el locator: 1.5 (r3 #2). ✅
- FSM y raw→promote crash-idempotent (clave durable, hash, temp+rename): Global/1.2/1.3 (r3 #3). ✅
- Privacidad sin excepción (solo sesiones frescas propias): Global (r3 #4/#19). ✅
- Perfiles Codex como `$CODEX_HOME/<n>.config.toml` + `-p` + `--strict-config` + `codex mcp get`: 1.4 (r3 #5). ✅
- apps/plugins con overrides por ID + fallar cerrado: Global/1.4 (r3 #6). ✅
- Claude toolset cerrado (inmune a Bash heredado) + preflight de reglas efectivas: Global/1.4 (r3 #7). ✅
- `sdd-orchestrator` propaga solo `desired`; el delegado reevalúa `effective`: 6.1/6.2 (r3 #8). ✅
- Reconciliación del diseño (decisión superseding): 0.0 (r3 #9). ✅

Rondas 4–5 (cierres): validación de autoridad en el adaptador antes de cosechar (r4 #1); FSM idempotente post-rename por reconstrucción determinística (r4 #2); privacidad sin rama de consentimiento en el resolver (r4 #3); validación de perfiles Codex por `test -f`+`mcp list --json`+`mcp get` (r4 #4); **apps fail-closed con `features.apps=false`** (r5 #5, cierra el override per-app heredado); toolset cerrado sin preflight ficticio (r4 #6, `--tools` deja Bash fuera — verificado); registro/FSM en raíz conductor-only (r4 #7); nombres `codex-*.config.toml` unificados (r5 #8). Verificado contra Codex 0.144.6 / Claude 2.1.214.

> **Trazabilidad de la review cross-model:** el plan pasó **5 rondas** de crítica adversarial de la otra familia (Codex), aplicadas con criterio del conductor. Trayectoria de hallazgos: 14 → 20 → 9 → 8 → 2, con la severidad descendiendo de arquitectura (cosecha/hooks/ARG_MAX) a wiring y precisión de CLI. Al cierre no quedan bloqueantes ni importantes de fondo abiertos; los detalles finos de implementación (algoritmo exacto de reconstrucción idempotente, formato del rollout) quedan como criterios con test dentro de sus tasks y se **fijan con los contratos del spike de Fase 0**.

**Dependencias declaradas (no placeholders):** matcher de `parseTranscript`, locator y contrato de señal se fijan con **fixtures/observaciones reales de la Fase 0**; sin contrato inequívoco, la rama orca-session **degrada a CLI** (comportamiento seguro por default).
