/**
 * T11 — escaneo, copia y verificación (AC-13, AC-14, AC-21).
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import fsRaw from 'node:fs/promises';
import path from 'node:path';

import { DurableFs } from '../../../skills/knowledge-vault/scripts/lib/durable-fs.mjs';
import { PortablePathError } from '../../../skills/knowledge-vault/scripts/lib/portable-path.mjs';
import {
  TreeError,
  assertIncludedTreePortable,
  collisionGroups,
  copyTree,
  fsyncTreeDirs,
  listFiles,
  scanInventory,
  verifyTree,
} from '../../../skills/knowledge-vault/scripts/lib/tree.mjs';
import { createSandbox } from './helpers/sandbox.mjs';
import { snapshotTree } from './helpers/tree-snapshot.mjs';

const EMOJI = String.fromCodePoint(0x1f600);

function falla(fn, code) {
  return assert.rejects(fn, (err) => {
    assert.ok(err instanceof TreeError, `se esperaba TreeError, llegó ${err?.name}: ${err?.message}`);
    assert.equal(err.code, code);
    return true;
  });
}

/** Un flujo SDD realista: documentos, análisis, prompts, scratch. */
const FLUJO = {
  'plan.md': 'plan',
  'spec.md': 'spec',
  'input/task.md': 'entrada',
  'cross-review/verdict-r1.txt': 'veredicto',
  'cross-review/prompt-r1.txt': 'prompt',
  'cross-review/session.txt': 'sesion',
  'node_modules/pkg/index.js': 'codigo',
  'node_modules/pkg/README.md': 'readme',
  'work/borrador.md': 'borrador',
};

async function origen(sandbox, arbol = FLUJO) {
  return sandbox.makeTree(sandbox.path('repos', 'demo', '.plans', 'abc-1'), arbol);
}

/**
 * Lo que un consumidor cualquiera elegiría preservar de `FLUJO`.
 *
 * Este módulo ya no clasifica nada: la partición la trae un manifiesto. Para
 * probar copia y verificación hace falta **un** conjunto de incluidos, y se
 * enumera a mano en vez de derivarlo de una política — enumerarlo deja claro que
 * la elección es del que llama, no de `tree.mjs`.
 */
const INCLUIDOS = ['cross-review/verdict-r1.txt', 'plan.md', 'spec.md'];

async function incluidos(fs, root, rutas = INCLUIDOS) {
  const { files } = await scanInventory({ fs, root });
  return files.filter((f) => rutas.includes(f.path));
}

// ── Inventario neutral (scanInventory) ────────────────────────────────────────

test('`scanInventory` describe el árbol y NO lo clasifica', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);

  const { files, directories } = await scanInventory({ fs: new DurableFs(), root });

  // Los nueve archivos, sin excepción: acá no hay política que omita nada.
  assert.equal(files.length, 9);
  assert.deepEqual(directories, []);

  // Un `prompt-r1.txt` es un archivo como cualquier otro: puede que un consumidor
  // decida no preservarlo, pero eso lo dice su manifiesto. El inventario no opina.
  const prompt = files.find((f) => f.path === 'cross-review/prompt-r1.txt');
  assert.ok(prompt, 'el prompt tiene que estar en el inventario');
  assert.deepEqual(Object.keys(prompt).sort(), ['path', 'sha256', 'size', 'type']);
  // Ni `disposition` ni `rule`: un número de regla dentro de una identidad es
  // justo el acoplamiento que este cambio elimina.
  assert.equal(prompt.disposition, undefined);
  assert.equal(prompt.rule, undefined);
});

test('`scanInventory` representa los directorios vacíos, y solo los vacíos', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await sandbox.makeTree(sandbox.path('repos', 'demo', 'x'), {
    'a.md': 'a',
    'lleno/b.md': 'b',
    'vacio/': null,
    'padre/hijo-vacio/': null,
  });

  const { files, directories } = await scanInventory({ fs: new DurableFs(), root });

  assert.deepEqual(files.map((f) => f.path), ['a.md', 'lleno/b.md']);
  // `padre` NO está: contiene a `hijo-vacio`, así que no está vacío. Un
  // directorio con un solo hijo vacío sigue teniendo una entrada.
  assert.deepEqual(directories.map((d) => d.path), ['padre/hijo-vacio', 'vacio']);
  assert.deepEqual(directories[0], { path: 'padre/hijo-vacio', type: 'directory' });
});

