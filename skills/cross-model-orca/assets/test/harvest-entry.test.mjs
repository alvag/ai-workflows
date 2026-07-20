// Tests de harvest-from-transcript.mjs: la función pura harvest() (poll
// estabilizado + desambiguación por nonce + contención + escritura exclusiva)
// y, end-to-end, el wrapper CLI lanzado como subproceso vía node:child_process.
// Cada test que usa el filesystem trabaja dentro de un directorio temporal
// propio (fs.mkdtempSync) para no dejar residuos ni interferir entre corridas.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { harvest } from '../harvest-from-transcript.mjs';

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const ASSETS_DIR = path.dirname(TEST_DIR);
const ENTRY_PATH = path.join(ASSETS_DIR, 'harvest-from-transcript.mjs');
const CODEX_FIXTURE = path.join(TEST_DIR, 'fixtures/codex-rollout.jsonl');
const CLAUDE_FIXTURE = path.join(TEST_DIR, 'fixtures/claude-transcript.jsonl');

function mkTmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

// ---------------------------------------------------------------------------
// harvest(): cosecha correcta
// ---------------------------------------------------------------------------

test('harvest: con NONCE-ACTUAL (codex) cosecha el informe actual sin el sentinel y lo persiste', async () => {
  const root = mkTmpDir('harvest-entry-root-');
  const result = await harvest({
    family: 'codex',
    transcriptPath: CODEX_FIXTURE,
    nonce: 'NONCE-ACTUAL',
    reportPath: 'informe.md',
    root,
    deadlineMs: 1000,
  });

  assert.equal(result.code, 0);
  assert.equal(result.reportPath, path.join(fs.realpathSync(root), 'informe.md'));

  const written = fs.readFileSync(result.reportPath, 'utf8');
  assert.match(written, /NONCE-ACTUAL/);
  assert.doesNotMatch(written, /ANTERIOR/);
  assert.notEqual(written.trimEnd().slice(-'STATUS: done'.length), 'STATUS: done');
});

test('harvest: con NONCE-ACTUAL (claude) cosecha el informe actual sin el sentinel y lo persiste', async () => {
  const root = mkTmpDir('harvest-entry-root-');
  const result = await harvest({
    family: 'claude',
    transcriptPath: CLAUDE_FIXTURE,
    nonce: 'NONCE-ACTUAL',
    reportPath: 'informe.md',
    root,
    deadlineMs: 1000,
  });

  assert.equal(result.code, 0);
  const written = fs.readFileSync(result.reportPath, 'utf8');
  assert.match(written, /NONCE-ACTUAL/);
  assert.doesNotMatch(written, /ANTERIOR/);
  assert.notEqual(written.trimEnd().slice(-'STATUS: done'.length), 'STATUS: done');
});

// ---------------------------------------------------------------------------
// harvest(): desambiguación por nonce
// ---------------------------------------------------------------------------

test('harvest: con NONCE-VIEJO cosecha el informe anterior, no el actual', async () => {
  const root = mkTmpDir('harvest-entry-root-');
  const result = await harvest({
    family: 'codex',
    transcriptPath: CODEX_FIXTURE,
    nonce: 'NONCE-VIEJO',
    reportPath: 'informe.md',
    root,
    deadlineMs: 1000,
  });

  assert.equal(result.code, 0);
  const written = fs.readFileSync(result.reportPath, 'utf8');
  assert.match(written, /ANTERIOR/);
  assert.match(written, /NONCE-VIEJO/);
});

// ---------------------------------------------------------------------------
// harvest(): contención
// ---------------------------------------------------------------------------

test('harvest: reportPath con ".." es rechazado por contención (code 2) y no escribe nada', async () => {
  const root = mkTmpDir('harvest-entry-root-');
  const result = await harvest({
    family: 'codex',
    transcriptPath: CODEX_FIXTURE,
    nonce: 'NONCE-ACTUAL',
    reportPath: '../escape.md',
    root,
    deadlineMs: 1000,
  });

  assert.equal(result.code, 2);
  assert.equal(typeof result.reason, 'string');
  assert.equal(fs.existsSync(path.join(path.dirname(root), 'escape.md')), false);
});

// ---------------------------------------------------------------------------
// harvest(): timeout
// ---------------------------------------------------------------------------

test('harvest: nonce inexistente agota el deadline y devuelve timeout (code 3)', async () => {
  const root = mkTmpDir('harvest-entry-root-');
  const result = await harvest({
    family: 'codex',
    transcriptPath: CODEX_FIXTURE,
    nonce: 'NONCE-NO-EXISTE',
    reportPath: 'informe.md',
    root,
    deadlineMs: 30,
  });

  assert.equal(result.code, 3);
  assert.equal(typeof result.reason, 'string');
  assert.equal(fs.existsSync(path.join(root, 'informe.md')), false);
});

test('harvest: respeta el reloj inyectado (now) en vez de depender del reloj real', async () => {
  const root = mkTmpDir('harvest-entry-root-');
  let calls = 0;
  // Reloj falso que ya arrancó vencido en la segunda lectura: fuerza el timeout
  // sin depender de que pase tiempo real.
  const now = () => {
    calls += 1;
    return calls === 1 ? 0 : 10_000;
  };

  const result = await harvest({
    family: 'codex',
    transcriptPath: CODEX_FIXTURE,
    nonce: 'NONCE-NO-EXISTE',
    reportPath: 'informe.md',
    root,
    deadlineMs: 5,
    now,
  });

  assert.equal(result.code, 3);
});

// ---------------------------------------------------------------------------
// End-to-end: CLI como subproceso
// ---------------------------------------------------------------------------

test('CLI end-to-end: cosecha vía subproceso y sale con code 0', () => {
  const root = mkTmpDir('harvest-entry-e2e-root-');
  const proc = spawnSync(process.execPath, [ENTRY_PATH], {
    env: {
      ...process.env,
      CMO_FAMILY: 'codex',
      CMO_TRANSCRIPT: CODEX_FIXTURE,
      CMO_NONCE: 'NONCE-ACTUAL',
      CMO_REPORT_PATH: 'e2e-informe.md',
      CMO_ROOT: root,
      CMO_DEADLINE_MS: '2000',
    },
    encoding: 'utf8',
  });

  assert.equal(proc.status, 0);
  const written = fs.readFileSync(path.join(fs.realpathSync(root), 'e2e-informe.md'), 'utf8');
  assert.match(written, /NONCE-ACTUAL/);
});

test('CLI end-to-end: variables de entorno faltantes salen con code distinto de 0 y no cuelgan', () => {
  const proc = spawnSync(
    process.execPath,
    [ENTRY_PATH],
    {
      env: {
        ...process.env,
        CMO_FAMILY: '',
        CMO_TRANSCRIPT: '',
        CMO_NONCE: '',
        CMO_REPORT_PATH: '',
        CMO_ROOT: '',
        CMO_DEADLINE_MS: '',
      },
      encoding: 'utf8',
    }
  );

  assert.notEqual(proc.status, 0);
  assert.notEqual(proc.status, null);
});
