/**
 * El verbo `retire` y su modo ensayo (AC-4, AC-5, AC-5b).
 *
 * Las tres propiedades que se prueban acá son las que separan este verbo de una
 * implementación floja que satisface la letra de todo lo demás:
 *
 * · el **ensayo no escribe** y sale cero **siempre**, incluso al encontrar lo que
 *   viene a buscar;
 * · el **digest se exige**, no se recalcula: un verbo que computa su propio
 *   digest al ejecutar se está aprobando solo;
 * · hay **dos alcances** de digest, y confundirlos rompe en las dos direcciones —
 *   abortar el lote entero por un archivo ajeno, o no ver un cambio de alcance.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

import { DurableFs, Recorder } from '../../../skills/knowledge-vault/scripts/lib/durable-fs.mjs';
import { runVaultTransaction } from '../../../skills/knowledge-vault/scripts/lib/engine-vault.mjs';
import { retireCommand, ESTADOS } from '../../../skills/knowledge-vault/scripts/lib/commands/retire.mjs';
import { runCli } from '../../../skills/knowledge-vault/scripts/lib/cli.mjs';
import { serializarRegistroIdentidades } from '../../../skills/knowledge-vault/scripts/lib/identity.mjs';
import { writeIdentitiesFile } from '../../../skills/knowledge-vault/scripts/lib/vault-store.mjs';
import { createSandbox } from './helpers/sandbox.mjs';
import { snapshotTree } from './helpers/tree-snapshot.mjs';

const git = (cwd, ...args) => promisify(execFile)('git', ['-C', cwd, ...args]);
const REPO_ID = 'api-pagos';

const PLAN = [
  '---', 'id: abc-1', 'branch: feature/abc-1', 'status: done',
  'created_at: 2026-03-04T12:00:00-03:00', '---', '', '# Plan', '',
].join('\n');

/**
 * Un repositorio con archivados, su vault con dos flujos archivados y la
 * identidad ya declarada. Es el estado desde el que un retiro sería legítimo.
 */
async function escena(t, { archivados = ['abc-1', 'abc-2'], sueltos = [] } = {}) {
  const caja = await createSandbox(t);
  const repoRoot = await caja.makeRepo('proyecto');
  await git(repoRoot, 'init', '-q');
  await git(repoRoot, 'remote', 'add', 'origin', 'git@github.com:acme/api.git');
  const raiz = path.join(repoRoot, '.plans', 'archived');
  await fs.mkdir(raiz, { recursive: true });
  const vault = await caja.makeVault('dev-memory');

  const flujos = [];
  for (const flowId of archivados) {
    const dir = await caja.makeTree(path.join(raiz, flowId), {
      'spec.md': `# ${flowId}\n\ncriterios\n`,
      'plan.md': PLAN,
      'notas.txt': 'no viaja\n',
    });
    await runVaultTransaction({
      fs: new DurableFs(), vaultRoot: vault, repoSlug: REPO_ID, flowId, flowDir: dir,
      summary: `resumen de ${flowId}`,
    });
    flujos.push(dir);
  }
  for (const nombre of sueltos) await fs.writeFile(path.join(raiz, nombre), 'suelto\n', 'utf8');

  // La identidad **declarada**: sin ella el verbo se detiene, que es el punto.
  const { stdout } = await git(repoRoot, 'rev-list', '--max-parents=0', 'HEAD').catch(() => ({ stdout: '' }));
  await writeIdentitiesFile({
    fs: new DurableFs(),
    vaultRoot: vault,
    texto: serializarRegistroIdentidades([{
      repoId: REPO_ID,
      remoto: 'git@github.com:acme/api.git',
      commitRaiz: stdout.trim().split('\n')[0] ?? '',
      rutaObservada: repoRoot,
    }]),
  });
  return { caja, repoRoot, raiz, vault, flujos };
}

const correr = (e, flags, extra = {}) =>
  retireCommand({
    fs: extra.fs ?? new DurableFs(),
    flags: { root: e.raiz, 'vault-root': e.vault, ...flags },
    ...extra,
  });

// ── AC-4 · el ensayo no escribe y emite el digest ────────────────────────────

