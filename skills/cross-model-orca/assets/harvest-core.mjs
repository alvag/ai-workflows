// Núcleo puro de cosecha del transporte cross-model vía Orca.
// Funciones sin efecto sobre Orca en runtime: validan el sentinel del envelope,
// extraen la autoridad (nonce/taskId/dispatchId), garantizan la contención del
// reportPath, parsean el transcript/rollout del secundario y gestionan el
// exactly-once (dedup-FSM). Las consumen harvest-from-transcript.mjs y
// dispatch-adapter.mjs.
import fs from 'node:fs';
import path from 'node:path';

const SENTINEL_LINE = 'STATUS: done';
const ENVELOPE_PREFIX = 'X-CMO:';
const ENVELOPE_KEYS = new Set(['nonce', 'taskId', 'dispatchId']);

/**
 * Texto exacto que devuelve `checkContainment` cuando el único motivo de rechazo es que el
 * destino ya existe (a diferencia de un escape real por ".."/absoluta/symlink). Exportado como
 * constante -- en vez de que cada llamador dependa de un literal duplicado -- para que
 * `dispatch-adapter.mjs` pueda distinguir, en un retry post-crash, "ya cosechado" (destino
 * existente = éxito idempotente) de un rechazo real de contención.
 */
export const REPORT_ALREADY_EXISTS_REASON = 'El destino ya existe.';

/**
 * Índice de la última línea no vacía de `msg`, o -1 si todas las líneas están vacías.
 * @param {string[]} lines
 * @returns {number}
 */
function lastNonEmptyLineIndex(lines) {
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i].trim() !== '') return i;
  }
  return -1;
}

/**
 * `true` sii la última línea no vacía de `msg` es exactamente "STATUS: done".
 * Un "STATUS: done" citado en el medio del cuerpo (con más líneas después) no cuenta.
 * @param {string} msg
 * @returns {boolean}
 */
export function hasSentinel(msg) {
  const lines = msg.split('\n');
  const idx = lastNonEmptyLineIndex(lines);
  if (idx === -1) return false;
  return lines[idx].trim() === SENTINEL_LINE;
}

/**
 * Devuelve `msg` sin la línea sentinel final. Si no hay sentinel, devuelve `msg`
 * intacto. No recorta nada más que esa línea (preserva el cuerpo y la línea X-CMO:
 * si están antes).
 * @param {string} msg
 * @returns {string}
 */
export function stripSentinel(msg) {
  const lines = msg.split('\n');
  const idx = lastNonEmptyLineIndex(lines);
  if (idx === -1 || lines[idx].trim() !== SENTINEL_LINE) return msg;
  return [...lines.slice(0, idx), ...lines.slice(idx + 1)].join('\n');
}

/**
 * Busca la última línea "X-CMO:" de `msg` y extrae sus pares clave=valor
 * (nonce, taskId, dispatchId). Nunca lanza: si no hay línea X-CMO: o falta un
 * campo, ese campo queda en `null` y el llamador decide qué hacer.
 * @param {string} msg
 * @returns {{ nonce: string|null, taskId: string|null, dispatchId: string|null }}
 */
export function parseEnvelope(msg) {
  const result = { nonce: null, taskId: null, dispatchId: null };
  const lines = typeof msg === 'string' ? msg.split('\n') : [];
  let envelopeLine = null;
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i].trim().startsWith(ENVELOPE_PREFIX)) {
      envelopeLine = lines[i];
      break;
    }
  }
  if (envelopeLine === null) return result;

  const rest = envelopeLine.trim().slice(ENVELOPE_PREFIX.length).trim();
  for (const pair of rest.split(/\s+/).filter(Boolean)) {
    const eqIdx = pair.indexOf('=');
    if (eqIdx === -1) continue;
    const key = pair.slice(0, eqIdx);
    const value = pair.slice(eqIdx + 1);
    if (ENVELOPE_KEYS.has(key) && value !== '') result[key] = value;
  }
  return result;
}

/**
 * Extrae el texto de un mensaje del asistente de un rollout de Codex, o `null`
 * si `obj` no es un mensaje del asistente.
 * @param {*} obj línea ya parseada como JSON.
 * @returns {string|null}
 */
function extractCodexAssistantText(obj) {
  if (!obj || obj.type !== 'response_item') return null;
  const payload = obj.payload;
  if (!payload || payload.role !== 'assistant') return null;
  const content = Array.isArray(payload.content) ? payload.content : [];
  return content
    .filter((item) => item && item.type === 'output_text')
    .map((item) => item.text ?? '')
    .join('');
}

