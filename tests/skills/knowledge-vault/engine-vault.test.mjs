/**
 * La transacción de archivado.
 *
 * Dos propiedades la ordenan, y son de naturaleza distinta.
 *
 * **El origen nunca se toca** (AC-2). No es una promesa sobre el camino feliz:
 * se comprueba con una caída inyectada en *cada* punto de escritura, comparando
 * el árbol de origen contra su estado previo. El motor no tiene ninguna llamada
 * capaz de borrar fuera del vault, así que la propiedad es estructural — y el
 * test existe para que siga siéndolo cuando alguien agregue un paso.
 *
 * **`ALREADY_ARCHIVED` exige las cuatro postcondiciones** (AC-6): frontera
 * publicada, nodo escrito, índices regenerados y commit creado. Con "publicado =
 * la frontera existe", una caída entre la publicación y el commit dejaría un
 * flujo que el reintento reporta como completo y que nunca aparece en el índice.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

import { DurableFs, Recorder } from '../../../skills/knowledge-vault/scripts/lib/durable-fs.mjs';
import { runVaultTransaction } from '../../../skills/knowledge-vault/scripts/lib/engine-vault.mjs';
import { resolveLayout } from '../../../skills/knowledge-vault/scripts/lib/vault-store.mjs';
import { createSandbox } from './helpers/sandbox.mjs';
import { snapshotTree } from './helpers/tree-snapshot.mjs';

const git = (cwd, ...args) => promisify(execFile)('git', ['-C', cwd, ...args]);

const PLAN = [
  '---', 'id: abc-1', 'branch: feature/abc-1', 'status: done',
  'created_at: 2026-03-04T12:00:00-03:00', '---', '', '# Plan', '',
].join('\n');

/** Un origen con la forma real, incluido andamiaje que no debe viajar. */
async function origen(caja, flowId = 'abc-1', extra = {}) {
  const dir = path.join(caja.reposDir, 'proyecto', '.plans', 'archived', flowId);
  await fs.mkdir(path.join(dir, 'cross-review'), { recursive: true });
  const archivos = {
    'spec.md': '# Exportar el carrito\n\ncriterios\n',
    'plan.md': PLAN,
    'notas.txt': 'esto no viaja\n',
    'cross-review/veredicto.md': 'esto tampoco\n',
    ...extra,
  };
  for (const [rel, contenido] of Object.entries(archivos)) {
    await fs.writeFile(path.join(dir, rel), contenido, 'utf8');
  }
  return dir;
}

function correr(vault, flowDir, flowId = 'abc-1', opciones = {}) {
  return runVaultTransaction({
    fs: opciones.fs ?? new DurableFs(),
    vaultRoot: vault,
    repoSlug: 'ai-workflows',
    flowId,
    flowDir,
    summary: opciones.summary ?? 'Exportación del carrito con separador configurable.',
  });
}

async function escena(t, extra = {}) {
  const caja = await createSandbox(t);
  const vault = path.join(caja.vaultsDir, 'dev-memory');
  await fs.mkdir(vault, { recursive: true });
  return { caja, vault, flowDir: await origen(caja, 'abc-1', extra) };
}

test('[AC-1] archiva el flujo y los documentos quedan byte-idénticos', async (t) => {
  const { vault, flowDir } = await escena(t);
  const r = await correr(vault, flowDir);
  assert.equal(r.status, 'ARCHIVED');

  const { frontier } = resolveLayout(vault, 'ai-workflows', 'abc-1');
  assert.deepEqual((await fs.readdir(frontier)).sort(), ['plan.md', 'spec.md']);
  for (const doc of ['spec.md', 'plan.md']) {
    assert.equal(
      await fs.readFile(path.join(frontier, doc), 'utf8'),
      await fs.readFile(path.join(flowDir, doc), 'utf8'),
      doc,
    );
  }
});

