/**
 * Las cuatro identidades (AC-1, AC-2, AC-2b, AC-2c, AC-4) — plan §3.1 y §3.2.
 *
 * | Identidad | Qué identifica | Cómo se obtiene |
 * |---|---|---|
 * | `revision_id`        | el **subconjunto archivado**      | `sha256` del manifest canónico |
 * | `source_fingerprint` | el **origen completo**, con omitidos | `sha256` del inventario canónico |
 * | `attempt_id`         | **un intento**, con su comando y su decisión de filtrado | `sha256` del cuerpo canónico |
 * | `retirement_id`      | **una operación** de retiro       | UUID v4 |
 *
 * Las tres primeras son determinísticas; la cuarta no, porque no identifica un
 * contenido sino un acto. `command` entra al `attempt_id` a propósito: un
 * `archive` y un `migrate` del mismo contenido son operaciones distintas con
 * receipts distintos.
 *
 * Módulo **puro**: los hechos de Git —remoto, commits raíz, formato de objeto— y
 * el generador de UUID llegan **inyectados**. Acá no se ejecuta `git` ni se toca
 * el disco.
 */

import { digestDocument, sortFilesByPath } from './canonical.mjs';

export class IdentityError extends Error {
  constructor(code, message, { detail = null } = {}) {
    super(message);
    this.name = 'IdentityError';
    this.code = code;
    this.detail = detail;
  }
}

// ── Patrones congelados (plan §3.1) ───────────────────────────────────────────

/** 1–63 caracteres, ASCII minúsculo, sin guion inicial ni final. */
export const REPO_SLUG_RE = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;

/** 1–128, agrega `.` y `_`, y prohíbe `..` en cualquier posición. */
export const FLOW_ID_RE = /^(?!.*\.\.)[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?$/;
const HEX64_RE = /^[0-9a-f]{64}$/;

/** Longitud máxima del `stem` antes de pegarle los 12 hex de la identidad. */
const STEM_MAX = 48;

// ── Plegado ASCII, escrito a mano ─────────────────────────────────────────────

/**
 * Minúsculas solo ASCII. Ninguna tabla Unicode: el `stem` desemboca en el
 * `source_id` y de ahí al manifest, así que no puede depender de una.
 */
function asciiLower(value) {
  let out = '';
  for (const character of value) {
    const codePoint = character.codePointAt(0);
    out += codePoint >= 0x41 && codePoint <= 0x5a ? String.fromCodePoint(codePoint + 32) : character;
  }
  return out;
}

// ── Validación de segmentos (AC-2, AC-3) ──────────────────────────────────────

export function isRepoSlug(value) {
  return typeof value === 'string' && REPO_SLUG_RE.test(value);
}

export function isFlowId(value) {
  return typeof value === 'string' && FLOW_ID_RE.test(value);
}

export function assertRepoSlug(value) {
  if (!isRepoSlug(value)) {
    throw new IdentityError('INVALID_REPO_SLUG', `repo-slug inválido: ${JSON.stringify(value)}`, {
      detail: value,
    });
  }
  return value;
}

export function assertFlowId(value) {
  if (!isFlowId(value)) {
    throw new IdentityError('INVALID_FLOW_ID', `flow-id inválido: ${JSON.stringify(value)}`, {
      detail: value,
    });
  }
  return value;
}

/**
 * Deriva el `flow-id` del basename del origen.
 *
 * **No transforma: exige que ya sea canónico.** Transformar antes de validar creaba
 * colisiones invisibles —`PQTCH-546` y `pqtch-546`, o `ª` y `a`, convergían al
 * mismo `flow-id`— que AC-2c no detectaba, porque comparten `repo_identity`. Dos
 * flujos distintos habrían quedado mezclados como revisiones de una sola fuente.
 */
export function deriveFlowId(basename) {
  if (!isFlowId(basename)) {
    throw new IdentityError(
      'INVALID_FLOW_ID',
      `el nombre del directorio ${JSON.stringify(basename)} no es un flow-id canónico; ` +
        'pasa --flow-id explícito',
      { detail: basename },
    );
  }
  return basename;
}

// ── `repo-slug`: la proyección legible de la identidad ────────────────────────

/**
 * `stem`: folding ASCII, runs fuera de `[a-z0-9]` a un solo `-`, corte a 48 y
 * recorte de guiones. Si queda vacío, el literal `repo`.
 *
 * El `stem` no es identidad: la unicidad la garantizan los 12 hex del hash, así
 * que un stem degenerado nunca provoca colisión.
 */
export function deriveStem(rawName) {
  const plegado = asciiLower(String(rawName ?? ''));
  let stem = plegado.replace(/[^a-z0-9]+/g, '-').slice(0, STEM_MAX);
  stem = stem.replace(/^-+/, '').replace(/-+$/, '');
  return stem.length === 0 ? 'repo' : stem;
}

// ── Los tres documentos canónicos y sus digests ───────────────────────────────

function assertHex64(value, field) {
  if (typeof value !== 'string' || !HEX64_RE.test(value)) {
    throw new IdentityError('INVALID_HEX', `${field} debe ser 64 hex en minúscula`, { detail: value });
  }
  return value;
}

function normalizeFile(entry, { withDisposition }) {
  const base = {
    path: entry.path,
    type: entry.type ?? 'file',
    size: entry.size,
    sha256: assertHex64(entry.sha256, `sha256 de ${entry.path}`),
  };
  if (!withDisposition) return base;
  return {
    ...base,
    disposition: entry.disposition,
    // El **motivo que aportó el consumidor**, transcrito literal (AC-9). El campo
    // se llamó `rule` mientras `kv` clasificaba y guardaba el número de su propia
    // regla; ese cuerpo se dio de baja junto con el filtrado propio, y con él la
    // necesidad de elegir el nombre del campo en cada llamada.
    reason: entry.reason ?? null,
  };
}

// ── Las formas `v2`: inventario neutral y consumidor autor de la selección ────

/**
 * Inventario del origen completo **incluidos los directorios vacíos** (AC-23).
 *
 * Es la forma que compara AC-8: el consumidor pide este inventario, decide sobre
 * él y devuelve su `source_fingerprint`; `kv` lo recalcula bajo lock y rechaza con
 * `MANIFEST_STALE` si no coincide. Un directorio vacío fuera del fingerprint
 * volvía inauditable justamente lo que no deja rastro al destruirse.
 */
export function buildSourceInventoryV2({ files, directories }) {
  return {
    schema: 'kv-source-inventory/2',
    files: sortFilesByPath(files.map((f) => normalizeFile(f, { withDisposition: false }))),
    directories: sortFilesByPath(
      directories.map((d) => ({ path: d.path, type: 'directory' })),
      '$.directories',
    ),
  };
}
export const computeSourceFingerprint = (inventory) => digestDocument(inventory);