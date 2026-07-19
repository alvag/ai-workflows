// Orquestador del lado del conductor para el transporte cross-model vía Orca.
// Crea la sesión secundaria fresca y captura su locator (createOwnedSession),
// despacha la tarea con un nonce (createDispatch), espera el fin del turno y
// valida la autoridad antes de invocar la cosecha (awaitDone, Task 1.3) y
// recupera ante fallos sin habilitar un doble escritor (recover).
//
// Principio de testeabilidad: este módulo NUNCA ejecuta `orca` directamente en
// su lógica. Toda invocación pasa por un `orcaRunner` inyectable — por default
// ejecuta el binario real vía child_process, pero los tests inyectan uno falso
// que devuelve JSON fijo. El reloj (`now`) y el `sleep` también son
// inyectables. Esto no es mockear el sistema bajo test: es inyectar la
// dependencia de proceso externo (Orca) para poder testear la lógica de
// coordinación de verdad, sin una instancia de Orca viva.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { randomUUID, createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { makeDedupFsm, REPORT_ALREADY_EXISTS_REASON } from './harvest-core.mjs';
import { harvest } from './harvest-from-transcript.mjs';
import { configDir, isWindows, resolveInstallRoot } from './lib/platform.mjs';

// ---------------------------------------------------------------------------
// orcaRunner / reloj / sleep por default
// ---------------------------------------------------------------------------

/**
 * Ejecuta el binario `orca` real. Default de `orcaRunner` para todas las
 * funciones públicas de este módulo.
 * @param {string[]} args
 * @returns {{ stdout: string, code: number }}
 */
function defaultOrcaRunner(args) {
  const result = spawnSync('orca', args, { encoding: 'utf8' });
  return { stdout: result.stdout ?? '', code: result.status ?? 1 };
}

/**
 * @param {number} ms
 * @returns {Promise<void>}
 */
function defaultSleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Parsea `stdout` como JSON sin lanzar nunca: una salida vacía, no-JSON o de
 * un `orcaRunner` fallado devuelve `null` y el llamador decide qué hacer.
 * @param {string} stdout
 * @returns {*}
 */
function parseJsonOutput(stdout) {
  if (typeof stdout !== 'string' || stdout.trim() === '') return null;
  try {
    return JSON.parse(stdout);
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// stateDir: registro de sesiones/dispatches, conductor-only, fuera de worktrees
// ---------------------------------------------------------------------------

/**
 * Default sensato de `stateDir`: bajo el home del conductor, nunca dentro de
 * un worktree que el secundario pueda escribir.
 * @returns {string}
 */
function defaultStateDir() {
  return path.join(os.homedir(), '.cross-model-orca-state');
}

function writeJsonAtomic(filePath, data) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tmpPath = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tmpPath, JSON.stringify(data, null, 2));
  fs.renameSync(tmpPath, filePath);
}

function readJsonOrEmpty(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return {};
  }
}

function persistSessionRecord(stateDir, session) {
  const filePath = path.join(stateDir, 'sessions.json');
  const state = readJsonOrEmpty(filePath);
  state[session.uid] = {
    uid: session.uid,
    terminalHandle: session.terminalHandle,
    family: session.family,
    role: session.role,
    mode: session.mode,
    sessionId: session.sessionId,
    transcriptPath: session.transcriptPath,
    createdAt: session.createdAt,
  };
  writeJsonAtomic(filePath, state);
}

function persistDispatchRecord(stateDir, dispatch) {
  const filePath = path.join(stateDir, 'dispatches.json');
  const state = readJsonOrEmpty(filePath);
  state[dispatch.dispatchId] = { ...dispatch };
  writeJsonAtomic(filePath, state);
}

// ---------------------------------------------------------------------------
// Comando de lanzamiento por family+role+mode (referencia los perfiles de
// assets/launch/ por nombre; no los parsea).
// ---------------------------------------------------------------------------

const CLAUDE_SETTINGS_FILE = {
  'read-only': 'claude-readonly.settings.json',
  write: 'claude-write.settings.json',
};