test('[AC-1] no evalúa ningún predicado de estado', async (t) => {
  // Un flujo a medias y uno sin `plan.md` se archivan con el mismo éxito: la
  // decisión de qué se guarda no es del verbo.
  for (const [caso, extra] of [
    ['implementing', { 'plan.md': PLAN.replace('status: done', 'status: implementing') }],
    ['sin plan.md', { 'plan.md': null }],
  ]) {
    const { vault, flowDir } = await escena(t);
    if (extra['plan.md'] === null) await fs.rm(path.join(flowDir, 'plan.md'));
    else await fs.writeFile(path.join(flowDir, 'plan.md'), extra['plan.md'], 'utf8');
    assert.equal((await correr(vault, flowDir)).status, 'ARCHIVED', caso);
  }
});

test('[AC-2] con éxito, el origen queda idéntico', async (t) => {
  const { vault, flowDir } = await escena(t);
  const antes = await snapshotTree(flowDir);
  await correr(vault, flowDir);
  assert.deepEqual(await snapshotTree(flowDir), antes);
});

test('[AC-2] con una caída inyectada en cada seam, el origen queda idéntico', async (t) => {
  // Primero se enumeran los puntos de escritura reales de una corrida completa,
  // en vez de listarlos a mano: una lista escrita a mano envejece con el motor.
  const grabador = new Recorder();
  const base = await escena(t);
  await correr(base.vault, base.flowDir, 'abc-1', { fs: new DurableFs({ recorder: grabador }) });
  const seams = [...new Set(grabador.succeeded().map((e) => e.label))];
  assert.ok(seams.length >= 5, `se esperaban varios seams y hubo ${seams.length}`);

  for (const seam of seams) {
    const e = await escena(t);
    const antes = await snapshotTree(e.flowDir);
    await correr(e.vault, e.flowDir, 'abc-1', { fs: new DurableFs({ crashAt: seam }) }).catch(() => {});
    assert.deepEqual(await snapshotTree(e.flowDir), antes, `el origen cambió al caer en ${seam}`);
  }
});

/**
 * Las llamadas destructivas y de dónde sale su destino.
 *
 * El AC no dice "no hay destrucción" —hay: el staging se barre, y los temporales
 * de la escritura atómica se reemplazan—; dice que **ninguna tiene destino fuera
 * del vault**. Así que el predicado no busca el nombre de la operación sino qué
 * recibe: si el argumento de una operación destructiva menciona alguna de las
 * variables que llevan el origen, eso es exactamente lo que AC-2 prohíbe.
 *
 * `durable-fs.mjs` queda fuera del barrido a propósito: es la capa primitiva, la
 * que **implementa** `rm` y `rename` sobre la ruta que le den. Incluirla sería
 * pedirle a la primitiva que se autolimite, y el límite es de quien la llama.
 */
const DESTRUCTIVAS = /\b(?:fs\.)?(rmTree|rmdir|unlink|rename)\s*\(([^;]*?)\)/g;
const LLEVA_EL_ORIGEN = /\b(flowDir|sourcePath|origen|source|from)\b/;

function destinosProhibidos(nombre, texto) {
  const hallazgos = [];
  for (const m of texto.matchAll(DESTRUCTIVAS)) {
    const args = m[2];
    if (!LLEVA_EL_ORIGEN.test(args)) continue;
    hallazgos.push(`${nombre}: ${m[1]}(${args.trim()})`);
  }
  return hallazgos;
}

test('[AC-2] el predicado de destinos prohibidos sabe ponerse rojo', () => {
  // Control positivo. Sin esto, un verde no distingue "no hay violaciones" de
  // "el predicado no ve nada", que es la forma en que una guarda miente.
  assert.deepEqual(
    destinosProhibidos('sintetico.mjs', 'await fs.rmTree(flowDir, label);'),
    ['sintetico.mjs: rmTree(flowDir, label)'],
  );
  assert.deepEqual(destinosProhibidos('sintetico.mjs', 'await fs.rmTree(staging, label);'), []);
});

