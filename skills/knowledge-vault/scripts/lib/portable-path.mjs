/**
 * Nombres portables, traversal y clave de colisión (AC-3, AC-7, AC-7b) — plan §3.2.
 *
 * Dos responsabilidades que parecen la misma y no lo son:
 *
 * 1. **Rechazo de nombres no portables** (AC-7). Enumerado y cerrado. El
 *    repertorio de nombres es **completo**: CJK, cirílico, emoji y acentos se
 *    archivan sin problema. Solo caen los nombres genuinamente irrepresentables
 *    en los filesystems objetivo.
 *
 * 2. **Clave de colisión portable** (AC-7b). Usa normalización canónica y
 *    case-fold Unicode, y por eso vive **fuera de todo digest**. Su único efecto
 *    es aceptar o rechazar: una diferencia de tabla ICU entre dos máquinas hace
 *    que una rechace y otra acepte —fail-closed—, nunca que dos digests difieran.
 *
 * `é` (U+00E9) y `e` + U+0301 son nombres **distintos** para la identidad (AC-5)
 * y **el mismo nombre** para esta guarda. Las dos cosas a la vez, y a propósito:
 * coexisten en Linux pero colisionan en un filesystem con equivalencia canónica,
 * y una revisión así no se podría restaurar fielmente (AC-38 a AC-41).
 *
 * Módulo **puro**: no toca el disco.
 */

/** Error tipado del módulo. */
export class PortablePathError extends Error {
  constructor(code, message, { at = null, detail = null } = {}) {
    super(at ? `${message} (en ${JSON.stringify(at)})` : message);
    this.name = 'PortablePathError';
    this.code = code;
    this.at = at;
    this.detail = detail;
  }
}

/** Caracteres prohibidos en un nombre de archivo, más allá de los separadores. */
const RESERVED_CHARACTERS = new Set([...':*?"<>|'].map((c) => c.codePointAt(0)));

/**
 * Nombres reservados de Windows, con cualquier extensión (plan §3.2).
 * La lista es **la congelada en el plan**: `COM0`/`LPT0` no están, y agregarlos
 * acá sería restringir el repertorio sin pasar por un gate.
 */
const RESERVED_NAMES = new Set([
  'CON',
  'PRN',
  'AUX',
  'NUL',
  ...Array.from({ length: 9 }, (_, i) => `COM${i + 1}`),
  ...Array.from({ length: 9 }, (_, i) => `LPT${i + 1}`),
]);

/** Mayúsculas solo ASCII, escritas a mano: no depende de ninguna tabla. */
function asciiUpper(value) {
  let out = '';
  for (const character of value) {
    const codePoint = character.codePointAt(0);
    out += codePoint >= 0x61 && codePoint <= 0x7a ? String.fromCodePoint(codePoint - 32) : character;
  }
  return out;
}

/**
 * Revisa un **segmento** (un solo nombre, sin separadores) y devuelve
 * `{ ok: true }` o `{ ok: false, code, detail }`. No lanza: los llamadores que
 * quieren excepción usan `assertPortableSegment`.
 */
export function inspectSegment(name) {
  if (typeof name !== 'string') return { ok: false, code: 'INVALID_TYPE', detail: typeof name };
  if (name.length === 0) return { ok: false, code: 'EMPTY_SEGMENT', detail: null };
  if (name === '.' || name === '..') return { ok: false, code: 'DOT_SEGMENT', detail: name };

  for (const character of name) {
    const codePoint = character.codePointAt(0);

    if (codePoint >= 0xd800 && codePoint <= 0xdfff) {
      return { ok: false, code: 'LONE_SURROGATE', detail: `U+${codePoint.toString(16)}` };
    }
    if (codePoint === 0x2f || codePoint === 0x5c) {
      return { ok: false, code: 'PATH_SEPARATOR', detail: character };
    }
    if (codePoint <= 0x1f || codePoint === 0x7f) {
      return { ok: false, code: 'CONTROL_CHARACTER', detail: `U+${codePoint.toString(16).padStart(4, '0')}` };
    }
    if (RESERVED_CHARACTERS.has(codePoint)) {
      return { ok: false, code: 'RESERVED_CHARACTER', detail: character };
    }
  }

  const last = name.at(-1);
  if (last === ' ' || last === '.') {
    return { ok: false, code: 'TRAILING_SPACE_OR_DOT', detail: last };
  }

  // `CON`, `con.md`, `LPT3.tar.gz`: en Windows el nombre reservado es el tramo
  // anterior al primer punto, sin importar la extensión.
  const stem = asciiUpper(name.split('.')[0]);
  if (RESERVED_NAMES.has(stem)) {
    return { ok: false, code: 'RESERVED_NAME', detail: stem };
  }

  return { ok: true, code: null, detail: null };
}

export function isPortableSegment(name) {
  return inspectSegment(name).ok;
}

export function assertPortableSegment(name, at = null) {
  const verdict = inspectSegment(name);
  if (!verdict.ok) {
    throw new PortablePathError(verdict.code, `nombre no portable: ${describe(verdict, name)}`, {
      at: at ?? name,
      detail: verdict.detail,
    });
  }
  return name;
}

