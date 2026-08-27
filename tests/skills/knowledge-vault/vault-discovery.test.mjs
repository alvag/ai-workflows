/**
 * El descubrimiento de vaults, y la guarda que sale de él.
 *
 * Dos propiedades distintas se prueban acá. **Que clasifique por marca
 * estructural y no por ubicación**: un vault de notas ajeno vive donde viven los
 * vaults, y ofrecerlo tiene consecuencia física —`ensureVaultRepo` le hace
 * `git init` antes de que ninguna otra guarda mire—. Y **que la clasificación
 * gobierne la resolución de la raíz**, no sólo el listado: descubrir bien y dejar
 * pasar igual el destino equivocado no protege de nada.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';

import { assertRootUsable } from '../../../skills/knowledge-vault/scripts/lib/config.mjs';
import { DurableFs } from '../../../skills/knowledge-vault/scripts/lib/durable-fs.mjs';
import {
  CLASES,
  clasificarDirectorio,
  descubrirVaults,
} from '../../../skills/knowledge-vault/scripts/lib/vault-discovery.mjs';
import { createSandbox } from './helpers/sandbox.mjs';

const fs = new DurableFs();
const clasificar = (dir) => clasificarDirectorio({ fs, dir });

/** Un home con las cuatro formas que el descubrimiento tiene que distinguir. */
async function home(caja) {
  const raiz = path.join(caja.reposDir, 'home');
  await caja.makeTree(raiz, {
    // un vault de kv por su marca fuerte
    'vaults/dev-memory/.kv/identidades.tsv': 'ai\t\t\t\n',
    'vaults/dev-memory/index.md': '# vault\n',
    'vaults/dev-memory/projects/ai/sdd/uno.md': '# uno\n',
    'vaults/dev-memory/projects/ai/sdd/dos.md': '# dos\n',
    'vaults/dev-memory/projects/ai/sdd/index.md': '# index\n',
    // un vault de kv anterior a `.kv`: sólo el par index.md + projects/
    'vaults/viejo/index.md': '# vault\n',
    'vaults/viejo/projects/otro/sdd/tres.md': '# tres\n',
    // un vault de notas ajeno
    'vaults/cocha/.obsidian/app.json': '{}\n',
    'vaults/cocha/Welcome.md': '# hola\n',
    // ruido que no es candidato
    'code/proyecto/README.md': '# code\n',
    'Library/no-se-recorre/index.md': '# trampa\n',
  });
  return raiz;
}

test('[AC-D1] la marca estructural distingue un vault de kv de un vault de notas', async (t) => {
  const caja = await createSandbox(t);
  const raiz = await home(caja);

  assert.equal((await clasificar(path.join(raiz, 'vaults/dev-memory'))).clase, CLASES.KV);
  assert.equal((await clasificar(path.join(raiz, 'vaults/viejo'))).clase, CLASES.KV, 'el par index.md+projects/ es marca válida');
  assert.equal((await clasificar(path.join(raiz, 'vaults/cocha'))).clase, CLASES.OBSIDIAN);
  assert.equal((await clasificar(path.join(raiz, 'code/proyecto'))).clase, CLASES.OTRO);
});

test('[AC-D1] un directorio abierto en Obsidian pero sin notas es vacío, no ajeno', async (t) => {
  const caja = await createSandbox(t);
  // El falso positivo que hay que no cometer: así se ve un vault de kv recién
  // creado que alguien abrió en Obsidian antes de archivar nada. Tratarlo como
  // ajeno rechazaría el camino normal del primer uso.
  const dir = await caja.makeTree(path.join(caja.reposDir, 'recien-creado'), {
    '.obsidian/app.json': '{}\n',
    '.DS_Store': 'ruido\n',
  });
  assert.equal((await clasificar(dir)).clase, CLASES.VACIO);
});

test('[AC-D2] el recorrido encuentra los vaults, informa los ajenos y poda lo que no toca', async (t) => {
  const caja = await createSandbox(t);
  const raiz = await home(caja);

  const { candidatos } = await descubrirVaults({ fs, raices: [raiz] });
  const kv = candidatos.filter((c) => c.clase === CLASES.KV).map((c) => path.relative(raiz, c.root));
  const ajenos = candidatos.filter((c) => c.clase === CLASES.OBSIDIAN).map((c) => path.relative(raiz, c.root));

  assert.deepEqual(kv, ['vaults/dev-memory', 'vaults/viejo']);
  assert.deepEqual(ajenos, ['vaults/cocha']);

  // `Library` está en la poda, así que el vault-trampa que vive adentro no
  // aparece pese a tener marca válida. Es lo que hace que recorrer un home real
  // no cueste minutos.
  assert.ok(!candidatos.some((c) => c.root.includes('Library')), 'la poda no se aplicó');
});