/**
 * Construye el comando de lanzamiento del perfil family+role+mode, referenciando
 * por nombre los perfiles de `assets/launch/` (ver `profiles.md`). No incluye el
 * prompt/work-order: la terminal se crea "en frío" y `createDispatch` inyecta la
 * tarea después vía `orchestration dispatch --inject`.
 *
 * POSIX (`windows:false`, default en macOS/Linux) usa `VAR=1 cmd ...`; Windows usa
 * el equivalente PowerShell `$env:VAR = "1"; cmd ...` en una sola línea (es el valor
 * de `--command` de `terminal create`, así que tiene que ser un one-liner). Codex no
 * necesita esta distinción: su comando no antepone variables de entorno.
 *
 * @param {object} params
 * @param {'codex'|'claude'} params.family
 * @param {'read-only'|'write'} params.role
 * @param {'attended'|'unattended'} params.mode atendido/desatendido (ver `profiles.md`).
 * @param {string|null} params.sessionId uuid fijado para Claude; ignorado para Codex.
 * @param {string} params.installRoot raíz de instalación del skill (`resolveInstallRoot()`); solo se usa para Claude.
 * @param {boolean} [params.windows] default `isWindows()`.
 * @returns {string}
 */
export function buildLaunchCommand({ family, role, mode, sessionId, installRoot, windows = isWindows() }) {
  if (family === 'claude') {
    const settingsPath = path.join(installRoot, 'launch', CLAUDE_SETTINGS_FILE[role]);
    const parts = [`--settings "${settingsPath}"`];
    if (role === 'read-only') {
      parts.push('--tools "Read,Grep,Glob"');
    } else {
      parts.push(`--permission-mode ${mode === 'attended' ? 'manual' : 'dontAsk'}`);
    }
    parts.push(`--session-id "${sessionId}"`);
    const claudeInvocation = `claude ${parts.join(' ')}`;
    return windows
      ? `$env:DISABLE_AUTOUPDATER = "1"; ${claudeInvocation}`
      : `DISABLE_AUTOUPDATER=1 ${claudeInvocation}`;
  }

  if (family === 'codex') {
    const profile = role === 'read-only' ? 'cmo-readonly' : 'cmo-write';
    const sandbox = role === 'read-only' ? 'read-only' : 'workspace-write';
    const approval =
      role === 'read-only'
        ? mode === 'attended' ? 'untrusted' : 'never'
        : mode === 'attended' ? 'on-request' : 'never';
    // Misma sintaxis en POSIX y PowerShell: no hay prefijo de variables de entorno que traducir.
    return `codex -p ${profile} -s ${sandbox} -a ${approval} --disable hooks`;
  }

  throw new Error(`Familia desconocida: "${family}". Los valores válidos son "codex" o "claude".`);
}

// ---------------------------------------------------------------------------
// Locator Codex: creación + cwd + timestamp (ver spikes/RESULTS.md, Task 0.1)
// ---------------------------------------------------------------------------

const ROLLOUT_FILENAME_RE = /^rollout-.*\.jsonl$/;
const HEAD_READ_BYTES = 8192;

function listRolloutFiles(rootDir) {
  const results = [];
  let entries;
  try {
    entries = fs.readdirSync(rootDir, { withFileTypes: true });
  } catch {
    return results;
  }
  for (const entry of entries) {
    const fullPath = path.join(rootDir, entry.name);
    if (entry.isDirectory()) {
      results.push(...listRolloutFiles(fullPath));
    } else if (entry.isFile() && ROLLOUT_FILENAME_RE.test(entry.name)) {
      results.push(fullPath);
    }
  }
  return results;
}

function matchField(line, key) {
  const match = line.match(new RegExp(`"${key}":"((?:[^"\\\\]|\\\\.)*)"`));
  return match ? match[1] : null;
}

/**
 * Lee solo los primeros `HEAD_READ_BYTES` de la primera línea del rollout y
 * extrae session_id/cwd/source/originator por regex, sin `JSON.parse` de la
 * línea completa (que puede traer `base_instructions.text` con el system
 * prompt entero — ver `spikes/RESULTS.md`, Task 0.1).
 * @param {string} filePath
 * @returns {{ sessionId: string, cwd: string, source: string, originator: string }|null}
 */
