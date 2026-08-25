/**
 * El retiro, extremo a extremo (AC-20).
 *
 * Es la única fila del contrato que mide **el problema** en vez de sus partes.
 * Con todas las demás en verde, un verbo que no libera un solo byte pasaría el
 * contrato entero: cada fila comprueba una propiedad —que la sonda no escriba,
 * que el manifiesto sea autoridad, que la tabla clasifique— y ninguna comprueba
 * que al final haya menos bytes en el origen que al principio.
 *
 * Acá se mide eso: el origen antes y después, en bytes y en archivos.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

import { DurableFs, Recorder } from '../../../skills/knowledge-vault/scripts/lib/durable-fs.mjs';
import { runVaultTransaction } from '../../../skills/knowledge-vault/scripts/lib/engine-vault.mjs';
import { retireCommand, ESTADOS } from '../../../skills/knowledge-vault/scripts/lib/commands/retire.mjs';
import { serializarRegistroIdentidades } from '../../../skills/knowledge-vault/scripts/lib/identity.mjs';
import { rutaDelManifiesto } from '../../../skills/knowledge-vault/scripts/lib/retire-execute.mjs';
import { writeIdentitiesFile } from '../../../skills/knowledge-vault/scripts/lib/vault-store.mjs';
import { createSandbox } from './helpers/sandbox.mjs';
import { snapshotTree } from './helpers/tree-snapshot.mjs';

const git = (cwd, ...args) => promisify(execFile)('git', ['-C', cwd, ...args]);
const REPO_ID = 'api-pagos';

const PLAN = [
  '---', 'id: abc-1', 'branch: feature/abc-1', 'status: done',
  'created_at: 2026-03-04T12:00:00-03:00', '---', '', '# Plan', '',
].join('\n');

/** Bytes y archivos que quedan bajo una raíz. La medida del problema. */
async function medir(raiz) {
  let bytes = 0;
  let archivos = 0;
  const recorrer = async (dir) => {
    for (const e of await fs.readdir(dir, { withFileTypes: true }).catch(() => [])) {
      const abs = path.join(dir, e.name);
      if (e.isDirectory()) { await recorrer(abs); continue; }
      bytes += (await fs.stat(abs)).size;
      archivos += 1;
    }
  };
  await recorrer(raiz);
  return { bytes, archivos };
}

