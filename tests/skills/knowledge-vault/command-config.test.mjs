/**
 * El verbo `config`, que es el que hace posible un vault por proyecto.
 *
 * Escribe en el config **del consumidor**, no en uno propio, así que lo que se
 * verifica es que no le arruine el archivo: las otras claves quedan como estaban,
 * y una raíz inválida se rechaza antes de escribir nada.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fsp from 'node:fs/promises';
import path from 'node:path';

import { configCommand } from '../../../skills/knowledge-vault/scripts/lib/commands/config.mjs';
import { DurableFs } from '../../../skills/knowledge-vault/scripts/lib/durable-fs.mjs';
import { createSandbox } from './helpers/sandbox.mjs';

const AJENO = 'stack: node\ntest_cmd: "npm test"\ntracker: none\n';

async function escena(t, contenido = null) {
  const caja = await createSandbox(t);
  const ruta = path.join(caja.reposDir, 'proyecto', '.specify', 'config.yml');
  if (contenido !== null) {
    await fsp.mkdir(path.dirname(ruta), { recursive: true });
    await fsp.writeFile(ruta, contenido, 'utf8');
  }
  return { caja, ruta, vault: path.join(caja.vaultsDir, 'dev-memory') };
}

const correr = (flags) => configCommand({ fs: new DurableFs(), flags, homeDir: '/home/nadie' });

test('escribe path_vault y conserva intactas las claves ajenas', async (t) => {
  const e = await escena(t, AJENO);
  const r = await correr({ config: e.ruta, 'set-root': e.vault });
  assert.equal(r.status, 'VAULT_SET');

  const texto = await fsp.readFile(e.ruta, 'utf8');
  for (const linea of AJENO.trim().split('\n')) assert.ok(texto.includes(linea), linea);
  assert.ok(texto.includes('knowledge-vault:'));
  assert.equal((await correr({ config: e.ruta })).root, e.vault);
});

test('crea el config si no existía', async (t) => {
  const e = await escena(t);
  assert.equal((await correr({ config: e.ruta, 'set-root': e.vault })).status, 'VAULT_SET');
  assert.equal((await correr({ config: e.ruta })).root, e.vault);
});

test('reemplaza una raíz previa en vez de agregar una segunda', async (t) => {
  const e = await escena(t, AJENO);
  await correr({ config: e.ruta, 'set-root': '/vaults/viejo' });
  await correr({ config: e.ruta, 'set-root': e.vault });
  const texto = await fsp.readFile(e.ruta, 'utf8');
  assert.equal((texto.match(/path_vault:/g) ?? []).length, 1);
  assert.ok(!texto.includes('/vaults/viejo'));
});

test('una raíz inválida se rechaza antes de escribir', async (t) => {
  const e = await escena(t, AJENO);
  for (const mala of ['relativa/no/sirve', '/con/../salto', '~usuario/otro']) {
    await assert.rejects(() => correr({ config: e.ruta, 'set-root': mala }), mala);
  }
  assert.equal(await fsp.readFile(e.ruta, 'utf8'), AJENO, 'el config cambió pese al rechazo');
});

test('leer un config que no declara la raíz es NO_VAULT, no una raíz inventada', async (t) => {
  const e = await escena(t, AJENO);
  await assert.rejects(() => correr({ config: e.ruta }), (error) => {
    assert.equal(error.code, 'NO_VAULT');
    return true;
  });
});

test('sin --config es USAGE', async () => {
  await assert.rejects(() => correr({}), (error) => {
    assert.equal(error.code, 'USAGE');
    return true;
  });
});