/**
 * Extrae el texto de un mensaje del asistente de un transcript de Claude, o
 * `null` si `obj` no es un mensaje del asistente.
 * @param {*} obj línea ya parseada como JSON.
 * @returns {string|null}
 */
function extractClaudeAssistantText(obj) {
  if (!obj || obj.type !== 'assistant') return null;
  const content = Array.isArray(obj.message?.content) ? obj.message.content : [];
  return content
    .filter((item) => item && item.type === 'text')
    .map((item) => item.text ?? '')
    .join('');
}

/**
 * Devuelve el extractor de texto de asistente correspondiente a la familia.
 * @param {'codex'|'claude'} family
 * @returns {(obj: *) => string|null}
 * @throws {Error} si la familia no es "codex" ni "claude".
 */
function assistantExtractorFor(family) {
  if (family === 'codex') return extractCodexAssistantText;
  if (family === 'claude') return extractClaudeAssistantText;
  throw new Error(`Familia desconocida: "${family}". Los valores válidos son "codex" o "claude".`);
}

/**
 * Lee `filePath` línea por línea (JSONL) y devuelve, en orden, el texto de cada
 * mensaje del asistente de la familia dada. Ignora líneas vacías, JSON inválido
 * o incompleto (una línea a medio escribir no rompe el parseo) y devuelve `[]`
 * si el archivo no existe o no se puede leer.
 * @param {'codex'|'claude'} family
 * @param {string} filePath
 * @returns {string[]}
 */
function readAssistantTexts(family, filePath) {
  const extractText = assistantExtractorFor(family);

  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch {
    return [];
  }

  const texts = [];
  for (const rawLine of content.split('\n')) {
    const line = rawLine.trim();
    if (line === '') continue;
    let obj;
    try {
      obj = JSON.parse(line);
    } catch {
      continue; // línea inválida o a medio escribir: se ignora sin romper el parseo
    }
    const text = extractText(obj);
    if (text !== null) texts.push(text);
  }
  return texts;
}

/**
 * Lee `filePath` (JSONL) y devuelve el texto del último mensaje del asistente
 * de la familia indicada, o `null` si no hay ninguno.
 * @param {'codex'|'claude'} family
 * @param {string} filePath
 * @returns {string|null}
 */
export function parseTranscript(family, filePath) {
  const texts = readAssistantTexts(family, filePath);
  return texts.length > 0 ? texts[texts.length - 1] : null;
}

/**
 * Devuelve el texto del último mensaje del asistente cuyo envelope tenga el
 * `nonce` dado. Sirve para desambiguar en una sesión reutilizada (dispatch
 * anterior vs. actual). `null` si ninguno coincide.
 * @param {'codex'|'claude'} family
 * @param {string} filePath
 * @param {string} nonce
 * @returns {string|null}
 */
export function selectAssistantByNonce(family, filePath, nonce) {
  const texts = readAssistantTexts(family, filePath);
  for (let i = texts.length - 1; i >= 0; i--) {
    if (parseEnvelope(texts[i]).nonce === nonce) return texts[i];
  }
  return null;
}

/**
 * Contención canónica robusta de `reportPath` dentro de `root`. Rechaza rutas
 * absolutas y segmentos "..", canonicaliza `root` con realpath, exige que el
 * realpath del directorio padre del destino quede dentro del root canónico
 * (bloquea symlink en el padre) y exige que el destino NO exista (bloquea
 * symlink en el componente final y respeta el contrato de ruta destino
 * inexistente). Nunca lanza: ante cualquier ruta inválida devuelve `ok:false`.
 * @param {string} reportPath ruta relativa propuesta para el reporte.
 * @param {string} root raíz permitida (puede ser, a su vez, un symlink).
 * @returns {{ ok: boolean, resolved?: string, reason?: string }}
 */
export function checkContainment(reportPath, root) {
  if (typeof reportPath !== 'string' || reportPath.length === 0) {
    return { ok: false, reason: 'reportPath vacío o inválido.' };
  }
  if (path.isAbsolute(reportPath)) {
    return { ok: false, reason: 'reportPath no puede ser una ruta absoluta.' };
  }
  const segments = reportPath.split(/[\\/]/);
  if (segments.includes('..')) {
    return { ok: false, reason: 'reportPath no puede contener segmentos "..".' };
  }

  let rootReal;
  try {
    rootReal = fs.realpathSync(root);
  } catch (err) {
    return { ok: false, reason: `No se pudo canonicalizar root: ${err.message}` };
  }

  const target = path.resolve(rootReal, reportPath);
  const parentDir = path.dirname(target);

  let parentReal;
  try {
    parentReal = fs.realpathSync(parentDir);
  } catch (err) {
    return { ok: false, reason: `No se pudo canonicalizar el directorio padre del destino: ${err.message}` };
  }

  const rootWithSep = rootReal.endsWith(path.sep) ? rootReal : rootReal + path.sep;
  if (parentReal !== rootReal && !parentReal.startsWith(rootWithSep)) {
    return { ok: false, reason: 'El directorio padre del destino escapa de root (posible symlink).' };
  }

  try {
    fs.lstatSync(target);
    return { ok: false, reason: REPORT_ALREADY_EXISTS_REASON };
  } catch (err) {
    if (err.code !== 'ENOENT') {
      return { ok: false, reason: `No se pudo verificar el destino: ${err.message}` };
    }
  }

  return { ok: true, resolved: target };
}

