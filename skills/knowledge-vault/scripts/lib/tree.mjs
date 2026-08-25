/**
 * Escaneo, copia y verificación del árbol (AC-13, AC-14, AC-21).
 *
 * Tres reglas que gobiernan todo el módulo:
 *
 * 1. **`lstat` en cada entrada, y se entra a los directorios omitidos.** AC-21
 *    exige una entrada por **archivo** dentro de un directorio excluido, no una
 *    sola por el directorio: el receipt describe lo que ese intento va a
 *    destruir, y "omití `node_modules`" no describe nada.
 * 2. **Cualquier symlink o archivo especial aborta** (AC-14), sin publicar ni
 *    retirar nada. No se publica una captura parcial en silencio.
 * 3. **La verificación compara hashes y el conjunto exacto** (AC-13): un archivo
 *    de más en el destino también falla.
 */

import path from 'node:path';

import { assertNoSiblingCollision, assertPortableSegment } from './portable-path.mjs';

export class TreeError extends Error {
  constructor(code, message, { path: target = null, detail = null } = {}) {
    super(message);
    this.name = 'TreeError';
    this.code = code;
    this.path = target;
    this.detail = detail;
  }
}

/** Describe qué clase de entrada no soportada se encontró. */
function describeEntry(info) {
  if (info.isSymbolicLink()) return 'symlink';
  if (info.isBlockDevice()) return 'dispositivo de bloque';
  if (info.isCharacterDevice()) return 'dispositivo de caracteres';
  if (info.isFIFO()) return 'FIFO';
  if (info.isSocket()) return 'socket';
  return 'entrada de tipo desconocido';
}

// ── Escaneo ───────────────────────────────────────────────────────────────────

/**
 * Inventario **neutral** del origen: describe el árbol y no lo clasifica.
 *
 * Devuelve **todos** los archivos con su `sha256`, porque el `source_fingerprint`
 * cubre el origen entero: sin hashear lo que después se omita, un archivo omitido
 * podría cambiar sus bytes manteniendo el tamaño y se retiraría un origen que ya
 * no es el archivado.
 *
 * Dos cosas que **no** hace, y las dos importan:
 *
 * 1. **No decide qué se preserva.** Eso lo trae el manifiesto de selección. Acá no
 *    hay `disposition` ni `rule`: un número de regla de filtrado dentro de una
 *    identidad es exactamente el acoplamiento que `kv` dejó atrás.
 * 2. **No valida portabilidad.** AC-7 solo aplica a lo que se va a escribir en el
 *    destino, y hasta que la selección no se aplica no se sabe cuál es ese
 *    conjunto. La comprueba quien aplica la selección, con
 *    `assertIncludedTreePortable`.
 *
 * Sí **representa los directorios vacíos**. Entran al `source_fingerprint` pero no
 * a la selección ni a la verificación: no tienen bytes que hashear. Si no entraran
 * al digest, un directorio vacío creado entre el escaneo y el retiro no lo movería,
 * y se destruiría sin aparecer en ningún receipt.
 */
export async function scanInventory({ fs, root, label = 'scan', withHashes = true }) {
  await assertScannableRoot(fs, root, label);

  const files = [];
  const directories = [];
  await walkNeutral(fs, root, '', label, files, directories, withHashes);

  files.sort((a, b) => (a.path < b.path ? -1 : 1));
  directories.sort((a, b) => (a.path < b.path ? -1 : 1));
  return { files, directories };
}

/**
 * Devuelve `true` si el directorio quedó vacío, para que el padre pueda saber si
 * él mismo lo está. Un directorio con un solo hijo vacío **no** está vacío.
 */
async function walkNeutral(fs, dirAbs, relPrefix, label, files, directories, withHashes) {
  const leidas = await fs.readDirNames(dirAbs, `${label}.readdir`);
  if (leidas.length === 0 && relPrefix !== '') {
    directories.push({ path: relPrefix, type: 'directory' });
    return true;
  }

  for (const { name } of leidas) {
    const abs = path.join(dirAbs, name);
    const rel = relPrefix === '' ? name : `${relPrefix}/${name}`;
    const info = await assertScannableEntry(fs, abs, rel, label);

    if (info.isDirectory()) {
      await walkNeutral(fs, abs, rel, label, files, directories, withHashes);
      continue;
    }

    const { sha256, size } = withHashes
      ? await fs.hashFile(abs, `${label}.hash`)
      : { sha256: null, size: info.size };
    files.push({ path: rel, type: 'file', size, sha256 });
  }
  return false;
}

