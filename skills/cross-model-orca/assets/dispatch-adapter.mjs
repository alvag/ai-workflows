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

/**
 * Todo comando `orca ... --json` envuelve su salida en un envelope común:
 * `{ id, ok, result | error, _meta }` (verificado en vivo contra el CLI real —
 * ver `spikes/RESULTS.md`, Fase 7). El éxito NO se decide por el exit code del
 * proceso (es inconsistente: `terminal close` sobre un handle stale devuelve
 * `ok:false` pero exit 0), sino por `ok === true`. Estos dos helpers son el
 * único punto por el que el adaptador lee salidas de `orca`.
 * @param {*} parsed salida ya pasada por `parseJsonOutput`.
 * @returns {boolean}
 */
function orcaOk(parsed) {
  return parsed != null && parsed.ok === true;
}

/**
 * Devuelve `parsed.result` solo si el envelope es `ok`; si no, `null`.
 * @param {*} parsed
 * @returns {*}
 */
function orcaResult(parsed) {
  return orcaOk(parsed) ? (parsed.result ?? null) : null;
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

// Encabezados de sección `[mcp_servers.<name>]` (y subtablas `[mcp_servers.<name>.…]`) de
// config.toml, con <name> "bare" — el único que el parser de `-c` de Codex acepta. Verificado
// en vivo (0.144.6): `mcp_servers.engram.enabled=false` funciona; la variante quoted
// `mcp_servers."x".enabled=false` ROMPE la carga del config. Un nombre quoted en el config no
// matchea este patrón y se salta (tampoco sería overrideable).
const CODEX_MCP_SECTION_RE = /^\s*\[mcp_servers\.([A-Za-z0-9_-]+)[.\]]/;

/**
 * Enumera los MCP servers declarados en el `config.toml` de Codex (`configDir('codex')`,
 * que respeta `CODEX_HOME`). Es la fuente CORRECTA para armar overrides `-c
 * mcp_servers.<name>.enabled=false`: enumerar por `codex mcp list --json` fue una
 * regresión real — esa lista agrega servers que NO viven en config.toml (p. ej.
 * `sites-design-picker`, gestionado por la app), y deshabilitar uno de esos por `-c` crea
 * una entrada nueva sin transporte → "Error loading config.toml: invalid transport" → el
 * boot entero de Codex aborta (observado en vivo en el E2E). Los servers fuera del config
 * no se pueden apagar por override (quedan vivos: son builtins locales y rápidos); los del
 * config —los npx/pesados que cuelgan el boot— son exactamente los que este listado cubre.
 *
 * Best-effort: config ausente/ilegible devuelve `[]` y el launch sale sin overrides.
 * @returns {string[]} nombres únicos, en orden de aparición.
 */
export function listCodexConfigMcpServers() {
  let content;
  try {
    content = fs.readFileSync(path.join(configDir('codex'), 'config.toml'), 'utf8');
  } catch {
    return [];
  }
  const names = new Set();
  for (const line of content.split('\n')) {
    const match = line.match(CODEX_MCP_SECTION_RE);
    if (match) names.add(match[1]);
  }
  return [...names];
}

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
 * @param {string[]} [params.disableMcpServers] nombres de MCP servers de Codex a deshabilitar por override (solo rol read-only; ver `listCodexConfigMcpServers`).
 * @param {boolean} [params.windows] default `isWindows()`.
 * @returns {string}
 */
export function buildLaunchCommand({ family, role, mode, sessionId, installRoot, disableMcpServers = [], windows = isWindows() }) {
  if (family === 'claude') {
    const settingsPath = path.join(installRoot, 'launch', CLAUDE_SETTINGS_FILE[role]);
    const parts = [`--settings "${settingsPath}"`];
    if (role === 'read-only') {
      parts.push('--tools "Read,Grep,Glob"');
      // MCP off para read-only: sin superficie de ejecución. `--tools` cierra los built-ins (sin
      // Bash), pero NO las tools MCP — un Claude read-only con los MCP del entorno podía alcanzar
      // una tool MCP de ejecución (p. ej. la terminal del IDE del usuario) y correr comandos fuera
      // del worktree, gatillado por el `worker_done` que le pide el preamble de `dispatch --inject`
      // (hallazgo del E2E de Fase 7). Con `--strict-mcp-config` + un `--mcp-config` VACÍO, el
      // secundario no ve ningún MCP: read-only de verdad (solo Read/Grep/Glob), y ni siquiera puede
      // intentar el `worker_done`. Endurecimiento OPCIONAL: para habilitar un MCP de lectura,
      // declararlo entero en `claude-readonly.mcp.json` (con `--strict-mcp-config` no se hereda nada).
      const mcpConfigPath = path.join(installRoot, 'launch', 'claude-readonly.mcp.json');
      parts.push('--strict-mcp-config', `--mcp-config "${mcpConfigPath}"`);
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
    const sandbox = role === 'read-only' ? 'read-only' : 'workspace-write';
    const approval =
      role === 'read-only'
        ? mode === 'attended' ? 'untrusted' : 'never'
        : mode === 'attended' ? 'on-request' : 'never';
    // Rol read-only: MCP off por override dinámico, un `-c mcp_servers.<name>.enabled=false` por
    // server habilitado (hallazgo del caso real en Windows: la TUI de Codex quedaba colgada en
    // "MCP startup incomplete" arrancando los MCP del usuario — atlassian/figma/postman/Mongo — y
    // el primer turno nunca arrancaba, así que no había rollout que cosechar; `codex exec` no lo
    // sufre porque avanza pese a los MCP fallidos). Además da simetría con el read-only de Claude
    // (MCP off = sin superficie de ejecución fuera del sandbox). No existe una forma global:
    // `-c mcp_servers={}` NO vacía la lista (semántica de merge de TOML, verificado en vivo).
    // Rol write conserva los MCP con vigilancia manual (S3/Fase 5): el gate es el humano en la
    // TUI. Sin `-p` (endurecimiento OPCIONAL del caso desatendido, ver profiles.md), con
    // `features.apps=false` inline como garantía cero-config. Misma sintaxis en POSIX y
    // PowerShell: no hay prefijo de variables de entorno que traducir ni comillas en los args.
    const mcpOverrides =
      role === 'read-only'
        ? disableMcpServers.map((name) => ` -c mcp_servers.${name}.enabled=false`).join('')
        : '';
    return `codex -c features.apps=false${mcpOverrides} -s ${sandbox} -a ${approval} --disable hooks`;
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
  // Codex read-only: MCP off por override dinámico (ver buildLaunchCommand). Best-effort:
  // si la enumeración falla, la lista queda vacía y el launch sale sin overrides.
  const disableMcpServers =
    family === 'codex' && role === 'read-only' ? listCodexConfigMcpServers() : [];
  const createdAtMs = now();
  const command = buildLaunchCommand({ family, role, mode, sessionId: claudeSessionId, installRoot, disableMcpServers });

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
  // Forma real (verificada en vivo): `{ ok:true, result: { terminal: { handle, ... } } }`.
  const terminalHandle = orcaResult(createJson)?.terminal?.handle ?? null;
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
 * Este envelope (nonce + sentinel `STATUS: done`) es la ÚNICA señal de fin y de
 * correlación que usa el conductor: `harvest()` busca el mensaje del asistente con
 * este `nonce` (único por dispatch) en el transcript propio (ver
 * `selectAssistantByNonce`). No se depende de `worker_done` (ver `awaitDone`).
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

// Presupuesto para que el secundario recién creado bootee su TUI (Codex/Claude cargan MCP servers,
// modelo, etc.) y llegue a tui-idle antes de inyectarle la tarea. En el E2E de Fase 7 el boot de
// Codex (con arranque de MCP servers) tardó decenas de segundos; 120s da margen holgado.
const CREATE_DISPATCH_BOOT_TIMEOUT_MS = 120_000;

/**
 * Crea el task+dispatch de Orca para `session`, genera un `nonce` e inyecta las
 * instrucciones de cierre en el spec vía `dispatch --inject`. Persiste el registro
 * en `session.stateDir`. El `dispatchId` es parte de la clave de dedup de `awaitDone`.
 *
 * **Espera de boot (tui-idle) antes de inyectar.** El secundario recién creado está
 * booteando su TUI. Inyectar la tarea antes de que esté listo la pierde: el agente
 * queda idle en su prompt sin trabajar (verificado en el E2E de Fase 7 — Codex quedaba
 * en su placeholder). La guía de orquestación de Orca lo exige: esperar tui-idle antes
 * de `dispatch --inject`. Se bloquea hasta `bootTimeoutMs`; si no llega a idle, se lanza
 * (el llamador degrada a `cli`).
 *
 * **No se pasa `--from` (worker_done abandonado).** El preamble de `--inject` le pide al
 * worker mandar un `worker_done`, pero el E2E probó que un Codex sandboxeado no alcanza el
 * runtime de Orca para enviarlo (falla con "Orca is not running"). La detección de fin y
 * la autoridad las da el nonce del envelope en el transcript propio (ver `awaitDone`), no
 * `worker_done`. El intento de worker_done del secundario falla de forma inocua; no lo
 * ruteamos con `--from` porque no lo consumimos.
 *
 * @param {object} params
 * @param {object} params.session sesión devuelta por `createOwnedSession`.
 * @param {string} params.spec texto de la tarea (sin envelope: este helper lo agrega).
 * @param {string} params.root raíz autorizada del dispatch (se persiste como referencia; la usa `awaitDone`/`harvest`).
 * @param {number} [params.bootTimeoutMs] presupuesto de boot del secundario hasta tui-idle.
 * @param {(args: string[]) => { stdout: string, code: number }} [params.orcaRunner]
 * @returns {{ taskId: string, dispatchId: string, expectedAssignee: string, nonce: string }}
 */
export function createDispatch({
  session,
  spec,
  root,
  bootTimeoutMs = CREATE_DISPATCH_BOOT_TIMEOUT_MS,
  orcaRunner = defaultOrcaRunner,
}) {
  const nonce = randomUUID();
  const augmentedSpec = `${spec}\n\n${buildEnvelopeInstructions(nonce)}`;

  const taskCreateResult = orcaRunner(['orchestration', 'task-create', '--spec', augmentedSpec, '--json']);
  const taskJson = parseJsonOutput(taskCreateResult.stdout);
  // Forma real (verificada en vivo): `{ ok:true, result: { task: { id: "task_...", ... } } }`.
  const taskId = orcaResult(taskJson)?.task?.id ?? null;
  if (!taskId) {
    throw new Error('No se pudo obtener taskId de "orchestration task-create": salida inesperada.');
  }

  // Espera a que el secundario termine de bootear (tui-idle) antes de inyectar (ver docstring).
  // Éxito = ok:true; un timeout llega como ok:false (error.code:"timeout").
  const bootWait = orcaRunner([
    'terminal', 'wait', '--terminal', session.terminalHandle,
    '--for', 'tui-idle', '--timeout-ms', String(bootTimeoutMs), '--json',
  ]);
  if (!orcaOk(parseJsonOutput(bootWait.stdout))) {
    throw new Error(
      `El secundario no alcanzó tui-idle en ${bootTimeoutMs}ms tras crearse: inyectar ahora perdería el prompt (degradar a cli).`
    );
  }

  const dispatchResult = orcaRunner([
    'orchestration', 'dispatch', '--task', taskId, '--to', session.terminalHandle, '--inject', '--json',
  ]);
  const dispatchJson = parseJsonOutput(dispatchResult.stdout);
  // Forma real (verificada en vivo): `{ ok:true, result: { dispatch: { id: "ctx_...", ... }, injected } }`.
  const dispatchId = orcaResult(dispatchJson)?.dispatch?.id ?? null;
  if (!dispatchId) {
    throw new Error('No se pudo obtener dispatchId de "orchestration dispatch": salida inesperada.');
  }

  // Nudge de sumisión (hallazgo del caso real en Windows/ConPTY): `dispatch --inject` tipea el
  // prompt en el composer del TUI, pero la tecla de envío puede no llegar — el secundario queda
  // con el prompt pegado, sin someter, para siempre. Enter explícito (`terminal send --enter`,
  // sin `--text`; verificado en vivo: `ok:true, bytesWritten:1`): viaja por el MISMO stream del
  // PTY que el paste, así que llega ordenado DESPUÉS del prompt; y si el inject ya lo sometió
  // (macOS), cae en un composer vacío y es no-op. Best-effort: si falla, el inject pudo haber
  // sometido igual — no se aborta el dispatch por esto.
  try {
    orcaRunner(['terminal', 'send', '--terminal', session.terminalHandle, '--enter', '--json']);
  } catch {
    // best-effort (ver arriba).
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

// Presupuesto máximo para esperar a que el rollout de Codex APAREZCA (se escribe cuando arranca
// el turno). Es solo la espera de aparición; una vez localizado, harvest() consume el resto del
// deadline esperando el nonce+sentinel. Acotado además por el deadline real. 240s (antes 60s):
// el caso real en Windows mostró que la TUI puede alcanzar tui-idle (dispatch inyectado OK) y aun
// así demorar el PRIMER turno en la cola del arranque de MCP ("MCP startup incomplete", >90s) —
// con 60s el adaptador declaraba code 4 e interrumpía a un Codex que solo estaba booteando lento.
// El launch read-only ya apaga los MCP (boot rápido); este margen cubre el rol write, que los
// conserva por diseño (vigilancia manual).
const CODEX_LOCATE_BUDGET_MS = 240_000;

function hashFile(filePath) {
  return createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

/**
 * Espera el fin del turno del secundario y cosecha su informe del transcript propio.
 *
 * **Detección de fin = el nonce+sentinel del envelope en el transcript propio, NO
 * `worker_done`.** El E2E de Fase 7 (primer contacto con Orca real) demostró que un
 * secundario Codex sandboxeado NO puede reportar `worker_done`: dentro del sandbox
 * `read-only`, `ORCA_CLI_SOCKET`/`ORCA_RUNTIME_DIR` vienen vacíos y `orca ...` falla
 * con "Orca is not running" (el sandbox no alcanza el runtime). Codex sí completa la
 * tarea, cierra con el envelope `X-CMO: nonce=… / STATUS: done`, y su rollout queda
 * en disco — todo observable por el conductor (que no está sandboxeado). Por eso la
 * autoridad/correlación es el **nonce** (único por dispatch) dentro del transcript de
 * la **sesión propia** (terminal que creamos nosotros; para Codex, rollout localizado
 * por cwd+mtime+source y desambiguado a exactamente 1), el mismo modelo que Claude.
 * `harvest()` ya hace el poll del transcript con backoff hasta el deadline esperando
 * ese nonce+sentinel: es la detección de fin. No se consulta `orchestration check`
 * ni `tui-idle`.
 *
 * Codex: el rollout no existe hasta que arranca el turno (segundos tras el inject),
 * así que primero se lo localiza reintentando hasta que aparece, acotado por el
 * deadline (`resolveCodexTranscript`). Si nunca aparece (0 candidatos) o es ambiguo
 * (>1), se devuelve `code: 4` (degradar a `cli`) sin cosechar. Claude ya trae su
 * `transcriptPath` resuelto de `createOwnedSession`.
 *
 * Dedup: la clave durable es `${dispatchId}:${nonce}` (misma clave que usa la FSM de
 * `harvest-core.mjs`). Si ya está `promoted`, no se vuelve a cosechar. Crash-
 * idempotencia adicional: si un intento anterior escribió el reporte (`writeExclusive`)
 * pero cayó antes de `markPromoted`, el retry ve un `harvest()` con `code:2` cuyo
 * `reason` es `REPORT_ALREADY_EXISTS_REASON` (destino ya existente, no un escape de
 * contención real) — ese caso se trata como éxito idempotente (`code:0`) y auto-repara
 * la FSM.
 *
 * **Cierre del dispatch (reúso de sesión).** Tras una cosecha exitosa (`code:0`), completa
 * el dispatch en Orca (`orchestration task-update --id <taskId> --status completed`). Como
 * NO usamos `worker_done` (que lo completaría automáticamente), sin este cierre el dispatch
 * queda "active" y Orca rechaza un segundo dispatch a la MISMA terminal ("already has an
 * active dispatch") — el **reúso de sesión** (cross-review multi-ronda) fallaría (hallazgo
 * del E2E de Fase 7, caso c). Es **best-effort**: si el cierre falla, la cosecha sigue siendo
 * válida (solo se resentiría un reúso posterior). Requiere `dispatch.taskId`.
 *
 * @param {object} params
 * @param {object} params.session
 * @param {{ taskId?: string, dispatchId: string, nonce: string }} params.dispatch
 * @param {string} params.reportPath
 * @param {string} params.root
 * @param {number} params.deadlineMs
 * @param {(args: string[]) => { stdout: string, code: number }} [params.orcaRunner]
 * @param {() => number} [params.now]
 * @param {(ms: number) => Promise<void>} [params.sleep]
 * @returns {Promise<{ code: 0, reportPath: string } | { code: 2|3, reason: string } | { code: 4, reason: string }>}
 *   `code` 4: no se pudo localizar el rollout de Codex antes del deadline — degradar a `cli`.
 */

/**
 * Cierra el lifecycle del dispatch en Orca tras cosechar (ver docstring de `awaitDone` →
 * "Cierre del dispatch"). Best-effort: nunca lanza, y no hace nada si falta `taskId`.
 * @param {(args: string[]) => { stdout: string, code: number }} orcaRunner
 * @param {string|undefined} taskId
 */
function completeDispatchTask(orcaRunner, taskId) {
  if (!taskId) return;
  try {
    orcaRunner(['orchestration', 'task-update', '--id', taskId, '--status', 'completed', '--json']);
  } catch {
    // best-effort: la cosecha ya fue válida; un cierre fallido solo afecta un reúso posterior.
  }
}

export async function awaitDone({
  session,
  dispatch,
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
    // Ya cosechado en una corrida anterior (recuperación post-crash, o una segunda
    // invocación con el mismo dispatch+nonce): no reprocesar. El destino ya existe en
    // disco, así que ni siquiera intentamos invocar harvest() de nuevo.
    return { code: 0, reportPath: path.resolve(root, reportPath) };
  }

  const deadlineAt = now() + deadlineMs;

  // Codex: localizar el rollout, que aparece cuando arranca el turno (segundos tras el inject).
  // Se reintenta hasta que aparezca, acotado por una porción del deadline; si no aparece o es
  // ambiguo, degradar a cli (code 4). Claude ya trae su transcriptPath de createOwnedSession.
  if (session.family === 'codex' && !session.transcriptPath) {
    const locateBudgetMs = Math.max(0, Math.min(deadlineAt - now(), CODEX_LOCATE_BUDGET_MS));
    const maxAttempts = Math.max(1, Math.floor(locateBudgetMs / CODEX_LOCATOR_RETRY_MS));
    const resolved = await resolveCodexTranscript({ session, sleep, maxAttempts, retryDelayMs: CODEX_LOCATOR_RETRY_MS });
    if (resolved === null) {
      return {
        code: 4,
        reason: 'no se pudo localizar el rollout de Codex antes del deadline: degradar a cli',
      };
    }
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
    // (code 2) -- aunque en realidad la cosecha anterior fue exitosa. El reporte en disco proviene
    // de un harvest() previo del mismo dispatch+nonce (la clave de dedup): es legítimo. Lo tratamos
    // como éxito idempotente, no como rechazo, y re-marcamos la
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
    completeDispatchTask(orcaRunner, dispatch.taskId); // libera la terminal para el reúso de sesión.
    return { code: 0, reportPath: resolvedPath };
  }

  if (harvestResult.code !== 0) {
    return harvestResult;
  }

  fsm.markHarvested(dedupKey);
  fsm.markPromoted(dedupKey, hashFile(harvestResult.reportPath));
  completeDispatchTask(orcaRunner, dispatch.taskId); // libera la terminal para el reúso de sesión.

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
 * **`closeTerminal` (abandono, no redispatch).** Cuando el llamador NO va a
 * redespachar sobre la sesión sino a abandonarla (degradación a `cli`), pasar
 * `closeTerminal: true` cierra la terminal aunque el rol sea read-only — sin
 * esto, la degradación deja una terminal zombie abierta "sin hacer nada"
 * (observado en el caso real de Windows). Para rol write ya es el default. Con
 * `closeTerminal`, el cierre se intenta aunque idle no se confirme (se está
 * descartando la sesión; un cierre exitoso es estrictamente mejor que dejarla
 * viva) y `recovered` refleja el cierre demostrado.
 *
 * @param {object} params
 * @param {object} params.session
 * @param {object} params.dispatch (no se usa para decidir la recuperación en sí; se acepta por
 *   simetría de interfaz con `awaitDone`/`createDispatch` y por si el llamador necesita loguear
 *   qué dispatch se está recuperando).
 * @param {boolean} [params.closeTerminal] default `session.role === 'write'`.
 * @param {(args: string[]) => { stdout: string, code: number }} [params.orcaRunner]
 * @returns {{ recovered: boolean }}
 */
export function recover({ session, dispatch, closeTerminal = session.role === 'write', orcaRunner = defaultOrcaRunner }) {
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
  // Idle confirmado = `ok:true` (el timeout llega como `ok:false, error.code:"timeout"`).
  const idleConfirmed = orcaOk(parseJsonOutput(idleResult.stdout));

  if (!closeTerminal) {
    // Read-only sin abandono: idle confirmado alcanza para habilitar el redispatch.
    return { recovered: idleConfirmed };
  }

  // Cierre demostrado = `ok:true`. El exit code del proceso NO sirve acá: `terminal close`
  // sobre un handle stale devuelve `ok:false` pero exit 0 (verificado en vivo). Un cierre
  // fallido deja `ok:false` (`error.code:"terminal_handle_stale"` u otro) → no se habilita el
  // redispatch en rol write (no se demostró que el escritor anterior no vaya a volver a escribir).
  const closeResult = orcaRunner(['terminal', 'close', '--terminal', session.terminalHandle, '--json']);
  const closed = orcaOk(parseJsonOutput(closeResult.stdout));

  return { recovered: closed };
}
