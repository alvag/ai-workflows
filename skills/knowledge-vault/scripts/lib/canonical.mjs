/**
 * Serialización canónica y digests (AC-5, AC-6, AC-8) — plan §3.2.
 *
 * Una sola canonicalización para el manifest, el inventario y el cuerpo del
 * intento. Sobre estos bytes se toman `revision_id`, `source_fingerprint` y
 * `attempt_id`, así que la regla que gobierna todo el módulo es:
 *
 *   **NINGUNA OPERACIÓN DEPENDIENTE DE TABLAS UNICODE.**
 *
 * Nada de `normalize()`, nada de `toLowerCase()` sobre datos, nada de
 * `localeCompare()`. Las strings viajan con sus bytes UTF-8 tal cual y el orden
 * de claves es por valor numérico de punto de código. Es lo que hace que el mismo
 * árbol de bytes dé el mismo digest en cualquier máquina, sin acotar por versión
 * de ICU (AC-5).
 *
 * Módulo **puro**: no toca el disco ni `process`.
 */

import { createHash } from 'node:crypto';

/** Error tipado del módulo. El mapeo a estados del CLI lo hace `contracts.mjs`. */
export class CanonicalError extends Error {
  constructor(code, message, { at = null } = {}) {
    super(at ? `${message} (en ${at})` : message);
    this.name = 'CanonicalError';
    this.code = code;
    this.at = at;
  }
}

/**
 * Schemas canónicos conocidos (AC-6). Uno desconocido se **rechaza**, no se
 * interpreta. `orderedArrays` declara qué arrays deben venir ordenados por
 * `path`: el serializador no reordena nada, verifica.
 */
const SCHEMAS = new Map([
  ['kv-manifest/1', { orderedArrays: ['files'] }],
  ['kv-source-inventory/1', { orderedArrays: ['files'] }],
  ['kv-attempt/1', { orderedArrays: ['inventory'] }],
  // ── v2: las formas que introduce el desacople del consumidor ────────────────
  // `kv-selection/1` es el documento que trae quien llama: qué preservar y qué
  // omitir. Nombre propio a propósito — `kv-manifest/1` ya identifica el
  // manifiesto durable de una revisión, y reusarlo haría ambigua la identidad.
  ['kv-selection/1', { orderedArrays: ['entries'] }],
  // `directories` es el array nuevo: solo los vacíos. Entra al fingerprint pero
  // no a la selección ni a la verificación (no tiene bytes que comprobar).
  ['kv-source-inventory/2', { orderedArrays: ['files', 'directories'] }],
  ['kv-attempt/2', { orderedArrays: ['inventory'] }],
  // El journal no tiene arrays: se registra para que `assertKnownSchema` lo
  // acepte, no por orden.
  ['kv-retirement/2', { orderedArrays: [] }],
]);

export function isKnownSchema(schema) {
  return typeof schema === 'string' && SCHEMAS.has(schema);
}

export function knownSchemas() {
  return [...SCHEMAS.keys()];
}

export function assertKnownSchema(schema) {
  if (!isKnownSchema(schema)) {
    throw new CanonicalError('UNKNOWN_SCHEMA', `schema desconocido: ${JSON.stringify(schema)}`);
  }
  return schema;
}

/**
 * Puntos de código de una string, rechazando surrogates sueltos.
 *
 * Una string de JS es UTF-16 y puede contener un surrogate sin par, que **no es
 * un escalar Unicode** y no tiene codificación UTF-8 válida. `Buffer.from` lo
 * reemplazaría por U+FFFD en silencio: dos valores distintos colapsarían al mismo
 * digest.
 */
export function toCodePoints(value, at = null) {
  if (typeof value !== 'string') {
    throw new CanonicalError('UNSUPPORTED_TYPE', `se esperaba string, llegó ${typeof value}`, { at });
  }
  const points = [];
  for (const character of value) {
    const codePoint = character.codePointAt(0);
    if (codePoint >= 0xd800 && codePoint <= 0xdfff) {
      throw new CanonicalError(
        'LONE_SURROGATE',
        `surrogate suelto U+${codePoint.toString(16).toUpperCase()} en una string canónica`,
        { at },
      );
    }
    points.push(codePoint);
  }
  return points;
}

