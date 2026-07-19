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

Estado: **pendiente**.

- Orden señal `worker_done` vs mensaje final en el transcript → _(a completar)_
- `terminal wait --for tui-idle` como transición busy→idle posterior al dispatch → _(a completar)_
- `nonce` en el envelope para desambiguar sesión reutilizada → _(a completar)_

## Task 0.3 — Señal por comando (solo Codex) con hooks apagados

Estado: **pendiente**.

- Codex read-only `--disable hooks -s read-only -a untrusted` emite `worker_done` por comando → _(a completar)_
- Claude read-only toolset cerrado (`--tools "Read,Grep,Glob"`) no señaliza → fin por `tui-idle` → _(a completar)_
- Mecanismo por familia/modo: _(a completar)_
