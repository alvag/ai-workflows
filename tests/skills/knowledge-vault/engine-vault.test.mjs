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
import { resolvePublicationState, runVaultTransaction } from '../../../skills/knowledge-vault/scripts/lib/engine-vault.mjs';
import { exitCodeFor } from '../../../skills/knowledge-vault/scripts/lib/contracts.mjs';
import { estaASalvo } from '../../../skills/knowledge-vault/scripts/lib/safety-probe.mjs';
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
    'notas.tsv': 'esto no viaja\n',
    'cross-review/veredicto.md': 'esto tampoco\n',
    ...extra,
  };
  for (const [rel, contenido] of Object.entries(archivos)) {
    const target = path.join(dir, rel);
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, contenido, 'utf8');
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
 * Quién puede destruir bajo el origen.
 *
 * La garantía cambió de naturaleza con el verbo de retiro. Antes se sostenía por
 * **ausencia**: ningún módulo tenía una llamada capaz de borrar fuera del vault,
 * y el predicado exigía cero. Eso dejó de ser cierto —y de ser deseable: el
 * retiro existe justamente para borrar el origen—, así que la guarda **invierte
 * su criterio** y pasa de prohibir a **enumerar quién puede**.
 *
 * La frontera sigue siendo el **destino**, no la operación: `discardOrphanStagings`
 * borra dentro del vault y es legítimo, y una guarda que prohibiera todo borrado
 * volvería ilegal código correcto. `durable-fs.mjs` queda fuera del barrido a
 * propósito: es la capa primitiva, la que **implementa** `rm` y `rename` sobre la
 * ruta que le den, y el límite es de quien la llama.
 *
 * **La guarda estática no alcanza sola.** Reconoce nombres de variables en
 * llamadas directas, así que un alias o un helper intermedio la evaden sin
 * esfuerzo. Su complemento es la contención en runtime de `DurableFs`, que se
 * ejerce abajo con esos dos casos exactos y con su control en la otra dirección.
 */
const DESTRUCTIVAS = /\b(?:fs\.)?(rmTree|rmdir|unlink|rename|removeEmptyDir)\s*\(([^;]*?)\)/g;
const LLEVA_EL_ORIGEN = /\b(flowDir|sourcePath|origen|source|from)\b/;

/**
 * Los únicos módulos autorizados a destruir bajo el origen, por su ruta relativa
 * a `lib/`. Que la lista sea explícita es el punto: agregar un módulo que borre
 * el origen exige agregarlo acá, y eso es una decisión visible en el diff.
 */
const PUEDEN_DESTRUIR = new Set(['retire-execute.mjs']);

function destinosProhibidos(nombre, texto) {
  if (PUEDEN_DESTRUIR.has(nombre)) return [];
  const hallazgos = [];
  for (const m of texto.matchAll(DESTRUCTIVAS)) {
    const args = m[2];
    if (!LLEVA_EL_ORIGEN.test(args)) continue;
    hallazgos.push(`${nombre}: ${m[1]}(${args.trim()})`);
  }
  return hallazgos;
}

test('[AC-14] el predicado sabe ponerse rojo, y sabe no ponerse', () => {
  // Control positivo. Sin esto, un verde no distingue "no hay violaciones" de
  // "el predicado no ve nada", que es la forma en que una guarda miente.
  assert.deepEqual(
    destinosProhibidos('sintetico.mjs', 'await fs.rmTree(flowDir, label);'),
    ['sintetico.mjs: rmTree(flowDir, label)'],
  );
  assert.deepEqual(destinosProhibidos('sintetico.mjs', 'await fs.rmTree(staging, label);'), []);
});

test('[AC-14] la enumeración mira quién llama, no qué se llama', () => {
  // El simétrico del control anterior, y lo que hace que "invertir el criterio"
  // signifique algo: el **mismo** texto es legal en el módulo de retiro e ilegal
  // en cualquier otro. Sin este par, un predicado que ignorara el módulo pasaría.
  const texto = 'await fs.rmTree(flowDir, label);';
  assert.deepEqual(destinosProhibidos('retire-execute.mjs', texto), []);
  assert.deepEqual(
    destinosProhibidos('engine-vault.mjs', texto),
    ['engine-vault.mjs: rmTree(flowDir, label)'],
  );
});