function readRolloutHeadMeta(filePath) {
  let fd;
  try {
    fd = fs.openSync(filePath, 'r');
  } catch {
    return null;
  }
  try {
    const buffer = Buffer.alloc(HEAD_READ_BYTES);
    const bytesRead = fs.readSync(fd, buffer, 0, HEAD_READ_BYTES, 0);
    const head = buffer.toString('utf8', 0, bytesRead);
    const newlineIdx = head.indexOf('\n');
    const firstLine = newlineIdx === -1 ? head : head.slice(0, newlineIdx);
    const sessionId = matchField(firstLine, 'session_id');
    const cwd = matchField(firstLine, 'cwd');
    const source = matchField(firstLine, 'source');
    const originator = matchField(firstLine, 'originator');
    if (!sessionId || !cwd || !source || !originator) return null;
    return { sessionId, cwd, source, originator };
  } catch {
    return null;
  } finally {
    fs.closeSync(fd);
  }
}

/**
 * Localiza el rollout de Codex de la sesión recién creada: interactivo
 * (`source:"cli"`/`originator:"codex-tui"`), mismo `cwd` que el worktree, y
 * `mtime` posterior a `afterMs` (el instante de creación de la terminal).
 * Si hay **más de un** candidato en esa ventana, el locator es ambiguo →
 * devuelve `null` (la skill llamadora degrada a `cli`).
 * @param {object} params
 * @param {string} params.sessionsRoot `<configDir('codex')>/sessions`.
 * @param {string} params.cwd
 * @param {number} params.afterMs
 * @returns {{ path: string, sessionId: string }|null}
 */
export function locateCodexRollout({ sessionsRoot, cwd, afterMs }) {
  const candidates = [];
  for (const filePath of listRolloutFiles(sessionsRoot)) {
    let stat;
    try {
      stat = fs.statSync(filePath);
    } catch {
      continue;
    }
    if (stat.mtimeMs <= afterMs) continue;
    const meta = readRolloutHeadMeta(filePath);
    if (!meta) continue;
    if (meta.source !== 'cli' || meta.originator !== 'codex-tui') continue;
    if (meta.cwd !== cwd) continue;
    candidates.push({ path: filePath, sessionId: meta.sessionId });
  }
  if (candidates.length !== 1) return null;
  return candidates[0];
}

/**
 * Reproduce el slug que Claude Code arma a partir de `cwd` para el nombre del
 * directorio bajo `<configDir('claude')>/projects/`: reemplaza **todo**
 * carácter no alfanumérico (no solo `/`) por `-`, preservando los guiones ya
 * existentes. Verificado contra dos directorios reales de proyecto:
 * `/Users/max/Personal/repos/ai-workflows` → `-Users-max-Personal-repos-ai-workflows`
 * (los guiones de "ai-workflows" se preservan) y `/Users/max/.claude` →
 * `-Users-max--claude` (el `/.` se vuelve `--`, dos reemplazos consecutivos).
 * Un `slugifyCwd` que solo reemplazara `/` (versión anterior, con bug) dejaría
 * el `.` literal en el slug para cualquier worktree con un punto en el path →
 * `transcriptPath` apuntaría a un directorio inexistente → timeout silencioso
 * en `harvest` (hallazgo del final review de Fase 1).
 * @param {string} cwd
 * @returns {string}
 */
function slugifyCwd(cwd) {
  return cwd.replace(/[^a-zA-Z0-9-]/g, '-');
}

// ---------------------------------------------------------------------------
// createOwnedSession
// ---------------------------------------------------------------------------

