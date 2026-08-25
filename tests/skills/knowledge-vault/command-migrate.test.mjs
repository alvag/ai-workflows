/**
 * `migrate`: un lote, y la razón por la que valida todo antes de escribir un byte.
 *
 * Migrar 49 de 50 deja un vault que **ningún criterio distingue** de uno
 * completo: no hay manifiesto que enumere lo que debía entrar, ni un conteo
 * esperado contra el que comparar. Quien lo consulte seis meses después va a leer
 * el índice y a concluir que el flujo que falta nunca existió.
 *
 * De ahí la forma: la entrada entera se valida primero —todo flujo tiene resumen,
 * todo resumen apunta a un flujo, ninguno vacío— y si algo falta **no migra
 * ninguno**. Un fallo total es recuperable con un comando; uno parcial y
 * silencioso, no.
 *
 * El otro dato que ordena el enumerado: la raíz de archivados real tiene 51
 * entradas y sólo 50 son directorios. Un `.md` suelto ahí no es un flujo.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fsp from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

import { DurableFs } from '../../../skills/knowledge-vault/scripts/lib/durable-fs.mjs';
import { migrateCommand } from '../../../skills/knowledge-vault/scripts/lib/commands/migrate.mjs';
import { indexCommand } from '../../../skills/knowledge-vault/scripts/lib/commands/index.mjs';
import { createSandbox } from './helpers/sandbox.mjs';

const ejecutar = promisify(execFile);

async function escena(t, flujos = ['aaa-1', 'bbb-2', 'ccc-3'], { sueltos = [] } = {}) {
  const caja = await createSandbox(t);
  const repoRoot = path.join(caja.reposDir, 'proyecto');
  const archivedRoot = path.join(repoRoot, '.plans', 'archived');
  const vault = path.join(caja.vaultsDir, 'dev-memory');
  await fsp.mkdir(vault, { recursive: true });
  for (const f of flujos) {
    await fsp.mkdir(path.join(archivedRoot, f), { recursive: true });
    await fsp.writeFile(path.join(archivedRoot, f, 'spec.md'), `# Flujo ${f}\n`, 'utf8');
    await fsp.writeFile(path.join(archivedRoot, f, 'notas.txt'), 'no viaja\n', 'utf8');
  }
  for (const s of sueltos) await fsp.writeFile(path.join(archivedRoot, s), 'suelto\n', 'utf8');
  await ejecutar('git', ['init', '-q', repoRoot]);
  return { caja, repoRoot, archivedRoot, vault };
}

async function tsv(e, filas) {
  const ruta = path.join(e.caja.scratchDir, 'resumenes.tsv');
  await fsp.writeFile(ruta, filas.map(([f, r]) => `${f}\t${r}`).join('\n') + '\n', 'utf8');
  return ruta;
}

const correr = (e, ruta, extra = {}) =>
  migrateCommand({
    fs: new DurableFs(),
    flags: { from: e.archivedRoot, summaries: ruta, 'vault-root': e.vault, ...extra },
    homeDir: '/home/nadie',
  });

const TODOS = [['aaa-1', 'Resumen del primero.'], ['bbb-2', 'Resumen del segundo.'], ['ccc-3', 'Resumen del tercero.']];

async function vaultVacio(vault) {
  const hay = [];
  const visitar = async (dir) => {
    for (const en of await fsp.readdir(dir, { withFileTypes: true })) {
      if (en.name === '.git') continue;
      const abs = path.join(dir, en.name);
      if (en.isDirectory()) await visitar(abs);
      else hay.push(abs);
    }
  };
  await visitar(vault).catch(() => {});
  return hay;
}

test('[AC-12] con todos los resúmenes, migra el lote entero y devuelve BATCH_OK', async (t) => {
  const e = await escena(t);
  const r = await correr(e, await tsv(e, TODOS));
  assert.equal(r.status, 'BATCH_OK');
  assert.equal(r.archivados, 3);
  for (const f of ['aaa-1', 'bbb-2', 'ccc-3']) {
    await assert.doesNotReject(
      () => fsp.stat(path.join(e.vault, 'projects', 'proyecto', 'sdd', `${f}.md`)), f);
  }
});

test('[AC-12] si a un flujo le falta su resumen, no migra ninguno', async (t) => {
  const e = await escena(t);
  const r = await correr(e, await tsv(e, TODOS.slice(0, 2)));
  assert.equal(r.status, 'BATCH_FAILED');
  assert.match(r.message, /ccc-3/);
  assert.deepEqual(await vaultVacio(e.vault), [], 'escribió pese a la entrada incompleta');
});

test('[AC-12] un resumen que no apunta a ningún flujo también frena el lote', async (t) => {
  const e = await escena(t);
  const r = await correr(e, await tsv(e, [...TODOS, ['no-existe', 'Un resumen huérfano.']]));
  assert.equal(r.status, 'BATCH_FAILED');
  assert.match(r.message, /no-existe/);
  assert.deepEqual(await vaultVacio(e.vault), []);
});

test('[AC-12] un resumen vacío o duplicado frena el lote', async (t) => {
  for (const [caso, filas] of [
    ['vacío', [['aaa-1', ''], ['bbb-2', 'x'], ['ccc-3', 'y']]],
    ['duplicado', [...TODOS, ['aaa-1', 'otra vez']]],
  ]) {
    const e = await escena(t);
    const r = await correr(e, await tsv(e, filas));
    assert.equal(r.status, 'BATCH_FAILED', caso);
    assert.deepEqual(await vaultVacio(e.vault), [], caso);
  }
});

test('[AC-12] un archivo suelto en la raíz de archivados no es un flujo', async (t) => {
  // Medido en el árbol real: 51 entradas, 50 directorios y un `.md` suelto.
  const e = await escena(t, ['aaa-1', 'bbb-2', 'ccc-3'], { sueltos: ['rama-contrato-dispatch-ready.md'] });
  const r = await correr(e, await tsv(e, TODOS));
  assert.equal(r.status, 'BATCH_OK', 'el suelto se contó como flujo sin resumen');
  assert.equal(r.archivados, 3);
});

test('[AC-12] --dry-run valida y no escribe', async (t) => {
  const e = await escena(t);
  const r = await correr(e, await tsv(e, TODOS), { 'dry-run': true });
  assert.equal(r.status, 'DRY_RUN');
  assert.deepEqual(await vaultVacio(e.vault), []);
});

test('[AC-12] si un flujo falla al archivar, el lote es PARCIAL y los demás quedan', async (t) => {
  const e = await escena(t);
  // Un nombre reservado hace fallar a ese flujo y sólo a ese.
  await fsp.mkdir(path.join(e.archivedRoot, 'index'), { recursive: true });
  await fsp.writeFile(path.join(e.archivedRoot, 'index', 'spec.md'), '# Reservado\n', 'utf8');
  const r = await correr(e, await tsv(e, [...TODOS, ['index', 'Un flujo con nombre reservado.']]));

  assert.equal(r.status, 'BATCH_PARTIAL');
  assert.equal(r.archivados, 3);
  assert.equal(r.fallidos.length, 1);
  assert.match(r.fallidos[0].flowId, /^index$/);
  for (const f of ['aaa-1', 'bbb-2', 'ccc-3']) {
    await assert.doesNotReject(
      () => fsp.stat(path.join(e.vault, 'projects', 'proyecto', 'sdd', `${f}.md`)), f);
  }
});

test('[AC-12] volver a migrar el mismo lote no duplica nada', async (t) => {
  const e = await escena(t);
  const ruta = await tsv(e, TODOS);
  await correr(e, ruta);
  const r = await correr(e, ruta);
  assert.equal(r.status, 'BATCH_OK');
  assert.equal(r.yaEstaban, 3);
});

test('[AC-7] index regenera los índices del vault y no toca nada más', async (t) => {
  const e = await escena(t);
  await correr(e, await tsv(e, TODOS));
  const raiz = path.join(e.vault, 'index.md');
  const antes = await fsp.readFile(raiz, 'utf8');
  await fsp.writeFile(raiz, '# Roto a mano\n', 'utf8');

  const r = await indexCommand({ fs: new DurableFs(), flags: { 'vault-root': e.vault }, homeDir: '/home/nadie' });
  assert.equal(r.status, 'INDEX_OK');
  assert.equal(await fsp.readFile(raiz, 'utf8'), antes, 'no regeneró el índice raíz');
  assert.deepEqual(r.reescritos, ['index.md']);
});

test('[AC-15] un vault dentro del repositorio frena el lote entero, antes de escribir', async (t) => {
  const e = await escena(t);
  const adentro = path.join(e.repoRoot, 'vault');
  await fsp.mkdir(adentro, { recursive: true });
  const ruta = await tsv(e, TODOS);
  await assert.rejects(
    () => migrateCommand({
      fs: new DurableFs(),
      flags: { from: e.archivedRoot, summaries: ruta, 'vault-root': adentro },
      homeDir: '/home/nadie',
    }),
    /disjunto/i,
  );
  assert.deepEqual(await fsp.readdir(adentro), [], 'escribió en el vault rechazado');
});
