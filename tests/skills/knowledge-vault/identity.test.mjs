/**
 * T5 — las cuatro identidades (AC-1, AC-2, AC-2b, AC-2c, AC-4).
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';

import {
  FLOW_ID_RE,
  IdentityError,
  REPO_SLUG_RE,
  assertFlowId,
  assertRepoSlug,
  buildSourceInventoryV2,
  computeSourceFingerprint,
  deriveFlowId,
  deriveStem,
} from '../../../skills/knowledge-vault/scripts/lib/identity.mjs';
import { GOLDEN } from './fixtures/canonical-golden.mjs';

/** Por punto de código: un NUL crudo volvería binario este archivo para git. */
const NUL = String.fromCodePoint(0);

const HASH_A = '0a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f9';

function rejects(fn, code) {
  assert.throws(fn, (err) => {
    assert.ok(err instanceof IdentityError, `se esperaba IdentityError, llegó ${err?.name}`);
    assert.equal(err.code, code);
    return true;
  });
}

// ── Segmentos (AC-2, AC-3) ────────────────────────────────────────────────────

test('acepta segmentos canónicos', () => {
  for (const slug of ['a', 'ab', 'mi-repo-0123456789ab', 'a1', '9x9']) {
    assert.equal(assertRepoSlug(slug), slug);
  }
  for (const flow of ['a', 'abc-123', 'pqtch-546', 'v1.2.3', 'a_b.c-d', 'x'.repeat(128)]) {
    assert.equal(assertFlowId(flow), flow);
  }
});

test('rechaza cada clase de segmento inválido', () => {
  const slugsInvalidos = [
    '', 'A', 'Mi-Repo', 'a/b', 'a\\b', 'a:b', 'a b', '-a', 'a-', 'a.b', 'a_b',
    'x'.repeat(64), 'ñ', NUL, `a${NUL}b`,
  ];
  for (const slug of slugsInvalidos) {
    rejects(() => assertRepoSlug(slug), 'INVALID_REPO_SLUG');
  }

  const flowsInvalidos = [
    '', 'A', 'ABC-1', 'a/b', 'a\\b', 'a:b', 'a b', '-a', 'a-', '.a', 'a.',
    'a..b', '..', 'x'.repeat(129), 'ñ',
  ];
  for (const flow of flowsInvalidos) {
    rejects(() => assertFlowId(flow), 'INVALID_FLOW_ID');
  }
});

test('el flow-id prohíbe `..` en cualquier posición', () => {
  assert.ok(!FLOW_ID_RE.test('a..b'));
  assert.ok(!FLOW_ID_RE.test('..abc'));
  assert.ok(!FLOW_ID_RE.test('abc..'));
  assert.ok(FLOW_ID_RE.test('a.b.c'));
});

test('los patrones acotan la longitud', () => {
  assert.ok(REPO_SLUG_RE.test('a'.repeat(63)));
  assert.ok(!REPO_SLUG_RE.test('a'.repeat(64)));
  assert.ok(FLOW_ID_RE.test('a'.repeat(128)));
  assert.ok(!FLOW_ID_RE.test('a'.repeat(129)));
});

// ── Derivación del flow-id: rechaza, no transforma (AC-3) ─────────────────────

test('el flow-id debe ya ser canónico: `A`/`a` y `ª`/`a` se rechazan', () => {
  assert.equal(deriveFlowId('pqtch-546'), 'pqtch-546');

  // Transformar antes de validar haría converger estos tres al mismo flow-id, y
  // AC-2c no lo detectaría: comparten `repo_identity`. Dos flujos distintos
  // quedarían mezclados como revisiones de una sola fuente.
  rejects(() => deriveFlowId('PQTCH-546'), 'INVALID_FLOW_ID');
  rejects(() => deriveFlowId('ª-546'), 'INVALID_FLOW_ID');
  rejects(() => deriveFlowId('Abc'), 'INVALID_FLOW_ID');
});

test('el error de flow-id dice cómo salir del paso', () => {
  assert.throws(() => deriveFlowId('PQTCH-546'), /--flow-id/);
});

// ── repo-slug: stem legible + hash de identidad (AC-4) ────────────────────────

test('el stem pliega a ASCII, colapsa runs y recorta', () => {
  assert.equal(deriveStem('mi-repo'), 'mi-repo');
  assert.equal(deriveStem('Mi_Repo'), 'mi-repo');
  assert.equal(deriveStem('API v2 (nuevo)'), 'api-v2-nuevo');
  assert.equal(deriveStem('---raro---'), 'raro');
  assert.equal(deriveStem('a'.repeat(80)), 'a'.repeat(48));
});

// ── Los tres documentos y sus digests (AC-1) ──────────────────────────────────

/** Digest de una selección cualquiera: acá se lo trata como un valor opaco. */

// ── T8 — los constructores `v2`, anclados al golden escrito a mano ────────────

/**
 * El golden es un oráculo independiente: sus bytes y su digest salen de
 * `shasum -a 256`, no de este código. Comprobar que los constructores **producen
 * exactamente ese valor** es lo que impide que un cambio de forma se cuele con
 * los tests en verde, porque el digest ya está publicado en `plan.md` como forma
 * congelada (AC-37).
 */
const golden = (nombre) => GOLDEN.find((g) => g.name === nombre);

test('`buildSourceInventoryV2` produce el documento congelado, con los directorios vacíos', () => {
  const g = golden('inventario-v2-con-directorio-vacio');
  const construido = buildSourceInventoryV2({
    // Desordenados a propósito: el orden lo pone el constructor, no quien llama.
    files: [{ path: 'plan.md', type: 'file', size: 12, sha256: g.value.files[0].sha256 }],
    directories: [{ path: 'vacio' }],
  });

  assert.deepEqual(construido, g.value);
  assert.equal(computeSourceFingerprint(construido), g.digest);
});

test('un directorio vacío mueve el fingerprint: por eso entra al inventario (AC-23)', () => {
  const archivos = [{ path: 'plan.md', type: 'file', size: 12, sha256: HASH_A }];
  const sin = computeSourceFingerprint(buildSourceInventoryV2({ files: archivos, directories: [] }));
  const con = computeSourceFingerprint(buildSourceInventoryV2({ files: archivos, directories: [{ path: 'vacio' }] }));
  assert.notEqual(sin, con);
});
