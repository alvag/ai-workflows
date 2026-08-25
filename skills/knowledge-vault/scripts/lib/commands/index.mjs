/**
 * El verbo `index`: regenera los índices del vault desde el vault.
 *
 * Existe porque los índices son **derivados**. Si uno se edita a mano, o queda a
 * medias por una corrida muerta, no hay que reconstruir el vault: se vuelven a
 * generar. Y como el generador es determinista, correrlo sobre un vault sano no
 * cambia un byte, que es la forma barata de comprobar que están al día.
 *
 * **No commitea.** Regenerar es una operación de mantenimiento y quién decide qué
 * entra a la historia es quien archiva; dejar que este verbo commitee metería en
 * el log entradas que no nombran ningún flujo.
 */

import path from 'node:path';

import { discoverRepoRootFromDir, resolveVaultRootWithDefault } from '../config.mjs';
import { renderIndexes } from '../index-render.mjs';
import { writeDerived } from '../vault-store.mjs';

async function leerSiExiste(fs, ruta, label) {
  try {
    return (await fs.readFile(ruta, label)).toString('utf8');
  } catch (error) {
    if (error?.code === 'ENOENT' || error?.cause?.code === 'ENOENT') return null;
    throw error;
  }
}

export async function indexCommand({ fs, flags, cwd = process.cwd(), homeDir = null, label = 'index' }) {
  const repoRoot = await discoverRepoRootFromDir({ fs, dir: cwd, label: `${label}.repo` });
  const { root: vaultRoot } = await resolveVaultRootWithDefault({
    fs,
    configPath: flags.config ?? null,
    vaultRoot: flags['vault-root'] ?? null,
    repoRoot,
    homeDir,
    label: `${label}.config`,
  });

  const reescritos = [];
  for (const [ruta, contenido] of await renderIndexes(vaultRoot)) {
    if ((await leerSiExiste(fs, ruta, `${label}.read`)) === contenido) continue;
    await writeDerived(
      async () => {
        await fs.mkdir(path.dirname(ruta), `${label}.mkdir`, { recursive: true });
        await fs.writeFileAtomic(ruta, Buffer.from(contenido, 'utf8'), `${label}.write`);
      },
      'INDEX_WRITE_FAILED',
      { path: ruta },
    );
    reescritos.push(path.relative(vaultRoot, ruta));
  }
  return { status: 'INDEX_OK', vaultRoot, reescritos: reescritos.sort() };
}
