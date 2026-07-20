// Tests del runner `run-orca-session.mjs`: la lógica de orquestación y degradación
// PROPIA del runner (createOwnedSession → createDispatch → awaitDone encadenados).
// El camino feliz (cosecha por nonce de un transcript real) ya está cubierto por los
// tests de cada función del adaptador y por el E2E en vivo; acá se testean las ramas
// de degradación a `cli`, que son la lógica que agrega el runner. Todo con un
// `orcaRunner` falso: nunca se lanza el binário `orca` real.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { runOrcaSession } from '../run-orca-session.mjs';

function mkTmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

// Envelope real de `orca --json`: `{ id, ok, result | error, _meta }`.
function okEnvelope(result) {
  return { stdout: JSON.stringify({ id: 'x', ok: true, result, _meta: {} }), code: 0 };
}
function errEnvelope(code) {
  return { stdout: JSON.stringify({ id: 'x', ok: false, error: { code }, _meta: {} }), code: 0 };
}

test('degrada a cli (code 4) cuando no se puede crear la sesión propia', async () => {
  const stateDir = mkTmpDir('cmo-run-nosess-');
  const root = mkTmpDir('cmo-run-root-');
  // terminal create devuelve ok:false → createOwnedSession no obtiene handle → null.
  const calls = [];
  const orcaRunner = (args) => {
    calls.push(args[0] + ' ' + args[1]);
    return errEnvelope('selector_not_found');
  };

  const res = await runOrcaSession({
    family: 'codex',
    role: 'read-only',
    mode: 'unattended',
    worktree: '/tmp/no-such-worktree',
    spec: 'tarea',
    reportPath: 'findings-codex.md',
    root,
    orcaRunner,
    stateDir,
  });

  assert.equal(res.transport, 'orca-session');
  assert.equal(res.code, 4);
  assert.match(res.reason, /sesión Orca propia/i);
  // No se llegó a task-create: se cortó en la creación de la terminal.
  assert.ok(calls.includes('terminal create'));
  assert.ok(!calls.some((c) => c.startsWith('orchestration task-create')));
});

test('degrada a cli (code 4) y recupera cuando createDispatch falla en el boot-wait', async () => {
  const stateDir = mkTmpDir('cmo-run-boot-');
  const root = mkTmpDir('cmo-run-root2-');
  const calls = [];
  const orcaRunner = (args) => {
    const verb = `${args[0]} ${args[1]}`;
    calls.push(verb);
    if (verb === 'terminal create') return okEnvelope({ terminal: { handle: 'term-1' } });
    if (verb === 'orchestration task-create') return okEnvelope({ task: { id: 'task_1' } });
    if (verb === 'terminal wait') return errEnvelope('timeout'); // nunca llega a tui-idle
    // recover: interrupt + wait idle (best-effort).
    if (verb === 'terminal send') return okEnvelope({});
    return okEnvelope({});
  };

  const res = await runOrcaSession({
    family: 'claude',
    role: 'read-only',
    mode: 'unattended',
    worktree: '/tmp/wt',
    spec: 'tarea',
    reportPath: 'findings-claude.md',
    root,
    orcaRunner,
    stateDir,
  });

  assert.equal(res.code, 4);
  assert.match(res.reason, /no se pudo despachar/i);
  // El dispatch --inject NUNCA se emitió (se abortó en el boot-wait).
  assert.ok(!calls.some((c) => c === 'orchestration dispatch'));
  // Se intentó recuperar la sesión (interrupt) antes de degradar.
  assert.ok(calls.includes('terminal send'));
});
