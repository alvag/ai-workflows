/**
 * El ruteo del CLI: qué invocación es válida y con qué código sale.
 *
 * El CLI no tiene lógica propia; su trabajo es traducir `argv` a una llamada y un
 * error a un código de salida. Lo que se verifica es justo eso, sin tocar disco:
 * los comandos se inyectan.
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import { parseArgv, runCli } from '../../../skills/knowledge-vault/scripts/lib/cli.mjs';
import { ContractError, VERBS } from '../../../skills/knowledge-vault/scripts/lib/contracts.mjs';

const espias = () => {
  const llamadas = [];
  const hacer = (status) => async (entrada) => { llamadas.push(entrada); return { status }; };
  return {
    llamadas,
    comandos: {
      archive: hacer('ARCHIVED'),
      migrate: hacer('BATCH_OK'),
      index: hacer('INDEX_OK'),
      config: hacer('VAULT_CONFIGURED'),
    },
  };
};

test('parsea el verbo y sus banderas largas', () => {
  const { verb, flags } = parseArgv(['archive', '--from', '.plans/archived/abc-1', '--summary', 'un resumen']);
  assert.equal(verb, 'archive');
  assert.equal(flags.from, '.plans/archived/abc-1');
  assert.equal(flags.summary, 'un resumen');
});

test('una bandera booleana no se come el argumento siguiente', () => {
  const { flags } = parseArgv(['migrate', '--dry-run', '--from', 'x']);
  assert.equal(flags['dry-run'], true);
  assert.equal(flags.from, 'x');
});

test('un verbo desconocido o ausente es USAGE, no un error interno', async () => {
  for (const argv of [[], ['restore'], ['doctor', '--repair']]) {
    assert.throws(() => parseArgv(argv), ContractError, JSON.stringify(argv));
  }
  const { comandos } = espias();
  const r = await runCli({ argv: ['restore'], comandos });
  assert.equal(r.status, 'USAGE');
  assert.equal(r.exitCode, 2);
});

// Cada verbo va con una bandera que su fila declara. Antes los cuatro usaban
// `--vault-root`, que `config` no acepta —su raíz la declara él mismo—: se parseaba
// y se descartaba en silencio, así que el test documentaba el defecto.
test('rutea cada verbo a su comando y devuelve su estado', async () => {
  const { llamadas, comandos } = espias();
  for (const [verbo, bandera, esperado] of [
    ['archive', '--vault-root', 'ARCHIVED'], ['migrate', '--vault-root', 'BATCH_OK'],
    ['index', '--vault-root', 'INDEX_OK'], ['config', '--config', 'VAULT_CONFIGURED'],
  ]) {
    const r = await runCli({ argv: [verbo, bandera, '/v'], comandos });
    assert.equal(r.status, esperado, verbo);
    assert.equal(r.exitCode, 0, verbo);
  }
  assert.equal(llamadas.length, 4);
});

test('--config y --vault-root son excluyentes', async () => {
  const { comandos } = espias();
  const r = await runCli({ argv: ['index', '--config', 'c.yml', '--vault-root', '/v'], comandos });
  assert.equal(r.status, 'USAGE');
  assert.equal(r.exitCode, 2);
});

test('un error con código de contrato sale con su código, no con el genérico', async () => {
  const comandos = {
    archive: async () => { throw Object.assign(new Error('no verifica'), { code: 'VERIFY_FAILED' }); },
  };
  const r = await runCli({ argv: ['archive', '--from', 'x', '--summary', 'y'], comandos });
  assert.equal(r.status, 'VERIFY_FAILED');
  assert.equal(r.exitCode, 9);
  assert.match(r.message, /no verifica/);
});

test('un error sin código de contrato es INTERNAL_ERROR y no se disfraza de otra cosa', async () => {
  const comandos = { index: async () => { throw new Error('algo raro'); } };
  const r = await runCli({ argv: ['index', '--vault-root', '/v'], comandos });
  assert.equal(r.status, 'INTERNAL_ERROR');
  assert.equal(r.exitCode, 1);
});

// El contador es lo único que discrimina: `USAGE`/2 también lo produce un comando
// que falla por una obligatoria ausente, así que el código de salida no distingue
// el rechazo del parser del fallo posterior.
const espiaTodos = () => {
  const cuenta = { llamadas: 0 };
  const comandos = Object.fromEntries(
    VERBS.map((v) => [v, async () => { cuenta.llamadas += 1; return { status: 'INDEX_OK' }; }]),
  );
  return { cuenta, comandos };
};

test('una bandera que ningún verbo declara es USAGE, en los seis', async () => {
  for (const verbo of VERBS) {
    for (const bandera of ['--flow-id', '--zzz', '--constructor']) {
      const { cuenta, comandos } = espiaTodos();
      const r = await runCli({ argv: [verbo, bandera, 'x'], comandos });
      assert.equal(r.status, 'USAGE', `${verbo} ${bandera}`);
      assert.equal(r.exitCode, 2, `${verbo} ${bandera}`);
      assert.equal(cuenta.llamadas, 0, `${verbo} ${bandera}: el comando se invocó`);
      assert.match(r.message, new RegExp(bandera.slice(2)), `${verbo} ${bandera}`);
      assert.match(r.message, new RegExp(verbo), `${verbo} ${bandera}`);
    }
  }
});

test('una bandera real de otro verbo también es USAGE, con invocación por lo demás válida', async () => {
  // Cada caso lleva sus obligatorias: sin ellas el comando fallaría igual con USAGE/2.
  const casos = [
    ['archive', ['--from', 'x', '--summary', 'y'], '--root', '/z'],
    ['migrate', ['--from', 'x', '--summaries', 't'], '--approve-digest', 'ab'],
    ['index', [], '--root', '/z'],
    ['config', ['--config', 'c'], '--summary', 's'],
    ['retire', ['--root', '/r'], '--summaries', 't'],
    ['identity', ['--propose'], '--set-root', '/v'],
  ];
  for (const [verbo, base, bandera, valor] of casos) {
    const { cuenta, comandos } = espiaTodos();
    const r = await runCli({ argv: [verbo, ...base, bandera, valor], comandos });
    assert.equal(r.status, 'USAGE', `${verbo} ${bandera}`);
    assert.equal(r.exitCode, 2, `${verbo} ${bandera}`);
    assert.equal(cuenta.llamadas, 0, `${verbo} ${bandera}: el comando se invocó`);
    assert.match(r.message, new RegExp(bandera.slice(2)), `${verbo} ${bandera}`);
    assert.match(r.message, new RegExp(verbo), `${verbo} ${bandera}`);
  }
});

test('las seis filas de la matriz se aceptan y conservan cada valor', () => {
  const filas = [
    ['archive', { from: 'x', summary: 'y', config: 'c' }],
    ['migrate', { from: 'x', summaries: 't', 'dry-run': true, 'vault-root': '/v' }],
    ['index', { config: 'c' }],
    ['config', { config: 'c', 'set-root': '/v', discover: true, 'search-root': '/s' }],
    ['retire', { root: '/r', from: 'f', 'dry-run': true, 'approve-digest': 'ab', config: 'c' }],
    ['identity', { propose: true, declare: 'id', 'vault-root': '/v' }],
  ];
  // El argv se deriva del esperado: una bandera booleana no lleva valor.
  const aArgv = (esperado) => Object.entries(esperado)
    .flatMap(([k, v]) => (v === true ? [`--${k}`] : [`--${k}`, v]));
  for (const [verbo, esperado] of filas) {
    const { verb, flags } = parseArgv([verbo, ...aArgv(esperado)]);
    assert.equal(verb, verbo);
    assert.deepEqual(flags, esperado, verbo);
  }
});

test('la forma de la bandera es por verbo, no global', async () => {
  const { flags } = parseArgv(['migrate', '--dry-run', '--from', 'x']);
  assert.equal(flags['dry-run'], true);
  assert.equal(flags.from, 'x');
  // `dry-run` es de `migrate` y `retire`; la tabla global la aceptaba en los seis.
  const { cuenta, comandos } = espiaTodos();
  const r = await runCli({ argv: ['identity', '--dry-run'], comandos });
  assert.equal(r.status, 'USAGE');
  assert.equal(r.exitCode, 2);
  assert.equal(cuenta.llamadas, 0);
});
