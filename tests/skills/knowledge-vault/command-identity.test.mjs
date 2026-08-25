/**
 * El verbo `identity` (AC-13).
 *
 * Lo que se prueba acá es sobre todo lo que **se niega a hacer**. Declarar una
 * identidad es barato; lo caro es declararla mal, porque la ruta dentro del vault
 * sale de ella y un identificador equivocado manda a copiar y a destruir a sitios
 * distintos sin que nada se vea raro hasta que ya no hay origen.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

import { DurableFs, Recorder } from '../../../skills/knowledge-vault/scripts/lib/durable-fs.mjs';
import { archiveCommand } from '../../../skills/knowledge-vault/scripts/lib/commands/archive.mjs';
import { identityCommand, ESTADOS } from '../../../skills/knowledge-vault/scripts/lib/commands/identity.mjs';
import { retireCommand } from '../../../skills/knowledge-vault/scripts/lib/commands/retire.mjs';
import { createSandbox } from './helpers/sandbox.mjs';
import { snapshotTree } from './helpers/tree-snapshot.mjs';

const git = (cwd, ...args) => promisify(execFile)('git', ['-C', cwd, ...args]);

/** Un repositorio de verdad —con remoto y un commit— y un vault vacío. */
async function escena(t, { remoto = 'git@github.com:acme/api.git', conCommit = true, nombre = 'proyecto' } = {}) {
  const caja = await createSandbox(t);
  const repoRoot = await caja.makeTree(path.join(caja.reposDir, nombre), {});
  await git(repoRoot, 'init', '-q');
  if (remoto !== null) await git(repoRoot, 'remote', 'add', 'origin', remoto);
  if (conCommit) {
    // El contenido lleva el nombre del repositorio a propósito. Con dos árboles
    // idénticos, mismo autor, mismo mensaje y el mismo segundo, Git produce el
    // **mismo** commit raíz — y entonces dos repositorios distintos comparten su
    // señal de identidad y el fixture deja de probar lo que dice probar.
    await fs.writeFile(path.join(repoRoot, 'README.md'), `# ${nombre}\n`, 'utf8');
    await git(repoRoot, 'add', '-A');
    await git(repoRoot, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'inicial');
  }
  const vault = await caja.makeVault('dev-memory');
  const raiz = path.join(repoRoot, '.plans', 'archived');
  await fs.mkdir(raiz, { recursive: true });
  return { caja, repoRoot, vault, raiz };
}

const correr = (e, flags, extra = {}) =>
  identityCommand({
    fs: extra.fs ?? new DurableFs(),
    cwd: e.repoRoot,
    flags: { 'vault-root': e.vault, ...flags },
  });

// ── Proponer: leer el repositorio, y nada más ────────────────────────────────

test('[AC-13] la propuesta sale del remoto y no escribe un solo byte', async (t) => {
  const e = await escena(t);
  const antes = await snapshotTree(e.vault);
  const grabador = new Recorder();

  const r = await correr(e, { propose: true }, { fs: new DurableFs({ recorder: grabador }) });

  assert.equal(r.status, ESTADOS.PROPUESTA);
  assert.equal(r.propuesta, 'api');
  assert.equal(r.origen, 'remoto');
  const MUTAN = new Set(['mkdir', 'writeFile', 'writeFileAtomic', 'rename', 'unlink', 'fsyncDir']);
  assert.deepEqual(grabador.entries.filter((o) => MUTAN.has(o.op)).map((o) => o.label), []);
  assert.deepEqual(await snapshotTree(e.vault), antes);
});

test('[AC-13] sin remoto la propuesta cae al nombre del directorio', async (t) => {
  const e = await escena(t, { remoto: null, nombre: 'Mi_Repo' });
  const r = await correr(e, { propose: true });
  assert.deepEqual(
    { propuesta: r.propuesta, origen: r.origen },
    { propuesta: 'mi-repo', origen: 'directorio' },
  );
});

test('[AC-13] sin remoto y sin commits se detiene: el directorio no es una señal', async (t) => {
  const e = await escena(t, { remoto: null, conCommit: false });
  await assert.rejects(() => correr(e, { propose: true }), (error) => {
    assert.equal(error.code, 'AMBIGUOUS_IDENTITY');
    assert.match(error.message, /no es una señal/);
    return true;
  });
});

// ── Declarar: el otro lado del gate ──────────────────────────────────────────

test('[AC-13] declarar escribe el registro y lo commitea en el vault', async (t) => {
  const e = await escena(t);
  const r = await correr(e, { declare: 'api' });

  assert.equal(r.status, ESTADOS.DECLARADA);
  const registro = await fs.readFile(path.join(e.vault, '.kv', 'identidades.tsv'), 'utf8');
  const [id, remoto, commitRaiz] = registro.trim().split('\t');
  assert.equal(id, 'api');
  assert.equal(remoto, 'git@github.com:acme/api.git');
  assert.match(commitRaiz, /^[0-9a-f]{40}$/);

  // Versionado, o no viaja entre clones — que es la razón entera de que la sede
  // sea el vault y no la configuración del proyecto.
  const { stdout } = await git(e.vault, 'log', '--format=%s');
  assert.match(stdout, /declara la identidad de api/);
  assert.equal((await git(e.vault, 'status', '--porcelain')).stdout.trim(), '');
});

