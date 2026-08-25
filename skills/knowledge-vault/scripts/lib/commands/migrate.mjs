/**
 * El verbo `migrate`: archivar un directorio entero de flujos.
 *
 * **Toda la entrada se valida antes de escribir un byte.** No es prolijidad: sin
 * manifiesto ni conteo esperado, un vault al que le falta un flujo es
 * indistinguible de uno completo. Quien lo consulte va a leer el índice y a
 * concluir que ese flujo nunca existió. Un fallo total se arregla con un comando;
 * uno parcial y silencioso no se descubre.
 *
 * De ahí que un resumen faltante frene el lote **entero**, y no sólo su flujo.
 *
 * Lo que cuenta como flujo: un **directorio** hijo de la raíz. Medido en el árbol
 * real, esa raíz tiene 51 entradas y una es un `.md` suelto; contarlo como flujo
 * lo dejaría para siempre sin resumen y bloquearía toda migración.
 */

import path from 'node:path';

import { assertPathMatrix, discoverRepoRootFromDir, resolveVaultRootWithDefault } from '../config.mjs';
import { ContractError } from '../contracts.mjs';
import { runVaultTransaction } from '../engine-vault.mjs';
import { deriveFlowId } from '../identity.mjs';
import { slugEfectivo } from '../repo-slug.mjs';

function exigir(flags, nombre) {
  const valor = flags[nombre];
  if (typeof valor !== 'string' || valor.length === 0) {
    throw new ContractError('USAGE', `migrate exige --${nombre}`);
  }
  return valor;
}

/** Los directorios hijos de la raíz, en orden estable. Un archivo suelto no es un flujo. */
async function flujosDe(fs, archivedRoot, label) {
  const nombres = [];
  for (const { name } of await fs.readDirNames(archivedRoot, `${label}.readdir`)) {
    const info = await fs.lstat(path.join(archivedRoot, name), `${label}.lstat`);
    if (info !== null && info.isDirectory()) nombres.push(name);
  }
  return nombres.sort();
}

/**
 * Parsea el TSV y **acumula todos los problemas** en vez de cortar en el primero:
 * quien tiene que arreglarlo prefiere la lista completa a descubrirla de a uno.
 */
function parsearResumenes(texto) {
  const resumenes = new Map();
  const problemas = [];
  texto.split('\n').forEach((linea, i) => {
    if (linea.trim().length === 0) return;
    const corte = linea.indexOf('\t');
    if (corte === -1) {
      problemas.push(`línea ${i + 1}: no tiene tabulador que separe flujo de resumen`);
      return;
    }
    const flowId = linea.slice(0, corte).trim();
    const resumen = linea.slice(corte + 1).trim();
    if (flowId.length === 0) problemas.push(`línea ${i + 1}: sin id de flujo`);
    else if (resumen.length === 0) problemas.push(`línea ${i + 1}: ${flowId} tiene el resumen vacío`);
    else if (resumenes.has(flowId)) problemas.push(`línea ${i + 1}: ${flowId} aparece dos veces`);
    else resumenes.set(flowId, resumen);
  });
  return { resumenes, problemas };
}

export async function migrateCommand({ fs, flags, homeDir = null, label = 'migrate' }) {
  const archivedRoot = path.resolve(exigir(flags, 'from'));
  const tsvPath = path.resolve(exigir(flags, 'summaries'));

  const repoRoot = await discoverRepoRootFromDir({ fs, dir: archivedRoot, label: `${label}.repo` });
  const { root: vaultRoot } = await resolveVaultRootWithDefault({
    fs,
    configPath: flags.config ?? null,
    vaultRoot: flags['vault-root'] ?? null,
    repoRoot,
    homeDir,
    label: `${label}.config`,
  });

  const flujos = await flujosDe(fs, archivedRoot, label);
  const { resumenes, problemas } = parsearResumenes(
    (await fs.readFile(tsvPath, `${label}.tsv`)).toString('utf8'),
  );
  for (const flujo of flujos) {
    if (!resumenes.has(flujo)) problemas.push(`el flujo ${flujo} no tiene resumen en el TSV`);
  }
  for (const declarado of resumenes.keys()) {
    if (!flujos.includes(declarado)) problemas.push(`el resumen de ${declarado} no apunta a ningún flujo`);
  }

  if (problemas.length > 0) {
    return {
      status: 'BATCH_FAILED',
      message: `la entrada no valida, no se migró ninguno: ${problemas.join('; ')}`,
      problemas,
      archivados: 0,
      yaEstaban: 0,
      fallidos: [],
    };
  }
  // La matriz de rutas, **una vez y antes del lote**. Un vault que cae dentro del
  // repositorio no es un problema de un flujo: lo es de la corrida entera, y
  // descubrirlo en el flujo 37 dejaría 36 ya escritos donde no van. La parte de
  // "hijo directo" queda garantizada por construcción, porque los flujos son los
  // hijos directos que se acaban de enumerar.
  if (flujos.length > 0) {
    await assertPathMatrix({
      vaultRoot,
      repoRoot,
      archivedRoot,
      flowDir: path.join(archivedRoot, flujos[0]),
    });
  }

  if (flags['dry-run'] === true) {
    return { status: 'DRY_RUN', vaultRoot, flujos: flujos.length, archivados: 0, yaEstaban: 0, fallidos: [] };
  }

  const repoSlug = await slugEfectivo({ fs, vaultRoot, repoRoot, label });
  let archivados = 0;
  let yaEstaban = 0;
  const fallidos = [];
  for (const flujo of flujos) {
    try {
      const r = await runVaultTransaction({
        fs,
        vaultRoot,
        repoSlug,
        flowId: deriveFlowId(flujo),
        flowDir: path.join(archivedRoot, flujo),
        summary: resumenes.get(flujo),
        label: `${label}.${flujo}`,
      });
      if (r.status === 'ARCHIVED') archivados += 1;
      else yaEstaban += 1;
    } catch (error) {
      // Se sigue con los demás: frenar acá dejaría el lote a medias **y** sin
      // saber cuántos más habrían fallado, que es la peor de las dos cosas.
      fallidos.push({ flowId: flujo, code: error?.code ?? null, message: error?.message ?? String(error) });
    }
  }

  const hechos = archivados + yaEstaban;
  const status = fallidos.length === 0 ? 'BATCH_OK' : hechos > 0 ? 'BATCH_PARTIAL' : 'BATCH_FAILED';
  return { status, vaultRoot, archivados, yaEstaban, fallidos };
}
