// Entrypoint del transporte `orca-session`: UN comando que el conductor corre
// para delegar una tarea a una sesión fresca de la otra familia vía Orca, y que
// encadena el flujo completo del adaptador —createOwnedSession → createDispatch →
// awaitDone— con la MISMA degradación a `cli` que documenta cada skill llamadora.
//
// Por qué existe: `dispatch-adapter.mjs` expone funciones (librería), no un
// comando. Sin este runner, el conductor tendría que ESCRIBIR un driver Node que
// importe y cablee esas tres funciones a mano cada vez — fricción que, en una
// corrida real, empuja a improvisar `orca terminal create --command 'codex exec …'`
// crudo: eso NO es este transporte (se salta el boot-wait de `createDispatch` y la
// cosecha por nonce de `awaitDone`, y pierde el prompt en la carrera de boot). La
// rama `orca-session` se corre SOLO por acá.
//
// El prompt/spec SIEMPRE se pasa por archivo (`--spec-file`), nunca inline: el
// markdown con backticks rompe el quoting del shell (misma regla que la rama `cli`).
//
// Contrato de salida (una línea JSON en stdout):
//   { transport: "orca-session", code, reportPath?, reason? }
//   code 0  → cosechado; `reportPath` es el informe. exit 0.
//   code !=0 → el conductor DEGRADA a `cli` (lee `reason`). exit == code.
//              4 = no se pudo crear/localizar la sesión propia (degradación limpia);
//              2/3 = fallo de cosecha/contención; 2+usageError = error de invocación.
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createOwnedSession, createDispatch, awaitDone, recover } from './dispatch-adapter.mjs';

// Deadline por default del turno del secundario (aparición de rollout + cosecha del
// nonce). 240s cubre el boot de MCP servers + un turno de exploración read-only real
// (medido en el E2E de Fase 7). El llamador lo ajusta con `--deadline-ms`.
const DEFAULT_DEADLINE_MS = 240_000;

/**
 * Best-effort: interrumpe al secundario y confirma idle (y cierra la terminal en
 * rol write) antes de degradar, para no dejar una sesión trabajando en el vacío.
 * Nunca lanza: la degradación a `cli` procede aunque la recuperación falle.
 * @param {object} session
 * @param {(args: string[]) => { stdout: string, code: number }} [orcaRunner]
 */
function tryRecover(session, orcaRunner) {
  try {
    recover({ session, dispatch: null, orcaRunner });
  } catch {
    // best-effort: si no se pudo recuperar, igual degradamos a cli.
  }
}

/**
 * Corre el flujo `orca-session` completo y devuelve el resultado normalizado.
 * Testeable: `orcaRunner`/`now`/`sleep` son inyectables (pasar `undefined` deja el
 * default real de cada función del adaptador); no invoca `orca` por sí mismo.
 *
 * @param {object} params
 * @param {'codex'|'claude'} params.family familia del secundario.
 * @param {'read-only'|'write'} params.role rol (garantía de sandbox/toolset).
 * @param {'attended'|'unattended'} params.mode atendido/desatendido.
 * @param {string} params.worktree ruta absoluta del worktree registrado en Orca.
 * @param {string} params.spec texto de la tarea (sin envelope: `createDispatch` lo agrega).
 * @param {string} params.reportPath destino del informe, RELATIVO a `root` (contención lo exige).
 * @param {string} params.root raíz autorizada del dispatch.
 * @param {number} [params.deadlineMs]
 * @param {number} [params.bootTimeoutMs]
 * @param {(args: string[]) => { stdout: string, code: number }} [params.orcaRunner]
 * @param {() => number} [params.now]
 * @param {(ms: number) => Promise<void>} [params.sleep]
 * @param {string} [params.stateDir]
 * @returns {Promise<{ transport: 'orca-session', code: number, reportPath?: string, reason?: string }>}
 */
