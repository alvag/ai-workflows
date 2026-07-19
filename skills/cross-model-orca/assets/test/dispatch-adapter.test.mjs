// Tests de dispatch-adapter.mjs: orquestador del lado del conductor
// (createOwnedSession, createDispatch, awaitDone, recover). Todos los tests
// inyectan un `orcaRunner` falso (nunca lanzan el binario `orca` real) y, donde
// aplica, un reloj (`now`) y un `sleep` falsos para no depender de tiempo real.
// Esto no es mockear el sistema bajo test: es inyectar la dependencia de
// proceso externo que el módulo declara explícitamente como inyectable.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  createOwnedSession,
  createDispatch,
  awaitDone,
  recover,
  buildLaunchCommand,
  locateCodexRollout,
  resolveCodexTranscript,
} from '../dispatch-adapter.mjs';
import { makeDedupFsm } from '../harvest-core.mjs';

const TEST_DIR = path.dirname(new URL(import.meta.url).pathname);
const ASSETS_DIR = path.dirname(TEST_DIR);
const CODEX_FIXTURE = path.join(TEST_DIR, 'fixtures/codex-rollout.jsonl');

function mkTmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

// async-aware: espera el resultado de `fn` (sync o async) antes de restaurar el entorno, para
// no filtrar las variables mientras un `fn` async todavía está corriendo.
async function withEnv(vars, fn) {
  const originals = {};
  for (const key of Object.keys(vars)) originals[key] = process.env[key];
  Object.assign(process.env, vars);
  try {
    return await fn();
  } finally {
    for (const key of Object.keys(vars)) {
      if (originals[key] === undefined) delete process.env[key];
      else process.env[key] = originals[key];
    }
  }
}

function instantSleep() {
  return Promise.resolve();
}

// ---------------------------------------------------------------------------
// buildLaunchCommand: construcción del comando por family+role+mode
// ---------------------------------------------------------------------------

test('buildLaunchCommand (claude, read-only, POSIX): tools cerrado, sin permission-mode, session-id fijado', () => {
  const cmd = buildLaunchCommand({
    family: 'claude',
    role: 'read-only',
    mode: 'attended',
    sessionId: 'uuid-123',
    installRoot: '/inst',
    windows: false,
  });
  assert.match(cmd, /^DISABLE_AUTOUPDATER=1 claude /);
  assert.match(cmd, /--tools "Read,Grep,Glob"/);
  assert.match(cmd, /--session-id "uuid-123"/);
  assert.match(cmd, /claude-readonly\.settings\.json/);
  assert.doesNotMatch(cmd, /--permission-mode/);
});

test('buildLaunchCommand (claude, write, atendido vs desatendido, PowerShell)', () => {
  const attended = buildLaunchCommand({
    family: 'claude',
    role: 'write',
    mode: 'attended',
    sessionId: 'uuid-1',
    installRoot: '/inst',
    windows: true,
  });
  const unattended = buildLaunchCommand({
    family: 'claude',
    role: 'write',
    mode: 'unattended',
    sessionId: 'uuid-2',
    installRoot: '/inst',
    windows: true,
  });
  assert.match(attended, /^\$env:DISABLE_AUTOUPDATER = "1"; claude /);
  assert.match(attended, /--permission-mode manual/);
  assert.match(unattended, /--permission-mode dontAsk/);
  assert.match(attended, /claude-write\.settings\.json/);
});

test('buildLaunchCommand (codex): perfil/sandbox/approval varían por role+mode, sin variante PowerShell distinta', () => {
  const roAttended = buildLaunchCommand({ family: 'codex', role: 'read-only', mode: 'attended' });
  const roUnattended = buildLaunchCommand({ family: 'codex', role: 'read-only', mode: 'unattended' });
  const writeAttended = buildLaunchCommand({ family: 'codex', role: 'write', mode: 'attended' });
  const writeUnattended = buildLaunchCommand({ family: 'codex', role: 'write', mode: 'unattended' });

  assert.equal(roAttended, 'codex -p cmo-readonly -s read-only -a untrusted --disable hooks');
  assert.equal(roUnattended, 'codex -p cmo-readonly -s read-only -a never --disable hooks');
  assert.equal(writeAttended, 'codex -p cmo-write -s workspace-write -a on-request --disable hooks');
  assert.equal(writeUnattended, 'codex -p cmo-write -s workspace-write -a never --disable hooks');
});

