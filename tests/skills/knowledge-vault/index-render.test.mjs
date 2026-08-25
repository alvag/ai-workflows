/**
 * Los índices, que son lo que vuelve consultable al vault.
 *
 * La regla que decide la forma: **el índice raíz tiene que dejar ubicar un flujo
 * sin abrir ningún documento.** De ahí que cada entrada lleve título, ruta y una
 * línea de resumen, y de ahí que la raíz **agregue transitivamente**: con "cada
 * índice lista sólo sus hijos", la raíz de este vault mostraría una única entrada
 * —`projects/`— y no serviría para nada.
 *
 * Y regenerar tiene que dar **los mismos bytes**: es lo que permite reconstruir
 * los índices después de cualquier corrida sin preguntarse si cambió algo. Eso
 * excluye timestamps, órdenes de lectura del filesystem y cualquier fuente de
 * afuera del vault — incluido invocar un modelo para redactar nada.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';

import { renderIndexes } from '../../../skills/knowledge-vault/scripts/lib/index-render.mjs';
import { buildNode } from '../../../skills/knowledge-vault/scripts/lib/node-builder.mjs';
import { resolveLayout } from '../../../skills/knowledge-vault/scripts/lib/vault-store.mjs';
import { createSandbox } from './helpers/sandbox.mjs';

function meta(flow, title, repo = 'ai-workflows') {
  return {
    type: 'sdd-flow', title, project: repo, flow,
    branch: `feature/${flow}`, date: '2026-03-04T12:00:00-03:00',
    provenance: `.plans/archived/${flow}`, state: 'done',
  };
}

/** Escribe un flujo completo en el vault: su nodo y su frontera con documentos. */
async function sembrar(vault, repo, flow, title, summary, docs = ['spec.md', 'plan.md']) {
  const { frontier, nodePath } = resolveLayout(vault, repo, flow);
  await fs.mkdir(frontier, { recursive: true });
  for (const d of docs) await fs.writeFile(path.join(frontier, d), `# ${d} de ${flow}\n`, 'utf8');
  await fs.writeFile(nodePath, buildNode({ metadata: meta(flow, title, repo), documents: docs, summary }), 'utf8');
}

async function vaultDeTres(t) {
  const caja = await createSandbox(t);
  const vault = path.join(caja.vaultsDir, 'dev-memory');
  await sembrar(vault, 'ai-workflows', 'ccc-3', 'Tercero', 'Resumen del tercero.');
  await sembrar(vault, 'ai-workflows', 'aaa-1', 'Primero', 'Resumen del primero.');
  await sembrar(vault, 'ai-workflows', 'bbb-2', 'Segundo', 'Resumen del segundo.');
  return vault;
}

test('[AC-7] la raíz lista los flujos con título, ruta y resumen', async (t) => {
  const vault = await vaultDeTres(t);
  const salida = await renderIndexes(vault);
  const raiz = salida.get(path.join(vault, 'index.md'));
  assert.ok(raiz, 'no se generó el índice raíz');
  for (const [flow, title, resumen] of [
    ['aaa-1', 'Primero', 'Resumen del primero.'],
    ['bbb-2', 'Segundo', 'Resumen del segundo.'],
    ['ccc-3', 'Tercero', 'Resumen del tercero.'],
  ]) {
    assert.ok(raiz.includes(`[${title}]`), title);
    assert.ok(raiz.includes(`sdd/${flow}.md`), flow);
    assert.ok(raiz.includes(resumen), resumen);
  }
});

test('[AC-7] regenerar da bytes idénticos', async (t) => {
  const vault = await vaultDeTres(t);
  const a = await renderIndexes(vault);
  const b = await renderIndexes(vault);
  assert.deepEqual([...a.keys()].sort(), [...b.keys()].sort());
  for (const [k, v] of a) assert.equal(b.get(k), v, k);
});

test('[AC-7] no escribe nada: devolver el contenido es todo lo que hace', async (t) => {
  const vault = await vaultDeTres(t);
  const antes = await fs.readdir(vault);
  await renderIndexes(vault);
  assert.deepEqual((await fs.readdir(vault)).sort(), antes.sort());
});

