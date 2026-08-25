/**
 * T8 — primitivas etiquetadas, inyección y recorder (AC-7, AC-25b).
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import fsRaw from 'node:fs/promises';
import path from 'node:path';

import {
  DurableFs,
  DurableFsError,
  InjectedCrash,
  Recorder,
  classifyFsyncError,
  decodeEntryName,
  isInjectedCrash,
} from '../../../skills/knowledge-vault/scripts/lib/durable-fs.mjs';
import { createSandbox } from './helpers/sandbox.mjs';
import { diffSnapshots, snapshotTree } from './helpers/tree-snapshot.mjs';

const BOM = String.fromCodePoint(0xfeff);

function falla(fn, code) {
  return assert.rejects(fn, (err) => {
    assert.ok(err instanceof DurableFsError, `se esperaba DurableFsError, llegó ${err?.name}`);
    assert.equal(err.code, code);
    return true;
  });
}

// ── Etiquetado obligatorio ────────────────────────────────────────────────────

test('toda operación necesita un label', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();

  await falla(() => disco.mkdir(sandbox.path('x')), 'MISSING_LABEL');
  await falla(() => disco.writeFile(sandbox.path('x'), Buffer.from('a'), ''), 'MISSING_LABEL');
});

test('el recorder registra op, label y rutas en orden de invocación', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();

  await disco.mkdir(sandbox.path('a'), 'mkdir.staging');
  await disco.writeFile(sandbox.path('a', 'f.txt'), Buffer.from('hola'), 'write.manifest');
  await disco.fsyncFile(sandbox.path('a', 'f.txt'), 'fsync.file');
  await disco.rename(sandbox.path('a'), sandbox.path('b'), 'publish.rename');

  assert.deepEqual(disco.recorder.labels(), [
    'mkdir.staging',
    'write.manifest',
    'fsync.file',
    'publish.rename',
  ]);
  assert.deepEqual(
    disco.recorder.entries.map((e) => e.op),
    ['mkdir', 'writeFile', 'fsyncFile', 'rename'],
  );
  assert.ok(disco.recorder.entries.every((e) => e.outcome === 'ok'));
  assert.deepEqual(disco.recorder.entries[3].paths, [sandbox.path('a'), sandbox.path('b')]);

  // El campo `seq` es un ordinal estable: sobrevive a filtrar la traza, que es
  // lo que hace falta para ubicar una operación dentro de la secuencia entera
  // después de quedarse solo con las que ocurrieron.
  assert.deepEqual(disco.recorder.entries.map((e) => e.seq), [0, 1, 2, 3]);
  assert.deepEqual(disco.recorder.succeeded().map((e) => e.seq), [0, 1, 2, 3]);
});

test('el recorder es el oracle del ORDEN, no solo del disparo', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();

  await disco.writeFile(sandbox.path('receipt.json'), Buffer.from('{}'), 'receipt.write');
  await disco.mkdir(sandbox.path('rev'), 'publish.mkdir');

  // Que el receipt exista y la revisión exista no dice nada del orden; la traza sí.
  assert.ok(disco.recorder.happenedBefore('receipt.write', 'publish.mkdir'));
  assert.ok(!disco.recorder.happenedBefore('publish.mkdir', 'receipt.write'));
  assert.throws(() => disco.recorder.happenedBefore('receipt.write', 'inexistente'), /no contiene/);
});

test('el recorder distingue lo intentado de lo efectivamente ocurrido', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs({ failAt: 'write.malo' });

  await disco.writeFile(sandbox.path('bien.txt'), Buffer.from('a'), 'write.bueno');
  await assert.rejects(() => disco.writeFile(sandbox.path('mal.txt'), Buffer.from('a'), 'write.malo'));

  assert.equal(disco.recorder.entries.length, 2);
  assert.deepEqual(disco.recorder.succeeded().map((e) => e.label), ['write.bueno']);
});

// ── Inyección de fallos ───────────────────────────────────────────────────────

test('`failAt` falla en el label exacto y no toca los demás', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs({ failAt: { label: 'publish.rename', code: 'EIO' } });

  await disco.mkdir(sandbox.path('origen'), 'mkdir.staging');
  await falla(
    () => disco.rename(sandbox.path('origen'), sandbox.path('destino'), 'publish.rename'),
    'EIO',
  );
  // Falla **antes** del syscall: el árbol queda como estaba.
  assert.ok(await fsRaw.stat(sandbox.path('origen')));
  await assert.rejects(() => fsRaw.stat(sandbox.path('destino')));
});

test('`failAt` con `nth` deja pasar las primeras ocurrencias', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs({ failAt: { label: 'copy.file', nth: 2 } });

  await disco.writeFile(sandbox.path('uno.txt'), Buffer.from('1'), 'copy.file');
  await assert.rejects(() => disco.writeFile(sandbox.path('dos.txt'), Buffer.from('2'), 'copy.file'));
  await disco.writeFile(sandbox.path('tres.txt'), Buffer.from('3'), 'copy.file');

  assert.deepEqual(
    disco.recorder.entries.map((e) => e.outcome),
    ['ok', 'failed', 'ok'],
  );
});

test('`failAt` acepta un predicado para casos como EXDEV', async (t) => {
  const sandbox = await createSandbox(t);
  // No hace falta tener dos volúmenes reales para probar el camino cross-filesystem.
  const disco = new DurableFs({
    failAt: ({ op }) => (op === 'rename' ? Object.assign(new DurableFsError('EXDEV', 'cross-device'), { injected: true }) : null),
  });

  await disco.mkdir(sandbox.path('a'), 'mkdir.a');
  await falla(() => disco.rename(sandbox.path('a'), sandbox.path('b'), 'local.rename'), 'EXDEV');
});

test('`partial` deja que la operación produzca su efecto a medias antes de fallar', async (t) => {
  const sandbox = await createSandbox(t);
  await sandbox.makeTree(sandbox.path('remanente'), {
    'a.md': 'a',
    'b.md': 'b',
    'c.md': 'c',
  });

  const disco = new DurableFs({ failAt: { label: 'rm.remnant', partial: 2 } });
  await assert.rejects(() => disco.rmTree(sandbox.path('remanente'), 'rm.remnant'));

  // Borró un subconjunto **real**: es el estado que obliga a `DELETE_STARTED` a
  // continuar sin recalcular el digest, porque ya no hay árbol completo.
  const quedaron = await fsRaw.readdir(sandbox.path('remanente'));
  assert.deepEqual(quedaron, ['c.md']);
});

// ── Inyección de caídas ───────────────────────────────────────────────────────

test('`checkpoint` sin regla es un no-op que igual queda en la traza', async () => {
  const disco = new DurableFs();
  disco.checkpoint('journal.PREPARED');
  disco.checkpoint('journal.RENAMED');

  assert.deepEqual(disco.recorder.labels(), ['journal.PREPARED', 'journal.RENAMED']);
  assert.ok(disco.recorder.entries.every((e) => e.op === 'checkpoint' && e.outcome === 'ok'));
});

test('`crashAt` lanza InjectedCrash y se distingue de un error de I/O', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs({ crashAt: 'journal.RENAMED' });

  disco.checkpoint('journal.PREPARED');
  assert.throws(() => disco.checkpoint('journal.RENAMED'), (err) => {
    assert.ok(err instanceof InjectedCrash);
    assert.ok(isInjectedCrash(err));
    assert.ok(!(err instanceof DurableFsError), 'una caída no es un error de I/O');
    assert.equal(err.label, 'journal.RENAMED');
    return true;
  });

  // También sobre una primitiva, y sin llegar a tocar el disco.
  const otro = new DurableFs({ crashAt: 'publish.rename' });
  await sandbox.makeTree(sandbox.path('origen'), { 'a.md': 'a' });
  await assert.rejects(
    () => otro.rename(sandbox.path('origen'), sandbox.path('destino'), 'publish.rename'),
    isInjectedCrash,
  );
  assert.ok(await fsRaw.stat(sandbox.path('origen')));
  assert.equal(otro.recorder.entries[0].outcome, 'crash');
});

// ── removeEmptyDir: la primitiva que evita una pérdida silenciosa ─────────────

test('`removeEmptyDir` borra un directorio vacío', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();
  const vacio = sandbox.path('vacio');
  await fsRaw.mkdir(vacio);

  await disco.removeEmptyDir(vacio, 'dest.remove-empty');
  await assert.rejects(() => fsRaw.stat(vacio));
});

test('`removeEmptyDir` falla ante un directorio que ganó contenido', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();
  const destino = sandbox.path('destino');
  await fsRaw.mkdir(destino);

  // Se clasificó como vacío...
  assert.deepEqual(await fsRaw.readdir(destino), []);
  // ...y entre la clasificación y el retiro apareció contenido.
  await fsRaw.writeFile(path.join(destino, 'del-usuario.md'), 'no me borres');

  await falla(() => disco.removeEmptyDir(destino, 'dest.remove-empty'), 'ENOTEMPTY');

  // Lo que apareció sigue ahí: un `rmTree` lo habría eliminado en silencio.
  assert.equal(await fsRaw.readFile(path.join(destino, 'del-usuario.md'), 'utf8'), 'no me borres');
});

test('`removeEmptyDir` no es recursivo ni siquiera con subdirectorios vacíos', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();
  await fsRaw.mkdir(sandbox.path('padre', 'hijo'), { recursive: true });

  await falla(() => disco.removeEmptyDir(sandbox.path('padre'), 'dest.remove-empty'), 'ENOTEMPTY');
  assert.ok(await fsRaw.stat(sandbox.path('padre', 'hijo')));
});

// ── Lectura de nombres congelada (AC-7, plan §3.2) ────────────────────────────

test('lee los nombres por bytes y conserva la forma exacta', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();
  const base = sandbox.path('arbol');

  const nfc = `caf${String.fromCodePoint(0xe9)}.md`;
  const nfd = `cafe${String.fromCodePoint(0x301)}.md`;
  await fsRaw.mkdir(base, { recursive: true });
  await fsRaw.writeFile(path.join(base, nfc), 'a');
  await fsRaw.writeFile(path.join(base, 'plan.md'), 'b');

  const entradas = await disco.readDirNames(base, 'scan.readdir');
  const nombres = entradas.map((e) => e.name).sort();
  assert.deepEqual(nombres, [nfc, 'plan.md'].sort());

  // Se devuelven los bytes exactos, que son los que entran al digest.
  const entrada = entradas.find((e) => e.name === nfc);
  assert.ok(entrada.bytes.equals(Buffer.from(nfc, 'utf8')));
  assert.notEqual(nfc, nfd, 'el fixture no colapsó');
});

test('un nombre con bytes que no son UTF-8 se rechaza sin colapsar a U+FFFD', async () => {
  // `0xff` no puede aparecer en UTF-8 válido.
  const invalido = Buffer.from([0x61, 0xff, 0x62]);

  // La prueba de que el rechazo hace falta: el decode normal lo destruiría, y dos
  // nombres POSIX distintos colapsarían en el mismo path.
  const colapsado = invalido.toString('utf8');
  assert.equal(colapsado, `a${String.fromCodePoint(0xfffd)}b`);
  assert.ok(!Buffer.from(colapsado, 'utf8').equals(invalido));

  assert.throws(() => decodeEntryName(invalido, '/tmp/x'), (err) => {
    assert.equal(err.code, 'UNSUPPORTED_SOURCE_ENTRY');
    return true;
  });
});

test('un nombre que empieza con BOM conserva su U+FEFF', async () => {
  // Con el decoder por defecto el BOM se consume y el nombre pierde bytes: se
  // escribiría un archivo con otro nombre que el leído.
  const conBom = `${BOM}raro.md`;
  const bytes = Buffer.from(conBom, 'utf8');

  assert.notEqual(new TextDecoder('utf-8').decode(bytes), conBom, 'el default lo estropea');
  assert.equal(decodeEntryName(bytes).name, conBom);
});

test('un nombre real con UTF-8 inválido en disco se rechaza al escanear', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();
  const base = sandbox.path('arbol');
  await fsRaw.mkdir(base, { recursive: true });

  // Se crea por bytes crudos: en Linux/macOS un nombre así es perfectamente legal.
  const nombreCrudo = Buffer.concat([Buffer.from(path.join(base, 'x')), Buffer.from([0xff])]);
  try {
    await fsRaw.writeFile(nombreCrudo, 'contenido');
  } catch {
    t.skip('el filesystem no acepta nombres con bytes inválidos');
    return;
  }

  await falla(() => disco.readDirNames(base, 'scan.readdir'), 'UNSUPPORTED_SOURCE_ENTRY');
});

test('acepta el repertorio completo de nombres válidos', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();
  const base = sandbox.path('arbol');
  await fsRaw.mkdir(base, { recursive: true });

  const nombres = ['plan.md', '你好.md', `${String.fromCodePoint(0x1f600)}.md`, 'ру.md'];
  for (const nombre of nombres) await fsRaw.writeFile(path.join(base, nombre), 'x');

  const leidos = (await disco.readDirNames(base, 'scan.readdir')).map((e) => e.name);
  for (const nombre of nombres) assert.ok(leidos.includes(nombre), nombre);
});

// ── fsync fail-closed (R8) ────────────────────────────────────────────────────

test('`fsyncFile` y `fsyncDir` funcionan sobre rutas reales', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();
  await fsRaw.writeFile(sandbox.path('f.txt'), 'a');

  await disco.fsyncFile(sandbox.path('f.txt'), 'fsync.file');
  await disco.fsyncDir(sandbox.root, 'fsync.dir');
  assert.deepEqual(disco.recorder.succeeded().map((e) => e.label), ['fsync.file', 'fsync.dir']);
});

test('un errno de "no soportado" se traduce a FSYNC_UNSUPPORTED', () => {
  // Se prueba la traducción real con errores sintéticos. Inyectar directamente
  // un `FSYNC_UNSUPPORTED` por label probaría el inyector, no esta lógica — y en
  // una plataforma que sí soporta fsync de directorios no hay otra forma.
  const errno = (code) => Object.assign(new Error(code), { code });

  for (const code of ['EINVAL', 'EPERM', 'ENOTSUP', 'EBADF']) {
    const traducido = classifyFsyncError(errno(code), '/v/raw', { stage: 'sync' });
    assert.ok(traducido instanceof DurableFsError);
    assert.equal(traducido.code, 'FSYNC_UNSUPPORTED');
    assert.equal(traducido.path, '/v/raw');
    assert.equal(traducido.cause.code, code);
  }

  for (const code of ['EISDIR', 'EPERM', 'EACCES']) {
    assert.equal(classifyFsyncError(errno(code), '/v', { stage: 'open' }).code, 'FSYNC_UNSUPPORTED');
  }
});

test('un errno que NO es "no soportado" se deja pasar tal cual', () => {
  // Un disco lleno o un archivo ausente son fallos reales, no ausencia de
  // soporte: confundirlos taparía el problema de verdad.
  const errno = (code) => Object.assign(new Error(code), { code });

  for (const code of ['ENOSPC', 'ENOENT', 'EIO']) {
    const pasado = classifyFsyncError(errno(code), '/v/raw', { stage: 'sync' });
    assert.ok(!(pasado instanceof DurableFsError));
    assert.equal(pasado.code, code);
  }
  // En `open`, la traducción solo aplica a directorios; un EISDIR de archivo sube crudo.
  assert.equal(classifyFsyncError(errno('EISDIR'), '/v/f', { stage: 'sync' }).code, 'EISDIR');
});

test('no se degrada a seguir sin sincronizar', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();
  // Un fsync sobre una ruta inexistente sube el error; nunca se traga.
  await assert.rejects(
    () => disco.fsyncDir(sandbox.path('no-existe'), 'fsync.dir'),
    (err) => err.code === 'ENOENT',
  );
  assert.equal(disco.recorder.entries[0].outcome, 'failed');
});

// ── Resto de primitivas ───────────────────────────────────────────────────────

test('`openExclusive` crea y falla si el destino ya existe', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();
  const destino = sandbox.path('receipt.json');

  await disco.openExclusive(destino, Buffer.from('{"a":1}'), 'receipt.write');
  assert.equal(await fsRaw.readFile(destino, 'utf8'), '{"a":1}');

  await assert.rejects(
    () => disco.openExclusive(destino, Buffer.from('{"a":2}'), 'receipt.write'),
    (err) => err.code === 'EEXIST',
  );
  // El contenido previo queda intacto: nunca se sobrescribe.
  assert.equal(await fsRaw.readFile(destino, 'utf8'), '{"a":1}');
});

test('`copyFile` es exclusiva por defecto', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();
  await fsRaw.writeFile(sandbox.path('origen.md'), 'contenido');

  await disco.copyFile(sandbox.path('origen.md'), sandbox.path('copia.md'), 'copy.file');
  assert.equal(await fsRaw.readFile(sandbox.path('copia.md'), 'utf8'), 'contenido');

  await assert.rejects(
    () => disco.copyFile(sandbox.path('origen.md'), sandbox.path('copia.md'), 'copy.file'),
    (err) => err.code === 'EEXIST',
  );
});

test('`lstat` devuelve null ante ENOENT y no sigue symlinks', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();

  assert.equal(await disco.lstat(sandbox.path('no-existe'), 'scan.lstat'), null);

  await fsRaw.writeFile(sandbox.path('real.md'), 'x');
  await sandbox.makeSymlink(sandbox.path('enlace.md'), sandbox.path('real.md'));
  const info = await disco.lstat(sandbox.path('enlace.md'), 'scan.lstat');
  assert.ok(info.isSymbolicLink(), 'lstat no debe seguir el enlace');
});

test('`writeFileAtomic` descompone la secuencia durable en la traza', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs();

  await disco.writeFileAtomic(sandbox.path('journal.json'), Buffer.from('{"phase":"PREPARED"}'), 'journal.write');

  assert.deepEqual(disco.recorder.labels(), [
    'journal.write.tmp',
    'journal.write.tmp.fsync',
    'journal.write.rename',
    'journal.write.fsync-dir',
  ]);
  assert.equal(await fsRaw.readFile(sandbox.path('journal.json'), 'utf8'), '{"phase":"PREPARED"}');
  // El temporal no queda tirado.
  assert.ok(!(await fsRaw.readdir(sandbox.root)).some((n) => n.startsWith('.kv-tmp-')));
});

test('el temporal abandonado por una caída es reconocible como de `kv`', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs({ crashAt: 'journal.write.tmp.fsync' });

  await assert.rejects(
    () => disco.writeFileAtomic(sandbox.path('journal.json'), Buffer.from('{}'), 'journal.write'),
    isInjectedCrash,
  );

  // Lleva prefijo propio y oculto: no se confunde con material del usuario ni
  // con un staging de publicación, que usan otros prefijos.
  const restos = (await fsRaw.readdir(sandbox.root)).filter((n) => n.startsWith('.kv-tmp-'));
  assert.deepEqual(restos, ['.kv-tmp-journal.json']);
  await assert.rejects(() => fsRaw.stat(sandbox.path('journal.json')));
});

test('si `writeFileAtomic` falla en el rename, el destino no aparece a medias', async (t) => {
  const sandbox = await createSandbox(t);
  const disco = new DurableFs({ failAt: 'journal.write.rename' });

  await assert.rejects(() =>
    disco.writeFileAtomic(sandbox.path('journal.json'), Buffer.from('{}'), 'journal.write'),
  );
  await assert.rejects(() => fsRaw.stat(sandbox.path('journal.json')));
});

// ── uniqueTemp y expectBytes (T4) ─────────────────────────────────────────────

test('con uniqueTemp, dos escrituras concurrentes no comparten el temporal', async (t) => {
  const sandbox = await createSandbox(t);
  const fs = new DurableFs({ recorder: new Recorder() });
  const a = sandbox.path('a.yml');
  const b = sandbox.path('b.yml');

  // El temporal fijo se derivaba del basename del target: dos targets con el mismo
  // basename en el mismo directorio no existen, pero DOS ESCRITURAS DEL MISMO
  // TARGET sí comparten el temporal, y ahí está la colisión.
  await Promise.all([
    fs.writeFileAtomic(a, Buffer.from('uno\n'), 'w1', { uniqueTemp: true }),
    fs.writeFileAtomic(b, Buffer.from('dos\n'), 'w2', { uniqueTemp: true }),
  ]);

  assert.equal((await fsRaw.readFile(a, 'utf8')), 'uno\n');
  assert.equal((await fsRaw.readFile(b, 'utf8')), 'dos\n');
  const restos = (await fsRaw.readdir(sandbox.root)).filter((n) => n.startsWith('.kv-tmp-'));
  assert.deepEqual(restos, [], 'no quedan temporales abandonados');
});

test('con uniqueTemp, dos INSTANCIAS de DurableFs no repiten el temporal aunque compartan pid', async (t) => {
  const sandbox = await createSandbox(t);
  // Dos instancias en el MISMO proceso: mismo pid. Si la unicidad dependiera de
  // un contador propio de cada instancia, las dos arrancan en el mismo valor y
  // generan el mismo nombre de temporal aunque el pid coincida con la realidad.
  const disco1 = new DurableFs({ recorder: new Recorder() });
  const disco2 = new DurableFs({ recorder: new Recorder() });
  const target = sandbox.path('compartido.yml');

  await Promise.all([
    disco1.writeFileAtomic(target, Buffer.from('uno\n'), 'w1', { uniqueTemp: true }),
    disco2.writeFileAtomic(target, Buffer.from('dos\n'), 'w2', { uniqueTemp: true }),
  ]);

  const temporal1 = disco1.recorder.find('w1.tmp')[0].paths[0];
  const temporal2 = disco2.recorder.find('w2.tmp')[0].paths[0];
  assert.notEqual(temporal1, temporal2, 'dos instancias no deben compartir el mismo temporal');

  const final = await fsRaw.readFile(target, 'utf8');
  assert.ok(final === 'uno\n' || final === 'dos\n', `contenido inesperado: ${JSON.stringify(final)}`);
  const restos = (await fsRaw.readdir(sandbox.root)).filter((n) => n.startsWith('.kv-tmp-'));
  assert.deepEqual(restos, [], 'no quedan temporales abandonados');
});

test('con uniqueTemp, dos escrituras concurrentes al MISMO target no colisionan en el temporal', async (t) => {
  const sandbox = await createSandbox(t);
  const fs = new DurableFs({ recorder: new Recorder() });
  const target = sandbox.path('mismo.yml');

  // Acá sí está la colisión real que el test anterior no puede ver: mismo basename,
  // mismo target, así que sin `uniqueTemp` ambas escrituras comparten un único
  // temporal y una le pisa el intermedio a la otra.
  await Promise.all([
    fs.writeFileAtomic(target, Buffer.from('uno\n'), 'w1', { uniqueTemp: true }),
    fs.writeFileAtomic(target, Buffer.from('dos\n'), 'w2', { uniqueTemp: true }),
  ]);

  // No importa cuál ganó la carrera del `rename`: lo que importa es que el
  // resultado sea una de las dos escrituras completas, no un intermedio corrupto.
  const final = await fsRaw.readFile(target, 'utf8');
  assert.ok(final === 'uno\n' || final === 'dos\n', `contenido inesperado: ${JSON.stringify(final)}`);
  const restos = (await fsRaw.readdir(sandbox.root)).filter((n) => n.startsWith('.kv-tmp-'));
  assert.deepEqual(restos, [], 'no quedan temporales abandonados');
});

test('expectBytes aborta si el archivo cambió en disco entre la lectura y la publicación', async (t) => {
  const sandbox = await createSandbox(t);
  const fs = new DurableFs({ recorder: new Recorder() });
  const target = sandbox.path('config.yml');
  await fsRaw.writeFile(target, 'original\n');

  const leidos = Buffer.from('original\n');
  // Alguien más lo guarda: el usuario en su editor.
  await fsRaw.writeFile(target, 'editado por el usuario\n');

  await assert.rejects(
    fs.writeFileAtomic(target, Buffer.from('nuestro\n'), 'w', { expectBytes: leidos }),
    (e) => {
      assert.equal(e.code, 'CONFLICT');
      return true;
    },
  );
  // Y lo importante: la edición del usuario sigue intacta.
  assert.equal(await fsRaw.readFile(target, 'utf8'), 'editado por el usuario\n');
  // Y el temporal que se llegó a escribir no queda tirado tras el aborto.
  const restos = (await fsRaw.readdir(sandbox.root)).filter((n) => n.startsWith('.kv-tmp-'));
  assert.deepEqual(restos, [], 'no quedan temporales abandonados tras el CONFLICT');
});

test('expectBytes con un archivo que todavía no existe exige el buffer vacío', async (t) => {
  const sandbox = await createSandbox(t);
  const fs = new DurableFs({ recorder: new Recorder() });
  const target = sandbox.path('nuevo.yml');

  await fs.writeFileAtomic(target, Buffer.from('a\n'), 'w', { expectBytes: Buffer.alloc(0) });
  assert.equal(await fsRaw.readFile(target, 'utf8'), 'a\n');

  // Y si aparece entre medio, es conflicto.
  await assert.rejects(
    fs.writeFileAtomic(target, Buffer.from('b\n'), 'w', { expectBytes: Buffer.alloc(0) }),
    (e) => e.code === 'CONFLICT',
  );
});

test('sin los flags nuevos, el comportamiento es el de siempre', async (t) => {
  const sandbox = await createSandbox(t);
  const fs = new DurableFs({ recorder: new Recorder() });
  const target = sandbox.path('viejo.yml');
  await fs.writeFileAtomic(target, Buffer.from('x\n'), 'w');
  assert.equal(await fsRaw.readFile(target, 'utf8'), 'x\n');
});

// ── El snapshot como oracle independiente ─────────────────────────────────────

test('el snapshot detecta cualquier escritura, y no detecta ninguna si no la hubo', async (t) => {
  const sandbox = await createSandbox(t);
  await sandbox.makeTree(sandbox.path('vault'), { 'raw/a.md': 'a', 'log.md': 'entrada' });

  const antes = await snapshotTree(sandbox.path('vault'));

  // Una corrida read-only no mueve nada.
  const disco = new DurableFs();
  await disco.readDirNames(sandbox.path('vault'), 'doctor.scan');
  await disco.lstat(sandbox.path('vault', 'log.md'), 'doctor.lstat');
  assert.deepEqual(diffSnapshots(antes, await snapshotTree(sandbox.path('vault'))), []);

  // Un solo byte cambiado sí aparece.
  await fsRaw.appendFile(sandbox.path('vault', 'log.md'), '!');
  const diferencias = diffSnapshots(antes, await snapshotTree(sandbox.path('vault')));
  assert.equal(diferencias.length, 1);
  assert.match(diferencias[0], /^~ log\.md/);
});

test('el snapshot registra symlinks por destino, sin seguirlos', async (t) => {
  const sandbox = await createSandbox(t);
  await sandbox.makeTree(sandbox.path('arbol'), { 'real.md': 'x' });
  await sandbox.makeSymlink(sandbox.path('arbol', 'enlace.md'), sandbox.path('arbol', 'real.md'));

  const foto = await snapshotTree(sandbox.path('arbol'));
  assert.match(foto.get('enlace.md'), /^symlink:/);
  assert.match(foto.get('real.md'), /^file:1:/);
});

// ── Canonicalización de rutas que pueden no existir ───────────────────────────

test('realpathExistingPrefix resuelve un ancestro enlazado, exista o no el final', async (t) => {
  // El hueco entre `path.resolve` (léxico, no mira el disco) y `realpath` (falla
  // con ENOENT si el final no está): una ruta cuyo **directorio** es un enlace.
  const sandbox = await createSandbox(t);
  const fs = new DurableFs();
  const real = sandbox.path('real');
  await fsRaw.mkdir(real, { recursive: true });
  await fsRaw.symlink(real, sandbox.path('alias'));
  await fsRaw.writeFile(path.join(real, 'hay.yml'), 'x\n');

  // (a) El archivo existe: las dos rutas canonicalizan a la misma.
  assert.equal(
    await fs.realpathExistingPrefix(sandbox.path('alias', 'hay.yml'), 'rp'),
    path.join(real, 'hay.yml'),
  );

  // (b) El archivo NO existe: el ancestro se resuelve igual y el segmento que
  //     falta se vuelve a pegar. Es el caso que `realpath` no puede atender.
  assert.equal(
    await fs.realpathExistingPrefix(sandbox.path('alias', 'no-esta.yml'), 'rp'),
    path.join(real, 'no-esta.yml'),
  );

  // (c) Varios segmentos ausentes, en orden.
  assert.equal(
    await fs.realpathExistingPrefix(sandbox.path('alias', 'a', 'b', 'c.yml'), 'rp'),
    path.join(real, 'a', 'b', 'c.yml'),
  );
});

test('realpathExistingPrefix devuelve un enlace roto sin resolver, en vez de fallar', async (t) => {
  const sandbox = await createSandbox(t);
  const fs = new DurableFs();
  const roto = sandbox.path('roto.yml');
  await fsRaw.symlink(sandbox.path('no-existe'), roto);

  // Esa **es** su ruta canónica. Que un destino ausente sea un error o no lo
  // decide quien llama, no esta función.
  assert.equal(await fs.realpathExistingPrefix(roto, 'rp'), roto);
});

test('realpathExistingPrefix no se traga un error que no sea de ruta ausente', async (t) => {
  const sandbox = await createSandbox(t);
  const fs = new DurableFs({ failAt: 'rp' });
  await falla(() => fs.realpathExistingPrefix(sandbox.path('lo-que-sea.yml'), 'rp'), 'EIO');
});

// ── Recorder aislado ──────────────────────────────────────────────────────────

test('el recorder se puede compartir entre instancias para una traza única', async (t) => {
  const sandbox = await createSandbox(t);
  const recorder = new Recorder();

  // Es lo que necesita el test de recuperación: cae, se instancia de nuevo el
  // núcleo sobre el mismo temporal, y la traza sigue siendo una sola.
  const primera = new DurableFs({ recorder, crashAt: 'paso.dos' });
  await primera.mkdir(sandbox.path('a'), 'paso.uno');
  assert.throws(() => primera.checkpoint('paso.dos'), InjectedCrash);

  const segunda = new DurableFs({ recorder });
  await segunda.mkdir(sandbox.path('b'), 'paso.tres');

  assert.deepEqual(recorder.labels(), ['paso.uno', 'paso.dos', 'paso.tres']);
  assert.deepEqual(recorder.entries.map((e) => e.outcome), ['ok', 'crash', 'ok']);

  recorder.reset();
  assert.deepEqual(recorder.labels(), []);
});
