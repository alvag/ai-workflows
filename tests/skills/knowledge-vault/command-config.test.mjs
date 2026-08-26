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
  // El vault **existe** en disco: `--set-root` ahora comprueba la raíz antes de
  // escribirla, y una escena que no la crea estaría probando el rechazo en vez de
  // la escritura.
  return { caja, ruta, vault: await caja.makeVault('dev-memory') };
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
  // Las dos raíces existen: lo que se prueba es el reemplazo, no la validación.
  const viejo = await e.caja.makeVault('viejo');
  await correr({ config: e.ruta, 'set-root': viejo });
  await correr({ config: e.ruta, 'set-root': e.vault });
  const texto = await fsp.readFile(e.ruta, 'utf8');
  assert.equal((texto.match(/path_vault:/g) ?? []).length, 1);
  assert.ok(!texto.includes(viejo));
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

// ── `--discover`: el primer uso, cuando no hay nada declarado ─────────────────

test('discover clasifica, sugiere el único vault y nombra los ajenos sin sugerirlos', async (t) => {
  const e = await escena(t);
  const raiz = await e.caja.makeTree(path.join(e.caja.reposDir, 'home'), {
    'vaults/dev-memory/.kv/identidades.tsv': 'ai\t\t\t\n',
    'vaults/dev-memory/projects/ai/sdd/uno.md': '# uno\n',
    'vaults/cocha/.obsidian/app.json': '{}\n',
    'vaults/cocha/Welcome.md': '# hola\n',
  });

  const r = await correr({ discover: true, 'search-root': raiz });
  assert.equal(r.status, 'VAULTS_DISCOVERED');
  assert.equal(r.sugerido, path.join(raiz, 'vaults', 'dev-memory'));
  assert.deepEqual(r.vaults.map((v) => v.root), [path.join(raiz, 'vaults', 'dev-memory')]);
  // El ajeno se informa pero **no** entra en `vaults` ni puede ser el sugerido:
  // callarlo dejaría a quien busca preguntándose por qué su carpeta no aparece,
  // y sugerirlo es exactamente el daño que este verbo existe para evitar.
  assert.deepEqual(r.ajenos, [path.join(raiz, 'vaults', 'cocha')]);
});

test('discover no sugiere nada cuando hay más de un vault', async (t) => {
  const e = await escena(t);
  const raiz = await e.caja.makeTree(path.join(e.caja.reposDir, 'home'), {
    'a/.kv/x': '\n',
    'b/.kv/x': '\n',
  });

  const r = await correr({ discover: true, 'search-root': raiz });
  assert.equal(r.vaults.length, 2);
  // Desempatar por número de flujos elegiría por tamaño una pregunta que es de
  // propósito: cuál de los dos vaults es el de este proyecto.
  assert.equal(r.sugerido, null);
});

test('discover sin candidatos sale 0 y lo dice, en vez de fallar', async (t) => {
  const e = await escena(t);
  const raiz = await e.caja.makeTree(path.join(e.caja.reposDir, 'desierto'), { 'a/b/nota.txt': 'x\n' });

  // Mismo criterio que el ensayo de `retire`: un descubrimiento que falla por lo
  // que encontró es un descubrimiento que no se puede leer. Cero candidatos es un
  // resultado legítimo —hay que crear el vault—, no un error.
  const r = await correr({ discover: true, 'search-root': raiz });
  assert.equal(r.status, 'VAULTS_DISCOVERED');
  assert.deepEqual(r.vaults, []);
  assert.equal(r.sugerido, null);
});

test('discover no escribe nada: descubrir no es configurar', async (t) => {
  const e = await escena(t, AJENO);
  const raiz = await e.caja.makeTree(path.join(e.caja.reposDir, 'home'), { 'v/.kv/x': '\n' });

  await correr({ discover: true, 'search-root': raiz, config: e.ruta });
  assert.equal(await fsp.readFile(e.ruta, 'utf8'), AJENO, 'discover tocó el config');
});

test('set-root rechaza una raíz que no existe, antes de escribirla', async (t) => {
  const e = await escena(t, AJENO);
  // El defecto que esto cierra: `resolveVaultRoot` sólo valida la **forma**, así
  // que una ruta mal tipeada se escribía sin chistar y reaparecía en el `archive`
  // siguiente, lejos de su causa y como error interno.
  await assert.rejects(
    () => correr({ config: e.ruta, 'set-root': path.join(e.caja.vaultsDir, 'no-existe') }),
    (error) => {
      assert.equal(error.code, 'VAULT_ROOT_UNAVAILABLE');
      return true;
    },
  );
  assert.equal(await fsp.readFile(e.ruta, 'utf8'), AJENO, 'el config cambió pese al rechazo');
});
