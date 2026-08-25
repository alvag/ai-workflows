/**
 * El manifiesto del retiro (AC-3, AC-3b).
 *
 * Dos propiedades distintas se prueban acá. **Que sea autoridad** (AC-3): su
 * digest cambia ante cualquiera de las siete cosas que cubre, y su lista de
 * directorios admite el reintento en vez de rechazarlo. **Que no siga enlaces**
 * (AC-3b): cualquier tipo que no sea archivo regular o directorio detiene la
 * operación nombrando la ruta y su tipo, porque un symlink seguido convierte un
 * borrado acotado en un borrado en cualquier parte del disco.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';

import { DurableFs } from '../../../skills/knowledge-vault/scripts/lib/durable-fs.mjs';
import {
  CLASES,
  SCHEMA_MANIFIESTO,
  construirManifiesto,
  digestManifiesto,
} from '../../../skills/knowledge-vault/scripts/lib/manifest.mjs';
import { createSandbox } from './helpers/sandbox.mjs';

const IDENTIDAD = { repoId: 'api-pagos', flowId: 'abc-1' };
const COMMIT = 'a'.repeat(40);

/** Un origen con archivos anidados y un directorio ya vacío. */
async function origen(caja, extra = {}) {
  const dir = await caja.makeTree(path.join(caja.reposDir, 'proyecto', '.plans', 'archived', 'abc-1'), {
    'spec.md': '# Exportar\n',
    'plan.md': '# Plan\n',
    'notas.txt': 'no viaja\n',
    'cross-review/veredicto.md': 'veredicto\n',
    'vacio/': null,
    ...extra,
  });
  return dir;
}

const construir = (flowDir, aSalvo = ['plan.md', 'spec.md']) =>
  construirManifiesto({ fs: new DurableFs(), flowDir, aSalvo, identidad: IDENTIDAD, vaultCommit: COMMIT });

// ── AC-3 · el manifiesto es durable y es autoridad ───────────────────────────

test('[AC-3] persiste ruta, hash y clasificación de cada archivo', async (t) => {
  const caja = await createSandbox(t);
  const m = await construir(await origen(caja));

  assert.equal(m.schema, SCHEMA_MANIFIESTO);
  assert.deepEqual(m.inventario.map((e) => e.path), [
    'cross-review/veredicto.md', 'notas.txt', 'plan.md', 'spec.md',
  ]);
  for (const e of m.inventario) assert.match(e.sha256, /^[0-9a-f]{64}$/);
  assert.deepEqual(
    m.inventario.filter((e) => e.clase === CLASES.A_SALVO).map((e) => e.path),
    ['plan.md', 'spec.md'],
  );
  // Los bytes de cada clase, y su suma: es lo que el ensayo le muestra a quien
  // aprueba, y lo que separa "277 documentos" de "163 MB sin copia".
  assert.equal(m.bytes.total, m.bytes.aSalvo + m.bytes.sinCopia);
  assert.ok(m.bytes.sinCopia > 0);
});

test('[AC-3] los directorios son el cierre de ancestros más los que ya estaban vacíos', async (t) => {
  const caja = await createSandbox(t);
  const m = await construir(await origen(caja));

  // `cross-review` no figura como vacío en el original —tiene un archivo—, pero
  // va a quedar vacío por el propio borrado. Sin el cierre de ancestros, el
  // reintento no encontraría autorización para retirarlo.
  assert.deepEqual(m.directorios.map((d) => d.path), ['cross-review', 'vacio']);
});

test('[AC-3] el digest cubre las siete cosas: cambiar cualquiera lo mueve', async (t) => {
  const caja = await createSandbox(t);
  const base = await construir(await origen(caja));
  const d0 = digestManifiesto(base);
  assert.match(d0, /^[0-9a-f]{64}$/);
  assert.equal(digestManifiesto(await construir(await origen(caja))), d0, 'el digest no es estable');

  const mutaciones = {
    identidad: (m) => { m.identidad = { ...m.identidad, repoId: 'otro-repo' }; },
    alcance: (m) => { m.alcance = { nombre: 'otro' }; },
    inventario: (m) => { m.inventario[0] = { ...m.inventario[0], sha256: 'f'.repeat(64) }; },
    clasificacion: (m) => { m.inventario[0] = { ...m.inventario[0], clase: CLASES.A_SALVO }; },
    directorios: (m) => { m.directorios = m.directorios.slice(1); },
    bytes: (m) => { m.bytes = { ...m.bytes, total: m.bytes.total + 1 }; },
    vault: (m) => { m.vault = { commit: 'b'.repeat(40) }; },
  };
  for (const [que, mutar] of Object.entries(mutaciones)) {
    const copia = JSON.parse(JSON.stringify(base));
    mutar(copia);
    assert.notEqual(digestManifiesto(copia), d0, `el digest ignora ${que}`);
  }
});

