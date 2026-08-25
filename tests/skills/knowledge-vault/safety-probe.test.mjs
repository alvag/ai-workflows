/**
 * La sonda de solo lectura que autoriza un borrado (AC-2, AC-10, AC-12).
 *
 * Lo que se prueba acá no es que la sonda "funcione": es que **no dependa de
 * nada que provea quien pregunta** y que **no escriba**. Esas dos son las
 * propiedades por las que existe, y la segunda se acredita por **dos vías
 * independientes** a propósito: el registro de operaciones del sistema de
 * archivos inyectado —que ve lo que la sonda pidió— y un snapshot externo de las
 * dos raíces —que ve lo que quedó—. Una vía sola no distingue "no escribió" de
 * "el registro no lo vio".
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

import { DurableFs, Recorder } from '../../../skills/knowledge-vault/scripts/lib/durable-fs.mjs';
import { runVaultTransaction } from '../../../skills/knowledge-vault/scripts/lib/engine-vault.mjs';
import { estaASalvo, CAUSAS } from '../../../skills/knowledge-vault/scripts/lib/safety-probe.mjs';
import { resolveLayout } from '../../../skills/knowledge-vault/scripts/lib/vault-store.mjs';
import { anclaEnHead } from '../../../skills/knowledge-vault/scripts/lib/vault-git.mjs';
import { createSandbox } from './helpers/sandbox.mjs';
import { snapshotTree } from './helpers/tree-snapshot.mjs';

const git = (cwd, ...args) => promisify(execFile)('git', ['-C', cwd, ...args]);
const REPO = 'ai-workflows';

const PLAN = [
  '---', 'id: abc-1', 'branch: feature/abc-1', 'status: done',
  'created_at: 2026-03-04T12:00:00-03:00', '---', '', '# Plan', '',
].join('\n');

async function origen(caja, flowId, extra = {}) {
  const dir = path.join(caja.reposDir, 'proyecto', '.plans', 'archived', flowId);
  await fs.mkdir(dir, { recursive: true });
  const archivos = { 'spec.md': '# Exportar\n\ncriterios\n', 'plan.md': PLAN, ...extra };
  for (const [rel, contenido] of Object.entries(archivos)) {
    await fs.mkdir(path.dirname(path.join(dir, rel)), { recursive: true });
    await fs.writeFile(path.join(dir, rel), contenido, 'utf8');
  }
  return dir;
}

function archivar(vault, flowDir, flowId, summary = 'un resumen') {
  return runVaultTransaction({
    fs: new DurableFs(),
    vaultRoot: vault,
    repoSlug: REPO,
    flowId,
    flowDir,
    summary,
  });
}

/** Un vault con un flujo ya archivado, listo para sondear. */
async function escena(t, { flowId = 'abc-1', summary = 'un resumen', extra = {} } = {}) {
  const caja = await createSandbox(t);
  const vault = await caja.makeVault('dev-memory');
  const flowDir = await origen(caja, flowId, extra);
  await archivar(vault, flowDir, flowId, summary);
  return { caja, vault, flowDir, flowId };
}

const sondear = (vault, flowDir, flowId, fsi = new DurableFs()) =>
  estaASalvo({ fs: fsi, vaultRoot: vault, repoId: REPO, flowId, flowDir });

// ── AC-2 · no escribe, y no recibe el resumen ────────────────────────────────

test('[AC-2] la sonda no escribe: el registro de operaciones no trae ninguna mutación', async (t) => {
  const { vault, flowDir, flowId } = await escena(t);
  const grabador = new Recorder();

  const r = await sondear(vault, flowDir, flowId, new DurableFs({ recorder: grabador }));
  assert.equal(r.aSalvo, true, `la escena no quedó a salvo: ${r.causa}`);

  const MUTAN = new Set([
    'mkdir', 'openExclusive', 'copyFile', 'writeFile', 'writeFileAtomic',
    'rename', 'unlink', 'rmTree', 'removeEmptyDir', 'fsyncFile', 'fsyncDir',
  ]);
  // `entries` y no `ops()`: `ops()` devuelve strings `op:label`, así que
  // filtrar por `.op` sobre ellas da siempre vacío y la comprobación queda
  // muerta pareciendo verde.
  const mutaciones = grabador.entries.filter((e) => MUTAN.has(e.op));
  assert.deepEqual(mutaciones.map((e) => `${e.op}:${e.label}`), []);
  // El registro tiene que haber visto ALGO: cero operaciones también da cero
  // mutaciones, y ese verde no dice nada.
  assert.ok(grabador.entries.length >= 5, `el registro vio ${grabador.entries.length} operaciones`);
});