test('`scanInventory` no registra la raíz como entrada, ni cuando está vacía', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await sandbox.makeTree(sandbox.path('repos', 'demo', 'vacia'), {});

  const { files, directories } = await scanInventory({ fs: new DurableFs(), root });

  // La raíz es el contenedor, no contenido: registrarla produciría una entrada con
  // `path` vacío, que no describe nada y entraría al `source_fingerprint`.
  assert.deepEqual(files, []);
  assert.deepEqual(directories, []);
});

test('`scanInventory` emite las dos listas ordenadas, aunque el filesystem no colabore', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await sandbox.makeTree(sandbox.path('repos', 'demo', 'orden'), {
    'z.md': 'z',
    'a.md': 'a',
    'm/n.md': 'n',
    'zz/': null,
    'aa/': null,
  });

  // APFS devuelve `readdir` ya ordenado, así que sobre el disco real este test
  // pasaría **aunque el escaneo no ordenara nada**: el mutante que quita el `sort`
  // sobrevive en macOS y muere en ext4. Se invierte el orden de lectura para que la
  // prueba mida el escaneo y no el filesystem de quien la corre.
  // Delegación explícita con `bind`: `DurableFs` usa campos privados de clase, así
  // que heredar por prototipo rompe su chequeo de receptor.
  const disco = new DurableFs();
  const alReves = {
    lstat: disco.lstat.bind(disco),
    hashFile: disco.hashFile.bind(disco),
    readDirNames: async (...args) => [...(await disco.readDirNames(...args))].reverse(),
  };

  const { files, directories } = await scanInventory({ fs: alReves, root });

  // El orden no es cosmético: el inventario alimenta el `source_fingerprint`, y la
  // canonicalización **verifica** el orden en vez de arreglarlo.
  assert.deepEqual(files.map((f) => f.path), ['a.md', 'm/n.md', 'z.md']);
  assert.deepEqual(directories.map((d) => d.path), ['aa', 'zz']);
});

test('`scanInventory` aborta ante lo que no es archivo ni directorio', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  await sandbox.makeSymlink(path.join(root, 'atajo.md'), 'plan.md');

  await falla(() => scanInventory({ fs: new DurableFs(), root }), 'UNSUPPORTED_SOURCE_ENTRY');
});

test('`scanInventory` sin hashes recorre lo mismo y deja `sha256` en null', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);

  const con = await scanInventory({ fs: new DurableFs(), root });
  const sin = await scanInventory({ fs: new DurableFs(), root, withHashes: false });

  assert.deepEqual(sin.files.map((f) => f.path), con.files.map((f) => f.path));
  assert.ok(sin.files.every((f) => f.sha256 === null));
  assert.ok(con.files.every((f) => typeof f.sha256 === 'string'));
});

// ── AC-21: una entrada por archivo, nunca una por el directorio ───────────────

test('un directorio entero rinde una entrada POR ARCHIVO, no una por el directorio', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);

  const { files, directories } = await scanInventory({ fs: new DurableFs(), root });
  const deNodeModules = files.filter((e) => e.path.startsWith('node_modules/'));

  // "Está node_modules" no describe lo que un intento puede llegar a destruir:
  // el receipt necesita el archivo, su tamaño y su hash.
  assert.deepEqual(deNodeModules.map((e) => e.path), [
    'node_modules/pkg/README.md',
    'node_modules/pkg/index.js',
  ]);
  for (const entrada of deNodeModules) {
    assert.match(entrada.sha256, /^[0-9a-f]{64}$/);
    assert.ok(entrada.size > 0);
  }
  // `node_modules` tiene contenido, así que no aparece entre los vacíos ni como
  // una entrada que resuma a sus hijos.
  assert.ok(!directories.some((e) => e.path === 'node_modules'));
  assert.ok(!files.some((e) => e.path === 'node_modules'));
});