test('[AC-2] ninguna llamada destructiva recibe una ruta del origen', async () => {
  const lib = path.resolve('skills/knowledge-vault/scripts/lib');
  const hallazgos = [];
  const visitar = async (dir) => {
    for (const e of await fs.readdir(dir, { withFileTypes: true })) {
      const abs = path.join(dir, e.name);
      if (e.isDirectory()) { await visitar(abs); continue; }
      if (!e.name.endsWith('.mjs') || e.name === 'durable-fs.mjs') continue;
      hallazgos.push(...destinosProhibidos(path.relative(lib, abs), await fs.readFile(abs, 'utf8')));
    }
  };
  await visitar(lib);
  assert.deepEqual(hallazgos, [], 'hay destrucción cuyo destino sale del origen');
});

test('[AC-3] un documento publicado alterado hace fallar el rearchivado y nombra la ruta', async (t) => {
  const { vault, flowDir } = await escena(t);
  await correr(vault, flowDir);
  const { frontier } = resolveLayout(vault, 'ai-workflows', 'abc-1');
  await fs.writeFile(path.join(frontier, 'spec.md'), '# Alterado a mano\n', 'utf8');
  await git(vault, 'add', '-A');
  await git(vault, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'manoseo');

  await assert.rejects(() => correr(vault, flowDir), (error) => {
    assert.match(String(error.message), /spec\.md/);
    return true;
  });
});

test('[AC-5] rearchivar sin cambios da ALREADY_ARCHIVED, con nodo e índices ya generados', async (t) => {
  const { vault, flowDir } = await escena(t);
  assert.equal((await correr(vault, flowDir)).status, 'ARCHIVED');
  const antes = await snapshotTree(vault);
  const r = await correr(vault, flowDir);
  assert.equal(r.status, 'ALREADY_ARCHIVED');
  // El nodo y los índices no son sobrantes de la frontera: viven fuera de ella.
  assert.deepEqual(await snapshotTree(vault), antes, 'el rearchivado movió bytes');
});

test('[AC-6] una caída antes del nodo se reconstruye y no reporta completo', async (t) => {
  const { vault, flowDir } = await escena(t);
  await correr(vault, flowDir);
  const { nodePath } = resolveLayout(vault, 'ai-workflows', 'abc-1');
  await fs.rm(nodePath);

  const r = await correr(vault, flowDir);
  assert.equal(r.status, 'ARCHIVED', 'reportó completo con el nodo faltante');
  await assert.doesNotReject(() => fs.stat(nodePath));
});

test('[AC-6] una caída antes de los índices o del commit también se reconstruye', async (t) => {
  const { vault, flowDir } = await escena(t);
  await correr(vault, flowDir);
  const { indexPaths } = resolveLayout(vault, 'ai-workflows', 'abc-1');

  await fs.rm(indexPaths[0]);
  assert.equal((await correr(vault, flowDir)).status, 'ARCHIVED', 'índice faltante');
  await assert.doesNotReject(() => fs.stat(indexPaths[0]));

  // Y sin commit que lo nombre, tampoco está archivado.
  await git(vault, 'update-ref', '-d', 'HEAD');
  assert.equal((await correr(vault, flowDir)).status, 'ARCHIVED', 'sin commit que lo nombre');
  const { stdout } = await git(vault, 'log', '--format=%s');
  assert.ok(stdout.includes('abc-1'));
});

test('[AC-6] las cuatro postcondiciones quedan satisfechas tras archivar', async (t) => {
  const { vault, flowDir } = await escena(t);
  await correr(vault, flowDir);
  const { frontier, nodePath, indexPaths } = resolveLayout(vault, 'ai-workflows', 'abc-1');
  for (const p of [frontier, nodePath, ...indexPaths]) await assert.doesNotReject(() => fs.stat(p), p);
  const { stdout } = await git(vault, 'log', '--format=%s');
  assert.ok(stdout.includes('abc-1'), 'no hay commit que nombre el flujo');
});