test('[AC-14] sólo el módulo de retiro destruye bajo el origen', async () => {
  const lib = path.resolve('skills/knowledge-vault/scripts/lib');
  const hallazgos = [];
  const barridos = [];
  const visitar = async (dir) => {
    for (const e of await fs.readdir(dir, { withFileTypes: true })) {
      const abs = path.join(dir, e.name);
      if (e.isDirectory()) { await visitar(abs); continue; }
      if (!e.name.endsWith('.mjs') || e.name === 'durable-fs.mjs') continue;
      barridos.push(abs);
      hallazgos.push(...destinosProhibidos(path.relative(lib, abs), await fs.readFile(abs, 'utf8')));
    }
  };
  await visitar(lib);
  // Un barrido que no ve un solo archivo también da la lista vacía, y ese verde
  // no dice nada. El piso es lo que separa "no hay violaciones" de "no hay nada".
  assert.ok(barridos.length >= 15, `el barrido vio ${barridos.length} módulos`);
  assert.deepEqual(hallazgos, [], 'hay destrucción con destino bajo el origen fuera del módulo de retiro');
});

/** Un árbol con una raíz declarada y un vecino que queda fuera de ella. */
async function contencion(t) {
  const caja = await createSandbox(t);
  const raiz = await caja.makeTree(path.join(caja.reposDir, 'declarada'), { 'adentro.md': 'vive\n' });
  const afuera = await caja.makeTree(path.join(caja.reposDir, 'ajena'), { 'afuera.md': 'no se toca\n' });
  return { durable: new DurableFs({ destructiveRoots: [raiz] }), raiz, afuera };
}

test('[AC-14] la contención en runtime caza el alias que la guarda estática no ve', async (t) => {
  const { durable, afuera } = await contencion(t);
  // Exactamente la evasión que el barrido de texto no puede ver: la llamada ya
  // no menciona ninguna de las variables que el predicado reconoce.
  const borrar = durable.rmTree.bind(durable);

  await assert.rejects(() => borrar(afuera, 'retire.rmTree'), (error) => {
    assert.equal(error.code, 'OUT_OF_BOUNDS');
    return true;
  });
  assert.equal(await fs.readFile(path.join(afuera, 'afuera.md'), 'utf8'), 'no se toca\n');
});

test('[AC-14] la contención en runtime caza el helper intermedio', async (t) => {
  const { durable, afuera } = await contencion(t);
  // La segunda evasión: la ruta llega por parámetro, así que en el sitio de la
  // llamada no hay ningún nombre que delate de dónde salió.
  const limpiar = (io, ruta) => io.unlink(ruta, 'retire.unlink');
  const victima = path.join(afuera, 'afuera.md');

  await assert.rejects(() => limpiar(durable, victima), (error) => {
    assert.equal(error.code, 'OUT_OF_BOUNDS');
    return true;
  });
  assert.equal(await fs.readFile(victima, 'utf8'), 'no se toca\n');
});

