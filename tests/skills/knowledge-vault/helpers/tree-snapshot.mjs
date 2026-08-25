/**
 * Snapshot byte a byte de un árbol, para las aserciones de "cero escrituras".
 *
 * Está escrito con `node:fs` **directo, a propósito**: es el oracle contra el que
 * se verifica `durable-fs.mjs`, así que no puede compartir su implementación. Si
 * los dos tuvieran el mismo bug, el test quedaría verde igual.
 */

import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';

/**
 * Devuelve un mapa `rutaRelativa → descriptor`. Los symlinks se registran por su
 * destino, sin seguirlos; los archivos, por tamaño y hash de contenido.
 */
export async function snapshotTree(root) {
  const salida = new Map();

  async function recorrer(actual, prefijo) {
    let entradas;
    try {
      entradas = await fs.readdir(actual, { withFileTypes: true });
    } catch (error) {
      if (error.code === 'ENOENT') return;
      throw error;
    }
    for (const entrada of entradas.sort((a, b) => (a.name < b.name ? -1 : 1))) {
      const absoluta = path.join(actual, entrada.name);
      const relativa = prefijo === '' ? entrada.name : `${prefijo}/${entrada.name}`;
      const info = await fs.lstat(absoluta);

      if (info.isSymbolicLink()) {
        salida.set(relativa, `symlink:${await fs.readlink(absoluta)}`);
      } else if (info.isDirectory()) {
        salida.set(relativa, 'dir');
        await recorrer(absoluta, relativa);
      } else if (info.isFile()) {
        const bytes = await fs.readFile(absoluta);
        salida.set(relativa, `file:${bytes.length}:${createHash('sha256').update(bytes).digest('hex')}`);
      } else {
        salida.set(relativa, 'special');
      }
    }
  }

  await recorrer(root, '');
  return salida;
}

/** Compara dos snapshots y devuelve las diferencias como texto legible. */
export function diffSnapshots(antes, despues) {
  const diferencias = [];
  for (const [ruta, valor] of antes) {
    if (!despues.has(ruta)) diferencias.push(`- ${ruta} (${valor})`);
    else if (despues.get(ruta) !== valor) diferencias.push(`~ ${ruta}: ${valor} → ${despues.get(ruta)}`);
  }
  for (const [ruta, valor] of despues) {
    if (!antes.has(ruta)) diferencias.push(`+ ${ruta} (${valor})`);
  }
  return diferencias;
}