test('se entra a TODOS los directorios y se hashea su contenido', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  const disco = new DurableFs();

  await scanInventory({ fs: disco, root });

  // Sin hashear lo que después se omita, un archivo omitido podría cambiar sus
  // bytes manteniendo el tamaño y se retiraría un origen que ya no es el
  // archivado.
  const hasheados = disco.recorder.find('scan.hash').length;
  assert.equal(hasheados, 9);
});

test('un emoji en el árbol no aborta nada', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox, { ...FLUJO, [`node_modules/pkg/${EMOJI}.js`]: 'x' });

  const { files } = await scanInventory({ fs: new DurableFs(), root });
  assert.ok(files.some((e) => e.path === `node_modules/pkg/${EMOJI}.js`));
});

// ── AC-7: la portabilidad se juzga sobre los INCLUIDOS, y solo sobre ellos ────

test('un nombre no portable que no se archiva no aborta', async (t) => {
  const sandbox = await createSandbox(t);
  // `aux.js` es un nombre reservado de Windows y aparece de verdad en paquetes npm.
  const root = await origen(sandbox, { ...FLUJO, 'node_modules/pkg/aux.js': 'x' });
  const disco = new DurableFs();

  // El inventario lo lista sin opinar: describir no es archivar.
  const { files } = await scanInventory({ fs: disco, root });
  assert.ok(files.some((e) => e.path === 'node_modules/pkg/aux.js'));

  // Y si el consumidor no lo incluye, nunca se escribe en ningún lado: viaja al
  // receipt como texto dentro de un JSON. Abortar el archivado entero por esto no
  // tendría salida posible.
  assert.equal(assertIncludedTreePortable(await incluidos(disco, root), root), undefined);
});

test('un nombre no portable entre los INCLUIDOS sí aborta', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox, { ...FLUJO, 'aux.md': 'x' });
  const seleccionados = await incluidos(new DurableFs(), root, [...INCLUIDOS, 'aux.md']);

  assert.throws(() => assertIncludedTreePortable(seleccionados, root), (err) => {
    assert.ok(err instanceof PortablePathError);
    assert.equal(err.code, 'RESERVED_NAME');
    return true;
  });
});

/**
 * La guarda de colisión se prueba **sin filesystem**.
 *
 * No es comodidad: en macOS y en Windows no se pueden crear dos hermanos que
 * colisionen —el sistema los trata como el mismo archivo y el segundo pisa al
 * primero—, así que el recorrido real jamás puede construir el caso. Justamente
 * por eso la guarda existe: protege a quien archive **desde Linux**, donde sí
 * coexisten, hacia un vault que después se lea en macOS.
 */
test('la colisión se evalúa sobre los incluidos y sobre los directorios que llevan a uno', () => {
  const incluido = (p) => ({ path: p, disposition: 'included' });

  assert.throws(() => assertIncludedTreePortable([incluido('Plan.md'), incluido('plan.md')]), (err) => {
    assert.equal(err.code, 'SIBLING_COLLISION');
    return true;
  });

  // Un directorio que conduce a un incluido participa igual que un archivo.
  assert.throws(() => assertIncludedTreePortable([incluido('Docs/a.md'), incluido('docs/b.md')]), (err) => {
    assert.equal(err.code, 'SIBLING_COLLISION');
    return true;
  });

  // El par NFC/NFD, que coexiste en Linux y colisiona en un filesystem con
  // equivalencia canónica.
  const nfc = `caf${String.fromCodePoint(0xe9)}.md`;
  const nfd = `cafe${String.fromCodePoint(0x301)}.md`;
  assert.throws(() => assertIncludedTreePortable([incluido(nfc), incluido(nfd)]), (err) => {
    assert.equal(err.code, 'SIBLING_COLLISION');
    return true;
  });

  // Nombres distintos en directorios distintos no colisionan.
  assert.equal(
    assertIncludedTreePortable([incluido('a/Plan.md'), incluido('b/plan.md')]),
    undefined,
  );
});