/** Rechaza lo que desapareció a mitad del escaneo y todo lo que no sea archivo o directorio. */
async function assertScannableEntry(fs, abs, rel, label) {
  const info = await fs.lstat(abs, `${label}.lstat`);
  if (info === null) {
    throw new TreeError('SOURCE_UNAVAILABLE', `la entrada desapareció durante el escaneo: ${rel}`, {
      path: abs,
    });
  }
  if (!info.isDirectory() && !info.isFile()) {
    throw new TreeError(
      'UNSUPPORTED_SOURCE_ENTRY',
      `el origen contiene un ${describeEntry(info)}: ${rel}`,
      { path: abs, detail: rel },
    );
  }
  return info;
}

/** Las tres condiciones de AC-14 sobre la raíz, compartidas por los dos escaneos. */
async function assertScannableRoot(fs, root, label) {
  const raiz = await fs.lstat(root, `${label}.lstat`);
  if (raiz === null) {
    throw new TreeError('SOURCE_UNAVAILABLE', `el origen no existe: ${root}`, { path: root });
  }
  if (raiz.isSymbolicLink()) {
    throw new TreeError('UNSUPPORTED_SOURCE_ENTRY', `el origen es un symlink: ${root}`, { path: root });
  }
  if (!raiz.isDirectory()) {
    throw new TreeError('SOURCE_UNAVAILABLE', `el origen no es un directorio: ${root}`, { path: root });
  }
  return raiz;
}

export function assertIncludedTreePortable(included, root = '') {
  const porDirectorio = collisionGroups(included);

  for (const entrada of included) {
    for (const segmento of entrada.path.split('/')) {
      assertPortableSegment(segmento, entrada.path);
    }
  }

  for (const [padre, nombres] of porDirectorio) {
    assertNoSiblingCollision(nombres, padre === '' ? root : `${root}/${padre}`);
  }
}

/**
 * Agrupa por directorio los nombres que participan de la guarda de colisión:
 * cada segmento de cada path incluido, o sea **también los directorios que
 * conducen a un incluido**.
 *
 * Se exporta para poder probarse sin filesystem: en macOS y Windows no se pueden
 * crear dos hermanos que colisionen —el sistema los trata como el mismo archivo—,
 * así que el recorrido real nunca puede construir el caso que esta guarda existe
 * para atajar. La guarda protege a quien archive **desde Linux** hacia un vault
 * que después se lea en macOS.
 */
export function collisionGroups(included) {
  const porDirectorio = new Map();
  for (const entrada of included) {
    const segmentos = entrada.path.split('/');
    for (let i = 0; i < segmentos.length; i += 1) {
      const padre = segmentos.slice(0, i).join('/');
      if (!porDirectorio.has(padre)) porDirectorio.set(padre, new Set());
      porDirectorio.get(padre).add(segmentos[i]);
    }
  }
  return new Map([...porDirectorio].map(([padre, nombres]) => [padre, [...nombres]]));
}

// ── Copia ─────────────────────────────────────────────────────────────────────

/**
 * Copia el subconjunto incluido al staging, con **creación exclusiva** y `fsync`
 * de cada archivo (pasos 10 y 11 del plan §4).
 *
 * La exclusividad no es paranoia: si el destino ya tuviera ese archivo, copiar
 * encima produciría una revisión que no es la que se calculó.
 */
export async function copyTree({ fs, from, to, entries, label = 'copy' }) {
  const directorios = new Set();

  for (const entrada of entries) {
    const destino = path.join(to, entrada.path);
    const padre = path.dirname(destino);
    if (!directorios.has(padre)) {
      await fs.mkdir(padre, `${label}.mkdir`, { recursive: true });
      directorios.add(padre);
    }
    await fs.copyFile(path.join(from, entrada.path), destino, `${label}.file`);
    await fs.fsyncFile(destino, `${label}.fsync`);
  }

  return [...directorios];
}

