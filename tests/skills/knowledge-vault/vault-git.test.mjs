/**
 * El vault como repositorio Git propio.
 *
 * Dos cosas que parecen la misma y no lo son. **Que el vault sea un repositorio**
 * y **que sea SU PROPIO repositorio**: si la raíz del vault cae dentro de otro
 * repositorio, `git add` desde ahí stagea contra el de afuera, y el vault termina
 * commiteado dentro del proyecto de alguien. Por eso se compara `--show-toplevel`
 * contra la raíz exacta, y un vault anidado se **rechaza** en vez de inicializarse.
 *
 * El chequeo de árbol sucio corre **antes de comprometer el archivado**: para
 * entonces la recuperación acotada de staging del flujo actual ya barrió lo
 * propio, y si queda un cambio ajeno sin commitear, el commit se lo llevaría puesto.
 *
 * Se prueba contra repositorios reales, no contra un mock: lo que hay que
 * verificar es cómo se comporta `git`, y un mock afirma lo que uno ya creía.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

import {
  anclaEnHead,
  assertVaultClean,
  commitFlow,
  ensureVaultRepo,
  inspectManifestAuthority,
  rutasNoAncladas,
  rutasTrackeadas,
} from '../../../skills/knowledge-vault/scripts/lib/vault-git.mjs';
import { createSandbox } from './helpers/sandbox.mjs';

const ejecutar = promisify(execFile);
const git = (cwd, ...args) => ejecutar('git', ['-C', cwd, ...args]);

/** Los asuntos de la historia, del más nuevo al más viejo. */
async function asuntos(vaultRoot) {
  const { stdout } = await git(vaultRoot, 'log', '--format=%s');
  return stdout.trim().length === 0 ? [] : stdout.trim().split('\n');
}

async function vaultNuevo(t) {
  const caja = await createSandbox(t);
  const vault = path.join(caja.vaultsDir, 'dev-memory');
  await fs.mkdir(vault, { recursive: true });
  return { caja, vault };
}

async function archivo(vault, rel, contenido = 'x\n') {
  const abs = path.join(vault, rel);
  await fs.mkdir(path.dirname(abs), { recursive: true });
  await fs.writeFile(abs, contenido, 'utf8');
  return abs;
}

test('[AC-13] inicializa el vault y su raíz de repositorio es exactamente la del vault', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  const { stdout } = await git(vault, 'rev-parse', '--show-toplevel');
  assert.equal(await fs.realpath(stdout.trim()), await fs.realpath(vault));
});

test('[AC-13] es idempotente: correrlo dos veces no rehace el repositorio', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  await archivo(vault, 'index.md');
  await commitFlow({ vaultRoot: vault, flowId: 'aaa-1', paths: ['index.md'] });
  const antes = await asuntos(vault);
  await ensureVaultRepo(vault);
  // Se compara la historia **entera**, no su tamaño: el conteo absoluto ataba el
  // test a cuántos commits de infraestructura tenga un vault nuevo, y se rompió
  // el día que la siembra del `.gitignore` agregó el suyo sin que la propiedad
  // que este caso afirma —que reinicializar no rehace el repositorio— cambiara.
  assert.deepEqual(await asuntos(vault), antes, 'se perdió la historia');
  assert.ok(antes.includes('archiva aaa-1'), 'el commit del archivado no está');
});

test('[AC-13] un vault dentro de otro repositorio se rechaza, no se inicializa anidado', async (t) => {
  const { caja } = await vaultNuevo(t);
  const contenedor = path.join(caja.reposDir, 'proyecto');
  const anidado = path.join(contenedor, 'vault');
  await fs.mkdir(anidado, { recursive: true });
  await git(contenedor, 'init', '-q').catch(async () => {
    await ejecutar('git', ['init', '-q', contenedor]);
  });
  await assert.rejects(() => ensureVaultRepo(anidado), /raíz|toplevel|anidad/i);
  // Y no dejó un repositorio a medias adentro.
  await assert.rejects(() => fs.stat(path.join(anidado, '.git')));
});

test('[AC-13] con cambios ajenos sin commitear, el chequeo lanza antes de escribir', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  await archivo(vault, 'index.md');
  await commitFlow({ vaultRoot: vault, flowId: 'aaa-1', paths: ['index.md'] });

  await archivo(vault, 'algo-ajeno.md', 'editado a mano\n');
  await assert.rejects(() => assertVaultClean(vault), /sucio|sin commitear|limpio/i);
});