test('los grupos de colisión abarcan cada nivel de cada path incluido', () => {
  const grupos = collisionGroups([
    { path: 'plan.md' },
    { path: 'docs/guia/a.md' },
    { path: 'docs/guia/b.md' },
  ]);

  assert.deepEqual([...grupos.keys()].sort(), ['', 'docs', 'docs/guia']);
  assert.deepEqual(grupos.get('').sort(), ['docs', 'plan.md']);
  assert.deepEqual(grupos.get('docs'), ['guia']);
  assert.deepEqual(grupos.get('docs/guia').sort(), ['a.md', 'b.md']);
});

test('una colisión entre lo NO incluido no aborta', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await sandbox.makeTree(sandbox.path('repos', 'b'), {
    'plan.md': 'x',
    'Work/notas.txt': 'a',
    'work/otras.txt': 'b',
  });

  // Lo que no se incluye no participa de la guarda: nunca se escribe en ningún
  // lado, así que dos hermanos que colisionarían en macOS son irrelevantes.
  const seleccionados = await incluidos(new DurableFs(), root, ['plan.md']);
  assert.equal(assertIncludedTreePortable(seleccionados, root), undefined);
  assert.deepEqual(collisionGroups([{ path: 'plan.md' }]).get(''), ['plan.md']);
});

test('en un filesystem case-sensitive la colisión real aborta antes de copiar', async (t) => {
  const sandbox = await createSandbox(t);
  const sonda = sandbox.path('sonda');
  await fsRaw.mkdir(sonda);
  await fsRaw.writeFile(path.join(sonda, 'a'), '1');
  const sensible = await fsRaw
    .stat(path.join(sonda, 'A'))
    .then(() => false)
    .catch(() => true);

  if (!sensible) {
    t.skip('filesystem case-insensitive: no se pueden crear dos hermanos que colisionen');
    return;
  }

  const root = await sandbox.makeTree(sandbox.path('repos', 'a'), { 'Plan.md': 'a', 'plan.md': 'b' });
  const seleccionados = await incluidos(new DurableFs(), root, ['Plan.md', 'plan.md']);
  assert.throws(() => assertIncludedTreePortable(seleccionados, root), (err) => {
    assert.equal(err.code, 'SIBLING_COLLISION');
    return true;
  });
});

// ── AC-14: symlinks y archivos especiales ─────────────────────────────────────

test('aborta ante un symlink interno', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  await sandbox.makeSymlink(path.join(root, 'atajo.md'), path.join(root, 'plan.md'));

  await falla(() => scanInventory({ fs: new DurableFs(), root }), 'UNSUPPORTED_SOURCE_ENTRY');
});

test('aborta ante un symlink externo', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  await sandbox.makeSymlink(path.join(root, 'afuera.md'), sandbox.path('vaults'));

  await falla(() => scanInventory({ fs: new DurableFs(), root }), 'UNSUPPORTED_SOURCE_ENTRY');
});

test('aborta ante un symlink roto', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  await sandbox.makeSymlink(path.join(root, 'roto.md'), path.join(root, 'no-existe.md'));

  // `lstat` lo ve igual: por eso no se usa `stat` en el escaneo del origen.
  await falla(() => scanInventory({ fs: new DurableFs(), root }), 'UNSUPPORTED_SOURCE_ENTRY');
});

test('aborta ante un symlink cíclico sin recorrerlo infinitamente', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  await sandbox.makeSymlink(path.join(root, 'ciclo'), root);

  await falla(() => scanInventory({ fs: new DurableFs(), root }), 'UNSUPPORTED_SOURCE_ENTRY');
});

test('aborta ante un symlink a directorio', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  await sandbox.makeSymlink(path.join(root, 'enlace-dir'), path.join(root, 'input'));

  await falla(() => scanInventory({ fs: new DurableFs(), root }), 'UNSUPPORTED_SOURCE_ENTRY');
});

test('aborta si `--from` es un symlink', async (t) => {
  const sandbox = await createSandbox(t);
  const real = await origen(sandbox);
  const enlace = sandbox.path('repos', 'enlace-al-flujo');
  await sandbox.makeSymlink(enlace, real);

  await falla(() => scanInventory({ fs: new DurableFs(), root: enlace }), 'UNSUPPORTED_SOURCE_ENTRY');
});