test('buildLaunchCommand: familia desconocida lanza Error', () => {
  assert.throws(() => buildLaunchCommand({ family: 'gpt', role: 'read-only', mode: 'attended' }), /Error/);
});

// ---------------------------------------------------------------------------
// locateCodexRollout: 1 candidato vs 2 candidatos (ambiguo)
// ---------------------------------------------------------------------------

function writeRollout(dir, name, { cwd, source = 'cli', originator = 'codex-tui', sessionId = 'sess-1' }) {
  const filePath = path.join(dir, name);
  const metaLine = JSON.stringify({
    timestamp: '2026-07-19T00:00:00.000Z',
    type: 'session_meta',
    payload: { session_id: sessionId, cwd, source, originator, cli_version: '0.144.6' },
  });
  fs.writeFileSync(filePath, `${metaLine}\n`);
  return filePath;
}

test('locateCodexRollout: un solo candidato en la ventana -> lo devuelve', () => {
  const sessionsRoot = mkTmpDir('cmo-sessions-');
  writeRollout(sessionsRoot, 'rollout-2026-07-19T00-00-00-sess-1.jsonl', {
    cwd: '/repo/worktree-a',
    sessionId: 'sess-1',
  });

  const located = locateCodexRollout({ sessionsRoot, cwd: '/repo/worktree-a', afterMs: 0 });
  assert.notEqual(located, null);
  assert.equal(located.sessionId, 'sess-1');
});

test('locateCodexRollout: dos candidatos en la ventana -> null (ambiguo)', () => {
  const sessionsRoot = mkTmpDir('cmo-sessions-');
  writeRollout(sessionsRoot, 'rollout-a.jsonl', { cwd: '/repo/worktree-a', sessionId: 'sess-1' });
  writeRollout(sessionsRoot, 'rollout-b.jsonl', { cwd: '/repo/worktree-a', sessionId: 'sess-2' });

  const located = locateCodexRollout({ sessionsRoot, cwd: '/repo/worktree-a', afterMs: 0 });
  assert.equal(located, null);
});

test('locateCodexRollout: descarta candidatos con distinto cwd, source u originator', () => {
  const sessionsRoot = mkTmpDir('cmo-sessions-');
  writeRollout(sessionsRoot, 'rollout-otro-cwd.jsonl', { cwd: '/repo/otro-worktree', sessionId: 'sess-x' });
  writeRollout(sessionsRoot, 'rollout-exec.jsonl', { cwd: '/repo/worktree-a', source: 'exec', originator: 'codex_exec', sessionId: 'sess-y' });
  writeRollout(sessionsRoot, 'rollout-bueno.jsonl', { cwd: '/repo/worktree-a', sessionId: 'sess-good' });

  const located = locateCodexRollout({ sessionsRoot, cwd: '/repo/worktree-a', afterMs: 0 });
  assert.notEqual(located, null);
  assert.equal(located.sessionId, 'sess-good');
});

// ---------------------------------------------------------------------------
// createOwnedSession (Codex)
// ---------------------------------------------------------------------------

test('createOwnedSession (codex): NO intenta localizar el rollout todavía -> registra la sesión con transcriptPath pendiente (null)', () => {
  // Contrato nuevo (fix wave 1, tras el hallazgo del review): el rollout de Codex no existe al
  // arrancar la terminal (se escribe recién en el primer turno). createOwnedSession ya no intenta
  // localizarlo -- ni siquiera toca CODEX_HOME/sessions -- y por eso este test no prepara ningún
  // rollout ni setea CODEX_HOME: si createOwnedSession intentara leerlo, fallaría o encontraría 0
  // candidatos, y este test lo detectaría por un transcriptPath/sessionId != null inesperado.
  const stateDir = mkTmpDir('cmo-state-');
  const worktree = '/repo/ai-workflows-worktree';

  const fakeOrcaRunner = (args) => {
    if (args[0] === 'terminal' && args[1] === 'create') {
      return { stdout: JSON.stringify({ handle: 'term_codex_1' }), code: 0 };
    }
    throw new Error(`orcaRunner inesperado en el test: ${args.join(' ')}`);
  };

  const result = createOwnedSession({
    family: 'codex',
    role: 'read-only',
    mode: 'attended',
    worktree,
    orcaRunner: fakeOrcaRunner,
    now: () => 12345,
    stateDir,
  });

  assert.notEqual(result, null);
  assert.equal(result.session.terminalHandle, 'term_codex_1');
  assert.equal(result.session.transcriptPath, null);
  assert.equal(result.session.sessionId, null);
  assert.equal(result.session.createdAt, 12345);

  const registry = JSON.parse(fs.readFileSync(path.join(stateDir, 'sessions.json'), 'utf8'));
  const entries = Object.values(registry);
  assert.equal(entries.length, 1);
  assert.equal(entries[0].terminalHandle, 'term_codex_1');
  assert.equal(entries[0].family, 'codex');
  assert.equal(entries[0].transcriptPath, null);
});