test('[AC-4] el ensayo no escribe: ni el registro de operaciones ni las dos raíces se mueven', async (t) => {
  const e = await escena(t);
  const antesVault = await snapshotTree(e.vault);
  const antesRaiz = await snapshotTree(e.raiz);
  const grabador = new Recorder();

  const r = await correr(e, { 'dry-run': true }, { fs: new DurableFs({ recorder: grabador }) });

  assert.equal(r.status, ESTADOS.DRY_RUN);
  const MUTAN = new Set(['mkdir', 'openExclusive', 'copyFile', 'writeFile', 'writeFileAtomic',
    'rename', 'unlink', 'rmTree', 'removeEmptyDir', 'fsyncFile', 'fsyncDir']);
  // `entries` y no `ops()`: esta última devuelve strings `op:label`.
  assert.deepEqual(grabador.entries.filter((o) => MUTAN.has(o.op)).map((o) => `${o.op}:${o.label}`), []);
  assert.ok(grabador.entries.length >= 10, `el registro vio ${grabador.entries.length} operaciones`);
  assert.deepEqual(await snapshotTree(e.vault), antesVault);
  assert.deepEqual(await snapshotTree(e.raiz), antesRaiz);
});

test('[AC-4] el ensayo clasifica cada flujo y emite el digest del lote', async (t) => {
  const e = await escena(t);
  const { informe } = await correr(e, { 'dry-run': true });

  assert.match(informe.digest, /^[0-9a-f]{64}$/);
  assert.deepEqual(informe.flujos.map((f) => f.flowId), ['abc-1', 'abc-2']);
  for (const f of informe.flujos) {
    assert.equal(f.aSalvo, true, `${f.flowId} no quedó a salvo: ${f.causa}`);
    assert.match(f.digest, /^[0-9a-f]{64}$/);
    // Los bytes por clase: es lo que separa "dos flujos" de "cuánto se pierde".
    assert.equal(f.bytes.total, f.bytes.aSalvo + f.bytes.sinCopia);
    assert.ok(f.bytes.sinCopia > 0, 'el andamiaje no aparece como sin copia');
  }
  assert.equal(informe.repoId, REPO_ID);
});

test('[AC-4] el ensayo sale cero aunque encuentre discrepancias', async (t) => {
  const e = await escena(t);
  // Un flujo que nunca se archivó, y otro cuya frontera se alteró: las dos
  // discrepancias que el ensayo existe para mostrar.
  await e.caja.makeTree(path.join(e.raiz, 'sin-copia'), { 'spec.md': '# nadie me archivó\n' });
  await fs.writeFile(
    path.join(e.vault, 'projects', REPO_ID, 'sdd', 'abc-1', 'spec.md'), '# manoseado\n', 'utf8',
  );

  const r = await correr(e, { 'dry-run': true });

  assert.equal(r.status, ESTADOS.DRY_RUN, 'el ensayo cambió de estado por lo que encontró');
  const porId = Object.fromEntries(r.informe.flujos.map((f) => [f.flowId, f]));
  assert.equal(porId['sin-copia'].aSalvo, false);
  assert.equal(porId['sin-copia'].causa, 'FRONTIER_MISSING');
  assert.equal(porId['abc-1'].aSalvo, false);
  assert.equal(porId['abc-1'].causa, 'VERIFY_FAILED');
  assert.equal(porId['abc-2'].aSalvo, true);
});

test('[AC-4] el ensayo nombra los remanentes que no procesa', async (t) => {
  const e = await escena(t, { sueltos: ['README.md'] });
  const { informe } = await correr(e, { 'dry-run': true });

  assert.deepEqual(informe.remanentesNoProcesados.map((p) => path.basename(p)), ['README.md']);
  assert.deepEqual(informe.flujos.map((f) => f.flowId), ['abc-1', 'abc-2']);
});

// ── AC-5 · el digest aprobado se exige y se compara ──────────────────────────

test('[AC-5] sin --approve-digest el retiro real no arranca', async (t) => {
  const e = await escena(t);
  await assert.rejects(() => correr(e, {}), (error) => {
    assert.equal(error.code, 'USAGE');
    assert.match(error.message, /approve-digest/);
    return true;
  });
});