test('[AC-14] la contención deja pasar lo que sí está bajo la raíz declarada', async (t) => {
  // El control en la otra dirección. Sin él, una contención que lanzara siempre
  // pasaría los dos casos de arriba sin contener nada — sólo prohibiría todo.
  const { durable, raiz } = await contencion(t);
  await durable.unlink(path.join(raiz, 'adentro.md'), 'retire.unlink');
  await assert.rejects(() => fs.readFile(path.join(raiz, 'adentro.md'), 'utf8'));
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

  // Y sin commit que lo nombre, tampoco está archivado. Se retrocede HEAD al
  // commit raíz en vez de borrarlo: una caída antes del commit **no borra la
  // historia previa del vault**, y `update-ref -d HEAD` la modelaba sólo mientras
  // un vault nuevo no tuviera ninguna. Desde que nace con su `.gitignore`
  // commiteado, amputar la historia entera lo deja sin trackear y el archivado
  // frena por un cambio ajeno que ninguna caída real produciría.
  //
  // **`--soft`:** el índice queda intacto, así que cada archivo publicado se
  // lista con su ruta completa. Es el caso simple, y el que este test ejerce.
  // El caso duro —índice desstageado, con git colapsando el árbol a su
  // ancestro— vive en su propio test, abajo.
  const { stdout: raiz } = await git(vault, 'rev-list', '--max-parents=0', 'HEAD');
  await git(vault, 'reset', '--soft', '-q', raiz.trim());
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

test('el reintento reconstruye con el árbol colapsado a su ancestro', async (t) => {
  // El caso duro del anterior: con el índice desstageado, `git status` colapsa
  // el árbol publicado a un `?? projects/`, que es **ancestro** de la frontera y
  // no descendiente. Un predicado que solo mire "por debajo de" lee ahí el
  // residuo de la propia corrida como trabajo ajeno y bloquea todo reintento.
  const { vault, flowDir } = await escena(t);
  await correr(vault, flowDir);
  const { stdout: raiz } = await git(vault, 'rev-list', '--max-parents=0', 'HEAD');
  await git(vault, 'reset', '--mixed', '-q', raiz.trim());
  assert.equal((await correr(vault, flowDir)).status, 'ARCHIVED', 'sin commit que lo nombre');
});

// Lo que puede fallar se valida **antes** de publicar. El título sale del
// encabezado del documento, así que quien archiva no lo elige; componiendo el
// nodo después de copiar, un valor irrepresentable fallaba con la frontera ya
// puesta, sin nodo ni índice, y el reintento veía un vault sucio que nadie tocó.
const ILEGIBLE = 'resumen con\ttabulador';

test('archiva un flujo con numeral en el encabezado sin tocar el origen', async (t) => {
  const encabezado = '# Ronda de feedback del PR #1264';
  const { vault, flowDir } = await escena(t, { 'spec.md': `${encabezado}\n\ncriterios\n` });
  const antes = await snapshotTree(flowDir);

  assert.equal((await correr(vault, flowDir)).status, 'ARCHIVED');
  assert.deepEqual(await snapshotTree(flowDir), antes, 'el archivado editó el origen');
  const nodo = await fs.readFile(resolveLayout(vault, 'ai-workflows', 'abc-1').nodePath, 'utf8');
  assert.ok(nodo.includes('#1264'), 'el nodo perdió el numeral del título');
});

test('un nodo irrepresentable no deja nada bajo la frontera', async (t) => {
  const { vault, flowDir } = await escena(t);
  await assert.rejects(() => correr(vault, flowDir, 'abc-1', { summary: ILEGIBLE }), /control/i);
  const { frontier } = resolveLayout(vault, 'ai-workflows', 'abc-1');
  await assert.rejects(() => fs.stat(frontier), 'quedó frontera publicada tras el fallo');
});

test('con frontera preexistente el residuo queda intacto', async (t) => {
  // La corrida que no puede completar tampoco destruye lo que encontró.
  const { vault, flowDir } = await escena(t);
  await correr(vault, flowDir);
  const { frontier } = resolveLayout(vault, 'ai-workflows', 'abc-1');
  const antes = await snapshotTree(frontier);

  await assert.rejects(() => correr(vault, flowDir, 'abc-1', { summary: ILEGIBLE }), /control/i);
  assert.deepEqual(await snapshotTree(frontier), antes, 'el fallo se llevó puesto el residuo');
});

test('[KV-SEL AC-9] primera publicación rechaza reservado, no portable e ignorado', async (t) => {
  const cases = [
    ['evidencia/sdd/note.md', 'RESERVED_DOCUMENT_PATH'],
    ['evidencia/aux.md', 'NON_PORTABLE_DOCUMENT_PATH'],
    ['evidencia/ignored.md', 'IGNORED_DOCUMENT_PATH'],
  ];
  for (const [relative, code] of cases) {
    const { vault, flowDir } = await escena(t, { [relative]: 'x\n' });
    if (code === 'IGNORED_DOCUMENT_PATH') {
      await git(vault, 'init', '-q');
      await fs.writeFile(
        path.join(vault, '.gitignore'),
        `.obsidian/\n.DS_Store\nprojects/ai-workflows/sdd/abc-1/${relative}\n`,
        'utf8',
      );
      await git(vault, 'add', '.gitignore');
      await git(vault, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'ignore');
    }
    const sourceBefore = await snapshotTree(flowDir);
    await assert.rejects(() => correr(vault, flowDir), (error) => {
      assert.equal(error.code, code, relative);
      assert.equal(error.path, relative, relative);
      assert.equal(exitCodeFor(error.code), 4);
      return true;
    });
    await assert.rejects(() => fs.stat(resolveLayout(vault, 'ai-workflows', 'abc-1').frontier));
    assert.deepEqual(await snapshotTree(flowDir), sourceBefore);
  }
});

test('[KV-SEL AC-9] historia incompatible gana antes que las guardas nuevas', async (t) => {
  const { vault, flowDir } = await escena(t);
  await correr(vault, flowDir);
  await fs.mkdir(path.join(flowDir, 'evidencia', 'sdd'), { recursive: true });
  await fs.writeFile(path.join(flowDir, 'evidencia', 'sdd', 'aux.md'), 'nuevo\n', 'utf8');
  const vaultBefore = await snapshotTree(vault);

  await assert.rejects(() => correr(vault, flowDir), (error) => {
    assert.equal(error.code, 'VERIFY_FAILED');
    assert.deepEqual(error.detail.missing, ['evidencia/sdd/aux.md']);
    return true;
  });
  assert.deepEqual(await snapshotTree(vault), vaultBefore);
});

test('[KV-SEL AC-19] histórico incompatible falla con detalle sin crecer', async (t) => {
  const { vault, flowDir } = await escena(t);
  await correr(vault, flowDir);
  await fs.mkdir(path.join(flowDir, 'runs'), { recursive: true });
  await fs.writeFile(path.join(flowDir, 'runs', 'new.ts'), 'export {};\n', 'utf8');
  const before = await snapshotTree(vault);

  await assert.rejects(() => correr(vault, flowDir), (error) => {
    assert.equal(error.code, 'VERIFY_FAILED');
    assert.deepEqual(error.detail, { missing: ['runs/new.ts'], extra: [], mismatched: [] });
    return true;
  });
  assert.deepEqual(await snapshotTree(vault), before);
});

test('[KV-SEL AC-19] autoridad del nodo informa missing y extra sin mismatched', async (t) => {
  const { vault, flowDir } = await escena(t);
  await correr(vault, flowDir);
  const { frontier, nodePath } = resolveLayout(vault, 'ai-workflows', 'abc-1');
  await fs.rm(frontier, { recursive: true });
  await fs.rm(path.join(flowDir, 'spec.md'));
  await fs.mkdir(path.join(flowDir, 'runs'), { recursive: true });
  await fs.writeFile(path.join(flowDir, 'runs', 'new.ts'), 'export {};\n', 'utf8');

  await assert.rejects(
    () => resolvePublicationState({
      fs: new DurableFs(),
      frontier,
      nodePath,
      currentEntries: [
        { path: 'plan.md', type: 'file', size: 0, sha256: '' },
        { path: 'runs/new.ts', type: 'file', size: 0, sha256: '' },
      ],
      flowId: 'abc-1',
      label: 'test',
    }),
    (error) => {
      assert.equal(error.code, 'VERIFY_FAILED');
      assert.deepEqual(error.detail, {
        missing: ['runs/new.ts'],
        extra: ['spec.md'],
        mismatched: [],
      });
      return true;
    },
  );
});

test('[KV-SEL AC-20] nodo histórico vacío precede frontera y no cambia con otro summary', async (t) => {
  const { vault, flowDir } = await escena(t);
  await fs.rm(path.join(flowDir, 'spec.md'));
  await fs.rm(path.join(flowDir, 'plan.md'));
  assert.equal((await correr(vault, flowDir)).status, 'ARCHIVED');

  const { frontier, nodePath } = resolveLayout(vault, 'ai-workflows', 'abc-1');
  const nodeBefore = await fs.readFile(nodePath, 'utf8');
  const { stdout: headBefore } = await git(vault, 'rev-parse', 'HEAD');
  await fs.rm(frontier, { recursive: true });

  const result = await correr(vault, flowDir, 'abc-1', { summary: 'Otro resumen que no debe reemplazar el nodo.' });
  assert.equal(result.status, 'ALREADY_ARCHIVED');
  assert.equal(await fs.readFile(nodePath, 'utf8'), nodeBefore);
  assert.equal((await git(vault, 'rev-parse', 'HEAD')).stdout, headBefore);
});

test('[KV-SEL AC-20] reconstruye frontera no vacía desde el nodo sin reescribirlo', async (t) => {
  const { vault, flowDir } = await escena(t, { 'runs/job.ts': 'export {};\n' });
  await correr(vault, flowDir);
  const { frontier, nodePath } = resolveLayout(vault, 'ai-workflows', 'abc-1');
  const nodeBefore = await fs.readFile(nodePath, 'utf8');
  await fs.rm(frontier, { recursive: true });

  assert.equal((await correr(vault, flowDir, 'abc-1', { summary: 'No reemplazar.' })).status, 'ARCHIVED');
  assert.equal(await fs.readFile(nodePath, 'utf8'), nodeBefore);
  assert.equal(await fs.readFile(path.join(frontier, 'runs', 'job.ts'), 'utf8'), 'export {};\n');
});

test('[KV-SEL AC-20] frontera publicada recupera nodo e índices faltantes', async (t) => {
  const { vault, flowDir } = await escena(t);
  await correr(vault, flowDir);
  const { nodePath, indexPaths } = resolveLayout(vault, 'ai-workflows', 'abc-1');
  await fs.rm(nodePath);
  for (const indexPath of indexPaths) await fs.rm(indexPath);

  assert.equal((await correr(vault, flowDir)).status, 'ARCHIVED');
  for (const target of [nodePath, ...indexPaths]) await assert.doesNotReject(() => fs.stat(target));
});

test('[KV-SEL AC-20] archive rechaza nodo histórico ilegible sin escribir', async (t) => {
  const { vault, flowDir } = await escena(t);
  await correr(vault, flowDir);
  const { frontier, nodePath } = resolveLayout(vault, 'ai-workflows', 'abc-1');
  await fs.rm(frontier, { recursive: true });
  await fs.writeFile(nodePath, 'sin frontmatter\n', 'utf8');
  const before = await snapshotTree(vault);

  await assert.rejects(() => correr(vault, flowDir), (error) => {
    assert.equal(error.code, 'NODE_UNREADABLE');
    assert.equal(error.path, nodePath);
    assert.equal(exitCodeFor(error.code), 9);
    return true;
  });
  assert.deepEqual(await snapshotTree(vault), before);
});


test('un documento de runs ya trackeado no rompe el rearchivo ni la sonda al aparecer un ignore', async (t) => {
  const { vault, flowDir } = await escena(t, { 'runs/r1.jsonl': '{"run":1}\n' });
  assert.equal((await correr(vault, flowDir)).status, 'ARCHIVED');
  await fs.appendFile(path.join(vault, '.gitignore'), 'runs/\n', 'utf8');
  await git(vault, 'add', '--', '.gitignore');
  await git(vault, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'ignore runs');
  const before = (await git(vault, 'rev-parse', 'HEAD')).stdout.trim();

  assert.equal((await correr(vault, flowDir)).status, 'ALREADY_ARCHIVED');
  assert.equal((await git(vault, 'rev-parse', 'HEAD')).stdout.trim(), before);
  assert.deepEqual(await estaASalvo({
    fs: new DurableFs(), vaultRoot: vault, repoId: 'ai-workflows', flowId: 'abc-1', flowDir,
  }), { aSalvo: true, causa: null, faltantes: [] });

  const { nodePath } = resolveLayout(vault, 'ai-workflows', 'abc-1');
  await fs.rm(nodePath);
  assert.equal((await correr(vault, flowDir)).status, 'ARCHIVED');
  assert.deepEqual(await estaASalvo({
    fs: new DurableFs(), vaultRoot: vault, repoId: 'ai-workflows', flowId: 'abc-1', flowDir,
  }), { aSalvo: true, causa: null, faltantes: [] });
});