/**
 * Crea la sesión secundaria fresca (terminal Orca) y captura su locator de
 * transcript/rollout donde ya se puede (Claude, directo). Registra la sesión
 * en `stateDir` (conductor-only, fuera de cualquier worktree que el
 * secundario pueda escribir).
 *
 * **Codex: el locator es diferido (lazy), no se resuelve acá.** Verificado en
 * vivo (`spikes/RESULTS.md`, Task 0.1, "TIMING del rollout"): el rollout de
 * Codex NO existe al arrancar la terminal — se escribe recién en el primer
 * turno, tras el primer `dispatch --inject`. Si `createOwnedSession`
 * intentara localizarlo acá, siempre encontraría 0 candidatos y devolvería
 * `null`, degradando el transporte a `cli` siempre para Codex (bug real,
 * encontrado en el review de esta task). Por eso, para Codex esta función
 * registra la sesión con `transcriptPath: null` y `sessionId: null`, y
 * devuelve la sesión normalmente (nunca `null` por esto); `resolveCodexTranscript`
 * hace la resolución diferida más adelante (ver esa función).
 *
 * @param {object} params
 * @param {'codex'|'claude'} params.family
 * @param {'read-only'|'write'} params.role
 * @param {'attended'|'unattended'} params.mode
 * @param {string} params.worktree ruta absoluta del worktree (se usa como selector `path:<worktree>` de Orca y, para Codex, como `cwd` a matchear contra el rollout).
 * @param {(args: string[]) => { stdout: string, code: number }} [params.orcaRunner]
 * @param {() => number} [params.now]
 * @param {string} [params.stateDir]
 * @returns {{ session: object } | null} `null` solo si no se pudo crear la terminal / leer su handle.
 */
export function createOwnedSession({
  family,
  role,
  mode,
  worktree,
  orcaRunner = defaultOrcaRunner,
  now = Date.now,
  stateDir = defaultStateDir(),
}) {
  if (family !== 'codex' && family !== 'claude') {
    throw new Error(`Familia desconocida: "${family}". Los valores válidos son "codex" o "claude".`);
  }

  const uid = randomUUID();
  const claudeSessionId = family === 'claude' ? randomUUID() : null;
  const installRoot = family === 'claude' ? resolveInstallRoot() : null;
  const createdAtMs = now();
  const command = buildLaunchCommand({ family, role, mode, sessionId: claudeSessionId, installRoot });

  const createArgs = [
    'terminal',
    'create',
    '--worktree',
    `path:${worktree}`,
    '--title',
    `cmo-${family}-${role}-${uid.slice(0, 8)}`,
    '--command',
    command,
    '--json',
  ];
  const createResult = orcaRunner(createArgs);
  const createJson = parseJsonOutput(createResult.stdout);
  const terminalHandle = createJson?.handle ?? createJson?.terminal?.handle ?? null;
  if (!terminalHandle) return null; // no se pudo crear la terminal / leer su handle: no hay sesión que registrar.

  let sessionId;
  let transcriptPath;
  if (family === 'claude') {
    // Locator directo e inequívoco: el session-id lo fijamos nosotros con --session-id.
    sessionId = claudeSessionId;
    transcriptPath = path.join(configDir('claude'), 'projects', slugifyCwd(worktree), `${sessionId}.jsonl`);
  } else {
    // Codex: el rollout todavía no existe (ver docstring de esta función). Queda pendiente;
    // `resolveCodexTranscript` lo resuelve más adelante, cuando ya arrancó el primer turno.
    sessionId = null;
    transcriptPath = null;
  }

  const session = {
    uid,
    family,
    role,
    mode,
    worktree,
    terminalHandle,
    sessionId,
    transcriptPath,
    createdAt: createdAtMs,
    stateDir,
  };

  persistSessionRecord(stateDir, session);
  return { session };
}

// ---------------------------------------------------------------------------
// createDispatch
// ---------------------------------------------------------------------------

/**
 * Instruye al secundario a cerrar su último mensaje con el envelope de nonce.
 * `harvest()` (Task 1.3) solo necesita el `nonce` para desambiguar (ver
 * `selectAssistantByNonce`); `taskId`/`dispatchId` viajan por el canal de
 * `worker_done` (payload de la orquestación), no por este envelope de texto.
 * @param {string} nonce
 * @returns {string}
 */
function buildEnvelopeInstructions(nonce) {
  return (
    'Al terminar esta tarea, cierra tu último mensaje exactamente con estas dos líneas finales, ' +
    'en este orden y sin texto adicional después:\n' +
    `X-CMO: nonce=${nonce}\n` +
    'STATUS: done'
  );
}