function describe(verdict, name) {
  switch (verdict.code) {
    case 'INVALID_TYPE':
      return `se esperaba string, llegó ${verdict.detail}`;
    case 'EMPTY_SEGMENT':
      return 'segmento vacío';
    case 'DOT_SEGMENT':
      return `segmento relativo ${verdict.detail}`;
    case 'PATH_SEPARATOR':
      return `separador de ruta ${JSON.stringify(verdict.detail)} dentro de un nombre`;
    case 'CONTROL_CHARACTER':
      return `carácter de control ${verdict.detail}`;
    case 'RESERVED_CHARACTER':
      return `carácter reservado ${JSON.stringify(verdict.detail)}`;
    case 'TRAILING_SPACE_OR_DOT':
      return `termina en ${JSON.stringify(verdict.detail)}`;
    case 'RESERVED_NAME':
      return `nombre reservado de Windows (${verdict.detail})`;
    case 'LONE_SURROGATE':
      return `surrogate suelto ${verdict.detail}`;
    default:
      return `${verdict.code} en ${JSON.stringify(name)}`;
  }
}

/**
 * Clave de colisión portable (AC-7b).
 *
 * **NUNCA entra a un digest.** Se calcula aparte y su único uso es rechazar dos
 * hermanos que un filesystem con equivalencia canónica o case-insensitivity
 * Unicode trataría como el mismo archivo.
 *
 * `toLowerCase` y no `toLocaleLowerCase`: el segundo depende del locale del
 * proceso y en turco convertiría `I` en `ı`, así que dos máquinas discreparían
 * por configuración regional en vez de por versión de tabla.
 */
export function collisionKey(name) {
  return name.normalize('NFC').toLowerCase().normalize('NFC');
}

/**
 * Rechaza colisiones entre hermanos. Recibe los nombres de **un solo**
 * directorio y lanza al primer par que colisione, nombrando a los dos.
 */
export function assertNoSiblingCollision(names, at = null) {
  const vistos = new Map();
  for (const name of names) {
    const key = collisionKey(name);
    const previo = vistos.get(key);
    if (previo !== undefined) {
      throw new PortablePathError(
        'SIBLING_COLLISION',
        `dos hermanos colisionan en un filesystem con equivalencia canónica o case-insensitivity: ` +
          `${JSON.stringify(previo)} y ${JSON.stringify(name)}`,
        { at, detail: [previo, name] },
      );
    }
    vistos.set(key, name);
  }
  return names;
}

/** Detecta rutas absolutas en las tres formas que importan: POSIX, unidad y UNC. */
function isAbsoluteLike(value) {
  return (
    value.startsWith('/') ||
    value.startsWith('\\') ||
    /^[A-Za-z]:/.test(value)
  );
}

/**
 * Valida una **ruta canónica relativa**: segmentos portables unidos por `/`.
 *
 * Es la guarda que usa `restore` sobre cada path del manifest antes de escribir
 * un byte (AC-39): un manifest ajeno o manipulado no puede sacar la escritura
 * del destino.
 */
export function assertCanonicalPath(value, at = null) {
  if (typeof value !== 'string' || value.length === 0) {
    throw new PortablePathError('EMPTY_PATH', 'ruta vacía o de tipo inválido', { at: at ?? value });
  }
  if (isAbsoluteLike(value)) {
    throw new PortablePathError('ABSOLUTE_PATH', `ruta absoluta: ${JSON.stringify(value)}`, {
      at: at ?? value,
    });
  }

  const segments = value.split('/');
  for (const segment of segments) {
    assertPortableSegment(segment, at ?? value);
  }
  return segments;
}

/**
 * Valida que una ruta relativa **no pueda salir de su raíz**, sin exigirle que
 * sus nombres sean portables.
 *
 * Es la guarda de los paths que solo se **reportan** —`omitted[]` y
 * `findings[]`—, no de los que se escriben. La diferencia importa: un
 * `node_modules/pkg/aux.js` es un archivo perfectamente normal que el filtrado
 * omite, y exigirle el repertorio de nombres de Windows volvería inválida la
 * salida de un archivado correcto. Lo que sí se prohíbe es lo que podría
 * confundir a un consumidor que reconstruya rutas: absolutas, `..` y `\`.
 */
export function assertContainedPath(value, at = null) {
  if (typeof value !== 'string' || value.length === 0) {
    throw new PortablePathError('EMPTY_PATH', 'ruta vacía o de tipo inválido', { at: at ?? value });
  }
  if (isAbsoluteLike(value)) {
    throw new PortablePathError('ABSOLUTE_PATH', `ruta absoluta: ${JSON.stringify(value)}`, { at: at ?? value });
  }

  const segments = value.split('/');
  for (const segment of segments) {
    if (segment.length === 0) {
      throw new PortablePathError('EMPTY_SEGMENT', `segmento vacío en ${JSON.stringify(value)}`, { at: at ?? value });
    }
    if (segment === '.' || segment === '..') {
      throw new PortablePathError('DOT_SEGMENT', `segmento ${segment} en ${JSON.stringify(value)}`, {
        at: at ?? value,
      });
    }
    if (segment.includes('\\')) {
      throw new PortablePathError('PATH_SEPARATOR', `separador de Windows en ${JSON.stringify(value)}`, {
        at: at ?? value,
      });
    }
  }
  return segments;
}

export function isContainedPath(value) {
  try {
    assertContainedPath(value);
    return true;
  } catch {
    return false;
  }
}

export function isCanonicalPath(value) {
  try {
    assertCanonicalPath(value);
    return true;
  } catch {
    return false;
  }
}

/** Une segmentos ya validados en una ruta canónica. Separador POSIX, siempre. */
export function toCanonicalPath(segments, at = null) {
  for (const segment of segments) assertPortableSegment(segment, at);
  return segments.join('/');
}
