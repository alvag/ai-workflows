// Tests end-to-end del CLI guardless `run-manifest.mjs`. Cada transición corre
// en un proceso Node separado, como lo hará el caller real.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const CLI_PATH = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'run-manifest.mjs');

function mkTmpDir(prefix = 'cmo-manifest-cli-') {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function runCli(args) {
  return spawnSync(process.execPath, [CLI_PATH, ...args], { encoding: 'utf8' });
}

function startCli(dir, extraArgs = []) {
  const result = runCli([
    'start',
    '--dir', dir,
    '--workflow', 'cross-implement',
    '--mode', 'implement',
    '--role', 'builder',
    '--family', 'claude',
    '--transport-desired', 'auto',
    ...extraArgs,
  ]);
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

function expectOk(args) {
  const result = runCli(args);
  assert.equal(result.status, 0, result.stderr);
  return result.stdout.trim() ? JSON.parse(result.stdout) : null;
}

test('start emite runId y partialPath por stdout', () => {
  const dir = mkTmpDir();
  const result = runCli([
    'start',
    '--dir', dir,
    '--workflow', 'cross-implement',
    '--mode', 'implement',
    '--role', 'builder',
    '--family', 'codex',
    '--transport-desired', 'auto',
  ]);

  assert.equal(result.status, 0, result.stderr);
  const output = JSON.parse(result.stdout);
  assert.match(output.runId, /^[a-z0-9-]{1,64}$/);
  assert.equal(output.partialPath, path.join(dir, `${output.runId}.partial.json`));
  assert.equal(fs.existsSync(output.partialPath), true);
});

test('flags requeridos ausentes y ext JSON inválido salen con error', () => {
  const missing = runCli(['start', '--dir', mkTmpDir()]);
  assert.notEqual(missing.status, 0);
  assert.match(missing.stderr, /faltan argumentos/i);

  const dir = mkTmpDir();
  const extPath = path.join(dir, 'ext.json');
  fs.writeFileSync(extPath, '{json roto');
  const invalidJson = runCli([
    'start',
    '--dir', dir,
    '--workflow', 'cross-implement',
    '--mode', 'implement',
    '--role', 'builder',
    '--family', 'codex',
    '--transport-desired', 'auto',
    '--ext-file', extPath,
  ]);
  assert.notEqual(invalidJson.status, 0);
  assert.match(invalidJson.stderr, /ext-file|json/i);
});

test('finish con attempt abierto falla y no crea terminal', () => {
  const dir = mkTmpDir();
  const { runId } = startCli(dir);
  expectOk([
    'attempt-start', '--dir', dir, '--run-id', runId,
    '--transport', 'cli', '--access', 'read-only',
  ]);

  const result = runCli(['finish', '--dir', dir, '--run-id', runId, '--status', 'failed']);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /attempt abierto/i);
  assert.equal(fs.existsSync(path.join(dir, `${runId}.json`)), false);
});

test('fallback completo vía CLI produce un único run.json ordenado', () => {
  const dir = mkTmpDir();
  const { runId } = startCli(dir);
  expectOk([
    'attempt-start', '--dir', dir, '--run-id', runId,
    '--transport', 'orca-session', '--access', 'write',
  ]);
  expectOk([
    'attempt-finish', '--dir', dir, '--run-id', runId,
    '--outcome', 'failed', '--code', '4', '--recovered', 'true',
  ]);
  expectOk([
    'attempt-start', '--dir', dir, '--run-id', runId,
    '--transport', 'cli', '--access', 'write',
  ]);
  expectOk([
    'attempt-finish', '--dir', dir, '--run-id', runId,
    '--outcome', 'completed', '--code', '0',
  ]);
  const finish = expectOk(['finish', '--dir', dir, '--run-id', runId, '--status', 'ready']);
  const terminal = JSON.parse(fs.readFileSync(finish.manifestPath, 'utf8'));

  assert.deepEqual(terminal.attempts.map((attempt) => attempt.transport), ['orca-session', 'cli']);
  assert.equal(terminal.transport.effective, 'cli');
  assert.equal(terminal.transport.fallbackUsed, true);
  assert.equal(terminal.outcome.status, 'ready');
  assert.equal(typeof terminal.timing.durationMs, 'number');
});

test('finish --ext-file sustituye los valores iniciales por métricas finales', () => {
  const dir = mkTmpDir();
  const { runId } = startCli(dir);
  expectOk([
    'attempt-start', '--dir', dir, '--run-id', runId,
    '--transport', 'cli', '--access', 'write',
  ]);
  expectOk([
    'attempt-finish', '--dir', dir, '--run-id', runId,
    '--outcome', 'completed', '--code', '0',
  ]);
  const ext = {
    'cross-implement': {
      fixRounds: 2,
      verificationReruns: 3,
      triage: [{
        checkId: 'contrato-final',
        class: 'IMPLEMENTATION_DEFECT',
        consumedRound: true,
      }],
    },
  };
  const extPath = path.join(dir, 'ext-final.json');
  fs.writeFileSync(extPath, JSON.stringify(ext));

  const finish = expectOk([
    'finish', '--dir', dir, '--run-id', runId, '--status', 'ready',
    '--ext-file', extPath,
  ]);
  const terminal = JSON.parse(fs.readFileSync(finish.manifestPath, 'utf8'));

  assert.deepEqual(terminal.ext, ext);
});

test('attempt-finish --code null persiste null y no string ni cero', () => {
  const dir = mkTmpDir();
  const { runId } = startCli(dir);
  expectOk([
    'attempt-start', '--dir', dir, '--run-id', runId,
    '--transport', 'cli', '--access', 'read-only',
  ]);
  expectOk([
    'attempt-finish', '--dir', dir, '--run-id', runId,
    '--outcome', 'failed', '--code', 'null',
  ]);
  const finish = expectOk(['finish', '--dir', dir, '--run-id', runId, '--status', 'failed']);
  const terminal = JSON.parse(fs.readFileSync(finish.manifestPath, 'utf8'));
  assert.equal(terminal.attempts[0].code, null);
  assert.equal(terminal.outcome.code, null);
});

test('resolve-writer vía CLI registra intervención, preserva recovered y valida slug', () => {
  const dir = mkTmpDir();
  const extPath = path.join(dir, 'ext.json');
  fs.writeFileSync(extPath, JSON.stringify({
    'cross-implement': {
      fixRounds: 1,
      verificationReruns: 2,
      triage: [{
        checkId: 'manifest-tests',
        class: 'IMPLEMENTATION_DEFECT',
        consumedRound: true,
      }],
    },
  }));
  const { runId } = startCli(dir, ['--ext-file', extPath]);
  expectOk([
    'attempt-start', '--dir', dir, '--run-id', runId,
    '--transport', 'orca-session', '--access', 'write',
  ]);
  expectOk([
    'attempt-finish', '--dir', dir, '--run-id', runId,
    '--outcome', 'unterminated', '--code', '3', '--recovered', 'false',
  ]);

  const blocked = runCli([
    'attempt-start', '--dir', dir, '--run-id', runId,
    '--transport', 'cli', '--access', 'write',
  ]);
  assert.notEqual(blocked.status, 0);
  assert.match(blocked.stderr, /escritor/i);
  const invalidResolution = runCli([
    'resolve-writer', '--dir', dir, '--run-id', runId,
    '--resolved-by', 'el usuario dijo que ok',
  ]);
  assert.notEqual(invalidResolution.status, 0);
  assert.match(invalidResolution.stderr, /resolvedBy/i);

  expectOk([
    'resolve-writer', '--dir', dir, '--run-id', runId, '--resolved-by', 'manual',
  ]);
  expectOk([
    'attempt-start', '--dir', dir, '--run-id', runId,
    '--transport', 'cli', '--access', 'write',
  ]);
  expectOk([
    'attempt-finish', '--dir', dir, '--run-id', runId,
    '--outcome', 'completed', '--code', '0',
  ]);
  const finish = expectOk(['finish', '--dir', dir, '--run-id', runId, '--status', 'ready']);
  const terminal = JSON.parse(fs.readFileSync(finish.manifestPath, 'utf8'));
  assert.equal(terminal.attempts[0].recovered, false);
  assert.equal(terminal.attempts[0].writerResolution.resolvedBy, 'manual');
  assert.equal(terminal.ext['cross-implement'].fixRounds, 1);
});

test('usage inválido falla y artifact válido usa sha256 de node:crypto', () => {
  const invalidDir = mkTmpDir();
  const invalidUsagePath = path.join(invalidDir, 'usage.json');
  fs.writeFileSync(invalidUsagePath, JSON.stringify({
    source: 'unavailable',
    inputTokens: 10,
    outputTokens: null,
    costUsd: null,
  }));
  const { runId: invalidRunId } = startCli(invalidDir);
  const invalid = runCli([
    'finish', '--dir', invalidDir, '--run-id', invalidRunId, '--status', 'aborted',
    '--usage-file', invalidUsagePath,
  ]);
  assert.notEqual(invalid.status, 0);
  assert.match(invalid.stderr, /unavailable.*null/i);

  const dir = mkTmpDir();
  const fixture = 'artifact fijo para digest';
  fs.writeFileSync(path.join(dir, 'result.md'), fixture);
  const artifactsPath = path.join(dir, 'artifacts.json');
  fs.writeFileSync(artifactsPath, JSON.stringify([{ kind: 'report', path: 'result.md' }]));
  const { runId } = startCli(dir);
  const finish = expectOk([
    'finish', '--dir', dir, '--run-id', runId, '--status', 'aborted',
    '--artifacts-file', artifactsPath,
  ]);
  const terminal = JSON.parse(fs.readFileSync(finish.manifestPath, 'utf8'));
  const expected = createHash('sha256').update(fixture).digest('hex');
  assert.equal(terminal.artifacts[0].sha256, expected);
});

test('artifact fuera de dir por .. o symlink falla vía CLI', () => {
  const outsideDir = mkTmpDir('cmo-manifest-cli-outside-');
  const outsidePath = path.join(outsideDir, 'fuga.md');
  fs.writeFileSync(outsidePath, 'fuera');

  const traversalDir = mkTmpDir();
  const traversalFile = path.join(traversalDir, 'artifacts.json');
  fs.writeFileSync(traversalFile, JSON.stringify([{
    kind: 'report',
    path: path.relative(traversalDir, outsidePath),
  }]));
  const { runId: traversalRunId } = startCli(traversalDir);
  const traversal = runCli([
    'finish', '--dir', traversalDir, '--run-id', traversalRunId, '--status', 'aborted',
    '--artifacts-file', traversalFile,
  ]);
  assert.notEqual(traversal.status, 0);
  assert.match(traversal.stderr, /escapa/i);

  const symlinkDir = mkTmpDir();
  fs.symlinkSync(outsidePath, path.join(symlinkDir, 'enlace.md'));
  const symlinkFile = path.join(symlinkDir, 'artifacts.json');
  fs.writeFileSync(symlinkFile, JSON.stringify([{ kind: 'report', path: 'enlace.md' }]));
  const { runId: symlinkRunId } = startCli(symlinkDir);
  const symlink = runCli([
    'finish', '--dir', symlinkDir, '--run-id', symlinkRunId, '--status', 'aborted',
    '--artifacts-file', symlinkFile,
  ]);
  assert.notEqual(symlink.status, 0);
  assert.match(symlink.stderr, /escapa/i);
});