/**
 * Crea el task+dispatch de Orca para `session`, genera un `nonce` e inyecta las
 * instrucciones de cierre en el spec. Persiste el registro en `session.stateDir`.
 *
 * @param {object} params
 * @param {object} params.session sesión devuelta por `createOwnedSession`.
 * @param {string} params.spec texto de la tarea (sin envelope: este helper lo agrega).
 * @param {string} params.root raíz autorizada del dispatch (se persiste como referencia; la usa `awaitDone`/`harvest`).
 * @param {(args: string[]) => { stdout: string, code: number }} [params.orcaRunner]
 * @returns {{ taskId: string, dispatchId: string, expectedAssignee: string, nonce: string }}
 */
export function createDispatch({ session, spec, root, orcaRunner = defaultOrcaRunner }) {
  const nonce = randomUUID();
  const augmentedSpec = `${spec}\n\n${buildEnvelopeInstructions(nonce)}`;

  const taskCreateResult = orcaRunner(['orchestration', 'task-create', '--spec', augmentedSpec, '--json']);
  const taskJson = parseJsonOutput(taskCreateResult.stdout);
  const taskId = taskJson?.taskId ?? taskJson?.task_id ?? taskJson?.id ?? null;
  if (!taskId) {
    throw new Error('No se pudo obtener taskId de "orchestration task-create": salida inesperada.');
  }

  const dispatchResult = orcaRunner([
    'orchestration',
    'dispatch',
    '--task',
    taskId,
    '--to',
    session.terminalHandle,
    '--inject',
    '--json',
  ]);
  const dispatchJson = parseJsonOutput(dispatchResult.stdout);
  const dispatchId = dispatchJson?.dispatchId ?? dispatchJson?.dispatch_id ?? dispatchJson?.id ?? null;
  if (!dispatchId) {
    throw new Error('No se pudo obtener dispatchId de "orchestration dispatch": salida inesperada.');
  }
  // El assignee es la terminal secundaria a la que acabamos de despachar: ya lo sabemos
  // (se lo pasamos nosotros mismos vía --to), no hace falta parsearlo del JSON de vuelta.
  const expectedAssignee = session.terminalHandle;

  const dispatch = { taskId, dispatchId, expectedAssignee, nonce, sessionRef: session.uid, root };
  persistDispatchRecord(session.stateDir, dispatch);
  return { taskId, dispatchId, expectedAssignee, nonce };
}

// ---------------------------------------------------------------------------
// resolveCodexTranscript: resolución LAZY del locator de Codex (post-dispatch)
// ---------------------------------------------------------------------------

const CODEX_LOCATOR_MAX_ATTEMPTS = 3;
const CODEX_LOCATOR_RETRY_MS = 200;

/**
 * Resuelve, de forma diferida y con reintentos acotados, el rollout de Codex
 * de `session`. Se invoca desde `awaitDone` (no desde `createOwnedSession`):
 * el rollout recién existe tras el primer turno del secundario, así que
 * intentar resolverlo en el momento de crear la terminal siempre falla (ver
 * `spikes/RESULTS.md`, Task 0.1, "TIMING del rollout").
 *
 * No participa `orcaRunner` acá: `locateCodexRollout` es una operación pura de
 * filesystem, no invoca `orca` en ningún paso — no hay proceso externo que
 * inyectar en esta función, solo tiempo (de ahí el `sleep` inyectable).
 *
 * Reglas de resultado: si en algún intento hay exactamente 1 candidato, lo
 * persiste en `session` (`transcriptPath`/`sessionId`) y en el registro de
 * `stateDir`, y lo devuelve. Si tras `maxAttempts` intentos sigue sin haber
 * exactamente 1 candidato (0 — el rollout aún no se flushó — o >1 —
 * ambiguo), devuelve `null`: el llamador (`awaitDone`) degrada a `cli`.
 *
 * Idempotente: si `session.transcriptPath` ya está resuelto (una llamada
 * anterior lo encontró, o es Claude y ya lo trae de `createOwnedSession`), no
 * vuelve a tocar el filesystem ni a dormir — devuelve el valor ya conocido.
 *
 * @param {object} params
 * @param {object} params.session sesión (se muta si resuelve: `transcriptPath`/`sessionId`).
 * @param {(ms: number) => Promise<void>} [params.sleep]
 * @param {number} [params.maxAttempts]
 * @param {number} [params.retryDelayMs]
 * @returns {Promise<string|null>}
 */