test('[AC-5] un digest que no describe este lote lo detiene antes de tocar nada', async (t) => {
  const e = await escena(t);
  const antes = await snapshotTree(e.raiz);
  let ejecutado = 0;

  await assert.rejects(
    () => correr(e, { 'approve-digest': 'f'.repeat(64) }, { ejecutor: async () => { ejecutado += 1; } }),
    (error) => {
      assert.equal(error.code, 'PRECONDITION_NOT_MET');
      assert.match(error.message, /no describe este lote/);
      return true;
    },
  );
  assert.equal(ejecutado, 0, 'se ejecutó algo con el digest equivocado');
  assert.deepEqual(await snapshotTree(e.raiz), antes);
});

test('[AC-5] el digest del ensayo es el que el retiro real acepta', async (t) => {
  const e = await escena(t);
  const { informe } = await correr(e, { 'dry-run': true });
  const vistos = [];

  const r = await correr(e, { 'approve-digest': informe.digest }, {
    ejecutor: async ({ flujo }) => { vistos.push(flujo.flowId); return { flowId: flujo.flowId, estado: 'RETIRADO' }; },
  });
  assert.equal(r.status, ESTADOS.BATCH_OK);
  assert.deepEqual(vistos, ['abc-1', 'abc-2']);
});

test('[AC-5] con el digest del ensayo, el retiro real libera el origen de verdad', async (t) => {
  const e = await escena(t);
  const { informe } = await correr(e, { 'dry-run': true });
  const antesDelVault = await snapshotTree(e.vault);

  // Sin ejecutor inyectado: el del verbo, el que destruye. Es el único test de
  // este archivo que mide el problema en vez de sus partes.
  const r = await correr(e, { 'approve-digest': informe.digest });

  assert.equal(r.status, ESTADOS.BATCH_OK);
  assert.deepEqual(await fs.readdir(e.raiz), [], 'quedó algo en la raíz de archivados');
  // Y lo que estaba a salvo sigue estándolo, byte a byte. Se compara sólo el
  // material del vault y no su `.git`, que avanza por diseño: el retiro agrega
  // el commit del manifiesto, así que exigir el árbol entero idéntico sería
  // exigir que el punto de no retorno no ocurriera.
  const despuesDelVault = await snapshotTree(e.vault);
  let comparadas = 0;
  for (const [ruta, valor] of antesDelVault) {
    if (!ruta.startsWith('projects/')) continue;
    comparadas += 1;
    assert.equal(despuesDelVault.get(ruta), valor, `el vault perdió ${ruta}`);
  }
  assert.ok(comparadas >= 6, `sólo se compararon ${comparadas} rutas del vault`);
});

test('[AC-5] el verbo declara la raíz destructiva antes de ejecutar', async (t) => {
  const e = await escena(t);
  const { informe } = await correr(e, { 'dry-run': true });
  const io = new DurableFs();

  await correr(e, { 'approve-digest': informe.digest }, { fs: io });

  // La contención quedó viva en esa instancia: una destrucción fuera de la raíz
  // declarada se rechaza aunque llegue por un alias o un helper. Sin esta
  // declaración el mecanismo existe y no protege nada.
  const afuera = path.join(e.repoRoot, 'ajeno.md');
  await fs.writeFile(afuera, 'no se toca\n', 'utf8');
  await assert.rejects(() => io.unlink(afuera, 'prueba.unlink'), (error) => {
    assert.equal(error.code, 'OUT_OF_BOUNDS');
    return true;
  });
  assert.equal(await fs.readFile(afuera, 'utf8'), 'no se toca\n');
});

// ── AC-5b · digest de alcance frente a digest por flujo ──────────────────────

test('[AC-5b] un cambio de alcance invalida el lote entero', async (t) => {
  const e = await escena(t);
  const { informe } = await correr(e, { 'dry-run': true });

  // Aparece un flujo más entre la aprobación y la ejecución. Lo que se aprobó
  // describía otro conjunto, así que no se toca nada — ni siquiera los dos que
  // sí estaban aprobados.
  await e.caja.makeTree(path.join(e.raiz, 'abc-3'), { 'spec.md': '# nuevo\n' });
  let ejecutado = 0;

  await assert.rejects(
    () => correr(e, { 'approve-digest': informe.digest }, { ejecutor: async () => { ejecutado += 1; } }),
    (error) => error.code === 'PRECONDITION_NOT_MET',
  );
  assert.equal(ejecutado, 0);
});