test('aborta ante un archivo especial', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);

  const { execFile } = await import('node:child_process');
  const { promisify } = await import('node:util');
  try {
    await promisify(execFile)('mkfifo', [path.join(root, 'tuberia')]);
  } catch {
    t.skip('no hay mkfifo disponible');
    return;
  }

  await falla(() => scanInventory({ fs: new DurableFs(), root }), 'UNSUPPORTED_SOURCE_ENTRY');
});

test('un symlink dentro de un directorio omitido también aborta', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  await sandbox.makeSymlink(path.join(root, 'node_modules', 'enlace'), sandbox.path('vaults'));

  // AC-21 obliga a recorrerlos, así que AC-14 también aplica adentro.
  await falla(() => scanInventory({ fs: new DurableFs(), root }), 'UNSUPPORTED_SOURCE_ENTRY');
});

test('el origen ausente o que no es directorio da SOURCE_UNAVAILABLE', async (t) => {
  const sandbox = await createSandbox(t);
  await falla(() => scanInventory({ fs: new DurableFs(), root: sandbox.path('no-existe') }), 'SOURCE_UNAVAILABLE');

  const archivo = sandbox.path('soy-archivo');
  await fsRaw.writeFile(archivo, 'x');
  await falla(() => scanInventory({ fs: new DurableFs(), root: archivo }), 'SOURCE_UNAVAILABLE');
});

test('el escaneo no escribe nada', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  const antes = await snapshotTree(root);

  const disco = new DurableFs();
  await scanInventory({ fs: disco, root });

  assert.deepEqual(await snapshotTree(root), antes);
  const ops = new Set(disco.recorder.entries.map((e) => e.op));
  assert.deepEqual([...ops].sort(), ['hashFile', 'lstat', 'readDirNames']);
});

// ── Copia ─────────────────────────────────────────────────────────────────────

test('copia solo lo incluido, con creación exclusiva y fsync por archivo', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  const staging = sandbox.path('vaults', 'staging');
  const disco = new DurableFs();

  const included = await incluidos(disco, root);
  disco.recorder.reset();
  await copyTree({ fs: disco, from: root, to: staging, entries: included });

  const copiados = (await listFiles({ fs: new DurableFs(), root: staging })).map((e) => e.path);
  assert.deepEqual(copiados.sort(), ['cross-review/verdict-r1.txt', 'plan.md', 'spec.md']);

  assert.equal(disco.recorder.find('copy.file').length, 3);
  assert.equal(disco.recorder.find('copy.fsync').length, 3);
  // Lo omitido no viaja.
  assert.ok(!copiados.some((p) => p.startsWith('node_modules/')));
});

test('la copia falla si el destino ya tenía ese archivo', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  const staging = sandbox.path('vaults', 'staging');
  await sandbox.makeTree(staging, { 'plan.md': 'contenido ajeno' });

  const included = await incluidos(new DurableFs(), root);
  // Copiar encima produciría una revisión que no es la que se calculó.
  await assert.rejects(
    () => copyTree({ fs: new DurableFs(), from: root, to: staging, entries: included }),
    (err) => err.code === 'EEXIST',
  );
});

test('`fsyncTreeDirs` va de hojas a raíz', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  const staging = sandbox.path('vaults', 'staging');
  const disco = new DurableFs();

  const included = await incluidos(disco, root);
  await copyTree({ fs: disco, from: root, to: staging, entries: included });
  const orden = await fsyncTreeDirs({ fs: disco, root: staging, entries: included });

  // Sincronizar un padre antes que su hijo no garantiza que la entrada del hijo
  // esté durable.
  const profundidades = orden.map((d) => d.split(path.sep).length);
  assert.deepEqual(profundidades, [...profundidades].sort((a, b) => b - a));
  assert.equal(orden.at(-1), staging);
});

// ── AC-13: verificación por hashes Y conjunto exacto ──────────────────────────

test('verifica un destino correcto', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  const staging = sandbox.path('vaults', 'staging');
  const disco = new DurableFs();

  const included = await incluidos(disco, root);
  await copyTree({ fs: disco, from: root, to: staging, entries: included });

  const verificados = await verifyTree({ fs: disco, root: staging, expected: included });
  assert.equal(verificados.length, 3);
});

