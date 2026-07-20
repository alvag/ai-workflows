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
import { fileURLToPath } from 'node:url';
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

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
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
// Builders de envelope de Orca (formas REALES, verificadas en vivo contra el CLI
// — ver spikes/RESULTS.md, Fase 7). Todo comando `orca ... --json` envuelve su
// salida en `{ id, ok, result | error, _meta }`. Los fakes de abajo devuelven
// exactamente esa forma para que los tests validen contra Orca real, no contra
// una forma plana asumida (el bug que estos tests no detectaban antes).
// ---------------------------------------------------------------------------

function okEnvelope(result) {
  return { stdout: JSON.stringify({ id: 'test', ok: true, result, _meta: {} }), code: 0 };
}

// `terminal wait` y `terminal close` fallidos: el CLI real devuelve `ok:false` con
// `error.code` — y, para `close`, exit 0 pese al fallo (por eso el adaptador NO mira el code).
function errEnvelope(code, { exit = 1 } = {}) {
  return { stdout: JSON.stringify({ id: 'test', ok: false, error: { code, message: code }, _meta: {} }), code: exit };
}

// ---------------------------------------------------------------------------
// buildLaunchCommand: construcción del comando por family+role+mode
// ---------------------------------------------------------------------------

test('buildLaunchCommand (claude, read-only, POSIX): tools cerrado, MCP off (strict + config vacío), sin permission-mode, session-id fijado', () => {
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
  // MCP off: read-only = sin superficie de ejecución (ni built-in Bash ni tool MCP del IDE).
  assert.match(cmd, /--strict-mcp-config/);
  assert.match(cmd, /--mcp-config "\/inst\/launch\/claude-readonly\.mcp\.json"/);
  assert.match(cmd, /--session-id "uuid-123"/);
  assert.match(cmd, /claude-readonly\.settings\.json/);
  assert.doesNotMatch(cmd, /--permission-mode/);
});

