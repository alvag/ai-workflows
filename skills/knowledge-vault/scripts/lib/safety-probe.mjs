/**
 * ¿Este flujo está a salvo en el vault? (AC-2, AC-10, AC-12)
 *
 * Es el predicado que autoriza un borrado irreversible, y su propiedad central no
 * es qué comprueba sino **de qué no depende**: no recibe nada de quien pregunta
 * más allá de dónde mirar, y no escribe un solo byte.
 *
 * Esa propiedad es la que se cayó al medir la premisa heredada. `ALREADY_ARCHIVED`
 * parecía la precondición natural del retiro, pero su valor depende del `--summary`
 * que recibe el comando: con el resumen correcto devuelve `ALREADY_ARCHIVED` sin
 * escribir, y con uno distinto **reescribe el nodo, crea un commit** y devuelve
 * `ARCHIVED`. Una sonda que muta lo que consulta no puede decidir un borrado.
 *
 * Las cuatro postcondiciones son las mismas que el archivado exige para declararse
 * completo, y se preguntan en este orden porque la primera es la más cara y la que
 * más dice:
 *
 * 1. **frontera** publicada y verificando hash por hash contra el origen;
 * 2. **nodo** del flujo escrito;
 * 3. **índices** regenerados, los cuatro;
 * 4. **anclaje**: todo eso en `HEAD` y limpio, no sólo en disco.
 *
 * Y antes que las cuatro, el **conjunto vacío se rechaza**. Con cero documentos
 * copiables, comparar el origen contra la frontera pasa de forma vacua y se
 * destruiría el 100 % de un flujo que no tiene un byte suyo a salvo. Es la clase
 * de verde que no distingue "todo está" de "no hay nada que comparar".
 */

import path from 'node:path';

import { fronteraPublicada } from './engine-vault.mjs';
import { isCopiable } from './selection.mjs';
import { scanInventory } from './tree.mjs';
import { anclaEnHead } from './vault-git.mjs';
import { resolveLayout } from './vault-store.mjs';

/** Causas posibles. Enum cerrado: quien consuma esto ramifica sobre él. */
export const CAUSAS = Object.freeze({
  EMPTY_SET: 'EMPTY_SET',
  FRONTIER_MISSING: 'FRONTIER_MISSING',
  VERIFY_FAILED: 'VERIFY_FAILED',
  NODE_MISSING: 'NODE_MISSING',
  INDEX_MISSING: 'INDEX_MISSING',
  NOT_ANCHORED: 'NOT_ANCHORED',
});

const noSalvo = (causa, faltantes = []) => ({ aSalvo: false, causa, faltantes });

async function existe(fs, ruta, label) {
  return (await fs.lstat(ruta, label)) !== null;
}

/**
 * @param {object} args
 * @param {object} args.fs sistema de archivos **inyectado**; nunca el crudo
 * @param {string} args.vaultRoot
 * @param {string} args.repoId identidad declarada del repositorio
 * @param {string} args.flowId
 * @param {string} args.flowDir origen, que se **lee** y nada más
 * @returns {Promise<{aSalvo: boolean, faltantes: string[], causa: string|null}>}
 */
export async function estaASalvo({ fs, vaultRoot, repoId, flowId, flowDir }) {
  const label = `probe.${flowId}`;
  const { frontier, nodePath, indexPaths } = resolveLayout(vaultRoot, repoId, flowId);

  const inventario = await scanInventory({ fs, root: flowDir, label: `${label}.scan` });
  const esperados = inventario.files.filter((e) => isCopiable(e.path));
  if (esperados.length === 0) return noSalvo(CAUSAS.EMPTY_SET);

  try {
    if (!(await fronteraPublicada(fs, frontier, esperados, label))) {
      return noSalvo(CAUSAS.FRONTIER_MISSING, esperados.map((e) => e.path));
    }
  } catch (error) {
    // La tercera respuesta de la sonda de frontera: existe y **no** coincide.
    // Para decidir un borrado eso es un no, y las rutas concretas viajan con él.
    if (error?.code !== 'VERIFY_FAILED') throw error;
    const d = error.detail ?? {};
    return noSalvo(CAUSAS.VERIFY_FAILED, [...(d.missing ?? []), ...(d.extra ?? []), ...(d.mismatched ?? [])]);
  }

  if (!(await existe(fs, nodePath, `${label}.node.lstat`))) {
    return noSalvo(CAUSAS.NODE_MISSING, [nodePath]);
  }

  const sinIndice = [];
  for (const ruta of indexPaths) {
    if (!(await existe(fs, ruta, `${label}.index.lstat`))) sinIndice.push(ruta);
  }
  if (sinIndice.length > 0) return noSalvo(CAUSAS.INDEX_MISSING, sinIndice);

  const propias = [frontier, nodePath, ...indexPaths].map((p) => path.relative(vaultRoot, p));
  if (!(await anclaEnHead(vaultRoot, propias))) return noSalvo(CAUSAS.NOT_ANCHORED, propias);

  return { aSalvo: true, causa: null, faltantes: [] };
}