test('[AC-13] declarar dos veces lo mismo es un no-op, no un error', async (t) => {
  const e = await escena(t);
  await correr(e, { declare: 'api' });
  const antes = await snapshotTree(e.vault);

  const r = await correr(e, { declare: 'api' });
  assert.equal(r.status, ESTADOS.YA_DECLARADA);
  assert.deepEqual(await snapshotTree(e.vault), antes, 'la segunda declaración movió algo');
});

test('[AC-13] declarar un segundo identificador para el mismo repositorio se detiene', async (t) => {
  const e = await escena(t);
  await correr(e, { declare: 'api' });

  await assert.rejects(() => correr(e, { declare: 'api-nuevo' }), (error) => {
    assert.equal(error.code, 'AMBIGUOUS_IDENTITY');
    assert.match(error.message, /ya está declarado como api/);
    return true;
  });
});

test('[AC-13] declarar un identificador que ya usa otro repositorio se detiene', async (t) => {
  const e = await escena(t);
  await correr(e, { declare: 'api' });
  // Otro repositorio, mismo vault, y quiere el mismo identificador: compartirían
  // ruta, que es el problema entero.
  const otro = await escena(t, { remoto: 'https://gitlab.com/otra/api.git', nombre: 'otro' });
  await assert.rejects(
    () => identityCommand({ fs: new DurableFs(), cwd: otro.repoRoot, flags: { 'vault-root': e.vault, declare: 'api' } }),
    (error) => {
      assert.equal(error.code, 'AMBIGUOUS_IDENTITY');
      assert.match(error.message, /ya identifica a otro repositorio/);
      return true;
    },
  );
});

test('[AC-13] las dos banderas juntas son USAGE: entre ellas va una persona', async (t) => {
  const e = await escena(t);
  await assert.rejects(() => correr(e, { propose: true, declare: 'api' }), (error) => {
    assert.equal(error.code, 'USAGE');
    assert.match(error.message, /excluyentes/);
    return true;
  });
  await assert.rejects(() => correr(e, {}), (error) => {
    assert.equal(error.code, 'USAGE');
    return true;
  });
});

// ── La unificación: copiar y borrar tienen que mirar el mismo sitio ──────────

test('[AC-13] el verbo que copia usa la identidad declarada, no el nombre del directorio', async (t) => {
  const e = await escena(t, { nombre: 'proyecto' });
  await correr(e, { declare: 'api-pagos' });
  await e.caja.makeTree(path.join(e.raiz, 'abc-1'), { 'spec.md': '# spec\n' });

  await archiveCommand({
    fs: new DurableFs(),
    flags: { from: path.join(e.raiz, 'abc-1'), 'vault-root': e.vault, summary: 'un resumen' },
  });

  // Sin la unificación, el derivado del directorio —`proyecto`— y el declarado
  // —`api-pagos`— mandan a dos rutas distintas, y **nada** se puede retirar
  // nunca porque la sonda mira donde el archivado no escribió.
  assert.deepEqual((await fs.readdir(path.join(e.vault, 'projects'))).sort(), ['api-pagos', 'index.md']);
});

test('[AC-13] copiar y retirar coinciden: la cadena entera cierra', async (t) => {
  const e = await escena(t, { nombre: 'proyecto' });
  await correr(e, { declare: 'api-pagos' });
  await e.caja.makeTree(path.join(e.raiz, 'abc-1'), { 'spec.md': '# spec\n', 'plan.md': '# plan\n' });
  await archiveCommand({
    fs: new DurableFs(),
    flags: { from: path.join(e.raiz, 'abc-1'), 'vault-root': e.vault, summary: 'un resumen' },
  });

  const r = await retireCommand({
    fs: new DurableFs(),
    flags: { root: e.raiz, 'vault-root': e.vault, 'dry-run': true },
  });
  assert.equal(r.informe.repoId, 'api-pagos');
  assert.deepEqual(r.informe.flujos.map((f) => [f.flowId, f.aSalvo]), [['abc-1', true]]);
});

test('[AC-13] declarar distinto del derivado con material ya archivado se detiene', async (t) => {
  const e = await escena(t, { nombre: 'proyecto' });
  // Se archivó primero, sin identidad: quedó bajo el derivado `proyecto`.
  await e.caja.makeTree(path.join(e.raiz, 'abc-1'), { 'spec.md': '# spec\n' });
  await archiveCommand({
    fs: new DurableFs(),
    flags: { from: path.join(e.raiz, 'abc-1'), 'vault-root': e.vault, summary: 'un resumen' },
  });
  assert.ok((await fs.readdir(path.join(e.vault, 'projects'))).includes('proyecto'));

  // Declarar otro identificador dejaría eso en una ruta que nadie vuelve a mirar.
  await assert.rejects(() => correr(e, { declare: 'api-pagos' }), (error) => {
    assert.equal(error.code, 'AMBIGUOUS_IDENTITY');
    assert.match(error.message, /ya tiene material bajo "proyecto"/);
    return true;
  });
  // Y declarar el derivado sí se puede: es el camino de salida.
  assert.equal((await correr(e, { declare: 'proyecto' })).status, ESTADOS.DECLARADA);
});