test('un cambio ajeno bajo el mismo ancestro se rechaza', async (t) => {
  // Reconocer lo propio no puede volverla permisiva con lo que cuelga del mismo
  // directorio: ahí vive el residuo de OTROS flujos, ajeno a esta corrida.
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  const propias = ['projects/ai-workflows/sdd/aaa-1', 'projects/ai-workflows/sdd/aaa-1.md'];
  await archivo(vault, 'projects/ai-workflows/sdd/aaa-1/spec.md');
  await archivo(vault, 'projects/ai-workflows/sdd/otro-flujo/spec.md', 'de otro flujo\n');

  await assert.rejects(() => assertVaultClean(vault, propias), /sin commitear/i);
});

test('[AC-13] con el árbol limpio el chequeo pasa', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  await assert.doesNotReject(() => assertVaultClean(vault));
  await archivo(vault, 'index.md');
  await commitFlow({ vaultRoot: vault, flowId: 'aaa-1', paths: ['index.md'] });
  await assert.doesNotReject(() => assertVaultClean(vault));
});

test('[AC-13] el commit stagea sólo las rutas dadas', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  await archivo(vault, 'projects/ai-workflows/sdd/aaa-1/spec.md');
  await archivo(vault, 'projects/ai-workflows/sdd/aaa-1.md');
  await archivo(vault, 'no-deberia-entrar.md');

  await commitFlow({
    vaultRoot: vault,
    flowId: 'aaa-1',
    paths: ['projects/ai-workflows/sdd/aaa-1', 'projects/ai-workflows/sdd/aaa-1.md'],
  });
  const { stdout } = await git(vault, 'show', '--name-only', '--format=', 'HEAD');
  const commiteados = stdout.trim().split('\n').sort();
  assert.deepEqual(commiteados, [
    'projects/ai-workflows/sdd/aaa-1.md',
    'projects/ai-workflows/sdd/aaa-1/spec.md',
  ]);
});

test('un prefijo con tracked y nuevos incorpora ambos al commit', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  const directory = 'projects/ai-workflows/sdd/aaa-1';
  await archivo(vault, `${directory}/spec.md`, 'primera versión\n');
  await commitFlow({ vaultRoot: vault, flowId: 'aaa-1', paths: [directory] });

  await archivo(vault, `${directory}/spec.md`, 'segunda versión\n');
  await archivo(vault, `${directory}/evidencia.json`, '{}\n');
  await commitFlow({ vaultRoot: vault, flowId: 'aaa-1', paths: [directory] });

  const { stdout } = await git(vault, 'show', '--name-only', '--format=', 'HEAD');
  assert.deepEqual(stdout.trim().split('\n').sort(), [
    `${directory}/evidencia.json`,
    `${directory}/spec.md`,
  ]);
});

test('[AC-13] el mensaje del commit nombra el flujo', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  for (const flujo of ['aaa-1', 'cross-model-co-explore-debate-runtime']) {
    await archivo(vault, `projects/p/sdd/${flujo}.md`);
    await commitFlow({ vaultRoot: vault, flowId: flujo, paths: [`projects/p/sdd/${flujo}.md`] });
  }
  const { stdout } = await git(vault, 'log', '--format=%s');
  for (const flujo of ['aaa-1', 'cross-model-co-explore-debate-runtime']) {
    assert.ok(stdout.includes(flujo), `ningún asunto nombra ${flujo}`);
  }
});

test('[AC-13] sin cambios que commitear no se crea un commit vacío', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  await archivo(vault, 'index.md');
  await commitFlow({ vaultRoot: vault, flowId: 'aaa-1', paths: ['index.md'] });
  const antes = await asuntos(vault);
  const r = await commitFlow({ vaultRoot: vault, flowId: 'aaa-1', paths: ['index.md'] });
  assert.equal(r.committed, false);
  assert.deepEqual(await asuntos(vault), antes, 'la segunda llamada agregó un commit');
});

// ── La siembra del `.gitignore` (el vault que se ensucia solo) ────────────────

test('[AC-16] un vault recién creado nace con su .gitignore, ya commiteado', async (t) => {
  const caja = await createSandbox(t);
  const raiz = await caja.makeVault('nuevo');
  await ensureVaultRepo(raiz);

  const contenido = await fs.readFile(path.join(raiz, '.gitignore'), 'utf8');
  assert.match(contenido, /^\.obsidian\/$/m);
  assert.match(contenido, /^\.DS_Store$/m);

  // Commiteado, no suelto: el porqué está en el docstring de `sembrarGitignore`.
  const { stdout } = await git(raiz, 'status', '--porcelain');
  assert.equal(stdout.trim(), '', 'el vault nace sucio por su propio .gitignore');
});