test('buildLaunchCommand (claude, write): NO fuerza MCP off (el rol write puede usar MCP con gate por permission-mode)', () => {
  const cmd = buildLaunchCommand({
    family: 'claude',
    role: 'write',
    mode: 'attended',
    sessionId: 'uuid-w',
    installRoot: '/inst',
    windows: false,
  });
  assert.doesNotMatch(cmd, /--strict-mcp-config/);
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

test('buildLaunchCommand (codex): sandbox/approval varían por role+mode, features.apps=false inline, sin -p ni variante PowerShell distinta', () => {
  const roAttended = buildLaunchCommand({ family: 'codex', role: 'read-only', mode: 'attended' });
  const roUnattended = buildLaunchCommand({ family: 'codex', role: 'read-only', mode: 'unattended' });
  const writeAttended = buildLaunchCommand({ family: 'codex', role: 'write', mode: 'attended' });
  const writeUnattended = buildLaunchCommand({ family: 'codex', role: 'write', mode: 'unattended' });

  assert.equal(roAttended, 'codex -c features.apps=false -s read-only -a untrusted --disable hooks');
  assert.equal(roUnattended, 'codex -c features.apps=false -s read-only -a never --disable hooks');
  assert.equal(writeAttended, 'codex -c features.apps=false -s workspace-write -a on-request --disable hooks');
  assert.equal(writeUnattended, 'codex -c features.apps=false -s workspace-write -a never --disable hooks');
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
      return okEnvelope({ terminal: { handle: 'term_codex_1' } });
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
  // Slug esperado como literal (NO se deriva con la misma lógica que el código bajo prueba: eso
  // consagraría un bug si `slugifyCwd` estuviera mal, como pasó con la versión anterior que solo
  // reemplazaba "/" y dejaba pasar el "." literal -- ver el test dedicado con path punteado más
  // abajo, que sí lo hubiera detectado).
  const expectedSlug = '-repo-ai-workflows-worktree';

  await withEnv({ CLAUDE_CONFIG_DIR: claudeConfigDir, CROSS_MODEL_ORCA: ASSETS_DIR }, () => {
    let capturedCommand = null;
    const fakeOrcaRunner = (args) => {
      if (args[0] === 'terminal' && args[1] === 'create') {
        const commandIdx = args.indexOf('--command');
        capturedCommand = args[commandIdx + 1];
        return okEnvelope({ terminal: { handle: 'term_claude_1' } });
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
    assert.equal(
      session.transcriptPath,
      path.join(claudeConfigDir, 'projects', expectedSlug, `${session.sessionId}.jsonl`)
    );
    assert.match(capturedCommand, new RegExp(`--session-id "${session.sessionId}"`));
  });
});

test('createOwnedSession (claude): un worktree con "." en el path slugifica el punto a "-" (fix wave 2, S1)', async () => {
  // Regresión del bug real encontrado en el final review: la versión anterior de slugifyCwd solo
  // reemplazaba "/" (\\ y /) y dejaba el "." literal en el slug, apuntando a un directorio de
  // transcript inexistente. Este worktree, con un "." en el medio del path, lo hubiera detectado.
  const claudeConfigDir = mkTmpDir('cmo-claude-home-');
  const stateDir = mkTmpDir('cmo-state-');
  const worktree = '/tmp/foo.bar/baz';
  // Literal (no derivado de slugifyCwd): confirmado a mano contra el algoritmo real de Claude Code
  // con dos directorios de proyecto reales (ver docstring de slugifyCwd en dispatch-adapter.mjs).
  const expectedSlug = '-tmp-foo-bar-baz';

  await withEnv({ CLAUDE_CONFIG_DIR: claudeConfigDir, CROSS_MODEL_ORCA: ASSETS_DIR }, () => {
    const fakeOrcaRunner = (args) => {
      if (args[0] === 'terminal' && args[1] === 'create') {
        return okEnvelope({ terminal: { handle: 'term_claude_dot' } });
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
    assert.equal(
      result.session.transcriptPath,
      path.join(claudeConfigDir, 'projects', expectedSlug, `${result.session.sessionId}.jsonl`)
    );
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
      return okEnvelope({ task: { id: 'task_1' } });
    }
    if (args[1] === 'wait') {
      return okEnvelope({ wait: { satisfied: true } }); // boot completo: tui-idle antes de inyectar.
    }
    if (args[1] === 'dispatch') {
      return okEnvelope({ dispatch: { id: 'dispatch_1' }, injected: true });
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

  // worker_done abandonado: el dispatch NO pasa --from (no ruteamos un worker_done que no consumimos).
  const dispatchCall = calls.find((c) => c[1] === 'dispatch');
  assert.equal(dispatchCall.includes('--from'), false);
  assert.equal(dispatchCall.includes('--inject'), true);

  const registry = JSON.parse(fs.readFileSync(path.join(stateDir, 'dispatches.json'), 'utf8'));
  assert.equal(registry['dispatch_1'].taskId, 'task_1');
  assert.equal(registry['dispatch_1'].nonce, dispatch.nonce);
  assert.equal(registry['dispatch_1'].expectedAssignee, 'term_1');
});

test('createDispatch: el secundario nunca llega a tui-idle (boot) -> lanza y NO despacha (degradar a cli)', () => {
  const stateDir = mkTmpDir('cmo-state-');
  const session = { uid: 'sess-uid-boot', terminalHandle: 'term_1', stateDir };

  const calls = [];
  const fakeOrcaRunner = (args) => {
    calls.push(args);
    if (args[1] === 'task-create') return okEnvelope({ task: { id: 'task_boot' } });
    if (args[1] === 'wait') return errEnvelope('timeout'); // boot no completó: tui-idle nunca satisfecho.
    if (args[1] === 'dispatch') throw new Error('no debería despachar si el boot no llegó a idle');
    throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
  };

  assert.throws(
    () => createDispatch({ session, spec: 'x', root: '/repo/root', orcaRunner: fakeOrcaRunner }),
    /tui-idle/
  );
  // No debe haberse intentado el dispatch (el prompt se perdería).
  assert.equal(calls.some((c) => c[1] === 'dispatch'), false);
});

test('createDispatch: lanza si "task-create" no devuelve taskId', () => {
  const stateDir = mkTmpDir('cmo-state-');
  const session = { uid: 'sess-uid-2', terminalHandle: 'term_1', stateDir };
  const fakeOrcaRunner = () => okEnvelope({}); // ok:true pero sin `task`: no hay task.id que extraer.

  assert.throws(
    () => createDispatch({ session, spec: 'x', root: '/repo/root', orcaRunner: fakeOrcaRunner }),
    /taskId/
  );
});

// ---------------------------------------------------------------------------
// awaitDone
// ---------------------------------------------------------------------------

test('awaitDone (codex): cosecha del transcript propio por nonce y marca promoted (sin worker_done)', async () => {
  // Nuevo modelo (decisión post-E2E de Fase 7): la detección de fin y la autoridad las da el
  // nonce+sentinel del envelope en el transcript propio, NO worker_done (que el sandbox de Codex
  // no puede enviar). awaitDone no consulta orchestration check: resuelve el transcript y llama a
  // harvest(), que hace el poll del archivo esperando el nonce. El fixture ya contiene NONCE-ACTUAL.
  const stateDir = mkTmpDir('cmo-state-');
  const root = mkTmpDir('cmo-report-root-');
  const session = { family: 'codex', transcriptPath: CODEX_FIXTURE, terminalHandle: 'term_1', stateDir };
  const dispatch = { dispatchId: 'D1', nonce: 'NONCE-ACTUAL' };

  const result = await awaitDone({ session, dispatch, reportPath: 'informe.md', root, deadlineMs: 1000 });

  assert.equal(result.code, 0);
  assert.match(fs.readFileSync(result.reportPath, 'utf8'), /NONCE-ACTUAL/);

  const fsm = makeDedupFsm(path.join(stateDir, 'dedup-fsm.json'));
  assert.equal(fsm.isPromoted('D1:NONCE-ACTUAL'), true);
});

test('awaitDone: tras cosechar OK, completa el dispatch (task-update --status completed) para liberar la terminal (reúso de sesión)', async () => {
  // Como no usamos worker_done, sin este cierre el dispatch queda "active" y Orca rechaza un segundo
  // dispatch a la misma terminal (hallazgo del E2E caso c). El cierre es best-effort y solo dispara
  // si hay dispatch.taskId.
  const stateDir = mkTmpDir('cmo-state-');
  const root = mkTmpDir('cmo-report-root-');
  const session = { family: 'codex', transcriptPath: CODEX_FIXTURE, terminalHandle: 'term_1', stateDir };
  const dispatch = { taskId: 'task_r1', dispatchId: 'D1', nonce: 'NONCE-ACTUAL' };

  const calls = [];
  const fakeOrcaRunner = (args) => {
    calls.push(args);
    if (args[1] === 'task-update') return okEnvelope({ task: { status: 'completed' } });
    throw new Error(`orcaRunner inesperado en awaitDone: ${args.join(' ')}`);
  };

  const result = await awaitDone({ session, dispatch, reportPath: 'informe.md', root, deadlineMs: 1000, orcaRunner: fakeOrcaRunner });

  assert.equal(result.code, 0);
  // Se llamó a task-update con el taskId del dispatch y --status completed.
  const upd = calls.find((c) => c[1] === 'task-update');
  assert.notEqual(upd, undefined);
  assert.equal(upd[upd.indexOf('--id') + 1], 'task_r1');
  assert.equal(upd[upd.indexOf('--status') + 1], 'completed');
});

test('awaitDone: el nonce nunca aparece en el transcript -> no cosecha, agota el deadline (timeout code 3)', async () => {
  const stateDir = mkTmpDir('cmo-state-');
  const root = mkTmpDir('cmo-report-root-');
  // transcriptPath válido (el fixture existe) pero con un nonce que NO está en él: harvest hace
  // poll hasta el deadline sin encontrarlo.
  const session = { family: 'codex', transcriptPath: CODEX_FIXTURE, terminalHandle: 'term_1', stateDir };
  const dispatch = { dispatchId: 'D1', nonce: 'NONCE-INEXISTENTE' };

  // now monotónico que avanza en cada llamada: cruza el deadline de forma determinista sin depender
  // de tiempo real (harvest chequea now() >= deadline antes de dormir, así que corta enseguida).
  let t = 0;
  const steppingNow = () => {
    const v = t;
    t += 1000;
    return v;
  };

  const result = await awaitDone({
    session,
    dispatch,
    reportPath: 'informe.md',
    root,
    deadlineMs: 1,
    now: steppingNow,
  });

  assert.equal(result.code, 3);
  assert.equal(fs.existsSync(path.join(root, 'informe.md')), false);

  const fsm = makeDedupFsm(path.join(stateDir, 'dedup-fsm.json'));
  assert.equal(fsm.isPromoted('D1:NONCE-INEXISTENTE'), false);
});

test('awaitDone: una segunda invocación con el mismo dispatch+nonce no reprocesa (dedup vía FSM)', async () => {
  const stateDir = mkTmpDir('cmo-state-');
  const root = mkTmpDir('cmo-report-root-');
  const session = { family: 'codex', transcriptPath: CODEX_FIXTURE, terminalHandle: 'term_1', stateDir };
  const dispatch = { dispatchId: 'D1', nonce: 'NONCE-ACTUAL' };

  const first = await awaitDone({ session, dispatch, reportPath: 'informe.md', root, deadlineMs: 1000 });
  assert.equal(first.code, 0);

  // Rompe el transcript antes de la 2da llamada: si reprocesara (volviera a harvest), fallaría por
  // no encontrar el nonce. Como isPromoted corta antes de tocar el transcript, devuelve code 0.
  const brokenSession = { ...session, transcriptPath: '/ruta/inexistente/rollout.jsonl' };
  const second = await awaitDone({ session: brokenSession, dispatch, reportPath: 'informe.md', root, deadlineMs: 1000 });

  assert.equal(second.code, 0);
  assert.equal(second.reportPath, path.resolve(root, 'informe.md'));
});

test('awaitDone: crash entre writeExclusive y markPromoted -> el retry ve "destino ya existe" y lo trata como éxito idempotente (fix wave 2, S2)', async () => {
  // Simula el hueco encontrado en el final review: un intento anterior ya escribió el reporte en
  // disco (writeExclusive real, dentro de "root") y avanzó la FSM hasta "received" -- pero cayó
  // antes de marcar "harvested"/"promoted". El siguiente awaitDone() para el MISMO dispatchId:nonce
  // vuelve a harvest() (isPromoted seguía en false), que encuentra el nonce en el transcript pero
  // ve el destino ya existente; el bug original devolvía {code:2} para lo que fue una cosecha exitosa.
  const stateDir = mkTmpDir('cmo-state-');
  const root = mkTmpDir('cmo-report-root-');
  const session = { family: 'codex', transcriptPath: CODEX_FIXTURE, terminalHandle: 'term_1', stateDir };
  const dispatch = { dispatchId: 'D1', nonce: 'NONCE-ACTUAL' };
  const dedupKey = 'D1:NONCE-ACTUAL';

  // Precondición: el reporte YA está en disco (como si un harvest() previo lo hubiera escrito) y
  // la FSM quedó en "received" (avanzó hasta ahí, pero el proceso cayó antes de "harvested"/"promoted").
  fs.writeFileSync(path.join(root, 'informe.md'), 'contenido cosechado por el intento anterior');
  const fsmBefore = makeDedupFsm(path.join(stateDir, 'dedup-fsm.json'));
  fsmBefore.markReceived(dedupKey);
  assert.equal(fsmBefore.isPromoted(dedupKey), false); // confirma la precondición del hueco.

  const result = await awaitDone({ session, dispatch, reportPath: 'informe.md', root, deadlineMs: 1000 });

  // Antes del fix esto era {code:2, reason:"El destino ya existe."}: un rechazo de contención
  // para lo que en realidad fue una cosecha exitosa.
  assert.equal(result.code, 0);
  assert.equal(result.reportPath, path.join(fs.realpathSync(root), 'informe.md'));
  // El contenido en disco es el del intento ANTERIOR (no se reescribe -- writeExclusive nunca se
  // vuelve a invocar en esta rama, y no debería: el archivo ya existe y es válido).
  assert.equal(fs.readFileSync(result.reportPath, 'utf8'), 'contenido cosechado por el intento anterior');

  const fsmAfter = makeDedupFsm(path.join(stateDir, 'dedup-fsm.json'));
  assert.equal(fsmAfter.isPromoted(dedupKey), true); // la FSM quedó reparada/completa.
});

test('awaitDone (claude): cosecha del transcript por nonce (transcriptPath ya resuelto en createOwnedSession)', async () => {
  // Claude ya trae su transcriptPath (determinístico por --session-id), así que awaitDone va directo
  // a harvest(), que hace poll del archivo esperando el nonce+sentinel. Mismo modelo que Codex.
  const stateDir = mkTmpDir('cmo-state-');
  const root = mkTmpDir('cmo-report-root-');
  const claudeFixture = path.join(TEST_DIR, 'fixtures/claude-transcript.jsonl');
  const session = { family: 'claude', transcriptPath: claudeFixture, terminalHandle: 'term_c1', stateDir };
  const dispatch = { dispatchId: 'D1', nonce: 'NONCE-ACTUAL' };

  const result = await awaitDone({ session, dispatch, reportPath: 'informe.md', root, deadlineMs: 1000 });

  assert.equal(result.code, 0);
  assert.match(fs.readFileSync(result.reportPath, 'utf8'), /NONCE-ACTUAL/);
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
    const dispatch = { dispatchId: 'D1', nonce: 'NONCE-ACTUAL' };

    const result = await awaitDone({
      session,
      dispatch,
      reportPath: 'informe.md',
      root,
      deadlineMs: 1000,
      sleep: instantSleep,
    });

    assert.equal(result.code, 0);
    assert.equal(session.transcriptPath, path.join(sessionsRoot, 'rollout-lazy-awaitdone.jsonl'));
    assert.match(fs.readFileSync(result.reportPath, 'utf8'), /NONCE-ACTUAL/);
  });
});

test('awaitDone (codex): el rollout nunca aparece -> code 4 (degradar a cli), sin cosechar', async () => {
  // Codex: el rollout aparece cuando arranca el turno. Si nunca aparece (aquí el sessions/ está
  // vacío), resolveCodexTranscript agota su presupuesto acotado por el deadline y awaitDone
  // devuelve code 4 (degradar a cli) sin llegar a harvest.
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
    const dispatch = { dispatchId: 'D1', nonce: 'NONCE-ACTUAL' };

    const result = await awaitDone({
      session,
      dispatch,
      reportPath: 'informe.md',
      root,
      deadlineMs: 1000, // acota el presupuesto de localización: ~5 intentos (1000/200) con sleep instantáneo.
      sleep: instantSleep,
    });

    assert.equal(result.code, 4);
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
    if (args.includes('--interrupt')) return okEnvelope({ sent: true });
    if (args[1] === 'wait') return okEnvelope({}); // idle confirmado = ok:true.
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
    if (args.includes('--interrupt')) return okEnvelope({ sent: true });
    if (args[1] === 'wait') return okEnvelope({}); // idle confirmado = ok:true.
    // Cierre fallido: ok:false. Ojo -- el CLI real devuelve exit 0 aun así para close, por eso
    // se usa exit:0 acá: prueba que el adaptador decide por `ok`, no por el code del proceso.
    if (args[1] === 'close') return errEnvelope('terminal_handle_stale', { exit: 0 });
    throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
  };

  const result = recover({ session, dispatch, orcaRunner: fakeOrcaRunner });

  assert.equal(result.recovered, false);
});

test('recover (write): idle confirmado y cierre exitoso -> recovered:true', () => {
  const session = { role: 'write', terminalHandle: 'term_1' };
  const dispatch = { taskId: 'T1', dispatchId: 'D1' };
  const fakeOrcaRunner = (args) => {
    if (args.includes('--interrupt')) return okEnvelope({ sent: true });
    if (args[1] === 'wait') return okEnvelope({}); // idle confirmado = ok:true.
    if (args[1] === 'close') return okEnvelope({ close: { handle: 'term_1', ptyKilled: true } });
    throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
  };

  const result = recover({ session, dispatch, orcaRunner: fakeOrcaRunner });

  assert.equal(result.recovered, true);
});

test('recover: idle NO confirmado -> recovered:false sin importar el rol', () => {
  const session = { role: 'read-only', terminalHandle: 'term_1' };
  const dispatch = { taskId: 'T1', dispatchId: 'D1' };
  const fakeOrcaRunner = (args) => {
    if (args.includes('--interrupt')) return okEnvelope({ sent: true });
    if (args[1] === 'wait') return errEnvelope('timeout'); // idle NO confirmado = ok:false (timeout).
    throw new Error(`orcaRunner inesperado: ${args.join(' ')}`);
  };

  const result = recover({ session, dispatch, orcaRunner: fakeOrcaRunner });

  assert.equal(result.recovered, false);
});