test('[AC-2] la sonda no escribe: el snapshot externo de las dos raíces es idéntico', async (t) => {
  const { vault, flowDir, flowId } = await escena(t);
  const antesVault = await snapshotTree(vault);
  const antesOrigen = await snapshotTree(flowDir);

  await sondear(vault, flowDir, flowId);

  assert.deepEqual(await snapshotTree(vault), antesVault, 'la sonda movió bytes en el vault');
  assert.deepEqual(await snapshotTree(flowDir), antesOrigen, 'la sonda tocó el origen');
});

test('[AC-2] el veredicto no depende del resumen con que se archivó', async (t) => {
  // Es la premisa heredada que se cayó al medirla: `ALREADY_ARCHIVED` cambia de
  // valor —y reescribe el nodo— según el `--summary` que reciba. Esta sonda no
  // recibe ninguno, así que dos flujos archivados con resúmenes distintos tienen
  // que dar el mismo veredicto y dejar sus nodos intactos.
  const a = await escena(t, { flowId: 'abc-1', summary: 'primer resumen' });
  const flowB = await origen(a.caja, 'abc-2');
  await archivar(a.vault, flowB, 'abc-2', 'un resumen completamente distinto');

  const antes = await snapshotTree(a.vault);
  const rA = await sondear(a.vault, a.flowDir, 'abc-1');
  const rB = await sondear(a.vault, flowB, 'abc-2');

  assert.equal(rA.aSalvo, true);
  assert.equal(rB.aSalvo, true);
  assert.deepEqual(await snapshotTree(a.vault), antes, 'sondear reescribió algo');
});

// ── AC-10 · el conjunto vacío se rechaza ─────────────────────────────────────

test('[AC-10] un flujo sin contenido copiable se rechaza en vez de pasar vacuamente', async (t) => {
  const caja = await createSandbox(t);
  const vault = await caja.makeVault('dev-memory');
  // Sólo andamiaje: nada de esto viaja al vault, así que el conjunto es vacío.
  const flowDir = await caja.makeTree(
    path.join(caja.reposDir, 'proyecto', '.plans', 'archived', 'vacio'),
    { 'notas.txt': 'no viaja\n', 'cross-review/veredicto.md': 'tampoco\n' },
  );

  const r = await sondear(vault, flowDir, 'vacio');
  assert.equal(r.aSalvo, false);
  assert.equal(r.causa, CAUSAS.EMPTY_SET);
});

test('[AC-10] el rechazo del vacío ocurre antes de comparar, no por comparar', async (t) => {
  // Con origen vacío **y** vault vacío, comparar dos conjuntos vacíos sale
  // verdadero. El rechazo tiene que llegar antes, y decirlo con su causa: si
  // llegara por la frontera, la causa sería otra y el flujo se destruiría en
  // cuanto alguien publicara una frontera vacía.
  const caja = await createSandbox(t);
  const vault = await caja.makeVault('dev-memory');
  const flowDir = await caja.makeTree(
    path.join(caja.reposDir, 'proyecto', '.plans', 'archived', 'pelado'), {},
  );
  const { frontier } = resolveLayout(vault, REPO, 'pelado');
  await fs.mkdir(frontier, { recursive: true });

  const r = await sondear(vault, flowDir, 'pelado');
  assert.equal(r.aSalvo, false);
  assert.equal(r.causa, CAUSAS.EMPTY_SET, 'el vacío se coló por otra rama');
});

// ── AC-12 · las cuatro postcondiciones, ancladas en HEAD ─────────────────────

