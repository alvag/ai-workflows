/**
 * Precondición del archivado, fail-closed (AC-16, AC-17).
 *
 * Parser mínimo de frontmatter y evaluador de un predicado
 * `<archivo>:<clave>=<valor>` que **declara quien llama**. La regla que implementa
 * es una sola y no admite matices:
 *
 *   **La ausencia de información nunca habilita el archivado.**
 *
 * Se acepta **solo** cuando se encuentra positivamente un único valor de primer
 * nivel que coincide con el pedido. Los cinco caminos que rechazan —archivo
 * ausente, frontmatter ilegible, clave ausente, clave duplicada y valor distinto—
 * son estados nombrados, no un `else`.
 *
 * `kv` no sabe qué archivo ni qué clave: un consumidor pide `plan.md:status=done`
 * y otro `README.md:estado=cerrado`, y los dos recorren este mismo código. Esa es
 * la diferencia con la versión anterior, que tenía `plan.md` y `done` escritos
 * adentro.
 *
 * No es un parser de YAML y no pretende serlo: solo necesita una clave escalar.
 * Las líneas indentadas se ignoran a propósito, para que una clave anidada dentro
 * de otra estructura no se confunda con la de primer nivel.
 *
 * Módulo **puro**: recibe el contenido, no la ruta. `null` significa que el
 * archivo no existe.
 */

const KEY_LINE_RE = /^([A-Za-z0-9_-]+)[ \t]*:(.*)$/;

/** Quita el BOM y normaliza los finales de línea de Windows. */
function toLines(text) {
  const sinBom = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
  return sinBom.split('\n').map((line) => (line.endsWith('\r') ? line.slice(0, -1) : line));
}

/**
 * Limpia el valor: recorta, saca comillas envolventes y descarta un comentario
 * `#` precedido de espacio, que es como lo trata YAML.
 */
function cleanValue(raw) {
  let valor = raw.replace(/[ \t]+#.*$/, '').trim();
  if (valor.length >= 2) {
    const primero = valor[0];
    if ((primero === '"' || primero === "'") && valor.at(-1) === primero) {
      valor = valor.slice(1, -1);
    }
  }
  return valor;
}

/**
 * Extrae las claves escalares de **primer nivel** del frontmatter.
 *
 * Devuelve `{ ok, keys, duplicated }`. `ok: false` significa que el bloque no
 * existe o no cierra — el único caso en que el documento se considera ilegible.
 * Una línea con forma desconocida **no** invalida el documento: la aceptación
 * exige un hallazgo positivo, así que ignorarla no puede producir un falso sí.
 */
export function parseFrontmatter(text) {
  if (typeof text !== 'string') return { ok: false, keys: new Map(), duplicated: new Set() };

  const lines = toLines(text);
  if (lines.length === 0 || lines[0].trim() !== '---') {
    return { ok: false, keys: new Map(), duplicated: new Set() };
  }

  const keys = new Map();
  const duplicated = new Set();

  for (let i = 1; i < lines.length; i += 1) {
    const line = lines[i];
    const recortada = line.trim();

    if (recortada === '---' || recortada === '...') {
      return { ok: true, keys, duplicated };
    }
    if (recortada.length === 0 || recortada.startsWith('#')) continue;
    // Indentada: es contenido anidado, no una clave del plan.
    if (/^[ \t]/.test(line)) continue;

    const match = KEY_LINE_RE.exec(line);
    if (match === null) continue;

    const clave = match[1];
    if (keys.has(clave)) duplicated.add(clave);
    else keys.set(clave, cleanValue(match[2]));
  }

  // Se acabó el archivo sin cerrar el bloque.
  return { ok: false, keys: new Map(), duplicated: new Set() };
}