test('[AC-5b] un cambio en un flujo concreto falla ese flujo y no el lote', async (t) => {
  const e = await escena(t);
  // La frontera de `abc-1` se altera **antes** del ensayo: el ensayo lo ve, el
  // digest del lote lo incluye como no-a-salvo, y el retiro real corre igual
  // saltándose ese flujo. Un solo digest global habría abortado los dos.
  await fs.writeFile(
    path.join(e.vault, 'projects', REPO_ID, 'sdd', 'abc-1', 'spec.md'), '# manoseado\n', 'utf8',
  );
  const { informe } = await correr(e, { 'dry-run': true });
  const vistos = [];

  const r = await correr(e, { 'approve-digest': informe.digest }, {
    ejecutor: async ({ flujo }) => { vistos.push(flujo.flowId); return { flowId: flujo.flowId, estado: 'RETIRADO' }; },
  });

  assert.deepEqual(vistos, ['abc-2'], 'se retiró un flujo que no estaba a salvo');
  // Uno retirado y uno fallido es **parcial**, no fallido: `BATCH_FAILED` está
  // reservado para cero retirados, que es un lote que no avanzó nada.
  assert.equal(r.status, ESTADOS.BATCH_PARTIAL);
  assert.deepEqual(
    r.informe.resultados.filter((x) => x.estado === 'FALLO').map((x) => x.flowId),
    ['abc-1'],
  );
});

test('[AC-5b] los dos digests son distintos y el del lote se mueve con el conjunto', async (t) => {
  const e = await escena(t, { archivados: ['abc-1', 'abc-2'] });
  const lote = await correr(e, { 'dry-run': true });
  const solo = await correr(e, { 'dry-run': true, from: path.join(e.raiz, 'abc-1') });

  // Mismo vault y mismo commit: el digest de `abc-1` describe su árbol y no
  // cambia porque al lado haya otro flujo.
  const enLote = lote.informe.flujos.find((f) => f.flowId === 'abc-1').digest;
  const enSolo = solo.informe.flujos.find((f) => f.flowId === 'abc-1').digest;
  assert.equal(enLote, enSolo);

  // El del lote sí cambia: describe el **alcance**, y el alcance es otro. Sin
  // esta separación habría que elegir entre no ver un flujo que aparece o
  // abortar los dos porque uno cambió.
  assert.notEqual(lote.informe.digest, solo.informe.digest);
  assert.notEqual(lote.informe.digest, enLote);
  assert.notEqual(solo.informe.digest, enSolo);

  // Y el commit del vault entra en los dos: el manifiesto autoriza destruir
  // contra una copia concreta, no contra "el vault".
  assert.equal(lote.informe.vaultCommit, solo.informe.vaultCommit);
});

// ── `omitidos` · el inventario omitido del ensayo dirigido ──────────────────