/**
 * Orden por valor numérico de punto de código.
 *
 * No sirve comparar strings con `<`: JS compara unidades UTF-16, así que todo el
 * plano suplementario (emoji, CJK extendido) quedaría **antes** de U+E000–U+FFFF
 * en vez de después.
 */
export function compareCodePoints(left, right) {
  const a = toCodePoints(left);
  const b = toCodePoints(right);
  const shared = Math.min(a.length, b.length);
  for (let i = 0; i < shared; i += 1) {
    if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1;
  }
  if (a.length === b.length) return 0;
  return a.length < b.length ? -1 : 1;
}

const ESCAPED = new Map([
  [0x22, '\\"'],
  [0x5c, '\\\\'],
]);

/** String JSON canónica: solo `"` y `\` escapados; C0 como `\u00xx` minúscula. */
function encodeString(value, at) {
  let out = '"';
  for (const codePoint of toCodePoints(value, at)) {
    const escaped = ESCAPED.get(codePoint);
    if (escaped !== undefined) {
      out += escaped;
    } else if (codePoint <= 0x1f) {
      out += `\\u00${codePoint.toString(16).padStart(2, '0')}`;
    } else {
      out += String.fromCodePoint(codePoint);
    }
  }
  return `${out}"`;
}

/**
 * Números: **solo enteros no negativos seguros**.
 *
 * Ahí estaba la ambigüedad numérica de JSON y se cierra restringiendo el dominio,
 * no inventando un formato. `-0`, fracciones, exponentes y todo lo que pase
 * `Number.MAX_SAFE_INTEGER` se rechazan.
 */
function encodeNumber(value, at) {
  if (Object.is(value, -0)) {
    throw new CanonicalError('UNSUPPORTED_NUMBER', 'el cero negativo no es canónico', { at });
  }
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new CanonicalError(
      'UNSUPPORTED_NUMBER',
      `solo enteros no negativos seguros; llegó ${value}`,
      { at },
    );
  }
  return String(value);
}

