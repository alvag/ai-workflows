/**
 * La transacción de archivado.
 *
 * Qué conserva del motor del que se rescata: resolución de entradas, escaneo e
 * identidades, bifurcación de idempotencia, limpieza de staging huérfano,
 * staging-copia-verificación, publicación atómica y reverificación.
 *
 * Qué pierde, y por qué junto: lock por `source_id`, recuperación de journal,
 * rama de origen ausente, receipt durable, lock de derivados y los dos pasos de
 * retiro. **Los seis existían para sostener el borrado del origen.** Sin retiro
 * no hay nada que reconstruir después de una caída: el origen sigue ahí, y el
 * peor caso es rehacer trabajo.
 *
 * La limpieza de staging huérfano **sí** se conserva, y separada de la
 * recuperación de journal con la que compartía bloque. No es simetría: `copyTree`
 * crea con exclusión, así que un staging que quedó de una corrida muerta
 * **bloquea** el reintento en vez de ser ruido inofensivo.
 *
 * ## Las cuatro postcondiciones
 *
 * `ARCHIVED` y `ALREADY_ARCHIVED` exigen las cuatro: frontera publicada, nodo
 * escrito, índices regenerados y commit creado. Con la definición fácil —
 * "publicado = la frontera existe"— una caída entre la publicación y el commit
 * dejaría un flujo copiado que el reintento reporta como completo y que no
 * aparece en ningún índice: presente en disco e invisible para siempre.
 *
 * ## Sobre el origen
 *
 * El motor **lee** el origen y nada más. No hay en este archivo, ni en ningún
 * módulo que importe, una llamada capaz de borrar, renombrar o escribir fuera del
 * vault. Es una propiedad de la forma del código, no del camino que tome.
 *
 * Lo que cambió con el quinto verbo es **cómo se comprueba esa propiedad**, no si
 * vale acá. Antes se seguía de la ausencia: ningún módulo de la skill podía
 * destruir. Ahora el módulo de retiro sí puede, así que la guarda enumera a los
 * autorizados y este motor sigue del lado de los que no lo están.
 */

import path from 'node:path';

import { computeSourceFingerprint, buildSourceInventoryV2 } from './identity.mjs';
import { isInjectedCrash } from './durable-fs.mjs';
import { withFlowLock } from './flow-lock.mjs';
import { renderIndexes } from './index-render.mjs';
import { buildNode } from './node-builder.mjs';
import { resolveMetadata } from './metadata-source.mjs';
import { isCopiable } from './selection.mjs';
import { copyTree, fsyncTreeDirs, scanInventory, verifyTree } from './tree.mjs';
import {
  appendLogEntry,
  discardOrphanStagings,
  formatLogEntry,
  resolveLayout,
  LOG_FILENAME,
  resolveStagingPath,
  writeDerived,
} from './vault-store.mjs';
import { anclaEnHead, assertVaultClean, commitFlow, ensureVaultRepo } from './vault-git.mjs';

export class EngineError extends Error {
  constructor(code, message, { path: target = null, detail = null } = {}) {
    super(message);
    this.name = 'EngineError';
    this.code = code;
    this.path = target;
    this.detail = detail;
  }
}

/**
 * Traduce el fallo de un tramo a su estado de contrato **sin tragarse nada más**:
 * un `EngineError` ya clasificado pasa tal cual, y una `InjectedCrash` —que
 * representa que el proceso dejó de existir— se reenvía siempre.
 */
async function enEtapa(code, target, accion) {
  try {
    return await accion();
  } catch (error) {
    if (isInjectedCrash(error) || error instanceof EngineError) throw error;
    throw new EngineError(code, error.message, { path: error.path ?? target, detail: error.detail ?? null });
  }
}

/** Las rutas concretas que hicieron fallar una verificación, para poder nombrarlas. */
function rutasDelFallo(error) {
  const d = error?.detail ?? {};
  return [...(d.missing ?? []), ...(d.extra ?? []), ...(d.mismatched ?? [])];
}

async function existe(fs, ruta, label) {
  return (await fs.lstat(ruta, label)) !== null;
}

