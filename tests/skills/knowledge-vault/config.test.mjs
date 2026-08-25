/**
 * La matriz de rutas de AC-15.
 *
 * El criterio ingenuo —"ninguna ruta se solapa con otra"— **bloquea el archivado
 * entero**: el directorio de un flujo vive dentro del repositorio por
 * construcción, así que exigir que no se solapen prohíbe el caso normal. Lo que
 * hay que exigir es más fino y son dos cosas distintas:
 *
 *   · el **vault** es disjunto del repositorio y de la raíz de archivados
 *     —si viviera adentro, archivar se copiaría a sí mismo—;
 *   · el **flujo** es hijo **directo** de la raíz de archivados.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';

import { assertPathMatrix } from '../../../skills/knowledge-vault/scripts/lib/config.mjs';
import { createSandbox } from './helpers/sandbox.mjs';

/** Arma un árbol realista y devuelve sus rutas ya creadas en disco. */
async function escenario(t, { vaultDentroDe = null } = {}) {
  const caja = await createSandbox(t);
  const repoRoot = path.join(caja.reposDir, 'proyecto');
  const archivedRoot = path.join(repoRoot, '.plans', 'archived');
  const flowDir = path.join(archivedRoot, 'un-flujo');
  const vaultRoot =
    vaultDentroDe === 'repo' ? path.join(repoRoot, 'vault')
    : vaultDentroDe === 'archivados' ? path.join(archivedRoot, 'vault')
    : path.join(caja.vaultsDir, 'dev-memory');
  for (const d of [flowDir, vaultRoot]) await fs.mkdir(d, { recursive: true });
  return { caja, repoRoot, archivedRoot, flowDir, vaultRoot };
}

test('[AC-15] acepta el caso normal: el flujo vive dentro del repositorio', async (t) => {
  const e = await escenario(t);
  // Sin esta aceptación la skill no puede archivar nada: `.plans/<id>` está
  // dentro del repositorio siempre, y una regla de "sin solapamiento" lo veta.
  await assert.doesNotReject(() => assertPathMatrix(e));
});

test('[AC-15] rechaza un vault dentro del repositorio', async (t) => {
  const e = await escenario(t, { vaultDentroDe: 'repo' });
  await assert.rejects(() => assertPathMatrix(e), /disjunto|repositorio/i);
});

test('[AC-15] rechaza un vault dentro de la raíz de archivados', async (t) => {
  const e = await escenario(t, { vaultDentroDe: 'archivados' });
  await assert.rejects(() => assertPathMatrix(e), /disjunto|archivad/i);
});

test('[AC-15] rechaza un repositorio dentro del vault: disjunto va en las dos direcciones', async (t) => {
  const e = await escenario(t);
  const repoAdentro = path.join(e.vaultRoot, 'proyecto');
  const archivados = path.join(repoAdentro, '.plans', 'archived');
  await fs.mkdir(path.join(archivados, 'un-flujo'), { recursive: true });
  await assert.rejects(
    () => assertPathMatrix({ ...e, repoRoot: repoAdentro, archivedRoot: archivados,
                             flowDir: path.join(archivados, 'un-flujo') }),
    /disjunto/i,
  );
});

test('[AC-15] rechaza un flujo que es nieto y no hijo directo de archivados', async (t) => {
  const e = await escenario(t);
  const nieto = path.join(e.archivedRoot, 'un-flujo', 'adentro');
  await fs.mkdir(nieto, { recursive: true });
  await assert.rejects(() => assertPathMatrix({ ...e, flowDir: nieto }), /hijo directo/i);
});

test('[AC-15] rechaza un flujo que no cuelga de la raíz de archivados', async (t) => {
  const e = await escenario(t);
  const afuera = path.join(e.repoRoot, '.plans', 'en-curso');
  await fs.mkdir(afuera, { recursive: true });
  await assert.rejects(() => assertPathMatrix({ ...e, flowDir: afuera }), /hijo directo/i);
});

test('[AC-15] resuelve enlaces simbólicos antes de comparar', async (t) => {
  const e = await escenario(t);
  // Un vault que es un enlace al repositorio NO es disjunto, por más que sus
  // rutas textuales no compartan un solo prefijo.
  const enlace = path.join(e.caja.vaultsDir, 'enlace-al-repo');
  await fs.symlink(e.repoRoot, enlace, 'dir');
  await assert.rejects(() => assertPathMatrix({ ...e, vaultRoot: enlace }), /disjunto/i);
});

test('[AC-15] la raíz de archivados no tiene por qué llamarse archived', async (t) => {
  const e = await escenario(t);
  const otra = path.join(e.repoRoot, 'historico');
  const flujo = path.join(otra, 'un-flujo');
  await fs.mkdir(flujo, { recursive: true });
  await assert.doesNotReject(() => assertPathMatrix({ ...e, archivedRoot: otra, flowDir: flujo }));
});
