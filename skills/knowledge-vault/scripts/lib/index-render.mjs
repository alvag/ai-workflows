/**
 * Los índices del vault: lo que lo vuelve consultable sin leerlo entero.
 *
 * **Agregación transitiva, no listado de hijos.** Un índice por directorio que
 * liste sólo su nivel deja la raíz de este vault con una sola entrada —
 * `projects/`— y obliga a bajar cuatro niveles para saber qué hay. Cada índice
 * lista todos los flujos que cuelgan de él, directa o indirectamente, así que la
 * raíz alcanza para ubicar cualquiera.
 *
 * **Regenerar da los mismos bytes.** Es lo que permite reconstruirlos después de
 * cualquier corrida sin preguntarse si algo cambió, y lo que hace del índice un
 * derivado y no una fuente. Para eso: nada de timestamps, orden explícito en vez
 * del que devuelva el filesystem, y **ninguna fuente externa al vault** — en
 * particular ningún modelo redactando nada. El resumen no se genera acá: se
 * **deriva** del frontmatter del nodo, que es donde lo puso quien archivó.
 *
 * Módulo de sólo lectura: devuelve el contenido y **no escribe**. Quien publica
 * es el motor.
 */

import fs from 'node:fs/promises';
import path from 'node:path';

import { parsePublishedNodeMetadata } from './node-builder.mjs';
import { encodeRelativePath } from './portable-path.mjs';
import { INDEX_FILENAME, isNodeFile } from './vault-store.mjs';

export class IndexRenderError extends Error {
  constructor(message, { path: target = null } = {}) {
    super(message);
    this.name = 'IndexRenderError';
    this.code = 'NODE_UNREADABLE';
    this.path = target;
  }
}

/** Recorre el vault y devuelve los nodos de flujo, con su directorio y su frontmatter. */
async function recolectarNodos(vaultRoot) {
  const nodos = [];
  const visitar = async (dirAbs) => {
    const entradas = await fs.readdir(dirAbs, { withFileTypes: true });
    for (const e of entradas) {
      const abs = path.join(dirAbs, e.name);
      if (e.isDirectory()) {
        await visitar(abs);
        continue;
      }
      if (!isNodeFile(path.basename(dirAbs), e.name)) continue;

      const text = await fs.readFile(abs, 'utf8');
      const expectedFlow = path.basename(abs, '.md');
      try {
        const metadata = parsePublishedNodeMetadata(text, expectedFlow);
        nodos.push({ abs, dir: dirAbs, ...metadata });
      } catch (error) {
        if (error?.code !== 'NODE_UNREADABLE') throw error;
        // No se completa ni se saltea en silencio: esconder un nodo ilegible lo
        // volvería invisible para siempre.
        throw new IndexRenderError(
          `el nodo ${path.basename(abs)} no se puede leer: ${error.message}`,
          { path: abs },
        );
      }
    }
  };
  await visitar(vaultRoot);
  // Orden explícito: `readdir` no promete ninguno, y sin esto dos máquinas
  // producirían índices distintos sobre el mismo contenido.
  nodos.sort((a, b) => (a.flow === b.flow ? a.abs.localeCompare(b.abs) : a.flow.localeCompare(b.flow)));
  return nodos;
}

/** Los ancestros de un nodo dentro del vault, de la raíz hacia su directorio. */
function ancestros(vaultRoot, dirAbs) {
  const cadena = [];
  let actual = dirAbs;
  for (;;) {
    cadena.push(actual);
    if (actual === vaultRoot) break;
    const padre = path.dirname(actual);
    if (padre === actual) break;
    actual = padre;
  }
  return cadena.reverse();
}

function renderizar(titulo, nodos, dirDelIndice) {
  const lineas = [`# ${titulo}`, ''];
  lineas.push(nodos.length === 1 ? '1 flujo.' : `${nodos.length} flujos.`, '');
  for (const n of nodos) {
    const rel = encodeRelativePath(path.relative(dirDelIndice, n.abs).split(path.sep).join('/'));
    lineas.push(`- [${n.title}](${rel}) — ${n.summary}`);
  }
  lineas.push('');
  return lineas.join('\n');
}

/**
 * @param {string} vaultRoot
 * @returns {Promise<Map<string,string>>} ruta absoluta de cada índice → su contenido.
 */
export async function renderIndexes(vaultRoot) {
  const nodos = await recolectarNodos(vaultRoot);

  // Cada directorio que tenga al menos un nodo por debajo recibe índice, y hereda
  // todos los que cuelgan de él. Derivarlo de los nodos —en vez de enumerar los
  // cuatro niveles del layout— hace que un vault con otra forma siga funcionando.
  const porDirectorio = new Map();
  for (const n of nodos) {
    for (const dir of ancestros(vaultRoot, n.dir)) {
      if (!porDirectorio.has(dir)) porDirectorio.set(dir, []);
      porDirectorio.get(dir).push(n);
    }
  }
  if (!porDirectorio.has(vaultRoot)) porDirectorio.set(vaultRoot, []);

  const salida = new Map();
  for (const [dir, suyos] of porDirectorio) {
    const titulo = dir === vaultRoot ? 'Índice del vault' : path.basename(dir);
    salida.set(path.join(dir, INDEX_FILENAME), renderizar(titulo, suyos, dir));
  }
  return salida;
}
