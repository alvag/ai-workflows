// Tests golden del manifest caller-owned. Usan filesystem real bajo os.tmpdir()
// y un reloj inyectado para que timestamps y duraciones sean deterministas.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import {
  attemptFinish,
  attemptStart,
  createRun,
  finishRun,
  readRun,
  resolveWriter,
} from '../manifest-core.mjs';

const DEFAULT_EXT = {
  'cross-implement': {
    fixRounds: 0,
    verificationReruns: 0,
    triage: [],
  },
};

function mkTmpDir(prefix = 'cmo-manifest-core-') {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function tickingClock(start = Date.parse('2026-07-22T12:00:00.000Z'), step = 1_000) {
  let current = start;
  return () => {
    const value = current;
    current += step;
    return value;
  };
}

function startRun(dir, overrides = {}) {
  return createRun({
    dir,
    workflow: 'cross-implement',
    mode: 'implement',
    role: 'builder',
    family: 'claude',
    transportDesired: 'auto',
    ext: DEFAULT_EXT,
    now: tickingClock(),
    ...overrides,
  });
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

test('createRun crea un partial mínimo sin campos terminales y con usage honesto', () => {
  const dir = mkTmpDir();
  const now = tickingClock();
  const { runId, partialPath } = startRun(dir, { now });
  const partial = readJson(partialPath);

  assert.match(runId, /^[a-z0-9-]{1,64}$/);
  assert.equal(partial.schemaVersion, 1);
  assert.equal(partial.runId, runId);
  assert.deepEqual(
    {
      workflow: partial.workflow,
      mode: partial.mode,
      role: partial.role,
      family: partial.family,
      model: partial.model,
    },
    {
      workflow: 'cross-implement',
      mode: 'implement',
      role: 'builder',
      family: 'claude',
      model: null,
    },
  );
  assert.deepEqual(partial.transport, { desired: 'auto' });
  assert.deepEqual(partial.attempts, []);
  assert.deepEqual(partial.timing, { startedAt: '2026-07-22T12:00:00.000Z' });
  assert.deepEqual(partial.usage, {
    inputTokens: null,
    outputTokens: null,
    costUsd: null,
    source: 'unavailable',
  });
  assert.deepEqual(partial.ext, DEFAULT_EXT);
  assert.equal(Object.hasOwn(partial, 'outcome'), false);
  assert.equal(Object.hasOwn(partial.transport, 'effective'), false);
  assert.equal(Object.hasOwn(partial.timing, 'finishedAt'), false);
  assert.equal(fs.readdirSync(dir).some((name) => name.endsWith('.tmp')), false);
});

test('attemptStart exige secuencia serial y attemptFinish conserva code null', () => {
  const dir = mkTmpDir();
  const now = tickingClock();
  const { runId } = startRun(dir, { now });

  attemptStart({ dir, runId, transport: 'orca-session', access: 'read-only', now });
  assert.throws(
    () => attemptStart({ dir, runId, transport: 'cli', access: 'read-only', now }),
    /attempt abierto/i,
  );
  attemptFinish({ dir, runId, outcome: 'failed', code: null, now });

  const partial = readRun({ dir, runId }).data;
  assert.equal(partial.attempts[0].code, null);
  assert.equal(partial.attempts[0].outcome, 'failed');
});

test('resolveWriter desbloquea el fallback sin mutar recovered false', () => {
  const dir = mkTmpDir();
  const now = tickingClock();
  const { runId } = startRun(dir, { now, role: 'builder' });

  attemptStart({ dir, runId, transport: 'orca-session', access: 'write', now });
  attemptFinish({ dir, runId, outcome: 'unterminated', code: 3, recovered: false, now });
  assert.throws(
    () => attemptStart({ dir, runId, transport: 'cli', access: 'write', now }),
    /escritor/i,
  );
  resolveWriter({ dir, runId, resolvedBy: 'manual', now });
  attemptStart({ dir, runId, transport: 'cli', access: 'write', now });

  const firstAttempt = readRun({ dir, runId }).data.attempts[0];
  assert.equal(firstAttempt.access, 'write');
  assert.equal(firstAttempt.recovered, false);
  assert.deepEqual(firstAttempt.writerResolution, {
    resolvedBy: 'manual',
    resolvedAt: '2026-07-22T12:00:03.000Z',
  });
});

test('la FSM rechaza éxito seguido de otro attempt y cli hacia orca-session', () => {
  const completedDir = mkTmpDir();
  const completedClock = tickingClock();
  const { runId: completedRunId } = startRun(completedDir, { now: completedClock });
  attemptStart({
    dir: completedDir,
    runId: completedRunId,
    transport: 'cli',
    access: 'read-only',
    now: completedClock,
  });
  attemptFinish({
    dir: completedDir,
    runId: completedRunId,
    outcome: 'completed',
    code: 0,
    now: completedClock,
  });
  assert.throws(
    () => attemptStart({
      dir: completedDir,
      runId: completedRunId,
      transport: 'cli',
      access: 'read-only',
      now: completedClock,
    }),
    /completed/i,
  );

  const sequenceDir = mkTmpDir();
  const sequenceClock = tickingClock();
  const { runId: sequenceRunId } = startRun(sequenceDir, { now: sequenceClock });
  attemptStart({
    dir: sequenceDir,
    runId: sequenceRunId,
    transport: 'cli',
    access: 'read-only',
    now: sequenceClock,
  });
  attemptFinish({
    dir: sequenceDir,
    runId: sequenceRunId,
    outcome: 'failed',
    code: 1,
    now: sequenceClock,
  });
  assert.throws(
    () => attemptStart({
      dir: sequenceDir,
      runId: sequenceRunId,
      transport: 'orca-session',
      access: 'read-only',
      now: sequenceClock,
    }),
    /cli.*orca-session/i,
  );
  assert.doesNotThrow(() => attemptStart({
    dir: sequenceDir,
    runId: sequenceRunId,
    transport: 'cli',
    access: 'read-only',
    now: sequenceClock,
  }));
});

test('los guards de escritor distinguen recovered ausente de recovered false', () => {
  const blockedDir = mkTmpDir();
  const blockedClock = tickingClock();
  const { runId: blockedRunId } = startRun(blockedDir, { now: blockedClock });
  attemptStart({
    dir: blockedDir,
    runId: blockedRunId,
    transport: 'orca-session',
    access: 'write',
    now: blockedClock,
  });
  attemptFinish({
    dir: blockedDir,
    runId: blockedRunId,
    outcome: 'failed',
    code: 2,
    recovered: false,
    now: blockedClock,
  });
  assert.throws(
    () => attemptStart({
      dir: blockedDir,
      runId: blockedRunId,
      transport: 'cli',
      access: 'write',
      now: blockedClock,
    }),
    /escritor/i,
  );

  const explicitDir = mkTmpDir();
  const explicitClock = tickingClock();
  const { runId: explicitRunId } = startRun(explicitDir, { now: explicitClock });
  attemptStart({
    dir: explicitDir,
    runId: explicitRunId,
    transport: 'orca-session',
    access: 'write',
    now: explicitClock,
  });
  assert.throws(
    () => attemptFinish({
      dir: explicitDir,
      runId: explicitRunId,
      outcome: 'unterminated',
      code: null,
      now: explicitClock,
    }),
    /recovered.*explícito/i,
  );

  const absentDir = mkTmpDir();
  const absentClock = tickingClock();
  const { runId: absentRunId } = startRun(absentDir, { now: absentClock });
  attemptStart({
    dir: absentDir,
    runId: absentRunId,
    transport: 'orca-session',
    access: 'write',
    now: absentClock,
  });
  attemptFinish({
    dir: absentDir,
    runId: absentRunId,
    outcome: 'failed',
    code: 4,
    now: absentClock,
  });
  assert.doesNotThrow(() => attemptStart({
    dir: absentDir,
    runId: absentRunId,
    transport: 'cli',
    access: 'write',
    now: absentClock,
  }));
});

test('ext y resolvedBy rechazan contenido libre o schemas no registrados', () => {
  const dir = mkTmpDir();

  assert.throws(
    () => startRun(dir, { ext: { 'cross-implement': { prompt: 'texto' } } }),
    /ext\.cross-implement/i,
  );
  assert.throws(
    () => createRun({
      dir,
      workflow: 'cross-review',
      mode: 'review',
      role: 'reviewer',
      family: 'codex',
      transportDesired: 'auto',
      ext: { 'cross-review': {} },
    }),
    /workflow.*registrado/i,
  );
  assert.throws(
    () => startRun(dir, {
      ext: {
        'cross-implement': {
          fixRounds: 0,
          verificationReruns: 0,
          triage: [{
            checkId: 'ID con espacios',
            class: 'IMPLEMENTATION_DEFECT',
            consumedRound: true,
          }],
        },
      },
    }),
    /checkId/i,
  );

  const validDir = mkTmpDir();
  const now = tickingClock();
  const { runId } = startRun(validDir, { now });
  attemptStart({ dir: validDir, runId, transport: 'orca-session', access: 'write', now });
  attemptFinish({
    dir: validDir,
    runId,
    outcome: 'failed',
    code: 3,
    recovered: false,
    now,
  });
  assert.throws(
    () => resolveWriter({ dir: validDir, runId, resolvedBy: 'el usuario dijo que ok', now }),
    /resolvedBy/i,
  );
});

test('finishRun sustituye por completo el ext inicial con los valores finales', () => {
  const dir = mkTmpDir();
  const { runId } = startRun(dir);
  const finalExt = {
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

  const terminal = readJson(finishRun({
    dir,
    runId,
    status: 'aborted',
    ext: finalExt,
  }).manifestPath);

  assert.deepEqual(terminal.ext, finalExt);
  assert.notDeepEqual(terminal.ext, DEFAULT_EXT);
});

test('finishRun rechaza ext final inválido sin publicar el terminal', () => {
  const invalidExts = [
    {
      'cross-implement': {
        fixRounds: 0,
        verificationReruns: 0,
        triage: [],
        extra: true,
      },
    },
    {
      'cross-implement': {
        fixRounds: 0,
        verificationReruns: 0,
        triage: [{
          checkId: 'contrato',
          class: 'OTRA_CLASE',
          consumedRound: false,
        }],
      },
    },
    {
      'cross-implement': {
        fixRounds: 0,
        verificationReruns: 0,
        triage: [{
          checkId: 'ID con espacios',
          class: 'VERIFICATION_DEFECT',
          consumedRound: false,
        }],
      },
    },
  ];

  for (const ext of invalidExts) {
    const dir = mkTmpDir();
    const { runId, partialPath } = startRun(dir);
    const manifestPath = path.join(dir, `${runId}.json`);

    assert.throws(
      () => finishRun({ dir, runId, status: 'aborted', ext }),
      /ext\.cross-implement|checkId/i,
    );
    assert.equal(fs.existsSync(manifestPath), false);
    assert.equal(fs.existsSync(partialPath), true);
  }
});

test('finishRun repetido ignora un ext distinto y no muta el terminal', () => {
  const dir = mkTmpDir();
  const { runId } = startRun(dir);
  const { manifestPath } = finishRun({
    dir,
    runId,
    status: 'aborted',
    ext: {
      'cross-implement': {
        fixRounds: 1,
        verificationReruns: 1,
        triage: [],
      },
    },
  });
  const original = fs.readFileSync(manifestPath);

  finishRun({
    dir,
    runId,
    status: 'ready',
    ext: {
      'cross-implement': {
        fixRounds: 99,
        verificationReruns: 99,
        triage: [],
      },
    },
  });

  assert.deepEqual(fs.readFileSync(manifestPath), original);
});

test('finishRun rechaza attempts abiertos y cierra explícitamente uno fallido', () => {
  const openDir = mkTmpDir();
  const openClock = tickingClock();
  const { runId: openRunId } = startRun(openDir, { now: openClock });
  attemptStart({
    dir: openDir,
    runId: openRunId,
    transport: 'cli',
    access: 'read-only',
    now: openClock,
  });
  assert.throws(
    () => finishRun({ dir: openDir, runId: openRunId, status: 'failed', now: openClock }),
    /attempt abierto/i,
  );
  assert.equal(fs.existsSync(path.join(openDir, `${openRunId}.json`)), false);
  const stillPartial = readJson(path.join(openDir, `${openRunId}.partial.json`));
  assert.equal(Object.hasOwn(stillPartial, 'outcome'), false);

  const failedDir = mkTmpDir();
  const failedClock = tickingClock();
  const { runId: failedRunId } = startRun(failedDir, { now: failedClock });
  attemptStart({
    dir: failedDir,
    runId: failedRunId,
    transport: 'orca-session',
    access: 'read-only',
    now: failedClock,
  });
  attemptFinish({
    dir: failedDir,
    runId: failedRunId,
    outcome: 'failed',
    code: 4,
    now: failedClock,
  });
  const { manifestPath } = finishRun({
    dir: failedDir,
    runId: failedRunId,
    status: 'failed',
    now: failedClock,
  });
  const terminal = readJson(manifestPath);
  assert.equal(terminal.attempts[0].outcome, 'failed');
  assert.deepEqual(terminal.outcome, { status: 'failed', code: 4 });
  assert.equal(fs.existsSync(path.join(failedDir, `${failedRunId}.partial.json`)), false);
});

test('finishRun bloquea un escritor no recuperado y conserva su resolución terminal', () => {
  const dir = mkTmpDir();
  const now = tickingClock();
  const { runId } = startRun(dir, { now });
  attemptStart({ dir, runId, transport: 'orca-session', access: 'write', now });
  attemptFinish({ dir, runId, outcome: 'unterminated', code: 3, recovered: false, now });

  assert.throws(
    () => finishRun({ dir, runId, status: 'aborted', now }),
    /escritor/i,
  );
  resolveWriter({ dir, runId, resolvedBy: 'manual', now });
  const { manifestPath } = finishRun({ dir, runId, status: 'aborted', now });
  const attempt = readJson(manifestPath).attempts[0];
  assert.equal(attempt.recovered, false);
  assert.equal(attempt.writerResolution.resolvedBy, 'manual');
});

test('readRun trata partial como incomplete y da precedencia al terminal', () => {
  const dir = mkTmpDir();
  const now = tickingClock();
  const { runId, partialPath } = startRun(dir, { now });
  const abandoned = readRun({ dir, runId });
  assert.equal(abandoned.state, 'incomplete');
  assert.equal(Object.hasOwn(abandoned.data, 'outcome'), false);

  const partialBytes = fs.readFileSync(partialPath);
  const { manifestPath } = finishRun({ dir, runId, status: 'aborted', now });
  const terminalBytes = fs.readFileSync(manifestPath);
  fs.writeFileSync(partialPath, partialBytes);

  assert.equal(readRun({ dir, runId }).state, 'terminal');
  finishRun({ dir, runId, status: 'ready', now });
  assert.deepEqual(fs.readFileSync(manifestPath), terminalBytes);
  assert.equal(fs.existsSync(partialPath), false);
});

test('un terminal es inmutable para todas las operaciones salvo finish limpiador', () => {
  const dir = mkTmpDir();
  const now = tickingClock();
  const { runId } = startRun(dir, { now });
  finishRun({ dir, runId, status: 'aborted', now });

  assert.throws(
    () => attemptStart({ dir, runId, transport: 'cli', access: 'read-only', now }),
    /terminal.*inmutable/i,
  );
  assert.throws(
    () => attemptFinish({ dir, runId, outcome: 'failed', code: null, now }),
    /terminal.*inmutable/i,
  );
  assert.throws(
    () => resolveWriter({ dir, runId, resolvedBy: 'manual', now }),
    /terminal.*inmutable/i,
  );
});

test('golden fallback orca-session hacia cli deriva transporte, duración y outcome', () => {
  const dir = mkTmpDir();
  const now = tickingClock();
  const { runId } = startRun(dir, { now, role: 'builder' });
  attemptStart({ dir, runId, transport: 'orca-session', access: 'write', now });
  attemptFinish({ dir, runId, outcome: 'failed', code: 4, recovered: true, now });
  attemptStart({ dir, runId, transport: 'cli', access: 'write', now });
  attemptFinish({ dir, runId, outcome: 'completed', code: 0, now });

  const { manifestPath } = finishRun({ dir, runId, status: 'ready', now });
  const terminal = readJson(manifestPath);
  assert.equal(terminal.attempts.length, 2);
  assert.deepEqual(terminal.attempts.map((attempt) => attempt.transport), ['orca-session', 'cli']);
  assert.deepEqual(terminal.transport, {
    desired: 'auto',
    effective: 'cli',
    fallbackUsed: true,
  });
  assert.equal(terminal.timing.durationMs, 5_000);
  assert.deepEqual(terminal.outcome, { status: 'ready', code: 0 });
  assert.deepEqual(terminal.usage, {
    inputTokens: null,
    outputTokens: null,
    costUsd: null,
    source: 'unavailable',
  });
});

test('instrumentación: fix tras CLI conserva un único attempt y persiste métricas finales', () => {
  const dir = mkTmpDir();
  const now = tickingClock();
  const { runId } = startRun(dir, { now, transportDesired: 'cli' });
  attemptStart({ dir, runId, transport: 'cli', access: 'write', now });
  attemptFinish({ dir, runId, outcome: 'completed', code: 0, now });
  const ext = {
    'cross-implement': {
      fixRounds: 2,
      verificationReruns: 3,
      triage: [
        {
          checkId: 'compilacion',
          class: 'IMPLEMENTATION_DEFECT',
          consumedRound: true,
        },
        {
          checkId: 'pruebas',
          class: 'IMPLEMENTATION_DEFECT',
          consumedRound: true,
        },
      ],
    },
  };

  const terminal = readJson(finishRun({ dir, runId, status: 'ready', ext, now }).manifestPath);
  assert.equal(terminal.attempts.length, 1);
  assert.equal(terminal.attempts[0].transport, 'cli');
  assert.deepEqual(terminal.ext, ext);
});

test('instrumentación: fix tras Orca conserva un único attempt y persiste métricas finales', () => {
  const dir = mkTmpDir();
  const now = tickingClock();
  const { runId } = startRun(dir, { now, transportDesired: 'orca-session' });
  attemptStart({ dir, runId, transport: 'orca-session', access: 'write', now });
  attemptFinish({ dir, runId, outcome: 'completed', code: 0, now });
  const ext = {
    'cross-implement': {
      fixRounds: 1,
      verificationReruns: 1,
      triage: [{
        checkId: 'lint',
        class: 'IMPLEMENTATION_DEFECT',
        consumedRound: true,
      }],
    },
  };

  const terminal = readJson(finishRun({ dir, runId, status: 'ready', ext, now }).manifestPath);
  assert.equal(terminal.attempts.length, 1);
  assert.equal(terminal.attempts[0].transport, 'orca-session');
  assert.equal(Object.hasOwn(terminal.attempts[0], 'recovered'), false);
  assert.deepEqual(terminal.ext, ext);
});

test('instrumentación: fallback seguido de fix usa dos attempts y triage mixto', () => {
  const dir = mkTmpDir();
  const now = tickingClock();
  const { runId } = startRun(dir, { now });
  attemptStart({ dir, runId, transport: 'orca-session', access: 'write', now });
  attemptFinish({ dir, runId, outcome: 'failed', code: 4, recovered: true, now });
  attemptStart({ dir, runId, transport: 'cli', access: 'write', now });
  attemptFinish({ dir, runId, outcome: 'completed', code: 0, now });
  const ext = {
    'cross-implement': {
      fixRounds: 1,
      verificationReruns: 2,
      triage: [
        {
          checkId: 'pruebas',
          class: 'VERIFICATION_DEFECT',
          consumedRound: false,
        },
        {
          checkId: 'compilacion',
          class: 'IMPLEMENTATION_DEFECT',
          consumedRound: true,
        },
      ],
    },
  };

  const terminal = readJson(finishRun({ dir, runId, status: 'ready', ext, now }).manifestPath);
  assert.equal(terminal.attempts.length, 2);
  assert.deepEqual(terminal.attempts.map((attempt) => attempt.transport), ['orca-session', 'cli']);
  assert.equal(terminal.transport.fallbackUsed, true);
  assert.equal(terminal.transport.effective, 'cli');
  assert.deepEqual(terminal.ext, ext);
});

test('la tabla de cierre cubre éxito directo, fallos, aborto y cero attempts', () => {
  const directDir = mkTmpDir();
  const directClock = tickingClock();
  const { runId: directRunId } = startRun(directDir, { now: directClock });
  attemptStart({
    dir: directDir,
    runId: directRunId,
    transport: 'orca-session',
    access: 'read-only',
    now: directClock,
  });
  attemptFinish({
    dir: directDir,
    runId: directRunId,
    outcome: 'completed',
    code: 0,
    now: directClock,
  });
  const direct = readJson(finishRun({
    dir: directDir,
    runId: directRunId,
    status: 'ready',
    now: directClock,
  }).manifestPath);
  assert.equal(direct.transport.effective, 'orca-session');
  assert.equal(direct.transport.fallbackUsed, false);

  const abortedDir = mkTmpDir();
  const abortedClock = tickingClock();
  const { runId: abortedRunId } = startRun(abortedDir, { now: abortedClock });
  const aborted = readJson(finishRun({
    dir: abortedDir,
    runId: abortedRunId,
    status: 'aborted',
    now: abortedClock,
  }).manifestPath);
  assert.equal(aborted.transport.effective, null);
  assert.equal(aborted.transport.fallbackUsed, false);
  assert.deepEqual(aborted.outcome, { status: 'aborted', code: null });

  const invalidDir = mkTmpDir();
  const { runId: invalidRunId } = startRun(invalidDir);
  assert.throws(
    () => finishRun({ dir: invalidDir, runId: invalidRunId, status: 'ready' }),
    /cero attempts.*aborted|ready.*completed/i,
  );
  assert.throws(
    () => finishRun({ dir: invalidDir, runId: invalidRunId, status: 'failed' }),
    /cero attempts.*aborted/i,
  );
});

test('un retry cli hacia cli no falsea fallbackUsed', () => {
  const dir = mkTmpDir();
  const now = tickingClock();
  const { runId } = startRun(dir, { now, transportDesired: 'cli' });
  attemptStart({ dir, runId, transport: 'cli', access: 'read-only', now });
  attemptFinish({ dir, runId, outcome: 'failed', code: 1, now });
  attemptStart({ dir, runId, transport: 'cli', access: 'read-only', now });
  attemptFinish({ dir, runId, outcome: 'completed', code: 0, now });

  const terminal = readJson(finishRun({ dir, runId, status: 'ready', now }).manifestPath);
  assert.equal(terminal.transport.effective, 'cli');
  assert.equal(terminal.transport.fallbackUsed, false);
});

test('usage rechaza estimaciones y persiste únicamente datos provider válidos', () => {
  const unavailableDir = mkTmpDir();
  const { runId: unavailableRunId } = startRun(unavailableDir);
  assert.throws(
    () => finishRun({
      dir: unavailableDir,
      runId: unavailableRunId,
      status: 'aborted',
      usage: {
        source: 'unavailable',
        inputTokens: 500,
        outputTokens: null,
        costUsd: null,
      },
    }),
    /unavailable.*null/i,
  );
  assert.throws(
    () => finishRun({
      dir: unavailableDir,
      runId: unavailableRunId,
      status: 'aborted',
      usage: {
        source: 'estimated',
        inputTokens: 500,
        outputTokens: 100,
        costUsd: 1,
      },
    }),
    /usage\.source/i,
  );

  const providerDir = mkTmpDir();
  const { runId: providerRunId } = startRun(providerDir);
  const terminal = readJson(finishRun({
    dir: providerDir,
    runId: providerRunId,
    status: 'aborted',
    usage: {
      source: 'provider',
      inputTokens: 500,
      outputTokens: 100,
      costUsd: 0.25,
    },
  }).manifestPath);
  assert.deepEqual(terminal.usage, {
    source: 'provider',
    inputTokens: 500,
    outputTokens: 100,
    costUsd: 0.25,
  });
});

test('artifacts guarda path y sha256, nunca el contenido', () => {
  const dir = mkTmpDir();
  const artifactPath = path.join(dir, 'result.md');
  const content = 'contenido sensible del informe';
  fs.writeFileSync(artifactPath, content);
  const expectedDigest = createHash('sha256').update(content).digest('hex');
  const { runId } = startRun(dir);

  const { manifestPath } = finishRun({
    dir,
    runId,
    status: 'aborted',
    artifacts: [{ kind: 'report', path: 'result.md' }],
  });
  const terminalText = fs.readFileSync(manifestPath, 'utf8');
  const terminal = JSON.parse(terminalText);
  assert.deepEqual(terminal.artifacts, [{
    kind: 'report',
    path: 'result.md',
    sha256: expectedDigest,
  }]);
  assert.equal(terminalText.includes(content), false);
});

test('artifacts exige archivo existente contenido por realpath dentro de dir', () => {
  const dir = mkTmpDir();
  const outsideDir = mkTmpDir('cmo-manifest-outside-');
  const outsidePath = path.join(outsideDir, 'fuga.md');
  fs.writeFileSync(outsidePath, 'fuera');

  const absoluteRun = startRun(dir).runId;
  assert.throws(
    () => finishRun({
      dir,
      runId: absoluteRun,
      status: 'aborted',
      artifacts: [{ kind: 'report', path: outsidePath }],
    }),
    /absoluta|escapa/i,
  );

  const traversalRun = startRun(dir).runId;
  const relativeEscape = path.relative(dir, outsidePath);
  assert.match(relativeEscape, /^\.\./);
  assert.throws(
    () => finishRun({
      dir,
      runId: traversalRun,
      status: 'aborted',
      artifacts: [{ kind: 'report', path: relativeEscape }],
    }),
    /escapa/i,
  );

  const symlinkPath = path.join(dir, 'enlace.md');
  fs.symlinkSync(outsidePath, symlinkPath);
  const symlinkRun = startRun(dir).runId;
  assert.throws(
    () => finishRun({
      dir,
      runId: symlinkRun,
      status: 'aborted',
      artifacts: [{ kind: 'report', path: 'enlace.md' }],
    }),
    /escapa/i,
  );
});