/** Un árbol de prueba con su vault, dos flujos archivados y la identidad declarada. */
async function arbol(t, { flujos = ['abc-1', 'abc-2'] } = {}) {
  const caja = await createSandbox(t);
  const repoRoot = await caja.makeRepo('proyecto');
  await git(repoRoot, 'init', '-q');
  await git(repoRoot, 'remote', 'add', 'origin', 'git@github.com:acme/api.git');
  const raiz = path.join(repoRoot, '.plans', 'archived');
  await fs.mkdir(raiz, { recursive: true });
  const vault = await caja.makeVault('dev-memory');

  for (const flowId of flujos) {
    const dir = await caja.makeTree(path.join(raiz, flowId), {
      'spec.md': `# ${flowId}\n\n${'criterio '.repeat(40)}\n`,
      'plan.md': PLAN,
      'notas.txt': `${'andamiaje '.repeat(80)}\n`,
      'cross-review/veredicto.md': `${'veredicto '.repeat(60)}\n`,
    });
    await runVaultTransaction({
      fs: new DurableFs(), vaultRoot: vault, repoSlug: REPO_ID, flowId, flowDir: dir,
      summary: `resumen de ${flowId}`,
    });
  }
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
  retireCommand({ fs: extra.fs ?? new DurableFs(), flags: { root: e.raiz, 'vault-root': e.vault, ...flags } });

/** Ensayo + retiro real con el digest del ensayo, que es el camino de verdad. */
async function retiroCompleto(e, extra = {}) {
  const { informe } = await correr(e, { 'dry-run': true });
  return correr(e, { 'approve-digest': informe.digest }, extra);
}

test('[AC-20-e2e] el origen se libera de verdad: menos bytes y menos archivos', async (t) => {
  const e = await arbol(t);
  const antes = await medir(e.raiz);
  assert.ok(antes.bytes > 0 && antes.archivos === 8, `el árbol de prueba midió ${JSON.stringify(antes)}`);

  const r = await retiroCompleto(e);
  assert.equal(r.status, ESTADOS.BATCH_OK);

  const despues = await medir(e.raiz);
  assert.deepEqual(despues, { bytes: 0, archivos: 0 }, 'el origen no se liberó');
  assert.ok(despues.bytes < antes.bytes, 'no se liberó un solo byte');
  assert.deepEqual(await fs.readdir(e.raiz), [], 'quedó algo en la raíz');
});

test('[AC-20-e2e] lo copiable sobrevive exacto y el manifiesto queda en HEAD', async (t) => {
  const e = await arbol(t);
  const frontera = (flowId) => path.join(e.vault, 'projects', REPO_ID, 'sdd', flowId);
  const antes = new Map();
  for (const flowId of e.flujos) antes.set(flowId, await snapshotTree(frontera(flowId)));

  await retiroCompleto(e);

  for (const flowId of e.flujos) {
    // Byte a byte: el retiro destruye el origen y no toca la copia.
    assert.deepEqual(await snapshotTree(frontera(flowId)), antes.get(flowId), `el vault perdió ${flowId}`);

    // Y el manifiesto está **en HEAD**, no sólo escrito: es lo que lo vuelve
    // autorización durable y registro del retiro a la vez.
    const rel = path.relative(e.vault, rutaDelManifiesto(e.vault, REPO_ID, flowId));
    const { stdout } = await git(e.vault, 'ls-tree', '-r', '--name-only', 'HEAD', '--', rel);
    assert.equal(stdout.trim(), rel, `el manifiesto de ${flowId} no está en HEAD`);
  }
});

test('[AC-20-e2e] una caída en cada transición termina en un reintento que cierra', async (t) => {
  // Primero se enumeran los checkpoints **reales** de una corrida completa, en
  // vez de listarlos a mano: una lista escrita a mano envejece con el motor.
  const base = await arbol(t, { flujos: ['abc-1'] });
  const grabador = new Recorder();
  await retiroCompleto(base, { fs: new DurableFs({ recorder: grabador }) });
  const transiciones = grabador.entries
    .filter((o) => o.op === 'checkpoint' && o.label.startsWith('retire.'))
    .map((o) => o.label);
  assert.ok(transiciones.length >= 4, `se esperaban varias transiciones y hubo ${transiciones.length}`);

  for (const transicion of transiciones) {
    const e = await arbol(t, { flujos: ['abc-1'] });
    await retiroCompleto(e, { fs: new DurableFs({ crashAt: transicion }) }).catch(() => {});

    // El reintento tiene que **cerrar**, sea cual sea el punto de la caída: o
    // deshaciendo un reclamo sin autorizar, o terminando una destrucción ya
    // autorizada. Lo que no puede es quedarse a mitad para siempre.
    const r = await retiroCompleto(e);
    assert.equal(r.status, ESTADOS.BATCH_OK, `caída en ${transicion}: el reintento no cerró`);
    const quedan = (await fs.readdir(e.raiz)).sort();
    assert.ok(
      quedan.length === 0 || quedan.every((n) => !n.startsWith('.kv-retirando-')),
      `caída en ${transicion}: quedó un remanente colgado (${quedan.join(', ')})`,
    );
  }
});

// ── Los tres mutantes que el contrato tiene que rechazar ─────────────────────

test('[AC-20-e2e] el verbo que no borra nada no pasa', async (t) => {
  const e = await arbol(t);
  const antes = await medir(e.raiz);
  // El mutante: acepta todo y devuelve el estado feliz sin tocar un byte. Es el
  // que sobrevive a **todas** las demás filas del contrato.
  const noBorra = async ({ flujo }) => ({ flowId: flujo.flowId, estado: 'RETIRADO' });

  const { informe } = await correr(e, { 'dry-run': true });
  const r = await retireCommand({
    fs: new DurableFs(),
    flags: { root: e.raiz, 'vault-root': e.vault, 'approve-digest': informe.digest },
    ejecutor: noBorra,
  });

  assert.equal(r.status, ESTADOS.BATCH_OK, 'el mutante ni siquiera llega a reportar éxito');
  // Y sin embargo el origen está intacto. Esta es la única comprobación de todo
  // el contrato que lo distingue del verbo real.
  assert.deepEqual(await medir(e.raiz), antes, 'el mutante borró algo, y no debía');
  assert.notDeepEqual(await medir(e.raiz), { bytes: 0, archivos: 0 });
});

test('[AC-20-e2e] el que recomputa su propio digest en vez de exigir el aprobado no pasa', async (t) => {
  const e = await arbol(t);
  const antes = await medir(e.raiz);

  // El real: el digest llega por argumento y se compara. Un digest ajeno —el de
  // otro alcance, que es lo que produciría recomputarlo sobre otro árbol— no
  // autoriza nada.
  const otro = await arbol(t, { flujos: ['abc-1'] });
  const { informe: ajeno } = await correr(otro, { 'dry-run': true });

  await assert.rejects(() => correr(e, { 'approve-digest': ajeno.digest }), (error) => {
    assert.equal(error.code, 'PRECONDITION_NOT_MET');
    return true;
  });
  assert.deepEqual(await medir(e.raiz), antes);
});

test('[AC-20-e2e] el que enumera lo presente en vez de leer el manifiesto no pasa', async (t) => {
  const e = await arbol(t, { flujos: ['abc-1'] });
  const { informe } = await correr(e, { 'dry-run': true });
  // Se corta en medio del borrado: queda un remanente parcial.
  await correr(e, { 'approve-digest': informe.digest }, { fs: new DurableFs({ crashAt: 'retire.destruir.archivo' }) })
    .catch(() => {});
  const remanente = path.join(e.raiz, '.kv-retirando-abc-1');
  assert.ok((await fs.lstat(remanente)).isDirectory());

  // Aparece un archivo que nadie autorizó. Quien enumera lo presente lo
  // destruiría; quien lee el manifiesto se niega y no toca nada.
  await fs.writeFile(path.join(remanente, 'de-otro.md'), 'material ajeno\n', 'utf8');
  const antes = await snapshotTree(remanente);
  const segundo = await correr(e, { 'dry-run': true });

  const r = await correr(e, { 'approve-digest': segundo.informe.digest });
  assert.equal(r.status, ESTADOS.BATCH_FAILED);
  assert.deepEqual(await snapshotTree(remanente), antes, 'se destruyó lo que nadie autorizó');
  assert.equal(await fs.readFile(path.join(remanente, 'de-otro.md'), 'utf8'), 'material ajeno\n');
});
