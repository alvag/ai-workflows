/**
 * El identificador de un repositorio dentro del vault, resuelto de una sola forma.
 *
 * Vive aparte porque lo consumen **tres** verbos —`archive`, `migrate` y
 * `retire`— y porque cablea tres módulos que no se conocen entre sí: el registro
 * del vault, las señales de Git y el derivado heurístico. Meterlo en cualquiera
 * de los tres lo acoplaría a los otros dos; meterlo en un verbo lo dejaría
 * duplicado en los otros, que es exactamente cómo se partió antes.
 */

import path from 'node:path';

import { deriveStem, identidadesCompatibles, parseRegistroIdentidades } from './identity.mjs';
import { senalesDelRepositorio } from './vault-git.mjs';
import { readIdentitiesFile, resolveRepoSlug } from './vault-store.mjs';

/**
 * Para los verbos que **copian**: la identidad declarada si existe, y el derivado
 * si no. Copiar bajo un nombre heurístico es benigno; el retiro no puede caer a
 * nada y por eso usa la resolución estricta.
 */
export async function slugEfectivo({ fs, vaultRoot, repoRoot, label = 'slug' }) {
  const senales = await senalesDelRepositorio(repoRoot);
  const registro = parseRegistroIdentidades(await readIdentitiesFile({ fs, vaultRoot, label: `${label}.ident` }));
  const { repoSlug } = resolveRepoSlug({
    compatibles: identidadesCompatibles({ registro, senales }).map((e) => e.repoId),
    derivado: deriveStem(path.basename(repoRoot)),
  });
  return repoSlug;
}