test('[AC-D2] la evidencia cuenta proyectos y flujos, sin contar dos veces cada flujo', async (t) => {
  const caja = await createSandbox(t);
  const raiz = await home(caja);

  const { candidatos } = await descubrirVaults({ fs, raices: [raiz] });
  const dev = candidatos.find((c) => c.root.endsWith('dev-memory'));
  // Dos flujos: `uno` y `dos`. El `index.md` del directorio `sdd/` no es un flujo,
  // y contar los directorios además de los `.md` daría cuatro.
  assert.deepEqual(dev.evidencia, { proyectos: 1, flujos: 2, nombresProyecto: ['ai'] });
});

test('[AC-D2] un directorio ilegible se saltea en vez de abortar el descubrimiento', async (t) => {
  const caja = await createSandbox(t);
  const raiz = await home(caja);
  // Un `fs` que se niega a listar un subárbol: es lo que hace `~/Library` en
  // macOS. El descubrimiento tiene que devolver igual lo que sí pudo mirar.
  const cascarrabias = new DurableFs();
  const original = cascarrabias.readDirNames.bind(cascarrabias);
  cascarrabias.readDirNames = async (target, label) => {
    if (target.endsWith('cocha')) throw new Error('EACCES simulado');
    return original(target, label);
  };

  const { candidatos } = await descubrirVaults({ fs: cascarrabias, raices: [raiz] });
  assert.deepEqual(
    candidatos.filter((c) => c.clase === CLASES.KV).map((c) => path.basename(c.root)),
    ['dev-memory', 'viejo'],
  );
});

test('[AC-D3] resolver la raíz rechaza el vault de notas ajeno, antes de tocarlo', async (t) => {
  const caja = await createSandbox(t);
  const raiz = await home(caja);
  const ajeno = path.join(raiz, 'vaults/cocha');

  await assert.rejects(
    () => assertRootUsable({ fs, root: ajeno, label: 'prueba' }),
    (error) => {
      // El código importa: es lo que lo separa de un fallo interno y lo vuelve
      // degradable para quien automatiza.
      assert.equal(error.code, 'VAULT_ROOT_UNAVAILABLE');
      assert.match(error.message, /vault de notas ajeno/);
      return true;
    },
  );

  // Y los dos que sí son destinos válidos siguen pasando: una guarda que rechaza
  // de más es tan inservible como una que no rechaza nada.
  await assertRootUsable({ fs, root: path.join(raiz, 'vaults/dev-memory'), label: 'prueba' });
  await assertRootUsable({ fs, root: await caja.makeVault('nuevo'), label: 'prueba' });
});

test('[AC-1] el vacío con .obsidian real se emite como candidato; el del .obsidian falso no', async (t) => {
  const caja = await createSandbox(t);
  // La marca se comprueba por tipo, no por nombre: las tres formas comparten
  // `nombres: ['.obsidian']` — `clasificarDirectorio` lo excluye antes de ver qué es.
  const raiz = await caja.makeTree(path.join(caja.reposDir, 'marcas'), {
    'real/.obsidian/app.json': '{}\n',
    'enlace/.DS_Store': 'ruido\n',
    'suelto/.obsidian': 'no soy un directorio\n',
  });
  await caja.makeSymlink(path.join(raiz, 'enlace/.obsidian'), path.join(raiz, 'real/.obsidian'), 'dir');

  const { candidatos } = await descubrirVaults({ fs, raices: [raiz] });
  assert.deepEqual(candidatos.map((c) => path.relative(raiz, c.root)), ['real']);
  // `evidencia: null` y no `{proyectos: 0, …}`, que es el de un vault de `kv` recién creado.
  assert.deepEqual(candidatos[0], { root: path.join(raiz, 'real'), clase: CLASES.VACIO, evidencia: null });
});

test('[AC-3] el vacío sin marca de Obsidian no entra en candidatos', async (t) => {
  const caja = await createSandbox(t);
  // Los dos subtipos sin marca: sobre un home real son diecisiete y ninguno es un vault.
  const raiz = await caja.makeTree(path.join(caja.reposDir, 'vacios'), { 'solo-ds/.DS_Store': 'x\n' });
  await caja.makeTree(path.join(raiz, 'del-todo-vacio'), {});
  assert.deepEqual((await descubrirVaults({ fs, raices: [raiz] })).candidatos, []);
});