test('el ensayo dirigido expone el conjunto exacto omitido', async (t) => {
  const e = await escena(t, { archivados: ['abc-1'] });
  const flowDir = e.flujos[0];
  // `notas.txt` ya lo pone `escena()`, a la raíz. Se agregan anidados de las dos
  // clases —Markdown y no Markdown— para probar que la exclusión es posicional
  // y no de extensión.
  const anidados = {
    'reports/explore.md': '# hallazgos\n\nno copiable por estar anidado\n',
    'reports/nested/data.json': '{"ok":true}\n',
  };
  for (const [rel, contenido] of Object.entries(anidados)) {
    const destino = path.join(flowDir, rel);
    await fs.mkdir(path.dirname(destino), { recursive: true });
    await fs.writeFile(destino, contenido, 'utf8');
  }

  const oracle = [];
  for (const rel of ['notas.txt', 'reports/explore.md', 'reports/nested/data.json']) {
    const bytes = await fs.readFile(path.join(flowDir, rel));
    oracle.push({ path: rel, size: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') });
  }
  oracle.sort((a, b) => (a.path < b.path ? -1 : 1));

  const { informe } = await correr(e, { 'dry-run': true, from: flowDir });

  assert.deepEqual(informe.flujos[0].omitidos, oracle);
});

test('el ensayo por lote de un único flujo conserva la salida agregada sin omitidos', async (t) => {
  const e = await escena(t, { archivados: ['abc-1'] });
  const { informe } = await correr(e, { 'dry-run': true });

  assert.deepEqual(informe.flujos.map((f) => f.flowId), ['abc-1']);
  assert.ok(!Object.hasOwn(informe.flujos[0], 'omitidos'), 'el lote sin --from expuso omitidos');
});

test('un flujo no seguro por VERIFY_FAILED excluye Markdown raíz de omitidos', async (t) => {
  const e = await escena(t, { archivados: ['abc-1'] });
  // La misma alteración de frontera que usa la prueba de AC-4 más arriba.
  await fs.writeFile(
    path.join(e.vault, 'projects', REPO_ID, 'sdd', 'abc-1', 'spec.md'), '# manoseado\n', 'utf8',
  );

  const { informe } = await correr(e, { 'dry-run': true, from: e.flujos[0] });
  const flujo = informe.flujos[0];

  assert.equal(flujo.causa, 'VERIFY_FAILED');
  assert.equal(flujo.aSalvo, false);
  // `spec.md` y `plan.md` son Markdown de raíz y copiables: no figuran, aunque
  // el flujo entero haya quedado sin copia verificada.
  assert.deepEqual(flujo.omitidos.map((o) => o.path), ['notas.txt']);
});

test('una medición fallida conserva omitidos null', async (t) => {
  const e = await escena(t, { archivados: ['abc-1'] });
  const io = new DurableFs({ failAt: 'retire.manifest.scan.readdir' });

  const { informe } = await correr(e, { 'dry-run': true, from: e.flujos[0] }, { fs: io });
  const flujo = informe.flujos[0];

  assert.equal(flujo.bytes, null);
  assert.ok(typeof flujo.error === 'string' && flujo.error.length > 0, 'no informó la medición fallida');
  assert.equal(flujo.omitidos, null, 'un inventario fallido no puede mostrar un conjunto vacío');
});

test('el retiro real dirigido no expone omitidos', async (t) => {
  const e = await escena(t, { archivados: ['abc-1'] });
  const flowDir = e.flujos[0];
  const { informe: ensayo } = await correr(e, { 'dry-run': true, from: flowDir });

  const r = await correr(e, { from: flowDir, 'approve-digest': ensayo.digest }, {
    ejecutor: async ({ flujo }) => ({ flowId: flujo.flowId, estado: 'RETIRADO' }),
  });

  assert.equal(r.status, ESTADOS.BATCH_OK);
  assert.ok(!Object.hasOwn(r.informe.flujos[0], 'omitidos'), 'el retiro real expuso omitidos');
});

// ── La identidad declarada gobierna el verbo ─────────────────────────────────

test('[AC-13] sin identidad declarada en el vault, el verbo se detiene', async (t) => {
  const e = await escena(t);
  await fs.rm(path.join(e.vault, '.kv', 'identidades.tsv'));

  await assert.rejects(() => correr(e, { 'dry-run': true }), (error) => {
    assert.equal(error.code, 'AMBIGUOUS_IDENTITY');
    return true;
  });
});

// ── AC-8 · los tres estados del lote ─────────────────────────────────────────

test('[AC-8] un lote vacío es BATCH_OK, no un fallo', async (t) => {
  // El vault sí tiene material —si no, el fallo sería la precondición global de
  // "vault sin commits" y este test mediría otra cosa—; lo que está vacío es la
  // raíz de archivados.
  const e = await escena(t, { archivados: ['abc-1'] });
  await fs.rename(path.join(e.raiz, 'abc-1'), path.join(e.repoRoot, 'guardado'));
  const { informe } = await correr(e, { 'dry-run': true });

  const r = await correr(e, { 'approve-digest': informe.digest });
  assert.equal(r.status, ESTADOS.BATCH_OK);
  assert.deepEqual(r.informe.resultados, []);
});

test('[AC-8] un lote ya retirado vuelve a dar BATCH_OK', async (t) => {
  const e = await escena(t);
  const primero = await correr(e, { 'dry-run': true });
  assert.equal((await correr(e, { 'approve-digest': primero.informe.digest })).status, ESTADOS.BATCH_OK);

  // Sin objetivos ni remanentes, el segundo lote está vacío: no queda trabajo, y
  // eso no es un fallo. Un cierre idempotente tiene que poder correr dos veces.
  const segundo = await correr(e, { 'dry-run': true });
  const r = await correr(e, { 'approve-digest': segundo.informe.digest });
  assert.equal(r.status, ESTADOS.BATCH_OK);
});

test('[AC-8] cero retirados y al menos uno fallido es BATCH_FAILED', async (t) => {
  const e = await escena(t, { archivados: ['abc-1'] });
  await fs.rename(path.join(e.raiz, 'abc-1'), path.join(e.repoRoot, 'guardado'));
  await e.caja.makeTree(path.join(e.raiz, 'sin-copia'), { 'spec.md': '# nadie me archivó\n' });
  const { informe } = await correr(e, { 'dry-run': true });

  const r = await correr(e, { 'approve-digest': informe.digest });
  assert.equal(r.status, ESTADOS.BATCH_FAILED);
  assert.deepEqual(r.informe.resultados.map((x) => x.estado), ['FALLO']);
});

test('[AC-8] las precondiciones globales fallan cerrado antes de cualquier borrado', async (t) => {
  const e = await escena(t);
  const antes = await snapshotTree(e.raiz);
  // Una precondición global: la identidad declarada. Falla antes de mirar un
  // solo flujo, así que no puede haber borrado parcial.
  await fs.rm(path.join(e.vault, '.kv', 'identidades.tsv'));

  await assert.rejects(() => correr(e, { 'approve-digest': 'f'.repeat(64) }), (error) => {
    assert.equal(error.code, 'AMBIGUOUS_IDENTITY');
    return true;
  });
  assert.deepEqual(await snapshotTree(e.raiz), antes);
});

test('[AC-8] un fallo individual no se lleva puesto el lote', async (t) => {
  const e = await escena(t, { archivados: ['abc-1', 'abc-2'] });
  // `abc-1` no verifica; `abc-2` sí. El lote tiene que terminar habiendo
  // retirado el segundo, no abortar en el primero.
  await fs.writeFile(
    path.join(e.vault, 'projects', REPO_ID, 'sdd', 'abc-1', 'spec.md'), '# manoseado\n', 'utf8',
  );
  const { informe } = await correr(e, { 'dry-run': true });

  const r = await correr(e, { 'approve-digest': informe.digest });
  assert.equal(r.status, ESTADOS.BATCH_PARTIAL);
  assert.deepEqual((await fs.readdir(e.raiz)).sort(), ['abc-1'], 'no se retiró el flujo sano');
});

test('[AC-8] un remanente huérfano entra al lote y se adopta', async (t) => {
  const e = await escena(t);
  // Una corrida anterior murió después del reclamo: queda el remanente y el
  // flujo ya no está en su ruta. Si el lote no lo enumerara, quedaría ahí para
  // siempre — ningún barrido lo mira y su flujo no existe.
  await fs.rename(path.join(e.raiz, 'abc-1'), path.join(e.raiz, '.kv-retirando-abc-1'));
  const { informe } = await correr(e, { 'dry-run': true });
  assert.ok(informe.flujos.some((f) => f.flowId === 'abc-1'), 'el remanente huérfano no entró al lote');

  const r = await correr(e, { 'approve-digest': informe.digest });
  // Sin manifiesto, el reclamo no estaba autorizado: se deshace, y el flujo
  // vuelve a su ruta intacto.
  assert.equal(r.status, ESTADOS.BATCH_OK);
  assert.ok((await fs.readdir(e.raiz)).includes('abc-1'), 'el flujo no volvió a su ruta');
});

// ── AC-11 · los sueltos quedan intactos y se nombran ─────────────────────────

test('[AC-11] los archivos sueltos no se procesan y quedan byte a byte', async (t) => {
  const e = await escena(t, { sueltos: ['README.md', 'notas-sueltas.md'] });
  const { informe: ensayo } = await correr(e, { 'dry-run': true });

  await correr(e, { 'approve-digest': ensayo.digest });

  const quedan = (await fs.readdir(e.raiz)).sort();
  assert.deepEqual(quedan, ['README.md', 'notas-sueltas.md']);
  assert.equal(await fs.readFile(path.join(e.raiz, 'README.md'), 'utf8'), 'suelto\n');
});

test('[AC-11] el reporte los nombra en vez de afirmar que la raíz quedó vacía', async (t) => {
  const e = await escena(t, { sueltos: ['README.md'] });
  const { informe } = await correr(e, { 'dry-run': true });

  // La raíz **no** queda literalmente vacía, y el reporte tiene que decirlo: es
  // el costo asumido de tocar sólo directorios hijos directos.
  assert.deepEqual(informe.remanentesNoProcesados.map((p) => path.basename(p)), ['README.md']);
  assert.ok(informe.remanentesNoProcesados.length > 0);
  assert.ok(!informe.flujos.some((f) => f.flowId === 'README.md'), 'un suelto entró como flujo');
});

// ── AC-16 · archivar, verificar y recién entonces retirar ────────────────────
//
// Estas tres filas dejaron de ser búsquedas de frases literales —que se
// satisfacen escribiendo la frase— y pasaron a **ejecutar el escenario**. La
// prosa del ciclo SDD dice el orden; lo que se comprueba acá es que el verbo lo
// vuelva imposible de violar en silencio.

test('[AC-16] retirar sin haber archivado es imposible, y el flujo queda intacto', async (t) => {
  const e = await escena(t, { archivados: ['abc-1'] });
  // Un flujo que nunca pasó por el vault, al lado de uno que sí.
  const sinArchivar = await e.caja.makeTree(path.join(e.raiz, 'nunca'), { 'spec.md': '# sin copia\n' });
  const antes = await snapshotTree(sinArchivar);
  const { informe } = await correr(e, { 'dry-run': true });

  const r = await correr(e, { 'approve-digest': informe.digest });
  assert.equal(r.status, ESTADOS.BATCH_PARTIAL);
  assert.deepEqual(await snapshotTree(sinArchivar), antes, 'se retiró algo sin copia verificada');
});

test('[AC-16] una instalación sin el verbo falla cerrado y no mueve nada', async (t) => {
  const e = await escena(t);
  const antes = await snapshotTree(e.raiz);
  // Es el caso concreto del criterio: el CLI existe y su versión no tiene el
  // verbo. El escenario se ejecuta —no se declara— cableando el CLI sin él.
  const r = await runCli({
    argv: ['retire', '--root', e.raiz, '--vault-root', e.vault, '--dry-run'],
    comandos: { archive: async () => ({ status: 'ARCHIVED' }) },
    fs: new DurableFs(),
  });

  assert.notEqual(r.exitCode, 0, 'salió cero sin poder retirar');
  assert.deepEqual(await snapshotTree(e.raiz), antes, 'degradó a mover el flujo igual');
});

test('[AC-16] un fallo posterior al punto de no retorno deja remanente parcial reintentable', async (t) => {
  const e = await escena(t, { archivados: ['abc-1'] });
  const { informe } = await correr(e, { 'dry-run': true });
  // Muere en medio del borrado, con el manifiesto ya commiteado.
  const caido = new DurableFs({ crashAt: 'retire.destruir.archivo' });
  await correr(e, { 'approve-digest': informe.digest }, { fs: caido });

  // El resultado **no** es un origen intacto: es un remanente parcial. Exigir
  // "intacto ante cualquier fallo" haría imposible el retiro por entradas.
  const quedan = (await fs.readdir(e.raiz)).sort();
  assert.deepEqual(quedan, ['.kv-retirando-abc-1']);

  // Y es reintentable: el segundo lote lo adopta y lo termina.
  const segundo = await correr(e, { 'dry-run': true });
  const r = await correr(e, { 'approve-digest': segundo.informe.digest });
  assert.equal(r.status, ESTADOS.BATCH_OK);
  assert.deepEqual(await fs.readdir(e.raiz), []);
});

// ── AC-17 · la reanudación resuelve sin escribir ─────────────────────────────

test('[AC-17] tras un archivado exitoso y un retiro fallido, reanudar no escribe', async (t) => {
  const e = await escena(t, { archivados: ['abc-1'] });
  await fs.writeFile(
    path.join(e.vault, 'projects', REPO_ID, 'sdd', 'abc-1', 'spec.md'), '# manoseado\n', 'utf8',
  );
  const grabador = new Recorder();

  const { informe } = await correr(e, { 'dry-run': true }, { fs: new DurableFs({ recorder: grabador }) });

  assert.equal(informe.flujos[0].aSalvo, false);
  const MUTAN = new Set(['mkdir', 'openExclusive', 'copyFile', 'writeFile', 'writeFileAtomic',
    'rename', 'unlink', 'rmTree', 'removeEmptyDir', 'fsyncFile', 'fsyncDir']);
  assert.deepEqual(grabador.entries.filter((o) => MUTAN.has(o.op)).map((o) => o.label), []);
});

test('[AC-17] reanudar no rearchiva: ni copia duplicada ni commit espurio', async (t) => {
  const e = await escena(t, { archivados: ['abc-1'] });
  const { stdout: antes } = await git(e.vault, 'rev-list', '--count', 'HEAD');
  const antesDelArbol = await snapshotTree(path.join(e.vault, 'projects'));

  // Tres reanudaciones seguidas. Si alguna usara `kv archive` como sonda —con un
  // resumen distinto al original— reescribiría el nodo y crearía un commit.
  for (let i = 0; i < 3; i += 1) await correr(e, { 'dry-run': true });

  const { stdout: despues } = await git(e.vault, 'rev-list', '--count', 'HEAD');
  assert.equal(despues.trim(), antes.trim(), 'reanudar creó un commit');
  assert.deepEqual(await snapshotTree(path.join(e.vault, 'projects')), antesDelArbol);
});

test('[AC-17] cada punto de corte tiene una ubicación observable distinta', async (t) => {
  const observado = async (e, flowId) => {
    const { informe } = await correr(e, { 'dry-run': true });
    const f = informe.flujos.find((x) => x.flowId === flowId);
    const enRaiz = (await fs.readdir(e.raiz)).sort();
    return {
      enRaiz: enRaiz.includes(flowId),
      remanente: enRaiz.includes(`.kv-retirando-${flowId}`),
      aSalvo: f?.aSalvo ?? null,
    };
  };

  // Corte 1: archivado sin correr. Corte 2: archivado y verificado, sin retirar.
  // El vault necesita material propio o el fallo sería "vault sin commits", que
  // es otra precondición y haría que este test midiera otra cosa.
  const sinArchivar = await escena(t, { archivados: ['otro'] });
  await sinArchivar.caja.makeTree(path.join(sinArchivar.raiz, 'abc-1'), { 'spec.md': '# x\n' });
  const archivado = await escena(t, { archivados: ['abc-1'] });

  const uno = await observado(sinArchivar, 'abc-1');
  const dos = await observado(archivado, 'abc-1');
  assert.deepEqual(uno, { enRaiz: true, remanente: false, aSalvo: false });
  assert.deepEqual(dos, { enRaiz: true, remanente: false, aSalvo: true });
  assert.notDeepEqual(uno, dos, 'los dos primeros cortes son indistinguibles');

  // Corte 4: el flujo ya salió del listado de activos y todavía no llegó a
  // destino — remanente sin objetivo. Es el que el criterio nombra aparte.
  await fs.rename(path.join(archivado.raiz, 'abc-1'), path.join(archivado.raiz, '.kv-retirando-abc-1'));
  const tres = await observado(archivado, 'abc-1');
  assert.equal(tres.enRaiz, false);
  assert.equal(tres.remanente, true);
});

// ── AC-5c · el ciclo no encadena ensayo y retiro real ────────────────────────

test('[AC-5c] una invocación no puede ensayar y retirar a la vez', async (t) => {
  const e = await escena(t);
  const { informe } = await correr(e, { 'dry-run': true });
  const antes = await snapshotTree(e.raiz);

  // La forma exacta que tiene un guion de eliminar el gate: correr el ensayo y
  // pasar su digest en la misma invocación.
  await assert.rejects(() => correr(e, { 'dry-run': true, 'approve-digest': informe.digest }), (error) => {
    assert.equal(error.code, 'USAGE');
    assert.match(error.message, /excluyentes/);
    return true;
  });
  assert.deepEqual(await snapshotTree(e.raiz), antes);
});

test('[AC-5c] el ensayo no deja el digest en ningún lado del que leerlo solo', async (t) => {
  const e = await escena(t);
  const antesRaiz = await snapshotTree(e.raiz);
  const antesVault = await snapshotTree(e.vault);

  const { informe } = await correr(e, { 'dry-run': true });
  assert.match(informe.digest, /^[0-9a-f]{64}$/);

  // El digest existe **sólo** en la salida que una persona lee. Si el ensayo lo
  // persistiera, el retiro real podría leerlo y el gate desaparecería sin que
  // ninguna bandera lo delatara.
  assert.deepEqual(await snapshotTree(e.raiz), antesRaiz);
  assert.deepEqual(await snapshotTree(e.vault), antesVault);
});
