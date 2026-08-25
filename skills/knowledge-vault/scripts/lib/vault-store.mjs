/**
 * Dónde va cada cosa dentro del vault, y las escrituras que no son la copia.
 *
 * El almacén del que se rescata este módulo guardaba revisiones inmutables en
 * `raw/<source_id>/<revision_id>/files/`. Ese layout es correcto para versionar
 * y **ilegible** para una persona que abre el vault en un editor de Markdown, que
 * es el único consumidor que le queda. Acá la ruta de un documento es la que
 * alguien escribiría a mano, y con eso se van el manifest, el directorio `files`,
 * los recibos, los punteros y el identificador de revisión.
 *
 * **La frontera verificada.** `verifyTree` compara conjuntos exactos: un archivo
 * de más en el destino es `sobrante` y hace fallar la verificación. Por eso el
 * directorio del flujo contiene **exactamente** los documentos copiados, y todo
 * lo generado —el nodo y los índices— vive fuera de él. No es una preferencia de
 * orden: meter el nodo adentro haría fallar cada rearchivado.
 */

import path from 'node:path';

import { assertCanonicalPath, collisionKey } from './portable-path.mjs';

export class VaultStoreError extends Error {
  constructor(code, message, { path: target = null, detail = null } = {}) {
    super(message);
    this.name = 'VaultStoreError';
    this.code = code;
    this.path = target;
    this.detail = detail;
  }
}

/** Prefijo del staging de publicación, hermano de la frontera. */
export const STAGING_PREFIX = '.kv-staging-';

// ── Los nombres del layout, en una sola sede ──────────────────────────────────
//
// `index-render` necesita el camino inverso —dado un archivo, decidir si es un
// nodo de flujo— y derivarlo de aquí evita que dos módulos declaren por separado
// cómo se llama cada nivel y se desincronicen.
export const PROJECTS_DIRNAME = 'projects';
export const SDD_DIRNAME = 'sdd';
export const INDEX_FILENAME = 'index.md';
export const LOG_FILENAME = 'log.md';

/** Un archivo es el **nodo** de un flujo si cuelga directo de `sdd/` y no es un generado. */
export function isNodeFile(parentDirName, fileName) {
  return (
    parentDirName === SDD_DIRNAME &&
    fileName.endsWith('.md') &&
    fileName !== INDEX_FILENAME &&
    fileName !== LOG_FILENAME
  );
}

/**
 * Nombres de flujo que colisionarían con un archivo generado.
 *
 * `index` choca de verdad: el nodo de un flujo así llamado sería
 * `sdd/index.md`, que es el índice generado de ese nivel. `log` se reserva por
 * el mismo motivo un nivel más arriba y para que la lista sea una sola.
 */
const NOMBRES_RESERVADOS = new Set(
  [INDEX_FILENAME, LOG_FILENAME].map((f) => collisionKey(f.replace(/\.md$/, ''))),
);

/**
 * Rechaza un nombre de flujo reservado.
 *
 * Compara por **clave de colisión**, no por igualdad: en macOS y en Windows el
 * filesystem no distingue mayúsculas, así que un flujo `Index` produciría un
 * `Index.md` que pisa `index.md`. Un rechazo que se esquiva cambiando una letra
 * no es un rechazo.
 */
export function assertFlowNameAllowed(flowId) {
  if (NOMBRES_RESERVADOS.has(collisionKey(String(flowId ?? '')))) {
    throw new VaultStoreError(
      'RESERVED_FLOW_NAME',
      `${JSON.stringify(flowId)} es un nombre de flujo reservado: colisionaría con un archivo generado`,
      { detail: [...NOMBRES_RESERVADOS] },
    );
  }
  return flowId;
}

/**
 * Las rutas de un flujo dentro del vault.
 *
 * ```
 * <vault>/index.md                              índice raíz
 * <vault>/projects/index.md                     índice
 * <vault>/projects/<repo>/index.md              índice
 * <vault>/projects/<repo>/sdd/index.md          índice
 * <vault>/projects/<repo>/sdd/<flujo>.md        el NODO, hermano del directorio
 * <vault>/projects/<repo>/sdd/<flujo>/          FRONTERA VERIFICADA
 * ```
 *
 * Los índices van de la raíz hacia la hoja, que es el orden en que se leen.
 *
 * @returns {{frontier: string, nodePath: string, indexPaths: string[]}}
 */