test('[AC-7] ningún index.md aparece como entrada de un índice', async (t) => {
  const vault = await vaultDeTres(t);
  // Se siembra un `index.md` **copiado** dentro de la frontera: es un documento
  // legítimo de un flujo de origen y no puede confundirse con uno generado.
  await sembrar(vault, 'ai-workflows', 'ddd-4', 'Cuarto', 'Con index copiado.', ['index.md', 'spec.md']);
  const salida = await renderIndexes(vault);
  for (const [ruta, contenido] of salida) {
    for (const linea of contenido.split('\n').filter((l) => l.startsWith('- ['))) {
      assert.ok(!/\bindex\.md\)/.test(linea), `${ruta} indexa un index.md: ${linea}`);
    }
  }
  assert.ok(salida.get(path.join(vault, 'index.md')).includes('sdd/ddd-4.md'), 'perdió el flujo');
});

test('[AC-7] los documentos copiados no son entradas del índice', async (t) => {
  const vault = await vaultDeTres(t);
  const raiz = await renderIndexes(vault).then((s) => s.get(path.join(vault, 'index.md')));
  const entradas = raiz.split('\n').filter((l) => l.startsWith('- ['));
  assert.equal(entradas.length, 3, 'entraron documentos además de los tres nodos');
  for (const l of entradas) assert.ok(!/\/(spec|plan)\.md\)/.test(l), l);
});

test('[AC-7] el índice de sdd lista su nivel y los superiores agregan transitivamente', async (t) => {
  const caja = await createSandbox(t);
  const vault = path.join(caja.vaultsDir, 'dev-memory');
  await sembrar(vault, 'ai-workflows', 'aaa-1', 'Uno', 'De ai-workflows.');
  await sembrar(vault, 'otro-repo', 'bbb-2', 'Dos', 'De otro-repo.');
  const salida = await renderIndexes(vault);

  const cuenta = (p) => (salida.get(p) ?? '').split('\n').filter((l) => l.startsWith('- [')).length;
  assert.equal(cuenta(path.join(vault, 'index.md')), 2, 'la raíz no agregó los dos proyectos');
  assert.equal(cuenta(path.join(vault, 'projects', 'index.md')), 2);
  assert.equal(cuenta(path.join(vault, 'projects', 'ai-workflows', 'index.md')), 1);
  assert.equal(cuenta(path.join(vault, 'projects', 'ai-workflows', 'sdd', 'index.md')), 1);
  assert.equal(cuenta(path.join(vault, 'projects', 'otro-repo', 'sdd', 'index.md')), 1);
});

test('[AC-7] el orden es estable y no el del filesystem', async (t) => {
  const vault = await vaultDeTres(t);
  const raiz = await renderIndexes(vault).then((s) => s.get(path.join(vault, 'index.md')));
  const ids = [...raiz.matchAll(/sdd\/([a-z0-9-]+)\.md/g)].map((m) => m[1]);
  assert.deepEqual(ids, [...ids].sort(), 'las entradas no están ordenadas por id de flujo');
});

test('[AC-7] un nodo sin resumen legible no se inventa: se reporta', async (t) => {
  const caja = await createSandbox(t);
  const vault = path.join(caja.vaultsDir, 'dev-memory');
  await sembrar(vault, 'ai-workflows', 'aaa-1', 'Uno', 'Con resumen.');
  const { nodePath } = resolveLayout(vault, 'ai-workflows', 'roto');
  await fs.writeFile(nodePath, 'sin frontmatter\n', 'utf8');
  await assert.rejects(() => renderIndexes(vault), /roto/);
});

test('[AC-11] el resumen del índice es el del frontmatter del nodo, carácter por carácter', async (t) => {
  const caja = await createSandbox(t);
  const vault = path.join(caja.vaultsDir, 'dev-memory');
  const resumen = 'Rescata el núcleo verificado y descarta la maquinaria de retiro.';
  await sembrar(vault, 'ai-workflows', 'aaa-1', 'Uno', resumen);

  const nodo = await fs.readFile(resolveLayout(vault, 'ai-workflows', 'aaa-1').nodePath, 'utf8');
  assert.ok(nodo.includes(`summary: ${resumen}`), 'el resumen no quedó en el frontmatter');
  const raiz = await renderIndexes(vault).then((s) => s.get(path.join(vault, 'index.md')));
  assert.ok(raiz.includes(resumen), 'el índice no derivó el resumen del nodo');
});
