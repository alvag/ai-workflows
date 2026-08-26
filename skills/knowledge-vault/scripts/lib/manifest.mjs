/**
 * El manifiesto del retiro: la **autoridad del conjunto** que se va a destruir.
 *
 * El inventario hasheado del origen completo ya se computa hoy —el archivado lo
 * usa para su `source_fingerprint`— y se descarta sin persistir. Acá se persiste,
 * porque un borrado que se reanuda tras una caída necesita saber qué autorizó
 * alguien, y el árbol que quedó **ya no lo dice**: enumerar lo presente daría el
 * remanente, no el conjunto aprobado.
 *
 * Tres decisiones que no son de forma:
 *
 * 1. **Cierre de ancestros, más los que ya estaban vacíos.** Un directorio que
 *    queda vacío *por el propio borrado* no figura como vacío en el original, así
 *    que comparar literalmente la lista de vacíos rechazaría todo reintento. El
 *    manifiesto guarda el cierre de ancestros de los archivos —los que van a
 *    quedar vacíos— **y** los que ya lo estaban, que son los únicos que el
 *    escaneo reporta.
 * 2. **Los tipos se resuelven sin seguir enlaces.** Sólo archivos regulares y
 *    directorios; cualquier otro tipo detiene la operación nombrando la ruta y su
 *    tipo. No es una comprobación nueva: es la que `scanInventory` ya hace con
 *    `lstat`, y este módulo no la debilita. Un symlink seguido convertiría un
 *    borrado acotado en un borrado en cualquier parte del disco.
 * 3. **El digest cubre siete cosas**: identidad, alcance, inventario con hashes,
 *    clasificación, directorios, bytes y el commit del vault. El commit está
 *    adentro porque el manifiesto autoriza destruir *contra una copia concreta*:
 *    si el vault avanzó, la autorización es sobre otra cosa.
 */

import path from 'node:path';

import { digestDocument, sortFilesByPath } from './canonical.mjs';
import { scanInventory } from './tree.mjs';

export const SCHEMA_MANIFIESTO = 'kv-retirement-manifest/1';

export class ManifestError extends Error {
  constructor(code, message, { path: target = null, detail = null } = {}) {
    super(message);
    this.name = 'ManifestError';
    this.code = code;
    this.path = target;
    this.detail = detail;
  }
}

/** Clasificación de cada entrada. Enum cerrado. */
export const CLASES = Object.freeze({ A_SALVO: 'a-salvo', SIN_COPIA: 'sin-copia' });

/**
 * Cierre de ancestros de una ruta relativa, sin la propia ruta y sin la raíz.
 * `a/b/c.md` → `['a', 'a/b']`.
 */
function ancestros(rel) {
  const partes = rel.split('/').slice(0, -1);
  return partes.map((_, i) => partes.slice(0, i + 1).join('/'));
}

/**
 * @param {object} args
 * @param {object} args.fs sistema de archivos inyectado
 * @param {string} args.flowDir origen, que se **lee** y nada más
 * @param {Iterable<string>} args.aSalvo rutas relativas cuyo contenido está en el vault
 * @param {{repoId: string, flowId: string}} args.identidad identidad **declarada**
 * @param {string} args.vaultCommit `HEAD` del vault contra el que se verificó
 */
export async function construirManifiesto({ fs, flowDir, aSalvo, identidad, vaultCommit, label = 'manifest' }) {
  if (typeof identidad?.repoId !== 'string' || typeof identidad?.flowId !== 'string') {
    throw new ManifestError('IDENTIDAD_AUSENTE', 'el manifiesto exige una identidad declarada');
  }
  if (typeof vaultCommit !== 'string' || vaultCommit.length === 0) {
    throw new ManifestError('COMMIT_AUSENTE', 'el manifiesto exige el commit del vault que lo respalda');
  }

  // `scanInventory` hashea todo y aborta ante symlinks y especiales.
  const inventario = await scanInventory({ fs, root: flowDir, label: `${label}.scan` });
  const salvos = new Set(aSalvo ?? []);

  const entradas = sortFilesByPath(
    inventario.files.map((e) => ({
      path: e.path,
      sha256: e.sha256,
      size: e.size,
      clase: salvos.has(e.path) ? CLASES.A_SALVO : CLASES.SIN_COPIA,
    })),
    '$.inventario',
  );

  const dirs = new Set(inventario.directories.map((d) => d.path));
  for (const e of entradas) for (const a of ancestros(e.path)) dirs.add(a);
  // Y los ancestros de los que ya estaban vacíos. Un directorio cuyos únicos
  // hijos son directorios vacíos no es ancestro de ningún archivo ni figura como
  // vacío, así que sin esta vuelta queda fuera de las dos ramas: el borrado deja
  // de vaciar a su padre y el reintento lo rechaza por no autorizado. Medido en
  // `cross-model-recovery-resume`, donde `cohort/transport` contenía sólo
  // `bindings/` y `events/`, los dos vacíos.
  for (const d of inventario.directories) for (const a of ancestros(d.path)) dirs.add(a);
  const directorios = sortFilesByPath([...dirs].map((p) => ({ path: p })), '$.directorios');

  const suma = (clase) =>
    entradas.filter((e) => clase === null || e.clase === clase).reduce((t, e) => t + e.size, 0);

  return {
    schema: SCHEMA_MANIFIESTO,
    identidad: { flowId: identidad.flowId, repoId: identidad.repoId },
    alcance: { nombre: path.basename(flowDir) },
    bytes: { aSalvo: suma(CLASES.A_SALVO), sinCopia: suma(CLASES.SIN_COPIA), total: suma(null) },
    directorios,
    inventario: entradas,
    vault: { commit: vaultCommit },
  };
}

/** El digest canónico del manifiesto: es lo que una persona aprueba. */
export function digestManifiesto(manifiesto) {
  return digestDocument(manifiesto);
}