export function resolveLayout(vaultRoot, repoSlug, flowId) {
  assertFlowNameAllowed(flowId);
  // Valida los dos segmentos variables antes de construir una sola ruta: una
  // barra o un `..` en el id de flujo escaparía del vault, y `CON` es un nombre
  // que Windows no puede crear.
  assertCanonicalPath(`${PROJECTS_DIRNAME}/${repoSlug}/${SDD_DIRNAME}/${flowId}`, 'layout del vault');

  const en = (...segmentos) => path.join(vaultRoot, ...segmentos);
  return {
    frontier: en('projects', repoSlug, 'sdd', flowId),
    nodePath: en('projects', repoSlug, 'sdd', `${flowId}.md`),
    indexPaths: [
      en(INDEX_FILENAME),
      en(PROJECTS_DIRNAME, INDEX_FILENAME),
      en(PROJECTS_DIRNAME, repoSlug, INDEX_FILENAME),
      en(PROJECTS_DIRNAME, repoSlug, SDD_DIRNAME, INDEX_FILENAME),
    ],
  };
}

/** El staging es **hermano** de la frontera: así el `rename` de publicación no cruza filesystem. */
export function resolveStagingPath(vaultRoot, repoSlug, flowId, token) {
  const { frontier } = resolveLayout(vaultRoot, repoSlug, flowId);
  return path.join(path.dirname(frontier), `${STAGING_PREFIX}${flowId}-${token}`);
}

export function isStagingName(name) {
  return name.startsWith(STAGING_PREFIX);
}

async function leerSiExiste(fs, ruta, label) {
  try {
    return await fs.readFile(ruta, label);
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

/**
 * Corre una escritura derivada y **falla si falla**.
 *
 * En el árbol de origen esto degradaba el error a una advertencia, y tenía
 * sentido ahí: un derivado que no se pudo escribir no invalidaba una revisión ya
 * publicada. Acá los derivados —el nodo y los índices— son **postcondiciones**
 * del verbo: sin ellos el flujo está copiado pero no consultable, que es lo que
 * el archivado prometía. Una advertencia dejaría al reintento reportando que ya
 * estaba todo hecho.
 */
export async function writeDerived(accion, warningCode, { path: target = null } = {}) {
  try {
    await accion();
    return { ok: true, warning: null };
  } catch (error) {
    if (error?.name === 'InjectedCrash') throw error;
    throw new VaultStoreError(warningCode, error.message, { path: target, detail: error.code ?? null });
  }
}

/**
 * Una línea del log del vault.
 *
 * La versión anterior citaba `rev` e `intento` —los dos identificadores del
 * almacén de revisiones—. Sin revisiones, lo que identifica a una entrada es el
 * flujo que se archivó.
 */
export function formatLogEntry({ timestamp, repoSlug, flowId, counts }) {
  return (
    `- ${timestamp} · \`${repoSlug}/${flowId}\` · ` +
    `${counts.included} archivados, ${counts.omitted} omitidos\n`
  );
}

export async function appendLogEntry({ fs, vaultRoot, entry, label = 'log.append' }) {
  const ruta = path.join(vaultRoot, LOG_FILENAME);
  return writeDerived(
    async () => {
      const previo = (await leerSiExiste(fs, ruta, `${label}.read`)) ?? Buffer.alloc(0);
      await fs.writeFileAtomic(ruta, Buffer.concat([previo, Buffer.from(entry, 'utf8')]), label);
    },
    'LOG_WRITE_FAILED',
    { path: ruta },
  );
}

/**
 * Barre los stagings que quedaron de una corrida muerta.
 *
 * Se conserva aunque el resto de la recuperación se haya retirado, y no por
 * simetría: `copyTree` crea el destino con creación **exclusiva**, así que un
 * staging huérfano bloquea el reintento en vez de ser ruido inofensivo.
 */
export async function discardOrphanStagings({ fs, parentDir, label = 'stage.discard' }) {
  const info = await fs.lstat(parentDir, `${label}.lstat`);
  if (info === null) return [];

  const descartados = [];
  for (const { name } of await fs.readDirNames(parentDir, `${label}.readdir`)) {
    if (!isStagingName(name)) continue;
    await fs.rmTree(path.join(parentDir, name), label);
    descartados.push(name);
  }
  if (descartados.length > 0) await fs.fsyncDir(parentDir, `${label}.fsync-dir`);
  return descartados;
}