// ---------------------------------------------------------------------------
// createOwnedSession (Claude)
// ---------------------------------------------------------------------------

test('createOwnedSession (claude): fija --session-id, arma el path del transcript por slug y devuelve la sesión', async () => {
  const claudeConfigDir = mkTmpDir('cmo-claude-home-');
  const stateDir = mkTmpDir('cmo-state-');
  const worktree = '/repo/ai-workflows-worktree';

  await withEnv({ CLAUDE_CONFIG_DIR: claudeConfigDir, CROSS_MODEL_ORCA: ASSETS_DIR }, () => {
    let capturedCommand = null;
    const fakeOrcaRunner = (args) => {
      if (args[0] === 'terminal' && args[1] === 'create') {
        const commandIdx = args.indexOf('--command');
        capturedCommand = args[commandIdx + 1];
        return { stdout: JSON.stringify({ handle: 'term_claude_1' }), code: 0 };
      }
      throw new Error(`orcaRunner inesperado en el test: ${args.join(' ')}`);
    };

    const result = createOwnedSession({
      family: 'claude',
      role: 'read-only',
      mode: 'attended',
      worktree,
      orcaRunner: fakeOrcaRunner,
      stateDir,
    });

    assert.notEqual(result, null);
    const { session } = result;
    assert.equal(session.terminalHandle, 'term_claude_1');
    assert.match(session.sessionId, /^[0-9a-f-]{36}$/);
    const expectedSlug = worktree.replace(/\//g, '-');
    assert.equal(
      session.transcriptPath,
      path.join(claudeConfigDir, 'projects', expectedSlug, `${session.sessionId}.jsonl`)
    );
    assert.match(capturedCommand, new RegExp(`--session-id "${session.sessionId}"`));
  });
});

// ---------------------------------------------------------------------------
// resolveCodexTranscript: resolución LAZY del locator de Codex (fix wave 1)
// ---------------------------------------------------------------------------

test('resolveCodexTranscript: un candidato ya presente -> resuelve en el primer intento, sin reintentos', async () => {
  const codexHome = mkTmpDir('cmo-codex-home-');
  const stateDir = mkTmpDir('cmo-state-');
  const worktree = '/repo/worktree-lazy';

  await withEnv({ CODEX_HOME: codexHome }, async () => {
    const sessionsRoot = path.join(codexHome, 'sessions');
    fs.mkdirSync(sessionsRoot, { recursive: true });
    writeRollout(sessionsRoot, 'rollout-lazy.jsonl', { cwd: worktree, sessionId: 'codex-sess-lazy' });

    const session = { family: 'codex', worktree, createdAt: 0, transcriptPath: null, sessionId: null, stateDir };
    let sleepCalls = 0;
    const fakeSleep = () => {
      sleepCalls += 1;
      return Promise.resolve();
    };

    const resolved = await resolveCodexTranscript({ session, sleep: fakeSleep });

    const expectedPath = path.join(sessionsRoot, 'rollout-lazy.jsonl');
    assert.equal(resolved, expectedPath);
    assert.equal(session.transcriptPath, expectedPath);
    assert.equal(session.sessionId, 'codex-sess-lazy');
    assert.equal(sleepCalls, 0);

    const registry = JSON.parse(fs.readFileSync(path.join(stateDir, 'sessions.json'), 'utf8'));
    assert.equal(Object.values(registry)[0].transcriptPath, expectedPath);
  });
});

test('resolveCodexTranscript: 0 candidatos al inicio, aparece recién en el 2do intento -> resuelve tras reintentar', async () => {
  const codexHome = mkTmpDir('cmo-codex-home-');
  const stateDir = mkTmpDir('cmo-state-');
  const worktree = '/repo/worktree-lazy-2';

  await withEnv({ CODEX_HOME: codexHome }, async () => {
    const sessionsRoot = path.join(codexHome, 'sessions');
    fs.mkdirSync(sessionsRoot, { recursive: true });
    // El rollout todavía no existe: simula el "aún no flushó" del hallazgo del review. Se
    // escribe recién durante el "sleep" del primer reintento (efecto colateral deliberado del
    // fake, para no depender de tiempo real).
    let sleepCalls = 0;
    const fakeSleep = () => {
      sleepCalls += 1;
      writeRollout(sessionsRoot, 'rollout-tardio.jsonl', { cwd: worktree, sessionId: 'codex-sess-tardio' });
      return Promise.resolve();
    };

    const session = { family: 'codex', worktree, createdAt: 0, transcriptPath: null, sessionId: null, stateDir };
    const resolved = await resolveCodexTranscript({ session, sleep: fakeSleep });

    assert.equal(resolved, path.join(sessionsRoot, 'rollout-tardio.jsonl'));
    assert.equal(sleepCalls, 1);
  });
});

test('resolveCodexTranscript: nunca aparece -> null tras agotar los reintentos acotados', async () => {
  const codexHome = mkTmpDir('cmo-codex-home-');
  const stateDir = mkTmpDir('cmo-state-');
  const worktree = '/repo/worktree-lazy-3';

  await withEnv({ CODEX_HOME: codexHome }, async () => {
    fs.mkdirSync(path.join(codexHome, 'sessions'), { recursive: true }); // vacío: nunca hay rollout.

    let sleepCalls = 0;
    const fakeSleep = () => {
      sleepCalls += 1;
      return Promise.resolve();
    };

    const session = { family: 'codex', worktree, createdAt: 0, transcriptPath: null, sessionId: null, stateDir };
    const resolved = await resolveCodexTranscript({ session, sleep: fakeSleep, maxAttempts: 3 });

    assert.equal(resolved, null);
    assert.equal(session.transcriptPath, null);
    assert.equal(sleepCalls, 2); // 3 intentos, sleep solo entre intentos (no después del último).
    assert.equal(fs.existsSync(path.join(stateDir, 'sessions.json')), false); // nunca se persistió nada.
  });
});

test('resolveCodexTranscript: dos candidatos (ambiguo) en todos los intentos -> null', async () => {
  const codexHome = mkTmpDir('cmo-codex-home-');
  const stateDir = mkTmpDir('cmo-state-');
  const worktree = '/repo/worktree-lazy-4';

  await withEnv({ CODEX_HOME: codexHome }, async () => {
    const sessionsRoot = path.join(codexHome, 'sessions');
    fs.mkdirSync(sessionsRoot, { recursive: true });
    writeRollout(sessionsRoot, 'rollout-a.jsonl', { cwd: worktree, sessionId: 'codex-sess-a' });
    writeRollout(sessionsRoot, 'rollout-b.jsonl', { cwd: worktree, sessionId: 'codex-sess-b' });

    const session = { family: 'codex', worktree, createdAt: 0, transcriptPath: null, sessionId: null, stateDir };
    const resolved = await resolveCodexTranscript({ session, sleep: () => Promise.resolve(), maxAttempts: 2 });

    assert.equal(resolved, null);
    assert.equal(session.transcriptPath, null);
  });
});

test('resolveCodexTranscript: ya resuelto -> devuelve el valor cacheado sin tocar el filesystem ni dormir', async () => {
  const stateDir = mkTmpDir('cmo-state-');
  const session = {
    family: 'codex',
    worktree: '/repo/no-importa',
    createdAt: 0,
    transcriptPath: '/ya/resuelto/rollout.jsonl',
    sessionId: 'codex-sess-cacheado',
    stateDir,
  };
  let sleepCalls = 0;
  const fakeSleep = () => {
    sleepCalls += 1;
    return Promise.resolve();
  };

  // Sin CODEX_HOME seteado a un sessions/ real: si esta función tocara el filesystem, fallaría
  // silenciosamente (listRolloutFiles atrapa el ENOENT) pero igual estaríamos verificando el
  // comportamiento equivocado. La aserción de sleepCalls===0 es la prueba real de que no reintentó.
  const resolved = await resolveCodexTranscript({ session, sleep: fakeSleep });

  assert.equal(resolved, '/ya/resuelto/rollout.jsonl');
  assert.equal(sleepCalls, 0);
});

test('resolveCodexTranscript (claude): pass-through del transcriptPath ya resuelto por createOwnedSession', async () => {
  const session = { family: 'claude', transcriptPath: '/algun/transcript.jsonl' };
  const resolved = await resolveCodexTranscript({ session, sleep: () => Promise.resolve() });
  assert.equal(resolved, '/algun/transcript.jsonl');
});

// ---------------------------------------------------------------------------
// createDispatch
// ---------------------------------------------------------------------------

test('createDispatch: parsea taskId/dispatchId, genera un nonce no vacío y persiste el registro', () => {
  const stateDir = mkTmpDir('cmo-state-');
  const session = { uid: 'sess-uid-1', terminalHandle: 'term_1', stateDir };

  const calls = [];
  const fakeOrcaRunner = (args) => {
    calls.push(args);
    if (args[1] === 'task-create') {
      return { stdout: JSON.stringify({ taskId: 'task_1' }), code: 0 };
    }
    if (args[1] === 'dispatch') {
      return { stdout: JSON.stringify({ dispatchId: 'dispatch_1' }), code: 0 };
    }
    throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
  };

  const dispatch = createDispatch({
    session,
    spec: 'Hace la tarea X.',
    root: '/repo/root',
    orcaRunner: fakeOrcaRunner,
  });

  assert.equal(dispatch.taskId, 'task_1');
  assert.equal(dispatch.dispatchId, 'dispatch_1');
  assert.equal(dispatch.expectedAssignee, 'term_1');
  assert.equal(typeof dispatch.nonce, 'string');
  assert.notEqual(dispatch.nonce.length, 0);

  // El spec inyectado (task-create) debe llevar el nonce.
  const taskCreateCall = calls.find((c) => c[1] === 'task-create');
  const specIdx = taskCreateCall.indexOf('--spec');
  assert.match(taskCreateCall[specIdx + 1], new RegExp(`nonce=${dispatch.nonce}`));

  const registry = JSON.parse(fs.readFileSync(path.join(stateDir, 'dispatches.json'), 'utf8'));
  assert.equal(registry['dispatch_1'].taskId, 'task_1');
  assert.equal(registry['dispatch_1'].nonce, dispatch.nonce);
  assert.equal(registry['dispatch_1'].expectedAssignee, 'term_1');
});

test('createDispatch: lanza si "task-create" no devuelve taskId', () => {
  const stateDir = mkTmpDir('cmo-state-');
  const session = { uid: 'sess-uid-2', terminalHandle: 'term_1', stateDir };
  const fakeOrcaRunner = () => ({ stdout: JSON.stringify({}), code: 0 });

  assert.throws(
    () => createDispatch({ session, spec: 'x', root: '/repo/root', orcaRunner: fakeOrcaRunner }),
    /taskId/
  );
});

// ---------------------------------------------------------------------------
// awaitDone
// ---------------------------------------------------------------------------

test('awaitDone: worker_done con IDs correctos -> valida autoridad, cosecha y marca promoted', async () => {
  const stateDir = mkTmpDir('cmo-state-');
  const root = mkTmpDir('cmo-report-root-');
  const session = { family: 'codex', transcriptPath: CODEX_FIXTURE, terminalHandle: 'term_1', stateDir };
  const dispatch = { taskId: 'T1', dispatchId: 'D1', nonce: 'NONCE-ACTUAL', expectedAssignee: 'term_1' };

  let checkCalls = 0;
  const fakeOrcaRunner = (args) => {
    if (args[0] === 'orchestration' && args[1] === 'check') {
      checkCalls += 1;
      return {
        stdout: JSON.stringify({
          messages: [{ type: 'worker_done', payload: { taskId: 'T1', dispatchId: 'D1' }, from: 'term_1' }],
        }),
        code: 0,
      };
    }
    throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
  };

  const result = await awaitDone({
    session,
    dispatch,
    coordinatorHandle: 'coord_1',
    reportPath: 'informe.md',
    root,
    deadlineMs: 1000,
    orcaRunner: fakeOrcaRunner,
    sleep: instantSleep,
  });

  assert.equal(result.code, 0);
  const written = fs.readFileSync(result.reportPath, 'utf8');
  assert.match(written, /NONCE-ACTUAL/);
  assert.equal(checkCalls, 1);

  const fsm = makeDedupFsm(path.join(stateDir, 'dedup-fsm.json'));
  assert.equal(fsm.isPromoted('D1:NONCE-ACTUAL'), true);
});

test('awaitDone: worker_done con IDs que NO coinciden -> no cosecha, agota el deadline (timeout)', async () => {
  const stateDir = mkTmpDir('cmo-state-');
  const root = mkTmpDir('cmo-report-root-');
  const session = { family: 'codex', transcriptPath: CODEX_FIXTURE, terminalHandle: 'term_1', stateDir };
  const dispatch = { taskId: 'T1', dispatchId: 'D1', nonce: 'NONCE-ACTUAL', expectedAssignee: 'term_1' };

  const fakeOrcaRunner = (args) => {
    if (args[0] === 'orchestration' && args[1] === 'check') {
      return {
        stdout: JSON.stringify({
          messages: [{ type: 'worker_done', payload: { taskId: 'OTRO', dispatchId: 'OTRO' }, from: 'term_1' }],
        }),
        code: 0,
      };
    }
    throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
  };

  let ticks = 0;
  const fakeNow = () => {
    ticks += 1;
    return ticks === 1 ? 0 : 10_000; // primer now() arranca el deadline; el resto ya lo agota.
  };

  const result = await awaitDone({
    session,
    dispatch,
    coordinatorHandle: 'coord_1',
    reportPath: 'informe.md',
    root,
    deadlineMs: 5,
    orcaRunner: fakeOrcaRunner,
    now: fakeNow,
    sleep: instantSleep,
  });

  assert.equal(result.code, 3);
  assert.equal(fs.existsSync(path.join(root, 'informe.md')), false);

  const fsm = makeDedupFsm(path.join(stateDir, 'dedup-fsm.json'));
  assert.equal(fsm.isPromoted('D1:NONCE-ACTUAL'), false);
});

test('awaitDone: un segundo worker_done idéntico no reprocesa (dedup vía FSM)', async () => {
  const stateDir = mkTmpDir('cmo-state-');
  const root = mkTmpDir('cmo-report-root-');
  const session = { family: 'codex', transcriptPath: CODEX_FIXTURE, terminalHandle: 'term_1', stateDir };
  const dispatch = { taskId: 'T1', dispatchId: 'D1', nonce: 'NONCE-ACTUAL', expectedAssignee: 'term_1' };

  let checkCalls = 0;
  const fakeOrcaRunner = (args) => {
    if (args[0] === 'orchestration' && args[1] === 'check') {
      checkCalls += 1;
      return {
        stdout: JSON.stringify({
          messages: [{ type: 'worker_done', payload: { taskId: 'T1', dispatchId: 'D1' }, from: 'term_1' }],
        }),
        code: 0,
      };
    }
    throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
  };

  const first = await awaitDone({
    session,
    dispatch,
    coordinatorHandle: 'coord_1',
    reportPath: 'informe.md',
    root,
    deadlineMs: 1000,
    orcaRunner: fakeOrcaRunner,
    sleep: instantSleep,
  });
  assert.equal(first.code, 0);
  assert.equal(checkCalls, 1);

  // Segundo worker_done idéntico (mismo dispatchId:nonce): no debe volver a invocar
  // "orchestration check" ni harvest -- isPromoted corta antes de entrar al loop.
  const second = await awaitDone({
    session,
    dispatch,
    coordinatorHandle: 'coord_1',
    reportPath: 'informe.md',
    root,
    deadlineMs: 1000,
    orcaRunner: fakeOrcaRunner,
    sleep: instantSleep,
  });

  assert.equal(second.code, 0);
  assert.equal(checkCalls, 1); // sin llamadas adicionales a "orchestration check"
});

test('awaitDone (claude): sin worker_done, tui-idle satisfied=true es autoridad suficiente', async () => {
  const stateDir = mkTmpDir('cmo-state-');
  const root = mkTmpDir('cmo-report-root-');
  const claudeFixture = path.join(TEST_DIR, 'fixtures/claude-transcript.jsonl');
  const session = { family: 'claude', transcriptPath: claudeFixture, terminalHandle: 'term_c1', stateDir };
  const dispatch = { taskId: 'T1', dispatchId: 'D1', nonce: 'NONCE-ACTUAL', expectedAssignee: 'term_c1' };

  const fakeOrcaRunner = (args) => {
    if (args[0] === 'orchestration' && args[1] === 'check') {
      return { stdout: JSON.stringify({ messages: [] }), code: 0 };
    }
    if (args[0] === 'terminal' && args[1] === 'wait') {
      return { stdout: JSON.stringify({ satisfied: true }), code: 0 };
    }
    throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
  };

  const result = await awaitDone({
    session,
    dispatch,
    coordinatorHandle: 'coord_1',
    reportPath: 'informe.md',
    root,
    deadlineMs: 1000,
    orcaRunner: fakeOrcaRunner,
    sleep: instantSleep,
  });

  assert.equal(result.code, 0);
  const written = fs.readFileSync(result.reportPath, 'utf8');
  assert.match(written, /NONCE-ACTUAL/);
});

test('awaitDone (codex): transcriptPath pendiente -> resuelve el rollout lazy y después cosecha normalmente', async () => {
  const codexHome = mkTmpDir('cmo-codex-home-');
  const stateDir = mkTmpDir('cmo-state-');
  const root = mkTmpDir('cmo-report-root-');
  const worktree = '/repo/ai-workflows'; // mismo cwd que CODEX_FIXTURE

  await withEnv({ CODEX_HOME: codexHome }, async () => {
    const sessionsRoot = path.join(codexHome, 'sessions');
    fs.mkdirSync(sessionsRoot, { recursive: true });
    fs.copyFileSync(CODEX_FIXTURE, path.join(sessionsRoot, 'rollout-lazy-awaitdone.jsonl'));

    const session = {
      family: 'codex',
      worktree,
      createdAt: 0,
      transcriptPath: null,
      sessionId: null,
      terminalHandle: 'term_1',
      stateDir,
    };
    const dispatch = { taskId: 'T1', dispatchId: 'D1', nonce: 'NONCE-ACTUAL', expectedAssignee: 'term_1' };

    let checkCalls = 0;
    const fakeOrcaRunner = (args) => {
      if (args[0] === 'orchestration' && args[1] === 'check') {
        checkCalls += 1;
        return {
          stdout: JSON.stringify({
            messages: [{ type: 'worker_done', payload: { taskId: 'T1', dispatchId: 'D1' }, from: 'term_1' }],
          }),
          code: 0,
        };
      }
      throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
    };

    const result = await awaitDone({
      session,
      dispatch,
      coordinatorHandle: 'coord_1',
      reportPath: 'informe.md',
      root,
      deadlineMs: 1000,
      orcaRunner: fakeOrcaRunner,
      sleep: instantSleep,
    });

    assert.equal(result.code, 0);
    assert.equal(checkCalls, 1);
    assert.equal(session.transcriptPath, path.join(sessionsRoot, 'rollout-lazy-awaitdone.jsonl'));
    const written = fs.readFileSync(result.reportPath, 'utf8');
    assert.match(written, /NONCE-ACTUAL/);
  });
});

test('awaitDone (codex): el rollout nunca aparece -> code 4 (degradar a cli), sin consultar "orchestration check"', async () => {
  const codexHome = mkTmpDir('cmo-codex-home-');
  const stateDir = mkTmpDir('cmo-state-');
  const root = mkTmpDir('cmo-report-root-');
  const worktree = '/repo/worktree-sin-rollout';

  await withEnv({ CODEX_HOME: codexHome }, async () => {
    fs.mkdirSync(path.join(codexHome, 'sessions'), { recursive: true }); // vacío: nunca hay rollout.

    const session = {
      family: 'codex',
      worktree,
      createdAt: 0,
      transcriptPath: null,
      sessionId: null,
      terminalHandle: 'term_1',
      stateDir,
    };
    const dispatch = { taskId: 'T1', dispatchId: 'D1', nonce: 'NONCE-ACTUAL', expectedAssignee: 'term_1' };

    let checkCalls = 0;
    const fakeOrcaRunner = (args) => {
      if (args[0] === 'orchestration' && args[1] === 'check') {
        checkCalls += 1;
        return { stdout: JSON.stringify({ messages: [] }), code: 0 };
      }
      throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
    };

    const result = await awaitDone({
      session,
      dispatch,
      coordinatorHandle: 'coord_1',
      reportPath: 'informe.md',
      root,
      deadlineMs: 1000,
      orcaRunner: fakeOrcaRunner,
      sleep: instantSleep,
    });

    assert.equal(result.code, 4);
    assert.equal(checkCalls, 0); // nunca llegó a entrar al poll de worker_done
    assert.equal(fs.existsSync(path.join(root, 'informe.md')), false);
  });
});

// ---------------------------------------------------------------------------
// recover
// ---------------------------------------------------------------------------

test('recover (read-only): interrumpe, confirma idle -> recovered:true', () => {
  const session = { role: 'read-only', terminalHandle: 'term_1' };
  const dispatch = { taskId: 'T1', dispatchId: 'D1' };
  const calls = [];
  const fakeOrcaRunner = (args) => {
    calls.push(args);
    if (args.includes('--interrupt')) return { stdout: '', code: 0 };
    if (args[1] === 'wait') return { stdout: JSON.stringify({ satisfied: true }), code: 0 };
    throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
  };

  const result = recover({ session, dispatch, orcaRunner: fakeOrcaRunner });

  assert.equal(result.recovered, true);
  assert.equal(calls.some((c) => c.includes('--interrupt')), true);
  assert.equal(calls.some((c) => c[1] === 'wait'), true);
  assert.equal(calls.some((c) => c[1] === 'close'), false); // read-only no necesita demostrar cierre
});

test('recover (write): idle confirmado pero SIN cierre demostrado -> recovered:false', () => {
  const session = { role: 'write', terminalHandle: 'term_1' };
  const dispatch = { taskId: 'T1', dispatchId: 'D1' };
  const fakeOrcaRunner = (args) => {
    if (args.includes('--interrupt')) return { stdout: '', code: 0 };
    if (args[1] === 'wait') return { stdout: JSON.stringify({ satisfied: true }), code: 0 };
    if (args[1] === 'close') return { stdout: JSON.stringify({ error: 'no se pudo cerrar' }), code: 1 };
    throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
  };

  const result = recover({ session, dispatch, orcaRunner: fakeOrcaRunner });

  assert.equal(result.recovered, false);
});

test('recover (write): idle confirmado y cierre exitoso -> recovered:true', () => {
  const session = { role: 'write', terminalHandle: 'term_1' };
  const dispatch = { taskId: 'T1', dispatchId: 'D1' };
  const fakeOrcaRunner = (args) => {
    if (args.includes('--interrupt')) return { stdout: '', code: 0 };
    if (args[1] === 'wait') return { stdout: JSON.stringify({ satisfied: true }), code: 0 };
    if (args[1] === 'close') return { stdout: JSON.stringify({ closed: true }), code: 0 };
    throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
  };

  const result = recover({ session, dispatch, orcaRunner: fakeOrcaRunner });

  assert.equal(result.recovered, true);
});

test('recover: idle NO confirmado -> recovered:false sin importar el rol', () => {
  const session = { role: 'read-only', terminalHandle: 'term_1' };
  const dispatch = { taskId: 'T1', dispatchId: 'D1' };
  const fakeOrcaRunner = (args) => {
    if (args.includes('--interrupt')) return { stdout: '', code: 0 };
    if (args[1] === 'wait') return { stdout: JSON.stringify({ satisfied: false }), code: 0 };
    throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
  };

  const result = recover({ session, dispatch, orcaRunner: fakeOrcaRunner });

  assert.equal(result.recovered, false);
});
