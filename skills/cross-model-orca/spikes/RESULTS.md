# Spikes de Fase 0 — bitácora de resultados

> Bitácora **fechada** de los spikes que fijan los contratos del transporte `orca-session`.
> Regla transversal: **sin un contrato inequívoco, la rama `orca-session` degrada a `cli`.**
> Plan: `docs/superpowers/plans/2026-07-18-cross-model-orca-transport.md`.

Entorno de referencia (registrar el real en cada corrida): Codex CLI 0.144.6 · Claude Code 2.1.214 ·
Orca 1.4.137 · `CODEX_HOME` = `~/Library/Application Support/orca/codex-runtime-home/home` (runtime de
Orca, **no** `~/.codex`).

---

## Task 0.1 — Contrato de locator de transcript/rollout

Estado: **pendiente**.

- Claude: path del transcript por `--session-id` fijo bajo `CLAUDE_CONFIG_DIR` efectivo → _(a completar)_
- Codex: captura del `thread/session-id` + path del rollout bajo `CODEX_HOME` → _(a completar)_
- Contrato / fallback: _(a completar)_
- Fixtures capturados: _(a completar)_

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
