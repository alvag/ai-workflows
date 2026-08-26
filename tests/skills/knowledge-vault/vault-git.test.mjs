/**
 * El vault como repositorio Git propio.
 *
 * Dos cosas que parecen la misma y no lo son. **Que el vault sea un repositorio**
 * y **que sea SU PROPIO repositorio**: si la raíz del vault cae dentro de otro
 * repositorio, `git add` desde ahí stagea contra el de afuera, y el vault termina
 * commiteado dentro del proyecto de alguien. Por eso se compara `--show-toplevel`
 * contra la raíz exacta, y un vault anidado se **rechaza** en vez de inicializarse.
 *
 * El chequeo de árbol sucio corre **antes de escribir nada**: si ya hay cambios
 * ajenos sin commitear, el commit del archivado se los llevaría puestos.
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
  assertVaultClean,
  commitFlow,
  ensureVaultRepo,
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