export async function runOrcaSession({
  family,
  role,
  mode,
  worktree,
  spec,
  reportPath,
  root,
  deadlineMs = DEFAULT_DEADLINE_MS,
  bootTimeoutMs,
  orcaRunner,
  now,
  sleep,
  stateDir,
}) {
  // 1. Sesión fresca propia. `null` = no se pudo crear la terminal / leer su handle.
  const owned = createOwnedSession({ family, role, mode, worktree, orcaRunner, now, stateDir });
  if (!owned || !owned.session) {
    return {
      transport: 'orca-session',
      code: 4,
      reason: 'no se pudo crear la sesión Orca propia y fresca: degradar a cli',
    };
  }
  const { session } = owned;

  // 2. Boot-wait (tui-idle) + inject del spec con nonce. Lanza si el secundario no
  //    llega a idle a tiempo o si task/dispatch no devuelven id → degradar a cli.
  let dispatch;
  try {
    dispatch = createDispatch({ session, spec, root, bootTimeoutMs, orcaRunner });
  } catch (err) {
    tryRecover(session, orcaRunner);
    return {
      transport: 'orca-session',
      code: 4,
      reason: `no se pudo despachar la tarea (${err && err.message}): degradar a cli`,
    };
  }

  // 3. Esperar el fin del turno y cosechar por nonce del transcript propio.
  const res = await awaitDone({ session, dispatch, reportPath, root, deadlineMs, orcaRunner, now, sleep });
  if (res.code === 4) {
    // Rollout de Codex no localizable/ambiguo: recuperar antes de degradar.
    tryRecover(session, orcaRunner);
  }
  return { transport: 'orca-session', ...res };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

const REQUIRED_FLAGS = ['family', 'role', 'mode', 'worktree', 'spec-file', 'report', 'root'];

/**
 * Parser mínimo de `--clave valor` (sin dependencias, sin `parseArgs` para no
 * atarse a una versión de Node). Un flag sin valor siguiente queda en `"true"`.
 * @param {string[]} argv
 * @returns {Record<string,string>}
 */
function parseCliArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const next = argv[i + 1];
    if (next !== undefined && !next.startsWith('--')) {
      out[key] = next;
      i++;
    } else {
      out[key] = 'true';
    }
  }
  return out;
}

function emit(result) {
  process.stdout.write(`${JSON.stringify(result)}\n`);
  process.exitCode = result.code === 0 ? 0 : result.code;
}

/**
 * ¿Se está invocando este archivo como script (`node run-orca-session.mjs …`)?
 * Compara el path del módulo con `process.argv[1]` **resolviendo symlinks en
 * ambos lados**: Node deriva `import.meta.url` del path físico (real), pero
 * `process.argv[1]` conserva el path literal que tecleó el llamador. Como las
 * skills se instalan por **symlink** (`~/.claude/skills/… → repo`), el conductor
 * invoca el runner por su ruta symlinked; sin resolver el symlink, la comparación
 * daría `false`, `main()` no correría y el proceso terminaría con salida VACÍA
 * (exit 0) — sin crear la terminal ni cosechar (bug observado en corrida real).
 * @returns {boolean}
 */
function isMainModule() {
  if (!process.argv[1]) return false;
  try {
    return fs.realpathSync(fileURLToPath(import.meta.url)) === fs.realpathSync(process.argv[1]);
  } catch {
    return false;
  }
}

async function main() {
  const args = parseCliArgs(process.argv.slice(2));

  const missing = REQUIRED_FLAGS.filter((flag) => !args[flag] || args[flag] === 'true');
  if (missing.length > 0) {
    emit({
      transport: 'orca-session',
      code: 2,
      usageError: true,
      reason:
        `faltan argumentos: ${missing.join(', ')}. Uso: node run-orca-session.mjs ` +
        '--family <codex|claude> --role <read-only|write> --mode <attended|unattended> ' +
        '--worktree <abspath> --spec-file <path> --report <relpath-a-root> --root <dir> ' +
        '[--deadline-ms <n>] [--boot-timeout-ms <n>]',
    });
    return;
  }

  let spec;
  try {
    spec = fs.readFileSync(args['spec-file'], 'utf8');
  } catch (err) {
    emit({
      transport: 'orca-session',
      code: 2,
      usageError: true,
      reason: `no se pudo leer --spec-file "${args['spec-file']}": ${err && err.message}`,
    });
    return;
  }

  const result = await runOrcaSession({
    family: args.family,
    role: args.role,
    mode: args.mode,
    worktree: args.worktree,
    spec,
    reportPath: args.report,
    root: args.root,
    deadlineMs: args['deadline-ms'] ? Number(args['deadline-ms']) : undefined,
    bootTimeoutMs: args['boot-timeout-ms'] ? Number(args['boot-timeout-ms']) : undefined,
  });
  emit(result);
}

// Solo corre el CLI cuando se invoca como script (no al importarlo desde un test).
if (isMainModule()) {
  main().catch((err) => {
    emit({ transport: 'orca-session', code: 2, reason: `error inesperado: ${err && err.message}` });
  });
}