test('[AC-16] lo que Obsidian y macOS dejan ya no ensucia el vault', async (t) => {
  const caja = await createSandbox(t);
  const raiz = await caja.makeVault('nuevo');
  await ensureVaultRepo(raiz);

  // Las dos formas medidas: la configuración de Obsidian y el `.DS_Store` de macOS.
  await fs.mkdir(path.join(raiz, '.obsidian'), { recursive: true });
  await fs.writeFile(path.join(raiz, '.obsidian', 'app.json'), '{}\n', 'utf8');
  await fs.writeFile(path.join(raiz, '.DS_Store'), 'basura\n', 'utf8');
  await fs.mkdir(path.join(raiz, 'projects'), { recursive: true });
  await fs.writeFile(path.join(raiz, 'projects', '.DS_Store'), 'basura\n', 'utf8');

  // Sin la siembra son cuatro cambios ajenos y el archivado frena.
  await assertVaultClean(raiz, []);
});

test('[AC-16] un .gitignore que ya existe no se pisa: es del usuario', async (t) => {
  const caja = await createSandbox(t);
  const raiz = await caja.makeVault('con-ignore');
  const propio = '# el mío\n*.tmp\n';
  await fs.writeFile(path.join(raiz, '.gitignore'), propio, 'utf8');

  await ensureVaultRepo(raiz);

  // El directorio pudo ser un repositorio de notas antes de ser un vault.
  assert.equal(await fs.readFile(path.join(raiz, '.gitignore'), 'utf8'), propio);
});

test('[AC-16] sobre un vault ya inicializado no se siembra nada', async (t) => {
  const caja = await createSandbox(t);
  const raiz = await caja.makeVault('existente');
  await git(raiz, 'init', '-q');
  // Un vault anterior a la siembra: es repositorio y no tiene `.gitignore`.
  await ensureVaultRepo(raiz);

  // Reponerlo pisaría a quien lo borró, y metería un commit en una historia que
  // es el registro de archivados del vault.
  await assert.rejects(() => fs.access(path.join(raiz, '.gitignore')));
});

test('[KV-SEL AC-8] Git reporta Unicode, faltante, sucio, ignorado y destino de rename NUL', async (t) => {
  const { caja, vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  await archivo(vault, '.gitignore', '.obsidian/\n.DS_Store\ndocs/ignored.md\n');
  for (const relative of ['docs/café.md', 'docs/dirty.md', 'docs/origen.md']) {
    await archivo(vault, relative, `${relative}\n`);
  }
  await commitFlow({
    vaultRoot: vault,
    flowId: 'git-fixture',
    paths: ['.gitignore', 'docs/café.md', 'docs/dirty.md', 'docs/origen.md'],
  });

  await archivo(vault, 'docs/dirty.md', 'modificado\n');
  await archivo(vault, 'docs/ignored.md', 'ignorado\n');
  await git(vault, 'mv', 'docs/origen.md', 'docs/destino.md');

  const routes = [
    'docs/café.md',
    'docs/missing.md',
    'docs/dirty.md',
    'docs/ignored.md',
    'docs/destino.md',
    'docs/origen.md',
  ];
  assert.deepEqual(await rutasNoAncladas(vault, routes, { scanPaths: ['docs'] }), {
    missing: ['docs/missing.md', 'docs/ignored.md', 'docs/destino.md'],
    dirty: ['docs/dirty.md', 'docs/destino.md'],
    ignored: ['docs/ignored.md'],
  });

  const unborn = caja.path('vaults', 'sin-head');
  await fs.mkdir(unborn, { recursive: true });
  await git(unborn, 'init', '-q');
  assert.deepEqual(await rutasNoAncladas(unborn, ['uno.md', 'dos.md'], {
    scanPaths: ['uno.md', 'dos.md'],
  }), {
    missing: ['uno.md', 'dos.md'],
    dirty: [],
    ignored: [],
  });
});

test('[KV-SEL AC-9] Git detecta destino ignorado antes de materializarlo', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  await archivo(vault, '.gitignore', '.obsidian/\n.DS_Store\n.kv/retiros/\n');
  await commitFlow({ vaultRoot: vault, flowId: 'ignore-fixture', paths: ['.gitignore'] });

  const target = '.kv/retiros/repo/flow.json';
  assert.deepEqual(await rutasNoAncladas(vault, [target], { scanPaths: ['.kv/retiros'] }), {
    missing: [target],
    dirty: [],
    ignored: [target],
  });
});

