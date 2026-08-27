/**
 * El verbo `archive`.
 *
 * En el árbol de origen este archivo tenía veintitrés líneas y delegaba entero en
 * `source-command.mjs`, que resolvía completitud, predicados de estado, políticas
 * de selección y retiro. Todo eso se fue: lo que queda es resolver dónde está el
 * vault, comprobar la matriz de rutas y llamar a la transacción.
 *
 * **No evalúa ningún predicado de estado.** El verbo del que se rescata esto
 * exigía `plan.md:status=done` antes de archivar, y tenía sentido cuando archivar
 * **borraba el origen**. Sin retiro, negarse a copiar un flujo a medias no
 * protege de nada y sí deja fuera del vault lo que ese flujo ya decidió.
 */

import path from 'node:path';

import {
  discoverRepoRootFromDir,
  assertPathMatrix,
  resolveVaultRootWithDefault,
} from '../config.mjs';
import { ContractError } from '../contracts.mjs';
import { runVaultTransaction } from '../engine-vault.mjs';
import { deriveFlowId } from '../identity.mjs';
import { slugEfectivo } from '../repo-slug.mjs';

function exigir(flags, nombre) {
  const valor = flags[nombre];
  if (typeof valor !== 'string' || valor.length === 0) {
    throw new ContractError('USAGE', `archive exige --${nombre}`);
  }
  return valor;
}

export async function archiveCommand({ fs, flags, homeDir = null, label = 'archive' }) {
  const flowDir = path.resolve(exigir(flags, 'from'));
  const summary = exigir(flags, 'summary');
  const archivedRoot = path.dirname(flowDir);

  const repoRoot = await discoverRepoRootFromDir({ fs, dir: archivedRoot, label: `${label}.repo` });
  const { root: vaultRoot } = await resolveVaultRootWithDefault({
    fs,
    configPath: flags.config ?? null,
    vaultRoot: flags['vault-root'] ?? null,
    repoRoot,
    homeDir,
    label: `${label}.config`,
  });

  // Antes de tocar un byte: el vault tiene que ser disjunto del repositorio y de
  // la raíz de archivados, y el flujo tiene que ser hijo directo de esa raíz.
  const rutas = await assertPathMatrix({ vaultRoot, repoRoot, archivedRoot, flowDir });

  // El `flow-id` sale del basename y no necesita tocar el vault, así que se deriva
  // **antes** que el slug, que sí lo lee. Dentro del literal se evaluaba después, y
  // un directorio mal nombrado pagaba una vuelta al vault para fallar por algo que
  // se sabía sin salir de la ruta.
  const flowId = deriveFlowId(path.basename(rutas.flowDir));

  const resultado = await runVaultTransaction({
    fs,
    vaultRoot: rutas.vaultRoot,
    repoSlug: await slugEfectivo({ fs, vaultRoot: rutas.vaultRoot, repoRoot: rutas.repoRoot, label }),
    flowId,
    flowDir: rutas.flowDir,
    summary,
    label,
  });

  return { status: resultado.status, counts: resultado.counts, vaultRoot: rutas.vaultRoot };
}
