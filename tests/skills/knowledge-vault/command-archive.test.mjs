/**
 * El verbo `archive`, y la propiedad que lo define: **no evalúa estado**.
 *
 * La versión de la que se rescata esto exigía un predicado —`plan.md:status=done`—
 * antes de archivar. Tenía sentido cuando el archivado **borraba el origen**:
 * había que estar seguro de que el flujo estaba terminado. Este flujo no borra
 * nada, así que negarse a copiar un flujo a medias no protege de nada y sí impide
 * consultar lo que ese flujo ya decidió.
 *
 * Acá también se ejerce `E1`: sin `--config` ni `--vault-root`, la raíz sale de
 * `<raíz del repo>/.specify/config.yml`. Es lo que permite que un repositorio
 * archive en un vault y otro en otro sin configuración global.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fsp from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

import { DurableFs } from '../../../skills/knowledge-vault/scripts/lib/durable-fs.mjs';
import { archiveCommand } from '../../../skills/knowledge-vault/scripts/lib/commands/archive.mjs';
import { createSandbox } from './helpers/sandbox.mjs';

const ejecutar = promisify(execFile);

const PLAN = (estado) =>
  ['---', 'id: abc-1', 'branch: feature/abc-1', `status: ${estado}`,
   'created_at: 2026-03-04T12:00:00-03:00', '---', '', '# Exportar el carrito', ''].join('\n');

async function escena(t, { plan = PLAN('done'), conConfig = false } = {}) {
  const caja = await createSandbox(t);
  const repoRoot = path.join(caja.reposDir, 'proyecto');
  const flowDir = path.join(repoRoot, '.plans', 'archived', 'abc-1');
  const vault = path.join(caja.vaultsDir, 'dev-memory');
  await fsp.mkdir(path.join(flowDir, 'cross-review'), { recursive: true });
  await fsp.mkdir(vault, { recursive: true });
  await fsp.writeFile(path.join(flowDir, 'spec.md'), '# Exportar el carrito\n', 'utf8');
  if (plan !== null) await fsp.writeFile(path.join(flowDir, 'plan.md'), plan, 'utf8');
  await fsp.writeFile(path.join(flowDir, 'notas.txt'), 'no viaja\n', 'utf8');
  await fsp.writeFile(path.join(flowDir, 'cross-review', 'v.md'), 'tampoco\n', 'utf8');
  // El repositorio de origen, para que `discoverRepoRoot` lo encuentre.
  await ejecutar('git', ['init', '-q', repoRoot]);
  if (conConfig) {
    await fsp.mkdir(path.join(repoRoot, '.specify'), { recursive: true });
    await fsp.writeFile(
      path.join(repoRoot, '.specify', 'config.yml'),
      `stack: node\nknowledge-vault:\n  path_vault: ${vault}\ntracker: none\n`,
      'utf8',
    );
  }
  return { caja, repoRoot, flowDir, vault };
}

const correr = (flags, { cwd, fs = new DurableFs() } = {}) =>
  archiveCommand({ fs, flags, cwd, homeDir: '/home/nadie' });

test('[AC-1] archiva y devuelve ARCHIVED, con los documentos byte-idénticos', async (t) => {
  const e = await escena(t);
  const r = await correr({ from: e.flowDir, summary: 'Exportación con separador configurable.', 'vault-root': e.vault });
  assert.equal(r.status, 'ARCHIVED');
  const frontera = path.join(e.vault, 'projects', 'proyecto', 'sdd', 'abc-1');
  assert.deepEqual((await fsp.readdir(frontera)).sort(), ['plan.md', 'spec.md']);
  assert.equal(
    await fsp.readFile(path.join(frontera, 'spec.md'), 'utf8'),
    await fsp.readFile(path.join(e.flowDir, 'spec.md'), 'utf8'),
  );
});

test('[AC-1] no evalúa ningún predicado de estado', async (t) => {
  for (const plan of [PLAN('implementing'), PLAN('planned'), null]) {
    const e = await escena(t, { plan });
    const r = await correr({ from: e.flowDir, summary: 'Un resumen cualquiera.', 'vault-root': e.vault });
    assert.equal(r.status, 'ARCHIVED', `plan: ${plan === null ? 'ausente' : plan.match(/status: \w+/)[0]}`);
  }
});

test('[AC-1] rearchivar sin cambios devuelve ALREADY_ARCHIVED', async (t) => {
  const e = await escena(t);
  const flags = { from: e.flowDir, summary: 'Un resumen.', 'vault-root': e.vault };
  assert.equal((await correr(flags)).status, 'ARCHIVED');
  assert.equal((await correr(flags)).status, 'ALREADY_ARCHIVED');
});

test('[AC-1] sin --from o sin --summary es USAGE', async (t) => {
  const e = await escena(t);
  for (const flags of [{ summary: 'x', 'vault-root': e.vault }, { from: e.flowDir, 'vault-root': e.vault }]) {
    await assert.rejects(() => correr(flags), (error) => {
      assert.equal(error.code, 'USAGE');
      return true;
    });
  }
});

test('[AC-1] E1 — sin banderas de raíz, la toma del config del proyecto', async (t) => {
  const e = await escena(t, { conConfig: true });
  const r = await correr({ from: e.flowDir, summary: 'Un resumen.' }, { cwd: e.flowDir });
  assert.equal(r.status, 'ARCHIVED');
  await assert.doesNotReject(() => fsp.stat(path.join(e.vault, 'projects', 'proyecto', 'sdd', 'abc-1.md')));
});

test('[AC-1] E1 — dos proyectos con configs distintas archivan en vaults distintos', async (t) => {
  const uno = await escena(t, { conConfig: true });
  const dos = await escena(t, { conConfig: true });
  await correr({ from: uno.flowDir, summary: 'Del primero.' }, { cwd: uno.flowDir });
  await correr({ from: dos.flowDir, summary: 'Del segundo.' }, { cwd: dos.flowDir });
  assert.notEqual(uno.vault, dos.vault);
  for (const e of [uno, dos]) {
    await assert.doesNotReject(() => fsp.stat(path.join(e.vault, 'projects', 'proyecto', 'sdd', 'abc-1.md')), e.vault);
  }
});

test('[AC-1] sin config y sin banderas, no se inventa un vault', async (t) => {
  const e = await escena(t);
  await assert.rejects(() => correr({ from: e.flowDir, summary: 'x' }, { cwd: e.flowDir }), (error) => {
    assert.equal(error.code, 'NO_VAULT');
    return true;
  });
});

test('[AC-15] un vault dentro del repositorio se rechaza antes de copiar nada', async (t) => {
  const e = await escena(t);
  const adentro = path.join(e.repoRoot, 'vault');
  await fsp.mkdir(adentro, { recursive: true });
  await assert.rejects(
    () => correr({ from: e.flowDir, summary: 'x', 'vault-root': adentro }),
    /disjunto/i,
  );
  assert.deepEqual(await fsp.readdir(adentro), [], 'llegó a escribir en el vault rechazado');
});
