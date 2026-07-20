#!/usr/bin/env node
// Entry point del conductor: cosecha el informe del transcript/rollout de la
// sesión fresca del secundario y lo persiste en reportPath. Se invoca una vez
// que el adaptador (dispatch-adapter.mjs, Task 1.5) detectó el fin del turno
// (worker_done / tui-idle) y ya validó la autoridad (sender vs. assignee) del
// dispatch. Este módulo NO revalida esa autoridad: asume una entrada ya
// autorizada y su única responsabilidad es cosechar del transcript → persistir.
import { realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import {
  hasSentinel,
  stripSentinel,
  selectAssistantByNonce,
  checkContainment,
  writeExclusive,
} from './harvest-core.mjs';

const POLL_INITIAL_MS = 20;
const POLL_MAX_MS = 200;

/**
 * @param {number} ms
 * @returns {Promise<void>}
 */
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Cosecha el informe del dispatch en curso desde el transcript/rollout y lo
 * persiste en `reportPath`.
 *
 * Hace poll estabilizado del transcript hasta el deadline: relee el archivo y
 * busca, vía `selectAssistantByNonce`, el mensaje del asistente cuyo envelope
 * tenga `nonce` y que además esté completo (`hasSentinel`). Si todavía no
 * aparece, espera un intervalo corto con backoff exponencial acotado (entre
 * `POLL_INITIAL_MS` y `POLL_MAX_MS`) y reintenta.
 *
 * `deadlineMs` es un **presupuesto de poll**: una duración en milisegundos
 * contada desde la invocación, no un timestamp absoluto. Internamente se
 * calcula el instante límite como `now() + deadlineMs`.
 *
 * @param {object} params
 * @param {'codex'|'claude'} params.family familia del secundario cuyo transcript se cosecha.
 * @param {string} params.transcriptPath ruta del transcript/rollout ya localizado por el adaptador.
 * @param {string} params.nonce nonce del dispatch en curso, para desambiguar sesiones reutilizadas.
 * @param {string} params.reportPath ruta relativa (dentro de `root`) donde persistir el informe; debe ser inexistente.
 * @param {string} params.root raíz autorizada del dispatch, usada para la contención de `reportPath`.
 * @param {number} params.deadlineMs presupuesto de poll, en milisegundos, contado desde la invocación.
 * @param {() => number} [params.now] reloj inyectable (default `Date.now`); útil en entornos de test sin reloj real.
 * @returns {Promise<{ code: 0, reportPath: string } | { code: 2|3, reason: string }>}
 *   `code` 0: cosechado y persistido (`reportPath` = ruta resuelta y escrita).
 *   `code` 2: contención rechazada (`reason` proviene de `checkContainment`).
 *   `code` 3: venció el deadline sin un mensaje válido con ese nonce+sentinel.
 */
export async function harvest(params) {
  const { family, transcriptPath, nonce, reportPath, root, deadlineMs, now = Date.now } = params;

  const deadlineAt = now() + deadlineMs;
  let waitMs = POLL_INITIAL_MS;
  let body = null;

  for (;;) {
    const msg = selectAssistantByNonce(family, transcriptPath, nonce);
    if (msg !== null && hasSentinel(msg)) {
      body = stripSentinel(msg);
      break;
    }
    if (now() >= deadlineAt) {
      return { code: 3, reason: 'timeout sin envelope válido' };
    }
    await sleep(Math.min(waitMs, Math.max(0, deadlineAt - now())));
    waitMs = Math.min(waitMs * 2, POLL_MAX_MS);
  }

  const contained = checkContainment(reportPath, root);
  if (!contained.ok) {
    return { code: 2, reason: contained.reason };
  }

  writeExclusive(contained.resolved, body);
  return { code: 0, reportPath: contained.resolved };
}

// ---------------------------------------------------------------------------
// Wrapper CLI: solo lee params de variables de entorno, invoca harvest() y
// sale con el código correspondiente. Sin lógica propia (eso vive en
// harvest(), testeada por separado como función pura).
// ---------------------------------------------------------------------------

const REQUIRED_ENV_VARS = [
  'CMO_FAMILY',
  'CMO_TRANSCRIPT',
  'CMO_NONCE',
  'CMO_REPORT_PATH',
  'CMO_ROOT',
  'CMO_DEADLINE_MS',
];

/**
 * Lee y valida los params de `harvest()` desde variables de entorno.
 * @param {NodeJS.ProcessEnv} env
 * @returns {{ family: 'codex'|'claude', transcriptPath: string, nonce: string, reportPath: string, root: string, deadlineMs: number }}
 * @throws {Error} si falta alguna variable requerida o `CMO_DEADLINE_MS` no es un número válido.
 */
function readCliParams(env) {
  const missing = REQUIRED_ENV_VARS.filter((name) => !env[name]);
  if (missing.length > 0) {
    throw new Error(`Faltan variables de entorno requeridas: ${missing.join(', ')}.`);
  }

  const deadlineMs = Number(env.CMO_DEADLINE_MS);
  if (!Number.isFinite(deadlineMs) || deadlineMs < 0) {
    throw new Error(`CMO_DEADLINE_MS debe ser un número >= 0. Valor recibido: "${env.CMO_DEADLINE_MS}".`);
  }

  return {
    family: env.CMO_FAMILY,
    transcriptPath: env.CMO_TRANSCRIPT,
    nonce: env.CMO_NONCE,
    reportPath: env.CMO_REPORT_PATH,
    root: env.CMO_ROOT,
    deadlineMs,
  };
}

async function main() {
  try {
    const params = readCliParams(process.env);
    const result = await harvest(params);
    if (result.reason) process.stderr.write(`${result.reason}\n`);
    process.exit(result.code);
  } catch (err) {
    // Cubre tanto params inválidos (readCliParams) como errores inesperados
    // de harvest() (p. ej. family desconocida): salida limpia, nunca un stack
    // trace sin manejar.
    process.stderr.write(`${err.message}\n`);
    process.exit(1);
  }
}

// ¿Se invoca como script? Compara resolviendo symlinks en ambos lados: Node deriva
// `import.meta.url` del path físico, pero `process.argv[1]` conserva el path literal.
// Con las skills instaladas por symlink (`~/.claude/skills/… → repo`), sin resolver el
// symlink el guard daría `false` y `main()` no correría (salida vacía, exit 0).
function isMainModule() {
  if (!process.argv[1]) return false;
  try {
    return realpathSync(fileURLToPath(import.meta.url)) === realpathSync(process.argv[1]);
  } catch {
    return false;
  }
}
if (isMainModule()) {
  main();
}
