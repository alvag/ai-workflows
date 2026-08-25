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
import { ContractError } from '../../../skills/knowledge-vault/scripts/lib/contracts.mjs';

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

test('rutea cada verbo a su comando y devuelve su estado', async () => {
  const { llamadas, comandos } = espias();
  for (const [verbo, esperado] of [
    ['archive', 'ARCHIVED'], ['migrate', 'BATCH_OK'], ['index', 'INDEX_OK'], ['config', 'VAULT_CONFIGURED'],
  ]) {
    const r = await runCli({ argv: [verbo, '--vault-root', '/v'], comandos });
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
