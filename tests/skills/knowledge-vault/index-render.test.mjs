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
import { pathToFileURL } from 'node:url';

import { IndexRenderError, renderIndexes } from '../../../skills/knowledge-vault/scripts/lib/index-render.mjs';
import { buildNode } from '../../../skills/knowledge-vault/scripts/lib/node-builder.mjs';
import { exitCodeFor } from '../../../skills/knowledge-vault/scripts/lib/contracts.mjs';
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

test('[KV-SEL AC-10] indexador normaliza separadores nativos antes de codificar', async (t) => {
  const caja = await createSandbox(t);
  const vault = path.join(caja.vaultsDir, 'dev-memory');
  await sembrar(vault, 'repo con espacio', 'flow one', 'Uno', 'Con espacios.');

  const rootIndex = (await renderIndexes(vault)).get(path.join(vault, 'index.md'));
  assert.ok(rootIndex.includes('(projects/repo%20con%20espacio/sdd/flow%20one.md)'));
  assert.ok(!rootIndex.includes('%2F'));
});

test('[KV-SEL AC-20] IndexRenderError conserva NODE_UNREADABLE y path del nodo', async (t) => {
  const caja = await createSandbox(t);
  const vault = path.join(caja.vaultsDir, 'dev-memory');
  const { nodePath } = resolveLayout(vault, 'ai-workflows', 'roto');
  await fs.mkdir(path.dirname(nodePath), { recursive: true });
  await fs.writeFile(nodePath, '---\ntitle: Roto\nflow: roto\n---\n', 'utf8');

  await assert.rejects(() => renderIndexes(vault), (error) => {
    assert.ok(error instanceof IndexRenderError);
    assert.equal(error.code, 'NODE_UNREADABLE');
    assert.equal(error.path, nodePath);
    assert.equal(exitCodeFor(error.code), 9);
    return true;
  });
});


test('regenerar índices acepta el flow histórico distinto del basename del nodo', async (t) => {
  const caja = await createSandbox(t);
  const vault = path.join(caja.vaultsDir, 'dev-memory');
  await sembrar(vault, 'ai-workflows', 'nombre-viejo', 'Título histórico', 'Resumen histórico.');
  const nodePath = resolveLayout(vault, 'ai-workflows', 'nombre-viejo').nodePath;
  const old = await fs.readFile(nodePath, 'utf8');
  await fs.writeFile(nodePath, old.replace('flow: nombre-viejo', 'flow: id-histórico'), 'utf8');

  const root = (await renderIndexes(vault)).get(path.join(vault, 'index.md'));
  assert.ok(root.includes('sdd/nombre-viejo.md'));
  assert.ok(root.includes('Resumen histórico.'));
});


/** Misma ruta según la plataforma, no igualdad de string: en Windows `path.resolve` conserva la caja. */
const mismaRuta = (a, b) => path.relative(a, b) === '';

test('grafias equivalentes dan el mismo resultado, y la guarda de contencion acredita por reversion', async (t) => {
  const vault = await vaultDeTres(t);
  const control = await renderIndexes(vault);
  const posix = vault.split(path.sep).join('/');

  // Las seis familias que AC-2 exige como mínimo, todas derivadas de la MISMA raíz sembrada. Las
  // cuatro últimas rompen la igualdad en las dos plataformas, así que el caso no queda verde por
  // vacuidad en POSIX, donde la grafía del config *es* la nativa.
  const grafias = [
    ['nativa (control)', vault],
    ['separadores POSIX (la del config)', posix],
    ['separador final', `${posix}/`],
    ['segmento punto', posix.replace(/\/([^/]+)$/, '/./$1')],
    ['separadores repetidos', posix.replace(/\//g, '//')],
    ['unidad y segmentos en otra caja', posix.charAt(0).toLowerCase() + posix.slice(1).toLowerCase()],
  ];

  let ejercidas = 0;
  for (const [nombre, raiz] of grafias) {
    if (!mismaRuta(vault, raiz)) {
      t.diagnostic(`salteada ${nombre}: esta plataforma no la resuelve a la misma ruta que la nativa`);
      continue;
    }
    ejercidas += 1;
    const salida = await renderIndexes(raiz);
    assert.equal(salida.size, control.size, `${nombre}: distinta cantidad de índices`);
    for (const [clave, contenido] of salida) {
      const par = [...control.keys()].find((k) => mismaRuta(k, clave));
      assert.ok(par, `${nombre}: ${clave} no tiene equivalente en la corrida nativa`);
      assert.equal(contenido, control.get(par), `${nombre}: el contenido de ${clave} difiere`);
    }
    // AC-3, sobre las claves ORIGINALES: normalizar antes de contar pisa la duplicada y hace
    // desaparecer justo lo que este criterio manda detectar.
    const raices = [...salida.keys()].filter((k) => mismaRuta(k, path.join(vault, 'index.md')));
    assert.equal(raices.length, 1, `${nombre}: ${raices.length} claves para el índice raíz`);
    const indiceRaiz = salida.get(raices[0]);
    for (const titulo of ['Primero', 'Segundo', 'Tercero']) {
      assert.ok(indiceRaiz.includes(titulo), `${nombre}: el índice raíz no lista ${titulo}`);
    }
  }
  assert.ok(ejercidas >= 2, 'ninguna grafía no nativa quedó ejercida en esta plataforma');

  // La reversión solo se puede observar donde la grafía del config rompe la igualdad con la
  // nativa. En POSIX `path.join(posix, '.') === posix`, así que revertir el sitio no emite
  // ninguna ruta externa y no habría nada que acreditar: se saltea declarando por qué, igual que
  // el bucle de grafías.
  if (path.join(posix, '.') === posix) {
    t.diagnostic('salteada la acreditación por reversión: en esta plataforma la grafía del config ya es la nativa');
    return;
  }

  // El sitio revertido es `ancestros(raiz, …)`, el único de los cuatro cuya reversión hace que
  // esta escena emita una ruta externa. Revertir la definición de la raíz canónica desarmaría
  // también la guarda, y el caso dejaría de probar lo que dice.
  const original = new URL('../../../skills/knowledge-vault/scripts/lib/index-render.mjs', import.meta.url);
  const fuente = await fs.readFile(original, 'utf8');
  const revertido = fuente.replace('ancestros(raiz, n.dir)', 'ancestros(vaultRoot, n.dir)');
  assert.notEqual(revertido, fuente, 'la mutación de reversión no encontró su sitio');
  // La copia vive en el sandbox, que se borra solo. Escribirla junto al original dejaría un .mjs
  // untracked en el árbol de producto si el proceso muere entre el write y el borrado, y sus
  // imports relativos por eso se reescriben a la carpeta del módulo real.
  const mutado = path.join(path.resolve(vault, '..', '..'), 'scratch', 'index-render.reversion.mjs');
  await fs.writeFile(mutado, revertido.replaceAll("from './", `from '${new URL('./', original).href}`), 'utf8');
  const { renderIndexes: renderRevertido } = await import(pathToFileURL(mutado).href);
  await assert.rejects(() => renderRevertido(posix), (error) => {
    // Por el identificador y la ruta ofensora, no por el código 9, que `NODE_UNREADABLE` comparte.
    assert.equal(error.name, 'IndexRenderError');
    assert.equal(error.code, 'INDEX_OUTSIDE_VAULT');
    assert.equal(exitCodeFor(error.code), 9);
    assert.ok(error.path && path.relative(vault, error.path).startsWith('..'),
      `la ruta ofensora ${error.path} no está fuera del vault`);
    return true;
  });
});
