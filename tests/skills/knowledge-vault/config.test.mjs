/**
 * La matriz de rutas de AC-15.
 *
 * El criterio ingenuo —"ninguna ruta se solapa con otra"— **bloquea el archivado
 * entero**: el directorio de un flujo vive dentro del repositorio por
 * construcción, así que exigir que no se solapen prohíbe el caso normal. Lo que
 * hay que exigir es más fino y son dos cosas distintas:
 *
 *   · el **vault** es disjunto del repositorio y de la raíz de archivados
 *     —si viviera adentro, archivar se copiaría a sí mismo—;
 *   · el **flujo** es hijo **directo** de la raíz de archivados.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';

import {
  assertObjetivoDestructivo,
  assertPathMatrix,
} from '../../../skills/knowledge-vault/scripts/lib/config.mjs';
import { createSandbox } from './helpers/sandbox.mjs';

/** Arma un árbol realista y devuelve sus rutas ya creadas en disco. */
async function escenario(t, { vaultDentroDe = null } = {}) {
  const caja = await createSandbox(t);
  const repoRoot = path.join(caja.reposDir, 'proyecto');
  const archivedRoot = path.join(repoRoot, '.plans', 'archived');
  const flowDir = path.join(archivedRoot, 'un-flujo');
  const vaultRoot =
    vaultDentroDe === 'repo' ? path.join(repoRoot, 'vault')
    : vaultDentroDe === 'archivados' ? path.join(archivedRoot, 'vault')
    : path.join(caja.vaultsDir, 'dev-memory');
  for (const d of [flowDir, vaultRoot]) await fs.mkdir(d, { recursive: true });
  return { caja, repoRoot, archivedRoot, flowDir, vaultRoot };
}

test('[AC-15] acepta el caso normal: el flujo vive dentro del repositorio', async (t) => {
  const e = await escenario(t);
  // Sin esta aceptación la skill no puede archivar nada: `.plans/<id>` está
  // dentro del repositorio siempre, y una regla de "sin solapamiento" lo veta.
  await assert.doesNotReject(() => assertPathMatrix(e));
});

test('[AC-15] rechaza un vault dentro del repositorio', async (t) => {
  const e = await escenario(t, { vaultDentroDe: 'repo' });
  await assert.rejects(() => assertPathMatrix(e), /disjunto|repositorio/i);
});

test('[AC-15] rechaza un vault dentro de la raíz de archivados', async (t) => {
  const e = await escenario(t, { vaultDentroDe: 'archivados' });
  await assert.rejects(() => assertPathMatrix(e), /disjunto|archivad/i);
});

test('[AC-15] rechaza un repositorio dentro del vault: disjunto va en las dos direcciones', async (t) => {
  const e = await escenario(t);
  const repoAdentro = path.join(e.vaultRoot, 'proyecto');
  const archivados = path.join(repoAdentro, '.plans', 'archived');
  await fs.mkdir(path.join(archivados, 'un-flujo'), { recursive: true });
  await assert.rejects(
    () => assertPathMatrix({ ...e, repoRoot: repoAdentro, archivedRoot: archivados,
                             flowDir: path.join(archivados, 'un-flujo') }),
    /disjunto/i,
  );
});

test('[AC-15] rechaza un flujo que es nieto y no hijo directo de archivados', async (t) => {
  const e = await escenario(t);
  const nieto = path.join(e.archivedRoot, 'un-flujo', 'adentro');
  await fs.mkdir(nieto, { recursive: true });
  await assert.rejects(() => assertPathMatrix({ ...e, flowDir: nieto }), /hijo directo/i);
});

test('[AC-15] rechaza un flujo que no cuelga de la raíz de archivados', async (t) => {
  const e = await escenario(t);
  const afuera = path.join(e.repoRoot, '.plans', 'en-curso');
  await fs.mkdir(afuera, { recursive: true });
  await assert.rejects(() => assertPathMatrix({ ...e, flowDir: afuera }), /hijo directo/i);
});

test('[AC-15] resuelve enlaces simbólicos antes de comparar', async (t) => {
  const e = await escenario(t);
  // Un vault que es un enlace al repositorio NO es disjunto, por más que sus
  // rutas textuales no compartan un solo prefijo.
  const enlace = path.join(e.caja.vaultsDir, 'enlace-al-repo');
  await fs.symlink(e.repoRoot, enlace, 'dir');
  await assert.rejects(() => assertPathMatrix({ ...e, vaultRoot: enlace }), /disjunto/i);
});

test('[AC-15] la raíz de archivados no tiene por qué llamarse archived', async (t) => {
  const e = await escenario(t);
  const otra = path.join(e.repoRoot, 'historico');
  const flujo = path.join(otra, 'un-flujo');
  await fs.mkdir(flujo, { recursive: true });
  await assert.doesNotReject(() => assertPathMatrix({ ...e, archivedRoot: otra, flowDir: flujo }));
});

// ── La matriz de un objetivo destructivo (AC-9) ───────────────────────────────
//
// Acá lo que se prueba no es que acepte lo correcto: es que **rechace**. Una
// matriz destructiva que no puede ponerse roja autoriza cualquier ruta, y el
// modo de fallar más barato —derivar la raíz del propio objetivo— la deja
// exactamente en ese estado sin que nada se vea distinto.

/** Un árbol con la forma real: repo, archivados, un flujo y un vault aparte. */
async function destructivo(t) {
  const caja = await createSandbox(t);
  const repoRoot = await caja.makeRepo('proyecto');
  const raizDeclarada = path.join(repoRoot, '.plans', 'archived');
  const objetivo = path.join(raizDeclarada, 'un-flujo');
  await fs.mkdir(objetivo, { recursive: true });
  await fs.writeFile(path.join(objetivo, 'spec.md'), '# spec\n', 'utf8');
  const vaultRoot = await caja.makeVault('dev-memory');
  return { caja, objetivo, raizDeclarada, vaultRoot, repoRoot };
}