test('[AC-3] el manifiesto exige identidad declarada y commit del vault', async (t) => {
  const caja = await createSandbox(t);
  const flowDir = await origen(caja);
  const con = (extra) =>
    construirManifiesto({ fs: new DurableFs(), flowDir, aSalvo: [], identidad: IDENTIDAD, vaultCommit: COMMIT, ...extra });

  await assert.rejects(() => con({ identidad: undefined }), (e) => e.code === 'IDENTIDAD_AUSENTE');
  await assert.rejects(() => con({ identidad: { repoId: 'x' } }), (e) => e.code === 'IDENTIDAD_AUSENTE');
  await assert.rejects(() => con({ vaultCommit: '' }), (e) => e.code === 'COMMIT_AUSENTE');
});

// ── AC-3b · los tipos especiales detienen, nombrando la ruta ─────────────────

test('[AC-3b] un symlink a un archivo detiene, y lo nombra', async (t) => {
  const caja = await createSandbox(t);
  const flowDir = await origen(caja);
  await caja.makeSymlink(path.join(flowDir, 'atajo.md'), path.join(flowDir, 'spec.md'));

  await assert.rejects(() => construir(flowDir), (error) => {
    assert.equal(error.code, 'UNSUPPORTED_SOURCE_ENTRY');
    assert.match(error.message, /symlink/);
    assert.match(error.message, /atajo\.md/);
    return true;
  });
});

test('[AC-3b] un symlink a un directorio de afuera detiene antes de enumerarlo', async (t) => {
  const caja = await createSandbox(t);
  const flowDir = await origen(caja);
  const afuera = await caja.makeTree(path.join(caja.reposDir, 'ajeno'), { 'secreto.md': 'no se toca\n' });
  await caja.makeSymlink(path.join(flowDir, 'salida'), afuera);

  await assert.rejects(() => construir(flowDir), (error) => {
    assert.equal(error.code, 'UNSUPPORTED_SOURCE_ENTRY');
    assert.match(error.message, /salida/);
    return true;
  });
  // Y lo de afuera nunca entró al inventario: si hubiera seguido el enlace, el
  // manifiesto autorizaría destruir un árbol que nadie miró.
  assert.equal(await fs.readFile(path.join(afuera, 'secreto.md'), 'utf8'), 'no se toca\n');
});

test('[AC-3b] un symlink colgado también detiene, en vez de leerse como ausencia', async (t) => {
  const caja = await createSandbox(t);
  const flowDir = await origen(caja);
  await caja.makeSymlink(path.join(flowDir, 'colgado.md'), path.join(flowDir, 'no-existe.md'));

  await assert.rejects(() => construir(flowDir), (error) => {
    assert.equal(error.code, 'UNSUPPORTED_SOURCE_ENTRY');
    assert.match(error.message, /colgado\.md/);
    return true;
  });
});

test('[AC-3b] un FIFO detiene nombrando su tipo', async (t) => {
  const caja = await createSandbox(t);
  const flowDir = await origen(caja);
  const { execFile } = await import('node:child_process');
  const { promisify } = await import('node:util');
  try {
    await promisify(execFile)('mkfifo', [path.join(flowDir, 'tubo')]);
  } catch {
    t.skip('la plataforma no tiene mkfifo');
    return;
  }

  await assert.rejects(() => construir(flowDir), (error) => {
    assert.equal(error.code, 'UNSUPPORTED_SOURCE_ENTRY');
    assert.match(error.message, /FIFO/);
    assert.match(error.message, /tubo/);
    return true;
  });
});

test('[AC-3b] la raíz misma tampoco se sigue si es un enlace', async (t) => {
  const caja = await createSandbox(t);
  const real = await origen(caja);
  const enlace = await caja.makeSymlink(path.join(caja.reposDir, 'atajo-al-flujo'), real);

  await assert.rejects(() => construir(enlace), (error) => {
    assert.ok(['UNSUPPORTED_SOURCE_ENTRY', 'SOURCE_UNAVAILABLE', 'UNSUPPORTED_SOURCE_ROOT'].includes(error.code),
      `código inesperado: ${error.code}`);
    return true;
  });
});