function isPlainObject(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function encodeValue(value, at, seen) {
  if (value === null) return 'null';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') return encodeNumber(value, at);
  if (typeof value === 'string') return encodeString(value, at);

  if (Array.isArray(value)) {
    if (seen.has(value)) throw new CanonicalError('CYCLE', 'ciclo en el valor canónico', { at });
    seen.add(value);
    const parts = value.map((item, index) => encodeValue(item, `${at}[${index}]`, seen));
    seen.delete(value);
    return `[${parts.join(',')}]`;
  }

  if (isPlainObject(value)) {
    if (seen.has(value)) throw new CanonicalError('CYCLE', 'ciclo en el valor canónico', { at });
    seen.add(value);
    if (Object.getOwnPropertySymbols(value).length > 0) {
      throw new CanonicalError('UNSUPPORTED_TYPE', 'un objeto canónico no lleva claves símbolo', { at });
    }
    const keys = Object.keys(value).sort(compareCodePoints);
    const parts = keys.map((key) => {
      const child = value[key];
      const childAt = `${at}.${key}`;
      if (child === undefined) {
        throw new CanonicalError(
          'UNSUPPORTED_TYPE',
          'un valor ausente cambiaría el digest en silencio: usa null explícito',
          { at: childAt },
        );
      }
      return `${encodeString(key, childAt)}:${encodeValue(child, childAt, seen)}`;
    });
    seen.delete(value);
    return `{${parts.join(',')}}`;
  }

  throw new CanonicalError('UNSUPPORTED_TYPE', `tipo no canonizable: ${typeof value}`, { at });
}

/** Bytes canónicos de cualquier valor admitido. UTF-8, sin BOM ni salto final. */
export function canonicalBytes(value) {
  return Buffer.from(encodeValue(value, '$', new Set()), 'utf8');
}

export function sha256Hex(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

/** Digest canónico de un valor: `sha256(canonicalBytes(valor))`. */
export function digestOf(value) {
  return sha256Hex(canonicalBytes(value));
}

/**
 * Ordena una lista de archivos por su `path` canónico y **rechaza duplicados**.
 *
 * Dos entradas con el mismo path en un manifest no son un detalle de orden: son
 * un inventario que no describe un árbol real.
 */
export function sortFilesByPath(files, at = '$.files') {
  if (!Array.isArray(files)) {
    throw new CanonicalError('UNSUPPORTED_TYPE', 'se esperaba una lista de archivos', { at });
  }
  const sorted = [...files].sort((a, b) => compareCodePoints(a?.path, b?.path));
  for (let i = 1; i < sorted.length; i += 1) {
    if (compareCodePoints(sorted[i - 1].path, sorted[i].path) === 0) {
      throw new CanonicalError('DUPLICATE_PATH', `path repetido: ${sorted[i].path}`, { at });
    }
  }
  return sorted;
}

function assertOrderedArrays(document) {
  const { orderedArrays } = SCHEMAS.get(document.schema);
  for (const field of orderedArrays) {
    const entries = document[field];
    if (entries === undefined) continue;
    if (!Array.isArray(entries)) {
      throw new CanonicalError('UNSUPPORTED_TYPE', `${field} debe ser una lista`, { at: `$.${field}` });
    }
    for (let i = 1; i < entries.length; i += 1) {
      const order = compareCodePoints(entries[i - 1]?.path, entries[i]?.path);
      if (order > 0) {
        throw new CanonicalError(
          'UNORDERED_FILES',
          `${field} no está ordenado por path canónico: ${entries[i - 1].path} > ${entries[i].path}`,
          { at: `$.${field}[${i}]` },
        );
      }
      if (order === 0) {
        throw new CanonicalError('DUPLICATE_PATH', `path repetido: ${entries[i].path}`, {
          at: `$.${field}[${i}]`,
        });
      }
    }
  }
}

/**
 * Bytes canónicos de un documento **versionado**: exige `schema` conocido (AC-6)
 * y verifica el orden de sus listas de archivos.
 *
 * Verifica en vez de ordenar a propósito: si el serializador reordenara, una lista
 * mal construida produciría un digest válido y el bug viviría hasta que alguien
 * comparara dos árboles.
 */
export function canonicalizeDocument(document) {
  if (!isPlainObject(document)) {
    throw new CanonicalError('UNSUPPORTED_TYPE', 'un documento canónico es un objeto');
  }
  assertKnownSchema(document.schema);
  assertOrderedArrays(document);
  return canonicalBytes(document);
}

export function digestDocument(document) {
  return sha256Hex(canonicalizeDocument(document));
}

/**
 * Lee un documento canónico desde bytes. Un schema desconocido o ausente se
 * **rechaza en vez de interpretarse** (AC-6).
 */
export function parseDocument(bytes, { expectSchema = null } = {}) {
  let text;
  try {
    // `ignoreBOM: true` significa "no lo consumas": el BOM llega como U+FEFF y se
    // puede rechazar. Con `false` —el default— el decoder lo **elimina**, y el
    // chequeo de abajo sería código muerto: un documento con BOM entraría como
    // válido y sus bytes ya no coincidirían con los recalculados.
    text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes);
  } catch {
    throw new CanonicalError('INVALID_ENCODING', 'el documento no es UTF-8 válido');
  }
  if (text.charCodeAt(0) === 0xfeff) {
    throw new CanonicalError('INVALID_ENCODING', 'un documento canónico no lleva BOM');
  }

  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (err) {
    throw new CanonicalError('INVALID_JSON', `JSON inválido: ${err.message}`);
  }
  if (!isPlainObject(parsed)) {
    throw new CanonicalError('UNSUPPORTED_TYPE', 'un documento canónico es un objeto');
  }
  assertKnownSchema(parsed.schema);
  if (expectSchema !== null) {
    // Acepta uno o varios: un lector doble `v1|v2` no es "cualquier schema", es
    // una lista corta y explícita. Pasarle `null` para permitir las dos versiones
    // sería aceptar también las ajenas.
    const esperados = Array.isArray(expectSchema) ? expectSchema : [expectSchema];
    if (!esperados.includes(parsed.schema)) {
      throw new CanonicalError(
        'SCHEMA_MISMATCH',
        `se esperaba ${esperados.join(' o ')} y llegó ${parsed.schema}`,
      );
    }
  }
  return parsed;
}
