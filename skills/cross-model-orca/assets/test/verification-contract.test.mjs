import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import {
  MAX_CONTRACT_BYTES,
  parseContract,
  validateContract,
} from '../verification-contract.mjs';

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const FIXTURES_DIR = path.join(TEST_DIR, 'fixtures');
const CLI_PATH = path.resolve(TEST_DIR, '..', 'run-verification-contract.mjs');

function fixture(name) {
  return fs.readFileSync(path.join(FIXTURES_DIR, name), 'utf8');
}

function runCli(...args) {
  return spawnSync(process.execPath, [CLI_PATH, ...args], { encoding: 'utf8' });
}

test('parseContract procesa un contrato válido con versiones y baseline tipado', () => {
  const parsed = parseContract(fixture('valid-multiversion.md'));

  assert.equal(parsed.versions.length, 2);
  assert.deepEqual(parsed.versions.map(({ version }) => version), [1, 2]);
  assert.deepEqual(
    parsed.versions[0].rows.map(({ id, baseline }) => [id, baseline]),
    [
      ['pruebas', 'RED'],
      ['formato', 'GREEN_ALREADY'],
      ['manual', 'NOT_APPLICABLE'],
      ['entorno', 'BLOCKED'],
    ],
  );
  assert.equal(parsed.versions[0].baseline[1].state, 'GREEN_ALREADY');
  assert.match(parsed.versions[0].baseline[1].adjudication, /^already_satisfied/);
  assert.match(parsed.versions[0].baseline[2].justification, /interfaz gráfica/);
});

test('la fixture derivada de la plantilla canónica valida sin variaciones', () => {
  assert.deepEqual(
    validateContract(fixture('valid-canonical-template.md')),
    { ok: true, versions: 1 },
  );
});

test('validateContract rechaza cada violación estructural con un error concreto', async (t) => {
  const cases = [
    ['invalid-baseline-state.md', /Baseline inválido/i],
    ['invalid-duplicate-id.md', /duplica el ID/i],
    ['invalid-non-slug-id.md', /slug/i],
    ['invalid-empty-cell.md', /celdas.*vacías/i],
    ['invalid-pipe-cell.md', /pipe/i],
    ['invalid-version-id-set.md', /conjunto estable/i],
    ['invalid-green-no-adjudication.md', /exige adjudicación/i],
    ['invalid-green-nonfinal-adjudication.md', /única adjudicación final/i],
    ['invalid-na-no-justification.md', /exige justificación/i],
    ['invalid-baseline-missing.md', /no registra los IDs/i],
    ['invalid-baseline-duplicate.md', /duplica el ID/i],
    ['invalid-baseline-incoherent.md', /no es coherente/i],
    ['invalid-no-baseline.md', /Falta el bloque.*Baseline/i],
    ['invalid-evidence.md', /Evidence inválido/i],
    ['invalid-version-gap.md', /versiones deben ser consecutivas/i],
    ['invalid-timestamp.md', /Timestamp.*inválido/i],
  ];

  for (const [name, expected] of cases) {
    await t.test(name, () => {
      assert.throws(() => validateContract(fixture(name)), expected);
    });
  }
});

test('input sobredimensionado y markdown malformado fallan de forma acotada', () => {
  const oversized = 'x'.repeat(MAX_CONTRACT_BYTES + 1);
  assert.throws(() => validateContract(oversized), /máximo de 1 MiB/i);
  assert.throws(
    () => validateContract('# Verification contract — roto\n\ncontenido inesperado\n'),
    /schemaVersion: 1/i,
  );
});

test('CLI validate emite JSON para un contrato válido', () => {
  const result = runCli('validate', path.join(FIXTURES_DIR, 'valid-multiversion.md'));

  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), { ok: true, versions: 2 });
  assert.equal(result.stderr, '');
});

test('CLI validate rechaza una fixture inválida por stderr y exit 2', () => {
  const result = runCli('validate', path.join(FIXTURES_DIR, 'invalid-baseline-state.md'));

  assert.equal(result.status, 2);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, /^error: .*Baseline inválido/im);
});