const rechaza = (fn, fragmento) =>
  assert.rejects(fn, (error) => {
    assert.equal(error.code, 'CONFIG_INVALID');
    assert.match(error.message, fragmento);
    return true;
  });

test('[AC-9] un objetivo bien formado pasa, y la raíz llega por su propio parámetro', async (t) => {
  const e = await destructivo(t);
  const r = await assertObjetivoDestructivo(e);
  assert.equal(path.basename(r.objetivo), 'un-flujo');
  // El control que importa: si la raíz se derivara del objetivo, este caso —una
  // raíz declarada que NO es el padre del objetivo— pasaría igual.
  const otraRaiz = path.join(e.repoRoot, 'otra-raiz');
  await fs.mkdir(otraRaiz, { recursive: true });
  await rechaza(
    () => assertObjetivoDestructivo({ ...e, raizDeclarada: otraRaiz }),
    /no es hijo directo de la raíz declarada/,
  );
});

test('[AC-9] la raíz de archivados, el repositorio y un nieto se rechazan', async (t) => {
  const e = await destructivo(t);
  await rechaza(
    () => assertObjetivoDestructivo({ ...e, objetivo: e.raizDeclarada }),
    /la propia raíz de archivados/,
  );
  await rechaza(
    () => assertObjetivoDestructivo({ ...e, objetivo: e.repoRoot, raizDeclarada: e.repoRoot }),
    /raíz del repositorio/,
  );
  const nieto = path.join(e.objetivo, 'adentro');
  await fs.mkdir(nieto, { recursive: true });
  await rechaza(
    () => assertObjetivoDestructivo({ ...e, objetivo: nieto }),
    /no es hijo directo de la raíz declarada/,
  );
});

test('[AC-9] un clon adentro del objetivo lo rechaza', async (t) => {
  const e = await destructivo(t);
  await fs.mkdir(path.join(e.objetivo, 'dependencia', '.git'), { recursive: true });
  await rechaza(() => assertObjetivoDestructivo(e), /repositorio Git \(clon\)/);
});

test('[AC-9] un árbol de trabajo enlazado adentro del objetivo lo rechaza', async (t) => {
  const e = await destructivo(t);
  // Es la forma que un chequeo por directorio no ve: acá `.git` es un archivo.
  const sub = path.join(e.objetivo, 'submodulo');
  await fs.mkdir(sub, { recursive: true });
  await fs.writeFile(path.join(sub, '.git'), 'gitdir: ../../.git/modules/submodulo\n', 'utf8');
  await rechaza(() => assertObjetivoDestructivo(e), /árbol de trabajo enlazado/);
});

test('[AC-9] un repositorio desnudo adentro del objetivo lo rechaza', async (t) => {
  const e = await destructivo(t);
  const desnudo = path.join(e.objetivo, 'espejo.git');
  await fs.mkdir(path.join(desnudo, 'objects'), { recursive: true });
  await fs.mkdir(path.join(desnudo, 'refs'), { recursive: true });
  await fs.writeFile(path.join(desnudo, 'HEAD'), 'ref: refs/heads/main\n', 'utf8');
  await rechaza(() => assertObjetivoDestructivo(e), /repositorio desnudo/);
});

test('[AC-9] un error de permisos durante la búsqueda detiene, no se lee como ausencia', async (t) => {
  if (process.getuid?.() === 0) {
    t.skip('como root los permisos no excluyen');
    return;
  }
  const e = await destructivo(t);
  const cerrado = path.join(e.objetivo, 'cerrado');
  await fs.mkdir(path.join(cerrado, '.git'), { recursive: true });
  await fs.chmod(cerrado, 0o000);
  try {
    await rechaza(() => assertObjetivoDestructivo(e), /no se puede enumerar/);
  } finally {
    // Se restaura acá y no en un `after`: el `after` del sandbox se registró
    // antes, corre antes, y su borrado recursivo fallaría contra el modo 000.
    await fs.chmod(cerrado, 0o755);
  }
});

test('[AC-9] un objetivo ausente detiene en vez de pasar por vacuidad', async (t) => {
  const e = await destructivo(t);
  await rechaza(
    () => assertObjetivoDestructivo({ ...e, objetivo: path.join(e.raizDeclarada, 'no-existe') }),
    /no se puede resolver objetivo/,
  );
});

test('[AC-9] un enlace no se recorre ni convierte su destino en objetivo', async (t) => {
  const e = await destructivo(t);
  // Un repositorio de verdad, afuera, alcanzado por un enlace desde adentro. El
  // borrado quita el enlace, no su destino, así que esto **no** se rechaza — y
  // que no se rechace es la mitad del criterio: recorrerlo haría imposible
  // retirar un flujo que apenas menciona otro sitio.
  const afuera = await e.caja.makeRepo('ajeno');
  await e.caja.makeSymlink(path.join(e.objetivo, 'atajo'), afuera);
  await assert.doesNotReject(() => assertObjetivoDestructivo(e));

  // Y el vault, aunque llegue por un enlace, sigue teniendo que ser disjunto.
  const enlaceAlVault = path.join(e.caja.vaultsDir, 'atajo-al-objetivo');
  await e.caja.makeSymlink(enlaceAlVault, e.objetivo);
  await rechaza(() => assertObjetivoDestructivo({ ...e, vaultRoot: enlaceAlVault }), /no son disjuntos/);
});