/**
 * Escribe `data` en `resolvedPath` en modo exclusivo: falla si el archivo
 * aparece entre el check de `checkContainment` y esta escritura (cierra la
 * carrera TOCTOU).
 * @param {string} resolvedPath
 * @param {string} data
 * @throws {Error} con código `EEXIST` si el archivo ya existe.
 */
export function writeExclusive(resolvedPath, data) {
  fs.writeFileSync(resolvedPath, data, { flag: 'wx' });
}

const FSM_ORDER = { received: 1, harvested: 2, promoted: 3 };

/**
 * Lee el estado persistido en `statePath`, o `{}` si el archivo no existe o
 * está corrupto (nunca lanza: el llamador recupera exactly-once desde raws
 * inmutables cuando hace falta reconstruir).
 * @param {string} statePath
 * @returns {Record<string, { status: string, desiredCanonicalHash?: string }>}
 */
function readFsmState(statePath) {
  try {
    return JSON.parse(fs.readFileSync(statePath, 'utf8'));
  } catch {
    return {};
  }
}

/**
 * Persiste el estado de la FSM en `statePath` de forma atómica: escribe a un
 * archivo temporal en el mismo directorio y lo renombra sobre `statePath`
 * (rename es atómico en el mismo filesystem), para que un crash a mitad de
 * escritura nunca deje un JSON parcial/corrupto en `statePath`.
 * @param {string} statePath
 * @param {Record<string, *>} state
 */
function writeFsmState(statePath, state) {
  const tmpPath = `${statePath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tmpPath, JSON.stringify(state, null, 2));
  fs.renameSync(tmpPath, statePath);
}

/**
 * FSM persistente y crash-idempotent para exactly-once de la cosecha. Clave
 * durable `${dispatchId}:${nonce}`. Estados `received -> harvested -> promoted`
 * persistidos en `statePath` (JSON).
 * @param {string} statePath
 */
export function makeDedupFsm(statePath) {
  /**
   * Avanza `key` a `nextStatus` si no está ya en ese estado o uno más avanzado
   * (idempotente: nunca regresa un estado).
   * @param {string} key
   * @param {'received'|'harvested'} nextStatus
   */
  function advance(key, nextStatus) {
    const state = readFsmState(statePath);
    const current = state[key];
    if (current && FSM_ORDER[current.status] >= FSM_ORDER[nextStatus]) return current;
    const entry = { ...current, status: nextStatus };
    state[key] = entry;
    writeFsmState(statePath, state);
    return entry;
  }

  return {
    /**
     * @param {string} key
     * @returns {{ status: string, desiredCanonicalHash?: string }|null}
     */
    state(key) {
      const state = readFsmState(statePath);
      return state[key] ?? null;
    },

    /** @param {string} key */
    markReceived(key) {
      return advance(key, 'received');
    },

    /** @param {string} key */
    markHarvested(key) {
      return advance(key, 'harvested');
    },

    /**
     * Marca `promoted` solo después de que el artefacto canónico quedó escrito
     * (el llamador informa el éxito pasando el hash del canónico, derivado por
     * completo de los raws inmutables). Si `key` ya está `promoted` con ese
     * mismo `canonicalHash`, no reaplica nada (idempotente ante reintentos
     * post-crash); si el hash difiere, se re-promueve con el nuevo hash.
     * @param {string} key
     * @param {string} canonicalHash
     */
    markPromoted(key, canonicalHash) {
      const state = readFsmState(statePath);
      const current = state[key];
      if (current?.status === 'promoted' && current.desiredCanonicalHash === canonicalHash) {
        return current;
      }
      const entry = { ...current, status: 'promoted', desiredCanonicalHash: canonicalHash };
      state[key] = entry;
      writeFsmState(statePath, state);
      return entry;
    },

    /**
     * @param {string} key
     * @returns {boolean}
     */
    isPromoted(key) {
      const state = readFsmState(statePath);
      return state[key]?.status === 'promoted';
    },
  };
}
