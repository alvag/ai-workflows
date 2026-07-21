// Orquestador (LIBRERÍA) del transporte `orca-session`: encadena el flujo del
// adaptador —createOwnedSession → createDispatch → awaitDone— con la MISMA
// degradación a `cli` que documenta cada skill llamadora.
//
// Este archivo NO se ejecuta como script: lo importan el entrypoint CLI
// (`run-orca-session.mjs`) y los tests. Por eso NO lleva guard de módulo-main —
// ese guard (`import.meta.url === argv[1]`) fue la fuente de dos bugs de
// invocación por symlink; separar la lógica (acá, importable) del CLI (allá,
// guardless) elimina esa clase de bug de raíz. Ver `run-orca-session.mjs`.
//
// Por qué existe el transporte por función y no un `orca terminal create` a mano:
// improvisar `orca terminal create --command 'codex exec …'` se salta el boot-wait
// (tui-idle) de `createDispatch` y la cosecha por nonce de `awaitDone`, y pierde el
// prompt en la carrera de boot. La rama `orca-session` se corre SOLO por este flujo.
import { createOwnedSession, createDispatch, awaitDone, recover } from './dispatch-adapter.mjs';

// Deadline por default del turno del secundario (aparición de rollout + cosecha del
// nonce). 240s cubre el boot de MCP servers + un turno de exploración read-only real
// (medido en el E2E de Fase 7). El llamador lo ajusta con `--deadline-ms`.
export const DEFAULT_DEADLINE_MS = 240_000;

/**
 * Best-effort: interrumpe al secundario y CIERRA la terminal antes de degradar.
 * `closeTerminal: true` explícito aunque el rol sea read-only: el runner degrada a
 * `cli` y abandona la sesión — no va a redespachar sobre ella —, y sin el cierre la
 * degradación deja una terminal zombie abierta "sin hacer nada" (observado en el
 * caso real de Windows). Nunca lanza: la degradación procede aunque falle, pero el
 * resultado del cierre SÍ se devuelve — un `false` en rol write significa que no se
 * demostró que el secundario dejó de escribir (ver `recovered` en el contrato del
 * runner; hallazgo del cross-review de Codex).
 * @param {object} session
 * @param {(args: string[]) => { stdout: string, code: number }} [orcaRunner]
 * @returns {boolean} cierre/recuperación demostrados.
 */
function tryRecover(session, orcaRunner) {
  try {
    return recover({ session, dispatch: null, closeTerminal: true, orcaRunner }).recovered;
  } catch {
    // best-effort: si no se pudo recuperar, igual degradamos a cli.
    return false;
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
    dispatch = await createDispatch({ session, spec, root, bootTimeoutMs, orcaRunner, sleep });
  } catch (err) {
    const recovered = tryRecover(session, orcaRunner);
    return {
      transport: 'orca-session',
      code: 4,
      recovered,
      reason: `no se pudo despachar la tarea (${err && err.message}): degradar a cli`,
    };
  }

  // 3. Esperar el fin del turno y cosechar por nonce del transcript propio.
  const res = await awaitDone({ session, dispatch, reportPath, root, deadlineMs, orcaRunner, now, sleep });
  if (res.code !== 0) {
    // TODO fallo (no solo code 4): recuperar/cerrar antes de degradar. Hallazgo del
    // cross-review de Codex: con code 3 (deadline vencido esperando el nonce) el
    // secundario puede seguir TRABAJANDO — degradar a cli sin interrumpirlo dejaría
    // un doble escritor en rol write (y una terminal zombie en read-only). `recovered`
    // viaja en el resultado: en rol write, `recovered:false` significa que el cierre
    // NO se demostró y la skill llamadora NO debe redespachar por cli sin intervención
    // manual (mismo contrato que `recover`, ver reference.md → "Recuperación").
    const recovered = tryRecover(session, orcaRunner);
    return { transport: 'orca-session', recovered, ...res };
  }
  return { transport: 'orca-session', ...res };
}