test('un archivo DE MÁS en el destino falla la verificación', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  const staging = sandbox.path('vaults', 'staging');
  const disco = new DurableFs();

  const included = await incluidos(disco, root);
  await copyTree({ fs: disco, from: root, to: staging, entries: included });
  await fsRaw.writeFile(path.join(staging, 'colado.md'), 'no debería estar');

  // Comparar solo los hashes de lo esperado dejaría pasar contenido extra, que
  // ya no es la revisión que se calculó.
  await assert.rejects(() => verifyTree({ fs: disco, root: staging, expected: included }), (err) => {
    assert.equal(err.code, 'VERIFY_FAILED');
    assert.deepEqual(err.detail.extra, ['colado.md']);
    assert.deepEqual(err.detail.missing, []);
    return true;
  });
});

test('un archivo faltante o con contenido distinto falla la verificación', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  const staging = sandbox.path('vaults', 'staging');
  const disco = new DurableFs();

  const included = await incluidos(disco, root);
  await copyTree({ fs: disco, from: root, to: staging, entries: included });

  await fsRaw.writeFile(path.join(staging, 'plan.md'), 'otro contenido');
  await assert.rejects(() => verifyTree({ fs: disco, root: staging, expected: included }), (err) => {
    assert.deepEqual(err.detail.mismatched, ['plan.md']);
    return true;
  });

  await fsRaw.rm(path.join(staging, 'spec.md'));
  await assert.rejects(() => verifyTree({ fs: disco, root: staging, expected: included }), (err) => {
    assert.deepEqual(err.detail.missing, ['spec.md']);
    return true;
  });
});

test('un archivo del mismo tamaño con otros bytes falla', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await sandbox.makeTree(sandbox.path('repos', 'demo'), { 'plan.md': 'aaaa' });
  const staging = sandbox.path('vaults', 'staging');
  const disco = new DurableFs();

  const included = await incluidos(disco, root);
  await copyTree({ fs: disco, from: root, to: staging, entries: included });
  await fsRaw.writeFile(path.join(staging, 'plan.md'), 'bbbb');

  await assert.rejects(() => verifyTree({ fs: disco, root: staging, expected: included }), (err) => {
    assert.deepEqual(err.detail.mismatched, ['plan.md']);
    return true;
  });
});

test('la verificación aborta si el destino tiene un symlink', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await origen(sandbox);
  const staging = sandbox.path('vaults', 'staging');
  const disco = new DurableFs();

  const included = await incluidos(disco, root);
  await copyTree({ fs: disco, from: root, to: staging, entries: included });
  await sandbox.makeSymlink(path.join(staging, 'enlace.md'), path.join(staging, 'plan.md'));

  await falla(() => verifyTree({ fs: disco, root: staging, expected: included }), 'UNSUPPORTED_SOURCE_ENTRY');
});

// ── Directorios vacíos: se describen, pero no se copian ───────────────────────

test('un directorio vacío entra al inventario y no viaja en la copia', async (t) => {
  const sandbox = await createSandbox(t);
  const root = await sandbox.makeTree(sandbox.path('repos', 'demo'), { 'plan.md': 'x', 'vacio/': null });
  const staging = sandbox.path('vaults', 'staging');
  const disco = new DurableFs();

  const { files, directories } = await scanInventory({ fs: disco, root });
  // Está en el inventario —y por lo tanto en el `source_fingerprint`— para que
  // crear un directorio vacío entre el escaneo y el retiro no pase inadvertido.
  assert.deepEqual(directories.map((d) => d.path), ['vacio']);

  // Pero la copia y la verificación son sobre archivos: un directorio no tiene
  // bytes que hashear, y la pérdida está declarada en el plan §3.2.
  await copyTree({ fs: disco, from: root, to: staging, entries: files });
  const copiados = (await listFiles({ fs: new DurableFs(), root: staging })).map((e) => e.path);
  assert.deepEqual(copiados, ['plan.md']);
  await falla(() => scanInventory({ fs: disco, root: path.join(staging, 'vacio') }), 'SOURCE_UNAVAILABLE');
});