test('[KV-SEL AC-21] inspector de manifiesto exige ruta exacta limpia y anclada', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  const relative = '.kv/retiros/repo/flow.json';
  const manifest = path.join(vault, ...relative.split('/'));

  assert.deepEqual(await inspectManifestAuthority(vault, manifest), {
    exists: false,
    anchored: false,
    dirty: false,
    ignored: false,
  });

  await archivo(vault, relative, '{}\n');
  assert.deepEqual(await inspectManifestAuthority(vault, manifest), {
    exists: true,
    anchored: false,
    dirty: true,
    ignored: false,
  });

  await commitFlow({ vaultRoot: vault, flowId: 'flow', paths: [relative] });
  assert.deepEqual(await inspectManifestAuthority(vault, manifest), {
    exists: true,
    anchored: true,
    dirty: false,
    ignored: false,
  });

  await fs.rm(manifest);
  assert.deepEqual(await inspectManifestAuthority(vault, manifest), {
    exists: true,
    anchored: false,
    dirty: true,
    ignored: false,
  });
  await git(vault, 'checkout', '--', relative);

  await archivo(vault, relative, '{"dirty":true}\n');
  assert.equal((await inspectManifestAuthority(vault, manifest)).dirty, true);
  await git(vault, 'checkout', '--', relative);

  await fs.appendFile(path.join(vault, '.gitignore'), `${relative}\n`, 'utf8');
  await commitFlow({ vaultRoot: vault, flowId: 'ignore-manifest', paths: ['.gitignore'] });
  assert.deepEqual(await inspectManifestAuthority(vault, manifest), {
    exists: true,
    anchored: true,
    dirty: false,
    ignored: true,
  });
});


test('una ruta trackeada y limpia sigue anclada aunque un ignore posterior la cubra', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  const route = 'projects/demo/sdd/flow/runs/r1.jsonl';
  await archivo(vault, route, '{"run":1}\n');
  await commitFlow({ vaultRoot: vault, flowId: 'flow', paths: [route] });
  await fs.appendFile(path.join(vault, '.gitignore'), 'runs/\n', 'utf8');
  await commitFlow({ vaultRoot: vault, flowId: 'ignore', paths: ['.gitignore'] });

  assert.deepEqual(await rutasNoAncladas(vault, [route], { scanPaths: [route] }), {
    missing: [], dirty: [], ignored: [],
  });
  assert.equal(await anclaEnHead(vault, [route], { scanPaths: [route] }), true);
  assert.equal((await git(vault, 'status', '--porcelain')).stdout.trim(), '');
});


test('el anclaje consulta un prefijo acotado aun con miles de rutas exactas', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  const prefix = 'projects/demo/sdd/flow';
  const routes = Array.from({ length: 15000 }, (_, index) =>
    `${prefix}/runs/${String(index).padStart(5, '0')}-${'x'.repeat(150)}.jsonl`);
  await assert.rejects(
    () => rutasNoAncladas(vault, routes),
    (error) => error?.code === 'INVALID_SCAN_PATHS',
  );
  const diagnostics = await rutasNoAncladas(vault, routes, { scanPaths: [prefix] });
  assert.equal(diagnostics.missing.length, routes.length);
  assert.equal(diagnostics.missing[0], routes[0]);
  assert.equal(diagnostics.missing.at(-1), routes.at(-1));
  assert.deepEqual(diagnostics.dirty, []);
  assert.deepEqual(diagnostics.ignored, []);
});

test('[KV-STAGING] rutasTrackeadas distingue HEAD, sólo-índice y no trackeada', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  await archivo(vault, 'projects/p/sdd/en-head/spec.md');
  await commitFlow({ vaultRoot: vault, flowId: 'en-head', paths: ['projects/p/sdd/en-head'] });
  await archivo(vault, 'projects/p/sdd/solo-indice/spec.md');
  await git(vault, 'add', '--', 'projects/p/sdd/solo-indice');
  await archivo(vault, 'projects/p/sdd/no-trackeada/spec.md');

  assert.deepEqual(
    await rutasTrackeadas(vault, [
      'projects/p/sdd/en-head',
      'projects/p/sdd/solo-indice',
      'projects/p/sdd/no-trackeada',
    ]),
    ['projects/p/sdd/en-head', 'projects/p/sdd/solo-indice'],
  );
});

test('omitir scanPaths falla antes de consultar Git', async (t) => {
  const { vault } = await vaultNuevo(t);
  await ensureVaultRepo(vault);
  await assert.rejects(
    () => rutasNoAncladas(vault, ['index.md']),
    (error) => error?.code === 'INVALID_SCAN_PATHS',
  );
  assert.deepEqual(await rutasNoAncladas(vault, ['index.md'], { scanPaths: ['index.md'] }), {
    missing: ['index.md'], dirty: [], ignored: [],
  });
});