export async function resolveCodexTranscript({
  session,
  sleep = defaultSleep,
  maxAttempts = CODEX_LOCATOR_MAX_ATTEMPTS,
  retryDelayMs = CODEX_LOCATOR_RETRY_MS,
}) {
  if (session.family !== 'codex') return session.transcriptPath ?? null; // Claude ya lo resolvió directo.
  if (session.transcriptPath) return session.transcriptPath; // ya resuelto: no reprocesar.

  const sessionsRoot = path.join(configDir('codex'), 'sessions');
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const located = locateCodexRollout({ sessionsRoot, cwd: session.worktree, afterMs: session.createdAt });
    if (located !== null) {
      session.transcriptPath = located.path;
      session.sessionId = located.sessionId;
      persistSessionRecord(session.stateDir, session);
      return located.path;
    }
    if (attempt < maxAttempts) {
      await sleep(retryDelayMs);
    }
  }
  return null; // 0 candidatos (aún no flushó) o ambiguo tras los reintentos: degradar a cli.
}

// ---------------------------------------------------------------------------
// awaitDone
// ---------------------------------------------------------------------------

const AWAIT_POLL_INITIAL_MS = 50;
const AWAIT_POLL_MAX_MS = 1000;

function hashFile(filePath) {
  return createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

/**
 * Busca, en la respuesta de `orchestration check`, un `worker_done` cuyo
 * `payload.taskId`/`payload.dispatchId` coincidan con `dispatch`. Autoridad de
 * tarea: Orca garantiza que un `worker_done` con el task/dispatch activos solo
 * completa desde el pane assignee (ver `spikes/RESULTS.md`, Task 0.2, "Matiz
 * para el adaptador"). Si el mensaje además expone el handle del sender, se
 * compara contra `expectedAssignee` como mejor esfuerzo; si no lo expone, no
 * bloquea por eso (la garantía de Orca + los IDs alcanzan para v1).
 * @param {object} params
 * @returns {{ authorized: boolean }}
 */
function checkWorkerDoneAuthority({ orcaRunner, coordinatorHandle, dispatch }) {
  const result = orcaRunner(['orchestration', 'check', '--terminal', coordinatorHandle, '--all', '--json']);
  const parsed = parseJsonOutput(result.stdout);
  const messages = Array.isArray(parsed?.messages) ? parsed.messages : Array.isArray(parsed) ? parsed : [];

  for (const msg of messages) {
    if (msg?.type !== 'worker_done') continue;
    const payload = msg.payload ?? {};
    if (payload.taskId !== dispatch.taskId || payload.dispatchId !== dispatch.dispatchId) continue;

    const sender = msg.from ?? msg.sender ?? msg.senderHandle ?? null;
    if (sender !== null && sender !== dispatch.expectedAssignee) continue;

    return { authorized: true };
  }
  return { authorized: false };
}

/**
 * Espera el fin del turno del secundario, valida autoridad y cosecha.
 *
 * Detección de fin: Codex señaliza `worker_done` por comando (autoridad =
 * `taskId`/`dispatchId` del payload, ver `checkWorkerDoneAuthority`). Claude no
 * emite `worker_done` por diseño (`spikes/RESULTS.md`, Task 0.3): su sesión es
 * exclusiva (nosotros fijamos el `--session-id`, así que el transcript solo
 * puede contener mensajes de esa sesión) y `harvest()` desambigua además por
 * `nonce`, así que para esa familia "fin del turno" (`terminal wait --for
 * tui-idle`) ya es autoridad suficiente. Para Codex, `tui-idle` NO sustituye la
 * validación de `worker_done`: solo se consulta para Claude.
 *
 * Dedup: la clave durable es `${dispatchId}:${nonce}` (misma clave que usa la
 * FSM de `harvest-core.mjs`). Si ya está `promoted`, no se vuelve a invocar
 * `harvest` — nunca se procesa dos veces el mismo dispatch+nonce. Crash-
 * idempotencia adicional: si un intento anterior escribió el reporte
 * (`writeExclusive`) pero cayó antes de `markPromoted`, el retry ve un
 * `harvest()` con `code:2` cuyo `reason` es exactamente
 * `REPORT_ALREADY_EXISTS_REASON` (destino ya existente, no un escape de
 * contención real) — ese caso se trata como éxito idempotente (`code:0`), no
 * como rechazo, y de paso auto-repara una FSM corrupta/perdida.
 *
 * Codex además necesita resolver el locator del rollout de forma diferida
 * (ver `resolveCodexTranscript`): si `session.transcriptPath` todavía no está
 * resuelto al entrar acá, se reintenta un número acotado de veces antes de
 * empezar el poll de `worker_done`. Si tras esos reintentos sigue sin
 * resolverse (0 candidatos — el rollout aún no se flushó — o >1, ambiguo),
 * esta función devuelve `code: 4` **sin** haber tocado la FSM ni haber
 * consultado `orchestration check` — es la señal explícita de "degradar a
 * cli" que debe interpretar la skill llamadora.
 *
 * @param {object} params
 * @param {object} params.session
 * @param {{ taskId: string, dispatchId: string, expectedAssignee: string, nonce: string }} params.dispatch
 * @param {string} params.coordinatorHandle terminal del conductor donde llega el `worker_done`.
 * @param {string} params.reportPath
 * @param {string} params.root
 * @param {number} params.deadlineMs
 * @param {(args: string[]) => { stdout: string, code: number }} [params.orcaRunner]
 * @param {() => number} [params.now]
 * @param {(ms: number) => Promise<void>} [params.sleep]
 * @returns {Promise<{ code: 0, reportPath: string } | { code: 2|3, reason: string } | { code: 4, reason: string }>}
 *   `code` 4: no se pudo resolver el locator de Codex tras los reintentos acotados — degradar a `cli`.
 */
export async function awaitDone({
  session,
  dispatch,
  coordinatorHandle,
  reportPath,
  root,
  deadlineMs,
  orcaRunner = defaultOrcaRunner,
  now = Date.now,
  sleep = defaultSleep,
}) {
  const dedupKey = `${dispatch.dispatchId}:${dispatch.nonce}`;
  const fsm = makeDedupFsm(path.join(session.stateDir, 'dedup-fsm.json'));

  if (fsm.isPromoted(dedupKey)) {
    // Ya cosechado en una corrida anterior (recuperación post-crash, o un
    // segundo worker_done idéntico llegando después): no reprocesar. El
    // destino ya existe en disco, así que ni siquiera intentamos invocar
    // harvest() de nuevo (checkContainment lo rechazaría por "ya existe").
    return { code: 0, reportPath: path.resolve(root, reportPath) };
  }

  if (session.family === 'codex' && !session.transcriptPath) {
    const resolved = await resolveCodexTranscript({ session, sleep });
    if (resolved === null) {
      return {
        code: 4,
        reason: 'no se pudo localizar el rollout de Codex tras los reintentos acotados: degradar a cli',
      };
    }
  }

  const deadlineAt = now() + deadlineMs;
  let waitMs = AWAIT_POLL_INITIAL_MS;
  let authorized = false;

  while (!authorized) {
    const authResult = checkWorkerDoneAuthority({ orcaRunner, coordinatorHandle, dispatch });
    if (authResult.authorized) {
      authorized = true;
      break;
    }

    if (session.family === 'claude') {
      const idleResult = orcaRunner([
        'terminal',
        'wait',
        '--terminal',
        session.terminalHandle,
        '--for',
        'tui-idle',
        '--timeout-ms',
        '0',
        '--json',
      ]);
      const idleJson = parseJsonOutput(idleResult.stdout);
      if (idleJson?.satisfied === true) {
        authorized = true;
        break;
      }
    }

    if (now() >= deadlineAt) {
      return { code: 3, reason: 'timeout esperando fin de turno autorizado (worker_done/tui-idle)' };
    }
    await sleep(Math.min(waitMs, Math.max(0, deadlineAt - now())));
    waitMs = Math.min(waitMs * 2, AWAIT_POLL_MAX_MS);
  }

  fsm.markReceived(dedupKey);

  const remainingMs = Math.max(0, deadlineAt - now());
  const harvestResult = await harvest({
    family: session.family,
    transcriptPath: session.transcriptPath,
    nonce: dispatch.nonce,
    reportPath,
    root,
    deadlineMs: remainingMs,
    now,
  });

  if (harvestResult.code === 2 && harvestResult.reason === REPORT_ALREADY_EXISTS_REASON) {
    // Hueco de crash-idempotencia (hallazgo del final review de Fase 1): si el proceso cae
    // DESPUÉS de que harvest() ya escribió el reporte (writeExclusive) pero ANTES de
    // markPromoted, el retry llega hasta acá (isPromoted seguía en false al entrar) y vuelve a
    // invocar harvest(), que ahora ve el destino ya existente y lo reporta como contención
    // (code 2) -- aunque en realidad la cosecha anterior fue exitosa. Como ya pasamos la
    // validación de autoridad de este mismo dispatch+nonce (arriba, en el loop), el reporte en
    // disco es legítimo: lo tratamos como éxito idempotente, no como rechazo, y re-marcamos la
    // FSM (esto también autorepara una FSM corrupta que hubiera perdido su estado). Un rechazo
    // real por escape (".."/absoluta/symlink/root inválido) tiene un `reason` DISTINTO (ver
    // checkContainment en harvest-core.mjs) y no entra en esta rama.
    let resolvedPath;
    try {
      resolvedPath = path.resolve(fs.realpathSync(root), reportPath);
    } catch {
      resolvedPath = path.resolve(root, reportPath);
    }
    fsm.markHarvested(dedupKey);
    fsm.markPromoted(dedupKey, hashFile(resolvedPath));
    return { code: 0, reportPath: resolvedPath };
  }

  if (harvestResult.code !== 0) {
    return harvestResult;
  }

  fsm.markHarvested(dedupKey);
  fsm.markPromoted(dedupKey, hashFile(harvestResult.reportPath));

  return harvestResult;
}

// ---------------------------------------------------------------------------
// recover
// ---------------------------------------------------------------------------

const RECOVER_IDLE_TIMEOUT_MS = 30_000;

/**
 * Orca no cancela un dispatch en curso: para recuperar ante un fallo hay que
 * interrumpir al secundario y confirmar que quedó idle antes de habilitar el
 * redispatch. Para rol **write**, interrumpir + idle NO alcanza (no demuestra
 * que el escritor anterior no vaya a volver a escribir) — solo se habilita el
 * redispatch si se demuestra el cierre real de la terminal (`terminal close`
 * exitoso). Para rol read-only, no hay riesgo de doble escritor: idle
 * confirmado alcanza.
 *
 * @param {object} params
 * @param {object} params.session
 * @param {object} params.dispatch (no se usa para decidir la recuperación en sí; se acepta por
 *   simetría de interfaz con `awaitDone`/`createDispatch` y por si el llamador necesita loguear
 *   qué dispatch se está recuperando).
 * @param {(args: string[]) => { stdout: string, code: number }} [params.orcaRunner]
 * @returns {{ recovered: boolean }}
 */
export function recover({ session, dispatch, orcaRunner = defaultOrcaRunner }) {
  void dispatch; // ver nota de interfaz arriba: no participa en la decisión de recuperación.

  orcaRunner(['terminal', 'send', '--terminal', session.terminalHandle, '--interrupt', '--json']);

  const idleResult = orcaRunner([
    'terminal',
    'wait',
    '--terminal',
    session.terminalHandle,
    '--for',
    'tui-idle',
    '--timeout-ms',
    String(RECOVER_IDLE_TIMEOUT_MS),
    '--json',
  ]);
  const idleJson = parseJsonOutput(idleResult.stdout);
  const idleConfirmed = idleJson?.satisfied === true;

  if (!idleConfirmed) {
    return { recovered: false };
  }

  if (session.role !== 'write') {
    return { recovered: true };
  }

  const closeResult = orcaRunner(['terminal', 'close', '--terminal', session.terminalHandle, '--json']);
  const closeJson = parseJsonOutput(closeResult.stdout);
  const closed = closeResult.code === 0 && closeJson?.error === undefined;

  return { recovered: closed };
}