test('[AC-12] con las cuatro postcondiciones, el flujo está a salvo', async (t) => {
  const { vault, flowDir, flowId } = await escena(t);
  assert.deepEqual(await sondear(vault, flowDir, flowId), { aSalvo: true, causa: null, faltantes: [] });
});

test('[AC-12] sin frontera publicada no está a salvo', async (t) => {
  const { vault, flowDir, flowId } = await escena(t);
  const { frontier } = resolveLayout(vault, REPO, flowId);
  await fs.rm(frontier, { recursive: true, force: true });

  const r = await sondear(vault, flowDir, flowId);
  assert.equal(r.aSalvo, false);
  assert.equal(r.causa, CAUSAS.FRONTIER_MISSING);
});

test('[AC-12] con la frontera alterada no está a salvo, y nombra la ruta', async (t) => {
  const { vault, flowDir, flowId } = await escena(t);
  const { frontier } = resolveLayout(vault, REPO, flowId);
  await fs.writeFile(path.join(frontier, 'spec.md'), '# Alterado a mano\n', 'utf8');

  const r = await sondear(vault, flowDir, flowId);
  assert.equal(r.aSalvo, false);
  assert.equal(r.causa, CAUSAS.VERIFY_FAILED);
  assert.ok(r.faltantes.some((p) => p.includes('spec.md')), `faltantes: ${r.faltantes.join(', ')}`);
});

test('[AC-12] sin el nodo, o sin los índices, no está a salvo', async (t) => {
  const sinNodo = await escena(t, { flowId: 'abc-1' });
  const { nodePath } = resolveLayout(sinNodo.vault, REPO, 'abc-1');
  await fs.rm(nodePath);
  const r1 = await sondear(sinNodo.vault, sinNodo.flowDir, 'abc-1');
  assert.equal(r1.causa, CAUSAS.NODE_MISSING);

  const sinIndice = await escena(t, { flowId: 'abc-1' });
  const { indexPaths } = resolveLayout(sinIndice.vault, REPO, 'abc-1');
  await fs.rm(indexPaths[3]);
  const r2 = await sondear(sinIndice.vault, sinIndice.flowDir, 'abc-1');
  assert.equal(r2.causa, CAUSAS.INDEX_MISSING);
  assert.deepEqual(r2.faltantes, [indexPaths[3]]);
});

test('[AC-12] escrito en disco pero sin commitear no está anclado', async (t) => {
  const { vault, flowDir, flowId } = await escena(t);
  // Todo sigue en su sitio; lo único que se deshace es el commit. Es el caso que
  // separa "existe" de "está anclado", y sin él las cuatro postcondiciones se
  // satisfacen con material que ningún commit respalda.
  // El vault tiene un solo commit, así que no hay `HEAD~1` al que volver: se
  // borra la referencia y el contenido queda en el árbol, escrito y sin anclar.
  await git(vault, 'update-ref', '-d', 'HEAD');

  const r = await sondear(vault, flowDir, flowId);
  assert.equal(r.aSalvo, false);
  assert.equal(r.causa, CAUSAS.NOT_ANCHORED);
});

test('[AC-12] el asunto del commit no autoriza: revertido, el ancla dice que no', async (t) => {
  const { vault, flowDir, flowId } = await escena(t);
  const { frontier, nodePath, indexPaths } = resolveLayout(vault, REPO, flowId);
  const propias = [frontier, nodePath, ...indexPaths].map((p) => path.relative(vault, p));
  assert.equal(await anclaEnHead(vault, propias), true, 'la escena no arrancó anclada');

  // Se revierte el commit: su asunto sigue en la historia —`git log` lo muestra—
  // pero el contenido ya no está en HEAD. La comparación por asunto que había
  // antes decía que sí; el ancla dice que no, que es lo que un borrado necesita.
  await git(vault, 'revert', '--no-edit', 'HEAD');
  const { stdout: historia } = await git(vault, 'log', '--format=%s');
  assert.ok(historia.includes(flowId), 'el asunto tiene que seguir en la historia');

  assert.equal(await anclaEnHead(vault, propias), false);
  const r = await sondear(vault, flowDir, flowId);
  assert.equal(r.aSalvo, false);
  assert.equal(r.causa, CAUSAS.FRONTIER_MISSING);
});