/**
 * `fsync` de los directorios de un árbol, **de hojas a raíz** (paso 12).
 *
 * El orden importa: sincronizar un padre antes que su hijo no garantiza que la
 * entrada del hijo esté durable.
 */
export async function fsyncTreeDirs({ fs, root, entries, label = 'copy' }) {
  const directorios = new Set([root]);
  for (const entrada of entries) {
    let actual = path.dirname(path.join(root, entrada.path));
    while (actual.length >= root.length && actual !== path.dirname(actual)) {
      directorios.add(actual);
      if (actual === root) break;
      actual = path.dirname(actual);
    }
  }

  const ordenados = [...directorios].sort((a, b) => b.split(path.sep).length - a.split(path.sep).length);
  for (const directorio of ordenados) {
    await fs.fsyncDir(directorio, `${label}.fsync-dir`);
  }
  return ordenados;
}

// ── Verificación ──────────────────────────────────────────────────────────────

/** Lista los archivos de un árbol sin clasificar. Aborta igual ante symlinks. */
export async function listFiles({ fs, root, label = 'verify' }) {
  const salida = [];
  await walkPlain(fs, root, '', label, salida);
  salida.sort((a, b) => (a.path < b.path ? -1 : 1));
  return salida;
}

async function walkPlain(fs, dirAbs, relPrefix, label, salida) {
  const leidas = await fs.readDirNames(dirAbs, `${label}.readdir`);
  for (const { name } of leidas) {
    const abs = path.join(dirAbs, name);
    const rel = relPrefix === '' ? name : `${relPrefix}/${name}`;
    const info = await fs.lstat(abs, `${label}.lstat`);
    if (info === null) continue;
    if (info.isDirectory()) {
      await walkPlain(fs, abs, rel, label, salida);
      continue;
    }
    if (!info.isFile()) {
      throw new TreeError('UNSUPPORTED_SOURCE_ENTRY', `${describeEntry(info)} en el destino: ${rel}`, {
        path: abs,
      });
    }
    const { sha256, size } = await fs.hashFile(abs, `${label}.hash`);
    salida.push({ path: rel, type: 'file', size, sha256 });
  }
}

/**
 * Verifica un árbol contra lo esperado: **hashes y conjunto exacto** (AC-13).
 *
 * Un archivo de más también falla. Comparar solo los hashes de lo esperado
 * dejaría pasar una revisión con contenido extra, que no es la que se calculó
 * y cuyo `revision_id` ya no la describe.
 */
export async function verifyTree({ fs, root, expected, label = 'verify' }) {
  const actuales = await listFiles({ fs, root, label });

  const esperados = new Map(expected.map((e) => [e.path, e]));
  const encontrados = new Map(actuales.map((e) => [e.path, e]));

  const faltantes = [];
  const sobrantes = [];
  const distintos = [];

  for (const [ruta, esperado] of esperados) {
    const actual = encontrados.get(ruta);
    if (actual === undefined) {
      faltantes.push(ruta);
      continue;
    }
    if (actual.sha256 !== esperado.sha256 || actual.size !== esperado.size) distintos.push(ruta);
  }
  for (const ruta of encontrados.keys()) {
    if (!esperados.has(ruta)) sobrantes.push(ruta);
  }

  if (faltantes.length > 0 || sobrantes.length > 0 || distintos.length > 0) {
    const partes = [];
    if (faltantes.length > 0) partes.push(`faltan ${faltantes.length}`);
    if (sobrantes.length > 0) partes.push(`sobran ${sobrantes.length}`);
    if (distintos.length > 0) partes.push(`${distintos.length} con contenido distinto`);
    throw new TreeError('VERIFY_FAILED', `la verificación de ${root} falló: ${partes.join(', ')}`, {
      path: root,
      detail: { missing: faltantes.sort(), extra: sobrantes.sort(), mismatched: distintos.sort() },
    });
  }

  return actuales;
}