async function leerSiExiste(fs, ruta, label) {
  try {
    return (await fs.readFile(ruta, label)).toString('utf8');
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

/**
 * ¿La frontera ya está publicada y verifica?
 *
 * Tres respuestas, no dos. `false` es "no existe todavía"; una excepción es
 * "existe y **no** coincide", que no puede tratarse como "hay que copiar de
 * nuevo": pisarla borraría la evidencia de que alguien la alteró.
 *
 * Es **pública** porque esas tres respuestas son exactamente las que necesita la
 * sonda del retiro, que tiene que decidir sin escribir y sin recibir nada de
 * quien pregunta. Reescribirla aparte habría sido más caro y menos fiel: dos
 * predicados sobre la misma propiedad se desincronizan.
 */
export async function fronteraPublicada(fs, frontier, esperados, label) {
  if (!(await existe(fs, frontier, `${label}.frontier.lstat`))) return false;
  try {
    await verifyTree({ fs, root: frontier, expected: esperados, label: `${label}.verify.published` });
    return true;
  } catch (error) {
    const rutas = rutasDelFallo(error);
    throw new EngineError(
      'VERIFY_FAILED',
      `la frontera publicada de ${path.basename(frontier)} no coincide con el origen: ` +
        `${rutas.join(', ')}`,
      { path: frontier, detail: error.detail ?? null },
    );
  }
}

async function publicar({ fs, flowDir, frontier, staging, incluidos, label }) {
  await enEtapa('COPY_FAILED', staging, async () => {
    await fs.mkdir(staging, `${label}.stage.create`, { recursive: true });
    await fs.fsyncDir(path.dirname(staging), `${label}.stage.fsync-parent`);
    await copyTree({ fs, from: flowDir, to: staging, entries: incluidos, label: `${label}.copy` });
    await fsyncTreeDirs({ fs, root: staging, entries: incluidos, label: `${label}.stage` });
  });

  // La verificación va en su **propio** tramo: si contara como "falló la copia",
  // un destino que no verifica se reportaría como un problema de escritura.
  await enEtapa('VERIFY_FAILED', staging, () =>
    verifyTree({ fs, root: staging, expected: incluidos, label: `${label}.verify.staging` }),
  );

  await enEtapa('PUBLISH_FAILED', frontier, async () => {
    await fs.mkdir(path.dirname(frontier), `${label}.publish.mkdir`, { recursive: true });
    await fs.rename(staging, frontier, `${label}.publish.rename`);
    await fs.fsyncDir(path.dirname(frontier), `${label}.publish.fsync-dir`);
  });

  await enEtapa('VERIFY_FAILED', frontier, () =>
    verifyTree({ fs, root: frontier, expected: incluidos, label: `${label}.verify.published` }),
  );
}

/** Escribe si el contenido difiere. Devuelve si hubo escritura. */
async function escribirSiCambia(fs, ruta, contenido, codigo, label) {
  if ((await leerSiExiste(fs, ruta, `${label}.read`)) === contenido) return false;
  await writeDerived(
    async () => {
      await fs.mkdir(path.dirname(ruta), `${label}.mkdir`, { recursive: true });
      await fs.writeFileAtomic(ruta, Buffer.from(contenido, 'utf8'), label);
    },
    codigo,
    { path: ruta },
  );
  return true;
}

/**
 * Archiva un flujo en el vault.
 *
 * @returns {Promise<{status: 'ARCHIVED'|'ALREADY_ARCHIVED', counts: {included:number, omitted:number}}>}
 */
export async function runVaultTransaction({
  fs,
  vaultRoot,
  repoSlug,
  flowId,
  flowDir,
  summary,
  label = 'archive',
}) {
  return withFlowLock(vaultRoot, flowId, async () => {
    const { frontier, nodePath, indexPaths } = resolveLayout(vaultRoot, repoSlug, flowId);

    await ensureVaultRepo(vaultRoot);
    // Las rutas que este archivado posee. Todo lo demás que esté sucio es ajeno,
    // y el commit se lo llevaría puesto.
    const propias = [frontier, nodePath, ...indexPaths, path.join(vaultRoot, LOG_FILENAME)].map((p) =>
      path.relative(vaultRoot, p),
    );
    // Antes de escribir un solo byte.
    await assertVaultClean(vaultRoot, propias);

    // Lectura del origen. Es lo único que se hace con él, en todo el archivo.
    const inventario = await scanInventory({ fs, root: flowDir, label: `${label}.scan` });
    const incluidos = inventario.files.filter((e) => isCopiable(e.path));
    const counts = { included: incluidos.length, omitted: inventario.files.length - incluidos.length };
    const fingerprint = computeSourceFingerprint(
      buildSourceInventoryV2({ files: incluidos, directories: [] }),
    );

    // Un staging de una corrida muerta bloquea el reintento, porque `copyTree`
    // crea con exclusión. Se barre antes de intentar nada.
    await discardOrphanStagings({ fs, parentDir: path.dirname(frontier), label: `${label}.stage.discard` });

    let reconstruido = false;
    if (!(await fronteraPublicada(fs, frontier, incluidos, label))) {
      await publicar({
        fs,
        flowDir,
        frontier,
        staging: resolveStagingPath(vaultRoot, repoSlug, flowId, fingerprint.slice(0, 8)),
        incluidos,
        label,
      });
      reconstruido = true;
    }

    // ── Postcondiciones ────────────────────────────────────────────────────────
    const metadata = await resolveMetadata({ flowDir, flowId, repoSlug });
    const nodo = buildNode({ metadata, documents: incluidos.map((e) => e.path), summary });
    if (await escribirSiCambia(fs, nodePath, nodo, 'NODE_WRITE_FAILED', `${label}.node`)) {
      reconstruido = true;
    }

    // Los índices se renderizan **después** del nodo: los leen del disco.
    for (const [ruta, contenido] of await renderIndexes(vaultRoot)) {
      if (await escribirSiCambia(fs, ruta, contenido, 'INDEX_WRITE_FAILED', `${label}.index`)) {
        reconstruido = true;
      }
    }

    const conCommit = await anclaEnHead(vaultRoot, propias);
    if (!conCommit || reconstruido) {
      await appendLogEntry({
        fs,
        vaultRoot,
        entry: formatLogEntry({ timestamp: metadata.date, repoSlug, flowId, counts }),
        label: `${label}.log`,
      });
      await commitFlow({ vaultRoot, flowId, paths: propias });
      if (!conCommit) reconstruido = true;
    }

    return { status: reconstruido ? 'ARCHIVED' : 'ALREADY_ARCHIVED', counts, fingerprint };
  });
}
